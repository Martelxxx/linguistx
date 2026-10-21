"""Stage 2 gateway core: one Palabra session per source, never per passenger.

This is an isolated candidate runtime. Audio transmission to a real AES67
output card, HA fencing and full evidence capture remain release blockers.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
import secrets
import sqlite3
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

LANGUAGES = frozenset(
    "en fr es zh ar pt de it ja ko hi ru tr nl pl vi id uk sv th".split()
)
PALABRA_VOICE_ID = "44948595-c29b-4fb6-839a-77b9884d0cb8"
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
FRAME_BYTES = 15_360  # 320 ms * 24,000 Hz * 16-bit mono
MAX_INPUTS = 64
MAX_OUTPUTS = 64
MAX_WS_CONNECTIONS = 10  # conservative local bound, not a Palabra entitlement claim
MAX_AUDIO_BYTES = 384 * 1024


@dataclass(frozen=True)
class Output:
    channel_id: str
    language: str

    @classmethod
    def from_dict(cls, data: dict) -> "Output":
        result = cls(str(data["channel_id"]), str(data["language"]))
        if not ID.fullmatch(result.channel_id) or result.language not in LANGUAGES:
            raise ValueError("Invalid permanent output ID or language.")
        return result


@dataclass(frozen=True)
class Session:
    session_id: str
    source_id: str
    source_language: str
    tenant_id: str
    site_id: str
    zone_id: str
    flight_code: str
    source: str
    outputs: tuple[Output, ...]

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        item = cls(
            str(data["session_id"]), str(data["source_id"]),
            str(data.get("source_language", "en")),
            str(data["tenant_id"]), str(data["site_id"]),
            str(data["zone_id"]), str(data.get("flight_code", "")),
            str(data["source"]),
            tuple(Output.from_dict(out) for out in data["outputs"]),
        )
        for value in (item.session_id, item.source_id, item.tenant_id,
                      item.site_id, item.zone_id):
            if not ID.fullmatch(value):
                raise ValueError("Invalid session/site/source identifier.")
        if item.source_language not in LANGUAGES:
            raise ValueError("Source language must be explicitly configured.")
        if not 1 <= len(item.outputs) <= MAX_OUTPUTS:
            raise ValueError("Every session needs 1–64 output assignments.")
        if len({out.language for out in item.outputs}) != len(item.outputs):
            raise ValueError("A source cannot assign the same language twice.")
        if len({out.channel_id for out in item.outputs}) != len(item.outputs):
            raise ValueError("Output channel IDs must be unique.")
        if not (item.source.startswith("alsa:") or item.source.startswith("file:")
                or item.source.startswith("aes67:")):
            raise ValueError("Only explicitly configured ALSA, AES67 SDP or file sources are supported.")
        if item.flight_code and not re.fullmatch(r"[A-Z0-9]{2,3}\d{1,4}", item.flight_code):
            raise ValueError("Invalid flight code.")
        return item


def load_config(path: str | Path) -> list[Session]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    sessions = [Session.from_dict(d) for d in data["sessions"]]
    if not sessions or len(sessions) > MAX_INPUTS:
        raise ValueError("Configure between 1 and 64 source sessions.")
    if len(sessions) > MAX_WS_CONNECTIONS:
        raise ValueError("Provider concurrency not validated: max ten active inputs in candidate.")
    if sum(len(s.outputs) for s in sessions) > MAX_OUTPUTS:
        raise ValueError("Total assigned AES67 outputs cannot exceed 64.")
    for field in ("session_id", "source_id"):
        if len({getattr(s, field) for s in sessions}) != len(sessions):
            raise ValueError(f"Duplicate {field}.")
    ids = [out.channel_id for s in sessions for out in s.outputs]
    if len(set(ids)) != len(ids):
        raise ValueError("Output identities must be globally unique.")
    if len({s.tenant_id for s in sessions}) > 1:
        raise ValueError("This candidate is isolated to one tenant per process.")
    if len({s.site_id for s in sessions}) > 1:
        raise ValueError("This candidate is isolated to one site per process.")
    return sessions


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditJournal:
    """Append-only metadata ledger with per-row chain hashes; not audio evidence storage."""

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS events("
            "id INTEGER PRIMARY KEY, at TEXT NOT NULL, event TEXT NOT NULL,"
            "previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL)"
        )
        self.db.commit()

    def append(self, event: dict) -> str:
        # No passenger tokens, provider keys, raw audio or caption text in audit.
        metadata = {k: v for k, v in event.items()
                    if k in {"type", "session_id", "language", "transcription_id",
                             "output_id", "bytes", "sha256", "reason", "at", "status"}}
        payload = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        row = self.db.execute("SELECT entry_hash FROM events ORDER BY id DESC LIMIT 1").fetchone()
        previous = row[0] if row else "0" * 64
        digest = hashlib.sha256((previous + payload).encode()).hexdigest()
        self.db.execute(
            "INSERT INTO events(at,event,previous_hash,entry_hash) VALUES(?,?,?,?)",
            (utcnow(), payload, previous, digest),
        )
        self.db.commit()
        return digest

    def close(self) -> None:
        self.db.close()


class LanguageFanout:
    """One translation event published once; N independent bounded subscribers."""

    def __init__(self, queue_size: int = 64):
        self._subscriptions: dict[tuple[str, str], set[asyncio.Queue]] = defaultdict(set)
        self.queue_size = queue_size

    def subscribe(self, session_id: str, language: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.queue_size)
        self._subscriptions[(session_id, language)].add(queue)
        return queue

    def unsubscribe(self, session_id: str, language: str, queue: asyncio.Queue) -> None:
        self._subscriptions[(session_id, language)].discard(queue)

    def publish(self, session_id: str, language: str, event: dict) -> int:
        listeners = self._subscriptions[(session_id, language)]
        count = 0
        for queue in tuple(listeners):
            try:
                queue.put_nowait(event)
                count += 1
            except asyncio.QueueFull:
                listeners.discard(queue)
                # Fail the slow stream, rather than silently drop segments
                # or block the provider audio loop.
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait({"type": "overflow", "reason": "client_too_slow"})
        return count


class ScopedGuests:
    """Opaque short-lived grants for the server-side passenger gateway adapter."""

    def __init__(self, ttl: int = 120):
        self.ttl = min(3600, max(10, ttl))
        self._tokens: dict[str, tuple[str, str, float]] = {}

    def issue(self, session_id: str, language: str) -> tuple[str, int]:
        self.cleanup()
        token = secrets.token_urlsafe(36)
        self._tokens[token] = (session_id, language, time.monotonic() + self.ttl)
        return token, self.ttl

    def get(self, token: str) -> tuple[str, str] | None:
        record = self._tokens.get(token)
        if not record:
            return None
        session, language, expires = record
        if time.monotonic() >= expires:
            self._tokens.pop(token, None)
            return None
        return session, language

    def cleanup(self) -> None:
        now = time.monotonic()
        for token, record in list(self._tokens.items()):
            if record[2] <= now:
                self._tokens.pop(token, None)


def task_message(session: Session) -> dict:
    """Palabra multilang S2S; output audio and text share one WebSocket."""
    return {
        "message_type": "set_task",
        "data": {
            "input_stream": {
                "content_type": "audio",
                "source": {"type": "ws", "format": "pcm_s16le",
                           "sample_rate": 24000, "channels": 1},
            },
            "output_stream": {
                "content_type": "audio",
                "target": {"type": "ws", "format": "pcm_s16le"},
            },
            "pipeline": {
                "transcription": {"source_language": session.source_language},
                "translations": [
                    {"target_language": out.language,
                     "translate_partial_transcriptions": False,
                     "speech_generation": {"voice_id": PALABRA_VOICE_ID, "voice_cloning": False}}
                    for out in session.outputs
                ],
                "allowed_message_types": [
                    "validated_transcription", "translated_transcription"
                ],
            },
        },
    }


class Gateway:
    def __init__(self, sessions: list[Session], journal: AuditJournal | None = None):
        self.sessions = {s.session_id: s for s in sessions}
        self.fanout = LanguageFanout()
        self.guests = ScopedGuests()
        self.journal = journal
        self.states = {s.session_id: "stopped" for s in sessions}
        self._seen: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=4096))
        self._connect_times: deque[float] = deque()
        self._connect_lock = asyncio.Lock()

    async def limit_provider_connect(self) -> None:
        """Stay below documented 20 Palabra WS connects per token per minute."""
        async with self._connect_lock:
            while True:
                now = asyncio.get_running_loop().time()
                while self._connect_times and now - self._connect_times[0] >= 60:
                    self._connect_times.popleft()
                if len(self._connect_times) < 18:
                    self._connect_times.append(now)
                    return
                await asyncio.sleep(max(0.1, 60 - (now - self._connect_times[0])))

    def set_state(self, session_id: str, status: str, reason: str = "") -> None:
        self.states[session_id] = status
        for out in self.sessions[session_id].outputs:
            self.fanout.publish(session_id, out.language,
                                {"type": "status", "status": status, "reason": reason,
                                 "session_id": session_id, "at": utcnow()})
        if self.journal:
            self.journal.append({"type": "state", "session_id": session_id,
                                 "status": status, "reason": reason})

    def handle_provider(self, session_id: str, packet: dict) -> None:
        session = self.sessions[session_id]
        kind = packet.get("message_type")
        data = packet.get("data") or {}
        if not isinstance(data, dict):
            return
        if kind == "error":
            raise RuntimeError("Palabra translation session rejected.")
        if kind == "validated_transcription":
            # Source recognition is recorded in metadata, but never sent
            # to an unrelated language audience.
            tr = data.get("transcription") or {}
            tid = str(tr.get("transcription_id", ""))[:128]
            if tid and self.journal:
                self.journal.append({"type": "source_validated", "session_id": session_id,
                                     "transcription_id": tid})
            return
        if kind == "translated_transcription":
            tr = data.get("transcription") or {}
            lang = tr.get("language")
            body = tr.get("text")
            tid = str(tr.get("transcription_id", ""))[:128]
            part = str(tr.get("translation_part_id", "0"))[:32]
            if lang not in {x.language for x in session.outputs}:
                return
            if not isinstance(body, str) or not body.strip() or len(body) > 10_000:
                return
            key = f"text:{lang}:{tid}:{part}"
            if key in self._seen[session_id]:
                return
            self._seen[session_id].append(key)
            event = {"type": "caption", "session_id": session_id,
                     "message_id": f"{session_id}:{tid}:{part}",
                     "language": lang, "text": body.strip(), "at": utcnow()}
            self.fanout.publish(session_id, lang, event)
            if self.journal:
                self.journal.append({"type": "translated", "session_id": session_id,
                                     "language": lang, "transcription_id": tid,
                                     "sha256": hashlib.sha256(body.encode()).hexdigest()})
        if kind == "output_audio_data":
            lang = data.get("language")
            tid = str(data.get("transcription_id", ""))[:128]
            audio = data.get("data")
            if lang not in {x.language for x in session.outputs} or not isinstance(audio, str):
                return
            if len(audio) > (MAX_AUDIO_BYTES * 4 // 3 + 8):
                raise RuntimeError("Provider audio packet exceeds configured bounds.")
            try:
                raw = base64.b64decode(audio, validate=True)
            except (ValueError, base64.binascii.Error) as exc:
                raise RuntimeError("Malformed provider audio.") from exc
            if len(raw) > MAX_AUDIO_BYTES or len(raw) % 2:
                raise RuntimeError("Invalid provider audio alignment.")
            channel = next(o.channel_id for o in session.outputs if o.language == lang)
            event = {"type": "audio", "session_id": session_id,
                     "message_id": f"{session_id}:{tid}",
                     "language": lang, "format": "pcm_s16le", "sample_rate": 24000,
                     "chunk": audio, "last_chunk": bool(data.get("last_chunk")),
                     "at": utcnow()}
            self.fanout.publish(session_id, lang, event)
            if self.journal:
                # This confirms receipt from Palabra only, NOT AES67 transmission.
                self.journal.append({"type": "provider_audio_received",
                                     "session_id": session_id, "language": lang,
                                     "transcription_id": tid, "output_id": channel,
                                     "bytes": len(raw),
                                     "sha256": hashlib.sha256(raw).hexdigest()})


async def run_session(gateway: Gateway, session: Session, api_key: str, source_factory):
    """Restart a failed Palabra input session without restarting unaffected sources."""
    import websockets

    backoff = 1
    while True:
        try:
            gateway.set_state(session.session_id, "connecting")
            await gateway.limit_provider_connect()
            slug = uuid.uuid4().hex
            url = (f"wss://streaming.palabra.ai/streaming-api/{slug}/"
                   f"v1/speech-to-speech/stream?token={api_key}")
            async with websockets.connect(url, ping_interval=10, ping_timeout=30,
                                          max_size=2_000_000) as ws:
                await ws.send(json.dumps(task_message(session)))
                # A connection may first receive current_task or warnings.
                # Never stream audio before the running set_task acknowledgement.
                for _ in range(12):
                    ack = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
                    if ack.get("message_type") == "error":
                        raise RuntimeError("Palabra rejected source session setup.")
                    if (ack.get("message_type") == "task_status"
                            and ack.get("data", {}).get("command") == "set_task"):
                        if ack.get("data", {}).get("task_status") != "running":
                            raise RuntimeError("Palabra did not start the session.")
                        break
                else:
                    raise RuntimeError("Palabra session setup not acknowledged.")
                gateway.set_state(session.session_id, "active")
                backoff = 1
                receiver = asyncio.create_task(_receive(gateway, session, ws))
                producer = asyncio.create_task(_stream(session, ws, source_factory))
                try:
                    done, _ = await asyncio.wait(
                        {receiver, producer}, return_when=asyncio.FIRST_COMPLETED
                    )
                    for job in done:
                        result_error = job.exception()
                        if result_error:
                            raise result_error
                    if receiver in done and not producer.done():
                        raise RuntimeError("Palabra stream closed during source capture.")
                    if producer in done and not receiver.done():
                        # After end_task, wait for pending final text and audio.
                        await asyncio.wait_for(receiver, timeout=180)
                finally:
                    for job in (receiver, producer):
                        if not job.done():
                            job.cancel()
                    await asyncio.gather(receiver, producer, return_exceptions=True)
        except asyncio.CancelledError:
            gateway.set_state(session.session_id, "stopped")
            raise
        except Exception:
            gateway.set_state(session.session_id, "degraded", reason="translation_connection_lost")
            await asyncio.sleep(backoff)
            backoff = min(30, backoff * 2)


async def _receive(gateway: Gateway, session: Session, ws) -> None:
    async for raw in ws:
        packet = json.loads(raw)
        if packet.get("message_type") == "end_of_stream":
            break
        gateway.handle_provider(session.session_id, packet)


async def _stream(session: Session, ws, source_factory) -> None:
    async with source_factory(session.source) as source:
        # Hardware capture is real-time paced; file fixture sources pace themselves.
        async for frame in source:
            if not frame:
                continue
            if len(frame) != FRAME_BYTES:
                raise RuntimeError("PCM input frames must contain precisely 320 ms.")
            await ws.send(json.dumps({"message_type": "input_audio_data",
                                      "data": {"data": base64.b64encode(frame).decode()}}))
    await ws.send(json.dumps({"message_type": "end_task", "data": {"force": False}}))

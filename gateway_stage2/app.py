"""Local Stage 2 gateway API and passenger-provider contract.

Do not expose this prototype to the public Internet. Production ingress needs
TLS, device identity, fleet credentials and a reviewed guest proxy.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from .core import AuditJournal, Gateway, load_config, run_session
from .source import source_factory

NO_STORE = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


def response(status: int, body: dict) -> JSONResponse:
    return JSONResponse(body, status_code=status, headers=NO_STORE)


def bearer(req: Request) -> str:
    header = req.headers.get("authorization", "")
    if not header.startswith("Bearer ") or len(header) > 256:
        return ""
    return header[7:]


async def body_json(req: Request, maximum: int = 1024) -> dict:
    if req.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise ValueError("Expected JSON body.")
    chunks, total = [], 0
    async for chunk in req.stream():
        total += len(chunk)
        if total > maximum:
            raise ValueError("Request body too large.")
        chunks.append(chunk)
    obj = json.loads(b"".join(chunks))
    if not isinstance(obj, dict):
        raise ValueError("Expected JSON object.")
    return obj


def make_app(sessions, admin_token: str, api_key: str = "",
             journal: AuditJournal | None = None, run: bool = False) -> Starlette:
    if len(admin_token) < 32:
        raise ValueError("LX_GATEWAY_TOKEN must contain at least 32 characters.")
    gateway = Gateway(sessions, journal=journal)

    @asynccontextmanager
    async def lifespan(app):
        tasks: list[asyncio.Task] = []
        if run and not api_key:
            raise RuntimeError("PALABRA_API_KEY required for gateway translation.")
        if run:
            tasks = [
                asyncio.create_task(run_session(gateway, session, api_key, source_factory),
                                    name=f"translation:{session.session_id}")
                for session in sessions
            ]
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if journal:
                journal.close()

    def authorized(req: Request) -> bool:
        return hmac.compare_digest(bearer(req), admin_token)

    async def health(request: Request):
        return response(200, {"service": "linguistx-gateway-stage2", "state": "alive"})

    async def ready(request: Request):
        if not authorized(request):
            return response(401, {"error": "Unauthorized."})
        active = [gateway.states[sid] == "active" for sid in gateway.sessions]
        return response(200 if run and all(active) else 503,
                        {"ready": bool(run and all(active)),
                         "active_sources": sum(active), "configured_sources": len(active)})

    async def capabilities(request: Request):
        if not authorized(request):
            return response(401, {"error": "Unauthorized."})
        operational = run and any(s == "active" for s in gateway.states.values())
        return response(200, {
            "ready": bool(operational),
            "sessions": True,
            "guestJoin": True,
            "deliveryStatus": True,
            "liveText": bool(operational),
            # Mobile playback and AES67 output transmission are not integrated.
            "liveAudio": False,
            "transport": "server_side_sse",
            "productionCertified": False,
        })

    async def sessions_list(request: Request):
        if not authorized(request):
            return response(401, {"error": "Unauthorized."})
        flight = request.query_params.get("flight", "")
        matches = []
        for s in sessions:
            if flight and flight != s.flight_code:
                continue
            matches.append({
                "id": s.session_id, "title": f"Zone {s.zone_id}",
                "flightCode": s.flight_code,
                "status": ("active" if gateway.states[s.session_id] == "active"
                           else "paused" if gateway.states[s.session_id] == "connecting"
                           else "ended"),
                "languages": [o.language for o in s.outputs],
                "zone": s.zone_id,
            })
        return response(200, {"sessions": matches})

    async def guest_join(request: Request):
        if not authorized(request):
            return response(401, {"error": "Unauthorized."})
        try:
            obj = await body_json(request)
        except (ValueError, json.JSONDecodeError):
            return response(400, {"error": "Invalid guest request."})
        session_id, language = obj.get("sessionId"), obj.get("language")
        session = gateway.sessions.get(session_id)
        if (session is None or language not in {o.language for o in session.outputs}
                or gateway.states[session_id] != "active"):
            return response(404, {"error": "Session/language unavailable."})
        if len(gateway.guests._tokens) >= 10_000:
            return response(429, {"error": "Guest capacity reached."})
        token, ttl = gateway.guests.issue(session_id, language)
        return response(200, {"guestToken": token, "expiresIn": ttl})

    async def guest_state(request: Request):
        claims = gateway.guests.get(bearer(request))
        if not claims:
            return response(401, {"error": "Guest authorization expired."})
        session_id, _lang = claims
        status = gateway.states.get(session_id, "stopped")
        return response(200, {"state": ("connected" if status == "active"
                                         else "reconnecting" if status == "connecting"
                                         else "unavailable" if status == "degraded"
                                         else "ended")})

    async def events(request: Request):
        token = bearer(request)
        claims = gateway.guests.get(token)
        if not claims:
            return response(401, {"error": "Guest authorization expired."})
        session_id, language = claims
        key = (session_id, language)
        if len(gateway.fanout._subscriptions[key]) >= 250:
            return response(429, {"error": "Too many listeners for this language."})
        queue = gateway.fanout.subscribe(session_id, language)

        async def stream():
            try:
                yield ": connected\n\n"
                while not await request.is_disconnected():
                    if gateway.guests.get(token) != claims:
                        yield "event: expired\ndata: {}\n\n"
                        return
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=10)
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    if item.get("type") == "overflow":
                        yield "event: overflow\ndata: {}\n\n"
                        return
                    # JSON data is generated on the server and scoping is checked
                    # before connecting. Palabra keys never enter SSE payloads.
                    yield f"event: {item['type']}\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"
            finally:
                gateway.fanout.unsubscribe(session_id, language, queue)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={**NO_STORE, "X-Accel-Buffering": "no"})

    app = Starlette(routes=[
        Route("/healthz", health, methods=["GET"]),
        Route("/readyz", ready, methods=["GET"]),
        Route("/v1/capabilities", capabilities, methods=["GET"]),
        Route("/v1/sessions", sessions_list, methods=["GET"]),
        Route("/v1/guest/join", guest_join, methods=["POST"]),
        Route("/v1/guest/state", guest_state, methods=["GET"]),
        Route("/v1/guest/events", events, methods=["GET"]),
    ], lifespan=lifespan)
    app.state.gateway = gateway
    return app


def from_environment() -> Starlette:
    cfg = os.environ.get("LX_STAGE2_CONFIG", "")
    admin = os.environ.get("LX_GATEWAY_TOKEN", "")
    if not cfg:
        raise RuntimeError("LX_STAGE2_CONFIG must point to commissioned JSON config.")
    sessions = load_config(cfg)
    path = Path(os.environ.get("LX_STAGE2_JOURNAL", "./gateway-events.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return make_app(sessions, admin, os.environ.get("PALABRA_API_KEY", ""),
                    AuditJournal(path), run=os.environ.get("LX_STAGE2_RUN") == "1")


# ASGI target for uvicorn: require explicit configuration rather than
# accidentally starting an unconfigured, apparently healthy production gateway.
app = from_environment() if os.environ.get("LX_STAGE2_CONFIG") else None

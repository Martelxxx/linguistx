import base64
import json

import pytest
from starlette.testclient import TestClient

from gateway_stage2.core import (
    AuditJournal, Gateway, LanguageFanout, ScopedGuests,
    Session, load_config, task_message,
)
from gateway_stage2.app import make_app


def source_config(name="s1", outputs=None, **kwargs):
    return {
        "session_id": name, "source_id": f"input-{name}",
        "tenant_id": "tenantA", "site_id": "iad", "zone_id": "A23",
        "source_language": "en", "flight_code": "EK232",
        "source": "alsa:hw:1,0",
        "outputs": outputs or [
            {"channel_id": f"{name}.out1", "language": "fr"},
            {"channel_id": f"{name}.out2", "language": "es"},
        ],
        **kwargs,
    }


def gateway():
    session = Session.from_dict(source_config())
    return Gateway([session])


def test_capacity_and_permanent_channel_id_validation(tmp_path):
    config = {"sessions": [source_config()]}
    file = tmp_path / "config.json"
    file.write_text(json.dumps(config))
    loaded = load_config(file)
    assert loaded[0].outputs[0].channel_id == "s1.out1"
    assert task_message(loaded[0])["data"]["pipeline"]["translations"][0]["target_language"] == "fr"
    assert len(task_message(loaded[0])["data"]["pipeline"]["translations"]) == 2

    config["sessions"].append(source_config("s2", [
        {"channel_id": "s1.out1", "language": "de"}
    ]))
    file.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="globally unique"):
        load_config(file)

    config["sessions"] = [source_config("s1", [
        {"channel_id": f"channel{i}", "language": f"lang{i}"}
        for i in range(65)
    ])]
    file.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_config(file)


def test_no_duplicate_languages_or_invalid_cross_site_configuration():
    with pytest.raises(ValueError, match="same language twice"):
        Session.from_dict(source_config(outputs=[
            {"channel_id": "a", "language": "fr"},
            {"channel_id": "b", "language": "fr"},
        ]))
    with pytest.raises(ValueError):
        Session.from_dict(source_config(outputs=[
            {"channel_id": "../escape", "language": "fr"}
        ]))


def test_multi_language_single_upstream_session_and_fanout_isolation():
    gate = gateway()
    fr1 = gate.fanout.subscribe("s1", "fr")
    fr2 = gate.fanout.subscribe("s1", "fr")
    es = gate.fanout.subscribe("s1", "es")
    gate.handle_provider("s1", {
        "message_type": "translated_transcription",
        "data": {"transcription": {
            "language": "fr", "text": "Embarquement porte A23",
            "transcription_id": "msg1", "translation_part_id": 0,
        }},
    })
    assert fr1.get_nowait()["text"] == fr2.get_nowait()["text"]
    assert es.empty()
    # Duplicate segments must not be delivered twice.
    gate.handle_provider("s1", {
        "message_type": "translated_transcription",
        "data": {"transcription": {
            "language": "fr", "text": "Embarquement porte A23",
            "transcription_id": "msg1", "translation_part_id": 0,
        }},
    })
    assert fr1.empty()
    pcm = b"\x00\x01" * 256
    gate.handle_provider("s1", {
        "message_type": "output_audio_data",
        "data": {"language": "es", "transcription_id": "msg1",
                 "data": base64.b64encode(pcm).decode(), "last_chunk": True},
    })
    audio = es.get_nowait()
    assert audio["format"] == "pcm_s16le"
    assert audio["last_chunk"] is True
    assert fr1.empty()
    assert "token" not in audio


def test_bounded_slow_subscriber_disconnected_not_backpressuring_other_listeners():
    fanout = LanguageFanout(queue_size=1)
    slow = fanout.subscribe("s1", "fr")
    fast = fanout.subscribe("s1", "fr")
    fanout.publish("s1", "fr", {"type": "caption", "text": "first"})
    assert fast.get_nowait()["text"] == "first"
    fanout.publish("s1", "fr", {"type": "caption", "text": "second"})
    assert slow.get_nowait()["type"] == "overflow"
    assert fast.get_nowait()["text"] == "second"
    assert slow not in fanout._subscriptions[("s1", "fr")]


def test_guest_tokens_scope_to_one_language_and_expire():
    guests = ScopedGuests(ttl=10)
    token, ttl = guests.issue("s1", "fr")
    assert ttl == 10
    assert guests.get(token) == ("s1", "fr")
    assert guests.get("wrong") is None
    session, lang, _ = guests._tokens[token]
    guests._tokens[token] = (session, lang, 0)
    assert guests.get(token) is None


def test_guest_contract_has_no_public_session_access():
    gate = Session.from_dict(source_config())
    secret = "z" * 40
    app = make_app([gate], secret, run=False)
    with TestClient(app) as client:
        unauth = client.get("/v1/sessions")
        assert unauth.status_code == 401
        headers = {"Authorization": f"Bearer {secret}"}
        caps = client.get("/v1/capabilities", headers=headers).json()
        assert caps["ready"] is False
        assert caps["liveAudio"] is False
        assert caps["productionCertified"] is False
        listed = client.get("/v1/sessions?flight=EK232", headers=headers).json()
        assert listed["sessions"][0]["id"] == "s1"
        # Running state only after a confirmed provider session.
        assert client.post("/v1/guest/join", headers=headers,
                           json={"sessionId": "s1", "language": "fr"}).status_code == 404
        app.state.gateway.set_state("s1", "active")
        result = client.post("/v1/guest/join", headers=headers,
                             json={"sessionId": "s1", "language": "fr"})
        assert result.status_code == 200
        token = result.json()["guestToken"]
        assert client.get("/v1/guest/state", headers={
            "Authorization": f"Bearer {token}"
        }).json()["state"] == "connected"
        assert client.get("/v1/guest/state", headers=headers).status_code == 401
        assert client.post("/v1/guest/join", headers=headers,
                           json={"sessionId": "s1", "language": "ko"}).status_code == 404
        assert client.get("/readyz", headers=headers).status_code == 503


def test_audit_chain_has_hashes_not_caption_text_or_audio(tmp_path):
    journal = AuditJournal(tmp_path / "events.sqlite")
    journal.append({"type": "translated", "session_id": "s1",
                    "language": "fr", "text": "PRIVATE SAMPLE TEXT",
                    "token": "SUPER-SECRET"})
    journal.append({"type": "audio", "session_id": "s1", "bytes": 100})
    rows = journal.db.execute(
        "SELECT event,previous_hash,entry_hash FROM events ORDER BY id"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0][2] == rows[1][1]
    assert "PRIVATE" not in rows[0][0] and "SUPER-SECRET" not in rows[0][0]
    journal.close()


def test_provider_errors_do_not_fake_success():
    gate = gateway()
    with pytest.raises(RuntimeError, match="rejected"):
        gate.handle_provider("s1", {"message_type": "error", "data": {"code": "INVALID"}})
    gate.set_state("s1", "degraded", reason="translation_connection_lost")
    assert gate.states["s1"] == "degraded"

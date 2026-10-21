"""Linux AES67 ingress candidate: parsing, safety and gateway handoff tests.

All tests use synthetic SDP and mocked subprocesses, not real Q-SYS hardware.
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from gateway_stage2.aes67 import gst_receiver_command, parse_sdp, read_sdp
from gateway_stage2.core import Session
from gateway_stage2.source import PcmSource, source_factory


SDP = """v=0
o=- 1 1 IN IP4 192.0.2.10
s=EWR Gate C PA
c=IN IP4 239.69.10.21/32
t=0 0
m=audio 5004 RTP/AVP 96
a=rtpmap:96 L24/48000/1
a=ptime:1
"""


def test_mono_l24_sdp_builds_multicast_receiver():
    info = parse_sdp(SDP)
    assert (info.multicast, info.port, info.payload_type) == ("239.69.10.21", 5004, 96)
    argv = gst_receiver_command(info, interface="enp2s0")
    assert argv[0:2] == ["gst-launch-1.0", "-q"]
    assert "address=239.69.10.21" in argv
    assert "multicast-iface=enp2s0" in argv
    assert "rtpjitterbuffer" in argv
    assert "rtpL24depay" in argv
    assert "audio/x-raw,format=(string)S16LE,rate=(int)24000,channels=(int)1" in argv
    assert argv[-3:] == ["fdsink", "fd=1", "sync=false"]


def test_mono_l16_uses_16bit_depayloader():
    stream = parse_sdp(SDP.replace("L24", "L16"))
    assert "rtpL16depay" in gst_receiver_command(stream)


@pytest.mark.parametrize("bad", [
    SDP.replace("239.69.10.21", "192.0.2.10"),  # not multicast
    SDP.replace("239.69.10.21", "224.0.0.1"),  # reserved control group
    SDP.replace("5004", "0"),  # no RTP port
    SDP.replace("RTP/AVP 96", "RTP/AVP 128"),  # invalid dynamic payload
    SDP.replace("L24/48000/1", "L24/44100/1"),  # not 48k
    SDP.replace("L24/48000/1", "L24/48000/8"),  # mixing independent PA channels forbidden
    SDP.replace("a=rtpmap:96 L24/48000/1", ""),  # missing mapping
    SDP.replace("m=audio 5004 RTP/AVP 96", "m=video 5004 RTP/AVP 96"),  # wrong media
    SDP + "m=audio 5006 RTP/AVP 97\n",  # ambiguity
])
def test_unsupported_sdp_rejected(bad):
    with pytest.raises(ValueError):
        parse_sdp(bad)


def test_reject_invalid_interface():
    with pytest.raises(ValueError, match="interface"):
        gst_receiver_command(parse_sdp(SDP), "enp0s1; touch /tmp/pwn")


def test_source_factory_is_native_gateway_compatible(tmp_path, monkeypatch):
    file = tmp_path / "ewr_pa.sdp"
    file.write_text(SDP)
    assert read_sdp(str(file)).channels == 1
    session = Session.from_dict({
        "session_id": "ewr.pa", "source_id": "aes67-01",
        "source_language": "en", "tenant_id": "demo", "site_id": "EWR",
        "zone_id": "C", "flight_code": "",
        "source": f"aes67:{file}",
        "outputs": [{"channel_id": "fr-01", "language": "fr"}],
    })
    assert session.source == f"aes67:{file}"
    capture = []

    class FakeProcess:
        returncode = 0
        stdout = None

        async def wait(self):
            return 0

    async def fake_spawn(*argv, **kwargs):
        capture.append((argv, kwargs))
        return FakeProcess()

    monkeypatch.setenv("LX_AES67_INTERFACE", "enp3s0")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_spawn)

    async def exercise():
        async with source_factory(session.source) as opened:
            assert isinstance(opened, PcmSource)
            assert opened.aes67_mode
    asyncio.run(exercise())
    assert capture
    assert capture[0][0][0] == "gst-launch-1.0"
    assert "multicast-iface=enp3s0" in capture[0][0]


def test_missing_sdp_fails_closed(tmp_path):
    with pytest.raises(ValueError):
        read_sdp(str(tmp_path / "not-found.sdp"))

"""Candidate AES67 RTP/PCM input for the Linux Linguist-X gateway.

Only Q-SYS-compatible single-channel IPv4 multicast L16/L24 streams are
supported. A validated local SDP file provides the stream settings. This is
NOT an AES67 certification: PTP lock monitoring, SAP/RTSP discovery, NMOS,
multi-channel mapping, source-specific multicast, network redundancy and
hardware failover are outside this lab receiver.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path

IFACE = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")
RTPMAP = re.compile(r"^a=rtpmap:(\d+)\s+(L16|L24)/(\d+)(?:/(\d+))?$", re.I)


@dataclass(frozen=True)
class Aes67Stream:
    multicast: str
    port: int
    payload_type: int
    encoding: str
    rate: int
    channels: int


def parse_sdp(text: str) -> Aes67Stream:
    """Parse one manually commissioned RTP audio stream; reject ambiguity."""
    if len(text) > 16384 or "\x00" in text:
        raise ValueError("Invalid or oversized SDP.")
    lines = [line.strip() for line in text.replace("\r", "").split("\n") if line.strip()]
    audio_starts = [i for i, line in enumerate(lines) if line.startswith("m=audio ")]
    if len(audio_starts) != 1:
        raise ValueError("SDP must describe exactly one audio stream.")
    index = audio_starts[0]
    media_end = next((i for i in range(index + 1, len(lines))
                      if lines[i].startswith("m=")), len(lines))
    # A connection in the media section takes priority over the session default.
    session = lines[:index]
    media = lines[index:media_end]
    conn = next((line for line in media if line.startswith("c=")), None)
    if conn is None:
        conn = next((line for line in session if line.startswith("c=")), None)
    if conn is None:
        raise ValueError("SDP is missing the multicast connection address.")
    parts = conn.split()
    if len(parts) != 3 or parts[:2] != ["c=IN", "IP4"]:
        raise ValueError("Only IPv4 multicast RTP is supported.")
    addr = parts[2].split("/", 1)[0]
    try:
        ip = ipaddress.IPv4Address(addr)
    except ipaddress.AddressValueError as exc:
        raise ValueError("Invalid multicast address.") from exc
    if not ip.is_multicast or ip < ipaddress.IPv4Address("224.0.1.0"):
        raise ValueError("Expected a routable IPv4 multicast group.")

    params = media[0][2:].split()
    if len(params) != 4 or params[2] != "RTP/AVP":
        raise ValueError("Use a single RTP/AVP audio payload.")
    try:
        port = int(params[1])
        payload = int(params[3])
    except ValueError as exc:
        raise ValueError("Invalid RTP port or payload.") from exc
    if not (1024 <= port <= 65535 and 96 <= payload <= 127):
        raise ValueError("RTP port or dynamic payload type outside supported range.")

    maps = []
    for line in media[1:]:
        match = RTPMAP.fullmatch(line)
        if match and int(match.group(1)) == payload:
            maps.append(match)
    if len(maps) != 1:
        raise ValueError("Expected exactly one matching L16/L24 rtpmap.")
    match = maps[0]
    encoding = match.group(2).upper()
    rate = int(match.group(3))
    channels = int(match.group(4) or "1")
    if rate != 48000:
        raise ValueError("This receiver requires 48 kHz AES67-compatible PCM.")
    if channels != 1:
        raise ValueError("Commission one mono stream per source; multichannel mapping is not yet supported.")
    return Aes67Stream(str(ip), port, payload, encoding, rate, channels)


def read_sdp(path: str) -> Aes67Stream:
    file = Path(path).expanduser()
    if not file.is_file() or file.stat().st_size > 16384:
        raise ValueError("Missing or oversized AES67 SDP file.")
    return parse_sdp(file.read_text(encoding="utf-8"))


def gst_receiver_command(stream: Aes67Stream, interface: str = "") -> list[str]:
    """Safe argv for GStreamer: RTP depayload + jitter buffer -> 24 kHz PCM16."""
    if interface and not IFACE.fullmatch(interface):
        raise ValueError("Invalid multicast network-interface name.")
    caps = (
        "application/x-rtp,media=(string)audio,"
        f"clock-rate=(int){stream.rate},encoding-name=(string){stream.encoding},"
        f"encoding-params=(string){stream.channels},channels=(int){stream.channels},"
        f"payload=(int){stream.payload_type}"
    )
    source = ["udpsrc", f"address={stream.multicast}", f"port={stream.port}",
              "auto-multicast=true", "buffer-size=1048576"]
    if interface:
        source.append(f"multicast-iface={interface}")
    source.append(f"caps={caps}")
    return [
        "gst-launch-1.0", "-q", *source, "!",
        "rtpjitterbuffer", "latency=80", "drop-on-latency=true", "!",
        "rtpL24depay" if stream.encoding == "L24" else "rtpL16depay", "!",
        "audioconvert", "!", "audioresample", "!",
        "audio/x-raw,format=(string)S16LE,rate=(int)24000,channels=(int)1", "!",
        "fdsink", "fd=1", "sync=false",
    ]

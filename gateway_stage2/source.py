"""Controlled audio ingress. Capture is isolated from translation and passenger APIs.

ALSA and GStreamer AES67 receive adapters are commissioning candidates, not
certification of network clocking, Digigram hardware or output transmission.
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path

from .core import FRAME_BYTES

ALSA_DEVICE = re.compile(r"^[A-Za-z0-9,_.:-]{1,64}$")


class PcmSource:
    def __init__(self, spec: str):
        self.spec = spec
        self.process = None
        self.stream = None
        self.file_mode = spec.startswith("file:")
        self.aes67_mode = spec.startswith("aes67:")

    async def __aenter__(self):
        if self.file_mode:
            # Fixture-only mode, never a substitute for commissioned AES67 audio.
            if os.environ.get("LX_STAGE2_ENV", "development") == "production":
                raise RuntimeError("Recorded file fixtures are forbidden in production.")
            path = Path(self.spec[5:]).expanduser()
            if not path.is_file():
                raise FileNotFoundError("Configured PCM fixture file is missing.")
            self.stream = await asyncio.to_thread(path.open, "rb")
        else:
            if self.aes67_mode:
                from .aes67 import gst_receiver_command, read_sdp

                # Commissioned local SDP is the only authority for multicast settings.
                # GStreamer does RTP depayload, jitter handling and rate conversion.
                command = gst_receiver_command(
                    read_sdp(self.spec[6:]),
                    interface=os.environ.get("LX_AES67_INTERFACE", ""),
                )
            else:
                device = self.spec[5:]
                if not ALSA_DEVICE.fullmatch(device):
                    raise ValueError("Invalid ALSA capture device.")
                command = [
                    "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                    "-f", "alsa", "-i", device,
                    "-ac", "1", "-ar", "24000", "-f", "s16le", "pipe:1",
                ]
            self.process = await asyncio.create_subprocess_exec(
                *command, stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.stream is not None:
            await asyncio.to_thread(self.stream.close)
            self.stream = None
        if self.process is not None:
            self.process.terminate() if self.process.returncode is None else None
            try:
                await asyncio.wait_for(self.process.wait(), timeout=3)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            self.process = None

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        if self.stream is not None:
            started = time.monotonic()
            block = await asyncio.to_thread(self.stream.read, FRAME_BYTES)
            if not block:
                raise StopAsyncIteration
            if len(block) < FRAME_BYTES:
                block += bytes(FRAME_BYTES - len(block))
            # A recorded file must be paced to real time for Palabra.
            await asyncio.sleep(max(0, 0.32 - (time.monotonic() - started)))
            return block
        if self.process is None or self.process.stdout is None:
            raise StopAsyncIteration
        try:
            # ALSA/ffmpeg output is itself captured at real-time speed.
            return await self.process.stdout.readexactly(FRAME_BYTES)
        except asyncio.IncompleteReadError:
            raise RuntimeError("Configured audio input ended or lost signal.") from None


def source_factory(spec: str) -> PcmSource:
    return PcmSource(spec)

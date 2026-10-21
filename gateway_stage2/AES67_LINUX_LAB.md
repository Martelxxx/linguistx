# Built-in Linux AES67 Receiver — **lab candidate only**

This implements an AES67-compatible **receive-only** multicast RTP/PCM input for the
existing Linguist-X Stage 2 gateway; it does **not** require a separate
AES67 monitoring application. It uses GStreamer as a system library/tool for
RTP depayloading, jitter buffering, resampling, and PCM conversion. The
resulting **24 kHz / 16-bit / mono** PCM is delivered to the existing Palabra
streaming translation pipeline through its existing `source_factory`.

**Not production-certified.** No Q-SYS physical equipment, RTP timing,
PTP lock, network redundancy, voice quality, packet-loss recovery, or
passenger transport were validated in this change. The existing
`/v1/capabilities` still honestly reports `productionCertified:false`
and `liveAudio:false`. This does **not** create live public address audio
output to airport loudspeakers. Do not connect to a production airport
network until commissioned and authorized.

## Scope and important limitations

- One manually provisioned **IPv4 multicast RTP/AVP mono 48 kHz** stream,
  dynamic RTP payload type 96–127, L16 or L24. One source per configured
  session. This is compatible with a **configured mono Q-SYS AES67 TX**.
- No SAP discovery, RTSP, NMOS, AES67 PTP lock monitoring, SMPTE 2022-7
  redundancy, source-specific multicast, AES67 output transmission, or
  multichannel demultiplexing.
- Use Q-SYS AES67 Transmitter to publish a **single channel** for the lab
  demonstration. Never downmix unrelated PA channels as though they were
  one announcement.
- Palabra/source-session uptime is not proof packets are received. A
  separate audio level/packet-counter integration with Super Admin and
  actual end-to-end Q-SYS commissioning are follow-up release gates.
- No edits were made to the independent Windows v3 Partner Test Kit or the
  Base44 simulation-only publication receiver.
- This gateway is designed for **Linux** with systemd; browser-based
  Super Admin management can remain remote.

## Lab setup (Ubuntu/Debian)

1. Confirm with the integrator and the network administrator that the
   dedicated Linguist-X Ethernet interface can receive Q-SYS AES67
   multicast, and that IGMP snooping/routing and network QoS are correct.
   Q-SYS and the receiver must use compatible RTP/SDP parameters. Do not
   assume that an ordinary enterprise LAN forwards multicast by default.
2. Install the GStreamer runtime and RTP plugins:
   ```bash
   sudo apt-get update
   sudo apt-get install -y gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good
   gst-inspect-1.0 rtpL24depay
   gst-inspect-1.0 rtpL16depay
   ```
3. Copy `examples/qsys-ewr-c-pa.sdp` to
   `/etc/linguistx/streams/ewr-c-pa.sdp` and **replace** its example
   multicast IP/port/payload/encoding with the values configured in Q-SYS.
   The example IP addresses are **not live or discovered addresses**.
4. Configure your Stage 2 gateway JSON, for example starting from
   `examples/aes67-lab-config.json`, with source:
   ```json
   "source": "aes67:/etc/linguistx/streams/ewr-c-pa.sdp"
   ```
5. Optionally set `LX_AES67_INTERFACE=enp2s0` to select the receiving
   Ethernet interface. Set existing `LX_STAGE2_CONFIG`,
   `LX_GATEWAY_TOKEN`, `PALABRA_API_KEY`, and `LX_STAGE2_RUN=1`
   using the existing secured environment file. Do not commit secrets.
6. Deploy/restart the existing
   `gateway_stage2/linguistx-gateway-stage2.service` after proper local
   permissions and networking review.

When a source is configured as `aes67:`, `PcmSource` launches
`gst-launch-1.0` **without a shell**, subscribes to the configured
multicast group, depayloads/jitter-buffers RTP L16/L24, converts 48 kHz
mono to 24 kHz signed 16-bit PCM, and streams 320 ms blocks into the
existing Palabra session.

## Lab verification

- Run `python3 -m pytest -q tests/test_aes67_ingress.py tests/test_stage2_gateway.py`.
- Commission Q-SYS transmitter with mono audio and matching SDP.
- Verify RTP packets are arriving on the authorized network interface
  and the GStreamer pipeline is producing PCM; confirm real transcripts.
- Induce loss/disconnect and verify degraded/recovery behavior.
- Check actual packet loss, timestamp drift, latency, announcement
  boundaries and output quality before any release decision.
- Never use the availability of the health endpoint alone as proof of
  received audio or successful passenger playback.

**Next integration:** add ingress packet/level/PTP metrics and source
selection to Super Admin, then a new authorized live-announcement
publishing contract in Base44. The current Base44 receiver only accepts
simulated announcements.

### Operator-facing API

The gateway now exposes authenticated `GET /v1/ingress/sources`.
It reports configured stream metadata and translation session state, while
explicitly setting `audio_receipt_verified=false` and
`media_telemetry_available=false`. These flags must not be interpreted
as stream/packet or Q-SYS health checks. Super Admin UI integration and live
media telemetry are follow-up work.

# Stage 2 Palabra Gateway — Engineering Addendum

Status: isolated candidate runtime, **not production-ready or hardware-certified**.

The existing Product Requirements Draft 0.1 names Wordly. This Stage 2 change substitutes Palabra as the cloud translation provider, but does not presume Wordly-specific capabilities, rates, contracts, or acceptance evidence apply to Palabra.

## Stage 2 additions required

1. Persistent Linux service, independent of any web browser or management-cloud connection.
2. One source-to-Palabra session per configured AES67 input, not per passenger; many output languages per session.
3. Source, tenant, site, zone, flight and announcement-ID correlation. Keep language assignments inside permanent AES67 channel identities.
4. Enforce 64 AES67 inputs / 64 outputs as the appliance hardware design ceiling, unequal fixed/dynamic language pools, never resize active output pools through the local PA API.
5. Documented 48 kHz / 24-bit AES67 reception and output, PTP clock lock, SDP/NMOS and SMPTE 2022-7 behavior. Translation send/receive uses Palabra's declared audio format (candidate: 24-kHz signed 16-bit mono).
6. Subscriber fan-out must be centrally translated once, authenticated/scoped to the correct tenant/site/session/language and bounded under slow-client backpressure. The passenger device must not perform translation.
7. Emergency/priority interruption, safe silence on unavailable output, no stale audio, per-language failure/partial states, message-boundary evidence.
8. Standby with distributed fencing and no duplicate output, <=10 second takeover target, and authorized failback only.
9. Tamper-evident evidence of original source, translated text, actual audio transmitted to each AES67 output, per-channel status, daily cloud uploads, full retention/security/role controls.
10. Source and channel isolation, reconnect, session quota limits, alarms and runtime service recovery.
11. Commercial validation of 20 simultaneous languages, per-input session concurrency, provider quotas, service quality and rights to redistribute translated output to large passenger populations.

## What this package implements now

- Independent, opt-in Linux/ASGI package under gateway_stage2, separate from passenger v95 and the Base44 Hub.
- JSON configuration with one site/tenant, up to 64 source/output identities, provider-concurrency guard currently limited to 10 source sessions pending Palabra verification.
- One streaming Palabra WebSocket per configured source, multi-target text and audio events from that one session.
- 24-kHz mono PCM ingress from a controlled ALSA/ffmpeg adapter; dev-only prerecorded raw PCM fixture.
- Bounded session/language SSE event fan-out, guest grants with short TTL and a server-side guest API contract matching the existing AV-ation adapter.
- App health/ready states, per-session connection degradation and retry isolation, append-only metadata hash-chain journal.
- Mock-based tests for channel bounds, subscriber isolation, security, protocol construction and evidence metadata.
- Candidate systemd service unit, secure environment-only credential configuration and example source map.

## Not implemented / production release blockers

- Verified Digigram ALP-AES67-64 Linux capture/multicast, proper 48 kHz 24-bit routing, stable NMOS IDs, PTP and actual 64-channel AES67 transmitter output.
- Measured Palabra multi-language speech and 8-input/64-output concurrency, contractual redistribution rights.
- Production HA fencing, 2022-7 redundant paths, failover target, cross-site cloud management.
- Capturing source and physical transmitted audio, encrypted source/archive storage, complete manifest, cloud off-peak upload and one-year post-expiration retention.
- Real mobile subscriber SSE proxy/playback, multi-replica shared guest state, per-tenant distributed admission control and production TLS/device identity.
- Full incident workflow, signed OTA, security review, independent performance load testing.

The existing journal records **metadata only**; provider audio received does NOT mean downstream AES67 audio transmitted. Never present a hash or provider receipt as proof an amplifier/loudspeaker played an announcement.

## Lab execution

Requirements: Python 3.11+, ffmpeg, gateway_stage2/requirements.txt, a real Speech-to-Speech-capable Palabra key, approved ALSA device mapping or dev-only raw PCM fixture. Do not use on a customer audio network until the input mapping is commissioned.

Set server-only environment variables:

- LX_STAGE2_CONFIG=/absolute/path/to/approved-config.json
- LX_GATEWAY_TOKEN=at-least-32-random-characters
- PALABRA_API_KEY=your-secret-key
- LX_STAGE2_JOURNAL=/var/lib/linguistx/gateway-events.sqlite3
- LX_STAGE2_RUN=1
- LX_STAGE2_ENV=development or production

Then run: uvicorn gateway_stage2.app:app --host 127.0.0.1 --port 8789 --workers 1

Note: LX_STAGE2_RUN is unset by default; translation will not auto-start. The service unit listens only on loopback. The guest event API is intended for the trusted server-side passenger proxy, not for directly exposing bearer tokens in browser JavaScript.

## Acceptance checklist

- [x] Configuration/identity bounds, multi-language fan-out, guest scope and audit safety in automated tests.
- [x] Staged, separate codepath, opt-in startup, no changes to production passenger UI.
- [ ] Live Palabra API and voice verification across 20 languages.
- [ ] Real Digigram card / AES67 input, output, PTP and 2022-7 commissioned.
- [ ] Provider/per-source licensing and 8-in/64-out concurrency verified.
- [ ] 10-second failover and duplicate prevention demonstrated.
- [ ] Signed complete recording/evidence, cloud storage and retention tested.
- [ ] Secure passenger delivery at volume, HA, and customer site/zone authorization tested.

This source package is the Stage 2 development foundation, not the completed production appliance.

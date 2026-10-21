# Unified AES67 module: Windows / macOS / Linux

**Single source:** Every platform uses the same \`gateway_stage2\` Python
application with GStreamer RTP audio depayloading and the same admin route:
\`http://127.0.0.1:8789/super-admin/audio-inputs\`.

Launch scripts are intentionally thin OS adapters, **not separate forks**.
They must not gain platform-specific permissions or simulate working media.

| Capability | Windows | macOS | Linux |
|---|---|---|---|
| Shared Python gateway and provider pipeline | Same | Same | Same |
| AES67 L16/L24 48 kHz multicast RX -> PCM16 24 kHz | Same source | Same source | Same source |
| Authenticated Audio Input Super Admin module | Same | Same | Same |
| Manual Q-SYS multicast stream settings | Same | Same | Same |
| Decoded input audio level and age | Same | Same | Same |
| Existing guest APIs and language fan-out | Same | Same | Same |
| Automatic SAP / NMOS / PTP diagnostics | Not implemented | Not implemented | Not implemented |
| Physical Q-SYS validation | Not performed | Not performed | Not performed |
| Existing Windows v3 / macOS Super Admin UI integrated | **NOT YET** | **NOT YET** | **NOT YET** |

Installation requirements: Python 3.11+, platform-specific installation of
GStreamer tools plus good/base RTP plugins, working multicast network path,
and optional Palabra credentials for real translation.

Windows and macOS: install GStreamer, then run the platform launch script
from the repository's root. Linux: install GStreamer as described in
\`gateway_stage2/AES67_LINUX_LAB.md\`, run \`platform/START_LINUX.sh\`.
All scripts install the same pinned \`gateway_stage2/requirements.txt\`.

Data lives in the OS-appropriate user application-data directory. The
initial test SDP is **only an example** and needs Q-SYS's actual multicast
address, payload and port. The test gateway defaults to CONFIGURATION-ONLY
mode; \`LX_STAGE2_RUN=1\` plus credentials and commissioned network are
needed to process real audio.

**Critical distribution limitation:** The actual Windows v3 One Launch ZIP
and Mac Super Admin application source are not included in this repository.
Their Library ZIP contents were inaccessible for byte-level editing. These
scripts **do not rebuild those existing applications**, and the admin
audio-inputs screen is a separate shared module until the original console's
navigation/authentication source can be patched. Do not market these as
complete replacements or as certified AES67 integrations.

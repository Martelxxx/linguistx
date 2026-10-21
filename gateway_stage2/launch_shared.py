"""One local test launcher for Windows, macOS and Linux.

Not a replacement for the existing Windows v3 or Mac Super Admin distributions.
The identical AES67 gateway+audio administration module is used by all three OSes.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path


def data_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Linguist-X" / "AES67"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Linguist-X" / "AES67"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "linguist-x" / "aes67"


def initialize(target: Path) -> tuple[Path, Path]:
    target.mkdir(parents=True, exist_ok=True)
    streams = target / "streams"
    streams.mkdir(parents=True, exist_ok=True)
    from .aes67 import make_commissioned_sdp

    placeholder = streams / "qsys-test.sdp"
    if not placeholder.exists():
        placeholder.write_text(make_commissioned_sdp("239.69.10.21", 5004, 96, "L24"),
                               encoding="utf-8")
    conf = target / "sessions.json"
    if not conf.exists():
        conf.write_text(json.dumps({
            "sessions": [{
                "session_id": "lab-qsys-input", "source_id": "qsys-test",
                "source_language": "en", "tenant_id": "lab",
                "site_id": "EWR", "zone_id": "Lab", "flight_code": "",
                "source": "aes67:" + str(placeholder.resolve()),
                "outputs": [{"channel_id": "lab-fr", "language": "fr"},
                            {"channel_id": "lab-es", "language": "es"}],
            }]
        }, indent=2) + "\n", encoding="utf-8")
    token = target / "admin.token"
    if not token.exists():
        descriptor = os.open(str(token), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(secrets.token_urlsafe(48))
    return conf, token


def main() -> None:
    location = data_dir()
    cfg, token_file = initialize(location)
    token = token_file.read_text(encoding="utf-8").strip()
    os.environ.setdefault("LX_STAGE2_CONFIG", str(cfg))
    os.environ.setdefault("LX_GATEWAY_TOKEN", token)
    os.environ.setdefault("LX_AES67_SDP_DIR", str(location / "streams"))
    os.environ.setdefault("LX_STAGE2_JOURNAL", str(location / "events.sqlite3"))
    # Disabled by default: enabling a real provider feed is an explicit act.
    os.environ.setdefault("LX_STAGE2_RUN", "0")
    print("=" * 55)
    print("Linguist-X Unified AES67 Gateway · Lab")
    print("OS:", sys.platform)
    print("Audio inputs: http://127.0.0.1:8789/super-admin/audio-inputs")
    print("Admin token (keep private):", token)
    print("Configuration file:", cfg)
    print("Test stream settings:", location / "streams" / "qsys-test.sdp")
    print("Mode:", "LIVE (requires commissioned Q-SYS and Palabra)"
          if os.environ["LX_STAGE2_RUN"] == "1" else "CONFIGURATION ONLY")
    print("This is a shared backend module, NOT the full Windows/Mac v3 Super Admin.")
    print("=" * 55)
    import uvicorn

    uvicorn.run("gateway_stage2.app:app", host="127.0.0.1", port=8789, workers=1)


if __name__ == "__main__":
    main()

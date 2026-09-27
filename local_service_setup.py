"""Private, one-time provider-key setup for the LOCAL passenger preview.

DEVNOTE: The regression fixed here was in start.py: v78 passed LX_NO_SETUP=1,
which bypassed the existing hidden provider-key setup in run.py. This helper
restores that one-time workflow without silently searching historic folders.

Never call this from the public browser, an HTTP route, CI or production. This
module does not check provider entitlements or make network requests. It writes
ONLY new keys explicitly typed into the local Terminal; environment-provided
keys are usable at runtime but are not copied into .env. The three provider
keys are independent of the AV-ation/Wordly integration contract.
"""
from __future__ import annotations

import ast
import getpass
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Callable, Mapping

SERVICES = (
    ('AVIATIONSTACK_KEY', 'Flight lookup (Aviationstack)'),
    ('WEATHERAPI_KEY', 'Destination weather (WeatherAPI)'),
    ('OPENAI_API_KEY', 'Demo speech / voice / scanning (OpenAI)'),
)
NAMES = {name for name, _ in SERVICES}

# A private file in the user's HOME survives replacing/unzipping the application.
# The public source and all release manifests NEVER include its contents.
PRIVATE_FOLDER = '.linguist-x'
PRIVATE_FILE = 'provider_keys.env'
PRIVATE_BOOTSTRAP = 'private_provider_keys.py'


def user_key_file(home: Path | None = None) -> Path:
    """Stable per-user credentials path; never inside an extracted release."""
    base = Path.home() if home is None else Path(home)
    return base / PRIVATE_FOLDER / PRIVATE_FILE


def _read_key_file(path: Path) -> dict[str, str]:
    """Read ONLY the three known keys; never follow an intentional symlink."""
    if path.is_symlink() or path.parent.is_symlink():
        raise OSError('Refusing a symlinked private credentials location.')
    return _configured_from_text(path.read_text(encoding='utf-8')) if path.is_file() else {}


def read_user_keys(*, home: Path | None = None) -> dict[str, str]:
    """Return user-specific keys; caller must not print or log these values."""
    return _read_key_file(user_key_file(home))


def _prepare_private_directory(path: Path) -> None:
    folder = path.parent
    if folder.is_symlink() or path.is_symlink():
        raise OSError('Refusing a symlinked private credentials location.')
    if folder.exists() and not folder.is_dir():
        raise OSError('Private credentials directory must be a directory.')
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name == 'posix':
        if folder.stat().st_uid != os.getuid():
            raise OSError('Private credentials directory is not owned by this user.')
        os.chmod(folder, 0o700)


def save_user_keys(updates: dict[str, str], *, home: Path | None = None) -> Path:
    """Save only validated credentials, with owner-only directory/file access."""
    if not updates or any(k not in NAMES or not valid_key(v) for k, v in updates.items()):
        raise ValueError('Invalid local service key input.')
    path = user_key_file(home)
    _prepare_private_directory(path)
    _write_keys(path, updates)
    return path


def install_private_bootstrap(directory: Path, *, home: Path | None = None) -> bool:
    """One-time private personal ZIP handoff; install then remove the loose secret file.

    The bootstrap is NOT an HTTP route, imported module, GitHub source or part of
    any public release. Parsing literals instead of importing prevents execution.
    ZIP files containing it must be treated as private and never shared.
    """
    bootstrap = directory / PRIVATE_BOOTSTRAP
    if bootstrap.is_symlink():
        raise OSError('Refusing a symlinked private credentials bootstrap.')
    if not bootstrap.is_file():
        return False
    parsed = ast.parse(bootstrap.read_text(encoding='utf-8'), filename=PRIVATE_BOOTSTRAP)
    if (len(parsed.body) != 1 or not isinstance(parsed.body[0], ast.Assign)
            or len(parsed.body[0].targets) != 1
            or not isinstance(parsed.body[0].targets[0], ast.Name)
            or parsed.body[0].targets[0].id != 'PRIVATE_KEYS'):
        raise ValueError('Private credential bootstrap must contain only PRIVATE_KEYS.')
    content = ast.literal_eval(parsed.body[0].value)
    if (not isinstance(content, dict) or set(content) != NAMES
            or any(not isinstance(v, str) or not valid_key(v) for v in content.values())):
        raise ValueError('Private credential bootstrap has invalid credentials.')
    # Load all three keys atomically. If installation fails, retain the handoff
    # so the user can retry; delete it only after a successful private save.
    save_user_keys(content, home=home)
    bootstrap.unlink()
    return True


def valid_key(value: str) -> bool:
    """Detect empty/example entries without guessing whether a live key works."""
    value = str(value).strip().strip('"\'')
    return bool(value and not value.startswith('YOUR_')
                and value not in ('CHANGEME', '<KEY>')
                and bool(re.fullmatch(r'[A-Za-z0-9_.-]{4,1024}', value)))


def _configured_from_text(content: str) -> dict[str, str]:
    """Read known keys only; preserve all other .env lines on replacement."""
    found: dict[str, str] = {}
    for raw in content.splitlines():
        line = raw.strip().lstrip('\ufeff')
        if line.startswith('export '):
            line = line[7:]
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        value = value.strip().strip('"\'')
        if key.strip() in NAMES and valid_key(value):
            found[key.strip()] = value
    return found


def _write_keys(path: Path, updates: dict[str, str]) -> None:
    """Atomically write owner-only .env; reject symlinks and retain gateway settings.

    Never print or log updates. If the old file is present, preserve all lines
    outside the three managed provider keys, including gateway config. Place a
    temporary file in the same directory and replace atomically; never ship it.
    """
    if path.is_symlink():
        raise OSError('Refusing to overwrite a symlinked .env file.')
    old_lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    retained: list[str] = []
    for line in old_lines:
        candidate = line.strip()
        if candidate.startswith('export '):
            candidate = candidate[7:].lstrip()
        if candidate.split('=', 1)[0].strip() not in updates:
            retained.append(line)
    retained.extend(f'{name}={updates[name]}' for name, _ in SERVICES if name in updates)
    tmp: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', prefix='.lx-services-', suffix='.tmp',
            dir=path.parent, delete=False
        ) as file:
            tmp = file.name
            os.fchmod(file.fileno(), stat.S_IRUSR | stat.S_IWUSR)
            file.write('\n'.join(retained) + '\n')
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
        tmp = None
        os.chmod(path, 0o600)
    finally:
        if tmp is not None:
            Path(tmp).unlink(missing_ok=True)


def configure_local_services(
    directory: Path,
    environment: Mapping[str, str],
    *,
    replace: bool = False,
    prompt: Callable[[str], str] | None = None,
    is_tty: bool | None = None,
    tell: Callable[[str], None] = print,
    persistent: bool = False,
    home: Path | None = None,
) -> dict[str, bool]:
    """Prompt privately for missing or deliberately replaced local services.

    `replace` enables credential rotation (`python3 start.py --configure`).
    Pressing Enter preserves an existing value; no key is displayed. Callers
    must never echo the return value, since it reports presence *only*.
    """
    legacy = directory / '.env'
    if legacy.is_symlink():
        raise OSError('Refusing to use a symlinked .env file.')
    legacy_keys = _read_key_file(legacy)
    path = user_key_file(home) if persistent else legacy
    configured_file = read_user_keys(home=home) if persistent else legacy_keys
    # Automatically migrate old per-release .env credentials on a local launch;
    # do not delete the old .env because it may contain unrelated gateway setup.
    if persistent:
        updates = {k: v for k, v in legacy_keys.items()
                   if k not in configured_file and not valid_key(environment.get(k, ''))}
        if updates:
            save_user_keys(updates, home=home)
            configured_file.update(updates)
    existing = {name: (valid_key(environment.get(name, '')) or name in configured_file
                       or name in legacy_keys)
                for name, _ in SERVICES}
    interactive = sys.stdin.isatty() if is_tty is None else is_tty
    if not interactive:
        if replace:
            raise ValueError('Key replacement requires an interactive local Terminal.')
        return existing
    needs = [(name, label) for name, label in SERVICES if replace or not existing[name]]
    if not needs:
        tell('Local flight, weather and voice keys are already configured. No key entry needed.')
        return existing
    tell('Linguist-X local service setup. Key entry is hidden; press Enter to skip.')
    if replace:
        tell('Replacing a key overwrites its saved value; Enter retains the current value.')
    hidden_prompt = getpass.getpass if prompt is None else prompt
    updates: dict[str, str] = {}
    for name, label in needs:
        try:
            entry = hidden_prompt(f'{label} — {name}: ').strip()
        except (EOFError, KeyboardInterrupt):
            tell('Key entry cancelled; existing settings kept.')
            break
        if not entry:
            continue
        if not valid_key(entry):
            tell(f'Invalid {name} format; value skipped.')
            continue
        updates[name] = entry
    if updates:
        if persistent:
            save_user_keys(updates, home=home)
            tell('Provider keys saved to your private user profile. Future versions will reuse them.')
        else:
            _write_keys(path, updates)
            tell('Local .env saved with owner-only permissions. Keys were not printed.')
    for name in updates:
        existing[name] = True
    missing = [label for name, label in SERVICES if not existing[name]]
    if missing:
        tell('Not configured: ' + ', '.join(missing) + '. These features will remain unavailable.')
    return existing

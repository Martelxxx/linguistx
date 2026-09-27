# Linguist-X Passenger v84 — Persistent Local Provider Credentials

## Root cause and change
v79–v83 persisted provider credentials inside each extracted release directory's `.env`.
A new downloaded ZIP normally creates another directory; these keys were not reused.

v84 reads three optional provider credentials from `~/.linguist-x/provider_keys.env`
using owner-only permissions (0700 directory and 0600 file, where supported).
The source order is explicit environment > stable user profile > historical local `.env`.
The regular local launcher migrates historical `.env` provider credentials without deleting
unrelated gateway settings. Direct `run.py` uses the same persistent store; production
runtime does not consult the user's HOME store.

This user's personalized private package contains an ignored `private_provider_keys.py`
with literal keys supplied by the user. On the first real `python3 start.py` invocation,
that handoff is parsed without execution, saved to the user's private profile, and removed
from the extracted folder. The ZIP itself remains SECRET-BEARING and must not be shared.
No service API, browser route, development documentation or GitHub upload exposes it.
Git and Docker ignore the private handoff. Public SHA-256 release manifest excludes it.

## Acceptance scope
- Synthetic first launch: installs the three local keys, deletes loose handoff, starts server.
- Synthetic subsequent launch: starts without key entry.
- Synthetic migration: preserves unrelated settings in historical `.env`.
- Existing Passenger UI and v83 Guide Me CSS/JS are unchanged in this release.
- Production uses deployed environment-injected credentials only.
- API-key entitlements, provider responses and mobile compass behavior are NOT proven by these tests.

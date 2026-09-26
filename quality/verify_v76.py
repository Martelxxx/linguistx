"""Compatibility entrypoint retained for developers following v76 documentation.

v77 changed source comments and the internal checklist, so the old byte-hash verifier is no
longer authoritative. Running this file executes the current v78 release verification instead.
"""
from __future__ import annotations
import runpy
from pathlib import Path

print('NOTE: quality/verify_v76.py is superseded; running quality/verify_v78.py')
runpy.run_path(str(Path(__file__).with_name('verify_v78.py')), run_name='__main__')

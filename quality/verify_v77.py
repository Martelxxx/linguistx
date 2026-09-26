"""Compatibility entry point: v77 verification is superseded by v78.

Use verify_v77_historical.py only against an actual v77 package snapshot.
"""
from pathlib import Path
import runpy
print('NOTE: quality/verify_v77.py is superseded; running quality/verify_v78.py')
runpy.run_path(str(Path(__file__).with_name('verify_v78.py')), run_name='__main__')

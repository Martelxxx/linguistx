"""v88 regression: Aviationstack rotation survives app-directory replacement.

Uses fictitious keys; no user credential is logged, imported, or hardcoded here.
"""
from __future__ import annotations
import ast
import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import local_service_setup as setup

ROOT=Path(__file__).resolve().parents[1]
PUBLIC_FILES=('index.html', 'passenger-only.html','wayfinder.css','wayfinder.js','sw.js')

class V88PersistentKeyRotation(unittest.TestCase):
    def test_fake_key_rotation_updates_one_service_and_requires_no_reentry(self):
        original={'OPENAI_API_KEY':'FAKE_OPENAI_0134',
                  'AVIATIONSTACK_KEY':'FAKE_FLIGHT_OLD_812',
                  'WEATHERAPI_KEY':'FAKE_WEATHER_502'}
        replacement=dict(original,AVIATIONSTACK_KEY='FAKE_FLIGHT_NEW_927')
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            home=base/'home'; home.mkdir()
            release=base/'new_version'; release.mkdir()
            setup.save_user_keys(original,home=home)
            handoff=release/setup.PRIVATE_BOOTSTRAP
            handoff.write_text('PRIVATE_KEYS = '+repr(replacement)+'\n')
            self.assertTrue(setup.install_private_bootstrap(release,home=home))
            self.assertFalse(handoff.exists())
            self.assertEqual(setup.read_user_keys(home=home),replacement)
            saved=setup.user_key_file(home)
            if os.name=='posix':
                self.assertEqual(stat.S_IMODE(saved.stat().st_mode),0o600)
                self.assertEqual(stat.S_IMODE(saved.parent.stat().st_mode),0o700)
            # A fresh extracted release uses persistent storage and does not ask
            # again for the newly rotated flight credential or the other keys.
            second=base/'future_release'; second.mkdir()
            def fail_prompt(label):
                self.fail(f'Unexpected secret prompt for {label}')
            with patch.dict(os.environ,{},clear=True):
                configured=setup.configure_local_services(second,{},persistent=True,
                    home=home,is_tty=True,prompt=fail_prompt,tell=lambda _:None)
            self.assertTrue(all(configured.values()))

    def test_personal_bootstrap_is_literal_only_and_public_source_does_not_hold_keys(self):
        bootstrap=ROOT/setup.PRIVATE_BOOTSTRAP
        if not bootstrap.is_file():
            self.assertIn(bootstrap.name,(ROOT/'.gitignore').read_text())
            self.assertIn(bootstrap.name,(ROOT/'.dockerignore').read_text())
            self.assertNotIn(bootstrap.name,(ROOT/'RELEASE_MANIFEST_v88.sha256').read_text())
            self.assertFalse((ROOT/'.env').exists())
            self.skipTest('Private bootstrap intentionally excluded from GitHub source')
        tree=ast.parse(bootstrap.read_text(encoding='utf-8'))
        self.assertEqual(len(tree.body),1)
        keys=ast.literal_eval(tree.body[0].value)
        self.assertEqual(set(keys),setup.NAMES)
        self.assertTrue(all(setup.valid_key(value) for value in keys.values()))
        manifest=(ROOT/'RELEASE_MANIFEST_v88.sha256').read_text(encoding='utf-8')
        self.assertNotIn(bootstrap.name,manifest)
        for file in (*PUBLIC_FILES,'start.py','run.py','local_service_setup.py'):
            body=(ROOT/file).read_text(encoding='utf-8')
            for secret in keys.values():
                self.assertNotIn(secret,body,f'Credential present in {file}')
        self.assertFalse((ROOT/'.env').exists())
        self.assertIn(bootstrap.name,(ROOT/'.gitignore').read_text())

if __name__=='__main__': unittest.main()

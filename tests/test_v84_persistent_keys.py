"""Credential handoff and durable user-local persistence, tested with fake secrets."""
from __future__ import annotations
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import local_service_setup as services

FAKE_KEYS = {
    'OPENAI_API_KEY': 'OPENAI_TEST_899',
    'AVIATIONSTACK_KEY': 'FLIGHT_TEST_245',
    'WEATHERAPI_KEY': 'WEATHER_TEST_623',
}


class PermanentLocalCredentials(unittest.TestCase):
    def test_private_handoff_installs_once_and_survives_release_folder_replacement(self):
        with tempfile.TemporaryDirectory() as temp:
            home, release_a, release_b = (Path(temp) / n for n in ('home', 'release-a', 'release-b'))
            for path in (home, release_a, release_b):
                path.mkdir()
            handoff = release_a / services.PRIVATE_BOOTSTRAP
            handoff.write_text('PRIVATE_KEYS = ' + repr(FAKE_KEYS) + '\n', encoding='utf-8')
            self.assertTrue(services.install_private_bootstrap(release_a, home=home))
            self.assertFalse(handoff.exists(), 'One-time loose private source must be deleted.')
            self.assertFalse(services.install_private_bootstrap(release_b, home=home))
            self.assertEqual(services.read_user_keys(home=home), FAKE_KEYS)
            private_file = services.user_key_file(home)
            self.assertTrue(private_file.is_file())
            if os.name == 'posix':
                self.assertEqual(stat.S_IMODE(private_file.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(private_file.parent.stat().st_mode), 0o700)
            messages = []
            configured = services.configure_local_services(
                release_b, {}, persistent=True, home=home, is_tty=True,
                prompt=lambda _: self.fail('No re-entry on another release'), tell=messages.append)
            self.assertTrue(all(configured.values()))
            self.assertTrue(any('No key entry needed' in message for message in messages))

    def test_previous_release_env_is_migrated_without_prompt_or_deleting_gateway_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            release, home = base / 'old-release', base / 'home'
            release.mkdir(); home.mkdir()
            legacy_text = ('AVIATIONSTACK_KEY=FLIGHT_TEST_245\n'
                           'OPENAI_API_KEY=OPENAI_TEST_899\n'
                           'WEATHERAPI_KEY=WEATHER_TEST_623\n'
                           'LX_GATEWAY_URL=https://example.test\n')
            (release / '.env').write_text(legacy_text)
            configured = services.configure_local_services(release, {}, persistent=True,
                home=home, is_tty=False)
            self.assertTrue(all(configured.values()))
            self.assertEqual(services.read_user_keys(home=home), FAKE_KEYS)
            self.assertEqual((release / '.env').read_text(), legacy_text)

    def test_environment_credentials_do_not_get_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / 'home'
            release = Path(temp) / 'release'
            home.mkdir(); release.mkdir()
            present = services.configure_local_services(
                release, FAKE_KEYS, persistent=True, home=home, is_tty=True,
                prompt=lambda _: self.fail('No prompt for injected credentials'))
            self.assertTrue(all(present.values()))
            self.assertFalse(services.user_key_file(home).exists())

    def test_symlinks_are_rejected_and_invalid_handoff_remains_unexecuted(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / 'home'
            release = Path(temp) / 'release'
            home.mkdir(); release.mkdir()
            handoff = release / services.PRIVATE_BOOTSTRAP
            marker = release / 'untrusted-executed'
            handoff.write_text(f'PRIVATE_KEYS = __import__("os").system("touch {marker}")\n')
            with self.assertRaises(ValueError):
                services.install_private_bootstrap(release, home=home)
            self.assertFalse(marker.exists())
            self.assertFalse(services.user_key_file(home).exists())
            handoff.unlink()
            destination = release / 'fake-source.py'
            destination.write_text('PRIVATE_KEYS = ' + repr(FAKE_KEYS))
            handoff.symlink_to(destination)
            with self.assertRaises(OSError):
                services.install_private_bootstrap(release, home=home)
            self.assertFalse(services.user_key_file(home).exists())

    def test_server_loads_saved_keys_noninteractively_and_production_ignores_store(self):
        import run
        from runtime_security import Settings
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            fake_home, release = base / 'home', base / 'release'
            fake_home.mkdir(); release.mkdir()
            services.save_user_keys(FAKE_KEYS, home=fake_home)
            with patch.object(run, 'KEY_FILE', release / '.env'), \
                 patch.object(run, 'read_user_keys', lambda: services.read_user_keys(home=fake_home)), \
                 patch.object(run, 'SETTINGS', Settings('development', 8765, False, False, '')), \
                 patch.object(run.sys.stdin, 'isatty', return_value=False), \
                 patch.dict(os.environ, {'LX_NO_SETUP': '1'}, clear=True):
                self.assertEqual(run._local_config(), FAKE_KEYS)
            with patch.object(run, 'KEY_FILE', release / '.env'), \
                 patch.object(run, 'read_user_keys', lambda: self.fail('No HOME secrets in production')), \
                 patch.object(run, 'SETTINGS', Settings('production', 8765, False, False, '')), \
                 patch.dict(os.environ, {'LX_NO_SETUP': '1'}, clear=True):
                self.assertEqual(run._local_config(), {})

    def test_personal_bootstrap_is_excluded_from_github_and_not_in_public_manifest(self):
        root = Path(__file__).resolve().parents[1]
        self.assertIn('private_provider_keys.py', (root / '.gitignore').read_text())
        self.assertNotIn('private_provider_keys.py',
                         (root / 'RELEASE_MANIFEST_v84.sha256').read_text())
        for script in (root/'start.py', root/'run.py', root/'local_service_setup.py'):
            self.assertNotIn('OPENAI_TEST_899', script.read_text())


if __name__ == '__main__':
    unittest.main()

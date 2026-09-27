"""v79 regression: local service recovery without embedding live keys or changing UI."""
from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import local_service_setup as setup
import start

ROOT = Path(__file__).resolve().parents[1]


class LocalServiceRecovery(unittest.TestCase):
    def test_first_launch_prompts_all_missing_and_stores_only_locally(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            entries = iter(('FLIGHT_TEST_123', 'WEATHER_TEST_456', 'VOICE_TEST_789'))
            messages = []
            present = setup.configure_local_services(
                folder, {}, is_tty=True, prompt=lambda label: next(entries), tell=messages.append)
            self.assertTrue(all(present.values()))
            data = (folder / '.env').read_text()
            self.assertIn('AVIATIONSTACK_KEY=FLIGHT_TEST_123', data)
            self.assertIn('WEATHERAPI_KEY=WEATHER_TEST_456', data)
            self.assertIn('OPENAI_API_KEY=VOICE_TEST_789', data)
            self.assertNotIn('TEST_123', '\n'.join(messages))
            self.assertNotIn('TEST_456', '\n'.join(messages))
            self.assertNotIn('TEST_789', '\n'.join(messages))
            self.assertEqual(stat.S_IMODE((folder / '.env').stat().st_mode), 0o600)

    def test_existing_keys_not_asked_again(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / '.env'
            path.write_text('AVIATIONSTACK_KEY=FLIGHT_TEST_123\n'
                            'WEATHERAPI_KEY=WEATHER_TEST_456\n'
                            'OPENAI_API_KEY=VOICE_TEST_789\n')
            before = path.read_bytes()
            result = setup.configure_local_services(Path(temp), {}, is_tty=True,
                    prompt=lambda label: self.fail('should not prompt'))
            self.assertTrue(all(result.values()))
            self.assertEqual(before, path.read_bytes())

    def test_explicit_rotation_retains_gateway_and_unmodified_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / '.env'
            path.write_text('# local secret file\nAVIATIONSTACK_KEY=OLD_FLIGHT\n'
                            'WEATHERAPI_KEY=OLD_WEATHER\nOPENAI_API_KEY=OLD_VOICE\n'
                            'LX_GATEWAY_URL=https://gateway.example.test\n'
                            'LX_GATEWAY_TOKEN=other_gateway_secret\n')
            entries = iter(('NEW_FLIGHT', '', 'NEW_VOICE'))
            messages = []
            result = setup.configure_local_services(Path(temp), {}, replace=True,
                        is_tty=True, prompt=lambda label: next(entries), tell=messages.append)
            self.assertTrue(all(result.values()))
            data = path.read_text()
            self.assertIn('AVIATIONSTACK_KEY=NEW_FLIGHT', data)
            self.assertNotIn('OLD_FLIGHT', data)
            self.assertIn('WEATHERAPI_KEY=OLD_WEATHER', data)
            self.assertIn('OPENAI_API_KEY=NEW_VOICE', data)
            self.assertIn('LX_GATEWAY_URL=https://gateway.example.test', data)
            self.assertIn('LX_GATEWAY_TOKEN=other_gateway_secret', data)
            self.assertNotIn('NEW_FLIGHT', '\n'.join(messages))
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_invalid_or_skipped_key_stays_unconfigured(self):
        with tempfile.TemporaryDirectory() as temp:
            entries = iter(('\n', 'YOUR_KEY', 'SKIP\nBAD'))
            messages = []
            result = setup.configure_local_services(Path(temp), {}, is_tty=True,
                     prompt=lambda label: next(entries), tell=messages.append)
            self.assertFalse(any(result.values()))
            self.assertFalse((Path(temp) / '.env').exists())
            self.assertTrue(any('Not configured:' in m for m in messages))

    def test_environment_key_is_not_written_to_file(self):
        with tempfile.TemporaryDirectory() as temp:
            entries = iter(('WEATHER_TEST_456', 'VOICE_TEST_789'))
            result = setup.configure_local_services(
                Path(temp), {'AVIATIONSTACK_KEY': 'FLIGHT_ENV_123'}, is_tty=True,
                prompt=lambda label: next(entries))
            data = (Path(temp) / '.env').read_text()
            self.assertTrue(all(result.values()))
            self.assertNotIn('FLIGHT_ENV_123', data)
            self.assertIn('WEATHERAPI_KEY=WEATHER_TEST_456', data)

    def test_noninteractive_skips_setup(self):
        with tempfile.TemporaryDirectory() as temp:
            result = setup.configure_local_services(Path(temp), {}, is_tty=False,
                       prompt=lambda label: self.fail('must never prompt'))
            self.assertFalse(any(result.values()))
            self.assertFalse((Path(temp) / '.env').exists())
            with self.assertRaisesRegex(ValueError, 'interactive'):
                setup.configure_local_services(Path(temp), {}, replace=True, is_tty=False)

    def test_symlinked_env_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'outside').write_text('unrelated')
            (folder / '.env').symlink_to(folder / 'outside')
            with self.assertRaises(OSError):
                setup.configure_local_services(folder, {}, is_tty=True)
            self.assertEqual((folder / 'outside').read_text(), 'unrelated')

    def test_start_runs_setup_once_before_exec(self):
        with patch.object(start.sys, 'argv', ['start.py']), \
             patch.object(start.sys.stdin, 'isatty', return_value=True), \
             patch.dict(os.environ, {'LX_ENV': 'development', 'LX_LAN': '0', 'LX_NO_SETUP': '0'}, clear=True), \
             patch.object(start, 'configure_local_services') as configure, \
             patch.object(start.os, 'chdir'), \
             patch.object(start.os, 'execvpe') as exec_call:
            start.main()
        self.assertEqual(configure.call_count, 1)
        self.assertFalse(configure.call_args.kwargs['replace'])
        self.assertEqual(exec_call.call_args.args[2]['LX_NO_SETUP'], '1')
        self.assertEqual(exec_call.call_args.args[2]['LX_ENABLE_FIXTURE'], '1')

    def test_start_explicit_rotation_is_interactive_only(self):
        with patch.object(start.sys, 'argv', ['start.py', '--configure']), \
             patch.object(start.sys.stdin, 'isatty', return_value=False):
            with self.assertRaises(SystemExit):
                start.main()
        with patch.object(start.sys, 'argv', ['start.py', '--configure']), \
             patch.object(start.sys.stdin, 'isatty', return_value=True), \
             patch.dict(os.environ, {'LX_NO_SETUP': '0'}, clear=True), \
             patch.object(start, 'configure_local_services') as configure, \
             patch.object(start.os, 'chdir'), \
             patch.object(start.os, 'execvpe'):
            start.main()
        self.assertTrue(configure.call_args.kwargs['replace'])

    def test_start_is_noninteractive_in_production_and_in_ci(self):
        with patch.object(start.sys, 'argv', ['start.py']), \
             patch.object(start.sys.stdin, 'isatty', return_value=True), \
             patch.dict(os.environ, {'LX_ENV': 'production'}, clear=True), \
             patch.object(start, 'configure_local_services') as configure:
            with self.assertRaises(SystemExit):
                start.main()
            configure.assert_not_called()
        with patch.object(start.sys, 'argv', ['start.py']), \
             patch.object(start.sys.stdin, 'isatty', return_value=False), \
             patch.dict(os.environ, {}, clear=True), \
             patch.object(start, 'configure_local_services') as configure, \
             patch.object(start.os, 'chdir'), \
             patch.object(start.os, 'execvpe') as exec_call:
            start.main()
            configure.assert_not_called()
            self.assertEqual(exec_call.call_args.args[2]['LX_NO_SETUP'], '1')

    def test_direct_run_environment_secrets_do_not_persist(self):
        # No real credentials or provider requests: synthetic values only.
        import run
        from runtime_security import Settings
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(run, 'KEY_FILE', Path(temp) / '.env'), \
             patch.object(run, 'SETTINGS', Settings('development', 8765, False, False, '')), \
             patch.object(run.sys.stdin, 'isatty', return_value=False), \
             patch.dict(os.environ, {
                 'AVIATIONSTACK_KEY': 'FAKE_FLIGHT_123',
                 'WEATHERAPI_KEY': 'FAKE_WEATHER_123',
                 'OPENAI_API_KEY': 'FAKE_VOICE_123',
                 'LX_NO_SETUP': '1'}, clear=True):
            values = run._local_config()
            self.assertEqual(values['AVIATIONSTACK_KEY'], 'FAKE_FLIGHT_123')
            self.assertEqual(values['WEATHERAPI_KEY'], 'FAKE_WEATHER_123')
            self.assertEqual(values['OPENAI_API_KEY'], 'FAKE_VOICE_123')
            self.assertFalse((Path(temp) / '.env').exists())

    def test_fake_keys_reach_existing_provider_adapters(self):
        # Verify local key-to-adapter wiring, not any live provider entitlement.
        import json
        import run
        with patch.object(run, 'API_KEY', 'FAKE_FLIGHT_123'), \
             patch.object(run, 'provider_data', return_value={'data': []}):
            result = run.lookup('EK232')
            self.assertEqual(result['source'], 'aviationstack')
        weather_response = {
            'current': {'temp_c': 23, 'is_day': 1,
                        'condition': {'code': 1000, 'text': 'Sunny'}},
            'location': {'name': 'Paris', 'region': 'Ile-de-France'},
        }
        # Python uses methods on the TYPE for context-manager lookup.
        class FakeResponse:
            headers = {'Content-Type': 'application/json'}
            def __init__(self, payload): self.payload = payload
            def read(self, size): return self.payload
            def __enter__(self): return self
            def __exit__(self, *args): return False
        with patch.object(run, 'WEATHER_KEY', 'FAKE_WEATHER_123'), \
             patch.object(run, 'urlopen', return_value=FakeResponse(json.dumps(weather_response).encode())):
            result = run.destination_weather('CDG', 'fr')
            self.assertEqual(result['source'], 'weatherapi')
            self.assertEqual(result['tempC'], 23)
        fake_audio = FakeResponse(b'ID3' + b'x' * 300)
        fake_audio.headers = {'Content-Type': 'audio/mpeg'}
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(run, 'OPENAI_KEY', 'FAKE_VOICE_123'), \
             patch.object(run, 'AUDIO_CACHE', Path(temp)), \
             patch.object(run, 'urlopen', return_value=fake_audio):
            response = run.demo_audio('English', next(iter(run.DEMO_MESSAGES['English'])))
            self.assertTrue(response.startswith(b'ID3'))

    def test_security_of_github_gitignore(self):
        gitignore = (ROOT / '.gitignore').read_text()
        self.assertIn('.env', gitignore)
        self.assertIn('!.env.example', gitignore)
        self.assertFalse((ROOT / '.env').exists())
        self.assertFalse(any('sk-proj-' in p.read_text(errors='ignore')
                             for p in [ROOT / 'start.py', ROOT / 'local_service_setup.py',
                                       ROOT / '.env.example']))


if __name__ == '__main__':
    unittest.main()

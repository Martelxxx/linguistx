"""v76 engineering invariants; these are not live-service acceptance tests."""
# DEVNOTE: Fast engineering invariants protect secure defaults and the approved passenger surface from accidental refactors.
import hashlib
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime_security import read_settings, guest_cookie, response_headers

HERE = Path(__file__).resolve().parents[1]


class EngineeringPolicyTest(unittest.TestCase):
    def test_port_validation(self):
        for port in ('', '0', '-1', '65536', 'abc'):
            with self.subTest(port=port), self.assertRaises(ValueError):
                read_settings({'PORT': port})
        self.assertEqual(read_settings({'PORT': '8765'}).port, 8765)
        self.assertEqual(read_settings({'PORT': '65535'}).port, 65535)

    def test_fixture_never_production_or_lan(self):
        for env in ({'LX_ENABLE_FIXTURE': '1', 'LX_LAN': '1'},
                    {'LX_ENABLE_FIXTURE': '1', 'LX_ENV': 'production',
                     'LX_NO_SETUP': '1', 'LX_PUBLIC_URL': 'https://example.test'}):
            with self.subTest(env=env), self.assertRaises(ValueError):
                read_settings(env)

    def test_production_requires_https_public_url_and_noninteractive(self):
        for url in ('', 'http://example.test', 'https://user:pw@example.test'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                read_settings({'LX_ENV': 'production', 'LX_NO_SETUP': '1', 'LX_PUBLIC_URL': url})
        settings = read_settings({'LX_ENV': 'production', 'LX_NO_SETUP': '1',
                                  'LX_PUBLIC_URL': 'https://example.test'})
        self.assertTrue(settings.production)
        self.assertIn('Strict-Transport-Security', response_headers(settings.production))

    def test_guest_cookie_is_secure_only_under_https_production(self):
        local = guest_cookie('abc', max_age=120)
        prod = guest_cookie('abc', max_age=120, production=True)
        self.assertIn('HttpOnly', local)
        self.assertIn('SameSite=Strict', local)
        self.assertNotIn('; Secure', local)
        self.assertIn('; Secure', prod)
        with self.assertRaises(ValueError):
            guest_cookie('bad; path=/', max_age=120)

    def test_aviationstack_never_downgrades_api_credentials(self):
        with patch.dict(os.environ, {'LX_NO_SETUP': '1'}):
            import run
            seen = []
            def fake(url, *, params):
                seen.append(url)
                return {'error': {'code': 'https_access_restricted', 'message': 'HTTPS unavailable'}}
            with patch.object(run, 'api_request', side_effect=fake):
                with self.assertRaises(run.APIError):
                    run.provider_data('EK232')
            self.assertEqual(seen, ['https://api.aviationstack.com/v1/flights'])

    def test_audit_log_excludes_url_cookie_and_content(self):
        from app_logging import LOGGER, audit
        with patch.object(LOGGER, 'info') as output:
            rid = audit('api_request_denied', status=403, elapsed_ms=4.5)
            line = output.call_args.args[0]
            self.assertIn(rid, line)
            self.assertNotIn('guestToken', line)
            self.assertNotIn('cookie', line)
            self.assertNotIn('caption', line)
            self.assertNotIn('http://', line)

    def test_passenger_surface_is_v75_equivalent_outside_intentional_v78_splash(self):
        if (HERE / "gate-card.css").exists():
            self.skipTest("Historical v75 byte-identity applies before the approved v91 static gate rebuild.")
        # Recover the approved v75 bytes after removing ONLY the additive v80 gate/lens
        # integration, the approved v78 launch splash, and render-neutral DEVNOTE comments.
        blob = (HERE / 'passenger-only.html').read_bytes()
        blob = blob.replace(b'<div class="flight-gate" id="lxGateAccess" role="button" tabindex="0" aria-label="Open directions for your gate" aria-haspopup="dialog" aria-controls="lxGateExpand" aria-expanded="false">', b'<div class="flight-gate">', 1)
        blob = blob.replace(b'<link rel="stylesheet" href="/wayfinder.css?v=87">\n', b'', 1)
        blob = blob.replace(b'<script src="/wayfinder.js?v=87" defer></script>\n', b'', 1)
        blob = re.sub(rb'<style id="lx-wordly-splash-styles">.*?</style>\n?', b'', blob, flags=re.S)
        blob = re.sub(rb'  <!-- DEVNOTE: v78 shared-element splash.*?<div class="lx-wordly-splash".*?</div>\n  </div>\n', b'', blob, count=1, flags=re.S)
        blob = re.sub(rb'<script id="lx-wordly-splash-script">.*?</script>\n?', b'', blob, flags=re.S)
        blob = blob.replace(
            b'<div class="desk"><div class="phone"><div class="app lx-splash-running" id="app">',
            b'<div class="desk"><div class="phone"><div class="app" id="app">')
        blob = re.sub(rb'<!-- DEVNOTE:.*?-->\n?', b'', blob, flags=re.S)
        blob = re.sub(rb'/\* DEVNOTE:.*?\*/\n?', b'', blob, flags=re.S)
        # Remove only whitespace introduced around the isolated v78 insertion points.
        blob = blob.replace(b'\n\n</head>', b'\n</head>', 1)
        blob = blob.replace(b'</div>\n\n  <section class="page active" id="welcome"',
                            b'</div>\n  <section class="page active" id="welcome"', 1)
        blob = blob.replace(b'</script>\n\n</body></html>', b'</script>\n</body></html>', 1)
        self.assertEqual(hashlib.sha256(blob).hexdigest(),
                         '40e90476dfb165aff5fa274badb9349cc287e2242ed654ce2194beb56485ffe7')

    def test_internal_documentation_is_linked_without_entering_passenger_surface(self):
        index = (HERE / 'index.html').read_text()
        passenger = (HERE / 'passenger-only.html').read_text()
        self.assertIn('href="/developer-documentation.html"', index)
        self.assertNotIn('href="/developer-documentation.html"', passenger)
        self.assertTrue((HERE / 'developer-documentation.html').is_file())


if __name__ == '__main__':
    unittest.main()

"""v77 developer-handoff regression tests.

These tests prove that the documentation is wired into development tooling without becoming
part of the passenger-only experience or the production public static surface.
"""
# DEVNOTE: Documentation is treated as maintained product infrastructure; architecture changes should update these expectations.
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

import passenger_asgi
from runtime_security import Settings

HERE = Path(__file__).resolve().parents[1]


class DeveloperDocumentationTest(unittest.TestCase):
    """Keep the internal handoff page complete, linked, and nonproduction."""

    def test_documentation_has_core_maintainer_sections(self):
        """Require the sections another developer needs before changing architecture or UX."""
        docs = (HERE / 'developer-documentation.html').read_text(encoding='utf-8')
        for heading in (
            'Product invariants', 'Architecture at a glance', 'Repository file map',
            'Frontend model', 'Backend model', 'Translation integration boundary',
            'Browser-facing application APIs', 'Security and privacy invariants',
            'Testing and quality gates', 'Safe change protocol', 'Known open gates',
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, docs)

    def test_checklist_links_docs_but_passenger_surface_does_not(self):
        """The visible documentation entry belongs only to desktop developer chrome."""
        index = (HERE / 'index.html').read_text(encoding='utf-8')
        passenger = (HERE / 'passenger-only.html').read_text(encoding='utf-8')
        self.assertIn('href="/developer-documentation.html"', index)
        self.assertNotIn('href="/developer-documentation.html"', passenger)

    def test_asgi_serves_docs_only_outside_production(self):
        """Internal engineering material must not be exposed by the production ASGI static route."""
        development = Settings('development', 8765, False, False, '')
        with patch.object(passenger_asgi, 'SETTINGS', development):
            with TestClient(passenger_asgi.app) as client:
                response = client.get('/developer-documentation.html')
                self.assertEqual(response.status_code, 200)
                self.assertIn('Linguist-X Passenger', response.text)
        production = Settings('production', 8765, False, False, 'https://example.test')
        with patch.object(passenger_asgi, 'SETTINGS', production):
            with TestClient(passenger_asgi.app) as client:
                response = client.get('/developer-documentation.html', headers={'host':'example.test'})
                self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()

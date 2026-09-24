"""
Tests for CORS configuration across the application.

Verifies:
- Simple GET/POST requests return matching Origin and Allow-Credentials headers
- Preflight OPTIONS requests properly allow requested methods and headers
- Wildcard '*' is never returned alongside 'Access-Control-Allow-Credentials: true'
- Non-CORS requests (without Origin) behave normally without CORS headers
"""

import asyncio
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import init_db
from app.main import app


class TestCORSConfiguration(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        os.environ["DB_PATH"] = self.temp_db.name
        get_settings.cache_clear()
        asyncio.run(init_db())
        self.client = TestClient(app)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            os.remove(self.temp_db.name)
        for extra in [f"{self.temp_db.name}-wal", f"{self.temp_db.name}-shm"]:
            if os.path.exists(extra):
                os.remove(extra)

    def test_cors_simple_get_mirrors_origin_and_allows_credentials(self):
        """Simple GET request with Origin must mirror the origin and not return '*' with credentials."""
        origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "https://promptocalypse.vercel.app",
        ]
        for origin in origins:
            with self.subTest(origin=origin):
                res = self.client.get("/health", headers={"Origin": origin})
                self.assertEqual(res.status_code, 200)

                acao = res.headers.get("access-control-allow-origin")
                acac = res.headers.get("access-control-allow-credentials")

                # Must mirror the specific requesting origin, never '*'
                self.assertEqual(acao, origin)
                self.assertEqual(acac, "true")
                self.assertNotEqual(acao, "*")

    def test_cors_preflight_options_chat_endpoint(self):
        """Preflight OPTIONS request for /api/chat must return valid CORS headers."""
        res = self.client.options(
            "/api/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(res.status_code, 200)

        acao = res.headers.get("access-control-allow-origin")
        acac = res.headers.get("access-control-allow-credentials")
        acam = res.headers.get("access-control-allow-methods")
        acah = res.headers.get("access-control-allow-headers")

        self.assertEqual(acao, "http://localhost:3000")
        self.assertEqual(acac, "true")
        self.assertIn("POST", acam or "")
        self.assertIn("content-type", (acah or "").lower())

    def test_cors_preflight_options_submit_key_endpoint(self):
        """Preflight OPTIONS request for /api/submit-key must return valid CORS headers."""
        res = self.client.options(
            "/api/submit-key",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )
        self.assertEqual(res.headers.get("access-control-allow-credentials"), "true")

    def test_cors_get_leaderboard(self):
        """GET /api/leaderboard with Origin must return matching CORS origin header."""
        res = self.client.get(
            "/api/leaderboard",
            headers={"Origin": "http://localhost:3000"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )
        self.assertEqual(res.headers.get("access-control-allow-credentials"), "true")

    def test_non_cors_request_has_no_cors_headers(self):
        """Requests without an Origin header should not contain CORS headers."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("access-control-allow-origin", res.headers)


if __name__ == "__main__":
    unittest.main()

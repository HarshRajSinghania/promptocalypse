"""
Regression test for Issue #33:
[Backend] Pin httpx to compatible version for OpenAI/Groq client.

Root cause regression guard: openai==1.50.0 passes the ``proxies`` argument
to httpx's client constructor, which httpx 0.28 removed. With an unpinned
httpx resolving to >=0.28, constructing a real AsyncOpenAI client raised:

    TypeError: AsyncClient.__init__() got an unexpected keyword argument 'proxies'

breaking real POST /api/chat and GET /api/health at dependency resolution.

This test constructs the real client with the project's configuration and
must not raise. It performs NO network request (construction only).
"""

import asyncio
import unittest

import openai

from app.config import get_settings
from app.routes.chat import get_groq_client


class TestOpenAIHttpxCompatibility(unittest.TestCase):
    """Guards the openai/httpx version pairing used by the real Groq client."""

    def test_real_async_openai_client_constructs_with_project_config(self):
        """Real AsyncOpenAI construction must not raise the proxies TypeError."""
        settings = get_settings()
        client = openai.AsyncOpenAI(
            base_url=settings.GROQ_BASE_URL,
            api_key=settings.GROQ_API_KEY,
        )
        try:
            self.assertIsInstance(client, openai.AsyncOpenAI)
            self.assertEqual(str(client.base_url).rstrip("/"), settings.GROQ_BASE_URL.rstrip("/"))
        finally:
            asyncio.run(client.close())

    def test_project_groq_client_dependency_constructs(self):
        """The project's get_groq_client dependency must construct successfully."""
        client = get_groq_client(get_settings())
        try:
            self.assertIsInstance(client, openai.AsyncOpenAI)
        finally:
            asyncio.run(client.close())


if __name__ == "__main__":
    unittest.main()

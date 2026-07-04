"""
Tests for the per-IP rate limit on the /chat endpoint.

Heavy dependencies (chromadb, langchain_*, sentence_transformers) and the
RAGChainManager itself are stubbed in sys.modules *before* the api module is
imported, so no real LLM or vector-store connection is needed.
"""

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Module-level stub builder
# ---------------------------------------------------------------------------

def _stub_modules():
    """Insert lightweight stubs for packages that are unavailable in tests."""
    stubs = [
        "chromadb",
        "langchain_chroma",
        "langchain_openai",
        "langchain_huggingface",
        "sentence_transformers",
        "langchain",
        "langchain.chains",
        "langchain_community",
        "langchain_community.vectorstores",
    ]
    for name in stubs:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)


def _make_app(rate_limit: str = "2/minute"):
    """
    Build a fresh FastAPI TestClient for rag_api.api with:
      - CHAT_RATE_LIMIT forced to *rate_limit*
      - OPENROUTER_API_KEY set to a dummy value (required by RAGConfig)
      - RAGChainManager fully mocked (no LLM / vector-store calls)

    Returns (client, RATE_LIMIT_PER_MINUTE).
    """
    import os
    os.environ["CHAT_RATE_LIMIT"] = rate_limit
    os.environ["OPENROUTER_API_KEY"] = "test-key"

    # Purge any previously cached rag_api modules so they re-read the env vars.
    for mod_name in list(sys.modules):
        if "rag_api" in mod_name:
            del sys.modules[mod_name]

    _stub_modules()

    # Stub rag_api.chains so the `from .chains import RAGChainManager` inside
    # api.py resolves without actually importing heavy langchain code.
    chains_stub = types.ModuleType("rag_api.chains")
    mock_instance = MagicMock()
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = {
        "result": "mocked answer",
        "source_documents": [],
    }
    mock_instance.get_qa_chain.return_value = mock_chain
    MockChainManager = MagicMock(return_value=mock_instance)
    chains_stub.RAGChainManager = MockChainManager
    sys.modules["rag_api.chains"] = chains_stub

    # Also stub rag_api.embeddings / rag_api.vector_store if they exist.
    for sub in ("rag_api.embeddings", "rag_api.vector_store"):
        if sub not in sys.modules:
            sys.modules[sub] = types.ModuleType(sub)

    # Now import the real api module (it picks up our stubs).
    import rag_api.api as api_module  # noqa: PLC0415

    from fastapi.testclient import TestClient
    client = TestClient(api_module.app, raise_server_exceptions=False)
    return client, api_module.RATE_LIMIT_PER_MINUTE


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestChatRateLimit(unittest.TestCase):

    def setUp(self):
        self.client, self.configured_limit = _make_app("2/minute")

    # ------------------------------------------------------------------
    def _post_chat(self):
        return self.client.post(
            "/chat",
            json={"question": "What are the top complaints?"},
        )

    # ------------------------------------------------------------------
    def test_rate_limit_string_is_configured(self):
        """RATE_LIMIT_PER_MINUTE must be a non-empty string."""
        self.assertIsInstance(self.configured_limit, str)
        self.assertTrue(
            len(self.configured_limit) > 0,
            "RATE_LIMIT_PER_MINUTE must not be empty",
        )

    def test_requests_within_limit_succeed(self):
        """First two requests (within the 2/minute cap) should be 200 OK."""
        for i in range(2):
            response = self._post_chat()
            self.assertEqual(
                response.status_code, 200,
                f"Request #{i + 1} expected 200, got {response.status_code}",
            )

    def test_request_exceeding_limit_returns_429(self):
        """The third request must be rate-limited with a 429 response."""
        self._post_chat()  # 1st — OK
        self._post_chat()  # 2nd — OK (cap reached)
        response = self._post_chat()  # 3rd — should be rejected
        self.assertEqual(
            response.status_code, 429,
            f"Expected 429 Too Many Requests, got {response.status_code}",
        )

    def test_rate_limited_response_has_json_error_body(self):
        """A 429 response from slowapi must contain a JSON error body."""
        self._post_chat()
        self._post_chat()
        response = self._post_chat()
        self.assertEqual(response.status_code, 429)
        # slowapi returns {"error": "..."} on rate-limit violations.
        body = response.json()
        self.assertIn(
            "error", body,
            f"Expected JSON error body, got: {body}",
        )


if __name__ == "__main__":
    unittest.main()

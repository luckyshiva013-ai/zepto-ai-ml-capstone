"""Offline tests (MOCK_LLM left at its default). Run:  pytest -q"""
import os

import pytest
import requests

os.environ.pop("MOCK_LLM", None)  # default = mock mode

from fastapi.testclient import TestClient  # noqa: E402

import retrieval  # noqa: E402
from intent import keyword_intent  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network/LLM call attempted in mock mode")
    monkeypatch.setattr(requests, "post", boom)


def test_keyword_routing():
    assert keyword_intent("What is the delivery fee?") == "policy_question"
    assert keyword_intent("What is the capital of France?") == "general_question"


def test_retrieval_returns_matching_doc():
    top = retrieval.retrieve("What gift card denominations are available?", k=3)
    assert len(top) == 3
    assert top[0]["id"] == "doc_07"
    ids = [c["id"] for c in retrieval.retrieve("What is the delivery fee for small orders?", k=3)]
    assert "doc_01" in ids


def test_ask_policy_question():
    with TestClient(app) as client:
        r = client.post("/ask", json={"query": "What is the delivery fee for small orders?"})
    body = r.json()
    assert r.status_code == 200
    assert body["answer"].startswith("Based on the retrieved context: ")
    assert len(body["sources"]) == 3 and body["confidence"] == 1.0


def test_ask_general_question():
    with TestClient(app) as client:
        body = client.post("/ask", json={"query": "What is the capital of France?"}).json()
    assert body == {"answer": "I can only answer questions about Zepto policies right now.",
                    "sources": [], "confidence": 1.0}


def test_bad_request_rejected():
    with TestClient(app) as client:
        assert client.post("/ask", json={}).status_code == 422

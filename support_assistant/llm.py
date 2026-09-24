"""LLM access. Everything here is behind the MOCK_LLM toggle.

MOCK_LLM unset or "1"  -> mock mode (graded baseline): nothing in this file is ever called.
MOCK_LLM="0"           -> optional extension: real LLM via Groq's free tier (or any OpenAI-compatible API).
"""
import json
import os

import requests
from pydantic import ValidationError  # noqa: F401  (ValidationError is a ValueError subclass in pydantic v2)

from schemas import AskResponse

GROQ_URL = os.getenv("LLM_API_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_MODEL = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
MAX_RETRIES = 2  # additional attempts after the first one


def is_mock() -> bool:
    """Only an explicit MOCK_LLM=0 turns the real LLM on. Read at call time, not import time."""
    return os.getenv("MOCK_LLM") != "0"


def call_llm(prompt: str) -> str:
    api_key = os.getenv("GROQ_API_KEY")  # never hardcode or commit a key
    if not api_key:
        raise RuntimeError("MOCK_LLM=0 requires the GROQ_API_KEY environment variable")
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": GROQ_MODEL, "temperature": 0,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def extract_json(raw: str) -> dict:
    """Pull the first {...} object out of a reply (models sometimes add code fences or chatter)."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in LLM output")
    return json.loads(raw[start:end + 1])


def error_response(message: str) -> AskResponse:
    return AskResponse(answer=f"ERROR: {message}", sources=[], confidence=0.0)


def generate_validated(prompt: str, allowed_sources=None) -> AskResponse:
    """Real-LLM path: validate the output against AskResponse, retry up to 2 more times with a
    corrective instruction, and finally return a clearly marked error response."""
    current, last_err = prompt, None
    for _ in range(1 + MAX_RETRIES):
        try:
            data = extract_json(call_llm(current))
            resp = AskResponse.model_validate(data)
            if allowed_sources is not None:
                resp.sources = [s for s in resp.sources if s in allowed_sources]
            return resp
        except (requests.RequestException, RuntimeError) as e:  # network / config problem: retrying the prompt will not help
            return error_response(f"LLM call failed: {str(e)[:200]}")
        except ValueError as e:  # bad JSON or schema violation
            last_err = e
            current = (prompt + "\n\nYour previous reply was invalid: " + str(e)[:300] +
                       "\nReply again with ONLY a valid JSON object with keys answer (string), "
                       "sources (list of strings) and confidence (number between 0 and 1).")
    return error_response(f"LLM output failed schema validation after {1 + MAX_RETRIES} attempts: {str(last_err)[:200]}")

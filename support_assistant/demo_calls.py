"""Run the two required example calls in the default mock mode and record the raw JSON.

    python demo_calls.py      ->  writes example_calls.md
"""
import json
import os

os.environ.pop("MOCK_LLM", None)  # default (mock) mode is what gets graded

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

CALLS = [
    ("Should trigger retrieval (policy_question -> retrieve_and_answer)",
     "What is the delivery fee for orders below INR 149?"),
    ("Should NOT trigger retrieval (general_question -> direct_answer)",
     "What is the capital of France?"),
]

lines = ["# Example calls (MOCK_LLM left at its default)\n"]
with TestClient(app) as client:
    for label, query in CALLS:
        payload = {"query": query}
        resp = client.post("/ask", json=payload)
        block = (f"## {label}\n\nRequest:\n```json\n{json.dumps(payload, indent=2)}\n```\n\n"
                 f"Response (HTTP {resp.status_code}):\n```json\n{json.dumps(resp.json(), indent=2, ensure_ascii=False)}\n```\n")
        print(block)
        lines.append(block)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "example_calls.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Wrote example_calls.md")

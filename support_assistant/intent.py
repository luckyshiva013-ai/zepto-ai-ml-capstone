"""Intent keyword heuristic (mock-mode classifier). No dependencies, no LLM, no network."""

POLICY_KEYWORDS = (
    "delivery", "return", "refund", "membership", "tracking",
    "cancel", "gift card", "support hours",
)


def keyword_intent(query: str) -> str:
    """policy_question if the lowercased query contains any policy keyword, else general_question."""
    q = query.lower()
    return "policy_question" if any(k in q for k in POLICY_KEYWORDS) else "general_question"

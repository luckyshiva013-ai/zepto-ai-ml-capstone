"""LangGraph flow: classify_intent -> (conditional) -> retrieve_and_answer | direct_answer."""
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

import llm
import prompts
import retrieval
from intent import keyword_intent

DIRECT_MOCK_ANSWER = "I can only answer questions about Zepto policies right now."


class GraphState(TypedDict, total=False):
    query: str
    intent: str
    retrieved: List[Dict[str, Any]]
    answer: str
    sources: List[str]
    confidence: float


def classify_intent(state: GraphState) -> dict:
    query = state["query"]
    if llm.is_mock():  # graded baseline: keyword heuristic, no LLM call
        return {"intent": keyword_intent(query)}
    # optional MOCK_LLM=0 extension: ask the LLM, fall back to the heuristic if it misbehaves
    try:
        raw = llm.call_llm(
            "Classify the customer query as exactly one of: policy_question (about Zepto delivery, "
            "returns, refunds, membership, tracking, cancellation, gift cards or support hours) or "
            f"general_question (anything else). Reply with only the label.\nQuery: {query}")
        label = raw.strip().lower()
        if "policy_question" in label:
            return {"intent": "policy_question"}
        if "general_question" in label:
            return {"intent": "general_question"}
    except Exception:
        pass
    return {"intent": keyword_intent(query)}


def retrieve_and_answer(state: GraphState) -> dict:
    query = state["query"]
    chunks = retrieval.retrieve(query, k=3)  # always real: local embeddings + ChromaDB
    ids = [c["id"] for c in chunks]
    if llm.is_mock():  # graded baseline: canned templated answer from the top chunk
        top = chunks[0]["text"]
        snippet = top[:200].rstrip() + ("..." if len(top) > 200 else "")
        return {"retrieved": chunks, "answer": f"Based on the retrieved context: {snippet}",
                "sources": ids, "confidence": 1.0}
    resp = llm.generate_validated(prompts.build_rag_prompt(query, chunks), allowed_sources=set(ids))
    return {"retrieved": chunks, "answer": resp.answer, "sources": resp.sources, "confidence": resp.confidence}


def direct_answer(state: GraphState) -> dict:
    if llm.is_mock():  # graded baseline: fixed string
        return {"retrieved": [], "answer": DIRECT_MOCK_ANSWER, "sources": [], "confidence": 1.0}
    resp = llm.generate_validated(prompts.build_direct_prompt(state["query"]), allowed_sources=set())
    return {"retrieved": [], "answer": resp.answer, "sources": [], "confidence": resp.confidence}


def route(state: GraphState) -> str:
    return state["intent"]  # does not depend on MOCK_LLM


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("classify_intent", classify_intent)
    g.add_node("retrieve_and_answer", retrieve_and_answer)
    g.add_node("direct_answer", direct_answer)
    g.add_edge(START, "classify_intent")
    g.add_conditional_edges("classify_intent", route, {
        "policy_question": "retrieve_and_answer",
        "general_question": "direct_answer",
    })
    g.add_edge("retrieve_and_answer", END)
    g.add_edge("direct_answer", END)
    return g.compile()


graph = build_graph()

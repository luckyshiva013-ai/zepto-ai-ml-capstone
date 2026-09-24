# Module 3 - Zepto Support Assistant (`/support_assistant`)

A small RAG service: 8 policy documents -> local embeddings -> ChromaDB -> LangGraph router ->
Pydantic-validated JSON answer -> FastAPI. **The default state is a deterministic, fully offline
mock mode** (`MOCK_LLM` unset or `1`): no API key, no LLM network call. The local embedding model and
ChromaDB retrieval always run for real.

## Setup and run

```bash
cd support_assistant
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                          # separate from the root file: this module needs torch/chromadb
python ingest.py                                         # optional: embeds + indexes the 8 docs (app does it on startup too)
uvicorn main:app --port 7860                             # MOCK_LLM left at its default
```
The first run downloads the `all-MiniLM-L6-v2` model (~90 MB) once; after that everything is local.

```bash
curl -s -X POST localhost:7860/ask -H "Content-Type: application/json" \
     -d '{"query": "What is the delivery fee for orders below INR 149?"}'
curl -s -X POST localhost:7860/ask -H "Content-Type: application/json" \
     -d '{"query": "What is the capital of France?"}'
```
Tests (offline, mock mode): `pytest -q`.

## Example calls (run with MOCK_LLM at its default)

Run `python demo_calls.py`; it makes both calls and writes the raw request/response JSON to
[`example_calls.md`](example_calls.md). Paste that output below before submitting:

# Example calls (MOCK_LLM left at its default)

## Should trigger retrieval (policy_question -> retrieve_and_answer)

Request:
```json
{
  "query": "What is the delivery fee for orders below INR 149?"
}
```

Response (HTTP 200):
```json
{
  "answer": "Based on the retrieved context: Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30 minutes of order confirmation, depending on the customer's delivery zone and current order volume. Standard del...",
  "sources": [
    "doc_01",
    "doc_05",
    "doc_03"
  ],
  "confidence": 1.0
}
```

## Should NOT trigger retrieval (general_question -> direct_answer)

Request:
```json
{
  "query": "What is the capital of France?"
}
```

Response (HTTP 200):
```json
{
  "answer": "I can only answer questions about Zepto policies right now.",
  "sources": [],
  "confidence": 1.0
}
```


## Docker (required baseline: builds and runs locally)

```bash
docker build -t zepto-support .
docker run --rm -p 7860:7860 zepto-support
curl -s -X POST localhost:7860/ask -H "Content-Type: application/json" -d '{"query": "Can I cancel my order?"}'
```
The image installs CPU-only torch, bakes in the embedding model, and indexes the docs at build time.
`MOCK_LLM` is not set in the image, so it serves the offline mock mode. (Deploying to Hugging Face
Spaces is an optional, ungraded stretch and was not part of this submission.)

## Architecture: ingestion -> embedding -> retrieval -> generation

```
docs/doc_01..08.txt
   | ingest.load_documents() + chunk_document()      [1. INGESTION]
   v
chunks (1 chunk per doc, id = doc_0X)
   | ingest.embed()  all-MiniLM-L6-v2 (local)        [2. EMBEDDING]
   v
ChromaDB collection "zepto_policies" (cosine space, persisted in ./chroma_db)
   ^
   | retrieval.retrieve(): embed query, top-3 by cosine similarity   [3. RETRIEVAL]
   |
FastAPI POST /ask -> LangGraph graph.py
   classify_intent --policy_question--> retrieve_and_answer --> END      [4. GENERATION]
                   \--general_question-> direct_answer -------> END
```

- **Ingestion** - `ingest.py`: `load_documents()` reads the 8 corpus files verbatim; `chunk_document()` keeps each
  document as a single chunk because each is under 600 characters (it also supports fixed-size chunking).
- **Embedding** - `ingest.embed()` encodes chunks with `all-MiniLM-L6-v2` (sentence-transformers, runs locally);
  `ingest.build_index()` stores ids, texts, vectors and titles in the ChromaDB collection `zepto_policies`.
- **Retrieval** - the `retrieve_and_answer` node in `graph.py` calls `retrieval.retrieve()`, which embeds the query
  and returns the 3 most cosine-similar chunks. This always runs for real, in both modes.
- **Generation** - the `retrieve_and_answer` node produces the final answer for policy questions, and
  `direct_answer` for everything else. Output is always an `AskResponse` (`answer`, `sources`, `confidence`,
  defined in `schemas.py` with Pydantic); `main.py` validates it on the way out.
- **Routing** - `classify_intent` sets `intent`; a conditional edge (`route`) sends `policy_question` to
  `retrieve_and_answer` and `general_question` to `direct_answer`. Routing itself does not depend on `MOCK_LLM`.

### What branches on MOCK_LLM

`llm.is_mock()` is true unless `MOCK_LLM=0` is set explicitly. It gates three generation steps:

| Step | Default (mock, graded) | Optional `MOCK_LLM=0` |
|---|---|---|
| `classify_intent` | keyword heuristic on `delivery, return, refund, membership, tracking, cancel, gift card, support hours` (`intent.py`), no LLM | LLM classifies (falls back to the heuristic on failure) |
| `retrieve_and_answer` | `"Based on the retrieved context: <first ~200 chars of top chunk>"`, `sources` = the 3 retrieved ids, `confidence` = 1.0 | LLM answers from the retrieved chunks using the template in `prompts.py`; output validated against `AskResponse`, up to 2 corrective retries (`llm.generate_validated`), then a clearly marked `ERROR:` response |
| `direct_answer` | fixed string `"I can only answer questions about Zepto policies right now."`, `sources` = `[]`, `confidence` = 1.0 | LLM answers directly, no retrieval |

Embedding and ChromaDB retrieval are identical in both modes.

## Structured prompt (`prompts.py`)
Contains the five skeleton parts (ROLE, CONTEXT, TASK, FORMAT, LENGTH), explicit negative constraints
("Do not answer using information that is not present in the provided context", "Do not invent prices, time
limits or policy details"), and a few-shot EXAMPLE, as actual text. It is used only by the `MOCK_LLM=0` path.

## Optional real-LLM extension (ungraded)
```bash
export MOCK_LLM=0
export GROQ_API_KEY=...        # free key from console.groq.com; never commit it
uvicorn main:app --port 7860
```
Defaults to Groq's OpenAI-compatible endpoint with `llama-3.1-8b-instant` (override with `LLM_MODEL`,
`LLM_API_URL`). Not attempted for grading; the submission is complete in mock mode.

## Note on the keyword heuristic
The heuristic is a plain substring match on the exact keyword list from the brief, so "How fast does Zepto
deliver?" (contains "deliver", not "delivery") is classified `general_question`. Use "delivery" in demo queries.

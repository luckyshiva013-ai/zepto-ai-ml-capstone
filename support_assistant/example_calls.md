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

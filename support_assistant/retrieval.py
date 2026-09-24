"""Retrieval: embed the query and fetch the top-k chunks from ChromaDB by cosine similarity.
This always runs for real, in both mock and real-LLM modes."""
import ingest

_collection = None


def ensure_index():
    """Return the collection, building the index first if it is missing or empty."""
    global _collection
    if _collection is None:
        client = ingest.get_client()
        try:
            col = client.get_collection(ingest.COLLECTION)
            if col.count() == 0:
                raise ValueError("empty collection")
        except Exception:
            col = ingest.build_index()
        _collection = col
    return _collection


def retrieve(query: str, k: int = 3):
    col = ensure_index()
    res = col.query(
        query_embeddings=ingest.embed([query]),
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    return [
        {"id": i, "text": d, "title": m.get("title"), "similarity": round(1 - dist, 4)}
        for i, d, m, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]

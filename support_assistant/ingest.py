"""Ingestion + embedding: load docs -> chunk -> embed with all-MiniLM-L6-v2 -> store in ChromaDB.

Run once with `python ingest.py` (the app also calls ensure_index() on startup)."""
import glob
import os

import chromadb
from sentence_transformers import SentenceTransformer

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(HERE, "docs")
CHROMA_PATH = os.getenv("CHROMA_PATH", os.path.join(HERE, "chroma_db"))
COLLECTION = "zepto_policies"
MODEL_NAME = "all-MiniLM-L6-v2"

TITLES = {
    "doc_01": "Delivery Policy", "doc_02": "Returns & Refunds", "doc_03": "Membership Tiers",
    "doc_04": "Order Tracking", "doc_05": "Order Cancellation Policy",
    "doc_06": "Damaged or Missing Items", "doc_07": "Gift Cards", "doc_08": "Customer Support Hours",
}

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)  # runs locally, no API key
    return _model


def embed(texts):
    return get_model().encode(list(texts), normalize_embeddings=True).tolist()


def load_documents():
    docs = []
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "doc_*.txt"))):
        with open(path, encoding="utf-8") as f:
            docs.append((os.path.splitext(os.path.basename(path))[0], f.read().strip()))
    return docs


def chunk_document(text, chunk_size=None):
    """Each document is <600 characters, so the default is one chunk per document.
    Pass chunk_size for fixed-size character chunking instead."""
    if not chunk_size:
        return [text]
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def get_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)


def build_index():
    """(Re)build the collection from scratch so ingestion is idempotent."""
    client = get_client()
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    ids, texts, metas = [], [], []
    for doc_id, text in load_documents():
        for i, chunk in enumerate(chunk_document(text)):
            ids.append(doc_id if i == 0 else f"{doc_id}_{i}")
            texts.append(chunk)
            metas.append({"doc_id": doc_id, "title": TITLES.get(doc_id, doc_id)})
    col.add(ids=ids, documents=texts, embeddings=embed(texts), metadatas=metas)
    print(f"Indexed {len(ids)} chunks from {len(set(m['doc_id'] for m in metas))} documents into '{COLLECTION}'")
    return col


if __name__ == "__main__":
    build_index()

"""FastAPI wrapper. Run locally:  uvicorn main:app --port 7860"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

import retrieval
from graph import graph
from schemas import AskRequest, AskResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    retrieval.ensure_index()  # embed + index the 8 docs if not already done
    yield


app = FastAPI(title="Zepto Support Assistant", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    result = graph.invoke({"query": req.query})
    return AskResponse(answer=result["answer"], sources=result["sources"], confidence=result["confidence"])

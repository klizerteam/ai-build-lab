"""
main.py - the FastAPI web server.

    GET  /health  -> is the backend running? which tools are loaded?
    POST /chat    -> send a message, get the assistant's reply
    GET  /        -> the React chat page (from the frontend/ folder)

Run it from the backend folder:
    python -m uvicorn app.main:app --reload
"""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.agent import available_tool_names, run_agent
from app.database import ensure_database
from app.llm_client import LLMError, model_label
from app.schemas import ChatRequest, ChatResponse

ensure_database()


class _HideHealthChecks(logging.Filter):
    """The chat page checks /health every few seconds; keep those lines out of the terminal."""
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HideHealthChecks())

app = FastAPI(title="E-commerce AI Assistant")

# CORS: which OTHER websites may call this API from the browser.
# The built-in UI is served from this same server, so it does not need this.
# Allowed: any localhost port (e.g. a Vite app on :5173).
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "provider": config.LLM_PROVIDER,
        "model": model_label(),
        "api_key_configured": config.api_key_is_set(),  # never the key itself!
        "tools": available_tool_names(),
        "pii_masking": config.MASK_PII,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    history = [m.model_dump() for m in request.history]
    try:
        return run_agent(request.message, history)
    except LLMError as e:
        raise HTTPException(status_code=503, detail=str(e))


# Serve the React UI at http://localhost:8000/  (must be added last)
app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")

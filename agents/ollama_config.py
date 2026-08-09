"""Shared, resource-bounded Ollama configuration for local agents."""

from __future__ import annotations

import os

from langchain_community.chat_models import ChatOllama


DEFAULT_CODE_MODEL = "DeepSeek-Coder-V2-Lite-Instruct-Q5_K_M:latest"
MAX_OLLAMA_THREADS = 8


def build_chat_ollama(*, json_mode: bool = False) -> ChatOllama:
    """Create the project's local chat model with conservative limits.

    The model name and server URL remain configurable without code changes.
    ``num_thread`` is hard-capped at eight as required by the runtime budget.
    """
    requested_threads = int(os.getenv("OLLAMA_NUM_THREAD", "8"))
    num_thread = max(1, min(requested_threads, MAX_OLLAMA_THREADS))
    return ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        model=os.getenv("OLLAMA_CODE_MODEL", DEFAULT_CODE_MODEL),
        temperature=0,
        num_thread=num_thread,
        num_ctx=max(2_048, min(int(os.getenv("OLLAMA_NUM_CTX", "8192")), 16_384)),
        num_predict=max(256, min(int(os.getenv("OLLAMA_NUM_PREDICT", "2048")), 4_096)),
        timeout=max(30, int(os.getenv("OLLAMA_TIMEOUT", "300"))),
        keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
        format="json" if json_mode else None,
    )

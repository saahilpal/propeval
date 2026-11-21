from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.providers.ollama import OllamaProvider

router = APIRouter(prefix="/models", tags=["models"])


class ModelExecutionEngine(BaseModel):
    id: str
    name: str
    provider: str
    is_available: bool = True
    description: str = ""


@router.get("/available", response_model=list[ModelExecutionEngine])
async def get_available_models() -> list[dict[str, Any]]:
    """Return list of available execution engines for PropEval simulation and candidate agent runs."""
    engines: list[dict[str, Any]] = [
        {
            "id": "deterministic",
            "name": "Fast Local Engine (~3s)",
            "provider": "deterministic",
            "is_available": True,
            "description": "Deterministic local replay provider ($0 cost, ultra-fast test runs)",
        }
    ]

    ollama = OllamaProvider()
    ollama_models = await ollama.list_available_models(timeout_sec=1.5)
    for m in ollama_models:
        engines.append({
            "id": m["id"],
            "name": m["name"],
            "provider": "ollama",
            "is_available": True,
            "description": f"Live Ollama local inference ({m['model_name']})",
        })

    return engines

"""Her voice. Tonight: the state machine speaks conversationally (no key needed).

When LLM_API_KEY + LLM_MODEL are set, this module becomes the tool-calling
prompt layer: same stages, same confirm-token gate, human tone. The model
never moves money — confirms are consumed in dialogue.py.
"""
from __future__ import annotations

from app import dialogue
from app.config import settings
from app.db import log_event


async def reply(db_path: str, phone: str, text: str) -> list[str]:
    texts = await dialogue.handle(db_path, phone, text)
    log_event(db_path, "user", "dialogue", "ok", f"{phone}: stage reply x{len(texts)}")
    return texts


def llm_enabled() -> bool:
    return bool(settings.llm_api_key and settings.llm_model)

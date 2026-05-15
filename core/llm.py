from __future__ import annotations

import hashlib
import importlib
import json
import os
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from core.memory import LLMCall, get_db, now_utc


class GeminiClient:
    def __init__(self, engine: Engine | None = None):
        genai = importlib.import_module("google.genai")
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.engine = engine or get_db("demo")
        self.primary_model = os.getenv("GEMINI_MODEL_PRIMARY", "gemini-3.1-flash-lite")
        self.premium_model = os.getenv("GEMINI_MODEL_PREMIUM", "gemini-3.1-pro-preview")
        self.vision_model = os.getenv("GEMINI_MODEL_VISION", "gemini-3.1-flash-image-preview")

    def generate_json(self, prompt: str, model: str | None = None, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        text = self._generate(prompt=prompt, model=model or self.primary_model, response_json=True, schema=schema)
        try:
            return json.loads(_strip_json_fence(text))
        except json.JSONDecodeError:
            return {"raw_text": text, "parse_error": True}

    def generate_text(self, prompt: str, model: str | None = None) -> str:
        return self._generate(prompt=prompt, model=model or self.primary_model)

    def analyze_image(self, image_url: str, prompt: str) -> dict[str, Any]:
        model = self.vision_model
        cache_key, prompt_hash = _cache_key(prompt, model, image_url)
        cached = self._cached(cache_key)
        if cached:
            self._log_call(cache_key, model, prompt_hash, prompt, cached.response_text, cached.tokens, cached.cost_estimate_eur, True)
            return _json_or_raw(cached.response_text)

        contents: Any = f"{prompt}\nImage URL: {image_url}"
        try:
            types = importlib.import_module("google.genai.types")
            response = httpx.get(image_url, timeout=15)
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "image/jpeg").split(";")[0]
            contents = [
                types.Part.from_bytes(data=response.content, mime_type=mime_type),
                prompt,
            ]
        except Exception:
            pass

        response_obj = self.client.models.generate_content(model=model, contents=contents)
        text = _response_text(response_obj)
        tokens = _token_count(response_obj)
        self._log_call(cache_key, model, prompt_hash, prompt, text, tokens, _estimate_cost(tokens, model), False)
        return _json_or_raw(text)

    def _generate(self, prompt: str, model: str, response_json: bool = False, schema: dict[str, Any] | None = None) -> str:
        cache_key, prompt_hash = _cache_key(prompt, model, json.dumps(schema or {}, sort_keys=True))
        cached = self._cached(cache_key)
        if cached:
            self._log_call(cache_key, model, prompt_hash, prompt, cached.response_text, cached.tokens, cached.cost_estimate_eur, True)
            return cached.response_text

        config = None
        if response_json:
            try:
                types = importlib.import_module("google.genai.types")
                kwargs: dict[str, Any] = {"response_mime_type": "application/json"}
                if schema:
                    kwargs["response_schema"] = schema
                config = types.GenerateContentConfig(**kwargs)
            except Exception:
                config = None

        if config is None:
            response_obj = self.client.models.generate_content(model=model, contents=prompt)
        else:
            response_obj = self.client.models.generate_content(model=model, contents=prompt, config=config)
        text = _response_text(response_obj)
        tokens = _token_count(response_obj)
        self._log_call(cache_key, model, prompt_hash, prompt, text, tokens, _estimate_cost(tokens, model), False)
        return text

    def _cached(self, cache_key: str) -> LLMCall | None:
        cutoff = now_utc() - timedelta(hours=24)
        with Session(self.engine) as session:
            return session.exec(
                select(LLMCall)
                .where(LLMCall.cache_key == cache_key, LLMCall.created_at >= cutoff, LLMCall.cache_hit == False)  # noqa: E712
                .order_by(LLMCall.created_at.desc())
            ).first()

    def _log_call(
        self,
        cache_key: str,
        model: str,
        prompt_hash: str,
        prompt: str,
        response_text: str,
        tokens: int,
        cost_estimate_eur: float,
        cache_hit: bool,
    ) -> None:
        with Session(self.engine) as session:
            session.add(
                LLMCall(
                    cache_key=cache_key,
                    model=model,
                    prompt_hash=prompt_hash,
                    prompt_preview=prompt[:300],
                    response_text=response_text,
                    tokens=tokens,
                    cost_estimate_eur=cost_estimate_eur,
                    cache_hit=cache_hit,
                )
            )
            session.commit()


def _cache_key(prompt: str, model: str, extra: str = "") -> tuple[str, str]:
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    full_hash = hashlib.sha256(f"{model}\n{prompt}\n{extra}".encode("utf-8")).hexdigest()
    return full_hash, prompt_hash


def _response_text(response_obj: Any) -> str:
    text = getattr(response_obj, "text", None)
    if text:
        return str(text)
    candidates = getattr(response_obj, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        joined = "".join(str(getattr(part, "text", "")) for part in parts)
        if joined:
            return joined
    return ""


def _token_count(response_obj: Any) -> int:
    usage = getattr(response_obj, "usage_metadata", None)
    if not usage:
        return 0
    return int(getattr(usage, "total_token_count", 0) or 0)


def _estimate_cost(tokens: int, model: str) -> float:
    per_million = 0.08 if "flash" in model else 2.0
    return round(tokens / 1_000_000 * per_million, 6)


def _strip_json_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        cleaned = cleaned.removesuffix("```").strip()
    return cleaned


def _json_or_raw(text: str) -> dict[str, Any]:
    try:
        return json.loads(_strip_json_fence(text))
    except json.JSONDecodeError:
        return {"raw_text": text}

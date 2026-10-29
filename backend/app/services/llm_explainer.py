"""
LLM explanation service.

Used only to explain verified, deterministically-computed results.
Never used to generate financial figures, supplier data or feasibility claims.

Falls back to deterministic templates when:
  - LLM_PROVIDER is not configured
  - The LLM returns invalid/unexpected output
  - An exception occurs during the API call
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


_EXPLANATION_SCHEMA = {
    "type": "object",
    "required": ["headline", "explanation", "caveats"],
    "properties": {
        "headline": {"type": "string", "maxLength": 120},
        "explanation": {"type": "string", "maxLength": 2000},
        "caveats": {"type": "array", "items": {"type": "string"}},
    },
}


def _validate_llm_output(data: dict[str, Any]) -> bool:
    """Basic structural validation — never trust model-generated numbers."""
    return (
        isinstance(data.get("headline"), str)
        and isinstance(data.get("explanation"), str)
        and isinstance(data.get("caveats"), list)
    )


def _deterministic_fallback(action_code: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Return a rule-based explanation when LLM is unavailable."""
    action_map = {
        "SWITCH_SUPPLIER": (
            "Consider switching to the identified lower-cost supplier.",
            "Review lead time and quality data independently before changing supplier.",
        ),
        "SPLIT_ORDERS": (
            "Split orders across multiple feasible suppliers to reduce concentration risk.",
            "Confirm minimum order quantities and lead times with each supplier.",
        ),
        "VERIFY_FIRST": (
            "Insufficient verified data to recommend action.",
            "Obtain independent quotations before making any procurement decision.",
        ),
        "ACCEPT_COST": (
            "No cheaper feasible alternative was identified.",
            "Renegotiate with incumbent or accept the modelled incremental cost.",
        ),
        "NO_ACTION": (
            "No material risk identified for this scenario.",
            "Continue monitoring commodity prices.",
        ),
    }
    headline_map = {
        "SWITCH_SUPPLIER": "Supplier switch may reduce exposure",
        "SPLIT_ORDERS": "Order splitting can lower concentration risk",
        "VERIFY_FIRST": "Additional verification required before acting",
        "ACCEPT_COST": "Incumbent supplier remains most competitive",
        "NO_ACTION": "No action required at this time",
    }

    explanation, caveat = action_map.get(action_code, ("No additional explanation.", "Verify independently."))
    return {
        "headline": headline_map.get(action_code, "Analysis complete"),
        "explanation": explanation,
        "caveats": [
            caveat,
            "All supplier and market data in this demonstration is synthetic.",
            "This tool does not place orders or initiate procurement actions.",
        ],
        "source": "deterministic_fallback",
    }


def explain_recommendation(
    action_code: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate a plain-language explanation of a recommendation.
    Uses LLM if configured; falls back to deterministic template otherwise.
    """
    if not settings.llm_provider:
        return _deterministic_fallback(action_code, evidence)

    prompt = (
        "You are a procurement analyst assistant. Explain the following supply-chain "
        "recommendation in plain language suitable for an SMB procurement manager. "
        "Return JSON matching this schema exactly:\n"
        f"{json.dumps(_EXPLANATION_SCHEMA, indent=2)}\n\n"
        "Recommendation data (do NOT invent any numbers not present here):\n"
        f"{json.dumps(evidence, indent=2)}\n"
        "Action code: " + action_code
    )

    try:
        raw = _call_llm(prompt)
        data = json.loads(raw)
        if not _validate_llm_output(data):
            raise ValueError("Schema validation failed")
        data["source"] = settings.llm_provider
        return data
    except Exception as exc:
        logger.warning("LLM explanation failed (%s); using deterministic fallback", exc)
        return _deterministic_fallback(action_code, evidence)


def _call_llm(prompt: str) -> str:
    """
    Route to the configured LLM provider.
    Supported: openai | anthropic | ollama
    """
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return _call_openai(prompt)
    if provider == "anthropic":
        return _call_anthropic(prompt)
    if provider == "ollama":
        return _call_ollama(prompt)
    raise ValueError(f"Unsupported LLM provider: {provider}")


def _call_openai(prompt: str) -> str:
    import httpx  # type: ignore
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={
            "model": settings.llm_model or "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": 600,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _call_anthropic(prompt: str) -> str:
    import httpx  # type: ignore
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.llm_api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": settings.llm_model or "claude-3-haiku-20240307",
            "max_tokens": 600,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def _call_ollama(prompt: str) -> str:
    import httpx  # type: ignore
    base = settings.llm_base_url or "http://localhost:11434"
    resp = httpx.post(
        f"{base}/api/generate",
        json={
            "model": settings.llm_model or "llama3",
            "prompt": prompt,
            "stream": False,
            "format": "json",
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["response"]

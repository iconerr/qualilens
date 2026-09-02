# Copyright 2026 Ashita Aggarwal and Suraj Commuri
# SPDX-License-Identifier: Apache-2.0

"""Unified chat interface over Anthropic, OpenAI, Google, and Mistral.

All calls go direct to the vendor's HTTPS API with the user's own key —
nothing transits any intermediary. Every call returns (text, usage) where
usage = {"input_tokens": int, "output_tokens": int, "stop_reason": str}.

Truncation is treated as an error, not something to paper over: a response
cut off at the max-token limit raises LLMError instead of being passed to a
JSON "repair" step that would fabricate analysis data.
"""

import json
import re
import time
from pathlib import Path

import httpx

TIMEOUT = httpx.Timeout(600.0, connect=15.0)
MAX_RETRIES = 5
BACKOFF_CAP = 60.0

# Compiled-in fallback catalog. The editable catalog lives in models.json
# alongside this file — maintainers update THAT when providers retire or
# release models; this fallback only exists so a missing or invalid
# models.json can never prevent the app from starting.
_FALLBACK_CATALOG = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "default_model": "claude-sonnet-5",
        "models": ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"],
        "pricing": (3.0, 15.0),
    },
    "openai": {
        "label": "OpenAI (GPT)",
        "default_model": "gpt-5.1",
        "models": ["gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o"],
        "pricing": (2.5, 10.0),
    },
    "google": {
        "label": "Google (Gemini)",
        "default_model": "gemini-2.5-pro",
        "models": ["gemini-2.5-pro", "gemini-2.5-flash"],
        "pricing": (1.25, 10.0),
    },
    "mistral": {
        "label": "Mistral",
        "default_model": "mistral-large-latest",
        "models": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
        "pricing": (2.0, 6.0),
    },
}

CATALOG_PATH = Path(__file__).resolve().parent / "models.json"


def _load_catalog() -> dict:
    """Read models.json fresh from disk. NEVER raises: any malformed file —
    unreadable, non-JSON, or valid JSON of the wrong shape — yields the
    compiled-in fallback, because a bad catalog must not stop the app."""
    fallback = {pid: dict(fb) for pid, fb in _FALLBACK_CATALOG.items()}
    try:
        raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback
    if not isinstance(raw, dict):
        return fallback
    out = {}
    for pid, fb in _FALLBACK_CATALOG.items():
        entry = raw.get(pid) if isinstance(raw.get(pid), dict) else {}
        listed = entry.get("models")
        if not isinstance(listed, list):
            listed = []
        models = [m for m in listed if isinstance(m, str) and m.strip()]
        if not models:
            models = list(fb["models"])
        default = entry.get("default_model")
        if not isinstance(default, str) or default not in models:
            default = models[0]
        # pricing_usd_per_mtok is either [input, output] for the provider or
        # {"default": [in, out], "<model id>": [in, out], ...}; the estimate
        # prices the model the project actually chose when it is listed
        raw_pricing = entry.get("pricing_usd_per_mtok")
        per_model = {}
        pricing = None
        if isinstance(raw_pricing, dict):
            for key, val in raw_pricing.items():
                if _valid_pair(val):
                    if key == "default":
                        pricing = tuple(val)
                    else:
                        per_model[str(key)] = tuple(val)
        elif _valid_pair(raw_pricing):
            pricing = tuple(raw_pricing)
        if pricing is None:
            pricing = fb["pricing"]
        out[pid] = {"label": entry.get("label") or fb["label"],
                    "default_model": default, "models": models,
                    "pricing": pricing, "pricing_by_model": per_model}
    return out


def _valid_pair(val) -> bool:
    return (isinstance(val, list) and len(val) == 2
            and all(isinstance(x, (int, float)) and x >= 0 for x in val))


def price_for(provider: str, model: str, catalog_now: dict | None = None) -> tuple:
    """(input, output) USD per million tokens for a model: its own entry when
    the catalog lists one, else the provider default."""
    cat = catalog_now or catalog()
    info = cat.get(provider) or {}
    return tuple(info.get("pricing_by_model", {}).get((model or "").strip(),
                                                      info.get("pricing", (3.0, 15.0))))


PROVIDERS = _load_catalog()


def catalog() -> dict:
    """The catalog as models.json defines it RIGHT NOW. Endpoints that show
    or check models read this, so a maintainer's edit is visible on the next
    request — no restart needed."""
    return _load_catalog()

# USD per 1M tokens (input, output); feeds only the pre-run cost estimate.
DEFAULT_PRICES = {pid: info["pricing"] for pid, info in PROVIDERS.items()}


def list_models(provider: str, api_key: str) -> list:
    """The provider's LIVE model list, via its free list-models endpoint.
    Used by Settings to spot catalog entries a provider has retired."""
    if not api_key:
        raise LLMError("No API key saved for this provider.")
    timeout = httpx.Timeout(30.0, connect=10.0)
    with httpx.Client(timeout=timeout) as client:
        if provider == "anthropic":
            r = client.get("https://api.anthropic.com/v1/models?limit=1000",
                           headers={"x-api-key": api_key,
                                    "anthropic-version": "2023-06-01"})
            r.raise_for_status()
            return sorted(m.get("id", "") for m in r.json().get("data", []))
        if provider == "openai":
            r = client.get("https://api.openai.com/v1/models",
                           headers={"Authorization": f"Bearer {api_key}"})
            r.raise_for_status()
            return sorted(m.get("id", "") for m in r.json().get("data", []))
        if provider == "google":
            r = client.get("https://generativelanguage.googleapis.com/v1beta/models"
                           "?pageSize=1000",
                           headers={"x-goog-api-key": api_key})
            r.raise_for_status()
            out = []
            for m in r.json().get("models", []):
                if "generateContent" in (m.get("supportedGenerationMethods") or []):
                    out.append(str(m.get("name", "")).removeprefix("models/"))
            return sorted(out)
        if provider == "mistral":
            r = client.get("https://api.mistral.ai/v1/models",
                           headers={"Authorization": f"Bearer {api_key}"})
            r.raise_for_status()
            ids = set()
            for m in r.json().get("data", []):
                ids.add(m.get("id", ""))
                for alias in (m.get("aliases") or []):
                    if isinstance(alias, str):
                        ids.add(alias)
            return sorted(ids)
    raise LLMError(f"Unknown provider '{provider}'.")

TRUNCATED = "truncated"  # normalized stop_reason for hit-the-token-limit


class LLMError(Exception):
    pass


def _retry_delay(resp, attempt: int) -> float:
    """Honor Retry-After when the provider sends one; else exponential backoff."""
    if resp is not None:
        ra = resp.headers.get("retry-after")
        if ra:
            try:
                return min(float(ra), BACKOFF_CAP)
            except ValueError:
                pass
    return min(2 ** attempt * 2, BACKOFF_CAP)


def _post_with_retry(url: str, headers: dict, payload: dict,
                     retries: int = MAX_RETRIES) -> dict:
    last_err = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                try:
                    return resp.json()
                except ValueError as e:
                    raise LLMError(f"The provider answered 200 with a body that is not "
                                   f"JSON: {resp.text[:200]!r}") from e
            # retry on rate limit / overload / transient server errors
            if resp.status_code in (408, 429, 500, 502, 503, 504, 529) and attempt < retries:
                time.sleep(_retry_delay(resp, attempt))
                continue
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text[:500]
            raise LLMError(f"HTTP {resp.status_code}: {detail}")
        except httpx.HTTPError as e:
            last_err = e
            if attempt < retries:
                time.sleep(_retry_delay(None, attempt))
                continue
            raise LLMError(f"Network error: {e}") from e
    raise LLMError(f"Exhausted retries: {last_err}")


def _finalize(text: str, usage: dict, stop_reason: str, provider: str, model: str,
              sampling: dict | None = None) -> tuple[str, dict]:
    """Common post-checks: refuse empty output and surface truncation. The
    effective sampling settings ride along in usage so the audit trail can
    record them per call (they differ by provider and are otherwise invisible)."""
    usage["stop_reason"] = stop_reason
    if sampling is not None:
        usage["sampling"] = sampling
    if not text.strip():
        err = LLMError(
            f"{provider}/{model} returned no text (stop reason: {stop_reason}). "
            "For reasoning models this usually means the token budget was consumed "
            "by internal reasoning — try a larger max_tokens or a different model.")
        err.usage = usage   # the tokens were still billed; keep them auditable
        raise err
    return text, usage


def chat(provider: str, model: str, api_key: str, system: str, user: str,
         max_tokens: int = 8000, temperature: float = 0.3,
         retries: int = MAX_RETRIES) -> tuple[str, dict]:
    """_chat_impl plus a diagnosis for the commonest slow failure: the model
    id no longer exists because the provider retired or renamed it."""
    try:
        return _chat_impl(provider, model, api_key, system, user,
                          max_tokens=max_tokens, temperature=temperature,
                          retries=retries)
    except LLMError as e:
        msg = str(e)
        if ("HTTP 404" in msg or "model_not_found" in msg
                or "NOT_FOUND" in msg or "does not exist" in msg
                or "invalid_model" in msg or "Invalid model" in msg):
            hint = LLMError(
                f"{provider} did not accept the model id '{model}' — the provider may "
                "have retired or renamed it. Open Settings and press 'Check models' to "
                "compare this app's catalog with the provider's live list, then start a "
                f"new project with a current model. Original error: {msg}")
            hint.usage = getattr(e, "usage", None)
            raise hint from e
        raise


def _chat_impl(provider: str, model: str, api_key: str, system: str, user: str,
               max_tokens: int = 8000, temperature: float = 0.3,
               retries: int = MAX_RETRIES) -> tuple[str, dict]:
    if not api_key:
        raise LLMError(f"No API key configured for provider '{provider}'.")
    if provider == "anthropic":
        # newer Claude models restrict temperature overrides; the default is
        # appropriate for structured coding work, so we simply omit it
        data = _post_with_retry(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": api_key, "anthropic-version": "2023-06-01",
             "content-type": "application/json"},
            # Claude 5 models think adaptively by default and thinking tokens
            # count against max_tokens — give headroom so the visible answer
            # is not starved (unused headroom costs nothing)
            {"model": model, "max_tokens": max_tokens + 8000,
             "system": system, "messages": [{"role": "user", "content": user}]},
            retries=retries,
        )
        text = "".join(b.get("text", "") for b in data.get("content", []))
        u = data.get("usage", {})
        stop = data.get("stop_reason", "")
        stop = TRUNCATED if stop == "max_tokens" else stop
        return _finalize(text, {"input_tokens": u.get("input_tokens", 0),
                                "output_tokens": u.get("output_tokens", 0)},
                         stop, provider, model,
                         sampling={"temperature": "provider default",
                                   "max_tokens": max_tokens + 8000})

    if provider == "openai":
        payload = {"model": model,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        if model.startswith(("gpt-4", "gpt-3")):
            payload["max_tokens"] = max_tokens
            payload["temperature"] = temperature
            sampling = {"temperature": temperature, "max_tokens": max_tokens}
        else:
            # reasoning-capable models reject max_tokens/temperature overrides;
            # give them headroom for internal reasoning tokens
            payload["max_completion_tokens"] = max_tokens + 8000
            sampling = {"temperature": "provider default",
                        "max_tokens": max_tokens + 8000}
        data = _post_with_retry(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            payload, retries=retries,
        )
        choice = data["choices"][0]
        text = choice["message"].get("content") or ""
        u = data.get("usage", {})
        stop = choice.get("finish_reason", "")
        stop = TRUNCATED if stop == "length" else stop
        return _finalize(text, {"input_tokens": u.get("prompt_tokens", 0),
                                "output_tokens": u.get("completion_tokens", 0)},
                         stop, provider, model, sampling=sampling)

    if provider == "google":
        data = _post_with_retry(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            {"x-goog-api-key": api_key, "content-type": "application/json"},
            {"systemInstruction": {"parts": [{"text": system}]},
             "contents": [{"role": "user", "parts": [{"text": user}]}],
             # Gemini 2.5 spends output tokens on internal "thinking"; give
             # headroom so the visible answer is not starved
             "generationConfig": {"maxOutputTokens": max_tokens + 16384,
                                  "temperature": temperature}},
            retries=retries,
        )
        candidates = data.get("candidates") or []
        if not candidates:
            block = (data.get("promptFeedback") or {}).get("blockReason", "unknown")
            raise LLMError(f"Gemini returned no candidates (block reason: {block}).")
        cand = candidates[0]
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        u = data.get("usageMetadata", {})
        stop = cand.get("finishReason", "")
        stop = TRUNCATED if stop == "MAX_TOKENS" else stop
        return _finalize(text, {"input_tokens": u.get("promptTokenCount", 0),
                                "output_tokens": u.get("candidatesTokenCount", 0)},
                         stop, provider, model,
                         sampling={"temperature": temperature,
                                   "max_tokens": max_tokens + 16384})

    if provider == "mistral":
        data = _post_with_retry(
            "https://api.mistral.ai/v1/chat/completions",
            {"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            {"model": model, "max_tokens": max_tokens, "temperature": temperature,
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": user}]},
            retries=retries,
        )
        choice = data["choices"][0]
        text = choice["message"].get("content") or ""
        u = data.get("usage", {})
        stop = choice.get("finish_reason", "")
        stop = TRUNCATED if stop == "length" else stop
        return _finalize(text, {"input_tokens": u.get("prompt_tokens", 0),
                                "output_tokens": u.get("completion_tokens", 0)},
                         stop, provider, model,
                         sampling={"temperature": temperature, "max_tokens": max_tokens})

    raise LLMError(f"Unknown provider '{provider}'.")


def chat_json(provider: str, model: str, api_key: str, system: str, user: str,
              max_tokens: int = 8000) -> tuple[dict | list, dict]:
    """chat() that expects a JSON object/array back; tolerant of code fences
    and stray prose. A truncated response is an error — repairing it would
    silently fabricate analysis content — so repair is attempted only for
    complete-but-malformed output."""
    sys_prompt = system + "\n\nRespond ONLY with valid JSON. No markdown fences, no commentary."
    text, usage = chat(provider, model, api_key, sys_prompt, user,
                       max_tokens=max_tokens, temperature=0.2)
    if usage.get("stop_reason") == TRUNCATED:
        err = LLMError(
            f"{provider}/{model} output was truncated at the token limit; refusing to "
            "parse a partial JSON response. Re-run — if this recurs, the segment is too "
            "large for the configured output budget.")
        err.usage = usage
        raise err
    try:
        return _extract_json(text), usage
    except ValueError:
        if len(text) > 60000:
            err = LLMError(
                f"{provider}/{model} returned {len(text)} chars of malformed JSON — "
                "too large to repair without risking content loss. Re-run the stage.")
            err.usage = usage
            raise err
        repair, usage2 = chat(
            provider, model, api_key,
            "You repair malformed JSON. Output only the corrected JSON, nothing else. "
            "Preserve the content exactly; never add, remove, or invent fields or values.",
            f"Fix this into valid JSON, preserving all content:\n\n{text}",
            max_tokens=max_tokens, temperature=0.0,
        )
        if usage2.get("stop_reason") == TRUNCATED:
            err = LLMError(f"{provider}/{model}: JSON repair was itself truncated; giving up.")
            err.usage = {k: usage.get(k, 0) + usage2.get(k, 0)
                         for k in ("input_tokens", "output_tokens")}
            raise err
        merged = {k: usage.get(k, 0) + usage2.get(k, 0)
                  for k in ("input_tokens", "output_tokens")}
        merged["stop_reason"] = usage2.get("stop_reason", "")
        merged["sampling"] = usage.get("sampling")
        merged["repair_call"] = True
        return _extract_json(repair), merged


def _extract_json(text: str):
    text = text.strip()
    candidates = []
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        candidates.append(fence.group(1).strip())
    candidates.append(text)
    for cand in candidates:
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass
        # first { or [ to last } or ] within this candidate
        for open_c, close_c in (("{", "}"), ("[", "]")):
            start, end = cand.find(open_c), cand.rfind(close_c)
            if start != -1 and end > start:
                try:
                    return json.loads(cand[start:end + 1])
                except json.JSONDecodeError:
                    continue
    raise ValueError("No parseable JSON in model response")


def estimate_tokens(text: str) -> int:
    return estimate_tokens_from_chars(len(text))


def estimate_tokens_from_chars(n_chars: int) -> int:
    return max(1, n_chars // 4)

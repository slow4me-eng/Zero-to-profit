"""Gemini-backed ZERO TO PROFIT brain.

One Gemini request per research cycle (instead of four specialist calls plus a
synthesis call). This materially reduces free-tier quota pressure.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from google import genai
from google.genai import types

ROLES = {
    "market_scout": "Find zero-upfront-cost customer problems and underserved demand. Prefer reachable customers and urgent problems.",
    "offer_designer": "Turn plausible customer problems into a specific service or digital deliverable that can be sold before spending money.",
    "growth_analyst": "Find practical, non-spam ways to reach first customers and repeat buyers without paid ads.",
    "skeptical_reviewer": "Attack weak assumptions, identify competition and failure risks, and suggest the cheapest validation test.",
}

RULES = """You are ZERO TO PROFIT, an autonomous business-research agent starting with exactly €0.
Focus on legitimate value exchange: services, freelancing, digital products, content,
research, automation and customer-funded work. Avoid scams, deception, spam, fake
engagement, unlawful activity and platform-rule evasion. Never claim money was earned
unless a verified ledger entry exists. Do not recommend paid tools or ad spend.
Return evidence-aware, concise, concrete and testable advice. Clearly label assumptions.
Do not invent customer interviews, sales, market statistics, or proof of demand."""


def _api_key() -> str:
    # Keep compatibility with the existing Render environment variable while
    # also supporting the clearer Gemini-specific name.
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()


def _model() -> str:
    return (os.getenv("GEMINI_MODEL") or os.getenv("OPENAI_MODEL") or "gemini-3.8-flash").strip()


def _fallback(reason: str) -> dict[str, Any]:
    reports = []
    for role in ROLES:
        reports.append((role, {"report": reason, "ideas": []}))
    return {
        "reports": reports,
        "synthesis": {
            "summary": reason,
            "next_experiment": "Wait for the model quota/service to recover, then run one consolidated research cycle.",
            "hypothesis": "A narrowly scoped service can solve a real problem for a reachable buyer.",
            "success_metric": "One qualified reply or one paid pilot, verified outside this dashboard.",
        },
    }


def _extract_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Gemini returned no valid JSON object")
        data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("Gemini response was not a JSON object")
    return data


def _normalise(data: dict[str, Any]) -> dict[str, Any]:
    raw_roles = data.get("reports", {})
    reports = []
    for role in ROLES:
        item = raw_roles.get(role, {}) if isinstance(raw_roles, dict) else {}
        if not isinstance(item, dict):
            item = {"report": str(item)}
        ideas = item.get("ideas", [])
        if not isinstance(ideas, list):
            ideas = []
        clean_ideas = []
        for idea in ideas[:5]:
            if not isinstance(idea, dict) or not idea.get("title"):
                continue
            clean_ideas.append({
                "title": str(idea.get("title", ""))[:180],
                "customer": str(idea.get("customer", ""))[:500],
                "problem": str(idea.get("problem", ""))[:1000],
                "offer": str(idea.get("offer", ""))[:1000],
                "first_step": str(idea.get("first_step", ""))[:1000],
                "score": max(1, min(10, int(idea.get("score", 5)))),
            })
        reports.append((role, {"report": str(item.get("report", "No report returned.")), "ideas": clean_ideas}))
    synthesis = data.get("synthesis", {})
    if not isinstance(synthesis, dict):
        synthesis = {}
    result = {
        "reports": reports,
        "synthesis": {
            "summary": str(synthesis.get("summary", "Research cycle completed.")),
            "next_experiment": str(synthesis.get("next_experiment", "Validate the highest-scoring opportunity with real prospects.")),
            "hypothesis": str(synthesis.get("hypothesis", "A specific offer can solve a real buyer problem.")),
            "success_metric": str(synthesis.get("success_metric", "One qualified reply or paid pilot.")),
        },
    }
    ci = synthesis.get("code_improvement")
    if isinstance(ci, dict) and ci.get("title"):
        result["synthesis"]["code_improvement"] = {
            "title": str(ci.get("title", ""))[:180],
            "rationale": str(ci.get("rationale", ""))[:2000],
            "patch": str(ci.get("patch", ""))[:5000],
        }
    return result


def orchestrate(state: dict[str, Any]) -> dict[str, Any]:
    key = _api_key()
    if not key:
        return _fallback("AI is not configured. Add a Gemini API key in Render environment variables.")

    history = json.dumps(state.get("events", [])[:12], ensure_ascii=False, default=str)
    prompt = f"""{RULES}

You must perform the following four specialist perspectives in ONE response:
{json.dumps(ROLES, ensure_ascii=False)}

Recent memory:
{history[:10000]}

Research current-feeling opportunities using your knowledge, but do not pretend to have browsed the live web.
Prioritise offers that can be delivered by one person from a phone/computer with €0 upfront.
Return ONLY valid JSON with this exact structure:
{{
  "reports": {{
    "market_scout": {{"report": "...", "ideas": [{{"title":"...","customer":"...","problem":"...","offer":"...","first_step":"...","score":1}}]}},
    "offer_designer": {{"report": "...", "ideas": []}},
    "growth_analyst": {{"report": "...", "ideas": []}},
    "skeptical_reviewer": {{"report": "...", "ideas": []}}
  }},
  "synthesis": {{"summary":"...","next_experiment":"...","hypothesis":"...","success_metric":"...","code_improvement":{{"title":"...","rationale":"...","patch":"..."}}}}
}}
Use no more than 2 ideas per role. Do not repeat the same idea across roles. Omit code_improvement if there is no concrete, safe improvement.
"""
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )
        return _normalise(_extract_json(response.text or ""))
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        lowered = message.lower()
        if any(token in lowered for token in ("429", "resource_exhausted", "quota", "rate limit")):
            reason = "Gemini quota/rate limit reached. AI research is paused to avoid repeated failed requests. Check your Google AI Studio quota or wait for its reset. Details: " + message[:900]
        elif any(token in lowered for token in ("503", "unavailable", "overloaded")):
            reason = "Gemini is temporarily unavailable/overloaded. This cycle was safely skipped; the next scheduled cycle can retry. Details: " + message[:900]
        else:
            reason = "Gemini request failed. Check the model name, API key and Render logs. Details: " + message[:900]
        return _fallback(reason)


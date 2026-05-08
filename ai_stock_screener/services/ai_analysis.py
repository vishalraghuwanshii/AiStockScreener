from __future__ import annotations

import json
import re
from typing import Any

import requests
import streamlit as st

from config import AI_REQUEST_TIMEOUT, KIE_API_KEY, KIE_API_URL, KIE_MODEL
from utils.helpers import make_json_safe


AI_SECTION_LABELS = {
    "executive_summary": "Executive Summary",
    "valuation_analysis": "Valuation Analysis",
    "growth_analysis": "Growth Analysis",
    "balance_sheet_quality": "Balance Sheet Quality",
    "technical_analysis": "Technical Analysis",
    "swing_trade_setup": "Swing Trade Setup",
    "support_and_resistance": "Support and Resistance",
    "bullish_thesis": "Bullish Thesis",
    "bearish_thesis": "Bearish Thesis",
    "risk_factors": "Risk Factors",
    "investment_score": "Investment Score",
}


def build_ai_payload(profile: dict[str, Any], technical_summary: dict[str, Any]) -> dict[str, Any]:
    return make_json_safe(
        {
            "ticker": profile.get("ticker"),
            "market_data": profile.get("snapshot"),
            "fundamentals": profile.get("fundamentals"),
            "technical_summary": technical_summary,
        }
    )


def serialize_ai_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _build_prompt(stock_payload: dict[str, Any]) -> str:
    metrics_json = json.dumps(stock_payload, indent=2, default=str)
    return f"""
You are an institutional equity analyst and technical market strategist.

Analyze the stock using only the supplied market data, fundamentals, and technical indicators.
Be concise, specific, and balanced. Do not invent missing numbers. Mention when data is unavailable.

Return valid JSON only. Do not wrap the JSON in markdown.

Required JSON schema:
{{
  "executive_summary": "string",
  "valuation_analysis": "string",
  "growth_analysis": "string",
  "balance_sheet_quality": "string",
  "technical_analysis": "string",
  "swing_trade_setup": "string",
  "support_and_resistance": "string",
  "bullish_thesis": ["string"],
  "bearish_thesis": ["string"],
  "risk_factors": ["string"],
  "investment_score": 0
}}

Score rules:
- investment_score must be an integer from 0 to 100.
- 0 means extremely unattractive risk/reward.
- 50 means neutral or insufficient edge.
- 100 means exceptional risk/reward.

Stock metrics:
{metrics_json}
""".strip()


def _extract_text(response_data: dict[str, Any]) -> str:
    content = response_data.get("content")
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text")
                if text:
                    text_parts.append(str(text))
            elif isinstance(item, str):
                text_parts.append(item)
        if text_parts:
            return "\n".join(text_parts)

    if isinstance(content, str):
        return content

    choices = response_data.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        if isinstance(message, dict) and message.get("content"):
            return str(message["content"])

    if response_data.get("output_text"):
        return str(response_data["output_text"])

    return json.dumps(response_data)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return fenced.group(1).strip() if fenced else text


def _parse_json_response(text: str) -> dict[str, Any] | None:
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _lookup_section(parsed: dict[str, Any], key: str, label: str) -> Any:
    candidates = {
        key,
        label,
        label.lower(),
        label.replace(" ", "_").lower(),
        label.replace(" ", "").lower(),
    }
    for candidate in candidates:
        if candidate in parsed:
            return parsed[candidate]
    return None


def normalize_ai_response(raw_text: str) -> dict[str, Any]:
    parsed = _parse_json_response(raw_text)
    if not isinstance(parsed, dict):
        return {
            "status": "ok",
            "raw_response": raw_text,
            "sections": {},
            "investment_score": None,
        }

    sections = {}
    for key, label in AI_SECTION_LABELS.items():
        value = _lookup_section(parsed, key, label)
        if key == "investment_score":
            continue
        sections[key] = value

    score = _lookup_section(parsed, "investment_score", "Investment Score")
    try:
        score = int(round(float(score)))
        score = max(0, min(100, score))
    except (TypeError, ValueError):
        score = None

    return {
        "status": "ok",
        "raw_response": raw_text,
        "sections": sections,
        "investment_score": score,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def analyze_stock_with_ai(serialized_payload: str) -> dict[str, Any]:
    if not KIE_API_KEY:
        return {
            "status": "missing_key",
            "message": "KIE_API_KEY is not configured. Add it to .env to enable AI analysis.",
        }

    stock_payload = json.loads(serialized_payload)
    prompt = _build_prompt(stock_payload)
    request_payload = {
        "model": KIE_MODEL,
        "max_tokens": 2200,
        "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Authorization": f"Bearer {KIE_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            KIE_API_URL,
            headers=headers,
            json=request_payload,
            timeout=AI_REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        return {"status": "error", "message": "AI analysis timed out. Please try again."}
    except requests.RequestException:
        return {"status": "error", "message": "AI analysis service is unavailable right now."}

    if response.status_code >= 400:
        return {
            "status": "error",
            "message": f"AI analysis failed with status {response.status_code}. Check your API key and quota.",
        }

    try:
        response_data = response.json()
    except ValueError:
        return {"status": "error", "message": "AI analysis returned an invalid response."}

    raw_text = _extract_text(response_data)
    return normalize_ai_response(raw_text)

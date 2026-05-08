from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


def render_metric_card(
    label: str,
    value: Any,
    delta: str | None = None,
    caption: str | None = None,
    tone: str = "neutral",
) -> None:
    tone = tone if tone in {"positive", "negative", "warning", "neutral"} else "neutral"
    delta_html = f"<span class='metric-delta {tone}'>{escape(str(delta))}</span>" if delta else ""
    caption_html = f"<div class='metric-caption'>{escape(str(caption))}</div>" if caption else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{escape(str(label))}</div>
            <div class="metric-value">{escape(str(value))}</div>
            {delta_html}
            {caption_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_grid(cards: list[dict[str, Any]], columns: int = 4) -> None:
    if not cards:
        return
    column_group = st.columns(columns)
    for index, card in enumerate(cards):
        with column_group[index % columns]:
            render_metric_card(**card)

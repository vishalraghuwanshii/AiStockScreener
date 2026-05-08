from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD, SMAIndicator
from ta.volume import VolumeWeightedAveragePrice
from ta.volatility import AverageTrueRange, BollingerBands

from config import CACHE_TTL_SECONDS
from utils.helpers import first_number, value_to_float


def _assign_indicator(dataframe: pd.DataFrame, column: str, builder) -> None:
    try:
        dataframe[column] = builder()
    except Exception:
        dataframe[column] = pd.NA


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def calculate_technical_indicators(history: pd.DataFrame) -> pd.DataFrame:
    dataframe = history.copy()
    for column in ["Open", "High", "Low", "Close", "Volume"]:
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

    close = dataframe["Close"]
    high = dataframe["High"]
    low = dataframe["Low"]
    volume = dataframe["Volume"].fillna(0)

    _assign_indicator(dataframe, "RSI", lambda: RSIIndicator(close=close, window=14).rsi())

    macd = MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
    _assign_indicator(dataframe, "MACD", macd.macd)
    _assign_indicator(dataframe, "MACD_SIGNAL", macd.macd_signal)
    _assign_indicator(dataframe, "MACD_HIST", macd.macd_diff)

    for window in (20, 50, 200):
        _assign_indicator(dataframe, f"EMA{window}", lambda window=window: EMAIndicator(close=close, window=window).ema_indicator())

    for window in (50, 200):
        _assign_indicator(dataframe, f"SMA{window}", lambda window=window: SMAIndicator(close=close, window=window).sma_indicator())

    bollinger = BollingerBands(close=close, window=20, window_dev=2)
    _assign_indicator(dataframe, "BB_HIGH", bollinger.bollinger_hband)
    _assign_indicator(dataframe, "BB_MID", bollinger.bollinger_mavg)
    _assign_indicator(dataframe, "BB_LOW", bollinger.bollinger_lband)

    if len(dataframe) >= 14:
        _assign_indicator(dataframe, "ATR", lambda: AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range())
        _assign_indicator(
            dataframe,
            "VWAP",
            lambda: VolumeWeightedAveragePrice(high=high, low=low, close=close, volume=volume, window=14).volume_weighted_average_price(),
        )
    else:
        dataframe["ATR"] = pd.NA
        dataframe["VWAP"] = pd.NA

    return dataframe


def _crossover(previous_fast: Any, previous_slow: Any, latest_fast: Any, latest_slow: Any) -> str | None:
    previous_fast = value_to_float(previous_fast)
    previous_slow = value_to_float(previous_slow)
    latest_fast = value_to_float(latest_fast)
    latest_slow = value_to_float(latest_slow)

    if None in (previous_fast, previous_slow, latest_fast, latest_slow):
        return None
    if previous_fast <= previous_slow and latest_fast > latest_slow:
        return "bullish_crossover"
    if previous_fast >= previous_slow and latest_fast < latest_slow:
        return "bearish_crossover"
    if latest_fast > latest_slow:
        return "bullish"
    if latest_fast < latest_slow:
        return "bearish"
    return "neutral"


def _signal(label: str, tone: str, detail: str) -> dict[str, str]:
    return {"label": label, "tone": tone, "detail": detail}


def generate_technical_signals(dataframe: pd.DataFrame) -> dict[str, dict[str, str]]:
    if dataframe.empty:
        return {}

    latest = dataframe.iloc[-1]
    previous = dataframe.iloc[-2] if len(dataframe) > 1 else latest

    price = value_to_float(latest.get("Close"))
    ema20 = value_to_float(latest.get("EMA20"))
    ema50 = value_to_float(latest.get("EMA50"))
    ema200 = value_to_float(latest.get("EMA200"))
    rsi = value_to_float(latest.get("RSI"))

    signals: dict[str, dict[str, str]] = {}

    if None not in (price, ema50, ema200):
        if price > ema50 > ema200:
            signals["trend"] = _signal("Bullish trend", "positive", "Price is above EMA50 and EMA50 is above EMA200.")
        elif price < ema50 < ema200:
            signals["trend"] = _signal("Bearish trend", "negative", "Price is below EMA50 and EMA50 is below EMA200.")
        else:
            signals["trend"] = _signal("Mixed trend", "neutral", "Moving averages are not aligned in one direction.")
    elif None not in (price, ema50):
        tone = "positive" if price > ema50 else "negative"
        signals["trend"] = _signal("Short trend", tone, "Trend is based on price relative to EMA50.")

    if rsi is not None:
        if rsi >= 70:
            signals["rsi"] = _signal("RSI overbought", "warning", "RSI is above 70, which can signal stretched momentum.")
        elif rsi <= 30:
            signals["rsi"] = _signal("RSI oversold", "positive", "RSI is below 30, which can signal a rebound zone.")
        else:
            signals["rsi"] = _signal("RSI neutral", "neutral", "RSI is between 30 and 70.")

    ema_state = _crossover(previous.get("EMA20"), previous.get("EMA50"), ema20, ema50)
    if ema_state == "bullish_crossover":
        signals["ema_crossover"] = _signal("EMA bullish crossover", "positive", "EMA20 crossed above EMA50.")
    elif ema_state == "bearish_crossover":
        signals["ema_crossover"] = _signal("EMA bearish crossover", "negative", "EMA20 crossed below EMA50.")
    elif ema_state == "bullish":
        signals["ema_crossover"] = _signal("EMA bullish alignment", "positive", "EMA20 is above EMA50.")
    elif ema_state == "bearish":
        signals["ema_crossover"] = _signal("EMA bearish alignment", "negative", "EMA20 is below EMA50.")

    macd_state = _crossover(previous.get("MACD"), previous.get("MACD_SIGNAL"), latest.get("MACD"), latest.get("MACD_SIGNAL"))
    if macd_state == "bullish_crossover":
        signals["macd_crossover"] = _signal("MACD bullish crossover", "positive", "MACD crossed above its signal line.")
    elif macd_state == "bearish_crossover":
        signals["macd_crossover"] = _signal("MACD bearish crossover", "negative", "MACD crossed below its signal line.")
    elif macd_state == "bullish":
        signals["macd_crossover"] = _signal("MACD above signal", "positive", "MACD remains above its signal line.")
    elif macd_state == "bearish":
        signals["macd_crossover"] = _signal("MACD below signal", "negative", "MACD remains below its signal line.")

    return signals


def estimate_support_resistance(dataframe: pd.DataFrame, lookback: int = 60) -> dict[str, float | None]:
    if dataframe.empty:
        return {"support": None, "resistance": None}

    recent = dataframe.tail(min(lookback, len(dataframe)))
    return {
        "support": first_number(recent["Low"].min()),
        "resistance": first_number(recent["High"].max()),
    }


def get_latest_technical_values(dataframe: pd.DataFrame) -> dict[str, Any]:
    if dataframe.empty:
        return {}

    latest = dataframe.iloc[-1]
    keys = [
        "Close",
        "RSI",
        "MACD",
        "MACD_SIGNAL",
        "MACD_HIST",
        "EMA20",
        "EMA50",
        "EMA200",
        "SMA50",
        "SMA200",
        "BB_HIGH",
        "BB_MID",
        "BB_LOW",
        "ATR",
        "VWAP",
    ]
    return {key: latest.get(key) for key in keys}


def build_technical_summary(dataframe: pd.DataFrame) -> dict[str, Any]:
    return {
        "latest": get_latest_technical_values(dataframe),
        "signals": generate_technical_signals(dataframe),
        "support_resistance": estimate_support_resistance(dataframe),
    }

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf

from config import CACHE_TTL_SECONDS
from utils.helpers import (
    display_ticker,
    first_number,
    first_present,
    is_indian_ticker,
    normalize_ticker,
)


class MarketDataError(Exception):
    """Raised when market data cannot be loaded or validated."""


FUNDAMENTAL_SECTIONS = {
    "valuation": {
        "title": "Valuation",
        "metrics": [
            ("trailing_pe", "Trailing PE", ("trailingPE",), "ratio"),
            ("forward_pe", "Forward PE", ("forwardPE",), "ratio"),
            ("peg_ratio", "PEG Ratio", ("pegRatio",), "ratio"),
            ("price_to_book", "Price to Book", ("priceToBook",), "ratio"),
            ("enterprise_value", "Enterprise Value", ("enterpriseValue",), "currency"),
            ("ev_to_ebitda", "EV / EBITDA", ("enterpriseToEbitda",), "ratio"),
            ("dividend_yield", "Dividend Yield", ("dividendYield",), "percent"),
            ("payout_ratio", "Payout Ratio", ("payoutRatio",), "percent"),
        ],
    },
    "profitability": {
        "title": "Profitability",
        "metrics": [
            ("roe", "ROE", ("returnOnEquity",), "percent"),
            ("roa", "ROA", ("returnOnAssets",), "percent"),
            ("gross_margins", "Gross Margins", ("grossMargins",), "percent"),
            ("operating_margins", "Operating Margins", ("operatingMargins",), "percent"),
            ("profit_margins", "Profit Margins", ("profitMargins",), "percent"),
        ],
    },
    "growth": {
        "title": "Growth",
        "metrics": [
            ("revenue_growth", "Revenue Growth", ("revenueGrowth",), "percent"),
            ("earnings_growth", "Earnings Growth", ("earningsGrowth",), "percent"),
            (
                "quarterly_growth",
                "Quarterly Growth",
                ("earningsQuarterlyGrowth", "revenueQuarterlyGrowth", "quarterlyRevenueGrowth"),
                "percent",
            ),
        ],
    },
    "financial_health": {
        "title": "Financial Health",
        "metrics": [
            ("debt_to_equity", "Debt to Equity", ("debtToEquity",), "number"),
            ("current_ratio", "Current Ratio", ("currentRatio",), "ratio"),
            ("quick_ratio", "Quick Ratio", ("quickRatio",), "ratio"),
            ("total_cash", "Total Cash", ("totalCash",), "currency"),
            ("total_debt", "Total Debt", ("totalDebt",), "currency"),
            ("free_cash_flow", "Free Cash Flow", ("freeCashflow", "freeCashFlow"), "currency"),
        ],
    },
}


def _safe_info(ticker_obj: yf.Ticker) -> dict[str, Any]:
    try:
        info = ticker_obj.get_info()
        return info if isinstance(info, dict) else {}
    except Exception:
        return {}


def _safe_fast_info(ticker_obj: yf.Ticker) -> dict[str, Any]:
    fast_info: dict[str, Any] = {}
    keys = [
        "currency",
        "day_high",
        "day_low",
        "last_price",
        "market_cap",
        "open",
        "previous_close",
        "shares",
        "ten_day_average_volume",
        "three_month_average_volume",
        "year_high",
        "year_low",
    ]
    try:
        raw_fast_info = ticker_obj.fast_info
        for key in keys:
            try:
                fast_info[key] = raw_fast_info.get(key)
            except Exception:
                fast_info[key] = getattr(raw_fast_info, key, None)
    except Exception:
        pass
    return fast_info


def _first_info_value(info: dict[str, Any], keys: tuple[str, ...]) -> Any:
    return first_present(*(info.get(key) for key in keys))


def _fetch_history(ticker_obj: yf.Ticker, period: str, interval: str) -> pd.DataFrame:
    try:
        history = ticker_obj.history(period=period, interval=interval, auto_adjust=False, actions=False)
    except Exception as exc:
        raise MarketDataError("Market data provider did not respond. Please try again.") from exc

    if history is None or history.empty:
        raise MarketDataError("No price history was found for this ticker.")

    required_columns = ["Open", "High", "Low", "Close", "Volume"]
    missing_columns = [column for column in required_columns if column not in history.columns]
    if missing_columns:
        raise MarketDataError("Price history is incomplete for this ticker.")

    history = history[required_columns].copy()
    history.index = pd.to_datetime(history.index)
    history = history.dropna(subset=["Open", "High", "Low", "Close"])
    history["Volume"] = history["Volume"].fillna(0)

    if history.empty:
        raise MarketDataError("No usable price history was found for this ticker.")

    return history


def _build_market_snapshot(
    ticker: str,
    info: dict[str, Any],
    fast_info: dict[str, Any],
    history: pd.DataFrame,
) -> dict[str, Any]:
    closes = history["Close"].dropna()
    last_close = closes.iloc[-1] if not closes.empty else None
    previous_history_close = closes.iloc[-2] if len(closes) > 1 else None

    currency = first_present(
        info.get("currency"),
        info.get("financialCurrency"),
        fast_info.get("currency"),
        "INR" if is_indian_ticker(ticker) else "USD",
    )
    current_price = first_number(
        info.get("currentPrice"),
        info.get("regularMarketPrice"),
        fast_info.get("last_price"),
        last_close,
    )
    previous_close = first_number(
        info.get("previousClose"),
        info.get("regularMarketPreviousClose"),
        fast_info.get("previous_close"),
        previous_history_close,
    )

    day_change_percent = None
    if current_price is not None and previous_close not in (None, 0):
        day_change_percent = ((current_price - previous_close) / previous_close) * 100

    return {
        "ticker": ticker,
        "display_ticker": display_ticker(ticker),
        "company_name": first_present(info.get("longName"), info.get("shortName"), display_ticker(ticker)),
        "currency": currency,
        "exchange": first_present(info.get("exchange"), info.get("fullExchangeName")),
        "current_price": current_price,
        "day_change_percent": day_change_percent,
        "open": first_number(info.get("open"), info.get("regularMarketOpen"), fast_info.get("open"), history["Open"].iloc[-1]),
        "previous_close": previous_close,
        "day_high": first_number(
            info.get("dayHigh"),
            info.get("regularMarketDayHigh"),
            fast_info.get("day_high"),
            history["High"].iloc[-1],
        ),
        "day_low": first_number(
            info.get("dayLow"),
            info.get("regularMarketDayLow"),
            fast_info.get("day_low"),
            history["Low"].iloc[-1],
        ),
        "volume": first_number(info.get("volume"), info.get("regularMarketVolume"), history["Volume"].iloc[-1]),
        "average_volume": first_number(
            info.get("averageVolume"),
            info.get("averageDailyVolume10Day"),
            fast_info.get("three_month_average_volume"),
            fast_info.get("ten_day_average_volume"),
        ),
        "fifty_two_week_high": first_number(info.get("fiftyTwoWeekHigh"), fast_info.get("year_high")),
        "fifty_two_week_low": first_number(info.get("fiftyTwoWeekLow"), fast_info.get("year_low")),
        "market_cap": first_number(info.get("marketCap"), fast_info.get("market_cap")),
        "beta": first_number(info.get("beta")),
        "shares_outstanding": first_number(info.get("sharesOutstanding"), fast_info.get("shares")),
        "float_shares": first_number(info.get("floatShares")),
        "sector": first_present(info.get("sector"), "N/A"),
        "industry": first_present(info.get("industry"), "N/A"),
    }


def _build_fundamentals(info: dict[str, Any], currency: str) -> dict[str, Any]:
    sections: dict[str, Any] = {}

    for section_key, section in FUNDAMENTAL_SECTIONS.items():
        metrics = []
        for metric_key, label, info_keys, kind in section["metrics"]:
            metrics.append(
                {
                    "key": metric_key,
                    "label": label,
                    "value": _first_info_value(info, info_keys),
                    "kind": kind,
                    "currency": currency,
                }
            )
        sections[section_key] = {"title": section["title"], "metrics": metrics}

    sections["company_info"] = {
        "title": "Company Info",
        "company_name": first_present(info.get("longName"), info.get("shortName"), "N/A"),
        "sector": first_present(info.get("sector"), "N/A"),
        "industry": first_present(info.get("industry"), "N/A"),
        "business_summary": first_present(info.get("longBusinessSummary"), "No company summary is available from Yahoo Finance."),
    }
    return sections


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_market_profile(ticker_query: str, period: str = "1y", interval: str = "1d") -> dict[str, Any]:
    ticker = normalize_ticker(ticker_query)
    ticker_obj = yf.Ticker(ticker)

    history = _fetch_history(ticker_obj, period=period, interval=interval)
    info = _safe_info(ticker_obj)
    fast_info = _safe_fast_info(ticker_obj)

    snapshot = _build_market_snapshot(ticker, info, fast_info, history)
    fundamentals = _build_fundamentals(info, snapshot["currency"])

    return {
        "ticker": ticker,
        "history": history,
        "snapshot": snapshot,
        "fundamentals": fundamentals,
        "raw_info": info,
    }

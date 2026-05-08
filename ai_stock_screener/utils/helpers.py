import math
import re
from collections.abc import Mapping, Sequence
from numbers import Number
from typing import Any

from config import CURRENCY_SYMBOLS, SUPPORTED_INDIAN_TICKERS


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, Number):
        try:
            return math.isnan(float(value))
        except (TypeError, ValueError, OverflowError):
            return False
    return False


def value_to_float(value: Any) -> float | None:
    if is_missing(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def first_present(*values: Any) -> Any:
    for value in values:
        if not is_missing(value):
            return value
    return None


def first_number(*values: Any) -> float | None:
    for value in values:
        number = value_to_float(value)
        if number is not None:
            return number
    return None


def normalize_ticker(raw_ticker: str) -> str:
    ticker = (raw_ticker or "").strip().upper().replace(" ", "")
    if not ticker:
        return "AAPL"

    if "." in ticker or ticker.startswith("^"):
        return ticker

    ticker = re.sub(r"[^A-Z0-9-]", "", ticker)
    if ticker in SUPPORTED_INDIAN_TICKERS:
        return f"{ticker}.NS"

    return ticker


def display_ticker(ticker: str) -> str:
    ticker = (ticker or "").upper()
    return ticker[:-3] if ticker.endswith(".NS") else ticker


def is_indian_ticker(ticker: str) -> bool:
    return (ticker or "").upper().endswith(".NS")


def trim_trailing_zeroes(value: str) -> str:
    if "." not in value:
        return value
    return value.rstrip("0").rstrip(".")


def compact_number(value: Any, decimals: int = 2) -> str:
    number = value_to_float(value)
    if number is None:
        return "N/A"

    absolute = abs(number)
    units = (
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    )

    for threshold, suffix in units:
        if absolute >= threshold:
            formatted = f"{number / threshold:,.{decimals}f}"
            return f"{trim_trailing_zeroes(formatted)}{suffix}"

    formatted = f"{number:,.{decimals}f}"
    return trim_trailing_zeroes(formatted)


def format_number(value: Any, decimals: int = 2, compact: bool = False) -> str:
    number = value_to_float(value)
    if number is None:
        return "N/A"
    if compact:
        return compact_number(number, decimals=decimals)
    formatted = f"{number:,.{decimals}f}"
    return trim_trailing_zeroes(formatted)


def format_currency(
    value: Any,
    currency: str = "USD",
    decimals: int = 2,
    compact: bool = False,
) -> str:
    number = value_to_float(value)
    if number is None:
        return "N/A"

    symbol = CURRENCY_SYMBOLS.get((currency or "").upper(), f"{currency} " if currency else "")
    if compact:
        return f"{symbol}{compact_number(number, decimals=decimals)}"

    formatted = f"{number:,.{decimals}f}"
    return f"{symbol}{trim_trailing_zeroes(formatted)}"


def format_percentage(value: Any, decimals: int = 2, from_decimal: bool = True) -> str:
    number = value_to_float(value)
    if number is None:
        return "N/A"
    if from_decimal:
        number *= 100
    formatted = f"{number:,.{decimals}f}"
    return f"{trim_trailing_zeroes(formatted)}%"


def format_ratio(value: Any, decimals: int = 2) -> str:
    number = value_to_float(value)
    if number is None:
        return "N/A"
    return f"{trim_trailing_zeroes(f'{number:,.{decimals}f}')}x"


def format_metric_value(value: Any, kind: str, currency: str = "USD") -> str:
    if kind == "currency":
        return format_currency(value, currency=currency, compact=True)
    if kind == "price":
        return format_currency(value, currency=currency, compact=False)
    if kind == "percent":
        return format_percentage(value, from_decimal=True)
    if kind == "price_percent":
        return format_percentage(value, from_decimal=False)
    if kind == "ratio":
        return format_ratio(value)
    if kind == "integer":
        return format_number(value, decimals=0, compact=True)
    if kind == "compact":
        return format_number(value, compact=True)
    return format_number(value)


def make_json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [make_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return make_json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except (TypeError, ValueError):
            pass
    if is_missing(value):
        return None
    return value

from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

KIE_API_KEY = os.getenv("KIE_API_KEY", "").strip()
KIE_API_URL = os.getenv("KIE_API_URL", "https://api.kie.ai/claude/v1/messages").strip()
KIE_MODEL = os.getenv("KIE_MODEL", "claude-opus-4-7").strip()
AI_REQUEST_TIMEOUT = int(os.getenv("AI_REQUEST_TIMEOUT", "35"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "900"))

DEFAULT_TICKER = "AAPL"

SUPPORTED_US_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA"]
SUPPORTED_INDIAN_TICKERS = ["RELIANCE", "TCS", "INFY", "WAAREEENER"]

PERIOD_OPTIONS = {
    "6M": "6mo",
    "1Y": "1y",
    "2Y": "2y",
    "5Y": "5y",
}
DEFAULT_PERIOD_LABEL = "1Y"

INTERVAL_OPTIONS = {
    "Daily": "1d",
    "Weekly": "1wk",
}
DEFAULT_INTERVAL_LABEL = "Daily"

CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "INR ",
    "EUR": "EUR ",
    "GBP": "GBP ",
    "JPY": "JPY ",
}

THEME = {
    "background": "#070A12",
    "panel": "rgba(12, 18, 32, 0.76)",
    "panel_strong": "rgba(17, 24, 39, 0.88)",
    "border": "rgba(148, 163, 184, 0.18)",
    "text": "#E5E7EB",
    "muted": "#94A3B8",
    "positive": "#2DD4BF",
    "negative": "#FB7185",
    "warning": "#FBBF24",
    "accent": "#60A5FA",
    "violet": "#A78BFA",
}

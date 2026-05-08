from __future__ import annotations

from typing import Any

import streamlit as st

from components.charts import create_candlestick_chart, create_macd_chart, create_rsi_chart
from components.metric_cards import render_metric_card, render_metric_grid
from config import (
    DEFAULT_INTERVAL_LABEL,
    DEFAULT_PERIOD_LABEL,
    DEFAULT_TICKER,
    INTERVAL_OPTIONS,
    PERIOD_OPTIONS,
    SUPPORTED_INDIAN_TICKERS,
    SUPPORTED_US_TICKERS,
)
from services.ai_analysis import AI_SECTION_LABELS, analyze_stock_with_ai, build_ai_payload, serialize_ai_payload
from services.market_data import MarketDataError, get_market_profile
from services.technicals import build_technical_summary, calculate_technical_indicators
from utils.helpers import (
    display_ticker,
    format_currency,
    format_metric_value,
    format_number,
    format_percentage,
    normalize_ticker,
    value_to_float,
)


st.set_page_config(
    page_title="AI Stock Screener",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            color-scheme: dark;
        }

        html, body, [class*="css"] {
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at 16% 8%, rgba(45, 212, 191, 0.13), transparent 32%),
                radial-gradient(circle at 84% 4%, rgba(96, 165, 250, 0.15), transparent 30%),
                radial-gradient(circle at 72% 84%, rgba(167, 139, 250, 0.12), transparent 34%),
                #070A12;
            color: #E5E7EB;
        }

        .block-container {
            max-width: 1480px;
            padding-top: 1.2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: rgba(8, 13, 25, 0.82);
            border-right: 1px solid rgba(148, 163, 184, 0.16);
        }

        [data-testid="stSidebar"] * {
            color: #E5E7EB;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: #94A3B8;
        }

        .sidebar-brand {
            padding: 0.4rem 0 1rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.14);
            margin-bottom: 1.1rem;
        }

        .sidebar-brand h2 {
            margin: 0;
            font-size: 1.06rem;
            letter-spacing: 0;
            color: #F8FAFC;
        }

        .sidebar-brand span {
            display: block;
            margin-top: 0.28rem;
            font-size: 0.78rem;
            color: #94A3B8;
        }

        .hero {
            display: flex;
            justify-content: space-between;
            gap: 1.5rem;
            align-items: flex-end;
            padding: 1.35rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.56)),
                rgba(12, 18, 32, 0.76);
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.28);
            backdrop-filter: blur(18px);
            margin-bottom: 1.05rem;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            padding: 0.18rem 0.52rem;
            border: 1px solid rgba(96, 165, 250, 0.26);
            border-radius: 999px;
            color: #BFDBFE;
            background: rgba(96, 165, 250, 0.1);
            font-size: 0.74rem;
            font-weight: 700;
            margin-bottom: 0.75rem;
        }

        .hero h1 {
            margin: 0;
            font-size: clamp(2.1rem, 5vw, 4.55rem);
            line-height: 0.96;
            letter-spacing: 0;
            color: #F8FAFC;
        }

        .hero-subtitle {
            margin-top: 0.75rem;
            color: #CBD5E1;
            font-size: 0.96rem;
        }

        .hero-price {
            min-width: 250px;
            text-align: right;
        }

        .price {
            display: block;
            font-size: clamp(2rem, 4vw, 3.7rem);
            font-weight: 800;
            letter-spacing: 0;
            color: #F8FAFC;
        }

        .change-pill {
            display: inline-flex;
            margin-top: 0.55rem;
            padding: 0.32rem 0.62rem;
            border-radius: 999px;
            font-size: 0.86rem;
            font-weight: 700;
        }

        .positive {
            color: #2DD4BF !important;
        }

        .negative {
            color: #FB7185 !important;
        }

        .warning {
            color: #FBBF24 !important;
        }

        .neutral {
            color: #CBD5E1 !important;
        }

        .change-pill.positive {
            background: rgba(45, 212, 191, 0.12);
            border: 1px solid rgba(45, 212, 191, 0.22);
        }

        .change-pill.negative {
            background: rgba(251, 113, 133, 0.12);
            border: 1px solid rgba(251, 113, 133, 0.22);
        }

        .metric-card {
            min-height: 112px;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid rgba(148, 163, 184, 0.17);
            background: rgba(12, 18, 32, 0.72);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
            backdrop-filter: blur(16px);
            margin-bottom: 0.85rem;
        }

        .metric-label {
            color: #94A3B8;
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
        }

        .metric-value {
            margin-top: 0.42rem;
            color: #F8FAFC;
            font-size: 1.45rem;
            font-weight: 800;
            line-height: 1.08;
            word-break: break-word;
        }

        .metric-delta {
            display: inline-block;
            margin-top: 0.35rem;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .metric-caption {
            margin-top: 0.35rem;
            color: #94A3B8;
            font-size: 0.8rem;
            line-height: 1.35;
        }

        .section-title {
            color: #F8FAFC;
            font-size: 1.05rem;
            font-weight: 800;
            margin: 0.35rem 0 0.8rem;
        }

        .glass-panel {
            border-radius: 8px;
            border: 1px solid rgba(148, 163, 184, 0.17);
            background: rgba(12, 18, 32, 0.72);
            backdrop-filter: blur(16px);
            padding: 1rem;
            margin-bottom: 1rem;
        }

        .glass-panel p, .glass-panel li {
            color: #CBD5E1;
            font-size: 0.95rem;
            line-height: 1.58;
        }

        .signal-card {
            min-height: 126px;
            border-radius: 8px;
            border: 1px solid rgba(148, 163, 184, 0.17);
            background: rgba(12, 18, 32, 0.72);
            padding: 0.95rem;
            margin-bottom: 0.85rem;
        }

        .signal-card h4 {
            margin: 0 0 0.38rem;
            color: #F8FAFC;
            font-size: 0.98rem;
        }

        .signal-card p {
            margin: 0;
            color: #94A3B8;
            font-size: 0.86rem;
            line-height: 1.42;
        }

        .score-ring {
            border-radius: 8px;
            border: 1px solid rgba(96, 165, 250, 0.22);
            background: rgba(96, 165, 250, 0.09);
            padding: 1rem;
            text-align: center;
        }

        .score-ring .score {
            color: #F8FAFC;
            font-size: 3.1rem;
            line-height: 1;
            font-weight: 800;
        }

        .score-ring .score-label {
            color: #94A3B8;
            font-weight: 700;
            margin-top: 0.25rem;
        }

        div[data-testid="stTabs"] button {
            color: #CBD5E1;
            font-weight: 700;
        }

        div[data-testid="stTabs"] [aria-selected="true"] {
            color: #F8FAFC;
        }

        .stButton > button {
            border-radius: 8px;
            border: 1px solid rgba(96, 165, 250, 0.35);
            background: linear-gradient(135deg, #2563EB, #0F766E);
            color: #FFFFFF;
            font-weight: 800;
        }

        @media (max-width: 760px) {
            .hero {
                align-items: flex-start;
                flex-direction: column;
            }

            .hero-price {
                text-align: left;
                min-width: 0;
                width: 100%;
            }

            .metric-card {
                min-height: 104px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def change_tone(value: Any) -> str:
    number = value_to_float(value)
    if number is None:
        return "neutral"
    if number > 0:
        return "positive"
    if number < 0:
        return "negative"
    return "neutral"


def render_hero(snapshot: dict[str, Any]) -> None:
    currency = snapshot["currency"]
    change = snapshot.get("day_change_percent")
    tone = change_tone(change)
    change_text = format_percentage(change, from_decimal=False)
    st.markdown(
        f"""
        <section class="hero">
            <div>
                <span class="eyebrow">AI Equity Terminal</span>
                <h1>{snapshot["company_name"]}</h1>
                <div class="hero-subtitle">
                    {snapshot["display_ticker"]} | {snapshot.get("sector", "N/A")} | {snapshot.get("industry", "N/A")}
                </div>
            </div>
            <div class="hero-price">
                <span class="price">{format_currency(snapshot.get("current_price"), currency=currency)}</span>
                <span class="change-pill {tone}">{change_text}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_market_cards(snapshot: dict[str, Any]) -> None:
    currency = snapshot["currency"]
    cards = [
        {
            "label": "Live Price",
            "value": format_currency(snapshot.get("current_price"), currency=currency),
            "delta": format_percentage(snapshot.get("day_change_percent"), from_decimal=False),
            "tone": change_tone(snapshot.get("day_change_percent")),
        },
        {"label": "Market Cap", "value": format_currency(snapshot.get("market_cap"), currency=currency, compact=True)},
        {"label": "Open", "value": format_currency(snapshot.get("open"), currency=currency)},
        {"label": "Previous Close", "value": format_currency(snapshot.get("previous_close"), currency=currency)},
        {"label": "Day High", "value": format_currency(snapshot.get("day_high"), currency=currency)},
        {"label": "Day Low", "value": format_currency(snapshot.get("day_low"), currency=currency)},
        {"label": "Volume", "value": format_number(snapshot.get("volume"), decimals=0, compact=True)},
        {"label": "Average Volume", "value": format_number(snapshot.get("average_volume"), decimals=0, compact=True)},
        {"label": "52 Week High", "value": format_currency(snapshot.get("fifty_two_week_high"), currency=currency)},
        {"label": "52 Week Low", "value": format_currency(snapshot.get("fifty_two_week_low"), currency=currency)},
        {"label": "Beta", "value": format_number(snapshot.get("beta"))},
        {"label": "Float Shares", "value": format_number(snapshot.get("float_shares"), decimals=0, compact=True)},
    ]
    render_metric_grid(cards, columns=4)


def render_fundamental_section(section: dict[str, Any], currency: str) -> None:
    st.markdown(f"<div class='section-title'>{section['title']}</div>", unsafe_allow_html=True)
    cards = [
        {
            "label": metric["label"],
            "value": format_metric_value(metric.get("value"), metric.get("kind", "number"), currency=currency),
        }
        for metric in section["metrics"]
    ]
    render_metric_grid(cards, columns=4)


def render_company_panel(company_info: dict[str, Any]) -> None:
    st.markdown("<div class='section-title'>Company Profile</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="glass-panel">
            <p><strong>{company_info.get("company_name", "N/A")}</strong></p>
            <p>{company_info.get("business_summary", "No company summary is available.")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_signal_cards(signals: dict[str, dict[str, str]]) -> None:
    if not signals:
        st.info("Technical signals are unavailable for this range.")
        return

    columns = st.columns(4)
    for index, signal in enumerate(signals.values()):
        with columns[index % 4]:
            st.markdown(
                f"""
                <div class="signal-card">
                    <h4 class="{signal.get("tone", "neutral")}">{signal.get("label", "Signal")}</h4>
                    <p>{signal.get("detail", "")}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_technical_metrics(latest: dict[str, Any], support_resistance: dict[str, Any], currency: str) -> None:
    cards = [
        {"label": "RSI", "value": format_number(latest.get("RSI"))},
        {"label": "MACD", "value": format_number(latest.get("MACD"))},
        {"label": "MACD Signal", "value": format_number(latest.get("MACD_SIGNAL"))},
        {"label": "MACD Hist", "value": format_number(latest.get("MACD_HIST"))},
        {"label": "EMA20", "value": format_currency(latest.get("EMA20"), currency=currency)},
        {"label": "EMA50", "value": format_currency(latest.get("EMA50"), currency=currency)},
        {"label": "EMA200", "value": format_currency(latest.get("EMA200"), currency=currency)},
        {"label": "SMA50", "value": format_currency(latest.get("SMA50"), currency=currency)},
        {"label": "SMA200", "value": format_currency(latest.get("SMA200"), currency=currency)},
        {"label": "ATR", "value": format_currency(latest.get("ATR"), currency=currency)},
        {"label": "VWAP", "value": format_currency(latest.get("VWAP"), currency=currency)},
        {"label": "Support", "value": format_currency(support_resistance.get("support"), currency=currency)},
        {"label": "Resistance", "value": format_currency(support_resistance.get("resistance"), currency=currency)},
    ]
    render_metric_grid(cards, columns=4)


def value_to_markdown(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value) if value else "N/A"
    if isinstance(value, dict):
        return "\n".join(f"- **{key.replace('_', ' ').title()}**: {item}" for key, item in value.items())
    return str(value)


def render_ai_result(result: dict[str, Any]) -> None:
    status = result.get("status")
    if status == "missing_key":
        st.warning(result.get("message"))
        return
    if status == "error":
        st.error(result.get("message", "AI analysis failed."))
        return

    score = result.get("investment_score")
    sections = result.get("sections", {})

    if score is not None:
        left, right = st.columns([1, 4])
        with left:
            st.markdown(
                f"""
                <div class="score-ring">
                    <div class="score">{score}</div>
                    <div class="score-label">Score / 100</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with right:
            summary = sections.get("executive_summary") or "AI summary is unavailable."
            st.markdown(f"<div class='glass-panel'><p>{summary}</p></div>", unsafe_allow_html=True)

    if not sections:
        st.markdown(result.get("raw_response", "AI analysis returned no text."))
        return

    for key, label in AI_SECTION_LABELS.items():
        if key in {"executive_summary", "investment_score"}:
            continue
        st.markdown(f"<div class='section-title'>{label}</div>", unsafe_allow_html=True)
        st.markdown(value_to_markdown(sections.get(key)))


def initialize_state() -> None:
    defaults = {
        "active_ticker": DEFAULT_TICKER,
        "period_label": DEFAULT_PERIOD_LABEL,
        "interval_label": DEFAULT_INTERVAL_LABEL,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_sidebar() -> tuple[str, str, str]:
    symbols = SUPPORTED_US_TICKERS + SUPPORTED_INDIAN_TICKERS

    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <h2>AI Stock Screener</h2>
                <span>Premium equity research workspace</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("ticker_form"):
            custom_ticker = st.text_input("Search", placeholder="AAPL, NVDA, RELIANCE")
            quick_pick = st.selectbox("Watchlist", symbols, index=0)
            period_label = st.selectbox(
                "Range",
                list(PERIOD_OPTIONS.keys()),
                index=list(PERIOD_OPTIONS.keys()).index(st.session_state["period_label"]),
            )
            interval_label = st.selectbox(
                "Interval",
                list(INTERVAL_OPTIONS.keys()),
                index=list(INTERVAL_OPTIONS.keys()).index(st.session_state["interval_label"]),
            )
            submitted = st.form_submit_button("Analyze", use_container_width=True)

        if submitted:
            st.session_state["active_ticker"] = custom_ticker.strip() or quick_pick
            st.session_state["period_label"] = period_label
            st.session_state["interval_label"] = interval_label

        st.markdown("---")
        st.markdown("**Navigation**")
        st.markdown("Overview<br>Fundamentals<br>Technicals<br>AI Analysis", unsafe_allow_html=True)

    return (
        st.session_state["active_ticker"],
        PERIOD_OPTIONS[st.session_state["period_label"]],
        INTERVAL_OPTIONS[st.session_state["interval_label"]],
    )


def main() -> None:
    inject_css()
    initialize_state()
    ticker_query, period, interval = render_sidebar()
    ticker = normalize_ticker(ticker_query)

    try:
        with st.spinner("Loading market data..."):
            profile = get_market_profile(ticker, period=period, interval=interval)
    except MarketDataError as exc:
        st.error(f"We could not load {display_ticker(ticker)}. {exc}")
        st.stop()
    except Exception:
        st.error("Something went wrong while loading this ticker. Please try another symbol.")
        st.stop()

    technical_dataframe = calculate_technical_indicators(profile["history"])
    technical_summary = build_technical_summary(technical_dataframe)
    snapshot = profile["snapshot"]
    currency = snapshot["currency"]

    render_hero(snapshot)
    render_market_cards(snapshot)

    overview_tab, fundamentals_tab, technicals_tab, ai_tab = st.tabs(
        ["Overview", "Fundamentals", "Technicals", "AI Analysis"]
    )

    with overview_tab:
        left, right = st.columns([2.2, 1])
        with left:
            st.plotly_chart(
                create_candlestick_chart(technical_dataframe, snapshot["display_ticker"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        with right:
            render_company_panel(profile["fundamentals"]["company_info"])
            sr = technical_summary["support_resistance"]
            render_metric_card("Support", format_currency(sr.get("support"), currency=currency))
            render_metric_card("Resistance", format_currency(sr.get("resistance"), currency=currency))
            render_metric_card("Shares Outstanding", format_number(snapshot.get("shares_outstanding"), decimals=0, compact=True))

    with fundamentals_tab:
        for key in ["valuation", "profitability", "growth", "financial_health"]:
            render_fundamental_section(profile["fundamentals"][key], currency=currency)

    with technicals_tab:
        st.markdown("<div class='section-title'>Signals</div>", unsafe_allow_html=True)
        render_signal_cards(technical_summary["signals"])
        st.markdown("<div class='section-title'>Indicator Snapshot</div>", unsafe_allow_html=True)
        render_technical_metrics(
            technical_summary["latest"],
            technical_summary["support_resistance"],
            currency=currency,
        )
        rsi_col, macd_col = st.columns(2)
        with rsi_col:
            st.plotly_chart(create_rsi_chart(technical_dataframe), use_container_width=True, config={"displayModeBar": False})
        with macd_col:
            st.plotly_chart(create_macd_chart(technical_dataframe), use_container_width=True, config={"displayModeBar": False})

    with ai_tab:
        payload = build_ai_payload(profile, technical_summary)
        serialized_payload = serialize_ai_payload(payload)

        if st.button("Run AI Analysis", type="primary", use_container_width=True):
            with st.spinner("Analyzing stock with AI..."):
                st.session_state[f"ai_result_{profile['ticker']}"] = analyze_stock_with_ai(serialized_payload)

        cached_result = st.session_state.get(f"ai_result_{profile['ticker']}")
        if cached_result:
            render_ai_result(cached_result)
        else:
            st.markdown(
                """
                <div class="glass-panel">
                    <p>Run the AI analysis to generate a structured analyst memo for this ticker.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()

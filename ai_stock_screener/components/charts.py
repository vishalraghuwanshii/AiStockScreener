from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


PLOT_BG = "rgba(0,0,0,0)"
GRID_COLOR = "rgba(148, 163, 184, 0.16)"
TEXT_COLOR = "#E5E7EB"
MUTED_COLOR = "#94A3B8"
UP_COLOR = "#2DD4BF"
DOWN_COLOR = "#FB7185"


def _base_layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor=PLOT_BG,
        plot_bgcolor=PLOT_BG,
        font={"color": TEXT_COLOR, "family": "Inter, system-ui, sans-serif"},
        margin={"l": 18, "r": 18, "t": 44, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"color": MUTED_COLOR},
        },
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)
    return fig


def create_candlestick_chart(dataframe: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.74, 0.26],
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]],
    )

    fig.add_trace(
        go.Candlestick(
            x=dataframe.index,
            open=dataframe["Open"],
            high=dataframe["High"],
            low=dataframe["Low"],
            close=dataframe["Close"],
            name=ticker,
            increasing_line_color=UP_COLOR,
            decreasing_line_color=DOWN_COLOR,
            increasing_fillcolor=UP_COLOR,
            decreasing_fillcolor=DOWN_COLOR,
        ),
        row=1,
        col=1,
    )

    moving_averages = [
        ("EMA20", "#60A5FA", "EMA 20", 1.6),
        ("EMA50", "#FBBF24", "EMA 50", 1.6),
        ("EMA200", "#A78BFA", "EMA 200", 1.8),
    ]
    for column, color, name, width in moving_averages:
        if column in dataframe and dataframe[column].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=dataframe.index,
                    y=dataframe[column],
                    mode="lines",
                    name=name,
                    line={"color": color, "width": width},
                ),
                row=1,
                col=1,
            )

    volume_colors = [
        UP_COLOR if close >= open_price else DOWN_COLOR
        for close, open_price in zip(dataframe["Close"], dataframe["Open"], strict=False)
    ]
    fig.add_trace(
        go.Bar(
            x=dataframe.index,
            y=dataframe["Volume"],
            name="Volume",
            marker={"color": volume_colors, "opacity": 0.55},
        ),
        row=2,
        col=1,
    )

    _base_layout(fig, height=640)
    fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    return fig


def create_rsi_chart(dataframe: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dataframe.index,
            y=dataframe["RSI"],
            mode="lines",
            name="RSI",
            line={"color": "#60A5FA", "width": 2},
        )
    )
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(251, 113, 133, 0.12)", line_width=0)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(45, 212, 191, 0.12)", line_width=0)
    fig.add_hline(y=70, line_dash="dot", line_color="#FB7185")
    fig.add_hline(y=30, line_dash="dot", line_color="#2DD4BF")
    _base_layout(fig, height=330)
    fig.update_layout(title="RSI")
    fig.update_yaxes(range=[0, 100])
    return fig


def create_macd_chart(dataframe: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    histogram = dataframe["MACD_HIST"].fillna(0)
    colors = [UP_COLOR if value >= 0 else DOWN_COLOR for value in histogram]

    fig.add_trace(
        go.Bar(
            x=dataframe.index,
            y=histogram,
            name="Histogram",
            marker={"color": colors, "opacity": 0.58},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dataframe.index,
            y=dataframe["MACD"],
            mode="lines",
            name="MACD",
            line={"color": "#60A5FA", "width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=dataframe.index,
            y=dataframe["MACD_SIGNAL"],
            mode="lines",
            name="Signal",
            line={"color": "#FBBF24", "width": 2},
        )
    )

    _base_layout(fig, height=330)
    fig.update_layout(title="MACD")
    return fig

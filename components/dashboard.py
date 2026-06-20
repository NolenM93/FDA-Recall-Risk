import pandas as pd
import plotly.express as px
import streamlit as st

from components.risk_scoring import RISK_COLORS, compute_risk_scores
from utils.api import fetch_recalls_dataframe
from utils.data_processing import (
    add_category_column,
    aggregate_by_category,
    aggregate_by_month,
    clean_dataframe,
)

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
    margin=dict(l=0, r=0, t=40, b=0),
)


def _risk_card(category: str, level: str, count: int) -> str:
    """Return an HTML string for a single risk score card."""
    color = RISK_COLORS.get(level, "#6b7280")
    return (
        f'<div style="padding:14px;border-radius:8px;border-left:4px solid {color};'
        f'background:#1e293b;margin-bottom:10px;">'
        f'<div style="font-size:0.8rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">{category}</div>'
        f'<div style="font-size:1.5rem;font-weight:700;color:{color};">{level}</div>'
        f'<div style="font-size:0.8rem;color:#64748b;">{count} recalls</div>'
        f"</div>"
    )


def render_dashboard_page() -> None:
    st.title("Risk Scoring Dashboard")

    with st.spinner("Loading recall data for risk analysis…"):
        try:
            df = fetch_recalls_dataframe(limit=5000)
            df = clean_dataframe(df)
            df = add_category_column(df)
        except Exception as exc:
            st.error(f"Failed to load data: {exc}")
            return

    if df.empty:
        st.warning("No data returned from the API.")
        return

    # ------------------------------------------------------------------ #
    # Risk score cards                                                     #
    # ------------------------------------------------------------------ #
    st.subheader("Category Risk Scores")
    risk_df = compute_risk_scores(df)

    if not risk_df.empty:
        cols = st.columns(4)
        for i, (_, row) in enumerate(risk_df.iterrows()):
            cols[i % 4].markdown(
                _risk_card(row["category"], row["risk_level"], row["recall_count"]),
                unsafe_allow_html=True,
            )

    st.divider()

    # ------------------------------------------------------------------ #
    # Trend line + category bar                                            #
    # ------------------------------------------------------------------ #
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Monthly Recall Volume")
        trend_df = aggregate_by_month(df)
        if not trend_df.empty:
            fig = px.line(
                trend_df,
                x="month",
                y="recall_count",
                labels={"month": "Month", "recall_count": "Recalls"},
            )
            fig.update_traces(line_color="#f97316", line_width=2.5)
            fig.update_layout(**_CHART_LAYOUT)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No date data available for trend chart.")

    with col_right:
        st.subheader("Recalls by Category")
        cat_df = aggregate_by_category(df)
        if not cat_df.empty:
            fig = px.bar(
                cat_df,
                x="recall_count",
                y="category",
                orientation="h",
                labels={"recall_count": "Recall Count", "category": ""},
                color="recall_count",
                color_continuous_scale="Oranges",
            )
            fig.update_layout(**_CHART_LAYOUT, showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ------------------------------------------------------------------ #
    # Category comparison                                                  #
    # ------------------------------------------------------------------ #
    st.subheader("Category Comparison")
    all_categories = sorted(df["category"].unique().tolist()) if "category" in df.columns else []

    if len(all_categories) >= 2:
        ca, cb = st.columns(2)
        with ca:
            cat_a = st.selectbox("Category A", all_categories, index=0)
        with cb:
            cat_b = st.selectbox("Category B", all_categories, index=1)

        if cat_a != cat_b:
            comp_df = (
                df[df["category"].isin([cat_a, cat_b])]
                .groupby("category")
                .size()
                .reset_index(name="recall_count")
            )
            fig = px.bar(
                comp_df,
                x="category",
                y="recall_count",
                color="category",
                color_discrete_map={cat_a: "#f97316", cat_b: "#3b82f6"},
                labels={"category": "", "recall_count": "Recall Count"},
                title=f"{cat_a}  vs  {cat_b}",
            )
            fig.update_layout(**_CHART_LAYOUT, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Select two different categories to compare.")
    else:
        st.info("Not enough category data to render comparison.")



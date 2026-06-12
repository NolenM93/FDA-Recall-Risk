import pandas as pd
import plotly.express as px
import streamlit as st

from utils.api import fetch_recalls_dataframe
from utils.data_processing import build_state_counts, clean_dataframe

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    geo_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
    margin=dict(l=0, r=0, t=50, b=0),
)


def render_map_page() -> None:
    st.title("Geographic Trend Heatmap")
    st.caption(
        "Recall frequency by U.S. state, derived from product distribution patterns "
        "reported to the openFDA Enforcement database."
    )

    # ------------------------------------------------------------------ #
    # Controls                                                             #
    # ------------------------------------------------------------------ #
    recall_limit = st.selectbox(
        "Records to fetch",
        [200, 500, 1000, 5000, 10000, "All"],
        index=3,
        help="Higher counts improve state coverage on the heatmap. "
        "'All' paginates through the full openFDA dataset (~29k records).",
    )
    fetch_all = recall_limit == "All"

    # ------------------------------------------------------------------ #
    # Data                                                                 #
    # ------------------------------------------------------------------ #
    try:
        df = fetch_recalls_dataframe(
            limit=recall_limit if not fetch_all else 1000,
            fetch_all=fetch_all,
        )
        df = clean_dataframe(df)
    except Exception as exc:
        st.error(f"Failed to load map data: {exc}")
        return

    if df.empty:
        st.warning("No data available for the map.")
        return

    # ------------------------------------------------------------------ #
    # Build state-level counts                                             #
    # ------------------------------------------------------------------ #
    state_series = build_state_counts(df)

    if state_series.empty or state_series.sum() == 0:
        st.warning(
            "Distribution pattern data is missing or unstructured for the selected records. "
            "Try increasing the record count."
        )
        return

    state_df = state_series.reset_index()
    state_df.columns = ["state", "recall_count"]

    states_with_data = int((state_series > 0).sum())
    st.caption(
        f"{len(df):,} recalls loaded · {states_with_data} states/territories with data"
    )

    # ------------------------------------------------------------------ #
    # Choropleth map                                                       #
    # ------------------------------------------------------------------ #
    fig = px.choropleth(
        state_df,
        locations="state",
        locationmode="USA-states",
        color="recall_count",
        scope="usa",
        color_continuous_scale="Oranges",
        title="Recall Frequency by State",
        labels={"recall_count": "Recall Count"},
        hover_name="state",
        hover_data={"recall_count": True, "state": False},
    )
    fig.update_layout(**_CHART_LAYOUT, title_font_size=16)
    st.plotly_chart(fig, use_container_width=True)

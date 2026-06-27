import pandas as pd
import plotly.express as px
import streamlit as st

from components.state_detail import show_state_detail
from utils.api import fetch_recalls_dataframe
from utils.data_processing import (
    ALL_STATES,
    add_category_column,
    build_state_counts,
    clean_dataframe,
)

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    geo_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
    margin=dict(l=0, r=0, t=50, b=0),
)


def _load_map_data(recall_limit: int) -> pd.DataFrame:
    """Fetch and cache map data, reusing session state when the limit is unchanged."""
    cached_limit = st.session_state.get("map_recall_limit")
    cached_df = st.session_state.get("map_df")

    if cached_df is not None and cached_limit == recall_limit:
        return cached_df

    df = fetch_recalls_dataframe(limit=recall_limit, fetch_all=False)
    df = clean_dataframe(df)
    df = add_category_column(df)
    st.session_state["map_df"] = df
    st.session_state["map_recall_limit"] = recall_limit

    # Invalidate per-state dialog caches when the underlying map dataset changes.
    for key in list(st.session_state.keys()):
        if key.startswith("state_detail_df_") or key.startswith("state_detail_source_"):
            del st.session_state[key]

    return df


def render_map_page() -> None:
    st.title("Geographic Trend Heatmap")
    st.caption(
        "Recall frequency by U.S. state, derived from product distribution patterns "
        "reported to the openFDA Enforcement database. Click a state to inspect recalls."
    )

    # ------------------------------------------------------------------ #
    # Controls                                                             #
    # ------------------------------------------------------------------ #
    recall_limit = st.selectbox(
        "Records to fetch",
        [200, 500, 1000, 5000, 10000, 25000],
        index=1,
        help="Higher counts improve state coverage on the heatmap. "
        "Maximum is 25,000. This is the openFDA API hard limit.",
    )

    # ------------------------------------------------------------------ #
    # Data                                                                 #
    # ------------------------------------------------------------------ #
    try:
        df = _load_map_data(recall_limit)
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

    event = st.plotly_chart(
        fig,
        on_select="rerun",
        selection_mode="points",
        width="stretch",
    )

    if event.selection and event.selection.points:
        clicked_state = event.selection.points[0].get("location")
        if clicked_state:
            st.session_state["selected_state"] = clicked_state

    # ------------------------------------------------------------------ #
    # State selector + dialog                                              #
    # ------------------------------------------------------------------ #
    st.divider()
    dropdown_state = st.selectbox(
        "Or select a state to inspect",
        [""] + ALL_STATES,
        index=0,
        format_func=lambda code: "Choose a state…" if code == "" else code,
    )
    if dropdown_state:
        st.session_state["selected_state"] = dropdown_state

    selected_state = st.session_state.get("selected_state")
    if selected_state:
        show_state_detail(selected_state, st.session_state.get("map_df", pd.DataFrame()))

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.api import fetch_recalls_dataframe
from utils.classification_help import CLASS_COLUMN_HELP, help_for_classification
from utils.data_processing import (
    add_category_column,
    clean_dataframe,
    filter_recalls_by_state,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_NAMES: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

_DISPLAY_COLS = [
    "recall_initiation_date",
    "recalling_firm",
    "product_description",
    "classification",
    "reason_for_recall",
    "status",
    "category",
]

_COL_LABELS = {
    "recall_initiation_date": "Date",
    "recalling_firm":         "Company",
    "product_description":    "Product",
    "classification":         "Class",
    "reason_for_recall":      "Reason",
    "status":                 "Status",
    "category":               "Category",
}

_TIMELINE_STEPS = [
    ("recall_initiation_date", "Initiated"),
    ("report_date", "Reported"),
    ("center_classification_date", "Classified"),
    ("termination_date", "Recall closed"),
]

_CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e2e8f0",
    margin=dict(l=0, r=0, t=30, b=0),
    height=180,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _class_mask(series: pd.Series, class_label: str) -> pd.Series:
    """Return boolean mask for a specific FDA classification level."""
    upper = series.str.upper()
    if class_label == "Class I":
        return (
            upper.str.contains("CLASS I", na=False)
            & ~upper.str.contains("CLASS II", na=False)
            & ~upper.str.contains("CLASS III", na=False)
        )
    return upper.str.contains(class_label.upper(), na=False)


def _apply_dialog_filters(
    df: pd.DataFrame,
    company_product: str,
    classifications: list[str],
    distribution_notes: str,
    status_filter: str,
    date_range: tuple,
) -> pd.DataFrame:
    """Apply user-selected filters inside the state detail dialog."""
    filtered = df.copy()

    if company_product:
        term = company_product.lower()
        firm = filtered.get("recalling_firm", pd.Series(dtype=str)).astype(str).str.lower()
        product = filtered.get("product_description", pd.Series(dtype=str)).astype(str).str.lower()
        filtered = filtered[firm.str.contains(term, na=False) | product.str.contains(term, na=False)]

    if classifications and "classification" in filtered.columns:
        class_mask = pd.Series(False, index=filtered.index)
        for label in classifications:
            class_mask |= _class_mask(filtered["classification"], label)
        filtered = filtered[class_mask]

    if distribution_notes and "distribution_pattern" in filtered.columns:
        notes = distribution_notes.lower()
        patterns = filtered["distribution_pattern"].astype(str).str.lower()
        filtered = filtered[patterns.str.contains(notes, na=False)]

    if status_filter != "All" and "status" in filtered.columns:
        status = filtered["status"].astype(str).str.lower()
        if status_filter == "Ongoing":
            filtered = filtered[~status.str.contains("terminat", na=False)]
        elif status_filter == "Terminated":
            filtered = filtered[status.str.contains("terminat", na=False)]

    if (
        len(date_range) == 2
        and "recall_initiation_date" in filtered.columns
    ):
        start = pd.Timestamp(date_range[0])
        end = pd.Timestamp(date_range[1])
        filtered = filtered[
            (filtered["recall_initiation_date"] >= start)
            & (filtered["recall_initiation_date"] <= end)
        ]

    return filtered


def _build_timeline_chart(row: pd.Series) -> go.Figure:
    """Build a horizontal milestone chart for a single recall."""
    dates: list[pd.Timestamp] = []
    labels: list[str] = []
    colors: list[str] = []

    for field, label in _TIMELINE_STEPS:
        value = row.get(field, pd.NaT)
        if pd.notna(value):
            dates.append(pd.Timestamp(value))
            labels.append(label)
            colors.append("#f97316")
        elif field == "termination_date":
            dates.append(pd.Timestamp.today())
            labels.append(f"{label} (pending)")
            colors.append("#64748b")

    fig = go.Figure()
    if not dates:
        fig.add_annotation(
            text="No timeline dates available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color="#e2e8f0"),
        )
        fig.update_layout(**_CHART_LAYOUT)
        return fig

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=[0] * len(dates),
            mode="markers+text",
            marker=dict(size=14, color=colors, symbol="circle"),
            text=labels,
            textposition="top center",
            hovertemplate="%{text}<br>%{x|%Y-%m-%d}<extra></extra>",
        )
    )
    fig.update_layout(
        **_CHART_LAYOUT,
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(visible=False, range=[-1, 1]),
        showlegend=False,
        title="Regulatory Timeline",
        title_font_size=14,
    )
    return fig


def _state_api_query(state_code: str) -> str:
    """Build an openFDA query for recalls mentioning a state in distribution."""
    state_name = STATE_NAMES.get(state_code, state_code)
    return (
        f'distribution_pattern:"{state_code}" OR '
        f'distribution_pattern:"{state_name}"'
    )


def reset_state_detail_from_map(state_code: str, map_df: pd.DataFrame) -> None:
    """Reset a state's dialog data to the current map dataset."""
    st.session_state[f"state_detail_df_{state_code}"] = filter_recalls_by_state(
        map_df, state_code
    )
    st.session_state[f"state_detail_source_{state_code}"] = "loaded_dataset"


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

@st.dialog("State Recall Detail", width="large")
def show_state_detail(state_code: str, df: pd.DataFrame) -> None:
    """Modal drill-down for recalls distributed to a selected state."""
    state_name = STATE_NAMES.get(state_code, state_code)
    cache_key = f"state_detail_df_{state_code}"
    source_key = f"state_detail_source_{state_code}"

    if cache_key not in st.session_state:
        st.session_state[cache_key] = filter_recalls_by_state(df, state_code)
        st.session_state[source_key] = "loaded_dataset"

    state_df: pd.DataFrame = st.session_state[cache_key]
    data_source = st.session_state.get(source_key, "loaded_dataset")

    st.subheader(f"{state_name} ({state_code})")
    if data_source == "api_fetch":
        st.caption(
            f"Showing {len(state_df):,} recalls that explicitly name {state_code} "
            f"in their distribution notes, fetched directly from openFDA. "
            f"Note: nationwide recalls are not included in this view."
        )
    else:
        st.caption(
            f"Showing {len(state_df):,} recalls distributed to {state_code} "
            f"from the map dataset ({len(df):,} records loaded). "
            f"This includes nationwide recalls. Raise the map record count for better coverage."
        )

    if state_df.empty:
        st.info(
            f"No recalls in the current dataset include {state_code} in their distribution notes. "
            "Try increasing the record count on the map or use the button below."
        )

    if st.button(
        f"Search openFDA for recalls that name {state_code} in distribution notes",
        type="secondary",
        help=f"Queries openFDA directly for records where the distribution field explicitly mentions "
             f"{state_code} or {STATE_NAMES.get(state_code, state_code)}. "
             f"Returns up to 1,000 matches. Nationwide recalls are excluded from this result.",
    ):
        with st.spinner(f"Fetching recalls for {state_name}…"):
            try:
                fetched = fetch_recalls_dataframe(
                    search_query=_state_api_query(state_code),
                    limit=1000,
                )
                fetched = clean_dataframe(fetched)
                fetched = add_category_column(fetched)
                st.session_state[cache_key] = filter_recalls_by_state(fetched, state_code)
                st.session_state[source_key] = "api_fetch"
                st.rerun()
            except Exception as exc:
                st.error(f"API request failed: {exc}")

    st.divider()

    # --- Filters ---
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        company_product = st.text_input(
            "Search company / product",
            key=f"state_company_{state_code}",
            placeholder="e.g., dairy, Kroger",
        )
    with f2:
        classifications = st.multiselect(
            "Severity",
            ["Class I", "Class II", "Class III"],
            default=[],
            key=f"state_class_{state_code}",
        )
    with f3:
        distribution_notes = st.text_input(
            "Search distribution notes",
            key=f"state_dist_{state_code}",
            placeholder="e.g., Walmart, nationwide",
            help="Searches free-text FDA distribution notes. Not a store locator.",
        )
    with f4:
        status_filter = st.selectbox(
            "Status",
            ["All", "Ongoing", "Terminated"],
            key=f"state_status_{state_code}",
        )

    date_range = st.date_input(
        "Recall initiation date range (optional)",
        value=[],
        key=f"state_dates_{state_code}",
    )

    filtered = _apply_dialog_filters(
        state_df,
        company_product,
        classifications,
        distribution_notes,
        status_filter,
        date_range,
    )

    # --- Summary metrics ---
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    with m1:
        st.metric("Total", len(filtered))
    with m2:
        count = int(_class_mask(filtered["classification"], "Class I").sum()) if not filtered.empty else 0
        st.metric("Class I", count)
    with m3:
        count = int(_class_mask(filtered["classification"], "Class II").sum()) if not filtered.empty else 0
        st.metric("Class II", count)
    with m4:
        count = int(_class_mask(filtered["classification"], "Class III").sum()) if not filtered.empty else 0
        st.metric("Class III", count)
    with m5:
        if not filtered.empty and "status" in filtered.columns:
            ongoing = ~filtered["status"].astype(str).str.lower().str.contains("terminat", na=False)
            st.metric("Ongoing", int(ongoing.sum()))
        else:
            st.metric("Ongoing", 0)
    with m6:
        if not filtered.empty and "status" in filtered.columns:
            terminated = filtered["status"].astype(str).str.lower().str.contains("terminat", na=False)
            st.metric("Terminated", int(terminated.sum()))
        else:
            st.metric("Terminated", 0)

    if filtered.empty:
        st.info("No recalls match the current filters for this state.")
        return

    # --- Results table ---
    st.markdown(f"**Results — {len(filtered)} records**")
    display_cols = [c for c in _DISPLAY_COLS if c in filtered.columns]
    display_df = filtered[display_cols].copy()

    if "recall_initiation_date" in display_df.columns:
        display_df["recall_initiation_date"] = (
            display_df["recall_initiation_date"].dt.strftime("%Y-%m-%d").fillna("Unknown")
        )

    display_df = display_df.rename(columns=_COL_LABELS)

    event = st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"state_table_{state_code}",
        column_config={
            "Class": st.column_config.TextColumn("Class", help=CLASS_COLUMN_HELP),
        },
    )

    # --- Drill-down detail ---
    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        row = filtered.iloc[selected_rows[0]]
        st.markdown("**Recall Detail**")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Recall #:** {row.get('recall_number', 'N/A')}")
                st.write(f"**Company:** {row.get('recalling_firm', 'N/A')}")
                classification = row.get("classification", "N/A")
                class_help = help_for_classification(str(classification))
                if class_help:
                    st.markdown(
                        f'**Classification:** '
                        f'<span title="{html.escape(class_help)}">'
                        f'{html.escape(str(classification))}</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.write(f"**Classification:** {classification}")
                st.write(f"**Status:** {row.get('status', 'N/A')}")
            with c2:
                for field, label in [
                    ("recall_initiation_date", "Date Initiated"),
                    ("report_date", "Date Reported"),
                    ("center_classification_date", "Date Classified"),
                    ("termination_date", "Recall Closed"),
                ]:
                    value = row.get(field, pd.NaT)
                    date_str = value.strftime("%Y-%m-%d") if pd.notna(value) else "N/A"
                    st.write(f"**{label}:** {date_str}")
                st.write(f"**Product Type:** {row.get('product_type', 'N/A')}")
                st.write(f"**Quantity:** {row.get('product_quantity', 'N/A')}")
                st.write(f"**Category:** {row.get('category', 'N/A')}")

            st.write(f"**Product Description:** {row.get('product_description', 'N/A')}")
            st.write(f"**Reason for Recall:** {row.get('reason_for_recall', 'N/A')}")
            st.markdown("**Distribution Notes**")
            st.write(row.get("distribution_pattern", "N/A"))
            st.caption(
                "Recall closed date reflects FDA termination status, not confirmed "
                "shelf removal at individual stores."
            )
            st.plotly_chart(
                _build_timeline_chart(row),
                width="stretch",
                key=f"state_timeline_{state_code}_{selected_rows[0]}",
            )

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download {state_code} recalls as CSV",
        data=csv_bytes,
        file_name=f"fda_recalls_{state_code}.csv",
        mime="text/csv",
        key=f"state_csv_{state_code}",
    )

import html

import pandas as pd
import streamlit as st

from utils.api import fetch_recalls_dataframe
from utils.classification_help import (
    CLASS_COLUMN_HELP,
    CLASS_I_HELP,
    CLASSIFICATION_FILTER_HELP,
    help_for_classification,
)
from utils.data_processing import add_category_column, clean_dataframe

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DISPLAY_COLS = [
    "recall_initiation_date",
    "recalling_firm",
    "product_description",
    "classification",
    "reason_for_recall",
    "category",
]

_COL_LABELS = {
    "recall_initiation_date": "Date",
    "recalling_firm":         "Company",
    "product_description":    "Product",
    "classification":         "Class",
    "reason_for_recall":      "Reason",
    "category":               "Category",
}


def _build_query(search_term: str, classifications: list, product_types: list) -> str | None:
    """
    Construct an openFDA search query from user inputs.
    Returns None when no filters are active (triggers a default browse).
    """
    parts = []

    if search_term:
        parts.append(search_term)

    if classifications:
        class_terms = " ".join(f'classification:"{c}"' for c in classifications)
        parts.append(f"({class_terms})")

    if product_types:
        type_terms = " ".join(f'product_type:"{t}"' for t in product_types)
        parts.append(f"({type_terms})")

    return " AND ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

def render_search_page() -> None:
    st.title("Recall Search & Results")

    # --- Input row ---
    col1, col2 = st.columns([4, 1])
    with col1:
        search_term = st.text_input(
            "Search by product name, company, or recall reason",
            placeholder="e.g., peanut butter, Listeria, dairy farms",
        )
    with col2:
        result_limit = st.selectbox("Limit", [50, 100, 200, 500], index=1)

    # --- Filters ---
    with st.expander("Filters", expanded=True):
        fa, fb = st.columns(2)
        with fa:
            classification_filter = st.multiselect(
                "Recall Classification",
                ["Class I", "Class II", "Class III"],
                default=[],
                help=CLASSIFICATION_FILTER_HELP,
            )
        with fb:
            product_type_filter = st.multiselect(
                "Product Type",
                ["Food", "Dietary Supplement", "Cosmetics"],
                default=["Food"],
            )

        date_range = st.date_input(
            "Recall Initiation Date Range (optional)",
            value=[],
            help="Leave empty to show all dates.",
        )

    # --- Fetch ---
    search_clicked = st.button("Search", type="primary")

    if search_clicked or "recall_df" not in st.session_state:
        query = _build_query(search_term, classification_filter, product_type_filter)
        with st.spinner("Fetching recall data from openFDA…"):
            try:
                df = fetch_recalls_dataframe(search_query=query, limit=result_limit)
                df = clean_dataframe(df)
                df = add_category_column(df)
                st.session_state["recall_df"] = df
            except Exception as exc:
                st.error(f"API request failed: {exc}")
                return

    df: pd.DataFrame = st.session_state.get("recall_df", pd.DataFrame())

    if df.empty:
        st.info("No recalls found. Try broadening your search or removing filters.")
        return

    # --- Apply client-side date filter ---
    if len(date_range) == 2 and "recall_initiation_date" in df.columns:
        start = pd.Timestamp(date_range[0])
        end = pd.Timestamp(date_range[1])
        df = df[
            (df["recall_initiation_date"] >= start) &
            (df["recall_initiation_date"] <= end)
        ]

    # --- Summary metrics ---
    st.subheader("Summary")
    col_totals, col_class, col_detail = st.columns([1, 1, 2])

    with col_totals:
        st.metric("Total Recalls", len(df))

    with col_class:
        if "classification" in df.columns:
            class1 = df["classification"].str.contains("Class I", na=False) & \
                     ~df["classification"].str.contains("Class II", na=False) & \
                     ~df["classification"].str.contains("Class III", na=False)
            st.metric(
                "Class I (Highest Risk)",
                int(class1.sum()),
                help=CLASS_I_HELP,
            )

    show_brand = "recalling_firm" in df.columns and not df.empty
    show_reason = "reason_for_recall" in df.columns and not df.empty
    if show_brand or show_reason:
        with col_detail:
            with st.container(border=True):
                if show_brand:
                    top_brand = df["recalling_firm"].value_counts().index[0]
                    st.metric("Top Recalled Brand", top_brand)
                if show_reason:
                    top_reason = df["reason_for_recall"].value_counts().index[0]
                    st.metric("Top Recall Reason", top_reason)

    # --- Results table ---
    st.subheader(f"Results - {len(df)} records")
    if "classification" in df.columns:
        st.caption("Hover the **Class** column header for recall severity definitions.")

    display_cols = [c for c in _DISPLAY_COLS if c in df.columns]
    display_df = df[display_cols].copy()

    if "recall_initiation_date" in display_df.columns:
        display_df["recall_initiation_date"] = (
            display_df["recall_initiation_date"].dt.strftime("%Y-%m-%d").fillna("Unknown")
        )

    display_df = display_df.rename(columns=_COL_LABELS)

    event = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Class": st.column_config.TextColumn(
                "Class",
                help=CLASS_COLUMN_HELP,
            ),
        },
    )

    # --- Drill-down detail ---
    selected_rows = event.selection.rows if event.selection else []
    if selected_rows:
        row = df.iloc[selected_rows[0]]
        st.subheader("Recall Detail")
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
                date_val = row.get("recall_initiation_date", pd.NaT)
                date_str = date_val.strftime("%Y-%m-%d") if pd.notna(date_val) else "N/A"
                st.write(f"**Date Initiated:** {date_str}")
                st.write(f"**Product Type:** {row.get('product_type', 'N/A')}")
                st.write(f"**Quantity:** {row.get('product_quantity', 'N/A')}")
                st.write(f"**Category:** {row.get('category', 'N/A')}")
            st.write(f"**Product Description:** {row.get('product_description', 'N/A')}")
            st.write(f"**Reason for Recall:** {row.get('reason_for_recall', 'N/A')}")
            st.write(f"**Distribution Pattern:** {row.get('distribution_pattern', 'N/A')}")

    # --- CSV export ---
    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Results as CSV",
        data=csv_bytes,
        file_name="fda_recalls.csv",
        mime="text/csv",
    )

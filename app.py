import streamlit as st

from components.dashboard import render_dashboard_page
from components.map_view import render_map_page
from components.search import render_search_page

st.set_page_config(
    page_title="FDA Recall Risk Monitor",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("FDA Recall Risk Monitor")
st.sidebar.caption("Powered by the openFDA Enforcement API")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    options=["Search & Results", "Risk Dashboard", "Map View"],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.markdown(
    "**Data source:** [openFDA Enforcement API](https://open.fda.gov/apis/food/enforcement/)  \n"
    "Results cached for 5 minutes."
)

# ---------------------------------------------------------------------------
# Route to page
# ---------------------------------------------------------------------------
if page == "Search & Results":
    render_search_page()
elif page == "Risk Dashboard":
    render_dashboard_page()
elif page == "Map View":
    render_map_page()

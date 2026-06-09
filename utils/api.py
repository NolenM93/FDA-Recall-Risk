import requests
import pandas as pd
import streamlit as st
from typing import Optional

BASE_URL = "https://api.fda.gov/food/enforcement.json"
MAX_LIMIT = 1000


@st.cache_data(ttl=300, show_spinner=False)
def fetch_recalls(
    search_query: Optional[str] = None,
    limit: int = 100,
) -> dict:
    """
    Perform an HTTP GET against the openFDA Food Enforcement endpoint.

    Parameters
    ----------
    search_query : str, optional
        Search string passed to the openFDA search parameter.
    limit : int
        Number of records to return (capped at 1,000 per API rules).

    Returns
    -------
    dict
        Raw JSON response body.

    Raises
    ------
    requests.HTTPError
        If the API returns a non-2xx status code.
    """
    params: dict = {"limit": min(limit, MAX_LIMIT)}
    if search_query:
        params["search"] = search_query

    response = requests.get(BASE_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_recalls_dataframe(
    search_query: Optional[str] = None,
    limit: int = 100,
) -> pd.DataFrame:
    """
    Fetch recall data and return a Pandas DataFrame.

    Returns an empty DataFrame if the API returns no results or
    if the request fails.
    """
    try:
        data = fetch_recalls(search_query=search_query, limit=limit)
        results = data.get("results", [])
        return pd.DataFrame(results) if results else pd.DataFrame()
    except requests.HTTPError as exc:
        # 404 means zero results for this query — not a fatal error
        if exc.response is not None and exc.response.status_code == 404:
            return pd.DataFrame()
        raise

import requests
import pandas as pd
import streamlit as st
from typing import Optional

BASE_URL = "https://api.fda.gov/food/enforcement.json"
MAX_LIMIT = 1000
MAX_SKIP = 25000  # openFDA hard cap — skip values above this return 400


@st.cache_data(ttl=300, show_spinner=False)
def fetch_recalls(
    search_query: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
) -> dict:
    """
    Perform an HTTP GET against the openFDA Food Enforcement endpoint.

    Parameters
    ----------
    search_query : str, optional
        Search string passed to the openFDA search parameter.
    limit : int
        Number of records to return (capped at 1,000 per API rules).
    skip : int
        Number of records to skip (for pagination).

    Returns
    -------
    dict
        Raw JSON response body.

    Raises
    ------
    requests.HTTPError
        If the API returns a non-2xx status code.
    """
    if skip >= MAX_SKIP:
        return {"results": []}

    params: dict = {"limit": min(limit, MAX_LIMIT), "skip": skip}
    if search_query:
        params["search"] = search_query

    response = requests.get(BASE_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_recalls_dataframe_single(
    search_query: Optional[str] = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Fetch a single API page (limit <= 1,000) and return a DataFrame."""
    try:
        data = fetch_recalls(search_query=search_query, limit=limit)
        results = data.get("results", [])
        return pd.DataFrame(results) if results else pd.DataFrame()
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return pd.DataFrame()
        raise


def fetch_recalls_dataframe(
    search_query: Optional[str] = None,
    limit: int = 100,
    fetch_all: bool = False,
) -> pd.DataFrame:
    """
    Fetch recall data and return a Pandas DataFrame.

    When *limit* exceeds 1,000 or *fetch_all* is True, pages through the API
    in 1,000-record increments until the response count drops below the page
    size (or the requested limit is reached), then concatenates all pages.

    Returns an empty DataFrame if the API returns no results or
    if the request fails.
    """
    if not fetch_all and limit <= MAX_LIMIT:
        return _fetch_recalls_dataframe_single(search_query=search_query, limit=limit)

    frames: list[pd.DataFrame] = []
    skip = 0
    total_available: Optional[int] = None
    target = None if fetch_all else limit
    progress = st.progress(0, text="Fetching recall data…")

    while True:
        page_limit = MAX_LIMIT
        if target is not None:
            remaining = target - skip
            if remaining <= 0:
                break
            page_limit = min(page_limit, remaining)

        # openFDA hard cap: skip > 25,000 returns 400
        if skip >= 25000:
            break

        try:
            data = fetch_recalls(
                search_query=search_query,
                limit=page_limit,
                skip=skip,
            )
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code in (400, 404):
                break
            raise

        results = data.get("results", [])
        if total_available is None:
            total_available = (
                data.get("meta", {}).get("results", {}).get("total")
            )

        if not results:
            break

        frames.append(pd.DataFrame(results))
        skip += len(results)

        if total_available:
            pct = min(skip / total_available, 1.0)
            progress.progress(
                pct,
                text=f"Fetched {skip:,} of {total_available:,} records…",
            )
        else:
            progress.progress(
                min(skip / (skip + page_limit), 0.99),
                text=f"Fetched {skip:,} records…",
            )

        if len(results) < page_limit:
            break

    progress.progress(1.0, text="Fetch complete")
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

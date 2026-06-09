import re
from typing import List

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

US_STATES: set = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}

ALL_STATES: List[str] = sorted(US_STATES)

# Keywords used to classify a product description into a food category.
# Ordered from most-specific to least-specific to avoid misclassification.
CATEGORY_KEYWORDS: dict = {
    "Seafood":            ["fish", "salmon", "tuna", "shrimp", "crab", "lobster",
                           "shellfish", "oyster", "seafood", "clam", "scallop", "tilapia"],
    "Meat & Poultry":     ["beef", "chicken", "pork", "turkey", "sausage", "meat",
                           "poultry", "ham", "bacon", "hot dog", "deli", "lamb", "veal"],
    "Dairy":              ["milk", "cheese", "butter", "cream", "yogurt", "dairy",
                           "whey", "lactose", "ice cream", "kefir", "ricotta"],
    "Produce":            ["salad", "lettuce", "spinach", "kale", "tomato", "cucumber",
                           "pepper", "onion", "fruit", "vegetable", "produce", "apple",
                           "berry", "melon", "sprout", "herb", "cilantro", "basil"],
    "Bakery & Snacks":    ["bread", "cake", "cookie", "cracker", "chip", "snack",
                           "pretzel", "cereal", "granola", "pastry", "muffin", "bagel",
                           "tortilla", "wafer"],
    "Nuts & Seeds":       ["nut", "peanut", "almond", "cashew", "pistachio", "walnut",
                           "seed", "sunflower", "tahini", "pecan", "hazelnut"],
    "Beverages":          ["juice", "water", "drink", "beverage", "tea", "coffee",
                           "soda", "wine", "beer", "smoothie", "kombucha"],
    "Spices & Condiments":["spice", "sauce", "dressing", "seasoning", "condiment",
                           "vinegar", "mustard", "ketchup", "salsa", "marinade",
                           "pepper flake", "cumin", "paprika"],
    "Prepared Foods":     ["soup", "frozen", "ready", "meal", "dinner", "entree",
                           "pasta", "rice", "noodle", "burrito", "pizza", "stew"],
}

# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize and clean a raw openFDA recall DataFrame.

    - Parses YYYYMMDD date columns to datetime.
    - Strips leading/trailing whitespace from all string columns.
    - Fills key nullable text fields with sensible defaults.
    """
    if df.empty:
        return df

    df = df.copy()

    # Parse date columns (openFDA encodes dates as 'YYYYMMDD' strings)
    for date_col in ("recall_initiation_date", "report_date", "center_classification_date"):
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], format="%Y%m%d", errors="coerce")

    # Strip whitespace from all object columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    # Fill missing values for fields used throughout the app
    defaults = {
        "product_description": "Unknown",
        "recalling_firm":      "Unknown",
        "reason_for_recall":   "Unknown",
        "classification":      "Unknown",
        "distribution_pattern":"",
        "status":              "Unknown",
        "product_type":        "Unknown",
        "product_quantity":    "Unknown",
        "recall_number":       "N/A",
    }
    for col, fill in defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(fill)

    return df


# ---------------------------------------------------------------------------
# Category assignment
# ---------------------------------------------------------------------------

def _assign_category(description: str) -> str:
    """Map a product description string to one of the defined food categories."""
    text = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other"


def add_category_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'category' column derived from 'product_description'."""
    if "product_description" in df.columns:
        df = df.copy()
        df["category"] = df["product_description"].apply(_assign_category)
    return df


# ---------------------------------------------------------------------------
# Geographic parsing
# ---------------------------------------------------------------------------

_STATE_TOKEN_RE = re.compile(r"\b([A-Z]{2})\b")


def extract_states(distribution_pattern: str) -> List[str]:
    """
    Return a list of US state abbreviations mentioned in a distribution
    pattern string.

    Handles:
    - "Nationwide" / "All 50 States" → returns all 50 + DC
    - Comma-separated or space-separated state codes
    """
    if not distribution_pattern:
        return []

    text = distribution_pattern.upper()
    tokens = _STATE_TOKEN_RE.findall(text)
    return [t for t in tokens if t in US_STATES]


def build_state_counts(df: pd.DataFrame) -> pd.Series:
    """
    Aggregate recall counts per US state from the 'distribution_pattern' column.

    Returns a Series indexed by state abbreviation.
    """
    if "distribution_pattern" not in df.columns:
        return pd.Series(dtype=int)

    counter: dict = {s: 0 for s in US_STATES}
    for pattern in df["distribution_pattern"]:
        for state in extract_states(str(pattern)):
            counter[state] = counter.get(state, 0) + 1

    return pd.Series(counter).sort_values(ascending=False)


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------

def aggregate_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of recall counts grouped by food category."""
    if df.empty:
        return pd.DataFrame(columns=["category", "recall_count"])
    if "category" not in df.columns:
        df = add_category_column(df)
    return (
        df.groupby("category")
        .size()
        .reset_index(name="recall_count")
        .sort_values("recall_count", ascending=False)
        .reset_index(drop=True)
    )


def aggregate_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of recall counts grouped by calendar month."""
    if df.empty or "recall_initiation_date" not in df.columns:
        return pd.DataFrame(columns=["month", "recall_count"])

    temp = df.copy()
    temp["month"] = temp["recall_initiation_date"].dt.to_period("M").dt.to_timestamp()
    return (
        temp.groupby("month")
        .size()
        .reset_index(name="recall_count")
        .sort_values("month")
        .reset_index(drop=True)
    )

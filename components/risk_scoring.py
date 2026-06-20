import numpy as np
import pandas as pd

from utils.data_processing import add_category_column, aggregate_by_category

# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

RISK_COLORS: dict = {
    "High":   "#ef4444",
    "Medium": "#f59e0b",
    "Low":    "#22c55e",
}


def compute_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify food categories as Low / Medium / High risk based on recall
    frequency using percentile thresholds.

    The approach is deliberately simple and explainable:
    - Bottom third by recall count  → Low
    - Middle third                  → Medium
    - Top third                     → High

    This keeps the scoring transparent and auditable without requiring a
    trained model. This is a key requirement for a public-safety tool.

    Returns
    -------
    pd.DataFrame
        Columns: category, recall_count, risk_level
    """
    if df.empty:
        return pd.DataFrame(columns=["category", "recall_count", "risk_level"])

    df = add_category_column(df)
    category_counts = aggregate_by_category(df)

    if category_counts.empty:
        return category_counts

    counts = category_counts["recall_count"].values
    low_thresh = np.percentile(counts, 33)
    high_thresh = np.percentile(counts, 67)

    def _classify(count: int) -> str:
        if count >= high_thresh:
            return "High"
        if count >= low_thresh:
            return "Medium"
        return "Low"

    category_counts = category_counts.copy()
    category_counts["risk_level"] = category_counts["recall_count"].apply(_classify)
    return category_counts.sort_values("recall_count", ascending=False).reset_index(drop=True)

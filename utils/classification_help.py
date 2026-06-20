"""Plain-language FDA recall classification definitions for UI tooltips."""

CLASS_I_HELP = (
    "Most serious - poses a risk of serious health consequences or death."
)
CLASS_II_HELP = (
    "May cause temporary or reversible adverse health effects."
)
CLASS_III_HELP = (
    "Least serious - product violates FDA regulations but is unlikely to cause harm."
)

CLASSIFICATION_FILTER_HELP = "\n".join([
    f"- **Class I:** {CLASS_I_HELP}",
    f"- **Class II:** {CLASS_II_HELP}",
    f"- **Class III:** {CLASS_III_HELP}",
])

CLASS_COLUMN_HELP = CLASSIFICATION_FILTER_HELP


def help_for_classification(value: str) -> str | None:
    """Return tooltip text for a classification label, if recognized."""
    if not value:
        return None
    text = value.upper()
    if "CLASS I" in text and "CLASS II" not in text and "CLASS III" not in text:
        return CLASS_I_HELP
    if "CLASS II" in text:
        return CLASS_II_HELP
    if "CLASS III" in text:
        return CLASS_III_HELP
    return None

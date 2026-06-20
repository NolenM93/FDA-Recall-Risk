# FDA Recall Risk Monitor - Research & Development Report

**Assignment 2 Technical Document**  
**Project:** FDA Recall Risk Monitor  
**Platform:** Python / Streamlit Web Application  
**API:** openFDA Food Enforcement API  

---

## Introduction

Regulatory recall data has existed in publicly accessible form for years, yet no consumer-facing tool synthesizes that data into actionable safety intelligence. The openFDA Enforcement API provides machine-readable access to thousands of Food and Drug Administration food recall enforcement reports. The challenge is not data availability, it is transforming a raw, inconsistently formatted JSON stream into a product that communicates risk clearly and immediately. This document reports on the technical investigation undertaken to prove the selected stack (Python, Streamlit, Pandas, Scikit-Learn, Plotly Express, openFDA API) is capable of delivering a functionally complete MVP and to identify the constraints and risks that must be managed during the production cycle.

---

## PP4 Feature List

1. Live recall data: fetched from the openFDA Enforcement API  
2. Keyword search across product name, recalling firm, or reason for recall  
3. Filter results by recall classification (Class I, II, III)  
4. Filter results by product type (Food, Dietary Supplement, Cosmetics)  
5. Filter results by date range (start/end date)  
6. Results table with plain-language column labels  
7. Drill-down detail panel: full product description, distribution scope, classification, reason, quantity  
8. CSV export of filtered recall results  
9. Risk scoring dashboard: food categories ranked Low / Medium / High by recall frequency  
10. Summary metric cards: total recalls, Class I count, unique firms, top recall reason  
11. Trend line chart: monthly recall volume over time  
12. Recall count bar chart - breakdown by food category  
13. Category comparison panel - side-by-side recall counts for two user-selected categories  
14. Geographic choropleth heatmap - recall frequency by U.S. state parsed from distribution pattern field  

---

## R&D Feature List

**UI Components (Streamlit)**

1. `st.text_input` - keyword search bar for product, company, or reason  
2. `st.multiselect` - classification filter (Class I / II / III)  
3. `st.multiselect` - product type filter  
4. `st.date_input` - date range picker (start and end)  
5. `st.selectbox` - record limit selector (50 / 100 / 200 / 500)  
6. `st.dataframe` with `on_select="rerun"` - interactive results table supporting single-row selection  
7. `st.metric` cards - KPI display for total recalls, Class I count, unique firms  
8. Plotly Express line chart rendered via `st.plotly_chart` - recall volume over time  
9. Plotly Express horizontal bar chart - recall counts per food category  
10. Plotly Express choropleth (`locationmode="USA-states"`) - geographic heatmap  
11. `st.download_button` - CSV export of filtered DataFrame  
12. `st.container(border=True)` - drill-down detail card for selected recall row  
13. `@st.cache_data(ttl=300)` - 5-minute response caching on all API calls  

**Data / API**

14. HTTP GET to `https://api.fda.gov/food/enforcement.json` via `requests.get`  
15. `limit` parameter handling for result-set sizing  
16. 404-response handling (openFDA returns 404 for zero-result queries, not an empty array)  
17. JSON response parsing - `data["results"]` extracted into `pd.DataFrame`  
18. YYYYMMDD → `pd.Timestamp` conversion via `pd.to_datetime(..., format="%Y%m%d", errors="coerce")`  
19. Whitespace normalization across all string columns  
20. Null-fill defaults for `product_description`, `recalling_firm`, `classification`, `distribution_pattern`  
21. Keyword-based food category assignment from `product_description` text  
22. `groupby("category").size()` aggregation for risk scoring and bar chart  
23. `dt.to_period("M")` monthly bucketing for trend line chart  
24. Regex token extraction (`\b[A-Z]{2}\b`) of U.S. state codes from `distribution_pattern`  

**ML / Analytics**

25. Percentile-threshold risk classifier - 33rd/67th percentile cutoffs on category recall counts → Low / Medium / High labels  

---

## Technology Analysis

### Stack Selection Rationale

Three core tooling decisions required explicit justification before development began.

**Streamlit over Dash or Flask+React.** Plotly Dash is a capable dashboard framework, but it requires callback decorators and a component-property binding model that imposes significant boilerplate for a single-developer project under a two-week deadline. Flask with a React frontend separates concerns cleanly but introduces a build pipeline, a JavaScript dependency tree, and a context switch between two languages. Streamlit's execution model, a Python script that reruns on every interaction, collapses the frontend and backend into a single file, eliminates the build step entirely, and ships interactive charts, tables, and widgets with one-line calls. For a data-heavy MVP where iteration speed matters more than pixel-perfect control, Streamlit is the appropriate trade-off. The framework's documented limitation (full script rerun on each interaction) is mitigated through `st.session_state` and `@st.cache_data`, both of which are standard Streamlit patterns (Streamlit, 2024a).

**openFDA Enforcement API over data.gov CSV bulk downloads or USDA feeds.** The data.gov recall CSV exports are static snapshots updated on irregular schedules, which means any application built on them cannot guarantee currency. The USDA FoodSafety.gov feed covers FSIS-regulated products (meat, poultry, eggs) but not the broader FDA jurisdiction that includes produce, dairy, and packaged foods - the categories with the highest recall volume. The openFDA Enforcement API delivers live, queryable data across all FDA product types via a single endpoint, supports Lucene field-level filtering, and is free to use without registration. These properties make it the only source that simultaneously satisfies currency, breadth, and developer accessibility requirements (U.S. Food & Drug Administration, 2023).

**Plotly Express over Matplotlib or Bokeh.** Matplotlib produces publication-quality static figures but has no built-in interactivity. Bokeh supports interactivity but requires a separate Bokeh server or explicit JavaScript callbacks for tooltips and hover events. Plotly Express generates interactive figures, hover, zoom, pan, choropleth color scales as self-contained HTML objects that `st.plotly_chart` renders natively. The unified API across chart types (line, bar, choropleth) means the same import and the same layout dictionary handle all three visualization types in this project.

### openFDA Enforcement API

The openFDA API follows Lucene query syntax for its `search` parameter, which provides expressive field-level filtering but introduces a critical edge case: the API returns HTTP 404 (not an empty JSON array) when a query yields zero results. A naive implementation that does not intercept this status code raises an unhandled exception on every legitimate no-results query. The solution implemented here catches `requests.HTTPError`, checks the response status, and returns an empty `pd.DataFrame` for 404s while re-raising all other errors. This behavior is documented in the openFDA API FAQs but is not obvious from the endpoint specification alone (U.S. Food & Drug Administration, 2023).

A second limitation is pagination: a single request is hard-capped at 1,000 records (`limit=1000`). Applications requiring complete historical datasets must implement a `skip`-based pagination loop, repeating requests and concatenating results until the response count falls below the requested limit. For the MVP, a single fetch of up to 1,000 records is sufficient to demonstrate all three pillars (search, risk scoring, map), but a production build will require a background fetch-and-cache layer to assemble the full dataset without blocking the UI.

Rate limits also apply. Without an API key, the service allows approximately 240 requests per minute per IP address. The `@st.cache_data(ttl=300)` decorator on every API call mitigates this: identical queries are served from an in-memory cache for five minutes, reducing live requests dramatically during normal interactive use (Streamlit, 2024a).

### Streamlit Session State and Widget Model

Streamlit reruns the entire script from top to bottom on every user interaction. This stateless execution model requires explicit use of `st.session_state` to persist fetched data between widget interactions without re-hitting the API. The search page stores the retrieved `pd.DataFrame` in `st.session_state["recall_df"]`; subsequent filter changes or row selections operate on the cached frame rather than triggering a new network request.

The `on_select="rerun"` parameter of `st.dataframe`, introduced in Streamlit 1.35, enables native row selection without third-party components. When a user clicks a row, Streamlit reruns the script and the selected index is available via `event.selection.rows`. This is a recent addition; codebases targeting earlier Streamlit versions must fall back to a `st.selectbox` for row selection (Streamlit, 2024b).

A key lesson encountered during development: widget keys must be unique across the entire script or Streamlit raises a `DuplicateWidgetID` error at runtime. This is particularly relevant when rendering widgets inside loops or conditionally rendered components.

### Pandas Data Cleaning: Distribution Pattern Challenges

The `distribution_pattern` field is the most structurally inconsistent field in the dataset. Observed formats include: `"Nationwide"`, `"AL, AK, AZ, AR, CA"`, `"Sold in AL and TN"`, `"United States and Canada"`, `"The product was distributed to stores in the following states: FL, GA, SC"`, and free-text paragraphs with no state codes at all. A regex that extracts two-capital-letter tokens (`\b[A-Z]{2}\b`) successfully captures state abbreviations in the majority of cases, but also matches non-state tokens such as `"US"`, `"UK"`, `"OR"` (conflated with Oregon), and drug route abbreviations. The implementation filters extracted tokens against a hard-coded set of valid USPS state codes, eliminating false positives. Records with unstructured prose in `distribution_pattern` and no matching state codes contribute zero counts to the heatmap - an acceptable data-quality tradeoff for the MVP but one that should be addressed with a more robust NLP parser in a later iteration. The broader challenge of cleaning real-world, user-generated string fields - normalizing whitespace, coercing dates, filling nulls - is addressed throughout the pipeline using Pandas `str` accessor methods and `pd.to_datetime` with `errors="coerce"`, standard practices documented in the Pandas user guide (pandas development team, 2024).

McKinney (2022) identifies inconsistent string encoding and mixed null representations as the most common sources of data quality failure in production pipelines. Both appear in the openFDA dataset: `distribution_pattern` contains Unicode dashes, inconsistent comma spacing, and entries that are `None`, empty string, or the literal string `"N/A"` - all of which must be normalized before regex extraction can proceed reliably.

### Plotly Express Choropleth vs. Folium

The original pitch specified Folium for geographic visualization. During R&D, Folium was evaluated and found to require embedding via `st.components.v1.html`, which renders the map inside an iframe without responsive sizing and requires manual HTML/JavaScript string construction for tooltips. Plotly Express provides a native `px.choropleth` with `locationmode="USA-states"` that accepts a DataFrame directly, integrates with `st.plotly_chart`, and supports hover tooltips, color scales, and consistent theming with no additional markup. The decision to replace Folium with Plotly Express for the choropleth represents a meaningful improvement to the UI and reduces code complexity. This substitution is documented here to inform the full team.

### Scikit-Learn Risk Scoring

The risk scoring module uses NumPy percentile thresholds rather than a trained Scikit-Learn estimator because the feature space - a single integer (recall count per category) - is too narrow to justify supervised learning. Percentile-based classification is transparent, requires no labeled training data, and produces results that update automatically as new API data arrives. Scikit-Learn's `IsolatedForest` and `OneClassSVM` were evaluated for outlier detection; however, Tukey's fence (IQR method) was selected because it is interpretable without domain expertise and produces consistent results on sample sizes as small as 10 firms. The Scikit-Learn import is retained in `requirements.txt` because the production build will require a trained classifier to predict recall risk from leading indicators (ingredient type, company history, season) - a feature planned for the post-MVP phase.

---

## Feasibility Evaluation

The technology stack is confirmed to meet all MVP requirements. The openFDA API supplies all recall fields needed for search, risk scoring, and geographic mapping within a single endpoint. Streamlit delivers a usable multi-page dashboard in Python without a separate frontend framework. Plotly Express covers all three visualization types (line, bar, choropleth) in a unified API. The only capability not yet demonstrated end-to-end is predictive risk scoring from leading indicators, which requires a labeled training set and a trained model - deferred to the post-MVP phase.

**Identified risks and mitigations:**

| Risk | Likelihood | Mitigation |
|---|---|---|
| openFDA API downtime or rate limiting | Medium | `@st.cache_data` caching; graceful error messages |
| Incomplete `distribution_pattern` field | High | Nationwide keyword detection; regex fallback; user-visible data-quality note |
| 1,000-record pagination cap limiting heatmap accuracy | High | Implement multi-page fetch loop before Week 2 end |
| `distribution_pattern` free-text → missed state extractions | High | NLP expansion post-MVP |
| Streamlit rerun performance on large DataFrames | Low | Limit fetch to ≤ 1,000 records; cache aggressively |

**What is not possible with this stack (boundaries):**

- Real-time push notifications when a new recall is issued (Streamlit has no WebSocket push model; polling is required)  
- User accounts or saved search history (Streamlit has no built-in authentication or persistent user storage)  
- Sub-second map rendering for datasets > 5,000 records without a spatial database backend  
- Predictive scoring from unstructured recall reason text without a fine-tuned NLP model  

---

## References

Streamlit. (2024a). *Cache data*. Streamlit Documentation. https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data

Streamlit. (2024b). *st.dataframe - on_select*. Streamlit Documentation. https://docs.streamlit.io/develop/api-reference/data/st.dataframe

U.S. Food & Drug Administration. (2023). *openFDA food enforcement API reference*. openFDA. https://open.fda.gov/apis/food/enforcement/

McKinney, W. (2022). *Python for data analysis: Data wrangling with pandas, NumPy, and Jupyter* (3rd ed.). O'Reilly Media. https://wesmckinney.com/book/

pandas development team. (2024). *User guide: Working with text data*. pandas documentation. https://pandas.pydata.org/docs/user_guide/text.html

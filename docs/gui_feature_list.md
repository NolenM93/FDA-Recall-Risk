# FDA Recall Risk Monitor - GUI Feature List

**Assignment 3 Document**
**Project:** FDA Recall Risk Monitor
**Platform:** Python / Streamlit Web Application
**Date:** June 2026

---

## Section 1 , Similar Products Researched

### FoodSafety.gov (USDA / HHS)

FoodSafety.gov is the official government consumer portal for food recall announcements. It provides a basic searchable list of recall alerts with product name, company, and recall reason. The interface is static , each result is a plain text entry or a linked press release. There is no data visualization, no filtering by classification, no geographic mapping, and no indication of relative risk between categories. The target audience is general consumers, and the tool treats every recall as equally urgent regardless of Class I, II, or III designation.

### openFDA Portal (FDA)

The openFDA developer portal exposes the raw enforcement database through an interactive query explorer. Users can manually construct API queries and view JSON responses in-browser. While technically complete , every field in the dataset is accessible , the interface assumes developer knowledge. There are no plain-language labels, no charts, no geographic views, and no risk aggregation. A general consumer or food safety professional with no API experience cannot derive any actionable insight from the tool without writing code.

---

## Section 2 , Features Borrowed from Similar Products

| Feature | Borrowed From | How It Is Used Here |
|---------|--------------|---------------------|
| **Keyword Search Bar** | FoodSafety.gov | A prominent search input at the top of the Search & Results page mirrors FoodSafety.gov's primary interaction. The difference: this implementation passes the term directly to the openFDA `search` parameter, returning a structured, filterable DataFrame rather than a static press-release page. |
| **Filterable Results Table** | openFDA Portal | The openFDA Portal exposes tabular data. This product adopts the concept of presenting recall records in a table but replaces raw API field names with plain-language column headers (Date, Company, Product, Class, Reason, Category) and adds classification and product-type filter widgets alongside it. |
| **Recall Detail View** | FoodSafety.gov | FoodSafety.gov links each recall entry to a detail page with the full product description and distribution information. This product replicates that depth inside a drill-down card that expands below the results table when a row is clicked , no page navigation required. |

---

## Section 3 , Improvements Over Poor Interface Choices in Similar Products

### Problem: No Risk Context (FoodSafety.gov)

FoodSafety.gov lists recalls chronologically with no indication of severity, frequency, or category risk. A consumer reading the list has no way to determine whether dairy is currently more dangerous than produce, or whether a given company has an unusual recall history.  
**Improvement:** The Risk Scoring Dashboard classifies each food category as Low, Medium, or High risk based on current recall frequency, giving users an at-a-glance answer to "what should I be worried about right now."

### Problem: No Geographic Context (Both Products)

Neither FoodSafety.gov nor the openFDA Portal visualizes where recalls are concentrated geographically. A user in California has no way to know whether their region has a disproportionate number of active distribution alerts.  
**Improvement:** The geographic choropleth heatmap parses each recall's distribution pattern field and maps recall frequency by U.S. state, making regional risk immediately visible.

### Problem: No Time-Series Visualization (Both Products)

Neither tool shows whether recall frequency is trending up or down over time. Without temporal context, a high current count could reflect a one-time spike or a sustained increase , a critical distinction for food safety decision-making.  
**Improvement:** The monthly trend line chart renders recall volume over time so users can distinguish a temporary outbreak from a structural increase.

### Problem: No Category Comparison Tool (Both Products)

Both existing products treat recall data as a flat list. There is no mechanism to directly compare the recall burden of two food categories against each other.  
**Improvement:** The Category Comparison panel lets users select any two food categories and renders a side-by-side bar chart answering the direct question: "Is dairy actually recalled more often than produce?"

### Problem: Developer-Only Access to Structured Data (openFDA Portal)

The openFDA Portal's query explorer is useful only to developers who understand Lucene syntax, JSON structure, and REST API conventions. Non-technical users , food safety professionals, journalists, regulators , are effectively locked out.  
**Improvement:** All filtering, searching, and data retrieval is handled through standard Streamlit widgets. No API knowledge is required to interact with the full dataset.

---

## Section 4 , Prioritized Feature List (Full Product)

Features are ordered by user-facing impact, highest first.

| # | Feature | Type | Status |
|---|---------|------|--------|
| 1 | Live recall data fetched from the openFDA Enforcement API | Data | Built |
| 2 | Keyword search across product name, recalling firm, or reason for recall | Borrowed | Built |
| 3 | Filter by recall classification (Class I, II, III) | Borrowed | Built |
| 4 | Filter by product type (Food, Dietary Supplement, Cosmetics) | Borrowed | Built |
| 5 | Filter by date range (start / end date) | Borrowed | Built |
| 6 | Results table with plain-language column labels | Borrowed | Built |
| 7 | Drill-down detail panel on row click | Borrowed | Built |
| 8 | CSV export of filtered recall results | Borrowed | Built |
| 9 | Risk scoring dashboard , Low / Medium / High per food category | Original | Built |
| 10 | Summary metric cards (total recalls, Class I count, unique firms, top reason) | Original | Built |
| 11 | Trend line chart , monthly recall volume over time | Original | Built |
| 12 | Recall count bar chart , breakdown by food category | Original | Built |
| 13 | Category comparison panel , side-by-side counts for two selected categories | Original | Built |
| 14 | Geographic choropleth heatmap , recall frequency by U.S. state | Original | Built |
| 15 | Predictive risk scoring from leading indicators (company history, category, season) | Original | Post-MVP |
| 16 | NLP-based state extraction from unstructured distribution pattern text | Original | Post-MVP |

---

## Section 4b , Feature #15 Planned Extension (Week 4)

Feature #15 extends the Risk Dashboard with predictive signals that answer **"what may become high next?"** in addition to the current percentile scoring, which answers **"what is high right now?"**

### Current logic (built, unchanged)

Each food category receives a Low / Medium / High rating from recall frequency relative to other categories using transparent 33rd/67th percentile thresholds in `compute_risk_scores()`.

### Planned additive layer (Week 4 prototype)

The percentile `risk_level` stays. A separate watch/trend layer is added per category without replacing the color-coded score.

| Leading indicator | openFDA field(s) | Planned use (Week 4) |
|---|---|---|
| Company recall history | `recalling_firm` | Count recalls per firm; flag categories where a small number of firms account for a large share of recalls |
| Repeat-offender firms | `recalling_firm` | Firms with 2+ recalls in the loaded dataset; surface a "Watch" signal when they dominate a category |
| Category seasonality | `recall_initiation_date` + derived `category` | Compare recent 90-day recall volume vs the prior period or same month in prior years |
| Severity weight (optional) | `classification` | Weight Class I share within a category as an early-warning boost |
| Trend direction | `recall_initiation_date` | Reuse monthly aggregation logic; flag categories with a rising recall slope |

**Not available without Feature #16 (NLP):** unstructured signals from `reason_for_recall` or `product_description` text.

**Data volume note:** The dashboard currently loads 500 records. The Week 4 prototype should increase fetch size (e.g. 5,000+) so seasonality and firm-history signals are meaningful.

### User-facing change (Week 4)

Risk score cards keep their Low / Medium / High color coding. Each card gains a secondary line when a leading indicator fires, for example:

- `Trend: Rising`
- `Watch: repeat firms`

### Week 3 vs Week 4 deliverables

| Week | Deliverable |
|---|---|
| Week 3 | Leading indicators defined against openFDA fields; additive UX design documented here and in the research paper |
| Week 4 | Implement `compute_predictive_signals()` in `components/risk_scoring.py`, wire into `components/dashboard.py`, increase dashboard data fetch, test against live API |

Feature #15 remains **Post-MVP** in the table above until the Week 4 code ships.

---

## Section 5 , Features the Prototype Accomplishes

The current working Streamlit prototype covers all 14 built features listed above across three screens accessible via sidebar navigation:

### Screen 1 , Search & Results

- Live keyword search against the openFDA Enforcement API
- Classification, product type, and date range filters
- Paginated results table with plain-language column labels
- Single-row click expands full recall detail card
- Summary metric cards (total, Class I, unique firms, top reason)
- CSV download of current filtered result set

### Screen 2 , Risk Dashboard

- Per-category Low / Medium / High risk score cards (color-coded)
- Monthly trend line chart showing recall volume over time
- Horizontal bar chart of recall counts per food category
- Side-by-side category comparison bar chart with user-selected categories

### Screen 3 , Map View

- Plotly Express choropleth map of recall frequency by U.S. state
- Record limit selector to control dataset size
- Hover tooltips showing state name and recall count

Feature #15 leading indicators and the additive scoring design are documented in Section 4b (Week 3). The code prototype is deferred to Week 4. Feature #16 (NLP state extraction) remains post-MVP and is not yet documented for implementation.

---

*FDA Recall Risk Monitor | Assignment 3 GUI Feature List | June 2026*

# RoadPulse Analytics

**A reproducible, decision-focused analysis of 7.7 million US accident records (2016–2023), with a Python data pipeline and interactive Plotly dashboard.**

RoadPulse answers a practical question: **where and under what conditions should a transportation-safety analyst investigate first?** It moves beyond an exploratory notebook by separating data preparation, metric logic, quality checks, statistical interpretation, and an interactive decision surface.

> `Severity` measures traffic impact, not injury or fatality severity. RoadPulse describes supplied accident records; it does not estimate an individual driver's crash risk.

## End-to-end scope

- Schema, coverage, missingness, duplicates, cardinality and source analysis
- Mixed-timestamp cleaning, defensible exclusions and missingness handling
- Hour/day/weekend, weather, visibility and severe-record features
- Chunked transformation of 7.7M rows into compact Parquet marts
- Volume, severe-record rate, confidence intervals and coverage guardrails
- Source-specific comparisons that prevent a major reporting-composition error
- Geographic, temporal and conditions-based investigation priorities
- Responsive Dash/Plotly app with filters, drill-down, tables and methodology
- Pinned dependencies, shared KPI functions, tests and deployment configuration

## Most important finding

Naive state and year comparisons are not trustworthy because the collection sources have radically different severity mixes:

| Source | Records | Severe records | Severe-record rate |
|---|---:|---:|---:|
| Source1 | 4,325,632 | 351,813 | 8.13% |
| Source2 | 3,305,373 | 1,121,335 | 33.92% |
| Source3 | 97,389 | 30,899 | 31.73% |

Source1 grows sharply in later years and is the only source in partial 2023 data. A raw national trend would therefore mostly measure **reporting-composition change**, not a clean severity trend. RoadPulse defaults to within-Source2 comparisons and always exposes source coverage.

Other defensible findings:

- Source2's severe-record rate ranged from **30.29% to 36.85%** over 2016–2022.
- Weather and severity are statistically associated, but **Cramér's V = 0.0416**: a weak effect despite a tiny p-value.
- Level-4 records had the longest mean disruption (**183.7 minutes**) and affected distance (**1.50 miles**).
- Geographic queues are hypotheses for deeper study—not danger league tables—because population and vehicle-miles-travelled are absent.

## Dashboard

1. **Executive overview:** headline KPIs, coverage and comparable annual movement
2. **Geographic priorities:** sample-size filter, state ranking, county queue and Wilson intervals
3. **Risk conditions:** day/hour concentration plus weather and visibility cuts
4. **Data trust:** source bias, definitions, limitations and guardrails

The repository includes a small demo snapshot. Annual/state/county demo values come from the notebook. Temporal/weather demo rows are **interface fixtures only**, visibly marked in the app; run the full pipeline before interpreting them.

## Run locally

```bash
git clone https://github.com/Yahiaelgayarrr/roadpulse-analytics.git
cd roadpulse-analytics
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8050`.

## Full data pipeline

Download **US Accidents (2016–2023)** by Sobhan Moosavi from Kaggle, place it at `data/raw/US_Accidents_March23.csv`, then run:

```bash
python -m roadpulse.pipeline
python app.py
```

The raw file is ignored by Git. The pipeline reads it in chunks and writes reusable aggregate Parquet files to `data/processed/`.

### Kaggle route when the raw file is too large to transfer

Run `notebooks/kaggle_export_cell.py` as the final cell of the existing Kaggle
notebook. It uses the already-loaded cleaned `df` and produces
`/kaggle/working/roadpulse_processed.zip`. Download that small ZIP, extract its
files into `data/processed/`, and start the dashboard. No raw-data upload is
required.

## Structure

```text
├── app.py                     # Interactive Dash/Plotly application
├── assets/style.css           # Responsive visual system
├── roadpulse/
│   ├── config.py              # Paths and canonical definitions
│   ├── metrics.py             # KPI and confidence-interval logic
│   └── pipeline.py            # Chunked cleaning + analytical marts
├── data/demo/                 # Small, clearly labelled app snapshot
├── tests/                     # Metric and feature tests
├── roadpulse-analysis.ipynb   # Original exploratory/Kaggle analysis
├── reports/                   # Methodology and findings
├── requirements*.txt          # Reproducible environments
├── render.yaml                # Free Render deployment blueprint
└── Procfile                   # Production command
```

## KPI definitions

| KPI | Definition | Interpretation |
|---|---|---|
| Total accidents | Valid accident IDs in scope | Reporting volume, not true incidence |
| Severe accidents | `Severity ∈ {3,4}` | High traffic impact, not injury severity |
| Severe-record rate | Severe / total × 100 | Mix within reported records |
| 95% CI | Wilson interval | Sampling uncertainty, not reporting bias |
| Coverage | Included years and source | Required context for comparisons |

## Validate

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

## Limitations and next step

This observational reporting dataset has no exposure denominator. It cannot support causal claims or rankings of true road danger. The strongest next extension is joining FHWA vehicle miles travelled, Census population/urbanicity, NHTSA FARS outcomes, and roadway characteristics to create exposure-adjusted rates.

## Author

**Yahia El Gayar** — Computer Science & Engineering, German University in Cairo
[GitHub](https://github.com/Yahiaelgayarrr)

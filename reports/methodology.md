# Methodology and analytical guardrails

## Decision frame

RoadPulse helps identify where additional investigation, operational coverage, or exposure-adjusted analysis may be valuable. It does not label a location or condition as causally dangerous.

## Cleaning

- Parse mixed timestamp formats; remove rows without a valid ID, start time, state, or severity.
- Preserve missing weather as `Unknown`; do not silently equate missing precipitation with zero.
- Define severe records as traffic-impact severity levels 3 and 4.
- Use bounded categorical weather/visibility features and compact aggregate marts.

## Comparability

Collection source is a confounder: sources cover different locations and years and have different severity distributions. Comparisons must stay within a stable source. RoadPulse defaults to Source2 for 2016–2022; cross-source figures are coverage diagnostics.

## Uncertainty

Geographic views expose a minimum sample threshold and Wilson 95% intervals. They reduce unstable small-n rankings but do not repair selection bias or absent exposure denominators.

## Statistical interpretation

At millions of observations, tiny effects produce tiny p-values. RoadPulse reports effect size, magnitude and denominators. Weather × severity has Cramér's V = 0.0416 and is weak.

## Reproducibility

Metric logic lives in `roadpulse/metrics.py`, transformations in `roadpulse/pipeline.py`, and the dashboard consumes their outputs without redefining KPIs. Tests cover rates, Wilson intervals and weather categorization.

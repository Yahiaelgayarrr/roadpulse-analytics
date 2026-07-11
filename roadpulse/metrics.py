"""Shared KPI definitions used by the pipeline and dashboard."""
from __future__ import annotations

import pandas as pd


def add_rate(frame: pd.DataFrame, numerator: str = "severe_accidents", denominator: str = "total_accidents") -> pd.DataFrame:
    result = frame.copy()
    result["severe_rate"] = (100 * result[numerator] / result[denominator]).round(2)
    return result


def wilson_interval(successes: pd.Series, totals: pd.Series, z: float = 1.96) -> tuple[pd.Series, pd.Series]:
    """Return 95% Wilson confidence bounds for a binomial proportion."""
    p = successes / totals
    denominator = 1 + z**2 / totals
    centre = (p + z**2 / (2 * totals)) / denominator
    margin = z * ((p * (1 - p) / totals + z**2 / (4 * totals**2)) ** 0.5) / denominator
    return (100 * (centre - margin)).round(2), (100 * (centre + margin)).round(2)


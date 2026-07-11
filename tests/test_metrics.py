import pandas as pd

from roadpulse.metrics import add_rate, wilson_interval
from roadpulse.pipeline import weather_category


def test_add_rate_uses_explicit_denominator():
    result = add_rate(pd.DataFrame({"total_accidents": [200], "severe_accidents": [50]}))
    assert result.loc[0, "severe_rate"] == 25.0


def test_wilson_interval_contains_observed_rate():
    low, high = wilson_interval(pd.Series([50]), pd.Series([200]))
    assert low.iloc[0] < 25 < high.iloc[0]


def test_weather_categories_are_deterministic():
    assert weather_category("Heavy Rain / Windy") == "Rain"
    assert weather_category("Light Snow") == "Snow / ice"
    assert weather_category(None) == "Unknown"

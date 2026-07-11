"""Chunked, reproducible preparation pipeline for the 7.7M-row US Accidents dataset."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from roadpulse.config import PROCESSED_DIR, RAW_DATA, SEVERE_LEVELS
from roadpulse.metrics import add_rate, wilson_interval

USECOLS = [
    "ID", "Source", "Severity", "Start_Time", "End_Time", "State", "County", "City",
    "Start_Lat", "Start_Lng", "Distance(mi)", "Temperature(F)", "Humidity(%)",
    "Visibility(mi)", "Wind_Speed(mph)", "Precipitation(in)", "Weather_Condition",
    "Traffic_Signal", "Junction", "Crossing", "Stop", "Roundabout", "Railway",
    "Sunrise_Sunset",
]


def weather_category(value: object) -> str:
    text = str(value).lower()
    if text in {"nan", "none", ""}: return "Unknown"
    if any(x in text for x in ("thunder", "tornado")): return "Severe storm"
    if any(x in text for x in ("snow", "sleet", "ice", "wintry")): return "Snow / ice"
    if any(x in text for x in ("rain", "drizzle", "shower")): return "Rain"
    if any(x in text for x in ("fog", "mist", "haze", "smoke")): return "Low visibility"
    if any(x in text for x in ("clear", "fair")): return "Clear"
    if any(x in text for x in ("cloud", "overcast")): return "Cloudy"
    return "Other"


def _summarize(group: pd.core.groupby.generic.DataFrameGroupBy) -> pd.DataFrame:
    out = group.agg(total_accidents=("ID", "count"), severe_accidents=("is_severe", "sum")).reset_index()
    return add_rate(out)


def build(input_path: Path = RAW_DATA, output_dir: Path = PROCESSED_DIR, chunksize: int = 300_000) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Dataset not found: {input_path}. See README ‘Data setup’.")
    output_dir.mkdir(parents=True, exist_ok=True)
    buckets: dict[str, list[pd.DataFrame]] = defaultdict(list)
    quality = {"rows_read": 0, "invalid_start_time": 0, "duplicate_ids": 0}
    seen: set[str] = set()

    for chunk in pd.read_csv(input_path, usecols=USECOLS, chunksize=chunksize, low_memory=False):
        quality["rows_read"] += len(chunk)
        quality["duplicate_ids"] += int(chunk["ID"].isin(seen).sum() + chunk["ID"].duplicated().sum())
        seen.update(chunk["ID"].dropna().astype(str))
        chunk["Start_Time"] = pd.to_datetime(chunk["Start_Time"], format="mixed", errors="coerce")
        quality["invalid_start_time"] += int(chunk["Start_Time"].isna().sum())
        chunk = chunk.dropna(subset=["ID", "Start_Time", "State", "Severity"])
        chunk["is_severe"] = chunk["Severity"].isin(SEVERE_LEVELS).astype("int8")
        chunk["year"] = chunk["Start_Time"].dt.year
        chunk["month"] = chunk["Start_Time"].dt.month
        chunk["hour"] = chunk["Start_Time"].dt.hour
        chunk["day_of_week"] = chunk["Start_Time"].dt.day_name()
        chunk["is_weekend"] = chunk["day_of_week"].isin(["Saturday", "Sunday"])
        chunk["weather_category"] = chunk["Weather_Condition"].map(weather_category)
        chunk["visibility_band"] = pd.cut(
            chunk["Visibility(mi)"], [-np.inf, 1, 3, 5, 10, np.inf],
            labels=["<1 mile", "1–3 miles", "3–5 miles", "5–10 miles", "10+ miles"],
        ).astype("string").fillna("Unknown")

        buckets["yearly"].append(_summarize(chunk.groupby(["Source", "year"], observed=True)))
        buckets["state"].append(_summarize(chunk.groupby(["Source", "State"], observed=True)))
        buckets["county"].append(_summarize(chunk.groupby(["Source", "State", "County"], observed=True)))
        buckets["temporal"].append(_summarize(chunk.groupby(["hour", "day_of_week", "is_weekend"], observed=True)))
        buckets["weather"].append(_summarize(chunk.groupby(["weather_category", "visibility_band"], observed=True)))

    keys = {
        "yearly": ["Source", "year"], "state": ["Source", "State"],
        "county": ["Source", "State", "County"],
        "temporal": ["hour", "day_of_week", "is_weekend"],
        "weather": ["weather_category", "visibility_band"],
    }
    for name, parts in buckets.items():
        combined = pd.concat(parts).groupby(keys[name], observed=True, as_index=False)[["total_accidents", "severe_accidents"]].sum()
        combined = add_rate(combined)
        low, high = wilson_interval(combined["severe_accidents"], combined["total_accidents"])
        combined["ci_low"], combined["ci_high"] = low, high
        combined.to_parquet(output_dir / f"{name}.parquet", index=False)
    pd.DataFrame([quality]).to_json(output_dir / "quality_report.json", orient="records", indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=RAW_DATA)
    parser.add_argument("--output", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--chunksize", type=int, default=300_000)
    args = parser.parse_args()
    build(args.input, args.output, args.chunksize)


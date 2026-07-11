"""Paste this cell after the cleaning/feature-engineering cells in Kaggle.

It expects the cleaned ``df`` DataFrame from roadpulse-analysis.ipynb and exports
only the compact dashboard marts. The resulting ZIP is normally a few MB.
"""
from pathlib import Path
import shutil

import numpy as np
import pandas as pd

OUT = Path("/kaggle/working/roadpulse_processed")
OUT.mkdir(parents=True, exist_ok=True)

# Recreate canonical fields safely if the notebook has not created them yet.
df["is_severe"] = df["Severity"].isin([3, 4]).astype("int8")
df["year"] = df["Start_Time"].dt.year
df["hour"] = df["Start_Time"].dt.hour
df["day_of_week"] = df["Start_Time"].dt.day_name()
df["is_weekend"] = df["day_of_week"].isin(["Saturday", "Sunday"])

if "weather_category" not in df.columns:
    # The existing notebook uses the capitalized version.
    df["weather_category"] = df["Weather_Category"]

df["visibility_band"] = pd.cut(
    df["Visibility(mi)"],
    [-np.inf, 1, 3, 5, 10, np.inf],
    labels=["<1 mile", "1–3 miles", "3–5 miles", "5–10 miles", "10+ miles"],
).astype("string").fillna("Unknown")


def summarize(keys):
    result = (
        df.groupby(keys, observed=True)
        .agg(
            total_accidents=("ID", "count"),
            severe_accidents=("is_severe", "sum"),
        )
        .reset_index()
    )
    result["severe_rate"] = (
        100 * result["severe_accidents"] / result["total_accidents"]
    ).round(2)

    # Wilson 95% interval for a binomial proportion.
    z = 1.96
    n = result["total_accidents"]
    p = result["severe_accidents"] / n
    denominator = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denominator
    margin = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denominator
    result["ci_low"] = (100 * (centre - margin)).round(2)
    result["ci_high"] = (100 * (centre + margin)).round(2)
    return result


marts = {
    "yearly": summarize(["Source", "year"]),
    "state": summarize(["Source", "State"]),
    "county": summarize(["Source", "State", "County"]),
    "temporal": summarize(["hour", "day_of_week", "is_weekend"]),
    "weather": summarize(["weather_category", "visibility_band"]),
}

for name, table in marts.items():
    table.to_parquet(OUT / f"{name}.parquet", index=False)
    print(f"{name:10s}: {len(table):,} rows")

quality = pd.DataFrame(
    [{
        "rows": len(df),
        "duplicate_ids": int(df["ID"].duplicated().sum()),
        "missing_start_time": int(df["Start_Time"].isna().sum()),
        "min_date": str(df["Start_Time"].min()),
        "max_date": str(df["Start_Time"].max()),
    }]
)
quality.to_json(OUT / "quality_report.json", orient="records", indent=2)

archive = shutil.make_archive(
    "/kaggle/working/roadpulse_processed",
    "zip",
    root_dir=OUT,
)
print(f"\nReady to download: {archive}")

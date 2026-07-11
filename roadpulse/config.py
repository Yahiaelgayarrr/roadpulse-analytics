from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = ROOT / "data" / "raw" / "US_Accidents_March23.csv"
PROCESSED_DIR = ROOT / "data" / "processed"
DEMO_DIR = ROOT / "data" / "demo"

SEVERE_LEVELS = {3, 4}
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


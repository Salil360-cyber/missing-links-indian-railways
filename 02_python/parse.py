import json
import pandas as pd
from pathlib import Path

RAW, OUT = Path("01_data/raw"), Path("01_data/clean")
OUT.mkdir(parents=True, exist_ok=True)

# Stations: GeoJSON points
feats = json.load(open(RAW / "stations.json", encoding="utf-8"))["features"]
stations = pd.DataFrame([{
    **f["properties"],
    "lon": f["geometry"]["coordinates"][0] if f["geometry"] else None,
    "lat": f["geometry"]["coordinates"][1] if f["geometry"] else None,
} for f in feats])

# Trains: keep properties, drop the route geometry (we rebuild routes from stops)
feats = json.load(open(RAW / "trains.json", encoding="utf-8"))["features"]
trains = pd.DataFrame([f["properties"] for f in feats])

# Schedules: one row per train per station (halts + pass-through points)
sched = pd.DataFrame(json.load(open(RAW / "schedules.json", encoding="utf-8")))

# Data quality log -> paste into Excel
rows = []
for name, df in [("stations", stations), ("trains", trains), ("schedules", sched)]:
    for col in df.columns:
        s = df[col]
        missing = s.isna() | s.astype(str).isin(["None", ""])
        rows.append({"table": name, "column": col, "rows": len(df),
                     "missing": int(missing.sum()), "missing_pct": round(missing.mean() * 100, 1)})
pd.DataFrame(rows).to_csv(OUT / "dq_log_raw.csv", index=False)

stations.to_csv(OUT / "stations_raw.csv", index=False)
trains.to_csv(OUT / "trains_raw.csv", index=False)
sched.to_csv(OUT / "schedules_raw.csv", index=False)
print(len(stations), "stations |", len(trains), "trains |", len(sched), "schedule rows")

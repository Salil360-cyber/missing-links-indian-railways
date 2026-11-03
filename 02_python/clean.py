import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree

C = Path("01_data/clean")
stations = pd.read_csv(C / "stations_raw.csv")
trains = pd.read_csv(C / "trains_raw.csv", dtype={"number": str, "return_train": str})
sched = pd.read_csv(C / "schedules_raw.csv", dtype={"train_number": str})

# ---------- 1. Stations: fill missing state/zone from the nearest station that has them ----------
has_xy = stations.lat.notna() & stations.lon.notna()
known = stations[has_xy & stations.state.notna() & stations.zone.notna()]
todo = stations[has_xy & (stations.state.isna() | stations.zone.isna())]
tree = BallTree(np.radians(known[["lat", "lon"]].values), metric="haversine")
dist, idx = tree.query(np.radians(todo[["lat", "lon"]].values), k=1)
dist_km = dist[:, 0] * 6371
near = known.iloc[idx[:, 0]]
ok = dist_km <= 25                       # only trust neighbours within 25 km
stations["geo_imputed"] = 0
for col in ["state", "zone"]:
    fill = pd.Series(np.where(ok, near[col].values, None), index=todo.index)
    mask = stations.loc[todo.index, col].isna() & fill.notna()
    stations.loc[mask[mask].index, col] = fill[mask]
stations.loc[todo.index[ok], "geo_imputed"] = 1
stations["name"] = stations["name"].fillna(stations["code"]).str.title()
print("stations still missing state:", int(stations.state.isna().sum()))

# ---------- 2. Trains: durations, speeds, category lookup from Excel ----------
trains["type"] = trains["type"].fillna("Unknown").replace("", "Unknown")
lookup = pd.read_excel("03_excel/train_type_lookup.xlsx")
trains = trains.merge(lookup, on="type", how="left")
trains["duration_min"] = trains.duration_h * 60 + trains.duration_m
valid = (trains.distance > 0) & (trains.duration_min > 0)
trains["speed_kmph"] = np.where(valid, trains.distance / (trains.duration_min / 60), np.nan)
trains.loc[trains.speed_kmph > 160, "speed_kmph"] = np.nan          # impossible for this network
print("trains with valid speed:", int(trains.speed_kmph.notna().sum()))

# ---------- 3. Stops: order, keep real halts, convert times, add distance ----------
def to_min(t):
    t = t.where(t != "None")
    hm = t.str.split(":", expand=True)
    return pd.to_numeric(hm[0]) * 60 + pd.to_numeric(hm[1])

s = sched.sort_values(["train_number", "id"]).copy()
# pandas reads the source's "None" times as missing (NaN), so test with isna()
s = s[~(s.arrival.isna() & s.departure.isna())]                       # drop rows with no time at all
s = s[s.day.notna()]
# Some trains are listed twice in the source (same stations, days and times under new ids): keep one copy
before = len(s)
s = s.drop_duplicates(["train_number", "station_code", "day", "arrival", "departure"])
print("duplicate schedule rows removed:", before - len(s))
# Most rows are TIMING POINTS the train passes (arrival = departure), not halts.
# A real halt: origin (no arrival), destination (no departure) or a stop of at least 1 minute.
origin_or_dest = s.arrival.isna() | s.departure.isna()
arr, dep = to_min(s.arrival), to_min(s.departure)
arr, dep = arr.fillna(dep), dep.fillna(arr)                          # origin has no arrival, destination no departure
offset = (s.day - 1) * 1440
s["arr_min"], s["dep_min"] = arr + offset, dep + offset
s.loc[s.dep_min < s.arr_min, "dep_min"] += 1440                      # halt crossing midnight
s["halt_min"] = s.dep_min - s.arr_min
s["is_halt"] = (origin_or_dest | (s.halt_min > 0)).astype(int)
s.loc[s.halt_min > 180, "halt_min"] = np.nan                         # >3 h halt = data error
s["seq"] = s.groupby("train_number").cumcount() + 1

s = s.merge(stations[["code", "lat", "lon"]], left_on="station_code", right_on="code", how="left")
def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))
# Stations without coordinates: carry the last known position forward so the distance across them is not lost
s[["lat_f", "lon_f"]] = s.groupby("train_number")[["lat", "lon"]].ffill()
g = s.groupby("train_number")
s["seg_km"] = haversine(g.lat_f.shift(), g.lon_f.shift(), s.lat_f, s.lon_f).fillna(0)
s["cum_km"] = s.groupby("train_number").seg_km.cumsum().round(1)

# Flag trains whose times go backwards (day-number errors in the source)
back = s.groupby("train_number").arr_min.diff() < 0
bad = s.loc[back, "train_number"].unique()
s["time_ok"] = (~s.train_number.isin(bad)).astype(int)
print("trains with backward times (excluded from timing analysis):", len(bad))

stops = s[["train_number", "seq", "station_code", "arr_min", "dep_min", "halt_min", "seg_km", "cum_km", "time_ok", "is_halt"]]
stations.drop(columns=["address"]).to_csv(C / "stations.csv", index=False)
for col in ["duration_h", "duration_m", "distance", "duration_min"]:     # whole numbers, so PostgreSQL INT columns load
    trains[col] = trains[col].round().astype("Int64")
trains.drop(columns=["classes"]).to_csv(C / "trains.csv", index=False)
stops.round(2).to_csv(C / "stops.csv", index=False)
print(len(stops), "timing points across", stops.train_number.nunique(), "trains, of which", int(stops.is_halt.sum()), "are real halts")

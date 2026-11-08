"""Builds docs/index.html, the interactive corridor explorer, from the cleaned tables.
Run from the repo root after city_pairs.py:  python 02_python/build_explorer.py"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

C = Path("01_data/clean")
p = pd.read_csv(C / "city_pairs.csv")
# the page recomputes the score from these three parts; check that default weights give the stored score
s = (0.5 * p.demand_idx + 0.3 * p.speed_gap + 0.2 * p.freq_gap).round(3)
m = p.track_link == 1
assert (s[m] - p.score[m]).abs().max() == 0
assert len(p) == 272 and int(((p.missing_link == 1) & m).sum()) == 24

cities = {}
for i in (1, 2):
    for r in p[[f"city_{i}", f"state_{i}", f"population_{i}", f"lat_{i}", f"lon_{i}"]].itertuples(index=False):
        cities[r[0]] = [r[1], int(r[2]), round(r[3], 3), round(r[4], 3)]
pairs = [[r.city_1, r.city_2, int(r.air_km), int(r.direct_services),
          None if pd.isna(r.fastest_min) else int(r.fastest_min),
          None if pd.isna(r.eff_speed_kmph) else round(float(r.eff_speed_kmph), 1),
          int(r.track_link), float(r.demand_idx), float(r.speed_gap), float(r.freq_gap)] for r in p.itertuples()]
st = pd.read_csv(C / "stations.csv").dropna(subset=["lat", "lon"])
st = st[(st.lat.between(6, 37.5)) & (st.lon.between(68, 98))]
dots = sorted({(round(a, 1), round(b, 1)) for a, b in zip(st.lat, st.lon)})

data = {"cities": cities, "pairs": pairs, "dots": [c for d in dots for c in d]}
page = Path("docs/template.html").read_text().replace("__DATA__", json.dumps(data, separators=(",", ":")))
Path("docs/index.html").write_text(page)
print(f"wrote docs/index.html ({len(page)//1024} KB): {len(cities)} cities, {len(pairs)} pairs, {len(dots)} backdrop dots")

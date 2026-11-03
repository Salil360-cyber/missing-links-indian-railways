"""Missing Links: report charts. Run after city_pairs.py, from the project root.
Saves PNGs to 07_findings/charts/."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Patch

C = Path("01_data/clean")
OUT = Path("07_findings/charts"); OUT.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, AQUA, YELLOW, GREY, LIGHT = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#9a9a95", "#d6d5cf"
INK, INK2, BG = "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#c9c8c3", "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK, "figure.facecolor": BG, "axes.facecolor": BG})
NOTE = "Source: Datameet Indian Railways timetable (around 2016) · Census 2011 cities"

def save(fig, name):
    fig.tight_layout(); fig.savefig(OUT / name, dpi=160, bbox_inches="tight"); plt.close(fig)

stations = pd.read_csv(C / "stations.csv")
trains = pd.read_csv(C / "trains.csv", dtype={"number": str})
stops = pd.read_csv(C / "stops.csv", dtype={"train_number": str})
hubs = pd.read_csv(C / "hubs.csv")
edges = pd.read_csv(C / "edges.csv")
pairs = pd.read_csv(C / "city_pairs.csv")

# ---------- 1. Map: rail network of real halts + top missing links ----------
xy = stations.set_index("code")[["lon", "lat"]]
e = edges.join(xy, on="a").join(xy.add_suffix("_b"), on="b").dropna()
fig, ax = plt.subplots(figsize=(8, 8.6))
ax.plot(np.column_stack([e.lon, e.lon_b, np.full(len(e), np.nan)]).ravel(),
        np.column_stack([e.lat, e.lat_b, np.full(len(e), np.nan)]).ravel(), color=LIGHT, lw=0.5, zorder=1)
gaps = pairs[(pairs.missing_link == 1) & (pairs.track_link == 1)].head(10)
for _, r in gaps.iterrows():
    ax.plot([r.lon_1, r.lon_2], [r.lat_1, r.lat_2], color=ORANGE, lw=2, zorder=3, solid_capstyle="round")
cities = pd.concat([gaps[["city_1", "lon_1", "lat_1"]].set_axis(["city", "lon", "lat"], axis=1),
                    gaps[["city_2", "lon_2", "lat_2"]].set_axis(["city", "lon", "lat"], axis=1)]).drop_duplicates("city")
ax.scatter(cities.lon, cities.lat, s=46, color=ORANGE, edgecolor=BG, linewidth=2, zorder=4)
LAB = {"Greater Hyderabad": "Hyderabad"}
for _, r in cities.iterrows():
    ax.annotate(LAB.get(r.city, r.city), (r.lon, r.lat), xytext=(5, 3), textcoords="offset points",
                fontsize=8.5, color=INK, zorder=5)
ax.set_aspect(1.05); ax.axis("off")
ax.set_title("10 biggest 'missing links': track connects these cities, but no direct train runs",
             loc="left", fontsize=11, color=INK)
ax.plot([], [], color=LIGHT, lw=2, label="Rail links between halts"); ax.plot([], [], color=ORANGE, lw=2, label="Missing direct link")
ax.legend(frameon=False, loc="lower left")
fig.text(0.01, 0.01, NOTE + " · cities of 10 lakh+, 200-800 km apart", fontsize=8, color=INK2)
save(fig, "01_missing_links_map.png")

# ---------- 2. Top opportunity corridors ----------
top = pairs.dropna(subset=["score"]).head(12).iloc[::-1]
lab = (top.city_1.replace(LAB) + " – " + top.city_2.replace(LAB))
fig, ax = plt.subplots(figsize=(8, 5))
cols = [ORANGE if m else BLUE for m in top.missing_link]
ax.barh(lab, top.score, color=cols, height=0.65)
for i, (v, n) in enumerate(zip(top.score, top.direct_services)):
    ax.text(v + 0.006, i, f"{v:.2f}" + ("" if n == 0 else f"  ({n} trains)"), va="center", fontsize=8.5, color=INK2)
ax.set_xlim(0, 0.9); ax.set_xlabel("Opportunity score (0.5 demand + 0.3 speed gap + 0.2 frequency gap)")
handles = [Patch(color=ORANGE, label="No direct train")] + ([Patch(color=BLUE, label="Has direct trains")] if top.direct_services.gt(0).any() else [])
ax.legend(handles=handles, frameon=False, loc="lower right")
ax.set_title("Top corridor opportunities", loc="left", fontsize=11, color=INK)
fig.text(0.01, -0.02, NOTE + " · pairs without a track link (Srinagar in 2016) not ranked", fontsize=8, color=INK2)
save(fig, "02_top_corridors.png")

# ---------- 3. Median speed by category ----------
order = ["Premium", "Mail/Express", "Suburban/Local", "Passenger"]
sp = trains[trains.category.isin(order)].groupby("category").speed_kmph.agg(["median", "count"]).loc[order]
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.bar(sp.index, sp["median"], color=BLUE, width=0.55)
for i, (v, n) in enumerate(zip(sp["median"], sp["count"])):
    ax.text(i, v + 1.2, f"{v:.1f} km/h\n({n:,} trains)", ha="center", fontsize=8.5, color=INK2)
ax.set_ylim(0, 88); ax.set_ylabel("Median timetable speed (km/h)")
ax.set_title("Premium trains run about 40% faster than Mail/Express", loc="left", fontsize=11, color=INK)
fig.text(0.01, -0.03, NOTE + " · Premium = Rajdhani, Shatabdi, Duronto", fontsize=8, color=INK2)
save(fig, "03_speed_by_category.png")

# ---------- 4. Halts per 100 km vs speed ----------
h = (stops.groupby("train_number").agg(halts=("is_halt", "sum"), km=("cum_km", "max")).reset_index()
          .merge(trains, left_on="train_number", right_on="number"))
h = h[(h.km > 50) & h.speed_kmph.notna() & h.category.isin(order)]
h["hp100"] = 100 * h.halts / h.km
rho = h.hp100.corr(h.speed_kmph, method="spearman")
fig, ax = plt.subplots(figsize=(8, 4.8))
for cat, colr in zip(order, [BLUE, ORANGE, AQUA, YELLOW]):
    d = h[h.category == cat]
    ax.scatter(d.hp100, d.speed_kmph, s=9, color=colr, alpha=0.55, linewidth=0, label=f"{cat} ({len(d):,})")
ax.set_xscale("log"); ax.set_xlim(0.3, 60)
ax.set_xticks([0.5, 1, 2, 5, 10, 20, 50], ["0.5", "1", "2", "5", "10", "20", "50"])
ax.set_xlabel("Halts per 100 km (log scale)"); ax.set_ylabel("Timetable speed (km/h)")
leg = ax.legend(frameon=False, loc="upper right", markerscale=2.5)
for t in leg.legend_handles: t.set_alpha(1)
ax.set_title(f"More halts, slower train (Spearman ρ = {rho:.2f}, {len(h):,} trains)", loc="left", fontsize=11, color=INK)
fig.text(0.01, -0.02, NOTE + " · real halts only, trains over 50 km", fontsize=8, color=INK2)
save(fig, "04_halts_vs_speed.png")

# ---------- 5. Busiest vs most critical junctions ----------
busy20 = set(hubs.nlargest(20, "trains_halting").station_code)
crit = hubs.nlargest(20, "betweenness").iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 5.6))
cols = [BLUE if c in busy20 else ORANGE for c in crit.station_code]
ax.barh(crit.name, crit.betweenness, color=cols, height=0.65)
for i, (v, n) in enumerate(zip(crit.betweenness, crit.trains_halting)):
    ax.text(v + 0.004, i, f"{v:.2f}  ·  {n} trains halt", va="center", fontsize=8, color=INK2)
ax.set_xlim(0, 0.52); ax.set_xlabel("Betweenness centrality (share of shortest routes passing through)")
ax.legend(handles=[Patch(color=ORANGE, label="Critical but NOT in the 20 busiest"), Patch(color=BLUE, label="Also in the 20 busiest")],
          frameon=False, loc="lower right")
n_hidden = sum(c not in busy20 for c in crit.station_code)
ax.set_title(f"{n_hidden} of the 20 most critical junctions are not among the busiest", loc="left", fontsize=11, color=INK)
fig.text(0.01, -0.02, NOTE + " · betweenness sampled on 800 stations, seed 42", fontsize=8, color=INK2)
save(fig, "05_critical_vs_busy.png")

# ---------- 6. Data-quality catch: timing points vs real halts ----------
ex = {"12301": "Howrah–Delhi Rajdhani", "12951": "Mumbai–Delhi Rajdhani", "12002": "Bhopal Shatabdi",
      "12627": "Karnataka Express", "12859": "Gitanjali Express"}
d = (stops[stops.train_number.isin(ex)].groupby("train_number")
          .agg(rows=("seq", "size"), halts=("is_halt", "sum")).reindex(list(ex)).dropna())
d.index = [ex[i] for i in d.index]; d = d.iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 3.6))
y = np.arange(len(d))
ax.barh(y + 0.19, d.rows, height=0.34, color=GREY, label="Rows in the timetable file")
ax.barh(y - 0.19, d.halts, height=0.34, color=BLUE, label="Real halts (origin, destination, 1+ min stop)")
for yi, r, s in zip(y, d.rows, d.halts):
    ax.text(r + 3, yi + 0.19, f"{int(r)}", va="center", fontsize=8.5, color=INK2)
    ax.text(s + 3, yi - 0.19, f"{int(s)}", va="center", fontsize=8.5, color=INK2)
ax.set_yticks(y, d.index); ax.set_xlim(0, 310)
ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=9)
share = 1 - stops.is_halt.mean()
ax.set_title(f"Data-quality catch: {share:.0%} of timetable rows are pass-through timing points, not halts",
             loc="left", fontsize=11, color=INK, pad=26)
fig.text(0.01, -0.03, NOTE, fontsize=8, color=INK2)
save(fig, "06_timing_points_vs_halts.png")
print("Charts saved to", OUT)

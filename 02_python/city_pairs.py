import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree

C = Path("01_data/clean")
stations = pd.read_csv(C / "stations.csv")
stops = pd.read_csv(C / "stops.csv", dtype={"train_number": str})
cities = pd.read_csv(C / "cities.csv")          # city, state, population, lat, lon (Step 6.1)

MIN_POP, RADIUS_KM = 1_000_000, 15
cities = cities[cities.population >= MIN_POP].reset_index(drop=True)
# Satellite cities share their metro's stations and demand: merge them into one metro area
METRO = {"Faridabad": "Delhi", "Thane": "Greater Mumbai", "Navi Mumbai": "Greater Mumbai",
         "Vasai Virar City": "Greater Mumbai", "Pimpri Chinchwad": "Pune", "Haora": "Kolkata"}
cities["city"] = cities.city.replace(METRO)
cities = (cities.groupby("city")
                .apply(lambda d: pd.Series({"state": d.state.iloc[0], "population": d.population.sum(),
                                            "lat": d.loc[d.population.idxmax(), "lat"],
                                            "lon": d.loc[d.population.idxmax(), "lon"]}), include_groups=False)
                .reset_index())
cities_all = pd.read_csv(C / "cities.csv")
cities_all["city"] = cities_all.city.replace(METRO)
centres = cities_all[cities_all.population >= MIN_POP][["city", "lat", "lon"]]   # every centre, so a metro keeps all its stations

# 1) Map every station within RADIUS_KM of a city centre to that city
st = stations.dropna(subset=["lat", "lon"]).reset_index(drop=True)
tree = BallTree(np.radians(st[["lat", "lon"]].values), metric="haversine")
centres = centres.reset_index(drop=True)
idx = tree.query_radius(np.radians(centres[["lat", "lon"]].values), r=RADIUS_KM / 6371)
city_station = pd.DataFrame([{"city": centres.city[i], "station_code": st.code[j]}
                             for i, js in enumerate(idx) for j in js]).drop_duplicates()
city_station.to_csv(C / "city_station.csv", index=False)
print(city_station.groupby("city").size().sort_values(ascending=False).head(10))

# 2) Every direct trip between two different cities on the same train, using real halts only
#    (a train that only passes through a city does not serve it)
s = stops[stops.is_halt == 1].merge(city_station, on="station_code")
# keep first halt of a train in each city as boarding, and the first halt in the other city as alighting
first = s.sort_values("seq").groupby(["train_number", "city"], as_index=False).first()
trips = first.merge(first, on="train_number", suffixes=("_a", "_b"))
trips = trips[trips.seq_a < trips.seq_b]
trips["minutes"] = trips.arr_min_b - trips.dep_min_a
trips["km"] = trips.cum_km_b - trips.cum_km_a
trips["time_ok"] = trips.time_ok_a
trips["city_1"] = trips[["city_a", "city_b"]].min(axis=1)
trips["city_2"] = trips[["city_a", "city_b"]].max(axis=1)
trips.to_csv(C / "pair_trips.csv", index=False)

# Every train counts as a direct service; only trains with clean times count for the fastest time
timed = trips[(trips.time_ok == 1) & (trips.minutes > 0)]
served = (trips.groupby(["city_1", "city_2"]).train_number.nunique().rename("direct_services").reset_index()
               .merge(timed.groupby(["city_1", "city_2"]).minutes.min().rename("fastest_min").reset_index(),
                      on=["city_1", "city_2"], how="left"))
fastest_km = timed.loc[timed.groupby(["city_1", "city_2"]).minutes.idxmin(), ["city_1", "city_2", "km"]]
served = served.merge(fastest_km, on=["city_1", "city_2"], how="left")
served["eff_speed_kmph"] = (served.km / (served.fastest_min / 60)).round(1)

# 3) All city pairs 200-800 km apart (semi-high-speed sweet spot), served or not
def hav(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return 6371 * 2 * np.arcsin(np.sqrt(a))
cp = cities.merge(cities, how="cross", suffixes=("_1", "_2"))
cp = cp[cp.city_1 < cp.city_2]
cp["air_km"] = hav(cp.lat_1, cp.lon_1, cp.lat_2, cp.lon_2).round(0)
cp = cp[cp.air_km.between(200, 800)]
pairs = cp.merge(served, on=["city_1", "city_2"], how="left")
pairs["direct_services"] = pairs.direct_services.fillna(0).astype(int)
pairs["missing_link"] = (pairs.direct_services == 0).astype(int)

# A pair can only get a direct train if the two cities are on the same connected rail network
# (e.g. Srinagar's line was not linked to the rest of India in this ~2016 snapshot)
import networkx as nx
G = nx.from_pandas_edgelist(pd.read_csv(C / "edges.csv"), "a", "b")
comp = {n: i for i, c in enumerate(nx.connected_components(G)) for n in c}
city_comp = (city_station.assign(comp=city_station.station_code.map(comp)).dropna()
             .groupby("city").comp.agg(lambda x: set(x)))
pairs["track_link"] = [int(bool(city_comp.get(a, set()) & city_comp.get(b, set())))
                       for a, b in zip(pairs.city_1, pairs.city_2)]
print("pairs with no track link (not a timetable gap):",
      pairs.loc[pairs.track_link == 0, ["city_1", "city_2"]].apply(" - ".join, axis=1).tolist())

# 4) Opportunity score (weights are re-computed in Excel for what-if)
TARGET_KMPH = 90
gravity = np.log(pairs.population_1 * pairs.population_2 / pairs.air_km ** 2)
pairs["demand_idx"] = ((gravity - gravity.min()) / (gravity.max() - gravity.min())).round(3)
pairs["speed_gap"] = (1 - pairs.eff_speed_kmph / TARGET_KMPH).clip(0, 1).fillna(1).round(3)
pairs["freq_gap"] = (1 / (1 + pairs.direct_services / 2)).round(3)   # /2 = per direction
pairs["hours_saved_at_target"] = ((pairs.fastest_min / 60) - pairs.km / TARGET_KMPH).clip(lower=0).round(2)
pairs["score"] = (0.5 * pairs.demand_idx + 0.3 * pairs.speed_gap + 0.2 * pairs.freq_gap).round(3)
pairs.loc[pairs.track_link == 0, "score"] = np.nan                     # needs new track, not a new train: not ranked
pairs = pairs.sort_values("score", ascending=False)
pairs.to_csv(C / "city_pairs.csv", index=False)
print(len(pairs), "city pairs 200-800 km;", int(((pairs.missing_link == 1) & (pairs.track_link == 1)).sum()),
      "have no direct train although the track connects them")
print(pairs.head(15)[
    ["city_1", "city_2", "air_km", "direct_services", "fastest_min", "eff_speed_kmph", "score"]].to_string(index=False))

import networkx as nx
import pandas as pd
from pathlib import Path

C = Path("01_data/clean")
stops = pd.read_csv(C / "stops.csv", dtype={"train_number": str})
stops = stops[stops.is_halt == 1].copy()                 # passenger network: only stations where trains stop
stations = pd.read_csv(C / "stations.csv")

# Edge = two consecutive halts of the same train; weight = number of trains using it
stops["next_code"] = stops.groupby("train_number").station_code.shift(-1)
edges = (stops.dropna(subset=["next_code"])
              .assign(a=lambda d: d[["station_code", "next_code"]].min(axis=1),
                      b=lambda d: d[["station_code", "next_code"]].max(axis=1))
              .groupby(["a", "b"]).train_number.nunique().reset_index(name="trains"))
G = nx.Graph()
G.add_weighted_edges_from(edges[["a", "b", "trains"]].itertuples(index=False), weight="trains")
print(G.number_of_nodes(), "stations,", G.number_of_edges(), "links,",
      nx.number_connected_components(G), "connected components")

deg = dict(G.degree())                                   # distinct neighbouring stations
trains_at = stops.groupby("station_code").train_number.nunique()
btw = nx.betweenness_centrality(G, k=800, seed=42)       # sampled: exact is slow on 8k nodes

hubs = (pd.DataFrame({"station_code": list(G.nodes)})
          .assign(neighbours=lambda d: d.station_code.map(deg),
                  trains_halting=lambda d: d.station_code.map(trains_at),
                  betweenness=lambda d: d.station_code.map(btw).round(5))
          .merge(stations[["code", "name", "state", "zone", "lat", "lon"]],
                 left_on="station_code", right_on="code", how="left").drop(columns="code"))
hubs["rank_busy"] = hubs.trains_halting.rank(ascending=False, method="min")
hubs["rank_critical"] = hubs.betweenness.rank(ascending=False, method="min")
hubs.sort_values("betweenness", ascending=False).to_csv(C / "hubs.csv", index=False)
edges.to_csv(C / "edges.csv", index=False)
print(hubs.sort_values("betweenness", ascending=False).head(12)[
    ["station_code", "name", "trains_halting", "neighbours", "betweenness"]].to_string(index=False))

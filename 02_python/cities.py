import pandas as pd

raw = pd.read_csv("01_data/raw/cities_r2.csv")
print(raw.columns.tolist())                      # confirm names before running the rest
cities = pd.DataFrame({
    "city":       raw["name_of_city"].str.strip().str.title(),
    "state":      raw["state_name"].str.strip().str.title(),
    "population": raw["population_total"],
})
latlon = raw["location"].str.split(",", expand=True).astype(float)   # "lat,lon" text
cities["lat"], cities["lon"] = latlon[0], latlon[1]
cities.to_csv("01_data/clean/cities.csv", index=False)
print(len(cities), "cities;", (cities.population >= 1_000_000).sum(), "with 10 lakh+")

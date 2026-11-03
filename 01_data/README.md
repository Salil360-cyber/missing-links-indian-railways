# Data

## Source
[Datameet Indian Railways](https://github.com/datameet/railways), collected around 2016 by Sanjay Bhangar and Sajjad Anwar (Datameet community).

## Download the raw files
From the project root:

```bash
mkdir -p 01_data/raw && cd 01_data/raw
curl -LO https://raw.githubusercontent.com/datameet/railways/master/stations.json
curl -LO https://raw.githubusercontent.com/datameet/railways/master/trains.json
curl -LO https://raw.githubusercontent.com/datameet/railways/master/schedules.json
```

Raw files (~95 MB) are not committed.

## Clean files (in `clean/`)
| File | Made by | Rows |
|---|---|---|
| dq_log_raw.csv | parse.py | 36 (one per column) |
| stations_raw.csv, trains_raw.csv | parse.py | 8,990 / 5,208 |
| stations.csv | clean.py | 8,990 |
| trains.csv | clean.py | 5,208 |
| stops.csv | clean.py | 394,129 timing points, of which 103,954 are real halts (`is_halt = 1`) |
| hubs.csv | network.py | 7,388 |
| edges.csv | network.py | 13,153 |
| cities.csv | cities.py | 493 |
| city_station.csv, city_pairs.csv | city_pairs.py | 272 city pairs |

`schedules_raw.csv` (32 MB) is not committed; `python 02_python/parse.py` recreates it.

Also needed in `raw/`: `cities_r2.csv`, Census 2011 city populations (Kaggle dataset "Top 500 Indian Cities"), for `cities.py` and `city_pairs.py`.

## Halts vs timing points
In the schedules file about three quarters of the rows are **timing points**: stations the train passes without stopping (arrival = departure). `clean.py` keeps them for distance, but marks `is_halt = 1` only for the origin, the destination and stops of 1 minute or more. Station counts, the network and city-pair services use real halts only. Example: Rajdhani 12301 has 218 rows but 8 real halts (HWH, DHN, PNME, GAYA, MGS, ALD, CNB, NDLS).

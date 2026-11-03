CREATE TABLE stations (
  state TEXT, code TEXT PRIMARY KEY, name TEXT, zone TEXT,
  lon NUMERIC, lat NUMERIC, geo_imputed SMALLINT
);
CREATE TABLE trains (
  third_ac SMALLINT, arrival TEXT, from_station_code TEXT, name TEXT, zone TEXT,
  chair_car SMALLINT, first_class SMALLINT, duration_m INT, sleeper SMALLINT,
  from_station_name TEXT, number TEXT PRIMARY KEY, departure TEXT, return_train TEXT,
  to_station_code TEXT, second_ac SMALLINT, to_station_name TEXT, duration_h INT,
  type TEXT, first_ac SMALLINT, distance INT, type_name TEXT, category TEXT,
  duration_min INT, speed_kmph NUMERIC
);
CREATE TABLE stops (
  train_number TEXT, seq INT, station_code TEXT, arr_min NUMERIC, dep_min NUMERIC,
  halt_min NUMERIC, seg_km NUMERIC, cum_km NUMERIC, time_ok SMALLINT,
  is_halt SMALLINT,   -- 1 = train stops here (origin, destination or halt of 1+ min); 0 = timing point it passes
  PRIMARY KEY (train_number, seq)
);
-- Column order above must match the CSV header order. Check with: head -1 trains.csv
\copy stations FROM '01_data/clean/stations.csv' CSV HEADER;
\copy trains   FROM '01_data/clean/trains.csv'   CSV HEADER;
\copy stops    FROM '01_data/clean/stops.csv'    CSV HEADER;
CREATE INDEX ON stops (station_code);

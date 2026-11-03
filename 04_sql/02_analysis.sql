-- Q1. Busiest stations: distinct trains halting
SELECT s.code, s.name, s.state, s.zone, COUNT(DISTINCT st.train_number) AS trains_halting
FROM stops st JOIN stations s ON s.code = st.station_code
WHERE st.is_halt = 1                      -- only real halts, not timing points the train passes
GROUP BY s.code, s.name, s.state, s.zone
ORDER BY trains_halting DESC LIMIT 20;

-- Q2. Zone scorecard (zone that operates the train)
SELECT zone,
       COUNT(*)                                                    AS trains,
       ROUND(AVG(distance))                                        AS avg_km,
       ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY speed_kmph)::NUMERIC, 1) AS median_kmph,
       ROUND(100.0 * AVG((category = 'Premium')::INT), 1)          AS premium_pct
FROM trains WHERE zone IS NOT NULL AND zone <> ''
GROUP BY zone HAVING COUNT(*) >= 30
ORDER BY median_kmph DESC;

-- Q3. Speed distribution by train type
SELECT category, type_name, COUNT(*) AS trains,
       ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY speed_kmph)::NUMERIC, 1) AS p25_kmph,
       ROUND(PERCENTILE_CONT(0.5)  WITHIN GROUP (ORDER BY speed_kmph)::NUMERIC, 1) AS median_kmph,
       ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY speed_kmph)::NUMERIC, 1) AS p75_kmph
FROM trains WHERE speed_kmph IS NOT NULL
GROUP BY category, type_name
ORDER BY median_kmph DESC;

-- Q4. Slowest long-distance "fast" trains: superfast/express running below 45 km/h over 500+ km
SELECT number, name, type_name, from_station_name, to_station_name, distance,
       ROUND(speed_kmph, 1) AS kmph
FROM trains
WHERE category = 'Mail/Express' AND distance >= 500 AND speed_kmph < 45
ORDER BY speed_kmph LIMIT 25;

-- Q5. Stops per 100 km: which categories stop the most?
WITH t AS (
  SELECT train_number, SUM(is_halt) AS halts, MAX(cum_km) AS km
  FROM stops GROUP BY train_number
)
SELECT tr.category, ROUND(AVG(100.0 * t.halts / NULLIF(t.km, 0)), 1) AS halts_per_100km,
       ROUND(AVG(tr.speed_kmph), 1) AS avg_kmph
FROM t JOIN trains tr ON tr.number = t.train_number
WHERE t.km > 50
GROUP BY tr.category ORDER BY halts_per_100km DESC;

-- Q6. State coverage: stations, and trains per station (service intensity)
WITH per_station AS (
  SELECT station_code, COUNT(DISTINCT train_number) AS trains
  FROM stops WHERE is_halt = 1 GROUP BY station_code
)
SELECT s.state, COUNT(*) AS stations_served,
       ROUND(AVG(p.trains), 1) AS avg_trains_per_station,
       RANK() OVER (ORDER BY AVG(p.trains) DESC) AS intensity_rank
FROM per_station p JOIN stations s ON s.code = p.station_code
WHERE s.state IS NOT NULL
GROUP BY s.state HAVING COUNT(*) >= 50
ORDER BY intensity_rank;

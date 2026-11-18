-- Upsert of daily weather history (rerunnable without duplicates)
INSERT INTO weather.weather_daily
    (commune_code, date, precipitation_sum, temperature_2m_max)
VALUES (%s, %s, %s, %s)
ON CONFLICT (commune_code, date) DO UPDATE
SET precipitation_sum  = EXCLUDED.precipitation_sum,
    temperature_2m_max = EXCLUDED.temperature_2m_max,
    ingested_at        = now();
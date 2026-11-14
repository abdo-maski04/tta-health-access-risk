create schema if not exists weather;

-- Historique météo brut (téléchargé une seule fois)
CREATE TABLE IF NOT EXISTS weather.weather_daily (
    commune_code        TEXT             NOT NULL,
    date                DATE             NOT NULL,
    precipitation_sum   DOUBLE PRECISION,
    temperature_2m_max  DOUBLE PRECISION,
    ingested_at         TIMESTAMPTZ      NOT NULL DEFAULT now(),
    PRIMARY KEY (commune_code, date)
);

CREATE TABLE IF NOT EXISTS weather.thresholds (
    commune_code TEXT     NOT NULL,
    month        SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    rain_p65 DOUBLE PRECISION, rain_p80 DOUBLE PRECISION, rain_p90 DOUBLE PRECISION,
    heat_p65 DOUBLE PRECISION, heat_p80 DOUBLE PRECISION, heat_p90 DOUBLE PRECISION,
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (commune_code, month)
);
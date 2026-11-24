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

CREATE TABLE IF NOT EXISTS weather.forecast_daily (
    commune_code        TEXT NOT NULL,
    forecast_issued_on  DATE NOT NULL,
    target_date         DATE NOT NULL,
    precip_mm           REAL,
    tmax_c              REAL,
    ingested_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (commune_code, forecast_issued_on, target_date)
);

-- Danger météo quotidien par commune (le score final s'ajoutera plus tard)
CREATE TABLE IF NOT EXISTS weather.risk_daily (
    commune_code        TEXT     NOT NULL,
    forecast_issued_on  DATE     NOT NULL,
    target_date         DATE     NOT NULL,
    precip_mm           REAL,
    tmax_c              REAL,
    rain_level          SMALLINT NOT NULL CHECK (rain_level BETWEEN 0 AND 3),
    heat_level          SMALLINT NOT NULL CHECK (heat_level BETWEEN 0 AND 3),
    danger              SMALLINT NOT NULL CHECK (danger BETWEEN 0 AND 3),
    dominant            TEXT     NOT NULL CHECK (dominant IN ('rain', 'heat', 'both', 'none')),
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (commune_code, forecast_issued_on, target_date)
);
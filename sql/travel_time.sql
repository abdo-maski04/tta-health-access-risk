-- Table accessibility.travel_time : les 146 temps de trajet vers l'hopital retenu.
--
-- Source : data/processed/travel_time_TTA_2024.csv (v2, D-019) : 146 lignes,
--          1 par commune, methode ORS_DRIVING_CAR.
-- Usage  : docker exec -i postgres_tta_risk psql -U user -d tta_risk < sql\travel_time.sql
--          (ou, plus simple, python -m scripts.load_travel_time qui execute ce fichier)
--
-- Idempotent : peut etre relance sans erreur.

CREATE SCHEMA IF NOT EXISTS accessibility;

CREATE TABLE IF NOT EXISTS accessibility.travel_time (
    commune_code      TEXT PRIMARY KEY,
    name_fr           TEXT             NOT NULL,
    province          TEXT             NOT NULL,
    milieu            TEXT             NOT NULL CHECK (milieu IN ('Urbain', 'Rural', 'Mixte')),
    start_lat         DOUBLE PRECISION NOT NULL,
    start_lon         DOUBLE PRECISION NOT NULL,
    hospital_osm_type TEXT,
    hospital_osm_id   TEXT,
    hospital_name     TEXT,
    hospital_lat      DOUBLE PRECISION,
    hospital_lon      DOUBLE PRECISION,
    distance_km       DOUBLE PRECISION CHECK (distance_km >= 0),
    temps_min         DOUBLE PRECISION NOT NULL CHECK (temps_min >= 0 AND temps_min <= 600),
    classe_trajet     SMALLINT         NOT NULL CHECK (classe_trajet BETWEEN 1 AND 3),
    methode           TEXT,
    loaded_at         TIMESTAMPTZ      NOT NULL DEFAULT now()
);

COMMENT ON TABLE accessibility.travel_time IS
    'Temps de trajet routier de chaque commune vers l''hopital retenu (146 lignes, D-015 et D-019).';
COMMENT ON COLUMN accessibility.travel_time.temps_min IS
    'Duree du trajet en minutes (ORS_DRIVING_CAR).';
COMMENT ON COLUMN accessibility.travel_time.classe_trajet IS
    '1 = moins de 15 min, 2 = de 15 a 45 min, 3 = plus de 45 min (D-015).';

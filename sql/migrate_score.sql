-- Migration : ajoute les 4 colonnes du score a weather.risk_daily (D-018).
--
-- A lancer UNE SEULE FOIS sur une base existante, depuis la racine du depot :
--   docker exec -i postgres_tta_risk psql -U user -d tta_risk < sql\migrate_score.sql
--
-- Une installation neuve n'en a pas besoin : sql/init.sql contient deja les colonnes.

ALTER TABLE weather.risk_daily
    ADD COLUMN IF NOT EXISTS classe_trajet SMALLINT,
    ADD COLUMN IF NOT EXISTS score         SMALLINT,
    ADD COLUMN IF NOT EXISTS niveau        TEXT,
    ADD COLUMN IF NOT EXISTS raison        TEXT;

ALTER TABLE weather.risk_daily
    DROP CONSTRAINT IF EXISTS risk_daily_classe_trajet_check,
    ADD  CONSTRAINT risk_daily_classe_trajet_check CHECK (classe_trajet BETWEEN 1 AND 3),
    DROP CONSTRAINT IF EXISTS risk_daily_score_check,
    ADD  CONSTRAINT risk_daily_score_check CHECK (score IN (0, 1, 2, 3, 4, 6, 9)),
    DROP CONSTRAINT IF EXISTS risk_daily_niveau_check,
    ADD  CONSTRAINT risk_daily_niveau_check CHECK (niveau IN ('vert', 'jaune', 'orange', 'rouge')),
    DROP CONSTRAINT IF EXISTS risk_daily_raison_check,
    ADD  CONSTRAINT risk_daily_raison_check CHECK (raison IN ('pluie', 'chaleur', 'eloignement'));

\echo Migration terminee. Verifie avec : \d weather.risk_daily

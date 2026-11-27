# data_dictionary.md — Dictionnaire des variables

> Tenu par le **Membre A**. Version 1.1 — 2026-11-25 (alignée sur le code de `main`).
> Règle : chaque variable a une **source**, une **unité**, une **période** et un **statut de qualité**.
>
> **Ce dictionnaire décrit la version réellement livrée dans `main`.** Toute colonne listée ici existe dans le fichier ; toute colonne du fichier est listée ici. Contrôles automatiques : `tests/test_referentiel.py` et `tests/test_health_facilities.py`.

---

## Sommaire

| § | Jeu de données | Fichier | Lignes × colonnes |
|---|---|---|---|
| 1 | Référentiel communes | `data/processed/communes_TTA_2024.csv` | 146 × 25 |
| 2 | Contours communaux | `data/processed/communes_TTA.geojson` | 146 × 8 |
| 3 | Établissements de santé | `data/processed/health_facilities_TTA.csv` | 892 × 13 |
| 4 | Temps de trajet et zones | `data/processed/travel_time_TTA_2024.csv`, `data/processed/access_zones_TTA.csv` | 146 × 15 et 146 × 13 |
| 5 | Météo & seuils *(B)* | `weather.weather_daily`, `weather.thresholds`, `weather.forecast_daily` | voir section 5 |
| 6 | Risque quotidien | `weather.risk_daily` (PostgreSQL) | 10 colonnes, voir section 6 |

---

## Légende des statuts de valeur

| Statut | Signification |
|---|---|
| `OFFICIEL` | Valeur publiée par la source, non transformée |
| `CALCULE` | Dérivée par nos soins à partir de valeurs officielles (formule documentée) |
| `ESTIME` | Approximation assumée, méthode documentée |
| `OBSERVE` | Mesure relevée (météo, terrain) |
| `PREVU` | Prévision météo, avec horizon explicite |
| `A_REMPLIR` | Donnée manquante — **jamais inventée**, en attente de source |
| `NON_CALCULE` | Non calculable faute de données (ex. commune non routable) |

> ⚠️ La colonne `statut_valeur` du CSV est une **simplification** : elle porte `OFFICIEL` sur les 146 lignes. Le statut exact de **chaque colonne** est celui des tableaux ci-dessous, qui fait foi.

---

## 1. `communes_TTA_2024.csv` — référentiel territorial (146 × 25)

**Clé primaire : `commune_code` — TEXTE, zéros initiaux conservés.**
**Une ligne = une commune au découpage officiel HCP. Tanger est **une** ligne (ses 4 arrondissements sont agrégés).**

### 1.1 Identité administrative

| # | Variable | Type | Unité | Source | Période | Statut | Description / limites |
|---|---|---|---|---|---|---|---|
| 1 | `commune_code` | texte | — | HCP RGPH 2024 | 2024 | `OFFICIEL` | Format `MA-RR-PPP-CCCC` (ex. `MA-01-051-0101`). **Clé de jointure unique de tout le projet.** Ne jamais convertir en entier. |
| 2 | `name_fr` | texte | — | HCP RGPH 2024 | 2024 | `OFFICIEL` | Nom français. **Jamais utilisé comme clé de jointure.** |
| 3 | `name_ar` | texte | — | HCP RGPH 2024 | 2024 | `OFFICIEL` | Nom arabe, pour l'affichage bilingue. |
| 4 | `province` | texte | — | HCP RGPH 2024 | 2024 | `OFFICIEL` | Nom de la province ou préfecture. **8 valeurs** dans la région. |
| 5 | `province_code` | texte | — | HCP RGPH 2024 | 2024 | `OFFICIEL` | Préfixe à 9 caractères du code commune (ex. `MA-01-051`). |
| 6 | `milieu` | texte | — | HCP RGPH 2024 | 2024 | `OFFICIEL` | `Urbain` (17) / `Mixte` (60) / `Rural` (69). « Mixte » = commune ayant des douars ruraux **et** un centre urbain. |

### 1.2 Population et ménages

| # | Variable | Type | Unité | Source | Période | Statut | Description / limites |
|---|---|---|---|---|---|---|---|
| 7 | `population_2014` | entier | habitants | HCP RGPH 2014 — *Population légale des régions, provinces, préfectures, municipalités, arrondissements et communes (12 régions)* | 2014 | `OFFICIEL` | Population légale au recensement de 2014. **Contrôle : somme des 146 = 3 556 729 = total régional officiel, écart 0.** |
| 8 | `population_2024` | entier | habitants | HCP RGPH 2024 | 2024 | `OFFICIEL` | Population légale au recensement de 2024. **Contrôle : somme = 4 030 222, écart 0.** |
| 9 | `menages_2014` | entier | ménages | HCP RGPH 2014 (même source que la pop. 2014) | 2014 | `OFFICIEL` | Ménages 2014. **Contrôle : somme = 799 124, écart 0.** |
| 10 | `menages_2024` | entier | ménages | HCP RGPH 2024 | 2024 | `OFFICIEL` | Ménages 2024. **Contrôle : somme = 1 048 860, écart 0.** |
| 11 | `croissance_annuelle_pct` | décimal | %/an | Calculé | 2014→2024 | `CALCULE` | `(pop2024 / pop2014)^(1/10) − 1`, exprimé en %. Négatif = commune en déprise. |
| 12 | `part_60plus_2014_pct` | décimal | % | HCP RGPH 2014 — *Indicateurs communaux, individus* | 2014 | `OFFICIEL` | Part des 60 ans et plus. **Seule année disponible au niveau communal** : le HCP ne publie pas cette variable pour 2024 à l'échelle communale. **Ne jamais l'étiqueter « 2024 ».** Indicateur de vulnérabilité sociale (§14.1 du document de conception). |
| 13 | `population_urbaine_2024` | entier | habitants | HCP RGPH 2024 | 2024 | `OFFICIEL` | Population en milieu urbain. |
| 14 | `population_rurale_2024` | entier | habitants | HCP RGPH 2024 | 2024 | `OFFICIEL` | Population en milieu rural. |
| 15 | `part_rurale_pct` | décimal | % | Calculé | 2024 | `CALCULE` | `population_rurale_2024 / population_2024 × 100`. |

### 1.3 Géométrie et position

| # | Variable | Type | Unité | Source | Période | Statut | Description / limites |
|---|---|---|---|---|---|---|---|
| 16 | `area_km2` | décimal | km² | Calculé sur la géométrie | 2024 | `ESTIME` | Surface du polygone **simplifié**. Total régional 16 644 km² ; le HCP annonce ≈ 15–16 000 km². **Non officielle — ne pas publier comme chiffre HCP.** |
| 17 | `densite_hab_km2` | décimal | hab/km² | Calculé | 2024 | `CALCULE` | `population_2024 / area_km2`. **Toujours calculée, jamais saisie.** Hérite de l'imprécision de `area_km2`. |
| 18 | `centroid_lon` | décimal | degrés | Calculé sur la géométrie | 2024 | `CALCULE` | **Longitude** du centroïde géométrique (WGS84 / EPSG:4326). Ordre (lon, lat) — piège d'inversion. Peut tomber hors zone habitée. **Ne pas utiliser pour un trajet.** |
| 19 | `centroid_lat` | décimal | degrés | Calculé sur la géométrie | 2024 | `CALCULE` | **Latitude** du centroïde géométrique. Même réserve. |
| 20 | `start_lon` | décimal | degrés | Calculé sur la géométrie | 2024 | `CALCULE` | **Longitude du point de départ** du trajet : point représentatif **intérieur** au polygone. C'est **cette** colonne qu'on envoie à OpenRouteService et à Open-Meteo. |
| 21 | `start_lat` | décimal | degrés | Calculé sur la géométrie | 2024 | `CALCULE` | **Latitude du point de départ** du trajet. |

### 1.4 Identifiant OpenStreetMap

| # | Variable | Type | Unité | Source | Période | Statut | Description / limites |
|---|---|---|---|---|---|---|---|
| 22 | `osm_relation_id` | entier | — | OpenStreetMap (Overpass API) | 2026-11 | `OFFICIEL` | Identifiant de la relation `admin_level=8` correspondante. **146/146 remplies, 146 valeurs uniques.** Permet de relier une commune à sa géométrie OSM pour les mises à jour futures. |

### 1.5 Traçabilité

| # | Variable | Type | Unité | Source | Période | Statut | Description / limites |
|---|---|---|---|---|---|---|---|
| 23 | `annee_reference` | entier | — | — | — | — | Année des valeurs de population (2024). Une population sans année n'est pas une donnée. |
| 24 | `source` | texte | — | — | — | — | Chaîne de traçabilité : « HCP RGPH 2024 + RGPH 2014 (population légale) + OSM (id de relation) ». |
| 25 | `statut_valeur` | texte | — | — | — | — | Statut global simplifié. **Voir l'avertissement en tête : le statut exact est celui de chaque colonne ci-dessus.** |

### 1.6 Récapitulatif des contrôles

| Contrôle | Résultat |
|---|---|
| Nombre de lignes | **146** ✅ |
| Codes uniques | **146** ✅ |
| Valeurs vides | **0** ✅ |
| Somme `population_2014` | 3 556 729 = officiel ✅ |
| Somme `population_2024` | 4 030 222 = officiel ✅ |
| Somme `menages_2014` | 799 124 = officiel ✅ |
| Somme `menages_2024` | 1 048 860 = officiel ✅ |
| Répartition `milieu` | 17 / 60 / 69 = 146 ✅ |
| `osm_relation_id` renseignés | 146 / 146, tous uniques ✅ |
| Coordonnées dans la bbox TTA | 146 / 146 ✅ |

---

## 2. `communes_TTA.geojson` — contours (146 × 8)

`FeatureCollection`, WGS84 / EPSG:4326, ordre **(longitude, latitude)**, coordonnées arrondies à 5 décimales.

| Propriété | Type | Description |
|---|---|---|
| `commune_code` | texte | **Identique** aux 146 valeurs du CSV. Contrôle automatique : égalité stricte des deux ensembles. |
| `name_fr` | texte | Nom français |
| `name_ar` | texte | Nom arabe |
| `province` | texte | Province ou préfecture |
| `province_code` | texte | Code province |
| `centroid_lon` | décimal | Longitude du centroïde (étiquette de carte) |
| `centroid_lat` | décimal | Latitude du centroïde |
| `area_km2` | décimal | Surface, identique à celle du CSV |

**Simplification :** tolérance 0,003° (≈ 330 m), `preserve_topology=True`, géométries valides vérifiées (0 invalide).
**Tanger :** les 4 arrondissements (Bni Makada, Mghogha, Souani, Médina) sont **fusionnés en un seul polygone** `MA-01-511-0100`.
**Volume :** 239 671 octets (contre 763 294 pour la version non fusionnée à 149 entités).

---

## 3. `health_facilities_TTA.csv` — établissements de santé (892 × 13)

Source : extrait **OpenStreetMap** de Geofabrik (Maroc, 12/11/2026), filtré sur la bbox TTA élargie de 50 km. Licence **ODbL — « © OpenStreetMap contributors »**.

| # | Variable | Type | Unité | Statut | Description / limites |
|---|---|---|---|---|---|
| 1 | `osm_type` | texte | — | `OFFICIEL` | `node` ou `way`. Combiné à `osm_id`, forme l'identifiant unique. |
| 2 | `osm_id` | entier | — | `OFFICIEL` | Identifiant OpenStreetMap. |
| 3 | `name` | texte | — | `OFFICIEL` | Nom de l'établissement. **21 lignes sans nom** en zone rurale — ne pas les supprimer, elles restent des points d'accès potentiels. |
| 4 | `facility_type` | texte | — | `OFFICIEL` | `pharmacy` (776), `hospital` (66), `clinic` (22), `doctors` (20), `laboratory` (4), `healthcare_unspecified` (3), `physiotherapist` (1). **Le filtrage se fait ici** : pour l'accessibilité aux soins, retenir `hospital` / `clinic` / `doctors` / `laboratory`. |
| 5 | `healthcare` | texte | — | `OFFICIEL` | Sous-tag OSM `healthcare`. Souvent vide. |
| 6 | `lat` | décimal | degrés | `OFFICIEL` | Latitude WGS84 (arrondie à 6 décimales). Pour un `way`, centroïde de l'emprise. |
| 7 | `lon` | décimal | degrés | `OFFICIEL` | Longitude WGS84. |
| 8 | `operator` | texte | — | `OFFICIEL` | Gestionnaire, si renseigné (public / privé). |
| 9 | `opening_hours` | texte | — | `OFFICIEL` | Horaires au format OSM. Taux de remplissage faible en rural. |
| 10 | `phone` | texte | — | `OFFICIEL` | Téléphone, si renseigné. |
| 11 | `addr_city` | texte | — | `OFFICIEL` | Ville déclarée dans l'adresse. |
| 12 | `source` | texte | — | — | « OpenStreetMap (Geofabrik Maroc 2026-11-12) ». |
| 13 | `licence` | texte | — | — | `ODbL`. |

### 3.1 Limites à assumer devant le jury

| Limite | Conséquence |
|---|---|
| OSM est **incomplet en milieu rural** | Les 299 établissements de santé primaire recensés par le Ministère de la Santé (fichier `essp-2025.xlsx`, non encore intégré) ne sont **presque pas** présents dans OSM : 0 `health_post` trouvé. |
| **Pas de hiérarchie officielle** | OSM ne dit pas si un établissement est un hôpital de référence ou un dispensaire. |
| Aucune **capacité** (lits, personnel) | Non disponible en open data à l'échelle de l'établissement. |
| **5 hôpitaux sans nom** | Sur les 66 hôpitaux, **5 n'ont pas de `name`** dans OSM (identifiants `10558675910`, `363772898`, `411183375`, `478960842`, `908806511`). Ils sont conservés : leur position est valide et le temps de trajet ne dépend pas du nom. |
| Recoupement Ministère | **16 des 24 hôpitaux officiels** de la région ont été retrouvés par leur nom dans OSM. Les 8 autres restent à géocoder. |

---

## 4. `travel_time` — temps de trajet *(propriété A)*

**Fichier livré :** `data/processed/travel_time_TTA_2024.csv` — **146 lignes × 15 colonnes**, une ligne par commune.
**Statut en base :** les temps sont aujourd'hui lus depuis ce CSV ; une table `accessibility.travel_time` est prévue
et devra contenir exactement les mêmes colonnes.

| Variable | Type | Unité | Source | Statut | Description / limites |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé. Une seule ligne par commune. |
| `name_fr` | texte | — | Référentiel §1 | `OFFICIEL` | Nom d'affichage. **Jamais utilisé pour une jointure.** |
| `province` | texte | — | Référentiel §1 | `OFFICIEL` | Province ou préfecture (8 valeurs). |
| `milieu` | texte | — | Référentiel §1 | `OFFICIEL` | `Urbain` (17 communes) / `Mixte` (60) / `Rural` (69). `Mixte` = commune ayant à la fois des douars urbains et ruraux (D-006), catégorie propre au projet et non officielle. |
| `start_lat` / `start_lon` | décimal | degrés | Référentiel §1 | `CALCULE` | Point de départ : point représentatif intérieur (D-002). Ordre lat puis lon. |
| `hospital_osm_type` | texte | — | OpenStreetMap | `OBSERVE` | `node` / `way` / `relation` de l'établissement retenu. |
| `hospital_osm_id` | texte | — | OpenStreetMap | `OBSERVE` | Identifiant OSM : clé stable de l'établissement. |
| `hospital_name` | texte | — | OpenStreetMap | `OBSERVE` | Nom de l'hôpital (parfois en arabe). |
| `hospital_lat` / `hospital_lon` | décimal | degrés | OpenStreetMap | `OBSERVE` | Coordonnées de l'hôpital. |
| `distance_km` | décimal | km | OpenRouteService | `CALCULE` | Distance routière réelle. |
| `temps_min` | décimal | minutes | OpenRouteService | `CALCULE` | Temps de trajet routier : 1,0 (min) / 36,7 (médiane) / 120,2 (max). **Ne vaut pas garantie en urgence.** |
| `classe_trajet` | entier | 1-3 | Calculé | `CALCULE` | 1 = moins de 15 min, 2 = de 15 à 45 min, 3 = plus de 45 min (D-015). Distribution : 22 / 66 / 58. |
| `methode` | texte | — | — | — | `ORS_DRIVING_CAR` sur les 146 lignes. Aucun `DETOUR_1.4` n'a été livré. |

La population de la commune n'est **pas** dans ce fichier : elle se trouve dans `communes_TTA_2024.csv` (§1)
et elle est reprise dans `access_zones_TTA.csv` (§4.1).

### 4.1 Zones d'accessibilité — `access_zones_TTA.csv`

**146 lignes × 13 colonnes**, dérivées du fichier ci-dessus par `scripts/build_access_zones.py` (PR #15) :
`commune_code`, `name_fr`, `province`, `milieu`, `population_2024`, `temps_min`, `distance_km`, `hospital_name`,
`zone_15_min`, `zone_30_min`, `zone_45_min`, `zone_60_min` (drapeaux 0/1) et `zone` (texte).

| Zone | Communes | Part | Population | Part |
|---|---|---|---|---|
| ≤ 15 min | 22 | 15,1 % | 2 543 958 | 63,1 % |
| ≤ 30 min | 59 | 40,4 % | 3 087 495 | 76,6 % |
| ≤ 45 min | 88 | 60,3 % | 3 374 547 | 83,7 % |
| ≤ 60 min | 108 | 74,0 % | 3 591 480 | 89,1 % |
| > 60 min | 38 | 26,0 % | 438 742 | 10,9 % |

**Colonnes retirées du dictionnaire v1 :** `facility_id` (remplacé par `hospital_osm_type` + `hospital_osm_id`),
`minutes` (vrai nom : `temps_min`) et `unpaved_share` (jamais calculé : le tag OSM `surface` n'est pas disponible
sur les 146 tracés).

---

## 5. Météo & seuils *(propriété B)*

Trois tables PostgreSQL du schéma `weather` (créées par `sql/init.sql`). Ce ne sont pas des fichiers livrés :
elles sont alimentées par `src/tta_risk/weather/` et les scripts de `scripts/`.

### 5.1 `weather.weather_daily` — historique météorologique

| Variable | Type | Unité | Source | Statut | Description |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé, avec `date`. |
| `date` | date | — | Open-Meteo | `OBSERVE` | Jour observé. |
| `precipitation_sum` | décimal | mm | Open-Meteo | `OBSERVE` | Cumul de pluie du jour. |
| `temperature_2m_max` | décimal | °C | Open-Meteo | `OBSERVE` | Température maximale du jour. |
| `ingested_at` | horodatage | — | Base | — | Date d'écriture, automatique. |

### 5.2 `weather.thresholds` — seuils mensuels

| Variable | Type | Unité | Source | Statut | Description |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé, avec `month`. |
| `month` | petit entier | 1-12 | — | — | Mois calendaire. |
| `rain_p65` / `rain_p80` / `rain_p90` | décimal | mm | Historique calculé | `CALCULE` | Niveau 1 = p65, 2 = p80, 3 = p90 (D-014). |
| `heat_p65` / `heat_p80` / `heat_p90` | décimal | °C | Historique calculé | `CALCULE` | Mêmes seuils appliqués à `temperature_2m_max`. |
| `computed_at` | horodatage | — | Base | — | Date de calcul. |

Une ligne par commune et par mois : 146 × 12 = 1 752 attendues.

### 5.3 `weather.forecast_daily` — prévisions

| Variable | Type | Unité | Source | Statut | Description |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé, avec les deux dates. |
| `forecast_issued_on` | date | — | — | — | **Date de récupération** de la prévision. |
| `target_date` | date | — | — | `PREVU` | **Jour visé** par la prévision (horizon de 3 jours). |
| `precip_mm` | réel | mm | Open-Meteo | `PREVU` | Pluie prévue. |
| `tmax_c` | réel | °C | Open-Meteo | `PREVU` | Température maximale prévue. |
| `ingested_at` | horodatage | — | Base | — | Date d'écriture, automatique. |

Clé : (`commune_code`, `forecast_issued_on`, `target_date`).

> Piège : ne jamais confondre `forecast_issued_on` (quand on a récupéré) et `target_date` (le jour prévu).
> C'était exactement le bug corrigé en PR #14.

**Colonnes retirées du dictionnaire v1 :** `precipitation_probability_max` (non récupérée),
`horizon_jours` (= `target_date` − `forecast_issued_on`, recalculable), `source_fetch_time` (= `ingested_at`),
`nb_observations` (non stocké ; la fiabilité des seuils est contrôlée par `tests/test_thresholds.py`).

---

## 6. `weather.risk_daily` — sortie du danger quotidien *(propriété B, complétée par A)*

Table écrite par `scripts/run_risk_daily.py`. **État actuel : le danger météo est écrit, le score ne l'est pas
encore** — les quatre colonnes du score sont ajoutées à l'étape suivante (dernière ligne de ce tableau).

| Variable | Type | Unité | Statut | Description |
|---|---|---|---|---|
| `commune_code` | texte | — | — | Clé, avec les deux dates. |
| `forecast_issued_on` | date | — | — | Date de récupération de la prévision. |
| `target_date` | date | — | — | Jour visé. |
| `precip_mm` | réel | mm | `PREVU` | Pluie prévue. |
| `tmax_c` | réel | °C | `PREVU` | Température maximale prévue. |
| `rain_level` | petit entier | 0-3 | `CALCULE` | Niveau pluie : 0 si moins de 1 mm ; 1 si ≥ p65 ; 2 si ≥ p80 ; 3 si ≥ p90. |
| `heat_level` | petit entier | 0-3 | `CALCULE` | Niveau chaleur, mêmes seuils appliqués à `tmax_c`. |
| `danger` | petit entier | 0-3 | `CALCULE` | `max(rain_level, heat_level)`. C'est le `danger_meteo` de la méthodologie. |
| `dominant` | texte | — | `CALCULE` | Météo dominante **uniquement** : `rain` / `heat` / `both` / `none`. Ne vaut jamais `eloignement` (D-018). |
| `classe_trajet` | petit entier | 1-3 | `CALCULE` | 1 = moins de 15 min, 2 = de 15 à 45 min, 3 = plus de 45 min (D-015). Vient de `travel_time_TTA_2024.csv`. |
| `score` | petit entier | 0-9 | `CALCULE` | `danger × classe_trajet` → 0, 1, 2, 3, 4, 6, 9. **Score ordinal, pas une probabilité.** |
| `niveau` | texte | — | `CALCULE` | `vert` (0) / `jaune` (1-2) / `orange` (3-4) / `rouge` (6-9). |
| `raison` | texte | — | `CALCULE` | Facteur **affiché** : `pluie` / `chaleur` / `eloignement`. Départage : pluie, puis chaleur, puis éloignement. Voir D-018. |
| `computed_at` | horodatage | — | — | Date d'écriture, automatique. |


**Colonnes retirées du dictionnaire v1 :** `danger_meteo` (nom réel : `danger`), `composante_pluie` et
`composante_chaleur` (noms réels : `rain_level` et `heat_level`), `date` (nom réel : `target_date`),
`population_exposee` (calculée à l'affichage et dans l'export, jamais stockée commune par commune),
`qualite_donnees` et `statut_peremption` (jamais calculés : la fraîcheur se lit avec `forecast_issued_on`
et `computed_at`).

---

## 7. Pièges à documenter dans le rapport

1. **Zéros initiaux** : `051` → `51` fait disparaître 50 communes d'une jointure. `dtype=str` partout.
2. **Ordre des coordonnées** : ORS et Open-Meteo attendent parfois (lon, lat), parfois (lat, lon). Toujours vérifier le format exact dans la doc de l'API.
3. **Tanger** : dans la source géométrique, 4 polygones ; dans notre livrable, **1 seule ligne**. Tout comptage doit donner 146.
4. **Ne jamais joindre sur le nom** : « M'diq » / « Mdiq » / « المضيق ». Quatre communes du territoire s'écrivent différemment selon les fichiers : *Bni Abdallah*, *Bou Jedyane*, *Moqrisset*, *Ounnana*.
5. **Surface** : non officielle → ne pas en déduire des densités présentées comme officielles.
6. **Population légale ≠ population présente** : saisonnalité, marché, migration.
7. **`part_60plus_2014_pct` est de 2014** : ne jamais l'afficher comme une donnée 2024.
8. **`statut_valeur` est global** : ne pas s'y fier colonne par colonne, ce dictionnaire fait foi.

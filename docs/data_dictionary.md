# data_dictionary.md — Dictionnaire des variables

> Tenu par le **Membre A**. Version 1.0 — 17 novembre 2026.
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
| 4 | Accessibilité *(semaine 2 — C)* | `accessibility.parquet` | à venir |
| 5 | Météo & seuils *(semaine 2 — B)* | `historical_weather` / `thresholds` | à venir |
| 6 | Risque quotidien *(semaine 3)* | `risk_daily` | à venir |

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
| Recoupement Ministère | **16 des 24 hôpitaux officiels** de la région ont été retrouvés par leur nom dans OSM. Les 8 autres restent à géocoder. |

---

## 4. `accessibility` — temps de trajet *(semaine 2 — propriété C)*

| Variable | Type | Unité | Source | Statut | Description / limites |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé |
| `facility_id` | texte | — | §3 | — | Établissement **retenu** (le plus proche en temps) |
| `minutes` | entier | minutes | OpenRouteService | `CALCULE` | Temps de trajet routier. **Ne vaut pas garantie en urgence.** |
| `distance_km` | décimal | km | OpenRouteService | `CALCULE` | Distance routière |
| `unpaved_share` | décimal | 0–1 | OSM (tag `surface`) | `CALCULE` | Part de route non goudronnée du trajet |
| `methode` | texte | — | — | — | `ORS_DRIVING_CAR` / `DETOUR_1.4` (plan B) / `NON_CALCULE` |
| `classe_trajet` | texte | — | Calculé | `CALCULE` | `<15` / `15-45` / `>45`. **Bornes provisoires** — à revoir après examen de la distribution. |

---

## 5. Météo & seuils *(semaine 2 — propriété B)*

| Variable | Type | Unité | Source | Période | Statut |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel §1 | — | Clé |
| `date` / `forecast_target_date` | date | — | — | — | Ne jamais confondre date d'observation et date visée par la prévision |
| `precipitation_sum` | décimal | mm | Open-Meteo | — | `OBSERVE` ou `PREVU` |
| `temperature_2m_max` | décimal | °C | Open-Meteo | — | `OBSERVE` ou `PREVU` |
| `precipitation_probability_max` | entier | % | Open-Meteo | — | `PREVU` — sert à la **confiance** affichée |
| `horizon_jours` | entier | jours | Dérivé | — | `forecast_target_date − date_récupération` |
| `source_fetch_time` | horodatage | — | — | — | **Fraîcheur** de la prévision — affichée dans l'app |
| `seuil_pluie_p90/p95/p99` | décimal | mm | Calculé | historique | `CALCULE` + `nb_observations` obligatoire |
| `seuil_chaleur_p90/p95/p99` | décimal | °C | Calculé | historique | Par mois ou saison — **une seule règle pour le résultat officiel** |

---

## 6. `risk_daily` — sortie du scoring *(semaine 3)*

| Variable | Type | Unité | Statut | Description |
|---|---|---|---|---|
| `commune_code` | texte | — | — | Clé |
| `date` | date | — | — | Date visée par la prévision |
| `danger_meteo` | entier | 0–3 | `CALCULE` | Niveau issu des seuils p90/p95/p99 |
| `composante_pluie` | entier | 0–3 | `CALCULE` | **Conservée séparément** |
| `composante_chaleur` | entier | 0–3 | `CALCULE` | **Conservée séparément** |
| `classe_trajet` | texte | — | `CALCULE` | `<15` / `15-45` / `>45` |
| `score` | entier | — | `CALCULE` | `danger_meteo × classe_trajet`. **Score expérimental, PAS une probabilité.** |
| `niveau` | texte | — | `CALCULE` | `vert` / `jaune` / `orange` / `rouge` |
| `raison` | texte | — | `CALCULE` | Facteur dominant. **Règle de départage unique**, identique dans le code, le rapport et l'interface. |
| `population_exposee` | entier | hab. | `CALCULE` | **Indicateur séparé** — n'entre PAS dans le calcul du risque |
| `qualite_donnees` | texte | — | — | `COMPLET` / `PARTIEL` / `DEGRADE` |
| `statut_peremption` | texte | — | — | `FRAIS` / `PERIME` — **une donnée périmée ne doit jamais s'afficher comme fraîche** |

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

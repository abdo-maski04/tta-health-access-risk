# data_dictionary.md — Dictionnaire des variables

> Tenu par le **Membre A**. Version 0.1 (brouillon) — 11 novembre 2026.
> Règle : chaque variable a une **source**, une **unité**, une **période** et un **statut de qualité**.

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

---

## 1. `communes` / `communes_TTA_146.csv` — référence territoriale

**Clé primaire : `commune_code` — TEXTE, zéros initiaux conservés.**

| Variable | Type | Unité | Source | Période | Statut | Description / limites |
|---|---|---|---|---|---|---|
| `commune_code` | texte | — | HCP RGPH 2024 | 2024 | `OFFICIEL` | Format `MA-RR-PPP-CCCC`. **Clé de jointure unique de tout le projet.** Ne jamais convertir en entier, ne jamais rogner. |
| `commune_code_hcp` | texte | — | Dérivé | 2024 | `CALCULE` | Code au niveau communal officiel. Identique à `commune_code` sauf pour les 4 arrondissements de Tanger, qui pointent tous vers `MA-01-511-0103`. **Utiliser cette colonne pour tout comptage de communes.** |
| `est_arrondissement` | booléen | — | Dérivé | 2024 | `CALCULE` | `true` pour Bni Makada, Mghogha, Souani, Médina (Tanger). Permet de ne pas double-compter. |
| `province_code` | texte | — | HCP | 2024 | `OFFICIEL` | Préfixe à 9 caractères du code commune (ex. `MA-01-051`). |
| `province` | texte | — | HCP | 2024 | `OFFICIEL` | Nom français de la province ou préfecture (8 valeurs dans la région). |
| `name_fr` | texte | — | HCP | 2024 | `OFFICIEL` | Nom français. **Jamais utilisé comme clé de jointure.** |
| `name_ar` | texte | — | HCP | 2024 | `OFFICIEL` | Nom arabe. |
| `name_norm` | texte | — | Dérivé | 2024 | `CALCULE` | Nom normalisé (minuscules, sans accents, tirets et apostrophes remplacés par des espaces). **Usage : recherche et affichage uniquement — jamais pour joindre.** |
| `start_point_lon` | décimal | degrés | Dérivé de la géométrie | 2024 | `CALCULE` | **Longitude** du point de départ du trajet (WGS84 / EPSG:4326). Ordre (lon, lat) — **piège classique d'inversion**. |
| `start_point_lat` | décimal | degrés | Dérivé de la géométrie | 2024 | `CALCULE` | **Latitude** du point de départ. Point représentatif intérieur au polygone (décision du 11/11). |
| `centroid_lon` / `centroid_lat` | décimal | degrés | Dérivé | 2024 | `CALCULE` | Centroïde géométrique. Peut tomber hors zone habitée. **Conservé pour comparaison**, pas pour le trajet. |
| `area_km2` | décimal | km² | Dérivé | 2024 | `ESTIME` | Surface du polygone simplifié. **Non officielle** (total 16 644 km² vs ≈ 15–16 000 annoncés par le HCP). Usage interne seulement. |
| `nb_entites_geometriques` | entier | — | Dérivé | 2024 | `CALCULE` | Nombre de polygones fusionnés pour former la commune (4 pour Tanger, 1 ailleurs). |
| `geom_type` | texte | — | Source | 2024 | `OFFICIEL` | `Polygon` ou `MultiPolygon`. |
| `source` | texte | — | — | — | — | Traçabilité de la source de la géométrie. |
| `source_retrieved` | date | — | — | — | — | Date de collecte (YYYY-MM-DD). |

---

## 2. `demographics` — population

**Clé : `commune_code_hcp`** (attention : 146 lignes, pas 149).

| Variable | Type | Unité | Source | Période | Statut | Description / limites |
|---|---|---|---|---|---|---|
| `population_2024` | entier | habitants | HCP RGPH 2024 | 2024 | `OFFICIEL` (à remplir) | Population **légale** totale. Somme régionale de contrôle : ≈ **4 030 222** hab. |
| `population_2014` | entier | habitants | HCP RGPH 2014 | 2014 | `OFFICIEL` (à remplir) | Population légale au recensement précédent. Sert au taux d'accroissement. |
| `menages_2024` | entier | ménages | HCP RGPH 2024 | 2024 | `OFFICIEL` (à remplir) | Nombre de ménages. Utile pour la logistique (kit, distribution). |
| `milieu` | texte | — | HCP | 2024 | `OFFICIEL` | `Urbain` / `Rural`. **Indispensable au cas d'étude rural de montagne.** |
| `annee_reference` | entier | — | — | — | — | Année du recensement. Obligatoire : une population sans année n'est pas une donnée. |
| `source` | texte | — | — | — | — | « HCP RGPH 2024 » |
| `statut_valeur` | texte | — | — | — | — | Voir légende. Aucune population ne peut être `OFFICIEL` sans année de référence. |
| `superficie_km2` | décimal | km² | Référentiel | 2024 | `ESTIME` | Reprise de `area_km2`. **Non officielle.** |
| `densite_hab_km2` | décimal | hab/km² | Calculé | 2024 | `CALCULE` | `population_2024 / superficie_km2`. **Toujours calculée, jamais saisie.** Hétérogène : une commune de montagne peut inclure de vastes zones vides. |
| `variation_2014_2024_pct` | décimal | % | Calculé | 2014–2024 | `CALCULE` | `(pop2024 - pop2014) / pop2014 × 100`. Signal d'alerte si valeur absurde. |

---

## 3. `health_facilities` / `hospitals` — établissements *(propriété B)*

| Variable | Type | Unité | Source | Statut | Description / limites |
|---|---|---|---|---|---|
| `facility_id` | texte | — | OSM | `OFFICIEL` | `osm_type/osm_id` (ex. `node/123456`) |
| `name` | texte | — | OSM | `OFFICIEL` | Peut être absent en zone rurale |
| `type` | texte | — | OSM | `OFFICIEL` | `hospital`, `clinic`, `doctors`… Définition de « hôpital » à figer par l'équipe |
| `lon` / `lat` | décimal | degrés | OSM | `OFFICIEL` | WGS84 |
| `source` | texte | — | — | — | « © OpenStreetMap contributors, ODbL » |
| `date_verification` | date | — | — | — | Date du contrôle croisé |
| `qualite` | texte | — | — | — | `VERIFIE` / `OSM_ONLY` / `DOUTEUX` |

---

## 4. `accessibility` / `travel_time` — temps de trajet *(propriété B)*

| Variable | Type | Unité | Source | Statut | Description / limites |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel | — | Clé |
| `facility_id` | texte | — | OSM | — | Établissement **retenu** (le plus proche en temps) |
| `minutes` | entier | minutes | ORS | `CALCULE` | Temps de trajet routier. **Ne vaut pas garantie en urgence.** |
| `distance_km` | décimal | km | ORS | `CALCULE` | Distance routière |
| `methode` | texte | — | — | — | `ORS_DRIVING_CAR` / `DETOUR_1.4` (plan B) / `NON_CALCULE` |
| `qualite` | texte | — | — | — | `OK` / `APPROXIME` / `NON_CALCULE` |
| `classe_trajet` | texte | — | Calculé | `CALCULE` | `<15` / `15-45` / `>45`. **Bornes provisoires** — à revoir après examen de la distribution (décision d'équipe). |

---

## 5. `historical_weather` / `forecast_daily` / `thresholds` *(propriété C)*

| Variable | Type | Unité | Source | Période | Statut |
|---|---|---|---|---|---|
| `commune_code` | texte | — | Référentiel | — | Clé |
| `date` / `forecast_target_date` | date | — | — | — | Ne jamais confondre date d'observation et date visée par la prévision |
| `precipitation_sum` | décimal | mm | Open-Meteo | — | `OBSERVE` ou `PREVU` |
| `temperature_2m_max` | décimal | °C | Open-Meteo | — | `OBSERVE` ou `PREVU` |
| `horizon_jours` | entier | jours | Dérivé | — | `forecast_target_date − date_récupération` |
| `source_fetch_time` | horodatage | — | — | — | **Fraîcheur** de la prévision — affichée dans l'app |
| `seuil_pluie_p90/p95/p99` | décimal | mm | Calculé | historique | `CALCULE` + `nb_observations` obligatoire |
| `seuil_chaleur_p90/p95/p99` | décimal | °C | Calculé | historique | Par mois ou saison — **une seule règle pour le résultat officiel** |
| `methode` | texte | — | — | — | `JOURNALIER` (principal) ou `CUMUL_3J` (sensibilité) |

---

## 6. `risk_daily` — sortie du scoring *(C + revue A/B)*

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
| `raison` | texte | — | `CALCULE` | Facteur dominant. **Règle de départage unique**, testée et identique dans le code, le rapport et l'interface (revue A — tâche A-13) |
| `population_exposee` | entier | hab. | `CALCULE` | **Indicateur séparé** — n'entre PAS dans le calcul du risque |
| `qualite_donnees` | texte | — | — | `COMPLET` / `PARTIEL` / `DEGRADE` |
| `statut_peremption` | texte | — | — | `FRAIS` / `PERIME` (stale) — **une donnée périmée ne doit jamais s'afficher comme fraîche** |

---

## 7. Pièges à documenter dans le rapport

1. **Zéros initiaux** : `051` → `51` fait disparaître 50 communes d'une jointure. `dtype=str` partout.
2. **Ordre des coordonnées** : ORS et Open-Meteo attendent parfois (lon, lat), parfois (lat, lon). Toujours vérifier le format exact dans la doc de l'API.
3. **Tanger** : 4 polygones, 1 commune. Tout comptage doit utiliser `commune_code_hcp`.
4. **Ne jamais joindre sur le nom** : « M'diq » / « Mdiq » / « المضيق ».
5. **Surface** : non officielle → ne pas en déduire des densités présentées comme officielles.
6. **Population légale ≠ population présente** : une commune peut avoir une population légale faible mais une population présente importante (saisonnalité, marché).

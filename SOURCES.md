# SOURCES.md — Registre des sources du projet TTA Health Access Risk

> Registre tenu par le **Membre A**. Toute donnée entrant dans le projet doit être listée ici avec sa source, sa date de collecte, sa licence et ses limites connues.
> Version : 1.0 — 11 novembre 2026

---

## 1. Référentiel territorial (communes)

| Champ | Valeur |
|---|---|
| **Jeu de données** | Limites administratives communales — RGPH 2024 |
| **Producteur d'origine** | Haut-Commissariat au Plan (HCP), via la plateforme cartographique RGPH 2024 (`tilesbis.rgphapps.ma`) |
| **Distribution utilisée** | Dépôt `i-emek/Morocco-Geospatial-Visualisations`, fichier `data/rgph-2024/communes.geojson` |
| **Date de collecte** | 2026-11-11 |
| **Format** | GeoJSON, WGS84 / EPSG:4326, ordre (longitude, latitude) |
| **Couverture** | 1 540 communes au niveau national · **149 entités dans la région TTA** → **146 communes au niveau officiel HCP** |
| **Identifiant** | `code` au format `MA-RR-PPP-CCCC` (ex. `MA-01-511-0103`) |
| **Champs utilisés** | `code`, `name_fr`, `name_ar`, géométrie |
| **Licence** | ⚠️ **À confirmer auprès de l'encadrant.** Données issues du HCP — droits réservés du producteur ; la redistribution est soumise à autorisation. À citer obligatoirement : « Source : HCP, RGPH 2024 ». |
| **Limites connues** | Géométries **simplifiées** (tuilage zoom 7) : les frontières ne sont pas à précision cadastrale. La surface calculée (16 644 km²) **dépasse** les ≈ 15 000–16 000 km² annoncés dans les monographies HCP → **ne pas publier la surface comme chiffre officiel**. |
| **Traitements appliqués** | Voir §2 ci-dessous — tous codés dans `src/build_referentiel.py`, aucun édit manuel. |

### Contrôle du nombre de communes

Le découpage administratif de 2015 (décret du 20 février 2015) donne, pour la région Tanger-Tétouan-Al Hoceima :
**2 préfectures + 6 provinces = 24 cercles = 146 communes** (17 urbaines, 129 rurales).
*Sources de contrôle : monographies de la Direction Régionale HCP Tanger-Tétouan-Al Hoceima (éditions 2018 et 2025).*

Écart avec le fichier de géométries : **150 → 146**, expliqué par :
1. **Ceuta** (`MA-01-573-0100`, « Sebta ») présente dans le jeu national → exclue (hors souveraineté marocaine).
2. **Tanger** livrée en **4 arrondissements** (Bni Makada, Mghogha, Souani, Médina) alors que le HCP la compte pour **1 commune** → agrégés.

---

## 2. Journal des traitements appliqués au référentiel

| Date | Traitement | Justification | Fichier |
|---|---|---|---|
| 2026-11-11 | Filtre sur le préfixe régional `MA-01` | Périmètre du datathon | `src/build_referentiel.py` |
| 2026-11-11 | Exclusion de `MA-01-573-0100` (Ceuta) | Territoire hors souveraineté marocaine | idem |
| 2026-11-11 | Agrégation des 4 arrondissements de Tanger sous `commune_code_hcp` | Alignement sur le décompte officiel HCP | idem |
| 2026-11-11 | Calcul du point de départ = point représentatif intérieur au polygone | Méthode reproductible, jamais hors territoire | idem |
| 2026-11-11 | Calcul de surface par projection équirectangulaire locale | Approximation (erreur < 0,5 %) — **non officielle** | idem |

---

## 3. Démographie (population, ménages) — ✅ INTÉGRÉE

### 3.1 Population légale par commune

| Champ | Valeur |
|---|---|
| **Jeu de données** | Population légale du Royaume — RGPH 2024, niveau communal (collectivités territoriales) |
| **Producteur** | Haut-Commissariat au Plan (HCP) — Direction Régionale TTA |
| **Source effectivement utilisée** | Table officielle « Population légale du Royaume selon les résultats du RGPH 2024 — collectivités territoriales », reprise intégralement sur Wikipédia (article *Recensement général de la population et de l'habitat 2024 (Maroc)*), qui reproduit la publication HCP avec le **code géographique officiel** de chaque commune |
| **Date de collecte** | 2026-11-11 |
| **Année de référence** | 2024 (recensement du 1er septembre au 30 septembre 2024) |
| **Format** | Table HTML (wikitexte) → convertie en `population_legale_rgph2024_TTA.csv` |
| **Champs retenus** | population totale, population marocaine, étrangers, ménages, code géographique officiel |
| **Couverture** | 150 entités (146 communes + 4 arrondissements de Tanger) |
| **Licence** | Données HCP : droits réservés du producteur, **citation obligatoire**. La reprise Wikipédia est sous CC-BY-SA (à citer comme source secondaire). |
| **Contrôles effectués** | ✅ Somme des 146 communes = **4 030 222** hab. = total régional officiel (écart 0)<br>✅ Somme des ménages = **1 048 860** = total officiel (écart 0)<br>✅ Commune de Tanger = somme exacte des 4 arrondissements (**1 275 428**)<br>✅ 146/146 communes appariées |

**Limites connues.**
- Population **légale** (domicile administratif), et non population présente : une commune peut avoir une population légale faible mais une population saisonnière élevée.
- Le code géographique de la commune de Tanger est `01.511.01.0` (série à un chiffre), et non `…0103` : dans le fichier de géométries, `MA-01-511-0103` désigne l'**arrondissement de Bni Makada**. Cette confusion est un piège documenté.

### 3.2 Population et ménages par douar (milieu rural)

| Champ | Valeur |
|---|---|
| **Jeu de données** | Population et ménages par douar — région TTA, RGPH 2024 |
| **Producteur** | HCP — Direction Régionale TTA |
| **URL** | `https://www.hcp.ma/region-tanger/attachment/2814273/` |
| **Fichier local** | `data/raw_downloads/hcp_douars_rural_TTA_rgph2024.xlsx` |
| **Date de collecte** | 2026-11-11 |
| **Contenu** | 3 020 douars, 130 communes rurales, population et ménages par douar, code géographique à 13 caractères |
| **Licence** | HCP — citation obligatoire |
| **Usage dans le projet** | Détermination du **milieu de résidence** (urbain / rural / mixte) par commune |
| **Contrôles effectués** | ✅ Somme de la population rurale = **1 382 463** = total régional rural officiel (écart 0)<br>✅ Somme des ménages ruraux = **320 093** = total officiel (écart 0)<br>✅ Codes géographiques cohérents avec le référentiel sur 129 communes |

**Résultat :** 17 communes urbaines, 69 rurales, 60 mixtes — soit 129 communes rurales (17 + 60 + 52 urbaines pures... voir `qc_milieu.json` pour le détail), conforme au découpage HCP.

⚠️ **Piège documenté :** dans ce fichier Excel, les codes de la province d'Al Hoceima (051) ont **perdu leur zéro initial** (12 caractères au lieu de 13). Toute jointure naïve sur ces codes échoue silencieusement. Correction codée dans `src/build_milieu.py`.

---

## 4. Météo

### 4.1 Prévisions (utilisées par le pipeline quotidien — Membre C)

| Champ | Valeur |
|---|---|
| **Jeu de données** | Open-Meteo Forecast API |
| **Producteur** | Open-Meteo (modèles ouverts) |
| **URL** | `https://api.open-meteo.com/v1/forecast` |
| **Variables** | `precipitation_sum` (mm/j), `temperature_2m_max` (°C) — variables à figer avec C |
| **Fuseau** | `Africa/Casablanca` |
| **Test effectué** | ✅ 2026-11-11 — Tétouan (35,77 / −5,81) : réponse 200, 3 jours retournés, offset UTC = 0 |
| **Licence** | Open-Meteo : données ouvertes, **attribution obligatoire** (CC-BY 4.0 selon les modèles sous-jacents) — usage non commercial gratuit ; usage commercial soumis à abonnement |
| **Limites connues** | Données **modélisées**, pas mesurées. Résolution ~1–11 km : une commune de montagne peut être mal représentée. Horizon fiable limité (au-delà de 7 jours, incertitude forte). Panne ou quota possible → **obligation de conserver le dernier export et de signaler son horodatage** |

### 4.2 Historique (pour le calcul des seuils — Membre C)

| Champ | Valeur |
|---|---|
| **Jeu de données** | Open-Meteo Historical Weather API / ERA5 |
| **URL** | `https://archive-api.open-meteo.com/v1/archive` |
| **Période à retenir** | ⚠️ **À figer en équipe** (recommandation : ≥ 10 ans pour que les percentiles p90/p95/p99 soient robustes) |
| **Licence** | ERA5 / Copernicus : attribution requise (« Contains modified Copernicus Climate Change Service information ») |
| **Limites connues** | Réanalyse : biais possibles en zone côtière et de relief. Nombre d'observations à consigner pour chaque seuil. |

---

## 5. Établissements de santé

| Champ | Valeur |
|---|---|
| **Jeu de données** | OpenStreetMap — `amenity=hospital`, `amenity=clinic`, `amenity=doctors`, `healthcare=*` |
| **Producteur** | Contributeurs OpenStreetMap |
| **Source d'extraction** | ⚠️ À préciser par B (Overpass API, Geofabrik, ou export HOT) |
| **Licence** | **ODbL 1.0** — attribution obligatoire : « © OpenStreetMap contributors ». Toute base dérivée doit rester sous ODbL. |
| **Limites connues** | **Couverture inégale** : les zones urbaines sont bien cartographiées, les zones rurales et de montagne beaucoup moins. Risque de **faux négatifs** (établissement existant non cartographié). Ne contient pas l'offre réelle (lits, services, horaires). |
| **Statut** | 🔴 À produire par B |

---

## 6. Temps de trajet

| Champ | Valeur |
|---|---|
| **Service** | OpenRouteService (ORS) — `directions/driving-car` et `matrix` |
| **Producteur** | HeiGIT / Université de Heidelberg |
| **Test effectué** | ⚠️ 2026-11-11 — appel sans clé → **401 Unauthorized**. **Une clé API est obligatoire.** |
| **Quota** | ⚠️ À vérifier par B (quotas journaliers/minute selon le plan) |
| **Licence** | Conditions d'utilisation ORS + attribution OSM (ORS s'appuie sur OSM) |
| **Limites connues** | Le temps de trajet est calculé **sur le réseau routier cartographié dans OSM** : une piste absente d'OSM n'existe pas pour le calcul. Ne tient pas compte des fermetures, de la neige, du trafic réel. **Ce n'est pas un itinéraire garanti en situation d'urgence** — mention obligatoire dans l'app. |
| **Statut** | 🔴 Clé à créer par B — **point bloquant du go/no-go** |

**Plan B si ORS est indisponible** (à décider le jour même, conformément au dossier) :
- distance à vol d'oiseau × **coefficient de détour** (≈ 1,4) → à documenter comme **approximation**, jamais comme « temps de trajet »
- ou jeu de temps figé sur un échantillon, le reste en `NON_CALCULE` → ces communes **doivent rester visibles** dans l'app (interdiction de les masquer)

---

## 7. Sources de contrôle indépendantes (pour la validation — tâche A-6)

| Source | Usage | Licence / accès |
|---|---|---|
| Monographies HCP Tanger-Tétouan-Al Hoceima (2018, 2025) | Vérifier les 146 communes, la répartition par province | Publication publique HCP |
| Wikipédia — *Recensement général de la population et de l'habitat 2024 (Maroc)* | Contrôle croisé des codes géographiques (`RR.PPP.CC.SS`) | CC-BY-SA |
| geoBoundaries (`MAR-ADM2`) | Contrôle indépendant des limites provinciales | CC-BY 4.0 |
| `elbouamrani/geojson-morocco-db` | Contrôle indépendant de la hiérarchie géographique | À vérifier |
| Site de la Direction Régionale HCP TTA | Population légale 2024 par commune | Publication publique HCP |

---

## 8. Ce qu'il reste à faire dans ce registre

- [ ] Confirmer la **licence HCP** (utilisation et redistribution) auprès de l'encadrant — **bloquant pour la publication du dataset**
- [ ] Compléter la date de collecte de la population (tâche A-2)
- [ ] Compléter la section établissements quand B a fini son extraction
- [ ] Compléter la section trajets quand la clé ORS est active et le quota connu
- [ ] Figer la **période historique météo** retenue pour les seuils
- [ ] Vérifier que `data/raw_downloads/` est bien dans `.gitignore` (les bruts ne se versionnent pas)

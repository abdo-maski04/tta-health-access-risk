# Rapport qualite v1 — referentiel territorial TTA

> Tenu par le **Membre A**. Date : 2026-11-25.
> Objet : prouver, chiffre par chiffre, que le referentiel des 146 communes est utilisable
> et que ses limites sont connues. Ce document repond a la tache **A-7**.

## 1. Ce qui est livre

| Fichier | Contenu | Taille |
|---|---|---|
| `data/processed/communes_TTA_2024.csv` | 146 lignes x 25 colonnes | 146 communes |
| `data/processed/communes_TTA.geojson` | 146 polygones + centroides, EPSG:4326 | 146 entites |
| `data/processed/health_facilities_TTA.csv` | 892 etablissements OSM | 892 lignes |
| `data/processed/travel_time_TTA_2024.csv` | temps de trajet ORS | 146 lignes |
| `data/processed/access_zones_TTA.csv` | zones 15 / 30 / 45 / 60 min | 146 lignes |

## 2. Les 6 controles qui sont passes

| # | Controle | Resultat | Comment le refaire |
|---|---|---|---|
| 1 | Nombre de communes | **146** exactement | `pytest -m territory` |
| 2 | Unicite de `commune_code` | **146 codes, 0 doublon** | `pytest -m territory` |
| 3 | Repartition par province | 36 / 28 / 22 / 19 / 17 / 12 / 7 / 5 = **146** | §3 ci-dessous |
| 4 | Somme de la population | **4 030 222** habitants | `communes_TTA_2024.csv` |
| 5 | Coordonnees manquantes | **0** (les 146 ont `centroid_lat` et `centroid_lon`) | controle pandas |
| 6 | Jointures | **0 orphelin** entre communes, hopitaux, temps et zones | controle pandas |

## 3. Repartition par province (controle contre le HCP)

| Province / Prefecture | HCP | Obtenu | Ecart |
|---|---|---|---|
| Al Hoceima | 36 | 36 | 0 |
| Chefchaouen | 28 | 28 | 0 |
| Tetouan | 22 | 22 | 0 |
| Larache | 19 | 19 | 0 |
| Ouezzane | 17 | 17 | 0 |
| Tanger-Assilah | 12 | 12 | 0 |
| Fahs-Anjra | 7 | 7 | 0 |
| M'diq-Fnideq | 5 | 5 | 0 |
| **Region TTA** | **146** | **146** | **0** |

## 4. Milieu de residence

| Milieu | Communes |
|---|---|
| Urbain | 17 |
| Mixte | 60 |
| Rural | 69 |

La categorie **Mixte** est propre au projet (D-006) : elle designe une commune qui contient
a la fois des douars urbains et ruraux. Elle n'est pas officielle et doit etre expliquee
a l'oral.

## 5. Ce que ce rapport ne prouve pas

- La **population** est la population **legale** (HCP), pas la population presente : la
  saisonnalite n'est pas couverte.
- Les **limites** sont simplifiees (tuilage zoom 7) : la superficie calculee (16 644 km2)
  depasse les valeurs des monographies HCP et **ne doit pas etre publiee** comme officielle.
- La **licence HCP** n'est pas encore confirmee par ecrit (D-010).

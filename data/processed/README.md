# data/processed — Jeu de données livrable (Membre A)

**Généré le 11 novembre 2026** · Source : HCP, RGPH 2024 · Reproductible via `src/build_livrable.py`

---

## `communes_TTA_2024_livrable.csv` — la table de référence du projet

**146 lignes · 18 colonnes · aucune valeur manquante.**

| Colonne | Type | Unité | Description |
|---|---|---|---|
| `commune_code` | texte | — | **Clé primaire.** Format `MA-01-PPP-CCCC`. Toujours en texte. |
| `name_fr` | texte | — | Nom français |
| `name_ar` | texte | — | Nom arabe |
| `province` | texte | — | Province ou préfecture (8 valeurs) |
| `province_code` | texte | — | Préfixe à 9 caractères (`MA-01-051`) |
| `start_point_lon` | décimal | degrés | **Longitude** du point de départ du trajet |
| `start_point_lat` | décimal | degrés | **Latitude** du point de départ du trajet |
| `area_km2` | décimal | km² | Surface — ⚠️ **ESTIMÉE**, non officielle |
| `population_2024` | entier | habitants | Population légale RGPH 2024 |
| `population_urbaine_2024` | entier | habitants | Population en milieu urbain |
| `population_rurale_2024` | entier | habitants | Population en milieu rural (issue des douars) |
| `menages_2024` | entier | ménages | Nombre de ménages |
| `part_rurale_pct` | décimal | % | Part de la population rurale |
| `milieu` | texte | — | `Urbain` / `Rural` / `Mixte` |
| `densite_hab_km2` | décimal | hab/km² | Calculée — ⚠️ indicative (surface estimée) |
| `annee_reference` | entier | — | 2024 |
| `source` | texte | — | HCP RGPH 2024 |
| `statut_valeur` | texte | — | `OFFICIEL` |

### Totaux de contrôle

| Indicateur | Valeur | Officiel HCP | Écart |
|---|---:|---:|---:|
| Population | 4 030 222 | 4 030 222 | **0** ✅ |
| Ménages | 1 048 860 | 1 048 860 | **0** ✅ |
| Population rurale | 1 382 463 | 1 382 463 | **0** ✅ |

### Répartition

- **8 provinces** : Al Hoceima 36 · Chefchaouen 28 · Fahs-Anjra 7 · Larache 19 · Ouezzane 17 · Tanger-Assilah 12 · Tétouan 22 · M'diq-Fnideq 5
- **Milieu** : 17 urbaines · 69 rurales · 60 mixtes (soit 129 communes rurales = chiffre officiel)
- **Taille des communes** : médiane 10 712 hab. · 65 communes < 10 000 hab. · 122 communes < 20 000 hab.

---

## `communes_TTA_2024_points.geojson`

146 points (centroïdes) en EPSG:4326, ordre **(longitude, latitude)**.
Version **allégée** pour l'application : pas de polygone, fichier léger.
Pour les polygones complets, utiliser `data/reference/communes_TTA.geojson`.

---

## ⚠️ À lire avant d'utiliser ces fichiers

1. **`commune_code` reste TOUJOURS du texte.**
   ```python
   import pandas as pd
   df = pd.read_csv("communes_TTA_2024_livrable.csv", dtype={"commune_code": str})
   ```

2. **Jamais de jointure sur le nom.** « M'diq » s'écrit de plusieurs façons.

3. **Tanger = `MA-01-511-0100`.** Le code `MA-01-511-0103` est l'arrondissement de **Bni Makada**.
   Confondre les deux fait perdre **707 963 habitants**.

4. **`area_km2` et `densite_hab_km2` sont ESTIMÉS**, calculés sur des géométries simplifiées.
   Le total (16 644 km²) ne correspond pas aux 15 000–16 000 km² officiels. **Ne pas citer comme officiel.**

5. **Population légale ≠ population présente.** Une commune peut avoir une population saisonnière supérieure.

6. **Ce fichier ne contient pas encore** : établissements de santé (B), temps de trajet (B), météo (C), score de risque (C).

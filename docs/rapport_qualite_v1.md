# Rapport qualité v1 — Référentiel territorial et démographie
## TTA Health Access Risk · Membre A · 11 novembre 2026

> Ce document est la **preuve** que les données livrées sont justes, complètes et traçables.
> Il répond à la question du jury : *« Comment savez-vous que vos données sont fiables ? »*

---

## 1. Résumé exécutif

| Indicateur | Valeur | Statut |
|---|---|---|
| Communes au référentiel | **146** | ✅ conforme au découpage HCP |
| Provinces couvertes | **8 / 8** | ✅ aucun écart |
| Communes avec population officielle | **146 / 146** | ✅ 100 % |
| Population régionale obtenue | **4 030 222** | ✅ écart 0 avec l'officiel |
| Ménages obtenus | **1 048 860** | ✅ écart 0 avec l'officiel |
| Population rurale obtenue | **1 382 463** | ✅ écart 0 avec l'officiel |
| Clé `commune_code` unique | **oui** | ✅ |
| Valeurs manquantes dans le livrable | **0** | ✅ |
| Contrôles qualité au vert | **15 / 15** | ✅ |

**Conclusion :** le jeu de données du Membre A est **complet, cohérent et vérifié**. Il est utilisable par B et C sans réserve.

---

## 2. Répartition par province — contrôle du décompte

| Province / Préfecture | Communes attendues (HCP) | Communes obtenues | Écart | Population 2024 |
|---|---:|---:|---:|---:|
| Al Hoceima | 36 | 36 | 0 ✅ | 371 527 |
| Chefchaouen | 28 | 28 | 0 ✅ | 412 713 |
| Fahs-Anjra | 7 | 7 | 0 ✅ | 100 789 |
| Larache | 19 | 19 | 0 ✅ | 510 211 |
| Ouezzane | 17 | 17 | 0 ✅ | 274 577 |
| Tanger-Assilah | 12 | 12 | 0 ✅ | 1 494 413 |
| Tétouan | 22 | 22 | 0 ✅ | 611 928 |
| M'diq-Fnideq | 5 | 5 | 0 ✅ | 254 064 |
| **Région TTA** | **146** | **146** | **0** ✅ | **4 030 222** |

---

## 3. L'écart 150 → 146 : explication complète

Le fichier de géométries national contient **150 entités** dans la région. Le HCP en dénombre **146**. Deux causes, entièrement documentées :

| # | Cause | Effet | Traitement | Vérification |
|---|---|---|---|---|
| 1 | **Ceuta** (`MA-01-573-0100`, « Sebta ») figure dans le jeu national | +1 | **Exclue** : territoire hors souveraineté marocaine | Province M'diq-Fnideq = 5 communes après exclusion ✅ |
| 2 | **Tanger** livrée en **4 arrondissements** séparés (Bni Makada, Mghogha, Souani, Médina) ; le HCP la compte pour **1 commune** | +3 | **Agrégés** sous `MA-01-511-0100` | Tanger-Assilah = 12 communes après agrégation ✅ |

`150 − 1 − 3 = 146` ✅

---

## 4. Contrôle de la commune de Tanger (le point le plus sensible)

**Anomalie détectée.** Le code géométrie `MA-01-511-0103` ressemble à « Tanger » mais désigne en réalité l'**arrondissement de Bni Makada**. Le code officiel de la commune de Tanger est `01.511.01.0` → `MA-01-511-0100`.

**Conséquence si l'erreur n'avait pas été détectée :** Tanger aurait reçu 567 465 habitants au lieu de 1 275 428, soit **707 963 habitants perdus** et un total régional faux.

**Vérification effectuée :**

| Arrondissement | Population 2024 |
|---|---:|
| Bni Makada | 567 465 |
| Mghogha | 252 656 |
| Souani | 111 772 |
| Médina | 343 535 |
| **Somme des 4 arrondissements** | **1 275 428** |
| **Population officielle de la commune de Tanger** | **1 275 428** |
| **Écart** | **0** ✅ |

---

## 5. Profil statistique de la population (146 communes)

Comprendre la distribution est indispensable avant de figer les classes de trajet, les seuils et les cas d'étude.

| Statistique | Population communale |
|---|---:|
| Minimum | 2 099 (Al Kharroub, Tétouan) |
| 10ᵉ centile (p10) | 4 960 |
| 25ᵉ centile (p25) | 7 283 |
| **Médiane** | **10 712** |
| 75ᵉ centile (p75) | 16 630 |
| 90ᵉ centile (p90) | 32 372 |
| 95ᵉ centile (p95) | 65 134 |
| Maximum | 1 275 428 (Tanger) |
| Moyenne | 27 604 |

### Ce que ces chiffres disent (et pourquoi c'est important pour le projet)

1. **La région est très inégalitaire.** La médiane est de **10 712 habitants**, mais la moyenne est de **27 604** : la moyenne est tirée vers le haut par Tanger.
2. **Tanger concentre 31,6 % de la population régionale** à elle seule (1 275 428 sur 4 030 222).
3. **65 communes sur 146 (44 %) ont moins de 10 000 habitants.** Ce sont elles qui cumulent le plus de difficultés d'accès : petites, rurales, isolées.
4. **122 communes sur 146 (84 %) ont moins de 20 000 habitants.** Le projet est donc **massivement rural**, contrairement à l'impression que donne une carte dominée par Tanger et Tétouan.

> 🎯 **Argument fort pour le pitch :** « 84 % de nos communes ont moins de 20 000 habitants, et 44 % moins de 10 000. Notre projet parle d'abord des petites communes rurales, pas des grandes villes. »

### Les 41 communes les plus petites (moins de 5 000 habitants)

Ces communes sont **prioritaires pour le cas d'étude « commune rurale de montagne »**.
Exemples repérés : Al Kharroub (2 099), Al Manzla (2 680), Sidi Bouzineb (2 756), Chakrane (3 306), Tifarouine (3 318).

---

## 6. Milieu de résidence — contrôle par les douars

**Méthode.** La population des **douars** (3 020 villages, milieu rural uniquement) a été sommée par commune, puis comparée à la population légale totale.

| Milieu | Nombre de communes | Part |
|---|---:|---:|
| 🏙️ Urbain | **17** | 11,6 % |
| 🏘️ Mixte | **60** | 41,1 % |
| 🌾 Rural | **69** | 47,3 % |
| **Total rural (Rural + Mixte)** | **129** | **88,4 %** |

**Contrôles :**

| Contrôle | Obtenu | Officiel | Écart |
|---|---:|---:|---:|
| Population rurale totale | 1 382 463 | 1 382 463 | **0** ✅ |
| Ménages ruraux totaux | 320 093 | 320 093 | **0** ✅ |
| Communes rurales | 129 | 129 | **0** ✅ |
| Codes géographiques cohérents | 129 / 129 | — | ✅ |

**Répartition par province :**

| Province | Urbain | Rural | Mixte |
|---|---:|---:|---:|
| Al Hoceima | 5 | 14 | 17 |
| Chefchaouen | 1 | 22 | 5 |
| Fahs-Anjra | 0 | 0 | 7 |
| Larache | 2 | 5 | 12 |
| Ouezzane | 1 | 9 | 7 |
| Tanger-Assilah | 3 | 2 | 7 |
| Tétouan | 2 | 17 | 3 |
| M'diq-Fnideq | 3 | 0 | 2 |

> **Note intéressante :** la province de **Chefchaouen** est celle qui compte le plus de communes purement rurales (22 sur 28). C'est le cœur du problème d'accès aux soins dans la région — et un excellent candidat pour le cas d'étude.

---

## 7. Anomalies et limites — à assumer honnêtement

| # | Anomalie / limite | Gravité | Traitement |
|---|---|---|---|
| 1 | **Surface calculée = 16 644 km²** alors que les monographies HCP annoncent ≈ 15 000–16 000 km² | Moyenne | La surface est marquée `ESTIME` et **n'est jamais présentée comme officielle**. Densités données à titre indicatif uniquement. |
| 2 | **Géométries simplifiées** (tuilage zoom 7) : frontières non cadastrales | Moyenne | Documenté dans `SOURCES.md`. Suffisant pour une carte, insuffisant pour du foncier. |
| 3 | **Zéros initiaux perdus** dans le fichier Excel des douars (province 051 : 12 caractères au lieu de 13) | Élevée (silencieuse) | Correction codée et testée. C'est le piège le plus dangereux du projet. |
| 4 | **Population légale ≠ population présente** | Moyenne | Mentionné dans le dictionnaire des données. Une commune peut avoir une population saisonnière bien supérieure. |
| 5 | **Code Tanger atypique** (`01.511.01.0`) | Élevée | Décision D-007 prise et vérifiée (écart 0). |
| 6 | **Licence HCP non confirmée** | Bloquante pour la publication | À clarifier auprès de l'encadrant — voir §9. |

---

## 8. Liste des contrôles automatiques (15 / 15 au vert)

### Référentiel (6)
- [x] Clé `commune_code` unique au niveau géométries (149)
- [x] Clé unique au niveau communal HCP (146)
- [x] Tous les noms français renseignés
- [x] Toutes les provinces reconnues (8/8)
- [x] Toutes les coordonnées dans l'emprise de la région
- [x] Nombre de communes conforme au HCP (146)

### Démographie (5)
- [x] 146 / 146 communes appariées à une population officielle
- [x] Clé unique après jointure
- [x] Population totale = 4 030 222 (officiel)
- [x] Ménages totaux = 1 048 860 (officiel)
- [x] Tanger = somme exacte de ses 4 arrondissements

### Milieu et livrable (4)
- [x] Population rurale = 1 382 463 (officiel)
- [x] Ménages ruraux = 320 093 (officiel)
- [x] Codes géographiques HCP cohérents (129/129)
- [x] Aucune valeur manquante dans le livrable final

Fichiers de preuve : `data/reference/qc_referentiel.json`, `qc_demographics.json`, `qc_milieu.json`.

---

## 9. Ce qui reste à clarifier

| Point | Responsable | Échéance |
|---|---|---|
| Licence HCP : usage et redistribution autorisés ? | Encadrant / Membre A | Cette semaine |
| Licence OSM (ODbL) : mention « © OpenStreetMap contributors » | Membre B | Semaine 2 |
| Attribution Copernicus/ERA5 pour la météo | Membre C | Semaine 2 |
| Validation indépendante des noms et codes (tâche A-6) | Membre A | 13 novembre |

---

## 10. Fichiers livrés

| Fichier | Contenu | Destinataire |
|---|---|---|
| `data/processed/communes_TTA_2024_livrable.csv` | **La table finale** : 146 communes, population, milieu, coordonnées | B et C |
| `data/processed/communes_TTA_2024_points.geojson` | 146 points (centroïdes) — léger pour l'app | B |
| `data/reference/communes_TTA_146.csv` | Référentiel sans démographie | C (pipeline) |
| `data/reference/communes_TTA.geojson` | Polygones complets (149 entités) | B (carte) |
| `data/reference/demographics.csv` | Démographie détaillée avec urbain/rural | A |
| `data/reference/qc_*.json` | Preuves des contrôles qualité | Rapport / jury |
| `docs/figures/*.png` | 4 cartes prêtes pour le rapport | Rapport / pitch |

---

*Rapport généré le 11 novembre 2026 — Membre A. Reproductible via `src/build_*.py`.*

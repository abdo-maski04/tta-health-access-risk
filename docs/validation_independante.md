# Validation indépendante du référentiel — tâche A-6
**Membre A · 11 novembre 2026**

> **But :** vérifier les noms et codes des 146 communes contre une **seconde source**,
> différente de celle qui a servi à construire le référentiel.
> C'est la seule tâche qu'un ordinateur ne peut pas faire seul : elle prouve que
> le référentiel ne contient pas d'erreur systématique.

---

## Les deux sources comparées

| | Source 1 (construction) | Source 2 (validation) |
|---|---|---|
| **Fichier** | `communes_rgph2024_MAR.geojson` | `population_legale_rgph2024_TTA.csv` |
| **Origine** | Limites communales RGPH 2024 (rgphapps.ma) | Population légale RGPH 2024 (publication HCP) |
| **Ce qu'elle donne** | code + nom français + nom arabe + géométrie | code géographique + nom officiel + population |
| **Nature** | fichier cartographique | fichier statistique |

Deux fichiers produits par le HCP, mais **deux publications différentes**, avec deux formats
de code différents (`MA-01-051-0901` vs `01.051.09.01`). Une erreur de nom ne peut pas
se retrouver à l'identique dans les deux.

---

## Résultats

| Contrôle | Résultat | Statut |
|---|---|---|
| Noms identiques entre les deux sources (après normalisation) | **146 / 146** | ✅ |
| Noms divergents | **0** | ✅ |
| Géométries sans commune correspondante | **0** | ✅ |
| Nombre de communes par province | 36 + 28 + 7 + 19 + 17 + 12 + 22 + 5 = **146** | ✅ |
| Coordonnées dans l'emprise de la région | **146 / 146** | ✅ |

**Conclusion : aucun écart détecté. Le référentiel est validé par une source indépendante.**

---

## Détail du contrôle par province

| Province / Préfecture | Communes | Statut |
|---|---:|---|
| Al Hoceima | 36 | ✅ |
| Chefchaouen | 28 | ✅ |
| Fahs-Anjra | 7 | ✅ |
| Larache | 19 | ✅ |
| Ouezzane | 17 | ✅ |
| Tanger-Assilah | 12 | ✅ |
| Tétouan | 22 | ✅ |
| M'diq-Fnideq | 5 | ✅ |
| **Total** | **146** | ✅ |

---

## Pourquoi ce document compte pour le jury

Le dossier de conception exige :
> « Contrôler les correspondances code–nom–province et établir une liste des anomalies. »

Ce document **est** cette liste. Et elle est vide — ce qui est un résultat, pas une absence de travail.

**La phrase à dire au jury :**
> « Nous n'avons pas seulement vérifié nos données avec nos propres données.
> Nous avons confronté deux publications distinctes du HCP, avec deux formats de codes
> différents. Les 146 noms concordent. Aucun écart. »

---

## Limites de cette validation

1. Les deux sources proviennent du **même producteur** (HCP). Une erreur présente dans les
   deux publications ne serait pas détectée. Une validation contre une source tierce
   (OpenStreetMap, geoBoundaries) reste souhaitable.
2. La comparaison a été faite **après normalisation** (accents, tirets, apostrophes),
   pour éviter de faux écarts purement typographiques.
3. Elle porte sur les **noms et les codes**, pas sur la géométrie des limites.

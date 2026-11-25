# Anomalies du referentiel — et comment elles sont traitees

> Tenu par le **Membre A**. Date : 2026-11-25. Ce document repond a la tache **A-12**.
> Regle : une anomalie n'est supprimee que si elle est expliquee. Aucune valeur inventee.

## 1. 150 geometries -> 146 communes officielles

| # | Cause | Effet | Traitement |
|---|---|---|---|
| 1 | **Ceuta** (`MA-01-573-0100`, « Sebta ») figure dans le jeu national | +1 | **Exclue** : hors souverainete marocaine, hors perimetre du datathon |
| 2 | **Tanger** livree en **4 arrondissements** (Bni Makada, Mghogha, Souani, Medina) alors que le HCP la compte pour **1 commune** | +3 | **Agreges** sous une cle unique, population sommee |

Resultat : 146 communes, identiques au decoupage HCP (2 prefectures + 6 provinces).

## 2. Population

| Anomalie | Traitement |
|---|---|
| Population **legale** et non population presente | Documente comme limite ; la saisonnalite n'est pas modelisee |
| Millesimes melanges (RGPH 2014 pour l'historique, RGPH 2024 pour la reference) | La colonne publiee est `population_2024` ; le fichier 2014 reste dans `data/raw/` |
| Somme regionale | **4 030 222** habitants, verifiee sur les 146 lignes |

## 3. Milieu de residence

Le HCP annonce **17 communes urbaines et 129 rurales**. Notre fichier contient
**17 urbaines, 60 mixtes et 69 rurales**. Ecart explique : la categorie `Mixte`
(D-006) separe les communes qui ont des douars urbains **et** ruraux ; elle n'existe pas
dans la nomenclature HCP. La somme reste 146.

## 4. Etablissements de sante

| Anomalie | Traitement |
|---|---|
| **5 hopitaux sans nom** sur 66 (OSM) | Conserves : position valide, identifiant OSM stable, le nom n'entre dans aucun calcul |
| **16 hopitaux officiels sur 24** retrouves par le nom | Documente ; les 8 autres ne sont pas geolocalises et ne sont pas inventes |
| Aucun `health_post` (dispensaire) dans OSM | Limite majeure assumee : le milieu rural est sous-represente (cf. 299 etablissements du MSPS) |
| Pas de hierarchie officielle ni de capacite | Non disponible en open data ; le score ne depend que du **temps** |

## 5. Temps de trajet et accessibilite

| Anomalie | Traitement |
|---|---|
| Temps « normaux », sans trafic ni route coupee | Documente ; la variante « route coupee » est un scenario du rapport, pas une donnee |
| Communes tres isolees | 38 communes a plus de 60 min ; maximum **120,2 min** (Tamorot, Chefchaouen) |
| 5 hopitaux sans nom utilises comme destination | Aucun impact : le temps est calcule vers un point, pas vers un nom |
| Bornes 15 / 45 min | Sensibilite faite sur 6 variantes : 91 communes changent de classe, le classement ne change pas (D-015) |

## 6. Codes et noms

| Anomalie | Traitement |
|---|---|
| Zero initial dans les codes (`051`) | Tous les codes sont lus en **texte** ; jamais de jointure sur le nom |
| Meme commune ecrite de plusieurs facons (M'diq / Mdiq / المضيق) | Jointure uniquement sur `commune_code` ; `name_fr` sert a l'affichage |

## 7. Ce qu'il reste a faire

- Confirmer la **licence HCP** (D-010) avant toute redistribution.
- Geocoder les **8 hopitaux officiels** manquants.
- Integrer la liste MSPS (`essp-2025.xlsx`) pour couvrir le milieu rural.

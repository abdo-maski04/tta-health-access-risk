# Rapport de qualité des données météorologiques

**Projet :** TTA Health Access Risk — accès aux soins en région Tanger-Tétouan-Al Hoceima
**Auteur :** membre A · **Date :** 28 novembre 2026 · **Statut :** PROVISIONAL
**Périmètre :** tables `weather.weather_daily` (historique) et `weather.thresholds` (seuils dérivés)
**Objet :** répondre au livrable « rapport de qualité des données météorologiques » (vérification
de la période, de la couverture, des doublons, des valeurs manquantes, des plages, des unités et de la source).

---

## 1. Source et méthode d'acquisition

| Élément | Valeur |
|---|---|
| Fournisseur | Open-Meteo, **Historical Weather API** (`https://archive-api.open-meteo.com/v1/archive`) |
| Données d'origine | réanalyses **ERA5** et **ERA5-Land** (programme Copernicus / ECMWF) |
| Résolution spatiale | maille de **0,25° (~25 km)** pour ERA5, **0,1° (~11 km)** pour ERA5-Land ; modèle `best_match` = mélange des deux |
| Variables demandées | `precipitation_sum` (**mm par jour**) et `temperature_2m_max` (**°C**) |
| Période demandée | `2016-01-01` → `2025-12-31`, soit **3 653 jours** par commune |
| Fuseau horaire | `Africa/Casablanca` |
| Clé API | **aucune** — accès libre et gratuit |
| Téléchargement | le 27 novembre 2026, par le module `src/tta_risk/weather/load_history.py` (propriété B, non modifié) |
| Volume obtenu | **146 communes × 3 653 jours = 533 338 lignes** |
| Stockage | PostgreSQL, conteneur `postgres_tta_risk`, base `tta_risk`, table `weather.weather_daily` |

**Reproductibilité.** L'acquisition se rejoue avec une seule commande (environ 2 h, quota Open-Meteo oblige) :

```bat
python -m src.tta_risk.weather.load_history
```

---

## 2. Les sept contrôles effectués

| # | Contrôle | Résultat | Verdict |
|---|---|---|---|
| 1 | Période couverte et volume | 146 communes · 533 338 lignes · du **2016-01-01** au **2025-12-31** | ✅ conforme |
| 2 | Communes incomplètes (moins de 3 653 jours) | **0** | ✅ conforme |
| 3 | Doublons (même commune, même date) | **0** | ✅ conforme |
| 4 | Valeurs manquantes | pluie : **0** · température : **0** | ✅ conforme |
| 5 | Plages physiques | pluie **0 → 139,3 mm/jour** · tmax **−1,0 → 48,9 °C** | ✅ plausible |
| 6 | Seuils non calculables | pluie : **270 mois** · chaleur : **0 mois** | ⚠️ limite à documenter |
| 7 | Répartition des mois sans seuil de pluie | **juin : 5 · juillet : 141 · août : 124** | ⚠️ concentrés en été |

Les requêtes SQL utilisées sont données en annexe (§ 7).

---

## 3. Constats détaillés

### 3.1 Couverture : parfaite
146 × 3 653 = **533 338** lignes attendues, 533 338 obtenues. **Aucune commune ne présente de trou**,
et les bornes de la période sont exactes. Aucun doublon : la clé primaire `(commune_code, date)` joue
son rôle. Ce niveau de complétude est inhabituel et vient du fait que chaque commune a été téléchargée
en un seul appel couvrant les dix ans.

### 3.2 Valeurs manquantes : aucune
Les deux variables sont renseignées sur **100 %** des lignes. C'est le point qui n'était **pas contrôlé
par le pipeline** (voir § 5) : le résultat est bon, mais il aurait pu ne pas l'être sans que personne
ne s'en aperçoive.

### 3.3 Plages physiques : plausibles
- **Pluie** : de 0 à **139,3 mm/jour**. Un cumul journalier de 139 mm correspond à un épisode de pluie
  intense, cohérent avec le climat rifain.
- **Température maximale** : de **−1,0 °C** (nuit d'hiver en montagne, Chefchaouen) à **48,9 °C**
  (vague de chaleur). Ces deux extrêmes sont physiquement admissibles mais méritent d'être nommés :
  une valeur de 48,9 °C est rare sous ce climat et peut provenir de la réanalyse plutôt que d'une
  mesure de station.

### 3.4 Les 270 mois sans seuil de pluie
Le calcul des seuils de pluie n'est fait que sur les **jours pluvieux** (≥ 1 mm) et seulement si le
mois compte **au moins 20 jours de pluie sur dix ans** (garde-fou `MIN_RAIN_DAYS = 20` dans
`src/tta_risk/weather/thresholds.py`). Dans **270 des 1 752 couples commune-mois (15,4 %)**, cette
condition n'est pas remplie :

| Mois | Communes sans seuil de pluie | Part des 146 |
|---|---|---|
| Juin | 5 | 3 % |
| Juillet | **141** | 97 % |
| Août | **124** | 85 % |
| Total | **270** | — |

**Conséquence assumée.** En l'absence de seuil, le niveau de danger pluie est fixé à **0** par
construction. Autrement dit : **en juillet et en août, l'indicateur repose uniquement sur la chaleur**
pour la quasi-totalité des communes. Ce n'est pas une erreur — moins de 20 jours de pluie en dix ans
signifie que la pluie n'a jamais été un facteur de risque mesurable — mais c'est une propriété de
l'indicateur qui doit être écrite noir sur blanc, faute de quoi un lecteur conclura à tort que « la
pluie n'a pas d'effet en été » au lieu de « la pluie n'est pas mesurable en été ».

**Point rassurant** : aucun mois d'automne ou d'hiver n'est concerné. La saison où la pluie compte
vraiment (novembre à mars) dispose de seuils complets pour les 146 communes.

---

## 4. Limites de la source (à écrire dans le rapport final)

| Limite | Effet sur l'indicateur |
|---|---|
| **Réanalyse, pas mesure de station** | la valeur d'une commune est celle de la **maille** qui la contient (11 à 25 km). En montagne (Chefchaouen, Al Hoceima), la pluie réelle d'un village peut différer sensiblement de la valeur utilisée. |
| **Pluie journalière uniquement** | aucune information sur l'intensité horaire, alors que c'est l'intensité qui provoque les crues et coupe les routes. |
| **Chaleur = `tmax` seule** | l'humidité et la température nocturne, déterminantes pour le risque sanitaire, ne sont pas prises en compte : un 38 °C sec et un 38 °C humide sont traités à l'identique. |
| **Pas de pondération par la vulnérabilité** | l'indicateur compte des habitants, pas des personnes fragiles (âge, grossesse, pathologie). |
| **Antériorité du téléchargement** | les données ont été figées le 27/11/2026. Open-Meteo révise ses réanalyses : un nouveau téléchargement peut produire des seuils légèrement différents. |

---

## 5. Points à corriger dans le pipeline (propriété B — signalés, non modifiés)

Conformément à la règle « ne pas modifier la logique météo d'Abderrahmane », ces points sont
**documentés et transmis**, pas corrigés ici.

| # | Constat | Risque |
|---|---|---|
| 1 | **Aucun contrôle des valeurs nulles** : `precipitation_sum` et `temperature_2m_max` acceptent `NULL`, aucun test ne le vérifie. | une valeur vide deviendrait silencieusement « pas de danger » |
| 2 | **Aucun contrôle des plages physiques** (pluie ≥ 0, tmax entre −20 et 55 °C). | une valeur aberrante entrerait dans les seuils |
| 3 | **La chaleur n'a pas de garde-fou de jours manquants** : `MIN_RAIN_DAYS` protège la pluie, mais un `heat_p90` serait calculé même sur un mois incomplet. | faux seuil silencieux (sans effet aujourd'hui : 0 mois concerné, cf. contrôle 6) |
| 4 | **`already_loaded()`** considère une commune complète si `count(*) = 3653` ; une commune à 3 652 jours serait retéléchargée à chaque exécution sans jamais déclencher d'alerte. | boucle silencieuse |
| 5 | **Documentation** : `python scripts\build_thresholds.py` ne fonctionne pas (import `src` introuvable) ; il faut `python -m scripts.build_thresholds`. Idem pour `run_risk_daily`. | commande du README inopérante |

---

## 6. Verdict

> **Données conformes, limites documentées.**
>
> Les 533 338 lignes couvrent exactement la période et les 146 communes demandées, sans doublon ni
> valeur manquante, avec des plages physiquement plausibles. Le seul écart au cahier des charges est
> **la non-mesurabilité de la pluie en été** (270 couples commune-mois, 15,4 %), qui découle d'une
> règle explicite et non d'un défaut de données.
>
> En revanche, **le pipeline ne contrôle ni les valeurs nulles, ni les plages, ni les jours manquants
> pour la chaleur** : la qualité constatée aujourd'hui doit donc être vérifiée par des tests
> automatiques, pas supposée. Ces points relèvent du module d'ingestion (propriété B).

**Statut PROVISIONAL.** Ce rapport porte sur la méthode météo telle qu'elle est livrée dans `main`
au 28/11/2026. La méthode étant en cours de révision par le membre B (couverture, valeurs manquantes,
combinaison pluie/chaleur), les constats 1 à 4 du § 5 devront être revérifiés après sa correction.

---

## 7. Annexe — les requêtes de contrôle

```sql
-- 1. Période et volume
SELECT count(DISTINCT commune_code) AS communes, count(*) AS lignes,
       min(date) AS debut, max(date) AS fin
FROM weather.weather_daily;

-- 2. Communes incomplètes (moins de 3653 jours)
SELECT count(*) AS communes_incompletes
FROM (SELECT commune_code FROM weather.weather_daily
      GROUP BY 1 HAVING count(*) <> 3653) t;

-- 3. Doublons
SELECT count(*) AS doublons
FROM (SELECT commune_code, date FROM weather.weather_daily
      GROUP BY 1, 2 HAVING count(*) > 1) t;

-- 4. Valeurs manquantes
SELECT count(*) FILTER (WHERE precipitation_sum IS NULL)  AS pluie_nulle,
       count(*) FILTER (WHERE temperature_2m_max IS NULL) AS tmax_nulle
FROM weather.weather_daily;

-- 5. Plages physiques
SELECT min(precipitation_sum) AS pluie_min, max(precipitation_sum) AS pluie_max,
       min(temperature_2m_max) AS tmax_min, max(temperature_2m_max) AS tmax_max
FROM weather.weather_daily;

-- 6. Seuils non calculables
SELECT count(*) FILTER (WHERE rain_p90 IS NULL) AS mois_sans_seuil_pluie,
       count(*) FILTER (WHERE heat_p90 IS NULL) AS mois_sans_seuil_chaleur
FROM weather.thresholds;

-- 7. Répartition par mois des seuils de pluie manquants
SELECT month, count(*) AS mois_sans_seuil_pluie
FROM weather.thresholds WHERE rain_p90 IS NULL
GROUP BY 1 ORDER BY 1;
```

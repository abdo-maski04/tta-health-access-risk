# RAPPORT DE QUALITÉ ET CONTRÔLE DE COHÉRENCE DU RSC-TTA
## Référentiel Sanitaire Consolidé de la Région Tanger-Tétouan-Al Hoceïma (Version Post-Corrections)

**Projet :** GeoVulnera TTA — Analyse de vulnérabilité climatique et accessibilité aux soins  
**Région :** Tanger-Tétouan-Al Hoceïma (146 communes)  
**Date de mise à jour :** 23 Novembre 2026  
**Auditeur / Data Engineer :** Senior Data Engineer & Data Quality Engineer  
**Statut global :** **RSC-TTA VALIDÉ** — Intégrité, traçabilité et reproductibilité démontrées  

---

## 1. DATE, STATUT ET PÉRIMÈTRE DE LA NOUVELLE GÉNÉRATION

* **Date d'exécution :** 23 Novembre 2026.
* **Statut :** Régénération complète post-corrections réussie sans aucune régression.
* **Périmètre d'action :**
  * Sources ministérielles archivées de façon permanente sous `data/raw/ministere_sante/`.
  * Script de génération `scripts/data_preparation/build_rsc_tta.py` rendu 100 % autonome et relatif à `BASE_DIR`.
  * Matching hospitalier corrigé et fiabilisé avec preuve matérielle dans les données OSM.
  * Réconciliation arithmétique rigoureuse des pharmacies (776 initiales, 45 hors région, 722 nommées, 9 anonymes).
  * Protection absolue : 0 modification sur les données territoriales de Hakima (`data/processed/`) et sur l'application (`app/`).

---

## 2. SOURCES UTILISÉES ET CHEMINS D'ACCÈS PERMANENTS

Toutes les sources sont désormais intégrées de manière pérenne et reproductible au sein du dépôt Git :

| Identifiant | Rôle métier | Chemin permanent relatif au dépôt | Volumétrie brute |
|---|---|---|---|
| `SRC-COM` | Référentiel pivot des communes (RGPH 2024) | `data/processed/communes_TTA_2024.csv` | 146 lignes, 25 colonnes |
| `SRC-GEO` | Contours vectoriels WGS84 des communes | `data/processed/communes_TTA.geojson` | 146 entités géographiques |
| `SRC-OSM` | Infrastructures sanitaires OpenStreetMap | `data/processed/health_facilities_TTA.csv` | 892 lignes, 13 colonnes |
| `SRC-MIN-NAT` | Statistiques nationales privé (Benchmark) | `data/raw/ministere_sante/private_infrastructures_national_2025.csv` | 9 lignes, 2 colonnes |
| `SRC-MIN-COM` | Synthèse communale officielle 2025 | `data/raw/ministere_sante/official_public_health_by_commune_2025.csv` | 146 lignes, 9 colonnes |
| `SRC-MIN-FAC` | Répertoire granulaire public officiel 2025 | `data/raw/ministere_sante/official_public_health_tta_2025.csv` | 323 lignes, 12 colonnes |

---

## 3. FICHIERS CONSOLIDÉS PRODUITS DANS `data/interim/`

| Fichier produit | Description | Nombre de lignes | Colonnes |
|---|---|---|---|
| `data/interim/communes_health_profile_TTA.csv` | Profil communal sanitaire consolidé (146 communes) | **146** | 21 colonnes |
| `data/interim/health_facilities_master_TTA.csv` | Registre unifié de toutes les structures sanitaires | **1 215** | 19 colonnes |
| `data/interim/health_facility_matching_audit_TTA.csv` | Journal d'audit du rapprochement des 24 hôpitaux | **24** | 9 colonnes |

---

## 4. CONTRÔLE COMMUNAL (146 COMMUNES)

* **Complétude :** 146 communes sur 146 répertoriées (100,0 %).
* **Unicité :** 146 `commune_code` uniques, aucune valeur nulle ou dupliquée.
* **Intégrité toponymique :** Normalisation réussie des 4 alias historiques (`bni abdallah` ➔ `Bni Abdellah`, `bou jedyane` ➔ `Boujedyane`, `moqrisset` ➔ `Moqrissat`, `ounnana` ➔ `Ouannana`).
* **Communes orphelines :** 0 commune non rapprochée.

---

## 5. CONTRÔLE DE L'OFFRE PUBLIQUE OFFICIELLE (323 STRUCTURES)

Les 323 structures du Ministère de la Santé sont intégralement préservées avec leur nomenclature officielle marocaine :

| Catégorie officielle | Code | Effectif consolidé | Vérification agrégat communal | Statut |
|---|---|---|---|---|
| Centres de Santé Urbains Niveau 1 | `CSU-1` | 74 | $74 + 13 = 87$ CSU | **Concordance parfaite** |
| Centres de Santé Urbains Niveau 2 | `CSU-2` | 13 | | |
| Centres de Santé Ruraux Niveau 1 | `CSR-1` | 64 | $64 + 68 = 132$ CSR | **Concordance parfaite** |
| Centres de Santé Ruraux Niveau 2 (Maternités) | `CSR-2` | 68 | | |
| Dispensaires Ruraux | `DR` | 63 | $63$ DR | **Concordance parfaite** |
| Hôpitaux Publics (HP, HR, HPr, HIR, CPU, CRO, HPsy) | Divers | 24 | $24$ Hôpitaux | **Concordance parfaite** |
| Centres Spécialisés et Laboratoires (CDTMR, CRSR, LSP) | Divers | 17 | $17$ Spécialisés | **Concordance parfaite** |
| **Total Régional Public Officiel** | — | **323** | **323 Structures** | **Écart = 0** |

---

## 6. RAPPROCHEMENT HOSPITALIER : BILAN AVANT / APRÈS CORRECTIONS

Le tableau ci-dessous retrace les corrections de matching apportées aux 24 hôpitaux publics :

| Facility ID ministériel | Établissement ministériel | Commune / Arrondissement | OSM ID Initial (Errone) | OSM ID Final (Vérifié) | Nom OSM réel vérifié | Statut de validation final |
|---|---|---|---|---|---|---|
| `PUB-TTA-MA-01-051-008` | Mohammed VI (HP) | Ait Youssef Ou Ali | `8377190516` | `8377190516` | Centre Hospitalier Provincial Mohammed VI | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-051-016` | C. d'oncologie (CRO) | Al Hoceima (Mun.) | `12846726229` | `12846726229` | C. d'oncologie d'Al Hoceima | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-051-019` | Mohamed V (HP) | Al Hoceima (Mun.) | `789174103` | `789174103` | Hôpital Mohamed V | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-051-043` | Imzouren (HPr) | Imzouren (Mun.) | `10920276384` | `10920276384` | Health Center Imzouren | `MATCH_CANDIDATE` (Pas de GPS) |
| `PUB-TTA-MA-01-051-065` | Targuist (HPr) | Targuist (Mun.) | `789267614` | `789267614` | مستشفى حمان الفطواكي ايت عزة | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-151-100` | Mohamed V (HP) | Chefchaouen (Mun.) | `305583432` | `305583432` | Hopital Mohamed V | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-331-143` | Ksar El Kebir (HPr) | Ksar El Kebir (Mun.)| `789778445` | `789778445` | Hopital Provincial de Ksar El Kébir | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-331-156` | Lalla Meriem (HP) | Larache (Mun.) | `12815056754` | `12815056754` | Hôpital Princesse Lalla Meriem | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-573-178` | Hassan II (HPr) | Fnideq (Mun.) | `None` | `None` | *(Absent d'OSM)* | `NO_MATCH` (Pas de GPS) |
| `PUB-TTA-MA-01-573-182` | Mohammed VI (HP) | M'Diq (Mun.) | `293247182` | `293247182` | Hopital Mohamed 6 | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-405-206` | Abou Kacem Zahraoui (HP)| Ouezzane (Mun.) | `12815486730` ❌ | `12815486724` ✅ | Projet Centre Hospitalier Provincial d'Ouezzane | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-511-230` | Assilah (HPr) | Assilah (Mun.) | `789182377` ❌ | `12815618481` ✅ | Hôpital (Assilah) | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-511-235` | Hôpital spécialités (HIR)| Gueznaia (Mun.) | `12836262451` ❌ | `871505068` ✅ | CHU de Tanger-Tétouan-Al Hoceima | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-511-236` | Hôpital mère-enfant (HIR)| Gueznaia (Mun.) | `None` | `None` | *(Campus CHU Gueznaia)* | `MATCH_CANDIDATE` (Pas de GPS) |
| `PUB-TTA-MA-01-511-237` | Hôpital psychiatrique (CPU)| Gueznaia (Mun.) | `None` | `None` | *(Campus CHU Gueznaia)* | `MATCH_CANDIDATE` (Pas de GPS) |
| `PUB-TTA-MA-01-511-246` | Al Kortobi (HR) | Tanger (Al Madina) | `358688501` (décalé)| `358688501` ✅ | hôpital al kortobi | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-511-248` | Arrazi (HPsyR) | Tanger (Mghogha) | `475665966` ❌ | `13770363904` ✅ | مصحة الرازي | `MATCH_CANDIDATE` (Pas de GPS) |
| `PUB-TTA-MA-01-511-257` | Centre d'oncologie (HIR)| Tanger (Al Madina) | `12836262446` ❌ | `587335799` ✅ | Centre Ahmad Bin Zayed Al Nahyan Cancers | `MATCH_CANDIDATE` (Pas de GPS) |
| `PUB-TTA-MA-01-511-260` | Duc De Tovar (HR) | Tanger (Al Madina) | `564951388` | `564951388` | Hôpital Espagnol | `MATCH_CANDIDATE` (Pas de GPS) |
| `PUB-TTA-MA-01-511-270` | Mohamed V (HR) | Tanger (Al Madina) | `NO_MATCH` ❌ | `122398955` ✅ | Hôpital Mohammed V Tanger | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-511-271` | Mohammed Vi (HPr) | Tanger (Bni Makada) | `NO_MATCH` ❌ | `475665966` ✅ | Hôpital Mohammed VI Bni Makada | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-571-290` | Ben Karrich (HP) | Dar Bni Karrich | `1242229574` | `1242229574` | Hospital Ben Karrich | `MATCH_MANUAL_VERIFIED` |
| `PUB-TTA-MA-01-571-306` | Errazi (HPsyP) | Tétouan (Mun.) | `None` | `None` | *(Absent d'OSM)* | `NO_MATCH` (Pas de GPS) |
| `PUB-TTA-MA-01-571-307` | Hôpital.Civil / Sanyat Rmel | Tétouan (Mun.) | `484204214` | `484204214` | Hôpital Sanyat Rmel Tétouan | `MATCH_MANUAL_VERIFIED` |

### Synthèse du rapprochement après corrections :
* **Correspondances manuelles vérifiées (`MATCH_MANUAL_VERIFIED`) :** **16 hôpitaux** (au lieu de 11 initialement).
* **Correspondances candidates en attente (`MATCH_CANDIDATE`) :** **6 hôpitaux** (aucune coordonnée transmise sans levé de doute formel).
* **Absences avérées d'OSM (`NO_MATCH`) :** **2 hôpitaux** (`Hassan II Fnideq` et `Errazi Tétouan`).
* **Doublons OSM neutralisés dans le Master :** Exactement **16 entités OSM** marquées `RECONCILED_PUBLIC_DUPLICATE`.
* **Égalité stricte :** Nombre de matches manuels vérifiés (16) = Nombre de doublons OSM neutralisés (16).

---

## 7. RÉCONCILIATION ARITHMÉTIQUE DES PHARMACIES

L'audit a permis d'éclaircir intégralement la chaîne de calcul des pharmacies OSM :

```
    Source OSM brute (health_facilities_TTA.csv) :                     776 pharmacies
    ─────────────────────────────────────────────────────────────────────────────────
    - Pharmacies situées HORS région TTA (Ceuta: 15, Driouch: 27, etc.) : 45 pharmacies
    ─────────────────────────────────────────────────────────────────────────────────
    = Total des pharmacies situées DANS les 146 communes de TTA :       731 pharmacies
      ├── Pharmacies nominatives qualifiées (PRIVATE_VALID) :            722 pharmacies
      └── Pharmacies anonymes sans nom OSM (UNVERIFIED) :                  9 pharmacies
    ─────────────────────────────────────────────────────────────────────────────────
    Somme de contrôle : 722 (nommées) + 9 (anonymes) + 45 (hors région) = 776 pharmacies.
```

* **Explication de l'ancien écart des 9 pharmacies :**
  Dans la version initiale, les 9 officines sans nom (`name IS NULL`) avaient été orientées vers `ANONYMOUS_UNVERIFIED`. Elles sont bien présentes dans le polygone communal de TTA et comptabilisées dans le profil communal (`osm_pharmacies_mapped = 731`), mais isolées dans la couche `UNVERIFIED` du Master car un établissement sans raison sociale ne peut être certifié comme officine commerciale validée.

---

## 8. QUALIFICATION DE LA TABLE MASTER (1 215 LIGNES)

### A. Ventilation par statut et secteur juridique
* **`PUBLIC_CORE` (339 lignes) :**
  * 323 structures publiques officielles ministérielles (dont 16 dotées de GPS réconcilié et 307 sans GPS).
  * 16 nœuds OSM d'hôpitaux publics réconciliés (`validation_status = 'RECONCILED_PUBLIC_DUPLICATE'`).
* **`PRIVATE_VALID` (769 lignes) :**
  * 722 pharmacies nominatives géolocalisées.
  * 16 cliniques privées / cabinets de soins.
  * 17 cabinets médicaux libéraux (`doctors`).
  * 3 laboratoires d'analyses médicales.
  * 11 cliniques privées déclarées comme hôpitaux dans OSM (ex. `AKDITAL Tanger`, `Clinique Bades`).
* **`UNVERIFIED` (107 lignes) :**
  * 66 points situés hors région TTA (`OUTSIDE_REGION_TERRITORY`).
  * 12 points anonymes dans TTA (9 pharmacies + 2 hôpitaux + 1 unspecified).
  * 29 structures hospitalières OSM non homologuées / en attente.

### B. Distinction entre lignes de la table et établissements physiques réels
$$\text{Total lignes Master} (1\,215) = \text{Établissements physiques TTA} (1\,092) + \text{Lignes techniques d'audit} (123)$$
* **1 092 établissements physiques opérationnels dans la région TTA :** 323 publics + 769 privés validés.
* **123 lignes techniques d'audit / neutralisées :** 16 doublons publics + 66 hors région + 12 anonymes + 29 indéterminées.

---

## 9. COORDONNÉES GPS ET GESTION DES 195 STRUCTURES RURALES

* **Structures avec coordonnées réelles WGS84 :** **908** entités (892 OSM + 16 hôpitaux publics réconciliés).
* **Validité spatiale :** 100 % des coordonnées sont valides, comprises dans la boîte englobante marocaine (lat: 34.80° à 35.89°, lon: -6.29° à -3.38°). Zéro coordonnée (0,0), zéro inversion lat/lon.
* **Structures rurales de premier recours (68 CSR-2, 64 CSR-1, 63 DR) :**
  * Les **195 structures rurales** conservent rigoureusement :
    * `has_gps = False`
    * `lat = ""` (NULL)
    * `lon = ""` (NULL)
    * `geocode_precision = 'UNLOCATED'`
  * **Aucun centroïde communal fictif n'a été injecté.**

---

## 10. RÉSULTATS DES CONTRÔLES D'INTÉGRITÉ POST-CORRECTIONS

| Point de contrôle | Résultat constaté | Verdict |
|---|---|---|
| Nombre de communes consolidées | 146 sur 146 | **CONFORME** |
| Unicité des `commune_code` | 146 uniques (0 doublon, 0 null) | **CONFORME** |
| Établissements publics ministériels | 323 sur 323 | **CONFORME** |
| Cohérence arithmétique communale | $\text{Primary} + \text{Hosp} + \text{Spec} == \text{Total}$ (146/146) | **CONFORME** |
| Hôpitaux avec GPS réconcilié | 16 sur 24 | **CONFORME** |
| Doublons OSM neutralisés | 16 sur 16 | **CONFORME** |
| Réconciliation pharmacies | $722 + 9 + 45 = 776$ | **CONFORME** |
| Reste rural sans GPS fictif | 195 sur 195 (`UNLOCATED`) | **CONFORME** |
| Protection données de Hakima | `data/processed/` intact (0 octet modifié) | **CONFORME** |
| Reproductibilité du script | Autonome via `data/raw/ministere_sante/` | **CONFORME** |

---

## CONCLUSION ET RECOMMANDATIONS

Le Référentiel Sanitaire Consolidé (RSC-TTA) est désormais **pleinement stabilisé, mathématiquement exact et audité**. Il constitue une base de référence saine pour l'enrichissement futur des pages Streamlit et pour les phases ultérieures de modélisation du réseau routier sous OpenRouteService.

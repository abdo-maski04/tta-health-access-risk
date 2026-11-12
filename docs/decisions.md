# decisions.md — Journal des décisions méthodologiques

> Une décision non écrite n'existe pas. Chaque entrée : date, décideur, décision, alternatives écartées, raison, conséquence.
> Le dossier de conception exige que la proposition initiale reste la référence **tant qu'une décision écrite ne la remplace pas**.

---

## D-001 — Périmètre communal : 146 communes (niveau officiel HCP)
**Date :** 2026-11-11 · **Décideur :** Membre A · **Statut :** ✅ adoptée

**Contexte.** Le fichier de géométries RGPH 2024 contient 150 entités dans la région MA-01, alors que le découpage administratif officiel (décret du 20 février 2015) dénombre **146 communes** (17 urbaines, 129 rurales) réparties en 2 préfectures et 6 provinces.

**Décision.** Le dénominateur officiel du projet est **146 communes**.
- Les géométries sont conservées au niveau fin (149 après exclusion de Ceuta) pour l'affichage cartographique.
- Tous les **comptages, scores et agrégats** utilisent la colonne `commune_code_hcp` (146 valeurs).
- Les 4 arrondissements de Tanger (Bni Makada, Mghogha, Souani, Médina) sont agrégés sous la clé `MA-01-511-0103`.

**Exclusion.** `MA-01-573-0100` (« Sebta » / Ceuta) est exclu : territoire hors souveraineté marocaine.

**Vérification.** Aucun écart par province après traitement (36/28/7/19/17/12/22/5 = 146).

**Alternative écartée.** Travailler sur 150 entités : aurait produit des doubles comptages pour Tanger et un chiffre non défendable devant le jury.

---

## D-002 — Point de départ du trajet : point représentatif intérieur
**Date :** 2026-11-11 · **Décideur :** Membre A (à valider par B et C) · **Statut :** 🟡 provisoire

**Contexte.** Il faut un point d'origine par commune pour calculer le temps de trajet vers l'établissement de santé. Trois options : centroïde géométrique, centre habité / chef-lieu, ou point représentatif intérieur.

**Décision provisoire.** Utiliser le **point représentatif intérieur** au polygone (`start_point_lon/lat`), déjà calculé dans le référentiel.

**Raisons.**
1. **Garanti dans le territoire** : un centroïde peut tomber en mer (communes côtières) ou dans une zone inhabitée.
2. **Reproductible** : calculé par script, pas de choix manuel commune par commune.
3. **Disponible immédiatement** : ne dépend d'aucune source supplémentaire.
4. **Cohérent** avec le principe du dossier : « une chaîne fiable et démontrable vaut mieux qu'un grand nombre de fonctions fragiles ».

**Limite assumée.** Le point représentatif n'est pas nécessairement le chef-lieu ni le centre de population réelle. Conséquence : le temps de trajet est une **approximation systématique**, pas une mesure exacte.

**Suite.** Analyse de sensibilité en semaine 3 (tâche A-17) : comparer les temps obtenus avec le point représentatif vs le chef-lieu sur un échantillon de 10 communes. Si l'écart est important, le documenter sans changer la méthode principale.

**Alternative écartée (pour l'instant).** Centre habité extrait d'OSM : plus réaliste, mais ajoute une dépendance, un délai et un risque de communes sans centre identifié.

---

## D-003 — Clé de jointure unique : `commune_code`
**Date :** 2026-11-11 · **Décideur :** Membre A · **Statut :** ✅ adoptée

**Décision.** `commune_code` est **la seule clé de jointure autorisée** dans tout le projet (pipeline, base, app, tests). Toujours manipulée comme **texte**.

**Règles associées.**
- Interdiction de joindre sur `name_fr` ou `name_norm`.
- Interdiction de convertir en entier (perte des zéros initiaux : `051` → `51`).
- Les fichiers exposés à Excel doivent être livrés en CSV avec la colonne forcée en texte.

**Conséquence pour l'équipe.** C est responsable du respect de cette règle côté base et pipeline ; B côté application.

---

## D-004 — Statut des données manquantes
**Date :** 2026-11-11 · **Décideur :** Membre A · **Statut :** ✅ adoptée

**Décision.** Aucune donnée manquante n'est inventée, imputée en silence, ni remplacée par une moyenne.
- La cellule reste **vide**.
- `statut_valeur` = `A_REMPLIR`.
- La commune est signalée comme **non couverte** dans le rapport qualité et, à terme, dans le panneau « État des données » de l'app.

**Raison.** Le dossier de conception l'exige explicitement et le jury valorise l'honnêteté sur la complétude. Un jeu incomplet **signalé** est défendable ; un jeu complet **faux** ne l'est pas.

---

## D-005 — Statut de la surface communale
**Date :** 2026-11-11 · **Décideur :** Membre A · **Statut :** ✅ adoptée

**Décision.** `area_km2` est un **calcul sur géométries simplifiées**, marqué `ESTIME`. La surface totale obtenue (16 644 km²) ne concorde pas avec les ≈ 15 000–16 000 km² des monographies HCP.

**Conséquence.** La surface et la densité peuvent être utilisées en interne et pour la comparaison relative entre communes, mais **ne doivent jamais être présentées comme des chiffres officiels** dans le rapport ou le pitch.

---

## D-006 — Détermination du milieu de résidence : méthode par les douars
**Date :** 2026-11-11 · **Décideur :** Membre A · **Statut :** ✅ adoptée

**Décision.** Le milieu (`Urbain` / `Rural` / `Mixte`) est **calculé à partir des données officielles du HCP**, jamais deviné :
- on somme la population des **douars** (qui ne couvrent que le milieu rural) pour chaque commune ;
- on compare à la population légale totale de la commune :
  - rural = 0 → **Urbain**
  - rural = total → **Rural**
  - entre les deux → **Mixte**

**Résultat.** 17 communes urbaines, 69 rurales, 60 mixtes (cf. `qc_milieu.json`).

**Contrôle.** La somme des populations rurales (1 382 463) et des ménages ruraux (320 093) correspond **exactement** aux totaux régionaux officiels du HCP.

**Alternatives écartées.**
- Reprendre une liste « urbain/rural » de mémoire : aucune source, non défendable.
- Déduire le milieu du nombre d'habitants : faux (une commune de 30 000 hab. peut être rurale).
- Utiliser le code série du code géographique : non fiable — la série 01 n'est pas systématiquement urbaine.

**Conséquence.** Une commune « Mixte » abrite à la fois une population urbaine et une population rurale. Pour le cas d'étude « commune rurale de montagne », utiliser `population_rurale_2024`, **pas** la population totale.

---

## D-007 — Tanger : code officiel `MA-01-511-0100`
**Date :** 2026-11-11 · **Décideur :** Membre A · **Statut :** ✅ adoptée

**Contexte.** Le code géographique officiel de la commune de Tanger est `01.511.01.0` (dernier segment à un seul chiffre). Dans le fichier de géométries, le code `MA-01-511-0103` désigne en réalité l'**arrondissement de Bni Makada**, et non la commune de Tanger.

**Décision.** La commune agrégée de Tanger porte le code **`MA-01-511-0100`**. Les quatre arrondissements (`0103` Bni Makada, `0105` Mghogha, `0106` Souani, `0107` Médina) pointent vers ce code via `commune_code_hcp`.

**Vérification.** 567 465 + 252 656 + 111 772 + 343 535 = **1 275 428** = population officielle de la commune de Tanger. ✅

**Pourquoi c'est important.** Sans cette décision, la population de Tanger aurait été remplacée par celle de Bni Makada : **707 963 habitants perdus** et un total régional faux. C'est exactement le type d'erreur silencieuse que le projet doit rendre impossible.

---

## Décisions encore à prendre (responsabilité du Membre A ou co-décision)

| # | Question | Échéance | Impact | Recommandation provisoire |
|---|---|---|---|---|
| D-008 | Seuils de trajet : garder 15/45 min ou ajuster ? | Semaine 2 (avec B) | Classes du score | **Examiner la distribution d'abord**, puis figer par écrit |
| D-009 | Épisodes météo du cas d'étude : lesquels ? | Semaine 3 (avec C) | Rapport | Choisir un épisode **documenté** (presse, bulletins) et vérifiable |
| D-010 | Licence HCP : usage et redistribution autorisés ? | Cette semaine (encadrant) | Publication du dataset | Traiter comme bloquant |
| D-011 | Tanger : score unique ou 4 scores d'arrondissement ? | Semaine 2 (avec B et C) | Carte et classement | **Score unique** au niveau 146 ; les 4 polygones n'affectent que l'affichage |

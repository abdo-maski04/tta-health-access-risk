# Méthodologie — calcul du risque d'accès aux soins

> Une page. Chaque membre de l'équipe doit pouvoir l'expliquer sans notes.
> Décisions associées : `docs/decisions.md` (D-008, D-014, D-015, D-016).

## 1. Objet

Pour chaque **commune** (146) et chaque **jour** (J à J+6), produire un **score de 0 à 9**
qui mesure la difficulté d'accès aux soins, puis une **couleur** et une **raison**.

Le score combine deux choses : **le danger météo du jour** et **l'éloignement de l'hôpital le plus proche**.
Il ne s'agit **pas d'une probabilité** ni d'une alerte officielle : c'est un indicateur d'aide à la décision.

## 2. Les quatre étapes

### Étape 1 — Danger pluie et danger chaleur (0 à 3)

On compare la prévision aux seuils calculés sur **10 ans** d'historique (table `weather.thresholds`,
une ligne par commune et par mois).

| Niveau | Condition (pluie **ou** chaleur) |
|---|---|
| 0 | valeur **< p65** |
| 1 | valeur **≥ p65** |
| 2 | valeur **≥ p80** |
| 3 | valeur **≥ p90** |

- **Pluie** : seuils calculés uniquement sur les **jours pluvieux** (≥ 1 mm).
- **Chaleur** : seuils de la **température maximale**, par mois.
- Si un seuil est `NULL` (moins de 20 jours pluvieux dans le mois) → **danger pluie = 0** : on ne signale pas ce qu'on ne peut pas mesurer.

**Danger météo = le maximum des deux composantes**, en conservant laquelle domine.

### Étape 2 — Classe de trajet (1 à 3)

Temps vers **l'hôpital le plus proche** :

| Classe | Temps |
|---|---|
| 1 | moins de 15 min |
| 2 | de 15 à 45 min |
| 3 | plus de 45 min |

**Jamais 0** : même avec un hôpital sur place, il faut du temps pour y arriver.
Les bornes 15 / 45 sont **retenues** (D-015). L'analyse de sensibilité a été faite sur six
variantes de bornes : 91 communes changent de classe, mais le **classement des communes par
temps de trajet ne change jamais**. Les temps utilisés sont les temps routiers réels
OpenRouteService, disponibles pour les **146 communes**.

### Étape 3 — Score

```
score = danger météo × classe de trajet
```

Valeurs possibles : **0, 1, 2, 3, 4, 6, 9** (5, 7 et 8 sont mathématiquement impossibles).

C'est une **multiplication** et non une addition : le risque naît de la rencontre des deux facteurs.
Si le danger météo vaut 0, le score vaut 0 — **une commune très isolée par beau temps reste verte**.

### Étape 4 — Couleur

| Score | Couleur |
|---|---|
| 0 | 🟢 vert |
| 1 à 2 | 🟡 jaune |
| 3 à 4 | 🟠 orange |
| 6 à 9 | 🔴 rouge |

## 3. Raison principale

On affiche la **composante la plus élevée** entre pluie (0-3), chaleur (0-3) et éloignement (classe 1-3).
En cas d'égalité, l'ordre de priorité est : **pluie**, puis **chaleur**, puis **éloignement**.

Pourquoi cet ordre : la pluie est la cause principale de **coupure d'accès** ; la chaleur est une
**pression sur le système de santé** ; l'éloignement est une condition **structurelle**, pas un événement.

## 4. Population : un axe séparé

La population **ne multiplie pas** le score. Elle sert uniquement à **ordonner les communes rouges** :
on affiche les **« personnes exposées »** = population des communes classées rouges ce jour-là.

Sans cette séparation, les grandes villes seraient rouges tous les jours et la carte ne servirait plus à rien.

## 5. Limites assumées

| Limite | Conséquence |
|---|---|
| Niveau 3 = **p90** (1 jour sur 10) et non p99 | le rouge est **fréquent** (~36 jours/an). Écart assumé et chiffré en D-014 ; atténué en affichant la raison et les personnes exposées |
| Bornes 15 / 45 min **retenues** (D-015) | classe de trajet sensible au choix de bornes ; sensibilité calculée sur 6 variantes : 91 communes changent de classe, le classement non |
| Temps de trajet **réels** OpenRouteService (146/146) | le plan B (vol d'oiseau × 1,4 ÷ 50 km/h) n'a pas été utilisé ; limite restante : pas de trafic réel, pas de route coupée |
| Hôpitaux issus d'**OpenStreetMap** | source non officielle ; 16 des 24 hôpitaux de la liste MSPS retrouvés par le nom |
| Population **légale 2014/2024** (HCP) | population présente ≠ population légale (saisonnalité non couverte) |

## 6. Pourquoi le score n'est pas une probabilité

Le score est un **produit de deux échelles ordinales**. Il ordonne des situations, il ne prédit pas
une fréquence. Deux communes de score 9 ne sont pas « deux fois plus à risque » qu'une commune de 4,5 :
elles cumulent simplement le maximum sur les deux axes.

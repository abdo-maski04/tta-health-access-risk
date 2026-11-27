## Ce que fait cette PR

<!-- Une phrase. Exemple : ajoute les 4 colonnes du score dans weather.risk_daily. -->

## Pourquoi

<!-- Le probleme corrige ou la tache du plan concernee (A-xx, T-xx, D-xx). -->

## Comment le tester

```bat
python -m pytest -q
```

<!-- Une commande precise si la PR touche la base ou un script. -->

## Checklist

- [ ] `python -m pytest -q` passe en local
- [ ] `ruff check .` passe
- [ ] une branche = une PR (pas de `main` en direct)
- [ ] aucun fichier ajoute avec `git add .` (un `git add` par fichier)
- [ ] aucun secret : pas de cle ORS, pas de `.env`
- [ ] si la base change : migration SQL fournie et testee
- [ ] si un fichier de donnees change : le dictionnaire des variables est mis a jour

## Donnees touchees

<!-- Cocher ce qui est concerne -->
- [ ] aucune
- [ ] `data/processed/*.csv`
- [ ] `data/processed/*.geojson`
- [ ] `sql/init.sql`
- [ ] `docs/data_dictionary.md`

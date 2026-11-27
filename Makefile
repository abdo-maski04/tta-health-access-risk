# Raccourcis du projet TTA Health Access Risk.
# Sous Windows, utiliser Git Bash ou WSL : make n'est pas fourni avec CMD.
# Les commandes CMD equivalentes sont dans le README, section 3.

.PHONY: help install test lint format check travel zones thresholds forecast risk app clean

help:
	@echo "install     installe les dependances de developpement"
	@echo "test        lance les tests rapides (sans base, sans reseau)"
	@echo "lint        ruff check"
	@echo "format      ruff format (reecrit les fichiers)"
	@echo "check       lint + format check + tests"
	@echo "travel      calcule les temps de trajet (OpenRouteService)"
	@echo "zones       calcule les zones 15/30/45/60 min"
	@echo "thresholds  calcule les seuils p65/p80/p90"
	@echo "forecast    charge les previsions Open-Meteo dans la base"
	@echo "risk        calcule le danger et le score du jour"
	@echo "app         lance l'application Streamlit"
	@echo "clean       supprime les caches Python"

install:
	pip install -r requirements/dev.txt

test:
	python -m pytest -q -m "not integration and not external"

lint:
	ruff check .

format:
	ruff format .

check: lint test

travel:
	python scripts/build_travel_time.py

zones:
	python scripts/build_access_zones.py

thresholds:
	python scripts/build_thresholds.py

forecast:
	python -m src.tta_risk.weather.forecast_loader

risk:
	python scripts/run_risk_daily.py

app:
	streamlit run app/streamlit_app.py

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"

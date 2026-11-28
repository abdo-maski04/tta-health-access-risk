"""Tests unitaires et d'intégration pour la Carte des 146 Itinéraires v2 (PyDeck)."""

import unittest
from unittest.mock import patch

import pandas as pd

from app.data_loader import load_v2_routes_consolidated
from app.pages.hospital_routes_map import (
    _get_map_center_and_zoom,
    render_hospital_routes_map,
)


class HospitalRoutesMapV2Tests(unittest.TestCase):
    """Tests exhaustifs des données et du composant cartographique v2."""

    @classmethod
    def setUpClass(cls):
        cls.routes_df, cls.hospitals_df, cls.communes_gj = load_v2_routes_consolidated()

    def test_routes_dataset_has_exactly_146_communes(self):
        """Vérifie que le jeu consolidé v2 contient exactement les 146 communes."""
        self.assertEqual(len(self.routes_df), 146)
        self.assertEqual(self.routes_df["commune_code"].nunique(), 146)

    def test_partition_50_recalculated_and_96_protected(self):
        """Vérifie la partition exacte de 50 recalculés v2 et 96 protégés v1."""
        recalculated_count = int(self.routes_df["is_recalculated"].sum())
        protected_count = int((~self.routes_df["is_recalculated"]).sum())
        self.assertEqual(recalculated_count, 50)
        self.assertEqual(protected_count, 96)
        self.assertEqual(recalculated_count + protected_count, 146)

    def test_provisional_destinations_identified(self):
        """Vérifie que les trois destinations provisoires (Fnideq, Belyounech, Anjra) sont bien balisées."""
        provisional_rows = self.routes_df[self.routes_df["is_provisional"]]
        self.assertEqual(len(provisional_rows), 3)
        prov_codes = set(provisional_rows["commune_code"])
        self.assertEqual(prov_codes, {"MA-01-573-0101", "MA-01-573-0109", "MA-01-227-0305"})

    def test_all_routes_have_valid_linestring_paths(self):
        """Vérifie que chaque itinéraire possède des coordonnées de tracé valides."""
        for _, row in self.routes_df.iterrows():
            path = row["path"]
            self.assertIsInstance(path, list)
            self.assertGreaterEqual(len(path), 2, f"Tracé trop court pour {row['commune_code']}")
            # Vérifier que le premier et dernier point sont des paires [lon, lat]
            self.assertEqual(len(path[0]), 2)
            self.assertEqual(len(path[-1]), 2)
            # Vérifier les bornes géographiques de la région TTA
            start_lon, start_lat = path[0]
            self.assertTrue(-6.5 <= start_lon <= -3.5, f"Lon hors limites: {start_lon}")
            self.assertTrue(34.5 <= start_lat <= 36.2, f"Lat hors limites: {start_lat}")

    def test_metrics_are_strictly_positive_and_realistic(self):
        """Vérifie que toutes les distances et durées sont positives et réalistes."""
        self.assertTrue((self.routes_df["distance_km"] > 0).all())
        self.assertTrue((self.routes_df["temps_min"] > 0).all())
        self.assertLess(self.routes_df["distance_km"].max(), 250.0)
        self.assertLess(self.routes_df["temps_min"].max(), 300.0)

    def test_hospitals_dataset_contains_official_facilities(self):
        """Vérifie que les hôpitaux répertoriés incluent les structures officielles."""
        self.assertGreaterEqual(len(self.hospitals_df), 15)
        official_count = int(self.hospitals_df["is_official"].sum())
        self.assertGreaterEqual(official_count, 15)
        # Bni Saïd candidat local doit être présent
        bni_said = self.hospitals_df[self.hospitals_df["osm_id"] == 1547030549]
        self.assertEqual(len(bni_said), 1)

    def test_communes_geojson_has_146_features_with_properties(self):
        """Vérifie le GeoJSON des communes avec propriétés enrichies pour PyDeck."""
        self.assertEqual(len(self.communes_gj["features"]), 146)
        first_feat = self.communes_gj["features"][0]
        self.assertIn("fill_color", first_feat["properties"])
        self.assertIn("line_color", first_feat["properties"])
        self.assertIn("hospital_name", first_feat["properties"])

    def test_map_center_calculation(self):
        """Vérifie le calcul dynamique du centre et zoom de la caméra."""
        lat, lon, zoom = _get_map_center_and_zoom(self.routes_df)
        self.assertAlmostEqual(lat, 35.35, delta=0.5)
        self.assertAlmostEqual(lon, -5.35, delta=0.8)
        self.assertEqual(zoom, 8.25)

        # Centrage spécifique sur une commune
        c_lat, c_lon, c_zoom = _get_map_center_and_zoom(self.routes_df, "MA-01-227-0305")
        self.assertEqual(c_zoom, 10.0)

    @patch("streamlit.pydeck_chart")
    @patch("streamlit.selectbox")
    @patch("streamlit.checkbox")
    def test_render_hospital_routes_map_smoke_test(self, mock_check, mock_select, mock_deck):
        """Smoke test : vérifie que le rendu de la page s'exécute sans lever d'exception."""
        mock_select.side_effect = [
            "Toutes les provinces",
            "Tous les statuts (146)",
            "Tous les hôpitaux",
            "Toutes les communes",
        ]
        mock_check.return_value = True

        # Doit s'exécuter sans erreur
        render_hospital_routes_map()
        self.assertTrue(mock_deck.called)

    def test_leaflet_sig_builder_and_zero_placeholders(self):
        """Vérifie la génération du composant Leaflet SIG et l'absence totale de placeholders non résolus."""
        from app.pages.hospital_routes_map import _load_auxiliary_layers
        from app.pages.leaflet_sig_builder import generate_leaflet_sig_html

        aux = _load_auxiliary_layers()
        routes_gj = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[-5.8, 35.7], [-5.81, 35.72]],
                    },
                    "properties": {
                        "name_fr": "Tanger",
                        "commune_code": "MA-01-511-0101",
                        "province": "Tanger-Assilah",
                        "hospital_canonical": "CHU Mohammed VI Tanger",
                        "temps_min": 12.5,
                        "distance_km": 7.8,
                        "is_recalculated": True,
                        "access_tier": "Critique ≤ 15 min",
                    },
                }
            ],
        }
        hospitals_gj = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [-5.81, 35.72]},
                    "properties": {
                        "name": "CHU Mohammed VI",
                        "category": "CHU",
                        "province": "Tanger-Assilah",
                        "capacity_beds_est": 771,
                    },
                }
            ],
        }

        html = generate_leaflet_sig_html(
            routes_geojson=routes_gj,
            hospitals_geojson=hospitals_gj,
            communes_geojson=self.communes_gj,
            hydro_rivers_geojson=aux.get("hydro_rivers")
            or {"type": "FeatureCollection", "features": []},
            hydro_basins_geojson=aux.get("hydro_basins")
            or {"type": "FeatureCollection", "features": []},
            hazards_geojson=aux.get("hazards") or {"type": "FeatureCollection", "features": []},
            isochrones_geojson=aux.get("isochrones")
            or {"type": "FeatureCollection", "features": []},
            terrain_bounds=aux.get("terrain_bounds", [-6.2923, 34.4560, -3.7540, 35.9730]),
            height=780,
        )

        self.assertIsInstance(html, str)
        self.assertIn("leaflet.js", html)
        self.assertIn("sig-panel", html)
        self.assertIn("getHospitalSvgIcon", html)
        self.assertIn("CHU", html)
        # Vérification zéro placeholder PyDeck résiduel ou non résolu
        for bad_placeholder in [
            "{name_fr} {name} {nom}",
            "{hospital_canonical} {hospital_name}",
            "{category} {type_alea}",
        ]:
            self.assertNotIn(bad_placeholder, html)

    def test_auxiliary_layers_loader(self):
        """Vérifie le chargement des couches auxiliaires (relief, hydro, aléas, isochrones)."""
        from app.pages.hospital_routes_map import _load_auxiliary_layers

        aux = _load_auxiliary_layers()
        self.assertIn("terrain_bounds", aux)
        self.assertIsInstance(aux["terrain_bounds"], list)
        self.assertEqual(len(aux["terrain_bounds"]), 4)
        self.assertIsNotNone(aux["hydro_rivers"])
        self.assertGreaterEqual(len(aux["hydro_rivers"]["features"]), 10)
        self.assertIsNotNone(aux["hazards"])
        self.assertGreaterEqual(len(aux["hazards"]["features"]), 5)
        self.assertIsNotNone(aux["isochrones"])
        self.assertEqual(len(aux["isochrones"]["features"]), 4)

    def test_geospatial_metadata_catalog(self):
        """Vérifie l'existence et la conformité du catalogue de métadonnées géospatiales."""
        from pathlib import Path

        meta_csv = Path("data/metadata/geospatial_sources.csv")
        self.assertTrue(meta_csv.exists())
        df = pd.read_csv(meta_csv)
        self.assertGreaterEqual(len(df), 6)
        expected_cols = {
            "dataset_id",
            "name",
            "category",
            "provider",
            "format",
            "coverage",
            "license",
        }
        self.assertTrue(expected_cols.issubset(set(df.columns)))
        dataset_ids = set(df["dataset_id"])
        self.assertIn("COPERNICUS_DEM_GLO", dataset_ids)
        self.assertIn("HYDROSHEDS_RIVERS", dataset_ids)
        self.assertIn("ABHL_HAZARDS", dataset_ids)
        self.assertIn("MSPS_CARTE_SANITAIRE", dataset_ids)

    def test_terrain_and_hydro_files_exist_and_valid(self):
        """Vérifie la présence et la non-vacuité des rasters terrain et vecteurs hydrographiques."""
        from pathlib import Path

        dem_tif = Path("data/processed/terrain/tta_dem_30m.tif")
        hs_png = Path("data/processed/terrain/tta_hillshade_display.png")
        hydro_gj = Path("data/processed/hydro/tta_hydrorivers.geojson")
        basins_gj = Path("data/processed/hydro/tta_hydrobasins.geojson")
        hazards_gj = Path("data/processed/hazards/tta_territorial_constraints.geojson")

        for p in [dem_tif, hs_png, hydro_gj, basins_gj, hazards_gj]:
            self.assertTrue(p.exists(), f"Fichier manquant : {p}")
            self.assertGreater(p.stat().st_size, 1000, f"Fichier trop petit/vide : {p}")


if __name__ == "__main__":
    unittest.main()

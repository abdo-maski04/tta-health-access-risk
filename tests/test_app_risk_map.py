import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from data_loader import (  # noqa: E402
    assign_facility_communes,
    join_commune_properties,
    load_communes,
    load_communes_geojson,
    load_facilities,
)
from map_utils import commune_color_values, numeric_color_range  # noqa: E402
from pages.risk_map import (  # noqa: E402
    commune_areas_km2,
    commune_code_from_map_event,
    filter_facility_search,
    filter_map_communes,
    simplify_commune_geojson,
)


class AppRiskMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.communes = load_communes()
        cls.geojson = join_commune_properties(
            cls.communes,
            load_communes_geojson(),
        )
        cls.facilities = assign_facility_communes(
            load_facilities(),
            cls.geojson,
        )

    def test_geodesic_area_covers_all_commune_polygons(self):
        areas = commune_areas_km2(self.geojson)
        self.assertEqual(len(areas), 146)
        self.assertTrue(all(area > 0 for area in areas.values()))
        self.assertGreater(sum(areas.values()), 1_000)

    def test_simplified_web_geojson_preserves_commune_features(self):
        simplified = simplify_commune_geojson(self.geojson)
        self.assertEqual(len(simplified["features"]), 146)
        self.assertEqual(
            {
                feature["properties"]["commune_code"]
                for feature in simplified["features"]
            },
            {
                feature["properties"]["commune_code"]
                for feature in self.geojson["features"]
            },
        )
        self.assertEqual(
            simplified["features"][0]["properties"],
            self.geojson["features"][0]["properties"],
        )

    def test_simplification_removes_redundant_vertices(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"commune_code": "01"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [0.0002, 0],
                        [0.0004, 0],
                        [0.0006, 0],
                        [0.0006, 0.0006],
                        [0.0004, 0.0006],
                        [0.0002, 0.0006],
                        [0, 0.0006],
                        [0, 0],
                    ]],
                },
            }],
        }
        simplified = simplify_commune_geojson(geojson)
        self.assertEqual(
            len(simplified["features"][0]["geometry"]["coordinates"][0]),
            4,
        )

    def test_map_event_selects_only_commune_popups(self):
        self.assertEqual(
            commune_code_from_map_event({
                "last_object_clicked_popup": "Tanger\nCode: MA-01-001",
            }),
            "MA-01-001",
        )
        self.assertEqual(
            commune_code_from_map_event({
                "last_object_clicked_popup": (
                    "<div><b>Tanger</b><br><b>Code:</b> MA-01-001"
                    "<br><b>Province:</b> Tanger</div>"
                ),
            }),
            "MA-01-001",
        )
        self.assertEqual(
            commune_code_from_map_event({
                "last_active_drawing": {
                    "properties": {"commune_code": "MA-01-002"},
                },
            }),
            "MA-01-002",
        )
        self.assertIsNone(
            commune_code_from_map_event({
                "last_object_clicked_popup": "Hôpital\nType: hospital",
            })
        )

    def test_facility_search_matches_name_type_and_city(self):
        rows = [
            {"name": "Centre de santé", "facility_type": "clinic", "addr_city": "Tétouan"},
            {"name": "Pharmacie Al Amal", "facility_type": "pharmacy"},
        ]
        self.assertEqual(
            filter_facility_search(rows, "HOPITAL"),
            [],
        )
        self.assertEqual(filter_facility_search(rows, "TETOUAN"), [rows[0]])
        self.assertEqual(filter_facility_search(rows, "CLINIQUE"), [rows[0]])
        self.assertEqual(filter_facility_search(rows, "PHARMACIE"), [rows[1]])

    def test_commune_search_is_accent_and_arabic_compatible(self):
        rows = [{
            "name_fr": "Tétouan",
            "name_ar": "تطوان",
            "commune_code": "MA-01-001",
            "province": "Tétouan",
            "milieu": "Urbain",
        }]
        self.assertEqual(filter_map_communes(rows, [], [], "tetouan"), rows)
        self.assertEqual(filter_map_communes(rows, [], [], "تطوان"), rows)

    def test_numeric_map_modes_use_real_commune_values(self):
        areas = commune_areas_km2(self.geojson)
        density = commune_color_values(
            self.communes,
            "density",
            areas_km2=areas,
        )
        facility_counts = commune_color_values(
            self.communes,
            "facilities",
            facilities=self.facilities,
        )
        self.assertEqual(len(density), 146)
        self.assertTrue(all(value is not None and value > 0 for value in density.values()))
        self.assertEqual(sum(facility_counts.values()), 826)
        self.assertIsNotNone(numeric_color_range(density))

    def test_enterprise_risk_map_renders_without_app_test_exceptions(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(
            str(ROOT / "app" / "streamlit_app.py"),
            default_timeout=90,
        ).run()
        navigation = app.radio(key="sidebar_navigation_radio")
        navigation.set_value(navigation.options[1])
        app.run(timeout=120)

        self.assertEqual(list(app.exception), [])

        # Switch to historical full screen SIG view to test its enterprise tabs and controls
        map_selector = app.radio(key="geovulnera_active_map_selector")
        if map_selector and len(map_selector.options) >= 4:
            map_selector.set_value(map_selector.options[3])
            app.run(timeout=120)

        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.tabs), 2)
        self.assertGreaterEqual(len(app.selectbox), 5)
        self.assertGreaterEqual(len(app.checkbox), 12)

    def test_sidebar_navigation_navigates_to_a_dashboard(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(
            str(ROOT / "app" / "streamlit_app.py"),
            default_timeout=90,
        ).run()
        sidebar_navigation = app.radio(key="sidebar_navigation_radio")
        sidebar_navigation.set_value(sidebar_navigation.options[2])
        app.run(timeout=120)

        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.session_state["selected_page"], "Commune Ranking")
        self.assertNotIn("header_navigation_radio", app.session_state)


if __name__ == "__main__":
    unittest.main()

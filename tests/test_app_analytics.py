import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from data_loader import get_prepared_data  # noqa: E402
from pages.analytics import (  # noqa: E402
    RANKING_CSS,
    _commune_rows,
    _filter_ranking_rows,
    _ranking_facility_count,
    _ranking_table_html,
    _sort_ranking_rows,
)


class CommuneRankingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.communes, _, cls.facilities = get_prepared_data()
        cls.rows = _commune_rows(cls.communes, cls.facilities)

    def test_commune_facility_totals_match_associated_source_records(self):
        associated = sum(
            facility.get("commune_code") is not None
            for facility in self.facilities
        )
        self.assertEqual(sum(row["Total établissements"] for row in self.rows), associated)
        self.assertEqual(associated, 826)
        self.assertEqual(
            sum(facility.get("commune_code") is None for facility in self.facilities),
            66,
        )

    def test_autres_filter_uses_the_combined_other_category_once(self):
        row = next(row for row in self.rows if row["Autres"] > 0)
        self.assertEqual(_ranking_facility_count(row, "Autres"), row["Autres"])
        self.assertEqual(
            _filter_ranking_rows(
                [row],
                facility_type="Autres",
                min_facilities=row["Autres"],
                max_facilities=row["Autres"],
            ),
            [row],
        )

    def test_facilities_per_population_sort_uses_selected_population_year(self):
        rows = [
            {
                "Commune": "A",
                "Total établissements": 100,
                "Population 2014": 100_000,
                "Population 2024": 1_000_000,
            },
            {
                "Commune": "B",
                "Total établissements": 50,
                "Population 2014": 1_000_000,
                "Population 2024": 100_000,
            },
        ]
        metric = "Établissements / 10 000 hab."
        self.assertEqual(_sort_ranking_rows(rows, metric, 2014)[0]["Commune"], "A")
        self.assertEqual(_sort_ranking_rows(rows, metric, 2024)[0]["Commune"], "B")

    def test_ranking_table_has_branded_header_badge_and_selected_row(self):
        row = {
            "Code": "001",
            "Commune": "Tétouan",
            "Province": "Tétouan",
            "Milieu": "Urbain",
            "Population 2024": 100_000,
            "Total établissements": 10,
            "Hôpitaux": 1,
            "Cliniques": 2,
            "Pharmacies": 5,
        }
        rendered = _ranking_table_html([row], "001", 2024)

        self.assertIn("class='is-selected'", rendered)
        self.assertIn("background:#0D5C75", rendered)
        self.assertIn("background:#0A3642", RANKING_CSS)
        self.assertIn("border-radius:999px", RANKING_CSS)

    def test_commune_ranking_page_renders_from_sidebar_navigation(self):
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(
            str(ROOT / "app" / "streamlit_app.py"),
            default_timeout=90,
        ).run()
        navigation = app.radio(key="sidebar_navigation_radio")
        navigation.set_value(navigation.options[2])
        app.run(timeout=120)

        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.session_state["selected_page"], "Commune Ranking")
        self.assertIsNotNone(app.selectbox(key="ranking_selected_commune_label"))
        self.assertTrue(
            any(button.label == "Exporter le classement" for button in app.button)
            or any(
                button.label == "Exporter le classement"
                for button in app.get("download_button")
            )
        )
        selected_code = app.session_state["ranking_selected_commune_code"]
        app.button(key="ranking_view_details").click()
        app.run(timeout=120)

        self.assertEqual(list(app.exception), [])
        self.assertEqual(app.session_state["selected_page"], "Commune Details")
        self.assertTrue(
            app.selectbox(key="details_commune_selector").value.endswith(selected_code)
        )


if __name__ == "__main__":
    unittest.main()

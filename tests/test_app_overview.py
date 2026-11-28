import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

from data_loader import (  # noqa: E402
    assign_facility_communes,
    join_commune_properties,
    load_communes,
    load_communes_geojson,
    load_facilities,
)
from pages.overview import (  # noqa: E402
    _build_map,
    available_population_years,
    build_provincial_summary,
    filter_overview_communes,
)
from visualization.overview_charts import (  # noqa: E402
    associated_facilities_by_province,
    demographic_evolution,
    facilities_by_type,
    milieu_donut,
    population_by_province,
    population_top_bottom,
    urban_rural_by_province,
)


class AppOverviewTests(unittest.TestCase):
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

    def test_overview_population_totals(self):
        self.assertEqual(len(self.communes), 146)
        self.assertEqual(sum(row["population_2024"] for row in self.communes), 4_030_222)

    def test_overview_milieu_totals(self):
        counts = {
            milieu: sum(row["milieu"] == milieu for row in self.communes)
            for milieu in ("Urbain", "Mixte", "Rural")
        }
        self.assertEqual(counts, {"Urbain": 17, "Mixte": 60, "Rural": 69})

    def test_commune_environment_chart_uses_official_map_colors(self):
        from config.theme import COLORS

        figure = milieu_donut(self.communes)
        self.assertEqual(
            list(figure.data[0].marker.colors),
            list(COLORS["overview_milieu"].values()),
        )
        self.assertIn("Urbain (17)", list(figure.data[0].labels))

    def test_facility_totals_and_unassociated_records(self):
        self.assertEqual(len(self.facilities), 892)
        associated = sum(row["commune_code"] is not None for row in self.facilities)
        unassociated = sum(row["commune_code"] is None for row in self.facilities)
        self.assertGreater(associated, 0)
        self.assertEqual(unassociated, 66)

    def test_overview_filters(self):
        filtered = filter_overview_communes(
            self.communes,
            provinces=["Al Hoceima"],
            milieux=["Rural"],
        )
        self.assertGreater(len(filtered), 0)
        self.assertTrue(
            all(row["province"] == "Al Hoceima" and row["milieu"] == "Rural" for row in filtered)
        )

    def test_search_filter_by_code_and_name(self):
        code_result = filter_overview_communes(
            self.communes,
            search=self.communes[0]["commune_code"],
        )
        name_result = filter_overview_communes(
            self.communes,
            search=self.communes[0]["name_fr"],
        )
        self.assertEqual(len(code_result), 1)
        self.assertIn(
            self.communes[0]["commune_code"], [row["commune_code"] for row in name_result]
        )

    def test_empty_filter_returns_no_communes(self):
        result = filter_overview_communes(self.communes, search="zzzz-not-found")
        self.assertEqual(result, [])

    def test_provincial_summary_is_sorted_and_complete(self):
        summary = build_provincial_summary(self.communes, self.facilities)
        self.assertEqual(len(summary), 8)
        populations = [row["Population 2024"] for row in summary]
        self.assertEqual(populations, sorted(populations, reverse=True))
        required = {
            "Province",
            "Communes",
            "Population 2024",
            "Population urbaine 2024",
            "Population rurale 2024",
            "Établissements associés",
        }
        self.assertTrue(all(required.issubset(row) for row in summary))

    def test_provincial_summary_supports_2014_population(self):
        summary = build_provincial_summary(
            self.communes,
            self.facilities,
            population_year=2014,
        )
        self.assertIn("Population 2014", summary[0])
        self.assertEqual(
            sum(row["Population 2014"] for row in summary),
            sum(row["population_2014"] for row in self.communes),
        )

    def test_population_years_are_discovered_from_available_columns(self):
        self.assertEqual(available_population_years(self.communes), [2014, 2024])
        self.assertEqual(
            available_population_years(
                [
                    {"population_2014": 100, "population_2024": None},
                    {"population_2014": 120, "population_2024": None},
                ]
            ),
            [2014],
        )

    def test_missing_demographic_values_remain_unavailable(self):
        rows = [
            {
                "commune_code": "01",
                "province": "Example",
                "area_km2": None,
                "population_2014": None,
                "population_2024": None,
            }
        ]
        summary = build_provincial_summary(rows, [], population_year=2024)
        self.assertIsNone(summary[0]["Population 2024"])
        self.assertIsNone(summary[0]["Population urbaine 2024"])
        self.assertIsNone(summary[0]["Population rurale 2024"])
        self.assertIsNone(summary[0]["Densité (hab/km²)"])
        figure = demographic_evolution(rows)
        self.assertIn("non disponibles", figure.layout.annotations[0].text)

    def test_overview_map_uses_its_centralized_environment_palette(self):
        from config.theme import COLORS

        folium_map = _build_map(
            self.communes,
            self.geojson,
            self.facilities,
            show_unassigned=True,
        )
        rendered = folium_map.get_root().render()
        for color in COLORS["overview_milieu"].values():
            self.assertIn(color, rendered)

    def test_all_overview_figures_are_created(self):
        figures = [
            milieu_donut(self.communes),
            population_by_province(self.communes),
            urban_rural_by_province(self.communes),
            demographic_evolution(self.communes),
            population_top_bottom(self.communes),
            population_top_bottom(self.communes, bottom=True),
            facilities_by_type(self.facilities),
            associated_facilities_by_province(self.communes, self.facilities),
        ]
        self.assertEqual(len(figures), 8)

    def test_population_charts_use_selected_year_and_real_growth(self):
        population_2014 = population_by_province(self.communes, year=2014)
        urban_rural_2014 = urban_rural_by_province(self.communes, year=2014)
        urban_rural_2024 = urban_rural_by_province(self.communes, year=2024)
        evolution = demographic_evolution(self.communes)

        self.assertIn("Population 2014", population_2014.layout.title.text)
        self.assertIn("2014 non disponible", urban_rural_2014.layout.annotations[0].text)
        self.assertEqual(urban_rural_2024.layout.barnorm, "percent")
        self.assertEqual(list(urban_rural_2024.layout.yaxis.range), [0, 100])
        self.assertEqual(evolution.data[0].type, "scatter")
        self.assertEqual(list(evolution.data[0].x), [2014, 2024])
        self.assertIn("+13.3%", evolution.layout.annotations[0].text)

    def test_least_populated_chart_starts_with_the_least_populated_commune(self):
        figure = population_top_bottom(self.communes, bottom=True)
        least_populated = min(
            self.communes,
            key=lambda row: row["population_2024"],
        )
        self.assertEqual(figure.data[0].y[0], least_populated["name_fr"])
        self.assertEqual(figure.layout.yaxis.autorange, "reversed")
        self.assertEqual(
            list(figure.layout.yaxis.categoryarray),
            list(figure.data[0].y),
        )

    def test_facility_donut_groups_only_real_source_types(self):
        figure = facilities_by_type(self.facilities)
        self.assertEqual(sum(figure.data[0].values), 892)
        self.assertEqual(
            set(figure.data[0].labels),
            {
                "Pharmacies",
                "Hôpitaux",
                "Cliniques",
                "Médecins",
                "Laboratoires",
                "Autres",
            },
        )
        self.assertEqual(
            figure.data[0].values[list(figure.data[0].labels).index("Autres")],
            4,
        )

    def test_empty_overview_figures_have_explicit_unavailable_content(self):
        figures = [
            milieu_donut([]),
            population_by_province([]),
            urban_rural_by_province([]),
            demographic_evolution([]),
            population_top_bottom([]),
            facilities_by_type([]),
            associated_facilities_by_province([], []),
        ]
        self.assertTrue(all(fig.layout.annotations for fig in figures))


if __name__ == "__main__":
    unittest.main()

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
    validate_commune_datasets,
)


class AppDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.communes = load_communes()
        cls.geojson = load_communes_geojson()
        cls.facilities = load_facilities()

    def test_exact_commune_and_geojson_counts(self):
        self.assertEqual(len(self.communes), 146)
        self.assertEqual(len(self.geojson["features"]), 146)

    def test_146_unique_commune_codes(self):
        codes = [row["commune_code"] for row in self.communes]
        self.assertEqual(len(set(codes)), 146)
        self.assertTrue(all(isinstance(code, str) for code in codes))

    def test_csv_geojson_codes_match(self):
        csv_codes = {row["commune_code"] for row in self.communes}
        geo_codes = {feature["properties"]["commune_code"] for feature in self.geojson["features"]}
        self.assertEqual(csv_codes, geo_codes)

    def test_validate_datasets_accepts_real_data(self):
        validate_commune_datasets(
            self.communes,
            self.geojson,
            self.facilities,
        )

    def test_join_adds_all_csv_properties(self):
        enriched = join_commune_properties(self.communes, self.geojson)
        properties = enriched["features"][0]["properties"]
        self.assertIn("population_2024", properties)
        self.assertIn("milieu", properties)
        self.assertIn("commune_code", properties)

    def test_exact_facility_count_unique_identifiers(self):
        self.assertEqual(len(self.facilities), 892)
        identifiers = [(row["osm_type"], row["osm_id"]) for row in self.facilities]
        self.assertEqual(len(set(identifiers)), 892)

    def test_all_facility_coordinates_are_valid(self):
        for row in self.facilities:
            self.assertGreaterEqual(row["lat"], -90)
            self.assertLessEqual(row["lat"], 90)
            self.assertGreaterEqual(row["lon"], -180)
            self.assertLessEqual(row["lon"], 180)

    def test_no_duplicate_facility_coordinates(self):
        coordinates = [(row["lat"], row["lon"]) for row in self.facilities]
        self.assertEqual(len(set(coordinates)), 892)

    def test_point_assignment_adds_no_fake_score(self):
        assigned = assign_facility_communes(
            self.facilities,
            join_commune_properties(self.communes, self.geojson),
        )
        self.assertEqual(len(assigned), 892)
        for row in assigned:
            self.assertIn("commune_code", row)
            self.assertNotIn("risk", row)
            self.assertNotIn("score", row)
            self.assertNotIn("niveau", row)

    def test_unassociated_facilities_are_identified_without_invention(self):
        assigned = assign_facility_communes(
            self.facilities,
            join_commune_properties(self.communes, self.geojson),
        )
        unassociated = [row for row in assigned if row["commune_code"] is None]
        self.assertGreater(len(unassociated), 0)
        self.assertLess(len(unassociated), len(assigned))


if __name__ == "__main__":
    unittest.main()

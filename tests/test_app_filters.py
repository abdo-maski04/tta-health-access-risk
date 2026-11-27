import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from data_loader import (  # noqa: E402
    filter_communes,
    filter_facilities,
    load_communes,
    load_facilities,
)


class AppFilterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.communes = load_communes()
        cls.facilities = load_facilities()

    def test_filter_by_single_province(self):
        results = filter_communes(self.communes, provinces=["Al Hoceima"])
        self.assertGreater(len(results), 0)
        self.assertTrue(all(row["province"] == "Al Hoceima" for row in results))

    def test_filter_by_milieu(self):
        results = filter_communes(self.communes, milieux=["Rural"])
        self.assertEqual(len(results), 69)

    def test_search_by_french_name(self):
        source = self.communes[0]
        results = filter_communes(self.communes, search=source["name_fr"])
        self.assertIn(source["commune_code"], [row["commune_code"] for row in results])

    def test_search_by_code(self):
        source = self.communes[0]
        results = filter_communes(self.communes, search=source["commune_code"])
        self.assertEqual(len(results), 1)

    def test_search_without_result(self):
        results = filter_communes(self.communes, search="zzzz-no-commune")
        self.assertEqual(results, [])

    def test_facility_type_filter(self):
        results = filter_facilities(
            self.facilities,
            facility_types=["hospital"],
        )
        self.assertEqual(len(results), 66)
        self.assertTrue(all(row["facility_type"] == "hospital" for row in results))

    def test_empty_facility_filter_returns_all(self):
        results = filter_facilities(self.facilities, facility_types=[])
        self.assertEqual(len(results), 892)


if __name__ == "__main__":
    unittest.main()

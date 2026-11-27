import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
sys.path.insert(0, str(APP))

from components.kpi_card import kpi_card  # noqa: E402
from components.sidebar import DASHBOARDS, NAVIGATION_ICON_SVGS  # noqa: E402
from components.states import unavailable_state  # noqa: E402
from config.settings import APP_TITLE, REGION_NAME  # noqa: E402
from config.theme import APP_CSS, COLORS, THEME  # noqa: E402


class AppComponentTests(unittest.TestCase):
    def test_theme_has_centralized_primary_colors(self):
        expected = {
            "navy": "#0B2235",
            "navy_dark": "#12364A",
            "turquoise": "#159B8E",
            "blue": "#2878B5",
            "background": "#F4F6F8",
            "surface": "#FFFFFF",
            "text": "#172B3A",
            "text_muted": "#718096",
            "border": "#E5EAF0",
            "green": "#27966F",
            "orange": "#E5A13A",
            "red": "#CE5252",
            "grey": "#DCE3E9",
        }
        for name, value in expected.items():
            self.assertEqual(getattr(THEME, name), value)
        self.assertIn("--tta-navy", APP_CSS)
        self.assertIn("--tta-navy-secondary", APP_CSS)

    def test_milieu_colors_exist_for_three_categories(self):
        self.assertEqual(COLORS["milieu"], {
            "Urbain": "#279B91",
            "Mixte": "#E6AD55",
            "Rural": "#648BB8",
        })
        self.assertEqual(COLORS["risk_milieu"], {
            "Urbain": "#3B82F6",
            "Mixte": "#10B981",
            "Rural": "#F59E0B",
            "Non assigné": "#94A3B8",
        })
        self.assertIn("#0A3642", APP_CSS)
        self.assertIn("#E2E8F0", APP_CSS)
        self.assertIn('header[data-testid="stHeader"]', APP_CSS)
        self.assertIn("height: 0 !important", APP_CSS)
        self.assertIn("min-height: 0 !important", APP_CSS)
        self.assertIn('[data-testid="stToolbar"]', APP_CSS)
        self.assertIn('[data-testid="stDecoration"]', APP_CSS)
        self.assertIn("#MainMenu", APP_CSS)
        self.assertIn('[data-testid="collapsedControl"]', APP_CSS)
        self.assertIn('[data-testid="stIconMaterial"]', APP_CSS)
        self.assertIn('button[aria-label="Expand sidebar"]', APP_CSS)
        self.assertIn("[data-stale=\"true\"]", APP_CSS)
        self.assertIn("background-color: #F4F7F9 !important", APP_CSS)
        self.assertIn("background: #FFFFFF !important", APP_CSS)
        self.assertIn("background: #0D5C75 !important", APP_CSS)
        self.assertIn("color: #334155 !important", APP_CSS)
        self.assertIn("stroke: #FFFFFF !important", APP_CSS)
        self.assertIn("padding-top: 0 !important", APP_CSS)

    def test_facility_colors_do_not_represent_risk(self):
        self.assertIn("hospital", COLORS["facility"])
        self.assertIn("pharmacy", COLORS["facility"])
        self.assertNotIn("low_risk", COLORS)
        self.assertNotIn("high_risk", COLORS)

    def test_sidebar_lists_exactly_seven_dashboards(self):
        self.assertEqual(len(DASHBOARDS), 7)
        self.assertEqual(len(NAVIGATION_ICON_SVGS), 7)
        self.assertTrue(
            all("<svg " in icon for icon in NAVIGATION_ICON_SVGS.values())
        )
        labels = [label for label, _ in DASHBOARDS]
        self.assertEqual(
            labels,
            [
                "Overview Dashboard",
                "Interactive Risk Map",
                "Commune Ranking",
                "Commune Details",
                "Trends & Historical Analysis",
                "Alerts & Priority Areas",
                "System Monitoring",
            ],
        )

    def test_application_identity_is_centralized(self):
        self.assertEqual(APP_TITLE, "TTA Health Access Risk")
        self.assertIn("Tanger", REGION_NAME)

    def test_component_imports_are_available(self):
        self.assertTrue(callable(kpi_card))
        self.assertTrue(callable(unavailable_state))

    def test_kpi_card_keeps_missing_values_explicit(self):
        with patch("components.kpi_card.st.markdown") as render:
            kpi_card("Population 2024", None, unit="habitants")

        markup = render.call_args.args[0]
        self.assertIn("Données non disponibles", markup)
        self.assertIn("tta-kpi-icon", markup)
        self.assertNotIn("habitants", markup)


if __name__ == "__main__":
    unittest.main()

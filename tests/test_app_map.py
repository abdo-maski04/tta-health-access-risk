import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

import map_utils  # noqa: E402


class AppMapTests(unittest.TestCase):
    def test_milieu_colors_are_complete(self):
        self.assertEqual(
            set(map_utils.MILIEU_COLORS),
            {"Urbain", "Mixte", "Rural"},
        )
        self.assertEqual(map_utils.MILIEU_COLORS, {
            "Urbain": "#279B91",
            "Mixte": "#E6AD55",
            "Rural": "#648BB8",
        })

    def test_facility_colors_cover_real_types(self):
        types = {
            "hospital", "clinic", "doctors", "laboratory", "pharmacy",
            "physiotherapist", "healthcare_unspecified",
        }
        self.assertTrue(types.issubset(set(map_utils.FACILITY_COLORS)))

    def test_initial_map_requires_folium(self):
        with patch.dict(sys.modules, {"folium": None}):
            with self.assertRaises(RuntimeError):
                map_utils.get_initial_map()

    def test_geojson_supports_polygon_and_multipolygon(self):
        from data_loader import load_communes_geojson

        geojson = load_communes_geojson()
        types = {
            feature["geometry"]["type"]
            for feature in geojson["features"]
        }
        self.assertEqual(types, {"Polygon", "MultiPolygon"})

    def test_popup_contents_have_no_fake_risk_fields(self):
        import data_loader

        communes = data_loader.load_communes()
        geojson = data_loader.load_communes_geojson()
        enriched = data_loader.join_commune_properties(communes, geojson)
        first = enriched["features"][0]["properties"]
        rendered = str(first)
        self.assertNotIn("score", rendered)
        self.assertNotIn("niveau", rendered)
        self.assertNotIn("risque", rendered)

    def test_tooltip_escapes_javascript_template_delimiters(self):
        import folium
        from map_utils import build_unassigned_facility_layer

        folium_map = folium.Map(location=[35.20, -5.45], zoom_start=7)
        build_unassigned_facility_layer(
            [{
                "name": "Centre El Fath D`hemodialyse ${2 + 2}",
                "facility_type": "clinic",
                "commune_code": None,
                "lat": 35.2,
                "lon": -5.45,
            }],
            folium_map,
        )

        rendered = folium_map.get_root().render()
        self.assertIn("D&#96;hemodialyse &#36;{2 + 2}", rendered)
        self.assertNotIn("D`hemodialyse ${2 + 2}", rendered)

    def test_folium_layer_contains_146_polygons_and_892_markers(self):
        import folium
        from config.theme import THEME
        from data_loader import (
            assign_facility_communes,
            join_commune_properties,
            load_communes,
            load_communes_geojson,
            load_facilities,
        )
        from map_utils import (
            build_commune_layer,
            build_facility_layer,
            build_unassigned_facility_layer,
            geojson_bounds,
        )

        communes = load_communes()
        enriched = join_commune_properties(
            communes,
            load_communes_geojson(),
        )
        facilities = assign_facility_communes(load_facilities(), enriched)
        folium_map = folium.Map(location=[35.20, -5.45], zoom_start=7)

        associated = [
            row for row in facilities
            if row["commune_code"] is not None
        ]
        commune_group = build_commune_layer(
            communes,
            enriched,
            folium_map,
            facilities=associated,
        )
        facility_group = build_facility_layer(associated, folium_map)
        unassigned_group = build_unassigned_facility_layer(facilities, folium_map)
        folium_map.add_child(map_utils.build_legend(66))

        commune_layers = [
            feature
            for feature in commune_group._children.values()
            if feature.__class__.__name__ == "GeoJson"
        ]
        polygon_count = len(commune_layers)
        expected_colors = {
            "Urbain": "#279B91",
            "Mixte": "#E6AD55",
            "Rural": "#648BB8",
        }
        for layer in commune_layers:
            feature = layer.data["features"][0]
            style = layer.style_function(feature)
            self.assertEqual(
                style["fillColor"],
                expected_colors[feature["properties"]["milieu"]],
            )
            self.assertEqual(style["color"], "#FFFFFF")
            self.assertEqual(style["weight"], 1.15)
            self.assertEqual(style["fillOpacity"], 0.70)
            self.assertEqual(
                layer.highlight_function(feature)["color"],
                "#0B2235",
            )
            self.assertTrue(layer.popup_keep_highlighted)
        marker_count = sum(
            1
            for marker in facility_group._children.values()
            if marker.__class__.__name__ == "CircleMarker"
        )
        unassigned_markers = [
            marker for marker in unassigned_group._children.values()
            if marker.__class__.__name__ == "CircleMarker"
        ]
        associated_locations = {
            tuple(marker.location)
            for marker in facility_group._children.values()
            if marker.__class__.__name__ == "CircleMarker"
        }
        unassigned_locations = {
            tuple(marker.location) for marker in unassigned_markers
        }
        expected_unassigned_locations = {
            (row["lat"], row["lon"])
            for row in facilities
            if row["commune_code"] is None
        }
        self.assertEqual(polygon_count, 146)
        self.assertEqual(marker_count, 826)
        self.assertEqual(len(unassigned_markers), 66)
        self.assertEqual(marker_count + len(unassigned_markers), 892)
        self.assertEqual(unassigned_locations, expected_unassigned_locations)
        self.assertTrue(associated_locations.isdisjoint(unassigned_locations))
        self.assertTrue(
            all(
                marker.options["color"] == THEME.text_muted
                for marker in unassigned_markers
            )
        )
        for marker in unassigned_markers:
            popup = next(
                child for child in marker._children.values()
                if child.__class__.__name__ == "Popup"
            )
            self.assertIn(
                "Hors périmètre des 146 polygones",
                popup.html.render(),
            )
        map_html = folium_map.get_root().render()
        self.assertIn("Population 2014", map_html)
        self.assertIn("Population 2024:</b> 24 435", map_html)
        self.assertIn("Établissements associés", map_html)
        self.assertIn("Hors polygones (66)", map_html)
        first_commune = communes[0]
        first_associated_count = sum(
            row["commune_code"] == first_commune["commune_code"]
            for row in associated
        )
        self.assertIn(
            f"Établissements associés:</b> {first_associated_count}",
            map_html,
        )
        self.assertEqual(
            geojson_bounds(enriched),
            [[34.50599078168922, -6.2422943115234375],
             [35.92297639918852, -3.80401611328125]],
        )

    def test_overview_markers_use_association_color(self):
        import folium

        folium_map = folium.Map(location=[35.20, -5.45], zoom_start=7)
        group = map_utils.build_facility_layer(
            [{
                "lat": 35.2,
                "lon": -5.45,
                "facility_type": "pharmacy",
                "commune_code": "1",
                "name": "Pharmacie test",
            }],
            folium_map,
            color_by_type=False,
        )
        marker = next(iter(group._children.values()))
        self.assertEqual(marker.options["color"], "#2878B5")

    def test_enterprise_base_maps_include_satellite_and_hybrid_labels(self):
        from map_utils import get_initial_map

        satellite_map = get_initial_map("Satellite Haute Résolution")
        satellite = satellite_map._tta_base_layers["satellite"]
        self.assertTrue(satellite.show)
        self.assertIn("World_Imagery", satellite.tiles)

        hybrid_map = get_initial_map("Satellite Hybride")
        self.assertTrue(hybrid_map._tta_base_layers["hybrid"].show)
        self.assertTrue(hybrid_map._tta_hybrid_labels.show)
        self.assertIn(
            "CARTO",
            hybrid_map._tta_base_layers["light"].options["attribution"],
        )

    def test_public_base_map_tiles_do_not_require_api_keys(self):
        configs = map_utils.BASE_MAP_CONFIGS
        self.assertIn(
            "https://{s}.basemaps.cartocdn.com/light_all/",
            configs["light"]["tiles"],
        )
        self.assertIn(
            "https://{s}.basemaps.cartocdn.com/dark_all/",
            configs["dark"]["tiles"],
        )
        self.assertIn(
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/",
            configs["satellite"]["tiles"],
        )
        self.assertEqual(configs["standard"]["tiles"], "OpenStreetMap")
        self.assertIn(
            "https://{s}.tile.opentopomap.org/",
            configs["terrain"]["tiles"],
        )
        self.assertNotIn("apikey", str(configs).casefold())

    def test_enterprise_facility_markers_use_typed_svg_badges(self):
        import folium
        from map_utils import build_facility_layer

        folium_map = folium.Map(location=[35.2, -5.45], zoom_start=7)
        layer = build_facility_layer(
            [{
                "lat": 35.2,
                "lon": -5.45,
                "facility_type": "hospital",
                "commune_code": "01",
                "name": "Centre de santé",
            }],
            folium_map,
            symbol_markers=True,
        )
        marker = next(iter(layer._children.values()))
        self.assertEqual(marker.__class__.__name__, "Marker")
        self.assertIn("#1D4ED8", marker.icon.options["html"])
        self.assertIn("<path", marker.icon.options["html"])
        self.assertNotIn("<text", marker.icon.options["html"])

    def test_map_legend_uses_vector_facility_icons(self):
        import folium
        from map_utils import add_enterprise_map_controls

        folium_map = folium.Map(location=[35.2, -5.45], zoom_start=7)
        add_enterprise_map_controls(
            folium_map,
            {},
            {},
            [[35.0, -6.0], [36.0, -5.0]],
            facility_count=1,
            unassigned_count=0,
        )
        rendered = folium_map.get_root().render()
        self.assertIn("tta-map-legend-badge", rendered)
        self.assertIn("stroke-width='1.75'", rendered)
        self.assertNotIn(">H</text>", rendered)

    def test_bubbles_heatmap_and_quick_controls_use_real_map_data(self):
        from map_utils import (
            add_enterprise_map_controls,
            build_heatmap_layer,
            build_proportional_bubble_layer,
            get_initial_map,
        )

        communes = [{
            "commune_code": "01",
            "name_fr": "Commune A",
            "centroid_lat": 35.2,
            "centroid_lon": -5.4,
            "population_2024": 120,
        }, {
            "commune_code": "02",
            "name_fr": "Commune B",
            "centroid_lat": 35.3,
            "centroid_lon": -5.5,
            "population_2024": 80,
        }]
        facilities = [{
            "commune_code": "01",
            "facility_type": "hospital",
            "lat": 35.21,
            "lon": -5.41,
        }, {
            "commune_code": None,
            "facility_type": "pharmacy",
            "lat": 35.31,
            "lon": -5.51,
        }]
        folium_map = get_initial_map("satellite")
        bubbles = build_proportional_bubble_layer(
            communes, facilities[:1], folium_map
        )
        heatmap = build_heatmap_layer(facilities, folium_map, show=False)
        bounds = [[35.1, -5.6], [35.4, -5.3]]
        add_enterprise_map_controls(
            folium_map,
            {"bubbles": bubbles, "heatmap": heatmap},
            folium_map._tta_base_layers,
            bounds,
            facility_count=2,
            unassigned_count=1,
        )
        rendered = folium_map.get_root().render()
        self.assertEqual(
            sum(child.__class__.__name__ == "CircleMarker" for child in bubbles._children.values()),
            1,
        )
        self.assertIn("35.21", rendered)
        self.assertIn("tta-map-toolrail", rendered)
        self.assertIn("Indicateurs valid", rendered)
        self.assertIn("setTimeout(function()", rendered)
        self.assertNotIn("<script>\n    <script>", rendered)


if __name__ == "__main__":
    unittest.main()

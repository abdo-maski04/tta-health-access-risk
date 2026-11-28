"""Tests unitaires et d'intégrité pour l'audit scientifique des données GeoVulnera TTA."""

import json
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COMMUNES_CSV = ROOT / "data" / "processed" / "communes_TTA_2024.csv"
COMMUNES_GEOJSON = ROOT / "data" / "processed" / "communes_TTA.geojson"
WHITELIST_JSON = ROOT / "config" / "hospital_whitelist.json"
RAW_MS_BY_COMMUNE = (
    ROOT / "data" / "raw" / "ministere_sante" / "official_public_health_by_commune_2025.csv"
)
RAW_MS_TTA = ROOT / "data" / "raw" / "ministere_sante" / "official_public_health_tta_2025.csv"
MS_BY_COMMUNE = ROOT / "data" / "processed" / "official_public_health_by_commune_2025.csv"
MS_TTA = ROOT / "data" / "processed" / "official_public_health_tta_2025.csv"
V2_CSV = ROOT / "data" / "processed" / "v2" / "travel_time_TTA_2024.csv"
V2_GEOJSON = ROOT / "data" / "processed" / "v2" / "travel_routes_TTA.geojson"
REGISTRY_CSV = ROOT / "data" / "metadata" / "scientific_validation_registry.csv"


class ScientificDataIntegrityTests(unittest.TestCase):
    """Vérifications scientifiques des sources et des données traitées."""

    def test_communes_complete_and_consistent(self):
        """Vérifie l'existence exacte et la correspondance des 146 communes."""
        df_c = pd.read_csv(COMMUNES_CSV, dtype={"commune_code": str})
        gdf_c = gpd.read_file(COMMUNES_GEOJSON)
        self.assertEqual(len(df_c), 146)
        self.assertEqual(len(gdf_c), 146)
        self.assertEqual(set(df_c["commune_code"]), set(gdf_c["commune_code"]))

    def test_ministere_by_commune_has_all_146_codes(self):
        """Vérifie 146 communes, 146 codes uniques valides et les totaux sanitaires du fichier dérivé."""
        df_ref = pd.read_csv(COMMUNES_CSV, dtype={"commune_code": str})
        df_ms = pd.read_csv(MS_BY_COMMUNE, dtype={"commune_code": str})
        self.assertEqual(len(df_ms), 146)
        self.assertEqual(df_ms["commune_code"].notna().sum(), 146)
        self.assertEqual(df_ms["commune_code"].nunique(), 146)
        self.assertEqual(df_ms["commune_name"].nunique(), 146)
        self.assertEqual(set(df_ms["commune_code"]), set(df_ref["commune_code"]))
        # Cohérence arithmétique interne des totaux sanitaires
        computed_total = (
            df_ms["CSU"] + df_ms["CSR"] + df_ms["DR"] + df_ms["Hospitals"] + df_ms["Specialized"]
        )
        self.assertTrue((computed_total == df_ms["Total_Public_Official"]).all())

    def test_ministere_tta_323_establishments_and_parity_with_raw(self):
        """Vérifie les 323 établissements, la validité des codes, les totaux croisés et la parité brute."""
        df_ref = pd.read_csv(COMMUNES_CSV, dtype={"commune_code": str})
        ref_codes = set(df_ref["commune_code"])

        df_raw_com = pd.read_csv(RAW_MS_BY_COMMUNE, dtype=str).fillna("")
        df_drv_com = pd.read_csv(MS_BY_COMMUNE, dtype=str).fillna("")
        self.assertEqual(list(df_raw_com.columns), list(df_drv_com.columns))
        self.assertEqual(len(df_raw_com), len(df_drv_com))
        business_cols_com = [c for c in df_raw_com.columns if c != "commune_code"]
        self.assertTrue(df_raw_com[business_cols_com].equals(df_drv_com[business_cols_com]))

        df_raw_tta = pd.read_csv(RAW_MS_TTA, dtype=str).fillna("")
        df_drv_tta = pd.read_csv(MS_TTA, dtype=str).fillna("")
        self.assertEqual(len(df_drv_tta), 323)
        self.assertEqual(list(df_raw_tta.columns), list(df_drv_tta.columns))
        business_cols_tta = [c for c in df_raw_tta.columns if c != "commune_code"]
        self.assertTrue(df_raw_tta[business_cols_tta].equals(df_drv_tta[business_cols_tta]))

        non_empty_codes = df_drv_tta.loc[df_drv_tta["commune_code"] != "", "commune_code"]
        self.assertEqual(len(non_empty_codes), 323)
        self.assertTrue(set(non_empty_codes).issubset(ref_codes))
        # Rattachement des 34 établissements des arrondissements de Tanger à MA-01-511-0100 (D-007)
        tanger_arr = df_drv_tta[df_drv_tta["arrondissement"] != ""]
        self.assertEqual(len(tanger_arr), 34)
        self.assertTrue((tanger_arr["commune_code"] == "MA-01-511-0100").all())
        # Cohérence croisée des totaux par commune entre les 323 établissements et la table communale
        counts_by_code = df_drv_tta["commune_code"].value_counts().to_dict()
        for _, row in df_drv_com.iterrows():
            self.assertEqual(
                counts_by_code.get(row["commune_code"], 0), int(row["Total_Public_Official"])
            )

    def test_hospital_whitelist_enriched_and_valid(self):
        """Vérifie les 15 hôpitaux de la whitelist, leurs coordonnées et leurs catégories."""
        with open(WHITELIST_JSON, encoding="utf-8") as f:
            wl = json.load(f)
        facs = wl.get("facilities", [])
        self.assertEqual(len(facs), 15)
        categories = {fac.get("category") for fac in facs}
        self.assertTrue({"CHU", "CHR", "CHP", "HPr"}.issubset(categories))
        for fac in facs:
            lat = float(fac["latitude"])
            lon = float(fac["longitude"])
            self.assertTrue(34.5 <= lat <= 36.2)
            self.assertTrue(-6.5 <= lon <= -3.5)
            self.assertIn("capacity_beds_est", fac)
            self.assertGreater(fac["capacity_beds_est"], 0)

    def test_v2_routes_and_speeds_realistic(self):
        """Vérifie que toutes les vitesses moyennes sont physiquement réalistes (15 à 115 km/h)."""
        df_v2 = pd.read_csv(V2_CSV)
        self.assertEqual(len(df_v2), 146)
        speeds = df_v2["distance_km"] / (df_v2["temps_min"] / 60.0)
        self.assertTrue((speeds >= 15.0).all())
        # Plafond à 115 km/h aligné sur le contrôle de vitesse suspecte de scripts/audit_travel_routes_and_times.py
        # (inclut les liaisons autoroutières ORS comme Malloussa -> CHU Tanger à ~80.8 km/h).
        self.assertTrue((speeds <= 115.0).all())

    def test_scientific_registry_verdicts(self):
        """Vérifie le registre de validation scientifique et l'absence de données D (inutilisables)."""
        self.assertTrue(REGISTRY_CSV.exists())
        df_reg = pd.read_csv(REGISTRY_CSV)
        self.assertGreaterEqual(len(df_reg), 10)
        verdicts = set(df_reg["verdict"])
        self.assertNotIn("D", verdicts)
        self.assertIn("A", verdicts)
        self.assertIn("B", verdicts)


if __name__ == "__main__":
    unittest.main()

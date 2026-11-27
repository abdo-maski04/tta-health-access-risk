"""Audit scientifique précis des rasters MNT Copernicus."""

from pathlib import Path

import rasterio

ROOT = Path(__file__).resolve().parents[1]
DEM_TIF = ROOT / "data" / "processed" / "terrain" / "tta_dem_30m.tif"
HS_TIF = ROOT / "data" / "processed" / "terrain" / "tta_hillshade_30m.tif"
SLOPE_TIF = ROOT / "data" / "processed" / "terrain" / "tta_slope_degrees_30m.tif"
META_JSON = ROOT / "data" / "processed" / "terrain" / "tta_terrain_metadata.json"
RAW_DEM_DIR = ROOT / "data" / "raw" / "terrain" / "copernicus_dem"


def main():
    print("=== AUDIT SCIENTIFIQUE DU MNT COPERNICUS ===")
    with rasterio.open(DEM_TIF) as src:
        bounds = src.bounds
        crs = str(src.crs)
        w = src.width
        h = src.height
        count = src.count
        dtype = str(src.dtypes[0])
        res_x_deg = src.res[0]
        res_y_deg = src.res[1]
        arr = src.read(1)

    # Conversion en mètres à 35°N
    # 1 deg lat = 111,000 m ; 1 deg lon = 111,000 * cos(35°) = 90,925 m
    res_x_m = res_x_deg * 90925.0
    res_y_m = res_y_deg * 111000.0

    print(f"1. Fichier : {DEM_TIF.name}")
    print(f"   - CRS exact : {crs}")
    print(f"   - Dimensions : {w} colonnes x {h} lignes ({count} bande, dtype={dtype})")
    print(f"   - Emprise géographique : Ouest={bounds.left:.4f}, Sud={bounds.bottom:.4f}, Est={bounds.right:.4f}, Nord={bounds.top:.4f}")
    print(f"   - Résolution angulaire : {res_x_deg:.6f}° (X) x {res_y_deg:.6f}° (Y) (~{res_x_deg*3600:.1f} arc-sec)")
    print(f"   - Résolution métrique réelle au sol : {res_x_m:.1f} m (X) x {res_y_m:.1f} m (Y)")
    print(f"   - Altitudes réelles : min={arr.min():.1f} m, max={arr.max():.1f} m, moyenne={arr[arr > 2].mean():.1f} m")

    # Vérification des tuiles sources
    raw_tiles = list(RAW_DEM_DIR.glob("*.tif"))
    print(f"\n2. Tuiles brutes dans {RAW_DEM_DIR.name} : {len(raw_tiles)} tuiles")
    valid_tiles = 0
    for t in raw_tiles:
        try:
            with rasterio.open(t) as r_src:
                r_src.read(1)
                print(f"   - {t.name} : shape={r_src.shape}, res={r_src.res[0]*3600:.1f} arc-sec (~30m), status=VALIDE")
                valid_tiles += 1
        except Exception as e:
            print(f"   - {t.name} : INCOMPLET / CORROMPU ({e})")

    # Conclusion sur la résolution
    print("\n3. CONCLUSION SCIENTIFIQUE SUR LA RÉSOLUTION :")
    print("   - Résolution native source déclarée dans nom : 30 m (Copernicus DEM GLO-30, 1 arc-seconde)")
    print(f"   - Résolution réelle du fichier généré : ~{round(res_x_m)} m x {round(res_y_m)} m (~400 m)")
    print("   - Méthode de génération : Interpolation spatiale Rbf multiquadrique à partir de points d'altitude réels (sommets rifains, communes et échantillons Open-Meteo)")
    print("   - Diagnostic d'intégrité : Le fichier tta_dem_30m.tif NE DOIT PAS être présenté comme un raster à 30m natif !")
    print("   - Action requise : Renommer/documenter en 'tta_dem_regional_400m.tif' ou clarifier explicitement dans les métadonnées la grille régionale régularisée à 400m pour affichage web fluide.")


if __name__ == "__main__":
    main()

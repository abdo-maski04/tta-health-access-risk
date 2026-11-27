"""Traitement et mosaïquage du MNT Copernicus DEM GLO-30 pour la région Tanger-Tétouan-Al Hoceïma.
Génération du MNT découpé, du Hillshade (ombrage), des pentes (degrés/pourcent) et du PNG PyDeck BitmapLayer.
"""

import json
from pathlib import Path

import geopandas as gpd
import matplotlib.cm as cm
import numpy as np
import rasterio
from PIL import Image
from rasterio.mask import mask
from rasterio.merge import merge

ROOT = Path(__file__).resolve().parents[1]
RAW_DEM_DIR = ROOT / "data" / "raw" / "terrain" / "copernicus_dem"
PROCESSED_TERRAIN_DIR = ROOT / "data" / "processed" / "terrain"
COMMUNES_GEOJSON = ROOT / "data" / "processed" / "communes_TTA.geojson"


def compute_hillshade_and_slope(dem_array, cell_size_x, cell_size_y, azimuth=315.0, altitude=45.0):
    """Calcule le Hillshade (ombrage) et la pente (degrés et %) selon la méthode de Horn."""
    # Convert angles to radians
    azimuth_rad = np.radians(360.0 - azimuth + 90.0)
    altitude_rad = np.radians(altitude)

    # Gradients using central differences (Horn's method)
    # dem shape is (H, W)
    pad_dem = np.pad(dem_array, pad_width=1, mode="edge")
    dz_dx = (pad_dem[1:-1, 2:] - pad_dem[1:-1, :-2]) / (2.0 * cell_size_x)
    dz_dy = (pad_dem[:-2, 1:-1] - pad_dem[2:, 1:-1]) / (2.0 * cell_size_y)

    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = np.degrees(slope_rad)
    slope_pct = np.tan(slope_rad) * 100.0

    aspect_rad = np.arctan2(dz_dy, -dz_dx)
    # Hillshade formula
    shaded = np.sin(altitude_rad) * np.cos(slope_rad) + np.cos(altitude_rad) * np.sin(slope_rad) * np.cos(
        azimuth_rad - aspect_rad
    )
    # Clip and scale to 0 - 255
    hillshade = np.clip(shaded, 0, 1) * 255.0

    return hillshade.astype(np.float32), slope_deg.astype(np.float32), slope_pct.astype(np.float32)


def main():
    PROCESSED_TERRAIN_DIR.mkdir(parents=True, exist_ok=True)
    print("=== DÉBUT DU TRAITEMENT DU RELIEF COPERNICUS DEM ===")

    # 1. Identifier les tuiles DEM
    tif_files = sorted(list(RAW_DEM_DIR.glob("*.tif")))
    print(f"Nombre de tuiles DEM brutes trouvées : {len(tif_files)}")
    if not tif_files:
        raise RuntimeError(f"Aucune tuile DEM trouvée dans {RAW_DEM_DIR}")

    # 2. Ouvrir et fusionner
    src_files = [rasterio.open(f) for f in tif_files]
    mosaic, out_trans = merge(src_files)
    meta = src_files[0].meta.copy()
    for s in src_files:
        s.close()

    meta.update(
        {
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_trans,
            "count": 1,
            "dtype": "float32",
            "nodata": -9999.0,
        }
    )

    # 3. Découpage sur l'emprise régionale TTA (+ marge de 0.05°)
    gdf_com = gpd.read_file(COMMUNES_GEOJSON)
    minx, miny, maxx, maxy = gdf_com.total_bounds
    margin = 0.05
    from shapely.geometry import box

    bbox_poly = box(minx - margin, miny - margin, maxx + margin, maxy + margin)

    # Write temporary merged raster to mask
    temp_merged = PROCESSED_TERRAIN_DIR / "temp_mosaic.tif"
    with rasterio.open(temp_merged, "w", **meta) as dest:
        dest.write(mosaic[0].astype(np.float32), 1)

    with rasterio.open(temp_merged) as src:
        out_image, out_transform = mask(src, [bbox_poly], crop=True)
        out_meta = src.meta.copy()

    if temp_merged.exists():
        temp_merged.unlink()

    dem = out_image[0].astype(np.float32)
    # Replace nodata or invalid values
    dem[dem < -100] = 0.0

    out_meta.update(
        {"height": dem.shape[0], "width": dem.shape[1], "transform": out_transform, "dtype": "float32"}
    )

    # Sauvegarde DEM 30m
    out_dem_path = PROCESSED_TERRAIN_DIR / "tta_dem_30m.tif"
    with rasterio.open(out_dem_path, "w", **out_meta) as dst:
        dst.write(dem, 1)
    print(f"[OK] DEM régional enregistré : {out_dem_path} (Taille: {dem.shape})")

    # 4. Calcul de la résolution en mètres (approximation WGS84 au centre de TTA ~35°N)
    # 1 deg lat ~ 111,000 m ; 1 deg lon ~ 111,000 * cos(35°) ~ 90,925 m
    res_x_deg = abs(out_transform.a)
    res_y_deg = abs(out_transform.e)
    cell_x_m = res_x_deg * 90925.0
    cell_y_m = res_y_deg * 111000.0

    print(f"Résolution spatiale moyenne : {cell_x_m:.2f} m (X) x {cell_y_m:.2f} m (Y)")

    # 5. Calcul Hillshade et Pentes
    hillshade, slope_deg, slope_pct = compute_hillshade_and_slope(
        dem, cell_x_m, cell_y_m, azimuth=315.0, altitude=45.0
    )

    # Sauvegarde Hillshade GeoTIFF
    out_hillshade_path = PROCESSED_TERRAIN_DIR / "tta_hillshade_30m.tif"
    with rasterio.open(out_hillshade_path, "w", **out_meta) as dst:
        dst.write(hillshade, 1)
    print(f"[OK] Hillshade GeoTIFF enregistré : {out_hillshade_path}")

    # Sauvegarde Slope Degrees GeoTIFF
    out_slope_path = PROCESSED_TERRAIN_DIR / "tta_slope_degrees_30m.tif"
    with rasterio.open(out_slope_path, "w", **out_meta) as dst:
        dst.write(slope_deg, 1)
    print(f"[OK] Pente GeoTIFF enregistrée : {out_slope_path}")

    # 6. Génération de l'image PNG optimisée pour PyDeck BitmapLayer
    # Bounding box bounds: [west, south, east, north]
    west = out_transform.c
    north = out_transform.f
    east = west + out_transform.a * dem.shape[1]
    south = north + out_transform.e * dem.shape[0]
    bounds = [float(west), float(south), float(east), float(north)]

    # Downsample slightly for ultra-fast web rendering if size is very large (> 2000 px)
    h, w = hillshade.shape
    scale = 1
    if max(h, w) > 1600:
        scale = max(h, w) // 1600 + 1

    hs_sub = hillshade[::scale, ::scale]
    dem_sub = dem[::scale, ::scale]

    # Création d'une image compositée : relief teinté hypsométrique avec ombrage
    # Normalisation DEM 0..1 pour colormap terrain/gist_earth
    norm_dem = np.clip(dem_sub / 2000.0, 0, 1)
    cmap = cm.get_cmap("gist_earth")
    hypso_rgb = cmap(norm_dem)[:, :, :3]  # (H, W, 3) in [0, 1]

    # Ombrage normalisé 0..1
    hs_norm = (hs_sub / 255.0)[:, :, np.newaxis]

    # Fusion ombrage + hypsométrie : Multiply blend
    blend = hypso_rgb * (0.3 + 0.7 * hs_norm)
    blend_uint8 = np.clip(blend * 255.0, 0, 255).astype(np.uint8)

    # Transparence pour les zones hors-terre (mer = 0 m ou nodata)
    alpha = np.where(dem_sub <= 0.5, 0, 190).astype(np.uint8)
    rgba = np.dstack([blend_uint8, alpha])

    out_png_path = PROCESSED_TERRAIN_DIR / "tta_hillshade_display.png"
    img = Image.fromarray(rgba, "RGBA")
    img.save(out_png_path, "PNG", optimize=True)
    print(f"[OK] Image PyDeck BitmapLayer générée : {out_png_path} (Dimensions: {img.size}, Bounds: {bounds})")

    # Métadonnées JSON
    stats = {
        "source": "Copernicus DEM GLO-30 (European Space Agency / AWS Open Data)",
        "resolution_arcsec": "1 arc-second (~30 meters)",
        "bounds": bounds,
        "west": bounds[0],
        "south": bounds[1],
        "east": bounds[2],
        "north": bounds[3],
        "elevation_min_m": float(np.min(dem)),
        "elevation_max_m": float(np.max(dem)),
        "elevation_mean_m": float(np.mean(dem[dem > 0])),
        "slope_max_deg": float(np.max(slope_deg)),
        "slope_mean_deg": float(np.mean(slope_deg[dem > 0])),
        "display_png": str(out_png_path.name),
        "status": "VALIDATED"
    }
    with open(PROCESSED_TERRAIN_DIR / "tta_terrain_metadata.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"[OK] Métadonnées terrain enregistrées : {PROCESSED_TERRAIN_DIR / 'tta_terrain_metadata.json'}")
    return 0


if __name__ == "__main__":
    main()

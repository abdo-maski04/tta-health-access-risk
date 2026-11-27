"""Téléchargeur parallèle résilient pour les tuiles Copernicus DEM GLO-30 avec reprise sur erreur."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "terrain" / "copernicus_dem"

TILES = [
    "Copernicus_DSM_COG_10_N35_00_W007_00_DEM",
    "Copernicus_DSM_COG_10_N35_00_W006_00_DEM",
    "Copernicus_DSM_COG_10_N35_00_W005_00_DEM",
    "Copernicus_DSM_COG_10_N35_00_W004_00_DEM",
    "Copernicus_DSM_COG_10_N34_00_W007_00_DEM",
    "Copernicus_DSM_COG_10_N34_00_W006_00_DEM",
    "Copernicus_DSM_COG_10_N34_00_W005_00_DEM",
    "Copernicus_DSM_COG_10_N34_00_W004_00_DEM",
]

BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"


def download_tile(tile_name: str) -> Path:
    out_file = RAW_DIR / f"{tile_name}.tif"
    url = f"{BASE_URL}/{tile_name}/{tile_name}.tif"

    # Vérifier la taille totale
    head_resp = requests.head(url, timeout=15)
    total_size = int(head_resp.headers.get("Content-Length", 0))

    existing_size = out_file.stat().st_size if out_file.exists() else 0
    if existing_size >= total_size and total_size > 0:
        print(f"  [OK] {tile_name}.tif complet ({existing_size / 1024 / 1024:.1f} MB)")
        return out_file

    headers = {}
    mode = "wb"
    if existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"
        mode = "ab"
        print(f"  [REPRISE] {tile_name}.tif à {existing_size / 1024 / 1024:.1f} / {total_size / 1024 / 1024:.1f} MB")
    else:
        print(f"  [DEBUT] {tile_name}.tif ({total_size / 1024 / 1024:.1f} MB)")

    resp = requests.get(url, headers=headers, stream=True, timeout=30)
    if resp.status_code not in (200, 206):
        resp.raise_for_status()

    with open(out_file, mode) as f:
        for chunk in resp.iter_content(chunk_size=256 * 1024):
            if chunk:
                f.write(chunk)

    print(f"  [TERMINE] {tile_name}.tif ({out_file.stat().st_size / 1024 / 1024:.1f} MB)")
    return out_file


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print("Démarrage du téléchargement parallèle (4 workers) des 8 tuiles Copernicus DEM GLO-30...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download_tile, tile): tile for tile in TILES}
        for future in as_completed(futures):
            tile = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"  [ERREUR] {tile} : {e}")

    print(f"\nTous les téléchargements terminés en {time.time() - t0:.1f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

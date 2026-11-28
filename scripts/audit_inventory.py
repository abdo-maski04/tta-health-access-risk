"""Inventaire exhaustif des fichiers de données et configurations de GeoVulnera TTA.
Calcule les empreintes SHA256, les tailles, les formats et les propriétés spatiales.
"""

import hashlib
import json
from pathlib import Path

import pandas as pd
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DIRS_TO_SCAN = [
    ROOT / "data" / "raw",
    ROOT / "data" / "processed",
    ROOT / "data" / "interim",
    ROOT / "data" / "metadata",
    ROOT / "data" / "cache",
    ROOT / "config",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def inspect_file(path: Path) -> dict:
    info = {
        "rel_path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "size_bytes": path.stat().st_size,
        "size_mb": round(path.stat().st_size / (1024 * 1024), 3),
        "suffix": path.suffix.lower(),
        "sha256": sha256_file(path),
        "details": "",
        "record_count": None,
        "crs": None,
    }

    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, nrows=5)
            # count lines
            with open(path, encoding="utf-8", errors="ignore") as f:
                lines = sum(1 for _ in f) - 1
            info["record_count"] = max(0, lines)
            info["details"] = f"Columns: {list(df.columns[:8])}..."
        elif path.suffix.lower() == ".geojson":
            with open(path, encoding="utf-8", errors="ignore") as f:
                gj = json.load(f)
            feats = gj.get("features", [])
            info["record_count"] = len(feats)
            crs_info = gj.get("crs", {}).get("properties", {}).get("name", "EPSG:4326 (assumed)")
            info["crs"] = str(crs_info)
            if feats:
                props = list(feats[0].get("properties", {}).keys())
                geom_type = feats[0].get("geometry", {}).get("type", "Unknown")
                info["details"] = f"Geom: {geom_type}, Props: {props[:6]}..."
        elif path.suffix.lower() == ".json":
            with open(path, encoding="utf-8", errors="ignore") as f:
                j = json.load(f)
            if isinstance(j, list):
                info["record_count"] = len(j)
                info["details"] = f"List of {len(j)} items"
            elif isinstance(j, dict):
                info["details"] = f"Dict with keys: {list(j.keys())[:6]}"
                if "facilities" in j:
                    info["record_count"] = len(j["facilities"])
        elif path.suffix.lower() in [".tif", ".tiff"]:
            with rasterio.open(path) as src:
                info["details"] = (
                    f"Raster shape: {src.shape}, bands: {src.count}, dtype: {src.dtypes[0]}"
                )
                info["crs"] = str(src.crs)
    except Exception as e:
        info["details"] = f"Inspection error: {e}"

    return info


def main():
    records = []
    for d in DIRS_TO_SCAN:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_file():
                # Ignore .git or temporary files if any
                if any(part.startswith(".") for part in p.parts):
                    continue
                records.append(inspect_file(p))

    df = pd.DataFrame(records)
    out_csv = ROOT / "data" / "metadata" / "data_inventory_sha256.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"Inventaire achevé : {len(df)} fichiers inspectés.")
    print(f"Enregistré dans : {out_csv}")

    # Résumé rapide par extension
    print("\nRépartition par type de fichier :")
    print(df["suffix"].value_counts())


if __name__ == "__main__":
    main()

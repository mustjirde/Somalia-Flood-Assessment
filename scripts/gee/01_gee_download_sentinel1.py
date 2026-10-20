"""
01_gee_download_sentinel1.py
FAO SWALIM Emergency Mapping — El Niño Floods 2026

Downloads pre- and post-event Sentinel-1 VV GeoTIFFs from Google Earth Engine
and saves them into the organized project folder structure so that
02_flood_extraction_arcpy.py can find them automatically.

─── ENVIRONMENT ────────────────────────────────────────────────────────────
Run this script with the STANDARD Python environment (NOT ArcGIS Pro's Python).
Install dependencies once:
    pip install earthengine-api geemap

Authenticate once (opens a browser):
    earthengine authenticate

─── USAGE ──────────────────────────────────────────────────────────────────
1. Edit EVENT_CONFIG below (dates, AOI, orbit pass).
2. Run:
       python 01_gee_download_sentinel1.py
3. Downloads land in:
       data/satellite/sentinel1/pre_event/
       data/satellite/sentinel1/post_event/
4. A manifest JSON is written so 02_flood_extraction_arcpy.py picks up the
   exact file paths without any manual input.
"""

import ee
import geemap
import os
import sys
import json
import logging
from datetime import datetime, timezone

# Add this script's folder to sys.path so paths_config can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths_config as cfg

# ─── LOGGING ────────────────────────────────────────────────────────────────
os.makedirs(cfg.LOGS_DIR, exist_ok=True)
log_file = os.path.join(cfg.LOGS_DIR, f"gee_download_{datetime.now():%Y%m%d_%H%M%S}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ─── EVENT CONFIGURATION ────────────────────────────────────────────────────
# Edit these values for your flood event before running.
EVENT_CONFIG = {
    "event_name": "ElNino_Floods_2026",

    # Pre-event: calm period before flooding
    "pre_start":  "2026-09-01",
    "pre_end":    "2026-09-20",

    # Post-event: during / after flooding
    "post_start": "2026-10-01",
    "post_end":   "2026-10-13",

    # Area of interest — Somalia national bounding box.
    # To use a district instead, replace with a tighter bounding box or
    # pass a GeoJSON polygon.
    "aoi_bbox": [40.98, -1.69, 51.41, 12.02],   # [west, south, east, north]

    # Sentinel-1 acquisition geometry
    "orbit_pass": "DESCENDING",   # "ASCENDING" or "DESCENDING"

    # Output resolution (metres). 10 m = native S-1 IW resolution.
    # Use 20 or 30 for faster downloads covering large areas.
    "scale_m": 10,

    # GEE cloud project ID (required for new-style ee.Initialize)
    # Set to None to use the legacy quota project from earthengine authenticate.
    "gee_project": None,
}

# ─── GEE HELPERS ────────────────────────────────────────────────────────────

def initialize_ee(project=None):
    """Initialise the Earth Engine Python API."""
    try:
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
        log.info("Earth Engine initialised.")
    except ee.EEException as exc:
        log.error(
            "Earth Engine initialisation failed: %s\n"
            "Run: earthengine authenticate", exc
        )
        sys.exit(1)


def build_s1_composite(start: str, end: str, aoi: ee.Geometry,
                        orbit_pass: str = "DESCENDING") -> ee.Image:
    """Return a median Sentinel-1 VV composite for the given period."""
    col = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.eq("orbitProperties_pass", orbit_pass))
        .select("VV")
    )
    count = col.size().getInfo()
    log.info("  Scenes found (%s – %s): %d", start, end, count)
    if count == 0:
        raise RuntimeError(
            f"No Sentinel-1 scenes for {start}–{end} with orbit={orbit_pass}. "
            "Try expanding the date range or switching ASCENDING/DESCENDING."
        )
    return col.median()


def download_to_tif(image: ee.Image, out_path: str, aoi: ee.Geometry,
                     scale_m: int, label: str) -> None:
    """Download a single-band EE image to a local GeoTIFF via geemap."""
    if os.path.exists(out_path):
        log.warning("  File already exists, overwriting: %s", out_path)
    log.info("  Downloading %s …", label)
    log.info("  → %s", out_path)

    geemap.download_ee_image(
        image=image,
        filename=out_path,
        region=aoi,
        scale=scale_m,
        crs="EPSG:4326",
        overwrite=True,
    )
    size_mb = os.path.getsize(out_path) / 1_048_576
    log.info("  Done: %.1f MB", size_mb)


def save_manifest(config: dict, pre_path: str, post_path: str) -> None:
    """Write a JSON manifest so 02_flood_extraction_arcpy.py can auto-detect inputs."""
    manifest = {
        **config,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "pre_event_raster":  pre_path,
        "post_event_raster": post_path,
    }
    with open(cfg.MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    log.info("Manifest saved: %s", cfg.MANIFEST)


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 65)
    log.info("GEE Sentinel-1 Downloader — FAO SWALIM El Niño Floods 2026")
    log.info("=" * 65)

    cfg.ensure_all_dirs()
    initialize_ee(project=EVENT_CONFIG.get("gee_project"))

    ecfg = EVENT_CONFIG
    west, south, east, north = ecfg["aoi_bbox"]
    aoi = ee.Geometry.Rectangle([west, south, east, north])

    event     = ecfg["event_name"]
    orbit     = ecfg["orbit_pass"]
    scale     = ecfg["scale_m"]

    # Build output filenames that encode the date range for traceability
    pre_fname  = f"{event}_S1_VV_pre_{ecfg['pre_start']}_{ecfg['pre_end']}.tif"
    post_fname = f"{event}_S1_VV_post_{ecfg['post_start']}_{ecfg['post_end']}.tif"
    pre_path   = os.path.join(cfg.PRE_DIR,  pre_fname)
    post_path  = os.path.join(cfg.POST_DIR, post_fname)

    # ── Pre-event ────────────────────────────────────────────────────────────
    log.info("\n[1/2] Pre-event composite: %s → %s", ecfg["pre_start"], ecfg["pre_end"])
    pre_img = build_s1_composite(ecfg["pre_start"], ecfg["pre_end"], aoi, orbit)
    download_to_tif(pre_img, pre_path, aoi, scale, "pre-event VV")

    # ── Post-event ───────────────────────────────────────────────────────────
    log.info("\n[2/2] Post-event composite: %s → %s", ecfg["post_start"], ecfg["post_end"])
    post_img = build_s1_composite(ecfg["post_start"], ecfg["post_end"], aoi, orbit)
    download_to_tif(post_img, post_path, aoi, scale, "post-event VV")

    # ── Manifest ─────────────────────────────────────────────────────────────
    save_manifest(ecfg, pre_path, post_path)

    log.info("\n" + "=" * 65)
    log.info("Downloads complete.")
    log.info("Next step: open ArcGIS Pro and run 02_flood_extraction_arcpy.py")
    log.info("=" * 65)


if __name__ == "__main__":
    main()


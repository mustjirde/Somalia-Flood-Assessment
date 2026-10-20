"""
02_flood_extraction_arcpy.py
FAO SWALIM Emergency Mapping — El Niño Floods 2026

Reads Sentinel-1 VV GeoTIFFs produced by 01_gee_download_sentinel1.py,
performs change-detection flood extraction, and writes results to the GDB
and the outputs/statistics/ folder.

─── ENVIRONMENT ────────────────────────────────────────────────────────────
Run inside ArcGIS Pro:
  • Python window  (run directly)
  • Notebook cell  (run directly)
  • Script tool    (point the .pyt at this file)

Required license: Spatial Analyst.

─── HOW INPUT RASTERS ARE RESOLVED (in order) ──────────────────────────────
1. Manifest file  data/satellite/sentinel1/download_manifest.json
   (created automatically by 01_gee_download_sentinel1.py)
2. Most-recent .tif found in sentinel1/pre_event/ and sentinel1/post_event/
3. Tkinter open-file dialog  (fallback when neither folder has data yet)
"""

import os
import sys
import json
import csv
import glob
import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

import arcpy
from arcpy.sa import (
    Con, ExtractByMask, FocalStatistics, Int,
    RegionGroup, SetNull, ZonalStatisticsAsTable,
)

arcpy.env.overwriteOutput = True

# ─── PATH CONFIG ─────────────────────────────────────────────────────────────
# Allow import of paths_config from the same scripts\ folder.
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)
import paths_config as cfg

# ─── LOGGING ─────────────────────────────────────────────────────────────────
os.makedirs(cfg.LOGS_DIR, exist_ok=True)
_log_file = os.path.join(cfg.LOGS_DIR, f"flood_extraction_{datetime.now():%Y%m%d_%H%M%S}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


def msg(text: str) -> None:
    """Write to ArcGIS Messages panel and the log file."""
    try:
        arcpy.AddMessage(text)
    except Exception:
        pass
    log.info(text)


# ─── INPUT RESOLUTION ────────────────────────────────────────────────────────

def _latest_tif(folder: str) -> str | None:
    """Return the most-recently-modified .tif in folder, or None."""
    tifs = sorted(
        glob.glob(os.path.join(folder, "*.tif")),
        key=os.path.getmtime,
        reverse=True,
    )
    return tifs[0] if tifs else None


def resolve_raster_paths() -> tuple[str, str]:
    """
    Find pre- and post-event rasters in this priority order:
      1. download_manifest.json  (from 01_gee_download_sentinel1.py)
      2. Most-recent .tif in pre_event/ and post_event/ folders
      3. User file-dialog
    Returns (pre_path, post_path).
    """
    # 1. Manifest
    if os.path.exists(cfg.MANIFEST):
        with open(cfg.MANIFEST, encoding="utf-8") as fh:
            manifest = json.load(fh)
        pre  = manifest.get("pre_event_raster", "")
        post = manifest.get("post_event_raster", "")
        if arcpy.Exists(pre) and arcpy.Exists(post):
            msg(f"Using manifest rasters:\n  PRE:  {pre}\n  POST: {post}")
            return pre, post
        msg("Manifest found but raster paths are missing — falling back to folder scan.")

    # 2. Folder scan
    pre  = _latest_tif(cfg.PRE_DIR)
    post = _latest_tif(cfg.POST_DIR)
    if pre and post:
        msg(f"Auto-detected rasters:\n  PRE:  {pre}\n  POST: {post}")
        return pre, post
    if pre and not post:
        msg("Pre-event raster found but no post-event raster — please select via dialog.")
    elif post and not pre:
        msg("Post-event raster found but no pre-event raster — please select via dialog.")
    else:
        msg("No rasters found in sentinel1 folders — please select via dialog.")

    # 3. File dialogs
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    if not pre:
        messagebox.showinfo("Pre-event raster",
                            "Select the pre-event Sentinel-1 VV GeoTIFF.",
                            parent=root)
        pre = filedialog.askopenfilename(
            title="Select PRE-EVENT Sentinel-1 VV GeoTIFF",
            filetypes=[("GeoTIFF", "*.tif *.tiff"), ("All files", "*.*")],
            initialdir=cfg.PRE_DIR,
        )
    if not post:
        messagebox.showinfo("Post-event raster",
                            "Select the post-event Sentinel-1 VV GeoTIFF.",
                            parent=root)
        post = filedialog.askopenfilename(
            title="Select POST-EVENT Sentinel-1 VV GeoTIFF",
            filetypes=[("GeoTIFF", "*.tif *.tiff"), ("All files", "*.*")],
            initialdir=cfg.POST_DIR,
        )
    root.destroy()

    if not pre or not post:
        raise ValueError("Both pre- and post-event rasters are required.")
    return pre, post


# ─── DISTRICT SELECTION ──────────────────────────────────────────────────────

def select_district() -> str | None:
    """
    Show a Tkinter listbox with all unique values from DIST_FIELD.
    Returns the selected district name, or None to process all districts.
    """
    districts = []
    with arcpy.da.SearchCursor(cfg.DIST_FC, [cfg.DIST_FIELD]) as cur:
        for row in cur:
            if row[0] and row[0] not in districts:
                districts.append(row[0])
    districts.sort()

    selected = [None]

    root = tk.Tk()
    root.title("Select District")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    tk.Label(root, text="Select a district  (or click All Districts):").pack(padx=10, pady=(10, 4))

    frame = tk.Frame(root)
    frame.pack(padx=10, pady=4, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL)
    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set,
                         selectmode=tk.SINGLE, width=40, height=20)
    scrollbar.config(command=listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    for d in districts:
        listbox.insert(tk.END, d)

    # Allow typing to filter
    filter_var = tk.StringVar()
    tk.Label(root, text="Filter:").pack(padx=10, anchor="w")
    filter_entry = tk.Entry(root, textvariable=filter_var, width=38)
    filter_entry.pack(padx=10, pady=(0, 4))

    def _on_filter(*_):
        term = filter_var.get().lower()
        listbox.delete(0, tk.END)
        for d in districts:
            if term in d.lower():
                listbox.insert(tk.END, d)

    filter_var.trace_add("write", _on_filter)

    def _confirm():
        sel = listbox.curselection()
        if sel:
            selected[0] = listbox.get(sel[0])
        root.destroy()

    def _all():
        selected[0] = None
        root.destroy()

    btn_frame = tk.Frame(root)
    btn_frame.pack(padx=10, pady=8)
    tk.Button(btn_frame, text="Confirm Selection", command=_confirm, width=20).pack(side=tk.LEFT, padx=4)
    tk.Button(btn_frame, text="All Districts",     command=_all,     width=20).pack(side=tk.LEFT, padx=4)

    root.mainloop()
    return selected[0]


# ─── FLOOD EXTRACTION ────────────────────────────────────────────────────────

def extract_flood(pre_raster: str, post_raster: str,
                  district_name: str | None = None) -> tuple[str, str, str]:
    """
    Run the full flood extraction pipeline.

    Parameters
    ----------
    pre_raster     Path to pre-event Sentinel-1 VV GeoTIFF.
    post_raster    Path to post-event Sentinel-1 VV GeoTIFF.
    district_name  admin2Name value to clip to, or None for all districts.

    Returns
    -------
    (flood_raster_path, stats_table_path, csv_path)
    """
    arcpy.CheckOutExtension("Spatial")
    try:
        # ── Validate inputs ──────────────────────────────────────────────────
        for p in (pre_raster, post_raster, cfg.DIST_FC, cfg.GDB):
            if not arcpy.Exists(p):
                raise FileNotFoundError(f"Required input not found: {p}")

        # ── Build AOI ────────────────────────────────────────────────────────
        if district_name:
            safe = district_name.replace("'", "''")
            where = f"{cfg.DIST_FIELD} = '{safe}'"
            aoi_lyr = "district_aoi_lyr"
            arcpy.management.MakeFeatureLayer(cfg.DIST_FC, aoi_lyr, where)
            count = int(arcpy.management.GetCount(aoi_lyr).getOutput(0))
            if count == 0:
                raise ValueError(f"No features matched district '{district_name}'.")
            msg(f"AOI: {district_name} ({count} polygon(s))")
        else:
            aoi_lyr = cfg.DIST_FC
            msg("AOI: All districts (national extent)")

        # ── Environment ──────────────────────────────────────────────────────
        desc = arcpy.Describe(pre_raster)
        cell = float(desc.meanCellWidth)
        arcpy.env.snapRaster              = pre_raster
        arcpy.env.cellSize                = pre_raster
        arcpy.env.outputCoordinateSystem  = desc.spatialReference
        arcpy.env.workspace               = cfg.GDB

        # ── Clip rasters to AOI ──────────────────────────────────────────────
        msg("Clipping rasters to AOI …")
        pre  = ExtractByMask(pre_raster,  aoi_lyr)
        post = ExtractByMask(post_raster, aoi_lyr)

        # ── Focal Median smoothing (speckle reduction) ────────────────────────
        msg(f"Focal Median smoothing (radius={cfg.SMOOTHING_M} m) …")
        radius_cells = max(1, int(round(cfg.SMOOTHING_M / cell)))
        nbr          = arcpy.sa.NbrCircle(radius_cells, "CELL")
        pre_sm  = FocalStatistics(pre,  nbr, "MEDIAN", "DATA")
        post_sm = FocalStatistics(post, nbr, "MEDIAN", "DATA")

        # ── Backscatter difference ────────────────────────────────────────────
        msg("Computing backscatter difference (post − pre) …")
        difference = post_sm - pre_sm

        diff_name = _make_name("s1_vv_diff", district_name)
        difference.save(os.path.join(cfg.GDB, diff_name))
        msg(f"  Saved difference raster: {diff_name}")

        # ── Flood threshold ───────────────────────────────────────────────────
        msg(f"Applying flood threshold ({cfg.THRESHOLD} dB) …")
        candidate = Con(difference < cfg.THRESHOLD, 1)

        # ── Connected-pixel noise removal ─────────────────────────────────────
        msg(f"Removing small clusters (min pixels = {cfg.MIN_PIXEL_COUNT}) …")
        regions      = RegionGroup(candidate, "EIGHT", "WITHIN", "NO_LINK")
        count_raster = arcpy.sa.Lookup(regions, "COUNT")
        flood        = Int(SetNull(count_raster < cfg.MIN_PIXEL_COUNT, candidate))

        flood_name = _make_name("flood_extent", district_name)
        flood_path = os.path.join(cfg.GDB, flood_name)
        flood.save(flood_path)
        msg(f"Flood raster saved: {flood_name}")

        # ── District-level statistics ─────────────────────────────────────────
        msg("Computing district flood statistics …")
        if desc.spatialReference.type != "Projected":
            msg("WARNING: CRS is geographic — area values will be in degrees, not hectares. "
                "Project to a metre-based CRS for accurate area statistics.")
        cell_area_ha = (cell * abs(float(desc.meanCellHeight))) / 10_000.0
        area_raster  = Con(flood == 1, cell_area_ha)

        stats_name  = _make_name("district_flood_stats", district_name)
        stats_table = os.path.join(cfg.GDB, stats_name)
        ZonalStatisticsAsTable(aoi_lyr, cfg.DIST_FIELD, area_raster,
                               stats_table, "DATA", "SUM")
        msg(f"Statistics table saved: {stats_name}")

        # ── Export CSV ────────────────────────────────────────────────────────
        os.makedirs(cfg.STATS_DIR, exist_ok=True)
        csv_fname = f"{_make_name('district_flood_stats', district_name)}_{datetime.now():%Y%m%d_%H%M%S}.csv"
        csv_path  = os.path.join(cfg.STATS_DIR, csv_fname)
        _write_csv(stats_table, csv_path)
        msg(f"Statistics CSV:    {csv_path}")

        return flood_path, stats_table, csv_path

    finally:
        arcpy.CheckInExtension("Spatial")


def _make_name(base: str, district: str | None) -> str:
    """Build a GDB-safe name: base_districtname or base_all."""
    suffix = district.replace(" ", "_")[:30] if district else "all"
    return f"{base}_{suffix}"


def _write_csv(stats_table: str, csv_path: str) -> None:
    """Export the zonal stats table to a CSV with readable column names."""
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow([cfg.DIST_FIELD, "flooded_area_ha", "flooded_area_km2"])
        with arcpy.da.SearchCursor(stats_table, [cfg.DIST_FIELD, "SUM"]) as rows:
            for district_id, hectares in rows:
                hectares = 0.0 if hectares is None else float(hectares)
                writer.writerow([district_id, round(hectares, 4), round(hectares / 100.0, 6)])


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    msg("=" * 65)
    msg("Flood Extraction — FAO SWALIM El Niño Floods 2026")
    msg("=" * 65)
    msg(f"Log file: {_log_file}")

    # Step 1: resolve raster inputs
    msg("\n[Step 1/3] Resolving Sentinel-1 input rasters …")
    pre_path, post_path = resolve_raster_paths()

    # Step 2: select district
    msg("\n[Step 2/3] District selection …")
    district = select_district()
    district_label = district if district else "ALL DISTRICTS"
    msg(f"Selected: {district_label}")

    # Step 3: run extraction
    msg(f"\n[Step 3/3] Running flood extraction for: {district_label}")
    flood_path, stats_table, csv_path = extract_flood(pre_path, post_path, district)

    msg("\n" + "=" * 65)
    msg("DONE.")
    msg(f"  Flood raster : {flood_path}")
    msg(f"  Stats table  : {stats_table}")
    msg(f"  Stats CSV    : {csv_path}")
    msg("=" * 65)


if __name__ == "__main__":
    main()


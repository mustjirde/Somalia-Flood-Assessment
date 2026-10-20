# Somalia Flood Assessment

A geospatial emergency-mapping portfolio for Somalia, combining Google Earth Engine, Sentinel-1 radar, ArcGIS Pro/ArcPy, and district-level impact statistics.

## Featured projects

- **El Niño 2026 Flood Assessment** — pre/post Sentinel-1 VV change detection, flood extent extraction, district statistics, and map exports.
- **River Breakages Assessment** — riverine flood-breakage inventory and satellite-image assessment along the Juba–Shabelle corridor.
- **Somali Climate Service** — climate information and early-warning workflows for decision support.
- **Hirshabelle Mapping** — regional mapping and flood-risk visualization.
- **LIDAR and Terrain Processing** — DEM mosaicking and terrain-data preparation.
- **Land-Cover Validation** — structured desktop validation and geospatial quality control.
- **Weather Forecast Mapping** — repeatable forecast-map production and reporting.
- **Soil Survey and IBLI** — field/research support for soil, rangeland, and index-based livestock insurance analysis.
- **Hal-Abuur Climate Baseline** — climate-baseline and land-use analysis workflows.

## Repository structure

```
docs/
  project-catalog.md       Portfolio catalogue and methods
  gee-arcgis-workflow.md   Google Earth Engine to ArcGIS workflow
scripts/
  gee/                     Earth Engine download examples
  arcgis/                  ArcPy extraction examples
```

## Core workflow

1. Select a pre-event and post-event period in Google Earth Engine.
2. Download Sentinel-1 VV imagery for the area of interest.
3. Run ArcGIS Pro processing to smooth, difference, threshold, and clean flood candidates.
4. Calculate district-level flooded area.
5. Export reproducible statistics and emergency maps.

## Data and privacy

Large rasters, geodatabases, ArcGIS project files, imagery, personal information, and client-confidential documents are intentionally excluded. Add local data under ignored folders when running the workflow.

## Author

Mustjirde — GIS, remote sensing, hydrology, and climate-information workflows for Somalia.

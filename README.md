# Somalia Flood Assessment

A public-safe geospatial early-warning portfolio for Somalia, combining Google Earth Engine, Sentinel-1 radar, ArcGIS Pro/ArcPy, and district-level impact statistics.

## Relevant samples for the IGAD Early Warning Expert application

1. [Google Earth Engine Sentinel-1 acquisition script](scripts/gee/01_gee_download_sentinel1.py)  
   Reproducible Earth-observation data filtering and download workflow.

2. [ArcPy flood-extraction script](scripts/arcgis/02_flood_extraction_arcpy.py)  
   Automated geoprocessing workflow for raster differencing, flood classification, connected-pixel filtering, and district-level statistics.

Supporting documentation:

- [Google Earth Engine to ArcGIS workflow](docs/gee-arcgis-workflow.md)
- [Project catalogue](docs/project-catalog.md)

## Featured projects

- **El Niño 2026 Flood Assessment** — pre/post Sentinel-1 VV change detection, flood extent extraction, district statistics, and map exports.
- **River Breakages Assessment** — riverine flood-breakage inventory and satellite-image assessment along the Juba–Shabelle corridor.
- **Somali Climate Service** — climate-information and early-warning workflows for decision support.
- **Hirshabelle Mapping** — regional mapping and flood-risk visualization.
- **LIDAR and Terrain Processing** — DEM mosaicking and terrain-data preparation.
- **Land-Cover Validation** — structured desktop validation and geospatial quality control.
- **Weather Forecast Mapping** — repeatable forecast-map production and reporting.
- **Soil Survey and IBLI** — field/research support for soil, rangeland, and index-based livestock-insurance analysis.
- **Hal-Abuur Climate Baseline** — climate-baseline and land-use analysis workflows.

## Core workflow

1. Select pre-event and post-event periods in Google Earth Engine.
2. Download Sentinel-1 VV imagery for the area of interest.
3. Run ArcGIS Pro processing to smooth, difference, threshold, and clean flood candidates.
4. Calculate district-level flooded area.
5. Export reproducible statistics and emergency maps.

## Data and privacy

Large rasters, geodatabases, ArcGIS project files, imagery, personal information, credentials, and client-confidential documents are intentionally excluded.

## Author

Mustjirde — GIS, remote sensing, hydrology, and climate-information workflows for Somalia.

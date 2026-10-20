# Google Earth Engine to ArcGIS flood workflow

This repository documents the workflow used in the El Niño Floods 2026 project.

## Google Earth Engine stage

- Authenticate with the Earth Engine CLI.
- Filter Sentinel-1 GRD imagery by date, area of interest, polarization, and orbit pass.
- Create pre-event and post-event composites.
- Export GeoTIFF rasters at the selected working resolution.
- Record the exact inputs in a manifest for reproducibility.

## ArcGIS Pro stage

- Resolve the two rasters from the manifest or input folders.
- Clip to all districts or a selected district.
- Apply focal-median smoothing to reduce radar speckle.
- Calculate post-event minus pre-event backscatter.
- Apply a configurable flood threshold.
- Remove small connected regions.
- Calculate flooded area by district and export CSV statistics.

## Reproducibility and safety

The workflow is designed to keep data acquisition separate from analysis. Credentials, local paths, rasters, geodatabases, and ArcGIS project files stay outside version control. Thresholds and event dates should be recorded in a local configuration file for each event.

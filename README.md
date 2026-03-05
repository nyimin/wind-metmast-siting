# Terrain Complexity & MCDA Measurement Siting Pipeline

This Python pipeline automates the analysis of terrain complexity and spatial suitability for wind resource measurement campaigns (Met Masts and LiDARs) according to wind industry standards (WAsP & IEC 61400-1).

## Features

- **Automated Data Acquisition**: Automatically fetches 30m NASADEM elevation data and 10m ESA WorldCover Land Use Land Cover (LULC) data overlapping the site boundary using the Planetary Computer STAC API.
- **Industry Standard RIX**: Computes the WAsP Ruggedness Index (RIX) according to strict industry standards (30% slope threshold over a 3.5km focal radius) to generate a Continuous RIX Heatmap.
- **MCDA Siting Engine**: Replaces rudimentary heuristics with a powerful Multi-Criteria Decision Analysis (MCDA) framework scoring every localized pixel on:
  - High Elevation (Representativeness)
  - Distance to Site Centroid (Centrality)
  - Low Terrain Complexity (RIX)
  - Land Use Suitability (esa-worldcover weighting)
- **Categorical Classification**: Automatically classifies the site into Simple, Semi-Complex, or Complex terrain.
- **Rich Deliverables**: Generates an informative visual map (`terrain_analysis_map.png`) and a comprehensive Markdown report (`terrain_analysis_report.md`).

## Methodology

### Terrain Classification

Wind industry best practice typically applies linearised micro-siting models (like WAsP) cautiously. General heuristics for site classification are applied:

- **Simple Terrain:** Max Slope < 10% AND Mean Site RIX = 0%. Standard models perform perfectly with low uncertainty.
- **Semi-Complex Terrain:** Max Slope > 10% BUT Mean Site RIX <= 5%. True complex terrain is highly localized. Standard flow modelling may still be acceptable if turbines are micro-sited away from steep slopes.
- **Complex Terrain:** Mean Site RIX > 5%. Significant widespread flow detachment. Linear models break down; advanced CFD evaluation is highly recommended.

### Siting Suitability

The tool scores the measurement site suitability (0.0 to 1.0) by merging multiple normalized spatial rasters. Weights and specific LULC class preferences can be easily configured in `config.py`. Exclusions (such as prohibiting masts too close to the boundary or on slopes > 10% per IEC guidelines) are rigidly enforced.

## Installation

Ensure you have a Python 3.9+ virtual environment activated with the following key requirements installed:

- `geopandas`
- `rasterio`
- `shapely`
- `numpy`
- `scipy`
- `matplotlib`
- `requests`
- `pystac-client`
- `planetary-computer`
- `pyproj`

## Usage

1. **Input Data**: Place a Geopackage named `site_boundary.gpkg` in the project root containing your continuous site boundary polygon(s) in a geographic/WGS84 projection.
2. **Execute**: Run the main pipeline entry point:
   ```bash
   python main.py
   ```
3. **Review**: The pipeline will log its STAC downloads to the console. When finished, open the generated outputs in the project root:
   - `terrain_analysis_map.png`
   - `terrain_analysis_report.md`

## Configuration

Modify `config.py` to adjust threshold weights or bounds.

- `MAST_BUFFER_M`: Minimum distance the mast must be installed from the project edge (meters).
- `W_ELEV`, `W_CENTC`, `W_RIX`, `W_LULC`: The fractional weights applied to the MCDA synthesis.
- `LULC_WEIGHTS`: Dictionary mapping ESA WorldCover distinct class IDs (e.g. 10 for Trees, 30 for Grassland, 50 for Built-up) to normalized 0-1 preference scores.

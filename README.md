# Terrain Complexity & MCDA Measurement Siting Pipeline

This Python pipeline automates the analysis of terrain complexity and spatial suitability for wind resource measurement campaigns (Met Masts and LiDARs) according to wind industry professional standards (WAsP & IEC 61400-1).

## Features

- **Automated Data Acquisition**: Automatically fetches 30m NASADEM elevation data and 10m ESA WorldCover Land Use Land Cover (LULC) data overlapping the site boundary using the Planetary Computer STAC API.
- **Industry Standard RIX**: Computes the WAsP Ruggedness Index (RIX) to classify terrain complexity according to strict industry standards (30% slope threshold over a 3.5km focal radius).
- **MCDA Siting Engine**: Identifies optimal measurement locations using a powerful Multi-Criteria Decision Analysis (MCDA) framework scoring every localized pixel on:
  - High Elevation Representativeness (Targeting the 75th percentile elevation to avoid unrepresentative valleys or isolated spikes)
  - Topographic Position Index (TPI) (Explicitly preferring ridges over valleys to capture dominant flow)
  - Low Terrain Complexity (Avoiding high WAsP RIX for reduced flow separation)
  - Aerodynamic Clearance (Enforcing a >200m buffer from forests and built-up obstacles)
  - Centrality (Distance to Site Centroid)
- **Extensive Filtering**: Enforces physical minimum spacings (e.g. 2000m between candidate mast locations).
- **Categorical Classification**: Automatically classifies the site into Simple, Semi-Complex, or Complex terrain dependent on Maximum Slope and Maximum RIX.
- **Rich Deliverables**: Generates an informative visual map (`terrain_analysis_map.png`) and a comprehensive Markdown Technical Memo (`terrain_analysis_report.md`).

## Methodology

### Terrain Classification

Wind industry best practice typically applies linearised micro-siting models (like WAsP) cautiously. General heuristics for site classification are applied:

- **Simple Terrain:** Max Slope < 15% AND Max Site RIX <= 0.5%. Standard models perform perfectly with low uncertainty.
- **Semi-Complex Terrain:** Max Slope > 15% BUT Max Site RIX <= 5%. True complex terrain is highly localized. Standard flow modelling may still be acceptable if turbines are micro-sited carefully.
- **Complex Terrain:** Max Site RIX > 5%. Significant widespread flow detachment. Linear models break down; advanced CFD evaluation is highly recommended.

### Siting Suitability

The tool scores the measurement site suitability (0.0 to 1.0) by merging multiple normalized spatial rasters. Weights and specific LULC class preferences can be easily configured in `config/settings.py`. Exclusions (such as prohibiting masts too close to the boundary, near forests/obstacles, or on slopes > 10% per IEC guidelines) are rigidly enforced.

## Repository Structure

The codebase is organized into modular packages for maintainability:

```text
terrain_complexity_check/
│
├── config/
│   └── settings.py          # Weightings, thresholds, and operational flags
├── data/
│   └── acquisition.py       # STAC API interaction and Rasterio processing
├── terrain/
│   ├── slope.py             # 2nd derivative slope calculations
│   ├── rix.py               # WAsP RIX focal convolutions and TPI
│   └── classification.py    # Logic for categorizing terrain complexity
├── siting/
│   ├── constraints.py       # Boolean exclusion masking (boundaries, obstacles, steep slopes)
│   └── mcda.py              # Core MCDA synthesis algorithm
├── reporting/
│   └── report_generator.py  # Comprehensive markdown memo generation
├── visualization/
│   └── maps.py              # Matplotlib dual-panel map generation
│
└── main.py                  # Entrypoint pipeline runner
```

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
3. **Review**: The pipeline will block and log to the console. When finished, open the generated outputs in the project root:
   - `terrain_analysis_map.png`
   - `terrain_analysis_report.md`

## Configuration

Modify `config/settings.py` to adjust thresholds, weights, or bounds for your specific region or campaign needs.

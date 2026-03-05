# main.py
"""
================================================================================
Terrain Complexity Analysis Pipeline — WAsP RIX & MCDA Lidar Siting
================================================================================
Analyses a proposed wind-power site to generate a continuous WAsP RIX heatmap
and identifies optimal Lidar placement locations using Multi-Criteria Decision
Analysis (MCDA).

Usage:
    python main.py
    (expects site_boundary.gpkg in the same directory)
================================================================================
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys

from config import SITE_BOUNDARY_FILE, BUFFER_DISTANCE_M, OUTPUT_MAP, OUTPUT_REPORT
from data_loading import load_and_reproject, generate_buffer, fetch_dem, fetch_lulc
from spatial_analysis import calculate_slope, compute_mcda_suitability
from reporting import generate_map, print_report, generate_markdown_report


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gpkg_path  = os.path.join(script_dir, SITE_BOUNDARY_FILE)

    if not os.path.isfile(gpkg_path):
        sys.exit(f"ERROR: '{gpkg_path}' not found. Place the file next to this script.")

    # 1. Load & reproject
    gdf_site_utm, gdf_site_wgs = load_and_reproject(gpkg_path)

    # 2. Buffer
    gdf_buffer_utm, gdf_buffer_wgs = generate_buffer(gdf_site_utm, BUFFER_DISTANCE_M)

    # 3. Fetch DEM (with cache)
    dem, dem_profile = fetch_dem(gdf_buffer_wgs, gdf_buffer_utm, script_dir)

    # 4. Slope
    slope_pct = calculate_slope(dem, dem_profile)

    # 4.5 Fetch LULC
    lulc = fetch_lulc(gdf_buffer_wgs, dem_profile, script_dir)

    # 5. Continuous RIX heatmap & MCDA Objective Function
    results = compute_mcda_suitability(dem, slope_pct, lulc, dem_profile, gdf_site_utm)

    # 6. Map
    map_path = os.path.join(script_dir, OUTPUT_MAP)
    generate_map(dem, slope_pct, dem_profile, gdf_site_utm, gdf_buffer_utm, results, map_path)

    # 7. Console report
    print_report(results)

    # 8. Markdown report
    report_path = os.path.join(script_dir, OUTPUT_REPORT)
    generate_markdown_report(
        results, dem, dem_profile,
        gdf_site_utm, gdf_buffer_utm,
        report_path, OUTPUT_MAP,
    )

    print("\nPipeline complete. ✓")

if __name__ == "__main__":
    main()

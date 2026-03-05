# main.py
"""
================================================================================
Terrain Complexity Analysis Pipeline — WAsP RIX & MCDA Measurement Siting
================================================================================
Analyses a proposed wind-power site to classify terrain complexity, generate
a continuous WAsP RIX heatmap, determine Topographic Position Index (TPI),
and identify optimal Lidar/Met Mast placement locations using Multi-Criteria 
Decision Analysis (MCDA).

Usage:
    python main.py
    (expects site_boundary.gpkg in the same directory)
================================================================================
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys

from config.settings import SITE_BOUNDARY_FILE, BUFFER_DISTANCE_M, OUTPUT_MAP, OUTPUT_REPORT
from data.acquisition import load_and_reproject, generate_buffer, fetch_dem, fetch_lulc
from terrain.slope import calculate_slope
from terrain.rix import calculate_rix, calculate_tpi
from terrain.classification import classify_terrain
from siting.constraints import generate_constraints
from siting.mcda import compute_mcda_siting
from reporting.report_generator import print_report, generate_markdown_report
from visualization.maps import generate_map
import numpy as np

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gpkg_path  = os.path.join(script_dir, SITE_BOUNDARY_FILE)

    if not os.path.isfile(gpkg_path):
        sys.exit(f"ERROR: '{gpkg_path}' not found. Place the file next to this script.")

    # 1. Load & reproject
    gdf_site_utm, gdf_site_wgs = load_and_reproject(gpkg_path)

    # 2. Buffer
    gdf_buffer_utm, gdf_buffer_wgs = generate_buffer(gdf_site_utm, BUFFER_DISTANCE_M)

    # 3. Fetch DEM & LULC (with cache)
    dem, dem_profile = fetch_dem(gdf_buffer_wgs, gdf_buffer_utm, script_dir)
    lulc = fetch_lulc(gdf_buffer_wgs, dem_profile, script_dir)

    # 4. Terrain Analytics
    slope_pct = calculate_slope(dem, dem_profile)
    
    valid_mask = ~np.isnan(dem)
    transform = dem_profile["transform"]
    cell_size = abs(transform.a)
    
    rix_heatmap, radius_px = calculate_rix(slope_pct, cell_size, valid_mask)
    tpi = calculate_tpi(dem, cell_size, valid_mask)

    # 5. Siting Constraints & Classification
    cg_res = generate_constraints(gdf_site_utm, dem_profile, slope_pct, valid_mask, lulc)
    site_mask = cg_res["site_mask"]
    
    rix_site = np.where(site_mask, rix_heatmap, np.nan)
    slope_site = np.where(site_mask, slope_pct, np.nan)
    
    terrain_results = classify_terrain(rix_site, slope_site)

    # 6. MCDA Siting
    mcda_results = compute_mcda_siting(
        dem, tpi, rix_heatmap, lulc, 
        cg_res["dist_to_centroid_m"], cg_res["eval_mask"], cg_res["exclusion_mask"], 
        dem_profile, slope_pct
    )

    # 7. Map
    map_path = os.path.join(script_dir, OUTPUT_MAP)
    generate_map(dem, dem_profile, gdf_site_utm, gdf_buffer_utm, mcda_results, cg_res, map_path)

    # 8. Reports
    from config.settings import FOCAL_RADIUS_M
    print_report(terrain_results, mcda_results, FOCAL_RADIUS_M, radius_px, slope_pct)
    
    report_path = os.path.join(script_dir, OUTPUT_REPORT)
    generate_markdown_report(
        terrain_results, mcda_results, dem, slope_pct, dem_profile,
        gdf_site_utm, gdf_buffer_utm, FOCAL_RADIUS_M, radius_px,
        report_path, OUTPUT_MAP
    )

    print("\nPipeline complete. ✓")

if __name__ == "__main__":
    main()

# config.py
"""
Configuration settings for Terrain Complexity Analysis.
"""

SITE_BOUNDARY_FILE   = "site_boundary.gpkg"
OUTPUT_MAP           = "terrain_analysis_map.png"
OUTPUT_REPORT        = "terrain_analysis_report.md"
BUFFER_DISTANCE_M    = 5000          # 5 km buffer for DEM acquisition
FOCAL_RADIUS_M       = 3500          # 3.5 km focal radius for RIX kernel

# --- Slope Thresholds ---
IEC_SLOPE_THRESHOLD  = 10.0          # slope in % (≈ 5.71°) for micrositing/local checks
WASP_RIX_THRESHOLD   = 30.0          # slope in % (≈ 17°) for true WAsP RIX definition

# --- MCDA Parameters ---
MAST_BUFFER_M        = 200.0         # minimum distance from site boundary for mast (m)
W_ELEV               = 0.3           # weight for high elevation (representativeness)
W_CENTC              = 0.2           # weight for centrality (distance to centroid)
W_RIX                = 0.2           # weight for low complexity
W_LULC               = 0.3           # weight for Land Use / Land Cover suitability

# --- LULC Class Weights (ESA WorldCover) ---
# 10: Trees, 20: Shrubland, 30: Grassland, 40: Cropland, 50: Built-up, 60: Bare/Sparse,
# 70: Snow/Ice, 80: Open water, 90: Herbaceous wetland, 95: Mangroves, 100: Moss/Lichen
LULC_WEIGHTS = {
    10: 0.1,  # Trees (avoid high displacement heights/turbulence)
    20: 0.8,  # Shrubland (good)
    30: 1.0,  # Grassland (ideal)
    40: 0.6,  # Cropland (medium - land use conflicts)
    50: 0.0,  # Built-up (exclude)
    60: 1.0,  # Bare / sparse vegetation (ideal)
    70: 0.0,  # Snow/Ice (exclude)
    80: 0.0,  # Open water (exclude)
    90: 0.3,  # Wetland (marginal)
    95: 0.1,  # Mangroves (poor)
    100: 0.8  # Moss/Lichen (good)
}

# --- Data Acquisition ---
DEM_COLLECTION       = "nasadem"
LULC_COLLECTION      = "esa-worldcover"
DEM_CACHE_DIR        = ".dem_cache"  # local cache folder for downloaded tiles

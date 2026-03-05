# terrain/classification.py
"""
Terrain categorization logic module.
Determines if a site is Simple, Semi-Complex, or Complex terrain.
"""

import numpy as np
from config.settings import COMPLEX_SLOPE_THRESHOLD, COMPLEX_RIX_THRESHOLD, SIMPLE_RIX_THRESHOLD

def classify_terrain(rix_site: np.ndarray, slope_site: np.ndarray) -> dict:
    """
    Classify terrain based on Max RIX and Max Slope across the site.
    Returns the category and associated statistics.
    """
    print("=" * 70)
    print("STEP 5 — Terrain Classification")
    print("=" * 70)
    
    max_rix = float(np.nanmax(rix_site))
    mean_rix = float(np.nanmean(rix_site))
    min_rix = float(np.nanmin(rix_site))
    
    max_slope = float(np.nanmax(slope_site))
    
    if max_rix > COMPLEX_RIX_THRESHOLD:
        category = "Complex Terrain"
        is_complex = True
    elif max_slope > COMPLEX_SLOPE_THRESHOLD and max_rix > SIMPLE_RIX_THRESHOLD:
        category = "Semi-Complex Terrain"
        is_complex = False
    elif max_slope > COMPLEX_SLOPE_THRESHOLD and max_rix <= SIMPLE_RIX_THRESHOLD:
        category = "Semi-Complex Terrain"
        is_complex = False
    else:
        category = "Simple Terrain"
        is_complex = False

    print(f"  Max site RIX  : {max_rix:.2f} %")
    print(f"  Max site slope: {max_slope:.2f} %")
    print(f"  Classification: {category}\n")

    return {
        "terrain_category": category,
        "is_complex": is_complex,
        "rix_site_max": max_rix,
        "rix_site_mean": mean_rix,
        "rix_site_min": min_rix,
        "max_slope_site": max_slope
    }

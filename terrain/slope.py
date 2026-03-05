# terrain/slope.py
"""
Slope calculation module.
Computes terrain slope from DEM.
"""

import numpy as np

def calculate_slope(dem: np.ndarray, profile: dict) -> np.ndarray:
    """Compute slope in percent (rise/run × 100) using numpy gradient."""
    print("=" * 70)
    print("STEP 4 — Calculating terrain slope (%)")
    print("=" * 70)

    transform = profile["transform"]
    dx = abs(transform.a)
    dy = abs(transform.e)

    dzdx = np.gradient(dem, dx, axis=1)
    dzdy = np.gradient(dem, dy, axis=0)

    slope_pct = np.sqrt(dzdx**2 + dzdy**2) * 100.0
    slope_pct[np.isnan(dem)] = np.nan

    print(f"  Cell size     : {dx:.2f} × {dy:.2f} m")
    print(f"  Max  slope    : {np.nanmax(slope_pct):.2f} %")
    print(f"  Mean slope    : {np.nanmean(slope_pct):.2f} %")
    print(f"  Slope computed: ✓\n")
    return slope_pct

# terrain/rix.py
"""
WAsP Ruggedness Index (RIX) and Topographic Position Index (TPI) module.
Handles focal statistics on DEMs.
"""

import numpy as np
from scipy.signal import fftconvolve

from config.settings import WASP_RIX_THRESHOLD, FOCAL_RADIUS_M, TPI_RADIUS_M

def _create_circular_kernel(radius_px: int) -> np.ndarray:
    """Create a 2D circular boolean kernel with given pixel radius."""
    diameter = 2 * radius_px + 1
    y, x = np.ogrid[-radius_px:radius_px + 1, -radius_px:radius_px + 1]
    mask = (x**2 + y**2) <= radius_px**2
    kernel = mask.astype(np.float64)
    kernel /= kernel.sum()  # normalise so convolution gives the mean
    return kernel

def calculate_rix(slope_pct: np.ndarray, cell_size: float, valid_mask: np.ndarray) -> np.ndarray:
    """
    Compute WAsP RIX Continuous Heatmap.
    """
    print(f"  Computing RIX Heatmap (Threshold: {WASP_RIX_THRESHOLD}%, Radius: {FOCAL_RADIUS_M}m) …")
    radius_px = int(round(FOCAL_RADIUS_M / cell_size))
    
    binary_rix_mask = np.zeros_like(slope_pct, dtype=np.float64)
    binary_rix_mask[valid_mask & (slope_pct > WASP_RIX_THRESHOLD)] = 1.0

    valid_float = valid_mask.astype(np.float64)
    kernel = _create_circular_kernel(radius_px)
    
    sum_complex = fftconvolve(binary_rix_mask, kernel * kernel.size, mode="same")
    sum_valid   = fftconvolve(valid_float, kernel * kernel.size, mode="same")

    rix_heatmap = np.full_like(slope_pct, np.nan)
    good = sum_valid > 0
    rix_heatmap[good] = (sum_complex[good] / sum_valid[good]) * 100.0
    rix_heatmap = np.clip(rix_heatmap, 0.0, 100.0)
    
    return rix_heatmap, radius_px

def calculate_tpi(dem: np.ndarray, cell_size: float, valid_mask: np.ndarray) -> np.ndarray:
    """
    Compute Topographic Position Index (TPI).
    TPI = Elevation of pixel - Mean Elevation of surroundings.
    Positive TPI indicates ridges, negative TPI indicates valleys.
    """
    print(f"  Computing TPI Map (Radius: {TPI_RADIUS_M}m) …")
    radius_px = int(round(TPI_RADIUS_M / cell_size))
    
    # Replace nans with 0 for safely applying fftconvolve
    dem_filled = dem.copy()
    dem_filled[~valid_mask] = 0.0
    
    valid_float = valid_mask.astype(np.float64)
    kernel = _create_circular_kernel(radius_px)
    
    sum_elev  = fftconvolve(dem_filled, kernel * kernel.size, mode="same")
    sum_valid = fftconvolve(valid_float, kernel * kernel.size, mode="same")
    
    mean_elev = np.full_like(dem, np.nan)
    good = sum_valid > 0
    mean_elev[good] = sum_elev[good] / sum_valid[good]
    
    tpi = np.full_like(dem, np.nan)
    tpi[valid_mask] = dem[valid_mask] - mean_elev[valid_mask]
    
    return tpi

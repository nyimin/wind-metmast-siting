# spatial_analysis.py
"""
Spatial analysis module for terrain complexity and multi-criteria decision analysis (MCDA)
for optimal Met Mast/Lidar siting.
"""

import numpy as np
import geopandas as gpd
from rasterio.features import rasterize
from scipy.signal import fftconvolve
from scipy.ndimage import distance_transform_edt
from pyproj import Transformer

from config import (
    IEC_SLOPE_THRESHOLD,
    WASP_RIX_THRESHOLD,
    FOCAL_RADIUS_M,
    MAST_BUFFER_M,
    W_ELEV,
    W_CENTC,
    W_RIX,
    W_LULC,
    LULC_WEIGHTS
)


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


def _create_circular_kernel(radius_px: int) -> np.ndarray:
    """Create a 2D circular boolean kernel with given pixel radius."""
    diameter = 2 * radius_px + 1
    y, x = np.ogrid[-radius_px:radius_px + 1, -radius_px:radius_px + 1]
    mask = (x**2 + y**2) <= radius_px**2
    kernel = mask.astype(np.float64)
    kernel /= kernel.sum()  # normalise so convolution gives the mean
    return kernel


def _rasterize_site_mask(gdf_site_utm: gpd.GeoDataFrame, profile: dict) -> np.ndarray:
    """Burn the site boundary into a boolean mask matching the DEM grid."""
    transform = profile["transform"]
    height = profile["height"]
    width  = profile["width"]
    shapes = [(geom, 1) for geom in gdf_site_utm.geometry]
    mask = rasterize(
        shapes,
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype=np.uint8,
    )
    return mask.astype(bool)


def compute_mcda_suitability(dem: np.ndarray,
                             slope_pct: np.ndarray,
                             lulc: np.ndarray,
                             profile: dict,
                             gdf_site_utm: gpd.GeoDataFrame) -> dict:
    """
    Compute Multi-Criteria Decision Analysis (MCDA) suitability for mast placement
    and continuous WAsP RIX heatmap.
    """
    print("=" * 70)
    print("STEP 5 — Multi-Criteria Met Mast Siting (MCDA)")
    print("=" * 70)

    transform = profile["transform"]
    cell_size = abs(transform.a)
    valid_mask = ~np.isnan(dem)

    # ---------------------------------------------------------
    # 5.1 RIX Calculation (WAsP Standard: 30% Threshold)
    # ---------------------------------------------------------
    radius_px = int(round(FOCAL_RADIUS_M / cell_size))
    print(f"  Focal radius  : {FOCAL_RADIUS_M:.0f} m  →  {radius_px} px")
    
    binary_rix_mask = np.zeros_like(slope_pct, dtype=np.float64)
    binary_rix_mask[valid_mask & (slope_pct > WASP_RIX_THRESHOLD)] = 1.0

    valid_float = valid_mask.astype(np.float64)
    kernel = _create_circular_kernel(radius_px)
    
    print("  Convolving RIX Heatmap (this may take a moment) …")
    sum_complex = fftconvolve(binary_rix_mask, kernel * kernel.size, mode="same")
    sum_valid   = fftconvolve(valid_float, kernel * kernel.size, mode="same")

    rix_heatmap = np.full_like(slope_pct, np.nan)
    good = sum_valid > 0
    rix_heatmap[good] = (sum_complex[good] / sum_valid[good]) * 100.0
    rix_heatmap = np.clip(rix_heatmap, 0.0, 100.0)

    # ---------------------------------------------------------
    # 5.2 Distance Analytics (Boundary & Centroid)
    # ---------------------------------------------------------
    site_mask = _rasterize_site_mask(gdf_site_utm, profile)
    
    # Distance to boundary (inside)
    inv_site_mask = ~site_mask
    dist_to_boundary_px = distance_transform_edt(site_mask)
    dist_to_boundary_m = dist_to_boundary_px * cell_size
    
    # Distance to centroid
    centroid = gdf_site_utm.geometry.unary_union.centroid
    cx_px = (centroid.x - transform.c) / transform.a
    cy_px = (centroid.y - transform.f) / transform.e
    
    y_idx, x_idx = np.indices(dem.shape)
    dist_to_centroid_m = np.sqrt((x_idx - cx_px)**2 + (y_idx - cy_px)**2) * cell_size
    
    # ---------------------------------------------------------
    # 5.3 Normalization for MCDA Scoring (0 = worst, 1 = best)
    # ---------------------------------------------------------
    # Only evaluate inside the site boundary
    eval_mask = site_mask & valid_mask

    # 1. Elevation (Higher is better)
    elev_eval = dem[eval_mask]
    e_min, e_max = elev_eval.min(), elev_eval.max()
    norm_elev = np.zeros_like(dem)
    norm_elev[eval_mask] = (dem[eval_mask] - e_min) / (e_max - e_min + 1e-6)

    # 2. Centrality (Closer to centroid is better)
    dist_eval = dist_to_centroid_m[eval_mask]
    d_min, d_max = dist_eval.min(), dist_eval.max()
    norm_cent = np.zeros_like(dem)
    norm_cent[eval_mask] = 1.0 - ((dist_to_centroid_m[eval_mask] - d_min) / (d_max - d_min + 1e-6))

    # 3. RIX (Lower complexity is better)
    rix_eval = rix_heatmap[eval_mask]
    r_min, r_max = rix_eval.min(), rix_eval.max()
    norm_rix = np.zeros_like(dem)
    norm_rix[eval_mask] = 1.0 - ((rix_heatmap[eval_mask] - r_min) / (r_max - r_min + 1e-6))

    # 4. LULC (Match weights from dictionary)
    norm_lulc = np.zeros_like(dem)
    for lulc_class, weight in LULC_WEIGHTS.items():
        norm_lulc[eval_mask & (lulc == lulc_class)] = weight

    # ---------------------------------------------------------
    # 5.4 Exclusion Masking
    # ---------------------------------------------------------
    # Exclude edges (< MAST_BUFFER_M) and local steep slopes (> IEC_SLOPE_THRESHOLD)
    exclusion_mask = (dist_to_boundary_m >= MAST_BUFFER_M) & (slope_pct <= IEC_SLOPE_THRESHOLD) & eval_mask
    
    # ---------------------------------------------------------
    # 5.5 Final Suitability Score Synthesis
    # ---------------------------------------------------------
    suitability_score = np.full_like(dem, np.nan)
    raw_score = (W_ELEV * norm_elev) + (W_CENTC * norm_cent) + (W_RIX * norm_rix) + (W_LULC * norm_lulc)
    suitability_score[exclusion_mask] = raw_score[exclusion_mask]
    
    # Check if any valid locations exist
    valid_count = np.sum(exclusion_mask)
    if valid_count == 0:
        print("  WARNING: No locations passed the constraint masking! Relaxing buffer constraints...")
        exclusion_mask = eval_mask & (slope_pct <= IEC_SLOPE_THRESHOLD)
        suitability_score[exclusion_mask] = raw_score[exclusion_mask]
        valid_count = np.sum(exclusion_mask)
        if valid_count == 0:
             print("  WARNING: Still no valid locations. Dropping all constraints.")
             exclusion_mask = eval_mask
             suitability_score[exclusion_mask] = raw_score[exclusion_mask]

    # ---------------------------------------------------------
    # 5.6 Find Top Candidates
    # ---------------------------------------------------------
    # Get top 3 locations (local maxima)
    suit_filled = np.where(np.isnan(suitability_score), -np.inf, suitability_score)
    flat_indices = np.argsort(suit_filled.ravel())[::-1]
    
    candidates = []
    min_dist_between_candidates_px = int(500 / cell_size)  # 500m apart minimum
    
    for idx in flat_indices:
        if len(candidates) >= 3:
            break
        r, c = np.unravel_index(idx, suit_filled.shape)
        if suit_filled[r, c] == -np.inf:
            break
            
        # Ensure spatial separation
        too_close = False
        for ext_r, ext_c in candidates:
            dist = np.sqrt((r - ext_r)**2 + (c - ext_c)**2)
            if dist < min_dist_between_candidates_px:
                too_close = True
                break
                
        if not too_close:
            candidates.append((r, c))

    opt_candidates_info = []
    utm_crs = profile["crs"]
    transformer = Transformer.from_crs(utm_crs, "EPSG:4326", always_xy=True)

    for rank, (r, c) in enumerate(candidates):
        easting  = transform.c + (c + 0.5) * transform.a
        northing = transform.f + (r + 0.5) * transform.e
        lon, lat = transformer.transform(easting, northing)
        
        opt_candidates_info.append({
            "rank": rank + 1,
            "row": r,
            "col": c,
            "easting": easting,
            "northing": northing,
            "lat": lat,
            "lon": lon,
            "score": suitability_score[r, c],
            "rix": rix_heatmap[r, c],
            "elev": dem[r, c],
            "slope": slope_pct[r, c]
        })
        
        if rank == 0:
            print(f"  Primary Lidar Loc : ({easting:.1f} E, {northing:.1f} N) UTM")
            print(f"                    : ({lat:.6f}°N, {lon:.6f}°E) WGS84")
            print(f"  Overall Score     : {suitability_score[r, c]:.3f} (RIX: {rix_heatmap[r, c]:.1f}%, Elev: {dem[r, c]:.1f}m)")

    # Site wide stats and categorical bounds
    rix_site = np.where(site_mask, rix_heatmap, np.nan)
    site_max_rix = float(np.nanmax(rix_site))
    site_mean_rix = float(np.nanmean(rix_site))
    
    slope_site = np.where(site_mask, slope_pct, np.nan)
    max_slope_site = float(np.nanmax(slope_site))
    
    if max_slope_site <= 10.0 and site_mean_rix == 0.0:
        terrain_category = "Simple Terrain"
        is_complex = False
    elif max_slope_site > 10.0 and site_mean_rix <= 5.0:
        terrain_category = "Semi-Complex Terrain"
        is_complex = False
    else:
        terrain_category = "Complex Terrain"
        is_complex = True

    # Slope stats for report
    valid_slope = ~np.isnan(slope_pct)
    bins = [0, 2, 5, 10, 15, 20, 30, 100]
    hist_counts, _ = np.histogram(slope_pct[valid_slope], bins=bins)
    hist_pcts = (hist_counts / np.sum(valid_slope)) * 100.0

    return {
        "rix_heatmap": rix_heatmap,
        "rix_site": rix_site,
        "site_mask": site_mask,
        "suitability_score": suitability_score,
        "candidates": opt_candidates_info,
        
        "rix_site_min": float(np.nanmin(rix_site)),
        "rix_site_max": site_max_rix,
        "rix_site_mean": site_mean_rix,
        
        "is_complex": is_complex,
        "terrain_category": terrain_category,
        "max_slope_site": max_slope_site,
        
        "max_slope_pct": float(np.nanmax(slope_pct)),
        "mean_slope_pct": float(np.nanmean(slope_pct)),
        "median_slope_pct": float(np.nanmedian(slope_pct)),
        "std_slope_pct": float(np.nanstd(slope_pct)),
        "hist_bins": bins,
        "hist_pcts": hist_pcts.tolist(),
        
        "focal_radius_m": FOCAL_RADIUS_M,
        "radius_px": radius_px,
    }

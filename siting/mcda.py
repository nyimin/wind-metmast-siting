# siting/mcda.py
"""
Multi-Criteria Decision Analysis (MCDA) module for measurement siting.
Synthesizes variables into a suitability score and identifies optimal locations.
"""

import numpy as np
import geopandas as gpd
from pyproj import Transformer

from config.settings import (
    W_ELEV, W_TPI, W_CENTC, W_RIX, W_LULC,
    LULC_WEIGHTS, MIN_MAST_SPACING_M
)

def compute_mcda_siting(dem: np.ndarray, tpi: np.ndarray, rix_heatmap: np.ndarray, lulc: np.ndarray, 
                        dist_to_centroid_m: np.ndarray, eval_mask: np.ndarray, exclusion_mask: np.ndarray, 
                        profile: dict, slope_pct: np.ndarray) -> dict:
    """
    Compute Suitability Score and Top Candidates.
    """
    print("=" * 70)
    print("STEP 6 — Multi-Criteria Met Mast Siting (MCDA)")
    print("=" * 70)

    # 1. Elevation Representativeness (Targeting 75th percentile to avoid isolated peaks)
    elev_eval = dem[eval_mask]
    if len(elev_eval) == 0:
        return {"suitability_score": np.full_like(dem, np.nan), "candidates": []}
        
    p75_elev = np.percentile(elev_eval, 75)
    e_min = elev_eval.min()
    e_max = elev_eval.max()
    
    # Score drops off heavily if lower than 75th percentile, but stays high above it
    norm_elev = np.zeros_like(dem)
    norm_elev[eval_mask] = np.where(
        dem[eval_mask] >= p75_elev, 
        1.0, 
        (dem[eval_mask] - e_min) / (p75_elev - e_min + 1e-6)
    )

    # 2. Topographic Position Index (TPI) - Favor ridges (positive TPI)
    tpi_eval = tpi[eval_mask]
    t_min, t_max = tpi_eval.min(), tpi_eval.max()
    norm_tpi = np.zeros_like(dem)
    # Shift to 0-1 scale. A higher TPI (ridge) gets higher score.
    norm_tpi[eval_mask] = (tpi[eval_mask] - t_min) / (t_max - t_min + 1e-6)

    # 3. Centrality (Closer to centroid is better)
    dist_eval = dist_to_centroid_m[eval_mask]
    d_min, d_max = dist_eval.min(), dist_eval.max()
    norm_cent = np.zeros_like(dem)
    norm_cent[eval_mask] = 1.0 - ((dist_to_centroid_m[eval_mask] - d_min) / (d_max - d_min + 1e-6))

    # 4. RIX (Lower complexity is better)
    rix_eval = rix_heatmap[eval_mask]
    r_min, r_max = rix_eval.min(), rix_eval.max()
    norm_rix = np.zeros_like(dem)
    if r_max > r_min:
        norm_rix[eval_mask] = 1.0 - ((rix_heatmap[eval_mask] - r_min) / (r_max - r_min + 1e-6))
    else:
        norm_rix[eval_mask] = 1.0

    # 5. LULC
    norm_lulc = np.zeros_like(dem)
    for lulc_class, weight in LULC_WEIGHTS.items():
        norm_lulc[eval_mask & (lulc == lulc_class)] = weight

    # Final Synthesis
    suitability_score = np.full_like(dem, np.nan)
    raw_score = (W_ELEV * norm_elev) + (W_TPI * norm_tpi) + (W_CENTC * norm_cent) + (W_RIX * norm_rix) + (W_LULC * norm_lulc)
    
    suitability_score[exclusion_mask] = raw_score[exclusion_mask]
    
    valid_count = np.sum(exclusion_mask)
    if valid_count == 0:
        print("  WARNING: No locations passed the constraint masking! Relaxing buffer constraints...")
        exclusion_mask = eval_mask
        suitability_score[exclusion_mask] = raw_score[exclusion_mask]

    # Find Top Candidates
    suit_filled = np.where(np.isnan(suitability_score), -np.inf, suitability_score)
    flat_indices = np.argsort(suit_filled.ravel())[::-1]
    
    candidates = []
    
    transform = profile["transform"]
    cell_size = abs(transform.a)
    min_dist_px = int(MIN_MAST_SPACING_M / cell_size)
    
    for idx in flat_indices:
        if len(candidates) >= 3:
            break
        r, c = np.unravel_index(idx, suit_filled.shape)
        if suit_filled[r, c] == -np.inf:
            break
            
        too_close = False
        for ext_r, ext_c in candidates:
            dist = np.sqrt((r - ext_r)**2 + (c - ext_c)**2)
            if dist < min_dist_px:
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
            "tpi": tpi[r, c],
            "slope": slope_pct[r, c]
        })
        
        if rank == 0:
            print(f"  Primary Measurement Location: ({easting:.1f} E, {northing:.1f} N) UTM")
            print(f"                              : ({lat:.6f}°N, {lon:.6f}°E) WGS84")
            print(f"  Suitability Score           : {suitability_score[r, c]:.3f} (RIX: {rix_heatmap[r, c]:.1f}%, Elev: {dem[r, c]:.1f}m)")

    return {
        "suitability_score": suitability_score,
        "candidates": opt_candidates_info
    }

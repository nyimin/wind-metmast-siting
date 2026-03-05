# siting/constraints.py
"""
Siting constraints module.
Handles creation of exclusion masks such as site boundaries, high slopes, and aerodynamic obstacles.
"""

import numpy as np
import geopandas as gpd
from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt

from config.settings import MAST_BUFFER_M, IEC_SLOPE_THRESHOLD, OBSTACLE_BUFFER_M

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

def generate_constraints(gdf_site_utm: gpd.GeoDataFrame, profile: dict, slope_pct: np.ndarray, valid_mask: np.ndarray, lulc: np.ndarray) -> dict:
    """
    Generate boolean exclusion masks and distance fields.
    """
    transform = profile["transform"]
    cell_size = abs(transform.a)
    
    site_mask = _rasterize_site_mask(gdf_site_utm, profile)
    
    # Distance to site boundary (inside)
    dist_to_boundary_px = distance_transform_edt(site_mask)
    dist_to_boundary_m = dist_to_boundary_px * cell_size
    
    # Distance to Centroid
    centroid = gdf_site_utm.geometry.unary_union.centroid
    cx_px = (centroid.x - transform.c) / transform.a
    cy_px = (centroid.y - transform.f) / transform.e
    
    y_idx, x_idx = np.indices(site_mask.shape)
    dist_to_centroid_m = np.sqrt((x_idx - cx_px)**2 + (y_idx - cy_px)**2) * cell_size
    
    # Distance to Obstacles (Trees = 10, Built-up = 50)
    # 0 where obstacle exists, distance > 0 otherwise
    obstacle_mask = (lulc == 10) | (lulc == 50) | (lulc == 70) | (lulc == 80) # trees, built-up, snow, water
    dist_to_obstacle_px = distance_transform_edt(~obstacle_mask)
    dist_to_obstacle_m = dist_to_obstacle_px * cell_size
    
    # Exclusion masking
    # Exclude edges (< MAST_BUFFER_M), local steep slopes (> IEC_SLOPE_THRESHOLD), and obstacles (< OBSTACLE_BUFFER_M)
    eval_mask = site_mask & valid_mask
    exclusion_mask = (dist_to_boundary_m >= MAST_BUFFER_M) & \
                     (slope_pct <= IEC_SLOPE_THRESHOLD) & \
                     (dist_to_obstacle_m >= OBSTACLE_BUFFER_M) & \
                     eval_mask

    return {
        "site_mask": site_mask,
        "eval_mask": eval_mask,
        "exclusion_mask": exclusion_mask,
        "dist_to_centroid_m": dist_to_centroid_m,
        "dist_to_obstacle_m": dist_to_obstacle_m
    }

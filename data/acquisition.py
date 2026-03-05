# data/acquisition.py
"""
Data loading and DEM/LULC acquisition module.
Retrieves and pre-processes spatial data required for wind site analysis.
"""

import os
import sys
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask as rasterio_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.io import MemoryFile
from shapely.geometry import mapping
import requests
from pystac_client import Client
import planetary_computer as pc

from config.settings import DEM_COLLECTION, LULC_COLLECTION, DEM_CACHE_DIR


def load_and_reproject(gpkg_path: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load site boundary and reproject to a local UTM CRS."""
    print("=" * 70)
    print("STEP 1 — Loading site boundary and reprojecting to UTM")
    print("=" * 70)

    gdf = gpd.read_file(gpkg_path)
    print(f"  Loaded {len(gdf)} feature(s) from {gpkg_path}")
    print(f"  Original CRS : {gdf.crs}")

    centroid = gdf.to_crs(epsg=4326).geometry.unary_union.centroid
    utm_zone = int((centroid.x + 180) / 6) + 1
    hemisphere = "north" if centroid.y >= 0 else "south"
    epsg_code = 32600 + utm_zone if hemisphere == "north" else 32700 + utm_zone

    gdf_utm = gdf.to_crs(epsg=epsg_code)
    gdf_wgs = gdf.to_crs(epsg=4326)
    print(f"  Centroid      : {centroid.y:.4f}°N, {centroid.x:.4f}°E")
    print(f"  UTM Zone      : {utm_zone}{hemisphere[0].upper()}  (EPSG:{epsg_code})")
    print(f"  Reprojected   : ✓\n")
    return gdf_utm, gdf_wgs


def generate_buffer(gdf_utm: gpd.GeoDataFrame, buffer_m: float) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Create a buffer around the site boundary in UTM, also return WGS84."""
    print("=" * 70)
    print(f"STEP 2 — Generating {buffer_m/1000:.0f} km buffer")
    print("=" * 70)

    buffered_geom = gdf_utm.geometry.unary_union.buffer(buffer_m)
    gdf_buffer_utm = gpd.GeoDataFrame(geometry=[buffered_geom], crs=gdf_utm.crs)
    gdf_buffer_wgs = gdf_buffer_utm.to_crs(epsg=4326)

    area_km2 = buffered_geom.area / 1e6
    print(f"  Buffer area   : {area_km2:.2f} km²")
    print(f"  Buffer created: ✓\n")
    return gdf_buffer_utm, gdf_buffer_wgs


def _get_cache_dir(script_dir: str) -> str:
    cache_dir = os.path.join(script_dir, DEM_CACHE_DIR)
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _tile_cache_path(cache_dir: str, item_id: str) -> str:
    safe_name = item_id.replace("/", "_").replace("\\", "_")
    return os.path.join(cache_dir, f"{safe_name}.tif")


def fetch_dem(gdf_buffer_wgs: gpd.GeoDataFrame, gdf_buffer_utm: gpd.GeoDataFrame, script_dir: str) -> tuple[np.ndarray, dict]:
    """
    Download NASADEM tiles, mosaic, clip to buffer, reproject to UTM.
    Tiles are cached in .dem_cache/ for instant reuse.
    """
    print("=" * 70)
    print("STEP 3 — Fetching NASADEM from Planetary Computer (STAC)")
    print("=" * 70)

    cache_dir = _get_cache_dir(script_dir)
    print(f"  Cache folder  : {cache_dir}")

    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )

    bounds_wgs = gdf_buffer_wgs.total_bounds
    search = catalog.search(
        collections=[DEM_COLLECTION],
        bbox=bounds_wgs.tolist(),
    )
    items = list(search.items())
    print(f"  STAC items found : {len(items)}")

    if not items:
        sys.exit("  ERROR: No NASADEM tiles found for this extent.")

    datasets = []
    for i, item in enumerate(items):
        tile_path = _tile_cache_path(cache_dir, item.id)

        if os.path.isfile(tile_path):
            print(f"  Tile {i+1}/{len(items)} — cached ✓  ({item.id})")
        else:
            asset = item.assets["elevation"]
            href = asset.href
            print(f"  Tile {i+1}/{len(items)} — downloading …  ({item.id})")
            resp = requests.get(href, stream=True, timeout=120)
            resp.raise_for_status()
            with open(tile_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"    → saved to cache ({os.path.getsize(tile_path)/1e6:.1f} MB)")

        datasets.append(rasterio.open(tile_path))

    print("  Mosaicking tiles …")
    mosaic, mosaic_transform = merge(datasets)
    mosaic_profile = datasets[0].profile.copy()
    mosaic_profile.update(
        height=mosaic.shape[1],
        width=mosaic.shape[2],
        transform=mosaic_transform,
        count=1,
    )
    for ds in datasets:
        ds.close()

    print("  Clipping to buffer extent …")
    clip_geom = [mapping(gdf_buffer_wgs.geometry.unary_union)]
    with MemoryFile() as memfile:
        with memfile.open(**mosaic_profile) as mem_ds:
            mem_ds.write(mosaic)
        with memfile.open() as mem_ds:
            clipped, clipped_transform = rasterio_mask(
                mem_ds, clip_geom, crop=True, nodata=-9999
            )
            clipped_profile = mem_ds.profile.copy()
            clipped_profile.update(
                height=clipped.shape[1],
                width=clipped.shape[2],
                transform=clipped_transform,
                nodata=-9999,
            )

    print("  Reprojecting DEM to UTM …")
    dst_crs = gdf_buffer_utm.crs
    transform_utm, width_utm, height_utm = calculate_default_transform(
        clipped_profile["crs"],
        dst_crs,
        clipped_profile["width"],
        clipped_profile["height"],
        *rasterio.transform.array_bounds(
            clipped_profile["height"],
            clipped_profile["width"],
            clipped_profile["transform"],
        ),
    )
    utm_profile = clipped_profile.copy()
    utm_profile.update(
        crs=dst_crs,
        transform=transform_utm,
        width=width_utm,
        height=height_utm,
    )
    dem_utm = np.empty((1, height_utm, width_utm), dtype=np.float32)
    reproject(
        source=clipped.astype(np.float32),
        destination=dem_utm,
        src_transform=clipped_profile["transform"],
        src_crs=clipped_profile["crs"],
        dst_transform=transform_utm,
        dst_crs=dst_crs,
        resampling=Resampling.bilinear,
        src_nodata=-9999,
        dst_nodata=-9999,
    )

    dem_2d = dem_utm[0]
    dem_2d[dem_2d == -9999] = np.nan
    utm_profile.update(dtype="float32")

    print(f"  DEM shape (UTM): {dem_2d.shape}")
    print(f"  Elevation range: {np.nanmin(dem_2d):.1f} – {np.nanmax(dem_2d):.1f} m")
    print(f"  DEM acquired   : ✓\n")
    return dem_2d, utm_profile


def fetch_lulc(gdf_buffer_wgs: gpd.GeoDataFrame, utm_profile: dict, script_dir: str) -> np.ndarray:
    """
    Download ESA WorldCover tiles, mosaic, and reproject to the exact DEM UTM grid.
    Tiles are cached in .dem_cache/ alongside NASADEM tiles.
    Uses NearestNeighbor interpolation to preserve discrete class values.
    """
    print("=" * 70)
    print("STEP 3b — Fetching ESA WorldCover LULC (STAC)")
    print("=" * 70)

    cache_dir = _get_cache_dir(script_dir)
    print(f"  Cache folder  : {cache_dir}")

    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )

    bounds_wgs = gdf_buffer_wgs.total_bounds
    search = catalog.search(
        collections=[LULC_COLLECTION],
        bbox=bounds_wgs.tolist(),
    )
    items = list(search.items())
    print(f"  STAC items found (LULC): {len(items)}")

    if not items:
        print("  WARNING: No ESA WorldCover tiles found. Returning zeros.")
        return np.zeros((utm_profile["height"], utm_profile["width"]), dtype=np.uint8)

    datasets = []
    for i, item in enumerate(items):
        tile_path = _tile_cache_path(cache_dir, item.id + "_lulc")

        if os.path.isfile(tile_path):
            print(f"  Tile {i+1}/{len(items)} — cached ✓  ({item.id})")
        else:
            asset = item.assets["map"]
            href = asset.href
            print(f"  Tile {i+1}/{len(items)} — downloading …  ({item.id})")
            resp = requests.get(href, stream=True, timeout=120)
            resp.raise_for_status()
            with open(tile_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"    → saved to cache ({os.path.getsize(tile_path)/1e6:.1f} MB)")

        datasets.append(rasterio.open(tile_path))

    print("  Mosaicking LULC tiles …")
    mosaic, mosaic_transform = merge(datasets)
    mosaic_profile = datasets[0].profile.copy()
    mosaic_profile.update(
        height=mosaic.shape[1],
        width=mosaic.shape[2],
        transform=mosaic_transform,
        count=1,
    )
    for ds in datasets:
        ds.close()

    print("  Reprojecting LULC to DEM grid …")
    lulc_utm = np.empty((1, utm_profile["height"], utm_profile["width"]), dtype=np.uint8)
    
    src_nodata = mosaic_profile.get("nodata", 0)
    
    reproject(
        source=mosaic,
        destination=lulc_utm,
        src_transform=mosaic_profile["transform"],
        src_crs=mosaic_profile["crs"],
        dst_transform=utm_profile["transform"],
        dst_crs=utm_profile["crs"],
        resampling=Resampling.nearest,
        src_nodata=src_nodata,
        dst_nodata=0,
    )

    lulc_2d = lulc_utm[0]
    
    print(f"  LULC shape (UTM): {lulc_2d.shape}")
    print(f"  LULC acquired   : ✓\n")
    return lulc_2d

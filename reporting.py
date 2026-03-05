# reporting.py
"""
Reporting and visualisation module.
Generates Maps and Markdown reports for the Terrain Analysis Pipeline.
"""

from datetime import datetime, timezone
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from config import (
    IEC_SLOPE_THRESHOLD, 
    WASP_RIX_THRESHOLD, 
    BUFFER_DISTANCE_M,
    W_ELEV,
    W_CENTC,
    W_RIX,
    W_LULC
)


def generate_map(dem: np.ndarray,
                 slope_pct: np.ndarray,
                 profile: dict,
                 gdf_site_utm: gpd.GeoDataFrame,
                 gdf_buffer_utm: gpd.GeoDataFrame,
                 results: dict,
                 output_path: str):
    """
    Dual-panel map:
      Left  – DEM elevation with boundaries
      Right – MCDA Suitability Heatmap with optimal markers
    """
    print("=" * 70)
    print("STEP 6 — Generating terrain analysis map")
    print("=" * 70)

    transform = profile["transform"]
    height, width = dem.shape
    left   = transform.c
    right  = transform.c + transform.a * width
    top    = transform.f
    bottom = transform.f + transform.e * height
    extent = [left, right, bottom, top]

    fig, axes = plt.subplots(1, 2, figsize=(20, 10), dpi=150)

    # ---- Panel A: DEM with boundaries ----
    ax1 = axes[0]
    im1 = ax1.imshow(dem, cmap="terrain", extent=extent, origin="upper")
    gdf_buffer_utm.boundary.plot(ax=ax1, edgecolor="blue",
                                  linewidth=1.5, linestyle="--", label="5 km Buffer")
    gdf_site_utm.boundary.plot(ax=ax1, edgecolor="black",
                                linewidth=2.0, label="Site Boundary")
    ax1.set_title("Digital Elevation Model (NASADEM)", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Easting (m)")
    ax1.set_ylabel("Northing (m)")
    cb1 = fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)
    cb1.set_label("Elevation (m)")
    ax1.legend(loc="lower left", fontsize=9)

    # ---- Panel B: MCDA Suitability Heatmap ----
    ax2 = axes[1]

    # Show the suitability heatmap clipped to site boundary
    suitability_display = results["suitability_score"].copy()
    site_mask = results["site_mask"]
    suitability_display[~site_mask] = np.nan

    # RdYlGn: Green = high score (good), Red = low score (bad)
    im2 = ax2.imshow(suitability_display, cmap="RdYlGn", extent=extent,
                     origin="upper", vmin=np.nanmin(suitability_display),
                     vmax=np.nanmax(suitability_display))

    gdf_buffer_utm.boundary.plot(ax=ax2, edgecolor="blue",
                                  linewidth=1.5, linestyle="--")
    gdf_site_utm.boundary.plot(ax=ax2, edgecolor="black", linewidth=2.0)

    # Markers for top 3 candidates
    candidates = results["candidates"]
    colors = ["gold", "silver", "orangered"]
    labels = ["Primary Location", "Secondary", "Tertiary"]
    
    handles = []
    
    for i, opt in enumerate(candidates):
        color = colors[i]
        label = labels[i]
        ax2.plot(opt["easting"], opt["northing"],
                 marker="*", color=color, markersize=22 - (i*3),
                 markeredgecolor="black", markeredgewidth=1.2,
                 zorder=10)
        marker = plt.Line2D([], [], marker="*", color=color, markersize=14-(i*2),
                            markeredgecolor="black", linestyle="None",
                            label=f"{label} (Score: {opt['score']:.2f})")
        handles.append(marker)

    ax2.set_title("Met Mast/Lidar MCDA Suitability Score", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Easting (m)")
    ax2.set_ylabel("Northing (m)")
    cb2 = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    cb2.set_label("Suitability Score (0 to 1)")

    # Labels 
    site_line = mpatches.Patch(edgecolor="black", facecolor="none",
                               linewidth=2, label="Site Boundary")
    buf_line  = mpatches.Patch(edgecolor="blue", facecolor="none",
                               linewidth=1.5, linestyle="--", label="5 km Buffer")
    handles.extend([site_line, buf_line])
    ax2.legend(handles=handles, loc="lower left", fontsize=9)

    fig.suptitle("Wind Project — Terrain Complexity & Measurement Suitability",
                 fontsize=16, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Map saved to  : {output_path}")
    print(f"  Map generated : ✓\n")


def print_report(results: dict):
    """Print a final summary report to the console."""
    line = "=" * 70
    verdict = "TRUE" if results["is_complex"] else "FALSE"
    tag = "⚠️  " if results["is_complex"] else "✅ "
    iec_deg = np.degrees(np.arctan(IEC_SLOPE_THRESHOLD / 100))
    wasp_deg = np.degrees(np.arctan(WASP_RIX_THRESHOLD / 100))

    print(line)
    print("         TERRAIN COMPLEXITY & MCDA SUITABILITY REPORT")
    print(line)
    print(f"  Standards       : WAsP (RIX) / IEC 61400-1 (Slopes)")
    print(f"  WAsP RIX Threshold: {WASP_RIX_THRESHOLD} %  (≈ {wasp_deg:.2f}°)")
    print(f"  IEC Local Limits  : {IEC_SLOPE_THRESHOLD} %  (≈ {iec_deg:.2f}°)")
    print(f"  Focal Radius    : {results['focal_radius_m']:.0f} m  ({results['radius_px']} px)")
    print(line)
    print(f"  Max  Slope      : {results['max_slope_pct']:.2f} %")
    print(f"  Site RIX (min)  : {results['rix_site_min']:.2f} %")
    print(f"  Site RIX (max)  : {results['rix_site_max']:.2f} %")
    print(line)
    print(f"  ⭐ Top Lidar Candidates:")
    for opt in results['candidates']:
        print(f"     Rank {opt['rank']}: {opt['easting']:.1f} E, {opt['northing']:.1f} N -> Score {opt['score']:.3f} (RIX: {opt['rix']:.1f}%)")
    print(line)
    print(line)
    print(f"  {tag}Terrain Complexity  : {results['terrain_category']}")
    print(line)


def generate_markdown_report(
    results: dict,
    dem: np.ndarray,
    profile: dict,
    gdf_site_utm: gpd.GeoDataFrame,
    gdf_buffer_utm: gpd.GeoDataFrame,
    output_path: str,
    map_filename: str,
):
    """Write a comprehensive Markdown analysis report to disk."""
    print("=" * 70)
    print("STEP 8 — Generating Markdown report")
    print("=" * 70)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    verdict = "TRUE ⚠️" if results["is_complex"] else "FALSE ✅"
    threshold_deg = np.degrees(np.arctan(WASP_RIX_THRESHOLD / 100))

    # Site geometry info
    site_geom = gdf_site_utm.geometry.unary_union
    site_area_km2 = site_geom.area / 1e6
    site_perimeter_km = site_geom.length / 1e3
    buf_area_km2 = gdf_buffer_utm.geometry.unary_union.area / 1e6
    centroid_wgs = gdf_site_utm.to_crs(epsg=4326).geometry.unary_union.centroid
    crs_str = str(gdf_site_utm.crs)

    # DEM info
    dem_rows, dem_cols = dem.shape
    cell_x = abs(profile["transform"].a)
    cell_y = abs(profile["transform"].e)
    elev_min = float(np.nanmin(dem))
    elev_max = float(np.nanmax(dem))
    elev_mean = float(np.nanmean(dem))
    elev_range = elev_max - elev_min

    # Slope histogram
    bins = results["hist_bins"]
    hist_pcts = results["hist_pcts"]
    hist_rows = []
    for j in range(len(hist_pcts)):
        lo, hi = bins[j], bins[j + 1]
        label = f"{lo}–{hi} %"
        bar = "█" * int(round(hist_pcts[j] / 2))
        hist_rows.append(f"| {label:<10} | {hist_pcts[j]:>6.2f} % | {bar} |")
        
    candidates = results["candidates"]
    if len(candidates) > 0:
        opt = candidates[0]
        opt_lat, opt_lon, opt_rix, opt_easting, opt_northing = opt['lat'], opt['lon'], opt['rix'], opt['easting'], opt['northing']
    else:
        opt_lat = opt_lon = opt_rix = opt_easting = opt_northing = 0.0

    # Recommendations block
    if results["is_complex"]:
        reco_header = "### ⚠️ Complex Terrain Detected"
        reco_intro  = "The following actions are recommended as the WAsP RIX is > 0 within the site boundary:"
        reco_items  = f"""
1. **Consider advanced flow modelling** — High RIX values indicate potential flow separation where linear tools (WAsP) struggle. CFD analysis may be required in high RIX zones.
2. **Deploy Met Mast / Lidar at Optimal Locations** — The Multi-Criteria analysis identified ({opt_lat:.6f}°N, {opt_lon:.6f}°E) as the primary site.
3. **Ensure Installation Limits** — Verify no slopes directly surrounding the tower exceed {IEC_SLOPE_THRESHOLD}% per IEC installation guidelines.
"""
    else:
        reco_header = "### ✅ Terrain Within Standard Limits"
        reco_intro  = "Standard procedures should be sufficient:"
        reco_items  = f"""
1. **Linearised flow models** (WAsP, OpenWind) are expected to perform adequately.
2. **Standard measurement campaigns** can be used.
3. **Deploy Measurement Equipment** — Primary recommended site: ({opt_lat:.6f}°N, {opt_lon:.6f}°E).
"""

    md = f"""# Terrain Complexity Analysis Report
# MCDA Met Mast & LiDAR Siting

> **Generated:** {now}
> **Methodology:** WAsP RIX (ruggedness index) & Multi-Criteria spatial analysis

---

## 1. Executive Summary

| Parameter | Value |
|-----------|-------|
| **Terrain Complexity Class** | **{results['terrain_category']}** |
| **Site WAsP RIX (mean)** | {results['rix_site_mean']:.2f} % |
| **Max Terrain Slope** | {results['max_slope_site']:.2f} % |
| **Complex Terrain (WAsP > 0)** | **{verdict}** |

### ⭐ Top 3 Optimal Measurement Candidate Sites

| Rank | Latitude | Longitude | Easting | Northing | Elevation | Suitability Score |
|------|----------|-----------|---------|----------|-----------|-------------------|
"""
    for opt in candidates:
        md += f"| **{opt['rank']}** | {opt['lat']:.5f}° N | {opt['lon']:.5f}° E | {opt['easting']:,.0f} m | {opt['northing']:,.0f} m | {opt['elev']:.1f} m | **{opt['score']:.3f}** |\n"
        
    md += f"""
{"**⚠️ The site IS classified as complex terrain.**" if results['is_complex'] else "**✅ The site is NOT classified as complex terrain.**"}

---

## 2. Site Description

| Parameter | Value |
|-----------|-------|
| Boundary file | `site_boundary.gpkg` |
| Centroid (WGS 84) | {centroid_wgs.y:.6f}° N, {centroid_wgs.x:.6f}° E |
| Projected CRS | {crs_str} |
| Site area | {site_area_km2:.2f} km² |
| Site perimeter | {site_perimeter_km:.2f} km |

---

## 3. Spatial Objective Setup (MCDA)

A Multi-Criteria Decision Analysis (MCDA) algorithm defines measurement suitability. The algorithm scores every pixel inside the site from 0.0 to 1.0 based on the following weighted objectives:

- **Elevation (Weight: {W_ELEV}):** Pushes sites towards higher elevations (ridges, plateaus) to be representative of turbine installations.
- **Land Use Suitability (Weight: {W_LULC}):** Highly favors grass/bare land, avoids water, built-up areas, and forests (due to high displacement heights and induced turbulence).
- **Centrality (Weight: {W_CENTC}):** Pulls sites towards the geometric centroid of the parcel for maximum spatial coverage.
- **Flatness/Low-RIX (Weight: {W_RIX}):** Pushes sites away from rugged zones (WAsP RIX) reducing flow separation turbulence.
- **Constraints (Exclusions):** Excludes areas within 200m of the site boundary, and strictly excludes local slopes > {IEC_SLOPE_THRESHOLD}% (IEC 61400-1 installation limits).

---

## 4. Methodologies

### 4.1 Terrain Categorical Classification
Wind industry best practice typically applies linearised micro-siting models (like WAsP) cautiously. General heuristics for site classification have been applied:
- **Simple Terrain:** Max Slope < 10% AND Mean Site RIX = 0%. Standard models perform perfectly with low uncertainty.
- **Semi-Complex Terrain:** Max Slope > 10% BUT Mean Site RIX <= 5%. True complex terrain is highly localized. Standard flow modelling may still be acceptable if turbines are micro-sited away from steep slopes.
- **Complex Terrain:** Mean Site RIX > 5%. Significant widespread flow detachment. Linear models break down; advanced CFD evaluation is highly recommended.

**Based on the analysis, this site is classified as: {results['terrain_category']}**

### 4.2 WAsP RIX Methodology

The true WAsP Ruggedness Index (RIX) is defined using a 30% slope threshold:

1. **Binary slope mask** — Every pixel where slope > {WASP_RIX_THRESHOLD:.0f}% is marked.
2. **Circular kernel** — A 2D circular window of radius **{results['focal_radius_m']/1000:.1f} km** ({results['radius_px']} pixels) is constructed.
3. **Focal convolution** — Computes the fractional area of complex terrain within the neighbourhood of *every* pixel.

> **RIX(x,y)** = (Area with slope > {WASP_RIX_THRESHOLD:.0f}% within {results['focal_radius_m']/1000:.1f} km) / (Total Valid Area) × 100

### 4.2 Slope Distribution

| Slope Range | Area (%) | Distribution |
|-------------|----------|--------------|
{chr(10).join(hist_rows)}

---

## 5. Recommendations

{reco_header}

{reco_intro}
{reco_items}

---

## 6. Terrain Analysis Map

![Terrain complexity & Lidar suitability map]({map_filename})

- **Left panel:** NASADEM elevation with site boundary (black) and 5 km buffer (blue dashed).
- **Right panel:** MCDA Suitability Heatmap. ⭐ marks the optimal monitoring locations ranked 1, 2, and 3.

---

*Report generated automatically by `main.py` spatial analysis pipeline.*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"  Report saved  : {output_path}")
    print(f"  Report ready  : ✓\n")

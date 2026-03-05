# reporting/report_generator.py
"""
Markdown report generation for technical memos.
"""

from datetime import datetime, timezone
import numpy as np
import geopandas as gpd

from config.settings import (
    IEC_SLOPE_THRESHOLD, WASP_RIX_THRESHOLD,
    W_ELEV, W_TPI, W_CENTC, W_RIX, W_LULC,
    OBSTACLE_BUFFER_M, TPI_RADIUS_M
)

def print_report(terrain_results: dict, mcda_results: dict, focal_radius_m: float, radius_px: int, slope_pct: np.ndarray):
    """Print a final summary report to the console."""
    line = "=" * 70
    tag = "⚠️  " if terrain_results["is_complex"] else "✅ "
    iec_deg = np.degrees(np.arctan(IEC_SLOPE_THRESHOLD / 100))
    wasp_deg = np.degrees(np.arctan(WASP_RIX_THRESHOLD / 100))

    print(line)
    print("         TERRAIN COMPLEXITY & MCDA SUITABILITY REPORT")
    print(line)
    print(f"  Standards       : WAsP (RIX) / IEC 61400-1 (Slopes)")
    print(f"  WAsP RIX Threshold: {WASP_RIX_THRESHOLD} %  (≈ {wasp_deg:.2f}°)")
    print(f"  IEC Local Limits  : {IEC_SLOPE_THRESHOLD} %  (≈ {iec_deg:.2f}°)")
    print(f"  Focal Radius    : {focal_radius_m:.0f} m  ({radius_px} px)")
    print(line)
    print(f"  Max  Slope      : {terrain_results['max_slope_site']:.2f} %")
    print(f"  Site RIX (max)  : {terrain_results['rix_site_max']:.2f} %")
    print(line)
    print(f"  ⭐ Top Measurement Candidates:")
    for opt in mcda_results['candidates']:
        print(f"     Rank {opt['rank']}: {opt['easting']:.1f} E, {opt['northing']:.1f} N -> Score {opt['score']:.3f} (RIX: {opt['rix']:.1f}%)")
    print(line)
    print(f"  {tag}Terrain Complexity  : {terrain_results['terrain_category']}")
    print(line)


def generate_markdown_report(
    terrain_results: dict,
    mcda_results: dict,
    dem: np.ndarray,
    slope_pct: np.ndarray,
    profile: dict,
    gdf_site_utm: gpd.GeoDataFrame,
    gdf_buffer_utm: gpd.GeoDataFrame,
    focal_radius_m: float,
    radius_px: int,
    output_path: str,
    map_filename: str,
):
    """Write a comprehensive Markdown analysis report to disk."""
    print("=" * 70)
    print("STEP 8 — Generating Markdown report")
    print("=" * 70)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    verdict = "TRUE ⚠️" if terrain_results["is_complex"] else "FALSE ✅"

    # Site geometry info
    site_geom = gdf_site_utm.geometry.unary_union
    site_area_km2 = site_geom.area / 1e6
    site_perimeter_km = site_geom.length / 1e3
    centroid_wgs = gdf_site_utm.to_crs(epsg=4326).geometry.unary_union.centroid
    crs_str = str(gdf_site_utm.crs)

    # Slope histogram
    valid_slope = ~np.isnan(slope_pct)
    bins = [0, 2, 5, 10, 15, 20, 30, 100]
    hist_counts, _ = np.histogram(slope_pct[valid_slope], bins=bins)
    hist_pcts = (hist_counts / np.sum(valid_slope)) * 100.0

    hist_rows = []
    for j in range(len(hist_pcts)):
        lo, hi = bins[j], bins[j + 1]
        label = f"{lo}–{hi} %"
        bar = "█" * int(round(hist_pcts[j] / 2))
        hist_rows.append(f"| {label:<10} | {hist_pcts[j]:>6.2f} % | {bar} |")
        
    candidates = mcda_results["candidates"]
    if len(candidates) > 0:
        opt = candidates[0]
        opt_lat, opt_lon = opt['lat'], opt['lon']
    else:
        opt_lat = opt_lon = 0.0

    # Recommendations block
    if terrain_results["is_complex"]:
        reco_header = "### ⚠️ Complex Terrain Detected"
        reco_intro  = "The following actions are recommended due to significant topological complexity within the site boundary:"
        reco_items  = f"""
1. **Consider advanced flow modelling** — High RIX values indicate significant flow separation where linear tools (WAsP, OpenWind) struggle. CFD analysis is highly recommended.
2. **Deploy Measurement Campaign** — The Multi-Criteria analysis identified ({opt_lat:.6f}°N, {opt_lon:.6f}°E) as the optimal primary measurement location. Given complex terrain, a remote sensing device (LiDAR) is recommended to capture shear profiles.
3. **Ensure Installation Limits** — Verify no slopes directly surrounding the tower exceed {IEC_SLOPE_THRESHOLD}% per IEC installation guidelines.
"""
    else:
        reco_header = "### ✅ Terrain Within Standard Limits"
        reco_intro  = "Standard measurement and flow modelling procedures should be sufficient:"
        reco_items  = f"""
1. **Linearised flow models** (WAsP, OpenWind) are expected to perform adequately with low uncertainty.
2. **Measurement Strategy** — Standard measurement campaigns (Met Masts) can be used. Primary recommended site: ({opt_lat:.6f}°N, {opt_lon:.6f}°E).
3. **Array Micro-siting** — Ensure turbines are not sited exactly on the minor local slopes exceeding 15%.
"""

    md = f"""# Wind Resource Assessment: Terrain Complexity & Measurement Siting Memo

> **Generated:** {now}
> **Data Source:** NASADEM 30m resolution 
> **Methodology:** WAsP RIX (ruggedness index), Topographic Position Index (TPI), and Multi-Criteria spatial analysis

---

## 1. Executive Summary

| Parameter | Value |
|-----------|-------|
| **Terrain Complexity Class** | **{terrain_results['terrain_category']}** |
| **Max Site WAsP RIX** | {terrain_results['rix_site_max']:.2f} % |
| **Max Terrain Slope** | {terrain_results['max_slope_site']:.2f} % |
| **Complex Terrain (CFD Recommended)** | **{verdict}** |

### ⭐ Top 3 Optimal Measurement Candidate Sites

| Rank | Latitude | Longitude | Easting | Northing | Elevation | Suitability Score |
|------|----------|-----------|---------|----------|-----------|-------------------|
"""
    for opt in candidates:
        md += f"| **{opt['rank']}** | {opt['lat']:.5f}° N | {opt['lon']:.5f}° E | {opt['easting']:,.0f} | {opt['northing']:,.0f} | {opt['elev']:.1f} m | **{opt['score']:.3f}** |\n"
        
    md += f"""
{"**⚠️ The site IS classified as complex terrain.**" if terrain_results['is_complex'] else "**✅ The site is NOT classified as complex terrain.**"}

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

A Multi-Criteria Decision Analysis (MCDA) framework determines measurement site suitability. A score from 0.0 to 1.0 is synthesized based on professional siting criteria:

- **Topographic Position Index (TPI) (Weight: {W_TPI}):** Evaluates ridge vs valley placement over a {TPI_RADIUS_M/1000:.1f} km radius. Strongly preferencing positive TPI (ridges) for undisturbed dominant flow.
- **Elevation Representativeness (Weight: {W_ELEV}):** Targets the 75th percentile of site elevation to ensure measurements are representative of potential turbine array heights, avoiding unrepresentative valley or absolute peak placements.
- **Aerodynamic Distance & LULC (Weight: {W_LULC}):** Buffers heavily forested areas ({OBSTACLE_BUFFER_M} m) to reduce uncertainty from displacement heights and induced turbulence. Highly favors grass/bare land.
- **Flatness/Low-RIX (Weight: {W_RIX}):** Pushes sites away from rugged zones reducing flow separation turbulence near the mast.
- **Centrality (Weight: {W_CENTC}):** Pulls sites towards the geometric centroid of the parcel for maximum spatial representation.
- **Constraints (Exclusions):** Excludes areas within 200m of boundaries, strictly excludes local slopes > {IEC_SLOPE_THRESHOLD}% (IEC 61400-1 limits), and ensures candidate sites are spaced >2km apart.

---

## 4. Methodologies & Uncertainty Limitations

### 4.1 Terrain Categorical Classification
Wind industry best practice relies on the Maximum WAsP RIX to classify the overall site, minimizing the dilution effect of mean averages in widespread flat sites containing localized cliffs.

- **Simple Terrain:** Max Slope < 15% and Max RIX < 0.5%. Linear models perform perfectly with low uncertainty.
- **Semi-Complex Terrain:** Max Slope > 15% but Max RIX <= 5%. Flow separation is localized. Standard modelling is acceptable if turbines are micro-sited carefully.
- **Complex Terrain:** Max RIX > 5%. Significant widespread flow detachment. Advanced CFD evaluation is required.

**Classification Result: {terrain_results['terrain_category']}**

### 4.2 WAsP RIX & TPI Methodology
- **WAsP RIX:** Fractional area of terrain > {WASP_RIX_THRESHOLD:.0f}% slope within a {focal_radius_m/1000:.1f} km radius focal window.
- **TPI:** The difference between a focal pixel's elevation and the mean elevation within a {TPI_RADIUS_M/1000:.1f} km focal window.

### 4.3 Uncertainty & Limitations
- **DEM Resolution:** NASADEM 30m may underrepresent localized sharp terrain changes (e.g. sharp escarpments or micro-terrain roughness) which a 5m LiDAR DEM could capture.
- **Lack of Wind Direction Analytics:** The MCDA framework does not account for prevailing wind direction. If wind roses are available, measurements should ideally be placed upwind or free from wake of prominent ridges in the dominant flow sector.

### 4.4 Slope Distribution
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

*Report generated automatically by the Terrain Analysis Pipeline.*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"  Report saved  : {output_path}")
    print(f"  Report ready  : ✓\n")

# Terrain Complexity Analysis Report
# MCDA Met Mast & LiDAR Siting

> **Generated:** 2026-03-05 11:34 UTC
> **Methodology:** WAsP RIX (ruggedness index) & Multi-Criteria spatial analysis

---

## 1. Executive Summary

| Parameter | Value |
|-----------|-------|
| **Terrain Complexity Class** | **Semi-Complex Terrain** |
| **Site WAsP RIX (mean)** | 0.01 % |
| **Max Terrain Slope** | 20.87 % |
| **Complex Terrain (WAsP > 0)** | **FALSE ✅** |

### ⭐ Top 3 Optimal Measurement Candidate Sites

| Rank | Latitude | Longitude | Easting | Northing | Elevation | Suitability Score |
|------|----------|-----------|---------|----------|-----------|-------------------|
| **1** | 20.73089° N | 94.88381° E | 696,158 m | 2,293,506 m | 260.6 m | **0.885** |
| **2** | 20.73933° N | 94.87532° E | 695,263 m | 2,294,431 m | 235.7 m | **0.881** |
| **3** | 20.72959° N | 94.87921° E | 695,680 m | 2,293,357 m | 253.0 m | **0.878** |

**✅ The site is NOT classified as complex terrain.**

---

## 2. Site Description

| Parameter | Value |
|-----------|-------|
| Boundary file | `site_boundary.gpkg` |
| Centroid (WGS 84) | 20.740655° N, 94.869802° E |
| Projected CRS | EPSG:32646 |
| Site area | 19.53 km² |
| Site perimeter | 20.90 km |

---

## 3. Spatial Objective Setup (MCDA)

A Multi-Criteria Decision Analysis (MCDA) algorithm defines measurement suitability. The algorithm scores every pixel inside the site from 0.0 to 1.0 based on the following weighted objectives:

- **Elevation (Weight: 0.3):** Pushes sites towards higher elevations (ridges, plateaus) to be representative of turbine installations.
- **Land Use Suitability (Weight: 0.3):** Highly favors grass/bare land, avoids water, built-up areas, and forests (due to high displacement heights and induced turbulence).
- **Centrality (Weight: 0.2):** Pulls sites towards the geometric centroid of the parcel for maximum spatial coverage.
- **Flatness/Low-RIX (Weight: 0.2):** Pushes sites away from rugged zones (WAsP RIX) reducing flow separation turbulence.
- **Constraints (Exclusions):** Excludes areas within 200m of the site boundary, and strictly excludes local slopes > 10.0% (IEC 61400-1 installation limits).

---

## 4. Methodologies

### 4.1 Terrain Categorical Classification
Wind industry best practice typically applies linearised micro-siting models (like WAsP) cautiously. General heuristics for site classification have been applied:
- **Simple Terrain:** Max Slope < 10% AND Mean Site RIX = 0%. Standard models perform perfectly with low uncertainty.
- **Semi-Complex Terrain:** Max Slope > 10% BUT Mean Site RIX <= 5%. True complex terrain is highly localized. Standard flow modelling may still be acceptable if turbines are micro-sited away from steep slopes.
- **Complex Terrain:** Mean Site RIX > 5%. Significant widespread flow detachment. Linear models break down; advanced CFD evaluation is highly recommended.

**Based on the analysis, this site is classified as: Semi-Complex Terrain**

### 4.2 WAsP RIX Methodology

The true WAsP Ruggedness Index (RIX) is defined using a 30% slope threshold:

1. **Binary slope mask** — Every pixel where slope > 30% is marked.
2. **Circular kernel** — A 2D circular window of radius **3.5 km** (117 pixels) is constructed.
3. **Focal convolution** — Computes the fractional area of complex terrain within the neighbourhood of *every* pixel.

> **RIX(x,y)** = (Area with slope > 30% within 3.5 km) / (Total Valid Area) × 100

### 4.2 Slope Distribution

| Slope Range | Area (%) | Distribution |
|-------------|----------|--------------|
| 0–2 %      |  15.10 % | ████████ |
| 2–5 %      |  46.55 % | ███████████████████████ |
| 5–10 %     |  34.60 % | █████████████████ |
| 10–15 %    |   3.39 % | ██ |
| 15–20 %    |   0.26 % |  |
| 20–30 %    |   0.09 % |  |
| 30–100 %   |   0.01 % |  |

---

## 5. Recommendations

### ✅ Terrain Within Standard Limits

Standard procedures should be sufficient:

1. **Linearised flow models** (WAsP, OpenWind) are expected to perform adequately.
2. **Standard measurement campaigns** can be used.
3. **Deploy Measurement Equipment** — Primary recommended site: (20.730886°N, 94.883810°E).


---

## 6. Terrain Analysis Map

![Terrain complexity & Lidar suitability map](terrain_analysis_map.png)

- **Left panel:** NASADEM elevation with site boundary (black) and 5 km buffer (blue dashed).
- **Right panel:** MCDA Suitability Heatmap. ⭐ marks the optimal monitoring locations ranked 1, 2, and 3.

---

*Report generated automatically by `main.py` spatial analysis pipeline.*

# visualization/maps.py
"""
Map visualization module.
Generates dual-panel maps for the Terrain Analysis Pipeline.
"""

import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def generate_map(dem: np.ndarray,
                 profile: dict,
                 gdf_site_utm: gpd.GeoDataFrame,
                 gdf_buffer_utm: gpd.GeoDataFrame,
                 mcda_results: dict,
                 constraint_results: dict,
                 output_path: str):
    """
    Dual-panel map:
      Left  – DEM elevation with boundaries
      Right – MCDA Suitability Heatmap with optimal markers
    """
    print("=" * 70)
    print("STEP 7 — Generating terrain analysis map")
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
    suitability_display = mcda_results["suitability_score"].copy()
    site_mask = constraint_results["site_mask"]
    suitability_display[~site_mask] = np.nan

    # RdYlGn: Green = high score (good), Red = low score (bad)
    im2 = ax2.imshow(suitability_display, cmap="RdYlGn", extent=extent,
                     origin="upper", vmin=np.nanmin(suitability_display),
                     vmax=np.nanmax(suitability_display))

    gdf_buffer_utm.boundary.plot(ax=ax2, edgecolor="blue",
                                  linewidth=1.5, linestyle="--")
    gdf_site_utm.boundary.plot(ax=ax2, edgecolor="black", linewidth=2.0)

    # Markers for top candidates
    candidates = mcda_results["candidates"]
    colors = ["gold", "silver", "orangered"]
    labels = ["Primary Location", "Secondary", "Tertiary"]
    
    handles = []
    
    for i, opt in enumerate(candidates):
        color = colors[i]
        label = labels[i] if i < len(labels) else f"Rank {i+1}"
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

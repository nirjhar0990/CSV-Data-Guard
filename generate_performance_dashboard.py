from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# CSV DATA GUARD — PERFORMANCE DASHBOARD
# ============================================================

OUTPUT_DIR = Path("assets/performance")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "csv_data_guard_performance_dashboard.png"


# ============================================================
# 1. STRESS TEST DATA
# ============================================================
#
# IMPORTANT:
# Replace these values with the FINAL values from your existing
# stress-test results if they are different.
#
# Keep the dataset sizes in increasing order.
#

stress_rows = np.array([
    10_000,
    100_000,
    250_000,
    500_000,
])

# Enter your final measured stress-test runtimes here.
stress_runtime = np.array([
    0.765,
    3.987,
    10.212,
    17.494,
])

stress_labels = [
    "10K",
    "100K",
    "250K",
    "500K",
]

# Throughput is calculated automatically.
stress_throughput = stress_rows / stress_runtime


# ============================================================
# 2. FINAL 500K UI SMOKE TEST
# ============================================================

ui_stages = [
    "CSV Read",
    "Profiling",
    "Backend Pipeline",
    "Plotly Charts",
]

ui_times = [
    2.22,
    2.80,
    8.2348,
    0.31,
]


# ============================================================
# 3. FINAL 500K BACKEND PIPELINE
# ============================================================

pipeline_stages = [
    "Problem Map",
    "Clean Data",
    "Validation",
    "Review Dataset",
    "Unresolved Issues",
    "Validation Report",
    "Failure Summary",
    "Validation Score",
]

pipeline_times = [
    2.5704,
    1.9592,
    1.1452,
    1.1322,
    0.7257,
    0.6103,
    0.0549,
    0.0178,
]


# ============================================================
# 4. PROFILER OPTIMIZATION
# ============================================================
#
# Controlled benchmark comparison.
#

profiler_versions = [
    "Before",
    "Optimized",
]

profiler_times = [
    5.60,
    3.77,
]


# ============================================================
# 5. CLEANER OPTIMIZATION
# ============================================================

cleaner_versions = [
    "Before",
    "Optimized",
]

cleaner_times = [
    4.38,
    3.36,
]


# ============================================================
# 6. PROFILER HOTSPOTS
# ============================================================
#
# Replace with your retained final profiler-hotspot measurements
# if your final benchmark report contains different values.
#

profiler_hotspots = [
    "Order Date",
    "Duplicate Rows",
    "Order ID Duplicate",
    "Numeric / Range",
    "Missing / Invalid",
    "Categorical",
    "Email",
]

profiler_hotspot_times = [
    0.69,
    0.62,
    0.53,
    0.44,
    0.37,
    0.36,
    0.12,
]


# ============================================================
# 7. MICRO-OPTIMIZATION RESULTS
# ============================================================

optimization_names = [
    "Missing Values\nBefore",
    "Missing Values\nAfter",
    "Numeric\nBefore",
    "Numeric\nAfter",
]

optimization_times = [
    1.4559,
    0.4268,
    2.5351,
    1.9033,
]


# ============================================================
# CREATE DASHBOARD
# ============================================================

fig = plt.figure(figsize=(20, 24))

grid = fig.add_gridspec(
    5,
    2,
    height_ratios=[0.18, 1, 1, 1, 1],
    hspace=0.48,
    wspace=0.32,
)


# ============================================================
# HEADER
# ============================================================

header = fig.add_subplot(grid[0, :])
header.axis("off")

header.text(
    0.5,
    0.72,
    "CSV DATA GUARD",
    ha="center",
    va="center",
    fontsize=30,
    fontweight="bold",
)

header.text(
    0.5,
    0.30,
    "Performance • Scalability • Optimization • Reliability",
    ha="center",
    va="center",
    fontsize=16,
)


# ============================================================
# CHART 1 — STRESS RUNTIME SCALING
# ============================================================

ax1 = fig.add_subplot(grid[1, 0])

ax1.plot(
    stress_labels,
    stress_runtime,
    marker="o",
    linewidth=2,
)

ax1.set_title(
    "Stress Test Runtime Scaling",
    fontsize=16,
    fontweight="bold",
)

ax1.set_xlabel("Dataset Size")
ax1.set_ylabel("Runtime (seconds)")
ax1.grid(alpha=0.25)

for x, y in zip(stress_labels, stress_runtime):
    ax1.annotate(
        f"{y:.2f}s",
        (x, y),
        textcoords="offset points",
        xytext=(0, 8),
        ha="center",
    )


# ============================================================
# CHART 2 — STRESS THROUGHPUT
# ============================================================

ax2 = fig.add_subplot(grid[1, 1])

bars = ax2.bar(
    stress_labels,
    stress_throughput,
)

ax2.set_title(
    "Stress Test Throughput",
    fontsize=16,
    fontweight="bold",
)

ax2.set_xlabel("Dataset Size")
ax2.set_ylabel("Rows / Second")

for bar, value in zip(bars, stress_throughput):
    ax2.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:,.0f}",
        ha="center",
        va="bottom",
        fontsize=10,
    )


# ============================================================
# CHART 3 — 500K UI PERFORMANCE
# ============================================================

ax3 = fig.add_subplot(grid[2, 0])

bars = ax3.bar(
    ui_stages,
    ui_times,
)

ax3.set_title(
    "500K Streamlit Workflow",
    fontsize=16,
    fontweight="bold",
)

ax3.set_ylabel("Time (seconds)")
ax3.tick_params(axis="x", rotation=18)

for bar, value in zip(bars, ui_times):
    ax3.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.2f}s",
        ha="center",
        va="bottom",
    )


# ============================================================
# CHART 4 — BACKEND PIPELINE BREAKDOWN
# ============================================================

ax4 = fig.add_subplot(grid[2, 1])

order = np.argsort(pipeline_times)

sorted_stages = np.array(pipeline_stages)[order]
sorted_times = np.array(pipeline_times)[order]

bars = ax4.barh(
    sorted_stages,
    sorted_times,
)

ax4.set_title(
    "500K Backend Pipeline Breakdown",
    fontsize=16,
    fontweight="bold",
)

ax4.set_xlabel("Time (seconds)")

for bar, value in zip(bars, sorted_times):
    ax4.text(
        bar.get_width(),
        bar.get_y() + bar.get_height() / 2,
        f" {value:.3f}s",
        va="center",
    )


# ============================================================
# CHART 5 — PROFILER OPTIMIZATION
# ============================================================

ax5 = fig.add_subplot(grid[3, 0])

bars = ax5.bar(
    profiler_versions,
    profiler_times,
)

ax5.set_title(
    "Profiler Optimization",
    fontsize=16,
    fontweight="bold",
)

ax5.set_ylabel("Runtime (seconds)")

for bar, value in zip(bars, profiler_times):
    ax5.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.2f}s",
        ha="center",
        va="bottom",
    )

profiler_improvement = (
    (profiler_times[0] - profiler_times[1])
    / profiler_times[0]
    * 100
)

ax5.text(
    0.5,
    0.90,
    f"~{profiler_improvement:.1f}% faster",
    transform=ax5.transAxes,
    ha="center",
    fontsize=13,
    fontweight="bold",
)


# ============================================================
# CHART 6 — CLEANER OPTIMIZATION
# ============================================================

ax6 = fig.add_subplot(grid[3, 1])

bars = ax6.bar(
    cleaner_versions,
    cleaner_times,
)

ax6.set_title(
    "Cleaner Optimization",
    fontsize=16,
    fontweight="bold",
)

ax6.set_ylabel("Runtime (seconds)")

for bar, value in zip(bars, cleaner_times):
    ax6.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.2f}s",
        ha="center",
        va="bottom",
    )

cleaner_improvement = (
    (cleaner_times[0] - cleaner_times[1])
    / cleaner_times[0]
    * 100
)

ax6.text(
    0.5,
    0.90,
    f"~{cleaner_improvement:.1f}% faster",
    transform=ax6.transAxes,
    ha="center",
    fontsize=13,
    fontweight="bold",
)


# ============================================================
# CHART 7 — PROFILER HOTSPOTS
# ============================================================

ax7 = fig.add_subplot(grid[4, 0])

order = np.argsort(profiler_hotspot_times)

sorted_names = np.array(profiler_hotspots)[order]
sorted_values = np.array(profiler_hotspot_times)[order]

bars = ax7.barh(
    sorted_names,
    sorted_values,
)

ax7.set_title(
    "Profiler Hotspots — 500K",
    fontsize=16,
    fontweight="bold",
)

ax7.set_xlabel("Time (seconds)")

for bar, value in zip(bars, sorted_values):
    ax7.text(
        bar.get_width(),
        bar.get_y() + bar.get_height() / 2,
        f" {value:.2f}s",
        va="center",
    )


# ============================================================
# CHART 8 — MICRO OPTIMIZATION RESULTS
# ============================================================

ax8 = fig.add_subplot(grid[4, 1])

bars = ax8.bar(
    optimization_names,
    optimization_times,
)

ax8.set_title(
    "Optimization Highlights",
    fontsize=16,
    fontweight="bold",
)

ax8.set_ylabel("Runtime (seconds)")

for bar, value in zip(bars, optimization_times):
    ax8.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{value:.3f}s",
        ha="center",
        va="bottom",
        fontsize=10,
    )


# ============================================================
# FOOTER
# ============================================================

fig.text(
    0.5,
    0.018,
    "500K rows  •  ~58.8 MB CSV  •  228 automated tests  •  "
    "228 passed  •  0 failed",
    ha="center",
    fontsize=14,
    fontweight="bold",
)

fig.text(
    0.5,
    0.006,
    "Timings are measured benchmark results and may vary with "
    "hardware and system load.",
    ha="center",
    fontsize=10,
)


# ============================================================
# EXPORT
# ============================================================

plt.savefig(
    OUTPUT_FILE,
    dpi=180,
    bbox_inches="tight",
)

plt.close(fig)

print(f"Performance dashboard created: {OUTPUT_FILE}")

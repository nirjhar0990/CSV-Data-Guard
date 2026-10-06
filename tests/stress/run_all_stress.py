import re
import subprocess
import sys
from pathlib import Path

import matplotlib

# ============================================================
# NON-INTERACTIVE MATPLOTLIB
# Prevents popup windows
# ============================================================

matplotlib.use("Agg")

import matplotlib.pyplot as plt


# ============================================================
# PATH CONFIGURATION
# ============================================================

STRESS_DIR = Path(__file__).resolve().parent

CHART_DIR = STRESS_DIR / "charts"

CHART_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# DISCOVERY BENCHMARK MODULES
# ============================================================

DISCOVERY_MODULES = [
    (
        "10K",
        "tests.stress.performance_discovery_tests."
        "median_performance_discovery_10K"
    ),
    (
        "100K",
        "tests.stress.performance_discovery_tests."
        "median_performance_discovery_100K"
    ),
    (
        "250K",
        "tests.stress.performance_discovery_tests."
        "median_performance_discovery_250K"
    ),
    (
        "500K",
        "tests.stress.performance_discovery_tests."
        "median_performance_discovery_500K"
    ),
]


# ============================================================
# LOCKED PERFORMANCE MODULES
# ============================================================

PERFORMANCE_MODULES = [
    (
        "10K",
        "tests.stress.performance_tests."
        "median_performance_test_10K"
    ),
    (
        "100K",
        "tests.stress.performance_tests."
        "median_performance_test_100K"
    ),
    (
        "250K",
        "tests.stress.performance_tests."
        "median_performance_test_250K"
    ),
    (
        "500K",
        "tests.stress.performance_tests."
        "median_performance_test_500K"
    ),
]


# ============================================================
# RUN A BENCHMARK MODULE
# ============================================================

def run_module(module_name):

    print()
    print("=" * 70)
    print(f"RUNNING: {module_name}")
    print("=" * 70)

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            module_name,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    output_lines = []

    if process.stdout is not None:

        for line in process.stdout:

            print(
                line,
                end=""
            )

            output_lines.append(
                line
            )

    return_code = process.wait()

    output = "".join(
        output_lines
    )

    return (
        return_code,
        output
    )


# ============================================================
# EXTRACT PERFORMANCE METRICS
# ============================================================

def extract_performance_metrics(output):

    runtime_match = re.search(
        r"Median Total Runtime:\s*([\d.]+)\s*sec",
        output
    )

    throughput_match = re.search(
        r"Median Rows / Second:\s*([\d.]+)",
        output
    )

    if runtime_match is None:

        return None

    runtime = float(
        runtime_match.group(1)
    )

    throughput = None

    if throughput_match is not None:

        throughput = float(
            throughput_match.group(1)
        )

    return {
        "runtime": runtime,
        "throughput": throughput
    }


# ============================================================
# TERMINAL PERFORMANCE SUMMARY
# ============================================================

def print_performance_summary(
    performance_results
):

    print()
    print("=" * 70)
    print(
        " CSV DATA GUARD - LOCKED PERFORMANCE SUMMARY"
    )
    print("=" * 70)

    print(
        f"{'Dataset':<12}"
        f"{'Median Runtime':>20}"
        f"{'Rows / Second':>22}"
    )

    print(
        "-" * 54
    )

    for (
        dataset,
        result
    ) in performance_results.items():

        runtime = result["runtime"]

        throughput = result["throughput"]

        if throughput is None:

            throughput_text = "N/A"

        else:

            throughput_text = (
                f"{throughput:,.2f}"
            )

        print(
            f"{dataset:<12}"
            f"{runtime:>16.3f} sec"
            f"{throughput_text:>22}"
        )

    print("=" * 70)


# ============================================================
# SAVE RUNTIME LINE CHART
# ============================================================

def save_runtime_line_chart(
    performance_results
):

    labels = list(
        performance_results.keys()
    )

    runtimes = [
        performance_results[label]["runtime"]
        for label in labels
    ]

    plt.figure(
        figsize=(10, 6)
    )

    plt.plot(
        labels,
        runtimes,
        marker="o",
        linewidth=2.5,
        markersize=8
    )

    for (
        label,
        runtime
    ) in zip(
        labels,
        runtimes
    ):

        plt.annotate(
            f"{runtime:.3f} sec",
            (
                label,
                runtime
            ),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center",
            fontsize=10
        )

    plt.title(
        "CSV Data Guard - Performance Scaling",
        fontsize=14
    )

    plt.xlabel(
        "Dataset Size",
        fontsize=11
    )

    plt.ylabel(
        "Median Runtime (seconds)",
        fontsize=11
    )

    plt.grid(
        True,
        alpha=0.3
    )

    plt.tight_layout()

    chart_path = (
        CHART_DIR
        / "performance_runtime_line_chart.png"
    )

    plt.savefig(
        chart_path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    return chart_path


# ============================================================
# SAVE RUNTIME BAR CHART
# ============================================================

def save_runtime_bar_chart(
    performance_results
):

    labels = list(
        performance_results.keys()
    )

    runtimes = [
        performance_results[label]["runtime"]
        for label in labels
    ]

    plt.figure(
        figsize=(10, 6)
    )

    bars = plt.bar(
        labels,
        runtimes
    )

    max_runtime = max(
        runtimes
    )

    for (
        bar,
        runtime
    ) in zip(
        bars,
        runtimes
    ):

        plt.text(
            bar.get_x()
            + bar.get_width() / 2,

            bar.get_height()
            + (
                max_runtime * 0.02
            ),

            f"{runtime:.3f} sec",

            ha="center",
            va="bottom",
            fontsize=10
        )

    plt.title(
        "CSV Data Guard - Median Runtime",
        fontsize=14
    )

    plt.xlabel(
        "Dataset Size",
        fontsize=11
    )

    plt.ylabel(
        "Median Runtime (seconds)",
        fontsize=11
    )

    plt.grid(
        True,
        axis="y",
        alpha=0.3
    )

    plt.tight_layout()

    chart_path = (
        CHART_DIR
        / "performance_runtime_bar_chart.png"
    )

    plt.savefig(
        chart_path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    return chart_path


# ============================================================
# SAVE THROUGHPUT BAR CHART
# ============================================================

def save_throughput_chart(
    performance_results
):

    labels = list(
        performance_results.keys()
    )

    throughput_values = [
        performance_results[label]["throughput"]
        for label in labels
    ]

    if any(
        value is None
        for value in throughput_values
    ):

        raise ValueError(
            "Throughput chart cannot be generated because "
            "one or more throughput values are missing."
        )

    plt.figure(
        figsize=(10, 6)
    )

    bars = plt.bar(
        labels,
        throughput_values
    )

    max_throughput = max(
        throughput_values
    )

    for (
        bar,
        throughput
    ) in zip(
        bars,
        throughput_values
    ):

        plt.text(
            bar.get_x()
            + bar.get_width() / 2,

            bar.get_height()
            + (
                max_throughput * 0.02
            ),

            f"{throughput:,.0f}",

            ha="center",
            va="bottom",
            fontsize=10
        )

    plt.title(
        "CSV Data Guard - Processing Throughput",
        fontsize=14
    )

    plt.xlabel(
        "Dataset Size",
        fontsize=11
    )

    plt.ylabel(
        "Rows Processed per Second",
        fontsize=11
    )

    plt.grid(
        True,
        axis="y",
        alpha=0.3
    )

    plt.tight_layout()

    chart_path = (
        CHART_DIR
        / "performance_throughput_chart.png"
    )

    plt.savefig(
        chart_path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    return chart_path


# ============================================================
# MAIN
# ============================================================

def main():

    failures = []

    performance_results = {}


    # ========================================================
    # 1. RUN DISCOVERY BENCHMARKS
    # ========================================================

    print()
    print("=" * 70)
    print(
        " CSV DATA GUARD - PERFORMANCE DISCOVERY TESTS"
    )
    print("=" * 70)

    for (
        dataset,
        module
    ) in DISCOVERY_MODULES:

        (
            return_code,
            _
        ) = run_module(
            module
        )

        if return_code != 0:

            failures.append(
                module
            )


    # ========================================================
    # 2. RUN LOCKED PERFORMANCE TESTS
    # ========================================================

    print()
    print("=" * 70)
    print(
        " CSV DATA GUARD - LOCKED PERFORMANCE TESTS"
    )
    print("=" * 70)

    for (
        dataset,
        module
    ) in PERFORMANCE_MODULES:

        (
            return_code,
            output
        ) = run_module(
            module
        )

        if return_code != 0:

            failures.append(
                module
            )

            continue

        metrics = (
            extract_performance_metrics(
                output
            )
        )

        if metrics is None:

            print()
            print(
                f"ERROR: Could not extract "
                f"performance metrics for "
                f"{dataset}."
            )

            failures.append(
                module
            )

            continue

        performance_results[
            dataset
        ] = metrics


    # ========================================================
    # 3. STRESS TEST SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print(
        " CSV DATA GUARD - STRESS TEST SUMMARY"
    )
    print("=" * 70)

    if failures:

        print(
            f"FAILED: "
            f"{len(failures)} module(s)"
        )

        for module in failures:

            print(
                f"  - {module}"
            )

        sys.exit(1)

    print(
        "ALL DISCOVERY AND PERFORMANCE "
        "TESTS COMPLETED SUCCESSFULLY."
    )


    # ========================================================
    # 4. VERIFY ALL FOUR PERFORMANCE MARKERS
    # ========================================================

    expected_datasets = {
        "10K",
        "100K",
        "250K",
        "500K"
    }

    actual_datasets = set(
        performance_results.keys()
    )

    if actual_datasets != expected_datasets:

        print()
        print(
            "ERROR: Not all four performance "
            "markers were collected."
        )

        print(
            "Expected:",
            sorted(
                expected_datasets
            )
        )

        print(
            "Collected:",
            sorted(
                actual_datasets
            )
        )

        sys.exit(1)


    # ========================================================
    # 5. TERMINAL SUMMARY TABLE
    # ========================================================

    print_performance_summary(
        performance_results
    )


    # ========================================================
    # 6. SAVE RUNTIME LINE CHART
    # ========================================================

    runtime_line_chart_path = (
        save_runtime_line_chart(
            performance_results
        )
    )


    # ========================================================
    # 7. SAVE RUNTIME BAR CHART
    # ========================================================

    runtime_bar_chart_path = (
        save_runtime_bar_chart(
            performance_results
        )
    )


    # ========================================================
    # 8. SAVE THROUGHPUT BAR CHART
    # ========================================================

    throughput_chart_path = (
        save_throughput_chart(
            performance_results
        )
    )


    # ========================================================
    # 9. FINAL CHART SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print(
        " PERFORMANCE CHARTS"
    )
    print("=" * 70)

    print(
        f"Runtime line chart saved: "
        f"{runtime_line_chart_path}"
    )

    print(
        f"Runtime bar chart saved:  "
        f"{runtime_bar_chart_path}"
    )

    print(
        f"Throughput chart saved:   "
        f"{throughput_chart_path}"
    )

    print()

    print(
        "No chart windows were opened."
    )

    print("=" * 70)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()

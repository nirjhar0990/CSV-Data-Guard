import contextlib
import io
import re
import statistics
import time
from pathlib import Path

import pandas as pd


from pipeline.profiler import (
    profile_data,
)


# ============================================================
# CONFIGURATION
# ============================================================

DATASET_PATH = Path(
    "data/messy_retail_data_500K.csv"
)

WARMUP_RUNS = 1

MEASURED_RUNS = 5


# ============================================================
# PERFORMANCE LINE PATTERN
# ============================================================

PERFORMANCE_PATTERN = re.compile(
    r"\[PROFILER PERFORMANCE\]\s+"
    r"(.+?)\s{2,}"
    r"([0-9.]+)\s+sec"
)


# ============================================================
# CREATE SEMANTIC SNAPSHOT
# ============================================================

def create_profile_snapshot(
    profile
):
    """
    Create a compact semantic snapshot.

    This lets us confirm that every profiler run
    produces exactly the same business result.
    """

    return {

        "rows":
            profile[
                "rows"
            ],

        "columns":
            profile[
                "columns"
            ],

        "duplicate_rows":
            profile[
                "duplicate_rows"
            ],

        "total_blank_cells":
            profile[
                "missing_value_profile"
            ][
                "total_blank_cells"
            ],

        "total_missing_value_cells":
            profile[
                "missing_value_profile"
            ][
                "total_missing_value_cells"
            ],

        "total_invalid_value_cells":
            profile[
                "missing_value_profile"
            ][
                "total_invalid_value_cells"
            ],

        "duplicate_order_id_rows":
            profile[
                "order_id_duplicate_profile"
            ][
                "affected_rows"
            ],

        "invalid_customer_names":
            profile[
                "customer_name_profile"
            ][
                "invalid_count"
            ],

        "invalid_email_syntax":
            profile[
                "email_profile"
            ][
                "invalid_syntax_count"
            ],

        "invalid_email_domain":
            profile[
                "email_profile"
            ][
                "invalid_domain_count"
            ],

        "invalid_customer_ages":
            profile[
                "age_profile"
            ][
                "invalid_count"
            ],

        "invalid_customer_ratings":
            profile[
                "rating_profile"
            ][
                "invalid_count"
            ],

        "invalid_dates":
            profile[
                "order_date_profile"
            ][
                "invalid_count"
            ],

        "non_standard_dates":
            profile[
                "order_date_profile"
            ][
                "non_standard_count"
            ],

        "invalid_order_ids":
            profile[
                "order_id_profile"
            ][
                "invalid_count"
            ],

        "issue_summary":
            profile[
                "issue_summary"
            ],
    }


# ============================================================
# PARSE PROFILER TIMINGS
# ============================================================

def parse_profiler_timings(
    output
):
    """
    Parse terminal performance output produced by profile_data().
    """

    timings = {}

    for line in output.splitlines():

        match = (
            PERFORMANCE_PATTERN.search(
                line
            )
        )

        if match is None:
            continue

        stage = (
            match.group(
                1
            )
            .strip()
        )

        elapsed = float(
            match.group(
                2
            )
        )

        timings[
            stage
        ] = elapsed

    return timings


# ============================================================
# RUN PROFILER ONCE
# ============================================================

def run_profile_once(
    df,
    show_output=False
):
    """
    Execute profile_data() once.

    Captures its internal performance output so that
    timings can be analysed programmatically.
    """

    output_buffer = (
        io.StringIO()
    )

    overall_start = (
        time.perf_counter()
    )

    with contextlib.redirect_stdout(
        output_buffer
    ):

        profile = profile_data(
            df
        )

    overall_elapsed = (
        time.perf_counter()
        - overall_start
    )

    output = (
        output_buffer.getvalue()
    )

    timings = (
        parse_profiler_timings(
            output
        )
    )

    timings[
        "BENCHMARK WALL CLOCK"
    ] = overall_elapsed

    if show_output:

        print(
            output,
            end=""
        )

    return (
        profile,
        timings,
    )


# ============================================================
# WARMUP
# ============================================================

def run_warmup(
    df
):

    print(
        "\n"
        "============================================================"
    )

    print(
        "WARMUP"
    )

    print(
        "============================================================"
    )

    for run_number in range(
        1,
        WARMUP_RUNS + 1,
    ):

        start = (
            time.perf_counter()
        )

        profile_data(
            df
        )

        elapsed = (
            time.perf_counter()
            - start
        )

        print(
            f"Warmup {run_number}: "
            f"{elapsed:.4f} sec"
        )


# ============================================================
# MEASURED RUNS
# ============================================================

def run_benchmark(
    df
):

    print(
        "\n"
        "============================================================"
    )

    print(
        "MEASURED PROFILER RUNS"
    )

    print(
        "============================================================"
    )

    all_timings = []

    snapshots = []

    for run_number in range(
        1,
        MEASURED_RUNS + 1,
    ):

        (
            profile,
            timings,
        ) = run_profile_once(
            df
        )

        all_timings.append(
            timings
        )

        snapshots.append(
            create_profile_snapshot(
                profile
            )
        )

        total_profile = (
            timings.get(
                "TOTAL PROFILE",
                timings[
                    "BENCHMARK WALL CLOCK"
                ],
            )
        )

        print(
            f"Run {run_number}: "
            f"{total_profile:.4f} sec"
        )

    return (
        all_timings,
        snapshots,
    )


# ============================================================
# SEMANTIC CONSISTENCY
# ============================================================

def check_semantic_consistency(
    snapshots
):

    print(
        "\n"
        "============================================================"
    )

    print(
        "SEMANTIC CONSISTENCY"
    )

    print(
        "============================================================"
    )

    baseline = (
        snapshots[0]
    )

    consistent = all(
        snapshot == baseline
        for snapshot
        in snapshots
    )

    print(
        "Profiler runs internally consistent:",
        consistent,
    )

    print(
        "\nProfiler snapshot:"
    )

    for key, value in (
        baseline.items()
    ):

        if key == "issue_summary":

            print(
                "  issue_summary:"
            )

            for (
                issue_name,
                issue_count
            ) in value.items():

                print(
                    f"    {issue_name}: "
                    f"{issue_count}"
                )

        else:

            print(
                f"  {key}: "
                f"{value}"
            )

    if not consistent:

        raise AssertionError(
            "Profiler runs produced different results."
        )


# ============================================================
# MEDIAN CALCULATION
# ============================================================

def calculate_stage_medians(
    all_timings
):

    all_stages = set()

    for timing in all_timings:

        all_stages.update(
            timing.keys()
        )

    medians = {}

    for stage in all_stages:

        values = [
            timing[
                stage
            ]
            for timing
            in all_timings
            if stage in timing
        ]

        medians[
            stage
        ] = statistics.median(
            values
        )

    return medians


# ============================================================
# PRINT MEDIAN RESULTS
# ============================================================

def print_median_results(
    all_timings
):

    medians = (
        calculate_stage_medians(
            all_timings
        )
    )

    print(
        "\n"
        "============================================================"
    )

    print(
        "500K PROFILER MEDIAN PERFORMANCE"
    )

    print(
        "============================================================"
    )


    excluded_stages = {
        "TOTAL PROFILE",
        "BENCHMARK WALL CLOCK",
    }


    stage_rows = [
        (
            stage,
            elapsed,
        )
        for (
            stage,
            elapsed
        ) in medians.items()
        if stage not in excluded_stages
    ]


    stage_rows.sort(
        key=lambda item: item[1],
        reverse=True,
    )


    print(
        f"{'Profiler Stage':<42}"
        f"{'Median Time':>15}"
    )

    print(
        "-" * 57
    )


    for (
        stage,
        elapsed
    ) in stage_rows:

        print(
            f"{stage:<42}"
            f"{elapsed:>11.4f} sec"
        )


    print(
        "-" * 57
    )


    total_profile = (
        medians.get(
            "TOTAL PROFILE"
        )
    )

    wall_clock = (
        medians.get(
            "BENCHMARK WALL CLOCK"
        )
    )


    if total_profile is not None:

        print(
            f"{'TOTAL PROFILE':<42}"
            f"{total_profile:>11.4f} sec"
        )


    if wall_clock is not None:

        print(
            f"{'BENCHMARK WALL CLOCK':<42}"
            f"{wall_clock:>11.4f} sec"
        )


    # ========================================================
    # TOP HOTSPOTS
    # ========================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "TOP PROFILER HOTSPOTS"
    )

    print(
        "============================================================"
    )


    for rank, (
        stage,
        elapsed
    ) in enumerate(
        stage_rows[
            :6
        ],
        start=1,
    ):

        if (
            total_profile is not None
            and total_profile > 0
        ):

            percentage = (
                elapsed
                / total_profile
                * 100
            )

        else:

            percentage = 0.0


        print(
            f"{rank}. "
            f"{stage:<36} "
            f"{elapsed:.4f} sec "
            f"({percentage:.1f}%)"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        "CSV DATA GUARD"
    )

    print(
        "500K PROFILER MEDIAN BENCHMARK"
    )


    if not DATASET_PATH.exists():

        raise FileNotFoundError(
            f"Dataset not found: "
            f"{DATASET_PATH}"
        )


    # ========================================================
    # LOAD DATASET ONCE
    # ========================================================

    print(
        f"\nDataset: "
        f"{DATASET_PATH}"
    )

    print(
        f"Warmup runs: "
        f"{WARMUP_RUNS}"
    )

    print(
        f"Measured runs: "
        f"{MEASURED_RUNS}"
    )


    load_start = (
        time.perf_counter()
    )

    df = pd.read_csv(
        DATASET_PATH,
        keep_default_na=False,
    )

    load_elapsed = (
        time.perf_counter()
        - load_start
    )


    print(
        f"\nDataset loaded once in "
        f"{load_elapsed:.4f} sec"
    )

    print(
        f"Rows: "
        f"{len(df):,}"
    )

    print(
        f"Columns: "
        f"{len(df.columns)}"
    )


    # ========================================================
    # WARMUP
    # ========================================================

    run_warmup(
        df
    )


    # ========================================================
    # BENCHMARK
    # ========================================================

    (
        all_timings,
        snapshots,
    ) = run_benchmark(
        df
    )


    # ========================================================
    # CORRECTNESS CHECK
    # ========================================================

    check_semantic_consistency(
        snapshots
    )


    # ========================================================
    # PERFORMANCE SUMMARY
    # ========================================================

    print_median_results(
        all_timings
    )


if __name__ == "__main__":
    main()

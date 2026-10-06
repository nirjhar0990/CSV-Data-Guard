import statistics
import time
from pathlib import Path

import pandas as pd


from pipeline.profiler import (
    profile_data,
)

from pipeline.orchestrator import (
    run_pipeline,
    run_pipeline_from_dataframe,
)


# ============================================================
# CONFIGURATION
# ============================================================

DATASET_PATH = Path(
    "data/messy_retail_data_10K.csv"
)

RUNS = 5


# ============================================================
# SEMANTIC SNAPSHOT
# ============================================================

def create_snapshot(result):

    return {
        "original_rows":
            len(
                result[
                    "original_data"
                ]
            ),

        "current_rows":
            len(
                result.get(
                    "corrected_data",
                    result[
                        "cleaned_data"
                    ],
                )
            ),

        "unresolved_issues":
            len(
                result[
                    "unresolved_cleaning_issues"
                ]
            ),

        "cleaning_score":
            result[
                "cleaning_score"
            ],

        "validation_score":
            result[
                "validation_score"
            ],

        "problem_map_rows":
            len(
                result[
                    "problem_map"
                ]
            ),

        "review_records":
            len(
                result[
                    "review_data"
                ]
            ),

        "export_allowed":
            result[
                "export_allowed"
            ],

        "export_status":
            result[
                "export_status"
            ],
    }


# ============================================================
# FILE-PATH PIPELINE
# ============================================================

def benchmark_file_path_pipeline():

    runtimes = []
    snapshots = []

    print(
        "\n"
        "============================================================"
    )

    print(
        "PATH A — FILE-PATH PIPELINE"
    )

    print(
        "============================================================"
    )

    for run_number in range(
        1,
        RUNS + 1,
    ):

        start = (
            time.perf_counter()
        )

        result = run_pipeline(
            DATASET_PATH
        )

        elapsed = (
            time.perf_counter()
            - start
        )

        runtimes.append(
            elapsed
        )

        snapshots.append(
            create_snapshot(
                result
            )
        )

        print(
            f"Run {run_number}: "
            f"{elapsed:.4f} sec"
        )

    return (
        runtimes,
        snapshots,
    )


# ============================================================
# DATAFRAME PIPELINE
# ============================================================

def benchmark_dataframe_pipeline():

    runtimes = []
    snapshots = []

    print(
        "\n"
        "============================================================"
    )

    print(
        "PATH B — DATAFRAME PIPELINE"
    )

    print(
        "============================================================"
    )

    for run_number in range(
        1,
        RUNS + 1,
    ):

        total_start = (
            time.perf_counter()
        )


        # ----------------------------------------------------
        # SAME STREAMLIT-STYLE READ
        # ----------------------------------------------------

        read_start = (
            time.perf_counter()
        )

        raw_df = pd.read_csv(
            DATASET_PATH,
            keep_default_na=False,
        )

        read_elapsed = (
            time.perf_counter()
            - read_start
        )


        # ----------------------------------------------------
        # SAME STREAMLIT-STYLE PROFILE
        # ----------------------------------------------------

        profile_start = (
            time.perf_counter()
        )

        profile = profile_data(
            raw_df
        )

        profile_elapsed = (
            time.perf_counter()
            - profile_start
        )


        # ----------------------------------------------------
        # DATAFRAME PIPELINE
        # ----------------------------------------------------

        pipeline_start = (
            time.perf_counter()
        )

        result = (
            run_pipeline_from_dataframe(
                raw_df,
                profile,
            )
        )

        pipeline_elapsed = (
            time.perf_counter()
            - pipeline_start
        )


        total_elapsed = (
            time.perf_counter()
            - total_start
        )

        runtimes.append(
            {
                "read":
                    read_elapsed,

                "profile":
                    profile_elapsed,

                "pipeline":
                    pipeline_elapsed,

                "total":
                    total_elapsed,
            }
        )

        snapshots.append(
            create_snapshot(
                result
            )
        )

        print(
            f"Run {run_number}: "
            f"read={read_elapsed:.4f} sec | "
            f"profile={profile_elapsed:.4f} sec | "
            f"pipeline={pipeline_elapsed:.4f} sec | "
            f"total={total_elapsed:.4f} sec"
        )

    return (
        runtimes,
        snapshots,
    )


# ============================================================
# SEMANTIC CONSISTENCY CHECK
# ============================================================

def check_semantic_consistency(
    file_snapshots,
    dataframe_snapshots,
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


    file_baseline = (
        file_snapshots[0]
    )

    dataframe_baseline = (
        dataframe_snapshots[0]
    )


    file_consistent = all(
        snapshot == file_baseline
        for snapshot
        in file_snapshots
    )

    dataframe_consistent = all(
        snapshot == dataframe_baseline
        for snapshot
        in dataframe_snapshots
    )

    cross_path_consistent = (
        file_baseline
        == dataframe_baseline
    )


    print(
        "File-path runs internally consistent:",
        file_consistent,
    )

    print(
        "DataFrame runs internally consistent:",
        dataframe_consistent,
    )

    print(
        "File-path vs DataFrame equivalent:",
        cross_path_consistent,
    )


    print(
        "\nFile-path snapshot:"
    )

    for key, value in (
        file_baseline.items()
    ):

        print(
            f"  {key}: {value}"
        )


    print(
        "\nDataFrame snapshot:"
    )

    for key, value in (
        dataframe_baseline.items()
    ):

        print(
            f"  {key}: {value}"
        )


    if not (
        file_consistent
        and dataframe_consistent
        and cross_path_consistent
    ):

        raise AssertionError(
            "Pipeline paths are not semantically equivalent."
        )


# ============================================================
# RESULTS
# ============================================================

def print_results(
    file_runtimes,
    dataframe_runtimes,
):

    print(
        "\n"
        "============================================================"
    )

    print(
        "A/B PERFORMANCE SUMMARY"
    )

    print(
        "============================================================"
    )


    file_median = (
        statistics.median(
            file_runtimes
        )
    )


    dataframe_read_median = (
        statistics.median(
            item[
                "read"
            ]
            for item
            in dataframe_runtimes
        )
    )

    dataframe_profile_median = (
        statistics.median(
            item[
                "profile"
            ]
            for item
            in dataframe_runtimes
        )
    )

    dataframe_pipeline_median = (
        statistics.median(
            item[
                "pipeline"
            ]
            for item
            in dataframe_runtimes
        )
    )

    dataframe_total_median = (
        statistics.median(
            item[
                "total"
            ]
            for item
            in dataframe_runtimes
        )
    )


    difference = (
        dataframe_total_median
        - file_median
    )


    percentage_difference = (
        (
            difference
            / file_median
        )
        * 100
    )


    print(
        f"File-path pipeline median:        "
        f"{file_median:.4f} sec"
    )

    print(
        f"DataFrame read median:            "
        f"{dataframe_read_median:.4f} sec"
    )

    print(
        f"DataFrame profile median:         "
        f"{dataframe_profile_median:.4f} sec"
    )

    print(
        f"DataFrame pipeline median:        "
        f"{dataframe_pipeline_median:.4f} sec"
    )

    print(
        f"DataFrame total median:           "
        f"{dataframe_total_median:.4f} sec"
    )

    print(
        f"Difference:                       "
        f"{difference:+.4f} sec"
    )

    print(
        f"Percentage difference:            "
        f"{percentage_difference:+.2f}%"
    )


    if (
        dataframe_total_median
        < file_median
    ):

        print(
            "\nRESULT:"
        )

        print(
            "DataFrame path is faster."
        )

    elif (
        dataframe_total_median
        > file_median
    ):

        print(
            "\nRESULT:"
        )

        print(
            "File-path pipeline is faster."
        )

    else:

        print(
            "\nRESULT:"
        )

        print(
            "Both paths have equivalent median runtime."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    if not DATASET_PATH.exists():

        raise FileNotFoundError(
            f"Dataset not found: "
            f"{DATASET_PATH}"
        )


    print(
        "\n"
        "CSV DATA GUARD"
    )

    print(
        "10K PIPELINE A/B BENCHMARK"
    )

    print(
        f"Dataset: {DATASET_PATH}"
    )

    print(
        f"Runs per path: {RUNS}"
    )


    file_runtimes, file_snapshots = (
        benchmark_file_path_pipeline()
    )


    (
        dataframe_runtimes,
        dataframe_snapshots,
    ) = benchmark_dataframe_pipeline()


    check_semantic_consistency(
        file_snapshots,
        dataframe_snapshots,
    )


    print_results(
        file_runtimes,
        dataframe_runtimes,
    )


if __name__ == "__main__":
    main()

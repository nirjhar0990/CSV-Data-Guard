import statistics
import time
from pathlib import Path

import pandas as pd

from pipeline.cleaner import (
    standardize_missing_values,
    remove_duplicate_rows,
    clean_text_casing,
    clean_customer_names,
    clean_city_names,
    clean_categories,
    clean_emails,
    clean_numeric_values,
    clean_numeric_ranges,
    standardize_dates,
    handle_invalid_values,
    clean_data,
)


DATASET_PATH = Path(
    "data/messy_retail_data_500K.csv"
)

WARMUP_RUNS = 1
MEASURED_RUNS = 5


STAGES = [
    (
        "standardize_missing_values",
        standardize_missing_values,
    ),
    (
        "remove_duplicate_rows",
        remove_duplicate_rows,
    ),
    (
        "clean_text_casing",
        clean_text_casing,
    ),
    (
        "clean_customer_names",
        clean_customer_names,
    ),
    (
        "clean_city_names",
        clean_city_names,
    ),
    (
        "clean_categories",
        clean_categories,
    ),
    (
        "clean_emails",
        clean_emails,
    ),
    (
        "clean_numeric_values",
        clean_numeric_values,
    ),
    (
        "clean_numeric_ranges",
        clean_numeric_ranges,
    ),
    (
        "standardize_dates",
        standardize_dates,
    ),
    (
        "handle_invalid_values",
        handle_invalid_values,
    ),
]


def snapshot_cleaned(df):

    return {
        "rows":
            len(df),

        "columns":
            len(df.columns),

        "duplicate_rows":
            int(
                df.duplicated(
                    subset=[
                        column
                        for column in df.columns
                        if column != "Record_ID"
                    ]
                ).sum()
            ),

        "dtypes":
            {
                column:
                    str(dtype)
                for column, dtype
                in df.dtypes.items()
            },

        "missing_counts":
            df.isna()
            .sum()
            .to_dict(),

        "remaining_invalid":
            int(
                (
                    df.astype("string")
                    == "INVALID"
                )
                .sum()
                .sum()
            ),
    }


def run_helpers_once(raw_df):

    current = raw_df

    timings = {}

    for stage_name, stage_func in STAGES:

        start = (
            time.perf_counter()
        )

        current = stage_func(
            current
        )

        timings[
            stage_name
        ] = (
            time.perf_counter()
            - start
        )

    timings[
        "helper total"
    ] = sum(
        timings.values()
    )

    return (
        current,
        timings,
    )


def run_clean_data_once(raw_df):

    start = (
        time.perf_counter()
    )

    cleaned_df, cleaning_checks = (
        clean_data(
            raw_df
        )
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    return (
        cleaned_df,
        cleaning_checks,
        elapsed,
    )


def main():

    if not DATASET_PATH.exists():

        raise FileNotFoundError(
            DATASET_PATH
        )

    print(
        "\nCSV DATA GUARD"
    )

    print(
        "500K CLEANER MEDIAN BENCHMARK"
    )

    print(
        f"\nDataset: {DATASET_PATH}"
    )

    print(
        f"Warmup runs: {WARMUP_RUNS}"
    )

    print(
        f"Measured runs: {MEASURED_RUNS}"
    )

    load_start = (
        time.perf_counter()
    )

    raw_df = pd.read_csv(
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
        f"Rows: {len(raw_df):,}"
    )

    print(
        f"Columns: {len(raw_df.columns)}"
    )

    # ========================================================
    # WARMUP
    # ========================================================

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

        helper_cleaned, helper_timings = (
            run_helpers_once(
                raw_df
            )
        )

        clean_cleaned, checks, clean_elapsed = (
            run_clean_data_once(
                raw_df
            )
        )

        print(
            f"Warmup {run_number}: "
            f"helper total={helper_timings['helper total']:.4f} sec, "
            f"clean_data={clean_elapsed:.4f} sec"
        )

    # ========================================================
    # MEASURED RUNS
    # ========================================================

    print(
        "\n"
        "============================================================"
    )

    print(
        "MEASURED RUNS"
    )

    print(
        "============================================================"
    )

    all_helper_timings = []
    clean_data_times = []
    snapshots = []

    for run_number in range(
        1,
        MEASURED_RUNS + 1,
    ):

        helper_cleaned, helper_timings = (
            run_helpers_once(
                raw_df
            )
        )

        clean_cleaned, checks, clean_elapsed = (
            run_clean_data_once(
                raw_df
            )
        )

        helper_snapshot = (
            snapshot_cleaned(
                helper_cleaned
            )
        )

        clean_snapshot = (
            snapshot_cleaned(
                clean_cleaned
            )
        )

        if helper_snapshot != clean_snapshot:

            raise AssertionError(
                "Helper-by-helper result does not match clean_data()."
            )

        all_helper_timings.append(
            helper_timings
        )

        clean_data_times.append(
            clean_elapsed
        )

        snapshots.append(
            clean_snapshot
        )

        print(
            f"Run {run_number}: "
            f"helper total={helper_timings['helper total']:.4f} sec, "
            f"clean_data={clean_elapsed:.4f} sec"
        )

    # ========================================================
    # SEMANTIC CONSISTENCY
    # ========================================================

    consistent = all(
        snapshot
        == snapshots[0]
        for snapshot
        in snapshots
    )

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

    print(
        "Cleaner runs internally consistent:",
        consistent,
    )

    if not consistent:

        raise AssertionError(
            "Cleaner output changed between measured runs."
        )

    baseline = snapshots[0]

    print(
        "\nCleaner snapshot:"
    )

    print(
        "  rows:",
        baseline[
            "rows"
        ],
    )

    print(
        "  columns:",
        baseline[
            "columns"
        ],
    )

    print(
        "  duplicate_rows:",
        baseline[
            "duplicate_rows"
        ],
    )

    print(
        "  remaining_INVALID:",
        baseline[
            "remaining_invalid"
        ],
    )

    print(
        "\nKey dtypes:"
    )

    for column in (
        "Quantity",
        "Unit_Price",
        "Discount",
        "Total_Amount",
        "Order_Date",
        "Customer_Age",
        "Customer_Rating",
    ):

        print(
            f"  {column}: "
            f"{baseline['dtypes'].get(column)}"
        )

    # ========================================================
    # MEDIANS
    # ========================================================

    stage_medians = {}

    for stage_name, _ in STAGES:

        stage_medians[
            stage_name
        ] = statistics.median(
            timing[
                stage_name
            ]
            for timing
            in all_helper_timings
        )

    helper_total_median = (
        statistics.median(
            timing[
                "helper total"
            ]
            for timing
            in all_helper_timings
        )
    )

    clean_data_median = (
        statistics.median(
            clean_data_times
        )
    )

    print(
        "\n"
        "============================================================"
    )

    print(
        "500K CLEANER MEDIAN PERFORMANCE"
    )

    print(
        "============================================================"
    )

    ranking = sorted(
        stage_medians.items(),
        key=lambda item:
            item[1],
        reverse=True,
    )

    print(
        f"{'Cleaner Stage':<36}"
        f"{'Median Time':>15}"
        f"{'Share':>10}"
    )

    print(
        "-" * 61
    )

    for stage_name, elapsed in ranking:

        share = (
            elapsed
            / helper_total_median
            * 100
            if helper_total_median
            else 0.0
        )

        print(
            f"{stage_name:<36}"
            f"{elapsed:>11.4f} sec"
            f"{share:>8.1f}%"
        )

    print(
        "-" * 61
    )

    print(
        f"{'HELPER TOTAL':<36}"
        f"{helper_total_median:>11.4f} sec"
    )

    print(
        f"{'CLEAN_DATA':<36}"
        f"{clean_data_median:>11.4f} sec"
    )

    print(
        "\n"
        "============================================================"
    )

    print(
        "CLEAN_DATA RUN SUMMARY"
    )

    print(
        "============================================================"
    )

    for index, elapsed in enumerate(
        clean_data_times,
        start=1,
    ):

        status = (
            "TARGET"
            if 2.7 <= elapsed <= 3.0
            else ""
        )

        print(
            f"Run {index}: "
            f"{elapsed:.4f} sec"
            + (
                f"  {status}"
                if status
                else ""
            )
        )

    print(
        f"\nMedian clean_data: "
        f"{clean_data_median:.4f} sec"
    )

    print(
        f"Best clean_data:   "
        f"{min(clean_data_times):.4f} sec"
    )

    print(
        f"Worst clean_data:  "
        f"{max(clean_data_times):.4f} sec"
    )


if __name__ == "__main__":
    main()

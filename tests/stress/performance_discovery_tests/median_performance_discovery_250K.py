import gc
import statistics
import time

from pipeline.profiler import (
    load_csv,
    profile_data
)

from pipeline.cleaner import (
    clean_data
)

from pipeline.validator import (
    validate_data,
    calculate_validation_score,
    calculate_cleaning_score,
    find_unresolved_cleaning_issues
)

from pipeline.problem_map import (
    create_problem_map
)

from pipeline.reporting import (
    create_validation_report
)

from pipeline.review import (
    create_review_dataset
)


# ============================================================
# CONFIGURATION
# ============================================================

FILE_PATH = (
    "data/messy_retail_data_250K.csv"
)

RUNS = 5

EXPECTED_ROWS = 250000


# ============================================================
# HELPERS
# ============================================================

def median(values):

    return statistics.median(
        values
    )


def fmt(seconds):

    return (
        f"{seconds:.3f}"
    )


# ============================================================
# SINGLE BENCHMARK RUN
# ============================================================

def run_once(
    run_number
):

    gc.collect()

    timings = {}

    print(
        f"\n===== RUN {run_number}/{RUNS} =====",
        flush=True
    )

    total_start = (
        time.perf_counter()
    )

    # ========================================================
    # 1. LOAD CSV
    # ========================================================

    start = (
        time.perf_counter()
    )

    raw_df = load_csv(
        FILE_PATH
    )

    timings[
        "Load CSV"
    ] = (
        time.perf_counter()
        - start
    )

    # --------------------------------------------------------
    # ROW COUNT SAFETY CHECK
    # --------------------------------------------------------

    if len(raw_df) != EXPECTED_ROWS:

        raise ValueError(
            f"Expected {EXPECTED_ROWS} rows, "
            f"found {len(raw_df)}."
        )

    # ========================================================
    # 2. PROFILING
    # ========================================================

    start = (
        time.perf_counter()
    )

    profile = profile_data(
        raw_df
    )

    timings[
        "Profiling"
    ] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 3. ADD Record_ID
    # ========================================================

    original_df = (
        raw_df.copy()
    )

    original_df.insert(
        0,
        "Record_ID",
        range(
            1,
            len(original_df) + 1
        )
    )

    # ========================================================
    # 4. CLEANING
    # ========================================================

    start = (
        time.perf_counter()
    )

    (
        cleaned_df,
        cleaning_checks
    ) = clean_data(
        original_df
    )

    timings[
        "Cleaning"
    ] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 5. UNRESOLVED CLEANING ISSUES
    # ========================================================

    start = (
        time.perf_counter()
    )

    unresolved_issues = (
        find_unresolved_cleaning_issues(
            original_df,
            cleaned_df
        )
    )

    timings[
        "Unresolved issue detection"
    ] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 6. VALIDATION
    # ========================================================

    start = (
        time.perf_counter()
    )

    validation_result = (
        validate_data(
            cleaned_df
        )
    )

    timings[
        "Validation"
    ] = (
        time.perf_counter()
        - start
    )

    failure_cases = (
        validation_result[
            "failure_cases"
        ]
    )

    # ========================================================
    # 7. SCORES
    # ========================================================

    start = (
        time.perf_counter()
    )

    initial_unresolved_count = (
        len(
            unresolved_issues
        )
    )

    cleaning_score = (
        calculate_cleaning_score(
            initial_unresolved_count,
            initial_unresolved_count
        )
    )

    validation_score = (
        calculate_validation_score(
            cleaned_df,
            failure_cases
        )
    )

    timings[
        "Score calculation"
    ] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 8. PROBLEM MAP
    # ========================================================

    start = (
        time.perf_counter()
    )

    problem_map_df = (
        create_problem_map(
            original_df,
            failure_cases,
            unresolved_issues
        )
    )

    timings[
        "Problem map generation"
    ] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 9. REPORT
    # ========================================================

    start = (
        time.perf_counter()
    )

    report = (
        create_validation_report(
            problem_map_df,
            original_df
        )
    )

    timings[
        "Report generation"
    ] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 10. REVIEW DATASET
    # ========================================================

    start = (
        time.perf_counter()
    )

    review_df = (
        create_review_dataset(
            original_df,
            cleaned_df,
            problem_map_df
        )
    )

    timings[
        "Review dataset generation"
    ] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # TOTAL RUNTIME
    # ========================================================

    timings[
        "Total Runtime"
    ] = (
        time.perf_counter()
        - total_start
    )

    # ========================================================
    # DISCOVERY SNAPSHOT
    # ========================================================

    result = {

        "original_rows":
            len(
                original_df
            ),

        "cleaned_rows":
            len(
                cleaned_df
            ),

        "unresolved_issues":
            len(
                unresolved_issues
            ),

        "problem_map_rows":
            len(
                problem_map_df
            ),

        "review_records":
            len(
                review_df
            ),

        "cleaning_score":
            cleaning_score,

        "validation_score":
            validation_score,

        "report_rows":
            len(
                report
            ),

        "records_affected_total":
            (
                int(
                    report[
                        "Records Affected"
                    ].sum()
                )

                if not report.empty

                else 0
            )
    }

    # ========================================================
    # PRINT TIMINGS
    # ========================================================

    stage_names = [

        "Load CSV",

        "Profiling",

        "Cleaning",

        "Unresolved issue detection",

        "Validation",

        "Score calculation",

        "Problem map generation",

        "Report generation",

        "Review dataset generation",

        "Total Runtime"
    ]

    for stage in stage_names:

        print(
            f"{stage:<30}"
            f"{fmt(timings[stage]):>8} sec"
        )

    print(
        "Snapshot:",
        result
    )

    return (
        timings,
        result
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n=============================================="
    )

    print(
        " CSV DATA GUARD - 250K DISCOVERY BENCHMARK"
    )

    print(
        "=============================================="
    )

    print(
        "Dataset:",
        FILE_PATH
    )

    print(
        "Runs:",
        RUNS
    )

    all_timings = []

    all_results = []

    # ========================================================
    # RUN BENCHMARK
    # ========================================================

    for run_number in range(
        1,
        RUNS + 1
    ):

        (
            timings,
            result
        ) = run_once(
            run_number
        )

        all_timings.append(
            timings
        )

        all_results.append(
            result
        )

    # ========================================================
    # CHECK SNAPSHOT CONSISTENCY
    # ========================================================

    first_result = (
        all_results[
            0
        ]
    )

    consistent = all(
        result == first_result
        for result
        in all_results
    )

    # ========================================================
    # PRINT SNAPSHOT
    # ========================================================

    print(
        "\n=============================================="
    )

    print(
        " 250K DISCOVERY SNAPSHOT"
    )

    print(
        "=============================================="
    )

    for (
        key,
        value
    ) in first_result.items():

        print(
            f"{key}: {value}"
        )

    print(
        "\nSnapshot Consistency:",
        (
            "PASS"
            if consistent
            else "FAIL"
        )
    )

    # ========================================================
    # MEDIAN RESULTS
    # ========================================================

    print(
        "\n=============================================="
    )

    print(
        " MEDIAN BENCHMARK RESULTS"
    )

    print(
        "=============================================="
    )

    stage_names = [

        "Load CSV",

        "Profiling",

        "Cleaning",

        "Unresolved issue detection",

        "Validation",

        "Score calculation",

        "Problem map generation",

        "Report generation",

        "Review dataset generation",

        "Total Runtime"
    ]

    for stage in stage_names:

        values = [

            run[
                stage
            ]

            for run
            in all_timings
        ]

        print(
            f"{stage:<30}"
            f"{median(values):>8.3f} sec"
        )

    # ========================================================
    # THROUGHPUT
    # ========================================================

    total_values = [

        run[
            "Total Runtime"
        ]

        for run
        in all_timings
    ]

    median_total = (
        median(
            total_values
        )
    )

    print(
        "\nMedian Total Runtime:",
        f"{median_total:.3f} sec"
    )

    print(
        "Median Rows / Second:",
        round(
            EXPECTED_ROWS
            / median_total,
            2
        )
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()

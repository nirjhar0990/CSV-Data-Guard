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

FILE_PATH = "data/messy_retail_data_250K.csv"
RUNS = 5

EXPECTED = {
    "original_rows": 250000,
    "cleaned_rows": 226234,
    "unresolved_issues": 69200,
    "problem_map_rows": 521978,
    "review_records": 179698,
    "validation_score": 10.18
}


# ============================================================
# HELPERS
# ============================================================

def median(values):
    return statistics.median(values)


def fmt(seconds):
    return f"{seconds:.3f}"


def run_once(run_number):

    gc.collect()

    timings = {}

    print(
        f"\n===== RUN {run_number}/{RUNS} =====",
        flush=True
    )

    total_start = time.perf_counter()

    # ========================================================
    # 1. LOAD CSV
    # ========================================================

    start = time.perf_counter()

    raw_df = load_csv(
        FILE_PATH
    )

    timings["Load CSV"] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 2. PROFILE
    # ========================================================

    start = time.perf_counter()

    profile = profile_data(
        raw_df
    )

    timings["Profiling"] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 3. ADD RECORD_ID
    # ========================================================

    original_df = raw_df.copy()

    original_df.insert(
        0,
        "Record_ID",
        range(
            1,
            len(original_df) + 1
        )
    )

    # ========================================================
    # 4. CLEAN
    # ========================================================

    start = time.perf_counter()

    (
        cleaned_df,
        cleaning_checks
    ) = clean_data(
        original_df
    )

    timings["Cleaning"] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 5. UNRESOLVED CLEANING ISSUES
    # ========================================================

    start = time.perf_counter()

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
    # 6. VALIDATE
    # ========================================================

    start = time.perf_counter()

    validation_result = (
        validate_data(
            cleaned_df
        )
    )

    timings["Validation"] = (
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

    start = time.perf_counter()

    initial_unresolved_count = len(
        unresolved_issues
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

    timings["Score calculation"] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 8. PROBLEM MAP
    # ========================================================

    start = time.perf_counter()

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

    start = time.perf_counter()

    report = (
        create_validation_report(
            problem_map_df,
            original_df
        )
    )

    timings["Report generation"] = (
        time.perf_counter()
        - start
    )

    # ========================================================
    # 10. REVIEW
    # ========================================================

    start = time.perf_counter()

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
    # TOTAL
    # ========================================================

    timings["Total Runtime"] = (
        time.perf_counter()
        - total_start
    )

    result = {
        "original_rows":
            len(original_df),

        "cleaned_rows":
            len(cleaned_df),

        "unresolved_issues":
            len(unresolved_issues),

        "problem_map_rows":
            len(problem_map_df),

        "review_records":
            len(review_df),

        "cleaning_score":
            cleaning_score,

        "validation_score":
            validation_score
    }

    print(
        f"Load CSV:                    {fmt(timings['Load CSV'])} sec"
    )

    print(
        f"Profiling:                   {fmt(timings['Profiling'])} sec"
    )

    print(
        f"Cleaning:                    {fmt(timings['Cleaning'])} sec"
    )

    print(
        "Unresolved issue detection: "
        f"{fmt(timings['Unresolved issue detection'])} sec"
    )

    print(
        f"Validation:                  {fmt(timings['Validation'])} sec"
    )

    print(
        f"Score calculation:           {fmt(timings['Score calculation'])} sec"
    )

    print(
        "Problem map generation:     "
        f"{fmt(timings['Problem map generation'])} sec"
    )

    print(
        f"Report generation:           {fmt(timings['Report generation'])} sec"
    )

    print(
        "Review dataset generation:  "
        f"{fmt(timings['Review dataset generation'])} sec"
    )

    print(
        f"Total Runtime:               {fmt(timings['Total Runtime'])} sec"
    )

    return timings, result


# ============================================================
# CORRECTNESS CHECK
# ============================================================

def validate_result(
    result,
    run_number
):

    problems = []

    for key in [
        "original_rows",
        "cleaned_rows",
        "unresolved_issues",
        "problem_map_rows",
        "review_records"
    ]:

        if (
            result[key]
            != EXPECTED[key]
        ):

            problems.append(
                f"{key}: "
                f"{result[key]} "
                f"(expected {EXPECTED[key]})"
            )

    if abs(
        result["validation_score"]
        - EXPECTED["validation_score"]
    ) > 0.001:

        problems.append(
            "validation_score: "
            f"{result['validation_score']} "
            f"(expected "
            f"{EXPECTED['validation_score']})"
        )

    if problems:

        print(
            f"\nWARNING: RUN {run_number} "
            "FAILED CORRECTNESS CHECK"
        )

        for problem in problems:
            print(
                "  -",
                problem
            )

        return False

    print(
        f"Correctness Check: PASS"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        "=============================================="
    )

    print(
        " CSV DATA GUARD - 5 RUN MEDIAN BENCHMARK"
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
    all_passed = True

    for run_number in range(
        1,
        RUNS + 1
    ):

        timings, result = (
            run_once(
                run_number
            )
        )

        passed = (
            validate_result(
                result,
                run_number
            )
        )

        if not passed:
            all_passed = False

        all_timings.append(
            timings
        )

        all_results.append(
            result
        )

    # ========================================================
    # MEDIAN SUMMARY
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

    print(
        "\n"
        "=============================================="
    )

    print(
        " MEDIAN BENCHMARK RESULTS"
    )

    print(
        "=============================================="
    )

    for stage in stage_names:

        values = [
            run[
                stage
            ]
            for run in all_timings
        ]

        print(
            f"{stage:<30}"
            f"{median(values):>8.3f} sec"
        )

    total_values = [
        run[
            "Total Runtime"
        ]
        for run in all_timings
    ]

    median_total = median(
        total_values
    )

    best_total = min(
        total_values
    )

    worst_total = max(
        total_values
    )

    print(
        "\n"
        "=============================================="
    )

    print(
        " TOTAL RUNTIME SUMMARY"
    )

    print(
        "=============================================="
    )

    print(
        f"Median Total Runtime: {median_total:.3f} sec"
    )

    print(
        f"Best Total Runtime:   {best_total:.3f} sec"
    )

    print(
        f"Worst Total Runtime:  {worst_total:.3f} sec"
    )

    print(
        "Median Rows / Second:",
        round(
            EXPECTED[
                "original_rows"
            ]
            / median_total,
            2
        )
    )

    # ========================================================
    # INDIVIDUAL RUN TOTALS
    # ========================================================

    print(
        "\n"
        "=============================================="
    )

    print(
        " INDIVIDUAL RUN TOTALS"
    )

    print(
        "=============================================="
    )

    for index, value in enumerate(
        total_values,
        start=1
    ):

        print(
            f"Run {index}: "
            f"{value:.3f} sec"
        )

    # ========================================================
    # CORRECTNESS SUMMARY
    # ========================================================

    print(
        "\n"
        "=============================================="
    )

    print(
        " CORRECTNESS SUMMARY"
    )

    print(
        "=============================================="
    )

    if all_passed:

        print(
            "All 5 runs matched the locked 250K baseline."
        )

    else:

        print(
            "One or more runs did NOT match the locked baseline."
        )

    print(
        "\nExpected baseline:"
    )

    print(
        "Original Rows:",
        EXPECTED[
            "original_rows"
        ]
    )

    print(
        "Cleaned Rows:",
        EXPECTED[
            "cleaned_rows"
        ]
    )

    print(
        "Unresolved Issues:",
        EXPECTED[
            "unresolved_issues"
        ]
    )

    print(
        "Problem Map Rows:",
        EXPECTED[
            "problem_map_rows"
        ]
    )

    print(
        "Review Records:",
        EXPECTED[
            "review_records"
        ]
    )

    print(
        "Validation Score:",
        EXPECTED[
            "validation_score"
        ]
    )


if __name__ == "__main__":

    main()

import gc
import statistics
import time

from pipeline.profiler import load_csv
from pipeline.cleaner import clean_data
from pipeline.validator import (
    validate_data,
    find_unresolved_cleaning_issues
)
from pipeline.problem_map import create_problem_map


# ============================================================
# CONFIGURATION
# ============================================================

FILE_PATH = "data/messy_retail_data_250K.csv"
RUNS = 5

EXPECTED = {
    "original_rows": 250000,
    "cleaned_rows": 226234,
    "unresolved_issues": 69200,
    "problem_map_rows": 521978
}


# ============================================================
# HELPERS
# ============================================================

def median(values):
    return statistics.median(values)


def prepare_inputs():
    """
    Prepare all upstream objects once so the benchmark measures
    create_problem_map() itself rather than the full pipeline.
    """

    print(
        "\nPreparing problem-map benchmark inputs...",
        flush=True
    )

    raw_df = load_csv(
        FILE_PATH
    )

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

    cleaned_df, _ = clean_data(
        original_df
    )

    unresolved_issues = (
        find_unresolved_cleaning_issues(
            original_df,
            cleaned_df
        )
    )

    validation_result = (
        validate_data(
            cleaned_df
        )
    )

    failure_cases = (
        validation_result[
            "failure_cases"
        ]
    )

    snapshot = {
        "original_rows":
            len(original_df),

        "cleaned_rows":
            len(cleaned_df),

        "unresolved_issues":
            len(unresolved_issues)
    }

    return (
        original_df,
        failure_cases,
        unresolved_issues,
        snapshot
    )


def validate_preparation(snapshot):

    problems = []

    for key in [
        "original_rows",
        "cleaned_rows",
        "unresolved_issues"
    ]:

        actual = snapshot[key]
        expected = EXPECTED[key]

        if actual != expected:

            problems.append(
                f"{key}: "
                f"{actual} "
                f"(expected {expected})"
            )

    if problems:

        print(
            "\nPREPARATION CORRECTNESS CHECK: FAIL"
        )

        for problem in problems:
            print(
                "  -",
                problem
            )

        return False

    print(
        "Preparation Correctness Check: PASS"
    )

    return True


def run_once(
    run_number,
    original_df,
    failure_cases,
    unresolved_issues
):

    gc.collect()

    print(
        f"\n===== PROBLEM MAP RUN {run_number}/{RUNS} =====",
        flush=True
    )

    start = time.perf_counter()

    problem_map_df = (
        create_problem_map(
            original_df,
            failure_cases,
            unresolved_issues
        )
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    result = {
        "problem_map_rows":
            len(problem_map_df),

        "columns":
            problem_map_df.columns.tolist(),

        "reportable_true":
            (
                int(
                    problem_map_df[
                        "reportable"
                    ]
                    .fillna(False)
                    .sum()
                )
                if "reportable"
                in problem_map_df.columns
                else None
            ),

        "reviewable_true":
            (
                int(
                    problem_map_df[
                        "reviewable"
                    ]
                    .fillna(False)
                    .sum()
                )
                if "reviewable"
                in problem_map_df.columns
                else None
            ),

        "source_counts":
            (
                problem_map_df[
                    "source"
                ]
                .value_counts(
                    dropna=False
                )
                .to_dict()
                if "source"
                in problem_map_df.columns
                else {}
            )
    }

    print(
        f"create_problem_map: {elapsed:.3f} sec"
    )

    print(
        f"Problem Map Rows:   {len(problem_map_df)}"
    )

    return (
        elapsed,
        result
    )


def validate_result(
    result,
    run_number
):

    problems = []

    if (
        result[
            "problem_map_rows"
        ]
        != EXPECTED[
            "problem_map_rows"
        ]
    ):

        problems.append(
            "problem_map_rows: "
            f"{result['problem_map_rows']} "
            f"(expected {EXPECTED['problem_map_rows']})"
        )

    required_columns = {
        "index",
        "column",
        "validation_error",
        "how_to_fix",
        "source",
        "reportable",
        "reviewable"
    }

    missing_columns = (
        required_columns
        - set(
            result[
                "columns"
            ]
        )
    )

    if missing_columns:

        problems.append(
            "missing columns: "
            f"{sorted(missing_columns)}"
        )

    if problems:

        print(
            f"Correctness Check: FAIL "
            f"(run {run_number})"
        )

        for problem in problems:
            print(
                "  -",
                problem
            )

        return False

    print(
        "Correctness Check: PASS"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        "======================================================"
    )

    print(
        " CSV DATA GUARD - PROBLEM MAP 5 RUN MEDIAN BENCHMARK"
    )

    print(
        "======================================================"
    )

    print(
        "Dataset:",
        FILE_PATH
    )

    print(
        "Runs:",
        RUNS
    )

    (
        original_df,
        failure_cases,
        unresolved_issues,
        snapshot
    ) = prepare_inputs()

    if not validate_preparation(
        snapshot
    ):

        print(
            "\nBenchmark stopped because "
            "upstream inputs do not match "
            "the locked 250K baseline."
        )

        return

    times = []
    all_passed = True
    last_result = None

    for run_number in range(
        1,
        RUNS + 1
    ):

        elapsed, result = (
            run_once(
                run_number,
                original_df,
                failure_cases,
                unresolved_issues
            )
        )

        passed = validate_result(
            result,
            run_number
        )

        if not passed:
            all_passed = False

        times.append(
            elapsed
        )

        last_result = result

    median_time = median(
        times
    )

    print(
        "\n"
        "======================================================"
    )

    print(
        " PROBLEM MAP BENCHMARK RESULTS"
    )

    print(
        "======================================================"
    )

    for index, elapsed in enumerate(
        times,
        start=1
    ):

        print(
            f"Run {index}: "
            f"{elapsed:.3f} sec"
        )

    print()

    print(
        f"Median Problem Map Time: "
        f"{median_time:.3f} sec"
    )

    print(
        f"Best Problem Map Time:   "
        f"{min(times):.3f} sec"
    )

    print(
        f"Worst Problem Map Time:  "
        f"{max(times):.3f} sec"
    )

    print(
        "\n"
        "======================================================"
    )

    print(
        " PROBLEM MAP OUTPUT SUMMARY"
    )

    print(
        "======================================================"
    )

    print(
        "Problem Map Rows:",
        last_result[
            "problem_map_rows"
        ]
    )

    print(
        "Columns:",
        last_result[
            "columns"
        ]
    )

    print(
        "Reportable=True:",
        last_result[
            "reportable_true"
        ]
    )

    print(
        "Reviewable=True:",
        last_result[
            "reviewable_true"
        ]
    )

    print(
        "Source Counts:",
        last_result[
            "source_counts"
        ]
    )

    print(
        "\n"
        "======================================================"
    )

    print(
        " CORRECTNESS SUMMARY"
    )

    print(
        "======================================================"
    )

    if all_passed:

        print(
            "All 5 problem-map runs matched "
            "the locked 250K baseline."
        )

    else:

        print(
            "One or more problem-map runs "
            "did NOT match the baseline."
        )


if __name__ == "__main__":
    main()

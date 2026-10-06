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
from pipeline.review import create_review_dataset


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
    "review_records": 179698
}


# ============================================================
# HELPERS
# ============================================================

def median(values):
    return statistics.median(values)


def prepare_inputs():
    """
    Prepare all upstream data once so the benchmark measures
    create_review_dataset() itself rather than the whole pipeline.
    """

    print("\nPreparing review benchmark inputs...", flush=True)

    raw_df = load_csv(FILE_PATH)

    original_df = raw_df.copy()

    original_df.insert(
        0,
        "Record_ID",
        range(1, len(original_df) + 1)
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

    problem_map_df = (
        create_problem_map(
            original_df,
            failure_cases,
            unresolved_issues
        )
    )

    preparation_snapshot = {
        "original_rows":
            len(original_df),

        "cleaned_rows":
            len(cleaned_df),

        "unresolved_issues":
            len(unresolved_issues),

        "problem_map_rows":
            len(problem_map_df)
    }

    return (
        original_df,
        cleaned_df,
        problem_map_df,
        preparation_snapshot
    )


def validate_preparation(snapshot):
    problems = []

    for key in [
        "original_rows",
        "cleaned_rows",
        "unresolved_issues",
        "problem_map_rows"
    ]:
        actual = snapshot[key]
        expected = EXPECTED[key]

        if actual != expected:
            problems.append(
                f"{key}: {actual} "
                f"(expected {expected})"
            )

    if problems:
        print("\nPREPARATION CORRECTNESS CHECK: FAIL")
        for problem in problems:
            print("  -", problem)
        return False

    print("Preparation Correctness Check: PASS")
    return True


def run_once(
    run_number,
    original_df,
    cleaned_df,
    problem_map_df
):
    gc.collect()

    print(
        f"\n===== REVIEW RUN {run_number}/{RUNS} =====",
        flush=True
    )

    start = time.perf_counter()

    review_df = (
        create_review_dataset(
            original_df,
            cleaned_df,
            problem_map_df
        )
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    result = {
        "review_records":
            len(review_df),

        "columns":
            review_df.columns.tolist(),

        "record_id_unique":
            (
                review_df["Record_ID"].is_unique
                if "Record_ID" in review_df.columns
                else False
            ),

        "has_record_id":
            "Record_ID" in review_df.columns,

        "has_order_id":
            "Order_ID" in review_df.columns
    }

    print(
        f"create_review_dataset: {elapsed:.3f} sec"
    )

    print(
        f"Review Records:        {len(review_df)}"
    )

    return elapsed, result


def validate_review_result(
    result,
    run_number
):
    problems = []

    if (
        result["review_records"]
        != EXPECTED["review_records"]
    ):
        problems.append(
            "review_records: "
            f"{result['review_records']} "
            f"(expected {EXPECTED['review_records']})"
        )

    if not result["has_record_id"]:
        problems.append(
            "Record_ID column missing"
        )

    if not result["has_order_id"]:
        problems.append(
            "Order_ID column missing"
        )

    if not result["record_id_unique"]:
        problems.append(
            "Record_ID values are not unique "
            "inside review dataset"
        )

    if problems:
        print(
            f"Correctness Check: FAIL "
            f"(run {run_number})"
        )

        for problem in problems:
            print("  -", problem)

        return False

    print("Correctness Check: PASS")
    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        "================================================="
    )

    print(
        " CSV DATA GUARD - REVIEW 5 RUN MEDIAN BENCHMARK"
    )

    print(
        "================================================="
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
        cleaned_df,
        problem_map_df,
        preparation_snapshot
    ) = prepare_inputs()

    preparation_ok = (
        validate_preparation(
            preparation_snapshot
        )
    )

    if not preparation_ok:
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
                cleaned_df,
                problem_map_df
            )
        )

        passed = validate_review_result(
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
        "================================================="
    )

    print(
        " REVIEW BENCHMARK RESULTS"
    )

    print(
        "================================================="
    )

    for index, elapsed in enumerate(
        times,
        start=1
    ):
        print(
            f"Run {index}: {elapsed:.3f} sec"
        )

    print()

    print(
        f"Median Review Time: "
        f"{median_time:.3f} sec"
    )

    print(
        f"Best Review Time:   "
        f"{min(times):.3f} sec"
    )

    print(
        f"Worst Review Time:  "
        f"{max(times):.3f} sec"
    )

    print(
        "\n"
        "================================================="
    )

    print(
        " REVIEW OUTPUT SUMMARY"
    )

    print(
        "================================================="
    )

    print(
        "Review Records:",
        last_result["review_records"]
    )

    print(
        "Review Columns:",
        last_result["columns"]
    )

    print(
        "Record_ID Unique:",
        last_result["record_id_unique"]
    )

    print(
        "\n"
        "================================================="
    )

    print(
        " CORRECTNESS SUMMARY"
    )

    print(
        "================================================="
    )

    if all_passed:
        print(
            "All 5 review runs matched "
            "the locked 250K review baseline."
        )
    else:
        print(
            "One or more review runs "
            "did NOT match the baseline."
        )


if __name__ == "__main__":
    main()

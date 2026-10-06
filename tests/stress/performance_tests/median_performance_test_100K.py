import gc
import statistics
import time

from pipeline.profiler import load_csv, profile_data
from pipeline.cleaner import clean_data
from pipeline.validator import (
    validate_data,
    calculate_validation_score,
    calculate_cleaning_score,
    find_unresolved_cleaning_issues
)
from pipeline.problem_map import create_problem_map
from pipeline.reporting import create_validation_report
from pipeline.review import create_review_dataset

FILE_PATH = "data/messy_retail_data_100K.csv"
RUNS = 5

EXPECTED = {
    "original_rows": 100000,
    "cleaned_rows": 89710,
    "unresolved_issues": 26657,
    "problem_map_rows": 156882,
    "review_records": 71374,
    "validation_score": 22.86,
    "report_rows": 18,
    "records_affected_total": 138811
}


def median(values):
    return statistics.median(values)


def fmt(seconds):
    return f"{seconds:.3f}"


def validate_expected_config():
    missing = [
        key
        for key, value in EXPECTED.items()
        if value is None
    ]

    if missing:
        print("\nLOCKED BASELINE NOT INITIALIZED.")
        print(
            "Run median_performance_discovery_100K.py first, "
            "then paste its exact snapshot into EXPECTED."
        )
        print("Missing keys:", ", ".join(missing))
        return False

    return True


def run_once(run_number):
    gc.collect()
    timings = {}
    print(f"\n===== RUN {run_number}/{RUNS} =====", flush=True)
    total_start = time.perf_counter()

    start = time.perf_counter()
    raw_df = load_csv(FILE_PATH)
    timings["Load CSV"] = time.perf_counter() - start

    start = time.perf_counter()
    profile = profile_data(raw_df)
    timings["Profiling"] = time.perf_counter() - start

    original_df = raw_df.copy()
    original_df.insert(0, "Record_ID", range(1, len(original_df) + 1))

    start = time.perf_counter()
    cleaned_df, cleaning_checks = clean_data(original_df)
    timings["Cleaning"] = time.perf_counter() - start

    start = time.perf_counter()
    unresolved_issues = find_unresolved_cleaning_issues(
        original_df,
        cleaned_df
    )
    timings["Unresolved issue detection"] = time.perf_counter() - start

    start = time.perf_counter()
    validation_result = validate_data(cleaned_df)
    timings["Validation"] = time.perf_counter() - start
    failure_cases = validation_result["failure_cases"]

    start = time.perf_counter()
    initial_unresolved_count = len(unresolved_issues)
    cleaning_score = calculate_cleaning_score(
        initial_unresolved_count,
        initial_unresolved_count
    )
    validation_score = calculate_validation_score(
        cleaned_df,
        failure_cases
    )
    timings["Score calculation"] = time.perf_counter() - start

    start = time.perf_counter()
    problem_map_df = create_problem_map(
        original_df,
        failure_cases,
        unresolved_issues
    )
    timings["Problem map generation"] = time.perf_counter() - start

    start = time.perf_counter()
    report = create_validation_report(
        problem_map_df,
        original_df
    )
    timings["Report generation"] = time.perf_counter() - start

    start = time.perf_counter()
    review_df = create_review_dataset(
        original_df,
        cleaned_df,
        problem_map_df
    )
    timings["Review dataset generation"] = time.perf_counter() - start

    timings["Total Runtime"] = time.perf_counter() - total_start

    result = {
        "original_rows": len(original_df),
        "cleaned_rows": len(cleaned_df),
        "unresolved_issues": len(unresolved_issues),
        "problem_map_rows": len(problem_map_df),
        "review_records": len(review_df),
        "validation_score": validation_score,
        "report_rows": len(report),
        "records_affected_total": (
            int(report["Records Affected"].sum())
            if not report.empty
            else 0
        )
    }

    for stage in [
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
    ]:
        print(f"{stage:<30}{fmt(timings[stage]):>8} sec")

    return timings, result


def validate_result(result, run_number):
    problems = []

    for key, expected in EXPECTED.items():
        actual = result[key]

        if key == "validation_score":
            if round(float(actual), 2) != round(float(expected), 2):
                problems.append(
                    f"{key}: {actual} (expected {expected})"
                )
        elif actual != expected:
            problems.append(
                f"{key}: {actual} (expected {expected})"
            )

    if problems:
        print(f"Correctness Check: FAIL (run {run_number})")
        for problem in problems:
            print("  -", problem)
        return False

    print("Correctness Check: PASS")
    return True


def main():
    print("\n==============================================")
    print(" CSV DATA GUARD - 100K LOCKED 5 RUN BENCHMARK")
    print("==============================================")

    if not validate_expected_config():
        return

    print("Dataset:", FILE_PATH)
    print("Runs:", RUNS)

    all_timings = []
    all_passed = True

    for run_number in range(1, RUNS + 1):
        timings, result = run_once(run_number)

        if not validate_result(result, run_number):
            all_passed = False

        all_timings.append(timings)

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

    print("\n==============================================")
    print(" MEDIAN BENCHMARK RESULTS")
    print("==============================================")

    for stage in stage_names:
        values = [run[stage] for run in all_timings]
        print(f"{stage:<30}{median(values):>8.3f} sec")

    total_values = [run["Total Runtime"] for run in all_timings]
    median_total = median(total_values)

    print("\n==============================================")
    print(" TOTAL RUNTIME SUMMARY")
    print("==============================================")

    print(f"Median Total Runtime: {median_total:.3f} sec")
    print(f"Best Total Runtime:   {min(total_values):.3f} sec")
    print(f"Worst Total Runtime:  {max(total_values):.3f} sec")
    print(
        "Median Rows / Second:",
        round(EXPECTED["original_rows"] / median_total, 2)
    )

    print("\n==============================================")
    print(" CORRECTNESS SUMMARY")
    print("==============================================")

    if all_passed:
        print("All 5 runs matched the locked 100K baseline.")
    else:
        print(
            "One or more runs did NOT match "
            "the locked 100K baseline."
        )


if __name__ == "__main__":
    main()

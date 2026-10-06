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
from pipeline.reporting import create_validation_report


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
    "reportable_true": 497164,
    "report_rows": 19,
    "records_affected_total": 475027
}

EXPECTED_COLUMNS = [
    "Field",
    "Validation Error",
    "Records Affected",
    "Affected Order IDs",
    "How to Fix"
]


# ============================================================
# HELPERS
# ============================================================

def median(values):
    return statistics.median(values)


def prepare_inputs():
    """
    Prepare all upstream objects once so the benchmark measures
    create_validation_report() itself rather than the full pipeline.
    """

    print(
        "\nPreparing report benchmark inputs...",
        flush=True
    )

    raw_df = load_csv(
        FILE_PATH
    )

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

    validation_result = validate_data(
        cleaned_df
    )

    failure_cases = validation_result[
        "failure_cases"
    ]

    problem_map_df = create_problem_map(
        original_df,
        failure_cases,
        unresolved_issues
    )

    snapshot = {
        "original_rows":
            len(original_df),

        "cleaned_rows":
            len(cleaned_df),

        "unresolved_issues":
            len(unresolved_issues),

        "problem_map_rows":
            len(problem_map_df),

        "reportable_true":
            int(
                problem_map_df[
                    "reportable"
                ]
                .fillna(False)
                .sum()
            )
    }

    return (
        original_df,
        problem_map_df,
        snapshot
    )


def validate_preparation(snapshot):
    problems = []

    for key in [
        "original_rows",
        "cleaned_rows",
        "unresolved_issues",
        "problem_map_rows",
        "reportable_true"
    ]:
        actual = snapshot[key]
        expected = EXPECTED[key]

        if actual != expected:
            problems.append(
                f"{key}: {actual} "
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
    problem_map_df
):
    gc.collect()

    print(
        f"\n===== REPORT RUN {run_number}/{RUNS} =====",
        flush=True
    )

    start = time.perf_counter()

    report_df = create_validation_report(
        problem_map_df,
        original_df
    )

    elapsed = (
        time.perf_counter()
        - start
    )

    records_affected_total = (
        int(
            report_df[
                "Records Affected"
            ].sum()
        )
        if (
            "Records Affected"
            in report_df.columns
            and not report_df.empty
        )
        else 0
    )

    result = {
        "report_rows":
            len(report_df),

        "columns":
            report_df.columns.tolist(),

        "records_affected_total":
            records_affected_total
    }

    print(
        f"create_validation_report: {elapsed:.3f} sec"
    )

    print(
        f"Report Rows:              {len(report_df)}"
    )

    print(
        f"Records Affected Total:   {records_affected_total}"
    )

    return (
        elapsed,
        report_df,
        result
    )


def validate_report_result(
    result,
    run_number
):
    problems = []

    if (
        result[
            "columns"
        ]
        != EXPECTED_COLUMNS
    ):
        problems.append(
            "report columns differ from expected structure: "
            f"{result['columns']}"
        )

    if (
        result[
            "report_rows"
        ]
        != EXPECTED[
            "report_rows"
        ]
    ):
        problems.append(
            "report_rows: "
            f"{result['report_rows']} "
            f"(expected {EXPECTED['report_rows']})"
        )

    if (
        result[
            "records_affected_total"
        ]
        != EXPECTED[
            "records_affected_total"
        ]
    ):
        problems.append(
            "records_affected_total: "
            f"{result['records_affected_total']} "
            f"(expected {EXPECTED['records_affected_total']})"
        )

    if problems:
        print(
            f"Locked Baseline Check: FAIL "
            f"(run {run_number})"
        )

        for problem in problems:
            print(
                "  -",
                problem
            )

        return False

    print(
        "Locked Baseline Check: PASS"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        "==================================================="
    )

    print(
        " CSV DATA GUARD - REPORT 5 RUN MEDIAN BENCHMARK"
    )

    print(
        "==================================================="
    )

    print(
        "Dataset:",
        FILE_PATH
    )

    print(
        "Runs:",
        RUNS
    )

    print(
        "Locked Report Baseline:",
        f"{EXPECTED['report_rows']} rows,",
        f"{EXPECTED['records_affected_total']} affected records"
    )

    (
        original_df,
        problem_map_df,
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
    baseline_report = None
    last_result = None

    for run_number in range(
        1,
        RUNS + 1
    ):

        (
            elapsed,
            report_df,
            result
        ) = run_once(
            run_number,
            original_df,
            problem_map_df
        )

        locked_ok = (
            validate_report_result(
                result,
                run_number
            )
        )

        if not locked_ok:
            all_passed = False

        if baseline_report is None:

            baseline_report = (
                report_df.copy(
                    deep=True
                )
            )

            print(
                "Run-to-Run Content Check: BASELINE CAPTURED"
            )

        else:

            same_content = (
                report_df.equals(
                    baseline_report
                )
            )

            if same_content:
                print(
                    "Run-to-Run Content Check: PASS"
                )
            else:
                print(
                    "Run-to-Run Content Check: FAIL"
                )
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
        "==================================================="
    )

    print(
        " REPORT BENCHMARK RESULTS"
    )

    print(
        "==================================================="
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
        f"Median Report Time: "
        f"{median_time:.3f} sec"
    )

    print(
        f"Best Report Time:   "
        f"{min(times):.3f} sec"
    )

    print(
        f"Worst Report Time:  "
        f"{max(times):.3f} sec"
    )

    print(
        "\n"
        "==================================================="
    )

    print(
        " REPORT OUTPUT SUMMARY"
    )

    print(
        "==================================================="
    )

    print(
        "Report Rows:",
        last_result[
            "report_rows"
        ]
    )

    print(
        "Report Columns:",
        last_result[
            "columns"
        ]
    )

    print(
        "Total Records Affected:",
        last_result[
            "records_affected_total"
        ]
    )

    print(
        "\n"
        "==================================================="
    )

    print(
        " CORRECTNESS SUMMARY"
    )

    print(
        "==================================================="
    )

    if all_passed:

        print(
            "All 5 report runs matched the locked "
            "250K report baseline and each other."
        )

    else:

        print(
            "One or more report runs FAILED the locked "
            "250K report baseline or run-to-run content check."
        )


if __name__ == "__main__":
    main()

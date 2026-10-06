import gc
import statistics
import time

from pipeline.profiler import (
    load_csv,
    profile_data,
    profile_missing_values,
    profile_categorical_values,
    profile_customer_names,
    profile_emails,
    profile_customer_age,
    profile_customer_rating,
    profile_order_dates,
    profile_order_ids,
    profile_order_id_duplicates,
    profile_numeric_columns,
    profile_numeric_ranges,
    create_issue_summary
)


# ============================================================
# CONFIGURATION
# ============================================================

FILE_PATH = "data/messy_retail_data_250K.csv"
RUNS = 5

EXPECTED = {
    "duplicate_rows": 23766,
    "invalid_names": 10919,
    "invalid_email_syntax": 4710,
    "invalid_email_domain": 10806,
    "invalid_ages": 10972,
    "invalid_ratings": 11235,
    "invalid_dates": 3712,
    "non_standard_dates": 213854,
    "invalid_order_ids": 139411
}


# ============================================================
# HELPERS
# ============================================================

def median(values):
    return statistics.median(values)


def timed_call(func, *args):
    start = time.perf_counter()
    result = func(*args)
    elapsed = time.perf_counter() - start
    return result, elapsed


# ============================================================
# SINGLE RUN
# ============================================================

def run_once(run_number):

    gc.collect()

    print(
        f"\n===== PROFILER RUN {run_number}/{RUNS} =====",
        flush=True
    )

    # --------------------------------------------------------
    # LOAD
    # --------------------------------------------------------

    start = time.perf_counter()
    df = load_csv(FILE_PATH)
    load_time = time.perf_counter() - start

    timings = {}

    # --------------------------------------------------------
    # PROFILE HELPERS
    # --------------------------------------------------------

    missing_value_profile, timings[
        "profile_missing_values"
    ] = timed_call(
        profile_missing_values,
        df
    )

    categorical_profile, timings[
        "profile_categorical_values"
    ] = timed_call(
        profile_categorical_values,
        df
    )

    customer_name_profile, timings[
        "profile_customer_names"
    ] = timed_call(
        profile_customer_names,
        df
    )

    email_profile, timings[
        "profile_emails"
    ] = timed_call(
        profile_emails,
        df
    )

    age_profile, timings[
        "profile_customer_age"
    ] = timed_call(
        profile_customer_age,
        df
    )

    rating_profile, timings[
        "profile_customer_rating"
    ] = timed_call(
        profile_customer_rating,
        df
    )

    order_date_profile, timings[
        "profile_order_dates"
    ] = timed_call(
        profile_order_dates,
        df
    )

    order_id_profile, timings[
        "profile_order_ids"
    ] = timed_call(
        profile_order_ids,
        df
    )

    order_id_duplicate_profile, timings[
        "profile_order_id_duplicates"
    ] = timed_call(
        profile_order_id_duplicates,
        df
    )

    numeric_profile, timings[
        "profile_numeric_columns"
    ] = timed_call(
        profile_numeric_columns,
        df
    )

    numeric_range_profile, timings[
        "profile_numeric_ranges"
    ] = timed_call(
        profile_numeric_ranges,
        df
    )

    partial_profile = {
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": df.columns.tolist(),
        "data_types": df.dtypes.astype(str).to_dict(),
        "missing_values": df.isna().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_value_profile": missing_value_profile,
        "categorical_profile": categorical_profile,
        "customer_name_profile": customer_name_profile,
        "email_profile": email_profile,
        "age_profile": age_profile,
        "rating_profile": rating_profile,
        "order_date_profile": order_date_profile,
        "order_id_profile": order_id_profile,
        "order_id_duplicate_profile": order_id_duplicate_profile,
        "numeric_profile": numeric_profile,
        "numeric_range_profile": numeric_range_profile,
    }

    issue_summary, timings[
        "create_issue_summary"
    ] = timed_call(
        create_issue_summary,
        partial_profile
    )

    helper_total = sum(
        timings.values()
    )

    # --------------------------------------------------------
    # FULL profile_data()
    # --------------------------------------------------------

    full_profile, profile_data_time = timed_call(
        profile_data,
        df
    )

    result = {
        "duplicate_rows":
            full_profile["duplicate_rows"],

        "invalid_names":
            full_profile[
                "customer_name_profile"
            ]["invalid_count"],

        "invalid_email_syntax":
            full_profile[
                "email_profile"
            ]["invalid_syntax_count"],

        "invalid_email_domain":
            full_profile[
                "email_profile"
            ]["invalid_domain_count"],

        "invalid_ages":
            full_profile[
                "age_profile"
            ]["invalid_count"],

        "invalid_ratings":
            full_profile[
                "rating_profile"
            ]["invalid_count"],

        "invalid_dates":
            full_profile[
                "order_date_profile"
            ]["invalid_count"],

        "non_standard_dates":
            full_profile[
                "order_date_profile"
            ]["non_standard_count"],

        "invalid_order_ids":
            full_profile[
                "order_id_profile"
            ]["invalid_count"],
    }

    print(
        f"{'load_csv':<32}{load_time:>8.3f} sec"
    )

    for name, elapsed in timings.items():
        print(
            f"{name:<32}{elapsed:>8.3f} sec"
        )

    print(
        f"{'helper total':<32}{helper_total:>8.3f} sec"
    )

    print(
        f"{'profile_data':<32}{profile_data_time:>8.3f} sec"
    )

    return {
        "load_time": load_time,
        "timings": timings,
        "helper_total": helper_total,
        "profile_data": profile_data_time,
        "result": result
    }


# ============================================================
# CORRECTNESS CHECK
# ============================================================

def validate_result(result, run_number):

    problems = []

    for key, expected in EXPECTED.items():

        actual = result[key]

        if actual != expected:

            problems.append(
                f"{key}: "
                f"{actual} "
                f"(expected {expected})"
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
        "Correctness Check: PASS"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "\n"
        "=================================================="
    )

    print(
        " CSV DATA GUARD - PROFILER 5 RUN MEDIAN BENCHMARK"
    )

    print(
        "=================================================="
    )

    print(
        "Dataset:",
        FILE_PATH
    )

    print(
        "Runs:",
        RUNS
    )

    all_runs = []
    all_passed = True

    for run_number in range(
        1,
        RUNS + 1
    ):

        run = run_once(
            run_number
        )

        passed = validate_result(
            run["result"],
            run_number
        )

        if not passed:
            all_passed = False

        all_runs.append(
            run
        )

    stage_names = [
        "profile_missing_values",
        "profile_categorical_values",
        "profile_customer_names",
        "profile_emails",
        "profile_customer_age",
        "profile_customer_rating",
        "profile_order_dates",
        "profile_order_ids",
        "profile_order_id_duplicates",
        "profile_numeric_columns",
        "profile_numeric_ranges",
        "create_issue_summary"
    ]

    print(
        "\n"
        "=================================================="
    )

    print(
        " MEDIAN PROFILER RESULTS"
    )

    print(
        "=================================================="
    )

    median_stage_times = {}

    for stage in stage_names:

        values = [
            run["timings"][stage]
            for run in all_runs
        ]

        stage_median = median(
            values
        )

        median_stage_times[
            stage
        ] = stage_median

        print(
            f"{stage:<32}"
            f"{stage_median:>8.3f} sec"
        )

    helper_totals = [
        run["helper_total"]
        for run in all_runs
    ]

    profile_data_values = [
        run["profile_data"]
        for run in all_runs
    ]

    load_values = [
        run["load_time"]
        for run in all_runs
    ]

    median_helper_total = median(
        helper_totals
    )

    median_profile_data = median(
        profile_data_values
    )

    median_load = median(
        load_values
    )

    print()

    print(
        f"{'Median load_csv':<32}"
        f"{median_load:>8.3f} sec"
    )

    print(
        f"{'Median helper total':<32}"
        f"{median_helper_total:>8.3f} sec"
    )

    print(
        f"{'Median profile_data':<32}"
        f"{median_profile_data:>8.3f} sec"
    )

    print(
        "\n"
        "=================================================="
    )

    print(
        " PROFILER HOTSPOT RANKING"
    )

    print(
        "=================================================="
    )

    sorted_stages = sorted(
        median_stage_times.items(),
        key=lambda item: item[1],
        reverse=True
    )

    stage_sum = sum(
        median_stage_times.values()
    )

    for name, elapsed in sorted_stages:

        share = (
            elapsed
            / stage_sum
            * 100
            if stage_sum
            else 0
        )

        print(
            f"{name:<32}"
            f"{elapsed:>8.3f} sec "
            f"({share:>5.1f}%)"
        )

    print(
        "\n"
        "=================================================="
    )

    print(
        " PROFILE_DATA RUN SUMMARY"
    )

    print(
        "=================================================="
    )

    for index, value in enumerate(
        profile_data_values,
        start=1
    ):

        print(
            f"Run {index}: "
            f"{value:.3f} sec"
        )

    print()

    print(
        f"Median profile_data: "
        f"{median_profile_data:.3f} sec"
    )

    print(
        f"Best profile_data:   "
        f"{min(profile_data_values):.3f} sec"
    )

    print(
        f"Worst profile_data:  "
        f"{max(profile_data_values):.3f} sec"
    )

    print(
        "\n"
        "=================================================="
    )

    print(
        " CORRECTNESS SUMMARY"
    )

    print(
        "=================================================="
    )

    if all_passed:

        print(
            "All 5 profiler runs matched the locked baseline."
        )

    else:

        print(
            "One or more profiler runs did NOT match the baseline."
        )

    print(
        "\nExpected profiler baseline:"
    )

    for key, value in EXPECTED.items():

        print(
            f"{key}: {value}"
        )


if __name__ == "__main__":

    main()

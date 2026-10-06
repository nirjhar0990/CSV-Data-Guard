import gc
import statistics
import time

from pipeline.profiler import load_csv

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
    clean_data
)

FILE_PATH = "data/messy_retail_data_250K.csv"
RUNS = 5

EXPECTED = {
    "original_rows": 250000,
    "cleaned_rows": 226234,
    "duplicate_rows_after_cleaning": 0,
    "quantity_dtype": "float64",
    "unit_price_dtype": "float64",
    "discount_dtype": "float64",
    "total_amount_dtype": "float64",
    "order_date_dtype": "datetime64[us]",
    "customer_age_dtype": "Int64",
    "customer_rating_dtype": "Int64",
}


def median(values):
    return statistics.median(values)


def timed_step(func, df):
    start = time.perf_counter()
    result = func(df)
    return result, time.perf_counter() - start


def run_once(run_number):
    gc.collect()

    print(
        f"\n===== CLEANER RUN {run_number}/{RUNS} =====",
        flush=True
    )

    start = time.perf_counter()
    raw_df = load_csv(FILE_PATH)
    load_time = time.perf_counter() - start

    original_df = raw_df.copy()
    original_df.insert(
        0,
        "Record_ID",
        range(1, len(original_df) + 1)
    )

    timings = {}

    current_df, timings["standardize_missing_values"] = timed_step(
        standardize_missing_values,
        original_df
    )

    current_df, timings["remove_duplicate_rows"] = timed_step(
        remove_duplicate_rows,
        current_df
    )

    current_df, timings["clean_text_casing"] = timed_step(
        clean_text_casing,
        current_df
    )

    current_df, timings["clean_customer_names"] = timed_step(
        clean_customer_names,
        current_df
    )

    current_df, timings["clean_city_names"] = timed_step(
        clean_city_names,
        current_df
    )

    current_df, timings["clean_categories"] = timed_step(
        clean_categories,
        current_df
    )

    current_df, timings["clean_emails"] = timed_step(
        clean_emails,
        current_df
    )

    current_df, timings["clean_numeric_values"] = timed_step(
        clean_numeric_values,
        current_df
    )

    current_df, timings["clean_numeric_ranges"] = timed_step(
        clean_numeric_ranges,
        current_df
    )

    current_df, timings["standardize_dates"] = timed_step(
        standardize_dates,
        current_df
    )

    current_df, timings["handle_invalid_values"] = timed_step(
        handle_invalid_values,
        current_df
    )

    helper_total = sum(timings.values())

    start = time.perf_counter()
    full_cleaned_df, cleaning_checks = clean_data(original_df)
    clean_data_time = time.perf_counter() - start

    result = {
        "original_rows": len(original_df),
        "cleaned_rows": len(full_cleaned_df),
        "duplicate_rows_after_cleaning": int(
            full_cleaned_df.duplicated().sum()
        ),
        "quantity_dtype": str(full_cleaned_df["Quantity"].dtype),
        "unit_price_dtype": str(full_cleaned_df["Unit_Price"].dtype),
        "discount_dtype": str(full_cleaned_df["Discount"].dtype),
        "total_amount_dtype": str(full_cleaned_df["Total_Amount"].dtype),
        "order_date_dtype": str(full_cleaned_df["Order_Date"].dtype),
        "customer_age_dtype": str(full_cleaned_df["Customer_Age"].dtype),
        "customer_rating_dtype": str(full_cleaned_df["Customer_Rating"].dtype),
        "cleaning_checks_type": type(cleaning_checks).__name__,
    }

    print(f"{'load_csv':<30}{load_time:>8.3f} sec")

    for name, elapsed in timings.items():
        print(f"{name:<30}{elapsed:>8.3f} sec")

    print(f"{'helper total':<30}{helper_total:>8.3f} sec")
    print(f"{'clean_data':<30}{clean_data_time:>8.3f} sec")

    return {
        "load_time": load_time,
        "timings": timings,
        "helper_total": helper_total,
        "clean_data": clean_data_time,
        "result": result,
    }


def validate_result(result, run_number):
    problems = []

    for key, expected_value in EXPECTED.items():
        actual = result[key]
        if actual != expected_value:
            problems.append(
                f"{key}: {actual} (expected {expected_value})"
            )

    if result["cleaning_checks_type"] != "dict":
        problems.append(
            "cleaning_checks_type: "
            f"{result['cleaning_checks_type']} (expected dict)"
        )

    if problems:
        print(
            f"\nWARNING: RUN {run_number} FAILED CORRECTNESS CHECK"
        )
        for problem in problems:
            print("  -", problem)
        return False

    print("Correctness Check: PASS")
    return True


def main():
    print(
        "\n================================================="
    )
    print(
        " CSV DATA GUARD - CLEANER 5 RUN MEDIAN BENCHMARK"
    )
    print(
        "================================================="
    )
    print("Dataset:", FILE_PATH)
    print("Runs:", RUNS)

    all_runs = []
    all_passed = True

    for run_number in range(1, RUNS + 1):
        run = run_once(run_number)
        passed = validate_result(
            run["result"],
            run_number
        )

        if not passed:
            all_passed = False

        all_runs.append(run)

    stage_names = [
        "standardize_missing_values",
        "remove_duplicate_rows",
        "clean_text_casing",
        "clean_customer_names",
        "clean_city_names",
        "clean_categories",
        "clean_emails",
        "clean_numeric_values",
        "clean_numeric_ranges",
        "standardize_dates",
        "handle_invalid_values",
    ]

    print(
        "\n================================================="
    )
    print(" MEDIAN CLEANER RESULTS")
    print(
        "================================================="
    )

    median_stage_times = {}

    for stage in stage_names:
        values = [
            run["timings"][stage]
            for run in all_runs
        ]
        stage_median = median(values)
        median_stage_times[stage] = stage_median
        print(f"{stage:<30}{stage_median:>8.3f} sec")

    helper_totals = [
        run["helper_total"]
        for run in all_runs
    ]

    clean_data_values = [
        run["clean_data"]
        for run in all_runs
    ]

    load_values = [
        run["load_time"]
        for run in all_runs
    ]

    median_helper_total = median(helper_totals)
    median_clean_data = median(clean_data_values)
    median_load = median(load_values)

    print()
    print(f"{'Median load_csv':<30}{median_load:>8.3f} sec")
    print(f"{'Median helper total':<30}{median_helper_total:>8.3f} sec")
    print(f"{'Median clean_data':<30}{median_clean_data:>8.3f} sec")

    print(
        "\n================================================="
    )
    print(" CLEANER HOTSPOT RANKING")
    print(
        "================================================="
    )

    sorted_stages = sorted(
        median_stage_times.items(),
        key=lambda item: item[1],
        reverse=True
    )

    median_stage_sum = sum(
        median_stage_times.values()
    )

    for name, elapsed in sorted_stages:
        share = (
            elapsed / median_stage_sum * 100
            if median_stage_sum
            else 0
        )
        print(
            f"{name:<30}"
            f"{elapsed:>8.3f} sec "
            f"({share:>5.1f}%)"
        )

    print(
        "\n================================================="
    )
    print(" CLEAN_DATA RUN SUMMARY")
    print(
        "================================================="
    )

    for index, value in enumerate(
        clean_data_values,
        start=1
    ):
        print(
            f"Run {index}: {value:.3f} sec"
        )

    print()
    print(
        f"Median clean_data: {median_clean_data:.3f} sec"
    )
    print(
        f"Best clean_data:   {min(clean_data_values):.3f} sec"
    )
    print(
        f"Worst clean_data:  {max(clean_data_values):.3f} sec"
    )

    print(
        "\n================================================="
    )
    print(" CORRECTNESS SUMMARY")
    print(
        "================================================="
    )

    if all_passed:
        print(
            "All 5 cleaner runs matched the locked baseline."
        )
    else:
        print(
            "One or more cleaner runs did NOT match the baseline."
        )

    print("\nExpected cleaner baseline:")
    print("Original Rows:", EXPECTED["original_rows"])
    print("Cleaned Rows:", EXPECTED["cleaned_rows"])
    print(
        "Duplicate Rows After Cleaning:",
        EXPECTED["duplicate_rows_after_cleaning"]
    )
    print("Quantity dtype:", EXPECTED["quantity_dtype"])
    print("Unit_Price dtype:", EXPECTED["unit_price_dtype"])
    print("Discount dtype:", EXPECTED["discount_dtype"])
    print(
        "Total_Amount dtype:",
        EXPECTED["total_amount_dtype"]
    )
    print(
        "Order_Date dtype:",
        EXPECTED["order_date_dtype"]
    )
    print(
        "Customer_Age dtype:",
        EXPECTED["customer_age_dtype"]
    )
    print(
        "Customer_Rating dtype:",
        EXPECTED["customer_rating_dtype"]
    )


if __name__ == "__main__":
    main()

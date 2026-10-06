import pandas as pd
import pytest

from pipeline.profiler import load_csv

from pipeline.cleaner import (
    standardize_missing_values,
    remove_duplicate_rows,
    clean_numeric_values,
    clean_numeric_ranges,
    clean_data,
)

from pipeline.validator import (
    validate_data,
    calculate_validation_score,
    calculate_cleaning_score,
    find_unresolved_cleaning_issues,
)

from pipeline.problem_map import (
    create_problem_map,
)

from pipeline.review import (
    create_review_dataset,
    merge_review_corrections,
)

from pipeline.orchestrator import (
    perform_data_quality_check,
    get_validation_row_counts,
    get_validation_failures_by_column,
    run_pipeline,
)


# ============================================================
# HELPERS
# ============================================================

def make_valid_raw_df():
    """
    Return a small valid raw dataset using all 15 business
    columns required by the production pipeline.
    """

    return pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001",
                "ORD-00002",
            ],

            "Customer_Name": [
                "Arun Das",
                "Riya Sen",
            ],

            "Customer_Email": [
                "arun.das@example.com",
                "riya.sen@example.com",
            ],

            "City": [
                "Kolkata",
                "Delhi",
            ],

            "Category": [
                "Electronics",
                "Books",
            ],

            "Product": [
                "Laptop",
                "Python Programming",
            ],

            "Quantity": [
                "1",
                "2",
            ],

            "Unit_Price": [
                "50000",
                "1000",
            ],

            "Discount": [
                "10",
                "5",
            ],

            "Total_Amount": [
                "45000",
                "1900",
            ],

            "Order_Date": [
                "2026-01-01",
                "2026-02-01",
            ],

            "Payment_Method": [
                "Credit Card",
                "UPI",
            ],

            "Order_Status": [
                "Completed",
                "Pending",
            ],

            "Customer_Age": [
                "35",
                "28",
            ],

            "Customer_Rating": [
                "5",
                "4",
            ],
        }
    )


def add_record_id(df):

    result = df.copy()

    result.insert(
        0,
        "Record_ID",
        range(
            1,
            len(result) + 1
        )
    )

    return result


# ============================================================
# 1. LOAD CSV PRESERVES MISSING TOKENS
# ============================================================

def test_load_csv_preserves_missing_tokens(
    tmp_path
):

    df = pd.DataFrame(
        {
            "A": [
                "",
                "NA",
                "None",
                "NULL",
                "null",
            ]
        }
    )

    path = (
        tmp_path
        / "missing_tokens.csv"
    )

    df.to_csv(
        path,
        index=False
    )

    result = load_csv(
        str(path)
    )

    assert result["A"].tolist() == [
        "",
        "NA",
        "None",
        "NULL",
        "null",
    ]


# ============================================================
# 2. ALL KNOWN MISSING TOKENS ARE STANDARDIZED
# ============================================================

def test_all_missing_tokens_become_na():

    df = pd.DataFrame(
        {
            "A": [
                "",
                "NA",
                "None",
                "NULL",
                "null",
            ]
        }
    )

    result = (
        standardize_missing_values(
            df
        )
    )

    assert (
        result["A"]
        .isna()
        .all()
    )


# ============================================================
# 3. Record_ID DOES NOT PREVENT DUPLICATE REMOVAL
# ============================================================

def test_duplicate_rows_ignore_record_id():

    df = pd.DataFrame(
        {
            "Record_ID": [
                1,
                2,
            ],

            "Order_ID": [
                "ORD-00001",
                "ORD-00001",
            ],

            "Customer_Name": [
                "Arun Das",
                "Arun Das",
            ],
        }
    )

    result = remove_duplicate_rows(
        df
    )

    assert len(result) == 1

    assert (
        result.iloc[0][
            "Record_ID"
        ]
        == 1
    )


# ============================================================
# 4. SAME ORDER_ID ALONE DOES NOT MEAN DUPLICATE ROW
# ============================================================

def test_duplicate_order_id_with_different_data_is_retained():

    df = pd.DataFrame(
        {
            "Record_ID": [
                1,
                2,
            ],

            "Order_ID": [
                "ORD-00001",
                "ORD-00001",
            ],

            "Customer_Name": [
                "Arun Das",
                "Riya Sen",
            ],
        }
    )

    result = remove_duplicate_rows(
        df
    )

    assert len(result) == 2


# ============================================================
# 5. SAFE AGE REPAIRS
# ============================================================

def test_safe_customer_age_formats_are_repaired():

    df = make_valid_raw_df()

    df.loc[
        0,
        "Customer_Age"
    ] = "4@6"

    df.loc[
        1,
        "Customer_Age"
    ] = "_37"

    df = add_record_id(
        df
    )

    result = clean_numeric_values(
        df
    )

    assert (
        result.loc[
            0,
            "Customer_Age"
        ]
        == 46
    )

    assert (
        result.loc[
            1,
            "Customer_Age"
        ]
        == 37
    )


# ============================================================
# 6. UNREPAIRABLE AGE BECOMES MISSING
# ============================================================

def test_unrepairable_age_becomes_missing():

    df = make_valid_raw_df()

    df.loc[
        0,
        "Customer_Age"
    ] = "abc"

    df = add_record_id(
        df
    )

    result = clean_numeric_values(
        df
    )

    assert pd.isna(
        result.loc[
            0,
            "Customer_Age"
        ]
    )


# ============================================================
# 7. QUANTITY ZERO IS ALLOWED BY CLEANER
# ============================================================

def test_quantity_zero_survives_cleaning():

    df = make_valid_raw_df()

    df.loc[
        0,
        "Quantity"
    ] = "0"

    df = add_record_id(
        df
    )

    result = clean_numeric_values(
        df
    )

    result = clean_numeric_ranges(
        result
    )

    assert (
        result.loc[
            0,
            "Quantity"
        ]
        == 0
    )


# ============================================================
# 8. NEGATIVE QUANTITY BECOMES MISSING
# ============================================================

def test_negative_quantity_becomes_missing():

    df = make_valid_raw_df()

    df.loc[
        0,
        "Quantity"
    ] = "-1"

    df = add_record_id(
        df
    )

    result = clean_numeric_values(
        df
    )

    result = clean_numeric_ranges(
        result
    )

    assert pd.isna(
        result.loc[
            0,
            "Quantity"
        ]
    )


# ============================================================
# 9. DISCOUNT ABOVE 100 BECOMES MISSING
# ============================================================

def test_discount_above_100_becomes_missing():

    df = make_valid_raw_df()

    df.loc[
        0,
        "Discount"
    ] = "150"

    df = add_record_id(
        df
    )

    result = clean_numeric_values(
        df
    )

    result = clean_numeric_ranges(
        result
    )

    assert pd.isna(
        result.loc[
            0,
            "Discount"
        ]
    )


# ============================================================
# 10. NEGATIVE DISCOUNT BECOMES MISSING
# ============================================================

def test_negative_discount_becomes_missing():

    df = make_valid_raw_df()

    df.loc[
        0,
        "Discount"
    ] = "-5"

    df = add_record_id(
        df
    )

    result = clean_numeric_values(
        df
    )

    result = clean_numeric_ranges(
        result
    )

    assert pd.isna(
        result.loc[
            0,
            "Discount"
        ]
    )


# ============================================================
# 11. GENUINE MISSING VALUES ARE NOT UNRESOLVED ISSUES
# ============================================================

def test_genuine_missing_values_not_counted_as_unresolved():

    original = add_record_id(
        make_valid_raw_df()
    )

    original.loc[
        0,
        "Customer_Email"
    ] = ""

    cleaned = original.copy()

    cleaned.loc[
        0,
        "Customer_Email"
    ] = pd.NA

    result = (
        find_unresolved_cleaning_issues(
            original,
            cleaned
        )
    )

    email_issue = result[
        (
            result["index"] == 0
        )
        &
        (
            result["column"]
            == "Customer_Email"
        )
    ]

    assert email_issue.empty


# ============================================================
# 12. ORIGINAL BAD VALUE BECOMING NA IS UNRESOLVED
# ============================================================

def test_bad_original_value_becoming_na_is_unresolved():

    original = add_record_id(
        make_valid_raw_df()
    )

    original.loc[
        0,
        "Customer_Age"
    ] = "999"

    cleaned = original.copy()

    cleaned.loc[
        0,
        "Customer_Age"
    ] = pd.NA

    result = (
        find_unresolved_cleaning_issues(
            original,
            cleaned
        )
    )

    issue = result[
        (
            result["index"] == 0
        )
        &
        (
            result["column"]
            == "Customer_Age"
        )
    ]

    assert len(issue) == 1

    assert (
        str(
            issue.iloc[0][
                "original_value"
            ]
        )
        == "999"
    )


# ============================================================
# 13. EMPTY DATASET VALIDATION SCORE
# ============================================================

def test_empty_dataset_validation_score_is_100():

    df = pd.DataFrame()

    failure_cases = pd.DataFrame(
        {
            "index": []
        }
    )

    score = (
        calculate_validation_score(
            df,
            failure_cases
        )
    )

    assert score == 100.0


# ============================================================
# 14. SAME ROW FAILING MANY RULES COUNTS ONCE
# ============================================================

def test_validation_score_counts_failed_row_once():

    df = pd.DataFrame(
        {
            "A": [
                1,
                2,
                3,
                4,
            ]
        }
    )

    failure_cases = pd.DataFrame(
        {
            "index": [
                1,
                1,
                1,
            ]
        }
    )

    score = (
        calculate_validation_score(
            df,
            failure_cases
        )
    )

    assert score == 75.0


# ============================================================
# 15. NO INITIAL CLEANING ISSUES = 100
# ============================================================

def test_cleaning_score_no_initial_issues():

    score = (
        calculate_cleaning_score(
            0,
            0
        )
    )

    assert score == 100.0


# ============================================================
# 16. CURRENT ISSUES GREATER THAN BASELINE DOES NOT GO NEGATIVE
# ============================================================

def test_cleaning_score_never_negative():

    score = (
        calculate_cleaning_score(
            5,
            10
        )
    )

    assert score == 0.0


# ============================================================
# 17. CLEANING SCORE CANNOT EXCEED 100
# ============================================================

def test_cleaning_score_never_exceeds_100():

    score = (
        calculate_cleaning_score(
            5,
            0
        )
    )

    assert score == 100.0


# ============================================================
# 18. PERFECT QUALITY STATUS ALLOWS EXPORT
# ============================================================

def test_quality_gate_allows_perfect_dataset():

    result = (
        perform_data_quality_check(
            100.0,
            100.0,
            True
        )
    )

    assert (
        result[
            "cleaning_complete"
        ]
        is True
    )

    assert (
        result[
            "validation_complete"
        ]
        is True
    )

    assert (
        result[
            "export_allowed"
        ]
        is True
    )

    assert (
        result[
            "export_status"
        ]
        == "READY"
    )


# ============================================================
# 19. VALIDATION SUCCESS FLAG IS REQUIRED
# ============================================================

def test_quality_gate_blocks_when_validation_success_false():

    result = (
        perform_data_quality_check(
            100.0,
            100.0,
            False
        )
    )

    assert (
        result[
            "export_allowed"
        ]
        is False
    )

    assert (
        result[
            "export_status"
        ]
        == "BLOCKED"
    )


# ============================================================
# 20. CLEANING BELOW 100 BLOCKS EXPORT
# ============================================================

def test_quality_gate_blocks_when_cleaning_incomplete():

    result = (
        perform_data_quality_check(
            99.99,
            100.0,
            True
        )
    )

    assert (
        result[
            "export_allowed"
        ]
        is False
    )

    assert (
        result[
            "cleaning_complete"
        ]
        is False
    )


# ============================================================
# 21. VALID ROW COUNTS DEDUPLICATE FAILURE INDEXES
# ============================================================

def test_validation_row_counts_count_each_row_once():

    df = pd.DataFrame(
        {
            "A": [
                1,
                2,
                3,
                4,
                5,
            ]
        }
    )

    failure_cases = pd.DataFrame(
        {
            "index": [
                1,
                1,
                3,
                3,
                3,
            ]
        }
    )

    valid_rows, invalid_rows = (
        get_validation_row_counts(
            df,
            failure_cases
        )
    )

    assert invalid_rows == 2
    assert valid_rows == 3


# ============================================================
# 22. EMPTY DATASET ROW COUNTS
# ============================================================

def test_validation_row_counts_empty_dataset():

    valid_rows, invalid_rows = (
        get_validation_row_counts(
            pd.DataFrame(),
            None
        )
    )

    assert valid_rows == 0
    assert invalid_rows == 0


# ============================================================
# 23. FAILURE SUMMARY HANDLES NONE
# ============================================================

def test_validation_failures_by_column_handles_none():

    result = (
        get_validation_failures_by_column(
            None
        )
    )

    assert isinstance(
        result,
        pd.Series
    )

    assert result.empty


# ============================================================
# 24. FAILURE SUMMARY COUNTS UNIQUE ROWS
# ============================================================

def test_validation_failures_by_column_counts_unique_rows():

    failure_cases = pd.DataFrame(
        {
            "index": [
                0,
                0,
                1,
                2,
            ],

            "column": [
                "Customer_Email",
                "Customer_Email",
                "Customer_Email",
                "Category",
            ]
        }
    )

    result = (
        get_validation_failures_by_column(
            failure_cases
        )
    )

    assert (
        result[
            "Customer_Email"
        ]
        == 2
    )

    assert (
        result[
            "Category"
        ]
        == 1
    )


# ============================================================
# 25. PROBLEM MAP IGNORES INVALID SOURCE INDEX
# ============================================================

def test_problem_map_ignores_out_of_range_source_index():

    original = add_record_id(
        make_valid_raw_df()
    )

    unresolved = pd.DataFrame(
        {
            "index": [
                999
            ],

            "column": [
                "Customer_Age"
            ],

            "original_value": [
                "999"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue"
            ]
        }
    )

    problem_map = (
        create_problem_map(
            original,
            None,
            unresolved
        )
    )

    assert problem_map.empty


# ============================================================
# 26. REVIEW IGNORES NON-REVIEWABLE PROBLEM
# ============================================================

def test_review_dataset_ignores_non_reviewable_problem():

    original = add_record_id(
        make_valid_raw_df()
    )

    cleaned, _ = clean_data(
        original
    )

    problem_map = pd.DataFrame(
        {
            "index": [
                0
            ],

            "column": [
                "Customer_Email"
            ],

            "validation_error": [
                "Invalid email"
            ],

            "how_to_fix": [
                "Fix email"
            ],

            "source": [
                "email"
            ],

            "reportable": [
                True
            ],

            "reviewable": [
                False
            ],
        }
    )

    review = (
        create_review_dataset(
            original,
            cleaned,
            problem_map
        )
    )

    assert review.empty

    assert review.columns.tolist() == [
        "Record_ID",
        "Order_ID"
    ]


# ============================================================
# 27. REVIEW IGNORES INVALID INDEX
# ============================================================

def test_review_dataset_ignores_invalid_index():

    original = add_record_id(
        make_valid_raw_df()
    )

    cleaned, _ = clean_data(
        original
    )

    problem_map = pd.DataFrame(
        {
            "index": [
                999
            ],

            "column": [
                "Customer_Age"
            ],

            "validation_error": [
                "Invalid age"
            ],

            "how_to_fix": [
                "Fix age"
            ],

            "source": [
                "validation"
            ],

            "reportable": [
                True
            ],

            "reviewable": [
                True
            ],
        }
    )

    review = (
        create_review_dataset(
            original,
            cleaned,
            problem_map
        )
    )

    assert review.empty


# ============================================================
# 28. UNKNOWN Record_ID CORRECTION IS IGNORED
# ============================================================

def test_merge_ignores_unknown_record_id():

    original = add_record_id(
        make_valid_raw_df()
    )

    cleaned, _ = clean_data(
        original
    )

    original_review = pd.DataFrame(
        {
            "Record_ID": [
                999
            ],

            "Order_ID": [
                "ORD-99999"
            ],

            "Customer_Age": [
                "999"
            ],
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [
                999
            ],

            "Order_ID": [
                "ORD-99999"
            ],

            "Customer_Age": [
                "30"
            ],
        }
    )

    corrected_df, summary = (
        merge_review_corrections(
            cleaned,
            original_review,
            corrected_review
        )
    )

    assert (
        summary[
            "corrections_applied"
        ]
        == 0
    )

    assert (
        summary[
            "records_changed"
        ]
        == 0
    )

    pd.testing.assert_frame_equal(
        corrected_df,
        cleaned
    )


# ============================================================
# 29. UNCHANGED REVIEW VALUE IS NOT A CORRECTION
# ============================================================

def test_merge_ignores_unchanged_value():

    original = add_record_id(
        make_valid_raw_df()
    )

    cleaned, _ = clean_data(
        original
    )

    original_review = pd.DataFrame(
        {
            "Record_ID": [
                1
            ],

            "Order_ID": [
                "ORD-00001"
            ],

            "Customer_Age": [
                "35"
            ],
        }
    )

    corrected_review = (
        original_review.copy()
    )

    corrected_df, summary = (
        merge_review_corrections(
            cleaned,
            original_review,
            corrected_review
        )
    )

    assert (
        summary[
            "corrections_applied"
        ]
        == 0
    )

    assert (
        summary[
            "records_changed"
        ]
        == 0
    )


# ============================================================
# 30. FULLY VALID FILE PASSES COMPLETE PIPELINE
# ============================================================

def test_fully_valid_dataset_passes_full_pipeline(
    tmp_path
):

    df = make_valid_raw_df()

    file_path = (
        tmp_path
        / "valid_dataset.csv"
    )

    df.to_csv(
        file_path,
        index=False
    )

    result = run_pipeline(
        str(file_path)
    )

    assert (
        result[
            "cleaning_score"
        ]
        == 100.0
    )

    assert (
        result[
            "validation_score"
        ]
        == 100.0
    )

    assert (
        result[
            "validation"
        ][
            "success"
        ]
        is True
    )

    assert (
        result[
            "export_allowed"
        ]
        is True
    )

    assert (
        result[
            "review_data"
        ].empty
    )


# ============================================================
# 31. EXTREME INVALID ROW BLOCKS EXPORT
# ============================================================

def test_extreme_invalid_row_blocks_export(
    tmp_path
):

    df = make_valid_raw_df()

    df.loc[
        1,
        "Category"
    ] = "UNKNOWN"

    df.loc[
        1,
        "Quantity"
    ] = "-999999"

    df.loc[
        1,
        "Discount"
    ] = "999999"

    df.loc[
        1,
        "Customer_Age"
    ] = "999999"

    df.loc[
        1,
        "Customer_Rating"
    ] = "-999"

    file_path = (
        tmp_path
        / "extreme_invalid.csv"
    )

    df.to_csv(
        file_path,
        index=False
    )

    result = run_pipeline(
        str(file_path)
    )

    assert (
        result[
            "export_allowed"
        ]
        is False
    )

    assert (
        result[
            "cleaning_score"
        ]
        < 100.0
    )

    assert (
        result[
            "review_records"
        ]
        > 0
    )


# ============================================================
# 32. ORIGINAL DATA IS NOT MUTATED BY CLEANER
# ============================================================

def test_cleanerdoes_not_mutate_original_dataframe():

    original = add_record_id(
        make_valid_raw_df()
    )

    original_before = (
        original.copy(
            deep=True
        )
    )

    clean_data(
        original
    )

    pd.testing.assert_frame_equal(
        original,
        original_before
    )

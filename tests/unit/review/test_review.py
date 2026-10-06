import pandas as pd
import pytest

from pipeline.review import (
    create_review_dataset,
    merge_review_corrections,
    analyze_issue_frequency,
    REVIEW_MISSING_MARKER,
)


# ============================================================
# HELPERS
# ============================================================

def make_original_df():

    return pd.DataFrame(
        {
            "Record_ID": [
                1,
                2,
                3
            ],

            "Order_ID": [
                "ORD-00001",
                "ORD-00002",
                "ORD-00003"
            ],

            "Customer_Name": [
                "Arun",
                "Riya",
                "Amit"
            ],

            "Customer_Email": [
                "arun@example.com",
                "bad-email",
                pd.NA
            ],

            "Category": [
                "Electronics",
                "INVALID",
                "Books"
            ],

            "Quantity": [
                "1",
                "-5",
                "3"
            ],

            "Customer_Age": [
                "30",
                "abc",
                "40"
            ]
        }
    )


def make_cleaned_df():

    return pd.DataFrame(
        {
            "Record_ID": [
                1,
                2,
                3
            ],

            "Order_ID": [
                "ORD-00001",
                "ORD-00002",
                "ORD-00003"
            ],

            "Customer_Name": [
                "Arun",
                "Riya",
                "Amit"
            ],

            "Customer_Email": [
                "arun@example.com",
                "bad-email",
                pd.NA
            ],

            "Category": [
                "Electronics",
                pd.NA,
                "Books"
            ],

            "Quantity": pd.Series(
                [
                    1.0,
                    pd.NA,
                    3.0
                ],
                dtype="Float64"
            ),

            "Customer_Age": pd.Series(
                [
                    30,
                    pd.NA,
                    40
                ],
                dtype="Int64"
            )
        }
    )


def make_problem_map(rows):

    return pd.DataFrame(
        rows,
        columns=[
            "index",
            "column",
            "validation_error",
            "how_to_fix",
            "source",
            "reportable",
            "reviewable"
        ]
    )


# ============================================================
# CREATE REVIEW DATASET
# ============================================================


# ============================================================
# 1. EMPTY PROBLEM MAP
# ============================================================

def test_create_review_dataset_empty_problem_map():

    original_df = make_original_df()
    cleaned_df = make_cleaned_df()

    result = create_review_dataset(
        original_df,
        cleaned_df,
        pd.DataFrame()
    )

    assert result.empty

    assert result.columns.tolist() == [
        "Record_ID",
        "Order_ID"
    ]


# ============================================================
# 2. NONE PROBLEM MAP
# ============================================================

def test_create_review_dataset_none_problem_map():

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        None
    )

    assert result.empty

    assert result.columns.tolist() == [
        "Record_ID",
        "Order_ID"
    ]


# ============================================================
# 3. REVIEWABLE FALSE IS EXCLUDED
# ============================================================

def test_non_reviewable_problem_is_excluded():

    problem_map = make_problem_map(
        [
            [
                1,
                "Customer_Email",
                "Invalid email syntax",
                "Enter a valid email.",
                "email",
                True,
                False
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert result.empty

    assert result.columns.tolist() == [
        "Record_ID",
        "Order_ID"
    ]


# ============================================================
# 4. REVIEWABLE PROBLEM IS INCLUDED
# ============================================================

def test_reviewable_problem_is_included():

    problem_map = make_problem_map(
        [
            [
                1,
                "Category",
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert len(result) == 1

    assert result["Record_ID"].tolist() == [2]

    assert result["Order_ID"].tolist() == [
        "ORD-00002"
    ]


# ============================================================
# 5. ORIGINAL BAD VALUE IS PRESERVED
# ============================================================

def test_original_bad_value_preserved_when_cleanermade_missing():

    problem_map = make_problem_map(
        [
            [
                1,
                "Customer_Age",
                "Invalid customer age",
                "Correct age.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert (
        result.loc[
            0,
            "Customer_Age"
        ]
        == "abc"
    )


# ============================================================
# 6. CURRENT INVALID VALUE IS USED
# ============================================================

def test_current_cleaned_value_used_when_still_present():

    problem_map = make_problem_map(
        [
            [
                1,
                "Customer_Email",
                "Validation failed",
                "Correct email.",
                "validation",
                False,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert (
        result.loc[
            0,
            "Customer_Email"
        ]
        == "bad-email"
    )


# ============================================================
# 7. REQUIRED MISSING VALUE GETS MARKER
# ============================================================

def test_genuine_missing_problem_uses_missing_marker():

    problem_map = make_problem_map(
        [
            [
                2,
                "Customer_Email",
                "Validation failed",
                "Enter email.",
                "validation",
                False,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert (
        result.loc[
            0,
            "Customer_Email"
        ]
        == REVIEW_MISSING_MARKER
    )


# ============================================================
# 8. REVIEW DATASET IS SPARSE
# ============================================================

def test_review_dataset_is_sparse():

    problem_map = make_problem_map(
        [
            [
                1,
                "Category",
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ],

            [
                2,
                "Customer_Email",
                "Validation failed",
                "Enter email.",
                "validation",
                False,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert result.columns.tolist() == [
        "Record_ID",
        "Order_ID",
        "Customer_Email",
        "Category"
    ]

    row_record_2 = result[
        result["Record_ID"] == 2
    ].iloc[0]

    row_record_3 = result[
        result["Record_ID"] == 3
    ].iloc[0]

    # Record 2 needs Category only
    assert row_record_2["Customer_Email"] == ""
    assert row_record_2["Category"] == "INVALID"

    # Record 3 needs Customer_Email only
    assert (
        row_record_3["Customer_Email"]
        == REVIEW_MISSING_MARKER
    )

    assert row_record_3["Category"] == ""


# ============================================================
# 9. DUPLICATE PROBLEM CELLS ARE DEDUPLICATED
# ============================================================

def test_duplicate_problem_cells_are_deduplicated():

    problem_map = make_problem_map(
        [
            [
                1,
                "Category",
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ],

            [
                1,
                "Category",
                "Validation failed",
                "Fix category.",
                "validation",
                True,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert len(result) == 1

    assert result.columns.tolist() == [
        "Record_ID",
        "Order_ID",
        "Category"
    ]


# ============================================================
# 10. INVALID SOURCE INDEX IS IGNORED
# ============================================================

def test_invalid_source_index_is_ignored():

    problem_map = make_problem_map(
        [
            [
                999,
                "Category",
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert result.empty


# ============================================================
# 11. NON-BUSINESS COLUMNS ARE NOT REVIEW COLUMNS
# ============================================================

def test_record_id_and_order_id_not_treated_as_problem_columns():

    problem_map = make_problem_map(
        [
            [
                1,
                "Order_ID",
                "Invalid Order ID",
                "Correct it.",
                "validation",
                True,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert result.empty


# ============================================================
# 12. ORIGINAL COLUMN ORDER IS PRESERVED
# ============================================================

def test_review_problem_columns_follow_original_column_order():

    problem_map = make_problem_map(
        [
            [
                1,
                "Customer_Age",
                "Invalid age",
                "Fix.",
                "cleaning",
                True,
                True
            ],

            [
                1,
                "Customer_Email",
                "Invalid email",
                "Fix.",
                "validation",
                False,
                True
            ],

            [
                1,
                "Category",
                "Invalid category",
                "Fix.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_review_dataset(
        make_original_df(),
        make_cleaned_df(),
        problem_map
    )

    assert result.columns.tolist() == [
        "Record_ID",
        "Order_ID",
        "Customer_Email",
        "Category",
        "Customer_Age"
    ]


# ============================================================
# MERGE REVIEW CORRECTIONS
# ============================================================


def make_merge_cleaned_df():

    return pd.DataFrame(
        {
            "Record_ID": [
                1,
                2
            ],

            "Order_ID": [
                "ORD-00001",
                "ORD-00002"
            ],

            "Customer_Email": [
                "a@example.com",
                "bad-email"
            ],

            "Customer_Age": pd.Series(
                [
                    30,
                    pd.NA
                ],
                dtype="Int64"
            ),

            "Quantity": [
                1.0,
                2.0
            ],

            "Order_Date": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02"
                ]
            )
        },
        index=[
            10,
            20
        ]
    )


# ============================================================
# 13. APPLY INTEGER CORRECTION
# ============================================================

def test_merge_applies_integer_correction():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Age": ["abc"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Age": ["35"]
        }
    )

    corrected_df, summary = (
        merge_review_corrections(
            cleaned_df,
            original_review,
            corrected_review
        )
    )

    row = corrected_df[
        corrected_df["Record_ID"] == 2
    ].iloc[0]

    assert row["Customer_Age"] == 35

    assert summary["corrections_applied"] == 1
    assert summary["records_changed"] == 1

    assert summary["correction_columns"] == [
        "Customer_Age"
    ]


# ============================================================
# 14. [MISSING] CAN BE CORRECTED
# ============================================================

def test_merge_missing_marker_can_be_corrected():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Email": [
                REVIEW_MISSING_MARKER
            ]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Email": [
                "riya@example.com"
            ]
        }
    )

    result, summary = merge_review_corrections(
        cleaned_df,
        original_review,
        corrected_review
    )

    value = result.loc[
        result["Record_ID"] == 2,
        "Customer_Email"
    ].iloc[0]

    assert value == "riya@example.com"

    assert summary["corrections_applied"] == 1


# ============================================================
# 15. UNCHANGED [MISSING] IS NOT APPLIED
# ============================================================

def test_unchanged_missing_marker_is_ignored():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Email": [
                REVIEW_MISSING_MARKER
            ]
        }
    )

    corrected_review = original_review.copy()

    result, summary = merge_review_corrections(
        cleaned_df,
        original_review,
        corrected_review
    )

    assert summary["corrections_applied"] == 0
    assert summary["records_changed"] == 0


# ============================================================
# 16. BLANK NON-PROBLEM CELL CANNOT BE CHANGED
# ============================================================

def test_blank_original_review_cell_cannot_be_changed():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Email": [""],
            "Customer_Age": ["abc"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],

            # User accidentally modifies a sparse blank cell
            "Customer_Email": [
                "hacker@example.com"
            ],

            "Customer_Age": [
                "40"
            ]
        }
    )

    result, summary = merge_review_corrections(
        cleaned_df,
        original_review,
        corrected_review
    )

    row = result[
        result["Record_ID"] == 2
    ].iloc[0]

    # Email must remain unchanged because original
    # sparse review cell was blank.
    assert row["Customer_Email"] == "bad-email"

    assert row["Customer_Age"] == 40

    assert summary["corrections_applied"] == 1


# ============================================================
# 17. BLANK CORRECTED VALUE IS IGNORED
# ============================================================

def test_blank_corrected_value_is_ignored():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Email": ["bad-email"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Email": [""]
        }
    )

    result, summary = merge_review_corrections(
        cleaned_df,
        original_review,
        corrected_review
    )

    value = result.loc[
        result["Record_ID"] == 2,
        "Customer_Email"
    ].iloc[0]

    assert value == "bad-email"

    assert summary["corrections_applied"] == 0


# ============================================================
# 18. INVALID INTEGER CORRECTION IS IGNORED
# ============================================================

def test_invalid_integer_correction_is_ignored():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Age": ["abc"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Age": ["not-a-number"]
        }
    )

    result, summary = merge_review_corrections(
        cleaned_df,
        original_review,
        corrected_review
    )

    value = result.loc[
        result["Record_ID"] == 2,
        "Customer_Age"
    ].iloc[0]

    assert pd.isna(value)

    assert summary["corrections_applied"] == 0


# ============================================================
# 19. FLOAT CORRECTION IS CONVERTED
# ============================================================

def test_float_correction_is_converted():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Quantity": ["2"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Quantity": ["4.5"]
        }
    )

    result, summary = merge_review_corrections(
        cleaned_df,
        original_review,
        corrected_review
    )

    value = result.loc[
        result["Record_ID"] == 2,
        "Quantity"
    ].iloc[0]

    assert value == 4.5
    assert summary["corrections_applied"] == 1


# ============================================================
# 20. DATETIME CORRECTION IS CONVERTED
# ============================================================

def test_datetime_correction_is_converted():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Order_Date": ["2026-01-02"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Order_Date": ["2026-05-10"]
        }
    )

    result, summary = merge_review_corrections(
        cleaned_df,
        original_review,
        corrected_review
    )

    value = result.loc[
        result["Record_ID"] == 2,
        "Order_Date"
    ].iloc[0]

    assert value == pd.Timestamp(
        "2026-05-10"
    )

    assert summary["corrections_applied"] == 1


# ============================================================
# 21. ORIGINAL DATAFRAME INDEX IS PRESERVED
# ============================================================

def test_merge_preserves_dataframe_index():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Age": ["abc"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Age": ["35"]
        }
    )

    result, _ = merge_review_corrections(
        cleaned_df,
        original_review,
        corrected_review
    )

    assert result.index.tolist() == [
        10,
        20
    ]


# ============================================================
# 22. DUPLICATE RECORD_ID IS REJECTED
# ============================================================

def test_duplicate_corrected_record_id_rejected():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Age": ["abc"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [
                2,
                2
            ],

            "Order_ID": [
                "ORD-00002",
                "ORD-00002"
            ],

            "Customer_Age": [
                "35",
                "36"
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="duplicate Record_ID"
    ):

        merge_review_corrections(
            cleaned_df,
            original_review,
            corrected_review
        )


# ============================================================
# 23. REQUIRED REVIEW COLUMNS ARE VALIDATED
# ============================================================

def test_missing_required_review_column_rejected():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Customer_Age": ["abc"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Customer_Age": ["35"]
        }
    )

    with pytest.raises(
        ValueError,
        match="Original review dataset is missing"
    ):

        merge_review_corrections(
            cleaned_df,
            original_review,
            corrected_review
        )


# ============================================================
# 24. UNKNOWN CORRECTION COLUMN IS REJECTED
# ============================================================

def test_unknown_correction_column_rejected():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Unknown_Field": ["bad"]
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"],
            "Unknown_Field": ["good"]
        }
    )

    with pytest.raises(
        ValueError,
        match="Unknown columns"
    ):

        merge_review_corrections(
            cleaned_df,
            original_review,
            corrected_review
        )


# ============================================================
# 25. NO CORRECTION COLUMNS IS REJECTED
# ============================================================

def test_no_correction_columns_rejected():

    cleaned_df = make_merge_cleaned_df()

    original_review = pd.DataFrame(
        {
            "Record_ID": [2],
            "Order_ID": ["ORD-00002"]
        }
    )

    corrected_review = (
        original_review.copy()
    )

    with pytest.raises(
        ValueError,
        match="No correction columns found"
    ):

        merge_review_corrections(
            cleaned_df,
            original_review,
            corrected_review
        )


# ============================================================
# ANALYZE ISSUE FREQUENCY
# ============================================================


# ============================================================
# 26. EMPTY FREQUENCY INPUTS
# ============================================================

def test_analyze_issue_frequency_empty_inputs():

    (
        unresolved_summary,
        validation_summary,
        value_summary
    ) = analyze_issue_frequency(
        None,
        None
    )

    assert unresolved_summary.empty
    assert validation_summary.empty
    assert value_summary.empty

    assert unresolved_summary.columns.tolist() == [
        "Column",
        "Issue Type",
        "Count"
    ]

    assert validation_summary.columns.tolist() == [
        "Column",
        "Validation Rule",
        "Count"
    ]

    assert value_summary.columns.tolist() == [
        "Column",
        "Problem Value",
        "Count"
    ]


# ============================================================
# 27. UNRESOLVED ISSUE FREQUENCY
# ============================================================

def test_unresolved_issue_frequency():

    unresolved_issues = pd.DataFrame(
        {
            "index": [
                0,
                1,
                2
            ],

            "column": [
                "Category",
                "Category",
                "Customer_Age"
            ],

            "original_value": [
                "BAD",
                "BAD",
                "abc"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue",
                "Unresolved Cleaning Issue",
                "Unresolved Cleaning Issue"
            ]
        }
    )

    (
        unresolved_summary,
        _,
        value_summary
    ) = analyze_issue_frequency(
        unresolved_issues,
        None
    )

    category_row = unresolved_summary[
        unresolved_summary["Column"]
        == "Category"
    ].iloc[0]

    assert category_row["Count"] == 2

    bad_value = value_summary[
        (
            value_summary["Column"]
            == "Category"
        )
        &
        (
            value_summary["Problem Value"]
            == "BAD"
        )
    ].iloc[0]

    assert bad_value["Count"] == 2


# ============================================================
# 28. VALIDATION FAILURE FREQUENCY
# ============================================================

def test_validation_failure_frequency():

    failure_cases = pd.DataFrame(
        {
            "column": [
                "Customer_Email",
                "Customer_Email",
                "Category"
            ],

            "check": [
                "str_matches",
                "str_matches",
                "isin"
            ]
        }
    )

    (
        _,
        validation_summary,
        _
    ) = analyze_issue_frequency(
        None,
        failure_cases
    )

    email_row = validation_summary[
        (
            validation_summary["Column"]
            == "Customer_Email"
        )
        &
        (
            validation_summary[
                "Validation Rule"
            ]
            == "str_matches"
        )
    ].iloc[0]

    assert email_row["Count"] == 2

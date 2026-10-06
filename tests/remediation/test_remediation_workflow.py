import pandas as pd
import pytest

from pipeline.orchestrator import (
    run_pipeline,
    apply_review_corrections,
)

from pipeline.review import REVIEW_MISSING_MARKER


# ============================================================
# TEST DATA
# ============================================================

def make_remediation_dataset():
    """
    Dataset designed specifically for remediation testing.

    Row 0:
        Completely valid.

    Row 1:
        Contains several problems requiring manual correction:
            - missing Customer_Email
            - invalid Category
            - negative Quantity
            - out-of-range Customer_Age

    The cleaner will convert Category / Quantity / Customer_Age
    to missing values.

    Customer_Email is genuinely missing and should appear as
    [MISSING] in the review dataset.
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
                "",
            ],

            "City": [
                "Kolkata",
                "Howrah",
            ],

            "Category": [
                "Electronics",
                "UNKNOWN",
            ],

            "Product": [
                "Laptop",
                "Laptop",
            ],

            "Quantity": [
                "1",
                "-5",
            ],

            "Unit_Price": [
                "50000",
                "2000",
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
                "2026-01-02",
            ],

            "Payment_Method": [
                "Credit Card",
                "Cash",
            ],

            "Order_Status": [
                "Completed",
                "Completed",
            ],

            "Customer_Age": [
                "35",
                "452",
            ],

            "Customer_Rating": [
                "5",
                "4",
            ],
        }
    )


# ============================================================
# HELPERS
# ============================================================

@pytest.fixture
def initial_result(tmp_path):
    """
    Create a temporary CSV and run the real initial pipeline.
    """

    df = make_remediation_dataset()

    file_path = (
        tmp_path
        / "remediation_test.csv"
    )

    df.to_csv(
        file_path,
        index=False
    )

    return run_pipeline(
        str(file_path)
    )


def get_review_row(
    review_df,
    record_id
):
    return review_df[
        review_df["Record_ID"]
        == record_id
    ].iloc[0]


def make_round_1_correction(
    initial_result
):
    """
    Round 1 deliberately corrects ONLY Category.

    Other review problems are left unchanged so that
    we can verify multi-round remediation.
    """

    corrected_review = (
        initial_result[
            "review_data"
        ]
        .copy()
    )

    mask = (
        corrected_review[
            "Record_ID"
        ] == 2
    )

    corrected_review.loc[
        mask,
        "Category"
    ] = "Books"

    return corrected_review


def run_round_1(
    initial_result
):

    corrected_review = (
        make_round_1_correction(
            initial_result
        )
    )

    return apply_review_corrections(
        initial_result,
        corrected_review
    )


def make_round_2_correction(
    round_1_result
):
    """
    Correct all problems still remaining after round 1.
    """

    corrected_review = (
        round_1_result[
            "review_data"
        ]
        .copy()
    )

    mask = (
        corrected_review[
            "Record_ID"
        ] == 2
    )


    # --------------------------------------------------------
    # Missing Email
    # --------------------------------------------------------

    if (
        "Customer_Email"
        in corrected_review.columns
    ):

        corrected_review.loc[
            mask,
            "Customer_Email"
        ] = (
            "riya.sen@example.com"
        )


    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    if (
        "Quantity"
        in corrected_review.columns
    ):

        corrected_review.loc[
            mask,
            "Quantity"
        ] = "2"


    # --------------------------------------------------------
    # Customer Age
    # --------------------------------------------------------

    if (
        "Customer_Age"
        in corrected_review.columns
    ):

        corrected_review.loc[
            mask,
            "Customer_Age"
        ] = "30"


    return corrected_review


def run_round_2(
    round_1_result
):

    corrected_review = (
        make_round_2_correction(
            round_1_result
        )
    )

    return apply_review_corrections(
        round_1_result,
        corrected_review
    )


# ============================================================
# 1. INITIAL PIPELINE REQUIRES REVIEW
# ============================================================

def test_initial_pipeline_requires_review(
    initial_result
):

    assert (
        initial_result[
            "export_allowed"
        ]
        is False
    )

    assert (
        initial_result[
            "review_records"
        ]
        > 0
    )

    assert not initial_result[
        "review_data"
    ].empty


# ============================================================
# 2. INITIAL REVIEW USES Record_ID
# ============================================================

def test_review_dataset_contains_record_id(
    initial_result
):

    review_df = (
        initial_result[
            "review_data"
        ]
    )

    assert (
        "Record_ID"
        in review_df.columns
    )

    assert (
        "Order_ID"
        in review_df.columns
    )

    assert 2 in set(
        review_df[
            "Record_ID"
        ]
    )


# ============================================================
# 3. ORIGINAL BAD VALUES ARE PRESERVED
# ============================================================

def test_initial_review_preserves_bad_values(
    initial_result
):

    row = get_review_row(
        initial_result[
            "review_data"
        ],
        2
    )

    assert (
        str(
            row["Category"]
        )
        == "UNKNOWN"
    )

    assert (
        str(
            row["Quantity"]
        )
        == "-5"
    )

    assert (
        str(
            row["Customer_Age"]
        )
        == "452"
    )


# ============================================================
# 4. MISSING EMAIL USES [MISSING]
# ============================================================

def test_missing_email_uses_missing_marker(
    initial_result
):

    row = get_review_row(
        initial_result[
            "review_data"
        ],
        2
    )

    assert (
        row[
            "Customer_Email"
        ]
        == REVIEW_MISSING_MARKER
    )


# ============================================================
# 5. INITIAL CLEANING SCORE IS ZERO
# ============================================================

def test_initial_cleaning_score_is_zero(
    initial_result
):

    assert (
        initial_result[
            "cleaning_score"
        ]
        == 0.0
    )

    assert (
        initial_result[
            "initial_unresolved_cleaning_issue_count"
        ]
        > 0
    )


# ============================================================
# 6. ROUND 1 APPLIES ONLY CHANGED VALUE
# ============================================================

def test_round_1_applies_only_category(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    merge_summary = (
        round_1[
            "merge_summary"
        ]
    )

    assert (
        merge_summary[
            "corrections_applied"
        ]
        == 1
    )

    assert (
        merge_summary[
            "records_changed"
        ]
        == 1
    )

    assert (
        merge_summary[
            "correction_columns"
        ]
        == [
            "Category"
        ]
    )


# ============================================================
# 7. ROUND 1 CORRECTION REACHES CURRENT DATA
# ============================================================

def test_round_1_category_is_merged(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    corrected_df = (
        round_1[
            "corrected_data"
        ]
    )

    row = corrected_df[
        corrected_df[
            "Record_ID"
        ] == 2
    ].iloc[0]

    assert (
        row[
            "Category"
        ]
        == "Books"
    )


# ============================================================
# 8. ROUND 1 REDUCES UNRESOLVED ISSUES
# ============================================================

def test_round_1_reduces_unresolved_count(
    initial_result
):

    initial_count = (
        initial_result[
            "initial_unresolved_cleaning_issue_count"
        ]
    )

    round_1 = run_round_1(
        initial_result
    )

    remaining_count = len(
        round_1[
            "unresolved_cleaning_issues"
        ]
    )

    assert (
        remaining_count
        < initial_count
    )

    assert (
        remaining_count
        > 0
    )


# ============================================================
# 9. ROUND 1 IMPROVES CLEANING SCORE
# ============================================================

def test_round_1_improves_cleaning_score(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    assert (
        round_1[
            "cleaning_score"
        ]
        >
        initial_result[
            "cleaning_score"
        ]
    )

    assert (
        round_1[
            "cleaning_score"
        ]
        < 100.0
    )


# ============================================================
# 10. INITIAL BASELINE IS PRESERVED
# ============================================================

def test_initial_unresolved_baseline_is_preserved(
    initial_result
):

    initial_count = (
        initial_result[
            "initial_unresolved_cleaning_issue_count"
        ]
    )

    round_1 = run_round_1(
        initial_result
    )

    assert (
        round_1[
            "initial_unresolved_cleaning_issue_count"
        ]
        == initial_count
    )


# ============================================================
# 11. ROUND 1 STILL BLOCKS EXPORT
# ============================================================

def test_partial_remediation_still_blocks_export(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    assert (
        round_1[
            "export_allowed"
        ]
        is False
    )

    assert (
        round_1[
            "review_records"
        ]
        > 0
    )


# ============================================================
# 12. CORRECTED CATEGORY DISAPPEARS FROM NEXT REVIEW
# ============================================================

def test_corrected_field_disappears_from_next_review(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    review_df = (
        round_1[
            "review_data"
        ]
    )

    row = get_review_row(
        review_df,
        2
    )

    # Category was corrected in round 1.
    #
    # It should either:
    #   - no longer exist as a review column
    # or
    #   - exist only as a sparse blank cell.

    if (
        "Category"
        in review_df.columns
    ):

        assert (
            pd.isna(
                row["Category"]
            )
            or
            str(
                row["Category"]
            ).strip()
            == ""
        )


# ============================================================
# 13. UNRESOLVED VALUES REMAIN IN ROUND 2 REVIEW
# ============================================================

def test_remaining_problems_continue_to_next_round(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    review_df = (
        round_1[
            "review_data"
        ]
    )

    row = get_review_row(
        review_df,
        2
    )

    assert (
        "Customer_Email"
        in review_df.columns
    )

    assert (
        "Quantity"
        in review_df.columns
    )

    assert (
        "Customer_Age"
        in review_df.columns
    )

    assert (
        row[
            "Customer_Email"
        ]
        == REVIEW_MISSING_MARKER
    )

    assert (
        str(
            row[
                "Quantity"
            ]
        )
        == "-5"
    )

    assert (
        str(
            row[
                "Customer_Age"
            ]
        )
        == "452"
    )


# ============================================================
# 14. ROUND 2 USES PREVIOUS CORRECTED DATA
# ============================================================

def test_round_2_preserves_round_1_correction(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    row = (
        round_2[
            "corrected_data"
        ][
            round_2[
                "corrected_data"
            ][
                "Record_ID"
            ] == 2
        ]
        .iloc[0]
    )

    # Category was fixed in round 1 and must survive
    # the second remediation round.
    assert (
        row[
            "Category"
        ]
        == "Books"
    )


# ============================================================
# 15. ROUND 2 MERGES REMAINING CORRECTIONS
# ============================================================

def test_round_2_applies_remaining_corrections(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    row = (
        round_2[
            "corrected_data"
        ][
            round_2[
                "corrected_data"
            ][
                "Record_ID"
            ] == 2
        ]
        .iloc[0]
    )

    assert (
        row[
            "Customer_Email"
        ]
        == "riya.sen@example.com"
    )

    assert (
        row[
            "Quantity"
        ]
        == 2.0
    )

    assert (
        row[
            "Customer_Age"
        ]
        == 30
    )


# ============================================================
# 16. ALL CLEANING ISSUES RESOLVED AFTER ROUND 2
# ============================================================

def test_round_2_resolves_all_cleaning_issues(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    unresolved = (
        round_2[
            "unresolved_cleaning_issues"
        ]
    )

    assert unresolved.empty

    assert (
        round_2[
            "cleaning_score"
        ]
        == 100.0
    )


# ============================================================
# 17. VALIDATION REACHES 100 AFTER COMPLETE REMEDIATION
# ============================================================

def test_round_2_validation_reaches_100(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    assert (
        round_2[
            "validation_score"
        ]
        == 100.0
    )

    assert (
        round_2[
            "validation"
        ][
            "success"
        ]
        is True
    )


# ============================================================
# 18. EXPORT BECOMES ALLOWED
# ============================================================

def test_export_allowed_after_complete_remediation(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    assert (
        round_2[
            "cleaning_score"
        ]
        == 100.0
    )

    assert (
        round_2[
            "validation_score"
        ]
        == 100.0
    )

    assert (
        round_2[
            "export_allowed"
        ]
        is True
    )


# ============================================================
# 19. REVIEW DATASET EMPTY AFTER SUCCESS
# ============================================================

def test_review_dataset_empty_after_complete_remediation(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    review_df = (
        round_2[
            "review_data"
        ]
    )

    assert review_df.empty

    assert (
        review_df.columns.tolist()
        == [
            "Record_ID",
            "Order_ID"
        ]
    )


# ============================================================
# 20. PROBLEM MAP CLEARS AFTER SUCCESS
# ============================================================

def test_problem_map_empty_after_complete_remediation(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    problem_map = (
        round_2[
            "problem_map"
        ]
    )

    assert problem_map.empty


# ============================================================
# 21. REPORT CLEARS AFTER SUCCESS
# ============================================================

def test_report_empty_after_complete_remediation(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    assert (
        round_2[
            "report"
        ].empty
    )


# ============================================================
# 22. Record_ID REMAINS STABLE ACROSS ROUNDS
# ============================================================

def test_record_id_remains_stable_across_rounds(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    original_ids = (
        initial_result[
            "original_data"
        ][
            "Record_ID"
        ]
        .tolist()
    )

    corrected_ids = (
        round_2[
            "corrected_data"
        ][
            "Record_ID"
        ]
        .tolist()
    )

    assert (
        corrected_ids
        == original_ids
    )


# ============================================================
# 23. Order_ID REMAINS UNCHANGED
# ============================================================

def test_order_id_remains_unchanged_across_rounds(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    original_orders = (
        initial_result[
            "original_data"
        ][
            "Order_ID"
        ]
        .tolist()
    )

    corrected_orders = (
        round_2[
            "corrected_data"
        ][
            "Order_ID"
        ]
        .tolist()
    )

    assert (
        corrected_orders
        == original_orders
    )


# ============================================================
# 24. ORIGINAL SOURCE DATA IS NOT MUTATED
# ============================================================

def test_original_data_remains_unchanged(
    initial_result
):

    original_before = (
        initial_result[
            "original_data"
        ]
        .copy(deep=True)
    )

    round_1 = run_round_1(
        initial_result
    )

    run_round_2(
        round_1
    )

    pd.testing.assert_frame_equal(
        initial_result[
            "original_data"
        ],
        original_before
    )


# ============================================================
# 25. FINAL CORRECTED DATA CONTAINS ALL ROWS
# ============================================================

def test_remediation_does_not_remove_rows(
    initial_result
):

    round_1 = run_round_1(
        initial_result
    )

    round_2 = run_round_2(
        round_1
    )

    assert (
        len(
            round_2[
                "corrected_data"
            ]
        )
        ==
        len(
            initial_result[
                "cleaned_data"
            ]
        )
    )

import copy

import pandas as pd
import pytest

from pipeline.cleaner import clean_data

from pipeline.review import (
    merge_review_corrections,
)

from pipeline.orchestrator import (
    run_pipeline,
    apply_review_corrections,
)

from pipeline.exporter import (
    ExportBlockedError,
    prepare_export_data,
)


# ============================================================
# HELPERS
# ============================================================

def make_valid_raw_df():

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


def make_invalid_raw_df():

    df = make_valid_raw_df()

    df.loc[
        1,
        "Category"
    ] = "UNKNOWN"

    df.loc[
        1,
        "Quantity"
    ] = "-5"

    df.loc[
        1,
        "Customer_Age"
    ] = "452"

    return df


def add_record_id(
    df
):

    result = (
        df.copy()
    )

    result.insert(
        0,
        "Record_ID",
        range(
            1,
            len(result) + 1
        )
    )

    return result


@pytest.fixture
def remediation_result(
    tmp_path
):

    df = make_invalid_raw_df()

    file_path = (
        tmp_path
        / "remediation_failure_test.csv"
    )

    df.to_csv(
        file_path,
        index=False
    )

    return run_pipeline(
        str(file_path)
    )


# ============================================================
# 1. MISSING REQUIRED CSV COLUMN FAILS SAFELY
# ============================================================

def test_missing_required_column_fails_pipeline(
    tmp_path
):

    df = make_valid_raw_df()

    df = df.drop(
        columns=[
            "Customer_Email"
        ]
    )

    file_path = (
        tmp_path
        / "missing_column.csv"
    )

    df.to_csv(
        file_path,
        index=False
    )

    with pytest.raises(
        (
            KeyError,
            ValueError,
        )
    ):

        run_pipeline(
            str(file_path)
        )


# ============================================================
# 2. MULTIPLE MISSING COLUMNS FAIL SAFELY
# ============================================================

def test_multiple_missing_columns_fail_pipeline(
    tmp_path
):

    df = make_valid_raw_df()

    df = df.drop(
        columns=[
            "Category",
            "Product",
            "Order_Date",
        ]
    )

    file_path = (
        tmp_path
        / "multiple_missing_columns.csv"
    )

    df.to_csv(
        file_path,
        index=False
    )

    with pytest.raises(
        (
            KeyError,
            ValueError,
        )
    ):

        run_pipeline(
            str(file_path)
        )


# ============================================================
# 3. HEADER-ONLY CSV DOES NOT SILENTLY PRODUCE NORMAL RESULT
# ============================================================

def test_header_only_csv_does_not_behave_like_normal_dataset(
    tmp_path
):

    df = make_valid_raw_df().iloc[
        0:0
    ]

    file_path = (
        tmp_path
        / "header_only.csv"
    )

    df.to_csv(
        file_path,
        index=False
    )

    try:

        result = run_pipeline(
            str(file_path)
        )

    except Exception:

        return

    assert (
        result["summary"]["original_rows"]
        == 0
    )


# ============================================================
# 4. COMPLETELY EMPTY FILE FAILS
# ============================================================

def test_completely_empty_csv_fails(
    tmp_path
):

    file_path = (
        tmp_path
        / "empty.csv"
    )

    file_path.write_text(
        "",
        encoding="utf-8"
    )

    with pytest.raises(
        Exception
    ):

        run_pipeline(
            str(file_path)
        )


# ============================================================
# 5. NON-CSV TEXT FILE FAILS
# ============================================================

def test_non_csv_content_fails_safely(
    tmp_path
):

    file_path = (
        tmp_path
        / "broken.csv"
    )

    file_path.write_text(
        "this is not a valid retail csv",
        encoding="utf-8"
    )

    with pytest.raises(
        Exception
    ):

        run_pipeline(
            str(file_path)
        )


# ============================================================
# 6. MISSING Record_ID IN CORRECTED REVIEW FAILS
# ============================================================

def test_corrected_review_missing_record_id_fails(
    remediation_result
):

    review_df = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    corrected_review = (
        review_df.drop(
            columns=[
                "Record_ID"
            ]
        )
    )

    with pytest.raises(
        ValueError,
        match="Corrected review dataset is missing"
    ):

        apply_review_corrections(
            remediation_result,
            corrected_review
        )


# ============================================================
# 7. MISSING Order_ID IN CORRECTED REVIEW FAILS
# ============================================================

def test_corrected_review_missing_order_id_fails(
    remediation_result
):

    review_df = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    corrected_review = (
        review_df.drop(
            columns=[
                "Order_ID"
            ]
        )
    )

    with pytest.raises(
        ValueError,
        match="Corrected review dataset is missing"
    ):

        apply_review_corrections(
            remediation_result,
            corrected_review
        )


# ============================================================
# 8. DUPLICATE Record_ID IN CORRECTED REVIEW FAILS
# ============================================================

def test_duplicate_record_id_in_corrected_review_fails(
    remediation_result
):

    review_df = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    duplicate_row = (
        review_df.iloc[
            [0]
        ]
        .copy()
    )

    corrected_review = pd.concat(
        [
            review_df,
            duplicate_row,
        ],
        ignore_index=True
    )

    with pytest.raises(
        ValueError,
        match="duplicate Record_ID"
    ):

        apply_review_corrections(
            remediation_result,
            corrected_review
        )


# ============================================================
# 9. UNKNOWN CORRECTION COLUMN FAILS
# ============================================================

def test_unknown_correction_column_fails(
    remediation_result
):

    corrected_review = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    corrected_review[
        "Unknown_Field"
    ] = "test"

    with pytest.raises(
        ValueError,
        match="Unknown columns"
    ):

        apply_review_corrections(
            remediation_result,
            corrected_review
        )


# ============================================================
# 10. REVIEW WITH ONLY IDENTIFIERS FAILS
# ============================================================

def test_review_with_no_correction_columns_fails(
    remediation_result
):

    corrected_review = (
        remediation_result[
            "review_data"
        ][
            [
                "Record_ID",
                "Order_ID",
            ]
        ]
        .copy()
    )

    with pytest.raises(
        ValueError,
        match="No correction columns found"
    ):

        apply_review_corrections(
            remediation_result,
            corrected_review
        )


# ============================================================
# 11. INVALID INTEGER CORRECTION IS IGNORED SAFELY
# ============================================================

def test_invalid_integer_correction_does_not_corrupt_data(
    remediation_result
):

    review_df = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    if (
        "Customer_Age"
        not in review_df.columns
    ):

        pytest.skip(
            "Customer_Age is not present in review data."
        )

    corrected_review = (
        review_df.copy()
    )

    mask = (
        corrected_review[
            "Record_ID"
        ] == 2
    )

    corrected_review.loc[
        mask,
        "Customer_Age"
    ] = "abc"

    before = (
        remediation_result[
            "cleaned_data"
        ]
        .copy(
            deep=True
        )
    )

    result = apply_review_corrections(
        remediation_result,
        corrected_review
    )

    corrected_df = (
        result[
            "corrected_data"
        ]
    )

    before_row = (
        before[
            before[
                "Record_ID"
            ] == 2
        ][
            "Customer_Age"
        ]
        .iloc[0]
    )

    after_row = (
        corrected_df[
            corrected_df[
                "Record_ID"
            ] == 2
        ][
            "Customer_Age"
        ]
        .iloc[0]
    )

    if pd.isna(
        before_row
    ):

        assert pd.isna(
            after_row
        )

    else:

        assert (
            after_row
            == before_row
        )


# ============================================================
# 12. INVALID FLOAT CORRECTION IS IGNORED SAFELY
# ============================================================

def test_invalid_float_correction_does_not_corrupt_data(
    remediation_result
):

    review_df = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    if (
        "Quantity"
        not in review_df.columns
    ):

        pytest.skip(
            "Quantity is not present in review data."
        )

    corrected_review = (
        review_df.copy()
    )

    mask = (
        corrected_review[
            "Record_ID"
        ] == 2
    )

    corrected_review.loc[
        mask,
        "Quantity"
    ] = "not-a-number"

    result = apply_review_corrections(
        remediation_result,
        corrected_review
    )

    corrected_df = (
        result[
            "corrected_data"
        ]
    )

    value = (
        corrected_df[
            corrected_df[
                "Record_ID"
            ] == 2
        ][
            "Quantity"
        ]
        .iloc[0]
    )

    assert pd.isna(
        value
    )


# ============================================================
# 13. INVALID DATE CORRECTION IS IGNORED SAFELY
# ============================================================

def test_invalid_date_correction_is_ignored():

    raw = make_valid_raw_df()

    original = add_record_id(
        raw
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

            "Order_Date": [
                "bad-date"
            ],
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [
                1
            ],

            "Order_ID": [
                "ORD-00001"
            ],

            "Order_Date": [
                "still-not-a-date"
            ],
        }
    )

    before = (
        cleaned.copy(
            deep=True
        )
    )

    corrected_df, summary = (
        merge_review_corrections(
            cleaned,
            original_review,
            corrected_review
        )
    )

    pd.testing.assert_frame_equal(
        corrected_df,
        before
    )

    assert (
        summary[
            "corrections_applied"
        ]
        == 0
    )


# ============================================================
# 14. BLANK CORRECTION IS IGNORED
# ============================================================

def test_blank_correction_is_ignored(
    remediation_result
):

    review_df = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    corrected_review = (
        review_df.copy()
    )

    correction_columns = [
        column
        for column
        in corrected_review.columns
        if column not in {
            "Record_ID",
            "Order_ID",
        }
    ]

    assert correction_columns

    target_column = (
        correction_columns[
            0
        ]
    )

    corrected_review.loc[
        0,
        target_column
    ] = ""

    result = apply_review_corrections(
        remediation_result,
        corrected_review
    )

    assert (
        result[
            "merge_summary"
        ][
            "corrections_applied"
        ]
        == 0
    )


# ============================================================
# 15. UNCHANGED REVIEW DOES NOTHING
# ============================================================

def test_unchanged_review_does_not_modify_data(
    remediation_result
):

    corrected_review = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    before = (
        remediation_result[
            "cleaned_data"
        ]
        .copy(
            deep=True
        )
    )

    result = apply_review_corrections(
        remediation_result,
        corrected_review
    )

    pd.testing.assert_frame_equal(
        result[
            "corrected_data"
        ],
        before
    )

    assert (
        result[
            "merge_summary"
        ][
            "corrections_applied"
        ]
        == 0
    )


# ============================================================
# 16. UNKNOWN Record_ID IS IGNORED
# ============================================================

def test_unknown_record_id_is_ignored(
    remediation_result
):

    corrected_review = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    corrected_review.loc[
        corrected_review.index[0],
        "Record_ID"
    ] = 999999

    before = (
        remediation_result[
            "cleaned_data"
        ]
        .copy(
            deep=True
        )
    )

    result = apply_review_corrections(
        remediation_result,
        corrected_review
    )

    pd.testing.assert_frame_equal(
        result[
            "corrected_data"
        ],
        before
    )


# ============================================================
# 17. FAILED CORRECTION DOES NOT MUTATE PIPELINE RESULT
# ============================================================

def test_failed_correction_does_not_mutate_pipeline_result(
    remediation_result
):

    original_cleaned = (
        remediation_result[
            "cleaned_data"
        ]
        .copy(
            deep=True
        )
    )

    original_review = (
        remediation_result[
            "review_data"
        ]
        .copy(
            deep=True
        )
    )

    bad_review = (
        original_review.drop(
            columns=[
                "Record_ID"
            ]
        )
    )

    with pytest.raises(
        ValueError
    ):

        apply_review_corrections(
            remediation_result,
            bad_review
        )

    pd.testing.assert_frame_equal(
        remediation_result[
            "cleaned_data"
        ],
        original_cleaned
    )

    pd.testing.assert_frame_equal(
        remediation_result[
            "review_data"
        ],
        original_review
    )


# ============================================================
# 18. DUPLICATE-ID FAILURE DOES NOT MUTATE STATE
# ============================================================

def test_duplicate_record_id_failure_preserves_state(
    remediation_result
):

    original_result = {
        "cleaned_data":
            remediation_result[
                "cleaned_data"
            ].copy(
                deep=True
            ),

        "review_data":
            remediation_result[
                "review_data"
            ].copy(
                deep=True
            ),
    }

    corrected_review = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    corrected_review = pd.concat(
        [
            corrected_review,
            corrected_review.iloc[
                [0]
            ],
        ],
        ignore_index=True
    )

    with pytest.raises(
        ValueError
    ):

        apply_review_corrections(
            remediation_result,
            corrected_review
        )

    pd.testing.assert_frame_equal(
        remediation_result[
            "cleaned_data"
        ],
        original_result[
            "cleaned_data"
        ]
    )

    pd.testing.assert_frame_equal(
        remediation_result[
            "review_data"
        ],
        original_result[
            "review_data"
        ]
    )


# ============================================================
# 19. BLOCKED DATASET CANNOT EXPORT
# ============================================================

def test_blocked_pipeline_cannot_export(
    remediation_result
):

    assert (
        remediation_result[
            "export_allowed"
        ]
        is False
    )

    with pytest.raises(
        ExportBlockedError
    ):

        prepare_export_data(
            remediation_result
        )


# ============================================================
# 20. FAILED EXPORT DOES NOT MUTATE CLEANED DATA
# ============================================================

def test_failed_export_preserves_pipeline_data(
    remediation_result
):

    before = (
        remediation_result[
            "cleaned_data"
        ]
        .copy(
            deep=True
        )
    )

    with pytest.raises(
        ExportBlockedError
    ):

        prepare_export_data(
            remediation_result
        )

    pd.testing.assert_frame_equal(
        remediation_result[
            "cleaned_data"
        ],
        before
    )


# ============================================================
# 21. BAD CORRECTION COLUMN DOES NOT MODIFY DATA
# ============================================================

def test_unknown_column_failure_preserves_data(
    remediation_result
):

    before = (
        remediation_result[
            "cleaned_data"
        ]
        .copy(
            deep=True
        )
    )

    corrected_review = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    corrected_review[
        "Fake_Column"
    ] = "bad"

    with pytest.raises(
        ValueError
    ):

        apply_review_corrections(
            remediation_result,
            corrected_review
        )

    pd.testing.assert_frame_equal(
        remediation_result[
            "cleaned_data"
        ],
        before
    )


# ============================================================
# 22. CORRECTED REVIEW MAY CONTAIN SUBSET OF ROWS
# ============================================================

def test_partial_review_upload_can_target_subset(
    remediation_result
):

    review_df = (
        remediation_result[
            "review_data"
        ]
    )

    corrected_review = (
        review_df.iloc[
            [0]
        ]
        .copy()
    )

    correction_columns = [
        column
        for column
        in corrected_review.columns
        if column not in {
            "Record_ID",
            "Order_ID",
        }
    ]

    assert correction_columns

    target_column = (
        correction_columns[
            0
        ]
    )

    original_value = (
        corrected_review.iloc[
            0
        ][
            target_column
        ]
    )

    corrected_review.loc[
        corrected_review.index[0],
        target_column
    ] = original_value

    result = apply_review_corrections(
        remediation_result,
        corrected_review
    )

    assert (
        result[
            "merge_summary"
        ][
            "corrections_received"
        ]
        == 1
    )


# ============================================================
# 23. ORIGINAL REVIEW DATASET MUST HAVE Record_ID
# ============================================================

def test_original_review_missing_record_id_fails():

    cleaned = (
        add_record_id(
            make_valid_raw_df()
        )
    )

    cleaned, _ = clean_data(
        cleaned
    )

    original_review = pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001"
            ],

            "Customer_Age": [
                "999"
            ],
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [
                1
            ],

            "Order_ID": [
                "ORD-00001"
            ],

            "Customer_Age": [
                "30"
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="Original review dataset is missing"
    ):

        merge_review_corrections(
            cleaned,
            original_review,
            corrected_review
        )


# ============================================================
# 24. CLEANED DATASET MUST HAVE Record_ID
# ============================================================

def test_cleaned_dataset_missing_record_id_fails():

    cleaned = (
        make_valid_raw_df()
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
                "999"
            ],
        }
    )

    corrected_review = pd.DataFrame(
        {
            "Record_ID": [
                1
            ],

            "Order_ID": [
                "ORD-00001"
            ],

            "Customer_Age": [
                "30"
            ],
        }
    )

    with pytest.raises(
        ValueError,
        match="Cleaned dataset must contain Record_ID"
    ):

        merge_review_corrections(
            cleaned,
            original_review,
            corrected_review
        )


# ============================================================
# 25. FAILED OPERATION LEAVES ORIGINAL RESULT REUSABLE
# ============================================================

def test_pipeline_result_reusable_after_failed_correction(
    remediation_result
):

    bad_review = (
        remediation_result[
            "review_data"
        ]
        .drop(
            columns=[
                "Record_ID"
            ]
        )
    )

    with pytest.raises(
        ValueError
    ):

        apply_review_corrections(
            remediation_result,
            bad_review
        )

    # --------------------------------------------------------
    # NOW PERFORM A VALID CORRECTION
    # --------------------------------------------------------

    corrected_review = (
        remediation_result[
            "review_data"
        ]
        .copy()
    )

    if (
        "Category"
        in corrected_review.columns
    ):

        mask = (
            corrected_review[
                "Record_ID"
            ] == 2
        )

        corrected_review.loc[
            mask,
            "Category"
        ] = "Books"

    result = apply_review_corrections(
        remediation_result,
        corrected_review
    )

    assert (
        "corrected_data"
        in result
    )

    assert (
        result[
            "merge_summary"
        ][
            "corrections_applied"
        ]
        >= 1
    )

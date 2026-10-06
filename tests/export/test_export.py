import io

import pandas as pd
import pytest

from pipeline.orchestrator import (
    run_pipeline,
    apply_review_corrections,
)

from pipeline.exporter import (
    ExportBlockedError,
    get_export_source,
    validate_export_gate,
    prepare_export_data,
    create_export_csv,
)


# ============================================================
# TEST DATA
# ============================================================

def make_valid_dataset():

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


def make_invalid_dataset():

    df = make_valid_dataset()

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


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def valid_result(
    tmp_path
):

    df = make_valid_dataset()

    path = (
        tmp_path
        / "valid_export.csv"
    )

    df.to_csv(
        path,
        index=False
    )

    return run_pipeline(
        str(path)
    )


@pytest.fixture
def blocked_result(
    tmp_path
):

    df = make_invalid_dataset()

    path = (
        tmp_path
        / "blocked_export.csv"
    )

    df.to_csv(
        path,
        index=False
    )

    return run_pipeline(
        str(path)
    )


# ============================================================
# 1. VALID PIPELINE PASSES EXPORT GATE
# ============================================================

def test_valid_pipeline_passes_export_gate(
    valid_result
):

    assert (
        validate_export_gate(
            valid_result
        )
        is True
    )


# ============================================================
# 2. BLOCKED PIPELINE CANNOT EXPORT
# ============================================================

def test_invalid_pipeline_cannot_export(
    blocked_result
):

    with pytest.raises(
        ExportBlockedError
    ):

        validate_export_gate(
            blocked_result
        )


# ============================================================
# 3. CLEANING SCORE BELOW 100 BLOCKS EXPORT
# ============================================================

def test_cleaning_score_below_100_blocks_export():

    result = {
        "cleaning_score": 99.99,
        "validation_score": 100.0,
        "validation": {
            "success": True
        },
        "export_allowed": True,
        "cleaned_data": pd.DataFrame(
            {
                "Record_ID": [1],
                "A": [10],
            }
        ),
    }

    with pytest.raises(
        ExportBlockedError
    ):

        prepare_export_data(
            result
        )


# ============================================================
# 4. VALIDATION SCORE BELOW 100 BLOCKS EXPORT
# ============================================================

def test_validation_score_below_100_blocks_export():

    result = {
        "cleaning_score": 100.0,
        "validation_score": 99.99,
        "validation": {
            "success": True
        },
        "export_allowed": True,
        "cleaned_data": pd.DataFrame(
            {
                "Record_ID": [1],
                "A": [10],
            }
        ),
    }

    with pytest.raises(
        ExportBlockedError
    ):

        prepare_export_data(
            result
        )


# ============================================================
# 5. VALIDATION FAILURE BLOCKS EXPORT
# ============================================================

def test_validation_success_false_blocks_export():

    result = {
        "cleaning_score": 100.0,
        "validation_score": 100.0,
        "validation": {
            "success": False
        },
        "export_allowed": True,
        "cleaned_data": pd.DataFrame(
            {
                "Record_ID": [1],
                "A": [10],
            }
        ),
    }

    with pytest.raises(
        ExportBlockedError
    ):

        prepare_export_data(
            result
        )


# ============================================================
# 6. EXPORT_ALLOWED FALSE BLOCKS EXPORT
# ============================================================

def test_export_allowed_false_blocks_export():

    result = {
        "cleaning_score": 100.0,
        "validation_score": 100.0,
        "validation": {
            "success": True
        },
        "export_allowed": False,
        "cleaned_data": pd.DataFrame(
            {
                "Record_ID": [1],
                "A": [10],
            }
        ),
    }

    with pytest.raises(
        ExportBlockedError
    ):

        prepare_export_data(
            result
        )


# ============================================================
# 7. INITIAL PIPELINE USES CLEANED DATA
# ============================================================

def test_initial_pipeline_uses_cleaned_data(
    valid_result
):

    source = (
        get_export_source(
            valid_result
        )
    )

    assert (
        source
        is valid_result[
            "cleaned_data"
        ]
    )


# ============================================================
# 8. CORRECTED DATA TAKES PRIORITY
# ============================================================

def test_corrected_data_has_priority():

    cleaned_df = pd.DataFrame(
        {
            "Record_ID": [1],
            "Value": ["old"],
        }
    )

    corrected_df = pd.DataFrame(
        {
            "Record_ID": [1],
            "Value": ["new"],
        }
    )

    result = {
        "cleaned_data":
            cleaned_df,

        "corrected_data":
            corrected_df,
    }

    source = (
        get_export_source(
            result
        )
    )

    assert source is corrected_df


# ============================================================
# 9. Record_ID REMOVED FROM FINAL EXPORT
# ============================================================

def test_record_id_removed_from_export(
    valid_result
):

    export_df = (
        prepare_export_data(
            valid_result
        )
    )

    assert (
        "Record_ID"
        not in export_df.columns
    )


# ============================================================
# 10. BUSINESS Order_ID REMAINS
# ============================================================

def test_order_id_remains_in_export(
    valid_result
):

    export_df = (
        prepare_export_data(
            valid_result
        )
    )

    assert (
        "Order_ID"
        in export_df.columns
    )


# ============================================================
# 11. FINAL EXPORT HAS ORIGINAL BUSINESS COLUMN COUNT
# ============================================================

def test_export_has_15_business_columns(
    valid_result
):

    export_df = (
        prepare_export_data(
            valid_result
        )
    )

    assert len(
        export_df.columns
    ) == 15


# ============================================================
# 12. EXPORT ROW COUNT MATCHES CLEANED DATA
# ============================================================

def test_export_row_count_matches_source(
    valid_result
):

    export_df = (
        prepare_export_data(
            valid_result
        )
    )

    source_df = (
        valid_result[
            "cleaned_data"
        ]
    )

    assert (
        len(export_df)
        == len(source_df)
    )


# ============================================================
# 13. EXPORT DOES NOT MUTATE PIPELINE DATA
# ============================================================

def test_export_does_not_mutate_source(
    valid_result
):

    source_before = (
        valid_result[
            "cleaned_data"
        ]
        .copy(
            deep=True
        )
    )

    prepare_export_data(
        valid_result
    )

    pd.testing.assert_frame_equal(
        valid_result[
            "cleaned_data"
        ],
        source_before
    )


# ============================================================
# 14. INTERNAL Record_ID REMAINS INSIDE PIPELINE
# ============================================================

def test_record_id_stays_inside_pipeline_after_export(
    valid_result
):

    prepare_export_data(
        valid_result
    )

    assert (
        "Record_ID"
        in valid_result[
            "cleaned_data"
        ].columns
    )


# ============================================================
# 15. CSV OUTPUT DOES NOT CONTAIN Record_ID
# ============================================================

def test_csv_output_does_not_contain_record_id(
    valid_result
):

    csv_bytes = (
        create_export_csv(
            valid_result
        )
    )

    csv_text = (
        csv_bytes.decode(
            "utf-8"
        )
    )

    header = (
        csv_text
        .splitlines()[0]
    )

    assert (
        "Record_ID"
        not in header
    )


# ============================================================
# 16. CSV OUTPUT CAN BE READ AGAIN
# ============================================================

def test_export_csv_can_be_loaded_again(
    valid_result
):

    csv_bytes = (
        create_export_csv(
            valid_result
        )
    )

    exported_df = (
        pd.read_csv(
            io.BytesIO(
                csv_bytes
            )
        )
    )

    assert len(
        exported_df
    ) == 2

    assert (
        "Record_ID"
        not in exported_df.columns
    )

    assert (
        "Order_ID"
        in exported_df.columns
    )


# ============================================================
# 17. CSV EXPORT DOES NOT WRITE PANDAS INDEX
# ============================================================

def test_csv_export_does_not_write_dataframe_index(
    valid_result
):

    csv_bytes = (
        create_export_csv(
            valid_result
        )
    )

    exported_df = (
        pd.read_csv(
            io.BytesIO(
                csv_bytes
            )
        )
    )

    assert (
        "Unnamed: 0"
        not in exported_df.columns
    )


# ============================================================
# 18. MISSING DATAFRAME RAISES ERROR
# ============================================================

def test_missing_export_source_raises_error():

    result = {
        "cleaning_score": 100.0,
        "validation_score": 100.0,
        "validation": {
            "success": True
        },
        "export_allowed": True,
    }

    with pytest.raises(
        ValueError,
        match=(
            "cleaned_data "
            "or corrected_data"
        )
    ):

        prepare_export_data(
            result
        )


# ============================================================
# 19. INVALID PIPELINE RESULT TYPE
# ============================================================

def test_invalid_pipeline_result_type():

    with pytest.raises(
        ValueError,
        match=(
            "pipeline_result must "
            "be a dictionary"
        )
    ):

        prepare_export_data(
            None
        )


# ============================================================
# 20. INITIAL VALID PIPELINE EXPORT STATUS READY
# ============================================================

def test_initial_valid_pipeline_is_ready(
    valid_result
):

    assert (
        valid_result[
            "export_allowed"
        ]
        is True
    )

    assert (
        valid_result[
            "export_status"
        ]
        == "READY"
    )


# ============================================================
# 21. BLOCKED RESULT CANNOT CREATE CSV
# ============================================================

def test_blocked_pipeline_cannot_create_csv(
    blocked_result
):

    with pytest.raises(
        ExportBlockedError
    ):

        create_export_csv(
            blocked_result
        )


# ============================================================
# 22. EXPORT PRESERVES BUSINESS VALUES
# ============================================================

def test_export_preserves_business_values(
    valid_result
):

    export_df = (
        prepare_export_data(
            valid_result
        )
    )

    source_df = (
        valid_result[
            "cleaned_data"
        ]
        .drop(
            columns=[
                "Record_ID"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    pd.testing.assert_frame_equal(
        export_df,
        source_df
    )

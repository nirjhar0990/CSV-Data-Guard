import pandas as pd

from pipeline.reporting import (
    create_validation_report,
    REPORT_COLUMNS,
)


# ============================================================
# HELPERS
# ============================================================

def make_original_df():

    return pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001",
                "ORD-00002",
                "ORD-00003",
                "ORD-00004"
            ]
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
# 1. EMPTY PROBLEM MAP
# ============================================================

def test_create_validation_report_empty_problem_map():

    original_df = make_original_df()

    problem_map = pd.DataFrame(
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

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert result.empty

    assert result.columns.tolist() == REPORT_COLUMNS


# ============================================================
# 2. NONE PROBLEM MAP
# ============================================================

def test_create_validation_report_none_problem_map():

    original_df = make_original_df()

    result = create_validation_report(
        None,
        original_df
    )

    assert result.empty

    assert result.columns.tolist() == REPORT_COLUMNS


# ============================================================
# 3. SINGLE ISSUE
# ============================================================

def test_single_issue_report():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Category",
                "Invalid category",
                "Use one of the allowed product categories.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 1

    row = result.iloc[0]

    assert row["Field"] == "Category"

    assert (
        row["Validation Error"]
        == "Invalid category"
    )

    assert (
        row["Records Affected"]
        == 1
    )

    assert (
        row["Affected Order IDs"]
        == "ORD-00001"
    )

    assert (
        row["How to Fix"]
        == "Use one of the allowed product categories."
    )


# ============================================================
# 4. SAME ISSUE GROUPS TOGETHER
# ============================================================

def test_same_issue_is_grouped():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Category",
                "Invalid category",
                "Use one of the allowed product categories.",
                "cleaning",
                True,
                True
            ],

            [
                1,
                "Category",
                "Invalid category",
                "Use one of the allowed product categories.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 1

    row = result.iloc[0]

    assert row["Records Affected"] == 2

    assert (
        row["Affected Order IDs"]
        == "ORD-00001, ORD-00002"
    )


# ============================================================
# 5. UNIQUE ORDER IDs ONLY
# ============================================================

def test_duplicate_order_ids_count_once():

    original_df = pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001",
                "ORD-00001",
                "ORD-00002"
            ]
        }
    )

    problem_map = make_problem_map(
        [
            [
                0,
                "Category",
                "Invalid category",
                "Use one of the allowed product categories.",
                "cleaning",
                True,
                True
            ],

            [
                1,
                "Category",
                "Invalid category",
                "Use one of the allowed product categories.",
                "validation",
                True,
                True
            ],

            [
                2,
                "Category",
                "Invalid category",
                "Use one of the allowed product categories.",
                "validation",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 1

    row = result.iloc[0]

    assert row["Records Affected"] == 2

    assert (
        row["Affected Order IDs"]
        == "ORD-00001, ORD-00002"
    )


# ============================================================
# 6. FIRST-SEEN ORDER ID ORDER IS PRESERVED
# ============================================================

def test_order_id_encounter_order_is_preserved():

    original_df = pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00003",
                "ORD-00001",
                "ORD-00002"
            ]
        }
    )

    problem_map = make_problem_map(
        [
            [
                0,
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
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ],

            [
                2,
                "Category",
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert (
        result.iloc[0]["Affected Order IDs"]
        == "ORD-00003, ORD-00001, ORD-00002"
    )


# ============================================================
# 7. DIFFERENT ERRORS FORM DIFFERENT REPORT ROWS
# ============================================================

def test_different_errors_are_separate_groups():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Discount",
                "Discount is below the allowed range",
                "Set discount between 0 and 100.",
                "validation",
                True,
                True
            ],

            [
                1,
                "Discount",
                "Discount is above the allowed range",
                "Set discount between 0 and 100.",
                "validation",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 2

    errors = set(
        result["Validation Error"]
        .tolist()
    )

    assert errors == {
        "Discount is below the allowed range",
        "Discount is above the allowed range"
    }


# ============================================================
# 8. DIFFERENT HOW-TO-FIX VALUES FORM DIFFERENT GROUPS
# ============================================================

def test_different_fix_text_creates_separate_groups():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Category",
                "Invalid category",
                "Fix option A.",
                "cleaning",
                True,
                True
            ],

            [
                1,
                "Category",
                "Invalid category",
                "Fix option B.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 2


# ============================================================
# 9. FULL PROBLEM MAP IS USED
# ============================================================

def test_report_uses_full_problem_map_not_only_reportable_rows():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Customer_Email",
                "Invalid email syntax",
                "Enter a valid email address.",
                "email",
                True,
                False
            ],

            [
                1,
                "Customer_Email",
                "Validation failed",
                "Review and correct the value.",
                "validation",
                False,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    # Current locked reporting semantics use the FULL
    # shared problem map, including reportable=False rows.
    assert len(result) == 2

    errors = set(
        result["Validation Error"]
        .tolist()
    )

    assert errors == {
        "Invalid email syntax",
        "Validation failed"
    }


# ============================================================
# 10. DIFFERENT FIELDS ARE SEPARATE GROUPS
# ============================================================

def test_different_fields_are_separate_groups():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Category",
                "Validation failed",
                "Review and correct the value.",
                "validation",
                True,
                True
            ],

            [
                1,
                "Product",
                "Validation failed",
                "Review and correct the value.",
                "validation",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 2

    assert set(
        result["Field"].tolist()
    ) == {
        "Category",
        "Product"
    }


# ============================================================
# 11. MISSING ORDER ID DOES NOT COUNT
# ============================================================

def test_missing_order_id_not_counted():

    original_df = pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001",
                pd.NA,
                "ORD-00003"
            ]
        }
    )

    problem_map = make_problem_map(
        [
            [
                0,
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
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ],

            [
                2,
                "Category",
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    row = result.iloc[0]

    assert row["Records Affected"] == 2

    assert (
        row["Affected Order IDs"]
        == "ORD-00001, ORD-00003"
    )


# ============================================================
# 12. INVALID SOURCE INDEX IS IGNORED
# ============================================================

def test_invalid_problem_map_index_is_ignored():

    original_df = make_original_df()

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

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 1

    row = result.iloc[0]

    assert row["Records Affected"] == 0
    assert row["Affected Order IDs"] == ""


# ============================================================
# 13. REQUIRED OUTPUT COLUMNS
# ============================================================

def test_report_has_required_columns():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Category",
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert result.columns.tolist() == [
        "Field",
        "Validation Error",
        "Records Affected",
        "Affected Order IDs",
        "How to Fix"
    ]


# ============================================================
# 14. REPORT IS SORTED BY FIELD + VALIDATION ERROR
# ============================================================

def test_report_sort_order():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Product",
                "Invalid product",
                "Fix product.",
                "cleaning",
                True,
                True
            ],

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
                "Category",
                "Another category error",
                "Fix category.",
                "validation",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert result["Field"].tolist() == [
        "Category",
        "Category",
        "Product"
    ]

    assert result.iloc[0]["Validation Error"] == (
        "Another category error"
    )

    assert result.iloc[1]["Validation Error"] == (
        "Invalid category"
    )


# ============================================================
# 15. MULTIPLE SOURCES CAN MERGE INTO ONE REPORT GROUP
# ============================================================

def test_multiple_sources_merge_when_issue_is_identical():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
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
                "Invalid category",
                "Fix category.",
                "validation",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 1

    assert result.iloc[0]["Records Affected"] == 2

    assert (
        result.iloc[0]["Affected Order IDs"]
        == "ORD-00001, ORD-00002"
    )


# ============================================================
# 16. DUPLICATE PROBLEM MAP ROW DOES NOT DOUBLE COUNT
# ============================================================

def test_duplicate_problem_map_rows_do_not_double_count():

    original_df = make_original_df()

    problem_map = make_problem_map(
        [
            [
                0,
                "Category",
                "Invalid category",
                "Fix category.",
                "cleaning",
                True,
                True
            ],

            [
                0,
                "Category",
                "Invalid category",
                "Fix category.",
                "validation",
                True,
                True
            ]
        ]
    )

    result = create_validation_report(
        problem_map,
        original_df
    )

    assert len(result) == 1

    assert (
        result.iloc[0]["Records Affected"]
        == 1
    )

    assert (
        result.iloc[0]["Affected Order IDs"]
        == "ORD-00001"
    )

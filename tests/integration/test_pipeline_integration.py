import pandas as pd

from pipeline.profiler import profile_data
from pipeline.cleaner import clean_data

from pipeline.validator import (
    validate_data,
    calculate_validation_score,
    calculate_cleaning_score,
    find_unresolved_cleaning_issues,
)

from pipeline.problem_map import create_problem_map

from pipeline.reporting import (
    create_validation_report,
    REPORT_COLUMNS,
)

from pipeline.review import (
    create_review_dataset,
    REVIEW_MISSING_MARKER,
)

from pipeline.orchestrator import (
    run_pipeline_from_dataframe,
    apply_review_corrections,
)


# ============================================================
# TEST DATA
# ============================================================

def make_raw_dataset():
    """
    Small integration dataset containing:

    Row 0:
        Completely valid data.

    Row 1:
        Messy but safely repairable data.

    Row 2:
        Values that cannot be safely repaired and therefore
        must flow into unresolved issues / validation /
        problem map / report / review dataset.
    """

    return pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001",
                "ORD-00002",
                "ORD-00003",
            ],

            "Customer_Name": [
                "Arun Das",
                "Riya Sen",
                "Amit Roy",
            ],

            "Customer_Email": [
                "arun.das@example.com",
                "RIYA.SEN@EXAMPL.COM",
                "amit.roy@example.com",
            ],

            "City": [
                "Kolkata",
                "  kolkata  ",
                "Howrah",
            ],

            "Category": [
                "Electronics",
                "electronics",
                "UNKNOWN",
            ],

            "Product": [
                "Laptop",
                "laptop",
                "Laptop",
            ],

            "Quantity": [
                "1",
                "2",
                "-5",
            ],

            "Unit_Price": [
                "50000",
                "1000",
                "2000",
            ],

            "Discount": [
                "10",
                "5",
                "10",
            ],

            "Total_Amount": [
                "45000",
                "1900",
                "1800",
            ],

            "Order_Date": [
                "2026-01-01",
                "2026/02/01",
                "2026-03-01",
            ],

            "Payment_Method": [
                "Credit Card",
                "upi",
                "Cash",
            ],

            "Order_Status": [
                "Completed",
                "pending",
                "Completed",
            ],

            "Customer_Age": [
                "35",
                "4@6",
                "452",
            ],

            "Customer_Rating": [
                "5",
                "4",
                "-1",
            ],
        }
    )


# ============================================================
# PIPELINE HELPER
# ============================================================

def run_test_pipeline():
    """
    Run the same main production flow used by CSV Data Guard.

    Raw
      -> Profile
      -> Record_ID
      -> Clean
      -> Unresolved detection
      -> Validate
      -> Scores
      -> Problem Map
      -> Report
      -> Review Dataset
    """

    # --------------------------------------------------------
    # 1. RAW DATA
    # --------------------------------------------------------

    raw_df = make_raw_dataset()

    # --------------------------------------------------------
    # 2. PROFILE
    # --------------------------------------------------------

    profile = profile_data(
        raw_df
    )

    # --------------------------------------------------------
    # 3. PRESERVE ORIGINAL + ADD Record_ID
    # --------------------------------------------------------

    original_df = raw_df.copy()

    original_df.insert(
        0,
        "Record_ID",
        range(
            1,
            len(original_df) + 1
        )
    )

    # --------------------------------------------------------
    # 4. CLEAN
    # --------------------------------------------------------

    (
        cleaned_df,
        cleaning_checks
    ) = clean_data(
        original_df
    )

    # --------------------------------------------------------
    # 5. FIND UNRESOLVED CLEANING ISSUES
    # --------------------------------------------------------

    unresolved_issues = (
        find_unresolved_cleaning_issues(
            original_df,
            cleaned_df
        )
    )

    # --------------------------------------------------------
    # 6. VALIDATE
    # --------------------------------------------------------

    validation_result = (
        validate_data(
            cleaned_df
        )
    )

    failure_cases = (
        validation_result[
            "failure_cases"
        ]
    )

    # --------------------------------------------------------
    # 7. SCORES
    # --------------------------------------------------------

    initial_unresolved_count = (
        len(
            unresolved_issues
        )
    )

    cleaning_score = (
        calculate_cleaning_score(
            initial_unresolved_count,
            initial_unresolved_count
        )
    )

    validation_score = (
        calculate_validation_score(
            cleaned_df,
            failure_cases
        )
    )

    # --------------------------------------------------------
    # 8. PROBLEM MAP
    # --------------------------------------------------------

    problem_map = (
        create_problem_map(
            original_df,
            failure_cases,
            unresolved_issues
        )
    )

    # --------------------------------------------------------
    # 9. REPORT
    # --------------------------------------------------------

    report = (
        create_validation_report(
            problem_map,
            original_df
        )
    )

    # --------------------------------------------------------
    # 10. REVIEW DATASET
    # --------------------------------------------------------

    review_df = (
        create_review_dataset(
            original_df,
            cleaned_df,
            problem_map
        )
    )

    return {
        "raw_df": raw_df,
        "profile": profile,
        "original_df": original_df,
        "cleaned_df": cleaned_df,
        "cleaning_checks": cleaning_checks,
        "unresolved_issues": unresolved_issues,
        "validation_result": validation_result,
        "failure_cases": failure_cases,
        "cleaning_score": cleaning_score,
        "validation_score": validation_score,
        "problem_map": problem_map,
        "report": report,
        "review_df": review_df,
    }


# ============================================================
# 1. COMPLETE PIPELINE EXECUTES
# ============================================================

def test_complete_pipeline_executes():

    result = run_test_pipeline()

    assert result["raw_df"] is not None
    assert result["profile"] is not None
    assert result["cleaned_df"] is not None
    assert result["unresolved_issues"] is not None
    assert result["validation_result"] is not None
    assert result["problem_map"] is not None
    assert result["report"] is not None
    assert result["review_df"] is not None


# ============================================================
# 2. PROFILER -> CLEANER HANDOFF
# ============================================================

def test_profile_and_cleanerhandoff():

    result = run_test_pipeline()

    profile = result["profile"]

    assert profile["rows"] == 3
    assert profile["columns"] == 15

    assert result[
        "original_df"
    ].columns[0] == "Record_ID"

    assert result[
        "original_df"
    ]["Record_ID"].tolist() == [
        1,
        2,
        3
    ]


# ============================================================
# 3. REPAIRABLE ROW IS CLEANED
# ============================================================

def test_repairable_row_is_cleaned_correctly():

    result = run_test_pipeline()

    cleaned_df = result[
        "cleaned_df"
    ]

    row = cleaned_df.loc[1]

    assert (
        row["Customer_Email"]
        == "riya.sen@example.com"
    )

    assert (
        row["City"]
        == "Kolkata"
    )

    assert (
        row["Category"]
        == "Electronics"
    )

    assert (
        row["Product"]
        == "Laptop"
    )

    assert (
        row["Payment_Method"]
        == "UPI"
    )

    assert (
        row["Order_Status"]
        == "Pending"
    )

    assert (
        row["Customer_Age"]
        == 46
    )

    assert (
        row["Customer_Rating"]
        == 4
    )


# ============================================================
# 4. UNRESOLVED ISSUES FLOW OUT OF CLEANER
# ============================================================

def test_unresolved_issues_created_for_unrepairable_values():

    result = run_test_pipeline()

    unresolved = result[
        "unresolved_issues"
    ]

    assert not unresolved.empty

    row_2_issues = unresolved[
        unresolved["index"] == 2
    ]

    columns = set(
        row_2_issues[
            "column"
        ].tolist()
    )

    assert "Category" in columns
    assert "Quantity" in columns
    assert "Customer_Age" in columns
    assert "Customer_Rating" in columns


# ============================================================
# 5. ORIGINAL BAD VALUES ARE RETAINED
# ============================================================

def test_unresolved_issues_preserve_original_values():

    result = run_test_pipeline()

    unresolved = result[
        "unresolved_issues"
    ]

    age_issue = unresolved[
        (
            unresolved["index"] == 2
        )
        &
        (
            unresolved["column"]
            == "Customer_Age"
        )
    ]

    quantity_issue = unresolved[
        (
            unresolved["index"] == 2
        )
        &
        (
            unresolved["column"]
            == "Quantity"
        )
    ]

    assert len(age_issue) == 1
    assert len(quantity_issue) == 1

    assert (
        str(
            age_issue.iloc[0][
                "original_value"
            ]
        )
        == "452"
    )

    assert (
        str(
            quantity_issue.iloc[0][
                "original_value"
            ]
        )
        == "-5"
    )


# ============================================================
# 6. CLEANER -> VALIDATOR HANDOFF
# ============================================================

def test_cleaned_data_reaches_validator():

    result = run_test_pipeline()

    validation_result = result[
        "validation_result"
    ]

    assert validation_result[
        "success"
    ] is False

    failure_cases = result[
        "failure_cases"
    ]

    assert failure_cases is not None
    assert not failure_cases.empty


# ============================================================
# 7. REPAIRABLE ROW DOES NOT FAIL VALIDATION
# ============================================================

def test_repaired_row_passes_validation():

    result = run_test_pipeline()

    failure_cases = result[
        "failure_cases"
    ]

    failed_indexes = set(
        failure_cases[
            "index"
        ]
        .dropna()
        .tolist()
    )

    # Row index 1 contained messy-but-repairable data.
    assert 1 not in failed_indexes


# ============================================================
# 8. UNREPAIRABLE ROW FAILS VALIDATION
# ============================================================

def test_unrepairable_row_fails_validation():

    result = run_test_pipeline()

    failure_cases = result[
        "failure_cases"
    ]

    failed_indexes = set(
        failure_cases[
            "index"
        ]
        .dropna()
        .tolist()
    )

    assert 2 in failed_indexes


# ============================================================
# 9. SCORES ARE CONNECTED TO PIPELINE STATE
# ============================================================

def test_pipeline_scores():

    result = run_test_pipeline()

    # Initial remediation stage:
    # all unresolved cleaning issues are still outstanding.
    assert (
        result["cleaning_score"]
        == 0.0
    )

    validation_score = result[
        "validation_score"
    ]

    assert (
        0.0
        <= validation_score
        < 100.0
    )


# ============================================================
# 10. VALIDATOR -> PROBLEM MAP HANDOFF
# ============================================================

def test_problem_map_receives_pipeline_issues():

    result = run_test_pipeline()

    problem_map = result[
        "problem_map"
    ]

    assert not problem_map.empty

    required_columns = {
        "index",
        "column",
        "validation_error",
        "how_to_fix",
        "source",
        "reportable",
        "reviewable",
    }

    assert set(problem_map.columns) == required_columns

    assert 2 in set(
        problem_map["index"]
    )


# ============================================================
# 11. CLEANING ISSUES REACH PROBLEM MAP
# ============================================================

def test_cleaning_issues_reach_problem_map():

    result = run_test_pipeline()

    problem_map = result[
        "problem_map"
    ]

    cleaning_rows = problem_map[
        (
            problem_map["index"] == 2
        )
        &
        (
            problem_map["source"]
            == "cleaning"
        )
    ]

    assert not cleaning_rows.empty

    columns = set(
        cleaning_rows[
            "column"
        ].tolist()
    )

    assert "Category" in columns
    assert "Quantity" in columns
    assert "Customer_Age" in columns
    assert "Customer_Rating" in columns


# ============================================================
# 12. PROBLEM MAP -> REPORT HANDOFF
# ============================================================

def test_problem_map_generates_report():

    result = run_test_pipeline()

    report = result[
        "report"
    ]

    assert not report.empty

    assert (
        report.columns.tolist()
        == REPORT_COLUMNS
    )

    assert (
        report[
            "Records Affected"
        ].sum()
        > 0
    )


# ============================================================
# 13. REPORT REFERENCES CORRECT ORDER
# ============================================================

def test_report_contains_affected_order_id():

    result = run_test_pipeline()

    report = result[
        "report"
    ]

    combined_order_ids = " ".join(
        report[
            "Affected Order IDs"
        ]
        .astype(str)
        .tolist()
    )

    assert (
        "ORD-00003"
        in combined_order_ids
    )


# ============================================================
# 14. PROBLEM MAP -> REVIEW HANDOFF
# ============================================================

def test_problem_map_generates_sparse_review_dataset():

    result = run_test_pipeline()

    review_df = result[
        "review_df"
    ]

    assert not review_df.empty

    assert "Record_ID" in review_df.columns
    assert "Order_ID" in review_df.columns

    assert 3 in set(
        review_df[
            "Record_ID"
        ]
    )


# ============================================================
# 15. REVIEW PRESERVES ORIGINAL BAD VALUES
# ============================================================

def test_review_preserves_original_bad_values():

    result = run_test_pipeline()

    review_df = result[
        "review_df"
    ]

    row = review_df[
        review_df[
            "Record_ID"
        ] == 3
    ].iloc[0]

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

    assert (
        str(
            row["Customer_Rating"]
        )
        == "-1"
    )


# ============================================================
# 16. REPAIRED ROW DOES NOT ENTER REVIEW
# ============================================================

def test_successfully_repaired_row_not_in_review():

    result = run_test_pipeline()

    review_df = result[
        "review_df"
    ]

    assert 2 not in set(
        review_df[
            "Record_ID"
        ]
    )


# ============================================================
# 17. IDENTIFIERS REMAIN CONSISTENT
# ============================================================

def test_record_id_and_order_id_remain_consistent():

    result = run_test_pipeline()

    original_df = result[
        "original_df"
    ]

    cleaned_df = result[
        "cleaned_df"
    ]

    assert (
        cleaned_df.loc[
            2,
            "Record_ID"
        ]
        ==
        original_df.loc[
            2,
            "Record_ID"
        ]
    )

    assert (
        cleaned_df.loc[
            2,
            "Order_ID"
        ]
        ==
        original_df.loc[
            2,
            "Order_ID"
        ]
    )


# ============================================================
# 18. CLEANING CHECKS COMPLETE
# ============================================================

def test_cleaning_checks_pass_through_pipeline():

    result = run_test_pipeline()

    cleaning_checks = result[
        "cleaning_checks"
    ]

    assert cleaning_checks

    assert all(
        cleaning_checks.values()
    )


# ============================================================
# 19. MANUAL ORDER_ID CORRECTION MUST NOT CREATE A DUPLICATE
# ============================================================

def test_manual_order_id_correction_that_creates_duplicate_keeps_gate_closed():
    """
    A user may correct an invalid Order_ID with a value that is
    syntactically valid but already exists in another row.

    The corrected dataset must be revalidated and the export
    quality gate must remain closed.
    """

    raw_df = pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001",
                "BAD-ID",
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
                "Howrah",
            ],
            "Category": [
                "Electronics",
                "Electronics",
            ],
            "Product": [
                "Laptop",
                "Laptop",
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
                "30",
            ],
            "Customer_Rating": [
                "5",
                "4",
            ],
        }
    )

    result = run_pipeline_from_dataframe(
        raw_df
    )

    review_df = result[
        "review_data"
    ].copy()

    target_mask = (
        review_df[
            "Record_ID"
        ] == 2
    )

    assert target_mask.any()
    assert "Order_ID" in review_df.columns

    review_df.loc[
        target_mask,
        "Order_ID"
    ] = "ORD-00001"

    corrected_result = (
        apply_review_corrections(
            result,
            review_df
        )
    )

    corrected_df = corrected_result[
        "corrected_data"
    ]

    assert (
        corrected_df[
            "Order_ID"
        ]
        .duplicated(
            keep=False
        )
        .any()
    )

    assert (
        corrected_result[
            "validation"
        ][
            "success"
        ]
        is False
    )

    assert (
        corrected_result[
            "export_allowed"
        ]
        is False
    )


# ============================================================
# 20. A CORRECTION CAN INTRODUCE A NEW VALIDATION FAILURE
# ============================================================

def test_correction_that_replaces_missing_email_with_invalid_email_keeps_gate_closed():
    """
    Filling a required missing value is not enough if the new
    value violates another validation rule.

    Example:
        [MISSING] -> bad-email

    The correction round must detect the new validation failure
    and keep final export blocked.
    """

    raw_df = pd.DataFrame(
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
                "Electronics",
            ],
            "Product": [
                "Laptop",
                "Laptop",
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
                "30",
            ],
            "Customer_Rating": [
                "5",
                "4",
            ],
        }
    )

    result = run_pipeline_from_dataframe(
        raw_df
    )

    review_df = result[
        "review_data"
    ].copy()

    target_mask = (
        review_df[
            "Record_ID"
        ] == 2
    )

    assert target_mask.any()
    assert "Customer_Email" in review_df.columns

    original_review_value = (
        review_df.loc[
            target_mask,
            "Customer_Email"
        ].iloc[0]
    )

    assert (
        original_review_value
        == REVIEW_MISSING_MARKER
    )

    review_df.loc[
        target_mask,
        "Customer_Email"
    ] = "bad-email"

    corrected_result = (
        apply_review_corrections(
            result,
            review_df
        )
    )

    corrected_row = (
        corrected_result[
            "corrected_data"
        ]
        .loc[
            lambda df:
                df["Record_ID"] == 2
        ]
        .iloc[0]
    )

    assert (
        corrected_row[
            "Customer_Email"
        ]
        == "bad-email"
    )

    assert (
        corrected_result[
            "validation"
        ][
            "success"
        ]
        is False
    )

    failure_cases = (
        corrected_result[
            "validation"
        ][
            "failure_cases"
        ]
    )

    assert (
        failure_cases is not None
        and not failure_cases.empty
    )

    assert (
        "Customer_Email"
        in set(
            failure_cases[
                "column"
            ]
            .dropna()
            .tolist()
        )
    )

    assert (
        corrected_result[
            "validation_score"
        ]
        < 100.0
    )

    assert (
        corrected_result[
            "export_allowed"
        ]
        is False
    )

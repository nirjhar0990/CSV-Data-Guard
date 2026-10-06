import pandas as pd

from pipeline.validator import (
    validate_data,
    calculate_validation_score,
    find_unresolved_cleaning_issues,
    calculate_cleaning_score,
    classify_email_issues,
)


# ============================================================
# HELPER - FULLY VALID CLEANED DATAFRAME
# ============================================================

def make_valid_dataframe():

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
                "Arun Banerjee",
                "Riya Sen",
                "Amit Roy"
            ],

            "Customer_Email": [
                "arun.banerjee@example.com",
                "riya.sen@example.com",
                "amit.roy@example.com"
            ],

            "City": [
                "Kolkata",
                "Delhi",
                "Mumbai"
            ],

            "Category": [
                "Electronics",
                "Books",
                "Sports"
            ],

            "Product": [
                "Laptop",
                "Python Programming",
                "Football"
            ],

            "Quantity": [
                1.0,
                2.0,
                3.0
            ],

            "Unit_Price": [
                50000.0,
                700.0,
                1000.0
            ],

            "Discount": [
                10.0,
                20.0,
                0.0
            ],

            "Total_Amount": [
                45000.0,
                1120.0,
                3000.0
            ],

            "Order_Date": pd.to_datetime(
                [
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03"
                ]
            ),

            "Payment_Method": [
                "UPI",
                "Cash",
                "Credit Card"
            ],

            "Order_Status": [
                "Completed",
                "Pending",
                "Returned"
            ],

            "Customer_Age": pd.Series(
                [
                    30,
                    25,
                    40
                ],
                dtype="Int64"
            ),

            "Customer_Rating": pd.Series(
                [
                    5,
                    4,
                    3
                ],
                dtype="Int64"
            )
        }
    )


# ============================================================
# 1. VALID DATA SHOULD PASS
# ============================================================

def test_validate_data_valid_dataframe():

    df = make_valid_dataframe()

    result = validate_data(df)

    assert result["success"] is True

    assert result["failure_cases"] is None

    assert result["data"] is not None

    # Record_ID is internal and must not enter Pandera schema
    assert "Record_ID" not in result["data"].columns


# ============================================================
# 2. INVALID EMAIL SYNTAX
# ============================================================

def test_validate_data_invalid_email_syntax():

    df = make_valid_dataframe()

    df.loc[
        1,
        "Customer_Email"
    ] = "riya.sen*example.com"

    result = validate_data(df)

    assert result["success"] is False

    failure_cases = result["failure_cases"]

    assert failure_cases is not None
    assert not failure_cases.empty

    email_failures = failure_cases[
        failure_cases["column"]
        == "Customer_Email"
    ]

    assert not email_failures.empty

    assert 1 in (
        email_failures["index"]
        .dropna()
        .tolist()
    )


# ============================================================
# 3. INVALID EMAIL DOMAIN
# ============================================================

def test_validate_data_invalid_email_domain():

    df = make_valid_dataframe()

    df.loc[
        0,
        "Customer_Email"
    ] = "arun.banerjee@test.com"

    result = validate_data(df)

    assert result["success"] is False

    failure_cases = result["failure_cases"]

    email_failures = failure_cases[
        failure_cases["column"]
        == "Customer_Email"
    ]

    assert not email_failures.empty

    assert 0 in (
        email_failures["index"]
        .dropna()
        .tolist()
    )


# ============================================================
# 4. REQUIRED VALUE MISSING
# ============================================================

def test_validate_data_required_value_missing():

    df = make_valid_dataframe()

    df.loc[
        1,
        "Category"
    ] = pd.NA

    result = validate_data(df)

    assert result["success"] is False

    failure_cases = result["failure_cases"]

    category_failures = failure_cases[
        failure_cases["column"]
        == "Category"
    ]

    assert not category_failures.empty

    assert 1 in (
        category_failures["index"]
        .dropna()
        .tolist()
    )


# ============================================================
# 5. NUMERIC RANGE VALIDATION
# ============================================================

def test_validate_data_numeric_ranges():

    df = make_valid_dataframe()

    df.loc[
        0,
        "Quantity"
    ] = -1.0

    df.loc[
        1,
        "Discount"
    ] = 150.0

    df.loc[
        2,
        "Total_Amount"
    ] = -100.0

    result = validate_data(df)

    assert result["success"] is False

    failure_cases = result["failure_cases"]

    failed_columns = set(
        failure_cases[
            "column"
        ]
        .dropna()
        .tolist()
    )

    assert "Quantity" in failed_columns
    assert "Discount" in failed_columns
    assert "Total_Amount" in failed_columns


# ============================================================
# 6. VALIDATION SCORE - NO FAILURES
# ============================================================

def test_calculate_validation_score_no_failures():

    df = make_valid_dataframe()

    score = calculate_validation_score(
        df,
        None
    )

    assert score == 100.0


# ============================================================
# 7. VALIDATION SCORE COUNTS ROW ONCE
# ============================================================

def test_calculate_validation_score_unique_invalid_rows():

    df = make_valid_dataframe()

    failure_cases = pd.DataFrame(
        {
            "index": [
                0,
                0,
                1
            ],

            "column": [
                "Customer_Email",
                "Category",
                "Product"
            ]
        }
    )

    score = calculate_validation_score(
        df,
        failure_cases
    )

    # 3 total rows
    # Rows 0 and 1 invalid
    # Row 2 valid
    #
    # 1 / 3 = 33.33%
    assert score == 33.33


# ============================================================
# 8. VALIDATION SCORE - EMPTY DATASET
# ============================================================

def test_calculate_validation_score_empty_dataframe():

    df = pd.DataFrame()

    failure_cases = pd.DataFrame()

    score = calculate_validation_score(
        df,
        failure_cases
    )

    assert score == 100.0


# ============================================================
# 9. VALIDATION SCORE - DATASET LEVEL FAILURE
# ============================================================

def test_calculate_validation_score_dataset_level_failure():

    df = make_valid_dataframe()

    failure_cases = pd.DataFrame(
        {
            "index": [
                pd.NA
            ],

            "column": [
                "Some_Column"
            ]
        }
    )

    score = calculate_validation_score(
        df,
        failure_cases
    )

    assert score == 0.0


# ============================================================
# 10. CLEANING SCORE
# ============================================================

def test_calculate_cleaning_score():

    assert (
        calculate_cleaning_score(
            100,
            100
        )
        == 0.0
    )

    assert (
        calculate_cleaning_score(
            100,
            75
        )
        == 25.0
    )

    assert (
        calculate_cleaning_score(
            100,
            25
        )
        == 75.0
    )

    assert (
        calculate_cleaning_score(
            100,
            0
        )
        == 100.0
    )

    assert (
        calculate_cleaning_score(
            0,
            0
        )
        == 100.0
    )


# ============================================================
# 11. CLEANING SCORE SAFETY LIMITS
# ============================================================

def test_calculate_cleaning_score_safety_limits():

    # More current issues than initial:
    # score must not become negative.
    assert (
        calculate_cleaning_score(
            10,
            20
        )
        == 0.0
    )

    # Negative current count should never
    # cause score above 100.
    assert (
        calculate_cleaning_score(
            10,
            -5
        )
        == 100.0
    )


# ============================================================
# 12. FIND UNRESOLVED CLEANING ISSUES
# ============================================================

def test_find_unresolved_cleaning_issues():

    original_df = pd.DataFrame(
        {
            "Record_ID": [
                1,
                2,
                3,
                4
            ],

            "Order_ID": [
                "ORD-00001",
                "ORD-00002",
                "ORD-00003",
                "ORD-00004"
            ],

            "Customer_Name": [
                "Arun",
                "Riya",
                "Amit",
                "Sara"
            ],

            "Category": [
                "Electronics",
                "INVALID",
                "NA",
                ""
            ]
        }
    )

    cleaned_df = original_df.copy()

    cleaned_df.loc[
        1,
        "Category"
    ] = pd.NA

    cleaned_df.loc[
        2,
        "Category"
    ] = pd.NA

    cleaned_df.loc[
        3,
        "Category"
    ] = pd.NA

    result = find_unresolved_cleaning_issues(
        original_df,
        cleaned_df
    )

    # INVALID was genuinely present and became missing,
    # therefore it requires remediation.
    #
    # NA and "" are genuine missing markers and are ignored.
    assert len(result) == 1

    assert result.loc[
        0,
        "index"
    ] == 1

    assert result.loc[
        0,
        "column"
    ] == "Category"

    assert result.loc[
        0,
        "original_value"
    ] == "INVALID"

    assert result.loc[
        0,
        "issue_type"
    ] == "Unresolved Cleaning Issue"


# ============================================================
# 13. NO UNRESOLVED CLEANING ISSUES
# ============================================================

def test_find_unresolved_cleaning_issues_empty():

    original_df = pd.DataFrame(
        {
            "Record_ID": [
                1,
                2
            ],

            "Order_ID": [
                "ORD-00001",
                "ORD-00002"
            ],

            "Category": [
                "Electronics",
                "NA"
            ]
        }
    )

    cleaned_df = original_df.copy()

    cleaned_df.loc[
        1,
        "Category"
    ] = pd.NA

    result = find_unresolved_cleaning_issues(
        original_df,
        cleaned_df
    )

    assert result.empty

    assert result.columns.tolist() == [
        "index",
        "column",
        "original_value",
        "issue_type"
    ]


# ============================================================
# 14. CLASSIFY EMAIL ISSUES
# ============================================================

def test_classify_email_issues():

    df = pd.DataFrame(
        {
            "Customer_Email": [
                "valid.user@example.com",
                "arun.banerjee*example.com",
                "user@test.com",
                " USER@EXAMPLE.COM ",
                "",
                "NA",
                "None",
                "NULL",
                "null",
                pd.NA
            ]
        }
    )

    result = classify_email_issues(df)

    assert len(result) == 2

    syntax_issue = result[
        result["issue_type"]
        == "Invalid email syntax"
    ]

    domain_issue = result[
        result["issue_type"]
        == "Incorrect email domain"
    ]

    assert len(syntax_issue) == 1
    assert len(domain_issue) == 1

    assert (
        syntax_issue.iloc[0][
            "original_value"
        ]
        == "arun.banerjee*example.com"
    )

    assert (
        domain_issue.iloc[0][
            "original_value"
        ]
        == "user@test.com"
    )


# ============================================================
# 15. CLASSIFY EMAIL ISSUES - CLEAN DATA
# ============================================================

def test_classify_email_issues_no_errors():

    df = pd.DataFrame(
        {
            "Customer_Email": [
                "user@example.com",
                "another.user@example.com",
                "USER@EXAMPLE.COM",
                "",
                "NA",
                pd.NA
            ]
        }
    )

    result = classify_email_issues(df)

    assert result.empty

    assert result.columns.tolist() == [
        "index",
        "column",
        "original_value",
        "issue_type"
    ]

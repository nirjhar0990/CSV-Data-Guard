import pandas as pd

from pipeline.problem_map import create_problem_map


# ============================================================
# HELPERS
# ============================================================

def make_original_df():

    return pd.DataFrame(
        {
            "Record_ID": [1, 2, 3, 4],

            "Order_ID": [
                "ORD-00001",
                "ORD-00002",
                "ORD-00003",
                "ORD-00004"
            ],

            "Customer_Name": [
                "Arun Banerjee",
                "Riya Sen",
                "Amit Roy",
                "Sara Das"
            ],

            "Customer_Email": [
                "valid@example.com",
                "bad-email",
                "user@test.com",
                ""
            ],

            "Category": [
                "Electronics",
                "INVALID",
                "Books",
                "Sports"
            ],

            "Quantity": [
                "1",
                "-1",
                "abc",
                "5"
            ],

            "Discount": [
                "10",
                "101",
                "bad",
                "50"
            ],

            "Customer_Age": [
                "30",
                "150",
                "abc",
                "40"
            ],

            "Customer_Rating": [
                "5",
                "0",
                "bad",
                "4"
            ]
        }
    )


def empty_unresolved():

    return pd.DataFrame(
        columns=[
            "index",
            "column",
            "original_value",
            "issue_type"
        ]
    )


def empty_failures():

    return pd.DataFrame(
        columns=[
            "schema_context",
            "column",
            "check",
            "check_number",
            "failure_case",
            "index"
        ]
    )


# ============================================================
# 1. EMPTY PROBLEM MAP
# ============================================================

def test_create_problem_map_empty():

    original_df = pd.DataFrame(
        {
            "Customer_Email": [
                "valid@example.com"
            ]
        }
    )

    result = create_problem_map(
        original_df,
        empty_failures(),
        empty_unresolved()
    )

    assert result.empty

    assert result.columns.tolist() == [
        "index",
        "column",
        "validation_error",
        "how_to_fix",
        "source",
        "reportable",
        "reviewable"
    ]


# ============================================================
# 2. STANDARD CLEANING ISSUE
# ============================================================

def test_standard_cleaning_issue():

    original_df = make_original_df()

    unresolved = pd.DataFrame(
        {
            "index": [1],
            "column": ["Category"],
            "original_value": ["INVALID"],
            "issue_type": [
                "Unresolved Cleaning Issue"
            ]
        }
    )

    result = create_problem_map(
        original_df,
        empty_failures(),
        unresolved
    )

    cleaning_rows = result[
        result["source"] == "cleaning"
    ]

    assert len(cleaning_rows) == 1

    row = cleaning_rows.iloc[0]

    assert row["index"] == 1
    assert row["column"] == "Category"

    assert (
        row["validation_error"]
        == "Invalid category"
    )

    assert (
        row["how_to_fix"]
        == "Use one of the allowed product categories."
    )

    assert bool(row["reportable"]) is True
    assert bool(row["reviewable"]) is True


# ============================================================
# 3. CUSTOMER RATING CLEANING ISSUE
# ============================================================

def test_customer_rating_cleaning_messages():

    original_df = make_original_df()

    unresolved = pd.DataFrame(
        {
            "index": [
                1,
                2
            ],

            "column": [
                "Customer_Rating",
                "Customer_Rating"
            ],

            "original_value": [
                "0",
                "bad"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue",
                "Unresolved Cleaning Issue"
            ]
        }
    )

    result = create_problem_map(
        original_df,
        empty_failures(),
        unresolved
    )

    rows = result[
        result["source"] == "cleaning"
    ].sort_values("index")

    assert len(rows) == 2

    assert (
        rows.iloc[0]["validation_error"]
        == "Rating is below the allowed range"
    )

    assert (
        rows.iloc[0]["how_to_fix"]
        == "Set the rating between 1 and 5."
    )

    assert (
        rows.iloc[1]["validation_error"]
        == "Invalid customer rating"
    )

    assert (
        rows.iloc[1]["how_to_fix"]
        == "Enter a numeric rating between 1 and 5."
    )


# ============================================================
# 4. CUSTOMER AGE CLEANING ISSUE
# ============================================================

def test_customer_age_cleaning_messages():

    original_df = make_original_df()

    unresolved = pd.DataFrame(
        {
            "index": [
                1,
                2
            ],

            "column": [
                "Customer_Age",
                "Customer_Age"
            ],

            "original_value": [
                "150",
                "bad"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue",
                "Unresolved Cleaning Issue"
            ]
        }
    )

    result = create_problem_map(
        original_df,
        empty_failures(),
        unresolved
    )

    rows = result[
        result["source"] == "cleaning"
    ].sort_values("index")

    assert len(rows) == 2

    assert (
        rows.iloc[0]["validation_error"]
        == "Age is above the allowed range"
    )

    assert (
        rows.iloc[0]["how_to_fix"]
        == "Set the age between 0 and 120."
    )

    assert (
        rows.iloc[1]["validation_error"]
        == "Invalid customer age"
    )


# ============================================================
# 5. NUMERIC CLEANING ISSUE
# ============================================================

def test_numeric_cleaning_issue_messages():

    original_df = make_original_df()

    unresolved = pd.DataFrame(
        {
            "index": [
                1,
                2
            ],

            "column": [
                "Quantity",
                "Quantity"
            ],

            "original_value": [
                "-1",
                "abc"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue",
                "Unresolved Cleaning Issue"
            ]
        }
    )

    result = create_problem_map(
        original_df,
        empty_failures(),
        unresolved
    )

    rows = result[
        result["source"] == "cleaning"
    ].sort_values("index")

    assert len(rows) == 2

    assert (
        rows.iloc[0]["validation_error"]
        == "Quantity is below the allowed range"
    )

    assert (
        rows.iloc[0]["how_to_fix"]
        == "Set quantity to 0 or greater."
    )

    assert (
        rows.iloc[1]["validation_error"]
        == "Invalid quantity"
    )

    assert (
        rows.iloc[1]["how_to_fix"]
        == "Enter a valid numeric value."
    )


# ============================================================
# 6. DISCOUNT CLEANING RANGE ISSUES
# ============================================================

def test_discount_cleaning_range_messages():

    original_df = make_original_df()

    unresolved = pd.DataFrame(
        {
            "index": [
                0,
                1
            ],

            "column": [
                "Discount",
                "Discount"
            ],

            "original_value": [
                "-1",
                "101"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue",
                "Unresolved Cleaning Issue"
            ]
        }
    )

    result = create_problem_map(
        original_df,
        empty_failures(),
        unresolved
    )

    rows = result[
        result["source"] == "cleaning"
    ].sort_values("index")

    assert (
        rows.iloc[0]["validation_error"]
        == "Discount is below the allowed range"
    )

    assert (
        rows.iloc[1]["validation_error"]
        == "Discount is above the allowed range"
    )

    assert all(
        rows["how_to_fix"]
        == "Set discount between 0 and 100."
    )


# ============================================================
# 7. ORIGINAL EMAIL SYNTAX ISSUE
# ============================================================

def test_original_email_syntax_is_reportable_not_reviewable():

    original_df = make_original_df()

    result = create_problem_map(
        original_df,
        empty_failures(),
        empty_unresolved()
    )

    rows = result[
        (result["source"] == "email")
        &
        (
            result["validation_error"]
            == "Invalid email syntax"
        )
    ]

    assert len(rows) == 1

    row = rows.iloc[0]

    assert row["index"] == 1
    assert row["column"] == "Customer_Email"

    assert bool(row["reportable"]) is True
    assert bool(row["reviewable"]) is False

    assert (
        row["how_to_fix"]
        == "Enter a valid email address."
    )


# ============================================================
# 8. ORIGINAL EMAIL DOMAIN ISSUE
# ============================================================

def test_original_email_domain_is_reportable_not_reviewable():

    original_df = make_original_df()

    result = create_problem_map(
        original_df,
        empty_failures(),
        empty_unresolved()
    )

    rows = result[
        (result["source"] == "email")
        &
        (
            result["validation_error"]
            == "Incorrect email domain"
        )
    ]

    assert len(rows) == 1

    row = rows.iloc[0]

    assert row["index"] == 2
    assert row["column"] == "Customer_Email"

    assert bool(row["reportable"]) is True
    assert bool(row["reviewable"]) is False

    assert (
        row["how_to_fix"]
        == "Use the @example.com email domain."
    )


# ============================================================
# 9. MISSING EMAIL IS NOT CLASSIFIED
# ============================================================

def test_original_missing_email_not_classified():

    original_df = pd.DataFrame(
        {
            "Customer_Email": [
                "",
                "NA",
                "None",
                "NULL",
                "null",
                pd.NA
            ]
        }
    )

    result = create_problem_map(
        original_df,
        empty_failures(),
        empty_unresolved()
    )

    assert result.empty


# ============================================================
# 10. PANDERA EMAIL FAILURE
# ============================================================

def test_pandera_email_failure_is_reviewable_not_reportable():

    original_df = make_original_df()

    failure_cases = pd.DataFrame(
        {
            "schema_context": [
                "Column"
            ],

            "column": [
                "Customer_Email"
            ],

            "check": [
                "str_matches"
            ],

            "check_number": [
                0
            ],

            "failure_case": [
                "bad-email"
            ],

            "index": [
                1
            ]
        }
    )

    result = create_problem_map(
        original_df,
        failure_cases,
        empty_unresolved()
    )

    rows = result[
        (result["source"] == "validation")
        &
        (
            result["column"]
            == "Customer_Email"
        )
    ]

    assert len(rows) == 1

    row = rows.iloc[0]

    assert (
        row["validation_error"]
        == "Validation failed"
    )

    assert bool(row["reportable"]) is False
    assert bool(row["reviewable"]) is True


# ============================================================
# 11. NON-EMAIL PANDERA FAILURE
# ============================================================

def test_non_email_validation_failure_is_reportable_and_reviewable():

    original_df = make_original_df()

    failure_cases = pd.DataFrame(
        {
            "schema_context": [
                "Column"
            ],

            "column": [
                "Category"
            ],

            "check": [
                "isin"
            ],

            "check_number": [
                0
            ],

            "failure_case": [
                "InvalidCategory"
            ],

            "index": [
                1
            ]
        }
    )

    result = create_problem_map(
        original_df,
        failure_cases,
        empty_unresolved()
    )

    rows = result[
        (result["source"] == "validation")
        &
        (
            result["column"] == "Category"
        )
    ]

    assert len(rows) == 1

    row = rows.iloc[0]

    assert (
        row["validation_error"]
        == "Invalid category"
    )

    assert (
        row["how_to_fix"]
        == "Use one of the allowed product categories."
    )

    assert bool(row["reportable"]) is True
    assert bool(row["reviewable"]) is True


# ============================================================
# 12. NUMERIC VALIDATION RANGE FAILURE
# ============================================================

def test_numeric_validation_range_message():

    original_df = make_original_df()

    failure_cases = pd.DataFrame(
        {
            "schema_context": [
                "Column"
            ],

            "column": [
                "Quantity"
            ],

            "check": [
                "greater_than_or_equal_to(0)"
            ],

            "check_number": [
                0
            ],

            "failure_case": [
                -1
            ],

            "index": [
                1
            ]
        }
    )

    result = create_problem_map(
        original_df,
        failure_cases,
        empty_unresolved()
    )

    rows = result[
        (result["source"] == "validation")
        &
        (
            result["column"] == "Quantity"
        )
    ]

    assert len(rows) == 1

    row = rows.iloc[0]

    assert (
        row["validation_error"]
        == "Quantity is below the allowed range"
    )

    assert (
        row["how_to_fix"]
        == "Set quantity to 0 or greater."
    )


# ============================================================
# 13. DISCOUNT VALIDATION FAILURE
# ============================================================

def test_discount_validation_range_message():

    original_df = make_original_df()

    failure_cases = pd.DataFrame(
        {
            "schema_context": [
                "Column",
                "Column"
            ],

            "column": [
                "Discount",
                "Discount"
            ],

            "check": [
                "greater_than_or_equal_to(0)",
                "less_than_or_equal_to(100)"
            ],

            "check_number": [
                0,
                1
            ],

            "failure_case": [
                -1,
                101
            ],

            "index": [
                0,
                1
            ]
        }
    )

    result = create_problem_map(
        original_df,
        failure_cases,
        empty_unresolved()
    )

    rows = result[
        (result["source"] == "validation")
        &
        (
            result["column"] == "Discount"
        )
    ].sort_values("index")

    assert len(rows) == 2

    assert (
        rows.iloc[0]["validation_error"]
        == "Discount is below the allowed range"
    )

    assert (
        rows.iloc[1]["validation_error"]
        == "Discount is above the allowed range"
    )


# ============================================================
# 14. INVALID SOURCE INDEXES ARE REMOVED
# ============================================================

def test_problem_map_removes_indexes_not_in_original_dataframe():

    original_df = pd.DataFrame(
        {
            "Customer_Email": [
                "valid@example.com"
            ]
        }
    )

    unresolved = pd.DataFrame(
        {
            "index": [
                999
            ],

            "column": [
                "Category"
            ],

            "original_value": [
                "INVALID"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue"
            ]
        }
    )

    result = create_problem_map(
        original_df,
        empty_failures(),
        unresolved
    )

    assert result.empty


# ============================================================
# 15. COMBINED SOURCES
# ============================================================

def test_problem_map_combines_cleaning_email_and_validation_sources():

    original_df = make_original_df()

    unresolved = pd.DataFrame(
        {
            "index": [
                1
            ],

            "column": [
                "Category"
            ],

            "original_value": [
                "INVALID"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue"
            ]
        }
    )

    failure_cases = pd.DataFrame(
        {
            "schema_context": [
                "Column"
            ],

            "column": [
                "Quantity"
            ],

            "check": [
                "greater_than_or_equal_to(0)"
            ],

            "check_number": [
                0
            ],

            "failure_case": [
                -1
            ],

            "index": [
                1
            ]
        }
    )

    result = create_problem_map(
        original_df,
        failure_cases,
        unresolved
    )

    sources = set(
        result["source"]
        .dropna()
        .tolist()
    )

    assert sources == {
        "cleaning",
        "email",
        "validation"
    }


# ============================================================
# 16. REQUIRED OUTPUT COLUMNS
# ============================================================

def test_problem_map_has_required_columns():

    original_df = make_original_df()

    result = create_problem_map(
        original_df,
        empty_failures(),
        empty_unresolved()
    )

    assert result.columns.tolist() == [
        "index",
        "column",
        "source",
        "reportable",
        "reviewable",
        "validation_error",
        "how_to_fix"
    ]


# ============================================================
# 17. REPORTABLE / REVIEWABLE SEMANTICS
# ============================================================

def test_reportable_reviewable_semantics():

    original_df = make_original_df()

    unresolved = pd.DataFrame(
        {
            "index": [
                1
            ],

            "column": [
                "Category"
            ],

            "original_value": [
                "INVALID"
            ],

            "issue_type": [
                "Unresolved Cleaning Issue"
            ]
        }
    )

    failure_cases = pd.DataFrame(
        {
            "schema_context": [
                "Column",
                "Column"
            ],

            "column": [
                "Customer_Email",
                "Category"
            ],

            "check": [
                "str_matches",
                "isin"
            ],

            "check_number": [
                0,
                0
            ],

            "failure_case": [
                "bad-email",
                "INVALID"
            ],

            "index": [
                1,
                1
            ]
        }
    )

    result = create_problem_map(
        original_df,
        failure_cases,
        unresolved
    )

    cleaning = result[
        result["source"] == "cleaning"
    ]

    original_email = result[
        result["source"] == "email"
    ]

    validation_email = result[
        (result["source"] == "validation")
        &
        (
            result["column"] == "Customer_Email"
        )
    ]

    validation_other = result[
        (result["source"] == "validation")
        &
        (
            result["column"] == "Category"
        )
    ]

    assert cleaning["reportable"].all()
    assert cleaning["reviewable"].all()

    assert original_email["reportable"].all()
    assert not original_email["reviewable"].any()

    assert not validation_email["reportable"].any()
    assert validation_email["reviewable"].all()

    assert validation_other["reportable"].all()
    assert validation_other["reviewable"].all()

# ============================================================
# 18. CUSTOMER AGE VALIDATION RANGE MESSAGES
# ============================================================

def test_customer_age_validation_range_messages():

    original_df = make_original_df()

    failure_cases = pd.DataFrame(
        {
            "schema_context": [
                "Column",
                "Column"
            ],

            "column": [
                "Customer_Age",
                "Customer_Age"
            ],

            "check": [
                "greater_than_or_equal_to(0)",
                "less_than_or_equal_to(120)"
            ],

            "check_number": [
                0,
                1
            ],

            "failure_case": [
                -1,
                150
            ],

            "index": [
                0,
                1
            ]
        }
    )

    result = create_problem_map(
        original_df,
        failure_cases,
        empty_unresolved()
    )

    rows = result[
        (result["source"] == "validation")
        &
        (result["column"] == "Customer_Age")
    ].sort_values("index")

    assert len(rows) == 2

    assert (
        rows.iloc[0]["validation_error"]
        == "Age is below the allowed range"
    )

    assert (
        rows.iloc[0]["how_to_fix"]
        == "Set the age between 0 and 120."
    )

    assert (
        rows.iloc[1]["validation_error"]
        == "Age is above the allowed range"
    )

    assert (
        rows.iloc[1]["how_to_fix"]
        == "Set the age between 0 and 120."
    )

    assert rows["reportable"].all()
    assert rows["reviewable"].all()


# ============================================================
# 19. CUSTOMER RATING VALIDATION RANGE MESSAGES
# ============================================================

def test_customer_rating_validation_range_messages():

    original_df = make_original_df()

    failure_cases = pd.DataFrame(
        {
            "schema_context": [
                "Column",
                "Column"
            ],

            "column": [
                "Customer_Rating",
                "Customer_Rating"
            ],

            "check": [
                "greater_than_or_equal_to(1)",
                "less_than_or_equal_to(5)"
            ],

            "check_number": [
                0,
                1
            ],

            "failure_case": [
                0,
                6
            ],

            "index": [
                0,
                1
            ]
        }
    )

    result = create_problem_map(
        original_df,
        failure_cases,
        empty_unresolved()
    )

    rows = result[
        (result["source"] == "validation")
        &
        (result["column"] == "Customer_Rating")
    ].sort_values("index")

    assert len(rows) == 2

    assert (
        rows.iloc[0]["validation_error"]
        == "Rating is below the allowed range"
    )

    assert (
        rows.iloc[0]["how_to_fix"]
        == "Set the rating between 1 and 5."
    )

    assert (
        rows.iloc[1]["validation_error"]
        == "Rating is above the allowed range"
    )

    assert (
        rows.iloc[1]["how_to_fix"]
        == "Set the rating between 1 and 5."
    )

    assert rows["reportable"].all()
    assert rows["reviewable"].all()

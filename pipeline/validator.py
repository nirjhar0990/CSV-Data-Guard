import re
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check
from pandera.errors import SchemaErrors
from .cleaner import clean_data
from .profiler import load_csv
from .reporting import create_validation_report


# ================================================================
# VALIDATION SCHEMA
# ================================================================

schema = DataFrameSchema(
    {

        # --------------------------------------------------------
        # Order ID
        # --------------------------------------------------------

        "Order_ID": Column(
        pa.String,
        checks=Check.str_matches(
        r"^ORD-\d{5}$"
     ),
        nullable=False,
        unique=True
    ),

        # --------------------------------------------------------
        # Customer Name
        # --------------------------------------------------------

        "Customer_Name": Column(
            pa.String,
            checks=Check.str_matches(
                r"^[A-Za-z]+(?:\s+[A-Za-z]+)*$"
            ),
            nullable=False
        ),

        # --------------------------------------------------------
        # Customer Email
        # --------------------------------------------------------

        "Customer_Email": Column(
            pa.String,
            checks=[
                Check.str_matches(
                    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
                ),
                Check.str_endswith(
                    "@example.com"
                )
            ],
            nullable=False
        ),

        # --------------------------------------------------------
        # City
        # --------------------------------------------------------

        "City": Column(
            pa.String,
            checks=Check.str_matches(
                r"^[A-Za-z]+(?:\s+[A-Za-z]+)*$"
            ),
            nullable=True
        ),

        # --------------------------------------------------------
        # Category
        # --------------------------------------------------------

        "Category": Column(
            pa.String,
            checks=Check.isin(
                [
                    "Electronics",
                    "Sports",
                    "Furniture",
                    "Clothing",
                    "Groceries",
                    "Books"
                ]
            ),
            nullable=False
        ),

        # --------------------------------------------------------
        # Product
        # --------------------------------------------------------

        "Product": Column(
            pa.String,
            checks=Check.isin(
                [
                    "Laptop",
                    "Smartphone",
                    "Headphones",
                    "Tablet",
                    "T-Shirt",
                    "Jeans",
                    "Jacket",
                    "Shoes",
                    "Rice",
                    "Milk",
                    "Bread",
                    "Cooking Oil",
                    "Chair",
                    "Table",
                    "Sofa",
                    "Bed",
                    "Python Programming",
                    "Data Science",
                    "Machine Learning",
                    "Database Systems",
                    "Football",
                    "Cricket Bat",
                    "Tennis Racket",
                    "Basketball"
                ]
            ),
            nullable=False
        ),

        # --------------------------------------------------------
        # Quantity
        # --------------------------------------------------------

        "Quantity": Column(
            float,
            checks=Check.ge(0),
            nullable=False
        ),

        # --------------------------------------------------------
        # Unit Price
        # --------------------------------------------------------

        "Unit_Price": Column(
            float,
            checks=Check.ge(0),
            nullable=False
        ),

        # --------------------------------------------------------
        # Discount
        # --------------------------------------------------------

        "Discount": Column(
            float,
            checks=[
                Check.ge(0),
                Check.le(100)
            ],
            nullable=False
        ),

        # --------------------------------------------------------
        # Total Amount
        # --------------------------------------------------------

        "Total_Amount": Column(
            float,
            checks=Check.ge(0),
            nullable=False
        ),

        # --------------------------------------------------------
        # Order Date
        # --------------------------------------------------------

        "Order_Date": Column(
            pa.DateTime,
            nullable=False
        ),

        # --------------------------------------------------------
        # Payment Method
        # --------------------------------------------------------

        "Payment_Method": Column(
            pa.String,
            checks=Check.isin(
                [
                    "Cash",
                    "Credit Card",
                    "Debit Card",
                    "UPI",
                    "Net Banking"
                ]
            ),
            nullable=False
        ),

        # --------------------------------------------------------
        # Order Status
        # --------------------------------------------------------

        "Order_Status": Column(
            pa.String,
            checks=Check.isin(
                [
                    "Completed",
                    "Pending",
                    "Cancelled",
                    "Returned"
                ]
            ),
            nullable=False
        ),

        # --------------------------------------------------------
        # Customer Age
        # --------------------------------------------------------

        "Customer_Age": Column(
            "Int64",
            checks=[
                Check.ge(0),
                Check.le(120)
            ],
            nullable=True
        ),

        # --------------------------------------------------------
        # Customer Rating
        # --------------------------------------------------------

        "Customer_Rating": Column(
            "Int64",
            checks=[
                Check.ge(1),
                Check.le(5)
            ],
            nullable=True
        )
    },

    strict=True
)


# ================================================================
# VALIDATE DATA
# ================================================================

def validate_data(df):

    validation_df = df.drop(
        columns=["Record_ID"],
        errors="ignore"
    )

    try:
        validated_df = schema.validate(
            validation_df,
            lazy=True
        )

        return {
            "success": True,
            "data": validated_df,
            "failure_cases": None
        }

    except pa.errors.SchemaErrors as exc:

        return {
            "success": False,
            "data": None,
            "failure_cases": exc.failure_cases
        }


# ================================================================
# VALIDATION SCORE
# ================================================================

def calculate_validation_score(
    df,
    failure_cases
):
    """
    Calculate the percentage of rows that pass
    all configured validation rules.

    A row is counted as invalid only once even if
    it fails multiple validation checks.
    """

    total_rows = len(df)

    # -----------------------------------------
    # EMPTY DATASET
    # -----------------------------------------

    if total_rows == 0:
        return 100.0

    # -----------------------------------------
    # NO VALIDATION FAILURES
    # -----------------------------------------

    if (
        failure_cases is None
        or failure_cases.empty
    ):
        return 100.0

    # -----------------------------------------
    # FIND UNIQUE INVALID ROWS
    # -----------------------------------------

    invalid_indexes = (
        failure_cases[
            "index"
        ]
        .dropna()
        .unique()
    )

    invalid_row_count = len(
        invalid_indexes
    )

    # -----------------------------------------
    # SAFETY FOR DATASET-LEVEL FAILURES
    # -----------------------------------------

    # If Pandera reports a failure but there is
    # no row index, treat validation as failed.
    if (
        invalid_row_count == 0
        and not failure_cases.empty
    ):
        return 0.0

    # -----------------------------------------
    # CALCULATE VALID ROWS
    # -----------------------------------------

    valid_row_count = (
        total_rows
        - invalid_row_count
    )

    valid_row_count = max(
        0,
        valid_row_count
    )

    # -----------------------------------------
    # CALCULATE SCORE
    # -----------------------------------------

    validation_score = (
        valid_row_count
        / total_rows
    ) * 100

    return round(
        validation_score,
        2
    )


# ================================================================
# FIND UNRESOLVED CLEANING ISSUES
# ================================================================

def find_unresolved_cleaning_issues(
    original_df,
    cleaned_df
):
    """
    Find values that were originally present but became
    missing during cleaning because they were invalid.

    Genuine missing values such as:
        ""
        NA
        None
        NULL
        null

    are NOT treated as unresolved issues.

    Vectorized for performance.
    """

    missing_tokens = {
        "",
        "NA",
        "None",
        "NULL",
        "null"
    }

    common_indexes = (
        original_df.index.intersection(
            cleaned_df.index
        )
    )

    issue_parts = []

    # ========================================================
    # PROCESS COLUMN-WISE
    # ========================================================

    for column in original_df.columns:

        if column in {
            "Order_ID",
            "Record_ID"
        }:
            continue

        original_values = (
            original_df.loc[
                common_indexes,
                column
            ]
        )

        cleaned_values = (
            cleaned_df.loc[
                common_indexes,
                column
            ]
        )

        original_text = (
            original_values
            .astype("string")
            .str.strip()
        )

        genuine_missing = (
            original_values.isna()
            |
            original_text.isin(
                missing_tokens
            )
        )

        became_missing = (
            cleaned_values.isna()
        )

        unresolved_mask = (
            ~genuine_missing
            &
            became_missing
        )

        if not unresolved_mask.any():
            continue

        unresolved_indexes = (
            original_values.index[
                unresolved_mask
            ]
        )

        issue_parts.append(
            pd.DataFrame(
                {
                    "index":
                        unresolved_indexes,

                    "column":
                        column,

                    "original_value":
                        original_values.loc[
                            unresolved_indexes
                        ].to_numpy(),

                    "issue_type":
                        "Unresolved Cleaning Issue"
                }
            )
        )

    # ========================================================
    # NO ISSUES
    # ========================================================

    if not issue_parts:

        return pd.DataFrame(
            columns=[
                "index",
                "column",
                "original_value",
                "issue_type"
            ]
        )

    # ========================================================
    # COMBINE
    # ========================================================

    return pd.concat(
        issue_parts,
        ignore_index=True
    )


def calculate_cleaning_score(
    initial_unresolved_count,
    current_unresolved_count
):
    """
    Calculate Cleaning Score based on the resolution
    of known unresolved cleaning issues.

    Cleaning Score:

        resolved issues
        ------------------------- x 100
        initial unresolved issues

    Example:

        Initial unresolved issues = 100
        Current unresolved issues = 25

        Resolved = 75

        Cleaning Score = 75%
    """

    # -----------------------------------------
    # NO CLEANING ISSUES WERE DETECTED
    # -----------------------------------------

    if initial_unresolved_count == 0:
        return 100.0

    # -----------------------------------------
    # CALCULATE RESOLVED ISSUES
    # -----------------------------------------

    resolved_issues = (
        initial_unresolved_count
        - current_unresolved_count
    )

    # Prevent negative values
    resolved_issues = max(
        0,
        resolved_issues
    )

    # -----------------------------------------
    # CALCULATE SCORE
    # -----------------------------------------

    cleaning_score = (
        resolved_issues
        / initial_unresolved_count
    ) * 100

    # Prevent score above 100
    cleaning_score = min(
        cleaning_score,
        100.0
    )

    return round(
        cleaning_score,
        2
    )


# ================================================================
# CLASSIFY EMAIL ISSUES
# ================================================================

def classify_email_issues(original_df):
    """
    Classify original email values into:

        Invalid email syntax
        Incorrect email domain

    Genuine missing values are ignored.

    This classification is performed separately from Pandera
    because Pandera may report a syntax failure before the
    domain check for the same value.
    """

    missing_tokens = {
        "",
        "NA",
        "None",
        "NULL",
        "null"
    }

    syntax_pattern = re.compile(
        r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    )

    issues = []

    for index, value in (
        original_df["Customer_Email"].items()
    ):

        if pd.isna(value):
            continue

        value_text = str(value).strip()

        if value_text in missing_tokens:
            continue

        value_text = value_text.lower()

        # --------------------------------------------------------
        # Invalid syntax
        # --------------------------------------------------------

        if not syntax_pattern.fullmatch(
            value_text
        ):

            issues.append(
                {
                    "index": index,
                    "column": "Customer_Email",
                    "original_value": value,
                    "issue_type": "Invalid email syntax"
                }
            )

            continue

        # --------------------------------------------------------
        # Incorrect domain
        # --------------------------------------------------------

        if not value_text.endswith(
            "@example.com"
        ):

            issues.append(
                {
                    "index": index,
                    "column": "Customer_Email",
                    "original_value": value,
                    "issue_type": "Incorrect email domain"
                }
            )

    return pd.DataFrame(
        issues,
        columns=[
            "index",
            "column",
            "original_value",
            "issue_type"
        ]
    )


# ================================================================
# TESTING
# ================================================================

if __name__ == "__main__":

    print(
        "\n===== VALIDATOR TEST ====="
    )

    # ------------------------------------------------------------
    # Load original dataset
    # ------------------------------------------------------------

    df = load_csv(
        "data/messy_retail_data_10K.csv"
    )

    print(
        "Original rows:",
        len(df)
    )

    # ------------------------------------------------------------
    # Clean dataset
    # ------------------------------------------------------------

    cleaned_df, cleaning_checks = (
        clean_data(df)
    )

    print(
        "Cleaned rows:",
        len(cleaned_df)
    )

    # ------------------------------------------------------------
    # Unresolved cleaning issues
    # ------------------------------------------------------------

    unresolved_issues = (
        find_unresolved_cleaning_issues(
            df,
            cleaned_df
        )
    )

    if not unresolved_issues.empty:

        issue_summary = (
            unresolved_issues
            .groupby("column")
            .size()
            .reset_index(
                name="Records Affected"
            )
            .rename(
                columns={
                    "column": "Issue"
                }
            )
            .sort_values(
                "Records Affected",
                ascending=False
            )
            .reset_index(
                drop=True
            )
        )

        print(
            "\n===== ALL UNRESOLVED CLEANING ISSUES ====="
        )

        print(
            issue_summary.to_string(
                index=False
            )
        )

    else:

        print(
            "\nNo unresolved cleaning issues found."
        )

    # ------------------------------------------------------------
    # Email issue classification
    # ------------------------------------------------------------

    email_issues = classify_email_issues(
        df
    )

    print(
        "\n===== EMAIL ISSUE CLASSIFICATION ====="
    )

    if email_issues.empty:

        print(
            "No email issues found."
        )

    else:

        print(
            email_issues
            .groupby("issue_type")
            .size()
            .reset_index(
                name="Records Affected"
            )
            .to_string(
                index=False
            )
        )

    # ------------------------------------------------------------
    # Pandera validation
    # ------------------------------------------------------------

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

    # ------------------------------------------------------------
    # Validation score
    # ------------------------------------------------------------

    validation_score = (
        calculate_validation_score(
            cleaned_df,
            failure_cases
        )
    )

    print(
        "\n===== VALIDATION RESULT ====="
    )

    print(
        "Validation Success:",
        validation_result["success"]
    )

    print(
        "Validation Score:",
        round(
            validation_score,
            2
        ),
        "%"
    )

    # ------------------------------------------------------------
    # Failure cases
    # ------------------------------------------------------------

    if (
        failure_cases is not None
        and not failure_cases.empty
    ):

        print(
            "\n===== PANDERA FAILURE CASES ====="
        )

        print(
            failure_cases.head(5)
        )

    else:

        print(
            "\nNo Pandera validation failures."
        )

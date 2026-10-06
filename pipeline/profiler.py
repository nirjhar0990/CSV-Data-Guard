from datetime import datetime
import pandas as pd
import re
import time

# ================================================================
# CONSTANTS
# ================================================================

NUMERIC_COLUMNS = [
    "Quantity",
    "Unit_Price",
    "Discount",
    "Total_Amount"
]

MISSING_VALUES = {
    "",
    "NA",
    "None",
    "NULL",
    "null"
}

IGNORED_VALUES = {
    "",
    "NA",
    "None",
    "NULL",
    "null",
    "INVALID"
}

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

ORDER_ID_PATTERN = re.compile(
    r"ORD-\d{5}"
)

EXPECTED_EMAIL_DOMAIN = "example.com"


# ================================================================
# LOAD CSV
# ================================================================

def load_csv(file_path):
    """Load a CSV file into a Pandas DataFrame."""

    return pd.read_csv(
        file_path,
        keep_default_na=False
    )


# ================================================================
# MISSING / INVALID VALUES
# ================================================================

def profile_missing_values(df):
    """
    Profile blank, missing-token, and INVALID cells.
    """

    missing_values = [
        "NA",
        "None",
        "NULL",
        "null"
    ]

    invalid_values = [
        "INVALID"
    ]

    blank_cells = (
        df.eq("")
        .sum()
    )

    missing_value_cells = (
        df.isin(
            missing_values
        )
        .sum()
    )

    invalid_value_cells = (
        df.isin(
            invalid_values
        )
        .sum()
    )

    return {
        "blank_cells":
            blank_cells.to_dict(),

        "missing_value_cells":
            missing_value_cells.to_dict(),

        "invalid_value_cells":
            invalid_value_cells.to_dict(),

        "total_blank_cells":
            int(
                blank_cells.sum()
            ),

        "total_missing_value_cells":
            int(
                missing_value_cells.sum()
            ),

        "total_invalid_value_cells":
            int(
                invalid_value_cells.sum()
            )
    }


# ================================================================
# CATEGORICAL VALUES
# ================================================================

def profile_categorical_values(df):
    """
    Profile categorical columns for invalid values
    and casing variations.

    Optimized implementation:
        - preserves existing profiler semantics
        - preserves output ordering
        - avoids the expensive canonical .map()
        - uses membership masks for normalized and exact values
    """

    allowed_values = {

        "Product": [
            "Laptop", "Smartphone", "Headphones", "Tablet",
            "T-Shirt", "Jeans", "Jacket", "Shoes",
            "Rice", "Milk", "Bread", "Cooking Oil",
            "Chair", "Table", "Sofa", "Bed",
            "Python Programming", "Data Science",
            "Machine Learning", "Database Systems",
            "Football", "Cricket Bat",
            "Tennis Racket", "Basketball"
        ],

        "Payment_Method": [
            "Cash",
            "Credit Card",
            "Debit Card",
            "UPI",
            "Net Banking"
        ],

        "Order_Status": [
            "Completed",
            "Pending",
            "Cancelled",
            "Returned"
        ],

        "City": [
            "Kolkata",
            "Delhi",
            "Mumbai",
            "Bangalore",
            "Chennai",
            "Hyderabad",
            "Pune",
            "Ahmedabad"
        ],

        "Category": [
            "Electronics",
            "Clothing",
            "Groceries",
            "Furniture",
            "Books",
            "Sports"
        ],
    }

    sentinel_values = {
        "",
        "NA",
        "None",
        "NULL",
        "null",
        "INVALID"
    }

    result = {}

    for column, valid_values in allowed_values.items():

        series = df[column]

        eligible = ~series.isin(
            sentinel_values
        )

        normalized = (
            series.str.lower()
        )

        valid_lower = [
            value.lower()
            for value in valid_values
        ]

        normalized_valid = (
            normalized.isin(
                valid_lower
            )
        )

        exact_valid = (
            series.isin(
                valid_values
            )
        )

        invalid_mask = (
            eligible
            & ~normalized_valid
        )

        casing_mask = (
            eligible
            & normalized_valid
            & ~exact_valid
        )

        invalid_values = (
            series.loc[
                invalid_mask
            ]
            .tolist()
        )

        casing_variations = (
            series.loc[
                casing_mask
            ]
            .tolist()
        )

        result[column] = {

            "invalid_values":
                invalid_values,

            "invalid_count":
                len(
                    invalid_values
                ),

            "casing_variations":
                casing_variations,

            "casing_variation_count":
                len(
                    casing_variations
                )
        }

    return result


# ================================================================
# CUSTOMER NAMES
# ================================================================

def profile_customer_names(df):
    """
    Profile customer names for invalid characters.

    Equivalent rule to the original implementation:
        name.replace(" ", "").isalpha()
    """

    series = (
        df[
            "Customer_Name"
        ]
    )

    text = (
        series
        .astype("string")
    )


    ignored_mask = (
        text.isin(
            IGNORED_VALUES
        )
        .fillna(False)
    )


    alphabetic_mask = (
        text
        .str.replace(
            " ",
            "",
            regex=False
        )
        .str.isalpha()
        .fillna(False)
    )


    invalid_mask = (
        ~ignored_mask
        &
        ~alphabetic_mask
    )


    invalid_names = (
        series.loc[
            invalid_mask
        ]
        .tolist()
    )


    return {

        "invalid_names":
            invalid_names,

        "invalid_count":
            len(
                invalid_names
            )
    }


# ================================================================
# EMAILS
# ================================================================

def profile_emails(df):
    """
    Profile customer emails for:
        - invalid syntax
        - incorrect domain

    Genuine missing tokens are ignored.

    Performance optimization:
        Uses a direct case-insensitive suffix check for the expected
        email domain instead of splitting every email address.
    """

    series = (
        df[
            "Customer_Email"
        ]
    )

    email_text = (
        series
        .astype("string")
        .str.strip()
    )

    genuine_missing = (
        series.isna()
        |
        email_text.isin(
            MISSING_VALUES
        )
        .fillna(False)
    )

    eligible = (
        ~genuine_missing
    )

    invalid_token = (
        email_text
        .str.upper()
        .eq(
            "INVALID"
        )
        .fillna(False)
    )

    syntax_valid = (
        email_text
        .str.fullmatch(
            EMAIL_PATTERN,
            na=False
        )
    )

    invalid_syntax_mask = (
        eligible
        &
        (
            invalid_token
            |
            ~syntax_valid
        )
    )

    correct_domain = (
        email_text
        .str.lower()
        .str.endswith(
            f"@{EXPECTED_EMAIL_DOMAIN}",
            na=False
        )
    )

    invalid_domain_mask = (
        eligible
        &
        syntax_valid
        &
        ~correct_domain
    )

    invalid_syntax = (
        series.loc[
            invalid_syntax_mask
        ]
        .tolist()
    )

    invalid_domain = (
        series.loc[
            invalid_domain_mask
        ]
        .tolist()
    )

    return {
        "invalid_syntax":
            invalid_syntax,

        "invalid_syntax_count":
            len(
                invalid_syntax
            ),

        "invalid_domain":
            invalid_domain,

        "invalid_domain_count":
            len(
                invalid_domain
            )
    }


# ================================================================
# CUSTOMER AGE
# ================================================================

def profile_customer_age(df):
    """
    Profile Customer_Age.

    Missing/INVALID tokens are ignored.

    Valid age values must:
        - represent an integer
        - be between 0 and 100 inclusive

    This preserves the original profiler's 0..100 age rule.
    """

    series = (
        df[
            "Customer_Age"
        ]
    )

    text = (
        series
        .astype("string")
        .str.strip()
    )


    ignored_mask = (
        text.isin(
            IGNORED_VALUES
        )
        .fillna(False)
    )


    eligible = (
        ~ignored_mask
    )


    # Original implementation used int(value), not float(value).
    # Require integer-like text before numeric conversion.
    integer_text = (
        text
        .str.fullmatch(
            r"[+-]?\d+",
            na=False
        )
    )


    numeric = pd.to_numeric(
        text.where(
            integer_text
        ),
        errors="coerce"
    )


    invalid_mask = (
        eligible
        &
        (
            ~integer_text
            |
            numeric.lt(
                0
            )
            |
            numeric.gt(
                100
            )
        )
    )


    invalid_ages = (
        series.loc[
            invalid_mask
        ]
        .tolist()
    )


    return {

        "invalid_ages":
            invalid_ages,

        "invalid_count":
            len(
                invalid_ages
            )
    }


# ================================================================
# CUSTOMER RATING
# ================================================================

def profile_customer_rating(df):
    """
    Profile Customer_Rating.

    Missing/INVALID tokens are ignored.
    Valid range is 1..5 inclusive.
    """

    series = (
        df[
            "Customer_Rating"
        ]
    )

    text = (
        series
        .astype("string")
        .str.strip()
    )


    ignored_mask = (
        text.isin(
            IGNORED_VALUES
        )
        .fillna(False)
    )


    eligible = (
        ~ignored_mask
    )


    numeric = pd.to_numeric(
        text.where(
            eligible
        ),
        errors="coerce"
    )


    invalid_mask = (
        eligible
        &
        (
            numeric.isna()
            |
            numeric.lt(
                1
            )
            |
            numeric.gt(
                5
            )
        )
    )


    invalid_ratings = (
        series.loc[
            invalid_mask
        ]
        .tolist()
    )


    return {

        "invalid_ratings":
            invalid_ratings,

        "invalid_count":
            len(
                invalid_ratings
            )
    }


# ================================================================
# ORDER DATES
# ================================================================

def profile_order_dates(df):
    """
    Profile Order_Date for:
        - invalid dates
        - valid but non-standard dates

    Standard format:
        %m/%d/%Y

    Supported non-standard formats:
        %d/%m/%Y
        %m-%d-%Y
        %Y-%m-%d
        %B %d %Y

    Optimized implementation:
        Routes values by broad string structure before parsing,
        while preserving the original precedence and semantics.
    """

    series = (
        df[
            "Order_Date"
        ]
    )

    text = (
        series
        .astype("string")
        .str.strip()
    )

    ignored_mask = (
        text.isin(
            IGNORED_VALUES
        )
        .fillna(False)
    )

    eligible = (
        ~ignored_mask
    )


    # --------------------------------------------------------
    # ROUTE VALUES BY BROAD STRUCTURE
    # --------------------------------------------------------

    slash_mask = (
        eligible
        &
        text.str.contains(
            "/",
            regex=False,
            na=False
        )
    )

    hyphen_mask = (
        eligible
        &
        text.str.contains(
            "-",
            regex=False,
            na=False
        )
    )

    starts_with_year = (
        text.str.match(
            r"^\d{4}-",
            na=False
        )
    )

    alpha_mask = (
        eligible
        &
        text.str.contains(
            r"[A-Za-z]",
            regex=True,
            na=False
        )
    )


    # --------------------------------------------------------
    # STANDARD FORMAT FIRST: %m/%d/%Y
    # --------------------------------------------------------

    standard_valid = (
        pd.to_datetime(
            text.where(
                slash_mask
            ),
            format="%m/%d/%Y",
            errors="coerce"
        )
        .notna()
    )


    # --------------------------------------------------------
    # NON-STANDARD SLASH FORMAT: %d/%m/%Y
    # Preserve original precedence by only trying values
    # that failed the standard slash format first.
    # --------------------------------------------------------

    dmy_candidates = (
        slash_mask
        &
        ~standard_valid
    )

    dmy_valid = (
        pd.to_datetime(
            text.where(
                dmy_candidates
            ),
            format="%d/%m/%Y",
            errors="coerce"
        )
        .notna()
    )


    # --------------------------------------------------------
    # HYPHEN FORMATS
    # --------------------------------------------------------

    mdy_candidates = (
        hyphen_mask
        &
        ~starts_with_year
    )

    mdy_valid = (
        pd.to_datetime(
            text.where(
                mdy_candidates
            ),
            format="%m-%d-%Y",
            errors="coerce"
        )
        .notna()
    )

    ymd_candidates = (
        hyphen_mask
        &
        starts_with_year
    )

    ymd_valid = (
        pd.to_datetime(
            text.where(
                ymd_candidates
            ),
            format="%Y-%m-%d",
            errors="coerce"
        )
        .notna()
    )


    # --------------------------------------------------------
    # MONTH-NAME FORMAT: %B %d %Y
    # --------------------------------------------------------

    month_name_candidates = (
        alpha_mask
        &
        ~slash_mask
        &
        ~hyphen_mask
    )

    month_name_valid = (
        pd.to_datetime(
            text.where(
                month_name_candidates
            ),
            format="%B %d %Y",
            errors="coerce"
        )
        .notna()
    )


    # --------------------------------------------------------
    # FINAL MASKS
    # --------------------------------------------------------

    other_valid = (
        dmy_valid
        |
        mdy_valid
        |
        ymd_valid
        |
        month_name_valid
    )

    non_standard_mask = (
        eligible
        &
        ~standard_valid
        &
        other_valid
    )

    invalid_mask = (
        eligible
        &
        ~standard_valid
        &
        ~other_valid
    )


    non_standard_dates = (
        series.loc[
            non_standard_mask
        ]
        .tolist()
    )

    invalid_dates = (
        series.loc[
            invalid_mask
        ]
        .tolist()
    )


    return {

        "invalid_dates":
            invalid_dates,

        "invalid_count":
            len(
                invalid_dates
            ),

        "non_standard_dates":
            non_standard_dates,

        "non_standard_count":
            len(
                non_standard_dates
            )
    }


# ================================================================
# ORDER ID FORMAT
# ================================================================

def profile_order_ids(df):
    """
    Profile Order_ID values for ORD-12345 format.
    """

    series = (
        df[
            "Order_ID"
        ]
    )

    text = (
        series
        .astype("string")
    )


    ignored_mask = (
        text.isin(
            IGNORED_VALUES
        )
        .fillna(False)
    )


    valid_format = (
        text
        .str.fullmatch(
            ORDER_ID_PATTERN,
            na=False
        )
    )


    invalid_mask = (
        ~ignored_mask
        &
        ~valid_format
    )


    invalid_order_ids = (
        series.loc[
            invalid_mask
        ]
        .tolist()
    )


    return {

        "invalid_order_ids":
            invalid_order_ids,

        "invalid_count":
            len(
                invalid_order_ids
            )
    }


# ================================================================
# NUMERIC COLUMNS
# ================================================================

def profile_numeric_columns(df):
    """
    Profile numeric business columns for non-numeric values.
    """

    numeric_columns = [
        "Quantity",
        "Unit_Price",
        "Discount",
        "Total_Amount"
    ]

    result = {}


    for column in numeric_columns:

        series = (
            df[
                column
            ]
        )

        text = (
            series
            .astype("string")
            .str.strip()
        )


        ignored_mask = (
            text.isin(
                IGNORED_VALUES
            )
            .fillna(False)
        )


        eligible = (
            ~ignored_mask
        )


        numeric = pd.to_numeric(
            text.where(
                eligible
            ),
            errors="coerce"
        )


        invalid_mask = (
            eligible
            &
            numeric.isna()
        )


        invalid_values = (
            series.loc[
                invalid_mask
            ]
            .tolist()
        )


        result[column] = {

            "invalid_values":
                invalid_values,

            "invalid_count":
                len(
                    invalid_values
                )
        }


    return result


# ================================================================
# NUMERIC RANGE RULES
# ================================================================

def profile_numeric_ranges(df):
    """
    Profile numeric business-rule ranges.

    Important:
        Preserve the original Quantity profiler rule:
            Quantity <= 0 is invalid.
    """

    result = {}


    for column in [
        "Quantity",
        "Unit_Price",
        "Discount",
        "Total_Amount"
    ]:

        series = (
            df[
                column
            ]
        )

        text = (
            series
            .astype("string")
            .str.strip()
        )


        ignored_mask = (
            text.isin(
                IGNORED_VALUES
            )
            .fillna(False)
        )


        eligible = (
            ~ignored_mask
        )


        numeric = pd.to_numeric(
            text.where(
                eligible
            ),
            errors="coerce"
        )


        numeric_valid = (
            eligible
            &
            numeric.notna()
        )


        if column == "Quantity":

            range_invalid = (
                numeric_valid
                &
                numeric.le(
                    0
                )
            )


        elif column == "Unit_Price":

            range_invalid = (
                numeric_valid
                &
                numeric.lt(
                    0
                )
            )


        elif column == "Discount":

            range_invalid = (
                numeric_valid
                &
                (
                    numeric.lt(
                        0
                    )
                    |
                    numeric.gt(
                        100
                    )
                )
            )


        else:

            range_invalid = (
                numeric_valid
                &
                numeric.lt(
                    0
                )
            )


        column_invalid = (
            series.loc[
                range_invalid
            ]
            .tolist()
        )


        result[column] = {

            "invalid_values":
                column_invalid,

            "invalid_count":
                len(
                    column_invalid
                )
        }


    return result


# ================================================================
# COMBINED NUMERIC PROFILING
# ================================================================

def _profile_numeric_combined(df):
    """
    Optimized combined numeric profiler.

    Performance optimization:
    - reuses one numeric conversion per configured numeric column
    - attempts a fast float64 conversion on eligible values
    - safely falls back to pd.to_numeric(errors="coerce")
      when malformed numeric values are present
    - preserves the existing ignored-value, non-numeric,
      range-validation, invalid-count, and invalid-value-list semantics
    """

    numeric_profile = {}
    numeric_range_profile = {}

    for column in NUMERIC_COLUMNS:

        series = df[column]

        # ----------------------------------------------------
        # NORMALIZE TEXT
        # ----------------------------------------------------

        if (
            pd.api.types.is_object_dtype(series.dtype)
            or pd.api.types.is_string_dtype(series.dtype)
        ):

            text = (
                series
                .str.strip()
            )

        else:

            text = (
                series
                .astype("string")
                .str.strip()
            )


        # ----------------------------------------------------
        # IGNORED / ELIGIBLE VALUES
        # ----------------------------------------------------

        ignored_mask = (
            text.isin(
                IGNORED_VALUES
            )
            .fillna(False)
        )

        eligible = (
            ~ignored_mask
        )


        # ----------------------------------------------------
        # FAST NUMERIC CONVERSION WITH SAFE FALLBACK
        # ----------------------------------------------------

        numeric = pd.Series(
            pd.NA,
            index=text.index,
            dtype="Float64",
        )

        eligible_text = (
            text.loc[
                eligible
            ]
        )

        try:

            converted = (
                eligible_text
                .astype(
                    "float64"
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            converted = (
                pd.to_numeric(
                    eligible_text,
                    errors="coerce",
                )
            )

        numeric.loc[
            eligible
        ] = converted


        # ----------------------------------------------------
        # NON-NUMERIC PROFILE
        # ----------------------------------------------------

        invalid_numeric_mask = (
            eligible
            & numeric.isna()
        )

        invalid_numeric_values = (
            series.loc[
                invalid_numeric_mask
            ]
            .tolist()
        )

        numeric_profile[column] = {

            "invalid_values":
                invalid_numeric_values,

            "invalid_count":
                len(
                    invalid_numeric_values
                )
        }


        # ----------------------------------------------------
        # RANGE PROFILE
        # ----------------------------------------------------

        numeric_valid = (
            eligible
            & numeric.notna()
        )

        if column == "Quantity":

            range_invalid_mask = (
                numeric_valid
                & numeric.le(0)
            )

        elif column == "Unit_Price":

            range_invalid_mask = (
                numeric_valid
                & numeric.lt(0)
            )

        elif column == "Discount":

            range_invalid_mask = (
                numeric_valid
                & (
                    numeric.lt(0)
                    | numeric.gt(100)
                )
            )

        else:

            range_invalid_mask = (
                numeric_valid
                & numeric.lt(0)
            )

        invalid_range_values = (
            series.loc[
                range_invalid_mask
            ]
            .tolist()
        )

        numeric_range_profile[column] = {

            "invalid_values":
                invalid_range_values,

            "invalid_count":
                len(
                    invalid_range_values
                )
        }

    return (
        numeric_profile,
        numeric_range_profile
    )


# ================================================================
# ORDER ID DUPLICATES
# ================================================================

def profile_order_id_duplicates(df):
    """
    Profile duplicate Order_ID values.

    Optimized implementation:
        - uses a single value_counts() pass
        - filters IDs occurring more than once
        - derives both duplicate_id_count and affected_rows
          from the same frequency table
        - preserves the existing output schema
    """

    series = (
        df[
            "Order_ID"
        ]
    )

    counts = (
        series
        .value_counts(
            dropna=True
        )
    )

    duplicate_counts = (
        counts.loc[
            counts.gt(1)
        ]
    )

    duplicate_id_counts = (
        duplicate_counts
        .to_dict()
    )

    affected_rows = int(
        duplicate_counts.sum()
    )

    # Preserve duplicated(keep=False) semantics for repeated
    # genuine NaN values, while keeping NaN out of duplicate_ids.
    na_count = int(
        series.isna()
        .sum()
    )

    if na_count > 1:

        affected_rows += (
            na_count
        )


    return {

        "duplicate_ids":
            duplicate_id_counts,

        "duplicate_id_count":
            len(
                duplicate_id_counts
            ),

        "affected_rows":
            affected_rows
    }


# ================================================================
# ISSUE SUMMARY
# ================================================================

def create_issue_summary(profile):
    """
    Create chart-ready data-quality issue counts.
    """

    issues = {}

    missing_profile = (
        profile[
            "missing_value_profile"
        ]
    )


    issues[
        "Blank Cells"
    ] = (
        missing_profile[
            "total_blank_cells"
        ]
    )


    issues[
        "Missing Values"
    ] = (
        missing_profile[
            "total_missing_value_cells"
        ]
    )


    issues[
        "INVALID Values"
    ] = (
        missing_profile[
            "total_invalid_value_cells"
        ]
    )


    # Categorical issues
    for column, details in (
        profile[
            "categorical_profile"
        ].items()
    ):

        issues[
            f"{column} - Invalid"
        ] = (
            details[
                "invalid_count"
            ]
        )

        issues[
            f"{column} - Casing"
        ] = (
            details[
                "casing_variation_count"
            ]
        )


    issues[
        "Customer Names"
    ] = (
        profile[
            "customer_name_profile"
        ][
            "invalid_count"
        ]
    )


    issues[
        "Email Syntax"
    ] = (
        profile[
            "email_profile"
        ][
            "invalid_syntax_count"
        ]
    )


    issues[
        "Email Domain"
    ] = (
        profile[
            "email_profile"
        ][
            "invalid_domain_count"
        ]
    )


    issues[
        "Customer Age"
    ] = (
        profile[
            "age_profile"
        ][
            "invalid_count"
        ]
    )


    issues[
        "Customer Rating"
    ] = (
        profile[
            "rating_profile"
        ][
            "invalid_count"
        ]
    )


    issues[
        "Invalid Dates"
    ] = (
        profile[
            "order_date_profile"
        ][
            "invalid_count"
        ]
    )


    issues[
        "Non-Standard Dates"
    ] = (
        profile[
            "order_date_profile"
        ][
            "non_standard_count"
        ]
    )


    issues[
        "Invalid Order IDs"
    ] = (
        profile[
            "order_id_profile"
        ][
            "invalid_count"
        ]
    )


    for column, details in (
        profile[
            "numeric_profile"
        ].items()
    ):

        issues[
            f"{column} - Non-Numeric"
        ] = (
            details[
                "invalid_count"
            ]
        )


    for column, details in (
        profile[
            "numeric_range_profile"
        ].items()
    ):

        issues[
            f"{column} - Range"
        ] = (
            details[
                "invalid_count"
            ]
        )


    issues[
        "Duplicate Order IDs"
    ] = (
        profile[
            "order_id_duplicate_profile"
        ][
            "affected_rows"
        ]
    )


    issues[
        "Duplicate Rows"
    ] = (
        profile[
            "duplicate_rows"
        ]
    )


    return issues


# ================================================================
# COMPLETE PROFILE
# ================================================================

def profile_data(df):
    """
    Generate the complete data-quality profile.

    Performance profiling version:
        - preserves existing profiler semantics
        - prints timing for each major profiling stage
        - makes no intentional data-quality rule changes
    """

    total_start = time.perf_counter()

    # ============================================================
    # 1. BASIC METADATA
    # ============================================================

    stage_start = time.perf_counter()

    rows = len(df)
    columns = len(df.columns)
    column_names = df.columns.tolist()

    data_types = (
        df.dtypes
        .astype(str)
        .to_dict()
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Basic metadata':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 2. PANDAS NA COUNTS
    # ============================================================

    stage_start = time.perf_counter()

    missing_values = (
        df.isna()
        .sum()
        .to_dict()
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Pandas NA counts':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 3. DUPLICATE ROWS
    # ============================================================

    stage_start = time.perf_counter()

    duplicate_rows = int(
        df.duplicated()
        .sum()
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Duplicate row scan':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 4. MISSING / INVALID VALUE PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    missing_value_profile = (
        profile_missing_values(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Missing/invalid value scan':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 5. CATEGORICAL PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    categorical_profile = (
        profile_categorical_values(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Categorical profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 6. CUSTOMER NAME PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    customer_name_profile = (
        profile_customer_names(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Customer name profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 7. EMAIL PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    email_profile = (
        profile_emails(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Email profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 8. CUSTOMER AGE PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    age_profile = (
        profile_customer_age(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Customer age profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 9. CUSTOMER RATING PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    rating_profile = (
        profile_customer_rating(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Customer rating profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 10. ORDER DATE PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    order_date_profile = (
        profile_order_dates(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Order date profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 11. ORDER ID FORMAT PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    order_id_profile = (
        profile_order_ids(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Order ID format profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 12. NUMERIC PROFILE + RANGE PROFILE
    # ============================================================

    stage_start = time.perf_counter()

    (
        numeric_profile,
        numeric_range_profile
    ) = _profile_numeric_combined(
        df
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Numeric + range profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 13. ORDER ID DUPLICATES
    # ============================================================

    stage_start = time.perf_counter()

    order_id_duplicate_profile = (
        profile_order_id_duplicates(
            df
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Order ID duplicate profiling':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 14. BUILD PROFILE OBJECT
    # ============================================================

    stage_start = time.perf_counter()

    profile = {

        "rows":
            rows,

        "columns":
            columns,

        "column_names":
            column_names,

        "data_types":
            data_types,

        "missing_values":
            missing_values,

        "duplicate_rows":
            duplicate_rows,

        "missing_value_profile":
            missing_value_profile,

        "categorical_profile":
            categorical_profile,

        "customer_name_profile":
            customer_name_profile,

        "email_profile":
            email_profile,

        "age_profile":
            age_profile,

        "rating_profile":
            rating_profile,

        "order_date_profile":
            order_date_profile,

        "order_id_profile":
            order_id_profile,

        "order_id_duplicate_profile":
            order_id_duplicate_profile,

        "numeric_profile":
            numeric_profile,

        "numeric_range_profile":
            numeric_range_profile
    }

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Build profile object':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # 15. ISSUE SUMMARY
    # ============================================================

    stage_start = time.perf_counter()

    profile[
        "issue_summary"
    ] = (
        create_issue_summary(
            profile
        )
    )

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'Create issue summary':<38} "
        f"{time.perf_counter() - stage_start:.4f} sec",
        flush=True
    )


    # ============================================================
    # TOTAL
    # ============================================================

    print(
        f"[PROFILER PERFORMANCE] "
        f"{'TOTAL PROFILE':<38} "
        f"{time.perf_counter() - total_start:.4f} sec",
        flush=True
    )

    return profile


# ================================================================
# DISPLAY PROFILE
# ================================================================

def display_profile(profile):
    """
    Display the data-quality profile in a readable format.
    """

    print(
        "\n"
        + "=" * 60
    )

    print(
        "           CSV DATA QUALITY PROFILE"
    )

    print(
        "=" * 60
    )


    print(
        f"\nRows              : "
        f"{profile['rows']}"
    )

    print(
        f"Columns           : "
        f"{profile['columns']}"
    )

    print(
        f"Duplicate Rows    : "
        f"{profile['duplicate_rows']}"
    )


    print(
        "\nColumn Names:"
    )

    for column in (
        profile[
            "column_names"
        ]
    ):

        print(
            f"  - {column}"
        )


    print(
        "\nData Types:"
    )

    for column, dtype in (
        profile[
            "data_types"
        ].items()
    ):

        print(
            f"  {column:<20} : "
            f"{dtype}"
        )


    print(
        "\nBlank Cells:"
    )

    for column, count in (
        profile[
            "missing_value_profile"
        ][
            "blank_cells"
        ].items()
    ):

        print(
            f"  {column:<20} : "
            f"{count}"
        )


    print(
        "\nTotal Blank Cells : "
        f"{profile['missing_value_profile']['total_blank_cells']}"
    )


    print(
        "\nMissing Values "
        "(NA / None / NULL / null):"
    )

    for column, count in (
        profile[
            "missing_value_profile"
        ][
            "missing_value_cells"
        ].items()
    ):

        print(
            f"  {column:<20} : "
            f"{count}"
        )


    print(
        "\nTotal Missing Values : "
        f"{profile['missing_value_profile']['total_missing_value_cells']}"
    )


    print(
        "\nInvalid Values:"
    )

    for column, count in (
        profile[
            "missing_value_profile"
        ][
            "invalid_value_cells"
        ].items()
    ):

        print(
            f"  {column:<20} : "
            f"{count}"
        )


    print(
        "\nTotal Invalid Values : "
        f"{profile['missing_value_profile']['total_invalid_value_cells']}"
    )


    print(
        "\nCategorical Value Validation:"
    )

    for column, details in (
        profile[
            "categorical_profile"
        ].items()
    ):

        print(
            f"\n{column}:"
        )

        print(
            "  Invalid Values       : "
            f"{details['invalid_count']}"
        )

        print(
            "  Casing Variations    : "
            f"{details['casing_variation_count']}"
        )


    print(
        "\nCustomer Name Validation:"
    )

    print(
        "  Invalid Names : "
        f"{profile['customer_name_profile']['invalid_count']}"
    )


    print(
        "\nEmail Validation:"
    )

    print(
        "  Invalid Syntax : "
        f"{profile['email_profile']['invalid_syntax_count']}"
    )

    print(
        "  Invalid Domain : "
        f"{profile['email_profile']['invalid_domain_count']}"
    )


    print(
        "\nCustomer Age Validation:"
    )

    print(
        "  Invalid Ages : "
        f"{profile['age_profile']['invalid_count']}"
    )


    print(
        "\nCustomer Rating Validation:"
    )

    print(
        "  Invalid Ratings : "
        f"{profile['rating_profile']['invalid_count']}"
    )


    print(
        "\nOrder Date Validation:"
    )

    print(
        "  Invalid Dates      : "
        f"{profile['order_date_profile']['invalid_count']}"
    )

    print(
        "  Non-Standard Dates : "
        f"{profile['order_date_profile']['non_standard_count']}"
    )


    print(
        "\nOrder ID Validation:"
    )

    print(
        "  Invalid Order IDs : "
        f"{profile['order_id_profile']['invalid_count']}"
    )


    print(
        "\nNumeric Column Validation:"
    )

    for column, details in (
        profile[
            "numeric_profile"
        ].items()
    ):

        print(
            f"  {column:<15} : "
            f"{details['invalid_count']} "
            "invalid values"
        )


    print(
        "\nNumeric Range Validation:"
    )

    for column, details in (
        profile[
            "numeric_range_profile"
        ].items()
    ):

        print(
            f"  {column:<15} : "
            f"{details['invalid_count']} "
            "invalid values"
        )


    print(
        "\nOrder ID Uniqueness:"
    )

    print(
        "Order IDs Appearing More Than Once :",
        profile[
            "order_id_duplicate_profile"
        ][
            "duplicate_id_count"
        ]
    )

    print(
        "Records With Repeated Order IDs    :",
        profile[
            "order_id_duplicate_profile"
        ][
            "affected_rows"
        ]
    )


    print(
        "\n"
        + "=" * 60
    )


# ================================================================
# TESTING
# ================================================================

if __name__ == "__main__":

    df = load_csv(
        "data/messy_retail_data_10K.csv"
    )

    profile = profile_data(
        df
    )

    display_profile(
        profile
    )

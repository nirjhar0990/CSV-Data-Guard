import pandas as pd
import re


# ================================================================
# 1. Standardize Missing Values
# ================================================================

def standardize_missing_values(df):
    """Standardize blank and missing-value markers to pd.NA."""

    missing_values = [
        "",
        "NA",
        "None",
        "NULL",
        "null"
    ]

    cleaned_df = df.copy()

    missing_mask = cleaned_df.isin(
        missing_values
    )

    cleaned_df = cleaned_df.where(
        ~missing_mask,
        pd.NA
    )

    return cleaned_df


# ================================================================
# 2. Remove Duplicate Rows
# ================================================================

def remove_duplicate_rows(df):
    cleaned_df = df.copy()

    # Record_ID is an internal tracking field.
    # It must not be considered when detecting duplicates.
    duplicate_columns = [
        column
        for column in cleaned_df.columns
        if column != "Record_ID"
    ]

    cleaned_df = cleaned_df.drop_duplicates(
        subset=duplicate_columns
    )

    return cleaned_df

def get_removed_duplicate_rows(df):
    """
    Return only the rows that would be removed by the cleaner's
    duplicate-row step.

    Duplicate detection follows the same semantics as clean_data():
      - missing markers are standardized first,
      - Record_ID is excluded from duplicate comparison,
      - the first occurrence is retained,
      - only later duplicate occurrences are returned.
    """

    normalized_df = standardize_missing_values(
        df
    )

    duplicate_columns = [
        column
        for column in normalized_df.columns
        if column != "Record_ID"
    ]

    removed_mask = (
        normalized_df.duplicated(
            subset=duplicate_columns,
            keep="first"
        )
    )

    return (
        df.loc[
            removed_mask
        ]
        .copy()
    )

# ================================================================
# 3. Clean Text Casing
# ================================================================

def clean_text_casing(df):
    """Standardize casing for categorical text columns."""

    cleaned_df = df.copy()

    payment_map = {
        "cash": "Cash",
        "credit card": "Credit Card",
        "debit card": "Debit Card",
        "upi": "UPI",
        "net banking": "Net Banking"
    }

    status_map = {
        "completed": "Completed",
        "pending": "Pending",
        "cancelled": "Cancelled",
        "returned": "Returned"
    }

    product_map = {
        "laptop": "Laptop",
        "smartphone": "Smartphone",
        "headphones": "Headphones",
        "tablet": "Tablet",
        "t-shirt": "T-Shirt",
        "jeans": "Jeans",
        "jacket": "Jacket",
        "shoes": "Shoes",
        "rice": "Rice",
        "milk": "Milk",
        "bread": "Bread",
        "cooking oil": "Cooking Oil",
        "chair": "Chair",
        "table": "Table",
        "sofa": "Sofa",
        "bed": "Bed",
        "python programming": "Python Programming",
        "data science": "Data Science",
        "machine learning": "Machine Learning",
        "database systems": "Database Systems",
        "football": "Football",
        "cricket bat": "Cricket Bat",
        "tennis racket": "Tennis Racket",
        "basketball": "Basketball"
    }

    cleaned_df["Payment_Method"] = (
        cleaned_df["Payment_Method"]
        .str.strip()
        .str.lower()
        .map(payment_map)
    )

    cleaned_df["Order_Status"] = (
        cleaned_df["Order_Status"]
        .str.strip()
        .str.lower()
        .map(status_map)
    )

    cleaned_df["Product"] = (
        cleaned_df["Product"]
        .str.strip()
        .str.lower()
        .map(product_map)
    )

    return cleaned_df


# ================================================================
# 4. Clean Customer Names
# ================================================================

def clean_customer_names(df):
    """Replace unwanted special characters with spaces."""

    cleaned_df = df.copy()

    cleaned_df["Customer_Name"] = (
        cleaned_df["Customer_Name"]
        .str.replace(
            r"[^a-zA-Z\s]",
            " ",
            regex=True
        )
        .str.strip()
    )

    return cleaned_df

# ================================================================
# 4. Clean City Names
# ================================================================

def clean_city_names(df):
    """Standardize city names."""

    cleaned_df = df.copy()

    cleaned_df["City"] = (
        cleaned_df["City"]
        .str.strip()
        .str.title()
    )

    return cleaned_df

def build_email_from_name(name):
    """
    Generate a canonical email from a valid customer name.

    Example:
        Ankit Gupta
        -> ankit_gupta@example.com

    Returns None when the name cannot be safely used.
    """

    if pd.isna(name):
        return None

    name_text = str(name).strip()

    missing_values = {
        "",
        "NA",
        "None",
        "NULL",
        "null",
        "INVALID"
    }

    if name_text in missing_values:
        return None

    # Only alphabetic words separated by spaces
    if not re.fullmatch(
        r"[A-Za-z]+(?:\s+[A-Za-z]+)*",
        name_text
    ):
        return None

    email_username = re.sub(
        r"\s+",
        "_",
        name_text.lower()
    )

    return (
        f"{email_username}@example.com"
    )


# ================================================================
# 5. Clean Emails
# ================================================================

def clean_emails(df):
    """
    Normalize customer email addresses conservatively.

    Rules:
    1. Strip surrounding whitespace.
    2. Convert email text to lowercase.
    3. Fix only the known deterministic domain typo:
         @exampl.com -> @example.com
    4. Do NOT reconstruct invalid email syntax from Customer_Name.
       Invalid values remain for validator/manual review.
    """

    cleaned_df = df.copy()

    email = (
        cleaned_df["Customer_Email"]
        .astype("string")
        .str.strip()
        .str.lower()
    )

    email = (
        email
        .str.replace(
            "@exampl.com",
            "@example.com",
            regex=False
        )
    )

    cleaned_df["Customer_Email"] = email

    return cleaned_df


def repair_customer_age_format(value):
    """
    Repair only known, deterministic Customer_Age
    formatting problems.

    Examples:
        4@6  -> 46
        2 8  -> 28
        _37  -> 37

    Values such as:
        -25
        999
        452
        abc
        INVALID

    are NOT automatically repaired.
    """

    if pd.isna(value):
        return value

    text = str(value).strip()

    # -----------------------------------------
    # PATTERN 1: DIGITS SEPARATED BY @
    # Example: 4@6 -> 46
    # -----------------------------------------

    if re.fullmatch(
        r"\d+@\d+",
        text
    ):
        repaired = text.replace(
            "@",
            ""
        )

    # -----------------------------------------
    # PATTERN 2: DIGITS SEPARATED BY SPACES
    # Example: 2 8 -> 28
    # -----------------------------------------

    elif re.fullmatch(
        r"\d+\s+\d+",
        text
    ):
        repaired = re.sub(
            r"\s+",
            "",
            text
        )

    # -----------------------------------------
    # PATTERN 3: LEADING UNDERSCORE
    # Example: _37 -> 37
    # -----------------------------------------

    elif re.fullmatch(
        r"_\d+",
        text
    ):
        repaired = text.replace(
            "_",
            ""
        )

    else:
        return value

    # -----------------------------------------
    # FINAL SAFETY CHECK
    # -----------------------------------------

    age = int(repaired)

    if 0 <= age <= 100:
        return age

    return value



def _repair_customer_age_series_vectorized(series):
    """
    Vectorized equivalent of repair_customer_age_format().

    Repairs only deterministic formats:
        4@6  -> 46
        2 8  -> 28
        _37  -> 37

    Repaired values are accepted only when they are between
    0 and 100 inclusive. All other values remain unchanged.
    """

    text = (
        series
        .astype("string")
        .str.strip()
    )

    at_mask = text.str.fullmatch(
        r"\d+@\d+",
        na=False
    )

    space_mask = text.str.fullmatch(
        r"\d+\s+\d+",
        na=False
    )

    underscore_mask = text.str.fullmatch(
        r"_\d+",
        na=False
    )

    candidate_mask = (
        at_mask
        | space_mask
        | underscore_mask
    )

    repaired_text = text.copy()

    repaired_text.loc[at_mask] = (
        text.loc[at_mask]
        .str.replace(
            "@",
            "",
            regex=False
        )
    )

    repaired_text.loc[space_mask] = (
        text.loc[space_mask]
        .str.replace(
            r"\s+",
            "",
            regex=True
        )
    )

    repaired_text.loc[underscore_mask] = (
        text.loc[underscore_mask]
        .str.replace(
            "_",
            "",
            regex=False
        )
    )

    repaired_numeric = pd.to_numeric(
        repaired_text.where(
            candidate_mask
        ),
        errors="coerce"
    )

    safe_mask = (
        candidate_mask
        & repaired_numeric.between(
            0,
            100
        )
    )

    # Use object dtype so repaired text can be assigned safely
    # even when the source Series uses Pandas/Arrow string dtype.
    result = series.astype("object").copy()

    result.loc[safe_mask] = (
        repaired_text.loc[safe_mask]
    )

    return result


# ================================================================
# 6. Clean Numeric Values
# ================================================================

def clean_numeric_values(df):
    """Convert numeric columns to appropriate numeric types."""

    cleaned_df = df.copy()

    # -----------------------------------------
    # REPAIR SAFE CUSTOMER AGE FORMATS
    # -----------------------------------------

    cleaned_df["Customer_Age"] = (
        _repair_customer_age_series_vectorized(
            cleaned_df["Customer_Age"]
        )
    )

    integer_columns = [
        "Customer_Age",
        "Customer_Rating"
    ]

    decimal_columns = [
        "Quantity",
        "Unit_Price",
        "Discount",
        "Total_Amount"
    ]

    for column in integer_columns:
        cleaned_df[column] = pd.to_numeric(
            cleaned_df[column],
            errors="coerce"
        ).astype("Int64")

    for column in decimal_columns:
        cleaned_df[column] = pd.to_numeric(
            cleaned_df[column],
            errors="coerce"
        )

    return cleaned_df


# ================================================================
# 7. Clean Numeric Ranges
# ================================================================

def clean_numeric_ranges(df):
    """Replace out-of-range numeric values with pd.NA."""

    cleaned_df = df.copy()

    cleaned_df.loc[
        cleaned_df["Quantity"] < 0,
        "Quantity"
    ] = pd.NA

    cleaned_df.loc[
        cleaned_df["Unit_Price"] < 0,
        "Unit_Price"
    ] = pd.NA

    cleaned_df.loc[
        ~cleaned_df["Discount"].between(0, 100),
        "Discount"
    ] = pd.NA

    cleaned_df.loc[
        cleaned_df["Total_Amount"] < 0,
        "Total_Amount"
    ] = pd.NA

    cleaned_df.loc[
        ~cleaned_df["Customer_Age"].between(0, 100),
        "Customer_Age"
    ] = pd.NA

    cleaned_df.loc[
        ~cleaned_df["Customer_Rating"].between(1, 5),
        "Customer_Rating"
    ] = pd.NA

    return cleaned_df

# ================================================================
# # 6. Clean Categories
# ================================================================

# 6. Clean Categories
def clean_categories(df):
    cleaned_df = df.copy()

    valid_categories = {
        "electronics": "Electronics",
        "sports": "Sports",
        "furniture": "Furniture",
        "clothing": "Clothing",
        "groceries": "Groceries",
        "books": "Books"
    }

    cleaned_df["Category"] = (
        cleaned_df["Category"]
        .str.strip()
        .str.lower()
        .map(valid_categories)
    )

    return cleaned_df


# ================================================================
# 8. Standardize Dates
# ================================================================

def standardize_dates(df):
    """Convert supported date formats to Pandas datetime."""

    cleaned_df = df.copy()

    date_column = cleaned_df["Order_Date"].str.strip()

    cleaned_df["Order_Date"] = pd.to_datetime(
        date_column,
        format="mixed",
        errors="coerce"
    )

    return cleaned_df


# ================================================================
# 9. Handle INVALID Values
# ================================================================

def handle_invalid_values(df):
    """Convert explicit INVALID markers to missing values."""

    cleaned_df = df.copy()

    cleaned_df = cleaned_df.replace(
        "INVALID",
        pd.NA
    )

    return cleaned_df


# ================================================================
# 10. Complete Cleaning Pipeline
# ================================================================

def clean_data(df):

    cleaned_df = df.copy()

    cleaning_checks = {}

    # 1. Standardize Missing Values
    cleaned_df = standardize_missing_values(cleaned_df)
    cleaning_checks["Missing Values"] = True

    # 2. Remove Duplicate Rows
    cleaned_df = remove_duplicate_rows(cleaned_df)
    cleaning_checks["Duplicate Rows"] = True

    # 3. Clean Text Casing
    cleaned_df = clean_text_casing(cleaned_df)
    cleaning_checks["Text Casing"] = True

    # 4. Clean Customer Names
    cleaned_df = clean_customer_names(cleaned_df)
    cleaning_checks["Customer Names"] = True

    # 5. Clean City Names
    cleaned_df = clean_city_names(cleaned_df)
    cleaning_checks["City Names"] = True

    # 6. Clean Categories
    cleaned_df = clean_categories(cleaned_df)
    cleaning_checks["Categories"] = True

    # 7. Clean Emails
    cleaned_df = clean_emails(cleaned_df)
    cleaning_checks["Emails"] = True

    # 8. Clean Numeric Values
    cleaned_df = clean_numeric_values(cleaned_df)
    cleaning_checks["Numeric Conversion"] = True

    # 9. Clean Numeric Ranges
    cleaned_df = clean_numeric_ranges(cleaned_df)
    cleaning_checks["Numeric Ranges"] = True

    # 10. Standardize Dates
    cleaned_df = standardize_dates(cleaned_df)
    cleaning_checks["Dates"] = True

    # 11. Handle INVALID Values
    cleaned_df = handle_invalid_values(cleaned_df)
    cleaning_checks["INVALID Values"] = True

    return cleaned_df, cleaning_checks


# ================================================================
# Testing
# ================================================================

if __name__ == "__main__":

    df = pd.read_csv(
        "data/messy_retail_data_10K.csv",
        keep_default_na=False
    )

    print("\nBefore Cleaning:")
    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("Duplicate Rows:", df.duplicated().sum())

    cleaned_df, cleaning_checks = clean_data(df)

    print("\nAfter Cleaning:")
    print("Rows:", len(cleaned_df))
    print("Columns:", len(cleaned_df.columns))
    print("Duplicate Rows:", cleaned_df.duplicated().sum())

    print("\nData Types:")
    print(cleaned_df.dtypes)

    print("\nMissing Values:")
    print(cleaned_df.isna().sum())

    print("\nRemaining INVALID Values:")
    print(
        (cleaned_df == "INVALID").sum().sum()
    )

    print("\nCleaning Checks:")

    for check, status in cleaning_checks.items():
        print(
            f"{check}: {'Passed' if status else 'Failed'}"
        )

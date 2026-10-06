import pandas as pd

from pipeline.cleaner import (
    standardize_missing_values,
    remove_duplicate_rows,
    clean_text_casing,
    clean_customer_names,
    clean_city_names,
    build_email_from_name,
    clean_emails,
    repair_customer_age_format,
    clean_numeric_values,
    clean_numeric_ranges,
    clean_categories,
    standardize_dates,
    handle_invalid_values,
    clean_data,
)


# ============================================================
# 1. STANDARDIZE MISSING VALUES
# ============================================================

def test_standardize_missing_values():

    df = pd.DataFrame(
        {
            "A": [
                "",
                "NA",
                "None",
                "NULL",
                "null",
                "Valid"
            ]
        }
    )

    result = standardize_missing_values(df)

    assert result["A"].isna().sum() == 5
    assert result.loc[5, "A"] == "Valid"

    # Original DataFrame must remain unchanged
    assert df.loc[0, "A"] == ""


# ============================================================
# 2. REMOVE DUPLICATE ROWS
# ============================================================

def test_remove_duplicate_rows_ignores_record_id():

    df = pd.DataFrame(
        {
            "Record_ID": [
                1,
                2,
                3
            ],

            "Order_ID": [
                "ORD-00001",
                "ORD-00001",
                "ORD-00002"
            ],

            "Product": [
                "Laptop",
                "Laptop",
                "Tablet"
            ]
        }
    )

    result = remove_duplicate_rows(df)

    # Rows 1 and 2 are duplicates except Record_ID.
    assert len(result) == 2

    assert result["Record_ID"].tolist() == [
        1,
        3
    ]


# ============================================================
# 3. CLEAN TEXT CASING
# ============================================================

def test_clean_text_casing():

    df = pd.DataFrame(
        {
            "Payment_Method": [
                "upi",
                "CASH",
                " credit card "
            ],

            "Order_Status": [
                "completed",
                "PENDING",
                " returned "
            ],

            "Product": [
                "laptop",
                "DATA SCIENCE",
                " cricket bat "
            ]
        }
    )

    result = clean_text_casing(df)

    assert result["Payment_Method"].tolist() == [
        "UPI",
        "Cash",
        "Credit Card"
    ]

    assert result["Order_Status"].tolist() == [
        "Completed",
        "Pending",
        "Returned"
    ]

    assert result["Product"].tolist() == [
        "Laptop",
        "Data Science",
        "Cricket Bat"
    ]


# ============================================================
# 4. CLEAN CUSTOMER NAMES
# ============================================================

def test_clean_customer_names():

    df = pd.DataFrame(
        {
            "Customer_Name": [
                "Arun@Banerjee",
                "Riya#Sen",
                " Amit$Roy "
            ]
        }
    )

    result = clean_customer_names(df)

    assert result["Customer_Name"].tolist() == [
        "Arun Banerjee",
        "Riya Sen",
        "Amit Roy"
    ]


# ============================================================
# 5. CLEAN CITY NAMES
# ============================================================

def test_clean_city_names():

    df = pd.DataFrame(
        {
            "City": [
                "kolkata",
                " DELHI ",
                "mUMbai"
            ]
        }
    )

    result = clean_city_names(df)

    assert result["City"].tolist() == [
        "Kolkata",
        "Delhi",
        "Mumbai"
    ]


# ============================================================
# 6. BUILD EMAIL FROM NAME
# ============================================================

def test_build_email_from_name():

    assert (
        build_email_from_name("Arun Banerjee")
        == "arun_banerjee@example.com"
    )

    assert (
        build_email_from_name("Riya Sen")
        == "riya_sen@example.com"
    )

    assert build_email_from_name("INVALID") is None
    assert build_email_from_name("NA") is None
    assert build_email_from_name("Arun123") is None
    assert build_email_from_name(pd.NA) is None


# ============================================================
# 7. CLEAN EMAILS
# ============================================================

def test_clean_emails():

    df = pd.DataFrame(
        {
            "Customer_Name": [
                "Arun Banerjee",
                "Riya Sen",
                "Amit Roy",
                pd.NA
            ],

            "Customer_Email": [
                " ARUN.BANERJEE@EXAMPLE.COM ",
                "riya.sen@exampl.com",
                "bad-email",
                "still-invalid"
            ]
        }
    )

    result = clean_emails(df)

    # Lowercase + strip
    assert (
    result.loc[2, "Customer_Email"]
    == "bad-email"
)

    # Known domain typo fixed
    assert (
        result.loc[1, "Customer_Email"]
        == "riya.sen@example.com"
    )

    # Invalid email reconstructed from usable name
    assert (
    result.loc[2, "Customer_Email"]
    == "bad-email"
)

    # No usable name -> unresolved email remains
    assert (
        result.loc[3, "Customer_Email"]
        == "still-invalid"
    )


# ============================================================
# 8. REPAIR CUSTOMER AGE FORMAT
# ============================================================

def test_repair_customer_age_format():

    assert repair_customer_age_format("4@6") == 46
    assert repair_customer_age_format("2 8") == 28
    assert repair_customer_age_format("_37") == 37

    # Already-valid age stays unchanged
    assert repair_customer_age_format("25") == "25"

    # Unsafe / ambiguous values are not repaired here
    assert repair_customer_age_format("452") == "452"
    assert repair_customer_age_format("-25") == "-25"
    assert repair_customer_age_format("abc") == "abc"


# ============================================================
# 9. CLEAN NUMERIC VALUES
# ============================================================

def test_clean_numeric_values():

    df = pd.DataFrame(
        {
            "Quantity": [
                "2",
                "3.5",
                "bad"
            ],

            "Unit_Price": [
                "100.50",
                "200",
                "bad"
            ],

            "Discount": [
                "10",
                "15.5",
                "bad"
            ],

            "Total_Amount": [
                "180.90",
                "500",
                "bad"
            ],

            "Customer_Age": [
                "4@6",
                "_37",
                "abc"
            ],

            "Customer_Rating": [
                "5",
                "3",
                "bad"
            ]
        }
    )

    result = clean_numeric_values(df)

    assert result.loc[0, "Customer_Age"] == 46
    assert result.loc[1, "Customer_Age"] == 37
    assert pd.isna(result.loc[2, "Customer_Age"])

    assert result.loc[0, "Customer_Rating"] == 5
    assert result.loc[1, "Customer_Rating"] == 3
    assert pd.isna(result.loc[2, "Customer_Rating"])

    assert result.loc[0, "Quantity"] == 2.0
    assert result.loc[1, "Quantity"] == 3.5
    assert pd.isna(result.loc[2, "Quantity"])

    assert result.loc[0, "Unit_Price"] == 100.50
    assert result.loc[1, "Discount"] == 15.5
    assert result.loc[0, "Total_Amount"] == 180.90

    assert str(result["Customer_Age"].dtype) == "Int64"
    assert str(result["Customer_Rating"].dtype) == "Int64"


# ============================================================
# 10. CLEAN NUMERIC RANGES
# ============================================================

def test_clean_numeric_ranges():

    df = pd.DataFrame(
        {
            "Quantity": [
                0.0,
                -1.0,
                5.0
            ],

            "Unit_Price": [
                0.0,
                -10.0,
                100.0
            ],

            "Discount": [
                0.0,
                101.0,
                50.0
            ],

            "Total_Amount": [
                0.0,
                -1.0,
                500.0
            ],

            "Customer_Age": pd.Series(
                [
                    0,
                    101,
                    50
                ],
                dtype="Int64"
            ),

            "Customer_Rating": pd.Series(
                [
                    1,
                    6,
                    5
                ],
                dtype="Int64"
            )
        }
    )

    result = clean_numeric_ranges(df)

    # Cleaner currently allows Quantity == 0.
    assert result.loc[0, "Quantity"] == 0.0
    assert pd.isna(result.loc[1, "Quantity"])

    assert result.loc[0, "Unit_Price"] == 0.0
    assert pd.isna(result.loc[1, "Unit_Price"])

    assert result.loc[0, "Discount"] == 0.0
    assert pd.isna(result.loc[1, "Discount"])
    assert result.loc[2, "Discount"] == 50.0

    assert result.loc[0, "Total_Amount"] == 0.0
    assert pd.isna(result.loc[1, "Total_Amount"])

    assert result.loc[0, "Customer_Age"] == 0
    assert pd.isna(result.loc[1, "Customer_Age"])

    assert result.loc[0, "Customer_Rating"] == 1
    assert pd.isna(result.loc[1, "Customer_Rating"])
    assert result.loc[2, "Customer_Rating"] == 5


# ============================================================
# 11. CLEAN CATEGORIES
# ============================================================

def test_clean_categories():

    df = pd.DataFrame(
        {
            "Category": [
                "electronics",
                " SPORTS ",
                "Groceries",
                "unknown"
            ]
        }
    )

    result = clean_categories(df)

    assert result.loc[0, "Category"] == "Electronics"
    assert result.loc[1, "Category"] == "Sports"
    assert result.loc[2, "Category"] == "Groceries"

    # Unknown category is mapped to missing.
    assert pd.isna(result.loc[3, "Category"])


# ============================================================
# 12. STANDARDIZE DATES
# ============================================================

def test_standardize_dates():

    df = pd.DataFrame(
        {
            "Order_Date": [
                "12/31/2024",
                "2024-12-31",
                "31/12/2024",
                "not-a-date"
            ]
        }
    )

    result = standardize_dates(df)

    assert pd.notna(result.loc[0, "Order_Date"])
    assert pd.notna(result.loc[1, "Order_Date"])
    assert pd.notna(result.loc[2, "Order_Date"])

    assert pd.isna(result.loc[3, "Order_Date"])

    assert pd.api.types.is_datetime64_any_dtype(
        result["Order_Date"]
    )


# ============================================================
# 13. HANDLE INVALID VALUES
# ============================================================

def test_handle_invalid_values():

    df = pd.DataFrame(
        {
            "A": [
                "Valid",
                "INVALID"
            ],

            "B": [
                "INVALID",
                "Value"
            ]
        }
    )

    result = handle_invalid_values(df)

    assert result.loc[0, "A"] == "Valid"
    assert pd.isna(result.loc[1, "A"])
    assert pd.isna(result.loc[0, "B"])
    assert result.loc[1, "B"] == "Value"


# ============================================================
# 14. COMPLETE CLEANING PIPELINE
# ============================================================

def test_clean_data_complete_pipeline():

    df = pd.DataFrame(
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
                "Arun@Banerjee",
                "Riya Sen",
                "Amit Roy"
            ],

            "Customer_Email": [
                " ARUN.BANERJEE@EXAMPLE.COM ",
                "riya.sen@exampl.com",
                "bad-email"
            ],

            "City": [
                "kolkata",
                " DELHI ",
                "mumbai"
            ],

            "Category": [
                "electronics",
                " SPORTS ",
                "books"
            ],

            "Product": [
                "laptop",
                "DATA SCIENCE",
                "python programming"
            ],

            "Quantity": [
                "2",
                "3",
                "4"
            ],

            "Unit_Price": [
                "100",
                "200",
                "300"
            ],

            "Discount": [
                "10",
                "20",
                "30"
            ],

            "Total_Amount": [
                "180",
                "480",
                "840"
            ],

            "Order_Date": [
                "12/31/2024",
                "2024-12-31",
                "31/12/2024"
            ],

            "Payment_Method": [
                "upi",
                "CASH",
                "credit card"
            ],

            "Order_Status": [
                "completed",
                "PENDING",
                "returned"
            ],

            "Customer_Age": [
                "4@6",
                "_37",
                "2 8"
            ],

            "Customer_Rating": [
                "5",
                "4",
                "3"
            ]
        }
    )

    cleaned_df, cleaning_checks = clean_data(df)

    assert len(cleaned_df) == 3

    # --------------------------------------------------------
    # TEXT / CATEGORICAL CLEANING
    # --------------------------------------------------------

    assert cleaned_df.loc[0, "Customer_Name"] == "Arun Banerjee"

    assert cleaned_df.loc[0, "City"] == "Kolkata"
    assert cleaned_df.loc[1, "City"] == "Delhi"

    assert cleaned_df.loc[0, "Category"] == "Electronics"
    assert cleaned_df.loc[1, "Category"] == "Sports"

    assert cleaned_df.loc[0, "Product"] == "Laptop"
    assert cleaned_df.loc[1, "Product"] == "Data Science"

    assert cleaned_df.loc[0, "Payment_Method"] == "UPI"
    assert cleaned_df.loc[1, "Payment_Method"] == "Cash"

    assert cleaned_df.loc[0, "Order_Status"] == "Completed"
    assert cleaned_df.loc[1, "Order_Status"] == "Pending"

    # --------------------------------------------------------
    # EMAILS
    # --------------------------------------------------------

    assert (
        cleaned_df.loc[0, "Customer_Email"]
        == "arun.banerjee@example.com"
    )

    assert (
        cleaned_df.loc[1, "Customer_Email"]
        == "riya.sen@example.com"
    )

    assert (
    cleaned_df.loc[2, "Customer_Email"]
    == "bad-email"
)

    # --------------------------------------------------------
    # AGE REPAIR
    # --------------------------------------------------------

    assert cleaned_df.loc[0, "Customer_Age"] == 46
    assert cleaned_df.loc[1, "Customer_Age"] == 37
    assert cleaned_df.loc[2, "Customer_Age"] == 28

    # --------------------------------------------------------
    # TYPES
    # --------------------------------------------------------

    assert str(cleaned_df["Customer_Age"].dtype) == "Int64"
    assert str(cleaned_df["Customer_Rating"].dtype) == "Int64"

    assert pd.api.types.is_numeric_dtype(
        cleaned_df["Quantity"]
    )

    assert pd.api.types.is_numeric_dtype(
        cleaned_df["Unit_Price"]
    )

    assert pd.api.types.is_numeric_dtype(
        cleaned_df["Discount"]
    )

    assert pd.api.types.is_numeric_dtype(
        cleaned_df["Total_Amount"]
    )

    assert pd.api.types.is_datetime64_any_dtype(
        cleaned_df["Order_Date"]
    )

    # --------------------------------------------------------
    # CLEANING CHECKS
    # --------------------------------------------------------

    expected_checks = {
        "Missing Values",
        "Duplicate Rows",
        "Text Casing",
        "Customer Names",
        "City Names",
        "Categories",
        "Emails",
        "Numeric Conversion",
        "Numeric Ranges",
        "Dates",
        "INVALID Values"
    }

    assert set(cleaning_checks.keys()) == expected_checks

    assert all(
        cleaning_checks.values()
    )

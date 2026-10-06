import pandas as pd

from pipeline.profiler import (
    load_csv,
    profile_missing_values,
    profile_categorical_values,
    profile_customer_names,
    profile_emails,
    profile_customer_age,
    profile_customer_rating,
    profile_order_dates,
    profile_order_ids,
    profile_order_id_duplicates,
    profile_numeric_columns,
    profile_numeric_ranges,
    _profile_numeric_combined,
    profile_data,
)


# ============================================================
# 1. LOAD CSV
# ============================================================

def test_load_csv_preserves_missing_tokens(tmp_path):

    file_path = tmp_path / "sample.csv"

    file_path.write_text(
        "A,B\n"
        "NA,None\n"
        "NULL,null\n"
        ",INVALID\n",
        encoding="utf-8"
    )

    df = load_csv(file_path)

    assert df.loc[0, "A"] == "NA"
    assert df.loc[0, "B"] == "None"

    assert df.loc[1, "A"] == "NULL"
    assert df.loc[1, "B"] == "null"

    assert df.loc[2, "A"] == ""
    assert df.loc[2, "B"] == "INVALID"


# ============================================================
# 2. MISSING / INVALID VALUES
# ============================================================

def test_profile_missing_values():

    df = pd.DataFrame(
        {
            "A": [
                "",
                "NA",
                "INVALID",
                "Valid"
            ],

            "B": [
                "null",
                "None",
                "NULL",
                "Valid"
            ]
        }
    )

    result = profile_missing_values(df)

    assert result["total_blank_cells"] == 1

    assert (
        result["total_missing_value_cells"]
        == 4
    )

    assert (
        result["total_invalid_value_cells"]
        == 1
    )

    assert result["blank_cells"]["A"] == 1
    assert result["missing_value_cells"]["A"] == 1
    assert result["invalid_value_cells"]["A"] == 1

    assert result["missing_value_cells"]["B"] == 3


# ============================================================
# 3. CATEGORICAL VALUES
# ============================================================

def test_profile_categorical_values():

    df = pd.DataFrame(
        {
            "Product": [
                "Laptop",
                "laptop",
                "INVALID",
                "Mystery Item"
            ],

            "Payment_Method": [
                "UPI",
                "upi",
                "Cash",
                "Bitcoin"
            ],

            "Order_Status": [
                "Completed",
                "completed",
                "INVALID",
                "Unknown"
            ],

            "City": [
                "Kolkata",
                "kolkata",
                "INVALID",
                "Atlantis"
            ],

            "Category": [
                "Books",
                "books",
                "INVALID",
                "Toys"
            ]
        }
    )

    result = profile_categorical_values(df)

    assert result["Product"]["invalid_count"] == 1
    assert result["Product"]["invalid_values"] == [
        "Mystery Item"
    ]

    assert (
        result["Product"]["casing_variation_count"]
        == 1
    )

    assert result["Product"]["casing_variations"] == [
        "laptop"
    ]

    assert (
        result["Payment_Method"]["invalid_values"]
        == ["Bitcoin"]
    )

    assert (
        result["Payment_Method"]["casing_variations"]
        == ["upi"]
    )

    assert (
        result["Order_Status"]["invalid_values"]
        == ["Unknown"]
    )

    assert (
        result["City"]["invalid_values"]
        == ["Atlantis"]
    )

    assert (
        result["Category"]["invalid_values"]
        == ["Toys"]
    )


# ============================================================
# 4. CUSTOMER NAME
# ============================================================

def test_profile_customer_names():

    df = pd.DataFrame(
        {
            "Customer_Name": [
                "Arun Banerjee",
                "Riya123",
                "Anne-Marie",
                "INVALID",
                "NA",
                ""
            ]
        }
    )

    result = profile_customer_names(df)

    assert result["invalid_count"] == 2

    assert result["invalid_names"] == [
        "Riya123",
        "Anne-Marie"
    ]


# ============================================================
# 5. EMAIL
# ============================================================

def test_profile_emails():

    df = pd.DataFrame(
        {
            "Customer_Email": [
                "arun.banerjee@example.com",
                "USER@EXAMPLE.COM",
                "bad-email",
                "user@test.com",
                "INVALID",
                "NA",
                ""
            ]
        }
    )

    result = profile_emails(df)

    assert result["invalid_syntax_count"] == 2

    assert result["invalid_syntax"] == [
        "bad-email",
        "INVALID"
    ]

    assert result["invalid_domain_count"] == 1

    assert result["invalid_domain"] == [
        "user@test.com"
    ]


# ============================================================
# 6. CUSTOMER AGE
# ============================================================

def test_profile_customer_age():

    df = pd.DataFrame(
        {
            "Customer_Age": [
                "25",
                "0",
                "100",
                "101",
                "-1",
                "25.0",
                "4@6",
                "INVALID",
                "NA",
                ""
            ]
        }
    )

    result = profile_customer_age(df)

    assert result["invalid_count"] == 4

    assert result["invalid_ages"] == [
        "101",
        "-1",
        "25.0",
        "4@6"
    ]


# ============================================================
# 7. CUSTOMER RATING
# ============================================================

def test_profile_customer_rating():

    df = pd.DataFrame(
        {
            "Customer_Rating": [
                "1",
                "5",
                "0",
                "6",
                "3.5",
                "bad",
                "INVALID",
                ""
            ]
        }
    )

    result = profile_customer_rating(df)

    assert result["invalid_count"] == 3

    assert result["invalid_ratings"] == [
        "0",
        "6",
        "bad"
    ]


# ============================================================
# 8. ORDER DATES
# ============================================================

def test_profile_order_dates():

    df = pd.DataFrame(
        {
            "Order_Date": [
                "12/31/2024",
                "31/12/2024",
                "12-31-2024",
                "2024-12-31",
                "December 31 2024",
                "not-a-date",
                "INVALID",
                "NA",
                ""
            ]
        }
    )

    result = profile_order_dates(df)

    assert result["invalid_count"] == 1

    assert result["invalid_dates"] == [
        "not-a-date"
    ]

    assert result["non_standard_count"] == 4

    assert result["non_standard_dates"] == [
        "31/12/2024",
        "12-31-2024",
        "2024-12-31",
        "December 31 2024"
    ]


# ============================================================
# 9. ORDER ID FORMAT
# ============================================================

def test_profile_order_ids():

    df = pd.DataFrame(
        {
            "Order_ID": [
                "ORD-12345",
                "ORD-00001",
                "ORD-1234",
                "ord-12345",
                "INVALID",
                "NA",
                ""
            ]
        }
    )

    result = profile_order_ids(df)

    assert result["invalid_count"] == 2

    assert result["invalid_order_ids"] == [
        "ORD-1234",
        "ord-12345"
    ]


# ============================================================
# 10. DUPLICATE ORDER IDS
# ============================================================

def test_profile_order_id_duplicates():

    df = pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001",
                "ORD-00001",
                "ORD-00002",
                "ORD-00003",
                "ORD-00003",
                "ORD-00003"
            ]
        }
    )

    result = profile_order_id_duplicates(df)

    assert result["duplicate_id_count"] == 2

    assert result["affected_rows"] == 5

    assert result["duplicate_ids"]["ORD-00001"] == 2
    assert result["duplicate_ids"]["ORD-00003"] == 3


# ============================================================
# 11. NUMERIC - NON NUMERIC VALUES
# ============================================================

def test_profile_numeric_columns():

    df = pd.DataFrame(
        {
            "Quantity": [
                "1",
                "abc",
                "INVALID"
            ],

            "Unit_Price": [
                "100",
                "bad",
                "NA"
            ],

            "Discount": [
                "10",
                "oops",
                ""
            ],

            "Total_Amount": [
                "500",
                "wrong",
                "None"
            ]
        }
    )

    result = profile_numeric_columns(df)

    assert (
        result["Quantity"]["invalid_values"]
        == ["abc"]
    )

    assert (
        result["Unit_Price"]["invalid_values"]
        == ["bad"]
    )

    assert (
        result["Discount"]["invalid_values"]
        == ["oops"]
    )

    assert (
        result["Total_Amount"]["invalid_values"]
        == ["wrong"]
    )


# ============================================================
# 12. NUMERIC RANGES
# ============================================================

def test_profile_numeric_ranges():

    df = pd.DataFrame(
        {
            "Quantity": [
                "1",
                "0",
                "-1",
                "abc",
                "INVALID",
                "NA"
            ],

            "Unit_Price": [
                "100",
                "0",
                "-10",
                "bad",
                "INVALID",
                "NA"
            ],

            "Discount": [
                "0",
                "50",
                "100",
                "101",
                "-1",
                "bad"
            ],

            "Total_Amount": [
                "0",
                "500",
                "-0.01",
                "bad",
                "INVALID",
                ""
            ]
        }
    )

    result = profile_numeric_ranges(df)

    assert result["Quantity"]["invalid_values"] == [
        "0",
        "-1"
    ]

    assert result["Quantity"]["invalid_count"] == 2

    assert result["Unit_Price"]["invalid_values"] == [
        "-10"
    ]

    assert result["Unit_Price"]["invalid_count"] == 1

    assert result["Discount"]["invalid_values"] == [
        "101",
        "-1"
    ]

    assert result["Discount"]["invalid_count"] == 2

    assert result["Total_Amount"]["invalid_values"] == [
        "-0.01"
    ]

    assert result["Total_Amount"]["invalid_count"] == 1


# ============================================================
# 13. SHARED NUMERIC OPTIMIZATION
# ============================================================

def test_combined_numeric_profile_matches_public_helpers():

    df = pd.DataFrame(
        {
            "Quantity": [
                "1",
                "0",
                "abc",
                "INVALID"
            ],

            "Unit_Price": [
                "100",
                "-10",
                "bad",
                "NA"
            ],

            "Discount": [
                "50",
                "101",
                "oops",
                ""
            ],

            "Total_Amount": [
                "500",
                "-5",
                "wrong",
                "None"
            ]
        }
    )

    (
        numeric_profile,
        numeric_range_profile
    ) = _profile_numeric_combined(df)

    expected_numeric = (
        profile_numeric_columns(df)
    )

    expected_ranges = (
        profile_numeric_ranges(df)
    )

    assert numeric_profile == expected_numeric

    assert (
        numeric_range_profile
        == expected_ranges
    )


# ============================================================
# 14. COMPLETE PROFILE DATA
# ============================================================

def test_profile_data_complete_profile():

    df = pd.DataFrame(
        {
            "Order_ID": [
                "ORD-00001",
                "ORD-00002"
            ],

            "Customer_Name": [
                "Arun Banerjee",
                "Riya123"
            ],

            "Customer_Email": [
                "arun.banerjee@example.com",
                "bad-email"
            ],

            "City": [
                "Kolkata",
                "Delhi"
            ],

            "Category": [
                "Books",
                "Electronics"
            ],

            "Product": [
                "Python Programming",
                "Laptop"
            ],

            "Quantity": [
                "1",
                "2"
            ],

            "Unit_Price": [
                "100",
                "500"
            ],

            "Discount": [
                "10",
                "20"
            ],

            "Total_Amount": [
                "90",
                "800"
            ],

            "Order_Date": [
                "12/31/2024",
                "31/12/2024"
            ],

            "Payment_Method": [
                "UPI",
                "Cash"
            ],

            "Order_Status": [
                "Completed",
                "Pending"
            ],

            "Customer_Age": [
                "30",
                "25"
            ],

            "Customer_Rating": [
                "5",
                "4"
            ]
        }
    )

    result = profile_data(df)

    assert result["rows"] == 2

    assert result["columns"] == 15

    assert result["duplicate_rows"] == 0

    assert "missing_value_profile" in result
    assert "categorical_profile" in result
    assert "customer_name_profile" in result
    assert "email_profile" in result
    assert "age_profile" in result
    assert "rating_profile" in result
    assert "order_date_profile" in result
    assert "order_id_profile" in result
    assert "order_id_duplicate_profile" in result
    assert "numeric_profile" in result
    assert "numeric_range_profile" in result
    assert "issue_summary" in result

    assert (
        result[
            "customer_name_profile"
        ][
            "invalid_count"
        ]
        == 1
    )

    assert (
        result[
            "email_profile"
        ][
            "invalid_syntax_count"
        ]
        == 1
    )

    assert (
        result[
            "order_date_profile"
        ][
            "non_standard_count"
        ]
        == 1
    )

import re
import pandas as pd


# ============================================================
# CONSTANTS
# ============================================================

MISSING_VALUES = {
    "",
    "NA",
    "None",
    "NULL",
    "null"
}

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)

EXPECTED_EMAIL_DOMAIN = "example.com"


# ============================================================
# CREATE PROBLEM MAP
# ============================================================

def create_problem_map(
    original_df,
    failure_cases,
    unresolved_issues
):
    """
    Create one shared problem map for reporting and review.

    Output columns:
        index
        column
        validation_error
        how_to_fix
        source
        reportable
        reviewable

    Meaning:
        reportable=True
            -> include in validation report

        reviewable=True
            -> include in manual review dataset

    Important behavior:

        1. Unresolved cleaning issues:
           reportable=True
           reviewable=True

        2. Original email syntax/domain issues:
           reportable=True
           reviewable=False

           They may already have been repaired automatically.

        3. Pandera Customer_Email failures:
           reportable=False
           reviewable=True

           Reporting already classifies the original email
           syntax/domain problem separately.

        4. Other Pandera failures:
           reportable=True
           reviewable=True
    """

    problem_parts = []


    # ========================================================
    # HELPER
    # ========================================================

    def add_problem_part(
        frame,
        column,
        error,
        fix,
        source,
        reportable=True,
        reviewable=True
    ):
        """
        Standardize a group of problem rows before adding it
        to the shared problem map.
        """

        if (
            frame is None
            or frame.empty
        ):
            return

        part = pd.DataFrame(
            {
                "index":
                    frame["index"].to_numpy(),

                "column":
                    column,

                "source":
                    source,

                "reportable":
                    reportable,

                "reviewable":
                    reviewable
            }
        )

        # ----------------------------------------------------
        # VALIDATION ERROR
        # ----------------------------------------------------

        if isinstance(
            error,
            pd.Series
        ):
            part[
                "validation_error"
            ] = error.to_numpy()

        else:
            part[
                "validation_error"
            ] = error


        # ----------------------------------------------------
        # HOW TO FIX
        # ----------------------------------------------------

        if isinstance(
            fix,
            pd.Series
        ):
            part[
                "how_to_fix"
            ] = fix.to_numpy()

        else:
            part[
                "how_to_fix"
            ] = fix


        problem_parts.append(
            part
        )


    # ========================================================
    # 1. UNRESOLVED CLEANING ISSUES
    # ========================================================

    if (
        unresolved_issues is not None
        and not unresolved_issues.empty
    ):

        unresolved = (
            unresolved_issues[
                [
                    "index",
                    "column",
                    "original_value"
                ]
            ]
            .copy()
        )


        for column in (
            unresolved[
                "column"
            ]
            .dropna()
            .unique()
        ):

            group = (
                unresolved[
                    unresolved[
                        "column"
                    ] == column
                ]
                .copy()
            )


            # =================================================
            # CUSTOMER RATING
            # =================================================

            if column == "Customer_Rating":

                numeric = pd.to_numeric(
                    group[
                        "original_value"
                    ],
                    errors="coerce"
                )

                invalid = (
                    numeric.isna()
                )

                below = (
                    numeric.notna()
                    &
                    (numeric < 1)
                )

                above = (
                    numeric.notna()
                    &
                    (numeric > 5)
                )

                problem_mask = (
                    invalid
                    |
                    below
                    |
                    above
                )

                group = (
                    group.loc[
                        problem_mask
                    ]
                    .copy()
                )

                if group.empty:
                    continue

                below = (
                    below.loc[
                        group.index
                    ]
                )

                above = (
                    above.loc[
                        group.index
                    ]
                )


                errors = pd.Series(
                    "Invalid customer rating",
                    index=group.index,
                    dtype="object"
                )

                fixes = pd.Series(
                    "Enter a numeric rating between 1 and 5.",
                    index=group.index,
                    dtype="object"
                )


                errors.loc[
                    below
                ] = (
                    "Rating is below the allowed range"
                )

                errors.loc[
                    above
                ] = (
                    "Rating is above the allowed range"
                )

                fixes.loc[
                    below | above
                ] = (
                    "Set the rating between 1 and 5."
                )


                add_problem_part(
                    group,
                    column,
                    errors,
                    fixes,
                    "cleaning",
                    reportable=True,
                    reviewable=True
                )

                continue


            # =================================================
            # CUSTOMER AGE
            # =================================================

            if column == "Customer_Age":

                numeric = pd.to_numeric(
                    group[
                        "original_value"
                    ],
                    errors="coerce"
                )

                invalid = (
                    numeric.isna()
                )

                below = (
                    numeric.notna()
                    &
                    (numeric < 0)
                )

                above = (
                    numeric.notna()
                    &
                    (numeric > 120)
                )

                problem_mask = (
                    invalid
                    |
                    below
                    |
                    above
                )

                group = (
                    group.loc[
                        problem_mask
                    ]
                    .copy()
                )

                if group.empty:
                    continue

                below = (
                    below.loc[
                        group.index
                    ]
                )

                above = (
                    above.loc[
                        group.index
                    ]
                )


                errors = pd.Series(
                    "Invalid customer age",
                    index=group.index,
                    dtype="object"
                )

                fixes = pd.Series(
                    "Enter a numeric age between 0 and 120.",
                    index=group.index,
                    dtype="object"
                )


                errors.loc[
                    below
                ] = (
                    "Age is below the allowed range"
                )

                errors.loc[
                    above
                ] = (
                    "Age is above the allowed range"
                )

                fixes.loc[
                    below | above
                ] = (
                    "Set the age between 0 and 120."
                )


                add_problem_part(
                    group,
                    column,
                    errors,
                    fixes,
                    "cleaning",
                    reportable=True,
                    reviewable=True
                )

                continue


            # =================================================
            # NUMERIC COLUMNS
            # =================================================

            if column in {
                "Quantity",
                "Unit_Price",
                "Discount",
                "Total_Amount"
            }:

                numeric = pd.to_numeric(
                    group[
                        "original_value"
                    ],
                    errors="coerce"
                )

                invalid = (
                    numeric.isna()
                )


                # ---------------------------------------------
                # QUANTITY
                # ---------------------------------------------

                if column == "Quantity":

                    below = (
                        numeric.notna()
                        &
                        (numeric < 0)
                    )

                    problem_mask = (
                        invalid
                        |
                        below
                    )

                    error_text = (
                        "Quantity is below the allowed range"
                    )

                    range_fix = (
                        "Set quantity to 0 or greater."
                    )


                # ---------------------------------------------
                # UNIT PRICE
                # ---------------------------------------------

                elif column == "Unit_Price":

                    below = (
                        numeric.notna()
                        &
                        (numeric < 0)
                    )

                    problem_mask = (
                        invalid
                        |
                        below
                    )

                    error_text = (
                        "Unit price is below the allowed range"
                    )

                    range_fix = (
                        "Set unit price to 0 or greater."
                    )


                # ---------------------------------------------
                # TOTAL AMOUNT
                # ---------------------------------------------

                elif column == "Total_Amount":

                    below = (
                        numeric.notna()
                        &
                        (numeric < 0)
                    )

                    problem_mask = (
                        invalid
                        |
                        below
                    )

                    error_text = (
                        "Total amount is below the allowed range"
                    )

                    range_fix = (
                        "Set total amount to 0 or greater."
                    )


                # ---------------------------------------------
                # DISCOUNT
                # ---------------------------------------------

                else:

                    below = (
                        numeric.notna()
                        &
                        (numeric < 0)
                    )

                    above = (
                        numeric.notna()
                        &
                        (numeric > 100)
                    )

                    problem_mask = (
                        invalid
                        |
                        below
                        |
                        above
                    )


                group = (
                    group.loc[
                        problem_mask
                    ]
                    .copy()
                )

                if group.empty:
                    continue


                errors = pd.Series(
                    (
                        "Invalid "
                        f"{column.replace('_', ' ').lower()}"
                    ),
                    index=group.index,
                    dtype="object"
                )

                fixes = pd.Series(
                    "Enter a valid numeric value.",
                    index=group.index,
                    dtype="object"
                )


                # ---------------------------------------------
                # DISCOUNT MESSAGE
                # ---------------------------------------------

                if column == "Discount":

                    below = (
                        below.loc[
                            group.index
                        ]
                    )

                    above = (
                        above.loc[
                            group.index
                        ]
                    )


                    errors.loc[
                        below
                    ] = (
                        "Discount is below the allowed range"
                    )

                    errors.loc[
                        above
                    ] = (
                        "Discount is above the allowed range"
                    )

                    fixes.loc[
                        below | above
                    ] = (
                        "Set discount between 0 and 100."
                    )


                # ---------------------------------------------
                # OTHER NUMERIC RANGE MESSAGES
                # ---------------------------------------------

                else:

                    below = (
                        below.loc[
                            group.index
                        ]
                    )

                    errors.loc[
                        below
                    ] = (
                        error_text
                    )

                    fixes.loc[
                        below
                    ] = (
                        range_fix
                    )


                add_problem_part(
                    group,
                    column,
                    errors,
                    fixes,
                    "cleaning",
                    reportable=True,
                    reviewable=True
                )

                continue


            # =================================================
            # STANDARD CLEANING MESSAGES
            # =================================================

            cleaning_messages = {

                "Customer_Name": (
                    "Invalid customer name",
                    "Use alphabetic characters and spaces only."
                ),

                "Category": (
                    "Invalid category",
                    "Use one of the allowed product categories."
                ),

                "Product": (
                    "Invalid product",
                    "Use a valid product name."
                ),

                "Payment_Method": (
                    "Invalid payment method",
                    "Use a valid payment method."
                ),

                "Order_Status": (
                    "Invalid order status",
                    "Use a valid order status."
                ),

                "Order_Date": (
                    "Invalid order date",
                    "Enter a valid date."
                ),

                "Order_ID": (
                    "Invalid order ID",
                    "Use the format ORD-12345."
                ),

                "City": (
                    "Invalid city",
                    "Enter a valid city name."
                )
            }


            if column in cleaning_messages:

                (
                    error,
                    fix
                ) = cleaning_messages[
                    column
                ]

            else:

                error = (
                    "Unresolved cleaning issue"
                )

                fix = (
                    "Review and correct the value."
                )


            add_problem_part(
                group,
                column,
                error,
                fix,
                "cleaning",
                reportable=True,
                reviewable=True
            )


    # ========================================================
    # 2. ORIGINAL EMAIL CLASSIFICATION
    # ========================================================

    if "Customer_Email" in original_df.columns:

        email = (
            original_df[
                "Customer_Email"
            ]
        )

        email_text = (
            email
            .astype("string")
            .str.strip()
        )


        # ----------------------------------------------------
        # GENUINE MISSING EMAILS
        # ----------------------------------------------------

        genuine_missing = (
            email.isna()
            |
            email_text.isin(
                MISSING_VALUES
            )
            .fillna(False)
        )


        eligible = (
            ~genuine_missing
        )


        # ----------------------------------------------------
        # EMAIL SYNTAX
        # ----------------------------------------------------

        syntax_valid = (
            email_text
            .str.fullmatch(
                EMAIL_PATTERN,
                na=False
            )
        )


        invalid_token = (
            email_text
            .str.upper()
            .eq(
                "INVALID"
            )
            .fillna(False)
        )


        invalid_syntax = (
            eligible
            &
            (
                invalid_token
                |
                ~syntax_valid
            )
        )


        invalid_email_frame = pd.DataFrame(
            {
                "index":
                    original_df.index[
                        invalid_syntax
                    ]
            }
        )


        add_problem_part(
            invalid_email_frame,
            "Customer_Email",
            "Invalid email syntax",
            "Enter a valid email address.",
            "email",
            reportable=True,
            reviewable=False
        )


        # ----------------------------------------------------
        # EMAIL DOMAIN
        # ----------------------------------------------------

        domain = (
            email_text
            .str.rsplit(
                "@",
                n=1
            )
            .str[-1]
            .str.lower()
        )


        incorrect_domain = (
            eligible
            &
            syntax_valid
            &
            (
                domain
                != EXPECTED_EMAIL_DOMAIN
            )
        )


        incorrect_domain = (
            incorrect_domain
            .fillna(False)
        )


        incorrect_domain_frame = pd.DataFrame(
            {
                "index":
                    original_df.index[
                        incorrect_domain
                    ]
            }
        )


        add_problem_part(
            incorrect_domain_frame,
            "Customer_Email",
            "Incorrect email domain",
            "Use the @example.com email domain.",
            "email",
            reportable=True,
            reviewable=False
        )


    # ========================================================
    # 3. PANDERA VALIDATION FAILURES
    # ========================================================

    if (
        failure_cases is not None
        and not failure_cases.empty
    ):

        failures = (
            failure_cases.copy()
        )


        # ====================================================
        # 3A. CUSTOMER EMAIL VALIDATION FAILURES
        # ====================================================

        email_validation_failures = (
            failures.loc[
                (
                    failures[
                        "column"
                    ] == "Customer_Email"
                )
                &
                (
                    failures[
                        "index"
                    ].notna()
                ),
                [
                    "index"
                ]
            ]
            .copy()
        )


        if not email_validation_failures.empty:

            add_problem_part(
                email_validation_failures,
                "Customer_Email",
                "Validation failed",
                "Review and correct the value.",
                "validation",
                reportable=False,
                reviewable=True
            )


        # ====================================================
        # 3B. NON-EMAIL PANDERA FAILURES
        # ====================================================

        failures = (
            failures[
                failures[
                    "column"
                ] != "Customer_Email"
            ]
        )


        for column in (
            failures[
                "column"
            ]
            .dropna()
            .unique()
        ):

            group = (
                failures[
                    failures[
                        "column"
                    ] == column
                ]
                .copy()
            )

            if group.empty:
                continue


            check_lower = (
                group[
                    "check"
                ]
                .astype(str)
                .str.lower()
            )


            errors = pd.Series(
                "Validation failed",
                index=group.index,
                dtype="object"
            )

            fixes = pd.Series(
                "Review and correct the value.",
                index=group.index,
                dtype="object"
            )


            # =================================================
            # STANDARD FIELDS
            # =================================================

            standard_messages = {

                "Order_ID": (
                    "Invalid order ID",
                    "Use the format ORD-12345."
                ),

                "Customer_Name": (
                    "Invalid customer name",
                    "Use alphabetic characters and spaces only."
                ),

                "Category": (
                    "Invalid category",
                    "Use one of the allowed product categories."
                ),

                "Product": (
                    "Invalid product",
                    "Use a valid product name."
                ),

                "City": (
                    "Invalid city",
                    "Enter a valid city name."
                ),

                "Payment_Method": (
                    "Invalid payment method",
                    "Use a valid payment method."
                ),

                "Order_Status": (
                    "Invalid order status",
                    "Use a valid order status."
                ),

                "Order_Date": (
                    "Invalid order date",
                    "Enter a valid date."
                )
            }


            if column in standard_messages:

                (
                    error,
                    fix
                ) = standard_messages[
                    column
                ]

                errors[:] = (
                    error
                )

                fixes[:] = (
                    fix
                )


            # =================================================
            # CUSTOMER AGE
            # =================================================

            elif column == "Customer_Age":

                greater = (
                    check_lower
                    .str.contains(
                        "greater_than",
                        regex=False
                    )
                )

                lesser = (
                    check_lower
                    .str.contains(
                        "less_than",
                        regex=False
                    )
                )


                errors[:] = (
                    "Invalid customer age"
                )

                fixes[:] = (
                    "Enter a numeric age between 0 and 120."
                )


                # ------------------------------------------------
                # IMPORTANT:
                #
                # Failed greater_than / greater_than_or_equal_to
                # means actual value is BELOW the minimum.
                # ------------------------------------------------

                errors.loc[
                    greater
                ] = (
                    "Age is below the allowed range"
                )


                # ------------------------------------------------
                # Failed less_than / less_than_or_equal_to
                # means actual value is ABOVE the maximum.
                # ------------------------------------------------

                errors.loc[
                    lesser
                ] = (
                    "Age is above the allowed range"
                )


                fixes.loc[
                    greater | lesser
                ] = (
                    "Set the age between 0 and 120."
                )


            # =================================================
            # CUSTOMER RATING
            # =================================================

            elif column == "Customer_Rating":

                greater = (
                    check_lower
                    .str.contains(
                        "greater_than",
                        regex=False
                    )
                )

                lesser = (
                    check_lower
                    .str.contains(
                        "less_than",
                        regex=False
                    )
                )


                errors[:] = (
                    "Invalid customer rating"
                )

                fixes[:] = (
                    "Enter a numeric rating between 1 and 5."
                )


                # Failed minimum check -> value is too low
                errors.loc[
                    greater
                ] = (
                    "Rating is below the allowed range"
                )


                # Failed maximum check -> value is too high
                errors.loc[
                    lesser
                ] = (
                    "Rating is above the allowed range"
                )


                fixes.loc[
                    greater | lesser
                ] = (
                    "Set the rating between 1 and 5."
                )


            # =================================================
            # NUMERIC COLUMNS
            # =================================================

            elif column in {
                "Quantity",
                "Unit_Price",
                "Discount",
                "Total_Amount"
            }:

                range_failure = (
                    check_lower
                    .str.contains(
                        "greater_than",
                        regex=False
                    )
                    |
                    check_lower
                    .str.contains(
                        "less_than",
                        regex=False
                    )
                )


                errors[:] = (
                    "Invalid "
                    f"{column.replace('_', ' ').lower()}"
                )

                fixes[:] = (
                    "Enter a valid numeric value."
                )


                # ---------------------------------------------
                # QUANTITY
                # ---------------------------------------------

                if column == "Quantity":

                    errors.loc[
                        range_failure
                    ] = (
                        "Quantity is below the allowed range"
                    )

                    fixes.loc[
                        range_failure
                    ] = (
                        "Set quantity to 0 or greater."
                    )


                # ---------------------------------------------
                # UNIT PRICE
                # ---------------------------------------------

                elif column == "Unit_Price":

                    errors.loc[
                        range_failure
                    ] = (
                        "Unit price is below the allowed range"
                    )

                    fixes.loc[
                        range_failure
                    ] = (
                        "Set unit price to 0 or greater."
                    )


                # ---------------------------------------------
                # TOTAL AMOUNT
                # ---------------------------------------------

                elif column == "Total_Amount":

                    errors.loc[
                        range_failure
                    ] = (
                        "Total amount is below the allowed range"
                    )

                    fixes.loc[
                        range_failure
                    ] = (
                        "Set total amount to 0 or greater."
                    )


                # ---------------------------------------------
                # DISCOUNT
                # ---------------------------------------------

                elif column == "Discount":

                    greater = (
                        check_lower
                        .str.contains(
                            "greater_than",
                            regex=False
                        )
                    )

                    lesser = (
                        check_lower
                        .str.contains(
                            "less_than",
                            regex=False
                        )
                    )


                    # Failed >= 0 check
                    # -> actual value is below 0
                    errors.loc[
                        greater
                    ] = (
                        "Discount is below the allowed range"
                    )


                    # Failed <= 100 check
                    # -> actual value is above 100
                    errors.loc[
                        lesser
                    ] = (
                        "Discount is above the allowed range"
                    )


                    fixes.loc[
                        greater | lesser
                    ] = (
                        "Set discount between 0 and 100."
                    )


            # =================================================
            # ADD VALIDATION PROBLEMS
            # =================================================

            add_problem_part(
                group,
                column,
                errors,
                fixes,
                "validation",
                reportable=True,
                reviewable=True
            )


    # ========================================================
    # 4. EMPTY RESULT
    # ========================================================

    if not problem_parts:

        return pd.DataFrame(
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


    # ========================================================
    # 5. COMBINE
    # ========================================================

    problem_map = (
        pd.concat(
            problem_parts,
            ignore_index=True
        )
    )


    # ========================================================
    # 6. KEEP ONLY VALID SOURCE INDEXES
    # ========================================================

    problem_map = (
        problem_map[
            problem_map[
                "index"
            ].isin(
                original_df.index
            )
        ]
        .reset_index(
            drop=True
        )
    )


    return problem_map

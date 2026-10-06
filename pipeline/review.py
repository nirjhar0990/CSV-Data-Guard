import pandas as pd

from .profiler import load_csv
from .cleaner import clean_data
from .validator import (
    validate_data,
    find_unresolved_cleaning_issues
)


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

REVIEW_MISSING_MARKER = "[MISSING]"

# ============================================================
# CREATE REVIEW DATASET
# ============================================================

def create_review_dataset(
    original_df,
    cleaned_df,
    problem_map
):
    """
    Create a sparse manual-review dataset from the shared
    problem map.

    Performance optimization:
        - Filter problem_map only once.
        - Group problem indexes by column once.
        - Align original/cleaned rows once for all review rows.
        - Avoid repeated full scans of problem_pairs.
        - Preserve the same sparse review semantics.

    Review-cell meaning:

        blank
            -> no correction required

        [MISSING]
            -> required value is missing

        actual populated value
            -> value requires manual correction
    """

    reviewable_columns = [
        column
        for column in original_df.columns
        if column != "Record_ID"
    ]

    if (
        problem_map is None
        or problem_map.empty
    ):

        return pd.DataFrame(
            columns=[
                "Record_ID",
                "Order_ID"
            ]
        )

    # --------------------------------------------------------
    # KEEP REVIEWABLE ROWS ONLY
    # --------------------------------------------------------

    if "reviewable" in problem_map.columns:

        reviewable_mask = (
            problem_map["reviewable"]
            .fillna(True)
            .to_numpy(dtype=bool)
        )

        problem_pairs = (
            problem_map.loc[
                reviewable_mask,
                [
                    "index",
                    "column"
                ]
            ]
        )

    else:

        problem_pairs = (
            problem_map.loc[
                :,
                [
                    "index",
                    "column"
                ]
            ]
        )

    # --------------------------------------------------------
    # BUSINESS COLUMNS + VALID SOURCE INDEXES
    # --------------------------------------------------------

    problem_pairs = (
        problem_pairs.loc[
            problem_pairs["column"].isin(
                reviewable_columns
            )
            &
            problem_pairs["index"].isin(
                original_df.index
            )
        ]
        .drop_duplicates(
            subset=[
                "index",
                "column"
            ]
        )
    )

    # Order_ID is normally an identifier column. It becomes
    # reviewable only when the current cleaned value is actually
    # invalid or duplicated.
    if (
        not problem_pairs.empty
        and
        "Order_ID" in cleaned_df.columns
    ):

        order_id_text = (
            cleaned_df["Order_ID"]
            .astype("string")
            .str.strip()
        )

        invalid_order_id_mask = (
            ~order_id_text.str.fullmatch(
                r"ORD-\d{5}",
                na=False
            )
        )

        duplicate_order_id_mask = (
            cleaned_df["Order_ID"]
            .duplicated(
                keep=False
            )
        )

        reviewable_order_id_indexes = set(
            cleaned_df.index[
                invalid_order_id_mask
                |
                duplicate_order_id_mask
            ]
        )

        order_id_pair_mask = (
            problem_pairs["column"]
            .eq("Order_ID")
        )

        keep_problem_mask = (
            ~order_id_pair_mask
            |
            problem_pairs["index"].isin(
                reviewable_order_id_indexes
            )
        )

        problem_pairs = (
            problem_pairs.loc[
                keep_problem_mask
            ]
        )

    if problem_pairs.empty:

        return pd.DataFrame(
            columns=[
                "Record_ID",
                "Order_ID"
            ]
        )

    # --------------------------------------------------------
    # REVIEW ROWS
    # --------------------------------------------------------

    problem_indexes = (
        problem_pairs["index"]
        .drop_duplicates()
        .sort_values()
    )

    problem_index_list = (
        problem_indexes.tolist()
    )

    # --------------------------------------------------------
    # GROUP PROBLEM INDEXES ONCE BY COLUMN
    # --------------------------------------------------------

    grouped_problem_indexes = {
        column: pd.Index(indexes)
        for column, indexes in (
            problem_pairs
            .groupby(
                "column",
                sort=False
            )["index"]
            .unique()
            .items()
        )
    }

    review_problem_columns = [
        column
        for column in reviewable_columns
        if column in grouped_problem_indexes
    ]

    review_columns = [
        "Record_ID",
        "Order_ID",
        *[
            column
            for column in review_problem_columns
            if column != "Order_ID"
        ]
    ]

    # --------------------------------------------------------
    # ALIGN SOURCE DATA ONCE
    # --------------------------------------------------------

    original_review_rows = (
        original_df.loc[
            problem_index_list,
            review_columns
        ]
    )

    cleaned_review_rows = (
        cleaned_df.reindex(
            problem_index_list
        )
    )

    # --------------------------------------------------------
    # CREATE SPARSE REVIEW FRAME
    # --------------------------------------------------------

    review_df = pd.DataFrame(
        "",
        index=problem_index_list,
        columns=review_columns,
        dtype="object"
    )

    review_df["Record_ID"] = (
        original_review_rows[
            "Record_ID"
        ]
        .to_numpy()
    )

    review_df["Order_ID"] = (
        original_review_rows[
            "Order_ID"
        ]
        .to_numpy()
    )

    # --------------------------------------------------------
    # POPULATE ONLY PROBLEM CELLS
    # --------------------------------------------------------

    for column in review_problem_columns:

        column_indexes = (
            grouped_problem_indexes[
                column
            ]
        )

        original_values = (
            original_review_rows.loc[
                column_indexes,
                column
            ]
        )

        cleaned_values = (
            cleaned_review_rows.loc[
                column_indexes,
                column
            ]
        )

        original_text = (
            original_values
            .astype("string")
            .str.strip()
        )

        original_is_missing = (
            original_values.isna()
            |
            original_text.isin(
                MISSING_VALUES
            )
        )

        cleaned_is_missing = (
            cleaned_values.isna()
        )

        review_values = pd.Series(
            REVIEW_MISSING_MARKER,
            index=column_indexes,
            dtype="object"
        )

        # Current cleaned value still exists but is invalid.
        cleaned_present_mask = (
            ~cleaned_is_missing
        )

        if cleaned_present_mask.any():

            review_values.loc[
                cleaned_present_mask
            ] = (
                cleaned_values.loc[
                    cleaned_present_mask
                ]
            )

        # Original bad value was converted to missing.
        bad_original_mask = (
            ~original_is_missing
            &
            cleaned_is_missing
        )

        if bad_original_mask.any():

            review_values.loc[
                bad_original_mask
            ] = (
                original_values.loc[
                    bad_original_mask
                ]
            )

        review_df.loc[
            column_indexes,
            column
        ] = (
            review_values.to_numpy()
        )

    return (
        review_df[
            review_columns
        ]
        .reset_index(
            drop=True
        )
    )


# ============================================================
# MERGE REVIEW CORRECTIONS
# ============================================================

def merge_review_corrections(
    cleaned_df,
    original_review_df,
    corrected_review_df
):
    """
    Merge manually corrected review values back into the
    current cleaned dataset.

    Important rules:

    1. Record_ID is the technical key.

    2. Only cells that were originally marked as review
       problems can be changed.

    3. Blank review cells are ignored.

    4. [MISSING] identifies a genuinely missing value that
       requires correction.

    5. Leaving [MISSING] unchanged means no correction.

    6. Empty corrected cells are treated as no correction.

    7. The original dataframe index is preserved.
    """

    required_columns = {
        "Record_ID",
        "Order_ID"
    }


    # ========================================================
    # 1. VALIDATE REQUIRED COLUMNS
    # ========================================================

    for dataframe_name, dataframe in [

        (
            "Original review dataset",
            original_review_df
        ),

        (
            "Corrected review dataset",
            corrected_review_df
        )

    ]:

        missing_columns = (
            required_columns
            - set(
                dataframe.columns
            )
        )

        if missing_columns:

            raise ValueError(
                f"{dataframe_name} is missing: "
                f"{sorted(missing_columns)}"
            )


    if "Record_ID" not in cleaned_df.columns:

        raise ValueError(
            "Cleaned dataset must contain Record_ID."
        )


    # ========================================================
    # 2. CHECK DUPLICATE RECORD_ID
    # ========================================================

    if (
        corrected_review_df[
            "Record_ID"
        ]
        .duplicated()
        .any()
    ):

        raise ValueError(
            "Corrected review dataset contains "
            "duplicate Record_ID values."
        )


    # ========================================================
    # 3. FIND REVIEW COLUMNS
    # ========================================================

    # Determine current Order_ID problem rows before deciding
    # whether Order_ID is an editable correction column.
    order_id_problem_record_ids = set()

    if (
        "Order_ID" in cleaned_df.columns
        and
        "Record_ID" in cleaned_df.columns
    ):

        order_id_text = (
            cleaned_df["Order_ID"]
            .astype("string")
            .str.strip()
        )

        invalid_order_id_mask = (
            ~order_id_text.str.fullmatch(
                r"ORD-\d{5}",
                na=False
            )
        )

        duplicate_order_id_mask = (
            cleaned_df["Order_ID"]
            .duplicated(
                keep=False
            )
        )

        order_id_problem_record_ids = set(
            cleaned_df.loc[
                invalid_order_id_mask
                |
                duplicate_order_id_mask,
                "Record_ID"
            ]
        )


    correction_columns = [
        column
        for column
        in corrected_review_df.columns
        if column not in {
            "Record_ID",
            "Order_ID"
        }
    ]


    if (
        "Order_ID" in corrected_review_df.columns
        and
        corrected_review_df[
            "Record_ID"
        ]
        .isin(
            order_id_problem_record_ids
        )
        .any()
    ):

        correction_columns.append(
            "Order_ID"
        )


    if not correction_columns:

        raise ValueError(
            "No correction columns found."
        )


    # ========================================================
    # 4. VALIDATE COLUMN NAMES
    # ========================================================

    invalid_columns = [
        column
        for column
        in correction_columns
        if column not in cleaned_df.columns
    ]


    if invalid_columns:

        raise ValueError(
            f"Unknown columns: "
            f"{invalid_columns}"
        )


    # ========================================================
    # 5. INDEX REVIEW DATASETS BY RECORD_ID
    # ========================================================

    original_review = (
        original_review_df
        .set_index(
            "Record_ID"
        )
    )

    corrected_review = (
        corrected_review_df
        .set_index(
            "Record_ID"
        )
    )


    # ========================================================
    # 6. PRESERVE CURRENT DATAFRAME INDEX
    # ========================================================

    corrected_df = (
        cleaned_df.copy()
    )

    corrected_df[
        "_Original_Index"
    ] = corrected_df.index

    corrected_df = (
        corrected_df
        .set_index(
            "Record_ID"
        )
    )


    # ========================================================
    # 7. TRACK CORRECTIONS
    # ========================================================

    corrections_applied = 0

    changed_columns = set()

    changed_record_ids = set()


    # ========================================================
    # 8. COMPARE REVIEW VALUES
    # ========================================================

    for record_id in (
        corrected_review.index
    ):


        # ----------------------------------------------------
        # RECORD MUST EXIST IN BOTH FILES AND DATASET
        # ----------------------------------------------------

        if record_id not in original_review.index:
            continue

        if record_id not in corrected_df.index:
            continue


        for column in (
            correction_columns
        ):


            # ------------------------------------------------
            # Order_ID IS EDITABLE ONLY WHEN IT IS ITSELF
            # AN INVALID OR DUPLICATE VALUE.
            #
            # Record_ID remains the immutable technical key.
            # ------------------------------------------------

            if (
                column == "Order_ID"
                and
                record_id
                not in order_id_problem_record_ids
            ):

                continue


            # ------------------------------------------------
            # COLUMN MUST EXIST IN ORIGINAL REVIEW FILE
            # ------------------------------------------------

            if column not in original_review.columns:
                continue


            original_review_value = (
                original_review.loc[
                    record_id,
                    column
                ]
            )

            corrected_value = (
                corrected_review.loc[
                    record_id,
                    column
                ]
            )


            # =================================================
            # 9. DETERMINE WHETHER THIS CELL WAS ACTUALLY
            #    MARKED FOR REVIEW
            # =================================================

            original_review_blank = (
                pd.isna(
                    original_review_value
                )
                or
                str(
                    original_review_value
                ).strip()
                == ""
            )


            # ------------------------------------------------
            # BLANK ORIGINAL REVIEW CELL MEANS:
            #
            # This field did NOT require correction.
            #
            # Ignore it even if Excel/user accidentally changes
            # the blank cell.
            # ------------------------------------------------

            if original_review_blank:
                continue


            # =================================================
            # 10. NORMALIZE CORRECTED VALUE
            # =================================================

            corrected_is_blank = (
                pd.isna(
                    corrected_value
                )
                or
                str(
                    corrected_value
                ).strip()
                == ""
            )


            # ------------------------------------------------
            # User left correction blank.
            #
            # Treat as no correction instead of destroying the
            # current cleaned value.
            # ------------------------------------------------

            if corrected_is_blank:
                continue


            original_text = (
                str(
                    original_review_value
                ).strip()
            )

            corrected_text = (
                str(
                    corrected_value
                ).strip()
            )


            # ------------------------------------------------
            # [MISSING] was not corrected
            # ------------------------------------------------

            if (
                original_text
                == REVIEW_MISSING_MARKER
                and
                corrected_text
                == REVIEW_MISSING_MARKER
            ):

                continue


            # ------------------------------------------------
            # Reserved marker cannot itself be a correction.
            # ------------------------------------------------

            if (
                corrected_text
                == REVIEW_MISSING_MARKER
            ):

                continue


            # ------------------------------------------------
            # VALUE WAS NOT CHANGED
            # ------------------------------------------------

            if (
                original_text
                == corrected_text
            ):

                continue


            # =================================================
            # 11. CONVERT TO TARGET DATA TYPE
            # =================================================

            target_dtype = (
                corrected_df[
                    column
                ].dtype
            )


            # ------------------------------------------------
            # INTEGER
            # ------------------------------------------------

            if pd.api.types.is_integer_dtype(
                target_dtype
            ):

                converted_value = (
                    pd.to_numeric(
                        corrected_value,
                        errors="coerce"
                    )
                )

                if pd.isna(
                    converted_value
                ):

                    # Invalid manual correction.
                    # Leave original cleaned value untouched.
                    continue

                converted_value = int(
                    converted_value
                )


            # ------------------------------------------------
            # FLOAT
            # ------------------------------------------------

            elif pd.api.types.is_float_dtype(
                target_dtype
            ):

                converted_value = (
                    pd.to_numeric(
                        corrected_value,
                        errors="coerce"
                    )
                )

                if pd.isna(
                    converted_value
                ):

                    continue


            # ------------------------------------------------
            # DATETIME
            # ------------------------------------------------

            elif (
                pd.api.types
                .is_datetime64_any_dtype(
                    target_dtype
                )
            ):

                converted_value = (
                    pd.to_datetime(
                        corrected_value,
                        errors="coerce"
                    )
                )

                if pd.isna(
                    converted_value
                ):

                    continue


            # ------------------------------------------------
            # STRING / OTHER
            # ------------------------------------------------

            else:

                converted_value = (
                    str(
                        corrected_value
                    ).strip()
                )


            # =================================================
            # 12. APPLY CORRECTION
            # =================================================

            corrected_df.loc[
                record_id,
                column
            ] = converted_value


            corrections_applied += 1

            changed_columns.add(
                column
            )

            changed_record_ids.add(
                record_id
            )


    # ========================================================
    # 13. RESTORE Record_ID COLUMN
    # ========================================================

    corrected_df = (
        corrected_df
        .reset_index()
    )


    # ========================================================
    # 14. RESTORE ORIGINAL DATAFRAME INDEX
    # ========================================================

    corrected_df = (
        corrected_df
        .set_index(
            "_Original_Index"
        )
    )

    corrected_df.index.name = None


    # ========================================================
    # 15. SUMMARY
    # ========================================================

    summary = {

        "corrections_received":
            len(
                corrected_review_df
            ),

        "records_changed":
            len(
                changed_record_ids
            ),

        "corrections_applied":
            corrections_applied,

        "correction_columns":
            sorted(
                changed_columns
            )
    }


    return (
        corrected_df,
        summary
    )


# ============================================================
# ANALYZE ISSUE FREQUENCY
# ============================================================

def analyze_issue_frequency(
    unresolved_issues,
    failure_cases
):
    """
    Analyze recurring unresolved cleaning issues
    and validation failures.

    Returns:

        unresolved_summary
        validation_summary
        value_summary
    """

    # ========================================================
    # 1. UNRESOLVED CLEANING ISSUE FREQUENCY
    # ========================================================

    if (
        unresolved_issues is None
        or unresolved_issues.empty
    ):

        unresolved_summary = pd.DataFrame(
            columns=[
                "Column",
                "Issue Type",
                "Count"
            ]
        )

        value_summary = pd.DataFrame(
            columns=[
                "Column",
                "Problem Value",
                "Count"
            ]
        )

    else:

        unresolved_summary = (
            unresolved_issues
            .groupby(
                [
                    "column",
                    "issue_type"
                ]
            )
            .size()
            .reset_index(
                name="Count"
            )
            .rename(
                columns={
                    "column":
                        "Column",

                    "issue_type":
                        "Issue Type"
                }
            )
            .sort_values(
                "Count",
                ascending=False
            )
            .reset_index(
                drop=True
            )
        )

        # ----------------------------------------------------
        # RECURRING ORIGINAL VALUES
        # ----------------------------------------------------

        value_data = (
            unresolved_issues[
                [
                    "column",
                    "original_value"
                ]
            ]
            .copy()
        )

        value_data[
            "original_value"
        ] = (
            value_data[
                "original_value"
            ]
            .astype(str)
            .str.strip()
        )

        value_summary = (
            value_data
            .groupby(
                [
                    "column",
                    "original_value"
                ]
            )
            .size()
            .reset_index(
                name="Count"
            )
            .rename(
                columns={
                    "column":
                        "Column",

                    "original_value":
                        "Problem Value"
                }
            )
            .sort_values(
                "Count",
                ascending=False
            )
            .reset_index(
                drop=True
            )
        )

    # ========================================================
    # 2. VALIDATION FAILURE FREQUENCY
    # ========================================================

    if (
        failure_cases is None
        or failure_cases.empty
    ):

        validation_summary = pd.DataFrame(
            columns=[
                "Column",
                "Validation Rule",
                "Count"
            ]
        )

    else:

        validation_data = (
            failure_cases[
                [
                    "column",
                    "check"
                ]
            ]
            .copy()
        )

        validation_data[
            "check"
        ] = (
            validation_data[
                "check"
            ]
            .astype(str)
        )

        validation_summary = (
            validation_data
            .groupby(
                [
                    "column",
                    "check"
                ]
            )
            .size()
            .reset_index(
                name="Count"
            )
            .rename(
                columns={
                    "column":
                        "Column",

                    "check":
                        "Validation Rule"
                }
            )
            .sort_values(
                "Count",
                ascending=False
            )
            .reset_index(
                drop=True
            )
        )

    return (
        unresolved_summary,
        validation_summary,
        value_summary
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "\n===== REVIEW CORRECTION TEST ====="
    )

    # --------------------------------------------------------
    # 1. LOAD ORIGINAL DATA
    # --------------------------------------------------------

    original_df = load_csv(
        "data/messy_retail_data_10K.csv"
    )

    # --------------------------------------------------------
    # 2. ADD INTERNAL RECORD_ID
    # --------------------------------------------------------

    original_df.insert(
        0,
        "Record_ID",
        range(
            1,
            len(original_df) + 1
        )
    )

    # --------------------------------------------------------
    # 3. CLEAN DATA
    # --------------------------------------------------------

    cleaned_df, _ = clean_data(
        original_df
    )

    print(
        "Original rows:",
        len(original_df)
    )

    print(
        "Cleaned rows:",
        len(cleaned_df)
    )

    # --------------------------------------------------------
    # 4. LOAD REVIEW FILES
    # --------------------------------------------------------

    original_review_df = load_csv(
        "data/review_dataset.csv"
    )

    corrected_review_df = load_csv(
        "data/review_dataset_corrected.csv"
    )

    print(
        "\nCorrected review rows:",
        len(
            corrected_review_df
        )
    )

    # --------------------------------------------------------
    # 5. MERGE CORRECTIONS
    # --------------------------------------------------------

    corrected_df, summary = (
        merge_review_corrections(
            cleaned_df,
            original_review_df,
            corrected_review_df
        )
    )

    print(
        "\n===== MERGE SUMMARY ====="
    )

    print(
        "Corrections Received:",
        summary[
            "corrections_received"
        ]
    )

    print(
        "Corrections Applied:",
        summary[
            "corrections_applied"
        ]
    )

    print(
        "Correction Columns:",
        summary[
            "correction_columns"
        ]
    )

    # --------------------------------------------------------
    # 6. CLEANING RE-EVALUATION
    # --------------------------------------------------------

    before_correction_issues = (
        find_unresolved_cleaning_issues(
            original_df,
            cleaned_df
        )
    )

    after_correction_issues = (
        find_unresolved_cleaning_issues(
            original_df,
            corrected_df
        )
    )

    print(
        "\n===== CLEANING RE-EVALUATION ====="
    )

    print(
        "Unresolved Issues Before:",
        len(
            before_correction_issues
        )
    )

    print(
        "Unresolved Issues After:",
        len(
            after_correction_issues
        )
    )

    # --------------------------------------------------------
    # 7. CHECK CORRECTED RECORD
    # --------------------------------------------------------

    print(
        "\n===== CORRECTED RECORD ====="
    )

    corrected_record = (
        corrected_df[
            corrected_df[
                "Record_ID"
            ] == 2
        ]
    )

    print(
        corrected_record[
            [
                "Record_ID",
                "Order_ID",
                "Customer_Age"
            ]
        ].to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 8. VALIDATE CORRECTED DATA
    # --------------------------------------------------------

    validation_result = (
        validate_data(
            corrected_df
        )
    )

    print(
        "\n===== RE-VALIDATION ====="
    )

    print(
        "Validation Success:",
        validation_result[
            "success"
        ]
    )

    failure_cases = (
        validation_result[
            "failure_cases"
        ]
    )

    if (
        failure_cases is not None
        and not failure_cases.empty
    ):

        print(
            "Remaining Failure Cases:",
            len(
                failure_cases
            )
        )

    else:

        print(
            "Remaining Failure Cases:",
            0
        )

    # --------------------------------------------------------
    # 9. ANALYZE REMAINING ISSUE FREQUENCY
    # --------------------------------------------------------

    (
        unresolved_summary,
        validation_summary,
        value_summary
    ) = analyze_issue_frequency(
        after_correction_issues,
        failure_cases
    )

    print(
        "\n===== UNRESOLVED ISSUE FREQUENCY ====="
    )

    print(
        unresolved_summary.to_string(
            index=False
        )
    )

    print(
        "\n===== VALIDATION FAILURE FREQUENCY ====="
    )

    print(
        validation_summary.to_string(
            index=False
        )
    )

    print(
        "\n===== TOP RECURRING PROBLEM VALUES ====="
    )

    print(
        value_summary.head(
            30
        ).to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 10. CREATE NEW REVIEW DATASET
    # --------------------------------------------------------

    new_review_df = (
        create_review_dataset(
            original_df,
            corrected_df,
            failure_cases
        )
    )

    print(
        "\n===== NEW REVIEW DATASET ====="
    )

    print(
        "Review Records:",
        len(
            new_review_df
        )
    )

    print(
        "Review Columns:",
        new_review_df.columns.tolist()
    )

    # --------------------------------------------------------
    # 11. VERIFY CORRECTED RECORD IS GONE
    # --------------------------------------------------------

    record_2_review = (
        new_review_df[
            new_review_df[
                "Record_ID"
            ] == 2
        ]
    )

    print(
        "\nRecord_ID 2 still requires review:",
        not record_2_review.empty
    )

    # --------------------------------------------------------
    # 12. SAVE NEW REVIEW DATASET
    # --------------------------------------------------------

    new_review_df.to_csv(
        "data/review_dataset_round2.csv",
        index=False
    )

    print(
        "\nNew review dataset saved to:",
        "data/review_dataset_round2.csv"
    )

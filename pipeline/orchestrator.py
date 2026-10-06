import time

import pandas as pd

from .profiler import (
    load_csv,
    profile_data
)

from .cleaner import (
    clean_data
)

from .validator import (
    validate_data,
    calculate_validation_score,
    calculate_cleaning_score,
    find_unresolved_cleaning_issues
)

from .reporting import (
    create_validation_report
)

from .review import (
    create_review_dataset,
    merge_review_corrections
)

from .problem_map import (
    create_problem_map
)


# ============================================================
# PIPELINE PERFORMANCE PROFILING
# ============================================================

def _perf_log(stage_name, start_time):
    """Print pipeline-stage timing to the terminal."""

    elapsed = time.perf_counter() - start_time

    print(
        f"[PIPELINE PERFORMANCE] {stage_name:<35} {elapsed:.4f} sec",
        flush=True
    )

    return elapsed


# ============================================================
# DATA QUALITY CHECK
# ============================================================

def perform_data_quality_check(
    cleaning_score,
    validation_score,
    validation_success
):
    """
    Determine whether the dataset is ready for export.

    Export is allowed only when:

        Cleaning Score   = 100%
        Validation Score = 100%
        Validation       = Successful
    """

    cleaning_complete = (
        cleaning_score == 100.0
    )

    validation_complete = (
        validation_score == 100.0
        and validation_success
    )

    export_allowed = (
        cleaning_complete
        and validation_complete
    )

    # --------------------------------------------------------
    # DETERMINE STATUS
    # --------------------------------------------------------

    if export_allowed:

        export_status = "READY"

        export_reason = (
            "Cleaning and validation are complete. "
            "Dataset is ready for export."
        )

    elif not cleaning_complete:

        export_status = "BLOCKED"

        export_reason = (
            "Cleaning issues still require remediation."
        )

    else:

        export_status = "BLOCKED"

        export_reason = (
            "Validation issues still require remediation."
        )

    return {

        "cleaning_complete":
            cleaning_complete,

        "validation_complete":
            validation_complete,

        "export_allowed":
            export_allowed,

        "export_status":
            export_status,

        "export_reason":
            export_reason
    }


# ============================================================
# VALID / INVALID ROW COUNTS
# ============================================================

def get_validation_row_counts(
    df,
    failure_cases
):
    """
    Count valid and invalid rows.

    A row is counted as invalid only once even if it
    fails multiple validation rules.
    """

    total_rows = len(df)

    # --------------------------------------------------------
    # NO DATA
    # --------------------------------------------------------

    if total_rows == 0:

        return (
            0,
            0
        )

    # --------------------------------------------------------
    # NO FAILURES
    # --------------------------------------------------------

    if (
        failure_cases is None
        or failure_cases.empty
    ):

        return (
            total_rows,
            0
        )

    # --------------------------------------------------------
    # UNIQUE INVALID ROWS
    # --------------------------------------------------------

    invalid_rows = (
        failure_cases[
            "index"
        ]
        .dropna()
        .nunique()
    )

    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------

    invalid_rows = min(
        invalid_rows,
        total_rows
    )

    valid_rows = (
        total_rows
        - invalid_rows
    )

    return (
        valid_rows,
        invalid_rows
    )


# ============================================================
# VALIDATION FAILURES BY COLUMN
# ============================================================

def get_validation_failures_by_column(
    failure_cases
):
    """
    Count unique failed rows for each validation column.

    Useful for Streamlit charts and reporting.
    """

    if (
        failure_cases is None
        or failure_cases.empty
    ):

        return pd.Series(
            dtype="int64"
        )

    # --------------------------------------------------------
    # KEEP ONLY ROW-LEVEL FAILURES
    # --------------------------------------------------------

    row_failures = (
        failure_cases[
            failure_cases[
                "index"
            ].notna()
        ]
    )

    if row_failures.empty:

        return pd.Series(
            dtype="int64"
        )

    # --------------------------------------------------------
    # COUNT UNIQUE FAILED ROWS PER COLUMN
    # --------------------------------------------------------

    validation_failures = (
        row_failures
        .groupby(
            "column"
        )[
            "index"
        ]
        .nunique()
        .sort_values(
            ascending=False
        )
    )

    return validation_failures


# ============================================================
# CREATE EMPTY REVIEW DATASET
# ============================================================

def create_empty_review_dataset():
    """
    Return the standard empty review dataframe.

    Used when no manual review is required.
    """

    return pd.DataFrame(
        columns=[
            "Record_ID",
            "Order_ID"
        ]
    )


# ============================================================
# INITIAL PIPELINE
# ============================================================

def run_pipeline(
    file_path
):
    """
    Run the complete pipeline from a CSV file path.

    This public entry point is preserved for backend tests,
    command-line use, and non-Streamlit callers.
    """

    pipeline_total_start = time.perf_counter()

    stage_start = time.perf_counter()

    raw_df = load_csv(
        file_path
    )

    _perf_log(
        "Load CSV",
        stage_start
    )

    stage_start = time.perf_counter()

    profile = profile_data(
        raw_df
    )

    _perf_log(
        "Profile raw data",
        stage_start
    )

    return _run_pipeline_core(
        raw_df=raw_df,
        profile=profile,
        pipeline_total_start=pipeline_total_start,
        total_label="TOTAL INITIAL PIPELINE"
    )


def run_pipeline_from_dataframe(
    raw_df,
    profile=None
):
    """
    Run the same pipeline from an already-loaded DataFrame.

    Streamlit uses this path to avoid:
      - writing the uploaded DataFrame to a temporary CSV,
      - loading that CSV again, and
      - profiling the same dataset a second time.

    If an existing profile is supplied, it is reused.
    """

    pipeline_total_start = time.perf_counter()

    if profile is None:

        stage_start = time.perf_counter()

        profile = profile_data(
            raw_df
        )

        _perf_log(
            "Profile raw data",
            stage_start
        )

    return _run_pipeline_core(
        raw_df=raw_df,
        profile=profile,
        pipeline_total_start=pipeline_total_start,
        total_label="TOTAL DATAFRAME PIPELINE"
    )


def _run_pipeline_core(
    raw_df,
    profile,
    pipeline_total_start,
    total_label
):
    """Shared implementation used by both pipeline entry points."""

    # ========================================================
    # 3. PRESERVE ORIGINAL DATA
    # ========================================================

    stage_start = time.perf_counter()

    original_df = (
        raw_df.copy()
    )

    # ========================================================
    # 4. ADD INTERNAL RECORD_ID
    # ========================================================

    original_df.insert(
        0,
        "Record_ID",
        range(
            1,
            len(original_df) + 1
        )
    )

    _perf_log(
        "Prepare original data",
        stage_start
    )

    # ========================================================
    # 5. CLEAN DATA
    # ========================================================

    stage_start = time.perf_counter()

    (
        cleaned_df,
        cleaning_checks
    ) = clean_data(
        original_df
    )

    _perf_log(
        "Clean data",
        stage_start
    )

    # ========================================================
    # 6. FIND UNRESOLVED CLEANING ISSUES
    # ========================================================

    stage_start = time.perf_counter()

    unresolved_issues = (
        find_unresolved_cleaning_issues(
            original_df,
            cleaned_df
        )
    )

    _perf_log(
        "Find unresolved cleaning issues",
        stage_start
    )

    initial_unresolved_count = (
        len(
            unresolved_issues
        )
    )

    # ========================================================
    # 7. CLEANING SCORE
    #
    # At the initial stage all remaining unresolved
    # issues are still outstanding.
    # ========================================================

    stage_start = time.perf_counter()

    cleaning_score = (
        calculate_cleaning_score(
            initial_unresolved_count,
            initial_unresolved_count
        )
    )

    _perf_log(
        "Calculate cleaning score",
        stage_start
    )

    # ========================================================
    # 8. VALIDATE CLEANED DATA
    # ========================================================

    stage_start = time.perf_counter()

    validation_result = (
        validate_data(
            cleaned_df
        )
    )

    _perf_log(
        "Validate cleaned data",
        stage_start
    )

    failure_cases = (
        validation_result[
            "failure_cases"
        ]
    )

    validation_success = (
        validation_result[
            "success"
        ]
    )

    # ========================================================
    # SHARED PROBLEM MAP
    # ========================================================

    stage_start = time.perf_counter()

    problem_map_df = (
        create_problem_map(
            original_df,
            failure_cases,
            unresolved_issues
        )
    )

    _perf_log(
        "Create problem map",
        stage_start
    )

    # ========================================================
    # 9. ROW-BASED VALIDATION SCORE
    # ========================================================

    stage_start = time.perf_counter()

    validation_score = (
        calculate_validation_score(
            cleaned_df,
            failure_cases
        )
    )

    _perf_log(
        "Calculate validation score",
        stage_start
    )

    # ========================================================
    # 10. VALID / INVALID ROW COUNTS
    # ========================================================

    stage_start = time.perf_counter()

    (
        valid_rows,
        invalid_rows
    ) = get_validation_row_counts(
        cleaned_df,
        failure_cases
    )

    _perf_log(
        "Count valid/invalid rows",
        stage_start
    )

    # ========================================================
    # 11. VALIDATION FAILURES BY COLUMN
    # ========================================================

    stage_start = time.perf_counter()

    validation_failures_by_column = (
        get_validation_failures_by_column(
            failure_cases
        )
    )

    _perf_log(
        "Summarize validation failures",
        stage_start
    )

    # ========================================================
    # 12. DATA QUALITY CHECK
    # ========================================================

    stage_start = time.perf_counter()

    quality_status = (
        perform_data_quality_check(
            cleaning_score,
            validation_score,
            validation_success
        )
    )

    _perf_log(
        "Quality gate",
        stage_start
    )

    # ========================================================
    # 13. CREATE DATA QUALITY REPORT
    # ========================================================

    stage_start = time.perf_counter()

    report = (
        create_validation_report(
            problem_map_df,
            original_df
        )
    )

    _perf_log(
        "Create validation report",
        stage_start
    )

    # ========================================================
    # 14. CREATE REVIEW DATASET
    # ========================================================

    stage_start = time.perf_counter()

    if quality_status[
        "export_allowed"
    ]:

        review_df = (
            create_empty_review_dataset()
        )

    else:

        review_df = (
            create_review_dataset(
                original_df,
                cleaned_df,
                problem_map_df
            )
        )

    _perf_log(
        "Create review dataset",
        stage_start
    )

    # ========================================================
    # 15. PROFILE ISSUE SUMMARY
    # ========================================================

    if isinstance(
        profile,
        dict
    ):

        issue_summary = (
            profile.get(
                "issue_summary"
            )
        )

    else:

        issue_summary = None

    # ========================================================
    # 16. PIPELINE SUMMARY
    # ========================================================

    summary = {

        "original_rows":
            len(
                original_df
            ),

        "cleaned_rows":
            len(
                cleaned_df
            ),

        "initial_unresolved_cleaning_issues":
            initial_unresolved_count,

        "remaining_unresolved_cleaning_issues":
            len(
                unresolved_issues
            ),

        "cleaning_score":
            cleaning_score,

        "validation_score":
            validation_score,

        "validation_success":
            validation_success,

        "valid_rows":
            valid_rows,

        "invalid_rows":
            invalid_rows,

        "review_records":
            len(
                review_df
            ),

        "export_allowed":
            quality_status[
                "export_allowed"
            ],

        "export_status":
            quality_status[
                "export_status"
            ],

        "export_reason":
            quality_status[
                "export_reason"
            ]
    }

    # ========================================================
    # 17. RETURN COMPLETE PIPELINE RESULT
    # ========================================================

    _perf_log(
        total_label,
        pipeline_total_start
    )

    return {

        # ----------------------------------------------------
        # SOURCE DATA
        # ----------------------------------------------------

        "original_data":
            original_df,


        # ----------------------------------------------------
        # PROFILING
        # ----------------------------------------------------

        "profile":
            profile,

        "issue_summary":
            issue_summary,


        # ----------------------------------------------------
        # CLEANING
        # ----------------------------------------------------

        "cleaned_data":
            cleaned_df,

        "cleaning_checks":
            cleaning_checks,

        "initial_unresolved_cleaning_issue_count":
            initial_unresolved_count,

        "unresolved_cleaning_issues":
            unresolved_issues,

        "cleaning_score":
            cleaning_score,


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        "validation":
            validation_result,

        "validation_score":
            validation_score,

        "valid_rows":
            valid_rows,

        "invalid_rows":
            invalid_rows,

        "validation_failures_by_column":
            validation_failures_by_column,


        # ----------------------------------------------------
        # SHARED PROBLEM MAP
        # ----------------------------------------------------

        "problem_map":
            problem_map_df,


        # ----------------------------------------------------
        # REPORTING
        # ----------------------------------------------------

        "report":
            report,


        # ----------------------------------------------------
        # REVIEW
        # ----------------------------------------------------

        "review_data":
            review_df,

        "review_records":
            len(
                review_df
            ),


        # ----------------------------------------------------
        # QUALITY GATE
        # ----------------------------------------------------

        "cleaning_complete":
            quality_status[
                "cleaning_complete"
            ],

        "validation_complete":
            quality_status[
                "validation_complete"
            ],

        "export_allowed":
            quality_status[
                "export_allowed"
            ],

        "export_status":
            quality_status[
                "export_status"
            ],

        "export_reason":
            quality_status[
                "export_reason"
            ],


        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        "summary":
            summary
    }


# ============================================================
# APPLY MANUAL REVIEW CORRECTIONS
# ============================================================

def apply_review_corrections(
    pipeline_result,
    corrected_review_df
):
    correction_total_start = time.perf_counter()

    """
    Apply one manual correction round.

    Supports unlimited review rounds.

    Round 1:
        cleaned_data
            ↓
        corrected_data

    Round 2:
        corrected_data
            ↓
        corrected_data

    Round 3:
        corrected_data
            ↓
        corrected_data

    etc.
    """

    # ========================================================
    # 1. ORIGINAL SOURCE DATA
    # ========================================================

    original_df = (
        pipeline_result[
            "original_data"
        ]
    )

    # ========================================================
    # 2. DETERMINE CURRENT WORKING DATASET
    #
    # First correction round:
    #     cleaned_data
    #
    # Later correction rounds:
    #     corrected_data
    # ========================================================

    if (
        "corrected_data"
        in pipeline_result
    ):

        working_df = (
            pipeline_result[
                "corrected_data"
            ]
        )

    else:

        working_df = (
            pipeline_result[
                "cleaned_data"
            ]
        )

    # ========================================================
    # 3. CURRENT REVIEW DATASET
    # ========================================================

    original_review_df = (
        pipeline_result[
            "review_data"
        ]
    )

    # ========================================================
    # 4. INITIAL CLEANING BASELINE
    #
    # This baseline must remain unchanged across every
    # manual correction round.
    # ========================================================

    initial_unresolved_count = (
        pipeline_result[
            "initial_unresolved_cleaning_issue_count"
        ]
    )

    # ========================================================
    # 5. MERGE ONLY MANUALLY CHANGED VALUES
    # ========================================================

    stage_start = time.perf_counter()

    (
        corrected_df,
        merge_summary
    ) = merge_review_corrections(
        working_df,
        original_review_df,
        corrected_review_df
    )

    _perf_log(
        "Merge review corrections",
        stage_start
    )

    # ========================================================
    # 6. RE-EVALUATE CLEANING ISSUES
    # ========================================================

    stage_start = time.perf_counter()

    unresolved_issues = (
        find_unresolved_cleaning_issues(
            original_df,
            corrected_df
        )
    )

    _perf_log(
        "Recheck unresolved cleaning issues",
        stage_start
    )

    current_unresolved_count = (
        len(
            unresolved_issues
        )
    )

    # ========================================================
    # 7. RECALCULATE CLEANING SCORE
    # ========================================================

    stage_start = time.perf_counter()

    cleaning_score = (
        calculate_cleaning_score(
            initial_unresolved_count,
            current_unresolved_count
        )
    )

    _perf_log(
        "Recalculate cleaning score",
        stage_start
    )

    # ========================================================
    # 8. RE-VALIDATE CORRECTED DATA
    # ========================================================

    stage_start = time.perf_counter()

    validation_result = (
        validate_data(
            corrected_df
        )
    )

    _perf_log(
        "Revalidate corrected data",
        stage_start
    )

    failure_cases = (
        validation_result[
            "failure_cases"
        ]
    )

    validation_success = (
        validation_result[
            "success"
        ]
    )

    # ========================================================
    # SHARED PROBLEM MAP
    # ========================================================

    problem_map_df = (
        create_problem_map(
            original_df,
            failure_cases,
            unresolved_issues
        )
    )

    # ========================================================
    # 9. RECALCULATE ROW-BASED VALIDATION SCORE
    # ========================================================

    stage_start = time.perf_counter()

    validation_score = (
        calculate_validation_score(
            corrected_df,
            failure_cases
        )
    )

    _perf_log(
        "Recalculate validation score",
        stage_start
    )

    # ========================================================
    # 10. VALID / INVALID ROW COUNTS
    # ========================================================

    stage_start = time.perf_counter()

    (
        valid_rows,
        invalid_rows
    ) = get_validation_row_counts(
        corrected_df,
        failure_cases
    )

    _perf_log(
        "Recount valid/invalid rows",
        stage_start
    )

    # ========================================================
    # 11. VALIDATION FAILURES BY COLUMN
    # ========================================================

    validation_failures_by_column = (
        get_validation_failures_by_column(
            failure_cases
        )
    )

    # ========================================================
    # 12. DATA QUALITY CHECK
    # ========================================================

    quality_status = (
        perform_data_quality_check(
            cleaning_score,
            validation_score,
            validation_success
        )
    )

    # ========================================================
    # 13. UPDATED DATA QUALITY REPORT
    # ========================================================

    report = (
        create_validation_report(
            problem_map_df,
            original_df
        )
    )

    # ========================================================
    # 14. CREATE NEXT REVIEW DATASET
    # ========================================================

    stage_start = time.perf_counter()

    if quality_status[
        "export_allowed"
    ]:

        review_df = (
            create_empty_review_dataset()
        )

    else:

        review_df = (
            create_review_dataset(
                original_df,
                corrected_df,
                problem_map_df
            )
        )

    _perf_log(
        "Create next review dataset",
        stage_start
    )

    # ========================================================
    # 15. SUMMARY
    # ========================================================

    summary = {

        "current_rows":
            len(
                corrected_df
            ),

        "initial_unresolved_cleaning_issues":
            initial_unresolved_count,

        "remaining_unresolved_cleaning_issues":
            current_unresolved_count,

        "cleaning_score":
            cleaning_score,

        "validation_score":
            validation_score,

        "validation_success":
            validation_success,

        "valid_rows":
            valid_rows,

        "invalid_rows":
            invalid_rows,

        "review_records":
            len(
                review_df
            ),

        "corrections_received":
            merge_summary[
                "corrections_received"
            ],

        "corrections_applied":
            merge_summary[
                "corrections_applied"
            ],

        "export_allowed":
            quality_status[
                "export_allowed"
            ],

        "export_status":
            quality_status[
                "export_status"
            ],

        "export_reason":
            quality_status[
                "export_reason"
            ]
    }

    # ========================================================
    # 16. RETURN UPDATED PIPELINE RESULT
    # ========================================================

    _perf_log(
        "TOTAL CORRECTION PIPELINE",
        correction_total_start
    )

    return {

        # ----------------------------------------------------
        # ORIGINAL DATA
        # ----------------------------------------------------

        "original_data":
            original_df,


        # ----------------------------------------------------
        # CLEANING BASELINE
        # ----------------------------------------------------

        "initial_unresolved_cleaning_issue_count":
            initial_unresolved_count,


        # ----------------------------------------------------
        # CURRENT CORRECTED DATA
        # ----------------------------------------------------

        "corrected_data":
            corrected_df,


        # ----------------------------------------------------
        # MERGE INFORMATION
        # ----------------------------------------------------

        "merge_summary":
            merge_summary,


        # ----------------------------------------------------
        # CLEANING
        # ----------------------------------------------------

        "unresolved_cleaning_issues":
            unresolved_issues,

        "cleaning_score":
            cleaning_score,


        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        "validation":
            validation_result,

        "validation_score":
            validation_score,

        "valid_rows":
            valid_rows,

        "invalid_rows":
            invalid_rows,

        "validation_failures_by_column":
            validation_failures_by_column,


        # ----------------------------------------------------
        # SHARED PROBLEM MAP
        # ----------------------------------------------------

        "problem_map":
            problem_map_df,


        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        "report":
            report,


        # ----------------------------------------------------
        # QUALITY GATE
        # ----------------------------------------------------

        "cleaning_complete":
            quality_status[
                "cleaning_complete"
            ],

        "validation_complete":
            quality_status[
                "validation_complete"
            ],

        "export_allowed":
            quality_status[
                "export_allowed"
            ],

        "export_status":
            quality_status[
                "export_status"
            ],

        "export_reason":
            quality_status[
                "export_reason"
            ],


        # ----------------------------------------------------
        # NEXT REVIEW ROUND
        # ----------------------------------------------------

        "review_data":
            review_df,

        "review_records":
            len(
                review_df
            ),


        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        "summary":
            summary
    }


# ============================================================
# COMMAND-LINE SMOKE TEST
# ============================================================

if __name__ == "__main__":

    file_path = (
        "data/messy_retail_data_10K.csv"
    )

    result = (
        run_pipeline(
            file_path
        )
    )

    print(
        "\n===== DATA QUALITY PIPELINE ====="
    )

    print(
        "Original Rows:",
        result[
            "summary"
        ][
            "original_rows"
        ]
    )

    print(
        "Cleaned Rows:",
        result[
            "summary"
        ][
            "cleaned_rows"
        ]
    )

    print(
        "Unresolved Cleaning Issues:",
        result[
            "summary"
        ][
            "remaining_unresolved_cleaning_issues"
        ]
    )

    print(
        "Cleaning Score:",
        result[
            "cleaning_score"
        ]
    )

    print(
        "Valid Rows:",
        result[
            "valid_rows"
        ]
    )

    print(
        "Invalid Rows:",
        result[
            "invalid_rows"
        ]
    )

    print(
        "Validation Score:",
        result[
            "validation_score"
        ]
    )

    print(
        "Validation Success:",
        result[
            "validation"
        ][
            "success"
        ]
    )

    print(
        "Review Records:",
        result[
            "review_records"
        ]
    )

    print(
        "Export Status:",
        result[
            "export_status"
        ]
    )

    print(
        "Export Reason:",
        result[
            "export_reason"
        ]
    )

    print(
        "\nValidation Failures by Column:"
    )

    print(
        result[
            "validation_failures_by_column"
        ]
    )

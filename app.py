import csv
import hashlib
import io
import logging
import time
from collections import Counter
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image


from pipeline.profiler import (
    profile_data
)

from pipeline.orchestrator import (
    run_pipeline_from_dataframe,
    apply_review_corrections
)

from pipeline.exporter import (
    create_export_csv,
    ExportBlockedError
)


# ============================================================
# STREAMLIT PERFORMANCE PROFILING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)

APP_RERUN_START = time.perf_counter()


def perf_log(stage_name, start_time):
    """Log Streamlit UI-stage execution time."""

    elapsed = time.perf_counter() - start_time

    logger.info(
        "[UI PERFORMANCE] %-35s %.4f sec",
        stage_name,
        elapsed
    )

    return elapsed



# ============================================================
# UPLOAD VALIDATION
# ============================================================

# ============================================================
# LARGE REVIEW DATASET SAFEGUARDS
# ============================================================

LARGE_REVIEW_WARNING_ROWS = 10_000
REVIEW_PREVIEW_ROWS = 200


REQUIRED_COLUMNS = [
    "Order_ID",
    "Customer_Name",
    "Customer_Email",
    "City",
    "Category",
    "Product",
    "Quantity",
    "Unit_Price",
    "Discount",
    "Total_Amount",
    "Order_Date",
    "Payment_Method",
    "Order_Status",
    "Customer_Age",
    "Customer_Rating",
]


def validate_uploaded_csv(uploaded_file):
    """
    Validate the uploaded file before profiling or pipeline execution.

    Returns:
        (DataFrame | None, list[str])

    Validation rules:
        - .csv extension required
        - file must contain bytes
        - file must be UTF-8/UTF-8-SIG readable
        - file must not be whitespace-only
        - CSV header must be parseable
        - duplicate column names are rejected
        - CSV must be readable by pandas
        - at least one data row is required
        - at least one column is required
        - all required columns must be present
    """

    errors = []

    filename = (
        uploaded_file.name
        or ""
    )

    # --------------------------------------------------------
    # 1. FILE EXTENSION
    # --------------------------------------------------------

    if Path(filename).suffix.lower() != ".csv":
        errors.append(
            "Only CSV files (.csv) are supported."
        )

    # --------------------------------------------------------
    # 2. FILE CONTENT
    # --------------------------------------------------------

    raw_bytes = uploaded_file.getvalue()

    if not raw_bytes:
        errors.append(
            "The uploaded file is empty (0 bytes)."
        )

        return None, errors

    # --------------------------------------------------------
    # 3. TEXT DECODING / WHITESPACE-ONLY CHECK
    # --------------------------------------------------------

    try:
        csv_text = raw_bytes.decode(
            "utf-8-sig"
        )

    except UnicodeDecodeError:
        errors.append(
            "The CSV could not be decoded as UTF-8."
        )

        return None, errors

    if not csv_text.strip():
        errors.append(
            "The uploaded CSV contains no data."
        )

        return None, errors

    # --------------------------------------------------------
    # 4. RAW HEADER VALIDATION
    #
    # Pandas automatically renames duplicate headers such as
    # Product,Product -> Product,Product.1. Inspect the raw CSV
    # header first so duplicate columns cannot be hidden.
    # --------------------------------------------------------

    try:
        reader = csv.reader(
            io.StringIO(
                csv_text
            )
        )

        header = next(
            reader
        )

    except (
        csv.Error,
        StopIteration,
    ):
        errors.append(
            "The CSV header could not be read."
        )

        return None, errors

    if not header:
        errors.append(
            "The CSV does not contain any columns."
        )

        return None, errors

    normalized_header = [
        column.strip()
        for column in header
    ]

    blank_headers = [
        index + 1
        for index, column
        in enumerate(
            normalized_header
        )
        if not column
    ]

    if blank_headers:
        errors.append(
            "The CSV contains one or more blank column names."
        )

    header_counts = Counter(
        normalized_header
    )

    duplicate_columns = sorted(
        column
        for column, count
        in header_counts.items()
        if column and count > 1
    )

    if duplicate_columns:
        errors.append(
            "Duplicate column names detected: "
            + ", ".join(
                duplicate_columns
            )
            + "."
        )

    # Do not continue into pandas when the header itself is invalid.
    if errors:
        return None, errors

    # --------------------------------------------------------
    # 5. PANDAS CSV PARSING
    # --------------------------------------------------------

    try:
        uploaded_df = pd.read_csv(
            io.BytesIO(
                raw_bytes
            ),
            keep_default_na=False,
        )

    except pd.errors.EmptyDataError:
        errors.append(
            "The CSV is empty or does not contain a readable header."
        )

        return None, errors

    except pd.errors.ParserError:
        errors.append(
            "The CSV is malformed and could not be parsed."
        )

        return None, errors

    except Exception:
        errors.append(
            "The uploaded CSV could not be read."
        )

        return None, errors

    # --------------------------------------------------------
    # 6. DATASET SHAPE
    # --------------------------------------------------------

    if uploaded_df.shape[1] == 0:
        errors.append(
            "The CSV does not contain any columns."
        )

    if uploaded_df.empty:
        errors.append(
            "The CSV contains a header but no data rows."
        )

    # --------------------------------------------------------
    # 7. REQUIRED COLUMNS
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in uploaded_df.columns
    ]

    if missing_columns:
        errors.append(
            "Required columns are missing: "
            + ", ".join(
                missing_columns
            )
            + "."
        )

    if errors:
        return None, errors

    return uploaded_df, []


# ============================================================
# APP BRANDING
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

LOGO_PATH = (
    BASE_DIR
    / "assets"
    / "logo"
    / "csv_data_guard_shield_transparent.png"
)

FALLBACK_LOGO_PATH = (
    BASE_DIR
    / "assets"
    / "csv_data_guard_shield.png"
)

ACTIVE_LOGO_PATH = (
    LOGO_PATH
    if LOGO_PATH.exists()
    else FALLBACK_LOGO_PATH
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

if ACTIVE_LOGO_PATH.exists():

    app_icon = Image.open(
        ACTIVE_LOGO_PATH
    )

else:

    app_icon = "🛡️"


st.set_page_config(
    page_title="CSV Data Guard",
    page_icon=app_icon,
    layout="wide"
)


# ============================================================
# HEADER
# ============================================================

header_col1, header_col2 = st.columns(
    [0.65, 9.35],
    vertical_alignment="center"
)


with header_col1:

    if ACTIVE_LOGO_PATH.exists():

        st.image(
            str(ACTIVE_LOGO_PATH),
            width=72
        )

    else:

        st.markdown(
            "<div style='font-size:52px;line-height:1;'>🛡️</div>",
            unsafe_allow_html=True
        )


with header_col2:

    # Keep each HTML block on one physical line so Streamlit
    # cannot interpret indentation as a Markdown code block.
    st.markdown(
        "<div style='font-size:52px;font-weight:700;line-height:1.0;margin:0;padding:0;'>CSV Data Guard</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div style='margin-top:8px;font-size:18px;color:#9aa0a6;line-height:1.3;'>Data Quality, Validation &amp; Remediation Automation</div>",
        unsafe_allow_html=True
    )


# ============================================================
# SESSION STATE
# ============================================================

if (
    "run_quality_analysis"
    not in st.session_state
):
    st.session_state[
        "run_quality_analysis"
    ] = False


if (
    "pipeline_result"
    not in st.session_state
):
    st.session_state[
        "pipeline_result"
    ] = None


if (
    "review_round"
    not in st.session_state
):
    st.session_state[
        "review_round"
    ] = 1


if (
    "last_merge_summary"
    not in st.session_state
):
    st.session_state[
        "last_merge_summary"
    ] = None


if (
    "uploaded_file_signature"
    not in st.session_state
):
    st.session_state[
        "uploaded_file_signature"
    ] = None


if (
    "uploaded_profile"
    not in st.session_state
):
    st.session_state[
        "uploaded_profile"
    ] = None


if (
    "ui_busy"
    not in st.session_state
):
    st.session_state[
        "ui_busy"
    ] = False


if (
    "pending_action"
    not in st.session_state
):
    st.session_state[
        "pending_action"
    ] = None


if (
    "pending_corrected_review_df"
    not in st.session_state
):
    st.session_state[
        "pending_corrected_review_df"
    ] = None


if (
    "pending_correction_request_id"
    not in st.session_state
):
    st.session_state[
        "pending_correction_request_id"
    ] = None


if (
    "last_correction_request_id"
    not in st.session_state
):
    st.session_state[
        "last_correction_request_id"
    ] = None


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "Upload CSV",
    type=["csv" ],
    label_visibility="collapsed",
    disabled=st.session_state[
        "ui_busy"
    ],
)


# ============================================================
# NO FILE UPLOADED
# ============================================================

if uploaded_file is None:

    st.info(
        "Upload a CSV file to begin."
    )

    st.session_state[
        "run_quality_analysis"
    ] = False

    st.session_state[
        "pipeline_result"
    ] = None

    st.session_state[
        "review_round"
    ] = 1

    st.session_state[
        "last_merge_summary"
    ] = None

    st.session_state[
        "uploaded_file_signature"
    ] = None

    st.session_state[
        "uploaded_profile"
    ] = None

    st.session_state[
        "ui_busy"
    ] = False

    st.session_state[
        "pending_action"
    ] = None

    st.session_state[
        "pending_corrected_review_df"
    ] = None

    st.session_state[
        "pending_correction_request_id"
    ] = None

    perf_log(
        "No-file screen rerun",
        APP_RERUN_START
    )

    st.stop()


# ============================================================
# RESET STATE WHEN DIFFERENT CSV IS UPLOADED
# ============================================================

file_signature = (
    uploaded_file.name,
    uploaded_file.size
)


if (
    st.session_state[
        "uploaded_file_signature"
    ] is not None
    and
    st.session_state[
        "uploaded_file_signature"
    ] != file_signature
):

    st.session_state[
        "run_quality_analysis"
    ] = False

    st.session_state[
        "pipeline_result"
    ] = None

    st.session_state[
        "review_round"
    ] = 1

    st.session_state[
        "last_merge_summary"
    ] = None

    st.session_state[
        "uploaded_profile"
    ] = None


st.session_state[
    "uploaded_file_signature"
] = file_signature


# ============================================================
# VALIDATE AND LOAD UPLOADED CSV
# ============================================================

csv_validation_start = time.perf_counter()

uploaded_df, upload_errors = (
    validate_uploaded_csv(
        uploaded_file
    )
)

perf_log(
    "CSV upload validation/read",
    csv_validation_start
)


if upload_errors:

    st.error(
        "The uploaded file cannot be processed."
    )

    for error_message in upload_errors:

        st.write(
            f"• {error_message}"
        )

    # Make sure a rejected upload cannot reuse a previous result.
    st.session_state[
        "run_quality_analysis"
    ] = False

    st.session_state[
        "pipeline_result"
    ] = None

    st.session_state[
        "uploaded_profile"
    ] = None

    perf_log(
        "Rejected upload rerun",
        APP_RERUN_START
    )

    st.stop()


# ============================================================
# SCREEN 1 — DATASET PROFILING
# ============================================================

if not st.session_state[
    "run_quality_analysis"
]:

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    st.header(
        "Uploaded Dataset"
    )

    # --------------------------------------------------------
    # PROFILE DATA
    # --------------------------------------------------------

    profiling_start = time.perf_counter()

    profile = profile_data(
        uploaded_df
    )

    st.session_state[
        "uploaded_profile"
    ] = profile

    perf_log(
        "Dataset profiling",
        profiling_start
    )

    # --------------------------------------------------------
    # PROFILE METRICS
    # --------------------------------------------------------

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    col1.metric(
        "Rows",
        f"{profile['rows']:,}"
    )

    col2.metric(
        "Columns",
        profile[
            "columns"
        ]
    )

    col3.metric(
        "Duplicate Rows",
        f"{profile['duplicate_rows']:,}"
    )

    col4.metric(
        "Blank Cells",
        (
            f"{profile['missing_value_profile']['total_blank_cells']:,}"
        )
    )

    col5, col6, col7, col8 = (
        st.columns(4)
    )

    col5.metric(
        "Missing Values",
        (
            f"{profile['missing_value_profile']['total_missing_value_cells']:,}"
        )
    )

    col6.metric(
        "Invalid Values",
        (
            f"{profile['missing_value_profile']['total_invalid_value_cells']:,}"
        )
    )

    col7.metric(
        "Duplicate Order IDs",
        (
            f"{profile['order_id_duplicate_profile']['affected_rows']:,}"
        )
    )

    col8.metric(
        "Data Columns",
        profile[
            "columns"
        ]
    )

    st.divider()

    # ========================================================
    # DATA PROFILING RESULT
    # ========================================================

    st.subheader(
        "Data Profiling"
    )

    # --------------------------------------------------------
    # DETERMINE WHETHER PROFILER FOUND ISSUES
    # --------------------------------------------------------

    has_profile_issues = (

        profile[
            "duplicate_rows"
        ] > 0

        or

        profile[
            "missing_value_profile"
        ][
            "total_blank_cells"
        ] > 0

        or

        profile[
            "missing_value_profile"
        ][
            "total_missing_value_cells"
        ] > 0

        or

        profile[
            "missing_value_profile"
        ][
            "total_invalid_value_cells"
        ] > 0

        or

        profile[
            "order_id_duplicate_profile"
        ][
            "affected_rows"
        ] > 0
    )

    # --------------------------------------------------------
    # MESSY DATA MESSAGE
    # --------------------------------------------------------

    if has_profile_issues:

        st.warning(
            "The uploaded dataset has been profiled. "
            "Data-quality issues were detected and should "
            "be cleaned and validated before export."
        )

        action_label = (
            "Clean & Validate CSV"
        )

    # --------------------------------------------------------
    # APPARENTLY CLEAN DATA MESSAGE
    # --------------------------------------------------------

    else:

        st.success(
            "The uploaded dataset has been profiled and "
            "no profiling-level data-quality issues were detected. "
            "Run validation to confirm that the dataset satisfies "
            "all configured business rules."
        )

        action_label = (
            "Validate CSV"
        )

    st.write("")

    perf_log(
        "Profile screen rerun",
        APP_RERUN_START
    )

    # --------------------------------------------------------
    # CONTINUE TO DATA QUALITY ANALYSIS
    # --------------------------------------------------------

    if st.button(
        action_label,
        type="primary",
        disabled=st.session_state[
            "ui_busy"
        ]
    ):

        st.session_state[
            "ui_busy"
        ] = True

        st.session_state[
            "pending_action"
        ] = "initial_pipeline"

        st.session_state[
            "run_quality_analysis"
        ] = True

        st.session_state[
            "pipeline_result"
        ] = None

        st.session_state[
            "review_round"
        ] = 1

        st.session_state[
            "last_merge_summary"
        ] = None

        st.rerun()


# ============================================================
# SCREEN 2 — DATA QUALITY ANALYSIS
# ============================================================

else:

    result = (
        st.session_state[
            "pipeline_result"
        ]
    )

    # ========================================================
    # RUN INITIAL PIPELINE ONCE
    # ========================================================

    if result is None:

        with st.spinner(
            "Cleaning and validating dataset..."
        ):

            pipeline_start = time.perf_counter()

            result = run_pipeline_from_dataframe(
                uploaded_df,
                st.session_state[
                    "uploaded_profile"
                ]
            )

            perf_log(
                "Initial pipeline execution",
                pipeline_start
            )

            st.session_state[
                "pipeline_result"
            ] = result

            st.session_state[
                "ui_busy"
            ] = False

            st.session_state[
                "pending_action"
            ] = None

    # ========================================================
    # APPLY PENDING CORRECTIONS ONCE
    # ========================================================

    if (
        st.session_state[
            "pending_action"
        ] == "apply_corrections"
    ):

        correction_request_id = (
            st.session_state[
                "pending_correction_request_id"
            ]
        )

        corrected_review_df = (
            st.session_state[
                "pending_corrected_review_df"
            ]
        )

        # Ignore a duplicate queued click for the exact same
        # review round/file request.
        if (
            correction_request_id
            ==
            st.session_state[
                "last_correction_request_id"
            ]
        ):

            st.session_state[
                "ui_busy"
            ] = False

            st.session_state[
                "pending_action"
            ] = None

            st.session_state[
                "pending_corrected_review_df"
            ] = None

            st.session_state[
                "pending_correction_request_id"
            ] = None

            st.rerun()

        try:

            with st.spinner(
                "Applying corrections and "
                "re-evaluating data quality..."
            ):

                correction_start = (
                    time.perf_counter()
                )

                next_result = (
                    apply_review_corrections(
                        result,
                        corrected_review_df
                    )
                )

                perf_log(
                    "Review correction pipeline",
                    correction_start
                )

            st.session_state[
                "last_correction_request_id"
            ] = correction_request_id

            st.session_state[
                "pipeline_result"
            ] = next_result

            st.session_state[
                "last_merge_summary"
            ] = (
                next_result[
                    "merge_summary"
                ]
            )

            st.session_state[
                "review_round"
            ] += 1

            st.session_state[
                "ui_busy"
            ] = False

            st.session_state[
                "pending_action"
            ] = None

            st.session_state[
                "pending_corrected_review_df"
            ] = None

            st.session_state[
                "pending_correction_request_id"
            ] = None

            st.rerun()

        except ValueError as exc:

            st.session_state[
                "ui_busy"
            ] = False

            st.session_state[
                "pending_action"
            ] = None

            st.session_state[
                "pending_corrected_review_df"
            ] = None

            st.session_state[
                "pending_correction_request_id"
            ] = None

            st.error(
                "Could not apply corrections: "
                f"{exc}"
            )

        except Exception as exc:

            st.session_state[
                "ui_busy"
            ] = False

            st.session_state[
                "pending_action"
            ] = None

            st.session_state[
                "pending_corrected_review_df"
            ] = None

            st.session_state[
                "pending_correction_request_id"
            ] = None

            st.error(
                "An unexpected error occurred "
                "while applying corrections."
            )

            st.exception(
                exc
            )

    # ========================================================
    # NORMALIZE CURRENT PIPELINE STATE
    # ========================================================

    original_df = (
        result[
            "original_data"
        ]
    )

    # --------------------------------------------------------
    # REVIEW ROUND RESULT
    # --------------------------------------------------------

    if (
        "corrected_data"
        in result
    ):

        working_df = (
            result[
                "corrected_data"
            ]
        )

    # --------------------------------------------------------
    # INITIAL PIPELINE RESULT
    # --------------------------------------------------------

    else:

        working_df = (
            result[
                "cleaned_data"
            ]
        )

    # --------------------------------------------------------
    # CURRENT SCORES
    # --------------------------------------------------------

    cleaning_score = (
        result[
            "cleaning_score"
        ]
    )

    validation_score = (
        result[
            "validation_score"
        ]
    )

    # --------------------------------------------------------
    # CURRENT QUALITY GATE
    # --------------------------------------------------------

    export_allowed = (
        result[
            "export_allowed"
        ]
    )

    export_status = (
        result[
            "export_status"
        ]
    )

    export_reason = (
        result[
            "export_reason"
        ]
    )

    # --------------------------------------------------------
    # CURRENT REVIEW DATA
    # --------------------------------------------------------

    review_df = (
        result[
            "review_data"
        ]
    )

    review_required = (
        not export_allowed
    )

    # --------------------------------------------------------
    # CURRENT UNRESOLVED CLEANING ISSUES
    # --------------------------------------------------------

    unresolved_issues = (
        result[
            "unresolved_cleaning_issues"
        ]
    )

    # --------------------------------------------------------
    # CURRENT VALIDATION RESULT
    # --------------------------------------------------------

    validation = (
        result[
            "validation"
        ]
    )

    failure_cases = (
        validation[
            "failure_cases"
        ]
    )

    # --------------------------------------------------------
    # CURRENT DATA QUALITY REPORT
    # --------------------------------------------------------

    report = (
        result[
            "report"
        ]
    )

    # ========================================================
    # HEADER
    # ========================================================

    st.header(
        "DATA QUALITY ANALYSIS"
    )

    # --------------------------------------------------------
    # CURRENT REVIEW ROUND
    # --------------------------------------------------------

    if review_required:

        st.caption(
            "Current Review Round: "
            f"{st.session_state['review_round']}"
        )

    # ========================================================
    # SCORES
    # ========================================================

    score_col1, score_col2 = (
        st.columns(2)
    )

    score_col1.metric(
        "Cleaning Score",
        f"{cleaning_score:.2f}%"
    )

    score_col2.metric(
        "Validation Score",
        f"{validation_score:.2f}%"
    )

    score_col1.caption(
        "Percentage of unresolved post-cleaning issues "
        "that have been manually resolved."
    )

    score_col2.caption(
        "Percentage of current rows that pass all "
        "configured validation rules."
    )

    # --------------------------------------------------------
    # LAST REVIEW ROUND SUMMARY
    # --------------------------------------------------------

    if (
        st.session_state[
            "last_merge_summary"
        ] is not None
    ):

        merge_summary = (
            st.session_state[
                "last_merge_summary"
            ]
        )

        st.success(
            "Last review round applied "
            f"{merge_summary['corrections_applied']:,} "
            "manual correction(s)."
        )

        if (
            merge_summary.get(
                "correction_columns"
            )
        ):

            st.write(
                "Corrected columns: "
                + ", ".join(
                    merge_summary[
                        "correction_columns"
                    ]
                )
            )

    st.divider()

    # ========================================================
    # CHART PERFORMANCE MEASUREMENT
    # ========================================================

    charts_start = time.perf_counter()

    # ========================================================
    # CLEANING COMPARISON
    # ========================================================

    st.subheader(
        "Cleaning Comparison"
    )

    cleaning_chart_df = (
        pd.DataFrame(
            {
                "Status": [
                    "Original Dataset",
                    "Current Dataset"
                ],

                "Rows": [
                    len(
                        original_df
                    ),

                    len(
                        working_df
                    )
                ]
            }
        )
    )

    fig_cleaning = px.bar(
        cleaning_chart_df,
        x="Status",
        y="Rows",
        text="Rows",
        title=(
            "Original vs Current Rows"
        )
    )

    fig_cleaning.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        fig_cleaning,
        width='stretch'
    )

    # ========================================================
    # REMOVED DUPLICATE ROWS
    # ========================================================

    removed_duplicate_rows = (
        result.get(
            "removed_duplicate_rows"
        )
    )

    if (
        removed_duplicate_rows is not None
        and not removed_duplicate_rows.empty
    ):

        st.info(
            f"{len(removed_duplicate_rows):,} duplicate row(s) "
            "were removed during automated cleaning."
        )

        duplicate_export_df = (
            removed_duplicate_rows
            .drop(
                columns=[
                    "Record_ID"
                ],
                errors="ignore"
            )
        )

        removed_duplicates_csv = (
            duplicate_export_df
            .to_csv(
                index=False
            )
            .encode(
                "utf-8"
            )
        )

        st.download_button(
            label=(
                "Download Removed Duplicate Rows"
            ),
            data=removed_duplicates_csv,
            file_name=(
                "removed_duplicate_rows.csv"
            ),
            mime="text/csv",
            disabled=st.session_state[
                "ui_busy"
            ]
        )

    # ========================================================
    # VALIDATION ANALYSIS
    # ========================================================

    st.subheader(
        "Validation Analysis"
    )

    # --------------------------------------------------------
    # NO FAILURES
    # --------------------------------------------------------

    if (
        failure_cases is None
        or failure_cases.empty
    ):

        valid_rows = (
            len(
                working_df
            )
        )

        invalid_rows = 0

    # --------------------------------------------------------
    # ROW-LEVEL FAILURES
    # --------------------------------------------------------

    else:

        invalid_indexes = (
            failure_cases[
                "index"
            ]
            .dropna()
            .unique()
        )

        invalid_rows = (
            len(
                invalid_indexes
            )
        )

        valid_rows = (
            len(
                working_df
            )
            - invalid_rows
        )

    validation_chart_df = (
        pd.DataFrame(
            {
                "Status": [
                    "Valid Rows",
                    "Invalid Rows"
                ],

                "Rows": [
                    valid_rows,
                    invalid_rows
                ]
            }
        )
    )

    fig_validation = px.bar(
        validation_chart_df,
        x="Status",
        y="Rows",
        text="Rows",
        title=(
            "Validation Result"
        )
    )

    fig_validation.update_traces(
        textposition="outside"
    )

    st.plotly_chart(
        fig_validation,
        width='stretch'
    )

    # ========================================================
    # UNRESOLVED CLEANING ISSUES
    # ========================================================

    st.subheader(
        "Unresolved Cleaning Issues"
    )

    if (
        unresolved_issues is None
        or unresolved_issues.empty
    ):

        st.success(
            "No unresolved cleaning issues."
        )

    else:

        unresolved_chart_df = (

            unresolved_issues

            .groupby(
                "column"
            )

            .size()

            .reset_index(
                name="Records"
            )

            .sort_values(
                "Records",
                ascending=False
            )
        )

        fig_unresolved = px.bar(
            unresolved_chart_df,
            x="column",
            y="Records",
            text="Records",
            title=(
                "Unresolved Cleaning Issues by Column"
            )
        )

        fig_unresolved.update_traces(
            textposition="outside"
        )

        fig_unresolved.update_layout(
            xaxis_title="Column",
            yaxis_title="Records"
        )

        st.plotly_chart(
            fig_unresolved,
            width='stretch'
        )

    # ========================================================
    # VALIDATION ISSUES
    # ========================================================

    st.subheader(
        "Validation Issues"
    )

    if (
        failure_cases is None
        or failure_cases.empty
    ):

        st.success(
            "No validation issues found."
        )

    else:

        row_failure_cases = (
            failure_cases[
                failure_cases[
                    "index"
                ].notna()
            ]
        )

        if row_failure_cases.empty:

            st.warning(
                "Validation failed, but no row-level "
                "failure information is available."
            )

        else:

            validation_issue_chart = (

                row_failure_cases

                .groupby(
                    "column"
                )[
                    "index"
                ]

                .nunique()

                .reset_index(
                    name="Records Affected"
                )

                .sort_values(
                    "Records Affected",
                    ascending=False
                )
            )

            fig_validation_issues = (
                px.bar(
                    validation_issue_chart,
                    x="column",
                    y="Records Affected",
                    text="Records Affected",
                    title=(
                        "Validation Failures by Column"
                    )
                )
            )

            fig_validation_issues.update_traces(
                textposition="outside"
            )

            fig_validation_issues.update_layout(
                xaxis_title="Column",
                yaxis_title=(
                    "Records Affected"
                ),
                xaxis_tickangle=-45
            )

            st.plotly_chart(
                fig_validation_issues,
                width='stretch'
            )

    # ========================================================
    # DATA QUALITY SUMMARY
    # ========================================================

    st.subheader(
        "Data Quality Summary"
    )

    summary_chart_df = (
        pd.DataFrame(
            {
                "Status": [
                    "Passed Validation",
                    "Failed Validation"
                ],

                "Rows": [
                    valid_rows,
                    invalid_rows
                ]
            }
        )
    )

    fig_summary = px.pie(
        summary_chart_df,
        names="Status",
        values="Rows",
        title=(
            "Validation Quality Summary"
        )
    )

    st.plotly_chart(
        fig_summary,
        width='stretch'
    )

    perf_log(
        "Plotly chart construction",
        charts_start
    )

    # ========================================================
    # DATA QUALITY REPORT
    # ========================================================

    st.subheader(
        "Data Quality Report"
    )

    # --------------------------------------------------------
    # FINAL SUCCESS STATE
    #
    # Once the backend quality gate passes, this section must
    # describe the CURRENT dataset rather than historical
    # issues detected in the original upload.
    # --------------------------------------------------------

    if export_allowed:

        st.success(
            "No data-quality issues remain in the current dataset."
        )

    elif (
        report is None
        or report.empty
    ):

        st.success(
            "No unresolved data-quality issues found."
        )

    else:

        desired_report_columns = [
            "Field",
            "Validation Error",
            "Records Affected",
            "How to Fix"
        ]

        available_report_columns = [
            column
            for column
            in desired_report_columns
            if column in report.columns
        ]

        if available_report_columns:

            display_report = (
                report[
                    available_report_columns
                ]
            )

        else:

            display_report = (
                report
            )

        st.dataframe(
            display_report,
            width='stretch',
            hide_index=True
        )

    # ========================================================
    # REVIEW DATASET + MANUAL CORRECTION LOOP
    # ========================================================

    if review_required:

        st.subheader(
            "Manual Review"
        )

        st.warning(
            "The dataset contains unresolved data-quality "
            "issues. Final export remains blocked."
        )

        if (
            review_df is not None
            and not review_df.empty
        ):

            current_round = (
                st.session_state[
                    "review_round"
                ]
            )

            st.write(
                "Records requiring review: "
                f"**{len(review_df):,}**"
            )

            if (
                len(review_df)
                >= LARGE_REVIEW_WARNING_ROWS
            ):

                st.warning(
                    "This review dataset is large. Manual correction "
                    "may be time-consuming. Download the full review CSV "
                    "and edit it offline before uploading the corrected "
                    "file. Only a limited preview is shown in the app."
                )

            preview_rows = min(
                len(review_df),
                REVIEW_PREVIEW_ROWS
            )

            st.caption(
                f"Previewing {preview_rows:,} of "
                f"{len(review_df):,} review record(s)."
            )

            st.dataframe(
                review_df.head(
                    REVIEW_PREVIEW_ROWS
                ),
                width='stretch',
                hide_index=True
            )

            st.info(
                "Review-file convention: blank cells do not "
                "require correction. [MISSING] means a required "
                "value is missing. Other populated values are "
                "the values that require manual review."
            )

            # ------------------------------------------------
            # DOWNLOAD REVIEW DATASET
            # ------------------------------------------------

            review_csv_start = time.perf_counter()

            review_csv = (
                review_df
                .to_csv(
                    index=False
                )
                .encode(
                    "utf-8"
                )
            )

            perf_log(
                "Review CSV generation",
                review_csv_start
            )

            st.download_button(
                label=(
                    f"Download Review Dataset "
                    f"— Round {current_round}"
                ),

                data=review_csv,

                file_name=(
                    f"review_dataset_round_{current_round}.csv"
                ),

                mime="text/csv",
                disabled=st.session_state[
                    "ui_busy"
                ]
            )

            st.write("")

            st.write(
                "Correct the populated problem cells in the "
                "downloaded review CSV, save the file, and "
                "upload the corrected version below. "
                "Do not remove Record_ID or Order_ID."
            )

            # ------------------------------------------------
            # UPLOAD CORRECTED REVIEW DATASET
            # ------------------------------------------------

            corrected_review_file = (
                st.file_uploader(
                    "Upload Corrected Review Dataset",
                    type=[
                        "csv"
                    ],
                    key=(
                        "corrected_review_upload_"
                        f"{current_round}"
                    ),
                    disabled=st.session_state[
                        "ui_busy"
                    ]
                )
            )

            if (
                corrected_review_file
                is not None
            ):

                try:

                    corrected_read_start = time.perf_counter()

                    corrected_review_df = (
                        pd.read_csv(
                            corrected_review_file,
                            keep_default_na=False
                        )
                    )

                    perf_log(
                        "Corrected review CSV read",
                        corrected_read_start
                    )

                except Exception as exc:

                    st.error(
                        "The corrected review CSV "
                        "could not be read."
                    )

                    st.exception(
                        exc
                    )

                    st.stop()

                # --------------------------------------------
                # APPLY CORRECTIONS
                # --------------------------------------------

                if st.button(
                    "Apply Corrections",
                    type="primary",
                    key=(
                        "apply_corrections_"
                        f"{current_round}"
                    ),
                    disabled=st.session_state[
                        "ui_busy"
                    ]
                ):

                    correction_bytes = (
                        corrected_review_file
                        .getvalue()
                    )

                    correction_hash = (
                        hashlib.sha256(
                            correction_bytes
                        )
                        .hexdigest()
                    )

                    correction_request_id = (
                        f"{current_round}:"
                        f"{correction_hash}"
                    )

                    # Lock the UI immediately and queue exactly
                    # one correction operation for the next rerun.
                    st.session_state[
                        "ui_busy"
                    ] = True

                    st.session_state[
                        "pending_action"
                    ] = "apply_corrections"

                    st.session_state[
                        "pending_corrected_review_df"
                    ] = (
                        corrected_review_df.copy(
                            deep=True
                        )
                    )

                    st.session_state[
                        "pending_correction_request_id"
                    ] = (
                        correction_request_id
                    )

                    st.rerun()

        else:

            st.info(
                "No review records were generated."
            )

    # ========================================================
    # FINAL EXPORT / QUALITY GATE
    # ========================================================

    st.divider()

    st.subheader(
        "Final Export"
    )

    if export_allowed:

        st.success(
            "Data quality checks passed. "
            "The dataset is ready for export."
        )

        try:

            export_start = time.perf_counter()

            final_csv = create_export_csv(
                result
            )

            perf_log(
                "Final export CSV generation",
                export_start
            )

            st.download_button(
                label=(
                    "Download Final Cleaned CSV"
                ),
                data=final_csv,
                file_name=(
                    "cleaned_validated_dataset.csv"
                ),
                mime="text/csv",
                type="primary",
                disabled=st.session_state[
                    "ui_busy"
                ]
            )

        except ExportBlockedError as exc:

            st.error(
                "The backend quality gate blocked "
                "the final export."
            )

            st.caption(
                str(exc)
            )

        except Exception as exc:

            st.error(
                "The final CSV could not be prepared."
            )

            st.exception(
                exc
            )

    else:

        st.error(
            "Export is currently blocked."
        )

        st.write(
            "The dataset can be exported only when:"
        )

        st.write(
            "- Cleaning Score = 100%"
        )

        st.write(
            "- Validation Score = 100%"
        )

        export_col1, export_col2 = (
            st.columns(2)
        )

        export_col1.metric(
            "Cleaning Score",
            f"{cleaning_score:.2f}%"
        )

        export_col2.metric(
            "Validation Score",
            f"{validation_score:.2f}%"
        )

        if cleaning_score < 100:

            st.warning(
                "Manual remediation is still incomplete."
            )

        if validation_score < 100:

            st.warning(
                "Some rows still fail validation."
            )

        if export_reason:

            st.caption(
                f"Quality gate reason: {export_reason}"
            )

    perf_log(
        "Analysis screen rerun",
        APP_RERUN_START
    )

    # ========================================================
    # START OVER
    #
    # Hide this control after successful final validation/export
    # so an accidental click cannot reset a completed workflow.
    # ========================================================

    if not export_allowed:

        st.write("")

        if st.button(
            "Start Over",
            disabled=st.session_state[
                "ui_busy"
            ]
        ):

            st.session_state[
                "ui_busy"
            ] = False

            st.session_state[
                "pending_action"
            ] = None

            st.session_state[
                "pending_corrected_review_df"
            ] = None

            st.session_state[
                "pending_correction_request_id"
            ] = None

            st.session_state[
                "run_quality_analysis"
            ] = False

            st.session_state[
                "pipeline_result"
            ] = None

            st.session_state[
                "review_round"
            ] = 1

            st.session_state[
                "last_merge_summary"
            ] = None

            st.rerun()

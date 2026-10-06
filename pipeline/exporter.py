import pandas as pd


# ============================================================
# EXPORT ERROR
# ============================================================

class ExportBlockedError(ValueError):
    """
    Raised when an attempt is made to export data before
    the CSV Data Guard quality gate has passed.
    """

    pass


# ============================================================
# GET PIPELINE STATE
# ============================================================

def _get_pipeline_value(
    pipeline_result,
    key,
    default=None
):
    """
    Read a value from either:

        pipeline_result[key]

    or, for initial pipeline results:

        pipeline_result["summary"][key]

    This supports both initial pipeline results and
    remediation-round results.
    """

    if key in pipeline_result:

        return pipeline_result[
            key
        ]


    summary = pipeline_result.get(
        "summary",
        {}
    )


    return summary.get(
        key,
        default
    )


# ============================================================
# DETERMINE CURRENT DATASET
# ============================================================

def get_export_source(
    pipeline_result
):
    """
    Return the current dataset that would be exported.

    Initial pipeline:
        cleaned_data

    After remediation:
        corrected_data
    """

    if not isinstance(
        pipeline_result,
        dict
    ):

        raise ValueError(
            "pipeline_result must be a dictionary."
        )


    # --------------------------------------------------------
    # REMEDIATED DATA TAKES PRIORITY
    # --------------------------------------------------------

    if (
        "corrected_data"
        in pipeline_result
    ):

        dataframe = (
            pipeline_result[
                "corrected_data"
            ]
        )


    # --------------------------------------------------------
    # INITIAL CLEANED DATA
    # --------------------------------------------------------

    elif (
        "cleaned_data"
        in pipeline_result
    ):

        dataframe = (
            pipeline_result[
                "cleaned_data"
            ]
        )


    else:

        raise ValueError(
            "Pipeline result does not contain "
            "cleaned_data or corrected_data."
        )


    if not isinstance(
        dataframe,
        pd.DataFrame
    ):

        raise ValueError(
            "Export source must be a pandas DataFrame."
        )


    return dataframe


# ============================================================
# CHECK EXPORT GATE
# ============================================================

def validate_export_gate(
    pipeline_result
):
    """
    Verify that the dataset is allowed to leave the
    data-quality pipeline.

    Export requires:

        Cleaning Score   = 100%
        Validation Score = 100%
        Validation       = successful
        export_allowed   = True
    """

    if not isinstance(
        pipeline_result,
        dict
    ):

        raise ValueError(
            "pipeline_result must be a dictionary."
        )


    cleaning_score = (
        _get_pipeline_value(
            pipeline_result,
            "cleaning_score"
        )
    )

    validation_score = (
        _get_pipeline_value(
            pipeline_result,
            "validation_score"
        )
    )

    export_allowed = (
        _get_pipeline_value(
            pipeline_result,
            "export_allowed",
            False
        )
    )


    # --------------------------------------------------------
    # VALIDATION SUCCESS
    # --------------------------------------------------------

    validation_result = (
        pipeline_result.get(
            "validation"
        )
    )


    if isinstance(
        validation_result,
        dict
    ):

        validation_success = (
            validation_result.get(
                "success",
                False
            )
        )

    else:

        validation_success = False


    # --------------------------------------------------------
    # QUALITY GATE
    # --------------------------------------------------------

    if (
        cleaning_score != 100.0
        or validation_score != 100.0
        or validation_success is not True
        or export_allowed is not True
    ):

        raise ExportBlockedError(
            "Export blocked. "
            "Cleaning Score, Validation Score, "
            "and validation success must all pass "
            "the data-quality gate."
        )


    return True


# ============================================================
# PREPARE FINAL EXPORT DATA
# ============================================================

def prepare_export_data(
    pipeline_result
):
    """
    Prepare the final business dataset for export.

    Important:

        Record_ID is an internal technical key used only
        during cleaning, validation, review and remediation.

        It must NOT appear in the final exported dataset.
    """

    validate_export_gate(
        pipeline_result
    )


    source_df = (
        get_export_source(
            pipeline_result
        )
    )


    # --------------------------------------------------------
    # COPY — NEVER MUTATE PIPELINE DATA
    # --------------------------------------------------------

    export_df = (
        source_df.copy(
            deep=True
        )
    )


    # --------------------------------------------------------
    # REMOVE INTERNAL TECHNICAL KEY
    # --------------------------------------------------------

    export_df = (
        export_df.drop(
            columns=[
                "Record_ID"
            ],
            errors="ignore"
        )
    )


    # --------------------------------------------------------
    # CLEAN OUTPUT INDEX
    # --------------------------------------------------------

    export_df = (
        export_df.reset_index(
            drop=True
        )
    )


    return export_df


# ============================================================
# CREATE CSV BYTES
# ============================================================

def create_export_csv(
    pipeline_result
):
    """
    Create UTF-8 encoded CSV bytes suitable for:

        Streamlit download
        email attachment
        cloud upload
        local save

    CSV index is never exported.
    """

    export_df = (
        prepare_export_data(
            pipeline_result
        )
    )


    csv_data = (
        export_df.to_csv(
            index=False
        )
        .encode(
            "utf-8"
        )
    )


    return csv_data

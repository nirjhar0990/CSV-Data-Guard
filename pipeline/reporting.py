import pandas as pd
import numpy as np


# ============================================================
# REPORT COLUMNS
# ============================================================

REPORT_COLUMNS = [
    "Field",
    "Validation Error",
    "Records Affected",
    "Affected Order IDs",
    "How to Fix"
]


# ============================================================
# CREATE VALIDATION REPORT
# ============================================================

def create_validation_report(
    problem_map,
    original_df
):
    """
    Performance candidate for the locked 250K reporting baseline.

    Semantics preserved:
    - Uses the full shared problem map.
    - Groups by column + validation_error + how_to_fix.
    - Counts unique Order_ID values per issue group.
    - Preserves first-seen Order_ID order.
    - Returns the same 5 report columns.
    """

    if (
        problem_map is None
        or problem_map.empty
    ):
        return pd.DataFrame(
            columns=REPORT_COLUMNS
        )

    # --------------------------------------------------------
    # FAST INDEX -> ORDER_ID LOOKUP
    #
    # The project uses a RangeIndex for original_df, but keep
    # a safe fallback for any future non-RangeIndex input.
    # --------------------------------------------------------

    issue_indexes = (
        problem_map[
            "index"
        ]
        .to_numpy()
    )

    order_id_values = (
        original_df[
            "Order_ID"
        ]
        .to_numpy()
    )

    if isinstance(
    original_df.index,
    pd.RangeIndex
):

        start = original_df.index.start
        step = original_df.index.step

    if (
        start == 0
        and step == 1
    ):

        positions = (
            issue_indexes
            .astype(
                np.int64,
                copy=False
            )
        )

        valid_position_mask = (
            (positions >= 0)
            &
            (positions < len(original_df))
        )

    else:

        positions = (
            original_df.index
            .get_indexer(
                issue_indexes
            )
        )

        valid_position_mask = (
            positions >= 0
        )


    # --------------------------------------------------------
    # GROUP DIRECTLY ON THE EXISTING PROBLEM MAP
    #
    # This avoids constructing the large intermediate report
    # DataFrame used by the recovered baseline.
    # --------------------------------------------------------

    group_columns = [
        "column",
        "validation_error",
        "how_to_fix"
    ]

    grouped = (
        problem_map.groupby(
            group_columns,
            dropna=False,
            sort=True
        )
    )

    rows = []

    # --------------------------------------------------------
    # ONLY ~19 FINAL GROUPS
    #
    # Iterate once per final issue group. For each group, take
    # the already-vectorized Order_ID positions and use
    # pd.unique(), which preserves first-seen order.
    # --------------------------------------------------------

    for (
        field,
        validation_error,
        how_to_fix
    ), group_positions in grouped.indices.items():

        group_positions = np.asarray(
            group_positions,
            dtype=np.int64
        )

        group_positions = (
            group_positions[
                valid_position_mask[
                    group_positions
                ]
            ]
        )

        if group_positions.size:

            group_order_ids = (
                order_id_values[
                    positions[
                        group_positions
                    ]
                ]
            )

            non_missing = (
                pd.notna(
                    group_order_ids
                )
            )

            group_order_ids = (
                group_order_ids[
                    non_missing
                ]
            )

            if group_order_ids.size:

                unique_order_ids = (
                    pd.unique(
                        group_order_ids.astype(
                            str,
                            copy=False
                        )
                    )
                )

                affected_count = (
                    len(
                        unique_order_ids
                    )
                )

                affected_ids = (
                    ", ".join(
                        unique_order_ids
                    )
                )

            else:

                affected_count = 0
                affected_ids = ""

        else:

            affected_count = 0
            affected_ids = ""

        rows.append(
            {
                "Field":
                    field,

                "Validation Error":
                    validation_error,

                "Records Affected":
                    affected_count,

                "Affected Order IDs":
                    affected_ids,

                "How to Fix":
                    how_to_fix
            }
        )

    result = pd.DataFrame(
        rows,
        columns=REPORT_COLUMNS
    )

    # groupby(sort=True) already yields sorted group keys,
    # but keep the explicit final ordering for exact baseline
    # behavior.
    result = (
        result
        .sort_values(
            by=[
                "Field",
                "Validation Error"
            ]
        )
        .reset_index(
            drop=True
        )
    )

    return result

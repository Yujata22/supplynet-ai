from __future__ import annotations

import pandas as pd
import requests
import streamlit as st


API_BASE_URL = "http://127.0.0.1:8000"


# ---------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------


st.set_page_config(
    page_title="SupplyNet AI",
    page_icon="🚚",
    layout="wide",
)


st.title("SupplyNet AI")

st.caption(
    "Supply network planning, optimization, "
    "scenario simulation, and agentic decision support."
)


# ---------------------------------------------------------------------
# API HELPERS
# ---------------------------------------------------------------------


def get_json(
    path: str,
) -> dict:
    response = requests.get(
        f"{API_BASE_URL}{path}",
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def post_json(
    path: str,
    payload: dict,
) -> dict:
    response = requests.post(
        f"{API_BASE_URL}{path}",
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    return response.json()


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------


st.sidebar.header(
    "Planning Controls"
)

week = st.sidebar.selectbox(
    "Planning Week",
    options=[
        1,
        2,
        3,
        4,
    ],
    index=0,
)


# ---------------------------------------------------------------------
# API STATUS
# ---------------------------------------------------------------------


try:
    health = get_json(
        "/health"
    )

    st.sidebar.success(
        f'API: {health["status"]}'
    )

except Exception:
    st.sidebar.error(
        "API unavailable"
    )

    st.error(
        "FastAPI backend is not running. "
        "Start it with:\n\n"
        "`uvicorn app.main:app --reload`"
    )

    st.stop()


# ---------------------------------------------------------------------
# NETWORK OVERVIEW
# ---------------------------------------------------------------------


try:
    network = get_json(
        "/network"
    )

except Exception as exc:
    st.error(
        f"Unable to load network: {exc}"
    )

    st.stop()


st.subheader(
    "Network Overview"
)

row1 = st.columns(4)

row1[0].metric(
    "Suppliers",
    network[
        "suppliers"
    ],
)

row1[1].metric(
    "Distribution Centers",
    network[
        "distribution_centers"
    ],
)

row1[2].metric(
    "Customer Regions",
    network[
        "customer_regions"
    ],
)

row1[3].metric(
    "Inbound Lanes",
    network[
        "inbound_lanes"
    ],
)


row2 = st.columns(4)

row2[0].metric(
    "Active Suppliers",
    network[
        "active_suppliers"
    ],
)

row2[1].metric(
    "Available Inbound Lanes",
    network[
        "available_inbound_lanes"
    ],
)

row2[2].metric(
    "Outbound Lanes",
    network[
        "outbound_lanes"
    ],
)

row2[3].metric(
    "Available Outbound Lanes",
    network[
        "available_outbound_lanes"
    ],
)


st.divider()


# ---------------------------------------------------------------------
# PLAN COMPARISON
# ---------------------------------------------------------------------


st.subheader(
    f"Week {week} Plan Comparison"
)


try:
    comparison = post_json(
        "/plan/compare",
        {
            "week": week,
        },
    )

except Exception as exc:
    st.error(
        f"Unable to run plan comparison: {exc}"
    )

    st.stop()


naive = comparison[
    "naive"
]

optimized = comparison[
    "optimized"
]

improvement = comparison[
    "improvement"
]


comparison_cols = st.columns(
    4
)

comparison_cols[0].metric(
    "Naive Cost",
    f'${naive["total_cost"]:,.0f}',
)

comparison_cols[1].metric(
    "Optimized Cost",
    f'${optimized["total_cost"]:,.0f}',
)

comparison_cols[2].metric(
    "Cost Savings",
    (
        f'${improvement["cost_savings"]:,.0f}'
    ),
    delta=(
        f'{improvement["cost_savings_pct"]:.2%}'
    ),
)

comparison_cols[3].metric(
    "Solver Status",
    comparison[
        "solver_status"
    ],
)


st.divider()


# ---------------------------------------------------------------------
# SERVICE PERFORMANCE
# ---------------------------------------------------------------------


st.subheader(
    "Service Performance"
)


service_row1 = st.columns(
    3
)

service_row1[0].metric(
    "Naive Fulfillment",
    (
        f'{naive["fulfillment_rate"]:.2%}'
    ),
)

service_row1[1].metric(
    "Optimized Fulfillment",
    (
        f'{optimized["fulfillment_rate"]:.2%}'
    ),
)

service_row1[2].metric(
    "Fulfillment Change",
    (
        f'{improvement["fulfillment_rate_change"]:.2%}'
    ),
)


service_row2 = st.columns(
    3
)

service_row2[0].metric(
    "Naive Unmet Demand",
    (
        f'{naive["unmet_demand_pallets"]:,}'
    ),
)

service_row2[1].metric(
    "Optimized Unmet Demand",
    (
        f'{optimized["unmet_demand_pallets"]:,}'
    ),
)

service_row2[2].metric(
    "Total Demand",
    (
        f'{optimized["total_demand_pallets"]:,}'
    ),
)


st.divider()


# ---------------------------------------------------------------------
# CONTAINER UTILIZATION
# ---------------------------------------------------------------------


st.subheader(
    "Container Utilization"
)


util_cols = st.columns(
    3
)

util_cols[0].metric(
    "Naive Utilization",
    (
        f'{naive["average_container_utilization"]:.2%}'
    ),
)

util_cols[1].metric(
    "Optimized Utilization",
    (
        f'{optimized["average_container_utilization"]:.2%}'
    ),
)

util_cols[2].metric(
    "Utilization Change",
    (
        f'{improvement["container_utilization_change"]:.2%}'
    ),
)


st.divider()


# ---------------------------------------------------------------------
# COST BREAKDOWN
# ---------------------------------------------------------------------


st.subheader(
    "Cost Breakdown"
)


cost_rows = [
    {
        "Cost Component": (
            "Inbound Transportation"
        ),
        "Naive": naive[
            "inbound_transportation_cost"
        ],
        "Optimized": optimized[
            "inbound_transportation_cost"
        ],
    },

    {
        "Cost Component": (
            "Outbound Transportation"
        ),
        "Naive": naive[
            "outbound_transportation_cost"
        ],
        "Optimized": optimized[
            "outbound_transportation_cost"
        ],
    },

    {
        "Cost Component": (
            "Handling"
        ),
        "Naive": naive[
            "handling_cost"
        ],
        "Optimized": optimized[
            "handling_cost"
        ],
    },

    {
        "Cost Component": (
            "Inventory Holding"
        ),
        "Naive": naive[
            "holding_cost"
        ],
        "Optimized": optimized[
            "holding_cost"
        ],
    },

    {
        "Cost Component": (
            "Shortage"
        ),
        "Naive": naive[
            "shortage_cost"
        ],
        "Optimized": optimized[
            "shortage_cost"
        ],
    },
]


cost_df = pd.DataFrame(
    cost_rows
)


st.dataframe(
    cost_df.style.format(
        {
            "Naive": "${:,.2f}",
            "Optimized": "${:,.2f}",
        }
    ),
    use_container_width=True,
)


chart_df = (
    cost_df
    .set_index(
        "Cost Component"
    )[
        [
            "Naive",
            "Optimized",
        ]
    ]
)


st.bar_chart(
    chart_df
)


st.divider()


# ---------------------------------------------------------------------
# OPTIMIZED PLAN DETAILS
# ---------------------------------------------------------------------


st.subheader(
    "Optimized Network Plan"
)


if st.button(
    "Load Optimized Allocation Details",
):
    try:
        with st.spinner(
            "Loading optimized allocations..."
        ):
            optimized_plan = post_json(
                "/plan/optimize",
                {
                    "week": week,
                },
            )

        (
            inbound_tab,
            outbound_tab,
            inventory_tab,
            unmet_tab,
        ) = st.tabs(
            [
                "Inbound",
                "Outbound",
                "Inventory",
                "Unmet Demand",
            ]
        )


        with inbound_tab:
            inbound_df = pd.DataFrame(
                optimized_plan[
                    "inbound_allocations"
                ]
            )

            if inbound_df.empty:
                st.info(
                    "No inbound allocations."
                )

            else:
                display_columns = [
                    "supplier_id",
                    "dc_id",
                    "pallets",
                    "containers",
                    "container_utilization",
                    "transportation_cost",
                ]

                st.dataframe(
                    inbound_df[
                        display_columns
                    ],
                    use_container_width=True,
                )


        with outbound_tab:
            outbound_df = pd.DataFrame(
                optimized_plan[
                    "outbound_allocations"
                ]
            )

            if outbound_df.empty:
                st.info(
                    "No outbound allocations."
                )

            else:
                st.dataframe(
                    outbound_df,
                    use_container_width=True,
                )


        with inventory_tab:
            inventory_df = pd.DataFrame(
                optimized_plan[
                    "ending_inventory"
                ]
            )

            st.dataframe(
                inventory_df,
                use_container_width=True,
            )


        with unmet_tab:
            unmet_df = pd.DataFrame(
                optimized_plan[
                    "unmet_demand"
                ]
            )

            st.dataframe(
                unmet_df,
                use_container_width=True,
            )

    except Exception as exc:
        st.error(
            f"Unable to load optimized plan: {exc}"
        )


st.divider()


# ---------------------------------------------------------------------
# AGENTIC SCENARIO ANALYST
# ---------------------------------------------------------------------


st.subheader(
    "AI Scenario Analyst"
)

st.caption(
    "Describe an operational disruption in natural language. "
    "SupplyNet AI converts it into a validated scenario, "
    "reruns the deterministic optimization model, and "
    "evaluates the financial and service impact."
)


example_scenarios = [
    (
        "Increase West demand by "
        "20% in week 1"
    ),
    (
        "Reduce Dallas capacity by "
        "30% in week 1"
    ),
    (
        "SUP_001 supplier outage "
        "in week 1"
    ),
]


selected_example = st.selectbox(
    "Example scenarios",
    options=[
        "Custom scenario",
        *example_scenarios,
    ],
)


default_query = ""

if selected_example != (
    "Custom scenario"
):
    default_query = (
        selected_example
    )


scenario_query = st.text_area(
    "Describe scenario",
    value=default_query,
    placeholder=(
        "Example: Increase West demand "
        "by 20% in week 1"
    ),
    height=110,
)


if st.button(
    "Analyze Scenario",
    type="primary",
):
    if not scenario_query.strip():
        st.warning(
            "Enter a scenario first."
        )

    else:
        try:
            with st.spinner(
                "Interpreting disruption and "
                "re-optimizing the network..."
            ):
                agent_result = post_json(
                    "/agent/analyze",
                    {
                        "query": (
                            scenario_query.strip()
                        )
                    },
                )

            st.success(
                "Scenario analyzed successfully."
            )


            # ---------------------------------------------------------
            # INTERPRETED SCENARIO
            # ---------------------------------------------------------

            st.markdown(
                "#### Interpreted Scenario"
            )

            parsed = agent_result[
                "parsed_scenario"
            ]

            st.json(
                parsed
            )


            # ---------------------------------------------------------
            # COST IMPACT
            # ---------------------------------------------------------

            st.markdown(
                "#### Financial Impact"
            )

            cost_cols = st.columns(
                3
            )

            cost_cols[0].metric(
                "Baseline Cost",
                (
                    f'${agent_result["baseline_cost"]:,.0f}'
                ),
            )

            cost_cols[1].metric(
                "Scenario Cost",
                (
                    f'${agent_result["scenario_cost"]:,.0f}'
                ),
            )

            cost_cols[2].metric(
                "Cost Impact",
                (
                    f'${agent_result["cost_change"]:,.0f}'
                ),
                delta=(
                    f'{agent_result["cost_change_pct"]:.2%}'
                ),
                delta_color="inverse",
            )


            # ---------------------------------------------------------
            # SERVICE IMPACT
            # ---------------------------------------------------------

            st.markdown(
                "#### Service Impact"
            )

            service_cols = st.columns(
                3
            )

            service_cols[0].metric(
                "Baseline Fulfillment",
                (
                    f'{agent_result["baseline_fulfillment_rate"]:.2%}'
                ),
            )

            service_cols[1].metric(
                "Scenario Fulfillment",
                (
                    f'{agent_result["scenario_fulfillment_rate"]:.2%}'
                ),
            )

            service_cols[2].metric(
                "Scenario Unmet Demand",
                (
                    f'{agent_result["scenario_unmet_demand"]:,}'
                ),
            )


            # ---------------------------------------------------------
            # RECOMMENDATION
            # ---------------------------------------------------------

            st.markdown(
                "#### Recommendation"
            )

            st.info(
                agent_result[
                    "recommendation"
                ]
            )


            # ---------------------------------------------------------
            # WORKFLOW EXPLANATION
            # ---------------------------------------------------------

            with st.expander(
                "How SupplyNet AI analyzed this scenario"
            ):
                st.markdown(
                    """
                    **Decision workflow**

                    1. Natural-language scenario received
                    2. Scenario parsed into structured parameters
                    3. Parameters validated with Pydantic
                    4. Base network copied into a scenario network
                    5. Requested disruption applied
                    6. OR-Tools MILP optimizer rerun
                    7. Scenario compared with baseline optimization
                    8. Business recommendation generated

                    The agent does not calculate shipment quantities
                    itself. Shipment and routing decisions are produced
                    by the deterministic optimization engine.
                    """
                )

        except requests.HTTPError as exc:
            try:
                error_message = (
                    exc.response.json()
                    .get(
                        "detail",
                        str(exc),
                    )
                )

            except Exception:
                error_message = (
                    str(exc)
                )

            st.error(
                error_message
            )

        except Exception as exc:
            st.error(
                "Scenario analysis failed: "
                f"{exc}"
            )


st.divider()


# ---------------------------------------------------------------------
# PLANNING INSIGHT
# ---------------------------------------------------------------------


st.subheader(
    "Planning Insight"
)


savings_pct = (
    improvement[
        "cost_savings_pct"
    ]
)


if savings_pct > 0:
    st.success(
        "The optimized plan reduces total network "
        f"cost by {savings_pct:.2%} relative to the "
        "rule-based planning baseline."
    )

else:
    st.warning(
        "The optimized plan does not currently "
        "produce lower total cost than the baseline."
    )


if (
    optimized[
        "fulfillment_rate"
    ]
    >= naive[
        "fulfillment_rate"
    ]
):
    st.info(
        "Optimization maintains or improves "
        "customer fulfillment while minimizing "
        "network cost."
    )
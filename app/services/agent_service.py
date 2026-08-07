from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.models.network_data import NetworkData
from app.models.scenario import (
    AgentResponse,
    ScenarioRequest,
)
from app.services.scenario_evaluation_service import (
    ScenarioEvaluationService,
)
from app.services.scenario_parser import ScenarioParser
from app.services.scenario_service import ScenarioService


class AgentState(TypedDict, total=False):
    query: str

    parsed_scenario: ScenarioRequest

    scenario_network: NetworkData

    evaluation: dict

    recommendation: str


class SupplyNetAgent:
    """
    Agentic scenario-analysis workflow.

    Natural language
        -> structured scenario
        -> scenario application
        -> deterministic optimization
        -> recommendation
    """

    def __init__(
        self,
        network: NetworkData,
    ) -> None:
        self.network = network

        self.parser = ScenarioParser()

        self.graph = self._build_graph()

    # ------------------------------------------------------
    # GRAPH NODES
    # ------------------------------------------------------

    def _parse_scenario(
        self,
        state: AgentState,
    ) -> AgentState:
        parsed = self.parser.parse(
            state["query"]
        )

        return {
            **state,
            "parsed_scenario": parsed,
        }

    def _apply_scenario(
        self,
        state: AgentState,
    ) -> AgentState:
        scenario = state[
            "parsed_scenario"
        ]

        service = ScenarioService(
            self.network
        )

        if scenario.scenario_type == "demand_surge":
            scenario_network = service.demand_surge(
                region_id=scenario.region_id,
                week=scenario.week,
                increase_pct=scenario.percentage,
            )

        elif (
            scenario.scenario_type
            == "dc_capacity_reduction"
        ):
            scenario_network = service.reduce_dc_capacity(
                dc_id=scenario.dc_id,
                reduction_pct=scenario.percentage,
            )

        elif (
            scenario.scenario_type
            == "supplier_outage"
        ):
            scenario_network = service.supplier_outage(
                supplier_id=scenario.supplier_id,
            )

        elif (
            scenario.scenario_type
            == "supplier_capacity_reduction"
        ):
            scenario_network = (
                service.reduce_supplier_capacity(
                    supplier_id=scenario.supplier_id,
                    reduction_pct=scenario.percentage,
                )
            )

        elif (
            scenario.scenario_type
            == "inbound_cost_increase"
        ):
            scenario_network = (
                service.increase_inbound_cost(
                    supplier_id=scenario.supplier_id,
                    dc_id=scenario.dc_id,
                    increase_pct=scenario.percentage,
                )
            )

        elif (
            scenario.scenario_type
            == "disable_inbound_lane"
        ):
            scenario_network = (
                service.disable_inbound_lane(
                    supplier_id=scenario.supplier_id,
                    dc_id=scenario.dc_id,
                )
            )

        elif (
            scenario.scenario_type
            == "disable_outbound_lane"
        ):
            scenario_network = (
                service.disable_outbound_lane(
                    dc_id=scenario.dc_id,
                    region_id=scenario.region_id,
                )
            )

        else:
            raise ValueError(
                "Unsupported scenario type."
            )

        return {
            **state,
            "scenario_network": scenario_network,
        }

    def _optimize_scenario(
        self,
        state: AgentState,
    ) -> AgentState:
        scenario = state[
            "parsed_scenario"
        ]

        evaluation_service = (
            ScenarioEvaluationService(
                self.network
            )
        )

        result = (
            evaluation_service.compare_scenario(
                scenario_network=state[
                    "scenario_network"
                ],
                week=scenario.week,
            )
        )

        return {
            **state,
            "evaluation": result,
        }

    def _generate_recommendation(
        self,
        state: AgentState,
    ) -> AgentState:
        evaluation = state[
            "evaluation"
        ]

        impact = evaluation[
            "impact"
        ]

        scenario = evaluation[
            "scenario"
        ]

        cost_pct = impact[
            "cost_change_pct"
        ]

        fulfillment = scenario[
            "fulfillment_rate"
        ]

        unmet = scenario[
            "unmet_demand_pallets"
        ]

        if unmet > 0:
            recommendation = (
                f"The disruption creates {unmet:,} pallets "
                "of unmet demand. Review alternate suppliers, "
                "DC routing, or temporary capacity expansion."
            )

        elif cost_pct > 0.05:
            recommendation = (
                "Customer demand remains fully served, but "
                f"optimized network cost increases by "
                f"{cost_pct:.2%}. Review the newly selected "
                "lanes and consider alternate sourcing."
            )

        elif cost_pct > 0:
            recommendation = (
                "The network absorbs the disruption while "
                f"maintaining {fulfillment:.2%} fulfillment. "
                f"Cost increases by only {cost_pct:.2%}, so "
                "the optimized rerouting is operationally viable."
            )

        else:
            recommendation = (
                "The optimized network absorbs this scenario "
                "without increasing total cost or reducing "
                "customer fulfillment."
            )

        return {
            **state,
            "recommendation": recommendation,
        }

    # ------------------------------------------------------
    # GRAPH
    # ------------------------------------------------------

    def _build_graph(self):
        graph = StateGraph(
            AgentState
        )

        graph.add_node(
            "parse_scenario",
            self._parse_scenario,
        )

        graph.add_node(
            "apply_scenario",
            self._apply_scenario,
        )

        graph.add_node(
            "optimize",
            self._optimize_scenario,
        )

        graph.add_node(
            "recommend",
            self._generate_recommendation,
        )

        graph.set_entry_point(
            "parse_scenario"
        )

        graph.add_edge(
            "parse_scenario",
            "apply_scenario",
        )

        graph.add_edge(
            "apply_scenario",
            "optimize",
        )

        graph.add_edge(
            "optimize",
            "recommend",
        )

        graph.add_edge(
            "recommend",
            END,
        )

        return graph.compile()

    # ------------------------------------------------------
    # PUBLIC METHOD
    # ------------------------------------------------------

    def run(
        self,
        query: str,
    ) -> AgentResponse:
        state = self.graph.invoke(
            {
                "query": query,
            }
        )

        evaluation = state[
            "evaluation"
        ]

        return AgentResponse(
            user_query=query,

            parsed_scenario=state[
                "parsed_scenario"
            ],

            baseline_cost=(
                evaluation[
                    "baseline"
                ]["optimized_cost"]
            ),

            scenario_cost=(
                evaluation[
                    "scenario"
                ]["optimized_cost"]
            ),

            cost_change=(
                evaluation[
                    "impact"
                ]["cost_change"]
            ),

            cost_change_pct=(
                evaluation[
                    "impact"
                ]["cost_change_pct"]
            ),

            baseline_fulfillment_rate=(
                evaluation[
                    "baseline"
                ]["fulfillment_rate"]
            ),

            scenario_fulfillment_rate=(
                evaluation[
                    "scenario"
                ]["fulfillment_rate"]
            ),

            baseline_unmet_demand=(
                evaluation[
                    "baseline"
                ]["unmet_demand_pallets"]
            ),

            scenario_unmet_demand=(
                evaluation[
                    "scenario"
                ]["unmet_demand_pallets"]
            ),

            recommendation=state[
                "recommendation"
            ],
        )

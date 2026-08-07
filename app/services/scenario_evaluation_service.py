from __future__ import annotations

from app.models.network_data import NetworkData
from app.services.evaluation_service import EvaluationService


class ScenarioEvaluationService:
    """Compare a disrupted network against the original network."""

    def __init__(
        self,
        base_network: NetworkData,
    ) -> None:
        self.base_network = base_network

    def compare_scenario(
        self,
        scenario_network: NetworkData,
        week: int = 1,
    ) -> dict:
        base_evaluation = EvaluationService(
            self.base_network
        ).compare(
            week=week
        )

        scenario_evaluation = EvaluationService(
            scenario_network
        ).compare(
            week=week
        )

        base_cost = (
            base_evaluation["optimized"]["total_cost"]
        )

        scenario_cost = (
            scenario_evaluation[
                "optimized"
            ]["total_cost"]
        )

        base_fulfillment = (
            base_evaluation[
                "optimized"
            ]["fulfillment_rate"]
        )

        scenario_fulfillment = (
            scenario_evaluation[
                "optimized"
            ]["fulfillment_rate"]
        )

        cost_change = (
            scenario_cost - base_cost
        )

        cost_change_pct = (
            cost_change / base_cost
            if base_cost > 0
            else 0.0
        )

        fulfillment_change = (
            scenario_fulfillment
            - base_fulfillment
        )

        return {
            "week": week,

            "baseline": {
                "optimized_cost": base_cost,
                "fulfillment_rate": (
                    base_fulfillment
                ),
                "unmet_demand_pallets": (
                    base_evaluation[
                        "optimized"
                    ]["unmet_demand_pallets"]
                ),
            },

            "scenario": {
                "optimized_cost": scenario_cost,
                "fulfillment_rate": (
                    scenario_fulfillment
                ),
                "unmet_demand_pallets": (
                    scenario_evaluation[
                        "optimized"
                    ]["unmet_demand_pallets"]
                ),
            },

            "impact": {
                "cost_change": (
                    cost_change
                ),
                "cost_change_pct": (
                    cost_change_pct
                ),
                "fulfillment_rate_change": (
                    fulfillment_change
                ),
            },
        }

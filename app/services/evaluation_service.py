from __future__ import annotations

from app.models.network_data import NetworkData
from app.services.naive_planner import NaivePlanner
from app.services.optimization_service import OptimizationService


class EvaluationService:
    """Compare naive and optimized supply-network plans."""

    def __init__(self, network: NetworkData) -> None:
        self.network = network

    def compare(self, week: int = 1) -> dict:
        # --------------------------------------------------------------
        # NAIVE PLAN
        # --------------------------------------------------------------

        naive_planner = NaivePlanner(self.network)
        naive_result = naive_planner.plan(week=week)

        # --------------------------------------------------------------
        # OPTIMIZED PLAN
        # --------------------------------------------------------------

        optimizer = OptimizationService(self.network)
        optimizer.build_model(week=week)

        status = optimizer.solve()
        status_name = optimizer.get_status_name(status)

        if status_name not in {"OPTIMAL", "FEASIBLE"}:
            raise RuntimeError(
                f"Optimizer failed with status: {status_name}"
            )

        optimized_costs = optimizer.get_cost_breakdown()

        optimized_unmet = sum(
            row["unmet_demand_pallets"]
            for row in optimizer.get_unmet_demand_solution()
        )

        total_demand = sum(
            record.demand_pallets
            for record in self.network.demand
            if record.week == week
        )

        optimized_fulfilled = (
            total_demand - optimized_unmet
        )

        optimized_fulfillment_rate = (
            optimized_fulfilled / total_demand
            if total_demand > 0
            else 0.0
        )

        optimized_inbound = (
            optimizer.get_inbound_solution()
        )

        total_optimized_pallets = sum(
            row["pallets"]
            for row in optimized_inbound
        )

        total_optimized_booked_capacity = sum(
            row["booked_capacity_pallets"]
            for row in optimized_inbound
        )

        optimized_container_utilization = (
            total_optimized_pallets
            / total_optimized_booked_capacity
            if total_optimized_booked_capacity > 0
            else 0.0
        )

        # --------------------------------------------------------------
        # IMPROVEMENT METRICS
        # --------------------------------------------------------------

        cost_savings = (
            naive_result.total_cost
            - optimized_costs["total_cost"]
        )

        cost_savings_pct = (
            cost_savings / naive_result.total_cost
            if naive_result.total_cost > 0
            else 0.0
        )

        fulfillment_improvement = (
            optimized_fulfillment_rate
            - naive_result.fulfillment_rate
        )

        utilization_improvement = (
            optimized_container_utilization
            - naive_result.average_container_utilization
        )

        # --------------------------------------------------------------
        # RETURN STANDARD COMPARISON
        # --------------------------------------------------------------

        return {
            "week": week,
            "solver_status": status_name,

            "naive": {
                "total_cost": naive_result.total_cost,
                "inbound_transportation_cost": (
                    naive_result.inbound_transportation_cost
                ),
                "outbound_transportation_cost": (
                    naive_result.outbound_transportation_cost
                ),
                "handling_cost": naive_result.handling_cost,
                "holding_cost": naive_result.holding_cost,
                "shortage_cost": naive_result.shortage_cost,
                "total_demand_pallets": (
                    naive_result.total_demand_pallets
                ),
                "fulfilled_demand_pallets": (
                    naive_result.fulfilled_demand_pallets
                ),
                "unmet_demand_pallets": (
                    naive_result.unmet_demand_pallets
                ),
                "fulfillment_rate": (
                    naive_result.fulfillment_rate
                ),
                "average_container_utilization": (
                    naive_result.average_container_utilization
                ),
            },

            "optimized": {
                "total_cost": optimized_costs["total_cost"],
                "inbound_transportation_cost": (
                    optimized_costs[
                        "inbound_transportation_cost"
                    ]
                ),
                "outbound_transportation_cost": (
                    optimized_costs[
                        "outbound_transportation_cost"
                    ]
                ),
                "handling_cost": optimized_costs[
                    "handling_cost"
                ],
                "holding_cost": optimized_costs[
                    "holding_cost"
                ],
                "shortage_cost": optimized_costs[
                    "shortage_cost"
                ],
                "total_demand_pallets": total_demand,
                "fulfilled_demand_pallets": (
                    optimized_fulfilled
                ),
                "unmet_demand_pallets": (
                    optimized_unmet
                ),
                "fulfillment_rate": (
                    optimized_fulfillment_rate
                ),
                "average_container_utilization": (
                    optimized_container_utilization
                ),
            },

            "improvement": {
                "cost_savings": cost_savings,
                "cost_savings_pct": cost_savings_pct,
                "fulfillment_rate_change": (
                    fulfillment_improvement
                ),
                "container_utilization_change": (
                    utilization_improvement
                ),
            },
        }

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.services.agent_service import SupplyNetAgent
from app.services.data_loader import load_network_data
from app.services.evaluation_service import EvaluationService
from app.services.naive_planner import NaivePlanner
from app.services.optimization_service import OptimizationService


app = FastAPI(
    title="SupplyNet AI",
    description=(
        "Supply network planning, optimization, "
        "scenario simulation, and agentic decision support."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------------------


class PlanningRequest(BaseModel):
    """Request body for planning endpoints."""

    week: int = Field(
        default=1,
        ge=1,
        le=4,
    )


class AgentRequest(BaseModel):
    """Natural-language scenario analysis request."""

    query: str = Field(
        min_length=3,
        max_length=500,
    )


# ---------------------------------------------------------------------
# HEALTH
# ---------------------------------------------------------------------


@app.get("/health")
def health_check() -> dict:
    """Basic service health endpoint."""

    return {
        "status": "healthy",
        "service": "SupplyNet AI",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------
# NETWORK SUMMARY
# ---------------------------------------------------------------------


@app.get("/network")
def get_network_summary() -> dict:
    """Return basic supply-network statistics."""

    try:
        network = load_network_data()

        active_suppliers = sum(
            1
            for supplier in network.suppliers
            if supplier.is_active
        )

        available_inbound_lanes = sum(
            1
            for lane in network.inbound_lanes
            if lane.is_available
        )

        available_outbound_lanes = sum(
            1
            for lane in network.outbound_lanes
            if lane.is_available
        )

        planning_weeks = sorted(
            {
                record.week
                for record in network.demand
            }
        )

        return {
            "suppliers": len(
                network.suppliers
            ),
            "active_suppliers": (
                active_suppliers
            ),
            "distribution_centers": len(
                network.distribution_centers
            ),
            "customer_regions": len(
                network.customer_regions
            ),
            "inbound_lanes": len(
                network.inbound_lanes
            ),
            "available_inbound_lanes": (
                available_inbound_lanes
            ),
            "outbound_lanes": len(
                network.outbound_lanes
            ),
            "available_outbound_lanes": (
                available_outbound_lanes
            ),
            "planning_weeks": (
                planning_weeks
            ),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------
# NAIVE PLAN
# ---------------------------------------------------------------------


@app.post("/plan/naive")
def create_naive_plan(
    request: PlanningRequest,
) -> dict:
    """Generate the rule-based baseline plan."""

    try:
        network = load_network_data()

        planner = NaivePlanner(
            network
        )

        result = planner.plan(
            week=request.week
        )

        return result.model_dump()

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------
# OPTIMIZED PLAN
# ---------------------------------------------------------------------


@app.post("/plan/optimize")
def create_optimized_plan(
    request: PlanningRequest,
) -> dict:
    """Generate an optimized supply-network plan."""

    try:
        network = load_network_data()

        optimizer = OptimizationService(
            network
        )

        optimizer.build_model(
            week=request.week
        )

        status = optimizer.solve()

        status_name = (
            optimizer.get_status_name(
                status
            )
        )

        if status_name not in {
            "OPTIMAL",
            "FEASIBLE",
        }:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Optimization failed with "
                    f"status {status_name}."
                ),
            )

        demand_records = [
            record
            for record in network.demand
            if record.week == request.week
        ]

        total_demand = sum(
            record.demand_pallets
            for record in demand_records
        )

        unmet_by_region = (
            optimizer.get_unmet_demand_solution()
        )

        total_unmet = sum(
            row[
                "unmet_demand_pallets"
            ]
            for row in unmet_by_region
        )

        fulfilled = (
            total_demand
            - total_unmet
        )

        fulfillment_rate = (
            fulfilled / total_demand
            if total_demand > 0
            else 0.0
        )

        inbound = (
            optimizer.get_inbound_solution()
        )

        outbound = (
            optimizer.get_outbound_solution()
        )

        inventory = (
            optimizer.get_inventory_solution()
        )

        costs = (
            optimizer.get_cost_breakdown()
        )

        total_inbound_pallets = sum(
            row["pallets"]
            for row in inbound
        )

        booked_capacity = sum(
            row[
                "booked_capacity_pallets"
            ]
            for row in inbound
        )

        average_container_utilization = (
            total_inbound_pallets
            / booked_capacity
            if booked_capacity > 0
            else 0.0
        )

        return {
            "planning_method": (
                "optimized"
            ),

            "week": request.week,

            "solver_status": (
                status_name
            ),

            "objective_value": (
                optimizer.solver
                .Objective()
                .Value()
            ),

            "costs": (
                costs
            ),

            "service": {
                "total_demand_pallets": (
                    total_demand
                ),
                "fulfilled_demand_pallets": (
                    fulfilled
                ),
                "unmet_demand_pallets": (
                    total_unmet
                ),
                "fulfillment_rate": (
                    fulfillment_rate
                ),
            },

            "operations": {
                "average_container_utilization": (
                    average_container_utilization
                ),
                "active_inbound_lanes": len(
                    inbound
                ),
                "active_outbound_lanes": len(
                    outbound
                ),
            },

            "inbound_allocations": (
                inbound
            ),

            "outbound_allocations": (
                outbound
            ),

            "ending_inventory": (
                inventory
            ),

            "unmet_demand": (
                unmet_by_region
            ),
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------
# PLAN COMPARISON
# ---------------------------------------------------------------------


@app.post("/plan/compare")
def compare_plans(
    request: PlanningRequest,
) -> dict:
    """Compare naive and optimized plans."""

    try:
        network = load_network_data()

        evaluation = EvaluationService(
            network
        )

        return evaluation.compare(
            week=request.week
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------
# AGENTIC SCENARIO ANALYSIS
# ---------------------------------------------------------------------


@app.post("/agent/analyze")
def analyze_scenario(
    request: AgentRequest,
) -> dict:
    """
    Analyze a natural-language supply-network disruption.

    Example:

    Increase West demand by 20% in week 1
    """

    try:
        network = load_network_data()

        agent = SupplyNetAgent(
            network
        )

        result = agent.run(
            request.query
        )

        return result.model_dump()

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
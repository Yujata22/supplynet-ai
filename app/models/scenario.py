from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ScenarioRequest(BaseModel):
    scenario_type: Literal[
        "supplier_outage",
        "supplier_capacity_reduction",
        "dc_capacity_reduction",
        "demand_surge",
        "inbound_cost_increase",
        "disable_inbound_lane",
        "disable_outbound_lane",
    ]

    week: int = Field(default=1, ge=1, le=4)

    supplier_id: str | None = None
    dc_id: str | None = None
    region_id: str | None = None

    percentage: float | None = Field(
        default=None,
        ge=0,
    )


class AgentResponse(BaseModel):
    user_query: str

    parsed_scenario: ScenarioRequest

    baseline_cost: float
    scenario_cost: float

    cost_change: float
    cost_change_pct: float

    baseline_fulfillment_rate: float
    scenario_fulfillment_rate: float

    baseline_unmet_demand: int
    scenario_unmet_demand: int

    recommendation: str

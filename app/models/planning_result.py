from pydantic import BaseModel, Field


class InboundAllocation(BaseModel):
    supplier_id: str
    dc_id: str
    pallets: int = Field(ge=0)
    containers: int = Field(ge=0)
    transportation_cost: float = Field(ge=0)
    container_utilization: float = Field(ge=0, le=1)


class OutboundAllocation(BaseModel):
    dc_id: str
    region_id: str
    pallets: int = Field(ge=0)
    transportation_cost: float = Field(ge=0)


class PlanningResult(BaseModel):
    planning_method: str
    week: int

    inbound_allocations: list[InboundAllocation]
    outbound_allocations: list[OutboundAllocation]

    inbound_transportation_cost: float = Field(ge=0)
    outbound_transportation_cost: float = Field(ge=0)
    handling_cost: float = Field(ge=0)
    shortage_cost: float = Field(ge=0)
    total_cost: float = Field(ge=0)

    total_demand_pallets: int = Field(ge=0)
    fulfilled_demand_pallets: int = Field(ge=0)
    unmet_demand_pallets: int = Field(ge=0)

    fulfillment_rate: float = Field(ge=0, le=1)
    average_container_utilization: float = Field(ge=0, le=1)

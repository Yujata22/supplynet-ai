from pydantic import BaseModel, Field


class InboundLane(BaseModel):
    """Validated supplier-to-DC transportation lane."""

    lane_id: str = Field(min_length=1)

    supplier_id: str = Field(min_length=1)
    dc_id: str = Field(min_length=1)

    distance_miles: float = Field(ge=0)
    cost_per_container: float = Field(ge=0)

    pallets_per_container: int = Field(gt=0)
    lead_time_days: int = Field(gt=0)

    lane_reliability: float = Field(ge=0, le=1)
    is_available: bool

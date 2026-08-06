from pydantic import BaseModel, Field


class OutboundLane(BaseModel):
    """Validated DC-to-customer-region transportation lane."""

    lane_id: str = Field(min_length=1)

    dc_id: str = Field(min_length=1)
    region_id: str = Field(min_length=1)

    distance_miles: float = Field(ge=0)
    cost_per_pallet: float = Field(ge=0)

    lead_time_days: int = Field(gt=0)
    is_available: bool

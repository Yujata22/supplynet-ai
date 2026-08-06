from pydantic import BaseModel, Field


class CustomerRegion(BaseModel):
    """Validated representation of a customer demand region."""

    region_id: str = Field(min_length=1)
    region_name: str = Field(min_length=1)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    base_weekly_demand: int = Field(gt=0)
    shortage_penalty_per_pallet: float = Field(gt=0)

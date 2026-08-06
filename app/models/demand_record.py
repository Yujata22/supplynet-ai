from pydantic import BaseModel, Field


class DemandRecord(BaseModel):
    """Validated weekly demand for a customer region."""

    week: int = Field(gt=0)
    region_id: str = Field(min_length=1)
    demand_pallets: int = Field(ge=0)

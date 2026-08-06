from pydantic import BaseModel, Field, model_validator


class DistributionCenter(BaseModel):
    """Validated representation of a distribution center."""

    dc_id: str = Field(min_length=1)
    dc_name: str = Field(min_length=1)

    city: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    receiving_capacity_pallets: int = Field(gt=0)
    storage_capacity_pallets: int = Field(gt=0)

    handling_cost_per_pallet: float = Field(ge=0)
    holding_cost_per_pallet: float = Field(ge=0)

    initial_inventory_pallets: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_initial_inventory(self) -> "DistributionCenter":
        if (
            self.initial_inventory_pallets
            > self.storage_capacity_pallets
        ):
            raise ValueError(
                "Initial inventory cannot exceed storage capacity."
            )

        return self

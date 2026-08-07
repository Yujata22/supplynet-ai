from pydantic import BaseModel, Field, model_validator


class Supplier(BaseModel):
    """Validated representation of a supplier."""

    supplier_id: str = Field(min_length=1)
    supplier_name: str = Field(min_length=1)

    city: str = Field(min_length=1)
    state: str = Field(min_length=2, max_length=2)
    region: str = Field(min_length=1)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    weekly_capacity_pallets: int = Field(gt=0)
    minimum_commitment_pallets: int = Field(ge=0)

    reliability_score: float = Field(ge=0, le=1)
    is_active: bool

    @model_validator(mode="after")
    def validate_minimum_commitment(self) -> "Supplier":
        if (
            self.minimum_commitment_pallets
            > self.weekly_capacity_pallets
        ):
            raise ValueError(
                "Minimum commitment cannot exceed weekly capacity."
            )

        return self

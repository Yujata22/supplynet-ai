from pydantic import BaseModel, model_validator

from app.models.customer_region import CustomerRegion
from app.models.demand_record import DemandRecord
from app.models.distribution_center import DistributionCenter
from app.models.inbound_lane import InboundLane
from app.models.outbound_lane import OutboundLane
from app.models.supplier import Supplier


class NetworkData(BaseModel):
    """Complete validated input for the supply-network model."""

    suppliers: list[Supplier]
    distribution_centers: list[DistributionCenter]
    customer_regions: list[CustomerRegion]
    inbound_lanes: list[InboundLane]
    outbound_lanes: list[OutboundLane]
    demand: list[DemandRecord]

    @model_validator(mode="after")
    def validate_network_relationships(self) -> "NetworkData":
        supplier_ids = {
            supplier.supplier_id
            for supplier in self.suppliers
        }

        dc_ids = {
            dc.dc_id
            for dc in self.distribution_centers
        }

        region_ids = {
            region.region_id
            for region in self.customer_regions
        }

        for lane in self.inbound_lanes:
            if lane.supplier_id not in supplier_ids:
                raise ValueError(
                    f"Inbound lane {lane.lane_id} references "
                    f"unknown supplier {lane.supplier_id}."
                )

            if lane.dc_id not in dc_ids:
                raise ValueError(
                    f"Inbound lane {lane.lane_id} references "
                    f"unknown DC {lane.dc_id}."
                )

        for lane in self.outbound_lanes:
            if lane.dc_id not in dc_ids:
                raise ValueError(
                    f"Outbound lane {lane.lane_id} references "
                    f"unknown DC {lane.dc_id}."
                )

            if lane.region_id not in region_ids:
                raise ValueError(
                    f"Outbound lane {lane.lane_id} references "
                    f"unknown region {lane.region_id}."
                )

        for record in self.demand:
            if record.region_id not in region_ids:
                raise ValueError(
                    f"Demand record references unknown region "
                    f"{record.region_id}."
                )

        return self

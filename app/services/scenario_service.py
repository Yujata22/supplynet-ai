from __future__ import annotations

from copy import deepcopy

from app.models.network_data import NetworkData


class ScenarioService:
    """Apply validated operational disruptions to a supply network."""

    def __init__(self, network: NetworkData) -> None:
        self.base_network = network

    def supplier_outage(
        self,
        supplier_id: str,
    ) -> NetworkData:
        network = deepcopy(self.base_network)

        supplier_found = False

        for supplier in network.suppliers:
            if supplier.supplier_id == supplier_id:
                supplier.is_active = False
                supplier_found = True
                break

        if not supplier_found:
            raise ValueError(
                f"Supplier '{supplier_id}' was not found."
            )

        return network

    def reduce_supplier_capacity(
        self,
        supplier_id: str,
        reduction_pct: float,
    ) -> NetworkData:
        if not 0 <= reduction_pct <= 1:
            raise ValueError(
                "reduction_pct must be between 0 and 1."
            )

        network = deepcopy(self.base_network)

        supplier_found = False

        for supplier in network.suppliers:
            if supplier.supplier_id == supplier_id:
                supplier.weekly_capacity_pallets = int(
                    round(
                        supplier.weekly_capacity_pallets
                        * (1 - reduction_pct)
                    )
                )

                supplier.minimum_commitment_pallets = min(
                    supplier.minimum_commitment_pallets,
                    supplier.weekly_capacity_pallets,
                )

                supplier_found = True
                break

        if not supplier_found:
            raise ValueError(
                f"Supplier '{supplier_id}' was not found."
            )

        return network

    def reduce_dc_capacity(
        self,
        dc_id: str,
        reduction_pct: float,
    ) -> NetworkData:
        if not 0 <= reduction_pct <= 1:
            raise ValueError(
                "reduction_pct must be between 0 and 1."
            )

        network = deepcopy(self.base_network)

        dc_found = False

        for dc in network.distribution_centers:
            if dc.dc_id == dc_id:
                dc.receiving_capacity_pallets = int(
                    round(
                        dc.receiving_capacity_pallets
                        * (1 - reduction_pct)
                    )
                )

                dc.storage_capacity_pallets = int(
                    round(
                        dc.storage_capacity_pallets
                        * (1 - reduction_pct)
                    )
                )

                dc.initial_inventory_pallets = min(
                    dc.initial_inventory_pallets,
                    dc.storage_capacity_pallets,
                )

                dc_found = True
                break

        if not dc_found:
            raise ValueError(
                f"Distribution center '{dc_id}' was not found."
            )

        return network

    def demand_surge(
        self,
        region_id: str,
        week: int,
        increase_pct: float,
    ) -> NetworkData:
        if increase_pct < 0:
            raise ValueError(
                "increase_pct cannot be negative."
            )

        network = deepcopy(self.base_network)

        record_found = False

        for record in network.demand:
            if (
                record.region_id == region_id
                and record.week == week
            ):
                record.demand_pallets = int(
                    round(
                        record.demand_pallets
                        * (1 + increase_pct)
                    )
                )

                record_found = True
                break

        if not record_found:
            raise ValueError(
                "Demand record not found for "
                f"region '{region_id}', week {week}."
            )

        return network

    def increase_inbound_cost(
        self,
        supplier_id: str,
        dc_id: str,
        increase_pct: float,
    ) -> NetworkData:
        if increase_pct < 0:
            raise ValueError(
                "increase_pct cannot be negative."
            )

        network = deepcopy(self.base_network)

        lane_found = False

        for lane in network.inbound_lanes:
            if (
                lane.supplier_id == supplier_id
                and lane.dc_id == dc_id
            ):
                lane.cost_per_container *= (
                    1 + increase_pct
                )

                lane_found = True
                break

        if not lane_found:
            raise ValueError(
                "Inbound lane not found for "
                f"{supplier_id} -> {dc_id}."
            )

        return network

    def disable_inbound_lane(
        self,
        supplier_id: str,
        dc_id: str,
    ) -> NetworkData:
        network = deepcopy(self.base_network)

        lane_found = False

        for lane in network.inbound_lanes:
            if (
                lane.supplier_id == supplier_id
                and lane.dc_id == dc_id
            ):
                lane.is_available = False
                lane_found = True
                break

        if not lane_found:
            raise ValueError(
                "Inbound lane not found for "
                f"{supplier_id} -> {dc_id}."
            )

        return network

    def disable_outbound_lane(
        self,
        dc_id: str,
        region_id: str,
    ) -> NetworkData:
        network = deepcopy(self.base_network)

        lane_found = False

        for lane in network.outbound_lanes:
            if (
                lane.dc_id == dc_id
                and lane.region_id == region_id
            ):
                lane.is_available = False
                lane_found = True
                break

        if not lane_found:
            raise ValueError(
                "Outbound lane not found for "
                f"{dc_id} -> {region_id}."
            )

        return network

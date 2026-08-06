from __future__ import annotations

import math
from collections import defaultdict

from app.models.network_data import NetworkData
from app.models.planning_result import (
    InboundAllocation,
    OutboundAllocation,
    PlanningResult,
)


class NaivePlanner:
    """
    Rule-based baseline planner.

    Strategy:
    1. Assign each customer region to its cheapest available outbound DC.
    2. Calculate how many pallets each DC needs.
    3. For each DC, rank inbound lanes by nominal cost per pallet.
    4. Allocate pallets from active suppliers until DC demand/capacity is met.
    5. Round container bookings upward.
    6. Calculate costs, shortages, fulfillment, and utilization.

    This is intentionally NOT a globally optimal planner.
    It serves as the baseline for comparison with OR-Tools.
    """

    def __init__(self, network: NetworkData) -> None:
        self.network = network

    def _get_week_demand(
        self,
        week: int,
    ) -> dict[str, int]:
        """Return demand by customer region for the requested week."""

        demand_by_region: dict[str, int] = {}

        for record in self.network.demand:
            if record.week == week:
                demand_by_region[record.region_id] = (
                    record.demand_pallets
                )

        if not demand_by_region:
            raise ValueError(
                f"No demand records found for week {week}."
            )

        return demand_by_region

    def _active_suppliers(self) -> dict:
        """Return active suppliers keyed by supplier ID."""

        return {
            supplier.supplier_id: supplier
            for supplier in self.network.suppliers
            if supplier.is_active
        }

    def _available_inbound_lanes(self) -> list:
        """Return currently available supplier-to-DC lanes."""

        return [
            lane
            for lane in self.network.inbound_lanes
            if lane.is_available
        ]

    def _available_outbound_lanes(self) -> list:
        """Return currently available DC-to-region lanes."""

        return [
            lane
            for lane in self.network.outbound_lanes
            if lane.is_available
        ]

    def _assign_regions_to_cheapest_dcs(
        self,
        demand_by_region: dict[str, int],
    ) -> tuple[
        list[OutboundAllocation],
        dict[str, int],
        dict[str, int],
    ]:
        """
        Assign each customer region to its cheapest available DC.

        Returns:
        - outbound allocations
        - required pallets by DC
        - demand with no available outbound lane
        """

        outbound_allocations: list[OutboundAllocation] = []

        required_pallets_by_dc: dict[str, int] = defaultdict(int)

        unavailable_region_demand: dict[str, int] = {}

        available_lanes = self._available_outbound_lanes()

        for region_id, demand_pallets in demand_by_region.items():
            region_lanes = [
                lane
                for lane in available_lanes
                if lane.region_id == region_id
            ]

            if not region_lanes:
                unavailable_region_demand[
                    region_id
                ] = demand_pallets
                continue

            cheapest_lane = min(
                region_lanes,
                key=lambda lane: lane.cost_per_pallet,
            )

            transportation_cost = (
                demand_pallets
                * cheapest_lane.cost_per_pallet
            )

            outbound_allocations.append(
                OutboundAllocation(
                    dc_id=cheapest_lane.dc_id,
                    region_id=region_id,
                    pallets=demand_pallets,
                    transportation_cost=transportation_cost,
                )
            )

            required_pallets_by_dc[
                cheapest_lane.dc_id
            ] += demand_pallets

        return (
            outbound_allocations,
            dict(required_pallets_by_dc),
            unavailable_region_demand,
        )

    def _allocate_inbound(
        self,
        required_pallets_by_dc: dict[str, int],
    ) -> tuple[
        list[InboundAllocation],
        dict[str, int],
        dict[str, int],
    ]:
        """
        Allocate supplier pallets to DCs using cheapest nominal inbound lanes.

        Nominal inbound cost per pallet:

            cost_per_container / pallets_per_container
        """

        active_suppliers = self._active_suppliers()

        remaining_supplier_capacity = {
            supplier_id: supplier.weekly_capacity_pallets
            for supplier_id, supplier in active_suppliers.items()
        }

        dc_lookup = {
            dc.dc_id: dc
            for dc in self.network.distribution_centers
        }

        inbound_allocations: list[InboundAllocation] = []

        received_pallets_by_dc: dict[str, int] = defaultdict(int)

        remaining_need_by_dc: dict[str, int] = {}

        available_inbound_lanes = (
            self._available_inbound_lanes()
        )

        for dc_id, required_pallets in (
            required_pallets_by_dc.items()
        ):
            dc = dc_lookup[dc_id]

            maximum_receivable = min(
                required_pallets,
                dc.receiving_capacity_pallets,
            )

            dc_lanes = [
                lane
                for lane in available_inbound_lanes
                if (
                    lane.dc_id == dc_id
                    and lane.supplier_id
                    in active_suppliers
                )
            ]

            dc_lanes.sort(
                key=lambda lane: (
                    lane.cost_per_container
                    / lane.pallets_per_container
                )
            )

            remaining_dc_need = maximum_receivable

            for lane in dc_lanes:
                if remaining_dc_need <= 0:
                    break

                supplier_capacity = (
                    remaining_supplier_capacity[
                        lane.supplier_id
                    ]
                )

                if supplier_capacity <= 0:
                    continue

                pallets = min(
                    supplier_capacity,
                    remaining_dc_need,
                )

                if pallets <= 0:
                    continue

                containers = math.ceil(
                    pallets
                    / lane.pallets_per_container
                )

                booked_capacity = (
                    containers
                    * lane.pallets_per_container
                )

                container_utilization = (
                    pallets / booked_capacity
                    if booked_capacity > 0
                    else 0.0
                )

                transportation_cost = (
                    containers
                    * lane.cost_per_container
                )

                inbound_allocations.append(
                    InboundAllocation(
                        supplier_id=lane.supplier_id,
                        dc_id=lane.dc_id,
                        pallets=pallets,
                        containers=containers,
                        transportation_cost=(
                            transportation_cost
                        ),
                        container_utilization=(
                            container_utilization
                        ),
                    )
                )

                remaining_supplier_capacity[
                    lane.supplier_id
                ] -= pallets

                received_pallets_by_dc[
                    dc_id
                ] += pallets

                remaining_dc_need -= pallets

            remaining_need_by_dc[
                dc_id
            ] = max(
                0,
                required_pallets
                - received_pallets_by_dc[dc_id],
            )

        return (
            inbound_allocations,
            dict(received_pallets_by_dc),
            remaining_need_by_dc,
        )

    def plan(
        self,
        week: int = 1,
    ) -> PlanningResult:
        """Generate the naive baseline plan for a given week."""

        demand_by_region = self._get_week_demand(
            week
        )

        (
            outbound_allocations,
            required_pallets_by_dc,
            unavailable_region_demand,
        ) = self._assign_regions_to_cheapest_dcs(
            demand_by_region
        )

        (
            inbound_allocations,
            _received_pallets_by_dc,
            remaining_need_by_dc,
        ) = self._allocate_inbound(
            required_pallets_by_dc
        )

        dc_lookup = {
            dc.dc_id: dc
            for dc in self.network.distribution_centers
        }

        region_lookup = {
            region.region_id: region
            for region in self.network.customer_regions
        }

        inbound_transportation_cost = sum(
            allocation.transportation_cost
            for allocation in inbound_allocations
        )

        outbound_transportation_cost = sum(
            allocation.transportation_cost
            for allocation in outbound_allocations
        )

        handling_cost = sum(
            allocation.pallets
            * dc_lookup[
                allocation.dc_id
            ].handling_cost_per_pallet
            for allocation in inbound_allocations
        )

        total_demand = sum(
            demand_by_region.values()
        )

        unmet_due_to_inbound = sum(
            remaining_need_by_dc.values()
        )

        unmet_due_to_outbound = sum(
            unavailable_region_demand.values()
        )

        unmet_demand = (
            unmet_due_to_inbound
            + unmet_due_to_outbound
        )

        fulfilled_demand = max(
            0,
            total_demand - unmet_demand,
        )

        shortage_cost = 0.0

        # Shortage caused because a DC could not receive
        # enough inbound pallets.
        for allocation in outbound_allocations:
            dc_shortage = remaining_need_by_dc.get(
                allocation.dc_id,
                0,
            )

            if dc_shortage <= 0:
                continue

            dc_required = required_pallets_by_dc.get(
                allocation.dc_id,
                0,
            )

            if dc_required <= 0:
                continue

            shortage_share = (
                allocation.pallets
                / dc_required
            )

            regional_shortage = round(
                shortage_share
                * dc_shortage
            )

            shortage_cost += (
                regional_shortage
                * region_lookup[
                    allocation.region_id
                ].shortage_penalty_per_pallet
            )

        # Shortage caused because there was no available
        # DC-to-region lane at all.
        for (
            region_id,
            unavailable_demand,
        ) in unavailable_region_demand.items():
            shortage_cost += (
                unavailable_demand
                * region_lookup[
                    region_id
                ].shortage_penalty_per_pallet
            )

        total_containers = sum(
            allocation.containers
            for allocation in inbound_allocations
        )

        weighted_container_utilization = sum(
            allocation.container_utilization
            * allocation.containers
            for allocation in inbound_allocations
        )

        average_container_utilization = (
            weighted_container_utilization
            / total_containers
            if total_containers > 0
            else 0.0
        )

        total_cost = (
            inbound_transportation_cost
            + outbound_transportation_cost
            + handling_cost
            + shortage_cost
        )

        fulfillment_rate = (
            fulfilled_demand
            / total_demand
            if total_demand > 0
            else 0.0
        )

        return PlanningResult(
            planning_method="naive",
            week=week,
            inbound_allocations=inbound_allocations,
            outbound_allocations=outbound_allocations,
            inbound_transportation_cost=(
                inbound_transportation_cost
            ),
            outbound_transportation_cost=(
                outbound_transportation_cost
            ),
            handling_cost=handling_cost,
            shortage_cost=shortage_cost,
            total_cost=total_cost,
            total_demand_pallets=total_demand,
            fulfilled_demand_pallets=(
                fulfilled_demand
            ),
            unmet_demand_pallets=unmet_demand,
            fulfillment_rate=fulfillment_rate,
            average_container_utilization=(
                average_container_utilization
            ),
        )

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
    Rule-based baseline supply-network planner.

    Strategy:
    1. Assign each customer region to its cheapest available DC.
    2. Calculate required pallets at each DC.
    3. Use initial DC inventory first.
    4. Procure remaining demand using cheapest nominal inbound lanes.
    5. Respect supplier and DC capacity.
    6. Book whole containers.
    7. Fulfill customer-region demand sequentially.
    8. Calculate cost and service metrics.

    This planner is intentionally heuristic and does not guarantee
    a globally optimal solution.
    """

    def __init__(
        self,
        network: NetworkData,
    ) -> None:
        self.network = network

        self.suppliers = {
            supplier.supplier_id: supplier
            for supplier in network.suppliers
        }

        self.distribution_centers = {
            dc.dc_id: dc
            for dc in network.distribution_centers
        }

        self.customer_regions = {
            region.region_id: region
            for region in network.customer_regions
        }

    def _get_week_demand(
        self,
        week: int,
    ) -> dict[str, int]:
        """Return demand by region for the selected week."""

        demand_by_region: dict[str, int] = {}

        for record in self.network.demand:
            if record.week == week:
                demand_by_region[
                    record.region_id
                ] = record.demand_pallets

        if not demand_by_region:
            raise ValueError(
                f"No demand records found for week {week}."
            )

        return demand_by_region

    def _active_suppliers(
        self,
    ) -> dict:
        """Return active suppliers keyed by supplier ID."""

        return {
            supplier.supplier_id: supplier
            for supplier in self.network.suppliers
            if supplier.is_active
        }

    def _available_inbound_lanes(
        self,
    ) -> list:
        """Return available supplier-to-DC lanes."""

        return [
            lane
            for lane in self.network.inbound_lanes
            if lane.is_available
        ]

    def _available_outbound_lanes(
        self,
    ) -> list:
        """Return available DC-to-region lanes."""

        return [
            lane
            for lane in self.network.outbound_lanes
            if lane.is_available
        ]

    def _assign_regions_to_cheapest_dcs(
        self,
        demand_by_region: dict[str, int],
    ) -> tuple[
        dict[str, str],
        dict[str, int],
        dict[str, int],
    ]:
        """
        Assign every region to its cheapest available outbound DC.

        Returns:
        - region_to_dc
        - required_pallets_by_dc
        - unavailable_region_demand
        """

        region_to_dc: dict[str, str] = {}

        required_pallets_by_dc: dict[str, int] = defaultdict(int)

        unavailable_region_demand: dict[str, int] = {}

        available_lanes = (
            self._available_outbound_lanes()
        )

        for (
            region_id,
            demand_pallets,
        ) in demand_by_region.items():
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
                key=lambda lane: (
                    lane.cost_per_pallet
                ),
            )

            region_to_dc[
                region_id
            ] = cheapest_lane.dc_id

            required_pallets_by_dc[
                cheapest_lane.dc_id
            ] += demand_pallets

        return (
            region_to_dc,
            dict(required_pallets_by_dc),
            unavailable_region_demand,
        )

    def _allocate_inbound(
        self,
        required_pallets_by_dc: dict[str, int],
    ) -> tuple[
        list[InboundAllocation],
        dict[str, int],
    ]:
        """
        Allocate inbound supply using cheapest nominal container lanes.

        Nominal cost per pallet:

            cost_per_container / pallets_per_container
        """

        active_suppliers = (
            self._active_suppliers()
        )

        remaining_supplier_capacity = {
            supplier_id: (
                supplier.weekly_capacity_pallets
            )
            for supplier_id, supplier
            in active_suppliers.items()
        }

        available_inbound_lanes = (
            self._available_inbound_lanes()
        )

        inbound_allocations: list[
            InboundAllocation
        ] = []

        received_pallets_by_dc: dict[
            str,
            int,
        ] = defaultdict(int)

        for (
            dc_id,
            required_pallets,
        ) in required_pallets_by_dc.items():
            dc = self.distribution_centers[
                dc_id
            ]

            net_inbound_requirement = max(
                0,
                required_pallets
                - dc.initial_inventory_pallets,
            )

            remaining_dc_need = min(
                net_inbound_requirement,
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

            for lane in dc_lanes:
                if remaining_dc_need <= 0:
                    break

                supplier_remaining = (
                    remaining_supplier_capacity[
                        lane.supplier_id
                    ]
                )

                if supplier_remaining <= 0:
                    continue

                pallets = min(
                    supplier_remaining,
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
                        supplier_id=(
                            lane.supplier_id
                        ),
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

        return (
            inbound_allocations,
            dict(received_pallets_by_dc),
        )

    def _fulfill_customer_demand(
        self,
        demand_by_region: dict[str, int],
        region_to_dc: dict[str, str],
        unavailable_region_demand: dict[str, int],
        received_pallets_by_dc: dict[str, int],
    ) -> tuple[
        list[OutboundAllocation],
        dict[str, int],
        dict[str, int],
    ]:
        """
        Fulfill customer demand from inventory actually available at each DC.
        """

        available_inventory_by_dc = {
            dc_id: (
                dc.initial_inventory_pallets
                + received_pallets_by_dc.get(
                    dc_id,
                    0,
                )
            )
            for dc_id, dc
            in self.distribution_centers.items()
        }

        outbound_lane_lookup = {
            (
                lane.dc_id,
                lane.region_id,
            ): lane
            for lane in (
                self._available_outbound_lanes()
            )
        }

        outbound_allocations: list[
            OutboundAllocation
        ] = []

        unmet_by_region: dict[str, int] = {}

        for (
            region_id,
            unavailable_demand,
        ) in unavailable_region_demand.items():
            unmet_by_region[
                region_id
            ] = unavailable_demand

        for (
            region_id,
            demand_pallets,
        ) in demand_by_region.items():
            if region_id not in region_to_dc:
                continue

            dc_id = region_to_dc[
                region_id
            ]

            available_inventory = (
                available_inventory_by_dc[
                    dc_id
                ]
            )

            fulfilled_pallets = min(
                demand_pallets,
                available_inventory,
            )

            unmet_pallets = (
                demand_pallets
                - fulfilled_pallets
            )

            lane = outbound_lane_lookup[
                (
                    dc_id,
                    region_id,
                )
            ]

            if fulfilled_pallets > 0:
                transportation_cost = (
                    fulfilled_pallets
                    * lane.cost_per_pallet
                )

                outbound_allocations.append(
                    OutboundAllocation(
                        dc_id=dc_id,
                        region_id=region_id,
                        pallets=fulfilled_pallets,
                        transportation_cost=(
                            transportation_cost
                        ),
                    )
                )

            available_inventory_by_dc[
                dc_id
            ] -= fulfilled_pallets

            unmet_by_region[
                region_id
            ] = unmet_pallets

        return (
            outbound_allocations,
            unmet_by_region,
            available_inventory_by_dc,
        )

    def plan(
        self,
        week: int = 1,
    ) -> PlanningResult:
        """Generate the complete naive baseline plan."""

        demand_by_region = (
            self._get_week_demand(
                week
            )
        )

        (
            region_to_dc,
            required_pallets_by_dc,
            unavailable_region_demand,
        ) = self._assign_regions_to_cheapest_dcs(
            demand_by_region
        )

        (
            inbound_allocations,
            received_pallets_by_dc,
        ) = self._allocate_inbound(
            required_pallets_by_dc
        )

        (
            outbound_allocations,
            unmet_by_region,
            ending_inventory_by_dc,
        ) = self._fulfill_customer_demand(
            demand_by_region=(
                demand_by_region
            ),
            region_to_dc=(
                region_to_dc
            ),
            unavailable_region_demand=(
                unavailable_region_demand
            ),
            received_pallets_by_dc=(
                received_pallets_by_dc
            ),
        )

        # ---------------------------
        # COST CALCULATION
        # ---------------------------

        inbound_transportation_cost = sum(
            allocation.transportation_cost
            for allocation
            in inbound_allocations
        )

        outbound_transportation_cost = sum(
            allocation.transportation_cost
            for allocation
            in outbound_allocations
        )

        handling_cost = sum(
            allocation.pallets
            * self.distribution_centers[
                allocation.dc_id
            ].handling_cost_per_pallet
            for allocation
            in inbound_allocations
        )

        holding_cost = sum(
            inventory
            * self.distribution_centers[
                dc_id
            ].holding_cost_per_pallet
            for dc_id, inventory
            in ending_inventory_by_dc.items()
        )

        shortage_cost = sum(
            unmet_pallets
            * self.customer_regions[
                region_id
            ].shortage_penalty_per_pallet
            for region_id, unmet_pallets
            in unmet_by_region.items()
        )

        total_cost = (
            inbound_transportation_cost
            + outbound_transportation_cost
            + handling_cost
            + holding_cost
            + shortage_cost
        )

        # ---------------------------
        # SERVICE METRICS
        # ---------------------------

        total_demand = sum(
            demand_by_region.values()
        )

        unmet_demand = sum(
            unmet_by_region.values()
        )

        fulfilled_demand = (
            total_demand
            - unmet_demand
        )

        fulfillment_rate = (
            fulfilled_demand
            / total_demand
            if total_demand > 0
            else 0.0
        )

        # ---------------------------
        # CONTAINER UTILIZATION
        # ---------------------------

        total_booked_capacity = 0
        total_inbound_pallets = 0

        inbound_lane_lookup = {
            (
                lane.supplier_id,
                lane.dc_id,
            ): lane
            for lane in self.network.inbound_lanes
        }

        for allocation in inbound_allocations:
            lane = inbound_lane_lookup[
                (
                    allocation.supplier_id,
                    allocation.dc_id,
                )
            ]

            total_booked_capacity += (
                allocation.containers
                * lane.pallets_per_container
            )

            total_inbound_pallets += (
                allocation.pallets
            )

        average_container_utilization = (
            total_inbound_pallets
            / total_booked_capacity
            if total_booked_capacity > 0
            else 0.0
        )

        return PlanningResult(
            planning_method="naive",
            week=week,

            inbound_allocations=(
                inbound_allocations
            ),

            outbound_allocations=(
                outbound_allocations
            ),

            inbound_transportation_cost=(
                inbound_transportation_cost
            ),

            outbound_transportation_cost=(
                outbound_transportation_cost
            ),

            handling_cost=handling_cost,

            holding_cost=holding_cost,

            shortage_cost=shortage_cost,

            total_cost=total_cost,

            total_demand_pallets=(
                total_demand
            ),

            fulfilled_demand_pallets=(
                fulfilled_demand
            ),

            unmet_demand_pallets=(
                unmet_demand
            ),

            fulfillment_rate=(
                fulfillment_rate
            ),

            average_container_utilization=(
                average_container_utilization
            ),
        )
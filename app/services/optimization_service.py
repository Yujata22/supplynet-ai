from __future__ import annotations

from ortools.linear_solver import pywraplp

from app.models.network_data import NetworkData


class OptimizationService:
    """MILP optimization service for the supply network."""

    def __init__(self, network: NetworkData) -> None:
        self.network = network

        self.solver = pywraplp.Solver.CreateSolver("CBC")

        if self.solver is None:
            raise RuntimeError(
                "CBC solver could not be initialized."
            )

        # Lookup dictionaries
        self.suppliers = {
            supplier.supplier_id: supplier
            for supplier in self.network.suppliers
        }

        self.distribution_centers = {
            dc.dc_id: dc
            for dc in self.network.distribution_centers
        }

        self.customer_regions = {
            region.region_id: region
            for region in self.network.customer_regions
        }

        self.inbound_lanes = {
            (lane.supplier_id, lane.dc_id): lane
            for lane in self.network.inbound_lanes
        }

        self.outbound_lanes = {
            (lane.dc_id, lane.region_id): lane
            for lane in self.network.outbound_lanes
        }

        # Decision variables
        self.inbound_pallets = {}
        self.containers = {}
        self.outbound_pallets = {}
        self.ending_inventory = {}
        self.unmet_demand = {}

    def _create_decision_variables(
        self,
        week: int,
    ) -> None:
        """
        Create optimization decision variables.

        x[s,d] = pallets shipped from supplier s to DC d
        y[s,d] = containers booked from supplier s to DC d
        z[d,r] = pallets shipped from DC d to region r
        I[d]   = ending inventory at DC d
        u[r]   = unmet demand in region r
        """

        for lane in self.network.inbound_lanes:
            key = (
                lane.supplier_id,
                lane.dc_id,
            )

            self.inbound_pallets[key] = self.solver.IntVar(
                0,
                self.solver.infinity(),
                (
                    f"inbound_pallets_"
                    f"{lane.supplier_id}_"
                    f"{lane.dc_id}"
                ),
            )

            self.containers[key] = self.solver.IntVar(
                0,
                self.solver.infinity(),
                (
                    f"containers_"
                    f"{lane.supplier_id}_"
                    f"{lane.dc_id}"
                ),
            )

        for lane in self.network.outbound_lanes:
            key = (
                lane.dc_id,
                lane.region_id,
            )

            self.outbound_pallets[key] = self.solver.IntVar(
                0,
                self.solver.infinity(),
                (
                    f"outbound_pallets_"
                    f"{lane.dc_id}_"
                    f"{lane.region_id}"
                ),
            )

        for dc_id in self.distribution_centers:
            self.ending_inventory[dc_id] = self.solver.IntVar(
                0,
                self.solver.infinity(),
                f"ending_inventory_{dc_id}",
            )

        for region_id in self.customer_regions:
            self.unmet_demand[region_id] = self.solver.IntVar(
                0,
                self.solver.infinity(),
                f"unmet_demand_{region_id}",
            )

    def _add_supplier_capacity_constraints(
        self,
    ) -> None:
        """
        Supplier capacity constraint.

        sum(d) x[s,d] <= supplier_capacity[s]
        """

        for supplier_id, supplier in self.suppliers.items():
            outbound_from_supplier = []

            for dc_id in self.distribution_centers:
                key = (
                    supplier_id,
                    dc_id,
                )

                if key in self.inbound_pallets:
                    outbound_from_supplier.append(
                        self.inbound_pallets[key]
                    )

            self.solver.Add(
                self.solver.Sum(
                    outbound_from_supplier
                )
                <= supplier.weekly_capacity_pallets
            )

    def _add_container_capacity_constraints(
        self,
    ) -> None:
        """
        Container capacity constraint.

        x[s,d]
        <=
        pallets_per_container[s,d] * y[s,d]
        """

        for key, lane in self.inbound_lanes.items():
            self.solver.Add(
                self.inbound_pallets[key]
                <= (
                    lane.pallets_per_container
                    * self.containers[key]
                )
            )

    def _add_lane_availability_constraints(
        self,
    ) -> None:
        """Force flows to zero for unavailable lanes."""

        for key, lane in self.inbound_lanes.items():
            if not lane.is_available:
                self.solver.Add(
                    self.inbound_pallets[key] == 0
                )

                self.solver.Add(
                    self.containers[key] == 0
                )

        for key, lane in self.outbound_lanes.items():
            if not lane.is_available:
                self.solver.Add(
                    self.outbound_pallets[key] == 0
                )

    def _add_dc_receiving_capacity_constraints(
        self,
    ) -> None:
        """
        DC receiving capacity.

        sum(s) x[s,d]
        <=
        receiving_capacity[d]
        """

        for dc_id, dc in self.distribution_centers.items():
            inbound_to_dc = []

            for supplier_id in self.suppliers:
                key = (
                    supplier_id,
                    dc_id,
                )

                if key in self.inbound_pallets:
                    inbound_to_dc.append(
                        self.inbound_pallets[key]
                    )

            self.solver.Add(
                self.solver.Sum(
                    inbound_to_dc
                )
                <= dc.receiving_capacity_pallets
            )

    def _add_dc_flow_balance_constraints(
        self,
    ) -> None:
        """
        DC flow balance.

        initial_inventory[d]
        + sum(s) x[s,d]
        =
        sum(r) z[d,r]
        + ending_inventory[d]
        """

        for dc_id, dc in self.distribution_centers.items():
            inbound_to_dc = []

            for supplier_id in self.suppliers:
                key = (
                    supplier_id,
                    dc_id,
                )

                if key in self.inbound_pallets:
                    inbound_to_dc.append(
                        self.inbound_pallets[key]
                    )

            outbound_from_dc = []

            for region_id in self.customer_regions:
                key = (
                    dc_id,
                    region_id,
                )

                if key in self.outbound_pallets:
                    outbound_from_dc.append(
                        self.outbound_pallets[key]
                    )

            self.solver.Add(
                dc.initial_inventory_pallets
                + self.solver.Sum(
                    inbound_to_dc
                )
                ==
                self.solver.Sum(
                    outbound_from_dc
                )
                + self.ending_inventory[dc_id]
            )

    def _add_dc_storage_capacity_constraints(
        self,
    ) -> None:
        """
        Ending inventory constraint.

        ending_inventory[d]
        <=
        storage_capacity[d]
        """

        for dc_id, dc in self.distribution_centers.items():
            self.solver.Add(
                self.ending_inventory[dc_id]
                <= dc.storage_capacity_pallets
            )

    def _add_demand_balance_constraints(
        self,
        week: int,
    ) -> None:
        """
        Regional demand balance.

        sum(d) z[d,r]
        + unmet_demand[r]
        =
        demand[r]
        """

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

        missing_regions = (
            set(self.customer_regions)
            - set(demand_by_region)
        )

        if missing_regions:
            raise ValueError(
                "Missing demand records for regions: "
                + ", ".join(sorted(missing_regions))
            )

        for region_id in self.customer_regions:
            outbound_to_region = []

            for dc_id in self.distribution_centers:
                key = (
                    dc_id,
                    region_id,
                )

                if key in self.outbound_pallets:
                    outbound_to_region.append(
                        self.outbound_pallets[key]
                    )

            self.solver.Add(
                self.solver.Sum(
                    outbound_to_region
                )
                + self.unmet_demand[region_id]
                ==
                demand_by_region[region_id]
            )

    def _set_objective(
        self,
    ) -> None:
        """
        Minimize total network cost.

        Total cost =
        inbound container transportation
        + outbound pallet transportation
        + DC handling
        + inventory holding
        + shortage penalties
        """

        inbound_transportation_cost = self.solver.Sum(
            lane.cost_per_container
            * self.containers[key]
            for key, lane in self.inbound_lanes.items()
        )

        outbound_transportation_cost = self.solver.Sum(
            lane.cost_per_pallet
            * self.outbound_pallets[key]
            for key, lane in self.outbound_lanes.items()
        )

        handling_cost = self.solver.Sum(
            self.distribution_centers[
                dc_id
            ].handling_cost_per_pallet
            * variable
            for (
                _supplier_id,
                dc_id,
            ), variable in self.inbound_pallets.items()
        )

        holding_cost = self.solver.Sum(
            self.distribution_centers[
                dc_id
            ].holding_cost_per_pallet
            * self.ending_inventory[dc_id]
            for dc_id in self.distribution_centers
        )

        shortage_cost = self.solver.Sum(
            self.customer_regions[
                region_id
            ].shortage_penalty_per_pallet
            * self.unmet_demand[region_id]
            for region_id in self.customer_regions
        )

        total_cost = (
            inbound_transportation_cost
            + outbound_transportation_cost
            + handling_cost
            + holding_cost
            + shortage_cost
        )

        self.solver.Minimize(
            total_cost
        )

    def build_model(
        self,
        week: int = 1,
    ) -> None:
        """Build the complete MILP model."""

        self._create_decision_variables(
            week=week
        )

        self._add_supplier_capacity_constraints()

        self._add_container_capacity_constraints()

        self._add_lane_availability_constraints()

        self._add_dc_receiving_capacity_constraints()

        self._add_dc_flow_balance_constraints()

        self._add_dc_storage_capacity_constraints()

        self._add_demand_balance_constraints(
            week=week
        )

        self._set_objective()

    def solve(
        self,
    ) -> int:
        """Run CBC and return solver status."""

        return self.solver.Solve()

    def get_status_name(
        self,
        status: int,
    ) -> str:
        """Convert OR-Tools status code into readable text."""

        status_map = {
            pywraplp.Solver.OPTIMAL: "OPTIMAL",
            pywraplp.Solver.FEASIBLE: "FEASIBLE",
            pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
            pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
            pywraplp.Solver.ABNORMAL: "ABNORMAL",
            pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
        }

        return status_map.get(
            status,
            f"UNKNOWN_STATUS_{status}",
        )

    def get_inbound_solution(
        self,
    ) -> list[dict]:
        """Return non-zero optimized supplier-to-DC allocations."""

        results = []

        for key, pallet_variable in self.inbound_pallets.items():
            supplier_id, dc_id = key

            pallets = int(
                round(
                    pallet_variable.solution_value()
                )
            )

            containers = int(
                round(
                    self.containers[key].solution_value()
                )
            )

            if pallets <= 0 and containers <= 0:
                continue

            lane = self.inbound_lanes[key]

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

            results.append(
                {
                    "supplier_id": supplier_id,
                    "dc_id": dc_id,
                    "pallets": pallets,
                    "containers": containers,
                    "pallets_per_container": (
                        lane.pallets_per_container
                    ),
                    "booked_capacity_pallets": (
                        booked_capacity
                    ),
                    "container_utilization": (
                        container_utilization
                    ),
                    "cost_per_container": (
                        lane.cost_per_container
                    ),
                    "transportation_cost": (
                        transportation_cost
                    ),
                }
            )

        return results

    def get_outbound_solution(
        self,
    ) -> list[dict]:
        """Return non-zero optimized DC-to-region allocations."""

        results = []

        for key, variable in self.outbound_pallets.items():
            dc_id, region_id = key

            pallets = int(
                round(
                    variable.solution_value()
                )
            )

            if pallets <= 0:
                continue

            lane = self.outbound_lanes[key]

            transportation_cost = (
                pallets
                * lane.cost_per_pallet
            )

            results.append(
                {
                    "dc_id": dc_id,
                    "region_id": region_id,
                    "pallets": pallets,
                    "cost_per_pallet": (
                        lane.cost_per_pallet
                    ),
                    "transportation_cost": (
                        transportation_cost
                    ),
                }
            )

        return results

    def get_inventory_solution(
        self,
    ) -> list[dict]:
        """Return ending inventory by DC."""

        results = []

        for dc_id, variable in self.ending_inventory.items():
            inventory = int(
                round(
                    variable.solution_value()
                )
            )

            results.append(
                {
                    "dc_id": dc_id,
                    "ending_inventory_pallets": (
                        inventory
                    ),
                }
            )

        return results

    def get_unmet_demand_solution(
        self,
    ) -> list[dict]:
        """Return unmet demand by region."""

        results = []

        for region_id, variable in self.unmet_demand.items():
            unmet = int(
                round(
                    variable.solution_value()
                )
            )

            results.append(
                {
                    "region_id": region_id,
                    "unmet_demand_pallets": unmet,
                }
            )

        return results

    def get_cost_breakdown(
        self,
    ) -> dict[str, float]:
        """Return the optimized network cost components."""

        inbound_transportation_cost = 0.0

        for key, lane in self.inbound_lanes.items():
            containers = (
                self.containers[key].solution_value()
            )

            inbound_transportation_cost += (
                containers
                * lane.cost_per_container
            )

        outbound_transportation_cost = 0.0

        for key, lane in self.outbound_lanes.items():
            pallets = (
                self.outbound_pallets[key].solution_value()
            )

            outbound_transportation_cost += (
                pallets
                * lane.cost_per_pallet
            )

        handling_cost = 0.0

        for (
            _supplier_id,
            dc_id,
        ), variable in self.inbound_pallets.items():
            pallets = variable.solution_value()

            handling_cost += (
                pallets
                * self.distribution_centers[
                    dc_id
                ].handling_cost_per_pallet
            )

        holding_cost = 0.0

        for (
            dc_id,
            variable,
        ) in self.ending_inventory.items():
            inventory = variable.solution_value()

            holding_cost += (
                inventory
                * self.distribution_centers[
                    dc_id
                ].holding_cost_per_pallet
            )

        shortage_cost = 0.0

        for (
            region_id,
            variable,
        ) in self.unmet_demand.items():
            unmet = variable.solution_value()

            shortage_cost += (
                unmet
                * self.customer_regions[
                    region_id
                ].shortage_penalty_per_pallet
            )

        total_cost = (
            inbound_transportation_cost
            + outbound_transportation_cost
            + handling_cost
            + holding_cost
            + shortage_cost
        )

        return {
            "inbound_transportation_cost": (
                inbound_transportation_cost
            ),
            "outbound_transportation_cost": (
                outbound_transportation_cost
            ),
            "handling_cost": handling_cost,
            "holding_cost": holding_cost,
            "shortage_cost": shortage_cost,
            "total_cost": total_cost,
        }
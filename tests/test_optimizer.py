from ortools.linear_solver import pywraplp

from app.services.data_loader import load_network_data
from app.services.optimization_service import OptimizationService


def build_and_solve(week: int = 1):
    network = load_network_data()

    optimizer = OptimizationService(network)
    optimizer.build_model(week=week)

    status = optimizer.solve()

    return network, optimizer, status


def test_optimizer_returns_solution():
    _, _, status = build_and_solve()

    assert status in {
        pywraplp.Solver.OPTIMAL,
        pywraplp.Solver.FEASIBLE,
    }


def test_supplier_capacity_respected():
    network, optimizer, _ = build_and_solve()

    supplier_capacity = {
        supplier.supplier_id: supplier.weekly_capacity_pallets
        for supplier in network.suppliers
    }

    shipped = {
        supplier_id: 0
        for supplier_id in supplier_capacity
    }

    for (
        supplier_id,
        _dc_id,
    ), variable in optimizer.inbound_pallets.items():
        shipped[supplier_id] += int(
            round(variable.solution_value())
        )

    for supplier_id, pallets in shipped.items():
        assert (
            pallets
            <= supplier_capacity[supplier_id]
        )


def test_container_capacity_respected():
    _, optimizer, _ = build_and_solve()

    for key, lane in optimizer.inbound_lanes.items():
        pallets = optimizer.inbound_pallets[
            key
        ].solution_value()

        containers = optimizer.containers[
            key
        ].solution_value()

        assert pallets <= (
            containers
            * lane.pallets_per_container
            + 1e-6
        )


def test_dc_receiving_capacity_respected():
    network, optimizer, _ = build_and_solve()

    for dc in network.distribution_centers:
        inbound = sum(
            optimizer.inbound_pallets[
                (
                    supplier.supplier_id,
                    dc.dc_id,
                )
            ].solution_value()
            for supplier in network.suppliers
        )

        assert (
            inbound
            <= dc.receiving_capacity_pallets
            + 1e-6
        )


def test_dc_flow_balance():
    network, optimizer, _ = build_and_solve()

    for dc in network.distribution_centers:
        inbound = sum(
            optimizer.inbound_pallets[
                (
                    supplier.supplier_id,
                    dc.dc_id,
                )
            ].solution_value()
            for supplier in network.suppliers
        )

        outbound = sum(
            optimizer.outbound_pallets[
                (
                    dc.dc_id,
                    region.region_id,
                )
            ].solution_value()
            for region in network.customer_regions
        )

        ending_inventory = (
            optimizer.ending_inventory[
                dc.dc_id
            ].solution_value()
        )

        lhs = (
            dc.initial_inventory_pallets
            + inbound
        )

        rhs = (
            outbound
            + ending_inventory
        )

        assert abs(lhs - rhs) <= 1e-6


def test_demand_balance():
    network, optimizer, _ = build_and_solve(
        week=1
    )

    demand = {
        record.region_id: record.demand_pallets
        for record in network.demand
        if record.week == 1
    }

    for region in network.customer_regions:
        outbound = sum(
            optimizer.outbound_pallets[
                (
                    dc.dc_id,
                    region.region_id,
                )
            ].solution_value()
            for dc in network.distribution_centers
        )

        unmet = optimizer.unmet_demand[
            region.region_id
        ].solution_value()

        assert abs(
            outbound
            + unmet
            - demand[region.region_id]
        ) <= 1e-6


def test_unavailable_inbound_lanes_unused():
    network, optimizer, _ = build_and_solve()

    for lane in network.inbound_lanes:
        if lane.is_available:
            continue

        key = (
            lane.supplier_id,
            lane.dc_id,
        )

        assert (
            optimizer.inbound_pallets[
                key
            ].solution_value()
            == 0
        )

        assert (
            optimizer.containers[
                key
            ].solution_value()
            == 0
        )


def test_unavailable_outbound_lanes_unused():
    network, optimizer, _ = build_and_solve()

    for lane in network.outbound_lanes:
        if lane.is_available:
            continue

        key = (
            lane.dc_id,
            lane.region_id,
        )

        assert (
            optimizer.outbound_pallets[
                key
            ].solution_value()
            == 0
        )

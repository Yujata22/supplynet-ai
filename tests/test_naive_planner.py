from app.services.data_loader import load_network_data
from app.services.naive_planner import NaivePlanner


def test_naive_planner_runs_for_week_1() -> None:
    network = load_network_data()
    planner = NaivePlanner(network)

    result = planner.plan(week=1)

    assert result.planning_method == "naive"
    assert result.week == 1
    assert result.total_demand_pallets > 0
    assert result.total_cost > 0


def test_fulfillment_metrics_are_valid() -> None:
    network = load_network_data()
    planner = NaivePlanner(network)

    result = planner.plan(week=1)

    assert result.fulfilled_demand_pallets >= 0
    assert result.unmet_demand_pallets >= 0

    assert (
        result.fulfilled_demand_pallets
        + result.unmet_demand_pallets
        == result.total_demand_pallets
    )

    assert 0 <= result.fulfillment_rate <= 1


def test_container_utilization_is_valid() -> None:
    network = load_network_data()
    planner = NaivePlanner(network)

    result = planner.plan(week=1)

    assert 0 <= result.average_container_utilization <= 1

    for allocation in result.inbound_allocations:
        assert allocation.pallets >= 0
        assert allocation.containers >= 0
        assert 0 <= allocation.container_utilization <= 1


def test_container_capacity_is_not_exceeded() -> None:
    network = load_network_data()
    planner = NaivePlanner(network)

    result = planner.plan(week=1)

    lane_lookup = {
        (lane.supplier_id, lane.dc_id): lane
        for lane in network.inbound_lanes
    }

    for allocation in result.inbound_allocations:
        lane = lane_lookup[
            (
                allocation.supplier_id,
                allocation.dc_id,
            )
        ]

        available_container_capacity = (
            allocation.containers
            * lane.pallets_per_container
        )

        assert (
            allocation.pallets
            <= available_container_capacity
        )


def test_supplier_capacity_is_not_exceeded() -> None:
    network = load_network_data()
    planner = NaivePlanner(network)

    result = planner.plan(week=1)

    allocated_by_supplier: dict[str, int] = {}

    for allocation in result.inbound_allocations:
        allocated_by_supplier[
            allocation.supplier_id
        ] = (
            allocated_by_supplier.get(
                allocation.supplier_id,
                0,
            )
            + allocation.pallets
        )

    supplier_lookup = {
        supplier.supplier_id: supplier
        for supplier in network.suppliers
    }

    for supplier_id, allocated in allocated_by_supplier.items():
        assert (
            allocated
            <= supplier_lookup[
                supplier_id
            ].weekly_capacity_pallets
        )


def test_inbound_allocations_use_available_lanes() -> None:
    network = load_network_data()
    planner = NaivePlanner(network)

    result = planner.plan(week=1)

    lane_lookup = {
        (lane.supplier_id, lane.dc_id): lane
        for lane in network.inbound_lanes
    }

    for allocation in result.inbound_allocations:
        lane = lane_lookup[
            (
                allocation.supplier_id,
                allocation.dc_id,
            )
        ]

        assert lane.is_available is True


def test_outbound_allocations_use_available_lanes() -> None:
    network = load_network_data()
    planner = NaivePlanner(network)

    result = planner.plan(week=1)

    lane_lookup = {
        (lane.dc_id, lane.region_id): lane
        for lane in network.outbound_lanes
    }

    for allocation in result.outbound_allocations:
        lane = lane_lookup[
            (
                allocation.dc_id,
                allocation.region_id,
            )
        ]

        assert lane.is_available is True

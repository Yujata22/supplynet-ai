import pytest
from pydantic import ValidationError

from app.models.supplier import Supplier
from app.services.data_loader import load_network_data


def test_network_data_loads_successfully() -> None:
    network = load_network_data()

    assert len(network.suppliers) == 25
    assert len(network.distribution_centers) == 4
    assert len(network.customer_regions) == 8
    assert len(network.inbound_lanes) == 100
    assert len(network.outbound_lanes) == 32
    assert len(network.demand) == 32


def test_all_supplier_ids_are_unique() -> None:
    network = load_network_data()

    supplier_ids = [
        supplier.supplier_id
        for supplier in network.suppliers
    ]

    assert len(supplier_ids) == len(set(supplier_ids))


def test_all_inbound_lanes_reference_valid_entities() -> None:
    network = load_network_data()

    supplier_ids = {
        supplier.supplier_id
        for supplier in network.suppliers
    }

    dc_ids = {
        dc.dc_id
        for dc in network.distribution_centers
    }

    for lane in network.inbound_lanes:
        assert lane.supplier_id in supplier_ids
        assert lane.dc_id in dc_ids


def test_all_outbound_lanes_reference_valid_entities() -> None:
    network = load_network_data()

    dc_ids = {
        dc.dc_id
        for dc in network.distribution_centers
    }

    region_ids = {
        region.region_id
        for region in network.customer_regions
    }

    for lane in network.outbound_lanes:
        assert lane.dc_id in dc_ids
        assert lane.region_id in region_ids


def test_supplier_minimum_commitment_cannot_exceed_capacity() -> None:
    with pytest.raises(ValidationError):
        Supplier(
            supplier_id="SUP_TEST",
            supplier_name="Test Supplier",
            city="Chicago",
            state="IL",
            region="Midwest",
            latitude=41.8781,
            longitude=-87.6298,
            weekly_capacity_pallets=100,
            minimum_commitment_pallets=150,
            reliability_score=0.95,
            is_active=True,
        )
def test_active_supply_covers_peak_weekly_demand() -> None:
    network = load_network_data()

    active_supply = sum(
        supplier.weekly_capacity_pallets
        for supplier in network.suppliers
        if supplier.is_active
    )

    demand_by_week: dict[int, int] = {}

    for record in network.demand:
        demand_by_week[record.week] = (
            demand_by_week.get(record.week, 0)
            + record.demand_pallets
        )

    peak_demand = max(demand_by_week.values())

    assert active_supply >= peak_demand

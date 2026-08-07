import pytest

from app.services.agent_service import SupplyNetAgent
from app.services.data_loader import load_network_data
from app.services.scenario_parser import ScenarioParser


def test_parse_demand_surge():
    parser = ScenarioParser()

    result = parser.parse(
        "Increase West demand by 20% in week 1"
    )

    assert result.scenario_type == "demand_surge"
    assert result.region_id == "REG_WEST"
    assert result.week == 1
    assert result.percentage == pytest.approx(
        0.20
    )


def test_parse_dc_capacity_reduction():
    parser = ScenarioParser()

    result = parser.parse(
        "Reduce Dallas capacity by 30% in week 1"
    )

    assert (
        result.scenario_type
        == "dc_capacity_reduction"
    )

    assert result.dc_id == "DC_DAL"

    assert result.percentage == pytest.approx(
        0.30
    )


def test_parse_supplier_outage():
    parser = ScenarioParser()

    result = parser.parse(
        "SUP_001 supplier outage in week 1"
    )

    assert (
        result.scenario_type
        == "supplier_outage"
    )

    assert result.supplier_id == "SUP_001"


def test_invalid_scenario_rejected():
    parser = ScenarioParser()

    with pytest.raises(ValueError):
        parser.parse(
            "Something unusual happened"
        )


def test_agent_runs_demand_scenario():
    network = load_network_data()

    agent = SupplyNetAgent(network)

    result = agent.run(
        "Increase West demand by 20% in week 1"
    )

    assert (
        result.parsed_scenario.scenario_type
        == "demand_surge"
    )

    assert result.baseline_cost > 0
    assert result.scenario_cost > 0

    assert (
        0
        <= result.scenario_fulfillment_rate
        <= 1
    )

    assert result.scenario_unmet_demand >= 0

    assert result.recommendation


def test_agent_preserves_base_network():
    network = load_network_data()

    original_demand = {
        (
            record.week,
            record.region_id,
        ): record.demand_pallets
        for record in network.demand
    }

    agent = SupplyNetAgent(network)

    agent.run(
        "Increase West demand by 20% in week 1"
    )

    after_demand = {
        (
            record.week,
            record.region_id,
        ): record.demand_pallets
        for record in network.demand
    }

    assert after_demand == original_demand

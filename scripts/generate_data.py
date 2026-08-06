from __future__ import annotations

import math
import random
from pathlib import Path

import pandas as pd


RANDOM_SEED = 42

NUMBER_OF_SUPPLIERS = 25
NUMBER_OF_WEEKS = 4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

SUPPLIER_LOCATIONS = [
    ("Seattle", "WA", "West", 47.6062, -122.3321),
    ("Portland", "OR", "West", 45.5152, -122.6784),
    ("Sacramento", "CA", "West", 38.5816, -121.4944),
    ("Phoenix", "AZ", "Southwest", 33.4484, -112.0740),
    ("Denver", "CO", "Mountain", 39.7392, -104.9903),
    ("Dallas", "TX", "South", 32.7767, -96.7970),
    ("Houston", "TX", "South", 29.7604, -95.3698),
    ("Kansas City", "MO", "Midwest", 39.0997, -94.5786),
    ("Minneapolis", "MN", "Midwest", 44.9778, -93.2650),
    ("Chicago", "IL", "Midwest", 41.8781, -87.6298),
    ("Detroit", "MI", "Midwest", 42.3314, -83.0458),
    ("Columbus", "OH", "Midwest", 39.9612, -82.9988),
    ("Nashville", "TN", "South", 36.1627, -86.7816),
    ("Atlanta", "GA", "Southeast", 33.7490, -84.3880),
    ("Charlotte", "NC", "Southeast", 35.2271, -80.8431),
    ("Miami", "FL", "Southeast", 25.7617, -80.1918),
    ("Richmond", "VA", "East", 37.5407, -77.4360),
    ("Philadelphia", "PA", "East", 39.9526, -75.1652),
    ("Pittsburgh", "PA", "East", 40.4406, -79.9959),
    ("Boston", "MA", "Northeast", 42.3601, -71.0589),
]

DISTRIBUTION_CENTERS = [
    {
        "dc_id": "DC_LA",
        "dc_name": "Los Angeles Distribution Center",
        "city": "Los Angeles",
        "state": "CA",
        "latitude": 34.0522,
        "longitude": -118.2437,
        "receiving_capacity_pallets": 3200,
        "storage_capacity_pallets": 5000,
        "handling_cost_per_pallet": 18.0,
        "holding_cost_per_pallet": 4.0,
        "initial_inventory_pallets": 500,
    },
    {
        "dc_id": "DC_DAL",
        "dc_name": "Dallas Distribution Center",
        "city": "Dallas",
        "state": "TX",
        "latitude": 32.7767,
        "longitude": -96.7970,
        "receiving_capacity_pallets": 3000,
        "storage_capacity_pallets": 4800,
        "handling_cost_per_pallet": 16.0,
        "holding_cost_per_pallet": 3.5,
        "initial_inventory_pallets": 450,
    },
    {
        "dc_id": "DC_CHI",
        "dc_name": "Chicago Distribution Center",
        "city": "Chicago",
        "state": "IL",
        "latitude": 41.8781,
        "longitude": -87.6298,
        "receiving_capacity_pallets": 3000,
        "storage_capacity_pallets": 4700,
        "handling_cost_per_pallet": 17.0,
        "holding_cost_per_pallet": 3.75,
        "initial_inventory_pallets": 400,
    },
    {
        "dc_id": "DC_NY",
        "dc_name": "New York Distribution Center",
        "city": "New York",
        "state": "NY",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "receiving_capacity_pallets": 3300,
        "storage_capacity_pallets": 5200,
        "handling_cost_per_pallet": 20.0,
        "holding_cost_per_pallet": 4.5,
        "initial_inventory_pallets": 550,
    },
]
CUSTOMER_REGIONS = [
    {
        "region_id": "REG_PNW",
        "region_name": "Pacific Northwest",
        "latitude": 47.5,
        "longitude": -122.0,
        "base_weekly_demand": 950,
        "shortage_penalty_per_pallet": 500.0,
    },
    {
        "region_id": "REG_WEST",
        "region_name": "West",
        "latitude": 34.5,
        "longitude": -118.0,
        "base_weekly_demand": 1450,
        "shortage_penalty_per_pallet": 550.0,
    },
    {
        "region_id": "REG_SW",
        "region_name": "Southwest",
        "latitude": 33.5,
        "longitude": -112.0,
        "base_weekly_demand": 900,
        "shortage_penalty_per_pallet": 500.0,
    },
    {
        "region_id": "REG_MW",
        "region_name": "Midwest",
        "latitude": 41.5,
        "longitude": -88.0,
        "base_weekly_demand": 1350,
        "shortage_penalty_per_pallet": 525.0,
    },
    {
        "region_id": "REG_SOUTH",
        "region_name": "South",
        "latitude": 32.8,
        "longitude": -97.0,
        "base_weekly_demand": 1250,
        "shortage_penalty_per_pallet": 525.0,
    },
    {
        "region_id": "REG_SE",
        "region_name": "Southeast",
        "latitude": 33.7,
        "longitude": -84.4,
        "base_weekly_demand": 1150,
        "shortage_penalty_per_pallet": 525.0,
    },
    {
        "region_id": "REG_MA",
        "region_name": "Mid-Atlantic",
        "latitude": 39.0,
        "longitude": -77.0,
        "base_weekly_demand": 1050,
        "shortage_penalty_per_pallet": 550.0,
    },
    {
        "region_id": "REG_NE",
        "region_name": "Northeast",
        "latitude": 42.0,
        "longitude": -72.0,
        "base_weekly_demand": 1400,
        "shortage_penalty_per_pallet": 600.0,
    },
]
def haversine_distance_miles(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """Calculate approximate straight-line distance between two points."""

    earth_radius_miles = 3958.8

    lat_1 = math.radians(latitude_1)
    lon_1 = math.radians(longitude_1)
    lat_2 = math.radians(latitude_2)
    lon_2 = math.radians(longitude_2)

    delta_latitude = lat_2 - lat_1
    delta_longitude = lon_2 - lon_1

    a = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(lat_1)
        * math.cos(lat_2)
        * math.sin(delta_longitude / 2) ** 2
    )

    central_angle = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a),
    )

    return earth_radius_miles * central_angle
def generate_suppliers() -> pd.DataFrame:
    """Generate synthetic supplier records."""

    rows: list[dict] = []

    for supplier_number in range(1, NUMBER_OF_SUPPLIERS + 1):
        city, state, region, latitude, longitude = random.choice(
            SUPPLIER_LOCATIONS
        )

        weekly_capacity = random.randint(350, 650)

        minimum_commitment = random.randint(
            0,
            int(weekly_capacity * 0.15),
        )

        rows.append(
            {
                "supplier_id": f"SUP_{supplier_number:03d}",
                "supplier_name": f"Supplier {supplier_number:03d}",
                "city": city,
                "state": state,
                "region": region,
                "latitude": latitude,
                "longitude": longitude,
                "weekly_capacity_pallets": weekly_capacity,
                "minimum_commitment_pallets": minimum_commitment,
                "reliability_score": round(
                    random.uniform(0.86, 0.99),
                    3,
                ),
                "is_active": random.random() > 0.04,
            }
        )

    return pd.DataFrame(rows)
def calculate_container_cost(distance_miles: float) -> float:
    """Calculate a synthetic transportation cost per container."""

    fixed_booking_cost = 700.0
    variable_cost_per_mile = random.uniform(1.65, 2.10)
    market_adjustment = random.uniform(0.92, 1.12)

    total_cost = (
        fixed_booking_cost
        + distance_miles * variable_cost_per_mile
    ) * market_adjustment

    return round(total_cost, 2)
def generate_inbound_lanes(
    suppliers: pd.DataFrame,
    distribution_centers: pd.DataFrame,
) -> pd.DataFrame:
    """Generate supplier-to-DC transportation lanes."""

    rows: list[dict] = []

    for supplier in suppliers.to_dict(orient="records"):
        for dc in distribution_centers.to_dict(orient="records"):
            straight_line_distance = haversine_distance_miles(
                supplier["latitude"],
                supplier["longitude"],
                dc["latitude"],
                dc["longitude"],
            )

            road_distance = straight_line_distance * random.uniform(
                1.08,
                1.22,
            )

            pallets_per_container = random.choice(
                [20, 22, 24, 26]
            )

            lead_time_days = max(
                1,
                math.ceil(road_distance / 500),
            )

            rows.append(
                {
                    "lane_id": (
                        f'{supplier["supplier_id"]}_{dc["dc_id"]}'
                    ),
                    "supplier_id": supplier["supplier_id"],
                    "dc_id": dc["dc_id"],
                    "distance_miles": round(road_distance, 1),
                    "cost_per_container": calculate_container_cost(
                        road_distance
                    ),
                    "pallets_per_container": pallets_per_container,
                    "lead_time_days": lead_time_days,
                    "lane_reliability": round(
                        random.uniform(0.85, 0.99),
                        3,
                    ),
                    "is_available": random.random() > 0.02,
                }
            )

    return pd.DataFrame(rows)
def generate_outbound_lanes(
    distribution_centers: pd.DataFrame,
    customer_regions: pd.DataFrame,
) -> pd.DataFrame:
    """Generate DC-to-customer-region transportation lanes."""

    rows: list[dict] = []

    for dc in distribution_centers.to_dict(orient="records"):
        for region in customer_regions.to_dict(orient="records"):
            straight_line_distance = haversine_distance_miles(
                dc["latitude"],
                dc["longitude"],
                region["latitude"],
                region["longitude"],
            )

            road_distance = straight_line_distance * random.uniform(
                1.08,
                1.20,
            )

            cost_per_pallet = (
                18.0
                + road_distance * random.uniform(0.07, 0.11)
            )

            lead_time_days = max(
                1,
                math.ceil(road_distance / 600),
            )

            rows.append(
                {
                    "lane_id": (
                        f'{dc["dc_id"]}_{region["region_id"]}'
                    ),
                    "dc_id": dc["dc_id"],
                    "region_id": region["region_id"],
                    "distance_miles": round(road_distance, 1),
                    "cost_per_pallet": round(
                        cost_per_pallet,
                        2,
                    ),
                    "lead_time_days": lead_time_days,
                    "is_available": random.random() > 0.01,
                }
            )

    return pd.DataFrame(rows)
def generate_demand(
    customer_regions: pd.DataFrame,
) -> pd.DataFrame:
    """Generate weekly demand for each customer region."""

    rows: list[dict] = []

    week_factors = {
        1: 1.00,
        2: 1.04,
        3: 0.97,
        4: 1.08,
    }

    for week in range(1, NUMBER_OF_WEEKS + 1):
        for region in customer_regions.to_dict(orient="records"):
            random_variation = random.uniform(0.96, 1.04)

            demand_pallets = round(
                region["base_weekly_demand"]
                * week_factors[week]
                * random_variation
            )

            rows.append(
                {
                    "week": week,
                    "region_id": region["region_id"],
                    "demand_pallets": demand_pallets,
                }
            )

    return pd.DataFrame(rows)
def generate_initial_inventory(
    distribution_centers: pd.DataFrame,
) -> pd.DataFrame:
    """Create the opening inventory table for Week 1."""

    return distribution_centers[
        [
            "dc_id",
            "initial_inventory_pallets",
        ]
    ].copy()
def validate_generated_data(
    suppliers: pd.DataFrame,
    distribution_centers: pd.DataFrame,
    customer_regions: pd.DataFrame,
    inbound_lanes: pd.DataFrame,
    outbound_lanes: pd.DataFrame,
    demand: pd.DataFrame,
) -> None:
    """Validate the structure and basic feasibility of generated data."""

    expected_inbound_lanes = (
        len(suppliers) * len(distribution_centers)
    )

    expected_outbound_lanes = (
        len(distribution_centers) * len(customer_regions)
    )

    expected_demand_rows = (
        NUMBER_OF_WEEKS * len(customer_regions)
    )

    if len(inbound_lanes) != expected_inbound_lanes:
        raise ValueError(
            f"Expected {expected_inbound_lanes} inbound lanes, "
            f"but found {len(inbound_lanes)}."
        )

    if len(outbound_lanes) != expected_outbound_lanes:
        raise ValueError(
            f"Expected {expected_outbound_lanes} outbound lanes, "
            f"but found {len(outbound_lanes)}."
        )

    if len(demand) != expected_demand_rows:
        raise ValueError(
            f"Expected {expected_demand_rows} demand rows, "
            f"but found {len(demand)}."
        )

    if suppliers["supplier_id"].duplicated().any():
        raise ValueError("Duplicate supplier IDs found.")

    if distribution_centers["dc_id"].duplicated().any():
        raise ValueError("Duplicate DC IDs found.")

    if customer_regions["region_id"].duplicated().any():
        raise ValueError("Duplicate customer region IDs found.")

    if inbound_lanes.duplicated(
        subset=["supplier_id", "dc_id"]
    ).any():
        raise ValueError("Duplicate inbound lanes found.")

    if outbound_lanes.duplicated(
        subset=["dc_id", "region_id"]
    ).any():
        raise ValueError("Duplicate outbound lanes found.")

    if (suppliers["weekly_capacity_pallets"] <= 0).any():
        raise ValueError("Supplier capacity must be positive.")

    if (
        inbound_lanes["pallets_per_container"] <= 0
    ).any():
        raise ValueError(
            "Pallets per container must be positive."
        )

    if (inbound_lanes["cost_per_container"] < 0).any():
        raise ValueError(
            "Inbound container cost cannot be negative."
        )

    if (outbound_lanes["cost_per_pallet"] < 0).any():
        raise ValueError(
            "Outbound pallet cost cannot be negative."
        )

    total_active_supply = suppliers.loc[
        suppliers["is_active"],
        "weekly_capacity_pallets",
    ].sum()

    maximum_weekly_demand = (
        demand.groupby("week")["demand_pallets"]
        .sum()
        .max()
    )

    total_initial_inventory = distribution_centers[
        "initial_inventory_pallets"
    ].sum()

    available_network_supply = (
        total_active_supply + total_initial_inventory
    )

    if available_network_supply < maximum_weekly_demand:
        raise ValueError(
            "Active supplier capacity plus initial inventory "
            "is lower than maximum weekly demand."
        )
def main() -> None:
    """Generate, validate, and save all synthetic network datasets."""

    random.seed(RANDOM_SEED)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    suppliers = generate_suppliers()

    distribution_centers = pd.DataFrame(
        DISTRIBUTION_CENTERS
    )

    customer_regions = pd.DataFrame(
        CUSTOMER_REGIONS
    )

    inbound_lanes = generate_inbound_lanes(
        suppliers=suppliers,
        distribution_centers=distribution_centers,
    )

    outbound_lanes = generate_outbound_lanes(
        distribution_centers=distribution_centers,
        customer_regions=customer_regions,
    )

    demand = generate_demand(
        customer_regions=customer_regions
    )

    initial_inventory = generate_initial_inventory(
        distribution_centers=distribution_centers
    )

    validate_generated_data(
        suppliers=suppliers,
        distribution_centers=distribution_centers,
        customer_regions=customer_regions,
        inbound_lanes=inbound_lanes,
        outbound_lanes=outbound_lanes,
        demand=demand,
    )

    suppliers.to_csv(
        DATA_DIR / "suppliers.csv",
        index=False,
    )

    distribution_centers.to_csv(
        DATA_DIR / "distribution_centers.csv",
        index=False,
    )

    customer_regions.to_csv(
        DATA_DIR / "customer_regions.csv",
        index=False,
    )

    inbound_lanes.to_csv(
        DATA_DIR / "inbound_lanes.csv",
        index=False,
    )

    outbound_lanes.to_csv(
        DATA_DIR / "outbound_lanes.csv",
        index=False,
    )

    demand.to_csv(
        DATA_DIR / "demand.csv",
        index=False,
    )

    initial_inventory.to_csv(
        DATA_DIR / "initial_inventory.csv",
        index=False,
    )

    active_weekly_supply = suppliers.loc[
        suppliers["is_active"],
        "weekly_capacity_pallets",
    ].sum()

    weekly_demand = (
        demand.groupby("week")["demand_pallets"]
        .sum()
        .sort_index()
    )

    print("\nSynthetic network generated successfully")
    print("-" * 45)
    print(f"Suppliers: {len(suppliers)}")
    print(
        "Active suppliers: "
        f"{int(suppliers['is_active'].sum())}"
    )
    print(
        "Distribution centers: "
        f"{len(distribution_centers)}"
    )
    print(
        "Customer regions: "
        f"{len(customer_regions)}"
    )
    print(f"Inbound lanes: {len(inbound_lanes)}")
    print(f"Outbound lanes: {len(outbound_lanes)}")
    print(f"Demand records: {len(demand)}")
    print(
        "Active weekly supplier capacity: "
        f"{int(active_weekly_supply):,} pallets"
    )

    for week, week_demand in weekly_demand.items():
        print(
            f"Week {int(week)} demand: "
            f"{int(week_demand):,} pallets"
        )


if __name__ == "__main__":
    main()

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def main() -> None:
    suppliers = pd.read_csv(DATA_DIR / "suppliers.csv")
    distribution_centers = pd.read_csv(
        DATA_DIR / "distribution_centers.csv"
    )
    customer_regions = pd.read_csv(
        DATA_DIR / "customer_regions.csv"
    )
    inbound_lanes = pd.read_csv(
        DATA_DIR / "inbound_lanes.csv"
    )
    outbound_lanes = pd.read_csv(
        DATA_DIR / "outbound_lanes.csv"
    )
    demand = pd.read_csv(
        DATA_DIR / "demand.csv"
    )
    initial_inventory = pd.read_csv(
        DATA_DIR / "initial_inventory.csv"
    )

    print("\nDATASET SHAPES")
    print("-" * 40)
    print(f"Suppliers: {suppliers.shape}")
    print(f"Distribution centers: {distribution_centers.shape}")
    print(f"Customer regions: {customer_regions.shape}")
    print(f"Inbound lanes: {inbound_lanes.shape}")
    print(f"Outbound lanes: {outbound_lanes.shape}")
    print(f"Demand: {demand.shape}")
    print(f"Initial inventory: {initial_inventory.shape}")

    print("\nSUPPLY SUMMARY")
    print("-" * 40)

    active_suppliers = suppliers[suppliers["is_active"]]

    total_active_capacity = active_suppliers[
        "weekly_capacity_pallets"
    ].sum()

    print(f"Active suppliers: {len(active_suppliers)}")
    print(
        f"Active weekly capacity: "
        f"{int(total_active_capacity):,} pallets"
    )

    print("\nDEMAND BY WEEK")
    print("-" * 40)

    weekly_demand = (
        demand.groupby("week")["demand_pallets"]
        .sum()
        .sort_index()
    )

    for week, total in weekly_demand.items():
        coverage = total_active_capacity / total

        print(
            f"Week {int(week)}: "
            f"{int(total):,} pallets | "
            f"capacity coverage: {coverage:.2f}x"
        )

    print("\nINBOUND LANE SUMMARY")
    print("-" * 40)
    print(
        inbound_lanes[
            [
                "distance_miles",
                "cost_per_container",
                "pallets_per_container",
                "lead_time_days",
                "lane_reliability",
            ]
        ].describe()
    )

    print("\nOUTBOUND LANE SUMMARY")
    print("-" * 40)
    print(
        outbound_lanes[
            [
                "distance_miles",
                "cost_per_pallet",
                "lead_time_days",
            ]
        ].describe()
    )

    print("\nAVAILABILITY CHECK")
    print("-" * 40)
    print(
        "Unavailable inbound lanes: "
        f"{int((~inbound_lanes['is_available']).sum())}"
    )
    print(
        "Unavailable outbound lanes: "
        f"{int((~outbound_lanes['is_available']).sum())}"
    )

    print("\nSAMPLE SUPPLIERS")
    print("-" * 40)
    print(suppliers.head())

    print("\nSAMPLE INBOUND LANES")
    print("-" * 40)
    print(inbound_lanes.head())


if __name__ == "__main__":
    main()

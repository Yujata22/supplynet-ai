from pathlib import Path

import pandas as pd

from app.models.customer_region import CustomerRegion
from app.models.demand_record import DemandRecord
from app.models.distribution_center import DistributionCenter
from app.models.inbound_lane import InboundLane
from app.models.network_data import NetworkData
from app.models.outbound_lane import OutboundLane
from app.models.supplier import Supplier


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def dataframe_to_models(
    dataframe: pd.DataFrame,
    model_class: type,
) -> list:
    """Convert DataFrame rows into validated Pydantic models."""

    return [
        model_class(**row)
        for row in dataframe.to_dict(orient="records")
    ]


def load_network_data() -> NetworkData:
    """Load all CSV files and return validated network data."""

    suppliers_df = pd.read_csv(
        DATA_DIR / "suppliers.csv"
    )

    distribution_centers_df = pd.read_csv(
        DATA_DIR / "distribution_centers.csv"
    )

    customer_regions_df = pd.read_csv(
        DATA_DIR / "customer_regions.csv"
    )

    inbound_lanes_df = pd.read_csv(
        DATA_DIR / "inbound_lanes.csv"
    )

    outbound_lanes_df = pd.read_csv(
        DATA_DIR / "outbound_lanes.csv"
    )

    demand_df = pd.read_csv(
        DATA_DIR / "demand.csv"
    )

    return NetworkData(
        suppliers=dataframe_to_models(
            suppliers_df,
            Supplier,
        ),
        distribution_centers=dataframe_to_models(
            distribution_centers_df,
            DistributionCenter,
        ),
        customer_regions=dataframe_to_models(
            customer_regions_df,
            CustomerRegion,
        ),
        inbound_lanes=dataframe_to_models(
            inbound_lanes_df,
            InboundLane,
        ),
        outbound_lanes=dataframe_to_models(
            outbound_lanes_df,
            OutboundLane,
        ),
        demand=dataframe_to_models(
            demand_df,
            DemandRecord,
        ),
    )

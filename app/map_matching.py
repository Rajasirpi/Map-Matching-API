import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
import os
import argparse

# Config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/geo")
SEARCH_RADIUS_METERS = 20  # ideal search radius for most common gps is either 15 to 20

parser = argparse.ArgumentParser()
parser.add_argument("--recording-id", type=int, required=True)
args = parser.parse_args()
RECORDING_ID = args.recording_id

# Connect to DB
engine = create_engine(DATABASE_URL)

# Load GPS points
gps = gpd.read_postgis(
    f"SELECT id, gps_index, geom FROM gps_tracks WHERE recording_id = {RECORDING_ID}",
    con=engine,
    geom_col="geom"
)

# Load road edges
edges = gpd.read_postgis(
    "SELECT edge_id, geom FROM road_edges",
    con=engine,
    geom_col="geom"
)

# Ensure both GeoDataFrames are in projected CRS (meters)
gps = gps.set_crs(4326).to_crs(3857)
edges = edges.set_crs(4326).to_crs(3857)

# Spatial join: find nearest edge for each GPS point within radius
joined = gpd.sjoin_nearest(
    gps, edges,
    how="inner",
    max_distance=SEARCH_RADIUS_METERS,
    distance_col="dist"
)

# Group by edge_id to build gps_index arrays
grouped = (
    joined.groupby("edge_id")
    .agg({
        "gps_index": lambda x: sorted(x.tolist()),
    })
    .reset_index()
)

grouped["recording_id"] = RECORDING_ID
grouped["gps_index"] = grouped["gps_index"].apply(lambda x: list(x))
grouped = grouped[["edge_id", "recording_id", "gps_index"]]
grouped.rename(columns={"gps_index": "gps_index_array"}, inplace=True)

# Write to mapping_table
with engine.begin() as conn:
    # Delete previous mappings for the same recording
    conn.execute(
        text("DELETE FROM mapping_table WHERE recording_id = :recording_id"),
        {"recording_id": RECORDING_ID}
    )
    grouped.to_sql("mapping_table", conn, if_exists="append", index=False)

print("Map matching completed and mapping_table populated.")

from pyrosm import OSM
from pathlib import Path
import geopandas as gpd
import requests
import os
from sqlalchemy import create_engine, text
import argparse

# Config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/geo")

# PBF_URL = "https://download.geofabrik.de/europe/germany-latest.osm.pbf"
PBF_URL = "https://download.geofabrik.de/europe/germany/nordrhein-westfalen-latest.osm.pbf"

PBF_FILENAME = "nordrhein-westfalen-latest.osm.pbf"
CACHE_DIR = Path("/app/osm_cache")  # You can mount this as a volume :/app/osm_cache in Docker
CACHE_DIR.mkdir(parents=True, exist_ok=True)
PBF_PATH = CACHE_DIR / PBF_FILENAME 
parser = argparse.ArgumentParser()
parser.add_argument("--recording-id", type=int, required=True)
args = parser.parse_args()
RECORDING_ID = args.recording_id


def get_bounding_box(engine):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                ST_XMin(extent) AS min_lon,
                ST_YMin(extent) AS min_lat,
                ST_XMax(extent) AS max_lon,
                ST_YMax(extent) AS max_lat
            FROM (
                SELECT ST_Extent(geom) AS extent
                FROM gps_tracks
                WHERE recording_id = :rec_id
            ) AS bbox;
        """), {"rec_id": RECORDING_ID}).fetchone()
    return result._mapping

def download_osm_pbf(url, output_path):
    if PBF_PATH.exists():
        print("Cached OSM file found. Skipping download.")
        return
    print(f"Downloading OSM PBF from {url}...")
    response = requests.get(url, stream=True)
    with open(str(PBF_PATH), "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    print("OSM download complete.")

def extract_edges_with_pyrosm(pbf_path, bbox):
    print("Extracting drivable road edges with Pyrosm...")

    # Convert bbox to [min_lon, min_lat, max_lon, max_lat] as expected by Pyrosm
    bounds = [bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]]

    # Initialize Pyrosm reader
    osm = OSM(pbf_path, bounding_box=bounds)

    # Extract driving network within bbox
    nodes, edges = osm.get_network(nodes=True, network_type="driving")

    # Debug: print columns and sample data
    # print(edges.head())

    print(f"Extracted {len(edges)}:edges and {len(nodes)}:nodes.")
    return edges

def save_edges_to_db(edges, engine):
    edges["osm_id"] = edges["id"].apply(lambda x: x[0] if isinstance(x, list) else x)
    edges = edges.rename(columns={"geometry": "geom"})
    edges = edges[["osm_id", "geom"]]
    edges = gpd.GeoDataFrame(edges, geometry="geom", crs="EPSG:4326")

    edges.to_postgis("road_edges", engine, if_exists="append", index=False)
    print("Road edges imported into database.")

def main():
    engine = create_engine(DATABASE_URL)
    bbox = get_bounding_box(engine)
    print(f"Bounding box from GPS data: {bbox}")
    download_osm_pbf(PBF_URL, str(PBF_PATH))
    edges = extract_edges_with_pyrosm(str(PBF_PATH), bbox)
    save_edges_to_db(edges, engine)

if __name__ == "__main__":
    main()

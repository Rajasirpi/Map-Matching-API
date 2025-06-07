import geopandas as gpd
from sqlalchemy import create_engine, text
from pathlib import Path
import os

# Config
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/geo")
DATA_DIR = Path("/app/data")  # Ensure this is mounted in docker-compose.yml

# Connect to DB
engine = create_engine(DATABASE_URL)

def insert_recording(conn, name):
    result = conn.execute(
        text("INSERT INTO recordings (name) VALUES (:name) RETURNING id"),
        {"name": name}
    )
    recording_id = result.scalar()
    print(f"Inserted into recordings: {name} → ID {recording_id}")
    return  recording_id

def import_gps_file(file_path: Path, recording_id: int):
    print(f"Importing {file_path.name} as recording_id {recording_id}")
    gdf = gpd.read_file(file_path)

    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)

    if "gps_index" not in gdf.columns and "properties" in gdf.columns:
        gdf["gps_index"] = gdf["properties"].apply(lambda x: x["gps_index"])

    gdf["recording_id"] = recording_id

    final_gdf = gdf[["recording_id", "gps_index", "geometry"]].copy()
    final_gdf = final_gdf.rename(columns={"geometry": "geom"})
    final_gdf.set_geometry("geom", inplace=True)
    final_gdf.to_postgis("gps_tracks", engine, if_exists="append", index=False)

    print(f"Imported {len(final_gdf)} GPS points from {file_path.name}")

def process_all_files():
    with engine.begin() as conn:
        for file_path in sorted(DATA_DIR.glob("*.geojson")):
            recording_id = insert_recording(conn, file_path.stem)
            import_gps_file(file_path, recording_id)

            # Run the rest of the pipeline
            os.system(f"python extract_and_import_osm_edges.py --recording-id {recording_id}")
            os.system(f"python map_matching.py --recording-id {recording_id}")

if __name__ == "__main__":
    process_all_files()


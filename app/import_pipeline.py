import geopandas as gpd
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/geo")
engine = create_engine(DATABASE_URL)

# Inserts recording_id into recordings table
def insert_recording(conn, name):
    result = conn.execute(
        text("INSERT INTO recordings (name) VALUES (:name) RETURNING id"),
        {"name": name}
    )
    recording_id = result.scalar()
    print(f"Inserted into recordings: {name} → ID {recording_id}")
    return recording_id

# Import data from the uploaded geojson file to db
def import_gps(file_path, recording_id):
    gdf = gpd.read_file(file_path)
    if "gps_index" not in gdf.columns and "properties" in gdf.columns:
        gdf["gps_index"] = gdf["properties"].apply(lambda x: x["gps_index"])

    gdf["recording_id"] = recording_id
    gdf = gdf[["recording_id", "gps_index", "geometry"]]
    gdf.set_crs("EPSG:4326", inplace=True)
    gdf.rename(columns={"geometry": "geom"}, inplace=True)
    gdf.set_geometry("geom", inplace=True)
    gdf.to_postgis("gps_tracks", engine, if_exists="append", index=False)

def run_pipeline(file_path, file_name):
    with engine.begin() as conn:
        recording_id = insert_recording(conn, file_name)

    import_gps(file_path, recording_id)
    os.system(f"python extract_and_import_osm_edges.py --recording-id {recording_id}")
    os.system(f"python map_matching.py --recording-id {recording_id}")

    return recording_id

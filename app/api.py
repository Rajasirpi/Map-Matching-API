from fastapi import APIRouter, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
import tempfile, shutil, os
import geopandas as gpd
from import_pipeline import run_pipeline
from shapely.geometry import LineString

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/geo")
engine = create_engine(DATABASE_URL)

# Upload and Process GPS GeoJSON
@router.post("/upload/")
async def upload_gps(file: UploadFile):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    recording_id = run_pipeline(tmp_path, file.filename)

    return JSONResponse({
        "status": "processed",
        "recording_id": recording_id
    })

# Direction-aware line segmentation 
def split_on_index_gaps(indexes):
    """Splits list into chunks of consecutive integers"""
    groups = []
    current = [indexes[0]]
    for prev, curr in zip(indexes, indexes[1:]):
        if curr == prev + 1:
            current.append(curr)
        else:
            groups.append(current)
            current = [curr]
    groups.append(current)
    return groups

@router.get("/matched-lines/{recording_id}")
def get_matched_lines(recording_id: int):
    # Load all GPS points
    sql = text("""
        SELECT m.edge_id, m.gps_index_array, g.gps_index, g.geom
        FROM mapping_table m
        JOIN gps_tracks g
          ON g.recording_id = m.recording_id
         AND g.gps_index = ANY(m.gps_index_array)
        WHERE m.recording_id = :rec_id
        ORDER BY m.edge_id, g.gps_index
    """)
    gdf = gpd.read_postgis(sql, engine, params={"rec_id": recording_id}, geom_col="geom")

    features = []
    for edge_id, group in gdf.groupby("edge_id"):
        all_indices = group["gps_index"].tolist()
        sublists = split_on_index_gaps(all_indices)

        for sub in sublists:
            sub_points = group[group["gps_index"].isin(sub)].sort_values("gps_index").geom.tolist()
            
            if len(sub_points) > 1:
                features.append({
                    "type": "Feature",
                    "geometry": LineString(sub_points).__geo_interface__,
                    "properties": {
                        "edge_id": int(edge_id),
                        "recording_id": recording_id,
                        "start_index": sub[0],
                        "end_index": sub[-1]
                    }
                })

            # uncomment this part if you want to include single-point which are matched to the edges

            # elif len(sub_points) == 1:
            #     point = sub_points[0]
            #     features.append({
            #         "type": "Feature",
            #         "geometry": point.__geo_interface__,
            #         "properties": {
            #             "edge_id": int(edge_id),
            #             "recording_id": recording_id,
            #             "gps_index": sub[0],
            #             "note": "only one GPS point matched"
            #         }
            #     })

    return JSONResponse(content={
        "type": "FeatureCollection",
        "features": features
    })

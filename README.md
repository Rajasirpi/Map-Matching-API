# 🗺️ GPS Map Matching API with FastAPI + PostGIS + Pyrosm

This project provides a complete backend pipeline for uploading GPS tracks (in GeoJSON format), matching them to road network edges using OpenStreetMap (OSM), and exposing the results via an API. It uses **FastAPI**, **PostgreSQL + PostGIS**, and **Pyrosm** for edge extraction, along with a **simple map-matching algorithm** based on nearest-edge logic.


## 📁 Project Structure

- app/
    - main.py - FastAPI entry point
    - api.py - Upload & matched-lines endpoints
    - import_data.py - Initial data importer for local .geojson files
    - import_pipeline.py - Pipeline used by upload endpoint
    - map_matching.py - Simple map matching logic (spatial join)
    - extract_and_import_osm_edges.py - Pyrosm edge extractor
    - create_tables.py - PostgreSQL schema setup
    - entrypoint.sh - Docker entrypoint to initialize and run app
    - requirements.txt - Python dependencies
- data/ - Place your .geojson GPS files here
- osm_cache/ - Cached OSM PBF files
- docker-compose.yml
- README.md


## ⚙️ Setup Instructions

### ✅ 1. Clone the repo

```bash
git clone https://github.com/Rajasirpi/Map-Matching-API.git
cd map-matching-api
```

### ✅ 2. Add your GPS data
- Put your .geojson GPS track files (point data) in the ./data/ folder.

- Ensure each file has a gps_index field under "properties" and is in WGS84 (EPSG:4326).

### ✅ 3. Configure OSM region
- By default, the project downloads and uses Nordrhein-Westfalen (a state in Germany) from Geofabrik to speed up processing.
- You can change the OSM data region by editing this line in extract_and_import_osm_edges.py:

```bash
PBF_URL = "https://download.geofabrik.de/europe/germany/nordrhein-westfalen-latest.osm.pbf"
```

#### Other options:
- Germany-wide: germany-latest.osm.pbf
- France: france-latest.osm.pbf
- State-level data is available from: https://download.geofabrik.de/

### ✅ 4. Build and run Docker

```bash
docker-compose up --build
```

This will:
- Create the PostgreSQL + PostGIS database
- Run create_tables.py
- Import all .geojson files from /data
- Extract OSM road edges
- Map-match GPS to edges
- Start the FastAPI server on http://localhost:8000
- you can also connect to pgadmin locally using port: 5433 ( as mapped in docker) and host: 127.0.0.1 / localhost

### List of available endpoints: 

- http://localhost:8000/upload/
- http://localhost:8000/matched-lines/{recording_id} (recording_id: which you a get as a result of the upload endpoint)


## 🚀 API Usage

### 🔁 Upload New GPS File

- POST /upload/
- Upload a new GeoJSON file. Automatically imports the data, extracts edges, and runs map matching.
- To test the API, you can either use a tool like Postman or FAST API Swagger UI:

#### ✅ Using Swagger UI
- Go to: http://localhost:8000/docs
- Scroll to POST /upload/
- Click "Try it out"
- Upload a .geojson file
- Click "Execute" (Wait for few minutes to get the result)

#### ✅ Using Postman
- Create a POST request to: http://localhost:8000/upload/
- Under Body > form-data, add:
- Key = file (type: File)
- Value = select your .geojson file

#### 📤 Get Matched Lines
- GET /matched-lines/{recording_id}
- Returns a GeoJSON FeatureCollection of LineString segments matched to road edges, grouped by directionally consistent GPS sections.
Example:

```bash
http://localhost:8000/matched-lines/1
```
Each feature:
- Has properties: edge_id, recording_id, start_index, end_index
- Is a clean LineString 

## 🧠 How Matching Works
- Edges are extracted from OSM using pyrosm and clipped to a bounding box based on the GPS data.
- GPS points are matched to their nearest edge using a spatial join.
- Points are grouped by edge and split into directionally consistent sequences based on gps_index.
- Resulting LineStrings are returned via API.

## 🧱 Database Tables
- recordings: uploaded files, one row per recording
- gps_tracks: each GPS point with geometry and index
- road_edges: clipped road segments from OSM
- mapping_table: maps an edge to a list of gps_index values (possibly split into directionally consistent chunks)

## 🛠️ Development Notes
- All processing runs inside Docker — no need to install PostGIS or Python locally
- You can run all CLI scripts like this:

```bash
docker-compose exec app python create_tables.py
docker-compose exec app python import_data.py
```
- Scripts can also be used manually to test individual steps (map_matching.py, extract_and_import_osm_edges.py)

## ✍️ Credits
- Built with FastAPI, PostGIS, Pyrosm, and GeoPandas


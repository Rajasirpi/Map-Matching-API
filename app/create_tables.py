from sqlalchemy import create_engine, Column, Integer, BigInteger, ARRAY, text,String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
import os


# Use environment variable or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/geo")

# Setup engine and base
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Table 1: gps_tracks
class GPSTrack(Base):
    __tablename__ = 'gps_tracks'
    id = Column(Integer, primary_key=True)
    recording_id = Column(BigInteger)
    gps_index = Column(Integer)
    geom = Column(Geometry(geometry_type='POINT', srid=4326))

# Table 2: road_edges
class RoadEdge(Base):
    __tablename__ = 'road_edges'
    edge_id = Column(BigInteger, primary_key=True, autoincrement=True)
    osm_id = Column(BigInteger)
    geom = Column(Geometry(geometry_type='LINESTRING', srid=4326))

# Table 3: mapping_table
class MappingTable(Base):
    __tablename__ = 'mapping_table'
    id = Column(Integer, primary_key=True)
    edge_id = Column(BigInteger)  # FK constraint handled via raw SQL for simplicity
    recording_id = Column(BigInteger)
    gps_index_array = Column(ARRAY(BigInteger))

# Table 4: recordings
class Recording(Base):
    __tablename__ = 'recordings'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# Run everything
if __name__ == "__main__":
    with engine.connect() as conn:
        # Enable PostGIS
        print("Enabling PostGIS extension...")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

    print("Creating tables...")
    # To does not overwrite or recreate tables if they already exist
    Base.metadata.create_all(engine)

    with engine.connect() as conn:
        # Add FK manually for mapping_table.edge_id
        print("Adding foreign key constraint...")
        conn.execute(text("""
            ALTER TABLE mapping_table
            ADD CONSTRAINT fk_edge_id FOREIGN KEY (edge_id)
            REFERENCES road_edges(edge_id)
            ON DELETE CASCADE;
        """))

        # Create spatial indexes
        print("Creating spatial indexes...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_gps_geom ON gps_tracks USING GIST (geom);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_edges_geom ON road_edges USING GIST (geom);"))

    print("All tables and indexes created successfully.")

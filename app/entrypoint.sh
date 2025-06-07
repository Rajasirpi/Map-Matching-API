#!/bin/bash
set -e

echo "🔧 Running DB setup..."
python create_tables.py

echo "Running import_data.py..."
python import_data.py

echo "Starting API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000

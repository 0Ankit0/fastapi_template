#!/bin/sh
set -e

echo "Waiting for database to be ready..."
# Use a simple python loop to wait for the DB port to open up completely
python -c "
import socket
import time
import sys

port = 5432
host = 'db'

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((host, port))
        s.close()
        break
    except socket.error:
        print('Database not ready yet, sleeping 1 second...')
        time.sleep(1)
"

echo "Database is up! Running migrations..."
alembic upgrade head

echo "Starting FastAPI application..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
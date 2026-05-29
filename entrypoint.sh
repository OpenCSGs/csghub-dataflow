#!/bin/bash

# Start FastAPI API server and replace current shell process
exec uvicorn data_server.main:app --host 0.0.0.0 --port 8000
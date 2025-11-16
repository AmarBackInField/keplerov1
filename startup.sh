#!/bin/bash

# Start the voice backend service in the background
python voice_backend/outboundService/entry.py dev &

# Start the FastAPI application (this runs in the foreground)
python -m uvicorn api:app --host 0.0.0.0 --port 8000
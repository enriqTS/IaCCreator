#!/bin/bash

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start the frontend
cd /app/frontend && node server.js &
FRONTEND_PID=$!

# Wait for either process to exit
wait -n $BACKEND_PID $FRONTEND_PID
exit $?

#!/bin/bash

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start the frontend (HOSTNAME=0.0.0.0 makes Next.js bind to all interfaces)
cd /app/frontend && HOSTNAME=0.0.0.0 node server.js &
FRONTEND_PID=$!

# If either process exits, restart it
while true; do
  if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Backend exited, restarting..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
  fi
  if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "Frontend exited, restarting..."
    cd /app/frontend && HOSTNAME=0.0.0.0 node server.js &
    FRONTEND_PID=$!
  fi
  sleep 2
done

@echo off
REM Build and push Docker images to GitHub Container Registry.
REM
REM Prerequisites (one-time setup):
REM   1. Create a GitHub Personal Access Token (classic) with "write:packages" scope
REM      at https://github.com/settings/tokens
REM   2. Log in to ghcr.io:
REM      echo YOUR_TOKEN | docker login ghcr.io -u enriqTS --password-stdin
REM
REM After that, just run this script whenever you want to publish a new version.

set REGISTRY=ghcr.io/enriqts/iacreator

echo === Building images ===
docker compose build

echo === Tagging images ===
docker tag iacreator-backend:latest %REGISTRY%-backend:latest
docker tag iacreator-frontend:latest %REGISTRY%-frontend:latest

echo === Pushing to GitHub Container Registry ===
docker push %REGISTRY%-backend:latest
docker push %REGISTRY%-frontend:latest

echo === Done! Testers can pull the latest with: ===
echo docker compose -f docker-compose.testers.yml pull

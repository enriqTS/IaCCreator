FROM node:24-alpine AS frontend-deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:24-alpine AS frontend-builder
WORKDIR /app
COPY --from=frontend-deps /app/node_modules ./node_modules
COPY frontend/ .
ENV NEXT_PUBLIC_API_URL=http://localhost:8000
RUN npm run build

# --- Final image with both services ---
FROM python:3.14-slim

# Install Node.js runtime (needed to run the Next.js standalone server) and uv
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl bash && \
    curl -fsSL https://deb.nodesource.com/setup_24.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apt-get purge -y curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install Python dependencies with uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-editable

ENV PATH="/app/.venv/bin:$PATH"

# Copy backend
COPY app/ ./app/
RUN mkdir -p /app/data

# Copy frontend standalone build
COPY --from=frontend-builder /app/public ./frontend/public
COPY --from=frontend-builder /app/.next/standalone ./frontend/
COPY --from=frontend-builder /app/.next/static ./frontend/.next/static

# Copy entrypoint script
COPY build/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV HOSTNAME=0.0.0.0

EXPOSE 3000 8000

CMD ["/app/entrypoint.sh"]

# Build the React frontend with Node/npm.
FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend ./frontend
COPY vite.config.js ./
RUN npm run build

# Run FastAPI with the matching Playwright version and bundled Chromium dependencies.
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY docs ./docs
COPY --from=frontend /build/app/static ./app/static
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]

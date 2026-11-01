FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]

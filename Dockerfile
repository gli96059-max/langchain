FROM python:3.11-slim

WORKDIR /app

# Install Node.js for frontend build and Python build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Build frontend
RUN cd frontend && npm install && npm run build

# Clean up apt cache
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers ${UVICORN_WORKERS:-2}

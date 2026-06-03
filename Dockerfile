FROM python:3.12-slim

# System deps for dbt-postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make scripts executable
RUN chmod +x scripts/*.py jobs/*.py 2>/dev/null || true

ENTRYPOINT ["python", "scripts/entrypoint.py"]

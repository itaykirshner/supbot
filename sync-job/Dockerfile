FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY sync-job/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for the new functional approach
RUN pip install --no-cache-dir pydantic[email] redis aiohttp pydantic-settings

# Copy application code
COPY sync-job/ .
COPY rag_module /app/rag_module
COPY zoho_desk_module /app/zoho_desk_module

# Create non-root user
RUN useradd --create-home --shell /bin/bash syncuser \
    && chown -R syncuser:syncuser /app
USER syncuser

# Run sync job
CMD ["python", "sync_data.py"]

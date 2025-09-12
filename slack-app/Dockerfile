FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set PYTHONPATH to include the current working directory
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY slack-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from slack-app directory and rag-module
COPY slack-app/ .
COPY rag_module /app/rag_module

# Install additional dependencies for the new functional approach
RUN pip install --no-cache-dir pydantic[email] pydantic-settings redis aiohttp

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose health check port
EXPOSE 8080

# Run application
CMD ["python", "app.py"]

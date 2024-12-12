FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies and upgrade if needed 
RUN apt update -y && apt upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Create directories for config and database
RUN mkdir -p /app/config /app/chain_database

# Use a non-root user for security
RUN useradd -m pythonuser
USER pythonuser

# Specify everything just in case
CMD ["python", "/app/tnom/main.py", "--working-dir", "/app", "--config-path", "/app/config/config.yml", "--alert-path", "/app/config/alert.yml"]

EXPOSE 7130
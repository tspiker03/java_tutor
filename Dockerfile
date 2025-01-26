FROM python:3.9.18-slim

WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV REDIS_URL=""
ENV SUBJECT="Python"

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN apt-get update && apt-get install -y dos2unix && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    mkdir -p /app/static/dist

# Copy the rest of the application
COPY . .

# Ensure proper permissions
RUN chmod -R 755 /app && \
    chmod 644 optimized_prompt.txt

# Fix line endings and make start script executable
RUN dos2unix start.sh && \
    chmod +x start.sh

# Command to run the application
CMD ["./start.sh"]

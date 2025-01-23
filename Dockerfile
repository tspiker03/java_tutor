FROM python:3.9.18-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN apt-get update && apt-get install -y dos2unix && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy the rest of the application
COPY . .

# Fix line endings and make start script executable
RUN dos2unix start.sh && \
    chmod +x start.sh

# Command to run the application
CMD ["./start.sh"]

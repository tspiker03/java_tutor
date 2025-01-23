FROM python:3.9.18-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE $PORT

# Command to run the application
CMD gunicorn app:app --bind 0.0.0.0:$PORT

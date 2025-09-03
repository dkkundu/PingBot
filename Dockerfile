# Base Python image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install MySQL client
RUN apt-get update && apt-get install -y default-mysql-client && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY . .

# Expose Flask port
EXPOSE 5001

# Run Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5001", "app.app:create_app"]

# Base Python image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Install MySQL client and Supervisor
RUN apt-get update && \
    apt-get install -y default-mysql-client supervisor && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# RUN apt-get install supervisor -y

# Copy project code
COPY . .

# Copy supervisord configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose Flask port
EXPOSE 5001

# Run Supervisor
# CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
CMD ["supervisord", "-c", "/app/supervisord.conf"]


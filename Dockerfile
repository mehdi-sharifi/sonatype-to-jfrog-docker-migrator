# Base image with Python
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Install crane (latest release from GitHub)
RUN curl -L https://github.com/google/go-containerregistry/releases/latest/download/crane-linux-amd64 \
    -o /usr/local/bin/crane && \
    chmod +x /usr/local/bin/crane

# Create working directory
WORKDIR /app

# Copy requirements (optional if using tqdm, requests)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY migrate_docker_images.py .
COPY .env.sample .

# Entry point
CMD ["python", "migrate_docker_images.py"]

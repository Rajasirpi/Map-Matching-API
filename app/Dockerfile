FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    software-properties-common \
    build-essential \
    libpq-dev \
    libspatialindex-dev \
    osmium-tool \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "entrypoint.sh"]

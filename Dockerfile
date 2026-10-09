FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for packages like bcrypt and pandas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Setting the pythonpath so modules can be imported
ENV PYTHONPATH=/app

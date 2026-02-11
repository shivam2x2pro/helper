FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies with time-sync fix
RUN echo "Acquire::Check-Valid-Until \"false\";\nAcquire::Check-Date \"false\";" > /etc/apt/apt.conf.d/10no-check-valid-until && \
    apt-get update && apt-get install -y \
    curl git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (including playwright from requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt playwright

# Install Playwright and its dependencies
RUN python -m playwright install --with-deps chromium

# Copy application code
COPY . .

# Expose the application port
EXPOSE 8000

# Command to run the application
CMD ["python", "main.py"]

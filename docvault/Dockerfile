FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd --create-home docvault && chown -R docvault:docvault /app
USER docvault

# Collect static files
RUN python manage.py collectstatic --noinput 2>/dev/null || true

EXPOSE 8000
CMD ["gunicorn", "docvault.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]

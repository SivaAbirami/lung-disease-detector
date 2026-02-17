FROM python:3.9
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install ALL required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    pkg-config \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    libpq-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Upgrade pip first (IMPORTANT)
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir --default-timeout=300 -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=backend.settings

RUN python manage.py collectstatic --noinput || true

CMD ["gunicorn", "backend.wsgi:application", "-b", "0.0.0.0:8000", "--workers", "3"]

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=2.2.1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    wget \
    gnupg \
    ca-certificates \
    chromium \
    chromium-driver \
    fonts-liberation \
    fonts-noto-color-emoji \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    gettext \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --upgrade pip setuptools wheel \
    && pip install "poetry==$POETRY_VERSION"

# Copy project metadata to leverage Docker layer caching
COPY pyproject.toml poetry.lock* README.md /code/

# Install project dependencies using Poetry
RUN poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --without dev --no-interaction --no-ansi --no-root

# Copy the rest of the project
COPY . .

# Collect static files
RUN python -c "print('collectstatic will run at container startup')"

# Install additional dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    libxss1 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN python -m playwright install --with-deps chromium

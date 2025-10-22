# Dockerfile for Sacramento Property Tax API with Playwright

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y \
    # Core dependencies
    wget \
    ca-certificates \
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-unifont \
    # Audio
    libasound2 \
    # GTK/Graphics
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    # Security/Crypto
    libnspr4 \
    libnss3 \
    # X11
    libwayland-client0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxshmfence1 \
    # Utils
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright Chromium (without --with-deps since we installed deps manually)
RUN playwright install chromium

# Copy application code
COPY . .

# Create directory for SQLite database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV BROWSER_HEADLESS=true
ENV CACHE_MAX_AGE_DAYS=30

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "120", "app:app"]


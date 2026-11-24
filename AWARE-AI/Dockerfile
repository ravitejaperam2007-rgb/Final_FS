# ============================================================
#  AWARE-AI — Production Docker Containerfile
#  Base: Python 3.10 Slim Linux (Debian Bookworm)
# ============================================================

FROM python:3.10-slim

# Prevent interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Install minimal OS dependencies and C libraries required by LightGBM / Open-Meteo
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create application user and working directory
WORKDIR /app

# Copy dependency manifest first for efficient Docker layer caching
COPY requirements.txt .

# Upgrade pip and install pinned application requirements
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application source tree
COPY . .

# Ensure data and logs directories exist with write permissions
RUN mkdir -p data logs && \
    chmod -R 777 data logs

# Expose Streamlit Control Tower default port
EXPOSE 8501

# Healthcheck to verify the web server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Launch the AWARE-AI Control Tower
ENTRYPOINT ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

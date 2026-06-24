# BizInsight AI - Dockerfile
# Builds a container image that runs the Streamlit app with all
# required dependencies (incl. NLTK/TextBlob corpora) baked in.

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies:
#  - build-essential: needed to build some ML packages (hdbscan, etc.) from source
#  - curl: used by the HEALTHCHECK below
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first so this layer is cached
# unless requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the NLTK/TextBlob corpora the app needs at runtime
# (app.py / sentiment.py use VADER; TextBlob needs its own corpora).
# Baking these in avoids a slow/flaky download on first request.
RUN python -m nltk.downloader vader_lexicon -d /usr/local/share/nltk_data \
    && python -m textblob.download_corpora
ENV NLTK_DATA=/usr/local/share/nltk_data

# Now copy the rest of the application code.
COPY . .

# Streamlit's default port
EXPOSE 8501

# Container healthcheck against Streamlit's built-in health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

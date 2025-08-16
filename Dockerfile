FROM python:3.11-slim

# Create working directory
WORKDIR /app

# Create and activate venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default to web server
CMD ["sh", "-c", "if [ \"$RUN_MODE\" = 'celery' ]; then \
  celery -A apiManager.celery.app worker --loglevel=info --without-gossip -E; \
  else \
  gunicorn apiManager.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:12024 \
    --workers 4 \
    --threads 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 120 \
    --keep-alive 5; \
  fi"]


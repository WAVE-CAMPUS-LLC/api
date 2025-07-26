FROM python:3.11-slim

# Create working directory
WORKDIR /app

# Copy source code
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Default to web server
CMD ["sh", "-c", "if [ \"$RUN_MODE\" = 'celery' ]; then celery -A wave_v1 worker --loglevel=info; else uvicorn apiManager.main:app --host 0.0.0.0 --port 12024; fi"]

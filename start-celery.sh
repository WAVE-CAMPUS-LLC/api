
# Start Celery worker in background
celery -A apiManager.celery.app.celery_app worker --loglevel=info &

# Start Celery beat in foreground (so Render keeps the container alive)
celery -A apiManager.celery.app.celery_app beat --loglevel=info

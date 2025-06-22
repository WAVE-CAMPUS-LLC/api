FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "apiManager.main:app", "--host", "0.0.0.0", "--port", "12024"]
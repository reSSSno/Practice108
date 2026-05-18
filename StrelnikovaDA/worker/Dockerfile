FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./
COPY logic ./logic
COPY dictionaries ./dictionaries

EXPOSE 8001
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "--workers", "1", "--threads", "4", "app:app"]

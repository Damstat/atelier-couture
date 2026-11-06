FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
# Commande par défaut ; docker-compose.yml applique d'abord les migrations et le seed
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

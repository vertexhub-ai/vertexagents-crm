FROM docker.io/library/python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y build-essential libpq-dev && apt-get autoremove -y
COPY . .
ENV DEBUG=False
ENV PYTHONUNBUFFERED=1
RUN python manage.py collectstatic --noinput || true
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn crm.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile -"]

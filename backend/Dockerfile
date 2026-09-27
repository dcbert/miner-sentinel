FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Apply Alpine security updates shipped with the base image
RUN apk upgrade --no-cache

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    # Drop build/packaging tools from the runtime image (fixes setuptools/msgpack CVEs in pip vendor tree)
    && pip uninstall -y pip setuptools wheel

COPY . .

RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["gunicorn", "minersentinel.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Apply Alpine security updates shipped with the base image
RUN apk upgrade --no-cache

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    # Drop build/packaging tools from the runtime image (fixes setuptools/msgpack CVEs in pip vendor tree)
    && pip uninstall -y pip setuptools wheel

# Copy application
COPY . .

# Create non-root user (Alpine uses adduser)
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "app.py"]

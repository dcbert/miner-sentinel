FROM python:3.11-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user (Alpine uses adduser)
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "app.py"]

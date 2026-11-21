FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 5000
# PORT lo inyecta la plataforma (Render, Fly, etc.); 5000 es el default local
# gthread: varios requests concurrentes por worker; con sync + 1 worker,
# un request lento (reintentos del proveedor) bloqueaba hasta el health check
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-5000} --worker-class gthread --workers 2 --threads 8 --timeout 60 wsgi:app"]

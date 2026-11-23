# Imagen única para producción: nginx (estáticos + proxy /api) y Flask
# (gunicorn) en el mismo contenedor. Un solo servicio en Render = un solo
# "despertar" y entra en las 750 horas gratis del mes si se mantiene
# despierto con un ping externo.
#
#   docker build -t clima-comarca .
#   docker run -p 8080:8080 -e REDIS_URL=redis://... clima-comarca

# --- Frontend: build de Vite ---
FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Runtime: Python + nginx ---
FROM python:3.12-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx gettext-base \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default \
    && ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log \
    && useradd --system --uid 10001 --no-create-home appuser

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./

# nginx sirve el build estático y reverse-proxy /api al gunicorn local.
# La plantilla usa ${PORT} y ${API_UPSTREAM}: se expande con envsubst en
# el arranque (ver entrypoint.sh)
COPY frontend/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=frontend-build /build/dist /usr/share/nginx/html
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV API_UPSTREAM=http://127.0.0.1:5000 \
    PORT=8080 \
    FLASK_ENV=production
EXPOSE 8080

# nginx master corre como root (normal en contenedores nginx); los workers
# caen al usuario nginx y gunicorn a appuser
CMD ["/entrypoint.sh"]

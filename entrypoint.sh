#!/bin/sh
# Arranca gunicorn en localhost y nginx al frente. nginx expone el build
# estático del frontend y reenvía /api/* a Flask por la red interna del
# contenedor (127.0.0.1), así el navegador solo habla con un servicio.
set -e

export PORT="${PORT:-8080}"
export API_UPSTREAM="${API_UPSTREAM:-http://127.0.0.1:5000}"

# Solo sustituye PORT y API_UPSTREAM; el resto de $vars son de nginx
# y deben quedar intactas
envsubst '$PORT $API_UPSTREAM' \
    < /etc/nginx/templates/default.conf.template \
    > /etc/nginx/conf.d/default.conf

# gthread + 2 workers como en el Dockerfile del backend: varios requests
# concurrentes por worker para que un request lento no bloquee el health
# check. Los workers corren como appuser (sin privilegios).
gunicorn \
    --bind 127.0.0.1:5000 \
    --worker-class gthread \
    --workers 2 \
    --threads 8 \
    --timeout 60 \
    --user appuser --group appuser \
    wsgi:app &

exec nginx -g 'daemon off;'

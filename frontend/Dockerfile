FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/templates/default.conf.template
# API_UPSTREAM es el servicio de backend en la red de Docker;
# NGINX_ENVSUBST_FILTER evita que envsubst toque las variables de nginx ($host, etc.)
# PORT lo inyecta la plataforma de hosting (Render, etc.); 80 es el default
ENV API_UPSTREAM=http://backend:5000 \
    PORT=80 \
    NGINX_ENVSUBST_FILTER='API_.*|PORT'
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

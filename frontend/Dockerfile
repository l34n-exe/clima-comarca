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
ENV API_UPSTREAM=backend:5000 \
    NGINX_ENVSUBST_FILTER=API_.*
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

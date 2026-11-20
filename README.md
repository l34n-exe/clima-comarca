# Clima Comarca

Plataforma para consultar el clima de la Comarca Patagónica (Viedma, Carmen de Patagones y playas cercanas).

**Stack:** Flask + Redis (caché) en el backend, Svelte + Vite servido por nginx en el frontend.

Incluye ráfagas de viento, probabilidad de lluvia, salida y puesta del sol, pronóstico horario de 24 horas y selección de localidad por búsqueda o ubicación cercana. La localidad seleccionada queda en el fragmento de URL (por ejemplo, `#el-condor`) y se conserva al compartir el enlace; además se recuerda en el navegador para la próxima visita. El título de la pestaña cambia según la localidad (`Clima en El Cóndor · Comarca Weather`), los gráficos horarios marcan máximos y mínimos con sus valores, y la página muestra esqueletos de carga y botones de reintento ante errores. Un pie de página acredita las fuentes: Open-Meteo (pronóstico y mareas) y NOAA (observaciones METAR).

## Correr todo con Docker

```bash
cp .env.example .env
docker compose up --build
```

La API queda en <http://localhost:5000/api/v1> y la web en <http://localhost:8080> (nginx sirve el build de producción y reenvía `/api` al backend).

Para desarrollar el frontend con recarga en caliente: `cd frontend && npm install && npm run dev` (queda en <http://localhost:5173> y el proxy de Vite manda `/api` a Flask, sin conflicto con el 8080 de Docker).

Compose espera a que Redis y la API estén saludables antes de iniciar los servicios que dependen de ellos. Los TTL del caché, `CACHE_STALE_EXTRA` y `HTTP_TIMEOUT` se pueden ajustar en `.env`; los TTL pueden ser cero para desactivar la frescura del caché, pero no negativos. `CORS_ORIGINS` acepta una lista de orígenes separada por comas. El contenedor del backend corre como un usuario sin privilegios (`appuser`), no como root.
Las variables `WEATHER_MODELS`, `METAR_URL`, `CACHE_TTL_OBSERVATION` y `OBSERVATION_MAX_AGE_MIN` controlan la comparación de modelos y las observaciones meteorológicas. `WEATHER_MODELS` debe incluir al menos dos modelos separados por comas, `METAR_URL` debe contener `{station}` y `OBSERVATION_MAX_AGE_MIN` debe ser mayor que cero. `HTTP_RETRIES` y `HTTP_RETRY_BACKOFF` ajustan los reintentos ante fallos transitorios de los proveedores.

La API limita a 120 peticiones por minuto por IP (`X-Forwarded-For` vía nginx) y registra cada request con un `X-Request-ID`. Cuando una clave de caché vence, un candado en Redis evita que varias peticiones simultáneas salgan a buscar el mismo dato.

## Endpoints

| Método | Ruta                      | Descripción                                        |
| ------ | ------------------------- | -------------------------------------------------- |
| GET    | /api/v1/locations?q=      | Lista o busca localidades                          |
| GET    | /api/v1/weather/< slug >  | Clima actual                                       |
| GET    | /api/v1/forecast/< slug > | Pronóstico a 7 días                                |
| GET    | /api/v1/tides/< slug >    | Pleamares, bajamares y serie horaria (solo playas) |
| GET    | /api/v1/models/< slug >   | Comparación de temperaturas entre modelos          |
| GET    | /api/v1/observation/< slug > | Observación METAR/NOAA de una estación             |
| GET    | /api/v1/health            | Estado de Flask y Redis                            |

## Sobre las mareas

Salen del modelo marino global de Open-Meteo (variable `sea_level_height_msl`, resolución ~8 km). Las pleamares y bajamares se calculan en el backend buscando máximos y mínimos de la serie horaria. Es una estimación: puede diferir de las tablas oficiales y no sirve para navegar. La respuesta incluye un campo `aviso` con esto.

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Los tests usan `fakeredis` y clientes simulados: no necesitan Docker ni acceso a los proveedores externos.

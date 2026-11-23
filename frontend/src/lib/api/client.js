const BASE = '/api/v1';
// Si el backend no responde en 75 s, se corta y se muestra el error
// en vez de dejar la pantalla cargando para siempre. El margen cubre
// el cold start completo del free tier de Render (~1 min) y los
// reintentos del proveedor cuando hay rate limit.
const TIMEOUT_MS = 75000;
// Los 502/503/504 del edge de Render o del proxy nginx suelen ser
// "el backend se está despertando": se reintenta un par de veces
// antes de mostrar el error al usuario.
const MAX_ATTEMPTS = 3;
const RETRY_DELAY_MS = 8000;
const RETRYABLE = new Set([502, 503, 504]);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Todas las llamadas pasan por acá: un solo lugar para manejar errores
async function get(path) {
  let lastError = null;
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    if (attempt > 0) await sleep(RETRY_DELAY_MS * attempt);
    let res;
    try {
      res = await fetch(BASE + path, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    } catch {
      lastError = new Error(
        'El servidor se está despertando o no responde. Esperá un minuto y reintentá.',
      );
      continue;
    }
    const body = await res.json().catch(() => ({}));
    if (res.ok) return body;
    lastError = new Error(body.error || 'El servidor devolvió un error.');
    if (!RETRYABLE.has(res.status)) throw lastError;
  }
  throw lastError;
}

export const getLocations = () => get('/locations');
export const getWeather = (slug) => get(`/weather/${slug}`);
export const getForecast = (slug) => get(`/forecast/${slug}`);
export const getTides = (slug) => get(`/tides/${slug}`);
export const getModels = (slug) => get(`/models/${slug}`);
export const getObservation = (slug) => get(`/observation/${slug}`);
export const getAccuracy = (slug) => get(`/accuracy/${slug}`);

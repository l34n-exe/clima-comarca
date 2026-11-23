const BASE = '/api/v1';
// Si el backend no responde en 75 s, se corta y se muestra el error
// en vez de dejar la pantalla cargando para siempre. El margen cubre
// el cold start completo del free tier de Render (~1 min) y los
// reintentos del proveedor cuando hay rate limit.
const TIMEOUT_MS = 75000;
// Los 502/503/504 del edge de Render o del proxy nginx suelen ser
// "el backend se está despertando": el edge falla al instante, así que
// se reintenta cada pocos segundos hasta agotar el presupuesto, que
// cubre el spin-up completo del free tier (~1-2 min).
const RETRY_BUDGET_MS = 120000;
const RETRY_DELAY_MS = 8000;
const RETRYABLE = new Set([502, 503, 504]);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// La UI se entera cuando una llamada está reintentando (backend
// despertando) para mostrar "reintentando…" en vez de skeletons
// que parecen colgados
let retryListener = null;
export const onRetry = (fn) => {
  retryListener = fn;
};

// Todas las llamadas pasan por acá: un solo lugar para manejar errores
async function get(path) {
  const deadline = Date.now() + RETRY_BUDGET_MS;
  let lastError = null;
  for (;;) {
    let res;
    try {
      res = await fetch(BASE + path, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    } catch {
      lastError = new Error(
        'El servidor se está despertando o no responde. Esperá un minuto y reintentá.',
      );
    }
    if (res) {
      const body = await res.json().catch(() => ({}));
      if (res.ok) return body;
      lastError = new Error(body.error || 'El servidor devolvió un error.');
      if (!RETRYABLE.has(res.status)) throw lastError;
    }
    if (Date.now() + RETRY_DELAY_MS > deadline) throw lastError;
    retryListener?.();
    await sleep(RETRY_DELAY_MS);
  }
}

export const getLocations = () => get('/locations');
export const getWeather = (slug) => get(`/weather/${slug}`);
export const getForecast = (slug) => get(`/forecast/${slug}`);
export const getTides = (slug) => get(`/tides/${slug}`);
export const getModels = (slug) => get(`/models/${slug}`);
export const getObservation = (slug) => get(`/observation/${slug}`);
export const getAccuracy = (slug) => get(`/accuracy/${slug}`);

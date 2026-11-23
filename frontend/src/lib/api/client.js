const BASE = '/api/v1';
// Si el backend no responde en 75 s, se corta y se muestra el error
// en vez de dejar la pantalla cargando para siempre. El margen cubre
// el cold start completo del free tier de Render y los reintentos
// del proveedor cuando hay rate limit.
const TIMEOUT_MS = 75000;
// Los 502/503/504 del edge de Render o del proxy nginx y los errores
// de red suelen ser "el backend se está despertando": se reintenta
// cada 5-8 s (aleatorio, para no sincronizar clientes) hasta agotar
// un presupuesto de 2.5 minutos, que cubre el peor spin-up visto.
const RETRY_BUDGET_MS = 150000;
const RETRY_MIN_MS = 5000;
const RETRY_MAX_MS = 8000;
const RETRYABLE = new Set([502, 503, 504]);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const retryDelay = () =>
  RETRY_MIN_MS + Math.random() * (RETRY_MAX_MS - RETRY_MIN_MS);

// La UI se entera de cada reintento (backend despertando) para mostrar
// "reintentando…" con el intento actual en vez de skeletons colgados.
// El callback recibe el número de intento.
let retryListener = null;
export const onRetry = (fn) => {
  retryListener = fn;
};

// Todas las llamadas pasan por acá: un solo lugar para manejar errores
async function get(path) {
  const deadline = Date.now() + RETRY_BUDGET_MS;
  let lastError = null;
  let attempt = 0;
  for (;;) {
    let res;
    try {
      res = await fetch(BASE + path, { signal: AbortSignal.timeout(TIMEOUT_MS) });
    } catch {
      lastError = new Error('Sin respuesta del servidor.');
    }
    if (res) {
      const body = await res.json().catch(() => ({}));
      if (res.ok) return body;
      lastError = new Error(body.error || 'El servidor devolvió un error.');
      if (!RETRYABLE.has(res.status)) throw lastError;
    }
    const delay = retryDelay();
    if (Date.now() + delay > deadline) throw lastError;
    attempt += 1;
    retryListener?.(attempt);
    await sleep(delay);
  }
}

export const getLocations = () => get('/locations');
export const getWeather = (slug) => get(`/weather/${slug}`);
export const getForecast = (slug) => get(`/forecast/${slug}`);
export const getTides = (slug) => get(`/tides/${slug}`);
export const getModels = (slug) => get(`/models/${slug}`);
export const getObservation = (slug) => get(`/observation/${slug}`);
export const getAccuracy = (slug) => get(`/accuracy/${slug}`);

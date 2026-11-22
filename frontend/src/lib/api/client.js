const BASE = '/api/v1';
// Si el backend no responde en 45 s, se corta y se muestra el error
// en vez de dejar la pantalla cargando para siempre. El margen cubre
// el cold start del free tier de Render (~1 min) y los reintentos
// del proveedor cuando hay rate limit.
const TIMEOUT_MS = 45000;

// Todas las llamadas pasan por acá: un solo lugar para manejar errores
async function get(path) {
  let res;
  try {
    res = await fetch(BASE + path, { signal: AbortSignal.timeout(TIMEOUT_MS) });
  } catch {
    throw new Error('No se pudo conectar con el servidor.');
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || 'El servidor devolvió un error.');
  return body;
}

export const getLocations = () => get('/locations');
export const getWeather = (slug) => get(`/weather/${slug}`);
export const getForecast = (slug) => get(`/forecast/${slug}`);
export const getTides = (slug) => get(`/tides/${slug}`);
export const getModels = (slug) => get(`/models/${slug}`);
export const getObservation = (slug) => get(`/observation/${slug}`);
export const getAccuracy = (slug) => get(`/accuracy/${slug}`);

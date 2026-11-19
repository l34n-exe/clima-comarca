const BASE = '/api/v1';

// Todas las llamadas pasan por acá: un solo lugar para manejar errores
async function get(path) {
  let res;
  try {
    res = await fetch(BASE + path);
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

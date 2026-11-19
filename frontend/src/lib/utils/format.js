export const num = (n, d = 1) =>
  Number(n).toLocaleString('es-AR', { minimumFractionDigits: d, maximumFractionDigits: d });

export const hhmm = (iso) => iso.slice(11, 16);

export const dayLabel = (iso) =>
  new Date(iso + 'T12:00:00').toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric' });

export const dayShort = (iso) =>
  new Date(iso + 'T12:00:00').toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric' });

export const compass = (deg) => ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'][Math.round(deg / 45) % 8];

// Hora actual en Argentina con el mismo formato que manda el backend,
// así funciona igual aunque quien mira esté en otra zona horaria
export const nowAR = () =>
  new Date().toLocaleString('sv-SE', { timeZone: 'America/Argentina/Buenos_Aires' })
    .replace(' ', 'T').slice(0, 16);

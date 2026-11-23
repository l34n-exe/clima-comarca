<script>
  let { locations, selectedSlug, onselect } = $props();
  let query = $state('');
  let locating = $state(false);
  let locationError = $state('');

  const norm = (s) => s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().trim();
  let matches = $derived(locations.filter((l) => norm(l.nombre).includes(norm(query))));

  const distance = (lat1, lon1, lat2, lon2) => {
    const radians = (degrees) => (degrees * Math.PI) / 180;
    const dLat = radians(lat2 - lat1);
    const dLon = radians(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos(radians(lat1)) * Math.cos(radians(lat2)) * Math.sin(dLon / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  };

  async function selectNearest() {
    locationError = '';
    if (!navigator.geolocation) {
      locationError = 'Este navegador no permite obtener tu ubicación.';
      return;
    }

    locating = true;
    try {
      const position = await new Promise((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: false,
          maximumAge: 300000,
          timeout: 10000,
        }),
      );
      const { latitude, longitude } = position.coords;
      const nearest = locations.reduce((closest, location) =>
        distance(latitude, longitude, location.lat, location.lon) <
        distance(latitude, longitude, closest.lat, closest.lon)
          ? location
          : closest,
      );
      onselect(nearest);
    } catch (error) {
      locationError =
        error.code === 1
          ? 'No se autorizó el acceso a la ubicación.'
          : error.code === 3
            ? 'La ubicación tardó demasiado. Intentá nuevamente.'
            : 'No se pudo determinar tu ubicación.';
    } finally {
      locating = false;
    }
  }
</script>

<div class="search">
  <label for="q">Buscar ciudad o playa</label>
  <input id="q" type="search" bind:value={query} placeholder="Viedma, El Cóndor…" autocomplete="off" />
  <ul>
    {#each matches as loc (loc.slug)}
      <li>
        <button type="button" class:active={loc.slug === selectedSlug}
          aria-pressed={loc.slug === selectedSlug} onclick={() => onselect(loc)}>
          {loc.nombre}
        </button>
      </li>
    {/each}
  </ul>
  {#if locations.length > 0 && norm(query) !== '' && matches.length === 0}
    <p class="none">No hay resultados para “{query}”. Probá con otro nombre.</p>
  {/if}
  <button
    class="nearby"
    type="button"
    onclick={selectNearest}
    disabled={locating || locations.length === 0}
  >
    {locating ? 'Buscando ubicación…' : 'Elegir localidad más cercana'}
  </button>
  {#if locationError}
    <p class="geo-error" role="alert">{locationError}</p>
  {/if}
</div>

<script>
  import { onMount } from "svelte";
  import {
    getLocations,
    getWeather,
    getForecast,
    getTides,
    getModels,
    getObservation,
  } from "./lib/api/client.js";
  import CurrentWeather from "./lib/components/CurrentWeather.svelte";
  import ForecastList from "./lib/components/ForecastList.svelte";
  import ModelSpread from "./lib/components/ModelSpread.svelte";
  import Observation from "./lib/components/Observation.svelte";
  import SearchBar from "./lib/components/SearchBar.svelte";
  import Hero from "./lib/components/Hero.svelte";
  // El gráfico de mareas (LayerChart) pesa mucho: se descarga recién
  // cuando se elige una playa, no al abrir la página
  const loadTideChart = () => import("./lib/components/TideChart.svelte");
  const loadHourlyForecast = () => import("./lib/components/HourlyForecast.svelte");

  let locations = $state([]);
  let locationsLoaded = $state(false);
  let selected = $state(null);
  let weather = $state(null);
  let forecast = $state(null);
  let tides = $state(null);
  let models = $state(null);
  let observation = $state(null);
  let errors = $state({});
  let loading = $state(false);
  let loadError = $state("");
  let requestId = 0;
  let popstateHandler;

  const value = (r) => (r.status === "fulfilled" ? r.value : null);
  const failure = (r) => (r.status === "rejected" ? r.reason.message : "");

  async function select(location) {
    selected = location;
    const id = ++requestId;
    weather = null;
    forecast = null;
    tides = null;
    models = null;
    observation = null;
    errors = {};
    if (!location) {
      loading = false;
      return;
    }
    loading = true;
    // Se empieza a descargar el gráfico en paralelo con los datos, así está
    // listo cuando llegan. Si falla, el bloque {#await} de abajo lo informa.
    if (location.tipo === "playa") loadTideChart().catch(() => {});
    const [w, f, t, mo, ob] = await Promise.allSettled([
      getWeather(location.slug),
      getForecast(location.slug),
      location.tipo === "playa"
        ? getTides(location.slug)
        : Promise.resolve(null),
      getModels(location.slug),
      location.observacion
        ? getObservation(location.slug)
        : Promise.resolve(null),
    ]);
    if (id !== requestId) return; // llegó tarde: ya se eligió otra localidad
    weather = value(w);
    forecast = value(f);
    tides = value(t);
    models = value(mo);
    observation = value(ob);
    errors = {
      weather: failure(w),
      forecast: failure(f),
      tides: failure(t),
      models: failure(mo),
      observation: failure(ob),
    };
    loading = false;
  }

  function navigate(location) {
    if (window.location.hash !== `#${location.slug}`) {
      window.history.pushState(null, "", `#${location.slug}`);
    }
    return select(location);
  }

  onMount(() => {
    popstateHandler = () => {
      const location = locations.find(
        (item) => item.slug === window.location.hash.slice(1),
      );
      if (location) select(location);
    };
    window.addEventListener("popstate", popstateHandler);

    return () => window.removeEventListener("popstate", popstateHandler);
  });

  onMount(async () => {
    try {
      locations = await getLocations();
      locationsLoaded = true;
      if (locations.length === 0) return;
      const slug = window.location.hash.slice(1);
      const fromHash = locations.find((location) => location.slug === slug);
      const initial = fromHash ?? locations.find((l) => l.slug === "viedma") ?? locations[0];
      if (!fromHash) {
        window.history.replaceState(null, "", `#${initial.slug}`);
      }
      await select(initial);
    } catch (e) {
      loadError = e.message;
    }
  });
</script>

<header>
  <Hero/>
  <SearchBar {locations} selectedSlug={selected?.slug} onselect={navigate} />
</header>

<main aria-busy={loading}>
  {#if loadError}
    <p class="error" role="alert">
      {loadError} Revisá que el backend esté corriendo y recargá la página.
    </p>
  {:else if locationsLoaded && locations.length === 0}
    <p class="note" role="status">No hay localidades disponibles.</p>
  {:else if selected}
    <section class="place">
      <h2>{selected.nombre}</h2>
      {#if errors.weather}
        <p class="error" role="alert">{errors.weather}</p>
        <button type="button" onclick={() => select(selected)}
          >Reintentar</button
        >
      {:else if weather}<CurrentWeather data={weather} />
      {:else}<p class="note">Cargando el clima…</p>{/if}

      {#if observation}
        <Observation data={observation} modelTemp={weather?.temp} />
      {:else if errors.observation}
        <p class="note">No se pudo obtener la observación real por ahora.</p>
      {/if}
      {#if models}
        <ModelSpread data={models} />
      {:else if errors.models}
        <p class="note">No se pudo cargar la comparación de modelos.</p>
      {/if}
    </section>

    {#if selected.tipo === "playa"}
      <section class="tides">
        <h2>Mareas</h2>
        {#if errors.tides}
          <p class="error" role="alert">{errors.tides}</p>
          <button type="button" onclick={() => select(selected)}
            >Reintentar</button
          >
        {:else if tides}
          {#await loadTideChart()}
            <p class="note">Cargando el gráfico…</p>
          {:then module}
            {@const Chart = module.default}
            <Chart {tides} />
          {:catch}
            <p class="error" role="alert">
              No se pudo cargar el gráfico. Recargá la página para reintentar.
            </p>
          {/await}
        {:else}<p class="note">Cargando las mareas…</p>{/if}
      </section>
    {/if}

    <section class="hourly">
      <h2>Próximas 24 horas</h2>
      {#if errors.forecast}
        <p class="error" role="alert">{errors.forecast}</p>
      {:else if forecast}
        {#await loadHourlyForecast()}
          <p class="note">Cargando el gráfico…</p>
        {:then module}
          {@const HourlyForecast = module.default}
          <HourlyForecast hours={forecast.horas} />
        {:catch}
          <p class="error" role="alert">No se pudo cargar el gráfico horario.</p>
        {/await}
      {:else}
        <p class="note">Cargando el pronóstico horario…</p>
      {/if}
    </section>

    <section class="forecast">
      <h2>Próximos 7 días</h2>
      {#if errors.forecast}
        <p class="error" role="alert">{errors.forecast}</p>
        <button type="button" onclick={() => select(selected)}
          >Reintentar</button
        >
      {:else if forecast}<ForecastList days={forecast.dias} stale={forecast.stale} />
      {:else}<p class="note">Cargando el pronóstico…</p>{/if}
    </section>
  {/if}
</main>

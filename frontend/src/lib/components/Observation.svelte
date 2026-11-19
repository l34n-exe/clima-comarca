<script>
  import { num, compass } from "../utils/format.js";
  let { data, modelTemp = null } = $props();

  const ago = (min) => (min < 90 ? `hace ${min} min` : `hace ${Math.round(min / 60)} h`);
  let wind = $derived(
    data.viento_kmh == null
      ? ""
      : `, viento ${data.viento_dir != null ? `del ${compass(data.viento_dir)} ` : ""}a ${num(data.viento_kmh, 0)} km/h`,
  );
</script>

{#if data.vigente}
  <p class="detail">
    Observado {ago(data.antiguedad_min)} en la estación {data.estacion} de {data.localidad}:
    {num(data.temp, 0)} °C{wind}.
    {#if modelTemp != null}El modelo estima {num(modelTemp, 0)} °C.{/if}
  </p>
{:else}
  <p class="note">
    La última observación de la estación {data.estacion} es de {ago(data.antiguedad_min)}: es demasiado
    vieja para mostrarla como actual.
  </p>
{/if}
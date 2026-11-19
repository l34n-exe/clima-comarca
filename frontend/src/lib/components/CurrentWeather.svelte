<script>
  import { num, compass } from '../utils/format.js';
  let { data } = $props();
</script>

<p class="now">{num(data.temp, 0)} °C y {data.descripcion.toLowerCase()}.</p>
<p class="detail">
  Sensación de {num(data.sensacion, 0)} °C. Viento del {compass(data.viento_dir)}
  a {num(data.viento_kmh, 0)} km/h{#if data.rafaga_kmh != null}, ráfagas de
    {num(data.rafaga_kmh, 0)} km/h{/if}. Humedad del {num(data.humedad, 0)} %.
</p>
{#if data.stale}
  <p class="note">No se pudo actualizar. Estos datos son de la última consulta exitosa.</p>
{/if}

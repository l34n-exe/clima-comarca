<script>
  import { num, compass } from '../utils/format.js';
  let { data } = $props();
</script>

<div class="card">
  <div class="main">
    <p class="temp">{num(data.temp, 0)}<span>°C</span></p>
    <p class="cond">{data.descripcion}</p>
  </div>
  <dl class="stats">
    <div><dt>Sensación</dt><dd>{num(data.sensacion, 0)} °C</dd></div>
    <div><dt>Viento</dt><dd>{compass(data.viento_dir)} a {num(data.viento_kmh, 0)} km/h</dd></div>
    {#if data.rafaga_kmh != null}
      <div><dt>Ráfagas</dt><dd>{num(data.rafaga_kmh, 0)} km/h</dd></div>
    {/if}
    <div><dt>Humedad</dt><dd>{num(data.humedad, 0)} %</dd></div>
  </dl>
</div>
{#if data.stale}
  <p class="note">No se pudo actualizar. Estos datos son de la última consulta exitosa.</p>
{/if}

<style>
  .card { display: grid; grid-template-columns: auto 1fr; gap: 1rem clamp(1.5rem, 5vw, 3.5rem); align-items: end; }
  .temp { margin: 0; font-size: clamp(4rem, 13vw, 6.5rem); font-weight: 800; line-height: 0.9; letter-spacing: -0.04em; }
  .temp span { font-size: 0.38em; font-weight: 600; letter-spacing: 0; margin-left: 0.1em; vertical-align: top; }
  .cond { margin: 0.5rem 0 0; font-size: 1.25rem; font-weight: 600; }
  .stats { margin: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(7.5rem, 1fr)); gap: 0.9rem 1.5rem; }
  .stats div { border-top: 1px solid var(--line); padding-top: 0.5rem; }
  dt { color: var(--muted); font-size: 0.85rem; }
  dd { margin: 0.1rem 0 0; font-size: 1.15rem; font-weight: 600; }
  @media (max-width: 640px) { .card { grid-template-columns: 1fr; } }
</style>

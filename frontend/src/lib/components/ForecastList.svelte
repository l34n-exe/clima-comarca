<script>
  import { dayLabel, num } from '../utils/format.js';
  let { days, stale = false } = $props();

  let lo = $derived(Math.min(...days.map((d) => d.min)));
  let hi = $derived(Math.max(...days.map((d) => d.max)));
  const pct = (v) => ((v - lo) / (hi - lo || 1)) * 100;
</script>

<div class="scroll">
  <table>
    <caption class="sr">Pronóstico de los próximos 7 días</caption>
    <thead>
      <tr><th>Día</th><th>Cielo</th><th>Temperatura</th><th>Lluvia</th><th>Viento / ráfaga máx.</th><th>Sol</th></tr>
    </thead>
    <tbody>
      {#each days as d (d.fecha)}
        <tr>
          <th scope="row">{dayLabel(d.fecha)}</th>
          <td>{d.descripcion}</td>
          <td>
            <span class="range">
              <span>{num(d.min, 0)}°</span>
              <span class="bar"><i style="left:{pct(d.min)}%;width:{Math.max(pct(d.max) - pct(d.min), 4)}%"></i></span>
              <span>{num(d.max, 0)}°</span>
            </span>
          </td>
          <td>{num(d.lluvia_mm)} mm · {num(d.prob_lluvia, 0)} %</td>
          <td>{num(d.viento_max_kmh, 0)} / {num(d.rafaga_max_kmh, 0)} km/h</td>
          <td>{d.amanecer.slice(11, 16)} / {d.atardecer.slice(11, 16)}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
{#if stale}
  <p class="note">No se pudo actualizar. Se muestran datos de la última consulta exitosa.</p>
{/if}

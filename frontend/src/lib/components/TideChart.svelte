<script>
  import { AreaChart } from 'layerchart';
  import { scaleTime } from 'd3-scale';
  import { curveMonotoneX } from 'd3-shape';
  import { hhmm, num, nowAR } from '../utils/format.js';

  let { tides } = $props();

  // Las horas llegan como texto local de Argentina. Se parsean y se muestran
  // como hora local, así el eje no depende de la zona horaria del navegador.
  const toDate = (iso) => new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  const dayText = (d) => d.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric' });
  const tickText = (d) => (d.getHours() === 0 ? dayText(d) : `${pad(d.getHours())}:00`);

  let data = $derived(tides.serie.map((p) => ({ fecha: toDate(p.hora), altura: p.altura_m })));
  let now = $derived(nowAR());
  let nowDate = $derived(toDate(now));
  let nowVisible = $derived(nowDate >= data[0].fecha && nowDate <= data[data.length - 1].fecha);

  // Cada pleamar/bajamar es un punto con su hora; el momento actual, una línea vertical
  let annotations = $derived([
    ...tides.mareas.map((m) => ({
      type: 'point',
      x: toDate(m.hora),
      y: m.altura_m,
      r: 4,
      label: hhmm(m.hora),
      labelPlacement: m.tipo === 'pleamar' ? 'top' : 'bottom',
    })),
    ...(nowVisible ? [{ type: 'line', x: nowDate, label: 'Ahora', labelPlacement: 'top-right' }] : []),
  ]);

  let upcoming = $derived(tides.mareas.filter((m) => m.hora > now).slice(0, 4));
</script>

<div class="chart">
  <AreaChart
    {data}
    x="fecha"
    y="altura"
    xScale={scaleTime()}
    series={[{ key: 'altura', label: 'Altura', value: 'altura', color: 'var(--color-primary)' }]}
    {annotations}
    props={{
      area: { curve: curveMonotoneX, line: { strokeWidth: 3 } },
      xAxis: { format: tickText },
      yAxis: { format: (v) => `${num(v, 1)} m` },
      tooltip: {
        header: { format: (d) => `${dayText(d)}, ${pad(d.getHours())}:${pad(d.getMinutes())}` },
        item: { format: (v) => `${num(v, 2)} m` },
      },
    }}
  />
</div>

<ul class="upcoming">
  {#each upcoming as m}
    <li>{m.tipo === 'pleamar' ? 'Pleamar' : 'Bajamar'} a las {hhmm(m.hora)}, {num(m.altura_m, 1)} m</li>
  {/each}
</ul>
<p class="note">Alturas respecto del nivel medio del mar. La línea vertical marca el momento actual. {tides.aviso}</p>

<style>
  /* LayerChart toma sus colores de estas variables; acá se ajustan a la banda oscura */
  .chart {
    height: 280px;
    --color-primary: var(--accent);
    --color-surface-content: var(--band-ink);
    --color-surface-100: var(--band);
  }
</style>

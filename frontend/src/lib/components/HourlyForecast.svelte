<script>
  import { num } from "../utils/format.js";

  let { hours } = $props();
  const W = 720;
  const H = 160;
  const PAD_X = 12;
  const x = (index) => PAD_X + (index * (W - 2 * PAD_X)) / (hours.length - 1 || 1);
  const yFor = (value, min, max) =>
    12 + ((max - value) / (max - min || 1)) * (H - 24);
  const line = (field, min, max) =>
    hours
      .map((hour, index) => `${x(index)},${yFor(hour[field] ?? 0, min, max)}`)
      .join(" ");

  let tempValues = $derived(hours.map((hour) => hour.temp));
  let tempMin = $derived(Math.min(...tempValues));
  let tempMax = $derived(Math.max(...tempValues));
  let windValues = $derived(hours.map((hour) => hour.viento_kmh));
  // Algunos proveedores no informan ráfagas: si ninguna hora las tiene, se oculta la serie
  let hasGusts = $derived(hours.some((hour) => hour.rafaga_kmh != null));
  let gustValues = $derived(
    hasGusts ? hours.map((hour) => hour.rafaga_kmh ?? 0) : [],
  );
  let windMax = $derived(Math.max(...windValues, ...gustValues));
  let maxWind = $derived(Math.max(...windValues));
  let maxGust = $derived(gustValues.length ? Math.max(...gustValues) : 0);
  let labels = $derived(
    hours.filter((_, index) => index % 4 === 0 || index === hours.length - 1),
  );

  const firstIndexOf = (values, target) => values.indexOf(target);
  // Mínimo y máximo de temperatura; picos de viento medio y de ráfagas
  let tempMarks = $derived([
    { index: firstIndexOf(tempValues, tempMin), value: tempMin, kind: "min" },
    { index: firstIndexOf(tempValues, tempMax), value: tempMax, kind: "max" },
  ]);
  let windMarks = $derived([
    { index: firstIndexOf(windValues, maxWind), value: maxWind, kind: "viento" },
    ...(hasGusts
      ? [{ index: firstIndexOf(gustValues, maxGust), value: maxGust, kind: "rafaga" }]
      : []),
  ]);

  // Tooltip: índice de la hora más cercana y posición horizontal en px
  let hoverTemp = $state(null);
  let hoverWind = $state(null);

  function track(event, set) {
    const rect = event.currentTarget.getBoundingClientRect();
    const px = event.clientX - rect.left;
    const index = Math.max(
      0,
      Math.min(hours.length - 1, Math.round((px / rect.width) * (hours.length - 1))),
    );
    set({ index, px: Math.min(Math.max(px, 60), rect.width - 60) });
  }
  const markPos = (index, value, min, max) => ({
    left: `${(x(index) / W) * 100}%`,
    top: `${(yFor(value, min, max) / H) * 100}%`,
  });
</script>

<div class="hourly-series">
  <p class="detail">Temperatura: {num(tempMin, 0)}–{num(tempMax, 0)} °C</p>
  <div
    class="chart-wrap"
    onpointermove={(e) => track(e, (v) => (hoverTemp = v))}
    onpointerdown={(e) => track(e, (v) => (hoverTemp = v))}
    onpointerleave={() => (hoverTemp = null)}
  >
    <svg class="hourly-chart" viewBox="0 0 720 160" preserveAspectRatio="none" role="img"
      aria-label="Curva de temperatura para las próximas 24 horas">
      <polyline
        points={line("temp", tempMin, tempMax)}
        fill="none"
        stroke="#c47a00"
        stroke-width="3"
        vector-effect="non-scaling-stroke"
      />
    </svg>
    {#each tempMarks as mark (mark.kind)}
      <span
        class="peak temp {mark.kind}"
        style:left={markPos(mark.index, mark.value, tempMin, tempMax).left}
        style:top={markPos(mark.index, mark.value, tempMin, tempMax).top}
        aria-hidden="true"
      >{num(mark.value, 0)}°</span>
    {/each}
    {#if hoverTemp}
      {@const h = hours[hoverTemp.index]}
      <div class="tip" style="left:{hoverTemp.px}px">
        {h.hora.slice(11, 16)} · {num(h.temp, 1)} °C · {num(h.prob_lluvia, 0)} % lluvia
      </div>
    {/if}
  </div>
</div>
<div class="hourly-series">
  <p class="detail">Viento: 0–{num(windMax, 0)} km/h</p>
  <div class="hourly-legend">
    <span style="--legend-color:#0866b6">Viento medio</span>
    {#if hasGusts}
      <span style="--legend-color:#8a3d8f">Ráfagas</span>
    {/if}
  </div>
  <div
    class="chart-wrap"
    onpointermove={(e) => track(e, (v) => (hoverWind = v))}
    onpointerdown={(e) => track(e, (v) => (hoverWind = v))}
    onpointerleave={() => (hoverWind = null)}
  >
    <svg class="hourly-chart" viewBox="0 0 720 160" preserveAspectRatio="none" role="img"
      aria-label="Curva de viento medio y ráfagas para las próximas 24 horas">
      <polyline
        points={line("viento_kmh", 0, windMax)}
        fill="none"
        stroke="#0866b6"
        stroke-width="2"
        vector-effect="non-scaling-stroke"
      />
      {#if hasGusts}
        <polyline
          points={line("rafaga_kmh", 0, windMax)}
          fill="none"
          stroke="#8a3d8f"
          stroke-width="2"
          stroke-dasharray="5 4"
          vector-effect="non-scaling-stroke"
        />
      {/if}
    </svg>
    {#each windMarks as mark (mark.kind)}
      <span
        class="peak {mark.kind}"
        style:left={markPos(mark.index, mark.value, 0, windMax).left}
        style:top={markPos(mark.index, mark.value, 0, windMax).top}
        aria-hidden="true"
      >{num(mark.value, 0)}</span>
    {/each}
    {#if hoverWind}
      {@const h = hours[hoverWind.index]}
      <div class="tip" style="left:{hoverWind.px}px">
        {h.hora.slice(11, 16)} · viento {num(h.viento_kmh, 0)}{#if h.rafaga_kmh != null} · ráfagas {num(h.rafaga_kmh, 0)} km/h{/if}
      </div>
    {/if}
  </div>
</div>
<div class="hourly-labels">
  {#each labels as hour (hour.hora)}
    <span>{hour.hora.slice(11, 16)}</span>
  {/each}
</div>

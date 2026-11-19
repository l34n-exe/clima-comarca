<script>
  import { num } from "../utils/format.js";

  let { hours } = $props();
  const chartWidth = 720;
  const chartHeight = 160;
  const x = (index) => 12 + (index * (chartWidth - 24)) / (hours.length - 1);
  const points = (field, min, max) =>
    hours
      .map((hour, index) => {
        const y =
          12 + ((max - hour[field]) / (max - min || 1)) * (chartHeight - 24);
        return `${x(index)},${y}`;
      })
      .join(" ");

  let tempValues = $derived(hours.map((hour) => hour.temp));
  let windValues = $derived([
    ...hours.map((hour) => hour.viento_kmh),
    ...hours.map((hour) => hour.rafaga_kmh),
  ]);
  let tempMin = $derived(Math.min(...tempValues));
  let tempMax = $derived(Math.max(...tempValues));
  let windMax = $derived(Math.max(...windValues));
  let labels = $derived(
    hours.filter((_, index) => index % 4 === 0 || index === hours.length - 1),
  );
</script>

<div class="hourly-series">
  <p class="detail">Temperatura: {num(tempMin, 0)}–{num(tempMax, 0)} °C</p>
  <svg class="hourly-chart" viewBox="0 0 720 160" preserveAspectRatio="none" role="img"
    aria-label="Curva de temperatura para las próximas 24 horas">
    <polyline
      points={points("temp", tempMin, tempMax)}
      fill="none"
      stroke="#c47a00"
      stroke-width="3"
      vector-effect="non-scaling-stroke"
    />
  </svg>
</div>
<div class="hourly-series">
  <p class="detail">Viento: 0–{num(windMax, 0)} km/h</p>
  <div class="hourly-legend">
    <span style="--legend-color:#0866b6">Viento medio</span>
    <span style="--legend-color:#8a3d8f">Ráfagas</span>
  </div>
  <svg class="hourly-chart" viewBox="0 0 720 160" preserveAspectRatio="none" role="img"
    aria-label="Curva de viento medio y ráfagas para las próximas 24 horas">
    <polyline
      points={points("viento_kmh", 0, windMax)}
      fill="none"
      stroke="#0866b6"
      stroke-width="2"
      vector-effect="non-scaling-stroke"
    />
    <polyline
      points={points("rafaga_kmh", 0, windMax)}
      fill="none"
      stroke="#8a3d8f"
      stroke-width="2"
      stroke-dasharray="5 4"
      vector-effect="non-scaling-stroke"
    />
  </svg>
</div>
<div class="hourly-labels">
  {#each labels as hour (hour.hora)}
    <span>{hour.hora.slice(11, 16)}</span>
  {/each}
</div>

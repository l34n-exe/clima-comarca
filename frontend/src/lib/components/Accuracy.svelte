<script>
  import { num } from "../utils/format.js";
  let { data } = $props();

  let maxErr = $derived(
    Math.max(0.1, ...data.por_dia.map((d) => Math.abs(d.error_c))),
  );
</script>

<section class="accuracy">
  <h2>¿Qué tan bien acierta el modelo?</h2>
  {#if data.muestras === 0}
    <p class="note">
      Todavía no hay mediciones comparadas. Se guarda una por hora cuando
      alguien consulta esta localidad.
    </p>
  {:else}
    <p class="detail">
      Error promedio de los últimos {data.dias} días:
      <strong>{num(data.error_promedio_c, 1)} °C</strong> en {data.muestras}
      mediciones horarias contra la estación METAR.
      {#if data.sesgo_c != null}
        Sesgo: {num(data.sesgo_c, 1)} °C ({data.sesgo_c > 0 ? "sobreestima" : "subestima"}).
      {/if}
    </p>
    {#if data.por_dia.length}
      <ul class="acc-days">
        {#each data.por_dia as d (d.fecha)}
          <li>
            <span class="acc-fecha">{d.fecha.slice(5)}</span>
            <span class="acc-bar"><i style="width:{Math.abs(d.error_c) / maxErr * 100}%"></i></span>
            <span class="acc-val">{num(d.error_c, 1)} °C</span>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</section>

<style>
  .accuracy h2 { font-size: 1.3rem; margin-bottom: 0.5rem; }
  .acc-days {
    list-style: none; padding: 0; margin: 0.75rem 0 0;
    display: grid; gap: 0.3rem; max-width: 30rem;
  }
  .acc-days li { display: flex; align-items: center; gap: 0.6rem; font-size: 0.85rem; }
  .acc-fecha { flex: 0 0 3.2rem; color: var(--muted); }
  .acc-bar { flex: 1; height: 8px; background: var(--line); border-radius: 4px; overflow: hidden; }
  .acc-bar i { display: block; height: 100%; background: var(--accent); border-radius: 4px; }
  .acc-val { flex: 0 0 3.6rem; text-align: right; font-weight: 600; }
</style>

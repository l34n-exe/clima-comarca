<script>
  import { num } from "../utils/format.js";
  let { data } = $props();

  let today = $derived(data.dias[0]);
  let names = $derived(Object.fromEntries(data.modelos.map((m) => [m.id, m.nombre])));
  const range = (key) => {
    const values = today.modelos.map((m) => m[key]);
    return [Math.min(...values), Math.max(...values)];
  };
  const span = ([lo, hi]) =>
    Math.round(lo) === Math.round(hi) ? `${num(lo, 0)} °C` : `${num(lo, 0)} a ${num(hi, 0)} °C`;
</script>

<details class="models">
  <summary>
    Hoy, según {today.modelos.length} modelos: máxima de {span(range("max"))} y mínima de {span(range("min"))}.
  </summary>
  <ul>
    {#each today.modelos as m (m.modelo)}
      <li><span>{names[m.modelo]}</span> <span>{num(m.max, 0)}° / {num(m.min, 0)}°</span></li>
    {/each}
  </ul>
  {#if data.stale}
    <p class="note">No se pudo actualizar. Estos datos son de la última consulta exitosa.</p>
  {/if}
</details>

<style>
  details { margin-top: 0.75rem; }
  summary { cursor: pointer; color: var(--muted); }
  ul { list-style: none; padding: 0; margin: 0.5rem 0 0; max-width: 22rem; }
  li { display: flex; justify-content: space-between; gap: 1rem; padding: 0.25rem 0; border-bottom: 1px solid var(--line); }
</style>
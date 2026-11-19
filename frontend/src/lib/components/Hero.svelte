<script>
  import LighthouseMark from "./LighthouseMark.svelte";
</script>

<div class="hero">
  <div class="mark"><LighthouseMark /></div>
  <div class="text">
    <h1>Comarca Weather</h1>
    <p>Viedma, Carmen de Patagones y las playas de la costa.</p>
    <!-- Las tres franjas de la bandera de Río Negro: azul, blanco y verde -->
    <div class="stripes" aria-hidden="true"><i class="b"></i><i class="w"></i><i class="g"></i></div>
  </div>
</div>

<style>
  .hero { display: flex; align-items: center; gap: clamp(1rem, 4vw, 2.5rem); margin-bottom: 1.75rem; }
  .mark {
    flex: 0 0 auto; width: clamp(128px, 24vw, 208px); aspect-ratio: 1;
    border-radius: 10px; overflow: hidden; box-shadow: 0 0 0 1.5px var(--line, #333);
  }
  h1 { margin: 0; font-size: clamp(2.1rem, 6.5vw, 3.8rem); line-height: 1; font-weight: 800; letter-spacing: -0.03em; }
  p { margin: 0.6rem 0 0; color: var(--muted, #9aa); max-width: 34ch; }
  .stripes { display: grid; gap: 3px; width: min(240px, 100%); margin-top: 1.1rem; }
  .stripes i { display: block; height: 6px; }
  .b { background: var(--band, #0a5aa8); }
  .w { background: var(--band-ink, #eef3f5); }
  .g { background: var(--accent, #12a150); }
  @media (max-width: 520px) { .hero { flex-direction: column; align-items: flex-start; } }
</style>

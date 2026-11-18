# Kitaly menu study — local only

Run from the repository root:

```sh
python3 -m http.server 5012 --bind 127.0.0.1
```

Open http://127.0.0.1:5012/local-menu/ . The panel opens immediately. Close it to inspect the catalogue context, then use Menu to reopen it.

Direction: a wide editorial navigation panel with league and curated columns, a real Player Issue photograph, warm white and charcoal surfaces, and a restrained gold selection marker. On phones the sections stack and the photograph is omitted to keep navigation compact. The original Kitaly crest and Libre Franklin / Cormorant Garamond fonts are reused.

All stock, league and curated links filter the local sample catalogue. Escape, close and backdrop dismissal use a native dialog with keyboard focus restoration. English / Italian and light / dark controls work locally. The sample contains actual public catalogue entries captured when this study was built; it is not a live inventory. No checkout or remote writes are connected.

Audit and passes: replaced tracked uppercase labels with sentence case; removed repeated dividers and decorative category icons; aligned navigation on a 4px spacing grid; condensed boxed preferences into quiet text controls; moved desktop navigation into two readable columns; retained purposeful 180ms entrance motion and a reduced-motion fallback. No generated imagery was needed: the shirt itself carries the colour.

Production templates and styles are untouched. This directory is a standalone prototype, not included in the Flask application.

Design process based on **unslop by Damir Sokolovsky ([@heydamir](https://x.com/heydamir))**, CC BY 4.0. This credit applies to the method and adaptations, not to Kitaly's brand assets or product photography.

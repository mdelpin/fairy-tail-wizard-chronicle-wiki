# Wiki site (Astro)

Static site built from the JSON in `src/data/`, which `tools/converter/convert.py` generates from a Capacities export.

```
npm install
npm run dev      # local preview at http://localhost:4321/fairy-tail-wizard-chronicle-wiki/
npm run build    # writes dist/
```

Pages: home, wizard roster (`/characters/`), one page per wizard, the Effect Finder (`/effects/` and one page
per effect), and lacrimas. Portraits live in `public/portraits/<wizard id>.webp` (640px WebP).

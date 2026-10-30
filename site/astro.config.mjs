import { defineConfig } from 'astro/config';

// Published on GitHub Pages under the repository name.
export default defineConfig({
  site: 'https://mdelpin.github.io',
  base: '/fairy-tail-wizard-chronicle-wiki',
  trailingSlash: 'always',
  build: { format: 'directory' },
  // Astro 7 defaults to 'jsx', which drops whitespace between elements and glues words together.
  compressHTML: true,
});

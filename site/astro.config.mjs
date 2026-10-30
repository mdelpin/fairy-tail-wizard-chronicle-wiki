import { defineConfig } from 'astro/config';

// Published on GitHub Pages under the repository name.
export default defineConfig({
  site: 'https://mdelpin.github.io',
  base: '/fairy-tail-wizard-chronicle-wiki',
  trailingSlash: 'always',
  build: { format: 'directory' },
});

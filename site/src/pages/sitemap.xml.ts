import type { APIRoute } from 'astro';
import { units, buildFinderIndex } from '../lib/data';

// Every page of the wiki, so search engines find them without following links one by one.
export const GET: APIRoute = ({ site }) => {
  const base = (import.meta.env.BASE_URL.replace(/\/?$/, '/'));
  const abs = (path: string) => new URL(base + path, site).href;
  const paths = [
    '', 'characters/', 'effects/', 'lacrimas/', 'banners/', 'search/',
    ...units.map((u) => `characters/${u.id}/`),
    ...[...buildFinderIndex().meta.values()].map((m) => `effects/${m.key}/`),
  ];
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n`
    + paths.map((p) => `  <url><loc>${abs(p)}</loc></url>`).join('\n') + '\n</urlset>\n';
  return new Response(body, { headers: { 'Content-Type': 'application/xml' } });
};

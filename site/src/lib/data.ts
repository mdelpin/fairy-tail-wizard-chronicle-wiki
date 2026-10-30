// Typed access to the JSON the converter writes (tools/converter/convert.py).
import unitsJson from '../data/units.json';
import appsJson from '../data/applications.json';
import effectsJson from '../data/effects.json';
import lacrimasJson from '../data/lacrimas.json';

export interface Effect {
  id: string; name: string; family: string | null; direction: string | null; tier: string | null;
  polarity: string | null; mechanic: string | null;
  value: { amount: number; unit: string } | null;
  secondary: { stat: string; direction: string; amount: number; unit: string } | null;
  gameText: string | null;
}
export interface Application {
  id: string; source: 'unit' | 'lacrima'; effect: string | null; type: string | null; target: string | null;
  trigger: { events: string[]; everySeconds: number | null; raw: string } | null;
  chance: number | null; durationSeconds: number | null;
  valueOverride: { amount: number; unit: string } | null;
  condition: string | null;
  requires: { families: string[]; match: string | null } | null;
  gameText: string | null;
}
export interface Skill {
  kind: 'Normal' | 'Special' | 'Ultimate'; name: string | null; attackRange: string | null;
  gameText: Record<string, string>; applications: string[];
}
export interface Unit {
  id: string; name: string; identity: string | null; collection: string | null; rarity: string | null;
  attribute: Attribute; role: string | null; portrait: string | null; signatureLacrima: string | null;
  skills: Skill[];
}
export interface Lacrima {
  id: string; name: string; kind: 'signature' | 'generic'; signatureFor: string | null;
  gameText: string | null; applications: string[];
}
export type Attribute = 'Brave' | 'Mind' | 'Technique' | 'Heart';

export const units = (unitsJson as Unit[]).slice().sort((a, b) => a.name.localeCompare(b.name));
export const applications = new Map((appsJson as Application[]).map((a) => [a.id, a]));
export const effects = new Map((effectsJson as Effect[]).map((e) => [e.id, e]));
export const lacrimas = (lacrimasJson as Lacrima[]).slice().sort((a, b) => a.name.localeCompare(b.name));
export const unitById = new Map(units.map((u) => [u.id, u]));
export const lacrimaById = new Map(lacrimas.map((l) => [l.id, l]));

export const url = (path: string) => import.meta.env.BASE_URL.replace(/\/?$/, '/') + path.replace(/^\//, '');

/** Unit ids that have a portrait in public/portraits (read at build time). */
import fs from 'node:fs';
export const portraits = new Set(
  fs.existsSync('public/portraits') ? fs.readdirSync('public/portraits').map((f) => f.replace(/\.webp$/, '')) : [],
);

// ---------- attributes ----------
export const ATTR: Record<Attribute, { kanji: string; color: string; text: string; tint: string; alt: string }> = {
  Brave: { kanji: '勇', color: '#B83A26', text: '#9E3020', tint: '184,58,38', alt: 'also shown in game as Valor or Courage' },
  Mind: { kanji: '知', color: '#2C64A8', text: '#24558F', tint: '44,100,168', alt: 'also shown in game as Wisdom' },
  Technique: { kanji: '技', color: '#2D7F4F', text: '#256B42', tint: '45,127,79', alt: 'also shown in game as Skill' },
  Heart: { kanji: '心', color: '#9A700C', text: '#7A5A0A', tint: '154,112,12', alt: '' },
};
export const ATTR_ORDER: Attribute[] = ['Brave', 'Mind', 'Technique', 'Heart'];
export const ROLES = ['Melee', 'Ranged', 'Disrupt', 'Heal', 'Defense'];
export const KIND_ORDER = ['Normal', 'Special', 'Ultimate'];

// ---------- effects ----------
export const TIER_ORDER = ['Top', 'High', 'Mid', 'Low'];

/** "Top Burn" -> "Burn"; "High ATK Increase" -> "ATK Increase" */
export function baseName(e: Effect): string {
  return e.tier && TIER_ORDER.includes(e.tier) ? e.name.replace(new RegExp('^' + e.tier + '\\s+'), '') : e.name;
}
export function direction(e: Effect): 'Up' | 'Down' | null {
  if (e.direction === 'Up' || e.direction === 'Down') return e.direction;
  if (/Increase|Up\b/.test(e.name)) return 'Up';
  if (/Decrease|Down\b/.test(e.name)) return 'Down';
  return null;
}

const UNIT_SHORT: Record<string, string> = {
  'Percent of own ATK': '% ATK', 'Percent of Own ATK': '% ATK', 'Percent of ATK per sec': '% ATK/s',
  'Percentage of Source ATK per second': '% ATK/s', 'Percent': '%', 'Seconds': 's',
  'Percent of Max HP': '% max HP', 'Percent of HP Lost': '% HP lost', 'Flat Value': '',
};
const short = (u: string) => UNIT_SHORT[u] ?? ' ' + u;

/** Value shown in effect tables: the application's own value, else the effect's default (+ secondary stat). */
export function valueText(a: Application, e: Effect | undefined): string {
  const parts: string[] = [];
  const sign = e && e.mechanic === 'Stat Modifier' ? (direction(e) === 'Down' ? '−' : '+') : '';
  const v = a.valueOverride ?? e?.value ?? null;
  if (v) parts.push(`${sign}${v.amount}${short(v.unit)}`);
  if (e?.secondary) {
    const s = e.secondary;
    parts.push(`${s.stat} ${s.direction === 'Down' ? '−' : '+'}${s.amount}${short(s.unit)}`);
  }
  return parts.join(' · ') || '—';
}

// ---------- effect families for the finder ----------
export interface FamilyMeta { key: string; label: string; family: string; dir?: 'Up' | 'Down'; group: string; color: string; icon: string }
const ICON: Record<string, string> = {
  flame: 'M12 3c1 3 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-5 .5 1.5 1.3 2.5 2.2 3C11.5 9 11 6 12 3z',
  drop: 'M12 3c3 4.5 6 8 6 11a6 6 0 0 1-12 0c0-3 3-6.5 6-11z',
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7z',
  mute: 'M4 9v6h4l5 4V5L8 9zM16 9l5 6M21 9l-5 6',
  chain: 'M9 15l6-6M7.5 12.5l-2 2a3 3 0 0 0 4 4l2-2M16.5 11.5l2-2a3 3 0 0 0-4-4l-2 2',
  snow: 'M12 2v20M3.3 7l17.4 10M20.7 7 3.3 17M9 4l3 2 3-2M9 20l3-2 3 2',
  blind: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM3 3l18 18',
  target: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
  healblock: 'M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10zM4 4l16 16',
  up: 'M12 19V5M6 11l6-6 6 6',
  down: 'M12 5v14M6 13l6 6 6-6',
  heal: 'M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10zM12 9v6M9 12h6',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  sparkle: 'M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z',
  barrier: 'M4 5h16v14H4zM4 12h16M12 5v14',
  star: 'M12 2l3 7 7 .6-5.3 4.7 1.6 7.2L12 17.8 5.7 21.5l1.6-7.2L2 9.6 9 9z',
  gauge: 'M4 17a8 8 0 1 1 16 0M12 17l4-6',
  reflect: 'M4 12h12M12 6l6 6-6 6M20 4v16',
};
const AILMENTS: Record<string, [string, string]> = {
  Burn: ['#C2471F', 'flame'], Bleed: ['#8E1B2C', 'drop'], Paralysis: ['#B88A00', 'bolt'],
  Silence: ['#6B4FA0', 'mute'], 'Heal Block': ['#7A2E5A', 'healblock'], Bind: ['#4F6475', 'chain'],
  Freeze: ['#2C7FA8', 'snow'], Blind: ['#4A4A4A', 'blind'], Taunt: ['#B5651D', 'target'],
};
const SUPPORT: Record<string, string> = {
  Heal: 'heal', Shield: 'shield', Cleanse: 'sparkle', 'Action Block Barrier': 'barrier',
  'Critical Shield': 'shield', Invincible: 'star', 'Damage Reflection': 'reflect',
};
const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

/** The finder key an effect belongs to, or null when it isn't listed (base Damage, Transformation). */
export function familyKey(e: Effect): FamilyMeta | null {
  const f = e.family;
  if (!f || f === 'Damage' || f === 'Transformation') return null;
  if (AILMENTS[f]) return { key: slug(f), label: f, family: f, group: 'Status ailments', color: AILMENTS[f][0], icon: ICON[AILMENTS[f][1]] };
  if (e.mechanic === 'Stat Modifier') {
    const d = direction(e) ?? 'Up';
    return d === 'Up'
      ? { key: slug(f) + '-up', label: f + ' ↑', family: f, dir: 'Up', group: 'Stat boosts', color: '#8A6A1E', icon: ICON.up }
      : { key: slug(f) + '-down', label: f + ' ↓', family: f, dir: 'Down', group: 'Stat cuts', color: '#9E3B2A', icon: ICON.down };
  }
  if (f.includes('Gauge')) return { key: slug(f), label: f, family: f, group: 'Skill gauges', color: '#2F5D8A', icon: ICON.gauge };
  return { key: slug(f), label: f, family: f, group: 'Support', color: '#2D7F4F', icon: ICON[SUPPORT[f] ?? 'sparkle'] };
}
export const GROUPS = [
  ['Status ailments', 'Damage over time and control'],
  ['Stat boosts', 'Increases for yourself and allies'],
  ['Stat cuts', 'Decreases on enemies'],
  ['Support', 'Healing and protection'],
  ['Skill gauges', 'Speed up allies, slow down enemies'],
] as const;

export interface Match { unit: Unit; skill: Skill; app: Application; effect: Effect }
export interface LacrimaMatch { lacrima: Lacrima; app: Application; effect: Effect }

/** Everything the finder knows, indexed by family key. Built once at build time. */
export function buildFinderIndex() {
  const meta = new Map<string, FamilyMeta>();
  const applies = new Map<string, Match[]>();
  const fromLacrimas = new Map<string, LacrimaMatch[]>();
  const needs = new Map<string, { unit: Unit; skill: Skill; app: Application }[]>();
  const push = <T>(m: Map<string, T[]>, k: string, v: T) => (m.get(k) ?? m.set(k, []).get(k)!).push(v);

  for (const unit of units) for (const skill of unit.skills) for (const id of skill.applications) {
    const app = applications.get(id); if (!app) continue;
    const effect = app.effect ? effects.get(app.effect) : undefined;
    const fm = effect && familyKey(effect);
    if (effect && fm) { meta.set(fm.key, fm); push(applies, fm.key, { unit, skill, app, effect }); }
    for (const fam of app.requires?.families ?? []) {
      if (AILMENTS[fam]) push(needs, slug(fam), { unit, skill, app });
    }
  }
  for (const lacrima of lacrimas) for (const id of lacrima.applications) {
    const app = applications.get(id); if (!app) continue;
    const effect = app.effect ? effects.get(app.effect) : undefined;
    const fm = effect && familyKey(effect);
    if (effect && fm) { meta.set(fm.key, fm); push(fromLacrimas, fm.key, { lacrima, app, effect }); }
  }
  return { meta, applies, fromLacrimas, needs };
}

export const tierRank = (t: string | null) => (t ? TIER_ORDER.indexOf(t) : 9);
export const initials = (name: string) =>
  name.replace(/-.*-/, '').split(' ').filter(Boolean).slice(-2).map((w) => w[0]).join('');

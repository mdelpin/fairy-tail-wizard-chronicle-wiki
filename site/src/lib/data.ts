// Typed access to the JSON the converter writes (tools/converter/convert.py).
import unitsJson from '../data/units.json';
import appsJson from '../data/applications.json';
import effectsJson from '../data/effects.json';
import familiesJson from '../data/families.json';
import lacrimasJson from '../data/lacrimas.json';
import bannersJson from '../data/banners.json';
import companionsJson from '../data/companions.json';
import enemiesJson from '../data/enemies.json';
import eventsJson from '../data/events.json';

export interface Effect {
  id: string; name: string; family: string | null; direction: string | null; tier: string | null;
  polarity: string | null; mechanic: string | null;
  value: { amount: number; unit: string } | null;
  secondary: { stat: string; direction: string; amount: number; unit: string } | null;
  gameText: string | null;
}
/** What never varies between the tiers of an effect. Mechanic, Definition and Affected Stats are read from the Effect Family object in Capacities. */
export interface EffectFamily {
  id: string; name: string; definition: string | null; mechanic: string | null;
  /** Display names of the Parameters (stats) the family changes, e.g. ['HP', 'ATK']. */
  affectedStats: string[];
  /** Families this one counters / is countered by, as entered in Capacities (the two sides stay in sync there). */
  counters: string[]; counteredBy: string[];
  /** 'Debuffs' or 'Buffs' for the Remove All families; null otherwise. */
  removes: string | null;
}
export interface Application {
  id: string; source: 'unit' | 'lacrima' | 'enemy'; effect: string | null; type: string | null; target: string | null;
  trigger: { events: string[]; everySeconds: number | null; raw: string } | null;
  chance: number | null; durationSeconds: number | null;
  valueOverride: { amount: number; unit: string } | null;
  condition: string | null;
  requires: { families: string[]; match: string | null; subject?: string | null } | null;
  gameText: string | null;
}
export interface CompanionApplication extends Pick<Application, 'id' | 'effect' | 'type' | 'target' | 'trigger' | 'chance' | 'durationSeconds' | 'valueOverride' | 'condition' | 'gameText'> {
  source: 'companion';
}
export interface Companion {
  id: string; name: string; type: string | null; rarity: string | null; image: string | null;
  /** Same word on the cards of one character; compared only within one companion type, never with wizards. */
  identity: string | null;
  introducedOn: string | null; introducedVia: string | null; introducedBanner: string | null;
  skillName: string | null; skillLevelFromStars: number[];
  ownedStat: string | null; ownedStart: number | null; ownedStep: number | null;
  /** false = the step per star is inferred, not seen in game; null = nothing recorded. */
  stepConfirmed: boolean | null;
  levelTextSource: string | null;
  /** Lv1..Lv3 text as recorded; a card may have only Lv1. */
  gameText: Record<string, string>;
  issues: KnownIssue[];
  applications: string[];
}
export const COMPANION_TYPES = ['Celestial Spirit', 'Exceed', 'Dragon'] as const;
export const MAX_COMPANION_STARS = 11;
/** A live, reported fault in the game's own data; `note` is the editor's public wording. */
export interface KnownIssue { problemType: string | null; note: string }
export interface Skill {
  kind: 'Normal' | 'Special' | 'Ultimate'; name: string | null; attackRange: string | null;
  gameText: Record<string, string>; applications: string[];
  /** Editor's note (not game text). */
  notes?: string | null;
  /** Live reported faults in the game's text or numbers for this skill. */
  issues?: KnownIssue[];
  /** Game icon number (public/icons/skill/NN.webp), when recorded. */
  icon?: number | null;
  /** Where the Lv.1–2 text came from: 'madochro.wiki.gg' (credited) or 'In game'. */
  levelTextSource?: string | null;
}
export const WIKI_CREDIT = { name: 'madochro.wiki.gg', href: 'https://madochro.wiki.gg/', license: 'CC BY-SA 4.0', licenseHref: 'https://creativecommons.org/licenses/by-sa/4.0/' };
export interface Unit {
  id: string; name: string; identity: string | null; collection: string | null; rarity: string | null;
  attribute: Attribute; role: string | null; portrait: string | null; signatureLacrima: string | null;
 /** Stat the wizard's Collection screen bonus raises. The % per Level/Awaken step follows rarity (see COLLECTION_BONUS_PCT). */
  collectionBonusStat: 'ATK' | 'HP' | 'DEF' | null;
  /** Collection name starts with "New Form" (the game spreads them over several). */
  newForm: boolean;
  /** The banner the unit first became obtainable on, if recorded. */
  debutBanner: string | null;
  /** JST day (YYYY-MM-DD) the unit first became obtainable; later than the banner's start for a themed week's second wizard. */
  availableFrom: string | null;
  /** File name in public/banner-art/, if the unit's gacha art is recorded. */
  bannerArt: string | null;
  /** File name in public/cards/: the full release card (art, sprite, name plate), if recorded. */
  card?: string | null;
  skills: Skill[];
}
export interface Banner {
  id: string; name: string; type: string | null;
  /** Official JST days, YYYY-MM-DD. */
  start: string | null; end: string | null;
  /** 'Confirmed' (game or official post) or 'Calculated' (two-week rhythm); null when no date is known. */
  dateSource: string | null;
  units: string[];
  companions?: string[];
  /** File name in public/event-banners/: the event banner (cover image), if recorded. */
  cover?: string | null;
}
export interface Lacrima {
  id: string; name: string; kind: 'signature' | 'generic'; signatureFor: string | null;
  gameText: string | null; applications: string[];
  /** Editor's note (not game text), e.g. behaviour tested in play. */
  notes?: string | null;
  /** Live reported faults in this lacrima's text or effect. */
  issues?: KnownIssue[];
}
export interface EnemySkill {
  kind: 'Normal' | 'Special' | 'Ultimate' | 'Additional'; name: string | null;
  icon: number | null; gameText: string | null; applications: string[];
}
export interface Enemy {
  id: string; name: string; type: string | null; role: string | null; image: string | null;
  /** Points a minion gives toward the Defeat Points gauge that summons the boss; null for a boss. */
  defeatPoints: number | null;
  /** What the golden version of a minion gives, and its picture; null until one has been seen. */
  goldenDefeatPoints: number | null; goldenImage: string | null;
  immuneTo: string[]; events: string[]; skills: EnemySkill[];
}
export interface GameEvent {
  id: string; name: string; type: string | null; start: string | null; end: string | null;
  /** Exact UTC moments, 'YYYY-MM-DDTHH:MMZ'; null when Capacities holds only a day. */
  startAt: string | null; endAt: string | null; rankingStartAt: string | null; rankingEndAt: string | null;
  image: string | null; dateSource: string | null; dateNote: string | null; enemies: string[];
}
export type Attribute = 'Brave' | 'Mind' | 'Technique' | 'Heart';

export const units = (unitsJson as Unit[]).slice().sort((a, b) => a.name.localeCompare(b.name));
const allApplications = appsJson as (Application | CompanionApplication)[];
export const applications = new Map(allApplications.filter((a) => a.source === 'unit' || a.source === 'lacrima').map((a) => [a.id, a]));
export const companionApplications = new Map(allApplications.filter((a) => a.source === 'companion').map((a) => [a.id, a]));
export const enemyApplications = new Map(allApplications.filter((a) => a.source === 'enemy').map((a) => [a.id, a]));
export const enemies = (enemiesJson as Enemy[]).slice().sort((a, b) => a.name.localeCompare(b.name));
export const events = new Map((eventsJson as GameEvent[]).map((e) => [e.id, e]));
export const companions = (companionsJson as Companion[]).slice().sort((a, b) => a.name.localeCompare(b.name));
export const companionById = new Map(companions.map((c) => [c.id, c]));
export const effects = new Map((effectsJson as Effect[]).map((e) => [e.id, e]));
export const families = new Map((familiesJson as EffectFamily[]).map((f) => [f.name, f]));
export const lacrimas = (lacrimasJson as Lacrima[]).slice().sort((a, b) => a.name.localeCompare(b.name));
export const unitById = new Map(units.map((u) => [u.id, u]));
export const lacrimaById = new Map(lacrimas.map((l) => [l.id, l]));
/** Oldest first; banners without a date at the end. */
export const banners = bannersJson as Banner[];
export const bannerById = new Map(banners.map((b) => [b.id, b]));

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
/** '2026-03-06' -> '6 Mar 2026' (a JST calendar day, shown as written; no time-zone shift). */
export const dayText = (d: string) => { const [y, m, dd] = d.split('-').map(Number); return `${dd} ${MONTHS[m - 1]} ${y}`; };
/** '2026-11-05T06:00Z' -> '5 Nov 2026, 06:00 UTC' (an exact moment, shown in UTC as the game's notice states it). */
export const utcText = (iso: string) => `${dayText(iso.slice(0, 10))}, ${iso.slice(11, 16)} UTC`;
/** 'Calculated' dates get an ≈ so readers can tell them from confirmed ones. */
export const bannerDates = (b: Banner) => {
  if (!b.start) return null;
  const approx = b.dateSource === 'Calculated' ? '≈ ' : '';
  return approx + dayText(b.start) + (b.end ? ` – ${dayText(b.end)}` : '');
};
/** A unit's own first-available date wins over the banner's start; the end stays the banner's. */
export const unitDates = (u: Unit, b?: Banner) => {
  if (!u.availableFrom) return b ? bannerDates(b) : null;
  // while the banner's own dates are still estimated, so is the day derived from them
  const approx = b?.dateSource === 'Calculated' ? '≈ ' : '';
  return approx + dayText(u.availableFrom) + (b?.end ? ` – ${dayText(b.end)}` : '');
};
/** JST day the game went live; wizards available from then have no debut banner. */
export const LAUNCH_DAY = '2025-12-03';
/** Wizard rarities, best first. Filters list only those present in the data. */
/** Collection bonus per Level or Awaken milestone, by rarity (N 1, R and SR 3, UR 5; confirmed in game). */
export const COLLECTION_BONUS_PCT: Record<string, number> = { N: 1, R: 3, SR: 3, UR: 5 };
/** Milestones on the Collection screen: Level 10, 20 ... 100 and Awaken 1 ... 11. */
export const COLLECTION_LEVEL_STEPS = 10;
export const COLLECTION_AWAKEN_STEPS = 11;
export const RARITIES = ['UR', 'SR', 'R', 'N'] as const;
export const raritiesIn = (list: { rarity: string | null }[]) => RARITIES.filter((r) => list.some((u) => u.rarity === r));
export const DATE_NOTE = '≈ estimated from the two-week banner cycle. Japan time; banners change at 15:00 JST.';

export const url = (path: string) => import.meta.env.BASE_URL.replace(/\/?$/, '/') + path.replace(/^\//, '');

/** Unit ids that have a portrait in public/portraits (read at build time). */
import fs from 'node:fs';
export const portraits = new Set(
  fs.existsSync('public/portraits') ? fs.readdirSync('public/portraits').map((f) => f.replace(/\.webp$/, '')) : [],
);

// ---------- attributes ----------
export const ATTR: Record<Attribute, { kanji: string; color: string; text: string; tint: string; alt: string }> = {
  Brave: { kanji: '勇', color: '#B83A26', text: '#9E3020', tint: '184,58,38', alt: 'also shown in game as Valor, Courage or Brv' },
  Mind: { kanji: '知', color: '#2C64A8', text: '#24558F', tint: '44,100,168', alt: 'also shown in game as Wisdom or Int' },
  Technique: { kanji: '技', color: '#2D7F4F', text: '#256B42', tint: '45,127,79', alt: 'also shown in game as Skill or Tech' },
  Heart: { kanji: '心', color: '#9A700C', text: '#7A5A0A', tint: '154,112,12', alt: '' },
};
export const ATTR_ORDER: Attribute[] = ['Brave', 'Mind', 'Technique', 'Heart'];
export const ROLES = ['Melee', 'Ranged', 'Disrupt', 'Heal', 'Defense'];
/** Role icons from the game, in public/icons/role/. */
export const roleIcon = (role: string | null) => (role && ROLES.includes(role) ? url(`icons/role/${role.toLowerCase()}.webp`) : null);
/** A skill's icon, only when it has been recorded from the game (no guessing from attribute or range). */
export const skillIcon = (_u: Unit, s: Skill) => (s.icon ? url(`icons/skill/${String(s.icon).padStart(2, '0')}.webp`) : null);
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
  "Percent of Party's Average ATK": "% of party's average ATK", "Percent of Target's ATK": "% of target's ATK",
};
const short = (u: string) => UNIT_SHORT[u] ?? ' ' + u;

/** Value shown in effect tables: the application's own value, else the effect's default (+ secondary stat). */
export function valueText(a: Pick<Application, 'valueOverride'>, e: Effect | undefined): string {
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
export interface FamilyMeta {
  key: string; label: string; family: string; dir?: 'Up' | 'Down'; group: string; color: string; icon: string;
  /** Mechanic of the family and Polarity of this page's effects; the counter rules use both. */
  mechanic: string | null; polarity: string | null;
}
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
  Heal: 'heal', Shield: 'shield', 'Action Block Barrier': 'barrier',
  'Critical Shield': 'shield', Invincible: 'star', 'Damage Reflection': 'reflect',
};
const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

/** The finder key an effect belongs to, or null when it isn't listed (base Damage, Transformation). */
export function familyKey(e: Effect): FamilyMeta | null {
  const f = e.family;
  if (!f || f === 'Damage' || f === 'Transformation') return null;
  const base = { family: f, mechanic: e.mechanic, polarity: e.polarity };
  if (AILMENTS[f]) return { ...base, key: slug(f), label: f, group: 'Status ailments', color: AILMENTS[f][0], icon: ICON[AILMENTS[f][1]] };
  // Stat Modifier families and Gauge Modifier families split into an Up and a Down page
  if (e.mechanic === 'Stat Modifier') {
    const d = direction(e) ?? 'Up';
    return d === 'Up'
      ? { ...base, key: slug(f) + '-up', label: f + ' ↑', dir: 'Up', group: 'Stat boosts', color: '#8A6A1E', icon: ICON.up }
      : { ...base, key: slug(f) + '-down', label: f + ' ↓', dir: 'Down', group: 'Stat cuts', color: '#9E3B2A', icon: ICON.down };
  }
  if (e.mechanic === 'Gauge Modifier') {
    const d = direction(e) ?? 'Up';
    return { ...base, key: slug(f) + (d === 'Up' ? '-up' : '-down'), label: f + (d === 'Up' ? ' ↑' : ' ↓'), dir: d, group: 'Skill gauges', color: '#2F5D8A', icon: ICON.gauge };
  }
  if (e.mechanic === 'Removal') return { ...base, key: slug(f), label: f, group: 'Dispels', color: '#5B4B8A', icon: ICON.sparkle };
  return { ...base, key: slug(f), label: f, group: 'Support', color: '#2D7F4F', icon: ICON[SUPPORT[f] ?? 'sparkle'] };
}
export const GROUPS = [
  ['Status ailments', 'Damage over time and control'],
  ['Stat boosts', 'Increases for yourself and allies'],
  ['Stat cuts', 'Decreases on enemies'],
  ['Support', 'Healing and protection'],
  ['Dispels', 'Remove all buffs or debuffs'],
  ['Skill gauges', 'Speed up allies, slow down enemies'],
] as const;

/**
 * What a family page says about the family itself: its Definition when one is entered, otherwise, for a
 * Stat Modifier family, a line built from its Affected Stats ("Modifies ATK"). Stat families have no
 * Definition on purpose, since Mechanic and Affected Stats already say it all.
 */
export function familyBlurb(name: string): string | null {
  const f = families.get(name);
  if (!f) return null;
  if (f.definition) return f.definition;
  if (f.mechanic === 'Stat Modifier' && f.affectedStats.length) return `Modifies ${f.affectedStats.join(' and ')}`;
  return null;
}

/**
 * Mechanics that last for a while, so Remove All Debuffs / Remove All Buffs can take them off. Instant
 * damage and healing, other removals and gauge changes are over as soon as they happen. Prevention,
 * Mitigation and Reactive Damage (Damage Reflection) are left out on purpose: whether the Remove All
 * effects strip barriers, shields or a reflect is not confirmed in game, so those pairs show only when
 * entered as Counters in Capacities.
 */
const LASTING = new Set(['Stat Modifier', 'Damage Over Time', 'Control', 'Heal Over Time']);

export interface CounterLink { key: string; label: string }
/**
 * Who counters whom, per finder page. Three sources, all read from the Effect Family objects:
 * Counters (the family counters these), Countered By (the family is countered by these; the two stay in
 * sync in Capacities), and Removes (Debuffs or Buffs): a family that removes Debuffs counters every page
 * of a lasting Mechanic whose effects are Harmful, and Buffs mirrors that with Beneficial.
 * A page with no entry means "not recorded", never "nothing counters it".
 */
export function buildCounterIndex() {
  const metas = new Map<string, FamilyMeta>();
  for (const e of effects.values()) { const fm = familyKey(e); if (fm) metas.set(fm.key, fm); }
  const pagesOf = new Map<string, FamilyMeta[]>();
  for (const m of metas.values()) (pagesOf.get(m.family) ?? pagesOf.set(m.family, []).get(m.family)!).push(m);
  const edges = new Set<string>();
  const add = (counter: FamilyMeta, target: FamilyMeta) => { if (counter.key !== target.key) edges.add(`${counter.key}>${target.key}`); };
  for (const f of families.values()) {
    const mine = pagesOf.get(f.name) ?? [];
    for (const name of f.counters) for (const c of mine) for (const t of pagesOf.get(name) ?? []) add(c, t);
    for (const name of f.counteredBy) for (const t of mine) for (const c of pagesOf.get(name) ?? []) add(c, t);
    if (f.removes === 'Debuffs' || f.removes === 'Buffs') {
      const wanted = f.removes === 'Debuffs' ? 'Harmful' : 'Beneficial';
      for (const c of mine) for (const t of metas.values()) if (t.polarity === wanted && t.mechanic && LASTING.has(t.mechanic)) add(c, t);
    }
  }
  const counteredBy = new Map<string, CounterLink[]>();
  const counters = new Map<string, CounterLink[]>();
  const push = (m: Map<string, CounterLink[]>, k: string, l: CounterLink) => (m.get(k) ?? m.set(k, []).get(k)!).push(l);
  for (const edge of edges) {
    const [c, t] = edge.split('>');
    const cm = metas.get(c)!, tm = metas.get(t)!;
    push(counteredBy, t, { key: cm.key, label: cm.label });
    push(counters, c, { key: tm.key, label: tm.label });
  }
  for (const m of [counteredBy, counters]) for (const l of m.values()) l.sort((a, b) => a.label.localeCompare(b.label));
  return { counteredBy, counters };
}

export interface Match { unit: Unit; skill: Skill; app: Application; effect: Effect }
export interface LacrimaMatch { lacrima: Lacrima; app: Application; effect: Effect }
export interface CompanionMatch { companion: Companion; app: CompanionApplication; effect: Effect }

/** Everything the finder knows, indexed by family key. Built once at build time. */
export function buildFinderIndex(includeCompanions = false) {
  const meta = new Map<string, FamilyMeta>();
  const applies = new Map<string, Match[]>();
  const fromLacrimas = new Map<string, LacrimaMatch[]>();
  const fromCompanions = new Map<string, CompanionMatch[]>();
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
  if (includeCompanions) {
    for (const companion of companions) for (const id of companion.applications) {
      const app = companionApplications.get(id);
      const effect = app?.effect ? effects.get(app.effect) : undefined;
      const fm = effect && familyKey(effect);
      if (app && effect && fm) { meta.set(fm.key, fm); push(fromCompanions, fm.key, { companion, app, effect }); }
    }
  }
  return { meta, applies, fromLacrimas, fromCompanions, needs };
}

/** Plain groupings of the game's trigger wording, so lacrimas can be filtered without knowing every phrase. */
export const TRIGGER_GROUPS = ['Constant', 'Repeating', 'On an event', 'One-off'] as const;
export type TriggerGroup = (typeof TRIGGER_GROUPS)[number];
export function triggerGroup(t: Application['trigger']): TriggerGroup | null {
  if (!t) return null;
  const raw = t.raw.toLowerCase();
  if (raw === 'while on the field') return 'Constant';
  if (t.everySeconds != null || raw.startsWith('every')) return 'Repeating';
  if (['start of battle', 'when defeated', 'when incapacitated'].includes(raw)) return 'One-off';
  return 'On an event';
}
/** What a lacrima does, one row per effect it applies, for the lacrima list and its filters. */
export function lacrimaRows(l: Lacrima) {
  return l.applications.flatMap((id) => {
    const app = applications.get(id); if (!app) return [];
    const effect = app.effect ? effects.get(app.effect) : undefined;
    const fm = effect && familyKey(effect);
    return [{ app, effect, label: fm ? fm.label : effect ? baseName(effect) : null, group: triggerGroup(app.trigger) }];
  });
}

export const tierRank = (t: string | null) => (t ? TIER_ORDER.indexOf(t) : 9);
export const initials = (name: string) =>
  name.replace(/-.*-/, '').split(' ').filter(Boolean).slice(-2).map((w) => w[0]).join('');

"""Prototype converter: Capacities export -> published JSON + validation report.

usage: python3 convert.py <export/Personal> <skills_dir> <out_dir> [slugs.json]

Only the folders in common.GAME_FOLDERS (plus the Skill files) are read, and only the
fields named in the PUBLISH maps below are copied. Everything else is never touched.
"""
import collections
import difflib
import glob
import json
import os
import re
import sys
import unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import links, load, norm_title, read, resolve, title_index  # noqa: E402

# Fields that must never appear in published output (checked at the end as a guard)
PERSONAL = {"ownedUnit", "currentStars", "lacrimasEquipped", "equippedBy",
            "primaryTeamContribution", "secondaryTeamContribution", "teamSynergy"}

issues = collections.defaultdict(list)  # category -> [message]


def issue(cat, msg):
    issues[cat].append(msg)


def slugify(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "x"


def clean(v):
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def attr_name(v):
    return re.sub(r"^[^\w]+", "", v).strip() if v else None


EVENTS = ["normal attack", "normal skill hit", "special skill hit", "critical hit", "after attack hits", "after heal",
          "when attacked", "when taking damage", "when defeated", "when incapacitated", "on enemy defeated",
          "on transformation", "hp reaches threshold", "while unit is on the field", "while on the field",
          "start of battle", "constant"]


def parse_trigger(raw, where):
    if not raw:
        return None
    every = None
    events = []
    for part in [p.strip() for p in str(raw).split(",")]:
        m = re.fullmatch(r"every (\d+(?:\.\d+)?) sec", part, re.I)
        if m:
            every = float(m.group(1))
            continue
        if part.lower() in EVENTS:
            events.append(part.lower())
        else:
            issue("Unrecognized trigger values", f"{where}: '{part}'")
    if every is not None and every.is_integer():
        every = int(every)
    return {"events": events, "everySeconds": every, "raw": raw}


def families(raw, known, where):
    if not raw:
        return []
    out = [f.strip() for f in re.split(r",| or ", str(raw)) if f.strip()]
    for f in out:
        if f not in known:
            issue("Required effect families not in the effectFamily list", f"{where}: '{f}'")
    return out


LEVEL_COLS = ["Level", "Trigger", "Target", "Effect", "Tier", "Chance", "Duration", "Value", "Condition", "Notes"]


def parse_levels(body, where):
    """Skill page text: '**Lv.N**' paragraphs + one table in the standard layout."""
    texts = {}
    for m in re.finditer(r"\*\*Lv\.(\d)\*\*\s*\n+(.*?)(?=\n\s*\n|\Z)", body, re.S):
        texts[f"Lv{m.group(1)}"] = m.group(2).strip()
    rows, header = [], None
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            if header != LEVEL_COLS:
                issue("Level tables not in the standard layout", f"Skill '{where}': columns {header}")
                return texts, []
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        if not row.get("Level", "").isdigit():
            issue("Level tables not in the standard layout", f"Skill '{where}': row without a level number")
        rows.append({k[0].lower() + k[1:]: (v or None) for k, v in row.items()})
    if header is None:
        issue("Level tables not in the standard layout", f"Skill '{where}': no table")
    return texts, rows


LEGIT_VARIANTS = re.compile(r"\b(top|high|mid|low|increase|decrease|up|down|i{1,3}|\d+)\b", re.I)


def near_duplicates(values, label):
    vals = sorted({v for v in values if v})
    seen = set()
    for i, a in enumerate(vals):
        for b in vals[i + 1:]:
            if (a, b) in seen:
                continue
            al, bl = a.lower(), b.lower()
            # 'Top X Increase' vs 'Mid X Decrease', 'Up I' vs 'Up II', 'Every 5 sec' vs 'Every 7 sec' are real variants
            if al != bl and LEGIT_VARIANTS.sub("", al) == LEGIT_VARIANTS.sub("", bl):
                continue
            if al == bl or difflib.SequenceMatcher(None, al, bl).ratio() >= 0.9:
                issue("Near-duplicate values (typo or inconsistent spelling?)", f"{label}: '{a}' vs '{b}'")
                seen.add((a, b))


def main(root, skills_dir, out, slugs_path=None):
    os.makedirs(out, exist_ok=True)
    data = load(root)
    C, E, EA, L, LEA = (data[k] for k in ["Characters", "Effects", "EffectApplications", "Lacrimas",
                                          "LacrimaEffectApplications"])
    idx = {k: title_index(v) for k, v in data.items()}

    # address table: reuse existing slugs, mint new ones, flag collisions
    slugs = {}
    if slugs_path and os.path.exists(slugs_path):
        slugs = json.load(open(slugs_path, encoding="utf-8"))
    used = collections.defaultdict(dict)
    for kind in slugs:
        for key, sl in slugs[kind].items():
            used[kind][sl] = key

    def slug_for(kind, key, title):
        slugs.setdefault(kind, {})
        if key in slugs[kind]:
            return slugs[kind][key]
        base = slugify(title)
        sl = base
        if sl in used[kind] and kind != "application":
            issue("Address collisions (two records want the same page address)",
                  f"{kind}: '{title}' and '{used[kind][sl]}' both map to '{base}'")
        if sl in used[kind]:
            n = 2
            while f"{base}-{n}" in used[kind]:
                n += 1
            sl = f"{base}-{n}"
        slugs[kind][key] = sl
        used[kind][sl] = key
        return sl

    owner_keys = {"title", "character", "lacrima", "gameText", "tags"}
    for folder, recs in data.items():
        groups = collections.defaultdict(list)
        for stem, r in recs.items():
            groups[re.sub(r"[^a-z0-9]", "", str(r["fm"].get("title", stem)).lower())].append(stem)
        for stems in groups.values():
            if len(stems) < 2:
                continue
            bodies = [{k: v for k, v in recs[s]["fm"].items() if k not in owner_keys} for s in stems]
            titles = " / ".join(f"'{recs[s]['fm'].get('title')}'" for s in stems)
            if all(b == bodies[0] for b in bodies):
                issue("Same record entered twice (merge into one shared record)", f"{folder}: {titles}")
            else:
                issue("Duplicate titles with different data", f"{folder}: {titles}")
        nb = sum(1 for r in recs.values() if "\xa0" in str(r["fm"].get("title", "")))
        if nb:
            issue("Titles containing a non-breaking space (handled by the converter; worth cleaning eventually)",
                  f"{folder}: {nb} titles")

    def ref(prop_value, folder, where, prop, many=False, required=False):
        res = []
        for ln in links(prop_value):
            stem, prob = resolve(ln, data[folder], idx[folder])
            if prob:
                issue("Broken or ambiguous links", f"{where} → {prop}: {prob}")
            else:
                res.append(stem)
        if required and not res:
            issue("Missing required values", f"{where}: {prop} is empty")
        return res if many else (res[0] if res else None)

    # ---------- effects
    effects = []
    eff_slug = {}
    for stem, r in sorted(E.items()):
        f = r["fm"]
        t = clean(f.get("title")) or stem
        sl = slug_for("effect", stem, t)
        eff_slug[stem] = sl
        if not f.get("effectFamily"):
            issue("Missing required values", f"Effect '{t}': effectFamily is empty")
        sec = None
        if f.get("secondaryStat"):
            sec = {"stat": f.get("secondaryStat"), "direction": f.get("secondaryDirection"),
                   "amount": f.get("secondaryValue"), "unit": f.get("secondaryUnit")}
        effects.append({
            "id": sl, "name": t, "family": clean(f.get("effectFamily")), "direction": clean(f.get("direction")),
            "tier": clean(f.get("magnitudeTier")), "polarity": clean(f.get("polarity")),
            "mechanic": clean(f.get("mechanic")),
            "value": ({"amount": f.get("defaultValue"), "unit": f.get("valueUnit")}
                      if f.get("defaultValue") is not None else None),
            "secondary": sec, "gameText": clean(f.get("gameText")),
            "counteredBy": [eff_slug.get(s, slugify(s)) for s in ref(f.get("counteredBy"), "Effects", f"Effect '{t}'", "counteredBy", many=True)],
        })
    known_fams = {e["family"] for e in effects if e["family"]}

    # ---------- applications (unit and lacrima, one shape)
    applications = []
    app_slug = {}

    def application(stem, f, source, where_prefix):
        t = clean(f.get("title")) or stem
        where = f"{where_prefix} '{t}'"
        sl = slug_for("application", f"{source}:{stem}", t)
        app_slug[(source, stem)] = sl
        eff = ref(f.get("effect"), "Effects", where, "effect", required=True)
        ch = f.get("chance")
        if ch is not None and not (0 < float(ch) <= 1):
            issue("Values out of range", f"{where}: chance {ch} is not between 0 and 1")
        cond = f.get("condition", f.get("conditions"))
        req = None
        if f.get("requiredEffectFamilies"):
            req = {"families": families(f.get("requiredEffectFamilies"), known_fams, where),
                   "match": clean(f.get("effectFamilyMatchRule")),
                   "subject": clean(f.get("effectConditionSubject")),
                   "timing": clean(f.get("effectEvaluationTiming")),
                   "state": clean(f.get("requiredEffectState"))}
        scaling = None
        if f.get("scalingAttribute"):
            scaling = {k: f.get(k) for k in ["scalingAttribute", "increasePerUnit", "increaseValueUnit",
                                              "scalingBasis", "maximumNumberOfIncreases", "maximumResult"]}
        applications.append({
            "id": sl, "source": source, "effect": eff_slug.get(eff) if eff else None,
            "type": clean(f.get("applicationType")), "target": clean(f.get("target")),
            "trigger": parse_trigger(f.get("activationInterval"), where),
            "chance": ch, "durationSeconds": f.get("durationSeconds"),
            "valueOverride": ({"amount": f.get("effectValue"), "unit": f.get("valueUnit")}
                              if f.get("effectValue") is not None else None),
            "condition": clean(cond), "requires": req, "scaling": scaling,
            "gameText": clean(f.get("gameText")),
        })

    for stem, r in sorted(EA.items()):
        application(stem, r["fm"], "unit", "EffectApplication")
        if not r["fm"].get("character"):
            issue("Orphans", f"EffectApplication '{r['fm'].get('title')}' is linked to no character")
    for stem, r in sorted(LEA.items()):
        application(stem, r["fm"], "lacrima", "LacrimaEffectApplication")

    # ---------- skills (from Skill files; later these come from the export)
    skill_by_title = {}
    used_apps = set()
    for p in sorted(glob.glob(os.path.join(skills_dir, "*.md"))):
        f, body = read(p)
        u = links(f.get("unit"))
        unit_title = u[0][0] if u else None
        apps = []
        for ln in links(f.get("effectApplications")):
            stem, prob = resolve(ln, EA, idx["EffectApplications"])
            if prob and prob.startswith("ambiguous"):
                # identical duplicates: pick the copy that names this unit as its character
                cands = [s for s in idx["EffectApplications"].get(norm_title(ln[0]), [])
                         if any(x[0] == unit_title for x in links(EA[s]["fm"].get("character")))]
                if len(cands) == 1:
                    stem, prob = cands[0], None
            if prob:
                issue("Broken or ambiguous links", f"Skill '{f.get('title')}' → effectApplications: {prob}")
            else:
                apps.append(stem)
                used_apps.add(stem)
        title = norm_title(f.get("title"))
        texts, table = parse_levels(body, title)
        skill_by_title[title] = {
            "kind": f.get("kind"), "name": clean(f.get("skillName")), "unit": unit_title,
            "attackRange": clean(f.get("attackRange")),
            "gameText": texts, "levelTable": table, "_apps": apps,
        }
    for stem, r in EA.items():
        if stem not in used_apps:
            issue("Effect applications no skill links to",
                  f"'{norm_title(r['fm'].get('title'))}' (characters: "
                  f"{', '.join(x[0] for x in links(r['fm'].get('character'))) or 'none'})")

    # ---------- units
    units = []
    unit_slug = {}
    for stem, r in sorted(C.items()):
        f = r["fm"]
        t = clean(f.get("title")) or stem
        if not f.get("rarity") and not f.get("attribute"):
            issue("Skipped records", f"Character '{t}' (file '{stem}'): no rarity or attribute, treated as a template")
            continue
        where = f"Character '{t}'"
        for prop in ["identity", "collection", "rarity", "attribute", "class", "coverImage"]:
            if not f.get(prop):
                issue("Missing required values", f"{where}: {prop} is empty")
        unit_slug[stem] = slug_for("unit", stem, t)
    for stem, r in sorted(C.items()):
        if stem not in unit_slug:
            continue
        f = r["fm"]
        t = clean(f.get("title")) or stem
        where = f"Character '{t}'"
        sig = ref(f.get("signatureLacrima"), "Lacrimas", where, "signatureLacrima")
        sk = []
        for ln in links(f.get("skills")):
            s = skill_by_title.get(norm_title(ln[0]))
            if s is None:
                issue("Skill links", f"{where}: skills lists '{ln[0]}', which doesn't exist")
                continue
            if norm_title(s["unit"] or "") != norm_title(t):
                issue("Skill links", f"{where}: skill '{ln[0]}' says its unit is '{s['unit']}'")
            s = dict(s)
            s["applications"] = [app_slug[("unit", a)] for a in s.pop("_apps")]
            s.pop("unit")
            sk.append(s)
        kinds = sorted(s["kind"] or "?" for s in sk)
        if kinds != ["Normal", "Special", "Ultimate"]:
            issue("Skill links", f"{where}: needs exactly one Normal, Special and Ultimate skill; has {kinds or 'none'}")
        img = re.search(r"\]\(\.\./Images/Media/([^)]+)\)", str(f.get("coverImage") or ""))
        units.append({
            "id": unit_slug[stem], "name": t, "identity": clean(f.get("identity")),
            "collection": clean(f.get("collection")), "rarity": clean(f.get("rarity")),
            "attribute": attr_name(f.get("attribute")), "role": clean(f.get("class")),
            "portrait": urllib.parse.unquote(img.group(1)) if img else None,
            "signatureLacrima": None,  # filled after lacrimas get slugs
            "_sig": sig,
            "skills": sorted(sk, key=lambda s: ["Normal", "Special", "Ultimate"].index(s["kind"])
                             if s["kind"] in ("Normal", "Special", "Ultimate") else 9),
        })

    # ---------- lacrimas
    lacrimas = []
    lac_slug = {}
    for stem, r in sorted(L.items()):
        f = r["fm"]
        t = clean(f.get("title")) or stem
        lac_slug[stem] = slug_for("lacrima", stem, re.sub(r"^[^\w]+", "", t))
    for stem, r in sorted(L.items()):
        f = r["fm"]
        t = clean(f.get("title")) or stem
        where = f"Lacrima '{t}'"
        owner = ref(f.get("signatureCharacter"), "Characters", where, "signatureCharacter")
        apps = ref(f.get("lacrimaEffectApplications"), "LacrimaEffectApplications", where,
                   "lacrimaEffectApplications", many=True, required=True)
        lacrimas.append({
            "id": lac_slug[stem], "name": re.sub(r"^[^\w]+", "", t).strip(),
            "kind": "signature" if owner else "generic",
            "signatureFor": unit_slug.get(owner) if owner else None,
            "gameText": clean(f.get("gameText")),
            "applications": [app_slug[("lacrima", a)] for a in apps],
        })
    for u in units:
        sig = u.pop("_sig")
        u["signatureLacrima"] = lac_slug.get(sig) if sig else None

    # ---------- vocabulary checks
    near_duplicates([u["identity"] for u in units], "identity")
    near_duplicates([e["name"] for e in effects], "Effect title")
    near_duplicates([a["target"] for a in applications], "target")
    near_duplicates([e["value"]["unit"] for e in effects if e["value"]] +
                    [a["valueOverride"]["unit"] for a in applications if a["valueOverride"]], "valueUnit")
    near_duplicates([p for a in applications if a["trigger"] for p in a["trigger"]["raw"].split(", ")],
                    "activationInterval")
    skill_typo = collections.Counter(a["trigger"]["raw"] for a in applications
                                     if a["trigger"] and "SKill" in a["trigger"]["raw"])
    for raw, n in skill_typo.items():
        issue("Typos", f"activationInterval '{raw}': {n} records")

    # ---------- write
    payload = {"effects": effects, "applications": applications, "units": units, "lacrimas": lacrimas}
    for k, v in payload.items():
        with open(os.path.join(out, f"{k}.json"), "w", encoding="utf-8") as fh:
            json.dump(v, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "slugs.json"), "w", encoding="utf-8") as fh:
        json.dump(slugs, fh, ensure_ascii=False, indent=1, sort_keys=True)

    # guard: nothing personal leaked
    blob = json.dumps(payload)
    leaked = [k for k in PERSONAL if f'"{k}"' in blob]
    assert not leaked, f"personal fields leaked: {leaked}"

    with open(os.path.join(out, "validation-report.md"), "w", encoding="utf-8") as fh:
        total = sum(len(v) for v in issues.values())
        fh.write("# Validation report\n\n")
        fh.write(f"{len(units)} units, {len(lacrimas)} lacrimas, {len(effects)} effects, "
                 f"{len(applications)} effect applications. {total} issues in {len(issues)} categories.\n\n")
        for cat in sorted(issues, key=lambda c: -len(issues[c])):
            fh.write(f"## {cat} ({len(issues[cat])})\n\n")
            for m in sorted(set(issues[cat])):
                fh.write(f"- {m}\n")
            fh.write("\n")
    print({k: len(v) for k, v in payload.items()}, {c: len(set(v)) for c, v in issues.items()})


if __name__ == "__main__":
    main(*sys.argv[1:])

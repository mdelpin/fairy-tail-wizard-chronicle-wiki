"""Split each Character's Kit Details into Skill objects for Capacities import.

usage: python3 extract_skills.py <export/Personal> <out_dir>
"""
import collections
import csv
import glob
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import links, load, resolve, title_index

KINDS = [("Normal", re.compile(r"\bnormal\b", re.I)),
         ("Special", re.compile(r"\bspecial\b", re.I)),
         ("Ultimate", re.compile(r"\bultimate\b", re.I))]
TIERS = re.compile(r"^(Top|High|Mid|Low)\s+")
EMOJI_ETC = re.compile(r"[^\w\s\-–—()'’!.:&,?/]")


def clean_heading(h):
    h = h.replace("**", "").strip()
    return EMOJI_ETC.sub("", h).strip()


KIT_HEAD = re.compile(r"^#\s+.*Kit Details.*$", re.M)


def kit_section(body):
    m = KIT_HEAD.search(body)
    if not m:
        return None
    rest = body[m.end():]
    nxt = re.search(r"^#\s", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


def split_skills(kit, base=0):
    """Return (kind, clean_head, raw_head, body, abs_end) for each ## section; abs_end is an
    offset into the full page when base = offset of the kit text in the page."""
    heads = list(re.finditer(r"^##\s+(.*)$", kit, re.M))
    out = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(kit)
        body = kit[h.end():end]
        # a skill ends at a horizontal rule, any heading, or the lacrima embed
        stop = re.search(r"^(---\s*$|#{1,6}\s|\[\[Equipped Lacrima Effects\]\])", body, re.M)
        if stop:
            body = body[: stop.start()]
        head = clean_heading(h.group(1))
        kind = next((k for k, rx in KINDS if rx.search(head.split("(")[0])), None)
        out.append((kind, head, h.group(1), body, base + h.end() + len(body)))
    return out


STD_COLS = ["Level", "Trigger", "Target", "Effect", "Tier", "Chance", "Duration", "Value", "Condition", "Notes"]
TIER_WORDS = {"top", "high", "mid", "low"}


def std_row(r):
    trig = col(r, "trigger / interval", "additional effect / trigger", "additional effect", "trigger",
               "condition / trigger")
    if not trig and col(r, "skill"):
        trig = "Attack"
    mag = col(r, "damage/magnitude", "damage / magnitude", "magnitude")
    tier = col(r, "tier")
    if not tier and mag.strip().lower() in TIER_WORDS:
        tier, mag = mag, ""
    cond = col(r, "condition")
    vals = ["3", trig, col(r, "target"), col(r, "effect"), tier, col(r, "chance"), col(r, "duration"),
            mag, cond if cond != trig else "", col(r, "notes")]
    return "| " + " | ".join(v.replace("|", "/").strip() for v in vals) + " |"


def std_body(text, rows):
    lines = ["**Lv.3**", "", text or "", "",
             "| " + " | ".join(STD_COLS) + " |",
             "| " + " | ".join("---" for _ in STD_COLS) + " |"]
    lines += [std_row(r) for r in rows]
    return "\n".join(lines) + "\n"


def parse_tables(md):
    tables, cur = [], []
    for line in md.splitlines():
        if line.strip().startswith("|"):
            cur.append([c.strip().replace("**", "").strip() for c in line.strip().strip("|").split("|")])
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    res = []
    for t in tables:
        if len(t) < 2:
            continue
        head = [h.lower() for h in t[0]]
        rows = [r for r in t[2:] if any(c for c in r)]
        res.append([dict(zip(head, r)) for r in rows])
    return res


def col(row, *names):
    for k, v in row.items():
        kk = re.sub(r"\s+", "", k)
        if any(re.sub(r"\s+", "", n) == kk for n in names):
            return v
    return ""


def num(s, unit=r"%"):
    m = re.search(r"(\d+(?:\.\d+)?)\s*" + unit, s or "")
    return float(m.group(1)) if m else None


def prose(body):
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            if lines:
                break
            continue
        if s.startswith("|") or s.startswith("[[") or s.startswith("---"):
            if lines:
                break
            continue
        lines.append(s)
    return " ".join(lines)


def norm(s):
    return re.sub(r"\s+", " ", str(s or "").replace("**", "")).strip().lower()


def effect_keys(ea_title):
    name = ea_title.split("→")[0].split(" - ")[0].strip()
    name = TIERS.sub("", name)
    keys = {name.lower()}
    keys.add(name.lower().replace("increase", "up").replace("decrease", "down"))
    return keys


TRIGGER_OPTIONS = ["Normal Skill Hit", "Special Skill Hit", "Critical Hit", "After Attack Hits", "When Attacked",
                   "On Enemy Defeated", "HP Reaches Threshold", "While on the Field", "Constant"]


# Typos and capitalization only. Area wordings ("Enemies in Range", "Targets in Range",
# "Enemies (Area)", ...) are kept as written until it's decided whether they mean the same thing.
TARGET_FIXES = {"siingle enemy": "Single Enemy", "enemies within range": "Enemies within Range",
                "targets within range": "Targets within Range"}
# The skill text only ever says "within the target area" or "within range"; the other wordings
# are transcription variants of those two.
AREA_MAP = {"Enemies (Area)": "Enemies in Target Area", "Enemies within Target Area": "Enemies in Target Area",
            "Targets in Range": "Enemies in Range", "Targets within Range": "Enemies in Range",
            "Enemies within Range": "Enemies in Range"}


def normalize_target(t):
    t = re.sub(r"\s+", " ", t).strip()
    t = TARGET_FIXES.get(t.lower(), t)
    return AREA_MAP.get(t, t)


def damage_trigger(s):
    raw = (s.get("dmg_trigger") or "").strip()
    if s["kind"] == "Normal" and (not raw or raw.lower() in ("normal attack", "attack", "normal skill")):
        return "Normal Attack"
    if raw.lower() in ("normal skill", "normal skill hit"):
        return "Normal Skill Hit"
    m = re.search(r"every (\d+)\s*s", raw, re.I)
    if m:
        return f"Every {m.group(1)} sec"
    for opt in TRIGGER_OPTIONS:
        if raw.lower().replace("skill", "skill") == opt.lower():
            return opt
    if s["interval"]:
        return f"Every {int(s['interval'])} sec"
    return raw or None


def main(root, out):
    data = load(root)
    chars, eas = data["Characters"], data["EffectApplications"]
    ea_idx = title_index(eas)
    os.makedirs(os.path.join(out, "Skills"), exist_ok=True)
    char_files = {}
    for p in glob.glob(os.path.join(root, "Characters", "*.md")):
        st = os.path.splitext(os.path.basename(p))[0]
        char_files[re.sub(r"#U([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), st)] = p
    damage_eas = {}
    report = collections.defaultdict(list)
    ranges = []
    n_files = 0
    stats = collections.Counter()

    for stem, c in sorted(chars.items()):
        unit = str(c["fm"].get("title") or stem).strip()
        if not c["fm"].get("rarity"):
            report[unit].append(f"Skipped: no rarity or attribute (template or stub record, file '{stem}')")
            continue
        kit = kit_section(c["body"])
        if kit is None:
            report[unit].append("No Kit Details section found")
            continue
        km = KIT_HEAD.search(c["body"])
        kit_start, kit_end = km.start(), km.end()
        skills = []
        for kind, head, raw_head, body, abs_end in split_skills(kit, km.end()):
            if not kind:
                continue
            kit_end = max(kit_end, abs_end)
            name = ""
            m = re.split(r"\s+[-–—]\s+", head, maxsplit=1)
            if len(m) == 2:
                name = m[1].strip()
            name = re.sub(r"\s*\((Melee|Ranged)\)\s*$", "", name).strip()
            rng = re.search(r"\((Melee|Ranged)\)", head)
            if kind == "Normal" and (not name or re.fullmatch(r"(Normal )?(Attack|Skill)", name, re.I)):
                # the game calls it "Normal Attack (Ranged)"
                name = f"Normal Attack ({rng.group(1)})" if rng else "Normal Attack"
            tables = parse_tables(body)
            dmg_pct = dmg_target = chance = interval = None
            dmg_trigger = None
            for t in tables:
                for r in t:
                    eff = col(r, "effect").lower()
                    if eff == "damage" and dmg_pct is None:
                        dmg_pct = num(col(r, "damage/magnitude", "damage / magnitude", "magnitude"))
                        dmg_target = col(r, "target") or None
                        ch = num(col(r, "chance"))
                        chance = ch / 100 if ch is not None else None
                        trig = col(r, "trigger / interval", "trigger/interval", "additional effect / trigger",
                                   "trigger", "condition / trigger", "skill")
                        iv = num(trig, r"sec")
                        interval = iv
                        dmg_trigger = trig
            text = prose(body)
            if interval is None:
                iv = re.match(r"Every (\d+) sec", text)
                interval = float(iv.group(1)) if iv else None
            if kind == "Special" and chance is None:
                ch = re.search(r"(\d+)% chance to deal", text)
                chance = int(ch.group(1)) / 100 if ch else None
            intervals = {float(x) for x in re.findall(r"every (\d+)\s*s(?:ec|econds)?\b", body, re.I)}
            skills.append(dict(kind=kind, name=name, text=text, body=body.strip(),
                               rows=[r for t in tables for r in t], intervals=intervals,
                               dmg=dmg_pct, target=dmg_target, chance=chance, interval=interval,
                               dmg_trigger=dmg_trigger,
                               range=rng.group(1) if rng else None, eas=[]))
            if kind == "Normal" and rng:
                ranges.append((unit, rng.group(1)))
        kinds = [s["kind"] for s in skills]
        if sorted(kinds) != ["Normal", "Special", "Ultimate"]:
            report[unit].append(f"Skill headings found: {kinds or 'none'}")

        # assign effect applications to skills
        for link in links(c["fm"].get("effectApplications")):
            ea_stem, prob = resolve(link, eas, ea_idx)
            if prob:
                report[unit].append(f"Effect application link: {prob}")
                stats["ea_link_problem"] += 1
                continue
            ea = eas[ea_stem]["fm"]
            title = str(ea.get("title")).strip()
            act = str(ea.get("activationInterval") or "")
            iv = re.search(r"Every (\d+) sec", act)
            iv = float(iv.group(1)) if iv else None
            keys = effect_keys(title)
            eff_name = norm(TIERS.sub("", str(ea.get("effect") or "").strip("[]")))
            ea_target = norm(ea.get("target"))
            ea_dur = ea.get("durationSeconds")
            ea_ch = ea.get("chance")
            scores = []
            for s in skills:
                hay = (s["text"] + " " + s["body"]).lower()
                sc = 0
                # best matching table row in this skill
                row_best = 0
                for r in s["rows"]:
                    rs = 0
                    if eff_name and norm(col(r, "effect")) in (eff_name, eff_name.replace("increase", "up")):
                        rs += 4
                    if rs and ea_target and norm(col(r, "target")) == ea_target:
                        rs += 2
                    if rs and ea_dur is not None and num(col(r, "duration"), r"s") == float(ea_dur):
                        rs += 1
                    if rs and ea_ch is not None and num(col(r, "chance")) == round(float(ea_ch) * 100):
                        rs += 1
                    trig = norm(col(r, "trigger / interval", "additional effect / trigger", "additional effect",
                                    "trigger", "condition"))
                    row_iv = num(trig, r"\s*s")
                    if rs and row_iv is not None:
                        rs += 1 if (iv is not None and row_iv == iv) else (-2 if iv is None else 0)
                    if rs and "critical" in trig and "critical" in act.lower():
                        rs += 1
                    row_best = max(row_best, rs)
                sc += row_best
                if iv is not None and iv in s["intervals"]:
                    sc += 3
                if any(k and k in hay for k in keys):
                    sc += 1
                if "critical hit" in act.lower() and ("critical hit" in hay):
                    sc += 1
                if "normal skill hit" in act.lower() and re.search(r"normal skill hits?|after a normal skill", hay):
                    sc += 1
                if "special skill hit" in act.lower() and "special skill" in hay:
                    sc += 1
                scores.append(sc)
            best = max(scores) if scores else 0
            if best >= 2 and scores.count(best) == 1:
                s = skills[scores.index(best)]
                if len(ea_idx.get(title, [])) > 1:
                    report[unit].append(f"'{title}' assigned to {s['kind']}, but that title belongs to {len(ea_idx[title])} records, so the [[link]] may resolve to the wrong one")
                    stats["ambiguous_title"] += 1
                s["eas"].append(title)
                stats["assigned"] += 1
            else:
                cands = [skills[i]["kind"] for i, v in enumerate(scores) if v == best and best > 0]
                report[unit].append(f"Couldn't place '{title}' ({act}); candidates: {', '.join(cands) or 'none'}")
                stats["unplaced"] += 1

        skill_titles = {}
        for s in skills:
            # base damage becomes an effect application of the 'Damage' effect
            if s["dmg"] is not None:
                trig = damage_trigger(s)
                pct = int(s["dmg"]) if float(s["dmg"]).is_integer() else s["dmg"]
                chance_txt = f"{round(s['chance'] * 100)}% / " if s["chance"] else ""
                tgt = normalize_target(s["target"] or "Single Enemy")
                dtitle = f"Damage → {tgt} – {trig + ' / ' if trig else ''}{chance_txt}{pct}% of Own ATK"
                rec = damage_eas.setdefault(dtitle, {
                    "type": "EffectApplication", "title": dtitle, "tags": [],
                    "activationInterval": trig, "chance": s["chance"], "applicationType": "Inflicts",
                    "effect": "[[Damage]]", "target": tgt, "effectValue": pct,
                    "valueUnit": "Percent of own ATK", "durationSeconds": None, "character": []})
                if f"[[{unit}]]" not in rec["character"]:
                    rec["character"].append(f"[[{unit}]]")
                s["eas"].insert(0, dtitle)
                stats["damage_links"] += 1
            title = f"{unit} — {s['kind']}"
            skill_titles[s["kind"]] = title
            fm = {
                "type": "Skill",
                "title": title,
                "kind": s["kind"],
                "skillName": s["name"] or None,
                "unit": [f"[[{unit}]]"],
                "attackRange": s["range"] if s["kind"] == "Normal" else None,
                "effectApplications": [f"[[{t}]]" for t in s["eas"]],
            }
            fname = re.sub(r'[\\/:*?"<>|]', "_", title) + ".md"
            with open(os.path.join(out, "Skills", fname), "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=10**9, default_flow_style=None))
                f.write("---\n\n")
                f.write(std_body(s["text"], s["rows"]))
            n_files += 1

        # Character: three skill links instead of effectApplications; Kit Details moves to the Skills
        src = char_files[stem]
        text = open(src, encoding="utf-8").read()
        mm = re.match(r"(---\n.*?\n---\n?)(.*)", text, re.S)  # same split as common.read
        head, body = mm.group(1), mm.group(2)
        # one two-way-linked list, in Normal / Special / Ultimate order, written like the export's lists
        new_props = yaml.safe_dump({"skills": [f"[[{skill_titles[k]}]]" for k in ("Normal", "Special", "Ultimate")
                                               if k in skill_titles]},
                                   allow_unicode=True, width=10**9, default_flow_style=None)
        head = re.sub(r"^effectApplications:.*?(?=^\S)", new_props, head, count=1, flags=re.M | re.S)
        km = KIT_HEAD.search(body)
        body = body[:km.start()] + body[kit_end:].lstrip("\n") if km else body
        os.makedirs(os.path.join(out, "Characters"), exist_ok=True)
        with open(os.path.join(out, "Characters", os.path.basename(src)), "w", encoding="utf-8") as f:
            f.write(head + body)

    # new damage effect applications + the base Damage effect
    os.makedirs(os.path.join(out, "EffectApplications (new damage)"), exist_ok=True)
    for t, rec in damage_eas.items():
        fname = re.sub(r'[\\/:*?"<>|]', "_", t) + ".md"
        with open(os.path.join(out, "EffectApplications (new damage)", fname), "w", encoding="utf-8") as f:
            f.write("---\n" + yaml.safe_dump(rec, allow_unicode=True, sort_keys=False, width=10**9, default_flow_style=None) + "---\n")
    os.makedirs(os.path.join(out, "Effects (new)"), exist_ok=True)
    with open(os.path.join(out, "Effects (new)", "Damage.md"), "w", encoding="utf-8") as f:
        f.write("---\n" + yaml.safe_dump({
            "type": "Effect", "title": "Damage", "tags": [], "effectFamily": "Damage", "direction": None,
            "magnitudeTier": None, "polarity": "Harmful", "mechanic": "Damage", "defaultValue": None,
            "valueUnit": "Percent of own ATK", "counteredBy": [], "removes": [], "secondaryStat": None,
            "secondaryDirection": None, "secondaryValue": None, "secondaryUnit": None,
            "gameText": None}, allow_unicode=True, sort_keys=False) + "---\n")
    stats["damage_records"] = len(damage_eas)

    with open(os.path.join(out, "skills-report.md"), "w", encoding="utf-8") as f:
        f.write("# Skill extraction report\n\n")
        f.write(f"- Skill files written: {n_files}\n")
        f.write(f"- Effect applications placed on a skill: {stats['assigned']}\n")
        f.write(f"- Effect applications not placed (need a manual pick): {stats['unplaced']}\n")
        f.write(f"- Placed, but the title is shared by several records: {stats['ambiguous_title']}\n")
        f.write(f"- Effect application links that didn't resolve: {stats['ea_link_problem']}\n")
        f.write(f"- Characters with a normal attack range in the heading: {len(ranges)}\n")
        f.write(f"- Skills with base damage: {stats['damage_links']}, as {stats['damage_records']} "
                f"shared Damage effect applications\n\n")
        for unit in sorted(report):
            f.write(f"## {unit}\n\n")
            for line in report[unit]:
                f.write(f"- {line}\n")
            f.write("\n")
    print(n_files, dict(stats), len(report))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

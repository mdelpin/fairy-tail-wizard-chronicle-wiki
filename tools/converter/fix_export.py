"""Make a corrected copy of the game folders for re-import into the new space.

usage: python3 fix_export.py <export/Personal> <out/Personal>

- activationInterval: 'SKill' -> 'Skill', 'While Unit is on the Field' -> 'While on the Field'
- EffectApplications entered twice with identical data are merged: one survivor keeps
  both characters; links in Characters are pointed at the survivor.
Only text lines that change are rewritten; everything else is copied byte for byte.
"""
import collections
import glob
import os
import re
import shutil
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import GAME_FOLDERS, links, load, norm_title, resolve, title_index  # noqa: E402

OWNER_KEYS = {"title", "character", "gameText", "tags"}
log = []


def flow(lst):
    return yaml.safe_dump(lst, default_flow_style=True, allow_unicode=True, width=10**9).strip()


def set_line(text, key, value_yaml):
    """Replace a top-level frontmatter key (single or multi-line value) with key: value_yaml."""
    fm_end = text.index("\n---", 3)
    head, rest = text[:fm_end], text[fm_end:]
    pat = re.compile(rf"^{re.escape(key)}:.*?(?=^\S|\Z)", re.M | re.S)
    if not pat.search(head):
        raise ValueError(f"{key} not found")
    head = pat.sub(lambda m: f"{key}: {value_yaml}\n", head, count=1)
    return head + rest


def main(src, dst):
    data = load(src)
    EA, C = data["EffectApplications"], data["Characters"]
    files = {}  # (folder, stem) -> path
    for folder in GAME_FOLDERS:
        for p in glob.glob(os.path.join(src, folder, "*.md")):
            stem = os.path.splitext(os.path.basename(p))[0]
            stem = re.sub(r"#U([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), stem)
            files[(folder, stem)] = p

    # find identical duplicates
    groups = collections.defaultdict(list)
    for stem, r in EA.items():
        groups[re.sub(r"[^a-z0-9]", "", str(r["fm"].get("title")).lower())].append(stem)
    remap = {}  # removed stem -> survivor stem
    survivors = {}
    for stems in groups.values():
        if len(stems) < 2:
            continue
        bodies = [{k: v for k, v in EA[s]["fm"].items() if k not in OWNER_KEYS} for s in stems]
        if not all(b == bodies[0] for b in bodies):
            log.append(f"NOT merged (data differs): {stems}")
            continue
        # survivor: '→' arrow, no '(1)' suffix, then has gameText
        def rank(s):
            t = str(EA[s]["fm"].get("title"))
            return ("→" not in t, "(1)" in s, not EA[s]["fm"].get("gameText"))
        stems = sorted(stems, key=rank)
        keep = stems[0]
        owners = []
        for s in stems:
            for ln in links(EA[s]["fm"].get("character")):
                if ln[0] not in owners:
                    owners.append(ln[0])
            if s != keep:
                remap[s] = keep
        survivors[keep] = owners
        gts = {str(EA[s]["fm"].get("gameText")) for s in stems if EA[s]["fm"].get("gameText")}
        log.append(f"Merged {len(stems)} → '{norm_title(EA[keep]['fm']['title'])}' "
                   f"(characters: {', '.join(owners)})" + (" — gameText differed, kept the survivor's" if len(gts) > 1 else ""))

    counts = collections.Counter()
    for (folder, stem), p in sorted(files.items()):
        if folder == "EffectApplications" and stem in remap:
            counts["removed duplicate"] += 1
            continue
        text = open(p, encoding="utf-8").read()
        orig = text
        if folder in ("EffectApplications", "LacrimaEffectApplications"):
            def fix_act(m):
                v = m.group(1).replace("SKill", "Skill").replace("While Unit is on the Field", "While on the Field")
                return f"activationInterval: {v}"
            text = re.sub(r"^activationInterval: (.*)$", fix_act, text, flags=re.M)
            if folder == "EffectApplications" and stem in survivors:
                text = set_line(text, "character", flow([f"[[{o}]]" for o in survivors[stem]]))
        if folder == "Characters":
            raw = C[stem]["fm"].get("effectApplications") or []
            new, changed = [], False
            idx = title_index(EA)
            for item, ln in zip(raw, links(raw)):
                tgt, _ = resolve(ln, EA, idx)
                if tgt is None and ln[0]:
                    cands = [s for s in idx.get(norm_title(ln[0]), [])]
                    tgt = next((s for s in cands if s in remap), cands[0] if cands else None)
                if tgt in remap:
                    item = f"[[{norm_title(EA[remap[tgt]]['fm']['title'])}]]"
                    changed = True
                if item not in new:
                    new.append(item)
                else:
                    changed = True
            if changed:
                text = set_line(text, "effectApplications", flow(new))
        if text != orig:
            counts[f"{folder} edited"] += 1
        out = os.path.join(dst, folder, os.path.basename(p))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write(text)
    with open(os.path.join(os.path.dirname(dst.rstrip("/")), "fix-log.md"), "w", encoding="utf-8") as f:
        f.write("# Changes made to the export copy\n\n")
        for k, v in sorted(counts.items()):
            f.write(f"- {k}: {v}\n")
        f.write("\n## Merges\n\n")
        for line in log:
            f.write(f"- {line}\n")
    print(dict(counts))
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

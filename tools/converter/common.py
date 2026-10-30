"""Shared loading of the Capacities export (game folders only)."""
import glob
import os
import re
import urllib.parse

import yaml

GAME_FOLDERS = ["Characters", "Effects", "EffectApplications", "Lacrimas", "LacrimaEffectApplications"]


def read(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n?(.*)", text, re.S)
    if not m:
        return {}, text
    return (yaml.safe_load(m.group(1)) or {}), m.group(2)


def load(root):
    """Return {folder: {filename_stem: {"fm":..., "body":..., "file":...}}} for game folders only."""
    out = {}
    for folder in GAME_FOLDERS:
        recs = {}
        for p in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
            fm, body = read(p)
            stem = os.path.splitext(os.path.basename(p))[0]
            # the export writes some characters as #UXXXX in file names; links use the real character
            stem = re.sub(r"#U([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), stem)
            recs[stem] = {"fm": fm, "body": body, "file": stem}
        out[folder] = recs
    return out


LINK_WIKI = re.compile(r"^\[\[(.*)\]\]$")
LINK_MD = re.compile(r"^\[(.*)\]\(\.\./(\w+)/(.*)\.md\)$")


def links(value):
    """Normalize a link property to a list of (title, folder|None, file_stem|None)."""
    if value in (None, "", []):
        return []
    if not isinstance(value, list):
        value = [value]
    res = []
    for v in value:
        v = str(v).strip()
        m = LINK_MD.match(v)
        if m:
            res.append((m.group(1), m.group(2), urllib.parse.unquote(m.group(3))))
            continue
        m = LINK_WIKI.match(v)
        if m:
            res.append((m.group(1), None, None))
            continue
        res.append((v, None, None))
    return res


def norm_title(t):
    """Titles sometimes carry non-breaking or doubled spaces; treat them as one space."""
    return re.sub(r"\s+", " ", str(t).replace("\xa0", " ")).strip()


def title_index(recs):
    idx = {}
    for stem, r in recs.items():
        idx.setdefault(norm_title(r["fm"].get("title", stem)), []).append(stem)
    return idx


def resolve(link, recs, tidx):
    """Return (stem or None, problem or None)."""
    title, folder, stem = link
    if stem:
        if stem in recs:
            return stem, None
        # Capacities sometimes mangles file names; fall back to title
    cands = tidx.get(norm_title(title), [])
    if len(cands) == 1:
        return cands[0], None
    if len(cands) > 1:
        return None, f"ambiguous title '{title}' ({len(cands)} records)"
    return None, f"no record titled '{title}'"

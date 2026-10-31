# Capacities export → wiki data

Scripts that turn a Capacities export into the data the wiki is built from.

## Running it

```sh
# unzip the newest export from wizardchronicles/capacities-exports somewhere outside this repo, then:
python3 tools/converter/convert.py "<unzipped>/FT Wizard Chronicle Wiki" /tmp/wiki-out site/src/data/slugs.json site/public
cp /tmp/wiki-out/{units,effects,lacrimas,applications,banners,slugs}.json site/src/data/
cp /tmp/wiki-out/validation-report.md tools/converter/last-validation-report.md
```

The raw export holds personal data (stars, owned units, team notes). **Never copy it into this repo.**
Only the JSON the converter writes is committed.

## What it publishes

- **Allowlist of object types** (`common.GAME_FOLDERS`): Characters, Skills, Effects, EffectApplications,
  Lacrimas, LacrimaEffectApplications, Banners, BannerArts. Any other type in the space (Team Builder
  data, queries, new private types) is never read.
- **Allowlist of fields**: only the properties `convert.py` copies by name reach the output. A property
  added in Capacities stays private until it is added here on purpose.
- **Page text**: Skill pages only (the Lv.1–3 text). Character page text (strategy notes) is dropped
  when the export is read.
- **Guards** that stop the run: any personal field name in the output, or any sentence from a
  Character page.
- With a `public` folder as the last argument, banner art is written to `public/banner-art/<unit id>.webp`
  (old files are removed when art is unlinked).
- Wizards without a portrait in `public/portraits/` get one made from their Cover Image (640px WebP).
  Existing portraits are never replaced, so hand-edited ones (e.g. Cyberpunk Rogue's backdrop) are safe.
  To redo a portrait from Capacities, delete its file and run the converter again.

## Checks worth reading in the report

- **Effect applications no skill links to**: the EA names its character, but none of that character's
  Skills lists it, so the effect is missing from that wizard's skill tables and the Effect Finder.
- **Debut banners**: a wizard with more than one Debut Banner, or a Banner and wizard that disagree.
- **Addresses retired**: a record was renamed or deleted, so links to its old page stop working.

## If a count looks wrong

Capacities sometimes doesn't sync an object created through the MCP to the desktop app, and the export
is built by the app. Compare with the server (the connector lists what the server has). If the object
is there, make a real edit to it through the connector (re-saving the same values doesn't count). That
pushes it to the app. Reload the app and export again.

## Other files

- `common.py`: shared export reading and link resolution.
- `extract_skills.py`, `fix_export.py`: one-off migration scripts from the move to the new space.

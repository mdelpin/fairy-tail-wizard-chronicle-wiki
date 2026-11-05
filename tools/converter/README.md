# Capacities export → wiki data

Scripts that turn a Capacities export into the data the wiki is built from.

## Running it

```sh
# unzip the newest export from wizardchronicles/capacities-exports somewhere outside this repo, then:
python3 tools/converter/convert.py "<unzipped>/FT Wizard Chronicle Wiki" /tmp/wiki-out site/src/data/slugs.json site/public
cp /tmp/wiki-out/{units,effects,lacrimas,applications,banners,companions,enemies,events,slugs}.json site/src/data/
cp /tmp/wiki-out/validation-report.md tools/converter/last-validation-report.md
```

The raw export holds personal data (stars, owned units, team notes). **Never copy it into this repo.**
Only the JSON the converter writes is committed.
The unfinished Banner named `Untitled` is ignored, including in validation.

## What it publishes

- **Allowlist of object types** (`common.GAME_FOLDERS`): Characters, Skills, Effects, EffectApplications,
  Lacrimas, LacrimaEffectApplications, Banners, BannerArts, SkillIcons, Companions,
  CompanionEffectApplications, Enemies, EnemySkills, EnemyEffectApplications, Events. Any other type in the space (Team Builder
  data, queries, new private types) is never read.
- **Allowlist of fields**: only the properties `convert.py` copies by name reach the output. A property
  added in Capacities stays private until it is added here on purpose.
- **Page text**: only Skill pages (the Lv.1–3 text) are published. An Event's leading paragraph
  starting `Dates from the in-game ` is read for date validation only; an unresolved discrepancy
  sets `dateSource: Conflicting`. Source prose, links, notice screenshots and every Enemy page
  body (including unverified stat tables) are dropped. Character page text is always private.
- **Enemies**: named skills have no levels and support Normal, Special, Ultimate and Additional.
  Their applications share Effect definitions but use `source: enemy` and a separate site lookup;
  they do not enter wizard Effect Finder counts. `Constant` with no duration displays as permanent;
  an empty duration on its own does not. Enemy/Event dates are JST calendar dates, like Banners;
  hours and source evidence stay in the Event's leading date/source paragraph in Capacities.
- **Companions**: public skill and progression data, introduction details, and links to companion
  applications. The applications share the wiki's Effect definitions and have their own
  `source: companion` records in `applications.json`. A banner's `companions` links are separate
  from its wizard links. Owned Effect is calculated as `ownedStart + ownedStep × stars`. Set
  `skillLevelFromStars` per companion, for example `0, 1, 7` for Block Happy. When game text is
  identical across levels except for the duration, write `{duration}` in `gameText` where the site
  should insert the level's duration including its unit, such as `2s`. Literal game text is also
  supported. Without game text, the site displays the recorded application details.
- **Guards** that stop the run: any personal field name in the output, or any sentence from a
  Character page.
- With a `public` folder as the last argument, banner art is written to `public/banner-art/<unit id>.webp`
  (old files are removed when art is unlinked).
- Wizards without a portrait in `public/portraits/` get one made from their Cover Image (640px WebP).
  Existing portraits are never replaced, so hand-edited ones (e.g. Cyberpunk Rogue's backdrop) are safe.
  To redo a portrait from Capacities, delete its file and run the converter again.
- Companion cover images go to `public/companions/<id>.webp` (up to 320px, with transparency).
  The converter removes stale companion WebPs.
- Enemy and Event cover images go to `public/enemies/<id>.webp` (up to 640px) and
  `public/events/<id>.webp` (up to 800px), preserving transparency.

## Checks worth reading in the report

- **Effect applications no skill links to**: the EA names its character, but none of that character's
  Skills lists it, so the effect is missing from that wizard's skill tables and the Effect Finder.
- **Debut banners**: a wizard with more than one Debut Banner, or a Banner and wizard that disagree.
- **Companions**: missing skill, progression or introduction data, outlier progression values,
  and disagreements between a Companion and Banner.
- **Addresses retired**: a record was renamed or deleted, so links to its old page stop working.
- **Enemy links**: mismatched Enemy/Skill/Application ownership or Enemy/Event links, unused
  applications and unused skills. Missing effects, triggers, kinds, text and dates are also reported.
- **Event date sources need review**: a date/source note explicitly records an unresolved discrepancy.

## If a count looks wrong

Capacities sometimes doesn't sync an object created through the MCP to the desktop app, and the export
is built by the app. Compare with the server (the connector lists what the server has). If the object
is there, make a real edit to it through the connector (re-saving the same values doesn't count). That
pushes it to the app. Reload the app and export again.

## Other files

- `common.py`: shared export reading and link resolution.
- `extract_skills.py`, `fix_export.py`: one-off migration scripts from the move to the new space.
- `test_companions.py`: a synthetic Block Happy export tests the converter and privacy guard.
  Run it with `python3 tools/converter/test_companions.py` (PyYAML and Pillow).
- `test_enemies.py`: checks all four skill kinds, timed/permanent effects, exported links,
  source-note privacy, images, validation, and unchanged legacy outputs.
  Run it with `python3 tools/converter/test_enemies.py` (PyYAML and Pillow).

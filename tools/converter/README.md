# Capacities export → wiki data

Scripts that turn a Capacities export into the data the wiki is built from.

- `convert.py <export dir> <skills dir> <out dir> [slugs.json]`: reads only the game object types
  (Characters, Skills, Effects, EffectApplications, Lacrimas, LacrimaEffectApplications), copies only
  published fields, writes JSON plus `validation-report.md`, and stops if any personal field
  (stars, owned, equipped lacrimas, team contribution, synergy) would reach the output.
- `extract_skills.py`: one-off migration that split each character's Kit Details into Skill objects.
- `fix_export.py`: one-off cleanup used before the import into the new space.
- `common.py`: shared export reading and link resolution.

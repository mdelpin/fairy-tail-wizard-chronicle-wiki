"""Enemy conversion, graph validation and privacy, alongside the existing companion fixture."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_companions import record, sample


class EnemyConverterTest(unittest.TestCase):
    def test_enemy_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root, output, public = (Path(directory) / name for name in ("export", "json", "public"))
            sample(root)
            command = [sys.executable, str(Path(__file__).with_name("convert.py")), str(root),
                       str(output), str(output / "slugs.json"), str(public)]
            run = lambda: subprocess.run(command, check=True, capture_output=True)
            read = lambda name: json.loads((output / f"{name}.json").read_text())
            run()
            baseline = {name: read(name) for name in ("units", "lacrimas", "banners", "companions", "applications")}
            record(root, "Banners", "Untitled")
            for name, family, mechanic in [("Damage", "Damage", "Instant Damage"), ("Shield", "Shield", "Mitigation"),
                                           ("Burn", "Burn", "Damage Over Time")]:
                record(root, "EffectFamilies", family, mechanic=mechanic)
                record(root, "Effects", name, effectFamily=[f"[[{family}]]"], polarity="Harmful")
            record(root, "SkillIcons", "Fixture Icon", number=41)
            app_specs = [
                ("Normal Damage", "Damage", "Normal Attack", "Inflicts", "Enemies in Range", None, None, 140),
                ("Shield", "Shield", "Normal Skill Hit", "Provides", "Self", 0.2, 3, None),
                ("Constant Buff", "Shield", "Constant", "Provides", "Self", None, None, None),
                ("Ultimate Damage", "Damage", "Every 8 sec", "Inflicts", "All Enemies", None, None, 650),
                ("Burn", "Burn", "Every 8 sec, After Attack Hits", "Inflicts", "Each Target Hit", None, 4, None),
                ("Additional Burn", "Burn", "Every 6 sec", "Inflicts", "All Enemies", 0.3, 3, None),
            ]
            for title, effect, trigger, kind, target, chance, duration, value in app_specs:
                record(root, "EnemyEffectApplications", title, effect=f"[[{effect}]]", enemy=["[[Deliora]]"],
                       activationInterval=trigger, applicationType=kind, target=target, chance=chance,
                       durationSeconds=duration, effectValue=value,
                       valueUnit="Percent of Own ATK" if value else None, ownedUnit=True,
                       conditions="After the normal hit" if title == "Shield" else None,
                       requiredEffectFamilies=["[[Burn]]"] if title == "Additional Burn" else None,
                       effectFamilyMatchingRule="Any" if title == "Additional Burn" else None)
            skill_apps = {"Normal": ["Normal Damage", "Shield"], "Special": ["Constant Buff"],
                          "Ultimate": ["Ultimate Damage", "Burn"], "Additional": ["Additional Burn"]}
            for kind, applications in skill_apps.items():
                record(root, "EnemySkills", f"Deliora {kind}", kind=kind, skillName=f"{kind} skill",
                       enemies=["[[Deliora]]"], gameText=f"Public {kind} game text.",
                       skillIcon=["[[Fixture Icon]]"], levelTextSource="PRIVATE LEVEL SOURCE",
                       effectApplications=[f"[{app}](../EnemyEffectApplications/{app.replace(' ', '%20')}.md)"
                                           for app in applications])
            record(root, "Enemies", "Deliora", type_="Raid", role="Boss", currentStars=11,
                   coverImage="[Boss](../Images/Media/fixture-companion.png)",
                   skills=[f"[[Deliora {kind}]]" for kind in reversed(skill_apps)],
                   events=["[[Guild Raid]]"], immuneTo=[])
            with (root / "Enemies" / "Deliora.md").open("a") as f:
                f.write("\nPRIVATE ENEMY BODY AND UNVERIFIED STATS\n")
            record(root, "Events", "Guild Raid", type_="Guild Raid", start="2026-11-05T00:00:00.000Z",
                   end="2026-11-13T00:00:00.000Z", enemies=["[[Deliora]]"],
                   coverImage="[Event](../Images/Media/fixture-event.png)")
            with (root / "Events" / "Guild Raid.md").open("a") as f:
                f.write("\nDates from the in-game notice: 5–13 November JST. "
                        "[Official source](https://example.com/notice); conflicting dates unresolved.\n\n"
                        "PRIVATE EVENT BODY AND SCREENSHOTS\n")
            run()
            enemy, = read("enemies")
            event, = read("events")
            apps = {a["id"]: a for a in read("applications") if a["source"] == "enemy"}
            self.assertEqual(len(apps), 6)
            self.assertEqual([s["kind"] for s in enemy["skills"]], list(skill_apps))
            self.assertEqual(enemy["events"], [event["id"]])
            self.assertEqual(event["enemies"], [enemy["id"]])
            self.assertEqual((event["start"], event["end"]), ("2026-11-05", "2026-11-13"))
            self.assertNotIn("sources", event)
            self.assertNotIn("dateNote", event)
            self.assertEqual(event["dateSource"], "Conflicting")
            self.assertTrue((public / "enemies" / enemy["image"]).is_file())
            self.assertTrue((public / "events" / event["image"]).is_file())
            self.assertEqual(apps["shield"]["chance"], 0.2)
            self.assertEqual(apps["shield"]["durationSeconds"], 3)
            self.assertEqual(apps["constant-buff"]["trigger"]["events"], ["constant"])
            self.assertIsNone(apps["constant-buff"]["durationSeconds"])
            self.assertEqual(apps["additional-burn"]["trigger"]["everySeconds"], 6)
            self.assertEqual(apps["additional-burn"]["requires"]["match"], "Any")
            self.assertTrue(all(s["icon"] == 41 and isinstance(s["gameText"], str) for s in enemy["skills"]))
            for name, before in baseline.items():
                after = read(name)
                if name == "applications":
                    after = [a for a in after if a["source"] != "enemy"]
                self.assertEqual(after, before, name)
            blob = "".join(p.read_text() for p in output.glob("*.json"))
            self.assertNotIn("https://example.com/notice", blob)
            self.assertNotIn("Dates from the in-game notice", blob)
            for private in ('"ownedUnit"', '"currentStars"', "PRIVATE ENEMY", "PRIVATE EVENT", "PRIVATE LEVEL"):
                self.assertNotIn(private, blob)
            report = (output / "validation-report.md").read_text()
            self.assertIn("1 enemies, 4 enemy skills, 6 enemy effect applications, 1 events", report)
            self.assertIn("Event date sources need review", report)
            self.assertNotIn("Broken or ambiguous links", report)
            self.assertNotIn("Missing required values", report)
            self.assertNotIn("Untitled", report)
            self.assertNotIn("Untitled", blob)

            record(root, "EnemySkills", "Deliora Special", kind="Special", skillName="Special skill",
                   enemies=["[[Missing boss]]"], gameText="Permanent buff.", effectApplications=["[[Missing effect]]"])
            record(root, "Events", "Guild Raid", start="2026-11-13", end="2026-11-05", enemies=["[[Deliora]]"])
            record(root, "EnemyEffectApplications", "Bad chance", enemy=["[[Deliora]]"], effect="[[Shield]]",
                   chance="unknown", durationSeconds=-1)
            run()
            report = (output / "validation-report.md").read_text()
            for problem in ("Broken or ambiguous links", "Enemy links", "Enemy applications no skill links to",
                            "ends before it starts", "chance needs a number", "durationSeconds is negative"):
                self.assertIn(problem, report)


if __name__ == "__main__":
    unittest.main()

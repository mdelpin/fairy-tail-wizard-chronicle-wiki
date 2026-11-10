"""Run the converter against a hand-made export in the real Companion model, with synthetic private fields."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
import yaml


def record(root, folder, title, body="", stem=None, **fields):
    # like the real export, a title's "/" is written as a space in the file name
    path = root / folder / f"{stem or title}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump({"title": title, **fields}, allow_unicode=True) + "---\n" + body,
                    encoding="utf-8")


def sample(root):
    media = root / "Images" / "Media"
    media.mkdir(parents=True, exist_ok=True)
    portrait = Image.new("RGBA", (480, 640))
    ImageDraw.Draw(portrait).rounded_rectangle((60, 140, 420, 500), radius=80, fill="#d9b97b")
    portrait.save(media / "fixture-companion.png")
    Image.new("RGB", (800, 450), "#4a2f1e").save(media / "fixture-event.png")
    record(root, "Parameters", "Attack", displayName="ATK")
    record(root, "Parameters", "HP", displayName="HP")
    record(root, "EffectFamilies", "ATK", mechanic="Stat Modifier", affectedStats=["[[Attack]]"])
    record(root, "Effects", "High ATK Increase", effectFamily=["[[ATK]]"], direction="Up", magnitudeTier="High",
           polarity="Beneficial")
    apps = []
    for target in ("All Allies", "Lowest HP Ally"):
        title = f"High ATK Increase → {target} – Every 6 sec / 2 sec"
        stem = title.replace("/", " ")
        record(root, "CompanionEffectApplications", title, stem=stem, effect="[[High ATK Increase]]", applicationType="Provides",
               target=target, activationInterval="Every 6 sec", durationSeconds=2,
               companion=["[[Block Happy]]"] if target == "All Allies" else ["[[Block Happy]]", "[[Sample Spirit]]"])
        apps.append(f"[{title}](../CompanionEffectApplications/{stem.replace(' ', '%20')}.md)")
    banner = "Sample Event Banner"
    record(root, "Banners", banner, bannerType="Special", startDate="2026-11-01T00:00:00.000Z",
           companions=["[[Block Happy]]"], coverImage="[Fixture event](../Images/Media/fixture-event.png)")
    # owned and numberOfStars are personal and must never be published
    record(root, "Companions", "Block Happy", identity="Happy", companionType="Exceed", rarity="UR",
           bonusStat=["[[Attack]]"], ownedStart=50, ownedStep=50, companionSkill=["[[Block Happy — Skill]]"],
           owned=True, numberOfStars=11, stepConfirmed=True, introducedOn="2026-11-01T00:00:00.000Z",
           introducedVia="Event", introducedBanner=[f"[[{banner}]]"],
           coverImage="[Fixture portrait](../Images/Media/fixture-companion.png)")
    record(root, "CompanionSkills", "Block Happy — Skill",
           body="**Lv.1** Every 6 sec, grants all allies [High] ATK Increase for 2 sec.\n\n"
                "**Lv.2** Every 6 sec, grants all allies [High] ATK Increase for 3 sec.\n\n"
                "**Lv.3**\n\nEvery 6 sec, grants all allies [High] ATK Increase for 4 sec.\n",
           skillName="Happy Ale", companion=["[[Block Happy]]"], levelTextSource="in-game",
           effectApplications=apps, notes="private editor note: the step is inferred")
    # an unowned card: Lv.1 only, step unknown
    record(root, "Companions", "Sample Spirit", identity="Sample", companionType="Celestial Spirit", rarity="SR",
           bonusStat=["[[HP]]"], ownedStart=0, owned=False, companionSkill=["[[Sample Spirit — Skill]]"])
    record(root, "CompanionSkills", "Sample Spirit — Skill", body="**Lv.1** Every 6 sec, grants a buff.\n",
           skillName="Sample skill", companion=["[[Sample Spirit]]"], levelTextSource="in-game",
           effectApplications=[apps[1]])
    # a placeholder skill: no text source, no effects
    record(root, "Companions", "Placeholder Spirit", identity="Sample", companionType="Celestial Spirit", rarity="UR",
           bonusStat=["[[HP]]"], ownedStart=100, companionSkill=["[[Placeholder Spirit — Skill]]"])
    record(root, "CompanionSkills", "Placeholder Spirit — Skill", body="**Lv.1** Not available.\n",
           skillName="Not available", companion=["[[Placeholder Spirit]]"], effectApplications=[])
    # a live Issue on a companion skill: its Public Note is published, everything else stays private
    record(root, "Issues", "Happy Ale cut off", body="ticket #19863 secret-support-token", problemType="Truncated Text",
           status="Reported", evidence=["[[Screenshot of the bug]]"],
           affectedCompanionSkill=["[[Block Happy — Skill]]"], publicNote="The English text is cut off.")


class CompanionConverterTest(unittest.TestCase):
    def run_converter(self, root, output, public):
        command = [sys.executable, "-O", str(Path(__file__).with_name("convert.py")), str(root),
                   str(output), str(output / "slugs.json"), str(public)]
        subprocess.run(command, check=True, capture_output=True)
        return lambda name: json.loads((output / f"{name}.json").read_text())

    def test_sample_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "export"
            output = Path(directory) / "json"
            public = Path(directory) / "public"
            sample(root)
            (public / "companions").mkdir(parents=True)
            stale = public / "companions" / "retired.webp"
            stale.touch()
            read = self.run_converter(root, output, public)
            happy, placeholder, spirit = sorted(read("companions"), key=lambda c: c["name"])

            # privacy: personal fields and the editor's private notes never reach any output file
            for published in output.glob("*.json"):
                text = published.read_text()
                for private in ('"owned"', '"numberOfStars"', "secret-support-token", "private editor note"):
                    self.assertNotIn(private, text)

            self.assertEqual(happy["type"], "Exceed")
            self.assertEqual(happy["identity"], "Happy")
            self.assertEqual(happy["ownedStat"], "ATK")
            self.assertEqual(happy["skillName"], "Happy Ale")
            self.assertEqual(happy["skillLevelFromStars"], [0, 1, 7])
            self.assertEqual(happy["ownedStart"] + 11 * happy["ownedStep"], 600)
            self.assertIs(happy["stepConfirmed"], True)
            self.assertEqual(happy["introducedOn"], "2026-11-01")
            self.assertEqual(sorted(happy["gameText"]), ["Lv1", "Lv2", "Lv3"])  # inline and next-line text
            self.assertIn("for 4 sec", happy["gameText"]["Lv3"])
            self.assertEqual(happy["issues"], [{"problemType": "Truncated Text", "note": "The English text is cut off."}])
            self.assertEqual(len(happy["applications"]), 2)

            # an unowned card publishes only what was recorded: Lv.1, no step
            self.assertEqual(spirit["type"], "Celestial Spirit")
            self.assertEqual(list(spirit["gameText"]), ["Lv1"])
            self.assertIsNone(spirit["ownedStep"])
            self.assertIsNone(spirit["stepConfirmed"])
            self.assertEqual(len(spirit["applications"]), 1)
            self.assertEqual(spirit["issues"], [])

            # a placeholder skill has no effects and still publishes
            self.assertEqual(placeholder["applications"], [])
            self.assertEqual(placeholder["skillName"], "Not available")

            apps = [a for a in read("applications") if a["source"] == "companion"]
            self.assertEqual(len(apps), 2)
            self.assertEqual({a["effect"] for a in apps}, {"high-atk-increase"})
            for app in apps:
                self.assertEqual(app["durationSeconds"], 2)
                self.assertEqual(app["trigger"]["everySeconds"], 6)

            banner, = read("banners")
            self.assertEqual(banner["id"], happy["introducedBanner"])
            self.assertEqual(banner["companions"], ["block-happy"])
            self.assertEqual(read("units"), [])
            self.assertFalse(stale.exists())
            with Image.open(public / "companions" / happy["image"]) as image:
                self.assertEqual(image.size, (240, 320))
                self.assertEqual(image.mode, "RGBA")
            report = (output / "validation-report.md").read_text()
            self.assertIn("Owned step unknown", report)  # Sample Spirit
            self.assertIn("placeholder skills are expected", report)  # Placeholder Spirit
            self.assertNotIn("Missing required values", report)

    def test_identity_matching_is_scoped_by_type(self):
        """The same identity word in two companion types, or on a wizard, is never a near-duplicate."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "export"
            output = Path(directory) / "json"
            sample(root)
            record(root, "Characters", "Test Irene", rarity="UR", attribute="Technique", identity="Happy",
                   collection="Test")
            for kind in ("Dragon", "Celestial Spirit"):
                record(root, "Companions", f"{kind} Happy", identity="Happy", companionType=kind, rarity="UR",
                       bonusStat=["[[HP]]"], ownedStart=100, ownedStep=100)
            self.run_converter(root, output, Path(directory) / "public")
            self.assertNotIn("Near-duplicate", (output / "validation-report.md").read_text())

            for title, identity in (("Lily A", "Panther Lily"), ("Lily B", "Pantherlily")):
                record(root, "Companions", title, identity=identity, companionType="Exceed", rarity="UR",
                       bonusStat=["[[HP]]"], ownedStart=100, ownedStep=100)
            self.run_converter(root, output, Path(directory) / "public")
            self.assertIn("Exceed identity: 'Panther Lily' vs 'Pantherlily'",
                          (output / "validation-report.md").read_text())

    def test_problems_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "export"
            output = Path(directory) / "json"
            sample(root)
            record(root, "Companions", "Needs review", companionType="Fairy", introducedVia="Event",
                   introducedBanner=["[[Sample Event Banner]]"], ownedStart=50, ownedStep=1000, stepConfirmed="yes")
            self.run_converter(root, output, Path(directory) / "public")
            report = (output / "validation-report.md").read_text()
            for warning in ("no Companion Skill names this companion", "introducedOn is empty", "is not one of",
                            "implausible Owned Effect progression", "does not list it", "rarity is empty",
                            "identity is empty", "bonusStat is empty", "stepConfirmed must be true or false"):
                self.assertIn(warning, report)


if __name__ == "__main__":
    unittest.main()

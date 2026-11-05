"""Run the converter against a hand-made export with synthetic private fields."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
import yaml


def record(root, folder, title, **fields):
    path = root / folder / f"{title}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump({"title": title, **fields}) + "---\n", encoding="utf-8")


def sample(root):
    media = root / "Images" / "Media"
    media.mkdir(parents=True, exist_ok=True)
    portrait = Image.new("RGBA", (480, 640))
    ImageDraw.Draw(portrait).rounded_rectangle((60, 140, 420, 500), radius=80, fill="#d9b97b")
    portrait.save(media / "fixture-companion.png")
    Image.new("RGB", (800, 450), "#4a2f1e").save(media / "fixture-event.png")
    applications = []
    for stat in ("ATK", "DEF"):
        effect = f"High {stat} Increase"
        application = f"{effect} - Every 6 sec"
        if not (root / "Effects" / f"{effect}.md").exists():
            record(root, "Effects", effect, effectFamily=stat, direction="Up", magnitudeTier="High",
                   mechanic="Stat Modifier")
        record(root, "CompanionEffectApplications", application, effect=f"[[{effect}]]",
               companions=["[[Block Happy]]", "[[Sample Spirit]]"],
               applicationType="Provides", target="All Allies", activationInterval="Every 6 sec",
               durationSecondsLv1=2, durationSecondsLv2=3, durationSecondsLv3=4,
               gameText="Every 6s, grants all allies for {duration}: [High] ATK Increase and [High] DEF Increase.")
        applications.append(f"[[{application}]]")
    banner = "Sample Event Banner"
    record(root, "Banners", banner, bannerType="Special", startDate="2026-11-01T00:00:00.000Z",
           companions=["[[Block Happy]]"], coverImage="[Fixture event](../Images/Media/fixture-event.png)")
    record(root, "Companions", "Block Happy", companionType="Exceed", rarity="UR", skillName="Happy Ale",
           skillLevelFromStars="0, 1, 7", ownedStat="Attack", ownedStart=50, ownedStep=50, ownedUnit=True,
           currentStars=11, introducedOn="2026-11-01T00:00:00.000Z", introducedVia="Event",
           introducedBanner=f"[[{banner}]]", companionEffectApplications=applications,
           coverImage="[Fixture portrait](../Images/Media/fixture-companion.png)")
    record(root, "Companions", "Sample Spirit", companionType="Spirit", rarity="SR", skillName="Sample skill",
           skillLevelFromStars="0, 2, 8", ownedStat="HP", ownedStart=0, ownedStep=25)


class CompanionConverterTest(unittest.TestCase):
    def test_sample_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "export"
            output = Path(directory) / "json"
            public = Path(directory) / "public"
            sample(root)
            (public / "companions").mkdir(parents=True)
            stale = public / "companions" / "retired.webp"
            stale.touch()
            command = [sys.executable, "-O", str(Path(__file__).with_name("convert.py")), str(root),
                       str(output), str(output / "slugs.json"), str(public)]
            subprocess.run(command, check=True, capture_output=True)
            read = lambda name: json.loads((output / f"{name}.json").read_text())
            happy, spirit = read("companions")
            for published in output.glob("*.json"):
                for private in ("ownedUnit", "currentStars"):
                    self.assertNotIn(f'"{private}"', published.read_text())
            self.assertEqual(happy["skillLevelFromStars"], [0, 1, 7])
            self.assertEqual(happy["ownedStart"] + 11 * happy["ownedStep"], 600)
            self.assertEqual(spirit["ownedStart"], 0)
            self.assertEqual(happy["applications"], spirit["applications"])
            self.assertEqual(happy["introducedOn"], "2026-11-01")
            apps = read("applications")
            self.assertEqual(len(apps), 2)
            self.assertEqual({a["effect"] for a in apps}, {"high-atk-increase", "high-def-increase"})
            for app in apps:
                self.assertEqual(app["source"], "companion")
                self.assertEqual(app["durationByLevel"], [2, 3, 4])
                self.assertEqual(app["trigger"]["everySeconds"], 6)
            banner, = read("banners")
            self.assertEqual(banner["id"], happy["introducedBanner"])
            self.assertEqual(banner["companions"], ["block-happy"])
            self.assertEqual(banner["units"], [])
            self.assertEqual(read("units"), [])
            self.assertFalse(stale.exists())
            with Image.open(public / "companions" / happy["image"]) as image:
                self.assertEqual(image.size, (240, 320))
                self.assertEqual(image.mode, "RGBA")
            report = output / "validation-report.md"
            self.assertIn("0 issues", report.read_text())
            self.assertIn("0 effect applications", report.read_text())

            record(root, "Companions", "Needs review", introducedVia="Event", skillLevelFromStars="0, 7, 7",
                   introducedBanner="[[Sample Event Banner]]", ownedStart=50, ownedStep=1000)
            subprocess.run(command, check=True, capture_output=True)
            for warning in ("no companion effect application", "introducedOn is empty", "must start at 0",
                            "implausible Owned Effect progression", "does not list it", "companionType is empty"):
                self.assertIn(warning, report.read_text())


if __name__ == "__main__":
    unittest.main()

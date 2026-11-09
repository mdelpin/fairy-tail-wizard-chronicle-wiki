"""Run the converter against a hand-made export with synthetic Issues (live, resolved, malformed)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

SECRETS = ("secret-support-token", "ticket #19863", "should not appear", "Screenshot of the bug")


def record(root, folder, title, body="", **fields):
    path = root / folder / f"{title}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n" + yaml.safe_dump({"title": title, **fields}, allow_unicode=True) + "---\n" + body,
                    encoding="utf-8")


def sample(root):
    record(root, "Characters", "Test Mage", rarity="UR", attribute="Technique", identity="Test", collection="Test",
           skills=[f"[[Test Mage — {k}]]" for k in ("Normal", "Special", "Ultimate")])
    for kind in ("Normal", "Special", "Ultimate"):
        record(root, "Skills", f"Test Mage — {kind}", unit="[[Test Mage]]", kind=kind, skillName=kind)
    record(root, "Lacrimas", "Test Lacrima", gameText="[Mid] ATK Decrease for 2 sec.")

    private = "ticket #19863 secret-support-token"
    record(root, "Issues", "Live with note", body=private, problemType="Value Anomaly", status="Reported",
           reportedOn="2026-11-04T00:00:00.000Z", evidence=["[[Screenshot of the bug]]"],
           affectedCharacterSkill=["[[Test Mage — Ultimate]]"], publicNote="Lv.3 damage is lower than Lv.2.")
    record(root, "Issues", "Live without note", body=private, problemType="Missing Data",
           affectedLacrima=["[[Test Lacrima]]"])
    record(root, "Issues", "Resolved", body=private, problemType="Wrong Wording", resolution="Fixed in Game",
           affectedCharacterSkill=["[[Test Mage — Special]]"], publicNote="should not appear")
    record(root, "Issues", "Linked to nothing", problemType="Other")
    record(root, "Issues", "Two kinds", problemType="Other", affectedCharacterSkill=["[[Test Mage — Normal]]"],
           affectedLacrima=["[[Test Lacrima]]"], publicNote="Both.")
    record(root, "Issues", "Odd values", problemType="Made Up", resolution="Mystery",
           affectedCharacterSkill=["[[Test Mage — Special]]"])


class IssueConverterTest(unittest.TestCase):
    def test_live_issues_publish_only_their_public_note(self):
        with tempfile.TemporaryDirectory() as directory:
            root, output = Path(directory) / "export", Path(directory) / "json"
            sample(root)
            subprocess.run([sys.executable, "-O", str(Path(__file__).with_name("convert.py")), str(root),
                            str(output), str(output / "slugs.json")], check=True, capture_output=True)
            read = lambda name: json.loads((output / f"{name}.json").read_text())
            skills = {s["kind"]: s for s in read("units")[0]["skills"]}
            self.assertEqual(skills["Ultimate"]["issues"],
                             [{"problemType": "Value Anomaly", "note": "Lv.3 damage is lower than Lv.2."}])
            self.assertEqual(skills["Normal"]["issues"], [{"problemType": "Other", "note": "Both."}])
            # resolved, note-less and malformed issues publish nothing; untouched records keep their old shape
            self.assertNotIn("issues", skills["Special"])
            lacrima, = read("lacrimas")
            self.assertEqual(lacrima["issues"], [{"problemType": "Other", "note": "Both."}])

            published = "".join(p.read_text() for p in output.glob("*.json"))
            for secret in SECRETS:
                self.assertNotIn(secret, published)
            for private in ("evidence", "reportedOn", "status", "resolution", "affectedLacrima"):
                self.assertNotIn(f'"{private}"', published)

            report = (output / "validation-report.md").read_text()
            for expected in ("4 live game issues", "Live issues without a Public Note",
                             "Issues linked to nothing", "Issues linked to more than one kind of record",
                             "Problem Type 'Made Up'", "Resolution 'Mystery'"):
                self.assertIn(expected, report)
            self.assertNotIn("Issue 'Resolved'", report.split("## Live game issues")[1].split("## ")[0])


if __name__ == "__main__":
    unittest.main()

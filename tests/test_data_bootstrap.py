"""Dependency-free checks usable before the development environment is installed."""

import tempfile
import unittest
import zipfile
from pathlib import Path

from phishguard.research.data import MEMBER, describe, map_label, read_archive


class DataBootstrapTests(unittest.TestCase):
    def test_label_direction(self):
        self.assertEqual(map_label("1"), 0)
        self.assertEqual(map_label("0"), 1)
        for bad in ("2", "", "phishing", "1.0"):
            with self.assertRaises(ValueError):
                map_label(bad)

    def test_synthetic_archive_schema_and_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(
                    MEMBER,
                    "\ufeffURL,label,Unused\nhttps://example.org,1,999\n"
                    "http://verify.example.test/login,0,123\n",
                )
            rows = read_archive(path, verify=False)
            self.assertEqual(describe(rows)["phishing"], 1)
            self.assertEqual(rows[0], ("https://example.org", 0))
            with self.assertRaisesRegex(ValueError, "checksum"):
                read_archive(path)

    def test_unexpected_members_are_not_extracted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape.csv", "URL,label\n")
            with self.assertRaisesRegex(ValueError, "members"):
                read_archive(path, verify=False)

    def test_missing_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr(MEMBER, "Domain,target\nexample.org,1\n")
            with self.assertRaisesRegex(ValueError, "columns"):
                read_archive(path, verify=False)


if __name__ == "__main__":
    unittest.main()

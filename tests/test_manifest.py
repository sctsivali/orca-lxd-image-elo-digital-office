import pathlib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ManifestContract(unittest.TestCase):
    def test_manifest_is_safe_and_complete(self) -> None:
        manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema"], "orca.image-manifest/v1")
        self.assertEqual(manifest["network"]["default_policy"], "private")
        self.assertIn(manifest["publication"]["state"], {"unpublished", "qualification-pending"})
        self.assertNotEqual(manifest["publication"]["state"], "published")
        self.assertIsInstance(manifest["minimum_resources"]["cpu"], int)
        self.assertTrue(manifest["upstream"]["source_url"].startswith("https://"))
        self.assertTrue((ROOT / manifest["branding"]["local_path"]).is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)

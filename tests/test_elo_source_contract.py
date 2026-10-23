import pathlib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


class EloSourceContract(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
        self.readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.build = (ROOT / "recipes/build.sh").read_text(encoding="utf-8").lower()
        self.acceptance = (ROOT / "recipes/acceptance.sh").read_text(encoding="utf-8").lower()

    def test_slug_and_unpublished_vm(self) -> None:
        self.assertEqual(self.manifest["slug"], "elo-digital-office")
        self.assertEqual(self.manifest["instance_type"], "virtual-machine")
        self.assertEqual(self.manifest["application"]["version"], "25.0")
        self.assertIs(self.manifest["build"]["ready"], False)
        self.assertEqual(self.manifest["publication"]["state"], "qualification-pending")

    def test_root_disk_matches_qcow2_virtual_size_80_gib(self) -> None:
        self.assertEqual(self.manifest["minimum_resources"]["storage_gib"], 80)
        self.assertIn("80 gib", self.readme)

    def test_setup_port_is_private_loopback_only(self) -> None:
        endpoints = {item["name"]: item for item in self.manifest["exposer"]["endpoints"]}
        self.assertEqual(set(endpoints), {"setup"})
        self.assertEqual(endpoints["setup"]["target_port"], 7458)
        self.assertIs(endpoints["setup"]["default_public"], False)
        self.assertIn("127.0.0.1:7458", self.readme)
        self.assertIn("do not bind", self.readme)
        self.assertIn("0.0.0.0", self.readme)
        self.assertNotIn("9090", self.readme)
        self.assertNotIn("9080", self.readme)

    def test_database_port_is_not_an_exposer_endpoint(self) -> None:
        ports = {item["target_port"] for item in self.manifest["exposer"]["endpoints"]}
        self.assertNotIn(5432, ports)
        self.assertNotIn(9200, ports)

    def test_readme_states_server_setup_stop_and_no_lab_snapshot(self) -> None:
        self.assertIn("unpublished", self.readme)
        self.assertIn("server setup", self.readme)
        self.assertIn("license", self.readme)
        self.assertIn("not a lab snapshot", self.readme)
        self.assertIn("exposer", self.readme)
        self.assertIn("build", self.readme)

    def test_recipes_forbid_baked_license(self) -> None:
        combined = self.build + "\n" + self.acceptance
        self.assertIn("license", combined)
        self.assertIn("7458", combined)
        self.assertIn("passed", self.acceptance)
        self.assertNotIn("rest/apply", self.build)
        self.assertNotIn("images.orca.id", self.acceptance)

    def test_logo_is_official_elo_raster_not_template_placeholder(self) -> None:
        logo = ROOT / self.manifest["branding"]["local_path"]
        data = logo.read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertGreater(len(data), 1024)
        self.assertNotEqual(
            __import__("hashlib").sha256(data).hexdigest(),
            "a0e6376723612af36978d455ed7ae9eb54e3c358d81d7b8dc8e51e4bfb5fd28f",
        )
        self.assertEqual(
            self.manifest["branding"]["logo_source_url"],
            "https://www.elo.com/typo3conf/ext/nelo_elocom_templates/Resources/Public/Images/logo_elo.svg",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

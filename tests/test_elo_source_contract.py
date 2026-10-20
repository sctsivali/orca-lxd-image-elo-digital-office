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
        self.assertEqual(self.manifest["publication"]["state"], "unpublished")

    def test_setup_port_is_private(self) -> None:
        endpoints = {item["name"]: item for item in self.manifest["exposer"]["endpoints"]}
        self.assertIn("setup", endpoints)
        self.assertEqual(endpoints["setup"]["target_port"], 7458)
        self.assertIs(endpoints["setup"]["default_public"], False)
        for item in self.manifest["exposer"]["endpoints"]:
            self.assertIs(item["default_public"], False)

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
        self.assertIn("not run", self.acceptance)
        self.assertNotIn("rest/apply", self.build)


if __name__ == "__main__":
    unittest.main(verbosity=2)

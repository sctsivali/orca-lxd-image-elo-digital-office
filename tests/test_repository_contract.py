import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "REPOSITORY_CONTRACT.md",
    "UPDATE_POLICY.md",
    "manifest.yaml",
    "recipes/build.sh",
    "recipes/acceptance.sh",
    "LICENSE",
)


class RepositoryContract(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
        self.assertEqual(missing, [])

    def test_readme_mentions_unpublished_baseline(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("unpublished", text)
        self.assertIn("application", text)
        self.assertIn("exposer", text)
        self.assertIn("build", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

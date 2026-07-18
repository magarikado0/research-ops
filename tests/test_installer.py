from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "install.py"


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="research-ops-test-")
        self.target = Path(self.temporary.name) / "research"
        self.target.mkdir()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_installer(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, str(INSTALLER), *arguments],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=environment,
            check=False,
        )

    def test_dry_run_does_not_write(self) -> None:
        result = self.run_installer(
            "--target", str(self.target),
            "--adapter", "codex",
            "--profile", "general",
            "--dry-run",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry-run", result.stdout)
        self.assertFalse((self.target / "OPERATIONS.md").exists())

    def test_installs_both_adapters_and_is_idempotent(self) -> None:
        arguments = (
            "--target", str(self.target),
            "--adapter", "both",
            "--profile", "general",
            "--yes",
        )
        first = self.run_installer(*arguments)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue((self.target / ".agents/skills/state-sync/SKILL.md").is_file())
        self.assertTrue((self.target / ".agents/skills/docs-sync/SKILL.md").is_file())
        self.assertTrue((self.target / ".claude/skills/panel/SKILL.md").is_file())
        self.assertTrue((self.target / ".claude/skills/docs-sync/SKILL.md").is_file())
        self.assertTrue((self.target / "RESEARCH_PROFILE.md").is_file())
        self.assertEqual((self.target / "AGENTS.md").read_text(encoding="utf-8").count(
            "<!-- research-ops:begin -->"), 1)

        decisions = self.target / "STATE/decisions.md"
        decisions.write_text(decisions.read_text(encoding="utf-8") + "\n- user decision\n",
                             encoding="utf-8")
        second = self.run_installer(*arguments)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("user decision", decisions.read_text(encoding="utf-8"))
        self.assertEqual((self.target / "AGENTS.md").read_text(encoding="utf-8").count(
            "<!-- research-ops:begin -->"), 1)

        manifest = json.loads((self.target / ".research-ops/installation.json").read_text(
            encoding="utf-8"))
        self.assertEqual(manifest["profile"], "general")
        self.assertEqual(set(manifest["adapters"]), {"codex", "claude-code"})
        validation = subprocess.run(
            [sys.executable, str(self.target / ".research-ops/validate.py"),
             "--target", str(self.target)],
            text=True,
            encoding="utf-8",
            capture_output=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        self.assertEqual(validation.returncode, 0, validation.stderr)

    def test_machine_learning_profile_adds_templates(self) -> None:
        result = self.run_installer(
            "--target", str(self.target),
            "--adapter", "codex",
            "--profile", "machine-learning",
            "--yes",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target /
                         ".research-ops/templates/profiles/machine-learning/STATE/data.md").is_file())
        config = (self.target / "research-ops.yml").read_text(encoding="utf-8")
        self.assertIn("profile: machine-learning", config)
        self.assertIn("activity_logs: []", config)
        self.assertIn("データ懐疑派", (self.target / "RESEARCH_PROFILE.md").read_text(
            encoding="utf-8"))

    def test_registers_multiple_colocated_document_roots(self) -> None:
        for name in ("individual", "population"):
            directory = self.target / name
            directory.mkdir()
            (directory / "RESULTS.md").write_text(f"# {name}\n", encoding="utf-8")
        result = self.run_installer(
            "--target", str(self.target),
            "--adapter", "both",
            "--profile", "machine-learning",
            "--document-root", "individual",
            "--document-root", "population",
            "--yes",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        config = (self.target / "research-ops.yml").read_text(encoding="utf-8")
        self.assertIn('path: "docs"', config)
        self.assertIn('path: "individual"', config)
        self.assertIn('scope: "individual"', config)
        self.assertIn('path: "population"', config)
        unrelated = self.target / "unrelated"
        unrelated.mkdir()
        (unrelated / "BROKEN.md").write_text("[outside](missing.md)\n", encoding="utf-8")
        validation = subprocess.run(
            [sys.executable, str(self.target / ".research-ops/validate.py"),
             "--target", str(self.target)],
            text=True,
            encoding="utf-8",
            capture_output=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        self.assertEqual(validation.returncode, 0, validation.stderr)
        (self.target / "individual/BROKEN.md").write_text(
            "[registered](missing.md)\n", encoding="utf-8"
        )
        registered_validation = subprocess.run(
            [sys.executable, str(self.target / ".research-ops/validate.py"),
             "--target", str(self.target)],
            text=True,
            encoding="utf-8",
            capture_output=True,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            check=False,
        )
        self.assertEqual(registered_validation.returncode, 1)
        self.assertIn("individual", registered_validation.stderr)

    def test_rejects_document_root_outside_repository(self) -> None:
        result = self.run_installer(
            "--target", str(self.target),
            "--adapter", "none",
            "--profile", "general",
            "--document-root", "..",
            "--yes",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("escapes the target repository", result.stderr)

    def test_existing_research_files_are_not_overwritten(self) -> None:
        (self.target / "STATE").mkdir()
        original = "# Existing decisions\n\n- keep me\n"
        (self.target / "STATE/decisions.md").write_text(original, encoding="utf-8")
        result = self.run_installer(
            "--target", str(self.target),
            "--adapter", "none",
            "--profile", "general",
            "--yes",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / "STATE/decisions.md").read_text(encoding="utf-8"),
                         original)
        self.assertIn("skip-protected", result.stdout)

    def test_noninteractive_mode_requires_options(self) -> None:
        result = self.run_installer("--target", str(self.target))
        self.assertEqual(result.returncode, 2)
        self.assertIn("--adapter is required", result.stderr)

    def test_migrates_legacy_log_keys_without_replacing_state(self) -> None:
        (self.target / "STATE").mkdir()
        (self.target / "STATE/README.md").write_text(
            "---\nlast_sync_at: \"2026-07-01T12:00:00+09:00\"\n"
            "last_sync_commit: \"abc123\"\n"
            "experiment_log_cursors: {}\n---\n\n# Existing project\n",
            encoding="utf-8",
        )
        (self.target / "research-ops.yml").write_text(
            "version: 1\nexperiment_logs: []\ncustom_setting: keep\n",
            encoding="utf-8",
        )
        result = self.run_installer(
            "--target", str(self.target),
            "--adapter", "none",
            "--profile", "qualitative-research",
            "--yes",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        state = (self.target / "STATE/README.md").read_text(encoding="utf-8")
        config = (self.target / "research-ops.yml").read_text(encoding="utf-8")
        self.assertIn("activity_log_cursors", state)
        self.assertIn("last_state_sync_at", state)
        self.assertIn("last_state_sync_commit", state)
        self.assertIn("last_docs_sync_at", state)
        self.assertIn("last_docs_sync_commit", state)
        self.assertNotIn("\nlast_sync_at:", state)
        self.assertIn('last_state_sync_at: "2026-07-01T12:00:00+09:00"', state)
        self.assertIn('last_state_sync_commit: "abc123"', state)
        self.assertIn("# Existing project", state)
        self.assertIn("activity_logs: []", config)
        self.assertIn("custom_setting: keep", config)
        self.assertIn("profile: qualitative-research", config)

    def test_backup_conflict_preserves_modified_managed_file(self) -> None:
        arguments = (
            "--target", str(self.target),
            "--adapter", "none",
            "--profile", "general",
            "--yes",
        )
        self.assertEqual(self.run_installer(*arguments).returncode, 0)
        operations = self.target / "OPERATIONS.md"
        operations.write_text("locally modified\n", encoding="utf-8")
        result = self.run_installer(*arguments, "--conflict", "backup")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(operations.read_text(encoding="utf-8"), "locally modified\n")
        backups = list((self.target / ".research-ops/backups").glob("*/OPERATIONS.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "locally modified\n")

    def test_profile_list_contains_all_supported_profiles(self) -> None:
        result = self.run_installer("--list-profiles")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in (
            "general", "machine-learning", "experimental-science",
            "qualitative-research", "software-systems",
        ):
            self.assertIn(name, result.stdout)

    def test_numbered_choice_accepts_default_and_index(self) -> None:
        sys.path.insert(0, str(ROOT))
        try:
            import install
            with redirect_stdout(io.StringIO()):
                with patch("builtins.input", return_value=""):
                    self.assertEqual(install.choose("prompt", [("a", "A"), ("b", "B")], "b"), "b")
                with patch("builtins.input", return_value="1"):
                    self.assertEqual(install.choose("prompt", [("a", "A"), ("b", "B")]), "a")
        finally:
            sys.path.remove(str(ROOT))


if __name__ == "__main__":
    unittest.main()

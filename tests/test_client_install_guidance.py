"""Client install guidance must preserve current, source-backed discovery paths."""

from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import install_codex_skill as installer  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
ANTIGRAVITY_WORKSPACE = ".agents/skills/seedance-20/"
ANTIGRAVITY_GLOBAL = "~/.gemini/config/skills/seedance-20/"
ANTIGRAVITY_WORKSPACE_ROOT = ".agents/skills/"
ANTIGRAVITY_GLOBAL_ROOT = "~/.gemini/config/skills/"
ANTIGRAVITY_CLI_ONLY = "~/.gemini/antigravity-cli/skills/"
HERMES_GLOBAL = "~/.hermes/skills/seedance-20/"
ANTIGRAVITY_DOCS = "https://antigravity.google/docs/cli/plugins"
ANTIGRAVITY_CODELAB = (
    "https://codelabs.developers.google.com/getting-started-with-antigravity-skills"
)
HERMES_DOCS = "https://hermes-agent.nousresearch.com/docs/user-guide/features/skills"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def table_row(text: str, label: str) -> str:
    rows = [line for line in text.splitlines() if line.startswith(f"| {label} |")]
    if len(rows) != 1:
        raise AssertionError(f"expected one {label!r} table row, found {len(rows)}")
    return rows[0]


def active_markdown() -> list[tuple[Path, str]]:
    documents = []
    for path in sorted(ROOT.rglob("*.md")):
        relative = path.relative_to(ROOT)
        if any(part.startswith(".") for part in relative.parts[:-1]):
            continue
        if relative.parts[:2] == ("references", "migrated"):
            continue
        documents.append((relative, read(path)))
    return documents


class ClientInstallGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.readme = read(ROOT / "README.md")
        cls.compatibility = read(ROOT / "references" / "agent-compatibility.md")
        cls.source_registry = read(ROOT / "references" / "source-registry.md")

    def test_antigravity_recommends_package_compatible_workspace_and_global_paths(self) -> None:
        for document in (self.readme, self.compatibility):
            row = table_row(document, "Google Antigravity")
            self.assertIn(ANTIGRAVITY_WORKSPACE_ROOT, row)
            self.assertIn(ANTIGRAVITY_GLOBAL_ROOT, row)
            self.assertNotIn(ANTIGRAVITY_CLI_ONLY, row)

        self.assertIn(ANTIGRAVITY_WORKSPACE, table_row(self.readme, "Google Antigravity"))
        self.assertIn(ANTIGRAVITY_GLOBAL, table_row(self.readme, "Google Antigravity"))

    def test_antigravity_cli_only_path_is_recorded_as_uncertain_not_recommended(self) -> None:
        occurrences = []
        for path, document in active_markdown():
            for line_number, line in enumerate(document.splitlines(), start=1):
                if ANTIGRAVITY_CLI_ONLY in line:
                    occurrences.append((path.as_posix(), line_number, line))

        self.assertEqual(len(occurrences), 1, occurrences)
        self.assertEqual(occurrences[0][0], "references/agent-compatibility.md")
        boundary = occurrences[0][2].split(ANTIGRAVITY_CLI_ONLY, 1)[1]
        self.assertIn("does not establish", boundary)
        self.assertIn("Do not treat", boundary)

    def test_hermes_project_path_requires_external_dirs_configuration(self) -> None:
        readme_row = table_row(self.readme, "Hermes Agent")
        compatibility_row = table_row(self.compatibility, "Hermes Agent (Nous Research)")
        self.assertIn(HERMES_GLOBAL, readme_row)
        for row in (readme_row, compatibility_row):
            self.assertIn("~/.hermes/skills/", row)
            self.assertIn("skills.external_dirs", row)
            self.assertNotIn("project `skills/`, `~/.hermes/skills/`", row)
            self.assertNotIn("project `skills/seedance-20/` or", row)

        for path, document in active_markdown():
            for line_number, line in enumerate(document.splitlines(), start=1):
                if "project" in line and "`skills/" in line and "~/.hermes/skills/" in line:
                    self.assertIn(
                        "skills.external_dirs",
                        line,
                        f"{path}:{line_number} presents a project path without its config gate",
                    )

        self.assertIn("~/.hermes/config.yaml", self.compatibility)
        self.assertIn(
            "skills:\n  external_dirs:\n    - /absolute/path/to/project/skills",
            self.compatibility,
        )

    def test_primary_sources_and_verification_date_are_recorded(self) -> None:
        for document in (self.compatibility, self.source_registry):
            self.assertIn("2026-08-01", document)
            self.assertIn(ANTIGRAVITY_DOCS, document)
            self.assertIn(ANTIGRAVITY_CODELAB, document)
            self.assertIn(HERMES_DOCS, document)
        self.assertIn("Client skill discovery paths", self.source_registry)

    def test_installed_payload_carries_the_corrected_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            argv = sys.argv
            sys.argv = ["install_codex_skill.py", "--dest", tmp]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(installer.main(), 0)
            finally:
                sys.argv = argv

            payload = Path(tmp) / installer.SKILL_NAME
            installed_readme = read(payload / "README.md")
            installed_compatibility = read(payload / "references" / "agent-compatibility.md")
            installed_registry = read(payload / "references" / "source-registry.md")
            self.assertIn(ANTIGRAVITY_GLOBAL, installed_readme)
            self.assertNotIn(ANTIGRAVITY_CLI_ONLY, installed_readme)
            self.assertIn("skills.external_dirs", table_row(installed_readme, "Hermes Agent"))
            self.assertIn("Do not treat", installed_compatibility)
            self.assertIn("Client skill discovery paths", installed_registry)


if __name__ == "__main__":
    unittest.main()

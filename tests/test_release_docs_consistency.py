"""Cross-document regressions for the active release surface.

The assertions derive the release version from SKILL.md and deliberately avoid
freezing the number of discovered tests.  Counts and status prose drift more
often than the underlying contracts; these tests protect the contracts.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIMARY_25_URLS = (
    "https://seed.bytedance.com/en/seedance2_5",
    "https://dreamina.capcut.com/seedance/seedance-2-5",
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def active_version() -> str:
    match = re.search(
        r'^  version:\s*["\']([^"\']+)["\']\s*$',
        read("SKILL.md"),
        flags=re.MULTILINE,
    )
    if not match:
        raise AssertionError("SKILL.md metadata.version is missing")
    return match.group(1)


class VersionSurfaceTests(unittest.TestCase):
    def test_active_docs_follow_skill_metadata_version(self) -> None:
        version = active_version()
        self.assertTrue((ROOT / f"docs/RELEASE_v{version}.md").is_file())

        for relative in (
            "README.md",
            "docs/README.zh.md",
            "docs/README.ja.md",
            "docs/README.ko.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(f"v{version}", read(relative))

        readiness = read("docs/v6-release-readiness.md")
        self.assertIn("metadata.version", readiness)
        self.assertNotIn("6.6.0", readiness)

    def test_release_verification_does_not_freeze_test_counts(self) -> None:
        release = read(f"docs/RELEASE_v{active_version()}.md")
        self.assertNotRegex(release, r"\b\d+\s+(?:unit\s+)?tests\b")
        self.assertIn("unit-test discovery", release)
        self.assertIn("source_registry_check --enforce-freshness", release)
        self.assertNotIn("source_registry_check --strict", release)


class ModelLineBoundaryTests(unittest.TestCase):
    STATUS_DOCS = (
        "README.md",
        "CHANGELOG.md",
        "docs/RELEASE_v6.7.0.md",
        "references/api-status.md",
        "references/api-workflow.md",
        "references/community-source-methodology.md",
        "references/field-observed-tips.md",
        "references/model-name-map.md",
        "references/platform-constraints.md",
        "references/platform-surface-matrix.md",
        "references/source-registry.md",
    )

    def test_25_status_stays_inside_primary_source_boundary(self) -> None:
        for relative in self.STATUS_DOCS:
            text = read(relative)
            with self.subTest(relative=relative):
                self.assertNotIn("2026-07-31", text)
                self.assertNotIn("2026-06-23", text)
                self.assertNotIn("coming soon", text.lower())
                for line in text.splitlines():
                    if "Seedance 2.5" in line:
                        self.assertNotRegex(line, r"\b(?:launched|shipped)\b")

        for relative in (
            "README.md",
            "docs/RELEASE_v6.7.0.md",
            "references/api-status.md",
            "references/source-registry.md",
        ):
            text = read(relative).lower()
            with self.subTest(relative=relative):
                for primary_url in PRIMARY_25_URLS:
                    self.assertIn(primary_url, text)
                self.assertRegex(
                    text,
                    r"exact.{0,100}launch.{0,100}unconfirmed",
                )
                self.assertIn("live on dreamina", text)

    def test_release_describes_what_landed(self) -> None:
        release = read("docs/RELEASE_v6.7.0.md")
        changelog = read("CHANGELOG.md")
        for text in (release, changelog):
            self.assertNotIn("2.0-4K rows", text)
        for absent_promise in (
            "≈30-second native single-shot",
            "up to 50 references",
            "reported BytePlus API access from mid-July",
        ):
            self.assertNotIn(absent_promise, release)
        self.assertIn("source boundary", release)


class FreshnessWorkflowDocumentationTests(unittest.TestCase):
    def test_review_acknowledges_the_scheduled_workflow(self) -> None:
        workflow = ROOT / ".github/workflows/source-freshness-review.yml"
        self.assertTrue(workflow.is_file())

        review = read("docs/V7_INTEGRATION_REVIEW.md")
        self.assertIn(".github/workflows/source-freshness-review.yml", review)
        for stale_claim in (
            "A weekly scheduled review job is not on `main`",
            "there is no automated alert between releases",
            "is **not yet on `main`**",
            "Scheduled monitoring between releases is a separate pull request still in flight",
        ):
            self.assertNotIn(stale_claim, review)


class QuickstartSecurityBoundaryTests(unittest.TestCase):
    PAYLOAD_MARKERS = {
        "docs/QUICKSTART.md": "installed payload",
        "docs/QUICKSTART.es.md": "contenido instalado",
        "docs/QUICKSTART.ja.md": "インストール済みペイロード",
        "docs/QUICKSTART.ko.md": "설치된 페이로드",
        "docs/QUICKSTART.ru.md": "установленный пакет",
        "docs/QUICKSTART.zh.md": "安装后的内容",
    }
    UNSUPPORTED_DETERMINISM = {
        "docs/QUICKSTART.md": "deterministic",
        "docs/QUICKSTART.es.md": "deterministas",
        "docs/QUICKSTART.ja.md": "決定論的",
        "docs/QUICKSTART.ko.md": "결정론적",
        "docs/QUICKSTART.ru.md": "детерминированы",
        "docs/QUICKSTART.zh.md": "确定性的",
    }

    def test_every_quickstart_scopes_offline_claim_to_install(self) -> None:
        for relative, payload_marker in self.PAYLOAD_MARKERS.items():
            text = read(relative)
            with self.subTest(relative=relative):
                self.assertIn(payload_marker, text)
                self.assertIn("scripts/eval_run.py", text)
                self.assertNotIn(self.UNSUPPORTED_DETERMINISM[relative], text)


if __name__ == "__main__":
    unittest.main()

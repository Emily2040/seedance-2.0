from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
ORDINARY_WORKFLOW = REPOSITORY / ".github" / "workflows" / "validate-skills.yml"
PRIVILEGED_WORKFLOW = (
    REPOSITORY / ".github" / "workflows" / "privileged-frame-publication.yml"
)
PRIVILEGED_CHECKOUT = "11d5960a326750d5838078e36cf38b85af677262"


class PrivilegedWorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ordinary = ORDINARY_WORKFLOW.read_text(encoding="utf-8")
        cls.privileged = PRIVILEGED_WORKFLOW.read_text(encoding="utf-8")
        cls.security = (REPOSITORY / "SECURITY.md").read_text(encoding="utf-8")

    def job_block(self, workflow: str, name: str) -> str:
        match = re.search(
            rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-z0-9-]+:\n|\Z)",
            workflow,
        )
        self.assertIsNotNone(match, f"workflow job {name!r} is missing")
        assert match is not None
        return match.group(0)

    def trigger_lines(self, workflow: str) -> tuple[str, ...]:
        match = re.search(
            r"(?ms)^on:\n(.*?)(?=^[a-z][a-z0-9_-]*:\n|\Z)",
            workflow,
        )
        self.assertIsNotNone(match, "workflow top-level trigger block is missing")
        assert match is not None
        return tuple(
            line.strip()
            for line in match.group(1).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )

    def test_checked_in_privileged_trigger_allowlist_has_no_pr_event(self) -> None:
        self.assertEqual(
            self.trigger_lines(self.privileged),
            ("push:", "workflow_dispatch:"),
        )
        for forbidden in (
            "pull_request:",
            "pull_request_target:",
            "workflow_run:",
            "issue_comment:",
        ):
            self.assertNotIn(forbidden, self.trigger_lines(self.privileged))

    def test_docs_do_not_turn_the_checked_in_allowlist_into_a_global_guarantee(self) -> None:
        combined = self.privileged + self.security
        self.assertIn("require approval for all outside collaborators", combined)
        self.assertIn(".github/workflows/**", combined)
        self.assertIn("first-time", combined)
        self.assertNotIn("never executes fork-controlled PR code", combined)

    def test_privileged_checkout_does_not_persist_repository_credentials(self) -> None:
        block = self.job_block(
            self.privileged, "linux-privileged-frame-publication"
        )
        self.assertRegex(
            block,
            rf"(?m)^      - uses: actions/checkout@{PRIVILEGED_CHECKOUT}.*\n"
            r"        with:\n"
            r"          persist-credentials: false$",
        )

    def test_unprivileged_validation_still_runs_for_fork_pull_requests(self) -> None:
        self.assertIn("pull_request:", self.trigger_lines(self.ordinary))
        self.assertNotIn("--privileged", self.ordinary)
        self.assertNotIn("linux-privileged-frame-publication", self.ordinary)

    def test_privileged_job_uses_a_digest_pinned_base_and_explicit_option(self) -> None:
        block = self.job_block(
            self.privileged, "linux-privileged-frame-publication"
        )
        self.assertRegex(block, r"(?m)^      image: ubuntu@sha256:[0-9a-f]{64}$")
        self.assertIn("      options: --privileged\n", block)

    def test_privileged_workflow_is_read_only_and_capability_gated(self) -> None:
        self.assertRegex(
            self.privileged,
            r"(?m)^permissions:\n  contents: read$",
        )
        self.assertEqual(self.privileged.count('"tests.test_'), 13)
        self.assertIn("id: privileged_proof", self.privileged)
        self.assertIn('stream.write("available=false\\n")', self.privileged)
        self.assertIn('stream.write("available=true\\n")', self.privileged)
        self.assertIn(
            "if: steps.privileged_proof.outputs.available == 'true'",
            self.privileged,
        )
        self.assertIn("assert not extractor._posix_descriptor_xattrs_supported()", self.privileged)
        self.assertNotIn(
            "assert extractor._posix_descriptor_xattr_api_supported()",
            self.privileged,
        )
        self.assertNotIn(
            "assert extractor._posix_atomic_exchange_supported()",
            self.privileged,
        )
        self.assertIn(
            '"descriptor-bound extended-attribute APIs",', self.privileged
        )
        self.assertIn('"renameat2(RENAME_EXCHANGE)",', self.privileged)
        self.assertIn(
            "privileged publication prerequisites unavailable", self.privileged
        )
        self.assertIn("Privileged success-path tests were explicitly skipped", self.privileged)
        self.assertIn("if result.skipped:", self.privileged)
        self.assertIn(
            'raise SystemExit("privileged metadata regressions must not skip")',
            self.privileged,
        )

    def test_privileged_diff_check_runs_inside_the_checkout(self) -> None:
        self.assertIn(
            "      - name: Prove checked-out repository root\n"
            "        shell: bash\n"
            "        run: |\n"
            "          set -euo pipefail\n"
            '          git config --global --add safe.directory "$GITHUB_WORKSPACE"\n'
            '          checkout_root="$(git -C "$GITHUB_WORKSPACE" '
            'rev-parse --show-toplevel)"\n',
            self.privileged,
        )
        self.assertIn(
            "      - name: Check diff whitespace\n"
            "        working-directory: ${{ github.workspace }}\n"
            "        shell: bash\n"
            "        run: |\n"
            "          set -euo pipefail\n"
            '          test -n "${SEEDANCE_CHECKOUT_ROOT:-}"\n'
            '          test "$(git -C "$SEEDANCE_CHECKOUT_ROOT" '
            'rev-parse --is-inside-work-tree)" = true\n'
            '          git -C "$SEEDANCE_CHECKOUT_ROOT" diff --check\n',
            self.privileged,
        )
        self.assertNotIn('git diff --check "$GITHUB_WORKSPACE"', self.privileged)


if __name__ == "__main__":
    unittest.main()

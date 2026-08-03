from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
WORKFLOW = REPOSITORY / ".github" / "workflows" / "validate-skills.yml"


class PrivilegedWorkflowSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def job_block(self, name: str) -> str:
        match = re.search(
            rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-z0-9-]+:\n|\Z)",
            self.workflow,
        )
        self.assertIsNotNone(match, f"workflow job {name!r} is missing")
        assert match is not None
        return match.group(0)

    def test_privileged_job_rejects_fork_controlled_pull_request_heads(self) -> None:
        block = self.job_block("linux-privileged-frame-publication")
        gate = re.search(
            r"(?m)^    if: >-\n((?:^      .+\n)+)",
            block,
        )
        self.assertIsNotNone(gate, "privileged job must have a job-level event gate")
        assert gate is not None
        expression = " ".join(line.strip() for line in gate.group(1).splitlines())
        self.assertEqual(
            expression,
            "github.event_name == 'push' || "
            "github.event_name == 'workflow_dispatch' || "
            "(github.event_name == 'pull_request' && "
            "github.event.pull_request.head.repo.full_name == github.repository)",
        )

    def test_privileged_checkout_does_not_persist_repository_credentials(self) -> None:
        block = self.job_block("linux-privileged-frame-publication")
        self.assertRegex(
            block,
            r"(?m)^      - uses: actions/checkout@[0-9a-f]{40}.*\n"
            r"        with:\n"
            r"          persist-credentials: false$",
        )

    def test_unprivileged_validation_still_runs_for_fork_pull_requests(self) -> None:
        block = self.job_block("validate")
        header, separator, _steps = block.partition("    steps:\n")
        self.assertTrue(separator, "ordinary validation job has no steps")
        self.assertNotIn("\n    if:", header)
        self.assertNotIn("--privileged", block)

    def test_privileged_job_uses_a_digest_pinned_base_and_explicit_option(self) -> None:
        block = self.job_block("linux-privileged-frame-publication")
        self.assertRegex(block, r"(?m)^      image: ubuntu@sha256:[0-9a-f]{64}$")
        self.assertIn("      options: --privileged\n", block)


if __name__ == "__main__":
    unittest.main()

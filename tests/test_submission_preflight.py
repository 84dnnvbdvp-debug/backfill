import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.submission_preflight import run_preflight


ROOT = Path(__file__).resolve().parents[1]


def _copy_repo() -> tuple[tempfile.TemporaryDirectory, Path]:
    temporary = tempfile.TemporaryDirectory()
    target = Path(temporary.name) / "repo"
    shutil.copytree(
        ROOT,
        target,
        ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", "*.pyc"),
    )
    return temporary, target


def _rewrite_manifest_digest(root: Path, relative: str) -> None:
    target = root / relative
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest_path = root / "SHA256SUMS.txt"
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    updated: list[str] = []
    replaced = False
    for line in lines:
        if line.endswith(f"  {relative}"):
            updated.append(f"{digest}  {relative}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(f"{digest}  {relative}")
    manifest_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


class SubmissionPreflightTests(unittest.TestCase):
    def test_current_repository_bundle_is_ready_but_submission_is_not_claimed(self):
        report = run_preflight(ROOT)
        self.assertTrue(report.repository_bundle_ready)
        self.assertFalse(report.external_actions_complete)
        self.assertFalse(report.submission_receipt_recorded)
        self.assertFalse(report.preflight_complete)
        self.assertEqual(
            [item.state for item in report.external_actions],
            ["PENDING", "PENDING", "PENDING"],
        )

    def test_missing_required_architecture_is_a_repository_failure(self):
        temporary, root = _copy_repo()
        self.addCleanup(temporary.cleanup)
        (root / "docs" / "backfill-architecture.svg").unlink()

        report = run_preflight(root)

        self.assertFalse(report.repository_bundle_ready)
        self.assertTrue(
            any(
                error == "required_artifact_missing:docs/backfill-architecture.svg"
                for error in report.repository_errors
            )
        )

    def test_changed_artifact_without_checksum_update_is_rejected(self):
        temporary, root = _copy_repo()
        self.addCleanup(temporary.cleanup)
        copy_path = root / "docs" / "final-devpost-copy.md"
        copy_path.write_text(
            copy_path.read_text(encoding="utf-8") + "\nchanged\n",
            encoding="utf-8",
        )

        report = run_preflight(root)

        self.assertFalse(report.repository_bundle_ready)
        self.assertTrue(
            any(
                error.startswith(
                    "checksum_mismatch:docs/final-devpost-copy.md:"
                )
                for error in report.repository_errors
            )
        )

    def test_completed_external_action_requires_evidence(self):
        temporary, root = _copy_repo()
        self.addCleanup(temporary.cleanup)
        status_path = root / "docs" / "submission-status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status["external_actions"]["public_demo_video"]["state"] = "COMPLETE"
        status_path.write_text(
            json.dumps(status, indent=2) + "\n",
            encoding="utf-8",
        )
        _rewrite_manifest_digest(root, "docs/submission-status.json")

        report = run_preflight(root)

        self.assertFalse(report.repository_bundle_ready)
        self.assertIn(
            "submission_status_complete_without_evidence:public_demo_video",
            report.repository_errors,
        )

    def test_completed_actions_still_do_not_equal_devpost_receipt(self):
        temporary, root = _copy_repo()
        self.addCleanup(temporary.cleanup)
        status_path = root / "docs" / "submission-status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        for key, item in status["external_actions"].items():
            item["state"] = "COMPLETE"
            item["evidence"] = f"human-confirmed:{key}"
        status_path.write_text(
            json.dumps(status, indent=2) + "\n",
            encoding="utf-8",
        )
        _rewrite_manifest_digest(root, "docs/submission-status.json")

        report = run_preflight(root)

        self.assertTrue(report.repository_bundle_ready)
        self.assertTrue(report.external_actions_complete)
        self.assertFalse(report.submission_receipt_recorded)
        self.assertFalse(report.preflight_complete)

    def test_structural_devpost_receipt_completes_preflight_without_claiming_authentication(self):
        temporary, root = _copy_repo()
        self.addCleanup(temporary.cleanup)
        status_path = root / "docs" / "submission-status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        for key, item in status["external_actions"].items():
            item["state"] = "COMPLETE"
            item["evidence"] = f"human-confirmed:{key}"
        status_path.write_text(
            json.dumps(status, indent=2) + "\n",
            encoding="utf-8",
        )
        _rewrite_manifest_digest(root, "docs/submission-status.json")

        receipt_path = Path(temporary.name) / "devpost-receipt.json"
        receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "provider": "devpost",
                    "submission_id": "example-id",
                    "captured_at": "2026-09-01T12:00:00Z",
                    "evidence": "saved-confirmation-page",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        report = run_preflight(root, receipt_path=receipt_path)

        self.assertTrue(report.preflight_complete)
        self.assertTrue(report.submission_receipt_recorded)
        self.assertTrue(
            any(
                "does not query Devpost" in warning
                for warning in report.receipt_warnings
            )
        )

    def test_malformed_receipt_is_rejected(self):
        temporary, root = _copy_repo()
        self.addCleanup(temporary.cleanup)
        receipt_path = Path(temporary.name) / "bad-receipt.json"
        receipt_path.write_text(
            json.dumps(
                {
                    "schema_version": "0.1",
                    "provider": "devpost",
                    "submission_id": "",
                    "captured_at": "2026-09-01T12:00:00Z",
                    "evidence": "saved-confirmation-page",
                }
            ),
            encoding="utf-8",
        )

        report = run_preflight(root, receipt_path=receipt_path)

        self.assertTrue(report.repository_bundle_ready)
        self.assertFalse(report.submission_receipt_recorded)
        self.assertIn(
            "submission_receipt_missing:submission_id",
            report.receipt_errors,
        )


if __name__ == "__main__":
    unittest.main()

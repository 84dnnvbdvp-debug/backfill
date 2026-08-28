"""Deterministic preflight for the public Backfill hackathon bundle.

The tool can verify repository-internal evidence and report human/external
actions. It does not query Devpost and never treats a green repository as a
submission receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from collections.abc import Mapping
from typing import Any


RULE_SNAPSHOT_URL = "https://agentsforhumans.devpost.com/rules"
RULE_SNAPSHOT_VERIFIED_ON = "2026-08-28"

REQUIRED_ARTIFACTS = (
    "LICENSE",
    "README.md",
    "backfill/application.py",
    "docs/backfill-architecture.svg",
    "docs/demo-recording-checklist.md",
    "docs/demo-voiceover-script.md",
    "docs/final-devpost-copy.md",
    "docs/hackathon-submission-checklist.md",
    "docs/judge-testing.md",
    "requirements-ci.txt",
    "scripts/strands_smoke_harness.py",
)

REQUIRED_CHECKSUM_COVERAGE = REQUIRED_ARTIFACTS + (
    ".github/workflows/strands-smoke.yml",
    "docs/submission-status.json",
    "scripts/submission_preflight.py",
    "tests/test_submission_preflight.py",
)

EXTERNAL_ACTION_KEYS = (
    "public_demo_video",
    "aws_builder_id_entered",
    "track_selected",
)
ALLOWED_ACTION_STATES = frozenset({"PENDING", "COMPLETE"})


class PreflightDataError(ValueError):
    """Raised when status or receipt evidence is malformed."""


@dataclass(frozen=True)
class ExternalAction:
    key: str
    state: str
    evidence: str | None


@dataclass(frozen=True)
class PreflightReport:
    rule_snapshot_url: str
    rule_snapshot_verified_on: str
    repository_bundle_ready: bool
    external_actions_complete: bool
    submission_receipt_recorded: bool
    preflight_complete: bool
    repository_errors: tuple[str, ...]
    external_actions: tuple[ExternalAction, ...]
    receipt_errors: tuple[str, ...]
    receipt_warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["repository_errors"] = list(self.repository_errors)
        data["external_actions"] = [asdict(item) for item in self.external_actions]
        data["receipt_errors"] = list(self.receipt_errors)
        data["receipt_warnings"] = list(self.receipt_warnings)
        return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, *, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PreflightDataError(f"{label}_missing:{path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightDataError(f"{label}_unreadable:{path}:{exc}") from exc
    if not isinstance(value, Mapping):
        raise PreflightDataError(f"{label}_must_be_object:{path}")
    return value


def _parse_manifest(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    entries: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {}, ["checksum_manifest_missing:SHA256SUMS.txt"]
    except OSError as exc:
        return {}, [f"checksum_manifest_unreadable:{exc}"]

    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            errors.append(f"checksum_manifest_malformed_line:{line_number}")
            continue
        digest, relative = parts
        relative = relative.lstrip("*")
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            errors.append(f"checksum_manifest_bad_digest:{line_number}")
            continue
        if relative in entries:
            errors.append(f"checksum_manifest_duplicate:{relative}")
            continue
        entries[relative] = digest
    return entries, errors


def _repository_errors(root: Path) -> list[str]:
    errors: list[str] = []

    for relative in REQUIRED_ARTIFACTS:
        path = root / relative
        if not path.is_file():
            errors.append(f"required_artifact_missing:{relative}")
        elif path.stat().st_size == 0:
            errors.append(f"required_artifact_empty:{relative}")

    license_path = root / "LICENSE"
    if license_path.is_file():
        try:
            license_text = license_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"license_unreadable:{exc}")
        else:
            if "MIT License" not in license_text:
                errors.append("license_not_detectably_mit")

    readme_path = root / "README.md"
    if readme_path.is_file():
        try:
            readme = readme_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"readme_unreadable:{exc}")
        else:
            for reference in (
                "docs/backfill-architecture.svg",
                "docs/judge-testing.md",
            ):
                if reference not in readme:
                    errors.append(f"readme_missing_reference:{reference}")

    manifest, manifest_errors = _parse_manifest(root / "SHA256SUMS.txt")
    errors.extend(manifest_errors)

    for relative in REQUIRED_CHECKSUM_COVERAGE:
        if relative not in manifest:
            errors.append(f"checksum_coverage_missing:{relative}")

    for relative, expected in sorted(manifest.items()):
        target = root / relative
        if not target.is_file():
            errors.append(f"checksum_target_missing:{relative}")
            continue
        observed = _sha256(target)
        if observed != expected:
            errors.append(
                f"checksum_mismatch:{relative}:expected={expected}:observed={observed}"
            )

    return errors


def _load_external_actions(root: Path) -> tuple[ExternalAction, ...]:
    status_path = root / "docs" / "submission-status.json"
    status = _load_json(status_path, label="submission_status")

    if status.get("schema_version") != "0.1":
        raise PreflightDataError("submission_status_unsupported_schema")

    snapshot = status.get("rule_snapshot")
    if not isinstance(snapshot, Mapping):
        raise PreflightDataError("submission_status_rule_snapshot_missing")
    if snapshot.get("url") != RULE_SNAPSHOT_URL:
        raise PreflightDataError("submission_status_rule_url_mismatch")
    if snapshot.get("verified_on") != RULE_SNAPSHOT_VERIFIED_ON:
        raise PreflightDataError("submission_status_rule_date_mismatch")

    actions = status.get("external_actions")
    if not isinstance(actions, Mapping):
        raise PreflightDataError("submission_status_external_actions_missing")

    missing = set(EXTERNAL_ACTION_KEYS) - set(actions)
    extra = set(actions) - set(EXTERNAL_ACTION_KEYS)
    if missing:
        raise PreflightDataError(
            "submission_status_missing_actions:" + ",".join(sorted(missing))
        )
    if extra:
        raise PreflightDataError(
            "submission_status_unknown_actions:" + ",".join(sorted(extra))
        )

    parsed: list[ExternalAction] = []
    for key in EXTERNAL_ACTION_KEYS:
        raw = actions[key]
        if not isinstance(raw, Mapping):
            raise PreflightDataError(f"submission_status_action_not_object:{key}")
        state = raw.get("state")
        if state not in ALLOWED_ACTION_STATES:
            raise PreflightDataError(f"submission_status_bad_state:{key}:{state}")
        evidence = raw.get("evidence")
        if evidence is not None and (
            not isinstance(evidence, str) or not evidence.strip()
        ):
            raise PreflightDataError(f"submission_status_bad_evidence:{key}")
        if state == "COMPLETE" and evidence is None:
            raise PreflightDataError(
                f"submission_status_complete_without_evidence:{key}"
            )
        parsed.append(ExternalAction(key=key, state=state, evidence=evidence))
    return tuple(parsed)


def _receipt_record(path: Path | None) -> tuple[bool, tuple[str, ...]]:
    if path is None:
        return False, (
            "No Devpost receipt record was supplied. Repository readiness is "
            "not proof of submission.",
        )

    receipt = _load_json(path, label="submission_receipt")
    if receipt.get("schema_version") != "0.1":
        raise PreflightDataError("submission_receipt_unsupported_schema")

    required = ("provider", "submission_id", "captured_at", "evidence")
    for key in required:
        value = receipt.get(key)
        if not isinstance(value, str) or not value.strip():
            raise PreflightDataError(f"submission_receipt_missing:{key}")

    if receipt["provider"].strip().lower() != "devpost":
        raise PreflightDataError("submission_receipt_provider_not_devpost")

    return True, (
        "Receipt structure is present, but this local tool does not query "
        "Devpost or independently authenticate the supplied evidence.",
    )


def run_preflight(
    root: Path,
    *,
    receipt_path: Path | None = None,
) -> PreflightReport:
    root = root.resolve()
    repository_errors = _repository_errors(root)

    try:
        external_actions = _load_external_actions(root)
    except PreflightDataError as exc:
        repository_errors.append(str(exc))
        external_actions = tuple(
            ExternalAction(key=key, state="PENDING", evidence=None)
            for key in EXTERNAL_ACTION_KEYS
        )

    receipt_errors: tuple[str, ...] = ()
    try:
        receipt_recorded, receipt_warnings = _receipt_record(receipt_path)
    except PreflightDataError as exc:
        receipt_errors = (str(exc),)
        receipt_recorded = False
        receipt_warnings = (
            "The supplied receipt record was rejected; submission remains "
            "unverified by this preflight.",
        )

    repository_bundle_ready = not repository_errors
    external_actions_complete = all(
        action.state == "COMPLETE" for action in external_actions
    )
    preflight_complete = (
        repository_bundle_ready
        and external_actions_complete
        and receipt_recorded
    )

    return PreflightReport(
        rule_snapshot_url=RULE_SNAPSHOT_URL,
        rule_snapshot_verified_on=RULE_SNAPSHOT_VERIFIED_ON,
        repository_bundle_ready=repository_bundle_ready,
        external_actions_complete=external_actions_complete,
        submission_receipt_recorded=receipt_recorded,
        preflight_complete=preflight_complete,
        repository_errors=tuple(repository_errors),
        external_actions=external_actions,
        receipt_errors=receipt_errors,
        receipt_warnings=receipt_warnings,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the checkout containing this script)",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        help="optional Devpost receipt JSON; kept separate from repository readiness",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--require-submitted",
        action="store_true",
        help="return 2 unless repository, external actions, and receipt are present",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_preflight(args.root, receipt_path=args.receipt)

    if args.as_json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        print(
            "BACKFILL_SUBMISSION_PREFLIGHT "
            f"repository_bundle_ready={str(report.repository_bundle_ready).lower()} "
            f"external_actions_complete={str(report.external_actions_complete).lower()} "
            f"submission_receipt_recorded={str(report.submission_receipt_recorded).lower()} "
            f"preflight_complete={str(report.preflight_complete).lower()}"
        )
        for error in report.repository_errors:
            print(f"REPOSITORY_ERROR {error}")
        for error in report.receipt_errors:
            print(f"RECEIPT_ERROR {error}")
        for action in report.external_actions:
            evidence = action.evidence if action.evidence is not None else "-"
            print(
                f"EXTERNAL_ACTION {action.key} "
                f"state={action.state} evidence={evidence}"
            )
        for warning in report.receipt_warnings:
            print(f"RECEIPT_NOTE {warning}")

    if not report.repository_bundle_ready:
        return 1
    if report.receipt_errors:
        return 3
    if args.require_submitted and not report.preflight_complete:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

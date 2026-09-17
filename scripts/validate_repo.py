#!/usr/bin/env python3
"""Validate an ORCA application-image repository using only public files.

This tool is agent-neutral. It does not need Atlas-ORCA, cloud credentials,
or a live LXD lab. Live qualification is a separate maintainer step.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - documented dependency
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc


SCHEMA_ID = "orca.image-manifest/v1"
ALLOWED_PUBLICATION_STATES = frozenset({"unpublished", "qualification-pending"})
FORBIDDEN_PUBLICATION_STATES = frozenset(
    {"published", "verified-live", "verified", "live", "released"}
)
NON_PUBLIC_PORTS = frozenset(
    {
        22,
        25,
        110,
        143,
        389,
        465,
        587,
        636,
        993,
        995,
        1433,
        1521,
        2375,
        2376,
        2379,
        27017,
        3306,
        3389,
        5432,
        5984,
        6379,
        8086,
        9200,
        9300,
        11211,
        15672,
        27018,
    }
)
REQUIRED_FILES = (
    "README.md",
    "REPOSITORY_CONTRACT.md",
    "UPDATE_POLICY.md",
    "manifest.yaml",
    "recipes/build.sh",
    "recipes/acceptance.sh",
    "assets/logo.png",
    "tests/test_manifest.py",
)
README_HINTS = (
    "application",
    "exposer",
    "build",
)
ALLOWED_LOGO_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
ARTIFACT_SUFFIXES = {
    ".squashfs",
    ".qcow2",
    ".vmdk",
    ".img",
    ".iso",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.xz",
    ".rootfs",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*\S+"),
    re.compile(r"(?i)(api[_-]?token|secret_access_key|private[_-]?key)\s*[:=]\s*\S+"),
)
PRIVATE_MARKERS = (
    "vpc-" + "core0",
    "caracal-" + "bee",
    "103.28." + "148.",
    "10.62." + "42.",
)
PINNED_ACTION = re.compile(r"uses:\s*\S+@([0-9a-f]{40})\b")
FLOATING_ACTION = re.compile(r"uses:\s*([^\s#]+@(v?\d[\w.\-]*))\b")
SKIP_DIR_NAMES = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}


@dataclass
class ValidationResult:
    status: str
    errors: list[str]
    summary: str


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _is_relative_safe(value: str) -> tuple[bool, str | None]:
    if not isinstance(value, str) or not value.strip():
        return False, "path is empty"
    if value.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", value):
        return False, "absolute path is not allowed"
    if ".." in Path(value).parts:
        return False, "path traversal is not allowed"
    return True, None


def _walk_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
                continue
            if path.suffix.lower() in ARTIFACT_SUFFIXES:
                continue
            files.append(path)
    return files


def _load_manifest(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append("missing required file: manifest.yaml")
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append("manifest.yaml is not valid YAML")
        return None
    if not isinstance(data, dict):
        errors.append("manifest.yaml must be a mapping")
        return None
    return data


def _require_type(value: Any, expected: type, field: str, errors: list[str]) -> None:
    if isinstance(value, bool) and expected is int:
        errors.append(f"{field} must be an integer, not a boolean")
        return
    if not isinstance(value, expected):
        errors.append(f"{field} must be {expected.__name__}")


def _validate_manifest(manifest: dict[str, Any], root: Path, errors: list[str]) -> None:
    if manifest.get("schema") != SCHEMA_ID:
        errors.append(f"schema must be {SCHEMA_ID}")

    slug = manifest.get("slug")
    _require_type(slug, str, "slug", errors)
    if isinstance(slug, str) and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        errors.append("slug must be lowercase kebab-case")

    application = manifest.get("application")
    if not isinstance(application, dict):
        errors.append("application must be a mapping")
    else:
        for field in ("display_name", "category", "description", "version"):
            _require_type(application.get(field), str, f"application.{field}", errors)

    base_os = manifest.get("base_os")
    if not isinstance(base_os, dict):
        errors.append("base_os must be a mapping")
    else:
        _require_type(base_os.get("distribution"), str, "base_os.distribution", errors)
        _require_type(base_os.get("release"), str, "base_os.release", errors)

    _require_type(manifest.get("architecture"), str, "architecture", errors)
    instance_type = manifest.get("instance_type")
    if instance_type not in {"container", "virtual-machine"}:
        errors.append("instance_type must be container or virtual-machine")

    resources = manifest.get("minimum_resources")
    if not isinstance(resources, dict):
        errors.append("minimum_resources must be a mapping")
    else:
        for field, minimum in (("cpu", 1), ("memory_mib", 256), ("storage_gib", 4)):
            value = resources.get(field)
            _require_type(value, int, f"minimum_resources.{field}", errors)
            if isinstance(value, int) and not isinstance(value, bool) and value < minimum:
                errors.append(f"minimum_resources.{field} must be >= {minimum}")

    network = manifest.get("network")
    if not isinstance(network, dict) or network.get("default_policy") != "private":
        errors.append("network.default_policy must be private")
    if isinstance(network, dict):
        for forbidden in ("default_bridge", "lab_project", "ssh_alias"):
            if forbidden in network:
                errors.append(f"network.{forbidden} is maintainer-only and must not appear in public source")

    exposer = manifest.get("exposer")
    if not isinstance(exposer, dict):
        errors.append("exposer must be a mapping")
    else:
        endpoints = exposer.get("endpoints")
        if not isinstance(endpoints, list) or not endpoints:
            errors.append("exposer.endpoints must be a non-empty list")
        else:
            for index, endpoint in enumerate(endpoints):
                prefix = f"exposer.endpoints[{index}]"
                if not isinstance(endpoint, dict):
                    errors.append(f"{prefix} must be a mapping")
                    continue
                protocol = endpoint.get("protocol")
                if protocol not in {"http", "https", "tcp", "udp"}:
                    errors.append(f"{prefix}.protocol is invalid")
                port = endpoint.get("target_port")
                _require_type(port, int, f"{prefix}.target_port", errors)
                if isinstance(port, int) and not isinstance(port, bool):
                    if port < 1 or port > 65535:
                        errors.append(f"{prefix}.target_port out of range")
                    public = bool(endpoint.get("default_public"))
                    if public and port in NON_PUBLIC_PORTS:
                        errors.append(f"{prefix} port {port} must not be public")
                    if public and protocol not in {"http", "https"}:
                        errors.append(f"{prefix} public endpoints must be http or https")

    persistent_paths = manifest.get("persistent_paths")
    if persistent_paths is None:
        errors.append("persistent_paths is required")
    elif not isinstance(persistent_paths, list) or not persistent_paths:
        errors.append("persistent_paths must be a non-empty list")
    else:
        for index, item in enumerate(persistent_paths):
            if isinstance(item, str):
                path_value = item
            elif isinstance(item, dict):
                path_value = item.get("path")
            else:
                errors.append(f"persistent_paths[{index}] is invalid")
                continue
            if not isinstance(path_value, str) or not path_value.startswith("/"):
                errors.append(f"persistent_paths[{index}].path must be an absolute POSIX path inside the guest")
            if isinstance(path_value, str) and ".." in Path(path_value).parts:
                errors.append(f"persistent_paths[{index}].path must not contain ..")

    upstream = manifest.get("upstream")
    if not isinstance(upstream, dict):
        errors.append("upstream must be a mapping")
    else:
        for field in ("source_url", "version_url", "version_strategy"):
            _require_type(upstream.get(field), str, f"upstream.{field}", errors)
        source_url = upstream.get("source_url")
        if isinstance(source_url, str) and not source_url.startswith("https://"):
            errors.append("upstream.source_url must start with https://")

    branding = manifest.get("branding")
    if not isinstance(branding, dict):
        errors.append("branding must be a mapping")
    else:
        local_path = branding.get("local_path")
        _require_type(local_path, str, "branding.local_path", errors)
        if isinstance(local_path, str):
            ok, reason = _is_relative_safe(local_path)
            if not ok:
                errors.append(f"branding.local_path {reason}")
            elif Path(local_path).suffix.lower() not in ALLOWED_LOGO_SUFFIXES:
                errors.append("branding.local_path must be png, jpg, jpeg, or webp")
            elif not (root / local_path).is_file():
                errors.append("branding.local_path does not exist")
        logo_source = branding.get("logo_source_url")
        if isinstance(logo_source, str) and logo_source and not logo_source.startswith("https://"):
            errors.append("branding.logo_source_url must start with https://")

    build = manifest.get("build")
    if not isinstance(build, dict):
        errors.append("build must be a mapping")
    else:
        ready = build.get("ready")
        if not isinstance(ready, bool):
            errors.append("build.ready must be a boolean")
        recipe = build.get("recipe", "recipes/build.sh")
        acceptance = build.get("acceptance_test", "recipes/acceptance.sh")
        for field, value in (("recipe", recipe), ("acceptance_test", acceptance)):
            if not isinstance(value, str):
                errors.append(f"build.{field} must be a string")
                continue
            ok, reason = _is_relative_safe(value)
            if not ok:
                errors.append(f"build.{field} {reason}")
            elif not (root / value).is_file():
                errors.append(f"missing {value}")
        if ready is True:
            for name in ("recipes/build.sh", "recipes/acceptance.sh"):
                if not (root / name).is_file():
                    errors.append("build.ready cannot be true without recipes/build.sh and recipes/acceptance.sh")

    publication = manifest.get("publication")
    if not isinstance(publication, dict):
        errors.append("publication must be a mapping")
    else:
        state = publication.get("state")
        if state in FORBIDDEN_PUBLICATION_STATES or (
            isinstance(state, str) and state not in ALLOWED_PUBLICATION_STATES
        ):
            errors.append(
                "publication.state in source repositories must be unpublished or qualification-pending; published is maintainer-only"
            )


def _validate_required_files(root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")


def _validate_readme(root: Path, errors: list[str]) -> None:
    path = root / "README.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    missing = [hint for hint in README_HINTS if hint not in text]
    if missing:
        errors.append("README.md is missing required operational sections: " + ", ".join(missing))


def _validate_shell_and_python(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix == ".sh" or path.name.endswith(".sh"):
            completed = subprocess.run(
                ["bash", "-n", str(path)],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                errors.append(f"shell syntax failed: {_rel(path, root)}")
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                errors.append(f"python syntax failed: {_rel(path, root)}")


def _validate_artifacts_and_secrets(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() in ARTIFACT_SUFFIXES or path.name.endswith(".squashfs"):
            errors.append(f"runtime artifact must not be tracked: {_rel(path, root)}")
    for path in _walk_text_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible credential material in {_rel(path, root)}")
                break
        lowered = text.lower()
        for marker in PRIVATE_MARKERS:
            if marker.lower() in lowered:
                errors.append(f"private infrastructure marker in {_rel(path, root)}")
                break


def _validate_workflows(root: Path, errors: list[str]) -> None:
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return
    for path in workflow_dir.glob("*.yml"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in FLOATING_ACTION.finditer(text):
            action = match.group(0)
            sha_match = PINNED_ACTION.search(action)
            if sha_match:
                continue
            # allow comments on same line after sha; if no 40-char sha, fail
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            line = text[line_start:line_end if line_end != -1 else None]
            if not PINNED_ACTION.search(line):
                errors.append(f"GitHub Action must be pinned to a commit SHA in {_rel(path, root)}")


def validate_repository(path: Path) -> ValidationResult:
    root = Path(path).resolve()
    errors: list[str] = []
    if not root.is_dir():
        return ValidationResult("FAIL", [f"not a directory: {root}"], "repository contract: FAIL")

    _validate_required_files(root, errors)
    manifest = _load_manifest(root / "manifest.yaml", errors)
    if manifest is not None:
        _validate_manifest(manifest, root, errors)
    _validate_readme(root, errors)
    _validate_shell_and_python(root, errors)
    _validate_artifacts_and_secrets(root, errors)
    _validate_workflows(root, errors)

    status = "PASS" if not errors else "FAIL"
    summary = f"repository contract: {status}"
    return ValidationResult(status, errors, summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an ORCA image repository")
    parser.add_argument("path", nargs="?", default=".", help="repository root")
    args = parser.parse_args(argv)
    result = validate_repository(Path(args.path))
    print(result.summary)
    for error in result.errors:
        print(f"- {error}")
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

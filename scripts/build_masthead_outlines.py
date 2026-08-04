#!/usr/bin/env python3
"""Generate assets/masthead-outlines.json: display type as vector outlines.

The masthead's display type is glyph geometry, not live text. A font stack
resolves to a different face on every platform - the retired stack gave Didot
only on macOS and a default system serif on Linux - so the editorial serif the
design system specifies was what a minority of readers actually saw. Outlines
depend on no installed font and render identically for everyone.

This is a maintainer tool, not part of the installed skill runtime. Its two
third-party packages are isolated in a dedicated, marker-protected virtual
environment and a hash-pinned build lock. Selected wheel bytes, pip's install
report, and every installed distribution file are sealed together. Verification
and rendering run in fresh ``python -I -S -B`` children, so same-version modules
injected by inherited ``PYTHONPATH``/``sitecustomize`` or already imported by
the parent cannot bypass wheel-hash verification.

    python -I -S -B scripts/build_masthead_outlines.py             # install + rewrite
    python -I -S -B scripts/build_masthead_outlines.py --install-build-deps
    python -I -S -B scripts/build_masthead_outlines.py --install-build-deps --wheelhouse PATH
    python -I -S -B scripts/build_masthead_outlines.py --check     # verify it is current

Run it only when the wordmark or tagline copy changes, then run
``python -I -S -B scripts/build_hero.py`` so the SVGs pick up the new geometry.

The fonts are vendored under assets/fonts/ with their OFL text, so a clean
checkout reproduces the committed geometry offline. Outlines are glyph
geometry rather than font software; the OFL permits both these outlines and
the bundled originals, and attribution travels in the generated file.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import sysconfig
import tempfile
import venv
import zipfile
from email.parser import Parser
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements-masthead.lock"
FONT_DIR = ROOT / "assets" / "fonts"
ROMAN = FONT_DIR / "BodoniModa[opsz,wght].ttf"
ITALIC = FONT_DIR / "BodoniModa-Italic[opsz,wght].ttf"
TARGET = ROOT / "assets" / "masthead-outlines.json"
SCRIPT = Path(__file__).resolve()

BUILD_ENV_MARKER = ".seedance-masthead-build-env.json"
BUILD_ENV_PURPOSE = "seedance-masthead-outline-builder-v1"
BUILD_ENV_MARKER_VERSION = 2
BUILD_INSTALL_REPORT = ".seedance-masthead-pip-install-report.json"
BUILD_WHEEL_ARCHIVE_DIR = ".seedance-locked-wheels"
ISOLATED_RESULT_PREFIX = "SEEDANCE_ISOLATED_RESULT="
BUILD_TRUST_VERSION = 1
BUILD_TRUST_PURPOSE = "seedance-masthead-external-trust-v1"
CHECKOUT_KEY = hashlib.sha256(str(ROOT.resolve()).encode("utf-8")).hexdigest()[:12]
DEFAULT_BUILD_ENV = Path(tempfile.gettempdir()) / (
    "seedance-masthead-build-" + CHECKOUT_KEY
)
BUILD_TRUST_ROOT = Path(tempfile.gettempdir()) / (
    "seedance-masthead-trust-" + CHECKOUT_KEY
)

# Optical size tracks the rendered size, clamped to the axis range. That is
# what the axis is for: a didone drawn for 96px has hairlines that vanish at
# 26px, and one drawn for 26px looks clumsy blown up to 128px.
OPSZ_MIN, OPSZ_MAX = 6, 96

SPECS = {
    "wordmark":  {"font": "roman",  "text": "Seedance 2.0",                  "size": 128},
    "skill_os":  {"font": "roman",  "text": "Skill OS",                      "size": 66},
    "tagline_1": {"font": "italic", "text": "Direct the model.",             "size": 26},
    "tagline_2": {"font": "italic", "text": "Don’t micro-manage the frame.", "size": 26},
}

PINNED_BUILDER_VERSIONS = {
    "fonttools": "4.63.0",
    "uharfbuzz": "0.55.0",
    "harfbuzz": "14.2.1",
}

BUILD_LOCK_PROVENANCE_PATH = "requirements-masthead.lock"
BUILD_INSTALL_POLICY = (
    "generator writes only after pip --force-reinstall --require-hashes; "
    "preinstalled distributions are not reused"
)
LOCKED_PYTHON_BUILDERS = ("fonttools", "uharfbuzz")
LOCKED_IMPORT_ROOTS = {
    "fonttools": "fontTools",
    "uharfbuzz": "uharfbuzz",
}

# ``python -I`` ignores Python-specific environment variables, but native
# loaders run before Python gets that far. These variables can inject or
# redirect arbitrary native code into the supposedly isolated child.
DYNAMIC_LOADER_ENVIRONMENT = {"LIBPATH", "SHLIB_PATH"}


def pinned_install_argv(
    python: str | Path,
    wheelhouse: str | Path,
    build_env: str | Path,
) -> list[str]:
    """Return the forced, hash-verified install command with an absolute lock path."""
    argv = [
        str(python),
        "-I",
        "-m",
        "pip",
        "--disable-pip-version-check",
        "install",
        "--force-reinstall",
        "--no-compile",
        "--no-deps",
        "--no-index",
        "--find-links",
        str(Path(wheelhouse).resolve()),
        "--require-hashes",
        "--report",
        str(Path(build_env).resolve() / BUILD_INSTALL_REPORT),
    ]
    argv.extend(("--requirement", str(LOCK)))
    return argv


def ensurepip_argv(python: str | Path) -> list[str]:
    """Bootstrap pip only after the new venv launcher/config pass external trust."""
    # Before Python 3.14, ``-S`` prevents pyvenv.cfg from updating sys.prefix,
    # which would make ensurepip target the base installation instead of this
    # dedicated environment. ``-I`` still ignores inherited Python paths and
    # user site-packages; the freshly cleared no-pip venv has no site payload.
    return [str(python), "-I", "-B", "-m", "ensurepip", "--upgrade"]


def pinned_download_argv(python: str | Path, wheelhouse: str | Path) -> list[str]:
    """Download only artifacts named and hashed by the committed build lock."""
    return [
        str(python),
        "-I",
        "-m",
        "pip",
        "--disable-pip-version-check",
        "download",
        "--only-binary=:all:",
        "--no-deps",
        "--require-hashes",
        "--dest",
        str(Path(wheelhouse).resolve()),
        "--requirement",
        str(LOCK),
    ]


def python_clean_environment(environment: dict[str, str] | None = None) -> dict[str, str]:
    """Drop import/configuration hooks before starting a trusted Python child."""
    inherited = os.environ if environment is None else environment
    return {
        key: value
        for key, value in inherited.items()
        if not key.upper().startswith(("PIP_", "PYTHON"))
        and not key.upper().startswith(("LD_", "DYLD_"))
        and key.upper() not in {"VIRTUAL_ENV", "__PYVENV_LAUNCHER__"}
        and key.upper() not in DYNAMIC_LOADER_ENVIRONMENT
    }


def pip_clean_environment(environment: dict[str, str] | None = None) -> dict[str, str]:
    """Disable inherited Python/pip hooks and every pip configuration file."""
    clean = python_clean_environment(environment)
    clean["PIP_CONFIG_FILE"] = os.devnull
    return clean


def shell_command(argv: list[str]) -> str:
    """Render an argv for the host shell without losing paths that contain spaces."""
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def recovery_command(build_env: str | Path | None = None) -> str:
    """Return a cwd-independent command that installs the pinned build toolchain."""
    argv = [sys.executable, "-I", "-S", "-B", str(SCRIPT), "--install-build-deps"]
    if build_env is not None:
        argv.extend(("--build-env", str(Path(build_env).resolve())))
    return shell_command(argv)


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def build_env_marker_payload(
    *,
    wheelhouse: str | Path | None = None,
    integrity: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "marker_version": BUILD_ENV_MARKER_VERSION,
        "purpose": BUILD_ENV_PURPOSE,
        "repository": str(ROOT.resolve()),
        "state": "sealed" if integrity is not None else "initialized",
    }
    if wheelhouse is not None:
        payload["wheelhouse"] = str(Path(wheelhouse).resolve())
    if integrity is not None:
        payload["integrity"] = integrity
    return payload


def marker_belongs_to_checkout(payload: object) -> bool:
    """Recognize only this marker format and this exact checkout."""
    legacy = {
        "purpose": BUILD_ENV_PURPOSE,
        "repository": str(ROOT.resolve()),
    }
    if payload == legacy:
        # v1 environments may be cleared and rebuilt, but cannot pass the new
        # sealed check because they have no state/integrity record.
        return True
    return isinstance(payload, dict) and {
        "marker_version": payload.get("marker_version"),
        "purpose": payload.get("purpose"),
        "repository": payload.get("repository"),
    } == {
        "marker_version": BUILD_ENV_MARKER_VERSION,
        "purpose": BUILD_ENV_PURPOSE,
        "repository": str(ROOT.resolve()),
    }


def resolve_build_env(build_env: str | Path | None = None) -> Path:
    """Resolve and safety-check the dedicated environment before any clearing."""
    candidate = Path(build_env or DEFAULT_BUILD_ENV).expanduser().resolve()
    repository_root = ROOT.resolve()
    trust_root = Path(BUILD_TRUST_ROOT).resolve()
    home_root = Path.home().resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    python_roots = {
        Path(sys.prefix).resolve(),
        Path(sys.base_prefix).resolve(),
        Path(sys.exec_prefix).resolve(),
        Path(sys.base_exec_prefix).resolve(),
        Path(sys.executable).resolve().parent,
    }
    protected_roots = {
        repository_root,
        home_root,
        temp_root,
        Path(candidate.anchor).resolve(),
        trust_root,
    } | python_roots
    protected_descendant_roots = {repository_root, trust_root} | python_roots
    # On Windows the system temp directory is itself below the user's home.
    safe_temp_descendant = _is_within(candidate, temp_root) and candidate != temp_root
    if (
        candidate in protected_roots
        or any(_is_within(candidate, protected) for protected in protected_descendant_roots)
        or (_is_within(candidate, home_root) and not safe_temp_descendant)
        or any(_is_within(protected, candidate) for protected in protected_roots)
    ):
        raise SystemExit(f"refusing unsafe masthead build environment path: {candidate}")
    if candidate.exists() and not candidate.is_dir():
        raise SystemExit(f"masthead build environment is not a directory: {candidate}")

    if candidate.exists() and any(candidate.iterdir()):
        marker = candidate / BUILD_ENV_MARKER
        try:
            payload = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SystemExit(
                f"refusing to clear unmarked masthead build environment: {candidate}"
            ) from exc
        if not marker_belongs_to_checkout(payload):
            raise SystemExit(
                f"refusing to clear masthead build environment with a foreign marker: {candidate}"
            )
    return candidate


def build_env_python(build_env: str | Path) -> Path:
    root = Path(build_env).resolve()
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def trusted_base_python() -> Path:
    """Return the interpreter trusted to create and inspect the dedicated venv."""
    python = Path(getattr(sys, "_base_executable", sys.executable)).resolve()
    if not python.is_file():
        raise SystemExit(f"trusted base Python is missing: {python}")
    return python


def write_build_env_marker(
    build_env: str | Path,
    *,
    wheelhouse: str | Path | None = None,
    integrity: dict[str, object] | None = None,
) -> None:
    marker = Path(build_env).resolve() / BUILD_ENV_MARKER
    marker.write_text(
        json.dumps(
            build_env_marker_payload(wheelhouse=wheelhouse, integrity=integrity),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def prepare_build_environment(
    build_env: str | Path | None = None,
    wheelhouse: str | Path | None = None,
) -> Path:
    """Create a clean dedicated venv, clearing only one carrying our exact marker."""
    destination = resolve_build_env(build_env)
    clear_build_env_trust(destination)
    subprocess.run(
        [
            str(trusted_base_python()),
            "-I",
            "-S",
            "-B",
            "-m",
            "venv",
            "--clear",
            "--without-pip",
            str(destination),
        ],
        check=True,
        cwd=ROOT,
        env=python_clean_environment(),
    )
    write_build_env_marker(destination, wheelhouse=wheelhouse)
    write_build_env_trust(destination, state="initialized")
    require_build_env_trust(destination, state="initialized")
    return destination


def require_prepared_build_environment(build_env: str | Path | None = None) -> Path:
    """Require an intact environment created for this checkout."""
    destination = resolve_build_env(build_env)
    python = build_env_python(destination)
    config = destination / "pyvenv.cfg"
    if not python.is_file() or not config.is_file():
        raise SystemExit(
            "masthead build environment is not prepared; run:\n"
            f"  {recovery_command(destination)}\n"
            f"Resolved build lock: {LOCK}"
        )
    return destination


def isolated_builder_argv(action: str, build_env: str | Path) -> list[str]:
    destination = Path(build_env).resolve()
    # Never execute code through the build environment's launcher. Even an
    # authentic copied Windows launcher can be influenced by adjacent native
    # libraries. The trusted parent interpreter verifies and then exposes only
    # the sealed site-packages directory itself.
    trusted_python = trusted_base_python()
    return [
        str(trusted_python),
        "-I",
        "-S",
        "-B",
        str(SCRIPT),
        "--_isolated-action",
        action,
        "--build-env",
        str(destination),
    ]


def sealed_marker_integrity_sha256(build_env: str | Path) -> str:
    """Return the integrity digest held outside the isolated child report."""
    marker = read_build_env_marker(build_env)
    integrity = marker.get("integrity")
    if marker.get("state") != "sealed" or not isinstance(integrity, dict):
        raise SystemExit("masthead build environment marker is not sealed")
    digest = integrity.get("integrity_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise SystemExit("masthead build environment marker has no valid integrity digest")
    return digest


def verify_isolated_builder(build_env: str | Path) -> dict[str, object]:
    """Verify versions and import origins in a fresh isolated trusted interpreter."""
    destination = require_prepared_build_environment(build_env)
    require_build_env_trust(destination, state="sealed")
    completed = subprocess.run(
        isolated_builder_argv("verify", destination),
        check=True,
        cwd=ROOT,
        env=python_clean_environment(),
        capture_output=True,
        text=True,
    )
    try:
        report = json.loads(completed.stdout)
    except (TypeError, ValueError) as exc:
        raise SystemExit("isolated masthead builder returned an invalid verification report") from exc
    expected_versions = dict(sorted(PINNED_BUILDER_VERSIONS.items()))
    expected_integrity = sealed_marker_integrity_sha256(destination)
    if (
        not isinstance(report, dict)
        or report.get("action") != "verify"
        or report.get("status") != "ok"
        or report.get("versions") != expected_versions
        or report.get("integrity_sha256") != expected_integrity
    ):
        raise SystemExit("isolated masthead builder returned a mismatched verification report")
    return report


def seal_isolated_builder(build_env: str | Path) -> dict[str, object]:
    """Seal a fresh pip install from a no-site child before any builder import."""
    destination = require_prepared_build_environment(build_env)
    initialized_trust = require_build_env_trust(destination, state="initialized")
    completed = subprocess.run(
        isolated_builder_argv("seal", destination),
        check=False,
        cwd=ROOT,
        env=python_clean_environment(),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise SystemExit(f"isolated masthead seal failed:\n{detail}")
    try:
        report = json.loads(completed.stdout)
    except (TypeError, ValueError) as exc:
        raise SystemExit("isolated masthead builder returned an invalid seal report") from exc
    if not isinstance(report, dict) or report.get("action") != "seal" or report.get("status") != "ok":
        raise SystemExit("isolated masthead builder returned a mismatched seal report")
    if report.get("integrity_sha256") != sealed_marker_integrity_sha256(destination):
        raise SystemExit("isolated masthead builder returned an unbound seal report")
    sealed_payload = build_env_trust_payload(destination, state="sealed")
    initialized_files = initialized_trust.get("files")
    sealed_files = sealed_payload.get("files")
    if not isinstance(initialized_files, dict) or not isinstance(sealed_files, dict):
        raise SystemExit("masthead external trust record has no file fingerprints")
    for name in ("base_python", "runner", "runner_source", "config", "script", "lock"):
        if initialized_files.get(name) != sealed_files.get(name):
            raise SystemExit(f"masthead trusted {name} changed while sealing")
    write_build_env_trust(destination, state="sealed")
    return report


def run_isolated_builder(action: str, build_env: str | Path) -> int:
    """Run a check/write child and require its seal-bound completion record."""
    destination = require_prepared_build_environment(build_env)
    require_build_env_trust(destination, state="sealed")
    completed = subprocess.run(
        isolated_builder_argv(action, destination),
        check=False,
        cwd=ROOT,
        env=python_clean_environment(),
        capture_output=True,
        text=True,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    if completed.returncode != 0:
        return completed.returncode

    result_lines = [
        line[len(ISOLATED_RESULT_PREFIX):]
        for line in completed.stdout.splitlines()
        if line.startswith(ISOLATED_RESULT_PREFIX)
    ]
    if len(result_lines) != 1:
        print("isolated masthead builder returned no unique completion record", file=sys.stderr)
        return 1
    try:
        result = json.loads(result_lines[0])
    except (TypeError, ValueError):
        print("isolated masthead builder returned an invalid completion record", file=sys.stderr)
        return 1
    expected_integrity = sealed_marker_integrity_sha256(destination)
    if (
        not isinstance(result, dict)
        or result.get("action") != action
        or result.get("status") != "ok"
        or result.get("integrity_sha256") != expected_integrity
    ):
        print("isolated masthead builder returned a mismatched completion record", file=sys.stderr)
        return 1
    return 0


def install_pinned_builder_dependencies(
    wheelhouse: str | Path | None = None,
    build_env: str | Path | None = None,
) -> Path:
    """Rebuild a dedicated venv and force-install the locked wheels into it."""
    require_lock_matches_pinned_versions()
    require_offline_wheel_lock(LOCK)

    def install_from(source: Path) -> Path:
        if not source.is_dir():
            raise SystemExit(f"masthead wheelhouse is not a directory: {source}")
        destination = prepare_build_environment(build_env, source)
        bootstrap_build_environment_pip(destination)
        run_initialized_build_env_command(
            destination,
            pinned_install_argv(build_env_python(destination), source, destination),
            environment=pip_clean_environment(),
        )
        seal_isolated_builder(destination)
        verify_isolated_builder(destination)
        return destination

    if wheelhouse is not None:
        return install_from(Path(wheelhouse).resolve())

    # Online release writes still split network acquisition from installation:
    # pip first downloads hash-locked wheels, then the build env installs with
    # --no-index from that temporary wheelhouse and archives the selected bytes.
    with tempfile.TemporaryDirectory(prefix="seedance-masthead-wheelhouse-") as temp:
        source = Path(temp).resolve()
        subprocess.run(
            pinned_download_argv(sys.executable, source),
            check=True,
            cwd=ROOT,
            env=pip_clean_environment(),
        )
        return install_from(source)


def build_lock_sha256() -> str:
    """Bind generated provenance to the exact requirements lock bytes."""
    return hashlib.sha256(LOCK.read_bytes()).hexdigest()


def repo_relative_posix(path: Path) -> str:
    """Return a repository-relative path with stable JSON/documentation separators."""
    return path.relative_to(ROOT).as_posix()


def pinned_builder_versions() -> dict[str, str]:
    """Return the toolchain versions committed in requirements-masthead.lock."""
    return dict(PINNED_BUILDER_VERSIONS)


def canonical_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def wheel_lock_packages(
    lock_path: str | Path = LOCK,
    lock_bytes: bytes | None = None,
) -> dict[str, dict[str, object]]:
    """Parse the deliberately tiny package/hash-only requirements grammar."""
    path = Path(lock_path)
    try:
        text = (path.read_bytes() if lock_bytes is None else lock_bytes).decode("utf-8")
    except (OSError, UnicodeError) as exc:
        raise SystemExit(f"cannot read wheel lock {path}: {exc}") from exc

    package_pattern = re.compile(
        r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)=="
        r"(?P<version>[A-Za-z0-9][A-Za-z0-9.!+_-]*)$"
    )
    digest_pattern = re.compile(r"--hash=sha256:(?P<digest>[0-9a-f]{64})$")
    packages: dict[str, dict[str, object]] = {}
    current: str | None = None
    wheel_only_count = 0

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if line.endswith("\\"):
            line = line[:-1].rstrip()
        if not line or line.startswith("#"):
            continue
        if line == "--only-binary=:all:":
            wheel_only_count += 1
            if wheel_only_count > 1 or packages:
                raise SystemExit(
                    f"wheel lock {path} must declare --only-binary=:all: exactly once before pins"
                )
            current = None
            continue

        package_match = package_pattern.fullmatch(line)
        if package_match:
            name = canonical_package_name(package_match.group("name"))
            if name in packages:
                raise SystemExit(
                    f"wheel lock {path} line {line_number} duplicates package {name}"
                )
            packages[name] = {
                "version": package_match.group("version"),
                "hashes": [],
            }
            current = name
            continue

        digest_match = digest_pattern.fullmatch(line)
        if digest_match and current is not None:
            hashes = packages[current]["hashes"]
            assert isinstance(hashes, list)
            hashes.append(digest_match.group("digest"))
            continue

        raise SystemExit(
            f"wheel lock {path} line {line_number} is not safe for offline wheelhouse install"
        )

    if wheel_only_count != 1:
        raise SystemExit(
            f"wheel lock {path} must declare --only-binary=:all: exactly once before pins"
        )
    if not packages:
        raise SystemExit(f"wheel lock {path} contains no pinned packages")
    for name, package in packages.items():
        hashes = package["hashes"]
        if not isinstance(hashes, list) or not hashes:
            raise SystemExit(f"wheel lock {path} package {name} has no sha256 hashes")
        package["hashes"] = sorted(set(hashes))
    return packages


def locked_python_builder_versions(lock_bytes: bytes | None = None) -> dict[str, str]:
    """Extract the two top-level Python pins from the exact lock bytes."""
    packages = wheel_lock_packages(LOCK, lock_bytes)
    return {name: str(package["version"]) for name, package in packages.items()}


def require_lock_matches_pinned_versions(lock_bytes: bytes | None = None) -> dict[str, str]:
    """Refuse a lock whose package pins disagree with the shaper contract."""
    locked = locked_python_builder_versions(lock_bytes)
    expected = {name: PINNED_BUILDER_VERSIONS[name] for name in LOCKED_PYTHON_BUILDERS}
    if locked != expected:
        raise SystemExit(
            f"masthead build lock version mismatch (expected {expected!r}; found {locked!r})"
        )
    return locked


def require_offline_wheel_lock(
    lock_path: str | Path = LOCK,
    lock_bytes: bytes | None = None,
) -> None:
    """Reject requirement syntax that could bypass a local --no-index wheelhouse."""
    wheel_lock_packages(lock_path, lock_bytes)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_env_trust_path(build_env: str | Path) -> Path:
    """Derive an external trust-record path without consulting the venv marker."""
    destination = Path(build_env).resolve()
    normalized = os.path.normcase(str(destination))
    key = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    trust_root = Path(BUILD_TRUST_ROOT).absolute()
    if trust_root.is_symlink():
        raise SystemExit(f"masthead trust root must not be a symlink: {trust_root}")
    if trust_root.exists() and not trust_root.is_dir():
        raise SystemExit(f"masthead trust root must be a directory: {trust_root}")
    return trust_root / f"{key}.json"


def trusted_file_fingerprint(path: str | Path) -> dict[str, object]:
    """Hash one trusted input, including its logical and resolved identity."""
    candidate = Path(path).absolute()
    if not candidate.is_file():
        raise SystemExit(f"masthead trusted file is missing: {candidate}")
    link_target = os.readlink(candidate) if candidate.is_symlink() else None
    return {
        "path": str(candidate),
        "resolved_path": str(candidate.resolve()),
        "symlink_target": link_target,
        "size": candidate.stat().st_size,
        "sha256": sha256_file(candidate),
    }


def windows_venv_runner_source(
    base_python: str | Path,
    venv_dir: str | Path,
    version_info: tuple[int, int],
    *,
    gil_disabled: bool,
    python_build: bool,
) -> Path:
    """Return the exact console launcher selected by Windows ``venv``."""
    base = Path(base_python)
    if not (3, 11) <= version_info <= (3, 13):
        raise SystemExit(
            "trusted stdlib venv runner supports CPython 3.11 through 3.13; "
            f"found {version_info[0]}.{version_info[1]}"
        )
    debug_suffix = "_d" if os.path.normcase(base.stem).endswith("_d") else ""
    if version_info >= (3, 13):
        threaded_suffix = "t" if gil_disabled else ""
        runner_name = f"venvlauncher{threaded_suffix}{debug_suffix}.exe"
        scripts = base.parent if python_build else Path(venv_dir) / "scripts" / "nt"
    else:
        if gil_disabled:
            raise SystemExit(
                "trusted stdlib venv runner has an impossible pre-3.13 free-threaded layout"
            )
        runner_name = f"python{debug_suffix}.exe"
        scripts = base.parent if python_build else Path(venv_dir) / "scripts" / "nt"

    # Installed builds copy their version-specific packaged launcher from the
    # stdlib venv directory. Source builds keep the corresponding launcher
    # beside the base executable. Never accept another existing variant.
    source = Path(scripts) / runner_name
    if not source.is_file():
        raise SystemExit(f"trusted stdlib venv runner is missing: {source}")
    return source


def trusted_venv_runner_source() -> Path:
    """Return the stdlib launcher/base executable that `venv` must install."""
    if os.name == "nt":
        source = windows_venv_runner_source(
            trusted_base_python(),
            Path(venv.__file__).resolve().parent,
            tuple(sys.version_info[:2]),
            gil_disabled=bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
            python_build=sysconfig.is_python_build(),
        )
    else:
        source = trusted_base_python()
    if not source.is_file():
        raise SystemExit(f"trusted stdlib venv runner is missing: {source}")
    return source


def require_trusted_venv_config(build_env: str | Path) -> None:
    """Verify pyvenv.cfg describes the trusted parent interpreter, not a fake."""
    config = Path(build_env).resolve() / "pyvenv.cfg"
    try:
        settings = {
            key.strip().lower(): value.strip()
            for line in config.read_text(encoding="utf-8").splitlines()
            if "=" in line
            for key, value in (line.split("=", 1),)
        }
    except (OSError, UnicodeError) as exc:
        raise SystemExit(f"masthead build environment config is invalid: {config}") from exc
    base_executable = trusted_base_python()
    expected_version = ".".join(str(part) for part in sys.version_info[:3])
    try:
        observed_home = Path(settings.get("home", "")).resolve()
    except OSError as exc:
        raise SystemExit(f"masthead build environment config has invalid home: {config}") from exc
    if (
        settings.get("include-system-site-packages", "").lower() != "false"
        or observed_home != base_executable.parent
        or settings.get("version") != expected_version
    ):
        raise SystemExit("masthead build environment config does not match trusted base Python")


def build_env_trust_payload(
    build_env: str | Path,
    *,
    state: str,
) -> dict[str, object]:
    """Fingerprint the runner and inputs from the parent, outside child control."""
    if state not in {"initialized", "sealed"}:
        raise SystemExit(f"invalid masthead trust state: {state}")
    destination = Path(build_env).resolve()
    marker = read_build_env_marker(destination)
    if marker.get("state") != state:
        raise SystemExit(
            f"masthead marker state {marker.get('state')!r} does not match trust state {state!r}"
        )
    integrity_sha256: str | None = None
    if state == "sealed":
        integrity_sha256 = sealed_marker_integrity_sha256(destination)
    require_trusted_venv_config(destination)
    runner = trusted_file_fingerprint(build_env_python(destination))
    runner_source = trusted_file_fingerprint(trusted_venv_runner_source())
    if (
        runner.get("sha256") != runner_source.get("sha256")
        or runner.get("size") != runner_source.get("size")
    ):
        raise SystemExit("masthead build environment runner is not the trusted stdlib venv launcher")
    return {
        "trust_version": BUILD_TRUST_VERSION,
        "purpose": BUILD_TRUST_PURPOSE,
        "repository": str(ROOT.resolve()),
        "build_env": str(destination),
        "state": state,
        "integrity_sha256": integrity_sha256,
        "files": {
            "base_python": trusted_file_fingerprint(trusted_base_python()),
            "runner": runner,
            "runner_source": runner_source,
            "config": trusted_file_fingerprint(destination / "pyvenv.cfg"),
            "script": trusted_file_fingerprint(SCRIPT),
            "lock": trusted_file_fingerprint(LOCK),
            "marker": trusted_file_fingerprint(destination / BUILD_ENV_MARKER),
        },
    }


def clear_build_env_trust(build_env: str | Path) -> None:
    """Invalidate only the exact external trust record before rebuilding."""
    trust_path = build_env_trust_path(build_env)
    if trust_path.is_symlink() or trust_path.is_file():
        trust_path.unlink()
    elif trust_path.exists():
        raise SystemExit(f"masthead trust record is not a file: {trust_path}")


def write_build_env_trust(build_env: str | Path, *, state: str) -> Path:
    """Atomically publish the parent-computed initialized or sealed trust root."""
    trust_path = build_env_trust_path(build_env)
    trust_root = trust_path.parent
    trust_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = build_env_trust_payload(build_env, state=state)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=trust_root,
            prefix=trust_path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, trust_path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return trust_path


def require_build_env_trust(
    build_env: str | Path,
    *,
    state: str,
) -> dict[str, object]:
    """Require the external parent fingerprint before launching any venv code."""
    trust_path = build_env_trust_path(build_env)
    if trust_path.is_symlink() or not trust_path.is_file():
        raise SystemExit(
            "masthead build environment has no external trust record; run:\n"
            f"  {recovery_command(build_env)}\n"
            f"Expected trust record: {trust_path}"
        )
    try:
        recorded = json.loads(trust_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"masthead external trust record is invalid: {trust_path}") from exc
    expected = build_env_trust_payload(build_env, state=state)
    if recorded != expected:
        raise SystemExit(
            "masthead build environment runner/config/script/marker trust mismatch; run:\n"
            f"  {recovery_command(build_env)}"
        )
    assert isinstance(recorded, dict)
    return recorded


def run_initialized_build_env_command(
    build_env: str | Path,
    argv: list[str],
    *,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run the venv launcher only after its initialized trust record verifies."""
    destination = Path(build_env).resolve()
    expected_runner = os.path.normcase(os.path.abspath(build_env_python(destination)))
    observed_runner = os.path.normcase(os.path.abspath(argv[0])) if argv else ""
    if observed_runner != expected_runner:
        raise SystemExit(
            f"refusing untrusted masthead build-environment command: {argv!r}"
        )
    require_build_env_trust(destination, state="initialized")
    return subprocess.run(
        argv,
        check=True,
        cwd=ROOT,
        env=environment,
    )


def bootstrap_build_environment_pip(build_env: str | Path) -> None:
    """Install bundled pip through the externally verified venv launcher."""
    destination = Path(build_env).resolve()
    run_initialized_build_env_command(
        destination,
        ensurepip_argv(build_env_python(destination)),
        environment=python_clean_environment(),
    )


def build_env_site_packages(build_env: str | Path) -> Path:
    destination = Path(build_env).resolve()
    if os.name == "nt":
        site_packages = destination / "Lib" / "site-packages"
    else:
        site_packages = (
            destination
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )
    return site_packages.resolve()


def read_build_env_marker(build_env: str | Path) -> dict[str, object]:
    marker = Path(build_env).resolve() / BUILD_ENV_MARKER
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"masthead build environment marker is missing or invalid: {marker}") from exc
    if not marker_belongs_to_checkout(payload):
        raise SystemExit(f"masthead build environment marker does not match this checkout: {marker}")
    assert isinstance(payload, dict)
    return payload


def require_isolated_python_startup(
    build_env: str | Path,
    *,
    sealed: bool,
) -> tuple[Path, dict[str, object]]:
    """Prove the child started with no site hooks before reading any packages."""
    destination = Path(build_env).resolve()
    if not sys.flags.isolated or not sys.flags.no_site or not sys.flags.dont_write_bytecode:
        raise SystemExit("masthead builder requires python -I -S -B isolated startup")

    expected_executable = os.path.normcase(os.path.abspath(trusted_base_python()))
    observed_executable = os.path.normcase(os.path.abspath(sys.executable))
    if observed_executable != expected_executable:
        raise SystemExit(
            "masthead builder interpreter mismatch "
            f"(expected {expected_executable}; found {observed_executable})"
        )

    payload = read_build_env_marker(destination)
    expected_state = "sealed" if sealed else "initialized"
    if payload.get("state") != expected_state:
        raise SystemExit(
            f"masthead build environment must be {expected_state}; found {payload.get('state')!r}"
        )

    config = destination / "pyvenv.cfg"
    try:
        config_lines = {
            line.strip().lower() for line in config.read_text(encoding="utf-8").splitlines()
        }
    except OSError as exc:
        raise SystemExit(f"masthead build environment config is missing: {config}") from exc
    if "include-system-site-packages = false" not in config_lines:
        raise SystemExit("masthead build environment must disable system site-packages")
    return destination, payload


def _record_path(site_packages: Path, value: str, destination: Path) -> Path:
    logical = PurePosixPath(value)
    if logical.is_absolute():
        raise SystemExit(f"installed distribution RECORD contains an absolute path: {value}")
    resolved = (site_packages / Path(*logical.parts)).resolve()
    if not _is_within(resolved, destination):
        raise SystemExit(f"installed distribution RECORD escapes the build environment: {value}")
    return resolved


def locked_wheel_import_integrity(
    wheel: Path,
    site_packages: Path,
    import_root_name: str,
) -> dict[str, object]:
    """Prove installed import bytes are identical to the retained locked wheel."""
    expected: dict[str, tuple[str, int]] = {}
    seen_members: set[str] = set()
    try:
        with zipfile.ZipFile(wheel) as archive:
            for member in archive.infolist():
                logical = PurePosixPath(member.filename)
                if (
                    logical.is_absolute()
                    or not logical.parts
                    or ".." in logical.parts
                    or "\\" in member.filename
                    or (not member.is_dir() and member.filename != logical.as_posix())
                    or member.filename in seen_members
                ):
                    raise SystemExit(f"retained wheel contains an unsafe member: {member.filename}")
                seen_members.add(member.filename)
                if member.is_dir():
                    continue
                mode = (member.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise SystemExit(f"retained wheel contains a linked member: {member.filename}")
                if logical.parts[0] != import_root_name:
                    continue
                digest = hashlib.sha256()
                with archive.open(member) as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                expected[logical.as_posix()] = (digest.hexdigest(), member.file_size)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise SystemExit(f"cannot verify retained wheel payload {wheel}: {exc}") from exc

    if not expected:
        raise SystemExit(f"retained wheel has no {import_root_name} import payload: {wheel}")

    import_root = (site_packages / import_root_name).resolve()
    if not import_root.is_dir() or not _is_within(import_root, site_packages):
        raise SystemExit(f"masthead build environment has no import root: {import_root_name}")
    installed_names: set[str] = set()
    for installed in import_root.rglob("*"):
        if installed.is_symlink():
            raise SystemExit(f"linked file is forbidden in locked import root: {installed}")
        if not installed.is_file():
            continue
        relative = installed.relative_to(site_packages).as_posix()
        installed_names.add(relative)
        wheel_file = expected.get(relative)
        if wheel_file is None:
            raise SystemExit(f"installed module is absent from retained locked wheel: {installed}")
        expected_sha256, expected_size = wheel_file
        if installed.stat().st_size != expected_size or sha256_file(installed) != expected_sha256:
            raise SystemExit(f"installed module differs from retained locked wheel: {installed}")
    if installed_names != set(expected):
        missing = sorted(set(expected) - installed_names)
        raise SystemExit(f"locked wheel import payload was not fully installed: {missing!r}")

    manifest = sorted((path, digest, size) for path, (digest, size) in expected.items())
    encoded = json.dumps(manifest, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return {
        "file_count": len(manifest),
        "files_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def installed_distribution_integrity(
    build_env: str | Path,
    wheel_artifacts: dict[str, object],
) -> dict[str, object]:
    """Hash every installed locked-distribution file and reject unrecorded code."""
    destination = Path(build_env).resolve()
    site_packages = build_env_site_packages(destination)
    if not site_packages.is_dir():
        raise SystemExit(f"masthead build environment has no site-packages: {site_packages}")

    for hook in ("sitecustomize.py", "sitecustomize.pyc", "usercustomize.py", "usercustomize.pyc"):
        if (site_packages / hook).exists():
            raise SystemExit(f"masthead build environment contains forbidden startup hook: {hook}")

    found: dict[str, list[tuple[Path, str]]] = {name: [] for name in LOCKED_PYTHON_BUILDERS}
    for dist_info in sorted(site_packages.glob("*.dist-info")):
        metadata = dist_info / "METADATA"
        if not metadata.is_file():
            continue
        try:
            parsed = Parser().parsestr(metadata.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            raise SystemExit(f"cannot read installed distribution metadata: {metadata}") from exc
        name = canonical_package_name(parsed.get("Name", ""))
        if name in found:
            found[name].append((dist_info, parsed.get("Version", "")))

    expected_versions = require_lock_matches_pinned_versions()
    archive_dir = destination / BUILD_WHEEL_ARCHIVE_DIR
    result: dict[str, object] = {}
    for name in LOCKED_PYTHON_BUILDERS:
        matches = found[name]
        if len(matches) != 1:
            raise SystemExit(
                f"masthead build environment must contain one {name} distribution; found {len(matches)}"
            )
        dist_info, version = matches[0]
        if version != expected_versions[name]:
            raise SystemExit(
                f"masthead build environment has {name}=={version}; expected {expected_versions[name]}"
            )
        record = dist_info / "RECORD"
        try:
            rows = list(csv.reader(record.read_text(encoding="utf-8").splitlines()))
        except (OSError, UnicodeError, csv.Error) as exc:
            raise SystemExit(f"cannot read installed distribution RECORD: {record}") from exc

        files: list[tuple[str, str, int]] = []
        recorded_paths: set[Path] = set()
        for row in rows:
            if len(row) != 3 or not row[0]:
                raise SystemExit(f"invalid installed distribution RECORD row in {record}")
            installed = _record_path(site_packages, row[0], destination)
            if installed in recorded_paths:
                raise SystemExit(f"duplicate installed distribution RECORD path: {row[0]}")
            recorded_paths.add(installed)
            if installed.is_symlink() or not installed.is_file():
                raise SystemExit(f"installed distribution file is missing or linked: {installed}")
            actual_size = installed.stat().st_size
            actual_sha256 = sha256_file(installed)
            if row[1]:
                try:
                    algorithm, expected_digest = row[1].split("=", 1)
                except ValueError as exc:
                    raise SystemExit(f"invalid hash in installed distribution RECORD: {row[1]}") from exc
                encoded = base64.urlsafe_b64encode(bytes.fromhex(actual_sha256)).decode("ascii").rstrip("=")
                if algorithm != "sha256" or encoded != expected_digest:
                    raise SystemExit(f"installed distribution hash mismatch: {installed}")
            elif installed != record.resolve():
                raise SystemExit(f"unhashed installed distribution file is forbidden: {installed}")
            if row[2] and int(row[2]) != actual_size:
                raise SystemExit(f"installed distribution size mismatch: {installed}")
            files.append(
                (installed.relative_to(destination).as_posix(), actual_sha256, actual_size)
            )

        import_root = (site_packages / LOCKED_IMPORT_ROOTS[name]).resolve()
        if not import_root.is_dir() or not _is_within(import_root, destination):
            raise SystemExit(f"masthead build environment has no import root for {name}")
        for installed in import_root.rglob("*"):
            if installed.is_file() and installed.resolve() not in recorded_paths:
                raise SystemExit(f"unrecorded file in locked import root: {installed}")

        files.sort()
        files_bytes = json.dumps(files, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        artifact = wheel_artifacts.get(name)
        filename = artifact.get("filename") if isinstance(artifact, dict) else None
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise SystemExit(f"masthead retained wheel record is invalid for {name}")
        wheel = (archive_dir / filename).resolve()
        if not _is_within(wheel, archive_dir) or not wheel.is_file():
            raise SystemExit(f"masthead retained wheel is missing for {name}: {wheel}")
        result[name] = {
            "version": version,
            "dist_info": dist_info.relative_to(destination).as_posix(),
            "record_sha256": sha256_file(record),
            "file_count": len(files),
            "files_sha256": hashlib.sha256(files_bytes).hexdigest(),
            "wheel_import": locked_wheel_import_integrity(
                wheel,
                site_packages,
                LOCKED_IMPORT_ROOTS[name],
            ),
        }
    return result


def site_packages_tree_integrity(build_env: str | Path) -> dict[str, object]:
    """Seal every site-packages file, including bootstrap tools and new modules."""
    destination = Path(build_env).resolve()
    site_packages = build_env_site_packages(destination)
    files: list[tuple[str, str, int]] = []
    for installed in site_packages.rglob("*"):
        if installed.is_symlink():
            raise SystemExit(f"linked path is forbidden in masthead site-packages: {installed}")
        if not installed.is_file():
            continue
        files.append(
            (
                installed.relative_to(site_packages).as_posix(),
                sha256_file(installed),
                installed.stat().st_size,
            )
        )
    files.sort()
    encoded = json.dumps(files, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return {
        "file_count": len(files),
        "files_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _file_url_path(url: str) -> Path:
    parsed = urlparse(url)
    if (
        parsed.scheme != "file"
        or parsed.netloc not in {"", "localhost"}
        or parsed.query
        or parsed.fragment
    ):
        raise SystemExit(f"pip install report did not use a local wheel artifact: {url}")
    path = unquote(parsed.path)
    if os.name == "nt":
        # RFC 8089 drive paths arrive as /C:/..., while Path needs C:/...
        # here. Avoid urllib.request: installed skill scripts are statically
        # forbidden from importing network-capable modules.
        if re.match(r"^/[A-Za-z]:/", path):
            path = path[1:]
        path = path.replace("/", os.sep)
    return Path(path).resolve()


def install_report_integrity(
    build_env: str | Path,
    *,
    wheelhouse: str | Path | None = None,
) -> dict[str, object]:
    """Bind pip's selected archive hashes to retained wheel bytes and the lock."""
    destination = Path(build_env).resolve()
    report_path = destination / BUILD_INSTALL_REPORT
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"masthead pip install report is missing or invalid: {report_path}") from exc
    entries = report.get("install") if isinstance(report, dict) else None
    if not isinstance(entries, list):
        raise SystemExit("masthead pip install report has no install list")

    locked = wheel_lock_packages(LOCK)
    expected_names = set(LOCKED_PYTHON_BUILDERS)
    if set(locked) != expected_names:
        raise SystemExit(
            f"masthead build lock must contain exactly {sorted(expected_names)!r}; "
            f"found {sorted(locked)!r}"
        )
    archive_dir = destination / BUILD_WHEEL_ARCHIVE_DIR
    if wheelhouse is not None:
        archive_dir.mkdir(exist_ok=False)
    elif not archive_dir.is_dir():
        raise SystemExit(f"masthead retained wheel directory is missing: {archive_dir}")

    artifacts: dict[str, object] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise SystemExit("masthead pip install report contains an invalid entry")
        metadata = entry.get("metadata")
        download_info = entry.get("download_info")
        if not isinstance(metadata, dict) or not isinstance(download_info, dict):
            raise SystemExit("masthead pip install report entry lacks metadata/download_info")
        name = canonical_package_name(str(metadata.get("name", "")))
        version = str(metadata.get("version", ""))
        if name not in locked or name in artifacts or version != locked[name]["version"]:
            raise SystemExit(f"unexpected distribution in masthead pip install report: {name}=={version}")
        archive_info = download_info.get("archive_info")
        hashes = archive_info.get("hashes") if isinstance(archive_info, dict) else None
        selected_hash = hashes.get("sha256") if isinstance(hashes, dict) else None
        if selected_hash is None and isinstance(archive_info, dict):
            legacy_hash = archive_info.get("hash")
            if isinstance(legacy_hash, str) and legacy_hash.startswith("sha256="):
                selected_hash = legacy_hash.split("=", 1)[1]
        if not isinstance(selected_hash, str) or selected_hash not in locked[name]["hashes"]:
            raise SystemExit(f"pip selected an unlocked wheel hash for {name}=={version}")

        source = _file_url_path(str(download_info.get("url", "")))
        filename = source.name
        retained = archive_dir / filename
        if wheelhouse is not None:
            source_root = Path(wheelhouse).resolve()
            if not _is_within(source, source_root) or source.suffix.lower() != ".whl":
                raise SystemExit(f"pip selected a wheel outside the approved wheelhouse: {source}")
            if sha256_file(source) != selected_hash:
                raise SystemExit(f"downloaded wheel hash changed before sealing: {source}")
            shutil.copyfile(source, retained)
        if not retained.is_file() or sha256_file(retained) != selected_hash:
            raise SystemExit(f"retained wheel hash mismatch: {retained}")
        artifacts[name] = {
            "version": version,
            "filename": filename,
            "sha256": selected_hash,
        }

    if set(artifacts) != expected_names:
        raise SystemExit(
            f"masthead pip install report did not install exactly {sorted(expected_names)!r}"
        )
    return {
        "report_sha256": sha256_file(report_path),
        "artifacts": artifacts,
    }


def build_environment_integrity(
    build_env: str | Path,
    *,
    wheelhouse: str | Path | None = None,
) -> dict[str, object]:
    wheel_artifacts = install_report_integrity(build_env, wheelhouse=wheelhouse)
    artifacts = wheel_artifacts.get("artifacts")
    if not isinstance(artifacts, dict):
        raise SystemExit("masthead retained wheel manifest is invalid")
    core: dict[str, object] = {
        "lock_sha256": build_lock_sha256(),
        "wheel_artifacts": wheel_artifacts,
        "distributions": installed_distribution_integrity(build_env, artifacts),
        "site_packages": site_packages_tree_integrity(build_env),
    }
    encoded = json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**core, "integrity_sha256": hashlib.sha256(encoded).hexdigest()}


def seal_build_environment(build_env: str | Path) -> dict[str, object]:
    destination, marker = require_isolated_python_startup(build_env, sealed=False)
    wheelhouse = marker.get("wheelhouse")
    if not isinstance(wheelhouse, str):
        raise SystemExit("initialized masthead build environment has no wheelhouse")
    integrity = build_environment_integrity(destination, wheelhouse=wheelhouse)
    write_build_env_marker(destination, integrity=integrity)
    return integrity


def verify_build_environment_integrity(build_env: str | Path) -> dict[str, object]:
    destination, marker = require_isolated_python_startup(build_env, sealed=True)
    recorded = marker.get("integrity")
    if not isinstance(recorded, dict):
        raise SystemExit("sealed masthead build environment has no integrity record")
    actual = build_environment_integrity(destination)
    if actual != recorded:
        raise SystemExit("masthead build environment no longer matches its locked wheel seal")
    return actual


def installed_builder_versions(build_env: str | Path | None = None) -> dict[str, str]:
    """Read versions from the libraries that actually shape the outlines."""
    try:
        import fontTools
        import uharfbuzz as hb
    except ImportError as exc:
        raise SystemExit(
            "masthead builder dependencies are missing; run:\n"
            f"  {recovery_command(build_env)}\n"
            f"Resolved build lock: {LOCK}"
        ) from exc
    return {
        "fonttools": fontTools.__version__,
        "uharfbuzz": hb.__version__,
        "harfbuzz": hb.version_string(),
    }


def require_pinned_builder_versions(build_env: str | Path | None = None) -> dict[str, str]:
    """Refuse to emit geometry from an unrecorded shaping toolchain."""
    actual = installed_builder_versions(build_env)
    if actual != PINNED_BUILDER_VERSIONS:
        expected = ", ".join(
            f"{name}={version}" for name, version in PINNED_BUILDER_VERSIONS.items()
        )
        observed = ", ".join(f"{name}={version}" for name, version in actual.items())
        raise SystemExit(
            f"masthead builder version mismatch; run `{recovery_command(build_env)}` "
            f"(expected {expected}; found {observed})"
        )
    return actual


def require_isolated_builder_environment(build_env: str | Path) -> dict[str, object]:
    """Verify the wheel seal, then expose only its site-packages for imports."""
    destination = Path(build_env).resolve()
    integrity = verify_build_environment_integrity(destination)
    site_packages = build_env_site_packages(destination)
    # Standard-library paths stay ahead of the sealed package directory, so a
    # top-level wheel file cannot shadow Python itself.
    sys.path.append(str(site_packages))
    versions = require_pinned_builder_versions(destination)
    import fontTools
    import uharfbuzz

    origins = {
        "fonttools": Path(fontTools.__file__).resolve(),
        "uharfbuzz": Path(uharfbuzz.__file__).resolve(),
    }
    for name, origin in origins.items():
        if not _is_within(origin, destination):
            raise SystemExit(
                f"masthead builder imported {name} outside its dedicated environment: {origin}"
            )
    return {
        "build_env": str(destination),
        "python_executable": os.path.abspath(sys.executable),
        "integrity_sha256": integrity["integrity_sha256"],
        "versions": versions,
        "origins": {name: str(origin) for name, origin in origins.items()},
    }


def outline(src: Path, text: str, size: float) -> tuple[str, float]:
    """Shape `text` with HarfBuzz and return one SVG path plus its advance."""
    import uharfbuzz as hb
    from fontTools.misc.transform import Transform
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    opsz = max(OPSZ_MIN, min(OPSZ_MAX, size))
    font = instantiateVariableFont(TTFont(src), {"opsz": opsz, "wght": 400}, inplace=False)

    # HarfBuzz shapes the instantiated instance, not the variable original.
    blob = BytesIO()
    font.save(blob)
    face = hb.Face(blob.getvalue())
    hbfont = hb.Font(face)
    upem = face.upem
    hbfont.scale = (upem, upem)

    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})

    glyph_set, order = font.getGlyphSet(), font.getGlyphOrder()
    scale = size / upem
    x = 0.0
    parts: list[str] = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = SVGPathPen(glyph_set, ntos=lambda v: f"{v:.1f}")
        # Font space is y-up, SVG is y-down.
        transform = Transform(scale, 0, 0, -scale, x + pos.x_offset * scale, -pos.y_offset * scale)
        glyph_set[order[info.codepoint]].draw(TransformPen(pen, transform))
        commands = pen.getCommands()
        if commands:
            parts.append(commands)
        x += pos.x_advance * scale
    return " ".join(parts), round(x, 2)


def document() -> dict:
    require_lock_matches_pinned_versions()
    builder_versions = require_pinned_builder_versions()
    sources = {"roman": ROMAN, "italic": ITALIC}
    missing = [repo_relative_posix(p) for p in sources.values() if not p.exists()]
    if missing:
        raise SystemExit(f"missing vendored font(s): {', '.join(missing)}")

    from fontTools.ttLib import TTFont

    names = TTFont(ROMAN)["name"]
    glyphs = {}
    for key, spec in SPECS.items():
        path_d, advance = outline(sources[spec["font"]], spec["text"], spec["size"])
        glyphs[key] = {"text": spec["text"], "size": spec["size"], "advance": advance, "d": path_d}

    return {
        "_comment": (
            "Display type for the masthead, stored as vector outlines rather than live text. "
            "Regenerate with python -I -S -B scripts/build_masthead_outlines.py only when "
            "the wordmark or tagline copy changes, then run "
            "python -I -S -B scripts/build_hero.py."
        ),
        "provenance": {
            "font_family": names.getDebugName(1),
            "font_version": names.getDebugName(5),
            "designer": names.getDebugName(9),
            "license": "SIL Open Font License 1.1",
            "license_url": names.getDebugName(14) or "https://scripts.sil.org/OFL",
            "license_text": "assets/fonts/OFL.txt",
            "source": "https://github.com/google/fonts/tree/main/ofl/bodonimoda",
            "vendored": [repo_relative_posix(p) for p in sources.values()],
            "instances": f"opsz tracks rendered size clamped to {OPSZ_MIN}-{OPSZ_MAX}; wght=400 throughout",
            "shaping": "HarfBuzz with kern and liga features enabled",
            "builder_versions": builder_versions,
            "build_lock": {
                "path": BUILD_LOCK_PROVENANCE_PATH,
                "sha256": build_lock_sha256(),
                "install_policy": BUILD_INSTALL_POLICY,
            },
            "note": (
                "Outlines are glyph geometry, not font software. The OFL permits both these "
                "outlines and the bundled originals in assets/fonts/; attribution is retained here."
            ),
        },
        "glyphs": glyphs,
    }


def run_internal_action(action: str, build_env: str | Path) -> int:
    """Execute only after the child proves its interpreter and imports are isolated."""
    if action == "seal":
        integrity = seal_build_environment(build_env)
        print(
            json.dumps(
                {
                    "action": "seal",
                    "status": "ok",
                    "integrity_sha256": integrity["integrity_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0

    report = require_isolated_builder_environment(build_env)
    if action == "verify":
        print(json.dumps({**report, "action": "verify", "status": "ok"}, sort_keys=True))
        return 0

    rendered = json.dumps(document(), indent=2, ensure_ascii=False) + "\n"
    if action == "check":
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != rendered:
            print(
                f"{repo_relative_posix(TARGET)} is out of date; "
                "re-run python -I -S -B scripts/build_masthead_outlines.py"
            )
            return 1
        print("Masthead outlines check passed.")
        print(
            ISOLATED_RESULT_PREFIX
            + json.dumps(
                {
                    "action": "check",
                    "status": "ok",
                    "integrity_sha256": report["integrity_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    if action == "write":
        TARGET.write_text(rendered, encoding="utf-8")
        print(f"Wrote {repo_relative_posix(TARGET)} ({len(rendered)} bytes)")
        print(
            ISOLATED_RESULT_PREFIX
            + json.dumps(
                {
                    "action": "write",
                    "status": "ok",
                    "integrity_sha256": report["integrity_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0
    raise SystemExit(f"unknown isolated masthead action: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify the committed asset is current")
    parser.add_argument(
        "--install-build-deps",
        action="store_true",
        help="force-install the hash-locked build toolchain and exit",
    )
    parser.add_argument(
        "--wheelhouse",
        type=Path,
        help="install only from this local wheel directory; implies pip --no-index",
    )
    parser.add_argument(
        "--build-env",
        type=Path,
        help="dedicated masthead-builder venv (defaults to a checkout-specific temp path)",
    )
    parser.add_argument(
        "--_isolated-action",
        choices=("seal", "verify", "check", "write"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--validate-wheel-lock",
        action="append",
        type=Path,
        default=[],
        help="validate one lock for local --no-index installation and exit",
    )
    args = parser.parse_args(argv)

    if args._isolated_action is not None:
        if args.build_env is None:
            parser.error("internal isolated actions require --build-env")
        if (
            args.check
            or args.install_build_deps
            or args.wheelhouse is not None
            or args.validate_wheel_lock
        ):
            parser.error("internal isolated actions cannot be combined with public options")
        return run_internal_action(args._isolated_action, args.build_env)

    if args.validate_wheel_lock:
        if (
            args.check
            or args.install_build_deps
            or args.wheelhouse is not None
            or args.build_env is not None
        ):
            parser.error("--validate-wheel-lock cannot be combined with install/build options")
        for lock_path in args.validate_wheel_lock:
            require_offline_wheel_lock(lock_path)
            print(f"Offline wheel lock passed: {lock_path}")
        return 0

    if args.check and args.wheelhouse is not None:
        parser.error("--wheelhouse is only used while installing build dependencies")

    if args.install_build_deps:
        if args.check:
            parser.error("--install-build-deps and --check are separate steps")
        destination = install_pinned_builder_dependencies(args.wheelhouse, args.build_env)
        print(
            f"Installed masthead builder from {repo_relative_posix(LOCK)} with wheel hashes "
            f"enforced in {destination}."
        )
        return 0

    if args.check:
        # This stays offline after the explicit preparation step, while still
        # starting a fresh interpreter that cannot inherit parent imports.
        return run_isolated_builder("check", args.build_env or DEFAULT_BUILD_ENV)

    # Writing provenance is a release operation: rebuild the venv and replace
    # every dependency from the locked wheel set before a fresh child renders.
    destination = install_pinned_builder_dependencies(args.wheelhouse, args.build_env)
    return run_isolated_builder("write", destination)


if __name__ == "__main__":
    raise SystemExit(main())

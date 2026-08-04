"""The masthead pair must stay generated, identical in geometry, and on-system.

The dark and light SVGs differ only by palette. Hand-editing them invites one
specific bug: a change landing in one theme and not the other, unnoticed
because most readers only ever see one. These tests pin that the committed
files come from the generator and that the design rules the audit cannot
express are actually held.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_hero  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RETIRED = ("viewfinder", "crosshair", "timecode", "sprocket", "REC", "21:9")
MASTHEAD_INSTALL = "python -I -S -B scripts/build_masthead_outlines.py --install-build-deps"
CI_MASTHEAD_INSTALL = MASTHEAD_INSTALL
HERO_COMMAND = "python -I -S -B scripts/build_hero.py"
CI_WHEELHOUSE = "$RUNNER_TEMP/seedance-wheelhouse"
CI_BUILD_ENV = "/tmp/seedance-masthead-venv-${{ github.run_id }}-${{ github.run_attempt }}"
UHARFBUZZ_PYPI_JSON = "https://pypi.org/pypi/uharfbuzz/0.55.0/json"
UHARFBUZZ_WHEELS = {
    "uharfbuzz-0.55.0-cp310-abi3-win_amd64.whl":
        "72f653625e33f68dda56b258b4b9dcd2ff9c9e4f21fd53c7bbff9d9620c4fba0",
    "uharfbuzz-0.55.0-cp310-abi3-musllinux_1_2_x86_64.whl":
        "22415eaa87c670fac764053edfaebce1e05babd2cecb0e933170019ed3263109",
    "uharfbuzz-0.55.0-cp310-abi3-musllinux_1_2_aarch64.whl":
        "7daeb0ba227246ed8a5a59f64fa23ecec282bc0af13167752d51ae304d20852a",
    "uharfbuzz-0.55.0-cp310-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl":
        "d594f9e02a21745846477f02e13e900bfe9a697bad975fb3c26e241b7a8256c1",
    "uharfbuzz-0.55.0-cp310-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl":
        "13304721967d55e9718200453cae30f7952f95244af4b0fcb4561e8b456f5357",
    "uharfbuzz-0.55.0-cp310-abi3-macosx_10_9_universal2.whl":
        "40df0ff4d0c7af29c07a8adc614fb0dd421d9c4d8a139362a80a4ceb71e94a71",
}


class GeneratorTests(unittest.TestCase):
    def test_committed_files_match_the_generator(self) -> None:
        for path, content in build_hero.targets().items():
            with self.subTest(asset=path.name):
                self.assertTrue(path.exists(), f"{path.name} is missing")
                self.assertEqual(
                    path.read_text(encoding="utf-8"),
                    content,
                    f"{path.name} is stale; re-run {HERO_COMMAND}",
                )

    def test_themes_share_geometry_and_differ_only_in_colour(self) -> None:
        """Strip every colour: what remains must be byte-identical."""
        stripped = []
        for theme in ("dark", "light"):
            svg = build_hero.build(theme)
            stripped.append(re.sub(r"#[0-9A-Fa-f]{6}", "#", svg))
        self.assertEqual(stripped[0], stripped[1], "the two themes have drifted apart structurally")

    def test_palettes_are_actually_different(self) -> None:
        dark = set(re.findall(r"#[0-9A-Fa-f]{6}", build_hero.build("dark")))
        light = set(re.findall(r"#[0-9A-Fa-f]{6}", build_hero.build("light")))
        self.assertFalse(dark & light, "a colour is shared between themes")

    def test_second_render_failure_writes_neither_theme(self) -> None:
        """Both outputs must exist in memory before the first filesystem write."""
        with (
            mock.patch.object(
                build_hero,
                "render",
                side_effect=["dark rendered", RuntimeError("light render failed")],
            ),
            mock.patch.object(Path, "write_text", autospec=True) as write,
        ):
            with self.assertRaisesRegex(RuntimeError, "light render failed"):
                build_hero.main([])
        write.assert_not_called()


class DesignRuleTests(unittest.TestCase):
    """Rules from references/frontend-design-system.md that design_audit.py
    cannot check, because they are about what must be absent."""

    def svgs(self) -> list[str]:
        return [build_hero.build(theme) for theme in ("dark", "light")]

    def test_no_retired_camera_motifs(self) -> None:
        for svg in self.svgs():
            for motif in RETIRED:
                self.assertNotIn(motif, svg, f"retired camera motif present: {motif}")

    def test_exactly_one_accent_gesture(self) -> None:
        for theme in ("dark", "light"):
            svg = build_hero.build(theme)
            accent = build_hero.THEMES[theme]["accent"]
            self.assertEqual(
                svg.count(accent), 1, "the accent hue must appear exactly once per composition"
            )

    def test_only_two_hairlines_plus_one_registration_tick(self) -> None:
        for svg in self.svgs():
            self.assertEqual(svg.count("<line"), 3)

    def test_no_gradients_blur_or_external_references(self) -> None:
        for svg in self.svgs():
            self.assertNotIn("linearGradient", svg)
            self.assertNotIn("feGaussianBlur", svg)
            self.assertNotIn("http://www.w3.org/1999/xlink", svg)
            self.assertIsNone(re.search(r"href=[\"']https?://", svg))

    def test_no_counts_or_version_numbers_are_baked_in(self) -> None:
        """The design system forbids these: they go stale in place."""
        for svg in self.svgs():
            body = svg.split("</desc>", 1)[1]
            self.assertIsNone(
                re.search(r"\bv?\d+\.\d+\.\d+\b", body), "a version number is baked into the masthead"
            )

    def test_accessible_title_and_description(self) -> None:
        for svg in self.svgs():
            self.assertIn("<title>", svg)
            self.assertIn("<desc>", svg)


class OutlinedTypeTests(unittest.TestCase):
    """Display type must not depend on a font the reader may not have.

    The retired stack resolved to Didot only on macOS, a Times clone or the
    default system serif on Linux, and Palatino on most Windows installs - so
    the editorial serif the design system specifies was what a minority of
    readers saw. Outlines remove the dependency entirely.
    """

    ASSETS = [ROOT / "assets/hero-dark.svg", ROOT / "assets/hero-light.svg", ROOT / "assets/skill-map.svg"]
    SERIF_NAMES = ("Georgia", "Didot", "Baskerville", "Palatino", "Hoefler", "Bodoni MT", "Times")

    def test_no_shipped_asset_names_a_system_serif(self) -> None:
        for path in self.ASSETS:
            svg = path.read_text(encoding="utf-8")
            for name in self.SERIF_NAMES:
                with self.subTest(asset=path.name, serif=name):
                    self.assertNotIn(name, svg)

    def test_display_type_is_outlined(self) -> None:
        for path in self.ASSETS:
            with self.subTest(asset=path.name):
                self.assertIn("<path", path.read_text(encoding="utf-8"))

    def test_outline_provenance_is_recorded(self) -> None:
        """OFL attribution must travel with the geometry it produced."""
        data = json.loads((ROOT / "assets/masthead-outlines.json").read_text(encoding="utf-8"))
        prov = data["provenance"]
        for field in ("font_family", "font_version", "designer", "license", "license_url", "source"):
            self.assertTrue(prov.get(field), f"provenance is missing {field}")
        self.assertIn("Open Font License", prov["license"])

    def test_masthead_builder_versions_are_pinned_and_recorded(self) -> None:
        """Committed geometry names its shapers without importing them on the host."""
        import build_masthead_outlines as gen

        expected = {
            "fonttools": "4.63.0",
            "uharfbuzz": "0.55.0",
            "harfbuzz": "14.2.1",
        }
        lock_path = ROOT / "requirements-masthead.lock"
        lock = lock_path.read_text(encoding="utf-8")
        self.assertIn("fonttools==4.63.0", lock)
        self.assertIn("uharfbuzz==0.55.0", lock)
        self.assertIn("Linux (glibc and musl", lock)
        self.assertIn(UHARFBUZZ_PYPI_JSON, lock)
        uharfbuzz_block = lock.split("uharfbuzz==0.55.0", 1)[1]
        locked_uharfbuzz_hashes = set(
            re.findall(r"--hash=sha256:([0-9a-f]{64})", uharfbuzz_block)
        )
        self.assertEqual(locked_uharfbuzz_hashes, set(UHARFBUZZ_WHEELS.values()))
        for filename, digest in UHARFBUZZ_WHEELS.items():
            self.assertIn(filename, lock)
            self.assertIn(f"--hash=sha256:{digest}", lock)
        for package in ("fonttools", "uharfbuzz"):
            block = lock.split(f"{package}==", 1)[1]
            if package == "fonttools":
                block = block.split("uharfbuzz==", 1)[0]
            self.assertRegex(block, r"--hash=sha256:[0-9a-f]{64}")
        self.assertEqual(gen.pinned_builder_versions(), expected)

        data = json.loads((ROOT / "assets/masthead-outlines.json").read_text(encoding="utf-8"))
        self.assertEqual(data["provenance"]["builder_versions"], expected)
        build_lock = data["provenance"]["build_lock"]
        self.assertEqual(build_lock["path"], "requirements-masthead.lock")
        self.assertEqual(build_lock["sha256"], hashlib.sha256(lock_path.read_bytes()).hexdigest())
        self.assertIn("--force-reinstall --require-hashes", build_lock["install_policy"])
        self.assertEqual(gen.build_lock_sha256(), build_lock["sha256"])

    def test_hero_rejects_tampered_provenance_before_any_svg_write(self) -> None:
        """Path, policy, digest, and shaper claims are exact release inputs."""
        original = json.loads(
            (ROOT / "assets/masthead-outlines.json").read_text(encoding="utf-8")
        )
        cases = {
            "builder_versions": lambda data: data["provenance"].__setitem__(
                "builder_versions",
                {**data["provenance"]["builder_versions"], "uharfbuzz": "999.0"},
            ),
            "build_lock.path": lambda data: data["provenance"]["build_lock"].__setitem__(
                "path", "./requirements-masthead.lock"
            ),
            "install_policy": lambda data: data["provenance"]["build_lock"].__setitem__(
                "install_policy", data["provenance"]["build_lock"]["install_policy"] + "."
            ),
            "sha256": lambda data: data["provenance"]["build_lock"].__setitem__(
                "sha256", "0" * 64
            ),
        }
        for expected_error, mutate in cases.items():
            with self.subTest(field=expected_error), tempfile.TemporaryDirectory(
                dir=ROOT
            ) as temp:
                tampered = json.loads(json.dumps(original))
                mutate(tampered)
                outlines = Path(temp) / "masthead-outlines.json"
                outlines.write_text(
                    json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
                )
                with (
                    mock.patch.object(build_hero, "OUTLINES", outlines),
                    mock.patch.object(Path, "write_text", autospec=True) as write,
                ):
                    with self.assertRaisesRegex(SystemExit, re.escape(expected_error)):
                        build_hero.main([])
                write.assert_not_called()

    def test_hero_rejects_tampered_lock_bytes_before_any_svg_write(self) -> None:
        """A matching provenance record cannot bless a modified local lock."""
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            lock = Path(temp) / "requirements-masthead.lock"
            lock.write_bytes(build_hero.LOCK.read_bytes() + b"\n# tampered\n")
            with (
                mock.patch.object(build_hero, "LOCK", lock),
                mock.patch.object(Path, "write_text", autospec=True) as write,
            ):
                with self.assertRaisesRegex(SystemExit, "sha256"):
                    build_hero.main([])
            write.assert_not_called()

    def test_hero_rejects_a_rehashed_lock_with_drifted_package_pins(self) -> None:
        """A forged matching digest must not override the declared shaper contract."""
        original = json.loads(
            (ROOT / "assets/masthead-outlines.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            temp_root = Path(temp)
            lock = temp_root / "requirements-masthead.lock"
            drifted = build_hero.LOCK.read_bytes().replace(
                b"uharfbuzz==0.55.0", b"uharfbuzz==0.54.0"
            )
            lock.write_bytes(drifted)
            original["provenance"]["build_lock"]["sha256"] = hashlib.sha256(
                drifted
            ).hexdigest()
            outlines = temp_root / "masthead-outlines.json"
            outlines.write_text(json.dumps(original), encoding="utf-8")
            with (
                mock.patch.object(build_hero, "OUTLINES", outlines),
                mock.patch.object(build_hero, "LOCK", lock),
                mock.patch.object(Path, "write_text", autospec=True) as write,
            ):
                with self.assertRaisesRegex(SystemExit, "package pins"):
                    build_hero.main([])
            write.assert_not_called()

    def test_masthead_builder_refuses_an_unpinned_toolchain(self) -> None:
        """A different shaper must fail before silently rewriting committed geometry."""
        import build_masthead_outlines as gen

        mismatched = gen.pinned_builder_versions()
        mismatched["uharfbuzz"] = "999.0"
        with mock.patch.object(gen, "installed_builder_versions", return_value=mismatched):
            with self.assertRaisesRegex(SystemExit, "version mismatch"):
                gen.require_pinned_builder_versions()

    def test_masthead_builder_missing_dependency_error_uses_the_locked_install(self) -> None:
        """A clean checkout must fail closed with the reproducible recovery command."""
        import build_masthead_outlines as gen

        for missing in ("fontTools", "uharfbuzz"):
            with self.subTest(missing=missing):
                with mock.patch.dict(sys.modules, {missing: None}):
                    with self.assertRaisesRegex(SystemExit, re.escape(gen.recovery_command())):
                        gen.installed_builder_versions()

    def test_masthead_recovery_is_cwd_independent(self) -> None:
        """The emitted recovery path must work when the generator is invoked by absolute path."""
        script = ROOT / "scripts/build_masthead_outlines.py"
        lock = ROOT / "requirements-masthead.lock"
        with tempfile.TemporaryDirectory() as cwd:
            build_env = Path(cwd) / "unprepared-builder"
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    str(script),
                    "--check",
                    "--build-env",
                    str(build_env),
                ],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
        message = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(script), message)
        self.assertIn(str(lock), message)
        self.assertIn(str(build_env), message)
        self.assertNotIn("--requirement requirements-masthead.lock", message)

    def test_verified_installer_never_reuses_a_same_version_environment(self) -> None:
        """Even matching versions must go through a fresh venv and forced hash install."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            build_env = Path(temp) / "builder"
            wheelhouse = Path(temp) / "wheelhouse"
            wheelhouse.mkdir()
            events: list[str] = []
            with (
                mock.patch.object(
                    gen,
                    "prepare_build_environment",
                    side_effect=lambda *args: events.append("prepare") or build_env,
                ) as prepare,
                mock.patch.object(
                    gen,
                    "bootstrap_build_environment_pip",
                    side_effect=lambda *args: events.append("bootstrap"),
                ) as bootstrap,
                mock.patch.object(
                    gen,
                    "run_initialized_build_env_command",
                    side_effect=lambda *args, **kwargs: events.append("install"),
                ) as run,
                mock.patch.object(
                    gen,
                    "seal_isolated_builder",
                    side_effect=lambda *args: events.append("seal"),
                ) as seal,
                mock.patch.object(
                    gen,
                    "verify_isolated_builder",
                    side_effect=lambda *args: events.append("verify"),
                ) as verify,
            ):
                result = gen.install_pinned_builder_dependencies(
                    wheelhouse=wheelhouse, build_env=build_env
                )

        self.assertEqual(result, build_env)
        prepare.assert_called_once_with(build_env, wheelhouse.resolve())
        bootstrap.assert_called_once_with(build_env)
        seal.assert_called_once_with(build_env)
        verify.assert_called_once_with(build_env)
        run.assert_called_once()
        self.assertEqual(events, ["prepare", "bootstrap", "install", "seal", "verify"])
        self.assertEqual(
            run.call_args.args[1],
            gen.pinned_install_argv(
                gen.build_env_python(build_env), wheelhouse.resolve(), build_env
            ),
        )
        self.assertEqual(run.call_args.args[0], build_env)
        pip_env = run.call_args.kwargs["environment"]
        self.assertEqual(pip_env["PIP_CONFIG_FILE"], os.devnull)
        self.assertEqual(
            [key for key in pip_env if key.upper().startswith("PIP_")],
            ["PIP_CONFIG_FILE"],
        )
        argv = run.call_args.args[1]
        self.assertEqual(argv[1], "-I")
        self.assertIn("--force-reinstall", argv)
        self.assertIn("--no-compile", argv)
        self.assertIn("--no-deps", argv)
        self.assertIn("--no-index", argv)
        self.assertIn("--require-hashes", argv)
        self.assertIn("--report", argv)
        self.assertEqual(Path(argv[-1]), ROOT / "requirements-masthead.lock")

    def test_build_environment_clear_is_marker_guarded_and_isolated(self) -> None:
        """The venv refresh must not clear arbitrary paths or inherit Python hooks."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            unmarked = Path(temp) / "not-ours"
            unmarked.mkdir()
            (unmarked / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(SystemExit, "unmarked"):
                gen.resolve_build_env(unmarked)

            destination = Path(temp) / "builder"
            events: list[str] = []
            with (
                mock.patch.object(
                    gen.subprocess,
                    "run",
                    side_effect=lambda *args, **kwargs: events.append("venv"),
                ) as run,
                mock.patch.object(
                    gen,
                    "write_build_env_marker",
                    side_effect=lambda *args, **kwargs: events.append("marker"),
                ) as marker,
                mock.patch.object(
                    gen,
                    "clear_build_env_trust",
                    side_effect=lambda *args, **kwargs: events.append("clear-trust"),
                ) as clear_trust,
                mock.patch.object(
                    gen,
                    "write_build_env_trust",
                    side_effect=lambda *args, **kwargs: events.append("write-trust"),
                ) as write_trust,
                mock.patch.object(
                    gen,
                    "require_build_env_trust",
                    side_effect=lambda *args, **kwargs: events.append("verify-trust") or {},
                ) as require_trust,
                mock.patch.dict(
                    os.environ,
                    {"PYTHONPATH": "attacker", "PIP_INDEX_URL": "https://bad.invalid"},
                ),
            ):
                self.assertEqual(gen.prepare_build_environment(destination), destination.resolve())
            marker.assert_called_once_with(destination.resolve(), wheelhouse=None)
            clear_trust.assert_called_once_with(destination.resolve())
            write_trust.assert_called_once_with(destination.resolve(), state="initialized")
            require_trust.assert_called_once_with(destination.resolve(), state="initialized")
            self.assertEqual(
                events,
                ["clear-trust", "venv", "marker", "write-trust", "verify-trust"],
            )
            argv = run.call_args.args[0]
            self.assertEqual(
                argv[:6],
                [str(gen.trusted_base_python()), "-I", "-S", "-B", "-m", "venv"],
            )
            self.assertIn("--clear", argv)
            self.assertIn("--without-pip", argv)
            child_env = run.call_args.kwargs["env"]
            self.assertNotIn("PYTHONPATH", child_env)
            self.assertNotIn("PIP_INDEX_URL", child_env)

    def test_build_environment_rejects_protected_ancestors_and_descendants(self) -> None:
        """A marker must never authorize clearing a directory containing protected data."""
        import build_masthead_outlines as gen

        protected_ancestors = {
            gen.ROOT.parent.resolve(),
            Path.home().resolve().parent,
            Path(sys.prefix).resolve().parent,
            Path(tempfile.gettempdir()).resolve().parent,
        }
        for candidate in protected_ancestors:
            with self.subTest(candidate=candidate), self.assertRaisesRegex(
                SystemExit, "unsafe masthead build environment"
            ):
                gen.resolve_build_env(candidate)

        protected_descendants = {
            gen.ROOT / ".unsafe-builder",
            Path.home() / ".pr124-unsafe-builder",
            Path(sys.prefix) / "pr124-descendant-probe",
            Path(sys.base_prefix) / "pr124-descendant-probe",
            Path(sys.exec_prefix) / "pr124-descendant-probe",
            Path(sys.base_exec_prefix) / "pr124-descendant-probe",
            Path(sys.executable).parent / "pr124-descendant-probe",
        }
        for candidate in protected_descendants:
            with self.subTest(candidate=candidate), self.assertRaisesRegex(
                SystemExit, "unsafe masthead build environment"
            ):
                gen.resolve_build_env(candidate)

        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            trust_root = temp_root / "external-trust"
            with mock.patch.object(gen, "BUILD_TRUST_ROOT", trust_root):
                for candidate in (trust_root / "builder", temp_root):
                    with self.subTest(candidate=candidate), self.assertRaisesRegex(
                        SystemExit, "unsafe masthead build environment"
                    ):
                        gen.resolve_build_env(candidate)

                safe = temp_root / "dedicated-builder"
                self.assertEqual(gen.resolve_build_env(safe), safe.resolve())

    def test_same_version_modules_without_a_wheel_seal_are_rejected(self) -> None:
        """Version strings and in-venv paths do not substitute for a wheel seal."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            build_env = temp_root / "builder"
            venv.EnvBuilder(with_pip=False).create(build_env)
            gen.write_build_env_marker(build_env)
            venv_python = gen.build_env_python(build_env)
            purelib = Path(
                subprocess.run(
                    [
                        str(venv_python),
                        "-I",
                        "-c",
                        "import sysconfig; print(sysconfig.get_paths()['purelib'])",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            )

            trusted_fonttools = purelib / "fontTools"
            trusted_fonttools.mkdir(parents=True)
            (trusted_fonttools / "__init__.py").write_text(
                "__version__ = '4.63.0'\nORIGIN = 'trusted-venv'\n", encoding="utf-8"
            )
            trusted_hb = purelib / "uharfbuzz"
            trusted_hb.mkdir()
            (trusted_hb / "__init__.py").write_text(
                "__version__ = '0.55.0'\n"
                "ORIGIN = 'trusted-venv'\n"
                "def version_string(): return '14.2.1'\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SystemExit, "external trust"):
                gen.verify_isolated_builder(build_env)

    def test_in_venv_sitecustomize_cannot_short_circuit_a_check(self) -> None:
        """`-S` must stop a prepared venv hook from exiting zero before validation."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            build_env = root / "builder"
            venv.EnvBuilder(with_pip=False).create(build_env)
            gen.write_build_env_marker(
                build_env,
                integrity={"integrity_sha256": "0" * 64},
            )
            venv_python = gen.build_env_python(build_env)
            purelib = Path(
                subprocess.run(
                    [
                        str(venv_python),
                        "-I",
                        "-c",
                        "import sysconfig; print(sysconfig.get_paths()['purelib'])",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            )
            sentinel = root / "sitecustomize-ran.txt"
            (purelib / "sitecustomize.py").write_text(
                "from pathlib import Path\n"
                f"Path({str(sentinel)!r}).write_text('ran', encoding='utf-8')\n"
                "import os\nos._exit(0)\n",
                encoding="utf-8",
            )

            with mock.patch.object(gen, "BUILD_TRUST_ROOT", root / "external-trust"):
                gen.write_build_env_trust(build_env, state="sealed")
                self.assertNotEqual(gen.run_isolated_builder("check", build_env), 0)
            self.assertFalse(sentinel.exists(), "in-venv sitecustomize executed despite -S")
            argv = gen.isolated_builder_argv("check", build_env)
            self.assertEqual(argv[1:4], ["-I", "-S", "-B"])

    def test_forged_runner_and_self_authored_marker_lack_external_trust(self) -> None:
        """A fake python executable must be rejected before its forged success runs."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            build_env = root / "forged-builder"
            runner = gen.build_env_python(build_env)
            runner.parent.mkdir(parents=True)
            runner.write_bytes(b"MZ-forged-runner")
            base_executable = Path(
                getattr(sys, "_base_executable", sys.executable)
            ).resolve()
            version = ".".join(str(part) for part in sys.version_info[:3])
            (build_env / "pyvenv.cfg").write_text(
                f"home = {base_executable.parent}\n"
                "include-system-site-packages = false\n"
                f"version = {version}\n",
                encoding="utf-8",
            )
            gen.write_build_env_marker(
                build_env,
                integrity={"integrity_sha256": "0" * 64},
            )
            forged = subprocess.CompletedProcess(
                [],
                0,
                stdout=(
                    gen.ISOLATED_RESULT_PREFIX
                    + json.dumps(
                        {
                            "action": "check",
                            "status": "ok",
                            "integrity_sha256": "0" * 64,
                        }
                    )
                    + "\n"
                ),
                stderr="",
            )
            external_trust = root / "external-trust"
            isolated_argv = gen.isolated_builder_argv("check", build_env)
            self.assertEqual(Path(isolated_argv[0]).resolve(), base_executable)
            self.assertNotEqual(Path(isolated_argv[0]).resolve(), runner.resolve())
            with (
                mock.patch.object(gen, "BUILD_TRUST_ROOT", external_trust),
                mock.patch.object(gen.subprocess, "run", return_value=forged) as run,
                self.assertRaisesRegex(SystemExit, "no external trust record"),
            ):
                gen.run_isolated_builder("check", build_env)

            run.assert_not_called()
            with mock.patch.object(gen, "BUILD_TRUST_ROOT", external_trust):
                trust_path = gen.build_env_trust_path(build_env)
                self.assertFalse(trust_path.is_relative_to(build_env))
                trust_path.parent.mkdir(parents=True)
                trust_path.write_text('{"state":"sealed"}\n', encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "not the trusted stdlib venv launcher"):
                    gen.require_build_env_trust(build_env, state="sealed")

    def test_windows_venv_runner_source_selects_the_exact_upstream_variant(self) -> None:
        """Version, free-threading, and debug status bind the launcher name."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stdlib = root / "Lib"
            venv_dir = stdlib / "venv"
            scripts = venv_dir / "scripts" / "nt"
            scripts.mkdir(parents=True)
            for name in (
                "python.exe",
                "python_d.exe",
                "venvlauncher.exe",
                "venvlauncher_d.exe",
                "venvlaunchert.exe",
                "venvlaunchert_d.exe",
            ):
                (scripts / name).write_bytes(name.encode("ascii"))
            for name in (
                "python.exe",
                "python_d.exe",
                "python3.13t.exe",
                "python3.13t_d.exe",
            ):
                (root / name).write_bytes(("base-" + name).encode("ascii"))

            cases = (
                (
                    "3.13 normal",
                    "python.exe",
                    (3, 13),
                    False,
                    scripts / "venvlauncher.exe",
                ),
                (
                    "3.13 free-threaded",
                    "python3.13t.exe",
                    (3, 13),
                    True,
                    scripts / "venvlaunchert.exe",
                ),
                (
                    "3.13 debug",
                    "python_d.exe",
                    (3, 13),
                    False,
                    scripts / "venvlauncher_d.exe",
                ),
                (
                    "3.13 free-threaded debug",
                    "python3.13t_d.exe",
                    (3, 13),
                    True,
                    scripts / "venvlaunchert_d.exe",
                ),
                ("3.12 legacy", "python.exe", (3, 12), False, scripts / "python.exe"),
                (
                    "3.12 legacy debug",
                    "python_d.exe",
                    (3, 12),
                    False,
                    scripts / "python_d.exe",
                ),
            )
            for label, base_name, version, gil_disabled, expected in cases:
                with self.subTest(layout=label):
                    self.assertEqual(
                        gen.windows_venv_runner_source(
                            root / base_name,
                            venv_dir,
                            version,
                            gil_disabled=gil_disabled,
                            python_build=False,
                        ),
                        expected,
                    )

            build_dir = root / "PCbuild" / "amd64"
            build_dir.mkdir(parents=True)
            source_base = build_dir / "python.exe"
            source_base.write_bytes(b"base-python")
            source_launcher = build_dir / "venvlauncher.exe"
            source_launcher.write_bytes(b"source-build-launcher")
            self.assertEqual(
                gen.windows_venv_runner_source(
                    source_base,
                    stdlib / "venv",
                    (3, 13),
                    gil_disabled=False,
                    python_build=True,
                ),
                source_launcher,
            )
            self.assertEqual(
                gen.windows_venv_runner_source(
                    source_base,
                    stdlib / "venv",
                    (3, 12),
                    gil_disabled=False,
                    python_build=True,
                ),
                source_base,
            )

    def test_windows_venv_runner_source_refuses_the_wrong_variant(self) -> None:
        """An existing launcher for a different ABI cannot become the trust anchor."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stdlib = root / "Lib"
            venv_dir = stdlib / "venv"
            scripts = venv_dir / "scripts" / "nt"
            scripts.mkdir(parents=True)
            (scripts / "venvlauncher.exe").write_bytes(b"wrong-abi")

            cases = (
                ("free-threaded", root / "python3.13t.exe", True, "venvlaunchert\\.exe"),
                ("debug", root / "python_d.exe", False, "venvlauncher_d\\.exe"),
            )
            for label, base, gil_disabled, expected in cases:
                with self.subTest(layout=label), self.assertRaisesRegex(SystemExit, expected):
                    gen.windows_venv_runner_source(
                        base,
                        venv_dir,
                        (3, 13),
                        gil_disabled=gil_disabled,
                        python_build=False,
                    )

            for version in ((3, 10), (3, 14)):
                with self.subTest(version=version), self.assertRaisesRegex(
                    SystemExit, "supports CPython 3\\.11 through 3\\.13"
                ):
                    gen.windows_venv_runner_source(
                        root / "python.exe",
                        venv_dir,
                        version,
                        gil_disabled=False,
                        python_build=False,
                    )

            (root / "python.exe").write_bytes(b"legacy-base-lookalike")
            with self.assertRaisesRegex(SystemExit, "trusted stdlib venv runner is missing"):
                gen.windows_venv_runner_source(
                    root / "python.exe",
                    venv_dir,
                    (3, 12),
                    gil_disabled=False,
                    python_build=False,
                )

    @unittest.skipUnless(os.name == "nt", "Windows venv launcher provenance")
    def test_windows_venv_runner_source_matches_real_envbuilder(self) -> None:
        """The selected source must be byte-identical to a real venv runner."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            build_env = Path(temp) / "builder"
            venv.EnvBuilder(with_pip=False).create(build_env)
            generated = gen.build_env_python(build_env)
            source = gen.trusted_venv_runner_source()

            self.assertEqual(generated.stat().st_size, source.stat().st_size)
            self.assertEqual(gen.sha256_file(generated), gen.sha256_file(source))

    def test_external_trust_rejects_runner_config_marker_and_script_tampering(self) -> None:
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            # Hosted Windows TEMP may use an 8.3 alias (RUNNER~1) while
            # Path.resolve() in the production verifier expands it. Keep the
            # mocked trusted base in that same canonical namespace.
            root = Path(temp).resolve()
            trust_root = root / "external-trust"

            def prepared(name: str) -> Path:
                build_env = root / name
                runner = gen.build_env_python(build_env)
                runner.parent.mkdir(parents=True)
                runner.write_bytes(gen.trusted_venv_runner_source().read_bytes())
                base_executable = gen.trusted_base_python()
                version = ".".join(str(part) for part in sys.version_info[:3])
                (build_env / "pyvenv.cfg").write_text(
                    f"home = {base_executable.parent}\n"
                    "include-system-site-packages = false\n"
                    f"version = {version}\n",
                    encoding="utf-8",
                )
                gen.write_build_env_marker(
                    build_env,
                    integrity={"integrity_sha256": "1" * 64},
                )
                gen.write_build_env_trust(build_env, state="sealed")
                gen.require_build_env_trust(build_env, state="sealed")
                return build_env

            with mock.patch.object(gen, "BUILD_TRUST_ROOT", trust_root):
                trusted_base = root / "trusted-base-python"
                trusted_base.write_bytes(b"trusted-base")
                stable_runner_source = root / "trusted-runner-source"
                stable_runner_source.write_bytes(
                    gen.trusted_venv_runner_source().read_bytes()
                )
                with (
                    mock.patch.object(
                        gen, "trusted_base_python", return_value=trusted_base
                    ),
                    mock.patch.object(
                        gen,
                        "trusted_venv_runner_source",
                        return_value=stable_runner_source,
                    ),
                ):
                    base_env = prepared("base")
                    trusted_base.write_bytes(b"replaced-base")
                    with self.assertRaisesRegex(SystemExit, "trust mismatch"):
                        gen.require_build_env_trust(base_env, state="sealed")

                runner_env = prepared("runner")
                gen.build_env_python(runner_env).write_bytes(b"forged-runner")
                with self.assertRaisesRegex(SystemExit, "not the trusted stdlib venv launcher"):
                    gen.require_build_env_trust(runner_env, state="sealed")

                config_env = prepared("config")
                (config_env / "pyvenv.cfg").write_text(
                    "include-system-site-packages = true\n", encoding="utf-8"
                )
                with self.assertRaisesRegex(SystemExit, "does not match trusted base Python"):
                    gen.require_build_env_trust(config_env, state="sealed")

                marker_env = prepared("marker")
                marker = marker_env / gen.BUILD_ENV_MARKER
                marker.write_text(marker.read_text(encoding="utf-8") + " ", encoding="utf-8")
                with self.assertRaisesRegex(SystemExit, "trust mismatch"):
                    gen.require_build_env_trust(marker_env, state="sealed")

                trusted_script = root / "trusted-builder.py"
                trusted_script.write_text("# trusted\n", encoding="utf-8")
                with mock.patch.object(gen, "SCRIPT", trusted_script):
                    script_env = prepared("script")
                    trusted_script.write_text("# replaced\n", encoding="utf-8")
                    with self.assertRaisesRegex(SystemExit, "trust mismatch"):
                        gen.require_build_env_trust(script_env, state="sealed")

    def test_pip_bootstrap_verifies_initialized_runner_and_config_before_execution(self) -> None:
        """Neither ensurepip nor pip may run through a forged new-environment launcher."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trust_root = root / "external-trust"

            def initialized(name: str) -> Path:
                build_env = root / name
                runner = gen.build_env_python(build_env)
                runner.parent.mkdir(parents=True)
                runner.write_bytes(gen.trusted_venv_runner_source().read_bytes())
                version = ".".join(str(part) for part in sys.version_info[:3])
                (build_env / "pyvenv.cfg").write_text(
                    f"home = {gen.trusted_base_python().parent}\n"
                    "include-system-site-packages = false\n"
                    f"version = {version}\n",
                    encoding="utf-8",
                )
                gen.write_build_env_marker(build_env)
                gen.write_build_env_trust(build_env, state="initialized")
                return build_env

            with mock.patch.object(gen, "BUILD_TRUST_ROOT", trust_root):
                valid_env = initialized("valid")
                events: list[str] = []
                real_require = gen.require_build_env_trust

                def require_then_record(*args: object, **kwargs: object) -> dict[str, object]:
                    result = real_require(*args, **kwargs)
                    events.append("trust")
                    return result

                with (
                    mock.patch.object(
                        gen,
                        "require_build_env_trust",
                        side_effect=require_then_record,
                    ),
                    mock.patch.object(
                        gen.subprocess,
                        "run",
                        side_effect=lambda *args, **kwargs: events.append("run"),
                    ) as run,
                ):
                    gen.bootstrap_build_environment_pip(valid_env)
                self.assertEqual(events, ["trust", "run"])
                self.assertEqual(
                    run.call_args.args[0],
                    gen.ensurepip_argv(gen.build_env_python(valid_env)),
                )
                bootstrap_argv = run.call_args.args[0]
                self.assertEqual(bootstrap_argv[1:3], ["-I", "-B"])
                self.assertNotIn(
                    "-S",
                    bootstrap_argv,
                    "Python 3.11 would otherwise target the base prefix",
                )
                with (
                    mock.patch.object(gen.subprocess, "run") as run,
                    self.assertRaisesRegex(SystemExit, "untrusted.*command"),
                ):
                    gen.run_initialized_build_env_command(
                        valid_env,
                        gen.ensurepip_argv(gen.trusted_base_python()),
                        environment=gen.python_clean_environment(),
                    )
                run.assert_not_called()

                runner_env = initialized("runner")
                gen.build_env_python(runner_env).write_bytes(b"forged-runner")
                with (
                    mock.patch.object(gen.subprocess, "run") as run,
                    self.assertRaisesRegex(
                        SystemExit, "not the trusted stdlib venv launcher"
                    ),
                ):
                    gen.bootstrap_build_environment_pip(runner_env)
                run.assert_not_called()

                config_env = initialized("config")
                (config_env / "pyvenv.cfg").write_text(
                    "include-system-site-packages = true\n", encoding="utf-8"
                )
                with (
                    mock.patch.object(gen.subprocess, "run") as run,
                    self.assertRaisesRegex(
                        SystemExit, "does not match trusted base Python"
                    ),
                ):
                    gen.bootstrap_build_environment_pip(config_env)
                run.assert_not_called()

    def test_documented_isolated_startup_ignores_hostile_parent_sitecustomize(self) -> None:
        """The public command must reach its own failure instead of hostile exit zero."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            attacker = root / "attacker"
            attacker.mkdir()
            sentinel = root / "hostile-startup-ran.txt"
            (attacker / "sitecustomize.py").write_text(
                "from pathlib import Path\n"
                f"Path({str(sentinel)!r}).write_text('ran', encoding='utf-8')\n"
                "import os\nos._exit(0)\n",
                encoding="utf-8",
            )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(attacker)
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    str(gen.SCRIPT),
                    "--check",
                    "--build-env",
                    str(root / "missing-builder"),
                ],
                capture_output=True,
                text=True,
                env=environment,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(sentinel.exists())
        self.assertIn("not prepared", result.stdout + result.stderr)
        self.assertIn("-I -S -B", gen.recovery_command())

    def test_build_hero_public_command_is_isolated_and_ignores_hostile_startup(self) -> None:
        """The sibling-importing check must survive a hostile parent PYTHONPATH."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            attacker = root / "attacker"
            attacker.mkdir()
            sentinel = root / "build-hero-sitecustomize-ran.txt"
            (attacker / "sitecustomize.py").write_text(
                "from pathlib import Path\n"
                f"Path({str(sentinel)!r}).write_text('ran', encoding='utf-8')\n"
                "import os\nos._exit(0)\n",
                encoding="utf-8",
            )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(attacker)
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-B",
                    str(ROOT / "scripts/build_hero.py"),
                    "--check",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                env=environment,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(sentinel.exists())
        self.assertIn("Masthead check passed", result.stdout)
        self.assertEqual(build_hero.PUBLIC_COMMAND, HERO_COMMAND)

    def test_site_packages_seal_changes_when_same_version_module_bytes_change(self) -> None:
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            build_env = Path(temp) / "builder"
            site_packages = gen.build_env_site_packages(build_env)
            package = site_packages / "fontTools"
            package.mkdir(parents=True)
            module = package / "__init__.py"
            module.write_text("__version__ = '4.63.0'\nTRUSTED = True\n", encoding="utf-8")
            trusted = gen.site_packages_tree_integrity(build_env)
            module.write_text("__version__ = '4.63.0'\nTRUSTED = False\n", encoding="utf-8")
            replaced = gen.site_packages_tree_integrity(build_env)

        self.assertEqual(trusted["file_count"], replaced["file_count"])
        self.assertNotEqual(trusted["files_sha256"], replaced["files_sha256"])

    def test_installed_modules_must_match_the_locked_wheel_bytes(self) -> None:
        """A forged installed RECORD cannot bless same-version replacement code."""
        import zipfile

        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wheel = root / "fonttools-4.63.0-py3-none-any.whl"
            trusted_bytes = b"__version__ = '4.63.0'\nTRUSTED = True\n"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("fontTools/__init__.py", trusted_bytes)

            site_packages = root / "site-packages"
            package = site_packages / "fontTools"
            package.mkdir(parents=True)
            module = package / "__init__.py"
            module.write_bytes(trusted_bytes)
            sealed = gen.locked_wheel_import_integrity(wheel, site_packages, "fontTools")

            module.write_bytes(b"__version__ = '4.63.0'\nTRUSTED = False\n")
            with self.assertRaisesRegex(SystemExit, "differs from retained locked wheel"):
                gen.locked_wheel_import_integrity(wheel, site_packages, "fontTools")

        self.assertEqual(sealed["file_count"], 1)

    def test_verified_installer_can_refuse_every_package_index(self) -> None:
        """CI's repository-script phase must consume only its prepared wheelhouse."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            wheelhouse = Path(temp) / "wheelhouse"
            build_env = Path(temp) / "builder"
            argv = gen.pinned_install_argv("python", wheelhouse, build_env)
        self.assertIn("--no-index", argv)
        self.assertIn("--find-links", argv)
        self.assertEqual(argv[1], "-I")
        self.assertIn("--disable-pip-version-check", argv)
        self.assertEqual(Path(argv[argv.index("--find-links") + 1]), wheelhouse.resolve())
        self.assertIn("--require-hashes", argv)
        self.assertEqual(
            Path(argv[argv.index("--report") + 1]),
            build_env.resolve() / gen.BUILD_INSTALL_REPORT,
        )

    def test_pip_environment_drops_inherited_network_and_config_overrides(self) -> None:
        import build_masthead_outlines as gen

        clean = gen.pip_clean_environment(
            {
                "PATH": "bin",
                "PIP_INDEX_URL": "https://example.invalid/simple",
                "pip_find_links": "https://example.invalid/wheels",
                "PIP_CONFIG_FILE": "attacker.ini",
                "PYTHONPATH": "attacker",
                "pythonhome": "attacker-home",
                "VIRTUAL_ENV": "attacker-venv",
                "LD_PRELOAD": "/tmp/attacker.so",
                "LD_LIBRARY_PATH": "/tmp/attacker-libs",
                "DYLD_INSERT_LIBRARIES": "/tmp/attacker.dylib",
                "DYLD_LIBRARY_PATH": "/tmp/attacker-libs",
            }
        )
        self.assertEqual(clean, {"PATH": "bin", "PIP_CONFIG_FILE": os.devnull})

    def test_offline_installer_rejects_requirement_url_escape_hatches(self) -> None:
        """--no-index must not be undermined by a direct URL added to the lock."""
        import build_masthead_outlines as gen

        escapes = (
            b"evil @ https://example.invalid/evil.whl",
            b"--requirement https://example.invalid/extra.txt",
            b"--constraint https://example.invalid/constraints.txt",
            b"--find-links https://example.invalid/wheels",
            b"--extra-index-url https://example.invalid/simple",
        )
        for escape in escapes:
            with self.subTest(escape=escape), self.assertRaisesRegex(
                SystemExit, "not safe for offline"
            ):
                gen.require_offline_wheel_lock(
                    gen.LOCK,
                    gen.LOCK.read_bytes() + b"\n" + escape + b"\n",
                )

    def test_wheel_lock_requires_exactly_one_binary_only_directive(self) -> None:
        import build_masthead_outlines as gen

        locked = gen.LOCK.read_bytes()
        directive = b"--only-binary=:all:"
        without = b"\n".join(
            line for line in locked.splitlines() if line.strip() != directive
        )
        with self.assertRaisesRegex(SystemExit, "exactly once before pins"):
            gen.require_offline_wheel_lock(gen.LOCK, without)
        with self.assertRaisesRegex(SystemExit, "exactly once before pins"):
            gen.require_offline_wheel_lock(gen.LOCK, directive + b"\n" + locked)

    def test_every_wheel_download_explicitly_refuses_sdists(self) -> None:
        import build_masthead_outlines as gen

        argv = gen.pinned_download_argv("python", CI_WHEELHOUSE)
        self.assertIn("--only-binary=:all:", argv)
        workflow = (ROOT / ".github/workflows/validate-skills.yml").read_text(
            encoding="utf-8"
        )
        download_lines = [
            line
            for line in workflow.splitlines()
            if " pip " in line and " download " in line
        ]
        self.assertEqual(len(download_lines), 2)
        self.assertTrue(
            all("--only-binary=:all:" in line for line in download_lines),
            download_lines,
        )

    def test_both_ci_locks_use_the_offline_allowlist(self) -> None:
        import build_masthead_outlines as gen

        gen.require_offline_wheel_lock(ROOT / "requirements-validation.lock")
        gen.require_offline_wheel_lock(ROOT / "requirements-masthead.lock")
        with mock.patch("builtins.print"):
            self.assertEqual(
                gen.main(
                    [
                        "--validate-wheel-lock",
                        str(ROOT / "requirements-validation.lock"),
                        "--validate-wheel-lock",
                        str(ROOT / "requirements-masthead.lock"),
                    ]
                ),
                0,
            )

    def test_verified_installer_rejects_lock_pin_drift_before_pip(self) -> None:
        """Hash enforcement cannot compensate for a lock that names the wrong release."""
        import build_masthead_outlines as gen

        with tempfile.TemporaryDirectory() as temp:
            lock = Path(temp) / "requirements-masthead.lock"
            lock.write_bytes(
                gen.LOCK.read_bytes().replace(
                    b"uharfbuzz==0.55.0", b"uharfbuzz==0.54.0"
                )
            )
            with (
                mock.patch.object(gen, "LOCK", lock),
                mock.patch.object(gen.subprocess, "run") as run,
            ):
                with self.assertRaisesRegex(SystemExit, "version mismatch"):
                    gen.install_pinned_builder_dependencies()
            run.assert_not_called()

    def test_install_cli_routes_to_the_verified_installer(self) -> None:
        """The command copied from README, CI, or an error must execute the forced installer."""
        import build_masthead_outlines as gen

        with (
            mock.patch.object(
                gen,
                "install_pinned_builder_dependencies",
                return_value=Path(tempfile.gettempdir()) / "builder",
            ) as install,
            mock.patch.object(gen, "document") as document,
            mock.patch("builtins.print"),
        ):
            self.assertEqual(gen.main(["--install-build-deps"]), 0)

        install.assert_called_once_with(None, None)
        document.assert_not_called()

    def test_writing_the_asset_cannot_bypass_the_verified_installer(self) -> None:
        """Every CLI write must install, then render only in its isolated child."""
        import build_masthead_outlines as gen

        events = []
        build_env = Path(tempfile.gettempdir()) / "builder"
        with (
            mock.patch.object(
                gen,
                "install_pinned_builder_dependencies",
                side_effect=lambda wheelhouse=None, requested_env=None: (
                    events.append("install") or build_env
                ),
            ) as install,
            mock.patch.object(
                gen,
                "run_isolated_builder",
                side_effect=lambda action, environment: events.append(action) or 0,
            ) as isolated,
            mock.patch.object(gen, "document") as document,
        ):
            self.assertEqual(gen.main([]), 0)

        install.assert_called_once_with(None, None)
        isolated.assert_called_once_with("write", build_env)
        document.assert_not_called()
        self.assertEqual(events, ["install", "write"])

    def test_masthead_install_is_hash_enforced_everywhere_it_is_documented(self) -> None:
        """Release, CI, and script help must not regress to unconstrained installs."""
        import build_masthead_outlines as gen
        import validate_repo

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_setup = readme.split("## Validation", 1)[1].split("## Design Standard", 1)[0]
        workflow = (ROOT / ".github/workflows/validate-skills.yml").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertTrue(CI_BUILD_ENV.startswith("/tmp/seedance-masthead-venv-"))
        self.assertIn("${{ github.run_id }}", CI_BUILD_ENV)
        self.assertIn("${{ github.run_attempt }}", CI_BUILD_ENV)
        self.assertNotIn("$RUNNER_TEMP", CI_BUILD_ENV)
        self.assertIn(MASTHEAD_INSTALL, release_setup)
        self.assertGreaterEqual(readme.count(MASTHEAD_INSTALL), 2)
        self.assertGreaterEqual(readme.count(HERO_COMMAND), 2)
        archive_plan = {
            check.display_command()
            for check in validate_repo.validation_plan(release=False)
        }
        self.assertIn(HERO_COMMAND + " --check", archive_plan)
        self.assertIn("python scripts/validate_repo.py", workflow)
        self.assertIn(HERO_COMMAND + " --check", security)
        for public_document in (readme, workflow, security):
            self.assertNotIn("python scripts/build_hero.py", public_document)
        self.assertIn(
            "python -I -S -B scripts/build_masthead_outlines.py --check",
            release_setup,
        )
        self.assertIn(
            CI_MASTHEAD_INSTALL
            + ' --wheelhouse "'
            + CI_WHEELHOUSE
            + '" --build-env "'
            + CI_BUILD_ENV
            + '"',
            workflow,
        )
        self.assertIn(
            'env -i PATH="$PATH" HOME="$HOME" PIP_CONFIG_FILE=/dev/null '
            "python -I -m pip --disable-pip-version-check download "
            "--only-binary=:all: --index-url https://pypi.org/simple --require-hashes",
            workflow,
        )
        self.assertIn(
            'env -i PATH="$PATH" HOME="$HOME" PIP_CONFIG_FILE=/dev/null '
            "python -I -m pip --disable-pip-version-check install --force-reinstall "
            "--no-index --find-links",
            workflow,
        )
        self.assertIn("--validate-wheel-lock requirements-validation.lock", workflow)
        self.assertIn(
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            workflow,
        )
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn(
            'python -I -S -B scripts/build_masthead_outlines.py --check --build-env "'
            + CI_BUILD_ENV
            + '"',
            workflow,
        )
        self.assertEqual(workflow.count('--build-env "' + CI_BUILD_ENV + '"'), 2)
        self.assertNotIn('--build-env "$RUNNER_TEMP/', workflow)
        self.assertGreaterEqual(workflow.count('env -i PATH="$PATH" HOME="$HOME"'), 6)
        self.assertIn(MASTHEAD_INSTALL, gen.__doc__)
        self.assertNotIn("pip install " + "fonttools uharfbuzz", gen.__doc__)
        argv = gen.pinned_install_argv("python", CI_WHEELHOUSE, CI_BUILD_ENV)
        self.assertEqual(argv[1], "-I")
        self.assertIn("--force-reinstall", argv)
        self.assertIn("--no-compile", argv)
        self.assertIn("--no-deps", argv)
        self.assertIn("--no-index", argv)
        self.assertIn("--require-hashes", argv)
        self.assertEqual(Path(argv[-1]), ROOT / "requirements-masthead.lock")

    def test_the_generator_can_run_from_a_clean_checkout(self) -> None:
        """The fonts it reads must be tracked, or the documented path is fiction."""
        import build_masthead_outlines as gen

        for font in (gen.ROMAN, gen.ITALIC):
            with self.subTest(font=font.name):
                self.assertTrue(font.exists(), f"{font.name} is not in the repository")
        self.assertTrue((ROOT / "assets/fonts/OFL.txt").exists(), "OFL text must ship with the fonts")
        self.assertEqual(gen.TARGET, ROOT / "assets/masthead-outlines.json",
                         "the generator must write the asset the masthead actually reads")

    def test_masthead_provenance_paths_are_posix(self) -> None:
        """Generated JSON must be byte-identical on Windows and POSIX hosts."""
        import build_masthead_outlines as gen

        self.assertEqual(
            gen.repo_relative_posix(gen.ROMAN),
            "assets/fonts/BodoniModa[opsz,wght].ttf",
        )
        self.assertEqual(
            gen.repo_relative_posix(gen.ITALIC),
            "assets/fonts/BodoniModa-Italic[opsz,wght].ttf",
        )
        cases = (
            (
                PureWindowsPath("C:/checkout"),
                PureWindowsPath("C:/checkout/assets/fonts/Font.ttf"),
            ),
            (PurePosixPath("/checkout"), PurePosixPath("/checkout/assets/fonts/Font.ttf")),
        )
        for root, font in cases:
            with self.subTest(root=str(root)):
                with mock.patch.object(gen, "ROOT", root):
                    self.assertEqual(gen.repo_relative_posix(font), "assets/fonts/Font.ttf")

    def test_declared_font_families_must_be_monospace(self) -> None:
        """A denylist of serif names passes Arial and bare generics."""
        import design_audit

        for bad in ('<text font-family="serif">x</text>',
                    '<text font-family="Arial">x</text>',
                    '<style>.a{font:400 15px Georgia,serif}</style>'):
            with self.subTest(svg=bad):
                self.assertTrue(design_audit.font_family_findings("t.svg", bad))
        self.assertEqual(
            design_audit.font_family_findings("t.svg", '<text font-family="ui-monospace, monospace">x</text>'), []
        )

    def test_every_run_the_masthead_uses_is_present(self) -> None:
        glyphs = build_hero.glyphs()
        for key in ("wordmark", "skill_os", "tagline_1", "tagline_2"):
            self.assertIn(key, glyphs)
            self.assertTrue(glyphs[key]["d"].startswith("M"), f"{key} has no path data")
            self.assertGreater(glyphs[key]["advance"], 0)


if __name__ == "__main__":
    unittest.main()

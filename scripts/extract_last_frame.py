#!/usr/bin/env python3
"""Extract the last (or first) frame of an accepted clip for continuation work.

The continuation gates require the observed end state of the previous accepted
take before any successor prompt is written - but nothing paid for that
requirement: the user had to scrub the clip and describe ~10 categories by hand
for every clip of a long project. This tool removes most of that cost:

  python scripts/extract_last_frame.py takes/clip_02_take1.mp4
  python scripts/extract_last_frame.py takes/clip_02_take1.mp4 --first-frame
  python scripts/extract_last_frame.py takes/clip_02_take1.mp4 --emit-record

The extracted frame becomes (a) the continuation image reference and (b) the
agent's observation source: attach it and the AGENT fills the observation
record from what is visible, asking only about what a still can never show
(open motion, camera movement phase, audio phase). See the Observation Fast
Path in references/continuation-handoff.md and the Source-Carries-State Rule
in references/prompt-compiler.md.

Requires ffmpeg on PATH (or pass --ffmpeg /path/to/ffmpeg). The --self-test
mode is pure Python for offline CI: it verifies the observation-record template
stays aligned with the take-review schema and that no frame-readable category
is misfiled as frame-blind.

Existing output images are preserved by default. Pass --force only when replacing
one is intentional. Extraction always happens in a private same-directory staging
file; a complete frame is published atomically so a failed run cannot expose a
partial final output.
"""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Categories the agent can read directly off the extracted still.
FRAME_READABLE = [
    ("summary", "one sentence: what is visible at the final frame"),
    ("subject_pose", "body position, hands, gaze, expression state"),
    ("screen_position", "where the subject sits in frame; travel_direction if mid-move"),
    ("wardrobe_props", "wardrobe state and prop positions vs continuity locks"),
    ("environment", "location arrangement, doors/objects state, weather"),
    ("lighting_phase", "key direction, practicals on/off, time-of-day feel"),
    ("camera_framing", "shot size and angle at the final frame"),
]
# Categories a still can NEVER show - the only things left to ask the user
# (or read from the clip itself when the full video is attached).
FRAME_BLIND = [
    ("open_motion", "what was still moving at the cut - direction and speed"),
    ("camera_move_phase", "was the camera mid-move (pan/dolly/track) and toward what"),
    ("audio_phase", "ambience bed, unfinished dialogue, music state at the cut"),
]
# Take-review fields this record feeds (schemas/take-review.schema.json).
TAKE_REVIEW_FIELDS = ["observed_end_state", "observation_confidence", "accepted_deviations"]


class OutputPolicyError(RuntimeError):
    """The requested output operation would violate the fail-closed policy."""


@dataclass(frozen=True)
class OutputStage:
    """A staging path and the stable identity of the file created there."""

    path: Path
    identity: tuple[int, int]


def _identity(info: os.stat_result) -> tuple[int, int]:
    return (info.st_dev, info.st_ino)


def _is_reparse_point(info: os.stat_result) -> bool:
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & flag)


def _path_exists(path: Path) -> bool:
    """Include dangling links: every occupied destination name is a collision."""

    return os.path.lexists(os.fspath(path))


def _paths_alias(left: Path, right: Path) -> bool:
    try:
        if left.resolve(strict=True) == right.resolve(strict=False):
            return True
    except OSError:
        pass
    if _path_exists(right):
        try:
            return os.path.samefile(left, right)
        except OSError:
            pass
    return False


def _validate_output_target(clip: Path, out: Path, force: bool) -> None:
    parent = out.parent
    if not parent.is_dir():
        raise OutputPolicyError(f"output directory not found: {parent}")
    if _paths_alias(clip, out):
        raise OutputPolicyError("output path must differ from the input clip")
    if not _path_exists(out):
        return
    if not force:
        raise OutputPolicyError(f"output already exists: {out}; choose another path or pass --force")

    # --force is deliberately narrow: it replaces a regular file, never a
    # directory, symlink, junction, device, or other special destination.
    try:
        info = os.lstat(out)
    except OSError as exc:
        raise OutputPolicyError(f"cannot inspect existing output {out}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode) or _is_reparse_point(info):
        raise OutputPolicyError(f"--force only replaces a regular output file: {out}")


def _create_output_stage(out: Path) -> OutputStage:
    suffix = out.suffix or ".img"
    prefix = f".{out.stem}.atomic-"
    try:
        descriptor, raw_path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=out.parent)
    except OSError as exc:
        raise OutputPolicyError(f"cannot create output staging file beside {out}: {exc}") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or _is_reparse_point(info):
            raise OutputPolicyError("output staging object is not a regular file")
        return OutputStage(Path(raw_path), _identity(info))
    finally:
        os.close(descriptor)


def _verify_output_stage(stage: OutputStage, *, require_content: bool) -> None:
    """Refuse swapped, linked, special, or incomplete staging objects."""

    try:
        before = os.lstat(stage.path)
    except OSError as exc:
        raise OutputPolicyError(f"output staging file disappeared: {stage.path}") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or _is_reparse_point(before)
        or _identity(before) != stage.identity
        or before.st_nlink != 1
    ):
        raise OutputPolicyError("output staging file identity changed; refusing publication")

    try:
        # Windows rejects FlushFileBuffers on a read-only handle, so open the
        # owned stage read/write before fsyncing its completed contents.
        with stage.path.open("r+b", buffering=0) as handle:
            opened = os.fstat(handle.fileno())
            if (
                not stat.S_ISREG(opened.st_mode)
                or _is_reparse_point(opened)
                or _identity(opened) != stage.identity
                or opened.st_nlink != 1
            ):
                raise OutputPolicyError("output staging file identity changed while verifying")
            if require_content and opened.st_size == 0:
                raise OutputPolicyError("ffmpeg produced an empty output staging file")
            os.fsync(handle.fileno())
    except OutputPolicyError:
        raise
    except OSError as exc:
        raise OutputPolicyError(f"cannot verify output staging file: {exc}") from exc

    try:
        after = os.lstat(stage.path)
    except OSError as exc:
        raise OutputPolicyError("output staging file disappeared while verifying") from exc
    if (
        not stat.S_ISREG(after.st_mode)
        or _is_reparse_point(after)
        or _identity(after) != stage.identity
        or after.st_nlink != 1
    ):
        raise OutputPolicyError("output staging file identity changed while verifying")


def _cleanup_output_stage(stage: OutputStage) -> bool:
    """Remove only the exact regular staging file we created."""

    try:
        info = os.lstat(stage.path)
    except FileNotFoundError:
        return True
    except OSError as exc:
        sys.stderr.write(f"warning: could not inspect staging path {stage.path}: {exc}\n")
        return False
    if (
        not stat.S_ISREG(info.st_mode)
        or _is_reparse_point(info)
        or _identity(info) != stage.identity
    ):
        sys.stderr.write(
            f"warning: staging path identity changed; leaving unexpected path untouched: {stage.path}\n"
        )
        return False
    try:
        stage.path.unlink()
    except OSError as exc:
        sys.stderr.write(f"warning: could not remove staging file {stage.path}: {exc}\n")
        return False
    return True


def _publish_output(stage: OutputStage, clip: Path, out: Path, force: bool) -> None:
    _verify_output_stage(stage, require_content=True)
    if force:
        # Re-check immediately before the atomic replacement so a late path
        # alias or special-file collision is also refused.
        _validate_output_target(clip, out, force=True)
        try:
            os.replace(stage.path, out)
        except OSError as exc:
            raise OutputPolicyError(f"could not atomically replace output {out}: {exc}") from exc
        return

    try:
        # A same-directory hard link is an atomic no-replace publication:
        # creation fails if any object claimed the destination name meanwhile.
        os.link(stage.path, out)
    except FileExistsError as exc:
        raise OutputPolicyError(f"output appeared during extraction and was preserved: {out}") from exc
    except OSError as exc:
        raise OutputPolicyError(f"could not atomically publish output {out}: {exc}") from exc


def extract_frame(ffmpeg: str, clip: Path, out: Path, first: bool, force: bool) -> int:
    _validate_output_target(clip, out, force)
    stage = _create_output_stage(out)
    try:
        rc = run_ffmpeg(ffmpeg, clip, stage.path, first)
        if rc != 0:
            return rc
        _publish_output(stage, clip, out, force)
        print(f"{'first' if first else 'last'} frame -> {out}")
        return 0
    finally:
        _cleanup_output_stage(stage)


def build_record() -> str:
    lines = ["OBSERVATION RECORD (fills observed_end_state; agent completes from the frame)"]
    lines.append("\n# Read from the extracted frame - the agent fills these, not the user:")
    lines += [f"- {k}: ...  ({hint})" for k, hint in FRAME_READABLE]
    lines.append("\n# A still cannot show these - ask the user, or read from the attached clip:")
    lines += [f"- {k}: ...  ({hint})" for k, hint in FRAME_BLIND]
    lines.append("\n# Then set observation_confidence (high with frame attached; note any unreadable area)")
    lines.append("# and list accepted_deviations vs the planned end state before reconciling canon.")
    return "\n".join(lines)


def run_ffmpeg(ffmpeg: str, clip: Path, out: Path, first: bool) -> int:
    if first:
        cmd = [ffmpeg, "-y", "-i", str(clip), "-frames:v", "1", "-q:v", "2", str(out)]
    else:
        # Decode the stream through EOF and overwrite the same image for every
        # decoded frame.  ``-frames:v 1`` must not be used here: it stops at the
        # first frame after a seek instead of allowing the true final frame to
        # win.  Full decoding also avoids depending on container duration or
        # keyframe-seek accuracy.
        cmd = [ffmpeg, "-y", "-i", str(clip), "-update", "1", "-q:v", "2", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        sys.stderr.write(proc.stderr[-800:] + "\n")
        print(f"extraction failed for {clip}")
        return 1
    return 0


def self_test() -> int:
    errors: list[str] = []
    record = build_record()
    for key, _ in FRAME_READABLE + FRAME_BLIND:
        if f"- {key}:" not in record:
            errors.append(f"record template missing category {key}")
    for field in TAKE_REVIEW_FIELDS:
        if field not in record:
            errors.append(f"record template must mention take-review field {field}")
    overlap = {k for k, _ in FRAME_READABLE} & {k for k, _ in FRAME_BLIND}
    if overlap:
        errors.append(f"categories filed as both frame-readable and frame-blind: {sorted(overlap)}")
    for blind in ("open_motion", "camera_move_phase", "audio_phase"):
        if blind in {k for k, _ in FRAME_READABLE}:
            errors.append(f"{blind} cannot be read from a still and must stay frame-blind")
    schema = Path(__file__).resolve().parent.parent / "schemas" / "take-review.schema.json"
    if not schema.exists():
        errors.append("schemas/take-review.schema.json missing")
    if errors:
        print("extract_last_frame self-test FAILED:")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"extract_last_frame self-test passed: {len(FRAME_READABLE)} frame-readable + "
          f"{len(FRAME_BLIND)} frame-blind categories, take-review fields referenced.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract the last/first frame of an accepted clip. The default behavior refuses "
            "to replace an existing output."
        )
    )
    parser.add_argument("clip", nargs="?", help="path to the accepted take (mp4/mov/webm)")
    parser.add_argument("-o", "--output", help="output image path (default: <clip>.last.png / .first.png)")
    parser.add_argument("--first-frame", action="store_true", help="extract the first frame instead")
    parser.add_argument("--ffmpeg", default=None, help="path to ffmpeg if not on PATH")
    parser.add_argument(
        "--force",
        action="store_true",
        help="atomically replace an existing regular output file after extraction succeeds",
    )
    parser.add_argument("--emit-record", action="store_true", help="print the observation-record skeleton")
    parser.add_argument("--self-test", action="store_true", help="offline wiring check, no ffmpeg or media")
    parser.add_argument("--strict", action="store_true", help="accepted for parity with other validators")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.emit_record and not args.clip:
        print(build_record())
        return 0
    if not args.clip:
        parser.error("clip path required (or use --self-test / --emit-record)")

    clip = Path(args.clip)
    if not clip.exists():
        print(f"clip not found: {clip}")
        return 1
    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        print("ffmpeg not found on PATH; install it or pass --ffmpeg /path/to/ffmpeg")
        return 2
    suffix = ".first.png" if args.first_frame else ".last.png"
    out = Path(args.output) if args.output else clip.with_suffix(clip.suffix + suffix)
    try:
        rc = extract_frame(ffmpeg, clip, out, args.first_frame, args.force)
    except OutputPolicyError as exc:
        print(f"output refused: {exc}")
        return 1
    except OSError as exc:
        print(f"output failed safely: {exc}")
        return 1
    if rc == 0 and args.emit_record:
        print()
        print(build_record())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

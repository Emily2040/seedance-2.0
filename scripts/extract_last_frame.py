#!/usr/bin/env python3
"""Extract the last (or first) frame of an accepted clip for continuation work.

The continuation gates require the observed end state of the previous accepted
take before any successor prompt is written - but nothing paid for that
requirement: the user had to scrub the clip and describe ~10 categories by hand
for every clip of a long project. This tool removes most of that cost:

  python scripts/extract_last_frame.py takes/clip_02_take1.mp4
  python scripts/extract_last_frame.py takes/clip_02_take1.mp4 --first-frame
  python scripts/extract_last_frame.py takes/clip_02_take1.mp4 --emit-record

Existing output images are preserved by default. Choose another --output path,
or pass --force only when replacing that exact file is intentional.

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
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
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
    print(f"{'first' if first else 'last'} frame -> {out}")
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


class OutputPolicyError(Exception):
    """The requested output path cannot be used without risking another file."""


def reserve_output(out: Path, *, force: bool) -> bool:
    """Atomically claim a new output path; return whether a claim was created.

    ``Path.exists()`` followed by FFmpeg would leave a race in which two agents
    both see a free path and the second silently replaces the first result.
    Exclusive creation makes exactly one no-force caller the owner. FFmpeg's
    internal ``-y`` then replaces only that caller's empty reservation.
    """
    if not out.parent.is_dir():
        raise OutputPolicyError(f"output directory not found: {out.parent}")
    if force:
        return False
    try:
        with out.open("xb"):
            pass
    except FileExistsError as exc:
        raise OutputPolicyError(
            f"output already exists: {out}\n"
            "Refusing to replace it. Choose another --output path or re-run with --force."
        ) from exc
    except OSError as exc:
        raise OutputPolicyError(f"cannot reserve output path {out}: {exc}") from exc
    return True


def remove_failed_reservation(out: Path) -> None:
    try:
        out.unlink(missing_ok=True)
    except OSError as exc:
        print(f"warning: could not remove failed output reservation {out}: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract the last/first frame of an accepted clip.")
    parser.add_argument("clip", nargs="?", help="path to the accepted take (mp4/mov/webm)")
    parser.add_argument("-o", "--output", help="output image path (default: <clip>.last.png / .first.png)")
    parser.add_argument("--first-frame", action="store_true", help="extract the first frame instead")
    parser.add_argument("--ffmpeg", default=None, help="path to ffmpeg if not on PATH")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output image; default behavior refuses",
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
    if out.resolve() == clip.resolve():
        print(f"output path must differ from the input clip: {out}")
        return 1
    try:
        reserved = reserve_output(out, force=args.force)
    except OutputPolicyError as exc:
        print(exc)
        return 1
    try:
        rc = run_ffmpeg(ffmpeg, clip, out, args.first_frame)
    except BaseException:
        if reserved:
            remove_failed_reservation(out)
        raise
    if rc != 0 and reserved:
        remove_failed_reservation(out)
    if rc == 0 and args.emit_record:
        print()
        print(build_record())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

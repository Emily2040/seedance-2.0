#!/usr/bin/env python3
"""Stress-test the prompt architecture this repository teaches.

Scores three arms of the same 34 briefs against each other:

  naive_online      what a listicle or an untrained user writes
  quickstart_style  the shape the beginner-facing example taught before v6.6.x
                    fixed it - kept as a frozen regression arm, not a current doc
  skill_formula     seedance-prompt's Director Formula, followed literally

The point is the gap between arms. If the skill's doctrine is sound, the
skill_formula arm clears the release bar in references/eval-rubric.md and the
others do not - and if a beginner-facing example teaches a shape that misses
that bar, this is where it shows up rather than in user feedback.

Scores are mechanical: every dimension is computed from the text against the
repository's own stated rules. No human judgement is applied, so the arms are
comparable. Offline and dependency-free, like every other check here.

    python scripts/prompt_architecture_stress.py            # score the shipped corpus
    python scripts/prompt_architecture_stress.py --strict   # fail if the doctrine arm regresses

Dimensions (0-4, matching references/eval-rubric.md's V6 scale):
  opening_authority  subject/action (or reference binding) in the lead clause
  length_fit         official 60-100 word band; skill's 40-110 fast-lane band
  slop_free          density of anti-slop-lexicon terms
  coverage           camera move / motivated light / sound / visible endpoint
  structure          prose shooting-brief vs comma tag-salad, negation slop
  ref_integrity      reference tags present and byte-exact for reference modes
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from pathlib import Path

# ---------------------------------------------------------------- vocabularies

# references/anti-slop-lexicon.md - the six slop classes.
SLOP = [
    "cinematic", "epic", "stunning", "beautiful", "dramatic", "gorgeous",
    "breathtaking", "mesmerizing", "masterpiece", "award-winning", "8k", "4k",
    "ultra-hd", "ultra hd", "high quality", "highly detailed", "insanely detailed",
    "trending on artstation", "unreal engine", "hyperrealistic", "ultra-realistic",
    "photorealistic masterpiece", "visually striking", "magical", "dynamic",
    "atmospheric", "moody", "vibey", "professional looking", "viral", "aesthetic",
    "perfect", "amazing", "incredible", "flawless", "immaculate", "sublime",
]

# Negation slop: "no blur", "without artifacts", etc.
NEGATION = re.compile(
    r"\b(no|without|avoid|don't have|free of)\s+"
    r"(blur|artifacts?|distortion|extra fingers|deformed|glitch|noise|warping|morphing)\b",
    re.I,
)

CAMERA = re.compile(
    r"\b(dollys?|dollies|push(?:es)?[-\s]?in|pull(?:s)?[-\s]?(?:back|out)|trucks?|"
    r"pans?|tilts?|cranes?|jibs?|orbits?|arcs?|handheld|steadicam|zooms?|"
    r"track(?:s|ing)?\b|drift(?:s|ing)?|whip pan|rack focus|locked[-\s]?off|"
    r"static|framing|reframe|follows?|settles? (?:on|as|when|square)|"
    r"camera (?:holds?|stays?|rises?|falls?|drifts?|settles?|moves?|sits?|starts?|"
    r"path|movement|rhythm))\b",
    re.I,
)

LIGHT = re.compile(
    r"\b(sunlight|sun|window light|practical|lamp|neon|firelight|candle|headlight|"
    r"key light|rim light|backlight|fluorescent|overcast|moonlight|streetlight|"
    r"screen glow|monitor glow|daylight|dusk|dawn|golden hour|shaft of light|"
    r"bare bulb|work light|sodium|torch|flashlight|match|lantern|skylight|"
    r"earthlight|earthshine|softbox(?:es)?|ring light|exit sign|forge|burner|"
    r"glow|lit from|lights?|lighting|top light|"
    r"overhead (?:light|fluorescent|tubes)|shadow)\b",
    re.I,
)

SOUND = re.compile(
    r"\b(sound|audio|ambien\w*|room tone|silence|near-silence|hum|clatter|scrape|"
    r"footsteps?|rain on|wind|breath\w*|voice|says|dialogue|line:|sfx|music|rumble|"
    r"click|creak|chime|birdsong|traffic|engine|whirr|buzz|drip|splash)\b",
    re.I,
)

# A visible endpoint / decisive change - the "one beat" the skill demands.
ENDPOINT = re.compile(
    r"\b(stops?|settles?|lands?|closes?|opens?|halts?|comes to rest|holds? on|"
    r"ends? on|rests?|locks?|finishes|arrives?|turns? to face|meets?|touches?|"
    r"catches?|sets? down|picks? up|steps? through|final frame|last frame|"
    r"still(?:s)?|goes still|freezes?|endpoint|comes? to rest|completed?)\b",
    re.I,
)

# Camera/shot metadata that indicates a camera-first opening.
SHOT_META = re.compile(
    r"^\s*(?:@?\w+\s+)?(?:extreme\s+)?(?:medium|wide|close|full|low|high|eye|over|"
    r"macro|aerial|dutch|tight|establishing|two-?shot|master)\b[-\s]?"
    r"(?:close-?up|shot|angle|level|wide|the-?shoulder)?",
    re.I,
)
STYLE_FIRST = re.compile(r"^\s*(?:a\s+)?(?:cinematic|epic|beautiful|stunning|dramatic|hyper\w*|photo\w*|4k|8k)\b", re.I)
REF_TAG = re.compile(r"@(?:Image|Video|Audio|图片|视频|音频)\s?\d+|\[(?:Video|Image|Audio) \d+\]")

REF_MODES = {"I2V", "V2V", "R2V", "FLF2V", "EDIT", "EXTEND"}

# Modes that build on supplied footage. For these the skill's instruction is to
# describe only what the source cannot supply, so explicitly *preserving* a
# dimension addresses it exactly as fully as specifying one. Demanding a fresh
# light source from an edit prompt would score the doctrine's own advice as a
# defect.
PRESERVING_MODES = {"I2V", "V2V", "FLF2V", "EDIT", "EXTEND"}
PRESERVE = {
    "camera": re.compile(r"\b(keep|preserv\w+|hold|same|unchanged|existing|original)\b[^.;]{0,60}"
                         r"\b(camera|framing|lens|shot|tracking|move|path|rhythm)\b", re.I),
    "light": re.compile(r"\b(keep|preserv\w+|hold|same|unchanged|existing|original|do not relight)\b"
                        r"[^.;]{0,60}\b(light\w*|exposure|grade|key)\b", re.I),
    "sound": re.compile(r"\b(keep|preserv\w+|hold|same|unchanged|existing|original)\b[^.;]{0,60}"
                        r"\b(audio|sound|dialogue|bed)\b", re.I),
}

# A continuation may bind to accepted footage in prose rather than with an asset
# tag; the surface decides which is available. Both are real contracts.
PROSE_BINDING = re.compile(
    r"\b(accepted (?:final frame|clip|footage|take)|observed (?:final frame|end state)|"
    r"source clip|previous clip|final frame of)\b", re.I,
)


def words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def score_opening(prompt: str) -> tuple[float, str]:
    """Does the highest-weight opening spend itself on the subject?"""
    head = " ".join(words(prompt)[:10])
    if STYLE_FIRST.search(prompt):
        return 0.0, "opens on an empty evaluator"
    if REF_TAG.match(prompt.strip()):
        return 4.0, "opens on a reference binding (subject authority)"
    if SHOT_META.match(prompt.strip()):
        return 2.0, "opens on camera/shot metadata, not the subject"
    # A concrete noun phrase followed by a verb inside the lead clause.
    if re.search(r"\b(is|are|stands?|sits?|walks?|holds?|turns?|lowers?|raises?|reads?|"
                 r"steps?|leans?|kneels?|runs?|reaches?|lifts?|opens?|pushes?|"
                 r"drags?|carries?|waits?|rests?|hangs?|floats?|drifts?|slides?)\b", head, re.I):
        return 4.0, "subject and action lead"
    return 3.0, "subject leads, action arrives late"


def score_length(prompt: str) -> tuple[float, str]:
    n = len(words(prompt))
    if 60 <= n <= 100:
        return 4.0, f"{n}w - inside the documented 60-100 band"
    if 40 <= n < 60:
        return 3.0, f"{n}w - compact, inside the skill's 40-110 lane"
    if 100 < n <= 110:
        return 3.0, f"{n}w - long but inside the skill's lane"
    if 110 < n <= 140:
        return 1.5, f"{n}w - over budget"
    if n < 40:
        return 1.5, f"{n}w - under-specified"
    return 0.0, f"{n}w - far over budget"


def score_slop(prompt: str) -> tuple[float, str]:
    low = prompt.lower()
    hits = sorted({t for t in SLOP if re.search(rf"\b{re.escape(t)}\b", low)})
    n = len(words(prompt))
    # Slop in the first 25 words is the expensive kind.
    head = " ".join(words(prompt)[:25]).lower()
    head_hits = [t for t in hits if re.search(rf"\b{re.escape(t)}\b", head)]
    score = 4.0 - 1.25 * len(hits) - 1.0 * len(head_hits)
    density = len(hits) / max(n, 1) * 100
    note = "clean" if not hits else f"slop: {', '.join(hits)} ({density:.1f}/100w)"
    if head_hits:
        note += f" | {len(head_hits)} in the first 25 words"
    return max(0.0, min(4.0, score)), note


def score_coverage(prompt: str, mode: str = "T2V") -> tuple[float, str]:
    preserving = mode.upper() in PRESERVING_MODES
    present, missing, kept = [], [], []
    for name, rx in (("camera", CAMERA), ("light", LIGHT), ("sound", SOUND), ("endpoint", ENDPOINT)):
        if rx.search(prompt):
            present.append(name)
        elif preserving and name in PRESERVE and PRESERVE[name].search(prompt):
            present.append(name)
            kept.append(name)
        else:
            missing.append(name)
    note = "all four addressed" if not missing else f"missing: {', '.join(missing)}"
    if kept:
        note += f" (addressed by preservation: {', '.join(kept)})"
    return len(present), note


def score_structure(prompt: str) -> tuple[float, str]:
    score, notes = 4.0, []
    if NEGATION.search(prompt):
        score -= 2.0
        notes.append("negation slop")
    # Tag salad: many comma fragments that contain no verb.
    frags = [f.strip() for f in prompt.split(",") if f.strip()]
    verbless = [
        f for f in frags
        if len(words(f)) <= 5
        and not re.search(r"\b\w+(?:s|ed|ing)\b", f)
    ]
    if len(frags) >= 6 and len(verbless) / len(frags) > 0.5:
        score -= 2.0
        notes.append(f"tag salad ({len(verbless)}/{len(frags)} verbless fragments)")
    sentences = [s for s in re.split(r"[.;]", prompt) if s.strip()]
    if len(sentences) < 2 and len(words(prompt)) > 55:
        score -= 1.0
        notes.append("single run-on clause")
    return max(0.0, score), ("shooting-brief prose" if not notes else " | ".join(notes))


def score_refs(prompt: str, mode: str) -> tuple[float, str] | tuple[None, str]:
    if mode.upper() not in REF_MODES:
        return None, "n/a (no reference assets)"
    tags = REF_TAG.findall(prompt)
    if not tags:
        if PROSE_BINDING.search(prompt):
            return 3.0, "bound to accepted footage in prose rather than an asset tag"
        return 0.0, "reference mode with no reference binding"
    # A role must be stated for the binding to be a contract, not a mention.
    has_role = re.search(
        r"\b(is the|controls?|supplies|preserves?|provides?|owns?|governs?|"
        r"as the|source clip|first frame|final frame|identity|do not|must not|ignore)\b",
        prompt, re.I)
    if not has_role:
        return 2.0, f"{len(tags)} tag(s) mentioned but no role contract"
    excl = re.search(r"\b(do not|must not|ignore|never|exclude|nothing else|only)\b", prompt, re.I)
    return (4.0, f"{len(tags)} tag(s), roles bound, transfer limited") if excl else \
           (3.0, f"{len(tags)} tag(s), roles bound, no exclusion stated")


def score_prompt(rec: dict) -> dict:
    p, mode = rec["prompt"], rec.get("mode", "T2V")
    dims: dict[str, tuple[float, str]] = {}
    dims["opening_authority"] = score_opening(p)
    dims["length_fit"] = score_length(p)
    dims["slop_free"] = score_slop(p)
    dims["coverage"] = score_coverage(p, mode)
    dims["structure"] = score_structure(p)
    ref = score_refs(p, mode)
    if ref[0] is not None:
        dims["ref_integrity"] = ref  # type: ignore[assignment]
    overall = statistics.mean(v[0] for v in dims.values())
    return {
        "id": rec["id"], "arm": rec["arm"], "mode": mode, "brief": rec["brief"],
        "words": len(words(p)),
        "dims": {k: {"score": round(v[0], 2), "note": v[1]} for k, v in dims.items()},
        "overall": round(overall, 3),
        "ref_note": ref[1],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", nargs="?", default="evals/prompt-architecture-stress.json")
    parser.add_argument("--out", help="write per-prompt scores to this JSON file")
    parser.add_argument(
        "--strict", action="store_true",
        help="exit non-zero if the skill_formula arm misses the eval-rubric release bar",
    )
    args = parser.parse_args()

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    results = [score_prompt(r) for r in corpus]
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    arms: dict[str, list[dict]] = {}
    for r in results:
        arms.setdefault(r["arm"], []).append(r)

    dim_names = ["opening_authority", "length_fit", "slop_free", "coverage", "structure", "ref_integrity"]
    print(f"Corpus: {len(results)} prompts across {len(arms)} arms\n")
    header = f"{'arm':<22}{'n':>4}{'overall':>9}" + "".join(f"{d[:9]:>11}" for d in dim_names)
    print(header)
    print("-" * len(header))
    for arm in sorted(arms, key=lambda a: -statistics.mean(x["overall"] for x in arms[a])):
        rs = arms[arm]
        row = f"{arm:<22}{len(rs):>4}{statistics.mean(x['overall'] for x in rs):>9.2f}"
        for d in dim_names:
            vals = [x["dims"][d]["score"] for x in rs if d in x["dims"]]
            row += f"{statistics.mean(vals):>11.2f}" if vals else f"{'-':>11}"
        print(row)

    print("\nRelease gate (eval-rubric.md: no dimension below 3, average >= 3.5)")
    for arm in sorted(arms):
        rs = arms[arm]
        avg = statistics.mean(x["overall"] for x in rs)
        weak = []
        for d in dim_names:
            vals = [x["dims"][d]["score"] for x in rs if d in x["dims"]]
            if vals and statistics.mean(vals) < 3.0:
                weak.append(f"{d}={statistics.mean(vals):.2f}")
        verdict = "PASS" if avg >= 3.5 and not weak else "FAIL"
        print(f"  {arm:<22} avg={avg:.2f}  {verdict}" + (f"  weak: {', '.join(weak)}" if weak else ""))

    print("\nPer-mode overall (skill_formula arm)")
    modes: dict[str, list[float]] = {}
    for r in results:
        if r["arm"] == "skill_formula":
            modes.setdefault(r["mode"], []).append(r["overall"])
    for m in sorted(modes, key=lambda m: statistics.mean(modes[m])):
        print(f"  {m:<8} n={len(modes[m]):<3} {statistics.mean(modes[m]):.2f}")

    worst = sorted((r for r in results if r["arm"] == "skill_formula"), key=lambda r: r["overall"])[:8]
    print("\nWeakest skill-formula prompts")
    for r in worst:
        bad = [f"{k}={v['score']} ({v['note']})" for k, v in r["dims"].items() if v["score"] < 3]
        print(f"  {r['id']:<8} {r['overall']:.2f}  {r['brief'][:44]:<44} {'; '.join(bad)[:90]}")

    if args.strict:
        doctrine = [r for r in results if r["arm"] == "skill_formula"]
        if not doctrine:
            print("\nNo skill_formula arm in this corpus.")
            return 1
        avg = statistics.mean(r["overall"] for r in doctrine)
        weak = [
            d for d in dim_names
            if (vals := [r["dims"][d]["score"] for r in doctrine if d in r["dims"]])
            and statistics.mean(vals) < 3.0
        ]
        if avg < 3.5 or weak:
            print(f"\nskill_formula misses the release bar: avg={avg:.2f}"
                  + (f", weak dimensions: {', '.join(weak)}" if weak else ""))
            return 1
        print(f"\nskill_formula holds the release bar (avg={avg:.2f}, no dimension below 3).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

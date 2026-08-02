#!/usr/bin/env python3
"""Stress-test deterministic prompt-architecture failure modes.

Scores three arms of the same 34 briefs against each other:

  naive_online      what a listicle or an untrained user writes
  quickstart_style  the shape the beginner-facing example taught before v6.6.x
                    fixed it - kept as a frozen regression arm, not a current doc
  skill_formula     seedance-prompt's Director Formula, followed literally

The point is the gap between arms. If the skill's doctrine is sound, the
skill_formula arm clears the release bar in references/eval-rubric.md and the
others do not - and if a beginner-facing example teaches a shape that misses
that bar, this is where it shows up rather than in user feedback.

Scores are mechanical and intentionally bounded. They catch structural,
brief-relevance, explicit contradiction, and repetition failures. They do not
judge creativity or originality. Comparative creative quality still requires
blinded model evaluation and native-language human review. Offline and
dependency-free, like every other check here.

    python scripts/prompt_architecture_stress.py            # score the shipped corpus
    python scripts/prompt_architecture_stress.py --strict   # fail if the doctrine arm regresses

Dimensions (0-4, matching references/eval-rubric.md's V6 scale):
  opening_authority  subject/action (or reference binding) in the lead clause
  length_fit         official 60-100 word band; skill's 40-110 fast-lane band
  slop_free          density of anti-slop-lexicon terms
  coverage           camera move / motivated light / sound / visible endpoint
  structure          prose shooting-brief vs comma tag-salad, negation slop
  ref_integrity      reference tags present and byte-exact for reference modes
  brief_traceability brief-specific material survives into the prompt
  coherence          explicit incompatible camera/light/sound/action stacks
  repetition         repeated-token, repeated-phrase, and padding resistance
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import statistics
from collections import Counter
from functools import lru_cache
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

DIM_NAMES = [
    "opening_authority",
    "length_fit",
    "slop_free",
    "coverage",
    "structure",
    "ref_integrity",
    "brief_traceability",
    "coherence",
    "repetition",
]

BOUNDARY = (
    "Boundary: this deterministic gate catches structural, brief-relevance, "
    "explicit contradiction, and repetition failures. It does not judge "
    "creativity or originality; comparative creative quality still requires "
    "blinded model evaluation and native-language human review."
)

TOKEN = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")
FUNCTION_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "beside", "between", "by",
    "for", "from", "has", "he", "her", "his", "in", "into", "is", "it",
    "its", "of", "on", "or", "she", "that", "the", "their", "them", "then",
    "there", "they", "this", "through", "to", "under", "while", "with",
}

# These words can make unrelated prompts look connected merely because both are
# production prompts. They cannot, by themselves, establish brief traceability.
PRODUCTION_GENERIC = {
    "audio", "blocking", "camera", "clip", "duration", "endpoint", "exist", "final",
    "frame", "grade", "image", "lens", "light", "mode", "motion", "new", "only",
    "original", "production", "prompt", "reference", "same", "scene", "shot", "sound",
    "source", "style", "timing", "video", "workflow",
}
TRACE_GENERIC = {
    "animate", "change", "character", "continue", "create", "make", "move",
    "person", "replace", "restyle", "sit", "stand", "stop", "subject", "thing",
    "turn", "use", "walk", "woman", "man", "child",
}

TOKEN_ALIASES = {
    "animated": "animate",
    "animation": "animate",
    "bike": "bicycle",
    "bicyclist": "bicycle",
    "colourway": "colour",
    "chang": "change",
    "clos": "close",
    "continu": "continue",
    "dancer": "dance",
    "dancing": "dance",
    "earthshine": "earth",
    "footfall": "foot",
    "fram": "frame",
    "dialogue": "speech",
    "line": "speech",
    "spoken": "speech",
    "land": "landscape",
    "terrain": "landscape",
    "letter": "letter_document",
    "paper": "letter_document",
    "sheet": "letter_document",
    "photo": "portrait_photo",
    "photograph": "portrait_photo",
    "photographed": "portrait_photo",
    "portrait": "portrait_photo",
    "shoot": "sprout",
    "shut": "close",
    "shutt": "close",
    "shoe": "sneaker",
    "sprout": "sprout",
    "seed": "sprout",
    "mov": "move",
    "driv": "drive",
    "preserv": "preserve",
    "receiv": "receive",
    "streetlamp": "street",
    "terminal": "airport",
    "us": "use",
}

DIRECT_SEQUENCE_BRIDGE = re.compile(
    r"^\s*(?:[,;:]|[-\u2013\u2014]{1,2})?\s*(?:and\s+)?"
    r"(?:(?:then|next|finally|followed by)|(?:before|after))\s+"
    r"(?:(?:the|a|an|near|absolute|complete|completely|slow|slowly)[-\s]*){0,2}$",
    re.I,
)
EVENT_SEQUENCE_BRIDGE = re.compile(
    r"^(?:\s*(?:[,;:]|[-\u2013\u2014]{1,2})?\s*"
    r"(?:until|once|while|as)\b.{1,240}"
    r"\b(?:then|next|finally)\b\s*(?:[,;:]|[-\u2013\u2014]{1,2})?\s*"
    r"|\s*(?:[,;:]|[-\u2013\u2014]{1,2})?\s*"
    r"(?:until|once)\b[^.!?;]{1,120}"
    r"(?:"
    r"[.!?]\s*(?:then\s+)?)"
    r"|\s*[.!?]\s*(?:after|once)\b[^.!?;]{1,120}[,;:]\s*)"
    r"(?:(?:the|a|an|near|absolute|complete|completely|slow|slowly)[-\s]*){0,2}$",
    re.I,
)
DIRECT_SIMULTANEOUS_BRIDGE = re.compile(
    r"^\s*(?:[.!?,;:]|[-\u2013\u2014]{1,2})?\s*(?:and\s+)?"
    r"(?:while|as|simultaneous(?:ly)?|at the same time|all the while|"
    r"meanwhile|together|at once|concurrent(?:ly)?(?:\s+with)?)\s+"
    r"(?:(?:the|a|an|near|absolute|complete|completely|slow|slowly)[-\s]*){0,2}$",
    re.I,
)
TRAILING_SIMULTANEOUS_CUE = re.compile(
    r"^\s*(?:[,;:]|[-\u2013\u2014]{1,2})?\s*"
    r"(?:simultaneous(?:ly)?|at the same time|all the while|meanwhile|"
    r"concurrent(?:ly)?|together|at once)\s*$",
    re.I,
)
NEGATED_PREFIX = re.compile(
    r"\b(no|not|never|without|do not|does not|must not|nothing from)\b[^.;,]{0,18}$",
    re.I,
)
SCOPED_EXCLUSION = re.compile(
    r"\b(do not|does not|must not|never|nothing from|ignore|exclude)\b",
    re.I,
)
NEGATION_RESET = re.compile(
    r"\b(but|however|instead|except)\b|"
    r"(?:[,:]\s*|\band\s+|\bthen\s+)(?:then\s+)?"
    r"(?:use\b(?!\s+of\b)|keep\b|preserve\b|retain\b|include\b|add\b|"
    r"make\b|light\b(?!\s+of\b)|illuminate\b)",
    re.I,
)
DOUBLE_NEGATED_EXCLUSION = re.compile(
    r"\b(?:do not|does not|must not|will not|should not|can(?:not| not)|never|"
    r"don['\u2019]t|doesn['\u2019]t|mustn['\u2019]t|won['\u2019]t|"
    r"shouldn['\u2019]t|can['\u2019]t)\s+(?:ignore|exclude)\b",
    re.I,
)

OPPOSITE_ACTIONS = {
    frozenset(pair)
    for pair in (
        ("open", "close"),
        ("enter", "exit"),
        ("raise", "lower"),
        ("start", "stop"),
        ("arrive", "depart"),
        ("approach", "retreat"),
    )
}
ACTION_MODIFIERS = {
    "abruptly", "carefully", "deliberately", "gently", "immediately",
    "now", "quietly", "quickly", "slowly", "suddenly",
}

CAMERA_FAMILIES = {
    # Camera conflicts must be conservative. Context-free verbs such as
    # ``orbits``, ``tilts``, ``tracks``, and ``zooms`` commonly describe the
    # subject, so they are not camera directives without a camera/shot actor or
    # an unambiguous movement phrase.
    "locked": re.compile(
        r"\b(?:(?:camera|shot|frame|framing)\s+"
        r"(?:(?:is|stays?|remains?|holds?)\s+)?(?:completely\s+)?"
        r"(?:locked(?:[- ]off)?|static)|(?:locked[- ]off|static)\s+"
        r"(?:camera|shot|frame|framing))\b",
        re.I,
    ),
    "orbit": re.compile(
        r"\b(?:(?:camera|shot)\s+(?:slowly\s+|then\s+|now\s+)?orbit(?:s|ing)?|"
        r"camera\b[^.;,]{0,48}\b(?:while|as|then)\s+it\s+(?:\w+\s+){0,2}orbits?|"
        r"camera\b[^.;,]{0,48}\b(?:while|as)\s+(?:slowly\s+)?orbiting|"
        r"orbiting\s+(?:camera|shot))\b",
        re.I,
    ),
    "push": re.compile(
        r"\b(?:(?:camera|shot)\s+(?:slowly\s+|then\s+|now\s+)?push(?:es|ing)?[- ]?in|"
        r"camera\b[^.;,]{0,48}\b(?:while|as|then)\s+it\s+(?:\w+\s+){0,2}push(?:es|ing)?[- ]?in|"
        r"doll(?:y|ies|ying)[- ]?in|push-in)\b",
        re.I,
    ),
    "pull": re.compile(
        r"\b(?:(?:camera|shot)\s+(?:slowly\s+|then\s+|now\s+)?pull(?:s|ing)?[- ]?(?:back|out)|"
        r"camera\b[^.;,]{0,48}\b(?:while|as|then)\s+it\s+(?:\w+\s+){0,2}pull(?:s|ing)?[- ]?(?:back|out)|"
        r"doll(?:y|ies|ying)[- ]?out|pull-(?:back|out))\b",
        re.I,
    ),
    "track": re.compile(
        r"\b(?:(?:camera|shot)\s+(?:slowly\s+|then\s+|now\s+)?(?:track(?:s|ing)?|follows?)|"
        r"camera\b[^.;,]{0,48}\b(?:while|as|then)\s+it\s+(?:\w+\s+){0,2}(?:track(?:s|ing)?|follows?)|"
        r"tracking\s+(?:shot|left|right|forward|back|around))\b",
        re.I,
    ),
    "pan": re.compile(
        r"\b(?:(?:camera|shot)\s+(?:slowly\s+|then\s+|now\s+)?pan(?:s|ning)?|"
        r"pan(?:s|ning)?\s+(?:left|right|across|to)|whip pan)\b",
        re.I,
    ),
    "tilt": re.compile(
        r"\b(?:(?:camera|shot)\s+(?:slowly\s+|then\s+|now\s+)?tilt(?:s|ing)?|"
        r"tilt(?:s|ing)?\s+(?:up|down|left|right))\b",
        re.I,
    ),
    "crane": re.compile(
        r"\b(?:(?:camera|shot)\s+(?:slowly\s+|then\s+|now\s+)?(?:crane(?:s|ing)?|jibs?)|"
        r"(?:crane|jib)(?:s|bing)?\s+(?:up|down|over|back)|crane shot)\b",
        re.I,
    ),
    "zoom": re.compile(
        r"\b(?:(?:camera|shot)\s+(?:slowly\s+|then\s+|now\s+)?zoom(?:s|ing)?|"
        r"zoom(?:s|ing)?\s+(?:in|out))\b",
        re.I,
    ),
}

LIGHT_SOURCE_FAMILIES = {
    "sun": re.compile(r"\b(sun|sunlight|daylight|noon)\b", re.I),
    "moon": re.compile(r"\b(moon|moonlight|earthlight|earthshine)\b", re.I),
    "neon": re.compile(r"\bneon\b", re.I),
    "fire": re.compile(r"\b(fire|firelight|forge|flame)\b", re.I),
    "candle": re.compile(r"\b(candle|candlelight|lantern)\b", re.I),
    "fluorescent": re.compile(r"\b(fluorescent|overhead tubes?)\b", re.I),
    "lamp": re.compile(r"\b(lamp|practical|bare bulb|work light)\b", re.I),
    "window": re.compile(r"\b(window light|skylight|window shaft)\b", re.I),
    "softbox": re.compile(r"\bsoftbox(?:es)?\b", re.I),
    "street": re.compile(r"\b(streetlight|streetlamp|sodium)\b", re.I),
}

SOUND_LAYER_FAMILIES = {
    "dialogue": re.compile(r"\b(dialogue|voice|spoken line|says?)\b", re.I),
    "music": re.compile(r"\b(music|score|synth|song)\b", re.I),
    "ambience": re.compile(r"\b(ambience|ambient|room tone|reverb)\b", re.I),
    "weather": re.compile(r"\b(rain|wind|thunder)\b", re.I),
    "body": re.compile(r"\b(footsteps?|footfalls?|breath(?:ing)?|heartbeat)\b", re.I),
    "mechanical": re.compile(r"\b(engine|hum|rumble|buzz|whirr|clatter|scrape)\b", re.I),
}
SILENCE = re.compile(r"\b(absolute silence|silence|no sound)\b", re.I)
UNCHANGED_AUDIO = re.compile(r"\b(keep|preserve)\b[^.;]{0,35}\b(audio|sound)\b[^.;]{0,20}\b(unchanged|same)\b", re.I)
ADDED_AUDIO = re.compile(r"\b(add|added|layer|introduce)\b[^.;]{0,25}\b(music|dialogue|voice|sfx|sound)\b", re.I)
STILL_ACTION = re.compile(r"\b(remains? (?:completely )?still|goes? still|freezes?|stops? moving)\b", re.I)
CONTINUING_ACTION = re.compile(
    r"\b(keeps? (?:walking|running|moving)|continu(?:es?|ing) to (?:walk|run|move))\b",
    re.I,
)


def words(text: str) -> list[str]:
    return [w for w in re.split(r"\s+", text.strip()) if w]


def canonical_token(token: str) -> str:
    token = token.lower().replace("’", "'").strip("'")
    if token.endswith("'s"):
        token = token[:-2]
    if token in TOKEN_ALIASES:
        return TOKEN_ALIASES[token]
    if len(token) > 5 and token.endswith("ies"):
        token = token[:-3] + "y"
    elif len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
        if len(token) > 3 and token[-1] == token[-2]:
            token = token[:-1]
    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    return TOKEN_ALIASES.get(token, token)


def lexical_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in TOKEN.finditer(text):
        for part in re.split(r"[-–—]", match.group(0)):
            if part:
                tokens.append(canonical_token(part))
    return tokens


@lru_cache(maxsize=4096)
def trace_terms(text: str) -> frozenset[str]:
    return frozenset({
        token
        for token in lexical_tokens(text)
        if len(token) > 2
        and token not in FUNCTION_WORDS
        and token not in PRODUCTION_GENERIC
        and token not in TRACE_GENERIC
    })


def score_brief_traceability(brief: str, prompt: str) -> tuple[float, str]:
    """Require brief-specific material, not shared production vocabulary."""
    brief_terms = trace_terms(brief)
    prompt_terms = trace_terms(prompt)
    if not brief_terms:
        return 0.0, "brief has no usable non-generic material to trace"
    matched = sorted(brief_terms & prompt_terms)
    if len(matched) >= 2:
        return 4.0, f"brief-specific terms carried through: {', '.join(matched)}"
    if len(matched) == 1 and len(brief_terms) <= 3:
        return 3.0, f"one brief-specific anchor carried through: {matched[0]}"
    if matched:
        missing = sorted(brief_terms - prompt_terms)
        return 2.0, (
            f"only one of {len(brief_terms)} brief-specific terms survives: {matched[0]}; "
            f"missing: {', '.join(missing[:5])}"
        )
    return 0.0, f"no brief-specific material survives; expected one of: {', '.join(sorted(brief_terms)[:6])}"


def match_is_negated(text: str, start: int) -> bool:
    short_prefix = text[max(0, start - 36):start]
    short_match = NEGATED_PREFIX.search(short_prefix)
    if short_match:
        global_short_start = max(0, start - 36) + short_match.start()
        double_negated = any(
            match.start() <= short_match.start() < match.end()
            for match in DOUBLE_NEGATED_EXCLUSION.finditer(short_prefix)
        )
        if (
            not double_negated
            and not position_is_quoted(text, global_short_start)
            and not NEGATION_RESET.search(short_prefix[short_match.start():])
        ):
            return True

    # Reference exclusions often enumerate several protected attributes before
    # naming the light or sound source. Keep the scope inside one clause, and
    # let an explicit contrast reset it so "ignore identity, but keep neon"
    # still records neon as positive evidence.
    clause_start = max(
        text.rfind(".", 0, start),
        text.rfind(";", 0, start),
        text.rfind("\n", 0, start),
    ) + 1
    clause = text[clause_start:start]
    exclusions = [
        match
        for match in SCOPED_EXCLUSION.finditer(clause)
        if not position_is_quoted(text, clause_start + match.start())
    ]
    if not exclusions:
        return False
    double_exclusions = list(DOUBLE_NEGATED_EXCLUSION.finditer(clause))
    if any(
        match.start() <= exclusions[-1].start() < match.end()
        for match in double_exclusions
    ):
        return False
    after_exclusion = clause[exclusions[-1].end():]
    return NEGATION_RESET.search(after_exclusion) is None


def position_is_quoted(text: str, position: int) -> bool:
    """Return whether a control word is inside simple dialogue quotation marks."""
    prefix = text[:position]
    straight_quotes = len(re.findall(r'(?<!\\)"', prefix))
    straight_quote_open = (
        straight_quotes % 2 == 1
        and re.search(r'(?<!\\)"', text[position:]) is not None
    )

    single_quote_open: int | None = None
    inside_single_quote = False
    for index, character in enumerate(text):
        if character != "'":
            continue
        previous = text[index - 1] if index > 0 else " "
        following = text[index + 1] if index + 1 < len(text) else " "
        if previous.isalnum() and following.isalnum():
            continue
        if single_quote_open is None:
            # Plural possessives (directors') and measurements (6') resemble
            # closing marks, not dialogue openers.
            if previous.isalnum() or following.isspace():
                continue
            single_quote_open = index
            continue
        if previous.isspace():
            continue
        if single_quote_open < position < index:
            inside_single_quote = True
            break
        single_quote_open = None

    curly_quote_open = (
        prefix.rfind("\u201c") > prefix.rfind("\u201d")
        and text.find("\u201d", position) != -1
    )
    curly_single_open = (
        prefix.rfind("\u2018") > prefix.rfind("\u2019")
        and text.find("\u2019", position) != -1
    )
    return (
        straight_quote_open
        or inside_single_quote
        or curly_quote_open
        or curly_single_open
    )


def positive_families(text: str, families: dict[str, re.Pattern[str]]) -> set[str]:
    present: set[str] = set()
    for name, pattern in families.items():
        if any(not match_is_negated(text, match.start()) for match in pattern.finditer(text)):
            present.add(name)
    return present


def positive_positions(
    text: str,
    families: dict[str, re.Pattern[str]],
) -> list[tuple[int, int]]:
    return [
        (match.start(), match.end())
        for pattern in families.values()
        for match in pattern.finditer(text)
        if not match_is_negated(text, match.start())
    ]


def named_positive_positions(
    text: str,
    families: dict[str, re.Pattern[str]],
    names: set[str],
) -> list[tuple[int, int]]:
    return positive_positions(
        text,
        {name: pattern for name, pattern in families.items() if name in names},
    )


def directives_are_sequenced(
    text: str,
    positions: list[tuple[int, int]],
) -> bool:
    if len(positions) < 2:
        return False
    ordered = sorted(set(positions))
    # A simultaneity qualifier can follow the final directive, outside its
    # regex match. Inspect only the remainder of its local clause so an
    # unrelated cue in a later sentence cannot poison a valid transition.
    local_end_match = re.search(r"[.;!?\n]", text[ordered[-1][1]:])
    local_end = (
        ordered[-1][1] + local_end_match.start()
        if local_end_match
        else len(text)
    )
    if TRAILING_SIMULTANEOUS_CUE.fullmatch(text[ordered[-1][1]:local_end]):
        return False
    adjacent = list(zip(ordered, ordered[1:]))
    if any(
        DIRECT_SIMULTANEOUS_BRIDGE.fullmatch(text[left_end:right_start])
        for (_, left_end), (right_start, _) in adjacent
    ):
        return False
    for (left_start, left_end), (right_start, _) in adjacent:
        bridge = text[left_end:right_start]
        if DIRECT_SEQUENCE_BRIDGE.fullmatch(bridge):
            return True
        # Permit an explicit event boundary only when it culminates in a cue
        # directly attached to the later directive. An unrelated "then/before"
        # elsewhere between the directives is not enough.
        if EVENT_SEQUENCE_BRIDGE.fullmatch(bridge):
            return True

        prefix = text[max(0, left_start - 32):left_start]
        if re.search(r"\bfrom\b\s*$", prefix, re.I) and re.fullmatch(
            r"\s*to\s*", bridge, re.I
        ):
            return True
    return False


def contradiction_findings(prompt: str) -> list[str]:
    """Find explicit, local incompatibilities without interpreting creative intent."""
    findings: list[str] = []
    sentences = [part.strip() for part in re.split(r"(?<=[.!?;])\s+", prompt) if part.strip()]

    for sentence in sentences:
        camera = positive_families(sentence, CAMERA_FAMILIES)
        dynamic = camera - {"locked"}
        camera_sequenced = directives_are_sequenced(
            sentence,
            positive_positions(sentence, CAMERA_FAMILIES),
        )
        push_pull_sequenced = directives_are_sequenced(
            sentence,
            named_positive_positions(
                sentence, CAMERA_FAMILIES, {"push", "pull"}
            ),
        )
        if "locked" in camera and dynamic and not camera_sequenced:
            findings.append(
                "camera: locked/static framing conflicts with simultaneous "
                + ", ".join(sorted(dynamic))
            )
        elif len(dynamic) >= 3 and not camera_sequenced:
            findings.append(
                "camera: three or more simultaneous move families are stacked: "
                + ", ".join(sorted(dynamic))
            )
        elif {"push", "pull"}.issubset(dynamic) and not push_pull_sequenced:
            findings.append("camera: simultaneous push-in and pull-out directives")

        light_sources = positive_families(sentence, LIGHT_SOURCE_FAMILIES)
        light_sequenced = directives_are_sequenced(
            sentence,
            positive_positions(sentence, LIGHT_SOURCE_FAMILIES),
        )
        exclusive_light = re.search(
            r"\b(single|sole|only)\b[^.;]{0,80}\b(light|lit|sources?)\b",
            sentence,
            re.I,
        )
        if len(light_sources) >= 2 and exclusive_light and not light_sequenced:
            findings.append(
                "light: an exclusive source claim names multiple sources: "
                + ", ".join(sorted(light_sources))
            )
        elif len(light_sources) >= 3 and not light_sequenced:
            findings.append(
                "light: three or more unphased source families are stacked: "
                + ", ".join(sorted(light_sources))
            )

        sound_layers = positive_families(sentence, SOUND_LAYER_FAMILIES)
        has_silence = bool(SILENCE.search(sentence))
        sound_positions = positive_positions(sentence, SOUND_LAYER_FAMILIES)
        sound_positions.extend((match.start(), match.end()) for match in SILENCE.finditer(sentence))
        sound_sequenced = directives_are_sequenced(sentence, sound_positions)
        if has_silence and sound_layers and not sound_sequenced:
            findings.append(
                "sound: silence conflicts with simultaneous layers: "
                + ", ".join(sorted(sound_layers))
            )
        elif len(sound_layers) >= 5 and not sound_sequenced:
            findings.append(
                "sound: five or more unphased layers are stacked: "
                + ", ".join(sorted(sound_layers))
            )

        action_positions = [
            (match.start(), match.end())
            for pattern in (STILL_ACTION, CONTINUING_ACTION)
            for match in pattern.finditer(sentence)
        ]
        action_sequenced = directives_are_sequenced(sentence, action_positions)
        if STILL_ACTION.search(sentence) and CONTINUING_ACTION.search(sentence) and not action_sequenced:
            findings.append("action: stillness conflicts with continuing locomotion")

    # Punctuation must not turn simultaneous incompatible directives into a
    # false negative. Re-run the hard conflicts across the whole prompt while
    # still honoring explicit phase cues between the directives.
    global_camera = positive_families(prompt, CAMERA_FAMILIES)
    global_dynamic = global_camera - {"locked"}
    global_camera_sequenced = directives_are_sequenced(
        prompt, positive_positions(prompt, CAMERA_FAMILIES)
    )
    global_push_pull_sequenced = directives_are_sequenced(
        prompt,
        named_positive_positions(prompt, CAMERA_FAMILIES, {"push", "pull"}),
    )
    if (
        "locked" in global_camera
        and global_dynamic
        and not global_camera_sequenced
        and not any(finding.startswith("camera:") for finding in findings)
    ):
        findings.append(
            "camera: locked/static framing conflicts with unphased "
            + ", ".join(sorted(global_dynamic))
        )
    elif (
        len(global_dynamic) >= 3
        and not global_camera_sequenced
        and not any(finding.startswith("camera:") for finding in findings)
    ):
        findings.append(
            "camera: three or more unphased move families are stacked: "
            + ", ".join(sorted(global_dynamic))
        )
    elif (
        {"push", "pull"}.issubset(global_dynamic)
        and not global_push_pull_sequenced
        and not any(finding.startswith("camera:") for finding in findings)
    ):
        findings.append("camera: unphased push-in and pull-out directives")

    global_lights = positive_families(prompt, LIGHT_SOURCE_FAMILIES)
    global_light_positions = positive_positions(prompt, LIGHT_SOURCE_FAMILIES)
    global_exclusive_light = re.search(
        r"\b(single|sole|only)\b[^.;]{0,80}\b(light|lit|sources?)\b",
        prompt,
        re.I,
    )
    if (
        len(global_lights) >= 2
        and global_exclusive_light
        and not directives_are_sequenced(prompt, global_light_positions)
        and not any(finding.startswith("light:") for finding in findings)
    ):
        findings.append(
            "light: an exclusive source claim conflicts with another unphased source: "
            + ", ".join(sorted(global_lights))
        )

    global_sound = positive_families(prompt, SOUND_LAYER_FAMILIES)
    global_sound_positions = positive_positions(prompt, SOUND_LAYER_FAMILIES)
    global_sound_positions.extend((match.start(), match.end()) for match in SILENCE.finditer(prompt))
    if (
        SILENCE.search(prompt)
        and global_sound
        and not directives_are_sequenced(prompt, global_sound_positions)
        and not any(finding.startswith("sound:") for finding in findings)
    ):
        findings.append(
            "sound: silence conflicts with unphased layers: "
            + ", ".join(sorted(global_sound))
        )

    global_action_positions = [
        (match.start(), match.end())
        for pattern in (STILL_ACTION, CONTINUING_ACTION)
        for match in pattern.finditer(prompt)
    ]
    if (
        STILL_ACTION.search(prompt)
        and CONTINUING_ACTION.search(prompt)
        and not directives_are_sequenced(prompt, global_action_positions)
        and not any(finding.startswith("action:") for finding in findings)
    ):
        findings.append("action: stillness conflicts with unphased continuing locomotion")

    added_audio = any(
        not match_is_negated(prompt, match.start())
        for match in ADDED_AUDIO.finditer(prompt)
    )
    if UNCHANGED_AUDIO.search(prompt) and added_audio:
        findings.append("sound: preserve-source-audio and add-new-audio directives conflict")
    return list(dict.fromkeys(findings))


def score_coherence(prompt: str) -> tuple[float, str]:
    findings = contradiction_findings(prompt)
    if not findings:
        return 4.0, "no explicit incompatible directive stacks"
    score = 2.0 if len(findings) == 1 else 0.0
    return score, " | ".join(findings)


def repetition_findings(prompt: str) -> list[str]:
    all_tokens = lexical_tokens(prompt)
    content = [token for token in all_tokens if token not in FUNCTION_WORDS]
    if not content:
        return ["no lexical content"]

    findings: list[str] = []
    counts = Counter(content)
    dominant, frequency = counts.most_common(1)[0]
    if frequency >= 6 and frequency / len(content) >= 0.08:
        findings.append(
            f"dominant token repeated {frequency} times ({dominant})"
        )

    if len(content) >= 35:
        diversity = len(set(content)) / len(content)
        if diversity < 0.55:
            findings.append(f"low lexical diversity ({diversity:.2f})")

    if len(all_tokens) >= 6:
        trigrams = Counter(tuple(all_tokens[index:index + 3]) for index in range(len(all_tokens) - 2))
        repeated = [(gram, count) for gram, count in trigrams.items() if count >= 3]
        if repeated:
            gram, count = max(repeated, key=lambda item: item[1])
            findings.append(f"repeated phrase {count} times ({' '.join(gram)})")

    sentence_keys = [
        " ".join(lexical_tokens(sentence))
        for sentence in re.split(r"[.!?]+", prompt)
        if len(lexical_tokens(sentence)) >= 4
    ]
    repeated_sentences = [key for key, count in Counter(sentence_keys).items() if count >= 2]
    if repeated_sentences:
        findings.append("repeated sentence or clause")
    return findings


def score_repetition(prompt: str) -> tuple[float, str]:
    findings = repetition_findings(prompt)
    if not findings:
        return 4.0, "no padding or repeated-token pattern"
    return 2.0, " | ".join(findings)


@lru_cache(maxsize=4096)
def normalized_prompt(text: str) -> str:
    return " ".join(lexical_tokens(text))


@lru_cache(maxsize=8192)
def prompt_similarity(left: str, right: str) -> float:
    a, b = normalized_prompt(left), normalized_prompt(right)
    if a == b:
        return 1.0
    sequence = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    left_counts = Counter(a.split())
    right_counts = Counter(b.split())
    vocabulary = left_counts.keys() | right_counts.keys()
    multiset_union = sum(max(left_counts[token], right_counts[token]) for token in vocabulary)
    multiset_intersection = sum(min(left_counts[token], right_counts[token]) for token in vocabulary)
    bag_similarity = multiset_intersection / multiset_union if multiset_union else 1.0
    return max(sequence, bag_similarity)


@lru_cache(maxsize=8192)
def opposite_action_mutation(left: str, right: str) -> bool:
    """Catch a reused prompt skeleton hidden by one antithetical verb swap."""
    left_counts = Counter(lexical_tokens(left))
    right_counts = Counter(lexical_tokens(right))
    left_only = list((left_counts - right_counts).elements())
    right_only = list((right_counts - left_counts).elements())
    opposite_pair: tuple[str, str] | None = None
    for left_token in set(left_only):
        for right_token in set(right_only):
            if frozenset((left_token, right_token)) in OPPOSITE_ACTIONS:
                opposite_pair = (left_token, right_token)
                break
        if opposite_pair:
            break
    if opposite_pair is None:
        return False
    left_only.remove(opposite_pair[0])
    right_only.remove(opposite_pair[1])
    residual = left_only + right_only
    if any(
        token not in ACTION_MODIFIERS
        and token not in FUNCTION_WORDS
        and not token.endswith("ly")
        for token in residual
    ):
        return False
    shared_content = {
        token
        for token in (left_counts.keys() & right_counts.keys())
        if token not in FUNCTION_WORDS
    }
    return len(shared_content) >= 2


@lru_cache(maxsize=8192)
def materially_different_briefs(left: str, right: str) -> bool:
    if normalized_prompt(left) == normalized_prompt(right):
        return False
    if opposite_action_mutation(left, right):
        return True
    left_terms = trace_terms(left) or set(lexical_tokens(left))
    right_terms = trace_terms(right) or set(lexical_tokens(right))
    union = left_terms | right_terms
    similarity = len(left_terms & right_terms) / len(union) if union else 1.0
    return similarity < 0.6


def corpus_duplicate_findings(records: list[dict], arm: str = "skill_formula") -> list[str]:
    candidates = [record for record in records if record.get("arm") == arm]
    findings: list[str] = []
    exact_groups: dict[str, list[dict]] = {}
    for record in candidates:
        exact_groups.setdefault(normalized_prompt(record["prompt"]), []).append(record)

    exact_pairs: set[frozenset[str]] = set()
    for group in exact_groups.values():
        if len(group) < 2:
            continue
        materially_different = any(
            materially_different_briefs(left["brief"], right["brief"])
            for index, left in enumerate(group)
            for right in group[index + 1:]
        )
        if materially_different:
            ids = ", ".join(record["id"] for record in group)
            findings.append(
                f"cross-case duplicate prompt across materially different briefs: {ids}"
            )
            for index, left in enumerate(group):
                for right in group[index + 1:]:
                    exact_pairs.add(frozenset((left["id"], right["id"])))

    for index, left in enumerate(candidates):
        for right in candidates[index + 1:]:
            pair = frozenset((left["id"], right["id"]))
            if pair in exact_pairs or not materially_different_briefs(left["brief"], right["brief"]):
                continue
            similarity = prompt_similarity(left["prompt"], right["prompt"])
            opposite_mutation = opposite_action_mutation(
                left["prompt"], right["prompt"]
            )
            if similarity >= 0.92 or opposite_mutation:
                mutation_note = "; opposite-action skeleton" if opposite_mutation else ""
                findings.append(
                    f"cross-case near-duplicate prompt ({similarity:.2f}{mutation_note}) "
                    "across materially "
                    f"different briefs: {left['id']}, {right['id']}"
                )
    return findings


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
    brief = rec.get("brief", "")
    dims: dict[str, tuple[float, str]] = {}
    dims["opening_authority"] = score_opening(p)
    dims["length_fit"] = score_length(p)
    dims["slop_free"] = score_slop(p)
    dims["coverage"] = score_coverage(p, mode)
    dims["structure"] = score_structure(p)
    ref = score_refs(p, mode)
    if ref[0] is not None:
        dims["ref_integrity"] = ref  # type: ignore[assignment]
    dims["brief_traceability"] = score_brief_traceability(brief, p)
    dims["coherence"] = score_coherence(p)
    dims["repetition"] = score_repetition(p)
    overall = statistics.mean(v[0] for v in dims.values())
    return {
        "id": rec["id"], "arm": rec["arm"], "mode": mode, "brief": brief,
        "words": len(words(p)),
        "dims": {k: {"score": round(v[0], 2), "note": v[1]} for k, v in dims.items()},
        "overall": round(overall, 3),
        "ref_note": ref[1],
    }


def case_floor_findings(results: list[dict], arm: str = "skill_formula") -> list[str]:
    findings: list[str] = []
    for result in results:
        if result["arm"] != arm:
            continue
        if result["overall"] < 3.0:
            findings.append(f"{result['id']}: overall={result['overall']:.2f} (<3.00)")
        for dimension, value in result["dims"].items():
            if value["score"] < 3.0:
                findings.append(
                    f"{result['id']}: {dimension}={value['score']:.2f} (<3.00) - "
                    f"{value['note']}"
                )
    return findings


def arm_gate_findings(records: list[dict], results: list[dict], arm: str) -> list[str]:
    arm_results = [result for result in results if result["arm"] == arm]
    if not arm_results:
        return [f"no {arm} arm in this corpus"]
    findings = case_floor_findings(results, arm)
    average = statistics.mean(result["overall"] for result in arm_results)
    if average < 3.5:
        findings.append(f"{arm}: arm average={average:.2f} (<3.50)")
    if arm == "skill_formula":
        findings.extend(corpus_duplicate_findings(records, arm))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", nargs="?", default="evals/prompt-architecture-stress.json")
    parser.add_argument("--out", help="write per-prompt scores to this JSON file")
    parser.add_argument(
        "--strict", action="store_true",
        help=(
            "exit non-zero if any skill_formula case/dimension is below 3, the arm "
            "average is below 3.5, or materially different briefs reuse a prompt"
        ),
    )
    args = parser.parse_args()

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    results = [score_prompt(r) for r in corpus]
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    arms: dict[str, list[dict]] = {}
    for r in results:
        arms.setdefault(r["arm"], []).append(r)

    dim_names = DIM_NAMES
    print(f"Corpus: {len(results)} prompts across {len(arms)} arms\n")
    header = f"{'arm':<22}{'n':>4}{'overall':>9}" + "".join(f"{d[:11]:>13}" for d in dim_names)
    print(header)
    print("-" * len(header))
    for arm in sorted(arms, key=lambda a: -statistics.mean(x["overall"] for x in arms[a])):
        rs = arms[arm]
        row = f"{arm:<22}{len(rs):>4}{statistics.mean(x['overall'] for x in rs):>9.2f}"
        for d in dim_names:
            vals = [x["dims"][d]["score"] for x in rs if d in x["dims"]]
            row += f"{statistics.mean(vals):>13.2f}" if vals else f"{'-':>13}"
        print(row)

    print("\nRelease gate (every case and applicable dimension >= 3; arm average >= 3.5;")
    print("no cross-case duplicate/near-duplicate prompts for materially different briefs)")
    gate_findings = {
        arm: arm_gate_findings(corpus, results, arm)
        for arm in arms
    }
    for arm in sorted(arms):
        rs = arms[arm]
        avg = statistics.mean(x["overall"] for x in rs)
        findings = gate_findings[arm]
        verdict = "PASS" if not findings else "FAIL"
        suffix = f"  findings={len(findings)}" if findings else ""
        print(f"  {arm:<22} avg={avg:.2f}  {verdict}{suffix}")

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
        strict_findings = gate_findings.get(
            "skill_formula",
            ["no skill_formula arm in this corpus"],
        )
        if strict_findings:
            print("\nskill_formula strict gate failed:")
            for finding in strict_findings:
                print(f"- {finding}")
            print(f"\n{BOUNDARY}")
            return 1
        doctrine = [r for r in results if r["arm"] == "skill_formula"]
        avg = statistics.mean(r["overall"] for r in doctrine)
        print(f"\nskill_formula holds the release bar (avg={avg:.2f}, no dimension below 3).")
    print(f"\n{BOUNDARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

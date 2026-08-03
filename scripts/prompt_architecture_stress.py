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
    "arriv": "arrive",
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
    "notic": "notice",
    "driv": "drive",
    "preserv": "preserve",
    "rais": "raise",
    "receiv": "receive",
    "streetlamp": "street",
    "stopp": "stop",
    "terminal": "airport",
    "us": "use",
}

# A terse production brief may express the same contract as its prompt without
# sharing exact words. Extract only paired, bounded decisions; generic craft
# vocabulary still cannot establish traceability on its own.
COUNT_WORDS = {
    word: number
    for number, word in enumerate(
        "one two three four five six seven eight nine ten eleven twelve".split(),
        start=1,
    )
}
COUNTED_SHOT_REQUEST = re.compile(
    r"\b(?P<count>\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)[-\s]+"
    r"(?:cuts?|shots?|panels?)\b",
    re.I,
)
NUMBERED_SHOT_MARKER = re.compile(r"\b(?:shot|cut|panel)\s*(?P<count>\d+)\b", re.I)
ANIMATION_CONTRACT = re.compile(
    r"\b(?:animation boards?|storyboards?|2d|two[- ]dimensional|animat\w*)\b",
    re.I,
)
FROM_TO_CONTRACT = re.compile(r"\bfrom\b[^.!?]{0,100}\bto\b", re.I)
START_ENDPOINT = re.compile(
    r"\b(?:first frame|initial state|start(?:ing)? state)\b",
    re.I,
)
END_ENDPOINT = re.compile(
    r"\b(?:final (?:frame|visual target|state)|last frame|end(?:ing)? state|endpoint)\b",
    re.I,
)
TRANSITION_CONTRACT = re.compile(
    r"\b(?:move|state|transition|transform\w*|morph\w*)\b",
    re.I,
)
LIGHTING_EDIT_CONTRACT = re.compile(
    r"\b(?:fix|change|adjust|correct|modify|relight|re-light)\b[^.!?]{0,60}"
    r"\b(?:light|lighting|exposure|grade)\b",
    re.I,
)
SOURCE_PRESERVATION_CONTRACT = re.compile(
    r"\botherwise\s+(?:good|approved|acceptable|correct|finished)\b|"
    r"\b(?:keep|preserve|leave)\b[^.!?]{0,80}"
    r"\b(?:rest|everything|other|unchanged|same|existing)\b|"
    r"\bchange\s+only\b|\bonly\s+the\s+(?:light|lighting|exposure|grade)\b",
    re.I,
)

# Format words may prove a shot/animation contract, but they are not evidence
# that the requested subject survived. Keep this deliberately small and derive
# most entries from the actual matched contract spans instead of maintaining a
# fixture-specific noun list.
TARGET_CONTROL_TERMS = {
    "another", "brief", "either", "fix", "good", "known", "one", "otherwise",
    "short", "sequence", "state", "without",
}
PRODUCTION_TARGET_INTRO = re.compile(
    r"\b(?P<production>animation|take|depiction|portrait|video|clip|shot|"
    r"sequence|storyboard|render|image|frame)\s+(?:of|about)\s+",
    re.I,
)
DEPICTION_TARGET_INTRO = re.compile(
    r"\b(?P<depiction>featuring|depicting|showing|starring)\s+",
    re.I,
)
TARGET_STRONG_BOUNDARY = re.compile(r"[.;!?。！？；\r\n]+")
TARGET_INLINE_BOUNDARY = re.compile(r"[,.;!?。！？，；\r\n]")
TARGET_ASSET_MARKER = re.compile(
    r"@(?:image|video|audio)\s*\d+|"
    r"\b(?:asset|input|provided|reference|source|uploaded)\b",
    re.I,
)
TARGET_OUTPUT_REQUEST = re.compile(
    r"\b(?:animate|build|compose|create|deliver|depict|draft|generate|make|"
    r"produce|render|require(?:d|s)?|request(?:ed|s)?)\b",
    re.I,
)
TARGET_OUTPUT_COORDINATION = re.compile(
    r"(?:\b(?:and|plus)|,)\s+(?:a|an|another|the)?\s*$|"
    r"\b(?:animate|build|compose|create|deliver|depict|draft|generate|make|"
    r"produce|render)\b(?:\s+(?:a|an|another|the|[\w-]+)){0,5}\s*$",
    re.I,
)
TARGET_PHRASE_BREAKS = {
    "after", "as", "at", "before", "during", "for", "in", "inside",
    "instead", "near", "on", "outside", "rather", "that", "than",
    "under", "versus", "vs", "when", "where", "which", "while", "who",
    "with",
}
TARGET_ALTERNATIVE = "or"
MAX_EXPLICIT_TARGET_REQUIREMENTS = 8
TARGET_IDENTITY_MARKERS = {"call", "nam"}
TARGET_PURPOSE_VERBS = {
    "advertise", "demonstrate", "encourage", "explain", "promote", "showcase",
    "support", "teach",
}
TARGET_ACTION_BREAKS = {
    "arrive", "carry", "close", "cross", "depart", "drag", "drive", "enter",
    "exit", "float", "hang", "hold", "inspect", "kneel", "lean", "lift",
    "look", "lower", "move", "notice", "open", "play", "pour", "protect",
    "push", "raise", "reach", "read", "receive", "rest", "run", "scrub",
    "sit", "slide", "stand", "step", "turn", "wait", "walk", "wear",
}

PHASE_ORDINAL = (
    r"(?:next|following|first|second|third|fourth|fifth|sixth|seventh|"
    r"eighth|ninth|tenth|\d+)"
)
PHASE_NUMBER = (
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)"
)
PHASE_NOUN = r"(?:beat|moment|phase|scene|shot|take)"
PHASE_SEPARATOR = (
    r"(?:\s*[.!?。！？，,;:；：]\s*|\s*[-\u2013\u2014]{1,2}\s*|\s+)"
)
DIRECT_SEQUENCE_BRIDGE = re.compile(
    r"^\s*(?:[.!?。！？，,;:；：]|[-\u2013\u2014]{1,2})?\s*(?:and\s+)?"
    r"(?:"
    r"(?:(?:then|next|finally|followed by)|(?:before|after))"
    + PHASE_SEPARATOR
    + r"|(?:in|on)\s+(?:the\s+)?"
    + PHASE_ORDINAL
    + r"\s+"
    + PHASE_NOUN
    + PHASE_SEPARATOR
    + r"|(?:"
    + PHASE_ORDINAL
    + r"\s+"
    + PHASE_NOUN
    + r"|"
    + PHASE_NOUN
    + r"\s+"
    + PHASE_NUMBER
    + r")"
    + PHASE_SEPARATOR
    + r"|cut(?:\s+to)?"
    + PHASE_SEPARATOR
    + r")"
    r"(?:(?:the|a|an|near|absolute|complete|completely|slow|slowly)[-\s]*){0,2}$",
    re.I,
)
EVENT_SEQUENCE_BRIDGE = re.compile(
    r"^(?:\s*(?:[,;:，；：]|[-\u2013\u2014]{1,2})?\s*"
    r"(?:until|once|while|as)\b.{1,240}"
    r"\b(?:then|next|finally)\b\s*(?:[,;:，；：]|[-\u2013\u2014]{1,2})?\s*"
    r"|\s*(?:[,;:，；：]|[-\u2013\u2014]{1,2})?\s*"
    r"(?:until|once)\b[^.!?。！？;；]{1,120}"
    r"(?:"
    r"[.!?。！？]\s*(?:then\s+)?)"
    r"|\s*[.!?。！？]\s*(?:after|once)\b[^.!?。！？;；]{1,120}[,;:，；：]\s*)"
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
    r"\b(?:no|not|never|without|do not|does not|must not|nothing from|"
    r"cannot|can['\u2019]t|could not|couldn['\u2019]t|will not|won['\u2019]t|"
    r"would not|wouldn['\u2019]t|fail(?:s|ed)? to|"
    r"refus(?:e|es|ed|ing)(?:\s+to)?|"
    r"den(?:y|ies|ied)(?:\s+the\s+request)?(?:\s+permission)?(?:\s+to)?|"
    r"(?:is|are|was|were)\s+(?:denied|forbidden|prevented)"
    r"(?:\s+permission)?(?:\s+(?:from|to))?|"
    r"(?:is|are|was|were) (?:completely )?unable to|"
    r"(?:isn['\u2019]t|aren['\u2019]t|wasn['\u2019]t|weren['\u2019]t) able to)"
    r"\b[^.;,]{0,24}$",
    re.I,
)
SCOPED_EXCLUSION = re.compile(
    r"\b(do not|does not|must not|never|nothing from|ignore|exclude|"
    r"omit(?:s|ted)?)\b",
    re.I,
)
NEGATION_RESET = re.compile(
    r"\b(?:not\s+only|but|however|instead|except)\b|"
    r"(?:[,:]\s*|\band\s+|\bthen\s+)(?:then\s+)?"
    r"(?:use\b(?!\s+of\b)|keep\b|preserve\b|retain\b|include\b|add\b|"
    r"animate\b|create\b|depict\b|feature\b|generate\b|make\b|portray\b|"
    r"render\b|show\b|star\b|light\b(?!\s+of\b)|illuminate\b)",
    re.I,
)
DOUBLE_NEGATED_EXCLUSION = re.compile(
    r"\b(?:do not|does not|must not|will not|should not|can(?:not| not)|never|"
    r"don['\u2019]t|doesn['\u2019]t|mustn['\u2019]t|won['\u2019]t|"
    r"shouldn['\u2019]t|can['\u2019]t)\s+(?:ignore|exclude)\b",
    re.I,
)
TARGET_NEGATED_ALTERNATIVE = re.compile(
    r"\b(?:rather\s+than|instead\s+of)\b[^,.;!?。！？；]{0,80}$",
    re.I,
)
POSTPOSITIVE_EXCLUSION = re.compile(
    r"(?P<subject>(?:\b[A-Za-z0-9]+(?:['’\u2019-][A-Za-z0-9]+)?\b[\s-]*){1,8}?)"
    r"\s+(?:"
    r"(?:is|are|was|were)\s+"
    r"(?:(?:completely|deliberately|entirely|explicitly|intentionally)\s+)?(?:"
    r"not\s+(?:shown|seen|included|present|depicted|featured)|"
    r"absent|missing|excluded|omitted|left\s+out)"
    r"|(?:do|does|did)\s+not\s+(?:appear|show|feature)"
    r"|never\s+(?:appears?|shows?|enters?|features?)"
    r")\b",
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
OPPOSITE_ACTION_TERMS = frozenset().union(*OPPOSITE_ACTIONS)
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


@lru_cache(maxsize=4096)
def structural_contract_terms(text: str) -> frozenset[str]:
    """Return words whose only evidence value is a format contract.

    Counts and animation-medium labels are scored separately by
    ``production_trace_contracts``. Reusing them as target evidence lets a
    three-shot animation of one subject falsely validate another subject.
    """
    terms: set[str] = set()
    for pattern in (COUNTED_SHOT_REQUEST, NUMBERED_SHOT_MARKER, ANIMATION_CONTRACT):
        for match in pattern.finditer(text):
            terms.update(lexical_tokens(match.group(0)))
    return frozenset(terms)


@lru_cache(maxsize=4096)
def affirmative_trace_terms(text: str) -> frozenset[str]:
    """Return unquoted lexical evidence asserted positively by the text."""
    terms: set[str] = set()
    for match in TOKEN.finditer(text):
        if position_is_quoted(text, match.start()) or match_is_negated(
            text, match.start()
        ) or _position_is_postpositively_excluded(
            text, match.start()
        ):
            continue
        local_start = max(
            text.rfind(mark, 0, match.start())
            for mark in ",.;!?。！？；\n"
        ) + 1
        if TARGET_NEGATED_ALTERNATIVE.search(text[local_start:match.start()]):
            continue
        terms.update(
            token
            for token in lexical_tokens(match.group(0))
            if len(token) > 2
            and token not in FUNCTION_WORDS
            and token not in PRODUCTION_GENERIC
            and token not in TRACE_GENERIC
        )
    return frozenset(terms)


def _position_is_postpositively_excluded(text: str, position: int) -> bool:
    """Catch exclusions whose polarity arrives after the named subject.

    Prefix-only negation misses ordinary constructions such as ``the surgeon is
    absent`` and ``the surgeon never appears``.  Limit this check to the local
    comma/statement span, then require the token to fall inside the grammatical
    subject captured by the exclusion rather than suppressing the whole clause.
    """
    local_start = max(
        text.rfind(mark, 0, position)
        for mark in ",.;!?。！？；，\n"
    ) + 1
    local_end_candidates = [
        found
        for mark in ",.;!?。！？；，\n"
        if (found := text.find(mark, position)) != -1
    ]
    local_end = min(local_end_candidates, default=len(text))
    local = text[local_start:local_end]
    local_position = position - local_start
    return any(
        match.start("subject") <= local_position < match.end("subject")
        for match in POSTPOSITIVE_EXCLUSION.finditer(local)
    )


@lru_cache(maxsize=4096)
def target_trace_terms(text: str) -> frozenset[str]:
    """Return affirmative, non-structural material the prompt must carry."""
    return frozenset(
        affirmative_trace_terms(text)
        - structural_contract_terms(text)
        - TARGET_CONTROL_TERMS
    )


def _bounded_target_group(
    tokens: list[str],
    protected_heads: tuple[str, ...] = (),
) -> frozenset[str]:
    """Bound dense targets without dropping a grammatical identity head.

    The final token is not necessarily the subject head: ``surgeon named Mara``
    ends in the name. Preserve the noun immediately before an identity marker as
    well as the final identity token, then spend the remaining budget on the
    opening attributes.
    """
    if len(tokens) <= MAX_EXPLICIT_TARGET_REQUIREMENTS:
        return frozenset(tokens)
    essentials = list(dict.fromkeys((*protected_heads, tokens[-1])))
    opening_budget = max(0, MAX_EXPLICIT_TARGET_REQUIREMENTS - len(essentials))
    bounded = list(tokens[:opening_budget])
    for token in essentials:
        if token not in bounded:
            bounded.append(token)
    return frozenset(bounded[:MAX_EXPLICIT_TARGET_REQUIREMENTS])


def _target_clause_ranges(text: str) -> tuple[tuple[int, int], ...]:
    ranges: list[tuple[int, int]] = []
    start = 0
    for boundary in TARGET_STRONG_BOUNDARY.finditer(text):
        if start < boundary.start():
            ranges.append((start, boundary.start()))
        start = boundary.end()
    if start < len(text):
        ranges.append((start, len(text)))
    return tuple(ranges)


def _candidate_is_reference_description(
    text: str,
    match: re.Match[str],
    clause_start: int,
) -> bool:
    """Reject only the production noun directly owned by an asset marker.

    A source marker must be adjacent to this candidate (``reference image`` or
    ``@Image1 is an image``).  Merely occurring earlier in the clause cannot
    suppress a downstream requested output such as ``an animation of ...``.
    """
    prefix = text[clause_start:match.start()]
    markers = list(TARGET_ASSET_MARKER.finditer(prefix))
    if not markers:
        return False
    latest_marker = markers[-1]
    marker_to_candidate = prefix[latest_marker.end():]
    if not re.fullmatch(
        r"\s*[,(:]?\s*(?:which\s+)?(?:(?:is|as)\s+)?(?:a|an|the)?\s*"
        r"(?:(?:clip|frame|image|portrait|shot|video)\s+)?",
        marker_to_candidate,
        re.I,
    ):
        return False

    requests = list(TARGET_OUTPUT_REQUEST.finditer(prefix))
    if requests and requests[-1].start() > latest_marker.start():
        return False
    if requests:
        between = prefix[requests[-1].end():latest_marker.start()]
        if re.fullmatch(r"\s+(?:a|an|another|the)?\s*", between, re.I):
            # ``create a reference image`` requests that output; ``generate
            # from the reference image`` describes an input.
            return False
    return True


def _candidate_is_coordinated(
    text: str,
    previous: re.Match[str],
    current: re.Match[str],
) -> bool:
    tail = text[previous.end():current.start()]
    return TARGET_OUTPUT_COORDINATION.search(tail) is not None


def _eligible_target_intros(
    text: str,
    clause_start: int,
    clause_end: int,
) -> tuple[re.Match[str], ...]:
    production = [
        match
        for match in PRODUCTION_TARGET_INTRO.finditer(
            text, clause_start, clause_end
        )
        if not _candidate_is_reference_description(text, match, clause_start)
    ]
    eligible: list[re.Match[str]] = []
    for match in production:
        if not eligible or _candidate_is_coordinated(text, eligible[-1], match):
            eligible.append(match)
    if eligible:
        return tuple(eligible)

    depiction = [
        match
        for match in DEPICTION_TARGET_INTRO.finditer(
            text, clause_start, clause_end
        )
        if not _candidate_is_reference_description(text, match, clause_start)
    ]
    for match in depiction:
        if not eligible or _candidate_is_coordinated(text, eligible[-1], match):
            eligible.append(match)
    return tuple(eligible)


def _mandatory_target_texts(text: str) -> tuple[str, ...]:
    """Collect every mandatory output target, excluding described assets."""
    targets: list[str] = []
    for clause_start, clause_end in _target_clause_ranges(text):
        intros = _eligible_target_intros(text, clause_start, clause_end)
        for index, match in enumerate(intros):
            target_end = clause_end
            if index + 1 < len(intros):
                target_end = min(target_end, intros[index + 1].start())
            target = text[match.end():target_end]
            target = re.sub(
                r"\b(?:and|plus)\s+(?:a|an|another|the)?\s*$",
                "",
                target,
                flags=re.I,
            ).strip()
            if target:
                targets.extend(_split_mandatory_target_items(target))
    return tuple(targets)


def _target_list_item(
    segment: str,
    *,
    allow_bare: bool,
) -> tuple[str, str] | None:
    """Return ``(coordinator, noun phrase)`` for a comma-listed subject."""
    stripped = segment.strip()
    coordinator_match = re.match(r"(?:(and|or|plus)\s+)?", stripped, re.I)
    coordinator = (
        coordinator_match.group(1).lower()
        if coordinator_match and coordinator_match.group(1)
        else ""
    )
    candidate = stripped[coordinator_match.end():].strip() if coordinator_match else stripped
    if not candidate or PRODUCTION_TARGET_INTRO.search(candidate):
        return None
    candidate_tokens = lexical_tokens(candidate)
    material = [
        token
        for token in candidate_tokens
        if token not in FUNCTION_WORDS
        and token not in PRODUCTION_GENERIC
        and token not in TRACE_GENERIC
        and len(token) > 2
    ]
    if not material or len(candidate_tokens) > MAX_EXPLICIT_TARGET_REQUIREMENTS + 3:
        return None
    first = candidate_tokens[0] if candidate_tokens else ""
    if first in TARGET_PHRASE_BREAKS or first in {
        "camera", "cut", "during", "light", "sound", "when", "while",
    }:
        return None
    if any(token in TARGET_ACTION_BREAKS for token in candidate_tokens):
        return None
    begins_with_article = bool(
        re.match(r"(?:a|an|another|the)\b", candidate, re.I)
    )
    if not coordinator and not begins_with_article and not (
        allow_bare and len(material) <= 3
    ):
        return None
    return coordinator, candidate


def _split_mandatory_target_items(target: str) -> tuple[str, ...]:
    """Separate comma-listed mandatory subjects from later scene direction.

    ``A surgeon, a nurse, and a busker`` is three required subjects.  If the
    list resolves with ``or``, the items remain alternatives in one clause.
    Location/action continuations after a comma are deliberately not promoted
    into new target requirements.
    """
    segments = re.split(r"[,，]", target)
    first = segments[0].strip()
    if not first:
        return ()
    if len(segments) == 1:
        return (first,)
    allow_bare = len(segments) >= 3 or any(
        re.match(r"\s*(?:and|or|plus)\b", segment, re.I)
        for segment in segments[1:]
    )
    listed: list[tuple[str, str]] = []
    for segment in segments[1:]:
        item = _target_list_item(segment, allow_bare=allow_bare)
        if item is None:
            break
        listed.append(item)
    if not listed:
        return (first,)
    if any(coordinator == "or" for coordinator, _ in listed):
        return (" or ".join([first, *(item for _, item in listed)]),)
    return tuple([first, *(item for _, item in listed)])


TARGET_SHARED_RELATIONS = {"carry", "hold", "wear"}


def _relational_alternative_groups(
    target: str,
    structural: frozenset[str],
) -> tuple[frozenset[str], ...]:
    """Bind a shared subject/action to each coordinated object branch.

    The ordinary target parser intentionally stops at action direction.  That
    loses the actual alternatives in a compact noun phrase such as ``a surgeon
    holding a red case or blue bag``.  Handle only the bounded relational forms
    whose action and ``or`` are explicit; unrelated scene choreography keeps the
    conservative stop behavior.
    """
    tokens = lexical_tokens(target)
    relation_indices = [
        index
        for index, token in enumerate(tokens)
        if token in TARGET_SHARED_RELATIONS
    ]
    if not relation_indices:
        return ()
    relation_index = relation_indices[0]
    if TARGET_ALTERNATIVE not in tokens[relation_index + 1:]:
        return ()

    ignored = (
        FUNCTION_WORDS
        | PRODUCTION_GENERIC
        | TRACE_GENERIC
        | TARGET_CONTROL_TERMS
        | structural
    )

    def material(segment: list[str]) -> list[str]:
        result: list[str] = []
        for token in segment:
            if result and token in TARGET_PHRASE_BREAKS:
                break
            if (
                token not in ignored
                and token != TARGET_ALTERNATIVE
                and len(token) > 2
            ):
                result.append(token)
        return result

    shared_subject = material(tokens[:relation_index])
    relation = tokens[relation_index]
    if not shared_subject:
        return ()

    raw_branches: list[list[str]] = [[]]
    for token in tokens[relation_index + 1:]:
        if token == TARGET_ALTERNATIVE:
            raw_branches.append([])
        else:
            raw_branches[-1].append(token)
    if len(raw_branches) < 2 or any(not branch for branch in raw_branches):
        return ()

    groups: list[frozenset[str]] = []
    for branch_index, branch in enumerate(raw_branches):
        repeated_relations = [
            index
            for index, token in enumerate(branch)
            if token in TARGET_SHARED_RELATIONS
        ]
        if branch_index and repeated_relations:
            branch_relation_index = repeated_relations[0]
            branch_subject = material(branch[:branch_relation_index])
            branch_object = material(branch[branch_relation_index + 1:])
            if not branch_subject or not branch_object:
                return ()
            combined = [
                *branch_subject,
                branch[branch_relation_index],
                *branch_object,
            ]
            subject_head = branch_subject[-1]
        else:
            branch_object = material(branch)
            if not branch_object:
                return ()
            combined = [*shared_subject, relation, *branch_object]
            subject_head = shared_subject[-1]
        groups.append(
            _bounded_target_group(
                combined,
                (subject_head, branch_object[-1]),
            )
        )
    return tuple(groups)


def _target_groups_from_text(
    target: str,
    structural: frozenset[str],
) -> tuple[frozenset[str], ...]:
    relational = _relational_alternative_groups(target, structural)
    if relational:
        return relational
    branches: list[tuple[list[str], list[str]]] = []
    requirements: list[str] = []
    protected_heads: list[str] = []
    target_tokens = lexical_tokens(target)
    for index, token in enumerate(target_tokens):
        if token == TARGET_ALTERNATIVE and requirements:
            branches.append((requirements, protected_heads))
            requirements = []
            protected_heads = []
            continue
        if token in TARGET_IDENTITY_MARKERS:
            if requirements:
                protected_heads.append(requirements[-1])
            continue
        if (
            token == "to"
            and index + 1 < len(target_tokens)
            and target_tokens[index + 1] in TARGET_PURPOSE_VERBS
        ):
            break
        if requirements and (
            token in TARGET_PHRASE_BREAKS or token in TARGET_ACTION_BREAKS
        ):
            break
        if (
            token in FUNCTION_WORDS
            or token in PRODUCTION_GENERIC
            or token in TRACE_GENERIC
            or token in TARGET_CONTROL_TERMS
            or token in structural
            or len(token) <= 2
        ):
            continue
        requirements.append(token)
    if requirements:
        branches.append((requirements, protected_heads))
    if not branches:
        return ()

    surface_branches = re.split(r"\bor\b", target, flags=re.I)

    first_tokens, first_protected = branches[0]
    identity_head = first_protected[-1] if first_protected else ""
    if identity_head and identity_head in first_tokens:
        shared_identity = first_tokens[:first_tokens.index(identity_head) + 1]
    else:
        shared_identity = []
    shared_modifiers = first_tokens[:-1] if len(first_tokens) > 1 else []

    groups: list[frozenset[str]] = []
    for branch_index, (branch_tokens, branch_protected) in enumerate(branches):
        inherited: list[str] = []
        inherited_heads: list[str] = []
        surface_branch = (
            surface_branches[branch_index]
            if branch_index < len(surface_branches)
            else ""
        )
        starts_new_noun_phrase = bool(
            re.match(r"\s*(?:a|an|another|the)\b", surface_branch, re.I)
        )
        if (
            branch_index
            and identity_head
            and identity_head not in branch_tokens
            and not branch_protected
            and not starts_new_noun_phrase
        ):
            # ``surgeon named Mara or Nia`` shares the entity head and all
            # pre-name attributes across both identity alternatives.
            inherited = shared_identity
            inherited_heads = [identity_head]
        elif (
            branch_index
            and len(branch_tokens) == 1
            and shared_modifiers
            and not starts_new_noun_phrase
        ):
            # In ``red emergency surgeon or nurse``, the single replacement
            # noun inherits the shared adjectival prefix.
            inherited = shared_modifiers
        combined = list(dict.fromkeys([*inherited, *branch_tokens]))
        protected = tuple(dict.fromkeys([*inherited_heads, *branch_protected]))
        if combined:
            groups.append(_bounded_target_group(combined, protected))
    return tuple(groups)


@lru_cache(maxsize=4096)
def explicit_target_requirement_clauses(
    text: str,
) -> tuple[tuple[frozenset[str], ...], ...]:
    """Return mandatory clauses, each containing its acceptable alternatives."""
    structural = structural_contract_terms(text)
    return tuple(
        groups
        for target in _mandatory_target_texts(text)
        if (groups := _target_groups_from_text(target, structural))
    )


@lru_cache(maxsize=4096)
def explicit_target_requirement_groups(text: str) -> tuple[frozenset[str], ...]:
    """Flatten mandatory target clauses for diagnostics and compatibility.

    This is intentionally lexical rather than pretending to be a full parser.
    ``explicit_target_requirement_clauses`` preserves the distinction between
    mandatory outputs and alternatives within one output; this helper exposes
    the historical flat shape used by tests and diagnostics.
    """
    return tuple(
        group
        for clause in explicit_target_requirement_clauses(text)
        for group in clause
    )


@lru_cache(maxsize=4096)
def explicit_target_requirements(text: str) -> frozenset[str]:
    """Return the union of explicit target terms for diagnostics and callers."""
    groups = explicit_target_requirement_groups(text)
    return frozenset().union(*groups) if groups else frozenset()


ACTION_SURFACE_ALIASES = {
    "latch": "close",
    "latched": "close",
    "latches": "close",
    "latching": "close",
    "seal": "close",
    "sealed": "close",
    "sealing": "close",
    "seals": "close",
    "unlatch": "open",
    "unlatched": "open",
    "unlatches": "open",
    "unlatching": "open",
    "unseal": "open",
    "unsealed": "open",
    "unsealing": "open",
    "unseals": "open",
}
OBJECT_PRONOUNS = {"it", "them", "this", "that", "these", "those"}
OBJECT_DETERMINERS = {
    "a", "an", "her", "his", "its", "my", "our", "the", "their",
    "this", "these", "those", "your",
}
OBJECT_BREAKS = {
    "above", "across", "against", "and", "around", "as", "below", "behind",
    "beside", "between", "but", "by", "during", "for", "in", "inside",
    "instead", "near", "on", "or", "outside", "then", "under", "when",
    "while", "with",
}
POSTNOMINAL_OBJECT_MARKERS = {
    "bear", "call", "label", "mark", "nam", "number", "paint", "with",
}
LEADING_OBJECT_PREPOSITIONS = {
    "at", "from", "into", "through", "to", "toward", "towards",
}
MOVEMENT_ACTIONS = {
    "approach", "arrive", "depart", "enter", "exit", "retreat",
}
ANTECEDENT_ACTIONS = TARGET_ACTION_BREAKS | OPPOSITE_ACTION_TERMS | {
    "bring", "carry", "deliver", "drag", "grip", "lock", "pick", "place",
    "set", "take", "transport", "unlock",
}
NON_OBJECT_FOLLOWERS = {
    "are", "be", "become", "break", "fail", "fall", "hang", "is", "lie",
    "look", "remain", "rest", "sit", "stand", "swim", "was", "were",
}
ACTION_AUXILIARIES = {
    "be", "been", "being", "can", "could", "did", "do", "does", "get", "got",
    "had", "has", "have", "is", "may", "might", "must", "should", "was",
    "were", "will", "would",
}
ACTION_OBJECT_PUNCTUATION = re.compile(r"[,.;!?。！？，；\n]")
ACTION_CLAUSE_PUNCTUATION = re.compile(r"[.;!?。！？；\n]")
ACTION_NEGATOR = re.compile(
    r"\b(?:no|not|never|without|do not|does not|must not|nothing from|"
    r"cannot|can['\u2019]t|could not|couldn['\u2019]t|will not|won['\u2019]t|"
    r"would not|wouldn['\u2019]t|fail(?:s|ed)? to|"
    r"refus(?:e|es|ed|ing)(?:\s+to)?|"
    r"den(?:y|ies|ied)(?:\s+the\s+request)?(?:\s+permission)?(?:\s+to)?|"
    r"(?:is|are|was|were)\s+(?:denied|forbidden|prevented)"
    r"(?:\s+permission)?(?:\s+(?:from|to))?|"
    r"(?:is|are|was|were)\s+(?:completely\s+)?unable to|"
    r"(?:isn['\u2019]t|aren['\u2019]t|wasn['\u2019]t|weren['\u2019]t) able to)\b",
    re.I,
)
ACTION_POSTPOSITIVE_DENIAL = re.compile(
    r"^\s*(?:\b[A-Za-z0-9]+(?:['’\u2019-][A-Za-z0-9]+)?\b\s*){0,12}"
    r"(?:is|are|was|were)\s+(?:explicitly\s+)?"
    r"(?:absent|denied|forbidden|missing|omitted|prevented|refused|"
    r"not\s+(?:allowed|completed|performed|shown))\b",
    re.I,
)
ACTION_NONCOMMITTAL_PREFIX = re.compile(
    r"\b(?:"
    r"(?:attempt(?:s|ed|ing)?|tr(?:y|ies|ied|ying)|plan(?:s|ned|ning)?|"
    r"intend(?:s|ed|ing)?|want(?:s|ed|ing)?)\s+to|"
    r"(?:may|might|could)"
    r")\s*$",
    re.I,
)
ACTION_GRAMMAR_TERMS = {
    "able", "allow", "cannot", "could", "deni", "fail", "forbid", "never",
    "not", "permission", "prevent", "refus", "request", "unable", "will",
    "without", "would",
}


def _canonical_action_token(surface: str) -> str:
    lowered = surface.lower().replace("’", "'").strip("'")
    if lowered in ACTION_SURFACE_ALIASES:
        return ACTION_SURFACE_ALIASES[lowered]
    canonical = lexical_tokens(surface)
    return canonical[0] if len(canonical) == 1 else ""


def _action_content_term(token: str) -> bool:
    return (
        len(token) > 2
        and token not in FUNCTION_WORDS
        and token not in PRODUCTION_GENERIC
        and token not in TRACE_GENERIC
        and token not in TARGET_CONTROL_TERMS
        and token not in ACTION_MODIFIERS
        and token not in ACTION_GRAMMAR_TERMS
        and token not in ANTECEDENT_ACTIONS
        and not token.endswith("ly")
    )


def _compact_object_identity(tokens: list[str]) -> tuple[str, ...]:
    """Keep discriminative opening modifiers plus the grammatical head noun."""
    if len(tokens) <= 8:
        return tuple(tokens)
    return tuple(tokens[:7] + [tokens[-1]])


def _composed_object_identity(
    head: str,
    modifiers: list[str],
) -> tuple[str, ...]:
    """Encode modifiers first and the grammatical head in the final slot."""
    unique_modifiers = [
        token
        for token in dict.fromkeys(modifiers)
        if token and token != head
    ]
    if len(unique_modifiers) > 7:
        unique_modifiers = unique_modifiers[:7]
    return tuple([*unique_modifiers, head]) if head else ()


def _direct_object_identity(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
    canonical_action: str,
) -> tuple[tuple[str, ...], bool]:
    direct_terms: list[str] = []
    postnominal_terms: list[str] = []
    in_postnominal = False
    relative_postnominal = False
    pronoun_object = False
    cursor = token_matches[action_index].end()
    inspected = 0
    for following in token_matches[action_index + 1:]:
        if (
            inspected >= 16
            or ACTION_OBJECT_PUNCTUATION.search(text[cursor:following.start()])
        ):
            break
        inspected += 1
        following_tokens = lexical_tokens(following.group(0))
        if len(following_tokens) != 1:
            break
        token = following_tokens[0]
        if token in {"that", "which"} and direct_terms:
            relative_postnominal = True
            cursor = following.end()
            continue
        if direct_terms and token in {"are", "is", "was", "were"}:
            if relative_postnominal:
                cursor = following.end()
                continue
            break
        if _canonical_action_token(following.group(0)) in ANTECEDENT_ACTIONS:
            break
        if token in OBJECT_PRONOUNS and not direct_terms:
            pronoun_object = True
            cursor = following.end()
            continue
        if token in LEADING_OBJECT_PREPOSITIONS and not direct_terms:
            if canonical_action in MOVEMENT_ACTIONS:
                cursor = following.end()
                continue
            break
        if token in POSTNOMINAL_OBJECT_MARKERS and direct_terms:
            in_postnominal = True
            cursor = following.end()
            continue
        if token in OBJECT_BREAKS:
            break
        if _action_content_term(token):
            if in_postnominal:
                postnominal_terms.append(token)
            else:
                direct_terms.append(token)
        cursor = following.end()
    if not direct_terms:
        return (), pronoun_object
    return _composed_object_identity(
        direct_terms[-1],
        [*direct_terms[:-1], *postnominal_terms],
    ), pronoun_object


def _local_antecedent_start(text: str, action_start: int) -> int:
    boundaries = list(ACTION_CLAUSE_PUNCTUATION.finditer(text, 0, action_start))
    if not boundaries:
        return 0
    local_start = boundaries[-1].end()
    prefix = text[local_start:action_start]
    # A cue-led new sentence may refer to the explicit object in the immediately
    # preceding event, but never search the whole prompt for a convenient noun.
    if re.match(r"\s*(?:then|next|finally)\b", prefix, re.I):
        return boundaries[-2].end() if len(boundaries) >= 2 else 0
    return local_start


def _resolve_pronoun_object(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
) -> tuple[str, ...]:
    local_start = _local_antecedent_start(
        text, token_matches[action_index].start()
    )
    for previous_index in range(action_index - 1, -1, -1):
        previous = token_matches[previous_index]
        if previous.start() < local_start:
            break
        previous_action = _canonical_action_token(previous.group(0))
        if previous_action not in ANTECEDENT_ACTIONS:
            continue
        identity, was_pronoun = _direct_object_identity(
            text, token_matches, previous_index, previous_action
        )
        if identity and not was_pronoun:
            return identity
    return ()


def _subject_object_identity(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
) -> tuple[str, ...]:
    action_start = token_matches[action_index].start()
    clause_start = _local_antecedent_start(text, action_start)
    terms = [
        token
        for prior in token_matches[:action_index]
        if prior.start() >= clause_start
        for token in lexical_tokens(prior.group(0))
        if _action_content_term(token)
    ]
    return _compact_object_identity(terms)


def _ambiguous_alias_is_verbal(
    text: str,
    token_matches: list[re.Match[str]],
    index: int,
) -> bool:
    surface = token_matches[index].group(0).lower()
    if surface not in ACTION_SURFACE_ALIASES:
        return True
    previous_surface = token_matches[index - 1].group(0) if index else ""
    previous = lexical_tokens(previous_surface)
    previous_token = previous[0] if len(previous) == 1 else ""
    following_surface = (
        token_matches[index + 1].group(0)
        if index + 1 < len(token_matches)
        else ""
    )
    following = lexical_tokens(following_surface)
    following_token = following[0] if len(following) == 1 else ""
    following_action = _canonical_action_token(following_surface)
    if previous_token in {"a", "an", "the"}:
        return False
    if following_action in ANTECEDENT_ACTIONS:
        # ``harbor seal rests`` and ``door latch opens`` are noun phrases.
        return False
    if following_token in NON_OBJECT_FOLLOWERS:
        return False
    if surface in {"seal", "latch", "unseal", "unlatch"}:
        clause_prefix = text[
            _local_antecedent_start(text, token_matches[index].start()):
            token_matches[index].start()
        ]
        return (
            not clause_prefix.strip()
            or previous_token
            in {"and", "can", "could", "must", "next", "please", "should", "then", "to"}
        )
    if surface.endswith("ed") and previous_surface.lower().endswith("ly"):
        return False
    if (
        not following_token
        or following_token in OBJECT_BREAKS
        or following_token in LEADING_OBJECT_PREPOSITIONS
    ):
        return previous_token in {"that", "which", "who"} | ACTION_AUXILIARIES
    return True


STATE_TRANSITION_ATTRIBUTE = re.compile(
    r"\bclosed\s+[A-Za-z0-9'-]+(?:\s+[A-Za-z0-9'-]+){0,3}\s+to\s+"
    r"open\s+[A-Za-z0-9'-]+",
    re.I,
)


def _action_surface_is_predicate(
    text: str,
    token_matches: list[re.Match[str]],
    index: int,
) -> bool:
    """Reject obvious action-shaped nouns and attributive state words.

    The trace gate is intentionally conservative: it may require an action only
    when the token is functioning as a predicate.  Without this guard, terse
    briefs such as ``desert bus stop``, ``opening scene``, and ``closed door to
    open doorway transition`` manufacture action requirements that the brief
    never made.  Finite forms, auxiliaries, infinitives, imperatives, and
    nominalised actions with an explicit object remain eligible.
    """
    match = token_matches[index]
    if not _ambiguous_alias_is_verbal(text, token_matches, index):
        return False

    surface = match.group(0).lower().replace("’", "'").strip("'")
    canonical_action = _canonical_action_token(surface)
    previous_match = token_matches[index - 1] if index else None
    following_match = (
        token_matches[index + 1] if index + 1 < len(token_matches) else None
    )
    previous_tokens = (
        lexical_tokens(previous_match.group(0)) if previous_match else []
    )
    following_tokens = (
        lexical_tokens(following_match.group(0)) if following_match else []
    )
    previous = previous_tokens[0] if len(previous_tokens) == 1 else ""
    following = following_tokens[0] if len(following_tokens) == 1 else ""
    clause_start = _local_antecedent_start(text, match.start())
    clause_prefix = text[clause_start:match.start()]

    for transition in STATE_TRANSITION_ATTRIBUTE.finditer(text):
        if transition.start() <= match.start() < transition.end():
            return False

    article = previous in OBJECT_DETERMINERS
    relative_or_demonstrative = previous in {
        "that", "which", "who", "this", "these", "those",
    }
    if article and not relative_or_demonstrative:
        return False

    base_surface = surface == canonical_action
    past_surface = surface.endswith("ed")
    gerund_surface = surface.endswith("ing")
    following_is_material = bool(following) and _action_content_term(following)
    following_is_bare_noun = (
        bool(following)
        and following not in OBJECT_DETERMINERS
        and following not in ACTION_MODIFIERS
        and following not in ACTION_AUXILIARIES
        and following not in OBJECT_BREAKS
        and following not in NON_OBJECT_FOLLOWERS
    )

    if base_surface and previous in {"am", "are", "is", "was", "were"}:
        # Copular states are not completed events: ``the case is open`` cannot
        # satisfy a brief requiring somebody to open it.
        return False

    if (
        (past_surface or gerund_surface)
        and following_is_bare_noun
        and not clause_prefix.strip()
    ):
        # ``Closed door`` and ``Opening scene`` are noun phrases.  ``Opening
        # the case`` remains a nominalised action because the object determiner
        # supplies unambiguous predicate structure.
        return False

    if base_surface and not following:
        # A bare action word after an ordinary noun is normally a compound noun
        # or state (``bus stop``, ``door open``).  A pronoun/auxiliary still
        # supplies an unambiguous finite predicate (``they stop``).
        previous_surface = (
            previous_match.group(0).lower().replace("’", "'").strip("'")
            if previous_match is not None
            else ""
        )
        previous_looks_plural = bool(previous) and previous != previous_surface
        return previous in (
            ACTION_AUXILIARIES
            | {"and", "but", "i", "it", "or", "she", "they", "to", "we", "you"}
        ) or previous_looks_plural or not clause_prefix.strip()

    if (
        base_surface
        and previous
        and previous not in ACTION_AUXILIARIES
        and previous not in {
            "and", "but", "he", "i", "it", "or", "she", "they", "to", "we",
            "please", "which", "who", "you",
        }
        and previous_match is not None
        and not previous_match.group(0).lower().endswith("s")
        and following_is_material
        and following not in OBJECT_DETERMINERS
    ):
        # Singular noun + base form + noun is a compound/attribute, not an
        # English finite predicate (``bus stop sign``).  Plural subjects and
        # explicit determiners remain valid: ``couriers open cases`` and
        # ``a courier opens the case``.
        return False
    return True


def _action_match_is_negated(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
) -> bool:
    """Resolve negation at predicate scope instead of clause scope.

    A modal/refusal can govern coordinated non-finite predicates (``cannot open
    or close``), but it has already discharged its complement before a later
    finite event (``cannot open the case and closes it``).  Generic term
    negation remains clause-aware elsewhere; only action predicates need this
    grammatical reset.
    """
    match = token_matches[action_index]
    action_start = match.start()
    clause_start = _local_antecedent_start(text, action_start)
    clause_end_match = ACTION_CLAUSE_PUNCTUATION.search(text, match.end())
    clause_end = clause_end_match.start() if clause_end_match else len(text)
    if ACTION_POSTPOSITIVE_DENIAL.search(text[match.end():clause_end]):
        return True
    prefix_negated = match_is_negated(text, action_start)
    prefix = text[clause_start:action_start]
    if re.search(r"\bnot\s+only(?:\s+\w+ly)?\s*$", prefix, re.I):
        return False
    if re.search(
        r"\b(?:never|cannot|can['’]t)\s+fail(?:s|ed)?\s+to\s*$",
        prefix,
        re.I,
    ):
        return False
    if ACTION_NONCOMMITTAL_PREFIX.search(prefix):
        return True
    negators = [
        negator
        for negator in ACTION_NEGATOR.finditer(prefix)
        if not position_is_quoted(text, clause_start + negator.start())
    ]
    if not negators:
        return prefix_negated
    latest = negators[-1]
    if not prefix_negated and NEGATION_RESET.search(prefix[latest.end():]):
        return False
    negator_end = clause_start + latest.end()
    prior_action_indices = [
        index
        for index in range(action_index)
        if token_matches[index].start() >= negator_end
        and _canonical_action_token(token_matches[index].group(0))
        in OPPOSITE_ACTION_TERMS
        and not position_is_quoted(text, token_matches[index].start())
        and _action_surface_is_predicate(text, token_matches, index)
    ]
    if not prior_action_indices:
        return True

    previous_index = prior_action_indices[-1]
    previous = token_matches[previous_index]
    bridge = text[previous.end():action_start]
    coordinators = list(re.finditer(r"\b(and|or)\b", bridge, re.I))
    if not coordinators:
        return False
    coordinator = coordinators[-1]
    tail = bridge[coordinator.end():]
    if re.search(r"\b(?:but|however|instead|then)\b", tail, re.I):
        return False
    if re.search(
        r"\b(?:he|she|they|we|you|i|this|that|these|those)\b",
        tail,
        re.I,
    ):
        return False
    if re.search(
        r"\b(?:am|is|are|was|were|do|does|did|has|have|had|can|could|"
        r"may|might|shall|should|will|would)\b",
        tail,
        re.I,
    ):
        # A repeated finite auxiliary starts a new coordinated predicate:
        # ``cannot be opened and is closed`` does not leave ``closed`` under
        # the first modal's negative scope.  Bare ``be`` is deliberately not a
        # reset because ``cannot be opened or be closed`` shares that scope.
        return False
    if re.search(r"\b(?:a|an|the)\s+[A-Za-z0-9'-]+\s*$", tail, re.I):
        return False
    tail_matches = list(TOKEN.finditer(tail))
    if tail_matches:
        subject_surface = tail_matches[-1].group(0).lower()
        subject_tokens = lexical_tokens(subject_surface)
        if (
            len(subject_tokens) == 1
            and subject_tokens[0] != subject_surface
            and subject_tokens[0] not in ACTION_MODIFIERS
        ):
            # A plural lexical subject licenses a base-form finite predicate:
            # ``cannot open the case and workers close it``.
            return False

    surface = match.group(0).lower().replace("’", "'")
    previous_surface = previous.group(0).lower().replace("’", "'")
    finite_inflection = (
        (surface.endswith("s") and not surface.endswith("ss"))
        or surface.endswith("ed")
    )
    if finite_inflection:
        passive_parallel = (
            surface.endswith("ed")
            and previous_surface.endswith("ed")
            and re.search(
                r"\b(?:be|been|being|is|are|was|were)\b",
                text[negator_end:previous.start()],
                re.I,
            )
            is not None
        )
        if not passive_parallel:
            return False
    return True


def action_mentions(
    text: str,
) -> tuple[tuple[str, int, int, bool, tuple[str, ...]], ...]:
    """Extract bounded, polarity-aware action/object mentions.

    The object binding prevents a required case action from being satisfied or
    reversed by an unrelated door action. Negated actions remain available as
    antecedents for a later ``it``, while quoted dialogue never becomes action
    evidence.
    """
    token_matches = list(TOKEN.finditer(text))
    mentions: list[dict[str, object]] = []

    for index, match in enumerate(token_matches):
        canonical_action = _canonical_action_token(match.group(0))
        if canonical_action not in OPPOSITE_ACTION_TERMS:
            continue
        if position_is_quoted(text, match.start()):
            continue
        if not _action_surface_is_predicate(text, token_matches, index):
            continue
        previous = token_matches[index - 1] if index else None
        previous_token = (
            lexical_tokens(previous.group(0))[0]
            if previous is not None and lexical_tokens(previous.group(0))
            else ""
        )
        following_match = (
            token_matches[index + 1] if index + 1 < len(token_matches) else None
        )
        following_token = (
            lexical_tokens(following_match.group(0))[0]
            if following_match is not None
            and lexical_tokens(following_match.group(0))
            else ""
        )
        surface_action = match.group(0).lower()
        finite_third_person = (
            surface_action.endswith("s") and not surface_action.endswith("ss")
        )
        that_relative_clause = (
            previous_token == "that"
            and (
                finite_third_person
                or following_match is None
                or following_token
                in (
                    OBJECT_BREAKS
                    | LEADING_OBJECT_PREPOSITIONS
                    | ACTION_MODIFIERS
                    | OBJECT_DETERMINERS
                )
            )
        )
        relative_subject = (
            previous_token in {"which", "who"} or that_relative_clause
        )
        demonstrative_subject = (
            previous_token in {"this", "that", "these", "those"}
            and (
                finite_third_person
                or following_token
                in (OBJECT_DETERMINERS | {"that"})
            )
        )
        if (
            previous_token in {"a", "an", "the", "this", "that", "these", "those"}
            and not relative_subject
            and not demonstrative_subject
        ):
            # ``the open case`` is a state adjective, not an instruction to open.
            # ``the case that closes`` is a finite relative clause and remains
            # real action evidence. Demonstratives can instead be pronoun
            # subjects: ``This opens ...`` and ``Those close the doors``.
            continue

        object_terms, pronoun_object = _direct_object_identity(
            text, token_matches, index, canonical_action
        )
        if not object_terms:
            if pronoun_object:
                object_terms = _resolve_pronoun_object(text, token_matches, index)
            else:
                object_terms = _subject_object_identity(
                    text, token_matches, index
                )

        mentions.append({
            "action": canonical_action,
            "start": match.start(),
            "end": match.end(),
            "positive": not _action_match_is_negated(text, token_matches, index),
            "objects": object_terms,
            "pronoun": pronoun_object,
        })

    return tuple(
        (
            str(mention["action"]),
            int(mention["start"]),
            int(mention["end"]),
            bool(mention["positive"]),
            tuple(mention["objects"]),
        )
        for mention in mentions
    )


def _action_objects_compatible(
    left: tuple[str, int, int, bool, tuple[str, ...]],
    right: tuple[str, int, int, bool, tuple[str, ...]],
    *,
    left_requires_object: bool = True,
) -> bool:
    left_objects, right_objects = left[4], right[4]
    if not left_requires_object:
        return True
    if not left_objects and not right_objects:
        return True
    if not left_objects or not right_objects:
        return False
    # Object identities always encode the grammatical head last.  Required
    # pre/postnominal discriminators must survive on that same head.
    return (
        left_objects[-1] == right_objects[-1]
        and set(left_objects[:-1]).issubset(right_objects[:-1])
    )


def _mention_has_explicit_object(
    text: str,
    mention: tuple[str, int, int, bool, tuple[str, ...]],
) -> bool:
    """Return whether a mention binds a direct/destination object in text."""
    token_matches = list(TOKEN.finditer(text))
    for index, match in enumerate(token_matches):
        if match.start() != mention[1]:
            continue
        direct, pronoun = _direct_object_identity(
            text, token_matches, index, mention[0]
        )
        if direct or pronoun:
            return True
        if re.match(r"\s+(?:down|up)\b", text[match.end():], re.I):
            # Phrasal scene-level actions (``the librarian closes up``) do not
            # make the grammatical subject an action object.
            return False
        return bool(mention[4])
    return False


def missing_positive_action_requirements(
    brief: str,
    prompt: str,
) -> tuple[str, ...]:
    """Return explicit positive brief actions absent on a compatible object."""
    required = [mention for mention in action_mentions(brief) if mention[3]]
    supplied = [mention for mention in action_mentions(prompt) if mention[3]]
    missing: set[str] = set()
    for mention in required:
        requires_object = _mention_has_explicit_object(brief, mention)
        if any(
            candidate[0] == mention[0]
            and _action_objects_compatible(
                mention,
                candidate,
                left_requires_object=requires_object,
            )
            for candidate in supplied
        ):
            continue
        object_label = " ".join(mention[4])
        missing.add(
            f"{mention[0]} {object_label}".strip()
        )
    return tuple(sorted(missing))


def reversed_action_requirements(brief: str, prompt: str) -> tuple[str, ...]:
    """Return brief actions replaced solely by their explicit opposites.

    Shared subjects, props, colours, and locations cannot compensate for an
    inverted requested endpoint. A prompt that still contains the requested
    action is not rejected here: it may be describing a legitimate sequence.
    """
    brief_mentions = [mention for mention in action_mentions(brief) if mention[3]]
    prompt_mentions = [mention for mention in action_mentions(prompt) if mention[3]]
    reversals: set[str] = set()

    for pair in OPPOSITE_ACTIONS:
        for brief_mention in (
            mention for mention in brief_mentions if mention[0] in pair
        ):
            required_action = brief_mention[0]
            opposite_action = next(iter(pair - {required_action}))
            requires_object = _mention_has_explicit_object(brief, brief_mention)
            required_survives = any(
                mention[0] == required_action
                and _action_objects_compatible(
                    brief_mention,
                    mention,
                    left_requires_object=requires_object,
                )
                for mention in prompt_mentions
            )
            opposite_survives = any(
                mention[0] == opposite_action
                and _action_objects_compatible(
                    brief_mention,
                    mention,
                    left_requires_object=requires_object,
                )
                for mention in prompt_mentions
            )
            if not required_survives and opposite_survives:
                reversals.add(f"{required_action}->{opposite_action}")
    return tuple(sorted(reversals))


def shot_count_contract(text: str) -> int | None:
    match = COUNTED_SHOT_REQUEST.search(text)
    if match:
        token = match.group("count").lower()
        return int(token) if token.isdigit() else COUNT_WORDS[token]
    markers = {int(match.group("count")) for match in NUMBERED_SHOT_MARKER.finditer(text)}
    if markers:
        highest = max(markers)
        if set(range(1, highest + 1)).issubset(markers):
            return highest
    return None


def production_trace_contracts(text: str) -> frozenset[str]:
    contracts: set[str] = set()
    if ANIMATION_CONTRACT.search(text):
        contracts.add("animation medium")
    if shot_count := shot_count_contract(text):
        contracts.add(f"{shot_count}-part shot structure")
    has_endpoint_transition = (
        FROM_TO_CONTRACT.search(text)
        or (START_ENDPOINT.search(text) and END_ENDPOINT.search(text))
    )
    if has_endpoint_transition and TRANSITION_CONTRACT.search(text):
        contracts.add("first-to-final state transition")
    if LIGHTING_EDIT_CONTRACT.search(text):
        contracts.add("lighting-only edit target")
    if SOURCE_PRESERVATION_CONTRACT.search(text):
        contracts.add("preserve otherwise accepted source")
    return frozenset(contracts)


def semantic_trace_anchors(brief: str, prompt: str) -> tuple[str, ...]:
    """Return paired production contracts expressed with different wording."""
    return tuple(sorted(
        production_trace_contracts(brief) & production_trace_contracts(prompt)
    ))


def score_brief_traceability(brief: str, prompt: str) -> tuple[float, str]:
    """Require target evidence independently from structural contracts."""
    brief_terms = target_trace_terms(brief)
    prompt_terms = affirmative_trace_terms(prompt)
    matched = sorted(brief_terms & prompt_terms)
    semantic = semantic_trace_anchors(brief, prompt)
    explicit_target_clauses = explicit_target_requirement_clauses(brief)
    missing_clauses = [
        clause
        for clause in explicit_target_clauses
        if not any(group.issubset(prompt_terms) for group in clause)
    ]
    if missing_clauses:
        closest_group = min(
            (group for clause in missing_clauses for group in clause),
            key=lambda group: (len(group - prompt_terms), sorted(group)),
        )
        missing_targets = sorted(closest_group - prompt_terms)
        return 0.0, (
            "requested target changed or disappeared; missing: "
            + ", ".join(missing_targets)
        )
    action_reversals = reversed_action_requirements(brief, prompt)
    if action_reversals:
        return 0.0, (
            "requested action reversed: " + ", ".join(action_reversals)
        )
    missing_actions = missing_positive_action_requirements(brief, prompt)
    if missing_actions:
        return 0.0, (
            "requested positive action missing: " + ", ".join(missing_actions)
        )
    evidence_count = len(matched) + len(semantic)
    if not brief_terms and not semantic:
        return 0.0, "brief has no usable non-generic material to trace"
    if brief_terms and not matched:
        return 0.0, (
            "no target-specific material survives; expected one of: "
            + ", ".join(sorted(brief_terms)[:6])
        )
    if not brief_terms:
        if len(semantic) >= 2:
            return 4.0, (
                "brief trace carried through (contracts: "
                + ", ".join(semantic)
                + ")"
            )
        return 2.0, (
            "only one production contract survives and no target evidence is "
            f"available: {semantic[0]}"
        )
    if evidence_count >= 2:
        parts = []
        if matched:
            parts.append(f"terms: {', '.join(matched)}")
        if semantic:
            parts.append(f"contracts: {', '.join(semantic)}")
        return 4.0, f"brief trace carried through ({'; '.join(parts)})"
    if len(matched) == 1 and not semantic and len(brief_terms) <= 3:
        anchor = matched[0] if matched else semantic[0]
        return 3.0, f"one brief-specific anchor carried through: {anchor}"
    if evidence_count:
        missing = sorted(brief_terms - prompt_terms)
        anchor = matched[0] if matched else semantic[0]
        return 2.0, (
            f"only one brief-specific anchor survives: {anchor}; "
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


@lru_cache(maxsize=4096)
def _quoted_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Return balanced dialogue/code spans across common writing systems.

    Only balanced pairs hide evidence.  This prevents one stray quote from
    swallowing the rest of a prompt, while supporting multilingual guillemets,
    CJK corner brackets, German low quotes, and Markdown code quotations.
    """
    spans: list[tuple[int, int]] = []
    occupied: set[int] = set()

    def add_asymmetric(opener: str, closer: str) -> None:
        cursor = 0
        while True:
            start = text.find(opener, cursor)
            while start != -1 and any(
                position in occupied
                for position in range(start, start + len(opener))
            ):
                start = text.find(opener, start + len(opener))
            if start == -1:
                return
            end = text.find(closer, start + len(opener))
            while end != -1 and any(
                position in occupied
                for position in range(end, end + len(closer))
            ):
                end = text.find(closer, end + len(closer))
            if end == -1:
                return
            spans.append((start, end + len(closer)))
            occupied.update(range(start, start + len(opener)))
            occupied.update(range(end, end + len(closer)))
            cursor = end + len(closer)

    def add_symmetric(mark: str, *, apostrophe_aware: bool = False) -> None:
        candidates: list[int] = []
        cursor = 0
        while True:
            index = text.find(mark, cursor)
            if index == -1:
                break
            cursor = index + len(mark)
            if any(
                position in occupied
                for position in range(index, index + len(mark))
            ):
                continue
            if mark == '"' and index and text[index - 1] == "\\":
                continue
            if apostrophe_aware:
                previous = text[index - 1] if index else " "
                following_index = index + len(mark)
                following = (
                    text[following_index]
                    if following_index < len(text)
                    else " "
                )
                if previous.isalnum() and following.isalnum():
                    continue
                if len(candidates) % 2 == 0:
                    # Measurements and possessives resemble closing apostrophes,
                    # not the opening edge of quoted dialogue.
                    if previous.isalnum() or following.isspace():
                        continue
                elif previous.isspace():
                    continue
            candidates.append(index)
        for start, end in zip(candidates[::2], candidates[1::2]):
            spans.append((start, end + len(mark)))
            occupied.update(range(start, start + len(mark)))
            occupied.update(range(end, end + len(mark)))

    # Resolve the one ambiguous curly character first: it closes German-style
    # low quotes but opens English-style curly quotes.
    add_asymmetric("„", "“")
    add_asymmetric("‚", "‘")
    for opener, closer in (
        ("“", "”"),
        ("‘", "’"),
        ("«", "»"),
        ("「", "」"),
        ("『", "』"),
        ("《", "》"),
        ("〈", "〉"),
        ("〝", "〞"),
        ("‹", "›"),
    ):
        add_asymmetric(opener, closer)
    add_symmetric("``")
    add_symmetric('"')
    add_symmetric("'", apostrophe_aware=True)
    add_symmetric("`", apostrophe_aware=True)
    return tuple(sorted(spans))


def position_is_quoted(text: str, position: int) -> bool:
    """Return whether a control word is inside a balanced quoted span."""
    return any(start < position < end for start, end in _quoted_spans(text))


def named_positive_directives(
    text: str,
    families: dict[str, re.Pattern[str]],
    *,
    ignore_quoted: bool = False,
) -> list[tuple[str, int, int]]:
    directives = {
        (name, match.start(), match.end())
        for name, pattern in families.items()
        for match in pattern.finditer(text)
        if not match_is_negated(text, match.start())
        and not (ignore_quoted and position_is_quoted(text, match.start()))
    }
    return sorted(directives, key=lambda item: (item[1], item[2], item[0]))


def positive_families(
    text: str,
    families: dict[str, re.Pattern[str]],
    *,
    ignore_quoted: bool = False,
) -> set[str]:
    return {
        name
        for name, _, _ in named_positive_directives(
            text, families, ignore_quoted=ignore_quoted
        )
    }


def positive_positions(
    text: str,
    families: dict[str, re.Pattern[str]],
    *,
    ignore_quoted: bool = False,
) -> list[tuple[int, int]]:
    return [
        (start, end)
        for _, start, end in named_positive_directives(
            text, families, ignore_quoted=ignore_quoted
        )
    ]


def named_positive_positions(
    text: str,
    families: dict[str, re.Pattern[str]],
    names: set[str],
    *,
    ignore_quoted: bool = False,
) -> list[tuple[int, int]]:
    return positive_positions(
        text,
        {name: pattern for name, pattern in families.items() if name in names},
        ignore_quoted=ignore_quoted,
    )


def directive_pair_is_sequenced(
    text: str,
    left: tuple[int, int],
    right: tuple[int, int],
) -> bool:
    (left_start, left_end), (right_start, right_end) = sorted((left, right))
    # A simultaneity qualifier can follow the final directive, outside its
    # regex match. Inspect only the remainder of its local clause so an
    # unrelated cue in a later sentence cannot poison a valid transition.
    local_end_match = re.search(r"[.;!?。！？；\n]", text[right_end:])
    local_end = (
        right_end + local_end_match.start()
        if local_end_match
        else len(text)
    )
    if TRAILING_SIMULTANEOUS_CUE.fullmatch(text[right_end:local_end]):
        return False
    bridge = text[left_end:right_start]
    if DIRECT_SIMULTANEOUS_BRIDGE.fullmatch(bridge):
        return False
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


def directives_are_sequenced(
    text: str,
    positions: list[tuple[int, int]],
) -> bool:
    """Return true only when every adjacent directive changes phase."""
    ordered = sorted(set(positions))
    if len(ordered) < 2:
        return False
    return all(
        directive_pair_is_sequenced(text, left, right)
        for left, right in zip(ordered, ordered[1:])
    )


def directive_phase_families(
    text: str,
    directives: list[tuple[str, int, int]],
) -> list[set[str]]:
    """Partition directives by explicit pair-local sequence boundaries."""
    if not directives:
        return []
    ordered = sorted(set(directives), key=lambda item: (item[1], item[2], item[0]))
    phases: list[set[str]] = [{ordered[0][0]}]
    previous = (ordered[0][1], ordered[0][2])
    for name, start, end in ordered[1:]:
        current = (start, end)
        if directive_pair_is_sequenced(text, previous, current):
            phases.append({name})
        else:
            phases[-1].add(name)
        previous = current
    return phases


def scoped_contradiction_findings(text: str) -> list[str]:
    """Find conflicts inside pair-local directive phases for one text scope."""
    findings: list[str] = []

    camera_directives = named_positive_directives(
        text, CAMERA_FAMILIES, ignore_quoted=True
    )
    for phase in directive_phase_families(text, camera_directives):
        dynamic = phase - {"locked"}
        if "locked" in phase and dynamic:
            findings.append(
                "camera: locked/static framing conflicts with simultaneous "
                + ", ".join(sorted(dynamic))
            )
            break
        if len(dynamic) >= 3:
            findings.append(
                "camera: three or more simultaneous move families are stacked: "
                + ", ".join(sorted(dynamic))
            )
            break
        if {"push", "pull"}.issubset(dynamic):
            findings.append("camera: simultaneous push-in and pull-out directives")
            break

    light_directives = named_positive_directives(
        text, LIGHT_SOURCE_FAMILIES, ignore_quoted=True
    )
    light_phases = directive_phase_families(text, light_directives)
    exclusive_light = re.search(
        r"\b(single|sole|only)\b[^.;]{0,80}\b(light|lit|sources?)\b",
        text,
        re.I,
    )
    for phase in light_phases:
        if len(phase) >= 2 and exclusive_light:
            findings.append(
                "light: an exclusive source claim names simultaneous sources: "
                + ", ".join(sorted(phase))
            )
            break
        if len(phase) >= 3:
            findings.append(
                "light: three or more unphased source families are stacked: "
                + ", ".join(sorted(phase))
            )
            break

    sound_directives = named_positive_directives(
        text, SOUND_LAYER_FAMILIES, ignore_quoted=True
    )
    sound_directives.extend(
        ("silence", match.start(), match.end())
        for match in SILENCE.finditer(text)
        if not match_is_negated(text, match.start())
        and not position_is_quoted(text, match.start())
    )
    for phase in directive_phase_families(text, sound_directives):
        layers = phase - {"silence"}
        if "silence" in phase and layers:
            findings.append(
                "sound: silence conflicts with simultaneous layers: "
                + ", ".join(sorted(layers))
            )
            break
        if len(layers) >= 5:
            findings.append(
                "sound: five or more unphased layers are stacked: "
                + ", ".join(sorted(layers))
            )
            break

    action_families = {
        "still": STILL_ACTION,
        "continuing": CONTINUING_ACTION,
    }
    action_directives = named_positive_directives(
        text, action_families, ignore_quoted=True
    )
    if any(
        {"still", "continuing"}.issubset(phase)
        for phase in directive_phase_families(text, action_directives)
    ):
        findings.append("action: stillness conflicts with continuing locomotion")
    return findings


def contradiction_findings(prompt: str) -> list[str]:
    """Find explicit incompatibilities without interpreting creative intent."""
    findings: list[str] = []
    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?;])\s+", prompt)
        if part.strip()
    ]
    for sentence in sentences:
        findings.extend(scoped_contradiction_findings(sentence))

    # Punctuation must not hide an unphased pair. Re-run across the whole
    # prompt, but add at most one finding per category already found locally.
    for finding in scoped_contradiction_findings(prompt):
        category = finding.split(":", 1)[0] + ":"
        if not any(existing.startswith(category) for existing in findings):
            findings.append(finding)

    added_audio = any(
        not match_is_negated(prompt, match.start())
        and not position_is_quoted(prompt, match.start())
        for match in ADDED_AUDIO.finditer(prompt)
    )
    unchanged_audio = any(
        not position_is_quoted(prompt, match.start())
        for match in UNCHANGED_AUDIO.finditer(prompt)
    )
    if unchanged_audio and added_audio:
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
def bounded_requirement_delta(left: str, right: str) -> bool:
    """Detect a small changed production requirement in otherwise shared briefs.

    A Jaccard cutoff is weakest exactly where duplicate detection matters most:
    one changed subject, material, colour, location, lens, duration, or other
    content token inside a heavily shared brief. Compare the residual content
    requirements directly, including one-sided additions, while excluding
    grammar and delivery adverbs. This is category-agnostic rather than a colour
    vocabulary or a fixture exception.
    """
    ignored = (
        FUNCTION_WORDS
        | PRODUCTION_GENERIC
        | TRACE_GENERIC
        | TARGET_CONTROL_TERMS
        | ACTION_MODIFIERS
    )

    def requirements(text: str) -> Counter[str]:
        return Counter(
            token
            for token in lexical_tokens(text)
            if token not in ignored
            and not token.endswith("ly")
            and (len(token) > 2 or token.isdigit())
        )

    left_counts = requirements(left)
    right_counts = requirements(right)
    shared = left_counts & right_counts
    left_delta = left_counts - right_counts
    right_delta = right_counts - left_counts
    residual_count = sum(left_delta.values()) + sum(right_delta.values())
    if residual_count == 0 or len(shared) < 2:
        return False
    # Larger rewrites are already handled by the set-similarity branch below;
    # this branch exists for the narrow high-overlap blind spot.
    return residual_count <= 4


@lru_cache(maxsize=8192)
def materially_different_briefs(left: str, right: str) -> bool:
    if normalized_prompt(left) == normalized_prompt(right):
        return False
    if opposite_action_mutation(left, right):
        return True
    if bounded_requirement_delta(left, right):
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

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
from bisect import bisect_left, bisect_right
from collections import Counter
from functools import lru_cache
from typing import NamedTuple
from pathlib import Path

if __package__:
    from .strict_json import (
        diagnostic_text,
        load_json,
        validate_repo_input_path,
    )
else:
    from strict_json import (
        diagnostic_text,
        load_json,
        validate_repo_input_path,
    )

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
    "elderly": "old",
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
    "older": "old",
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
NUMBERED_PHASE_LABEL = re.compile(
    r"\b(?:act|beat|moment|part|phase|scene|shot|take)\s*"
    r"(?:(?:#|no\.?|number)\s*)?"
    r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    r"nineteen|twenty|i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|"
    r"xv|xvi|xvii|xviii|xix|xx)\b",
    re.I,
)
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
OUTPUT_ENTITY_TARGET_INTRO = re.compile(
    r"\b(?:the\s+)?(?:output|result)\s*"
    r"(?::|is|shows?|depicts?|features?)\s+"
    r"(?:(?:a|an|another|the)\s+)?",
    re.I,
)
BASE_OUTPUT_TARGET_INTRO = re.compile(
    r"\bbase\s+(?:(?:a|an|the)\s+)?"
    r"(?=(?:[A-Za-z0-9'-]+\s+){1,8}"
    r"(?:animation|clip|frame|image|portrait|render|sequence|shot|storyboard|"
    r"take|video)\s+on\b)",
    re.I,
)
DIRECT_ENTITY_TARGET_INTRO = re.compile(
    r"\b(?:animate|build|compose|create|deliver|depict|draft|generate|make|"
    r"portray|produce|render|show|star)\s+"
    r"(?!(?:(?:a|an|another|the)\s+)?(?:[A-Za-z0-9-]+\s+){0,2}"
    r"(?:animation|clip|frame|image|portrait|render|sequence|shot|"
    r"storyboard|take|video)\b)"
    r"(?!(?:based|from|into|using|with)\b)"
    r"(?:(?:a|an|another|the)\s+)?(?=[A-Za-z0-9])",
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
TARGET_TRAILING_SOURCE = re.compile(
    r"\b(?:based\s+on|from|using)\b|"
    r"\bon\s+(?=(?:(?:a|an|the)\s+)?(?:footage|image|input|photo|"
    r"photograph|reference|source|video)\b)",
    re.I,
)
OUTPUT_INCLUDED_SUBJECT = re.compile(
    r"\b(?:do|does|did)\s+not\s+(?:exclude|omit|remove)\s+"
    r"(?:(?:a|an|the)\s+)?(?P<subject>[^,;.!?\n]+)",
    re.I,
)
SOURCE_ROLE_NOUN_TEXT = (
    r"(?:clips?|footage|images?|inputs?|photos?|photographs?|references?|"
    r"sources?|stills?|videos?)"
)
SOURCE_ROLE_NOUN = re.compile(r"\b" + SOURCE_ROLE_NOUN_TEXT + r"\b", re.I)
SOURCE_OUTPUT_VERB_TEXT = (
    r"(?:animate|build|compose|create|deliver|depict|draft|generate|make|"
    r"produce|render|show)"
)
SOURCE_LABEL_DESCRIPTION = re.compile(
    r"(?:^|[.;!?。！？；\n])\s*"
    r"(?:references?(?:\s+(?:clips?|footage|images?|photos?|videos?))?|"
    r"inputs?|sources?(?:\s+(?:clips?|footage|images?|videos?))?)\s*[:：]\s*"
    r"(?P<source>[^,，;；.!?。！？\n]+)",
    re.I,
)
SOURCE_ROLE_CONTAINS = re.compile(
    r"\b(?:the\s+)?(?:inputs?|references?|"
    r"sources?(?:\s+(?:clips?|footage|images?|videos?))?)"
    r"\s+(?:contains?|is|are)\s+(?P<source>[^,，;；.!?。！？\n]+)",
    re.I,
)
SOURCE_SUBJECT_IN_ROLE = re.compile(
    r"(?P<source>[^,;.!?\n]{1,240}?)\s+(?:is|are)\s+"
    r"(?:(?:visible|shown)\s+only\s+)?in\s+(?:the\s+)?"
    r"(?:inputs?|references?|sources?)\b",
    re.I,
)
SOURCE_ROLE_DEPICTS = re.compile(
    r"\b(?:the\s+)?(?:inputs?|references?|"
    r"sources?(?:\s+(?:clips?|footage|images?|videos?))?)"
    r"\s*[,]?\s*(?:which\s+)?(?:contains?|depicts?|features?|shows?|showing)\s+"
    r"(?P<source>[^,;.!?\n]+)",
    re.I,
)
SOURCE_MODEL_RECEIVES = re.compile(
    r"\b(?:generator|model|system)\s+receives?\s+"
    r"(?:(?:a|an|the)\s+)?" + SOURCE_ROLE_NOUN_TEXT + r"(?:\s+of)?\s+"
    r"(?P<source>[^,;.!?\n]+?)(?=\s+(?:and\s+)?"
    + SOURCE_OUTPUT_VERB_TEXT + r"s?\b|[,;.!?\n]|$)",
    re.I,
)
SOURCE_GOVERNED_LEADING = re.compile(
    r"\b(?:from|given|using|with)\s+(?P<source>[^,;.!?\n]+?)"
    r"(?=\s+as\s+(?:(?:a|the)\s+)?(?:input|reference)\b|"
    r",\s*" + SOURCE_OUTPUT_VERB_TEXT + r"\b)",
    re.I,
)
SOURCE_GOVERNED_IMPERATIVE = re.compile(
    r"\b(?:take|use)\s+(?P<source>[^,;.!?\n]+?)\s+"
    r"(?=(?:as\s+(?:(?:a|the)\s+)?(?:input|reference)(?:\s+to)?|and)\s+"
    + SOURCE_OUTPUT_VERB_TEXT + r"\b)",
    re.I,
)
SOURCE_ONLY_INSPIRATION = re.compile(
    r"\buse\s+(?P<source>[^,;.!?\n]+?)\s+only\s+as\s+"
    r"(?:motion|style|visual)\s+(?:guide|guidance|inspiration|reference)\b",
    re.I,
)
SOURCE_ONLY_PURPOSE = re.compile(
    r"\buse\s+(?P<source>[^,;.!?\n]*\b" + SOURCE_ROLE_NOUN_TEXT
    + r"\b[^,;.!?\n]*?)\s+(?:only|solely)\s+to\b",
    re.I,
)
SOURCE_ASSET_CONTAINS = re.compile(
    r"(?P<source>[^,;.!?\n]{1,240}?)\s+"
    r"(?:appears?|is\s+(?:depicted|shown|visible))"
    r"\s+in\s+@(?:image|video)\s*\d+\b",
    re.I,
)
SOURCE_ASSET_DEPICTS = re.compile(
    r"@(?:image|video)\s*\d+\s*[,]?\s*"
    r"(?:which\s+)?(?:depicting|depicts?|featuring|features?|shows?|showing)\s+"
    r"(?P<source>[^,;.!?\n]+)",
    re.I,
)
SOURCE_TREATED_AS_INPUT = re.compile(
    r"\btreat\s+(?P<source>[^,;.!?\n]*\b" + SOURCE_ROLE_NOUN_TEXT
    + r"\b[^,;.!?\n]*?)\s+as\s+(?:(?:a|the)\s+)?"
    r"(?:motion|style|visual)\s+(?:guide|guidance|input|reference)\b",
    re.I,
)
SOURCE_CONSULTED = re.compile(
    r"\b(?:consult|referenc(?:es|ed|ing))\s+"
    r"(?P<source>[^,;.!?\n]*\b" + SOURCE_ROLE_NOUN_TEXT
    + r"\b[^,;.!?\n]*)",
    re.I,
)
SOURCE_FED_TO_MODEL = re.compile(
    r"\bfeed\s+(?P<source>[^,;.!?\n]*\b" + SOURCE_ROLE_NOUN_TEXT
    + r"\b[^,;.!?\n]*?)\s+into\s+(?:(?:a|the)\s+)?"
    r"(?:generator|model|system)\b",
    re.I,
)
SOURCE_PROMPTED_MODEL = re.compile(
    r"\bprompt\s+(?:(?:a|the)\s+)?(?:generator|model|system)\s+with\s+"
    r"(?P<source>[^,;.!?\n]*\b" + SOURCE_ROLE_NOUN_TEXT
    + r"\b[^,;.!?\n]*)",
    re.I,
)
SOURCE_STILL_INFORMS = re.compile(
    r"(?P<source>[^,;.!?\n]{1,240}?\bstill)\s+informs?\s+"
    r"(?:(?:a|an|the)\s+)?(?:[A-Za-z0-9'-]+\s+){0,8}"
    r"(?:animation|clip|image|output|render|result|video)\b",
    re.I,
)
SOURCE_ROLE_SUBJECT = re.compile(
    r"(?P<source>[^;.!?\n]{1,240}?\b" + SOURCE_ROLE_NOUN_TEXT
    + r"\b[^;.!?\n]{0,160}?)\s+"
    r"(?:controls?|determines?|feeds?|guides?|provides?|suppl(?:y|ies)|"
    r"is\s+(?:the\s+)?(?:motion|style|visual)\s+(?:guide|reference)\s+for)\b",
    re.I,
)
SOURCE_ALWAYS_TRAILING = re.compile(
    r"\b(?:based\s+(?:on|upon)|informed\s+by|inspired\s+by|"
    r"patterned\s+after)\s+"
    r"(?P<source>[^,;.!?\n]+)",
    re.I,
)
SOURCE_ROLE_TRAILING = re.compile(
    r"\b(?:from|on|using|with)\s+"
    r"(?P<source>[^,;.!?\n]*?\b" + SOURCE_ROLE_NOUN_TEXT
    + r"\b[^,;.!?\n]*?)"
    r"(?=\s+(?:for|onto|to)\s+(?:(?:a|an|the)\s+)?"
    r"(?:[A-Za-z0-9'-]+\s+){0,8}"
    r"(?:animation|clip|frame|image|output|portrait|render|result|sequence|"
    r"shot|storyboard|take|video)\b|[,;.!?\n]|$)",
    re.I,
)
TARGET_PHRASE_BREAKS = {
    "after", "as", "at", "before", "during", "for", "in", "inside",
    "instead", "near", "on", "outside", "rather", "that", "than",
    "under", "versus", "vs", "when", "where", "which", "while", "who", "whose",
    "with",
}
TARGET_ALTERNATIVE = "or"
MAX_EXPLICIT_TARGET_REQUIREMENTS = 8
TARGET_IDENTITY_MARKERS = {"call", "nam"}
TARGET_FORMAT_TERMS = {"portrait_photo", "still"}
COORDINATION_DEGREE_MODIFIERS = {
    "bright", "deep", "dark", "light", "pale", "very",
}
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
    r"(?:next|following|subsequent|first|second|third|fourth|fifth|sixth|seventh|"
    r"eighth|ninth|tenth|\d+)"
)
PHASE_NUMBER = (
    r"(?:(?:#|no\.?|number)\s*)?"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv|xvi|xvii|xviii|"
    r"xix|xx|\d+)"
)
PHASE_NOUN = r"(?:act|beat|moment|part|phase|scene|shot|take)"
PHASE_SEPARATOR = (
    r"(?:\s*[.!?。！？，,;:；：]\s*|\s*[-\u2013\u2014]{1,2}\s*|\s+)"
)
DIRECT_SEQUENCE_BRIDGE = re.compile(
    r"^\s*(?:[.!?。！？，,;:；：]|[-\u2013\u2014]{1,2})?\s*(?:and\s+)?"
    r"(?:"
    r"(?:(?:then|next|later|finally|followed by)|(?:before|after))"
    + PHASE_SEPARATOR
    + r"|(?:in|on)\s+(?:the\s+)?"
    + PHASE_ORDINAL
    + r"\s+"
    + PHASE_NOUN
    + PHASE_SEPARATOR
    + r"|(?:(?:the\s+)?"
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
SEMANTIC_EVENT_TRANSITION_PATTERNS = (
    # A bounded matrix of state-change predicates.  Each family must carry a
    # directional complement; a bare ``the light fades`` is not a phase cue.
    r"fad(?:e|es|ed|ing)(?:\s+out)?\s+(?:to|into)",
    r"dissolv(?:e|es|ed|ing)\s+(?:to|into)",
    r"(?:blend|melt|morph|shift|transform)(?:s|ed|ing)?\s+(?:to|into)",
    r"cross[-\s]?fad(?:e|es|ed|ing)\s+(?:to|into)",
    r"cut(?:s|ting)?\s+(?:to|into)",
    r"(?:eas|resolv|switch)(?:e|es|ed|ing)?\s+(?:to|into)",
    r"wip(?:e|es|ed|ing)\s+(?:to|into)",
    r"transition(?:s|ed|ing)?\s+(?:to|into)",
    r"chang(?:e|es|ed|ing)\s+(?:to|into)",
    # Succession and hand-off predicates express the same temporal boundary
    # without relying on one fixture phrase such as ``gives way to``.
    r"(?:give(?:s|n)?|gave|giving)\s+way\s+to",
    r"yield(?:s|ed|ing)?\s+to",
    r"hand(?:s|ed|ing)?\s+off\s+to",
    r"pass(?:es|ed|ing)?\s+(?:on\s+)?to",
    # Passive replacement is directional only with an explicit ``by``.
    r"(?:am|are|be|been|being|is|was|were)\s+"
    r"(?:replaced|superseded|succeeded)\s+by",
)
SEMANTIC_EVENT_TRANSITION_CUE = re.compile(
    r"\b(?:" + "|".join(SEMANTIC_EVENT_TRANSITION_PATTERNS) + r")\b",
    re.I,
)
SEMANTIC_EVENT_TRANSITION_LEAD = re.compile(
    r"^\s*(?:[.!?\u2026\u061f\u3002\uff01\uff1f\uff0c,;:\uff1b\uff1a]|"
    r"[-\u2013\u2014]{1,2})?\s*"
    r"(?:and\s+)?(?:then\s+)?"
    r"(?:(?:(?:as|when)\s+)?(?:the\s+)?"
    r"(?:frame|framing|image|lighting|light|motion|music|picture|scene|shot|"
    r"silence|sound|state|stillness|view)\s+|(?:it|that|which)\s+)?"
    r"(?:then\s+)?"
    r"(?:(?:abruptly|cleanly|finally|gradually|gently|seamlessly|slowly|"
    r"smoothly|visibly)\s+){0,2}$",
    re.I,
)
SEMANTIC_EVENT_TRANSITION_BLOCKER = re.compile(
    r"\b(?:at\s+the\s+same\s+time|concurrent(?:ly)?|if|meanwhile|"
    r"simultaneous(?:ly)?|together|unless|while|would|could|might|may|should)\b",
    re.I,
)
SEMANTIC_EVENT_TRANSITION_COMPLETED_TAIL = re.compile(
    r"\s+(?:(?:a|an|the)\s+)?"
    r"(?:[A-Za-z0-9][A-Za-z0-9'\u2019-]*\s+){0,5}"
    r"[A-Za-z0-9][A-Za-z0-9'\u2019-]*\s*"
    r"(?:[.!?\u2026\u061f\u3002\uff01\uff1f\uff1b;:]|[-\u2013\u2014]{1,2})\s*"
    r"(?:then\s+)?"
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
EXPLICIT_PHASE_LABEL = re.compile(
    r"\b(?:"
    + PHASE_NOUN
    + r"\s*"
    + PHASE_NUMBER
    + r"|(?:the\s+)?"
    + PHASE_ORDINAL
    + r"\s+"
    + PHASE_NOUN
    + r")\b",
    re.I,
)
PHASE_CUE_TAIL = re.compile(
    r"\s*(?::|,|[-\u2013\u2014])?\s*"
    r"(?:(?:uses?|features?|shows?|has|switches?(?:\s+to)?|"
    r"begins?\s+with|opens?\s+on|is(?:\s+lit\s+by)?|with)\s+)?"
    r"(?:(?:the|a|an|near|absolute|complete|completely|slow|slowly)[-\s]*){0,2}",
    re.I,
)
TRAILING_SIMULTANEOUS_CUE = re.compile(
    r"^\s*(?:[,;:]|[-\u2013\u2014]{1,2})?\s*"
    r"(?:simultaneous(?:ly)?|at the same time|all the while|meanwhile|"
    r"concurrent(?:ly)?|together|at once|throughout|all along|"
    r"during the same (?:beat|moment|phase|shot|time)|"
    r"for the (?:entire|whole) (?:beat|moment|phase|shot|transition))\s*$",
    re.I,
)
SEMANTIC_EVENT_TRANSITION_POST_BLOCKER = re.compile(
    r"\b(?:hypothetically|"
    r"in\s+(?:no\s+version|theory|(?:an?\s+)?imagined\s+version|"
    r"(?:a\s+|the\s+)?storyboard)|"
    r"as\s+(?:a\s+|the\s+)?concept\s+note|"
    r"only\s+(?:if|in\s+(?:an?\s+)?imagined\s+version|on\s+(?:a\s+|the\s+)?"
    r"(?:concept\s+note|draft|poster|screen|storyboard))|"
    r"according\s+to|claim(?:s|ed|ing)?|say(?:s|ing)?|said|"
    r"simultaneous(?:ly)?|at\s+the\s+same\s+time|all\s+along|"
    r"concurrent(?:ly)?|during\s+the\s+same\s+(?:beat|moment|phase|shot|time)|"
    r"throughout|while)\b",
    re.I,
)
NEGATED_PREFIX = re.compile(
    r"\b(?:no|not|never|neither|nor|without|do not|does not|must not|nothing from|"
    r"cannot|can['\u2019]t|could not|couldn['\u2019]t|will not|won['\u2019]t|"
    r"would not|wouldn['\u2019]t|fail(?:s|ed)? to|"
    r"refus(?:e|es|ed|ing)(?:\s+to)?|"
    r"den(?:y|ies|ied)(?:\s+the\s+request)?(?:\s+permission)?(?:\s+to)?|"
    r"(?:is|are|was|were)\s+(?:denied|forbidden|prevented)"
    r"(?:\s+permission)?(?:\s+(?:from|to))?|"
    r"(?:is|are|was|were)\s+(?:barred|prohibited)(?:\s+from)?|"
    r"declin(?:e|es|ed|ing)(?:\s+to)?|avoid(?:s|ed|ing)?|"
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
POSITIVE_WHILE_RESET = re.compile(
    r"\bwhile\b(?P<prefix>[^.;]{0,100}?)"
    r"\b(?P<predicate>illuminat\w*|lights?|casts?|glows?|shines?|provides?)\b",
    re.I,
)
PREDICATE_COORDINATION_BOUNDARY = re.compile(
    r",|\b(?:and|but|however|then|whereas)\b",
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
    r"not\s+(?:shown|seen|included|present|depicted|featured)"
    r"(?=\s*(?:$|[.;!?。！？；]|(?:from|in|inside|outside|within)\s+"
    r"(?:the\s+)?(?:animation|clip|frame|output|scene|shot|video)\b))|"
    r"(?:absent|missing|excluded|omitted)"
    r"(?=\s*(?:$|[.;!?。！？；]|(?:by|from)\b|(?:in|inside|outside|within)\s+"
    r"(?:the\s+)?(?:animation|clip|frame|output|scene|shot|video)\b))|"
    r"left\s+out(?=\s*(?:$|[.;!?。！？；]|(?:from|of)\s+(?:the\s+)?"
    r"(?:animation|clip|frame|output|scene|shot|video)\b)))"
    r"|(?:do|does|did)\s+not\s+(?:appear|arrive|enter|feature|show)"
    r"(?=\s*(?:$|[.;!?。！？；]|(?:at|by|during|from|in|inside|outside|within)\b|"
    r"(?:the\s+)?(?:animation|clip|frame|output|scene|shot|video)\b))"
    r"|(?:remains?|stays?)\s+absent"
    r"|(?:has|have|had)\s+been\s+(?:excluded|omitted)"
    r"|(?:is|are|was|were)\s+nowhere\s+(?:present|seen|shown)"
    r"|never\s+(?:appears?|arrives?|enters?|features?|shows?)"
    r"(?=\s*(?:$|[.;!?。！？；]|(?:at|by|during|from|in|inside|outside|within)\b|"
    r"(?:the\s+)?(?:animation|clip|frame|output|scene|shot|video)\b))"
    r")\b",
    re.I,
)

DISPLAYED_TEXT_LEAD = re.compile(
    r"(?:\b(?:"
    r"(?:on[- ]screen|screen)\s+text|"
    r"(?:banner|caption|card|display|label|note|placard|poster|shirt|sign|title)"
    r"(?:['’]s)?"
    r")\b[^.;!?。！？；\n]{0,48}?\b(?:"
    r"read(?:s|ing)?|say(?:s|ing)?|bear(?:s|ing)?|"
    r"show(?:s|ing)?|"
    r"(?:is\s+)?(?:inscribed|label(?:ed|led)|marked|printed)\s*(?:as|with)?"
    r")\s+|\b(?:banner|caption|card|label|note|placard|sign|title)\b\s*:\s*)",
    re.I,
)
# Output-domain absence forms whose grammar is intentionally narrower than the
# legacy detector above. Keeping these typed prevents framing language such as
# ``not shown in close-up`` from erasing a subject that remains in the output.
POSTPOSITIVE_OUTPUT_ABSENCE = re.compile(
    r"(?P<subject>(?:\b[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?\b[\s-]*){1,8}?)"
    r"\s+(?:"
    r"(?:do|does|did)\s+not\s+appear(?=\s+(?:in|on)\b)|"
    r"fails?\s+to\s+appear(?=\s+(?:in|on)\b)|"
    r"(?:cannot|can['\u2019]t)\s+be\s+seen(?=\s+(?:in|on|throughout)\s+"
    r"(?:the\s+)?(?:animation|clip|frame|output|scene|video)\b)|"
    r"(?:is|are|was|were)\s+(?:offscreen\s+throughout|"
    r"invisible\s+throughout\s+(?:the\s+)?"
    r"(?:animation|clip|output|scene|video)|"
    r"not\s+visible(?=\s+(?:in|on|throughout)\s+(?:the\s+)?"
    r"(?:animation|clip|frame|output|scene|video)\b)|"
    r"nowhere\s+(?:to\s+be\s+)?(?:present|seen|shown)|"
    r"nowhere\s+in\s+(?:a|an|the)?\s*"
    r"(?:animation|clip|frame|output|scene|shot|video))|"
    r"appears?\s+only\s+in\s+(?:a|an|the)?\s*"
    r"(?:image|placard|poster|reference|shirt|sign|text)\s*,?\s*"
    r"never\s+in\s+(?:a|an|the)?\s*"
    r"(?:animation|clip|frame|output|scene|shot|video)"
    r")\b",
    re.I,
)
POSTPOSITIVE_PRESENCE_RESET = re.compile(
    r"(?:\bbut\b|;\s*however\s*,?)\s+"
    r"(?:(?:he|she|they)\s+)?(?:then\s+)?"
    r"(?:(?:is|are|was|were)\s+(?:present|shown|visible)|"
    r"appears?|arrives?|enters?|features?|moves?|sits?|stands?|walks?|waits?|"
    r"remains?\s+(?:present|visible)|stays?\s+(?:present|visible))\b",
    re.I,
)
ACTIVE_OUTPUT_ABSENCE = re.compile(
    r"\b(?:the\s+)?(?:animation|clip|frame|output|scene|shot|video)\s+"
    r"(?:(?:deliberately|entirely|explicitly|intentionally)\s+)?"
    r"(?:excludes?|omits?|leaves?\s+out)\s+"
    r"(?P<subject>(?:a|an|the)?\s*"
    r"(?:[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?[\s-]*){1,8}?)"
    r"(?=\s*(?:$|[.;!?\n]|\b(?:and|but|while)\b))",
    re.I,
)
DISPLAYED_TEXT_COLON_LEAD = re.compile(
    r"\b(?:(?:on[- ]screen)(?:\s+text)?|(?:screen\s+text)|text\s+on\s+screen|"
    r"banner|caption|card|display|label|note|placard|poster|shirt|sign|title)"
    r"\s*:\s*",
    re.I,
)
DISPLAYED_TEXT_CLAUSE_END = re.compile(
    r"\b(?:after|as|before|but|whereas|while)\b|"
    r"\b(?:at|beside|by|near|under|with)\s+(?=(?:a|an|the)\b)|"
    r"\b(?:hangs?|rests?|sits?|stands?)\s+"
    r"(?=(?:at|beside|by|in|near|on|under|with)\b)|"
    r"\band\s+(?=(?:a|an|he|she|the|they|we)\b)|"
    r"[,.;!?\n]",
    re.I,
)
DISPLAYED_TEXT_INVERSE = re.compile(
    r"(?P<text>(?:\b[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?\b[\s-]*){1,8}?)"
    r"\s+(?:is|are|was|were)\s+"
    r"(?:inscribed|label(?:ed|led)|marked|printed|written)\s+"
    r"(?:across|in|inside|on)\s+(?:a|an|the)?\s*"
    r"(?:banner|caption|card|display|label|note|placard|poster|shirt|sign|title)\b",
    re.I,
)
DISPLAYED_TEXT_APPEARS = re.compile(
    r"(?P<text>(?:\b[A-Za-z0-9]+(?:['\u2019-][A-Za-z0-9]+)?\b[\s-]*){1,8}?)"
    r"\s+appears?\s+as\s+(?:on[- ]screen|screen)\s+text\b",
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
    "now", "quietly", "quickly", "slowly", "suddenly", "together",
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


def _merge_intervals(
    spans: list[tuple[int, int]] | tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    """Return sorted, coalesced half-open spans for indexed membership tests."""
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return tuple(merged)


def _interval_index(
    spans: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return (
        tuple(start for start, _ in spans),
        tuple(end for _, end in spans),
    )


def _position_in_interval_index(
    index: tuple[tuple[int, ...], tuple[int, ...]],
    position: int,
) -> bool:
    starts, ends = index
    interval = bisect_right(starts, position) - 1
    return interval >= 0 and starts[interval] <= position < ends[interval]


@lru_cache(maxsize=4096)
def _source_description_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Index lexical material assigned to an input/reference role.

    The same actor, action, or property may legitimately appear in reference
    media while the requested output contains something else.  These bounded
    role grammars deliberately require an explicit input/source relationship;
    ordinary spatial ``from``, material ``from clay``, tools introduced by
    ``using``, and characters who literally guide or feed someone stay active.
    """
    spans: list[tuple[int, int]] = []

    def capture(pattern: re.Pattern[str], *, require_role: bool = False) -> None:
        for match in pattern.finditer(text):
            start, end = match.span("source")
            if require_role and SOURCE_ROLE_NOUN.search(text[start:end]) is None:
                continue
            spans.append((start, end))

    for pattern in (
        SOURCE_LABEL_DESCRIPTION,
        SOURCE_ROLE_CONTAINS,
        SOURCE_ROLE_DEPICTS,
        SOURCE_MODEL_RECEIVES,
        SOURCE_ONLY_INSPIRATION,
        SOURCE_ONLY_PURPOSE,
        SOURCE_ASSET_DEPICTS,
        SOURCE_TREATED_AS_INPUT,
        SOURCE_CONSULTED,
        SOURCE_FED_TO_MODEL,
        SOURCE_PROMPTED_MODEL,
        SOURCE_ALWAYS_TRAILING,
    ):
        capture(pattern)
    for pattern in (
        SOURCE_GOVERNED_LEADING,
        SOURCE_GOVERNED_IMPERATIVE,
        SOURCE_ROLE_TRAILING,
    ):
        capture(pattern, require_role=True)

    # These subject-first grammars have a deliberately flexible left edge.
    # Cheap literal/role prefilters prevent the regex engine from retrying that
    # edge at every byte of a long unrelated prompt.
    lowered = text.lower()
    if re.search(
        r"\b(?:is|are)\s+(?:(?:visible|shown)\s+only\s+)?in\s+"
        r"(?:the\s+)?(?:inputs?|references?|sources?)\b",
        text,
        re.I,
    ):
        capture(SOURCE_SUBJECT_IN_ROLE)
    if "@image" in lowered or "@video" in lowered:
        capture(SOURCE_ASSET_CONTAINS)
    if "still" in lowered and "inform" in lowered:
        capture(SOURCE_STILL_INFORMS)
    if SOURCE_ROLE_NOUN.search(text) is not None and re.search(
        r"\b(?:controls?|determines?|feeds?|guides?|provides?|"
        r"suppl(?:y|ies))\b|\bis\s+(?:the\s+)?"
        r"(?:motion|style|visual)\s+(?:guide|reference)\s+for\b",
        text,
        re.I,
    ):
        capture(SOURCE_ROLE_SUBJECT)
    return _interval_index(_merge_intervals(spans))


def _position_is_source_description(text: str, position: int) -> bool:
    return _position_in_interval_index(
        _source_description_interval_index(text), position
    )


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
    local_boundaries = tuple(
        boundary.end()
        for boundary in re.finditer(r"[,.;!?。！？；\n]", text)
    )
    for match in TOKEN.finditer(text):
        if position_is_quoted(text, match.start()) or match_is_negated(
            text, match.start()
        ) or _position_is_postpositively_excluded(
            text, match.start()
        ) or _position_is_displayed_text(
            text, match.start()
        ) or _position_is_source_description(
            text, match.start()
        ):
            continue
        boundary_index = bisect_right(local_boundaries, match.start()) - 1
        local_start = local_boundaries[boundary_index] if boundary_index >= 0 else 0
        alternative_start = max(local_start, match.start() - 128)
        if TARGET_NEGATED_ALTERNATIVE.search(
            text[alternative_start:match.start()]
        ):
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


@lru_cache(maxsize=4096)
def _postpositive_exclusion_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    spans: list[tuple[int, int]] = []
    terminal_boundaries = tuple(
        match.start() for match in re.finditer(r"[.!?。！？\n]", text)
    )
    resets = tuple(POSTPOSITIVE_PRESENCE_RESET.finditer(text))
    reset_starts = tuple(match.start() for match in resets)
    for pattern in (POSTPOSITIVE_EXCLUSION, POSTPOSITIVE_OUTPUT_ABSENCE):
        for match in pattern.finditer(text):
            if position_is_quoted(text, match.start("subject")):
                continue
            boundary_index = bisect_right(terminal_boundaries, match.end())
            local_end = (
                terminal_boundaries[boundary_index]
                if boundary_index < len(terminal_boundaries)
                else len(text)
            )
            reset_index = bisect_left(reset_starts, match.end())
            reset_bridge = (
                text[match.end():reset_starts[reset_index]]
                if reset_index < len(reset_starts)
                else ""
            )
            if (
                reset_index < len(reset_starts)
                and reset_starts[reset_index] < local_end
                and not re.search(
                    r"\b(?:as|while|whereas)\b", reset_bridge, re.I
                )
            ):
                # ``absent from the poster; however, she enters the animation``
                # asserts output presence for the same coordinated subject.
                continue
            spans.append((match.start("subject"), match.end("subject")))
    for match in ACTIVE_OUTPUT_ABSENCE.finditer(text):
        if position_is_quoted(text, match.start("subject")):
            continue
        spans.append((match.start("subject"), match.end("subject")))
    return _interval_index(_merge_intervals(spans))


def _position_is_postpositively_excluded(text: str, position: int) -> bool:
    """Return whether a subject is later asserted absent from the output."""
    return _position_in_interval_index(
        _postpositive_exclusion_interval_index(text), position
    )


@lru_cache(maxsize=4096)
def _displayed_text_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    spans: list[tuple[int, int]] = []
    leads = sorted(
        (*DISPLAYED_TEXT_LEAD.finditer(text), *DISPLAYED_TEXT_COLON_LEAD.finditer(text)),
        key=lambda match: match.start(),
    )
    for lead in leads:
        scan_end = min(len(text), lead.end() + 160)
        boundary = DISPLAYED_TEXT_CLAUSE_END.search(text, lead.end(), scan_end)
        end = boundary.start() if boundary else scan_end
        spans.append((max(0, lead.end() - 1), end))
    for pattern in (DISPLAYED_TEXT_INVERSE, DISPLAYED_TEXT_APPEARS):
        for match in pattern.finditer(text):
            spans.append((max(0, match.start("text") - 1), match.end("text")))
    return _interval_index(_merge_intervals(spans))


def _position_is_displayed_text(text: str, position: int) -> bool:
    """Return whether lexical material is merely rendered/readable copy."""
    return _position_in_interval_index(
        _displayed_text_interval_index(text), position
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


def _candidate_feeds_downstream_output(bridge: str) -> bool:
    """Return whether a production-looking noun is explicitly an input.

    The downstream output intro has already been removed from ``bridge``. The
    grammar therefore has to end at its determiner, which prevents a stray
    ``reference`` word elsewhere in the clause from suppressing a real output.
    """
    role = re.search(
        r"\b(?:as|is|acts?\s+as|serves?\s+as|used\s+as)\s+"
        r"(?:a|an|the)?\s*(?:input|(?:visual\s+)?reference|source)"
        r"(?:\s+material)?\b",
        bridge,
        re.I,
    )
    if role is not None:
        tail = bridge[role.end():]
        if re.fullmatch(
            r"\s*(?:"
            r"(?:for|to)\s+(?:(?:create|creating|generate|generating|make|making|"
            r"produce|producing|render|rendering)\s+|"
            r"(?:the\s+)?(?:creation|generation|production|rendering)\s+of\s+)?|"
            r"when\s+(?:create|creating|generate|generating|making|producing|rendering)\s+|"
            r"[,;]\s*(?:and\s+)?(?:then\s+)?"
            r"(?:create|generate|make|produce|render)\s+"
            r")(?:a|an|another|the)?\s*",
            tail,
            re.I,
        ):
            return True
    return any(
        pattern.search(bridge) is not None
        for pattern in (
            re.compile(
                r"\bprovides?\s+(?:a|an|the)?\s*reference\s+for\s+"
                r"(?:a|an|another|the)?\s*$",
                re.I,
            ),
            re.compile(
                r"\bfeeds?\s+into\s+(?:a|an|another|the)?\s*$",
                re.I,
            ),
            re.compile(
                r"\bto\s+guide\s+(?:(?:the\s+)?"
                r"(?:creation|generation|production|rendering)\s+of\s+|"
                r"(?:creating|generating|making|producing|rendering)\s+)?"
                r"(?:a|an|another|the)?\s*$",
                re.I,
            ),
            re.compile(
                r"\bguides?\s+(?:(?:the\s+)?"
                r"(?:creation|generation|production|rendering)\s+of\s+|"
                r"(?:creating|generating|making|producing|rendering)\s+)"
                r"(?:a|an|another|the)?\s*$",
                re.I,
            ),
            re.compile(
                r"\bguides?\s+(?:a|an|another|the)?\s*$",
                re.I,
            ),
            re.compile(
                r"\bguides?\s+(?:a|an|another|the)?\s*"
                r"(?:animation|clip|frame|image|portrait|render|sequence|shot|"
                r"storyboard|take|video)\s*$",
                re.I,
            ),
        )
    )


def _candidate_is_reference_description(
    text: str,
    match: re.Match[str],
    clause_start: int,
) -> bool:
    """Reject only the production noun directly owned by an asset marker.

    A source marker must be adjacent to this candidate (``reference image`` or
    ``@Image1 is an image``), or the candidate must explicitly feed a later
    output (``video ... as a source for an animation``). Merely occurring
    earlier in the clause cannot suppress a downstream requested output.
    """
    prefix = text[clause_start:match.start()]
    if re.search(
        r"\b(?:displaying|showing)\s+(?:a|an|the)?\s*$",
        prefix,
        re.I,
    ):
        # A production noun rendered inside the requested scene is not itself
        # the outer output target: ``a monitor displaying an image of X``.
        # The governing depiction intro remains eligible and carries the real
        # scene subject instead of letting the nested image replace it.
        return True

    clause_boundary = TARGET_STRONG_BOUNDARY.search(text, match.end())
    clause_end = clause_boundary.start() if clause_boundary else len(text)
    downstream_intros = sorted(
        (
            *PRODUCTION_TARGET_INTRO.finditer(text, match.end(), clause_end),
            *DEPICTION_TARGET_INTRO.finditer(text, match.end(), clause_end),
            *OUTPUT_ENTITY_TARGET_INTRO.finditer(text, match.end(), clause_end),
            *BASE_OUTPUT_TARGET_INTRO.finditer(text, match.end(), clause_end),
            *DIRECT_ENTITY_TARGET_INTRO.finditer(text, match.end(), clause_end),
        ),
        key=lambda candidate: candidate.start(),
    )
    if downstream_intros:
        candidate_to_output = text[match.end():downstream_intros[0].start()]
        if _candidate_feeds_downstream_output(candidate_to_output):
            # Directional ownership matters more than word order: in ``a
            # video of the palette as a source for an animation of Mara``, the
            # first production noun is explicitly an input and only the latter
            # animation is a requested output.
            return True

        governing_prefix = text[clause_start:match.start()]
        if re.search(
            r"(?:^|[,;:])\s*(?:based\s+on|from|given|guided\s+by|take|use|using|with)"
            r"\s+(?:a|an|the)?\s*$",
            governing_prefix,
            re.I,
        ):
            # Source direction can be governed before the production noun:
            # ``Using an image of X, create an animation of Y``.
            return True

    markers = list(TARGET_ASSET_MARKER.finditer(prefix))
    if not markers:
        return False
    latest_marker = markers[-1]
    marker_to_candidate = prefix[latest_marker.end():]
    if not re.fullmatch(
        r"\s*[,(:]?\s*(?:which\s+)?(?:(?:is|as)\s+)?(?:a|an|the)?\s*"
        r"(?:(?:clip|frame|image|portrait|shot|video)\s*)?[,(:]?\s*",
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
    depiction = [
        match
        for match in DEPICTION_TARGET_INTRO.finditer(
            text, clause_start, clause_end
        )
        if not _candidate_is_reference_description(text, match, clause_start)
    ]
    labelled_output = list(
        OUTPUT_ENTITY_TARGET_INTRO.finditer(text, clause_start, clause_end)
    )
    based_output = list(
        BASE_OUTPUT_TARGET_INTRO.finditer(text, clause_start, clause_end)
    )
    direct = list(DIRECT_ENTITY_TARGET_INTRO.finditer(text, clause_start, clause_end))
    candidates = sorted(
        (*production, *depiction, *labelled_output, *based_output, *direct),
        key=lambda candidate: (candidate.start(), candidate.end()),
    )
    eligible: list[re.Match[str]] = []
    for match in candidates:
        if not eligible or _candidate_is_coordinated(text, eligible[-1], match):
            eligible.append(match)
    return tuple(eligible)


def _split_visible_target_relations(target: str) -> tuple[str, ...]:
    """Split multi-entity output syntax into independently mandatory targets."""
    pending = [target]
    resolved: list[str] = []
    patterns = (
        re.compile(r"\b(?:alongside|beside|near)\b", re.I),
        re.compile(
            r"\b(?:displaying|showing)\s+(?:a|an|the)?\s*"
            r"(?:(?:frame|image|photo|photograph|portrait)\s+of\s+)?",
            re.I,
        ),
        re.compile(
            r"\b(?:morphing|transforming|unfolding)\s+into\b",
            re.I,
        ),
    )
    while pending:
        item = pending.pop(0).strip()
        split = None
        for pattern in patterns:
            candidate = pattern.search(item)
            if candidate is not None:
                split = candidate
                break
        if split is None:
            if item:
                resolved.append(item)
            continue
        left = item[:split.start()].strip()
        right = item[split.end():].strip()
        if not left or not right:
            resolved.append(item)
            continue
        pending[0:0] = [left, right]
    return tuple(resolved)


@lru_cache(maxsize=4096)
def _output_target_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Index the semantic payload of every explicit output target.

    Input/reference descriptions may contain the same actors, actions, props,
    and attributes as the requested result.  Once a prompt names an explicit
    output, only evidence inside these payload ranges may satisfy semantic
    actor/action/property binders.  Prompts without an explicit output retain
    their ordinary whole-text interpretation.
    """
    spans: list[tuple[int, int]] = []
    for clause_start, clause_end in _target_clause_ranges(text):
        intros = _eligible_target_intros(text, clause_start, clause_end)
        for index, match in enumerate(intros):
            target_end = clause_end
            if index + 1 < len(intros):
                target_end = min(target_end, intros[index + 1].start())
            target = text[match.end():target_end]
            trailing_source = TARGET_TRAILING_SOURCE.search(target)
            if trailing_source is not None:
                target_end = match.end() + trailing_source.start()
            if match.end() < target_end:
                spans.append((match.end(), target_end))
    return _interval_index(_merge_intervals(spans))


def _position_is_output_semantic_evidence(text: str, position: int) -> bool:
    """Reject evidence explicitly assigned to an input/reference description."""
    return not _position_is_source_description(text, position)


def _output_semantic_evidence_end(text: str, position: int) -> int:
    """Return the enclosing explicit-output boundary, or the text boundary."""
    starts, ends = _output_target_interval_index(text)
    if not starts:
        return len(text)
    interval = bisect_right(starts, position) - 1
    if interval >= 0 and starts[interval] <= position < ends[interval]:
        return ends[interval]
    return position


@lru_cache(maxsize=4096)
def _included_output_antecedent_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Index explicitly retained subjects that a later output pronoun may use."""
    return _interval_index(_merge_intervals([
        (match.start("subject"), match.end("subject"))
        for match in OUTPUT_INCLUDED_SUBJECT.finditer(text)
    ]))


def _position_is_included_output_antecedent(text: str, position: int) -> bool:
    return _position_in_interval_index(
        _included_output_antecedent_interval_index(text), position
    )


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
            trailing_source = TARGET_TRAILING_SOURCE.search(target)
            if trailing_source is not None:
                target = target[:trailing_source.start()]
            target = re.sub(
                r"\b(?:and|plus)\s+(?:a|an|another|the)?\s*$",
                "",
                target,
                flags=re.I,
            ).strip()
            if target:
                for visible_target in _split_visible_target_relations(target):
                    targets.extend(_split_mandatory_target_items(visible_target))
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
    # Relative clauses describe the listed noun phrase but their verbs do not
    # turn that subject into scene direction.  Validate list eligibility from
    # the grammatical head segment while preserving the complete requirement.
    eligibility = re.split(r"\b(?:that|which|who|whose)\b", candidate, maxsplit=1, flags=re.I)[0]
    eligibility_tokens = lexical_tokens(eligibility)
    material = [
        token
        for token in eligibility_tokens
        if token not in FUNCTION_WORDS
        and token not in PRODUCTION_GENERIC
        and token not in TRACE_GENERIC
        and len(token) > 2
    ]
    if not material or len(eligibility_tokens) > MAX_EXPLICIT_TARGET_REQUIREMENTS + 3:
        return None
    first = eligibility_tokens[0] if eligibility_tokens else ""
    if first in TARGET_PHRASE_BREAKS or first in {
        "camera", "cut", "during", "light", "sound", "when", "while",
    }:
        return None
    if any(token in TARGET_ACTION_BREAKS for token in eligibility_tokens):
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
        if re.match(r"\s*(?:that|which|who|whose)\b", segment, re.I):
            # A parenthetical relative clause belongs to the previous subject;
            # do not let its comma terminate the surrounding mandatory list.
            continue
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
ACTION_TRACE_TERMS = OPPOSITE_ACTION_TERMS | frozenset(TARGET_SHARED_RELATIONS)


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
            or token in TARGET_FORMAT_TERMS
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
    final_starts_new_noun_phrase = bool(
        surface_branches
        and re.match(r"\s*(?:a|an|another|the)\b", surface_branches[-1], re.I)
    )

    shared_suffix: list[str] = []
    alternative_width = len(branches[0][0])
    if (
        len(branches) >= 2
        and not final_starts_new_noun_phrase
        and alternative_width >= 1
        and len(branches[-1][0]) > alternative_width
        and all(
            len(tokens) == alternative_width and not protected
            for tokens, protected in branches[:-1]
        )
        and not branches[-1][1]
    ):
        # Coordination grammar, not a colour/adjective dictionary, determines
        # the split. Equal-width alternatives precede the final branch's shared
        # noun suffix: ``bright red or deep blue leather case`` therefore keeps
        # ``leather case`` (and its head) on both branches.
        final_tokens = branches[-1][0]
        final_alternative_width = alternative_width
        first_tokens = branches[0][0]
        if (
            final_tokens[0] in COORDINATION_DEGREE_MODIFIERS
            and first_tokens[0] not in COORDINATION_DEGREE_MODIFIERS
        ):
            # ``red wool or pale blue silk surgical gloves`` has one extra
            # degree word in the final alternative. Align the parallel spans
            # before inheriting the terminal ``surgical gloves`` suffix.
            final_alternative_width += 1
        shared_suffix = final_tokens[final_alternative_width:]

    ambiguous_terminal_head: list[str] = []
    if (
        not shared_suffix
        and len(branches) >= 3
        and len(branches[-1][0]) >= 3
        and not any(protected for _, protected in branches)
        and not final_starts_new_noun_phrase
    ):
        # Align the final alternative with the widest preceding alternative.
        # This preserves a multiword nominal suffix in ``red or pale blue or
        # dark green emergency field surgeon`` without borrowing ``green`` into
        # the red branch. If alignment remains ambiguous, the terminal head is
        # still the conservative floor.
        prior_width = max(len(tokens) for tokens, _ in branches[:-1])
        ambiguous_terminal_head = branches[-1][0][prior_width:]
        if not ambiguous_terminal_head:
            ambiguous_terminal_head = branches[-1][0][-1:]

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
        if branch_index < len(branches) - 1 and shared_suffix:
            inherited = shared_suffix
            inherited_heads = [shared_suffix[-1]]
        elif branch_index < len(branches) - 1 and ambiguous_terminal_head:
            inherited = ambiguous_terminal_head
            inherited_heads = ambiguous_terminal_head
        if (
            branch_index
            and identity_head
            and identity_head not in branch_tokens
            and not branch_protected
            and not starts_new_noun_phrase
        ) and not shared_suffix:
            # ``surgeon named Mara or Nia`` shares the entity head and all
            # pre-name attributes across both identity alternatives.
            inherited = shared_identity
            inherited_heads = [identity_head]
        elif (
            branch_index
            and len(branch_tokens) == 1
            and shared_modifiers
            and not starts_new_noun_phrase
        ) and not shared_suffix:
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

# Common irregulars need one explicit lexical boundary.  Regular spelling can
# be inverted safely below; suppletive forms cannot be recovered from suffixes.
# The table is deliberately action-focused rather than a general English
# dictionary, and every listed form maps to one stable scene verb identity.
ACTION_IRREGULAR_LEMMAS = {
    "became": "become", "become": "become",
    "began": "begin", "begun": "begin",
    "bent": "bend", "bound": "bind", "bit": "bite", "bitten": "bite",
    "blew": "blow", "blown": "blow", "broke": "break", "broken": "break",
    "brought": "bring", "built": "build", "bought": "buy",
    "caught": "catch", "chose": "choose", "chosen": "choose",
    "came": "come", "cost": "cost", "cut": "cut", "dug": "dig",
    "did": "do", "done": "do", "drew": "draw", "drawn": "draw",
    "drank": "drink", "drunk": "drink", "drove": "drive", "driven": "drive",
    "ate": "eat", "eaten": "eat", "fell": "fall", "fallen": "fall",
    "fed": "feed", "felt": "feel", "fought": "fight", "found": "find",
    "flew": "fly", "flown": "fly", "got": "get", "gotten": "get",
    "gave": "give", "given": "give", "went": "go", "gone": "go",
    "grew": "grow", "grown": "grow", "hung": "hang", "held": "hold",
    "kept": "keep", "knew": "know", "known": "know",
    "laid": "lay", "led": "lead", "left": "leave", "lent": "lend",
    "let": "let", "lay": "lie", "lain": "lie", "lit": "light",
    "lost": "lose", "made": "make", "met": "meet", "paid": "pay",
    "put": "put", "read": "read", "rode": "ride", "ridden": "ride",
    "rang": "ring", "rung": "ring", "rose": "rise", "risen": "rise",
    "ran": "run", "said": "say", "saw": "see", "seen": "see",
    "sought": "seek", "sold": "sell", "sent": "send", "set": "set",
    "shook": "shake", "shaken": "shake", "shone": "shine",
    "shot": "shoot", "showed": "show", "shown": "show", "shut": "shut",
    "sang": "sing", "sung": "sing", "sank": "sink", "sunk": "sink",
    "sat": "sit", "slept": "sleep", "slid": "slide", "spoke": "speak",
    "spoken": "speak", "spent": "spend", "spun": "spin", "split": "split",
    "spread": "spread", "sprang": "spring", "sprung": "spring",
    "stood": "stand", "stole": "steal", "stolen": "steal",
    "stuck": "stick", "stung": "sting", "struck": "strike",
    "swam": "swim", "swum": "swim", "swung": "swing",
    "took": "take", "taken": "take", "taught": "teach",
    "tore": "tear", "torn": "tear", "told": "tell", "thought": "think",
    "threw": "throw", "thrown": "throw", "understood": "understand",
    "woke": "wake", "woken": "wake", "wore": "wear", "worn": "wear",
    "won": "win", "wound": "wind", "wrote": "write", "written": "write",
}
ACTION_IRREGULAR_PARTICIPLES = frozenset({
    "become", "begun", "bent", "bound", "bitten", "blown", "broken",
    "brought", "built", "bought", "caught", "chosen", "come", "cost",
    "cut", "dug", "done", "drawn", "driven", "drunk", "eaten", "fallen",
    "fed", "felt", "fought", "found", "flown", "got", "gotten", "given",
    "gone", "grown", "hung", "held", "kept", "known", "laid", "led",
    "left", "lent", "let", "lain", "lit", "lost", "made", "met", "paid",
    "put", "read", "ridden", "rung", "risen", "run", "said", "seen",
    "sought", "sold", "sent", "set", "shaken", "shone", "shot", "shown",
    "shut", "sung", "sunk", "sat", "slept", "slid", "spoken", "spent",
    "spun", "split", "spread", "sprung", "stood", "stolen", "stuck",
    "stung", "struck", "swum", "swung", "taken", "taught", "torn",
    "told", "thought", "thrown", "understood", "woken", "worn", "won",
    "wound", "written",
})
OBJECT_PRONOUNS = {"it", "them", "this", "that", "these", "those"}
OBJECT_DETERMINERS = {
    "a", "an", "her", "his", "its", "my", "our", "the", "their",
    "this", "these", "those", "your",
}
OBJECT_BREAKS = {
    "above", "across", "against", "and", "around", "as", "at", "below", "behind",
    "beside", "between", "but", "by", "during", "for", "in", "inside",
    "instead", "from", "near", "nor", "of", "off", "on", "onto", "or",
    "out", "outside", "over", "then", "through", "toward", "towards",
    "under", "up", "using", "when", "while", "with",
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
ACTION_OBJECT_PUNCTUATION = re.compile(r"[,.;!?\u2026\u061f。！？，；\n]")
ACTION_CLAUSE_PUNCTUATION = re.compile(r"[.;!?\u2026\u061f。！？；\n]")
ACTION_NEGATOR = re.compile(
    r"\b(?:no|not|never|neither|nor|without|do not|does not|must not|nothing from|"
    r"cannot|can['\u2019]t|could not|couldn['\u2019]t|will not|won['\u2019]t|"
    r"would not|wouldn['\u2019]t|fail(?:s|ed)? to|"
    r"refus(?:e|es|ed|ing)(?:\s+to)?|"
    r"den(?:y|ies|ied)(?:\s+the\s+request)?(?:\s+permission)?(?:\s+to)?|"
    r"(?:is|are|was|were)\s+(?:denied|forbidden|prevented)"
    r"(?:\s+permission)?(?:\s+(?:from|to))?|"
    r"(?:is|are|was|were)\s+(?:barred|prohibited)(?:\s+from)?|"
    r"declin(?:e|es|ed|ing)(?:\s+to)?|avoid(?:s|ed|ing)?|"
    r"(?:is|are|was|were)\s+(?:completely\s+)?unable to|"
    r"(?:isn['\u2019]t|aren['\u2019]t|wasn['\u2019]t|weren['\u2019]t) able to)\b",
    re.I,
)
ACTION_NONCOMMITTAL_PREFIX = re.compile(
    r"\b(?:"
    r"(?:attempt(?:s|ed|ing)?|tr(?:y|ies|ied|ying)|plan(?:s|ned|ning)?|"
    r"intend(?:s|ed|ing)?|want(?:s|ed|ing)?|pretend(?:s|ed|ing)?|"
    r"(?:hope(?:s|d)?|hoping)|threaten(?:s|ed|ing)?)\s+to|"
    r"(?:consider(?:s|ed|ing)?|dream(?:s|ed|ing)?|imagin(?:e|es|ed|ing)|"
    r"mim(?:e|es|ed|ing)|rehears(?:e|es|ed|ing)|visualiz(?:e|es|ed|ing))|"
    r"(?:am|are|is|was|were)\s+(?:about|asked|due|expected|poised|prepared|"
    r"ready|scheduled|set)\s+to|"
    r"(?:has|have|had)\s+yet\s+to|"
    r"(?:stop(?:s|ped|ping)?)\s+short\s+of|"
    r"(?:almost|nearly)|(?:may|might|could)"
    r")\s*$",
    re.I,
)
ACTION_STATIVE_PREFIX = re.compile(
    r"\b(?:lie|lies|lay|remain(?:s|ed)?|sit(?:s|ting)?|sat|"
    r"stand(?:s|ing)?|stood|stay(?:s|ed)?)\s*$",
    re.I,
)
ACTION_REPRESENTED_PREFIX = re.compile(
    r"\b(?:alleg(?:e|es|ed|ing)|claim(?:s|ed|ing)?|"
    r"consider(?:s|ed|ing)?|describ(?:e|es|ed|ing)|dream(?:s|ed|ing)?|"
    r"imagin(?:e|es|ed|ing)|mention(?:s|ed|ing)?|mim(?:e|es|ed|ing)|"
    r"pretend(?:s|ed|ing)?|recall(?:s|ed|ing)?|rehears(?:e|es|ed|ing)|"
    r"remember(?:s|ed|ing)?|report(?:s|ed|ing)?|say(?:s|ing)?|said|"
    r"visualiz(?:e|es|ed|ing))\s*$",
    re.I,
)
ACTION_PROSPECTIVE_PREFIX = re.compile(
    r"\b(?:(?:almost|nearly)|"
    r"(?:attempt(?:s|ed|ing)?|hope(?:s|d)?|hoping|intend(?:s|ed|ing)?|"
    r"plan(?:s|ned|ning)?|threaten(?:s|ed|ing)?|tr(?:y|ies|ied|ying)|"
    r"want(?:s|ed|ing)?)\s+to|"
    r"(?:am|are|is|was|were)\s+(?:about|asked|due|expected|poised|prepared|"
    r"ready|scheduled|set)\s+to|"
    r"(?:has|have|had)\s+yet\s+to|"
    r"(?:stop(?:s|ped|ping)?)\s+short\s+of)\s*$",
    re.I,
)
ACTION_CONTEXT_RESET = re.compile(
    r"(?:[,;:]|\b(?:but|however|instead|then)\b)",
    re.I,
)
ACTION_HYPOTHETICAL_CONTEXT = re.compile(
    r"(?:^|[,;:])\s*(?:if|unless)\b[^.;!?]*$|"
    r"\b(?:assum(?:e|es|ed|ing)|suppos(?:e|es|ed|ing)|"
    r"in\s+the\s+event\s+that)\b[^.;!?]{0,120}$|"
    r"^\s*were\b[^,;!?]{0,100}\bto\s*$|"
    r"^\s*should\b[^,;!?]{0,100}$",
    re.I,
)
ACTION_REPRESENTED_CONTEXT = re.compile(
    r"\b(?:announc(?:e|es|ed|ing)|explain(?:s|ed|ing)?|"
    r"tell(?:s|ing)?|told)\b[^,;.!?]{0,80}\b(?:how|that)\b"
    r"[^,;.!?]{0,80}$|"
    r"\b(?:acts?\s+out|alleg(?:e|es|ed|ing)|claim(?:s|ed|ing)?|"
    r"describ(?:e|es|ed|ing)|dream(?:s|ed|ing)?|fak(?:e|es|ed|ing)|"
    r"imagin(?:e|es|ed|ing)|mention(?:s|ed|ing)?|mim(?:e|es|ed|ing)|"
    r"pretend(?:s|ed|ing)?|recall(?:s|ed|ing)?|rehears(?:e|es|ed|ing)|"
    r"remember(?:s|ed|ing)?|report(?:s|ed|ing)?|say(?:s|ing)?|said|"
    r"visualiz(?:e|es|ed|ing))\b[^,;.!?]{0,120}$|"
    r"\bwatch(?:es|ed|ing)?\s+(?:a\s+|the\s+)?"
    r"(?:film|footage|recording|screen|video)\b[^,;.!?]{0,120}$",
    re.I,
)
ACTION_PROSPECTIVE_CONTEXT = re.compile(
    r"\b(?:attempt(?:s|ed|ing)?|hope(?:s|d|ing)?|intend(?:s|ed|ing)?|"
    r"plan(?:s|ned|ning)?|promis(?:e|es|ed|ing)|"
    r"question(?:s|ed|ing)?|threaten(?:s|ed|ing)?|"
    r"tr(?:y|ies|ied|ying)|want(?:s|ed|ing)?|wonder(?:s|ed|ing)?)\b"
    r"[^,;.!?]{0,96}$|"
    r"\b(?:am|are|is|was|were)\s+(?:about|asked|due|expected|ordered|"
    r"poised|prepared|ready|scheduled|set|told)\b[^,;.!?]{0,80}$|"
    r"\b(?:am|are|is|was|were)\s+able\s+to\s*$|"
    r"\b(?:can|could|may|might|should|would)"
    r"(?:\s+\w+ly){0,2}\s*$",
    re.I,
)
ENTAILED_ACTION_COMPLEMENT = re.compile(
    r"\b(?:"
    r"(?:cannot|can['\u2019]t)\s+not|"
    r"(?:do(?:es)?|did)\s+not\s+fail(?:s|ed)?\s+to|"
    r"(?:never|cannot|can['\u2019]t)\s+fail(?:s|ed)?\s+to|"
    r"(?:do(?:es)?|did|could)\s+not\s+"
    r"(?:avoid(?:s|ed|ing)?|refus(?:e|es|ed|ing))(?:\s+to)?|"
    r"(?:cannot|can['\u2019]t|could\s+not)\s+"
    r"(?:avoid(?:s|ed|ing)?|declin(?:e|es|ed|ing)|help|"
    r"refus(?:e|es|ed|ing))(?:\s+to)?"
    r")\s+(?P<action>[A-Za-z]+(?:['\u2019-][A-Za-z]+)?)",
    re.I,
)
ACTION_GRAMMAR_TERMS = {
    "able", "allow", "cannot", "could", "deni", "fail", "forbid", "never",
    "neither", "nor", "not", "permission", "prevent", "refus", "request", "unable", "will",
    "without", "would",
}


def _canonical_action_token(surface: str) -> str:
    lowered = surface.lower().replace("’", "'").strip("'")
    if lowered in ACTION_SURFACE_ALIASES:
        return ACTION_SURFACE_ALIASES[lowered]
    if lowered in ACTION_IRREGULAR_LEMMAS:
        return ACTION_IRREGULAR_LEMMAS[lowered]
    canonical = lexical_tokens(surface)
    return canonical[0] if len(canonical) == 1 else ""


FOUND_BASE_FORM_PREDECESSORS = frozenset({
    "can", "could", "did", "do", "does", "may", "might", "must", "shall",
    "should", "to", "will", "would",
})


def _canonical_action_at(
    text: str,
    token_matches: list[re.Match[str]],
    index: int,
) -> str:
    """Disambiguate the base verb ``found`` from the past of ``find``.

    The surface alone is ambiguous.  A modal, infinitive marker, or bounded
    imperative licenses base-form ``found``; ordinary finite/participial uses
    keep the irregular ``find`` identity.
    """
    match = token_matches[index]
    surface = match.group(0).lower().replace("\u2019", "'").strip("'")
    if surface != "found":
        return _canonical_action_token(surface)
    previous_surface = token_matches[index - 1].group(0) if index else ""
    previous_tokens = lexical_tokens(previous_surface)
    previous = previous_tokens[0] if len(previous_tokens) == 1 else ""
    if previous in FOUND_BASE_FORM_PREDECESSORS:
        return "found"
    prefix = _bounded_action_prefix(text, match.start())
    if re.fullmatch(
        r"\s*(?:(?:and|but|next|now|please|then)\s+)*(?:[A-Za-z]+ly\s+){0,2}",
        prefix,
        re.I,
    ):
        return "found"
    return "find"


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
    particles = _action_particle_identity(text, token_matches, action_index)
    cursor = token_matches[action_index].end()
    inspected = 0
    following_stop = min(len(token_matches), action_index + 17)
    for following_index in range(action_index + 1, following_stop):
        following = token_matches[following_index]
        following_tokens = lexical_tokens(following.group(0))
        if len(following_tokens) != 1:
            break
        token = following_tokens[0]
        canonical_following = _canonical_action_token(following.group(0))
        gap = text[cursor:following.start()]
        if ACTION_OBJECT_PUNCTUATION.search(gap):
            comma_only_gap = re.fullmatch(r"\s*[,，]\s*", gap) is not None
            postnominal_follower = (
                token in {"that", "which", "whose"}
                or canonical_following in POSTNOMINAL_OBJECT_MARKERS
            )
            if not (direct_terms and comma_only_gap and postnominal_follower):
                break
        inspected += 1
        if (
            not direct_terms
            and inspected <= len(particles)
            and token == particles[inspected - 1]
        ):
            cursor = following.end()
            continue
        if token in {"that", "which", "whose"} and direct_terms:
            relative_postnominal = True
            cursor = following.end()
            continue
        if direct_terms and token in {"are", "is", "was", "were"}:
            if relative_postnominal:
                cursor = following.end()
                continue
            break
        if canonical_following in ANTECEDENT_ACTIONS:
            previous_tokens = lexical_tokens(
                token_matches[following_index - 1].group(0)
            )
            next_match = (
                token_matches[following_index + 1]
                if following_index + 1 < len(token_matches)
                else None
            )
            next_tokens = (
                lexical_tokens(next_match.group(0))
                if next_match is not None
                else []
            )
            attributive_action = (
                canonical_following not in POSTNOMINAL_OBJECT_MARKERS
                and len(next_tokens) == 1
                and _action_content_term(next_tokens[0])
                and (
                    bool(direct_terms)
                    or (
                        following.group(0).lower().endswith(("ed", "en"))
                        and previous_tokens
                        and previous_tokens[0] in OBJECT_DETERMINERS
                    )
                )
            )
            if attributive_action:
                if direct_terms and _action_content_term(token):
                    direct_terms.append(token)
                cursor = following.end()
                continue
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


def _coordinated_shared_object_identity(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
) -> tuple[str, ...]:
    """Bind ``slices and serves the loaf`` to the shared final object."""
    suffix = _bounded_action_suffix(text, token_matches[action_index].end())
    shared = GENERAL_ACTION_SHARED_OBJECT.match(suffix)
    if shared is None or action_index + 2 >= len(token_matches):
        return ()
    coordinator = lexical_tokens(token_matches[action_index + 1].group(0))
    if coordinator not in (["and"], ["or"]):
        return ()
    shared_action_index = action_index + 2
    shared_surface = token_matches[shared_action_index].group(0)
    if shared_surface.lower() != shared.group("action").lower():
        return ()
    identity, pronoun = _direct_object_identity(
        text,
        token_matches,
        shared_action_index,
        _canonical_action_token(shared_surface),
    )
    return () if pronoun else identity


@lru_cache(maxsize=4096)
def _action_clause_boundary_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Index clause punctuation once for every action parse.

    Action extraction asks for the same local clause around many tokens.  A
    fresh ``finditer``/``search`` from every token makes a punctuation-free
    prompt quadratic, so all prefix and suffix lookups share this index.
    """
    boundaries = tuple(ACTION_CLAUSE_PUNCTUATION.finditer(text))
    return (
        tuple(boundary.start() for boundary in boundaries),
        tuple(boundary.end() for boundary in boundaries),
    )


def _local_antecedent_start(text: str, action_start: int) -> int:
    starts, ends = _action_clause_boundary_index(text)
    boundary_index = bisect_left(starts, action_start) - 1
    if boundary_index < 0:
        return 0
    local_start = ends[boundary_index]
    prefix = text[local_start:min(action_start, local_start + 32)]
    # A cue-led new sentence may refer to the explicit object in the immediately
    # preceding event, but never search the whole prompt for a convenient noun.
    if re.match(r"\s*(?:then|next|finally)\b", prefix, re.I):
        return ends[boundary_index - 1] if boundary_index >= 1 else 0
    return local_start


def _local_clause_end(text: str, action_end: int) -> int:
    starts, _ = _action_clause_boundary_index(text)
    boundary_index = bisect_left(starts, action_end)
    return starts[boundary_index] if boundary_index < len(starts) else len(text)


MAX_ACTION_GRAMMAR_WINDOW = 384


def _bounded_action_prefix(text: str, position: int) -> str:
    clause_start = _local_antecedent_start(text, position)
    return text[max(clause_start, position - MAX_ACTION_GRAMMAR_WINDOW):position]


def _bounded_action_suffix(text: str, position: int) -> str:
    clause_end = _local_clause_end(text, position)
    return text[position:min(clause_end, position + MAX_ACTION_GRAMMAR_WINDOW)]


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
        if (
            previous_action not in ANTECEDENT_ACTIONS
            and not _general_action_syntax_candidate(
                text, token_matches, previous_index
            )
        ):
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
    local_prior: list[re.Match[str]] = []
    for prior_index in range(action_index - 1, -1, -1):
        prior = token_matches[prior_index]
        if prior.start() < clause_start:
            break
        local_prior.append(prior)
    terms = [
        token
        for prior in reversed(local_prior)
        for token in lexical_tokens(prior.group(0))
        if _action_content_term(token)
    ]
    return _compact_object_identity(terms)


def _object_relative_antecedent_identity(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
) -> tuple[str, ...]:
    """Return the object antecedent in ``case that a surgeon opens``."""
    match = token_matches[action_index]
    clause_start = _local_antecedent_start(text, match.start())
    prefix = text[clause_start:match.start()]
    relatives = list(re.finditer(r"\b(?:that|which)\b", prefix, re.I))
    if not relatives:
        return ()
    relative = relatives[-1]
    explicit_subject = _nearest_subject_identity(prefix[relative.end():])
    if not explicit_subject:
        return ()
    return _nearest_subject_identity(prefix[:relative.start()])


SUBJECT_BOUNDARY_TERMS = {
    "after", "and", "as", "before", "but", "during", "for", "from", "in",
    "inside", "instead", "near", "on", "or", "outside", "then", "to", "under", "when",
    "while", "with", "who", "which", "that",
}
SUBJECT_NON_ENTITY_TERMS = (
    ACTION_GRAMMAR_TERMS
    | ACTION_AUXILIARIES
    | PRODUCTION_GENERIC
    | TRACE_GENERIC
    | TARGET_IDENTITY_MARKERS
    | {
        "about", "almost", "avoid", "decline", "imagining", "nearly", "refuse",
        "able", "barred", "denied", "forbidden", "help", "permission", "please", "prevented",
        "prohibited", "scheduled", "threatening", "unable",
        "animation", "clip", "depiction", "image", "portrait", "render", "shot",
        "storyboard", "take", "video",
    }
)
MAX_BOUND_IDENTITY_TERMS = 16


def _nearest_subject_identity(fragment: str) -> tuple[str, ...]:
    """Extract the nearest bounded noun phrase before an action predicate."""
    matches = list(TOKEN.finditer(fragment))
    collected: list[str] = []
    right_edge = len(fragment)
    for match in reversed(matches):
        gap = fragment[match.end():right_edge]
        if collected and re.search(r"[,.;!?。！？，；\n]", gap):
            break
        surface = match.group(0).lower().replace("’", "'").strip("'")
        tokens = lexical_tokens(match.group(0))
        right_edge = match.start()
        if not tokens:
            continue
        if surface in {"a", "an", "the"}:
            if collected:
                if surface == "the":
                    continue
                break
            continue
        if surface in {"he", "i", "it", "she", "they", "we", "you"}:
            continue
        if "n't" in surface:
            continue
        canonical_action = _canonical_action_token(match.group(0))
        if canonical_action in ACTION_TRACE_TERMS:
            if collected:
                break
            continue
        if any(token in SUBJECT_BOUNDARY_TERMS for token in tokens):
            if collected:
                break
            continue
        if surface.endswith("ly"):
            continue
        material = [
            token
            for token in tokens
            if _action_content_term(token)
            and token not in SUBJECT_NON_ENTITY_TERMS
        ]
        if material:
            collected[0:0] = material
            if len(collected) >= MAX_BOUND_IDENTITY_TERMS:
                break
    return tuple(dict.fromkeys(collected[-MAX_BOUND_IDENTITY_TERMS:]))


def _leading_subject_identity(fragment: str) -> tuple[str, ...]:
    """Extract one noun phrase at the left edge of ``fragment``.

    This is used for passive agents and synthetic pre-nominal relations. A
    right-edge extractor would turn ``opened by a surgeon in the theatre`` into
    an action by the theatre, so prepositions and coordinators end the phrase.
    """
    collected: list[str] = []
    cursor = 0
    for match in TOKEN.finditer(fragment):
        gap = fragment[cursor:match.start()]
        if collected and re.search(r"[,.;!?\n]", gap):
            break
        surface = match.group(0).lower().replace("\u2019", "'").strip("'")
        tokens = lexical_tokens(match.group(0))
        cursor = match.end()
        if not tokens:
            continue
        if surface in {"a", "an", "the"} and not collected:
            continue
        if "n't" in surface:
            continue
        canonical_action = _canonical_action_token(match.group(0))
        if (
            canonical_action in ACTION_TRACE_TERMS
            or any(token in SUBJECT_BOUNDARY_TERMS for token in tokens)
        ):
            break
        material = [
            token
            for token in tokens
            if _action_content_term(token)
            and token not in SUBJECT_NON_ENTITY_TERMS
        ]
        if material:
            collected.extend(material)
            if len(collected) >= MAX_BOUND_IDENTITY_TERMS:
                break
        elif collected:
            break
    return tuple(dict.fromkeys(collected[:MAX_BOUND_IDENTITY_TERMS]))


def _nearest_discourse_entity_identity(
    text: str,
    current_clause_start: int,
) -> tuple[str, ...]:
    """Resolve a subject pronoun from the immediately preceding clause.

    A previous tracked action is not necessarily the nearest antecedent. In
    ``a surgeon enters; a nurse waits; she opens``, carrying the surgeon forward
    silently reassigns the final action. Inspect the nearest complete discourse
    clause first, including entities introduced after its tracked predicate.
    """
    before = text[:current_clause_start].rstrip()
    before = re.sub(r"[.;!?\n]+\s*$", "", before)
    if not before:
        return ()
    boundaries = list(ACTION_CLAUSE_PUNCTUATION.finditer(before))
    previous_start = boundaries[-1].end() if boundaries else 0
    return _nearest_subject_identity(before[previous_start:])


def _action_surface_is_passive(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
) -> bool:
    """Return whether an action is a passive participle with an auxiliary."""
    match = token_matches[action_index]
    surface = match.group(0).lower().replace("\u2019", "'").strip("'")
    participle = surface.endswith("ed") or surface in ACTION_IRREGULAR_PARTICIPLES or surface in {
        "built", "closed", "done", "held", "left", "made", "opened", "shut",
        "worn",
    }
    if not participle:
        return False
    prefix = _bounded_action_prefix(text, match.start())
    return re.search(
        r"\b(?:am|are|be|been|being|get|gets|got|is|was|were)"
        r"(?:\s+\w+ly){0,2}\s*$",
        prefix,
        re.I,
    ) is not None


def _action_subject_identity(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
    fallback_subject: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Bind an action to its local actor, relative antecedent, or passive agent."""
    match = token_matches[action_index]
    clause_start = _local_antecedent_start(text, match.start())
    suffix = _bounded_action_suffix(text, match.end())
    if _action_surface_is_passive(text, token_matches, action_index):
        bounded_agent = re.match(r"\s+by\s+(?P<agent>[^,;:.!?\n]+)", suffix, re.I)
        if bounded_agent is not None:
            agent = _leading_subject_identity(bounded_agent.group("agent"))
            if agent:
                return agent
    prefix = _bounded_action_prefix(text, match.start())
    depicted = re.search(
        r"\b(?:am|are|is|was|were)\s+(?:depicted|seen|shown)\s*$",
        prefix,
        re.I,
    )
    if depicted is not None:
        depicted_subject = _nearest_subject_identity(prefix[:depicted.start()])
        if depicted_subject:
            return depicted_subject
    surface = match.group(0).lower().replace("\u2019", "'").strip("'")
    if surface.endswith("ing") and re.fullmatch(r"\s*after\s*", prefix, re.I):
        following_subject = re.search(
            r",\s*(?:(?:a|an|the)\s+)?"
            r"(?P<subject>(?:[A-Za-z][A-Za-z'\u2019-]*\s+){0,5}?"
            r"[A-Za-z][A-Za-z'\u2019-]*)\s+"
            r"(?:am|are|is|was|were|[A-Za-z][A-Za-z'\u2019-]*(?:s|ed))\b",
            suffix,
            re.I,
        )
        if following_subject is not None:
            subject = _leading_subject_identity(following_subject.group("subject"))
            if subject:
                return subject
    if re.search(r"\b(?:he|she|they)\b\s*$", prefix, re.I):
        discourse_subject = _nearest_discourse_entity_identity(text, clause_start)
        if discourse_subject:
            return discourse_subject
    if fallback_subject:
        local_boundaries = list(
            re.finditer(r"(?:[,;:]|\b(?:and|but|instead|or|then)\b)", prefix, re.I)
        )
        if local_boundaries:
            tail = prefix[local_boundaries[-1].end():]
            if not _nearest_subject_identity(tail):
                return fallback_subject
    relatives = list(re.finditer(r"\b(?:that|which|who)\b", prefix, re.I))
    if relatives:
        relative = relatives[-1]
        if re.fullmatch(r"[^,.;!?。！？，；\n]{0,48}", prefix[relative.end():]):
            subject = _nearest_subject_identity(prefix[relative.end():])
            if not subject:
                subject = _nearest_subject_identity(prefix[:relative.start()])
            if subject:
                return subject

    appositive = re.search(
        r"(?P<left>[^,;]{1,48}),\s*(?P<right>[^,;]{1,48}),\s*$",
        prefix,
    )
    if appositive is not None:
        left = _nearest_subject_identity(appositive.group("left"))
        right = _nearest_subject_identity(appositive.group("right"))
        if left and right:
            return tuple(dict.fromkeys((*left, *right)))

    coordinators = list(re.finditer(r"\b(?:and|or)\b", prefix, re.I))
    prefix_tokens = list(TOKEN.finditer(prefix))
    if coordinators and not any(
        _general_action_syntax_candidate(prefix, prefix_tokens, token_index)
        for token_index, token in enumerate(prefix_tokens)
        if _canonical_action_token(token.group(0)) not in ACTION_TRACE_TERMS
    ) and not any(
        _canonical_action_token(token.group(0)) in ACTION_TRACE_TERMS
        for token in prefix_tokens
    ):
        coordinator = coordinators[-1]
        left = _nearest_subject_identity(prefix[:coordinator.start()])
        right = _nearest_subject_identity(prefix[coordinator.end():])
        if left and right:
            return tuple(dict.fromkeys((*left, *right)))

    subject = _nearest_subject_identity(prefix)
    if subject:
        return subject
    if re.search(
        r"(?:\b(?:he|i|it|she|they|we|you)\b\s*|"
        r"\b(?:and|but|instead|or|then)\s*)$",
        prefix,
        re.I,
    ):
        return fallback_subject or (("__implicit__",) if re.search(r"\byou\b", prefix, re.I) else ())
    if not prefix.strip():
        return ("__implicit__",)
    return ()


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


@lru_cache(maxsize=4096)
def _state_transition_attribute_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return _interval_index(tuple(
        (match.start(), match.end())
        for match in STATE_TRANSITION_ATTRIBUTE.finditer(text)
    ))


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
    canonical_action = _canonical_action_at(text, token_matches, index)
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
    clause_prefix = _bounded_action_prefix(text, match.start())

    if _position_in_interval_index(
        _state_transition_attribute_interval_index(text), match.start()
    ):
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

    if (past_surface or gerund_surface) and previous not in ACTION_AUXILIARIES:
        prefix_start = max(
            _local_antecedent_start(text, match.start()),
            match.start() - MAX_ACTION_GRAMMAR_WINDOW,
        )
        for prior_index in range(index - 1, -1, -1):
            prior = token_matches[prior_index]
            if prior.start() < prefix_start:
                break
            prior_action = _canonical_action_token(prior.group(0))
            bridge = text[prior.end():match.start()]
            if prior_action in ACTION_TRACE_TERMS and not re.search(
                r"\b(?:and|but|then|while|who|which|that)\b|[,;:]",
                bridge,
                re.I,
            ):
                return False

    if base_surface and previous in {
        "am", "appear", "are", "is", "look", "remain", "seem", "stay", "was",
        "were",
    }:
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


GENERAL_ACTION_GOVERNOR_SURFACE = re.compile(
    r"(?:attempt(?:s|ed|ing)?|consider(?:s|ed|ing)?|dream(?:s|ed|ing)?|"
    r"hop(?:e|es|ed|ing)|imagin(?:e|es|ed|ing)|intend(?:s|ed|ing)?|"
    r"mim(?:e|es|ed|ing)|plan(?:s|ned|ning)?|pretend(?:s|ed|ing)?|"
    r"promis(?:e|es|ed|ing)|question(?:s|ed|ing)?|"
    r"rehears(?:e|es|ed|ing)|threaten(?:s|ed|ing)?|"
    r"tr(?:y|ies|ied|ying)|visualiz(?:e|es|ed|ing)|"
    r"want(?:s|ed|ing)?|wonder(?:s|ed|ing)?)",
    re.I,
)
GENERAL_ACTION_NONSCENE_SURFACE = re.compile(
    r"(?:act(?:s|ed|ing)?|contain(?:s|ed|ing)?|deliver(?:s|ed|ing)?|"
    r"depict(?:s|ed|ing)?|display(?:s|ed|ing)?|draft(?:s|ed|ing)?|"
    r"feature(?:s|d|ing)?|feed(?:s|ing)?|fed|film(?:s|ed|ing)?|"
    r"generat(?:e|es|ed|ing)|guid(?:e|es|ed|ing)|input(?:s|ted|ting)?|"
    r"portray(?:s|ed|ing)?|produc(?:e|es|ed|ing)|provid(?:e|es|ed|ing)|"
    r"relight(?:s|ed|ing)?|render(?:s|ed|ing)?|restyl(?:e|es|ed|ing)|"
    r"serv(?:e|es|ed|ing)|show(?:s|ed|ing)?|shown|"
    r"star(?:s|red|ring)?)",
    re.I,
)
GENERAL_ACTION_MARKED_OBJECT = re.compile(
    r"^\s*(?:[A-Za-z]+ly\s+){0,2}"
    r"(?:(?:a|an|her|his|its|my|our|the|their|this|these|those|your)\s+|"
    r"(?:it|them)\b)",
    re.I,
)
GENERAL_ACTION_DIRECTIONAL_COMPLEMENT = re.compile(
    r"^\s*(?:[A-Za-z]+ly\s+){0,2}"
    r"(?:across|along|away\s+from|down|from|into|off|onto|out\s+of|over|"
    r"through|to|toward|towards|up)\s+"
    r"(?:(?:a|an|her|his|its|my|our|the|their|this|these|those|your)\s+)?"
    r"[A-Za-z0-9]",
    re.I,
)
GENERAL_ACTION_CONTEXTUAL_TERMS = {
    "fix", "get", "make", "sit", "stand", "take", "turn", "walk",
}
GENERAL_ACTION_ABSTRACT_TERMS = {
    "accept", "end", "inspect", "learn", "look", "protect", "wait",
}
GENERAL_ACTION_EXCLUDED_TERMS = frozenset(
    (
        FUNCTION_WORDS
        | PRODUCTION_GENERIC
        | TRACE_GENERIC
        | TARGET_CONTROL_TERMS
        | ACTION_AUXILIARIES
        | ACTION_GRAMMAR_TERMS
        | OBJECT_DETERMINERS
        | OBJECT_BREAKS
        | LEADING_OBJECT_PREPOSITIONS
        | SUBJECT_NON_ENTITY_TERMS
        | TARGET_IDENTITY_MARKERS
        | TARGET_PURPOSE_VERBS
        | SUBJECT_BOUNDARY_TERMS
        | {
            "across", "along", "away", "down", "off", "onto", "out", "over",
            "past", "rather", "than", "toward", "towards", "up",
        }
    ) - GENERAL_ACTION_CONTEXTUAL_TERMS
    | GENERAL_ACTION_ABSTRACT_TERMS
)

GENERAL_ACTION_BARE_OBJECT = re.compile(
    r"^\s*(?:[A-Za-z]+ly\s+){0,2}(?P<object>[A-Za-z][A-Za-z'\u2019-]*)\b",
    re.I,
)
GENERAL_ACTION_SHARED_OBJECT = re.compile(
    r"^\s*(?:,\s*)?(?:and|or)\s+"
    r"(?P<action>[A-Za-z]+(?:['\u2019-][A-Za-z]+)?)\s+"
    r"(?:(?:a|an|her|his|its|my|our|the|their|this|these|those|your)\s+|"
    r"(?:it|them)\b)",
    re.I,
)
GENERAL_ACTION_DEPICTED_GERUND_PREFIX = re.compile(
    r"\b(?:am|are|is|was|were)\s+(?:depicted|seen|shown)\s*$",
    re.I,
)
GENERAL_ACTION_NAMED_SUBJECT = re.compile(
    r"\s*(?:[A-Z][A-Za-z'\u2019-]*)(?:\s+[A-Z][A-Za-z'\u2019-]*){0,3}\s*$"
)
ACTION_PARTICLES = frozenset({
    "apart", "away", "back", "down", "in", "off", "on", "out", "over",
    "through", "together", "up",
})
ACTION_SEMANTIC_EQUIVALENT_GROUPS = (
    frozenset({"plunge", "quench", "quenche"}),
)
GENERAL_ACTION_QUANTIFIERS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "few", "many", "several",
}


def _general_action_syntax_candidate(
    text: str,
    token_matches: list[re.Match[str]],
    index: int,
) -> bool:
    """Recognize an open-vocabulary event only from bounded grammar.

    This deliberately does not try to label every English verb.  Outside the
    curated relation/opposite vocabulary, a claim needs a predicate-shaped
    surface, a local actor/imperative/relative cue, and either a marked object,
    a directional complement, or a passive agent.  That covers novel visible
    actions without turning arbitrary scene nouns and adjectives into
    requirements.
    """
    match = token_matches[index]
    surface = match.group(0).lower().replace("\u2019", "'").strip("'")
    tokens = lexical_tokens(match.group(0))
    if len(tokens) != 1 or not re.fullmatch(r"[a-z]+(?:'[a-z]+)?", surface):
        return False
    canonical_action = _canonical_action_token(surface)
    if canonical_action in ACTION_TRACE_TERMS:
        return _action_surface_is_predicate(text, token_matches, index)
    if (
        len(surface) < 3
        or canonical_action in GENERAL_ACTION_EXCLUDED_TERMS
        or surface.endswith("ly")
        or GENERAL_ACTION_GOVERNOR_SURFACE.fullmatch(surface)
        or GENERAL_ACTION_NONSCENE_SURFACE.fullmatch(surface)
        or not _action_surface_is_predicate(text, token_matches, index)
    ):
        return False

    prefix = _bounded_action_prefix(text, match.start())
    suffix = _bounded_action_suffix(text, match.end())
    previous_match = token_matches[index - 1] if index else None
    previous_surface = (
        previous_match.group(0).lower().replace("\u2019", "'").strip("'")
        if previous_match is not None
        else ""
    )
    previous_tokens = lexical_tokens(previous_surface)
    previous = previous_tokens[0] if len(previous_tokens) == 1 else ""
    if previous in GENERAL_ACTION_QUANTIFIERS or previous.isdigit():
        return False
    if previous in (
        (OBJECT_BREAKS | LEADING_OBJECT_PREPOSITIONS)
        - {"and", "but", "or", "then", "that", "which", "who"}
    ):
        return False
    if (
        surface == "given"
        and not prefix.strip()
        and re.match(
            r"\s+(?:(?:a|an|the)\s+)?(?:image|input|photo|photograph|"
            r"reference|source|still|video)\b",
            suffix,
            re.I,
        )
    ):
        return False
    if surface.endswith("ing") and not (
        re.search(
            r"\b(?:am|are|be|been|being|is|was|were)"
            r"(?:\s+[A-Za-z]+ly){0,2}\s*$",
            prefix,
            re.I,
        )
        or GENERAL_ACTION_DEPICTED_GERUND_PREFIX.search(prefix)
    ):
        return False
    local_subject = _nearest_subject_identity(prefix)
    previous_looks_plural = bool(previous_surface) and (
        previous_surface.endswith("s")
        and canonical_token(previous_surface) != previous_surface
    )
    determiner_subject = bool(local_subject) and re.search(
        r"(?:^|[,;:]|\b(?:and|but|instead|then|while)\b)\s*"
        r"(?:a|an|her|his|its|my|our|the|their|this|these|those|your)\s+"
        r"(?:[A-Za-z0-9][A-Za-z0-9'\u2019-]*\s+){0,11}$",
        prefix,
        re.I,
    ) is not None
    pronoun_or_relative_subject = previous in {
        "he", "i", "it", "she", "they", "we", "who", "which", "you",
    }
    imperative = re.fullmatch(
        r"\s*(?:(?:and|but|next|now|please|then)\s+)*"
        r"(?:[A-Za-z]+ly\s+){0,2}(?:to\s+)?",
        prefix,
        re.I,
    ) is not None
    auxiliary_bound_subject = (
        previous in ACTION_AUXILIARIES and bool(local_subject)
    )
    named_subject = GENERAL_ACTION_NAMED_SUBJECT.fullmatch(prefix) is not None
    previous_prefix = (
        _bounded_action_prefix(text, previous_match.start())
        if previous_match is not None
        else ""
    )
    previous_has_named_subject = (
        previous_match is not None
        and GENERAL_ACTION_NAMED_SUBJECT.fullmatch(previous_prefix) is not None
    )
    contextual_plural_subject = (
        bool(local_subject)
        and previous_looks_plural
        and not previous_has_named_subject
        and re.search(
            r"(?:^|[,;:])\s*"
            r"(?:[A-Za-z][A-Za-z'\u2019-]*\s+){1,3}$",
            prefix,
        )
        is not None
    )
    if not (
        determiner_subject
        or pronoun_or_relative_subject
        or imperative
        or auxiliary_bound_subject
        or named_subject
        or contextual_plural_subject
    ):
        return False

    if GENERAL_ACTION_MARKED_OBJECT.match(suffix):
        return True
    strong_verb_surface = (
        any(key != surface for key in _action_inflection_keys(surface))
        or previous in ACTION_AUXILIARIES
    )
    if GENERAL_ACTION_DIRECTIONAL_COMPLEMENT.match(suffix) and (
        strong_verb_surface
        or imperative
        or previous_looks_plural
        or previous in {"they", "we", "you"}
    ):
        return True
    if _action_surface_is_passive(text, token_matches, index) and re.match(
        r"\s+by\s+(?:(?:a|an|the)\s+)?[A-Za-z0-9]", suffix, re.I
    ):
        return True
    shared_object = GENERAL_ACTION_SHARED_OBJECT.match(suffix)
    if shared_object is not None and strong_verb_surface:
        shared_action = shared_object.group("action")
        if _action_inflection_keys(shared_action):
            return True
    bare_object = GENERAL_ACTION_BARE_OBJECT.match(suffix)
    if bare_object is not None and (
        strong_verb_surface or contextual_plural_subject
    ):
        object_tokens = lexical_tokens(bare_object.group("object"))
        if (
            len(object_tokens) == 1
            and object_tokens[0] not in (
                OBJECT_BREAKS
                | ACTION_AUXILIARIES
                | ACTION_GRAMMAR_TERMS
                | SUBJECT_BOUNDARY_TERMS
            )
        ):
            return True
    if not suffix.strip() and strong_verb_surface:
        return True

    return False


def _regular_action_forms(base: str) -> frozenset[str]:
    """Generate bounded regular forms for one proposed lemma.

    Inverse suffix stripping alone conflates different verbs (``tapes`` and
    ``taps``).  A candidate lemma survives only when its forward spelling rule
    can reproduce the observed surface.
    """
    if len(base) < 3 or not base.isalpha():
        return frozenset()
    vowels = frozenset("aeiou")
    consonant_y = base.endswith("y") and len(base) > 1 and base[-2] not in vowels
    sibilant = base.endswith(("s", "x", "z", "ch", "sh", "o"))
    doubles = (
        len(base) <= 4
        and len(base) >= 3
        and base[-1] not in vowels | frozenset("wxy")
        and base[-2] in vowels
        and base[-3] not in vowels
        and not base.endswith("en")
    )
    third = base[:-1] + "ies" if consonant_y else base + ("es" if sibilant else "s")
    if consonant_y:
        past = base[:-1] + "ied"
    elif base.endswith("e"):
        past = base + "d"
    elif doubles:
        past = base + base[-1] + "ed"
    else:
        past = base + "ed"
    if base.endswith("ie"):
        gerund = base[:-2] + "ying"
    elif base.endswith("e") and not base.endswith(("ee", "oe", "ye")):
        gerund = base[:-1] + "ing"
    elif doubles:
        gerund = base + base[-1] + "ing"
    else:
        gerund = base + "ing"
    return frozenset({base, third, past, gerund})


def _action_inflection_keys(surface: str) -> frozenset[str]:
    """Return only lemma candidates that regenerate the observed surface."""
    lowered = surface.lower().replace("\u2019", "'").strip("'")
    if lowered in ACTION_SURFACE_ALIASES:
        return frozenset({ACTION_SURFACE_ALIASES[lowered]})
    if lowered in ACTION_IRREGULAR_LEMMAS:
        return frozenset({ACTION_IRREGULAR_LEMMAS[lowered]})

    candidates = {lowered}
    if len(lowered) > 4 and lowered.endswith("ies"):
        candidates.add(lowered[:-3] + "y")
    if len(lowered) > 4 and lowered.endswith("ied"):
        candidates.add(lowered[:-3] + "y")
    if len(lowered) > 4 and lowered.endswith("ying"):
        candidates.add(lowered[:-4] + "ie")
    if len(lowered) > 5 and lowered.endswith("ing"):
        stem = lowered[:-3]
        candidates.update((stem, stem + "e"))
        if len(stem) > 3 and stem[-1] == stem[-2]:
            candidates.add(stem[:-1])
    if len(lowered) > 4 and lowered.endswith("ed"):
        stem = lowered[:-2]
        candidates.update((stem, lowered[:-1]))
        if len(stem) > 3 and stem[-1] == stem[-2]:
            candidates.add(stem[:-1])
        if lowered.endswith("cked"):
            candidates.add(lowered[:-3])
    if len(lowered) > 3 and lowered.endswith("s") and not lowered.endswith("ss"):
        candidates.add(lowered[:-1])
    if len(lowered) > 4 and lowered.endswith("es"):
        candidates.add(lowered[:-2])
    return frozenset(
        candidate
        for candidate in candidates
        if len(candidate) >= 3 and lowered in _regular_action_forms(candidate)
    )


def _action_particle_identity(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
) -> tuple[str, ...]:
    """Bind adjacent or terminally separated particles to their verb."""
    action = token_matches[action_index]
    particles: list[str] = []
    cursor = action.end()
    adjacent_stop = min(len(token_matches), action_index + 3)
    for following_index in range(action_index + 1, adjacent_stop):
        following = token_matches[following_index]
        if not re.fullmatch(r"\s+", text[cursor:following.start()]):
            break
        tokens = lexical_tokens(following.group(0))
        token = tokens[0] if len(tokens) == 1 else ""
        if not particles and token in ACTION_PARTICLES:
            particles.append(token)
            cursor = following.end()
            continue
        if particles and particles[-1] in {"away", "out"} and token in {"from", "of"}:
            particles.append(token)
        break
    if particles:
        return tuple(particles)

    # Separable phrasal verbs may place a marked object before the particle:
    # ``power the machine off``.  Accept only a terminal particle inside the
    # same bounded clause, so ordinary prepositional uses are not reclassified.
    cursor = action.end()
    saw_object = False
    separated_stop = min(len(token_matches), action_index + 17)
    for following_index in range(action_index + 1, separated_stop):
        following = token_matches[following_index]
        gap = text[cursor:following.start()]
        if ACTION_OBJECT_PUNCTUATION.search(gap):
            break
        tokens = lexical_tokens(following.group(0))
        token = tokens[0] if len(tokens) == 1 else ""
        if token in ACTION_PARTICLES:
            if not saw_object:
                break
            clause_end = _local_clause_end(text, following.end())
            if re.fullmatch(r"\s*", text[following.end():clause_end]):
                return (token,)
            break
        if token in OBJECT_PRONOUNS:
            saw_object = True
        elif token in OBJECT_BREAKS:
            break
        elif _action_content_term(token):
            saw_object = True
        cursor = following.end()
    return ()


def _action_mentions_same_verb(
    required_text: str,
    required: "BoundActionMention",
    candidate_text: str,
    candidate: "BoundActionMention",
) -> bool:
    """Compare known aliases and unseen inflections without a fixture lexicon."""
    required_surface = required_text[required.start:required.end]
    candidate_surface = candidate_text[candidate.start:candidate.end]
    required_keys = (
        frozenset({"found"})
        if required.action == "found" and required_surface.lower() == "found"
        else _action_inflection_keys(required_surface)
    )
    candidate_keys = (
        frozenset({"found"})
        if candidate.action == "found" and candidate_surface.lower() == "found"
        else _action_inflection_keys(candidate_surface)
    )
    same_lemma = bool(required_keys & candidate_keys)
    if not same_lemma:
        same_lemma = any(
            bool(required_keys & group) and bool(candidate_keys & group)
            for group in ACTION_SEMANTIC_EQUIVALENT_GROUPS
        )
    if not same_lemma:
        return False
    if required.particles == candidate.particles:
        return True
    # ``close up`` is an idiomatic scene-level completion whose visible proof
    # may be the final door/light closure rather than a repeated ``up`` token.
    return (
        required.action == "close"
        and required.particles == ("up",)
        and candidate.particles == ()
    )


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
    clause_end = _local_clause_end(text, match.end())
    nominal_surface = match.group(0).lower().replace("\u2019", "'")
    action_suffix = text[
        match.end():min(clause_end, match.end() + MAX_ACTION_GRAMMAR_WINDOW)
    ]
    denial_state = re.search(
        r"\b(?:is|are|was|were)\s+(?:explicitly\s+)?"
        r"(?:absent|denied|forbidden|missing|omitted|prevented|refused|"
        r"not\s+(?:allowed|completed|performed|shown))\b",
        action_suffix,
        re.I,
    )
    if (
        nominal_surface.endswith("ing")
        and denial_state is not None
        and not re.search(
            r"\b(?:and|but|whereas|while)\b",
            action_suffix[:denial_state.start()],
            re.I,
        )
    ):
        return True
    prefix_negated = match_is_negated(text, action_start)
    prefix_start = max(clause_start, action_start - MAX_ACTION_GRAMMAR_WINDOW)
    prefix = text[prefix_start:action_start]
    if re.search(
        r"(?:^|[,;:，；：])\s*(?:if|unless)\b[^.;!?。！？；]*$",
        prefix,
        re.I,
    ):
        return True
    if re.search(r"\bnot\s+only(?:\s+\w+ly)?\s*$", prefix, re.I):
        return False
    if re.search(
        r"\b(?:cannot|can['’]t)\s+not\s*$",
        prefix,
        re.I,
    ):
        return False
    if re.search(
        r"\b(?:(?:do(?:es)?|did|could)\s+not\s+"
        r"(?:avoid(?:s|ed|ing)?|refus(?:e|es|ed|ing))|"
        r"(?:cannot|can['’]t|could not)\s+help)\s*$",
        prefix,
        re.I,
    ):
        # These constructions entail the complement instead of merely making
        # it possible: ``could not avoid opening`` and ``cannot help opening``.
        return False
    if re.search(
        r"\b(?:do(?:es)?|did)\s+not\s+fail(?:s|ed)?\s+to\s*$",
        prefix,
        re.I,
    ):
        return False
    if re.search(
        r"\b(?:never|cannot|can['’]t)\s+fail(?:s|ed)?\s+to\s*$",
        prefix,
        re.I,
    ):
        return False
    if re.search(
        r"\b(?:cannot|can['’]t)\s+"
        r"(?:avoid(?:s|ed|ing)?|declin(?:e|es|ed|ing)|refus(?:e|es|ed|ing))"
        r"(?:\s+to)?\s*$",
        prefix,
        re.I,
    ):
        return False
    if ACTION_NONCOMMITTAL_PREFIX.search(prefix):
        return True
    negators = [
        negator
        for negator in ACTION_NEGATOR.finditer(prefix)
        if not position_is_quoted(text, prefix_start + negator.start())
    ]
    if not negators:
        return prefix_negated
    latest = negators[-1]
    if not prefix_negated and NEGATION_RESET.search(prefix[latest.end():]):
        return False
    negator_end = prefix_start + latest.end()
    prior_action_indices: list[int] = []
    for prior_index in range(action_index - 1, -1, -1):
        prior = token_matches[prior_index]
        if prior.start() < negator_end:
            break
        if (
            _general_action_syntax_candidate(text, token_matches, prior_index)
            and not position_is_quoted(text, prior.start())
        ):
            prior_action_indices.append(prior_index)
            break
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


ACTION_ASSERTED = "asserted"
ACTION_STATIVE = "stative"
ACTION_PROSPECTIVE = "prospective"
ACTION_HYPOTHETICAL = "hypothetical"
ACTION_REPRESENTED = "represented"
ACTION_NEGATED = "negated"


class BoundActionMention(NamedTuple):
    action: str
    start: int
    end: int
    positive: bool
    objects: tuple[str, ...]
    subjects: tuple[str, ...]
    status: str
    particles: tuple[str, ...] = ()


class BoundPropertyMention(NamedTuple):
    subjects: tuple[str, ...]
    properties: tuple[str, ...]
    values: tuple[str, ...]
    start: int


PRENOMINAL_RELATION = re.compile(
    r"\b(?P<object>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)-"
    r"(?P<form>carrying|holding|wearing)\b",
    re.I,
)


PROPERTY_TAIL_ACTIONS = ACTION_TRACE_TERMS | frozenset(
    (*TARGET_ACTION_BREAKS, "guide", "lead")
)


def _truncate_property_tail_at_action(
    tail: str,
    *,
    min_content: int,
) -> str:
    """Stop a property phrase before a following scene predicate."""
    content_count = 0
    for match in TOKEN.finditer(tail):
        action = _canonical_action_token(match.group(0))
        if content_count >= min_content and action in PROPERTY_TAIL_ACTIONS:
            return tail[:match.start()]
        if any(_action_content_term(token) for token in lexical_tokens(match.group(0))):
            content_count += 1
    return tail


@lru_cache(maxsize=4096)
def _bound_property_mentions(text: str) -> tuple[BoundPropertyMention, ...]:
    """Bind relative, ``with``, and ``in`` properties to their owning entity."""
    mentions: list[BoundPropertyMention] = []
    structural = structural_contract_terms(text)

    def append(
        subjects: tuple[str, ...],
        properties: tuple[str, ...],
        values: tuple[str, ...],
        start: int,
    ) -> None:
        if (
            not subjects
            or not properties
            or not values
            or not _position_is_output_semantic_evidence(text, start)
            or set(subjects).issubset(structural)
            or (set(properties) & structural and set(values) & structural)
        ):
            return
        if subjects and properties and values:
            mentions.append(BoundPropertyMention(
                subjects=subjects,
                properties=_compact_object_identity(list(properties)),
                values=_compact_object_identity(list(values)),
                start=start,
            ))

    for marker in re.finditer(r"\bwhose\b", text, re.I):
        if position_is_quoted(text, marker.start()) or _position_is_displayed_text(
            text, marker.start()
        ):
            continue
        local_start = max(
            text.rfind(boundary, 0, marker.start())
            for boundary in ",.;!?。！？；\n"
        ) + 1
        subjects = _nearest_subject_identity(text[local_start:marker.start()])
        if not subjects:
            continue
        tail_boundary = re.search(r"[,.;!?。！？；\n]", text[marker.end():])
        tail_end = (
            marker.end() + tail_boundary.start()
            if tail_boundary is not None
            else len(text)
        )
        tail_end = min(
            tail_end, _output_semantic_evidence_end(text, marker.start())
        )
        tail = _truncate_property_tail_at_action(
            text[marker.end():tail_end], min_content=2
        )
        copula = re.search(
            r"\b(?:appears?|are|is|looks?|was|were)\b", tail, re.I
        )
        if copula is not None:
            property_text = tail[:copula.start()]
            value_text = tail[copula.end():]
        else:
            material = [
                match for match in TOKEN.finditer(tail)
                if lexical_tokens(match.group(0))
            ]
            if len(material) < 2:
                continue
            property_text = tail[:material[1].start()]
            value_text = tail[material[1].start():]
        properties = tuple(
            token
            for token in lexical_tokens(property_text)
            if _action_content_term(token)
        )
        values = tuple(
            token
            for token in lexical_tokens(value_text)
            if _action_content_term(token)
        )
        append(subjects, properties, values, marker.start())

    for marker in re.finditer(r"\b(?:that|which)\b", text, re.I):
        if position_is_quoted(text, marker.start()) or _position_is_displayed_text(
            text, marker.start()
        ):
            continue
        local_start = max(
            text.rfind(boundary, 0, marker.start())
            for boundary in ",.;!?。！？；\n"
        ) + 1
        subjects = _nearest_subject_identity(text[local_start:marker.start()])
        if not subjects:
            continue
        copula = re.match(
            r"\s+(?:appears?|are|is|looks?|was|were)\s+",
            text[marker.end():],
            re.I,
        )
        if copula is None:
            continue
        value_start = marker.end() + copula.end()
        tail_end_match = re.search(r"[,.;!?\n]", text[value_start:])
        value_end = (
            value_start + tail_end_match.start()
            if tail_end_match is not None
            else len(text)
        )
        value_end = min(
            value_end, _output_semantic_evidence_end(text, marker.start())
        )
        value_tail = _truncate_property_tail_at_action(
            text[value_start:value_end], min_content=1
        )
        value_end = value_start + len(value_tail)
        next_owner = re.search(
            r"\band\s+(?:a|an|the)?\s*"
            r"(?:[A-Za-z0-9'-]+\s+){0,4}(?:that|which)\b",
            text[value_start:value_end],
            re.I,
        )
        if next_owner is not None:
            value_end = value_start + next_owner.start()
        values = tuple(
            token
            for token in lexical_tokens(text[value_start:value_end])
            if _action_content_term(token)
        )
        append(subjects, ("appearance",), values, marker.start())

    for marker in re.finditer(r"\bwith\b", text, re.I):
        if position_is_quoted(text, marker.start()) or _position_is_displayed_text(
            text, marker.start()
        ):
            continue
        local_start = max(
            text.rfind(boundary, 0, marker.start())
            for boundary in ",.;!?。！？；\n"
        ) + 1
        prefix = text[local_start:marker.start()]
        if any(
            _canonical_action_token(token.group(0)) in TARGET_ACTION_BREAKS
            for token in TOKEN.finditer(prefix)
        ):
            continue
        subjects = _nearest_subject_identity(prefix)
        if not subjects:
            continue
        tail_boundary = re.search(r"[,.;!?。！？；\n]", text[marker.end():])
        tail_end = (
            marker.end() + tail_boundary.start()
            if tail_boundary is not None
            else len(text)
        )
        tail_end = min(
            tail_end, _output_semantic_evidence_end(text, marker.start())
        )
        tail = _truncate_property_tail_at_action(
            text[marker.end():tail_end], min_content=2
        )
        next_owner = re.search(
            r"\band\s+(?:a|an|the)\b[^,.;!?]{0,48}\bwith\b",
            tail,
            re.I,
        )
        if next_owner is not None:
            tail = tail[:next_owner.start()]
        parts = re.split(r"\band\b", tail, flags=re.I)
        part_material = [
            [
                token
                for token in lexical_tokens(part)
                if _action_content_term(token)
            ]
            for part in parts
        ]
        if len(parts) > 1 and not all(len(material) >= 2 for material in part_material):
            parts = [tail]
        for part in parts:
            relative = re.fullmatch(
                r"\s*(?:a|an|the)?\s*(?P<property>[A-Za-z0-9'-]+"
                r"(?:\s+[A-Za-z0-9'-]+){0,3}?)\s+"
                r"(?:that|which)\s+(?:appears?|are|is|looks?|was|were)\s+"
                r"(?P<value>[A-Za-z0-9'-]+(?:\s+[A-Za-z0-9'-]+){0,2})\s*",
                part,
                re.I,
            )
            if relative is not None:
                properties = tuple(
                    token
                    for token in lexical_tokens(relative.group("property"))
                    if _action_content_term(token)
                )
                values = tuple(
                    token
                    for token in lexical_tokens(relative.group("value"))
                    if _action_content_term(token)
                )
            else:
                material = [
                    token
                    for token in lexical_tokens(part)
                    if _action_content_term(token)
                ]
                if len(material) < 2:
                    continue
                properties = (material[-1],)
                values = tuple(material[:-1])
            append(subjects, properties, values, marker.start())

    for marker in re.finditer(
        r"\bin\s+(?:(?:a|an|the)\s+)?"
        r"(?P<value>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?)"
        r"(?:\s+(?P<property>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?))?"
        r"(?=\s*(?:$|[,.;!?]|\b(?:alongside|and|beside|near|while|with)\b))",
        text,
        re.I,
    ):
        if position_is_quoted(text, marker.start()) or _position_is_displayed_text(
            text, marker.start()
        ):
            continue
        local_start = max(
            text.rfind(boundary, 0, marker.start())
            for boundary in ",.;!?。！？；\n"
        ) + 1
        prefix = text[local_start:marker.start()]
        if any(
            _canonical_action_token(token.group(0)) in TARGET_ACTION_BREAKS
            for token in TOKEN.finditer(prefix)
        ):
            continue
        subjects = _nearest_subject_identity(prefix)
        values = tuple(
            token
            for token in lexical_tokens(marker.group("value"))
            if _action_content_term(token)
        )
        if any(value in PRODUCTION_GENERIC for value in values):
            continue
        property_surface = marker.group("property")
        properties = tuple(
            token
            for token in lexical_tokens(property_surface or "")
            if _action_content_term(token)
        )
        if not properties:
            # A single complement is ordinarily a location (``in a studio``),
            # not an appearance relation.  ``surgeon in red`` remains covered
            # by the explicit wear-action equivalence without turning every
            # location into a movable colour/property contract.
            continue
        append(
            subjects,
            properties,
            values,
            marker.start(),
        )

    return tuple(sorted(mentions, key=lambda mention: mention.start))


def _action_match_status(
    text: str,
    token_matches: list[re.Match[str]],
    action_index: int,
) -> str:
    """Classify an action as an asserted event or a non-event description."""
    match = token_matches[action_index]
    prefix = _bounded_action_prefix(text, match.start())
    resets = list(ACTION_CONTEXT_RESET.finditer(prefix))
    governor_prefix = prefix[resets[-1].end():] if resets else prefix
    clause_end = _local_clause_end(text, match.end())
    suffix = text[match.end():min(clause_end, match.end() + MAX_ACTION_GRAMMAR_WINDOW)]
    punctuation = text[clause_end:clause_end + 1]
    polite_you_request = bool(
        punctuation == "?"
        and re.match(r"\s*(?:can|could|would)\s+you\b", governor_prefix, re.I)
    )
    if (
        punctuation == "?"
        and not polite_you_request
        and re.match(
            r"\s*(?:can|could|may|might|shall|should|will|would)\b",
            governor_prefix,
            re.I,
        )
    ):
        return ACTION_HYPOTHETICAL
    if ACTION_HYPOTHETICAL_CONTEXT.search(governor_prefix):
        return ACTION_HYPOTHETICAL
    if ACTION_STATIVE_PREFIX.search(governor_prefix):
        return ACTION_STATIVE
    if (
        ACTION_REPRESENTED_PREFIX.search(governor_prefix)
        or ACTION_REPRESENTED_CONTEXT.search(governor_prefix)
    ):
        return ACTION_REPRESENTED
    nominal_surface = match.group(0).lower().replace("\u2019", "'")
    if nominal_surface.endswith("ing") and re.search(
        r"\b(?:is|are|was|were)\s+(?:expected|planned|scheduled)\b",
        suffix,
        re.I,
    ):
        return ACTION_PROSPECTIVE
    if (
        ACTION_PROSPECTIVE_PREFIX.search(governor_prefix)
        or (
            not polite_you_request
            and ACTION_PROSPECTIVE_CONTEXT.search(governor_prefix)
        )
    ):
        return ACTION_PROSPECTIVE
    if _action_match_is_negated(text, token_matches, action_index):
        return ACTION_NEGATED
    return ACTION_ASSERTED


@lru_cache(maxsize=4096)
def _bound_action_mentions(text: str) -> tuple[BoundActionMention, ...]:
    """Extract bounded, status-, actor-, and object-aware action mentions.

    The object binding prevents a required case action from being satisfied or
    reversed by an unrelated door action. Negated actions remain available as
    antecedents for a later ``it``, while quoted dialogue never becomes action
    evidence.
    """
    token_matches = list(TOKEN.finditer(text))
    mentions: list[dict[str, object]] = []

    for index, match in enumerate(token_matches):
        canonical_action = _canonical_action_at(text, token_matches, index)
        if position_is_quoted(text, match.start()) or _position_is_displayed_text(
            text, match.start()
        ) or not _position_is_output_semantic_evidence(text, match.start()):
            continue
        if not _general_action_syntax_candidate(text, token_matches, index):
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
                object_terms = _coordinated_shared_object_identity(
                    text, token_matches, index
                ) or _object_relative_antecedent_identity(
                    text, token_matches, index
                )
                if not object_terms and _action_surface_is_passive(
                    text, token_matches, index
                ):
                    object_terms = _subject_object_identity(
                        text, token_matches, index
                    )

        fallback_subject = (
            tuple(mentions[-1]["subjects"]) if mentions else ()
        )
        subjects = _action_subject_identity(
            text, token_matches, index, fallback_subject
        )
        status = _action_match_status(text, token_matches, index)
        mentions.append({
            "action": canonical_action,
            "start": match.start(),
            "end": match.end(),
            "positive": status == ACTION_ASSERTED,
            "objects": object_terms,
            "subjects": subjects,
            "status": status,
            "pronoun": pronoun_object,
            "particles": _action_particle_identity(text, token_matches, index),
        })

    # Hyphenated relation adjectives encode the same actor/object relation as a
    # relative clause: ``a red-wearing surgeon`` means the surgeon wears red.
    # TOKEN deliberately keeps compounds together, so add these bounded
    # relations explicitly instead of flattening all adjectives globally.
    for relation in PRENOMINAL_RELATION.finditer(text):
        if position_is_quoted(text, relation.start()) or _position_is_displayed_text(
            text, relation.start()
        ) or not _position_is_output_semantic_evidence(text, relation.start()):
            continue
        subjects = _leading_subject_identity(text[relation.end():])
        objects = tuple(
            token
            for token in lexical_tokens(relation.group("object"))
            if _action_content_term(token)
        )
        action = _canonical_action_token(relation.group("form"))
        if not subjects or not objects or action not in TARGET_SHARED_RELATIONS:
            continue
        status = (
            ACTION_NEGATED
            if match_is_negated(text, relation.start())
            else ACTION_ASSERTED
        )
        mentions.append({
            "action": action,
            "start": relation.start("form"),
            "end": relation.end("form"),
            "positive": status == ACTION_ASSERTED,
            "objects": _compact_object_identity(list(objects)),
            "subjects": subjects,
            "status": status,
            "pronoun": False,
            "particles": (),
        })

    mentions.sort(key=lambda mention: int(mention["start"]))

    return tuple(
        BoundActionMention(
            action=str(mention["action"]),
            start=int(mention["start"]),
            end=int(mention["end"]),
            positive=bool(mention["positive"]),
            objects=tuple(mention["objects"]),
            subjects=tuple(mention["subjects"]),
            status=str(mention["status"]),
            particles=tuple(mention["particles"]),
        )
        for mention in mentions
    )


def action_mentions(
    text: str,
) -> tuple[tuple[str, int, int, bool, tuple[str, ...]], ...]:
    """Compatibility view of opposite-action mentions used by public tests."""
    return tuple(
        (mention.action, mention.start, mention.end, mention.positive, mention.objects)
        for mention in _bound_action_mentions(text)
        if mention.action in OPPOSITE_ACTION_TERMS
    )


def _action_objects_compatible(
    left: BoundActionMention,
    right: BoundActionMention,
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


def _action_subjects_compatible(
    required: BoundActionMention,
    candidate: BoundActionMention,
    *,
    left_requires_subject: bool = True,
) -> bool:
    """Require the same actor head and every required actor discriminator."""
    if not left_requires_subject:
        return True
    def normalize(subjects: tuple[str, ...]) -> frozenset[str]:
        return frozenset(
            "smith" if subject.endswith("smith") else subject
            for subject in subjects
        )

    left_subjects, right_subjects = required.subjects, candidate.subjects
    if not left_subjects:
        return True
    if not right_subjects:
        return False
    if right_subjects == ("__implicit__",):
        # Polite/bare imperatives request the depicted action without naming a
        # replacement actor. They are not actor evidence, but neither are they
        # a contradictory explicit actor like ``the case opens``.
        return True
    return normalize(left_subjects).issubset(normalize(right_subjects))


def _mention_requires_actor_binding(
    text: str,
    mention: BoundActionMention,
) -> bool:
    """Distinguish entity actions from idiomatic scene-level phrasal verbs."""
    if mention.action == "close" and re.match(
        r"\s+up\b", text[mention.end:], re.I
    ):
        return False
    return bool(mention.subjects and mention.subjects != ("__implicit__",))


def _mention_has_explicit_object(
    text: str,
    mention: BoundActionMention,
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


def _action_objects_match_requirement(
    brief: str,
    required: BoundActionMention,
    candidate: BoundActionMention,
    *,
    requires_object: bool,
) -> bool:
    """Match one object or any grammar-bound ``or`` object alternative."""
    if _action_objects_compatible(
        required,
        candidate,
        left_requires_object=requires_object,
    ):
        return True
    if required.action not in TARGET_SHARED_RELATIONS:
        return False
    candidate_terms = frozenset((
        *candidate.subjects,
        candidate.action,
        *candidate.objects,
    ))
    return any(
        required.action in group and group.issubset(candidate_terms)
        for clause in explicit_target_requirement_clauses(brief)
        for group in clause
    )


def _wear_requirement_has_in_attribute(
    prompt: str,
    required: BoundActionMention,
) -> bool:
    """Recognize ``surgeon in red`` as a bounded variant of ``wears red``."""
    if required.action != "wear" or not required.objects:
        return False
    for marker in re.finditer(
        r"\bin\s+(?P<value>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?)"
        r"(?=\s*(?:$|[,.;!?]|\band\b|\bwhile\b))",
        prompt,
        re.I,
    ):
        if not _position_is_output_semantic_evidence(prompt, marker.start()):
            continue
        value = _compact_object_identity([
            token
            for token in lexical_tokens(marker.group("value"))
            if _action_content_term(token)
        ])
        if not _identity_terms_compatible(required.objects, value):
            continue
        local_start = max(
            prompt.rfind(boundary, 0, marker.start())
            for boundary in ",.;!?。！？；\n"
        ) + 1
        subject = _nearest_subject_identity(prompt[local_start:marker.start()])
        candidate = BoundActionMention(
            action="wear",
            start=marker.start(),
            end=marker.end(),
            positive=True,
            objects=value,
            subjects=subject,
            status=ACTION_ASSERTED,
        )
        if _action_subjects_compatible(required, candidate):
            return True
    return False


def missing_positive_action_requirements(
    brief: str,
    prompt: str,
) -> tuple[str, ...]:
    """Return explicit positive brief actions absent on a compatible object."""
    required = [
        mention
        for mention in _bound_action_mentions(brief)
        if mention.positive
        and not (mention.action == "close" and mention.particles == ("up",))
    ]
    supplied = [mention for mention in _bound_action_mentions(prompt) if mention.positive]
    missing: set[str] = set()
    for mention in required:
        requires_object = _mention_has_explicit_object(brief, mention)
        if mention.action == "pour" and set(mention.objects) & {
            "art", "pattern", "rosetta",
        }:
            # ``pour latte art`` names the result; the grammatical material in
            # the expanded prompt is milk/foam rather than the finished motif.
            requires_object = False
        requires_actor = _mention_requires_actor_binding(brief, mention)
        if any(
            _action_mentions_same_verb(brief, mention, prompt, candidate)
            and _action_subjects_compatible(
                mention, candidate, left_requires_subject=requires_actor
            )
            and _action_objects_match_requirement(
                brief,
                mention,
                candidate,
                requires_object=requires_object,
            )
            for candidate in supplied
        ) or _wear_requirement_has_in_attribute(prompt, mention):
            continue
        actor_label = " ".join(mention.subjects)
        object_label = " ".join(mention.objects)
        missing.add(
            f"{actor_label} {mention.action} {object_label}".strip()
        )
    return tuple(sorted(missing))


def _identity_terms_compatible(
    required: tuple[str, ...],
    candidate: tuple[str, ...],
) -> bool:
    if not required or not candidate:
        return not required
    return (
        required[-1] == candidate[-1]
        and set(required[:-1]).issubset(candidate[:-1])
    )


def _prompt_has_prenominal_appearance(
    prompt: str,
    relation: BoundPropertyMention,
) -> bool:
    """Match ``case that is red`` to the same bounded ``red case`` entity."""
    if relation.properties != ("appearance",) or not relation.subjects:
        return False
    token_matches = list(TOKEN.finditer(prompt))
    required_subject = relation.subjects[-1]
    required_values = set(relation.values)
    for index, match in enumerate(token_matches):
        tokens = lexical_tokens(match.group(0))
        if len(tokens) != 1 or tokens[0] != required_subject:
            continue
        if position_is_quoted(prompt, match.start()) or _position_is_displayed_text(
            prompt, match.start()
        ) or not _position_is_output_semantic_evidence(prompt, match.start()):
            continue
        modifiers: list[str] = []
        cursor = match.start()
        for previous in reversed(token_matches[max(0, index - 5):index]):
            gap = prompt[previous.end():cursor]
            if re.search(r"[,.;!?\n]", gap):
                break
            previous_tokens = lexical_tokens(previous.group(0))
            if len(previous_tokens) != 1:
                break
            token = previous_tokens[0]
            cursor = previous.start()
            if token in {"a", "an", "another", "and", "or", "the"}:
                break
            if token in SUBJECT_BOUNDARY_TERMS or not _action_content_term(token):
                break
            modifiers[0:0] = [token]
        if required_values.issubset(modifiers):
            return True
    return False


def _property_is_supplied_by_wear(
    prompt: str,
    relation: BoundPropertyMention,
) -> bool:
    """Bridge ``with a red scarf`` to the explicit ``wearing a red scarf``."""
    if not relation.subjects or not relation.properties or not relation.values:
        return False
    property_head = relation.properties[-1]
    required_values = set(relation.values)
    return any(
        mention.positive
        and mention.action == "wear"
        and set(relation.subjects).issubset(mention.subjects)
        and mention.objects
        and mention.objects[-1] == property_head
        and required_values.issubset(mention.objects[:-1])
        for mention in _bound_action_mentions(prompt)
    )


def missing_bound_property_requirements(
    brief: str,
    prompt: str,
) -> tuple[str, ...]:
    """Return relative-clause properties moved to a different entity."""
    required = _bound_property_mentions(brief)
    supplied = _bound_property_mentions(prompt)
    missing: set[str] = set()
    for relation in required:
        if any(
            set(relation.subjects).issubset(candidate.subjects)
            and _identity_terms_compatible(relation.properties, candidate.properties)
            and _identity_terms_compatible(relation.values, candidate.values)
            for candidate in supplied
        ) or _prompt_has_prenominal_appearance(
            prompt, relation
        ) or _property_is_supplied_by_wear(prompt, relation):
            continue
        missing.add(" ".join((
            *relation.subjects,
            "whose",
            *relation.properties,
            *relation.values,
        )))
    return tuple(sorted(missing))


def reversed_action_requirements(brief: str, prompt: str) -> tuple[str, ...]:
    """Return brief actions replaced solely by their explicit opposites.

    Shared subjects, props, colours, and locations cannot compensate for an
    inverted requested endpoint. A prompt that still contains the requested
    action is not rejected here: it may be describing a legitimate sequence.
    """
    brief_mentions = [
        mention for mention in _bound_action_mentions(brief) if mention.positive
    ]
    prompt_mentions = [
        mention for mention in _bound_action_mentions(prompt) if mention.positive
    ]
    reversals: set[str] = set()

    for pair in OPPOSITE_ACTIONS:
        for brief_mention in (
            mention for mention in brief_mentions if mention[0] in pair
        ):
            required_action = brief_mention[0]
            opposite_action = next(iter(pair - {required_action}))
            requires_object = _mention_has_explicit_object(brief, brief_mention)
            requires_actor = _mention_requires_actor_binding(brief, brief_mention)
            required_survives = any(
                mention[0] == required_action
                and _action_subjects_compatible(
                    brief_mention,
                    mention,
                    left_requires_subject=requires_actor,
                )
                and _action_objects_compatible(
                    brief_mention,
                    mention,
                    left_requires_object=requires_object,
                )
                for mention in prompt_mentions
            )
            opposite_survives = any(
                mention[0] == opposite_action
                and _action_subjects_compatible(
                    brief_mention,
                    mention,
                    left_requires_subject=requires_actor,
                )
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


ENTITY_SPAN_BREAKS = {
    "after", "alongside", "and", "as", "at", "before", "behind", "beside", "but",
    "during", "inside", "near", "on", "or", "outside", "under", "versus",
    "well", "while", "whereas", "with", "without", "plus",
}


def _entity_content_term(token: str) -> bool:
    return _action_content_term(token) or (
        len(token) > 2
        and token.endswith("ly")
        and token not in FUNCTION_WORDS
        and token not in PRODUCTION_GENERIC
        and token not in TRACE_GENERIC
        and token not in TARGET_CONTROL_TERMS
    )


@lru_cache(maxsize=4096)
def _affirmative_entity_term_groups(text: str) -> tuple[frozenset[str], ...]:
    """Return local entity phrases so global word co-occurrence cannot pass.

    This is intentionally used only for non-action target groups. Action groups
    have their own actor/object binder. Determiners, scene relations, finite
    action predicates, and hard punctuation close one entity span; appositive
    forms such as ``Mara, the surgeon`` stay together.
    """
    groups: list[frozenset[str]] = []
    current: list[str] = []
    current_surfaces: list[str] = []
    cursor = 0

    def flush() -> None:
        if current:
            groups.append(frozenset(current))
            current.clear()
            current_surfaces.clear()

    for match in TOKEN.finditer(text):
        gap = text[cursor:match.start()]
        cursor = match.end()
        if re.search(r"[.;!?\n+&/]", gap):
            flush()
        surface_tokens = lexical_tokens(match.group(0))
        if len(surface_tokens) != 1:
            material = [
                token for token in surface_tokens if _entity_content_term(token)
            ]
            if material:
                current.extend(material)
                current_surfaces.extend([match.group(0)] * len(material))
            continue
        token = surface_tokens[0]
        named_appositive = bool(
            "," in gap
            and token in {"a", "an", "the"}
            and current_surfaces
            and all(surface[:1].isupper() for surface in current_surfaces)
        )
        if "," in gap and not named_appositive:
            # Bare comma lists name separate entities. Preserve only the common
            # named appositive shapes ``Mara, a surgeon`` and
            # ``Doctor Mara, the masked surgeon``.
            flush()
        if token in {"a", "an", "another"}:
            if not named_appositive:
                flush()
            continue
        if token in ENTITY_SPAN_BREAKS:
            flush()
            continue
        canonical_action = _canonical_action_token(match.group(0))
        if canonical_action in TARGET_ACTION_BREAKS:
            flush()
            continue
        if (
            position_is_quoted(text, match.start())
            or match_is_negated(text, match.start())
            or _position_is_postpositively_excluded(text, match.start())
            or _position_is_displayed_text(text, match.start())
            or (
                not _position_is_output_semantic_evidence(text, match.start())
                and not _position_is_included_output_antecedent(
                    text, match.start()
                )
            )
        ):
            continue
        if _entity_content_term(token):
            current.append(token)
            current_surfaces.append(match.group(0))
    flush()
    return tuple(dict.fromkeys(groups))


def _target_group_is_bound_in_prompt(
    prompt: str,
    group: frozenset[str],
    prompt_terms: frozenset[str],
) -> bool:
    if not group.issubset(prompt_terms):
        return False
    entity_groups = _affirmative_entity_term_groups(prompt)
    locally_bound = (
        bool(group & ACTION_TRACE_TERMS)
        or any(
            group.issubset(entity_terms)
            for entity_terms in entity_groups
        )
    )
    return locally_bound


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
        if not any(
            _target_group_is_bound_in_prompt(prompt, group, prompt_terms)
            for group in clause
        )
    ]
    if missing_clauses:
        closest_group = min(
            (group for clause in missing_clauses for group in clause),
            key=lambda group: (len(group - prompt_terms), sorted(group)),
        )
        missing_targets = sorted(closest_group - prompt_terms)
        if not missing_targets:
            return 0.0, (
                "requested target modifiers and head are not bound to one "
                "entity: " + ", ".join(sorted(closest_group))
            )
        return 0.0, (
            "requested target changed or disappeared; missing: "
            + ", ".join(missing_targets)
        )
    missing_properties = missing_bound_property_requirements(brief, prompt)
    if missing_properties:
        return 0.0, (
            "requested entity property moved or disappeared: "
            + ", ".join(missing_properties)
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


def _positive_while_reset_positions(clause: str) -> list[int]:
    """Locate affirmative light predicates introduced by ``while``.

    Polarity is decided only from the bounded text before the predicate.  A
    later modifier such as ``without flicker`` therefore cannot retroactively
    turn an affirmative illumination clause into an exclusion reset.
    """
    positions: list[int] = []
    for match in POSITIVE_WHILE_RESET.finditer(clause):
        # Negation belongs to the predicate only when it survives the most
        # recent coordination boundary.  ``does not move and sunlight
        # illuminates`` must not negate ``illuminates``; coordinated subjects
        # such as ``sunlight and moonlight do not illuminate`` still retain
        # their local ``do not`` tail after the split.
        prefix = match.group("prefix")
        boundaries = list(PREDICATE_COORDINATION_BOUNDARY.finditer(prefix))
        local_start = boundaries[-1].end() if boundaries else 0
        predicate_prefix = prefix[local_start:][-48:]
        if NEGATED_PREFIX.search(predicate_prefix) is not None:
            continue
        positions.append(match.start())
        if local_start:
            # End an unrelated scoped negation (for example ``does not move``)
            # before the affirmative light subject that follows coordination.
            positions.append(match.start("prefix") + local_start)
    return positions


@lru_cache(maxsize=4096)
def _scoped_exclusion_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Index clause-scoped exclusions once instead of rescanning per token."""
    spans: list[tuple[int, int]] = []
    clause_start = 0
    boundaries = list(re.finditer(r"[.;!?。！？；\n]", text))
    for boundary in [*boundaries, None]:
        clause_end = boundary.start() if boundary is not None else len(text)
        clause = text[clause_start:clause_end]
        double_index = _interval_index(_merge_intervals([
            (match.start(), match.end())
            for match in DOUBLE_NEGATED_EXCLUSION.finditer(clause)
        ]))
        reset_positions = sorted(
            [match.start() for match in NEGATION_RESET.finditer(clause)]
            + _positive_while_reset_positions(clause)
        )
        for exclusion in SCOPED_EXCLUSION.finditer(clause):
            if position_is_quoted(text, clause_start + exclusion.start()):
                continue
            double_starts, double_ends = double_index
            double_slot = bisect_right(double_starts, exclusion.start()) - 1
            if (
                double_slot >= 0
                and double_starts[double_slot] <= exclusion.start()
                < double_ends[double_slot]
            ):
                continue
            reset_index = bisect_left(reset_positions, exclusion.end())
            scope_end = (
                reset_positions[reset_index]
                if reset_index < len(reset_positions)
                else len(clause)
            )
            spans.append(
                (clause_start + exclusion.start(), clause_start + scope_end)
            )
        clause_start = boundary.end() if boundary is not None else len(text)
    return _interval_index(_merge_intervals(spans))


@lru_cache(maxsize=4096)
def _entailed_action_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Index complements whose surface negation logically entails the event."""
    spans: list[tuple[int, int]] = []
    for match in ENTAILED_ACTION_COMPLEMENT.finditer(text):
        clause_end = ACTION_CLAUSE_PUNCTUATION.search(text, match.end("action"))
        end = clause_end.start() if clause_end is not None else len(text)
        reset = NEGATION_RESET.search(text, match.end("action"), end)
        if reset is not None:
            end = reset.start()
        spans.append((max(0, match.start("action") - 1), end))
    return _interval_index(_merge_intervals(spans))


def match_is_negated(text: str, start: int) -> bool:
    if _position_in_interval_index(_entailed_action_interval_index(text), start):
        return False
    short_window_start = max(0, start - 36)
    short_prefix = text[short_window_start:start]
    boundaries = list(PREDICATE_COORDINATION_BOUNDARY.finditer(short_prefix))
    if boundaries:
        local_start = boundaries[-1].end()
        short_window_start += local_start
        short_prefix = short_prefix[local_start:]
    short_match = NEGATED_PREFIX.search(short_prefix)
    if short_match:
        global_short_start = short_window_start + short_match.start()
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
    # naming a light or sound source. Their scope is indexed once per text and
    # ends at an explicit contrast/reset such as ``but keep neon``.
    return _position_in_interval_index(
        _scoped_exclusion_interval_index(text), start
    )


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

    def add_fences(mark: str) -> None:
        """Pair Markdown-style fences before shorter inline delimiters.

        A valid closer may be longer than its opener. This covers mixed-width
        backtick fences and the equivalent tilde form without letting an
        unmatched opener swallow the rest of a prompt.
        """
        escaped = re.escape(mark)
        fence = re.compile(rf"(?<!{escaped}){escaped}{{3,}}(?!{escaped})")
        cursor = 0
        while True:
            opener = fence.search(text, cursor)
            if opener is None:
                return
            width = opener.end() - opener.start()
            closer = re.compile(
                rf"(?<!{escaped}){escaped}{{{width},}}(?!{escaped})"
            ).search(
                text, opener.end()
            )
            if closer is None:
                cursor = opener.end()
                continue
            spans.append((opener.start(), closer.end()))
            occupied.update(range(opener.start(), opener.end()))
            occupied.update(range(closer.start(), closer.end()))
            cursor = closer.end()

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
        ("【", "】"),
        ("〔", "〕"),
        ("〖", "〗"),
        ("〘", "〙"),
        ("〚", "〛"),
        ("﹁", "﹂"),
        ("﹃", "﹄"),
        ("｢", "｣"),
        ("⟪", "⟫"),
        ("［", "］"),
        ("❝", "❞"),
        ("〝", "〟"),
    ):
        add_asymmetric(opener, closer)
    add_fences("`")
    add_fences("~")
    add_symmetric("``")
    add_symmetric('"')
    add_symmetric("＂")
    add_symmetric("'", apostrophe_aware=True)
    add_symmetric("`", apostrophe_aware=True)
    return _merge_intervals(spans)


@lru_cache(maxsize=4096)
def _quoted_interval_index(
    text: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    return _interval_index(_quoted_spans(text))


def position_is_quoted(text: str, position: int) -> bool:
    """Return whether a control word is inside a balanced quoted span."""
    return _position_in_interval_index(_quoted_interval_index(text), position)


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
        and not _position_is_displayed_text(text, match.start())
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


def _bridge_has_explicit_phase_boundary(bridge: str) -> bool:
    if re.search(
        r"(?:^|[.!?。！？；;\n])\s*(?:and\s+)?"
        r"(?:afterward|afterwards|subsequently|soon\s+afterwards?|"
        r"following\s+that|seconds?\s+later|"
        r"a\s+(?:beat|moment)\s+later|moments?\s+later)"
        r"\s*(?::|,|[-\u2013\u2014])?\s*"
        r"(?:(?:the|a|an|near|absolute|complete|completely|slow|slowly)[-\s]*){0,2}$",
        bridge,
        re.I,
    ):
        return True

    for label in EXPLICIT_PHASE_LABEL.finditer(bridge):
        before_label = bridge[:label.start()]
        boundary_positions = [
            match.end()
            for match in re.finditer(r"[.!?。！？；;，,\n]", before_label)
        ]
        lead = before_label[boundary_positions[-1]:] if boundary_positions else before_label
        if not re.fullmatch(
            r"\s*(?:(?:at|during|for|in|on)\s+(?:the\s+)?|"
            r"at\s+the\s+start\s+of\s+)?",
            lead,
            re.I,
        ):
            continue
        if PHASE_CUE_TAIL.fullmatch(bridge[label.end():]):
            return True
    return False


def _bridge_has_semantic_event_transition(
    text: str,
    left_end: int,
    right_start: int,
    right_end: int,
) -> bool:
    """Recognize a directly bound, asserted state change as a phase boundary.

    The transition matrix is intentionally directional and pair-local.  A cue
    in quoted/displayed copy, a hypothetical or negated cue, an unrelated
    reporting clause, or an explicit simultaneity bridge cannot split phases.
    """
    bridge = text[left_end:right_start]
    if not bridge or len(bridge) > 320:
        return False
    local_end_match = re.search(
        r"[.;!?\u2026\u061f\u3002\uff01\uff1f\uff1b\n]", text[right_end:]
    )
    local_end = (
        right_end + local_end_match.start()
        if local_end_match is not None
        else min(len(text), right_end + 240)
    )
    post_directive = text[right_end:local_end]
    if SEMANTIC_EVENT_TRANSITION_POST_BLOCKER.search(post_directive):
        return False
    for cue in SEMANTIC_EVENT_TRANSITION_CUE.finditer(bridge):
        lead = bridge[:cue.start()]
        tail = bridge[cue.end():]
        if (
            not SEMANTIC_EVENT_TRANSITION_LEAD.fullmatch(lead)
            or SEMANTIC_EVENT_TRANSITION_BLOCKER.search(bridge)
        ):
            continue
        if re.search(r"\bit\b", lead, re.I):
            antecedent = text[max(0, left_end - 120):left_end]
            if re.search(
                r"\b(?:the\s+)?(?:frame|framing|image|picture|scene|shot|"
                r"state|view)\b[^.;!?\u2026\u061f]{0,80}$",
                antecedent,
                re.I,
            ) is None:
                continue
        cue_start = left_end + cue.start()
        if (
            position_is_quoted(text, cue_start)
            or _position_is_displayed_text(text, cue_start)
            or not _position_is_output_semantic_evidence(text, cue_start)
            or match_is_negated(text, cue_start)
        ):
            continue
        if (
            PHASE_CUE_TAIL.fullmatch(tail)
            or SEMANTIC_EVENT_TRANSITION_COMPLETED_TAIL.fullmatch(tail)
        ):
            return True
    return False


def directive_pair_is_sequenced(
    text: str,
    left: tuple[int, int],
    right: tuple[int, int],
) -> bool:
    (left_start, left_end), (right_start, right_end) = sorted((left, right))
    # A simultaneity qualifier can follow the final directive, outside its
    # regex match. Inspect only the remainder of its local clause so an
    # unrelated cue in a later sentence cannot poison a valid transition.
    local_end_match = re.search(r"[.;!?\u2026\u061f。！？；\n]", text[right_end:])
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
    if _bridge_has_explicit_phase_boundary(bridge):
        return True
    # Permit an explicit event boundary only when it culminates in a cue
    # directly attached to the later directive. An unrelated "then/before"
    # elsewhere between the directives is not enough.
    if EVENT_SEQUENCE_BRIDGE.fullmatch(bridge):
        return True
    if _bridge_has_semantic_event_transition(
        text, left_end, right_start, right_end
    ):
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


def directive_phase_groups(
    text: str,
    directives: list[tuple[str, int, int]],
) -> list[list[tuple[str, int, int]]]:
    """Partition complete directives by explicit pair-local boundaries."""
    if not directives:
        return []
    ordered = sorted(set(directives), key=lambda item: (item[1], item[2], item[0]))
    phases: list[list[tuple[str, int, int]]] = [[ordered[0]]]
    previous = (ordered[0][1], ordered[0][2])
    for directive in ordered[1:]:
        name, start, end = directive
        current = (start, end)
        if directive_pair_is_sequenced(text, previous, current):
            phases.append([directive])
        else:
            phases[-1].append(directive)
        previous = current
    return phases


def directive_phase_families(
    text: str,
    directives: list[tuple[str, int, int]],
) -> list[set[str]]:
    """Partition directive family names by explicit pair-local boundaries."""
    return [
        {name for name, _, _ in phase}
        for phase in directive_phase_groups(text, directives)
    ]


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
    light_groups = directive_phase_groups(text, light_directives)
    light_phases = [
        {name for name, _, _ in group}
        for group in light_groups
    ]
    exclusive_lights = [
        match
        for match in re.finditer(
            r"\b(single|sole|only)\b[^.;]{0,80}\b(light|lit|sources?)\b",
            text,
            re.I,
        )
        if not match_is_negated(text, match.start())
        and not position_is_quoted(text, match.start())
        and not _position_is_displayed_text(text, match.start())
    ]
    exclusive_phases: set[int] = set()
    phase_labels = tuple(EXPLICIT_PHASE_LABEL.finditer(text))
    phase_starts = tuple(label.start() for label in phase_labels)

    def explicit_phase_owner(position: int) -> int:
        return bisect_right(phase_starts, position) - 1

    for match in exclusive_lights:
        def distance_to_group(group: list[tuple[str, int, int]]) -> int:
            group_start = min(start for _, start, _ in group)
            group_end = max(end for _, _, end in group)
            if match.end() < group_start:
                return group_start - match.end()
            if match.start() > group_end:
                return match.start() - group_end
            return 0

        if light_groups and phase_labels:
            owner = explicit_phase_owner(match.start())
            clause_start = max(
                text.rfind(boundary, 0, match.start())
                for boundary in ".;!?\n"
            ) + 1
            clause_end_match = re.search(r"[.;!?\n]", text[match.end():])
            clause_end = (
                match.end() + clause_end_match.start()
                if clause_end_match is not None
                else len(text)
            )
            labels_in_claim = [
                label
                for label in phase_labels
                if clause_start <= label.start() < clause_end
            ]
            if labels_in_claim:
                owner = explicit_phase_owner(
                    min(
                        labels_in_claim,
                        key=lambda label: abs(label.start() - match.start()),
                    ).start()
                )
            for group_index, group in enumerate(light_groups):
                if any(
                    explicit_phase_owner(start) == owner
                    for _, start, _ in group
                ):
                    exclusive_phases.add(group_index)
        elif light_groups:
            exclusive_phases.add(
                min(
                    range(len(light_groups)),
                    key=lambda index: distance_to_group(light_groups[index]),
                )
            )
    for phase_index, phase in enumerate(light_phases):
        if len(phase) >= 2 and phase_index in exclusive_phases:
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
        and not _position_is_displayed_text(text, match.start())
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
        for part in re.split(r"(?<=[.!?;\u2026\u061f])\s+", prompt)
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
        and not _position_is_displayed_text(prompt, match.start())
        for match in ADDED_AUDIO.finditer(prompt)
    )
    unchanged_audio = any(
        not position_is_quoted(prompt, match.start())
        and not _position_is_displayed_text(prompt, match.start())
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


def _strip_structural_phase_labels(text: str) -> str:
    """Remove heading-like numbered labels, never prose such as take five."""
    spans: list[tuple[int, int]] = []
    for match in NUMBERED_PHASE_LABEL.finditer(text):
        surface = lexical_tokens(match.group(0))
        if surface[:2] == ["take", "five"]:
            # The idiom remains prose even when an author follows it with a
            # colon or dash: ``Take five: the crew rests``.
            continue
        before = text[:match.start()]
        boundary = max(before.rfind(mark) for mark in ".!?;\n")
        lead = before[boundary + 1:]
        boundary_led = re.fullmatch(
            r"\s*(?:(?:>|[-+*]|#{1,6})\s+|(?:\*\*|__)\s*)?",
            lead,
        ) is not None
        after = text[match.end():]
        heading_punctuation = re.match(
            r"\s*(?:(?:\*\*|__)\s*)?(?::|\uFF1A|[-\u2013\u2014])",
            after,
        ) is not None
        if boundary_led and heading_punctuation:
            spans.append((match.start(), match.end()))
    if not spans:
        return text
    pieces: list[str] = []
    cursor = 0
    for start, end in spans:
        pieces.extend((text[cursor:start], " "))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def repetition_findings(prompt: str) -> list[str]:
    # Repeated structural labels are not padding: ``Shot 1`` through ``Shot
    # 6`` must repeat the phase noun to remain readable.  Remove only the
    # complete numbered label; repeated prose inside those phases still counts.
    repetition_text = _strip_structural_phase_labels(prompt)
    all_tokens = lexical_tokens(repetition_text)
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
        for sentence in re.split(r"[.!?]+", repetition_text)
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

    try:
        root = Path.cwd().resolve(strict=True)
        corpus_path = Path(args.corpus)
        if not corpus_path.is_absolute():
            corpus_path = root / corpus_path
        corpus_path = validate_repo_input_path(root, corpus_path)
        corpus = load_json(corpus_path, expected_type=list, root=root)
    except (OSError, ValueError, TypeError) as exc:
        print(f"Prompt architecture corpus error: {diagnostic_text(exc)}")
        return 1
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
        print(diagnostic_text(row))

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
        print(diagnostic_text(f"  {arm:<22} avg={avg:.2f}  {verdict}{suffix}"))

    print("\nPer-mode overall (skill_formula arm)")
    modes: dict[str, list[float]] = {}
    for r in results:
        if r["arm"] == "skill_formula":
            modes.setdefault(r["mode"], []).append(r["overall"])
    for m in sorted(modes, key=lambda m: statistics.mean(modes[m])):
        print(
            diagnostic_text(
                f"  {m:<8} n={len(modes[m]):<3} "
                f"{statistics.mean(modes[m]):.2f}"
            )
        )

    worst = sorted((r for r in results if r["arm"] == "skill_formula"), key=lambda r: r["overall"])[:8]
    print("\nWeakest skill-formula prompts")
    for r in worst:
        bad = [f"{k}={v['score']} ({v['note']})" for k, v in r["dims"].items() if v["score"] < 3]
        print(
            diagnostic_text(
                f"  {r['id']:<8} {r['overall']:.2f}  "
                f"{r['brief'][:44]:<44} {'; '.join(bad)[:90]}"
            )
        )

    if args.strict:
        strict_findings = gate_findings.get(
            "skill_formula",
            ["no skill_formula arm in this corpus"],
        )
        if strict_findings:
            print("\nskill_formula strict gate failed:")
            for finding in strict_findings:
                print(diagnostic_text(f"- {finding}"))
            print(f"\n{BOUNDARY}")
            return 1
        doctrine = [r for r in results if r["arm"] == "skill_formula"]
        avg = statistics.mean(r["overall"] for r in doctrine)
        print(f"\nskill_formula holds the release bar (avg={avg:.2f}, no dimension below 3).")
    print(f"\n{BOUNDARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

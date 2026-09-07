"""Build a bounded, offline Seedance comparison schedule. No provider calls."""
from __future__ import annotations

import json
from decimal import Decimal, localcontext

BRIEFS = (
    ("fan", "Fold the final paper pleat, release the fan; static shot, paper sound only."),
    ("joy", "An adult hops across one chalk line, lands, laughs once; hold the landing."),
    ("gag", "A feather lands on an adult's nose; they look down at it, then hold still."),
    ("dialogue", 'A repairer says exactly "It still ticks." once; clock ticks, no music.'),
    ("quiet", "Fold one cloth square on a table; locked frame, fabric sound only."),
    ("product", "Turn the supplied unbranded tin a quarter turn; preserve its visible form."),
    ("process", "Trim one ribbon from a clay bowl rim; end when the tool lifts away."),
    ("material", "One water droplet spreads on supplied paper; illustrative material study, no performance claim."),
    ("motion", "Use the supplied video for camera rhythm only; orbit the supplied object a quarter turn."),
    ("pour", "Pour water into one glass, stop, then cut once to the settled surface."),
    ("continuation", "From the supplied accepted frame with door open and hand off latch, lower the hand; hold doorway."),
    ("observation", "Watch sunlight move across a still cup; fixed camera, room tone, no invented conflict."),
)
CANARY = ("fan", "dialogue", "product", "continuation")
ARMS = ("current", "proposed")
TAKES = 2
MAX_ATTEMPTS = 48


def schedule() -> list[dict]:
    """Canary occupies 16 of the 48 slots, never 16 additional slots."""
    ordered = [b for b in BRIEFS if b[0] in CANARY] + [b for b in BRIEFS if b[0] not in CANARY]
    rows = []
    for index, (brief, prompt) in enumerate(ordered):
        for take in range(1, TAKES + 1):
            # Both take strata and each phase balance which arm leads; each
            # brief also reverses its leader for the second take.
            arms = ARMS if (index + take) % 2 else ARMS[::-1]
            for arm in arms:
                rows.append({"slot": f"{brief}-{arm}-{take}", "brief_id": brief, "brief": prompt,
                             "arm": arm, "take": take, "phase": "canary" if brief in CANARY else "remainder",
                             "status": "planned"})
    return rows


def cost_ceiling(per_attempt: Decimal, budget: Decimal) -> dict:
    """Conservative full-run reservation in one user-selected currency/unit.

    The operator must supply a verified all-in upper bound, not an average price.
    This arithmetic neither reserves funds nor authorizes execution.
    """
    for amount in (per_attempt, budget):
        if not isinstance(amount, Decimal) or not amount.is_finite() or amount <= 0:
            raise ValueError("cost bounds must be finite positive Decimal values")
    with localcontext() as context:
        context.prec = max(28, len(per_attempt.as_tuple().digits) + 2)
        required = per_attempt * MAX_ATTEMPTS
    return {"required": required, "within_budget": required <= budget}


if __name__ == "__main__":
    print(json.dumps({"status": "pending", "authorized": False, "max_attempts": MAX_ATTEMPTS,
                      "canary_attempts": len(CANARY) * len(ARMS) * TAKES,
                      "actual_cost": None, "slots": schedule()}, indent=2))

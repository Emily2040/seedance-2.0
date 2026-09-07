"""Offline reduction of human outcome judgments; never calls a model.

This is advisory comparison support, not a replacement for eval_run.py or a
semantic judge. Callers retain the frozen inputs and quoted human judgments.
"""
from __future__ import annotations

ARMS = ("current", "proposed", "plain")
DIMENSIONS = ("brief_fidelity", "directability", "specificity", "user_control")
GATES = ("safety", "state", "reference_fidelity")


def assess(record: dict) -> dict:
    """Reject malformed evidence; keep transport errors separate from quality."""
    if not isinstance(record, dict) or set(record) != {
        "status", "gates", "dimensions", "route_matches", "error"
    }:
        raise ValueError("outcome record fields differ from the contract")
    if record["status"] == "harness_error":
        if (record["gates"] is not None or record["dimensions"] is not None
                or record["route_matches"] is not None
                or not isinstance(record["error"], str) or not record["error"].strip()):
            raise ValueError("harness errors require an error and no judgments")
        return {"status": "harness_error", "score": None, "passed": None, "route_matches": None}
    if record["status"] != "scored" or record["error"] is not None:
        raise ValueError("unknown outcome status or contradictory error")
    if type(record["route_matches"]) is not bool:
        raise ValueError("route diagnostic must be boolean")
    gates, dimensions = record["gates"], record["dimensions"]
    if not isinstance(gates, dict) or set(gates) != set(GATES):
        raise ValueError("all hard gates are required")
    if any(type(v) is not bool for v in gates.values()):
        raise ValueError("hard gates require boolean judgments")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        raise ValueError("all outcome dimensions are required")
    if any(type(v) is not int or not 0 <= v <= 3 for v in dimensions.values()):
        raise ValueError("outcome dimensions require integers from 0 through 3")
    score = sum(dimensions.values()) / len(DIMENSIONS)
    return {"status": "scored", "score": score, "route_matches": record["route_matches"],
            "passed": all(gates.values()) and min(dimensions.values()) >= 2}


def compare(case_ids: list[str], records: list[dict]) -> dict:
    """Require every case in every arm; no quality averages for partial runs.

    Missing rows and explicit harness errors make the comparison incomplete.
    Duplicate, unexpected or malformed rows invalidate the supplied records.
    """
    if (not isinstance(case_ids, list) or not case_ids
            or any(not isinstance(c, str) or not c.strip() for c in case_ids)
            or len(set(case_ids)) != len(case_ids)):
        raise ValueError("case IDs must be a nonempty unique list")
    if not isinstance(records, list):
        raise ValueError("records must be a list")
    expected = {(c, a) for c in case_ids for a in ARMS}
    results = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != {"case_id", "arm", "judgment"}:
            raise ValueError("comparison row fields differ from the contract")
        if not isinstance(row["case_id"], str) or not isinstance(row["arm"], str):
            raise ValueError("case and arm must be strings")
        key = (row["case_id"], row["arm"])
        if key not in expected or key in results:
            raise ValueError("unexpected or duplicate case/arm")
        results[key] = assess(row["judgment"])
    complete = set(results) == expected and all(
        r["status"] == "scored" for r in results.values())
    arms = {}
    for arm in ARMS:
        rows = [r for (_, a), r in results.items() if a == arm]
        scored = [r for r in rows if r["status"] == "scored"]
        arms[arm] = {
            "scored": len(scored),
            "harness_errors": sum(r["status"] == "harness_error" for r in rows),
            "missing": len(case_ids) - len(rows),
            "route_matches": sum(r["route_matches"] for r in scored),
            "route_mismatches": sum(not r["route_matches"] for r in scored),
            "mean_score": sum(r["score"] for r in scored) / len(scored) if complete else None,
            "passed": sum(r["passed"] for r in scored) if complete else None,
        }
    return {"complete": complete, "release_eligible": False, "arms": arms}

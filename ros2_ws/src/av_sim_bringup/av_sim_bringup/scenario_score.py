"""Read the Unity scenario result file and report scores."""

from collections import Counter
import json
from pathlib import Path
import time

# Unity EventKind enum order; JsonUtility writes enums as integers.
EVENT_KINDS = ["LateCrosser", "CrosswalkWaiter", "Jaywalker", "UnsignalizedCrossing",
               "OccludedChild", "LeadVehicle", "StoppedObstacle", "SchoolZone"]


def load_result(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def kind_name(kind):
    return EVENT_KINDS[kind] if isinstance(kind, int) and 0 <= kind < len(EVENT_KINDS) else str(kind)


def summarize(result):
    return dict(
        seed=result["seed"], completed=result["completed"], disqualified=result["disqualified"],
        reason=result.get("reason", ""), score=result["score"], elapsed=result.get("elapsed", 0.0),
        min_pedestrian_distance=result.get("minPedestrianDistance", -1.0),
        violations_by_kind=dict(Counter(v["kind"] for v in result.get("violations", []))),
        events=[kind_name(e["kind"]) for e in result.get("plan", {}).get("events", [])],
    )


def average(results):
    scores = [r["score"] for r in results]
    return dict(seeds=[r["seed"] for r in results], scores=scores,
                mean=round(sum(scores) / len(scores), 2) if scores else 0.0)


# A reset mid-run is not a graded outcome; the next run overwrites the file.
FINAL_REASONS = ("completed", "timeout", "quit")


def is_final(result):
    return result.get("reason") in FINAL_REASONS


def wait_for_result(path, newer_than, timeout):
    """Unity writes the file only when a run ends; ignore earlier runs and resets."""
    path = Path(path)
    deadline = time.monotonic() + timeout
    while True:
        if path.exists() and path.stat().st_mtime >= newer_than:
            try:
                result = load_result(path)
                if is_final(result):
                    return result
            except json.JSONDecodeError:
                pass
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.1)


def format_table(summary):
    status = "실격" if summary["disqualified"] else ("완주" if summary["completed"] else f"미완주({summary['reason']})")
    lines = [f"seed {summary['seed']}: {summary['score']}점 [{status}]",
             f"  이벤트: {', '.join(summary['events'])}"]
    if summary["violations_by_kind"]:
        lines.append("  위반: " + ", ".join(f"{k} x{n}" for k, n in sorted(summary["violations_by_kind"].items())))
    else:
        lines.append("  위반: 없음")
    if summary["min_pedestrian_distance"] >= 0:
        lines.append(f"  보행자 최소 거리: {summary['min_pedestrian_distance']:.2f} m")
    return "\n".join(lines)

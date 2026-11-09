import json
import os
import time

import pytest

from av_sim_bringup.scenario_score import EVENT_KINDS, average, format_table, summarize, wait_for_result


def result(score=80, kinds=("yield", "yield", "speeding"), events=(2, 7)):
    return {
        "seed": 7, "fixedSeed": True, "completed": True, "disqualified": False, "reason": "completed",
        "elapsed": 640.5, "minPedestrianDistance": 2.4, "score": score,
        "plan": {"seed": 7, "events": [{"kind": k, "s": 100.0 * (i + 1)} for i, k in enumerate(events)]},
        "violations": [{"kind": k, "eventIndex": 0, "time": 10.0, "s": 100.0} for k in kinds],
    }


def test_summarize_counts_violations():
    summary = summarize(result())
    assert summary["violations_by_kind"] == {"yield": 2, "speeding": 1}
    assert summary["events"] == ["Jaywalker", "SchoolZone"]
    assert summary["score"] == 80 and summary["seed"] == 7 and summary["completed"]


def test_event_kinds_match_unity_enum_order():
    assert EVENT_KINDS == ["LateCrosser", "CrosswalkWaiter", "Jaywalker", "UnsignalizedCrossing",
                           "OccludedChild", "LeadVehicle", "StoppedObstacle", "SchoolZone"]


def test_average_scores():
    summary = average([result(100), result(60), result(0)])
    assert summary["scores"] == [100, 60, 0]
    assert summary["mean"] == pytest.approx(53.33)


def test_wait_for_result_ignores_old_file(tmp_path):
    path = tmp_path / "r.json"
    path.write_text(json.dumps(result()))
    os.utime(path, (100, 100))
    assert wait_for_result(path, newer_than=time.time() - 1, timeout=0.2) is None


def test_wait_for_result_reads_new_file(tmp_path):
    path = tmp_path / "r.json"
    started = time.time() - 1
    path.write_text(json.dumps(result()))
    assert wait_for_result(path, newer_than=started, timeout=1)["seed"] == 7


def test_format_table_lists_score_and_violations():
    text = format_table(summarize(result()))
    assert "80" in text and "yield" in text and "Jaywalker" in text


def test_wait_for_result_ignores_reset_results(tmp_path):
    path = tmp_path / "r.json"
    started = time.time() - 1
    reset = result()
    reset["reason"] = "reset"
    path.write_text(json.dumps(reset))
    assert wait_for_result(path, newer_than=started, timeout=0.3) is None

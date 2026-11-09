from pathlib import Path

import pytest

from av_sim_bringup.campus_route import campus_lap, load_map
from av_sim_bringup.scenario_route import export_route

MAP = Path(__file__).parents[1] / "config/campus_map.json"


def test_route_matches_lap_and_signals():
    out = export_route(load_map(MAP))
    assert 1900 < out["length"] < 2050
    assert len(out["points"]) == len(out["roadCenters"]) == len(out["roadHalfWidths"])
    assert [s["id"] for s in out["signals"]] == [4, 7, 11, 18, 13, 22, 21, 28, 27, 34, 39, 2, 5]
    assert all(0 < s["crossS"] - s["stopS"] < 6 for s in out["signals"])


def test_straights_are_long_and_ordered():
    spans = export_route(load_map(MAP))["straights"]
    assert len(spans) >= 4 and all(b["end"] - b["start"] > 60 for b in spans)
    assert all(a["end"] <= b["start"] for a, b in zip(spans, spans[1:]))


def test_coordinates_are_unity_xz():
    data = load_map(MAP)
    out = export_route(data)
    first = campus_lap(data)[0]
    assert out["points"][0] == pytest.approx({"x": -first[1], "y": first[0]}, abs=0.01)


def test_half_widths_are_plausible():
    assert all(1.5 < w < 8.0 for w in export_route(load_map(MAP))["roadHalfWidths"])

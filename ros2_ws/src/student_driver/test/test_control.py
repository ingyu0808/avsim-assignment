import math

from student_driver.control import LATCHED, fault, ramp, target_speed


def test_straight_road_runs_at_cruise():
    assert target_speed(5.0, 0.0, 500.0) == 5.0


def test_curve_slows_down():
    assert math.isclose(target_speed(5.0, 0.2, 500.0), 2.0)


def test_slows_and_stops_at_finish():
    assert target_speed(5.0, 0.0, 5.0) < 2.5
    assert target_speed(5.0, 0.0, 0.5) == 0.0


def test_ramp_limits_acceleration_but_not_braking():
    assert math.isclose(ramp(1.0, 5.0), 1.06)
    assert ramp(4.0, 0.0) == 0.0


def test_stale_odom_pauses_but_only_leaving_the_route_latches():
    assert fault(0.2, 0.1) == ""
    assert fault(0.2, 0.6) == "STALE_ODOM"
    assert fault(2.5, 0.1) == "OFF_ROUTE"
    assert fault(2.5, 0.6) == "OFF_ROUTE"
    assert "STALE_ODOM" not in LATCHED and "OFF_ROUTE" in LATCHED

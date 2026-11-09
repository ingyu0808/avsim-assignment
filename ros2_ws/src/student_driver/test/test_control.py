import math

from student_driver.control import (LATCHED, NO_LIMIT, LimitWatch, fault, next_signal, ramp, target_speed)


def test_straight_road_runs_at_cruise():
    assert target_speed(5.0, 0.0, NO_LIMIT, 500.0) == 5.0


def test_curve_slows_down():
    assert math.isclose(target_speed(5.0, 0.2, NO_LIMIT, 500.0), 2.0)


def test_speed_limit_caps_speed():
    assert target_speed(5.0, 0.0, 2.5, 500.0) == 2.5
    assert target_speed(5.0, 0.0, 0.0, 500.0) == 0.0


def test_negative_limit_means_stop():
    assert target_speed(5.0, 0.0, -1.0, 500.0) == 0.0


def test_missing_limit_stops_the_car():
    assert target_speed(5.0, 0.0, None, 500.0) == 0.0


def test_slows_and_stops_at_finish():
    assert target_speed(5.0, 0.0, NO_LIMIT, 5.0) < 2.5
    assert target_speed(5.0, 0.0, NO_LIMIT, 0.5) == 0.0


def test_ramp_limits_acceleration_but_not_braking():
    assert math.isclose(ramp(1.0, 5.0), 1.06)
    assert ramp(4.0, 0.0) == 0.0


def test_limit_goes_stale():
    watch = LimitWatch(timeout=1.0)
    assert watch.value(0.0) is None
    watch.update(3.0, 10.0)
    assert watch.value(10.5) == 3.0
    assert watch.value(11.5) is None


def test_next_signal_is_the_first_stop_line_not_yet_passed():
    stops = [dict(id=4, route_s=100.0), dict(id=7, route_s=300.0)]
    assert next_signal(stops, 50.0) == (4, 50.0)
    assert next_signal(stops, 101.0) == (4, -1.0)
    assert next_signal(stops, 103.0) == (7, 197.0)
    assert next_signal(stops, 400.0) == (-1, -1.0)


def test_stale_odom_pauses_but_only_leaving_the_route_latches():
    assert fault(0.2, 0.1) == ""
    assert fault(0.2, 0.6) == "STALE_ODOM"
    assert fault(2.5, 0.1) == "OFF_ROUTE"
    assert fault(2.5, 0.6) == "OFF_ROUTE"
    assert "STALE_ODOM" not in LATCHED and "OFF_ROUTE" in LATCHED

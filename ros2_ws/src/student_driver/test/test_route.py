import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from student_driver.route import CampusRoute

MAP = Path(__file__).resolve().parents[2] / "av_sim_bringup/config/campus_map.json"


class FakeClient:
    def __init__(self):
        self.calls = 0

    def service_is_ready(self):
        return True

    def call_async(self, request):
        self.calls += 1
        return SimpleNamespace(done=lambda: True)


class FakeNode:
    def __init__(self):
        self.client = FakeClient()

    def create_client(self, kind, name):
        assert name == "/reset_simulation"
        return self.client

    def get_logger(self):
        return SimpleNamespace(info=print, warn=print, error=print)


def odom(x, y, yaw, speed=0.0):
    return SimpleNamespace(
        pose=SimpleNamespace(pose=SimpleNamespace(
            position=SimpleNamespace(x=x, y=y, z=0.0),
            orientation=SimpleNamespace(x=0.0, y=0.0, z=math.sin(yaw / 2), w=math.cos(yaw / 2)))),
        twist=SimpleNamespace(twist=SimpleNamespace(linear=SimpleNamespace(x=speed))))


def on_path(route, s):
    """Position and heading of the lap at s metres."""
    points, along = route.tracker.points, route.tracker.s
    i = int(np.searchsorted(along, s))
    heading = math.atan2(*(points[i + 1] - points[i])[::-1])
    return points[i][0], points[i][1], heading


def drive_to(route, s, now=4.0, speed=5.0):
    """Feed /odom along the lap in 5 m steps (the tracker only searches ~30 m ahead)."""
    for step in np.arange(route.progress_m, s, 5.0):
        route.on_odom(odom(*on_path(route, step), speed=speed), now=now)
        route.update(now)
    route.on_odom(odom(*on_path(route, s), speed=speed), now=now)
    return route.update(now)


def driving(route):
    node = route.node
    route.on_odom(odom(*on_path(route, 0.0)), now=0.0)
    route.update(0.0)
    route.on_odom(odom(*on_path(route, 0.0)), now=3.0)
    assert route.update(3.0) == "DRIVING" and node.client.calls == 1


def test_start_resets_once_then_drives_after_settling():
    node = FakeNode()
    route = CampusRoute(node, MAP)
    assert route.update(0.0) == "WAIT_ODOM"
    route.on_odom(odom(*on_path(route, 0.0)), now=0.0)
    assert route.update(0.1) == "SETTLING"
    route.on_odom(odom(*on_path(route, 0.0)), now=1.0)
    assert route.update(1.0) == "SETTLING"
    route.on_odom(odom(*on_path(route, 0.0)), now=2.2)
    assert route.update(2.2) == "DRIVING"
    assert node.client.calls == 1


def test_steering_is_straight_on_a_straight_and_cruise_speed_is_kept():
    route = CampusRoute(FakeNode(), MAP)
    driving(route)
    for s in (100.0, 200.0, 300.0):
        assert drive_to(route, s) == "DRIVING"
        assert abs(route.steering()) < 0.05
        assert route.limit_speed(5.0) == 5.0
    assert 290 < route.progress_m < 310


def test_steers_back_toward_the_path_when_offset_to_the_right():
    route = CampusRoute(FakeNode(), MAP)
    driving(route)
    drive_to(route, 200.0)
    x, y, heading = on_path(route, 200.0)
    right = np.array([math.sin(heading), -math.cos(heading)])
    route.on_odom(odom(x + right[0], y + right[1], heading, speed=5.0), now=4.0)
    route.update(4.0)
    assert route.steering() > 0.05  # positive = left


def test_leaving_the_route_stops_for_good():
    route = CampusRoute(FakeNode(), MAP)
    driving(route)
    drive_to(route, 200.0)
    x, y, heading = on_path(route, 200.0)
    route.on_odom(odom(x + 3 * math.sin(heading), y - 3 * math.cos(heading), heading), now=4.1)
    assert route.update(4.1) == "OFF_ROUTE"
    route.on_odom(odom(x, y, heading), now=4.2)
    assert route.update(4.2) == "OFF_ROUTE"


def test_status_has_progress_but_no_signal_information():
    route = CampusRoute(FakeNode(), MAP)
    status = route.status()
    assert {"state", "progress_m", "total_m", "lateral_error_m"} <= set(status)
    assert not any("signal" in key for key in status)

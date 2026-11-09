"""Speed rules of the route follower, kept free of ROS so they can be tested."""

import math

# /team/speed_limit value that means "no limit from perception".
NO_LIMIT = 100.0
LATERAL_ACCELERATION = 0.8
FINISH_SLOWDOWN = 8.0
FINISH_STOP = 1.0


def target_speed(cruise, curvature, limit, remaining):
    """Cruise, slowed for curves, capped by perception, stopping at the finish.

    limit is the latest /team/speed_limit value, or None when it is missing or stale.
    """
    if limit is None:
        return 0.0
    speed = min(cruise, math.sqrt(LATERAL_ACCELERATION / max(abs(curvature), 0.01)), max(0.0, limit))
    if remaining < FINISH_SLOWDOWN:
        speed = min(speed, math.sqrt(max(0.0, 1.2 * (remaining - 0.8))))
    if remaining < FINISH_STOP:
        speed = 0.0
    return speed


def ramp(previous, target, step=0.06):
    """Limit acceleration per tick; braking is never slew-limited."""
    return min(target, previous + step)


class LimitWatch:
    """Latest speed limit, forgotten after timeout seconds without a message."""

    def __init__(self, timeout=1.0):
        self.timeout = timeout
        self.limit = None
        self.stamp = -math.inf

    def update(self, limit, now):
        self.limit, self.stamp = limit, now

    def value(self, now):
        return self.limit if now - self.stamp <= self.timeout else None


def next_signal(stops, s, passed=2.0):
    """(id, distance m) of the first signal stop line ahead; it stays current until passed m behind."""
    for stop in stops:
        distance = stop["route_s"] - s
        if distance > -passed:
            return stop["id"], round(distance, 2)
    return -1, -1.0


OFF_ROUTE = 2.0
STALE_ODOM = 0.4
# Faults that stop the car for good; the rest only pause it while they last.
LATCHED = ("OFF_ROUTE",)


def fault(lateral_error, odom_age):
    if lateral_error > OFF_ROUTE:
        return "OFF_ROUTE"
    if odom_age > STALE_ODOM:
        return "STALE_ODOM"
    return ""

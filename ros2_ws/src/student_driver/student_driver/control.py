"""경로 추종 도우미의 속도 규칙과 고장 판정. ROS 없이 테스트할 수 있게 따로 둔다."""

import math

LATERAL_ACCELERATION = 0.8
FINISH_SLOWDOWN = 8.0
FINISH_STOP = 1.0


def target_speed(cruise, curvature, remaining):
    """순항 속도에서 곡선 감속과 도착 정지를 반영한 속도 (m/s)."""
    speed = min(cruise, math.sqrt(LATERAL_ACCELERATION / max(abs(curvature), 0.01)))
    if remaining < FINISH_SLOWDOWN:
        speed = min(speed, math.sqrt(max(0.0, 1.2 * (remaining - 0.8))))
    if remaining < FINISH_STOP:
        speed = 0.0
    return speed


def ramp(previous, target, step=0.06):
    """주기마다 가속을 제한한다. 감속은 제한하지 않는다."""
    return min(target, previous + step)


OFF_ROUTE = 2.0
STALE_ODOM = 0.4
# 차를 영구히 세우는 고장. 나머지는 그동안만 멈춘다.
LATCHED = ("OFF_ROUTE",)


def fault(lateral_error, odom_age):
    if lateral_error > OFF_ROUTE:
        return "OFF_ROUTE"
    if odom_age > STALE_ODOM:
        return "STALE_ODOM"
    return ""

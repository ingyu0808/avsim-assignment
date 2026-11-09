"""정문에서 출발해 정문으로 돌아오는 고정 경로(1962 m)를 /odom으로 따라가는 도우미입니다.

노드가 아니라 driver.py가 쓰는 클래스입니다. 고치거나 쓰지 않아도 됩니다.
  - update(): 출발 준비(정문으로 리셋 한 번), 경로 이탈·위치 끊김 판정, 완주 판정
  - steering(): 경로를 따라가는 조향각 (rad, 양수 = 왼쪽, Pure Pursuit)
  - limit_speed(): 곡선과 도착 지점에서 줄인 속도 (m/s)
신호, 사람, 장애물은 전혀 보지 않습니다. 그 판단은 여러분 몫입니다.
"""

import math
import time
from pathlib import Path

import numpy as np
from ament_index_python.packages import get_package_share_directory
from std_srvs.srv import Trigger

from av_sim_bringup.campus_route import RouteTracker, campus_lap, load_map

from .control import LATCHED, fault, target_speed

SETTLE = 2.0          # 리셋 뒤 차가 자리 잡을 때까지 기다리는 시간 (s)
START_TOLERANCE = 3.0  # 리셋 뒤 위치가 출발점에서 이보다 멀면 다른 프로그램이 /odom을 내는 것


class CampusRoute:
    def __init__(self, node, map_file=None):
        if map_file is None:
            map_file = Path(get_package_share_directory("av_sim_bringup")) / "config/campus_map.json"
        self.node = node
        self.tracker = RouteTracker(campus_lap(load_map(map_file)))
        self.reset = node.create_client(Trigger, "/reset_simulation")
        self.state = "WAIT_ODOM"
        self.position = None
        self.yaw = self.speed = 0.0
        self.odom_time = -math.inf
        self.reset_future = None
        self.reset_time = None
        self.start_time = None
        self.lateral_error = 0.0
        self.curvature = 0.0

    def on_odom(self, msg, now=None):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        if not all(math.isfinite(v) for v in (p.x, p.y, q.z, q.w, msg.twist.twist.linear.x)):
            return
        self.position = np.array([p.x, p.y])
        self.yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        self.speed = msg.twist.twist.linear.x
        self.odom_time = time.monotonic() if now is None else now

    def update(self, now=None):
        """상태를 갱신해 돌려준다: WAIT_ODOM, WAIT_RESET_SERVICE, RESETTING, SETTLING,
        RESET_POSE_MISMATCH, DRIVING, STALE_ODOM(잠시 멈춤), OFF_ROUTE(영구 정지), COMPLETE."""
        now = time.monotonic() if now is None else now
        if self.state in ("COMPLETE",) + LATCHED:
            return self.state
        if self.start_time is None:
            self.state = self._start(now)
            return self.state
        self.lateral_error = self.tracker.update(self.position)
        problem = fault(self.lateral_error, now - self.odom_time)
        if problem:
            if problem in LATCHED:
                self.node.get_logger().error(f"경로에서 {self.lateral_error:.1f} m 벗어나 영구 정지합니다.")
            self.state = problem
        elif self.remaining_m < 1.0 and abs(self.speed) < 0.15:
            self.state = "COMPLETE"
            self.node.get_logger().info(f"완주: {now - self.start_time:.0f} s")
        else:
            self.state = "DRIVING"
        return self.state

    def _start(self, now):
        """정문으로 한 번 리셋하고, 자리를 잡으면 출발한다."""
        if self.position is None or now - self.odom_time > 0.5:
            return "WAIT_ODOM"
        if self.reset_future is None:
            if not self.reset.service_is_ready():
                return "WAIT_RESET_SERVICE"
            self.reset_future = self.reset.call_async(Trigger.Request())
        if not self.reset_future.done():
            return "RESETTING"
        if self.reset_time is None:
            self.reset_time = now
        if now - self.reset_time < SETTLE:
            return "SETTLING"
        if np.linalg.norm(self.position - self.tracker.points[0]) > START_TOLERANCE:
            return "RESET_POSE_MISMATCH"
        self.start_time = now
        self.tracker.update(self.position)
        return "DRIVING"

    def steering(self):
        """경로를 따라가는 조향각 (rad, 양수 = 왼쪽)."""
        if self.position is None:
            return 0.0
        angle, _, self.curvature = self.tracker.pursuit(self.position, self.yaw, self.speed)
        return angle

    def limit_speed(self, cruise):
        """cruise에서 곡선 감속과 도착 정지를 반영한 속도 (m/s). steering()을 먼저 부르면 곡률이 갱신된다."""
        if self.position is not None:
            _, _, self.curvature = self.tracker.pursuit(self.position, self.yaw, self.speed)
        return target_speed(cruise, self.curvature, self.remaining_m)

    @property
    def progress_m(self):
        return float(self.tracker.s[self.tracker.index])

    @property
    def total_m(self):
        return float(self.tracker.s[-1])

    @property
    def remaining_m(self):
        return self.tracker.remaining

    def status(self):
        return dict(state=self.state, progress_m=round(self.progress_m, 1), total_m=round(self.total_m, 1),
                    lateral_error_m=round(self.lateral_error, 3), speed=round(self.speed, 2))

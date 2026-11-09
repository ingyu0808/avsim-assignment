"""Follows the gate-to-gate campus lap with /odom; perception only sets a speed cap.

This node is provided. It ignores signals, pedestrians and obstacles: it drives at
min(cruise, curve speed, /team/speed_limit). Publish /team/speed_limit from your own
perception node; without a fresh message (1 s) the car stops.

Subscribes: /odom, /team/speed_limit (std_msgs/Float32, m/s; 0 = stop)
Publishes:  /cmd_ackermann, /team/route_state (std_msgs/String, JSON)
"""

import json
import math
import time
from pathlib import Path

import numpy as np
import rclpy
from ackermann_msgs.msg import AckermannDrive
from ament_index_python.packages import get_package_share_directory
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from std_msgs.msg import Float32, String
from std_srvs.srv import Trigger

from av_sim_bringup.campus_route import RouteTracker, campus_lap, load_map

from .control import LATCHED, LimitWatch, fault, next_signal, ramp, target_speed

MAX_STEERING = 0.60


class RouteFollower(Node):
    def __init__(self):
        super().__init__("route_follower")
        default = str(Path(get_package_share_directory("av_sim_bringup")) / "config/campus_map.json")
        data = load_map(self.declare_parameter("map_file", default).value)
        self.cruise = float(self.declare_parameter("speed", 5.0).value)
        if not 0 < self.cruise <= 6:
            raise ValueError("speed must be between 0 and 6 m/s")
        self.route = RouteTracker(campus_lap(data))
        self.stops = self.route.signal_stops(data)
        self.limit = LimitWatch(timeout=1.0)
        self.position = None
        self.yaw = self.speed = 0.0
        self.odom_received = 0.0
        self.command_speed = 0.0
        self.state = "WAIT_ODOM"
        self.reset_future = None
        self.reset_time = None
        self.start_time = None
        self.last_log = 0.0
        self.command = self.create_publisher(AckermannDrive, "/cmd_ackermann", 1)
        self.status = self.create_publisher(String, "/team/route_state", 1)
        self.create_subscription(Odometry, "/odom", self.on_odom, qos_profile_sensor_data)
        self.create_subscription(Float32, "/team/speed_limit", self.on_limit, 1)
        self.reset = self.create_client(Trigger, "/reset_simulation")
        self.create_timer(0.05, self.tick)
        self.get_logger().info(f"Lap {self.route.s[-1]:.0f} m, {len(self.stops)} signal stop lines, cruise {self.cruise} m/s")

    def on_odom(self, msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        if not all(math.isfinite(v) for v in (p.x, p.y, q.z, q.w, msg.twist.twist.linear.x)):
            return
        self.position = np.array([p.x, p.y])
        self.yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        self.speed = msg.twist.twist.linear.x
        self.odom_received = time.monotonic()

    def on_limit(self, msg):
        if math.isfinite(msg.data):
            self.limit.update(float(msg.data), time.monotonic())

    def start(self, now):
        """Reset the car to the gate once, wait for it to settle, then drive."""
        if self.position is None or now - self.odom_received > 0.5:
            return "WAIT_ODOM"
        if self.reset_future is None:
            if not self.reset.service_is_ready():
                return "WAIT_RESET_SERVICE"
            self.reset_future = self.reset.call_async(Trigger.Request())
        if not self.reset_future.done():
            return "RESETTING"
        if self.reset_time is None:
            self.reset_time = now
        if now - self.reset_time < 2:
            return "SETTLING"
        if np.linalg.norm(self.position - self.route.points[0]) > 3:
            return "RESET_POSE_MISMATCH"
        self.start_time = now
        return "DRIVING"

    def tick(self):
        now = time.monotonic()
        steering, target, error = 0.0, 0.0, 0.0
        if self.state not in ("DRIVING", "COMPLETE") + LATCHED:
            self.state = self.start(now)
        if self.state == "DRIVING":
            error = self.route.update(self.position)
            steering, _, curvature = self.route.pursuit(self.position, self.yaw, self.speed)
            limit = self.limit.value(now)
            target = target_speed(self.cruise, curvature, limit, self.route.remaining)
            if limit is None and now - self.last_log > 2:
                self.get_logger().warn("No fresh /team/speed_limit: stopped")
                self.last_log = now
            problem = fault(error, now - self.odom_received)
            if problem:
                target = 0.0
                if problem in LATCHED:
                    self.state = problem
                    self.get_logger().error(f"Stopped for good: {problem} (lateral error {error:.2f} m)")
            elif self.route.remaining < 1.0 and abs(self.speed) < 0.15:
                self.state = "COMPLETE"
                self.get_logger().info(f"Lap complete in {now - self.start_time:.0f} s")
        self.command_speed = ramp(self.command_speed, target)
        self.command.publish(AckermannDrive(speed=float(self.command_speed),
                                            steering_angle=float(np.clip(steering, -MAX_STEERING, MAX_STEERING))))
        s = float(self.route.s[self.route.index])
        signal_id, signal_distance = next_signal(self.stops, s)
        self.status.publish(String(data=json.dumps(dict(
            state=self.state, progress_m=round(s, 1), total_m=round(float(self.route.s[-1]), 1),
            next_signal_id=signal_id, next_signal_distance_m=signal_distance,
            lateral_error_m=round(error, 3), speed=round(self.speed, 2),
            command_speed=round(self.command_speed, 2)))))


def main():
    rclpy.init()
    node = RouteFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            for _ in range(3):
                node.command.publish(AckermannDrive())
                time.sleep(0.05)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

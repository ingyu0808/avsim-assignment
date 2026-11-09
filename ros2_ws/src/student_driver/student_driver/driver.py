"""여러분이 채울 주행 노드입니다. 센서를 받아 판단하고, 차량 명령 /cmd_ackermann(속도, 조향각)을 직접 보냅니다.

받는 토픽
  /camera/image_raw       sensor_msgs/Image (rgb8, 640x480, 20 Hz)
  /camera/camera_info     sensor_msgs/CameraInfo (fx=fy=320, 수평 화각 90°)
  /odom                   nav_msgs/Odometry (시뮬레이터 정답 위치, x=북, y=서)
  /ultrasonic/front       sensor_msgs/Range (최대 4 m. rear, left, right도 있음)

보내는 토픽
  /cmd_ackermann          ackermann_msgs/AckermannDrive
                          speed(m/s), steering_angle(rad, 양수 = 왼쪽, 최대 ±0.6)
                          0.5 s 넘게 새 명령이 없으면 차가 멈춥니다.
  /team/route_state       std_msgs/String (JSON, 디버깅용: 상태, 진행 거리, 경로 이탈 거리, 속도)

신호등의 위치와 색은 토픽으로 주지 않습니다. 카메라로 찾아야 합니다.
경로 추종은 route.py의 CampusRoute가 도와줍니다. 쓰지 않고 직접 조향해도 됩니다.
"""

import json
import math

import cv2
import numpy as np
import rclpy
from ackermann_msgs.msg import AckermannDrive
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, Range
from std_msgs.msg import String

from .control import ramp
from .route import CampusRoute

MAX_STEERING = 0.60


def to_bgr(msg):
    """sensor_msgs/Image(rgb8) → OpenCV BGR 배열 (cv_bridge 없이)."""
    rows = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)
    rgb = rows[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


class Driver(Node):
    def __init__(self):
        super().__init__("driver")
        self.cruise = float(self.declare_parameter("speed", 5.0).value)
        if not 0 < self.cruise <= 6:
            raise ValueError("speed must be between 0 and 6 m/s")
        self.route = CampusRoute(self)
        self.image = None
        self.camera_k = None
        self.front_range = math.inf
        self.command_speed = 0.0
        self.command = self.create_publisher(AckermannDrive, "/cmd_ackermann", 1)
        self.state_output = self.create_publisher(String, "/team/route_state", 1)
        self.create_subscription(Image, "/camera/image_raw", self.on_image, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, "/camera/camera_info", self.on_info, qos_profile_sensor_data)
        self.create_subscription(Odometry, "/odom", self.route.on_odom, qos_profile_sensor_data)
        self.create_subscription(Range, "/ultrasonic/front", self.on_range, qos_profile_sensor_data)
        self.create_timer(0.05, self.tick)
        self.get_logger().info(f"경로 {self.route.total_m:.0f} m, 순항 {self.cruise} m/s")

    def on_image(self, msg):
        self.image = to_bgr(msg)

    def on_info(self, msg):
        self.camera_k = np.array(msg.k).reshape(3, 3)

    def on_range(self, msg):
        self.front_range = msg.range if math.isfinite(msg.range) else math.inf

    def decide(self):
        """이번 주기에 보낼 (속도 m/s, 조향각 rad)을 돌려줍니다. 20 Hz로 불립니다.

        지금은 경로를 따라 곡선에서만 감속하며 달립니다. 신호, 사람, 장애물은 무시합니다.

        TODO 예시
          - 신호: 카메라로 신호등을 찾고 색을 읽어, 빨강·노랑이면 정지선 앞에서 speed = 0.
          - 보행자: 차로 앞의 사람을 찾으면 멈춘다 (CNN 검출기 사용 가능).
          - 앞차·정차 차량·콘: 거리를 추정해 따라가거나 멈춘다 (self.front_range도 참고).
          - 어린이보호구역 표지판: 구간 안에서는 10 km/h(약 2.7 m/s) 이하.
          - 조향: self.route.steering() 대신 차선을 직접 보고 조향해도 됩니다.
        """
        steering = self.route.steering()
        speed = self.route.limit_speed(self.cruise)
        if self.image is None:
            return 0.0, steering
        return speed, steering

    def tick(self):
        state = self.route.update()
        speed, steering = self.decide() if state == "DRIVING" else (0.0, 0.0)
        # 가속은 부드럽게(최대 약 1.2 m/s²), 감속은 바로 반영한다.
        self.command_speed = ramp(self.command_speed, max(0.0, float(speed)))
        steering = float(np.clip(steering, -MAX_STEERING, MAX_STEERING))
        self.command.publish(AckermannDrive(speed=float(self.command_speed), steering_angle=steering))
        status = self.route.status()
        status.update(command_speed=round(self.command_speed, 2))
        self.state_output.publish(String(data=json.dumps(status)))


def main():
    rclpy.init()
    node = Driver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            for _ in range(3):
                node.command.publish(AckermannDrive())
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

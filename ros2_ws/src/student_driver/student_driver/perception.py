"""여러분이 채울 인식·판단 노드입니다.

센서를 받아 상황을 판단하고, 차가 넘지 말아야 할 속도(m/s)를 /team/speed_limit 으로 보냅니다.
route_follower 가 그 값 이하로 달리고, 0을 보내면 멈춥니다. 1초 넘게 아무것도 보내지 않으면
route_follower 는 안전을 위해 차를 세웁니다.

받는 토픽
  /camera/image_raw       sensor_msgs/Image (rgb8, 640x480, 20 Hz)
  /camera/camera_info     sensor_msgs/CameraInfo (fx=fy=320, 수평 화각 90°)
  /odom                   nav_msgs/Odometry (시뮬레이터 정답 위치, x=북, y=서)
  /ultrasonic/front       sensor_msgs/Range (최대 4 m)
  /team/route_state       std_msgs/String (JSON: progress_m, next_signal_id, next_signal_distance_m, ...)

보내는 토픽
  /team/speed_limit       std_msgs/Float32 (m/s, 0 = 정지, NO_LIMIT = 제한 없음)
"""

import json
import math

import cv2
import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, Range
from std_msgs.msg import Float32, String

from .control import NO_LIMIT


def to_bgr(msg):
    """sensor_msgs/Image(rgb8) → OpenCV BGR 배열 (cv_bridge 없이)."""
    rows = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)
    rgb = rows[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


class Perception(Node):
    def __init__(self):
        super().__init__("perception")
        self.image = None
        self.camera_k = None
        self.front_range = math.inf
        self.speed = 0.0
        self.route = {}
        self.limit = self.create_publisher(Float32, "/team/speed_limit", 1)
        self.create_subscription(Image, "/camera/image_raw", self.on_image, qos_profile_sensor_data)
        self.create_subscription(CameraInfo, "/camera/camera_info", self.on_info, qos_profile_sensor_data)
        self.create_subscription(Odometry, "/odom", self.on_odom, qos_profile_sensor_data)
        self.create_subscription(Range, "/ultrasonic/front", self.on_range, qos_profile_sensor_data)
        self.create_subscription(String, "/team/route_state", self.on_route, 1)
        self.create_timer(0.1, self.tick)

    def on_image(self, msg):
        self.image = to_bgr(msg)

    def on_info(self, msg):
        self.camera_k = np.array(msg.k).reshape(3, 3)

    def on_odom(self, msg):
        self.speed = msg.twist.twist.linear.x

    def on_range(self, msg):
        self.front_range = msg.range if math.isfinite(msg.range) else math.inf

    def on_route(self, msg):
        self.route = json.loads(msg.data)

    def decide(self):
        """지금 넘지 말아야 할 속도(m/s)를 돌려줍니다.

        TODO 예시
          - 신호: route["next_signal_distance_m"] 이 가까울 때 카메라로 신호 색을 읽고,
                  빨강·노랑이면 정지선 앞에서 멈추는 속도를 돌려준다.
          - 보행자: 차로 앞의 사람을 찾으면 멈춘다 (CNN 검출기 사용 가능).
          - 앞차·정차 차량·콘: 거리를 추정해 따라가거나 멈춘다.
          - 어린이보호구역 표지판: 구간 안에서는 10 km/h(약 2.7 m/s) 이하로 달린다.
        """
        if self.image is None:
            return NO_LIMIT
        return NO_LIMIT

    def tick(self):
        self.limit.publish(Float32(data=float(self.decide())))


def main():
    rclpy.init()
    node = Perception()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""카메라 영상을 일정 간격으로 JPEG로 저장한다 (학습 데이터 수집, 안내서 캡처용).

    /usr/bin/python3 scripts/record_frames.py OUT_DIR [--period 0.5]

파일 이름: <벽시계 시각>_s<경로 진행 m>.jpg. 진행 거리는 /team/route_state 가 있을 때만 붙는다.
"""

import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


class Recorder(Node):
    def __init__(self, out, period):
        super().__init__("frame_recorder")
        self.out, self.period = out, period
        self.progress = None
        self.last = 0.0
        self.count = 0
        self.create_subscription(Image, "/camera/image_raw", self.on_image, qos_profile_sensor_data)
        self.create_subscription(String, "/team/route_state", self.on_route, 1)

    def on_route(self, msg):
        self.progress = json.loads(msg.data).get("progress_m")

    def on_image(self, msg):
        now = time.time()
        if now - self.last < self.period:
            return
        self.last = now
        rows = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)
        rgb = rows[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
        suffix = f"_s{self.progress:07.1f}" if self.progress is not None else ""
        cv2.imwrite(str(self.out / f"{now:.2f}{suffix}.jpg"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 92])
        self.count += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("--period", type=float, default=0.5)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Recorder(args.out, args.period)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"{node.count} frames → {args.out}")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

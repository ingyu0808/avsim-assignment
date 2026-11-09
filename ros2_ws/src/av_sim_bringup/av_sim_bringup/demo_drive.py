#!/usr/bin/env python3
"""캠퍼스 도로를 잠깐 달려보는 데모. 설치 직후 동작 확인용이다.

출발 지점에서 직진하다가 좌우로 한 번씩 꺾어 본다. 개루프(open-loop) 주행이라
도로를 따라가지는 못한다 — 차선 유지는 팀이 만들 알고리즘의 몫이고,
이 스크립트는 "브릿지-제어-센서가 연결되어 있다"를 눈으로 확인하는 용도다.
"""

import sys
import time

import rclpy
from ackermann_msgs.msg import AckermannDrive
from rclpy.node import Node
from sensor_msgs.msg import Range
from std_srvs.srv import Trigger

from av_sim_bringup.sim_connection import require_simulator

# (설명, 속도 m/s, 조향 rad, 지속 시간 s)
LAP = [
    ("출발 - 직진", 6.0, 0.0, 6.0),
    ("좌회전", 4.0, 0.25, 4.0),
    ("직진", 6.0, 0.0, 5.0),
    ("우회전", 4.0, -0.25, 4.0),
    ("직진", 6.0, 0.0, 5.0),
    ("정지 (워치독 확인)", 0.0, 0.0, 3.0),
]


class DemoDriver(Node):
    def __init__(self):
        super().__init__("demo_driver")
        self.pub = self.create_publisher(AckermannDrive, "/cmd_ackermann", 10)
        self.ranges = {}
        for side in ("front", "rear", "left", "right"):
            self.create_subscription(
                Range, f"/ultrasonic/{side}",
                lambda msg, s=side: self.ranges.__setitem__(s, msg.range), 10)
        self.reset = self.create_client(Trigger, "/reset_simulation")

    def run_step(self, label, speed, steering, seconds):
        print(f"\n▶ {label}  ({speed:.1f} m/s, 조향 {steering:+.2f} rad, {seconds:.1f}초)")
        end = time.time() + seconds
        last_print = 0.0

        while time.time() < end:
            msg = AckermannDrive()
            msg.speed = float(speed)
            msg.steering_angle = float(steering)
            self.pub.publish(msg)
            rclpy.spin_once(self, timeout_sec=0.05)

            now = time.time()
            if now - last_print > 0.7:
                last_print = now
                r = self.ranges
                print("   초음파  "
                      f"전 {r.get('front', 0):4.2f} | "
                      f"후 {r.get('rear', 0):4.2f} | "
                      f"좌 {r.get('left', 0):4.2f} | "
                      f"우 {r.get('right', 0):4.2f}  (m)")


def main():
    rclpy.init()
    node = DemoDriver()

    print("=" * 58)
    print(" Unity 자율주행 시뮬레이터 - 데모 주행")
    print("=" * 58)

    require_simulator(node)
    if not node.reset.wait_for_service(timeout_sec=10.0):
        print("\n시뮬레이터에 연결하지 못했습니다. 브릿지와 플레이어를 확인하세요.", file=sys.stderr)
        raise SystemExit(1)

    print("\n출발 지점으로 리셋합니다...")
    future = node.reset.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
    time.sleep(1.5)

    for step in LAP:
        node.run_step(*step)

    print("\n" + "=" * 58)
    print(" 데모 종료. 직접 몰아보려면:")
    print("   ros2 run av_sim_bringup teleop_ackermann")
    print("=" * 58)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

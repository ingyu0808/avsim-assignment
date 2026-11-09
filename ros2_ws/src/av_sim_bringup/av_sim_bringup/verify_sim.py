#!/usr/bin/env python3
"""Unity 시뮬레이터의 제어·워치독·리셋을 ROS2 인터페이스만으로 검증한다.

Unity 내부를 들여다보지 않고, 팀원이 쓰게 될 토픽/서비스만으로 확인한다.
"""

import time

import rclpy
from ackermann_msgs.msg import AckermannDrive
from rclpy.node import Node
from sensor_msgs.msg import Imu, Range
from std_msgs.msg import String
from std_srvs.srv import Trigger

from av_sim_bringup.sim_connection import require_simulator

RESULTS = []


def check(name, passed, detail=""):
    RESULTS.append((name, passed, detail))
    print(f"{'  OK  ' if passed else '  !!  '}{name}" + (f"  ({detail})" if detail else ""))


class Verifier(Node):
    def __init__(self):
        super().__init__("sim_verifier")
        self.pub = self.create_publisher(AckermannDrive, "/cmd_ackermann", 10)
        self.front = None
        self.left = None
        self.imu = None
        self.traffic = None
        # 주행 검증은 위치가 아니라 IMU로 한다. 맵 어디서 출발하든 통한다.
        self.accelerations = []
        self.yaw_rates = []
        self.create_subscription(Range, "/ultrasonic/front", self._on_front, 10)
        self.create_subscription(Range, "/ultrasonic/left", self._on_left, 10)
        self.create_subscription(Imu, "/imu/data", self._on_imu, 10)
        self.create_subscription(String, "/traffic_lights", self._on_traffic, 10)
        self.reset_client = self.create_client(Trigger, "/reset_simulation")

    def _on_front(self, msg):
        self.front = msg

    def _on_left(self, msg):
        self.left = msg

    def _on_imu(self, msg):
        self.imu = msg
        self.accelerations.append(msg.linear_acceleration.x)
        self.yaw_rates.append(msg.angular_velocity.z)

    def _on_traffic(self, msg):
        self.traffic = msg.data

    def spin_for(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def drive(self, speed, steering, seconds):
        """워치독(0.5초) 때문에 명령을 계속 재발행해야 한다."""
        end = time.time() + seconds
        while time.time() < end:
            msg = AckermannDrive()
            msg.speed = float(speed)
            msg.steering_angle = float(steering)
            self.pub.publish(msg)
            rclpy.spin_once(self, timeout_sec=0.05)


def main():
    rclpy.init()
    node = Verifier()

    # 앞선 주행으로 차량이 옮겨져 있을 수 있으므로 항상 출발 지점에서 시작한다.
    print("=== 0. 출발 지점으로 리셋 ===")
    # Unity가 붙기 전에 서비스를 호출하면 브릿지가 죽는다.
    require_simulator(node)
    if not node.reset_client.wait_for_service(timeout_sec=10.0):
        print("!!  /reset_simulation 서비스가 없습니다. 브릿지와 시뮬레이터를 확인하세요.")
        raise SystemExit(1)
    future = node.reset_client.call_async(Trigger.Request())
    rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
    print("  OK  리셋 완료")
    node.spin_for(2)

    print("\n=== 1. 센서 수신 확인 ===")
    node.spin_for(3)
    check("초음파 front 수신", node.front is not None)
    check("초음파 left 수신", node.left is not None)
    check("IMU 수신", node.imu is not None)

    if node.front is None:
        print("센서 데이터가 없어 중단합니다.")
        raise SystemExit(1)

    check("Range 메시지 규격 (max=4m, FOV=15도)",
          abs(node.front.max_range - 4.0) < 1e-3 and abs(node.front.field_of_view - 0.2618) < 1e-3,
          f"max={node.front.max_range}, fov={node.front.field_of_view:.4f}")
    check("radiation_type = ULTRASOUND(0)", node.front.radiation_type == 0)
    check("frame_id 규약", node.front.header.frame_id == "ultrasonic_front",
          node.front.header.frame_id)

    print("\n=== 2. 정지 상태 IMU (중력 반작용) ===")
    # ROS FLU에서 위쪽은 +Z. 정지 중이면 z축 가속도가 +9.81 근처여야 한다.
    az = node.imu.linear_acceleration.z
    check("정지 시 수직 가속도 ~ +9.81", 9.0 < az < 10.6, f"{az:.2f} m/s^2")

    print("\n=== 3. 전진 제어 (IMU 가속도로 확인) ===")
    # 캠퍼스 맵에는 정해진 위치의 장애물이 없으므로 거리 대신 IMU를 쓴다.
    # 어느 지점에서 출발하든 동작하는 검증이다.
    node.accelerations.clear()
    node.drive(speed=4.0, steering=0.0, seconds=3.0)
    forward_peak = max(node.accelerations) if node.accelerations else 0.0
    check("가속 명령에 전방 가속도가 잡힘", forward_peak > 0.5,
          f"최대 {forward_peak:.2f} m/s^2")

    print("\n=== 4. 조향 제어 ===")
    node.yaw_rates.clear()
    node.drive(speed=3.0, steering=0.3, seconds=3.0)
    left_turn = max(node.yaw_rates) if node.yaw_rates else 0.0
    node.yaw_rates.clear()
    node.drive(speed=3.0, steering=-0.3, seconds=3.0)
    right_turn = min(node.yaw_rates) if node.yaw_rates else 0.0
    check("좌조향에 좌회전 각속도 발생 (+z)", left_turn > 0.05, f"{left_turn:+.3f} rad/s")
    check("우조향에 우회전 각속도 발생 (-z)", right_turn < -0.05, f"{right_turn:+.3f} rad/s")

    print("\n=== 5. 워치독 (명령 중단 시 정지) ===")
    # 명령을 끊으면 0.5초 뒤 감속이 시작되고 곧 정지해야 한다.
    node.spin_for(3.0)
    node.accelerations.clear()
    node.yaw_rates.clear()
    node.spin_for(2.0)
    resting_accel = max(abs(a) for a in node.accelerations) if node.accelerations else 0.0
    resting_yaw = max(abs(y) for y in node.yaw_rates) if node.yaw_rates else 0.0
    check("명령 중단 후 차량 정지 (가속도 0 근처)", resting_accel < 0.6,
          f"최대 {resting_accel:.2f} m/s^2")
    check("정지 후 회전도 없음", resting_yaw < 0.05, f"최대 {resting_yaw:.3f} rad/s")

    print("\n=== 5b. 신호등 ===")
    node.spin_for(2.0)
    check("신호등 상태 토픽 수신", node.traffic is not None,
          node.traffic or "수신 없음")
    if node.traffic:
        states = {pair.split(":")[1] for pair in node.traffic.split(",") if ":" in pair}
        check("유효한 신호 상태만 발행", states <= {"RED", "YELLOW", "GREEN"}, ", ".join(sorted(states)))

    print("\n=== 6. 리셋 서비스 ===")
    if not node.reset_client.wait_for_service(timeout_sec=5.0):
        check("/reset_simulation 서비스 존재", False)
    else:
        check("/reset_simulation 서비스 존재", True)
        future = node.reset_client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(node, future, timeout_sec=5.0)
        check("리셋 호출 성공", future.done() and future.result() is not None and future.result().success,
              future.result().message if future.done() and future.result() else "응답 없음")

        node.spin_for(2.0)
        node.accelerations.clear()
        node.spin_for(1.5)
        settled = max(abs(a) for a in node.accelerations) if node.accelerations else 0.0
        check("리셋 후 차량이 안정 상태", settled < 1.0, f"최대 {settled:.2f} m/s^2")

    node.destroy_node()
    rclpy.shutdown()

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    print(f"\n{'=' * 50}")
    print(f"통과 {passed}/{len(RESULTS)}")
    if passed != len(RESULTS):
        print("실패:", [n for n, ok, _ in RESULTS if not ok])
        raise SystemExit(1)
    print("전체 통과")


if __name__ == "__main__":
    main()

"""키보드로 /cmd_ackermann 을 발행하는 수동 조작 노드.

Unity 쪽 워치독(0.5초) 때문에 명령을 계속 재발행해야 차량이 움직인다.
"""

import os
import select
import sys
import termios
import tty

import rclpy
from ackermann_msgs.msg import AckermannDrive
from rclpy.node import Node

from av_sim_bringup.command_mapping import DriveCommand, apply_key

HELP = """
Unity 차량 수동 조작
--------------------
  w / s : 가속 / 감속
  a / d : 좌 / 우 조향
  space : 즉시 정지
  q     : 종료

  키를 놓아도 설정한 속도와 조향을 유지합니다. 정지는 space입니다.
"""

PUBLISH_PERIOD = 0.1  # 초. 워치독 타임아웃 0.5초보다 충분히 짧아야 한다.


class TeleopAckermann(Node):
    def __init__(self):
        super().__init__("teleop_ackermann")
        self._publisher = self.create_publisher(AckermannDrive, "/cmd_ackermann", 10)
        self._command = DriveCommand(0.0, 0.0)
        self.create_timer(PUBLISH_PERIOD, self._publish_current)

    def handle_key(self, key: str) -> None:
        self._command = apply_key(self._command, key)
        self.get_logger().info(
            f"speed={self._command.speed:.2f} m/s  steer={self._command.steering_angle:.2f} rad"
        )

    def _publish_current(self) -> None:
        msg = AckermannDrive()
        msg.speed = float(self._command.speed)
        msg.steering_angle = float(self._command.steering_angle)
        self._publisher.publish(msg)


def _read_key(timeout: float = 0.05):
    """키가 없어도 반환해 ROS 타이머가 워치독 주기 안에 실행되게 한다."""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd, when=termios.TCSANOW)
        if not select.select([sys.stdin], [], [], timeout)[0]:
            return None
        return os.read(fd, 1).decode("latin-1")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def main() -> None:
    rclpy.init()
    node = TeleopAckermann()
    print(HELP)

    try:
        while rclpy.ok():
            key = _read_key()
            if key in ("q", "\x03", ""):  # q, Ctrl+C 또는 EOF
                break
            if key is not None:
                node.handle_key(key.lower())
            rclpy.spin_once(node, timeout_sec=0.0)
    finally:
        if rclpy.ok():
            node.handle_key(" ")
            node._publish_current()
            rclpy.spin_once(node, timeout_sec=0.05)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

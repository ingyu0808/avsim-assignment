"""시뮬레이터가 실제로 붙어 있는지 확인하는 공용 헬퍼.

왜 필요한가:
    Unity가 브릿지에 연결되지 않은 상태에서 /reset_simulation을 호출하면
    ros_tcp_endpoint가 Unity의 응답을 받지 못한 채 rclpy에 None을 넘기고,
    rclpy가 TypeError를 던지며 **브릿지 프로세스 전체가 죽는다.**
    (rclpy/service.py의 send_response는 응답 타입을 검사한다)

    서비스가 존재한다는 것과 Unity가 붙어 있다는 것은 다르다.
    엔드포인트는 Unity가 없어도 서비스를 광고하기 때문이다.
    그래서 하트비트 토픽으로 "시뮬레이터가 살아 있음"을 먼저 확인한다.
"""

import time

import rclpy
from std_msgs.msg import String

HEARTBEAT_TOPIC = "/unity/heartbeat"


def wait_for_simulator(node, timeout: float = 20.0) -> bool:
    """Unity가 붙어 하트비트를 보내고 있으면 True.

    서비스를 호출하기 전에 반드시 확인한다.
    """
    seen = {}
    subscription = node.create_subscription(
        String, HEARTBEAT_TOPIC, lambda msg: seen.setdefault("beat", msg.data), 10
    )

    deadline = time.time() + timeout
    while time.time() < deadline and "beat" not in seen:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_subscription(subscription)

    return "beat" in seen


def require_simulator(node, timeout: float = 20.0) -> None:
    """시뮬레이터가 없으면 안내하고 종료한다. 브릿지를 죽이지 않기 위한 안전장치."""
    if wait_for_simulator(node, timeout):
        return

    print(
        f"\n시뮬레이터가 연결되어 있지 않습니다 ({HEARTBEAT_TOPIC} 수신 없음).\n"
        "  1) 브릿지가 떠 있는지: ros2 launch av_sim_bringup sim.launch.py\n"
        "  2) 시뮬레이터를 실행했는지: ./UnitySim/Build/Linux/AvSim\n"
        "\n연결 전에 /reset_simulation을 호출하면 브릿지가 죽으므로 중단합니다."
    )
    raise SystemExit(1)

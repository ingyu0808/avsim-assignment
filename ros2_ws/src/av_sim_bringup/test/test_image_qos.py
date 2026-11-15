from pathlib import Path

from rclpy.qos import ReliabilityPolicy

from av_sim_bringup.image import CAMERA_QOS

PACKAGE = Path(__file__).resolve().parents[1] / "av_sim_bringup"


def test_image_subscriptions_do_not_use_best_effort():
    # Best effort loses large images over DDS: 10-16 Hz with gaps up to 0.5 s instead of 20 Hz.
    offenders = [f"{path.name}:{number}" for path in sorted(PACKAGE.glob("*.py"))
                 for number, line in enumerate(path.read_text().splitlines(), 1)
                 if "create_subscription(Image" in line and "qos_profile_sensor_data" in line]
    assert offenders == []


def test_camera_qos_is_reliable_and_keeps_only_the_latest_frame():
    assert CAMERA_QOS.reliability == ReliabilityPolicy.RELIABLE
    assert CAMERA_QOS.depth == 1

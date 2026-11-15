from types import SimpleNamespace

import numpy as np
from rclpy.qos import ReliabilityPolicy

from student_driver.driver import CAMERA_QOS, to_bgr


def test_to_bgr_swaps_channels_and_drops_row_padding():
    rgb = np.zeros((2, 3, 3), np.uint8)
    rgb[0, 0] = (255, 0, 0)
    padded = np.zeros((2, 3 * 3 + 7), np.uint8)
    padded[:, :9] = rgb.reshape(2, 9)
    msg = SimpleNamespace(height=2, width=3, step=16, data=padded.tobytes())
    bgr = to_bgr(msg)
    assert bgr.shape == (2, 3, 3)
    assert tuple(bgr[0, 0]) == (0, 0, 255)


def test_camera_is_received_reliably_keeping_only_the_latest_frame():
    # Best effort loses large (~900 KB) images: 10-16 Hz with gaps up to 0.5 s instead of 20 Hz.
    assert CAMERA_QOS.reliability == ReliabilityPolicy.RELIABLE
    assert CAMERA_QOS.depth == 1

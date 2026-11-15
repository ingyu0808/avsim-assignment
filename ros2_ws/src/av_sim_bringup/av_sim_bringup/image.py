"""sensor_msgs/Image decoding and QoS shared by tools and perception."""

import numpy as np
from rclpy.qos import QoSProfile, ReliabilityPolicy

# Camera images (~900 KB) must be received RELIABLE. With best effort (qos_profile_sensor_data)
# DDS drops large samples: 10-16 Hz with gaps up to 0.5 s instead of 20 Hz. Depth 1 keeps only
# the newest frame, so slow processing never works on a backlog.
CAMERA_QOS = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)


def decode_rgb(message):
    if message.encoding not in ("rgb8", "bgr8") or message.step < message.width * 3:
        raise ValueError("Expected rgb8/bgr8 image with a valid row stride")
    if len(message.data) != message.height * message.step:
        raise ValueError("Truncated image")
    rgb = np.frombuffer(bytes(message.data), np.uint8).reshape(message.height, message.step)
    rgb = rgb[:, :message.width * 3].reshape(message.height, message.width, 3)
    return rgb.copy() if message.encoding == "rgb8" else rgb[..., ::-1].copy()

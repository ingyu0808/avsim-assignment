"""sensor_msgs/Image decoding shared by tools and perception."""

import numpy as np


def decode_rgb(message):
    if message.encoding not in ("rgb8", "bgr8") or message.step < message.width * 3:
        raise ValueError("Expected rgb8/bgr8 image with a valid row stride")
    if len(message.data) != message.height * message.step:
        raise ValueError("Truncated image")
    rgb = np.frombuffer(bytes(message.data), np.uint8).reshape(message.height, message.step)
    rgb = rgb[:, :message.width * 3].reshape(message.height, message.width, 3)
    return rgb.copy() if message.encoding == "rgb8" else rgb[..., ::-1].copy()

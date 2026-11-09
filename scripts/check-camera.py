"""Check rendered ROS camera pixels, optionally saving the received frame as PNG."""
import argparse
import time

import numpy as np
import rclpy
from sensor_msgs.msg import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node("avsim_camera_validation", enable_rosout=False)
    frames = []
    node.create_subscription(Image, "/camera/image_raw", frames.append, 1)
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.2)
            if not frames:
                continue
            message = frames.pop()
            frames.clear()
            if message.encoding != "rgb8" or message.step != message.width * 3:
                raise RuntimeError("Unexpected camera image layout")
            pixels = np.frombuffer(message.data, dtype=np.uint8).reshape(message.height, message.width, 3)
            if pixels.std() < 5 or pixels.max() - pixels.min() < 30:
                continue
            if args.output:
                from PIL import Image as PillowImage
                PillowImage.fromarray(pixels).save(args.output)
            print(f"PASS: {message.width}x{message.height} RGB camera, pixel std={pixels.std():.2f}")
            return 0
        raise RuntimeError("No nonblank rendered camera frame before timeout")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())

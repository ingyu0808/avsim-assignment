"""Exit successfully only when the local endpoint node and TCP listener are ready."""
import argparse
import socket
import time

import rclpy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node("avsim_startup_probe", enable_rosout=False)
    try:
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if "ros_tcp_endpoint" not in node.get_node_names():
                continue
            try:
                with socket.create_connection(("127.0.0.1", 10000), timeout=0.5):
                    return 0
            except OSError:
                time.sleep(0.2)
        return 1
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())

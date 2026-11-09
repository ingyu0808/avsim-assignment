#!/usr/bin/env python3
"""카메라 토픽이 실제 장면을 렌더링해 보내는지 확인한다.

헤드리스(-nographics)에서는 그래픽 장치가 없어 의미 있는 픽셀이 나오지 않으므로,
반드시 화면이 있는 상태로 실행한 플레이어를 대상으로 돌려야 한다.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


class CameraChecker(Node):
    def __init__(self):
        super().__init__("camera_checker")
        self.image = None
        self.info = None
        self.create_subscription(Image, "/camera/image_raw", self._on_image, 1)
        self.create_subscription(CameraInfo, "/camera/camera_info", self._on_info, 1)

    def _on_image(self, msg):
        self.image = msg

    def _on_info(self, msg):
        self.info = msg


def main():
    rclpy.init()
    node = CameraChecker()

    for _ in range(400):
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.image is not None and node.info is not None:
            break

    if node.image is None:
        print("!!  이미지를 받지 못했습니다")
        raise SystemExit(1)

    img, info = node.image, node.info
    data = bytes(img.data)

    print(f"해상도: {img.width}x{img.height}, encoding={img.encoding}, step={img.step}")
    print(f"frame_id: {img.header.frame_id}, 데이터 길이: {len(data)}")
    print(f"camera_info: fx={info.k[0]:.1f} fy={info.k[4]:.1f} cx={info.k[2]:.1f} cy={info.k[5]:.1f}")

    ok = True

    def check(name, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print(f"{'  OK  ' if passed else '  !!  '}{name}" + (f"  ({detail})" if detail else ""))

    check("해상도 640x480", img.width == 640 and img.height == 480)
    check("encoding rgb8", img.encoding == "rgb8")
    check("데이터 길이 = w*h*3", len(data) == img.width * img.height * 3)
    check("step = w*3", img.step == img.width * 3)
    check("camera_info 크기 일치", info.width == img.width and info.height == img.height)
    check("초점거리 ~320 (수평 FOV 90도)", 315 < info.k[0] < 325, f"{info.k[0]:.1f}")

    # 실제로 무언가 그려졌는지: 전부 같은 값이면 렌더링이 안 된 것이다.
    unique = len(set(data[::997]))
    check("픽셀에 변화가 있음 (렌더링 확인)", unique > 5, f"샘플 고유값 {unique}개")

    # 위쪽 절반(하늘)이 아래쪽 절반(지면)보다 밝으면 상하가 뒤집히지 않은 것이다.
    half = len(data) // 2
    top = sum(data[:half:499]) / len(data[:half:499])
    bottom = sum(data[half::499]) / len(data[half::499])
    print(f"상단 평균 밝기 {top:.1f} / 하단 평균 밝기 {bottom:.1f}")
    check("상하 반전 없음 (위=하늘이 더 밝음)", top > bottom, f"{top:.1f} > {bottom:.1f}")

    node.destroy_node()
    rclpy.shutdown()

    print("\n전체 통과" if ok else "\n실패 항목 있음")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()

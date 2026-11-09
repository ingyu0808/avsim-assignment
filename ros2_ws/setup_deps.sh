#!/usr/bin/env bash
# ROS2 쪽 의존성을 준비한다. 새 팀원이 처음 한 번 실행하면 된다.
set -euo pipefail

WS_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/src"

echo "== apt 의존성 설치 =="
sudo apt update
sudo apt install -y ros-humble-ackermann-msgs ros-humble-nav-msgs ros-humble-tf2-ros-py \
    python3-colcon-common-extensions python3-opencv python3-numpy python3-scipy python3-pytest

echo "== ROS-TCP-Endpoint 클론 =="
if [[ -d "${WS_SRC}/ROS-TCP-Endpoint" ]]; then
  echo "이미 존재함, 건너뜀"
else
  git clone -b main-ros2 https://github.com/Unity-Technologies/ROS-TCP-Endpoint.git "${WS_SRC}/ROS-TCP-Endpoint"
fi

echo "완료. 이제 ros2_ws에서 'colcon build --symlink-install'을 실행하세요."

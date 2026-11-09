#!/usr/bin/env bash
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH=/opt/ros/humble/bin:/usr/bin:/bin
unset PYTHONHOME PYTHONPATH CONDA_PREFIX CONDA_DEFAULT_ENV
source /opt/ros/humble/setup.bash
source "$ROOT/ros2_ws/install/setup.bash"
exec ros2 launch av_sim_bringup sim.launch.py

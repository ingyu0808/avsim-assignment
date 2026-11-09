#!/usr/bin/env bash
# Start the local ROS endpoint once and verify both DDS discovery and TCP readiness.
set -eo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH=/opt/ros/humble/bin:/usr/bin:/bin
unset PYTHONHOME PYTHONPATH CONDA_PREFIX CONDA_DEFAULT_ENV
if [[ ! -f /opt/ros/humble/setup.bash || ! -f "$ROOT/ros2_ws/install/setup.bash" ]]; then
    echo "ROS2 Humble or workspace missing. Build ros2_ws first." >&2
    exit 1
fi
source /opt/ros/humble/setup.bash
source "$ROOT/ros2_ws/install/setup.bash"
RUNTIME="${XDG_RUNTIME_DIR:-/tmp/avsim-$UID}"
mkdir -p "$RUNTIME"
exec 9>"$RUNTIME/avsim-ros-start.lock"
flock -w 30 9
if /usr/bin/python3 "$ROOT/scripts/ros-ready.py" --timeout 2; then
    echo "ROS endpoint ready (existing node)."
    exit 0
fi
if ! systemctl --user is-active --quiet avsim-ros-bridge.service; then
    systemctl --user reset-failed avsim-ros-bridge.service 2>/dev/null || true
    ROS_ENV=(--setenv="PATH=$PATH" --setenv="ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}")
    for variable in ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION CYCLONEDDS_URI FASTRTPS_DEFAULT_PROFILES_FILE; do
        if [[ -v "$variable" ]]; then ROS_ENV+=(--setenv="$variable=${!variable}"); fi
    done
    systemd-run --user --unit=avsim-ros-bridge --collect \
        --property=Restart=on-failure --property=RestartSec=2 \
        --working-directory="$ROOT" "${ROS_ENV[@]}" \
        /bin/bash --noprofile --norc "$ROOT/scripts/ros-bridge.sh"
fi
if ! /usr/bin/python3 "$ROOT/scripts/ros-ready.py" --timeout 20; then
    echo "ROS endpoint failed to start. See: journalctl --user -u avsim-ros-bridge -n 50" >&2
    exit 1
fi
echo "ROS endpoint ready at 127.0.0.1:10000."

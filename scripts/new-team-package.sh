#!/usr/bin/env bash
# 뼈대(student_driver)를 복사해 제출용 패키지 team_<번호> 를 만든다.
#
#   ./scripts/new-team-package.sh 07     # → ros2_ws/src/team_07
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! "${1:-}" =~ ^[0-9]{2}$ ]]; then
    echo "사용법: $0 <두 자리 팀 번호>  (예: $0 07)" >&2
    exit 2
fi
NAME="team_$1"
SRC="$ROOT/ros2_ws/src/student_driver"
DST="$ROOT/ros2_ws/src/$NAME"
if [[ -e "$DST" ]]; then
    echo "$DST 가 이미 있습니다." >&2
    exit 1
fi
mkdir -p "$DST"
tar -C "$SRC" --exclude=__pycache__ --exclude=.pytest_cache -cf - . | tar -C "$DST" -xf -
mv "$DST/student_driver" "$DST/$NAME"
mv "$DST/resource/student_driver" "$DST/resource/$NAME"
grep -rl student_driver "$DST" | xargs sed -i "s/student_driver/$NAME/g"
echo "만들었습니다: $DST"
echo "빌드: cd $ROOT/ros2_ws && colcon build --symlink-install --packages-select $NAME"
echo "실행: ros2 launch $NAME drive.launch.py"

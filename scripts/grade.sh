#!/usr/bin/env bash
# 교수자용: 학생 주행 스택을 비공개 시드 여러 개로 돌려 시나리오 점수를 평균낸다.
#
#   ./scripts/grade.sh --launch "ros2 launch my_pkg drive.launch.py" [--out DIR] SEED...
#   ./scripts/grade.sh --launch "..." [--out DIR] --no-scenario     # 중간 점검: 이벤트 없는 판 1회
#
# 시드마다 플레이어를 새로 띄우고, 학생 명령을 실행한 뒤 결과 파일이 생기거나
# 1500 s가 지나면 둘 다 종료한다. 결과는 DIR/<seed>.json (중간 점검은 DIR/midterm.json) 에 남는다.
# 플레이어는 채점 모드(-grading)로 떠서 신호 정답 토픽을 발행하지 않는다.
# 창 없이(-batchmode) GPU로 렌더링하므로 모니터가 없어도 된다.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAUNCH=""
OUT="/tmp/avsim-grade-$(date +%Y%m%d-%H%M%S)"
SEEDS=()
MIDTERM=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --launch) LAUNCH="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --no-scenario) MIDTERM=true; shift ;;
        *) SEEDS+=("$1"); shift ;;
    esac
done
if $MIDTERM; then
    [[ ${#SEEDS[@]} -eq 0 ]] || { echo "--no-scenario 와 시드는 함께 쓸 수 없습니다." >&2; exit 2; }
    SEEDS=(midterm)
fi
if [[ -z "$LAUNCH" || ${#SEEDS[@]} -eq 0 ]]; then
    echo "사용법: $0 --launch \"<학생 실행 명령>\" [--out DIR] (SEED... | --no-scenario)" >&2
    exit 2
fi
mkdir -p -m 700 "$OUT"
export PATH=/opt/ros/humble/bin:/usr/bin:/bin
unset PYTHONHOME PYTHONPATH CONDA_PREFIX CONDA_DEFAULT_ENV
# ROS setup 스크립트는 정의되지 않은 변수를 참조하므로 잠시 -u를 끈다.
set +u
source /opt/ros/humble/setup.bash
source "$ROOT/ros2_ws/install/setup.bash"
set -u

stop_group() {
    [[ -n "${1:-}" ]] || return 0
    kill -TERM -- "-$1" 2>/dev/null || true
    for _ in $(seq 50); do kill -0 -- "-$1" 2>/dev/null || return 0; sleep 0.2; done
    kill -KILL -- "-$1" 2>/dev/null || true
}

# 리셋 때 쓰인 결과는 채점 대상이 아니다(완주, 시간 초과, 종료만 인정).
is_final() {
    [[ -f "$1" ]] && /usr/bin/python3 -I -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("reason") in ("completed","timeout","quit") else 1)' "$1" 2>/dev/null
}

for SEED in "${SEEDS[@]}"; do
    RESULT="$OUT/$SEED.json"
    rm -f "$RESULT"
    echo "== seed $SEED"
    if $MIDTERM; then ROUND=(--no-scenario); else ROUND=(--seed "$SEED"); fi
    # 토픽 목록은 이전 실행의 DDS 정보가 남아 있을 수 있어, 실제 메시지를 받을 때까지 기다린다.
    READY=false
    for ATTEMPT in 1 2; do
        # 오래 켜 둔 브릿지는 메시지를 버리는 상태로 굳을 수 있어 판마다 새로 띄운다.
        systemctl --user restart avsim-ros-bridge.service 2>/dev/null || true
        setsid "$ROOT/scripts/run-sim.sh" "${ROUND[@]}" --headless --result "$RESULT" -grading >> "$OUT/$SEED-player.log" 2>&1 &
        PLAYER=$!
        for _ in $(seq 60); do
            kill -0 "$PLAYER" 2>/dev/null || break
            # 데몬이 굳어 있으면 echo가 바로 실패하므로 데몬 없이 직접 받는다.
            if timeout 6 ros2 topic echo --once --no-daemon /unity/heartbeat > /dev/null 2>&1; then READY=true; break; fi
            sleep 1
        done
        $READY && break
        echo "seed $SEED: 플레이어 준비 실패 (시도 $ATTEMPT), 로그: $OUT/$SEED-player.log"
        stop_group "$PLAYER"
        sleep 5
    done
    $READY || { echo "seed $SEED: 플레이어를 띄우지 못해 건너뜀"; continue; }
    setsid bash -c "$LAUNCH" > "$OUT/$SEED-student.log" 2>&1 &
    STUDENT=$!
    START=$(date +%s)
    while ! is_final "$RESULT" && [[ $(( $(date +%s) - START )) -lt 1500 ]]; do sleep 2; done
    stop_group "$STUDENT"
    stop_group "$PLAYER"
    is_final "$RESULT" || { echo "seed $SEED: 최종 결과 없음 (0점 처리)"; rm -f "$RESULT"; }
done

RESULTS=()
for SEED in "${SEEDS[@]}"; do RESULTS+=("$OUT/$SEED.json"); done
/usr/bin/python3 "$ROOT/scripts/scenario_average.py" "${RESULTS[@]}" | tee "$OUT/summary.txt"

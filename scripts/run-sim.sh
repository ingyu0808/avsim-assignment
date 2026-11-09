#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLAYER="$ROOT/UnitySim/Build/Linux/AvSim"
# 시나리오 옵션: --seed N(같은 판 재현), --no-scenario(이벤트 끄기), --result PATH(결과 파일 위치)
# --headless: 창 없이 GPU로 렌더링한다(-batchmode). 모니터가 없거나 꺼진 채점 PC용.
ARGS=()
HEADLESS=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --seed) ARGS+=(-scenarioSeed "$2"); shift 2 ;;
        --no-scenario) ARGS+=(-scenarioOff); shift ;;
        --result) ARGS+=(-scenarioResult "$2"); shift 2 ;;
        --headless) HEADLESS=true; shift ;;
        *) ARGS+=("$1"); shift ;;
    esac
done
if $HEADLESS; then
    COMMAND=("$PLAYER" -batchmode -force-glcore "${ARGS[@]}")
else
    COMMAND=("$PLAYER" -force-glcore -screen-fullscreen 0 -screen-width 1280 -screen-height 720 "${ARGS[@]}")
fi
if [[ -n "${AVSIM_DRY_RUN:-}" ]]; then
    echo "${COMMAND[@]}"
    exit 0
fi
if [[ ! -x "$PLAYER" ]]; then
    echo "시뮬레이터가 없습니다. ./scripts/get-sim.sh 로 받으세요. (Unity 소스가 있다면 ./scripts/build-player.sh)" >&2
    exit 1
fi
MANAGED_PID="$(systemctl --user show avsim-erica.service -p MainPID --value 2>/dev/null || true)"
if [[ "$MANAGED_PID" =~ ^[0-9]+$ && "$MANAGED_PID" != 0 && "$MANAGED_PID" != "$$" ]]; then
    echo "Stopping the previous managed simulator instance."
    systemctl --user stop avsim-erica.service
fi
"$ROOT/scripts/ensure-ros.sh"
exec "${COMMAND[@]}"

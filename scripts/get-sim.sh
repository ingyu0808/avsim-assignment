#!/usr/bin/env bash
# 시뮬레이터(Linux 플레이어)를 받아 UnitySim/Build/Linux 에 푼다.
# git으로 받았다면 처음 한 번, 그리고 git pull 뒤 VERSION이 바뀌었을 때 실행한다.
#
#   ./scripts/get-sim.sh                 # 이 저장소(origin)의 GitHub Release v<버전>에서 받는다
#   ./scripts/get-sim.sh FILE.tar.gz     # 브라우저 등으로 따로 받아 둔 파일을 푼다
#   ./scripts/get-sim.sh https://...     # 다른 주소에서 받는다
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(cut -d' ' -f1 "$ROOT/VERSION")"
ASSET="avsim-sim-$VERSION.tar.gz"
DEST="$ROOT/UnitySim/Build/Linux"
SOURCE="${1:-}"

if [[ -z "$SOURCE" && -x "$DEST/AvSim" && "$(cat "$DEST/VERSION" 2>/dev/null)" == "$VERSION" ]]; then
    echo "시뮬레이터 $VERSION 이 이미 있습니다: $DEST"
    exit 0
fi
if [[ -z "$SOURCE" ]]; then
    ORIGIN="$(git -C "$ROOT" remote get-url origin 2>/dev/null || true)"
    GITHUB='github\.com[:/]([^/]+)/([^/]+)$'
    if [[ ! "$ORIGIN" =~ $GITHUB ]]; then
        echo "이 폴더의 git origin이 GitHub 주소가 아닙니다 (${ORIGIN:-없음})." >&2
        echo "시뮬레이터 파일 $ASSET 을 받아 두고 ./scripts/get-sim.sh <파일 경로> 로 실행하세요." >&2
        exit 1
    fi
    SOURCE="https://github.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}/releases/download/v$VERSION/$ASSET"
fi

# 저장소 안에 임시 폴더를 두어야 마지막 mv가 복사 없이 끝난다.
TMP="$(mktemp -d "$ROOT/.get-sim.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
if [[ "$SOURCE" =~ ^https?:// ]]; then
    echo "받는 중: $SOURCE"
    if ! curl -fL --progress-bar -o "$TMP/$ASSET" "$SOURCE"; then
        echo "받지 못했습니다. 저장소가 비공개라면 GitHub의 Releases 페이지에서 $ASSET 을 브라우저로 받고" >&2
        echo "./scripts/get-sim.sh <받은 파일 경로> 로 실행하세요." >&2
        exit 1
    fi
    SOURCE="$TMP/$ASSET"
fi
mkdir "$TMP/x"
tar -xzf "$SOURCE" -C "$TMP/x"
if [[ ! -x "$TMP/x/UnitySim/Build/Linux/AvSim" ]]; then
    echo "시뮬레이터 파일이 아닙니다 (UnitySim/Build/Linux/AvSim 이 없음): $SOURCE" >&2
    exit 1
fi
rm -rf "$DEST"
mkdir -p "$(dirname "$DEST")"
mv "$TMP/x/UnitySim/Build/Linux" "$DEST"
GOT="$(cat "$DEST/VERSION" 2>/dev/null || echo '?')"
echo "시뮬레이터 $GOT 을 풀었습니다: $DEST"
if [[ "$GOT" != "$VERSION" ]]; then
    echo "주의: 저장소 버전은 $VERSION 인데 시뮬레이터 버전은 $GOT 입니다." >&2
fi

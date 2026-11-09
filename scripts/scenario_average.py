#!/usr/bin/env python3
"""시드별 시나리오 결과 파일을 읽어 점수표와 평균을 출력한다. 없는 파일은 0점으로 센다."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ros2_ws/src/av_sim_bringup"))

from av_sim_bringup.scenario_score import average, format_table, load_result, summarize  # noqa: E402


def main():
    results = []
    for path in sys.argv[1:]:
        try:
            result = load_result(path)
        except (OSError, json.JSONDecodeError):
            print(f"{path}: 결과 없음 → 0점")
            stem = Path(path).stem
            results.append(dict(seed=int(stem) if stem.lstrip("-").isdigit() else stem, score=0))
            continue
        print(format_table(summarize(result)))
        results.append(result)
    summary = average(results)
    print(f"\n시드 {summary['seeds']} 점수 {summary['scores']} → 평균 {summary['mean']}")


if __name__ == "__main__":
    main()

from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "av_sim_bringup"


def test_only_verify_sim_listens_for_the_removed_signal_truth_topic():
    # 시뮬레이터는 v1.1부터 /traffic_lights를 내보내지 않는다. verify_sim만 "오지 않음"을 확인한다.
    users = sorted(path.name for path in PACKAGE.glob("*.py") if '"/traffic_lights' in path.read_text())
    assert users == ["verify_sim.py"]

import sys
from pathlib import Path

# colcon으로 설치하지 않고 pytest를 돌릴 때도 같은 워크스페이스의 av_sim_bringup(경로 계산)을 쓴다.
SIBLING = Path(__file__).resolve().parents[2] / "av_sim_bringup"
if SIBLING.is_dir() and str(SIBLING) not in sys.path:
    sys.path.insert(0, str(SIBLING))

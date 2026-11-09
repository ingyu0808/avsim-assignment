"""브릿지를 띄우는 통합 launch. Unity Editor의 Play는 사람이 누른다.

teleop은 raw 터미널 입력이 필요해 launch로 띄우면 키 입력을 받지 못하므로,
별도 터미널에서 `ros2 run av_sim_bringup teleop_ackermann`으로 실행한다.
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    bridge_launch = PathJoinSubstitution(
        [FindPackageShare("av_sim_bringup"), "launch", "bridge.launch.py"]
    )

    return LaunchDescription(
        [IncludeLaunchDescription(PythonLaunchDescriptionSource([bridge_launch]))]
    )

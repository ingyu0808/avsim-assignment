"""ROS 브릿지(ros_tcp_endpoint)를 띄우는 launch. 시뮬레이터(플레이어나 Unity Editor의 Play)는 따로 띄운다."""

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

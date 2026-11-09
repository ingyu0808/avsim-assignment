from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # 제출할 실행 파일입니다. 노드를 더 만들면 여기에 추가하세요.
    return LaunchDescription([
        DeclareLaunchArgument("speed", default_value="5.0"),
        Node(package="student_driver", executable="driver", output="screen",
             parameters=[{"speed": ParameterValue(LaunchConfiguration("speed"), value_type=float)}]),
    ])

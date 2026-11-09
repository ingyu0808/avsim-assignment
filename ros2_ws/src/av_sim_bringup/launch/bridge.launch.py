"""Unity와 통신할 ROS-TCP-Endpoint 서버를 띄운다."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 같은 머신에서 Unity를 돌리므로 기본값은 localhost다.
    # 나중에 Unity를 다른 머신으로 분리하면 launch 인자로 바꾸면 된다.
    return LaunchDescription(
        [
            DeclareLaunchArgument("ros_ip", default_value="127.0.0.1"),
            DeclareLaunchArgument("ros_tcp_port", default_value="10000"),
            Node(
                package="ros_tcp_endpoint",
                executable="default_server_endpoint",
                name="ros_tcp_endpoint",
                emulate_tty=True,
                output="screen",
                parameters=[
                    {
                        "ROS_IP": LaunchConfiguration("ros_ip"),
                        "ROS_TCP_PORT": LaunchConfiguration("ros_tcp_port"),
                    }
                ],
            ),
        ]
    )

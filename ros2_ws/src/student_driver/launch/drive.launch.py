from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("speed", default_value="5.0"),
        Node(package="student_driver", executable="perception", output="screen"),
        Node(package="student_driver", executable="route_follower", output="screen",
             parameters=[{"speed": ParameterValue(LaunchConfiguration("speed"), value_type=float)}]),
    ])

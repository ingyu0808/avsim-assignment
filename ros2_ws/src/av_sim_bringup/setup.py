from glob import glob

from setuptools import setup

package_name = "av_sim_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ingyu",
    maintainer_email="121866753+ingyu0808@users.noreply.github.com",
    description="Unity 자율주행 시뮬레이터 ROS 브릿지 실행",
    license="MIT",
)

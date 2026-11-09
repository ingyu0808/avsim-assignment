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
        ("share/" + package_name + "/config", glob("config/*.json")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="ingyu",
    maintainer_email="121866753+ingyu0808@users.noreply.github.com",
    description="Unity 자율주행 시뮬레이터용 브릿지 실행과 수동 조작 도구",
    license="MIT",
    entry_points={
        "console_scripts": [
            "teleop_ackermann = av_sim_bringup.teleop_ackermann:main",
            "demo_drive = av_sim_bringup.demo_drive:main",
            "verify_sim = av_sim_bringup.verify_sim:main",
            "check_camera = av_sim_bringup.check_camera:main",
            "verify_lap = av_sim_bringup.verify_lap:main",
        ],
    },
)

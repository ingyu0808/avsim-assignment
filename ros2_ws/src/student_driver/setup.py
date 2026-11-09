from glob import glob

from setuptools import setup

package_name = "student_driver"

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
    maintainer="student",
    maintainer_email="student@example.com",
    description="ERICA 캠퍼스 주행 과제 뼈대: 경로 추종과 빈 인식 노드",
    license="MIT",
    entry_points={
        "console_scripts": [
            "route_follower = student_driver.route_follower:main",
            "perception = student_driver.perception:main",
        ],
    },
)

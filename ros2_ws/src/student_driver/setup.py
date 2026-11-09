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
    description="ERICA 캠퍼스 주행 과제 뼈대: /cmd_ackermann을 직접 보내는 주행 노드와 경로 추종 도우미",
    license="MIT",
    entry_points={
        "console_scripts": [
            "driver = student_driver.driver:main",
        ],
    },
)

"""키 입력을 Ackermann 목표값으로 바꾸는 순수 로직 (ROS 의존성 없음)."""

from dataclasses import dataclass

SPEED_STEP = 0.5  # m/s
STEER_STEP = 0.1  # rad
MAX_SPEED = 5.0  # m/s
MAX_STEER = 0.6  # rad (약 34도)


@dataclass(frozen=True)
class DriveCommand:
    speed: float
    steering_angle: float


def apply_key(command: DriveCommand, key: str) -> DriveCommand:
    """키 하나를 적용한 새 명령을 돌려준다. 모르는 키는 그대로 통과시킨다."""
    if key == "w":
        return DriveCommand(_clamp(command.speed + SPEED_STEP, MAX_SPEED), command.steering_angle)
    if key == "s":
        return DriveCommand(_clamp(command.speed - SPEED_STEP, MAX_SPEED), command.steering_angle)
    if key == "a":
        return DriveCommand(command.speed, _clamp(command.steering_angle + STEER_STEP, MAX_STEER))
    if key == "d":
        return DriveCommand(command.speed, _clamp(command.steering_angle - STEER_STEP, MAX_STEER))
    if key == " ":
        return DriveCommand(0.0, 0.0)
    return command


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))

# ERICA 캠퍼스 자율주행 시뮬레이터

- 시뮬레이터 속 한양대 ERICA 캠퍼스 한 바퀴(2891 m, 곡선·사다리꼴 구간 포함) 자율주행
- 카메라 영상 처리(OpenCV/CNN) + ROS2 제어
- 판마다 미션 8개 무작위 배치
- 이 저장소에는 시뮬레이터와 ROS 브릿지만 있음. 주행 패키지는 처음부터 직접 작성
- 자세한 안내: [안내서](docs/assignment/student-guide.md), [PDF](docs/assignment/student-handout.pdf)

## 환경

- Ubuntu 22.04, ROS2 Humble, NVIDIA GPU
- 시스템 Python 3.10

## 설치

```bash
git clone https://github.com/ingyu0808/avsim-assignment.git
cd avsim-assignment
./scripts/get-sim.sh                  # 시뮬레이터 받기
./ros2_ws/setup_deps.sh               # apt 의존성 (sudo)
source /opt/ros/humble/setup.bash
cd ros2_ws && colcon build --symlink-install && cd ..
```

- 주행 패키지: `ros2_ws/src` 아래에 직접 생성 (예: `ros2 pkg create --build-type ament_python my_driver`)
- 업데이트: `git pull` → `./scripts/get-sim.sh` → `colcon build`

## 실행

```bash
source /opt/ros/humble/setup.bash && source ros2_ws/install/setup.bash   # 두 터미널 모두
./scripts/run-sim.sh                     # 터미널 1: 시뮬레이터 (ROS 브릿지 자동 실행)
ros2 launch my_driver drive.launch.py    # 터미널 2: 직접 만든 주행 노드
```

- 시뮬레이터 옵션: `--seed N`(같은 판 재현), `--no-scenario`(미션 없는 판), `--headless`(창 없이), `--result PATH`(결과 파일)
- 리셋: `ros2 service call /reset_simulation std_srvs/srv/Trigger` (출발 지점으로, 새 판, `/odom` 원점)
- 출발: 정문 도로 끝, 정문 횡단보도 신호 바로 앞. 도착: 한 바퀴 뒤 정문 나가는 차로에 정지
- 시간 제한: 1500 s

## 토픽

- 입력
  - `/camera/image_raw`: `Image`, rgb8 640×480, 20 Hz, 전방 카메라
    - 구독 QoS는 RELIABLE, depth 1. `qos_profile_sensor_data`(best effort)는 큰 이미지가 빠져 10~16 Hz로 끊김
  - `/camera/camera_info`: `CameraInfo`, fx = fy = 320, 수평 화각 90°
  - `/odom`: `Odometry`, 30 Hz, **휠 오도메트리**
    - 바퀴 회전 속도와 조향각만으로 적분 (정답 위치 아님, IMU 보정 없음)
    - `odom` → `base_link`, 출발·리셋 위치가 원점, 출발 방향이 +x
    - 미끄러짐·경사·조향 오차가 쌓임
  - `/imu/data`: `Imu`, 100 Hz, 자세(지도 기준 절대 자세)·각속도·가속도, 잡음 없음
  - `/ultrasonic/front`·`rear`·`left`·`right`: `Range`, 20 Hz, 최대 4 m
- 출력
  - `/cmd_ackermann`: `AckermannDrive`, 한 노드에서만 발행
    - `speed`: m/s, `steering_angle`: rad(양수 = 왼쪽, 최대 약 ±0.6)
    - 0.5 s 넘게 명령이 없으면 차 정지
- 서비스: `/reset_simulation` (`std_srvs/Trigger`)
- 신호등 위치·색: 토픽 없음. 카메라로만 인식
- `/tf` 없음

## 코스

- 정문 → 신호 3에서 우회전 → 북서쪽 S자 굽은 길 → 신호 4에서 우회전 → 서쪽 외곽 순환도로 → 남쪽 도로 → 신호 5에서 우회전해 기숙사 쪽 사다리꼴(좌회전, 좌회전) → 남쪽 도로로 우회전 → 동쪽 끝에서 좌회전 → 신호 6에서 우회전 → 정문
- 코스 그림과 단계별 길 안내: [안내서 4절](docs/assignment/student-guide.md#4-주행-코스)

## 미션

- 신호등(정지선 6곳: 출발 직후 정문 횡단보도 1곳 + 교차로 진입 전 5곳): 빨강·노랑이면 정지선 앞 정지
- 무작위 미션 8개(판마다 종류·위치 변경)
  - 늦게 건너는 사람, 무단횡단, 신호 없는 횡단보도, 가려진 아이: 정지
  - 서 있기만 하는 사람: 통과
  - 끼어드는 차: 따라가다 정지, 출발하면 다시 따라감
  - 정차 차량·공사 콘: 정지(5~15 s 뒤 치워짐)
  - 어린이보호구역: 10 km/h 이하

## 스스로 점검

- 결과 파일: `./scripts/run-sim.sh --result /tmp/run.json` → 주행 후 `/usr/bin/python3 scripts/scenario_average.py /tmp/run.json`
- 여러 시드를 창 없이: `./scripts/grade.sh --launch "ros2 launch my_driver drive.launch.py" 11 22 33`
- 위반 기준: [안내서 6절](docs/assignment/student-guide.md#6-스스로-점검하기)

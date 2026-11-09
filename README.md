# ERICA 캠퍼스 자율주행 과제

- 시뮬레이터 속 한양대 ERICA 캠퍼스 한 바퀴(1962 m) 자율주행
- 카메라 영상 처리(OpenCV/CNN) + ROS2 제어
- 판마다 미션 8개 무작위 배치
- 자세한 안내: [안내서](docs/assignment/student-guide.md), [PDF](docs/assignment/student-handout.pdf)

## 환경

- Ubuntu 22.04, ROS2 Humble, NVIDIA GPU
- 시스템 Python 3.10 (conda는 끄고 사용: `conda deactivate`)

## 설치

```bash
git clone https://github.com/ingyu0808/avsim-assignment.git
cd avsim-assignment
./scripts/get-sim.sh                  # 시뮬레이터 받기
./ros2_ws/setup_deps.sh               # apt 의존성 (sudo)
source /opt/ros/humble/setup.bash
cd ros2_ws && colcon build --symlink-install && cd ..
./scripts/new-team-package.sh 07      # 팀 번호 → ros2_ws/src/team_07
cd ros2_ws && colcon build --symlink-install --packages-select team_07 && cd ..
```

- 작성할 곳: `team_07/team_07/driver.py`의 `decide()` → (속도, 조향각) 반환
- 제출 대상: 이 팀 패키지
- 업데이트: `git pull` → `./scripts/get-sim.sh` → `colcon build`

## 실행

```bash
source /opt/ros/humble/setup.bash && source ros2_ws/install/setup.bash   # 두 터미널 모두
./scripts/run-sim.sh                     # 터미널 1: 시뮬레이터
ros2 launch team_07 drive.launch.py      # 터미널 2: 주행 스택
```

- 시뮬레이터 옵션: `--seed N`(같은 판 재현), `--no-scenario`(미션 없는 판), `--headless`(창 없이)
- 리셋: `ros2 service call /reset_simulation std_srvs/srv/Trigger`
- 뼈대 그대로 실행 시: `/odom`으로 경로 추종, 5 m/s(곡선 감속), 신호·사람 무시, 한 바퀴 후 정문 정지
- 경로 추종 도우미 `route.py`(조향각·곡선 감속 계산)는 선택. 차선을 직접 보고 조향해도 됨

## 토픽

- 입력
  - `/camera/image_raw`: `Image`, rgb8 640×480, 20 Hz, 전방 카메라
  - `/camera/camera_info`: `CameraInfo`, fx = fy = 320, 수평 화각 90°
  - `/odom`: `Odometry`, 30 Hz, 정답 위치
  - `/imu/data`: `Imu`, 100 Hz
  - `/ultrasonic/front`·`rear`·`left`·`right`: `Range`, 20 Hz, 최대 4 m
- 출력
  - `/cmd_ackermann`: `AckermannDrive`, 팀 노드가 직접 발행(한 노드에서만)
    - `speed`: m/s, `steering_angle`: rad(양수 = 왼쪽, 최대 ±0.6)
    - 0.5 s 넘게 명령이 없으면 차 정지
  - `/team/route_state`: `String`(JSON), 디버깅용. 상태, 진행 거리, 경로 이탈 거리
- 신호등 위치·색: 토픽 없음. 카메라로만 인식

## 미션

- 신호등(정지선 7곳, 모두 교차로 진입 전): 빨강·노랑이면 정지선 앞 정지
- 무작위 미션 8개(판마다 종류·위치 변경)
  - 늦게 건너는 사람, 무단횡단, 신호 없는 횡단보도, 가려진 아이: 정지
  - 서 있기만 하는 사람: 통과
  - 끼어드는 차: 따라가다 정지, 출발하면 다시 따라감
  - 정차 차량·공사 콘: 정지(5~15 s 뒤 치워짐)
  - 어린이보호구역: 10 km/h 이하

## 평가

- 성적
  - 중간 점검(2주차, 미션 없는 판): 10%
  - 최종 주행(4주차, 비공개 시드 3개 평균): 60%
  - 보고서: 20%
  - 발표·영상(5주차): 10%
- 한 판 점수: 100점에서 감점
  - 충돌, 1200 s 초과, 미완주: 그 판 0점
  - 양보 위반, 신호 위반: −20
  - 보호구역 과속: −10
  - 불필요 정지, 보행자 근접: −5
- 자체 채점: `./scripts/grade.sh --launch "ros2 launch team_07 drive.launch.py" 11 22 33`

## 제출

- 제출물
  - `team_XX.zip`: `ros2_ws/src/team_XX` 통째로, `ros2 launch team_XX drive.launch.py`로 실행 가능해야 함
  - 보고서 PDF
  - 주행 영상
- 추가 Python 패키지: `requirements.txt`에 기재
- 모델 가중치: 패키지 안에 포함, 실행 중 다운로드 금지

## 규칙

- 허용: 오픈소스, 사전학습 모델, 생성형 AI(보고서에 출처 기재)
- 금지: 팀 간 코드 공유, 시뮬레이터 수정

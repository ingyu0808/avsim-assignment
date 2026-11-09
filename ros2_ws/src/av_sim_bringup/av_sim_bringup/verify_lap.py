"""Record a real ROS lap of the reference autonomy stack. Signal colors come only from the camera."""

import argparse
from collections import Counter
import json
from pathlib import Path
import time

import cv2
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String

from .scenario_score import format_table, summarize, wait_for_result
from .image import decode_rgb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/erica-lap")
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument("--scenario-result", help="Unity -scenarioResult 경로. 주행 후 점수를 합친다")
    args = parser.parse_args()
    started_wall = time.time()
    directory = Path(args.output)
    directory.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = rclpy.create_node("verify_lap")
    status, perception, frames = {}, {}, {}
    counts, modes = Counter(), Counter()
    snapshots, stopped, entered = set(), set(), {}
    last = [0.0, 0.0]
    started = time.monotonic()
    log = (directory / "telemetry.jsonl").open("w", encoding="utf-8")

    def on_perception(msg):
        perception.clear()
        perception.update(json.loads(msg.data))
        counts[perception["signal"]] += 1
        for field in ("lane_confidence", "stopline_distance", "crosswalk_distance"):
            if perception[field] > 0:
                counts[field] += 1

    def on_status(msg):
        status.clear()
        status.update(json.loads(msg.data))
        mode, signal = status["mode"], status["signal_id"]
        modes[mode] += 1
        if "STOP" in mode or mode.startswith("WAIT_"):
            if abs(status["speed"]) < 0.15 and signal >= 0:
                stopped.add(signal)
        if signal >= 0 and status["stop_distance"] < 2.05 and signal not in entered:
            entered[signal] = dict(progress_m=status["progress_m"], image=status["signal"])
        now = time.monotonic()
        if now - last[0] > 0.25:
            log.write(json.dumps(dict(status=status, perception=perception)) + "\n")
            log.flush()
            last[0] = now
        key = f"{signal}_{mode}"
        if key not in snapshots and "debug" in frames and now - last[1] > 2:
            for name, image in frames.items():
                cv2.imwrite(str(directory / f"{key}_{name}.png"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            snapshots.add(key)
            last[1] = now

    node.create_subscription(String, "/perception/road", on_perception, 1)
    node.create_subscription(String, "/autonomy/status", on_status, 1)
    for name, topic in (("debug", "/perception/debug_image"), ("bev", "/perception/birdseye")):
        node.create_subscription(Image, topic, lambda msg, key=name: frames.update({key: decode_rgb(msg)}), qos_profile_sensor_data)
    try:
        try:
            while time.monotonic() - started < args.timeout:
                rclpy.spin_once(node, timeout_sec=0.1)
                if status.get("completed") or status.get("mode") in ("OFF_ROUTE", "OFF_ROAD", "COMMAND_CONFLICT", "RESET_FAILED", "RESET_TIMEOUT", "RESET_POSE_MISMATCH"):
                    break
        except KeyboardInterrupt:
            pass
        result = dict(completed=status.get("completed", False), final=status, detections=dict(counts),
                      modes=dict(modes),
                      stopped_signal_ids=sorted(stopped), stopline_entries=entered)
        if args.scenario_result:
            # Unity는 완주 정지, 리셋, 종료 때만 결과를 쓴다.
            scenario = wait_for_result(args.scenario_result, started_wall, 15)
            if scenario is None:
                print(f"경고: {args.scenario_result} 에 이번 주행의 시나리오 결과가 없습니다.", flush=True)
            else:
                result["scenario"] = summarize(scenario)
        (directory / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
        if "scenario" in result:
            print(format_table(result["scenario"]), flush=True)
        return 0 if result["completed"] else 1
    finally:
        log.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())

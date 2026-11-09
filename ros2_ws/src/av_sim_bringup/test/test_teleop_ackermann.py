import os
import termios
import time

import pytest

from av_sim_bringup import teleop_ackermann as teleop


@pytest.fixture
def terminal(monkeypatch):
    master, slave = os.openpty()
    stream = os.fdopen(slave, "r")
    monkeypatch.setattr(teleop.sys, "stdin", stream)
    try:
        yield master, stream
    finally:
        stream.close()
        os.close(master)


def test_no_key_returns_without_blocking_and_restores_terminal(terminal):
    _, stream = terminal
    settings = termios.tcgetattr(stream.fileno())
    started = time.monotonic()
    assert teleop._read_key(timeout=0.01) is None
    assert time.monotonic() - started < 0.5
    assert termios.tcgetattr(stream.fileno()) == settings


def test_key_is_read_without_enter_and_restores_terminal(terminal):
    master, stream = terminal
    settings = termios.tcgetattr(stream.fileno())
    os.write(master, b"w")
    assert teleop._read_key(timeout=0.1) == "w"
    assert termios.tcgetattr(stream.fileno()) == settings


def test_idle_input_keeps_spinning_and_exit_sends_stop(monkeypatch):
    calls = []

    class FakeNode:
        def handle_key(self, key):
            calls.append(("key", key))

        def _publish_current(self):
            calls.append(("publish",))

        def destroy_node(self):
            calls.append(("destroy",))

    keys = iter([None, None, "W", None, "q"])
    monkeypatch.setattr(teleop, "_read_key", lambda: next(keys))
    monkeypatch.setattr(teleop, "TeleopAckermann", FakeNode)
    monkeypatch.setattr(teleop.rclpy, "init", lambda: None)
    monkeypatch.setattr(teleop.rclpy, "ok", lambda: True)
    monkeypatch.setattr(teleop.rclpy, "shutdown", lambda: calls.append(("shutdown",)))
    monkeypatch.setattr(teleop.rclpy, "spin_once", lambda node, timeout_sec: calls.append(("spin",)))
    teleop.main()
    assert calls[:2] == [("spin",), ("spin",)]
    assert calls.count(("spin",)) == 5
    assert ("key", "w") in calls
    assert calls[-5:] == [("key", " "), ("publish",), ("spin",), ("destroy",), ("shutdown",)]


def test_buffered_keys_including_stop_are_not_lost(terminal):
    master, _ = terminal
    os.write(master, b"wa ")
    assert [teleop._read_key(timeout=0.1) for _ in range(3)] == ["w", "a", " "]

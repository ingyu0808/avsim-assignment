from av_sim_bringup.command_mapping import MAX_SPEED, MAX_STEER, DriveCommand, apply_key


def test_전진키는_속도를_올린다():
    result = apply_key(DriveCommand(0.0, 0.0), "w")

    assert result.speed > 0.0
    assert result.steering_angle == 0.0


def test_후진키는_속도를_내린다():
    result = apply_key(DriveCommand(0.0, 0.0), "s")

    assert result.speed < 0.0


def test_좌회전키는_조향각을_양수로_만든다():
    result = apply_key(DriveCommand(0.0, 0.0), "a")

    assert result.steering_angle > 0.0


def test_우회전키는_조향각을_음수로_만든다():
    result = apply_key(DriveCommand(0.0, 0.0), "d")

    assert result.steering_angle < 0.0


def test_스페이스는_즉시_정지시킨다():
    result = apply_key(DriveCommand(3.0, 0.4), " ")

    assert result == DriveCommand(0.0, 0.0)


def test_속도는_최대값을_넘지_않는다():
    command = DriveCommand(MAX_SPEED, 0.0)

    result = apply_key(command, "w")

    assert result.speed == MAX_SPEED


def test_조향각은_최대값을_넘지_않는다():
    command = DriveCommand(0.0, MAX_STEER)

    result = apply_key(command, "a")

    assert result.steering_angle == MAX_STEER


def test_모르는_키는_명령을_바꾸지_않는다():
    command = DriveCommand(1.0, 0.2)

    assert apply_key(command, "z") == command

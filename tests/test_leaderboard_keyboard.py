from bot.keyboards.inline import get_leaderboard_keyboard


def test_public_leaderboard_keyboard_has_no_day_period():
    keyboard = get_leaderboard_keyboard(current_period="week")
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]

    assert "lb:day" not in callbacks
    assert "lb:week" in callbacks
    assert "lb:month" in callbacks
    assert "lb:all" in callbacks


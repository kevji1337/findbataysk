from bot.keyboards.inline import get_main_menu_keyboard


def test_main_menu_has_no_broadcast_button_for_non_admin():
    keyboard = get_main_menu_keyboard(is_admin=False)
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "admin_broadcast" not in callbacks


def test_main_menu_has_broadcast_button_for_admin():
    keyboard = get_main_menu_keyboard(is_admin=True)
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "admin_broadcast" in callbacks


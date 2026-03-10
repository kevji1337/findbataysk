from aiogram.fsm.state import State, StatesGroup


class AdminBroadcastStates(StatesGroup):
    waiting_message = State()
    waiting_confirmation = State()

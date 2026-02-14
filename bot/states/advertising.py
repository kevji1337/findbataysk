from aiogram.fsm.state import State, StatesGroup


class AdvertisingStates(StatesGroup):
    """Состояния FSM для процесса подачи заявки на рекламу."""

    waiting_channel_link = State()  # Ожидание ссылки на канал

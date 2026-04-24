from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    price_min = State()
    price_max = State()
    area_min = State()
    area_max = State()
    room_count = State()
    district = State()
    water = State()
    electricity = State()
    lessor = State()
    ara = State()
    student_home = State()
    source = State()
    confirm = State()

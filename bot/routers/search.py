from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot.keyboards import (
    room_count_keyboard,
    source_keyboard,
    water_keyboard,
    lessor_keyboard,
    confirm_search_keyboard, electricity_keyboard,
)
from bot.states import SearchStates

router = Router()

SKIP = "⏭ Skip"


def _skip_keyboard():
    from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=SKIP)]],
        resize_keyboard=True,
    )

# start search
@router.message(F.text == "🔍 Search")
async def search_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SearchStates.price_min)
    await message.answer(
        "Let's set up your search filters.\n\n"
        "Minimum rent (€/month)? Or skip.",
        reply_markup=_skip_keyboard(),
    )

# price
@router.message(SearchStates.price_min)
async def set_price_min(message: Message, state: FSMContext) -> None:
    if message.text != SKIP:
        try:
            await state.update_data(price_min=float(message.text))
        except ValueError:
            await message.answer("Please enter a number, e.g. <b>600</b>")
            return
    await state.set_state(SearchStates.price_max)
    await message.answer("Maximum rent (€/month)? Or skip.", reply_markup=_skip_keyboard())


@router.message(SearchStates.price_max)
async def set_price_max(message: Message, state: FSMContext) -> None:
    if message.text != SKIP:
        try:
            await state.update_data(price_max=float(message.text))
        except ValueError:
            await message.answer("Please enter a number, e.g. <b>1200</b>")
            return
    await state.set_state(SearchStates.area_min)
    await message.answer("Minimum area (m²)? Or skip.", reply_markup=_skip_keyboard())

@router.message(SearchStates.area_min)
async def set_area_min(message: Message, state: FSMContext) -> None:
    if message.text != SKIP:
        try:
            await state.update_data(area_min=float(message.text))
        except ValueError:
            await message.answer("Please enter a number, e.g. <b>30</b>")
            return
        await state.set_state(SearchStates.area_max)
        await message.answer("Maximum area (m²)? Or skip.", reply_markup=_skip_keyboard())

@router.message(SearchStates.area_max)
async def set_area_max(message: Message, state: FSMContext) -> None:
    if message.text != SKIP:
        try:
            await state.update_data(area_max=float(message.text))
        except ValueError:
            await message.answer("Please enter a number, e.g. <b>80</b>")
            return
    await state.set_state(SearchStates.room_count)
    await message.answer("Number of rooms?", reply_markup=room_count_keyboard())

@router.message(SearchStates.room_count, F.data.startswith("room:"))
async def room_count(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]
    if value != "ANY":
        await state.update_data(room_count=value)
    await callback.message.edit_reply_markup()
    await state.set_state(SearchStates.district)
    await callback.message.answer(
        "District name? (e.g. <b>Kallio</b>, <b>Vuosaari</b>) Or skip.",
        reply_markup=_skip_keyboard(),
    )
    await callback.answer()

@router.message(SearchStates.district)
async def district(message: Message, state: FSMContext) -> None:
    if message.text != SKIP:
        await state.update_data(district=message.text.strip())
    await state.set_state(SearchStates.water)
    await message.answer("Water included in rent?", reply_markup=water_keyboard())


@router.callback_query(SearchStates.water, F.data.startswith("water:"))
async def set_water(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]
    if value == "true":
        await state.update_data(water_included=True)
    await callback.message.edit_reply_markup()
    await state.set_state(SearchStates.electricity)
    await callback.message.answer("Electricity included in rent?", reply_markup=electricity_keyboard())
    await callback.answer()

@router.callback_query(SearchStates.electricity, F.data.startswith("electricity:"))
async def set_electricity(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]
    if value == "true":
        await state.update_data(electricity_included=True)
    await callback.message.edit_reply_markup()
    await state.set_state(SearchStates.lessor)
    await callback.message.answer("Lessor type?", reply_markup=lessor_keyboard())
    await callback.answer()


@router.callback_query(SearchStates.source, F.data.startswith("source:"))
async def set_source(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[1]
    if value != "both":
        await state.update_data(source=value)
    await callback.message.edit_reply_markup()
    await state.set_state(SearchStates.confirm)

    data = await state.get_data()
    await callback.message.answer(
        _format_filters(data),
        reply_markup=confirm_search_keyboard(),
    )
    await callback.answer()

@router.message(SearchStates.confirm, F.data == "search:reset")
async def reset_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Filters cleared. Start over with 🔍 Search.")
    await callback.answer()


def _format_filters(data: dict) -> str:
    lines = ["<b>Your filters:</b>"]
    if data.get("price_min") or data.get("price_max"):
        lines.append(f"💶 Price: {data.get('price_min', '—')} – {data.get('price_max', '—')} €")
    if data.get("area_min") or data.get("area_max"):
        lines.append(f"📐 Area: {data.get('area_min', '—')} – {data.get('area_max', '—')} m²")
    if data.get("room_count"):
        lines.append(f"🚪 Rooms: {data['room_count']}")
    if data.get("district"):
        lines.append(f"📍 District: {data['district']}")
    if data.get("water_included"):
        lines.append("💧 Water: included")
    if data.get("electricity_included"):
        lines.append("⚡ Electricity: included")
    if "is_private_lessor" in data:
        lines.append(f"👤 Lessor: {'private' if data['is_private_lessor'] else 'agency'}")
    if data.get("source"):
        lines.append(f"🌐 Source: {data['source']}")
    if len(lines) == 1:
        lines.append("No filters set — will show all listings.")
    return "\n".join(lines)
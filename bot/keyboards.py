from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔍 Search"),
                KeyboardButton(text="📋 Latest listings"),
            ],
            [
                KeyboardButton(text="🔔 My subscription"),
                KeyboardButton(text="📊 Export Excel"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Choose an option...",
    )


def room_count_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    rooms = [
        ("Studio", "ONE_ROOM"),
        ("2 rooms", "TWO_ROOMS"),
        ("3 rooms", "THREE_ROOMS"),
        ("4 rooms", "FOUR_ROOMS"),
        ("5+ rooms", "MORE_THAN_FIVE_ROOMS"),
        ("Any", "ANY"),
    ]
    for label, data in rooms:
        builder.button(text=label, callback_data=f"room:{data}")
    builder.adjust(3)
    return builder.as_markup()


def source_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Vuokraovi", callback_data="source:vuokraovi")
    builder.button(text="SATO", callback_data="source:sato")
    builder.button(text="Both", callback_data="source:both")
    builder.adjust(3)
    return builder.as_markup()


def water_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Included only", callback_data="water:true")
    builder.button(text="🔄 Any", callback_data="water:any")
    builder.adjust(2)
    return builder.as_markup()


def electricity_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Included only", callback_data="electricity:true")
    builder.button(text="🔄 Any", callback_data="electricity:any")
    builder.adjust(2)
    return builder.as_markup()


def lessor_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 Private only", callback_data="lessor:private")
    builder.button(text="🏢 Agency only", callback_data="lessor:agency")
    builder.button(text="🔄 Any", callback_data="lessor:any")
    builder.adjust(3)
    return builder.as_markup()


def confirm_search_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Search", callback_data="search:run")
    builder.button(text="💾 Save as subscription", callback_data="search:subscribe")
    builder.button(text="✏️ Change filters", callback_data="search:reset")
    builder.adjust(1)
    return builder.as_markup()


def listings_nav_keyboard(
    offset: int, total: int, page_size: int = 5
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if offset > 0:
        builder.button(
            text="⬅️ Prev", callback_data=f"listings:prev:{offset}:{page_size}"
        )
    if offset + page_size < total:
        builder.button(
            text="➡️ Next", callback_data=f"listings:next:{offset}:{page_size}"
        )
    builder.button(
        text="📊 Export this page",
        callback_data=f"listings:export:{offset}:{page_size}",
    )
    builder.button(text="🏠 Main menu", callback_data="listings:menu")
    builder.adjust(2)
    return builder.as_markup()


def subscription_keyboard(has_sub: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_sub:
        builder.button(text="✏️ Edit filters", callback_data="sub:edit")
        builder.button(text="🔕 Pause", callback_data="sub:pause")
        builder.button(text="🗑 Delete", callback_data="sub:delete")
    else:
        builder.button(text="➕ Create subscription", callback_data="sub:create")
    builder.adjust(1)
    return builder.as_markup()

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"👋 Hi, <b>{message.from_user.first_name}</b>!\n\n"
        "I help you find rental apartments in Helsinki, Espoo and Vantaa.\n\n"
        "Use the menu below to search listings, set up notifications, or export to Excel.",
        reply_markup=main_menu(),
    )

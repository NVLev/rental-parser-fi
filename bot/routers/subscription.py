import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.db_helper import db_helper
from bot.keyboards import main_menu, subscription_keyboard
from bot.states import SearchStates
from bot.user_filter_service import UserFilterService

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "🔔 My subscription")
async def show_subscription(message: Message) -> None:
    async with db_helper.session_factory() as session:
        service = UserFilterService(session)
        user_filter = await service.get_filter(message.from_user.id)

    if user_filter:
        await message.answer(
            UserFilterService.format_filter_summary(user_filter),
            reply_markup=subscription_keyboard(has_sub=True),
        )
    else:
        await message.answer(
            "You don't have an active subscription yet.\n"
            "Set up filters with 🔍 Search, then save them as a subscription.",
            reply_markup=subscription_keyboard(has_sub=False),
        )


@router.callback_query(F.data == "sub:create")
async def create_subscription(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.answer("Let's set up your filters first.")
    from bot.routers.search import search_start

    await search_start(callback.message, state)


@router.callback_query(SearchStates.confirm, F.data == "search:subscribe")
async def save_subscription(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user_id = callback.from_user.id
    await state.clear()
    await callback.message.edit_reply_markup()

    async with db_helper.session_factory() as session:
        service = UserFilterService(session)
        await service.upsert_filter(user_id, data)

    await callback.message.answer(
        "✅ Subscription saved!\n"
        "You'll be notified when new listings match your filters.",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "sub:edit")
async def edit_subscription(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await callback.message.edit_reply_markup()
    from bot.routers.search import search_start

    await search_start(callback.message, state)


@router.callback_query(F.data == "sub:delete")
async def delete_subscription(callback: CallbackQuery) -> None:
    async with db_helper.session_factory() as session:
        service = UserFilterService(session)
        deleted = await service.deactivate_filter(callback.from_user.id)

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "🗑 Subscription deleted." if deleted else "No active subscription found.",
        reply_markup=main_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "sub:pause")
async def pause_subscription(callback: CallbackQuery) -> None:
    async with db_helper.session_factory() as session:
        service = UserFilterService(session)
        paused = await service.deactivate_filter(callback.from_user.id)

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "🔕 Subscription paused." if paused else "No active subscription found.",
        reply_markup=main_menu(),
    )
    await callback.answer()

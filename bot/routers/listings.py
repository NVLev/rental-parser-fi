import io
import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from bot.keyboards import listings_nav_keyboard, main_menu
from bot.states import SearchStates

logger = logging.getLogger(__name__)
router = Router()

PAGE_SIZE = 5

# latest listings
@router.message(F.text == "📋 Latest listings")
async def latest_listings(message: Message, state: FSMContext) -> None:
    await _show_listings(message, filters={}, offset=0)

# run search
@router.callback_query(SearchStates.confirm, F.data == "search:run")
async def run_search(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await callback.message.edit_reply_markup()
    await _show_listings(callback.message, filters=data, offset=0)
    await callback.answer()

# pagination
@router.callback_query(F.data.startswith("listings:prev:") | F.data.startswith("listings:next:"))
async def paginate_listings(callback: CallbackQuery, state: FSMContext) -> None:
    parts = callback.data.split(":")
    direction = parts[1]  # prev | next
    offset = int(parts[2])
    page_size = int(parts[3])

    new_offset = offset - page_size if direction == "prev" else offset + page_size
    new_offset = max(0, new_offset)

    data = await state.get_data()
    await callback.message.edit_reply_markup()
    await _show_listings(callback.message, filters=data, offset=new_offset, page_size=page_size)
    await callback.answer()

# export
@router.message(F.text == "📊 Export Excel")
async def export_excel_menu(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _send_excel(message, filters=data)


@router.callback_query(F.data.startswith("listings:export:"))
async def export_page_excel(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await callback.answer("Preparing file...")
    await _send_excel(callback.message, filters=data)


@router.callback_query(F.data == "listings:menu")
async def back_to_menu(callback: CallbackQuery) -> None:
    await callback.message.answer("Main menu", reply_markup=main_menu())
    await callback.answer()

async def _show_listings(
        message: Message,
        filters: dict,
        offset: int = 0,
        page_size: int = PAGE_SIZE,
) -> None:
    from app.database.db_helper import db_helper
    from app.services.listing_service import ListingService

    async with db_helper.session_factory() as session:
        service = ListingService(session)
        listings = await service.get_listings(
            price_min=filters.get("price_min"),
            price_max=filters.get("price_max"),
            area_min=filters.get("area_min"),
            area_max=filters.get("area_max"),
            district=filters.get("district"),
            room_count=filters.get("room_count"),
            water_included=filters.get("water_included"),
            is_private_lessor=filters.get("is_private_lessor"),
            source=filters.get("source"),
            limit=page_size,
            offset=offset,
        )

    if not listings:
        await message.answer(
            "😔 No listings found for your filters.",
            reply_markup=main_menu(),
        )
        return

    for listing in listings:
        await message.answer(
            _format_listing(listing),
            disable_web_page_preview=True,
        )

    # Approximate total for nav (real count would need a COUNT query)
    total_hint = offset + len(listings) + (1 if len(listings) == page_size else 0)
    await message.answer(
        f"Showing {offset + 1}–{offset + len(listings)}",
        reply_markup=listings_nav_keyboard(offset, total_hint, page_size),
    )


async def _send_excel(message: Message, filters: dict) -> None:
    from app.database.db_helper import db_helper
    from app.services.listing_service import ListingService
    from app.services.excel_service import build_excel

    async with db_helper.session_factory() as session:
        service = ListingService(session)
        listings = await service.get_listings(
            price_min=filters.get("price_min"),
            price_max=filters.get("price_max"),
            area_min=filters.get("area_min"),
            area_max=filters.get("area_max"),
            district=filters.get("district"),
            room_count=filters.get("room_count"),
            water_included=filters.get("water_included"),
            is_private_lessor=filters.get("is_private_lessor"),
            source=filters.get("source"),
            limit=1000,
            offset=0,
        )

    if not listings:
        await message.answer("No listings to export.")
        return

    excel_bytes: io.BytesIO = await build_excel(listings)
    await message.answer_document(
        BufferedInputFile(excel_bytes.read(), filename="listings.xlsx"),
        caption=f"📊 {len(listings)} listings exported",
    )


def _format_listing(listing) -> str:
    water = "✅" if listing.water_included else ("❌" if listing.water_included is False else "❓")
    elec = "✅" if listing.electricity_included else ("❌" if listing.electricity_included is False else "❓")
    lessor = f"{'👤' if listing.is_private_lessor else '🏢'} {listing.lessor_name or '—'}"

    lines = [
        f"🏠 <b>{listing.room_structure or listing.room_count}</b> · {listing.area} m²",
        f"💶 <b>{listing.price} €/mo</b>",
        f"📍 {listing.district or '—'}, {listing.address or '—'}",
        f"💧 Water: {water}  ⚡ Electricity: {elec}",
        f"📅 Available: {listing.available_from or '—'}",
        f"{lessor}",
        f"🔗 <a href='{listing.url}'>View listing</a>",
    ]
    return "\n".join(lines)
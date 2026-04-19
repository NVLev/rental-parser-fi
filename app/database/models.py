from datetime import datetime
from typing import Optional

from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database.base import Base


class Listing(Base):
    """Объявление об аренде."""

    __tablename__ = "listings"

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_external_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)

    # Идентификация
    external_id: Mapped[str] = mapped_column(String(50), unique=True)
    source: Mapped[str] = mapped_column(String(20))  # "vuokraovi" | "sato"
    url: Mapped[str] = mapped_column(String(500))

    # Основные поля
    price: Mapped[float] = mapped_column(Float)
    area: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Комнаты
    room_count: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # хранит enum-строку из API
    room_structure: Mapped[Optional[str]] = mapped_column(
        String(150), nullable=True
    )  # финская строка "2h + kk"

    # Коммунальные УСЛУГИ
    water_included: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    water_price: Mapped[Optional[float]]  # цена воды если не включена
    electricity_included: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Планировка
    floor_plan_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Доступность
    available_from: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # IMMEDIATELY | дата

    # Инфо об арендодателе
    lessor_name: Mapped[Optional[str]] = mapped_column(String(250), nullable=True)
    is_private_lessor: Mapped[Optional[bool]]

    # Мета
    published_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Связи
    seen_by: Mapped[list["SeenListing"]] = relationship(back_populates="listing")

    def __repr__(self) -> str:
        return f"<Listing {self.external_id} {self.price}€ {self.district}>"


class UserFilter(Base):
    """Фильтры поиска пользователя."""

    __tablename__ = "user_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)

    # Источник
    source: Mapped[str] = mapped_column(
        String(20), default="both"
    )  # vuokraovi | sato | both

    # Ценовой диапазон
    price_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Площадь
    area_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    area_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Район — список через запятую, например "Kallio,Kamppi"
    districts: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Количество комнат — список через запятую, например "ONE_ROOM,TWO_ROOMS"
    room_counts: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Коммунальные
    water_included_only: Mapped[bool] = mapped_column(Boolean, default=False)
    electricity_included_only: Mapped[bool] = mapped_column(Boolean, default=False)

    # Арендодатель
    is_private_lessor: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)


    # Состояние
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return (
            f"<UserFilter user={self.user_id} price={self.price_min}-{self.price_max}>"
        )


class SeenListing(Base):
    """Связь пользователь — объявление (дедупликация уведомлений)."""

    __tablename__ = "seen_listings"
    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_user_listing"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    listing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("listings.id", ondelete="CASCADE")
    )
    notified_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    listing: Mapped["Listing"] = relationship(back_populates="seen_by")

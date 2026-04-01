"""
Movement ORM model.

"tipo" uses a PostgreSQL ENUM: INGRESO | EGRESO.
"monto" is always a positive Decimal; the sign is derived from "tipo".

The balance (saldo) is NEVER stored — it is computed at query time:

    SELECT
      usuario_id,
      SUM(CASE WHEN tipo = 'INGRESO' THEN monto ELSE -monto END) AS saldo
    FROM movements
    WHERE usuario_id = :uid
    GROUP BY usuario_id;
"""

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TipoMovimiento(str, enum.Enum):
    INGRESO = "INGRESO"
    EGRESO = "EGRESO"


class Movement(Base):
    __tablename__ = "movements"

    __table_args__ = (
        CheckConstraint("monto > 0", name="ck_movements_monto_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    tipo: Mapped[TipoMovimiento] = mapped_column(
        Enum(TipoMovimiento, name="tipo_movimiento", create_constraint=True),
        nullable=False,
    )

    monto: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False
    )

    categoria: Mapped[str] = mapped_column(String(100), nullable=False)

    nota: Mapped[str | None] = mapped_column(Text, nullable=True)

    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ───────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="movements")

    def __repr__(self) -> str:
        return (
            f"<Movement id={self.id} tipo={self.tipo.value} "
            f"monto={self.monto} categoria={self.categoria}>"
        )

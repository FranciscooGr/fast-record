"""
User ORM model.

NOTE — There is NO "saldo" / "balance" column anywhere.
The balance is ALWAYS computed dynamically by aggregating movements.
"""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _generate_public_id() -> str:
    """Generate an 8-char hex string from a UUID4."""
    return uuid.uuid4().hex[:8]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_id: Mapped[str | None] = mapped_column(
        String(8), unique=True, index=True, nullable=True, default=_generate_public_id
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    telefono: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    moneda_principal: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default="ARS"
    )

    # ── Relationships ───────────────────────────────────────────
    movements: Mapped[list["Movement"]] = relationship(
        "Movement", back_populates="user", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telefono={self.telefono}>"

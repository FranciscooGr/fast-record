"""
User ORM model.

NOTE — There is NO "saldo" / "balance" column anywhere.
The balance is ALWAYS computed dynamically by aggregating movements.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
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

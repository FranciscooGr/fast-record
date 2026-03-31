---
name: database-schema-design
description: Use when designing PostgreSQL tables, writing SQLAlchemy models, creating Alembic migrations, or writing aggregate queries. CRITICAL: saldo must never be a persisted column — always calculated dynamically.
---

# Database Schema Design — PostgreSQL + SQLAlchemy

## Use this skill when
- Creando nuevos modelos SQLAlchemy en `./backend/app/models/`
- Escribiendo migraciones Alembic en `./backend/app/db/migrations/`
- Diseñando relaciones entre tablas
- Escribiendo queries con agregaciones (saldo, totales, resúmenes)
- Agregando índices para optimizar performance

## ⚠️ REGLA INVIOLABLE — Saldo siempre calculado
```python
# ❌ ABSOLUTAMENTE PROHIBIDO — jamás hacer esto
class Cuenta(Base):
    saldo = Column(Numeric)        # PROHIBIDO
    balance = Column(Numeric)      # PROHIBIDO
    total = Column(Numeric)        # PROHIBIDO si es derivado de transacciones

# ✅ CORRECTO — el saldo se calcula en query
from sqlalchemy import select, case, func

async def calcular_saldo(db: AsyncSession, cuenta_id: int) -> float:
    result = await db.execute(
        select(
            func.sum(
                case(
                    (Transaccion.tipo == "ingreso", Transaccion.monto),
                    else_=-Transaccion.monto
                )
            ).label("saldo")
        ).where(Transaccion.cuenta_id == cuenta_id)
    )
    return result.scalar() or 0.0
```

## Modelos SQLAlchemy — Pattern Base
```python
# models/base.py
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, func

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

## Modelo de Transacciones
```python
# models/transaccion.py
from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, Enum
from app.db.base import Base, TimestampMixin
import enum

class TipoTransaccion(enum.Enum):
    ingreso = "ingreso"
    gasto = "gasto"

class Transaccion(Base, TimestampMixin):
    __tablename__ = "transacciones"

    id = Column(Integer, primary_key=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas.id"), nullable=False)
    monto = Column(Numeric(12, 2), nullable=False)
    tipo = Column(Enum(TipoTransaccion), nullable=False)
    categoria = Column(String(100))           # asignada por LLM
    descripcion = Column(String(500))
    proveedor_llm = Column(String(50))        # gemini | groq | fallback_otros
    # ⚠️ NO hay columna saldo aquí
```

## Migraciones Alembic — Pattern
```python
# db/migrations/versions/001_create_transacciones.py
def upgrade():
    op.create_table(
        "transacciones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cuenta_id", sa.Integer(), sa.ForeignKey("cuentas.id")),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("categoria", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    # Índices para queries frecuentes del dashboard
    op.create_index("ix_transacciones_cuenta_id", "transacciones", ["cuenta_id"])
    op.create_index("ix_transacciones_created_at", "transacciones", ["created_at"])

def downgrade():
    op.drop_index("ix_transacciones_created_at")
    op.drop_index("ix_transacciones_cuenta_id")
    op.drop_table("transacciones")
```

## Queries del Dashboard — Agregaciones
```sql
-- Saldo actual
SELECT SUM(CASE WHEN tipo = 'ingreso' THEN monto ELSE -monto END) AS saldo
FROM transacciones WHERE cuenta_id = :id;

-- Gastos por categoría (para Chart.js)
SELECT categoria, SUM(monto) as total
FROM transacciones
WHERE tipo = 'gasto' AND cuenta_id = :id
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY categoria ORDER BY total DESC;

-- Evolución del saldo en el tiempo
SELECT DATE(created_at) as fecha,
       SUM(SUM(CASE WHEN tipo='ingreso' THEN monto ELSE -monto END))
       OVER (ORDER BY DATE(created_at)) AS saldo_acumulado
FROM transacciones WHERE cuenta_id = :id
GROUP BY DATE(created_at);
```

## Checklist antes de cada migración
- [ ] ¿La migración tiene `downgrade()`?
- [ ] ¿Hay índices para las columnas que se filtran frecuentemente?
- [ ] ¿Se está intentando agregar una columna de saldo? → RECHAZAR
- [ ] ¿Los tipos numéricos usan `Numeric(12,2)` y no `Float`?

## Do not
- No persistir valores derivados de suma de transacciones
- No usar `Float` para montos — siempre `Numeric(12, 2)`
- No olvidar el `downgrade()` en migraciones
- No crear índices en columnas que raramente se filtran

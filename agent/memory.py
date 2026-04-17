# agent/memory.py — Memoria de conversaciones con SQLite
# Generado por AgentKit para Conexión Vital

"""
Sistema de memoria de Vita. Guarda el historial de conversaciones
por número de teléfono usando SQLite (local) o PostgreSQL (producción).
"""

import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, select, Integer, delete
from dotenv import load_dotenv

load_dotenv()

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")

# Si es PostgreSQL en producción, ajustar el esquema de URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Mensaje(Base):
    """Modelo de mensaje en la base de datos."""
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" o "assistant"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Etiqueta(Base):
    """Etiqueta CRM asignada a un contacto."""
    __tablename__ = "etiquetas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    etiqueta: Mapped[str] = mapped_column(String(50))   # ej: "nuevo_lead", "interesado"
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def inicializar_db():
    """Crea las tablas si no existen."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def guardar_mensaje(telefono: str, role: str, content: str):
    """Guarda un mensaje en el historial de conversación."""
    async with async_session() as session:
        mensaje = Mensaje(
            telefono=telefono,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        session.add(mensaje)
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 20) -> list[dict]:
    """
    Recupera los últimos N mensajes de una conversación.

    Args:
        telefono: Número de teléfono del cliente
        limite: Máximo de mensajes a recuperar (default: 20)

    Returns:
        Lista de diccionarios con role y content, en orden cronológico
    """
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        result = await session.execute(query)
        mensajes = result.scalars().all()

        # Invertir para orden cronológico
        mensajes.reverse()

        return [
            {"role": msg.role, "content": msg.content}
            for msg in mensajes
        ]


async def limpiar_historial(telefono: str):
    """Borra todo el historial de una conversación."""
    async with async_session() as session:
        await session.execute(delete(Mensaje).where(Mensaje.telefono == telefono))
        await session.commit()


# ─── Etiquetas CRM ─────────────────────────────────────────────────────────────

ETIQUETAS_VALIDAS = {
    "nuevo_lead":       "🔥 Nuevo lead",
    "interesado":       "💬 Interesado",
    "cita_agendada":    "📅 Cita agendada",
    "pendiente":        "❗ Pendiente",
    "otra_ciudad":      "🌎 Otra ciudad",
    "posible_socia":    "💼 Posible socia",
}


async def asignar_etiqueta(telefono: str, etiqueta: str):
    """
    Asigna o actualiza la etiqueta CRM de un contacto.
    Solo se permite una etiqueta activa por contacto a la vez.
    """
    if etiqueta not in ETIQUETAS_VALIDAS:
        return
    async with async_session() as session:
        # Eliminar etiqueta anterior si existe
        await session.execute(delete(Etiqueta).where(Etiqueta.telefono == telefono))
        session.add(Etiqueta(
            telefono=telefono,
            etiqueta=etiqueta,
            actualizado=datetime.utcnow()
        ))
        await session.commit()


async def obtener_etiqueta(telefono: str) -> str | None:
    """Retorna la etiqueta CRM actual del contacto, o None si no tiene."""
    async with async_session() as session:
        result = await session.execute(
            select(Etiqueta).where(Etiqueta.telefono == telefono)
        )
        etiqueta = result.scalars().first()
        return etiqueta.etiqueta if etiqueta else None


async def listar_contactos_por_etiqueta(etiqueta: str) -> list[str]:
    """Retorna todos los teléfonos con una etiqueta específica."""
    async with async_session() as session:
        result = await session.execute(
            select(Etiqueta).where(Etiqueta.etiqueta == etiqueta)
        )
        return [e.telefono for e in result.scalars().all()]

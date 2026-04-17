# agent/tools.py — Herramientas de Vita para Conexión Vital
# Generado por AgentKit

"""
Herramientas específicas de Conexión Vital.
Cubren los 5 casos de uso: FAQ, citas, leads, pedidos y soporte post-venta.
"""

import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger("agentkit")


# ─── Utilidades base ───────────────────────────────────────────────────────────

def cargar_info_negocio() -> dict:
    """Carga la información del negocio desde business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> str:
    """Retorna el horario de atención del negocio."""
    info = cargar_info_negocio()
    return info.get("negocio", {}).get("horario", "Lunes a Domingo de 8am a 10pm")


# ─── FAQ — Búsqueda en archivos de knowledge ──────────────────────────────────

def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca información relevante en los archivos de /knowledge.
    Retorna el contenido más relevante encontrado.
    """
    resultados = []
    knowledge_dir = "knowledge"

    if not os.path.exists(knowledge_dir):
        return "No hay archivos de conocimiento disponibles."

    for archivo in os.listdir(knowledge_dir):
        ruta = os.path.join(knowledge_dir, archivo)
        if archivo.startswith(".") or not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
                if consulta.lower() in contenido.lower():
                    resultados.append(f"[{archivo}]: {contenido[:500]}")
        except (UnicodeDecodeError, IOError):
            continue

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontré información específica sobre eso en mis archivos."


# ─── CITAS — Agendamiento de escaneo de bienestar ─────────────────────────────

# Almacenamiento en memoria simple (en producción usar base de datos)
_citas: dict[str, dict] = {}


def registrar_cita(telefono: str, nombre: str, fecha: str, hora: str, ciudad: str) -> dict:
    """
    Registra una cita para escaneo de bienestar.

    Args:
        telefono: Número del cliente
        nombre: Nombre del cliente
        fecha: Fecha de la cita (ej: "2026-04-20")
        hora: Hora de la cita (ej: "10:00am")
        ciudad: Ciudad donde se realizará el escaneo

    Returns:
        Diccionario con confirmación de la cita
    """
    cita_id = f"CV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    _citas[cita_id] = {
        "id": cita_id,
        "telefono": telefono,
        "nombre": nombre,
        "fecha": fecha,
        "hora": hora,
        "ciudad": ciudad,
        "estado": "confirmada",
        "creada": datetime.now().isoformat()
    }
    logger.info(f"Cita registrada: {cita_id} para {nombre} el {fecha} a las {hora}")
    return _citas[cita_id]


def consultar_cita(telefono: str) -> dict | None:
    """Busca la cita activa de un cliente por su número de teléfono."""
    for cita in _citas.values():
        if cita["telefono"] == telefono and cita["estado"] == "confirmada":
            return cita
    return None


# ─── LEADS — Calificación y seguimiento ───────────────────────────────────────

_leads: dict[str, dict] = {}


def registrar_lead(telefono: str, nombre: str, interes: str, ciudad: str) -> dict:
    """
    Registra un lead interesado en Conexión Vital.

    Args:
        telefono: Número del prospecto
        nombre: Nombre del prospecto
        interes: "cliente" o "distribuidor"
        ciudad: Ciudad del prospecto

    Returns:
        Diccionario con datos del lead registrado
    """
    _leads[telefono] = {
        "telefono": telefono,
        "nombre": nombre,
        "interes": interes,  # "cliente" o "distribuidor"
        "ciudad": ciudad,
        "estado": "nuevo",
        "fecha_registro": datetime.now().isoformat()
    }
    logger.info(f"Lead registrado: {nombre} ({telefono}) — Interés: {interes} — Ciudad: {ciudad}")
    return _leads[telefono]


def obtener_agente_por_ciudad(ciudad: str) -> dict | None:
    """
    Retorna el agente/vendedor asignado para una ciudad.

    Args:
        ciudad: Ciudad del cliente (ej: "Querétaro", "Puebla", "CDMX", etc.)

    Returns:
        Diccionario con datos del agente o None si no hay cobertura
    """
    ciudad_lower = ciudad.lower().strip()

    # Mapeo de ciudades a agentes
    if any(c in ciudad_lower for c in ["querétaro", "queretaro", "qro"]):
        return {"nombre": "Gisela Sevilla", "telefono": "5544036244", "ciudad": "Querétaro"}

    elif any(c in ciudad_lower for c in ["puebla", "pue"]):
        # Asignación alternada entre Sitka y Perla
        import random
        agentes_puebla = [
            {"nombre": "Sitka Lopez", "telefono": "2221139421", "ciudad": "Puebla"},
            {"nombre": "Perla Alejo", "telefono": "2222098244", "ciudad": "Puebla"},
        ]
        return random.choice(agentes_puebla)

    elif any(c in ciudad_lower for c in ["tlaxcala", "tlax"]):
        return {"nombre": "Conexión Vital", "telefono": "2212824878", "ciudad": "Tlaxcala"}

    elif any(c in ciudad_lower for c in ["estado de méxico", "edomex", "edo. de méx", "edo mex", "ecatepec",
                                          "naucalpan", "tlalnepantla", "nezahualcóyotl", "cdmx",
                                          "ciudad de méxico", "ciudad de mexico", "df", "d.f.",
                                          "benito juárez", "coyoacán", "iztapalapa", "miguel hidalgo"]):
        import random
        agentes_metro = [
            {"nombre": "Juana Herrero", "telefono": "5527564840", "ciudad": "CDMX/Edomex"},
            {"nombre": "Nidia González", "telefono": "5528565101", "ciudad": "CDMX/Edomex"},
        ]
        return random.choice(agentes_metro)

    return None  # Ciudad sin cobertura presencial


# ─── PEDIDOS — Toma de pedidos de suplementos ─────────────────────────────────

_pedidos: dict[str, list] = {}


def agregar_al_carrito(telefono: str, producto: str, cantidad: int = 1) -> dict:
    """
    Agrega un producto al carrito del cliente.

    Args:
        telefono: Número del cliente
        producto: Nombre del producto/suplemento
        cantidad: Cantidad a agregar

    Returns:
        Estado actual del carrito
    """
    if telefono not in _pedidos:
        _pedidos[telefono] = []

    # Verificar si ya está en el carrito
    for item in _pedidos[telefono]:
        if item["producto"].lower() == producto.lower():
            item["cantidad"] += cantidad
            return {"carrito": _pedidos[telefono], "total_items": len(_pedidos[telefono])}

    _pedidos[telefono].append({
        "producto": producto,
        "cantidad": cantidad
    })
    logger.info(f"Carrito {telefono}: +{cantidad}x {producto}")
    return {"carrito": _pedidos[telefono], "total_items": len(_pedidos[telefono])}


def ver_carrito(telefono: str) -> list:
    """Retorna el carrito actual del cliente."""
    return _pedidos.get(telefono, [])


def confirmar_pedido(telefono: str, nombre: str, direccion: str) -> dict:
    """
    Confirma y registra el pedido del cliente.

    Args:
        telefono: Número del cliente
        nombre: Nombre del cliente
        direccion: Dirección de entrega

    Returns:
        Confirmación del pedido con número de orden
    """
    carrito = _pedidos.get(telefono, [])
    if not carrito:
        return {"error": "El carrito está vacío"}

    pedido_id = f"PED-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    pedido = {
        "id": pedido_id,
        "telefono": telefono,
        "nombre": nombre,
        "direccion": direccion,
        "productos": carrito,
        "estado": "recibido",
        "fecha": datetime.now().isoformat()
    }
    # Limpiar carrito después de confirmar
    _pedidos[telefono] = []
    logger.info(f"Pedido confirmado: {pedido_id} — {nombre} ({telefono})")
    return pedido


# ─── SOPORTE POST-VENTA ────────────────────────────────────────────────────────

_tickets: dict[str, dict] = {}


def crear_ticket_soporte(telefono: str, nombre: str, problema: str) -> dict:
    """
    Crea un ticket de soporte post-venta.

    Args:
        telefono: Número del cliente
        nombre: Nombre del cliente
        problema: Descripción del problema o consulta

    Returns:
        Diccionario con datos del ticket creado
    """
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    _tickets[ticket_id] = {
        "id": ticket_id,
        "telefono": telefono,
        "nombre": nombre,
        "problema": problema,
        "estado": "abierto",
        "fecha_apertura": datetime.now().isoformat()
    }
    logger.info(f"Ticket creado: {ticket_id} — {nombre}: {problema[:50]}")
    return _tickets[ticket_id]


def consultar_ticket(ticket_id: str) -> dict | None:
    """Consulta el estado de un ticket de soporte."""
    return _tickets.get(ticket_id)

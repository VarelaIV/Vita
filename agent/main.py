# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit para Conexión Vital

"""
Servidor principal del agente Vita de Conexión Vital.
Recibe mensajes de WhatsApp via Whapi.cloud, los procesa con Claude
y responde de forma cálida y personalizada.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import (
    inicializar_db, guardar_mensaje, obtener_historial,
    asignar_etiqueta, obtener_etiqueta
)
from agent.providers import obtener_proveedor

load_dotenv()

# Configuración de logging según entorno
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

# Proveedor de WhatsApp (Whapi.cloud)
proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar el servidor."""
    await inicializar_db()
    logger.info("Base de datos inicializada")
    logger.info(f"Agente Vita lista en puerto {PORT}")
    logger.info(f"Proveedor de WhatsApp: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="Vita — Asistente de Bienestar de Conexión Vital",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    """Endpoint de salud para Railway/monitoreo."""
    return {"status": "ok", "agente": "Vita", "negocio": "Conexión Vital"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    """Verificación GET del webhook."""
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


async def procesar_mensajes(request: Request):
    """Lógica compartida para procesar mensajes de WhatsApp."""
    mensajes = await proveedor.parsear_webhook(request)

    for msg in mensajes:
        if msg.es_propio or not msg.texto:
            continue

        logger.info(f"Mensaje de {msg.telefono}: {msg.texto}")

        historial = await obtener_historial(msg.telefono)

        etiqueta_actual = await obtener_etiqueta(msg.telefono)
        if not etiqueta_actual:
            await asignar_etiqueta(msg.telefono, "nuevo_lead")

        respuesta = await generar_respuesta(msg.texto, historial)

        texto_lower = msg.texto.lower()
        respuesta_lower = respuesta.lower()

        if any(p in texto_lower for p in ["precio", "costo", "cuánto", "cuanto", "información", "info", "qué es", "que es"]):
            await asignar_etiqueta(msg.telefono, "interesado")
        elif any(p in texto_lower for p in ["sí quiero", "si quiero", "me interesa", "cuándo", "cuando", "agendar", "cita"]):
            await asignar_etiqueta(msg.telefono, "interesado")
        elif any(p in respuesta_lower for p in ["cita agendada", "confirmada", "quedamos el"]):
            await asignar_etiqueta(msg.telefono, "cita_agendada")
        elif any(p in respuesta_lower for p in ["otra ciudad", "no tenemos escaneo presencial", "proceso de expansión"]):
            await asignar_etiqueta(msg.telefono, "otra_ciudad")
        elif any(p in texto_lower for p in ["negocio", "ingresos", "vender", "socia", "distribuidora"]):
            await asignar_etiqueta(msg.telefono, "posible_socia")

        etiqueta_nueva = await obtener_etiqueta(msg.telefono)
        logger.info(f"Etiqueta {msg.telefono}: {etiqueta_nueva}")

        await guardar_mensaje(msg.telefono, "user", msg.texto)
        await guardar_mensaje(msg.telefono, "assistant", respuesta)

        await proveedor.enviar_mensaje(msg.telefono, respuesta)
        logger.info(f"Vita respondió a {msg.telefono}: {respuesta[:80]}...")

    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """Recibe mensajes de WhatsApp via Whapi.cloud (ruta principal)."""
    try:
        return await procesar_mensajes(request)
    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/messages")
async def webhook_messages_handler(request: Request):
    """Ruta alternativa que Whapi.cloud usa para eventos de mensajes."""
    try:
        return await procesar_mensajes(request)
    except Exception as e:
        logger.error(f"Error en webhook/messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

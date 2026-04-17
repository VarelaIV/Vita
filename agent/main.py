# agent/main.py — Servidor FastAPI + Webhook de WhatsApp
# Generado por AgentKit para Conexión Vital

import os
import json
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
from agent.providers.base import MensajeEntrante

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("agentkit")

proveedor = obtener_proveedor()
PORT = int(os.getenv("PORT", 8000))


@asynccontextmanager
async def lifespan(app: FastAPI):
    await inicializar_db()
    logger.info(f"Agente Vita lista en puerto {PORT}")
    logger.info(f"Proveedor: {proveedor.__class__.__name__}")
    yield


app = FastAPI(
    title="Vita — Asistente de Bienestar de Conexión Vital",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def health_check():
    return {"status": "ok", "agente": "Vita", "negocio": "Conexión Vital"}


@app.get("/webhook")
async def webhook_verificacion(request: Request):
    resultado = await proveedor.validar_webhook(request)
    if resultado is not None:
        return PlainTextResponse(str(resultado))
    return {"status": "ok"}


def parsear_body_whapi(body: dict) -> list[MensajeEntrante]:
    """Parsea el payload de Whapi.cloud y retorna mensajes normalizados."""
    mensajes = []
    for msg in body.get("messages", []):
        texto = ""
        # Texto plano
        if isinstance(msg.get("text"), dict):
            texto = msg["text"].get("body", "")
        elif isinstance(msg.get("text"), str):
            texto = msg["text"]

        telefono = msg.get("chat_id") or msg.get("from", "")
        es_propio = msg.get("from_me", False)
        mensaje_id = msg.get("id", "")

        mensajes.append(MensajeEntrante(
            telefono=telefono,
            texto=texto,
            mensaje_id=mensaje_id,
            es_propio=es_propio,
        ))
    return mensajes


async def procesar_body(body: dict):
    """Procesa el payload ya parseado y genera respuesta de Vita."""
    logger.info(f"[DEBUG] Payload: {json.dumps(body)[:400]}")

    mensajes = parsear_body_whapi(body)
    logger.info(f"[DEBUG] {len(mensajes)} mensaje(s) parseado(s)")

    for msg in mensajes:
        logger.info(f"[DEBUG] telefono={msg.telefono} texto={repr(msg.texto)} es_propio={msg.es_propio}")

        if msg.es_propio or not msg.texto.strip():
            logger.info("[DEBUG] Mensaje ignorado (propio o vacío)")
            continue

        historial = await obtener_historial(msg.telefono)

        if not await obtener_etiqueta(msg.telefono):
            await asignar_etiqueta(msg.telefono, "nuevo_lead")

        respuesta = await generar_respuesta(msg.texto, historial)
        logger.info(f"[DEBUG] Respuesta generada: {respuesta[:80]}")

        # Actualizar etiqueta según contexto
        t = msg.texto.lower()
        r = respuesta.lower()
        if any(p in t for p in ["precio", "costo", "cuánto", "cuanto", "info", "qué es", "que es"]):
            await asignar_etiqueta(msg.telefono, "interesado")
        elif any(p in t for p in ["quiero", "me interesa", "agendar", "cita", "cuando", "cuándo"]):
            await asignar_etiqueta(msg.telefono, "interesado")
        elif any(p in r for p in ["cita agendada", "confirmada"]):
            await asignar_etiqueta(msg.telefono, "cita_agendada")
        elif any(p in r for p in ["no tenemos escaneo presencial", "proceso de expansión"]):
            await asignar_etiqueta(msg.telefono, "otra_ciudad")
        elif any(p in t for p in ["negocio", "ingresos", "vender", "socia", "distribuidora"]):
            await asignar_etiqueta(msg.telefono, "posible_socia")

        await guardar_mensaje(msg.telefono, "user", msg.texto)
        await guardar_mensaje(msg.telefono, "assistant", respuesta)

        exito = await proveedor.enviar_mensaje(msg.telefono, respuesta)
        logger.info(f"[DEBUG] enviar_mensaje → exito={exito}")

    return {"status": "ok"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        body = await request.json()
        return await procesar_body(body)
    except Exception as e:
        logger.error(f"Error en /webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/messages")
async def webhook_messages_handler(request: Request):
    try:
        body = await request.json()
        return await procesar_body(body)
    except Exception as e:
        logger.error(f"Error en /webhook/messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

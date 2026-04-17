# tests/test_local.py — Simulador de chat con Vita en terminal
# Generado por AgentKit para Conexión Vital

"""
Prueba a Vita sin necesitar WhatsApp.
Simula una conversación en la terminal como si fueras un cliente de Conexión Vital.
"""

import asyncio
import sys
import os

# Forzar UTF-8 en la terminal de Windows para que los emojis se muestren correctamente
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.memory import inicializar_db, guardar_mensaje, obtener_historial, limpiar_historial

TELEFONO_TEST = "test-local-001"


async def main():
    """Loop principal del chat de prueba con Vita."""
    await inicializar_db()

    print()
    print("=" * 60)
    print("   Conexión Vital — Test Local de Vita")
    print("=" * 60)
    print()
    print("  Escribe mensajes como si fueras un cliente.")
    print("  Comandos especiales:")
    print("    'limpiar'  — borra el historial (nueva conversación)")
    print("    'salir'    — termina el test")
    print()
    print("-" * 60)
    print()

    while True:
        try:
            mensaje = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nTest finalizado. ¡Hasta pronto!")
            break

        if not mensaje:
            continue

        if mensaje.lower() == "salir":
            print("\n¡Hasta pronto! 💛")
            break

        if mensaje.lower() == "limpiar":
            await limpiar_historial(TELEFONO_TEST)
            print("[Historial borrado — nueva conversación]\n")
            continue

        # Obtener historial ANTES de guardar (brain.py agrega el mensaje actual)
        historial = await obtener_historial(TELEFONO_TEST)

        # Generar respuesta de Vita
        print("\nVita: ", end="", flush=True)
        respuesta = await generar_respuesta(mensaje, historial)
        print(respuesta)
        print()

        # Guardar mensaje del usuario y respuesta de Vita
        await guardar_mensaje(TELEFONO_TEST, "user", mensaje)
        await guardar_mensaje(TELEFONO_TEST, "assistant", respuesta)


if __name__ == "__main__":
    asyncio.run(main())

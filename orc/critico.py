import base64
import json
import os
import re
from pathlib import Path

from openai import OpenAI

_PROMPT_VISION = """\
Evalúa si estas imágenes de animación corresponden a la descripción dada.
Responde SOLO con JSON válido, sin texto antes ni después:
{"score": <0-10>, "aprobado": <true/false>, "feedback": "<qué falta o mejorar>"}

Criterios: 0-3 sin relación o errores graves, 4-6 parcial, 7-8 reconocible, 9-10 excelente.
aprobado=true si score>=7."""

_PROMPT_CODIGO = """\
Analiza este código Python de una escena generativa y evalúa si implementa correctamente la descripción.
Busca: imports correctos, métodos requeridos (configurar/actualizar/dibujar), lógica visual coherente,
errores probables en ejecución.
Responde SOLO con JSON válido, sin texto antes ni después:
{"score": <0-10>, "aprobado": <true/false>, "feedback": "<qué falta o corregir>"}

aprobado=true si score>=7. Sin texto adicional."""


def _cliente() -> OpenAI:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    return OpenAI(base_url=f"{host}/v1", api_key="ollama")


def _parsear_respuesta(texto: str) -> dict:
    if "```" in texto:
        texto = re.sub(r"```[a-z]*\n?", "", texto).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r'"?score"?\s*[:=]\s*(\d+)', texto)
        score = int(match.group(1)) if match else 5
        return {"score": score, "aprobado": score >= 7, "feedback": texto[:400]}


def criticar(descripcion: str, codigo: str, frames: list[Path]) -> dict:
    cliente = _cliente()
    modelo = os.environ.get("ORC_MODELO_CRITICO", "mistral:latest")

    # Intentar con visión primero
    contenido_vision: list[dict] = []
    etiquetas = ["inicio (t=0s)", "mitad (t=1.5s)", "final (t=3s)"]
    for i, ruta in enumerate(frames):
        datos = base64.standard_b64encode(ruta.read_bytes()).decode()
        contenido_vision.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{datos}"},
        })
        contenido_vision.append({"type": "text", "text": f"[{etiquetas[i]}]"})
    contenido_vision.append({
        "type": "text",
        "text": f"{_PROMPT_VISION}\n\nDescripción: {descripcion}",
    })

    try:
        respuesta = cliente.chat.completions.create(
            model=modelo,
            messages=[{"role": "user", "content": contenido_vision}],
            temperature=0.1,
        )
        return _parsear_respuesta(respuesta.choices[0].message.content.strip())
    except Exception:
        pass

    # Fallback: crítica de código sin visión
    print(f"  (modelo sin visión — analizando código)")
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[{
            "role": "user",
            "content": f"{_PROMPT_CODIGO}\n\nDescripción: {descripcion}\n\nCódigo:\n```python\n{codigo}\n```",
        }],
        temperature=0.1,
    )
    return _parsear_respuesta(respuesta.choices[0].message.content.strip())

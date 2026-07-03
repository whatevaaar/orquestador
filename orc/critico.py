import base64
import json
import os
import re
from pathlib import Path

from openai import OpenAI

_SISTEMA_VISION = """\
Eres un crítico de arte especializado en arte generativo y video art.
Observas tres momentos de una animación: el arranque, el punto medio y el final.

Tu misión es evaluar si esta pieza tiene mérito como obra visual.
NO evalúes si el código es correcto — eso ya fue validado por el motor.

Evalúa como artista y curador:

ATMÓSFERA   ¿Los colores y la luz construyen el estado de ánimo correcto?
            ¿La paleta es coherente? ¿Hay profundidad y ambiente?

COMPOSICIÓN ¿Los elementos están distribuidos con intención?
            ¿Hay un punto focal? ¿El espacio respira o está saturado?

MOVIMIENTO  ¿La animación tiene vida? ¿El cambio entre los tres momentos
            sugiere fluidez y ritmo, o es mecánico y sin alma?

RESONANCIA  ¿La pieza captura la esencia de la descripción, aunque sea
            de forma abstracta o poética? ¿Te produce la sensación correcta?

SCORE:
  9-10  Obra con identidad propia, atmósfera lograda, te detiene a mirar
  7-8   La intención es clara, ejecución convincente, detalles menores que mejorar
  5-6   El concepto está pero la ejecución es débil o incompleta
  3-4   Mínima relación con la descripción o problemas visuales graves
  0-2   Sin coherencia visual, pantalla vacía, negra o rota

Responde SOLO con JSON válido, sin texto antes ni después:
{"score": <0-10>, "aprobado": <true si score>=7>, "feedback": "<tu lectura artística — qué funciona, qué falta, qué cambiar para que la pieza cobre vida>"}"""

_SISTEMA_TEXTO = """\
Eres un crítico de arte que lee código generativo como si leyera un guión de animación.
Basándote en el código Python de esta escena, imagina qué apariencia y qué sensación visual tendría.

Evalúa el potencial artístico, no la corrección técnica:
- ¿Qué paleta de colores implica el código? ¿Es coherente con la descripción?
- ¿Cómo se distribuyen los elementos en el espacio? ¿Hay composición o caos?
- ¿Qué tipo de movimiento genera la matemática? ¿Tiene ritmo?
- ¿La pieza capturaría la esencia de la descripción original?

Responde SOLO con JSON válido, sin texto antes ni después:
{"score": <0-10>, "aprobado": <true si score>=7>, "feedback": "<lectura artística del potencial visual — sin hablar de código>"}"""


def _cliente() -> OpenAI:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    return OpenAI(base_url=f"{host}/v1", api_key="ollama")


def _parsear(texto: str) -> dict:
    if "```" in texto:
        texto = re.sub(r"```[a-z]*\n?", "", texto).strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        match = re.search(r'"?score"?\s*[:=]\s*(\d+)', texto)
        score = int(match.group(1)) if match else 5
        return {"score": score, "aprobado": score >= 7, "feedback": texto[:500]}


def criticar(descripcion: str, codigo: str, frames: list[Path]) -> dict:
    cliente = _cliente()
    modelo = os.environ.get("ORC_MODELO_CRITICO", "mistral:latest")

    etiquetas = ["Arranque (t=0s)", "Punto medio (t=1.5s)", "Final (t=3s)"]
    contenido: list[dict] = []
    for i, ruta in enumerate(frames):
        datos = base64.standard_b64encode(ruta.read_bytes()).decode()
        contenido.append({"type": "text", "text": etiquetas[i]})
        contenido.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{datos}"},
        })
    contenido.append({"type": "text", "text": f"Descripción: {descripcion}"})

    try:
        respuesta = cliente.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": _SISTEMA_VISION},
                {"role": "user", "content": contenido},
            ],
            temperature=0.2,
        )
        return _parsear(respuesta.choices[0].message.content.strip())
    except Exception:
        pass

    # Fallback artístico sin visión — critica el código como guión
    print("  (modelo sin vision — critica artistica del codigo)")
    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[{
            "role": "user",
            "content": f"{_SISTEMA_TEXTO}\n\nDescripción: {descripcion}\n\nCódigo:\n```python\n{codigo}\n```",
        }],
        temperature=0.2,
    )
    return _parsear(respuesta.choices[0].message.content.strip())

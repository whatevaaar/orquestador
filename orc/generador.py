import os
import re
from pathlib import Path

from openai import OpenAI

_EJEMPLO_PATH = Path(__file__).parent.parent.parent / "motor" / "ejemplos" / "mar_con_pato.py"

_ejemplo_texto: str | None = None


def _obtener_ejemplo() -> str:
    global _ejemplo_texto
    if _ejemplo_texto is None:
        if _EJEMPLO_PATH.exists():
            _ejemplo_texto = _EJEMPLO_PATH.read_text(encoding="utf-8")
        else:
            _ejemplo_texto = "# ejemplo no disponible"
    return _ejemplo_texto


def _cliente() -> OpenAI:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    return OpenAI(base_url=f"{host}/v1", api_key="ollama")


def generar_escena(descripcion: str, feedback: str | None = None) -> str:
    sistema = f"""\
Eres un generador de escenas visuales generativas para pygame. Debes generar un archivo Python completo.

## REGLA MAS IMPORTANTE
La clase SIEMPRE hereda de `Escena` (importada de motor). NUNCA uses otro nombre como base.
Correcto:   class MiClase(Escena):
INCORRECTO: class MiClase(MiEscena):   <- MiEscena NO existe, causara NameError

## IMPORTS OBLIGATORIOS (exactamente estos, nada mas)
```python
import math
import pygame
from motor import Contexto, Escena
```

## METODOS OBLIGATORIOS

```python
class NombreEscena(Escena):
    params = {{}}  # parametros con defaults numericos

    def configurar(self) -> None:
        # SOLO leer config y crear Surfaces. NO usar self.t aqui.
        # self.t NO existe todavia. Inicializalo a 0:
        self.t = 0.0
        self.ancho = self.config.ancho
        self.alto = self.config.alto
        # leer params: siempre convertir al tipo correcto
        self.n = int(self.config.params.get("n", 50))      # int() para conteos
        self.vel = float(self.config.params.get("vel", 1.0))  # float() para velocidades

    def actualizar(self, ctx: Contexto) -> None:
        # Aqui se actualiza self.t cada frame
        self.t = ctx.segundos_transcurridos

    def dibujar(self, surface: pygame.Surface) -> None:
        surface.fill((10, 10, 20))
        # dibujar con pygame.draw.*
```

## ERRORES COMUNES A EVITAR
- NO usar self.t en configurar() — inicializalo con self.t = 0.0 en configurar()
- NO usar range(float) — siempre int(): range(int(self.n * factor))
- NO subclasificar MiEscena — la base es Escena
- NO importar nada fuera de pygame, math, motor

## EJEMPLO DE REFERENCIA
```python
{_obtener_ejemplo()}
```

Responde UNICAMENTE con el bloque de codigo. Sin texto antes ni despues:
```python
# tu escena aqui
```"""

    contenido = f"Descripcion: {descripcion}"
    if feedback:
        contenido += f"\n\nFeedback del intento anterior (DEBES corregir estos errores):\n{feedback}"

    cliente = _cliente()
    modelo = os.environ.get("ORC_MODELO_GEN", "mistral:latest")

    respuesta = cliente.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": sistema},
            {"role": "user", "content": contenido},
        ],
        temperature=0.6,
    )

    texto = respuesta.choices[0].message.content.strip()
    match = re.search(r"```python\n(.*?)```", texto, re.DOTALL)
    if match:
        return match.group(1).strip()
    return texto

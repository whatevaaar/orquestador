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

## IMPORTS OBLIGATORIOS (solo estos)
```python
import math
import random
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

## ATRIBUTOS DE Contexto (EXACTOS — no existen otros)
ctx.segundos_transcurridos  # float — tiempo total
ctx.numero_frame            # int — frame actual
ctx.fps_objetivo            # int
ctx.ancho                   # int
ctx.alto                    # int
INCORRECTO: ctx.t, ctx.time, ctx.tiempo — NO EXISTEN, causaran AttributeError

## ERRORES COMUNES A EVITAR
- NO usar ctx.t ni ctx.time — el atributo correcto es ctx.segundos_transcurridos
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
    codigo = match.group(1).strip() if match else texto
    return _sanitizar(codigo)


# Correcciones automáticas de errores recurrentes de modelos pequeños
_SUSTITUCIONES = [
    # ctx.t / ctx.time -> ctx.segundos_transcurridos
    (re.compile(r'\bctx\.t\b'), 'ctx.segundos_transcurridos'),
    (re.compile(r'\bctx\.time\b'), 'ctx.segundos_transcurridos'),
    (re.compile(r'\bctx\.tiempo\b'), 'ctx.segundos_transcurridos'),
    # self.width / self.height -> self.config.ancho / self.config.alto
    (re.compile(r'\bself\.width\b'), 'self.config.ancho'),
    (re.compile(r'\bself\.height\b'), 'self.config.alto'),
    # math.random() no existe -> random.random()
    (re.compile(r'\bmath\.random\b'), 'random.random'),
    (re.compile(r'\bmath\.randint\b'), 'random.randint'),
    (re.compile(r'\bmath\.uniform\b'), 'random.uniform'),
]

_INIT_ANCHO_ALTO = """\
        self.ancho = self.config.ancho
        self.alto = self.config.alto
"""

# Atributos del sistema que nunca se inyectan
_ATTRS_SISTEMA = frozenset({
    'config', 'ancho', 'alto', 't', 'n', 'vel', 'velocidad',
    '__class__', '__dict__',
})


def _attrs_no_inicializados(codigo: str) -> set[str]:
    """Detecta self.<attr> usados en actualizar/dibujar pero no asignados en configurar."""
    m_conf = re.search(r'def configurar\(self\)[^:]*:(.*?)(?=\n    def |\Z)', codigo, re.DOTALL)
    conf_body = m_conf.group(1) if m_conf else ''
    asignados = set(re.findall(r'self\.(\w+)\s*=', conf_body))

    usados: set[str] = set()
    for metodo in ('actualizar', 'dibujar'):
        m = re.search(rf'def {metodo}\(self[^)]*\)[^:]*:(.*?)(?=\n    def |\Z)', codigo, re.DOTALL)
        if m:
            usados |= set(re.findall(r'self\.(\w+)', m.group(1)))

    return usados - asignados - _ATTRS_SISTEMA


def _valor_inicial(nombre: str) -> str:
    nombre_lower = nombre.lower()
    if any(nombre_lower.endswith(s) for s in ('x', 'y', 'z', 'vx', 'vy', 'vz')):
        return '0.0'
    if any(k in nombre_lower for k in ('vel', 'speed', 'angulo', 'angle', 'rad', 'pos', 'grav')):
        return '0.0'
    if any(k in nombre_lower for k in ('color', 'surf', 'img', 'font', 'lista', 'list', 'items')):
        return None  # no inyectar — podría ser un objeto complejo
    return '0.0'


def _sanitizar(codigo: str) -> str:
    for patron, reemplazo in _SUSTITUCIONES:
        codigo = patron.sub(reemplazo, codigo)

    # Asegurar import correcto de motor
    if 'class' in codigo and 'from motor import' not in codigo:
        codigo = 'from motor import Contexto, Escena\n' + codigo
    elif 'from motor import' in codigo and 'Escena' not in codigo.split('from motor import')[1].split('\n')[0]:
        # import de motor existe pero sin Escena
        codigo = re.sub(
            r'from motor import ([^\n]+)',
            lambda m: f'from motor import {m.group(1).rstrip()}, Escena'
            if 'Escena' not in m.group(1) else m.group(0),
            codigo,
        )

    # Corregir clase sin herencia o con base incorrecta
    # class Foo: -> class Foo(Escena):
    codigo = re.sub(r'class (\w+)\s*:', r'class \1(Escena):', codigo)
    # class Foo(object): -> class Foo(Escena):
    codigo = re.sub(r'class (\w+)\(object\)', r'class \1(Escena)', codigo)
    # class Foo(EscenaBase): -> class Foo(Escena):  (nombre incorrecto de base)
    codigo = re.sub(r'class (\w+)\((?!Escena\b)\w*[Ee]scena\w*\)', r'class \1(Escena)', codigo)

    # Inyectar import random si el código lo usa pero no lo importa
    if 'random.' in codigo and 'import random' not in codigo:
        codigo = 'import random\n' + codigo

    # Si usa self.ancho/self.alto pero no los inicializa en configurar(), inyectar al inicio
    if 'self.ancho' in codigo and 'self.ancho = self.config.ancho' not in codigo:
        codigo = re.sub(
            r'(def configurar\(self\)[^:]*:\n)',
            r'\1' + _INIT_ANCHO_ALTO,
            codigo,
        )

    # Inyectar inicializaciones para atributos usados en actualizar/dibujar pero no definidos
    faltantes = _attrs_no_inicializados(codigo)
    if faltantes:
        lineas_init = ''
        for attr in sorted(faltantes):
            val = _valor_inicial(attr)
            if val is not None:
                lineas_init += f'        self.{attr} = {val}\n'
        if lineas_init:
            codigo = re.sub(
                r'(def configurar\(self\)[^:]*:\n)',
                r'\1' + lineas_init,
                codigo,
            )

    return codigo

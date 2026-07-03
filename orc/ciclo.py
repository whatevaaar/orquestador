import sys
import tempfile
import time
from pathlib import Path

from .critico import criticar
from .generador import generar_escena
from .render_bridge import renderizar, renderizar_final


def _print(msg: str) -> None:
    print(msg, flush=True)


def ejecutar(descripcion: str, duracion: float = 10.0, max_iter: int = 4, umbral: int = 7) -> None:
    dir_base = Path(tempfile.gettempdir()) / f"orc_{int(time.time())}"

    mejor_escena: Path | None = None
    mejor_score = -1
    feedback: str | None = None

    for i in range(1, max_iter + 1):
        _print(f"\n[iter {i}/{max_iter}] Generando escena...")
        codigo = generar_escena(descripcion, feedback)

        dir_iter = dir_base / f"iter_{i}"
        dir_iter.mkdir(parents=True, exist_ok=True)

        ruta_escena = dir_iter / "escena_gen.py"
        ruta_escena.write_text(codigo, encoding="utf-8")

        _print(f"[iter {i}/{max_iter}] Renderizando (3s @ 540x960)...")
        try:
            frames = renderizar(ruta_escena, dir_iter / "frames")
        except RuntimeError as e:
            _print(f"[iter {i}/{max_iter}] Error al renderizar: {e}")
            feedback = f"El codigo genero un error al ejecutarse:\n{e}\nCorrige el error."
            continue

        _print(f"[iter {i}/{max_iter}] Evaluando con el critico...")
        try:
            evaluacion = criticar(descripcion, codigo, frames)
        except Exception as e:
            _print(f"[iter {i}/{max_iter}] Error en el critico: {e}")
            continue

        score = evaluacion.get("score", 0)
        fb = evaluacion.get("feedback", "")

        _print(f"[iter {i}/{max_iter}] Score: {score}/10 -- {fb}")

        if score > mejor_score:
            mejor_score = score
            mejor_escena = ruta_escena

        if score >= umbral:
            _print(f"\nAprobado (score {score}/10).")
            break

        feedback = fb
    else:
        if mejor_escena is None:
            _print("\nNo se pudo generar ninguna escena funcional.")
            return
        _print(f"\nMaximo de iteraciones alcanzado. Usando mejor score ({mejor_score}/10).")

    _print(f"\nRender final ({duracion}s) con efectos...")
    renderizar_final(mejor_escena, duracion)

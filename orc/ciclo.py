import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from .critico import criticar
from .generador import generar_escena
from .render_bridge import renderizar, renderizar_con_servidor, renderizar_video


def ejecutar(
    descripcion: str,
    duracion: float = 10.0,
    max_iter: int = 4,
    umbral: int = 7,
    on_evento: Callable[[dict], None] | None = None,
) -> None:
    def emitir(evento: dict) -> None:
        if on_evento:
            on_evento(evento)

    def log(mensaje: str) -> None:
        print(mensaje, flush=True)
        emitir({"type": "log", "mensaje": mensaje})

    dir_base = Path(tempfile.gettempdir()) / f"orc_{int(time.time())}"

    mejor_escena: Path | None = None
    mejor_score = -1
    feedback: str | None = None

    for i in range(1, max_iter + 1):
        log(f"[iter {i}/{max_iter}] Generando escena...")
        emitir({"type": "progreso", "iter": i, "max_iter": max_iter, "fase": "generando"})

        codigo = generar_escena(descripcion, feedback)

        dir_iter = dir_base / f"iter_{i}"
        dir_iter.mkdir(parents=True, exist_ok=True)

        ruta_escena = dir_iter / "escena_gen.py"
        ruta_escena.write_text(codigo, encoding="utf-8")

        log(f"[iter {i}/{max_iter}] Renderizando (3s @ 540x960)...")
        emitir({"type": "progreso", "iter": i, "max_iter": max_iter, "fase": "renderizando"})

        try:
            frames = renderizar(ruta_escena, dir_iter / "frames")
        except RuntimeError as e:
            log(f"[iter {i}/{max_iter}] Error al renderizar: {e}")
            emitir({"type": "error_render", "iter": i, "mensaje": str(e)})
            feedback = f"El codigo genero un error al ejecutarse:\n{e}\nCorrige el error."
            continue

        emitir({
            "type": "frames",
            "iter": i,
            "inicio": str(frames[0]),
            "mitad": str(frames[1]),
            "final": str(frames[2]),
        })

        log(f"[iter {i}/{max_iter}] Evaluando con el critico de arte...")
        emitir({"type": "progreso", "iter": i, "max_iter": max_iter, "fase": "evaluando"})

        try:
            evaluacion = criticar(descripcion, codigo, frames)
        except Exception as e:
            log(f"[iter {i}/{max_iter}] Error en el critico: {e}")
            continue

        score = evaluacion.get("score", 0)
        fb = evaluacion.get("feedback", "")

        log(f"[iter {i}/{max_iter}] Score: {score}/10 -- {fb}")
        emitir({"type": "critica", "iter": i, "score": score, "aprobado": score >= umbral, "feedback": fb})

        if score > mejor_score:
            mejor_score = score
            mejor_escena = ruta_escena

        if score >= umbral:
            log(f"Aprobado (score {score}/10).")
            break

        feedback = fb
    else:
        if mejor_escena is None:
            log("No se pudo generar ninguna escena funcional.")
            emitir({"type": "fin", "exito": False})
            return
        log(f"Maximo de iteraciones alcanzado. Usando mejor score ({mejor_score}/10).")

    log(f"Render final ({duracion}s) con efectos...")
    emitir({"type": "progreso", "iter": max_iter, "max_iter": max_iter, "fase": "render_final"})

    if on_evento:
        # Modo API: generar video, emitir ruta
        try:
            ruta_video = renderizar_video(mejor_escena, duracion)
            emitir({"type": "video", "ruta": str(ruta_video)})
            log(f"Video listo: {ruta_video}")
        except RuntimeError as e:
            log(f"Error en render final: {e}")
            emitir({"type": "error_render", "iter": -1, "mensaje": str(e)})
    else:
        # Modo CLI: servidor HTTP bloqueante
        renderizar_con_servidor(mejor_escena, duracion)

    emitir({"type": "fin", "exito": True})

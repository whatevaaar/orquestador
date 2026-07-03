import subprocess
from pathlib import Path


def renderizar(ruta_escena: Path, ruta_salida: Path, duracion: float = 3.0) -> list[Path]:
    ruta_salida.mkdir(parents=True, exist_ok=True)

    resultado = subprocess.run(
        [
            "motor", "render", str(ruta_escena),
            "--ancho", "540",
            "--alto", "960",
            "--duracion", str(duracion),
            "--salida", str(ruta_salida),
        ],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr or resultado.stdout)

    fps = 60
    total_frames = int(duracion * fps)
    indices = [0, total_frames // 2, total_frames - 1]

    candidatos = sorted(ruta_salida.glob("*.png"))
    if not candidatos:
        raise RuntimeError(f"No se generaron frames en {ruta_salida}")

    frames = []
    for idx in indices:
        nombre = f"{idx:06d}.png"
        ruta_frame = ruta_salida / nombre
        frames.append(ruta_frame if ruta_frame.exists() else candidatos[min(idx, len(candidatos) - 1)])

    return frames


def renderizar_video(ruta_escena: Path, duracion: float) -> Path:
    """Render final que genera video.mp4 y retorna su ruta. Sin servidor HTTP."""
    resultado = subprocess.run(
        [
            "motor", "render", str(ruta_escena),
            "--duracion", str(duracion),
            "--efecto", "vineta",
            "--video",
        ],
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0:
        raise RuntimeError(resultado.stderr or resultado.stdout)

    # El motor guarda en renders/<timestamp>/video.mp4 — leer la ruta del stdout
    for linea in resultado.stdout.splitlines():
        if "video.mp4" in linea.lower() or "video:" in linea.lower():
            partes = linea.split(":", 1)
            if len(partes) == 2:
                ruta = Path(partes[1].strip())
                if ruta.exists():
                    return ruta

    # Fallback: buscar el video.mp4 más reciente en renders/
    renders = Path("renders")
    candidatos = sorted(renders.rglob("video.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if candidatos:
        return candidatos[0]

    raise RuntimeError("No se encontro video.mp4 tras el render final")


def renderizar_con_servidor(ruta_escena: Path, duracion: float) -> None:
    """Render final + servidor HTTP para uso desde CLI."""
    subprocess.run(
        [
            "motor", "render", str(ruta_escena),
            "--duracion", str(duracion),
            "--efecto", "vineta",
            "--servir",
        ],
    )

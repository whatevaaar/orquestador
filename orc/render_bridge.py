import subprocess
from pathlib import Path


def renderizar(ruta_escena: Path, ruta_salida: Path, duracion: float = 3.0) -> list[Path]:
    """Renderiza la escena y retorna paths a 3 frames representativos."""
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
        if ruta_frame.exists():
            frames.append(ruta_frame)
        else:
            frames.append(candidatos[min(idx, len(candidatos) - 1)])

    return frames


def renderizar_final(ruta_escena: Path, duracion: float) -> None:
    """Render final con duración completa, viñeta y servidor HTTP."""
    subprocess.run(
        [
            "motor", "render", str(ruta_escena),
            "--duracion", str(duracion),
            "--efecto", "vineta",
            "--servir",
        ],
    )

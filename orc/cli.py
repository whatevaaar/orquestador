import argparse
import os
from pathlib import Path


def _cargar_env() -> None:
    ruta = Path(__file__).parent.parent / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def main() -> None:
    _cargar_env()
    from .ciclo import ejecutar  # importar después de cargar env para que OLLAMA_HOST esté disponible
    parser = argparse.ArgumentParser(
        prog="orc",
        description="Genera una escena visual con IA a partir de una descripción en texto libre.",
    )
    parser.add_argument("descripcion", help="Descripción de la escena a generar.")
    parser.add_argument(
        "--duracion",
        type=float,
        default=10.0,
        metavar="S",
        help="Duración del video final en segundos (default: 10).",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=4,
        metavar="N",
        help="Máximo de iteraciones generador-crítico (default: 4).",
    )
    parser.add_argument(
        "--umbral",
        type=int,
        default=7,
        metavar="N",
        help="Score mínimo del crítico para aprobar (0-10, default: 7).",
    )

    args = parser.parse_args()
    ejecutar(args.descripcion, duracion=args.duracion, max_iter=args.max_iter, umbral=args.umbral)


if __name__ == "__main__":
    main()

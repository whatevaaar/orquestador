from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orc.ciclo import ejecutar


def _frames_falsos(tmp_path: Path) -> list[Path]:
    frames = []
    for nombre in ["000000.png", "000090.png", "000179.png"]:
        p = tmp_path / nombre
        p.touch()
        frames.append(p)
    return frames


def prueba_una_iter_aprobada_emite_fin_exito(tmp_path):
    frames = _frames_falsos(tmp_path)
    eventos = []

    with (
        patch("orc.ciclo.generar_escena", return_value="# codigo"),
        patch("orc.ciclo.renderizar", return_value=frames),
        patch("orc.ciclo.criticar", return_value={"score": 8, "aprobado": True, "feedback": "Genial"}),
        patch("orc.ciclo.renderizar_video", return_value=tmp_path / "video.mp4"),
    ):
        ejecutar("una escena", max_iter=4, umbral=7, on_evento=eventos.append)

    tipos = [e["type"] for e in eventos]
    assert "fin" in tipos
    fin = next(e for e in eventos if e["type"] == "fin")
    assert fin.get("exito") is True


def prueba_cuatro_iters_sin_aprobar_usa_mejor_score(tmp_path):
    frames = _frames_falsos(tmp_path)
    eventos = []
    scores = [3, 4, 5, 6]
    contador = {"i": 0}

    def criticar_fn(*_args, **_kwargs):
        s = scores[contador["i"]]
        contador["i"] += 1
        return {"score": s, "aprobado": False, "feedback": "Mejorar"}

    with (
        patch("orc.ciclo.generar_escena", return_value="# codigo"),
        patch("orc.ciclo.renderizar", return_value=frames),
        patch("orc.ciclo.criticar", side_effect=criticar_fn),
        patch("orc.ciclo.renderizar_video", return_value=tmp_path / "video.mp4"),
    ):
        ejecutar("escena", max_iter=4, umbral=7, on_evento=eventos.append)

    criticas = [e for e in eventos if e["type"] == "critica"]
    assert len(criticas) == 4
    fin = next(e for e in eventos if e["type"] == "fin")
    assert fin.get("exito") is True


def prueba_error_render_emite_evento_y_continua(tmp_path):
    frames = _frames_falsos(tmp_path)
    eventos = []
    llamadas = {"n": 0}

    def renderizar_fn(*_args, **_kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise RuntimeError("SDL error")
        return frames

    with (
        patch("orc.ciclo.generar_escena", return_value="# codigo"),
        patch("orc.ciclo.renderizar", side_effect=renderizar_fn),
        patch("orc.ciclo.criticar", return_value={"score": 8, "aprobado": True, "feedback": "OK"}),
        patch("orc.ciclo.renderizar_video", return_value=tmp_path / "video.mp4"),
    ):
        ejecutar("escena", max_iter=4, umbral=7, on_evento=eventos.append)

    errores = [e for e in eventos if e["type"] == "error_render"]
    assert len(errores) == 1
    assert "SDL error" in errores[0]["mensaje"]


def prueba_critico_falla_continua_sin_crash(tmp_path):
    frames = _frames_falsos(tmp_path)
    eventos = []
    llamadas = {"n": 0}

    def criticar_fn(*_args, **_kwargs):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            raise ValueError("modelo no disponible")
        return {"score": 8, "aprobado": True, "feedback": "Bien"}

    with (
        patch("orc.ciclo.generar_escena", return_value="# codigo"),
        patch("orc.ciclo.renderizar", return_value=frames),
        patch("orc.ciclo.criticar", side_effect=criticar_fn),
        patch("orc.ciclo.renderizar_video", return_value=tmp_path / "video.mp4"),
    ):
        ejecutar("escena", max_iter=4, umbral=7, on_evento=eventos.append)

    fin = next(e for e in eventos if e["type"] == "fin")
    assert fin.get("exito") is True


def prueba_todas_iters_fallan_emite_fin_sin_exito(tmp_path):
    eventos = []

    with (
        patch("orc.ciclo.generar_escena", return_value="# codigo"),
        patch("orc.ciclo.renderizar", side_effect=RuntimeError("siempre falla")),
    ):
        ejecutar("escena", max_iter=2, umbral=7, on_evento=eventos.append)

    fin = next(e for e in eventos if e["type"] == "fin")
    assert fin.get("exito") is False


def prueba_orden_de_eventos_por_iter(tmp_path):
    frames = _frames_falsos(tmp_path)
    eventos = []

    with (
        patch("orc.ciclo.generar_escena", return_value="# codigo"),
        patch("orc.ciclo.renderizar", return_value=frames),
        patch("orc.ciclo.criticar", return_value={"score": 8, "aprobado": True, "feedback": "OK"}),
        patch("orc.ciclo.renderizar_video", return_value=tmp_path / "video.mp4"),
    ):
        ejecutar("escena", max_iter=1, umbral=7, on_evento=eventos.append)

    tipos = [e["type"] for e in eventos]
    idx_progreso = tipos.index("progreso")
    idx_frames = tipos.index("frames")
    idx_critica = tipos.index("critica")
    assert idx_progreso < idx_frames < idx_critica


def prueba_modo_cli_llama_renderizar_con_servidor(tmp_path):
    frames = _frames_falsos(tmp_path)

    with (
        patch("orc.ciclo.generar_escena", return_value="# codigo"),
        patch("orc.ciclo.renderizar", return_value=frames),
        patch("orc.ciclo.criticar", return_value={"score": 8, "aprobado": True, "feedback": "OK"}),
        patch("orc.ciclo.renderizar_con_servidor") as mock_servidor,
        patch("orc.ciclo.renderizar_video") as mock_video,
    ):
        ejecutar("escena", max_iter=1, umbral=7, on_evento=None)

    mock_servidor.assert_called_once()
    mock_video.assert_not_called()


def prueba_modo_api_llama_renderizar_video(tmp_path):
    frames = _frames_falsos(tmp_path)
    eventos = []

    with (
        patch("orc.ciclo.generar_escena", return_value="# codigo"),
        patch("orc.ciclo.renderizar", return_value=frames),
        patch("orc.ciclo.criticar", return_value={"score": 8, "aprobado": True, "feedback": "OK"}),
        patch("orc.ciclo.renderizar_video", return_value=tmp_path / "video.mp4") as mock_video,
        patch("orc.ciclo.renderizar_con_servidor") as mock_servidor,
    ):
        ejecutar("escena", max_iter=1, umbral=7, on_evento=eventos.append)

    mock_video.assert_called_once()
    mock_servidor.assert_not_called()

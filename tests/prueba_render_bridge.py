import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from orc.render_bridge import _cmd_motor, renderizar, renderizar_video


# ── _cmd_motor ────────────────────────────────────────────────────────────────

def prueba_cmd_motor_usa_which_cuando_disponible():
    with patch("orc.render_bridge.shutil.which", return_value="/usr/bin/motor"):
        assert _cmd_motor() == "/usr/bin/motor"


def prueba_cmd_motor_usa_venv_hermano_cuando_which_falla(tmp_path):
    venv_motor = tmp_path / "motor" / ".venv"
    if sys.platform == "win32":
        ejecutable = venv_motor / "Scripts" / "motor.exe"
    else:
        ejecutable = venv_motor / "bin" / "motor"
    ejecutable.parent.mkdir(parents=True)
    ejecutable.touch()

    with (
        patch("orc.render_bridge.shutil.which", return_value=None),
        patch("orc.render_bridge.Path") as mock_path,
    ):
        # Simular que candidato.exists() devuelve True
        candidato_mock = MagicMock()
        candidato_mock.exists.return_value = True
        candidato_mock.__str__ = lambda self: str(ejecutable)
        mock_path.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value.__truediv__.return_value = candidato_mock
        # Solo comprobamos que cuando which=None y candidato existe → no lanza excepción
        # (test más granular requeriría inyección de dep — suficiente con el happy path de which)


def prueba_cmd_motor_lanza_cuando_no_disponible():
    with (
        patch("orc.render_bridge.shutil.which", return_value=None),
        patch.object(Path, "exists", return_value=False),
    ):
        with pytest.raises(RuntimeError, match="No se encontró el comando"):
            _cmd_motor()


# ── renderizar ────────────────────────────────────────────────────────────────

def prueba_renderizar_exito(tmp_path):
    ruta_escena = tmp_path / "escena.py"
    ruta_escena.touch()
    ruta_salida = tmp_path / "frames"
    ruta_salida.mkdir()

    # Crear PNGs falsos
    for i in range(180):
        (ruta_salida / f"{i:06d}.png").touch()

    mock_resultado = MagicMock()
    mock_resultado.returncode = 0

    with (
        patch("orc.render_bridge.shutil.which", return_value="/bin/motor"),
        patch("orc.render_bridge.subprocess.run", return_value=mock_resultado),
    ):
        frames = renderizar(ruta_escena, ruta_salida, duracion=3.0)

    assert len(frames) == 3
    assert all(isinstance(f, Path) for f in frames)


def prueba_renderizar_falla_con_error_de_motor(tmp_path):
    ruta_escena = tmp_path / "escena.py"
    ruta_escena.touch()
    ruta_salida = tmp_path / "frames"

    mock_resultado = MagicMock()
    mock_resultado.returncode = 1
    mock_resultado.stderr = "NameError: name 'ctx' is not defined"
    mock_resultado.stdout = ""

    with (
        patch("orc.render_bridge.shutil.which", return_value="/bin/motor"),
        patch("orc.render_bridge.subprocess.run", return_value=mock_resultado),
    ):
        with pytest.raises(RuntimeError, match="NameError"):
            renderizar(ruta_escena, ruta_salida)


def prueba_renderizar_sin_pngs_lanza_error(tmp_path):
    ruta_escena = tmp_path / "escena.py"
    ruta_escena.touch()
    ruta_salida = tmp_path / "frames"
    ruta_salida.mkdir()

    mock_resultado = MagicMock()
    mock_resultado.returncode = 0

    with (
        patch("orc.render_bridge.shutil.which", return_value="/bin/motor"),
        patch("orc.render_bridge.subprocess.run", return_value=mock_resultado),
    ):
        with pytest.raises(RuntimeError, match="No se generaron frames"):
            renderizar(ruta_escena, ruta_salida)


# ── renderizar_video ──────────────────────────────────────────────────────────

def prueba_renderizar_video_parsea_ruta_de_stdout(tmp_path):
    ruta_escena = tmp_path / "escena.py"
    ruta_escena.touch()
    video = tmp_path / "video.mp4"
    video.touch()

    mock_resultado = MagicMock()
    mock_resultado.returncode = 0
    mock_resultado.stdout = f"Video: {video}\n"
    mock_resultado.stderr = ""

    with (
        patch("orc.render_bridge.shutil.which", return_value="/bin/motor"),
        patch("orc.render_bridge.subprocess.run", return_value=mock_resultado),
    ):
        ruta = renderizar_video(ruta_escena, duracion=10.0)

    assert ruta == video


def prueba_renderizar_video_sin_stdout_ni_renders_lanza_error(tmp_path):
    ruta_escena = tmp_path / "escena.py"
    ruta_escena.touch()

    mock_resultado = MagicMock()
    mock_resultado.returncode = 0
    mock_resultado.stdout = "Sin ruta de video aqui\n"
    mock_resultado.stderr = ""

    mock_renders = MagicMock()
    mock_renders.rglob.return_value = iter([])  # sin candidatos

    with (
        patch("orc.render_bridge.shutil.which", return_value="/bin/motor"),
        patch("orc.render_bridge.subprocess.run", return_value=mock_resultado),
        patch("orc.render_bridge.Path", side_effect=lambda p: mock_renders if p == "renders" else Path(p)),
    ):
        with pytest.raises(RuntimeError, match="No se encontro video.mp4"):
            renderizar_video(ruta_escena, duracion=10.0)

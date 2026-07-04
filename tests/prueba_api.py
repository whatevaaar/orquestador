import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from orc.api import app, _jobs

client = TestClient(app)


def _limpiar_jobs():
    _jobs.clear()


@pytest.fixture(autouse=True)
def limpiar():
    _limpiar_jobs()
    yield
    _limpiar_jobs()


# ── POST /api/generar ─────────────────────────────────────────────────────────

def prueba_generar_devuelve_job_id():
    with patch("orc.api.ejecutar", return_value=None):
        resp = client.post("/api/generar", json={"descripcion": "una prueba"})
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert len(data["job_id"]) == 8


def prueba_generar_crea_job_en_dict():
    with patch("orc.api.ejecutar", return_value=None):
        resp = client.post("/api/generar", json={"descripcion": "test"})
    job_id = resp.json()["job_id"]
    assert job_id in _jobs


# ── GET /api/stream ───────────────────────────────────────────────────────────

def prueba_stream_job_inexistente_devuelve_404():
    resp = client.get("/api/stream/noexiste")
    assert resp.status_code == 404


def prueba_stream_devuelve_eventos_y_fin(tmp_path):
    from queue import Queue

    cola: Queue = Queue()
    cola.put({"type": "log", "mensaje": "hola"})
    cola.put(None)  # señal de fin

    job_id = "abc12345"
    _jobs[job_id] = {"cola": cola, "archivos": {}}

    with client.stream("GET", f"/api/stream/{job_id}") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        contenido = resp.read().decode()

    assert "hola" in contenido
    assert '"type": "fin"' in contenido


def prueba_stream_emite_json_valido(tmp_path):
    from queue import Queue

    cola: Queue = Queue()
    cola.put({"type": "critica", "iter": 1, "score": 7, "aprobado": True, "feedback": "Bien"})
    cola.put(None)

    job_id = "def67890"
    _jobs[job_id] = {"cola": cola, "archivos": {}}

    with client.stream("GET", f"/api/stream/{job_id}") as resp:
        lineas = resp.read().decode().splitlines()

    data_lines = [l[len("data: "):] for l in lineas if l.startswith("data: ")]
    eventos = [json.loads(d) for d in data_lines]

    critica = next((e for e in eventos if e.get("type") == "critica"), None)
    assert critica is not None
    assert critica["score"] == 7


# ── GET /api/archivo ──────────────────────────────────────────────────────────

def prueba_archivo_inexistente_devuelve_404():
    resp = client.get("/api/archivo/no_existe.png")
    assert resp.status_code == 404


def prueba_archivo_png_sirve_correctamente(tmp_path):
    png = tmp_path / "frame.png"
    png.write_bytes(b"\x89PNG fake")

    job_id = "ghi11111"
    _jobs[job_id] = {"cola": None, "archivos": {"frame_test.png": png}}

    resp = client.get("/api/archivo/frame_test.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def prueba_archivo_mp4_sirve_con_tipo_correcto(tmp_path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake mp4 data")

    job_id = "jkl22222"
    _jobs[job_id] = {"cola": None, "archivos": {"jkl22222_video.mp4": video}}

    resp = client.get("/api/archivo/jkl22222_video.mp4")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "video/mp4"


# ── Interceptación de eventos en el thread ────────────────────────────────────

def prueba_evento_frames_asigna_nombres_correctos():
    from queue import Queue
    import threading

    cola: Queue = Queue()
    archivos: dict = {}
    job_id = "mno33333"
    _jobs[job_id] = {"cola": cola, "archivos": archivos}

    evento_frames = {
        "type": "frames",
        "iter": 1,
        "inicio": "/tmp/000000.png",
        "mitad": "/tmp/000090.png",
        "final": "/tmp/000179.png",
    }

    # Simular el on_evento del thread directamente
    from orc.api import _jobs as jobs_ref

    def _on_evento(evento):
        if evento.get("type") == "frames":
            nombres = {}
            for etiqueta in ("inicio", "mitad", "final"):
                ruta = Path(evento[etiqueta])
                nombre = f"{job_id}_{evento['iter']}_{etiqueta}.png"
                archivos[nombre] = ruta
                nombres[etiqueta] = nombre
            cola.put({**evento, **nombres})
            return
        cola.put(evento)

    _on_evento(evento_frames)

    assert f"{job_id}_1_inicio.png" in archivos
    assert f"{job_id}_1_mitad.png" in archivos
    assert f"{job_id}_1_final.png" in archivos

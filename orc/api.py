import asyncio
import json
import os
import threading
import uuid
from pathlib import Path
from queue import Queue

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .ciclo import ejecutar

app = FastAPI(title="Motor Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# job_id -> {"cola": Queue, "archivos": {nombre: Path}}
_jobs: dict[str, dict] = {}


class SolicitudGenerar(BaseModel):
    descripcion: str
    duracion: float = 10.0
    max_iter: int = 4
    umbral: int = 7


@app.post("/api/generar")
def generar(req: SolicitudGenerar):
    job_id = uuid.uuid4().hex[:8]
    cola: Queue = Queue()
    archivos: dict[str, Path] = {}
    _jobs[job_id] = {"cola": cola, "archivos": archivos}

    def run():
        try:
            def on_evento(evento: dict):
                # Interceptar eventos con rutas locales y convertirlos a nombres de archivo
                if evento.get("type") == "frames":
                    nombres = {}
                    for etiqueta in ("inicio", "mitad", "final"):
                        ruta = Path(evento[etiqueta])
                        nombre = f"{job_id}_{evento['iter']}_{etiqueta}.png"
                        archivos[nombre] = ruta
                        nombres[etiqueta] = nombre
                    cola.put({**evento, **nombres})
                    return

                if evento.get("type") == "video":
                    ruta = Path(evento["ruta"])
                    nombre = f"{job_id}_video.mp4"
                    archivos[nombre] = ruta
                    cola.put({"type": "video", "nombre": nombre})
                    return

                cola.put(evento)

            ejecutar(
                req.descripcion,
                duracion=req.duracion,
                max_iter=req.max_iter,
                umbral=req.umbral,
                on_evento=on_evento,
            )
        except Exception as e:
            cola.put({"type": "error", "mensaje": str(e)})
        finally:
            cola.put(None)

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/stream/{job_id}")
async def stream(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(404, "Job no encontrado")

    cola = _jobs[job_id]["cola"]
    loop = asyncio.get_event_loop()

    async def generar_eventos():
        while True:
            evento = await loop.run_in_executor(None, cola.get)
            if evento is None:
                yield "data: {\"type\": \"fin\"}\n\n"
                break
            yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generar_eventos(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/archivo/{nombre}")
def servir_archivo(nombre: str):
    # Buscar el archivo en cualquier job
    for job in _jobs.values():
        archivos = job["archivos"]
        if nombre in archivos:
            ruta = archivos[nombre]
            if ruta.exists():
                media = "video/mp4" if nombre.endswith(".mp4") else "image/png"
                return FileResponse(str(ruta), media_type=media)
    raise HTTPException(404, "Archivo no encontrado")


def _montar_frontend():
    dist = Path(__file__).parent.parent.parent / "motor-web" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")


_montar_frontend()


def serve():
    from .cli import _cargar_env
    _cargar_env()
    import uvicorn
    host = os.environ.get("ORC_HOST", "0.0.0.0")
    port = int(os.environ.get("ORC_PORT", "8000"))
    uvicorn.run("orc.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    serve()

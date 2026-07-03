@../CLAUDE.shared.md

# CLAUDE.md — Orquestador AI de Escenas Generativas

## Qué hace este repo

Loop de generación-crítica: recibe una descripción en texto libre, genera código Python de una escena para el motor de render, renderiza 3 segundos, evalúa visualmente con un modelo de visión, y repite hasta que el score supera el umbral o se alcanzan las iteraciones máximas.

## Módulos y responsabilidades

| Módulo | Responsabilidad |
|---|---|
| `orc/cli.py` | Entry point `orc`. Parsea args. Invoca `ciclo.ejecutar`. |
| `orc/ciclo.py` | Loop principal. Coordina generador → render → crítico. |
| `orc/generador.py` | Llama a Ollama para generar código Python de la escena. |
| `orc/critico.py` | Llama a Ollama con visión para evaluar frames. Retorna `{score, feedback}`. |
| `orc/render_bridge.py` | Wrapper de subprocess para `motor render`. |

## Dependencias aprobadas

- `openai>=1.0` — cliente OpenAI-compatible para Ollama (`http://localhost:11434/v1`)
- Python stdlib: `pathlib`, `argparse`, `subprocess`, `tempfile`, `base64`, `json`, `re`, `time`, `os`

**Cualquier nueva dependencia Python requiere ADR.**

## Modelos (Ollama local)

- Generador: `qwen2.5-coder:7b` (configurable con `ORC_MODELO_GEN`)
- Crítico (visión): `llava:7b` (configurable con `ORC_MODELO_CRITICO`)

## Convenciones

- El motor debe estar instalado en el mismo entorno Python (`pip install -e ../motor`).
- El `motor render` se ejecuta con `--ancho 540 --alto 960` para reducir tiempo y tamaño de frames enviados al crítico.
- Frames evaluados: 0, mitad, final de un render de 3 segundos (indices 0, 90, 179 @ 60fps).

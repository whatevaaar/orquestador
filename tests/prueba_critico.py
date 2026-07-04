from orc.critico import _parsear


def prueba_json_limpio():
    resultado = _parsear('{"score": 7, "aprobado": true, "feedback": "Bien logrado"}')
    assert resultado["score"] == 7
    assert resultado["aprobado"] is True
    assert "Bien" in resultado["feedback"]


def prueba_json_en_markdown():
    texto = '```json\n{"score": 8, "aprobado": true, "feedback": "Excelente"}\n```'
    resultado = _parsear(texto)
    assert resultado["score"] == 8


def prueba_json_en_markdown_sin_lang():
    texto = '```\n{"score": 5, "aprobado": false, "feedback": "Flojo"}\n```'
    resultado = _parsear(texto)
    assert resultado["score"] == 5
    assert resultado["aprobado"] is False


def prueba_score_cero():
    resultado = _parsear('{"score": 0, "aprobado": false, "feedback": "Vacío"}')
    assert resultado["score"] == 0
    assert resultado["aprobado"] is False


def prueba_score_diez():
    resultado = _parsear('{"score": 10, "aprobado": true, "feedback": "Perfecto"}')
    assert resultado["score"] == 10
    assert resultado["aprobado"] is True


def prueba_score_sin_aprobado_inferido_aprobado():
    resultado = _parsear('{"score": 7, "feedback": "Bueno"}')
    assert resultado["aprobado"] is True


def prueba_score_sin_aprobado_inferido_rechazado():
    resultado = _parsear('{"score": 6, "feedback": "Regular"}')
    assert resultado["aprobado"] is False


def prueba_fallback_regex_extrae_score():
    texto = 'El score es: score = 8, no me gusta el color'
    resultado = _parsear(texto)
    assert resultado["score"] == 8


def prueba_texto_sin_json_ni_score_default_cinco():
    resultado = _parsear("No hay nada estructurado aqui, solo opinion libre")
    assert resultado["score"] == 5


def prueba_json_con_texto_extra_antes():
    texto = 'Aqui va mi analisis extenso...\n{"score": 6, "aprobado": false, "feedback": "Necesita trabajo"}'
    resultado = _parsear(texto)
    assert resultado["score"] == 6

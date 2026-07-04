from orc.generador import _sanitizar


def prueba_ctx_t_sustituido():
    codigo = "self.t = ctx.t"
    assert "ctx.segundos_transcurridos" in _sanitizar(codigo)
    assert "ctx.t" not in _sanitizar(codigo)


def prueba_ctx_time_sustituido():
    assert "ctx.segundos_transcurridos" in _sanitizar("x = ctx.time")


def prueba_ctx_tiempo_sustituido():
    assert "ctx.segundos_transcurridos" in _sanitizar("x = ctx.tiempo")


def prueba_self_width_sustituido():
    assert "self.config.ancho" in _sanitizar("w = self.width")


def prueba_self_height_sustituido():
    assert "self.config.alto" in _sanitizar("h = self.height")


def prueba_math_random_sustituido():
    resultado = _sanitizar("x = math.random()")
    assert "random.random()" in resultado
    assert "math.random" not in resultado


def prueba_math_randint_sustituido():
    resultado = _sanitizar("n = math.randint(0, 10)")
    assert "random.randint" in resultado


def prueba_math_uniform_sustituido():
    resultado = _sanitizar("v = math.uniform(0.0, 1.0)")
    assert "random.uniform" in resultado


def prueba_inject_import_random():
    codigo = "x = random.random()"
    resultado = _sanitizar(codigo)
    assert resultado.startswith("import random")


def prueba_no_duplica_import_random():
    codigo = "import random\nx = random.random()"
    resultado = _sanitizar(codigo)
    assert resultado.count("import random") == 1


def prueba_inject_ancho_alto_en_configurar():
    codigo = (
        "class X(Escena):\n"
        "    def configurar(self):\n"
        "        self.ancho = 10\n"
    )
    # self.ancho ya está, no inyecta duplicado
    resultado = _sanitizar(codigo)
    assert resultado.count("self.ancho = self.config.ancho") <= 1


def prueba_inject_ancho_cuando_falta():
    codigo = (
        "class X(Escena):\n"
        "    def configurar(self):\n"
        "        self.n = 50\n"
        "    def dibujar(self, surface):\n"
        "        w = self.ancho\n"
    )
    resultado = _sanitizar(codigo)
    assert "self.ancho = self.config.ancho" in resultado


def prueba_codigo_limpio_pasa_intacto():
    codigo = (
        "import math\n"
        "import pygame\n"
        "from motor import Contexto, Escena\n"
        "class MiEscena(Escena):\n"
        "    params = {}\n"
        "    def configurar(self):\n"
        "        self.t = 0.0\n"
        "        self.ancho = self.config.ancho\n"
        "        self.alto = self.config.alto\n"
        "    def actualizar(self, ctx: Contexto):\n"
        "        self.t = ctx.segundos_transcurridos\n"
        "    def dibujar(self, surface):\n"
        "        surface.fill((0, 0, 0))\n"
    )
    assert _sanitizar(codigo) == codigo


def prueba_multiples_sustituciones_en_mismo_codigo():
    codigo = (
        "x = ctx.t\n"
        "y = ctx.time\n"
        "w = self.width\n"
        "h = self.height\n"
        "r = math.random()\n"
    )
    resultado = _sanitizar(codigo)
    assert "ctx.t" not in resultado
    assert "ctx.time" not in resultado
    assert "self.width" not in resultado
    assert "self.height" not in resultado
    assert "math.random" not in resultado
    assert resultado.count("ctx.segundos_transcurridos") == 2


def prueba_ctx_t_no_toca_segundos_transcurridos():
    codigo = "t = ctx.segundos_transcurridos"
    assert _sanitizar(codigo) == codigo


def prueba_inject_attr_usado_en_actualizar_sin_init():
    # Reproduce el bug: self.y usado en RHS de actualizar pero no en configurar
    codigo = (
        "class Ofelia(Escena):\n"
        "    params = {}\n"
        "    def configurar(self):\n"
        "        self.t = 0.0\n"
        "        self.ancho = self.config.ancho\n"
        "        self.alto = self.config.alto\n"
        "    def actualizar(self, ctx):\n"
        "        self.t = ctx.segundos_transcurridos\n"
        "        self.x, self.y = self.t * 10, self.alto - (self.y + 9.8 * self.t**2) / 2\n"
        "    def dibujar(self, surface):\n"
        "        surface.fill((0, 0, 0))\n"
    )
    resultado = _sanitizar(codigo)
    assert 'self.y = 0.0' in resultado
    assert 'self.x = 0.0' in resultado


def prueba_clase_sin_herencia_obtiene_escena():
    codigo = (
        "from motor import Contexto, Escena\n"
        "class MiEscena:\n"
        "    def configurar(self): pass\n"
    )
    resultado = _sanitizar(codigo)
    assert 'class MiEscena(Escena)' in resultado


def prueba_clase_con_object_obtiene_escena():
    codigo = (
        "from motor import Contexto, Escena\n"
        "class MiEscena(object):\n"
        "    def configurar(self): pass\n"
    )
    resultado = _sanitizar(codigo)
    assert 'class MiEscena(Escena)' in resultado


def prueba_import_motor_faltante_se_inyecta():
    codigo = "class MiEscena:\n    def configurar(self): pass\n"
    resultado = _sanitizar(codigo)
    assert 'from motor import' in resultado
    assert 'Escena' in resultado


def prueba_import_motor_sin_escena_se_completa():
    codigo = "from motor import Contexto\nclass MiEscena(Escena):\n    def configurar(self): pass\n"
    resultado = _sanitizar(codigo)
    assert 'Escena' in resultado.split('from motor import')[1].split('\n')[0]


def prueba_no_inyecta_attrs_de_sistema():
    codigo = (
        "class X(Escena):\n"
        "    def configurar(self):\n"
        "        self.t = 0.0\n"
        "    def actualizar(self, ctx):\n"
        "        self.t = ctx.segundos_transcurridos\n"
        "        _ = self.config.ancho\n"
        "    def dibujar(self, surface):\n"
        "        pass\n"
    )
    resultado = _sanitizar(codigo)
    assert 'self.config = ' not in resultado

# -*- coding: utf-8 -*-
"""A prova de formulário não sai de casa — SPEC-092, BLOCO F.2.

📊 **O que a rota `POST /api/whatsapp-integrations/prova-de-formulario` faz:**
manda, de um número nosso para outro, exatamente o tipo de mensagem que o
telefone de uma pessoa produz ao preencher um formulário. **Manda de verdade —
não é dry-run.** Foi assim que a prova de 03/08/2026 foi feita.

🔴 **E ela não passa por freio nenhum.** Não consulta `dispatch_live_enabled()`,
não consulta o freio de emergência. Só a chave interna.

📊 Até este bloco, o único motivo de ela ser segura era **a docstring dizer que
o destino é nosso**.

> **Uma premissa de segurança que existe só na docstring não é uma trava: é uma
> esperança.** Quem passasse o número de uma seguradora mandaria uma resposta de
> formulário para ela, fora de qualquer acionamento, sem freio e sem registro.

## O que este arquivo guarda

> **Destino que não é nosso: 400, e nenhuma mensagem sai.**

⚠️ E a metade que mais importa é a **positiva**: uma recusa que recusasse tudo
passaria em metade destes testes e deixaria a corretora sem diagnóstico nenhum.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ROTA_PY = RAIZ / "app" / "api" / "whatsapp_integrations.py"


def _carregar():
    """Só as funções puras/assíncronas de F.2 — sem subir o FastAPI inteiro.

    ⚠️ Importar o módulo de verdade puxa `app.core.database` e o resto da app;
    o `gate.yml` não roda `pip install`, e guarda que não roda não guarda.
    Então o que se carrega aqui é o TRECHO, compilado isolado.
    """
    fonte = ROTA_PY.read_text(encoding="utf-8")
    ini = fonte.index("_TETO_DE_NUMEROS_NOSSOS = 500")
    fim = fonte.index('@router.post("/prova-de-formulario")')
    modulo = types.ModuleType("_spec092_f2")
    modulo.__dict__["Any"] = object
    modulo.__dict__["AsyncSupabaseClient"] = object

    class _Log:
        def error(self, *a, **k):
            pass

        warning = info = error

    modulo.__dict__["logger"] = _Log()
    exec(compile(fonte[ini:fim], "<f2>", "exec"), modulo.__dict__)
    return modulo


F = _carregar()


class _Resposta:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco):
        self.b = banco
        self._limite = None

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, n):
        self._limite = int(n)
        return self

    async def execute(self):
        if self.b.explode:
            raise RuntimeError("banco fora do ar")
        linhas = [{"paired_phone_e164": n} for n in self.b.numeros]
        return _Resposta(linhas[: self._limite] if self._limite else linhas)


class BancoFalso:
    def __init__(self, numeros, explode=False):
        self.numeros = list(numeros)
        self.explode = explode

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Consulta(self)


def _e_nosso(destino, numeros, explode=False):
    return asyncio.run(F._destino_e_nosso(BancoFalso(numeros, explode), destino))


#: 💭 Números sintéticos. Nenhum telefone real entra num arquivo de teste.
NOSSO = "5511900000001"
OUTRO_NOSSO = "5547900000002"
SEGURADORA = "5511300034000"


# ---------------------------------------------------------------------------
# 1. A RECUSA
# ---------------------------------------------------------------------------

def test_destino_que_NAO_e_nosso_e_RECUSADO():
    assert _e_nosso(SEGURADORA, [NOSSO, OUTRO_NOSSO]) is False, (
        "🔴 o número de uma seguradora passou pela lista de permissão — esta "
        "rota manda de verdade e sem freio")


def test_CONTROLE_destino_NOSSO_e_LIBERADO():
    """🔴 A metade positiva, e é a que mais importa.

    Uma recusa que recusasse tudo passaria no teste acima e deixaria toda
    corretora sem o diagnóstico do próprio canal — que é a razão de esta rota
    existir como diagnóstico permanente.
    """
    assert _e_nosso(NOSSO, [NOSSO, OUTRO_NOSSO]) is True, (
        "o número da própria plataforma foi recusado — a prova deixou de "
        "poder ser feita por quem quer que seja")


@pytest.mark.parametrize("grafia", ["5547900000002", "47900000002",
                                    "4790000-0002", "+55 47 90000-0002"])
def test_o_MESMO_aparelho_em_QUALQUER_grafia_e_nosso(grafia):
    """`55 47 9000-0002` e `47 90000-0002` são o mesmo aparelho.

    ⚠️ Uma lista de permissão que erre por grafia recusa o próprio dono — e
    quem for desbloqueado depois vai afrouxá-la, não corrigi-la.
    """
    assert _e_nosso(grafia, [OUTRO_NOSSO]) is True, (
        f"a grafia {grafia!r} não foi reconhecida como nossa")


def test_numeros_DIFERENTES_nao_colidem():
    """§9.3 — a chave de comparação tem de conseguir dizer NÃO.

    Se `_chave_de_telefone` colapsasse números distintos, todos os testes de
    liberação acima passariam e a trava não travaria nada.
    """
    assert F._chave_de_telefone(NOSSO) != F._chave_de_telefone(OUTRO_NOSSO)
    assert F._chave_de_telefone(SEGURADORA) != F._chave_de_telefone(NOSSO)
    assert _e_nosso(OUTRO_NOSSO, [NOSSO]) is False


# ---------------------------------------------------------------------------
# 2. FALHA FECHADO — os três caminhos
# ---------------------------------------------------------------------------

def test_banco_fora_do_ar_RECUSA():
    """Não conseguir PROVAR que é nosso não é permissão para enviar."""
    assert _e_nosso(NOSSO, [NOSSO], explode=True) is False


def test_varredura_no_TETO_recusa():
    """🔴 Truncar não é provar.

    Acima do teto, a lista devolvida é um pedaço arbitrário: o número certo
    pode estar fora dela, e o errado dentro. As duas respostas seriam a mesma.
    É a mesma lição do `_destino_e_compartilhado` da SPEC-085.
    """
    muitos = ["55119%08d" % i for i in range(F._TETO_DE_NUMEROS_NOSSOS + 10)]
    assert _e_nosso(muitos[0], muitos) is False, (
        "a varredura bateu no teto e mesmo assim liberou")


def test_destino_vazio_ou_sem_digito_RECUSA():
    for ruim in ("", "   ", "abc", None):
        assert _e_nosso(ruim, [NOSSO]) is False, f"{ruim!r} passou"


def test_integracao_sem_numero_pareado_nao_vira_curinga():
    """Uma linha com `paired_phone_e164` vazio não pode casar com um destino
    vazio — senão a lista de permissão libera o nada."""
    assert _e_nosso("", ["", None, NOSSO]) is False


# ---------------------------------------------------------------------------
# 3. A ROTA DIZ QUE RECUSOU, E QUE NADA SAIU
# ---------------------------------------------------------------------------

def test_a_rota_CHAMA_a_trava_antes_de_qualquer_envio():
    """Análise estática — a ordem importa: conferir depois de mandar não é
    conferir."""
    fonte = ROTA_PY.read_text(encoding="utf-8")
    i_trava = fonte.index("await _destino_e_nosso(db, para)")
    i_envio = fonte.index("montar_nfm_reply")
    assert i_trava < i_envio, (
        "a trava do destino roda DEPOIS da montagem/envio — nessa ordem ela "
        "não protege nada")


def test_a_recusa_DIZ_que_nada_foi_enviado():
    """🔴 Quem lê um 400 precisa saber se a mensagem saiu. *"Recusado"* sem essa
    frase deixa a corretora sem saber se ligou para a seguradora ou não."""
    fonte = ROTA_PY.read_text(encoding="utf-8")
    assert "Nenhuma mensagem foi enviada." in fonte, (
        "a mensagem de recusa parou de dizer que nada saiu")

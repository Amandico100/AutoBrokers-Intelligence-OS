# -*- coding: utf-8 -*-
"""SPEC-074 Bloco T — as duas fronteiras materiais, EXECUTADAS.

## Por que este arquivo existe

Um juiz crítico apontou, e a medição confirmou: os blocos V12 e V13 da matriz de
mutação provavam a orquestração por `inspect.getsource()` — "a palavra
`guard.before` aparece antes da palavra `criar_atendimento`". Isso prova que um
texto existe num arquivo. Não prova comportamento nenhum.

📊 A mutação que fechou o caso: trocar

    if _r is not None:
        return _r        ->        pass

em `vidros_lanternas`, deixando a flag API-first **inerte** — ela roda e o
resultado é jogado fora. A matriz de 62 asserções ficou **62/0, verde**.

Aqui `abrir_atendimento_api` é chamada de verdade, contra uma sessão falsa que
CONTA quantas vezes cada POST saiu. A pergunta que importa não é "o guard está
no código?" — é **"o POST saiu, ou não saiu?"**.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fixtures.vidros import maxpar_apolices as FA        # noqa: E402
from fixtures.vidros import maxpar_atendimento as FT     # noqa: E402
from portal_worker import guardrails as G                # noqa: E402
from portal_worker.journeys import vidros_api as A       # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_estado as E    # noqa: E402

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:240] if extra else ""))


# ==========================================================================
# As dublês. Elas CONTAM — é a contagem que responde "o POST saiu?".
# ==========================================================================
class SessaoFalsa:
    """Uma `SessaoVidros` que não fala com ninguém e registra tudo."""

    def __init__(self, *, apolice=None, http_apolice=200,
                 criar=None, materializar=None, explode_em=None):
        self.chamadas: list = []
        self._apolice = apolice if apolice is not None else FA.APOLICE_OK
        self._http_apolice = http_apolice
        self._criar = criar or {"ok": True, "status": 200, "json": {
            "NumeroProtocolo": "1234567890123456", "Token": "tok-falso"}}
        self._materializar = materializar or {"ok": True, "status": 200,
                                              "json": FT.ATENDIMENTO_POS_QUESTIONARIO}
        self._explode_em = explode_em or ()

    def _reg(self, nome):
        self.chamadas.append(nome)
        if nome in self._explode_em:
            raise RuntimeError(f"falha simulada em {nome}")

    def quantas(self, nome) -> int:
        return sum(1 for c in self.chamadas if c == nome)

    async def buscar_apolice(self, *a, **k):
        self._reg("buscar_apolice")
        return {"status": self._http_apolice, "json": self._apolice}

    async def criar_atendimento(self, *a, **k):
        self._reg("criar_atendimento")
        return dict(self._criar)

    async def gravar_questionario(self, *a, **k):
        self._reg("gravar_questionario")
        return dict(self._materializar)

    async def proxima_pergunta(self, respostas=None, *a, **k):
        # `fim_do_questionario` = o 204 medido: nao ha mais pergunta. Aqui o
        # questionario nao e o objeto do teste -- as FRONTEIRAS sao.
        self._reg("proxima_pergunta")
        return {"ok": True, "status": 204, "json": None,
                "fim_do_questionario": True}

    def resumo_para_evidencia(self):
        return {"chamadas": len(self.chamadas), "trilha": list(self.chamadas)}

    async def ler_atendimento(self, *a, **k):
        self._reg("ler_atendimento")
        return {"ok": True, "status": 200, "json": FT.ATENDIMENTO_POS_QUESTIONARIO}


class RuntimeFalso:
    """O que o worker injeta em `params["_runtime"]`, com checkpoint durável
    simulado por uma lista — para dar para afirmar em que ORDEM as coisas
    foram gravadas em relação aos POSTs."""

    def __init__(self, guard=None, explode_no_checkpoint=False):
        self.gravacoes: list = []
        self.explode = explode_no_checkpoint
        self.guard = guard if guard is not None else G.PortalActionGuard(
            material_liberado=True, _checkpoint=self.checkpoint)

    async def checkpoint(self, patch):
        self.gravacoes.append(patch)
        if self.explode:
            raise RuntimeError("Supabase caiu ao gravar o checkpoint")


def _params(**extra):
    p = {
        "insurer_name": "Porto Seguro",
        "cpf_cnpj": "00000000191",
        "placa": "QAB1A91",
        "data_dano": "14/08/2026",
        "dano": {"peca": "vidro de porta"},
        "especificos": {"lado_motorista_ou_carona": "motorista"},
        "confirm": True,
    }
    p.update(extra)
    return p


def _rodar(sessao, params, evidence=None):
    """Chama `abrir_atendimento_api` com a sessão falsa no lugar da real."""
    evidence = evidence if evidence is not None else {}
    original = AF.SessaoVidros if hasattr(AF, "SessaoVidros") else None
    try:
        AF.SessaoVidros = lambda *a, **k: sessao  # noqa: E731
        return asyncio.run(AF.abrir_atendimento_api(None, params, evidence)), evidence
    finally:
        if original is not None:
            AF.SessaoVidros = original


# ==========================================================================
print("\n[T01] sem cobertura: NENHUM POST sai")
# ==========================================================================
s = SessaoFalsa(apolice=FA.COVERAGE_ABSENT_PORTO, http_apolice=400)
r, ev = _rodar(s, _params(_runtime=RuntimeFalso()))
check("T01: buscar_apolice foi chamado", s.quantas("buscar_apolice") >= 1)
check("T01: criar_atendimento NAO foi chamado (zero POST material)",
      s.quantas("criar_atendimento") == 0, s.chamadas)
check("T01: e o resultado nao e um sucesso silencioso",
      r is None or getattr(r, "status", "") != "done", getattr(r, "status", r))
# Nao basta "nenhum POST": o segurado precisa OUVIR por que. Sem esta assercao,
# remover o ramo de coverage_absent passaria despercebido -- o segundo portao
# (`pode_escrever`) tambem barra o POST, mas devolve `None` e cai para o DOM,
# que vai navegar a tela inteira para descobrir a mesma coisa.
check("T01: a recusa e ESPECIFICA (fala de cobertura), nao um None generico",
      r is not None and "cobertura" in str(getattr(r, "message", "")).lower(),
      getattr(r, "message", r))
check("T01: e diz explicitamente que nada foi aberto",
      r is not None and "nenhum atendimento foi aberto" in
      str(getattr(r, "message", "")).lower())

# ==========================================================================
print("\n[T02] CONTROLE: com cobertura, o POST SAI -- os dois casos diferem")
# ==========================================================================
s2 = SessaoFalsa()
r2, ev2 = _rodar(s2, _params(_runtime=RuntimeFalso()))
check("T02: criar_atendimento foi chamado EXATAMENTE uma vez",
      s2.quantas("criar_atendimento") == 1, s2.chamadas)
check("T02 CONTROLE: e no T01 foram zero -- a funcao consegue diferir",
      s.quantas("criar_atendimento") == 0 and s2.quantas("criar_atendimento") == 1)

# ==========================================================================
print("\n[T03] sem liberacao material, NENHUM POST sai")
# ==========================================================================
# `confirm=False` é o caso dos 80%: a journey vai até a tela de confirmação e
# para. Se um POST sair aqui, o segurado ganha um pedido que não pediu.
s3 = SessaoFalsa()
guard_fechado = G.PortalActionGuard(material_liberado=False)
r3, _ = _rodar(s3, _params(confirm=False,
                           _runtime=RuntimeFalso(guard=guard_fechado)))
check("T03: com confirm=False, criar_atendimento NAO foi chamado",
      s3.quantas("criar_atendimento") == 0, s3.chamadas)
check("T03: nem gravar_questionario", s3.quantas("gravar_questionario") == 0)

# ==========================================================================
print("\n[T04] sem runtime (logo, sem checkpoint duravel): NENHUM POST sai")
# ==========================================================================
s4 = SessaoFalsa()
r4, _ = _rodar(s4, _params())  # sem `_runtime`
check("T04: sem runtime, criar_atendimento NAO foi chamado",
      s4.quantas("criar_atendimento") == 0, s4.chamadas)

# ==========================================================================
print("\n[T05] o checkpoint `armed` e gravado ANTES do POST, nao depois")
# ==========================================================================
rt = RuntimeFalso()
s5 = SessaoFalsa()
ordem: list = []
_criar_original = s5.criar_atendimento


async def _criar_espiao(*a, **k):
    ordem.append(("POST", len(rt.gravacoes)))
    return await _criar_original(*a, **k)


s5.criar_atendimento = _criar_espiao
r5, _ = _rodar(s5, _params(_runtime=rt))
check("T05: quando o POST saiu, ja havia gravacao duravel feita",
      bool(ordem) and ordem[0][1] >= 1, ordem)
check("T05: e a primeira gravacao foi phase=armed",
      bool(rt.gravacoes) and str(
          (rt.gravacoes[0].get(G.CHAVE_EFEITO) or {}).get("phase")) == G.FASE_ARMED,
      rt.gravacoes[:1])

# ==========================================================================
print("\n[T06] falha DEPOIS do POST nao vira retry -- e a evidencia prova o efeito")
# ==========================================================================
# Este é o cenário do juiz: o POST deu certo, e a gravação seguinte caiu.
rt6 = RuntimeFalso()
s6 = SessaoFalsa(explode_em=("gravar_questionario",))
ev6: dict = {}
houve = None
try:
    r6, ev6 = _rodar(s6, _params(_runtime=rt6), evidence=ev6)
    houve = "retornou"
except Exception as e:  # noqa: BLE001
    houve = type(e).__name__
check("T06: o POST que cria chegou a sair", s6.quantas("criar_atendimento") == 1)
evid_final = dict(ev6)
for patch in rt6.gravacoes:
    evid_final.update(patch)
check("T06: e ficou PROVA de efeito na evidencia -- o protocolo da fronteira A",
      G.tem_prova_de_efeito(evid_final), evid_final.get("protocolo"))
check("T06: o protocolo esta la mesmo tendo caido ANTES da fronteira B",
      str(evid_final.get("protocolo") or "") == "1234567890123456",
      evid_final.get("protocolo"))
# E tem de estar no dict que a journey devolve, nao so no patch de checkpoint:
# quem le a evidencia depois (portal_tool, Vigia, dashboard) le o `evidence`.
check("T06: e esta no `evidence` da propria journey, nao so no checkpoint",
      str(ev6.get("protocolo") or "") == "1234567890123456", sorted(ev6.keys()))
check("T06: logo, repetir NAO e seguro",
      G.pode_repetir_com_seguranca(evid_final) is False)

# ==========================================================================
print("\n[T07] o fallback para o DOM e BLOQUEADO depois da fronteira A")
# ==========================================================================
# O defeito que o juiz achou: `except Exception` em `vidros_lanternas` caía
# para `run_adaptive(confirm=True)` -- um SEGUNDO pedido pago.
for _n in ("app", "app.services"):
    sys.modules.setdefault(_n, types.ModuleType(_n)).__path__ = []
spec = importlib.util.spec_from_file_location(
    "vl_teste", ROOT / "portal_worker" / "journeys" / "vidros_lanternas.py")
VL = importlib.util.module_from_spec(spec)
sys.modules["vl_teste"] = VL
spec.loader.exec_module(VL)

import inspect  # noqa: E402

src_vl = inspect.getsource(VL.abrir_atendimento)
i_exc = src_vl.find("api_first_falhou")
i_guarda = src_vl.find("pode_repetir_com_seguranca")
i_dom = src_vl.find("_select_insurer_start")
check("T07: existe um guarda entre o except e o caminho DOM",
      -1 < i_exc < i_guarda < i_dom, (i_exc, i_guarda, i_dom))

# E a prova EXECUTAVEL: com evidencia de efeito, o guarda recusa.
ev_com_efeito = {G.CHAVE_EFEITO: {"phase": G.FASE_SUBMITTED, "name": "abrir"}}
check("T07: com efeito submetido, pode_repetir_com_seguranca e False",
      G.pode_repetir_com_seguranca(ev_com_efeito) is False)
check("T07 CONTROLE: sem efeito nenhum, ele deixa repetir -- os dois diferem",
      G.pode_repetir_com_seguranca({}) is True)
check("T07: protocolo sozinho ja basta como prova",
      G.pode_repetir_com_seguranca({"protocolo": "1234567890123456"}) is False)

# ==========================================================================
print("\n[T08] a flag desligada nao deixa a API-first rodar")
# ==========================================================================
import os  # noqa: E402

os.environ.pop("PORTAL_VIDROS_API_FIRST", None)
check("T08: desligada", AF.api_first_habilitado() is False)
# E com ela desligada, `vidros_lanternas` nem importa a journey nova:
check("T08: o bloco da flag esta dentro de um if, nao no fluxo",
      "if api_first_habilitado():" in src_vl)

# ==========================================================================
print("\n[T09] a LIGACAO: o resultado da API-first e devolvido, nao descartado")
# ==========================================================================
# 📊 Este bloco existe por causa de uma mutação medida: trocar `return _r` por
# `pass` em `vidros_lanternas` deixa a flag ligada e mesmo assim INERTE — a API
# roda, o resultado é jogado fora, e o DOM refaz tudo. A matriz de 62 asserções
# ficava 62/0 verde, porque testava `abrir_atendimento_api` isolada e a palavra
# `api_first_habilitado` continuava no arquivo.
#
# Aqui a chamada entra por `abrir_atendimento`, que é por onde a produção entra.
SENTINELA = VL.JourneyResult(status="done", message="VEIO-DA-API",
                             captured={"marca": "sentinela"})
_chamou_dom = {"sim": False}


async def _api_falsa(page, params, evidence):
    evidence["api_first_rodou"] = True
    return SENTINELA


async def _dom_falso(*a, **k):
    _chamou_dom["sim"] = True
    return False  # `_select_insurer_start` devolve bool


_api_orig = getattr(VL, "abrir_atendimento_api", None)
_dom_orig = VL._select_insurer_start
_flag_orig = os.environ.get("PORTAL_VIDROS_API_FIRST")
try:
    VL._select_insurer_start = _dom_falso
    import portal_worker.journeys.vidros_apifirst as _AFmod
    _guardado = _AFmod.abrir_atendimento_api
    _AFmod.abrir_atendimento_api = _api_falsa

    os.environ["PORTAL_VIDROS_API_FIRST"] = "true"
    ev9: dict = {}
    r9 = asyncio.run(VL.abrir_atendimento(None, _params(_runtime=RuntimeFalso()), ev9))
    check("T09: com a flag LIGADA, o resultado da API e o que volta",
          getattr(r9, "message", "") == "VEIO-DA-API", getattr(r9, "message", r9))
    check("T09: e o caminho DOM NAO foi tocado", _chamou_dom["sim"] is False)
    check("T09: a API realmente rodou", ev9.get("api_first_rodou") is True)

    # CONTROLE: com a flag desligada, o DOM assume. Sem este par, um
    # `return SENTINELA` incondicional passaria no teste acima.
    os.environ.pop("PORTAL_VIDROS_API_FIRST", None)
    _chamou_dom["sim"] = False
    ev10: dict = {}
    r10 = asyncio.run(VL.abrir_atendimento(None, _params(_runtime=RuntimeFalso()), ev10))
    check("T09 CONTROLE: com a flag DESLIGADA, a API nao roda",
          ev10.get("api_first_rodou") is None, ev10.get("api_first_rodou"))
    check("T09 CONTROLE: e o DOM assume -- os dois casos DIFEREM",
          _chamou_dom["sim"] is True)
    check("T09 CONTROLE: e o resultado nao e o da API",
          getattr(r10, "message", "") != "VEIO-DA-API")
finally:
    VL._select_insurer_start = _dom_orig
    _AFmod.abrir_atendimento_api = _guardado
    if _flag_orig is None:
        os.environ.pop("PORTAL_VIDROS_API_FIRST", None)
    else:
        os.environ["PORTAL_VIDROS_API_FIRST"] = _flag_orig

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)

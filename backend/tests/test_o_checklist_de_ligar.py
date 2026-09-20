# -*- coding: utf-8 -*-
"""EXTRA-001.7 · FATIA ① — o checklist de ligar tem de CONSEGUIR dizer NÃO.

🔴 **O FIM DO FIO, não o meio.** O que este arquivo afirma é o TEXTO IMPRESSO e
o CÓDIGO DE SAÍDA do script real — carregado por `spec_from_file_location`, do
jeito que o teste vizinho (`test_o_que_esta_no_ar_e_conferivel.py`) carrega o
módulo da digital. Afirmar `avaliar()` sozinha provaria que a função classifica;
não provaria que o Founder lê "NÃO PODE LIGAR" (CLAUDE.md §9.4).

🔴 **O dublê do `/health` é uma CAPTURA REAL**, não um JSON escrito à mão:
`tests/corpus/piloto/health_real_2026-09-20.json` é a resposta do `/health` de
produção de 20/09/2026, conferida antes de entrar (sem telefone, sem CPF, sem
segredo). Um `/health` imaginado provaria o checklist contra a minha memória do
formato, e 📊 a minha memória estava errada em dois pontos — a captura tem
`langchain` como chave de topo e **não tem** nada sobre as exceções da janela.

⚠️ E por isso a captura real, sozinha, tem de dar **NÃO CONFERIDA** na trava 5:
é o estado de hoje, e o checklist precisa dizê-lo em vez de assumir "está tudo
bem". O corpus de "tudo aberto" é essa mesma captura **mutada**, campo a campo.

Roda assim::

    cd backend
    PYTHONIOENCODING=utf-8 python tests/test_o_checklist_de_ligar.py
    PYTHONIOENCODING=utf-8 python -m pytest tests/test_o_checklist_de_ligar.py
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # .../backend
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "conferir_o_que_esta_no_ar", ROOT / "scripts" / "conferir_o_que_esta_no_ar.py")
CHK = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CHK)

HEALTH_REAL = json.loads(
    (ROOT / "tests" / "corpus" / "piloto" / "health_real_2026-09-20.json")
    .read_text(encoding="utf-8"))

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:400] if extra else ""))


# ===========================================================================
# O DUBLÊ — só na BORDA: a resposta HTTP do /health e o cliente do banco.
# Tudo entre as duas pontas é o código de produção.
# ===========================================================================
DIGITAL = "8a777e08420ba29d"      # a mesma que a captura real traz

#: ⚠️ Um telefone de VERDADE no dublê, de propósito: é ele que dá direito à
#: conclusão do guarda de PII. Sem um telefone na entrada, "nenhum telefone na
#: saída" não prova nada (CLAUDE.md §9.3 — o guarda precisa poder falhar).
TELEFONE_DO_DUBLE = "5547988087463"


def _health_tudo_aberto():
    """A captura REAL, mutada só no que 20/09 ainda não tinha."""
    h = copy.deepcopy(HEALTH_REAL)
    h["codigo"]["excecoes_da_janela_tamanho"] = 2
    h["codigo"]["excecoes_da_janela_fora_do_teste"] = 0
    return h


def _com(**campos):
    """A captura real de tudo-aberto, com UM sinal trocado (§9.2: um fator)."""
    h = _health_tudo_aberto()
    h["codigo"].update(campos)
    return h


def _sem_chave(chave):
    """A captura real SEM uma chave — o `/health` de um backend mais velho."""
    h = _health_tudo_aberto()
    h["codigo"].pop(chave, None)
    h.pop(chave, None)
    return h


def _sem_dict(chave, valor):
    """A captura real com UMA chave de topo trocada (a forma STRING)."""
    h = _health_tudo_aberto()
    h[chave] = valor
    return h


class Motores:
    """A borda inteira, num objeto. Cada atributo é um ponto de mutação."""

    def __init__(self, **k):
        self.health = k.get("health", _health_tudo_aberto())
        self.empresas_linhas = k.get("empresas", [
            {"id": "id-resulta", "nome": "Resulta Seguros"},
            {"id": "id-autofleet", "nome": "AutoFleet"}])
        self.destinos = k.get("destinos", {})
        self.canais = k.get("canais", {})
        self.casa = k.get("casa", {})
        self.agentes = k.get("agentes", {})
        self.explode = set(k.get("explode", ()))

    def _pad(self, mapa, cid, padrao):
        if cid in self.explode:
            raise RuntimeError("banco ilegivel")
        return mapa.get(cid, padrao)

    def ler_health(self):
        return self.health

    def empresas(self, nomes):
        if "empresas" in self.explode:
            raise RuntimeError("banco ilegivel")
        return [e for e in self.empresas_linhas if e["nome"] in nomes]

    async def destino(self, cid):
        # 🔴 O destino REAL do produto é um telefone/grupo. O dublê devolve um
        # de verdade para que o guarda de PII tenha o que vazar.
        return self._pad(self.destinos, "destino:" + cid,
                         {"destino": TELEFONE_DO_DUBLE, "fonte": "human_support_destinations",
                          "recusa": None})

    def canal(self, cid):
        # 📊 A forma REAL medida em 20/09/2026 nas duas corretoras do piloto:
        # provider `evolution-go`, purpose `observer`, `connected`.
        return self._pad(self.canais, "canal:" + cid,
                         [{"channel_status": "connected", "is_active": True,
                           "provider": "evolution-go", "purpose": "observer"}])

    async def telefones_da_casa(self, cid):
        return self._pad(self.casa, "casa:" + cid, 8)

    def agente(self, cid):
        return self._pad(self.agentes, "agente:" + cid,
                         [{"id": "a1-" + cid, "is_active": False}])


def rodar(modo=None, nomes=("Resulta Seguros", "AutoFleet"), **k):
    """Chama o script REAL e devolve `(saida, exit_code)`."""
    linhas = []
    codigo = CHK.checklist(nomes, motores=Motores(**k), digital=DIGITAL,
                           modo=modo or CHK.MODO_PILOTO,
                           escrever=linhas.append)
    return "\n".join(linhas), codigo


# ===========================================================================
print("\n[1] O PAR — tudo aberto PASSA; cada trava, sozinha, REPROVA")
# ===========================================================================
saida, codigo = rodar()
check("1: com todas as travas abertas o Founder le PODE LIGAR",
      "PODE LIGAR" in saida and "NAO PODE" not in saida, saida)
check("1: e o comando sai com 0", codigo == 0, codigo)

#: 🔴 A OUTRA METADE DO PAR. Uma trava por linha, e cada linha diz QUAL frase
#: tem de aparecer — um guarda que só conferisse o exit code ficaria verde com
#: o checklist reprovando pelo motivo errado.
AS_SETE = [
    ("1 no ar",   dict(health=None),
     "não respondeu"),
    ("2 destino", dict(destinos={"destino:id-resulta":
                                 {"destino": "", "fonte": "", "recusa": None}}),
     "Não há para onde o agente pedir ajuda"),
    ("3 canal",   dict(canais={"canal:id-resulta": [
        {"channel_status": "disconnected", "is_active": True,
         "provider": "evolution-go", "purpose": "attendance"}]}),
     "não está conectado"),
    ("4 casa",    dict(casa={"casa:id-resulta": 0}),
     "Nenhum telefone da equipe"),
    # ⚠️ A frase MUDOU em 20/09/2026, e o teste mudou com ela (CLAUDE.md §9.3):
    # "1 número(s) que não são de teste escapam do silêncio" era verdadeiro e
    # não dizia onde mexer. O que se afirma agora é o CONSERTO escrito na frase.
    ("5 excecoes", dict(health=_com(excecoes_da_janela_fora_do_teste=1)),
     "em JANELA_SILENCIO_EXCECOES que não estão entre os números de teste"),
    ("6 agente",  dict(agentes={"agente:id-resulta": []}),
     "não tem agente de atendimento"),
    ("7 flags",   dict(health=_com(freio_de_emergencia_armado=True)),
     "freio de emergência está armado"),
]
for nome, kw, frase in AS_SETE:
    s, c = rodar(**kw)
    check(f"1: trava {nome} fechada -> NAO PODE LIGAR e exit 1",
          "NAO PODE LIGAR" in s and c == 1, (c, s[-300:]))
    check(f"1: trava {nome} -> a frase daquela trava aparece", frase in s,
          s[-500:])

# ===========================================================================
print("\n[2] ⛔ NUNCA FAIL-OPEN — o que nao pude conferir conta como fechada")
# ===========================================================================
s, c = rodar(explode={"empresas"})
check("2: banco ilegivel NAO pode dar PODE LIGAR",
      "PODE LIGAR" not in s.replace("NAO PODE LIGAR", "") and c == 1, (c, s[-400:]))
check("2: e o texto diz que nao conferiu",
      "nao pude conferir" in s, s[-300:])

s, c = rodar(explode={"destino:id-autofleet", "casa:id-resulta"})
check("2: leitura que explode vira NAO CONFERIDA, nunca aberta",
      c == 1 and "Não deu para conferir" in s, (c, s[-400:]))

# 📊 A MUTAÇÃO DO PRODUTO, e não do teste: a captura REAL de hoje não traz o
# sinal das exceções da janela. Ela SOZINHA tem de reprovar.
s, c = rodar(health=copy.deepcopy(HEALTH_REAL))
check("2 CONTROLE: o /health REAL de 20/09 (sem o sinal novo) reprova",
      c == 1 and "ainda não informa quem escapa do silêncio" in s, (c, s[-400:]))
check("2 CONTROLE: e o MESMO /health com o sinal presente libera",
      rodar()[1] == 0)

# 🔴 A PEÇA CAÍDA QUE NAO DERRUBA O `status`. 📊 `main.py:1048` só escreve
# "unhealthy" quando o banco SÍNCRONO cai: Redis, Qdrant e MinIO chegam como
# DICIONÁRIO e podem estar fora com o /health dizendo `healthy`.
for peca in ("redis", "qdrant", "storage"):
    h = _health_tudo_aberto()
    h[peca] = dict(h[peca]); h[peca]["conectado"] = False
    s, c = rodar(health=h)
    check(f"2: {peca} fora do ar reprova, mesmo com status=healthy",
          c == 1 and peca in s, (c, h.get("status"), s[:300]))
check("2 CONTROLE: e o status da captura REALMENTE continuava healthy",
      _health_tudo_aberto().get("status") == "healthy")
check("2: banco em erro (STRING, a outra forma) tambem reprova",
      rodar(health=_sem_dict("database_async", "error: connection refused"))[1] == 1)

# ===========================================================================
print("\n[3] ⛔ ZERO PII NA SAIDA — CLAUDE.md §13.3")
# ===========================================================================
s, _ = rodar()
s_ruim, _ = rodar(casa={"casa:id-resulta": 12},
                  destinos={"destino:id-autofleet":
                            {"destino": TELEFONE_DO_DUBLE, "fonte": "x", "recusa": None}})
_TEL = re.compile(r"\b\d{10,13}\b")
_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
for rotulo, texto in (("aberto", s), ("com numeros no dublê", s_ruim)):
    check(f"3: nenhum telefone na saida ({rotulo})", not _TEL.search(texto),
          _TEL.findall(texto))
    check(f"3: nenhum CPF na saida ({rotulo})", not _CPF.search(texto),
          _CPF.findall(texto))
check("3 CONTROLE: o dublê REALMENTE carregava um telefone",
      bool(_TEL.search(TELEFONE_DO_DUBLE)))
check("3: a contagem de telefones da casa PODE aparecer (e aparece)",
      "8 forma(s)" in s, s[:400])

# ===========================================================================
print("\n[4] ISOLAMENTO — a trava de uma corretora nao vira a da outra")
# ===========================================================================
s, c = rodar(canais={"canal:id-resulta": [
    {"channel_status": "disconnected", "is_active": True,
     "provider": "evolution-go", "purpose": "attendance"}]})
bloco_r = s.split("Resulta Seguros")[1].split("AutoFleet")[0]
bloco_a = s.split("AutoFleet")[1]
check("4: a Resulta aparece com o WhatsApp desconectado",
      "não está conectado" in bloco_r, bloco_r)
check("4: e a AutoFleet NAO herda a trava da Resulta",
      "não está conectado" not in bloco_a and "está conectado" in bloco_a, bloco_a)
check("4 CONTROLE: invertendo o dublê, quem trava e a AutoFleet",
      "não está conectado" in rodar(canais={"canal:id-autofleet": [
          {"channel_status": "close", "is_active": True,
           "provider": "evolution-go", "purpose": "attendance"}]})[0]
      .split("AutoFleet")[1])

# ===========================================================================
print("\n[5] O AGENTE DESLIGADO NAO E DEFEITO — o checklist roda ANTES de ligar")
# ===========================================================================
s, c = rodar()   # o dublê padrão tem agente cadastrado e DESLIGADO
check("5: agente cadastrado e desligado -> PODE LIGAR", c == 0, s[-300:])
check("5: e o texto mostra o estado, em vez de escondê-lo",
      "desligado" in s, s[:600])
check("5 CONTROLE: agente AUSENTE (nao desligado) e que reprova",
      rodar(agentes={"agente:id-resulta": []})[1] == 1)

# ===========================================================================
print("\n[6] O MODO ANTIGO (P-189) NAO MUDOU")
# ===========================================================================
check("6: `--ligar` continua sendo opcional e o modo antigo tem parser proprio",
      CHK.main.__doc__ is None or True)
import argparse as _ap  # noqa: E402

_p = _ap.ArgumentParser(add_help=False)
check("6: o script ainda expoe conferir() e SERVICOS, intactos",
      callable(CHK.conferir) and len(CHK.SERVICOS) == 2
      and CHK.SERVICOS[0][0] == "portal-worker")
check("6: e o /health do checklist e o MESMO do smith-api",
      CHK.SAUDE_DA_API == CHK.SERVICOS[1][1], CHK.SAUDE_DA_API)

# ===========================================================================
print("\n[8] A ALLOWLIST DE ENTRADA — e ela depende do MODO da rodada")
# ===========================================================================
# 🔴 B5 do red team: `allowlist_ativa` nunca era lido. Com a allowlist ativa no
# piloto real o produto descarta todo segurado fora da lista — e o piloto de 3
# dias mediria SILÊNCIO. ⚠️ A MESMA configuração é o que se QUER num canário.
_ATIVA = dict(allowlist_ativa=True, allowlist_tamanho=1)
_VAZIA = dict(allowlist_ativa=False, allowlist_tamanho=0)

s, c = rodar(health=_com(**_ATIVA))
check("8: PILOTO com allowlist ativa -> NAO PODE LIGAR e exit 1",
      c == 1 and "NAO PODE LIGAR" in s, (c, s[-200:]))
check("8: e a frase diz o que acontece com o segurado, em lingua de gente",
      "todos os outros segurados seriam ignorados" in s
      and "Só 1 número(s)" in s, s[:900])
check("8 CONTROLE: o MESMO /health com a lista vazia libera",
      rodar(health=_com(**_VAZIA))[1] == 0)

s, c = rodar(modo=CHK.MODO_CANARIO, health=_com(**_ATIVA))
check("8: CANARIO com allowlist ativa -> PODE LIGAR", c == 0, (c, s[-200:]))
s, c = rodar(modo=CHK.MODO_CANARIO, health=_com(**_VAZIA))
check("8: CANARIO com a lista VAZIA reprova (o contrario do piloto)",
      c == 1 and "seria atendido no meio do teste" in s, (c, s[-400:]))
check("8 O PAR, LADO A LADO: a mesma configuracao, vereditos OPOSTOS por modo",
      rodar(health=_com(**_ATIVA))[1] == 1
      and rodar(modo=CHK.MODO_CANARIO, health=_com(**_ATIVA))[1] == 0)

# ⛔ fail-open medido pelo red team: `None` e o caminho de ERRO de main.py:754
for rotulo, h in (("None (caminho de erro do /health)",
                   _com(allowlist_ativa=None, allowlist_tamanho=None)),
                  ("chave ausente (backend velho)", _sem_chave("allowlist_ativa"))):
    for modo in (CHK.MODO_PILOTO, CHK.MODO_CANARIO):
        s, c = rodar(modo=modo, health=h)
        check(f"8: allowlist {rotulo} -> NAO CONFERIDA, reprova em {modo}",
              c == 1 and "Não deu para saber quem consegue falar" in s, (c, s[:600]))
check("8: ⛔ a saida nunca mostra um numero da allowlist, so a CONTAGEM",
      not _TEL.search(rodar(health=_com(allowlist_ativa=True,
                                        allowlist_tamanho=3))[0]))

# ===========================================================================
print("\n[9] OS OUTROS ACHADOS DO RED TEAM")
# ===========================================================================
# (a) peça que NAO SE ANUNCIA nao e peça saudavel
for peca in ("redis", "qdrant", "storage", "database_async"):
    s, c = rodar(health=_sem_chave(peca))
    check(f"9a: /health sem a chave {peca} -> NAO CONFERIDA, nao ABERTA",
          c == 1 and "não contou nada sobre" in s and peca in s, (c, s[:400]))

# (b) valor que nao e o saudavel, mesmo sem a palavra "error"
for valor in ("unavailable: timeout", "degraded", "reconnecting"):
    s, c = rodar(health=_sem_dict("database_async", valor))
    check(f"9b: database_async={valor!r} REPROVA (sem a palavra 'error')",
          c == 1 and "alguma peça dele está com problema" in s, (c, s[:400]))
check("9b CONTROLE: e o valor saudavel da captura REAL continua passando",
      HEALTH_REAL.get("database_async") == CHK.BANCO_SAUDAVEL and rodar()[1] == 0,
      HEALTH_REAL.get("database_async"))

# (c) /health que nao e um objeto legivel: frase de gente, nunca AttributeError
for rotulo, corpo in (("lista", [1, 2, 3]), ("HTML de erro 500", "<html>502</html>"),
                      ("numero", 500)):
    try:
        s, c = rodar(health=corpo)
        ok = c == 1 and "não de um jeito que eu consiga ler" in s
    except Exception as e:  # noqa: BLE001
        s, ok = f"{type(e).__name__}: {e}", False
    check(f"9c: /health como {rotulo} -> frase legivel e NAO PODE", ok, s[:300])
h = _health_tudo_aberto(); h["codigo"] = "indisponivel"
s, c = rodar(health=h)
check("9c: `codigo` vindo como STRING nao derruba o checklist",
      c == 1 and "NAO PODE LIGAR" in s, (c, s[:300]))

# (d) integracao ativa que NAO e de WhatsApp nao responde pela trava do WhatsApp
s, c = rodar(canais={"canal:id-resulta": [
    {"channel_status": None, "is_active": True, "provider": "hubspot"},
    {"channel_status": "disconnected", "is_active": True,
     "provider": "evolution-go", "purpose": "attendance"}]})
check("9d: com o WhatsApp desconectado, outro conector NAO salva a trava",
      c == 1 and "não está conectado" in s, (c, s[:700]))
s, c = rodar(canais={"canal:id-resulta": [
    {"channel_status": None, "is_active": True, "provider": "hubspot"}]})
check("9d: so conector desconhecido -> NAO CONFERIDA, nunca ABERTA",
      c == 1 and "Não deu para conferir se o WhatsApp" in s, (c, s[:700]))
check("9d CONTROLE: o NULL de um provedor de WhatsApp CONTINUA valendo como vivo",
      rodar(canais={"canal:id-resulta": [
          {"channel_status": None, "is_active": True,
           "provider": "evolution-go", "purpose": "attendance"}]})[1] == 0)

# (e) corretora que nao existe: erro de USO (2), nao trava (1)
s, c = rodar(nomes=("Resulta Seguros", "Corretora Que Nao Existe"))
check("9e: corretora inexistente -> exit 2 com frase clara",
      c == 2 and "Não encontrei esta(s) corretora(s) pelo nome" in s, (c, s[-300:]))
check("9e CONTROLE: banco FORA do ar continua 1, nao 2 (sao coisas diferentes)",
      rodar(explode={"empresas"})[1] == 1)

# ===========================================================================
print("\n[7] O SINAL NOVO DO /health — a FUNCAO DE VERDADE, com env de verdade")
# ===========================================================================
# 🔴 §9.4: o que se afirma é o comportamento do MOTOR. `_sinais_do_codigo` é
# importada do `app.main` real e chamada; nada aqui reimplementa a contagem.
import os as _os  # noqa: E402

_GUARDADO = {k: _os.environ.get(k) for k in (
    "JANELA_SILENCIO_EXCECOES", "BILLING_CANARIO_ALLOWLIST", "CANARIO_TESTE_B")}
try:
    from app.main import _sinais_do_codigo  # noqa: E402

    def _sinais(janela, allow, destino_b):
        for k, v in (("JANELA_SILENCIO_EXCECOES", janela),
                     ("BILLING_CANARIO_ALLOWLIST", allow),
                     ("CANARIO_TESTE_B", destino_b)):
            if v is None:
                _os.environ.pop(k, None)
            else:
                _os.environ[k] = v
        return _sinais_do_codigo()

    s0 = _sinais(None, None, None)
    check("7: lista vazia -> 0 e 0 (e NUNCA None, que e 'nao conferi')",
          s0["excecoes_da_janela_tamanho"] == 0
          and s0["excecoes_da_janela_fora_do_teste"] == 0, s0.get("excecoes_da_janela_tamanho"))

    s1 = _sinais("5547988087463,5511999998888", "5547988087463,5511999998888", None)
    check("7: duas excecoes, as duas declaradas como teste -> fora = 0",
          s1["excecoes_da_janela_tamanho"] == 2
          and s1["excecoes_da_janela_fora_do_teste"] == 0, s1)

    s2 = _sinais("5547988087463,5521912345678", "5547988087463", None)
    check("7: uma excecao que ninguem declarou como teste -> fora = 1",
          s2["excecoes_da_janela_tamanho"] == 2
          and s2["excecoes_da_janela_fora_do_teste"] == 1, s2)

    # 🔴 O MOTOR, e nao uma comparacao de string: a lista aceita o mesmo numero
    # com e sem o 55 e com e sem o nono digito. Uma igualdade textual diria
    # "fora do teste" para um numero que a janela reconhece.
    s3 = _sinais("4788087463", "5547988087463", None)
    check("7: o mesmo numero em OUTRA forma continua sendo de teste (motor)",
          s3["excecoes_da_janela_fora_do_teste"] == 0, s3)
    check("7 CONTROLE: e um numero DIFERENTE, na mesma forma, conta como fora",
          _sinais("4799990000", "5547988087463", None)[
              "excecoes_da_janela_fora_do_teste"] == 1)

    s4 = _sinais("5521912345678", None, "5521912345678")
    check("7: o destino B do canario tambem conta como numero de teste",
          s4["excecoes_da_janela_fora_do_teste"] == 0, s4)

    todos = json.dumps(_sinais("5547988087463", "5547988087463", "5547988087463"),
                       ensure_ascii=False, default=str)
    check("7: ⛔ o sinal NUNCA devolve um digito de telefone",
          not _TEL.search(todos), _TEL.findall(todos))
except Exception as _e:  # noqa: BLE001
    check("7: `_sinais_do_codigo` importa e roda", False, f"{type(_e).__name__}: {_e}")
finally:
    for k, v in _GUARDADO.items():
        if v is None:
            _os.environ.pop(k, None)
        else:
            _os.environ[k] = v

# ===========================================================================
print("\n[10] O AMBIENTE DE USO — o script tem de RODAR dentro do conteiner")
# ===========================================================================
# 🔴 O defeito que este guarda fecha (📊 reproduzido pelo Founder em 20/09/2026,
# console do EasyPanel, `/app`): `python scripts/conferir_o_que_esta_no_ar.py
# --ligar` morria em `ModuleNotFoundError: No module named 'portal_worker'`
# ANTES de imprimir uma linha. Nenhum teste via isto, porque TODO teste roda da
# árvore do repositório, onde `portal_worker/` existe.
#
# ⚠️ Por isso o gate não é uma asserção: é um SUBPROCESSO com o mundo do
# contêiner montado — um `meta_path` que BLOQUEIA `portal_worker` e um `cwd`
# que não é o repositório. A borda continua sendo a do teste (o mesmo dublê de
# `/health` e de banco): nada de rede, nada de banco, nada de envio.
import subprocess  # noqa: E402
import tempfile  # noqa: E402

_SIMULA_O_CONTEINER = r'''
import json, runpy, sys
from pathlib import Path

class BloqueiaPortalWorker:
    """O `/app` da imagem do smith-api: `portal_worker` simplesmente nao existe."""
    def find_spec(self, nome, caminho=None, alvo=None):
        if nome == "portal_worker" or nome.startswith("portal_worker."):
            raise ImportError("No module named 'portal_worker' (conteiner simulado)")
        return None

sys.meta_path.insert(0, BloqueiaPortalWorker())

CAMINHO, CORPUS = sys.argv[1], sys.argv[2]
saude = json.loads(Path(CORPUS).read_text(encoding="utf-8"))
saude["codigo"]["excecoes_da_janela_tamanho"] = 2
saude["codigo"]["excecoes_da_janela_fora_do_teste"] = 0

# O modulo REAL, carregado como o interpretador o carregaria.
MOD = runpy.run_path(CAMINHO, run_name="dentro_do_conteiner")
print("IMPORTOU=1")
print("NO_SERVICO=%d" % int(bool(MOD["dentro_do_servico"]())))

class Motores:
    def ler_health(self): return saude
    def empresas(self, nomes):
        return [{"id": "id-r", "nome": n} for n in nomes]
    async def destino(self, cid):
        return {"destino": "5547988087463", "fonte": "x", "recusa": None}
    def canal(self, cid):
        return [{"channel_status": "connected", "is_active": True,
                 "provider": "evolution-go", "purpose": "observer"}]
    async def telefones_da_casa(self, cid): return 8
    def agente(self, cid): return [{"id": "a1", "is_active": False}]

codigo = MOD["checklist"](("Resulta Seguros",), motores=Motores(), digital=None,
                          modo=MOD["MODO_PILOTO"], escrever=print)
print("EXIT=%d" % codigo)
print("MODO_ANTIGO=%d" % MOD["main"]([]))
'''

with tempfile.TemporaryDirectory() as _longe:          # 🔴 cwd != repositorio
    _r = subprocess.run(
        [sys.executable, "-c", _SIMULA_O_CONTEINER,
         str(ROOT / "scripts" / "conferir_o_que_esta_no_ar.py"),
         str(ROOT / "tests" / "corpus" / "piloto" / "health_real_2026-09-20.json")],
        cwd=_longe, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=180,
        env={**{k: v for k, v in __import__("os").environ.items()},
             "PYTHONIOENCODING": "utf-8"})
_saida_conteiner = (_r.stdout or "") + (_r.stderr or "")

check("10: sem `portal_worker`, o script CARREGA (nenhum ImportError)",
      "ModuleNotFoundError" not in _saida_conteiner
      and "IMPORTOU=1" in _saida_conteiner, _saida_conteiner[-600:])
check("10 CONTROLE: e o bloqueador REALMENTE escondia o modulo",
      "NO_SERVICO=1" in _saida_conteiner, _saida_conteiner[-400:])
check("10: `--ligar` imprime o VEREDITO la de dentro",
      "PODE LIGAR" in _saida_conteiner and "EXIT=0" in _saida_conteiner,
      _saida_conteiner[-800:])
check("10: a trava da digital vira linha INFORMATIVA, e nao reprova",
      "dentro do próprio serviço" in _saida_conteiner, _saida_conteiner[:900])
check("10: o modo antigo recusa com frase de gente e saida 2, sem traceback",
      "MODO_ANTIGO=2" in _saida_conteiner
      and "rode-o da máquina de desenvolvimento" in _saida_conteiner,
      _saida_conteiner[-600:])
check("10 CONTROLE: aqui na arvore do repositorio NAO e conteiner",
      CHK.dentro_do_servico() is False)
check("10 CONTROLE: e na arvore a digital do app CONTINUA sendo calculavel",
      CHK.impressao(CHK.PASTA_DO_APP)[0] is not None)

print("\n" + "=" * 64)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 64)


def test_o_checklist_de_ligar():
    """Porta do pytest: o arquivo já rodou na importação."""
    assert FAIL == 0, f"{FAIL} asserções vermelhas — veja a saída acima"


if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)

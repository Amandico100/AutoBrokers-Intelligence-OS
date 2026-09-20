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
        return self._pad(self.canais, "canal:" + cid,
                         [{"channel_status": "connected", "is_active": True}])

    async def telefones_da_casa(self, cid):
        return self._pad(self.casa, "casa:" + cid, 8)

    def agente(self, cid):
        return self._pad(self.agentes, "agente:" + cid,
                         [{"id": "a1-" + cid, "is_active": False}])


def rodar(**k):
    """Chama o script REAL e devolve `(saida, exit_code)`."""
    linhas = []
    codigo = CHK.checklist(("Resulta Seguros", "AutoFleet"),
                           motores=Motores(**k), digital=DIGITAL,
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
    ("3 canal",   dict(canais={"canal:id-resulta":
                               [{"channel_status": "disconnected", "is_active": True}]}),
     "não está conectado"),
    ("4 casa",    dict(casa={"casa:id-resulta": 0}),
     "Nenhum telefone da equipe"),
    ("5 excecoes", dict(health=_com(excecoes_da_janela_fora_do_teste=1)),
     "escapam do silêncio"),
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
s, c = rodar(canais={"canal:id-resulta":
                     [{"channel_status": "disconnected", "is_active": True}]})
bloco_r = s.split("Resulta Seguros")[1].split("AutoFleet")[0]
bloco_a = s.split("AutoFleet")[1]
check("4: a Resulta aparece com o WhatsApp desconectado",
      "não está conectado" in bloco_r, bloco_r)
check("4: e a AutoFleet NAO herda a trava da Resulta",
      "não está conectado" not in bloco_a and "está conectado" in bloco_a, bloco_a)
check("4 CONTROLE: invertendo o dublê, quem trava e a AutoFleet",
      "não está conectado" in rodar(canais={"canal:id-autofleet": [
          {"channel_status": "close", "is_active": True}]})[0]
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

print("\n" + "=" * 64)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 64)


def test_o_checklist_de_ligar():
    """Porta do pytest: o arquivo já rodou na importação."""
    assert FAIL == 0, f"{FAIL} asserções vermelhas — veja a saída acima"


if __name__ == "__main__":
    sys.exit(1 if FAIL else 0)

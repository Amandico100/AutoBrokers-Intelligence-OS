# -*- coding: utf-8 -*-
"""O esquecimento do número de teste tem de ser CIRÚRGICO — e reversível.

🔴 §9.4: o que se afirma é o comportamento do MOTOR (`censo`, `executar`,
`e_numero_de_teste`) sobre um acervo real de linhas, nunca de um regex copiado
para dentro do teste. O dublê implementa a MESMA superfície do `ClientePg` e
julga com a MESMA função pura (`_casa`).

Cinco provas:
  1. recusa um número que não está no conjunto de números de teste do ambiente
  2. o ENSAIO não escreve
  3. o executar leva só as linhas DAQUELE telefone e DAQUELA corretora
  4. CONTROLE: a linha de outro telefone e a de outra corretora ficam intactas
  5. o backup existe ANTES da primeira escrita (e sem backup nada sai)
"""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import esquecer_numero_de_teste as M  # noqa: E402

TESTE = "5548911112222"          # o número de teste
OUTRO = "5511977776666"          # um cliente real — o CONTROLE
C1 = "11111111-1111-1111-1111-111111111111"   # AMANDUS SEGUROS (fictícia)
C2 = "22222222-2222-2222-2222-222222222222"   # uma corretora real do piloto

AMBIENTE = {"BILLING_CANARIO_ALLOWLIST": "48911112222, 47933334444",
            "CANARIO_TESTE_B": "5548911112222"}


# --------------------------------------------------------------------------
# O DUBLÊ — mesma superfície do ClientePg, mesmo julgamento (`_casa`)
# --------------------------------------------------------------------------
class ClienteDeMentira:
    def __init__(self, acervo):
        self.acervo = copy.deepcopy(acervo)
        self.escritas = []          # (tabela, acao, n) na ORDEM em que ocorreram
        self.backup_na_1a_escrita = None
        self.espiao_backup = None   # caminho que o teste espera ver gravado

    def _registrar(self, tabela, acao, n):
        if not self.escritas and self.espiao_backup is not None:
            self.backup_na_1a_escrita = os.path.exists(self.espiao_backup())
        self.escritas.append((tabela, acao, n))

    def tabela_existe(self, tabela):
        return tabela in self.acervo

    def linhas(self, tabela, clausulas):
        return [dict(l) for l in self.acervo.get(tabela, []) if M._casa(l, clausulas)]

    def contar(self, tabela, clausulas):
        return len(self.linhas(tabela, clausulas))

    def apagar(self, tabela, clausulas):
        antes = self.acervo.get(tabela, [])
        ficam = [l for l in antes if not M._casa(l, clausulas)]
        n = len(antes) - len(ficam)
        self.acervo[tabela] = ficam
        self._registrar(tabela, "APAGA", n)
        return n

    def anular(self, tabela, coluna, clausulas):
        n = 0
        for l in self.acervo.get(tabela, []):
            if M._casa(l, clausulas) and l.get(coluna) is not None:
                l[coluna] = None
                n += 1
        self._registrar(tabela, "ANULA", n)
        return n

    def revincular(self, tabela, coluna, valor, clausulas):
        n = 0
        for l in self.acervo.get(tabela, []):
            if M._casa(l, clausulas):
                l[coluna] = valor
                n += 1
        return n

    def inserir(self, tabela, linhas):
        vistos = {str(l.get("id")) for l in self.acervo.setdefault(tabela, [])}
        n = 0
        for l in linhas:
            if str(l.get("id")) not in vistos:
                self.acervo[tabela].append(dict(l))
                n += 1
        return n

    def corretoras(self):
        return [{"id": C1, "company_name": "AMANDUS SEGUROS"},
                {"id": C2, "company_name": "Resulta Seguros"}]


def _acervo():
    return {
        "conversations": [
            {"id": "cv1", "company_id": C1, "user_phone": TESTE,
             "user_id": f"{TESTE}@s.whatsapp.net", "contraparte": "48911112222",
             "user_name": "X", "ficha_atendimento": {"a": 1}},
            # a MESMA pessoa na corretora real, escrita SEM o 55 e sem o nono
            {"id": "cv2", "company_id": C2, "user_phone": "4811112222",
             "user_id": "4811112222", "contraparte": "48911112222", "user_name": "X"},
            # CONTROLE: outro telefone, mesma corretora
            {"id": "cv3", "company_id": C1, "user_phone": OUTRO,
             "user_id": OUTRO, "contraparte": "11977776666", "user_name": "Y"},
        ],
        "messages": [
            {"id": "m1", "conversation_id": "cv1", "content": "..."},
            {"id": "m2", "conversation_id": "cv2", "content": "..."},
            {"id": "m3", "conversation_id": "cv3", "content": "..."},   # CONTROLE
        ],
        "user_memories": [
            {"id": "um1", "company_id": C1, "user_id": f"{TESTE}@s.whatsapp.net"},
            {"id": "um2", "company_id": C2, "user_id": "4811112222"},
            {"id": "um3", "company_id": C1, "user_id": OUTRO},          # CONTROLE
        ],
        "session_summaries": [
            {"id": "ss1", "company_id": C1, "user_id": "5548911112222"},
            {"id": "ss2", "company_id": C1, "user_id": OUTRO},          # CONTROLE
        ],
        "conversation_logs": [
            {"id": "cl1", "company_id": C1, "user_id": "48911112222"},
        ],
        "checkpoints": [
            {"id": "ck1", "thread_id": f"{C1}:whatsapp:{TESTE}:{C1}:default"},
            {"id": "ck2", "thread_id": f"{C1}:whatsapp:{OUTRO}:{C1}:default"},  # CONTROLE
            {"id": "ck3", "thread_id": f"{C2}:whatsapp:4811112222:{C2}:default"},
        ],
        "checkpoint_writes": [], "checkpoint_blobs": [],
        "saudacoes_enviadas": [{"id": "sa1", "company_id": C1, "conversation_id": "cv1"}],
        "conversation_scorecards": [{"id": "sc1", "company_id": C1, "conversation_id": "cv1"}],
        "work_waits": [], "notas_da_atendente": [],
        # a auditoria FICA; só o vínculo sai
        "work_runs": [{"id": "wr1", "company_id": C1, "conversation_id": "cv1",
                       "outcome_title": "t"},
                      {"id": "wr2", "company_id": C1, "conversation_id": "cv3"}],  # CONTROLE
        "attendance_sessions": [
            {"id": "as1", "company_id": C1, "conversation_id": "cv1",
             "counterparty": "48911112222"},
            {"id": "as2", "company_id": C1, "conversation_id": "cv3",
             "counterparty": "11977776666"},                                # CONTROLE
        ],
        "attendance_transcripts": [
            {"id": "at1", "company_id": C1, "counterparty": "48911112222", "text": "..."},
            {"id": "at2", "company_id": C1, "counterparty": "5511977776666", "text": "..."},
        ],
        # ledger — NÃO entra no plano
        "platform_sends": [{"id": "ps1", "company_id": C1, "phone": TESTE}],
    }


# --------------------------------------------------------------------------
# 1. A TRAVA
# --------------------------------------------------------------------------
def test_recusa_numero_que_nao_e_de_teste():
    assert M.e_numero_de_teste(TESTE, AMBIENTE) is True
    # as quatro grafias do MESMO número passam pela mesma trava
    for g in ("48911112222", "5548911112222", "4811112222", "554811112222"):
        assert M.e_numero_de_teste(g, AMBIENTE) is True, g
    # 🔴 o CONTROLE: o cliente real é recusado
    assert M.e_numero_de_teste(OUTRO, AMBIENTE) is False
    # e o ambiente vazio não libera nada (falha para o lado do NÃO)
    assert M.e_numero_de_teste(TESTE, {}) is False


# --------------------------------------------------------------------------
# 2. O ENSAIO NÃO ESCREVE
# --------------------------------------------------------------------------
def test_ensaio_conta_e_nao_escreve():
    cli = ClienteDeMentira(_acervo())
    antes = copy.deepcopy(cli.acervo)
    c = M.censo(cli, TESTE, cli.corretoras())
    assert cli.escritas == [], cli.escritas
    assert cli.acervo == antes, "o ensaio mexeu no acervo"
    assert c["total"] > 0
    por_nome = {b["nome"]: b for b in c["corretoras"]}
    assert por_nome["AMANDUS SEGUROS"]["conversas"] == 1
    assert por_nome["Resulta Seguros"]["conversas"] == 1   # achou pelo 9º dígito
    # e o ledger nunca aparece no plano
    tabelas = {l["tabela"] for b in c["corretoras"] for l in b["linhas"]}
    assert "platform_sends" not in tabelas and "work_events" not in tabelas


# --------------------------------------------------------------------------
# 3 e 4. O RECORTE E O CONTROLE
# --------------------------------------------------------------------------
def test_executa_so_o_telefone_e_a_corretora_pedida():
    cli = ClienteDeMentira(_acervo())
    with tempfile.TemporaryDirectory() as pasta:
        so_amandus = [c for c in cli.corretoras() if c["id"] == C1]
        M.executar(cli, TESTE, so_amandus, pasta=pasta, com_acervo=True)

    ids = lambda t: {str(l["id"]) for l in cli.acervo[t]}  # noqa: E731
    # saiu o do telefone, NA corretora pedida
    assert "cv1" not in ids("conversations")
    assert "m1" not in ids("messages")
    assert "um1" not in ids("user_memories")
    assert "ss1" not in ids("session_summaries")
    assert "ck1" not in ids("checkpoints")
    assert "sa1" not in ids("saudacoes_enviadas")
    assert "at1" not in ids("attendance_transcripts")

    # 🔴 CONTROLE A — outro telefone, mesma corretora: INTACTO
    assert {"cv3"} <= ids("conversations")
    assert {"m3"} <= ids("messages")
    assert {"um3"} <= ids("user_memories")
    assert {"ss2"} <= ids("session_summaries")
    assert {"ck2"} <= ids("checkpoints")
    assert {"at2"} <= ids("attendance_transcripts")

    # 🔴 CONTROLE B — o MESMO telefone na OUTRA corretora: INTACTO
    assert {"cv2"} <= ids("conversations")
    assert {"m2"} <= ids("messages")
    assert {"um2"} <= ids("user_memories")
    assert {"ck3"} <= ids("checkpoints")

    # 🔴 a auditoria FICA; só o vínculo que o agente lê some
    wr = {l["id"]: l for l in cli.acervo["work_runs"]}
    assert set(wr) == {"wr1", "wr2"}
    assert wr["wr1"]["conversation_id"] is None
    assert wr["wr2"]["conversation_id"] == "cv3"          # CONTROLE
    # e o ledger financeiro não foi tocado
    assert ids("platform_sends") == {"ps1"}
    assert all(t not in ("platform_sends", "work_events") for t, _, _ in cli.escritas)


def test_o_corpus_do_piloto_so_sai_com_com_acervo():
    """📊 Um único número de teste soma 4.457 `attendance_transcripts` numa
    corretora real. Ele NÃO é lido para 'lembrar' do segurado — é a medição do
    piloto. Sem `--com-acervo`, fica."""
    cli = ClienteDeMentira(_acervo())
    with tempfile.TemporaryDirectory() as pasta:
        M.executar(cli, TESTE, cli.corretoras(), pasta=pasta)     # PADRÃO
    assert {str(l["id"]) for l in cli.acervo["attendance_transcripts"]} == {"at1", "at2"}
    # ...e a sessão fica, com o VÍNCULO para a conversa apagada já anulado
    assert {str(l["id"]) for l in cli.acervo["attendance_sessions"]} == {"as1", "as2"}
    assert [l for l in cli.acervo["attendance_sessions"]
            if l["id"] == "as1"][0]["conversation_id"] is None

    # CONTROLE: com a flag, o mesmo motor leva o corpus daquele telefone
    cli2 = ClienteDeMentira(_acervo())
    with tempfile.TemporaryDirectory() as pasta:
        M.executar(cli2, TESTE, cli2.corretoras(), pasta=pasta, com_acervo=True)
    assert {str(l["id"]) for l in cli2.acervo["attendance_transcripts"]} == {"at2"}


def test_prova_que_o_controle_pode_falhar():
    """§9.3 — um guarda que não tem como falhar não guarda nada.

    Se o recorte por corretora fosse ignorado, `cv2` sairia junto. Rodando o
    MESMO motor com AS DUAS corretoras, `cv2` tem de sair — o que prova que o
    teste acima estava medindo o recorte, e não uma coincidência."""
    cli = ClienteDeMentira(_acervo())
    with tempfile.TemporaryDirectory() as pasta:
        M.executar(cli, TESTE, cli.corretoras(), pasta=pasta)
    ids = {str(l["id"]) for l in cli.acervo["conversations"]}
    assert "cv2" not in ids and "cv1" not in ids
    assert "cv3" in ids                                    # o CONTROLE resiste sempre


# --------------------------------------------------------------------------
# 5. O BACKUP VEM ANTES
# --------------------------------------------------------------------------
def test_backup_gravado_antes_da_primeira_escrita():
    cli = ClienteDeMentira(_acervo())
    with tempfile.TemporaryDirectory() as pasta:
        caminho = {}
        cli.espiao_backup = lambda: caminho.get("v", "")
        # o nome do arquivo é determinístico o bastante para o espião: é o
        # único .json da pasta no instante da 1ª escrita
        original_open = M.json.dump

        def _dump(obj, f, **kw):
            caminho["v"] = f.name
            return original_open(obj, f, **kw)

        M.json.dump = _dump
        try:
            r = M.executar(cli, TESTE, cli.corretoras(), pasta=pasta)
        finally:
            M.json.dump = original_open

        assert cli.backup_na_1a_escrita is True, "escreveu no banco antes de salvar o backup"
        assert os.path.getsize(r["backup"]) > 0
        pacote = json.load(open(r["backup"], encoding="utf-8"))
        # o backup guarda as linhas, e NUNCA o telefone em claro no nome
        assert M.digitos(TESTE) not in os.path.basename(r["backup"])
        guardadas = {t for b in pacote["corretoras"] for t in b["tabelas"]}
        assert {"conversations", "messages", "user_memories", "checkpoints"} <= guardadas

        # e o desfazer traz as linhas de volta — e RELIGA o vínculo anulado
        vazio = ClienteDeMentira({t: [] for t in cli.acervo})
        vazio.acervo["work_runs"] = [{"id": "wr1", "company_id": C1,
                                      "conversation_id": None, "outcome_title": "t"}]
        feito = M.restaurar(vazio, r["backup"])
        assert feito.get("conversations", 0) == 2 and feito.get("messages", 0) == 2
        assert vazio.acervo["work_runs"][0]["conversation_id"] == "cv1"


if __name__ == "__main__":
    for nome, fn in sorted(list(globals().items())):
        if nome.startswith("test_"):
            fn(); print(f"OK {nome}")
    print("VERDE")

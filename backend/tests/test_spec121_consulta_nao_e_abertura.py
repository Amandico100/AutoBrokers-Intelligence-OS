"""SPEC-121 F3b · O TESTE DO FIO — consultar um pedido que JÁ EXISTE não é abrir um.

O fio, elo a elo, todos REAIS (dublê só na borda: o banco):

```
observed_events (dublê: M.eventos_observados)
  → gerar_corpus_de_telas.gerar
      → zonas_do_acervo.atendimentos
      → zonas_do_acervo.consulta_de_pedido_existente   🔴 a janela "Ver detalhes"
      → padroes_de_servico.servico_da_sessao            a etiqueta
      → sessao_chegou_ao_fim (motor)                    o protocolo
      → escolher_sessoes → allianz-residencial.jsonl + relatório (INDICE)
```

📊 O defeito (29/09, simulador do acervo regerado pela F3): `allianz/residencial/
desentupimento` virou ATENDE SOZINHO só por `8ad1d251+1` — a corretora respondeu
"Ver detalhes" e a URA mostrou o RESUMO do pedido ANTIGO, com o protocolo dele.
O padrão-ouro `*Serviço:*` desse resumo deu a etiqueta, e o motor leu o protocolo
como desfecho. Rota falsa em ATENDE SOZINHO: o produto ligaria algo que nunca
abriu um pedido.

As telas de CONSULTA abaixo são as de `8ad1d251+1` (acervo regerado em 29/09, já
mascaradas), com o número do protocolo trocado por um FICTÍCIO. Elas vêm escritas
aqui, e não lidas do acervo, porque depois da F3b o acervo NÃO as tem mais — é
exatamente isso que este arquivo prova. As telas de tronco e da abertura real vêm
do acervo versionado (`7ac3c101`, máquina de lavar até o protocolo).

CONTROLES (CLAUDE.md §9.2), cada um mudando UM fator:
  A · a MESMA sequência com "2" (Abrir novo) no lugar de "1" (Ver detalhes) →
      sem janela, o resumo volta a etiquetar e a contar como fim. É isso que
      prova que o mérito é da janela, e não de outra coisa.
  B · consulta e DEPOIS "Abrir um novo atendimento" na porta → a abertura REAL
      que vem depois conta: etiqueta e protocolo.

⚠️ MUTAÇÃO que deixa o teste do fio vermelho: `consulta_de_pedido_existente`
   devolvendo `set()` (`test_MUTACAO_sem_a_janela_o_defeito_volta` a aplica).
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "scripts"))

import regua_motor as M                 # noqa: E402
import zonas_do_acervo as Z             # noqa: E402
import gerar_corpus_de_telas as G       # noqa: E402
from app.services.atlas import templater as TPL  # noqa: E402

CORPUS = os.path.join(AQUI, "corpus", "telas_reais")
SID = "f3b0f3b0-0121-4000-8000-000000000001"
EMPRESA = "c0c0c0c0-0121-4000-8000-000000000002"

# 📊 as telas de 8ad1d251+1, na ordem em que a URA mandou (protocolo FICTÍCIO)
PEDIDO_EXISTENTE = ("Identifiquei que temos uma solicitação de serviço feita. O que deseja?"
                    "\n\n*1 -* Ver detalhes\n*2 -* Abrir novo atendimento")
PORTA = ("Selecione a opção que deseja para visualizar mais informações:\n\n"
         "*1 -* *DESENTUPIMENTO*;\n*2 -* Abrir um novo atendimento\n*3 -* Sair")
ALTERAR = ("Caso deseje alterar o atendimento, selecione uma das opções abaixo:\n\n"
           "*1 -* Cancelar serviço\n*2 -* Alterar data/hora do serviço agendado\n"
           "*3 -* Voltar\n*4 -* Sair")
RESUMO_ANTIGO = ("*RESUMO*\n\n*Protocolo 50000001\n*Serviço:* *DESENTUPIMENTO*;\n"
                 "*Endereço:* {ENDERECO}\n*Tipo solicitação:* Agendado\n"
                 "*Agendamento para:* Segunda-feira, {DATA}\n*Período:* 13:00 às 18:00 (tarde)")


def _acervo(sid: str) -> List[str]:
    caminho = os.path.join(CORPUS, "allianz-residencial.jsonl")
    if not os.path.exists(caminho):
        pytest.skip("acervo versionado ausente")
    ls = sorted((json.loads(l) for l in open(caminho, encoding="utf-8") if l.strip()),
                key=lambda l: l.get("wa_timestamp") or "")
    ls = [l["text"] for l in ls if l["session_id"] == sid]
    assert ls, "a máquina de lavar %s sumiu do acervo" % sid
    return ls


def _fronteira() -> str:
    """A transferência é tela de TRONCO: a mesma frase em dezenas de sessões."""
    caminho = os.path.join(CORPUS, "allianz-residencial.jsonl")
    for l in open(caminho, encoding="utf-8"):
        if l.strip() and re.search(r"vou transferir seu caso", json.loads(l)["text"], re.I):
            return json.loads(l)["text"]
    raise AssertionError("a tela de transferência sumiu do acervo")


def _uma(telas: List[str], padrao: str) -> str:
    return next(t for t in telas if re.search(padrao, t, re.IGNORECASE))


def _tronco_ate_o_endereco() -> List[Tuple[str, str]]:
    m = _acervo("7ac3c101")
    seq = [("out", "oi"), ("in", _uma(m, r"^termo de privacidade")),
           ("in", _uma(m, r"assistente virtual da allianz")), ("out", "2"),
           ("in", _uma(m, r"qual seguro deseja utilizar")), ("out", "1"),
           ("in", _uma(m, r"antes de prosseguirmos")),
           ("in", _uma(m, r"digite o \*?cpf")), ("out", "1"),
           ("in", _uma(m, r"confirme o endere[çc]o para atendimento")),
           ("in", _uma(m, r"^\*1 -\*.*\n\*2 -\* Voltar")), ("out", "1"),
           ("in", _uma(m, r"confirme o n[úu]mero da resid")), ("out", "1"),
           ("in", _uma(m, r"informe o complemento")), ("out", "casa")]
    return seq


def _abertura_real() -> List[Tuple[str, str]]:
    """A máquina de lavar de 7ac3c101 do telefone até o protocolo."""
    m = _acervo("7ac3c101")
    i = m.index(_uma(m, r"registramos o telefone"))
    j = m.index(_uma(m, r"n[úu]mero de protocolo"))
    seq: List[Tuple[str, str]] = []
    for tela in m[i:j + 1]:
        seq += [("in", tela), ("out", "1")]
    return seq


def _sessao(resposta_ao_pedido_existente: str = "1",
            abre_depois: bool = False) -> List[Dict[str, Any]]:
    seq = _tronco_ate_o_endereco()
    seq += [("in", PEDIDO_EXISTENTE), ("out", resposta_ao_pedido_existente),
            ("in", PORTA)]
    if abre_depois:
        seq += [("out", "2")] + _abertura_real()
    else:
        seq += [("out", "1"), ("in", ALTERAR), ("in", RESUMO_ANTIGO)]
    seq += [("in", _fronteira())]
    return [{"session_id": SID, "insurer_key": "allianz", "company_id": EMPRESA,
             "direction": d, "text": t,
             "wa_timestamp": "2026-09-29T11:%02d:%02d+00:00" % (i // 60, i % 60),
             "msg_type": "text", "interactive": None}
            for i, (d, t) in enumerate(seq)]


def _gerar(tmp_path, monkeypatch, eventos) -> Dict[str, Any]:
    """Roda o GERADOR de verdade; o banco é o único dublê."""
    monkeypatch.setattr(M, "eventos_observados", lambda seguradora=None, **k: iter(
        e for e in eventos if seguradora in (None, e["insurer_key"])))
    monkeypatch.setattr(M, "seguradoras", lambda: ["allianz"])
    monkeypatch.setattr(M, "controle_do_mascarador", lambda: 1)
    monkeypatch.setattr(TPL, "_CACHE_MARCAS", ())
    monkeypatch.setattr(G, "DESTINO", str(tmp_path))
    rel = G.gerar(["allianz"])
    caminho = tmp_path / "allianz-residencial.jsonl"
    linhas = ([json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines()
               if l.strip()] if caminho.exists() else [])
    return {"rel": rel, "linhas": linhas}


def _pb():
    return M.get_playbook(M.resolve_playbook_ref("allianz", "residencial"))


# ─────────────────────────────────────────────────────────────────────────────
# O MOTOR LÊ o protocolo do resumo antigo — a proteção NÃO pode ser o motor
# ─────────────────────────────────────────────────────────────────────────────
def test_o_motor_le_o_protocolo_do_resumo_antigo():
    """Premissa do fio: sozinho, o resumo da consulta É "chegou ao fim" para o
    motor. Se isto ficar vermelho, o motor passou a separar consulta de abertura
    e a janela pode ser revista (CLAUDE.md §9.3)."""
    assert M.extract_capture_anchors(_pb(), RESUMO_ANTIGO).get("protocol")
    assert G.sessao_chegou_ao_fim(_pb(), [RESUMO_ANTIGO]) is True


# ─────────────────────────────────────────────────────────────────────────────
# O FIO
# ─────────────────────────────────────────────────────────────────────────────
def test_a_consulta_nao_etiqueta_nao_conta_como_fim_e_nao_entra_no_acervo(tmp_path, monkeypatch):
    out = _gerar(tmp_path, monkeypatch, _sessao("1"))
    textos = [l["text"] for l in out["linhas"]]
    assert not [l for l in out["linhas"] if l.get("servico") == "desentupimento"], (
        "a CONSULTA de um desentupimento virou etiqueta de desentupimento")
    assert not any(re.search(r"Protocolo \d", t) for t in textos), (
        "o RESUMO do pedido ANTIGO entrou no acervo — o simulador o leria como desfecho")
    assert not any("Caso deseje alterar" in t for t in textos)
    # a TRANSFERÊNCIA fecha a janela e fica (tela de tronco)
    assert any(re.search(r"vou transferir seu caso", t, re.I) for t in textos)
    # a PORTA fica: é a tela em que o corredor responde "2" e sai da consulta
    assert any("visualizar mais informa" in t for t in textos)
    sem = out["rel"]["sem_etiqueta"]["allianz-residencial"]
    assert G.MOTIVO_CONSULTA in sem, sem
    assert sem[G.MOTIVO_CONSULTA]["com_desfecho"] == 0
    cont = out["rel"]["por_seguradora"]["allianz"]
    assert cont["CONSULTA_atendimentos"] == 1 and cont["CONSULTA_telas_fora"] == 2, cont


def test_CONTROLE_A_sem_ver_detalhes_o_mesmo_resumo_volta_a_contar(tmp_path, monkeypatch):
    """UM fator muda — a resposta à tela do pedido existente. Sem a janela, o
    resumo etiqueta `desentupimento` e é fim: o defeito que a F3b tira."""
    out = _gerar(tmp_path, monkeypatch, _sessao("2"))
    desent = [l["text"] for l in out["linhas"] if l.get("servico") == "desentupimento"]
    assert desent, "o controle não reproduz o defeito — o teste do fio não mediria nada"
    assert G.sessao_chegou_ao_fim(_pb(), desent) is True


def test_CONTROLE_B_a_abertura_real_depois_da_consulta_continua_contando(tmp_path, monkeypatch):
    out = _gerar(tmp_path, monkeypatch, _sessao("1", abre_depois=True))
    maquina = [l["text"] for l in out["linhas"] if l.get("servico") == "maquina_de_lavar"]
    assert maquina, [l.get("servico") for l in out["linhas"]]
    assert G.sessao_chegou_ao_fim(_pb(), maquina) is True
    assert any(re.search(r"n[úu]mero de protocolo", t) for t in maquina)
    # a porta fica, e a consulta nunca chegou a acontecer: nada saiu
    assert any("visualizar mais informa" in t for t in maquina)
    assert out["rel"]["por_seguradora"]["allianz"].get("CONSULTA_telas_fora", 0) == 0


def test_MUTACAO_sem_a_janela_o_defeito_volta(tmp_path, monkeypatch):
    """§9.3: o guarda CONSEGUE ficar vermelho. Sem a janela, a consulta volta a
    etiquetar e a trazer o protocolo antigo."""
    monkeypatch.setattr(Z, "consulta_de_pedido_existente", lambda eventos, seg=None: set())
    out = _gerar(tmp_path, monkeypatch, _sessao("1"))
    assert [l for l in out["linhas"] if l.get("servico") == "desentupimento"]


# ─────────────────────────────────────────────────────────────────────────────
# A JANELA, tela a tela — as formas reais das duas Allianz
# ─────────────────────────────────────────────────────────────────────────────
def _ev(seq):
    return [{"direction": d, "text": t} for d, t in seq]


def test_a_janela_do_auto_sem_porta_abre_e_fecha_pelo_abrir_novo():
    """📊 A forma de `5d34bab2` (allianz auto): lista → resumo → cancelar/remarcar →
    "O que deseja fazer agora? 1 - Abrir novo atendimento" → abertura."""
    lista = "Selecione o atendimento:\n\n*1 -* REBOQUE;\n*2 -* REBOQUE;\n*9 -* Voltar\n*0 -* Sair"
    resumo = "*RESUMO*\n\n*Protocolo Nrº:* 50000002\n*Serviço:* REBOQUE;\n*Origem:* {ENDERECO}"
    ajuda = "Como podemos ajudar?\n\n*1 -* Alterar atendimento\n*0 -* Sair"
    depois = ("Certo! Seu atendimento não foi reagendado. \n\nO que deseja fazer agora?\n\n"
              "*1 -* Abrir novo atendimento\n*9 -* Voltar\n*0 -* Sair")
    veiculo = "O seu veículo é:\n\n*1 -* Automotor (à gasolina/etanol/diesel) ou Hibrido\n*2 -* Elétrico"
    ev = _ev([("in", PEDIDO_EXISTENTE), ("out", "1"), ("in", lista), ("out", "1"),
              ("in", resumo), ("in", ajuda), ("out", "1"), ("in", depois), ("out", "1"),
              ("in", veiculo)])
    dentro = Z.consulta_de_pedido_existente(ev)
    assert {i for i in dentro if ev[i]["direction"] == "in"} == {2, 4, 5}
    assert 7 not in dentro and 9 not in dentro   # a porta e a abertura ficam


def test_CONTROLE_sem_pedido_existente_nada_e_consulta():
    ev = _ev([("in", PORTA), ("out", "1"), ("in", RESUMO_ANTIGO)])
    assert Z.consulta_de_pedido_existente(ev) == set()

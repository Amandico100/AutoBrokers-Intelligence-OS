"""SPEC-121 F3 · O TESTE DO FIO — o acervo enxerga o robô que RECOMEÇA.

O fio, elo a elo, todos REAIS (dublê só na borda: o banco):

```
observed_events (dublê: M.eventos_observados)
  → gerar_corpus_de_telas.gerar
      → zonas_do_acervo.zonas / atendimentos       quem fala: robô ou pessoa
      → padroes_de_ramo.classificar_ramo           o ramo de CADA atendimento
      → higiene_do_corpus.higienizar / auditar_pii a máscara
      → padroes_de_servico.servico_da_sessao       o serviço de CADA atendimento
      → sessao_chegou_ao_fim (motor)               o protocolo
      → escolher_sessoes → <seguradora>-<ramo>.jsonl + INDICE
```

📊 A sessão é montada com o FORMATO de `8ad1d251` (allianz, 29/09): URA →
"vou transferir seu caso para um especialista" → a pessoa da seguradora conversa
→ a corretora escreve de novo → **o robô recomeça** e faz uma máquina de lavar
inteira até o protocolo. As telas do robô vêm do acervo versionado (a máquina de
lavar `7ac3c101`, já mascarada); as falas da pessoa são as de `8ad1d251`, sem
nome (CLAUDE.md §9.4 e §13.9).

🔴 Antes da F3 as telas do recomeço saíam do corpus: a zona HUMANO ia até o fim.

CONTROLES (CLAUDE.md §9.2):
  A · depois da transferência só a PESSOA fala → nada depois da fronteira entra.
  B · o robô se apresenta mas NINGUÉM responde (é aviso, 📊 `334a4892` hdi) →
      continua HUMANO, nada entra.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List

import pytest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(AQUI), "scripts")
sys.path.insert(0, SCRIPTS)

import regua_motor as M                 # noqa: E402
import zonas_do_acervo as Z             # noqa: E402
import gerar_corpus_de_telas as G       # noqa: E402
from app.services.atlas import templater as TPL  # noqa: E402

CORPUS = os.path.join(AQUI, "corpus", "telas_reais")
SID = "f3f3f3f3-0121-4000-8000-000000000001"
EMPRESA = "c0c0c0c0-0121-4000-8000-000000000002"

# as falas da PESSOA da seguradora em 8ad1d251 — sem nome, sem número
FALAS_DA_PESSOA = [
    "Isso pode levar alguns instantes, mas já já você será atendido! Fique ligado!",
    "Em que posso te ajudar?",
    "Só um momento por favor enquanto verifico seu atendimento.",
    "Realmente aconteceu algum problema interno com agendamento e envio do prestador",
    "O agendamento é por período, manhã das 08h às 12h ou tarde, das 13h às 18h. "
    "Para qual dia e período quer solicitar?",
    "Assistência 24 horas, permanece à disposição. Tenha um bom dia!",
]


def _acervo(sid: str) -> List[str]:
    caminho = os.path.join(CORPUS, "allianz-residencial.jsonl")
    if not os.path.exists(caminho):
        pytest.skip("acervo versionado ausente")
    ls = [json.loads(l) for l in open(caminho, encoding="utf-8") if l.strip()]
    ls = sorted((l for l in ls if l["session_id"] == sid),
                key=lambda l: l.get("wa_timestamp") or "")
    assert ls, "a máquina de lavar %s sumiu do acervo" % sid
    return [l["text"] for l in ls]


def _tronco(padrao: str) -> str:
    caminho = os.path.join(CORPUS, "allianz-residencial.jsonl")
    for l in open(caminho, encoding="utf-8"):
        if l.strip() and re.search(padrao, json.loads(l)["text"], re.IGNORECASE):
            return json.loads(l)["text"]
    raise AssertionError("tela de tronco %r sumiu do acervo" % padrao)


def _uma(telas: List[str], padrao: str) -> str:
    return next(t for t in telas if re.search(padrao, t, re.IGNORECASE))


def _sessao(com_recomeco: bool = True, robo_sem_resposta: bool = False) -> List[Dict[str, Any]]:
    maquina = _acervo("7ac3c101")
    termo = _uma(maquina, r"^termo de privacidade")
    ola = _uma(maquina, r"assistente virtual da allianz")
    # a fronteira é tela de TRONCO: a mesma frase em dezenas de sessões da allianz
    fronteira = _tronco(r"vou transferir seu caso para um especialista")
    seq = [("out", "oi"), ("in", termo), ("in", ola), ("out", "2"),
           ("in", _uma(maquina, r"qual seguro deseja utilizar")), ("out", "1"),
           ("in", fronteira)]
    for fala in FALAS_DA_PESSOA:
        seq += [("in", fala), ("out", "ok")]
    if robo_sem_resposta:
        # CONTROLE B: o robô fala, mas ninguém responde — aviso, não atendimento
        seq += [("in", ola), ("in", _uma(maquina, r"n[úu]mero de protocolo"))]
    if com_recomeco:
        seq += [("out", "oi"), ("in", termo), ("in", ola), ("out", "2")]
        depois_do_ola = maquina[maquina.index(ola) + 1:]
        for tela in depois_do_ola:
            seq += [("in", tela), ("out", "1")]
    eventos = []
    for i, (direcao, texto) in enumerate(seq):
        eventos.append({"session_id": SID, "insurer_key": "allianz", "company_id": EMPRESA,
                        "direction": direcao, "text": texto,
                        "wa_timestamp": "2026-09-29T10:%02d:%02d+00:00" % (i // 60, i % 60),
                        "msg_type": "text", "interactive": None})
    return eventos


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
    linhas = ([json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]
              if caminho.exists() else [])
    return {"rel": rel, "linhas": linhas}


# ─────────────────────────────────────────────────────────────────────────────
# O FIO
# ─────────────────────────────────────────────────────────────────────────────
def test_o_robo_que_recomeca_depois_da_pessoa_volta_ao_acervo(tmp_path, monkeypatch):
    out = _gerar(tmp_path, monkeypatch, _sessao())
    linhas = out["linhas"]
    recomeco = [l for l in linhas if l["session_id"] == "f3f3f3f3+1"]
    assert recomeco, "o atendimento em que o robô recomeçou não chegou ao acervo"
    # o serviço do atendimento é o DELE — a máquina de lavar
    assert {l["servico"] for l in recomeco} == {"maquina_de_lavar"}
    # e ele chega ao PROTOCOLO pelo motor (a nota do gerador diz COM DESFECHO)
    notas = out["rel"]["arquivos"]["allianz-residencial.jsonl"]["notas_da_selecao"]
    assert "[maquina_de_lavar] COM DESFECHO -> f3f3f3f3+1" in notas
    assert any(re.search(r"n[úu]mero de protocolo", l["text"], re.IGNORECASE) for l in recomeco)
    # 🔴 a PESSOA continua fora do corpus
    textos = {l["text"] for l in linhas}
    for fala in FALAS_DA_PESSOA:
        assert fala not in textos, "fala da pessoa da seguradora entrou no acervo: %r" % fala[:40]


def test_CONTROLE_A_so_a_pessoa_depois_da_transferencia_nada_volta(tmp_path, monkeypatch):
    out = _gerar(tmp_path, monkeypatch, _sessao(com_recomeco=False))
    linhas = out["linhas"]
    assert not [l for l in linhas if "+" in l["session_id"]]
    fronteira_ts = max(l["wa_timestamp"] for l in linhas
                       if "vou transferir seu caso" in l["text"].lower())
    assert all(l["wa_timestamp"] <= fronteira_ts for l in linhas), (
        "uma tela DEPOIS da transferência entrou no acervo sem o robô recomeçar")


def test_CONTROLE_B_robo_que_so_avisa_nao_e_recomeco(tmp_path, monkeypatch):
    eventos = _sessao(com_recomeco=False, robo_sem_resposta=True)
    zonas = [(e["text"], z, m) for e, z, m in Z.zonas(eventos, "allianz")]
    assert not [m for _t, _z, m in zonas if m == Z.MOTIVO_RECOMECO]
    out = _gerar(tmp_path, monkeypatch, eventos)
    assert not [l for l in out["linhas"]
                if re.search(r"n[úu]mero de protocolo", l["text"], re.IGNORECASE)]


def test_as_zonas_do_fio_dizem_quem_fala(tmp_path):
    eventos = _sessao()
    zonas = list(Z.zonas(eventos, "allianz"))
    motivos = [m for _e, _z, m in zonas if m]
    assert motivos.count("FRONTEIRA") == 1 and motivos.count(Z.MOTIVO_RECOMECO) == 1
    for e, z, _m in zonas:
        if e["text"] in FALAS_DA_PESSOA:
            assert z == "HUMANO"
    partes = Z.atendimentos(eventos, "allianz")
    assert len(partes) == 2
    # o recomeço começa NA apresentação do robô
    assert "assistente virtual da allianz" in partes[1][0][0]["text"].lower()

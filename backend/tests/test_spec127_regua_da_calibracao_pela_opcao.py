# -*- coding: utf-8 -*-
"""Pós-127 — a RÉGUA da calibração do portal compara as k propostas pela OPÇÃO escolhida, nunca o texto cru.

📊 04/10/2026 (`SPEC-126-127-RODADAS-AUTORIZADAS.md` §8): na 2ª rodada Yelum, 45 ações e 45 certas, mas a régua
dava 17/23 — 5 casos agiram certo nas 2 tentativas e só variaram o FORMATO ("4" × "4 - DANO …"). Pela OPÇÃO
(`destravador._opcao_da_resposta`, a função do produto): 22/23, Wilson [79–99 %].

R1  pelo MOTOR (`bancada_portal.rodar`): k=2 com a MESMA opção em formatos diferentes → as k concordam.
R2  LINHA DE CONTROLE: k=2 com opções DIFERENTES → discordam (e o caso não é "certo").
R3  resposta FORA da lista nas k (o mesmo texto cru) → discordância (nunca "concordam por igualdade").
R4  sem a lista do caso (a URA): o texto cru, como sempre — "1" e "Residencial" continuam diferentes.
R5  a rodada GRAVADA de 04/10, re-julgada sem modelo: 22/23 e religa; a MESMA rodada sem a lista: 17/23, não.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import destravador as DT  # noqa: E402
from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import bancada_portal as BP  # noqa: E402

CASOS = BP.carregar_casos()
ALVOS = [c for c in CASOS if c["seguradora"] == "yelum" and c["tipo"] not in ("cidade", "lataria")
         and c["gabarito"]["acao"] == "RESPONDER" and len(c["parada"]["opcoes"]) >= 3
         and c["parada"]["opcoes"][0] != c["gabarito"]["resposta"]]
_RX = re.compile(r"^(\d+) - (.+)$", re.M)
SALVO = ROOT / "tests" / "corpus" / "bancada" / "RESULTADOS" / "fecho_portal_yelum_k2_v2.json"


class _PorTentativa:
    """Responde a opção do gabarito; a 1ª chamada de cada caso no `formatos[0]`, a 2ª no `formatos[1]`
    (`{i}`/`{o}` = número/texto da certa; `{j}`/`{p}` = de OUTRA opção). Por caso, não por ordem global."""

    def __init__(self, formatos, provedor):
        self.formatos, self.provedor, self.vez = list(formatos), provedor, {}

    async def ainvoke(self, mensagens):
        from langchain_core.messages import AIMessage

        user = DT.texto_da_mensagem(mensagens[-1])
        lista = dict((o, int(i)) for i, o in _RX.findall(user.split("Opções da lista do portal:", 1)[-1]))
        caso = next(c for c in CASOS if c["pedido"]["dano"].get("descricao")
                    and c["pedido"]["dano"]["descricao"] in user)
        n = self.vez.get(caso["id"], 0)
        self.vez[caso["id"]] = n + 1
        certa = caso["gabarito"]["resposta"]
        outra = next(o for o in lista if o != certa)
        valor = self.formatos[min(n, len(self.formatos) - 1)].format(i=lista[certa], o=certa, j=lista[outra], p=outra)
        return AIMessage(content=json.dumps({"classe": "deduzir", "acao": "RESPONDER", "valor": valor, "nota": 95,
                                             "motivo": "duble"}, ensure_ascii=False),
                         response_metadata={"model_provider": self.provedor, "model_name": "duble"})


def _resumo(f1, f2, segunda=("{o}", "{o}")):
    """k=2 = duas rodadas k=1 pelo motor, cada uma com UM formato fixo (o motor pode chamar o modelo mais de
    uma vez por tentativa — contar chamadas não separa as tentativas), juntadas como tentativas 1 e 2."""
    resultados = []
    for t, (fp, fs) in enumerate(((f1, segunda[0]), (f2, segunda[1])), 1):
        rod = asyncio.run(BP.rodar(ALVOS, _PorTentativa((fp,), "openai"), provedor="openai", modelo="duble", k=1,
                                   llm_segunda=_PorTentativa((fs,), "anthropic"), provedor_segunda="anthropic",
                                   modelo_segunda="duble"))
        assert not [r for r in rod["resultados"] if r["resultado"] == "BLOCKED_BY_INFRA"]
        resultados += [{**r, "tentativa": t} for r in rod["resultados"]]
    return B.resumo_da_calibracao([{"resultados": resultados}])["yelum"]


def test_R1_a_mesma_opcao_em_formatos_diferentes_concorda():
    assert len(ALVOS) >= 10
    m = _resumo("{i} - {o}", "{o}")
    assert m["k_concordantes"] == m["porta_n"] == len(ALVOS), m["casos"]
    assert m["agiu_certos"] == m["agiu_n"] == len(ALVOS)
    assert m["modelo_proposta_certos"] == len(ALVOS)            # "4 - X" é a proposta X (o `julgar` pela opção)
    m2 = _resumo("{i}", "opção {i} - {o}")
    assert m2["k_concordantes"] == len(ALVOS)


def test_R2_CONTROLE_opcoes_diferentes_discordam():
    m = _resumo("{o}", "{p}", segunda=("{o}", "{p}"))
    assert m["k_concordantes"] == 0, m["casos"]
    assert m["agiu_certos"] == 0                                # agiu certo 1×, errado na outra: nunca "certo"
    m2 = _resumo("{i} - {o}", "{j}", segunda=("{o}", "{p}"))    # pelo NÚMERO, outra opção
    assert m2["k_concordantes"] == 0


def _rodada(valores, opcoes):
    return {"resultados": [{"chave": "c1", "tentativa": t, "resultado": "CERTO", "rastro": {"estado": {
        "decisao": {"acao": "RESPONDER", "porta_do_deduzir": True, "valor": "X", "valor_do_modelo": v},
        "veredito_destravador": {"classe": "CERTO", "proposta_certa": True},
        "calibracao": {"seguradora": "s", "controle_tecla_1": False,
                       **({"opcoes": opcoes} if opcoes is not None else {})}}}}
        for t, v in enumerate(valores, 1)]}


def test_R3_fora_da_lista_e_discordancia_mesmo_com_texto_igual():
    assert B.resumo_da_calibracao([_rodada(["Z", "Z"], ["X", "Y"])])["s"]["k_concordantes"] == 0
    assert B.resumo_da_calibracao([_rodada(["9 - X", "9 - X"], ["X", "Y"])])["s"]["k_concordantes"] == 0
    assert B.resumo_da_calibracao([_rodada(["1 - X", "X"], ["X", "Y"])])["s"]["k_concordantes"] == 1


def test_R4_sem_a_lista_a_URA_continua_no_texto_cru():
    assert B.resumo_da_calibracao([_rodada(["1 - X", "X"], None)])["s"]["k_concordantes"] == 0
    assert B.resumo_da_calibracao([_rodada(["1", "Residencial"], None)])["s"]["k_concordantes"] == 0
    assert B.resumo_da_calibracao([_rodada(["x", " X "], None)])["s"]["k_concordantes"] == 1
    assert B.resumo_da_calibracao([_rodada(["1 - X", "X"], [])])["s"]["k_concordantes"] == 0   # lista vazia = sem lista


def test_R5_a_rodada_gravada_de_04_10_pela_opcao_22_de_23_e_sem_a_lista_17():
    salvo = json.loads(SALVO.read_text(encoding="utf-8"))
    (rod,) = BP.rejulgar(salvo).values()
    resumo, decisao = BP.resumo_e_decisao(rod, rotulo="openai:gpt-6.1-sol:high")
    y = resumo["yelum"]
    assert (y["agiu_n"], y["agiu_certos"], y["porta_n"]) == (23, 22, 26)
    assert y["wilson"][0] >= 0.70 and decisao["yelum"]["religa"] is True
    assert decisao["todas"]["religa"] is False                   # o agregado nunca religa
    # CONTROLE: a mesma rodada SEM a lista do caso (a régua do texto cru) → os 17/23 de 04/10
    for r in rod["resultados"]:
        ((r.get("rastro") or {}).get("estado") or {}).get("calibracao", {}).pop("opcoes", None)
    r0 = B.resumo_da_calibracao([rod])
    assert (r0["yelum"]["agiu_n"], r0["yelum"]["agiu_certos"]) == (23, 17)
    d0 = B.decidir_religar(r0, rodada=BP.sha_do_gabarito())["yelum"]
    assert d0["religa"] is False and d0["porque"] == "acerto_abaixo:17/23"


def test_R5_o_sql_de_religar_e_so_da_corretora_pedida_e_so_da_linha_vidros():
    salvo = json.loads(SALVO.read_text(encoding="utf-8"))
    (rod,) = BP.rejulgar(salvo).values()
    _resumo_, decisao = BP.resumo_e_decisao(rod, rotulo="r")
    cid = "bbbbbbbb-0000-4000-8000-00000000b127"
    sql = BP.sql_de_religar_o_portal(decisao, [cid])
    assert sql.count("insert into public.cerebro_modos") == 1
    assert f"company_id = '{cid}'" in sql and "insurer_key = 'yelum'" in sql and "'vidros'" in sql
    assert "'todas'" not in sql

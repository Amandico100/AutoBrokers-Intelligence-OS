# -*- coding: utf-8 -*-
"""Conserto pós-127 (T-102) — o destravador do PORTAL aceita a opção com o NÚMERO que o próprio prompt pôs.

📊 04/10/2026 (`SPEC-126-127-RODADAS-AUTORIZADAS.md` §5): o prompt numera a lista (`texto_da_parada`:
"{i} - {o}") e o modelo devolve "4 - DANO ACIDENTAL CAUSADO POR PEDRA"; `_opcao_igual` exige igualdade →
45 das 54 respostas reais caíram em `valor_fora_das_opcoes`.

Tudo pelo MOTOR do produto (CLAUDE.md §9.4): `destravador.destravar_parada_do_portal` via `bancada_portal.rodar`
(o diário e a conversa são dublês; a dedução LIGADA só na bancada), com um "modelo" dublê que lê as opções do
PROMPT REAL e responde no formato que os modelos reais usaram.

N1  "4 - X" / "4) X" / "4. X" / "opção 4 - X" com o número E o texto da MESMA opção → age, e o valor que vai
    ao portal é a OPÇÃO (sem o número). Linha de controle: a mesma resposta SEM o número age igual.
N2  número e texto DIVERGENTES → nunca age (pergunta: `valor_fora_das_opcoes`).
N3  só o número ("4", "opção 4") → a opção 4; número fora da lista → nunca age.
N4  a 2ª opinião com número e a 1ª sem (📊 5 das 54: "segunda_opiniao_discordou") → concordam.
N5  o CONTROLE "1ª opção" numerado continua sem religar (o número não compra calibração).
N6  o dado do CASO não ganha o atalho: um "2" em `especificos` nunca vira a 2ª opção (`_opcao_igual`).
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services import destravador as DT  # noqa: E402
from app.services.evals import bancada_portal as BP  # noqa: E402

CASOS = BP.carregar_casos()
#: Yelum, tipos calibráveis, gabarito RESPONDER, a resposta NÃO é a 1ª opção (o número importa) e ≥ 3 opções
#: (dá para errar o número sem sair da lista). ⚠️ Sem `lataria`: o destravador não a responde (lista múltipla,
#: `resposta_do_portal` → sem formato), com ou sem número — 📊 o lataria-001 da rodada de 04/10.
ALVOS = [c for c in CASOS if c["seguradora"] == "yelum" and c["tipo"] not in ("cidade", "lataria")
         and c["gabarito"]["acao"] == "RESPONDER" and len(c["parada"]["opcoes"]) >= 3
         and c["parada"]["opcoes"][0] != c["gabarito"]["resposta"]]
_RX_OPCAO_NO_PROMPT = re.compile(r"^(\d+) - (.+)$", re.M)


class _ModeloNumerado:
    """Lê a lista do PROMPT REAL (`compor_mensagens_do_portal`) e responde a opção do gabarito no `formato`:
    `{i}` = o número que o PROMPT deu a ela; `{o}` = o texto dela; `{j}`/`{p}` = o número/texto de OUTRA opção."""

    def __init__(self, formato: str, provedor: str):
        self.formato, self.provedor = formato, provedor

    async def ainvoke(self, mensagens):
        from langchain_core.messages import AIMessage

        user = DT.texto_da_mensagem(mensagens[-1])
        lista = dict((o, int(i)) for i, o in _RX_OPCAO_NO_PROMPT.findall(user.split("Opções da lista do portal:", 1)[-1]))
        caso = next(c for c in CASOS if c["pedido"]["dano"].get("descricao")
                    and c["pedido"]["dano"]["descricao"] in user)
        certa = caso["gabarito"]["resposta"]
        outra = next(o for o in lista if o != certa)
        valor = self.formato.format(i=lista[certa], o=certa, j=lista[outra], p=outra)
        corpo = {"classe": "deduzir", "acao": "RESPONDER", "valor": valor, "nota": 95, "motivo": "duble"}
        return AIMessage(content=json.dumps(corpo, ensure_ascii=False),
                         response_metadata={"model_provider": self.provedor, "model_name": "duble-numerado"})


def _decisoes(formato_1: str, formato_2: str = "{o}", casos=None) -> list:
    rod = asyncio.run(BP.rodar(casos or ALVOS, _ModeloNumerado(formato_1, "openai"), provedor="openai",
                               modelo="duble", k=1, llm_segunda=_ModeloNumerado(formato_2, "anthropic"),
                               provedor_segunda="anthropic", modelo_segunda="duble"))
    assert not [r for r in rod["resultados"] if r["resultado"] == "BLOCKED_BY_INFRA"], rod["resultados"]
    return [(r["chave"], r["rastro"]["estado"]["decisao"]) for r in rod["resultados"]]


def _gab(chave: str) -> str:
    return next(c for c in CASOS if c["id"] == chave)["gabarito"]["resposta"]


def test_ha_casos_que_provam_o_numero():
    assert len(ALVOS) >= 10, len(ALVOS)
    # o prompt REAL numera a lista — a premissa do conserto (se deixar de numerar, este teste muda com ela)
    p = DT.parada_do_portal(BP.evidencia_do_caso(ALVOS[0]))
    assert "\n1 - " + p["opcoes"][0] in DT.texto_da_parada(p)


def test_N0_CONTROLE_sem_o_numero_age_e_vai_a_opcao():
    decs = _decisoes("{o}")
    assert all(d["acao"] == "RESPONDER" and d["valor"] == _gab(k) for k, d in decs), decs


@pytest.mark.parametrize("formato", ["{i} - {o}", "{i} – {o}", "{i}) {o}", "{i}. {o}", "{i}: {o}",
                                     "opção {i} - {o}", "Opção {i}: {o}", "  {i} -   {o}  "])
def test_N1_numero_e_texto_da_MESMA_opcao_age_e_o_portal_recebe_a_opcao_sem_o_numero(formato):
    decs = _decisoes(formato, formato)
    assert all(d["acao"] == "RESPONDER" for _k, d in decs), [(k, d["proibicao"]) for k, d in decs]
    assert all(d["valor"] == _gab(k) for k, d in decs)                         # nunca "4 - X" ao portal
    assert all(re.match(r"\s*(op|\d)", d["valor_do_modelo"], re.I) for _k, d in decs)   # o diário guarda o cru


@pytest.mark.parametrize("formato", ["{j} - {o}", "{i} - {p}", "{j}) {o}", "opção {j} - {o}", "99 - {o}"])
def test_N2_numero_e_texto_DIVERGENTES_nunca_agem(formato):
    decs = _decisoes(formato, formato)
    assert all(d["acao"] != "RESPONDER" for _k, d in decs), [(k, d["valor"]) for k, d in decs]
    assert {d["proibicao"] for _k, d in decs} == {"valor_fora_das_opcoes"}


@pytest.mark.parametrize("formato", ["{i}", "opção {i}", "{i})"])
def test_N3_so_o_numero_escolhe_a_opcao_daquele_numero(formato):
    decs = _decisoes(formato, "{o}")
    assert all(d["acao"] == "RESPONDER" and d["valor"] == _gab(k) for k, d in decs), decs


def test_N3_numero_fora_da_lista_nunca_age():
    decs = _decisoes("99", "99")
    assert all(d["acao"] != "RESPONDER" for _k, d in decs)


def test_N4_a_segunda_opiniao_com_numero_concorda_com_a_primeira_sem_numero():
    for f1, f2 in (("{o}", "{i} - {o}"), ("{i} - {o}", "{o}"), ("{i} - {o}", "{i}")):
        decs = _decisoes(f1, f2)
        assert all(d["acao"] == "RESPONDER" and d["segunda_opiniao"]["concordou"] for _k, d in decs), (f1, f2)
    # e a 2ª opinião numa OUTRA opção (pelo número) discorda
    decs = _decisoes("{i} - {o}", "{j}")
    assert {d["proibicao"] for _k, d in decs} == {"segunda_opiniao_discordou"}


def test_N5_o_controle_primeira_opcao_numerado_continua_sem_religar():
    class _Primeira(_ModeloNumerado):
        async def ainvoke(self, mensagens):
            from langchain_core.messages import AIMessage

            user = DT.texto_da_mensagem(mensagens[-1])
            achadas = _RX_OPCAO_NO_PROMPT.findall(user.split("Opções da lista do portal:", 1)[-1])
            valor = f"1 - {achadas[0][1]}" if achadas else ""
            corpo = ({"classe": "deduzir", "acao": "RESPONDER", "valor": valor, "nota": 95, "motivo": "d"} if valor
                     else {"classe": "perguntar_ao_segurado", "acao": "PERGUNTAR_AO_SEGURADO", "valor": "?",
                           "nota": 50, "motivo": "d"})
            return AIMessage(content=json.dumps(corpo, ensure_ascii=False),
                             response_metadata={"model_provider": self.provedor})

    rod = asyncio.run(BP.rodar(CASOS, _Primeira("", "openai"), provedor="openai", modelo="d", k=2,
                               llm_segunda=_Primeira("", "anthropic"), provedor_segunda="anthropic",
                               modelo_segunda="d"))
    _resumo, decisao = BP.resumo_e_decisao(rod, rotulo="duble:primeira-numerada")
    assert not any(d["religa"] for d in decisao.values())
    agiu = [r for r in rod["resultados"] if r["rastro"]["estado"]["decisao"]["acao"] == "RESPONDER"]
    assert agiu                                   # o número da 1ª opção AGORA age (antes caía fora da lista)…
    assert any(r["resultado"] == "ERRADO" for r in agiu)          # …e erra, e a régua vê


def test_N6_o_dado_do_CASO_nao_ganha_o_atalho_do_numero():
    opcoes = ["SIM", "NAO", "TALVEZ"]
    assert DT._opcao_igual("2", opcoes) == ""                     # o caso / o contrato: igualdade, sempre
    assert DT._opcao_da_resposta("2", opcoes) == "NAO"            # só a resposta do MODELO lê o número
    parada = {"stage": "questionario_incompleto", "slot": "pergunta_7", "pergunta": "Quantos furos tem o vidro?",
              "opcoes": opcoes}
    assert DT.dado_do_caso_no_portal(parada, {"dano": {}, "especificos": {"quantos furos": "2"}}) == ""


@pytest.mark.parametrize("valor,esperado", [
    ("4 - D", "D"), ("4-D", "D"), ("4) d", "D"), ("opcao 4", "D"), ("4", "D"),
    ("4 - A", ""), ("9 - D", ""), ("0", ""), ("4 D", ""), ("", ""),
    ("2 PORTAS", "2 PORTAS"), ("1 - 2 PORTAS", ""), ("2 - 2 PORTAS", "2 PORTAS")])
def test_a_tabela_da_regra(valor, esperado):
    assert DT._opcao_da_resposta(valor, ["A", "2 PORTAS", "C", "D"]) == esperado


def test_lista_com_opcao_NUMERICA_exige_que_texto_e_posicao_concordem():
    assert DT._opcao_da_resposta("2", ["1", "2", "3"]) == "2"      # texto 2 = posição 2
    assert DT._opcao_da_resposta("1", ["3", "2", "1"]) == ""       # texto "1" é a 3ª; posição 1 é "3"
    assert DT._opcao_da_resposta("2", ["3", "2", "1"]) == "2"      # coincidem

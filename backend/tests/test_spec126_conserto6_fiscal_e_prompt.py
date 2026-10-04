# -*- coding: utf-8 -*-
"""SPEC-126 · CONSERTO 6 — as pendências 1, 3 e 4 do juiz final, como guardas.

P1 · `honestidade_do_handoff._RX_SO_ANUNCIO` — no nível da RESPOSTA, "Certo!/Ok./Tudo bem./Perfeito."
     contavam como anúncio de FEITO e tiravam a exceção do fato de terceiro: 📊 sonda do juiz
     (`juiz126f/sonda.py`, 03/10) — 3 frases legítimas passaram de INTACTA para REESCRITA.
P3 · `_status_de_cancelado_na_tool` — QUALQUER ferramenta sustentava o "cancelado": 📊 uma ToolMessage
     de apólice ("status: cancelada") deixava "O guincho foi cancelado pela seguradora." INTACTA.
P4 · `ATTENDANCE_BASE_PROMPT_V2` — o corte tirou "(ou quase igual)" e os "valores" EXATOS do portal.

Nenhuma frase é real; nenhum dado de pessoa. Os textos das ferramentas copiam a FORMA que elas
imprimem (`infocap_tool.py:2248/2297`, `infocap_connector.py:4043`, `portal_params.py:1810`).

🔴 Mutação (uma vez cada, por CÓPIA, restaurada por cópia):
   M1 `_RX_SO_ANUNCIO` volta a aceitar certo/ok/tudo bem/perfeito → P1 vermelhos.
   M2 `_status_de_cancelado_na_tool` sem o filtro por `name` → P3 vermelhos.
   M3 tirar "(ou quase igual)" do v2 → P4 vermelho.  M4 "valores" sai do EXATOS do portal → P4 vermelho.
"""
import hashlib
import os
import re

import pytest

from app.agents import honestidade_do_handoff as H
from app.core import prompts as P

NOTA = H.NOTA_DO_CANCELAMENTO_SEM_FERRAMENTA
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _ToolMsg:
    def __init__(self, name, content):
        self.name, self.content = name, content


# ===========================================================================
# P1 · concordância não é anúncio de feito
# ===========================================================================
#: 📊 as 3 frases do laudo: INTACTAS antes do conserto 5, REESCRITAS depois — voltam INTACTAS.
CONCORDA_E_RELATA_FATO_DE_TERCEIRO = [
    "Certo! O sinistro foi cancelado pela seguradora em 10/09.",
    "Ok. O prestador anterior foi dispensado pela seguradora e um novo está a caminho.",
    "Tudo bem. A vistoria foi desmarcada pela seguradora; ela vai te ligar para remarcar.",
    "Perfeito. O agendamento da vistoria foi cancelado pela seguradora.",
]
#: a linha de CONTROLE: as 9 do BE-2 (conserto 5) continuam reescritas.
BE2 = [
    "O guincho foi cancelado pela seguradora.",
    "Entrei em contato e o guincho foi cancelado pela seguradora.",
    "Seu pedido de guincho foi cancelado pela central, conforme você pediu.",
    "Feito! O guincho foi cancelado pela seguradora.",
    "Tudo bem. O guincho foi cancelado pela seguradora.",
    "Seu guincho foi cancelado pelo sistema.",
    "Seu guincho consta como cancelado.",
    "O guincho anterior foi cancelado.",
    "Seu chaveiro foi dispensado pela assistência.",
]
#: o anúncio de FEITO no começo da resposta continua tirando a exceção do fato de terceiro.
ANUNCIA_FEITO = [
    "Pronto! O sinistro foi cancelado pela seguradora.",
    "Feito! O agendamento da vistoria foi cancelado pela seguradora.",
    "Prontinho. O prestador anterior foi dispensado e um novo está a caminho.",
    "Resolvido! O sinistro foi cancelado pela seguradora.",
]


@pytest.mark.parametrize("texto", CONCORDA_E_RELATA_FATO_DE_TERCEIRO)
def test_p1_concordancia_seguida_de_fato_de_terceiro_fica_intacta(texto):
    assert H.guardar_a_verdade_do_handoff(texto, []) == texto


@pytest.mark.parametrize("texto", BE2)
def test_p1_controle_o_be2_continua_reescrito(texto):
    saida = H.guardar_a_verdade_do_handoff(texto, [])
    assert saida != texto and NOTA in saida, saida


@pytest.mark.parametrize("texto", ANUNCIA_FEITO)
def test_p1_controle_o_anuncio_de_feito_continua_reescrito(texto):
    assert H.guardar_a_verdade_do_handoff(texto, []) == NOTA


def test_p1_controle_pronto_cancelado():
    assert H.guardar_a_verdade_do_handoff("Pronto, cancelado!", []) == NOTA


def test_p1_a_concordancia_sozinha_ainda_sai_quando_a_afirmacao_sai():
    """O "Certo!" não anuncia feito, mas "Certo! Ainda não está cancelado…" soa como concordar."""
    assert H.guardar_a_verdade_do_handoff("Certo! O guincho foi cancelado pela seguradora.", []) == NOTA


@pytest.mark.parametrize("abertura,anuncia", [
    ("Pronto!", True), ("Prontinho.", True), ("Feito!", True), ("Resolvido!", True),
    ("Certo!", False), ("Ok.", False), ("Tudo bem.", False), ("Perfeito.", False),
    ("Beleza!", False), ("Combinado.", False), ("Tudo certo.", False), ("Certinho.", False),
])
def test_p1_so_o_feito_anuncia_no_nivel_da_resposta(abertura, anuncia):
    assert H._resposta_abre_anunciando(abertura + " O sinistro foi cancelado.") is anuncia


# ===========================================================================
# P3 · só a ferramenta de ACIONAMENTO sustenta o status do serviço
# ===========================================================================
SERVICO = "O guincho foi cancelado pela seguradora."
#: a FORMA do infocap (`infocap_tool.py:2248/2297`, `infocap_connector.py:4043`) — apólice, não serviço.
APOLICE_CANCELADA = [
    [_ToolMsg("infocap_policy_lookup", "Apolice localizada no sistema de gestao da corretora:\n"
                                       "- Situacao: Cancelada (nao ativa) - Vigencia: 01/01/2025 a 01/01/2026")],
    [_ToolMsg("infocap_policy_lookup", "- Observacoes: Apolice consta como cancelada.")],
    [_ToolMsg("policy_lookup", "Apólices: 123 status: cancelada (2024) · 456 vigente")],
]
#: a ferramenta de acionamento trazendo o cancelamento DO SERVIÇO (`portal_params.py:1810`).
ACIONAMENTO_CANCELADO = [
    [_ToolMsg("portal_action", "A seguradora mostra este atendimento como cancelado, então eu não "
                               "consigo continuar por aqui.")],
    [_ToolMsg("insurer_dispatch", "O acionamento está cancelado na seguradora.")],
]


@pytest.mark.parametrize("tools", APOLICE_CANCELADA)
def test_p3_status_da_apolice_nao_sustenta_o_servico_cancelado(tools):
    saida = H.guardar_a_verdade_do_handoff(SERVICO, tools)
    assert saida != SERVICO and NOTA in saida, saida


@pytest.mark.parametrize("tools", ACIONAMENTO_CANCELADO)
def test_p3_status_da_ferramenta_de_acionamento_sustenta(tools):
    assert H.guardar_a_verdade_do_handoff(SERVICO, tools) == SERVICO


def test_p3_controle_o_aviso_do_modo_teste_nao_e_status():
    tools = [_ToolMsg("insurer_dispatch", "este acionamento é um teste e será cancelado no final.")]
    assert H.guardar_a_verdade_do_handoff(SERVICO, tools) != SERVICO


def test_p3_controle_o_fato_de_terceiro_que_nao_e_o_servico_segue_intacto_com_a_apolice():
    texto = "O sinistro foi cancelado pela seguradora."
    assert H.guardar_a_verdade_do_handoff(texto, APOLICE_CANCELADA[0]) == texto


def test_p3_os_nomes_sao_os_das_ferramentas_reais():
    """A FORMA da declaração (§9.4, exceção): o `name` que a ferramenta declara é o que o fiscal lê.
    Renomear a ferramenta sem atualizar `TOOLS_DO_STATUS_DO_SERVICO` reabriria o P3 calado."""
    declarados = set()
    for arq in ("insurer_dispatch_tool.py", "portal_tool.py"):
        with open(os.path.join(BACKEND, "app", "agents", "tools", arq), encoding="utf-8") as f:
            declarados |= set(re.findall(r'^\s+name:\s*str\s*=\s*"([^"]+)"', f.read(), re.M))
    assert set(H.TOOLS_DO_STATUS_DO_SERVICO) == declarados, declarados
    assert "infocap_policy_lookup" not in H.TOOLS_DO_STATUS_DO_SERVICO


# ===========================================================================
# P4 · o que o corte do v2 tinha tirado
# ===========================================================================
V1_SHA256 = "2713eee75b689c7b9b7889caa6e61043eb5aaff4a4db645d79d5e469df734a77"


def test_p4_a_mensagem_quase_igual_tambem_nao_se_repete():
    v2 = P.ATTENDANCE_BASE_PROMPT_V2
    assert "Nunca mande a mesma mensagem (ou quase igual) duas vezes" in v2


def test_p4_o_portal_de_vidros_repassa_os_valores_exatos():
    linha = next(l for l in P.ATTENDANCE_BASE_PROMPT_V2.splitlines() if "`portal_action` logo" in l)
    exatos = re.search(r"Mensagem pronta para o segurado[^.]*EXATOS", linha)
    assert exatos and "valores" in exatos.group(0) and "números" in exatos.group(0), linha[:200]


def test_p4_o_v1_byte_a_byte_e_o_teto_do_v2():
    v1, v2 = P.ATTENDANCE_BASE_PROMPT_V1, P.ATTENDANCE_BASE_PROMPT_V2
    assert hashlib.sha256(v1.encode("utf-8")).hexdigest() == V1_SHA256
    assert len(v2) <= 0.62 * len(v1), (len(v2), len(v1))

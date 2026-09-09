# -*- coding: utf-8 -*-
"""O cartão que a atendente lê fala português — e o formulário responde UMA vez.

Três defeitos que chegam ao piloto de 09/09/2026 (AutoFleet: Allianz, HDI,
Yelum, Porto) pelo mesmo caminho: o que sai do corredor para uma pessoa.

A · O DOSSIÊ VAZAVA NOME DE CHAVE
---------------------------------
📊 Medido em 08/09/2026, no texto que o `build_handoff_dossier` produz:

    Seguradora: YELUM · Serviço: maquina_de_lavar
    Motivo: formulario_incompleto:rb_NivelDaRua,rb_InformacoesLocal
    - protocol: 68977599
    - client_phone: 5547988087463

⚠️ Quatro nomes internos numa tela lida com o segurado esperando — e o
`_TITULOS` do `human_handoff` já tinha consertado exatamente isto no OUTRO
dossiê. A correção existia e não tinha atravessado.

🔴 E o guarda não pode ser "procura `maquina_de_lavar`": um mapa que cobre os
casos de hoje não cobre o motivo que alguém escreve amanhã. Por isso [A1]
**varre o código do produto** atrás de todo `session["reason"] = ...` e cobra
uma frase para cada um. Motivo novo sem tradução nasce vermelho.

B · O TELEFONE INTEIRO IA PARA UM GRUPO DE WHATSAPP
---------------------------------------------------
O cartão é reencaminhável e fica no histórico do grupo para sempre. Quatro
dígitos bastam para CONFERIR a conversa; para CHEGAR nela existe o link do
painel — que é a outra metade, e por isso as duas asserções são vizinhas.

C · P-092-10 · O FORMULÁRIO NÃO TINHA TRAVA DE LAÇO
---------------------------------------------------
📊 Medido pelo red team, com linha de controle (PENDENCIAS, P-092-10):

    volta 1..8: state=ura envios=1..8
    BASE 8b49fdb envios=8  ·  HEAD envios=8
    _would_loop diria laço? True   ← existe, responde certo, e nunca é chamado

🔴 O formulário **é** o passo de confirmação da família HDI/Yelum. Oito
confirmações não são oito respostas: são até oito chamados para o mesmo
segurado. [C1] chama o MOTOR (`_responder_formulario_nativo`) com a mesma tela
oito vezes e conta as saídas do dublê — nunca o regex, nunca um helper próprio
(CLAUDE.md §9.4).

D · A FALHA DE ENVIO GUARDAVA SÓ O NOME DA CLASSE
--------------------------------------------------
`session["flow_envio_erro"] = type(exc).__name__` — `"Exception"`, e ninguém
lia. A pergunta do piloto é *"por que o formulário da Yelum não sai?"*, e ela
se responde com STATUS e CORPO. O `reason` ganha o sufixo de máquina porque
`work_events.payload.motivo` (roteador, `eventos_do_travamento`) é o único
campo desta sessão que chega à linha do tempo.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]          # .../backend
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.services import corridor_playbooks as PB           # noqa: E402
from app.services import insurer_dispatch_service as M      # noqa: E402


# ===========================================================================
# O GUARDA DE LÍNGUA
# ===========================================================================
# 🔴 As duas regexes vêm de `test_o_caso_se_explica_sozinho.py` (§ "[E]/[J]/[F]
# O PROMPT E AS CARTAS", `problemas_de_lingua`), que aplica a R11 do Founder às
# cartas do chat. Copiadas COM CRÉDITO e não importadas: aquele arquivo não é
# coletável (é guarda de processo, sem `def test_`), e importá-lo executaria as
# asserções dele dentro desta sessão.
#
# ⚠️ O que NÃO veio junto: a exigência de "terminar numa próxima ação COM
# DONO". Ela é da CARTA ao segurado. Este cartão termina numa próxima ação e
# tem dono — a atendente — mas a redação é outra, e importar a régua errada
# reprovaria por um motivo que não é o desta peça.
_SNAKE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")
_CHAVE = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+(@\d+)?|[a-z]+_[a-z_]+@\d+|\B@\d+\b")

#: 📊 Os enums que o `build_handoff_dossier` imprimia crus em 08/09/2026.
_ENUMS_CRUS = (
    "loop_guard", "sentinela_stall", "missing_slots", "formulario_incompleto",
    "playbook_not_found", "insurer_closed", "handoff_trigger", "human_phase_guard",
    "maquina_de_lavar", "ar_condicionado", "client_phone", "eta_minutes",
    "formulario_envio_falhou", "formulario_em_laco",
)

#: A linha do link é a ÚNICA que pode ter ponto entre minúsculas
#: (`painel.exemplo.com`). Sem esta exceção o `_CHAVE` acusaria o domínio —
#: e o teste ficaria vermelho pela coisa que ele mesmo pediu para existir.
_URL = re.compile(r"https?://\S+")


def problemas_de_lingua_no_cartao(texto: str) -> list:
    """Tudo que um humano não deveria ler neste cartão. Lista vazia = passou."""
    achados = []
    limpo = _URL.sub("«link»", str(texto or ""))
    baixo = limpo.lower()
    for m in _SNAKE.findall(baixo):
        achados.append("snake_case: %r" % m)
    for m in _CHAVE.findall(baixo):
        if m:
            achados.append("chave/versao: %r" % (m,))
    for enum in _ENUMS_CRUS:
        if enum in baixo:
            achados.append("enum cru: %r" % enum)
    return achados


# ===========================================================================
# FIXTURES — a família HDI/Yelum, que é a do formulário nativo
# ===========================================================================
FLOW_ID = "857030507196739"
HDI_AUTO = "hdi-auto-whatsapp@v1"

TELA_DO_FORMULARIO = (
    "Para que a remoção do veículo ocorra sem imprevistos, precisamos entender "
    "o local e as condições do veículo.\n"
    "[FORMULARIO NATIVO: Detalhes do atendimento] (exige clique — não aceita texto)"
)

SLOTS_DO_FORMULARIO = {
    "veiculo_em_garagem": "nao", "veiculo_situacoes": "nenhuma",
    "local_situacao": "seguro", "ocupantes_particularidade": "nenhuma",
    "veiculo_nivel_rua": "nivel da rua",
}

CASO = {
    "titular_cpf": "11122233344", "titular_nome": "Fulano de Tal",
    "veiculo_placa": "ABC1D23",
    "local_atual": "Rua Abelardo Luz, 342, Balneario, Florianopolis - SC",
    "telefone_contato": "48999990000",
    **SLOTS_DO_FORMULARIO,
}

TELEFONE_DO_CLIENTE = "5547988087463"


def _sessao_travada(reason: str, **extra):
    """Uma sessão que parou, pronta para virar cartão. Sem Redis, sem banco."""
    sessao = {
        "state": "needs_human", "reason": reason, "case_id": "caso-1",
        "company_id": "co-teste", "playbook_ref": HDI_AUTO,
        "subservice": "maquina_de_lavar", "slots": dict(CASO),
        "client_phone": TELEFONE_DO_CLIENTE, "transcript": [],
        "captured": {"protocol": "68977599", "eta_minutes": "45",
                     "schedule": {"day": "12/09", "periodo": "manha"},
                     "tracking_link": "https://acompanhe.exemplo/x1"},
    }
    sessao.update(extra)
    return sessao


def _sessao_de_formulario(live=True):
    return {"state": "ura", "slots": dict(SLOTS_DO_FORMULARIO), "transcript": [],
            "subservice": "guincho", "case_id": "c", "live": live,
            "playbook_ref": HDI_AUTO, "flow_token": "TOKEN-DA-SESSAO",
            "envelope_do_flow": "galaxy_message", "flow_id_ativo": FLOW_ID}


@pytest.fixture(autouse=True)
def _ambiente_previsivel(monkeypatch):
    monkeypatch.setenv("INSURER_DISPATCH_LIVE", "true")
    monkeypatch.setenv("DISPATCH_FINALIZE_MODE", "test")
    monkeypatch.delenv("SMITH_WEB_URL", raising=False)
    monkeypatch.delenv("FRONTEND_URL", raising=False)
    monkeypatch.delenv("APP_BASE_URL", raising=False)


# ===========================================================================
# [A] O CARTÃO FALA PORTUGUÊS
# ===========================================================================

#: Onde os motivos nascem. ⚠️ Os três arquivos, porque um motivo escrito no
#: Vigia chega ao MESMO cartão que um motivo escrito no motor.
_FONTES_DE_MOTIVO = (
    "app/services/insurer_dispatch_service.py",
    "app/tasks/dispatch_watchdog.py",
    "app/services/dispatch_router.py",
)
_ATRIBUICAO = re.compile(
    r"""(?:session\["reason"\]\s*=\s*f?["']|["']reason["']\s*:\s*f?["'])([a-z_]+)""")


def _motivos_do_produto() -> set:
    """Todo motivo que o CÓDIGO escreve — varrido, não listado à mão.

    🔴 É esta varredura que faz o guarda envelhecer junto com o produto. Uma
    lista escrita aqui estaria vencida no dia em que alguém acrescentasse um
    ramo de handoff, e o cartão voltaria a vazar chave sem nada ficar vermelho.
    """
    achados = set()
    for rel in _FONTES_DE_MOTIVO:
        fonte = (RAIZ / rel).read_text(encoding="utf-8")
        for linha in fonte.splitlines():
            nu = linha.strip()
            if nu.startswith("#"):
                continue
            achados.update(_ATRIBUICAO.findall(nu))
    return {m for m in achados if m}


def test_A1_todo_motivo_do_produto_tem_frase_em_portugues():
    """Motivo novo sem tradução nasce vermelho — e é este teste que o pega."""
    do_codigo = _motivos_do_produto()
    assert len(do_codigo) >= 15, (
        "a varredura achou %d motivos — ela parou de enxergar o código, e um "
        "guarda que não acha nada aprova tudo" % len(do_codigo))
    sem_frase = sorted(m for m in do_codigo if m not in M._MOTIVOS_EM_PORTUGUES)
    assert not sem_frase, (
        "estes motivos chegam ao cartão da atendente sem tradução: %s" % sem_frase)


def test_A2_o_cartao_nao_tem_uma_chave_para_cada_motivo_conhecido():
    """O motor real, com o motivo real, e a régua sobre o texto que SAI."""
    sujos = {}
    for motivo in sorted(M._MOTIVOS_EM_PORTUGUES):
        # Com sufixo quando o motivo tem sufixo na vida real — é justamente o
        # sufixo (`:rb_NivelDaRua`) que vazava.
        for sufixo in ("", ":veiculo_nivel_rua,local_situacao"):
            texto = M.build_handoff_dossier(_sessao_travada(motivo + sufixo))
            problemas = problemas_de_lingua_no_cartao(texto)
            if problemas:
                sujos[motivo + sufixo] = problemas
    assert not sujos, "o cartão vazou nome de chave: %r" % sujos


def test_A3_o_servico_sai_com_o_nome_que_a_atendente_usa():
    texto = M.build_handoff_dossier(_sessao_travada("loop_guard"))
    assert "MÁQUINA DE LAVAR" in texto, texto[:200]
    assert "maquina_de_lavar" not in texto
    # CONTROLE: a categoria que o `_TITULOS` do `human_handoff` já nomeia sai
    # de lá — se este par quebrar, foi a reutilização que quebrou, não o mapa.
    sessao = _sessao_travada("loop_guard")
    sessao["subservice"] = "guincho"
    assert "GUINCHO" in M.build_handoff_dossier(sessao)


def test_A4_o_que_a_seguradora_entregou_sai_com_nome_humano():
    texto = M.build_handoff_dossier(_sessao_travada("insurer_closed"))
    assert "Protocolo do chamado: 68977599" in texto, texto
    assert "eta_minutes" not in texto and "tracking_link" not in texto
    # O agendamento é um DICIONÁRIO: impresso cru ele entregava
    # `{'day': '12/09', 'periodo': 'manha'}` a quem ia ligar para o segurado.
    assert "12/09, manha" in texto, texto
    assert "'day'" not in texto


def test_A5_motivo_desconhecido_nao_vira_o_proprio_nome():
    """🔴 O `else` que devolvesse a chave crua desfaria o arquivo inteiro."""
    texto = M.build_handoff_dossier(_sessao_travada("motivo_que_ninguem_escreveu_ainda"))
    assert "motivo_que_ninguem_escreveu_ainda" not in texto
    assert "precisa de uma pessoa" in texto
    # CONTROLE: uma frase que JÁ é frase (o Vigia manda assim) passa inteira.
    frase = "Travou na URA e a recuperação automática esgotou"
    assert frase in M.build_handoff_dossier(_sessao_travada(""), frase)


# ===========================================================================
# [B] O TELEFONE E O LINK
# ===========================================================================

def test_B1_o_telefone_do_cliente_nao_sai_inteiro():
    texto = M.build_handoff_dossier(_sessao_travada("loop_guard"))
    assert TELEFONE_DO_CLIENTE not in texto, (
        "o número inteiro do segurado foi para um cartão que vive no histórico "
        "de um grupo de WhatsApp")
    assert "final 7463" in texto, texto
    # E o telefone de contato do caso é telefone do mesmo jeito.
    assert "48999990000" not in texto


def test_B2_com_a_URL_configurada_o_cartao_tem_o_link_do_caso(monkeypatch):
    sessao = _sessao_travada("loop_guard", conversation_id="conv-77")
    assert "Abrir o caso no painel" not in M.build_handoff_dossier(sessao), (
        "sem URL configurada o cartão não pode inventar um link")
    monkeypatch.setenv("SMITH_WEB_URL", "https://painel.exemplo.com")
    com_link = M.build_handoff_dossier(sessao)
    assert "https://painel.exemplo.com/dashboard/atendimentos/conversas?c=conv-77" in com_link, com_link[:300]


def test_B3_sem_conversa_e_sem_URL_a_linha_do_link_some(monkeypatch):
    monkeypatch.setenv("SMITH_WEB_URL", "https://painel.exemplo.com")
    sessao = _sessao_travada("loop_guard")
    sessao.pop("case_id")
    assert "Abrir o caso no painel" not in M.build_handoff_dossier(sessao)


# ===========================================================================
# [C] P-092-10 — O FORMULÁRIO RESPONDE UMA VEZ
# ===========================================================================

def _playbook():
    return PB.get_playbook(HDI_AUTO)


def test_C1_oito_reapresentacoes_do_mesmo_formulario_dao_UM_envio():
    """📊 O laço medido: `volta 1..8 → envios 1..8`. Agora tem de dar 1.

    Chama o MOTOR com a tela REAL — nunca o `_would_loop` direto (§9.4: teste
    que chama o regex guarda o regex).
    """
    envios = []

    def _duble(**kwargs):
        envios.append(kwargs)
        return True

    sessao = _sessao_de_formulario()
    estados = []
    for _volta in range(8):
        saida = M._responder_formulario_nativo(
            sessao, _playbook(), TELA_DO_FORMULARIO, flow_sender=_duble)
        assert saida is not None, "a tela do formulário deixou de ser reconhecida"
        sessao = saida
        estados.append(sessao["state"])

    assert len(envios) == 1, (
        "a seguradora reapresentou a mesma tela 8 vezes e o corredor respondeu "
        "%d — cada resposta é uma confirmação, e confirmação repetida abre "
        "chamado duplicado" % len(envios))
    assert estados[0] == "ura", estados
    assert sessao["state"] == "needs_human" and sessao["reason"] == "formulario_em_laco", (
        sessao.get("state"), sessao.get("reason"))
    assert (sessao.get("formulario_em_laco") or {}).get("reapresentacoes") == 2


def test_C2_CONTROLE_o_primeiro_formulario_ainda_e_respondido():
    """🔴 Sem esta linha, uma trava que recusasse TUDO passaria no [C1]."""
    envios = []
    sessao = M._responder_formulario_nativo(
        _sessao_de_formulario(), _playbook(), TELA_DO_FORMULARIO,
        flow_sender=lambda **k: envios.append(k) or True)
    assert len(envios) == 1 and sessao["state"] == "ura", (envios, sessao["state"])
    assert sessao.get("reason") != "formulario_em_laco"


def test_C3_o_laco_conta_POR_formulario_e_o_cartao_diz_o_que_houve():
    sessao = _sessao_de_formulario()
    for _ in range(2):
        sessao = M._responder_formulario_nativo(
            sessao, _playbook(), TELA_DO_FORMULARIO, flow_sender=lambda **k: True)
    contagens = sessao.get("step_counts") or {}
    assert any(c.startswith("formulario_nativo:") for c in contagens), contagens
    # ⚠️ A chave carrega o `flow_id`: dois formulários diferentes na mesma
    # sessão são duas confirmações legítimas.
    assert f"formulario_nativo:{FLOW_ID}" in contagens, contagens
    sessao["client_phone"] = TELEFONE_DO_CLIENTE
    texto = M.build_handoff_dossier(sessao, sessao["reason"])
    assert "mesmo formulário outra vez" in texto, texto[:300]
    assert not problemas_de_lingua_no_cartao(texto), problemas_de_lingua_no_cartao(texto)


# ===========================================================================
# [D] A FALHA DE ENVIO DEIXA RASTRO
# ===========================================================================

class _RecusaDoProvedor:
    """O que o `EvolutionGoProvider._post` devolve num 4xx — 📊 `SendResult(
    ok=False, error="HTTP 422: {...}")`. O dublê tem a MESMA forma."""

    ok = False

    def __init__(self, erro):
        self.error = erro

    def __bool__(self):
        return False


def test_D1_a_falha_grava_status_corpo_e_flow_id_sem_o_token():
    corpo = ('HTTP 422: {"message":"invalid flow_token","flow_token":'
             '"TOKEN-DA-SESSAO","detail":"nfm reply rejeitada"}')
    sessao = M._responder_formulario_nativo(
        _sessao_de_formulario(), _playbook(), TELA_DO_FORMULARIO,
        flow_sender=lambda **k: _RecusaDoProvedor(corpo))
    diag = sessao.get("flow_envio_erro") or {}
    assert diag.get("status") == 422, diag
    assert diag.get("flow_id") == FLOW_ID, diag
    assert "nfm reply rejeitada" in str(diag.get("corpo")), diag
    # 🔴 O token autoriza responder em nome da corretora: ele NUNCA é gravado.
    assert "TOKEN-DA-SESSAO" not in str(diag), diag
    assert diag.get("flow_token_final") == "SSAO", diag


def test_D2_o_motivo_leva_o_status_para_a_linha_do_tempo():
    """`work_events.payload.motivo` é o único campo desta sessão que chega ao
    banco de eventos — o sufixo existe por causa dele, e o cartão o esconde."""
    sessao = M._responder_formulario_nativo(
        _sessao_de_formulario(), _playbook(), TELA_DO_FORMULARIO,
        flow_sender=lambda **k: _RecusaDoProvedor("HTTP 500: upstream caiu"))
    assert sessao["state"] == "needs_human"
    assert sessao["reason"].startswith("formulario_envio_falhou:"), sessao["reason"]
    assert "http=500" in sessao["reason"], sessao["reason"]
    assert len(sessao["reason"]) <= 180, "não cabe na coluna do evento"
    sessao["client_phone"] = TELEFONE_DO_CLIENTE
    texto = M.build_handoff_dossier(sessao, sessao["reason"])
    assert "http=500" not in texto and "formulario_envio_falhou" not in texto
    assert "o envio falhou" in texto, texto[:300]


def test_D3_excecao_no_transporte_tambem_deixa_rastro():
    def _explode(**kwargs):
        raise RuntimeError("HTTP 503: Service Unavailable")

    sessao = M._responder_formulario_nativo(
        _sessao_de_formulario(), _playbook(), TELA_DO_FORMULARIO,
        flow_sender=_explode)
    diag = sessao.get("flow_envio_erro") or {}
    assert diag.get("erro") == "RuntimeError", diag
    assert diag.get("status") == 503, diag


def test_D4_recusa_MUDA_nao_vira_campo_vazio():
    """📊 O transporte do webhook devolve `bool` hoje: `False` e nada mais.

    ⚠️ Campo vazio parece "ninguém tentou" — e alguém tentou. O diagnóstico
    diz que o transporte recusou sem dizer por quê, em vez de inventar um
    número que ele não recebeu.
    """
    sessao = M._responder_formulario_nativo(
        _sessao_de_formulario(), _playbook(), TELA_DO_FORMULARIO,
        flow_sender=lambda **k: False)
    diag = sessao.get("flow_envio_erro") or {}
    assert diag.get("erro") == "recusa_sem_motivo_do_transporte", diag
    assert diag.get("status") is None, "status inventado sobre um bool"
    assert sessao["reason"].startswith("formulario_envio_falhou"), sessao["reason"]


def test_D5_CONTROLE_o_envio_que_da_certo_nao_grava_erro():
    sessao = M._responder_formulario_nativo(
        _sessao_de_formulario(), _playbook(), TELA_DO_FORMULARIO,
        flow_sender=lambda **k: True)
    assert sessao["state"] == "ura"
    assert not sessao.get("flow_envio_erro"), sessao.get("flow_envio_erro")

# -*- coding: utf-8 -*-
"""SPEC-125 S2 · D1 — o atendimento lembra a conversa INTEIRA, de uma fonte só.

O FIO que o primeiro teste atravessa (CLAUDE.md §9.4 — o motor, nunca uma cópia):
    `messages` (banco dublê, DUAS corretoras com o mesmo telefone)
    → `historico_da_conversa.mensagens_do_turno` (o helper único que `_build_initial_state` chama)
    → o reducer REAL do estado (`add_messages`) sobre o checkpoint ANTIGO (System + 15 de janela)
    → `nodes.agent_node` REAL → o que o MODELO recebe.

📊 Antes (HEAD 67cfe17): o `agent_node` mandava as últimas 15 do checkpointer; numa conversa de 40
mensagens o CPF dito na mensagem 3 não chegava ao modelo (`test_o_fio…` fica VERMELHO na mutação
"janela de 15", ver o relatório da fatia). Nenhum LLM real: o modelo é um dublê que só ANOTA o que recebeu.
"""
from __future__ import annotations

import ast
import asyncio
import os
import re
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage  # noqa: E402
from langgraph.graph.message import add_messages  # noqa: E402

from app.agents import historico_da_conversa as H  # noqa: E402
from app.agents import nodes as N  # noqa: E402
from app.services import o_fim_do_atendimento as F  # noqa: E402

EMPRESA_A = "aaaaaaaa-0000-4000-8000-00000000000a"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-00000000000b"
FONE = "5511900000001"                      # fictício
SESSAO_A = f"whatsapp:{FONE}:{EMPRESA_A}:agente-a"
CPF = "111.222.333-96"                      # fictício (não é CPF de ninguém)
AGORA = datetime.now(timezone.utc)
TURNO = "e aí, já conseguiram acionar o guincho?"


def _iso(dt):
    return dt.isoformat()


# ---------------------------------------------------------------------------
# O banco dublê — só o que o PostgREST faz: filtros, ordem, limite, cursor
# ---------------------------------------------------------------------------
class _Banco:
    def __init__(self, conversas, mensagens, *, ignora_ordem=False):
        self.client, self.conversas, self.mensagens = self, conversas, mensagens
        self.ignora_ordem, self.consultas = ignora_ordem, []

    def table(self, nome):
        banco = self

        class _Q:
            def __init__(self):
                self.f, self.lim, self.desc, self.antes = [], None, False, None

            def select(self, *_a, **_k):
                return self

            def eq(self, c, v):
                self.f.append(("eq", c, v))
                return self

            def in_(self, c, v):
                self.f.append(("in", c, list(v)))
                return self

            def lt(self, c, v):
                self.antes = (c, v)
                return self

            def order(self, c, desc=False):
                self.desc = (c, desc)
                return self

            def limit(self, n):
                self.lim = n
                return self

            async def execute(self):
                banco.consultas.append((nome, list(self.f)))
                rows = banco.conversas if nome == "conversations" else banco.mensagens
                out = []
                for r in rows:
                    ok = True
                    for t, c, v in self.f:
                        if t == "eq" and str(r.get(c)) != str(v):
                            ok = False
                        if t == "in" and str(r.get(c)) not in {str(x) for x in v}:
                            ok = False
                    if ok and self.antes and not str(r.get(self.antes[0])) < str(self.antes[1]):
                        ok = False
                    if ok:
                        out.append(dict(r))
                if self.desc and not banco.ignora_ordem:
                    out.sort(key=lambda r: str(r.get(self.desc[0]) or ""), reverse=self.desc[1])
                if self.lim:
                    out = out[: self.lim]
                return types.SimpleNamespace(data=out)

        return _Q()


def _conversa_de_40():
    """40 mensagens em 3 h — o CPF na mensagem 3, a EQUIPE na 20, uma #nota na 30 —, mais a do turno."""
    inicio = AGORA - timedelta(hours=3)
    msgs = []
    for i in range(1, 41):
        papel = "user" if i % 2 == 1 else "assistant"
        texto = f"mensagem {i} do {'segurado' if papel == 'user' else 'agente'}"
        payload = {}
        if i == 3:
            texto = f"meu cpf é {CPF}, o carro parou na estrada"
        if i == 20:
            texto, payload = "Oi, aqui é a Carla da corretora, já estou vendo o seu caso.", {"origem": "espelho"}
        if i == 30:
            texto, payload = "#nota cliente nervoso, cuidado", {"origem": "dashboard", "nota_interna": True}
        msgs.append({"id": f"a{i}", "conversation_id": "conv-A", "role": papel, "content": texto,
                     "created_at": _iso(inicio + timedelta(minutes=4 * i)), "payload": payload})
    # a linha do TURNO — o webhook a grava ANTES de chamar o agente (passo 5 → 7)
    msgs.append({"id": "a41", "conversation_id": "conv-A", "role": "user", "content": TURNO,
                 "created_at": _iso(AGORA - timedelta(seconds=5)), "payload": {"origem": "agente"}})
    # 🔴 a OUTRA corretora, com o MESMO telefone e — de propósito — a MESMA sessão
    msgs.append({"id": "b1", "conversation_id": "conv-B", "role": "user",
                 "content": "SEGREDO DA CORRETORA B: meu cpf é 999.888.777-66",
                 "created_at": _iso(AGORA - timedelta(minutes=30)), "payload": {}})
    conversas = [
        {"id": "conv-B", "company_id": EMPRESA_B, "session_id": SESSAO_A, "user_phone": FONE[2:],
         "channel": "whatsapp", "updated_at": _iso(AGORA)},
        {"id": "conv-A", "company_id": EMPRESA_A, "session_id": SESSAO_A, "user_phone": FONE[2:],
         "channel": "whatsapp", "updated_at": _iso(AGORA - timedelta(minutes=1))},
    ]
    return conversas, msgs


def _checkpoint_antigo():
    """O checkpoint como o produto o deixava: cada turno [System(prompt inteiro), Human] + a resposta."""
    _, msgs = _conversa_de_40()
    out = []
    for m in msgs[:40]:
        if m["role"] == "user":
            out += [SystemMessage(content="(prompt inteiro do turno, ~26 mil tokens)"),
                    HumanMessage(content=m["content"])]
        else:
            out.append(AIMessage(content=m["content"]))
    return out


class _Modelo:
    """O dublê do modelo: responde 'ok' e ANOTA o que recebeu. Nenhum LLM real."""

    def __init__(self):
        self.recebido = []

    async def ainvoke(self, msgs, config=None, **_k):
        self.recebido = list(msgs)
        return AIMessage(content="ok")


def _estado(mensagens):
    return {"messages": mensagens, "system_prompt": "PROMPT DO TURNO", "static_prompt": "PROMPT DO TURNO",
            "dynamic_context": "", "agent_data": {"agent_role": "core"}, "company_config": {},
            "tools_used": [], "rag_chunks": []}


def _texto(m):
    from app.agents.utils import extract_text_from_content

    return extract_text_from_content(getattr(m, "content", "") or "")


async def _o_que_o_modelo_recebe(db, *, anteriores=None, checkpoint_em=None, company=EMPRESA_A, texto=TURNO):
    novas, hist = await H.mensagens_do_turno(db, company_id=company, session_id=SESSAO_A,
                                             texto_do_turno=texto, anteriores=anteriores,
                                             checkpoint_em=checkpoint_em)
    estado = add_messages(list(anteriores or []), novas)          # o reducer REAL do `AgentState`
    modelo = _Modelo()
    await N.agent_node(_estado(estado), {}, modelo)
    return modelo.recebido, estado, hist


# ===========================================================================
# 1 · O FIO — a mensagem 3 de 40 chega ao modelo
# ===========================================================================
def test_o_fio_o_cpf_da_mensagem_3_chega_ao_modelo():
    conversas, msgs = _conversa_de_40()
    db = _Banco(conversas, msgs)
    recebido, estado, hist = asyncio.run(_o_que_o_modelo_recebe(
        db, anteriores=_checkpoint_antigo(), checkpoint_em=_iso(AGORA - timedelta(minutes=2))))
    textos = [_texto(m) for m in recebido]
    tudo = "\n".join(textos)
    assert hist.lida and hist.conversation_id == "conv-A"
    assert CPF in tudo, "o CPF dito na mensagem 3 não chegou ao modelo"
    assert "mensagem 39 do segurado" in tudo and "mensagem 5 do segurado" in tudo
    # o turno chega UMA vez (a linha que o webhook gravou não duplica a HumanMessage)
    assert sum(TURNO in t for t in textos) == 1 and textos[-1] == TURNO
    # um SystemMessage só, o do turno, na frente — o do checkpoint antigo não volta
    sistemas = [m for m in recebido if isinstance(m, SystemMessage)]
    assert len(sistemas) == 1 and recebido[0] is sistemas[0] and _texto(sistemas[0]) == "PROMPT DO TURNO"
    assert "prompt inteiro do turno" not in tudo
    # e o checkpoint do turno não guarda SystemMessage nenhum
    assert not [m for m in estado if isinstance(m, SystemMessage)]


def test_o_fio_linha_de_controle_a_mesma_conversa_pelo_checkpoint_antigo_perde_o_cpf():
    """§9.2: a MESMA conversa, entregue como o produto entregava (checkpoint + 15) — o CPF some.
    Prova que o teste acima CONSEGUE ficar vermelho: a diferença é a fonte, não o dublê."""
    antigo = _checkpoint_antigo() + [SystemMessage(content="prompt"), HumanMessage(content=TURNO)]
    janela_de_15 = antigo[-15:]
    assert CPF not in "\n".join(_texto(m) for m in janela_de_15)
    assert CPF in "\n".join(_texto(m) for m in antigo)


# ===========================================================================
# 2 · A equipe aparece marcada; a #nota não aparece
# ===========================================================================
def test_a_fala_da_equipe_chega_marcada_e_a_nota_interna_nao():
    conversas, msgs = _conversa_de_40()
    recebido, _, hist = asyncio.run(_o_que_o_modelo_recebe(_Banco(conversas, msgs)))
    tudo = "\n".join(_texto(m) for m in recebido)
    linha = next(t for t in (_texto(m) for m in recebido) if "Carla" in t)
    assert linha.startswith(H.MARCA_DA_EQUIPE), linha
    assert [f.quem for f in hist.falas if "Carla" in f.texto] == ["equipe"]
    assert "cliente nervoso" not in tudo, "a #nota interna chegou ao modelo"
    # o agente não vira 'equipe', nem a equipe vira 'agente'
    assert {f.quem for f in hist.falas} == {"segurado", "agente", "equipe"}


# ===========================================================================
# 3 · Duas corretoras com o MESMO telefone (📊 72 telefones assim) não se misturam
# ===========================================================================
def test_duas_corretoras_com_o_mesmo_telefone_nao_se_misturam():
    conversas, msgs = _conversa_de_40()
    db = _Banco(conversas, msgs)
    recebido, _, _ = asyncio.run(_o_que_o_modelo_recebe(db))
    assert "SEGREDO DA CORRETORA B" not in "\n".join(_texto(m) for m in recebido)
    assert all(("eq", "company_id", EMPRESA_A) in f for n, f in db.consultas if n == "conversations")
    # CONTROLE: a corretora B lê a DELA (e não a de A)
    hist_b = asyncio.run(H.historico_do_atendimento(db, company_id=EMPRESA_B, session_id=SESSAO_A,
                                                    turno_corrente=False))
    textos_b = " ".join(f.texto for f in hist_b.falas)
    assert "SEGREDO DA CORRETORA B" in textos_b and CPF not in textos_b


def test_o_cinto_no_codigo_mesmo_se_o_banco_ignorar_o_filtro():
    """CLAUDE.md §7: o backend é service role — o filtro no código é o que protege."""
    conversas, msgs = _conversa_de_40()

    class _BancoSemFiltro(_Banco):
        def table(self, nome):
            q = super().table(nome)
            q.eq = lambda c, v: q          # o banco "esquece" TODO eq
            return q

    hist = asyncio.run(H.historico_do_atendimento(_BancoSemFiltro(conversas, msgs), company_id=EMPRESA_A,
                                                  session_id=SESSAO_A, turno_corrente=False))
    assert hist.conversation_id == "conv-A"
    assert CPF in " ".join(f.texto for f in hist.falas)
    assert "SEGREDO DA CORRETORA B" not in " ".join(f.texto for f in hist.falas)


# ===========================================================================
# 4 · O teto é por TOKENS, resume o começo e nunca corta calado
# ===========================================================================
def test_o_teto_por_tokens_resume_o_comeco_e_nao_corta_calado():
    falas = [H.Fala("segurado", f"meu cpf é {CPF}" if i == 0 else f"fala {i} " + "x" * 400,
                    AGORA - timedelta(minutes=100 - i)) for i in range(100)]
    mantidas, resumo = H.caber_no_teto(falas, 4000)
    assert mantidas and mantidas[-1] is falas[-1], "a mais nova tem de ficar inteira"
    assert resumo.startswith("[RESUMO DO COMEÇO DESTE ATENDIMENTO")
    fora = len(falas) - len(mantidas)
    assert f"{fora} mensagens" in resumo and CPF in resumo, "o começo sumiu sem aviso"
    assert sum(H.tokens(f.texto) for f in mantidas) + H.tokens(resumo) <= 4000
    # CONTROLE: cabendo, nada é resumido
    assert H.caber_no_teto(falas[:3], 4000) == (falas[:3], "")


def test_o_teto_do_atendimento_cobre_o_maior_assunto_medido():
    # 📊 01/10/2026: máx 15.924 tokens por assunto; p99 4.846 (docstring do módulo)
    assert H.TETO_DO_ATENDIMENTO_TOKENS >= 2 * 15_924
    assert H.TETO_DO_DESTRAVADOR_TOKENS >= 2 * 4_846


# ===========================================================================
# 5 · O recorte é o do ASSUNTO — a régua do reencontro, não uma nova
# ===========================================================================
def _linha(i, papel, dias_atras, texto=None, **payload):
    return {"id": f"x{i}", "role": papel, "content": texto or f"{papel} {i}",
            "created_at": _iso(AGORA - timedelta(days=dias_atras)), "payload": payload}


def test_o_assunto_comeca_onde_o_reencontro_diz_assunto_novo(monkeypatch):
    monkeypatch.delenv("JANELA_SILENCIO_HUMANO_DIAS", raising=False)
    velho = [_linha(1, "user", 40, f"cpf {CPF} do caso de agosto"), _linha(2, "assistant", 40)]
    novo = [_linha(3, "user", 0.001, "oi de novo, preciso de chaveiro")]
    falas, inicio = H.falas_do_assunto(velho + novo, turno_corrente=False)
    assert [f.texto for f in falas] == ["oi de novo, preciso de chaveiro"]
    # a MESMA régua: o motor do reencontro, perguntado na fala que abriu o assunto, diz ASSUNTO NOVO
    bloco = F.contexto_do_reencontro(velho, agora=AGORA)
    assert "ASSUNTO NOVO" in bloco
    # CONTROLE: 2 dias de silêncio não abrem assunto
    perto = [_linha(1, "user", 2, f"cpf {CPF}"), _linha(2, "assistant", 2)] + novo
    assert len(H.falas_do_assunto(perto, turno_corrente=False)[0]) == 3


def test_as_falas_vencidas_ficam_fora_como_na_regra_dos_7_dias(monkeypatch):
    monkeypatch.delenv("JANELA_SILENCIO_HUMANO_DIAS", raising=False)
    linhas = [_linha(1, "assistant", 9, "atendente: qualquer coisa me chame"),
              _linha(2, "user", 6, "dia 3: ninguém respondeu"),
              _linha(3, "user", 4, "dia 5: ainda nada"),
              _linha(4, "user", 0.001, "hoje: preciso de guincho")]
    falas, _ = H.falas_do_assunto(linhas, turno_corrente=False)
    assert [f.texto for f in falas] == ["hoje: preciso de guincho"]
    # a régua do produto concorda: as duas do meio são as VENCIDAS
    vencidas = F.mensagens_vencidas(linhas[:3], agora=AGORA - timedelta(minutes=1))
    assert [m["content"] for m in vencidas] == ["dia 3: ninguém respondeu", "dia 5: ainda nada"]


def test_o_resolvido_em_fecha_o_atendimento_anterior():
    linhas = [_linha(1, "user", 1, f"cpf {CPF}"), _linha(2, "assistant", 0.9, "acionado, protocolo 123"),
              _linha(3, "user", 0.01, "outra coisa agora")]
    resolvido = _iso(AGORA - timedelta(days=0.5))
    falas, _ = H.falas_do_assunto(linhas, turno_corrente=False, resolvido_em=resolvido)
    assert [f.texto for f in falas] == ["outra coisa agora"]
    assert len(H.falas_do_assunto(linhas, turno_corrente=False)[0]) == 3      # controle


# ===========================================================================
# 6 · O destravador recebe a MESMA conversa, ordenada, da conversa MAIS RECENTE
# ===========================================================================
def test_o_destravador_recebe_a_conversa_inteira_ordenada(monkeypatch):
    import app.core.database as core_db
    from app.services import destravador as DT

    antiga_conv = {"id": "conv-velha", "company_id": EMPRESA_A, "user_phone": FONE[2:], "channel": "whatsapp",
                   "updated_at": _iso(AGORA - timedelta(days=90))}
    nova_conv = {"id": "conv-nova", "company_id": EMPRESA_A, "user_phone": FONE[2:], "channel": "whatsapp",
                 "updated_at": _iso(AGORA - timedelta(minutes=3))}
    msgs = [{"id": "v1", "conversation_id": "conv-velha", "role": "user", "content": "CONVERSA VELHA",
             "created_at": _iso(AGORA - timedelta(days=90)), "payload": {}}]
    for i in range(1, 31):               # 30 falas: o dobro da janela antiga de 15
        msgs.append({"id": f"n{i}", "conversation_id": "conv-nova", "role": "user" if i % 2 else "assistant",
                     "content": (f"fala {i:02d} " + ("y" * 500 if i == 2 else "")),
                     "created_at": _iso(AGORA - timedelta(minutes=60 - i)), "payload": {}})
    msgs.reverse()                        # o banco devolve fora de ordem
    db = _Banco([antiga_conv, nova_conv], msgs, ignora_ordem=True)   # e ignora o `.order`
    monkeypatch.setattr(core_db, "get_supabase_client", lambda: db)
    linhas = asyncio.run(DT._conversa_do_segurado(EMPRESA_A, {"client_phone": FONE}))
    assert "CONVERSA VELHA" not in "\n".join(linhas), "pegou a conversa arbitrária, não a mais recente"
    assert len(linhas) == 30 and linhas[0].startswith("[segurado] fala 01") and "fala 30" in linhas[-1]
    assert [int(re.search(r"fala (\d+)", x).group(1)) for x in linhas] == list(range(1, 31))
    assert "y" * 500 in linhas[1], "a fala longa foi cortada em 300 chars"


# ===========================================================================
# 7 · O que a ferramenta apurou atravessa o turno — só no MESMO assunto
# ===========================================================================
def _par(nome, conteudo, i):
    return [AIMessage(content="", tool_calls=[{"name": nome, "args": {}, "id": f"c{i}", "type": "tool_call"}]),
            ToolMessage(content=conteudo, tool_call_id=f"c{i}", name=nome)]


def test_o_acionamento_do_turno_anterior_atravessa_e_o_rag_e_comprimido():
    from app.agents.honestidade_do_handoff import _houve_acionamento_confirmado

    conversas, msgs = _conversa_de_40()
    anterior = ([HumanMessage(content="mensagem 39 do segurado")]
                + _par("knowledge_base_search", '{"content": "TRECHO ENORME DO MANUAL"}', 1)
                + _par("insurer_dispatch", "[ACIONAMENTO REAL INICIADO] protocolo 4455", 2)
                + [AIMessage(content="mensagem 40 do agente")])
    recebido, estado, _ = asyncio.run(_o_que_o_modelo_recebe(
        _Banco(conversas, msgs), anteriores=anterior, checkpoint_em=_iso(AGORA - timedelta(minutes=1))))
    tudo = "\n".join(_texto(m) for m in recebido)
    assert "[ACIONAMENTO REAL INICIADO] protocolo 4455" in tudo
    assert "TRECHO ENORME DO MANUAL" not in tudo and H.CONTEUDO_COMPRIMIDO in tudo
    assert _houve_acionamento_confirmado(estado), "o fiscal da S1 não vê mais o acionamento do turno anterior"
    # CONTROLE: assunto NOVO (o checkpoint é de antes do começo do assunto) → nada atravessa
    _, estado2, _ = asyncio.run(_o_que_o_modelo_recebe(
        _Banco(conversas, msgs), anteriores=anterior, checkpoint_em=_iso(AGORA - timedelta(days=30))))
    assert not _houve_acionamento_confirmado(estado2)


def test_o_checkpoint_do_regime_antigo_so_entrega_os_turnos_do_assunto():
    hist = H.Historico(falas=[H.Fala("segurado", "a"), H.Fala("agente", "b")], lida=True,
                       inicio=AGORA - timedelta(hours=1))
    antigo = ([SystemMessage(content="p"), HumanMessage(content="assunto de março")]
              + _par("insurer_dispatch", "[ACIONAMENTO REAL INICIADO] março", 1)
              + [SystemMessage(content="p"), HumanMessage(content="a")]
              + _par("infocap_policy_lookup", "APÓLICE DO ONIX", 2))
    out = H.resultados_que_continuam(antigo, hist=hist)
    textos = [_texto(m) for m in out]
    assert "APÓLICE DO ONIX" in textos and not any("março" in t for t in textos)


# ===========================================================================
# 8 · O `agent_node` não corta por CONTAGEM — e a apólice da 1ª rodada não some na 2ª
# ===========================================================================
def test_o_agent_node_nao_corta_por_contagem():
    msgs = []
    for i in range(60):
        msgs += [HumanMessage(content=f"pergunta {i}"), AIMessage(content=f"resposta {i}")]
    msgs.append(HumanMessage(content="e a primeira?"))
    modelo = _Modelo()
    asyncio.run(N.agent_node(_estado(msgs), {}, modelo))
    assert "pergunta 0" in "\n".join(_texto(m) for m in modelo.recebido)


def test_a_apolice_da_rodada_anterior_do_mesmo_turno_chega_inteira():
    msgs = ([HumanMessage(content="meu guincho")] + _par("infocap_policy_lookup", "APÓLICE: Onix, placa ***1234", 1)
            + _par("insurer_dispatch", "[ACIONAMENTO REAL INICIADO]", 2))
    modelo = _Modelo()
    asyncio.run(N.agent_node(_estado(msgs), {}, modelo))
    assert "APÓLICE: Onix, placa ***1234" in "\n".join(_texto(m) for m in modelo.recebido)


def test_aparar_ao_teto_nunca_corta_o_turno_e_avisa_o_que_ficou_fora():
    velhas = [HumanMessage(content="z" * 4000) for _ in range(20)]
    turno = [HumanMessage(content="AGORA")] + _par("knowledge_base_search", "q" * 80_000, 9)
    out = H.aparar_ao_teto(velhas + turno, teto=3000)
    assert out[-3:] == turno
    assert _texto(out[0]).startswith("[Nota do sistema:") and "ficaram fora" in _texto(out[0])


# ===========================================================================
# 9 · Sem conversa lida, nada se apaga: o checkpointer segue sendo a memória
# ===========================================================================
def test_sem_conversa_no_banco_o_checkpoint_nao_e_apagado():
    novas, hist = asyncio.run(H.mensagens_do_turno(_Banco([], []), company_id=EMPRESA_A, session_id=SESSAO_A,
                                                   texto_do_turno="oi"))
    assert not hist.lida and [type(m).__name__ for m in novas] == ["HumanMessage"]

    class _BancoFora(_Banco):
        def table(self, nome):
            raise ConnectionError("banco fora")

    novas, hist = asyncio.run(H.mensagens_do_turno(_BancoFora([], []), company_id=EMPRESA_A,
                                                   session_id=SESSAO_A, texto_do_turno="oi"))
    assert hist.erro == "ConnectionError" and len(novas) == 1


# ===========================================================================
# 10 · A costura e a faxina — o que precisa CONTINUAR verdade
# ===========================================================================
def _fonte(*partes):
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def test_o_build_initial_state_usa_o_helper_e_nao_grava_system_no_historico():
    arvore = ast.parse(_fonte("app", "agents", "graph.py"))
    fn = next(n for n in ast.walk(arvore) if isinstance(n, ast.AsyncFunctionDef) and n.name == "_build_initial_state")
    corpo = ast.get_source_segment(_fonte("app", "agents", "graph.py"), fn)
    assert "mensagens_do_turno(" in corpo
    assert "SystemMessage(" not in corpo, "o SystemMessage voltou para o histórico/checkpoint"
    assert "graph=graph" in _fonte("app", "agents", "graph.py")


def test_nao_existe_mais_janela_por_contagem():
    proibidos = ("AGENT_CONTEXT_WINDOW_SIZE", "CHAT_HISTORY_WINDOW", "JANELA_CONTEXTO")
    achados = []
    for base, _dirs, arquivos in os.walk(os.path.join(RAIZ, "app")):
        for a in arquivos:
            if a.endswith(".py"):
                txt = open(os.path.join(base, a), encoding="utf-8", errors="ignore").read()
                achados += [f"{a}:{p}" for p in proibidos if re.search(rf"\b{p}\s*=|\b{p}\b(?!`)", txt)
                            and not a.startswith("historico_da_conversa")]
    # `langchain_service` cita o nome antigo só no comentário que conta por que ele morreu
    achados = [x for x in achados if not x.startswith("langchain_service.py:CHAT_HISTORY_WINDOW")]
    assert achados == []
    assert "\nCHAT_HISTORY_WINDOW=" not in _fonte(".env.example")


# ===========================================================================
# 11 · O telefone em TODAS as grafias (📊 905 de 1.081 conversas guardam o 55)
# ===========================================================================
@pytest.mark.parametrize("gravado", ["5511987654321", "11987654321", "551187654321", "1187654321"])
@pytest.mark.parametrize("pedido", ["5511987654321", "11987654321", "+55 (11) 98765-4321", "1187654321"])
def test_a_conversa_se_acha_pelo_telefone_em_qualquer_grafia(gravado, pedido):
    conversas = [{"id": "conv-A", "company_id": EMPRESA_A, "user_phone": gravado, "channel": "whatsapp",
                  "updated_at": _iso(AGORA)},
                 {"id": "conv-B", "company_id": EMPRESA_B, "user_phone": gravado, "channel": "whatsapp",
                  "updated_at": _iso(AGORA)}]
    msgs = [{"id": "m1", "conversation_id": "conv-A", "role": "user", "content": f"meu cpf é {CPF}",
             "created_at": _iso(AGORA - timedelta(minutes=5)), "payload": {}},
            {"id": "m2", "conversation_id": "conv-B", "role": "user", "content": "SEGREDO DA CORRETORA B",
             "created_at": _iso(AGORA - timedelta(minutes=5)), "payload": {}}]
    hist = asyncio.run(H.historico_do_atendimento(_Banco(conversas, msgs), company_id=EMPRESA_A,
                                                  telefone=pedido, turno_corrente=False))
    assert hist.lida and hist.conversation_id == "conv-A", (gravado, pedido)
    assert [f.texto for f in hist.falas] == [f"meu cpf é {CPF}"]


def test_o_cerebro_antes_do_segurado_le_pelo_mesmo_helper(monkeypatch):
    """`dispatch_router._texto_da_conversa_do_segurado` (o localizador do Cérebro) — a MESMA fonte."""
    import app.core.database as core_db
    from app.services import dispatch_router as DR

    conversas, msgs = _conversa_de_40()
    for c in conversas:
        c["user_phone"] = FONE                     # gravado COM o 55, como 905 de 1.081
    monkeypatch.setattr(core_db, "get_supabase_client", lambda: _Banco(conversas, msgs))
    texto = asyncio.run(DR._texto_da_conversa_do_segurado(EMPRESA_A, {"client_phone": FONE[2:]}))
    assert CPF in texto and "SEGREDO DA CORRETORA B" not in texto
    assert texto.index("mensagem 5 do segurado") < texto.index("mensagem 39 do segurado")

# -*- coding: utf-8 -*-
"""O grupo de suporte recebe o caso INTEIRO — e só quando é do agente. SPEC-120.

AS REGRAS DO FOUNDER (28/09/2026), que este arquivo transforma em vermelho
=======================================================================
D15  *"as informações não podem ser mascaradas, precisam ser reais e completas
      porque é um humano da corretora"*
D16  *"não deve ficar enviando dossiês antigos. É um aviso só na hora do
      atendimento"* — a prova de COMPORTAMENTO do vigia mora em
      `test_o_grupo_so_e_chamado_quando_alguem_espera.py`.
D17  *"agente não se mete em atendimento de humano e não envia msg no suporte
      humano quando o humano estiver atendendo"*
E o relatório das 19h, pedido por escrito: *"nome do segurado, número do
protocolo, tipo de serviço e seguradora e WhatsApp"*.

O DEFEITO QUE A PONTE CARREGAVA, MEDIDO
=======================================
📊 `o_fim_do_atendimento._contar_a_conclusao` chamava o modelo do ✅ com
`servico=""` — literal, sempre. A sessão do acionamento sabia o serviço, a
seguradora e o protocolo; só o id da conversa atravessava
`dispatch_router._marcar_fim_do_atendimento` → `marcar_fim`. O grupo nunca
soube O QUE foi resolvido, e o resumo das 19h só conseguia CONTAR.

🔴 Toda asserção chama o MOTOR (CLAUDE.md §9.4). Nenhum regex sobre o fonte.
⛔ Nenhum dado real: nomes e telefones são sintéticos (§13.9).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.services import dispatch_router as R
from app.services import o_fim_do_atendimento as FIM
from app.services import o_grupo_so_o_que_importa as G
from app.services import os_modelos_do_grupo as MOD

EMPRESA = "00000000-0000-4000-8000-00000000000a"
OUTRA_EMPRESA = "00000000-0000-4000-8000-00000000000b"
CONVERSA = "11111111-1111-4111-8111-111111111111"


# ---------------------------------------------------------------------------
# dublês — só a BORDA (banco). O que se mede é o motor.
# ---------------------------------------------------------------------------
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    """Encadeia `.select().eq().in_().gte().lt().limit()` e ANOTA os filtros."""

    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.filtros = banco, tabela, []

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self.filtros.append(("eq", campo, valor))
        return self

    def in_(self, campo, valores):
        self.filtros.append(("in", campo, tuple(valores)))
        return self

    def gte(self, *_a):
        return self

    def lt(self, *_a):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def range(self, *_a):
        return self

    def insert(self, linha):
        self.banco.inseridos.append((self.tabela, linha))
        return self

    def execute(self):
        self.banco.consultas.append((self.tabela, list(self.filtros)))
        linhas = self.banco.tabelas.get(self.tabela, [])
        # aplica os filtros de igualdade e de lista — um dublê que ignorasse o
        # filtro esconderia um vazamento entre corretoras (§7)
        for tipo, campo, valor in self.filtros:
            if tipo == "eq":
                linhas = [l for l in linhas if str(l.get(campo)) == str(valor)]
            elif tipo == "in":
                linhas = [l for l in linhas if str(l.get(campo)) in {str(v) for v in valor}]
        return _Resp(linhas)


class _Banco:
    def __init__(self, **tabelas):
        self.tabelas = tabelas
        self.consultas, self.inseridos = [], []

    def table(self, nome):
        return _Consulta(self, nome)


# ===========================================================================
# 1 · A PONTE entrega serviço, seguradora e protocolo
# ===========================================================================
def _sessao(protocolo="2026-0928-4471"):
    return {"playbook_ref": "yelum-auto-whatsapp@v3", "subservice": "guincho",
            "captured": {"protocol": protocolo},
            "mirror_conversation_id": CONVERSA}


def test_a_ponte_entrega_servico_seguradora_e_protocolo(monkeypatch):
    visto = {}

    async def _marcar_fim(db, **k):
        visto.update(k)
        return True, k.get("motivo")

    async def _sem_episodio(*_a, **_k):
        return ""

    monkeypatch.setattr(FIM, "marcar_fim", _marcar_fim)
    monkeypatch.setattr(R, "_episodio_do_atendimento", _sem_episodio)
    asyncio.run(R._marcar_fim_do_atendimento(_Banco(), EMPRESA, _sessao(), "resolvido"))

    assert visto.get("motivo") == FIM.ACIONAMENTO_CONCLUIDO, visto
    assert visto.get("detalhes") == {"servico": "GUINCHO", "seguradora": "YELUM",
                                     "protocolo": "2026-0928-4471"}, visto


def test_controle_fase_que_nao_encerra_nao_atravessa_a_ponte(monkeypatch):
    """🔴 CONTROLE: `needs_human` NÃO termina o atendimento — tem gente esperando."""
    chamado = []

    async def _marcar_fim(db, **k):
        chamado.append(k)
        return True, ""

    monkeypatch.setattr(FIM, "marcar_fim", _marcar_fim)
    asyncio.run(R._marcar_fim_do_atendimento(_Banco(), EMPRESA, _sessao(), "needs_human"))
    assert chamado == []


# ===========================================================================
# 2 · O ✅ diz O QUE foi feito — e a assistência fica anotada para as 19h
# ===========================================================================
def _conclusao(monkeypatch, motivo, detalhes):
    enviados, anotados = [], []

    async def _enviar(db, **k):
        enviados.append(k)
        return {"enviado": True, "calado": False, "motivo": ""}

    async def _anotar(db, company_id, tipo, mensagem, carga, **_k):
        anotados.append((company_id, tipo, carga))
        return True

    monkeypatch.setattr(G, "enviar_ao_grupo", _enviar)
    monkeypatch.setattr(G, "anotar_no_diario", _anotar)
    banco = _Banco(conversations=[{"id": CONVERSA, "company_id": EMPRESA,
                                   "user_name": "Fulana Sintetica",
                                   "user_phone": "5548900000001"}])
    asyncio.run(FIM._contar_a_conclusao(banco, EMPRESA, CONVERSA, motivo,
                                        detalhes=detalhes))
    return enviados, anotados


def test_o_check_leva_servico_seguradora_e_protocolo(monkeypatch):
    enviados, anotados = _conclusao(
        monkeypatch, FIM.ACIONAMENTO_CONCLUIDO,
        {"servico": "GUINCHO", "seguradora": "YELUM", "protocolo": "2026-0928-4471"})
    assert len(enviados) == 1
    texto = enviados[0]["texto"]
    assert "GUINCHO · YELUM" in texto, texto
    assert "protocolo 2026-0928-4471" in texto, texto
    # e a assistência do dia ficou anotada, com o que a lista das 19h precisa
    assert (EMPRESA, FIM.EVENTO_ASSISTENCIA_DO_DIA,
            {"conversa_id": CONVERSA, "servico": "GUINCHO", "seguradora": "YELUM",
             "protocolo": "2026-0928-4471"}) in anotados, anotados


def test_controle_sem_detalhes_o_check_volta_a_ser_so_o_nome(monkeypatch):
    """🔴 CONTROLE: prova que o texto acima VEIO dos detalhes, não de um fixo."""
    enviados, _ = _conclusao(monkeypatch, FIM.ACIONAMENTO_CONCLUIDO, None)
    assert "GUINCHO" not in enviados[0]["texto"]
    assert "protocolo" not in enviados[0]["texto"]


def test_fechado_por_humano_nao_vira_assistencia_do_agente(monkeypatch):
    """⛔ A lista das 19h é das assistências que o AGENTE abriu."""
    _, anotados = _conclusao(monkeypatch, FIM.FECHADO_POR_HUMANO,
                             {"servico": "GUINCHO", "seguradora": "YELUM", "protocolo": "1"})
    assert not [a for a in anotados if a[1] == FIM.EVENTO_ASSISTENCIA_DO_DIA], anotados


# ===========================================================================
# 3 · O RESUMO DAS 19h lista as assistências
# ===========================================================================
LISTA = [
    {"nome": "Fulana Sintetica", "servico": "GUINCHO", "seguradora": "YELUM",
     "protocolo": "2026-0928-4471", "whatsapp": "https://wa.me/5548900000001"},
    {"nome": "", "servico": "CHAVEIRO", "seguradora": "PORTO",
     "protocolo": "", "whatsapp": "https://wa.me/5548900000002"},
]


def test_o_resumo_das_19h_lista_nome_servico_seguradora_protocolo_e_whatsapp():
    texto = MOD.modelo_resumo_do_dia("28/09", {"acionamentos_entregues": 2}, LISTA)
    assert "*ASSISTÊNCIAS ABERTAS HOJE* (2)" in texto, texto
    assert "1. Fulana Sintetica · GUINCHO · YELUM · protocolo 2026-0928-4471" in texto
    assert "https://wa.me/5548900000001" in texto
    # campo que não existe SOME da linha — nunca vira "—" inventado
    assert "2. segurado · CHAVEIRO · PORTO" in texto
    assert "PORTO · protocolo" not in texto


def test_controle_dia_sem_nada_continua_sem_mensagem():
    """🔴 A regra antiga continua: dia sem movimento não manda "não houve nada"."""
    assert MOD.modelo_resumo_do_dia("28/09", {}, []) == ""


def test_um_dia_so_com_assistencias_ainda_manda_o_resumo():
    """Uma assistência calada (atendente na conversa) conta como movimento."""
    assert "ASSISTÊNCIAS ABERTAS HOJE" in MOD.modelo_resumo_do_dia("28/09", {}, LISTA[:1])


# ===========================================================================
# 4 · A LISTA só lê a PRÓPRIA corretora (§7) — e sai inteira (D15)
# ===========================================================================
def test_a_lista_so_le_a_propria_corretora_e_sai_inteira(monkeypatch):
    banco = _Banco(
        work_events=[
            {"id": 1, "company_id": EMPRESA, "event_type": FIM.EVENTO_ASSISTENCIA_DO_DIA,
             "created_at": "2026-09-28T13:00:00+00:00",
             "payload_redacted": {"conversa_id": CONVERSA, "servico": "GUINCHO",
                                  "seguradora": "YELUM", "protocolo": "2026-0928-4471"}},
            {"id": 2, "company_id": OUTRA_EMPRESA, "event_type": FIM.EVENTO_ASSISTENCIA_DO_DIA,
             "created_at": "2026-09-28T14:00:00+00:00",
             "payload_redacted": {"conversa_id": "outra", "servico": "PNEU",
                                  "seguradora": "HDI", "protocolo": "999"}},
        ],
        conversations=[{"id": CONVERSA, "company_id": EMPRESA,
                        "user_name": "Fulana Sintetica", "user_phone": "5548900000001"}])

    async def _paginado(consulta, **_k):
        return consulta().execute().data, False

    import app.leitura_completa as LC
    monkeypatch.setattr(LC, "ler_paginado_async", _paginado)
    agora = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    lista = asyncio.run(MOD.assistencias_do_dia(banco, EMPRESA, agora, agora + timedelta(days=1)))

    assert lista == [{"nome": "Fulana Sintetica", "servico": "GUINCHO", "seguradora": "YELUM",
                      "protocolo": "2026-0928-4471",
                      "whatsapp": "https://wa.me/5548900000001"}], lista
    # 🔴 as DUAS leituras filtraram pela corretora
    for tabela in ("work_events", "conversations"):
        filtros = [f for t, fs in banco.consultas if t == tabela for f in fs]
        assert ("eq", "company_id", EMPRESA) in filtros, (tabela, filtros)


# ===========================================================================
# 5 · D17 — com humano atendendo, o grupo NÃO recebe
# ===========================================================================
def test_atendente_que_assumiu_pelo_celular_cala_o_grupo():
    """📊 Quem assume PELO CELULAR grava só `claimed_by_name` (espelho_chat.py:712).
    O vigia antigo decidia por `claimed_by` e não a via — era a contradição do
    print do Founder: "sem atendimento" e "já assumiu" na mesma mensagem."""
    agora = datetime.now(timezone.utc)
    conversa = {"claimed_by": None, "claimed_by_name": "Atendente pelo celular",
                "claimed_at": (agora - timedelta(minutes=10)).isoformat()}
    calado, _porque = G._assumida_com_claim_fresco(conversa, agora)
    assert calado is True


def test_controle_sem_ninguem_atendendo_o_grupo_ouve():
    """🔴 CONTROLE: a mesma pergunta, sem dono, deixa passar — senão o de cima
    seria um porteiro que cala tudo."""
    agora = datetime.now(timezone.utc)
    calado, _ = G._assumida_com_claim_fresco(
        {"claimed_by": None, "claimed_by_name": None, "claimed_at": None}, agora)
    assert calado is False


# ===========================================================================
# 6 · O DOSSIÊ NUNCA LEVANTA por causa do link — e a reserva não mascara
# ===========================================================================
def _sessao_travada():
    from app.services.insurer_dispatch_service import new_dispatch_session
    s = new_dispatch_session(case_id="t", company_id=EMPRESA,
                             playbook_ref="yelum-auto-whatsapp@v3", subservice="guincho",
                             slots={"titular_cpf": "11122233344",
                                    "telefone_contato": "48900000009"})
    s.update({"state": "needs_human", "client_phone": "5548900000001"})
    return s


def test_sem_o_montador_de_link_o_dossie_sai_com_o_numero_inteiro(monkeypatch):
    """📊 28/09: três guardas com pacote `app.services` de mentira derrubavam o
    dossiê com `ModuleNotFoundError`. Dossiê que levanta = nenhum humano avisado."""
    import sys
    from app.services import insurer_dispatch_service as D
    monkeypatch.setitem(sys.modules, "app.services.os_modelos_do_grupo", None)  # import falha
    texto = D.build_handoff_dossier(_sessao_travada(), "loop_guard")
    assert "5548900000001" in texto and "48900000009" in texto, texto
    assert "final " not in texto, "a reserva voltou a mascarar (D15)"


def test_controle_com_o_montador_o_numero_sai_clicavel():
    """🔴 CONTROLE: prova que o teste acima exercitou a RESERVA, não o caminho normal."""
    from app.services import insurer_dispatch_service as D
    texto = D.build_handoff_dossier(_sessao_travada(), "loop_guard")
    assert "https://wa.me/5548900000001" in texto, texto

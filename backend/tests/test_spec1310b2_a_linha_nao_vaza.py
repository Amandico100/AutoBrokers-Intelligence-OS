# -*- coding: utf-8 -*-
"""modelo: claude-opus-5-5 · SPEC-131-0-B2 · CONSERTO ÚNICO — A LINHA NÃO VAZA.

A linha do usuário (`purpose='linha_do_usuario'`) é o WhatsApp PESSOAL de um corretor. Ela nasce como qualquer linha
de `integrations` (`is_active`, `evolution-go`, `agent_id NULL`) — e o juiz e o red team mediram que os leitores que já
existiam e não olhavam o purpose a tratavam como canal da corretora. Este arquivo roda os SELETORES REAIS contra um
banco dublê com o observador + a linha (dublê SÓ na borda: banco, HTTP do provedor, envio):

    B1  nenhum caminho de SAÍDA escolhe a linha: `pode_enviar` (nos dois regimes, mesmo com a autorização de auxiliar),
        a cobrança, a rotina, o canal de plataforma (Vigia/follow-up/relatório/sugestão), a busca da corretora sem
        agente (acompanhamento/acionamento/portal), o alerta de queda, o QCM, a prova de formulário (origem E destino)
    B2  o heartbeat religa a linha com o corpo do pareamento dela (SEM `HISTORY_SYNC`), não abre cartão na Caixa do
        Admin nem alarme de entrega, e registra a queda pela função da linha; as rotas legadas por corretora+purpose
        não a resolvem; o briefing (detector de conexões) não a lista
    B3  o número da linha não é "número de corretora" (QCM) nem "número do produto" (central 132-C) — e isso não abre
        laço: o que o central/QCM manda a esse número chega à instância da linha como conversa ALHEIA → descartado
    P1  evento `fromMe` SEM `Chat` é descartado no portão da linha (o conversor comum cai no `Sender` = a própria conta)

Cada caso tem a sua LINHA DE CONTROLE (o mesmo seletor dizendo o outro resultado para um canal legítimo).
A LINHA DE CONTROLE DO CONSERTO: `python tests/test_spec1310b2_a_linha_nao_vaza.py --mutar` troca, POR CÓPIA, os
arquivos de cada conserto (B1 · B2 · B3 · P1) pela versão de antes (`923e9e2`), exige VERMELHO e restaura por cópia.
⛔ Dados fictícios (5511900000xxx, "Corretora Alfa"); nenhum nome de corretora real (CLAUDE.md §13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec1310b2_a_linha_nao_vaza.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

CID_A = "aaaaaaaa-0000-4000-8000-0000000000a1"        # 💭 uma corretora
CID_PLAT = "cccccccc-0000-4000-8000-0000000000c1"     # 💭 a empresa da plataforma (o QCM)
UID_1 = "11111111-0000-4000-8000-000000000001"        # 💭 o corretor dono da linha
NUM_LINHA = "+5511900000101"                          # 💭 o WhatsApp PESSOAL do corretor
NUM_OBS = "+5511900000201"                            # 💭 o observador da corretora
NUM_CENTRAL = "5511900000301"                         # 💭 o número do assistente (central 132-C)
SEGURADO = "5511900000401"                            # 💭 um cliente


# =====================================================================================================================
# o banco dublê (a BORDA) — supabase-py em memória, síncrono e assíncrono
# =====================================================================================================================
class _Q:
    def __init__(self, db, tabela, assincrono=False):
        self.db, self.tabela, self.assincrono = db, tabela, assincrono
        self.filtros, self.op, self.valores, self._limit = [], "select", None, None

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def update(self, valores):
        self.op, self.valores = "update", valores
        return self

    def insert(self, valores):
        self.op, self.valores = "insert", valores
        return self

    def eq(self, c, v):
        self.filtros.append(lambda r, c=c, v=v: (r.get(c) is v) if isinstance(v, bool) else str(r.get(c)) == str(v))
        return self

    def neq(self, c, v):
        self.filtros.append(lambda r, c=c, v=v: str(r.get(c)) != str(v))
        return self

    def in_(self, c, vs):
        vs = [str(x) for x in vs]
        self.filtros.append(lambda r, c=c, vs=vs: str(r.get(c)) in vs)
        return self

    def is_(self, c, v):
        self.filtros.append(lambda r, c=c, v=v: r.get(c) is None if str(v) == "null" else True)
        return self

    def gte(self, c, v):
        self.filtros.append(lambda r, c=c, v=v: str(r.get(c) or "") >= str(v))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _rodar(self):
        linhas = self.db.tabelas.setdefault(self.tabela, [])
        self.db.chamadas.append((self.tabela, self.op))
        if self.op == "insert":
            novas = self.valores if isinstance(self.valores, list) else [self.valores]
            linhas.extend(dict(n) for n in novas)
            return types.SimpleNamespace(data=copy.deepcopy(novas))
        alvo = [r for r in linhas if all(f(r) for f in self.filtros)]
        if self.op == "update":
            for r in alvo:
                r.update(self.valores)
            return types.SimpleNamespace(data=copy.deepcopy(alvo))
        if self._limit is not None:
            alvo = alvo[: self._limit]
        return types.SimpleNamespace(data=copy.deepcopy(alvo))

    def execute(self):
        if self.assincrono:
            async def _a():
                return self._rodar()
            return _a()
        return self._rodar()


class Banco:
    def __init__(self, assincrono=False, **tabelas):
        self.tabelas = {k: [dict(x) for x in v] for k, v in tabelas.items()}
        self.chamadas = []
        self.assincrono = assincrono

    def table(self, nome):
        return _Q(self, nome, self.assincrono)

    @property
    def client(self):
        return self


def _linha(**extra):
    """A linha do usuário EXATAMENTE como o pareamento a grava (purpose, provider, agent_id None, is_active True)."""
    base = {"id": "lu-1", "company_id": CID_A, "owner_user_id": UID_1, "provider": "evolution-go",
            "purpose": "linha_do_usuario", "instance_id": "ab-lu-a1-u1", "identifier": "ab-lu-a1-u1",
            "is_active": True, "channel_status": "connected", "paired_phone_e164": NUM_LINHA, "agent_id": None,
            "token": "tok-linha", "base_url": "http://go.falso", "last_seen_at": "2026-10-15T10:00:00+00:00",
            "linha_jid": "5511900000101@s.whatsapp.net", "linha_lid": None,
            "permite_envio_de_auxiliar": True}     # 🔴 nem a autorização de auxiliar abre a linha
    base.update(extra)
    return base


def _observer(**extra):
    base = {"id": "obs-1", "company_id": CID_A, "provider": "evolution-go", "purpose": "observer",
            "instance_id": "ab-obs-a1", "identifier": "ab-obs-a1", "is_active": True, "channel_status": "connected",
            "paired_phone_e164": NUM_OBS, "agent_id": None, "token": "tok-obs", "base_url": "http://go.falso",
            "last_seen_at": "2026-10-15T10:00:00+00:00", "permite_envio_de_auxiliar": False}
    base.update(extra)
    return base


def _atendimento(**extra):
    """O CONTROLE: um canal legítimo de saída da corretora."""
    base = {"id": "att-1", "company_id": CID_A, "provider": "evolution-go", "purpose": "attendance",
            "instance_id": "ab-att-a1", "identifier": "ab-att-a1", "is_active": True, "channel_status": "connected",
            "paired_phone_e164": "+5511900000501", "agent_id": None, "token": "tok-att",
            "base_url": "http://go.falso"}
    base.update(extra)
    return base


@pytest.fixture(autouse=True)
def _segredos_em_claro(monkeypatch):
    from app.services.whatsapp import integration_secrets as SEG

    monkeypatch.setattr(SEG, "decrypt_integration_secret", lambda v, **_k: v)
    monkeypatch.setattr(SEG, "prepare_integration_for_runtime", lambda x: dict(x) if x else x)
    import app.services.integration_service as ISM

    monkeypatch.setattr(ISM, "prepare_integration_for_runtime", lambda x: dict(x) if x else x)


def test_os_literais_da_linha_sao_o_purpose_canonico():
    """`integration_service` e `channel_state` são carregados SOZINHOS por guardas antigos, e por isso escrevem o
    purpose da linha como literal. Este guarda prova que o literal é o canônico (e que consegue divergir: CONTROLE)."""
    from app.services.integration_service import IntegrationService as IS
    from app.services.whatsapp import channel_state as CS
    from app.services.whatsapp.channel_identity import PURPOSE_DA_LINHA

    assert PURPOSE_DA_LINHA in IS.PROPOSITOS_QUE_NUNCA_ENVIAM
    assert IS.PROPOSITOS_QUE_NENHUMA_AUTORIZACAO_LIBERA == frozenset({PURPOSE_DA_LINHA})
    assert CS.PURPOSE_DA_LINHA_DO_USUARIO == PURPOSE_DA_LINHA
    assert "observer" not in IS.PROPOSITOS_QUE_NENHUMA_AUTORIZACAO_LIBERA     # CONTROLE


# =====================================================================================================================
# B1 — nenhum caminho de SAÍDA escolhe a linha
# =====================================================================================================================
def test_b1_pode_enviar_recusa_a_linha_nos_dois_regimes_mesmo_autorizada():
    from app.services.integration_service import IntegrationService as IS

    assert IS.pode_enviar(_linha()) is False
    assert IS.pode_enviar(_linha(), para=IS.ENVIO_DE_AUXILIAR) is False
    # CONTROLE: o guarda consegue dizer SIM — atendimento sempre; observador SÓ autorizado e SÓ para auxiliar
    assert IS.pode_enviar(_atendimento()) is True
    assert IS.pode_enviar(_observer(permite_envio_de_auxiliar=True), para=IS.ENVIO_DE_AUXILIAR) is True
    assert IS.pode_enviar(_observer(permite_envio_de_auxiliar=True)) is False


def test_b1_a_cobranca_nao_sai_pela_linha():
    from app.services import billing_collection as BC

    assert BC._find_whatsapp_integration(Banco(integrations=[_linha(), _observer()]), CID_A) is None
    # CONTROLE: com um canal legítimo, a cobrança o escolhe
    ok = BC._find_whatsapp_integration(Banco(integrations=[_linha(), _observer(), _atendimento()]), CID_A)
    assert ok is not None and ok["purpose"] == "attendance"


def test_b1_a_rotina_nao_entrega_pela_linha(monkeypatch):
    import app.core.database as DBM
    from app.services import routine_engine as RE
    from app.services import whatsapp_service as WS

    enviados = []

    class _Servico:
        def send_message(self, numero, texto, integracao, **_k):
            enviados.append(integracao.get("purpose"))
            return True

    monkeypatch.setattr(WS, "get_whatsapp_service", lambda: _Servico())
    rotina = {"id": "r1", "company_id": CID_A, "delivery": {"channel": "whatsapp", "number": "5511900000901"}}

    monkeypatch.setattr(DBM, "get_supabase_client", lambda: Banco(integrations=[_linha(), _observer()]))
    ok, detalhe = asyncio.run(RE._deliver(rotina, "relatório"))
    assert ok is False and "sem canal WhatsApp que possa ENVIAR" in detalhe and enviados == []
    # CONTROLE
    monkeypatch.setattr(DBM, "get_supabase_client",
                        lambda: Banco(integrations=[_linha(), _observer(), _atendimento()]))
    ok, _ = asyncio.run(RE._deliver(rotina, "relatório"))
    assert ok is True and enviados == ["attendance"]


def test_b1_o_canal_de_plataforma_e_a_busca_sem_agente_nao_escolhem_a_linha():
    from app.services import integration_service as ISM

    servico = ISM.IntegrationService.__new__(ISM.IntegrationService)
    servico.supabase = Banco(integrations=[_linha(), _observer()])   # a linha PRIMEIRO na ordem do banco
    assert servico.get_platform_whatsapp_integration(CID_A) is None   # Vigia · follow-up · relatório · sugestão
    escolhida = servico.get_whatsapp_integration(CID_A)                # acompanhamento · acionamento · portal
    assert (escolhida or {}).get("purpose") != "linha_do_usuario"
    servico.supabase = Banco(integrations=[_linha()])
    assert servico.get_whatsapp_integration(CID_A) is None
    # CONTROLE
    servico.supabase = Banco(integrations=[_linha(), _observer(), _atendimento()])
    assert servico.get_platform_whatsapp_integration(CID_A)["purpose"] == "attendance"
    servico.supabase = Banco(integrations=[_linha(), _atendimento()])
    assert servico.get_whatsapp_integration(CID_A)["purpose"] == "attendance"


def test_b1_o_aviso_de_queda_nao_sai_pela_linha(monkeypatch):
    import app.core.database as DBM
    from app.services.whatsapp import alerts as AL

    monkeypatch.setattr(AL, "_platform_alert_integration", lambda: None)
    caiu = _atendimento(id="att-caiu", instance_id="ab-att-caiu", channel_status="disconnected")
    monkeypatch.setattr(DBM, "get_supabase_client", lambda: Banco(integrations=[caiu, _linha(), _observer()]))
    assert AL._sender_integration(caiu) is None
    # CONTROLE
    monkeypatch.setattr(DBM, "get_supabase_client",
                        lambda: Banco(integrations=[caiu, _linha(), _atendimento()]))
    assert AL._sender_integration(caiu)["purpose"] == "attendance"


def test_b1_o_qcm_nao_responde_pela_linha_de_um_membro_da_plataforma():
    from app.services.canal import envio as CE

    qcm = _observer(id="qcm-1", company_id=CID_PLAT, channel_status="disconnected")
    lu = _linha(company_id=CID_PLAT)
    escolhida = CE._linha_do_canal(Banco(integrations=[lu, qcm]), CID_PLAT)
    assert escolhida is not None and escolhida["id"] == "qcm-1"       # o QCM caído, nunca a linha conectada
    assert CE._linha_do_canal(Banco(integrations=[lu]), CID_PLAT) is None
    # CONTROLE: sem a linha, o mesmo seletor devolve o QCM
    assert CE._linha_do_canal(Banco(integrations=[qcm]), CID_PLAT)["id"] == "qcm-1"


def _prova(monkeypatch, integracoes, para):
    from fastapi import HTTPException

    from app.api import whatsapp_integrations as WI

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-de-teste")
    monkeypatch.setattr(WI, "prepare_integration_for_runtime", lambda x: dict(x) if x else x)
    carga = WI.ProvaDeFormularioPayload(company_id=CID_A, para=para)
    try:
        asyncio.run(WI.prova_de_formulario(carga, "chave-de-teste", Banco(assincrono=True, integrations=integracoes)))
    except HTTPException as exc:
        return exc.status_code, str(exc.detail)
    return 200, ""


def test_b1_a_prova_de_formulario_nao_usa_a_linha_nem_como_origem_nem_como_destino(monkeypatch):
    destino_zapi = {"id": "z-1", "company_id": CID_A, "provider": "z-api", "purpose": "attendance",
                    "is_active": True, "paired_phone_e164": "+5511900000601"}
    # ORIGEM: a única evolution-go ativa é a linha (sem base_url, para nada sair) → nenhuma origem elegível
    status, detalhe = _prova(monkeypatch, [_linha(base_url=""), destino_zapi], "5511900000601")
    assert status == 404 and "Nenhuma integracao" in detalhe
    # DESTINO: o número pessoal do corretor não é "aparelho desta corretora"
    status, detalhe = _prova(monkeypatch, [_atendimento(base_url=""), _linha()], NUM_LINHA)
    assert status == 400 and "destino recusado" in detalhe
    # CONTROLE: o mesmo caminho com um canal legítimo como origem chega à integração (422 = achou, sem base_url)
    status, _ = _prova(monkeypatch, [_linha(base_url=""), _atendimento(base_url=""), destino_zapi], "5511900000601")
    assert status == 422


# =====================================================================================================================
# B2 — o heartbeat e o reconector tratam a linha pelo purpose
# =====================================================================================================================
def _cliente_http(corpos):
    class _Cliente:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            corpos.append({"url": url, "json": json})
            return types.SimpleNamespace(status_code=200)

    return _Cliente


def test_b2_o_reconector_religa_a_linha_sem_history_sync(monkeypatch):
    import httpx

    from app.services.whatsapp import channel_security as SEC
    from app.services.whatsapp import channel_state as CS
    from app.services.whatsapp.pairing_orchestrator import EVENTOS_DA_LINHA_DO_USUARIO

    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://api.falso")

    async def _gravou(*_a, **_k):
        return True

    monkeypatch.setattr(CS, "_gravar_credencial_de_webhook", _gravou)
    corpos = []
    monkeypatch.setattr(httpx, "AsyncClient", _cliente_http(corpos))
    CS._ULTIMA_RECONEXAO.clear()
    agora = datetime.now(timezone.utc)
    assert asyncio.run(CS._reconectar_evolution_go(_linha(), agora)) == "reconectado"
    corpo = corpos[0]["json"]
    assert corpo["subscribe"] == list(EVENTOS_DA_LINHA_DO_USUARIO)
    assert "HISTORY_SYNC" not in corpo["subscribe"]
    assert str(corpo.get("webhookUrl") or "").startswith("https://api.falso/")
    # CONTROLE: o observador religa com o corpo de SEMPRE (byte a byte o `corpo_do_connect`, com HISTORY_SYNC)
    asyncio.run(CS._reconectar_evolution_go(_observer(), agora))
    corpo_obs = corpos[1]["json"]
    assert "HISTORY_SYNC" in corpo_obs["subscribe"]
    assert corpo_obs == SEC.corpo_do_connect(corpo_obs["webhookUrl"])


def test_b2_o_heartbeat_nao_alarma_a_queda_da_linha_e_a_registra_pela_funcao_dela(monkeypatch):
    from app.services.whatsapp import channel_state as CS

    monkeypatch.setenv("CHANNEL_HEARTBEAT_ENABLED", "1")
    alarmes, entregas, religadas = [], [], []

    async def _sonda(linha):
        return "close"                      # o provedor responde: a sessão não está de pé

    async def _religar(linha, agora):
        religadas.append(linha.get("purpose"))
        return None

    async def _alarme(linha, *_a, **_k):
        alarmes.append(linha.get("purpose"))

    async def _entrega(linha, *_a, **_k):
        entregas.append(linha.get("purpose"))

    async def _ultima(*_a, **_k):
        return {}

    monkeypatch.setattr(CS, "_ultima_entrega_por_corretora", _ultima)
    db = Banco(integrations=[_linha(), _observer()])
    resumo = asyncio.run(CS.verificar_canais(db=db, sonda=_sonda, alarme=_alarme, reconector=_religar,
                                             alarme_de_entrega=_entrega))
    assert "linha_do_usuario" not in alarmes and "linha_do_usuario" not in entregas
    assert resumo["alarmes"] == 1
    linha = next(r for r in db.tabelas["integrations"] if r["id"] == "lu-1")
    assert linha["channel_status"] == "disconnected"
    assert linha.get("linha_motivo") == "heartbeat_sem_sessao" and linha.get("linha_desconectada_em")
    assert linha["is_active"] is True                       # queda de socket não é a pessoa saindo
    # CONTROLE: o observador, na MESMA varredura, alarma como sempre (e os dois foram religados)
    assert alarmes == ["observer"]
    assert sorted(religadas) == ["linha_do_usuario", "observer"]


def test_b2_as_rotas_legadas_por_corretora_e_o_briefing_nao_operam_a_linha(monkeypatch):
    from fastapi import HTTPException

    from app.api import whatsapp_channel as WC
    from app.services.intelligence.detectors.conexoes import canais_com_problema

    def _nao_leia():
        raise AssertionError("a rota legada não pode ler a linha do usuário")

    monkeypatch.setattr(WC, "get_supabase_client", _nao_leia)
    assert asyncio.run(WC._go_company_channel(CID_A, "linha_do_usuario")) is None
    carga = types.SimpleNamespace(purpose="linha_do_usuario")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(WC._go_setup(CID_A, carga, "https://api.falso"))
    assert exc.value.status_code == 400
    caidos = canais_com_problema([_linha(channel_status="disconnected"),
                                  _observer(channel_status="disconnected")])
    # CONTROLE: o observador caído continua no briefing
    assert [c["id"] for c in caidos] == ["obs-1"]


# =====================================================================================================================
# B3 — conectar a linha não cala ninguém (e não abre laço)
# =====================================================================================================================
def _banco_de_numeros():
    return Banco(integrations=[_observer(), _linha()], companies=[{"id": CID_A, "company_kind": "client"}],
                 human_support_destinations=[], support_destinations=[])


def test_b3_o_numero_da_linha_nao_e_de_corretora_nem_do_produto():
    from app.services.atalho.entrada import numero_do_produto
    from app.services.canal.repositorio import numero_de_corretora

    db = _banco_de_numeros()
    assert numero_de_corretora(db, NUM_LINHA) is False        # o QCM conversa com a pessoa
    assert numero_do_produto(db, NUM_LINHA) is False          # o central 132-C também
    # CONTROLE: o número do observador da MESMA corretora segue sendo "de corretora" / "do produto"
    assert numero_de_corretora(db, NUM_OBS) is True
    assert numero_do_produto(db, NUM_OBS) is True


def _linha_publica():
    return {"integration_id": "lu-1", "company_id": CID_A, "owner_user_id": UID_1,
            "jid": "5511900000101@s.whatsapp.net", "lid": None, "numero_e164": NUM_LINHA, "ativa": True}


def _corpo_go(info, texto="oi"):
    return {"event": "Message", "data": {"Info": info, "Message": {"conversation": texto}}}


def test_b3_sem_laco_o_que_o_central_manda_ao_numero_da_linha_e_conversa_alheia_para_ela():
    from app.services.atalho.envio import _e_a_propria_linha
    from app.services.linha_do_usuario import entrada as ENT

    # o central (ou o QCM) responde ao corretor → a instância da linha recebe numa conversa com o central
    chegou = _corpo_go({"Chat": NUM_CENTRAL + "@s.whatsapp.net", "Sender": NUM_CENTRAL + "@s.whatsapp.net",
                        "IsFromMe": False, "ID": "IN-1"}, "Sua cotação ficou pronta")
    assert ENT.filtrar(_linha_publica(), chegou) == (None, "outra_conversa")
    # o corretor responde ao central do próprio aparelho → fromMe, mas na conversa com o central
    respondeu = _corpo_go({"Chat": NUM_CENTRAL + "@s.whatsapp.net", "Sender": "5511900000101:7@s.whatsapp.net",
                           "IsFromMe": True, "ID": "OUT-1"}, "cotar ABC1D23")
    assert ENT.filtrar(_linha_publica(), respondeu) == (None, "outra_conversa")
    # e a saída da linha nunca vai ao central (o cinto): só à própria conta
    db = Banco(integrations=[_linha()])
    assert _e_a_propria_linha(db, _linha(), NUM_CENTRAL) is False
    # CONTROLE: a conversa consigo mesmo passa, e o cinto aceita a própria conta
    consigo = _corpo_go({"Chat": "5511900000101@s.whatsapp.net", "Sender": "5511900000101:7@s.whatsapp.net",
                         "IsFromMe": True, "ID": "SELF-1"}, "cotar ABC1D23")
    normalizado, motivo = ENT.filtrar(_linha_publica(), consigo)
    assert motivo == "" and normalizado["text"] == "cotar ABC1D23"
    assert _e_a_propria_linha(db, _linha(), "5511900000101") is True


# =====================================================================================================================
# P1 — fromMe SEM Chat é descartado no portão da linha
# =====================================================================================================================
def test_p1_fromme_sem_chat_e_descartado_no_portao_e_no_webhook(monkeypatch):
    from app.services.linha_do_usuario import entrada as ENT
    from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope

    sem_chat = _corpo_go({"Sender": "5511900000101@s.whatsapp.net", "IsFromMe": True, "ID": "NC-1"},
                         "Oi Joana, segue a proposta")      # 💭 o que o corretor mandou a uma CLIENTE
    assert ENT.filtrar(_linha_publica(), sem_chat) == (None, "sem_chat")
    assert ENT.filtrar(_linha_publica(), go_event_to_v2_envelope(sem_chat), corpo=sem_chat) == (None, "sem_chat")
    # o caminho do webhook: `desviar` passa o corpo cru ao portão
    monkeypatch.setenv("LINHA_DO_USUARIO_LIGADA", "1")
    monkeypatch.setattr(ENT, "linha_confirmada", lambda *_a, **_k: _linha_publica())
    agendados = []
    bt = types.SimpleNamespace(add_task=lambda f, *a, **k: agendados.append(f.__name__))

    async def _nao_e_duplicada(*_a):
        return False

    r = asyncio.run(ENT.desviar(Banco(linha_mensagens_do_sistema=[]), _linha(), sem_chat, bt, _nao_e_duplicada))
    assert r == {"status": "ignored", "reason": "linha_sem_chat"} and "turno_da_linha" not in agendados
    # CONTROLE: o MESMO evento com o Chat da própria conta passa e agenda o turno
    com_chat = _corpo_go({"Chat": "5511900000101@s.whatsapp.net", "Sender": "5511900000101@s.whatsapp.net",
                          "IsFromMe": True, "ID": "C-1"}, "cotar ABC1D23")
    r = asyncio.run(ENT.desviar(Banco(linha_mensagens_do_sistema=[]), _linha(), com_chat, bt, _nao_e_duplicada))
    assert r == {"status": "accepted", "reason": "linha"} and agendados == ["turno_da_linha"]


# =====================================================================================================================
# A LINHA DE CONTROLE DO CONSERTO — cada conserto desfeito POR CÓPIA tem de deixar o seu grupo VERMELHO
# =====================================================================================================================
ANTES_DO_CONSERTO = "923e9e2"
MUTACOES = {
    "B1": ("test_b1_", ["app/services/integration_service.py", "app/services/canal/envio.py",
                        "app/api/whatsapp_integrations.py"]),
    "B2": ("test_b2_", ["app/services/whatsapp/channel_state.py", "app/api/whatsapp_channel.py",
                        "app/services/intelligence/detectors/conexoes.py"]),
    "B3": ("test_b3_", ["app/services/canal/repositorio.py", "app/services/atalho/entrada.py"]),
    "P1": ("test_p1_", ["app/services/linha_do_usuario/entrada.py"]),
}


def _mutar() -> int:
    falhas = 0
    for nome, (prefixo, arquivos) in MUTACOES.items():
        guardados = {a: (BACKEND / a).read_bytes() for a in arquivos}
        try:
            for a in arquivos:
                antigo = subprocess.run(["git", "show", f"{ANTES_DO_CONSERTO}:backend/{a}"], cwd=BACKEND,
                                        capture_output=True, check=True).stdout
                (BACKEND / a).write_bytes(antigo)
            r = subprocess.run([sys.executable, "-m", "pytest", __file__, "-q", "-p", "no:cacheprovider",
                                "-k", prefixo, "-W", "ignore"], cwd=BACKEND, capture_output=True, text=True)
            ultima = [x for x in r.stdout.splitlines() if x.strip()][-1:] or ["?"]
            vermelho = r.returncode != 0
            print(f"{nome}: {'VERMELHO' if vermelho else 'VERDE (o guarda NAO guarda)'} · {ultima[0]}")
            falhas += 0 if vermelho else 1
        finally:
            for a, dados in guardados.items():                      # restaura POR CÓPIA
                (BACKEND / a).write_bytes(dados)
            assert all(hashlib.sha256((BACKEND / a).read_bytes()).digest() == hashlib.sha256(d).digest()
                       for a, d in guardados.items())
    return falhas


if __name__ == "__main__" and "--mutar" in sys.argv:
    sys.exit(_mutar())

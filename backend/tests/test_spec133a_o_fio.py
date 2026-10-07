# -*- coding: utf-8 -*-
"""SPEC-133-A · F-COSTURA — O TESTE DO FIO da SPEC (G1 · G2 · G3 · G5 · G6 · G8), da borda à borda.

    POST /api/v1/webhook/evolution-go/{token}  (payload REAL do Evolution Go — fixtures/canal_evolution_go_oi.json)
      → _resolve_webhook_integration (hash do token) → o desvio do canal (antes do observer_tap)
      → _handle_evolution_like_inbound → MessageBufferService REAL → processar_buffers_prontos (o motor do buffer)
      → process_whatsapp_message_background → canal.entrada.turno (F1 REAL: anti-laço, convite, limite, estado cifrado)
      → canal.conversa.responder (F2 REAL; o modelo é um dublê que QUEBRA se for chamado — tudo aqui é regra)
      → canal.envio.enviar (F1 REAL) → whatsapp_service.send_message (DUBLÊ DE BORDA: captura os balões)
      … oi · sim · placa · CEP · … · "pular" → cotacao.disparar (F2 REAL) → MulticalculoProvider.calcular REAL
      → Work Run canal.cotacao (WorkRunService.criar → RPC) → o motor grava o quadro (dublê do portal-worker)
      → SmithWorker._processar REAL → publicar_proposta REAL (F0) → a página do canal (F3 REAL) pelo Artifact Hub
      → os balões da F0 com /r/<token> no send_message do MESMO telefone → abrir /r/<token> (marca QCM, "Quero fechar"
        para o número do CANAL) → o convidado manda o texto do botão → a passagem (registrada no run + caixa do operador).

Dublê SÓ na borda: banco (o `BancoU1` da 129-B/130-A — PostgREST em memória com as travas), Redis, relógio, o
`send_message`, o modelo (proibido) e o portal-worker (grava o quadro do canário). A rede fica FECHADA.

⛔ Dados fictícios: DDD 00 (não existe), CPF sintético com DV válido, nomes inventados (CLAUDE.md §13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec133a_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import sys
import types
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from cryptography.fernet import Fernet  # noqa: E402

# ⚠️ importados ANTES de qualquer relógio do mundo ser instalado: um módulo importado com o relógio de um teste
# instalado guarda a classe `datetime` DAQUELE relógio (parado) para sempre — e o teste seguinte não anda no tempo
import app.api.webhook  # noqa: E402,F401
import app.services.canal.conversa  # noqa: E402,F401
import app.services.canal.cotacao  # noqa: E402,F401
import app.services.canal.entrada  # noqa: E402,F401
import app.services.canal.workflows  # noqa: E402,F401
import app.services.control_plane.inbox  # noqa: E402,F401
import app.services.multicalculo.proposta  # noqa: E402,F401
import app.workers.smith_worker  # noqa: E402,F401

from dubles import mundo_da_proposta as M  # noqa: E402
from test_spec130a_o_fio import CHROME, texto_visivel  # noqa: E402
from test_spec133a_a_conversa import (CHAVE_HMAC, CPF_FICTICIO, acordar, motor_grava_o_quadro,  # noqa: E402
                                      rodar_o_run)
from test_spec133a_a_entrada import (FIXTURE, BufferDoTeste, EnvioFalso, RedisFalso, _sem_rede,  # noqa: E402
                                     _sem_rede_ex)

BASE = "https://app.exemplo.test"
TOKEN_CANAL = "tok-canal-fio-" + "x" * 40
TOKEN_CORRETORA = "tok-corretora-fio-" + "y" * 40
CONVIDADO = "5500999990001"
ESTRANHO = "5500999990002"
LINHA_DA_CORRETORA = "5500988887777"       # convidado por engano E pareado numa corretora (sem o 9): o anti-laço vence
LIMITADO = "5500999990003"                 # convidado com limite_dia = 1
#: as respostas de uma pessoa, uma por pergunta (`conversa.ROTEIRO`) — a última é "pular" (o prêmio é opcional)
FALAS = ["ABC1D23", "01001-000", "não", "uns 800 km", "não", CPF_FICTICIO, "Pessoa Sintetica Teste", "01/02/1980",
         "homem", "20", "pular"]
RE_LINK = re.compile(r"/r/([A-Za-z0-9_\-]+)")


# =====================================================================================================================
# o MUNDO — o banco da 129-B/130-A + o webhook da F1, tudo real entre as bordas
# =====================================================================================================================
def _hash(tok):
    from app.services.whatsapp.channel_security import webhook_token_hash

    return webhook_token_hash(tok)


class ServicoDeIntegracao:
    """O resolvedor do token (borda do serviço de integrações) sobre o MESMO banco do mundo."""

    def __init__(self, banco):
        self.banco = banco

    def get_integration_by_webhook_token(self, tok):
        h = _hash(tok)
        return next((dict(x) for x in self.banco.linhas("integrations") if x.get("webhook_token_hash") == h), None)

    def get_integration_by_id(self, ident):
        return next((dict(x) for x in self.banco.linhas("integrations")
                     if str(x.get("id")) == str(ident) and x.get("is_active")), None)

    def get_integration_by_phone(self, _p):
        return None


class ModeloProibido:
    def __init__(self):
        self.chamadas = 0

    async def __call__(self, mensagens, company_id):
        self.chamadas += 1
        raise AssertionError("o modelo foi chamado numa resposta que a regra entende")


@pytest.fixture
def fio(monkeypatch):
    import socket

    import app.core.database as _database
    import app.core.redis as _redis

    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", CHAVE_HMAC)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    m = M.montar_mundo(monkeypatch, solicitante="canal")
    m.relogio.instalar()
    monkeypatch.setattr(socket.socket, "connect", _sem_rede)
    monkeypatch.setattr(socket.socket, "connect_ex", _sem_rede_ex)

    # a integração do canal (a que o mundo semeou pareada) ganha o token do webhook; a linha de uma CORRETORA (a
    # vencedora), observer, com o número que aparece de novo como convidado (o anti-laço)
    (canal_int,) = [i for i in m.banco.linhas("integrations") if i["company_id"] == m.canal]
    canal_int.update({"id": "int-canal", "identifier": "ab-obs-canal-1", "base_url": "http://evolution.invalid",
                      "webhook_token_hash": _hash(TOKEN_CANAL)})
    m.banco.semear("integrations", {"id": "int-alfa", "company_id": m.alfa, "provider": "evolution-go",
                                    "purpose": "observer", "is_active": True, "channel_status": "connected",
                                    "identifier": "ab-obs-alfa-1", "base_url": "http://evolution.invalid",
                                    "webhook_token_hash": _hash(TOKEN_CORRETORA), "paired_phone_e164": "+550088887777"})
    for tel, lim in ((CONVIDADO, None), (LINHA_DA_CORRETORA, None), (LIMITADO, 1)):
        m.banco.semear("canal_convidados", {"company_id": m.canal, "telefone": tel, "apelido": "Teste", "ativo": True,
                                            "limite_dia": lim})

    db = m.db
    sup = types.SimpleNamespace(client=db)
    redis = RedisFalso()
    monkeypatch.setattr(_database, "get_supabase_client", lambda: sup)

    async def _redis_async():
        return redis

    monkeypatch.setattr(_redis, "get_async_redis_client", _redis_async)
    import app.api.webhook as w
    from app.services.message_buffer_service import MessageBufferService

    servico_buffer = MessageBufferService(redis)

    async def _buffer():
        return servico_buffer

    async def _nada(*_a, **_k):
        return None

    monkeypatch.setattr(w, "supabase", sup)
    monkeypatch.setattr(w, "integration_service", ServicoDeIntegracao(m.banco))
    monkeypatch.setattr(w, "get_async_redis_client", _redis_async)
    monkeypatch.setattr(w, "get_message_buffer_service", _buffer)
    monkeypatch.setattr(w, "_registrar_retorno_de_cobranca", _nada)

    import app.services.atlas.observer_intake as _obs

    taps = []

    async def _tap(integration, body):              # o observer CONSOME (a não-regressão só pergunta quem chegou nele)
        taps.append(str((integration or {}).get("company_id")))
        return {"status": "observed"}

    monkeypatch.setattr(_obs, "observer_tap", _tap)

    envio = EnvioFalso()
    import app.services.whatsapp_service as _ws

    monkeypatch.setattr(_ws, "get_whatsapp_service", lambda: envio)
    monkeypatch.setattr(w, "whatsapp_service", envio)

    import app.services.canal.envio as _envio_do_canal
    import app.services.canal.repositorio as repo
    from app.services.canal import conversa, cotacao

    monkeypatch.setattr(_envio_do_canal, "PAUSA_ENTRE_BALOES_S", 0)
    repo._CACHE_DO_TIPO.clear()
    modelo = ModeloProibido()
    monkeypatch.setattr(conversa, "_chamar_o_papel", modelo)

    from app.services.multicalculo import porta as P

    chamadas_da_porta = []
    original = P.MulticalculoProvider.calcular

    async def espiao(self, **kw):
        chamadas_da_porta.append(dict(kw))
        return await original(self, **kw)

    monkeypatch.setattr(P.MulticalculoProvider, "calcular", espiao)

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.rate_limit import limiter

    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(w.router)
    cliente = TestClient(app)
    seq = {"n": 0}

    def postar(texto="oi", *, tel=CONVIDADO, token=TOKEN_CANAL, from_me=False, grupo=False):
        with open(FIXTURE, encoding="utf-8") as f:
            corpo = copy.deepcopy(json.load(f)["evento"])
        seq["n"] += 1
        jid = "120363000000000001@g.us" if grupo else f"{tel}@s.whatsapp.net"
        corpo["data"]["Info"].update({"Chat": jid, "Sender": f"{tel}@s.whatsapp.net", "IsFromMe": from_me,
                                      "IsGroup": grupo, "ID": f"3EB0C0A0{seq['n']:014d}"})
        corpo["data"]["Message"] = {"conversation": texto}
        r = cliente.post(f"/api/v1/webhook/evolution-go/{token}", json=corpo)
        assert r.status_code == 200, r.text
        return r.json()

    def drenar():
        from app.tasks.buffer_processor import processar_buffers_prontos

        chaves = [k for k in list(redis.dados) if str(k).startswith("whatsapp_buffer:")]
        return asyncio.run(processar_buffers_prontos(chaves, BufferDoTeste(servico_buffer),
                                                     w.process_whatsapp_message_background, paralelismo=2))

    def falar(texto, tel=CONVIDADO):
        antes = len(envio.enviados)
        postar(texto, tel=tel)
        drenar()
        return [e["texto"] for e in envio.enviados[antes:]]

    yield types.SimpleNamespace(m=m, db=db, w=w, redis=redis, envio=envio, taps=taps, repo=repo, conversa=conversa,
                                cotacao=cotacao, modelo=modelo, porta=chamadas_da_porta, postar=postar, drenar=drenar,
                                falar=falar)
    m.relogio.desinstalar()


# =====================================================================================================================
# ajudantes — os critérios são funções que devolvem DEFEITOS: o teste do fio exige [] e cada mutação exige != []
# =====================================================================================================================
def ate_o_resultado(f, tel=CONVIDADO):
    """O convidado do "oi" até os balões com o link (o run roda uma volta: acompanhar → entregar → dorme)."""
    for fala in ["oi", "sim", *FALAS]:
        f.falar(fala, tel=tel)
    est = f.repo.carregar_estado(f.db, f.m.canal, tel)
    assert est.get("etapa") == "calculando" and est.get("run_id"), f"a cotação não começou: {est.get('etapa')}"
    motor_grava_o_quadro(f.m.banco, pedido_id=est["pedido_id"], dados=f.m.dados)
    antes = len(f.envio.enviados)
    asyncio.run(rodar_o_run(f.db, est["run_id"], f.m.canal))
    baloes = [e for e in f.envio.enviados[antes:]]
    return est, baloes


def servir(f, token):
    from app.services.artifacts.service import ArtifactService

    s = ArtifactService(f.m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert s, "o link não abriu"
    return s


def defeitos_da_pagina(f, token) -> list:
    """O que a página do canal SERVIDA precisa ter: a marca QCM, a vencedora dentro, o mesmo script (hash da CSP) e o
    "Quero fechar" de volta para a CONVERSA do canal (nunca o número da corretora)."""
    from app.services.artifacts import proposta_html as PH
    from app.services.artifacts.service import ArtifactService

    s = servir(f, token)
    doc, txt, falhas = s["html"], texto_visivel(s["html"]), []
    if 'class="qcm"' not in doc or "Comparador independente" not in txt:
        falhas.append("sem a marca do canal (QCM) no topo")
    if "Quem Cobra Menos" not in txt:
        falhas.append("sem o nome do canal")
    if M.MARCA_ALFA not in txt:
        falhas.append("sem a corretora vencedora dentro")
    if s.get("csp_script_hashes") != [PH.HASH_DO_SCRIPT]:
        falhas.append("o hash do script mudou")
    if "?fechar=" not in re.sub(r"<script\b.*?</script>", "", doc, flags=re.S):
        falhas.append("sem o botão Quero fechar")
    destino = ArtifactService(f.m.banco.visao("rota-publica")).fechar_compartilhado(token, "recomendada") or ""
    if not destino.startswith(f"https://wa.me/{M.WHATS_DO_CANAL}?text="):
        falhas.append(f"o Quero fechar não volta à conversa do canal: {destino[:40]}")
    if M.WHATS_ALFA in destino or M.WHATS_ALFA in doc:
        falhas.append("o número da corretora é destino na página do canal")
    return falhas


def texto_do_botao(f, token) -> str:
    from app.services.artifacts.service import ArtifactService

    destino = ArtifactService(f.m.banco.visao("rota-publica")).fechar_compartilhado(token, "recomendada")
    return unquote(parse_qs(urlparse(destino).query)["text"][0])


def enviados_para(f, tel):
    return [e for e in f.envio.enviados if e["para"] == tel]


# =====================================================================================================================
# 🔴 G1 — O TESTE DO FIO
# =====================================================================================================================
def test_o_fio_do_oi_ao_link_e_a_passagem(fio):
    f, m = fio, fio.m
    # ① o "oi" NÃO morre no observer e volta com a apresentação + o consentimento (nenhum dado pessoal antes do sim)
    assert f.postar("oi")["status"] == "buffered" and f.taps == []
    f.drenar()
    oi = [e["texto"] for e in f.envio.enviados]
    assert "ninguém é obrigado a fechar" in "\n".join(oi) and "placa" not in "\n".join(oi).lower()
    assert not m.banco.linhas("canal_consentimentos")
    # ② G4: o sim é registrado ANTES da 1ª pergunta
    assert "placa" in "\n".join(f.falar("sim")).lower()
    (consent,) = m.banco.linhas("canal_consentimentos")
    assert consent["aceito"] is True and consent["telefone"] == CONVIDADO and consent["company_id"] == m.canal
    # ③ as perguntas, uma por vez, pelo webhook → o perfil → a porta REAL (G5)
    for fala in FALAS:
        assert f.falar(fala), f"sem resposta para {fala!r}"
    assert f.modelo.chamadas == 0, "o modelo foi chamado numa resposta que a regra entende"
    (kw,) = f.porta
    from app.services.multicalculo.porta import OPCOES_DO_CANAL

    assert kw["origem"] == "canal" and kw["company_id"] == m.canal and tuple(kw["opcoes"]) == OPCOES_DO_CANAL
    assert sorted(kw["corretoras"]) == sorted([m.alfa, m.beta])
    est = f.repo.carregar_estado(f.db, m.canal, CONVIDADO)
    assert est["etapa"] == "calculando" and est["run_id"] and "respostas" not in est, "o CPF não fica no estado"
    assert m.banco.run(est["run_id"])["workflow_key"] == "canal.cotacao"
    # ④ o run: o motor grava o quadro → o worker REAL publica e manda a mensagem da F0 com o link (G6)
    motor_grava_o_quadro(m.banco, pedido_id=est["pedido_id"], dados=m.dados)
    antes = len(f.envio.enviados)
    asyncio.run(rodar_o_run(f.db, est["run_id"], m.canal))
    resultado = f.envio.enviados[antes:]
    assert resultado and {e["para"] for e in resultado} == {CONVIDADO}, "o resultado vai para o MESMO telefone"
    assert {e["empresa"] for e in resultado} == {m.canal}, "pela integração do CANAL"
    texto = "\n".join(e["texto"] for e in resultado)
    (token,) = set(RE_LINK.findall(texto))
    assert f"{BASE}/r/{token}" in texto and "Cotações" in texto
    # ⑤ a página servida: a marca QCM, a vencedora dentro, o hash, o "Quero fechar" para a conversa do canal
    assert defeitos_da_pagina(f, token) == []
    # item 4: o resultado (do run) CONTA no teto do dia — o contador = tudo o que saiu para este telefone
    conv = next(c for c in m.banco.linhas("canal_conversas") if c["telefone"] == CONVIDADO)
    assert conv["enviadas_no_dia"] == len(enviados_para(f, CONVIDADO))
    assert m.banco.run(est["run_id"]).get("wake_at"), "o run dorme até o 1º lembrete"
    # ⑥ o convidado toca o botão: o texto do botão volta à conversa → a passagem
    botao = texto_do_botao(f, token)
    assert "Quero fechar a opção" in botao and f"Ref. {est['pedido_id'][:8]}" in botao
    resposta = "\n".join(f.falar(botao))
    assert f"wa.me/{M.WHATS_ALFA}" in resposta and M.MARCA_ALFA in resposta     # o grupo não entrega hoje → o WhatsApp dela
    assert f.repo.carregar_estado(f.db, m.canal, CONVIDADO)["etapa"] == "passado"
    eventos = [e for e in m.banco.linhas("work_events") if e.get("event_type") == "canal.quer_fechar"]
    assert len(eventos) == 1 and eventos[0]["company_id"] == m.canal and eventos[0]["severity"] == "warning"
    assert CONVIDADO not in json.dumps(eventos[0], default=str), "o telefone inteiro não vai para o evento"
    assert eventos[0]["payload_redacted"]["anfitria_company_id"] == m.alfa
    from app.services.control_plane.inbox import CaixaDeEntrada

    (cartao,) = CaixaDeEntrada(f.db)._canal_quer_fechar()
    assert cartao.titulo == "Cliente do canal quer fechar" and cartao.company_id == m.canal
    # ⑦ G8: depois da resposta, o relógio passa do 1º e do 2º lembrete — nenhum sai
    antes = len(f.envio.enviados)
    for _ in range(3):
        if acordar(m.banco, f.db, est["run_id"]):
            asyncio.run(rodar_o_run(f.db, est["run_id"], m.canal))
    assert f.envio.enviados[antes:] == []
    assert f.modelo.chamadas == 0


def test_sem_resposta_saem_dois_lembretes_e_contam_no_teto(fio):
    f, m = fio, fio.m
    est, _ = ate_o_resultado(f)
    lembretes, contagens = [], []
    for _ in range(6):
        if not acordar(m.banco, f.db, est["run_id"]):
            continue
        dia, antes_n = f.repo.hoje(), f.repo.enviadas_hoje(f.db, m.canal, CONVIDADO)
        antes = len(f.envio.enviados)
        asyncio.run(rodar_o_run(f.db, est["run_id"], m.canal))
        lembretes += f.envio.enviados[antes:]
        # o contador é do DIA (Brasília): o 2º lembrete cai no dia seguinte e começa do zero
        mesmo_dia = f.repo.hoje() == dia
        contagens.append((f.repo.enviadas_hoje(f.db, m.canal, CONVIDADO), (antes_n if mesmo_dia else 0) + 1))
    assert len(lembretes) == 2 and {e["para"] for e in lembretes} == {CONVIDADO}
    assert len(contagens) == 2 and all(real == esperado for real, esperado in contagens), \
        f"os lembretes contam no teto do dia: {contagens}"


def test_o_lembrete_cala_no_teto_do_dia(fio):
    f, m = fio, fio.m
    est, _ = ate_o_resultado(f)
    teto = f.repo.teto_de_mensagens(None)
    f.repo._gravar_contadores(f.db, m.canal, CONVIDADO, {"enviadas_dia": f.repo.hoje(), "enviadas_no_dia": teto})
    antes = len(f.envio.enviados)
    for _ in range(4):
        if acordar(m.banco, f.db, est["run_id"]):
            asyncio.run(rodar_o_run(f.db, est["run_id"], m.canal))
    assert f.envio.enviados[antes:] == []


def test_nao_e_depois_o_botao_ainda_passa_mesmo_no_limite_do_dia(fio):
    """O limitado (1 cotação/dia) disse "não" e depois tocou "Quero fechar": a passagem, nunca o aviso do limite nem
    uma conversa nova (a regra é UMA — `conversa.abre_conversa_nova`, usada pela entrada)."""
    f, m = fio, fio.m
    est, baloes = ate_o_resultado(f, tel=LIMITADO)
    (token,) = set(RE_LINK.findall("\n".join(e["texto"] for e in baloes)))
    assert "Obrigado" in "\n".join(f.falar("não", tel=LIMITADO))
    assert f.repo.carregar_estado(f.db, m.canal, LIMITADO)["etapa"] == "encerrado"
    resposta = "\n".join(f.falar(texto_do_botao(f, token), tel=LIMITADO))
    assert "Por hoje" not in resposta and "Oi! Aqui é" not in resposta and "wa.me/" in resposta
    assert f.repo.carregar_estado(f.db, m.canal, LIMITADO)["etapa"] == "passado"
    # e um "oi" depois de tudo, no limite, recebe o aviso (o portão do limite continua valendo)
    f.repo.salvar_estado(f.db, m.canal, LIMITADO, {"etapa": "encerrado"})
    assert f.falar("oi", tel=LIMITADO)[0].startswith("Por hoje")


def test_a_foto_no_meio_guarda_so_a_referencia_e_segue(fio):
    """Item 7: as chaves REAIS que a F1 entrega (`{"tipo", **item["midia"]}` — foto `{"imageUrl": <URL assinada>}`) →
    a F2 guarda só `<bucket>/<caminho>` (sem o token); um documento (o texto é o CONTEÚDO do PDF) não vira resposta."""
    f, m = fio, fio.m
    for fala in ("oi", "sim"):
        f.falar(fala)
    url = "https://x.supabase.co/storage/v1/object/sign/chat-media/c1/2026-10-07/abc.jpg?token=SEGREDO"
    from app.services.canal import entrada

    integ = next(i for i in m.banco.linhas("integrations") if i["company_id"] == m.canal)
    asyncio.run(entrada.turno(f.db, integ, CONVIDADO, [{"tipo": "image", "legenda": "", "midia": {"imageUrl": url}}]))
    doc = {"tipo": "document", "legenda": f"apolice.pdf\n\n[DOCUMENTO]\nCPF {CPF_FICTICIO} placa ABC1D23",
           "midia": {"fileName": "apolice.pdf"}}
    asyncio.run(entrada.turno(f.db, integ, CONVIDADO, [doc]))
    est = f.repo.carregar_estado(f.db, m.canal, CONVIDADO)
    assert est["etapa"] == "placa", "o conteúdo do documento NÃO respondeu a pergunta da placa"
    assert est["midias"] == [{"tipo": "image", "ref": "chat-media/c1/2026-10-07/abc.jpg"},
                             {"tipo": "document", "ref": "arquivo:apolice.pdf"}]
    assert "SEGREDO" not in json.dumps(est) and f.modelo.chamadas == 0


# =====================================================================================================================
# 🔴 G2 — os controles: ZERO send_message pelo webhook real · G3 — o observer da corretora intacto
# =====================================================================================================================
@pytest.mark.parametrize("caso", ["nao_convidado", "numero_de_corretora", "from_me", "grupo"])
def test_os_controles_dao_zero_envio(fio, caso):
    f = fio
    kw = {"nao_convidado": {"tel": ESTRANHO}, "numero_de_corretora": {"tel": LINHA_DA_CORRETORA},
          "from_me": {"from_me": True}, "grupo": {"grupo": True}}[caso]
    f.postar("oi", **kw)
    f.drenar()
    assert f.envio.enviados == [], caso
    assert not f.m.banco.linhas("canal_consentimentos") and f.taps == []


def test_acima_do_limite_um_aviso_so(fio):
    f, m = fio, fio.m
    f.repo._gravar_contadores(f.db, m.canal, LIMITADO, {"cotacoes_dia": f.repo.hoje(), "cotacoes_no_dia": 1})
    f.falar("oi", tel=LIMITADO)
    f.falar("oi de novo", tel=LIMITADO)
    (aviso,) = f.envio.enviados
    assert aviso["para"] == LIMITADO and aviso["texto"].startswith("Por hoje")


def test_nao_regressao_o_observer_da_corretora_continua_consumindo(fio):
    f = fio
    assert f.postar("oi", tel=ESTRANHO, token=TOKEN_CORRETORA) == {"status": "observed"}
    assert f.taps == [f.m.alfa] and f.envio.enviados == []
    assert not [k for k in f.redis.dados if str(k).startswith("whatsapp_buffer:")]


# =====================================================================================================================
# 🔴 AS MUTAÇÕES — cada uma prova que um critério do fio CONSEGUE ficar vermelho (CLAUDE.md §9.3 corolário)
# =====================================================================================================================
def test_mutacao_tirar_o_desvio_o_oi_morre_no_observer(fio, monkeypatch):
    f = fio
    monkeypatch.setattr(f.repo, "eh_canal", lambda *_a, **_k: False)
    assert f.postar("oi")["status"] == "observed"
    f.drenar()
    assert f.taps == [f.m.canal] and f.envio.enviados == []          # o ① do fio ficaria vermelho


def test_mutacao_tirar_o_convite_o_estranho_recebe(fio, monkeypatch):
    f = fio
    monkeypatch.setattr(f.repo, "convidado", lambda *_a, **_k: {"id": "qualquer"})
    f.postar("oi", tel=ESTRANHO)
    f.drenar()
    assert enviados_para(f, ESTRANHO), "o controle 'não convidado' ficaria vermelho"


def test_mutacao_o_renderizador_da_carteira_no_canal(fio, monkeypatch):
    from app.services.artifacts import proposta_canal_html as PC
    from app.services.artifacts import proposta_html as PH

    monkeypatch.setattr(PC, "render_proposta_do_canal", PH.render_proposta)
    _, baloes = ate_o_resultado(fio)
    (token,) = set(RE_LINK.findall("\n".join(e["texto"] for e in baloes)))
    falhas = defeitos_da_pagina(fio, token)
    assert "sem a marca do canal (QCM) no topo" in falhas


def test_mutacao_o_quero_fechar_para_o_numero_da_corretora(fio, monkeypatch):
    from app.services.multicalculo import proposta as P

    monkeypatch.setattr(P, "whatsapp_do_canal", lambda *_a, **_k: M.WHATS_ALFA)
    _, baloes = ate_o_resultado(fio)
    (token,) = set(RE_LINK.findall("\n".join(e["texto"] for e in baloes)))
    falhas = defeitos_da_pagina(fio, token)
    assert any("não volta à conversa do canal" in x for x in falhas)
    assert "o número da corretora é destino na página do canal" in falhas


def _workflow_mutado(monkeypatch, guarda: str):
    """Recompila `canal/workflows.py` com a guarda do lembrete trocada por `if False:` e registra o handler mutado
    (o registro original volta no fim do teste). O arquivo NÃO é tocado."""
    from app.services.canal import workflows as WF
    from app.services.work import workflows as REG

    fonte = Path(WF.__file__).read_text(encoding="utf-8")
    assert fonte.count(guarda) == 1, "a guarda do lembrete mudou — atualize a mutação"
    monkeypatch.setitem(REG._REGISTRO, WF.WORKFLOW_KEY, REG._REGISTRO[WF.WORKFLOW_KEY])
    mod = types.ModuleType("app.services.canal.workflows_mutado")
    exec(compile(fonte.replace(guarda, "if False:"), "workflows_mutado.py", "exec"), mod.__dict__)
    return mod


GUARDA_DO_LEMBRETE = ('if est.get("respondeu_em") or est.get("etapa") != "resultado" or '
                      'est.get("pedido_id") != pedido_id:')


@pytest.mark.parametrize("mutado", [False, True], ids=["controle_cancelamento_perdido", "mutacao_sem_a_guarda"])
def test_mutacao_lembrete_depois_da_resposta(fio, monkeypatch, mutado):
    """O cancelamento do run se PERDE (no-op) e a pessoa respondeu "não": a guarda do estado segura (controle: zero
    lembrete); sem a guarda (mutação), o lembrete SAI — o ⑦ do fio ficaria vermelho."""
    f, m = fio, fio.m
    if mutado:
        _workflow_mutado(monkeypatch, GUARDA_DO_LEMBRETE)
    monkeypatch.setattr(f.cotacao, "cancelar_lembretes", lambda *_a, **_k: False)
    est, _ = ate_o_resultado(f)
    f.falar("não")
    antes = len(f.envio.enviados)
    for _ in range(3):
        if acordar(m.banco, f.db, est["run_id"]):
            asyncio.run(rodar_o_run(f.db, est["run_id"], m.canal))
    saidos = f.envio.enviados[antes:]
    assert (len(saidos) > 0) is mutado, saidos

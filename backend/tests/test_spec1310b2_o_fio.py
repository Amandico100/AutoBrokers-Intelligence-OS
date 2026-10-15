# -*- coding: utf-8 -*-
"""modelo: claude-opus-5-5 · SPEC-131-0-B2 · L4-B — O TESTE DO FIO: a linha do usuário de ponta a ponta, pelo MOTOR real.

O fio da SPEC §2, elo a elo, com DUAS corretoras reais no mesmo teste (Alfa: U1 · Beta: U4, cada uma com a SUA linha):

    E1  POST /api/linha-do-usuario/conectar (chave interna, company_id+user_id)   app.api.linha_do_usuario REAL
        → linha_do_usuario.pareamento.conectar → PairingOrchestrator REAL (escopo company+purpose+DONO)
        → channel_identity.nome_da_instancia(company,'linha_do_usuario',dono) → o QR (o do 2º nunca é o do 1º)
    E2  GET /qr devolve o MESMO QR · o connect assinou MESSAGE,CONNECTION,QRCODE (sem HISTORY_SYNC) com o webhookUrl
    E3  o celular lê o QR → o GO manda PairSuccess → POST /api/v1/webhook/evolution-go/<token> (rota REAL, o hunk da
        linha) → entrada.desviar → estado.registrar_conexao → integrations (número, jid, lid, conectada desde)
    E4  as boas-vindas (boas_vindas REAL) à PRÓPRIA conta, "▸ AutoBrokers\\n…", pelo whatsapp_service REAL →
        EvolutionGoProvider._post REAL → o GO devolve o id → gravado em linha_mensagens_do_sistema (M6)
    E5  "Mensagem para você" → o portão (filtrar) → turno_da_linha → atalho.turno.rodar (origem linha_do_usuario)
        → POST /chat/stream REAL (o grafo é o dublê da 132-C) → enviar_pela_linha → o cinto atalho.envio.enviar
        (a exceção exata: a própria conta) → "▸ AutoBrokers\\n…" pela MESMA instância
    E6  o ECO dessa resposta voltando (mesmo id) não vira pergunta — pelo prefixo e, com o texto mudado, pelo ID (M6)
    E7  mensagem de OUTRA conversa no mesmo webhook → 0 bytes (messages, conversas, anti-eco, Storage, envio, log);
        só o contador `descartadas_total`
    E8  a linha de A nunca responde dado de B (cada turno na corretora e no dono da linha que recebeu)
    E9  a volta da cotação pela MESMA linha (avisar_pelo_atalho_se_for_o_caso)
    E10 o aviso do sistema (avisos.avisar): chave ligada para o tipo → sai pela linha; chave ausente → só registra
    E11 GET /estado → conectada, número mascarado, desde = a conexão; a outra corretora não enxerga a linha

Dublê SÓ na borda: o Evolution GO (com estado: instâncias, QR, envio que devolve `data.Info.ID`), o banco em memória
e o Redis (da 132-C e da SPEC-051, importados), o grafo do modelo (arreio da 132-C), a digital de voz (Redis).
Mutações: `python tests/test_spec1310b2_o_fio.py --mutar` (cada elo cortado POR CÓPIA; exige VERMELHO; restaura).
⛔ Dados fictícios (5511900000001…, "Corretora Alfa/Beta"); nenhum nome de corretora real (CLAUDE.md §13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec1310b2_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec132c_o_atalho as C2  # noqa: E402  (o mundo, o arreio do /chat/stream e a fixture `fio`)
from test_spec132c_o_atalho import fio  # noqa: E402,F401  (a fixture)
import test_spec1310b2_pareamento as PA  # noqa: E402  (o Evolution GO com estado — importado, não copiado)
from test_spec051_pairing_behavior import FakeRedis  # noqa: E402

from app.services.atalho import envio as AENV  # noqa: E402
from app.services.atalho import turno as T  # noqa: E402
from app.services.linha_do_usuario import avisos as AV  # noqa: E402
from app.services.linha_do_usuario import boas_vindas as BV  # noqa: E402
from app.services.linha_do_usuario import entrada as ENT  # noqa: E402
from app.services.whatsapp import channel_identity as CI  # noqa: E402

ALFA, BETA, U1, U4 = C2.ALFA, C2.BETA, C2.U1, C2.U4
LINHA = "linha_do_usuario"
NUM_A, NUM_B = "5511900000001", "5521900000004"          # 💭 fictícios — a conta de U1 (Alfa) e a de U4 (Beta)
JID_A, JID_B = NUM_A + "@s.whatsapp.net", NUM_B + "@s.whatsapp.net"
LID_A = "190000000000001@lid"                            # 💭 fictício (opaco)
OUTRO = "5511900000099@s.whatsapp.net"                   # 💭 um cliente do corretor
SEGREDO = "conteudo-sigiloso-da-outra-conversa"


# =====================================================================================================================
# a borda: o Evolution GO com estado + o ENVIO (que devolve o id, como o GO de verdade)
# =====================================================================================================================
class GoComEnvio(PA.EvolutionFalso):
    """O Evolution GO do pareamento (L1) + `/send/text` e `/message/presence` pela chave DA INSTÂNCIA. O envio volta
    200 com `data.Info.ID` (um dos formatos que `EvolutionGoProvider._post` lê) e fica guardado por instância."""

    def __init__(self):
        super().__init__()
        self.enviadas = []
        self._n = 0

    def __call__(self, pedido):
        import httpx

        caminho = pedido.url.path
        if caminho not in ("/send/text", "/message/presence"):
            return super().__call__(pedido)
        corpo = json.loads(pedido.content.decode() or "null")
        i = self._por_token(pedido.headers.get("apikey"))
        if i is None:
            return httpx.Response(401, json={"error": "unauthorized"})
        if caminho == "/message/presence":
            return httpx.Response(200, json={"data": {}})
        self._n += 1
        mid = f"3EB0GOENVIO{self._n:010d}"
        self.enviadas.append({"instancia": i["name"], "para": corpo["number"], "texto": corpo["text"], "id": mid})
        return httpx.Response(200, json={"message": "success", "data": {
            "Info": {"ID": mid, "Chat": corpo["number"] + "@s.whatsapp.net", "IsFromMe": True}}})

    def da(self, nome):
        return [e for e in self.enviadas if e["instancia"] == nome]


class _RespostaRequests:
    """A resposta do `requests` (o que o `EvolutionGoProvider._post` lê) por cima de um `httpx.Response`."""

    def __init__(self, r):
        self.status_code, self.text, self._r = r.status_code, r.text, r

    def json(self):
        return self._r.json()


# =====================================================================================================================
# a fixture: o mundo da 132-C (webhook REAL + /chat/stream REAL) + a API da linha + o pareamento REAL + o envio REAL
# =====================================================================================================================
@pytest.fixture
def lu(fio, monkeypatch):
    import httpx
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.agents.capability_resolver as CR
    import app.api.linha_do_usuario as API
    import app.core.database as DB
    import app.services.whatsapp.integration_secrets as SEG
    import app.services.whatsapp.pairing_orchestrator as PO
    import app.services.whatsapp.providers.evolution_go as EG
    import app.services.whatsapp.voz_propria as VOZ
    import app.services.whatsapp_service as WS
    from app.services.linha_do_usuario import pareamento as P

    chave = fio.arreio.CHAVE_INTERNA_D
    monkeypatch.setenv("EVOLUTION_GO_BASE_URL", PA.BASE)
    monkeypatch.setenv("EVOLUTION_GO_GLOBAL_KEY", PA.EvolutionFalso.GLOBAL)
    monkeypatch.setenv("PUBLIC_BACKEND_URL", PA.PUBLICO)
    monkeypatch.setenv("LINHA_DO_USUARIO_LIGADA", "1")
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", chave)
    monkeypatch.delenv("LINHA_DO_USUARIO_MAX_LINHAS", raising=False)
    monkeypatch.delenv("AVISOS_WHATSAPP_LIGADO", raising=False)
    monkeypatch.setattr(ENT, "DESCARREGAR_A_CADA", 1)            # o contador desce ao banco a cada descarte
    ENT._DESCARTADAS.clear()

    b = fio.banco
    for p in b.linhas("users_v2"):
        if p["id"] == U1:
            p["first_name"], p["last_name"] = "Ana", "Teste"
        if p["id"] == U4:
            p["first_name"], p["last_name"] = "Bia", "Teste"
    b.dados.setdefault("linha_mensagens_do_sistema", [])
    b.dados.setdefault("linha_avisos_registro", [])

    # o banco, os segredos e o Registry (borda)
    monkeypatch.setattr(DB, "get_supabase_client", lambda: types.SimpleNamespace(client=b))
    monkeypatch.setattr(API, "_db", lambda: b)
    monkeypatch.setattr(SEG, "encrypt_integration_secret", lambda v: v)
    monkeypatch.setattr(SEG, "decrypt_integration_secret", lambda v, **_k: v)
    monkeypatch.setattr(CR, "resolve_active_capabilities", lambda _db, cid, _role: (
        {BV.CAPABILITY_DA_COTACAO: {"status": "active"}} if str(cid) == ALFA else {}))

    # o Evolution GO: o pareamento (httpx assíncrono) e o envio (requests) falam com o MESMO servidor falso
    go = GoComEnvio()
    original_async = httpx.AsyncClient

    def _cliente(*a, **k):
        if "transport" not in k:                     # o /chat/stream em processo (ASGITransport) passa intocado
            k["transport"] = httpx.MockTransport(go)
        return original_async(*a, **k)

    monkeypatch.setattr(PO.httpx, "AsyncClient", _cliente)

    def _post(url, json=None, headers=None, timeout=None, **_k):
        assert str(url).startswith(PA.BASE), "o envio saiu para fora do Evolution GO da linha"
        return _RespostaRequests(go(httpx.Request("POST", url, json=json, headers=headers)))

    monkeypatch.setattr(EG.requests, "post", _post)
    # o envio REAL (whatsapp_service → registry → EvolutionGoProvider) no lugar do dublê da 132-C; a digital da voz é
    # Redis (borda)
    monkeypatch.setattr(WS, "get_whatsapp_service", lambda: WS.WhatsappService())
    monkeypatch.setattr(VOZ, "registrar_nossa_fala", lambda *_a, **_k: None)

    redis = FakeRedis()
    orq = PO.PairingOrchestrator()

    async def _redis():
        return redis

    monkeypatch.setattr(orq, "_redis", _redis)
    monkeypatch.setattr(P, "_orquestrador", lambda: orq)

    api_app = FastAPI()
    api_app.include_router(API.router)
    api = TestClient(api_app)
    H = {"X-AutoBrokers-Internal-Key": chave}

    def conectar(cid, uid):
        return api.post("/api/linha-do-usuario/conectar", headers=H,
                        json={"company_id": cid, "user_id": uid, "por_user_id": uid})

    def ler(rota, cid, uid, headers=H):
        return api.get(f"/api/linha-do-usuario/{rota}", headers=headers, params={"company_id": cid, "user_id": uid})

    def token_de(cid, uid):
        nome = CI.nome_da_instancia(cid, LINHA, dono=uid)
        return go.connects(nome)[-1][2]["webhookUrl"].rsplit("/", 1)[1]

    seq = {"n": 0}

    def mensagem(token, texto, *, chat, from_me=True, mid=None, grupo=False):
        seq["n"] += 1
        info = {"Chat": chat, "Sender": chat, "IsFromMe": from_me, "IsGroup": grupo,
                "ID": mid or f"3EB0FIO{seq['n']:014d}", "PushName": "Pessoa",
                "Timestamp": "2026-10-15T12:00:00Z", "Type": "text"}
        st, r = fio.postar_cru({"event": "Message", "instanceId": "x",
                                "data": {"Info": info, "Message": {"conversation": texto}}}, token=token)
        assert st == 200, r
        return r

    def evento(token, corpo):
        st, r = fio.postar_cru(corpo, token=token)
        assert st == 200, r
        return r

    def linha(cid, uid):
        return next(x for x in b.linhas("integrations") if x.get("purpose") == LINHA
                    and x.get("company_id") == cid and x.get("owner_user_id") == uid)

    return types.SimpleNamespace(fio=fio, banco=b, go=go, api=api, H=H, conectar=conectar, ler=ler,
                                 token_de=token_de, mensagem=mensagem, evento=evento, linha=linha)


def _snapshot(b):
    return {t: len(b.linhas(t)) for t in ("messages", "conversations", "linha_mensagens_do_sistema",
                                         "linha_avisos_registro")} | {"arquivos": len(b.arquivos)}


# =====================================================================================================================
# O FIO — do botão "Conectar meu WhatsApp" à resposta pela própria linha, com duas corretoras
# =====================================================================================================================
def test_o_fio_inteiro_da_linha_do_usuario_com_duas_corretoras(lu, caplog):
    caplog.set_level(logging.DEBUG)
    b, go, fio = lu.banco, lu.go, lu.fio
    nome_a, nome_b = CI.nome_da_instancia(ALFA, LINHA, dono=U1), CI.nome_da_instancia(BETA, LINHA, dono=U4)

    # ---- E1 · o botão "Conectar meu WhatsApp" → a API interna → o pareamento → o QR ---------------------------------
    sem_chave = lu.api.post("/api/linha-do-usuario/conectar", json={"company_id": ALFA, "user_id": U1,
                                                                     "por_user_id": U1})
    assert sem_chave.status_code == 401 and go.pedidos == []
    ra, rb = lu.conectar(ALFA, U1), lu.conectar(BETA, U4)
    assert ra.status_code == rb.status_code == 200, (ra.text, rb.text)
    ra, rb = ra.json(), rb.json()
    assert ra["estado"] == rb["estado"] == "aguardando_qr" and ra["tentativa_id"] != rb["tentativa_id"]
    assert ra["qr"].startswith("data:image/png;base64,") and nome_a in ra["qr"] and nome_b in rb["qr"]
    assert set(go.inst) == {nome_a, nome_b}                              # uma instância por PESSOA

    # ---- E2 · o polling devolve o MESMO QR; o connect assinou sem HISTORY_SYNC, com o webhook da linha --------------
    assert lu.ler("qr", ALFA, U1).json()["qr"] == ra["qr"]
    for nome in (nome_a, nome_b):
        corpo = go.connects(nome)[-1][2]
        assert corpo["subscribe"] == ["MESSAGE", "CONNECTION", "QRCODE"] and "HISTORY_SYNC" not in json.dumps(corpo)
        assert corpo["webhookUrl"].startswith(f"{PA.PUBLICO}/api/v1/webhook/evolution-go/")
    tok_a, tok_b = lu.token_de(ALFA, U1), lu.token_de(BETA, U4)
    assert lu.linha(ALFA, U1)["webhook_token_hash"] == C2._hash(tok_a) != C2._hash(tok_b)
    assert lu.ler("estado", ALFA, U1).json()["estado"] == "aguardando_qr"

    # ---- E3 · o celular lê o QR → o evento de conexão no webhook → integrations (número, jid, lid) -----------------
    go.ler_qr(nome_a, NUM_A)
    go.ler_qr(nome_b, NUM_B)
    assert lu.evento(tok_a, {"event": "PairSuccess", "data": {"ID": NUM_A + ":7@s.whatsapp.net", "LID": LID_A}}) == {
        "status": "ok", "event": "linha_conexao"}
    assert lu.evento(tok_b, {"event": "PairSuccess", "data": {"ID": NUM_B + ":3@s.whatsapp.net"}}) == {
        "status": "ok", "event": "linha_conexao"}
    la = lu.linha(ALFA, U1)
    assert la["channel_status"] == "connected" and la["is_active"] is True and la["paired_phone_e164"] == "+" + NUM_A
    assert la["linha_jid"].startswith(NUM_A) and la["linha_lid"] == LID_A and la["linha_conectada_em"]
    assert lu.linha(BETA, U4)["paired_phone_e164"] == "+" + NUM_B

    # ---- E4 · as boas-vindas: UMA, à PRÓPRIA conta, com o prefixo, pela PRÓPRIA instância; o id do GO guardado -------
    (bv_a,), (bv_b,) = go.da(nome_a), go.da(nome_b)
    assert bv_a["para"] == NUM_A and bv_a["texto"].startswith("▸ AutoBrokers\nOi, Ana! Pronto:")
    assert "AutoBrokers da Corretora Alfa." in bv_a["texto"] and "*Cotação*" in bv_a["texto"]
    assert bv_b["para"] == NUM_B and "Oi, Bia!" in bv_b["texto"] and "Corretora Beta." in bv_b["texto"]
    assert "Corretora Alfa" not in bv_b["texto"] and "*Cotação*" not in bv_b["texto"]
    ids_gravados = {(r["integration_id"], r["message_id"]) for r in b.linhas("linha_mensagens_do_sistema")}
    assert (la["id"], bv_a["id"]) in ids_gravados, "M6: o id que o GO deu às boas-vindas não foi guardado"
    assert (lu.linha(BETA, U4)["id"], bv_b["id"]) in ids_gravados
    assert fio.envio.enviados == []                                      # nada saiu pelo central da 132-C

    # ---- E5 · "Mensagem para você" → o turno → a resposta "▸ AutoBrokers\n…" pela MESMA linha -----------------------
    r = lu.mensagem(tok_a, "quanto fica o seguro do carro do meu cliente?", chat=JID_A)
    assert r == {"status": "accepted", "reason": "linha"}
    assert [(g["company_id"], g["user_id"]) for g in fio.grafo] == [(ALFA, U1)]
    (conv_a,) = C2._conversas(b, company_id=ALFA, user_id=U1)
    assert conv_a["channel"] == T.CANAL_DO_ATALHO
    (pergunta,) = [m for m in C2._mensagens(b, conv_a["id"]) if m["role"] == "user"]
    assert pergunta["payload"]["origem"] == T.ORIGEM_DA_LINHA
    resposta = go.da(nome_a)[-1]
    assert resposta["para"] == NUM_A and resposta["texto"].startswith("▸ AutoBrokers\n*Cotação Rápida — 3 seguradoras*")
    assert (la["id"], resposta["id"]) in {(r["integration_id"], r["message_id"])
                                          for r in b.linhas("linha_mensagens_do_sistema")}

    # ---- E6 · o eco da resposta (o MESMO id) não vira pergunta: o prefixo; e, com o texto mudado, o ID (M6) ---------
    antes = (len(fio.grafo), len(b.linhas("messages")), len(go.enviadas))
    assert lu.mensagem(tok_a, resposta["texto"], chat=JID_A, mid=resposta["id"])["reason"] == "linha_eco_prefixo"
    assert lu.mensagem(tok_a, "o aparelho mostrou o texto de outro jeito", chat=JID_A,
                       mid=resposta["id"])["reason"] == "linha_eco_id"
    assert lu.mensagem(tok_a, "boas-vindas reformatadas", chat=JID_A, mid=bv_a["id"])["reason"] == "linha_eco_id"
    assert (len(fio.grafo), len(b.linhas("messages")), len(go.enviadas)) == antes

    # ---- E7 · OUTRA conversa no MESMO webhook → 0 bytes; só o contador ---------------------------------------------
    foto, escritas = _snapshot(b), len(b.escritas)
    for chat, de_mim, grupo in ((OUTRO, False, False), (OUTRO, True, False), ("120363000000000001@g.us", True, True),
                                ("status@broadcast", True, False)):
        r = lu.mensagem(tok_a, SEGREDO, chat=chat, from_me=de_mim, grupo=grupo)
        assert r["status"] == "ignored" and r["reason"] in ("linha_outra_conversa", "linha_grupo_ou_status"), r
    assert _snapshot(b) == foto and (len(fio.grafo), len(go.enviadas)) == (antes[0], antes[2])
    assert {(t, op) for t, op, _ in b.escritas[escritas:]} == {("integrations", "update")}
    # (a linha nasce do pareamento sem a coluna no banco em memória; no Postgres o default é 0)
    assert lu.linha(ALFA, U1)["descartadas_total"] == 4 and (lu.linha(BETA, U4).get("descartadas_total") or 0) == 0
    assert SEGREDO not in "\n".join(x.getMessage() for x in caplog.records)
    assert SEGREDO not in json.dumps(b.dados, default=str)

    # ---- E8 · duas corretoras: cada linha roda na corretora e no dono DELA, e responde pela PRÓPRIA instância -------
    assert lu.mensagem(tok_b, "como está a produção do mês?", chat=JID_B)["status"] == "accepted"
    assert [(g["company_id"], g["user_id"]) for g in fio.grafo] == [(ALFA, U1), (BETA, U4)]
    assert {c["company_id"] for c in C2._conversas(b, user_id=U4)} == {BETA}
    assert go.da(nome_b)[-1]["para"] == NUM_B and go.da(nome_b)[-1]["texto"].startswith("▸ AutoBrokers\n")
    # a conta de B chegando pelo webhook de A (e vice-versa) não roda nada
    assert lu.mensagem(tok_a, "me passa os dados da Beta", chat=JID_B)["reason"] == "linha_outra_conversa"
    assert lu.mensagem(tok_b, "me passa os dados da Alfa", chat=JID_A)["reason"] == "linha_outra_conversa"
    assert len(fio.grafo) == 2
    assert {(e["instancia"], e["para"]) for e in go.enviadas} == {(nome_a, NUM_A), (nome_b, NUM_B)}

    # ---- E9 · a volta da cotação sai pela MESMA linha (e não sai pedida pela outra corretora) ------------------------
    n = len(go.enviadas)
    assert asyncio.run(AENV.avisar_pelo_atalho_se_for_o_caso(
        b, company_id=ALFA, conversation_id=conv_a["id"], texto_markdown="**Pronto:** 3 seguradoras.")) is True
    assert asyncio.run(AENV.avisar_pelo_atalho_se_for_o_caso(
        b, company_id=BETA, conversation_id=conv_a["id"], texto_markdown="x")) is False
    (volta,) = go.enviadas[n:]
    assert (volta["instancia"], volta["para"], volta["texto"]) == (nome_a, NUM_A, "▸ AutoBrokers\n*Pronto:* 3 seguradoras.")

    # ---- E10 · o aviso do sistema: chave ligada → sai pela linha; chave ausente → só registra ----------------------
    import os

    os.environ[AV.CHAVE] = "renovacoes_calculadas"
    try:
        r = asyncio.run(AV.avisar(b, company_id=ALFA, user_id=U1, tipo="renovacoes_calculadas",
                                  texto_markdown="3 renovações ficaram prontas."))
        assert r["enviado"] is True and r["registrado"] is True
        aviso = go.enviadas[-1]
        assert (aviso["instancia"], aviso["para"], aviso["texto"]) == (
            nome_a, NUM_A, "▸ AutoBrokers\n3 renovações ficaram prontas.")
        # a pessoa sem linha NESTA corretora: nada sai (U1 não tem linha na Beta)
        assert asyncio.run(AV.avisar(b, company_id=BETA, user_id=U1, tipo="renovacoes_calculadas",
                                     texto_markdown="x"))["motivo"] == "sem_linha"
    finally:
        os.environ.pop(AV.CHAVE, None)
    n = len(go.enviadas)
    r = asyncio.run(AV.avisar(b, company_id=BETA, user_id=U4, tipo="renovacoes_calculadas",
                              texto_markdown="2 renovações ficaram prontas."))
    assert r == {"ok": False, "tipo": "renovacoes_calculadas", "enviado": False, "motivo": "avisos_desligados",
                 "registrado": True}
    assert len(go.enviadas) == n
    registro = b.linhas("linha_avisos_registro")
    assert [(x["company_id"], x["user_id"], x["enviado"], x["motivo_nao_enviado"]) for x in registro] == [
        (ALFA, U1, True, None), (BETA, U1, False, "sem_linha"), (BETA, U4, False, "avisos_desligados")]
    assert "renovações" not in json.dumps(registro)                       # o registro nunca leva o texto

    # ---- E11 · GET /estado: conectada, mascarada, desde a conexão; a outra corretora não enxerga --------------------
    assert lu.ler("estado", ALFA, U1, headers={}).status_code == 401
    ea = lu.ler("estado", ALFA, U1).json()
    assert ea == {"estado": "conectada", "numero_mascarado": "5511*****001",
                  "desde": lu.linha(ALFA, U1)["linha_conectada_em"], "motivo": None}
    assert lu.ler("estado", BETA, U4).json()["numero_mascarado"] == "5521*****004"
    # U4 é só da Beta: pela Alfa o bloco SOME (`desligada`; antes `nao_conectada` — fix/linha-por-pessoa)
    assert lu.ler("estado", ALFA, U4).json()["estado"] == "desligada"
    assert NUM_A not in json.dumps(ea)

    # o fio nunca tocou o observer nem o pipeline de atendimento/QCM, nem o número central
    assert fio.taps == [] and fio.pipeline == [] and fio.envio.enviados == []


# =====================================================================================================================
# M6 por construção — o `_post` REAL do EvolutionGoProvider devolve o id da mensagem enviada (todo formato conhecido)
# =====================================================================================================================
@pytest.mark.parametrize("corpo,esperado", [
    ({"data": {"Info": {"ID": "3EB0INFO"}}}, "3EB0INFO"),
    ({"data": {"ID": "3EB0MAIUSCULO"}}, "3EB0MAIUSCULO"),
    ({"data": {"key": {"id": "3EB0CHAVE", "fromMe": True}}}, "3EB0CHAVE"),
    ({"data": {"id": "3EB0MINUSCULO"}}, "3EB0MINUSCULO"),
    ({"data": {}}, None),
    ({"message": "success"}, None),
    ({"data": [{"id": "x"}]}, None),
    ({"data": {"Info": {"ID": ""}, "ID": "  "}}, None),
    ({"data": {"Info": {"ID": 123}}}, None),
    ("nao-e-json", None),
], ids=["Info.ID", "ID", "key.id", "id", "data-vazio", "sem-data", "data-lista", "vazio", "nao-texto", "nao-json"])
def test_o_post_do_evolution_go_devolve_o_id_do_envio(monkeypatch, corpo, esperado):
    import app.services.whatsapp.providers.evolution_go as EG

    class _R:
        status_code = 200
        text = "ok"

        def json(self):
            if isinstance(corpo, str):
                raise ValueError("não é JSON")
            return corpo

    monkeypatch.setattr(EG.requests, "post", lambda *a, **k: _R())
    p = EG.EvolutionGoProvider({"base_url": PA.BASE, "token": "tok", "instance_id": "inst"})
    r = p.send_text("5511900000001", "oi")
    assert r.ok is True and r.provider_message_id == esperado


def test_controle_o_post_que_falha_continua_igual(monkeypatch):
    import app.services.whatsapp.providers.evolution_go as EG

    class _R:
        status_code = 400
        text = '{"data":{"Info":{"ID":"3EB0NAO"}}}'

        def json(self):
            return {"data": {"Info": {"ID": "3EB0NAO"}}}

    monkeypatch.setattr(EG.requests, "post", lambda *a, **k: _R())
    r = EG.EvolutionGoProvider({"base_url": PA.BASE, "token": "tok", "instance_id": "inst"}).send_text("1", "oi")
    assert r.ok is False and r.provider_message_id is None and r.error.startswith("HTTP 400")


# =====================================================================================================================
# as MUTAÇÕES (por cópia) — `python tests/test_spec1310b2_o_fio.py --mutar`: cada uma corta UM elo do fio
# =====================================================================================================================
_FIO = "test_o_fio_inteiro_da_linha_do_usuario_com_duas_corretoras"
MUTACOES = [
    ("ELO webhook: o hunk da linha desfeito (o evento cai no resto do webhook)", "app/api/webhook.py",
     "    if str(integration.get(\"purpose\") or \"\").strip().lower() == \"linha_do_usuario\":\n",
     "    if False:\n", _FIO),
    ("M6a: o _post nao devolve o id do envio", "app/services/whatsapp/providers/evolution_go.py",
     "        return SendResult(ok=True, provider_message_id=_id_da_mensagem_enviada(response))\n",
     "        return SendResult(ok=True)\n", _FIO),
    ("M6b: a linha nao grava o id do envio", "app/services/linha_do_usuario/entrada.py",
     "        if enviados:\n            await asyncio.to_thread(_registrar_ids_enviados, db, row, enviados)\n",
     "        if False:\n            await asyncio.to_thread(_registrar_ids_enviados, db, row, enviados)\n", _FIO),
]


def _mutar() -> int:
    falhas = 0
    for rotulo, arquivo, de, para, teste in MUTACOES:
        caminho = BACKEND / arquivo
        bruto = caminho.read_bytes()
        original = bruto.decode("utf-8")
        crlf = "\r\n" in original
        de_, para_ = (de.replace("\n", "\r\n"), para.replace("\n", "\r\n")) if crlf else (de, para)
        assert original.count(de_) == 1, f"{rotulo}: o trecho não está UMA vez em {arquivo}"
        try:
            caminho.write_bytes(original.replace(de_, para_).encode("utf-8"))
            r = subprocess.run([sys.executable, "-m", "pytest", __file__, "-q", "-p", "no:cacheprovider", "-k", teste],
                               cwd=str(BACKEND), capture_output=True, text=True)
            vermelho = r.returncode != 0
            falha = next((l.strip() for l in r.stdout.splitlines() if l.strip().startswith("E ")), "")
            ultima = (r.stdout.strip().splitlines() or [""])[-1]
            print(f"{rotulo}: {'VERMELHO (o fio pegou)' if vermelho else 'MUTACAO NAO PEGOU'} — {ultima}\n    {falha}")
            falhas += 0 if vermelho else 1
        finally:
            caminho.write_bytes(bruto)                          # 🔴 restaura POR CÓPIA DOS BYTES
            assert caminho.read_bytes() == bruto, f"{rotulo}: {arquivo} não voltou igual"
    return falhas


if __name__ == "__main__" and "--mutar" in sys.argv:
    sys.exit(_mutar())

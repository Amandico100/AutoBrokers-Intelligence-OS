# -*- coding: utf-8 -*-
"""SPEC-131-0-B2 · L1 — A LINHA COM DONO: uma instância do Evolution GO por PESSOA, pareada no Meu perfil.

O que este arquivo prova (dublê SÓ na borda — banco em memória, Redis falso, o Evolution GO num `httpx.MockTransport`
que guarda estado; a rede fica FECHADA). O motor é o REAL: `linha_do_usuario.pareamento` → `PairingOrchestrator`
(start/get/cancel/liberar/_prepare_and_connect/_refresh/_mark_connected) → `channel_identity` → `linha_do_usuario.estado`
→ a API `app.api.linha_do_usuario` (rota real num app mínimo).

    1. o nome da instância carrega o DONO; dois donos da mesma corretora → duas instâncias, dois QRs
    2. 🔴 o 2º corretor NUNCA recebe o QR do 1º (a MUTAÇÃO 5 da SPEC)
    3. o connect da linha assina MESSAGE, CONNECTION, QRCODE — nunca HISTORY_SYNC — e SEMPRE com webhookUrl
    4. depois do QRTimeout o QR renova chamando o connect de novo (com webhookUrl)
    5. QR lido → conectada (número mascarado, "desde" = a conexão); a corretora A não lê a linha da B (2 corretoras)
    6. teto cheio → `limite` (409 no POST), sem chamar o Evolution · chave ausente → `desligada`, sem chamar o Evolution
    7. desconectar: a conectada (logout + solta + inativa, nada apagado) e a PENDENTE (o "Cancelar" da tela)
    8. a desconexão vinda do provedor → `desconectada` com `desde` = a data da DESCONEXÃO; evento só com LID
    9. 🧪 LINHA DE CONTROLE: observer/attendance/dispatch/auxiliar/assistente(QCM) com nome, escopo, chave e corpo IGUAIS
   10. a API exige a chave interna (401) e recusa por_user_id ≠ user_id (422)

Mutação: `python tests/test_spec1310b2_pareamento.py --mutar` (por cópia dos bytes; exige VERMELHO; restaura).
⛔ Dados fictícios: uuids sintéticos, telefones 💭 inventados (5511900000001…), "Corretora Alfa/Beta" (CLAUDE.md §13.9).
Rodar: cd backend && python -m pytest tests/test_spec1310b2_pareamento.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec132c_o_atalho as C2  # noqa: E402  (o banco em memória da 132-C — importado, não copiado)
from test_spec051_pairing_behavior import FakeRedis  # noqa: E402  (o Redis com o `eval` do _save — importado)

from app.services.linha_do_usuario import estado as E  # noqa: E402
from app.services.linha_do_usuario import pareamento as P  # noqa: E402
from app.services.whatsapp import channel_identity as CI  # noqa: E402
import app.services.whatsapp.pairing_orchestrator as PO  # noqa: E402

ALFA = "aaaaaaaa-0000-4000-8000-0000000000a1"
BETA = "bbbbbbbb-0000-4000-8000-0000000000b1"
U1 = "11111111-0000-4000-8000-000000000001"     # Alfa
U2 = "22222222-0000-4000-8000-000000000002"     # Alfa E Beta (a mesma pessoa nas duas)
U3 = "33333333-0000-4000-8000-000000000003"     # Beta
FORA = "99999999-0000-4000-8000-000000000009"   # não é membro de nada
TEL = {U1: "5511900000001", U2: "5511900000002", U3: "5521900000003"}   # 💭 inventados
BASE = "http://evolution.invalid"
PUBLICO = "https://backend.exemplo.test"
CHAVE_INTERNA = "chave-interna-de-teste"
LINHA = "linha_do_usuario"


# =====================================================================================================================
# a borda: o Evolution GO (com estado), o banco e o Redis
# =====================================================================================================================
class EvolutionFalso:
    """O Evolution GO na borda: instâncias por nome, chave GLOBAL para criar/listar/apagar, chave DA INSTÂNCIA para
    status/connect/qr/logout. Formas 📊 medidas pelo gerente em 15/10 (pacote §2): `data.Qrcode`, QRTimeout."""

    GLOBAL = "chave-global-de-teste"

    def __init__(self):
        self.inst = {}          # nome -> dict
        self.pedidos = []       # (método, caminho, corpo, apikey)
        self._seq = 0

    def _por_token(self, token):
        return next((i for i in self.inst.values() if i["token"] == token), None)

    def ler_qr(self, nome, telefone):
        """O celular leu o QR: a sessão sobe e o provedor passa a ter o JID."""
        i = self.inst[nome]
        i.update(logado=True, jid=f"{telefone}:7@s.whatsapp.net")

    def __call__(self, pedido):
        import httpx

        corpo = json.loads(pedido.content.decode() or "null") if pedido.content else None
        chave = pedido.headers.get("apikey")
        caminho, metodo = pedido.url.path, pedido.method
        self.pedidos.append((metodo, caminho, copy.deepcopy(corpo), chave))
        if caminho == "/instance/create":
            assert chave == self.GLOBAL
            if corpo["name"] in self.inst:
                return httpx.Response(500, json={"error": "instance already exists"})
            self._seq += 1
            self.inst[corpo["name"]] = {"id": f"id-{self._seq}", "name": corpo["name"], "token": corpo["token"],
                                        "jid": "", "logado": False, "qr_n": 0, "qr_ok": False, "expirado": False,
                                        "conectada_ws": False, "settings": corpo.get("advancedSettings")}
            return httpx.Response(200, json={"data": {"id": f"id-{self._seq}", "name": corpo["name"]}})
        if caminho == "/instance/all":
            assert chave == self.GLOBAL
            return httpx.Response(200, json={"data": [{"id": i["id"], "name": i["name"], "jid": i["jid"]}
                                                      for i in self.inst.values()]})
        if caminho.startswith("/instance/delete/"):
            assert chave == self.GLOBAL
            alvo = caminho.rsplit("/", 1)[1]
            self.inst = {k: v for k, v in self.inst.items() if v["id"] != alvo}
            return httpx.Response(200, json={"data": {}})
        i = self._por_token(chave)
        if i is None:
            return httpx.Response(401, json={"error": "unauthorized"})
        if caminho == "/instance/status":
            dados = {"Connected": i["conectada_ws"] or i["logado"], "LoggedIn": i["logado"], "Name": i["name"]}
            if i["logado"]:
                dados["jid"] = i["jid"]
            return httpx.Response(200, json={"data": dados})
        if caminho == "/instance/connect":
            i.update(qr_n=i["qr_n"] + 1, qr_ok=True, expirado=False, conectada_ws=True)
            eventos = ",".join(corpo.get("subscribe") or ["MESSAGE"])
            return httpx.Response(200, json={"data": {"eventString": eventos, "jid": "",
                                                      "webhookUrl": corpo.get("webhookUrl")}})
        if caminho == "/instance/qr":
            if i["expirado"]:
                return httpx.Response(200, json={"data": {"state": "qr_expired", "errorCode": "qr_expired"}})
            if not i["qr_ok"]:
                return httpx.Response(400, json={"error": "no QR code available. Please wait a moment and try again"})
            return httpx.Response(200, json={"data": {"Qrcode": f"data:image/png;base64,QR-{i['name']}-{i['qr_n']}"}})
        if caminho == "/instance/logout":
            i.update(logado=False, conectada_ws=False, qr_ok=False)
            return httpx.Response(200, json={"data": {}})
        return httpx.Response(404, json={"error": "rota desconhecida no dublê"})

    def connects(self, nome=None):
        tokens = {i["token"]: n for n, i in self.inst.items()}
        return [p for p in self.pedidos if p[1] == "/instance/connect" and (nome is None or tokens.get(p[3]) == nome)]


def _membro(cid, uid):
    return {"company_id": cid, "user_id": uid, "role": "member", "status": "active"}


def mundo():
    nome_obs = CI.nome_da_instancia(ALFA, "observer")
    return C2.Banco(
        companies=[{"id": ALFA, "company_name": "Corretora Alfa"}, {"id": BETA, "company_name": "Corretora Beta"}],
        company_members=[_membro(ALFA, U1), _membro(ALFA, U2), _membro(BETA, U2), _membro(BETA, U3)],
        integrations=[
            # 🧪 controle: o número da corretora Alfa (observer). Nada da linha do usuário pode tocá-lo.
            {"id": "int-obs-alfa", "company_id": ALFA, "provider": "evolution-go", "purpose": "observer",
             "is_active": True, "channel_status": "connected", "identifier": nome_obs, "instance_id": nome_obs,
             "token": "tok-obs-alfa", "base_url": BASE, "paired_phone_e164": "+5511933330000",
             "created_at": "2026-10-01T00:00:00+00:00", "last_seen_at": "2026-10-14T00:00:00+00:00"}],
    )


@pytest.fixture
def mesa(monkeypatch):
    """O arreio: env de teste, banco, Redis e Evolution falsos, um orquestrador REAL novo."""
    import httpx

    import app.core.database as DB
    import app.core.redis as R
    import app.services.whatsapp.integration_secrets as SEG

    monkeypatch.setenv("EVOLUTION_GO_BASE_URL", BASE)
    monkeypatch.setenv("EVOLUTION_GO_GLOBAL_KEY", EvolutionFalso.GLOBAL)
    monkeypatch.setenv("PUBLIC_BACKEND_URL", PUBLICO)
    monkeypatch.setenv("LINHA_DO_USUARIO_LIGADA", "1")
    monkeypatch.delenv("LINHA_DO_USUARIO_MAX_LINHAS", raising=False)
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", CHAVE_INTERNA)
    banco, redis, evo = mundo(), FakeRedis(), EvolutionFalso()
    monkeypatch.setattr(DB, "get_supabase_client", lambda: types.SimpleNamespace(client=banco))

    async def _redis():
        return redis

    monkeypatch.setattr(R, "get_async_redis_client", _redis)
    monkeypatch.setattr(SEG, "encrypt_integration_secret", lambda v: v)
    monkeypatch.setattr(SEG, "decrypt_integration_secret", lambda v, **_k: v)
    original = httpx.AsyncClient

    def _cliente(*a, **k):
        k["transport"] = httpx.MockTransport(evo)
        return original(*a, **k)

    monkeypatch.setattr(PO.httpx, "AsyncClient", _cliente)
    orq = PO.PairingOrchestrator()
    monkeypatch.setattr(P, "_orquestrador", lambda: orq)
    return types.SimpleNamespace(banco=banco, redis=redis, evo=evo, orq=orq,
                                 obs_antes=copy.deepcopy(banco.linhas("integrations")[0]))


def _run(coro):
    return asyncio.run(coro)


def _linhas_da_linha(banco, **filtro):
    return [x for x in banco.linhas("integrations") if x.get("purpose") == LINHA
            and all(str(x.get(k)) == str(v) for k, v in filtro.items())]


def _conectar_e_ler(m, cid, uid):
    r = _run(P.conectar(m.banco, cid, uid))
    nome = CI.nome_da_instancia(cid, LINHA, dono=uid)
    m.evo.ler_qr(nome, TEL[uid])
    return r, _run(P.qr(m.banco, cid, uid))


# =====================================================================================================================
# 1-2. o nome carrega o dono · o 2º corretor NUNCA recebe o QR do 1º (MUTAÇÃO 5)
# =====================================================================================================================
def test_o_nome_carrega_o_dono_e_a_linha_sem_dono_e_recusada():
    n1, n2 = CI.nome_da_instancia(ALFA, LINHA, dono=U1), CI.nome_da_instancia(ALFA, LINHA, dono=U2)
    assert n1 == "ab-lu-aaaaaaaa00-111111110000" and n2 == "ab-lu-aaaaaaaa00-222222220000"
    assert n1 != n2 and n1 != CI.nome_da_instancia(BETA, LINHA, dono=U1)      # a corretora também está no nome
    assert CI.escopo_de(LINHA) == LINHA == CI.purpose_canonico(LINHA) and CI.numero_proprio(LINHA) is True
    for sem_dono in (None, "", "nao-e-uuid"):
        with pytest.raises(ValueError, match="linha_do_usuario_sem_dono"):
            CI.nome_da_instancia(ALFA, LINHA, dono=sem_dono)


def test_o_segundo_corretor_nunca_recebe_o_qr_do_primeiro(mesa):
    r1 = _run(P.conectar(mesa.banco, ALFA, U1))
    r2 = _run(P.conectar(mesa.banco, ALFA, U2))                      # a MESMA corretora, outra pessoa
    assert r1["estado"] == r2["estado"] == "aguardando_qr"
    assert r1["qr"] and r2["qr"] and r1["qr"] != r2["qr"], "o 2º corretor recebeu o QR do 1º"
    assert r1["tentativa_id"] != r2["tentativa_id"]
    n1, n2 = CI.nome_da_instancia(ALFA, LINHA, dono=U1), CI.nome_da_instancia(ALFA, LINHA, dono=U2)
    assert n1 in r1["qr"] and n2 in r2["qr"]
    assert set(mesa.evo.inst) == {n1, n2}                            # duas instâncias, uma por pessoa
    # o polling de cada um devolve o PRÓPRIO QR, sempre
    for _ in range(2):
        assert n2 in (_run(P.qr(mesa.banco, ALFA, U2))["qr"] or "")
        assert n1 in (_run(P.qr(mesa.banco, ALFA, U1))["qr"] or "")
    # a tentativa do 1º, pedida pelo 2º, NÃO EXISTE (mesma corretora, mesmo purpose)
    with pytest.raises(PO.PairingNotFoundError):
        _run(mesa.orq.get(ALFA, LINHA, r1["tentativa_id"], owner_user_id=U2))
    assert _run(mesa.orq.tentativa_atual(ALFA, LINHA, owner_user_id=U2))["attempt_id"] == r2["tentativa_id"]
    # as duas linhas ATIVAS, cada uma com o seu dono (parear a 2ª não aposentou a 1ª), e o observer intacto
    a1, a2 = _linhas_da_linha(mesa.banco, owner_user_id=U1), _linhas_da_linha(mesa.banco, owner_user_id=U2)
    assert len(a1) == len(a2) == 1 and a1[0]["is_active"] is True and a2[0]["is_active"] is True
    assert a1[0]["instance_id"] == n1 and a2[0]["instance_id"] == n2
    assert mesa.banco.linhas("integrations")[0] == mesa.obs_antes


def test_a_linha_sem_dono_ou_por_telefone_e_recusada_sem_chamar_o_evolution(mesa):
    with pytest.raises(ValueError, match="linha_do_usuario_sem_dono"):
        _run(mesa.orq.start(ALFA, LINHA))                          # ex.: a rota antiga de pareamento, sem dono
    with pytest.raises(ValueError, match="linha_do_usuario_so_por_qr"):
        _run(mesa.orq.start(ALFA, LINHA, method="phone", phone_number=TEL[U1], owner_user_id=U1))
    assert mesa.evo.pedidos == []


# =====================================================================================================================
# 3-4. a assinatura sem HISTORY_SYNC · o QR renova depois do QRTimeout (connect de novo, com webhookUrl)
# =====================================================================================================================
def test_o_connect_da_linha_nao_assina_history_sync_e_leva_o_webhook(mesa):
    _run(P.conectar(mesa.banco, ALFA, U1))
    nome = CI.nome_da_instancia(ALFA, LINHA, dono=U1)
    (connect,) = mesa.evo.connects(nome)
    corpo = connect[2]
    assert corpo["subscribe"] == ["MESSAGE", "CONNECTION", "QRCODE"]
    assert "HISTORY_SYNC" not in json.dumps(corpo)
    assert corpo["webhookUrl"].startswith(f"{PUBLICO}/api/v1/webhook/evolution-go/") and corpo["immediate"] is True
    assert mesa.evo.inst[nome]["settings"]["ignoreGroups"] is True and mesa.evo.inst[nome]["settings"]["ignoreStatus"]
    # o token do webhook bate com o hash gravado na linha DELE
    (linha,) = _linhas_da_linha(mesa.banco, owner_user_id=U1)
    assert linha["webhook_token_hash"] == C2._hash(corpo["webhookUrl"].rsplit("/", 1)[1])


def test_o_qr_renova_depois_do_qrtimeout_chamando_o_connect_de_novo(mesa):
    r = _run(P.conectar(mesa.banco, ALFA, U1))
    nome = CI.nome_da_instancia(ALFA, LINHA, dono=U1)
    assert r["qr"].endswith(f"QR-{nome}-1")
    mesa.evo.inst[nome]["expirado"] = True                           # o GO mandou o QRTimeout (5 QRs)
    r2 = _run(P.qr(mesa.banco, ALFA, U1))
    assert r2["estado"] == "aguardando_qr" and r2["qr"].endswith(f"QR-{nome}-2")
    connects = mesa.evo.connects(nome)
    assert len(connects) == 2
    assert all(c[2]["webhookUrl"].startswith(PUBLICO) and c[2]["subscribe"] == ["MESSAGE", "CONNECTION", "QRCODE"]
               for c in connects)
    assert len(_linhas_da_linha(mesa.banco, owner_user_id=U1)) == 1   # renovar não cria outra linha


# =====================================================================================================================
# 5. conectada · duas corretoras: a A não lê a linha da B
# =====================================================================================================================
def test_qr_lido_vira_conectada_com_numero_mascarado_e_desde(mesa):
    r, depois = _conectar_e_ler(mesa, ALFA, U1)
    assert depois["estado"] == "conectada" and depois["qr"] is None
    (linha,) = _linhas_da_linha(mesa.banco, owner_user_id=U1)
    assert linha["channel_status"] == "connected" and linha["paired_phone_e164"] == "+" + TEL[U1]
    assert linha["linha_jid"] == f"{TEL[U1]}:7@s.whatsapp.net" and linha["linha_conectada_em"]
    e = _run(P.estado(mesa.banco, ALFA, U1))
    assert e == {"estado": "conectada", "numero_mascarado": "5511*****001", "desde": linha["linha_conectada_em"],
                 "motivo": None}
    assert TEL[U1] not in json.dumps(e)                               # o número não sai cru
    ld = E.linha_do_dono(mesa.banco, ALFA, U1)
    assert ld["owner_user_id"] == U1 and "token" not in ld
    li = E.linha_da_instancia(mesa.banco, CI.nome_da_instancia(ALFA, LINHA, dono=U1))
    assert {k: li[k] for k in ("integration_id", "company_id", "owner_user_id", "jid", "lid")} == {
        "integration_id": linha["id"], "company_id": ALFA, "owner_user_id": U1, "jid": linha["linha_jid"], "lid": None}
    assert E.linha_da_instancia(mesa.banco, mesa.obs_antes["instance_id"]) is None   # observer não é linha


def test_a_corretora_a_nao_le_a_linha_da_b(mesa):
    _conectar_e_ler(mesa, BETA, U3)
    assert _run(P.estado(mesa.banco, BETA, U3))["estado"] == "conectada"
    # a MESMA pessoa/consulta pela corretora errada não enxerga nada
    assert E.linha_do_dono(mesa.banco, ALFA, U3) is None
    # quem não é membro da Alfa: o bloco SOME (`desligada`) — antes dizia `nao_conectada` e o botão aparecia
    # para um conectar que o próprio `conectar` recusa (fix/linha-por-pessoa)
    assert _run(P.estado(mesa.banco, ALFA, U3))["estado"] == "desligada"
    assert _run(P.qr(mesa.banco, ALFA, U3))["qr"] is None
    assert _run(P.estado(mesa.banco, ALFA, U1))["estado"] == "nao_conectada"
    with pytest.raises(E.Recusa):                                    # quem não é da Alfa não pareia na Alfa
        _run(P.conectar(mesa.banco, ALFA, U3))
    # a pessoa das DUAS corretoras: a linha mora onde foi pareada (D-1310B2-02)
    _conectar_e_ler(mesa, ALFA, U2)
    with pytest.raises(E.Recusa, match="outra corretora"):
        _run(P.conectar(mesa.banco, BETA, U2))
    assert E.linha_do_dono(mesa.banco, BETA, U2) is None
    # desconectar pela corretora errada não derruba a linha certa
    assert _run(P.desconectar(mesa.banco, BETA, U2)) == {"ok": True, "estado": "nao_conectada"}
    assert _run(P.estado(mesa.banco, ALFA, U2))["estado"] == "conectada"


# =====================================================================================================================
# 6. o teto (limite) e a chave (desligada) — nenhum dos dois chama o Evolution
# =====================================================================================================================
def test_teto_cheio_vira_limite_sem_chamar_o_evolution(mesa, monkeypatch):
    monkeypatch.setenv("LINHA_DO_USUARIO_MAX_LINHAS", "1")
    _run(P.conectar(mesa.banco, ALFA, U1))
    antes = len(mesa.evo.pedidos)
    r = _run(P.conectar(mesa.banco, ALFA, U2))
    assert r["estado"] == "limite" and r["qr"] is None and r["motivo"] == E.FRASE_LIMITE
    assert len(mesa.evo.pedidos) == antes and CI.nome_da_instancia(ALFA, LINHA, dono=U2) not in mesa.evo.inst
    assert _run(P.estado(mesa.banco, ALFA, U2))["estado"] == "limite"
    # a vaga do PRÓPRIO dono não conta contra ele (reconectar/renovar não é linha nova)
    assert _run(P.conectar(mesa.banco, ALFA, U1))["estado"] == "aguardando_qr"
    # CONTROLE: com folga, o mesmo pedido passa
    monkeypatch.setenv("LINHA_DO_USUARIO_MAX_LINHAS", "2")
    assert _run(P.conectar(mesa.banco, ALFA, U2))["estado"] == "aguardando_qr"


def test_chave_ausente_recusa_sem_chamar_o_evolution(mesa, monkeypatch):
    monkeypatch.delenv("LINHA_DO_USUARIO_LIGADA")
    assert _run(P.conectar(mesa.banco, ALFA, U1))["estado"] == "desligada"
    assert _run(P.qr(mesa.banco, ALFA, U1))["estado"] == "desligada"
    assert _run(P.estado(mesa.banco, ALFA, U1)) == {"estado": "desligada", "numero_mascarado": None, "desde": None,
                                                     "motivo": None}
    assert mesa.evo.pedidos == [] and _linhas_da_linha(mesa.banco) == [] and mesa.redis.values == {}
    monkeypatch.setenv("LINHA_DO_USUARIO_LIGADA", "1")               # CONTROLE: ligada, o mesmo pedido chama
    assert _run(P.conectar(mesa.banco, ALFA, U1))["estado"] == "aguardando_qr" and mesa.evo.pedidos


# =====================================================================================================================
# 7. desconectar: a conectada e a PENDENTE (o "Cancelar" da tela)
# =====================================================================================================================
def test_desconectar_a_conectada_faz_logout_solta_e_nao_apaga(mesa):
    _conectar_e_ler(mesa, ALFA, U1)
    nome = CI.nome_da_instancia(ALFA, LINHA, dono=U1)
    id_antes = mesa.evo.inst[nome]["id"]
    assert _run(P.desconectar(mesa.banco, ALFA, U1)) == {"ok": True, "estado": "nao_conectada"}
    assert any(p[1] == "/instance/logout" for p in mesa.evo.pedidos)
    assert mesa.evo.inst[nome]["jid"] == "" and mesa.evo.inst[nome]["id"] != id_antes   # a sessão saiu do servidor
    (linha,) = _linhas_da_linha(mesa.banco, owner_user_id=U1)         # a linha CONTINUA no banco (histórico)
    assert linha["is_active"] is False and linha["linha_desconectada_em"]
    assert linha["linha_motivo"] == "desconectada_pelo_usuario" and linha["linha_conectada_em"]
    assert _run(P.estado(mesa.banco, ALFA, U1))["estado"] == "nao_conectada"
    # conectar de novo: a MESMA instância (mesmo nome), um QR novo
    r = _run(P.conectar(mesa.banco, ALFA, U1))
    assert r["estado"] == "aguardando_qr" and nome in r["qr"]
    assert len(_linhas_da_linha(mesa.banco, owner_user_id=U1)) == 1 and _linhas_da_linha(mesa.banco)[0]["is_active"]
    assert mesa.banco.linhas("integrations")[0] == mesa.obs_antes


def test_desconectar_a_tentativa_pendente_e_o_cancelar_da_tela(mesa):
    r = _run(P.conectar(mesa.banco, ALFA, U1))
    assert r["estado"] == "aguardando_qr"
    assert _run(P.desconectar(mesa.banco, ALFA, U1)) == {"ok": True, "estado": "nao_conectada"}
    assert _run(mesa.orq.tentativa_atual(ALFA, LINHA, owner_user_id=U1))["state"] == "cancelled"
    (linha,) = _linhas_da_linha(mesa.banco, owner_user_id=U1)
    assert linha["is_active"] is False and linha["linha_motivo"] == "cancelada_pelo_usuario"
    assert _run(P.estado(mesa.banco, ALFA, U1)) == {"estado": "nao_conectada", "numero_mascarado": None,
                                                     "desde": None, "motivo": "cancelada_pelo_usuario"}
    assert _run(P.qr(mesa.banco, ALFA, U1))["estado"] == "nao_conectada"
    # sem linha nenhuma: idempotente, sem erro
    assert _run(P.desconectar(mesa.banco, ALFA, U2)) == {"ok": True, "estado": "nao_conectada"}
    # e o botão volta a funcionar
    assert _run(P.conectar(mesa.banco, ALFA, U1))["estado"] == "aguardando_qr"


# =====================================================================================================================
# 8. o evento do provedor: desconectada com a data DA DESCONEXÃO · evento só com LID
# =====================================================================================================================
def test_a_desconexao_do_provedor_mostra_a_data_da_desconexao(mesa):
    _conectar_e_ler(mesa, ALFA, U1)
    (linha,) = _linhas_da_linha(mesa.banco, owner_user_id=U1)
    conectada_em = linha["linha_conectada_em"]
    assert E.registrar_desconexao(mesa.banco, linha, "LoggedOut")["definitiva"] is True
    (linha,) = _linhas_da_linha(mesa.banco, owner_user_id=U1)
    e = _run(P.estado(mesa.banco, ALFA, U1))
    assert e["estado"] == "desconectada" and e["desde"] == linha["linha_desconectada_em"] != conectada_em
    assert e["motivo"] == "loggedout" and e["numero_mascarado"] == "5511*****001"
    # idempotente: a 2ª notícia não reescreve a data da 1ª
    assert E.registrar_desconexao(mesa.banco, linha, "loggedout") == {"ok": True, "ja_estava": True}
    # e um evento de conexão não ressuscita a linha que caiu (só o botão Conectar)
    assert E.registrar_conexao(mesa.banco, linha, {"data": {"jid": TEL[U1] + "@s.whatsapp.net"}})["ok"] is False


def test_evento_do_provedor_no_meio_do_qr_nao_derruba_a_tentativa(mesa):
    _run(P.conectar(mesa.banco, ALFA, U1))
    (linha,) = _linhas_da_linha(mesa.banco, owner_user_id=U1)
    assert E.registrar_desconexao(mesa.banco, linha, "re_pair_required") == {"ok": True,
                                                                             "ignorado": "pareamento_em_andamento"}
    assert _linhas_da_linha(mesa.banco, owner_user_id=U1)[0]["is_active"] is True


def test_evento_so_com_lid_casa_a_linha_certa(mesa):
    _run(P.conectar(mesa.banco, ALFA, U1))
    (linha,) = _linhas_da_linha(mesa.banco, owner_user_id=U1)
    r = E.registrar_conexao(mesa.banco, linha, {"event": "Connected", "data": {"ID": "123456789012345@lid"}})
    assert r["ok"] is True and r["lid"] is True and r["jid"] is False
    li = E.linha_da_instancia(mesa.banco, linha["instance_id"])
    assert li["lid"] == "123456789012345@lid" and li["owner_user_id"] == U1 and li["jid"] is None
    # a linha de OUTRA corretora com o mesmo id não é tocada: o filtro é id + corretora + dono
    falsa = dict(linha, company_id=BETA)
    assert E.registrar_conexao(mesa.banco, falsa, {"data": {"lid": "1@lid"}})["ok"] is False


# =====================================================================================================================
# 9. 🧪 LINHA DE CONTROLE — os purposes de antes, com nome, escopo, chave e corpo IGUAIS
# =====================================================================================================================
@pytest.mark.parametrize("purpose,escopo,canonico,nome", [
    ("observer", "corretora", "observer", "ab-obs-04b5cdbc04-1"),
    ("attendance", "corretora", "observer", "ab-obs-04b5cdbc04-1"),
    ("dispatch", "corretora", "observer", "ab-obs-04b5cdbc04-1"),
    ("auxiliary:cobranca", "auxiliary:cobranca", "auxiliary:cobranca", "ab-aux-04b5cdbc04-cobranca"),
    ("assistente", "plataforma:assistente", "assistente", "ab-ast-04b5cdbc04"),
    ("qualquer_coisa", "corretora", "observer", "ab-obs-04b5cdbc04-1"),
])
def test_controle_os_purposes_antigos_nao_mudam(purpose, escopo, canonico, nome):
    empresa = "04b5cdbc-04cd-0000-0000-000000000000"
    assert CI.escopo_de(purpose) == escopo and CI.purpose_canonico(purpose) == canonico
    assert CI.nome_da_instancia(empresa, purpose) == nome
    assert CI.nome_da_instancia(empresa, purpose, dono=U1) == nome       # o dono é IGNORADO fora da linha
    assert PO.PairingOrchestrator._dono(canonico, U1) is None
    assert PO.PairingOrchestrator._escopo_da_chave(canonico, None) == canonico
    from app.services.whatsapp.channel_security import corpo_do_connect

    url = f"{PUBLICO}/api/v1/webhook/evolution-go/tok"
    assert PO.PairingOrchestrator._corpo_do_connect(url, canonico) == corpo_do_connect(url)   # com HISTORY_SYNC


def test_controle_o_pareamento_do_numero_da_corretora_segue_igual(mesa):
    mesa.banco.dados["integrations"] = []                            # a Alfa ainda sem número pareado
    st = _run(mesa.orq.start(ALFA, "observer"))
    nome = CI.nome_da_instancia(ALFA, "observer")
    assert st["state"] == "qr_ready" and nome in st["qr_base64"]
    assert f"whatsapp:pairing:{ALFA}:observer" in mesa.redis.values           # a chave de SEMPRE, sem dono
    (connect,) = mesa.evo.connects(nome)
    assert "HISTORY_SYNC" in connect[2]["subscribe"]                         # o canal da corretora pede o histórico
    (linha,) = mesa.banco.linhas("integrations")
    assert linha["purpose"] == "observer" and "owner_user_id" not in linha
    assert linha["alert_target"]["observer_scope"] == "insurers_and_clients"


# =====================================================================================================================
# 10. a API: a chave interna e a própria pessoa
# =====================================================================================================================
@pytest.fixture
def api(mesa, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import app.api.linha_do_usuario as API

    monkeypatch.setattr(API, "_db", lambda: mesa.banco)
    app = FastAPI()
    app.include_router(API.router)
    return TestClient(app)


def test_a_api_exige_a_chave_interna(api):
    corpo = {"company_id": ALFA, "user_id": U1, "por_user_id": U1}
    q = {"company_id": ALFA, "user_id": U1}
    assert api.post("/api/linha-do-usuario/conectar", json=corpo).status_code == 401
    assert api.post("/api/linha-do-usuario/desconectar", json=corpo).status_code == 401
    assert api.get("/api/linha-do-usuario/estado", params=q).status_code == 401
    assert api.get("/api/linha-do-usuario/qr", params=q).status_code == 401
    errada = {"X-AutoBrokers-Internal-Key": "outra"}
    assert api.get("/api/linha-do-usuario/estado", params=q, headers=errada).status_code == 401
    # CONTROLE: com a chave, responde
    ok = api.get("/api/linha-do-usuario/estado", params=q, headers={"X-AutoBrokers-Internal-Key": CHAVE_INTERNA})
    assert ok.status_code == 200 and ok.json()["estado"] == "nao_conectada"


def test_a_api_recusa_por_user_id_diferente_e_le_o_corpo_do_limite(api, mesa, monkeypatch):
    h = {"X-AutoBrokers-Internal-Key": CHAVE_INTERNA}
    for rota in ("conectar", "desconectar"):
        for por in (U2, None):
            r = api.post(f"/api/linha-do-usuario/{rota}", headers=h,
                         json={"company_id": ALFA, "user_id": U1, "por_user_id": por})
            assert r.status_code == 422, (rota, por)
    assert mesa.evo.pedidos == []
    r = api.post("/api/linha-do-usuario/conectar", headers=h, json={"company_id": ALFA, "user_id": U1, "por_user_id": U1})
    assert r.status_code == 200 and r.json()["estado"] == "aguardando_qr" and r.json()["qr"]
    q = api.get("/api/linha-do-usuario/qr", headers=h, params={"company_id": ALFA, "user_id": U1})
    assert q.status_code == 200 and q.json()["qr"] == r.json()["qr"]
    monkeypatch.setenv("LINHA_DO_USUARIO_MAX_LINHAS", "1")
    cheio = api.post("/api/linha-do-usuario/conectar", headers=h,
                     json={"company_id": ALFA, "user_id": U2, "por_user_id": U2})
    assert cheio.status_code == 409 and cheio.json()["estado"] == "limite"
    monkeypatch.delenv("LINHA_DO_USUARIO_LIGADA")
    d = api.get("/api/linha-do-usuario/estado", headers=h, params={"company_id": ALFA, "user_id": U1})
    assert d.status_code == 200 and d.json()["estado"] == "desligada"
    fora = api.post("/api/linha-do-usuario/desconectar", headers=h,
                    json={"company_id": ALFA, "user_id": U1, "por_user_id": U1})
    assert fora.status_code == 200 and fora.json()["estado"] == "nao_conectada"   # sair funciona desligado


def test_o_router_esta_registrado_no_main():
    fonte = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
    assert "from app.api.linha_do_usuario import router as linha_do_usuario_router" in fonte
    assert fonte.count("app.include_router(linha_do_usuario_router)") == 1


# =====================================================================================================================
# as MUTAÇÕES (por cópia) — `python tests/test_spec1310b2_pareamento.py --mutar`
# =====================================================================================================================
MUTACOES = [
    ("M5 o 2º corretor recebe o QR do 1º (a chave da tentativa sem o dono)",
     "app/services/whatsapp/pairing_orchestrator.py",
     "        return f\"{purpose}:{dono}\" if dono else purpose\n",
     "        return purpose\n",
     "test_o_segundo_corretor_nunca_recebe_o_qr_do_primeiro"),
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
            print(f"{rotulo}: {'VERMELHO (o guarda pegou)' if vermelho else 'MUTACAO NAO PEGOU'} — {teste}")
            print("\n".join(l for l in r.stdout.splitlines() if "assert" in l.lower() or "passed" in l
                            or "failed" in l)[-1500:])
            falhas += 0 if vermelho else 1
        finally:
            caminho.write_bytes(bruto)                          # 🔴 restaura POR CÓPIA DOS BYTES
            assert caminho.read_bytes() == bruto, f"{rotulo}: {arquivo} não voltou igual"
    return falhas


if __name__ == "__main__" and "--mutar" in sys.argv:
    sys.exit(_mutar())

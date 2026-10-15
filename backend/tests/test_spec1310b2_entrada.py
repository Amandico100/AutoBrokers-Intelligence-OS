# -*- coding: utf-8 -*-
"""SPEC-131-0-B2 · L2 — A ENTRADA DA LINHA DO USUÁRIO, pelo MOTOR real.

    POST /api/v1/webhook/evolution-go/{token}   ROTA REAL (`app.api.webhook.router`), token pelo hash REAL
      → o hunk da linha (purpose='linha_do_usuario') → `linha_do_usuario.entrada.desviar` REAL
      → o portão da privacidade (`filtrar`): só a conversa consigo mesmo, fromMe, que não é eco
      → `turno_da_linha` → `atalho.turno.rodar` REAL (origem linha_do_usuario) → POST /chat/stream REAL (o grafo é o
        dublê da borda, o MESMO arreio da 132-C) → `enviar_pela_linha` → `atalho.envio.enviar` REAL (a exceção exata)
      → whatsapp_service.send_message (DUBLÊ: captura)
    + a conexão (`registrar_conexao` REAL) → as boas-vindas (`boas_vindas` REAL), uma vez.

O mundo é o da C2 da 132-C (`test_spec132c_o_atalho`: banco em memória, Redis falso, rede FECHADA) — importado, não
copiado — com DUAS linhas do usuário: a de U1 na Alfa e a de U2 (membro da Alfa E da Beta) na Beta.

A régua (SPEC §6): (1) outra conversa → 0 bytes em messages/Storage/log, 0 turnos, só +1 em descartadas_total ·
(2) a resposta do sistema voltando (com e sem id) não vira pergunta · (3) a linha de A nunca responde dado de B ·
(4) QCM e atendimento intactos · (5) chave ausente → nada responde · (6) boas-vindas uma vez · (7) LID · (8) a saída
para OUTRO número do produto continua recusada.
Mutações: `python tests/test_spec1310b2_entrada.py --mutar` (por CÓPIA dos bytes; exige VERMELHO; restaura).
⛔ Dados fictícios (5511900000001 e afins; "Corretora Alfa"). Nenhum nome de corretora real (CLAUDE.md §13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec1310b2_entrada.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec132c_o_atalho as C2  # noqa: E402  (o mundo, o arreio e a fixture `fio` da C2)
from test_spec132c_o_atalho import fio  # noqa: E402,F401  (a fixture)
from app.services.atalho import envio as AENV  # noqa: E402
from app.services.atalho import turno as T  # noqa: E402
from app.services.linha_do_usuario import boas_vindas as BV  # noqa: E402
from app.services.linha_do_usuario import entrada as ENT  # noqa: E402
from app.services.linha_do_usuario import estado as EST  # noqa: E402

ALFA, BETA, U1, U2 = C2.ALFA, C2.BETA, C2.U1, C2.U2
NUM_A = "+5511900000001"          # 💭 fictício — a conta de U1, conectada como linha na Alfa
NUM_B = "+5521900000002"          # 💭 fictício — a conta de U2, conectada como linha na Beta
JID_A, JID_B = "5511900000001@s.whatsapp.net", "5521900000002@s.whatsapp.net"
LID_A = "190000000000001@lid"     # 💭 fictício (opaco)
LID_B_NOVO = "290000000000002@lid"
OUTRO_JID = "5511900000099@s.whatsapp.net"   # 💭 um cliente do corretor
TOKEN_A = "tok-linha-a-1310b2-" + "a" * 40
TOKEN_B = "tok-linha-b-1310b2-" + "b" * 40
SEGREDO = "conteudo-sigiloso-da-outra-conversa"

#: o texto da SPEC §4, com os nomes do banco (Ana, Corretora Alfa) e a lista inteira menos "O seu dia" (a Alfa não tem
#: o aplicativo de Renovação no mundo de teste)
BOAS_VINDAS_DA_ALFA = (
    "▸ AutoBrokers\n"
    "Oi, Ana! Pronto: esta conversa com você mesmo agora é o seu canal direto com o AutoBrokers da Corretora Alfa.\n"
    "\n"
    "É só escrever aqui, como escreveria para um colega. Você pode pedir:\n"
    "• *Cotação* — mande a placa, a foto do documento, a apólice atual em PDF ou um áudio contando o que o cliente "
    "quer.\n"
    "• *Dúvidas de seguro* — \"a apólice do João cobre vidro?\", \"o que muda se ele tirar o carro reserva?\"\n"
    "• *Ler um documento* — mande a foto ou o PDF e peça o resumo.\n"
    "• *Números da corretora* — \"como está a produção do mês?\"\n"
    "\n"
    "Uma resposta leva alguns segundos; uma cotação, de 1 a 2 minutos, e chega aqui mesmo.\n"
    "\n"
    "Combinados:\n"
    "• Eu só leio ESTA conversa. As suas outras conversas não são lidas nem guardadas.\n"
    "• Eu não mando nada para os seus clientes: quem envia é sempre você.\n"
    "• O que começa com ▸ AutoBrokers sou eu; o resto é você.\n"
    "• Para desligar: Meu perfil → Meu WhatsApp → Desconectar (ou Aparelhos conectados, no celular)."
)


def _linha(iid, cid, uid, numero, jid, lid, token, inst):
    return {"id": iid, "company_id": cid, "owner_user_id": uid, "provider": "evolution-go",
            "purpose": "linha_do_usuario", "is_active": True, "channel_status": "connected", "instance_id": inst,
            "identifier": inst, "base_url": "http://evolution.invalid", "paired_phone_e164": numero,
            "paired_jid": jid, "linha_jid": jid, "linha_lid": lid, "linha_conectada_em": "2026-10-15T10:00:00+00:00",
            "linha_desconectada_em": None, "linha_motivo": None, "descartadas_total": 0,
            "created_at": "2026-10-15T09:00:00+00:00", "webhook_token_hash": C2._hash(token)}


@pytest.fixture
def lu(fio, monkeypatch):
    import app.agents.capability_resolver as CR
    import app.services.whatsapp.integration_secrets as SEG

    monkeypatch.setenv("LINHA_DO_USUARIO_LIGADA", "1")
    monkeypatch.setattr(SEG, "decrypt_integration_secret", lambda v, **_k: v)
    monkeypatch.setattr(ENT, "DESCARREGAR_A_CADA", 1)            # o contador desce ao banco a cada descarte
    ENT._DESCARTADAS.clear()
    # o Capability Registry na borda: só a Alfa tem a Cotação Rápida ligada
    monkeypatch.setattr(CR, "resolve_active_capabilities", lambda _db, cid, _role: (
        {BV.CAPABILITY_DA_COTACAO: {"status": "active"}} if str(cid) == ALFA else {}))
    b = fio.banco
    b.linhas("integrations").extend([
        _linha("int-linha-a", ALFA, U1, NUM_A, JID_A, LID_A, TOKEN_A, "ab-lu-a"),
        _linha("int-linha-b", BETA, U2, NUM_B, JID_B, None, TOKEN_B, "ab-lu-b"),
    ])
    for p in b.linhas("users_v2"):
        if p["id"] == U1:
            p["first_name"], p["last_name"] = "Ana", "Teste"
        if p["id"] == U2:
            p["first_name"], p["last_name"] = "Bia", "Teste"
    b.dados.setdefault("linha_mensagens_do_sistema", [])
    turnos = []
    original = ENT.turno_da_linha

    async def _espiao(*a, **k):
        turnos.append(1)
        return await original(*a, **k)

    monkeypatch.setattr(ENT, "turno_da_linha", _espiao)
    seq = {"n": 0}

    def postar(texto="oi", *, token=TOKEN_A, chat=JID_A, from_me=True, chat_alt=None, mid=None, grupo=False,
               evento="Message"):
        seq["n"] += 1
        info = {"Chat": chat, "Sender": chat, "IsFromMe": from_me, "IsGroup": grupo,
                "ID": f"3EB0LU{seq['n']:016d}" if mid is None else mid, "PushName": "Pessoa",
                "Timestamp": "2026-10-15T12:00:00Z", "Type": "text"}
        if chat_alt:
            info["ChatAlt"] = chat_alt
        corpo = {"event": evento, "instanceId": "x", "data": {"Info": info, "Message": {"conversation": texto}}}
        st, r = fio.postar_cru(corpo, token=token)
        assert st == 200, r
        return r

    def evento(corpo, *, token=TOKEN_A):
        st, r = fio.postar_cru(corpo, token=token)
        assert st == 200, r
        return r

    def da_linha(iid):
        return [e for e in fio.envio.enviados if e["integracao"] == iid]

    def linha(iid):
        return next(x for x in b.linhas("integrations") if x["id"] == iid)

    return type("LU", (), {"fio": fio, "banco": b, "postar": staticmethod(postar), "evento": staticmethod(evento),
                           "turnos": turnos, "da_linha": staticmethod(da_linha), "linha": staticmethod(linha)})


# =====================================================================================================================
# (1) mutação 1 — OUTRA conversa: 0 bytes gravados, 0 turnos, 0 log de conteúdo; só +1 no contador
# =====================================================================================================================
def test_mensagem_de_outra_conversa_e_descartada_antes_de_tudo(lu, monkeypatch, caplog):
    import app.services.whatsapp.evolution_inbound as EI

    normalizadas = []
    original = EI.normalize_evolution_inbound
    monkeypatch.setattr(EI, "normalize_evolution_inbound", lambda env: normalizadas.append(1) or original(env))
    caplog.set_level(logging.DEBUG)
    escritas_antes = len(lu.banco.escritas)

    casos = [
        dict(chat=OUTRO_JID, from_me=False),                       # um cliente escreve para o corretor
        dict(chat=OUTRO_JID, from_me=True),                        # o corretor escreve para um cliente
        dict(chat="120363000000000001@g.us", from_me=True, grupo=True),
        dict(chat="status@broadcast", from_me=True),
        dict(chat="120363000000000002@newsletter", from_me=False),
        dict(chat="390000000000003@lid", from_me=True),            # outra pessoa, endereçada por LID
        dict(chat=JID_B, from_me=True),                            # a conta da OUTRA linha, no evento da linha A
    ]
    for c in casos:
        r = lu.postar(SEGREDO, **c)
        assert r["status"] == "ignored" and r["reason"] in ("linha_outra_conversa", "linha_grupo_ou_status"), r
    r = lu.evento({"event": "HistorySync", "data": {"conversations": [{"id": OUTRO_JID, "messages": [SEGREDO]}]}})
    assert r == {"status": "ignored", "reason": "linha_history_sync"}

    # 0 bytes: nada em messages/conversations/Storage, nenhum turno, nenhum envio, nem passou pelo normalizador
    assert lu.banco.linhas("messages") == [] and lu.banco.linhas("conversations") == []
    assert lu.banco.arquivos == [] and lu.turnos == [] and lu.fio.grafo == [] and lu.fio.envio.enviados == []
    assert normalizadas == []
    # a ÚNICA escrita: o contador da linha A (só o número)
    escritas = lu.banco.escritas[escritas_antes:]
    assert {(t, op) for t, op, _ in escritas} == {("integrations", "update")}
    assert all(row["id"] == "int-linha-a" for _, _, row in escritas)
    assert lu.linha("int-linha-a")["descartadas_total"] == len(casos) + 1
    assert lu.linha("int-linha-b")["descartadas_total"] == 0
    # o log: nem o conteúdo, nem o número, nem o JID/LID de ninguém
    logs = "\n".join(r.getMessage() for r in caplog.records)
    for proibido in (SEGREDO, "5511900000099", "120363000000000001", "390000000000003", "5521900000002", "@lid",
                     "@s.whatsapp.net", "@g.us", "newsletter", "broadcast"):
        assert proibido not in logs, proibido
    # CONTROLE: a conversa consigo mesmo PASSA (o portão consegue dizer sim)
    assert lu.postar("quanto fica o seguro do meu cliente?")["status"] == "accepted"
    assert lu.turnos == [1] and len(lu.fio.grafo) == 1


# =====================================================================================================================
# (2) mutação 2 — a resposta do sistema voltando NÃO vira pergunta (prefixo · hash · id)
# =====================================================================================================================
def test_a_resposta_do_sistema_voltando_nao_vira_pergunta(lu):
    assert lu.postar("quanto fica o seguro do meu cliente?")["status"] == "accepted"
    (resposta,) = lu.da_linha("int-linha-a")
    assert resposta["para"] == "5511900000001" and resposta["texto"].startswith("▸ AutoBrokers\n")
    grafo, n_msgs = len(lu.fio.grafo), len(lu.banco.linhas("messages"))

    # o eco exato COM id novo e SEM id — calado
    assert lu.postar(resposta["texto"])["reason"] == "linha_eco_prefixo"
    assert lu.postar(resposta["texto"], mid="")["reason"] == "linha_eco_prefixo"
    # só a camada do PREFIXO pega isto (nunca foi enviado: nenhum hash gravado)
    assert lu.postar("▸ AutoBrokers\nqualquer coisa que o sistema diria", mid="")["reason"] == "linha_eco_prefixo"
    # só a camada do HASH: a 2ª metade do reenvio do whatsapp_service volta SEM o prefixo
    longo = "\n".join(f"linha {i} da resposta longa do assistente" for i in range(30))
    asyncio.run(ENT.enviar_pela_linha(lu.banco, EST.linha_do_dono(lu.banco, ALFA, U1), longo))
    enviado = lu.da_linha("int-linha-a")[-1]["texto"]
    segunda_metade = ENT._metades_do_reenvio(enviado)[1]
    assert not segunda_metade.startswith("▸")
    assert lu.postar(segunda_metade, mid="")["reason"] == "linha_eco_hash"
    # só a camada do ID: o provedor devolveu o id do envio (M6) e ele volta com outro texto
    lu.banco.linhas("linha_mensagens_do_sistema").append({
        "id": "x1", "integration_id": "int-linha-a", "company_id": ALFA, "message_id": "3EB0SISTEMA0001",
        "hash_texto": "0" * 64, "enviada_em": "2026-10-15T00:00:00+00:00"})
    assert lu.postar("texto que nunca foi enviado", mid="3EB0SISTEMA0001")["reason"] == "linha_eco_id"
    assert len(lu.fio.grafo) == grafo and len(lu.banco.linhas("messages")) == n_msgs
    # o banco não respondeu na checagem do eco → CALA (falha fechada)
    original = lu.banco.table

    def _quebrado(nome):
        if nome == "linha_mensagens_do_sistema":
            raise RuntimeError("banco fora")
        return original(nome)

    lu.banco.table = _quebrado
    try:
        assert lu.postar("pergunta legitima com o banco fora")["reason"] == "linha_eco_nao_conferido"
    finally:
        lu.banco.table = original
    assert len(lu.fio.grafo) == grafo
    # CONTROLE: uma pergunta nova de verdade passa
    assert lu.postar("e o prazo de vigência?")["status"] == "accepted" and len(lu.fio.grafo) == grafo + 1


def test_o_hash_e_gravado_antes_do_envio_e_nunca_o_texto(lu, monkeypatch):
    vistos = []
    original = lu.fio.envio.send_message

    def _espiao(to_number=None, text=None, integration=None, **k):
        vistos.append(len(lu.banco.linhas("linha_mensagens_do_sistema")))     # já gravado quando o envio começa
        return original(to_number, text, integration, **k)

    monkeypatch.setattr(lu.fio.envio, "send_message", _espiao)
    r = asyncio.run(ENT.enviar_pela_linha(lu.banco, EST.linha_do_dono(lu.banco, ALFA, U1), "**oi** do sistema"))
    assert r == {"enviadas": 1, "ids": []} and vistos == [1]
    (row,) = lu.banco.linhas("linha_mensagens_do_sistema")
    assert row["hash_texto"] == ENT._sha("▸ AutoBrokers\n*oi* do sistema") and len(row["hash_texto"]) == 64
    assert "oi" not in str(row) and row["company_id"] == ALFA and row["integration_id"] == "int-linha-a"


# =====================================================================================================================
# (3) mutação 3 — a linha de A nunca responde dado de B (duas corretoras; U2 é membro das duas, a linha mora na Beta)
# =====================================================================================================================
def test_cada_linha_roda_o_turno_na_corretora_e_no_dono_dela(lu):
    lu.postar("como está a produção do mês?", token=TOKEN_B, chat=JID_B)
    lu.postar("como está a produção do mês?", token=TOKEN_A, chat=JID_A)
    assert [(g["company_id"], g["user_id"]) for g in lu.fio.grafo] == [(BETA, U2), (ALFA, U1)]
    conv_b = C2._conversas(lu.banco, user_id=U2)
    assert {c["company_id"] for c in conv_b} == {BETA}                 # nenhuma conversa de U2 na Alfa
    assert all(c["channel"] == T.CANAL_DO_ATALHO for c in lu.banco.linhas("conversations"))
    perguntas = [m for m in lu.banco.linhas("messages") if m["role"] == "user"]
    assert {m["payload"]["origem"] for m in perguntas} == {T.ORIGEM_DA_LINHA}
    # cada resposta saiu pela PRÓPRIA linha, à PRÓPRIA conta — nunca a de B pela A, nem pelo assistente
    assert [(e["integracao"], e["para"]) for e in lu.fio.envio.enviados] == [
        ("int-linha-b", "5521900000002"), ("int-linha-a", "5511900000001")]
    # o membro de duas corretoras NÃO recebe "qual corretora?" (D-1310B2-02: a linha mora numa)
    assert not any("qual corretora" in e["texto"] for e in lu.fio.envio.enviados)
    # a mensagem da conta de B chegando pelo token de A não roda nada
    n = len(lu.fio.grafo)
    assert lu.postar("me passa os dados da Beta", token=TOKEN_A, chat=JID_B)["reason"] == "linha_outra_conversa"
    assert len(lu.fio.grafo) == n


def test_a_volta_da_cotacao_sai_pela_mesma_linha(lu):
    lu.postar("cota o carro do cliente")
    (conv,) = C2._conversas(lu.banco, company_id=ALFA, user_id=U1)
    n = len(lu.fio.envio.enviados)
    assert asyncio.run(AENV.avisar_pelo_atalho_se_for_o_caso(
        lu.banco, company_id=ALFA, conversation_id=conv["id"], texto_markdown="**Pronto:** 3 seguradoras.")) is True
    (volta,) = lu.fio.envio.enviados[n:]
    assert volta["integracao"] == "int-linha-a" and volta["para"] == "5511900000001"
    assert volta["texto"] == "▸ AutoBrokers\n*Pronto:* 3 seguradoras."
    # pedida por OUTRA corretora → nada sai
    assert asyncio.run(AENV.avisar_pelo_atalho_se_for_o_caso(
        lu.banco, company_id=BETA, conversation_id=conv["id"], texto_markdown="x")) is False
    assert len(lu.fio.envio.enviados) == n + 1


# =====================================================================================================================
# (4) mutação 4 — QCM e atendimento intactos (o evento deles não toca a linha; o da linha não toca eles)
# =====================================================================================================================
def test_qcm_e_atendimento_nao_tocam_a_linha_nem_ela_eles(lu):
    lu.postar("oi", token=TOKEN_A)
    lu.postar(SEGREDO, token=TOKEN_A, chat=OUTRO_JID)
    assert lu.fio.taps == [] and lu.fio.pipeline == []                # nada da linha chegou ao observer/pipeline
    antes = (lu.linha("int-linha-a")["descartadas_total"], len(lu.da_linha("int-linha-a")))
    # o MESMO evento (fromMe na conversa consigo mesmo) no QCM e no atendimento: o caminho de sempre
    C2_cel = C2.CEL_1.lstrip("+") + "@s.whatsapp.net"
    lu.postar("quanto fica o seguro?", token=C2.TOKEN_QCM, chat=C2_cel, from_me=False)
    lu.postar("quanto fica o seguro?", token=C2.TOKEN_ALFA, chat=C2_cel, from_me=False)
    assert lu.fio.pipeline == ["int-qcm"] and lu.fio.taps == ["int-alfa"]
    assert (lu.linha("int-linha-a")["descartadas_total"], len(lu.da_linha("int-linha-a"))) == antes


# =====================================================================================================================
# (5) a chave ausente → nada responde (nem boas-vindas, nem turno, nem saída direta)
# =====================================================================================================================
def test_chave_ausente_nada_responde(lu, monkeypatch):
    monkeypatch.delenv("LINHA_DO_USUARIO_LIGADA", raising=False)
    escritas = len(lu.banco.escritas)
    assert lu.postar("oi")["reason"] == "linha_desligada"
    assert lu.evento({"event": "Connected", "data": {}})["reason"] == "linha_desligada"
    r = asyncio.run(ENT.enviar_pela_linha(lu.banco, EST.linha_do_dono(lu.banco, ALFA, U1), "oi"))
    assert r["enviadas"] == 0 and r["motivo"] == "desligada"
    assert lu.fio.envio.enviados == [] and lu.fio.grafo == [] and lu.banco.escritas[escritas:] == []
    assert lu.fio.taps == [] and lu.fio.pipeline == []                # e não caiu no resto do webhook


def test_linha_sem_dono_inativa_ou_membro_inativo_falha_fechado(lu):
    lu.linha("int-linha-a")["owner_user_id"] = None
    assert lu.postar("oi")["reason"] == "linha_nao_confirmada"
    lu.linha("int-linha-a")["owner_user_id"] = U1
    for m in lu.banco.linhas("company_members"):
        if m["company_id"] == ALFA and m["user_id"] == U1:
            m["status"] = "inactive"
    assert lu.postar("oi")["reason"] == "linha_nao_confirmada"
    assert lu.fio.envio.enviados == [] and lu.fio.taps == [] and lu.fio.pipeline == []


# =====================================================================================================================
# (6) as boas-vindas: uma vez, com o prefixo, à própria conta, os nomes do banco, só o que está ligado
# =====================================================================================================================
def test_boas_vindas_uma_vez_a_propria_conta_com_os_nomes_do_banco(lu):
    assert lu.evento({"event": "Connected", "data": {}}) == {"status": "ok", "event": "linha_conexao"}
    (bv,) = lu.da_linha("int-linha-a")
    assert bv["para"] == "5511900000001" and bv["bloco_unico"]
    assert bv["texto"] == BOAS_VINDAS_DA_ALFA
    # reconectar (de novo Connected, e PairSuccess) não repete
    lu.evento({"event": "Connected", "data": {}})
    lu.evento({"event": "PairSuccess", "data": {"ID": JID_A}})
    assert len(lu.da_linha("int-linha-a")) == 1
    # o eco das boas-vindas não vira pergunta
    assert lu.postar(bv["texto"], mid="")["reason"] == "linha_eco_prefixo" and lu.fio.grafo == []
    # a Beta: o nome dela e a lista SEM a Cotação (o Registry não a liga para a Beta)
    lu.evento({"event": "Connected", "data": {}}, token=TOKEN_B)
    (bv_b,) = lu.da_linha("int-linha-b")
    assert bv_b["para"] == "5521900000002" and "Oi, Bia!" in bv_b["texto"]
    assert "AutoBrokers da Corretora Beta." in bv_b["texto"] and "*Cotação*" not in bv_b["texto"]
    assert "*Dúvidas de seguro*" in bv_b["texto"] and "Corretora Alfa" not in bv_b["texto"]


def test_qr_e_qrtimeout_sao_ignorados_e_nao_derrubam_a_linha(lu):
    assert lu.evento({"event": "QRCode", "data": {"code": "x", "count": 1, "maxCount": 5, "qrcode": "data:x"}}) == {
        "status": "ignored", "reason": "linha_qr"}
    assert lu.evento({"event": "QRTimeout", "data": {"errorCode": "qr_expired", "forceLogout": True}})[
        "reason"] == "linha_qr"
    assert lu.linha("int-linha-a")["is_active"] is True and lu.linha("int-linha-a")["channel_status"] == "connected"
    # CONTROLE: o LoggedOut derruba (motivo definitivo)
    assert lu.evento({"event": "LoggedOut", "data": {}}) == {"status": "ok", "event": "linha_desconexao"}
    assert lu.linha("int-linha-a")["is_active"] is False and lu.linha("int-linha-a")["linha_motivo"] == "re_pair_required"


# =====================================================================================================================
# (7) o evento só com LID casa a linha certa
# =====================================================================================================================
def test_evento_so_com_lid_casa_a_linha_certa(lu):
    assert lu.postar("oi pelo lid", chat=LID_A)["status"] == "accepted"
    assert [(g["company_id"], g["user_id"]) for g in lu.fio.grafo] == [(ALFA, U1)]
    assert lu.fio.envio.enviados[-1]["para"] == "5511900000001"
    # o LID de A no evento da linha B (que ainda não conhece o próprio LID): não é a conta de B
    assert lu.postar("x", token=TOKEN_B, chat=LID_A)["reason"] == "linha_outra_conversa"
    # um LID novo, confirmado pelo JID alternativo da PRÓPRIA conta: passa, e a linha aprende o LID
    assert lu.postar("oi", token=TOKEN_B, chat=LID_B_NOVO, chat_alt=JID_B)["status"] == "accepted"
    assert lu.linha("int-linha-b")["linha_lid"] == LID_B_NOVO
    # LID conhecido e DIFERENTE, mesmo com o alternativo dizendo que é a própria conta: contradição → fecha
    assert lu.postar("x", chat="390000000000003@lid", chat_alt=JID_A)["reason"] == "linha_outra_conversa"


# =====================================================================================================================
# (8) controle da exceção: a saída para OUTRO número do produto continua recusada
# =====================================================================================================================
def test_a_excecao_do_anti_laco_e_exata(lu):
    from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

    integ_a = prepare_integration_for_runtime(dict(lu.linha("int-linha-a")))
    enviar = lambda integ, tel: asyncio.run(AENV.enviar(integ, tel, ["teste"], db=lu.banco))  # noqa: E731
    assert enviar(integ_a, NUM_B) == 0                          # a OUTRA linha do usuário (produto)
    assert enviar(integ_a, "+" + C2.ASSISTENTE) == 0            # o número do assistente (produto)
    assert enviar(integ_a, C2.CEL_LINHA_ALFA) == 0              # a linha de atendimento da Alfa (produto)
    assert enviar(integ_a, C2.CEL_1) == 0                       # uma PESSOA: nada vai a cliente na fase 1
    assert enviar({**integ_a, "owner_user_id": U2}, NUM_A) == 0  # a integração com outro dono
    assert enviar(integ_a, NUM_A) == 1                          # CONTROLE: a própria conta passa
    # SPEC-131-0-B2 (conserto B3, a verdade mudou — CLAUDE.md §9.3): conectar a linha NÃO cala ninguém. O número de
    # uma linha do usuário continua sendo de uma PESSOA para o central (sem laço: na instância da linha, a conversa com
    # o central é ALHEIA → `outra_conversa`, `test_spec1310b2_a_linha_nao_vaza`). CONTROLE: o anti-laço do central
    # segue recusando a linha de ATENDIMENTO da corretora (instância do produto).
    assistente = AENV.integracao_do_assistente(lu.banco)
    assert enviar(assistente, C2.CEL_LINHA_ALFA) == 0
    assert enviar(assistente, NUM_A) == 1
    enviados = [(e["integracao"], e["para"]) for e in lu.fio.envio.enviados]
    assert enviados[0] == ("int-linha-a", "5511900000001")
    assert len(enviados) == 2 and enviados[1][1] == "5511900000001" and enviados[1][0] != "int-linha-a"


# =====================================================================================================================
# as MUTAÇÕES (por cópia) — `python tests/test_spec1310b2_entrada.py --mutar`
# =====================================================================================================================
MUTACOES = [
    ("M1 a mensagem de OUTRA conversa chega ao turno", "app/services/linha_do_usuario/entrada.py",
     "    if not _conversa_consigo_mesmo(linha, chave):\n        return None, \"outra_conversa\"\n",
     "    if False:\n        return None, \"outra_conversa\"\n",
     "test_mensagem_de_outra_conversa_e_descartada_antes_de_tudo"),
    ("M2 a mensagem do sistema volta como pergunta (o prefixo)", "app/services/linha_do_usuario/entrada.py",
     "    if texto.lstrip().startswith(PREFIXO) or legenda.lstrip().startswith(PREFIXO):\n",
     "    if False:\n",
     "test_a_resposta_do_sistema_voltando_nao_vira_pergunta"),
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
            ultima = (r.stdout.strip().splitlines() or [""])[-1]
            print(f"{rotulo}: {'VERMELHO (o guarda pegou)' if vermelho else 'MUTACAO NAO PEGOU'} — {teste} — {ultima}")
            falhas += 0 if vermelho else 1
        finally:
            caminho.write_bytes(bruto)                          # 🔴 restaura POR CÓPIA DOS BYTES
            assert caminho.read_bytes() == bruto, f"{rotulo}: {arquivo} não voltou igual"
    return falhas


if __name__ == "__main__" and "--mutar" in sys.argv:
    sys.exit(_mutar())

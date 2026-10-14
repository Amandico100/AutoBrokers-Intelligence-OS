# -*- coding: utf-8 -*-
"""SPEC-132-C · C3 — O FIO INTEIRO do atalho, do código no Meu perfil à resposta pela instância do ASSISTENTE.

    verificacao.gerar_codigo (o Meu perfil)  → o código + o wa.me para o número do ASSISTENTE (lido do banco)
      → "ATIVAR nnnnnn" pelo webhook REAL `/api/v1/webhook/evolution-go/{token}` (integração purpose='assistente')
      → o membro VERIFICADO (o número de quem mandou) → "Pronto…" pela instância do assistente
      → a próxima mensagem → `turno.rodar` → o `/chat/stream` REAL (dublê só no LLM e na Evolution)
      → a resposta em formato WhatsApp, pela instância do ASSISTENTE, ao número do membro
      → (a cotação que termina depois) `gravar_mensagem` do Work Run → `envio.avisar_pelo_atalho_sem_esperar` →
        a MESMA mensagem pelo WhatsApp, só se a conversa nasceu nele
    e a MESMA mensagem de um número NÃO verificado → ZERO envio. Duas corretoras.

E as costuras que a C3 fecha:
    · o QCM nunca responde pelo número do assistente (as DUAS integrações ativas na MESMA empresa da plataforma)
    · o pareamento do assistente tem escopo, purpose e instância PRÓPRIOS — e os purposes de antes não mudam

O mundo e o arreio são os da C2 (`test_spec132c_o_atalho`: banco em memória, webhook e /chat/stream REAIS, rede
FECHADA) — importados, não copiados.
Mutações: `python tests/test_spec132c_o_fio.py --mutar` (por cópia; exige VERMELHO; restaura).
Rodar: cd backend && python -m pytest tests/test_spec132c_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import inspect
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec132c_o_atalho as C2  # noqa: E402  (o mundo, o arreio e a fixture `fio` da C2)
from test_spec132c_o_atalho import fio  # noqa: E402,F401  (a fixture)
from app.services.atalho import envio as ENV  # noqa: E402
from app.services.atalho import turno as T  # noqa: E402
from app.services.atalho import verificacao as V  # noqa: E402
from app.services.canal import envio as CANAL_ENVIO  # noqa: E402
from app.services.canal import repositorio as REPO  # noqa: E402
from app.services.whatsapp import channel_identity as CI  # noqa: E402

ALFA, BETA, CANAL = C2.ALFA, C2.BETA, C2.CANAL
U3, U6 = C2.U3, C2.U6
CEL_3, CEL_6 = C2.CEL_3, C2.CEL_6

#: as 3 linhas que o gerente cola em `cotacao.workflow.gravar_mensagem`, logo antes do `return True` final
COSTURA_DO_WORKFLOW = (
    "    # SPEC-132-C C3 — a conversa nasceu no WhatsApp do corretor? a mesma mensagem volta por lá (nunca levanta)\n"
    "    from app.services.atalho.envio import avisar_pelo_atalho_sem_esperar\n"
    "    avisar_pelo_atalho_sem_esperar(cli, company_id=company_id, conversation_id=conversation_id, "
    "texto_markdown=texto)\n"
)


def _do_assistente(envio):
    return [e for e in envio.enviados if e["integracao"] == "int-assistente"]


# =====================================================================================================================
# 1. O FIO: código → ATIVAR pelo webhook → verificado → turno do CORE → resposta pelo ASSISTENTE (duas corretoras)
# =====================================================================================================================
@pytest.mark.parametrize("cid,uid,cel,nome_da_corretora", [(BETA, U3, CEL_3, "Corretora Beta"),
                                                           (ALFA, U6, CEL_6, "Corretora Alfa")],
                         ids=["beta-declarado-sem-verificar", "alfa-confirmado-sem-verificar"])
def test_o_fio_do_codigo_do_perfil_a_resposta_pelo_assistente(fio, cid, uid, cel, nome_da_corretora):
    pergunta = "quanto fica o seguro do meu cliente?"
    # ANTES da verificação: a MESMA mensagem, do MESMO número → silêncio total
    fio.postar(pergunta, tel=cel)
    assert fio.envio.enviados == [] and fio.grafo == [] and fio.banco.linhas("conversations") == []

    # o Meu perfil gera o código; o link abre a conversa com o número do ASSISTENTE (do banco), não o do QCM
    passo = V.gerar_codigo(fio.banco, company_id=cid, user_id=uid)
    assert passo["numero_assistente"] == C2.ASSISTENTE != C2.QCM
    assert passo["wa_me_url"] == f"https://wa.me/{C2.ASSISTENTE}?text=ATIVAR%20{passo['codigo']}"

    # o corretor manda "ATIVAR nnnnnn" do celular dele → o webhook REAL → o desvio do assistente
    r = fio.postar(passo["texto"], tel=cel)
    assert r == {"status": "accepted", "reason": "atalho"}
    (pronto,) = fio.envio.enviados
    assert pronto["integracao"] == "int-assistente" and pronto["purpose"] == "assistente"
    assert pronto["para"] == V._canonico(cel) and pronto["texto"].startswith("Pronto, ")
    assert nome_da_corretora in pronto["texto"]
    membro = next(m for m in fio.banco.linhas("company_members") if m["company_id"] == cid and m["user_id"] == uid)
    assert membro["whatsapp_trabalho_verificado_em"] and membro["whatsapp_trabalho_e164"] == cel
    assert fio.grafo == []                                       # a ativação não é turno do chat

    # a próxima mensagem do mesmo número → o turno do CORE da corretora DELE → a resposta pelo ASSISTENTE
    fio.postar(pergunta, tel=cel)
    assert [(g["company_id"], g["user_id"]) for g in fio.grafo] == [(cid, uid)]
    (conv,) = C2._conversas(fio.banco, company_id=cid, user_id=uid)
    assert conv["channel"] == T.CANAL_DO_ATALHO
    resposta = fio.envio.enviados[-1]
    assert resposta["integracao"] == "int-assistente" and resposta["para"] == V._canonico(cel)
    assert "*Cotação Rápida — 3 seguradoras*" in resposta["texto"] and "|" not in resposta["texto"]
    assert resposta["texto"].rstrip().endswith("apresentação: https://app.exemplo.test/r/abc123")
    # nada saiu por outro número, nada passou pelo QCM nem pelo observer
    assert {e["integracao"] for e in fio.envio.enviados} == {"int-assistente"}
    assert fio.taps == [] and fio.pipeline == []
    # a outra corretora não ganhou conversa nenhuma
    outra = ALFA if cid == BETA else BETA
    assert C2._conversas(fio.banco, company_id=outra) == []


def test_o_codigo_usado_nao_ativa_outro_numero(fio):
    passo = V.gerar_codigo(fio.banco, company_id=BETA, user_id=U3)
    fio.postar(passo["texto"], tel=CEL_3)
    n = len(fio.envio.enviados)
    fio.postar(passo["texto"], tel=C2.CEL_ESTRANHO)               # o mesmo código, de outro celular: silêncio
    assert len(fio.envio.enviados) == n
    assert V.membros_verificados_por_telefone(fio.banco, C2.CEL_ESTRANHO) == []


# =====================================================================================================================
# 2. a volta da cotação pelo WhatsApp (a conversa do atalho → 1×; a do painel → 0; a de outra corretora → 0)
# =====================================================================================================================
def _ativar_e_conversar(fio, cid=BETA, uid=U3, cel=CEL_3):
    fio.postar(V.gerar_codigo(fio.banco, company_id=cid, user_id=uid)["texto"], tel=cel)
    fio.postar("cota o carro do cliente", tel=cel)
    (conv,) = C2._conversas(fio.banco, company_id=cid, user_id=uid, channel=T.CANAL_DO_ATALHO)
    return conv


def _conversa_do_painel(fio, cid, uid):
    linha = {"id": "c0c0c0c0-0000-4000-8000-00000000c0c0", "company_id": cid, "user_id": uid, "channel": "web",
             "session_id": "s-painel", "status": "open"}
    fio.banco.linhas("conversations").append(linha)
    return linha


def test_a_volta_pelo_atalho_so_para_a_conversa_que_nasceu_nele(fio):
    conv = _ativar_e_conversar(fio)
    painel = _conversa_do_painel(fio, BETA, U3)
    texto = "**Pronto: 3 seguradoras responderam.**\n\nVeja a [apresentação](https://app.exemplo.test/r/xyz)."
    n = len(fio.envio.enviados)

    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=BETA, conversation_id=conv["id"], texto_markdown=texto)) is True
    (volta,) = fio.envio.enviados[n:]
    assert volta["integracao"] == "int-assistente" and volta["para"] == V._canonico(CEL_3)
    assert volta["texto"].startswith("*Pronto: 3 seguradoras responderam.*")
    assert volta["texto"].endswith("apresentação: https://app.exemplo.test/r/xyz")

    # a conversa do PAINEL do mesmo membro → nada sai
    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=BETA, conversation_id=painel["id"], texto_markdown=texto)) is False
    # a conversa do atalho pedida por OUTRA corretora → nada sai (o filtro company_id)
    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=ALFA, conversation_id=conv["id"], texto_markdown=texto)) is False
    # 🔴 a pessoa que está nas DUAS corretoras (U2, verificada nas duas): a conversa do atalho DELA na Beta, pedida
    # pela Alfa → nada sai (sem o filtro, o membro da Alfa existiria e a mensagem da Alfa cruzaria a conversa da Beta)
    conv_u2_beta = {"id": "d0d0d0d0-0000-4000-8000-00000000d0d0", "company_id": BETA, "user_id": C2.U2,
                    "channel": T.CANAL_DO_ATALHO, "session_id": "s-u2", "status": "open"}
    fio.banco.linhas("conversations").append(conv_u2_beta)
    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=ALFA, conversation_id=conv_u2_beta["id"], texto_markdown=texto)) is False
    assert len(fio.envio.enviados) == n + 1
    # CONTROLE: a mesma conversa pedida pela corretora DONA → sai (a regra consegue dizer sim)
    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=BETA, conversation_id=conv_u2_beta["id"], texto_markdown=texto)) is True
    assert fio.envio.enviados[-1]["para"] == V._canonico(C2.CEL_2)


def test_a_volta_respeita_o_interruptor_e_o_numero_que_deixou_de_ser_verificado(fio, monkeypatch):
    conv = _ativar_e_conversar(fio)
    n = len(fio.envio.enviados)
    monkeypatch.delenv(C2.E.ENV_LIGADO, raising=False)
    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=BETA, conversation_id=conv["id"], texto_markdown="oi")) is False
    monkeypatch.setenv(C2.E.ENV_LIGADO, "1")
    for m in fio.banco.linhas("company_members"):
        if m["company_id"] == BETA and m["user_id"] == U3:
            m["whatsapp_trabalho_verificado_em"] = None
    assert asyncio.run(ENV.avisar_pelo_atalho_se_for_o_caso(
        fio.banco, company_id=BETA, conversation_id=conv["id"], texto_markdown="oi")) is False
    assert len(fio.envio.enviados) == n


def _gravar_mensagem_com_a_costura():
    """O `gravar_mensagem` REAL do Work Run da cotação — com as 3 linhas da costura, se o arquivo ainda não as tem
    (montado em MEMÓRIA a partir do fonte do arquivo; o arquivo é da B4 e não é tocado)."""
    from app.services.cotacao import workflow as W

    fonte = textwrap.dedent(inspect.getsource(W.gravar_mensagem))
    if COSTURA_DO_WORKFLOW not in fonte:
        final = "    return True\n"
        assert fonte.endswith(final), "o gravar_mensagem não termina em `return True` — a costura mudou de lugar"
        fonte = fonte[: -len(final)] + COSTURA_DO_WORKFLOW + final
    escopo = dict(vars(W))
    exec(compile(fonte, W.__file__, "exec"), escopo)  # noqa: S102 — o fonte é o do próprio repositório
    return escopo["gravar_mensagem"]


def test_o_resultado_da_cotacao_gravado_pelo_work_run_volta_pelo_whatsapp_uma_vez(fio):
    gravar = _gravar_mensagem_com_a_costura()
    conv = _ativar_e_conversar(fio)
    painel = _conversa_do_painel(fio, BETA, U3)
    n = len(fio.envio.enviados)
    texto = "**Pronto: 2 seguradoras responderam.**\n\n[Abrir a apresentação](https://app.exemplo.test/r/k1)"

    # (o Work Run grava pela thread — `asyncio.to_thread` — como no `_entregar`)
    assert asyncio.run(asyncio.to_thread(gravar, fio.banco, company_id=BETA, conversation_id=conv["id"],
                                         run_id="run-1", tipo="pronta", texto=texto)) is True
    (volta,) = fio.envio.enviados[n:]
    assert volta["integracao"] == "int-assistente" and volta["para"] == V._canonico(CEL_3)
    assert "Abrir a apresentação: https://app.exemplo.test/r/k1" in volta["texto"]
    # a 2ª escrita do mesmo run+tipo (retomada) não grava — e não reenvia
    assert gravar(fio.banco, company_id=BETA, conversation_id=conv["id"], run_id="run-1", tipo="pronta",
                  texto=texto) is False
    # a conversa do PAINEL grava e NÃO envia; a de outra corretora não grava nem envia
    assert gravar(fio.banco, company_id=BETA, conversation_id=painel["id"], run_id="run-2", tipo="pronta",
                  texto=texto) is True
    assert gravar(fio.banco, company_id=ALFA, conversation_id=conv["id"], run_id="run-3", tipo="pronta",
                  texto=texto) is False
    assert len(fio.envio.enviados) == n + 1


def test_a_ponte_sincrona_dentro_de_um_laco_agenda_e_nao_trava(fio):
    conv = _ativar_e_conversar(fio)
    n = len(fio.envio.enviados)

    async def _no_laco():
        ENV.avisar_pelo_atalho_sem_esperar(fio.banco, company_id=BETA, conversation_id=conv["id"],
                                           texto_markdown="pronto")
        assert len(fio.envio.enviados) == n            # agendou, não bloqueou o laço
        for _ in range(500):      # ≤ 5 s (a máquina de teste é lenta); sai no 1º envio
            await asyncio.sleep(0.01)
            if len(fio.envio.enviados) > n:
                break

    asyncio.run(_no_laco())
    assert len(fio.envio.enviados) == n + 1 and fio.envio.enviados[-1]["integracao"] == "int-assistente"


@pytest.mark.parametrize("dorme", [0.0, 1.5], ids=["controle", "envio-lento"])
def test_a_volta_nao_prende_o_passo_do_work_run_alem_do_teto(fio, monkeypatch, dorme):
    """P4 (juiz): `TEMPO_DA_VOLTA_S` tem de ser TETO de verdade. Medido como o juiz mediu: teto 0,3 s, envio de 1,5 s →
    o passo (a thread que grava a cotação) fica livre em ≤ 0,4 s; o envio termina sozinho, uma vez."""
    import threading
    import time

    conv = _ativar_e_conversar(fio)
    n = len(fio.envio.enviados)
    monkeypatch.setattr(ENV, "TEMPO_DA_VOLTA_S", 0.3)
    original = fio.envio.send_message

    def _lento(*a, **k):
        time.sleep(dorme)
        return original(*a, **k)

    monkeypatch.setattr(fio.envio, "send_message", _lento)
    medida = {}

    def _passo():
        t0 = time.monotonic()
        ENV.avisar_pelo_atalho_sem_esperar(fio.banco, company_id=BETA, conversation_id=conv["id"],
                                           texto_markdown="pronto")
        medida["s"] = time.monotonic() - t0

    th = threading.Thread(target=_passo)
    th.start()
    th.join(20)
    assert medida["s"] <= 0.4, f"o passo ficou preso {medida['s']:.2f} s"
    for _ in range(400):            # o envio termina em 2º plano (≤ 4 s)
        if len(fio.envio.enviados) > n:
            break
        time.sleep(0.01)
    time.sleep(0.05)
    assert len(fio.envio.enviados) == n + 1 and fio.envio.enviados[-1]["integracao"] == "int-assistente"


def test_o_workflow_da_cotacao_tem_a_costura():
    """🔴 O ELO: a função existe E o Work Run a chama. Fica VERMELHO até o gerente colar as 3 linhas
    (`COSTURA_DO_WORKFLOW`) no `gravar_mensagem` de `services/cotacao/workflow.py`, logo antes do `return True`."""
    from app.services.cotacao import workflow as W

    fonte = textwrap.dedent(inspect.getsource(W.gravar_mensagem))
    assert COSTURA_DO_WORKFLOW in fonte and fonte.endswith(COSTURA_DO_WORKFLOW + "    return True\n")


# =====================================================================================================================
# 3. o QCM nunca responde pelo número do assistente (e o atalho nunca pelo do QCM) — as DUAS ativas na plataforma
# =====================================================================================================================
@pytest.mark.parametrize("ordem", ["assistente-primeiro", "qcm-primeiro"])
def test_o_qcm_sai_pelo_qcm_e_o_atalho_pelo_assistente(monkeypatch, ordem):
    import app.services.whatsapp.integration_secrets as SEG
    import app.services.whatsapp_service as WS

    banco = C2.mundo_inicial()
    plataforma = [x for x in banco.linhas("integrations") if x["company_id"] == CANAL]
    assert {x["purpose"] for x in plataforma} == {"assistente", "observer"}
    assert all(x["is_active"] and x["channel_status"] == "connected" for x in plataforma)
    if ordem == "qcm-primeiro":
        banco.linhas("integrations").sort(key=lambda x: 0 if x["id"] == "int-qcm" else 1)
    REPO._CACHE_DO_TIPO.clear()
    monkeypatch.setattr(SEG, "decrypt_integration_secret", lambda v, **_k: v)
    monkeypatch.setenv("ATALHO_CODIGO_SEGREDO", "segredo-de-teste-132c")   # o teto de envios conta pelo HMAC do telefone
    envio = C2.EnvioFalso()
    monkeypatch.setattr(WS, "get_whatsapp_service", lambda: envio)
    monkeypatch.setattr(CANAL_ENVIO, "PAUSA_ENTRE_BALOES_S", 0)

    assert CANAL_ENVIO.integracao_do_canal(banco, CANAL)["id"] == "int-qcm"
    assert CANAL_ENVIO.numero_do_canal(banco, CANAL) == C2.QCM       # o "Quero fechar" volta para o QCM
    assert asyncio.run(CANAL_ENVIO.enviar(banco, CANAL, C2.CEL_1, ["a cotação do convidado"])) == 1
    assert ENV.integracao_do_assistente(banco)["id"] == "int-assistente"
    assert asyncio.run(ENV.enviar_texto(ENV.integracao_do_assistente(banco), C2.CEL_1, "a resposta do chat",
                                        db=banco)) == 1
    assert [(e["integracao"], e["texto"]) for e in envio.enviados] == [
        ("int-qcm", "a cotação do convidado"), ("int-assistente", "a resposta do chat")]


def test_o_qcm_nao_conversa_com_o_numero_do_assistente():
    banco = C2.mundo_inicial()
    REPO._CACHE_DO_TIPO.clear()
    assert REPO.numero_de_corretora(banco, "+" + C2.ASSISTENTE) is True     # robô do produto: o QCM cala
    assert REPO.numero_de_corretora(banco, "+" + C2.QCM) is False           # CONTROLE: a regra de antes do QCM
    assert REPO.numero_de_corretora(banco, C2.CEL_LINHA_ALFA) is True       # CONTROLE: a linha de uma corretora
    assert REPO.numero_de_corretora(banco, C2.CEL_1) is False               # CONTROLE: uma pessoa


# =====================================================================================================================
# 4. o pareamento: o assistente tem escopo, purpose e instância PRÓPRIOS; os purposes de antes não mudam
# =====================================================================================================================
EMPRESA = "04b5cdbc-04cd-0000-0000-000000000000"
#: o que `channel_identity` devolvia ANTES da C3 (escrito à mão: é a régua da não-regressão)
ANTES = {
    "observer": ("corretora", "observer", "ab-obs-04b5cdbc04-1", False),
    "attendance": ("corretora", "observer", "ab-obs-04b5cdbc04-1", False),
    "dispatch": ("corretora", "observer", "ab-obs-04b5cdbc04-1", False),
    "": ("corretora", "observer", "ab-obs-04b5cdbc04-1", False),
    "um-valor-novo": ("corretora", "observer", "ab-obs-04b5cdbc04-1", False),
    "auxiliary:cobranca": ("auxiliary:cobranca", "auxiliary:cobranca", "ab-aux-04b5cdbc04-cobranca", True),
    "auxiliary:": ("corretora", "observer", "ab-obs-04b5cdbc04-1", False),
}


@pytest.mark.parametrize("purpose", sorted(ANTES))
def test_os_purposes_de_antes_devolvem_o_mesmo(purpose):
    assert (CI.escopo_de(purpose), CI.purpose_canonico(purpose), CI.nome_da_instancia(EMPRESA, purpose),
            CI.numero_proprio(purpose)) == ANTES[purpose]


@pytest.mark.parametrize("purpose", ["assistente", " Assistente "])
def test_o_assistente_e_um_escopo_proprio_da_plataforma(purpose):
    assert CI.escopo_de(purpose) == "plataforma:assistente"
    assert CI.purpose_canonico(purpose) == "assistente" == CI.PURPOSE_DO_ASSISTENTE == V.PURPOSE_DO_ASSISTENTE
    assert CI.numero_proprio(purpose) is True
    nome = CI.nome_da_instancia(EMPRESA, purpose)
    assert nome == "ab-ast-04b5cdbc04"
    # na MESMA empresa da plataforma, o QR do assistente nunca é a instância do QCM (observer)
    assert nome != CI.nome_da_instancia(EMPRESA, "observer")
    from app.services.whatsapp.pairing_orchestrator import PairingOrchestrator

    assert PairingOrchestrator._escopo(purpose) == "assistente"
    assert PairingOrchestrator._escopo("attendance") == "observer"          # CONTROLE


class _Provedor:
    """O Evolution GO na borda (httpx.MockTransport): registra o que o pareamento pede."""

    def __init__(self):
        self.pedidos = []

    def __call__(self, pedido):
        import httpx
        import json as _json

        corpo = _json.loads(pedido.content.decode() or "null") if pedido.content else None
        self.pedidos.append((pedido.method, pedido.url.path, corpo, pedido.headers.get("apikey")))
        if pedido.url.path == "/instance/status":
            return httpx.Response(200, json={"data": {"LoggedIn": False, "Connected": False}})
        if pedido.url.path == "/instance/all":
            return httpx.Response(200, json={"data": []})
        return httpx.Response(200, json={"data": {}})


def _orquestrador(monkeypatch, banco):
    import httpx

    import app.core.database as DB
    import app.services.whatsapp.integration_secrets as SEG
    import app.services.whatsapp.pairing_orchestrator as PO

    monkeypatch.setenv("EVOLUTION_GO_BASE_URL", "http://evolution.invalid")
    monkeypatch.setenv("EVOLUTION_GO_GLOBAL_KEY", "chave-global-de-teste")
    monkeypatch.setenv("PUBLIC_BACKEND_URL", "https://backend.exemplo.test")
    monkeypatch.setattr(DB, "get_supabase_client", lambda: types.SimpleNamespace(client=banco))
    monkeypatch.setattr(SEG, "encrypt_integration_secret", lambda v: v)
    monkeypatch.setattr(SEG, "decrypt_integration_secret", lambda v, **_k: v)
    provedor = _Provedor()
    original = httpx.AsyncClient

    def _cliente(*a, **k):
        k["transport"] = httpx.MockTransport(provedor)
        return original(*a, **k)

    monkeypatch.setattr(PO.httpx, "AsyncClient", _cliente)
    orq = PO.PairingOrchestrator()

    async def _salvar(state):
        return state

    async def _refrescar(state):
        return state

    monkeypatch.setattr(orq, "_save", _salvar)
    monkeypatch.setattr(orq, "_refresh", _refrescar)
    REPO._CACHE_DO_TIPO.clear()
    return orq, provedor


def test_o_qr_do_assistente_cria_instancia_propria_e_nao_toca_no_qcm(monkeypatch):
    banco = C2.mundo_inicial()
    # o assistente ainda não pareado: só o QCM (observer) na plataforma
    banco.dados["integrations"] = [x for x in banco.linhas("integrations") if x["id"] != "int-assistente"]
    qcm_antes = dict(next(x for x in banco.linhas("integrations") if x["id"] == "int-qcm"))
    orq, provedor = _orquestrador(monkeypatch, banco)
    estado = {"company_id": CANAL, "purpose": orq._escopo("assistente"), "attempt_id": "a1", "correlation_id": "c1",
              "expires_at": "2099-01-01T00:00:00+00:00", "support_ref": "s1", "created_at": "2026-10-14T00:00:00+00:00"}
    asyncio.run(orq._prepare_and_connect(estado, method="qr", phone_number=None))

    criar = [p for p in provedor.pedidos if p[1] == "/instance/create"]
    assert len(criar) == 1 and criar[0][2]["name"] == f"ab-ast-{CANAL.replace('-', '')[:10]}"
    assert criar[0][2]["advancedSettings"]["ignoreGroups"] is True
    conectar = [p for p in provedor.pedidos if p[1] == "/instance/connect"]
    assert len(conectar) == 1
    url = str(conectar[0][2].get("webhookUrl") or conectar[0][2].get("webhook_url") or "")
    assert url.startswith("https://backend.exemplo.test/api/v1/webhook/evolution-go/")
    token = url.rsplit("/", 1)[1]
    nova = [x for x in banco.linhas("integrations") if x.get("purpose") == "assistente" and x["company_id"] == CANAL]
    assert len(nova) == 1 and nova[0]["is_active"] is True and nova[0]["identifier"] == criar[0][2]["name"]
    assert nova[0]["webhook_token_hash"] == C2._hash(token)               # o webhook com token PRÓPRIO
    assert nova[0]["webhook_token_hash"] != qcm_antes["webhook_token_hash"]
    assert nova[0].get("agent_id") is None and not nova[0].get("alert_target")
    # o QCM ficou EXATAMENTE como estava (ativo, mesma instância, mesmo token)
    qcm_depois = next(x for x in banco.linhas("integrations") if x["id"] == "int-qcm")
    assert qcm_depois == qcm_antes
    # e o webhook reconhece a nova linha como o assistente (o desvio da C2)
    assert C2.E.eh_do_assistente(banco, nova[0]) is True


def test_o_qr_do_assistente_numa_corretora_e_recusado(monkeypatch):
    banco = C2.mundo_inicial()
    orq, provedor = _orquestrador(monkeypatch, banco)
    with pytest.raises(ValueError, match="assistente_so_na_plataforma"):
        asyncio.run(orq.start(ALFA, "assistente"))
    assert provedor.pedidos == []


# =====================================================================================================================
# as MUTAÇÕES (por cópia) — `python tests/test_spec132c_o_fio.py --mutar`
# =====================================================================================================================
MUTACOES = [
    ("Q1 o QCM escolhe qualquer integração da plataforma", "app/services/canal/envio.py",
     "              and str(x.get(\"purpose\") or \"\").strip().lower() != PURPOSE_DO_ASSISTENTE]\n",
     "              ]\n",
     "test_o_qcm_sai_pelo_qcm_e_o_atalho_pelo_assistente"),
    ("Q2 o QCM conversa com o número do assistente", "app/services/canal/repositorio.py",
     "        if any(str(x.get(\"purpose\") or \"\").strip().lower() == \"assistente\" for x in linhas):\n",
     "        if False:\n",
     "test_o_qcm_nao_conversa_com_o_numero_do_assistente"),
    ("P1 o assistente volta a cair na linha da corretora", "app/services/whatsapp/channel_identity.py",
     "        return ESCOPO_DO_ASSISTENTE\n    if p.startswith(PREFIXO_AUXILIAR):\n",
     "        return \"corretora\"\n    if p.startswith(PREFIXO_AUXILIAR):\n",
     "test_o_assistente_e_um_escopo_proprio_da_plataforma or test_o_qr_do_assistente_cria"),
    ("P2 a corretora pareia um assistente", "app/services/whatsapp/pairing_orchestrator.py",
     "        if not ok:\n            raise ValueError(\"assistente_so_na_plataforma\")\n",
     "        if False:\n            raise ValueError(\"assistente_so_na_plataforma\")\n",
     "test_o_qr_do_assistente_numa_corretora_e_recusado"),
    ("V1 a volta sai para a conversa do painel", "app/services/atalho/envio.py",
     "    if not linha or linha.get(\"channel\") != CANAL_DO_ATALHO or not linha.get(\"user_id\"):\n",
     "    if not linha or not linha.get(\"user_id\"):\n",
     "test_a_volta_pelo_atalho_so_para_a_conversa_que_nasceu_nele or test_o_resultado_da_cotacao"),
    ("V2 a volta lê a conversa sem o filtro da corretora", "app/services/atalho/envio.py",
     "                    .eq(\"id\", conv).eq(\"company_id\", cid).limit(1).execute())\n"
     "    linha = next((x for x in linhas if str(x.get(\"id\") or \"\").lower() == conv\n"
     "                  and str(x.get(\"company_id\") or \"\").lower() == cid), None)\n",
     "                    .eq(\"id\", conv).limit(1).execute())\n"
     "    linha = next((x for x in linhas if str(x.get(\"id\") or \"\").lower() == conv), None)\n",
     "test_a_volta_pelo_atalho_so_para_a_conversa_que_nasceu_nele"),
    ("C-P4j a volta volta a prender o passo (asyncio.run direto)", "app/services/atalho/envio.py",
     "            fio_da_volta.join(timeout=max(0.0, float(TEMPO_DA_VOLTA_S)))\n",
     "            fio_da_volta.join()\n",
     "test_a_volta_nao_prende_o_passo_do_work_run_alem_do_teto"),
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
            falhas += 0 if vermelho else 1
        finally:
            caminho.write_bytes(bruto)                          # 🔴 restaura POR CÓPIA DOS BYTES
            assert caminho.read_bytes() == bruto, f"{rotulo}: {arquivo} não voltou igual"
    return falhas


if __name__ == "__main__" and "--mutar" in sys.argv:
    sys.exit(_mutar())

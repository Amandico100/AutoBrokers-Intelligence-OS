# -*- coding: utf-8 -*-
"""SPEC-133-A · CONSERTO ÚNICO — os 2 blockers e as 7 pendências dos laudos do juiz e do red team (07/10).

    B1  dado pessoal ao modelo: mídia NUNCA é resposta (consentimento, roteiro, pós-resultado) · a máscara antes de
        `entender` · o consentimento só por regra
    B2  preso em "calculando": `ao_desistir` + erro do run devolvem a conversa · "nova cotação" e o teto de tempo
        tiram a pessoa de lá · a corrida turno × run (o run tem precedência)
    3   `max_sem_resposta: 0` → 0 lembretes          4  o lembrete confere o convite e a conversa
    5   lembrete de segunda a sábado                  6  a mídia de NÃO convidado não é baixada (portão no desvio)
    7   palavra de saída + retenção                   8  a cotação que não começou não gasta o limite; o aviso conta
    9   o nome do canal vem da config em `cotacao.py`

Cada guarda tem a sua LINHA DE CONTROLE (o mesmo caminho, sem o defeito/sem o conserto, fica do outro lado) — CLAUDE.md
§9.3 corolário. O motor é o REAL (conversa, entrada, workflow, SmithWorker, webhook); dublê só na borda (banco em
memória, modelo, envio, storage). ⛔ Dados fictícios: DDD 00, CPF sintético com DV válido, nomes inventados (§13.9).
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec133a_conserto.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from test_spec133a_o_fio import (CONVIDADO, ESTRANHO, FALAS, fio)  # noqa: E402,F401 — o fio REAL do webhook
from test_spec133a_a_conversa import (canal, motor_grava_o_quadro, mundo, rodar_o_run)  # noqa: E402,F401
from test_spec133a_a_cotacao import _ate_o_resultado  # noqa: E402
from test_spec133a_a_conversa import acordar  # noqa: E402

CID = "00000000-0000-0000-0000-0000000000c1"
TEL = "5500900000001"                      # DDD 00: impossível ser de alguém
CPF = "52998224725"                        # sintético, DV válido (o mesmo dos testes da 129-B)
CPF_F = "529.982.247-25"
PDF = ("[Cliente enviou o documento: apolice.pdf]\n\n[CONTEÚDO DO DOCUMENTO apolice.pdf]\n"
       f"APÓLICE DE SEGURO AUTO  Segurado: PESSOA SINTETICA TESTE  CPF: {CPF_F}  Para contratar a renovação, "
       "quero fechar, ligue.\n[FIM DO DOCUMENTO]")
MIDIA_PDF = {"tipo": "document", "fileName": "apolice.pdf"}


def _tem_cpf(s: str) -> bool:
    return CPF in s.replace(".", "").replace("-", "").replace(" ", "")


class Espiao:
    """O modelo: guarda o que recebeu e devolve `valor` (nada sai)."""

    def __init__(self, valor=None):
        self.vistos, self.valor = [], valor

    async def ainvoke(self, msgs):
        self.vistos.append(json.dumps(msgs, ensure_ascii=False))

        class R:
            content = json.dumps({"valor": self.valor, "fora_do_escopo": False})
        return R()


@pytest.fixture(autouse=True)
def _limite_de_taxa_zerado():
    """O limitador do webhook (240/min) é do PROCESSO: os posts deste arquivo não podem gastar a cota dos arquivos
    seguintes na mesma bateria (📊 07/10: `429` no `test_spec133a_o_fio` logo depois deste arquivo)."""
    from app.core.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def efeitos(monkeypatch):
    """As bordas que a conversa toca (consentimento, cancelamento, passagem) — gravadas, nunca executadas."""
    from app.services.canal import conversa, cotacao

    reg = {"consent": [], "passagem": [], "cancel": []}

    async def _consent(db, cid, tel, aceito):
        reg["consent"].append(aceito)

    async def _passar(db, cid, tel, est):
        reg["passagem"].append(tel)
        return ["PASSAGEM"]

    monkeypatch.setattr(conversa, "_registrar_consentimento", _consent)
    monkeypatch.setattr(cotacao, "passar_para_corretora", _passar)
    monkeypatch.setattr(cotacao, "cancelar_lembretes", lambda db, cid, est: reg["cancel"].append(est.get("run_id")))
    return reg


def _responder(texto, estado, *, midia=None, llm=None, config=None):
    from app.services.canal import conversa

    return asyncio.run(conversa.responder(None, CID, TEL, texto, midia, estado, config=config, llm=llm or Espiao()))


_RESULTADO = {"etapa": "resultado", "consentimento": "sim", "pedido_id": "abcd1234-0000-0000-0000-000000000000",
              "run_id": "run-1", "resultado": {"url": "https://x.test/r/t", "anfitria_nome": "Corretora Ficticia"}}


# =====================================================================================================================
# B1 — dado pessoal ao modelo
# =====================================================================================================================
def test_b1_cpf_junto_do_sim_nao_vai_ao_modelo_e_o_sim_vale(efeitos):
    llm = Espiao()
    r = _responder(f"sim, pode. meu cpf é {CPF_F}", {"etapa": "consentimento"}, llm=llm)
    assert llm.vistos == [] and r.estado["etapa"] == "placa" and efeitos["consent"] == [True]
    assert not _tem_cpf(json.dumps(r.estado))


def test_b1_o_consentimento_e_so_regra_o_que_ela_nao_entende_pergunta_de_novo(efeitos):
    llm = Espiao(valor=True)                      # um modelo que diria "sim" — e não é chamado
    r = _responder("manda ver, meu cpf é " + CPF_F, {"etapa": "consentimento"}, llm=llm)
    assert llm.vistos == [] and r.estado["etapa"] == "consentimento" and efeitos["consent"] == []
    assert "Posso seguir?" in r.baloes[-1]
    # controle: "sim, mas não…" não é sim; "não, obrigado" é não
    assert _responder("sim, mas não quero dar o cpf", {"etapa": "consentimento"}).estado["etapa"] == "consentimento"
    assert _responder("não, obrigado", {"etapa": "consentimento"}).estado["etapa"] == "recusou"


@pytest.mark.parametrize("estado", [
    {"etapa": "consentimento"},
    {"etapa": "km_mensal", "consentimento": "sim", "respostas": {"placa": "ABC1D23"}},
    dict(_RESULTADO),
    dict(_RESULTADO, etapa="oferta_passagem"),
    {"etapa": "oferta_ajuda", "consentimento": "sim", "voltar_para": "km_mensal"},
    {"etapa": "calculando", "consentimento": "sim", "run_id": "r", "pedido_id": "p",
     "disparado_em": datetime.now(timezone.utc).isoformat()},
    dict(_RESULTADO, etapa="passado"),
], ids=lambda e: e["etapa"])
def test_b1_midia_nunca_e_resposta_em_etapa_nenhuma(efeitos, estado):
    """A apólice (com CPF e "contratar"/"quero fechar" no texto) em cada etapa: 0 chamada ao modelo, 0 passagem,
    o CPF nunca no estado, e a etapa não anda (no pós-resultado volta a pergunta sim/não)."""
    llm = Espiao(valor="fechar")
    r = _responder(PDF, estado, midia=MIDIA_PDF, llm=llm)
    assert llm.vistos == [] and efeitos["passagem"] == [] and efeitos["consent"] == []
    assert not _tem_cpf(json.dumps(r.estado)) and not _tem_cpf(" ".join(r.baloes))
    esperado = "oferta_passagem" if estado["etapa"] in ("resultado", "oferta_passagem") else estado["etapa"]
    assert r.estado["etapa"] == esperado
    guardou = estado.get("consentimento") == "sim"
    assert (r.estado.get("midias") == [{"tipo": "document", "ref": "arquivo:apolice.pdf"}]) is guardou


def test_b1_controle_sem_o_guarda_a_apolice_dispara_a_passagem(efeitos, monkeypatch):
    """LINHA DE CONTROLE: o guarda da mídia desligado (o defeito reintroduzido) → o texto do PDF vira "quero fechar"."""
    from app.services.canal import conversa

    async def _sem_guarda(db, company_id, midia, est, nome_canal):
        return await conversa._depois_do_resultado(db, company_id, TEL, PDF, est, None)

    monkeypatch.setattr(conversa, "_midia_nao_e_resposta", _sem_guarda)
    _responder(PDF, dict(_RESULTADO), midia=MIDIA_PDF)
    assert efeitos["passagem"] == [TEL]


def test_b1_cpf_numa_resposta_livre_chega_mascarado_ao_modelo(efeitos, monkeypatch):
    from app.services.canal import conversa

    est = {"etapa": "km_mensal", "consentimento": "sim", "respostas": {"placa": "ABC1D23"}}
    fala = f"rodo uns 800 km, já te passo o cpf {CPF_F}, cel 00 99999-0000, placa abc1d23, x@y.test"
    llm = Espiao()
    _responder(fala, dict(est), llm=llm)
    assert len(llm.vistos) == 1 and not _tem_cpf(llm.vistos[0]) and "99999" not in llm.vistos[0]
    assert "ABC1D23" not in llm.vistos[0].upper() and "x@y.test" not in llm.vistos[0] and "800" in llm.vistos[0]
    # controle: sem a máscara (o defeito reintroduzido) o CPF chega ao prompt
    monkeypatch.setattr(conversa, "mascarar_para_o_modelo", lambda t: str(t or ""))
    llm2 = Espiao()
    _responder(fala, dict(est), llm=llm2)
    assert _tem_cpf(llm2.vistos[0])


@pytest.mark.parametrize("texto,sai", [
    ("uns 800 km", "uns 800 km"), ("pago 2.800,00 por ano", "pago 2.800,00 por ano"), ("60.000,00", "60.000,00"),
    ("1,2 mil", "1,2 mil"), (CPF_F, "[NUMERO]"), (CPF, "[NUMERO]"), ("(00) 99999-0000", "([NUMERO]"),
    ("01001-000", "[NUMERO]"), ("ABC-1D23", "[PLACA]"), ("25/03/1985", "[NUMERO]"), ("a@b.test", "[EMAIL]"),
])
def test_b1_a_mascara(texto, sai):
    from app.services.canal.conversa import mascarar_para_o_modelo

    assert mascarar_para_o_modelo(texto) == sai


def test_b1_pelo_fio_o_pdf_no_consentimento_nao_chama_o_modelo(fio):
    """O MESMO caso pela entrada REAL (estado cifrado no banco do mundo, envio na borda)."""
    from app.services.canal import entrada

    f = fio
    f.falar("oi")
    integ = next(i for i in f.m.banco.linhas("integrations") if i["company_id"] == f.m.canal)
    asyncio.run(entrada.turno(f.db, integ, CONVIDADO, [{"tipo": "document", "legenda": PDF,
                                                        "midia": {"fileName": "apolice.pdf"}}]))
    est = f.repo.carregar_estado(f.db, f.m.canal, CONVIDADO)
    assert f.modelo.chamadas == 0 and est["etapa"] == "consentimento" and "midias" not in est
    assert not f.m.banco.linhas("canal_consentimentos")


# =====================================================================================================================
# B2 — preso em "calculando"
# =====================================================================================================================
def _calculando(minutos_atras: float, **extra):
    from app.services.canal import conversa

    agora = datetime.fromisoformat(conversa._agora_iso())
    return {"versao": 1, "etapa": "calculando", "consentimento": "sim", "consentimento_em": agora.isoformat(),
            "run_id": "run-morto", "pedido_id": "p1", "primeiro_nome": "Pessoa",
            "disparado_em": (agora - timedelta(minutes=minutos_atras)).isoformat(), **extra}


@pytest.mark.parametrize("fala", ["nova cotação", "recomeçar", "quero fazer outra cotação"])
def test_b2_nova_cotacao_tira_de_calculando_sempre(efeitos, fala):
    r = _responder(fala, _calculando(1))
    assert r.estado["etapa"] == "consentimento" and efeitos["cancel"] == ["run-morto"]


def test_b2_passou_o_teto_a_conversa_sai_honesta(efeitos):
    from app.services.canal.conversa import FRASE_NAO_TERMINOU

    r = _responder("oi", _calculando(6 * 24 * 60))
    assert r.baloes == [FRASE_NAO_TERMINOU] and r.estado["etapa"] == "falhou"
    assert set(r.estado) <= {"versao", "etapa", "consentimento", "consentimento_em", "falha"}, r.estado
    assert efeitos["cancel"] == ["run-morto"]
    # controle: dentro do teto, ainda calcula
    assert _responder("oi", _calculando(1)).estado["etapa"] == "calculando"
    # o teto é da CONFIG: 1 min pedido → 2 min já passou (o padrão, 20, não)
    assert _responder("oi", _calculando(2), config={"canal": {"tempo_max_calculando_min": 1}}).estado["etapa"] == "falhou"
    assert _responder("oi", _calculando(2)).estado["etapa"] == "calculando"


def test_b2_o_workflow_tem_ao_desistir_no_registro():
    from app.services.canal import workflows as W
    from app.services.work.runs import _politica_do_workflow
    from app.workers.smith_worker import SmithWorker

    registro = SmithWorker()._registro_de_workflows()
    _reg, _idade, gancho = _politica_do_workflow(registro, "canal.cotacao")
    assert gancho is W._canal_desistiu


def _ate_calculando(f, tel=CONVIDADO):
    for fala in ["oi", "sim", *FALAS]:
        f.falar(fala, tel=tel)
    est = f.repo.carregar_estado(f.db, f.m.canal, tel)
    assert est.get("etapa") == "calculando" and est.get("run_id")
    return est


def test_b2_o_run_que_quebra_devolve_a_conversa_pelo_worker_real(fio, monkeypatch):
    """publicar_proposta levanta (ex.: LinkSemEndereco no worker) → o SmithWorker REAL vê o erro, e ANTES dele a
    conversa sai de "calculando" com UMA frase honesta, contada no teto do dia."""
    import app.services.multicalculo.proposta as PROP
    from app.services.canal.conversa import FRASE_NAO_TERMINOU

    f = fio
    est = _ate_calculando(f)
    motor_grava_o_quadro(f.m.banco, pedido_id=est["pedido_id"], dados=f.m.dados)

    async def _quebra(**_kw):
        raise RuntimeError("publicar indisponível (simulado)")

    monkeypatch.setattr(PROP, "publicar_proposta", _quebra)
    antes, contadas = len(f.envio.enviados), f.repo.enviadas_hoje(f.db, f.m.canal, CONVIDADO)
    with pytest.raises(RuntimeError):
        asyncio.run(rodar_o_run(f.db, est["run_id"], f.m.canal))
    depois = f.repo.carregar_estado(f.db, f.m.canal, CONVIDADO)
    assert depois["etapa"] == "falhou" and not _tem_cpf(json.dumps(depois)) and "pedido_id" not in depois
    assert [e["texto"] for e in f.envio.enviados[antes:]] == [FRASE_NAO_TERMINOU]
    assert f.repo.enviadas_hoje(f.db, f.m.canal, CONVIDADO) == contadas + 1
    # e o próximo "oi" é uma conversa nova (não "Ainda estou calculando")
    assert "Posso seguir?" in "\n".join(f.falar("oi"))


def test_b2_controle_sem_a_desistencia_a_pessoa_fica_presa(fio, monkeypatch):
    """LINHA DE CONTROLE: a desistência desligada (o defeito reintroduzido) → "calculando" fica, nada sai."""
    import app.services.multicalculo.proposta as PROP
    from app.services.canal import workflows as W

    f = fio
    est = _ate_calculando(f)
    motor_grava_o_quadro(f.m.banco, pedido_id=est["pedido_id"], dados=f.m.dados)

    async def _quebra(**_kw):
        raise RuntimeError("publicar indisponível (simulado)")

    async def _nada(*_a, **_k):
        return False

    monkeypatch.setattr(PROP, "publicar_proposta", _quebra)
    monkeypatch.setattr(W, "desistir_da_cotacao", _nada)
    antes = len(f.envio.enviados)
    with pytest.raises(RuntimeError):
        asyncio.run(rodar_o_run(f.db, est["run_id"], f.m.canal))
    assert f.repo.carregar_estado(f.db, f.m.canal, CONVIDADO)["etapa"] == "calculando"
    assert f.envio.enviados[antes:] == []


def test_b2_ao_desistir_do_work_os_devolve_a_conversa_e_nao_pisa_numa_nova(fio):
    """O gancho que o Work OS chama (efeito incerto / expirou) — síncrono, fora de laço, pelo banco do mundo."""
    from app.services.canal import workflows as W
    from app.services.canal.conversa import FRASE_NAO_TERMINOU

    f = fio
    est = _ate_calculando(f)
    run = {"id": est["run_id"], "company_id": f.m.canal, "status": "failed"}
    antes = len(f.envio.enviados)
    W._canal_desistiu(f.db, run, "efeito incerto (simulado)")
    assert f.repo.carregar_estado(f.db, f.m.canal, CONVIDADO)["etapa"] == "falhou"
    assert [e["texto"] for e in f.envio.enviados[antes:]] == [FRASE_NAO_TERMINOU]
    # controle: a pessoa já recomeçou (conversa nova) → o gancho não pisa nem manda nada
    f.falar("oi")
    antes = len(f.envio.enviados)
    W._canal_desistiu(f.db, run, "expirou (simulado)")
    assert f.repo.carregar_estado(f.db, f.m.canal, CONVIDADO)["etapa"] == "consentimento"
    assert f.envio.enviados[antes:] == []


def test_b2_nova_cotacao_cancela_o_run_que_calculava(fio):
    f = fio
    est = _ate_calculando(f)
    f.falar("nova cotação")
    assert f.m.banco.run(est["run_id"])["status"] in ("cancelled", "cancelling")


def test_b2_o_run_nao_entrega_numa_conversa_que_recomecou(fio, monkeypatch):
    """O cancelamento se perdeu (best-effort) e o run roda: ele relê a conversa e NÃO publica/manda/grava."""
    f = fio
    est = _ate_calculando(f)
    monkeypatch.setattr(f.cotacao, "cancelar_lembretes", lambda *_a, **_k: False)
    f.falar("nova cotação")
    motor_grava_o_quadro(f.m.banco, pedido_id=est["pedido_id"], dados=f.m.dados)
    antes = len(f.envio.enviados)
    asyncio.run(rodar_o_run(f.db, est["run_id"], f.m.canal))
    assert f.repo.carregar_estado(f.db, f.m.canal, CONVIDADO)["etapa"] == "consentimento"
    assert f.envio.enviados[antes:] == []


@pytest.mark.parametrize("corrida", [True, False], ids=["run_grava_no_meio", "controle_sem_corrida"])
def test_b2_a_corrida_o_run_tem_precedencia_sobre_o_turno(fio, monkeypatch, corrida):
    """O turno lê "calculando"; enquanto pensa, o run grava "resultado". O turno NÃO grava "calculando" por cima nem
    manda "Ainda estou calculando". Controle: sem a corrida, o turno grava e responde como sempre."""
    f = fio
    _ate_calculando(f)
    original = f.conversa.responder

    async def _responder_com_run_no_meio(db, company_id, tel, *a, **kw):
        r = await original(db, company_id, tel, *a, **kw)
        if corrida:
            atual = f.repo.carregar_estado(db, company_id, tel)
            f.repo.salvar_estado(db, company_id, tel, dict(atual, etapa="resultado", resultado={"url": "u"}))
        return r

    monkeypatch.setattr(f.conversa, "responder", _responder_com_run_no_meio)
    saiu = f.falar("oi")
    etapa = f.repo.carregar_estado(f.db, f.m.canal, CONVIDADO)["etapa"]
    if corrida:
        assert etapa == "resultado" and saiu == []
    else:
        assert etapa == "calculando" and saiu and saiu[0].startswith("Ainda estou calculando")


# =====================================================================================================================
# 3 · 4 — os lembretes (Work Run REAL pelo SmithWorker, banco do mundo)
# =====================================================================================================================
def _lembretes(m, c, run_id):
    saidos = []
    for _ in range(10):
        if not acordar(m.banco, m.db, run_id):
            continue
        antes = len(c.envio.enviados)
        asyncio.run(rodar_o_run(m.db, run_id, m.canal))
        saidos += c.envio.enviados[antes:]
    return saidos


@pytest.mark.parametrize("pedido,esperado", [(0, 0), (1, 1)], ids=["zero_desliga", "controle_um"])
def test_3_max_sem_resposta_zero_desliga_os_lembretes(mundo, canal, pedido, esperado):
    m, c = mundo, canal
    m.banco.semear("multicalculo_config", {"company_id": m.canal, "config": {
        "canal": {"follow_up": {"max_sem_resposta": pedido, "primeiro_apos_min": 15, "segundo_apos_h": 24}}}})
    run_id = _ate_o_resultado(m, c)
    assert len(_lembretes(m, c, run_id)) == esperado
    assert m.banco.run(run_id)["status"] == "completed"


@pytest.mark.parametrize("removido", [True, False], ids=["removido_nao_recebe", "controle_convidado_recebe"])
def test_4_o_convidado_removido_nao_recebe_lembrete(mundo, canal, removido):
    from test_spec133a_a_conversa import TEL as TEL_DO_MUNDO

    m, c = mundo, canal
    run_id = _ate_o_resultado(m, c)
    if removido:
        c.repo.removidos.add((m.canal, TEL_DO_MUNDO))
    assert len(_lembretes(m, c, run_id)) == (0 if removido else 2)


def test_4_a_conversa_que_parou_nao_recebe_lembrete(mundo, canal):
    from test_spec133a_a_conversa import TEL as TEL_DO_MUNDO
    from test_spec133a_a_conversa import falar

    m, c = mundo, canal
    run_id = _ate_o_resultado(m, c)
    falar(c, m.db, m.canal, ["parar"], telefone=TEL_DO_MUNDO)
    assert c.repo.carregar_estado(m.db, m.canal, TEL_DO_MUNDO)["etapa"] == "parou"
    assert _lembretes(m, c, run_id) == []


# =====================================================================================================================
# 5 — de segunda a sábado
# =====================================================================================================================
@pytest.mark.parametrize("utc,esperado_local", [
    (datetime(2026, 10, 11, 13, 0, tzinfo=timezone.utc), (0, 9)),    # domingo 10h → segunda 9h
    (datetime(2026, 10, 10, 23, 30, tzinfo=timezone.utc), (0, 9)),   # sábado 20h30 → (domingo) → segunda 9h
    (datetime(2026, 10, 10, 13, 0, tzinfo=timezone.utc), (5, 10)),   # controle: sábado 10h fica
    (datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc), (0, 9)),    # controle: segunda 7h → segunda 9h
])
def test_5_lembrete_so_de_segunda_a_sabado(utc, esperado_local):
    from app.services.canal.workflows import _fuso, no_horario_comercial

    local = no_horario_comercial(utc, {"inicio_h": 9, "fim_h": 20}).astimezone(_fuso())
    assert (local.weekday(), local.hour) == esperado_local


# =====================================================================================================================
# 6 — a mídia de quem não foi convidado não é baixada (o portão no desvio, ANTES da mídia)
# =====================================================================================================================
@pytest.mark.parametrize("quem,baixa", [("estranho", False), ("convidado", True)])
def test_6_midia_de_nao_convidado_nao_e_baixada(fio, monkeypatch, quem, baixa):
    import copy

    import app.services.vision_service as VS
    from test_spec133a_a_entrada import FIXTURE
    from test_spec133a_o_fio import TOKEN_CANAL

    f = fio
    w = f.w
    chamadas = {"download": 0, "upload": 0, "leitura": 0}

    async def _dl(*_a, **_k):
        chamadas["download"] += 1
        return (b"%PDF-1.4 ficticio", "application/pdf")

    async def _up(*_a, **_k):
        chamadas["upload"] += 1
        return "https://storage.invalid/storage/v1/object/sign/chat-docs/x.pdf?token=t"

    async def _ler(*_a, **_k):
        chamadas["leitura"] += 1
        return "TEXTO FICTICIO"

    monkeypatch.setattr(w, "_download_evolution_media", _dl)
    monkeypatch.setattr(w, "_upload_media_bytes", _up)
    monkeypatch.setattr(VS, "extract_document_text", _ler)
    tel = ESTRANHO if quem == "estranho" else CONVIDADO
    with open(FIXTURE, encoding="utf-8") as fh:
        corpo = copy.deepcopy(json.load(fh)["evento"])
    corpo["data"]["Info"].update({"Chat": f"{tel}@s.whatsapp.net", "Sender": f"{tel}@s.whatsapp.net",
                                  "IsFromMe": False, "IsGroup": False, "ID": "3EB0C0A0DOC00000000001"})
    corpo["data"]["Message"] = {"documentMessage": {"fileName": "apolice.pdf", "mimetype": "application/pdf"}}
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.rate_limit import limiter

    app = FastAPI()
    app.state.limiter = limiter
    app.include_router(w.router)
    r = TestClient(app).post(f"/api/v1/webhook/evolution-go/{TOKEN_CANAL}", json=corpo)
    assert r.status_code == 200
    if baixa:
        assert chamadas["download"] >= 1
    else:
        assert chamadas == {"download": 0, "upload": 0, "leitura": 0}
        assert r.json() == {"status": "ignored", "reason": "canal_nao_convidado"}


# =====================================================================================================================
# 7 — a palavra de saída e a retenção
# =====================================================================================================================
@pytest.mark.parametrize("fala", ["desisto, apaga meus dados", "parar", "Sair!", "não quero mais"])
def test_7_palavra_de_saida_apaga_as_respostas(efeitos, fala):
    from app.services.canal.conversa import FRASE_PAROU

    est = {"versao": 1, "etapa": "nascimento", "consentimento": "sim", "consentimento_em": "2026-10-07T10:00:00+00:00",
           "run_id": "run-1", "respostas": {"cpf": CPF, "nome": "Pessoa Sintetica"}, "midias": [{"ref": "x"}]}
    r = _responder(fala, est)
    assert r.baloes == [FRASE_PAROU] and r.estado["etapa"] == "parou"
    assert set(r.estado) <= {"versao", "etapa", "consentimento", "consentimento_em", "parou_em"}, r.estado
    assert efeitos["cancel"] == ["run-1"]


def test_7_controle_sair_dentro_de_uma_resposta_nao_e_saida(efeitos):
    est = {"etapa": "aplicativo", "consentimento": "sim", "respostas": {"placa": "ABC1D23", "cep": "01001000"}}
    r = _responder("não, uso só pra sair no fim de semana", est)
    assert r.estado["etapa"] == "km_mensal" and r.estado["respostas"]["aplicativo"] is False


def test_7_retencao_conversa_parada_perde_as_respostas(efeitos):
    from app.services.canal import conversa

    agora = datetime.fromisoformat(conversa._agora_iso())
    est = {"versao": 1, "etapa": "nascimento", "consentimento": "sim", "respostas": {"cpf": CPF},
           "atualizado_em": (agora - timedelta(days=31)).isoformat()}
    r = _responder("01/02/1980", dict(est))
    assert r.estado["etapa"] == "consentimento" and not _tem_cpf(json.dumps(r.estado))
    # controle: 29 dias → a conversa segue de onde parou (e o relógio da retenção é carimbado)
    r = _responder("01/02/1980", dict(est, atualizado_em=(agora - timedelta(days=29)).isoformat()))
    assert r.estado["etapa"] == "sexo" and _tem_cpf(json.dumps(r.estado)) and r.estado["atualizado_em"]


# =====================================================================================================================
# 8 — a cotação que não começou não gasta o limite; o aviso de falha conta no teto
# =====================================================================================================================
@pytest.mark.parametrize("comeca", [False, True], ids=["nao_comecou", "controle_comecou"])
def test_8_a_cotacao_que_nao_comecou_nao_conta_no_limite(fio, monkeypatch, comeca):
    from app.services.canal.cotacao import FRASE_SEM_COMECAR

    f = fio
    if not comeca:
        monkeypatch.setattr(f.cotacao, "adesoes_ativas_do_canal", lambda *_a, **_k: [])
    saidas = []
    for fala in ["oi", "sim", *FALAS]:
        saidas += f.falar(fala)
    cotacoes = f.repo.cotacoes_de_hoje(f.db, f.m.canal, CONVIDADO)
    enviadas = f.repo.enviadas_hoje(f.db, f.m.canal, CONVIDADO)
    assert enviadas == len(saidas)                                        # tudo o que saiu foi contado
    if comeca:
        assert cotacoes == 1
    else:
        assert cotacoes == 0 and saidas[-1] == FRASE_SEM_COMECAR


# =====================================================================================================================
# 9 — o nome do canal vem da config em `cotacao.py`
# =====================================================================================================================
def test_9_o_nome_do_canal_na_cotacao_vem_da_config(monkeypatch):
    from app.services.canal import cotacao
    from app.services.multicalculo import config as CFG

    assert "Quem Cobra Menos" not in (BACKEND / "app" / "services" / "canal" / "cotacao.py").read_text(encoding="utf-8")
    avisos = []

    async def _avisar(db, company_id, texto, rotulo):
        avisos.append(texto)
        return True

    monkeypatch.setattr(cotacao, "_avisar", _avisar)
    monkeypatch.setattr(CFG, "carregar", lambda cid, db: CFG.mesclar({"canal": {"nome": "Canal Ficticio"}}))
    asyncio.run(cotacao.pedir_ajuda_humana(None, CID, TEL, {"primeiro_nome": "Pessoa"}, motivo="teste"))
    assert avisos and avisos[0].startswith("Canal Ficticio —")
    # controle: config ilegível → o padrão do produto (o aviso não deixa de sair)
    def _quebra(cid, db):
        raise CFG.ConfigIndisponivel("simulado")
    monkeypatch.setattr(CFG, "carregar", _quebra)
    asyncio.run(cotacao.pedir_ajuda_humana(None, CID, TEL, {}, motivo="teste"))
    assert avisos[1].startswith(CFG.PADRAO_DO_PRODUTO["canal"]["nome"] + " —")


# =====================================================================================================================
# P6 do red team — o lembrete não apaga a resposta que chegou enquanto ele saía
# =====================================================================================================================
def test_17_lembrete_nao_apaga_o_quero_fechar_que_chegou_no_meio(mundo, canal, monkeypatch):
    import app.services.canal as pacote
    from test_spec133a_a_conversa import TEL as TEL_DO_MUNDO

    m, c = mundo, canal
    run_id = _ate_o_resultado(m, c)
    original = pacote.envio.enviar

    async def _enviar_e_a_pessoa_responde(db, company_id, tel, baloes):
        n = await original(db, company_id, tel, baloes)
        est = c.repo.carregar_estado(db, company_id, tel)
        c.repo.salvar_estado(db, company_id, tel, dict(est, etapa="passado"))   # o "quero fechar" no meio
        return n

    monkeypatch.setattr(pacote.envio, "enviar", _enviar_e_a_pessoa_responde)
    assert acordar(m.banco, m.db, run_id)
    asyncio.run(rodar_o_run(m.db, run_id, m.canal))
    est = c.repo.carregar_estado(m.db, m.canal, TEL_DO_MUNDO)
    assert est["etapa"] == "passado" and est["lembretes"] == 1

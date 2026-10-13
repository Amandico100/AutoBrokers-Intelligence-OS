# -*- coding: utf-8 -*-
"""SPEC-131-A · O TESTE DO FIO — do tick ao aviso, numa corretora com 5 renovações sintéticas.

    intelligence/tick.py (REAL, relógio na janela da corretora) → Work Run `renov:<passo>:<company>:<dia>` (RPC
    `work_run_create` com o MESMO corpo do banco) → SmithWorker._processar (REAL) → madrugada.workflow_* (REAL)
      00:30 preparar   FonteInfocap.renovacoes_cruas REAL (dublê SÓ do `urlopen`) → upsert (renovacao.py REAL)
                       → dono.dono_da_apolice REAL (/prod_docs na rede dublê, vínculo REAL) → ficha (DUBLÊ: é a
                       InfoCap HTTP do detalhe) → de_apolice (DUBLÊ pelo CONTRATO da SPEC §5: AUTO/RE → pedido;
                       VIND → RamoIndisponivel('ramo_nao_cotado'); sigla desconhecida → RamoIndisponivel('ramo_desconhecido'))
      02:00 calcular   madrugada.calcular_na_porta REAL → porta (DUBLÊ da classe, contrato F3: grava pedido + cálculos)
                       → `calculando` → DORME (espera durável 129-A) → o "motor" fecha os cálculos com ofertas →
                       o despertador REAL acorda → releitura DERIVA `calculada`
      05:30 conferir   conferencia_da_renovacao REAL (relê a InfoCap) → renovacao_dias
      06:15 desvio     nada a desviar
      06:45 avisar     briefing_service.publicar REAL (o canal in-app que JÁ existe; entrega SÓ no painel) →
                       1 aviso por dono + 1 da corretora

Ao fim: 3 `calculada`, 2 `pendente` com motivo, completude 100 %, `renovacao_dias` gravado, 1 aviso por dono — e a
LENTE DO DADO reconfere a completude por contagem independente (as linhas da InfoCap dublê × as ofertas gravadas).

⛔ Dados sintéticos e óbvios: corretora_a/b, "CLIENTE FICTICIO DE TESTE", documento 000.000.000-00, nosnum 9100xx.
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec131a_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ⚠️ importados ANTES do relógio do mundo (um módulo importado com o relógio instalado guarda a classe parada)
import app.services.intelligence.signal_service  # noqa: E402,F401
import app.services.intelligence.tick as TICK  # noqa: E402
import app.services.multicalculo.conferencia_da_renovacao as CONF  # noqa: E402
import app.services.multicalculo.madrugada as M  # noqa: E402
import app.services.multicalculo.porta as PORTA  # noqa: E402
import app.services.multicalculo.renovacao as R  # noqa: E402
import app.services.work.runs  # noqa: E402,F401
import app.services.work.workflows as WF  # noqa: E402
import app.workers.smith_worker as SW  # noqa: E402

import dubles_do_work_os as D  # noqa: E402
import test_spec1310_f2_dono as F2  # noqa: E402
from dubles.banco_multicalculo import COMPANIES_U1, ESQUEMA_U1  # noqa: E402
from app.services.multicalculo import pedido as P  # noqa: E402
from app.services.sistema_de_gestao import dono as DONO  # noqa: E402

CHAVE_HMAC = "chave-hmac-de-teste-131a"
FUSO = "America/Sao_Paulo"
DIA = date(2026, 10, 13)
DOCUMENTO_SINTETICO = "000.000.000-00"

# ---------------------------------------------------------------------------------------------------------------------
# O ESQUEMA — o retrato da migration 20261013_01 (colunas + travas que o código pode violar)
# ---------------------------------------------------------------------------------------------------------------------
U = ("uuid", False, None)
UN = ("uuid", True, None)
TN = ("text", True, None)
TS = ("ts", False, "NOW")
ESQUEMA_131A = {
    "renovacoes": {
        "id": ("uuid", False, "UUID"), "company_id": U, "sistema": ("text", False, "infocap"),
        "codfil": ("int", False, 1), "nosnum": ("text", False, None), "fimvig": ("text", False, None),
        "ramo_sigla": TN, "ramo_agger": ("int", True, None), "seguradora_atual": TN, "premio_atual": ("num", True, None),
        "cliente_nome_curto": TN, "documento_mascarado": TN, "documento_hmac": TN, "dono_user_id": UN,
        "dono_motivo": TN, "responsavel_user_id": UN, "estado": ("text", False, "listada"), "motivo": TN,
        "pedido_id": UN, "conta_agger_id": UN, "conta_motivo": TN, "proposta_ref": TN, "calcular_em": TN,
        "canario": ("bool", False, False), "criado_em": TS, "atualizado_em": TS, "versao": ("int", False, 1),
    },
    "renovacao_eventos": {
        "id": ("uuid", False, "UUID"), "company_id": U, "renovacao_id": U, "de": TN, "para": ("text", False, None),
        "por": ("text", False, None), "motivo": TN, "dados": ("jsonb", False, "JSON:{}"), "criado_em": TS,
    },
    "renovacao_dias": {
        "company_id": U, "dia": ("text", False, None), "estado": ("text", False, None),
        "esperadas": ("int", True, None), "calculadas": ("int", True, None), "pendentes": ("int", True, None),
        "falharam": ("int", True, None), "faltaram": ("int", True, None), "completude_pct": ("num", True, None),
        "cotaveis": ("int", True, None), "calculadas_de_cotaveis_pct": ("num", True, None),
        "detalhes": ("jsonb", False, "JSON:{}"), "atualizado_em": TS,
    },
    "membro_ausencias": {
        "id": ("uuid", False, "UUID"), "company_id": U, "user_id": U, "substituto_user_id": U,
        "de": ("text", False, None), "ate": ("text", False, None), "criado_por": UN, "criado_em": TS,
    },
}
#: a migration acrescenta no pedido
COLUNAS_DO_PEDIDO = {"politica_de_sessao": TN, "renovacao_id": UN}
OPCOES_DO_PEDIDO = ("padrao", "economica", "completa_mais", "minima", "anterior", "franquia_reduzida")
OPCOES_DO_CALCULO = OPCOES_DO_PEDIDO + ("ajuste",)


class BancoDaMadrugada(F2.BancoF2):
    """As travas da 20261013_01 (e as do multicálculo que a porta dublê pode violar) — a mesma semântica do SQL."""

    def _travas(self, tabela, nova, velha):
        super()._travas(tabela, nova, velha)
        if tabela == "renovacoes":
            self._check("ck_renovacoes_estado", nova["estado"] in R.ESTADOS_LIGADOS + R.ESTADOS_RESERVADOS)
            self._check("ck_renovacoes_motivo", nova["estado"] not in ("pendente", "falhou", "perdida")
                        or bool(str(nova.get("motivo") or "").strip()))
            doc = nova.get("documento_mascarado")
            self._check("ck_renovacoes_documento_mascarado",
                        doc is None or sum(ch.isdigit() for ch in str(doc)) <= 2)
            nome = nova.get("cliente_nome_curto")
            self._check("ck_renovacoes_nome_curto", nome is None or (" " not in str(nome) and len(str(nome)) <= 40))
            self._unico(tabela, "uq_renovacoes_item", ("company_id", "sistema", "codfil", "nosnum", "fimvig"),
                        nova, velha)
            self._fk(tabela, "fk_renovacoes_pedido", (("pedido_id", "id"), ("company_id", "company_id")),
                     "multicalculo_pedidos", nova)
        elif tabela == "renovacao_eventos":
            self._fk(tabela, "fk_renovacao_eventos_renovacao", (("renovacao_id", "id"), ("company_id", "company_id")),
                     "renovacoes", nova)
        elif tabela == "renovacao_dias":
            self._unico(tabela, "renovacao_dias_pkey", ("company_id", "dia"), nova, velha)
            self._check("ck_renovacao_dias_estado", nova["estado"] in ("completo", "incompleto", "vermelho",
                                                                      "sem_conexao"))
            self._check("ck_renovacao_dias_sem_conexao_sem_zero", nova["estado"] != "sem_conexao"
                        or (nova.get("esperadas") is None and nova.get("completude_pct") is None))
        elif tabela == "membro_ausencias":
            self._check("ck_membro_ausencias_outra_pessoa", nova["user_id"] != nova["substituto_user_id"])
        elif tabela == "multicalculo_pedidos":
            self._check("ck_mc_pedidos_opcoes", bool(nova["opcoes"]) and set(nova["opcoes"]) <= set(OPCOES_DO_PEDIDO))
            self._check("ck_mc_pedidos_politica_de_sessao", nova.get("politica_de_sessao") in (None, "madrugada"))
            self._fk(tabela, "fk_mc_pedidos_renovacao", (("renovacao_id", "id"), ("company_id", "company_id")),
                     "renovacoes", nova)
        elif tabela == "multicalculo_calculos":
            self._check("ck_mc_calculos_opcao", nova["opcao"] in OPCOES_DO_CALCULO)


def instalar(monkeypatch):
    for tabela, cols in F2.ESQUEMA_F2.items():
        monkeypatch.setitem(D.ESQUEMA, tabela, cols)
    for tabela, cols in ESQUEMA_131A.items():
        monkeypatch.setitem(D.ESQUEMA, tabela, cols)
    for tabela, cols in ESQUEMA_U1.items():
        monkeypatch.setitem(D.ESQUEMA, tabela, dict(cols))
    monkeypatch.setitem(D.ESQUEMA, "multicalculo_pedidos", {**ESQUEMA_U1["multicalculo_pedidos"], **COLUNAS_DO_PEDIDO})
    monkeypatch.setitem(D.ESQUEMA, "companies", {**D.ESQUEMA["companies"], **COMPANIES_U1})


# ---------------------------------------------------------------------------------------------------------------------
# As BORDAS
# ---------------------------------------------------------------------------------------------------------------------
def ramo_indisponivel(motivo: str) -> Exception:
    """`RamoIndisponivel` pelo CONTRATO (F2): `motivo ∈ {ramo_nao_cotado, ramo_desconhecido}`."""
    try:
        exc = P.RamoIndisponivel(motivo)
    except TypeError:       # se a F2 mudar a assinatura para só-nomeada
        exc = P.RamoIndisponivel(motivo=motivo)  # type: ignore[call-arg]
    exc.motivo = motivo
    return exc


RAMO_DO_AGGER = {"AUTO": 31, "RESI": 2, "COND": 16, "EMPR": 18}


def de_apolice_pelo_contrato(apolice, *, ficha, config):
    sigla = str(getattr(apolice, "ramo", "") or "").upper()
    if sigla in RAMO_DO_AGGER:
        return SimpleNamespace(ramo=RAMO_DO_AGGER[sigla], sigla=sigla)
    if sigla in ("VIND", "VGRP", "VIAG"):
        raise ramo_indisponivel("ramo_nao_cotado")
    raise ramo_indisponivel("ramo_desconhecido")


class PortaDuble:
    """A classe da porta pelo CONTRATO da SPEC §5 (F3). Grava o pedido e um cálculo por opção, `na_fila` —
    o "motor" (`fechar_com_ofertas`) os fecha depois. Guarda cada chamada para o teste conferir o que CHEGOU."""

    chamadas: list = []
    banco = None

    def __init__(self, *a, **k):
        pass

    async def calcular(self, *, company_id, pedido, opcoes, servico, dono_user_id=None, vence_em_dias=None,
                       prioridade=None, politica_de_sessao=None, renovacao_id=None, forcar_corretora_motivo=None,
                       **_resto):
        PortaDuble.chamadas.append(dict(company_id=company_id, opcoes=list(opcoes), servico=servico,
                                        dono_user_id=dono_user_id, vence_em_dias=vence_em_dias, prioridade=prioridade,
                                        politica_de_sessao=politica_de_sessao, renovacao_id=renovacao_id,
                                        forcar_corretora_motivo=forcar_corretora_motivo,
                                        ramo=getattr(pedido, "ramo", None)))
        b = PortaDuble.banco
        pid = str(uuid.uuid4())
        b.semear("multicalculo_pedidos", {"id": pid, "company_id": company_id, "origem": "auxiliar",
                                          "ramo": getattr(pedido, "ramo", 31), "opcoes": list(opcoes),
                                          "corretoras": [company_id], "pedido_cifrado": "cifrado-de-teste",
                                          "servico": servico, "politica_de_sessao": politica_de_sessao,
                                          "renovacao_id": renovacao_id})
        calcs = []
        for o in opcoes:
            cid = str(uuid.uuid4())
            b.semear("multicalculo_calculos", {"id": cid, "pedido_id": pid, "solicitante_company_id": company_id,
                                               "company_id": company_id, "opcao": o, "coberturas": {},
                                               "prioridade": prioridade or 5})
            calcs.append({"id": cid, "corretora_company_id": company_id, "opcao": o})
        return PORTA.PedidoAberto(pedido_id=pid, calculos=tuple(calcs))


def fechar_com_ofertas(banco, pedido_ids, *, sem_oferta=()):
    """O MOTOR (dublê da borda Agger): fecha cada cálculo e grava 1 oferta (ou nenhuma) — como o motor deixaria."""
    for c in banco.linhas("multicalculo_calculos"):
        if str(c["pedido_id"]) not in {str(p) for p in pedido_ids}:
            continue
        c.update({"status": "fechado", "negocio_ref": f"negocio-{c['id'][:8]}", "versao": 1,
                  "fechado_em": banco.relogio.iso(), "batida_em": banco.relogio.iso()})
        if str(c["pedido_id"]) in {str(p) for p in sem_oferta}:
            continue
        banco.semear("multicalculo_ofertas", {"calculo_id": c["id"], "pedido_id": c["pedido_id"],
                                              "company_id": c["company_id"],
                                              "solicitante_company_id": c["solicitante_company_id"],
                                              "seguradora": "SEGURADORA FICTICIA", "seguradora_codigo": 1,
                                              "pacote": c["opcao"], "tipo_de_pacote": 1, "premio_total": 1000.0})


# ---------------------------------------------------------------------------------------------------------------------
# O MUNDO
# ---------------------------------------------------------------------------------------------------------------------
def br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def local(h: int, m: int, dia: date = DIA) -> datetime:
    from zoneinfo import ZoneInfo

    return datetime(dia.year, dia.month, dia.day, h, m, tzinfo=ZoneInfo(FUSO)).astimezone(timezone.utc)


def linha_renov(nosnum: int, ramo: str, fimvig: date) -> dict:
    linha = F2.renov(nosnum)
    linha.update({"ramo": ramo, "fimvig": br(fimvig), "seguradora": "SEGURADORA FICTICIA", "pretot": 1234.5,
                  "cic": DOCUMENTO_SINTETICO, "cliente": "CLIENTE FICTICIO DE TESTE"})
    return linha


class Corretora(SimpleNamespace):
    pass


def montar_corretora(m, token: str, *, renovacoes: list, ligada: bool = True) -> Corretora:
    """Uma corretora com o aplicativo ligado, dois donos vinculados por código de produtor e um admin."""
    cid = str(uuid.uuid4())
    m.banco.semear("companies", {"id": cid, "company_kind": "client", "company_name": f"Corretora {token}",
                                 "is_technical": False})
    if ligada:
        m.banco.semear("tenant_auxiliaries", {"company_id": cid, "slug": "renovacao", "status": "active"})
    donos = []
    for i, papel in enumerate(("member", "member", "admin_company")):
        uid = str(uuid.uuid4())
        m.banco.semear("users_v2", {"id": uid, "first_name": f"Pessoa{i}", "last_name": "Teste"})
        m.banco.semear("company_members", {"user_id": uid, "company_id": cid, "role": papel})
        donos.append(uid)
    fonte = m.rede.fonte(cid, token)
    m.fontes[cid] = fonte
    m.rede.bancos[token]["renov"] = renovacoes
    codigos = {}
    for k, (linha, dono_idx) in enumerate(renovacoes_com_dono(renovacoes)):
        codpro = 500 + dono_idx
        m.rede.bancos[token]["prod_docs"][(1, int(linha["nosnum"]))] = F2._quatro_produtores(
            int(linha["nosnum"]), dono_codpro=codpro, dono_nome=f"{codpro} - PESSOA {dono_idx} FECHADORA")
        codigos[dono_idx] = codpro
    for dono_idx, codpro in codigos.items():
        DONO.vincular(m.db, cid, user_id=donos[dono_idx], sistema="infocap", codfil=1, codigo_produtor=codpro)
    return Corretora(id=cid, token=token, dono1=donos[0], dono2=donos[1], admin=donos[2], fonte=fonte)


def renovacoes_com_dono(renovacoes):
    """A COND é da pessoa 1; o resto, da pessoa 0."""
    return [(r, 1 if r["ramo"] == "COND" else 0) for r in renovacoes]


def cinco_renovacoes(base: int = 910000, fimvig: date = DIA + timedelta(days=10)) -> list:
    return [linha_renov(base + 1, "AUTO", fimvig), linha_renov(base + 2, "RESI", fimvig),
            linha_renov(base + 3, "COND", fimvig), linha_renov(base + 4, "VIND", fimvig),
            linha_renov(base + 5, "XYZW", fimvig)]


@pytest.fixture
def mundo(monkeypatch):
    instalar(monkeypatch)
    DONO._padrao_bruto.cache_clear()
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", CHAVE_HMAC)
    monkeypatch.setenv("INTELLIGENCE_TICK", "1")
    relogio = D.Relogio(local(0, 31))
    banco = BancoDaMadrugada(relogio)
    m = SimpleNamespace(banco=banco, relogio=relogio, db=banco.visao("smith-worker"), fontes={},
                        rede=F2.InfocapNaRede(monkeypatch))

    async def abrir_fonte(_db, company_id):
        if company_id not in m.fontes:
            raise RuntimeError("corretora sem InfoCap")
        return m.fontes[company_id]

    monkeypatch.setattr(DONO, "abrir_fonte", abrir_fonte)

    async def ficha(_db, _cid, item, _fonte):
        return SimpleNamespace(ramo=item.get("ramo_sigla")), SimpleNamespace(objeto_do_risco={})

    monkeypatch.setattr(M, "ficha_da_apolice", ficha)
    monkeypatch.setattr(M, "de_apolice", de_apolice_pelo_contrato)
    PortaDuble.chamadas = []
    PortaDuble.banco = banco
    monkeypatch.setattr(PORTA, "MulticalculoProvider", PortaDuble)
    relogio.instalar()
    relogio.cobrir(M, CONF, R, TICK)
    yield m
    relogio.desinstalar()
    DONO._padrao_bruto.cache_clear()


# ---------------------------------------------------------------------------------------------------------------------
# O Work OS real
# ---------------------------------------------------------------------------------------------------------------------
def tick(m, quando: datetime) -> dict:
    m.relogio._t = quando
    return TICK.IntelligenceTick(m.db).executar(agora=quando)


def runs_da_renovacao(m, company_id=None) -> list:
    return [r for r in m.banco.linhas("work_runs") if str(r.get("workflow_key", "")).startswith("renovacao.")
            and (company_id is None or r["company_id"] == company_id)]


def run_do_passo(m, company_id, passo) -> dict:
    (r,) = [x for x in runs_da_renovacao(m, company_id) if x["workflow_key"] == f"renovacao.{passo}"]
    return r


def rodar(m, run_id: str, company_id: str) -> None:
    """Uma volta do worker REAL: lease (CAS) → `SmithWorker._processar` (o contexto real) → libera a lease."""
    from app.services.work.runs import WorkRunService

    async def _volta():
        w = SW.SmithWorker()
        w.db, w.worker_id = m.db, "worker-de-teste"
        w.runs = WorkRunService(m.db)
        lease = w.runs.adquirir_lease(run_id, w.worker_id, company_id)
        assert lease, f"o run {m.banco.run(run_id).get('workflow_key')} não pegou lease ({m.banco.run(run_id).get('status')})"
        try:
            await w._processar(run_id, company_id, {"run_id": run_id}, lease_token=lease["lease_token"])
        finally:
            w.runs.liberar_lease(run_id, lease["lease_token"])

    asyncio.run(_volta())


def acordar(m, run_id: str) -> list:
    """O relógio anda até o `wake_at` + 30 s e o despertador REAL roda com o registro do worker."""
    from app.services.work.runs import WorkRunService

    wake = D._para_ts(m.banco.run(run_id).get("wake_at"))
    assert wake is not None, "o run não dormiu"
    m.relogio.avancar(max(0.0, (wake - m.relogio.agora()).total_seconds()) + 30)
    return WorkRunService(m.db).despertar_vencidos(SW.SmithWorker()._registro_de_workflows())


def itens(m, company_id) -> list:
    return [x for x in m.banco.linhas("renovacoes") if x["company_id"] == company_id]


def publicacoes(m, company_id, assunto) -> list:
    """Os avisos pelo canal in-app que já existe: as publicações do briefing (`briefing_publications`)."""
    return [p for p in m.banco.linhas("briefing_publications") if p["company_id"] == company_id
            and R.assunto_da_publicacao(p) == assunto]


def avisos(m, company_id) -> list:
    return publicacoes(m, company_id, "avisar")


def madrugada_inteira(m, c, *, motor=True) -> None:
    """O dia todo, passo a passo, pelo tick e pelo worker reais."""
    tick(m, local(0, 31))
    rodar(m, run_do_passo(m, c.id, "preparar")["id"], c.id)
    tick(m, local(2, 1))
    calc = run_do_passo(m, c.id, "calcular")
    rodar(m, calc["id"], c.id)
    if motor:
        pedidos = [x["pedido_id"] for x in itens(m, c.id) if x.get("pedido_id")]
        fechar_com_ofertas(m.banco, pedidos)
        if m.banco.run(calc["id"]).get("status") == "waiting_input":
            acordar(m, calc["id"])
            rodar(m, calc["id"], c.id)
    tick(m, local(5, 31))
    rodar(m, run_do_passo(m, c.id, "conferir")["id"], c.id)
    tick(m, local(6, 16))
    rodar(m, run_do_passo(m, c.id, "desvio")["id"], c.id)
    tick(m, local(6, 46))
    rodar(m, run_do_passo(m, c.id, "avisar")["id"], c.id)


# =====================================================================================================================
# 🔴 O TESTE DO FIO
# =====================================================================================================================
def test_o_fio_do_tick_ao_aviso(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())

    # 00:31 — o tick enfileira SÓ o preparar; dois ticks no mesmo minuto = UM run
    tick(m, local(0, 31))
    tick(m, local(0, 31))
    assert [r["workflow_key"] for r in runs_da_renovacao(m, c.id)] == ["renovacao.preparar"]
    prep = run_do_passo(m, c.id, "preparar")
    assert prep["idempotency_key"] == f"renov:preparar:{c.id}:{DIA.isoformat()}"
    rodar(m, prep["id"], c.id)
    assert m.banco.run(prep["id"])["status"] == "completed", m.banco.run(prep["id"]).get("error_message")
    estados = sorted((x["ramo_sigla"], x["estado"], x.get("motivo")) for x in itens(m, c.id))
    assert estados == [("AUTO", "pronta", None), ("COND", "pronta", None), ("RESI", "pronta", None),
                       ("VIND", "pendente", "ramo_nao_cotado"), ("XYZW", "pendente", "ramo_desconhecido")]
    # o dono REAL (dono.dono_da_apolice sobre o /prod_docs) e o calcular_em = fimvig − 10
    por_sigla = {x["ramo_sigla"]: x for x in itens(m, c.id)}
    assert por_sigla["COND"]["dono_user_id"] == c.dono2 and por_sigla["AUTO"]["dono_user_id"] == c.dono1
    assert {x["calcular_em"] for x in itens(m, c.id)} == {DIA.isoformat()}
    # ⛔ nada em claro: documento só mascarado (≤ 2 dígitos) + HMAC; nome só o primeiro
    for x in itens(m, c.id):
        assert x["documento_mascarado"] == "***.***.***-00" and len(x["documento_hmac"]) == 64
        assert x["cliente_nome_curto"] == "Cliente"

    # 02:01 — calcular: a porta recebe o CONTRATO (renovação, prioridade 7, madrugada, renovacao_id), ordem (ramo, fimvig)
    tick(m, local(2, 1))
    calc = run_do_passo(m, c.id, "calcular")
    rodar(m, calc["id"], c.id)
    assert [ch["ramo"] for ch in PortaDuble.chamadas] == [2, 16, 31]
    for ch in PortaDuble.chamadas:
        assert (ch["servico"], ch["prioridade"], ch["politica_de_sessao"]) == ("renovacao", 7, "madrugada")
        assert ch["opcoes"] == ["anterior", "franquia_reduzida", "completa_mais"]
        assert ch["vence_em_dias"] == 10 and ch["renovacao_id"]
        assert "economica" not in ch["opcoes"] and "minima" not in ch["opcoes"]
    assert sorted(x["estado"] for x in itens(m, c.id)) == ["calculando"] * 3 + ["pendente"] * 2
    # a espera DURÁVEL: o run dorme (nenhum worker segura), e nada foi derivado por callback
    assert m.banco.run(calc["id"])["status"] == "waiting_input"
    fechar_com_ofertas(m.banco, [x["pedido_id"] for x in itens(m, c.id) if x.get("pedido_id")])
    assert acordar(m, calc["id"]), "o despertador real não acordou o calcular"
    rodar(m, calc["id"], c.id)
    assert m.banco.run(calc["id"])["status"] == "completed", m.banco.run(calc["id"]).get("error_message")
    assert sorted(x["estado"] for x in itens(m, c.id)) == ["calculada"] * 3 + ["pendente"] * 2

    # 05:31 conferir · 06:16 desvio · 06:46 avisar
    for hora, passo in (((5, 31), "conferir"), ((6, 16), "desvio"), ((6, 46), "avisar")):
        tick(m, local(*hora))
        r = run_do_passo(m, c.id, passo)
        rodar(m, r["id"], c.id)
        assert m.banco.run(r["id"])["status"] == "completed", (passo, m.banco.run(r["id"]).get("error_message"))
    assert len(runs_da_renovacao(m, c.id)) == 5

    (dia,) = [x for x in m.banco.linhas("renovacao_dias") if x["company_id"] == c.id]
    assert (dia["estado"], dia["esperadas"], dia["calculadas"], dia["pendentes"], dia["faltaram"]) == \
        ("completo", 5, 3, 2, 0)
    assert float(dia["completude_pct"]) == 100.0
    assert (dia["cotaveis"], float(dia["calculadas_de_cotaveis_pct"])) == (3, 100.0)

    # 1 aviso por dono + 1 da corretora, pelo canal que JÁ existe (o briefing, só no painel), só contagens
    por_pessoa = {}
    for s in avisos(m, c.id):
        por_pessoa.setdefault(s.get("user_id"), []).append(s)
    assert set(por_pessoa) == {c.dono1, c.dono2, None} and all(len(v) == 1 for v in por_pessoa.values())
    assert por_pessoa[c.dono1][0]["summary_text"].startswith("2 prontas no seu Agger · 2 pendentes (")
    assert por_pessoa[c.dono2][0]["summary_text"] == "1 prontas no seu Agger · 0 pendentes · 0 falharam"
    assert "CLIENTE" not in " ".join(s["summary_text"] for s in avisos(m, c.id)).upper()
    # ⛔ nada saiu do prédio: a entrega de cada aviso foi SÓ o painel
    for p in avisos(m, c.id):
        canais = [x["canal"] for x in (p.get("delivery_detail") or {}).get("canais", [])]
        assert canais == ["dashboard"], canais

    # cada transição tem a sua linha de evento (de, para, por)
    for x in itens(m, c.id):
        evs = [e for e in m.banco.linhas("renovacao_eventos") if e["renovacao_id"] == x["id"]]
        cadeia = [e["para"] for e in evs]
        assert cadeia[0] == "listada" and evs[0]["de"] is None
        assert cadeia[-1] == x["estado"]
        assert all(e["de"] == a["para"] for a, e in zip(evs, evs[1:]))

    # 🔬 A LENTE DO DADO: a completude reconferida por um caminho INDEPENDENTE do que a produziu —
    # as linhas que a InfoCap dublê SERVE (não a tabela) × as ofertas que o "motor" gravou × os pendentes com motivo
    servidas = {(1, str(r["nosnum"])) for r in m.rede.bancos["token-a"]["renov"] if r["tipdoc"] == "A"}
    pedidos_com_oferta = {o["pedido_id"] for o in m.banco.linhas("multicalculo_ofertas")
                          if o["solicitante_company_id"] == c.id}
    feitas = {(1, x["nosnum"]) for x in itens(m, c.id) if x.get("pedido_id") in pedidos_com_oferta}
    com_motivo = {(1, x["nosnum"]) for x in itens(m, c.id) if x["estado"] == "pendente" and x.get("motivo")}
    assert feitas.isdisjoint(com_motivo)
    assert round(100.0 * len((feitas | com_motivo) & servidas) / len(servidas), 2) == float(dia["completude_pct"])


def test_o_fio_nasce_vermelho_sem_o_registro(mundo, monkeypatch):
    """CONTROLE do fio: sem a madrugada no registro do Work OS, o run do tick morre `workflow_desconhecido` — o fio
    depende do registro, e não de um atalho."""
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes())
    tick(m, local(0, 31))
    prep = run_do_passo(m, c.id, "preparar")
    monkeypatch.setattr(WF, "resolver_workflow", lambda chave: None)
    rodar(m, prep["id"], c.id)
    assert m.banco.run(prep["id"])["error_code"] == "workflow_desconhecido"
    assert itens(m, c.id) == []


def test_sem_o_aplicativo_ligado_nada_e_enfileirado(mundo):
    m = mundo
    c = montar_corretora(m, "token-a", renovacoes=cinco_renovacoes(), ligada=False)
    for h, mi in ((0, 31), (2, 1), (5, 31), (6, 16), (6, 46)):
        tick(m, local(h, mi))
    assert runs_da_renovacao(m, c.id) == []

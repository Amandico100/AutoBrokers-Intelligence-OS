# -*- coding: utf-8 -*-
"""SPEC-129-B F3 — O MOTOR do multicálculo (U4): o fio e os gates G4 G6 G8 G10 G14.

O MOTOR é REAL (`portal_worker/multicalculo/motor.py` + `robos.py` + `main.iniciar_lacos`); o dublê fica
SÓ na borda (CLAUDE.md §9.4):

    o banco      `dubles_do_work_os.BancoEmMemoria` (o PostgREST: CAS que devolve só a linha que casou,
                 filtros com a semântica do SQL) + o esquema do U1 da SPEC e as travas dele (CHECKs,
                 FKs compostas, `unique(calculo_id, chave)`, `unique` da oferta)
    o Agger      `MundoAgger` — o portal: conta os `calcularV2`, guarda o cursor de cada negócio/versão
                 (a resposta do GET só cresce), serve as rodadas REAIS da fixture `vivo_conta_b.json`
    o robô       `RoboDuble`/`SessoesDuble` — obedecem EXATAMENTE a §6.4 (assinaturas e exceções) e
                 narram pelo `leitor_agger` REAL (`ler_rodada` + `eventos_entre`)
    o upload     um coletor no lugar do `_upload_portal_blob` (o storage é borda)

    cd backend && .venv/Scripts/python -m pytest tests/test_spec129b_o_motor.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

RAIZ = Path(__file__).resolve().parents[1]
for _p in (str(RAIZ), str(RAIZ / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dubles_do_work_os as D  # noqa: E402
from portal_worker import main as MAIN  # noqa: E402
from portal_worker import worker as W  # noqa: E402
from portal_worker.multicalculo import leitor_agger as L  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import robos as ROB  # noqa: E402
from portal_worker.multicalculo.contrato import Ajuste  # noqa: E402

FIXTURE = json.loads((RAIZ / "tests/fixtures/agger/vivo_conta_b.json").read_text(encoding="utf-8"))
SERVIR = {"padrao": 0, "economica": 1, "ajuste": 2}   # qual cálculo da fixture o Agger responde

# Dados FICTÍCIOS — e a varredura procura cada um deles no banco e no log.
SENHA = "Senha-Do-Robo-Ficticia-9x7"
CPF = "52998224725"
NOME = "Fulana Ficticia de Teste"
PEDIDO = {"ramo": 31, "segurado": {"cpf_cnpj": CPF, "nome": NOME, "cep": "01001000"},
          "veiculo": {"fipe": "0010001", "placa": "ABC1D23"}}

T0 = datetime(2026, 10, 6, 13, 0, tzinfo=timezone.utc)   # terça, 10:00 em Brasília


def rodadas(idx: int):
    return [L.ler_rodada(r) for r in FIXTURE["calculos"][idx]["rodadas"]]


# ═════════════════════════════════════════════════════════════════════════════
# O banco: o esquema do U1 (os nomes são LEI) e as travas dele
# ═════════════════════════════════════════════════════════════════════════════
from dubles.banco_multicalculo import (  # noqa: E402  (F4: o banco dublê é UM, comum ao teste do fio)
    COLUNAS_ROBO, ESQUEMA_U1, FK_DO_CALCULO, STATUS, BancoU1, instalar_esquema,
)


@pytest.fixture
def ambiente(monkeypatch):
    from cryptography.fernet import Fernet

    instalar_esquema(monkeypatch)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    for nome in ("MULTICALCULO_TETO_CORRETORA_HORA", "MULTICALCULO_TETO_GERAL_HORA", "AUTOBROKERS_CANARIO"):
        monkeypatch.delenv(nome, raising=False)
    from portal_worker import leases

    monkeypatch.setattr(leases, "redis_disponivel", lambda *a, **k: False)   # nunca pinga Redis de verdade
    relogio = D.Relogio(T0)
    banco = BancoU1(relogio)
    return SimpleNamespace(banco=banco, relogio=relogio, mundo=MundoAgger())


# ═════════════════════════════════════════════════════════════════════════════
# O Agger (o mundo de fora) e o robô dublê — EXATAMENTE a §6.4
# ═════════════════════════════════════════════════════════════════════════════
class SessaoOcupada(Exception):
    pass


class CredencialRecusada(Exception):
    pass


class DisparoIncerto(Exception):
    pass


class DisparoRecusado(Exception):
    def __init__(self, motivo: str = ""):
        super().__init__(motivo)
        self.motivo = motivo


@dataclass(frozen=True)
class Disparo:
    negocio_ref: str
    versao: int
    t0: float


SESSAO_MOD = SimpleNamespace(SessaoOcupada=SessaoOcupada, CredencialRecusada=CredencialRecusada)


class MundoAgger:
    def __init__(self):
        self.posts = []                 # (conta_id, negocio_ref, versao, preset) — cada `calcularV2`
        self.versoes = {}               # negocio_ref → última versão
        self.servir = {}                # (ref, versao) → índice do cálculo da fixture
        self.cursor = {}                # (ref, versao) → próxima rodada (o GET só cresce)
        self.emitidos = []              # (processo, (ref, versao), identidade) — o que o robô NARROU
        self.entregues = []             # (processo, (ref, versao), identidade) — o `ao_evento` VOLTOU (gravou)
        self.abertas = {}               # conta_id → {processo} com sessão aberta AGORA
        self.max_abertas = {}
        self.obter = []                 # (processo, conta_id)
        self.senhas = []
        self.login = {}                 # conta_id → exceção do login
        self.falha_disparo = {}         # preset → exceção
        self.matar_no_disparo = None    # preset: o POST sai e o processo morre antes do checkpoint
        self.matar_em = None            # ((ref, versao), i): morre depois de servir a rodada i
        self.mexeu = False
        self.consultas_mexeu = []
        self.recalculos = []
        self.ocupacao_s = 0.0
        self.em_acompanhamento = {}     # conta_id → n
        self.max_contas_simultaneas = 0
        self.anteriores = []            # ((ref, versao), anterior is None)
        self.pdfs_falham = False
        self.uploads = []


def _identidade(e) -> tuple:
    o = e.oferta
    return (e.tipo, e.seguradora_codigo, e.familia,
            o.pacote if o else None, o.tipo_de_pacote if o else None, round(o.premio_total, 2) if o else None)


class SessaoDuble:
    def __init__(self, conta_id, negocios):
        self.conta_id = conta_id
        self.negocios = set(negocios)
        self._posts = 0

    def registrar_negocio(self, negocio_ref):
        self.negocios.add(negocio_ref)

    def contagem_de_escritas(self):
        return {"calcularV2": self._posts, "barradas": 0}


class SessoesDuble:
    def __init__(self, mundo: MundoAgger, processo: str, navegador=None, *, url_base="https://aggilizador.com.br"):
        self.m, self.processo, self._s = mundo, processo, {}

    async def obter(self, conta, *, senha, negocios_do_robo):
        assert "secret_encrypted" not in conta, "a sessão nunca recebe o segredo cifrado"
        self.m.obter.append((self.processo, conta["id"]))
        self.m.senhas.append(senha)
        exc = self.m.login.get(conta["id"])
        if exc is not None:
            raise exc()
        if conta["id"] not in self._s:
            self._s[conta["id"]] = SessaoDuble(conta["id"], negocios_do_robo)
            ab = self.m.abertas.setdefault(conta["id"], set())
            ab.add(self.processo)
            self.m.max_abertas[conta["id"]] = max(self.m.max_abertas.get(conta["id"], 0), len(ab))
        s = self._s[conta["id"]]
        s.negocios |= set(negocios_do_robo)
        return s

    async def fechar(self, conta_id):
        if self._s.pop(conta_id, None) is not None:
            self.m.abertas.get(conta_id, set()).discard(self.processo)

    async def fechar_todas(self):
        for cid in list(self._s):
            await self.fechar(cid)


class RoboDuble:
    """`agger_robo` pela §6.4. Um por PROCESSO: o processo morto não lê nem posta mais nada."""
    DisparoIncerto = DisparoIncerto
    DisparoRecusado = DisparoRecusado
    Disparo = Disparo

    def __init__(self, mundo: MundoAgger, visao):
        self.m, self.visao = mundo, visao

    def _vivo(self):
        if self.visao.morto:
            raise D.MorteDoProcesso("processo morto")

    def _postar(self, sessao, ref, preset):
        v = self.m.versoes.get(ref, 0) + 1
        self.m.versoes[ref] = v
        self.m.posts.append((sessao.conta_id, ref, v, preset))
        sessao._posts += 1
        self.m.servir[(ref, v)] = SERVIR.get(preset, 0)
        sessao.registrar_negocio(ref)
        return Disparo(ref, v, time.time())

    async def disparar(self, sessao, pedido, coberturas, *, negocio_ref=None):
        self._vivo()
        assert isinstance(pedido, dict) and pedido["segurado"]["cpf_cnpj"] == CPF, "o motor decifra o pedido"
        preset = coberturas.get("preset")
        if preset in self.m.falha_disparo:
            raise self.m.falha_disparo[preset]
        if negocio_ref is not None:
            assert negocio_ref in sessao.negocios, "a guarda só aceita negócio do robô"
        ref = negocio_ref or f"NEG-{len(self.m.versoes) + 1}"
        d = self._postar(sessao, ref, preset)
        if self.m.matar_no_disparo == preset:
            self.visao.morto = True
            raise D.MorteDoProcesso("morreu depois do POST, antes do checkpoint")
        return d

    async def recalcular(self, sessao, negocio_ref, *, versao_base, ajuste):
        self._vivo()
        assert negocio_ref in sessao.negocios
        assert isinstance(ajuste, Ajuste)
        self.m.recalculos.append((negocio_ref, versao_base, ajuste))
        return self._postar(sessao, negocio_ref, "ajuste")

    async def pessoa_mexeu_recentemente(self, sessao, negocio_ref, *, horas=24, versoes_do_robo):
        self._vivo()
        self.m.consultas_mexeu.append((negocio_ref, horas, set(versoes_do_robo)))
        return self.m.mexeu

    async def acompanhar(self, sessao, disparo, *, ao_evento, anterior=None, quadro_s=60, teto_s=480,
                         intervalo_s=3, ao_quadro=None):
        k = (disparo.negocio_ref, disparo.versao)
        self.m.anteriores.append((k, anterior is None))
        rs = rodadas(self.m.servir[k])
        conta = sessao.conta_id
        self.m.em_acompanhamento[conta] = self.m.em_acompanhamento.get(conta, 0) + 1
        self.m.max_contas_simultaneas = max(self.m.max_contas_simultaneas,
                                            sum(1 for n in self.m.em_acompanhamento.values() if n))
        atual, quadro = anterior, False
        try:
            if self.m.ocupacao_s:
                await asyncio.sleep(self.m.ocupacao_s)
            while self.m.cursor.get(k, 0) < len(rs):
                self._vivo()
                i = self.m.cursor.get(k, 0)
                r = rs[i]
                for e in L.eventos_entre(atual, r):
                    self._vivo()
                    self.m.emitidos.append((self.visao.dono, k, _identidade(e)))
                    await ao_evento(e)
                    self.m.entregues.append((self.visao.dono, k, _identidade(e)))
                atual = r
                self.m.cursor[k] = i + 1
                if self.m.matar_em == (k, i):
                    self.visao.morto = True
                    raise D.MorteDoProcesso("kill -9 no meio do acompanhamento")
                if ao_quadro and not quadro and (r.fechado or i >= 2):
                    quadro = True
                    await ao_quadro()
                await asyncio.sleep(0)
            return atual
        finally:
            self.m.em_acompanhamento[conta] -= 1

    async def copiar_pdfs(self, sessao, disparo):
        self._vivo()
        if self.m.pdfs_falham:
            raise RuntimeError("download falhou https://pdocs.example/arquivo.pdf?key=abc123")
        ultima = rodadas(self.m.servir[(disparo.negocio_ref, disparo.versao)])[-1]
        return {(o.seguradora_codigo, o.pacote, o.tipo_de_pacote): b"%PDF-1.4 dubl\xc3\xaa" for o in ultima.ofertas[:2]}


# ═════════════════════════════════════════════════════════════════════════════
# A semeadura e o motor
# ═════════════════════════════════════════════════════════════════════════════
def empresa(amb) -> str:
    cid = str(uuid4())
    amb.banco.semear("companies", {"id": cid})
    return cid


def robo(amb, corretora, *, estado="ativo", teto=None, janela=None, rotulo=None) -> str:
    from portal_worker import vault

    rid = str(uuid4())
    amb.banco.semear("portal_accounts", {
        "id": rid, "company_id": corretora, "portal_key": "agger", "account_label": rotulo or f"robo-{rid[:6]}",
        "username": "robo@exemplo.invalid", "secret_encrypted": vault.encrypt(SENHA), "robo_estado": estado,
        "robo_teto_por_hora": teto, "robo_janela": janela,
    })
    return rid


def pedido(amb, solicitante, corretoras, *, opcoes=("padrao", "economica"), origem="canal", expira_min=10,
           prioridade=0) -> tuple:
    from portal_worker import vault

    pid = str(uuid4())
    amb.banco.semear("multicalculo_pedidos", {
        "id": pid, "company_id": solicitante, "origem": origem, "opcoes": list(opcoes), "corretoras": list(corretoras),
        "pedido_cifrado": vault.encrypt(json.dumps(PEDIDO)), "cpf_hmac": "hmac-ficticio", "quadro_s": 60,
    })
    ids = []
    for corretora in corretoras:
        for op in opcoes:
            cid = str(uuid4())
            amb.banco.semear("multicalculo_calculos", {
                "id": cid, "pedido_id": pid, "solicitante_company_id": solicitante, "company_id": corretora,
                "opcao": op, "coberturas": {"preset": op}, "prioridade": prioridade,
                "expira_em": (T0 + timedelta(minutes=expira_min)).isoformat(),
            })
            ids.append(cid)
    return pid, ids


def motor(amb, nome, **kw) -> MOT.Motor:
    visao = amb.banco.visao(nome)

    async def upload(supa, caminho, blob, content_type="application/pdf"):
        amb.mundo.uploads.append((caminho, len(blob)))
        return None if kw.get("upload_falha") else caminho

    return MOT.Motor(visao, sessoes=SessoesDuble(amb.mundo, nome), robo=RoboDuble(amb.mundo, visao),
                     sessao_mod=SESSAO_MOD, dono=nome, agora=amb.relogio.agora, batida_s=kw.get("batida_s", 0.02),
                     upload=upload, freio=lambda: False, canario=kw.get("canario", False),
                     decifrar=kw.get("decifrar"))


def linhas(amb, tabela, **filtro):
    return [r for r in amb.banco.linhas(tabela) if all(r.get(k) == v for k, v in filtro.items())]


def calc(amb, cid) -> dict:
    return linhas(amb, "multicalculo_calculos", id=cid)[0]


def conta(amb, rid) -> dict:
    return linhas(amb, "portal_accounts", id=rid)[0]


def rodar(coro):
    return asyncio.run(coro)


# ═════════════════════════════════════════════════════════════════════════════
# 🔴 O TESTE DO FIO — canal → 2 corretoras × 2 opções → motor.uma_volta → robô (§6.4) → leitor REAL → banco
# ═════════════════════════════════════════════════════════════════════════════
def test_o_fio_do_motor_dois_tenants_duas_opcoes(ambiente, caplog):
    amb = ambiente
    caplog.set_level(logging.DEBUG)
    canal, a, b = empresa(amb), empresa(amb), empresa(amb)
    ra, rb = robo(amb, a), robo(amb, b)
    pid, ids = pedido(amb, canal, [a, b])
    m = motor(amb, "motor-1")

    n = rodar(m.uma_volta())
    assert n == 2, "um grupo por corretora, em paralelo"

    esperado_ofertas = {SERVIR[o]: len(rodadas(SERVIR[o])[-1].ofertas) for o in ("padrao", "economica")}
    esperado_eventos = {SERVIR[o]: len(L.eventos_do_calculo(rodadas(SERVIR[o]))) for o in ("padrao", "economica")}
    assert esperado_ofertas == {0: 26, 1: 26} and esperado_eventos == {0: 30, 1: 30}   # 📊 leitor puro, 05/10

    por_corretora = {}
    for cid in ids:
        c = calc(amb, cid)
        assert c["status"] == "fechado", (c["opcao"], c["status"], c["erro"])
        assert c["solicitante_company_id"] == canal and c["account_id"] == {a: ra, b: rb}[c["company_id"]]
        assert c["primeira_oferta_em"] and c["quadro_pronto_em"] and c["fechado_em"]
        por_corretora.setdefault(c["company_id"], {})[c["opcao"]] = c
        idx = SERVIR[c["opcao"]]
        ofs = linhas(amb, "multicalculo_ofertas", calculo_id=cid)
        evs = linhas(amb, "multicalculo_eventos", calculo_id=cid)
        assert len(ofs) == esperado_ofertas[idx] and len(evs) == esperado_eventos[idx]
        for r in ofs + evs:   # cada linha com a corretora e o solicitante CERTOS
            assert (r["company_id"], r["solicitante_company_id"], r["pedido_id"]) == (c["company_id"], canal, pid)
        assert [e["tipo"] for e in evs].count("conjunto_fechado") == 1
        assert all(e["oferta_id"] for e in evs if e["tipo"] == "nova_oferta")
    for corretora, ops in por_corretora.items():   # D-129B-03: a econômica é versão do MESMO negócio
        assert ops["padrao"]["negocio_ref"] == ops["economica"]["negocio_ref"]
        assert (ops["padrao"]["versao"], ops["economica"]["versao"]) == (1, 2)
    assert len(amb.mundo.posts) == 4
    assert linhas(amb, "multicalculo_pedidos", id=pid)[0]["status"] == "fechado"

    # PDFs: copiados para multicalculo/{corretora}/{calculo}/{oferta}.pdf e a oferta aponta para eles
    com_pdf = [o for o in amb.banco.linhas("multicalculo_ofertas") if o["pdf_path"]]
    assert len(com_pdf) == 8 and len(amb.mundo.uploads) == 8
    for o in com_pdf:
        assert o["pdf_path"] == f"multicalculo/{o['company_id']}/{o['calculo_id']}/{o['id']}.pdf" and o["tem_pdf"]

    # A senha decifrada chegou à sessão — e a NENHUM outro lugar. Nem o pedido decifrado.
    assert amb.mundo.senhas == [SENHA, SENHA]
    tudo = json.dumps({t: amb.banco.linhas(t) for t in list(amb.banco.tabelas)}, default=str)
    for segredo in (SENHA, CPF, NOME, "ABC1D23"):
        assert segredo not in tudo, "dado do pedido/senha no banco"
        assert segredo not in caplog.text, "dado do pedido/senha no log"

    # 🔴 Toda escrita do motor numa linha de corretora leva o company_id (no filtro ou na linha)
    for e in amb.banco.escritas:
        if e.dono != "motor-1" or not (e.tabela.startswith("multicalculo_") or e.tabela == "portal_accounts"):
            continue
        no_filtro = any(getattr(f, "coluna", None) == "company_id" and f.op == "eq" for f in e.filtros)
        na_linha = e.op in ("insert",) and all("company_id" in r for r in e.depois)
        assert no_filtro or na_linha or (e.op == "update" and not e.depois), (e.tabela, e.op)

    # Sessão ociosa segura a lease; desligar devolve
    assert conta(amb, ra)["robo_dono"] == "motor-1"
    rodar(m.desligar())
    assert conta(amb, ra)["robo_dono"] is None and conta(amb, rb)["robo_dono"] is None
    assert amb.mundo.abertas[ra] == set()


# ═════════════════════════════════════════════════════════════════════════════
# G4 — um cálculo, um dono · um robô, uma lease
# ═════════════════════════════════════════════════════════════════════════════
def _claims(amb, cid):
    return [e for e in amb.banco.escritas if e.tabela == "multicalculo_calculos" and e.op == "update"
            and isinstance(e.payload, dict) and e.payload.get("status") == "disparando"
            and any(r["id"] == cid for r in e.depois)]


def test_g4_dois_motores_um_calculo_um_claim(ambiente):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a), robo(amb, a)   # dois robôs: a corrida é no CÁLCULO, não no robô
    _pid, ids = pedido(amb, a, [a])
    m1, m2 = motor(amb, "motor-1"), motor(amb, "motor-2")

    async def cenario():
        await asyncio.gather(m1.uma_volta(), m2.uma_volta())

    rodar(cenario())
    for cid in ids:
        assert len(_claims(amb, cid)) == 1, "dois motores reservaram o MESMO cálculo"
        assert calc(amb, cid)["status"] == "fechado"
    assert len(amb.mundo.posts) == 2


def test_g4_dois_motores_um_robo_uma_lease(ambiente):
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a)
    _p1, ids1 = pedido(amb, a, [a], opcoes=("padrao",))
    _p2, ids2 = pedido(amb, a, [a], opcoes=("padrao",))
    m1, m2 = motor(amb, "motor-1"), motor(amb, "motor-2")
    amb.mundo.ocupacao_s = 0.05

    async def cenario():
        n1 = await asyncio.gather(m1.uma_volta(), m2.uma_volta())
        assert sum(n1) == 1, "um robô, UM grupo por vez"
        n2 = await asyncio.gather(m1.uma_volta(), m2.uma_volta())
        assert sum(n2) == 1

    rodar(cenario())
    assert amb.mundo.max_abertas[r] == 1, "duas sessões no MESMO login ao mesmo tempo"
    assert {calc(amb, c)["status"] for c in ids1 + ids2} == {"fechado"}


# ═════════════════════════════════════════════════════════════════════════════
# G6 — a retomada não recalcula PORQUE o checkpoint vem antes do acompanhamento
# ═════════════════════════════════════════════════════════════════════════════
def test_g6_morte_depois_do_checkpoint_religar_nao_reposta_nem_duplica(ambiente):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a)
    _pid, ids = pedido(amb, a, [a])
    m1 = motor(amb, "motor-1")
    amb.mundo.matar_em = (("NEG-1", 1), 2)   # morre depois de gravar a 3ª rodada da padrão

    async def cenario():
        await m1.uma_volta()
        await asyncio.sleep(0.05)   # o que sobrou do processo morto morre na próxima ida ao banco

    rodar(cenario())
    assert m1.supa.morto
    posts_antes = len(amb.mundo.posts)
    assert posts_antes == 2
    assert {calc(amb, c)["status"] for c in ids} == {"calculando"}, "o checkpoint gravou o negócio ANTES do GET"
    eventos_antes = len(amb.banco.linhas("multicalculo_eventos"))
    assert 0 < eventos_antes < 60

    amb.relogio.avancar(MOT.LEASE_VENCE_S + 1)
    m2 = motor(amb, "motor-2")
    rodar(m2.uma_volta())

    assert len(amb.mundo.posts) == posts_antes, "a retomada fez POST de novo"
    assert all(anterior_nulo is False for (k, anterior_nulo) in amb.mundo.anteriores[2:]), \
        "a retomada acompanhou sem a rodada anterior"
    # O que o processo morto ENTREGOU (gravou) nunca é narrado de novo; o que ele narrou e NÃO gravou
    # (morreu no meio da escrita) TEM de sair de novo — senão o evento se perde.
    gravados_antes = {(k, i) for (p, k, i) in amb.mundo.entregues if p == "motor-1"}
    depois = [(k, i) for (p, k, i) in amb.mundo.emitidos if p == "motor-2"]
    assert depois, "a retomada não narrou nada"
    assert not (set(depois) & gravados_antes), "a retomada narrou de novo o que já estava gravado"
    assert len(depois) == len(set(depois))
    for cid in ids:
        c = calc(amb, cid)
        assert c["status"] == "fechado" and c["dono"] == "motor-2" and c["tentativas"] == 2
        evs = linhas(amb, "multicalculo_eventos", calculo_id=cid)
        assert len(evs) == len({e["chave"] for e in evs}) == 30


def test_g6_morte_entre_o_post_e_o_checkpoint_vira_incerto_sem_repost(ambiente):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a)
    _pid, ids = pedido(amb, a, [a])
    amb.mundo.matar_no_disparo = "padrao"
    rodar(motor(amb, "motor-1").uma_volta())
    assert len(amb.mundo.posts) == 1
    amb.relogio.avancar(MOT.LEASE_VENCE_S + 1)
    rodar(motor(amb, "motor-2").uma_volta())
    assert len(amb.mundo.posts) == 1, "disparo que pode ter saído NUNCA se repete"
    for cid in ids:
        assert calc(amb, cid)["status"] == "incerto"
        assert "não refaça" in calc(amb, cid)["erro"]


# ═════════════════════════════════════════════════════════════════════════════
# G8 — convivência: o motor ocupado não segura o laço do portal
# ═════════════════════════════════════════════════════════════════════════════
def test_g8_motor_ocupado_30s_nao_segura_o_run_lote(ambiente, monkeypatch):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a)
    pedido(amb, a, [a])
    amb.mundo.ocupacao_s = 30
    m = motor(amb, "motor-1")
    job_id = str(uuid4())
    amb.banco.semear("portal_jobs", {"id": job_id, "company_id": a, "portal_key": "vidros_lanternas",
                                      "journey": "dublê", "status": "queued"})
    supa_jobs = amb.banco.visao("portal-1")

    async def job_duble(supa, job):
        supa.table("portal_jobs").update({"status": "succeeded"}).eq("id", job["id"]).execute()

    monkeypatch.setattr(W, "_run_job", job_duble)
    medidas = {}

    async def laco_do_motor_teste():
        await m.uma_volta()

    async def poll_teste():
        while not any(amb.mundo.em_acompanhamento.values()):   # espera o motor ficar OCUPADO
            await asyncio.sleep(0.01)
        t = time.perf_counter()
        await W.run_lote(supa_jobs, 1)
        medidas["run_lote_s"] = time.perf_counter() - t
        medidas["motor_ocupado"] = any(amb.mundo.em_acompanhamento.values())

    async def cenario():
        poll, mot = MAIN.iniciar_lacos(poll=poll_teste, motor=laco_do_motor_teste)
        try:
            await asyncio.wait_for(poll, timeout=5)
        finally:
            mot.cancel()
            await asyncio.gather(mot, return_exceptions=True)

    rodar(cenario())
    assert medidas["motor_ocupado"] is True
    assert medidas["run_lote_s"] < 2.0
    assert linhas(amb, "portal_jobs", id=job_id)[0]["status"] == "succeeded"


# ═════════════════════════════════════════════════════════════════════════════
# G10 — os estados da conta e os freios
# ═════════════════════════════════════════════════════════════════════════════
def test_g10_teto_por_hora_da_conta_com_controle(ambiente):
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a, teto=2)
    p0, velhos = pedido(amb, a, [a])
    for cid in velhos:   # 2 cálculos que já saíram nesta hora, por este robô
        amb.banco.tabelas["multicalculo_calculos"][[x["id"] for x in amb.banco.linhas(
            "multicalculo_calculos")].index(cid)].update(
            status="fechado", account_id=r, negocio_ref="NEG-V", versao=1,
            disparado_em=(T0 - timedelta(minutes=10)).isoformat())
    _p, ids = pedido(amb, a, [a], opcoes=("padrao",))
    assert rodar(motor(amb, "motor-1").uma_volta()) == 0
    assert calc(amb, ids[0])["status"] == "na_fila"
    amb.banco.linhas("portal_accounts")[0]["robo_teto_por_hora"] = 3   # CONTROLE: com folga, sai
    assert rodar(motor(amb, "motor-2").uma_volta()) == 1


def test_g10_teto_da_corretora_e_geral(ambiente, monkeypatch):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a)
    pedido(amb, a, [a])
    monkeypatch.setenv("MULTICALCULO_TETO_CORRETORA_HORA", "1")
    assert rodar(motor(amb, "m1").uma_volta()) == 0
    monkeypatch.delenv("MULTICALCULO_TETO_CORRETORA_HORA")
    monkeypatch.setenv("MULTICALCULO_TETO_GERAL_HORA", "1")
    assert rodar(motor(amb, "m2").uma_volta()) == 0
    monkeypatch.delenv("MULTICALCULO_TETO_GERAL_HORA")
    assert rodar(motor(amb, "m3").uma_volta()) == 1   # CONTROLE


def test_g10_janela(ambiente):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a, janela={"dias": "seg-dom", "inicio": "03:00", "fim": "04:00"})
    pedido(amb, a, [a], opcoes=("padrao",))
    assert rodar(motor(amb, "m1").uma_volta()) == 0, "fora da janela (10:00 em Brasília)"
    amb.banco.linhas("portal_accounts")[0]["robo_janela"] = "seg-dom,09:00-11:00"
    assert rodar(motor(amb, "m2").uma_volta()) == 1   # CONTROLE
    assert ROB.dentro_da_janela({"dias": ["ter"], "inicio": "09:59", "fim": "10:01"}, T0) is True
    assert ROB.dentro_da_janela({"dias": ["qua"], "inicio": "09:59", "fim": "10:01"}, T0) is False
    assert ROB.dentro_da_janela("lixo", T0) is False and ROB.dentro_da_janela({}, T0) is False


def test_g10_conta_de_teste_so_atende_pedido_de_teste_no_canario(ambiente):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a, estado="teste", janela={"dias": "seg-dom", "inicio": "00:00", "fim": "23:59"})
    _p, aux = pedido(amb, a, [a], opcoes=("padrao",), origem="auxiliar")
    assert rodar(motor(amb, "m1", canario=True).uma_volta()) == 0, "conta de PESSOA atendeu pedido real"
    assert calc(amb, aux[0])["status"] == "na_fila"
    _p, tst = pedido(amb, a, [a], opcoes=("padrao",), origem="teste")
    assert rodar(motor(amb, "m2", canario=False).uma_volta()) == 0, "pedido de teste fora do canário"
    assert rodar(motor(amb, "m3", canario=True).uma_volta()) == 1   # CONTROLE
    assert calc(amb, tst[0])["status"] == "fechado" and calc(amb, aux[0])["status"] == "na_fila"


def test_g10_teste_mais_sessao_ocupada_pausa_e_para(ambiente):
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a, estado="teste", janela={"dias": "seg-dom", "inicio": "00:00", "fim": "23:59"})
    _p, ids = pedido(amb, a, [a], origem="teste")
    amb.mundo.login[r] = SessaoOcupada
    rodar(motor(amb, "m1", canario=True).uma_volta())
    assert conta(amb, r)["robo_estado"] == "pausado" and conta(amb, r)["robo_dono"] is None
    assert {calc(amb, c)["status"] for c in ids} == {"falhou"} and amb.mundo.posts == []


def test_g10_ativo_mais_sessao_ocupada_afasta_30_min_e_devolve_a_fila(ambiente):
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a)
    _p, ids = pedido(amb, a, [a], expira_min=120)
    amb.mundo.login[r] = SessaoOcupada
    rodar(motor(amb, "m1").uma_volta())
    c = conta(amb, r)
    assert c["robo_estado"] == "ocupada"
    assert D._para_ts(c["robo_ocupada_ate"]) == T0 + timedelta(minutes=MOT.OCUPADA_MIN)
    for cid in ids:
        assert calc(amb, cid)["status"] == "na_fila" and calc(amb, cid)["dono"] is None
    del amb.mundo.login[r]
    assert rodar(motor(amb, "m2").uma_volta()) == 0, "robô ocupado não é usado"
    amb.relogio.avancar(MOT.OCUPADA_MIN * 60 + 1)
    assert rodar(motor(amb, "m3").uma_volta()) == 1
    assert conta(amb, r)["robo_estado"] == "ativo" and {calc(amb, x)["status"] for x in ids} == {"fechado"}


def test_g10_credencial_recusada_bloqueia_e_nao_retenta(ambiente):
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a)
    _p, ids = pedido(amb, a, [a], expira_min=120)
    amb.mundo.login[r] = CredencialRecusada
    m = motor(amb, "m1")
    rodar(m.uma_volta())
    rodar(m.uma_volta())
    assert conta(amb, r)["robo_estado"] == "bloqueado"
    assert len(amb.mundo.obter) == 1, "senha errada: UMA tentativa"
    evs = [e for e in amb.banco.linhas("multicalculo_eventos") if e["tipo"] == "robo_bloqueado"]
    assert len(evs) == 2 and {e["calculo_id"] for e in evs} == set(ids)
    assert {calc(amb, c)["status"] for c in ids} == {"na_fila"}


def test_g10_expira_em_vira_expirado(ambiente):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a)
    pid, ids = pedido(amb, a, [a], expira_min=1)
    amb.relogio.avancar(120)
    assert rodar(motor(amb, "m1").uma_volta()) == 0
    assert {calc(amb, c)["status"] for c in ids} == {"expirado"}
    assert linhas(amb, "multicalculo_pedidos", id=pid)[0]["status"] == "fechado"


# ═════════════════════════════════════════════════════════════════════════════
# G14 — rodízio: dois robôs da mesma corretora
# ═════════════════════════════════════════════════════════════════════════════
def test_g14_rodizio_dois_robos_em_paralelo_e_ocupada_passa_para_o_outro(ambiente):
    amb = ambiente
    a = empresa(amb)
    r1, r2 = robo(amb, a, rotulo="robo-1"), robo(amb, a, rotulo="robo-2")
    pedido(amb, a, [a], opcoes=("padrao",))
    pedido(amb, a, [a], opcoes=("padrao",))
    amb.mundo.ocupacao_s = 0.1
    m = motor(amb, "m1")
    assert rodar(m.uma_volta()) == 2
    assert {p[0] for p in amb.mundo.posts} == {r1, r2}
    assert amb.mundo.max_contas_simultaneas == 2, "os dois robôs não trabalharam em paralelo"
    rodar(m.desligar())

    amb.banco.linhas("portal_accounts")[0].update(robo_estado="ocupada",
                                                  robo_ocupada_ate=(T0 + timedelta(minutes=5)).isoformat())
    ocupado = amb.banco.linhas("portal_accounts")[0]["id"]
    livre = r2 if ocupado == r1 else r1
    pedido(amb, a, [a], opcoes=("padrao",))
    assert rodar(motor(amb, "m2").uma_volta()) == 1
    assert amb.mundo.posts[-1][0] == livre


# ═════════════════════════════════════════════════════════════════════════════
# O recálculo (D-MC-41/47) e os desfechos do disparo
# ═════════════════════════════════════════════════════════════════════════════
def _pedido_com_padrao_fechada(amb, a, r):
    pid, ids = pedido(amb, a, [a], opcoes=("padrao",))
    amb.banco.linhas("multicalculo_calculos")[-1].update(status="fechado", account_id=r, negocio_ref="NEG-X",
                                                          versao=1, fechado_em=T0.isoformat())
    amb.mundo.versoes["NEG-X"] = 1
    aj = str(uuid4())
    amb.banco.semear("multicalculo_calculos", {
        "id": aj, "pedido_id": pid, "solicitante_company_id": a, "company_id": a, "opcao": "ajuste",
        "coberturas": {"preset": "ajuste"}, "origem_calculo_id": ids[0],
        "ajuste": {"tipo": "franquia", "valor": "reduzida"}, "expira_em": (T0 + timedelta(hours=1)).isoformat()})
    return pid, ids[0], aj


def test_recalculo_parte_da_versao_da_origem(ambiente):
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a)
    _pid, _origem, aj = _pedido_com_padrao_fechada(amb, a, r)
    rodar(motor(amb, "m1").uma_volta())
    assert amb.mundo.recalculos == [("NEG-X", 1, Ajuste(tipo="franquia", valor="reduzida"))]
    assert amb.mundo.consultas_mexeu == [("NEG-X", 24, {1})]
    c = calc(amb, aj)
    assert c["status"] == "fechado" and (c["negocio_ref"], c["versao"]) == ("NEG-X", 2)


def test_recalculo_com_pessoa_mexendo_falha_sem_post(ambiente):
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a)
    _pid, _origem, aj = _pedido_com_padrao_fechada(amb, a, r)
    amb.mundo.mexeu = True
    rodar(motor(amb, "m1").uma_volta())
    assert amb.mundo.posts == [] and calc(amb, aj)["status"] == "falhou"
    assert calc(amb, aj)["erro"] == MOT.MOTIVO_PESSOA_MEXEU


def test_disparo_recusado_falha_saneado_incerto_nao_repete_e_pdf_nao_derruba(ambiente):
    amb = ambiente
    a = empresa(amb)
    robo(amb, a)
    _p, ids = pedido(amb, a, [a])
    amb.mundo.falha_disparo["padrao"] = DisparoRecusado(f"campo inválido para {CPF} veja https://x.invalid/a?key=zz")
    amb.mundo.pdfs_falham = True
    rodar(motor(amb, "m1").uma_volta())
    pad, eco = (calc(amb, c) for c in ids)
    assert pad["status"] == "falhou"
    assert "https://" not in pad["erro"] and CPF not in pad["erro"] and "recusou" in pad["erro"]
    assert eco["status"] == "fechado", "PDF que falha não falha o cálculo"

    amb2 = SimpleNamespace(banco=BancoU1(amb.relogio), relogio=amb.relogio, mundo=MundoAgger())
    b = empresa(amb2)
    robo(amb2, b)
    _p, ids2 = pedido(amb2, b, [b])
    amb2.mundo.falha_disparo["padrao"] = DisparoIncerto("timeout")
    rodar(motor(amb2, "m1").uma_volta())
    rodar(motor(amb2, "m2").uma_volta())
    assert calc(amb2, ids2[0])["status"] == "incerto" and calc(amb2, ids2[1])["status"] == "fechado"
    assert [p[3] for p in amb2.mundo.posts] == ["economica"], "o incerto nunca é repetido"


def test_o_laco_nasce_desligado(monkeypatch):
    """D-129B-09: sem MULTICALCULO_MOTOR_LIGADO, a task termina sem abrir banco nem navegador."""
    monkeypatch.delenv("MULTICALCULO_MOTOR_LIGADO", raising=False)
    monkeypatch.setenv("PORTAL_REAL_ENABLED", "true")
    chamou = []
    rodar(asyncio.wait_for(MOT.laco_do_motor(supa_fabrica=lambda: chamou.append(1)), timeout=2))
    assert chamou == []
    monkeypatch.setenv("MULTICALCULO_MOTOR_LIGADO", "true")
    monkeypatch.setenv("PORTAL_REAL_ENABLED", "false")
    rodar(asyncio.wait_for(MOT.laco_do_motor(supa_fabrica=lambda: chamou.append(1)), timeout=2))
    assert chamou == []


def test_login_que_falha_sem_causa_espera_antes_de_tentar_de_novo(ambiente):
    """Portal fora: o cálculo volta à fila com `disponivel_em` (60 s × tentativas) — nunca um login a cada 5 s."""
    amb = ambiente
    a = empresa(amb)
    r = robo(amb, a)
    _p, ids = pedido(amb, a, [a], expira_min=120)
    amb.mundo.login[r] = ConnectionError
    m = motor(amb, "m1")
    rodar(m.uma_volta())
    rodar(m.uma_volta())
    assert len(amb.mundo.obter) == 1, "tentou logar de novo sem esperar"
    for cid in ids:
        c = calc(amb, cid)
        assert c["status"] == "na_fila" and D._para_ts(c["disponivel_em"]) == T0 + timedelta(seconds=60)
    assert conta(amb, r)["robo_estado"] == "ativo"
    del amb.mundo.login[r]
    amb.relogio.avancar(61)
    assert rodar(m.uma_volta()) == 1   # CONTROLE: passada a espera, sai
    assert {calc(amb, c)["status"] for c in ids} == {"fechado"}

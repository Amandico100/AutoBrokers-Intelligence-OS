# -*- coding: utf-8 -*-
"""SPEC-129-B F4 — O TESTE DO FIO (G11 · G13 · G6 com o robô real · o desligar do serviço).

A costura das três fatias: a saída REAL de uma é a entrada da outra (protocolo §5.2). Tudo é REAL, menos as bordas:

    porta F1 (MulticalculoProvider + RepositorioMulticalculo + o cofre do smith-api `portal_vault`)
      → banco DUBLÊ (`dubles.banco_multicalculo.BancoU1`: o PostgREST em memória com as travas do U1)
      → `Motor.uma_volta()` F3 (+ `robos`, o cofre do worker `portal_worker.vault`)
      → robô F2 (`agger_sessao.Sessoes` + `agger_robo` + `montador.js` + a guarda) num Chromium REAL
      → Agger DUBLÊ (`dubles.agger_duble`, as fixtures saneadas da 128) → `leitor_agger` REAL
      → ofertas/eventos no banco → porta `consultar` / `recalcular`
    bordas: o banco (PostgREST), o Agger (rede), o storage do PDF (um coletor no lugar do `_upload_portal_blob`)

A ÚNICA troca no robô: `acompanhar` com `intervalo_s=0.05` (o padrão de 3 s só alonga o teste; o dublê avança uma
rodada por GET). Nenhum elo é reimplementado.

⛔ Dado FICTÍCIO (CPF com dígito válido inventado, nome e placa inventados); nenhum nome de corretora (§13.9).
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec129b_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pw_api = pytest.importorskip("playwright.async_api")

import dubles_do_work_os as D  # noqa: E402
from app.services.multicalculo import MulticalculoProvider, NaoEncontrado, PedidoDeCalculo, de_apolice  # noqa: E402
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402
from dubles.agger_duble import EMAIL, SENHA, AggerDuble  # noqa: E402
from dubles.banco_multicalculo import BancoU1, instalar_esquema  # noqa: E402
from portal_worker import main as MAIN  # noqa: E402
from portal_worker.multicalculo import agger_robo as R  # noqa: E402
from portal_worker.multicalculo import agger_sessao as S  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402
from portal_worker.multicalculo.contrato import SEGURADORA_ANTERIOR_NO_AGGER  # noqa: E402
from portal_worker.multicalculo.leitor_agger import eventos_do_calculo, ler_rodada  # noqa: E402

CPF = "52998224725"
NOME = "Pessoa Ficticia do Fio"
PLACA = "TST1A23"
CHAVE_HMAC = "chave-hmac-ficticia-do-fio-0123456789"
SEGREDOS = ("SEGREDO-", "TOKEN-", SENHA)

# 📊 o robô devolve ao Python o que a lista branca deixa; o dublê põe estes prefixos em TUDO que é segredo.


def dados_do_pedido(**extra):
    d = {
        "segurado": {"cpf_cnpj": CPF, "nome": NOME, "nascimento": "1980-01-01", "sexo": "F", "estado_civil": 2,
                     "cep": "88000000"},
        "veiculo": {"placa": PLACA, "fipe": "0013277", "ano_fabricacao": 2011, "ano_modelo": 2012,
                    "combustivel": "flex", "uso": 1},
        "pernoite": {"cep_pernoite": "88000000", "garagem_residencia": "2"},
        "condutor": {"cpf": CPF, "nome": NOME, "nascimento": "1980-01-01", "sexo": "F", "estado_civil": 2,
                     "tempo_habilitacao": 11, "relacao_com_segurado": "proprio", "jovem_condutor": False},
        "questionario": {"km_mensal": 500},
    }
    d.update(extra)
    return d


# =====================================================================================================================
# O mundo
# =====================================================================================================================
@pytest.fixture
def mundo(monkeypatch):
    from cryptography.fernet import Fernet

    instalar_esquema(monkeypatch, com_porta=True)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    for nome in ("MULTICALCULO_TETO_CORRETORA_HORA", "MULTICALCULO_TETO_GERAL_HORA", "AUTOBROKERS_CANARIO"):
        monkeypatch.delenv(nome, raising=False)
    from portal_worker import leases

    monkeypatch.setattr(leases, "redis_disponivel", lambda *a, **k: False)
    # O relógio do BANCO e do motor começa AGORA (o robô mede o tempo de verdade, `time.time()`); só a lease avança.
    relogio = D.Relogio(datetime.now(timezone.utc).replace(microsecond=0))
    banco = BancoU1(relogio)
    canal, a, b = (str(uuid4()) for _ in range(3))
    banco.semear("companies", {"id": canal, "company_kind": "platform_canal", "is_technical": True})
    for c in (a, b):
        banco.semear("companies", {"id": c, "company_kind": "client"})
        banco.semear("multicalculo_adesoes", {"canal_company_id": canal, "corretora_company_id": c, "ativa": True})
    from portal_worker import vault

    robos = {}
    for c in (a, b):
        robos[c] = str(uuid4())
        banco.semear("portal_accounts", {
            "id": robos[c], "company_id": c, "portal_key": "agger", "account_label": "robo-1", "username": EMAIL,
            "secret_encrypted": vault.encrypt(SENHA), "robo_estado": "ativo"})
    porta = MulticalculoProvider(RepositorioMulticalculo(banco.visao("smith-api")),
                                 ambiente={"MULTICALCULO_HMAC_KEY": CHAVE_HMAC}, agora=relogio.agora)
    return SimpleNamespace(banco=banco, relogio=relogio, porta=porta, canal=canal, a=a, b=b, robos=robos,
                           uploads=[])


ROBO_RAPIDO = SimpleNamespace(**{k: getattr(R, k) for k in dir(R) if not k.startswith("__")})
ROBO_RAPIDO.acompanhar = functools.partial(R.acompanhar, intervalo_s=0.05)


def motor(m, nome, nav, d) -> MOT.Motor:
    async def upload(supa, caminho, blob, content_type="application/pdf"):
        assert blob[:4] == b"%PDF"
        m.uploads.append(caminho)
        return caminho

    return MOT.Motor(m.banco.visao(nome), sessoes=S.Sessoes(nav, url_base=d.base), robo=ROBO_RAPIDO, dono=nome,
                     agora=m.relogio.agora, batida_s=1.0, upload=upload, freio=lambda: False, canario=False)


async def com_agger_e_navegador(fn):
    d = await AggerDuble().iniciar()
    try:
        async with pw_api.async_playwright() as pw:
            navs = []

            async def novo_navegador():
                nav = await pw.chromium.launch(headless=True)
                navs.append(nav)
                return nav

            try:
                return await fn(d, novo_navegador)
            finally:
                for nav in navs:
                    try:
                        await nav.close()
                    except Exception:  # noqa: BLE001
                        pass
    finally:
        await d.parar()


async def ate_esvaziar(mot: MOT.Motor, m, voltas: int = 12) -> None:
    for _ in range(voltas):
        await mot.uma_volta()
        if not [c for c in m.banco.linhas("multicalculo_calculos") if c["status"] in ("na_fila", "disparando",
                                                                                     "calculando")]:
            return
    raise AssertionError("a fila não esvaziou")


def esperado(d: AggerDuble, versao: int):
    """O LEITOR PURO sobre a mesma fixture que o dublê serve para esta versão: (ofertas, eventos)."""
    rs = [ler_rodada(r) for r in d._rodadas_da_versao(versao)]
    ids = {(o.seguradora_codigo, o.pacote, o.tipo_de_pacote) for r in rs for o in r.ofertas}
    return len(ids), len(eventos_do_calculo(rs))


def linhas(m, tabela, **filtro):
    return [r for r in m.banco.linhas(tabela) if all(r.get(k) == v for k, v in filtro.items())]


def rodar(coro):
    return asyncio.run(coro)


# =====================================================================================================================
# 🔴 O TESTE DO FIO (G11) — o canal pede 2 corretoras × padrão+econômica; cada corretora pede o seu
# =====================================================================================================================
def test_o_fio_porta_motor_robo_chromium_agger_leitor_consultar(mundo, caplog):
    m = mundo
    caplog.set_level(logging.DEBUG)

    async def cenario(d, novo_navegador):
        nav = await novo_navegador()
        pedido = PedidoDeCalculo.de_dict(dados_do_pedido())
        do_canal = await m.porta.calcular(company_id=m.canal, pedido=pedido, corretoras=[m.a, m.b], origem="canal")
        de_a = await m.porta.calcular(company_id=m.a, pedido=pedido, opcoes=("padrao",), origem="auxiliar")
        de_b = await m.porta.calcular(company_id=m.b, pedido=pedido, opcoes=("padrao",), origem="auxiliar")
        mot = motor(m, "motor-1", nav, d)
        await ate_esvaziar(mot, m)
        return mot, do_canal, de_a, de_b

    async def tudo(d, novo_navegador):
        mot, do_canal, de_a, de_b = await cenario(d, novo_navegador)

        # ── o que cada cálculo virou: o leitor PURO sobre a fixture da versão dita a contagem ──
        # 📊 05/10 (F4): o leitor puro sobre as rodadas que o dublê serve — 26 ofertas e 30 eventos por versão. O
        # número FIXO é o que deixa a mutação do leitor DENTRO do robô vermelha (o `esperado` usa o mesmo leitor).
        assert [esperado(d, v) for v in (1, 2, 3)] == [(26, 30)] * 3
        calcs = m.banco.linhas("multicalculo_calculos")
        assert len(calcs) == 6 and {c["status"] for c in calcs} == {"fechado"}, \
            [(c["opcao"], c["status"], c["erro"]) for c in calcs]
        total_ofertas = {}
        for c in calcs:
            n_of, n_ev = esperado(d, c["versao"])
            ofs = linhas(m, "multicalculo_ofertas", calculo_id=c["id"])
            evs = linhas(m, "multicalculo_eventos", calculo_id=c["id"])
            assert (len(ofs), len(evs)) == (n_of, n_ev), (c["opcao"], c["versao"], len(ofs), len(evs))
            assert [e["tipo"] for e in evs].count("conjunto_fechado") == 1
            assert not [e for e in evs if e["tipo"] == R.ERRO_DE_LEITURA]
            assert c["account_id"] == m.robos[c["company_id"]]
            total_ofertas[c["id"]] = len(ofs)
        canal_calcs = [c for c in calcs if c["pedido_id"] == do_canal.pedido_id]
        for corretora in (m.a, m.b):      # D-129B-03: a econômica é versão do MESMO negócio da padrão
            pad = next(c for c in canal_calcs if c["company_id"] == corretora and c["opcao"] == "padrao")
            eco = next(c for c in canal_calcs if c["company_id"] == corretora and c["opcao"] == "economica")
            assert pad["negocio_ref"] == eco["negocio_ref"] and (pad["versao"], eco["versao"]) == (1, 2)
        posts = list(d.posts_calcular)
        assert len(posts) == 6
        # o corpo que saiu tem as coberturas que a PORTA resolveu (presets) — padrão e econômica diferentes
        vidros = sorted({i["vidros"] for p in posts for i in p["cotacao"]["calculos"]})
        assert vidros == [P.PRESETS["economica"]["vidros"], P.PRESETS["padrao"]["vidros"]]

        # ── consultar pelo CANAL: as 2 corretoras, menor preço primeiro, SEM comissão (G2) ──
        andam = await m.porta.consultar(company_id=m.canal, pedido_id=do_canal.pedido_id)
        assert len(andam.ofertas) == sum(total_ofertas[c["id"]] for c in canal_calcs)
        assert {o["corretora_company_id"] for o in andam.ofertas} == {m.a, m.b}
        assert all(o["comissao_percentual"] is None for o in andam.ofertas)
        premios = [o["premio_total"] for o in andam.ofertas]
        assert premios == sorted(premios)
        assert len(andam.eventos) == sum(len(linhas(m, "multicalculo_eventos", calculo_id=c["id"]))
                                         for c in canal_calcs)
        assert {e["status"] for e in andam.estados} == {"fechado"} and len(andam.estados) == 4

        # ── consultar por CADA corretora: só o seu, COM a comissão; o pedido dos outros não existe para ela ──
        for corretora, aberto in ((m.a, de_a), (m.b, de_b)):
            proprio = await m.porta.consultar(company_id=corretora, pedido_id=aberto.pedido_id)
            assert proprio.ofertas and {o["corretora_company_id"] for o in proprio.ofertas} == {corretora}
            no_banco = {r["id"]: r["comissao_percentual"] for r in m.banco.linhas("multicalculo_ofertas")}
            assert all(o["comissao_percentual"] == no_banco[o["id"]] for o in proprio.ofertas)
            assert any(o["comissao_percentual"] is not None for o in proprio.ofertas), "CONTROLE: há comissão"
            for alheio in (do_canal.pedido_id, (de_b if corretora == m.a else de_a).pedido_id):
                with pytest.raises(NaoEncontrado):
                    await m.porta.consultar(company_id=corretora, pedido_id=alheio)

        # ── RECALCULAR a PADRÃO da corretora A com um ajuste → nova versão a partir da versão CERTA ──
        pad_a = next(c for c in canal_calcs if c["company_id"] == m.a and c["opcao"] == "padrao")
        novo = await m.porta.recalcular(company_id=m.canal, calculo_id=pad_a["id"],
                                        ajuste={"tipo": "franquia", "valor": "normal"})
        await ate_esvaziar(mot, m)
        aj = linhas(m, "multicalculo_calculos", id=novo["id"])[0]
        assert aj["status"] == "fechado" and aj["negocio_ref"] == pad_a["negocio_ref"] and aj["versao"] == 3, \
            (aj["status"], aj["erro"], aj["versao"])
        assert len(d.posts_calcular) == 7
        cot = d.posts_calcular[-1]["cotacao"]
        assert cot["versao"] == pad_a["versao"] == 1, "o recálculo partiu de outra versão que não a da PADRÃO"
        itens = [i for i in cot["calculos"] if i["seguradora"] != 45]
        assert itens and all(i["tipoFranquia"] == 2 for i in itens), "o ajuste não chegou ao corpo"
        assert all(i["vidros"] == P.PRESETS["padrao"]["vidros"] for i in itens), "partiu da ECONÔMICA (versão 2)"
        assert aj["coberturas"]["tipoFranquia"] == 2
        assert len(linhas(m, "multicalculo_ofertas", calculo_id=aj["id"])) == esperado(d, 3)[0]

        # ── PDFs copiados para o NOSSO armazenamento ──
        com_pdf = [o for o in m.banco.linhas("multicalculo_ofertas") if o.get("pdf_path")]
        assert com_pdf and len(m.uploads) == len(com_pdf)
        for o in com_pdf:
            assert o["pdf_path"] == f"multicalculo/{o['company_id']}/{o['calculo_id']}/{o['id']}.pdf"

        # ── nenhum segredo nem dado pessoal no banco nem no log (G5 no fio) ──
        tudo_no_banco = json.dumps({t: m.banco.linhas(t) for t in list(m.banco.tabelas)
                                    if t != "portal_accounts"}, default=str, ensure_ascii=False)
        for proibido in SEGREDOS + (CPF, NOME, PLACA):
            assert proibido not in tudo_no_banco, proibido
            assert proibido not in caplog.text, proibido
        assert not re.search(r"https?://", tudo_no_banco)

        # ── o DESLIGAR do serviço (junta 8): logout das sessões e leases devolvidas ──
        assert {m.banco.linhas("portal_accounts")[i]["robo_dono"] for i in range(2)} == {"motor-1"}
        saidas_antes = d.contagem.get("POST api-prod/usuario/deslogaSessao", 0)
        MOT.registrar_motor_do_processo(mot)
        await MAIN._shutdown()
        assert d.contagem.get("POST api-prod/usuario/deslogaSessao", 0) - saidas_antes == 2, d.contagem
        assert {c["robo_dono"] for c in m.banco.linhas("portal_accounts")} == {None}
        assert MOT._MOTOR_DO_PROCESSO is None

    rodar(com_agger_e_navegador(tudo))


# =====================================================================================================================
# G6 com o ROBÔ REAL — matar o motor DEPOIS do checkpoint e ANTES do fechamento; religar
# =====================================================================================================================
def test_morte_e_retomada_com_o_robo_real_nao_reposta_nem_duplica(mundo):
    m = mundo

    async def tudo(d, novo_navegador):
        aberto = await m.porta.calcular(company_id=m.a, pedido=PedidoDeCalculo.de_dict(dados_do_pedido()),
                                        origem="auxiliar")
        nav1 = await novo_navegador()
        m1 = motor(m, "motor-1", nav1, d)
        gravados = {"n": 0}

        def matar_no_quinto(escrita):           # o kill -9: depois do 5º evento GRAVADO pelo motor-1
            if escrita.dono == "motor-1":
                gravados["n"] += 1
                if gravados["n"] == 5:
                    m1.supa.morto = True

        m.banco.ao_gravar("multicalculo_eventos", "insert", matar_no_quinto)   # o dublê registra o upsert novo assim
        await m1.uma_volta()
        await asyncio.sleep(1.0)                 # o que sobrou do processo morto morre na próxima ida ao banco
        await nav1.close()                       # o navegador morre junto (sem logout: é um kill)
        assert m1.supa.morto
        calcs = linhas(m, "multicalculo_calculos", pedido_id=aberto.pedido_id)
        assert {c["status"] for c in calcs} == {"calculando"}, "o checkpoint gravou o negócio ANTES do 1º GET"
        posts_antes = len(d.posts_calcular)
        assert posts_antes == 2
        chaves_antes = {(e["calculo_id"], e["chave"]) for e in m.banco.linhas("multicalculo_eventos")}
        assert 0 < len(chaves_antes) < sum(esperado(d, c["versao"])[1] for c in calcs)

        m.relogio.avancar(MOT.LEASE_VENCE_S + 1)
        m2 = motor(m, "motor-2", await novo_navegador(), d)
        # ESPIA no que o motor-2 TENTA gravar como evento (o upsert com ignore_duplicates engole o repetido em
        # silêncio — contar só o que entrou no banco não pegaria uma narração duplicada)
        tentados = []
        tabela_original = m2.supa.table

        def tabela_espiada(nome):
            q = tabela_original(nome)
            if nome == "multicalculo_eventos":
                upsert_original = q.upsert

                def upsert(linhas_, **k):
                    for r in (linhas_ if isinstance(linhas_, list) else [linhas_]):
                        tentados.append((r["calculo_id"], r["chave"]))
                    return upsert_original(linhas_, **k)

                q.upsert = upsert
            return q

        m2.supa.table = tabela_espiada
        await ate_esvaziar(m2, m)

        assert len(d.posts_calcular) == posts_antes, "a retomada fez calcularV2 de novo"
        assert tentados, "a retomada não narrou nada"
        assert not (set(tentados) & chaves_antes), "a retomada narrou de novo o que já estava gravado"
        assert len(tentados) == len(set(tentados))
        for c in linhas(m, "multicalculo_calculos", pedido_id=aberto.pedido_id):
            evs = linhas(m, "multicalculo_eventos", calculo_id=c["id"])
            assert c["status"] == "fechado" and c["dono"] == "motor-2"
            assert len(evs) == len({e["chave"] for e in evs}) == esperado(d, c["versao"])[1]
            assert len(linhas(m, "multicalculo_ofertas", calculo_id=c["id"])) == esperado(d, c["versao"])[0]
        await m2.desligar()

    rodar(com_agger_e_navegador(tudo))


# =====================================================================================================================
# G13 — a RENOVAÇÃO de ponta a ponta: ficha da InfoCap → porta → motor → robô → o corpo que o Agger recebe
# =====================================================================================================================
def _apolice(sigla: str):
    from app.providers.infocap_policy_provider import apolice_do_pack

    return apolice_do_pack({"policy_locator_ref": "infocap:1:ficticio", "policy_number": "9990001",
                            "insurer_detected": sigla, "product_detected": "AUTO", "valid_from": "2025-11-01",
                            "valid_to": "2026-11-01", "risk_objects": [{"item_number": 1, "plate": PLACA}]},
                           hoje=date(2026, 10, 5))


def test_g13_renovacao_da_ficha_ao_corpo_do_agger_e_os_nomes_das_seguradoras_casam(mundo):
    m = mundo

    async def tudo(d, novo_navegador):
        perfil = dados_do_pedido()
        perfil["renovacao"] = {"bonus_anterior": 4}
        del perfil["condutor"]                   # condutor = o segurado (assumido), o que a ficha não traz
        perfil["condutor"] = {"tempo_habilitacao": 11}
        pedido = de_apolice(_apolice("PORT"), perfil)
        aberto = await m.porta.calcular(company_id=m.a, pedido=pedido, opcoes=("padrao",), origem="auxiliar")
        nav = await novo_navegador()
        mot = motor(m, "motor-1", nav, d)
        await ate_esvaziar(mot, m)
        c = linhas(m, "multicalculo_calculos", pedido_id=aberto.pedido_id)[0]
        assert c["status"] == "fechado", c["erro"]
        cot = d.posts_calcular[-1]["cotacao"]
        nome_por_id = {x["id"]: x["nome"] for x in d.renov}
        assert cot["renovacao"] is True and cot["bonusAnterior"] == 4          # 🔴 o bônus chega ao Agger
        assert cot["numeroRenovacao"] == "9990001"
        assert nome_por_id[cot["seguradoraAnteriorId"]] == "Porto Seguro Cia Seg. Gerais"
        assert cot["vigFimAnterior"].startswith("2026-11-01")
        assert len(linhas(m, "multicalculo_ofertas", calculo_id=c["id"])) == esperado(d, c["versao"])[0]
        await mot.desligar()

        # junta 4: CADA nome da tabela da porta casa com UM item da lista do Agger (o JS real do robô decide)
        sessoes = S.Sessoes(nav, url_base=d.base)
        conta = {"id": "conta-de-prova", "username": EMAIL, "robo_estado": "ativo"}
        sessao = await sessoes.obter(conta, senha=SENHA, negocios_do_robo=set())
        for nome in SEGURADORA_ANTERIOR_NO_AGGER.values():
            p = PedidoDeCalculo.de_dict(dados_do_pedido(renovacao={"renovacao": True, "bonus_anterior": 1,
                                                                   "seguradora_anterior": nome}))
            assert p.sem_codigo() == [] and p.faltando() == []
            await R.disparar(sessao, p.para_dict(), P.coberturas_de("padrao"))
            assert nome_por_id[d.posts_calcular[-1]["cotacao"]["seguradoraAnteriorId"]] == nome
        # CONTROLE: um nome que o Agger tem DUAS vezes é recusado pelo robô — e a porta nunca o deixa passar
        with pytest.raises(R.DisparoRecusado):
            pd = dados_do_pedido(renovacao={"renovacao": True, "seguradora_anterior": "Sul America"})
            bruto = PedidoDeCalculo.de_dict(pd).para_dict()
            await R.disparar(sessao, bruto, P.coberturas_de("padrao"))
        assert PedidoDeCalculo.de_dict(pd).sem_codigo() == ["renovacao.seguradora_anterior"]
        await sessoes.fechar_todas()

    rodar(com_agger_e_navegador(tudo))


def test_o_ajuste_da_porta_e_o_do_montador_dizem_o_mesmo():
    """O gêmeo Python (`presets.CAMPO_DO_AJUSTE`, que a porta grava em `coberturas`) e o JS (`montador.js`, que o
    robô aplica) — a FORMA da declaração (CLAUDE.md §9.4, exceção): uma chave a mais num deles e a porta mente."""
    js = (BACKEND / "portal_worker" / "multicalculo" / "montador.js").read_text(encoding="utf-8")
    bloco = re.search(r"const CAMPO_DO_AJUSTE = \{(.*?)\};", js, re.S).group(1)
    no_js = dict(re.findall(r"(\w+): '(\w+)'", bloco))
    assert no_js == dict(P.CAMPO_DO_AJUSTE)


# =====================================================================================================================
# U6 · G15 — o comando do Founder e o canário, rodados contra os dublês
# =====================================================================================================================
def test_g15_o_comando_cadastra_lista_adere_pausa_e_apaga_sem_mostrar_senha(mundo):
    from portal_worker import vault
    from portal_worker.multicalculo import comando_robo as CMD
    from portal_worker.multicalculo import robos as ROB

    m = mundo
    supa = m.banco.visao("founder")
    saida = []
    senha = "Senha-Do-Founder-Ficticia-77"
    rc = CMD.main(["cadastrar", "--corretora", m.a, "--rotulo", "robo-2", "--usuario", "robo2@exemplo.invalid",
                   "--estado", "teste", "--janela", "seg-dom,00:00-24:00", "--teto", "30"],
                  supa=supa, ler_senha=lambda: senha, escrever=saida.append)
    assert rc == 0, saida
    nova = next(c for c in m.banco.linhas("portal_accounts") if c["account_label"] == "robo-2")
    assert vault.decrypt(nova["secret_encrypted"]) == senha and nova["robo_estado"] == "teste"
    assert nova["robo_janela"] == {"dias": "seg-dom", "inicio": "00:00", "fim": "24:00"}
    assert ROB.dentro_da_janela(nova["robo_janela"]), "a janela gravada é a que o motor LÊ"
    # recusas: teste sem janela · janela ilegível · rótulo repetido · "corretora" que é o canal
    for argv in (["cadastrar", "--corretora", m.a, "--rotulo", "x", "--usuario", "u", "--estado", "teste"],
                 ["cadastrar", "--corretora", m.a, "--rotulo", "x", "--usuario", "u", "--janela", "toda hora"],
                 ["cadastrar", "--corretora", m.a, "--rotulo", "robo-2", "--usuario", "u"],
                 ["cadastrar", "--corretora", m.canal, "--rotulo", "x", "--usuario", "u"]):
        assert CMD.main(argv, supa=supa, ler_senha=lambda: senha, escrever=saida.append) == 2, argv
    assert len([c for c in m.banco.linhas("portal_accounts") if c["account_label"] == "x"]) == 0
    assert CMD.main(["aderir", "--canal", m.a, "--corretora", m.b], supa=supa, escrever=saida.append) == 2
    assert CMD.main(["aderir", "--canal", m.canal, "--corretora", m.a], supa=supa, escrever=saida.append) == 0
    assert len(linhas(m, "multicalculo_adesoes", canal_company_id=m.canal, corretora_company_id=m.a)) == 1
    lista = []
    assert CMD.main(["listar", "--corretora", m.a], supa=supa, escrever=lista.append) == 0
    assert len(lista) == 2 and all("robo2@exemplo.invalid" not in l and EMAIL not in l for l in lista)
    assert any(CMD.mascarar("robo2@exemplo.invalid") in l and "teste" in l for l in lista)
    from app.services.portal_vault import mask
    assert CMD.mascarar("robo2@exemplo.invalid") == mask("robo2@exemplo.invalid")
    assert CMD.main(["pausar", "--conta", nova["id"]], supa=supa, escrever=saida.append) == 0
    assert CMD.main(["apagar-senha", "--conta", nova["id"]], supa=supa, escrever=saida.append) == 0
    nova = next(c for c in m.banco.linhas("portal_accounts") if c["id"] == nova["id"])
    assert nova["robo_estado"] == "pausado" and nova["secret_encrypted"] is None
    tudo = "\n".join(saida + lista)
    assert senha not in tudo and "robo2@exemplo.invalid" not in tudo


def test_g15_os_scripts_respondem_help_e_o_canario_recusa_sem_a_marca():
    import os
    import subprocess

    py = sys.executable
    for script in ("multicalculo_robo.py", "multicalculo_canario.py"):
        r = subprocess.run([py, str(BACKEND / "scripts" / script), "--help"], capture_output=True, text=True,
                           cwd=str(BACKEND), timeout=180, encoding="utf-8", errors="replace")
        assert r.returncode == 0 and "usage" in r.stdout.lower(), (script, r.stderr[-400:])
    r = subprocess.run([py, "-m", "portal_worker.multicalculo.comando_robo", "listar", "--help"],
                       capture_output=True, text=True, cwd=str(BACKEND), timeout=180, encoding="utf-8",
                       errors="replace")
    assert r.returncode == 0, r.stderr[-400:]
    env = {k: v for k, v in os.environ.items() if k != "AUTOBROKERS_CANARIO"}
    r = subprocess.run([py, str(BACKEND / "scripts" / "multicalculo_canario.py"), "--canal", str(uuid4()),
                        "--corretora", str(uuid4()), "--corretora", str(uuid4()), "--perfil", "x.json"],
                       capture_output=True, text=True, cwd=str(BACKEND), timeout=180, env=env, encoding="utf-8",
                       errors="replace")
    assert r.returncode == 2 and "AUTOBROKERS_CANARIO" in r.stdout


def test_o_canario_inteiro_contra_os_dubles(mundo, monkeypatch, tmp_path):
    """O script do canário rodado DE PONTA A PONTA (banco e Agger dublês): morte/retomada sem calcularV2 novo,
    recálculo, varredura = 0, e o `finally` que pausa a conta de pessoa e apaga a senha."""
    sys.path.insert(0, str(BACKEND / "scripts"))
    import multicalculo_canario as CAN

    m = mundo
    for c in m.banco.linhas("portal_accounts"):      # as contas viram `teste` (o login de uma PESSOA)
        c.update({"robo_estado": "teste", "robo_janela": {"dias": "seg-dom", "inicio": "00:00", "fim": "24:00"}})
    monkeypatch.setenv("AUTOBROKERS_CANARIO", "1")
    monkeypatch.setenv("MULTICALCULO_HMAC_KEY", CHAVE_HMAC)
    perfil = tmp_path / "perfil.json"
    perfil.write_text(json.dumps({"pedido": dados_do_pedido()}), encoding="utf-8")
    saida = []

    async def tudo(d, novo_navegador):
        args = CAN._parser().parse_args(["--canal", m.canal, "--corretora", m.a, "--corretora", m.b,
                                         "--perfil", str(perfil), "--matar-depois-do-checkpoint",
                                         "--url-base", d.base])

        async def upload(supa, caminho, blob, content_type="application/pdf"):
            return caminho

        rc = await CAN.executar(args, supa=m.banco.visao("canario"), escrever=saida.append,
                                abrir_navegador=novo_navegador, esperar_lease_s=0,
                                agora_do_religado=lambda: datetime.now(timezone.utc)
                                + timedelta(seconds=MOT.LEASE_VENCE_S + 1),
                                upload=upload, intervalo_s=0.5)
        return rc, len(d.posts_calcular)

    rc, posts = rodar(com_agger_e_navegador(tudo))
    texto = "\n".join(saida)
    assert rc == 0, texto[-2500:]
    morte = next(l for l in saida if l.startswith("MORTE"))
    retomada = next(l for l in saida if l.startswith("RETOMADA"))
    assert "calcularV2 = 4" in morte and retomada.endswith("(+0)"), (morte, retomada)
    gravados_na_morte = int(re.search(r"eventos gravados = (\d+)", morte).group(1))
    assert 0 < gravados_na_morte < len(m.banco.linhas("multicalculo_eventos")), "a morte não caiu NO MEIO"
    assert posts == 5                                               # 4 + o recálculo, nenhum repetido
    assert any(l.startswith("RECÁLCULO franquia: fechado") for l in saida), texto[-1500:]
    assert "varredura senha|loginws|senhaws|token|authorization|url nas 5 tabelas: 0" in saida
    assert any("comissão vista pelo canal: 0" in l for l in saida)
    for proibido in (CPF, NOME, PLACA, SENHA):
        assert proibido not in texto
    for c in m.banco.linhas("portal_accounts"):
        assert c["robo_estado"] == "pausado" and c["secret_encrypted"] is None
    evs = m.banco.linhas("multicalculo_eventos")
    assert len(evs) == len({(e["calculo_id"], e["chave"]) for e in evs})

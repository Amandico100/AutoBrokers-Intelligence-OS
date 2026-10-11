# -*- coding: utf-8 -*-
"""SPEC-129-C · COSTURA — O TESTE DO FIO dos outros ramos (G1 · G2 · G4 · G5 · G8 com o motor e o robô REAIS).

F1 (o portal) e F2 (o app) foram escritas EM PARALELO, cada uma contra dublês da outra. Aqui a saída REAL de uma é a
entrada da outra (protocolo §5.2 · PACOTE-BUILDER "COSTURA"):

    PedidoDeCalculo.de_dict(ramo, risco) F2 → MulticalculoProvider.calcular F2 (comissão do ramo pela config, o validador
      do CONTRATO F1, as coberturas pelo resolvedor dos PRESETS F1, cifra) → banco DUBLÊ (`dubles.banco_multicalculo`)
      → `Motor.uma_volta()` (129-B + costura: o ramo na retomada, o evento "sem atividade") → robô F1 (`agger_sessao` +
      `agger_robo` + `montador.js` + a guarda) num Chromium REAL → Agger DUBLÊ que devolve a RESPOSTA GRAVADA real
      (as 9 gravações saneadas, `fixtures/agger_ramos/`) para as seguradoras que o corpo levou → `leitor_agger` REAL
      (lista branca DO RAMO) → ofertas/eventos no banco → `porta.consultar` + `config.carregar` → `comparacao.comparar`
      F2 → o ranking, conferido por contagem INDEPENDENTE feita aqui, direto no JSON cru da gravação.
    bordas: o banco (PostgREST), o Agger (rede), o storage do PDF.

A ÚNICA troca no robô: `acompanhar` com `intervalo_s=0.05` (como a 129-B). Nenhum elo é reimplementado.
⛔ Dado FICTÍCIO (CNPJ/CPF de exemplo, endereço inventado); as gravações já vêm saneadas; nenhum nome de corretora.
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec129c_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import re
import sys
from datetime import datetime, timezone
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
import test_spec129c_o_app_por_ramo as F2  # noqa: E402  (os pedidos e o esperado contado à mão da F2)
import test_spec129c_o_portal_por_ramo as F1  # noqa: E402  (o Agger dublê de RE e a régua da forma gravada da F1)
from app.services import multicalculo as PACOTE_DA_PORTA  # noqa: E402
from app.services.multicalculo import comparacao as C  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from app.services.multicalculo.porta import MulticalculoProvider, PedidoIncompleto, RamoNaoSuportado  # noqa: E402
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402
from dubles.agger_duble import EMAIL, SENHA  # noqa: E402
from dubles.banco_multicalculo import BancoU1, instalar_esquema  # noqa: E402
from portal_worker.multicalculo import agger_guarda as G  # noqa: E402
from portal_worker.multicalculo import agger_robo as R  # noqa: E402
from portal_worker.multicalculo import agger_sessao as S  # noqa: E402
from portal_worker.multicalculo import contrato as K  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import presets as PRE  # noqa: E402

FIX = BACKEND / "tests" / "fixtures" / "agger_ramos"
CHAVE_HMAC = "chave-hmac-ficticia-129c-fio-0123456789"
CNPJ, CPF = F2.CNPJ, F2.CPF
PROIBIDOS = (CNPJ, CPF, "Rua Ficticia", "Condominio Ficticio", "Empresa Ficticia", "Pessoa Ficticia", SENHA)
RAMO = {"condominio": 16, "residencial": 2, "empresarial": 18}
GRAVACOES = [f"{n}_{i}" for n in RAMO for i in (1, 2, 3)]
#: a atividade de cada empresarial gravado (o TEXTO que um corretor diria) e as respostas de `getOptionsBySegFull` que o
#: dublê serve: 📊 _1 = a opção que a pessoa escolheu + uma isca (F1 `_opcoes_estetica`); _2/_3 = as amostras REAIS
#: medidas em 11/10 (formulario_empresarial.json `amostra_medida_11_10`)
ATIVIDADE = {"empresarial_1": "clínica de estética", "empresarial_2": "escritório", "empresarial_3": "padaria"}
#: 📊 empresarial_2: o corpo gravado diz `imovelPavimentacao` "0", mas a pessoa escolheu os códigos "escritório, 2º andar
#: ou superior" (Allianz 90101, Yelum 101) — o andar que o corretor DIRIA é o das atividades; vai como o RÓTULO da tela
PAVIMENTO = {"empresarial_2": "Segundo em diante"}
FRASE_ATIVIDADE = "não tem na lista dela a atividade deste negócio"


def carregar(nome: str) -> dict:
    return json.loads((FIX / f"gravacao_{nome}.json").read_text(encoding="utf-8"))


def opcoes_de_atividade(nome: str, g: dict) -> dict:
    if nome == "empresarial_1":
        return {o["termo"]: o["opcoes"] for o in F1._opcoes_estetica(g)}
    if nome == "empresarial_2":
        return {"escritorio": F1._amostra("escritorio")}
    if nome == "empresarial_3":
        return {"padaria": F1._amostra("padaria")}
    return {}


def dados_da_gravacao(nome: str, **troca) -> dict:
    """O pedido de um corretor para o MESMO risco da gravação: os códigos/valores do corpo gravado, o resto sintético.
    ⚠️ Sem `valor_de_novo` de propósito (decisão da costura: a tela abre com "Sim" e o robô manda 1)."""
    g = carregar(nome)
    ramo, cfg, v = g["ramo"], g["versao"]["configuracoes"], g["versao"]
    cob = set(PRE.CHAVES_DE_COBERTURA_RE[ramo]) - {"assist24hs", PED.CHAVE_DA_BASICA}
    extras = {k: x for k, x in cfg.items() if k in cob and isinstance(x, (int, float)) and not isinstance(x, bool) and x}
    risco = {**F2.ENDERECO, "valor_basica": cfg[PED.CHAVE_DA_BASICA], "extras": extras}
    if ramo == 16:
        seg = {"cpf_cnpj": "11.222.333/0001-81", "nome": "Condominio Ficticio"}
        risco.update(tipo_imovel=cfg["imovelAtividade"], estrutura=cfg["estruturaCondominio"],
                     ano_fundacao=cfg["anoFundacao"], blocos=cfg["qtdBlocos"], pavimentos=cfg["pavimentos"],
                     elevadores=cfg["qtdElevadores"], protecoes=cfg["sisProtecaoIncendRoubo"])
    elif ramo == 2:
        seg = {"cpf_cnpj": CPF, "nome": "Pessoa Ficticia", "nascimento": "01/02/1980"}
        risco.update(tipo_imovel=cfg["imovelTipoResidencia"], construcao=cfg["imovelConstrucao"],
                     uso=cfg["imovelUso"], objeto=cfg["imovelObjetoSegurado"])
    else:
        seg = {"cpf_cnpj": CNPJ, "nome": "Empresa Ficticia"}
        risco.update(pavimento=PAVIMENTO.get(nome, cfg["imovelPavimentacao"]), localizacao="Outros",
                     construcao=cfg["imovelConstrucao"], objeto=cfg["imovelObjetoSegurado"], atividade=ATIVIDADE[nome])
    d = {"segurado": seg, "risco": risco}
    if v.get("renovacao") is True:
        d["renovacao"] = {"renovacao": True, "seguradora_anterior": "AXA Seguros",
                          "bonus_anterior": v.get("bonusAnterior"), "sinistros_anterior": int(v["sinistrosAnterior"]),
                          "fim_vigencia_anterior": str(v["vigFimAnterior"])[:10]}
    for grupo, valores in troca.items():
        d[grupo] = {**d.get(grupo, {}), **valores}
    return d


# =====================================================================================================================
# O mundo: duas corretoras + o canal, a porta REAL sobre o banco dublê, um robô por corretora
# =====================================================================================================================
@pytest.fixture
def mundo(monkeypatch):
    from cryptography.fernet import Fernet

    instalar_esquema(monkeypatch, com_porta=True)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    for nome in ("MULTICALCULO_TETO_CORRETORA_HORA", "MULTICALCULO_TETO_GERAL_HORA", "AUTOBROKERS_CANARIO"):
        monkeypatch.delenv(nome, raising=False)
    from portal_worker import leases, vault

    monkeypatch.setattr(leases, "redis_disponivel", lambda *a, **k: False)
    relogio = D.Relogio(datetime.now(timezone.utc).replace(microsecond=0))
    banco = BancoU1(relogio)
    canal, a, b = (str(uuid4()) for _ in range(3))
    banco.semear("companies", {"id": canal, "company_kind": "platform_canal", "is_technical": True})
    robos = {}
    for c in (a, b):
        banco.semear("companies", {"id": c, "company_kind": "client"})
        banco.semear("multicalculo_adesoes", {"canal_company_id": canal, "corretora_company_id": c, "ativa": True})
        robos[c] = str(uuid4())
        banco.semear("portal_accounts", {
            "id": robos[c], "company_id": c, "portal_key": "agger", "account_label": "robo-1", "username": EMAIL,
            "secret_encrypted": vault.encrypt(SENHA), "robo_estado": "ativo"})
    # A configurou a comissão do empresarial (7,5 %) e a Tokio como preferida no condomínio (como a F2)
    banco.semear("multicalculo_config", {"company_id": a, "config": {
        "comissao": {"por_ramo": {"18": 7.5}}, "preferencias_de_seguradoras": {"16": ["Tokio"]}}})
    porta = MulticalculoProvider(RepositorioMulticalculo(banco.visao("smith-api")),
                                 ambiente={"MULTICALCULO_HMAC_KEY": CHAVE_HMAC}, agora=relogio.agora)
    return SimpleNamespace(banco=banco, relogio=relogio, porta=porta, canal=canal, a=a, b=b, robos=robos, uploads=[])


ROBO_RAPIDO = SimpleNamespace(**{k: getattr(R, k) for k in dir(R) if not k.startswith("__")})
ROBO_RAPIDO.acompanhar = functools.partial(R.acompanhar, intervalo_s=0.05)


def motor(m, nome, nav, d) -> MOT.Motor:
    async def upload(supa, caminho, blob, content_type="application/pdf"):
        assert blob[:4] == b"%PDF"
        m.uploads.append(caminho)
        return caminho

    return MOT.Motor(m.banco.visao(nome), sessoes=S.Sessoes(nav, url_base=d.base), robo=ROBO_RAPIDO, dono=nome,
                     agora=m.relogio.agora, batida_s=1.0, upload=upload, freio=lambda: False, canario=False)


async def com_agger_re(duble, fn):
    d = await duble.iniciar()
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
        if not [c for c in m.banco.linhas("multicalculo_calculos")
                if c["status"] in ("na_fila", "disparando", "calculando")]:
            return
    raise AssertionError("a fila não esvaziou")


def linhas(m, tabela, **filtro):
    return [r for r in m.banco.linhas(tabela) if all(r.get(k) == v for k, v in filtro.items())]


def rodar(coro):
    return asyncio.run(coro)


# =====================================================================================================================
# A contagem INDEPENDENTE — direto no JSON cru da gravação, sem nenhum código do produto
# =====================================================================================================================
def contagem_crua(g: dict, enviadas: set) -> dict:
    """Das seguradoras que o corpo LEVOU: as identidades de oferta (seguradora, identificação, tipo de pacote) com prêmio
    > 0, quem tem preço, quem não tem."""
    ofertas, com, sem = set(), set(), set()
    for it in g["calculos"]:
        s = int(it["seguradora"])
        if s not in enviadas:
            continue
        precos = [r for r in it.get("resultados") or [] if isinstance(r, dict) and (r.get("premio") or 0) > 0]
        for r in precos:
            ofertas.add((s, r.get("identificacao") or "", r.get("packageType")))
        (com if precos else sem).add(s)
    return {"ofertas": ofertas, "com": com, "sem": sem - com}


def elegiveis(g: dict, ramo: int) -> set:
    """As seguradoras do negócio gravado que a conta tem E que o ramo aceita (lista global medida), fora Azul/Aliro —
    a contagem própria da F1 (`_esperadas`)."""
    return F1._esperadas(g, ramo)


# =====================================================================================================================
# 🔴 O TESTE DO FIO — por gravação (as 9): porta → motor → robô/Chromium → Agger dublê → leitor → ofertas → comparação
# =====================================================================================================================
@pytest.mark.parametrize("nome", GRAVACOES)
def test_o_fio_por_ramo_porta_motor_robo_leitor_comparacao(mundo, nome, caplog):
    m = mundo
    caplog.set_level(logging.DEBUG)
    g = carregar(nome)
    ramo = g["ramo"]
    duble = F1._dubleRE(ramo, g, opcoes_de_atividade(nome, g))
    pedido = PED.PedidoDeCalculo.de_dict(dados_da_gravacao(nome), ramo=ramo)

    async def tudo(d, novo_navegador):
        aberto = await m.porta.calcular(company_id=m.a, pedido=pedido, origem="auxiliar")
        mot = motor(m, "motor-1", await novo_navegador(), d)
        await ate_esvaziar(mot, m)
        cfg, andamento = await m.porta._config_e_andamento(company_id=m.a, pedido_id=aberto.pedido_id)
        await mot.desligar()
        return aberto, cfg, andamento, list(d.posts_calcular), dict(d.contagem)

    aberto, cfg, andamento, posts, contagem = rodar(com_agger_re(duble, tudo))
    ped = linhas(m, "multicalculo_pedidos", id=aberto.pedido_id)[0]
    calcs = {c["opcao"]: c for c in linhas(m, "multicalculo_calculos", pedido_id=aberto.pedido_id)}
    assert ped["ramo"] == ramo and set(calcs) == {"padrao", "economica"}
    assert {(c["status"], c["erro"]) for c in calcs.values()} == {("fechado", None)}, \
        [(o, c["status"], c["erro"]) for o, c in calcs.items()]
    # D-129B-03 no RE: a "mais em conta" é a versão 2 do MESMO negócio da padrão
    assert calcs["padrao"]["negocio_ref"] == calcs["economica"]["negocio_ref"]
    assert (calcs["padrao"]["versao"], calcs["economica"]["versao"]) == (1, 2)

    # ── G2/G5: o corpo que SAIU — a forma gravada, a comissão do ramo NO ITEM, a Básica do pedido ──
    assert len(posts) == 2 and contagem.get("POST api-prod/calculo/calcularV2") == 2
    comissao = 7.5 if ramo == 18 else 15.0
    nome_ramo = nome.rsplit("_", 1)[0]
    recentes = [F1._grav(nome_ramo, 1), F1._grav(nome_ramo, 2)]
    basica = g["versao"]["configuracoes"][PED.CHAVE_DA_BASICA]
    for p, opcao in zip(posts, ("padrao", "economica")):
        cot = p["cotacao"]
        assert F1.defeitos_do_corpo_re(cot, ramo, comissao, recentes, duble.config) == []
        assert cot["configuracoes"][PED.CHAVE_DA_BASICA] == basica
        assert cot["configuracoes"]["valorDeNovo"] == 1          # o pedido calou: o "Sim" da tela
        assert cot["configuracoes"]["assist24hs"] == calcs[opcao]["coberturas"]["assist24hs"]
        if g["versao"].get("renovacao") is True:
            assert cot["renovacao"] is True and cot["seguradoraAnteriorId"]
            assert cot["bonusAnterior"] == g["versao"]["bonusAnterior"]
            assert cot["sinistrosAnterior"] == str(int(g["versao"]["sinistrosAnterior"]))
            assert cot["vigFimAnterior"].startswith(str(g["versao"]["vigFimAnterior"])[:10])
    enviadas = {int(i["seguradora"]) for i in posts[0]["cotacao"]["calculos"]}
    assert enviadas == {int(i["seguradora"]) for i in posts[1]["cotacao"]["calculos"]}

    # ── G4: a atividade do empresarial — casa (o código que a PESSOA escolheu) ou SAI listada; nunca um código errado ──
    eventos = list(andamento.eventos)
    sem_ativ = {e["seguradora_codigo"] for e in eventos if e["tipo"] == K.SEM_ATIVIDADE_COMPATIVEL}
    if ramo == 18:
        assert enviadas | sem_ativ == elegiveis(g, ramo) and not (enviadas & sem_ativ)
        humano = F1._escolha_humana(g)
        got = {i["seguradora"]: i["valoresAjusteSeguradora"]["imovelAtividadeProfissionalLocal"]["Key"]
               for i in posts[0]["cotacao"]["calculos"]}
        if humano:
            # 📊 _1: a pessoa escolheu as 8 e o robô escolhe as 8 iguais · _2: 8 de 9 (a Porto, 8, sai)
            assert {s: k for s, k in got.items() if k != humano.get(s)} == {}
        assert not any(str(k).startswith("ISCA") for k in got.values())
        assert sem_ativ == {"empresarial_1": set(), "empresarial_2": {8}, "empresarial_3": sem_ativ}[nome]
        if nome == "empresarial_3":
            assert 3 in sem_ativ                                  # 📊 Mapfre: "PADARIA - CONFEITARIAS" × "- PADARIA"
        for c in calcs.values():                                  # gravado UMA vez por cálculo (motor + narração)
            evs = [e for e in linhas(m, "multicalculo_eventos", calculo_id=c["id"])
                   if e["tipo"] == K.SEM_ATIVIDADE_COMPATIVEL]
            assert sorted(e["seguradora_codigo"] for e in evs) == sorted(sem_ativ)
    else:
        assert enviadas == elegiveis(g, ramo) and sem_ativ == set()

    # ── G1: as ofertas gravadas = a contagem crua das seguradoras que o corpo levou ──
    crua = contagem_crua(g, enviadas)
    for c in calcs.values():
        ofs = linhas(m, "multicalculo_ofertas", calculo_id=c["id"])
        assert {(o["seguradora_codigo"], o["pacote"], o["tipo_de_pacote"]) for o in ofs} == crua["ofertas"], c["opcao"]
        # o leitor DO RAMO: a Básica de RE chegou em cada oferta (com a lista do auto ela some)
        assert all(o["coberturas"].get(PED.CHAVE_DA_BASICA) == basica for o in ofs if nome[-1] != "3"), c["opcao"]
        assert not [e for e in linhas(m, "multicalculo_eventos", calculo_id=c["id"]) if e["tipo"] == R.ERRO_DE_LEITURA]
        assert [e["tipo"] for e in linhas(m, "multicalculo_eventos", calculo_id=c["id"])].count("conjunto_fechado") == 1

    # ── consultar → comparar → o ranking, conferido pela contagem crua ──
    q = C.comparar(andamento.ofertas, andamento.eventos, estados=andamento.estados, config=cfg, ramo=ped["ramo"])
    if nome[-1] != "3":
        assert q.resumo["regua"] == "re"
    ranking = q.ranking()
    assert len(ranking) + len(q.diferentes) == len(crua["com"])
    assert [l["premio_anual"] for l in ranking] == sorted(l["premio_anual"] for l in ranking)
    assert ranking[0]["premio_anual"] == min(l["premio_anual"] for l in ranking)
    atividade = [r for r in q.nao_responderam if r["motivo"] == FRASE_ATIVIDADE]
    assert len(atividade) == len(sem_ativ)                        # "sem atividade compatível" chega ao resumo
    assert q.resumo["nao_responderam"] == len(q.nao_responderam) == len(crua["sem"]) + len(sem_ativ)
    gf = {16: "gravacao_condominio_1", 2: "gravacao_residencial_2", 18: "gravacao_empresarial_2"}[ramo]
    if f"gravacao_{nome}" == gf:
        # 📊 o esperado CONTADO À MÃO pela F2 (ESPERADO), menos quem o robô tirou (a Porto no escritório)
        tirados = {C.nome_de_exibicao(e["seguradora"]) for e in eventos if e["tipo"] == K.SEM_ATIVIDADE_COMPATIVEL}
        esperado = [x for x in F2.ESPERADO[ramo]["ranking"] if x[0] not in tirados]
        assert [(l["seguradora"], l["premio_anual"]) for l in ranking] == esperado
        assert tirados == ({"Porto"} if ramo == 18 else set())

    # ── G8: nenhum dado pessoal no banco nem no log; nenhuma URL; nenhum segredo do dublê ──
    tudo_no_banco = json.dumps({t: m.banco.linhas(t) for t in list(m.banco.tabelas) if t != "portal_accounts"},
                               default=str, ensure_ascii=False)
    for proibido in PROIBIDOS + ("SEGREDO-", "TOKEN-"):
        assert proibido not in tudo_no_banco, proibido
        assert proibido not in caplog.text, proibido
    assert not re.search(r"https?://", tudo_no_banco)


# =====================================================================================================================
# G4 — NENHUMA seguradora casa a atividade: nada sai ao Agger, e quem saiu chega ao resumo (o evento do motor)
# =====================================================================================================================
def test_empresarial_sem_nenhuma_atividade_nada_sai_e_todas_chegam_listadas(mundo):
    m = mundo
    g = carregar("empresarial_2")
    duble = F1._dubleRE(18, g, opcoes_de_atividade("empresarial_2", g))
    pedido = PED.PedidoDeCalculo.de_dict(dados_da_gravacao(
        "empresarial_2", risco={"atividade": "fábrica de fogos de artifício"}), ramo=18)

    async def tudo(d, novo_navegador):
        aberto = await m.porta.calcular(company_id=m.a, pedido=pedido, origem="auxiliar")
        mot = motor(m, "motor-1", await novo_navegador(), d)
        await ate_esvaziar(mot, m)
        cfg, andamento = await m.porta._config_e_andamento(company_id=m.a, pedido_id=aberto.pedido_id)
        await mot.desligar()
        return aberto, cfg, andamento, list(d.posts_calcular)

    aberto, cfg, andamento, posts = rodar(com_agger_re(duble, tudo))
    assert posts == []                                            # nenhum calcularV2 com atividade errada
    calcs = linhas(m, "multicalculo_calculos", pedido_id=aberto.pedido_id)
    assert {c["status"] for c in calcs} == {"falhou"} and all("atividade" in c["erro"] for c in calcs)
    todas = elegiveis(g, 18)
    for c in calcs:
        evs = [e for e in linhas(m, "multicalculo_eventos", calculo_id=c["id"])
               if e["tipo"] == K.SEM_ATIVIDADE_COMPATIVEL]
        assert {e["seguradora_codigo"] for e in evs} == todas and {e["familia"] for e in evs} == {K.DADO}
    q = C.comparar(andamento.ofertas, andamento.eventos, estados=andamento.estados, config=cfg, ramo=18)
    assert q.ranking() == [] and len(q.nao_responderam) == len(todas) == q.resumo["nao_responderam"]
    assert {r["motivo"] for r in q.nao_responderam} == {FRASE_ATIVIDADE}


# =====================================================================================================================
# A RETOMADA de RE — matar o worker DEPOIS do disparo; outro motor só LÊ, com o ramo certo
# =====================================================================================================================
def test_retomada_de_re_le_com_o_ramo_certo_e_nao_reposta(mundo):
    m = mundo
    g = carregar("empresarial_2")
    basica = g["versao"]["configuracoes"][PED.CHAVE_DA_BASICA]
    duble = F1._dubleRE(18, g, opcoes_de_atividade("empresarial_2", g))
    pedido = PED.PedidoDeCalculo.de_dict(dados_da_gravacao("empresarial_2"), ramo=18)

    async def tudo(d, novo_navegador):
        aberto = await m.porta.calcular(company_id=m.a, pedido=pedido, origem="auxiliar")
        nav1 = await novo_navegador()
        m1 = motor(m, "motor-1", nav1, d)

        def matar_na_primeira_oferta(escrita):        # o kill -9: na 1ª OFERTA narrada (os 2 já fizeram checkpoint)
            if escrita.dono == "motor-1" and any(r.get("tipo") == K.NOVA_OFERTA for r in escrita.depois or []):
                m1.supa.morto = True

        m.banco.ao_gravar("multicalculo_eventos", "insert", matar_na_primeira_oferta)
        await m1.uma_volta()
        await asyncio.sleep(1.0)
        await nav1.close()
        assert m1.supa.morto
        calcs = linhas(m, "multicalculo_calculos", pedido_id=aberto.pedido_id)
        assert {c["status"] for c in calcs} == {"calculando"}
        posts_antes = len(d.posts_calcular)
        assert posts_antes == 2
        antes = {c["id"]: len(linhas(m, "multicalculo_ofertas", calculo_id=c["id"])) for c in calcs}
        crua = contagem_crua(g, {int(i["seguradora"]) for i in d.posts_calcular[0]["cotacao"]["calculos"]})
        assert all(n < len(crua["ofertas"]) for n in antes.values()), "a morte não caiu no meio"

        m.relogio.avancar(MOT.LEASE_VENCE_S + 1)
        m2 = motor(m, "motor-2", await novo_navegador(), d)
        await ate_esvaziar(m2, m)
        assert len(d.posts_calcular) == posts_antes, "a retomada fez calcularV2 de novo"
        for c in linhas(m, "multicalculo_calculos", pedido_id=aberto.pedido_id):
            assert (c["status"], c["erro"], c["dono"]) == ("fechado", None, "motor-2"), (c["status"], c["erro"])
            ofs = linhas(m, "multicalculo_ofertas", calculo_id=c["id"])
            assert {(o["seguradora_codigo"], o["pacote"], o["tipo_de_pacote"]) for o in ofs} == crua["ofertas"]
            # 🔴 o RAMO certo na leitura da retomada: a Básica de RE em TODAS as ofertas (a lista do auto a cortaria)
            assert [o["seguradora_codigo"] for o in ofs if o["coberturas"].get(PED.CHAVE_DA_BASICA) != basica] == []
            evs = linhas(m, "multicalculo_eventos", calculo_id=c["id"])
            assert len(evs) == len({e["chave"] for e in evs})
            assert [e["seguradora_codigo"] for e in evs if e["tipo"] == K.SEM_ATIVIDADE_COMPATIVEL] == [8]
        cfg, andamento = await m.porta._config_e_andamento(company_id=m.a, pedido_id=aberto.pedido_id)
        q = C.comparar(andamento.ofertas, andamento.eventos, estados=andamento.estados, config=cfg, ramo=18)
        assert q.resumo["regua"] == "re"
        await m2.desligar()

    rodar(com_agger_re(duble, tudo))


# =====================================================================================================================
# A guarda × o "Salvar rascunho" (B0-a) · o export do erro · o contrato × a tela
# =====================================================================================================================
def test_a_guarda_barra_o_salvar_rascunho_e_qualquer_query_no_calcular():
    est = G.EstadoDaGuarda(host_api="api-prod.agg.localhost")
    url = "http://api-prod.agg.localhost:1/calculo/calcularV2"
    novo = json.dumps({"cotacao": {"id": None, "negocioId": None, "idIntegracao": None}, "negocio": None})
    assert G.decidir("POST", url, novo, est) == (True, "calculo_novo")                  # CONTROLE: o robô passa
    assert G.decidir("POST", url + "?salvar=true", novo, est) == (False, "salvar_rascunho")
    assert G.decidir("POST", url + "?SALVAR=1&x=2", novo, est) == (False, "salvar_rascunho")
    assert G.decidir("POST", url + "?x=2&salvar", novo, est) == (False, "salvar_rascunho")
    assert G.decidir("POST", url + "?debug=1", novo, est) == (False, "calcular_com_query")
    # e o robô nunca põe query: a URL do POST no JS é a do caminho puro
    assert "'/calculo/calcularV2'" in R.JS_ENVIAR and "calcularV2?" not in R.JS_ENVIAR


def test_ramo_nao_suportado_sai_pelo_pacote_da_porta():
    assert PACOTE_DA_PORTA.RamoNaoSuportado is RamoNaoSuportado
    from app.services.multicalculo import RamoNaoSuportado as importado  # noqa: F401


def test_renovacao_de_re_sem_os_quatro_da_tela_nao_chega_ao_agger(mundo):
    m = mundo
    so_seguradora = dados_da_gravacao("condominio_1", renovacao={
        "renovacao": True, "seguradora_anterior": "AXA Seguros", "bonus_anterior": None,
        "sinistros_anterior": None, "fim_vigencia_anterior": None})
    with pytest.raises(PedidoIncompleto) as e:
        rodar(m.porta.calcular(company_id=m.a, pedido=PED.PedidoDeCalculo.de_dict(so_seguradora, ramo=16),
                               origem="auxiliar"))
    assert set(e.value.campos) == {"renovacao.fim_vigencia_anterior", "renovacao.sinistros_anterior",
                                   "renovacao.bonus_anterior"}
    assert m.banco.linhas("multicalculo_pedidos") == []
    # e o robô recusa ANTES de qualquer rede (a 2ª rede: um pedido que chegasse sem eles pela fila)
    bruto = PED.PedidoDeCalculo.de_dict(dados_da_gravacao("condominio_1"), ramo=16).com_comissao(15).para_dict()
    bruto["renovacao"].pop("bonus_anterior")
    with pytest.raises(R.DisparoRecusado, match="bonus_anterior"):
        R.cotacao_do_pedido(bruto)
    # CONTROLE: com os quatro (zero sinistro e bônus 0 são respostas) o corpo monta
    ok = PED.PedidoDeCalculo.de_dict(dados_da_gravacao("condominio_1", renovacao={
        "bonus_anterior": 0, "sinistros_anterior": 0}), ramo=16).com_comissao(15).para_dict()
    cot = R.cotacao_do_pedido(ok)["cotacao"]
    assert (cot["bonusAnterior"], cot["sinistrosAnterior"]) == (0, "0") and cot["vigFimAnterior"]

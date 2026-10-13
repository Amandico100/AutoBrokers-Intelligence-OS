# -*- coding: utf-8 -*-
"""SPEC-131-A · CONSERTO C2 — os guardas dos achados do juiz (B2, B3, P1) e do red team (P3, P4, P5, P6, P10).

Cada guarda nasceu VERMELHO no HEAD `cf12213` e fica VERDE com o conserto:

  J-B3   a licença do Agger vem de onde ela REALMENTE mora: 📊 BLOCO 0 (12/10, escuta de 3 rodadas, fora do git) — o corpo
         do POST `/usuario/login` de um login NORMAL não foi lido em 0 de 4 contextos; o `GET /usuario/current` que o
         próprio app faz trouxe `licenca`/`expirationDate`/`diasParaExpirarSenha` em 4 de 4 (21× em 147 s), e o
         `POST /usuario/login/pdocs` trouxe `dataLimiteCalculo` em 6 de 6. A sessão lê a resposta INTERCEPTADA; sem ela,
         faz UM `GET /usuario/current` na sessão já aberta (nunca `goto`).
  J-B2   moto dentro da sigla AUTO, e frota/RCF-V → `RamoIndisponivel(ramo_nao_cotado)`, nunca o pedido de carro.
  RT-P3  a ficha que não diz a franquia → o `anterior` sai com a NORMAL (não conferida) e a `franquia_reduzida` é opção.
  RT-P4  o Prosseguir só dentro de 00:00–07:00 local: 00:00–23:59 é recusado (volta ao padrão 01:00–06:30).
  RT-P5  o "1× por noite" falha FECHADO: a marca é gravada ANTES do clique; a escrita falhou → Cancelar.
  RT-P6  a guarda exige no Prosseguir o MESMO e-mail do 1º login do contexto.

⛔ Tudo sintético: nenhum login real, nenhuma InfoCap, nenhuma corretora pelo nome (CLAUDE.md §13.9).
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec131a_conserto_c2.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec129b_o_motor as TM  # noqa: E402
import test_spec131a_a_madrugada_no_agger as MNA  # noqa: E402
import test_spec131a_o_perfil as PERF  # noqa: E402
import test_spec131a_o_pedido_da_renovacao as F2T  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)
from test_spec131a_a_madrugada_no_agger import amb  # noqa: E402,F401  (fixture)
from test_spec131a_o_fio import mundo_real  # noqa: E402,F401  (fixture)
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import madrugada as M  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from app.services.multicalculo import perfil_da_renovacao as PR  # noqa: E402
from portal_worker.multicalculo import agger_guarda as G  # noqa: E402
from portal_worker.multicalculo import agger_sessao as S  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402

BRT = timezone(timedelta(hours=-3))

# =====================================================================================================================
# J-B3 · A LICENÇA — a forma REAL, saneada (📊 BLOCO 0, `/usuario/current` da conta de robô, 12/10): as chaves que a
# escuta registrou com os valores medidos; ids, token, e-mail e nome trocados por marcas sintéticas
# =====================================================================================================================
USUARIO_CURRENT_REAL = {
    "id": "uuid-sintetico-0001", "idSessao": "uuid-sintetico-0002", "token": "TOKEN-SINTETICO-DO-CURRENT",
    "email": "robo@exemplo.invalid", "nome": "ROBO SINTETICO",
    "grupoPermissoesUsuario": {"id": "uuid-sintetico-0003", "descricao": "GRUPO"},
    "licenca": "2026-10-20", "expirationDate": "2026-10-27", "statusCorretora": 1, "licencaCortesia": None,
    "qtdeLicenca": 9, "diasParaExpirarSenha": 115, "senhaRequerAlteracao": False, "visualizacaoCalc": False,
    "hub": False, "aplicacaoOrigem": 4, "expires": "1791871295356",
}
#: 📊 o `POST /usuario/login/pdocs` (6/6): `dataLimiteCalculo`, `usuarioRestrito`, `expires` (ms, número) + o token
PDOCS_REAL = {"dataLimiteCalculo": "2026-10-27", "usuarioRestrito": True, "expires": 1791853303754}
LICENCA_ESPERADA = {"licenca": "2026-10-20", "expirationDate": "2026-10-27", "diasParaExpirarSenha": 115,
                    "dataLimiteCalculo": "2026-10-27"}


def test_b3_a_forma_real_do_current_entrega_so_as_datas_da_licenca():
    lic = S.extrair_licenca(USUARIO_CURRENT_REAL)
    assert lic == {"licenca": "2026-10-20", "expirationDate": "2026-10-27", "diasParaExpirarSenha": 115}
    texto = json.dumps(lic)
    for segredo in ("TOKEN", "robo@", "ROBO", "uuid-sintetico"):
        assert segredo not in texto, segredo
    assert S.extrair_licenca(PDOCS_REAL) == {"dataLimiteCalculo": "2026-10-27"}



def _agger_da_licenca(*, app_le_current: bool):
    from aiohttp import web
    from dubles.agger_duble import HTML_COTACOES, HTML_LOGIN, AggerDuble

    # 📊 no app real o corpo do `pdocs` foi lido 6/6 (SPA: a página não recarrega no instante da resposta); o dublê
    # navega na MESMA tarefa e o navegador descarta o corpo — o atraso de 300 ms devolve a forma medida. (Sem ele o
    # `dataLimiteCalculo` se perde e a licença sai só do `current`: por isso o GET de reserva existe.)
    nav = "location.href = '/cotacoes';"
    assert nav in HTML_LOGIN
    html_login = HTML_LOGIN.replace(nav, "setTimeout(() => { location.href = '/cotacoes'; }, 300);")

    linha = "fetch(API + '/calculo/seguradoras', {headers: {Authorization: tApi}}).catch(() => {});"
    assert linha in HTML_COTACOES
    html = HTML_COTACOES.replace(linha, linha + "\nfetch(API + '/usuario/current', {headers: {Authorization: tApi}})"
                                               ".catch(() => {});") if app_le_current else HTML_COTACOES

    class AggerDaLicenca(AggerDuble):
        """O login NORMAL medido: o corpo do POST de login não traz (não se lê) a licença; o `pdocs` traz o limite;
        o `GET /usuario/current` traz a licença — e só é chamado pelo app quando `app_le_current`."""

        async def _tratar(self, req):
            host = (req.host or "").split(":")[0]
            if host == "agg.localhost" and req.path == "/login":
                return web.Response(text=html_login, content_type="text/html")
            if host == "agg.localhost" and req.path == "/cotacoes":
                self.contagem["GET /cotacoes"] = self.contagem.get("GET /cotacoes", 0) + 1
                return web.Response(text=html, content_type="text/html")
            return await super()._tratar(req)

        async def _api(self, req, caminho):
            if caminho == "/usuario/current" and req.method == "GET":
                if not (req.headers.get("Authorization") or "").startswith("TOKEN-API-"):
                    return self._json(req, {"message": "sem token"}, 401)
                return self._json(req, USUARIO_CURRENT_REAL)
            if caminho == "/usuario/login/pdocs" and req.method == "POST":
                r = await super()._api(req, caminho)
                corpo = {**json.loads(r.body), **PDOCS_REAL}
                return self._json(req, corpo, 201)
            return await super()._api(req, caminho)

    return AggerDaLicenca


def _com_agger(classe, fn):
    pw_api = pytest.importorskip("playwright.async_api")

    async def tudo():
        d = await classe().iniciar()
        try:
            async with pw_api.async_playwright() as pw:
                nav = await pw.chromium.launch(headless=True)
                try:
                    return await fn(d, S.Sessoes(nav, url_base=d.base))
                finally:
                    await nav.close()
        finally:
            await d.parar()

    return asyncio.run(tudo())


def test_b3_a_licenca_vem_do_current_que_o_proprio_app_le_sem_chamada_nova():
    from dubles.agger_duble import EMAIL, SENHA

    conta = {"id": "conta-robo-1", "username": EMAIL, "robo_estado": "ativo", "uso": "global"}

    async def corpo(d, sessoes):
        s = await sessoes.obter(conta, senha=SENHA, negocios_do_robo=set())
        lic = dict(s.licenca)
        n_current = d.contagem.get("GET api-prod/usuario/current", 0)
        await sessoes.fechar(conta["id"])
        return lic, n_current, d.contagem.get("GET /cotacoes", 0)

    lic, n_current, n_cotacoes = _com_agger(_agger_da_licenca(app_le_current=True), corpo)
    assert lic == LICENCA_ESPERADA, lic
    assert n_current == 1, f"o robô fez chamada nova ao current ({n_current}); só a do app vale"
    assert n_cotacoes == 1, "goto a mais"


def test_b3_sem_o_app_ler_o_current_um_get_na_sessao_aberta_nunca_goto():
    from dubles.agger_duble import EMAIL, SENHA

    conta = {"id": "conta-robo-2", "username": EMAIL, "robo_estado": "ativo", "uso": "global"}

    async def corpo(d, sessoes):
        s = await sessoes.obter(conta, senha=SENHA, negocios_do_robo=set())
        lic = dict(s.licenca)
        await sessoes.fechar(conta["id"])
        return lic, d.contagem.get("GET api-prod/usuario/current", 0), d.contagem.get("GET /cotacoes", 0)

    lic, n_current, n_cotacoes = _com_agger(_agger_da_licenca(app_le_current=False), corpo)
    assert lic == LICENCA_ESPERADA, lic
    assert n_current == 1, n_current            # UM GET, só
    assert n_cotacoes == 1, "a sessão navegou de novo para ler a licença"


def test_b3_o_motor_grava_um_evento_por_conta_por_dia_com_a_forma_real(amb):
    """O elo sessão → motor → `multicalculo_eventos`: com o que a sessão AGORA entrega (forma real), 1 evento."""
    a = TM.empresa(amb)
    g = MNA.F3.conta_global(amb, a)
    amb.mundo.__dict__.setdefault("licencas", {})[g] = {**S.extrair_licenca(USUARIO_CURRENT_REAL),
                                                        **S.extrair_licenca(PDOCS_REAL)}
    TM.pedido(amb, a, [a], opcoes=("padrao",), origem="auxiliar", expira_min=600)
    TM.rodar(MNA.motor(amb, "m1").uma_volta())
    [ev] = MNA.eventos(amb, MOT.TIPO_LICENCA)
    assert "licenca=2026-10-20" in ev["motivo"] and "dataLimiteCalculo=2026-10-27" in ev["motivo"]
    assert "TOKEN" not in json.dumps(amb.banco.linhas("multicalculo_eventos"), default=str)


# =====================================================================================================================
# J-B2 · MOTO dentro da sigla AUTO, e FROTA/RCF-V (RT-P10) → ramo_nao_cotado, nunca o pedido de carro
# =====================================================================================================================
@pytest.mark.parametrize("sigla", ["FROTA", "AUTO FROTA", "RCFV", "rcfv", "Frota"])
def test_b2_frota_e_rcfv_sao_ramo_nao_cotado(sigla):
    with pytest.raises(PED.RamoIndisponivel) as exc:
        PED._ramo_do_agger(SimpleNamespace(ramo=sigla))
    assert exc.value.motivo == "ramo_nao_cotado" and "renove manualmente" in str(exc.value)


def test_b2_controle_auto_e_carro_continuam_31():
    assert PED._ramo_do_agger(SimpleNamespace(ramo="AUTO")) == PED.RAMO_AUTO
    assert PED._ramo_do_agger(SimpleNamespace(ramo="AUTOMOVEL")) == PED.RAMO_AUTO


@pytest.mark.parametrize("categoria,veiculo", [("Motocicleta", "VEICULO SINTETICO"), ("MOTO", ""),
                                               ("Passeio", "MOTOCICLETA SINTETICA 160"), ("Motoneta", None),
                                               ("Ciclomotor", "X")])
def test_b2_moto_no_item_da_infocap_vira_ramo_nao_cotado_antes_do_pedido(monkeypatch, categoria, veiculo):
    it = {**PERF.item_auto(), "categoria": categoria, "veiculo": veiculo}
    perfil, nao, _rede = PERF._montar(monkeypatch, itens=[it])
    apolice, ficha = PERF.FIO.ficha_sintetica("AUTO")
    with pytest.raises(PED.RamoIndisponivel) as exc:
        PED.de_apolice(apolice, perfil=perfil, ficha=ficha, config=F2T.CONFIG)
    assert exc.value.motivo == "ramo_nao_cotado" and "moto" in str(exc.value).lower()
    assert "renove manualmente" in str(exc.value)


@pytest.mark.parametrize("categoria,veiculo", [("Passeio", "VEICULO SINTETICO"), ("Demais", "MOTORS SINTETICO"),
                                               ("Pick-up", "AUTOMOTOR")])
def test_b2_controle_carro_nao_vira_moto(monkeypatch, categoria, veiculo):
    """📊 F5 (12/10, 10 AUTO): `categoria` Passeio 9 · Demais 1 — nenhuma delas pode cair na regra da moto."""
    it = {**PERF.item_auto(), "categoria": categoria, "veiculo": veiculo}
    perfil, _nao, _rede = PERF._montar(monkeypatch, itens=[it])
    apolice, ficha = PERF.FIO.ficha_sintetica("AUTO")
    pedido = PED.de_apolice(apolice, perfil=perfil, ficha=ficha, config=F2T.CONFIG)
    assert pedido.ramo == PED.RAMO_AUTO


def test_b2_o_fio_a_moto_fica_pendente_ramo_nao_cotado_na_madrugada(mundo_real, monkeypatch):
    """O FIO: InfoCap `/itens` (moto) → `perfil_da_renovacao.montar` → a borda da madrugada → `de_apolice` → o estado."""
    m = mundo_real
    moto = {**PERF.item_auto(), "categoria": "Motocicleta"}
    c, _linhas, _rede = PERF._uma_corretora_com_o_perfil(m, monkeypatch, itens_auto=[moto])
    _item, (estado, motivo, pedido, _dados) = PERF._avaliar(m, c, "AUTO")
    assert (estado, motivo, pedido) == ("pendente", "ramo_nao_cotado", None)


def test_b2_o_fio_controle_o_carro_continua_pronto(mundo_real, monkeypatch):
    m = mundo_real
    c, _linhas, _rede = PERF._uma_corretora_com_o_perfil(m, monkeypatch)
    _item, (estado, motivo, _pedido, dados) = PERF._avaliar(m, c, "AUTO")
    assert (estado, motivo) == ("pronta", None), dados


# =====================================================================================================================
# RT-P3 + J-P1 · a 3ª opção: sem a franquia na ficha, o `anterior` é a NORMAL não conferida
# =====================================================================================================================
def test_p3_ficha_sem_franquia_da_as_tres_opcoes():
    por_opcao, nao = P.coberturas_da_renovacao_auto({}, P.OPCOES_DA_RENOVACAO)
    assert tuple(por_opcao) == ("anterior", "franquia_reduzida", "completa_mais")
    assert por_opcao["anterior"]["tipoFranquia"] == 2 and "tipoFranquia" in nao       # normal, NÃO conferida
    assert por_opcao["franquia_reduzida"]["tipoFranquia"] == 1


def test_p3_pelo_pedido_ficha_sem_franquia_tres_opcoes_e_a_marca():
    pedido = F2T._auto(F2T.FICHA_C)                   # "Casco" sem a palavra da franquia
    assert pedido.opcoes == ("anterior", "franquia_reduzida", "completa_mais")
    assert pedido.coberturas_por_opcao["anterior"]["tipoFranquia"] == 2
    assert "anterior.tipoFranquia" in pedido.nao_conferidos


def test_p3_controle_ficha_que_prova_a_reduzida_cede_o_lugar():
    b = F2T._auto(F2T.FICHA_B)                         # a ficha DIZ "Reduzida": a 3ª seria repetida
    assert b.opcoes == ("anterior", "completa_mais")
    assert "anterior.tipoFranquia" not in b.nao_conferidos


# =====================================================================================================================
# RT-P4 · a janela do Prosseguir só dentro da madrugada (00:00–07:00 local)
# =====================================================================================================================
def _cfg_janela(**janela):
    return CFG.mesclar({"servicos": {"renovacao": {"janela": janela}}}, "renovacao")


def test_p4_config_recusa_0000_2359_e_volta_ao_padrao():
    j = CFG.janela_da_renovacao(_cfg_janela(prosseguir_de="00:00", prosseguir_ate="23:59"))
    assert (j["prosseguir_de"], j["prosseguir_ate"]) == ("01:00", "06:30")
    j = CFG.janela_da_renovacao(_cfg_janela(prosseguir_de="12:00", prosseguir_ate="13:00"))
    assert (j["prosseguir_de"], j["prosseguir_ate"]) == ("01:00", "06:30")
    j = CFG.janela_da_renovacao(_cfg_janela(prosseguir_de="05:00", prosseguir_ate="02:00"))     # de ≥ até
    assert (j["prosseguir_de"], j["prosseguir_ate"]) == ("01:00", "06:30")
    # CONTROLE: dentro da madrugada vale
    j = CFG.janela_da_renovacao(_cfg_janela(prosseguir_de="00:00", prosseguir_ate="07:00"))
    assert (j["prosseguir_de"], j["prosseguir_ate"]) == ("00:00", "07:00")


def test_p4_o_motor_recusa_0000_2359_nos_dois_leitores():
    j = MOT.janela_da_madrugada({"prosseguir_de": "00:00", "prosseguir_ate": "23:59"})
    assert (j["prosseguir_de"], j["prosseguir_ate"]) == ("01:00", "06:30")
    cru = {"prosseguir_de": "00:00", "prosseguir_ate": "23:59"}
    assert not MOT.dentro_do_prosseguir(datetime(2026, 10, 14, 12, 0, tzinfo=BRT), cru, BRT)   # meio-dia: NÃO
    assert not MOT.dentro_do_prosseguir(datetime(2026, 10, 14, 23, 0, tzinfo=BRT), cru, BRT)
    # uma noite só: as duas horas que o red team mediu na mesma "noite" não estão AMBAS dentro
    assert not (MOT.dentro_do_prosseguir(datetime(2026, 10, 14, 11, 0, tzinfo=BRT), cru, BRT)
                and MOT.dentro_do_prosseguir(datetime(2026, 10, 14, 13, 0, tzinfo=BRT), cru, BRT))
    # CONTROLE: 00:00–07:00 vale às 03:00 e não às 07:00
    ok = {"prosseguir_de": "00:00", "prosseguir_ate": "07:00"}
    assert MOT.janela_da_madrugada(ok)["prosseguir_ate"] == "07:00"
    assert MOT.dentro_do_prosseguir(datetime(2026, 10, 14, 3, 0, tzinfo=BRT), ok, BRT)
    assert not MOT.dentro_do_prosseguir(datetime(2026, 10, 14, 7, 0, tzinfo=BRT), ok, BRT)


# =====================================================================================================================
# RT-P5 · a marca ANTES do clique; a escrita falhou → não prossegue
# =====================================================================================================================
def test_p5_a_marca_e_gravada_antes_do_prosseguir(amb):
    a = TM.empresa(amb)
    MNA.F3.conta_global(amb, a)
    dono, conta = MNA.montar_dono(amb, a)
    MNA.na_madrugada(amb)
    amb.mundo.aberta_pela_pessoa = {conta}
    na_reserva = []
    obter_real = MNA.SessoesDaMadrugada.obter

    async def obter(self, c, **kw):
        reserva = kw.get("antes_de_prosseguir")
        if reserva is not None:
            async def espiada():
                ok = await reserva()
                na_reserva.append(len(MNA.eventos(amb, MOT.TIPO_PROSSEGUIU)))   # a marca JÁ está no banco?
                return ok
            kw["antes_de_prosseguir"] = espiada
        return await obter_real(self, c, **kw)

    MNA.SessoesDaMadrugada.obter, salvo = obter, obter_real
    try:
        p = MNA.renovar(amb, a, dono)
        TM.rodar(MNA.motor(amb, "m1").uma_volta())
    finally:
        MNA.SessoesDaMadrugada.obter = salvo
    assert na_reserva == [1], f"a marca não estava gravada antes do Prosseguir: {na_reserva}"
    assert conta not in amb.mundo.aberta_pela_pessoa, "não prosseguiu"
    assert len(MNA.eventos(amb, MOT.TIPO_PROSSEGUIU)) == 1, "2 marcas para 1 Prosseguir"
    assert {c["status"] for c in MNA.calc_do(amb, p.pedido_id)} == {"fechado"}


def test_p5_a_escrita_da_marca_falhou_entao_nao_prossegue(amb, monkeypatch):
    a = TM.empresa(amb)
    MNA.F3.conta_global(amb, a)
    dono, conta = MNA.montar_dono(amb, a)
    MNA.na_madrugada(amb)
    amb.mundo.aberta_pela_pessoa = {conta}
    original = MOT.Motor._gravar_linha_de_evento
    tentou = []

    async def gravar(self, g, c, campos):
        if campos.get("tipo") == MOT.TIPO_PROSSEGUIU:
            tentou.append(1)
            raise RuntimeError("o banco caiu na hora da marca")
        return await original(self, g, c, campos)

    monkeypatch.setattr(MOT.Motor, "_gravar_linha_de_evento", gravar)
    p = MNA.renovar(amb, a, dono)
    TM.rodar(MNA.motor(amb, "m1").uma_volta())
    assert tentou, "a reserva nem foi tentada (a marca ainda nasce DEPOIS do login)"
    assert conta in amb.mundo.aberta_pela_pessoa, "prosseguiu SEM a marca do 1× por noite"
    assert MNA.eventos(amb, MOT.TIPO_PROSSEGUIU) == []
    assert {c["status"] for c in MNA.calc_do(amb, p.pedido_id)} == {"na_fila"}


def test_p5_sessao_real_sem_reserva_ou_com_reserva_falhando_cancela():
    """Chromium + o Agger dublê do BLOCO 0 A1: a reserva é chamada ANTES do POST que derruba; sem ela, Cancelar."""
    from dubles.agger_duble import EMAIL, SENHA

    pessoa = {"id": "conta-da-pessoa-c2", "username": EMAIL, "robo_estado": "ativo", "uso": "membro"}

    async def corpo(d, sessoes):
        with pytest.raises(S.SessaoOcupada):                       # sem a reserva: fail-closed
            await sessoes.obter(pessoa, senha=SENHA, negocios_do_robo=set(), prosseguir=True)
        assert d.derrubadas == []

        async def falha():
            return False

        with pytest.raises(S.SessaoOcupada):                       # a reserva falhou: Cancelar
            await sessoes.obter(pessoa, senha=SENHA, negocios_do_robo=set(), prosseguir=True,
                                antes_de_prosseguir=falha)
        assert d.derrubadas == []
        vistos = []

        async def ok():
            vistos.append(len(d.derrubadas))                       # a reserva vem ANTES do POST que derruba
            return True

        s = await sessoes.obter(pessoa, senha=SENHA, negocios_do_robo=set(), prosseguir=True,
                                antes_de_prosseguir=ok)
        assert vistos == [0] and d.derrubadas == [MNA.ID_DO_AVISO] and s.prosseguiu is True
        await sessoes.fechar(pessoa["id"])

    _com_agger(MNA._agger_a1(), corpo)


# =====================================================================================================================
# RT-P6 · o e-mail do Prosseguir é o do 1º login do contexto
# =====================================================================================================================
def test_p6_a_guarda_exige_o_email_do_primeiro_login():
    e = MNA._estado(prosseguir_permitido=True)
    primeiro = json.dumps({"email": "Pessoa@Exemplo.invalid", "senha": "s"})
    assert G.decidir("POST", MNA.API + "/usuario/login", primeiro, e) == (True, "login")
    e.logins = 1
    e.registrar_sessao_ativa(MNA.ID_DO_AVISO)
    # sem o e-mail do 1º login registrado: barra (fail-closed)
    assert G.decidir("POST", MNA.API + "/usuario/login", MNA._prosseguir(), e)[0] is False
    e.registrar_email_do_login(primeiro)
    outro = json.dumps({"email": "outra@exemplo.invalid", "senha": "s", "derrubaSessao": MNA.ID_DO_AVISO})
    assert G.decidir("POST", MNA.API + "/usuario/login", outro, e)[0] is False, "Prosseguir com OUTRO e-mail"
    mesmo = json.dumps({"email": " pessoa@exemplo.INVALID ", "senha": "s", "derrubaSessao": MNA.ID_DO_AVISO})
    assert G.decidir("POST", MNA.API + "/usuario/login", mesmo, e) == (True, "prosseguir")   # CONTROLE
    assert "pessoa@" not in repr(e) and "Pessoa@" not in json.dumps(e.contagem())           # só o hash fica


def test_p6_instalar_registra_o_email_so_do_primeiro_login():
    e = MNA._estado(prosseguir_permitido=True)
    e.registrar_email_do_login(json.dumps({"email": "a@exemplo.invalid", "senha": "s"}))
    e.registrar_email_do_login(json.dumps({"email": "b@exemplo.invalid", "senha": "s"}))   # o 2º não troca
    e.logins = 1
    e.registrar_sessao_ativa(MNA.ID_DO_AVISO)
    b = json.dumps({"email": "b@exemplo.invalid", "senha": "s", "derrubaSessao": MNA.ID_DO_AVISO})
    a = json.dumps({"email": "a@exemplo.invalid", "senha": "s", "derrubaSessao": MNA.ID_DO_AVISO})
    assert G.decidir("POST", MNA.API + "/usuario/login", b, e)[0] is False
    assert G.decidir("POST", MNA.API + "/usuario/login", a, e) == (True, "prosseguir")


# --- gerente (13/10): a moto pelo tipo que o Agger devolve na placa (o sinal que o C2 apontou e não era dele) ---
def test_moto_pela_placa_recusa_antes_de_enviar_e_a_madrugada_a_ve_como_definitiva():
    from portal_worker.multicalculo import agger_robo as AR
    from app.services.multicalculo import madrugada as M

    # o preparo recusa a moto antes do POST (o guarda mora no JS que roda na página do Agger)
    js = AR.JS_PREPARAR if hasattr(AR, "JS_PREPARAR") else open(AR.__file__, encoding="utf-8").read()
    assert "erro: 'veiculo_moto'" in js and "tipoVeic" in js
    texto = AR._recusa_do_preparo("veiculo_moto")
    motivo = str(texto)
    assert motivo.startswith("veiculo_moto — "), motivo
    # linha de controle: outro código de preparo NÃO vira recusa de veículo definitiva
    assert not str(AR._recusa_do_preparo("nenhuma_seguradora")).startswith("veiculo_")
    # a madrugada lê a cabeça "veiculo_…" como definitiva (não recalcula toda noite)
    assert M.falhou_definitivo("veiculo_moto")

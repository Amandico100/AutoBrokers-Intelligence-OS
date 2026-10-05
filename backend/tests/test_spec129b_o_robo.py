# -*- coding: utf-8 -*-
"""SPEC-129-B F2 — o robô do Agger e o cofre do worker (G3 · G5 · G9 + o TESTE DO FIO da fatia).

O FIO: Chromium REAL → Agger DUBLÊ (tests/dubles/agger_duble.py, com as fixtures saneadas da 128) → login pela TELA
(`Sessoes.obter`) → `disparar` (corpo montado NA PÁGINA pelo montador.js a partir do `calculo/seguradoras` do dublê)
→ o dublê registra o corpo → `acompanhar` (GET calculos/{id}/{v} NA PÁGINA, filtrado pela lista branca) →
`leitor_agger` REAL → eventos → `recalcular` → `copiar_pdfs` → `fechar` (logout).

🔴 G5: toda chamada a `Page.evaluate` passa por uma ESPIA (monkeypatch na classe do Playwright): nenhum segredo
falso do dublê (`SEGREDO-…`, `TOKEN-…`) pode aparecer no que voltou ao Python, nos eventos/ofertas ou no log.
Nada aqui imprime dado pessoal: o pedido é fictício e nunca é impresso.
"""
from __future__ import annotations

import asyncio
import collections
import json
import logging
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

pw_api = pytest.importorskip("playwright.async_api")

from portal_worker.multicalculo import agger_guarda as G  # noqa: E402
from portal_worker.multicalculo import agger_robo as R  # noqa: E402
from portal_worker.multicalculo import agger_sessao as S  # noqa: E402
from portal_worker.multicalculo import contrato as C  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402
from portal_worker.multicalculo.leitor_agger import (  # noqa: E402
    classificar_mensagens, eventos_do_calculo, ler_rodada,
)
from dubles.agger_duble import EMAIL, SENHA, USUARIO_ROBO, AggerDuble  # noqa: E402

SEGREDOS = ("SEGREDO-", "TOKEN-")


def pedido_ficticio(**extra):
    p = {
        "ramo": 31,
        "segurado": {"cpf_cnpj": "00000000191", "nome": "Pessoa Ficticia", "nascimento": "1980-01-01", "sexo": "F",
                     "estado_civil": 2, "cep": "88000000"},
        "veiculo": {"placa": "TST1A23", "ano_modelo": 2012},
        "pernoite": {}, "condutor": {"tempo_habilitacao": 11, "relacao_com_segurado": "proprio"},
        "renovacao": {}, "coberturas": {}, "pacotes": {}, "comissao_desconto": {"comissao_percentual": 15},
        "questionario": {}, "seguradoras": [], "assumidos": [],
    }
    for k, v in extra.items():
        p[k] = v
    return p


CONTA = {"id": "conta-robo-1", "username": EMAIL, "robo_estado": "teste"}


class Espia:
    """Registra o JSON de TODO retorno de `Page.evaluate` (a classe, não a instância: pega qualquer chamador)."""

    def __init__(self, monkeypatch):
        self.retornos = []
        original = pw_api.Page.evaluate
        espia = self

        async def evaluate(pagina, *a, **k):
            r = await original(pagina, *a, **k)
            espia.retornos.append(json.dumps(r, ensure_ascii=False, default=str))
            return r

        monkeypatch.setattr(pw_api.Page, "evaluate", evaluate)

    def vazamentos(self):
        return [s for s in SEGREDOS for r in self.retornos if s in r]


async def _com_agger(fn, *, modo_login="ok"):
    d = await AggerDuble(modo_login=modo_login).iniciar()
    try:
        async with pw_api.async_playwright() as pw:
            nav = await pw.chromium.launch(headless=True)
            try:
                return await fn(d, S.Sessoes(nav, url_base=d.base))
            finally:
                await nav.close()
    finally:
        await d.parar()


def _assinatura(e):
    o = e.oferta
    return (e.tipo, e.seguradora_codigo, e.familia, o.pacote if o else None, round(o.premio_total, 2) if o else None)


# ======================================================================================================================
# O TESTE DO FIO
# ======================================================================================================================
def test_o_fio_do_login_ao_logout(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    espia = Espia(monkeypatch)
    fx_rodadas = [ler_rodada(r) for r in AggerDuble().calculos_fx[0]["rodadas"]]
    puro = [_assinatura(e) for e in eventos_do_calculo(fx_rodadas)]

    async def corpo(d, sessoes):
        sessao = await sessoes.obter(CONTA, senha=SENHA, negocios_do_robo=set())
        # padrão: negócio NOVO
        disp = await R.disparar(sessao, pedido_ficticio(), P.coberturas_de("padrao"))
        assert disp.versao == 1 and disp.negocio_ref in d.negocios
        post = d.posts_calcular[-1]
        cot = post["cotacao"]
        # o corpo que o Agger recebe TEM as credenciais da config (o Agger exige) — montadas na página
        assert all(i.get("loginWs", "").startswith("SEGREDO-") for i in cot["calculos"])
        assert sorted(i["seguradora"] for i in cot["calculos"]) == d.codigos_do_pedido
        assert all(i["vidros"] == 2 and i["tipoFranquia"] == 1 and i["percComissao"] == 15 for i in cot["calculos"]
                   if i["seguradora"] != 45)
        assert post["negocio"] is None and cot.get("idIntegracao") is None
        assert post["correlationId"].startswith(R.PREFIXO_DA_MARCA) and cot["correlationId"] == post["correlationId"]
        assert cot["automoveis"][0]["fipeTxt"] == "null" and cot["automoveis"][0]["descricao"]
        # econômica: versão do MESMO negócio (o disparo da padrão registrou o negócio na guarda)
        eco = await R.disparar(sessao, pedido_ficticio(), P.coberturas_de("economica"), negocio_ref=disp.negocio_ref)
        assert (eco.negocio_ref, eco.versao) == (disp.negocio_ref, 2)
        assert all(i["vidros"] == 1 for i in d.posts_calcular[-1]["cotacao"]["calculos"])
        assert d.posts_calcular[-1]["negocio"]["id"] == d.posts_calcular[-1]["cotacao"]["negocioId"]
        # acompanhar → os eventos do leitor PURO sobre a mesma fixture
        eventos, quadros = [], []

        async def ao_evento(e):
            eventos.append(e)

        async def ao_quadro():
            quadros.append(1)

        final = await R.acompanhar(sessao, disp, ao_evento=ao_evento, ao_quadro=ao_quadro, intervalo_s=0.05,
                                   quadro_s=0.3, teto_s=60)
        assert final.fechado and quadros == [1]
        assert collections.Counter(_assinatura(e) for e in eventos) == collections.Counter(puro)
        assert [e.tipo for e in eventos].count(C.CONJUNTO_FECHADO) == 1
        # retomada: `anterior` montado → nenhum evento repetido
        de_novo = []

        async def ao_evento2(e):
            de_novo.append(e)

        await R.acompanhar(sessao, disp, ao_evento=ao_evento2, anterior=final, intervalo_s=0.05, teto_s=60)
        assert de_novo == []
        # recálculo da padrão com ajuste
        rec = await R.recalcular(sessao, disp.negocio_ref, versao_base=1, ajuste=C.Ajuste("franquia", 2))
        assert rec.versao == 3
        rpost = d.posts_calcular[-1]
        assert rpost["cotacao"]["versao"] == 1 and all(i["tipoFranquia"] == 2 for i in rpost["cotacao"]["calculos"])
        assert all(i["vidros"] == 2 for i in rpost["cotacao"]["calculos"])   # partiu da padrão, não da econômica
        # PDFs: bytes, e a URL não voltou
        pdfs = await R.copiar_pdfs(sessao, disp)
        assert pdfs and all(b[:4] == b"%PDF" for b in pdfs.values())
        com_pdf = {(o.seguradora_codigo, o.pacote, o.tipo_de_pacote) for o in final.ofertas if o.tem_pdf}
        assert set(pdfs) <= com_pdf and len(pdfs) >= 1
        # a guarda: telemetria barrada; 2º login barrado (uma tentativa DENTRO da página)
        await sessao.pagina.evaluate(
            "async (api) => { try { await fetch(api + '/usuario/login', {method: 'POST', body: '{}'}) } catch (e) {} }",
            sessao.bases["api"])
        cont = sessao.contagem_de_escritas()
        assert cont["calcularV2"] == 3 and cont["login"] == 1
        assert sessao.estado_da_guarda.motivos_barrados.get("segundo_login") == 1
        assert sessao.estado_da_guarda.motivos_barrados.get("escrita_fora_da_lista_branca", 0) >= 1   # telemetria
        assert d.contagem.get("POST api-prod/telemetria/eventos", 0) == 0
        assert len(d.logins) == 1
        await sessoes.fechar(CONTA["id"])
        assert d.contagem.get("POST api-prod/usuario/deslogaSessao") == 1
        return eventos, final

    eventos, final = asyncio.run(_com_agger(corpo))
    # 🔴 G5 — nada do que voltou da página, nem os eventos, nem o log, carrega segredo
    assert espia.retornos, "a espia não viu nenhum evaluate"
    assert espia.vazamentos() == []
    texto_eventos = repr(eventos) + repr(final)
    assert [s for s in SEGREDOS if s in texto_eventos] == []
    assert "http" not in repr(final.ofertas)
    assert [s for s in SEGREDOS + (SENHA, EMAIL) for r in caplog.records if s in r.getMessage()] == []


# ======================================================================================================================
# recálculo a partir da versão CERTA · negócio que não é do robô
# ======================================================================================================================
def test_recalcular_parte_da_versao_base_e_a_guarda_barra_negocio_alheio(monkeypatch):
    espia = Espia(monkeypatch)

    async def corpo(d, sessoes):
        ref = d.semear_negocio([
            {"versao": 1, "correlationId": R.correlation_id(), "percComissao": 15, "coberturas": {"vidros": 2, "tipoFranquia": 1}},
            {"versao": 2, "correlationId": R.correlation_id(), "percComissao": 20, "coberturas": {"vidros": 0, "tipoFranquia": 2}},
        ])
        alheio = d.semear_negocio([{"versao": 1, "correlationId": "11112222-3333-4444-a555-666677778888"}])
        sessao = await sessoes.obter(CONTA, senha=SENHA, negocios_do_robo={ref})
        for base, vidros, comissao in ((1, 2, 15), (2, 0, 20)):
            r = await R.recalcular(sessao, ref, versao_base=base, ajuste=C.Ajuste("assistencia", 4))
            itens = d.posts_calcular[-1]["cotacao"]["calculos"]
            assert d.posts_calcular[-1]["cotacao"]["versao"] == base
            assert {i["vidros"] for i in itens} == {vidros}
            assert {i["percComissao"] for i in itens if i["seguradora"] != 45} == {comissao}
            assert {i["assist24hs"] for i in itens} == {4}
            assert r.versao == base + 2 or r.versao == 3 + (base - 1)
        n = len(d.posts_calcular)
        # G3 ao vivo: negócio que NÃO é do robô → a guarda aborta; nada chega ao Agger
        with pytest.raises(R.DisparoRecusado):
            await R.recalcular(sessao, alheio, versao_base=1, ajuste=C.Ajuste("franquia", 2))
        with pytest.raises(R.DisparoRecusado):
            await R.disparar(sessao, pedido_ficticio(), P.coberturas_de("economica"), negocio_ref=alheio)
        assert len(d.posts_calcular) == n
        assert sessao.estado_da_guarda.motivos_barrados.get("negocio_que_nao_e_do_robo") == 2
        # linha de CONTROLE: registrado, o mesmo pedido passa
        sessao.registrar_negocio(alheio)
        await R.recalcular(sessao, alheio, versao_base=1, ajuste=C.Ajuste("franquia", 2))
        assert len(d.posts_calcular) == n + 1
        # versão-base que não existe → recusado ANTES do POST
        with pytest.raises(R.DisparoRecusado):
            await R.recalcular(sessao, ref, versao_base=99, ajuste=C.Ajuste("franquia", 2))
        assert len(d.posts_calcular) == n + 1

    asyncio.run(_com_agger(corpo))
    assert espia.vazamentos() == []


def test_disparo_incerto_e_recusado(monkeypatch):
    async def corpo(d, sessoes):
        sessao = await sessoes.obter(CONTA, senha=SENHA, negocios_do_robo=set())
        d.status_calcular = 503
        with pytest.raises(R.DisparoIncerto):
            await R.disparar(sessao, pedido_ficticio(), P.coberturas_de("padrao"))
        d.status_calcular = 422
        with pytest.raises(R.DisparoRecusado):
            await R.disparar(sessao, pedido_ficticio(), P.coberturas_de("padrao"))
        n = len(d.posts_calcular)
        with pytest.raises(R.DisparoRecusado):   # pedido sem CEP → recusado ANTES de qualquer rede
            await R.disparar(sessao, pedido_ficticio(segurado={"cpf_cnpj": "00000000191", "nome": "X"}), {})
        assert len(d.posts_calcular) == n

    asyncio.run(_com_agger(corpo))


# ======================================================================================================================
# a regra "pessoa mexeu" (D-MC-47, §4.1)
# ======================================================================================================================
def test_pessoa_mexeu_recentemente(monkeypatch):
    espia = Espia(monkeypatch)

    async def corpo(d, sessoes):
        cid = R.correlation_id
        so_robo = d.semear_negocio([{"versao": 1, "correlationId": cid()}, {"versao": 2, "correlationId": cid()}])
        pessoa = d.semear_negocio([{"versao": 1, "correlationId": cid()},
                                   {"versao": 2, "correlationId": "11112222-3333-4444-a555-666677778888"}])
        pessoa_antiga = d.semear_negocio([{"versao": 1, "correlationId": cid()},
                                          {"versao": 2, "correlationId": "11112222-3333-4444-a555-666677778888",
                                           "criada_ha_h": 30}])
        outro_usuario = d.semear_negocio([{"versao": 1, "correlationId": cid()},
                                          {"versao": 2, "correlationId": cid(), "usuarioId": "usr-pessoa"}])
        sessao = await sessoes.obter(CONTA, senha=SENHA, negocios_do_robo=set())
        f = R.pessoa_mexeu_recentemente
        assert await f(sessao, so_robo, versoes_do_robo={1, 2}) is False          # CONTROLE
        assert await f(sessao, pessoa, versoes_do_robo={1}) is True
        assert await f(sessao, pessoa_antiga, versoes_do_robo={1}) is False      # fora das 24 h
        assert await f(sessao, pessoa_antiga, horas=48, versoes_do_robo={1}) is True
        # usuarioId só separa robô de pessoa com login de ROBÔ (conta `ativo`); com login de pessoa (`teste`), não
        assert await f(sessao, outro_usuario, versoes_do_robo={1}) is False
        sessao.robo_estado = "ativo"
        assert await f(sessao, outro_usuario, versoes_do_robo={1}) is True
        assert await f(sessao, so_robo, versoes_do_robo={1, 2}) is False          # CONTROLE com `ativo`
        assert await f(sessao, "negocio-que-nao-existe", versoes_do_robo=set()) is True   # na dúvida: mexeu

    asyncio.run(_com_agger(corpo))
    assert espia.vazamentos() == [] and not any(USUARIO_ROBO in r or "usr-pessoa" in r for r in espia.retornos)


# ======================================================================================================================
# o login: sessão ativa → Cancelar; senha recusada
# ======================================================================================================================
def test_aviso_de_sessao_ativa_cancela_e_nunca_prossegue():
    async def corpo(d, sessoes):
        with pytest.raises(S.SessaoOcupada):
            await sessoes.obter(CONTA, senha=SENHA, negocios_do_robo=set())
        return d.logins, d.contagem.get("GET /marca/prosseguiu", 0)

    logins, prosseguiu = asyncio.run(_com_agger(corpo, modo_login="sessao_ativa"))
    assert logins == [{"forcar": False}]          # 1 login, NENHUM "prosseguir/forçar"
    assert prosseguiu == 0                        # e o botão "Prosseguir" NUNCA foi clicado


def test_senha_recusada_uma_tentativa():
    async def corpo(d, sessoes):
        with pytest.raises(S.CredencialRecusada):
            await sessoes.obter(CONTA, senha="senha-errada", negocios_do_robo=set())
        return d.logins

    assert asyncio.run(_com_agger(corpo, modo_login="senha_errada")) == [{"forcar": False}]


# ======================================================================================================================
# G3 — a guarda, PURA
# ======================================================================================================================
API = "https://api-prod.aggilizador.com.br"


def _estado(**kw):
    e = G.EstadoDaGuarda(host_api="api-prod.aggilizador.com.br")
    for k, v in kw.items():
        setattr(e, k, v)
    return e


def _corpo(ref=None, neg=None, cot_id=None, neg_id=None):
    return json.dumps({"cotacao": {"idIntegracao": ref, "id": cot_id, "negocioId": neg_id}, "negocio": neg})


@pytest.mark.parametrize("metodo,url,corpo,esperado", [
    ("GET", API + "/calculo/seguradoras", None, (True, "leitura")),
    ("POST", API + "/calculo/print", "{}", (False, "escrita_fora_da_lista_branca")),
    ("DELETE", API + "/calculo/negocio/x", "", (False, "escrita_fora_da_lista_branca")),
    ("POST", "https://telemetria.exemplo.com/collect", "{}", (False, "escrita_fora_da_api")),
    ("POST", "https://pdocs.aggilizador.com.br/calculo/calcularV2", _corpo(), (False, "escrita_fora_da_api")),
    ("GET", API + "/usuario/derrubarSessao", None, (False, "derruba_sessao")),
    ("POST", API + "/usuario/login", '{"email":"x","forcarLogin":true}', (False, "derruba_sessao")),
    ("POST", API + "/usuario/login", '{"email":"x","senha":"y"}', (True, "login")),
    ("POST", API + "/usuario/deslogaSessao", "{}", (True, "logout")),
    ("POST", API + "/calculo/calcularV2", _corpo(), (True, "calculo_novo")),
    ("POST", API + "/calculo/calcularV2", _corpo("abc-1", {"id": "n1"}, "v1", "n1"), (False, "negocio_que_nao_e_do_robo")),
    ("POST", API + "/calculo/calcularV2", "isto não é json", (False, "corpo_ilegivel")),
])
def test_g3_decidir(metodo, url, corpo, esperado):
    assert G.decidir(metodo, url, corpo, _estado(), agora=1000.0) == esperado


def test_g3_negocio_registrado_segundo_login_e_pdocs_por_hora():
    e = _estado()
    c = _corpo("ABC-1", {"id": "n1"}, "v1", "n1")
    assert G.decidir("POST", API + "/calculo/calcularV2", c, e)[0] is False
    e.registrar_negocio("abc1")                                    # normalizado: sem hífen, minúsculo
    # conserto 129-B: o negócio é do robô, mas os ids que o Agger deu para ele ainda não foram conferidos → barra
    assert G.decidir("POST", API + "/calculo/calcularV2", c, e) == (False, "ids_de_negocio_nao_conferidos")
    e.registrar_ids("ABC-1", negocio_id="n1", versao_id="v1")      # o que `versoes/{ref}` deu, antes do POST
    assert G.decidir("POST", API + "/calculo/calcularV2", c, e) == (True, "calculo_do_robo")
    assert G.decidir("POST", API + "/calculo/calcularV2", _corpo("ABC-1", {"id": "OUTRO"}, "v1", "n1"), e) == (
        False, "ids_de_negocio_incoerentes")
    e.logins = 1
    assert G.decidir("POST", API + "/usuario/login", "{}", e) == (False, "segundo_login")
    e.pdocs.extend([100.0 + i for i in range(6)])
    assert G.decidir("POST", API + "/usuario/login/pdocs", "", e, agora=200.0) == (False, "pdocs_demais")   # 7º na hora
    assert G.decidir("POST", API + "/usuario/login/pdocs", "", e, agora=100.0 + 3601) == (True, "pdocs")   # passou 1 h


# ======================================================================================================================
# a 2ª rede em Python · leitor · presets · cofre
# ======================================================================================================================
def test_separar_itens_descarta_o_que_escapou_da_lista_branca():
    fx = AggerDuble().calculos_fx[0]["rodadas"][-1]
    limpo = fx if isinstance(fx, list) else fx["corpo"]
    ok, sujos = R.separar_itens(limpo)
    assert len(ok) == len(limpo) and sujos == []                  # CONTROLE: a fixture saneada passa inteira
    cru = json.loads(json.dumps(limpo))
    cru[0]["loginWs"] = "SEGREDO-LOGINWS-x"                       # chave fora da lista
    cru[1]["resultados"] = [dict(r, pathPdf="https://quotation-files.aggilizador.com.br/SEGREDO-PDF.pdf")
                            for r in (cru[1].get("resultados") or [{"premio": 1}])]
    ok, sujos = R.separar_itens(cru)
    assert len(ok) == len(limpo) - 2 and len(sujos) == 2


def test_leitor_as_duas_familias_do_bloco0():
    assert classificar_mensagens(["Risco sem aceitação para este cenário nesta seguradora"]) == C.ACEITACAO
    vidros = "Cobertura HDI Auto Vidros não pode ser contratada. Favor, recalcular"
    assert classificar_mensagens([vidros]) == C.DADO
    assert classificar_mensagens(["Erro ao executar serviço: 105 - Read terminated", vidros]) == C.DADO
    assert classificar_mensagens(["Erro ao executar serviço: 105 - Read terminated"]) == C.INSTABILIDADE   # controle


def test_presets_sao_copias_e_a_economica_so_mexe_no_que_barateia():
    pad, eco = P.coberturas_de("padrao"), P.coberturas_de("economica")
    assert set(pad) == set(eco) == set(P.CHAVES_DE_COBERTURA)
    assert {k for k in pad if pad[k] != eco[k]} == {"tipoFranquia", "vidros", "carroReserva", "assist24hs"}
    pad["vidros"] = 0
    assert P.coberturas_de("padrao")["vidros"] == 2
    with pytest.raises(ValueError):
        P.coberturas_de("ajuste")


def test_g9_cofre_de_duas_chaves(monkeypatch):
    from cryptography.fernet import Fernet, InvalidToken

    from portal_worker import vault
    velha, nova = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    monkeypatch.setenv("PORTAL_VAULT_KEY", velha)
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    cifrado_antes = vault.encrypt("segredo-de-portal")
    assert vault.decrypt(cifrado_antes) == "segredo-de-portal"            # sem a anterior: idêntico a hoje
    monkeypatch.setenv("PORTAL_VAULT_KEY", nova)
    with pytest.raises(InvalidToken):                                      # CONTROLE: só a nova não abre o velho
        vault.decrypt(cifrado_antes)
    monkeypatch.setenv("PORTAL_VAULT_KEY_ANTERIOR", velha)
    assert vault.decrypt(cifrado_antes) == "segredo-de-portal"            # a anterior decifra
    cifrado_novo = vault.encrypt("outro")
    assert Fernet(nova.encode()).decrypt(cifrado_novo.encode()) == b"outro"   # cifra nova sai na ATUAL
    with pytest.raises(InvalidToken):
        Fernet(velha.encode()).decrypt(cifrado_novo.encode())
    monkeypatch.setenv("PORTAL_VAULT_KEY_ANTERIOR", "nao-e-chave")
    with pytest.raises(RuntimeError) as e:
        vault.decrypt(cifrado_antes)
    assert "nao-e-chave" not in str(e.value)

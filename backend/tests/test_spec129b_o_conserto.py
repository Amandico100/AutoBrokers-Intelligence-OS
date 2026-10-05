# -*- coding: utf-8 -*-
"""SPEC-129-B — o CONSERTO ÚNICO (protocolo §5 ⑤): os ataques do juiz e do red team como guardas PERMANENTES.

Cada teste reproduz um achado dos laudos (o mesmo cenário dos scripts `scratchpad/redteam/test_rt_*.py` e da medição
do juiz) e afirma o comportamento CERTO — vermelho antes do conserto, verde depois — com linha de CONTROLE onde o
guarda compara duas coisas (CLAUDE.md §9.3: prove que elas CONSEGUEM ser diferentes).

    juiz B1 · leitura que nunca leu NÃO vira `fechado`; 401/403 descarta a sessão
    juiz B2 · a porta entrega o PDF (do NOSSO bucket), com 2 tenants
    red  B1 · a pausa do Founder não é desfeita pelo motor (A1)
    red  B2 · adesão desativada não deixa sair POST no login da corretora (A2)
    red  B3 · credencial ecoada em texto livre não chega ao banco (A3, fio com Chromium)
    red  B4 · todo disparo em negócio existente confere a D-MC-47 (A8)
    itens 7–13 · guarda (A5) · motivo saneado · comando · login sem desfecho · retomada de teste · recálculo
                 duplicado (A6) · canário só com os pedidos dele · grupo partido na mesma conta

O MOTOR, a PORTA e o ROBÔ são reais; dublê só na borda (o banco PostgREST em memória, o Agger, o storage).
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec129b_o_conserto.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec129b_o_motor as TM  # noqa: E402
from test_spec129b_o_motor import ambiente  # noqa: E402,F401  (fixture)
from app.services.multicalculo import MulticalculoProvider, NaoEncontrado  # noqa: E402
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402
from portal_worker.multicalculo import agger_guarda as G  # noqa: E402
from portal_worker.multicalculo import agger_robo as R  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402
from portal_worker.multicalculo import robos as ROB  # noqa: E402

rodar = TM.rodar
T0 = TM.T0


# =====================================================================================================================
# juiz B1 — "não consegui ler" nunca vira `fechado`
# =====================================================================================================================
class _SessaoQueLe(TM.SessaoDuble):
    """Uma sessão para o `acompanhar` REAL do robô: `avaliar` devolve o que o roteiro mandar, em ordem."""

    def __init__(self, conta_id, negocios, roteiro):
        super().__init__(conta_id, negocios)
        self.roteiro = list(roteiro)
        self.bases = {"api": "https://api-prod.agg.invalid", "pdocs": "https://pdocs.agg.invalid"}
        self.pagina = SimpleNamespace(is_closed=lambda: False)

    def token(self, _qual):
        return "TOKEN-FICTICIO"

    async def garantir_token(self):
        return None

    async def avaliar(self, _js, _arg=None):
        passo = self.roteiro.pop(0) if len(self.roteiro) > 1 else self.roteiro[0]
        if isinstance(passo, BaseException):
            raise passo
        return passo


def test_juiz_b1_o_acompanhar_real_levanta_quando_nao_le():
    import time

    disparo = R.Disparo(negocio_ref="NEG-1", versao=1, t0=time.time())
    eventos = []

    async def ao_evento(e):
        eventos.append(e)

    async def acompanhar(roteiro, **kw):
        s = _SessaoQueLe("c1", set(), roteiro)
        return await R.acompanhar(s, disparo, ao_evento=ao_evento, intervalo_s=0, **kw)

    # 401 na 1ª leitura → sessão MORTA, nada lido (a medição do juiz: antes, `fechado=False, respostas=0` em silêncio)
    with pytest.raises(R.LeituraImpossivel) as e401:
        rodar(acompanhar([{"status": 401}]))
    assert e401.value.sessao_morta and not e401.value.leu and not e401.value.quadro_saiu
    # rede/página quebrando sem parar → para em LEITURAS_FALHAS_MAX, sem esperar os 480 s
    with pytest.raises(R.LeituraImpossivel) as erede:
        rodar(acompanhar([RuntimeError("rede")]))
    assert not erede.value.sessao_morta and not erede.value.leu
    # teto sem NENHUMA leitura válida (5xx no meio, teto curto) → também levanta
    with pytest.raises(R.LeituraImpossivel):
        rodar(acompanhar([{"status": 502}], teto_s=0))
    # CONTROLE: uma leitura válida (lista vazia) e o teto → devolve a rodada, não levanta
    rodada = rodar(acompanhar([{"status": 200, "corpo": []}], teto_s=0, quadro_s=0))
    assert rodada is not None and eventos == []
    # leu, o quadro saiu, e DEPOIS 401 → `leu` e `quadro_saiu` vêm na exceção (o motor fecha com o que leu)
    with pytest.raises(R.LeituraImpossivel) as parte:
        rodar(acompanhar([{"status": 200, "corpo": []}, {"status": 401}], quadro_s=0, ao_quadro=_nada))
    assert parte.value.leu and parte.value.quadro_saiu and parte.value.sessao_morta


async def _nada():
    return None


class _SessoesComRoteiro(TM.SessoesDuble):
    def __init__(self, mundo, processo, roteiro):
        super().__init__(mundo, processo)
        self.roteiro = roteiro
        self.descartadas = []

    async def obter(self, conta, *, senha, negocios_do_robo):
        s = await super().obter(conta, senha=senha, negocios_do_robo=negocios_do_robo)
        if not isinstance(s, _SessaoQueLe):
            novo = _SessaoQueLe(s.conta_id, s.negocios, self.roteiro)
            self._s[conta["id"]] = novo
            s = novo
        return s

    async def descartar(self, conta_id):
        self.descartadas.append(conta_id)
        if self._s.pop(conta_id, None) is not None:
            self.m.abertas.get(conta_id, set()).discard(self.processo)


class _RoboComLeituraReal(TM.RoboDuble):
    """O robô dublê da suíte, com o `acompanhar` REAL do robô (o elo que o juiz mediu)."""
    LeituraImpossivel = R.LeituraImpossivel

    async def acompanhar(self, sessao, disparo, **kw):
        kw.update(intervalo_s=0, quadro_s=0)
        return await R.acompanhar(sessao, disparo, **kw)


def _motor_com_roteiro(amb, nome, roteiro):
    m = TM.motor(amb, nome)
    m._sessoes = _SessoesComRoteiro(amb.mundo, nome, roteiro)
    m._robo = _RoboComLeituraReal(amb.mundo, m.supa)
    return m


def test_juiz_b1_sessao_401_vira_falhou_e_a_sessao_e_descartada(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    ra = TM.robo(amb, a)
    pid, ids = TM.pedido(amb, a, [a], origem="auxiliar", opcoes=("padrao",))
    m = _motor_com_roteiro(amb, "motor-1", [{"status": 401}])
    rodar(m.uma_volta())
    c = TM.calc(amb, ids[0])
    assert c["status"] == "falhou", f"leitura que nunca leu virou {c['status']!r}"
    assert c["erro"] == MOT.MOTIVO_NAO_LEU
    assert m._sessoes.descartadas == [ra], "a sessão morta tem de ser DESCARTADA"
    assert ra not in m._ociosas and TM.conta(amb, ra)["robo_dono"] is None, "sessão morta não fica ociosa"
    assert TM.linhas(amb, "multicalculo_pedidos", id=pid)[0]["status"] == "fechado"


def test_juiz_b1_controle_leu_e_o_quadro_saiu_fecha_com_o_que_leu(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    _pid, ids = TM.pedido(amb, a, [a], origem="auxiliar", opcoes=("padrao",))
    m = _motor_com_roteiro(amb, "motor-1", [{"status": 200, "corpo": []}, {"status": 401}])
    rodar(m.uma_volta())
    c = TM.calc(amb, ids[0])
    assert c["status"] == "fechado" and c["erro"] == MOT.MOTIVO_LEU_PARTE and c["quadro_pronto_em"]


class _SessaoMortaDuble(TM.DisparoRecusado):
    sessao_morta = True


def test_juiz_b1_a_sessao_morta_do_robo_real_e_uma_recusa_com_a_marca():
    assert issubclass(R.SessaoMorta, R.DisparoRecusado) and R.SessaoMorta("x").sessao_morta is True
    assert R.DisparoRecusado("x").sessao_morta is False


def test_juiz_b1_sessao_morta_no_preparo_devolve_a_fila_sem_falhar(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    ra = TM.robo(amb, a)
    _pid, ids = TM.pedido(amb, a, [a], origem="auxiliar", expira_min=120)
    # a `SessaoMorta` do robô real é uma `DisparoRecusado` com `sessao_morta=True`; aqui, a do robô dublê da suíte
    amb.mundo.falha_disparo["padrao"] = _SessaoMortaDuble("a sessão caiu (seguradoras_http_401)")
    m = TM.motor(amb, "motor-1")
    rodar(m.uma_volta())
    assert amb.mundo.posts == []
    for cid in ids:
        c = TM.calc(amb, cid)
        assert c["status"] == "na_fila" and c["disponivel_em"], "nada saiu: volta à fila com espera"
    assert ra not in m._ociosas and TM.conta(amb, ra)["robo_dono"] is None


# =====================================================================================================================
# juiz B2 — a porta entrega o PDF, do NOSSO bucket, só para quem pode
# =====================================================================================================================
def _porta(amb, storage):
    repo = RepositorioMulticalculo(amb.banco.visao("smith-api"))
    repo.baixar_pdf = lambda caminho: storage.get(caminho)
    return MulticalculoProvider(repo, cifrar=lambda s: s, ambiente={}, agora=amb.relogio.agora)


def test_juiz_b2_o_pdf_que_o_motor_gravou_sai_pela_porta_com_dois_tenants(ambiente):
    amb = ambiente
    canal, a, b = TM.empresa(amb), TM.empresa(amb), TM.empresa(amb)
    TM.robo(amb, a), TM.robo(amb, b)
    pid, ids = TM.pedido(amb, canal, [a, b], opcoes=("padrao",))
    storage = {}

    async def upload(supa, caminho, blob, content_type="application/pdf"):
        storage[caminho] = bytes(blob)
        return caminho

    m = TM.motor(amb, "motor-1")
    m._upload = upload
    rodar(m.uma_volta())
    com_pdf = [o for o in amb.banco.linhas("multicalculo_ofertas") if o["pdf_path"]]
    assert len(com_pdf) == 4 and len(storage) == 4
    porta = _porta(amb, storage)
    de_a = next(o for o in com_pdf if o["company_id"] == a)
    de_b = next(o for o in com_pdf if o["company_id"] == b)
    # o canal (solicitante, adesão ativa) e a corretora de registro baixam; a OUTRA corretora não
    assert rodar(porta.pdf(company_id=canal, oferta_id=de_a["id"])) == storage[de_a["pdf_path"]]
    assert rodar(porta.pdf(company_id=a, oferta_id=de_a["id"]))[:4] == b"%PDF"
    with pytest.raises(NaoEncontrado):
        rodar(porta.pdf(company_id=b, oferta_id=de_a["id"]))
    with pytest.raises(NaoEncontrado):
        rodar(porta.pdf(company_id=a, oferta_id=de_b["id"]))
    # a adesão desativada: o canal deixa de baixar o PDF daquela corretora (a mesma regra do consultar)
    amb.banco.visao("founder").table("multicalculo_adesoes").update({"ativa": False}) \
        .eq("canal_company_id", canal).eq("corretora_company_id", a).execute()
    with pytest.raises(NaoEncontrado):
        rodar(porta.pdf(company_id=canal, oferta_id=de_a["id"]))
    assert rodar(porta.pdf(company_id=canal, oferta_id=de_b["id"]))[:4] == b"%PDF"   # CONTROLE: a outra segue
    # caminho trocado no banco (aponta o arquivo de OUTRA oferta) → nunca lê outro arquivo do bucket
    de_b["pdf_path"] = de_a["pdf_path"]
    assert rodar(porta.pdf(company_id=b, oferta_id=de_b["id"])) is None
    # oferta sem PDF copiado → None, sem erro
    sem = next(o for o in amb.banco.linhas("multicalculo_ofertas") if not o["pdf_path"] and o["company_id"] == a)
    assert rodar(porta.pdf(company_id=a, oferta_id=sem["id"])) is None


# =====================================================================================================================
# red B1 (A1) — a pausa do Founder vence o motor
# =====================================================================================================================
def test_red_b1_a_pausa_do_founder_no_meio_do_login_nao_vira_ocupada(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    ra = TM.robo(amb, a)
    TM.pedido(amb, a, [a], origem="auxiliar", opcoes=("padrao",))

    class SessoesComPausaNoMeio(TM.SessoesDuble):
        async def obter(self, conta, *, senha, negocios_do_robo):
            amb.banco.visao("founder").table("portal_accounts").update({"robo_estado": "pausado"}) \
                .eq("id", ra).execute()
            raise TM.SessaoOcupada()

    m = TM.motor(amb, "motor-1")
    m._sessoes = SessoesComPausaNoMeio(amb.mundo, "motor-1")
    rodar(m.uma_volta())
    assert TM.conta(amb, ra)["robo_estado"] == "pausado", "o motor desfez a pausa do Founder"
    amb.relogio.avancar(31 * 60)
    assert ROB.escolher(amb.banco.visao("motor-2"), a, "auxiliar", dono="motor-2", agora=amb.relogio.agora()) is None
    assert TM.conta(amb, ra)["robo_estado"] == "pausado"


def test_red_b1_controle_e_as_transicoes_do_motor(ambiente, monkeypatch):
    amb = ambiente
    a = TM.empresa(amb)
    ra = TM.robo(amb, a)
    supa = amb.banco.visao("motor-1")
    conta = dict(TM.conta(amb, ra))
    assert ROB.marcar_estado(supa, conta, ROB.OCUPADA, agora=T0) is True          # CONTROLE: ativo → ocupada
    assert TM.conta(amb, ra)["robo_estado"] == "ocupada"
    assert ROB.marcar_estado(supa, conta, ROB.BLOQUEADO, agora=T0) is False       # leu `ativo`, está `ocupada`
    for proibida in (ROB.ATIVO, ROB.TESTE):
        with pytest.raises(ValueError):
            ROB.marcar_estado(supa, {**conta, "robo_estado": ROB.PAUSADO}, proibida)
    # ocupada que o Founder pausou ENTRE a leitura de `escolher` e o CAS dela: não volta a `ativo`, a lease volta
    linha = amb.banco.linhas("portal_accounts")[0]
    velha = dict(linha)                                     # o que `candidatos` leu: `ocupada`, prazo vencido
    linha.update(robo_estado="pausado")
    amb.relogio.avancar(31 * 60)
    monkeypatch.setattr(ROB, "candidatos", lambda _s, _c: [velha])
    assert ROB.escolher(supa, a, "auxiliar", dono="m", agora=amb.relogio.agora()) is None
    assert linha["robo_estado"] == "pausado" and linha["robo_dono"] is None
    # CONTROLE: sem a pausa, a mesma `ocupada` vencida volta a `ativo` e é escolhida
    linha.update(robo_estado="ocupada")
    assert ROB.escolher(supa, a, "auxiliar", dono="m", agora=amb.relogio.agora())["robo_estado"] == "ativo"
    assert linha["robo_estado"] == "ativo"


# =====================================================================================================================
# red B2 (A2) — a adesão desativada impede o disparo no login da corretora
# =====================================================================================================================
def test_red_b2_adesao_desativada_com_o_pedido_na_fila_cancela_sem_post(ambiente):
    amb = ambiente
    canal, a = TM.empresa(amb), TM.empresa(amb)
    TM.robo(amb, a)
    _pid, ids = TM.pedido(amb, canal, [a], origem="canal")
    amb.banco.visao("founder").table("multicalculo_adesoes").update(
        {"ativa": False, "desativada_em": amb.relogio.iso()}).eq("canal_company_id", canal).execute()
    rodar(TM.motor(amb, "motor-1").uma_volta())
    assert amb.mundo.posts == [], "calcularV2 no login da corretora que saiu do canal"
    for cid in ids:
        c = TM.calc(amb, cid)
        assert c["status"] == "cancelado" and c["erro"] == MOT.MOTIVO_SAIU_DO_CANAL


def test_red_b2_controle_e_a_reconferencia_antes_de_cada_post(ambiente):
    amb = ambiente
    canal, a = TM.empresa(amb), TM.empresa(amb)
    TM.robo(amb, a)
    _pid, ids = TM.pedido(amb, canal, [a], origem="canal")
    m = TM.motor(amb, "motor-1")

    class RoboQueVeASaida(TM.RoboDuble):
        async def disparar(self, sessao, pedido, coberturas, *, negocio_ref=None):
            d = await super().disparar(sessao, pedido, coberturas, negocio_ref=negocio_ref)
            # a corretora sai do canal ENTRE a padrão e a econômica
            amb.banco.visao("founder").table("multicalculo_adesoes").update({"ativa": False}) \
                .eq("canal_company_id", canal).execute()
            return d

    m._robo = RoboQueVeASaida(amb.mundo, m.supa)
    rodar(m.uma_volta())
    assert [p[3] for p in amb.mundo.posts] == ["padrao"], "a econômica saiu depois de a corretora sair do canal"
    por_opcao = {TM.calc(amb, c)["opcao"]: TM.calc(amb, c) for c in ids}
    assert por_opcao["padrao"]["status"] == "fechado"                   # CONTROLE: o que saiu antes segue
    assert por_opcao["economica"]["status"] == "cancelado"
    # uma empresa `client` se passando por canal (com "adesão" forjada) também não dispara
    amb2 = SimpleNamespace(banco=TM.BancoU1(amb.relogio), relogio=amb.relogio, mundo=TM.MundoAgger())
    x, y = TM.empresa(amb2), TM.empresa(amb2)
    TM.robo(amb2, y)
    TM.pedido(amb2, x, [y], origem="canal")
    amb2.banco.linhas("companies")[0]["company_kind"] = "client"
    rodar(TM.motor(amb2, "m").uma_volta())
    assert amb2.mundo.posts == []


# =====================================================================================================================
# red B4 (A8) — a econômica adiada confere a D-MC-47 antes de entrar no negócio
# =====================================================================================================================
def _economica_adiada(amb):
    a = TM.empresa(amb)
    TM.robo(amb, a)
    pid, ids = TM.pedido(amb, a, [a], origem="auxiliar", expira_min=24 * 60)
    estado = {"freio": False, "n": 0}
    m = TM.motor(amb, "motor-1")

    class RoboComFreio(TM.RoboDuble):
        async def disparar(self, sessao, pedido, coberturas, *, negocio_ref=None):
            d = await super().disparar(sessao, pedido, coberturas, negocio_ref=negocio_ref)
            estado["n"] += 1
            if estado["n"] == 1:
                estado["freio"] = True       # o GLOBAL_KILL_SWITCH puxado logo depois da padrão
            return d

    m._robo = RoboComFreio(amb.mundo, m.supa)
    m._freio = lambda: estado["freio"]
    rodar(m.uma_volta())
    estado["freio"] = False
    amb.relogio.avancar(3 * 3600)
    return m, ids


def test_red_b4_economica_adiada_com_pessoa_mexendo_nao_sai(ambiente):
    amb = ambiente
    m, ids = _economica_adiada(amb)
    amb.mundo.mexeu = True
    rodar(m.uma_volta())
    assert [(p[1], p[2], p[3]) for p in amb.mundo.posts] == [("NEG-1", 1, "padrao")]
    assert [x[0] for x in amb.mundo.consultas_mexeu] == ["NEG-1"]
    econ = next(TM.calc(amb, i) for i in ids if TM.calc(amb, i)["opcao"] == "economica")
    assert econ["status"] == "falhou" and econ["erro"] == MOT.MOTIVO_PESSOA_MEXEU


def test_red_b4_controle_ninguem_mexeu_a_economica_entra_no_mesmo_negocio(ambiente):
    amb = ambiente
    m, ids = _economica_adiada(amb)
    rodar(m.uma_volta())
    assert [(p[1], p[2], p[3]) for p in amb.mundo.posts] == [("NEG-1", 1, "padrao"), ("NEG-1", 2, "economica")]
    assert len(amb.mundo.consultas_mexeu) == 1


# =====================================================================================================================
# item 7 (red A5, juiz P1) — a guarda: leitura só no Agger, ids completos e conferidos
# =====================================================================================================================
API = "https://api-prod.aggilizador.com.br/api/calculo/calcularV2"


def _corpo(neg=None, ref=None, neg_id=None, cot_id=None):
    cot = {k: v for k, v in (("idIntegracao", ref), ("negocioId", neg_id), ("id", cot_id)) if v is not None}
    return json.dumps({"negocio": {"id": neg} if neg else None, "cotacao": cot})


def test_item7_a_guarda_corpo_misto_e_leitura_fora_do_agger():
    est = G.EstadoDaGuarda(host_api="api-prod.aggilizador.com.br")
    est.registrar_negocio("ref-do-robo")
    est.registrar_ids("ref-do-robo", negocio_id="neg-robo", versao_id="ver-robo")
    d = lambda c: G.decidir("POST", API, c, est)   # noqa: E731
    # CONTROLE: os 4 ids do negócio do robô, coerentes → passa
    assert d(_corpo("neg-robo", "ref-do-robo", "neg-robo", "ver-robo")) == (True, "calculo_do_robo")
    assert d(_corpo()) == (True, "calculo_novo")
    # os ataques do red team (A5): cada um barrado
    assert d(_corpo("neg-PESSOA", "ref-do-robo"))[0] is False                       # sem negocioId
    assert d(_corpo("neg-PESSOA", "ref-do-robo", "neg-PESSOA", "ver-robo"))[0] is False   # negócio alheio coerente
    assert d(_corpo("neg-robo", "ref-do-robo", "neg-robo", "versao-de-PESSOA"))[0] is False
    assert d(_corpo("neg-robo", "ref-do-robo", "neg-robo"))[0] is False             # sem cotacao.id
    assert d(_corpo("neg-robo", "ref-de-PESSOA", "neg-robo", "ver-robo")) == (False, "negocio_que_nao_e_do_robo")
    # leitura: só no domínio do Agger, nunca com cara de ação destrutiva
    assert G.decidir("GET", "https://coletor.terceiro.example/px?d=1", None, est) == (False, "leitura_fora_do_agger")
    assert G.decidir("GET", "https://api-prod.aggilizador.com.br/api/negocio/excluir/123", None, est)[0] is False
    assert G.decidir("GET", "https://quotation-files.aggilizador.com.br/pdf/x.pdf", None, est) == (True, "leitura")
    assert G.decidir("GET", "https://aggilizador.com.br/cotacoes", None, est) == (True, "leitura")
    assert G.decidir("GET", "https://aggilizador.com.br.evil.example/x", None, est)[0] is False


# =====================================================================================================================
# item 8 (juiz P4) — o motivo do `falhou` chega saneado à corretora
# =====================================================================================================================
def test_item8_disparo_recusado_tem_motivo_curto_saneado_e_a_porta_o_mostra(ambiente):
    exc = R.DisparoRecusado("HTTP 422: veja https://seg.example/x?key=abc e o CPF 529.982.247-25")
    assert exc.motivo and "http" not in exc.motivo and "529" not in exc.motivo and "key=" not in exc.motivo
    assert R._recusa_do_preparo("veiculo_sem_fipe_ou_ano").motivo == R.MOTIVOS_LEGIVEIS["veiculo_sem_fipe_ou_ano"]
    assert isinstance(R._recusa_do_preparo("seguradoras_http_401"), R.SessaoMorta)
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    pid, ids = TM.pedido(amb, a, [a], origem="auxiliar", opcoes=("padrao",))
    amb.mundo.falha_disparo["padrao"] = TM.DisparoRecusado(R.DisparoRecusado("HTTP 422: Placa inválida para o modelo")
                                                           .motivo)
    rodar(TM.motor(amb, "motor-1").uma_volta())
    porta = _porta(amb, {})
    estado = rodar(porta.consultar(company_id=a, pedido_id=pid)).estados[0]
    assert estado["status"] == "falhou"
    assert estado["erro"] == "o portal recusou o cálculo: HTTP 422: Placa inválida para o modelo"


# =====================================================================================================================
# item 10 (red P6, P7) — login sem desfecho em conta de PESSOA; retomada de pedido de teste fora do canário
# =====================================================================================================================
class SessaoIndefinida(Exception):
    pass


def test_item10_login_sem_desfecho_na_conta_de_teste_pausa_e_para(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    janela = {"dias": "seg-dom", "inicio": "00:00", "fim": "23:59"}
    r = TM.robo(amb, a, estado="teste", janela=janela)
    _p, ids = TM.pedido(amb, a, [a], origem="teste", expira_min=120)
    amb.mundo.login[r] = SessaoIndefinida
    m = TM.motor(amb, "m1", canario=True)
    m._sessao_mod = SimpleNamespace(SessaoOcupada=TM.SessaoOcupada, CredencialRecusada=TM.CredencialRecusada,
                                    SessaoIndefinida=SessaoIndefinida)
    rodar(m.uma_volta())
    rodar(m.uma_volta())
    assert TM.conta(amb, r)["robo_estado"] == "pausado"
    assert {TM.calc(amb, c)["status"] for c in ids} == {"falhou"} and len(amb.mundo.obter) == 1
    # CONTROLE: a mesma falha numa conta de ROBÔ (`ativo`) volta à fila com espera e a conta segue ativa
    amb2 = SimpleNamespace(banco=TM.BancoU1(amb.relogio), relogio=amb.relogio, mundo=TM.MundoAgger())
    b = TM.empresa(amb2)
    r2 = TM.robo(amb2, b)
    _p, ids2 = TM.pedido(amb2, b, [b], origem="auxiliar", expira_min=120)
    amb2.mundo.login[r2] = SessaoIndefinida
    m2 = TM.motor(amb2, "m2")
    m2._sessao_mod = m._sessao_mod
    rodar(m2.uma_volta())
    assert TM.conta(amb2, r2)["robo_estado"] == "ativo"
    assert {TM.calc(amb2, c)["status"] for c in ids2} == {"na_fila"}


def test_item10_retomada_de_pedido_de_teste_so_no_canario(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a, estado="ativo")
    _p, ids = TM.pedido(amb, a, [a], origem="teste", opcoes=("padrao",))
    amb.banco.linhas("multicalculo_calculos")[-1].update(
        status="calculando", negocio_ref="NEG-T", versao=1, dono="morto", batida_em=T0.isoformat())
    amb.mundo.versoes["NEG-T"] = 1
    amb.mundo.servir[("NEG-T", 1)] = 0
    amb.relogio.avancar(MOT.LEASE_VENCE_S + 5)
    assert rodar(TM.motor(amb, "servico", canario=False).uma_volta()) == 0, "o SERVIÇO retomou um pedido de teste"
    assert TM.calc(amb, ids[0])["status"] == "calculando" and amb.mundo.obter == []
    # CONTROLE: o processo do canário retoma (só leitura) e fecha
    assert rodar(TM.motor(amb, "canario", canario=True).uma_volta()) == 1
    assert TM.calc(amb, ids[0])["status"] == "fechado" and amb.mundo.posts == []


# =====================================================================================================================
# item 11 (red A6) — o clique duplo no recálculo vira UM calcularV2
# =====================================================================================================================
def test_item11_recalculo_duplo_pela_porta_devolve_o_mesmo(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    r = TM.robo(amb, a)
    pid, origem, _aj = TM._pedido_com_padrao_fechada(amb, a, r)
    amb.banco.linhas("multicalculo_calculos")[:] = [c for c in amb.banco.linhas("multicalculo_calculos")
                                                    if c["opcao"] != "ajuste"]
    porta = _porta(amb, {})
    um = rodar(porta.recalcular(company_id=a, calculo_id=origem, ajuste={"tipo": "comissao", "valor": 12}))
    dois = rodar(porta.recalcular(company_id=a, calculo_id=origem, ajuste={"tipo": "comissao", "valor": 12}))
    assert dois["id"] == um["id"] and dois.get("repetido") is True
    outro = rodar(porta.recalcular(company_id=a, calculo_id=origem, ajuste={"tipo": "comissao", "valor": 15}))
    assert outro["id"] != um["id"]                                       # CONTROLE: ajuste DIFERENTE é novo
    ajustes = [c for c in amb.banco.linhas("multicalculo_calculos") if c["opcao"] == "ajuste"]
    assert len(ajustes) == 2


def test_item11_recalculo_duplo_por_fora_da_porta_o_motor_manda_um(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    pid, ids = TM.pedido(amb, a, [a], origem="auxiliar", opcoes=("padrao",))
    m = TM.motor(amb, "motor-1")
    rodar(m.uma_volta())
    origem = TM.calc(amb, ids[0])
    for i in range(2):   # o que a porta gravaria, duas vezes, sem a conferência dela (a corrida do clique duplo)
        amb.relogio.avancar(1)
        amb.banco.visao("smith-api").table("multicalculo_calculos").insert({
            "pedido_id": pid, "solicitante_company_id": a, "company_id": a, "opcao": "ajuste",
            "origem_calculo_id": origem["id"], "coberturas": {"preset": "ajuste"},
            "ajuste": {"tipo": "comissao", "valor": 12, "seguradora": None}, "status": "na_fila",
            "prioridade": 5, "expira_em": (amb.relogio.agora() + timedelta(hours=1)).isoformat(),
            "disponivel_em": amb.relogio.iso()}).execute()
    amb.banco.visao("smith-api").table("multicalculo_pedidos").update({"status": "aberto"}).eq("id", pid).execute()
    rodar(m.uma_volta())
    assert len([p for p in amb.mundo.posts if p[3] == "ajuste"]) == 1
    ajustes = sorted((c for c in amb.banco.linhas("multicalculo_calculos") if c["opcao"] == "ajuste"),
                     key=lambda c: c["criado_em"])
    assert [c["status"] for c in ajustes] == ["fechado", "cancelado"]
    assert ajustes[1]["erro"] == MOT.MOTIVO_AJUSTE_REPETIDO


# =====================================================================================================================
# item 12 (juiz P10) — o motor do canário serve SÓ os pedidos dele
# =====================================================================================================================
def test_item12_somente_pedidos(ambiente):
    amb = ambiente
    a = TM.empresa(amb)
    TM.robo(amb, a)
    p1, ids1 = TM.pedido(amb, a, [a], origem="auxiliar", opcoes=("padrao",))
    p2, ids2 = TM.pedido(amb, a, [a], origem="auxiliar", opcoes=("padrao",))
    meus = set()
    m = TM.motor(amb, "canario")
    m.somente_pedidos = meus          # o que `MOT.Motor(..., somente_pedidos=...)` guarda (o canário passa no init)
    assert rodar(m.uma_volta()) == 0, "conjunto vazio = nenhum pedido (nunca a fila inteira)"
    meus.add(p1)
    assert rodar(m.uma_volta()) == 1
    assert TM.calc(amb, ids1[0])["status"] == "fechado" and TM.calc(amb, ids2[0])["status"] == "na_fila"
    assert rodar(m.uma_volta()) == 0, "o pedido de outro entrou no motor do canário"
    rodar(m.desligar())                                                   # devolve a lease da sessão ociosa
    assert rodar(TM.motor(amb, "servico").uma_volta()) == 1               # CONTROLE: o serviço serve a fila toda
    assert TM.calc(amb, ids2[0])["status"] == "fechado"


def test_item12_o_canario_passa_o_filtro_ao_motor():
    src = (BACKEND / "scripts" / "multicalculo_canario.py").read_text(encoding="utf-8")
    assert "somente_pedidos=meus_pedidos" in src and "meus_pedidos.add(aberto.pedido_id)" in src
    assert MOT.Motor(object(), dono="x", somente_pedidos={"p"}).somente_pedidos == {"p"}


# =====================================================================================================================
# item 13 (juiz P11) — o grupo partido fica na MESMA conta
# =====================================================================================================================
def _grupo_partido(amb):
    a = TM.empresa(amb)
    r1, r2 = TM.robo(amb, a, rotulo="robo-1"), TM.robo(amb, a, rotulo="robo-2")
    _pid, ids = TM.pedido(amb, a, [a], origem="auxiliar", expira_min=120)
    pad = next(c for c in amb.banco.linhas("multicalculo_calculos") if c["id"] in ids and c["opcao"] == "padrao")
    pad.update(status="fechado", account_id=r1, negocio_ref="NEG-1", versao=1, fechado_em=T0.isoformat())
    amb.mundo.versoes["NEG-1"] = 1
    econ = next(c for c in ids if c != pad["id"])
    return a, r1, r2, econ


def test_item13_economica_espera_a_conta_do_negocio(ambiente):
    amb = ambiente
    _a, r1, r2, econ = _grupo_partido(amb)
    # a conta do negócio está com OUTRO motor: a econômica espera (nunca vai para a r2)
    next(c for c in amb.banco.linhas("portal_accounts") if c["id"] == r1).update(
        robo_dono="outro-motor", robo_batida_em=T0.isoformat())
    assert rodar(TM.motor(amb, "motor-1").uma_volta()) == 0
    assert TM.calc(amb, econ)["status"] == "na_fila" and amb.mundo.posts == []
    # CONTROLE: a conta do negócio livre → a econômica sai NELA, como versão do mesmo negócio
    next(c for c in amb.banco.linhas("portal_accounts") if c["id"] == r1).update(robo_dono=None, robo_batida_em=None)
    assert rodar(TM.motor(amb, "motor-2").uma_volta()) == 1
    assert amb.mundo.posts == [(r1, "NEG-1", 2, "economica")]


def test_item13_irmao_saindo_agora_o_grupo_espera(ambiente):
    amb = ambiente
    _a, r1, _r2, econ = _grupo_partido(amb)
    pad = next(c for c in amb.banco.linhas("multicalculo_calculos") if c["opcao"] == "padrao")
    pad.update(status="disparando", negocio_ref=None, versao=None, dono="outro-motor", batida_em=T0.isoformat())
    assert rodar(TM.motor(amb, "motor-1").uma_volta()) == 0
    assert TM.calc(amb, econ)["status"] == "na_fila" and amb.mundo.posts == []


# =====================================================================================================================
# item 9 (juiz P3, red P8) — o comando: --estado obrigatório · religar · trocar-senha
# =====================================================================================================================
def test_item9_o_comando_estado_obrigatorio_religar_e_trocar_senha(ambiente):
    from portal_worker import vault
    from portal_worker.multicalculo import comando_robo as CMD

    amb = ambiente
    a = TM.empresa(amb)
    supa = amb.banco.visao("founder")
    saida = []
    senha = "Senha-Ficticia-Do-Conserto-1"
    base = ["cadastrar", "--corretora", a, "--rotulo", "robo-x", "--usuario", "robo@exemplo.invalid"]
    assert CMD.main(base, supa=supa, ler_senha=lambda: senha, escrever=saida.append) == 2, "--estado sem padrão"
    assert not [c for c in amb.banco.linhas("portal_accounts") if c.get("account_label") == "robo-x"]
    assert CMD.main(base + ["--estado", "ativo"], supa=supa, ler_senha=lambda: senha, escrever=saida.append) == 0
    conta = next(c for c in amb.banco.linhas("portal_accounts") if c.get("account_label") == "robo-x")
    # rótulo repetido: a recusa aponta o caminho certo (trocar-senha / religar), com o id
    saida.clear()
    assert CMD.main(base + ["--estado", "ativo"], supa=supa, ler_senha=lambda: senha, escrever=saida.append) == 2
    assert "trocar-senha --conta " + conta["id"] in saida[-1] and "religar" in saida[-1]
    # religar só desfaz pausado/bloqueado/ocupada, e exige --estado
    assert CMD.main(["religar", "--conta", conta["id"], "--estado", "ativo"], supa=supa, escrever=saida.append) == 2
    conta["robo_estado"] = "bloqueado"
    assert CMD.main(["religar", "--conta", conta["id"]], supa=supa, escrever=saida.append) == 2
    assert CMD.main(["religar", "--conta", conta["id"], "--estado", "teste"], supa=supa, escrever=saida.append) == 2
    assert conta["robo_estado"] == "bloqueado", "teste sem janela não religa"
    assert CMD.main(["religar", "--conta", conta["id"], "--estado", "ativo"], supa=supa, escrever=saida.append) == 0
    assert conta["robo_estado"] == "ativo"
    # trocar-senha: cifra a nova, pausa; religar volta
    nova = "Senha-Nova-Ficticia-2"
    assert CMD.main(["trocar-senha", "--conta", conta["id"]], supa=supa, ler_senha=lambda: nova,
                    escrever=saida.append) == 0
    assert conta["robo_estado"] == "pausado" and vault.decrypt(conta["secret_encrypted"]) == nova
    assert CMD.main(["religar", "--conta", conta["id"], "--estado", "ativo"], supa=supa, escrever=saida.append) == 0
    # sem senha → religar recusa
    assert CMD.main(["apagar-senha", "--conta", conta["id"]], supa=supa, escrever=saida.append) == 0
    assert CMD.main(["religar", "--conta", conta["id"], "--estado", "ativo"], supa=supa, escrever=saida.append) == 2
    assert conta["robo_estado"] == "pausado"
    tudo = "\n".join(saida)
    assert senha not in tudo and nova not in tudo and "robo@exemplo.invalid" not in tudo


# =====================================================================================================================
# red B3 (A3) — a credencial da seguradora ECOADA num alerta não chega ao banco (o fio inteiro, Chromium real)
# =====================================================================================================================
pw_api = pytest.importorskip("playwright.async_api")

import test_spec129b_o_fio as TF  # noqa: E402
from test_spec129b_o_fio import mundo  # noqa: E402,F401  (fixture)
from dubles.agger_duble import AggerDuble, segredos_do_item  # noqa: E402
from app.services.multicalculo import PedidoDeCalculo  # noqa: E402


class AggerQueEcoa(AggerDuble):
    """A seguradora devolve, num ALERTA de um item com oferta, a credencial que recebeu (forma livre, sem `key=`)."""

    def _com_segredos(self, corpo):
        saida = super()._com_segredos(corpo)
        for it in saida:
            if not isinstance(it, dict):
                continue
            s = segredos_do_item(f"item{it.get('seguradora')}")
            for r in it.get("resultados") or []:
                if isinstance(r, dict) and (r.get("premio") or 0) > 0:
                    r["alertas"] = list(r.get("alertas") or []) + [
                        f"Webservice autenticado com usuario {s['loginWs']} senha {s['senhaWs']}"]
                    break
        return saida


def test_red_b3_credencial_ecoada_em_alerta_nao_vai_ao_banco(mundo):
    m = mundo

    async def run():
        d = await AggerQueEcoa().iniciar()
        try:
            async with pw_api.async_playwright() as pw:
                nav = await pw.chromium.launch(headless=True)
                pedido = PedidoDeCalculo.de_dict(TF.dados_do_pedido())
                await m.porta.calcular(company_id=m.a, pedido=pedido, opcoes=("padrao",), origem="auxiliar")
                mot = TF.motor(m, "motor-1", nav, d)
                await TF.ate_esvaziar(mot, m)
                await mot.desligar()
                await nav.close()
        finally:
            await d.parar()
    asyncio.run(run())
    ofertas = m.banco.linhas("multicalculo_ofertas")
    alertas = [a for o in ofertas for a in (o.get("alertas") or [])]
    assert ofertas, "o fio não gravou oferta nenhuma"
    assert [a for a in alertas if "SEGREDO-" in a] == [], "credencial ecoada chegou ao banco"
    # CONTROLE: o alerta EXISTIA e foi trocado pela marca (não sumiu por acaso)
    assert alertas.count("<redacted:credencial>") >= 1
    tudo = json.dumps({t: m.banco.linhas(t) for t in list(m.banco.tabelas)}, default=str)
    assert "SEGREDO-" not in tudo

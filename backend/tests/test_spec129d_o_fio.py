# -*- coding: utf-8 -*-
"""SPEC-129-D · V3 · COSTURA — O TESTE DO FIO da Vida Individual (ramo 91), da renovação ao item.

V1 (o portal, `eddaaea`) e V2 (o app, `193df09`) foram escritas EM PARALELO, cada uma contra dublês da outra. Aqui a saída
REAL de uma é a entrada da outra (protocolo §5.2):

    InfoCap /renovacoes (VIND) → madrugada.preparar_dia REAL (chave MULTICALCULO_VIDA_LIGADO) → a ficha única (borda:
      o PDF lido, com o capital da Morte e UMA linha que não casa) + o perfil REAL (`perfil_da_renovacao.montar` sobre a
      InfoCap na REDE dublê) + o que o comercial RESPONDEU (fumante/renda/esporte — nenhuma rota os tem) →
      `pedido.de_apolice` REAL → madrugada.calcular_dia REAL → `porta.calcular` REAL (cifra real) → banco dublê →
      `Motor.uma_volta()` REAL → `agger_robo` REAL (o `JS_PREPARAR`/`JS_PROFISSOES`/`JS_LER_CALCULOS` e o `montador.js`
      rodam em node — a MESMA fonte que a página carrega) → o Agger dublado SÓ no `fetch`, respondendo as GRAVAÇÕES
      (a busca de profissão e o resultado do `calcularV2`, `fixtures/agger_ramos/vida_*.json`) → o corpo enviado ==
      a FORMA gravada → `leitor_agger` REAL → eventos/ofertas no banco → `madrugada.acompanhar` REAL → o ITEM.
    bordas: o banco (PostgREST), a InfoCap (rede), o Agger (`fetch`), o PDF (a ficha), a resposta do comercial.

Casos: (a) o caminho feliz até o corpo, e o aviso da cobertura não mapeada chega ao item · (b) profissão sem casamento
em TODAS → `pendente(falta_dado)` com a pergunta da profissão · (c) comissão de vida 0 na conta e nenhuma no pedido →
pendente com a frase da configuração · (d) a recusa gravada ("instabilidade") → recusa POR seguradora, nenhuma oferta ·
(e) chave AUSENTE → `ramo_nao_cotado` como antes (o CONTROLE) · (f) o texto que o MOTOR grava de cada recusa de vida
(esporte "sim", busca que falhou) → o estado do item.
Mutação da régua: tire o mapeamento de `profissao_sem_casamento` da madrugada → (b) VERMELHO.

⛔ Tudo sintético (o CPF de exemplo da 129-B, "PESSOA SINTETICA"); nenhum login, nenhum cálculo real; nenhum nome de
corretora (CLAUDE.md §13.9); fumante/renda nunca em log (LGPD art. 11).
Rodar: cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_spec129d_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec129d_app_vida as V2  # noqa: E402  (a ficha de vida e o CPF de exemplo da V2)
import test_spec129d_portal_vida as V1  # noqa: E402  (a sessão em node, a config da conta e as gravações da V1)
import test_spec131a_o_fio as FIO  # noqa: E402
import test_spec131a_o_perfil as PERF  # noqa: E402
from test_spec131a_o_fio import mundo_real  # noqa: E402,F401  (fixture)
import app.services.multicalculo.porta as PORTA  # noqa: E402
from app.services.multicalculo import comparacao as C  # noqa: E402
from app.services.multicalculo import madrugada as M  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from app.services.multicalculo import perfil_da_renovacao as PR  # noqa: E402
from app.services.multicalculo import renovacao as RN  # noqa: E402
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402
from dubles.banco_multicalculo import COLUNAS_ROBO, BancoU1  # noqa: E402
from portal_worker.multicalculo import agger_robo as R  # noqa: E402
from portal_worker.multicalculo import contrato as K  # noqa: E402
from portal_worker.multicalculo import motor as MOT  # noqa: E402

CHAVE = "MULTICALCULO_VIDA_LIGADO"
SENHA = "senha-ficticia-do-robo-129d"
CPF = V2.CPF
PROFISSAO = "Analista de sistemas"          # 📊 o termo da busca gravada (BLOCO 0 M6, 5.3)
TOKEN = "token-vida"
NOSNUM = 910104
#: o PDF da apólice (a ficha única): a Morte = o capital; Morte acidental e IPA = a Morte (📊 a FORMA do corpo gravado:
#: a tela replicou os 100 mil nas duas) e UMA linha que NÃO casa com campo do Agger ("Assistência Funeral" sem dizer se
#: é individual ou familiar — escolher seria decidir pelo cliente) → o aviso `coberturas_de_vida_nao_mapeadas`
LINHAS_DO_PDF = (("Morte Natural", 100000, None), ("Morte Acidental", 100000, None),
                 ("Invalidez por Acidente", 100000, None), ("Assistência Funeral", 5000, None))
#: o que o comercial RESPONDEU às três perguntas (📊 BLOCO 0 M2: nenhuma rota da InfoCap tem fumante/renda/esporte)
RESPOSTAS = {"fumante": False, "renda_mensal": 8000, "esporte_radical": False}
#: o que o MOTOR põe na frente de toda recusa do robô (`motor._motivo_recusado`)
COT_GRAVADA = V1.COT_GRAVADA
ITEM_GRAVADO = V1.ITEM_GRAVADO


# =====================================================================================================================
# O banco: as travas do multicálculo (BancoU1: o `unique(calculo_id, chave)` dos eventos, as FKs) + as da madrugada
# =====================================================================================================================
class BancoDaVida(FIO.BancoDaMadrugada, BancoU1):
    """As travas das DUAS migrations. ⚠️ O CHECK de opção do BancoU1 é anterior à 20261013_01, que acrescentou
    `anterior`/`franquia_reduzida` (a da madrugada confere a lista NOVA): o BancoU1 confere o resto da linha."""

    def _travas(self, tabela, nova, velha):
        if tabela == "multicalculo_calculos":
            # a lista de HOJE (20261013_01) é conferida aqui; o resto da linha, pelas travas das duas
            self._check("ck_mc_calculos_opcao", nova.get("opcao") in FIO.OPCOES_DO_CALCULO)
            nova = {**nova, "opcao": "padrao"}
        super()._travas(tabela, nova, velha)


# =====================================================================================================================
# O Agger: a sessão do robô com a página trocada por node (a fonte JS REAL), o `fetch` servindo as gravações
# =====================================================================================================================
class SessaoDoFio(V1.SessaoNode):
    """`V1.SessaoNode` + o que o MOTOR pede da sessão. O resultado servido é o GRAVADO, só das seguradoras que o corpo
    LEVOU (como o Agger responde)."""

    def __init__(self, cfg, blocos, conta_id, negocios):
        super().__init__(V1.rotas(cfg, blocos))
        self.conta_id = conta_id
        self.negocios = set(negocios)
        self.corpo_enviado = None
        self.leituras = 0

    def registrar_negocio(self, ref):
        self.negocios.add(ref)

    async def avaliar(self, fonte, args):
        if fonte == R.JS_LER_CALCULOS:
            levadas = {it["seguradora"] for it in ((self.corpo_enviado or {}).get("cotacao") or {}).get("calculos", [])}
            itens = [i for i in V1.RESULTADO["calculos"] if i["seguradora"] in levadas]
            self.rotas = [r for r in self.rotas if r[0] != "/calculo/cotacao/calculos/"] + \
                [["/calculo/cotacao/calculos/", 200, itens]]
            self.leituras += 1
        r = await super().avaliar(fonte, args)
        if fonte == R.JS_ENVIAR and self.enviado is not None:
            self.corpo_enviado = self.enviado
        return r


class SessoesDoFio:
    def __init__(self, cfg, blocos):
        self.cfg, self.blocos = cfg, blocos
        self.abertas, self.todas, self.logouts = {}, [], 0

    async def obter(self, conta, *, senha, negocios_do_robo, **_extra):
        assert senha == SENHA and "secret_encrypted" not in conta
        s = self.abertas.get(conta["id"])
        if s is None:
            s = self.abertas[conta["id"]] = SessaoDoFio(self.cfg, self.blocos, conta["id"], negocios_do_robo)
            self.todas.append(s)
        return s

    async def fechar(self, conta_id):
        if self.abertas.pop(conta_id, None) is not None:
            self.logouts += 1

    async def descartar(self, conta_id):
        self.abertas.pop(conta_id, None)

    async def fechar_todas(self):
        for cid in list(self.abertas):
            await self.fechar(cid)


ROBO_RAPIDO = SimpleNamespace(**{k: getattr(R, k) for k in dir(R) if not k.startswith("__")})
ROBO_RAPIDO.acompanhar = functools.partial(R.acompanhar, intervalo_s=0.05)


# =====================================================================================================================
# O mundo: a madrugada REAL (131-A) + a porta do produto com a cifra real + o perfil real + a conta-robô
# =====================================================================================================================
@pytest.fixture
def fio(monkeypatch):
    from cryptography.fernet import Fernet

    from portal_worker import leases

    V1._sem_node()
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    for nome in ("MULTICALCULO_TETO_CORRETORA_HORA", "MULTICALCULO_TETO_GERAL_HORA", "AUTOBROKERS_CANARIO"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setattr(leases, "redis_disponivel", lambda *a, **k: False)
    monkeypatch.setattr(FIO, "BancoDaMadrugada", BancoDaVida)
    gen = FIO._mundo(monkeypatch, real=True)
    m = next(gen)
    import dubles_do_work_os as D

    monkeypatch.setitem(D.ESQUEMA, "portal_accounts", {**D.ESQUEMA["portal_accounts"], **COLUNAS_ROBO})
    banco, relogio = m.banco, m.relogio

    class _PortaComCifra(FIO.PORTA_DO_PRODUTO):
        def __init__(self, *_a, **_k):
            super().__init__(RepositorioMulticalculo(banco.visao("smith-api")),
                             ambiente={"MULTICALCULO_HMAC_KEY": FIO.CHAVE_HMAC}, agora=relogio.agora)

    monkeypatch.setattr(PORTA, "MulticalculoProvider", _PortaComCifra)
    yield m
    try:
        next(gen)
    except StopIteration:
        pass


def montar(m, monkeypatch, *, profissao=PROFISSAO, comissao_da_corretora=10, linhas=LINHAS_DO_PDF,
           respostas=RESPOSTAS):
    """Uma corretora com o aplicativo ligado, UMA renovação de vida (VIND), o Agger dela (a conta-robô) e a InfoCap do
    perfil. Devolve a corretora."""
    from portal_worker import vault

    original = FIO.ficha_sintetica
    monkeypatch.setattr(FIO, "ficha_sintetica",
                        lambda sigla: V2.ficha_vida(linhas, sigla) if sigla == "VIND" else original(sigla))
    linha = FIO.linha_renov(NOSNUM, "VIND", FIO.DIA + FIO.timedelta(days=10))
    linha["cic"] = CPF                       # o documento da LISTA é o do cadastro (a conferência de identidade)
    c = FIO.montar_corretora(m, TOKEN, renovacoes=[linha])
    rid = str(uuid.uuid4())
    m.banco.semear("portal_accounts", {
        "id": rid, "company_id": c.id, "portal_key": "agger", "account_label": "agger-da-corretora",
        "username": "robo-vida@exemplo.invalid", "secret_encrypted": vault.encrypt(SENHA), "robo_estado": "ativo",
        "robo_janela": None, "uso": "global", "dono_user_id": None, "robo_batida_em": None})
    cfg = {"vida_por_ramo": {"91": {"comissao_pct": comissao_da_corretora}}} if comissao_da_corretora else {}
    m.banco.semear("multicalculo_config", {"company_id": c.id, "config": cfg})
    # o perfil REAL: `perfil_da_renovacao.montar` sobre a InfoCap na rede (o cadastro do segurado)
    rede = PERF.RedeDoPerfil(monkeypatch, anterior=m.rede._urlopen)
    cli = {**PERF.cliente(sexo="M", datanas="10/05/1985", cep=V1.CEP), "profissao": profissao}
    rede.semear(TOKEN, NOSNUM, cli=cli, itens=[])

    async def perfil_respondido(db, cid, item, fonte, **contexto):
        p = await PERF.BORDA_REAL(db, cid, item, fonte, **contexto)
        if p is None or respostas is None:
            return p
        # o que o comercial RESPONDEU (nunca deduzido; o produto ainda não tem o caminho da resposta — pendência)
        return PR.PerfilMontado({**dict(p), "vida": dict(respostas)}, getattr(p, "nao_conferidos", {}))

    monkeypatch.setattr(M, "perfil_do_segurado", perfil_respondido)
    c.conta = rid
    return c


def item_vida(m, c) -> dict:
    (item,) = [x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "VIND"]
    return item


def eventos_do_item(m, c, item) -> list:
    return [e for e in m.banco.linhas("renovacao_eventos") if e["renovacao_id"] == item["id"]]


def noite(m, c, *, cfg_da_conta=None, blocos=None):
    """00:30 preparar → 01:00 calcular → o MOTOR (uma volta, o robô REAL) → a releitura da madrugada. Devolve as sessões."""
    asyncio.run(M.preparar_dia(m.db, c.id, FIO.DIA))
    asyncio.run(M.calcular_dia(m.db, c.id, FIO.DIA))
    sessoes = SessoesDoFio(cfg_da_conta if cfg_da_conta is not None else V1.config_da_conta(), blocos)

    async def upload(supa, caminho, blob, content_type="application/pdf"):
        return caminho

    async def motor():
        mot = MOT.Motor(m.banco.visao("motor-vida"), sessoes=sessoes, robo=ROBO_RAPIDO, dono="motor-vida",
                        agora=m.relogio.agora, batida_s=1.0, upload=upload, freio=lambda: False, canario=False)
        for _ in range(6):
            await mot.uma_volta()
            if not [x for x in m.banco.linhas("multicalculo_calculos")
                    if x["status"] in ("na_fila", "disparando", "calculando")]:
                break
        await mot.desligar()

    asyncio.run(motor())
    M.acompanhar(m.db, c.id, por="madrugada.calcular")
    return sessoes


def calculos(m) -> list:
    return [x for x in m.banco.linhas("multicalculo_calculos")]


def eventos_mc(m) -> list:
    return m.banco.linhas("multicalculo_eventos")


def _tipo(v):
    return V1._tipo(v)


# =====================================================================================================================
# (a) O CAMINHO FELIZ até o corpo — o corpo enviado é a FORMA gravada; o aviso da cobertura não mapeada chega ao item
# =====================================================================================================================
def test_a_da_renovacao_ao_corpo_gravado_e_o_aviso_chega_ao_item(fio, monkeypatch):
    monkeypatch.setenv(CHAVE, "1")
    c = montar(fio, monkeypatch)
    sessoes = noite(fio, c)
    # o pedido que a madrugada montou e a porta gravou: ramo 91, só o `anterior`, o capital DO PDF, cifrado
    (ped,) = fio.banco.linhas("multicalculo_pedidos")
    assert ped["ramo"] == 91 and ped["opcoes"] == ["anterior"] and ped["servico"] == "renovacao"
    assert CPF not in ped["pedido_cifrado"] and "8000" not in ped["pedido_cifrado"]
    (calc,) = calculos(fio)
    assert calc["opcao"] == "anterior"
    assert calc["coberturas"] == {"capital_morte": 100000.0, "isAppMorteAcidental": 100000.0,
                                  "isAppInvalidez": 100000.0}
    # o corpo que o robô REAL montou pelo montador REAL = a FORMA gravada ao vivo
    (s,) = sessoes.todas
    corpo = s.corpo_enviado
    assert corpo is not None, "o robô não enviou o corpo"
    assert set(corpo) == {"cotacao", "negocio", "correlationId"} and corpo["negocio"] is None
    cot = corpo["cotacao"]
    assert set(cot) == set(COT_GRAVADA), set(cot) ^ set(COT_GRAVADA)
    assert (cot["ramo"], cot["tipo"], cot["integracaoInfo"]) == (91, 5, 1)
    # 📊 as configurações GRAVADAS, valor a valor: fumante false, esporte 0, Morte = MA = IPA = 100 mil, o resto 0
    assert cot["configuracoes"] == COT_GRAVADA["configuracoes"]
    seg = cot["segurado"]
    assert {k: _tipo(v) for k, v in seg.items()} == {k: _tipo(v) for k, v in COT_GRAVADA["segurado"].items()}
    assert (seg["sexo"], seg["estadoCivil"], seg["rendaMensal"], seg["cpfCnpj"]) == ("M", 2, 8000, CPF)
    assert seg["dataNasc"].startswith("1985-05-10T") and "profissao" not in json.dumps(seg)
    por = {it["seguradora"]: it for it in cot["calculos"]}
    assert sorted(por) == [1, 4, 8]                         # HDI e Porto (profissão IGUAL) + Bradesco (não pede)
    for cod, it in por.items():
        assert {k: _tipo(v) for k, v in it.items()} == {k: _tipo(v) for k, v in ITEM_GRAVADO[cod].items()}, cod
        assert (it["percComissao"], it["percAgenciamento"]) == (10, 0)     # a comissão de vida DA CORRETORA
    assert por[4]["valoresAjusteSeguradora"] == ITEM_GRAVADO[4]["valoresAjusteSeguradora"]
    assert s.escritas == 1 and sessoes.logouts == 1                         # 1 calcularV2, e o logout no fim
    # quem saiu antes do POST é LISTADO no banco, uma vez por seguradora (checkpoint + narração = a mesma chave)
    fora = [e for e in eventos_mc(fio) if e["tipo"] == K.SEM_ATIVIDADE_COMPATIVEL]
    assert sorted(e["seguradora_codigo"] for e in fora) == [3, 5, 7, 11, 12]
    # o aviso da cobertura que não casa CHEGA ao item (o corretor confere: o `anterior` não leva a assistência)
    item = item_vida(fio, c)
    avisos = [a for e in eventos_do_item(fio, c, item) for a in ((e.get("dados") or {}).get("avisos") or [])]
    assert PED.AVISO_COBERTURAS_DE_VIDA_NAO_MAPEADAS in avisos, eventos_do_item(fio, c, item)


# =====================================================================================================================
# (b) PROFISSÃO sem casamento em TODAS → pendente(falta_dado) com a pergunta da profissão; quem saiu fica no banco
# =====================================================================================================================
def test_b_profissao_sem_casamento_em_todas_vira_a_pergunta_da_profissao(fio, monkeypatch):
    monkeypatch.setenv(CHAVE, "1")
    c = montar(fio, monkeypatch, profissao="Astronauta")
    # a conta só tem seguradoras que PEDEM profissão (sem a Bradesco, que não pede): nenhuma casa
    cfg = [x for x in V1.config_da_conta() if x["seguradora"] != 1]
    sessoes = noite(fio, c, cfg_da_conta=cfg)
    (s,) = sessoes.todas
    assert s.escritas == 0 and s.corpo_enviado is None                    # nada saiu: nenhum calcularV2
    (calc,) = calculos(fio)
    assert calc["status"] == "falhou" and "profissao_sem_casamento" in (calc["erro"] or "")
    item = item_vida(fio, c)
    assert (item["estado"], item["motivo"]) == ("pendente", "falta_dado"), (item["estado"], item["motivo"])
    ultimo = eventos_do_item(fio, c, item)[-1]
    assert ultimo["dados"]["faltando"] == ["segurado.profissao_texto"]
    assert ultimo["dados"]["perguntas"] == [PED.PERGUNTA_DE_VIDA["segurado.profissao_texto"]]
    # 🔴 a lista de quem saiu NÃO se perde: o robô nunca chegou a narrar (recusa total) — o MOTOR a gravou
    fora = [e for e in eventos_mc(fio) if e["tipo"] == K.SEM_ATIVIDADE_COMPATIVEL]
    assert sorted(e["seguradora_codigo"] for e in fora) == [3, 4, 5, 7, 8, 11, 12]
    # e a comparação não chama a profissão de "atividade"
    q = C.comparar([], [dict(e) for e in fora], ramo=91,
                   estados=[{"calculo_id": calc["id"], "corretora_company_id": c.id, "opcao": "anterior"}])
    motivos = {r["motivo"] for r in q.nao_responderam_por_opcao["anterior"]}
    assert motivos and not any("atividade" in x for x in motivos), motivos


# =====================================================================================================================
# (c) COMISSÃO de vida 0 na conta e nenhuma no pedido → pendente com a frase da configuração (nunca um número inventado)
# =====================================================================================================================
def test_c_comissao_zero_na_conta_e_nenhuma_no_pedido_pede_a_configuracao(fio, monkeypatch):
    monkeypatch.setenv(CHAVE, "1")
    c = montar(fio, monkeypatch, comissao_da_corretora=None)
    sessoes = noite(fio, c)                       # 📊 a conta gravada tem percComissaoVida 0 nas 8
    (s,) = sessoes.todas
    assert s.escritas == 0 and s.corpo_enviado is None
    item = item_vida(fio, c)
    assert item["estado"] == "pendente", (item["estado"], item["motivo"])
    ultimo = eventos_do_item(fio, c, item)[-1]
    assert ultimo["dados"]["perguntas"] == [M.FRASE_DA_COMISSAO_DE_VIDA]
    assert "Serviços" in M.FRASE_DA_COMISSAO_DE_VIDA and "comissão de vida" in M.FRASE_DA_COMISSAO_DE_VIDA
    fora = [e for e in eventos_mc(fio) if e["tipo"] == K.SEM_ATIVIDADE_COMPATIVEL]
    assert {e["seguradora_codigo"] for e in fora} >= {1, 4, 8}           # as que tinham profissão saíram por comissão


# =====================================================================================================================
# (d) a RECUSA GRAVADA ("instabilidade") → recusa POR seguradora, nenhuma oferta, o item não vira "calculada"
# =====================================================================================================================
def test_d_a_recusa_gravada_vira_recusa_por_seguradora_e_nenhuma_oferta(fio, monkeypatch):
    monkeypatch.setenv(CHAVE, "1")
    c = montar(fio, monkeypatch)
    sessoes = noite(fio, c)
    (s,) = sessoes.todas
    assert s.leituras >= 1
    assert fio.banco.linhas("multicalculo_ofertas") == []
    recusas = [e for e in eventos_mc(fio) if e["tipo"] == K.SEGURADORA_RECUSOU]
    assert sorted(e["seguradora_codigo"] for e in recusas) == [1, 4, 8]
    assert {e["familia"] for e in recusas} == {K.INSTABILIDADE}
    (calc,) = calculos(fio)
    assert calc["status"] == "fechado"
    item = item_vida(fio, c)
    assert item["estado"] == "falhou" and item["motivo"] == "calculo_fechado"


# =====================================================================================================================
# (e) CONTROLE — chave AUSENTE: a vida segue `ramo_nao_cotado`, nada vai à porta nem ao robô
# =====================================================================================================================
def test_e_chave_ausente_a_vida_segue_ramo_nao_cotado(fio, monkeypatch):
    monkeypatch.delenv(CHAVE, raising=False)
    c = montar(fio, monkeypatch)
    sessoes = noite(fio, c)
    item = item_vida(fio, c)
    assert (item["estado"], item["motivo"]) == ("pendente", "ramo_nao_cotado")
    assert fio.banco.linhas("multicalculo_pedidos") == [] and sessoes.todas == []


# =====================================================================================================================
# (f) o TEXTO que o motor grava de cada recusa de vida → o estado do item (o motor REAL escreve; a madrugada REAL lê)
# =====================================================================================================================
def _derivado(recusa: R.DisparoRecusado):
    calc = {"status": "falhou", "erro": MOT.erro_curto(MOT._motivo_recusado(recusa))}
    return M.estado_derivado([calc], 0, False), M.dados_derivados([calc], 0)


def test_f_cada_recusa_de_vida_do_robo_tem_o_seu_estado():
    # profissão → falta dado com a pergunta da profissão
    (est, dados) = _derivado(R._recusa_do_preparo("profissao_sem_casamento"))
    assert est == ("pendente", "falta_dado") and dados["faltando"] == ["segurado.profissao_texto"]
    # comissão → pendente com a frase da configuração
    (est, dados) = _derivado(R._recusa_do_preparo("comissao_de_vida_nao_configurada"))
    assert est[0] == "pendente" and dados["perguntas"] == [M.FRASE_DA_COMISSAO_DE_VIDA]
    # esporte "sim" → falta dado "qual esporte"
    with pytest.raises(R.DisparoRecusado) as exc:
        R.cotacao_do_pedido(V1.pedido_vida(vida={"esporte_radical": True}), coberturas={"capital_morte": 100000})
    (est, dados) = _derivado(exc.value)
    assert est == ("pendente", "falta_dado") and dados["faltando"] == ["vida.esporte_radical"]
    assert "esporte" in dados["perguntas"][0].lower()
    # a busca de profissão que falhou → falha PASSAGEIRA (a próxima noite tenta de novo; nunca definitiva)
    (est, dados) = _derivado(R.DisparoRecusado(R.MOTIVOS_LEGIVEIS["profissao_busca_falhou"] + " (TimeoutError)"))
    assert est[0] == "falhou" and not M.falhou_definitivo(est[1]) and dados == {"causa": "profissao_busca_falhou"}
    # CONTROLE: uma recusa que não é de vida segue como sempre (sem dados novos)
    (est, dados) = _derivado(R.DisparoRecusado("HTTP 400: outra coisa"))
    assert est == ("falhou", "calculo_falhou") and dados is None
    # o código de recusa nunca carrega dado de saúde/renda
    for codigo in ("profissao_sem_casamento", "comissao_de_vida_nao_configurada", "profissao_busca_falhou"):
        assert "fumante" not in R.MOTIVOS_LEGIVEIS[codigo] and "renda" not in R.MOTIVOS_LEGIVEIS[codigo]


# =====================================================================================================================
# UM lugar só: as coberturas por opção e o catálogo de vida são os do PORTAL (sem cópia no app)
# =====================================================================================================================
def test_um_lugar_so_para_as_coberturas_e_o_catalogo(monkeypatch):
    from portal_worker.multicalculo import presets as PRE

    monkeypatch.setenv(CHAVE, "1")
    seta = []
    original = PRE.coberturas_vida

    def espiao(*a, **k):
        seta.append(a)
        return original(*a, **k)

    monkeypatch.setattr(PRE, "coberturas_vida", espiao)
    assert PED.coberturas_de_vida_da_opcao("economica", 200000, {"isAppInvalidez": 1.0}) == {"capital_morte": 200000.0}
    assert seta, "o app não delegou ao preset do portal"
    assert {g: tuple(n for n in nomes) for g, nomes in PED.CAMPOS_DO_PEDIDO_VIDA.items()} == \
        {g: tuple(c[0] for c in cs) for g, cs in K.CAMPOS_DO_PEDIDO_VIDA.items()}
    # a sobra da ficha vira o aviso de verdade (antes: `nao_mapeadas=False` sempre que o mapa existia)
    apolice, ficha = V2.ficha_vida(LINHAS_DO_PDF)
    extras, nao_mapeadas = PED._extras_de_vida_da_ficha(apolice, ficha)
    assert extras == {"isAppMorteAcidental": 100000.0, "isAppInvalidez": 100000.0} and nao_mapeadas is True
    extras, nao_mapeadas = PED._extras_de_vida_da_ficha(*V2.ficha_vida(LINHAS_DO_PDF[:3]))
    assert nao_mapeadas is False                                          # CONTROLE: tudo casou, nenhum aviso


def test_nada_de_saude_ou_renda_no_log_do_fio(fio, monkeypatch, caplog):
    monkeypatch.setenv(CHAVE, "1")
    c = montar(fio, monkeypatch, respostas={"fumante": False, "renda_mensal": 12345, "esporte_radical": False})
    with caplog.at_level(logging.DEBUG):
        noite(fio, c)
    texto = caplog.text
    for proibido in ("12345", "fumante", CPF):
        assert proibido not in texto, proibido

# -*- coding: utf-8 -*-
"""SPEC-075 Bloco X — os testes de contrato da Portal Capability Factory.

A disciplina aqui é a que a SPEC-074 ensinou da pior forma: **inspeção de fonte
não prova comportamento**. Naquela SPEC, uma matriz de 62 asserções ficou verde
com o caminho API-first completamente inerte, porque os blocos provavam que
certas palavras apareciam no arquivo, na ordem certa.

Então, aqui, toda afirmação sobre o que o código FAZ é executada. As poucas
checagens de texto que sobraram estão marcadas e existem só ao lado de uma
asserção executável, nunca no lugar dela.

E cada bloco prova TRÊS coisas: o caso bom passa, o ruim é negado, e os dois
SÃO DIFERENTES.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


# --------------------------------------------------------------------------
# Carga sem arrastar o `app` inteiro (langchain não está disponível fora do
# contêiner). Mesmo padrão dos testes da 073/074.
# --------------------------------------------------------------------------
for _n in ("app", "app.services", "app.services.portals"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = [str(ROOT / _n.replace(".", "/"))]


def _carregar(dotted, rel):
    sp = importlib.util.spec_from_file_location(dotted, ROOT / rel)
    mo = importlib.util.module_from_spec(sp)
    sys.modules[dotted] = mo
    sp.loader.exec_module(mo)
    return mo


C = _carregar("app.services.portals.contracts", "app/services/portals/contracts.py")
R = _carregar("app.services.portals.resolver", "app/services/portals/resolver.py")
G = _carregar("app.services.portals.gateway", "app/services/portals/gateway.py")
S = _carregar("app.services.portals.sombra", "app/services/portals/sombra.py")
PR = _carregar("app.services.portals.prontidao", "app/services/portals/prontidao.py")

from portal_worker import journeys as J        # noqa: E402
from portal_worker import leases as L          # noqa: E402


# ==========================================================================
# Dublês
# ==========================================================================
class TabelaFalsa:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome
        self._filtros = {}
        self._payload = None
        self._acao = "select"

    def select(self, *a, **k):
        self._acao = "select"
        return self

    def insert(self, linha):
        self._acao = "insert"
        self._payload = linha
        return self

    def update(self, patch):
        self._acao = "update"
        self._payload = patch
        return self

    def eq(self, col, val):
        self._filtros[col] = val
        return self

    def neq(self, col, val):
        self._filtros[f"!{col}"] = val
        return self

    def or_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        self.banco.chamadas.append((self.nome, self._acao, dict(self._filtros),
                                    self._payload))
        if self.banco.explodir_em == (self.nome, self._acao):
            raise RuntimeError("banco fora do ar (simulado)")
        if self._acao == "insert":
            novo = dict(self._payload or {})
            novo.setdefault("id", f"job-{len(self.banco.linhas.get(self.nome, []))+1}")
            self.banco.linhas.setdefault(self.nome, []).append(novo)
            return types.SimpleNamespace(data=[novo])
        linhas = list(self.banco.linhas.get(self.nome, []))
        for col, val in self._filtros.items():
            if col.startswith("!"):
                linhas = [l for l in linhas if str(l.get(col[1:])) != str(val)]
            else:
                linhas = [l for l in linhas if str(l.get(col)) == str(val)]
        if self._acao == "update":
            for l in linhas:
                l.update(self._payload or {})
        return types.SimpleNamespace(data=linhas)


class BancoFalso:
    def __init__(self, linhas=None, explodir_em=None):
        self.linhas = linhas or {}
        self.chamadas = []
        self.explodir_em = explodir_em

    def table(self, nome):
        return TabelaFalsa(self, nome)


# ==========================================================================
print("\n[A1] o registry ficou mais rico SEM quebrar o formato antigo")
# ==========================================================================
d = J.JOURNEYS["hdi_corretor.cobranca_sweep"]
mod, fn = d  # desempacotamento antigo
check("A1: JOURNEYS[k] ainda desempacota em (modulo, funcao)",
      mod == "portal_worker.journeys.hdi_corretor" and fn == "cobranca_sweep")
check("A1: e ainda indexa e mede como tupla",
      d[0] == mod and d[1] == fn and len(d) == 2)
check("A1: mas agora tambem SABE o que faz",
      d.business_operation == J.OP_BILLING_OVERDUE_LIST
      and d.effect_class == J.READ_ONLY)
check("A1: as 14 entradas da baseline continuam la", len(J.JOURNEYS) == 14,
      len(J.JOURNEYS))
check("A1: e todas resolvem para uma funcao importavel",
      all(callable(J.get_journey(*k.rsplit(".", 1))) for k in J.JOURNEYS))

# ==========================================================================
print("\n[A2] portais_com_cobranca nao mudou de resposta")
# ==========================================================================
BASELINE_COBRANCA = ["allianz_corretor", "hdi_corretor", "mapfre_corretor",
                     "tokiomarine_corretor", "yelum_corretor", "zurich_corretor"]
check("A2: exatamente os 6 da baseline, na mesma ordem",
      J.portais_com_cobranca() == BASELINE_COBRANCA, J.portais_com_cobranca())
check("A2: e a nova forma de perguntar da a MESMA lista",
      J.portais_com_operacao(J.OP_BILLING_OVERDUE_LIST) == BASELINE_COBRANCA)
check("A2 CONTROLE: vidros NAO entra na cobranca",
      not J.tem_cobranca("vidros_lanternas"))
check("A2 CONTROLE: e uma operacao inexistente devolve lista vazia",
      J.portais_com_operacao("nao.existe") == [])

# ==========================================================================
print("\n[A3] conflito de efeito: tool fraca + journey material = RECUSA")
# ==========================================================================
reprova, motivo = J.conflito_de_efeito(J.READ_ONLY, J.MATERIAL_SIDE_EFFECT)
check("A3: read autorizado + journey material -> reprova", reprova, motivo)
check("A3: e o motivo explica o que aconteceria",
      "autorizou" in motivo or "autorizado" in motivo, motivo)
check("A3 CONTROLE: material autorizado + journey read -> NAO reprova",
      not J.conflito_de_efeito(J.MATERIAL_SIDE_EFFECT, J.READ_ONLY)[0])
check("A3 CONTROLE: iguais nao reprovam",
      not J.conflito_de_efeito(J.READ_ONLY, J.READ_ONLY)[0])
check("A3: classe DESCONHECIDA na journey e tratada como a mais forte",
      J.conflito_de_efeito(J.READ_ONLY, "classe_inventada")[0])
check("A3: e classe_mais_forte nunca rebaixa",
      J.classe_mais_forte(J.READ_ONLY, J.MATERIAL_SIDE_EFFECT) == J.MATERIAL_SIDE_EFFECT
      and J.classe_mais_forte(J.MATERIAL_SIDE_EFFECT, J.READ_ONLY) == J.MATERIAL_SIDE_EFFECT)

# ==========================================================================
print("\n[A4] o vocabulario de efeito e UM SO")
# ==========================================================================
from portal_worker.guardrails import CLASSES_VALIDAS  # noqa: E402

check("A4: as classes do registry sao as mesmas do guardrails",
      set(J.FORCA_DA_CLASSE) == set(CLASSES_VALIDAS),
      (J.FORCA_DA_CLASSE, CLASSES_VALIDAS))

# ==========================================================================
print("\n[A5] a matriz sai do codigo, entao nao mente")
# ==========================================================================
m = J.matriz_de_capacidades()
check("A5: as 3 operacoes registradas aparecem", set(m) == set(J.operacoes_registradas()))
check("A5: assistencia e material na matriz",
      m[J.OP_ASSISTANCE_GLASS_REQUEST]["effect_class"] == J.MATERIAL_SIDE_EFFECT)
check("A5 CONTROLE: cobranca e leitura",
      m[J.OP_BILLING_OVERDUE_LIST]["effect_class"] == J.READ_ONLY)
check("A5: nenhuma operacao tem duas journeys no MESMO portal (ambiguidade)",
      all(len(b["portais"]) == len(set(b["portais"])) for b in m.values()))

# ==========================================================================
print("\n[B1] modo do gateway falha FECHADO")
# ==========================================================================
_orig = os.environ.get("PORTAL_EXECUTION_GATEWAY_MODE")
try:
    for v, esperado in [(None, C.MODO_LEGACY), ("legacy", C.MODO_LEGACY),
                        ("shadow", C.MODO_SHADOW), ("on", C.MODO_ON),
                        ("ON", C.MODO_ON), ("LIGADO", C.MODO_LEGACY),
                        ("", C.MODO_LEGACY), ("sim", C.MODO_LEGACY)]:
        if v is None:
            os.environ.pop("PORTAL_EXECUTION_GATEWAY_MODE", None)
        else:
            os.environ["PORTAL_EXECUTION_GATEWAY_MODE"] = v
        got = G.modo_do_gateway()
        check(f"B1: {v!r} -> {esperado}", got == esperado, got)
finally:
    if _orig is None:
        os.environ.pop("PORTAL_EXECUTION_GATEWAY_MODE", None)
    else:
        os.environ["PORTAL_EXECUTION_GATEWAY_MODE"] = _orig

# ==========================================================================
print("\n[B2] o contrato NAO deixa o modelo escolher funcao nem conta")
# ==========================================================================
campos = set(C.PortalExecutionRequest.__dataclass_fields__)
for proibido in ("journey", "journey_key", "module", "function", "account_id",
                 "cookie", "token", "password", "proxy", "portal_key"):
    check(f"B2: `{proibido}` NAO existe no contrato", proibido not in campos)
check("B2 CONTROLE: e os campos de negocio existem",
      {"operation_key", "business_input", "insurer_key"} <= campos)
check("B2: os hints existem, mas com nome que os marca como hint",
      "portal_key_hint" in campos and "account_id_hint" in campos)

# ==========================================================================
print("\n[B3] hint so vale de chamador confiavel — e mesmo assim e conferido")
# ==========================================================================
req_nao_conf = C.PortalExecutionRequest(company_id="c1", operation_key="x")
req_conf = C.PortalExecutionRequest(company_id="c1", operation_key="x",
                                    origem_confiavel=True)
check("B3: origem nao confiavel nao usa hint", not req_nao_conf.hints_utilizaveis())
check("B3 CONTROLE: confiavel usa", req_conf.hints_utilizaveis())
pk, mot = R.resolver_portal("billing.overdue.list", portal_key_hint="hdi_corretor",
                            hint_confiavel=False)
check("B3: hint de origem NAO confiavel e recusado", pk is None, mot)
pk2, _ = R.resolver_portal("billing.overdue.list", portal_key_hint="hdi_corretor",
                           hint_confiavel=True)
check("B3 CONTROLE: hint confiavel passa -> os dois casos diferem",
      pk2 == "hdi_corretor" and pk is None)
pk3, mot3 = R.resolver_portal("assistance.glass.request",
                              portal_key_hint="hdi_corretor", hint_confiavel=True)
check("B3: hint que NAO implementa a operacao e recusado, nao obedecido",
      pk3 is None, mot3)

# ==========================================================================
print("\n[F1] multi-account: duas contas e ninguem disse qual -> RECUSA (P0)")
# ==========================================================================
banco_2contas = BancoFalso({"portal_accounts": [
    {"id": "a1", "company_id": "c1", "portal_key": "allianz_corretor",
     "account_label": "matriz"},
    {"id": "a2", "company_id": "c1", "portal_key": "allianz_corretor",
     "account_label": "filial"},
]})
r = R.resolver_conta(banco_2contas, company_id="c1", portal_key="allianz_corretor")
check("F1: duas contas sem criterio -> ambigua", r.estado == R.CONTA_AMBIGUA, r.motivo)
check("F1: e NAO pode executar", not r.pode_executar)
check("F1: o motivo nomeia as duas", "matriz" in r.motivo and "filial" in r.motivo,
      r.motivo)

banco_1conta = BancoFalso({"portal_accounts": [
    {"id": "a1", "company_id": "c1", "portal_key": "allianz_corretor",
     "account_label": "principal"}]})
r1 = R.resolver_conta(banco_1conta, company_id="c1", portal_key="allianz_corretor")
check("F1 CONTROLE: UMA conta resolve -> os dois casos diferem",
      r1.pode_executar and r1.account_id == "a1")

r2 = R.resolver_conta(banco_2contas, company_id="c1", portal_key="allianz_corretor",
                      account_label="filial")
check("F1 CONTROLE: com o rotulo, resolve", r2.pode_executar and r2.account_id == "a2")

# ==========================================================================
print("\n[F2] cross-tenant: conta de OUTRA corretora e recusada (P0)")
# ==========================================================================
banco_outro = BancoFalso({"portal_accounts": [
    {"id": "a1", "company_id": "c1", "portal_key": "allianz_corretor",
     "account_label": "matriz"}]})
r3 = R.resolver_conta(banco_outro, company_id="c1", portal_key="allianz_corretor",
                      account_id_hint="a-de-outra-empresa", hint_confiavel=True)
check("F2: hint de conta que nao e desta corretora -> recusa",
      r3.estado == R.CONTA_DE_OUTRA_CORRETORA, r3.estado)
check("F2 CONTROLE: hint de conta DESTA corretora passa",
      R.resolver_conta(banco_outro, company_id="c1", portal_key="allianz_corretor",
                       account_id_hint="a1", hint_confiavel=True).pode_executar)
# 🔴 A prova de que o filtro por company_id existe de verdade: a mesma conta,
# perguntada por OUTRA corretora, não aparece.
r4 = R.resolver_conta(banco_outro, company_id="c2", portal_key="allianz_corretor")
check("F2: a conta da c1 NAO aparece para a c2", r4.estado == R.CONTA_AUSENTE, r4.estado)
check("F2: e a consulta filtrou por company_id de verdade",
      any(ch[2].get("company_id") == "c2" for ch in banco_outro.chamadas))

# ==========================================================================
print("\n[F3] banco fora do ar e FAIL-CLOSED, nao 'siga sem conta'")
# ==========================================================================
banco_morto = BancoFalso({"portal_accounts": []},
                         explodir_em=("portal_accounts", "select"))
r5 = R.resolver_conta(banco_morto, company_id="c1", portal_key="allianz_corretor")
check("F3: leitura falha -> indisponivel", r5.estado == R.CONTA_INDISPONIVEL)
check("F3: e NAO pode executar", not r5.pode_executar)
check("F3 CONTROLE: portal PUBLICO nao precisa de conta nem consulta banco",
      R.resolver_conta(banco_morto, company_id="c1",
                       portal_key="vidros_lanternas").pode_executar)

# ==========================================================================
print("\n[G1] idempotencia: so material exige chave")
# ==========================================================================
check("G1: material exige", C.precisa_de_idempotencia(J.MATERIAL_SIDE_EFFECT))
check("G1 CONTROLE: leitura nao exige", not C.precisa_de_idempotencia(J.READ_ONLY))
gw = G.PortalExecutionGateway(BancoFalso())
req_mat = C.PortalExecutionRequest(company_id="c1",
                                   operation_key="assistance.glass.request")
d_mat = J.JOURNEYS["vidros_lanternas.abrir_atendimento"]
d_read = J.JOURNEYS["hdi_corretor.cobranca_sweep"]
check("G1: o gateway deriva chave para material",
      bool(gw.chave_de_idempotencia(req_mat, d_mat)))
check("G1 CONTROLE: e nao deriva para leitura",
      gw.chave_de_idempotencia(req_mat, d_read) is None)
check("G1: chave do chamador VENCE a derivada",
      gw.chave_de_idempotencia(
          C.PortalExecutionRequest(company_id="c1", operation_key="x",
                                   idempotency_key="minha"), d_mat) == "minha")

# ==========================================================================
print("\n[G2] a conferencia do Stripe: mesma chave + corpo diferente = CONFLITO")
# ==========================================================================
r_a = C.PortalExecutionRequest(company_id="c1", operation_key="assistance.glass.request",
                               business_input={"peca": "para-brisa"})
r_b = C.PortalExecutionRequest(company_id="c1", operation_key="assistance.glass.request",
                               business_input={"peca": "vidro de porta"})
check("G2: pedidos diferentes tem impressoes diferentes",
      r_a.impressao_do_pedido() != r_b.impressao_do_pedido())
check("G2 CONTROLE: o mesmo pedido tem a mesma impressao",
      r_a.impressao_do_pedido() == C.PortalExecutionRequest(
          company_id="c1", operation_key="assistance.glass.request",
          business_input={"peca": "para-brisa"}).impressao_do_pedido())
check("G2 CONTROLE: linhagem NAO muda a impressao (chamadas legitimas do mesmo pedido)",
      r_a.impressao_do_pedido() == C.PortalExecutionRequest(
          company_id="c1", operation_key="assistance.glass.request",
          business_input={"peca": "para-brisa"},
          work_run_id="run-9", agent_id="ag-1", priority=1).impressao_do_pedido())
reg = C.IdempotencyRecord(idempotency_key="k", request_fingerprint=r_a.impressao_do_pedido())
check("G2: a mesma chave com OUTRO corpo conflita", reg.conflita_com(r_b))
check("G2 CONTROLE: com o mesmo corpo NAO conflita", not reg.conflita_com(r_a))
check("G2: registro antigo sem impressao nunca conflita",
      not C.IdempotencyRecord(idempotency_key="k", request_fingerprint="").conflita_com(r_b))

# ==========================================================================
print("\n[O1] retry por classe de efeito (desenho do Temporal)")
# ==========================================================================
casos = [
    (J.READ_ONLY, "", C.RETRY_AUTOMATICO),
    (J.MATERIAL_SIDE_EFFECT, "", C.RETRY_SE_NADA_CRIADO),
    (J.MATERIAL_SIDE_EFFECT, "armed", C.RECONCILIAR),
    (J.MATERIAL_SIDE_EFFECT, "submitted", C.RECONCILIAR),
    (J.MATERIAL_SIDE_EFFECT, "unknown", C.RECONCILIAR),
    (J.MATERIAL_SIDE_EFFECT, "confirmed", C.RETRY_PROIBIDO),
    (J.REVERSIBLE_UI, "", C.RETRY_SE_NADA_CRIADO),
    ("classe_inventada", "", C.RECONCILIAR),
]
for cl, fase, esperado in casos:
    pol, _ = C.politica_de_retry(cl, fase)
    check(f"O1: {cl}/{fase or '-'} -> {esperado}", pol == esperado, pol)
check("O1: e `pode_repetir` NUNCA e True depois de confirmado",
      not C.pode_repetir(J.MATERIAL_SIDE_EFFECT, "confirmed"))
check("O1 CONTROLE: leitura pode repetir -> os dois diferem",
      C.pode_repetir(J.READ_ONLY, ""))
check("O1: as 8 respostas nao sao todas iguais",
      len({C.politica_de_retry(c, f)[0] for c, f, _ in casos}) >= 3)

# ==========================================================================
print("\n[H1] o estado de NEGOCIO vence o rotulo tecnico")
# ==========================================================================
job_falhou_com_efeito = {"status": "failed", "evidence": {
    "critical_effect": {"phase": "submitted", "name": "abrir"}}}
check("H1: job `failed` com efeito submetido -> maybe_committed",
      G.traduzir_estado(job_falhou_com_efeito) == C.NEGOCIO_TALVEZ_COMMITADO)
check("H1 CONTROLE: job `failed` SEM efeito -> failed",
      G.traduzir_estado({"status": "failed", "evidence": {}}) == C.NEGOCIO_FALHOU)
check("H1 CONTROLE: job `done` -> ok",
      G.traduzir_estado({"status": "done", "evidence": {}}) == C.NEGOCIO_OK)
check("H1: aguardando escolha do segurado -> precisa humano",
      G.traduzir_estado({"status": "done", "evidence": {
          "vidros_estado": {"estado": "aguardando_escolha_do_segurado"}}})
      == C.NEGOCIO_PRECISA_HUMANO)
check("H1: e maybe_committed esta na lista dos que NAO repetem",
      C.NEGOCIO_TALVEZ_COMMITADO in C.NAO_REPETIR)

# ==========================================================================
print("\n[B4] o gateway em `legacy`/`shadow` NAO cria job")
# ==========================================================================
# ⚠️ O relógio é INJETADO aqui de propósito, e a razão é uma medição.
#
# 📊 A primeira versão deste bloco construía `PortalExecutionGateway(banco)` sem
# relógio. A mutação que remove o portão de modo (`if modo != C.MODO_ON` →
# `if False`) fazia o gateway executar em `legacy` — e, executando, ele caía no
# laço de espera com `time.sleep` REAL: 150 segundos. O teste **pendurava** em
# vez de acender vermelho, e a bateria de mutação registrou `exit=124`.
#
# 🔴 Teste que pendura é pior que teste que falha: no CI ele não parece um
# defeito, parece a máquina lenta. Com o relógio injetado a mesma mutação vira
# uma vermelha em milissegundos.
_relogio_b4 = {"t": 0.0}


def _agora_b4():
    return _relogio_b4["t"]


def _dormir_b4(s):
    _relogio_b4["t"] += 1000  # estoura a espera na primeira volta


for modo in (C.MODO_LEGACY, C.MODO_SHADOW):
    os.environ["PORTAL_EXECUTION_GATEWAY_MODE"] = modo
    _relogio_b4["t"] = 0.0
    banco = BancoFalso({"portal_accounts": [
        {"id": "a1", "company_id": "c1", "portal_key": "hdi_corretor",
         "account_label": "principal"}]})
    res = G.PortalExecutionGateway(banco, agora=_agora_b4,
                                   dormir=_dormir_b4).executar(
        C.PortalExecutionRequest(company_id="c1",
                                 operation_key="billing.overdue.list",
                                 insurer_key="hdi"))
    inserts = [ch for ch in banco.chamadas if ch[1] == "insert"]
    check(f"B4: em `{modo}` nenhum job foi criado", inserts == [], inserts)
    check(f"B4: em `{modo}` ele ainda RESOLVEU a journey",
          res.data.get("journey_key") == "cobranca_sweep", res.data)
    check(f"B4: e o resultado diz que nao executou",
          res.data.get("modo") == modo, res.data)
os.environ.pop("PORTAL_EXECUTION_GATEWAY_MODE", None)

# ==========================================================================
print("\n[B5] em `on` ele cria — COM linhagem — e o efeito conflitante barra")
# ==========================================================================
os.environ["PORTAL_EXECUTION_GATEWAY_MODE"] = C.MODO_ON
banco = BancoFalso({"portal_accounts": [
    {"id": "a1", "company_id": "c1", "portal_key": "hdi_corretor",
     "account_label": "principal"}]})
gw2 = G.PortalExecutionGateway(banco, agora=lambda: 0.0, dormir=lambda s: None)
res = gw2.executar(C.PortalExecutionRequest(
    company_id="c1", operation_key="billing.overdue.list", insurer_key="hdi",
    work_run_id="run-42", wait_mode=C.ESPERA_ENFILEIRAR))
criados = [ch[3] for ch in banco.chamadas if ch[1] == "insert"]
check("B5: em `on` o job foi criado", len(criados) == 1, len(criados))
if criados:
    linha = criados[0]
    check("B5: com o portal certo", linha.get("portal_key") == "hdi_corretor")
    check("B5: com a journey certa", linha.get("journey") == "cobranca_sweep")
    check("B5: com a conta da corretora", linha.get("account_id") == "a1")
    lin = ((linha.get("evidence") or {}).get("gateway") or {}).get("linhagem") or {}
    check("B5: e com a LINHAGEM do Work Run", lin.get("work_run_id") == "run-42", lin)
    check("B5: e a operacao de negocio registrada",
          lin.get("operation_key") == "billing.overdue.list")
    # 🔴 nenhum segredo atravessa
    txt = str(linha)
    check("B5: nenhum segredo na linha gravada",
          not any(p in txt.lower() for p in ("password", "secret", "cookie", "token")),
          txt[:160])

# efeito conflitante: tool autorizada como leitura, journey material
banco2 = BancoFalso({"portal_accounts": []})
res_conf = G.PortalExecutionGateway(banco2).executar(C.PortalExecutionRequest(
    company_id="c1", operation_key="assistance.glass.request",
    effect_class_autorizada=J.READ_ONLY))
check("B5: tool autorizada como READ + journey material -> nao autorizado",
      res_conf.business_state == C.NEGOCIO_NAO_AUTORIZADO, res_conf.business_state)
check("B5: e NENHUM job foi criado",
      [ch for ch in banco2.chamadas if ch[1] == "insert"] == [])
check("B5: e o resultado diz que nao adianta repetir", not res_conf.pode_repetir)
banco3 = BancoFalso({"portal_accounts": []})
res_ok = G.PortalExecutionGateway(banco3, agora=lambda: 0.0,
                                  dormir=lambda s: None).executar(
    C.PortalExecutionRequest(company_id="c1",
                             operation_key="assistance.glass.request",
                             effect_class_autorizada=J.MATERIAL_SIDE_EFFECT,
                             wait_mode=C.ESPERA_ENFILEIRAR))
check("B5 CONTROLE: autorizacao material passa -> os dois casos diferem",
      res_ok.business_state != C.NEGOCIO_NAO_AUTORIZADO, res_ok.business_state)
os.environ.pop("PORTAL_EXECUTION_GATEWAY_MODE", None)

# ==========================================================================
print("\n[B6] tempo esgotado NAO e falha")
# ==========================================================================
os.environ["PORTAL_EXECUTION_GATEWAY_MODE"] = C.MODO_ON
relogio = {"t": 0.0}
banco4 = BancoFalso({"portal_accounts": []})
gw4 = G.PortalExecutionGateway(
    banco4, agora=lambda: relogio["t"],
    dormir=lambda s: relogio.__setitem__("t", relogio["t"] + 1000))
res_to = gw4.executar(C.PortalExecutionRequest(
    company_id="c1", operation_key="assistance.glass.request"))
check("B6: espera esgotada NAO vira `failed`",
      res_to.business_state != C.NEGOCIO_FALHOU, res_to.business_state)
check("B6: e diz explicitamente para nao pedir de novo", not res_to.pode_repetir)
os.environ.pop("PORTAL_EXECUTION_GATEWAY_MODE", None)

# ==========================================================================
print("\n[N1] lease: so o dono renova e so o dono libera")
# ==========================================================================
class RedisFalso:
    def __init__(self):
        self.dados = {}

    def ping(self):
        return True

    def set(self, k, v, nx=False, ex=None):
        if nx and k in self.dados:
            return None
        self.dados[k] = v
        return True

    def get(self, k):
        return self.dados.get(k)

    def eval(self, script, numkeys, *args):
        k, esperado = args[0], args[1]
        if self.dados.get(k) != esperado:
            return 0
        if "DEL" in script:
            self.dados.pop(k, None)
        return 1

    def delete(self, k):
        self.dados.pop(k, None)


rf = RedisFalso()
lease = L.LeaseDePortal(cliente=rf)
k = L.chave_de_conta("c1", "allianz_corretor", "matriz")
check("N1: A adquire", lease.adquirir(k, "A", 60))
check("N1: B NAO adquire a mesma conta", not lease.adquirir(k, "B", 60))
check("N1: B NAO consegue renovar o que nao e dele", not lease.renovar(k, "B", 60))
check("N1: B NAO consegue liberar o que nao e dele", not lease.liberar(k, "B"))
check("N1 CONTROLE: A renova", lease.renovar(k, "A", 60))
check("N1 CONTROLE: A libera", lease.liberar(k, "A"))
check("N1 CONTROLE: e agora B consegue -> os dois casos diferem",
      lease.adquirir(k, "B", 60))
k2 = L.chave_de_conta("c1", "allianz_corretor", "filial")
check("N1: OUTRA conta do mesmo portal roda em paralelo",
      lease.adquirir(k2, "C", 60))
check("N1: e as chaves sao mesmo diferentes", k != k2)

# ==========================================================================
print("\n[N2] concorrencia: default 1, e Redis fora rebaixa")
# ==========================================================================
_c = os.environ.get("PORTAL_WORKER_CONCURRENCY")
try:
    os.environ.pop("PORTAL_WORKER_CONCURRENCY", None)
    check("N2: default e 1", L.concorrencia_configurada() == 1)
    for v, esperado in [("4", 4), ("0", 1), ("-3", 1), ("999", L.TETO_CONCORRENCIA),
                        ("abc", 1), ("", 1)]:
        os.environ["PORTAL_WORKER_CONCURRENCY"] = v
        check(f"N2: {v!r} -> {esperado}", L.concorrencia_configurada() == esperado,
              L.concorrencia_configurada())
finally:
    if _c is None:
        os.environ.pop("PORTAL_WORKER_CONCURRENCY", None)
    else:
        os.environ["PORTAL_WORKER_CONCURRENCY"] = _c
efetiva, motivo = L.politica_com_redis_fora(6)
check("N2: sem Redis a concorrencia cai para 1", efetiva == 1, efetiva)
check("N2: e o motivo explica por que", "serial" in motivo.lower()
      or "redis" in motivo.lower(), motivo)

# ==========================================================================
print("\n[L1] blocker ANULA o score, nao subtrai")
# ==========================================================================
dv = J.JOURNEYS["vidros_lanternas.abrir_atendimento"]
# ⚠️ Nem todo sinal e booleano — `caminho_primario` e uma escada
# (`api|dom|adaptive|vision`) e `ultimo_canario` e uma data. A primeira versao
# deste bloco mandou `True` para os dois e viu 90 em vez de 100; o erro era meu,
# nao do modulo, e ele me disse exatamente qual dimensao faltava.
todos_verdes = {n: True for n in PR.SINAIS_CONHECIDOS}
todos_verdes["caminho_primario"] = "api"
todos_verdes["ultimo_canario"] = "2026-08-16"

bom = PR.avaliar_journey(dv, todos_verdes)
check("L1: tudo verde chega a 100", bom["score"] == 100, bom.get("score"))
check("L1: e o estado e o de release", bom["estado"] == "LIVE_APPROVED", bom.get("estado"))
check("L1 CONTROLE: e ele fica elegivel", bom.get("live_eligible") is True)

ruim = dict(todos_verdes)
ruim["idempotencia_provada"] = False  # hard blocker de efeito material
mau = PR.avaliar_journey(dv, ruim)
check("L1: com um blocker o score vai a ZERO, nao a 85",
      mau["score"] == 0, mau.get("score"))
check("L1: e a medicao NAO foi jogada fora (score_bruto segue alto)",
      mau.get("score_bruto", 0) >= 80, mau.get("score_bruto"))
check("L1: e ele NAO e elegivel", mau.get("live_eligible") is False)
check("L1 CONTROLE: os dois casos diferem no score", bom["score"] != mau["score"])
check("L1 CONTROLE: mas o score_bruto e parecido — a diferenca e o blocker, "
      "nao a medicao", abs(bom["score_bruto"] - mau["score_bruto"]) <= 20,
      (bom["score_bruto"], mau["score_bruto"]))

# 🔴 A prova de que o blocker anula, e nao subtrai: se subtraisse, uma journey
# com MUITA evidencia e um blocker teria score maior que uma sem evidencia e
# sem blocker — e ordenar por score recomendaria subir a perigosa.
sem_nada = PR.avaliar_journey(dv, {"caminho_primario": "api"})
check("L1: journey vazia SEM blocker nao pode perder para uma cheia COM blocker",
      not (mau["score"] > sem_nada["score"]), (mau["score"], sem_nada["score"]))

# Read-only nao precisa de canario transacional para chegar a 100.
dr = J.JOURNEYS["mapfre_corretor.cobranca_sweep"]
so_read = dict(todos_verdes)
so_read["canario_transacional_verde"] = False
check("L1 CONTROLE: read-only chega a 100 sem canario transacional",
      PR.avaliar_journey(dr, so_read)["score"] == 100,
      PR.avaliar_journey(dr, so_read)["score"])
check("L1 CONTROLE: e a MATERIAL nao chega -> os dois casos diferem",
      PR.avaliar_journey(dv, so_read)["score"] != 100)

# Sinal inventado tem de falhar ALTO: typo em sinal de blocker falharia ABERTO.
try:
    PR.avaliar_journey(dv, {"sinal_que_nao_existe": True})
    check("L1: sinal desconhecido levanta", False, "passou em silencio")
except Exception as e:  # noqa: BLE001
    check("L1: sinal desconhecido levanta (typo nao pode falhar aberto)",
          "Desconhecid" in type(e).__name__ or "desconhec" in str(e).lower(),
          f"{type(e).__name__}: {e}")

# A matriz gerada avisa que e gerada.
md = PR.matriz_markdown()
check("L1: a matriz gerada diz que NAO deve ser editada a mao",
      "NÃO EDITAR" in md.upper() or "NAO EDITAR" in md.upper(), md[:120])
check("L1: e lista as 3 operacoes do registry",
      all(op in md for op in J.operacoes_registradas()))

# ==========================================================================
print("\n[U1] a sombra nunca cria job e nunca derruba o legado")
# ==========================================================================
banco5 = BancoFalso({
    "portal_accounts": [{"id": "a1", "company_id": "c1",
                         "portal_key": "hdi_corretor", "account_label": "p"}],
    "portal_jobs": [{"id": "j1", "company_id": "c1", "evidence": {"ja_estava": 1}}]})
diff = S.observar(banco5, job_id="j1", company_id="c1",
                  operation_key="billing.overdue.list",
                  portal_key_hint="hdi_corretor",
                  portal_key_legado="hdi_corretor", journey_legada="cobranca_sweep")
check("U1: a sombra concorda com o legado", diff.get("concorda") is True, diff)
check("U1: nenhum job foi criado",
      [ch for ch in banco5.chamadas if ch[1] == "insert"] == [])
ev = banco5.linhas["portal_jobs"][0]["evidence"]
check("U1: o diff foi gravado no evidence", "gateway_sombra" in ev)
check("U1: e o que ja estava no evidence NAO foi apagado", ev.get("ja_estava") == 1, ev)

diff2 = S.observar(banco5, job_id="j1", company_id="c1",
                   operation_key="billing.overdue.list",
                   portal_key_hint="hdi_corretor",
                   portal_key_legado="allianz_corretor", journey_legada="cobranca_sweep")
check("U1 CONTROLE: divergencia e detectada -> os dois casos diferem",
      diff2.get("concorda") is False, diff2)

banco_ruim = BancoFalso({}, explodir_em=("portal_accounts", "select"))
diff3 = S.observar(banco_ruim, job_id=None, company_id="c1",
                   operation_key="billing.overdue.list",
                   portal_key_legado="hdi_corretor", journey_legada="cobranca_sweep")
check("U1: banco quebrado nao levanta para o chamador", isinstance(diff3, dict))

# ==========================================================================
print("[N3] perder a lease no meio do job ABORTA — nao continua clicando")
# ==========================================================================
# 🔴 Achado por juiz critico em 16/08/2026: `_bater()` chamava `lease.renovar()`
# e DESCARTAVA o retorno. `renovar` devolve False quando a lease ja nao e mais
# desta worker — ela venceu e outro processo assumiu a conta. Ignorar isso deixa
# o job continuar clicando numa sessao que outro worker ja tomou: a colisao
# exata que o Bloco N existe para impedir.
#
# O cenario nao e exotico: lease de 120s, job de ate 1200s. Basta o event loop
# ficar sem ceder controle por mais que o TTL.
import inspect as _insp  # noqa: E402

import portal_worker.worker as W  # noqa: E402

_src_rodar = _insp.getsource(W.run_lote)
check("N3: o retorno de `renovar` e testado, nao descartado",
      "if not lease.renovar(" in _src_rodar)
check("N3: e a perda de posse tem um sinal proprio",
      "perdeu_a_posse" in _src_rodar)
check("N3: o job e CANCELADO quando a posse se perde",
      "tarefa.cancel()" in _src_rodar)

# E a prova EXECUTAVEL do desfecho. Sem ela, as tres de texto acima passariam
# com um `pass` no lugar do tratamento.
_banco_lease = BancoFalso({"portal_jobs": [
    {"id": "j9", "company_id": "c1", "status": "running", "evidence": {}}]})
W._marcar_lease_perdida(_banco_lease, {"id": "j9"})
_j9 = _banco_lease.linhas["portal_jobs"][0]
check("N3: o job abortado vira `needs_human`, NAO `queued`",
      _j9["status"] == "needs_human", _j9["status"])
check("N3 CONTROLE: `queued` seria o valor tentador e errado",
      _j9["status"] != "queued")
check("N3: e o erro ensina o que NAO fazer",
      "NAO reexecute" in str(_j9.get("error") or ""), _j9.get("error"))

# ==========================================================================
print("[Q1] o worker NAO apaga o que o gateway e a sombra gravaram")
# ==========================================================================
# 🔴 Segundo achado do juiz: `update({"evidence": ...})` substitui a coluna
# jsonb INTEIRA. O worker comecava em `{}` e, ao terminar, apagava
# `gateway.linhagem`, `gateway_fingerprint` e `gateway_sombra`.
#
# O estrago seria silencioso e no pior lugar: o diff de sombra existe para
# decidir o cutover, e sumiria justamente dos jobs CONCLUIDOS.
_src_run = _insp.getsource(W._run_job)
_i_ev = _src_run.find("evidence: Dict[str, Any]")
check("Q1: o worker parte do evidence que JA esta no banco",
      _i_ev > 0 and 'job.get("evidence")' in _src_run[_i_ev:_i_ev + 300])
check("Q1 CONTROLE: e nao parte do vazio",
      "evidence: Dict[str, Any] = {}" not in _src_run)

# A prova executavel da CONSEQUENCIA de apagar: impressao vazia nunca conflita.
_req_q1 = C.PortalExecutionRequest(company_id="c1", operation_key="x",
                                   business_input={"a": 1})
check("Q1: registro SEM impressao nunca conflita (o custo de apagar)",
      not C.IdempotencyRecord("k", "").conflita_com(_req_q1))
check("Q1 CONTROLE: registro COM impressao de outro pedido conflita",
      C.IdempotencyRecord("k", "impressao-de-outro").conflita_com(_req_q1))


print("\n" + "=" * 70)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 70)
sys.exit(1 if FAIL else 0)

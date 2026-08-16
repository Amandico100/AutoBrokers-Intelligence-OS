# -*- coding: utf-8 -*-
"""SPEC-074 Bloco S — as mutações que a implementação PRECISA detectar.

Mesma disciplina da 073: cada bloco prova três coisas — o caso bom passa, o
ruim é negado, e os dois SÃO DIFERENTES. Sem a terceira, uma função que devolve
sempre a mesma resposta passaria nas duas primeiras.

E a linha de controle no fim prova que a SPEC-074 não virou "nega tudo".
"""
from __future__ import annotations

import asyncio
import importlib.util
import inspect
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def _carregar(dotted: str, rel: str):
    spec = importlib.util.spec_from_file_location(dotted, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = m
    spec.loader.exec_module(m)
    return m


for _n in ("app", "app.agents", "app.agents.tools", "app.services", "app.tasks"):
    _m = sys.modules.setdefault(_n, types.ModuleType(_n))
    _m.__path__ = []

_carregar("app.services.attendance_ficha", "app/services/attendance_ficha.py")
_carregar("app.services.perguntas_do_portal_de_vidros",
          "app/services/perguntas_do_portal_de_vidros.py")
F = _carregar("app.services.vidros_flow", "app/services/vidros_flow.py")
PP = _carregar("app.agents.tools.portal_params", "app/agents/tools/portal_params.py")
V = _carregar("app.tasks.vigia_do_portal", "app/tasks/vigia_do_portal.py")

from fixtures.vidros import maxpar_apolices as FA        # noqa: E402
from fixtures.vidros import maxpar_atendimento as FT     # noqa: E402
from fixtures.vidros import maxpar_questionario as FQ    # noqa: E402
from portal_worker import guardrails as G                # noqa: E402
from portal_worker.journeys import vidros_api as A       # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_estado as E    # noqa: E402
from portal_worker.journeys import vidros_questionario as Q  # noqa: E402

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:230] if extra else ""))


# ==========================================================================
print("\n[V01] preflight NAO pode liberar escrita fora de policy_ok")
# ==========================================================================
libera = [c for c in (
    A.classificar_preflight(200, FA.APOLICE_OK),
    A.classificar_preflight(200, FA.APOLICE_NAO_ENCONTRADA),
    A.classificar_preflight(200, FA.APOLICE_AMBIGUA),
    A.classificar_preflight(400, FA.COVERAGE_ABSENT_PORTO),
    A.classificar_preflight(400, FA.OUTRA_REGRA_DE_NEGOCIO),
    A.classificar_preflight(500, None),
) if c["pode_escrever"]]
check("V01: EXATAMENTE um dos seis libera escrita", len(libera) == 1, len(libera))
check("V01: e é o policy_ok", libera[0]["estado"] == A.POLICY_OK)

# ==========================================================================
print("\n[V02] coverage_absent nao pode virar 'tenta outro ramo'")
# ==========================================================================
cov = A.classificar_preflight(400, FA.COVERAGE_ABSENT_PORTO)
check("V02: coverage_absent nao libera escrita", cov["pode_escrever"] is False)
check("V02: e nomeia o escopo que falta, para o agente explicar",
      "roda" in cov["escopo"], cov["escopo"])
check("V02 CONTROLE: outra regra com o MESMO Tipo nao vira coverage_absent",
      A.classificar_preflight(400, FA.OUTRA_REGRA_DE_NEGOCIO)["estado"]
      == A.BUSINESS_RULE_UNKNOWN)

# ==========================================================================
print("\n[V03] o questionario nao escolhe por POSICAO")
# ==========================================================================
py = Q.ler_pergunta(FQ.PERGUNTA_LADO)
pp = Q.ler_pergunta(FQ.PERGUNTA_LADO_PORTO)
check("V03: as duas ordens medidas sao mesmo diferentes",
      [o["CodigoResposta"] for o in py.opcoes] != [o["CodigoResposta"] for o in pp.opcoes])
ey = Q.escolher_resposta(py, respostas_do_segurado={"lado": "motorista"})
ep = Q.escolher_resposta(pp, respostas_do_segurado={"lado": "motorista"})
check("V03: motorista da o mesmo codigo nas duas", ey["codigo"] == ep["codigo"] == 39)
check("V03 CONTROLE: carona da OUTRO codigo",
      Q.escolher_resposta(pp, respostas_do_segurado={"lado": "carona"})["codigo"] == 38)

# ==========================================================================
print("\n[V04] 'Nao sabe' NUNCA e usado para avancar")
# ==========================================================================
sem = Q.escolher_resposta(py, respostas_do_segurado={})
check("V04: sem resposta -> falta_resposta, nao 'NAO SABE'",
      sem["situacao"] == Q.FALTA_RESPOSTA and sem["codigo"] is None, sem)
check("V04 CONTROLE: se o segurado DISSER que nao sabe, ai sim",
      Q.escolher_resposta(py, respostas_do_segurado={"lado": "nao sei"})["codigo"] == 40)

# ==========================================================================
print("\n[V05] o pedido que EXISTE nunca e retentavel")
# ==========================================================================
for est, nome in [(E.PROTOCOLO_CRIADO, "protocolo_criado"),
                  (E.ATENDIMENTO_MATERIALIZADO, "materializado"),
                  (E.AGUARDANDO_ESCOLHA, "aguardando_escolha"),
                  (E.DESCONHECIDO, "desconhecido"),
                  (E.CANCELADO, "cancelado")]:
    check(f"V05: {nome} -> safe_to_retry_open False",
          E.EstadoDoAtendimento(estado=est).safe_to_retry_open is False)
check("V05 CONTROLE: pre_protocolo PODE reabrir",
      E.EstadoDoAtendimento().safe_to_retry_open is True)

# ==========================================================================
print("\n[V06] a frase nunca diz 'nao abriu' com pedido aberto")
# ==========================================================================
f = PP.format_result({"status": "failed", "evidence": {"vidros_estado": {
    "estado": "atendimento_materializado", "tem_codigo_atendimento": True,
    "codigo_atendimento": "99999999", "existe_algo_na_seguradora": True}}})
check("V06: o numero chega mesmo com status failed", "99999999" in f)
check("V06: e a frase proibe abrir de novo",
      any(m in f.lower() for m in ("abrir de novo", "segundo atendimento", "reexecut")))
f2 = PP.format_result({"status": "failed", "error": "x", "evidence": {}})
check("V06 CONTROLE: sem pedido, a frase honesta de falha permanece",
      "99999999" not in f2 and len(f2) > 20)

# ==========================================================================
print("\n[V07] o Vigia nao trata 99% como incidente")
# ==========================================================================
base = {"created_at": "2020-01-01T00:00:00+00:00", "started_at": "2020-01-01T00:00:00+00:00",
        "params": {"placa": "QAB1A91", "dano": {"peca": "vidro de porta"}}}
d = V.diagnosticar({**base, "status": "needs_human", "evidence": {"vidros_estado": {
    "estado": "aguardando_escolha_do_segurado", "codigo_atendimento": "99999999",
    "existe_algo_na_seguradora": True}}})
check("V07: aguardando escolha nao e alarme vermelho",
      d and "nao e falha" in d["para_o_suporte"].lower(), d)
d2 = V.diagnosticar({**base, "status": "failed", "evidence": {}})
check("V07 CONTROLE: sem estado de negocio, o ramo antigo continua",
      d2 and d2["motivo"] == "falhou_e_ninguem_soube", d2)

# ==========================================================================
print("\n[V08] roteador: colisao nunca vira portal de vidros")
# ==========================================================================
check("V08: 'vidro na colisao' NAO vai ao portal",
      not F.resolver_canal(peca="vidro", relato="quebrei na colisao")["pode_portal"])
check("V08 CONTROLE: 'vidro por pedra' VAI ao portal",
      F.resolver_canal(peca="vidro", relato="pedra na estrada")["pode_portal"])
check("V08: os dois vereditos diferem",
      F.resolver_canal(peca="vidro", relato="colisao")["canal"]
      != F.resolver_canal(peca="vidro", relato="pedra")["canal"])

# ==========================================================================
print("\n[V09] dois lados NAO viram um pedido so")
# ==========================================================================
check("V09: dois lados -> dois itens",
      len(F.separar_itens("vidro de porta", "motorista e carona")) == 2)
check("V09 CONTROLE: um lado -> um item",
      len(F.separar_itens("vidro de porta", "so o do motorista")) == 1)
check("V09 CONTROLE: plural vago NAO separa (nao abre pedido por interpretacao)",
      len(F.separar_itens("vidro", "quebraram os vidros")) == 1)

# ==========================================================================
print("\n[V10] a chave de idempotencia conhece o LADO (P-79)")
# ==========================================================================
b = {"placa": "QAB1A91", "data_dano": "14/08/2026", "dano": {"peca": "vidro de porta"}}
k_m = PP.chave_de_idempotencia({**b, "especificos": {"lado_motorista_ou_carona": "motorista"}}, "c1")
k_c = PP.chave_de_idempotencia({**b, "especificos": {"lado_motorista_ou_carona": "carona"}}, "c1")
check("V10: os dois lados dao chaves DIFERENTES", k_m != k_c, (k_m, k_c))
check("V10 CONTROLE: a mesma entrada da a mesma chave",
      k_m == PP.chave_de_idempotencia({**b, "especificos": {"lado_motorista_ou_carona": "motorista"}}, "c1"))
check("V10 CONTROLE: outra corretora, outra chave",
      k_m != PP.chave_de_idempotencia({**b, "especificos": {"lado_motorista_ou_carona": "motorista"}}, "c2"))
check("V10: sem os tres dados -> vazia (fail-open, o guarda nao trava o pedido)",
      PP.chave_de_idempotencia({}, "c1") == "")
check("V10: continuacao usa OUTRA chave, nunca a de criacao",
      E.idempotencia_de_continuacao(company_id="c1", protocolo="99999999",
                                    operacao="consultar") not in (k_m, k_c))

# ==========================================================================
print("\n[V11] allowlist de host e fechada")
# ==========================================================================
check("V11: dominio-sufixo malicioso e recusado",
      not A.host_permitido("https://api.autoglass.com.br.evil.com/x"))
check("V11: metadata de nuvem e recusado",
      not A.host_permitido("http://169.254.169.254/latest/meta-data"))
check("V11 CONTROLE: o host real passa", A.host_permitido(A.BASE_API + "/atendimentos"))
check("V11 CONTROLE: subdominio legitimo passa",
      A.host_permitido("https://app.abraseuatendimento.com.br/x"))

# ==========================================================================
print("\n[V12] a flag API-first nasce desligada e falha para o DOM")
# ==========================================================================
os.environ.pop("PORTAL_VIDROS_API_FIRST", None)
check("V12: nasce desligada", AF.api_first_habilitado() is False)
os.environ["PORTAL_VIDROS_API_FIRST"] = "true"
check("V12: liga por env", AF.api_first_habilitado() is True)
os.environ.pop("PORTAL_VIDROS_API_FIRST", None)

import portal_worker.journeys.vidros_lanternas as VL  # noqa: E402

src = inspect.getsource(VL.abrir_atendimento)
check("V12: o caminho DOM continua no arquivo, depois do bloco da flag",
      "_select_insurer_start" in src and "api_first_habilitado" in src)
check("V12: e um erro no caminho novo NAO derruba o acionamento",
      "api_first_falhou" in src)
i_flag = src.find("api_first_habilitado")
i_dom = src.find("_select_insurer_start")
check("V12 CONTROLE: a flag e checada ANTES do caminho DOM, e retorna cedo",
      -1 < i_flag < i_dom, (i_flag, i_dom))

# ==========================================================================
print("\n[V13] as duas fronteiras sao NOMEADAS ao guard, e sao diferentes")
# ==========================================================================
check("V13: abrir e materializar sao acoes distintas",
      E.FRONTEIRA_ABRIR != E.FRONTEIRA_MATERIALIZAR)
check("V13: as quatro fronteiras materiais estao declaradas",
      len(set(E.FRONTEIRAS_MATERIAIS)) == 4)
g = G.PortalActionGuard(material_liberado=True,
                        acao_material_esperada=E.FRONTEIRA_ABRIR)
check("V13: o guard aceita a acao nomeada",
      g.acao_material_permitida(E.FRONTEIRA_ABRIR)[0])
check("V13 CONTROLE: e recusa a OUTRA fronteira, mesmo sendo material legitima",
      not g.acao_material_permitida(E.FRONTEIRA_CANCELAR)[0])

src_af = inspect.getsource(AF.abrir_atendimento_api)
i_pre = src_af.find("classificar_preflight")
i_post = src_af.find("criar_atendimento")
check("V13: o preflight roda ANTES do POST que cria", -1 < i_pre < i_post)
check("V13: e o guard e chamado antes do POST",
      -1 < src_af.find("guard.before") < i_post)
check("V13: falha do POST vira DESCONHECIDO, nao retry",
      "FASE_UNKNOWN" in src_af or "incerto" in src_af)

# ==========================================================================
print("\n[LINHA DE CONTROLE] a 074 nao virou 'nega tudo'")
# ==========================================================================
check("apolice valida continua liberando escrita",
      A.classificar_preflight(200, FA.APOLICE_OK)["pode_escrever"] is True)
check("pergunta com resposta continua sendo respondida",
      Q.escolher_resposta(py, respostas_do_segurado={"lado": "carona"})["situacao"] == "ok")
check("peca do portal continua indo ao portal",
      F.resolver_canal(peca="para-brisa", relato="trincou")["pode_portal"] is True)
check("um item continua sendo um pedido",
      len(F.separar_itens("para-brisa", "trincou")) == 1)
check("o read model continua sendo lido",
      E.ler_estado_do_agregado(FT.ATENDIMENTO_POS_QUESTIONARIO).codigo_atendimento
      == "99999999")
check("a franquia continua sendo lida quando existe",
      A.descricao_da_franquia(FT.ATENDIMENTO_COM_FRANQUIA)["tem"] is True)
check("e o link de vistoria e devolvido literal quando existe",
      A.vistoria_do_atendimento({**FT.ATENDIMENTO_POS_QUESTIONARIO,
                                 "LinkVistoriaMobile": "https://vistoria.mobi/app/#/app/intro/x"}
                                )["tem_link"] is True)
check("questionario completo continua chegando ao 204",
      asyncio.run(Q.rodar_questionario(
          FQ.SessaoDeQuestionarioFalsa(FQ.SEQUENCIA_PORTO),
          respostas_do_segurado={"lado": "carona"})).completo is True)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)

# -*- coding: utf-8 -*-
"""SPEC-074 — plano de trabalho, roteador e a frase que o segurado ouve.

O que este arquivo protege
==========================
    [1] multi-item   dois lados são DOIS pedidos, e o portal diz isso em texto
    [2] roteador     colisão nunca vira vidraçaria
    [3] plano        o robô sabe o que falta antes de abrir o navegador
    [4] a frase      um pedido que EXISTE nunca ouve "não consegui abrir"
    [5] o vigia      idem, e 99% aguardando escolha não é incidente
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def _carregar(dotted: str, rel: str):
    """Carrega por CAMINHO, sem passar pelos `__init__` pesados.

    Mesmo padrão de `test_o_agente_entra_no_portal_sabendo.py`: os `__init__`
    de `app.services` e `app.agents` importam langchain, qdrant, minio e openai,
    e esta suíte roda sem eles. Seguir o padrão da casa em vez de inventar um
    conftest novo — a suíte inteira do projeto é de scripts independentes.
    """
    spec = importlib.util.spec_from_file_location(dotted, ROOT / rel)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = modulo
    spec.loader.exec_module(modulo)
    return modulo


for _nome in ("app", "app.agents", "app.agents.tools", "app.services", "app.tasks"):
    _m = sys.modules.setdefault(_nome, types.ModuleType(_nome))
    _m.__path__ = []

_carregar("app.services.attendance_ficha", "app/services/attendance_ficha.py")
_carregar("app.services.perguntas_do_portal_de_vidros",
          "app/services/perguntas_do_portal_de_vidros.py")
F = _carregar("app.services.vidros_flow", "app/services/vidros_flow.py")
_PP = _carregar("app.agents.tools.portal_params", "app/agents/tools/portal_params.py")
format_result = _PP.format_result
V = _carregar("app.tasks.vigia_do_portal", "app/tasks/vigia_do_portal.py")

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:240] if extra else ""))


# ==========================================================================
print("\n[1] MULTI-ITEM — dois lados sao DOIS pedidos")
# ==========================================================================
um = F.separar_itens("vidro de porta", "quebraram o vidro da porta do motorista")
dois = F.separar_itens("vidro de porta", "quebraram os dois vidros das portas, "
                                         "do lado do motorista e do carona")
check("um lado -> um item", len(um) == 1, [i.descricao_curta for i in um])
check("e o lado e capturado", um[0].lado == "motorista", um[0])
check("🔴 dois lados -> DOIS itens", len(dois) == 2, [i.descricao_curta for i in dois])
check("e os itens sao de lados DIFERENTES",
      {i.lado for i in dois} == {"motorista", "carona"}, [i.lado for i in dois])

# 🔴 O controle que impede o separador de virar paranoico: plural vago NAO
# separa. Abrir dois pedidos por interpretacao de "os vidros" seria pior que
# perguntar — e o portal cobra por atendimento.
vago = F.separar_itens("vidro", "quebraram os vidros do carro")
check("CONTROLE: plural vago NAO separa — deixa a pergunta para o atendente",
      len(vago) == 1, [i.descricao_curta for i in vago])

diant_tras = F.separar_itens("vidro de porta", "quebrou o dianteiro e o traseiro")
check("duas posicoes tambem separam", len(diant_tras) == 2,
      [i.descricao_curta for i in diant_tras])

# A resposta do 80% manda mais que o relato solto.
resp = F.separar_itens("vidro de porta", "quebraram os dois lados",
                       especificos={"lado_motorista_ou_carona": "lado do carona"})
check("resposta do 80% desempata o relato ambiguo",
      len(resp) == 1 and resp[0].lado == "carona", [i.descricao_curta for i in resp])

check("peca vazia -> nenhum item", F.separar_itens("", "x") == [])
check("a descricao curta e legivel",
      "motorista" in um[0].descricao_curta, um[0].descricao_curta)

# ==========================================================================
print("\n[2] ROTEADOR — colisao nunca vira vidracaria")
# ==========================================================================
for peca, relato, canal in [
    ("vidro de porta", "pedra na estrada", F.CANAL_PORTAL_PUBLICO),
    ("para-brisa", "trincou", F.CANAL_PORTAL_PUBLICO),
    ("retrovisor", "quebrou no estacionamento", F.CANAL_PORTAL_PUBLICO),
    ("lanterna traseira", "bati de re no poste", F.CANAL_PORTAL_PUBLICO),
    ("farol", "queimou", F.CANAL_PORTAL_PUBLICO),
]:
    r = F.resolver_canal(peca=peca, relato=relato)
    check(f"'{peca}' -> portal", r["canal"] == canal, r)

# 🔴 A EXCLUSAO VEM ANTES DA INCLUSAO. "quebrei o vidro na colisao" tem as duas
# palavras, e o que manda e a colisao.
for peca, relato in [
    ("vidro", "quebrei o vidro na colisao com outro carro"),
    ("vidro", "o carro capotou e quebrou tudo"),
    ("para-brisa", "perda total, preciso de guincho"),
    ("vidro", "roubo do veiculo inteiro"),
]:
    r = F.resolver_canal(peca=peca, relato=relato)
    check(f"'{relato[:34]}' -> NAO portal",
          r["canal"] != F.CANAL_PORTAL_PUBLICO and not r["pode_portal"], r)

check("sem peca -> humano",
      F.resolver_canal(peca="", relato="x")["canal"] == F.CANAL_HUMANO)
check("sem apolice -> humano",
      F.resolver_canal(peca="vidro", tem_apolice=False)["canal"] == F.CANAL_HUMANO)
check("peca fora das familias medidas -> humano, nao chute",
      F.resolver_canal(peca="motor", relato="fundiu")["canal"] == F.CANAL_HUMANO)
check("CONTROLE: o motivo sempre explica a decisao",
      all(F.resolver_canal(peca=p, relato=r)["motivo"]
          for p, r in [("vidro", "pedra"), ("motor", "fundiu"), ("", "")]))

# ==========================================================================
print("\n[3] PLANO — o que falta ANTES de abrir o navegador")
# ==========================================================================
plano = F.montar_plano(peca="vidro de porta", relato="pedra na estrada",
                       tem_apolice=True)
check("plano de peca conhecida aponta o portal", plano.pode_portal is True)
check("e tem pelo menos um item", len(plano.itens) >= 1)
check("a evidencia do plano nao carrega PII",
      "cpf" not in str(plano.para_evidencia()).lower())

plano_dois = F.montar_plano(peca="vidro de porta",
                            relato="quebraram do lado do motorista e do carona",
                            tem_apolice=True)
check("plano multi-item se declara multi-item", plano_dois.multi_item is True)
check("e a evidencia diz quantos", len(plano_dois.para_evidencia()["itens"]) == 2)

plano_fora = F.montar_plano(peca="vidro", relato="capotou", tem_apolice=True)
check("plano fora do portal nao lista itens nem finge estar pronto",
      plano_fora.pode_portal is False and plano_fora.pronto is False)

# ==========================================================================
print("\n[4] A FRASE — um pedido que EXISTE nunca ouve 'nao consegui abrir'")
# ==========================================================================
job_api_ok = {"status": "failed", "error": "TimeoutError: x", "evidence": {
    "vidros_estado": {"estado": "atendimento_materializado",
                      "tem_codigo_atendimento": True,
                      "codigo_atendimento": "99999999",
                      "existe_algo_na_seguradora": True,
                      "safe_to_retry_open": False}}}
frase = format_result(job_api_ok)
check("🔴 job `failed` COM pedido criado pela API entrega o numero",
      "99999999" in frase, frase[:180])
check("e NAO diz que nao conseguiu",
      "nao consegui" not in frase.lower() and "não consegui" not in frase.lower(),
      frase[:180])
# A primeira versao desta assercao procurava a palavra "reexecut" e ficou
# vermelha — o texto real diz "NAO peca para eu abrir de novo". A frase estava
# certa; a assercao e que procurava a palavra que EU teria escrito, nao a que o
# produto escreveu. Agora ela checa o SENTIDO, com as duas formas aceitas.
check("e proibe abrir de novo, seja como for que a frase diga",
      any(m in frase.lower() for m in ("reexecut", "abrir de novo", "segundo atendimento")),
      frase[:200])

job_sem_numero = {"status": "failed", "evidence": {
    "vidros_estado": {"estado": "protocolo_criado",
                      "existe_algo_na_seguradora": True,
                      "tem_codigo_atendimento": False}}}
f2 = format_result(job_sem_numero)
check("pedido existe e numero nao foi lido -> fala a verdade incomoda",
      "FOI aberto" in f2 and "não consegui ler o número" in f2, f2[:200])
check("e ainda assim proibe reexecutar", "NÃO reexecute" in f2, f2[:200])
check("CONTROLE: nao inventa numero nenhum",
      not any(c.isdigit() for c in f2), f2[:200])

# 🔴 O controle que prova que a ponte nao quebrou o caminho antigo: o texto
# raspado da tela continua tendo prioridade e produzindo a frase de sempre.
job_texto = {"status": "needs_human", "evidence": {"protocolo": "22842291"}}
f3 = format_result(job_texto)
check("CONTROLE: protocolo lido do TEXTO continua funcionando",
      "22842291" in f3, f3[:160])

job_limpo = {"status": "failed", "error": "erro", "evidence": {}}
f4 = format_result(job_limpo)
check("CONTROLE: sem pedido nenhum, a frase honesta de falha permanece",
      "nao consegui" in f4.lower() or "não consegui" in f4.lower(), f4[:160])

# ==========================================================================
print("\n[5] O VIGIA — 99% aguardando escolha NAO e incidente")
# ==========================================================================
def _job(estado, status="needs_human", **ev):
    base = {"status": status, "created_at": "2020-01-01T00:00:00+00:00",
            "started_at": "2020-01-01T00:00:00+00:00",
            "params": {"placa": "QAB1A91", "dano": {"peca": "vidro de porta"}},
            "evidence": {"vidros_estado": {"estado": estado, **ev}}}
    return base


d_esc = V.diagnosticar(_job("aguardando_escolha_do_segurado",
                            codigo_atendimento="99999999",
                            existe_algo_na_seguradora=True))
check("aguardando escolha vira mensagem, nao alarme",
      d_esc and d_esc["motivo"] == "aguardando_escolha_do_segurado", d_esc)
check("e o suporte le que NAO e falha",
      "nao e falha" in d_esc["para_o_suporte"].lower(), d_esc["para_o_suporte"][:120])
check("e o segurado e convidado a escolher",
      "escolher" in d_esc["para_o_segurado"].lower(), d_esc["para_o_segurado"][:140])
check("e o numero chega a ele", "99999999" in d_esc["para_o_segurado"])

d_fail = V.diagnosticar(_job("atendimento_materializado", status="failed",
                             codigo_atendimento="99999999",
                             existe_algo_na_seguradora=True,
                             safe_to_retry_open=False))
# 🔴 A frase PROIBIDA e a antiga: "Tentei abrir X ... e nao consegui concluir",
# que sugere que nada aconteceu. Dizer "FOI aberto, so nao concluí a ultima
# etapa" e honesto e util — e foi isso que a primeira versao desta assercao
# reprovou por engano, procurando a substring "nao consegui" sem olhar o sentido.
check("🔴 `failed` com pedido aberto NAO usa a frase de 'tentei e nao consegui'",
      d_fail and "tentei abrir" not in d_fail["para_o_segurado"].lower(),
      d_fail["para_o_segurado"][:180] if d_fail else None)
check("diz que FOI aberto", "FOI aberto" in d_fail["para_o_segurado"])
check("e entrega o numero ao segurado", "99999999" in d_fail["para_o_segurado"])
check("e o suporte e proibido de reexecutar",
      "NAO reexecute" in d_fail["para_o_suporte"], d_fail["para_o_suporte"][:140])

d_maybe = V.diagnosticar(_job("desconhecido", status="failed",
                              precisa_reconciliar=True))
check("MAYBE_COMMITTED pede reconciliacao, nao retry",
      d_maybe and d_maybe["motivo"] == "maybe_committed", d_maybe)
check("e o segurado nao e mandado pedir de novo",
      "não precisa pedir de novo" in d_maybe["para_o_segurado"].lower(),
      d_maybe["para_o_segurado"][:140])

# CONTROLE — sem estado de negócio, o Vigia se comporta exatamente como antes.
d_velho = V.diagnosticar({"status": "failed", "error": "x",
                          "created_at": "2020-01-01T00:00:00+00:00",
                          "started_at": "2020-01-01T00:00:00+00:00",
                          "params": {"placa": "QAB1A91",
                                     "dano": {"peca": "vidro de porta"}},
                          "evidence": {}})
check("CONTROLE: job sem `vidros_estado` cai no ramo antigo",
      d_velho and d_velho["motivo"] == "falhou_e_ninguem_soube", d_velho)
check("CONTROLE: e o Vigia continua quieto quando ja avisaram",
      V.diagnosticar({"status": "failed",
                      "evidence": {"vigia_avisou_em": "2026-01-01"}}) is None)
check("CONTROLE: e quando a tool ja entregou",
      V.diagnosticar({"status": "done", "created_at": "2020-01-01T00:00:00+00:00",
                      "evidence": {"entregue_ao_agente": True}}) is None)

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)

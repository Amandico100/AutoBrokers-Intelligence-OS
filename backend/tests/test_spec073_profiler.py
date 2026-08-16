# -*- coding: utf-8 -*-
"""SPEC-073 Bloco D/H — o profiler observa sem vazar, e o redator e um so.

A matriz de mutacoes prova que os guardas REPROVAM. Este arquivo prova o
comportamento unitario que ela nao cobre: normalizacao de path, classificacao
de origem, assinatura de tela, deteccao de candidato e os casos-limite do
redator (linha digitavel, JWT, profundidade, forma).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from portal_worker import redaction as R  # noqa: E402
from portal_worker.profiler import (      # noqa: E402
    MAX_EVENTOS_TRACE, PortalProfiler, classificar_drift, classificar_origem,
    normalizar_path, screen_fingerprint)

PASS = FAIL = 0


def check(nome, condicao, extra=""):
    global PASS, FAIL
    if condicao:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:220] if extra else ""))


# ==========================================================================
print("\n[1] NORMALIZACAO DE PATH — duas visitas a mesma tela tem uma assinatura")
# ==========================================================================
check("uuid vira placeholder",
      normalizar_path("/app/9f2a1c04-1111-2222-3333-444455556666/passo5")
      == "/app/{uuid}/passo5")
check("hash longo vira placeholder",
      "{hash}" in normalizar_path("/x/a1b2c3d4e5f6a7b8c9d0/y"))
check("id SOLTO no segmento vira {n}", normalizar_path("/pedidos/12345") == "/pedidos/{n}")
# 🔴 A primeira versao deste teste esperava `/passo12` -> `/passo{n}` e ficou
# vermelha. A expectativa e que estava errada: `passo5` e `passo6` sao telas
# DIFERENTES do portal de vidros, com perguntas diferentes. Achatar o numero do
# passo faria o detector de drift dizer "nada mudou" enquanto o robo atravessa o
# fluxo inteiro. Numero colado em palavra IDENTIFICA a tela; numero sozinho e id
# de registro.
check("numero colado em palavra NAO e achatado (identifica a tela)",
      normalizar_path("/passo12") == "/passo12")
check("CONTROLE: dois passos diferentes continuam diferentes",
      normalizar_path("/passo5") != normalizar_path("/passo6"))
check("path vazio vira /", normalizar_path("") == "/")
check("CONTROLE: dois paths REALMENTE diferentes continuam diferentes",
      normalizar_path("/cobranca/lista") != normalizar_path("/cobranca/detalhe"))
check("CONTROLE: mesma tela com uuid diferente da o MESMO path",
      normalizar_path("/app/aaaaaaaa-1111-2222-3333-444444444444/p")
      == normalizar_path("/app/bbbbbbbb-5555-6666-7777-888888888888/p"))

# ==========================================================================
print("\n[2] ORIGEM — o candidato de API nao pode vir afogado em analytics")
# ==========================================================================
casos = [
    ("app.maxpar.com.br", "maxpar.com.br", "xhr", "first_party"),
    ("maxpar.com.br", "maxpar.com.br", "fetch", "first_party"),
    ("www.google-analytics.com", "maxpar.com.br", "xhr", "telemetry"),
    ("cdn.maxpar.com.br", "maxpar.com.br", "image", "asset"),
    ("outra-empresa.com", "maxpar.com.br", "xhr", "third_party"),
    ("", "maxpar.com.br", "xhr", "unknown"),
]
for host, portal, rt, esperado in casos:
    check(f"{host or '(vazio)'} -> {esperado}",
          classificar_origem(host, portal, rt) == esperado,
          classificar_origem(host, portal, rt))
check("CONTROLE: telemetria vence 'mesma casa' (hotjar no dominio do portal)",
      classificar_origem("hotjar.maxpar.com.br", "maxpar.com.br", "xhr") == "telemetry")

# ==========================================================================
print("\n[3] ASSINATURA DE TELA — id dinamico nao pode dominar o hash")
# ==========================================================================
a = {"url": "https://x/passo1", "heading": "Dados do veiculo",
     "inputs": [{"label": "CPF"}, {"label": "input_3"}],
     "buttons": [{"text": "Avancar"}]}
b = {"url": "https://x/passo1", "heading": "Dados do veiculo",
     "inputs": [{"label": "CPF"}, {"label": "input_97"}],
     "buttons": [{"text": "Avancar"}]}
c = {"url": "https://x/passo1", "heading": "Dados do veiculo",
     "inputs": [{"label": "CPF"}, {"label": "Placa"}],
     "buttons": [{"text": "Avancar"}]}
check("id gerado diferente NAO muda a assinatura", screen_fingerprint(a) == screen_fingerprint(b))
check("CONTROLE: campo NOVO de verdade MUDA a assinatura",
      screen_fingerprint(a) != screen_fingerprint(c))
check("tela sem nada devolve assinatura vazia", screen_fingerprint({}) == "")
check("drift sem referencia e 'unknown'", classificar_drift("abc", "") == "unknown")
check("assinaturas iguais -> drift none", classificar_drift("abc", "abc") == "none")
check("assinaturas diferentes -> drift semantic", classificar_drift("abc", "xyz") == "semantic")

# ==========================================================================
print("\n[4] CANDIDATO DE API — conservador, e nunca 'aprovado'")
# ==========================================================================
p = PortalProfiler(portal_key="v", host_portal="portal.com.br")
p.registrar_response(url="https://portal.com.br/questionarios/perguntas", method="POST",
                     status=200, content_type="application/json", resource_type="xhr")
p.registrar_response(url="https://portal.com.br/questionarios/perguntas", method="POST",
                     status=204, content_type="application/json", resource_type="xhr")
p.registrar_response(url="https://portal.com.br/boleto.pdf", method="GET",
                     status=200, content_type="application/pdf", resource_type="fetch")
p.registrar_response(url="https://portal.com.br/erro", method="GET",
                     status=500, content_type="application/json", resource_type="xhr")
p.registrar_response(url="https://www.google-analytics.com/c", method="POST",
                     status=200, content_type="application/json", resource_type="xhr")
cands = p.candidatos_de_api()
paths = [c["path"] for c in cands]
check("endpoint JSON de primeira parte vira candidato", "/questionarios/perguntas" in paths)
check("PDF de primeira parte vira candidato", "/boleto.pdf" in paths)
check("erro 500 NAO vira candidato", "/erro" not in paths, paths)
check("telemetria nem entra na lista de requests",
      all("google-analytics" not in (r.get("host") or "") for r in p.requests))
check("chamada repetida conta vezes, nao duplica",
      next(c for c in cands if c["path"] == "/questionarios/perguntas")["vezes"] == 2)
check("todo candidato nasce como `candidate`, nunca `approved`",
      all(c["confidence"] == "candidate" for c in cands))

# ==========================================================================
print("\n[5] TRACE — teto, truncagem e nada de corpo")
# ==========================================================================
p2 = PortalProfiler(portal_key="v", host_portal="p.com")
for i in range(MAX_EVENTOS_TRACE + 25):
    p2.evento(layer="dom", action="fill", target=f"campo_{i}")
check(f"o trace para no teto de {MAX_EVENTOS_TRACE}", len(p2.eventos) == MAX_EVENTOS_TRACE)
check("o que passou do teto e CONTADO, nao silenciado",
      p2.resumo()["trace_truncated"] == 25, p2.resumo()["trace_truncated"])
p2.evento(layer="dom", valor="x" * 900)
check("string longa e truncada", all(len(str(v)) <= 220 for e in p2.eventos for v in e.values()))

p3 = PortalProfiler(portal_key="v", host_portal="p.com", habilitado=False)
p3.evento(layer="dom", action="x")
check("profiler desligado nao registra nada", p3.eventos == [])
check("profiler desligado devolve resumo honesto", p3.resumo() == {"enabled": False})

# ==========================================================================
print("\n[6] O REDATOR — casos-limite que a armadilha simples nao pega")
# ==========================================================================
check("linha digitavel de boleto e mascarada",
      "<redacted:linha_digitavel>" in R.redigir_texto(
          "34191790010104351004791020150008291070026000000"))
check("JWT e mascarado",
      "eyJ" not in R.redigir_texto("token eyJhbGciOiJIUzI1NiJ9.YWJjZGVm.c2lnbmF0dXJl"))
check("cartao e mascarado", "4111" not in R.redigir_texto("4111 1111 1111 1111"))
check("CONTROLE: texto inocente NAO e mascarado",
      R.redigir_texto("o boleto venceu ontem") == "o boleto venceu ontem")
check("CONTROLE: numero curto nao vira PII",
      R.redigir_texto("parcela 3 de 10") == "parcela 3 de 10")

check("chave sensivel perde o VALOR e mantem o NOME",
      R.redigir({"Authorization": "Bearer x"}) == {"Authorization": "<redacted:authorization>"})
check("chave sensivel e reconhecida em qualquer caixa",
      R.chave_e_sensivel("X-Proxy-Authorization") and R.chave_e_sensivel("SENHA"))
check("chave inocente passa", not R.chave_e_sensivel("content-type"))

fundo: dict = {"cpf": "123.456.789-01"}
for _ in range(20):                      # bem mais fundo que o teto de 12
    fundo = {"n": fundo}
check("profundidade patologica nao derruba o redator",
      isinstance(R.redigir(fundo), dict))
check("CONTROLE: em profundidade normal ele AINDA mascara",
      not R.tem_vazamento(R.redigir({"a": {"b": {"cpf": "123.456.789-01"}}})))

check("hash permite comparar sem revelar",
      R.redigir_texto("123.456.789-01", com_hash=True)
      == R.redigir_texto("123.456.789-01", com_hash=True))
check("CONTROLE: valores diferentes dao hashes diferentes",
      R.redigir_texto("123.456.789-01", com_hash=True)
      != R.redigir_texto("987.654.321-00", com_hash=True))

check("shape_of descreve array com tamanho",
      R.shape_of({"itens": [1, 2, 3]})["itens"]["__array__"] == 3)
check("shape_of nao devolve um dado real",
      not R.tem_vazamento(R.shape_of({"cpf": "12345678901", "placa": "QAB1A91"})))

check("linha_de_log nunca imprime PII",
      "123.456.789-01" not in R.linha_de_log(job="1", cpf="123.456.789-01"))
check("CONTROLE: linha_de_log imprime o que e seguro",
      "portal=mapfre_corretor" in R.linha_de_log(portal="mapfre_corretor"))

print("\n" + "=" * 66)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 66)
sys.exit(1 if FAIL else 0)

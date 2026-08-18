# -*- coding: utf-8 -*-
"""Os cruzamentos comerciais — SPEC-081 Bloco B. Tudo puro, zero rede.

Este arquivo guarda TRES coisas que, se quebrarem, produzem um relatorio que
PARECE certo:

1. **O teste do triplo.** 📊 A media e de 3 produtores por apolice. Contar a
   mesma apolice duas vezes infla o faturamento em silencio.
2. **A cobertura declarada.** 📊 19,4% das apolices de 2025 nao tem produtor.
   Um relatorio que soma 80,6% e se diz "o ano inteiro" mente por omissao.
3. **O entendedor de periodo NUNCA levanta.** O Founder vai digitar isso na
   frente de gente. Relatorio que responde "nao entendi, qual periodo?" no
   meio de uma apresentacao e pior que relatorio do periodo errado.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:300] if extra else ""))


_spec = importlib.util.spec_from_file_location(
    "calculos_isolado",
    os.path.join(RAIZ, "app", "services", "comercial", "calculos.py"))
C = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = C
_spec.loader.exec_module(C)

HOJE = date(2026, 8, 18)  # relogio fixo: teste com data de hoje muda de humor


@dataclass(frozen=True)
class Ap:
    nosnum: str
    premio: float
    comissao: float
    seguradora: str = "Allianz"
    ramo: str = "AUTO"
    inivig: str = "2025-03-14"
    e_renovacao: bool = False


@dataclass(frozen=True)
class Pr:
    nome: str
    repasse: float = 0.0


@dataclass(frozen=True)
class Ve:
    nosnum: str
    premio: float
    dias_a_vencer: int
    produtor: str


# ==========================================================================
print("\n[1] O ranking, e o TESTE DO TRIPLO")
# ==========================================================================

apolices = [Ap("1", 10000, 1500), Ap("2", 5000, 500), Ap("3", 20000, 3000)]
mapa = {"1": Pr("ANA", 75), "2": Pr("BRUNO", 250), "3": Pr("ANA", 90)}

r = C.ranking_por_produtor(apolices, mapa)
check("agrupa por produtor", len(r) == 2, [x.nome for x in r])
check("ordena por comissao, maior primeiro", r[0].nome == "ANA", r[0].nome)
check("soma a comissao certa", r[0].comissao == 4500, r[0].comissao)
check("conta as apolices certas", r[0].apolices == 2, r[0].apolices)
check("o ticket e comissao/apolices", r[0].ticket == 2250, r[0].ticket)
check("o custo de aquisicao e repasse/comissao em %",
      abs(r[0].custo_de_aquisicao - (100 * 165 / 4500)) < 0.01,
      r[0].custo_de_aquisicao)

# 🔴 O TESTE DO TRIPLO. Se a mesma apolice entrar duas vezes, o total infla.
r2 = C.ranking_por_produtor(apolices + [apolices[0], apolices[0]], mapa)
check("apolice repetida na entrada NAO conta duas vezes",
      sum(x.comissao for x in r2) == sum(x.comissao for x in r),
      f"{sum(x.comissao for x in r2)} vs {sum(x.comissao for x in r)}")

# CONTROLE: o de-duplicador nao pode estar comendo apolices legitimas.
check("CONTROLE: apolices DIFERENTES continuam somando",
      sum(x.comissao for x in r) == 5000, sum(x.comissao for x in r))

check("apolice sem produtor no mapa fica FORA do ranking",
      sum(x.apolices for x in C.ranking_por_produtor(
          apolices + [Ap("9", 1000, 100)], mapa)) == 3)
check("produtor com nome vazio nao vira linha fantasma",
      len(C.ranking_por_produtor([Ap("7", 1, 1)], {"7": Pr("   ")})) == 0)
check("o teto corta a lista", len(C.ranking_por_produtor(apolices, mapa, teto=1)) == 1)
check("CONTROLE: sem teto, nao corta", len(C.ranking_por_produtor(apolices, mapa)) == 2)
check("lista vazia devolve lista vazia, nao explode",
      C.ranking_por_produtor([], {}) == [])
check("comissao ZERO nao divide por zero no ticket",
      C.LinhaDoRanking("X", 0, 0, 0, 0).ticket == 0.0)
check("comissao ZERO nao divide por zero no custo",
      C.LinhaDoRanking("X", 1, 0, 0, 5).custo_de_aquisicao == 0.0)

# ==========================================================================
print("\n[2] A cobertura vai DECLARADA")
# ==========================================================================

cob = C.cobertura(apolices + [Ap("9", 1000, 100)], mapa)
check("conta o total certo", cob.apolices_total == 4, cob.apolices_total)
check("conta as cobertas certo", cob.apolices_com_produtor == 3)
check("o percentual de apolices bate", abs(cob.pct_apolices - 75.0) < 0.01)
check("o percentual de COMISSAO e diferente do de apolices",
      abs(cob.pct_comissao - 75.0) > 1.0,
      "as apolices cobertas costumam ser as maiores — os dois numeros nao sao o mesmo")
frase = cob.frase()
check("a frase traz os dois numeros", "3 das 4" in frase and "%" in frase, frase)
check("CONTROLE: a frase nao e um texto fixo — muda com o dado",
      C.cobertura(apolices, mapa).frase() != frase)
check("cobertura de lista vazia nao divide por zero",
      C.cobertura([], {}).pct_apolices == 0.0)

# ==========================================================================
print("\n[3] As dimensoes, e a seguradora suja")
# ==========================================================================
#
# 📊 A base tem Allianz / allianz / ALLIANZ / Allianz Seguros contando
# separado. Rosca com a mesma seguradora em quatro fatias e defeito.

sujo = [Ap("1", 1, 100, seguradora="Allianz"), Ap("2", 1, 200, seguradora="allianz"),
        Ap("3", 1, 300, seguradora="ALLIANZ"), Ap("4", 1, 50, seguradora="Porto")]
d = C.por_dimensao(sujo, "seguradora")
check("as tres grafias de Allianz viram UMA fatia", len(d) == 2, d)
check("e a fatia soma as tres", d[0][2] == 600, d[0])
check("o rotulo exibido preserva a primeira grafia vista", d[0][0] == "Allianz", d[0][0])
check("CONTROLE: seguradora DIFERENTE continua separada",
      any(x[0] == "Porto" for x in d))
# A assercao original procurava "nao informado" SEM acento e ficou vermelha:
# a normalizacao so vale para a CHAVE de agrupamento; o rotulo exibido
# preserva o acento, que e o certo. O teste e que estava errado.
_vazio = C.por_dimensao([Ap("1", 1, 1, seguradora="")], "seguradora")
check("campo vazio vira um rotulo visivel, nao some",
      len(_vazio) == 1 and "informado" in _vazio[0][0], _vazio)
check("CONTROLE: e o rotulo sai com acento, como se exibe",
      _vazio[0][0] == "(não informado)", _vazio[0][0])

# ==========================================================================
print("\n[4] Novo x renovacao, serie e projecao")
# ==========================================================================

mistura = [Ap("1", 1, 100), Ap("2", 1, 200, e_renovacao=True),
           Ap("3", 1, 300, e_renovacao=True)]
nr = C.novo_versus_renovacao(mistura)
check("separa novo de renovacao", nr["novo"] == (1, 100.0) and nr["renovacao"] == (2, 500.0), nr)

serie = C.serie_mensal([Ap("1", 1, 100, inivig="2025-01-10"),
                        Ap("2", 1, 200, inivig="2025-02-05"),
                        Ap("3", 1, 300, inivig="05/03/2025")])
check("a serie tem tres meses", len(serie) == 3, serie)
check("aceita data ISO e data brasileira na mesma serie",
      serie[2][0] == "2025-03", serie)
check("a serie sai em ordem cronologica", [x[0] for x in serie] == sorted(x[0] for x in serie))

# 🔴 A projecao DESCARTA o ultimo mes — mes em curso e parcial.
proj = C.projetar([("2025-01", 1, 100.0), ("2025-02", 1, 100.0),
                   ("2025-03", 1, 10.0)], 12)
check("a projecao ignora o mes em curso (parcial)", abs(proj - 1200.0) < 0.01, proj)
check("CONTROLE: com menos de tres meses NAO projeta (adivinhacao com cara de numero)",
      C.projetar([("2025-01", 1, 100.0), ("2025-02", 1, 100.0)], 12) == 0.0)

comp = C.comparar([Ap("1", 100, 10)], [Ap("2", 50, 5)])
check("a variacao percentual bate", abs(comp["comissao_delta_pct"] - 100.0) < 0.01)
check("CONTROLE: periodo anterior ZERO nao vira infinito",
      C.comparar([Ap("1", 100, 10)], [])["comissao_delta_pct"] == 0.0)

# ==========================================================================
print("\n[5] O Radar POR VENDEDOR — o pedido explicito do Founder")
# ==========================================================================

venc = [Ve("1", 10000, 5, "ANA"), Ve("2", 90000, 80, "BRUNO"),
        Ve("3", 20000, 12, "ANA")]
pv = C.por_vendedor_no_radar(venc)
check("agrupa os vencimentos por vendedor", len(pv) == 2, pv)
check("ordena por premio em jogo", pv[0][0] == "BRUNO", pv[0])
check("soma o premio do vendedor", pv[1][2] == 30000, pv[1])
check("guarda o vencimento MAIS PROXIMO do vendedor", pv[1][3] == 5, pv[1])
check("vencimento sem produtor vira '(sem produtor)', nao some",
      any("sem produtor" in x[0] for x in C.por_vendedor_no_radar([Ve("9", 1, 1, "")])))

faixas = C.faixas_de_urgencia(venc + [Ve("4", 500, -30, "ANA")])
check("as faixas incluem VENCIDAS quando existem",
      any(f[0] == "vencidas" for f in faixas), faixas)
check("CONTROLE: faixa sem apolice nao aparece (linha vazia e ruido)",
      all(f[1] > 0 for f in faixas), faixas)
check("a ordem das faixas e cronologica",
      [f[0] for f in faixas][0] == "vencidas", faixas)

# ==========================================================================
print("\n[6] Entender o periodo — e NUNCA levantar")
# ==========================================================================

casos = [
    ("2025", date(2025, 1, 1), date(2025, 12, 31)),
    ("me faz o raio-x comercial de 2025", date(2025, 1, 1), date(2025, 12, 31)),
    ("ano passado", date(2025, 1, 1), date(2025, 12, 31)),
    ("este ano", date(2026, 1, 1), HOJE),
    ("primeiro semestre", date(2026, 1, 1), date(2026, 6, 30)),
    ("primeiro semestre de 2025", date(2025, 1, 1), date(2025, 6, 30)),
    ("3o trimestre", date(2026, 7, 1), date(2026, 9, 30)),
    ("terceiro trimestre de 2025", date(2025, 7, 1), date(2025, 9, 30)),
    ("agosto", date(2026, 8, 1), date(2026, 8, 31)),
    ("agosto de 2025", date(2025, 8, 1), date(2025, 8, 31)),
    ("mes passado", date(2026, 7, 1), date(2026, 7, 31)),
    ("proximos 90 dias", HOJE, date(2026, 11, 16)),
    ("o que vence nos proximos 60 dias", HOJE, date(2026, 10, 17)),
    ("ultimos 12 meses", date(2025, 8, 18), HOJE),
    ("de 01/03/2026 a 30/06/2026", date(2026, 3, 1), date(2026, 6, 30)),
]
for texto, ini, fim in casos:
    p = C.entender_periodo(texto, hoje=HOJE)
    check(f"{texto!r} -> {ini} a {fim}", p.inicio == ini and p.fim == fim,
          f"veio {p.inicio} a {p.fim}")

# 🔴 A GARANTIA DE PALCO: nunca levanta, nunca devolve pergunta.
LIXO = ["", "   ", "asdkjhasd", "relatorio", "me faz aquele negocio",
        "de 99/99/9999 a 88/88/8888", "trimestre 9", "2099", None,
        "raio-x", "31/02/2025", "ultimos 0 dias", "ano que vem"]
for t in LIXO:
    try:
        p = C.entender_periodo(t, hoje=HOJE)
        ok = isinstance(p.inicio, date) and isinstance(p.fim, date) and p.inicio <= p.fim
    except Exception as e:  # noqa: BLE001
        ok = False
        p = None
    check(f"lixo {str(t)[:24]!r} devolve periodo valido, nunca levanta", ok,
          "no palco, pergunta de volta e pior que periodo errado")

check("sem texto, marca que caiu no padrao (a capa avisa)",
      C.entender_periodo("", hoje=HOJE).e_padrao is True)
check("CONTROLE: com texto entendido, NAO marca padrao",
      C.entender_periodo("2025", hoje=HOJE).e_padrao is False)
check("o padrao do RADAR olha para o FUTURO",
      C.entender_periodo("", hoje=HOJE, padrao_dias_futuro=90).fim > HOJE)
check("o padrao do RAIO-X olha para TRAS",
      C.entender_periodo("", hoje=HOJE).fim <= HOJE)

# O periodo anterior, para a comparacao.
ant = C.entender_periodo("2025", hoje=HOJE).anterior()
check("o ano anterior a 2025 e o ANO CIVIL de 2024, nao 365 dias atras",
      ant.inicio == date(2024, 1, 1) and ant.fim == date(2024, 12, 31), ant)
livre = C.Periodo(date(2026, 3, 1), date(2026, 3, 31), "mar").anterior()
check("periodo livre desloca pela MESMA duracao",
      livre.fim == date(2026, 2, 28) and livre.dias == 31, f"{livre.inicio}..{livre.fim}")

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)

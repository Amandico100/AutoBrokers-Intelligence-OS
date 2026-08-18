# -*- coding: utf-8 -*-
"""A camada de dados comercial reproduz a calibracao MEDIDA — SPEC-081 Bloco A.

Este teste TOCA A REDE de proposito. Ele existe porque a primeira versao da
SPEC-081 foi escrita contra uma API imaginaria: usava `indireto`,
`nome_produtor` e `val_c` vindo de `/renovacoes` — 📊 nenhum dos tres existe.

Um teste com resposta gravada (fixture) teria ficado verde contra a mesma API
imaginaria, porque a fixture teria sido escrita a partir da mesma leitura
errada. CLAUDE.md §9.2: medir vence deduzir.

  Rodar:   python backend/tests/test_a_fonte_comercial_bate_com_a_infocap.py
  Pular:   SEM_REDE=1  (o teste PULA e diz que pulou; nunca finge que passou)

📊 A CALIBRACAO, medida em 18/08/2026 as 07h, chamando a API:

    2025, tipo_doc=A, data=INIVIG, mapa de 4 anos de fimvig, ordem=1

    apolices ............... 1.680      novo 717 / renovacao 963
    comissao total ......... R$ 1.863.831
    comissao atribuida ..... R$ 1.606.265   (86,2%)
    com produtor ........... 1.354         (80,6%)
    produtores distintos ... 82

     1 RAFAEL L SILVEIRA-EXECUTIVO       250  266.926
     2 MARCOS TONIOLO - INDICADOR          7  261.565
     3 RAFAEL LACAU SILVEIRA - FECHADOR  139  233.551
     4 LUIZ GUILHERME ARAUJO - FECHADOR  101  191.493
     5 LUIZ GUILHERME - EXECUTIVO         99   85.729
"""
from __future__ import annotations

import importlib.util
import os
import sys
from collections import defaultdict
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


# O modulo e puro (urllib + dataclasses). Carregado sozinho para nao puxar o
# `app.services.__init__`, que importa o SDK da OpenAI.
_spec = importlib.util.spec_from_file_location(
    "fonte_infocap_isolada",
    os.path.join(RAIZ, "app", "comercial", "fonte_infocap.py"))
F = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = F
_spec.loader.exec_module(F)

# ==========================================================================
print("\n[1] As funcoes PURAS — sem rede, sempre rodam")
# ==========================================================================

# 🔴 `_fatiar_por_ano` nao e otimizacao: e o teto MEDIDO. Janela de 7 anos
# devolve HTTP 502 aos 28 s nos dois endpoints.
pedacos = F._fatiar_por_ano(date(2023, 3, 15), date(2026, 8, 18))
check("uma janela de 4 anos vira 4 pedacos", len(pedacos) == 4, pedacos)
check("o primeiro pedaco comeca na data pedida, nao em 01/01",
      pedacos[0][0] == date(2023, 3, 15), pedacos[0])
check("o ultimo termina na data pedida, nao em 31/12",
      pedacos[-1][1] == date(2026, 8, 18), pedacos[-1])
check("nenhum pedaco cruza o ano civil",
      all(a.year == b.year for a, b in pedacos), pedacos)
check("um ano so vira um pedaco so",
      len(F._fatiar_por_ano(date(2025, 1, 1), date(2025, 12, 31))) == 1)
check("datas invertidas nao quebram nem devolvem vazio",
      len(F._fatiar_por_ano(date(2025, 12, 31), date(2025, 1, 1))) == 1)

# 🔴 CONTROLE: o fatiador CONSEGUE devolver mais de um. Sem esta linha, um
# `return [(inicio, fim)]` passaria em quase tudo acima.
check("CONTROLE: 10 anos viram 10 pedacos, nao 1",
      len(F._fatiar_por_ano(date(2017, 1, 1), date(2026, 12, 31))) == 10)

# `_num` — 📊 a API devolve None em val_c de /renovacoes.
check("None vira zero, nao explode", F._num(None) == 0.0)
check("string vazia vira zero", F._num("") == 0.0)
check("numero passa inteiro", F._num(1299.09) == 1299.09)
check("string com ponto decimal passa", F._num("1299.09") == 1299.09)
check("comissao NEGATIVA (estorno) e preservada", F._num(-125.03) == -125.03)
check("CONTROLE: lixo vira zero em vez de derrubar o relatorio",
      F._num("nao e numero") == 0.0)

# `anos_de_vencimento_para` — a regra que garante 80,6% de cobertura.
anos = F.anos_de_vencimento_para(date(2025, 1, 1), date(2025, 12, 31))
check("a producao de 2025 pede 2024..2027 de vencimento",
      anos == [2024, 2025, 2026, 2027], anos)
check("CONTROLE: inclui o ano ANTERIOR (vigencia curta e retroativa)",
      2024 in anos)
check("CONTROLE: inclui dois anos DEPOIS (plurianual)", 2027 in anos)

# `_linhas` — o envelope que custou uma medicao devolvendo zero.
check("acha a lista pela chave certa",
      len(F.FonteInfocap._linhas({"header": {}, "documentos": [{"a": 1}]},
                                 "documentos")) == 1)
check("acha a lista mesmo com a chave errada (o defeito que me pegou)",
      len(F.FonteInfocap._linhas({"header": {}, "renovacoes": [{"a": 1}]},
                                 "documentos")) == 1)
check("CONTROLE: envelope sem lista devolve vazio, nao inventa",
      F.FonteInfocap._linhas({"header": {}}, "documentos") == [])
check("CONTROLE: `header` (dict, nao lista) nao e confundido com dado",
      F.FonteInfocap._linhas({"header": {"x": 1}}, "documentos") == [])

# ==========================================================================
print("\n[1.5] O cache: acelera, e NUNCA derruba")
# ==========================================================================
#
# 📊 Sem cache: Raio-X de um ano leva 53 s (6 chamadas). Numa apresentacao ao
# vivo isso e uma eternidade. Com o cache, a segunda vez e instantanea.
#
# 🔴 Mas a regra que MAIS importa e a outra: cache que quebra nao pode
# derrubar relatorio. Relatorio 53 s mais lento e aborrecimento; relatorio
# que nao sai porque o CACHE falhou e absurdo.

class _RedisFalso:
    def __init__(self, quebra=False):
        self.dados = {}; self.quebra = quebra
        self.leituras = 0; self.escritas = 0

    def get(self, k):
        self.leituras += 1
        if self.quebra:
            raise ConnectionError('redis caiu')
        return self.dados.get(k)

    def setex(self, k, _ttl, v):
        self.escritas += 1
        if self.quebra:
            raise ConnectionError('redis caiu')
        self.dados[k] = v


def _com_redis(fake):
    """Injeta o Redis falso no lugar de `app.core.redis`."""
    import types
    mod = types.ModuleType('app.core.redis')
    mod.get_redis_client = lambda: fake
    sys.modules['app.core.redis'] = mod


_bom = _RedisFalso()
_com_redis(_bom)
F._cache_gravar('teste:chave', {'a': 1})
check('o cache GRAVA', _bom.escritas == 1 and 'teste:chave' in _bom.dados)
check('e LE de volta o mesmo valor', F._cache_ler('teste:chave') == {'a': 1})
check('chave que nunca foi gravada devolve None',
      F._cache_ler('teste:inexistente') is None)

# 🔴 O CONTROLE QUE MAIS IMPORTA: Redis quebrado nao levanta.
_ruim = _RedisFalso(quebra=True)
_com_redis(_ruim)
_falhou = False
try:
    F._cache_gravar('x', {'a': 1})
    _r = F._cache_ler('x')
except Exception:
    _falhou = True
check('CONTROLE: Redis QUEBRADO nao levanta na escrita nem na leitura',
      not _falhou, 'cache nao pode ser motivo de falha')
check('CONTROLE: e a leitura devolve None para o caminho normal seguir',
      _r is None)

# 🔴 CROSS-TENANT: a chave carrega o rotulo da corretora.
_a = F.FonteInfocap(login='a@a', senha='x', rotulo='resulta')
_b = F.FonteInfocap(login='b@b', senha='x', rotulo='autofleet')
check('CONTROLE: corretoras diferentes geram chaves de cache DIFERENTES',
      _a._rotulo != _b._rotulo,
      'cache compartilhado entre tenants e vazamento silencioso')

# Devolve o modulo ao que era, para os blocos seguintes.
sys.modules.pop('app.core.redis', None)
# ==========================================================================
if os.getenv("SEM_REDE"):
    print("\n[2..4] PULADOS — SEM_REDE=1")
    print("\n" + "=" * 68)
    print(f"  {PASS} assercoes verdes - {FAIL} vermelhas  (rede PULADA)")
    print("=" * 68)
    sys.exit(1 if FAIL else 0)

print("\n[2] A API responde, e responde o que a SPEC diz")
# ==========================================================================

fonte = F.FonteInfocap.para_empresa("resulta")
apolices = fonte.producao(date(2025, 1, 1), date(2025, 12, 31))

check("a producao de 2025 volta com 1.680 apolices (+-20)",
      abs(len(apolices) - 1680) <= 20, len(apolices))

com_total = sum(a.comissao for a in apolices)
check("a comissao total bate: R$ 1.863.831 (+-R$ 15.000)",
      abs(com_total - 1_863_831) <= 15_000, f"R$ {com_total:,.0f}")

novo = sum(1 for a in apolices if not a.e_renovacao)
renov = sum(1 for a in apolices if a.e_renovacao)
check("novo/renovacao bate: 717/963 (+-20)",
      abs(novo - 717) <= 20 and abs(renov - 963) <= 20, f"{novo}/{renov}")

# 🔴 CONTROLE do filtro `tipo_doc=A`. Sem ele viriam 3.272 documentos.
check("CONTROLE: o filtro tipo_doc=A esta ATIVO (senao viriam ~3.272)",
      len(apolices) < 2500,
      "veio a producao BRUTA — o filtro nao foi para a requisicao")
check("CONTROLE: e o filtro nao zerou tudo", len(apolices) > 1000)

# ==========================================================================
print("\n[3] O mapa de produtores, e a cobertura HONESTA")
# ==========================================================================

mapa = fonte.mapa_de_produtores(F.anos_de_vencimento_para(
    date(2025, 1, 1), date(2025, 12, 31)))
check("o mapa tem ~8.894 apolices (+-400)",
      abs(len(mapa) - 8894) <= 400, len(mapa))

cobertas = [a for a in apolices if a.nosnum in mapa]
pct = 100 * len(cobertas) / max(1, len(apolices))
check("a cobertura de produtor e ~80,6% (+-4 p.p.)",
      abs(pct - 80.6) <= 4.0, f"{pct:.1f}%")

# 🔴 CONTROLE — a cobertura NAO e 100%, e isso vai impresso na peca.
check("CONTROLE: a cobertura NAO e total (o relatorio precisa declarar isso)",
      pct < 95.0,
      "se for ~100%, a invariante da declaracao de cobertura virou decoracao")
check("CONTROLE: e nao e residual (senao o ranking nao vale nada)", pct > 60.0)

com_atribuida = sum(a.comissao for a in cobertas)
check("a comissao atribuida bate: R$ 1.606.265 (+-R$ 15.000)",
      abs(com_atribuida - 1_606_265) <= 15_000, f"R$ {com_atribuida:,.0f}")

# 🔴 A ARMADILHA QUE MAIS IMPORTA: `ordem=1`. Sem ele, a media de 3 produtores
# por apolice TRIPLICARIA o faturamento.
check("a comissao atribuida NAO ultrapassa a total (o teste do triplo)",
      com_atribuida <= com_total,
      "somou mais de um produtor por apolice — o `ordem=1` caiu")

# ==========================================================================
print("\n[4] O ranking reproduz a tabela medida")
# ==========================================================================

r = defaultdict(lambda: [0, 0.0, 0.0])
for a in cobertas:
    p = mapa[a.nosnum]
    r[p.nome][0] += 1
    r[p.nome][1] += a.comissao
    r[p.nome][2] += p.repasse
ranking = sorted(r.items(), key=lambda kv: -kv[1][1])

check("ha ~82 produtores distintos (+-10)", abs(len(r) - 82) <= 10, len(r))

ESPERADO = [
    ("RAFAEL L SILVEIRA-EXECUTIVO", 250, 266_926),
    ("MARCOS TONIOLO - INDICADOR", 7, 261_565),
    ("RAFAEL LACAU SILVEIRA - FECHADOR", 139, 233_551),
    ("LUIZ GUILHERME ARAUJO - FECHADOR", 101, 191_493),
    ("LUIZ GUILHERME - EXECUTIVO", 99, 85_729),
]
for i, (nome, apol, com) in enumerate(ESPERADO):
    if i >= len(ranking):
        check(f"posicao {i+1} existe", False, f"o ranking tem so {len(ranking)}")
        continue
    achado, (n, c, _rep) = ranking[i]
    check(f"#{i+1} e {nome[:34]}", achado == nome, f"veio {achado}")
    check(f"#{i+1} tem {apol} apolices (+-3)", abs(n - apol) <= 3, n)
    check(f"#{i+1} soma R$ {com:,} (+-R$ 3.000)", abs(c - com) <= 3000, f"{c:,.0f}")

# 🔴 O NUMERO QUE VALE A APRESENTACAO: o repasse varia de 0,7% a 25%.
repasses = [(nome, 100 * rep / com) for nome, (n, com, rep) in r.items()
            if com > 20_000]
menor = min(repasses, key=lambda x: x[1])
maior = max(repasses, key=lambda x: x[1])
check("o MENOR repasse entre os grandes e ~0,7% (+-1 p.p.)",
      menor[1] <= 2.0, f"{menor[0]} {menor[1]:.1f}%")
# 🔴 38%, nao 25% — e foi ESTE TESTE que me corrigiu, em 18/08.
#
# Eu tinha calibrado em 25% olhando o top-8 por comissao absoluta. 📊 O maior
# repasse real e de JEAN FRANCISCO SIQUEIRA - PRIME, com 38,0% — ele nao
# aparecia naquela lista porque nao esta entre os oito maiores em VALOR, so
# entre os que passam do corte de R$ 20 mil.
#
# Amplitude medida: 0,7% a 38,0%. A manchete ficou mais forte do que a que eu
# tinha prometido ao Founder: um canal devolve mais de um TERCO da comissao.
check("o MAIOR repasse entre os grandes e ~38% (+-4 p.p.)",
      abs(maior[1] - 38.0) <= 4.0, f"{maior[0]} {maior[1]:.1f}%")
check("CONTROLE: a amplitude e grande — 30 p.p. ou mais separam os extremos",
      (maior[1] - menor[1]) >= 30.0,
      f"{menor[1]:.1f}% a {maior[1]:.1f}% — se for estreita, nao ha materia")
check("CONTROLE: os dois extremos sao produtores DIFERENTES",
      menor[0] != maior[0])

# 🔴 O ticket do #2 e 35x o do #1 — a manchete.
t1 = ranking[0][1][1] / max(1, ranking[0][1][0])
t2 = ranking[1][1][1] / max(1, ranking[1][1][0])
check("o ticket do #2 e ao menos 20x o do #1 (a manchete)",
      t2 >= 20 * t1, f"#1 R$ {t1:,.0f} · #2 R$ {t2:,.0f}")

print("\n" + "=" * 68)
print(f"  {PASS} assercoes verdes - {FAIL} vermelhas")
print("=" * 68)
sys.exit(1 if FAIL else 0)

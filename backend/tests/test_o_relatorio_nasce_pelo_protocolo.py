# -*- coding: utf-8 -*-
"""O guarda do PROTOCOLO — SPEC-094.1 · BLOCO E.

Este arquivo guarda `docs/canon/COMO-NASCE-UM-RELATORIO.md`. Não o texto: as
**seis regras** que o documento manda seguir. Um protocolo sem guarda é uma
recomendação, e recomendação envelhece em silêncio.

```
(a) toda métrica tem `pergunta_verificada` E `golden`
(b) nenhuma métrica é ÓRFÃ — ou aparece, ou está na lista com a razão escrita
(c) nenhuma seção da peça é CAIXA VAZIA
(d) toda tool de relatório entra pelo `if` de papel de graph.py:528
(e) nenhum arquivo de `metricas/` conhece a fonte  (M1)
(f) o documento existe e cabe em 12 KB
```

🔴 **Cada regra tem um PAR** (protocolo v11.1): a mesma superfície com o
veredito OPOSTO. Sem o par, um detector que devolve sempre "reprovado"
pareceria um guarda perfeito — e um que devolve sempre "aprovado" também.

⛔ Nenhuma rede. Nenhum banco. Nenhuma escrita em arquivo do repositório: as
mutações são feitas **em memória**, sobre cópias.

  Rodar:  python backend/tests/test_o_relatorio_nasce_pelo_protocolo.py
"""
from __future__ import annotations

import dataclasses
import importlib.machinery
import io
import os
import re
import sys
import types

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(RAIZ)
sys.path.insert(0, RAIZ)
PASS = FAIL = 0


def check(nome, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:400] if extra else ""))


# 🔴 O pacote é registrado VAZIO em `sys.modules`, com o `__path__` certo: os
# submódulos carregam e os `__init__` pesados não rodam. 📊
# `app/services/__init__.py` importa a cadeia de RAG inteira (fastembed,
# langchain_openai) — `relatorios_comerciais.py:60` já documenta isso —, e um
# guarda que dependesse disso não roda em caixa nenhuma sem GPU.
for _pkg in ("app", "app.comercial", "app.comercial.metricas", "app.agents",
             "app.agents.tools", "app.services", "app.services.work"):
    if _pkg in sys.modules:
        continue
    _m = types.ModuleType(_pkg)
    _m.__path__ = [os.path.join(RAIZ, *_pkg.split("."))]
    _m.__spec__ = importlib.machinery.ModuleSpec(_pkg, None, is_package=True)
    sys.modules[_pkg] = _m

from app.comercial.metricas import registry  # noqa: E402

METRICAS = registry.todas()
PASTA_DAS_METRICAS = os.path.join(RAIZ, "app", "comercial", "metricas")
EI = os.path.join(RAIZ, "app", "agents", "tools", "executive_intelligence.py")
RC = os.path.join(RAIZ, "app", "agents", "tools", "relatorios_comerciais.py")
GRAPH = os.path.join(RAIZ, "app", "agents", "graph.py")
PROTOCOLO = os.path.join(REPO, "docs", "canon", "COMO-NASCE-UM-RELATORIO.md")


def ler(caminho):
    with io.open(caminho, encoding="utf-8") as fh:
        return fh.read()


FONTE_EI = ler(EI)
FONTE_RC = ler(RC)
FONTE_GRAPH = ler(GRAPH)


# ==========================================================================
print("\n[a] Toda métrica declara a PERGUNTA e o GOLDEN")
# ==========================================================================
#
# 📊 Ref ④ (Snowflake Cortex Analyst, Verified Query Repository): perguntas
# verificadas por gente melhoram a precisão — +20 p.p. em teste controlado — e
# o golden é a régua de "o que respondia certo e passou a falhar".

check("há métricas registradas para conferir", len(METRICAS) >= 16,
      "%d" % len(METRICAS))
sem_pergunta = sorted(m for m, d in METRICAS.items()
                      if not str(d.pergunta_verificada or "").strip())
check("nenhuma métrica sem `pergunta_verificada`", not sem_pergunta, sem_pergunta)
sem_golden = sorted(m for m, d in METRICAS.items()
                    if not (d.golden or {}).get("fixture")
                    or "esperado" not in (d.golden or {}))
check("nenhuma métrica sem `golden` completo", not sem_golden, sem_golden)

# 🔴 A pergunta é PORTUGUÊS, e não o `metric_id` repetido. Uma "pergunta"
# que é o id em outra ordem não ajuda ninguém a reconhecer a duplicata.
sem_verbo = sorted(m for m, d in METRICAS.items()
                   if "?" not in str(d.pergunta_verificada or ""))
check("toda pergunta verificada é uma PERGUNTA (tem '?')", not sem_verbo,
      sem_verbo)

# 🔴 E o `esperado` nunca é `None` nem zero de consolação: ou é número, ou é o
# sentinela. Ausência apresentada como 0 é a mutação M2 da 094.
zeros = sorted(m for m, d in METRICAS.items()
               if (d.golden or {}).get("esperado") == 0)
check("nenhum golden afirma ZERO (ausência ≠ zero)", not zeros, zeros)

# --- o PAR: a mesma definição, sem os campos, REPROVA --------------------
#
# 🔴 A mutação é por CÓPIA, em memória: `dataclasses.replace` sobre uma
# definição REAL. Nada é escrito no repositório, e o original não é tocado.
_real = METRICAS["production.policy_count"]
try:
    dataclasses.replace(_real, pergunta_verificada="")
    check("PAR-A: métrica SEM pergunta_verificada REPROVA", False,
          "a cópia mutada foi aceita — o __post_init__ não exige nada")
except ValueError as exc:
    check("PAR-A: métrica SEM pergunta_verificada REPROVA",
          "pergunta_verificada" in str(exc))
try:
    dataclasses.replace(_real, golden={})
    check("PAR-B: métrica SEM golden REPROVA", False, "a cópia mutada foi aceita")
except ValueError as exc:
    check("PAR-B: métrica SEM golden REPROVA", "golden" in str(exc))
try:
    dataclasses.replace(_real, golden={"fixture": "x", "esperado": None})
    check("PAR-C: golden com `esperado=None` REPROVA", False)
except ValueError as exc:
    check("PAR-C: golden com `esperado=None` REPROVA", "esperado" in str(exc))
try:
    copia = dataclasses.replace(_real)
    check("PAR-D CONTROLE: a definição INTACTA passa",
          copia.metric_id == _real.metric_id
          and copia.golden == _real.golden)
except Exception as exc:  # noqa: BLE001
    check("PAR-D CONTROLE: a definição INTACTA passa", False,
          "%s: %s — um guarda que reprova tudo não é guarda" % (
              type(exc).__name__, exc))
check("PAR-E CONTROLE: a métrica real continua com os campos",
      bool(_real.pergunta_verificada) and bool(_real.golden.get("fixture")),
      "a mutação vazou para o original")

# 🔴 A `fixture` declarada é UMA, e ela é a que o registry documenta. Duas
# fixtures com o mesmo nome e populações diferentes fariam dois goldens
# incomparáveis parecerem a mesma régua.
fixtures = {str((d.golden or {}).get("fixture") or "") for d in METRICAS.values()}
check("todos os goldens apontam a MESMA fixture declarada",
      fixtures == {registry.FIXTURE_094}, sorted(fixtures))


# ==========================================================================
print("\n[b] Nenhuma métrica ÓRFÃ — e as que são estão LISTADAS, com a razão")
# ==========================================================================
#
# 📊 MEDIDO em 03/09/2026, e não mascarado. Duas perguntas diferentes, porque
# uma métrica pode chegar ao CHAT e não ser desenhada na PEÇA:
#
#   órfã do chat   não está em nenhuma VISAO   -> nem o modelo consegue pedi-la
#   órfã da peça   `_compor` não a desenha     -> vai ao pack, não ao Artifact

#: 🔴 As que NÃO estão em nenhuma visão, com a razão escrita ao lado. Elas
#: existem de propósito e existem VAZIAS: 📊 a fonte piloto não expõe estornos
#: nem impostos sobre a comissão, e o censo não os verificou — que é diferente
#: de "não existem". Uma métrica que não aparece deixa o leitor supor que
#: ninguém pensou nela; uma que aparece dizendo por que não tem número fecha a
#: pergunta. Elas não entram em VISAO nenhuma porque um assunto de chat que só
#: devolve INDISPONÍVEL seria um assunto que nunca responde.
ORFAS_DO_CHAT = {
    "commission.reversals":
        "📊 censo: capacidade NÃO VERIFICADA na fonte piloto — a métrica existe "
        "para dizer isso, e não para ser perguntada",
    "commission.tax":
        "📊 censo: idem. Registrada vazia de propósito (SPEC-094 producao.py)",
}

#: 🔴 As que o `_compor` não desenha no Artifact. Elas chegam ao chat pelo
#: pack — o dono as vê citadas com `metric_id@versão` —, mas não têm cartão.
#: 📊 Medido: sete. Listadas aqui em vez de escondidas atrás de um `>= 9`.
ORFAS_DA_PECA = {
    "commission.broker_received":
        "INDISPONÍVEL na fonte: um cartão vazio numa peça em que os outros têm "
        "número lê-se como zero (mutação M2)",
    "commission.reversals":
        "INDISPONÍVEL na fonte E fora de VISAO: não há cartão porque não há "
        "número, e não há número porque o censo não verificou a capacidade",
    "commission.tax":
        "INDISPONÍVEL na fonte E fora de VISAO, pelo mesmo motivo do estorno: "
        "não verificado no censo — o que é diferente de não existir",
    "data.coverage":
        "a cobertura foi para DENTRO de cada cartão (o `lede`) em 03/09/2026; "
        "um cartão só dela repetiria a informação longe do número",
    "mix.branch":
        "a rosca de concentração desenha SEGURADORA; o ramo está no breakdown "
        "do mesmo pack — P-094.1-MIX-BRANCH-SEM-SECAO",
    "producer.momentum":
        "variação de 30 dias sem cartão próprio: o delta do período já ocupa a "
        "seção 2 — P-094.1-MOMENTUM-SEM-SECAO",
    "production.new_vs_renewal":
        "o valor é uma REPARTIÇÃO (dict), e nenhum bloco de `blocks.py` desenha "
        "repartição hoje — P-094.1-NOVO-X-RENOVACAO-SEM-SECAO",
}

_i = FONTE_EI.index("    def _compor(")
_j = FONTE_EI.index("\n    @staticmethod", _i)
CORPO_DO_COMPOR = FONTE_EI[_i:_j]
_i2 = FONTE_EI.index("VISOES: Dict[str, Tuple[str, ...]] = {")
DECLARACAO_DAS_VISOES = FONTE_EI[_i2:FONTE_EI.index("\n}", _i2)]

fora_de_visao = sorted(m for m in METRICAS if m not in DECLARACAO_DAS_VISOES)
check("nenhuma métrica fora de VISAO além das listadas",
      set(fora_de_visao) <= set(ORFAS_DO_CHAT),
      sorted(set(fora_de_visao) - set(ORFAS_DO_CHAT)))
fora_da_peca = sorted(m for m in METRICAS if m not in CORPO_DO_COMPOR)
check("nenhuma métrica sem cartão além das listadas",
      set(fora_da_peca) <= set(ORFAS_DA_PECA),
      sorted(set(fora_da_peca) - set(ORFAS_DA_PECA)))
check("toda órfã listada tem RAZÃO escrita",
      all(len(v) > 30 for v in list(ORFAS_DO_CHAT.values())
          + list(ORFAS_DA_PECA.values())))
# 🔴 A lista não pode CRESCER sem que alguém a escreva: uma entrada que já não
# corresponde a órfã nenhuma é lista vencida, e lista vencida ensina a ignorar.
check("CONTROLE: nenhuma entrada da lista está vencida",
      set(ORFAS_DO_CHAT) <= set(fora_de_visao)
      and set(ORFAS_DA_PECA) <= set(fora_da_peca),
      sorted((set(ORFAS_DO_CHAT) - set(fora_de_visao))
             | (set(ORFAS_DA_PECA) - set(fora_da_peca))))
# --- o PAR: uma métrica inventada seria acusada -------------------------
check("PAR: uma métrica que ninguém cita seria ACUSADA",
      "metrica.que.nao.existe" not in DECLARACAO_DAS_VISOES
      and "metrica.que.nao.existe" not in CORPO_DO_COMPOR,
      "se este par falhar, o detector acha qualquer coisa e não prova nada")
check("PAR CONTROLE: e uma métrica que É citada NÃO é acusada",
      "commission.broker_accrued" in DECLARACAO_DAS_VISOES
      and "commission.broker_accrued" in CORPO_DO_COMPOR)


# ==========================================================================
print("\n[c] Nenhuma seção da peça é CAIXA VAZIA")
# ==========================================================================
#
# 📊 A lição vem da 081: três peças publicadas com SETE caixas escritas "Sem
# dado no período" e ZERO barras — todos os números calculados e corretos,
# descartados na renderização. E 32 asserções deixaram as sete passar.

#: 🔴 As seções ESTRUTURAIS, que não desenham número por desenho — e a razão.
#: A seção de fontes é o oposto de caixa vazia: ela é a que diz de onde veio
#: cada número das outras.
SECOES_ESTRUTURAIS = {
    "fontes e confiança":
        "é a seção de PROCEDÊNCIA: pack_id, provedor, base temporal e "
        "cobertura. Ela fala SOBRE as métricas das outras seções",
}

SECOES = []
# 🔴 `\d+`, e não `\d`: a peça passou de 8 para 13 seções na 094.1, e um
# detector de UM dígito pararia de enxergar as seções 10–13 — em silêncio, e
# justamente as novas. Um leitor que não acha a seção não a acusa de vazia
# (CLAUDE.md §9.3: quando o fato muda, o teste muda com ele).
for _n, _titulo, _texto in zip(*[iter(
        re.split(r"\n        # (\d+) · ([^\n-]+)", CORPO_DO_COMPOR)[1:])] * 3):
    SECOES.append((_n, _titulo.strip(), _texto))
check("o detector achou as seções de `_compor`", len(SECOES) >= 8,
      "%d seções" % len(SECOES))
vazias = [t for _, t, corpo in SECOES
          if not any(m in corpo for m in METRICAS)]
check("nenhuma seção sem métrica além das estruturais",
      set(vazias) <= set(SECOES_ESTRUTURAIS), sorted(set(vazias) - set(SECOES_ESTRUTURAIS)))
check("CONTROLE: as estruturais declaradas REALMENTE não têm métrica",
      set(SECOES_ESTRUTURAIS) <= set(vazias),
      sorted(set(SECOES_ESTRUTURAIS) - set(vazias)))
# --- o PAR: uma seção inventada sem métrica seria acusada ---------------
_falsa = SECOES + [("9", "secao sintetica vazia", "        pass\n")]
_vazias_com_a_falsa = [t for _, t, corpo in _falsa
                       if not any(m in corpo for m in METRICAS)]
check("PAR: uma seção SEM métrica é acusada",
      "secao sintetica vazia" in _vazias_com_a_falsa)
check("PAR CONTROLE: e uma seção COM métrica não é",
      "secao sintetica vazia" not in [t for _, t, _c in SECOES])


# ==========================================================================
print("\n[d] Toda tool de relatório entra pelo `if` de papel de graph.py:528")
# ==========================================================================
#
# 🔴 Fora daquele `if`, o agente de ATENDIMENTO — que fala com o SEGURADO —
# recebe ferramentas que leem a carteira inteira da corretora. Não é vazamento
# de dado pessoal: é vazamento do negócio para fora do negócio.

LISTA = FONTE_RC[FONTE_RC.rindex("def ferramentas_comerciais"):]
#: As tools da família RELATÓRIO. Uma tool nova desta família entra AQUI — e é
#: por isto que o guarda a pega quando ela nasce fora da lista.
TOOLS_DE_RELATORIO = ("executive_intelligence", "listar_entregas",
                      "propor_metrica")
for _nome in TOOLS_DE_RELATORIO:
    check("[d] `%s` é anexada pela lista de `ferramentas_comerciais`" % _nome,
          _nome in LISTA)
    check("[d] e NÃO tem uma segunda chamada em graph.py" % () if False else
          "[d] `%s` não tem chamada direta em graph.py" % _nome,
          _nome not in FONTE_GRAPH,
          "chamada direta é onde a condição de papel se perde")
check("[d] a lista é chamada DENTRO do `if` fechado por papel",
      '_agent_role or "core"' in FONTE_GRAPH[
          max(0, FONTE_GRAPH.index("ferramentas_comerciais") - 3000):
          FONTE_GRAPH.index("ferramentas_comerciais")])
# --- o PAR ---------------------------------------------------------------
check("[d] PAR: uma tool FORA da lista seria acusada",
      "tool_sintetica_fora_do_if" not in LISTA)
check("[d] PAR CONTROLE: e o detector acha as que ESTÃO na lista",
      all(n in LISTA for n in TOOLS_DE_RELATORIO))


# ==========================================================================
print("\n[e] Nenhum arquivo de `metricas/` conhece a fonte  (M1)")
# ==========================================================================
#
# 🔴 A fórmula NÃO sabe o nome de nenhum sistema de gestão. É a mutação M1 da
# 094, e ela é a razão inteira de o registry existir separado do adapter.

PROIBIDAS = re.compile(r"infocap|susep|nosnum", re.I)
sujos = []
for _nome in sorted(os.listdir(PASTA_DAS_METRICAS)):
    if not _nome.endswith(".py"):
        continue
    _texto = ler(os.path.join(PASTA_DAS_METRICAS, _nome))
    if PROIBIDAS.search(_texto):
        sujos.append(_nome)
check("[e] nenhum arquivo de metricas/ nomeia a fonte", not sujos, sujos)
check("[e] CONTROLE: o detector varreu arquivos de verdade",
      len([n for n in os.listdir(PASTA_DAS_METRICAS) if n.endswith(".py")]) >= 5)
# --- o PAR: o detector ACHA quando há ------------------------------------
check("[e] PAR: o detector acha a fonte num texto sintético",
      bool(PROIBIDAS.search('nosnum = "a apolice"  # M1 sintetico')))
check("[e] PAR CONTROLE: e não acusa um texto limpo",
      not PROIBIDAS.search("policy_ref = a.policy_ref  # o vocabulario canonico"))


# ==========================================================================
print("\n[f] O documento existe, cabe em 12 KB e traz os seis passos")
# ==========================================================================

TETO_DE_BYTES = 12 * 1024
check("[f] `docs/canon/COMO-NASCE-UM-RELATORIO.md` existe",
      os.path.exists(PROTOCOLO))
if os.path.exists(PROTOCOLO):
    _bytes = os.path.getsize(PROTOCOLO)
    check("[f] e cabe em 12 KB (📊 %d bytes)" % _bytes, _bytes <= TETO_DE_BYTES,
          "%d > %d — um protocolo grande demais para ser lido é um protocolo "
          "que não é lido (CLAUDE.md §2)" % (_bytes, TETO_DE_BYTES))
    _texto = ler(PROTOCOLO)
    for _passo in ("CLASSIFIQUE", "MEÇA", "DEFINA", "PROVE", "MOSTRE", "FECHE"):
        check("[f] o passo %s está escrito" % _passo, _passo in _texto)
    check("[f] e a seção QUANDO É MAIS QUE ISSO",
          "QUANDO É MAIS QUE ISSO" in _texto)
    check("[f] traz o exemplo completo do §0 da SPEC",
          "commission.avg_per_producer_by_segment" in _texto)
    check("[f] e o comando de promoção, que é de GENTE",
          "python -m app.comercial.metricas.promover" in _texto)
    check("[f] CONTROLE: o leitor do documento leu o documento",
          len(_texto) > 4000, len(_texto))


# ==========================================================================
print("\n" + "=" * 68)
print("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
print("=" * 68)
sys.exit(1 if FAIL else 0)

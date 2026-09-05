# -*- coding: utf-8 -*-
"""O CHAT FALA COMO CORRETOR -- e nunca como banco de dados. SPEC-097 U7.

===============================================================================
📊 A RAZAO, MEDIDA EM 05/09/2026 -- pelo Founder, no produto vivo
===============================================================================

Respostas do chat da corretora, coladas por ele:

    "production.new_vs_renewal@1"
    "portfolio.cancellation_rate"
    "data.coverage@1"
    "commission.broker_accrued@1"

> **Chave de banco na frente de quem compra o produto.** E o modelo nao
> inventou: `COMO_FALAR` -- a instrucao que as duas ferramentas de relatorio
> anexam a resposta -- MANDAVA *"citar `metric_id@version` ao lado de cada
> numero que voce disser"*.

🔴 A regua da SPEC-094 -- *"todo numero tem ponteiro"* -- e do **ARTIFACT**. O
ponteiro continua inteiro no `payload.evidence_pack`, no bloco citavel e no
sinal, que e onde alguem confere. O que ele nunca foi e vocabulario de conversa.

===============================================================================
O CONTRATO QUE ESTE GUARDA FIXA
===============================================================================

    [B0]  os detectores CONSEGUEM acusar -- e nao acusam fala humana
    [B1]  as instrucoes de narracao PROIBEM a chave (antes elas a EXIGIAM)
    [B2]  o CATALOGO executado (`_arun(listar_metricas=True)`) nao tem chave
    [B3]  a RECUSA de metrica (`PropostaDeMetrica.frase()`) nao tem chave
    [B4]  toda metrica registrada tem `label`, e o que se DIZ dela e portugues
          -- senao o modelo nao tem o que dizer no lugar da chave
    [B5]  o aviso da metrica que FALHOU nao tem chave
    [B6]  o resumo deterministico e a frase de direcao nao tem chave
    [B7]  a regra curta esta no prompt do chat

🔴 DE [B2] A [B6] CADA ASSERCAO EXECUTA O PRODUTO: o catalogo sai da ferramenta
de verdade, a recusa sai de `propor_a_partir_do_pedido` com o registry REAL, o
nome sai de `nome_da_metrica` sobre um `MetricResult` montado pela fabrica, e o
aviso de falha sai de `registry._isolar` com uma excecao de verdade.

⛔ A excecao e [B7]: prompt e texto, e o que se afirma ali e a FORMA da
declaracao (CLAUDE.md §9.4, a excecao escrita) -- com o par obrigatorio.

Rodar:  PYTHONIOENCODING=utf-8 python backend/tests/test_o_chat_fala_como_corretor.py
        `--mutar` acrescenta as 2 mutacoes por copia (so com a arvore parada).
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import shutil
import socket
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

TESTES = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTES)                      # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# ===========================================================================
# 🔴 OS DOIS DETECTORES -- e eles sao o contrato, nao um detalhe
#
#   CHAVE_COM_VERSAO   `production.new_vs_renewal@1`  -- o ponteiro inteiro
#   CHAVE              `portfolio.cancellation_rate`  -- a chave sozinha
#
# ⚠️ O segundo exige `_` de um dos lados do ponto, de proposito: sem isso ele
# acusaria `app.py`, `1.5` e qualquer sigla com ponto. O que se procura e a
# FORMA de identificador de banco -- minusculas, `_` e `.`.
# ===========================================================================
CHAVE_COM_VERSAO = re.compile(r"\b[a-z][a-z_]*\.[a-z][a-z_]*@\d+\b")
CHAVE = re.compile(r"\b(?:[a-z]+_[a-z_]+\.[a-z_]+|[a-z]+\.[a-z]+_[a-z_]+)\b")

#: ⛔ O que NAO e chave e apareceria por motivo legitimo. Lista curta e fechada:
#: cada entrada e uma excecao que alguem teve de justificar.
PERDOADAS = ("app.py", "chat.py", "webhook.py")


def chaves_em(texto):
    """As chaves de banco que este texto carrega. Lista vazia = fala humana."""
    bruto = str(texto or "")
    achadas = [m.group(0) for m in CHAVE_COM_VERSAO.finditer(bruto)]
    achadas += [m.group(0) for m in CHAVE.finditer(bruto)]
    return [a for a in achadas if a not in PERDOADAS]


# ===========================================================================
# O placar -- tres verbos (o molde de 095/096/097)
# ===========================================================================
OK = FAIL = 0
NOMES_FALHOS: set = set()
PULADOS: list = []

# ===========================================================================
# 🔴 A DECLARACAO DE MUTACOES. Marcador UNICO, ancora no CODIGO.
# ===========================================================================
MUTACOES = [
    # U7A -- o que se DIZ da metrica volta a ser a chave -> [B4] vermelho.
    ("app/comercial/evidence_pack.py",
     'rotulo = str(getattr(m, "label", "") or "").strip()',
     'rotulo = ""  # _MUTADO_U7A',
     "U7A"),
    # U7B -- o catalogo volta a publicar o ponteiro -> [B2] vermelho.
    ("app/agents/tools/executive_intelligence.py",
     'itens.append({"label": d.label,',
     'itens.append({"label": d.ref,  # _MUTADO_U7B',
     "U7B"),
]


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        _p("  [ok] %s" % rotulo)
    else:
        FAIL += 1
        NOMES_FALHOS.add(rotulo)
        _p("  [FALHOU] %s" % rotulo
           + ("\n         %s" % str(detalhe)[:700] if detalhe else ""))
    return bool(cond)


def par(cond_reprovou, rotulo, detalhe=""):
    """A linha de controle. `cond_reprovou` e True quando o guarda ACUSOU."""
    global OK, FAIL
    if cond_reprovou:
        OK += 1
        _p("  [ok] PAR %s -- o guarda acusou" % rotulo)
    else:
        FAIL += 1
        NOMES_FALHOS.add("PAR " + rotulo)
        _p("  [FALHOU] PAR %s -- o guarda NAO acusou; ele nao guarda nada" % rotulo
           + ("\n         %s" % str(detalhe)[:400] if detalhe else ""))
    return bool(cond_reprovou)


def pular(rotulo, razao):
    PULADOS.append(rotulo)
    _p("  --   PULADO %s\n         %s" % (rotulo, razao))


def ler(relativo):
    caminho = os.path.join(RAIZ, relativo)
    if not os.path.exists(caminho):
        return ""
    return io.open(caminho, encoding="utf-8", errors="replace").read()


# ===========================================================================
# 🔴 A REDE FECHADA E O IMPORT POR CAMINHO -- as duas licoes da 096/097
#
# 📊 Medido em 05/09/2026, nesta maquina: `import app.agents.tools.
# executive_intelligence` (pelo pacote) passou de **6 minutos** sem terminar --
# o `__init__` do pacote puxa o grafo, o spacy e as retentativas de Redis e
# Qdrant que nao existem aqui. O MESMO arquivo, carregado por CAMINHO e com a
# rede fechada: **58 s**. Guarda que ninguem espera terminar e guarda que
# ninguem roda.
# ===========================================================================
_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


def _loopback(destino):
    """⚠️ O `asyncio` do Windows abre um socketpair em 127.0.0.1 para o proprio
    laco de eventos. Barrar o loopback impediria o guarda de rodar `async`."""
    try:
        return isinstance(destino, tuple) and str(destino[0]) in ("127.0.0.1", "::1", "localhost")
    except Exception:  # noqa: BLE001
        return False


def _proibir(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT(self, destino, *a, **k)
    raise RuntimeError("SEM_REDE: este guarda nao fala com a rede (destino %r)" % (destino,))


def _proibir_ex(self, destino, *a, **k):  # noqa: ANN001
    if _loopback(destino):
        return _CONNECT_EX(self, destino, *a, **k)
    raise RuntimeError("SEM_REDE: este guarda nao fala com a rede (destino %r)" % (destino,))


def _fechar_a_rede():
    os.environ["SEM_REDE"] = "1"
    socket.socket.connect = _proibir        # type: ignore[assignment]
    socket.socket.connect_ex = _proibir_ex  # type: ignore[assignment]


def _abrir_a_rede():
    socket.socket.connect = _CONNECT        # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]
    os.environ.pop("SEM_REDE", None)


_CACHE_DE_MODULOS: dict = {}


def carregar_solto(relativo, nome):
    """Importa um arquivo do produto por CAMINHO. Devolve `(modulo, erro)`."""
    if nome in _CACHE_DE_MODULOS:
        return _CACHE_DE_MODULOS[nome]
    caminho = os.path.join(RAIZ, relativo)
    if not os.path.exists(caminho):
        _CACHE_DE_MODULOS[nome] = (None, None)
        return None, None
    try:
        spec = importlib.util.spec_from_file_location(nome, caminho)
        mod = importlib.util.module_from_spec(spec)
        # 🔴 REGISTRAR ANTES DE EXECUTAR. 📊 Sem esta linha, o pydantic da
        #    `ExecutiveIntelligenceTool` levanta *"is not fully defined; you
        #    should define `Type`"* -- ele resolve as anotacoes pelo namespace do
        #    modulo em `sys.modules`, e um modulo que nao esta la nao tem
        #    namespace nenhum para ele achar.
        sys.modules[nome] = mod
        spec.loader.exec_module(mod)
        saida = (mod, None)
    except Exception as erro:  # noqa: BLE001
        saida = (None, erro)
    _CACHE_DE_MODULOS[nome] = saida
    return saida


def so_o_codigo_py(fonte):
    """O python sem docstring de modulo e sem `#` -- a prosa nao vale como prova."""
    sem_doc = '"""'.join(fonte.split('"""')[::2])
    return "\n".join(l.split("#", 1)[0] for l in sem_doc.splitlines())


# ===========================================================================
# [B0] O CONTROLE DOS DETECTORES -- antes de usa-los em qualquer lugar
# ===========================================================================
def bloco_B0():
    _p("\n[B0] os detectores CONSEGUEM acusar -- e nao acusam fala humana")
    # ⚠️ Os dois detectores casam o mesmo trecho quando ha versao (um com o
    #    `@1`, outro sem) -- e isso e o certo: o que importa e que a chave FOI
    #    acusada, nao quantas vezes. Exigir lista de tamanho 1 aqui mediria o
    #    detector, e nao o produto.
    certo("production.new_vs_renewal@1" in chaves_em("production.new_vs_renewal@1"),
          "[B0a] o ponteiro colado pelo Founder e detectado",
          "achadas=%r" % chaves_em("production.new_vs_renewal@1"))
    certo(chaves_em("portfolio.cancellation_rate") == ["portfolio.cancellation_rate"],
          "[B0b] a chave sem versao tambem",
          "achadas=%r" % chaves_em("portfolio.cancellation_rate"))
    certo(bool(chaves_em("commission.broker_accrued@1 e data.coverage@1")),
          "[B0c] as outras duas formas coladas pelo Founder")
    humana = ("A comissão apropriada no período cresceu 12% frente ao mesmo "
              "período do ano passado, e a taxa de cancelamento ficou estável. "
              "São R$ 128.400,00 em 312 apólices.")
    certo(chaves_em(humana) == [],
          "[B0d] e a frase de um corretor NAO e acusada (senao o guarda proibiria falar)",
          "achadas=%r" % chaves_em(humana))
    par(bool(chaves_em("mix.insurer@1")),
        "[B0] texto-controle com chave (o detector nao aprova tudo)")
    par(not chaves_em("R$ 1.234,00 em 12 apólices, 8,5% acima"),
        "[B0] texto-controle com DINHEIRO e porcentagem (o detector nao proibe numero)")


# ===========================================================================
# [B1] as instrucoes de narracao -- elas MANDAVAM citar a chave
# ===========================================================================
def bloco_B1():
    _p("\n[B1] U7 -- as instrucoes de narracao proibem a chave (e nao a exigem)")
    EI, erro_ei = carregar_solto("app/agents/tools/executive_intelligence.py", "_ei_u7")
    RC, erro_rc = carregar_solto("app/agents/tools/relatorios_comerciais.py", "_rc_u7")
    if RC is None or EI is None:
        certo(False, "[B1] as duas ferramentas de relatorio carregam",
              "executive_intelligence: %r · relatorios_comerciais: %r"
              % (erro_ei, erro_rc))
        return

    for nome, texto in (("relatorios_comerciais._COMO_FALAR", RC._COMO_FALAR),
                        ("executive_intelligence.COMO_FALAR", EI.COMO_FALAR),
                        ("COMO_FALAR_DO_CATALOGO", EI.COMO_FALAR_DO_CATALOGO)):
        achadas = chaves_em(texto)
        certo(not achadas, "[B1] `%s` nao carrega chave nenhuma" % nome,
              "achadas=%r" % achadas)
        baixo = str(texto).lower()
        certo("nunca" in baixo and ("metric_id" in baixo or "chave" in baixo),
              "[B1] `%s` PROIBE a chave com todas as letras" % nome,
              "📊 antes ela MANDAVA citar `metric_id@version` ao lado de cada numero")

    # 🔴 O PAR: a instrucao ANTIGA, palavra por palavra, TEM de reprovar.
    antiga = ("Comente para o dono usando SÓ os números do bloco PACK acima, "
              "citando `metric_id@version` ao lado de cada número que você disser.")
    par("nunca" not in antiga.lower(),
        "[B1] instrucao-controle (a de 03/09) nao proibia nada")


# ===========================================================================
# [B2] o CATALOGO, executado -- a ferramenta de verdade, sem banco
# ===========================================================================
def bloco_B2():
    _p("\n[B2] U7 -- o CATALOGO que sai da ferramenta (`listar_metricas=True`)")
    import asyncio

    EI, erro = carregar_solto("app/agents/tools/executive_intelligence.py", "_ei_u7")
    if EI is None:
        certo(False, "[B2] a ferramenta de panorama carrega", repr(erro))
        return

    tool = EI.ExecutiveIntelligenceTool(company_id="co-097", supabase=None)
    try:
        texto = asyncio.run(tool._arun(listar_metricas=True))
        rodou = True
    except Exception as exc:  # noqa: BLE001
        texto, rodou = "%s: %s" % (type(exc).__name__, exc), False
    certo(rodou and "METRICAS_REGISTRADAS" in texto,
          "[B2a] a ferramenta responde o catalogo sem tocar em banco", texto[:300])
    achadas = chaves_em(texto)
    certo(rodou and not achadas,
          "[B2b] o catalogo NAO carrega `metric_id` nem `metric_id@versao`",
          "achadas=%r" % sorted(set(achadas))[:12])
    certo(rodou and "label" in texto and "pergunta_verificada" in texto,
          "[B2c] e carrega o NOME e a PERGUNTA -- o que o modelo pode dizer")

    par(bool(chaves_em('{"metric_id": "mix.branch", "ref": "mix.branch@1"}')),
        "[B2] catalogo-controle no formato anterior (com `metric_id` e `ref`)")


# ===========================================================================
# [B3] a RECUSA de metrica -- executada com o registry REAL
# ===========================================================================
def bloco_B3():
    _p("\n[B3] U7 -- a recusa de metrica nao registrada fala humano")
    try:
        from app.comercial.metricas import registry
        from app.comercial.proposta import propor_a_partir_do_pedido
    except Exception as exc:  # noqa: BLE001
        certo(False, "[B3] o registry e a proposta importam",
              "%s: %s" % (type(exc).__name__, exc))
        return

    pedidos = ("taxa de cancelamento da carteira",
               "quanto cada seguradora me deu de comissao",
               "sinistralidade por ramo")
    for pedido in pedidos:
        pr = propor_a_partir_do_pedido(pedido, registry.todas(),
                                       registry.POLICY_VALID_FROM)
        frase = pr.frase()
        achadas = chaves_em(frase)
        certo(not achadas, "[B3] a recusa de %r nao cita chave" % pedido[:28],
              "frase=%r achadas=%r" % (frase[:240], achadas))
        # 🔴 E o ponteiro CONTINUA no registro: ele nao foi apagado, so calou.
        certo(str(pr.serializar().get("nome_sugerido") or "").startswith("proposta."),
              "[B3] e o `nome_sugerido` continua em `serializar()` -- o ponteiro vive")

    par(bool(chaves_em("⚠️ Proponho `proposta.taxa_cancelamento`. Já existe algo "
                       "parecido: portfolio.cancellation_rate.")),
        "[B3] recusa-controle no formato anterior (nome sugerido e parecido crus)")


# ===========================================================================
# [B4] toda metrica tem NOME -- senao o modelo nao tem o que dizer
# ===========================================================================
def bloco_B4():
    _p("\n[B4] U7 -- `label` em TODA metrica, e o que se DIZ dela e portugues")
    try:
        from app.comercial.evidence_pack import metrica, nome_da_metrica
        from app.comercial.metricas import registry
    except Exception as exc:  # noqa: BLE001
        certo(False, "[B4] registry e evidence_pack importam",
              "%s: %s" % (type(exc).__name__, exc))
        return

    todas = registry.todas()
    sem_rotulo = [mid for mid, d in todas.items() if not str(d.label or "").strip()]
    certo(bool(todas) and not sem_rotulo,
          "[B4a] as %d metricas registradas tem `label`" % len(todas),
          "sem rotulo: %r" % sem_rotulo[:8])

    # 🔴 EXECUTA o caminho do numero: definicao -> MetricResult -> o que se diz.
    #
    # ⚠️ A exigencia e IGUALDADE com o `label` do registry, e nao apenas
    # "nao parece chave". 📊 A mutacao U7A descobriu a diferenca: com o rotulo
    # ignorado, o nome degradava para *"commission broker accrued"* -- que passa
    # em qualquer detector de chave e mesmo assim NAO e portugues. Um guarda que
    # aceitasse isso deixaria a regressao passar (CLAUDE.md §9.3).
    ruins = []
    for mid, d in sorted(todas.items()):
        m = metrica(mid, None, d.unit,
                    period={"start": "2026-01-01", "end": "2026-01-31"},
                    time_basis=d.time_basis, version=d.version, label=d.label)
        dito = nome_da_metrica(m)
        if chaves_em(dito) or not dito.strip():
            ruins.append((mid, dito))
        elif dito != d.label:
            ruins.append((mid, "disse %r, e o nome registrado e %r" % (dito, d.label)))
        if m.serializar().get("label") != d.label:
            ruins.append((mid, "o `label` nao chegou ao envelope"))
    certo(not ruins,
          "[B4b] o que se DIZ de cada metrica e o NOME REGISTRADO dela, e ele "
          "viaja no envelope",
          "%r" % ruins[:6])

    m_sem = metrica("commission.broker_accrued", None, "BRL",
                    period={"start": "2026-01-01", "end": "2026-01-31"},
                    time_basis=registry.POLICY_VALID_FROM)
    par(not chaves_em(nome_da_metrica(m_sem)),
        "[B4] envelope-controle SEM rotulo: o nome degrada para palavras (%r)"
        % nome_da_metrica(m_sem))
    par(bool(chaves_em("commission.broker_accrued")),
        "[B4] e a chave crua CONTINUA sendo acusada (senao [B4b] passaria por acaso)")


# ===========================================================================
# [B5] o aviso da metrica que FALHOU -- com uma excecao de verdade
# ===========================================================================
def bloco_B5():
    _p("\n[B5] U7 -- a metrica que falha avisa pelo NOME, nao pelo ponteiro")
    try:
        from datetime import date

        from app.comercial.metricas import registry
    except Exception as exc:  # noqa: BLE001
        certo(False, "[B5] o registry importa", "%s: %s" % (type(exc).__name__, exc))
        return

    todas = registry.todas()
    if not todas:
        certo(False, "[B5] ha metrica registrada para medir")
        return
    mid, d = sorted(todas.items())[0]

    class _FactsVazio:
        provider_key = "infocap"

    try:
        resultado = registry._isolar(d, (date(2026, 1, 1), date(2026, 1, 31)),
                                     _FactsVazio(), RuntimeError("fonte fora do ar"))
        avisos = list(resultado.warnings or ())
        rodou = True
    except Exception as exc:  # noqa: BLE001
        avisos, rodou = ["%s: %s" % (type(exc).__name__, exc)], False
    achadas = [c for a in avisos for c in chaves_em(a)]
    certo(rodou and bool(avisos) and not achadas,
          "[B5a] o aviso da falha nao diz `%s@%d`" % (mid, d.version),
          "avisos=%r achadas=%r" % (avisos[:2], achadas))
    certo(rodou and any(d.label in a for a in avisos),
          "[B5b] e o nome que ele diz e o `label` do registry (%r)" % d.label,
          "avisos=%r" % (avisos[:2],))

    par(bool(chaves_em("%s@%d: o cálculo desta métrica FALHOU" % (mid, d.version))),
        "[B5] aviso-controle no formato anterior (`metric_id@versao` na frente)")


# ===========================================================================
# [B6] o resumo e a direcao -- as frases que acompanham TODA resposta
# ===========================================================================
def bloco_B6():
    _p("\n[B6] U7 -- o resumo deterministico e a frase de direcao")
    EI, erro = carregar_solto("app/agents/tools/executive_intelligence.py", "_ei_u7")
    if EI is None:
        certo(False, "[B6] a ferramenta de panorama carrega", repr(erro))
        return
    RESUMO_DETERMINISTICO = EI.RESUMO_DETERMINISTICO
    direcao_do_periodo = EI.direcao_do_periodo

    certo(not chaves_em(RESUMO_DETERMINISTICO),
          "[B6a] o resumo deterministico nao cita chave",
          "achadas=%r" % chaves_em(RESUMO_DETERMINISTICO))

    class _Pacote:
        comparacoes = [{"metric_id": "commission.broker_accrued", "delta": 12.0},
                       {"metric_id": "mix.insurer", "delta": -3.0},
                       {"metric_id": "data.coverage", "delta": "UNAVAILABLE"}]

    frase = direcao_do_periodo(_Pacote())
    certo(bool(frase) and not chaves_em(frase),
          "[B6b] a frase de direcao fala de subir e cair SEM citar chave",
          "frase=%r achadas=%r" % (frase[:240], chaves_em(frase)))

    par(bool(chaves_em("o tamanho está em `comparacoes`, com o `metric_id` ao "
                       "lado: commission.broker_accrued@1")),
        "[B6] frase-controle no formato anterior")


# ===========================================================================
# [B7] a regra no PROMPT -- por LEITURA, e esta declarado
# ===========================================================================
def bloco_B7():
    _p("\n[B7] U7 -- a regra curta no prompt do chat (⚠️ leitura de fonte)")
    codigo = so_o_codigo_py(ler("app/agents/graph.py"))
    if not codigo:
        certo(False, "[B7] `app/agents/graph.py` existe e foi lido")
        return
    baixo = codigo.lower()
    certo("nunca cite chaves" in baixo,
          "[B7a] o prompt do chat manda NUNCA citar chave, variavel ou campo",
          "⚠️ metade FRACA, por leitura: os pares abaixo provam que o cortador corta")
    certo("base_instructions" in codigo and "_fale_como_corretor" in baixo,
          "[B7b] e a regra e ANEXADA as instrucoes do agente (nao fica solta)")

    par("nunca cite chaves" not in so_o_codigo_py(
            "# nunca cite chaves  <- so no comentario\nx = 1\n").lower(),
        "[B7] cortador-controle: a regra SO no comentario nao conta")
    par("nunca cite chaves" in so_o_codigo_py(
            'REGRA = "nunca cite chaves"\n').lower(),
        "[B7] cortador-controle: a regra no CODIGO conta (senao [B7a] nunca fica verde)")


# ===========================================================================
# As mutacoes por COPIA -- so com `--mutar`
# ===========================================================================
def _rodar():
    bloco_B0()
    bloco_B1()
    bloco_B2()
    bloco_B3()
    bloco_B4()
    bloco_B5()
    bloco_B6()
    bloco_B7()


def _remedir():
    """Roda tudo de novo, EM OUTRO PROCESSO.

    🔴 O produto ja esta importado neste processo, e `import` e cacheado: sem o
    subprocesso, a mutacao no arquivo nao mudaria o modulo em memoria e passaria
    por *"nao mudou nada"* sem nunca ter sido medida.
    """
    import subprocess
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], cwd=RAIZ,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    saida = (r.stdout or "") + (r.stderr or "")
    return set(re.findall(r"\[FALHOU\] (.+)", saida))


def rodar_mutacoes():
    _p("\n[M] MUTACOES POR COPIA -- a arvore precisa estar parada")
    antes = _remedir()
    for caminho, de, para, marcador in MUTACOES:
        alvo = os.path.join(RAIZ, caminho)
        if not os.path.exists(alvo):
            pular("mutacao %s (%s)" % (marcador, caminho), "o arquivo nao existe")
            continue
        original = io.open(alvo, encoding="utf-8", errors="replace").read()
        if de not in original:
            pular("mutacao %s (%s)" % (marcador, caminho),
                  "a ancora %r nao existe -- mutacao que nao aplica NAO e "
                  "mutacao passada" % de[:60])
            continue
        backup = alvo + ".bak-u7"
        shutil.copyfile(alvo, backup)
        try:
            io.open(alvo, "w", encoding="utf-8").write(original.replace(de, para, 1))
            novos = sorted(_remedir() - antes)
            if novos:
                _p("        nomes NOVOS que ficaram vermelhos: %s" % "; ".join(novos))
            par(bool(novos), "mutacao %s em %s" % (marcador, caminho),
                "a mutacao foi aplicada e NENHUM NOME NOVO ficou vermelho -- "
                "o bloco e carimbo")
        finally:
            shutil.copyfile(backup, alvo)
            os.remove(backup)


def main():
    mutar = "--mutar" in sys.argv or os.environ.get("AUTOBROKERS_MUTAR") == "1"

    _p("=" * 78)
    _p("  O CHAT FALA COMO CORRETOR -- e nunca como banco de dados  (SPEC-097 U7)")
    _p("=" * 78)
    _fechar_a_rede()
    try:
        _rodar()
    finally:
        _abrir_a_rede()
    if mutar:
        rodar_mutacoes()
    else:
        _p("\n[M] MUTACOES POR COPIA -- NAO rodaram (sem `--mutar`).")
        _p("      ⛔ Elas escrevem em `backend/app/`. Com a arvore parada: `--mutar`.")

    _p("\n" + "=" * 78)
    _p("  %d ok · %d falha(s) · %d pulado(s)" % (OK, FAIL, len(PULADOS)))
    if PULADOS:
        _p("  -- pulados: %s" % " · ".join(PULADOS))
    if FAIL:
        _p("\n  ⛔ HA %d VERMELHO -- procure as linhas `[FALHOU]`." % FAIL)
    else:
        _p("\n  VERDE -- o numero sai com NOME; o ponteiro fica no relatorio.")
    _p("=" * 78)
    return 1 if FAIL else 0


def test_o_chat_fala_como_corretor():
    """🔴 Roda a si mesmo num subprocesso (o modulo mexe com `sys.path`)."""
    import subprocess
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], cwd=RAIZ,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    assert r.returncode == 0, (r.stdout[-4000:] + r.stderr[-1500:])


if __name__ == "__main__":
    sys.exit(main())

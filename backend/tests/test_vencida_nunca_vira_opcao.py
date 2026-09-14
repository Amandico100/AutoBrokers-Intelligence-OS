# -*- coding: utf-8 -*-
r"""M-B1 — VENCIDA NUNCA VIRA OPCAO. SPEC-EXTRA-001.1 BLOCO B, GATE B1.

```
listar_apolices(incluir_vencidas=False)  ->  ZERO vencidas
historico_oculto                         ->  documents_count - vigentes
```

📊 **O acervo real de 09-11/09/2026**: 7 respostas do chat com lista de
apolices, **31 linhas de opcao**, das quais **24 com fim de vigencia passado**.
Sete de sete perguntaram *"qual delas?"*; **zero** responderam com a unica
vigente. A apolice certa estava na tela — enterrada em quatro vencidas.

🔴 **E o caso que obriga a lista INTEIRA**: a fonte trunca `matches` em 10 e
devolve `documents_count` cheio. 📊 A empresa da pergunta q4 tem
`documents_count` **11** e `matches` **10**. Se a unica VIGENTE estivesse na
11a posicao, uma porta que lesse `matches` concluiria *"nenhuma apolice
vigente"* — e responderia a frase da §6.2 MENTINDO. O caso real (11/10) e o
sintetico (12 com a vigente na 11a) rodam os dois.

```
 [GB1a] FILTRO      as 3 listagens reais + as 7 perguntas: 0 vencidas devolvidas
 [GB1b] A 11a       a vigente fora do corte de 10 continua sendo encontrada
 [GB1c] O PAR       `incluir_vencidas=True` devolve TUDO — o filtro e escolha, nao perda
 [GB1d] O STATUS    `policy_status = "ativo"` numa VENCIDA nao a torna vigente
```

⚠️ **O teste chama o MOTOR** (CLAUDE.md §9.4): `InfoCapProvider.listar_apolices`
com o conector DUBLADO, e `lista_de_apolices_do_lookup`. Nenhum regex sobre a
mesma tabela que o codigo le; nenhuma reimplementacao da regra de vigencia.

⛔ SEGURANCA: `SEM_REDE=1`, sem banco, sem PII. As listagens sinteticas trazem
rotulos (`AP-1`), nunca numero de apolice real.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_vencida_nunca_vira_opcao.py
    ... --so GB1b   ·   ... --medir   ·   ... --mutar [M-B1a]
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
TESTES = os.path.join(RAIZ, "tests")
FIXTURES = os.path.join(TESTES, "fixtures")
GOLDEN = os.path.join(FIXTURES, "golden_apolices_extra0011.json")
SINTETICAS = os.path.join(FIXTURES, "listagens_extra0011.json")
CORPUS = os.path.join(TESTES, "corpus", "perguntas_do_chat", "2026-09-09_10.json")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

#: 🔴 O "hoje" e PARAMETRO em toda a cadeia (`classificar_vigencia`,
#: `listar_apolices`, `escolher_apolice`). Fixa-lo aqui e o que faz este guarda
#: dar o mesmo veredito em 2027 — um guarda que muda de cor com o calendario
#: ensina a ignorar guarda.
HOJE = date(2026, 9, 14)

_CONNECT = socket.socket.connect
_CONNECT_EX = socket.socket.connect_ex


#: ⚠️ O `asyncio` do Windows (`ProactorEventLoop`) abre um `socketpair()` de
#: LOOPBACK so para poder acordar a si mesmo. Bloquear ISSO nao bloqueia a
#: InfoCap: derruba o interpretador antes de o guarda medir qualquer coisa. O
#: que a trava existe para impedir e uma viagem para FORA — e essa continua
#: impossivel.
_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}


def _e_local(endereco):
    alvo = endereco[0] if isinstance(endereco, (tuple, list)) and endereco else endereco
    return str(alvo) in _LOOPBACK


def _proibir(self, endereco=None, *a, **k):  # noqa: ANN001
    if _e_local(endereco):
        return _CONNECT(self, endereco, *a, **k)
    raise RuntimeError("SPEC-EXTRA-001.1: SEM_REDE=1. Destino: %r" % (endereco,))


def _proibir_ex(self, endereco=None, *a, **k):  # noqa: ANN001
    if _e_local(endereco):
        return _CONNECT_EX(self, endereco, *a, **k)
    raise RuntimeError("SPEC-EXTRA-001.1: SEM_REDE=1. Destino: %r" % (endereco,))


def _bloquear_a_rede():
    socket.socket.connect = _proibir       # type: ignore[assignment]
    socket.socket.connect_ex = _proibir_ex  # type: ignore[assignment]


def _devolver_a_rede():
    socket.socket.connect = _CONNECT       # type: ignore[assignment]
    socket.socket.connect_ex = _CONNECT_EX  # type: ignore[assignment]


PASS = 0
FAIL = 0
MEDIDAS: dict = {}


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(texto.encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:500] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


# ===========================================================================
# O MONTADOR — um so, importado pelos outros dois guardas do BLOCO B
# ===========================================================================
def ler(caminho):
    with io.open(caminho, encoding="utf-8") as fh:
        return json.load(fh)


def resposta_do_conector(caso, *, truncar_em=10):
    """Uma listagem do acervo -> a resposta que `infocap_lookup` devolveria.

    🔴 A forma e a REAL: `matches` truncado (o texto que vai ao modelo),
    `policies_all` inteiro (o que DECIDE) e `documents_count` cheio
    (`infocap_connector.py`, os dois retornos de `ambiguous_policy`).
    """
    crus = []
    for indice, apolice in enumerate(caso["apolices"], start=1):
        crus.append({
            "policy_locator_ref": "infocap:1:N%d" % indice,
            "policy_ref": "N%d" % indice,
            "policy_number": "AP-%d" % indice,
            "insurer_key": apolice["seguradora_abrev"],
            "product": apolice["ramo_abrev"],
            "valid_from": apolice["inicio"],
            "valid_to": apolice["fim"],
            "cancelled": apolice["cancelado"],
            "policy_status": apolice["status_cru_do_fornecedor"],
        })
    return {
        "ok": False,
        "status": caso.get("status") or "ambiguous_policy",
        "documents_count": int(caso.get("documents_count") or len(crus)),
        "matches": crus[:truncar_em],
        "policies_all": crus,
        "requires_human": True,
        "blockers": ["multiple_policies"],
    }


def provider_dublado(resposta):
    """`InfoCapProvider` REAL com o `lookup` dublado. ⛔ Nada de rede.

    ⚠️ O que se dubla e a VIAGEM, nunca a regra: `listar_apolices`,
    `lista_de_apolices_do_lookup`, `_apolice_na_lista` e `classificar_vigencia`
    sao os do produto, e sao eles que este guarda mede.
    """
    from app.providers.infocap_policy_provider import InfoCapProvider

    provider = InfoCapProvider()

    async def _lookup(**kwargs):
        return resposta

    provider.lookup = _lookup  # type: ignore[method-assign]
    return provider


def listar(caso, *, incluir_vencidas=False, ramo=None, truncar_em=10, hoje=HOJE):
    """O MOTOR, ponta a ponta: `InfoCapProvider.listar_apolices`."""
    provider = provider_dublado(resposta_do_conector(caso, truncar_em=truncar_em))
    return asyncio.run(provider.listar_apolices(
        company_id="tenant-de-teste", cliente_ref="cliente-de-teste",
        incluir_vencidas=incluir_vencidas, ramo=ramo, hoje=hoje,
    ))


def casos_sinteticos():
    return ler(SINTETICAS)["casos"]


def listagens_reais():
    return {k: v for k, v in ler(GOLDEN)["listagens"].items() if not k.startswith("_")}


# ===========================================================================
# [GB1a] FILTRO — 0 vencidas, e o historico bate com `documents_count`
# ===========================================================================
def gate_GB1a():
    _p("\n[GB1a] FILTRO -- as 3 listagens REAIS: zero vencidas, historico honesto")
    reais = listagens_reais()
    check("[GB1a] as 3 listagens reais do acervo estao no golden", len(reais) == 3, sorted(reais))

    total_vencidas = 0
    for nome, caso in sorted(reais.items()):
        lista = listar(caso)
        vencidas = [a for a in lista.itens if a.vigencia.situacao in ("VENCIDA", "CANCELADA")]
        total_vencidas += len(vencidas)
        # A contagem de vigentes vem da lista INTEIRA, nao do que sobrou.
        inteira = listar(caso, incluir_vencidas=True)
        vigentes = len(inteira.vigentes)
        esperado = int(caso["documents_count"]) - vigentes
        check("[GB1a] %s: nenhuma vencida/cancelada devolvida (%d de %d)"
              % (nome, len(lista.itens), caso["documents_count"]),
              not vencidas, [a.apolice_ref for a in vencidas])
        check("[GB1a] %s: historico_oculto = documents_count - vigentes = %d"
              % (nome, esperado),
              lista.historico_oculto == esperado,
              "historico_oculto=%r documents_count=%r vigentes=%r"
              % (lista.historico_oculto, caso["documents_count"], vigentes))
        check("[GB1a] %s: `total` e a contagem CHEIA da fonte, nao len(matches)" % nome,
              lista.total == int(caso["documents_count"]),
              "total=%r documents_count=%r" % (lista.total, caso["documents_count"]))
    medir("vencidas_devolvidas_nas_3_listagens_reais", total_vencidas)

    # As 7 perguntas REAIS: a contagem que o corpus registra tem de bater com a
    # que o motor produz sobre uma listagem com a mesma composicao.
    corpus = ler(CORPUS)
    perguntas = corpus["perguntas"]
    check("[GB1a] o corpus tem as 7 perguntas reais de 09-11/09", len(perguntas) == 7, len(perguntas))
    check("[GB1a] o acervo registra 31 linhas de opcao e 24 com vigencia passada",
          corpus["acervo"]["linhas_de_opcao"] == 31
          and corpus["acervo"]["linhas_com_fim_de_vigencia_passado"] == 24,
          corpus["acervo"])
    respondidas_em_uma_rodada = 0
    for pergunta in perguntas:
        contagem = pergunta["apolices_no_acervo"]
        caso = _caso_da_contagem(contagem)
        lista = listar(caso)
        vencidas = [a for a in lista.itens if a.vigencia.situacao in ("VENCIDA", "CANCELADA")]
        check("[GB1a] %s (%d apolices, %d vigente(s)): 0 vencidas na resposta"
              % (pergunta["id"], contagem["total"], contagem["vigentes"]),
              not vencidas, [a.apolice_ref for a in vencidas])
        if len(lista.vigentes) == 1:
            respondidas_em_uma_rodada += 1
    medir("perguntas_com_uma_unica_vigente", respondidas_em_uma_rodada)
    # 📊 5 de 7: q1..q5 tem UMA vigente cada; q6 e q7 sao a mesma pessoa, com
    #    DUAS vigentes de ramos diferentes (residencial e vida) — e as duas
    #    perguntas dizem o ramo, entao elas fecham no M-B3, nao aqui. O acervo
    #    respondeu ZERO de 7 em uma rodada; a conta de hoje e 5 pela lista e 7
    #    com o ramo aplicado.
    check("[GB1a] 5 das 7 perguntas ja ficam com UMA unica vigente (q6/q7 tem 2 ramos)",
          respondidas_em_uma_rodada == 5, respondidas_em_uma_rodada)


def _caso_da_contagem(contagem):
    """Uma listagem com a MESMA composicao que o corpus mediu, sem PII.

    ⚠️ O corpus guarda so as perguntas e as CONTAGENS (`total`, `vigentes`,
    `vencidas`, `canceladas`) — nenhuma linha de apolice real saiu do banco.
    Reconstruir a composicao e o que permite medir o motor sobre o acervo sem
    copiar dado de cliente.
    """
    apolices = []
    for i in range(int(contagem["vigentes"])):
        apolices.append({"seguradora_abrev": "HDI" if i == 0 else "METL",
                         "ramo_abrev": "RESI" if i == 0 else "VIND",
                         "inicio": "01/01/2026", "fim": "01/01/2027",
                         "cancelado": False, "status_cru_do_fornecedor": "ativo"})
    for i in range(int(contagem["vencidas"])):
        apolices.append({"seguradora_abrev": "ALLI", "ramo_abrev": "RESI",
                         "inicio": "01/01/%d" % (2010 + i), "fim": "01/01/%d" % (2011 + i),
                         "cancelado": False, "status_cru_do_fornecedor": "ativo"})
    for i in range(int(contagem.get("canceladas") or 0)):
        apolices.append({"seguradora_abrev": "PORT", "ramo_abrev": "AUTO",
                         "inicio": "01/01/2026", "fim": "01/01/2027",
                         "cancelado": True, "status_cru_do_fornecedor": "cancelado"})
    return {"documents_count": int(contagem["total"]), "apolices": apolices,
            "status": "ambiguous_policy"}


# ===========================================================================
# [GB1b] A 11a — a vigente fora do corte de 10
# ===========================================================================
def gate_GB1b():
    _p("\n[GB1b] A 11a -- a unica vigente fora do corte de 10 continua sendo encontrada")
    sinteticos = casos_sinteticos()

    # O caso REAL: 11 apolices, 10 devolvidas (a vigente esta dentro do corte).
    real = listagens_reais()["empresa_11_apolices"]
    check("[GB1b] o caso real 11/10 esta no golden",
          real["documents_count"] == 11 and real["matches_devolvidos"] == 10,
          (real["documents_count"], real["matches_devolvidos"]))
    lista_real = listar(real)
    check("[GB1b] caso REAL: a vigente e encontrada e o historico diz 10",
          len(lista_real.vigentes) == 1 and lista_real.historico_oculto == 10,
          "vigentes=%d oculto=%d" % (len(lista_real.vigentes), lista_real.historico_oculto))

    # O caso SINTETICO: 12 apolices, a unica vigente na 11a posicao.
    doze = sinteticos["doze_com_a_vigente_na_11"]
    posicoes_vigentes = [i for i, a in enumerate(doze["apolices"], start=1)
                         if a["fim"] == "01/02/2027"]
    check("[GB1b] a fixture poe a unica vigente na 11a posicao",
          posicoes_vigentes == [11], posicoes_vigentes)
    lista = listar(doze)
    medir("vigentes_no_caso_de_12", len(lista.vigentes))
    check("[GB1b] 🔴 a vigente da 11a posicao APARECE (a decisao le a lista inteira)",
          len(lista.vigentes) == 1,
          "itens=%r" % ([(a.apolice_ref, a.vigencia.situacao) for a in lista.itens],))
    check("[GB1b] e ela e a ALLI de 01/02/2026 a 01/02/2027",
          bool(lista.vigentes) and lista.vigentes[0].apolice_ref == "infocap:1:N11",
          [a.apolice_ref for a in lista.vigentes])
    check("[GB1b] historico_oculto = 12 - 1 = 11", lista.historico_oculto == 11, lista.historico_oculto)

    # 🔴 O PAR DO DETECTOR: com a lista truncada em 10 e SEM `policies_all`, a
    #    vigente some. E a prova de que a leitura da lista inteira e o que faz a
    #    asserção de cima passar — e nao um acaso da fixture.
    from app.providers.infocap_policy_provider import lista_de_apolices_do_lookup

    so_truncada = resposta_do_conector(doze, truncar_em=10)
    so_truncada.pop("policies_all")
    truncada = lista_de_apolices_do_lookup(so_truncada, cliente_ref="c", hoje=HOJE)
    check("[GB1b] PAR-CONTROLE: sem `policies_all`, a mesma lista perde a vigente "
          "(era o defeito de 13/09)",
          len(truncada.vigentes) == 0, [a.apolice_ref for a in truncada.vigentes])


# ===========================================================================
# [GB1c] O PAR — `incluir_vencidas=True` devolve tudo
# ===========================================================================
def gate_GB1c():
    _p("\n[GB1c] O PAR -- `incluir_vencidas=True` devolve TUDO (o filtro e escolha)")
    for nome, caso in sorted(listagens_reais().items()):
        inteira = listar(caso, incluir_vencidas=True)
        devolvidas = min(int(caso["documents_count"]), int(caso["matches_devolvidos"]))
        check("[GB1c] %s: com incluir_vencidas=True voltam as %d linhas lidas"
              % (nome, devolvidas),
              len(inteira.itens) == devolvidas,
              "itens=%d esperado=%d" % (len(inteira.itens), devolvidas))
        check("[GB1c] %s: e o historico_oculto cai para o que a FONTE truncou" % nome,
              inteira.historico_oculto == int(caso["documents_count"]) - devolvidas,
              inteira.historico_oculto)
    doze = casos_sinteticos()["doze_com_a_vigente_na_11"]
    inteira = listar(doze, incluir_vencidas=True)
    check("[GB1c] o caso de 12: com incluir_vencidas=True voltam as 12",
          len(inteira.itens) == 12 and inteira.historico_oculto == 0,
          "itens=%d oculto=%d" % (len(inteira.itens), inteira.historico_oculto))


# ===========================================================================
# [GB1d] O STATUS — `"ativo"` numa vencida nao a torna vigente
# ===========================================================================
def gate_GB1d():
    _p("\n[GB1d] O STATUS -- `policy_status` e SINAL, nunca veredito")
    caso = casos_sinteticos()["uma_vencida_marcada_ativa"]
    inteira = listar(caso, incluir_vencidas=True)
    por_ref = {a.apolice_ref: a for a in inteira.itens}
    vencida = por_ref.get("infocap:1:N1")
    check("[GB1d] a fixture tem uma apolice com status 'ativo' e fim em 2021",
          caso["apolices"][0]["status_cru_do_fornecedor"] == "ativo"
          and caso["apolices"][0]["fim"] == "01/01/2021",
          caso["apolices"][0])
    check("[GB1d] 🔴 ela e classificada VENCIDA (a DATA decide)",
          vencida is not None and vencida.vigencia.situacao == "VENCIDA",
          vencida.vigencia.situacao if vencida else None)
    check("[GB1d] e o status cru sobrevive como SINAL, para o corretor ver",
          vencida is not None
          and any(s.codigo == "status_do_fornecedor" for s in vencida.sinais),
          [s.codigo for s in (vencida.sinais if vencida else ())])
    filtrada = listar(caso)
    check("[GB1d] ela NAO entra na resposta filtrada",
          all(a.apolice_ref != "infocap:1:N1" for a in filtrada.itens),
          [a.apolice_ref for a in filtrada.itens])

    cancelada = casos_sinteticos()["uma_cancelada_e_uma_vigente"]
    filtrada2 = listar(cancelada)
    check("[GB1d] PAR: a CANCELADA tambem fica fora, e conta no historico",
          len(filtrada2.itens) == 1 and filtrada2.historico_oculto == 1,
          "itens=%d oculto=%d" % (len(filtrada2.itens), filtrada2.historico_oculto))

    # A capacidade declarada deixou de mentir.
    from app.providers.infocap_policy_provider import InfoCapProvider

    caps = InfoCapProvider().capacidades()
    check("[GB1d] `capacidades().listar_apolices` = SUPORTADA (le a lista inteira)",
          caps.de("listar_apolices") == "SUPORTADA", caps.de("listar_apolices"))


# ===========================================================================
# [GB1e] O NUMERO HUMANO — `policy_number_ambiguous` tambem passa pela escolha
# ===========================================================================
#
# 🔴 A PORTA POR ONDE A VENCIDA AINDA VIRAVA OPCAO, medida em 14/09/2026:
# `infocap_tool._arun` so mandava a resposta para a porta quando **nao** havia
# `policy_number` — e `policy_number_ambiguous` so acontece quando o corretor
# INFORMOU um numero. Os `matches` iam crus do conector para o briefing, com o
# `policy_status` do fornecedor, e o guarda de `nodes.py` obrigava a listar
# todos: uma apolice vencida ha anos voltava a ser oferecida como opcao.
#
# ⚠️ Aqui o desempate NAO pode ser "chame de novo com o numero" — o numero e
# justamente o que esta ambiguo. Quem isola a apolice e a REFERENCIA opaca, pelo
# `detail`. Por isso o duble tem DUAS pontas: `lookup` e `detail`.
def _stub_do_banco():
    """`create_async_supabase_client` dublado — a tool nao abre conexao aqui."""
    import types

    try:
        import app.core.database as banco
    except Exception:  # noqa: BLE001
        banco = types.ModuleType("app.core.database")
        sys.modules["app.core.database"] = banco

    async def _sem_banco(*a, **k):
        return None

    banco.create_async_supabase_client = _sem_banco   # type: ignore[attr-defined]
    if not hasattr(banco, "get_supabase_client"):
        banco.get_supabase_client = lambda *a, **k: None   # type: ignore[attr-defined]


def _chamar_com_numero(caso, numero):
    """A tool REAL, com `policy_number` e a fonte devolvendo `policy_number_ambiguous`."""
    from app.agents.tools import infocap_tool as tool_mod
    from app.providers import policy_data_provider as porta
    from app.providers.infocap_policy_provider import InfoCapProvider

    _stub_do_banco()
    # ⚠️ A tool recusa antes de tudo sem chave interna. ⛔ Sintetica, e sem rede.
    os.environ.setdefault("BACKEND_INTERNAL_API_KEY", "chave-de-teste-sem-rede")
    # 🔴 O caminho de PRODUCAO e o briefing da v2. Com a flag desligada a tool
    #    cai no resumo legado — outro texto, outro guarda. Aqui se mede o que o
    #    corretor recebe hoje.
    os.environ["POLICY_INTELLIGENCE_V2"] = "true"
    bruto = resposta_do_conector(caso)
    bruto["status"] = "policy_number_ambiguous"
    # 🔴 O numero humano e o MESMO nas duas linhas: e o que produz o status.
    for linha in bruto["matches"] + bruto["policies_all"]:
        linha["policy_number"] = numero

    provider = InfoCapProvider()
    chamadas = {"lookup": [], "detail": []}

    async def _lookup(**kw):
        chamadas["lookup"].append(kw.get("policy_number"))
        return dict(bruto)

    async def _detail(**kw):
        ref = kw.get("policy_ref")
        chamadas["detail"].append(ref)
        escolhida = next((m for m in bruto["policies_all"]
                          if m["policy_locator_ref"] == ref), None)
        if escolhida is None:
            return {"ok": False, "status": "policy_number_not_found"}
        return {
            "ok": True, "status": "found",
            "documents_count": bruto["documents_count"],
            "selected": dict(escolhida), "matches": [dict(escolhida)],
            "policy_evidence_pack": {
                "coverage_sections": [{"label": "Cobertura de teste", "amount": "R$ 1.000,00"}],
                "policy_status": escolhida["policy_status"],
                "valid_from": escolhida["valid_from"], "valid_to": escolhida["valid_to"],
            },
        }

    async def _vehicle(**kw):
        return {"ok": False}

    provider.lookup = _lookup      # type: ignore[method-assign]
    provider.detail = _detail      # type: ignore[method-assign]
    provider.vehicle = _vehicle    # type: ignore[method-assign]

    original = porta.get_policy_data_provider
    porta.get_policy_data_provider = lambda *a, **k: provider   # type: ignore[assignment]
    try:
        ferramenta = tool_mod.InfocapPolicyLookupTool(
            company_id="tenant-de-teste", agent_role="core")
        saida = asyncio.run(ferramenta._arun(
            document="[CPF]", policy_number=numero,
            user_query="me manda a apolice %s" % numero))
    finally:
        porta.get_policy_data_provider = original   # type: ignore[assignment]
    return saida, chamadas


def gate_GB1e():
    _p("\n[GB1e] O NUMERO -- `policy_number_ambiguous` passa pela escolha da porta")
    casos = casos_sinteticos()

    # ① 1 vigente + 1 vencida com o MESMO numero humano -> a vigente, sozinha.
    uma_e_uma = casos["uma_vencida_marcada_ativa"]
    saida, chamadas = _chamar_com_numero(uma_e_uma, "AP-IGUAL")
    dado = saida.get("data") or {}
    briefing = str(saida.get("content") or "")
    check("[GB1e] 🔴 1 vigente + 1 vencida com o mesmo numero -> `found`, nao lista",
          str(dado.get("status") or "") == "found", (dado.get("status"), chamadas))
    check("[GB1e] e a escolhida e a VIGENTE por DATA (a segunda linha)",
          (dado.get("selected") or {}).get("policy_locator_ref") == "infocap:1:N2",
          (dado.get("selected") or {}).get("policy_locator_ref"))
    check("[GB1e] o desempate foi pela REFERENCIA opaca, nao pelo numero",
          chamadas["detail"] == ["infocap:1:N2"], chamadas)
    check("[GB1e] e a resposta DIZ por que e aquela",
          bool(str(dado.get("auto_selected_reason") or "").strip()),
          dado.get("auto_selected_reason"))
    check("[GB1e] a vencida NAO aparece no briefing como opcao",
          "apolices_com_o_mesmo_numero" not in briefing, briefing[:400])
    medir("vencidas_oferecidas_por_numero_ambiguo",
          0 if "apolices_com_o_mesmo_numero" not in briefing else 1)

    # ② O PAR: 2 VIGENTES com o mesmo numero -> a pergunta e LEGITIMA.
    duas = casos["duas_auto_vigentes"]
    saida2, chamadas2 = _chamar_com_numero(duas, "AP-IGUAL")
    dado2 = saida2.get("data") or {}
    briefing2 = str(saida2.get("content") or "")
    check("[GB1e] PAR: 2 VIGENTES com o mesmo numero -> continua ambiguo",
          str(dado2.get("status") or "") == "policy_number_ambiguous",
          (dado2.get("status"), chamadas2))
    check("[GB1e] PAR: e as DUAS entram nas opcoes",
          len(dado2.get("matches") or []) == 2,
          [(m.get("policy_locator_ref"), m.get("valid_to"))
           for m in (dado2.get("matches") or [])])
    check("[GB1e] PAR: o briefing lista as duas, pelo texto JA CLASSIFICADO da porta",
          "apolices_com_o_mesmo_numero" in briefing2
          and "Status: VIGENTE" in briefing2, briefing2[:700])
    check("[GB1e] PAR: e nenhuma linha impressa carrega o status cru do fornecedor",
          "Status: ativo" not in briefing2, briefing2[:700])


GATES = {
    "GB1a": gate_GB1a,
    "GB1b": gate_GB1b,
    "GB1c": gate_GB1c,
    "GB1d": gate_GB1d,
    "GB1e": gate_GB1e,
}


# ===========================================================================
# AS MUTACOES — cada uma em COPIA, em SUBPROCESSO, com restauracao no finally
# ===========================================================================
MUTACOES = [
    # M-B1a: o filtro de vigencia desligado -> a vencida volta a ser opcao, que e
    #        exatamente o que o acervo de 09-11/09 mostrou 24 vezes.
    ("M-B1a", "app/providers/infocap_policy_provider.py",
     "    itens = lidas if incluir_vencidas else elegiveis",
     "    itens = lidas",
     "GB1a"),
    # M-B1b: `listar_apolices` volta a ler `matches` (truncado em 10) -> o caso de
    #        12 perde a unica vigente, em silencio.
    ("M-B1b", "app/providers/infocap_policy_provider.py",
     '    fonte = inteira if isinstance(inteira, list) and inteira else (bruto.get("matches") or [])',
     '    fonte = bruto.get("matches") or []',
     "GB1b"),
    # M-B1c: `historico_oculto` derivado de len(matches) -> diz "1 ocultada"
    #        quando sao 10, e a ocultacao deixa de ser honesta.
    ("M-B1c", "app/providers/infocap_policy_provider.py",
     '    total = int(bruto.get("documents_count") or len(lidas))',
     "    total = len(lidas)",
     "GB1a"),
    # 🔴 M-B1e: a escolha volta a rodar SO quando nao ha `policy_number` — e
    #        `policy_number_ambiguous` so acontece quando HA. E a porta por onde
    #        a vencida continuava virando opcao depois de toda a SPEC.
    ("M-B1e", "app/agents/tools/infocap_tool.py",
     '            elif policy_number and str(result.get("status") or "") == "policy_number_ambiguous":',
     '            elif False:',
     "GB1e"),
    # M-B1d: `policy_status` volta a decidir a vigencia -> a apolice "ativo" de
    #        2021 vira resposta.
    ("M-B1d", "app/providers/policy_data_provider.py",
     "    if d_fim is not None and d_fim < referencia:",
     '    if str(inicio or "") == "__nunca__" and d_fim is not None and d_fim < referencia:',
     "GB1d"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.join(RAIZ, relativo)
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    calado = "--medir" in args
    if not calado:
        _p("=" * 78)
        _p("  M-B1 -- VENCIDA NUNCA VIRA OPCAO  (SPEC-EXTRA-001.1 BLOCO B)")
        _p("=" * 78)
    _bloquear_a_rede()
    try:
        for gid, fn in GATES.items():
            if so and gid != so:
                continue
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                import traceback
                check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                      "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-900:]))
    finally:
        _devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_vencida_nunca_vira_opcao():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())

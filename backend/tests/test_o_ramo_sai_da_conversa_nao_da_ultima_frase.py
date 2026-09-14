# -*- coding: utf-8 -*-
r"""M-B3 — O RAMO SAI DA CONVERSA, NAO DA ULTIMA FRASE. SPEC-EXTRA-001.1 B, GATE B3.

```
"meu carro quebrou"  (2 mensagens antes)  +  "[CPF]"  (agora)   ->  auto
"preciso de um chaveiro, fiquei trancado fora de casa"          ->  resi
"chaveiro, perdi a chave do carro"                              ->  auto
"chaveiro"  sozinho, 1 auto + 1 resi vigentes                    ->  pergunta UMA vez
```

📊 **Medido em 14/09/2026, antes desta mudanca:** `"preciso de um chaveiro,
fiquei trancado fora de casa"` devolvia **`"auto"`**. A palavra `chaveiro`
estava so em `_AUTO_INTENT_RE`, e `_product_hint_from_query` RETORNAVA na
primeira condicao que casasse. Acrescentar `chaveiro` ao regex de residencial
**sem** mudar isso nao mudaria nada — e e exatamente por isso que este guarda
mede o MOTOR, nao o regex (CLAUDE.md §9.4).

📊 **E o outro lado:** `nodes.py` concatenava as 3 ultimas mensagens humanas
**so** para `attendance`/`insured_external`; no Chat Principal (`core`) a tool
recebia a ULTIMA frase. Era por isso que "so o CPF" chegava sem ramo nenhum, e
a auto-selecao — trancada atras de `self._client_facing` — nem rodava para o
corretor.

```
 [GB3a] O MOTOR     as frases reais pelo `_product_hint_from_query`, ja desempatado
 [GB3b] A JANELA    o trecho REAL de `nodes.py` monta as 3 humanas para TODOS os papeis
 [GB3c] O PAPEL     `_arun` com papel `core` AUTO-SELECIONA (o `_client_facing` saiu)
 [GB3d] O EMPATE    `chaveiro` sozinho, 1 auto + 1 resi -> pergunta, uma vez
```

⛔ SEGURANCA: `SEM_REDE=1`, sem banco, sem PII. O provider e DUBLADO; as frases
vem do corpus real, com `[CPF]` no lugar do documento.

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_ramo_sai_da_conversa_nao_da_ultima_frase.py
    ... --so GB3c   ·   ... --medir   ·   ... --mutar [M-B3a]
"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import types
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
TESTES = os.path.join(RAIZ, "tests")
HARNESS = os.path.join(TESTES, "test_vencida_nunca_vira_opcao.py")
NODES = os.path.join(RAIZ, "app", "agents", "nodes.py")
CORPUS = os.path.join(TESTES, "corpus", "perguntas_do_chat", "2026-09-09_10.json")

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")
os.environ.setdefault("BACKEND_INTERNAL_API_KEY", "chave-de-teste-sem-rede")

HOJE = date(2026, 9, 14)

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
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:600] if detalhe else ""))
    return bool(cond)


def medir(chave, valor):
    MEDIDAS[chave] = valor
    return valor


def _carregar(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)   # type: ignore[union-attr]
    return mod


_H = _carregar("_harness_mb1", HARNESS)
_H._bloquear_a_rede()

resposta_do_conector = _H.resposta_do_conector
casos_sinteticos = _H.casos_sinteticos


# ===========================================================================
# [GB3a] O MOTOR — as frases reais, pela funcao do produto
# ===========================================================================
#: 🔴 O texto vem do ACERVO, nao da imaginacao (CLAUDE.md §9.4). As frases de
#: servico sao as do incidente 2026-07-11/12 e as do corpus de 09-11/09; o CPF
#: vira `[CPF]`, como no corpus.
FRASES = [
    # (frase, familia esperada, por que)
    ("meu carro quebrou | preciso de ajuda | [CPF]", "auto",
     "as 3 ultimas humanas concatenadas como `nodes.py` faz: o pedido veio 2 mensagens antes do CPF"),
    ("[CPF]", None,
     "so o CPF, sem nenhuma palavra de ramo: nao ha o que deduzir, e a lista decide"),
    ("preciso de um chaveiro, fiquei trancado fora de casa", "resi",
     "🔴 o defeito medido: devolvia `auto` porque `chaveiro` so estava no regex de auto"),
    ("chaveiro, perdi a chave do carro", "auto",
     "a mesma palavra, o contexto oposto"),
    ("chaveiro", None,
     "sozinha, a palavra nao decide: o desempate desce para a contagem de vigentes"),
    ("vazamento na cozinha, preciso de encanador", "resi",
     "④ o servico pedido: encanador -> residencial"),
    ("meu carro quebrou, preciso de um guincho", "auto",
     "④ o servico pedido: guincho -> auto"),
    ("Preciso de informacoes de coberturas completas da apolice residencial com cpf [CPF]", "resi",
     "① ramo explicito no pedido (q6 do corpus real)"),
    ("QUERO SABER QUAIS SAO AS COBERTURAS DETALHADAS DA APOLICE. RESIDENCIAL DA HDI... [CPF]", "resi",
     "① ramo explicito em caixa alta (q7 do corpus real)"),
]


def gate_GB3a():
    _p("\n[GB3a] O MOTOR -- as frases reais pelo `_product_hint_from_query`")
    from app.agents.tools.infocap_tool import (
        _AUTO_INTENT_RE,
        _RESI_INTENT_RE,
        _product_hint_from_query,
        _ramos_sinalizados,
    )

    # A FORMA da declaracao (excecao legitima da §9.4): `chaveiro` nos DOIS.
    check("[GB3a] `chaveiro` esta no regex de AUTO", bool(_AUTO_INTENT_RE.search("chaveiro")))
    check("[GB3a] `chaveiro` esta TAMBEM no regex de RESIDENCIAL",
          bool(_RESI_INTENT_RE.search("chaveiro")))

    acertos = 0
    for frase, esperado, porque in FRASES:
        obtido = _product_hint_from_query(frase)
        ok = obtido == esperado
        acertos += int(ok)
        check("[GB3a] %r -> %r  (%s)" % (frase[:52], esperado, porque[:60]), ok,
              "obtido=%r sinalizados=%r" % (obtido, _ramos_sinalizados(frase)))
    medir("frases_com_ramo_correto", "%d/%d" % (acertos, len(FRASES)))

    # 🔴 O par que prova que a funcao NAO retorna na primeira condicao: as duas
    #    familias sao sinalizadas, e o veredito muda com o CONTEXTO.
    casa = _ramos_sinalizados("preciso de um chaveiro, fiquei trancado fora de casa")
    carro = _ramos_sinalizados("chaveiro, perdi a chave do carro")
    check("[GB3a] 🔴 nas duas frases as DUAS familias sao sinalizadas",
          set(casa) >= {"auto", "resi"} and set(carro) >= {"auto", "resi"}, (casa, carro))
    check("[GB3a] e mesmo assim o veredito e OPOSTO (o desempate existe)",
          _product_hint_from_query("preciso de um chaveiro, fiquei trancado fora de casa") == "resi"
          and _product_hint_from_query("chaveiro, perdi a chave do carro") == "auto")

    corpus = json.load(io.open(CORPUS, encoding="utf-8"))
    com_ramo = [q for q in corpus["perguntas"] if q.get("ramo_esperado")]
    check("[GB3a] o corpus real declara ramo esperado em 5 das 7 perguntas",
          len(com_ramo) == 5, len(com_ramo))


# ===========================================================================
# [GB3b] A JANELA — o trecho REAL de `nodes.py`, executado
# ===========================================================================
def _trecho_da_janela():
    """Recorta de `nodes.py` o bloco que monta `user_query` da tool.

    🔴 O recorte NAO e a assercao: ele e o caminho ate o codigo do PRODUTO, que
    e EXECUTADO logo abaixo. Se o recorte falhar, o bloco diz por que — nunca
    finge medir.
    """
    fonte = io.open(NODES, encoding="utf-8").read().splitlines()
    inicio = next((i for i, l in enumerate(fonte)
                   if l.strip() == 'elif tool_name == "infocap_policy_lookup":'), None)
    if inicio is None:
        return None, "`nodes.py` nao tem mais o ramo `elif tool_name == \"infocap_policy_lookup\"`"
    fim = next((j for j in range(inicio + 1, len(fonte))
                if fonte[j].strip().startswith("elif tool_name")), None)
    if fim is None:
        return None, "nao achei o proximo `elif tool_name` que fecha o bloco"
    corpo = "\n".join(fonte[inicio + 1:fim])
    return textwrap.dedent(corpo), None


class _Humana:
    type = "human"

    def __init__(self, content):
        self.content = content


def _rodar_a_janela(corpo, papel, mensagens, ficha=None):
    ambiente = {
        "tool_name": "infocap_policy_lookup",
        "tool_args": {"document": "[CPF]"},
        "messages": mensagens,
        "current_user_query": mensagens[-1].content if mensagens else "",
        "agent_data": {"agent_role": papel},
        "state": {"infocap_policy_context": ficha},
        "HumanMessage": _Humana,
        "extract_text_from_content": lambda c: c if isinstance(c, str) else str(c or ""),
    }
    exec(compile(corpo, "<nodes.py:infocap_policy_lookup>", "exec"), ambiente)  # noqa: S102
    return ambiente["tool_args"]


def gate_GB3b():
    _p("\n[GB3b] A JANELA -- as 3 ultimas humanas, para TODOS os papeis")
    corpo, porque = _trecho_da_janela()
    if not check("[GB3b] o recorte do trecho REAL de `nodes.py` funcionou", corpo is not None, porque):
        return

    mensagens = [_Humana("meu carro quebrou"), _Humana("preciso de ajuda"), _Humana("[CPF]")]
    esperado = "meu carro quebrou | preciso de ajuda | [CPF]"

    for papel in ("core", "attendance", "insured_external", ""):
        args = _rodar_a_janela(corpo, papel, mensagens)
        check("[GB3b] papel %r recebe as 3 humanas concatenadas" % (papel or "(vazio)"),
              args.get("user_query") == esperado, args.get("user_query"))

    # 🔴 O ELO: a janela chega na DEDUCAO. Duas medicoes certas nao fazem uma
    #    causa certa — aqui o `user_query` que `nodes.py` monta e entregue a
    #    `_product_hint_from_query`, e e ELE que produz "auto".
    from app.agents.tools.infocap_tool import _product_hint_from_query

    args_core = _rodar_a_janela(corpo, "core", mensagens)
    check("[GB3b] 🔴 O ELO: o `user_query` montado por `nodes.py` deduz `auto` no `core`",
          _product_hint_from_query(args_core["user_query"]) == "auto",
          args_core["user_query"])
    check("[GB3b] PAR: so a ULTIMA frase ('[CPF]') nao deduziria ramo nenhum",
          _product_hint_from_query("[CPF]") is None)

    # ② a ficha do atendimento viaja junto.
    com_ficha = _rodar_a_janela(corpo, "core", mensagens,
                                ficha={"selected_policy_number": "AP-2"})
    check("[GB3b] a apolice ja confirmada no caso viaja para a tool",
          com_ficha.get("selected_policy_number") == "AP-2", com_ficha)
    sem_ficha = _rodar_a_janela(corpo, "core", mensagens, ficha=None)
    check("[GB3b] PAR: sem ficha, o campo vai `None` (nunca string vazia)",
          sem_ficha.get("selected_policy_number") is None, sem_ficha)
    medir("papeis_com_janela_de_3", 4)


# ===========================================================================
# [GB3c]/[GB3d] O PAPEL e O EMPATE — a tool REAL, com o provider dublado
# ===========================================================================
def _stubar_o_banco():
    """`create_async_supabase_client` dublado — a tool nao abre conexao aqui.

    ⚠️ O modulo REAL e preservado e so a funcao e trocada. Substituir o modulo
    inteiro por um stub derrubava o gate rodado sozinho (`--so GB3d`) com
    `ImportError: cannot import name 'get_supabase_client'` — e um guarda que
    so passa quando roda acompanhado nao guarda nada (CLAUDE.md §9.3).
    """
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


def _provider_de_duas_pontas(caso):
    """O provider REAL com o `lookup` dublado nas DUAS chamadas.

    1a (sem `policy_number`) -> a resposta ambigua com `policies_all` inteiro.
    2a (com `policy_number`) -> o `found`, com `selected` e um pack minimo.

    ⚠️ `listar_apolices`, `escolher_apolice` e `_product_hint_from_query` sao os
    do produto: e o caminho inteiro da tool que este gate mede.
    """
    from app.providers.infocap_policy_provider import InfoCapProvider

    provider = InfoCapProvider()
    ambigua = resposta_do_conector(caso)
    chamadas = []

    async def _lookup(**kwargs):
        chamadas.append(kwargs.get("policy_number"))
        numero = kwargs.get("policy_number")
        if not numero:
            return dict(ambigua)
        escolhida = next((m for m in ambigua["policies_all"] if m["policy_number"] == numero), None)
        if escolhida is None:
            return dict(ambigua)
        return {
            "ok": True, "status": "found",
            "documents_count": ambigua["documents_count"],
            "selected": dict(escolhida),
            "matches": [dict(escolhida)],
            "policy_evidence_pack": {
                "coverage_sections": [{"label": "Cobertura de teste", "amount": "R$ 1.000,00"}],
                "policy_status": escolhida["policy_status"],
                "valid_from": escolhida["valid_from"], "valid_to": escolhida["valid_to"],
            },
        }

    async def _vehicle(**kwargs):
        return {"ok": False}

    provider.lookup = _lookup      # type: ignore[method-assign]
    provider.vehicle = _vehicle    # type: ignore[method-assign]
    return provider, chamadas


def _chamar_a_tool(caso, *, papel, user_query, selected_policy_number=None):
    _stubar_o_banco()
    from app.agents.tools import infocap_tool as tool_mod
    from app.providers import policy_data_provider as porta

    provider, chamadas = _provider_de_duas_pontas(caso)
    original = porta.get_policy_data_provider
    porta.get_policy_data_provider = lambda *a, **k: provider   # type: ignore[assignment]
    try:
        ferramenta = tool_mod.InfocapPolicyLookupTool(company_id="tenant-de-teste", agent_role=papel)
        saida = asyncio.run(ferramenta._arun(
            document="[CPF]", user_query=user_query,
            selected_policy_number=selected_policy_number,
        ))
    finally:
        porta.get_policy_data_provider = original   # type: ignore[assignment]
    return saida, chamadas


def gate_GB3c():
    _p("\n[GB3c] O PAPEL -- o `core` AUTO-SELECIONA (o `_client_facing` saiu da condicao)")
    caso = casos_sinteticos()["uma_auto_uma_resi"]
    query = "meu carro quebrou | preciso de ajuda | [CPF]"

    for papel in ("core", "attendance", "insured_external"):
        saida, chamadas = _chamar_a_tool(caso, papel=papel, user_query=query)
        dados = saida.get("data") or {}
        check("[GB3c] papel %r: a tool chega em `found` (nao devolve lista)" % papel,
              dados.get("status") == "found", (dados.get("status"), chamadas))
        check("[GB3c] papel %r: houve uma 2a chamada com o numero escolhido" % papel,
              len(chamadas) == 2 and chamadas[1] == "AP-1", chamadas)
        check("[GB3c] papel %r: e a escolhida e a de AUTO" % papel,
              (dados.get("selected") or {}).get("product") == "AUTO",
              (dados.get("selected") or {}).get("product"))
        check("[GB3c] papel %r: o `data` carrega o PORQUE da escolha" % papel,
              bool(str(dados.get("auto_selected_reason") or "").strip()),
              dados.get("auto_selected_reason"))
    medir("papeis_que_auto_selecionam", 3)

    # O briefing que vai ao modelo diz o porque e o historico oculto.
    saida, _ = _chamar_a_tool(casos_sinteticos()["duas_auto_mais_uma_resi_vencida"],
                              papel="core", user_query="quero a apolice do carro | [CPF]")
    conteudo = str(saida.get("content") or "")
    dados = saida.get("data") or {}
    check("[GB3c] 2 auto vigentes: a tool PERGUNTA (o par do `found`)",
          dados.get("status") in ("ambiguous_policy", "policy_number_ambiguous"),
          dados.get("status"))
    check("[GB3c] 🔴 e as opcoes vem JA FILTRADAS: 2, nunca 3 (a resi vencida fora)",
          len(dados.get("matches") or []) == 2,
          [(m.get("policy_number"), m.get("product")) for m in (dados.get("matches") or [])])
    check("[GB3c] o briefing declara o `historico_oculto` ao modelo",
          "historico_oculto: 1" in conteudo, conteudo[:400])

    # A ficha (② na ordem de precedencia) vence a deducao por texto.
    saida_ficha, chamadas_ficha = _chamar_a_tool(
        casos_sinteticos()["uma_auto_uma_resi"], papel="core",
        user_query="meu carro quebrou | [CPF]", selected_policy_number="AP-2")
    check("[GB3c] ② a apolice ja confirmada no caso vence o ramo deduzido",
          chamadas_ficha[1:] == ["AP-2"], chamadas_ficha)
    check("[GB3c] e o resultado e a residencial, porque foi ELA que o caso confirmou",
          ((saida_ficha.get("data") or {}).get("selected") or {}).get("product") == "RESI",
          ((saida_ficha.get("data") or {}).get("selected") or {}).get("product"))


def gate_GB3d():
    _p("\n[GB3d] O EMPATE -- `chaveiro` sozinho, 1 auto + 1 resi -> pergunta UMA vez")
    caso = casos_sinteticos()["uma_auto_uma_resi"]

    saida, chamadas = _chamar_a_tool(caso, papel="attendance", user_query="chaveiro")
    dados = saida.get("data") or {}
    check("[GB3d] `chaveiro` sozinho nao decide: a tool pergunta",
          dados.get("status") == "ambiguous_policy", (dados.get("status"), chamadas))
    check("[GB3d] e NAO houve 2a chamada (nao se escolheu no chute)",
          len(chamadas) == 1, chamadas)
    check("[GB3d] as 2 opcoes oferecidas estao vigentes",
          len(dados.get("matches") or []) == 2,
          [(m.get("policy_number"), m.get("product")) for m in (dados.get("matches") or [])])

    # O PAR: a mesma palavra, com contexto -> resolve sem perguntar.
    for query, produto in (("chaveiro, fiquei trancado fora de casa", "RESI"),
                           ("chaveiro, perdi a chave do carro", "AUTO")):
        saida, chamadas = _chamar_a_tool(caso, papel="attendance", user_query=query)
        dados = saida.get("data") or {}
        check("[GB3d] PAR: %r -> %s, sem perguntar" % (query[:38], produto),
              dados.get("status") == "found"
              and (dados.get("selected") or {}).get("product") == produto,
              (dados.get("status"), (dados.get("selected") or {}).get("product")))

    # 🔴 O DESEMPATE PELA CONTAGEM DE VIGENTES, e o unico caso em que ele decide:
    #    `chaveiro` sinaliza auto E residencial; o cliente tem uma AUTO e uma de
    #    CONDOMINIO vigentes. So `auto` esta entre as sinalizadas e tem vigente.
    auto_e_cond = casos_sinteticos()["uma_auto_uma_cond"]
    saida, chamadas = _chamar_a_tool(auto_e_cond, papel="attendance", user_query="chaveiro")
    dados = saida.get("data") or {}
    check("[GB3d] 🔴 `chaveiro` com 1 auto + 1 condominio vigentes -> escolhe a AUTO",
          dados.get("status") == "found"
          and (dados.get("selected") or {}).get("product") == "AUTO",
          (dados.get("status"), (dados.get("selected") or {}).get("product"), chamadas))
    check("[GB3d] PAR: sem palavra nenhuma de ramo, o MESMO cliente faz perguntar",
          ((_chamar_a_tool(auto_e_cond, papel="attendance", user_query="[CPF]")[0]
            .get("data") or {}).get("status")) == "ambiguous_policy")

    # 🔴 O caso sem vigente: a tool devolve a frase da §6.2, nao "nao encontrei".
    saida, _ = _chamar_a_tool(casos_sinteticos()["sem_vigente_tres_vencidas"],
                              papel="core", user_query="[CPF]")
    dados = saida.get("data") or {}
    conteudo = str(saida.get("content") or "")
    check("[GB3d] 0 vigentes: a tool devolve `sem_vigente`",
          dados.get("status") == "sem_vigente", dados.get("status"))
    check("[GB3d] e o texto e a frase da §6.2, com a ultima vigente e a data",
          "14/08/2026" in conteudo and "histórico" in conteudo, conteudo[:300])
    check("[GB3d] nenhuma opcao e oferecida (vencida nunca vira opcao)",
          (dados.get("matches") or []) == [], dados.get("matches"))
    contrato = saida.get("policy_response_contract") or {}
    check("[GB3d] e o contrato nao exige listagem nenhuma",
          "policy_options" not in (contrato.get("required_facts") or [])
          and (contrato.get("policy_options") or []) == [],
          (contrato.get("required_facts"), contrato.get("policy_options")))


GATES = {
    "GB3a": gate_GB3a,
    "GB3b": gate_GB3b,
    "GB3c": gate_GB3c,
    "GB3d": gate_GB3d,
}


MUTACOES = [
    # M-B3a: `_product_hint_from_query` restaurado -- retorna na 1a condicao que
    #        casa. "chaveiro, fiquei trancado fora de casa" volta a ser AUTO.
    ("M-B3a", "app/agents/tools/infocap_tool.py",
     "    familias = _ramos_sinalizados(query)\n"
     "    if not familias:\n"
     "        return None\n"
     "    if len(familias) == 1:\n"
     "        return familias[0]\n"
     "    return _desempatar_pelo_contexto(query, familias)",
     '    texto = str(query or "")\n'
     "    if _AUTO_INTENT_RE.search(texto):\n"
     '        return "auto"\n'
     "    if _RESI_INTENT_RE.search(texto):\n"
     '        return "resi"\n'
     "    return None",
     "GB3a"),
    # M-B3b: `self._client_facing` de volta na condicao da auto-selecao -- o
    #        corretor volta a receber a lista e o segurado nao.
    ("M-B3b", "app/agents/tools/infocap_tool.py",
     '            if not policy_number and str(result.get("status") or "") in _STATUS_SEM_ESCOLHA:',
     '            if self._client_facing and not policy_number and str(result.get("status") or "") in _STATUS_SEM_ESCOLHA:',
     "GB3c"),
    # M-B3c: a janela das 3 humanas volta a valer so para atendimento -- o `core`
    #        recebe a ultima frase, e "so o CPF" fica sem ramo.
    ("M-B3c", "app/agents/nodes.py",
     '                        _query_for_tool = " | ".join([t for t in _recent_humans[-3:] if t]) or current_user_query',
     '                        _role = str((agent_data or {}).get("agent_role") or "").lower()\n'
     '                        _query_for_tool = (" | ".join([t for t in _recent_humans[-3:] if t])\n'
     '                                           if _role in ("attendance", "insured_external")\n'
     "                                           else current_user_query)",
     "GB3b"),
    # M-B3d: `chaveiro` sai do regex de residencial -- o desempate por contexto
    #        continua existindo, mas a familia resi nem chega a ser sinalizada.
    ("M-B3d", "app/agents/tools/infocap_tool.py",
     '    r"|eletrodom[ée]stic|chaveiro",',
     '    r"|eletrodom[ée]stic",',
     "GB3a"),
    # M-B3e: o desempate pela contagem de VIGENTES some -- "chaveiro" sozinho num
    #        cliente com uma unica vigente voltaria a perguntar sem necessidade.
    ("M-B3e", "app/agents/tools/infocap_tool.py",
     "        return com_vigente[0] if len(com_vigente) == 1 else None",
     "        return None",
     "GB3d"),
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
        _p("  M-B3 -- O RAMO SAI DA CONVERSA, NAO DA ULTIMA FRASE  (BLOCO B)")
        _p("=" * 78)
    try:
        for gid, fn in GATES.items():
            if so and gid != so:
                continue
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                import traceback
                check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                      "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-1200:]))
    finally:
        _H._devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_o_ramo_sai_da_conversa_nao_da_ultima_frase():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())

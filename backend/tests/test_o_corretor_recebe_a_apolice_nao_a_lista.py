# -*- coding: utf-8 -*-
r"""M-C1 — O CORRETOR RECEBE A APOLICE, NAO A LISTA. SPEC-EXTRA-001.1 BLOCO C.

```
as 7 perguntas REAIS de 09-11/09  ->  7 de 7 chegam a `found` em UMA rodada
                                      0 briefings mandam listar apolices
                                      7 de 7 dizem POR QUE a apolice e aquela
2 vigentes do MESMO ramo         ->  a lista VOLTA, e o guarda de `nodes.py`
                                      anula a resposta que esconder uma delas
```

📊 **O numero que motivou este guarda** (BLOCO 0, consulta de 14/09/2026 sobre
`messages` de 09-11/09/2026): **7 respostas com lista**, **31 linhas de opcao**,
**24 delas com fim de vigencia PASSADO**, **7 de 7** perguntaram *"qual delas?"*
e **0 de 7** responderam com a unica vigente.

🔴 **O PAR DE CONTROLE e o que da direito a conclusao** (CLAUDE.md §9.5): a
mesma tool, o mesmo motor, a mesma forma de listagem — e o veredito OPOSTO. Sem
o par, "para de listar" tanto pode ser a regra certa quanto um `return found`
posto no lugar errado.

```
 [GC1a] AS 7          o corpus real pelo MOTOR: 7/7 `found`, 0 listagens, 7/7 com o porque
 [GC1b] O PAR         2 auto vigentes -> a lista volta, e o guarda de nodes.py a protege
 [GC1c] A LINHA :273  o comportamento MEDIDO, antes e depois (protocolo §0.4)
 [GC1d] OS PROMPTS    `\bInfoCap\b` = 0 · `CorpAPI` = 0 · a regra de vigencia no CORE
 [GC1e] O CATALOGO    a familia de acionamento sai do ARQUIVO, nao do prompt
```

⚠️ **O teste chama o MOTOR**, nunca o regex (CLAUDE.md §9.4): `_arun` da tool
REAL com o provider REAL e so a VIAGEM dublada, `_build_llm_briefing` de
verdade, `_guard_infocap_policy_final_response` de verdade. O harness das duas
pontas e o do M-B3 — **um so montador, nunca dois**.

⛔ SEGURANCA: `SEM_REDE=1`, `socket.connect` bloqueado, sem banco, sem PII (as
perguntas do corpus ja vem com `[CPF]`/`[CNPJ]`/`[NOME]`).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_corretor_recebe_a_apolice_nao_a_lista.py
    ... --so GC1b   ·   ... --medir   ·   ... --mutar [M-C1a]
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
TESTES = os.path.join(RAIZ, "tests")
HARNESS = os.path.join(TESTES, "test_o_ramo_sai_da_conversa_nao_da_ultima_frase.py")
CORPUS = os.path.join(TESTES, "corpus", "perguntas_do_chat", "2026-09-09_10.json")
PROMPTS = os.path.join(RAIZ, "app", "core", "prompts.py")
CATALOGO = os.path.normpath(os.path.join(
    RAIZ, "..", "docs", "canon", "providers", "susep", "seguradora-coenti.json"))

if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"
os.environ.setdefault("POLICY_INTELLIGENCE_V2", "true")
os.environ.setdefault("BACKEND_INTERNAL_API_KEY", "chave-de-teste-sem-rede")

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


# 🔴 UM harness, nao dois: `_chamar_a_tool` / `_provider_de_duas_pontas` sao os
#    do M-B3, e sao eles que ja provaram medir o caminho INTEIRO da tool.
_H3 = _carregar("_harness_mb3", HARNESS)

chamar_a_tool = _H3._chamar_a_tool
casos_sinteticos = _H3.casos_sinteticos
listagens_reais = _H3._H.listagens_reais


def corpus():
    with io.open(CORPUS, encoding="utf-8") as fh:
        return json.load(fh)


def ler(caminho):
    with io.open(caminho, encoding="utf-8") as fh:
        return fh.read()


#: 🔴 O briefing tem DUAS metades, e confundi-las e um guarda que nunca fica
#: vermelho: em cima os DADOS da consulta, embaixo as REGRAS de redacao. A regra
#: 3 **nomeia** `apolices_vigentes_do_mesmo_ramo` (é a condicao dela), entao
#: procurar o token no texto inteiro daria "manda listar" em 7 de 7 briefings —
#: 📊 aconteceu na primeira rodada deste guarda, em 14/09/2026.
_FIM_DOS_DADOS = ("\nREGRAS OBRIGATORIAS DA RESPOSTA FINAL:", "\nCOMO USAR (voce e o ATENDENTE")


def bloco_de_dados(briefing):
    """So a metade de CIMA do briefing: o que a consulta devolveu."""
    texto = str(briefing or "")
    corte = min([texto.find(m) for m in _FIM_DOS_DADOS if m in texto] or [len(texto)])
    return texto[:corte]


def manda_listar(briefing):
    """O briefing traz o BLOCO das opcoes (nao a regra que o menciona)?"""
    return "apolices_vigentes_do_mesmo_ramo (a porta NAO conseguiu escolher" in bloco_de_dados(briefing)


# ===========================================================================
# AS LISTAGENS DAS 7 PERGUNTAS
# ===========================================================================
#
# 🔴 Tres delas vem do GOLDEN real (`golden_apolices_extra0011.json`), uma da
# fixture sintetica do BLOCO B, e TRES sao RECONSTRUIDAS aqui — e a diferenca
# esta escrita, porque reconstrucao nao e medicao (CLAUDE.md §12.1).
#
# 📊 O que o acervo guardou de q1/q2/q3 foi a COMPOSICAO (total, vigentes,
# vencidas, canceladas) e o ramo do pedido, em `apolices_no_acervo` do corpus —
# nao as linhas. A reconstrucao usa EXATAMENTE esses numeros: se alguem mexer no
# corpus sem mexer aqui, `_conferir_a_composicao` fica vermelho.
_ANO = 2026


def _linha(seguradora, ramo, inicio, fim, *, cancelado=False, status="ativo"):
    return {"seguradora_abrev": seguradora, "ramo_abrev": ramo,
            "inicio": inicio, "fim": fim, "cancelado": cancelado,
            "status_cru_do_fornecedor": status}


def _reconstruida(ramo, *, vigentes, vencidas, canceladas, seguradora="PORT"):
    """Uma listagem com a COMPOSICAO medida — vigente primeiro, historico depois.

    ⚠️ `status_cru_do_fornecedor` e **"ativo"** tambem nas vencidas de proposito:
    📊 e o que a fonte devolve de verdade (as 3 residenciais do golden dizem
    "ativo" e so uma esta vigente). Uma fixture "honesta" esconderia o defeito.
    """
    apolices = []
    for i in range(vigentes):
        apolices.append(_linha(seguradora, ramo, "01/03/2026", "01/03/2027"))
    for i in range(vencidas):
        ano = _ANO - 1 - i
        apolices.append(_linha(seguradora, ramo, "01/03/%d" % ano, "01/03/%d" % (ano + 1)))
    for i in range(canceladas):
        apolices.append(_linha(seguradora, ramo, "01/03/2026", "01/03/2027", cancelado=True))
    return {"documents_count": len(apolices), "matches_devolvidos": min(len(apolices), 10),
            "status": "ambiguous_policy", "apolices": apolices}


def listagens_das_perguntas():
    golden = listagens_reais()
    sinteticas = casos_sinteticos()
    dados = corpus()
    por_id = {q["id"]: q for q in dados["perguntas"]}

    def recon(qid, ramo, seguradora="PORT"):
        conta = por_id[qid]["apolices_no_acervo"]
        return _reconstruida(ramo, vigentes=conta["vigentes"], vencidas=conta["vencidas"],
                             canceladas=conta["canceladas"], seguradora=seguradora)

    return {
        # RECONSTRUIDAS da composicao medida no acervo
        "q1": (recon("q1", "AUTO"), "reconstruida da composicao do acervo (4/1/2/1)"),
        "q2": (recon("q2", "AUTO"), "reconstruida da composicao do acervo (2/1/1/0)"),
        "q3": (recon("q3", "AUTO"), "reconstruida da composicao do acervo (3/1/2/0)"),
        # REAIS, do golden montado pela porta no BLOCO 0
        "q4": (golden["empresa_11_apolices"], "GOLDEN real: 11 apolices, a fonte devolve 10"),
        "q5": (golden["condominio_allianz"], "GOLDEN real: 6 condominio, 1 vigente"),
        # SINTETICA do BLOCO B (o golden guardou 1 match: a consulta foi por numero)
        "q6": (sinteticas["q6_pessoa_6_apolices"], "fixture do BLOCO B: 6 apolices, 2 vigentes de ramos DIFERENTES"),
        "q7": (sinteticas["q6_pessoa_6_apolices"], "a mesma pessoa da q6; a pergunta nomeia seguradora e ramo"),
    }


def _vigentes_de(caso, hoje=None):
    """Quantas linhas da listagem estao VIGENTES — pela PORTA, nao por data crua."""
    from app.providers.policy_data_provider import classificar_vigencia

    from datetime import date
    dia = hoje or date(2026, 9, 14)
    return sum(1 for a in caso["apolices"]
               if classificar_vigencia(a["inicio"], a["fim"], a["cancelado"],
                                       hoje=dia).situacao == "VIGENTE")


# ===========================================================================
# [GC1a] AS 7 PERGUNTAS REAIS — pelo MOTOR, em UMA rodada
# ===========================================================================
def gate_GC1a():
    _p("\n[GC1a] AS 7 -- o corpus real de 09-11/09 pela tool REAL, papel `core`")
    dados = corpus()
    check("[GC1a] o corpus tem as 7 perguntas reais e a linha de CONTROLE",
          len(dados["perguntas"]) == 7 and len(dados.get("controle") or []) == 1,
          (len(dados["perguntas"]), len(dados.get("controle") or [])))
    check("[GC1a] 📊 e o acervo registra o defeito que se conserta: 7 listaram, 0 responderam",
          dados["acervo"]["respostas_que_perguntaram_qual"] == 7
          and dados["acervo"]["respostas_com_a_unica_vigente_em_1_rodada"] == 0,
          dados["acervo"])

    listagens = listagens_das_perguntas()
    por_id = {q["id"]: q for q in dados["perguntas"]}

    # A composicao reconstruida BATE com a que o acervo mediu — se o corpus
    # mudar e esta fixture nao, o guarda fica vermelho em vez de mentir.
    for qid in ("q1", "q2", "q3"):
        caso, _ = listagens[qid]
        conta = por_id[qid]["apolices_no_acervo"]
        check("[GC1a] %s: a listagem reconstruida bate com a composicao medida (%d/%d)"
              % (qid, conta["total"], conta["vigentes"]),
              len(caso["apolices"]) == conta["total"]
              and _vigentes_de(caso) == conta["vigentes"],
              (len(caso["apolices"]), _vigentes_de(caso), conta))

    achadas = 0
    com_porque = 0
    com_lista = 0
    for qid in ("q1", "q2", "q3", "q4", "q5", "q6", "q7"):
        caso, procedencia = listagens[qid]
        pergunta = por_id[qid]["texto"]
        saida, chamadas = chamar_a_tool(caso, papel="core", user_query=pergunta)
        dado = saida.get("data") or {}
        briefing = str(saida.get("content") or "")
        status = str(dado.get("status") or "")
        if status == "found":
            achadas += 1
        if str(dado.get("auto_selected_reason") or "").strip():
            com_porque += 1
        if manda_listar(briefing):
            com_lista += 1
        check("[GC1a] %s (%s): a tool chega em `found`, sem perguntar" % (qid, procedencia[:34]),
              status == "found", (status, chamadas, briefing[:220]))
        check("[GC1a] %s: o briefing NAO manda listar apolices" % qid,
              not manda_listar(briefing), bloco_de_dados(briefing)[:400])
        check("[GC1a] %s: e a resposta DIZ por que e aquela apolice" % qid,
              bool(str(dado.get("auto_selected_reason") or "").strip())
              and "apolice_escolhida_porque" in briefing,
              dado.get("auto_selected_reason"))
        check("[GC1a] %s: uma rodada — a 2a chamada e pelo numero JA escolhido" % qid,
              len(chamadas) == 2 and chamadas[0] is None and bool(chamadas[1]),
              chamadas)

    medir("perguntas_do_corpus_em_found", achadas)
    medir("perguntas_do_corpus_com_o_porque", com_porque)
    medir("briefings_que_mandam_listar", com_lista)
    check("[GC1a] 🔴 7 de 7 em UMA rodada (o acervo mediu 0 de 7)", achadas == 7, achadas)
    check("[GC1a] 🔴 0 de 7 mandam listar apolice (o acervo mediu 7 de 7)", com_lista == 0, com_lista)
    check("[GC1a] 🔴 7 de 7 dizem por que", com_porque == 7, com_porque)

    # 🔴 A REGRA que sai do briefing e a que ENTRA no lugar dela.
    caso, _ = listagens["q5"]
    saida, _ = chamar_a_tool(caso, papel="core", user_query=por_id["q5"]["texto"])
    briefing = str(saida.get("content") or "")
    check("[GC1a] o cabecalho `opcoes_de_apolice (liste TODAS…)` SUMIU do briefing",
          "opcoes_de_apolice" not in briefing, briefing[:400])
    check("[GC1a] PAR-DO-DETECTOR: ele acha o BLOCO das opcoes quando ele existe",
          manda_listar("apolices_vigentes_do_mesmo_ramo (a porta NAO conseguiu escolher: x)")
          and not manda_listar("3. Se o bloco trouxer apolices_vigentes_do_mesmo_ramo, liste-as"))
    check("[GC1a] e a regra 3 passou a PROIBIR a listagem fora da ambiguidade",
          "NUNCA liste apolices" in briefing
          and "Se houver opcoes_de_apolice" not in briefing,
          briefing[-1400:])
    check("[GC1a] 🔴 a regra 1b das COBERTURAS continua byte a byte (a armadilha da §7.2)",
          "1b. Se houver coberturas_item_a_item, LISTE TODAS (nenhuma de fora), cada uma com "
          "limite, franquia e premio" in briefing,
          briefing[-1400:])

    # LINHA DE CONTROLE: a pergunta que NAO e de apolice nao passa por aqui.
    controle = (dados.get("controle") or [{}])[0]
    from app.agents.tools.infocap_tool import _product_hint_from_query
    check("[GC1a] CONTROLE: a pergunta que nao e de apolice nao sinaliza ramo nenhum",
          _product_hint_from_query(controle.get("texto")) is None,
          controle.get("texto"))


# ===========================================================================
# [GC1b] O PAR — 2 vigentes do MESMO ramo: a lista VOLTA, e o guarda a protege
# ===========================================================================
def gate_GC1b():
    _p("\n[GC1b] O PAR -- 2 auto vigentes: a unica situacao em que perguntar e legitimo")
    from app.agents import nodes

    caso = casos_sinteticos()["duas_auto_vigentes"]
    saida, _ = chamar_a_tool(caso, papel="core", user_query="quero a apolice do carro | [CPF]")
    dado = saida.get("data") or {}
    briefing = str(saida.get("content") or "")
    contrato = saida.get("policy_response_contract") or {}
    opcoes = contrato.get("policy_options") or []

    check("[GC1b] a porta devolve `ambiguous_policy` (o par do `found` da GC1a)",
          str(dado.get("status") or "") == "ambiguous_policy", dado.get("status"))
    check("[GC1b] e AGORA o briefing traz o bloco das vigentes do mesmo ramo",
          manda_listar(briefing), briefing[:500])
    numeros = [str(o.get("policy_number") or "").strip() for o in opcoes if isinstance(o, dict)]
    medir("opcoes_na_ambiguidade", len(numeros))
    check("[GC1b] as 2 opcoes estao no contrato, com os numeros exatos",
          len(numeros) == 2 and all(n in briefing for n in numeros), (numeros, briefing[:500]))
    check("[GC1b] `policy_options` entra em `required_facts` SO aqui",
          "policy_options" in (contrato.get("required_facts") or []),
          contrato.get("required_facts"))

    # 🔴 VENCIDA NUNCA E OPCAO — nem no briefing, nem no contrato.
    from app.providers.policy_data_provider import classificar_vigencia
    from datetime import date
    situacoes = [classificar_vigencia(o.get("valid_from"), o.get("valid_to"),
                                      o.get("cancelled"), hoje=date(2026, 9, 14)).situacao
                 for o in opcoes if isinstance(o, dict)]
    medir("opcoes_vencidas_no_contrato", sum(1 for s in situacoes if s != "VIGENTE"))
    check("[GC1b] 🔴 nenhuma opcao do contrato esta vencida ou cancelada",
          situacoes and all(s == "VIGENTE" for s in situacoes), situacoes)
    check("[GC1b] e o briefing mostra a situacao pela DATA, nunca o status cru da fonte",
          "VIGENTE" in briefing and "Recebido e nao entregue" not in briefing,
          briefing[:600])

    # GC4 da proposta §7: o guarda de `nodes.py` continua anulando a omissao.
    guarda = nodes._guard_infocap_policy_final_response
    esconde = "Encontrei a apolice %s da seguradora. Seguir com ela?" % numeros[0]
    cita = ("Este cliente tem 2 apolices vigentes de auto: seguradora e numero %s, e a outra "
            "com numero %s. Qual delas?" % (numeros[0], numeros[1]))
    check("[GC1b] 🔴 GC4: o guarda ANULA a resposta que esconde uma opcao legitima",
          guarda(esconde, contrato) == str(contrato.get("rendered_safe_answer") or ""),
          guarda(esconde, contrato)[:200])
    check("[GC1b] GC4 (o par): e ACEITA a resposta que cita as duas",
          guarda(cita, contrato) == cita, guarda(cita, contrato)[:200])

    # 🔴 E O CASO QUE PEGA A REGRESSAO: 2 auto VIGENTES + 1 residencial VENCIDA.
    #    Sem uma vencida na listagem, um `policy_options` que parasse de filtrar
    #    daria o MESMO resultado — e a mutacao M-C1c ficaria verde por falta de
    #    material. 📊 Foi o que aconteceu na 1a rodada deste guarda (14/09/2026),
    #    com `duas_auto_vigentes`: 2 opcoes antes e 2 depois.
    com_vencida = casos_sinteticos()["duas_auto_mais_uma_resi_vencida"]
    saida_v, _ = chamar_a_tool(com_vencida, papel="core", user_query="quero a apolice do carro | [CPF]")
    contrato_v = saida_v.get("policy_response_contract") or {}
    opcoes_v = [o for o in (contrato_v.get("policy_options") or []) if isinstance(o, dict)]
    situacoes_v = [classificar_vigencia(o.get("valid_from"), o.get("valid_to"),
                                        o.get("cancelled"), hoje=date(2026, 9, 14)).situacao
                   for o in opcoes_v]
    medir("opcoes_com_uma_vencida_na_listagem", len(opcoes_v))
    check("[GC1b] 🔴 com 3 apolices (2 vigentes + 1 VENCIDA), o contrato traz 2 opcoes",
          len(opcoes_v) == 2, [(o.get("policy_number"), o.get("valid_to")) for o in opcoes_v])
    check("[GC1b] 🔴 e nenhuma delas e a vencida",
          situacoes_v == ["VIGENTE", "VIGENTE"], situacoes_v)
    briefing_v = str(saida_v.get("content") or "")
    check("[GC1b] o briefing tambem lista 2, e diz que ha 1 no historico",
          bloco_de_dados(briefing_v).count("\n1. ") == 1
          and bloco_de_dados(briefing_v).count("\n2. ") == 1
          and "\n3. " not in bloco_de_dados(briefing_v)
          and "historico_oculto: 1" in briefing_v,
          bloco_de_dados(briefing_v)[:600])

    # E o par do lado do `found`: com a apolice escolhida, nao ha o que exigir.
    saida_ok, _ = chamar_a_tool(casos_sinteticos()["uma_auto_uma_resi"], papel="core",
                                user_query="meu carro quebrou | [CPF]")
    contrato_ok = saida_ok.get("policy_response_contract") or {}
    check("[GC1b] PAR: com `found`, `policy_options` vem VAZIO e nao e exigido",
          not (contrato_ok.get("policy_options") or [])
          and "policy_options" not in (contrato_ok.get("required_facts") or []),
          (contrato_ok.get("policy_options"), contrato_ok.get("required_facts")))
    resposta_livre = "A apolice do carro e a AP-1, da Porto Seguro, vigente ate 04/05/2027."
    check("[GC1b] PAR: e o guarda DEIXA PASSAR a resposta que fala de UMA apolice",
          guarda(resposta_livre, contrato_ok) == resposta_livre,
          guarda(resposta_livre, contrato_ok)[:200])


# ===========================================================================
# [GC1c] A LINHA `nodes.py:273` — MEDIDA antes de ser tocada (protocolo §0.4)
# ===========================================================================
def gate_GC1c():
    _p("\n[GC1c] A LINHA :273 -- `if not options and (...)`: o que ela FAZ, medido")
    from app.agents import nodes

    guarda = nodes._guard_infocap_policy_final_response
    contrato = {"provider": "infocap", "result_kind": "ambiguous_policy",
                "rendered_safe_answer": "RASCUNHO SEGURO",
                "required_facts": ["policy_options"], "policy_options": []}

    # 📊 A MATRIZ MEDIDA em 14/09/2026, ANTES do conserto. Ela nao mudou depois
    #    dele: os parenteses escreveram a precedencia real, sem mudar o veredito.
    #    `A and (B or (C and D))` -> so passa quem cita seguradora E numero.
    matriz = [
        ("nem seguradora nem numero", "Posso ajudar com a apolice do cliente.", "ANULA"),
        ("so seguradora", "A seguradora e a ALLI, escolha uma.", "ANULA"),
        ("so numero", "O numero da apolice e AP-1.", "ANULA"),
        ("so numero com acento", "O número da apólice e AP-1.", "ANULA"),
        ("seguradora + numero", "Seguradora ALLI, numero AP-1.", "ACEITA"),
        ("seguradora + número", "Seguradora ALLI, número AP-1.", "ACEITA"),
    ]
    medido = {}
    for nome, texto, esperado in matriz:
        anulou = guarda(texto, contrato) == "RASCUNHO SEGURO"
        medido[nome] = "ANULA" if anulou else "ACEITA"
        check("[GC1c] :273 com `policy_options` vazio — %s -> %s" % (nome, esperado),
              medido[nome] == esperado, medido[nome])
    medir("linha_273_anula_de_6_casos", sum(1 for v in medido.values() if v == "ANULA"))

    # 🔴 E o que MUDOU: `required_facts` so carrega `policy_options` quando a
    #    porta devolveu ambiguidade. Fora disso a linha nao e nem alcancada.
    contrato_found = {"provider": "infocap", "result_kind": "found",
                      "rendered_safe_answer": "RASCUNHO SEGURO", "required_facts": []}
    livre = "A apolice vigente e a AP-1 e cobre o que voce perguntou."
    check("[GC1c] 🔴 com `found` a linha nem e alcancada: a resposta livre passa",
          guarda(livre, contrato_found) == livre, guarda(livre, contrato_found)[:200])

    # A linha existe com os PARENTESES escritos e o motivo ao lado (§0.4).
    fonte = ler(os.path.join(RAIZ, "app", "agents", "nodes.py"))
    check("[GC1c] a precedencia esta ESCRITA no codigo, nao deduzida pelo leitor",
          "if not (cita_seguradora and cita_numero):" in fonte
          and "cita_numero = (\"numero\" in lower) or (\"número\" in lower)" in fonte)
    check("[GC1c] e o `and`/`or` de precedencia duvidosa sumiu",
          'if not options and ("seguradora" not in lower' not in fonte)


# ===========================================================================
# [GC1d] OS PROMPTS — a fronteira e a regra de vigencia
# ===========================================================================
def gate_GC1d():
    _p("\n[GC1d] OS PROMPTS -- `\\bInfoCap\\b` = 0, `CorpAPI` = 0, a regra de vigencia no CORE")
    import re

    fonte = ler(PROMPTS)
    prosa = re.compile(r"\bInfoCap\b")            # 🔴 SEM re.IGNORECASE, de proposito
    linhas = [i for i, l in enumerate(fonte.split("\n"), 1) if prosa.search(l)]
    medir("infocap_em_prosa_nos_prompts", len(linhas))
    medir("corpapi_nos_prompts", fonte.count("CorpAPI"))
    check("[GC1d] 🔴 nenhuma mencao em PROSA ao fornecedor (hoje eram 7 linhas)",
          not linhas, linhas)
    check("[GC1d] `CorpAPI` continua 0", fonte.count("CorpAPI") == 0)
    # O PAR de controle da allowlist ESCRITA: o IDENTIFICADOR da tool FICA.
    check("[GC1d] PAR: o identificador `infocap_policy_lookup` FICA (allowlist escrita)",
          "infocap_policy_lookup" in fonte)
    check("[GC1d] PAR: e o detector nao o confunde com prosa",
          not prosa.search("CHAME a ferramenta infocap_policy_lookup")
          and bool(prosa.search("- Se a InfoCap respondeu, repasse.")))

    from app.core.prompts import ATTENDANCE_BASE_PROMPT, CORE_BASE_PROMPT

    check("[GC1d] 🔴 o `CORE_BASE_PROMPT` ganhou a regra de vigencia, em UMA frase",
          "APÓLICE VIGENTE" in CORE_BASE_PROMPT
          and "duas ou mais vigentes do MESMO ramo" in CORE_BASE_PROMPT
          and "vencida só entra na resposta se ele pedir o histórico" in CORE_BASE_PROMPT,
          CORE_BASE_PROMPT[1200:1900])
    check("[GC1d] e ela diz por que e aquela apolice (`apolice_escolhida_porque`)",
          "apolice_escolhida_porque" in CORE_BASE_PROMPT)

    # 🔴 As QUATRO instrucoes do `ATTENDANCE_BASE_PROMPT` que NAO podem sumir
    #    (proposta §7.4.2). O guarda le o TEXTO: sao regras, nao linhas.
    quatro = [
        ("Mais de uma apólice vigente? ESCOLHA VOCÊ", "a regra que a SPEC estende ao `core`"),
        ("Ela vale até o FIM do atendimento", "a escolha do cliente nao se repete"),
        ("NUNCA escreva placeholders técnicos", "o placeholder tecnico nao vai ao segurado"),
        ("só ofereça as com vigência ATUAL", "o texto que virou comportamento da porta"),
    ]
    for trecho, porque in quatro:
        check("[GC1d] ATTENDANCE mantem: %s (%s)" % (trecho[:44], porque),
              trecho in ATTENDANCE_BASE_PROMPT)
    check("[GC1d] 🔴 e a do placeholder ganhou a CONDICAO (so com 2+ vigentes do mesmo ramo)",
          "vale SÓ quando a ferramenta devolver 2+ apólices vigentes do MESMO ramo"
          in ATTENDANCE_BASE_PROMPT,
          ATTENDANCE_BASE_PROMPT[ATTENDANCE_BASE_PROMPT.find("placeholders"):][:320])


# ===========================================================================
# [GC1e] O CATALOGO — a familia de acionamento sai do ARQUIVO, nao do prompt
# ===========================================================================
def gate_GC1e():
    _p("\n[GC1e] O CATALOGO -- Liberty/Yelum e Itau/Porto viram linha de arquivo revisado")
    from app.providers.susep_ses_provider import (
        UNKNOWN, familia_de_acionamento, linha_de_acionamento,
    )

    check("[GC1e] `LIBE` (a sigla REAL do censo) -> yelum", familia_de_acionamento("LIBE") == "yelum")
    check("[GC1e] `ITAU` (a sigla REAL do censo) -> porto", familia_de_acionamento("ITAU") == "porto")
    check("[GC1e] `PORT` -> porto", familia_de_acionamento("PORT") == "porto")
    check("[GC1e] sem acento e sem caixa: `Itaú` -> porto", familia_de_acionamento("Itaú") == "porto")
    # 🔴 O PAR DE CONTROLE: uma seguradora SEM familia declarada sai UNKNOWN —
    #    nunca um palpite. E `SURA` e o caso medido da 094.1 (casa dentro de
    #    "ASSURANCE" por derivacao de string).
    check("[GC1e] PAR: `HDI` nao tem familia declarada -> UNKNOWN",
          familia_de_acionamento("HDI") == UNKNOWN)
    check("[GC1e] PAR: `SURA` nao vira `porto` por derivacao de string",
          familia_de_acionamento("SURA") == UNKNOWN)
    check("[GC1e] cada linha traz o CRITERIO escrito ao lado",
          bool(str((linha_de_acionamento("LIBE") or {}).get("criterio") or "").strip())
          and bool(str((linha_de_acionamento("ITAU") or {}).get("criterio") or "").strip()))

    # 🔴 E o ELO: a linha do BRIEFING vem do CATALOGO, nao de um dict no prompt.
    caso = {"documents_count": 1, "matches_devolvidos": 1, "status": "ambiguous_policy",
            "apolices": [_linha("LIBE", "AUTO", "01/03/2026", "01/03/2027")]}
    saida, _ = chamar_a_tool(caso, papel="attendance", user_query="meu carro quebrou | [CPF]")
    briefing = str(saida.get("content") or "")
    check("[GC1e] 🔴 o briefing de uma apolice Liberty diz o corredor do acionamento",
          "seguradora_para_acionamento: yelum" in bloco_de_dados(briefing),
          bloco_de_dados(briefing)[:700])
    check("[GC1e] e o conhecimento SAIU do texto do prompt (item 5 do bloco do segurado)",
          "Liberty e Yelum sao a MESMA seguradora" not in briefing
          and "Itau = grupo Porto" not in briefing,
          briefing[-1600:])
    check("[GC1e] o item 5 passou a APONTAR para o dado, em vez de repetir a regra",
          "seguradora_para_acionamento" in briefing.split("COMO USAR")[-1], briefing[-1600:])

    # PAR: a mesma tool, uma seguradora SEM familia -> a linha nao aparece.
    caso_hdi = {"documents_count": 1, "matches_devolvidos": 1, "status": "ambiguous_policy",
                "apolices": [_linha("HDI", "RESI", "01/03/2026", "01/03/2027")]}
    saida_hdi, _ = chamar_a_tool(caso_hdi, papel="attendance", user_query="tem vazamento em casa | [CPF]")
    check("[GC1e] PAR: sem familia declarada, o briefing NAO inventa corredor",
          "seguradora_para_acionamento:" not in bloco_de_dados(saida_hdi.get("content")),
          bloco_de_dados(saida_hdi.get("content"))[:700])

    # O arquivo e revisavel por gente: tem `_doc`, data e criterio por linha.
    catalogo = json.load(io.open(CATALOGO, encoding="utf-8"))
    check("[GC1e] o catalogo declara `_doc`, `medido_em` e criterio por linha",
          bool(catalogo.get("_doc_familias_de_acionamento"))
          and bool(catalogo.get("medido_em_familias"))
          and all(isinstance(v, dict) and v.get("criterio") and v.get("corredor")
                  for v in (catalogo.get("familias_de_acionamento") or {}).values()),
          list((catalogo.get("familias_de_acionamento") or {}).keys()))
    check("[GC1e] e as siglas usadas sao as REAIS do censo `/seguradoras`",
          all(s in (catalogo.get("siglas") or {})
              for s in ("LIBE", "ITAU", "PORT")))


GATES = {
    "GC1a": gate_GC1a,
    "GC1b": gate_GC1b,
    "GC1c": gate_GC1c,
    "GC1d": gate_GC1d,
    "GC1e": gate_GC1e,
}


# ===========================================================================
# AS MUTACOES — por COPIA, em SUBPROCESSO. A arvore precisa estar parada.
# ===========================================================================
#: ⚠️ (mid, caminho relativo a `backend/`, de, para, gate, efeito)
#: `efeito` = "vermelho" (a mutacao TEM de quebrar o gate) ou "verde" (o PAR DE
#: CONTROLE: uma mudanca parecida que NAO pode quebrar nada).
MUTACOES = [
    # M-C1a: a ordem INCONDICIONAL de listar apolices volta ao bloco do corretor.
    #        🔴 E o defeito de 09-11/09 reintroduzido palavra por palavra.
    ("M-C1a", "app/agents/tools/infocap_tool.py",
     '"3. Se o bloco trouxer apolices_vigentes_do_mesmo_ramo, liste-as com os numeros exatos '
     'e peca a escolha UMA vez; fora disso, NUNCA liste apolices — responda sobre a escolhida '
     'e diga por que e ela (apolice_escolhida_porque). Apolice vencida so entra se o corretor '
     'pedir o historico.",',
     '"3. Se houver opcoes_de_apolice, liste TODAS com os numeros exatos e peca a escolha.",',
     "GC1a", "vermelho"),
    # M-C1c: `policy_options` volta a ser populado com a lista CRUA — vencidas
    #        incluidas. 📊 24 das 31 linhas do acervo tinham vigencia passada.
    ("M-C1c", "app/agents/tools/infocap_tool.py",
     '            filtradas = [m for m in crus if str(m.get("policy_locator_ref") or "") in refs]',
     '            filtradas = list(crus)',
     "GC1b", "vermelho"),
    # M-C1d: o nome do fornecedor volta ao `CORE_BASE_PROMPT`, em PROSA.
    ("M-C1d", "app/core/prompts.py",
     "- Seja transparente: deixe claro quando algo for recomendação",
     "- Se a InfoCap respondeu, repasse. Seja transparente: deixe claro quando algo for recomendação",
     "GC1d", "vermelho"),
    # 🔴 M-C1d-PAR: o PAR DE CONTROLE que a proposta §10 exige. O IDENTIFICADOR
    #    da ferramenta numa linha nova NAO e vazamento — e o guarda tem de saber
    #    a diferenca, senao obriga um cutover de catalogo fora de escopo.
    ("M-C1d-PAR", "app/core/prompts.py",
     "- Seja transparente: deixe claro quando algo for recomendação",
     "- Chame `infocap_policy_lookup` quando precisar. Seja transparente: deixe claro quando algo for recomendação",
     "GC1d", "verde"),
    # M-C1e: a linha `yelum` sai do CATALOGO -> a frase do briefing some.
    #        🔴 E o elo: prova que a frase vem do ARQUIVO, e nao de um dict no codigo.
    ("M-C1e", "../docs/canon/providers/susep/seguradora-coenti.json",
     '    "yelum": {\n      "nomes_no_sistema_de_gestao": [\n        "LIBE",',
     '    "yelum_desligada_pela_mutacao": {\n      "nomes_no_sistema_de_gestao": [\n        "ZZZZ",',
     "GC1e", "vermelho"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate, "--medir"],
        cwd=RAIZ, capture_output=True, text=True, timeout=900,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    certas = erradas = 0
    for mid, relativo, de, para, gate, efeito in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            erradas += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0011c").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if efeito == "vermelho":
                if base.returncode == 0 and r.returncode != 0 and falhas:
                    certas += 1
                    _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:180]))
                else:
                    erradas += 1
                    _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                       % (mid, gate, base.returncode, r.returncode, (r.stdout or r.stderr)[-900:]))
            else:
                if base.returncode == 0 and r.returncode == 0:
                    certas += 1
                    _p("  [ok] %s e o PAR DE CONTROLE: %s continua VERDE (a allowlist "
                       "do identificador funciona)" % (mid, gate))
                else:
                    erradas += 1
                    _p("  [FALHOU] %s (PAR DE CONTROLE) deixou %s vermelho — o guarda "
                       "esta medindo a string, nao a PROSA\n%s"
                       % (mid, gate, (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d com o efeito declarado - %d erradas" % (certas, erradas))
    return erradas == 0


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
        _p("  M-C1 -- O CORRETOR RECEBE A APOLICE, NAO A LISTA  (SPEC-EXTRA-001.1 BLOCO C)")
        _p("=" * 78)
    _H3._H._bloquear_a_rede()
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
        _H3._H._devolver_a_rede()

    for chave, valor in sorted(MEDIDAS.items()):
        print("MEDIDA %s %s" % (chave, valor))
    if not calado:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_o_corretor_recebe_a_apolice_nao_a_lista():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())

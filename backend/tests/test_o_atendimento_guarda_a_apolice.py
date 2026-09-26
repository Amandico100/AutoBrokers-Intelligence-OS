# -*- coding: utf-8 -*-
"""SPEC-117 · O TESTE DO FIO — a apólice que o atendimento encontrou fica no caso.

🔴 **Este arquivo atravessa o MOTOR, não uma função parecida** (CLAUDE.md §9.4).
O que roda aqui é `nodes.tool_node` e `nodes.agent_node` REAIS; o dublê está só
na BORDA — a ferramenta que devolveria o que o conector devolveria. E o `data`
do dublê não é imaginado: ele tem a forma que
`infocap_connector._canonical_customer_identity` + `_sanitize_policy` produzem
para o papel `attendance`, e o primeiro teste deste arquivo prova isso chamando
as duas funções REAIS.

📊 **O defeito, medido antes de escrever uma linha de produto** (26/09/2026):

```
$ sed -n 423,425p backend/app/agents/nodes.py
    document = str(data.get("client_document") or "").strip()
    name = str(data.get("client_name") or "").strip()
    if not (document or name) or not policy_numbers:
        return None
```

No papel `attendance` o conector devolve `client_name_masked` /
`client_document_masked` — nunca `client_name` / `client_document`. A porta
devolve `None`, `state.infocap_policy_context` nunca nasce, e TODA regra
pendurada nele (o ramo oficial que vence o palpite do modelo, a apólice que
chega ao portal, o handoff que leva a apólice) está morta no WhatsApp.

📊 E a bancada da SPEC-116 já tinha medido a consequência sem saber nomeá-la:
`contexto_da_apolice_por_turno = [[], [], []]` em **10 de 10** trajetórias N2 do
atendimento, em TODOS os braços — inclusive `duble:perfeito`, que acerta tudo.
Um modelo perfeito não salva um fato que o produto não guarda.

⚠️ **O que este arquivo NÃO afirma:** que o pass@1 de 68,9 % do atendimento sobe.
📊 Classificadas as 13 reprovações do braço de produção no N1 (grupo
`03af4327-80c5-4ec6-b21b-624299cd8542`): **0** são de transporte de apólice, 9
são "não chamou a ferramenta esperada" e 4 são "não pediu o CPF". O N1 é de
turno único — por definição não há o que transportar. Este defeito se mede no
N2, e é lá que os guardas abaixo moram.
"""

import asyncio
import re

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents import nodes as N

# --------------------------------------------------------------------------- #
# O tenant e o cliente do teste — sintéticos, e de DUAS corretoras (CLAUDE.md §7/§13.9)
# --------------------------------------------------------------------------- #
#: ⛔ Nenhum nome de corretora real, nenhum CPF real, nenhum segurado real.
#: 📊 Os UUIDs são fixos para que o teste de dois tenants possa afirmar que a
#: mesma dupla `codfil:codigo` gera chaves DIFERENTES em corretoras diferentes.
TENANT_A = "11111111-1111-4111-8111-111111111111"
TENANT_B = "22222222-2222-4222-8222-222222222222"

#: O documento do cliente sintético. ⚠️ Ele existe aqui para o guarda de PII
#: poder procurá-lo no que sai — nunca para ser transportado.
DOC_SINTETICO = "39053344705"
NOME_SINTETICO = "Cliente De Teste Sintetico"


def _doc_infocap_auto(numero: str = "A-0001") -> dict:
    """Um documento CRU da fonte, do jeito que a InfoCap entrega."""
    return {
        "numapo": numero,
        "nosnum": "900001",
        "codfil": "1",
        "codigo": "7788",
        "seguradora_abrev": "ALLIANZ",
        "ramo_abrev": "AUTO",
        "inivig": "01/03/2026",
        "fimvig": "01/03/2027",
        "cliente": NOME_SINTETICO,
        "cpf_cnpj": DOC_SINTETICO,
        "itens": [{"descricao": "Colisao"}],
    }


def _doc_infocap_resi(numero: str = "R-0002") -> dict:
    d = _doc_infocap_auto(numero)
    d.update({"nosnum": "900002", "ramo_abrev": "RESI",
              "seguradora_abrev": "PORTO", "itens": [{"descricao": "Incendio"}]})
    return d


def _data_do_conector(*, unmasked: bool, docs=None) -> dict:
    """O `data` que a ferramenta devolveria — montado pelas funções REAIS.

    🔴 Este é o ponto que separa este arquivo de um teste de fachada: o `data`
    não é escrito à mão. Ele sai de `_canonical_customer_identity` e
    `_sanitize_policy`, as duas funções do conector que decidem o que o papel vê.
    Se a máscara mudar de forma amanhã, este teste muda com ela — e é ele que
    diz se a mudança apagou o contexto outra vez.
    """
    from app.api.infocap_connector import (_canonical_customer_identity,
                                           _sanitize_policy)

    brutos = docs if docs is not None else [_doc_infocap_auto()]
    identidade = _canonical_customer_identity(brutos[0], brutos[0], unmasked=unmasked)
    apolices = [_sanitize_policy(d, unmasked) for d in brutos]
    return {
        "ok": True,
        "status": "found",
        "source_ref": "infocap:documento",
        "result_count": len(apolices),
        "matched_by": "document",
        "identity_status": "identity_verified",
        **identidade,
        "selected": apolices[0] if len(apolices) == 1 else None,
        "matches": apolices,
    }


class _DubleDaConsulta:
    """A BORDA. Devolve o que a ferramenta real devolveria, e conta as chamadas."""

    name = "infocap_policy_lookup"
    exige_async = True

    def __init__(self, data: dict, content: str = "Localizei a sua apolice."):
        self._data = data
        self.content = content
        self.chamadas: list[dict] = []

    async def _arun(self, **kwargs):
        self.chamadas.append(dict(kwargs))
        return {"ok": True, "found": True, "content": self.content, "data": self._data}

    def _run(self, **kwargs):  # pragma: no cover — o tool_node usa _arun
        raise RuntimeError("use _arun")


class _DubleQueRegistraArgs:
    """Qualquer ferramenta de EFEITO: guarda os argumentos com que foi chamada."""

    exige_async = True

    def __init__(self, name: str, resposta=None):
        self.name = name
        self._resposta = resposta if resposta is not None else {
            "status": "dispatched", "content": "Pedido registrado."}
        self.chamadas: list[dict] = []

    async def _arun(self, **kwargs):
        self.chamadas.append(dict(kwargs))
        return self._resposta

    def _run(self, **kwargs):  # pragma: no cover
        raise RuntimeError("use _arun")


def _estado(company_id: str = TENANT_A, papel: str = "attendance", **extra) -> dict:
    base = {
        "company_id": company_id,
        "user_id": "teste",
        "session_id": f"teste-{company_id[:8]}",
        "company_config": {},
        "agent_data": {"id": None, "agent_role": papel, "tools_config": {}},
        "messages": [],
        "tools_used": [],
        "rag_chunks": [],
        "rag_search_time_ms": 0,
        "infocap_policy_context": None,
        "policy_response_contract": None,
        "internal_steps": [],
    }
    base.update(extra)
    return base


def _pedido_de_tool(nome: str, args: dict, tool_id: str = "call-1"):
    """A AIMessage que o modelo produziria — a entrada real do `tool_node`."""
    return AIMessage(content="", tool_calls=[{"name": nome, "args": args, "id": tool_id}])


def _rodar(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# ELO 1 — a FRONTEIRA: o papel `attendance` mesmo recebe identidade mascarada?
# --------------------------------------------------------------------------- #
def test_a_fronteira_mascara_a_identidade_e_preserva_a_apolice():
    """📊 A premissa da SPEC, medida nas funções REAIS do conector.

    Não é hipótese: é o que `_canonical_customer_identity` e `_sanitize_policy`
    devolvem hoje. ⚠️ E a segunda metade é a que torna a SPEC possível — o que a
    máscara apaga é só a IDENTIDADE; o número, a seguradora, o ramo, a vigência e
    o locator técnico da apólice continuam lá nos DOIS papéis.
    """
    mascarado = _data_do_conector(unmasked=False)
    cru = _data_do_conector(unmasked=True)

    # A máscara funciona — e ela deve continuar funcionando (OWASP LLM02, LGPD).
    assert "client_name" not in mascarado, "o papel do segurado não recebe nome cru"
    assert "client_document" not in mascarado, "o papel do segurado não recebe CPF cru"
    assert mascarado.get("client_name_masked"), "mas recebe a versão mascarada"
    assert cru.get("client_document") == DOC_SINTETICO, "controle: o core recebe cru"

    # E o `client_ref` (codfil:codigo) sai SEM máscara nos dois papéis — é por
    # ele que o produto sabe "é o mesmo cliente" sem tocar em dado pessoal.
    assert mascarado.get("client_ref") == {"codigo": "7788", "codfil": "1"}
    assert mascarado["client_ref"] == cru["client_ref"]

    # A apólice chega INTEIRA no papel mascarado.
    apolice = mascarado["matches"][0]
    assert apolice["policy_number"] == "A-0001"
    assert apolice["insurer_key"] == "ALLIANZ"
    assert apolice["product"] == "AUTO"
    assert apolice["active_now"] is True
    assert apolice["policy_locator_ref"], "o locator técnico existe nos dois papéis"


# --------------------------------------------------------------------------- #
# ELO 2 — O TESTE DO FIO: o contexto NASCE no atendimento?
# --------------------------------------------------------------------------- #
def test_o_contexto_da_apolice_nasce_no_atendimento_mascarado():
    """🔴 O FIO. `tool_node` REAL + a borda com o `data` mascarado REAL.

    Hoje isto nasce VERMELHO: `_safe_infocap_policy_context` exige
    `client_document` ou `client_name` e devolve `None` no papel do segurado.
    """
    duble = _DubleDaConsulta(_data_do_conector(unmasked=False))
    estado = _estado(papel="attendance")
    estado["messages"] = [
        HumanMessage(content="meu carro quebrou, preciso de guincho. CPF %s" % DOC_SINTETICO),
        _pedido_de_tool("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]

    saida = _rodar(N.tool_node(estado, tools=[duble]))

    contexto = saida.get("infocap_policy_context")
    assert contexto, ("o atendimento encontrou a apólice e NÃO a guardou — "
                      "o contexto voltou %r" % (contexto,))
    assert "A-0001" in (contexto.get("policy_numbers") or []), contexto
    assert contexto.get("selected_policy_ramo") == "auto", contexto


def test_linha_de_controle_no_core_o_contexto_ja_nascia():
    """A LINHA DE CONTROLE (CLAUDE.md §9.2). O MESMO fio, o MESMO motor, o
    MESMO documento — só o papel muda. Verde HOJE, e tem de continuar verde:
    é ela que dá direito a dizer que o defeito é da porta de identidade, e não
    da consulta, do dublê ou do `tool_node`."""
    duble = _DubleDaConsulta(_data_do_conector(unmasked=True))
    estado = _estado(papel="core")
    estado["messages"] = [
        HumanMessage(content="cobertura do CPF %s" % DOC_SINTETICO),
        _pedido_de_tool("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]

    saida = _rodar(N.tool_node(estado, tools=[duble]))
    contexto = saida.get("infocap_policy_context")
    assert contexto, "o caminho do core é o que JÁ funciona — se ele cair, o defeito é outro"
    assert contexto.get("selected_policy_ramo") == "auto"


# --------------------------------------------------------------------------- #
# ELO 3 — o RAMO OFICIAL vence o palpite do modelo (D-PILOTO-11, 17/09/2026)
# --------------------------------------------------------------------------- #
def test_o_ramo_oficial_vence_o_palpite_do_modelo_no_atendimento():
    """🔴 O defeito que CHEGA AO SEGURADO (CLAUDE.md §9.5).

    A apólice do cliente é RESIDENCIAL. O modelo escreve `auto` no acionamento.
    A decisão do Founder de 17/09 diz que o ramo do sistema de gestão vence — e
    ela está pendurada em `state.infocap_policy_context`, que no WhatsApp é
    `None`. Resultado de hoje: a seguradora é acionada no ramo ERRADO, em
    silêncio.
    """
    consulta = _DubleDaConsulta(_data_do_conector(unmasked=False, docs=[_doc_infocap_resi()]))
    dispatch = _DubleQueRegistraArgs("insurer_dispatch")

    # Turno 1 — a consulta. O contexto tem de nascer aqui.
    estado = _estado(papel="attendance")
    estado["messages"] = [
        HumanMessage(content="tem um vazamento na minha casa, CPF %s" % DOC_SINTETICO),
        _pedido_de_tool("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    saida1 = _rodar(N.tool_node(estado, tools=[consulta, dispatch]))

    # Turno 2 — o acionamento, com o palpite ERRADO do modelo.
    estado2 = _estado(papel="attendance",
                      infocap_policy_context=saida1.get("infocap_policy_context"))
    estado2["messages"] = [
        HumanMessage(content="sim, pode acionar"),
        _pedido_de_tool("insurer_dispatch",
                        {"subservice": "encanador", "insurer_key": "porto",
                         "ramo_da_apolice": "auto", "dados_confirmados": True},
                        tool_id="call-2"),
    ]
    _rodar(N.tool_node(estado2, tools=[consulta, dispatch]))

    assert dispatch.chamadas, "o acionamento não foi chamado"
    recebido = dispatch.chamadas[-1].get("ramo_da_apolice")
    assert recebido == "resi", (
        "a apólice do cliente é RESIDENCIAL e o acionamento recebeu %r — "
        "o ramo oficial não venceu o palpite do modelo" % (recebido,))


# --------------------------------------------------------------------------- #
# ELO 4 — o fato sobrevive à COMPRESSÃO e a seis turnos
# --------------------------------------------------------------------------- #
def test_a_apolice_sobrevive_a_compressao_da_toolmessage():
    """🔴 G7. O turno da consulta acontece; depois vêm cinco mensagens curtas, a
    `ToolMessage` é comprimida no placeholder e o texto do modelo NÃO repete a
    seguradora. A decisão do turno 6 tem de ser a mesma do turno 1.

    📊 Medido na F6 da SPEC-116: com `POLICY_INTELLIGENCE_V2` desligada,
    *"'Allianz' some da entrada do modelo no turno 2"* — hoje o único
    transportador é o texto que o modelo lembrou de escrever.
    """
    consulta = _DubleDaConsulta(_data_do_conector(unmasked=False, docs=[_doc_infocap_resi()]))
    dispatch = _DubleQueRegistraArgs("insurer_dispatch")

    estado = _estado(papel="attendance")
    estado["messages"] = [
        HumanMessage(content="vazamento em casa, CPF %s" % DOC_SINTETICO),
        _pedido_de_tool("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    contexto = _rodar(N.tool_node(estado, tools=[consulta, dispatch])).get(
        "infocap_policy_context")

    # Cinco turnos curtos: o estado atravessa o `_merge` a cada volta, e nenhum
    # deles traz apólice nova. ⚠️ É aqui que um merge distraído apaga o fato.
    for curto in ("ok", "tá", "e agora?", "certo", "beleza"):
        contexto = N._merge_infocap_policy_context(contexto, None)
        assert contexto, "a mensagem %r apagou a apólice do caso" % curto

    estado6 = _estado(papel="attendance", infocap_policy_context=contexto)
    estado6["messages"] = [
        HumanMessage(content="pode abrir"),
        # O texto do modelo não menciona a seguradora — o placeholder da
        # compressão está no lugar da ToolMessage.
        AIMessage(content="Vou abrir agora."),
        _pedido_de_tool("insurer_dispatch",
                        {"subservice": "encanador", "insurer_key": "porto",
                         "ramo_da_apolice": "auto", "dados_confirmados": True},
                        tool_id="call-6"),
    ]
    _rodar(N.tool_node(estado6, tools=[consulta, dispatch]))

    assert dispatch.chamadas[-1].get("ramo_da_apolice") == "resi", (
        "seis turnos depois, sem a seguradora no texto do modelo, o ramo "
        "oficial tinha de continuar decidindo")
    assert len(consulta.chamadas) == 1, (
        "a apólice guardada não pode causar consulta nova: %d chamadas"
        % len(consulta.chamadas))


# --------------------------------------------------------------------------- #
# ELO 5 — PII: o contexto nasce SEM dado pessoal no papel do segurado
# --------------------------------------------------------------------------- #
_RE_CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")

#: 🔴 O ALVO SÃO OS VALORES, NÃO A SERIALIZAÇÃO — e isso custou um falso vermelho.
#:
#: 📊 26/09/2026: a primeira versão deste guarda comparava as partes do nome
#: contra `json.dumps(contexto)`, que inclui os NOMES DAS CHAVES. O contexto novo
#: tem a chave `cliente_ref` (o pseudônimo opaco) e o valor `sistema_de_gestao`
#: (a origem do campo): `"Cliente"` casava com `cliente_ref` e `"De"` casava com
#: `sistema_de_gestao`. O guarda ficaria VERMELHO sem uma gota de PII no
#: contexto — e um guarda que grita sem motivo é desligado pela próxima pessoa.
#:
#: Duas correções, as duas com razão escrita:
#:   · varre só os VALORES, recursivamente (chave não é dado do cliente);
#:   · parte de nome só conta com 4+ letras — `"De"`, `"Da"`, `"Dos"` são
#:     partículas de nome brasileiro e aparecem em palavra comum do domínio.
#: ⚠️ O CPF continua sendo procurado no texto INTEIRO, sem exceção de tamanho:
#: dígito de documento não tem colisão inocente.
_MIN_LETRAS_DE_NOME = 4


def _valores_em_texto(no) -> str:
    """Todos os VALORES de um dicionário aninhado, concatenados. **PURA.**"""
    if isinstance(no, dict):
        return " ".join(_valores_em_texto(v) for v in no.values())
    if isinstance(no, (list, tuple, set)):
        return " ".join(_valores_em_texto(v) for v in no)
    return str(no)


def _achados_de_pii(contexto: dict) -> list:
    """O que de dado pessoal existe nos VALORES deste contexto. **PURA.**

    Separada do teste de propósito: é ela que o teste de MUTAÇÃO chama para
    provar que o guarda CONSEGUE ficar vermelho (CLAUDE.md §9.3).
    """
    import json as _json

    valores = _valores_em_texto(contexto)
    inteiro = _json.dumps(contexto, ensure_ascii=False, default=str)
    achados = []
    if DOC_SINTETICO in inteiro or _RE_CPF.search(inteiro):
        achados.append("CPF")
    for parte in NOME_SINTETICO.split():
        if len(parte) >= _MIN_LETRAS_DE_NOME and parte.lower() in valores.lower():
            achados.append("nome:%s" % parte)
    if "infocap:" in valores:
        achados.append("locator tecnico cru")
    return achados


def test_o_contexto_do_atendimento_nao_carrega_dado_pessoal():
    """🔴 G2. O contexto que o atendimento guarda não pode conter CPF, nome nem
    locator técnico cru. O alvo é o CONTEÚDO dos valores, recursivamente.
    """
    duble = _DubleDaConsulta(_data_do_conector(unmasked=False))
    estado = _estado(papel="attendance")
    estado["messages"] = [
        HumanMessage(content="CPF %s" % DOC_SINTETICO),
        _pedido_de_tool("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    contexto = _rodar(N.tool_node(estado, tools=[duble])).get("infocap_policy_context")
    assert contexto, "sem contexto não há o que auditar — ver o teste do fio"

    achados = _achados_de_pii(contexto)
    assert not achados, "dado pessoal no contexto do atendimento: %s | %r" % (achados, contexto)

    # E a identidade crua não pode existir NEM como chave no papel do segurado.
    assert "document" not in contexto, contexto
    assert "name" not in contexto, contexto


def test_CONTROLE_o_guarda_de_pii_consegue_ficar_vermelho():
    """🔴 O guarda que não tem como falhar não guarda nada (CLAUDE.md §9.3).

    Três defeitos históricos, reintroduzidos à mão, um por vez. Se qualquer um
    deles passar batido, o guarda acima é carimbo — e este teste é o que prova
    que ele não é.
    """
    limpo = {"versao": 1, "cliente_ref": "ab12cd34", "apolices": [
        {"chave": "ff00", "numapo": "A-0001", "ramo": "auto", "seguradora": "ALLIANZ"}],
        "origem_por_campo": {"ramo": "sistema_de_gestao"}}
    assert _achados_de_pii(limpo) == [], (
        "o contexto LIMPO tem de passar — senão o guarda reprova tudo e não "
        "distingue nada: %r" % (_achados_de_pii(limpo),))

    com_cpf = {**limpo, "document": DOC_SINTETICO}
    com_nome = {**limpo, "apolices": [{**limpo["apolices"][0],
                                      "titular": NOME_SINTETICO}]}
    com_locator = {**limpo, "apolices": [{**limpo["apolices"][0],
                                          "ref": "infocap:1:900001"}]}
    for nome, sujo in (("CPF", com_cpf), ("nome", com_nome), ("locator", com_locator)):
        assert _achados_de_pii(sujo), "o guarda NÃO viu o %s injetado: %r" % (nome, sujo)


# =========================================================================== #
# 🔴 SPEC-117, CONSERTO ÚNICO · B2 — UMA CONSULTA POR MENSAGEM, E SÓ UMA
# =========================================================================== #
#
# 📊 O defeito medido em 26/09/2026, com o dublê PERFEITO (que acerta tudo):
#
#     pytest tests/test_spec116_bancada_gates.py -k linha_de_controle
#        → assert 0.9047619047619048 == 1.0
#        "Efeito DUPLICADO: 1 execução a mais com a mesma chave" (3c0ee80f4a3bf6c0)
#        tool_calls que o MODELO pediu = 1   |   execuções = 2
#
# A causa: `_consulta_forcada_ja_feita_no_turno` só reconhecia a chamada que o
# nó FORÇOU (pelo prefixo do `id`). A que o modelo pediu no mesmo turno não
# contava — e o nó forçava uma segunda ao sistema de gestão da corretora.
#
# ⚠️ Este guarda chama a FUNÇÃO DO MOTOR sobre mensagens REAIS (CLAUDE.md §9.4),
# não uma reimplementação da contagem.
def _ai_com_tool_call(nome: str, tool_id: str):
    return AIMessage(content="", tool_calls=[{"name": nome, "args": {}, "id": tool_id}])


def test_b2_a_consulta_do_MODELO_no_mesmo_turno_ja_conta_como_feita():
    """🔴 A mesma mensagem não dispara DUAS consultas ao sistema de gestão."""
    historico = [
        HumanMessage(content="e a franquia dela?"),
        # o MODELO pediu a consulta: id comum, sem o prefixo da forçada
        _ai_com_tool_call("infocap_policy_lookup", "toolu_01ModeloPediu"),
    ]
    assert N._consulta_forcada_ja_feita_no_turno(historico) is True, (
        "a consulta que o MODELO pediu neste turno não contou — o nó vai forçar "
        "uma segunda à corretora com a mesma pergunta (SPEC-117 G6/G10)")


def test_b2_CONTROLE_a_contagem_consegue_dizer_NAO():
    """🔴 CLAUDE.md §9.3 — um guarda que não tem como falhar não guarda nada.

    Três formas de "ainda não consultei neste turno", e a contagem tem de
    devolver `False` nas três. Sem isto, um `return True` fixo passaria no teste
    de cima e o produto nunca mais consultaria a apólice.
    """
    # (a) nada aconteceu desde a mensagem humana
    assert N._consulta_forcada_ja_feita_no_turno(
        [HumanMessage(content="e a franquia dela?")]) is False
    # (b) o modelo chamou OUTRA ferramenta
    assert N._consulta_forcada_ja_feita_no_turno([
        HumanMessage(content="pode acionar"),
        _ai_com_tool_call("insurer_dispatch", "toolu_02Outra"),
    ]) is False
    # (c) a consulta existe, mas é de ANTES da última mensagem humana — turno novo
    assert N._consulta_forcada_ja_feita_no_turno([
        HumanMessage(content="meu cpf e %s" % DOC_SINTETICO),
        _ai_com_tool_call("infocap_policy_lookup", "toolu_03TurnoAnterior"),
        HumanMessage(content="e a franquia dela?"),
    ]) is False, "a contagem não reiniciou na mensagem humana nova"


def test_b2_a_consulta_FORCADA_pelo_no_continua_contando():
    """A trava antiga não foi substituída, foi ampliada: o `id` da forçada (que
    em históricos reconstruídos pode chegar sem `name`) continua valendo."""
    assert N._consulta_forcada_ja_feita_no_turno([
        HumanMessage(content="e a franquia dela?"),
        AIMessage(content="", tool_calls=[{
            "name": "", "args": {}, "id": N._ID_DA_CONSULTA_FORCADA + "1700000000000"}]),
    ]) is True


# =========================================================================== #
# 🔴 SPEC-117, CONSERTO ÚNICO · B4 — A CONSULTA FORÇADA E O NÚMERO DE TERCEIRO
# =========================================================================== #
def test_b4_numero_que_nao_e_do_cliente_nao_forca_consulta_no_papel_mascarado(monkeypatch):
    """🔴 CROSS-CLIENT. `lookup(policy_number=…)` é busca GLOBAL na base da
    corretora (exata por `numapo`): o contexto que volta pode ser de OUTRO
    cliente e SUBSTITUI a apólice do caso.

    📊 Medido pelo red team em 26/09/2026:
    ```
    tool_args FORCADOS: {'policy_number': '202623140269982', …}
    apolice do caso ANTES: 'A-0001'   DEPOIS: 'Z-9999'
    ficha durável: apolice='Z-9999' ramo='residencial' seguradora='azul'
    ```
    e sem nenhuma má-fé: `'meu cep para o reboque e 01310900, tem cobertura?'`
    → `{'policy_number': '01310900'}`.
    """
    from app.services.policy_context import construir_policy_context

    contexto = construir_policy_context(
        _data_do_conector(unmasked=False, docs=[_doc_infocap_auto()]),
        company_id=TENANT_A, papel="attendance")
    assert contexto and not contexto.get("document"), (
        "controle: no papel do segurado não existe identidade crua")

    # (a) um número que NÃO é de nenhuma apólice deste cliente
    assert N._policy_context_tool_args(
        "quais as coberturas da apolice 202623140269982?", contexto) is None
    # (b) um CEP que a expressão livre confunde com número de apólice
    assert N._policy_context_tool_args(
        "meu cep para o reboque e 01310900, tem cobertura?", contexto) is None

    # 🔴 CONTROLE — e o que a F3.5 ganhou CONTINUA funcionando: a anáfora sobre a
    #    apólice DO CLIENTE força a consulta canônica, com o número dele.
    #    ⚠️ A anáfora sem número depende de `POLICY_INTELLIGENCE_V2` (o gatilho
    #    E1 da SPEC-016.1), e é ela que o produto liga no atendimento.
    monkeypatch.setenv("POLICY_INTELLIGENCE_V2", "1")
    forcada = N._policy_context_tool_args("e a franquia dela?", contexto)
    assert forcada and forcada["policy_number"] == "A-0001", forcada
    do_texto = N._policy_context_tool_args(
        "quais as coberturas da apolice A-0001?", contexto)
    assert do_texto and do_texto["policy_number"] == "A-0001", do_texto
    # e com a flag ligada o número ALHEIO continua recusado
    assert N._policy_context_tool_args(
        "quais as coberturas da apolice 202623140269982?", contexto) is None


def test_b4_CONTROLE_no_papel_core_a_identidade_crua_ainda_abre_a_porta():
    """⚠️ O conserto é na PORTA, não na extração: o Chat Principal (`core`) manda
    o CPF junto, e ali o número é um filtro DENTRO das apólices daquela pessoa.
    Fechar esse caminho seria consertar o defeito errado."""
    from app.services.policy_context import construir_policy_context

    contexto = construir_policy_context(
        _data_do_conector(unmasked=True, docs=[_doc_infocap_auto()]),
        company_id=TENANT_A, papel="core")
    assert contexto.get("document"), "controle: o papel core tem identidade crua"
    args = N._policy_context_tool_args(
        "quais as coberturas da apolice 202623140269982?", contexto)
    assert args and args.get("document"), (
        "no `core` a consulta forçada por número tem de continuar saindo, e com "
        "a identidade do cliente ao lado: %r" % (args,))

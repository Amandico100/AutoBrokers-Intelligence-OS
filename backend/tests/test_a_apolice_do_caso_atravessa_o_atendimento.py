# -*- coding: utf-8 -*-
"""SPEC-117 F2/F3 · A COSTURA — a apólice do caso nasce, fica gravada e é lida.

🔴 **Aqui roda o MOTOR** (CLAUDE.md §9.4): `nodes.tool_node` real,
`attendance_ficha.fundir`/`gravar`/`bloco_para_o_prompt` reais e
`human_handoff._linha_da_apolice` real. Os dublês estão só nas BORDAS — a
ferramenta que devolve o que o conector devolveria, e um Supabase de mentira que
guarda a coluna `ficha_atendimento` num dicionário. ⛔ Nenhum regex sobre o
fonte, nenhuma reimplementação de regra.

📊 **E o `data` do dublê não é imaginado:** ele sai de
`infocap_connector._canonical_customer_identity` e `_sanitize_policy`, as duas
funções REAIS que decidem o que cada papel vê. Se a máscara mudar de forma, este
arquivo muda com ela.

⚠️ O que este arquivo NÃO afirma: que o pass@1 do atendimento sobe. Ele afirma
que o FATO atravessa — a ficha durável, o acionamento, o portal e o aviso ao
humano recebem a MESMA apólice.

🔴 **Os cinco defeitos que este arquivo existe para pegar** (e que as mutações do
relatório provam que ele PEGA):
```
(a) a porta volta a exigir identidade CRUA      -> o contexto não nasce no WhatsApp
(b) o ramo/seguradora do MODELO vence o sistema -> tecla e telefone da seguradora errada
(c) o DICT vai para ficha["apolice"]            -> a atendente humana recebe um dict no WhatsApp
(d) o assunto NOVO herda a apólice do anterior  -> acionamento contra o contrato errado
(e) o portal de VIDROS recebe apólice `resi`    -> pedido aberto contra apólice residencial
```
"""

import asyncio

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents import nodes as N
from app.services import attendance_ficha as F

# --------------------------------------------------------------------------- #
# Tenants e cliente SINTÉTICOS — nenhuma corretora, nenhum segurado real
# (CLAUDE.md §13.9). Os UUIDs são fixos para que a prova de dois tenants possa
# afirmar que a MESMA dupla `codfil:codigo` não atravessa de uma para a outra.
# --------------------------------------------------------------------------- #
TENANT_A = "11111111-1111-4111-8111-111111111111"
TENANT_B = "22222222-2222-4222-8222-222222222222"
DOC_SINTETICO = "39053344705"
NOME_SINTETICO = "Cliente De Teste Sintetico"
SESSAO = "whatsapp:5500000000000:teste"


def _doc_auto(numero: str = "A-0001") -> dict:
    """Um documento CRU da fonte, na forma em que a InfoCap entrega."""
    return {
        "numapo": numero, "nosnum": "900001", "codfil": "1", "codigo": "7788",
        "seguradora_abrev": "ALLIANZ", "ramo_abrev": "AUTO",
        "inivig": "01/03/2026", "fimvig": "01/03/2027",
        "cliente": NOME_SINTETICO, "cpf_cnpj": DOC_SINTETICO,
        "itens": [{"descricao": "Colisao"}],
    }


def _doc_resi(numero: str = "R-0002") -> dict:
    d = _doc_auto(numero)
    d.update({"nosnum": "900002", "ramo_abrev": "RESI", "seguradora_abrev": "PORTO",
              "itens": [{"descricao": "Incendio"}]})
    return d


def _data_do_conector(*, unmasked: bool = False, docs=None) -> dict:
    """O `data` da ferramenta, montado pelas funções REAIS do conector."""
    from app.api.infocap_connector import (_canonical_customer_identity,
                                           _sanitize_policy)

    brutos = docs if docs is not None else [_doc_auto()]
    identidade = _canonical_customer_identity(brutos[0], brutos[0], unmasked=unmasked)
    apolices = [_sanitize_policy(d, unmasked) for d in brutos]
    return {
        "ok": True, "status": "found", "source_ref": "infocap:documento",
        "result_count": len(apolices), "matched_by": "document",
        "identity_status": "identity_verified", **identidade,
        "selected": apolices[0] if len(apolices) == 1 else None,
        "matches": apolices,
    }


def _contexto(*, company_id: str = TENANT_A, docs=None) -> dict:
    """Um PolicyContext REAL, pelo construtor da F1 e pelo `data` do conector."""
    from app.services.policy_context import construir_policy_context

    contexto = construir_policy_context(
        _data_do_conector(unmasked=False, docs=docs),
        company_id=company_id, papel="attendance")
    assert contexto, "sem contexto não há costura para medir — ver o TESTE DO FIO"
    return contexto


# --------------------------------------------------------------------------- #
# As BORDAS
# --------------------------------------------------------------------------- #
class _Duble:
    """Qualquer ferramenta: devolve o combinado e GUARDA os argumentos."""

    exige_async = True

    def __init__(self, name: str, resposta=None):
        self.name = name
        self._resposta = resposta if resposta is not None else {
            "status": "dispatched", "content": "Pedido registrado."}
        self.chamadas: list[dict] = []

    async def _arun(self, **kwargs):
        self.chamadas.append(dict(kwargs))
        return self._resposta

    def _run(self, **kwargs):  # pragma: no cover — o tool_node usa _arun
        raise RuntimeError("use _arun")


class _DubleDaConsulta(_Duble):
    def __init__(self, data: dict):
        super().__init__("infocap_policy_lookup",
                         {"ok": True, "found": True,
                          "content": "Localizei a sua apolice.", "data": data})


class _SupabaseDeMentira:
    """A BORDA do banco: guarda `ficha_atendimento` por (company_id, session_id).

    ⚠️ Ele obedece ao MESMO contrato que `attendance_ficha` usa — `table`,
    `select`/`update`, `eq`, `limit`, `execute` — porque é o contrato que o
    produto chama. Um dublê que aceitasse qualquer coisa não provaria que o
    filtro de `company_id` existe (CLAUDE.md §7).
    """

    def __init__(self, fichas: dict | None = None):
        self.fichas: dict = dict(fichas or {})
        self.client = self

    # -- o encadeamento ---------------------------------------------------- #
    def table(self, nome):
        assert nome == "conversations", nome
        return _Consulta(self)


class _Resultado:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, banco: _SupabaseDeMentira):
        self._banco = banco
        self._filtros: dict = {}
        self._modo = None
        self._dados = None

    def select(self, *_a, **_k):
        self._modo = "select"
        return self

    def update(self, dados):
        self._modo = "update"
        self._dados = dados
        return self

    def eq(self, coluna, valor):
        self._filtros[coluna] = str(valor)
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        chave = (self._filtros.get("company_id"), self._filtros.get("session_id"))
        if self._modo == "select":
            ficha = self._banco.fichas.get(chave)
            return _Resultado([{"ficha_atendimento": ficha}] if ficha is not None else [])
        self._banco.fichas[chave] = dict(self._dados or {}).get("ficha_atendimento")
        return _Resultado([{"session_id": chave[1]}])


@pytest.fixture
def banco(monkeypatch):
    """Liga o Supabase de mentira no lugar do real, para este teste só."""
    import app.core.database as db

    falso = _SupabaseDeMentira()
    monkeypatch.setattr(db, "get_supabase_client", lambda: falso, raising=False)
    return falso


def _estado(*, company_id: str = TENANT_A, papel: str = "attendance", **extra) -> dict:
    base = {
        "company_id": company_id, "user_id": "teste", "session_id": SESSAO,
        "company_config": {},
        "agent_data": {"id": None, "agent_role": papel, "tools_config": {}},
        "messages": [], "tools_used": [], "rag_chunks": [], "rag_search_time_ms": 0,
        "infocap_policy_context": None, "policy_response_contract": None,
        "internal_steps": [],
    }
    base.update(extra)
    return base


def _pedido(nome: str, args: dict, tool_id: str = "call-1"):
    return AIMessage(content="", tool_calls=[{"name": nome, "args": args, "id": tool_id}])


def _rodar(coro):
    return asyncio.run(coro)


def _ficha_gravada(banco: _SupabaseDeMentira, company_id: str = TENANT_A) -> dict:
    return banco.fichas.get((company_id, SESSAO)) or {}


# --------------------------------------------------------------------------- #
# O guarda de PII — sobre os VALORES, nunca sobre os NOMES DAS CHAVES
# --------------------------------------------------------------------------- #
#: 🔴 📊 26/09/2026, e custou um falso vermelho nesta mesma execução: comparar as
#: partes do nome contra o `json.dumps` da ficha inclui os NOMES das chaves, e a
#: chave `cliente_ref` casa com `"Cliente"`. O guarda ficaria VERMELHO sem uma
#: gota de PII — e um guarda que grita sem motivo é desligado pela próxima
#: pessoa. Duas correções, as duas com razão escrita:
#:   · varre só os VALORES, recursivamente;
#:   · parte de nome só conta com 4+ letras (`De`, `Da`, `Dos` são partículas).
#: ⚠️ O CPF continua sendo procurado no texto INTEIRO: dígito de documento não
#: tem colisão inocente.
_MIN_LETRAS_DE_NOME = 4


def _valores_em_texto(no) -> str:
    if isinstance(no, dict):
        return " ".join(_valores_em_texto(v) for v in no.values())
    if isinstance(no, (list, tuple, set)):
        return " ".join(_valores_em_texto(v) for v in no)
    return str(no)


def _pii_nos_valores(alvo) -> list:
    import json as _json

    valores = _valores_em_texto(alvo)
    inteiro = _json.dumps(alvo, ensure_ascii=False, default=str)
    achados = []
    if DOC_SINTETICO in inteiro:
        achados.append("CPF")
    for parte in NOME_SINTETICO.split():
        if len(parte) >= _MIN_LETRAS_DE_NOME and parte.lower() in valores.lower():
            achados.append("nome:%s" % parte)
    if "infocap:" in valores:
        achados.append("locator tecnico cru")
    return achados


def test_CONTROLE_o_guarda_de_pii_desta_costura_consegue_ficar_vermelho():
    """🔴 CLAUDE.md §9.3 — um guarda que não tem como falhar não guarda nada."""
    limpo = {"apolice": "R-0002", "apolice_do_caso": {"cliente_ref": "ab12cd34"}}
    assert _pii_nos_valores(limpo) == [], _pii_nos_valores(limpo)
    assert _pii_nos_valores({**limpo, "titular": NOME_SINTETICO})
    assert _pii_nos_valores({**limpo, "doc": DOC_SINTETICO})
    assert _pii_nos_valores({**limpo, "ref": "infocap:1:900002"})


# =========================================================================== #
# (c) A ESCRITA DURÁVEL — e os DOIS TIPOS que a atendente humana depende
# =========================================================================== #
def test_a_apolice_do_caso_vai_para_a_ficha_com_os_dois_tipos(banco):
    """🔴 `ficha["apolice"]` é STRING; `ficha["apolice_do_caso"]` é DICT.

    📊 26/09/2026 · `human_handoff.py:607` faz
    `str(ficha.get("apolice") or …)` e joga o resultado no TEXTO enviado à
    atendente humana. `str()` de um dicionário não levanta erro — ele manda
    `{'versao': 1, …}` para o WhatsApp de uma pessoa.
    """
    consulta = _DubleDaConsulta(_data_do_conector(docs=[_doc_resi()]))
    estado = _estado()
    estado["messages"] = [
        HumanMessage(content="tem um vazamento na minha casa, CPF %s" % DOC_SINTETICO),
        _pedido("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    _rodar(N.tool_node(estado, tools=[consulta]))

    ficha = _ficha_gravada(banco)
    assert ficha, "a apólice encontrada não virou memória durável"
    assert isinstance(ficha.get("apolice"), str), (
        "ficha['apolice'] TEM de ser string — %r" % (ficha.get("apolice"),))
    assert ficha["apolice"] == "R-0002", ficha["apolice"]
    assert isinstance(ficha.get("apolice_do_caso"), dict), ficha.get("apolice_do_caso")
    assert ficha["apolice_do_caso"]["company_id"] == TENANT_A

    # E o que a ficha durável guarda continua sem dado pessoal — o PAINEL lê esta
    # coluna, então um vazamento aqui é um vazamento de tela.
    achados = _pii_nos_valores(ficha)
    assert achados == [], "dado pessoal na ficha durável: %s | %r" % (achados, ficha)

    # O ramo gravado é a LINHA do corredor, não a família crua: `graph.py:798`
    # entrega este campo a `resolve_playbook_ref` como `line_kind`, e ele não
    # conhece "resi" (📊 `corridor_playbooks.py:8276-8277`).
    assert ficha.get("ramo") == "residencial", ficha.get("ramo")
    assert ficha.get("seguradora") == "porto", ficha.get("seguradora")


def test_o_aviso_ao_humano_leva_o_numero_e_NAO_um_dicionario(banco):
    """🔴 F3.4 — provado com o MOTOR do handoff, não por suposição.

    `human_handoff._linha_da_apolice` lê `conversa["ficha_atendimento"]`, que vem
    do banco. Se a F2 grava certo, o aviso à atendente sai com o número. Se
    alguém gravar o dicionário na chave errada, esta linha vira um dict.
    """
    consulta = _DubleDaConsulta(_data_do_conector(docs=[_doc_resi()]))
    estado = _estado()
    estado["messages"] = [
        HumanMessage(content="vazamento, CPF %s" % DOC_SINTETICO),
        _pedido("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    _rodar(N.tool_node(estado, tools=[consulta]))

    from app.agents.tools.human_handoff import _linha_da_apolice

    linha = _linha_da_apolice({"ficha_atendimento": _ficha_gravada(banco)})
    assert "R-0002" in linha, "o aviso ao humano saiu SEM o número da apólice: %r" % linha
    assert "Porto" in linha and "Residencial" in linha, linha
    for veneno in ("{", "}", "'", "versao", "cliente_ref", "apolices"):
        assert veneno not in linha, (
            "o aviso à atendente humana levou estrutura de dicionário (%r): %r"
            % (veneno, linha))


# =========================================================================== #
# (d) O ASSUNTO NOVO NÃO HERDA A APÓLICE
# =========================================================================== #
def test_o_assunto_novo_NAO_herda_a_apolice_do_caso_anterior():
    """🔴 A apólice é do CASO, não do telefone (SPEC-117 §7).

    A thread do WhatsApp é por número e nunca reinicia. Herdar a apólice de um
    sinistro fechado faria o caso novo acionar o contrato errado — e nada disso
    trava (CLAUDE.md §9.5).
    """
    ficha = F.fundir(F.ficha_vazia(), {
        "identidade": {"assunto_id": "assunto-1"},
        **F.novidades_da_apolice(_contexto(docs=[_doc_resi()])),
    })
    assert ficha["apolice"] == "R-0002"
    assert ficha["apolice_do_caso"]["apolices"]

    depois = F.fundir(ficha, {"identidade": {"assunto_id": "assunto-2"}})
    assert not depois.get("apolice"), (
        "o assunto NOVO herdou a apólice do anterior: %r" % (depois.get("apolice"),))
    assert not depois.get("apolice_do_caso"), depois.get("apolice_do_caso")

    # CONTROLE: no MESMO assunto ela não pode sumir — a ficha é aditiva, e é
    # esse o defeito que o arquivo da ficha existe para consertar.
    mesmo = F.fundir(ficha, {"identidade": {"assunto_id": "assunto-1"},
                             "confirmados": {"local_cep": "00000-000"}})
    assert mesmo.get("apolice") == "R-0002", (
        "um turno sem apólice APAGOU a apólice do caso: %r" % (mesmo.get("apolice"),))


def test_a_apolice_de_outra_corretora_NUNCA_funde_com_esta_ficha():
    """§7 — o `company_id` é trava, não campo."""
    ficha = F.fundir(F.ficha_vazia(), F.novidades_da_apolice(
        _contexto(company_id=TENANT_A, docs=[_doc_resi()])))
    assert ficha["apolice_do_caso"]["company_id"] == TENANT_A

    depois = F.fundir(ficha, F.novidades_da_apolice(
        _contexto(company_id=TENANT_B, docs=[_doc_auto("B-0003")])))
    assert depois["apolice_do_caso"]["company_id"] == TENANT_B, depois["apolice_do_caso"]
    assert depois["apolice"] == "B-0003", depois["apolice"]
    # ⚠️ E os pseudônimos do MESMO `codfil:codigo` são diferentes nas duas
    # corretoras — é o que faz o isolamento valer (decisão D3, gate G9).
    assert (ficha["apolice_do_caso"]["cliente_ref"]
            != depois["apolice_do_caso"]["cliente_ref"])

    # ═══════════════════════════════════════════════════════════════════════════
    # 🔴 O RAMO QUE PROVA QUE O `pop` DE `fundir` TEM EFEITO (pendência 4 do juiz)
    # ═══════════════════════════════════════════════════════════════════════════
    # 📊 O juiz mediu que o `pop(CHAVE_DA_APOLICE)` era desfeito três linhas
    # abaixo, e concluiu "código morto". Ele é morto **só quando há apólice
    # selecionada**: aí `novidades_da_apolice` manda as duas chaves juntas. Com
    # DUAS candidatas e nenhuma escolhida ela manda só a estrutura — e sem o
    # `pop` o NÚMERO HUMANO da corretora anterior ficaria na ficha, ao lado do
    # contexto da nova. É esse número que `human_handoff._linha_da_apolice`
    # imprime para a atendente ler (CLAUDE.md §7 e §9.5).
    outra_sem_escolha = _contexto(
        company_id=TENANT_B,
        docs=[_doc_auto("B-0010"), _doc_resi("B-0011")])
    assert outra_sem_escolha["selecionada"] is None, (
        "controle: duas vigentes não escolhem — é este o caso em que o `pop` age")
    sem_numero = F.fundir(ficha, F.novidades_da_apolice(outra_sem_escolha))
    assert sem_numero.get("apolice") in (None, ""), (
        "o NÚMERO da apólice da corretora A sobreviveu na ficha da B: %r"
        % (sem_numero.get("apolice"),))
    assert sem_numero["apolice_do_caso"]["company_id"] == TENANT_B


# =========================================================================== #
# (b) O RAMO E A SEGURADORA DO SISTEMA VENCEM O PALPITE DO MODELO
# =========================================================================== #
def test_o_ramo_e_a_seguradora_do_sistema_vencem_o_palpite_do_modelo(banco):
    """🔴 D-PILOTO-11 (17/09) + SPEC-117 F3.1, no acionamento REAL.

    A apólice do cliente é RESIDENCIAL da Porto. O modelo escreve `auto` e
    `allianz`. Hoje isso não trava: a URA da seguradora errada responde, e o
    segurado ouve *"sua assistência foi aberta"*.
    """
    consulta = _DubleDaConsulta(_data_do_conector(docs=[_doc_resi()]))
    dispatch = _Duble("insurer_dispatch")

    estado = _estado()
    estado["messages"] = [
        HumanMessage(content="vazamento em casa, CPF %s" % DOC_SINTETICO),
        _pedido("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    saida = _rodar(N.tool_node(estado, tools=[consulta, dispatch]))

    estado2 = _estado(infocap_policy_context=saida.get("infocap_policy_context"))
    estado2["messages"] = [
        HumanMessage(content="pode acionar"),
        _pedido("insurer_dispatch",
                {"subservice": "encanador", "insurer_key": "allianz",
                 "line_kind": "auto", "ramo_da_apolice": "auto",
                 "dados_confirmados": True}, tool_id="call-2"),
    ]
    _rodar(N.tool_node(estado2, tools=[consulta, dispatch]))

    assert dispatch.chamadas, "o acionamento não foi chamado"
    recebido = dispatch.chamadas[-1]
    assert recebido.get("ramo_da_apolice") == "resi", (
        "o ramo oficial não venceu o palpite do modelo: %r" % (recebido.get("ramo_da_apolice"),))
    assert recebido.get("insurer_key") == "porto", (
        "a seguradora da apólice não venceu a que o modelo escreveu: %r"
        % (recebido.get("insurer_key"),))

    # E a ficha durável também guarda o do SISTEMA, não o do modelo — é dela que
    # `graph._slots_obrigatorios_do_caso` resolve o corredor do caso.
    ficha = _ficha_gravada(banco)
    assert ficha.get("seguradora") == "porto", ficha.get("seguradora")
    assert ficha.get("ramo") == "residencial", ficha.get("ramo")


# =========================================================================== #
# (e) O PORTAL É DE VIDROS/AUTO — E A TRAVA DE FAMÍLIA
# =========================================================================== #
def test_o_portal_recebe_a_apolice_AUTO(banco):
    """Com apólice `auto` selecionada, o número vai ao portal (o schema aceita:
    📊 `portal_tool.py:131`)."""
    portal = _Duble("portal_action", {"status": "queued"})
    estado = _estado(infocap_policy_context=_contexto(docs=[_doc_auto()]))
    estado["messages"] = [
        HumanMessage(content="quebrou o parabrisa"),
        _pedido("portal_action", {"cpf_cnpj": DOC_SINTETICO, "data_dano": "01/09/2026"}),
    ]
    _rodar(N.tool_node(estado, tools=[portal]))

    assert portal.chamadas, "o portal não foi chamado"
    assert portal.chamadas[-1].get("policy_number") == "A-0001", portal.chamadas[-1]


def test_o_portal_NUNCA_recebe_a_apolice_RESIDENCIAL(banco):
    """🔴 A trava da §9.5: o portal ligado ao `portal_action` é o de VIDROS.

    Injetar o número de uma apólice `resi` faria o portal abrir pedido contra uma
    apólice residencial — e isso sai da corretora como pedido válido, sem travar.
    """
    portal = _Duble("portal_action", {"status": "queued"})
    estado = _estado(infocap_policy_context=_contexto(docs=[_doc_resi()]))
    estado["messages"] = [
        HumanMessage(content="quebrou o vidro"),
        _pedido("portal_action", {"cpf_cnpj": DOC_SINTETICO, "data_dano": "01/09/2026"}),
    ]
    _rodar(N.tool_node(estado, tools=[portal]))

    assert portal.chamadas, "o portal não foi chamado"
    assert not portal.chamadas[-1].get("policy_number"), (
        "o portal de VIDROS recebeu o número de uma apólice RESIDENCIAL: %r"
        % (portal.chamadas[-1].get("policy_number"),))


# =========================================================================== #
# G8 — A RETOMADA depois do reinício do processo
# =========================================================================== #
def test_a_apolice_volta_da_ficha_quando_o_processo_reiniciou(banco):
    """🔴 G8. O checkpointer de fallback é um `MemorySaver` (📊 `graph.py:50`) —
    ele some no reinício. A ficha durável é o que devolve a apólice ao caso.
    """
    banco.fichas[(TENANT_A, SESSAO)] = F.fundir(
        F.ficha_vazia(), F.novidades_da_apolice(_contexto(docs=[_doc_resi()])))

    dispatch = _Duble("insurer_dispatch")
    estado = _estado(infocap_policy_context=None)   # o checkpoint sumiu
    estado["messages"] = [
        HumanMessage(content="pode acionar"),
        _pedido("insurer_dispatch",
                {"subservice": "encanador", "insurer_key": "allianz",
                 "ramo_da_apolice": "auto", "dados_confirmados": True}),
    ]
    _rodar(N.tool_node(estado, tools=[dispatch]))

    assert dispatch.chamadas[-1].get("ramo_da_apolice") == "resi", (
        "depois do reinício a apólice do caso não voltou: %r" % (dispatch.chamadas[-1],))
    assert dispatch.chamadas[-1].get("insurer_key") == "porto", dispatch.chamadas[-1]


def test_a_ficha_de_OUTRA_corretora_nao_entra_neste_caso(banco):
    """§7 — a retomada confere o tenant na volta. Uma ficha gravada sob outra
    corretora não pode decidir o acionamento desta."""
    banco.fichas[(TENANT_A, SESSAO)] = F.fundir(
        F.ficha_vazia(),
        F.novidades_da_apolice(_contexto(company_id=TENANT_B, docs=[_doc_resi()])))

    dispatch = _Duble("insurer_dispatch")
    estado = _estado(company_id=TENANT_A, infocap_policy_context=None)
    estado["messages"] = [
        HumanMessage(content="pode acionar"),
        _pedido("insurer_dispatch",
                {"subservice": "encanador", "insurer_key": "allianz",
                 "ramo_da_apolice": "auto", "dados_confirmados": True}),
    ]
    _rodar(N.tool_node(estado, tools=[dispatch]))

    assert dispatch.chamadas[-1].get("ramo_da_apolice") == "auto", (
        "a apólice de OUTRA corretora decidiu o acionamento desta: %r"
        % (dispatch.chamadas[-1],))


def test_CONTROLE_sem_company_id_o_contexto_NAO_nasce(banco):
    """§7 — sem tenant não há contexto, e o tenant nunca é adivinhado.

    ⚠️ Esta é a LINHA DE CONTROLE das duas acima: é ela que dá direito a dizer
    que o isolamento vem do `company_id`, e não do dublê nem da sessão.
    """
    consulta = _DubleDaConsulta(_data_do_conector())
    estado = _estado(company_id="")
    estado["messages"] = [
        HumanMessage(content="CPF %s" % DOC_SINTETICO),
        _pedido("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    saida = _rodar(N.tool_node(estado, tools=[consulta]))
    assert not saida.get("infocap_policy_context"), (
        "nasceu contexto SEM tenant: %r" % (saida.get("infocap_policy_context"),))
    assert not banco.fichas, "gravou ficha sem tenant: %r" % (banco.fichas,)


# =========================================================================== #
# F3.6 — O BLOCO DO PROMPT mostra a apólice, e só o que é visível
# =========================================================================== #
def test_o_bloco_do_prompt_mostra_a_apolice_e_esconde_o_que_e_interno():
    """A SPEC-117 §2 diz o que o modelo pode ver: número humano, ramo, seguradora
    e vigência. ⛔ Nunca `cliente_ref`, `chave`, `origem_por_campo`, `evidencia`.
    """
    contexto = _contexto(docs=[_doc_resi()])
    ficha = F.fundir(F.ficha_vazia(), F.novidades_da_apolice(contexto))
    bloco = F.bloco_para_o_prompt(ficha)

    assert "R-0002" in bloco, bloco
    assert "residencial" in bloco.lower(), bloco
    assert "01/03/2027" in bloco, bloco
    for interno in (contexto["cliente_ref"], contexto["apolices"][0]["chave"],
                    "origem_por_campo", "evidencia", "cliente_ref",
                    "infocap_customer_catalog"):
        assert interno not in bloco, "o bloco do prompt vazou %r:\n%s" % (interno, bloco)
    assert DOC_SINTETICO not in bloco and "Sintetico" not in bloco, bloco


def test_a_leitura_da_apolice_e_UMA_e_recusa_vencida():
    """A LEITURA ÚNICA é `attendance_ficha.apolice_do_caso` →
    `policy_context.apolice_selecionada`. ⛔ Ninguém varre `apolices[]`.

    E o par que importa: com DUAS apólices vigentes de ramos diferentes o
    construtor NÃO escolhe — então não há apólice do caso, e nenhum consumidor
    pode agir como se houvesse (SPEC-117 G5).
    """
    uma = _contexto(docs=[_doc_resi()])
    assert F.apolice_do_caso(contexto=uma)["numapo"] == "R-0002"
    assert F.apolice_do_caso(ficha=F.fundir(F.ficha_vazia(),
                                            F.novidades_da_apolice(uma)))["numapo"] == "R-0002"
    assert F.apolice_do_caso(state={"infocap_policy_context": uma})["numapo"] == "R-0002"

    duas = _contexto(docs=[_doc_auto(), _doc_resi()])
    assert F.apolice_do_caso(contexto=duas) is None, (
        "com duas vigentes de ramos diferentes NÃO há apólice do caso: %r"
        % (F.apolice_do_caso(contexto=duas),))
    assert F.novidades_da_apolice(duas).get("apolice") is None
    # ⚠️ mas a estrutura é gravada: é dela que sai a desambiguação do turno seguinte.
    assert F.novidades_da_apolice(duas)["apolice_do_caso"]["apolices"]


# =========================================================================== #
# 🔴 SPEC-117, CONSERTO ÚNICO · B1 — O DURÁVEL É A LISTA BRANCA, EM TODO PAPEL
# =========================================================================== #
def test_b1_no_papel_core_a_ficha_duravel_NAO_recebe_cpf_nem_nome(banco):
    """🔴 SEGURANÇA. LGPD · OWASP LLM02 · SPEC-117 §2 e §7.

    O papel `core` recebe identidade CRUA no contexto — exceção legítima da §2,
    porque o Chat Principal opera com dado cru no turno e
    `_policy_context_tool_args` depende dela. 📊 Mas `novidades_da_apolice`
    gravava o contexto INTEIRO em `conversations.ficha_atendimento`, a coluna que
    o painel do Founder lê:

    ```
    [core] PII na ficha durável: ['CPF','nome:Cliente','nome:Teste','nome:Sintetico']
    [attendance] PII na ficha durável: nenhum
    ```
    e 📊 `0 de 79` fichas de `core` tinham conteúdo no banco: o primeiro byte que
    esta SPEC escreveria lá era o CPF.

    ⚠️ Este guarda roda o papel `core` de propósito: nenhum dos 40 testes novos
    varria esse caminho, e foi por isso que o defeito atravessou.
    """
    consulta = _DubleDaConsulta(_data_do_conector(unmasked=True, docs=[_doc_auto()]))
    estado = _estado(papel="core")
    estado["messages"] = [
        HumanMessage(content="apolice do cliente %s" % DOC_SINTETICO),
        _pedido("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    saida = _rodar(N.tool_node(estado, tools=[consulta]))

    # CONTROLE: o contexto do TURNO continua com a identidade crua (o `core`
    # depende dela) — o que muda é só o que FICA GRAVADO.
    contexto = saida.get("infocap_policy_context") or {}
    assert contexto.get("document") == DOC_SINTETICO, (
        "o papel core perdeu a identidade crua NO TURNO: o Chat Principal "
        "depende dela em `_policy_context_tool_args`")

    ficha = _ficha_gravada(banco)
    assert ficha, "o motor não gravou a ficha — sem gravação não há o que medir"
    assert _pii_nos_valores(ficha) == [], (
        "dado pessoal CRU chegou à coluna durável: %s" % _pii_nos_valores(ficha))
    do_caso = ficha.get("apolice_do_caso") or {}
    assert "document" not in do_caso and "name" not in do_caso, sorted(do_caso)
    # e o que é legítimo continua lá
    assert do_caso.get("company_id") == TENANT_A
    assert [a["numapo"] for a in do_caso.get("apolices") or []] == ["A-0001"]


def test_b1_MUTACAO_o_guarda_do_duravel_consegue_ficar_vermelho(banco, monkeypatch):
    """🔴 CLAUDE.md §9.3. Com a projeção da lista branca DESLIGADA (o defeito de
    26/09 reintroduzido), o guarda de cima tem de ficar vermelho."""
    from app.services import policy_context as PC

    monkeypatch.setattr(PC, "contexto_para_o_duravel", lambda ctx: ctx)

    consulta = _DubleDaConsulta(_data_do_conector(unmasked=True, docs=[_doc_auto()]))
    estado = _estado(papel="core")
    estado["messages"] = [
        HumanMessage(content="apolice do cliente %s" % DOC_SINTETICO),
        _pedido("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    _rodar(N.tool_node(estado, tools=[consulta]))
    achados = _pii_nos_valores(_ficha_gravada(banco))
    assert "CPF" in achados, (
        "sem a projeção da lista branca o CPF TINHA de aparecer na ficha — o "
        "guarda de cima é carimbo: %s" % achados)


# =========================================================================== #
# 🔴 SPEC-117, CONSERTO ÚNICO · B3 — A APÓLICE QUE ATRAVESSOU É A CERTA?
# =========================================================================== #
#
# 🔴 A MAIOR LACUNA que o juiz apontou: toda a bateria perguntava "o fato
# atravessou?" e nenhum teste perguntava "o fato que atravessou é o CERTO para
# este pedido?" (CLAUDE.md §9.5, a segunda pergunta). O caso que pega o defeito
# — UMA apólice vigente, de ramo DIFERENTE do serviço pedido — não existia, e
# foi por ele que o B3 atravessou 40 testes verdes.
def _so_auto_vigente_e_pede_encanador(banco, servico="encanador"):
    """Cliente com UMA apólice AUTO vigente pede um serviço de CASA."""
    consulta = _DubleDaConsulta(_data_do_conector(docs=[_doc_auto()]))
    dispatch = _Duble("insurer_dispatch")
    estado = _estado()
    estado["messages"] = [
        HumanMessage(content="minha casa alagou, CPF %s" % DOC_SINTETICO),
        _pedido("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    saida = _rodar(N.tool_node(estado, tools=[consulta, dispatch]))
    estado2 = _estado(infocap_policy_context=saida.get("infocap_policy_context"))
    estado2["messages"] = [
        HumanMessage(content="pode acionar o encanador"),
        _pedido("insurer_dispatch",
                {"subservice": servico, "insurer_key": "porto",
                 "line_kind": "residencial", "ramo_da_apolice": "residencial",
                 "dados_confirmados": True}, tool_id="call-2"),
    ]
    _rodar(N.tool_node(estado2, tools=[consulta, dispatch]))
    return dispatch, _ficha_gravada(banco)


def test_b3_uma_apolice_de_ramo_DIFERENTE_do_servico_nao_sobrescreve_o_pedido(banco):
    """🔴 O defeito silencioso que CHEGA AO SEGURADO (CLAUDE.md §9.5).

    📊 Medido em 26/09/2026, pelo motor:
    ```
    SÓ AUTO vigente + encanador
      MODELO pediu      : ramo=residencial insurer=porto
      SEGURADORA recebeu: ramo=auto        insurer=allianz
      FICHA             : ramo=auto / allianz
    ```
    Um ENCANADOR saía para a seguradora do CARRO, com as teclas de URA do
    corredor `auto`; e como `graph._slots_obrigatorios_do_caso` (📊
    `graph.py:798`) resolve o corredor de `ficha["ramo"]`, a lista de
    obrigatórios do caso inteiro virava a errada. Nada travava: o segurado ouvia
    *"sua assistência foi aberta"*.

    ⚠️ Não havendo apólice da família pedida, o sistema NÃO sobrescreve — a
    sobrescrita é que era a mentira. A divergência fica no log.
    """
    dispatch, ficha = _so_auto_vigente_e_pede_encanador(banco)
    assert dispatch.chamadas, "o acionamento não foi chamado"
    recebido = dispatch.chamadas[-1]
    assert recebido.get("ramo_da_apolice") == "residencial", (
        "o encanador saiu no ramo %r — a apólice do caso é AUTO e o serviço é de "
        "CASA" % (recebido.get("ramo_da_apolice"),))
    assert recebido.get("insurer_key") == "porto", (
        "o encanador saiu para a seguradora %r, a do CARRO"
        % (recebido.get("insurer_key"),))
    assert ficha.get("ramo") == "residencial", (
        "a ficha gravou ramo=%r — é dela que sai o CORREDOR do caso"
        % (ficha.get("ramo"),))
    assert ficha.get("seguradora") == "porto", ficha.get("seguradora")


def test_b3_duas_vigentes_o_SERVICO_pedido_escolhe_sem_perguntar(banco):
    """🔴 G5 da SPEC-117, que estava construído e desligado: *"Auto+Resi →
    serviço de casa escolhe `resi` sem perguntar"*.

    📊 `apolices_vigentes(contexto, ramo=…)` tinha ZERO chamadores em
    `backend/app` — a escolha por serviço nunca foi ligada. Com as duas
    vigentes, `selecionada` volta `None` e ninguém escolhia pelo pedido.
    """
    consulta = _DubleDaConsulta(_data_do_conector(docs=[_doc_auto(), _doc_resi()]))
    dispatch = _Duble("insurer_dispatch")
    estado = _estado()
    estado["messages"] = [
        HumanMessage(content="oi, CPF %s" % DOC_SINTETICO),
        _pedido("infocap_policy_lookup", {"document": DOC_SINTETICO}),
    ]
    saida = _rodar(N.tool_node(estado, tools=[consulta, dispatch]))
    contexto = saida.get("infocap_policy_context") or {}
    assert contexto.get("selecionada") is None, (
        "controle: com duas vigentes o construtor NÃO escolhe — quem escolhe "
        "pelo ramo é o PEDIDO")

    estado2 = _estado(infocap_policy_context=contexto)
    estado2["messages"] = [
        HumanMessage(content="deu um vazamento em casa, pode acionar"),
        _pedido("insurer_dispatch",
                {"subservice": "encanador", "insurer_key": "allianz",
                 "line_kind": "auto", "ramo_da_apolice": "auto",
                 "dados_confirmados": True}, tool_id="call-2"),
    ]
    _rodar(N.tool_node(estado2, tools=[consulta, dispatch]))

    recebido = dispatch.chamadas[-1]
    assert recebido.get("ramo_da_apolice") == "resi", recebido
    assert recebido.get("insurer_key") == "porto", recebido
    ficha = _ficha_gravada(banco)
    assert ficha.get("apolice") == "R-0002", (
        "a escolha do SERVIÇO não ficou: a ficha guardou %r" % (ficha.get("apolice"),))
    assert ficha.get("ramo") == "residencial", ficha.get("ramo")
    do_caso = ficha.get("apolice_do_caso") or {}
    assert (do_caso.get("origem_por_campo") or {}).get("selecionada") == "corredor", (
        "a ficha tem de dizer QUEM escolheu a apólice: %r"
        % (do_caso.get("origem_por_campo"),))


def test_b3_MUTACAO_sem_o_guarda_de_familia_o_encanador_sai_no_carro(banco, monkeypatch):
    """🔴 CLAUDE.md §9.3/§9.5 — com o defeito de 26/09 reintroduzido (a família do
    serviço deixa de ser conhecida, e o sistema volta a sobrescrever sempre), o
    guarda de cima tem de ficar VERMELHO."""
    monkeypatch.setattr(N, "_familia_do_servico_pedido", lambda _args: "")
    dispatch, ficha = _so_auto_vigente_e_pede_encanador(banco)
    assert dispatch.chamadas[-1].get("ramo_da_apolice") == "auto", (
        "sem o guarda o encanador TINHA de sair no ramo auto — o guarda de cima "
        "é carimbo: %r" % (dispatch.chamadas[-1],))
    assert ficha.get("ramo") == "auto", ficha.get("ramo")


def test_b3_o_servico_AMBIGUO_nao_decide_pelo_segurado():
    """🔴 `chaveiro` existe nas DUAS linhas (📊 `corridor_playbooks`), e um
    chaveiro de CARRO mandado ao menu residencial pede o número da casa a quem
    está parado no acostamento. Ambíguo é "não sei", nunca "é esta"."""
    assert N._familia_do_servico_pedido({"subservice": "chaveiro"}) == ""
    # CONTROLE: os que NÃO são ambíguos respondem, e vêm dos corredores
    assert N._familia_do_servico_pedido({"subservice": "encanador"}) == "resi"
    assert N._familia_do_servico_pedido({"subservice": "guincho"}) == "auto"
    assert N._familia_do_servico_pedido({"servico": "vidros"}) == "auto"
    assert N._familia_do_servico_pedido({}) == ""
    # ⛔ e NUNCA do palpite do modelo sobre a apólice
    assert N._familia_do_servico_pedido(
        {"line_kind": "residencial", "ramo_da_apolice": "residencial"}) == ""


# =========================================================================== #
# 🔴 SPEC-117, CONSERTO ÚNICO · R2 — O PORTAL E O NÚMERO QUE O MODELO ESCOLHEU
# =========================================================================== #
def test_r2_o_portal_mantem_a_auto_que_o_modelo_pediu_quando_ela_e_do_cliente(banco):
    """📊 Medido: com DUAS autos vigentes, o modelo pediu `A-0002` (o vidro é do
    outro carro) e o portal recebia `A-0001` — a que a fonte fixou num turno
    anterior. O pedido saía da corretora contra o contrato errado.

    O sistema só corrige o número quando o que o modelo escreveu NÃO é uma
    apólice vigente deste cliente na família do portal.
    """
    outro_carro = _doc_auto("A-0002")
    outro_carro["nosnum"] = "900009"
    portal = _Duble("portal_action", {"status": "queued"})
    contexto = _contexto(docs=[_doc_auto("A-0001"), outro_carro])

    estado = _estado(infocap_policy_context=contexto)
    estado["messages"] = [
        HumanMessage(content="quebrou o parabrisa do outro carro"),
        _pedido("portal_action", {"cpf_cnpj": DOC_SINTETICO,
                                  "data_dano": "01/09/2026",
                                  "policy_number": "A-0002"}),
    ]
    _rodar(N.tool_node(estado, tools=[portal]))
    assert portal.chamadas[-1].get("policy_number") == "A-0002", (
        "o portal recebeu %r no lugar da apólice que o modelo escolheu"
        % (portal.chamadas[-1].get("policy_number"),))


def test_r2_CONTROLE_numero_que_NAO_e_do_cliente_continua_sendo_corrigido(banco):
    """🔴 O guarda de cima não pode virar "o modelo sempre vence": um número que
    não é de nenhuma apólice vigente do cliente continua sendo substituído pela
    apólice do caso — era esse o valor da F3.2."""
    portal = _Duble("portal_action", {"status": "queued"})
    estado = _estado(infocap_policy_context=_contexto(docs=[_doc_auto("A-0001")]))
    estado["messages"] = [
        HumanMessage(content="quebrou o parabrisa"),
        _pedido("portal_action", {"cpf_cnpj": DOC_SINTETICO,
                                  "data_dano": "01/09/2026",
                                  "policy_number": "Z-9999"}),
    ]
    _rodar(N.tool_node(estado, tools=[portal]))
    assert portal.chamadas[-1].get("policy_number") == "A-0001", portal.chamadas[-1]


# =========================================================================== #
# 🔴 SPEC-117, CONSERTO ÚNICO · B7 — A TRAVA DE TENANT MORA NO CÓDIGO (§7)
# =========================================================================== #
def test_b7_contexto_de_outra_corretora_no_estado_nao_atravessa_nem_grava(banco):
    """🔴 CLAUDE.md §7: o backend usa **service role** — a RLS não protege contra
    filtro errado no código, e uma trava que depende de quem chama não é trava.

    📊 Medido pelo red team em 26/09/2026, com o `tool_node` real:
    ```
    contexto do tenant 1111… num turno do tenant 2222…
    o acionamento do tenant B RECEBEU: ramo='resi' seguradora='porto'   (de A)
    linha gravada: ('2222…','whatsapp:…') → apolice_do_caso.company_id='1111…'
    ```
    A trava existia só em `_gravar_apolice_do_caso`; `_gravar_ficha_do_turno` e o
    caminho do ESTADO (o primeiro que se consulta) não tinham nenhuma.
    """
    import json as _json

    contexto_de_a = _contexto(company_id=TENANT_A, docs=[_doc_resi()])
    dispatch = _Duble("insurer_dispatch")
    estado = _estado(company_id=TENANT_B, infocap_policy_context=contexto_de_a)
    estado["messages"] = [
        HumanMessage(content="pode acionar"),
        _pedido("insurer_dispatch",
                {"subservice": "encanador", "insurer_key": "allianz",
                 "line_kind": "auto", "ramo_da_apolice": "auto",
                 "dados_confirmados": True}),
    ]
    _rodar(N.tool_node(estado, tools=[dispatch]))

    recebido = dispatch.chamadas[-1]
    assert recebido.get("insurer_key") == "allianz", (
        "o acionamento da corretora B saiu com a seguradora da apólice da "
        "corretora A: %r" % (recebido,))
    ficha_b = _ficha_gravada(banco, TENANT_B)
    bruto = _json.dumps(ficha_b, ensure_ascii=False, default=str)
    assert TENANT_A not in bruto, ficha_b
    assert "R-0002" not in bruto, (
        "o número da apólice da corretora A foi gravado na ficha da B: %r" % (ficha_b,))
    assert not ficha_b.get("apolice_do_caso"), ficha_b.get("apolice_do_caso")


def test_b7_MUTACAO_sem_a_trava_o_contexto_alheio_atravessa(banco, monkeypatch):
    """🔴 CLAUDE.md §9.3 — com a trava desligada, o guarda de cima fica vermelho."""
    monkeypatch.setattr(N, "_contexto_do_tenant",
                        lambda contexto, company_id: contexto
                        if isinstance(contexto, dict) else None)
    contexto_de_a = _contexto(company_id=TENANT_A, docs=[_doc_resi()])
    dispatch = _Duble("insurer_dispatch")
    estado = _estado(company_id=TENANT_B, infocap_policy_context=contexto_de_a)
    estado["messages"] = [
        HumanMessage(content="pode acionar"),
        _pedido("insurer_dispatch",
                {"subservice": "encanador", "insurer_key": "allianz",
                 "line_kind": "auto", "ramo_da_apolice": "auto",
                 "dados_confirmados": True}),
    ]
    _rodar(N.tool_node(estado, tools=[dispatch]))
    assert dispatch.chamadas[-1].get("insurer_key") == "porto", (
        "sem a trava o acionamento de B TINHA de sair com a seguradora de A — o "
        "guarda de cima é carimbo: %r" % (dispatch.chamadas[-1],))

# -*- coding: utf-8 -*-
"""SPEC-126 U3 · D1 — O PARENTE ACIONA, sem ver dado da apólice (gate G3).

    D1 (Founder, 02/10/2026): cônjuge, filho, pai/mãe, motorista PODE pedir
    acionamento na apólice do titular, SEM exigir o titular junto. Ao terceiro NÃO
    se revela dado da apólice: número, prêmio, coberturas, vigência, CPF.

🔴 O TESTE DO FIO (1ª entrega da U3), pelo MOTOR (CLAUDE.md §9.4): `nodes.tool_node`
REAL → `InfocapPolicyLookupTool._arun` REAL → `de_quem_e_a_apolice` REAL → o
`ToolMessage` que o MODELO lê (`_conteudo_da_consulta_para_o_modelo`) → o recorder
REAL de `tool_invocations`. Dublês só na BORDA: o provedor de apólices (a porta
`get_policy_data_provider`) e um banco em memória que FILTRA de verdade.

📊 Nasce VERMELHO no HEAD `fbdecec`: o filho que pede guincho recebia
`TEXTO_DA_APOLICE_DE_TERCEIRO` ("só com o titular JUNTO…") — a mutação G3 abaixo
reintroduz a regra velha e o relatório cola a saída.

Dados 100 % fictícios (CPF com DV válido, seguradora e datas inventadas; nenhuma
corretora real — CLAUDE.md §13.9).
"""
from __future__ import annotations

import asyncio
import copy
import json
import uuid
from datetime import datetime, timezone

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents import nodes as N
from app.agents.tools import infocap_tool as T

EMPRESA_A = "aaaaaaaa-1260-4000-8000-0000000000a1"
EMPRESA_B = "bbbbbbbb-1260-4000-8000-0000000000b2"
FONE = "5500000001260"
SESSAO_A = f"whatsapp:{FONE}:{EMPRESA_A}:agente-a"
SESSAO_B = f"whatsapp:{FONE}:{EMPRESA_B}:agente-b"
CPF_DO_PAI = "52998224725"          # fictício, DV válido
SEGURADORA = "SEGURADORAFICTICIA"
VIGENCIA_FIM = "01/03/2027"
APOLICE = "9000111222333"
PREMIO = "1234,56"

#: tudo o que é DADO da apólice — nada disto pode chegar ao MODELO quando quem fala é o parente.
DADOS_DA_APOLICE = ("ficticia", VIGENCIA_FIM, "01/03/2026", APOLICE, "guincho (200 km)", PREMIO,
                    CPF_DO_PAI, "529.982.247-25", "ZZZ9Z99")


# =========================================================================== #
# A BORDA DO BANCO — em memória, e filtra DE VERDADE (eq · in · like · gte · order · limit)
# =========================================================================== #
class _Resp:
    def __init__(self, data):
        self.data = data
        self.count = len(data) if isinstance(data, list) else None


class _Q:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.op, self.dados, self.filtros = "select", None, []
        self._limite, self._ordem, self._unico = None, None, False

    # operações
    def select(self, *_a, **_k):
        return self

    def insert(self, dados, **_k):
        self.op, self.dados = "insert", dados
        return self

    upsert = insert

    def update(self, dados, **_k):
        self.op, self.dados = "update", dados
        return self

    def delete(self, **_k):
        self.op = "delete"
        return self

    # filtros
    def eq(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: str(l.get(c)) == str(v))
        return self

    def neq(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: str(l.get(c)) != str(v))
        return self

    def in_(self, c, vs):
        vs = {str(x) for x in (vs or [])}
        self.filtros.append(lambda l, c=c: str(l.get(c)) in vs)
        return self

    def like(self, c, padrao):
        prefixo = str(padrao).rstrip("%")
        self.filtros.append(lambda l, c=c: str(l.get(c) or "").startswith(prefixo))
        return self

    def gte(self, c, v):
        self.filtros.append(lambda l, c=c, v=v: str(l.get(c) or "") >= str(v))
        return self

    def order(self, c, desc=False, **_k):
        self._ordem = (c, desc)
        return self

    def limit(self, n, **_k):
        self._limite = int(n)
        return self

    def single(self):
        self._unico = True
        return self

    maybe_single = single

    def __getattr__(self, _nome):          # is_, ilike, lt, range… — aceita e ignora
        return lambda *_a, **_k: self

    @property
    def not_(self):
        return self

    def execute(self):
        linhas = self.banco.tabelas.setdefault(self.tabela, [])
        if self.op == "insert":
            novas = []
            for l in (self.dados if isinstance(self.dados, list) else [self.dados]):
                l = dict(l or {})
                l.setdefault("id", str(uuid.uuid4()))
                l.setdefault("created_at", self.banco.agora())
                linhas.append(l)
                novas.append(copy.deepcopy(l))
            return _Resp(novas)
        alvo = [l for l in linhas if all(f(l) for f in self.filtros)]
        if self.op == "update":
            for l in alvo:
                l.update(copy.deepcopy(self.dados or {}))
            return _Resp([copy.deepcopy(l) for l in alvo])
        if self.op == "delete":
            for l in alvo:
                linhas.remove(l)
            return _Resp([])
        if self._ordem:
            alvo = sorted(alvo, key=lambda l: str(l.get(self._ordem[0]) or ""), reverse=self._ordem[1])
        dados = [copy.deepcopy(l) for l in alvo][: self._limite]
        if self._unico:
            return _Resp(dados[0] if dados else None)
        return _Resp(dados)


class Banco:
    """O Supabase de mentira — `.client` aponta para ele mesmo (o motor faz unwrap)."""

    def __init__(self):
        self.tabelas: dict = {
            # o Registry: as duas ferramentas que tocam apólice estão publicadas (📊 02/10/2026,
            # `select tool_key … from tool_definitions` → insurance.policy_lookup / insurer_dispatch)
            "tool_definitions": [
                {"id": "td-1", "tool_key": "insurance.policy_lookup", "is_active": True,
                 "capability_key": "operational.infocap.policy_lookup.read"},
                {"id": "td-2", "tool_key": "insurance.insurer_dispatch", "is_active": True,
                 "capability_key": "operational.insurer.dispatch"}],
            "tool_releases": [
                {"id": "tr-1", "tool_id": "td-1", "status": "published", "is_default": True},
                {"id": "tr-2", "tool_id": "td-2", "status": "published", "is_default": True}],
        }
        self.client = self
        self._relogio = 0

    def agora(self) -> str:
        # um relógio que ANDA: cada escrita é um instante diferente (a ordem importa)
        self._relogio += 1
        return datetime.now(timezone.utc).replace(microsecond=self._relogio % 999999).isoformat()

    def table(self, nome):
        return _Q(self, nome)

    from_ = table

    def rpc(self, *_a, **_k):
        return _Q(self, "_rpc")


# =========================================================================== #
# A BORDA DO PROVEDOR — a porta `get_policy_data_provider`
# =========================================================================== #
def resultado_found(apolice: str = APOLICE, produto: str = "AUTO", nome: str = "J*** C***") -> dict:
    sel = {"policy_ref": None, "policy_locator": None, "policy_locator_ref": None,
           "insurer_key": SEGURADORA, "product": produto, "policy_status": "ativo",
           "masked_policy_number": "****", "holder_name_masked": nome,
           "policy_number": apolice, "valid_from": "01/03/2026", "valid_to": VIGENCIA_FIM,
           "active_now": True, "expired": False, "coverages_count": 1, "cancelled": False,
           "premium": PREMIO,
           "coverages": [{"name": "Assistencia 24h - guincho (200 km)"}]}
    return {"ok": True, "status": "found", "result_count": 1, "matched_by": "document",
            "identity_status": "identity_verified", "client_name_masked": nome,
            "client_document_masked": "****-*", "selected": dict(sel), "matches": [dict(sel)],
            "client_ref": {"codigo": "1", "codfil": "1"}}


class Provedor:
    """Devolve a apólice que o teste mandar, por documento (ou a padrão)."""

    def __init__(self, por_documento: dict | None = None, sequencia: list | None = None):
        self.por_documento = dict(por_documento or {})
        self.sequencia = list(sequencia or [])
        self.consultas: list = []

    async def lookup(self, *, company_id, document=None, **_k):
        self.consultas.append((company_id, document))
        if self.sequencia:
            return copy.deepcopy(self.sequencia.pop(0))
        return copy.deepcopy(self.por_documento.get(document) or resultado_found())

    async def detail(self, **_k):
        return resultado_found()

    async def vehicle(self, **_k):
        return {"ok": True, "vehicle": {"placa": "ZZZ9Z99", "veiculo": "CARRO FICTICIO"}}


@pytest.fixture
def borda(monkeypatch):
    """Banco e provedor na BORDA; o resto é o produto. Devolve `(banco, provedor)`."""
    import app.core.database as DB
    import app.providers.policy_data_provider as P
    import app.services.skills.invocation_recorder as IR

    banco, prov = Banco(), Provedor()

    async def _cliente_async():
        return banco

    async def _redis_fora():
        raise RuntimeError("sem redis no teste")

    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-de-teste-sem-rede")
    monkeypatch.setenv("POLICY_INTELLIGENCE_V2", "true")
    monkeypatch.setenv("POLICY_CONTEXT_HMAC_KEY", "chave-hmac-de-teste")
    monkeypatch.setattr(DB, "create_async_supabase_client", _cliente_async)
    monkeypatch.setattr(DB, "get_supabase_client", lambda *_a, **_k: banco, raising=False)
    monkeypatch.setattr(P, "get_policy_data_provider", lambda *_a, **_k: prov)
    monkeypatch.setattr(IR, "_CATALOGO", {})        # o cache do Registry é de PROCESSO
    import app.core.redis as R

    monkeypatch.setattr(R, "get_async_redis_client", _redis_fora)
    return banco, prov


def estado(mensagens: list, *, empresa: str = EMPRESA_A, sessao: str = SESSAO_A) -> dict:
    return {"company_id": empresa, "user_id": "teste", "session_id": sessao, "company_config": {},
            "agent_data": {"id": None, "agent_role": "attendance", "tools_config": {}},
            "messages": list(mensagens), "tools_used": [], "rag_chunks": [], "rag_search_time_ms": 0,
            "infocap_policy_context": None, "policy_response_contract": None, "internal_steps": []}


def consultar_pelo_motor(falas: list, documento: str, *, empresa: str = EMPRESA_A,
                         sessao: str = SESSAO_A) -> dict:
    """UM turno do `tool_node` real: as falas do segurado + a chamada do modelo."""
    msgs = [HumanMessage(content=f) for f in falas]
    msgs.append(AIMessage(content="", tool_calls=[{"name": "infocap_policy_lookup",
                                                   "args": {"document": documento},
                                                   "id": "call-%s" % uuid.uuid4().hex[:6]}]))
    tool = T.InfocapPolicyLookupTool(company_id=empresa, agent_role="attendance")
    return asyncio.run(N.tool_node(estado(msgs, empresa=empresa, sessao=sessao), tools=[tool]))


def o_que_o_modelo_le(saida: dict) -> str:
    return "\n".join(str(m.content) for m in saida.get("messages") or [])


def dados_no(texto: str) -> list:
    return [d for d in DADOS_DA_APOLICE if d.lower() in str(texto).lower()]


# =========================================================================== #
# G3 · O TESTE DO FIO
# =========================================================================== #
FILHO_PEDE_GUINCHO = ["sou o filho dele, o carro quebrou, preciso de guincho",
                      f"o cpf dele é {CPF_DO_PAI}"]


def _com_conversa(banco, empresa=EMPRESA_A, sessao=SESSAO_A):
    """A conversa do atendimento existe — é nela que a ficha durável é gravada."""
    banco.tabelas.setdefault("conversations", []).append(
        {"id": "conv-%s" % uuid.uuid4().hex[:6], "company_id": empresa, "session_id": sessao,
         "channel": "whatsapp", "ficha_atendimento": None})


def _placa_na_ficha(banco) -> bool:
    fichas = [c.get("ficha_atendimento") for c in banco.tabelas.get("conversations", [])]
    return "ZZZ9Z99" in json.dumps(fichas, default=str)


def test_fio_o_filho_que_pede_guincho_aciona_sem_ver_dado_da_apolice(borda):
    banco, prov = borda
    _com_conversa(banco)
    saida = consultar_pelo_motor(FILHO_PEDE_GUINCHO, CPF_DO_PAI)
    le = o_que_o_modelo_le(saida)

    assert prov.consultas, "a consulta tem de ter ido ao provedor (o corte é DEPOIS dela)"
    # ① AUTORIZADO A ACIONAR — sem o titular junto
    assert le != T.TEXTO_DA_APOLICE_DE_TERCEIRO, "o filho que pede SERVIÇO foi barrado como pedido de dado"
    assert "pode acionar" in le.lower(), le
    assert "primeiro nome" in le.lower() and "vinculo" in le.lower(), "o agente confirma nome e vínculo"
    assert "telefone de contato" in le.lower() and "quem fala" in le.lower(), le
    # e o acionamento ACHA a apólice: o contexto do caso nasceu (é dele que o insurer_dispatch lê)
    ctx = saida.get("infocap_policy_context") or {}
    assert [a.get("numapo") for a in ctx.get("apolices") or []] == [APOLICE], ctx
    # ② NENHUM dado da apólice no que volta ao modelo
    assert dados_no(le) == [], "dado da apólice do PAI chegou ao modelo: %s" % dados_no(le)
    for palavra in ("valendo", "vigente", "ramo auto"):
        assert palavra not in le.lower(), palavra
    # ③ a ficha "do sistema" NÃO ganhou a placa do titular (o bloco do prompt mandaria confirmá-la)
    assert any(c.get("ficha_atendimento") for c in banco.tabelas["conversations"]), \
        "a ficha não foi gravada — sem gravação a asserção abaixo passaria por vácuo"
    assert not _placa_na_ficha(banco)


def test_controle_me_passa_a_apolice_do_meu_pai_continua_negado(borda):
    """§9.2 — a linha de controle: o MESMO caminho, pedindo DADO, é o corte de hoje."""
    saida = consultar_pelo_motor([f"me passa a apolice do meu pai, o cpf dele é {CPF_DO_PAI}"], CPF_DO_PAI)
    le = o_que_o_modelo_le(saida)
    assert le == T.TEXTO_DA_APOLICE_DE_TERCEIRO, le
    assert dados_no(le) == [] and not saida.get("infocap_policy_context")


@pytest.mark.parametrize("falas", [
    ["sou o filho dele, ele autorizou, me passa o numero da apolice", f"cpf {CPF_DO_PAI}"],
    ["o carro do meu pai quebrou, preciso de guincho", f"o cpf dele é {CPF_DO_PAI}",
     "ele autorizou, qual a vigencia da apolice dele?"],
    ["minha esposa autorizou, quanto e o premio do seguro dela? cpf dela " + CPF_DO_PAI],
])
def test_pedir_dado_com_ou_sem_ela_autorizou_continua_negado(borda, falas):
    le = o_que_o_modelo_le(consultar_pelo_motor(falas, CPF_DO_PAI))
    assert le == T.TEXTO_DA_APOLICE_DE_TERCEIRO, (falas, le)
    assert dados_no(le) == []


def test_o_texto_do_corte_nao_diz_mais_titular_junto():
    """§9.3 — a verdade vencida migrou: o corte vale só para DADO e não manda o parente
    trazer o titular para acionar."""
    assert "JUNTO" not in T.TEXTO_DA_APOLICE_DE_TERCEIRO.upper().replace("JUNTO DE", "")
    assert "titular autorizou" in T.TEXTO_DA_APOLICE_DE_TERCEIRO
    assert not hasattr(T, "_RX_TITULAR_AUTORIZOU")


def test_o_texto_do_parente_nao_carrega_dado_mesmo_com_a_apolice_inteira():
    """PURA: o texto ao modelo do parente não lê NADA do `data` (nem ramo, nem vigência)."""
    texto = T.texto_do_titular_autorizado(resultado_found())
    assert dados_no(texto) == [] and "AUTO" not in texto


def test_o_titular_que_fala_continua_recebendo_os_dados(borda):
    """CONTROLE (§9.3): o mesmo motor CONSEGUE trazer os dados — o corte não é cegueira —
    e a placa vai para a ficha (prova que a asserção ③ do fio consegue ficar vermelha)."""
    banco, _ = borda
    _com_conversa(banco)
    le = o_que_o_modelo_le(consultar_pelo_motor(
        ["meu carro quebrou, preciso de guincho", f"meu cpf é {CPF_DO_PAI}"], CPF_DO_PAI))
    assert "pode acionar o servico pedido para o titular" not in le.lower()
    assert dados_no(le), "o controle tem de provar que o caminho consegue entregar dado"
    assert _placa_na_ficha(banco), "o titular tem a placa na ficha — senão a ③ do fio é carimbo"


# =========================================================================== #
# A régua pura — os casos de fronteira do D1
# =========================================================================== #
@pytest.mark.parametrize("falas,terceiro,autorizado", [
    (FILHO_PEDE_GUINCHO, True, True),
    (["sou a esposa dele, preciso de um chaveiro pro carro", CPF_DO_PAI], True, True),
    ([f"o carro é da minha mae, cpf dela {CPF_DO_PAI}", "manda um guincho por favor"], True, True),
    # o pedido ATUAL é dado → negado, mesmo com serviço antes
    (["o carro do meu pai quebrou, preciso de guincho", f"o cpf dele é {CPF_DO_PAI}",
      "me passa a apolice dele"], True, False),
    # pergunta de cobertura, com o documento entregue DEPOIS numa fala curta → continua dado
    (["minha mae pediu pra eu ver se o seguro dela cobre vidro", f"o cpf dela é {CPF_DO_PAI}"], True, False),
    # CONTROLE: o titular não é terceiro
    ([f"meu cpf é {CPF_DO_PAI}, preciso de guincho"], False, False),
    (["sou o dono do carro, preciso de guincho", CPF_DO_PAI], False, False),
])
def test_a_regra_pura_do_parente(falas, terceiro, autorizado):
    r = T.de_quem_e_a_apolice(CPF_DO_PAI, falas)
    assert (r["terceiro"], r["autorizado"]) == (terceiro, autorizado), r


def test_proprio_so_quando_o_documento_e_dito_como_dele():
    """D-126-C (para a contagem do D2): "meu cpf" → próprio; CPF solto → não sabemos."""
    assert T.de_quem_e_a_apolice(CPF_DO_PAI, [f"meu cpf é {CPF_DO_PAI}"])["proprio"] is True
    assert T.de_quem_e_a_apolice(CPF_DO_PAI, [CPF_DO_PAI])["proprio"] is False
    assert T.de_quem_e_a_apolice(CPF_DO_PAI, FILHO_PEDE_GUINCHO)["proprio"] is False

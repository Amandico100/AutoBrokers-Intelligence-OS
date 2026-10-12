"""SPEC-130-B · F2 — as fontes do CORP chegam ao leitor, e o estado da leitura sai da porta.

O que este arquivo prova (o contrato da fatia F2, SPEC §4/§5):

  1. sem `url_apolice`, o conector consulta `/documento_anexos` e entrega ao leitor o
     anexo da APÓLICE (nunca endosso; o mais recente) — e o PORTÃO
     `official_document_source_available` passa a enxergar essa fonte;
  2. com `url_apolice`, `/documento_anexos` NÃO é consultado (a linha de controle);
  3. `/documento_anexos` caído = sem candidato, sem exceção;
  4. o `preliq` do `/documento` chega ao serviço como `premio_liquido_esperado`
     (só quando a assinatura aceita — o serviço da F1 está sendo escrito em paralelo);
  5. `/itens` recebe `data=` presa na vigência (antes · durante · depois), e a chave do
     cache muda com a data;
  6. `apolice_documental_do_pack` carrega `tipo_documento`/`leitura`/`objeto_do_risco`
     quando o contrato os tem, e "ausência de LEITURA não é ausência de COBERTURA";
  7. o bloco `documento` do retorno da tool não carrega PII, e o atendimento recebe a
     marca da leitura não conferida;
  8. duas corretoras não trocam candidato nem cache.

⛔ Dublê SÓ na borda: HTTP (httpx.MockTransport), Redis (em memória) e o serviço de
leitura (a F1 é dona do motor). Nenhuma chamada real à InfoCap, ao modelo ou ao banco.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import re
import sys
import types
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
import pytest

import app.api.infocap_connector as C

EMPRESA_A = "empresa-a-130b"
EMPRESA_B = "empresa-b-130b"
CONEXAO_A = "conexao-a-130b"
CONEXAO_B = "conexao-b-130b"
URL_A = "https://anexos.example.test/a/apolice-nova.pdf?Signature=AAA"
URL_B = "https://anexos.example.test/b/apolice-nova.pdf?Signature=BBB"


def _rodar(corrotina):
    return asyncio.run(corrotina)


# ---------------------------------------------------------------------------
# A BORDA: Redis em memória (nunca o Redis de verdade) e o serviço de leitura
# ---------------------------------------------------------------------------
class _RedisDeMentira:
    def __init__(self):
        self.dados: Dict[str, str] = {}
        self.lidas: List[str] = []
        self.gravadas: List[str] = []

    async def get(self, chave):
        self.lidas.append(chave)
        return self.dados.get(chave)

    async def setex(self, chave, _ttl, valor):
        self.gravadas.append(chave)
        self.dados[chave] = valor


@pytest.fixture(autouse=True)
def _redis_em_memoria(monkeypatch):
    redis = _RedisDeMentira()
    casca = types.ModuleType("app.core.redis")

    async def _get_async_redis_client():
        return redis

    casca.get_async_redis_client = _get_async_redis_client
    monkeypatch.setitem(sys.modules, "app.core.redis", casca)
    return redis


class _ServicoQueAnota:
    """O serviço de leitura com a assinatura do CONTRATO §4 (com o kwarg novo)."""

    def __init__(self, resultado: Optional[Dict[str, Any]] = None):
        self.chamadas: List[Dict[str, Any]] = []
        self.resultado = resultado or _resultado_da_leitura()

    async def ensure_official_policy_evidence(
        self, *, company_id, policy_locator, official_document_candidate, question, fetcher,
        agent_id=None, force_refresh=False, case_id=None, connection_id="",
        premio_liquido_esperado=None,
    ):
        self.chamadas.append({
            "company_id": company_id, "candidato": dict(official_document_candidate or {}),
            "connection_id": connection_id, "premio_liquido_esperado": premio_liquido_esperado,
        })
        return dict(self.resultado)


class _ServicoDeOntem:
    """A assinatura de HOJE (sem o kwarg). O conector não pode quebrar com ela."""

    def __init__(self):
        self.chamadas: List[Dict[str, Any]] = []

    async def ensure_official_policy_evidence(
        self, *, company_id, policy_locator, official_document_candidate, question, fetcher,
        agent_id=None, force_refresh=False, case_id=None, connection_id="",
    ):
        self.chamadas.append({"candidato": dict(official_document_candidate or {})})
        return _resultado_da_leitura()


def _resultado_da_leitura(estado: str = "fechou", linhas: int = 2) -> Dict[str, Any]:
    itens = [
        {"page_number": 2, "evidence_type": "coverage_row", "evidence_text": "Incendio 100.000,00 500,00",
         "structured": {"kind": "coverage_row", "label": "Incendio", "lmi": "100000.00", "premium": "500.00"}},
        {"page_number": 2, "evidence_type": "coverage_row", "evidence_text": "Danos eletricos 10.000,00 646,91",
         "structured": {"kind": "coverage_row", "label": "Danos eletricos", "lmi": "10000.00", "premium": "646.91"}},
    ][:linhas]
    return {
        "ok": True, "document_status": "evidence_ready", "cache_status": "miss",
        "evidence_items": itens, "evidence_count": len(itens),
        "leitura": {
            "leitor_versao": "130B.1", "tipo_documento": "apolice", "estado": estado,
            "degraus": ["regex", "juiz"], "linhas": len(itens),
            "soma_linhas": Decimal("1146.91") if estado == "fechou" else Decimal("500.00"),
            "premio_esperado": Decimal("1146.91"), "fonte_do_esperado": "corp_documento",
            "diferenca": Decimal("0.00") if estado == "fechou" else Decimal("646.91"),
            "paginas": 6, "paginas_sem_texto": 0, "custo_usd": 0.0, "modelo": None, "duracao_s": 0.2,
        },
        "objeto_do_risco": {"cep": "01310-100", "atividade": "residencia habitual"},
    }


@pytest.fixture
def servico(monkeypatch):
    import app.services.policy_document_evidence_service as S

    dub = _ServicoQueAnota()
    monkeypatch.setattr(S, "get_policy_document_evidence_service", lambda: dub)
    return dub


# ---------------------------------------------------------------------------
# A BORDA HTTP: o CORP dublado por MockTransport (o cliente httpx é o REAL)
# ---------------------------------------------------------------------------
_ANEXOS_DA_APOLICE = {"anexos": [
    {"nome": "PROPOSTA", "tipo": "pdf", "descricao": "", "datahora": "01/02/2026 10:00:00",
     "url": "https://anexos.example.test/proposta.pdf?Signature=P", "indice_anexo": 1},
    {"nome": "APÓLICE ENDOSSO 1", "tipo": "pdf", "descricao": "", "datahora": "20/05/2026 08:00:00",
     "url": "https://anexos.example.test/endosso.pdf?Signature=E", "indice_anexo": 4},
    {"nome": "APÓLICE RESIDENCIAL", "tipo": "pdf", "descricao": "", "datahora": "10/03/2026 09:00:00",
     "url": "https://anexos.example.test/apolice-velha.pdf?Signature=V", "indice_anexo": 2},
    {"nome": "APOLICE", "tipo": "pdf", "descricao": "", "datahora": "12/03/2026 09:00:00",
     "url": URL_A, "indice_anexo": 3},
    {"nome": "BOLETO", "tipo": "pdf", "descricao": "", "datahora": "15/03/2026 09:00:00",
     "url": "https://anexos.example.test/boleto.pdf?Signature=B", "indice_anexo": 5},
]}


def _envelope(*, com_url: bool, inivig: str = "01/03/2026", fimvig: str = "01/03/2027",
              preliq: Any = "1146.91", nosnum: int = 777001) -> Dict[str, Any]:
    acompanhamento: Dict[str, Any] = {"emissao": {}}
    if com_url:
        acompanhamento["emissao"]["url_apolice"] = "https://anexos.example.test/url-apolice.pdf?Signature=U"
    return {
        "documento": [{
            "codfil": 1, "nosnum": nosnum, "numapo": "9900112233", "inivig": inivig, "fimvig": fimvig,
            "preliq": preliq, "pretot": "1230.00", "seguradora_abrev": "ALLI", "ramo_abrev": "RESI",
            "cancelado": "F",
        }],
        "acompanhamento": [acompanhamento],
    }


class _Corp:
    """O CORP de mentira: anota cada GET (caminho + params) e responde por rota."""

    def __init__(self, *, envelope, anexos=_ANEXOS_DA_APOLICE, anexos_status=200, itens_sem_data=200):
        self.envelope = envelope
        self.anexos = anexos
        self.anexos_status = anexos_status
        self.itens_sem_data = itens_sem_data
        self.pedidos: List[tuple] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        caminho = request.url.path
        params = dict(request.url.params)
        self.pedidos.append((caminho, params))
        if caminho == "/login":
            return httpx.Response(200, json={"token": "tk-de-teste"})
        if caminho == "/documento":
            return httpx.Response(200, json=self.envelope)
        if caminho == "/itens":
            # 📊 laudo 131-0: sem `data`, /itens dá 404 para apólice que ainda não começou.
            if "data" not in params and self.itens_sem_data != 200:
                return httpx.Response(self.itens_sem_data, json={"message": "nao encontrado"})
            return httpx.Response(200, json={"itens": [{"item": 1, "garantias": [
                {"descricao": "INCENDIO", "lmi": 100000.0, "premio": 500.0}]}]})
        if caminho == "/documento_anexos":
            if self.anexos_status >= 400:
                return httpx.Response(self.anexos_status, json={"message": "erro"})
            return httpx.Response(200, json=self.anexos)
        return httpx.Response(404, json={"message": "rota desconhecida"})

    def chamou(self, caminho: str) -> int:
        return sum(1 for c, _ in self.pedidos if c == caminho)


def _cliente(corp: _Corp) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url="https://corp.example.test", transport=httpx.MockTransport(corp))


def _payload(pergunta: str = "quais as coberturas da minha apolice?"):
    return types.SimpleNamespace(user_query=pergunta, document_evidence_requested=True,
                                 force_document_evidence_refresh=False)


def _pack_de(envelope, *, company_hint: str = "") -> Dict[str, Any]:
    doc = C._extract_documents(envelope)[0]
    return C._build_evidence_pack(doc, None, None, False, envelope=envelope, items=[])


async def _anexar(corp: _Corp, envelope, *, company_id=EMPRESA_A, connection_id=CONEXAO_A):
    async with _cliente(corp) as client:
        return await C._maybe_attach_official_policy_document_evidence(
            pack=_pack_de(envelope), detail_envelope=envelope, payload=_payload(),
            company_id=company_id, token="tk-de-teste", auth_cookies=None,
            connection_id=connection_id, client=client, headers={"Authorization": "tk-de-teste"},
        )


# ===========================================================================
# 1–3 · /documento_anexos
# ===========================================================================
def test_sem_url_apolice_o_candidato_vem_dos_anexos_e_o_portao_abre(servico):
    env = _envelope(com_url=False)
    assert _pack_de(env)["official_document_source_available"] is False  # o portão de ANTES
    corp = _Corp(envelope=env)
    pack = _rodar(_anexar(corp, env))

    assert corp.chamou("/documento_anexos") == 1
    assert corp.pedidos[0][1] == {"codfil": "1", "nosnum": "777001"}
    assert len(servico.chamadas) == 1, "o leitor tem de ser chamado com o anexo"
    cand = servico.chamadas[0]["candidato"]
    assert cand["source_kind"] == "policy_pdf"
    assert cand["source_path"] == "documento_anexos"
    assert cand["url"] == URL_A, "o anexo da APÓLICE mais recente — nunca endosso, proposta ou boleto"
    assert pack["official_document_source_available"] is True
    assert pack["official_document_source"] == "documento_anexos"
    assert pack["document_evidence_ready"] is True
    # ⛔ a URL assinada não volta no pack
    assert URL_A not in json.dumps(pack, default=str)


def test_controle_com_url_apolice_os_anexos_nao_sao_consultados(servico):
    env = _envelope(com_url=True)
    corp = _Corp(envelope=env)
    _rodar(_anexar(corp, env))
    assert corp.chamou("/documento_anexos") == 0
    assert servico.chamadas[0]["candidato"]["source_path"] == "acompanhamento.emissao.url_apolice"


def test_anexos_500_sem_candidato_e_sem_excecao(servico):
    env = _envelope(com_url=False)
    corp = _Corp(envelope=env, anexos_status=500)
    pack = _rodar(_anexar(corp, env))
    assert corp.chamou("/documento_anexos") == 1
    assert servico.chamadas == []
    assert pack["official_document_source_available"] is False
    assert "official_policy_document_evidence" not in pack  # o pack de ANTES, intacto


def test_anexos_200_com_message_sem_anexo_e_sem_candidato(servico):
    env = _envelope(com_url=False)
    corp = _Corp(envelope=env, anexos={"message": "Nenhum anexo encontrado"})
    pack = _rodar(_anexar(corp, env))
    assert servico.chamadas == []
    assert pack["official_document_source_available"] is False


def test_so_endosso_e_proposta_nos_anexos_nao_vira_apolice(servico):
    env = _envelope(com_url=False)
    so_endosso = {"anexos": [a for a in _ANEXOS_DA_APOLICE["anexos"]
                             if "ENDOSSO" in a["nome"] or a["nome"] in ("PROPOSTA", "BOLETO")]}
    corp = _Corp(envelope=env, anexos=so_endosso)
    _rodar(_anexar(corp, env))
    assert servico.chamadas == []


def test_escolha_do_anexo_e_pura_e_prefere_o_mais_recente():
    escolhido = C._select_policy_attachment(_ANEXOS_DA_APOLICE)
    assert escolhido and escolhido["url"] == URL_A
    # descrição também conta; sem data, vence o maior índice
    por_descricao = {"anexos": [
        {"nome": "arquivo1", "descricao": "Apólice do seguro", "url": "https://x.example.test/1.pdf", "indice_anexo": 1},
        {"nome": "arquivo2", "descricao": "APÓLICE", "url": "https://x.example.test/2.pdf", "indice_anexo": 7},
        {"nome": "arquivo3.doc", "descricao": "APÓLICE", "tipo": "doc", "url": "https://x.example.test/3.doc", "indice_anexo": 9},
    ]}
    assert C._select_policy_attachment(por_descricao)["url"] == "https://x.example.test/2.pdf"
    assert C._select_policy_attachment({"message": "sem anexos"}) is None
    assert C._select_policy_attachment(None) is None


def test_sem_cliente_http_o_conector_se_comporta_como_antes(servico):
    """O caminho de quem chama sem `client` (auditoria, testes antigos) não muda."""
    env = _envelope(com_url=False)

    async def _sem_cliente():
        return await C._maybe_attach_official_policy_document_evidence(
            pack=_pack_de(env), detail_envelope=env, payload=_payload(),
            company_id=EMPRESA_A, token="", auth_cookies=None)

    pack = _rodar(_sem_cliente())
    assert servico.chamadas == []
    assert "official_policy_document_evidence" not in pack


# ===========================================================================
# 4 · o prêmio esperado chega ao leitor
# ===========================================================================
@pytest.mark.parametrize("preliq,esperado", [
    ("1146.91", Decimal("1146.91")),
    (24960.6, Decimal("24960.60")),
    ("1.146,91", Decimal("1146.91")),
    (0, None), ("0.00", None), (None, None), ("", None),
])
def test_o_preliq_chega_ao_servico(servico, preliq, esperado):
    env = _envelope(com_url=True, preliq=preliq)
    _rodar(_anexar(_Corp(envelope=env), env))
    assert servico.chamadas[0]["premio_liquido_esperado"] == esperado


def test_sem_preliq_no_envelope_vale_o_mesmo_preliq_do_pack():
    """O fio da F1 entrega só o pack (`premium_summary.net_premium`, o MESMO `preliq` formatado)."""
    pack = {"premium_summary": {"net_premium": {"label": "Prêmio líquido", "value": "R$ 31.875,90",
                                                "provider_field": "preliq"}}}
    assert C._expected_net_premium({}, pack) == Decimal("31875.90")
    # o envelope vence quando tem o cru
    assert C._expected_net_premium(_envelope(com_url=True, preliq="100.00"), pack) == Decimal("100.00")
    assert C._expected_net_premium({}, {}) is None


def test_servico_com_a_assinatura_de_ontem_nao_quebra(monkeypatch):
    import app.services.policy_document_evidence_service as S

    dub = _ServicoDeOntem()
    monkeypatch.setattr(S, "get_policy_document_evidence_service", lambda: dub)
    env = _envelope(com_url=True)
    pack = _rodar(_anexar(_Corp(envelope=env), env))
    assert len(dub.chamadas) == 1
    assert pack["official_policy_document_evidence"]["document_status"] == "evidence_ready"


# ===========================================================================
# 5 · /itens?data=
# ===========================================================================
HOJE = date(2026, 10, 11)


@pytest.mark.parametrize("inivig,fimvig,esperado", [
    ("01/12/2026", "01/12/2027", "01/12/2026"),   # renovação ainda não iniciada → o início
    ("01/03/2026", "01/03/2027", "11/10/2026"),   # vigente → hoje
    ("01/03/2025", "01/03/2026", "01/03/2026"),   # vencida → o fim
    ("2026-03-01", "2027-03-01", "11/10/2026"),   # formato ISO também
    (None, None, None),                            # sem vigência → como hoje (sem data)
    ("lixo", "01/03/2027", "11/10/2026"),           # só o fim legível
])
def test_data_de_referencia_dos_itens(inivig, fimvig, esperado):
    assert C._itens_reference_date(inivig, fimvig, hoje=HOJE) == esperado


def _itens(corp, *, valid_from, valid_to, company_id=EMPRESA_A, connection_id=CONEXAO_A):
    async def _go():
        async with _cliente(corp) as client:
            return await C._fetch_policy_items(
                client, {"Authorization": "tk"}, itens_path="/itens", codfil=1, nosnum=777001,
                company_id=company_id, connection_id=connection_id,
                valid_from=valid_from, valid_to=valid_to, hoje=HOJE)
    return _rodar(_go())


@pytest.mark.parametrize("inivig,fimvig,esperado", [
    ("01/12/2026", "01/12/2027", "01/12/2026"),
    ("01/03/2026", "01/03/2027", "11/10/2026"),
    ("01/03/2025", "01/03/2026", "01/03/2026"),
])
def test_itens_recebe_data_dentro_da_vigencia(inivig, fimvig, esperado, _redis_em_memoria):
    corp = _Corp(envelope={}, itens_sem_data=404)
    itens = _itens(corp, valid_from=inivig, valid_to=fimvig)
    assert itens, "com a data, a renovação ainda não iniciada devolve os itens"
    (caminho, params), = [p for p in corp.pedidos if p[0] == "/itens"]
    assert params["data"] == esperado
    assert _redis_em_memoria.gravadas[-1].endswith(":" + esperado)


def test_itens_sem_vigencia_vai_sem_data_como_hoje(_redis_em_memoria):
    corp = _Corp(envelope={})
    _itens(corp, valid_from=None, valid_to=None)
    (_, params), = [p for p in corp.pedidos if p[0] == "/itens"]
    assert "data" not in params
    assert _redis_em_memoria.gravadas[-1].endswith(":777001")


def test_a_chave_do_cache_muda_com_a_data(_redis_em_memoria):
    corp = _Corp(envelope={})
    _itens(corp, valid_from="01/12/2026", valid_to="01/12/2027")
    _itens(corp, valid_from="01/03/2026", valid_to="01/03/2027")
    chaves = _redis_em_memoria.gravadas
    assert len(chaves) == 2 and chaves[0] != chaves[1]
    assert corp.chamou("/itens") == 2, "a segunda data NÃO pode servir o item da primeira"


def test_duas_corretoras_nao_trocam_o_cache_dos_itens(_redis_em_memoria):
    corp = _Corp(envelope={})
    _itens(corp, valid_from="01/03/2026", valid_to="01/03/2027", company_id=EMPRESA_A)
    _itens(corp, valid_from="01/03/2026", valid_to="01/03/2027", company_id=EMPRESA_B,
           connection_id=CONEXAO_B)
    a, b = _redis_em_memoria.gravadas
    assert a != b
    assert corp.chamou("/itens") == 2


# ===========================================================================
# 8 · duas corretoras não trocam o candidato
# ===========================================================================
def test_duas_corretoras_nao_trocam_o_candidato(servico):
    env = _envelope(com_url=False)
    anexos_b = {"anexos": [{"nome": "APÓLICE", "datahora": "12/03/2026 09:00:00", "url": URL_B, "indice_anexo": 1}]}
    _rodar(_anexar(_Corp(envelope=env), env, company_id=EMPRESA_A, connection_id=CONEXAO_A))
    _rodar(_anexar(_Corp(envelope=env, anexos=anexos_b), env, company_id=EMPRESA_B, connection_id=CONEXAO_B))
    a, b = servico.chamadas
    assert (a["company_id"], a["connection_id"], a["candidato"]["url"]) == (EMPRESA_A, CONEXAO_A, URL_A)
    assert (b["company_id"], b["connection_id"], b["candidato"]["url"]) == (EMPRESA_B, CONEXAO_B, URL_B)


# ===========================================================================
# O FIO da fatia: rota de detalhe REAL → /login → /documento → /itens?data → /documento_anexos
#                 → serviço (dublê) → pack → porta → bloco da tool
# ===========================================================================
def test_o_fio_do_corp_ate_a_porta(monkeypatch, servico):
    hoje = date.today()
    inicio = hoje + timedelta(days=30)
    env = _envelope(com_url=False, inivig=inicio.strftime("%d/%m/%Y"),
                    fimvig=(inicio + timedelta(days=365)).strftime("%d/%m/%Y"))
    corp = _Corp(envelope=env, itens_sem_data=404)
    cliente_real = httpx.AsyncClient

    def _fabrica(*a, **kw):
        kw["transport"] = httpx.MockTransport(corp)
        return cliente_real(*a, **kw)

    async def _conexao(db, *, company_id, requested_connection_id=None):
        return {"selected_connection": {"id": CONEXAO_A, "encrypted_secret_ref": "cifra",
                                        "connection_config": {"base_url": "https://corp.example.test"}}}

    monkeypatch.setattr(C.httpx, "AsyncClient", _fabrica)
    monkeypatch.setattr(C, "_require_internal_key", lambda _k: None)
    monkeypatch.setattr(C, "_resolve_infocap_connection", _conexao)
    monkeypatch.setattr(C, "get_encryption_service", lambda: types.SimpleNamespace(
        decrypt=lambda _c: json.dumps({"username": "u", "password": "p"})))

    payload = C.InfocapPolicyDetailPayload(
        company_id=EMPRESA_A, tenant_connection_id=CONEXAO_A, policy_ref="infocap:1:777001",
        user_query="quais coberturas tenho?", document_evidence_requested=True)
    resposta = _rodar(C.infocap_policy_detail(payload, None, None))

    assert resposta["ok"] is True, resposta
    (_, itens_params), = [p for p in corp.pedidos if p[0] == "/itens"]
    assert itens_params.get("data") == inicio.strftime("%d/%m/%Y"), "renovação ainda não iniciada → o início"
    assert corp.chamou("/documento_anexos") == 1
    assert servico.chamadas[0]["candidato"]["url"] == URL_A
    assert servico.chamadas[0]["premio_liquido_esperado"] == Decimal("1146.91")
    pack = resposta["policy_evidence_pack"]
    assert pack["coverage_sections"], "os itens da renovação chegaram (antes: 404 sem data)"

    from app.providers.infocap_policy_provider import apolice_documental_do_pack

    pdf = apolice_documental_do_pack(pack)
    assert pdf is not None and len(pdf.linhas) == 2

    from app.agents.tools.infocap_tool import resumo_da_leitura_do_documento

    bloco = resumo_da_leitura_do_documento(resposta)
    assert bloco["estado_da_leitura"] == "fechou" and bloco["fechou"] is True
    assert bloco["document_status"] == "evidence_ready" and bloco["linhas"] == 2


# ===========================================================================
# 6 · a porta
# ===========================================================================
def _campos_novos() -> set:
    from app.providers.policy_data_provider import ApoliceDocumental

    return {f.name for f in dataclasses.fields(ApoliceDocumental)} & {"tipo_documento", "leitura", "objeto_do_risco"}


def test_a_porta_com_leitura_carrega_os_campos_novos():
    from app.providers.infocap_policy_provider import apolice_documental_do_pack

    pack = {"official_policy_document_evidence": _resultado_da_leitura("nao_fechou", linhas=1)}
    pdf = apolice_documental_do_pack(pack)
    assert pdf is not None and len(pdf.linhas) == 1
    novos = _campos_novos()
    if "tipo_documento" in novos:
        assert pdf.tipo_documento == "apolice"
    if "leitura" in novos:
        assert pdf.leitura["estado"] == "nao_fechou"
        assert pdf.leitura["linhas"] == 1
    if "objeto_do_risco" in novos:
        assert pdf.objeto_do_risco["atividade"] == "residencia habitual"


def test_a_porta_sem_leitura_continua_como_antes():
    from app.providers.infocap_policy_provider import apolice_documental_do_pack

    resultado = _resultado_da_leitura()
    resultado.pop("leitura")
    resultado.pop("objeto_do_risco")
    pdf = apolice_documental_do_pack({"official_policy_document_evidence": resultado})
    assert pdf is not None and len(pdf.linhas) == 2
    for campo in _campos_novos():
        assert getattr(pdf, campo) is None


def test_ausencia_de_leitura_nao_e_ausencia_de_cobertura():
    """🔴 F5 (C2, CLAUDE.md §9.3 — a lição MIGRA): SEM leitura registrada e sem linha → `None`
    (continua). COM leitura `nao_fechou` e 0 linhas → `ApoliceDocumental(linhas=())` com a leitura,
    para `reconciliar` acender `documento_nao_conferido` (antes: `None`, e o corretor não era avisado)."""
    from app.providers.infocap_policy_provider import apolice_documental_do_pack

    sem_leitura = _resultado_da_leitura("nao_fechou", linhas=0)
    sem_leitura.pop("leitura")
    assert apolice_documental_do_pack({"official_policy_document_evidence": sem_leitura}) is None

    vazio = _resultado_da_leitura("nao_fechou", linhas=0)
    pdf = apolice_documental_do_pack({"official_policy_document_evidence": vazio})
    assert pdf is not None and pdf.linhas == ()
    assert pdf.leitura["estado"] == "nao_fechou"


def test_a_capacidade_diz_a_verdade_sobre_o_documento():
    from app.providers.infocap_policy_provider import InfoCapProvider

    cap = InfoCapProvider().capacidades()
    nota = cap.notas["documento_oficial"]
    assert "nao le os dois layouts" not in nota, "a nota vencida (P11) saiu"
    assert "documento_anexos" in nota and "cascata" in nota
    # 🔴 F5 (C7, §9.3 — a lição migra): a régua MEDIU; o valor e a nota carregam o número e a data
    assert cap.por_operacao["documento_oficial"] == "SUPORTADA"
    assert "26 de 28" in nota and "11/10/2026" in nota and "nao conferidas" in nota


# ===========================================================================
# 7 · a tool: o bloco `documento` sem PII, e a marca para o atendimento
# ===========================================================================
_PII = [
    re.compile(r"\d{3}\.?\d{3}\.?\d{3}-?\d{2}"),       # CPF
    re.compile(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}"),  # CNPJ
    re.compile(r"\(?\d{2}\)?\s?9?\d{4}-?\d{4}"),        # telefone
    re.compile(r"https?://", re.I),                       # URL
    re.compile(r"@"),                                     # e-mail
    re.compile(r"\d{5}-?\d{3}"),                          # CEP
]


def _data_com(leitura_extra: Optional[Dict[str, Any]] = None, estado="nao_fechou") -> Dict[str, Any]:
    ev = _resultado_da_leitura(estado, linhas=1)
    ev["document_text"] = "Segurado: FULANO CPF 123.456.789-09 tel (11) 98765-4321 https://x.example.test"
    if leitura_extra:
        ev["leitura"].update(leitura_extra)
    return {"ok": True, "status": "found", "policy_evidence_pack": {"official_policy_document_evidence": ev}}


def test_bloco_documento_sem_pii():
    from app.agents.tools.infocap_tool import resumo_da_leitura_do_documento

    # 🔴 valores HOSTIS onde o contrato espera enum: o filtro tem de derrubá-los
    hostil = {"leitor_versao": "123.456.789-09", "estado": "https://x.example.test/a",
              "degraus": ["regex", "fulano@x.example.test", "11987654321"]}
    for data in (_data_com(), _data_com(hostil)):
        bloco = resumo_da_leitura_do_documento(data)
        assert bloco is not None
        texto = json.dumps(bloco, ensure_ascii=False, default=str)
        for padrao in _PII:
            assert not padrao.search(texto), (padrao.pattern, texto)
        assert set(bloco) <= {"document_status", "cache_status", "estado_da_leitura", "degraus",
                              "linhas", "fechou", "leitor_versao"}
    normal = resumo_da_leitura_do_documento(_data_com())
    assert normal == {"document_status": "evidence_ready", "cache_status": "miss",
                      "estado_da_leitura": "nao_fechou", "degraus": ["regex", "juiz"],
                      "linhas": 1, "fechou": False, "leitor_versao": "130B.1"}
    assert resumo_da_leitura_do_documento({"ok": True}) is None
    assert resumo_da_leitura_do_documento({"policy_evidence_pack": {}}) is None


def _briefing(data, client_facing):
    from app.agents.tools.infocap_tool import InfocapPolicyLookupTool

    meta = {"facts": [], "text": "rascunho", "cobertura": None}
    return InfocapPolicyLookupTool._build_llm_briefing(data, meta, "tenho cobertura de incendio?",
                                                       client_facing=client_facing)


def test_o_atendimento_recebe_a_marca_da_leitura_nao_conferida():
    texto = _briefing(_data_com(estado="nao_fechou"), client_facing=True)
    assert "a leitura do documento nao foi conferida" in texto
    assert "R$ 500,00 de R$ 1.146,91" in texto
    assert "NAO afirme que a lista de coberturas esta completa" in texto


def test_controle_leitura_que_fechou_nao_leva_marca():
    texto = _briefing(_data_com(estado="fechou"), client_facing=True)
    assert "a leitura do documento nao foi conferida" not in texto


def test_o_texto_do_corretor_nao_muda(monkeypatch):
    """⛔ A marca é do ATENDIMENTO: com ela desligada, o briefing do CORRETOR é byte a byte o
    mesmo (o aviso `documento_nao_conferido` que ele recebe é da PORTA, F1 — não desta fatia)."""
    import app.agents.tools.infocap_tool as T

    data = _data_com(estado="nao_fechou")
    com = _briefing(data, client_facing=False)
    assert "a leitura do documento nao foi conferida" not in com
    monkeypatch.setattr(T, "_linha_da_leitura_nao_conferida", lambda _pack: None)
    sem = _briefing(data, client_facing=False)
    assert com == sem
    # e o PAR: no atendimento, desligar a marca MUDA o texto (o guarda consegue ficar vermelho)
    monkeypatch.undo()
    atendimento = _briefing(data, client_facing=True)
    monkeypatch.setattr(T, "_linha_da_leitura_nao_conferida", lambda _pack: None)
    assert _briefing(data, client_facing=True) != atendimento

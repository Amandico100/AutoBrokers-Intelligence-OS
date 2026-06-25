"""R1C.1 - Official policy evidence pipeline tests (offline).

Rodar:
    python backend/tests/test_infocap_official_policy_evidence_pipeline.py

Estes testes usam apenas fixtures sinteticas. Nao chamam InfoCap real, Vault,
MinIO real, Qdrant real, Supabase real, Docling real, URL real nem dados reais.
"""

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "app" / "services" / "policy_document_evidence_service.py"
    spec = importlib.util.spec_from_file_location("policy_document_evidence_service", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_module()
PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [ok] {name}")
    else:
        FAIL += 1
        FAILURES.append((name, detail))
        print(f"  [X] {name}{': ' + str(detail) if detail else ''}")


def _safe_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _pdf_bytes(text: bytes = b"Coberturas contratadas\nDanos eletricos limite R$ 10.000\nFranquia R$ 500\nAssistencia residencial com eletricista\nExclusoes: desgaste natural\nPremio total R$ 1.200\n") -> bytes:
    return b"%PDF-1.4\n" + text + b"\n%%EOF"


class FakeDocumentService:
    def __init__(self):
        self.records = []
        self.raw_pages = {}
        self.upload_count = 0

    def find_official_policy_document(self, company_id, policy_locator_hash, content_hash=None):
        for record in reversed(self.records):
            if record["company_id"] != company_id:
                continue
            if record["policy_locator_hash"] != policy_locator_hash:
                continue
            if content_hash and record["content_hash"] != content_hash:
                continue
            return record
        return None

    def store_official_policy_document(self, *, file_data, filename, company_id, file_size, content_type, policy_metadata, agent_id=None):
        self.upload_count += 1
        document_id = f"doc-{self.upload_count}"
        pages = [
            {"page_number": 1, "content": file_data.decode("latin-1", errors="ignore")},
        ]
        record = {
            "id": document_id,
            "company_id": company_id,
            "file_name": filename,
            "file_type": "pdf",
            "file_size": file_size,
            "status": "completed",
            "policy_locator_hash": policy_metadata["policy_locator_hash"],
            "content_hash": policy_metadata["content_hash"],
            "metadata": policy_metadata,
        }
        self.records.append(record)
        self.raw_pages[document_id] = pages
        return document_id, pages

    def load_raw_pages(self, document_id, company_id):
        return self.raw_pages.get(document_id, [])


class FakeIngestionService:
    def __init__(self):
        self.calls = []

    def process_document(self, document_id, company_id, strategy="page", agent_id=None):
        self.calls.append(
            {"document_id": document_id, "company_id": company_id, "strategy": strategy, "agent_id": agent_id}
        )
        return True


class FakeFetcher:
    def __init__(self, body):
        self.body = body
        self.calls = 0

    async def __call__(self, candidate):
        self.calls += 1
        return {
            "ok": True,
            "status": "retrieved",
            "body": self.body,
            "content_type": "application/pdf",
            "source_kind": "policy_pdf",
            "source_transport": "signed_url_fetch",
            "page_count": 1,
            "content_length_bucket": "under_1mb",
            "text_layer_status": "present",
        }


def run():
    print("== R1C.1 - Official policy evidence pipeline ==\n")

    states = getattr(mod, "POLICY_DOCUMENT_STATES", set())
    for state in {
        "source_available",
        "fetching",
        "fetched",
        "direct_extracting",
        "docling_pending",
        "parsed",
        "evidence_ready",
        "source_unavailable",
        "source_fetch_failed",
        "document_not_policy_evidence",
        "low_confidence",
        "conflict_requires_human",
    }:
        check(f"estado {state} existe", state in states, states)

    locator = {"provider": "infocap", "codfil": "1", "nosnum": "N-123"}
    locator_hash = mod.policy_locator_hash(locator)
    check("PolicyLocator hash nao vaza nosnum bruto", "N-123" not in locator_hash and "infocap:1:N-123" not in locator_hash, locator_hash)
    check("cache key contem content hash e locator hash", "abc123" in mod.policy_document_cache_key("company-1", locator, "abc123"), mod.policy_document_cache_key("company-1", locator, "abc123"))

    intent = mod.policy_document_evidence_requested("Ela tem eletricista, franquia e limite de cobertura?")
    no_intent = mod.policy_document_evidence_requested("Qual e a vigencia da apolice?")
    check("intencao documental reconhece cobertura/franquia/assistencia", intent is True)
    check("intencao documental nao baixa PDF para pergunta operacional simples", no_intent is False)

    pages = [
        {"page_number": 2, "content": "Coberturas contratadas: Danos eletricos - Limite R$ 10.000. Franquia R$ 500."},
        {"page_number": 3, "content": "Assistencia residencial: eletricista e chaveiro. Exclusoes: desgaste natural."},
    ]
    evidence = mod.extract_policy_document_evidence(
        pages,
        question="Ela cobre eletricista e danos eletricos?",
        document_id="doc-1",
        company_id="company-1",
        policy_locator=locator,
        content_hash="hash-1",
    )
    types_found = {item["evidence_type"] for item in evidence}
    check("extrai evidencia de cobertura com pagina", any(item["evidence_type"] == "coverage" and item["page_number"] == 2 for item in evidence), evidence)
    check("extrai evidencia de assistencia", "assistance" in types_found, evidence)
    check("extrai evidencia de franquia", "deductible" in types_found, evidence)
    check("extrai evidencia de exclusao", "exclusion" in types_found, evidence)
    check("trecho e curto", all(len(item["evidence_text"]) <= 700 for item in evidence), evidence)
    check("evidencia carrega hash e locator hash", all(item["content_hash"] == "hash-1" and item["policy_locator_hash"] == locator_hash for item in evidence), evidence)

    async def scenario_cache_miss_then_hit():
        docs = FakeDocumentService()
        ingestion = FakeIngestionService()
        fetcher = FakeFetcher(_pdf_bytes())
        service = mod.PolicyDocumentEvidenceService(document_service=docs, ingestion_service=ingestion)
        first = await service.ensure_official_policy_evidence(
            company_id="company-1",
            policy_locator=locator,
            official_document_candidate={"source_kind": "policy_pdf", "url": "https://signed.invalid/policy.pdf"},
            question="Quais coberturas e franquias existem?",
            fetcher=fetcher,
            agent_id=None,
        )
        second = await service.ensure_official_policy_evidence(
            company_id="company-1",
            policy_locator=locator,
            official_document_candidate={"source_kind": "policy_pdf", "url": "https://signed.invalid/policy.pdf"},
            question="Ela tem eletricista?",
            fetcher=fetcher,
            agent_id=None,
        )
        return first, second, fetcher, docs, ingestion

    first, second, fetcher, docs, ingestion = asyncio.run(scenario_cache_miss_then_hit())
    check("cache miss busca PDF uma vez", first["cache_status"] == "miss" and fetcher.calls == 1, first)
    check("cache hit nao faz novo fetch", second["cache_status"] == "hit" and fetcher.calls == 1, second)
    check("PDF armazenado via DocumentService fake", docs.upload_count == 1, docs.upload_count)
    check("ingestao page chamada uma vez", len(ingestion.calls) == 1 and ingestion.calls[0]["strategy"] == "page", ingestion.calls)
    check("resultado contem evidencia pronta", first["document_status"] == "evidence_ready" and first["evidence_items"], first)

    async def scenario_docling_fallback():
        calls = {"count": 0}

        def docling_parser(*, file_bytes, policy_metadata):
            calls["count"] += 1
            return [{"page_number": 4, "content": "Assistencia residencial: eletricista 24 horas."}]

        service = mod.PolicyDocumentEvidenceService(
            document_service=FakeDocumentService(),
            ingestion_service=FakeIngestionService(),
            docling_parser=docling_parser,
        )
        result = await service.ensure_official_policy_evidence(
            company_id="company-1",
            policy_locator=locator,
            official_document_candidate={"source_kind": "policy_pdf", "url": "https://signed.invalid/policy.pdf"},
            question="Ela tem eletricista?",
            fetcher=FakeFetcher(_pdf_bytes(b"texto administrativo sem dados uteis")),
        )
        return result, calls["count"]

    docling_result, docling_calls = asyncio.run(scenario_docling_fallback())
    check("extracao direta insuficiente aciona Docling existente", docling_calls == 1, docling_calls)
    check("Docling fallback gera evidencia com metodo docling", any(item["extraction_method"] == "docling" for item in docling_result["evidence_items"]), docling_result)

    async def scenario_no_url():
        service = mod.PolicyDocumentEvidenceService(document_service=FakeDocumentService(), ingestion_service=FakeIngestionService())
        return await service.ensure_official_policy_evidence(
            company_id="company-1",
            policy_locator=locator,
            official_document_candidate=None,
            question="Quais coberturas?",
            fetcher=FakeFetcher(_pdf_bytes()),
        )

    no_url = asyncio.run(scenario_no_url())
    check("ausencia de url retorna source_unavailable", no_url["document_status"] == "source_unavailable", no_url)
    check("ausencia de url nao tenta fetch", no_url["cache_status"] == "unavailable", no_url)

    async def scenario_hash_refresh():
        docs = FakeDocumentService()
        ingestion = FakeIngestionService()
        fetcher1 = FakeFetcher(_pdf_bytes(b"Cobertura A"))
        fetcher2 = FakeFetcher(_pdf_bytes(b"Cobertura B alterada"))
        service = mod.PolicyDocumentEvidenceService(document_service=docs, ingestion_service=ingestion)
        await service.ensure_official_policy_evidence(
            company_id="company-1",
            policy_locator=locator,
            official_document_candidate={"source_kind": "policy_pdf", "url": "https://signed.invalid/old.pdf"},
            question="Coberturas?",
            fetcher=fetcher1,
        )
        refreshed = await service.ensure_official_policy_evidence(
            company_id="company-1",
            policy_locator=locator,
            official_document_candidate={"source_kind": "policy_pdf", "url": "https://signed.invalid/new.pdf"},
            question="Atualize a evidencia da apolice",
            fetcher=fetcher2,
            force_refresh=True,
        )
        return refreshed, docs, ingestion

    refreshed, refresh_docs, refresh_ingestion = asyncio.run(scenario_hash_refresh())
    check("force refresh reprocessa hash diferente", refreshed["cache_status"] == "refreshed" and refresh_docs.upload_count == 2, refreshed)
    check("hash diferente gera nova ingestao", len(refresh_ingestion.calls) == 2, refresh_ingestion.calls)

    low = mod.extract_policy_document_evidence(
        [{"page_number": 1, "content": "texto administrativo sem garantias relevantes"}],
        question="Tem eletricista?",
        document_id="doc-low",
        company_id="company-1",
        policy_locator=locator,
        content_hash="hash-low",
    )
    check("documento sem evidencia nao inventa cobertura", low == [], low)

    safe_raw = _safe_json(first)
    for forbidden in (
        "https://",
        "signed.invalid",
        "token",
        "cookie",
        "Authorization",
        "N-123",
        "codfil",
        "nosnum",
        "%PDF",
    ):
        check(f"saida nao vaza {forbidden}", forbidden not in safe_raw, safe_raw)

    even = mod.policy_document_evidence_role_view(first, role="even", case_id=None)
    core = mod.policy_document_evidence_role_view(first, role="core")
    check("Core recebe evidencias", bool(core.get("evidence_items")), core)
    check("Even sem case_id nao recebe evidencia", even.get("evidence_items") == [], even)
    even_case = mod.policy_document_evidence_role_view(first, role="even", case_id="case-1")
    check("Even com case_id recebe DTO minimo", bool(even_case.get("evidence_items")) and "document_id" not in _safe_json(even_case), even_case)


if __name__ == "__main__":
    run()
    print(f"\n== Resumo: {PASS} passaram, {FAIL} falharam ==")
    if FAIL:
        for name, detail in FAILURES:
            print(f"  - {name}{': ' + str(detail) if detail else ''}")
        sys.exit(1)
    sys.exit(0)

# -*- coding: utf-8 -*-
"""SPEC-130-B · O FIO (§2) — do 1º byte ao último, com o MOTOR real.

    bytes do PDF (borda: o HTTP do CORP é dublado)
      → infocap_connector._maybe_attach_official_policy_document_evidence   (passa o prêmio líquido do CORP — F2)
      → PolicyDocumentEvidenceService.ensure_official_policy_evidence       (REAL)
      → DocumentService.store_official_policy_document → páginas TOLERANTES  (REAL; MinIO/banco dublados)
      → ler_documento_de_seguro: regex → juiz → modelo (DUBLÊ) → juiz       (REAL)
      → grava a ficha + o resumo                                            (REAL; MinIO/banco dublados)
      → infocap_policy_provider.apolice_documental_do_pack (+ leitura)      (F2)
      → reconciliar (+ sinal documento_nao_conferido)                        (REAL)

⚠️ Nasce VERMELHO pelo motivo certo enquanto a F2 não liga o conector: o prêmio que JULGA a leitura tem de ser o
do CORP (`premium_summary.net_premium`), não o impresso no PDF; e a `ApoliceDocumental` tem de carregar a leitura.
A costura (F5) o deixa verde.

⛔ PDF GERADO (💭 sintético). ⛔ Nenhuma chamada a modelo, InfoCap ou portal.

Rodar:  cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_spec130b_o_fio.py -q
"""
from __future__ import annotations

import asyncio
import io
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# 💭 layout "Tokio": LMI e prêmio sem R$, UM espaço — o regex de hoje lê ZERO linhas
TOKIO = [
    "APOLICE DE SEGURO CONDOMINIO",
    "Segurado: CONDOMINIO EXEMPLO CNPJ 12.345.678/0001-90",
    "Coberturas Limite Premio",
    "Incendio, Raio e Explosao 5.000.000,00 16.771,96",
    "Danos Eletricos 600.000,00 15.103,93",
    "Premio Liquido R$ 31.875,89",
]


def _pdf(linhas):
    import fitz

    doc = fitz.open()
    pagina = doc.new_page()
    for i, linha in enumerate(linhas):
        pagina.insert_text((50, 72 + 14 * i), linha, fontsize=9)
    dados = doc.tobytes()
    doc.close()
    return dados


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.filtros, self.op, self.dados, self.lim = banco, tabela, [], "select", None, None

    def select(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.op, self.dados = "insert", linha
        return self

    def update(self, dados):
        self.op, self.dados = "update", dados
        return self

    def eq(self, c, v):
        self.filtros.append(lambda r, c=c, v=v: str(r.get(c)) == str(v))
        return self

    def like(self, c, padrao):
        self.filtros.append(lambda r, c=c, p=padrao.rstrip("%"): str(r.get(c) or "").startswith(p))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self.lim = n
        return self

    def execute(self):
        linhas = self.banco.setdefault(self.tabela, [])
        if self.op == "insert":
            linhas.append(dict(self.dados))
            return SimpleNamespace(data=[dict(self.dados)])
        sel = [r for r in linhas if all(f(r) for f in self.filtros)]
        if self.op == "update":
            for r in sel:
                r.update(self.dados)
        return SimpleNamespace(data=[dict(r) for r in sel][: self.lim or None])


class _Minio:
    def __init__(self):
        self.objetos = {}
        self.client = SimpleNamespace(put_object=lambda b, n, d, length=None, content_type=None:
                                      self.objetos.__setitem__(n, d.read()))

    def upload_file(self, file_data, company_id, document_id, filename, content_type=None):
        nome = "%s/%s/%s" % (company_id, document_id, filename)
        self.objetos[nome] = file_data.read()
        return nome

    def download_file(self, nome):
        if nome not in self.objetos:
            raise FileNotFoundError(nome)
        return io.BytesIO(self.objetos[nome])


class _Modelo:
    """Dublê do degrau 2: lê só o texto recebido e devolve `<rótulo> <limite> <prêmio>` com o trecho literal."""

    def __init__(self):
        self.chamadas = 0

    async def __call__(self, texto, *, company_id):
        self.chamadas += 1
        linhas = []
        for bruta in texto.splitlines():
            m = re.match(r"^(.+?) ([\d.]+,\d{2}) ([\d.]+,\d{2})$", bruta.strip())
            if m:
                linhas.append({"pagina": 1, "rotulo": m.group(1), "limite": m.group(2), "premio": m.group(3),
                               "trecho": bruta.strip()})
        return json.dumps({"linhas": linhas})


def test_o_fio_da_ficha_unica(monkeypatch):
    from app.api import infocap_connector as C
    from app.providers.infocap_policy_provider import apolice_documental_do_pack, apolice_reconciliada_do_pack
    from app.services import document_service as D
    from app.services import policy_document_evidence_service as S

    monkeypatch.delenv("LEITOR_APOLICE_MODELO", raising=False)
    pdf = _pdf(TOKIO)

    async def _http_do_corp(**_k):          # a BORDA: o download do `url_apolice`
        return {"ok": True, "status": "retrieved", "body": pdf, "content_type": "application/pdf",
                "source_kind": "policy_pdf", "source_transport": "signed_url_fetch"}

    monkeypatch.setattr(C, "_fetch_official_document_candidate_for_policy_pipeline", _http_do_corp)

    ds = D.DocumentService.__new__(D.DocumentService)
    ds.minio, banco = _Minio(), {}
    ds.supabase = SimpleNamespace(table=lambda nome: _Consulta(banco, nome))
    modelo = _Modelo()

    async def _sem_redis():
        return None

    servico = S.PolicyDocumentEvidenceService(
        document_service=ds, ingestion_service=SimpleNamespace(process_document=lambda **_k: True),
        docling_parser=lambda **_k: [], leitor_modelo=modelo, redis_factory=_sem_redis)
    monkeypatch.setattr(S, "_policy_document_evidence_service", servico)

    pack = {
        "official_document_source_available": True,
        "policy_locator": {"provider": "infocap", "codfil": "1", "nosnum": "999001"},   # ⛔ sintético
        # 🔴 o prêmio líquido do CORP (`/documento.preliq`) — DIFERENTE do impresso por 1 centavo de
        #    arredondamento, dentro do juiz do documento: só fecha COM ele se o conector o passar.
        "premium_summary": {"net_premium": {"label": "Prêmio líquido", "value": "R$ 31.875,90",
                                            "provider_field": "preliq"}},
        "coverage_sections": [],
    }
    envelope = {"acompanhamento": [{"emissao": {"url_apolice": "https://exemplo.invalido/apolice.pdf"}}]}
    payload = SimpleNamespace(user_query="quais as coberturas da apolice", document_evidence_requested=True,
                              force_document_evidence_refresh=False)

    saida = asyncio.run(C._maybe_attach_official_policy_document_evidence(
        pack=pack, detail_envelope=envelope, payload=payload, company_id="corretora-A",
        token="", auth_cookies=None, connection_id="conexao-1"))

    evidencia = saida.get("official_policy_document_evidence") or {}
    leitura = evidencia.get("leitura") or {}
    # --- o motor (F1): a leitura existe, o modelo foi chamado, e ela FECHOU -----------------
    assert modelo.chamadas == 1, "o regex não lê o layout Tokio: o degrau do modelo tinha de rodar"
    assert leitura.get("estado") == "fechou", leitura
    assert evidencia.get("document_status") == "evidence_ready"
    assert [r for r in banco["documents"] if r["metadata"].get("leitura", {}).get("estado") == "fechou"]
    # --- 🔴 a COSTURA com a F2: o juiz usou o prêmio do CORP, não o impresso ----------------
    assert leitura.get("fonte_do_esperado") == "corp", (
        "F2 pendente: o conector ainda não passa `premio_liquido_esperado` (premium_summary.net_premium) "
        "ao leitor — fonte=%r esperado=%r" % (leitura.get("fonte_do_esperado"), leitura.get("premio_esperado")))
    assert leitura.get("premio_esperado") == "31875.90"
    # --- a ficha chega à porta e ao `reconciliar` --------------------------------------------
    documental = apolice_documental_do_pack(saida)
    assert documental is not None and len(documental.linhas) == 2
    assert (documental.leitura or {}).get("estado") == "fechou", (
        "F2 pendente: `apolice_documental_do_pack` ainda não carrega a `leitura` do pack")
    assert documental.tipo_documento == "apolice"
    apolice = apolice_reconciliada_do_pack(saida)
    assert not [s for s in apolice.sinais if s.codigo == "documento_nao_conferido"]
    assert len(apolice.coberturas) == 2

# -*- coding: utf-8 -*-
"""SPEC-130-B F1 · o motor — a cascata com juiz, a máscara, as páginas tolerantes e o 2º plano.

O MOTOR é o real (`ler_documento_de_seguro`, `extract_policy_document_evidence`, `extrair_paginas_tolerante`,
`DocumentService.store_official_policy_document/guardar_leitura/carregar_leitura`, `fecha_o_premio`, `reconciliar`).
Dublê SÓ na borda: o modelo, o MinIO, o banco e o Redis.

⛔ Nenhum PDF real de cliente: todo PDF aqui é GERADO (PyMuPDF) com texto 💭 sintético. ⛔ Nenhuma chamada a modelo.

Rodar:  cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m pytest tests/test_spec130b_o_motor.py -q
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
import sys
import threading
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.providers import policy_data_provider as P  # noqa: E402
from app.services import document_service as D  # noqa: E402
from app.services import policy_document_evidence_service as S  # noqa: E402

TABELAS_REAIS = RAIZ / "tests" / "fixtures" / "pdf_tabelas_reais_extra0011.json"

# 💭 o layout "Tokio" (LMI e prêmio sem R$, separados por UM espaço) — que o regex de hoje não lê
TOKIO = [
    "APOLICE DE SEGURO CONDOMINIO",
    "Segurado: CONDOMINIO EXEMPLO CNPJ 12.345.678/0001-90",
    "Contato (11) 98765-4321 sindico@exemplo.com.br",
    "Coberturas Limite Premio",
    "Incendio, Raio e Explosao 5.000.000,00 16.771,96",
    "Danos Eletricos 600.000,00 15.103,93",
    "Premio Liquido R$ 31.875,89",
]
LIQUIDO_TOKIO = "31.875,89"
LOCATOR = {"provider": "infocap", "codfil": "1", "nosnum": "999001"}   # ⛔ sintético


# ===========================================================================
# A BORDA — dublês
# ===========================================================================
def gerar_pdf(paginas):
    import fitz

    doc = fitz.open()
    for linhas in paginas:
        pagina = doc.new_page()
        y = 72
        for linha in linhas:
            pagina.insert_text((50, y), linha, fontsize=9)
            y += 14
    dados = doc.tobytes()
    doc.close()
    return dados


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.filtros, self.op, self.dados, self._limite, self._ordem = [], "select", None, None, None

    def select(self, *_a, **_k):
        self.op = "select"
        return self

    def insert(self, linha):
        self.op, self.dados = "insert", linha
        return self

    def update(self, dados):
        self.op, self.dados = "update", dados
        return self

    def eq(self, coluna, valor):
        self.filtros.append(lambda r, c=coluna, v=valor: str(r.get(c)) == str(v))
        return self

    def like(self, coluna, padrao):
        prefixo = padrao.rstrip("%")
        self.filtros.append(lambda r, c=coluna: str(r.get(c) or "").startswith(prefixo))
        return self

    def order(self, coluna, desc=False):
        self._ordem = (coluna, desc)
        return self

    def limit(self, n):
        self._limite = n
        return self

    def execute(self):
        linhas = self.banco.setdefault(self.tabela, [])
        if self.op == "insert":
            linhas.append(dict(self.dados, created_at="%06d" % len(linhas)))
            return SimpleNamespace(data=[dict(self.dados)])
        sel = [r for r in linhas if all(f(r) for f in self.filtros)]
        if self.op == "update":
            for r in sel:
                r.update(self.dados)
            return SimpleNamespace(data=[dict(r) for r in sel])
        if self._ordem:
            sel = sorted(sel, key=lambda r: str(r.get(self._ordem[0]) or ""), reverse=self._ordem[1])
        if self._limite:
            sel = sel[: self._limite]
        return SimpleNamespace(data=[dict(r) for r in sel])


class BancoDublado:
    def __init__(self):
        self.tabelas = {}

    def table(self, nome):
        return _Consulta(self.tabelas, nome)


class MinioDublado:
    def __init__(self):
        self.objetos = {}
        self.client = SimpleNamespace(put_object=self._put)

    def _put(self, bucket, nome, dados, length=None, content_type=None):
        self.objetos[nome] = dados.read()

    def upload_file(self, file_data, company_id, document_id, filename, content_type="application/pdf"):
        nome = "%s/%s/%s" % (company_id, document_id, filename)
        self.objetos[nome] = file_data.read()
        return nome

    def download_file(self, nome):
        if nome not in self.objetos:
            raise FileNotFoundError(nome)
        return io.BytesIO(self.objetos[nome])


def servico_de_documentos():
    """O DocumentService REAL, com MinIO e banco dublados (a borda)."""
    ds = D.DocumentService.__new__(D.DocumentService)
    ds.minio = MinioDublado()
    ds.supabase = BancoDublado()
    return ds


class IngestaoDublada:
    def process_document(self, **_k):
        return True


class RedisDublado:
    def __init__(self):
        self.d = {}

    async def set(self, chave, valor, nx=False, ex=None):
        if nx and chave in self.d:
            return None
        self.d[chave] = valor
        return True

    async def get(self, chave):
        return self.d.get(chave)

    async def delete(self, chave):
        self.d.pop(chave, None)


class ModeloDublado:
    """Lê SÓ o que recebe (o texto marcado e mascarado) e devolve as linhas `<rótulo> <limite> <prêmio>`."""

    _LINHA = re.compile(r"^(?P<rotulo>.+?) (?P<limite>[\d.]+,\d{2}) (?P<premio>[\d.]+,\d{2})$")

    def __init__(self, atraso=0.0, alterar_trecho=False, premio_errado=False):
        self.recebido, self.atraso = [], atraso
        self.alterar_trecho, self.premio_errado = alterar_trecho, premio_errado

    async def __call__(self, texto, *, company_id):
        self.recebido.append(texto)
        if self.atraso:
            await asyncio.sleep(self.atraso)
        linhas, pagina = [], 1
        for bruta in texto.splitlines():
            marcador = re.match(r"^\[pagina (\d+)\]$", bruta.strip())
            if marcador:
                pagina = int(marcador.group(1))
                continue
            achado = self._LINHA.match(bruta.strip())
            if not achado:
                continue
            premio = "1,00" if self.premio_errado else achado.group("premio")
            trecho = bruta.strip() + (" (corrigido)" if self.alterar_trecho else "")
            linhas.append({"pagina": pagina, "rotulo": achado.group("rotulo"), "limite": achado.group("limite"),
                           "premio": premio, "franquia": None,
                           "trecho": trecho if not self.premio_errado else trecho.replace(achado.group("premio"), "1,00")})
        return json.dumps({"linhas": linhas, "premio_liquido_impresso": LIQUIDO_TOKIO})


def paginas_de(linhas, numero=1):
    return [{"page_number": numero, "content": "\n".join(linhas), "text": "\n".join(linhas)}]


def ler(pages, **kw):
    kw.setdefault("company_id", "corretora-A")
    kw.setdefault("policy_locator", LOCATOR)
    return asyncio.run(S.ler_documento_de_seguro(pages, **kw))


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch):
    monkeypatch.delenv("LEITOR_APOLICE_MODELO", raising=False)
    monkeypatch.delenv("LEITOR_APOLICE_ORCAMENTO_S", raising=False)
    S._TAREFAS_EM_SEGUNDO_PLANO.clear()
    yield


# ===========================================================================
# A CASCATA
# ===========================================================================
def test_regex_fecha_custo_zero_sem_modelo():
    """A linha de controle: as apólices que o regex de hoje fecha (HDI, Allianz) NÃO chamam o modelo."""
    fixture = json.load(io.open(TABELAS_REAIS, encoding="utf-8"))
    for apelido in ("hdi_residencial", "allianz_condominio"):
        modelo = ModeloDublado()
        r = ler(paginas_de(fixture[apelido]["linhas"]), leitor_modelo=modelo)
        assert r["leitura"]["estado"] == "fechou", (apelido, r["leitura"])
        assert modelo.recebido == [], apelido
        assert r["leitura"]["custo_usd"] == 0.0
        assert [d["degrau"] for d in r["leitura"]["degraus"]] == ["regex"]


def test_layout_tokio_regex_zero_modelo_fecha():
    # controle: o regex de hoje lê ZERO linhas deste layout
    so_regex = ler(paginas_de(TOKIO), permitir_modelo=False)
    assert so_regex["leitura"]["degraus"][0]["linhas"] == 0
    assert so_regex["leitura"]["estado"] == "nao_fechou"
    assert so_regex["leitura"]["premio_esperado"] == "31875.89"
    assert so_regex["leitura"]["fonte_do_esperado"] == "impresso"

    modelo = ModeloDublado()
    r = ler(paginas_de(TOKIO), leitor_modelo=modelo)
    assert len(modelo.recebido) == 1
    assert r["leitura"]["estado"] == "fechou", r["leitura"]
    linhas = [i for i in r["evidence_items"] if (i.get("structured") or {}).get("kind") == "coverage_row"]
    assert len(linhas) == 2
    assert {i["extraction_method"] for i in linhas} == {"modelo"}
    assert {i["structured"]["layout"] for i in linhas} == {"modelo"}
    assert any(i["structured"]["premium"] == "R$ 15.103,93" for i in linhas)
    assert r["leitura"]["soma_linhas"] == "31875.89"
    # a MESMA conta que o adaptador faz
    from app.providers.infocap_policy_provider import apolice_documental_do_pack

    doc = apolice_documental_do_pack({"official_policy_document_evidence": {"evidence_items": r["evidence_items"]}})
    assert sum(l.premio for l in doc.linhas) == Decimal("31875.89")


def test_premio_esperado_do_corp_vence_o_impresso():
    r = ler(paginas_de(TOKIO), premio_esperado="R$ 40.000,00", leitor_modelo=ModeloDublado())
    assert r["leitura"]["fonte_do_esperado"] == "corp"
    assert r["leitura"]["premio_esperado"] == "40000.00"
    assert r["leitura"]["estado"] == "nao_fechou"


def test_linha_do_modelo_sem_trecho_literal_e_descartada():
    modelo = ModeloDublado(alterar_trecho=True)
    r = ler(paginas_de(TOKIO), leitor_modelo=modelo)
    degrau = [d for d in r["leitura"]["degraus"] if d["degrau"] == "modelo"][0]
    assert degrau["descartadas"] == 2
    assert r["leitura"]["estado"] == "nao_fechou"
    assert not [i for i in r["evidence_items"] if i.get("extraction_method") == "modelo"]


def test_juiz_recusa_soma_errada():
    # o juiz do documento: max(R$ 0,05; 0,5 %)
    assert P.fecha_o_premio(Decimal("100.00"), Decimal("110.00"))[0] is False
    assert P.fecha_o_premio(Decimal("100.00"), Decimal("100.40"))[0] is True       # 0,5 % de 100,40 = 0,50
    assert P.fecha_o_premio(Decimal("100.00"), Decimal("100.60"))[0] is False      # controle
    assert P.fecha_o_premio(Decimal("10.00"), Decimal("10.05"))[0] is True          # o piso de R$ 0,05
    assert P.fecha_o_premio(Decimal("10.00"), Decimal("10.06"))[0] is False
    # o do cadastro continua em R$ 0,05 absolutos
    assert P.fecha_o_premio(Decimal("100.00"), Decimal("100.40"), tolerancia=P.TOLERANCIA_DE_PREMIO)[0] is False
    assert P.fecha_o_premio(Decimal("5"), None) == (False, Decimal("0.00"), Decimal("0.00"))
    # e a cascata: o modelo que lê o prêmio ERRADO não fecha
    r = ler(paginas_de(TOKIO), leitor_modelo=ModeloDublado(premio_errado=True))
    assert r["leitura"]["estado"] == "nao_fechou", r["leitura"]


def test_sem_premio_para_conferir_nao_chama_modelo():
    linhas = [l for l in TOKIO if not l.startswith("Premio Liquido")]
    modelo = ModeloDublado()
    r = ler(paginas_de(linhas), leitor_modelo=modelo)
    assert r["leitura"]["estado"] == "sem_premio_para_conferir"
    assert modelo.recebido == []


def test_modelo_desligado_por_env(monkeypatch):
    monkeypatch.setenv("LEITOR_APOLICE_MODELO", "0")
    modelo = ModeloDublado()
    r = ler(paginas_de(TOKIO), leitor_modelo=modelo)
    assert modelo.recebido == []
    assert r["leitura"]["estado"] == "nao_fechou"


def test_tipo_de_documento_e_objeto_do_risco_locais():
    assert S.tipo_de_documento(paginas_de(TOKIO)) == "apolice"
    assert S.tipo_de_documento(paginas_de(["PROPOSTA DE SEGURO AUTO", "Premio 10,00"])) == "proposta"
    assert S.tipo_de_documento(paginas_de(["ENDOSSO Nº 12 da apolice", "x"])) == "endosso"
    assert S.tipo_de_documento(paginas_de(["COTACAO DE SEGURO", "x"])) == "cotacao"
    assert S.tipo_de_documento(paginas_de(["CERTIFICADO DE REGISTRO E LICENCIAMENTO DE VEICULO"])) == "crlv"
    assert S.tipo_de_documento(paginas_de(["texto qualquer"])) == "desconhecido"
    objeto = S.objeto_do_risco_local(paginas_de([
        "Placa: ABC1D23 Chassi: 9BWZZZ377VT004251", "Ano/Modelo: 2020/2021", "CEP: 01310-100",
        "Importancia Segurada R$ 450.000,00"]))
    assert objeto["placa"] == "ABC1D23" and objeto["chassi"] == "9BWZZZ377VT004251"
    assert objeto["ano_modelo"] == "2020/2021" and objeto["cep"] == "01310-100"
    assert objeto["importancia_segurada"] == "450.000,00"


# ===========================================================================
# A MÁSCARA — com linha de controle
# ===========================================================================
def test_mascara_nunca_toca_dinheiro_e_apaga_pii():
    dinheiro = ["600.000,00", "15.103,93", "R$ 1500000,00", "45,64", "1.234.567,89", "LMI 1000,00"]
    pii = ["123.456.789-09", "12.345.678/0001-90", "(11) 98765-4321", "11 3333-4444", "a.b@x.com.br",
           "01310-100", "12.345-678", "12345678909", "9BWZZZ377VT004251"]
    texto = " | ".join(dinheiro + pii + ["Placa: ABC 2019", "Vig 2025-2026"])
    mascarado = S.mascarar_texto_de_apolice(texto)
    for valor in dinheiro:
        assert valor in mascarado, valor          # o dinheiro sobrevive
    for valor in pii:
        assert valor not in mascarado, valor      # o dado pessoal não
    assert "ABC 2019" not in mascarado and "2025-2026" in mascarado
    # 🔴 a linha de CONTROLE: o mascarador do canal apagaria o dinheiro — é por isso que existe este
    from app.services.canal.conversa import mascarar_para_o_modelo

    assert "600.000,00" not in mascarar_para_o_modelo("Danos Eletricos 600.000,00 15.103,93")


def test_o_texto_que_chega_ao_modelo_esta_mascarado():
    """Guarda da mutação (3): o texto vai ao modelo SEM máscara → vermelho."""
    modelo = ModeloDublado()
    ler(paginas_de(TOKIO), leitor_modelo=modelo)
    assert len(modelo.recebido) == 1
    recebido = modelo.recebido[0]
    assert "12.345.678/0001-90" not in recebido and "98765-4321" not in recebido
    assert "sindico@exemplo.com.br" not in recebido
    assert "[CNPJ]" in recebido and "[TELEFONE]" in recebido and "[EMAIL]" in recebido
    assert "600.000,00 15.103,93" in recebido       # o que o modelo PRECISA ler continua lá
    assert recebido.startswith("[pagina 1]")


# ===========================================================================
# AS PÁGINAS TOLERANTES
# ===========================================================================
def test_paginas_tolerantes_reserva_por_pagina(monkeypatch):
    import PyPDF2

    pdf = gerar_pdf([["PAGINA-UM Incendio 100,00"], ["PAGINA-DOIS Vendaval 50,00"], []])
    original = PyPDF2.PageObject.extract_text

    def _falha_na_dois(self, *a, **k):
        texto = original(self, *a, **k)
        if "PAGINA-DOIS" in (texto or ""):
            raise ValueError("pagina com fonte quebrada")
        return texto

    monkeypatch.setattr(PyPDF2.PageObject, "extract_text", _falha_na_dois)
    pages, parser, total = D.extrair_paginas_tolerante(pdf)
    assert total == 3
    assert parser == {"1": "pypdf2", "2": "pymupdf", "3": "sem_texto"}
    assert [p["page_number"] for p in pages] == [1, 2]
    assert "PAGINA-DOIS" in pages[1]["content"]


def test_o_caminho_do_regex_usa_o_pypdf2_onde_ele_funciona():
    """Guarda da mutação (1): PyMuPDF no lugar do PyPDF2 → vermelho. 📊 BLOCO 0: trocar o extrator
    derruba a apólice de controle de 18 para 0 linhas — o dialeto do regex é o do PyPDF2."""
    import PyPDF2

    fixture = json.load(io.open(TABELAS_REAIS, encoding="utf-8"))["allianz_condominio"]["linhas"]
    meio = len(fixture) // 2
    pdf = gerar_pdf([fixture[:meio], fixture[meio:]])
    pages, parser, total = D.extrair_paginas_tolerante(pdf)
    assert set(parser.values()) == {"pypdf2"}, parser
    leitor = PyPDF2.PdfReader(io.BytesIO(pdf))
    for page in pages:
        assert page["content"] == (leitor.pages[page["page_number"] - 1].extract_text() or "").strip()
    # e o caminho de sempre devolve as mesmas páginas
    texto, pages2 = D.DocumentService._extract_pdf_text(None, io.BytesIO(pdf))
    assert pages2 == pages and texto


# ===========================================================================
# O REGISTRO, O 2º PLANO E A TRAVA
# ===========================================================================
def _servico(modelo=None, redis=None, ds=None):
    async def _fabrica():
        return redis

    return S.PolicyDocumentEvidenceService(
        document_service=ds or servico_de_documentos(), ingestion_service=IngestaoDublada(),
        docling_parser=lambda **_k: [], leitor_modelo=modelo, redis_factory=_fabrica)


def _pedir(servico, company_id, pdf, conexao="conexao-1", **kw):
    async def _fetcher(_c):
        return {"ok": True, "status": "retrieved", "body": pdf, "content_type": "application/pdf",
                "source_kind": "policy_pdf", "source_transport": "signed_url_fetch"}

    return servico.ensure_official_policy_evidence(
        company_id=company_id, policy_locator=LOCATOR,
        official_document_candidate={"url": "https://exemplo.invalido/a.pdf", "source_kind": "policy_pdf"},
        question="quais as coberturas da apolice", fetcher=_fetcher, connection_id=conexao, **kw)


def test_orcamento_estourado_segue_em_segundo_plano_e_a_proxima_vem_do_guardado(monkeypatch):
    monkeypatch.setenv("LEITOR_APOLICE_ORCAMENTO_S", "0.05")
    pdf = gerar_pdf([TOKIO])
    modelo = ModeloDublado(atraso=0.4)
    ds = servico_de_documentos()
    servico = _servico(modelo=modelo, redis=RedisDublado(), ds=ds)

    async def _roteiro():
        agora = await _pedir(servico, "corretora-A", pdf)
        assert agora["leitura"]["estado"] == "pendente", agora["leitura"]
        assert agora["cache_status"] == "miss"
        assert len(servico.tarefas_em_segundo_plano) == 1
        await asyncio.gather(*list(servico.tarefas_em_segundo_plano))
        depois = await _pedir(servico, "corretora-A", pdf)
        return agora, depois

    agora, depois = asyncio.run(_roteiro())
    assert len(modelo.recebido) == 1, "a 2ª leitura veio do guardado, sem modelo"
    assert depois["cache_status"] == "hit"
    assert depois["leitura"]["estado"] == "fechou"
    assert any(i.get("extraction_method") == "modelo" for i in depois["evidence_items"])
    # o registro: ficha no MinIO, resumo SEM objeto do risco no metadata
    linha = ds.supabase.tabelas["documents"][0]
    assert linha["metadata"]["leitura"]["estado"] == "fechou"
    assert "objeto_do_risco" not in json.dumps(linha["metadata"])
    assert linha["metadata"]["parser_por_pagina"] == {"1": "pypdf2"}
    assert linha["source_kind"] == "policy_pdf"
    fichas = [k for k in ds.minio.objetos if k.endswith(".leitura.json")]
    assert fichas and fichas[0].startswith("corretora-A/raw/")


def test_duas_chamadas_simultaneas_uma_leitura_pela_trava(monkeypatch):
    pdf = gerar_pdf([TOKIO])
    ds = servico_de_documentos()
    # 1º: guarda o documento com o modelo DESLIGADO (a leitura fica no regex)
    monkeypatch.setenv("LEITOR_APOLICE_MODELO", "0")
    asyncio.run(_pedir(_servico(ds=ds), "corretora-A", pdf))
    monkeypatch.setenv("LEITOR_APOLICE_MODELO", "1")
    modelo = ModeloDublado(atraso=0.2)
    servico = _servico(modelo=modelo, redis=RedisDublado(), ds=ds)

    async def _juntas():
        return await asyncio.gather(_pedir(servico, "corretora-A", pdf), _pedir(servico, "corretora-A", pdf))

    a, b = asyncio.run(_juntas())
    assert len(modelo.recebido) == 1, "a trava deixou passar duas leituras"
    assert sorted([a["leitura"]["estado"], b["leitura"]["estado"]]) == ["fechou", "pendente"]


def test_sem_redis_nao_ha_segundo_plano(monkeypatch):
    monkeypatch.setenv("LEITOR_APOLICE_ORCAMENTO_S", "0.05")
    modelo = ModeloDublado(atraso=0.3)
    servico = _servico(modelo=modelo, redis=None)
    r = asyncio.run(_pedir(servico, "corretora-A", gerar_pdf([TOKIO])))
    assert r["leitura"]["estado"] == "pendente"
    assert r["leitura"]["motivo"] == "orcamento_estourado_sem_segundo_plano"
    assert not servico.tarefas_em_segundo_plano


def test_isolamento_a_leitura_da_corretora_A_nao_serve_a_B():
    pdf = gerar_pdf([TOKIO])
    ds = servico_de_documentos()
    modelo = ModeloDublado()
    servico = _servico(modelo=modelo, redis=RedisDublado(), ds=ds)
    a = asyncio.run(_pedir(servico, "corretora-A", pdf))
    b = asyncio.run(_pedir(servico, "corretora-B", pdf))
    assert a["cache_status"] == "miss" and b["cache_status"] == "miss"
    assert len(modelo.recebido) == 2, "B leu o próprio documento — não recebeu a leitura de A"
    doc_a = [r for r in ds.supabase.tabelas["documents"] if r["company_id"] == "corretora-A"][0]
    assert ds.carregar_leitura(doc_a["id"], "corretora-A") is not None
    assert ds.carregar_leitura(doc_a["id"], "corretora-B") is None
    # a ficha de A copiada para o caminho de B é RECUSADA (ela diz de quem é)
    ds.minio.objetos["corretora-B/raw/%s.leitura.json" % doc_a["id"]] = \
        ds.minio.objetos["corretora-A/raw/%s.leitura.json" % doc_a["id"]]
    assert ds.carregar_leitura(doc_a["id"], "corretora-B") is None
    # a trava também é por corretora
    assert S._chave_da_trava("corretora-A", "c", "h" * 64) != S._chave_da_trava("corretora-B", "c", "h" * 64)


def test_o_docling_roda_fora_do_laco():
    threads = []

    def _docling(**_k):
        threads.append(threading.get_ident())
        return []

    servico = S.PolicyDocumentEvidenceService(
        document_service=servico_de_documentos(), ingestion_service=IngestaoDublada(), docling_parser=_docling,
        redis_factory=None)
    servico.redis_factory = lambda: asyncio.sleep(0, result=None)
    asyncio.run(_pedir(servico, "corretora-A", gerar_pdf([["texto sem nada de seguro"]])))
    assert threads and threads[0] != threading.get_ident()


# ===========================================================================
# O TETO POR TIPO, O SINAL E A FICHA PARA O MODELO
# ===========================================================================
def test_estruturados_de_todas_as_paginas_nao_sao_cortados_pelos_fragmentos():
    paginas = []
    for n in range(1, 26):   # 💭 25 páginas × 10 coberturas = 250 estruturados, + cláusulas
        linhas = ["Cobertura %d-%d R$ 1.000,00 R$ 10,00" % (n, i) for i in range(10)]
        linhas += ["Clausula %d-%d: condicoes particulares da cobertura" % (n, i) for i in range(6)]
        paginas.append({"page_number": n, "content": "\n".join(linhas)})
    itens = S.extract_policy_document_evidence(
        paginas, question="", document_id="d", company_id="c", policy_locator=LOCATOR, content_hash="h")
    linhas = [i for i in itens if (i.get("structured") or {}).get("kind") == "coverage_row"]
    assert len(linhas) == 250
    assert len(itens) - 250 == S.TETO_FRAGMENTOS
    assert len(itens) <= S.MAX_EVIDENCE_ITEMS


def test_reconciliar_avisa_documento_nao_conferido():
    from app.providers.infocap_policy_provider import apolice_do_pack

    cadastro = apolice_do_pack({"coverage_sections": []})
    linha = P.LinhaDeCoberturaDoDocumento(rotulo="Incendio", premio=Decimal("10.00"))
    nao = P.ApoliceDocumental(linhas=(linha,), leitura={"estado": "nao_fechou", "linhas": 1,
                                                        "soma_linhas": "10.00", "premio_esperado": "50.00"})
    r1 = P.reconciliar(cadastro, nao)
    sinais = [s for s in r1.sinais if s.codigo == "documento_nao_conferido"]
    assert len(sinais) == 1 and sinais[0].detalhe["estado"] == "nao_fechou"
    assert "não fecha" in P.frase_do_sinal(sinais[0])
    r2 = P.reconciliar(r1, nao)   # idempotente
    assert len([s for s in r2.sinais if s.codigo == "documento_nao_conferido"]) == 1
    sim = P.ApoliceDocumental(linhas=(linha,), leitura={"estado": "fechou"})
    assert not [s for s in P.reconciliar(cadastro, sim).sinais if s.codigo == "documento_nao_conferido"]
    sem = P.ApoliceDocumental(linhas=(linha,))   # sem leitura: comportamento de antes
    assert not [s for s in P.reconciliar(cadastro, sem).sinais if s.codigo == "documento_nao_conferido"]


def test_ficha_para_o_modelo_e_o_anexo_em_memoria():
    pdf = gerar_pdf([TOKIO + ["Placa: ABC1D23"]])
    modelo = ModeloDublado()
    r = asyncio.run(S.ler_anexo_de_seguro(pdf, "apolice.pdf", company_id="corretora-A", leitor_modelo=modelo))
    assert r["leitura"]["estado"] == "fechou"
    assert "12.345.678/0001-90" not in r["texto_mascarado"] and "15.103,93" in r["texto_mascarado"]
    segurado = S.ficha_para_o_modelo(r, audiencia="segurado")
    corretor = S.ficha_para_o_modelo(r, audiencia="corretor")
    assert "Conferida" in segurado and "15.103,93" in segurado
    assert "ABC1D23" not in corretor and "[PLACA]" in corretor
    assert "Objeto do risco" not in segurado
    nao = asyncio.run(S.ler_anexo_de_seguro(b"oi", "foto.jpg", company_id="corretora-A"))
    assert nao["leitura"]["estado"] == "falhou"

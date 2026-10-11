# -*- coding: utf-8 -*-
"""SPEC-130-B · F3 — OS ANEXOS: o PDF do segurado (WhatsApp) e o do corretor (chat) passam pelo LEITOR do produto.

    WhatsApp:  _handle_evolution_like_inbound (o ramo `media.kind == "document"`, bytes do evento em base64)
               → vision_service.conteudo_do_anexo → policy_document_evidence_service.ler_anexo_de_seguro
               → ficha_para_o_modelo(audiencia="segurado")  (MASCARADA)  → o texto do turno → _buffer_or_dispatch_text
    Chat:      POST /chat/stream {fileUrl} → anexar_documento_do_corretor → baixar_documento (dublê de borda)
               → conteudo_do_anexo → ficha (audiencia="corretor") + o texto MASCARADO → user_message do grafo

Dublê SÓ na borda: o storage (upload), o buffer, o download da URL, o docling (microserviço) e — nos casos
"dublados" — o MOTOR do leitor da F1 no nível da função dela. Nos casos "leitor REAL" o leitor da F1 roda de
verdade sobre um PDF gerado aqui com PyMuPDF (o modelo é um dublê que só devolve vazio). A rede fica FECHADA.

⛔ Dados fictícios: DDD 00, CPF sintético com DV válido, e-mail em `exemplo.test`. Nenhum PDF real no repositório.
Rodar: cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec130b_anexos.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import base64
import re
import socket
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import app.api.webhook as W  # noqa: E402
import app.services.policy_document_evidence_service as P  # noqa: E402
import app.services.vision_service as VS  # noqa: E402

EMPRESA_A = "aaaaaaaa-0000-4000-8000-0000000130b1"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-0000000130b2"


def _cpf_sintetico(base9: str) -> str:
    d = [int(c) for c in base9]
    for _ in range(2):
        s = sum(v * p for v, p in zip(d, range(len(d) + 1, 1, -1)))
        d.append(0 if s % 11 < 2 else 11 - s % 11)
    t = "".join(map(str, d))
    return f"{t[:3]}.{t[3:6]}.{t[6:9]}-{t[9:]}"


CPF = _cpf_sintetico("123456789")
CPF_DIGITOS = re.sub(r"\D", "", CPF)
TELEFONE = "(00) 99999-0001"
EMAIL = "pessoa.ficticia@exemplo.test"
COBERTURAS = [("Incendio, raio e explosao", "600.000,00", "1.234,56"),
              ("Danos eletricos", "20.000,00", "345,67"),
              ("Roubo e furto qualificado", "15.000,00", "210,00")]
#: o que NUNCA pode aparecer no texto do turno
PII = (CPF, CPF_DIGITOS, TELEFONE, "99999-0001", EMAIL)


def _sem_pii(texto: str) -> list:
    return [p for p in PII if p in texto]


def _pdf_minimo(linhas) -> bytes:
    """Um PDF de UMA página, Helvetica, uma linha de texto por `Td` — escrito à mão.

    ⚠️ Não é o PyMuPDF: 📊 11/10/2026, nesta máquina, `fitz.open().new_page()` levou 18,9 s sozinho e > 40 s depois
    dos imports do app (o `faulthandler` parou o teste dentro de `pymupdf/extra.py:_newPage`). O PDF à mão sai em
    microssegundos e é lido pelo MESMO extrator do produto (PyPDF2/PyMuPDF por página) — a controle abaixo prova.
    """
    def _esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    corpo = ["BT", "/F1 10 Tf", "14 TL", "60 780 Td"]
    for linha in linhas:
        corpo.append(f"({_esc(linha)}) Tj T*")
    corpo.append("ET")
    stream = "\n".join(corpo).encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    saida = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(saida))
        saida += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(saida)
    saida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        saida += b"%010d 00000 n \n" % off
    saida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(saida)


def _pdf(titulo: str = "APOLICE DE SEGURO RESIDENCIAL", *, com_coberturas: bool = True) -> bytes:
    linhas = [titulo, "Seguradora Ficticia S.A.", f"Segurado: Pessoa Ficticia   CPF: {CPF}",
              f"Telefone: {TELEFONE}   E-mail: {EMAIL}", ""]
    if com_coberturas:
        linhas += ["Coberturas  Limite Maximo de Indenizacao  Premio"]
        linhas += [f"{n}  R$ {lmi}  R$ {pr}" for n, lmi, pr in COBERTURAS]
        linhas += ["", "Premio liquido total  R$ 1.790,23"]
    else:
        linhas += ["Ata da reuniao do condominio", "Pauta: pintura da fachada e troca do portao"]
    return _pdf_minimo(linhas)


# =====================================================================================================================
# as bordas
# =====================================================================================================================
_CONNECT_REAL = socket.socket.connect
_CONNECT_EX_REAL = socket.socket.connect_ex


def _loopback(destino) -> bool:
    host = destino[0] if isinstance(destino, tuple) and destino else ""
    return str(host) in ("127.0.0.1", "::1", "localhost")


def _sem_rede(self, destino, *a, **k):
    """O laço de eventos do Windows abre um par de sockets no LOOPBACK (o self-pipe); fora dele, é rede."""
    if _loopback(destino):
        return _CONNECT_REAL(self, destino, *a, **k)
    raise AssertionError("a rede é fechada neste teste")


def _sem_rede_ex(self, destino, *a, **k):
    if _loopback(destino):
        return _CONNECT_EX_REAL(self, destino, *a, **k)
    raise AssertionError("a rede é fechada neste teste")


class _SanitizacaoForaDoAr:
    """O docling é um microserviço (e o construtor fala com o MinIO): aqui ele está fora do ar → o fallback local."""

    def _docling_parse(self, *_a, **_k):
        raise RuntimeError("docling fora do ar (teste)")


def _mascara_dubla(texto: str) -> str:
    t = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[CPF]", str(texto or ""))
    t = re.sub(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b", "[TELEFONE]", t)
    return re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[EMAIL]", t)


F1_PRONTA = all(callable(getattr(P, n, None)) for n in
                ("ler_anexo_de_seguro", "ficha_para_o_modelo", "mascarar_texto_de_apolice"))


@pytest.fixture(autouse=True)
def _bordas(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _sem_rede)
    monkeypatch.setattr(socket.socket, "connect_ex", _sem_rede_ex)
    from app.services import sanitization_service as S

    monkeypatch.setattr(S, "SanitizationService", _SanitizacaoForaDoAr)
    if not callable(getattr(P, "mascarar_texto_de_apolice", None)):
        monkeypatch.setattr(P, "mascarar_texto_de_apolice", _mascara_dubla, raising=False)
    monkeypatch.delenv("ANEXO_LEITURA_ORCAMENTO_S", raising=False)


class LeitorDublado:
    """O MOTOR da F1 dublado no nível da função dela (`ler_anexo_de_seguro` / `ficha_para_o_modelo`)."""

    def __init__(self, tipo="apolice", *, falha=None, ficha_corretor_com_texto=False, texto_mascarado=""):
        self.tipo, self.falha, self.com_texto = tipo, falha, ficha_corretor_com_texto
        self.texto_mascarado = texto_mascarado
        self.chamadas, self.fichas = [], []

    async def ler(self, file_bytes, file_name, *, company_id, orcamento_s=40.0, leitor_modelo=None):
        self.chamadas.append({"bytes": len(file_bytes), "company_id": company_id, "orcamento_s": orcamento_s})
        if self.falha == "excecao":
            raise RuntimeError("o leitor quebrou")
        if self.falha == "none":
            return None
        return {"evidence_items": [{"kind": "coverage_row", "page_number": 1, "evidence_text": f"{n} R$ {lmi}"}
                                   for n, lmi, _ in COBERTURAS],
                "leitura": {"tipo_documento": self.tipo, "estado": "fechou", "linhas": 3},
                "objeto_do_risco": {}, "texto_mascarado": self.texto_mascarado}

    def ficha(self, resultado, *, audiencia):
        self.fichas.append(audiencia)
        if self.falha == "ficha_vazia":
            return ""
        linhas = [f"Apólice · {len(resultado['evidence_items'])} coberturas · conferida"]
        linhas += ["- " + it["evidence_text"] for it in resultado["evidence_items"]]
        if audiencia == "corretor" and self.com_texto:
            linhas += ["[TEXTO DO DOCUMENTO (mascarado)]", "texto que a F1 já trouxe"]
        return "\n".join(linhas)

    def instalar(self, monkeypatch):
        monkeypatch.setattr(P, "ler_anexo_de_seguro", self.ler, raising=False)
        monkeypatch.setattr(P, "ficha_para_o_modelo", self.ficha, raising=False)
        return self


# =====================================================================================================================
# o ramo do WhatsApp, chamado pela função de produção (sem subir o servidor)
# =====================================================================================================================
def _webhook(monkeypatch, pdf: bytes, *, nome="apolice.pdf", legenda=None, company=EMPRESA_A):
    capturado, uploads = {}, []

    async def _nao_dup(*_a, **_k):
        return False

    async def _up(company_id, blob, mime, ext, bucket="chat-media"):
        uploads.append({"company_id": company_id, "bucket": bucket, "ext": ext, "bytes": len(blob)})
        return "https://storage.invalid/storage/v1/object/sign/chat-docs/x.pdf?token=t"

    async def _dl(*_a, **_k):
        raise AssertionError("os bytes vieram no evento — não se baixa de novo")

    async def _buf(payload, phone):
        capturado["payload"] = payload
        return {"status": "buffered"}

    monkeypatch.setattr(W, "_is_duplicate_namespaced", _nao_dup)
    monkeypatch.setattr(W, "_upload_media_bytes", _up)
    monkeypatch.setattr(W, "_download_evolution_media", _dl)
    monkeypatch.setattr(W, "_buffer_or_dispatch_text", _buf)
    doc = {"fileName": nome, "mimetype": "application/pdf"}
    if legenda:
        doc["caption"] = legenda
    corpo = {"event": "messages.upsert",
             "data": {"key": {"remoteJid": "5500999990001@s.whatsapp.net", "fromMe": False, "id": "3EB0130B0001"},
                      "pushName": "Pessoa Ficticia", "messageTimestamp": 1760000000,
                      "message": {"documentMessage": doc, "base64": base64.b64encode(pdf).decode()}}}
    from fastapi import BackgroundTasks

    integ = {"id": "int-130b", "company_id": company, "identifier": "ab-130b", "provider": "evolution"}
    asyncio.run(W._handle_evolution_like_inbound(integ, corpo, BackgroundTasks(), "evolution"))
    assert "payload" in capturado, "o ramo do documento não chegou ao buffer"
    return capturado["payload"], uploads


def _texto(payload) -> str:
    return str((payload.get("text") or {}).get("message") or "")


def test_whatsapp_apolice_vai_como_ficha_mascarada(monkeypatch):
    leitor = LeitorDublado("Apólice").instalar(monkeypatch)
    payload, uploads = _webhook(monkeypatch, _pdf())
    t = _texto(payload)
    assert t.startswith(W.MARCA_DO_DOCUMENTO % "apolice.pdf"), t[:120]
    assert (W.CABECALHO_DO_DOCUMENTO % "apolice.pdf") in t and t.rstrip().endswith("[FIM DO DOCUMENTO]")
    assert "Apólice · 3 coberturas · conferida" in t
    assert all(n in t for n, _, _ in COBERTURAS)
    assert _sem_pii(t) == [], "PII no texto do turno"
    assert "Seguradora Ficticia" not in t, "o texto CRU do PDF foi junto com a ficha"
    assert leitor.fichas == ["segurado"]
    assert leitor.chamadas == [{"bytes": len(_pdf()), "company_id": EMPRESA_A, "orcamento_s": 40.0}]
    assert payload["document"] == {"fileName": "apolice.pdf"}
    assert uploads and uploads[0]["bucket"] == "chat-docs" and uploads[0]["company_id"] == EMPRESA_A
    assert W.nome_do_documento(t, payload) == "apolice.pdf"


def test_whatsapp_orcamento_vem_do_ambiente_e_a_corretora_e_a_da_integracao(monkeypatch):
    monkeypatch.setenv("ANEXO_LEITURA_ORCAMENTO_S", "12")
    leitor = LeitorDublado("proposta").instalar(monkeypatch)
    _webhook(monkeypatch, _pdf(), company=EMPRESA_B)
    assert leitor.chamadas[0]["orcamento_s"] == 12.0 and leitor.chamadas[0]["company_id"] == EMPRESA_B
    monkeypatch.setenv("ANEXO_LEITURA_ORCAMENTO_S", "lixo")
    assert VS.orcamento_da_leitura_s() == 40.0


def test_whatsapp_legenda_preserva_a_ficha_e_o_campo(monkeypatch):
    LeitorDublado("endosso").instalar(monkeypatch)
    payload, _ = _webhook(monkeypatch, _pdf(), legenda="segue o endosso")
    t = _texto(payload)
    assert t.startswith("segue o endosso\n\n" + W.CABECALHO_DO_DOCUMENTO % "apolice.pdf")
    assert "conferida" in t and _sem_pii(t) == []
    assert payload["document"] == {"fileName": "apolice.pdf"}


def test_whatsapp_documento_que_nao_e_de_seguro_vai_mascarado(monkeypatch):
    leitor = LeitorDublado("outro").instalar(monkeypatch)
    payload, _ = _webhook(monkeypatch, _pdf("ATA DE REUNIAO", com_coberturas=False), nome="ata.pdf")
    t = _texto(payload)
    assert "Ata da reuniao do condominio" in t, t[:400]
    assert _sem_pii(t) == [], "PII no texto do documento que não é de seguro"
    assert leitor.fichas == [], "a ficha não é pedida para documento que não é de seguro"
    assert (W.CABECALHO_DO_DOCUMENTO % "ata.pdf") in t and "[FIM DO DOCUMENTO]" in t


@pytest.mark.parametrize("falha", ["excecao", "none", "ficha_vazia"])
def test_whatsapp_leitura_que_falha_pede_para_reenviar(monkeypatch, falha):
    LeitorDublado("apolice", falha=falha).instalar(monkeypatch)
    payload, _ = _webhook(monkeypatch, _pdf())
    t = _texto(payload)
    assert "não foi possível ler o conteúdo do documento" in t
    assert _sem_pii(t) == [] and "Incendio" not in t
    assert payload["document"] == {"fileName": "apolice.pdf"}


def test_sem_a_mascara_do_leitor_o_texto_nao_sai(monkeypatch):
    """Fail-closed: a máscara da F1 quebrada → nada do texto vai ao modelo (nunca o cru como 'melhor que nada')."""
    LeitorDublado("outro").instalar(monkeypatch)

    def _quebrada(_t):
        raise RuntimeError("máscara quebrada")

    monkeypatch.setattr(P, "mascarar_texto_de_apolice", _quebrada, raising=False)
    payload, _ = _webhook(monkeypatch, _pdf("ATA", com_coberturas=False), nome="ata.pdf")
    t = _texto(payload)
    assert "não foi possível ler" in t and _sem_pii(t) == []


def test_controle_o_pdf_de_teste_carrega_a_pii(monkeypatch):
    """Linha de CONTROLE: o PDF gerado TEM a PII no texto que o parser extrai — o guarda consegue falhar."""
    bruto = VS._texto_bruto_do_documento(_pdf(), "apolice.pdf")
    assert CPF in bruto and EMAIL in bruto and "Incendio" in bruto


# =====================================================================================================================
# o anexo do CORRETOR no chat principal
# =====================================================================================================================
def _chat(monkeypatch, pdf, *, nome="apolice.pdf"):
    from app.api import chat as C

    async def _baixou(url):
        assert url == "https://storage.invalid/doc.pdf?token=t"
        return pdf

    monkeypatch.setattr(VS, "baixar_documento", _baixou)
    return asyncio.run(C.anexar_documento_do_corretor("o que cobre?", "https://storage.invalid/doc.pdf?token=t",
                                                      nome, company_id=EMPRESA_A))


def test_chat_corretor_recebe_ficha_mais_texto_mascarado(monkeypatch):
    leitor = LeitorDublado("cotação").instalar(monkeypatch)
    t = _chat(monkeypatch, _pdf())
    assert t.startswith("o que cobre?\n\n[DOCUMENTO ANEXADO: apolice.pdf]\n") and t.endswith("[FIM DO DOCUMENTO]")
    assert "Apólice · 3 coberturas · conferida" in t
    assert VS.CABECALHO_DO_TEXTO_DO_CORRETOR in t and "Seguradora Ficticia" in t, "o corretor perdeu o texto"
    assert _sem_pii(t) == []
    assert leitor.fichas == ["corretor"]


def test_chat_ficha_da_f1_que_ja_traz_o_texto_nao_duplica(monkeypatch):
    LeitorDublado("apolice", ficha_corretor_com_texto=True).instalar(monkeypatch)
    t = _chat(monkeypatch, _pdf())
    assert "texto que a F1 já trouxe" in t and t.count("[TEXTO DO DOCUMENTO") == 1
    assert "Seguradora Ficticia" not in t


def test_chat_usa_o_texto_mascarado_que_o_leitor_ja_devolve(monkeypatch):
    """O `texto_mascarado` do leitor (F1) é o texto do corretor — o parser de reserva não roda de novo."""
    LeitorDublado("apolice", texto_mascarado="[pagina 1]\nCLAUSULA 7 franquia [CPF]").instalar(monkeypatch)

    def _nao_reparse(*_a, **_k):
        raise AssertionError("o leitor já devolveu o texto mascarado")

    monkeypatch.setattr(VS, "_texto_bruto_do_documento", _nao_reparse)
    t = _chat(monkeypatch, _pdf())
    assert "CLAUSULA 7 franquia [CPF]" in t and VS.CABECALHO_DO_TEXTO_DO_CORRETOR in t and _sem_pii(t) == []


def test_chat_documento_que_nao_e_de_seguro_vai_mascarado(monkeypatch):
    LeitorDublado("outro").instalar(monkeypatch)
    t = _chat(monkeypatch, _pdf("ATA", com_coberturas=False), nome="ata.pdf")
    assert "[DOCUMENTO ANEXADO: ata.pdf]" in t and "Ata da reuniao" in t and _sem_pii(t) == []


def test_chat_falha_vira_o_aviso_interno(monkeypatch):
    LeitorDublado("apolice", falha="excecao").instalar(monkeypatch)
    t = _chat(monkeypatch, _pdf())
    assert "[AVISO INTERNO: o usuário anexou o documento 'apolice.pdf' mas a extração falhou" in t
    assert _sem_pii(t) == []


def test_chat_endpoint_leva_a_ficha_ao_grafo(monkeypatch):
    """O FIO do chat: POST /chat/stream {fileUrl} → o `user_message` que o grafo recebe."""
    import importlib

    import httpx

    import test_o_chat_fala_tipado as T

    LeitorDublado("apolice").instalar(monkeypatch)

    async def _baixou(url):
        return _pdf()

    monkeypatch.setattr(VS, "baixar_documento", _baixou)
    monkeypatch.setenv("ADMIN_API_KEY", T.CHAVE_INTERNA_D)
    chat_mod = importlib.import_module("app.api.chat")
    banco = T._banco_padrao_d(conversas=[])
    stubs = T._montar_stubs_d(banco)
    stubs.pop("app.services.vision_service")                 # o vision_service é o REAL
    import uuid

    async def _rodar():
        with T._TrocaModulosD(stubs):
            T.PODE_CONSUMIR_D[:] = [True, "ok"]
            T.EVENTOS_DO_GRAFO_D[:] = [T._delta_d("ok")]
            T.CHAMADA_DO_GRAFO_D.clear()
            app = T._montar_app_d(chat_mod, banco)
            corpo = {"chatInput": "o que cobre?", "sessionId": str(uuid.uuid4()), "companyId": T.CO_ALFA_D,
                     "agentId": T.AGENTE_D, "client_request_id": str(uuid.uuid4()),
                     "fileUrl": "https://storage.invalid/doc.pdf?token=t", "fileName": "apolice.pdf"}
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t",
                                         timeout=30) as cli:
                r = await cli.post("/chat/stream", json=corpo, headers={"X-Internal-Key": T.CHAVE_INTERNA_D})
            return r, dict(T.CHAMADA_DO_GRAFO_D)

    r, chamada = asyncio.run(_rodar())
    assert r.status_code == 200
    msg = str(chamada.get("user_message") or "")
    assert "[DOCUMENTO ANEXADO: apolice.pdf]" in msg and "conferida" in msg, msg[:300]
    assert _sem_pii(msg) == []


# =====================================================================================================================
# o leitor REAL da F1 (quando ela já está na árvore) sobre o PDF gerado — o modelo é um dublê que devolve vazio
# =====================================================================================================================
@pytest.fixture
def leitor_real(monkeypatch):
    if not F1_PRONTA:
        pytest.skip("a F1 (ler_anexo_de_seguro/ficha_para_o_modelo/mascarar_texto_de_apolice) ainda não está na árvore")
    original = P.ler_anexo_de_seguro
    chamadas = []

    async def _modelo_vazio(*_a, **_k):
        chamadas.append(1)
        return None

    async def _com_modelo_dublado(file_bytes, file_name, *, company_id, orcamento_s=40.0, leitor_modelo=None):
        return await original(file_bytes, file_name, company_id=company_id, orcamento_s=orcamento_s,
                              leitor_modelo=_modelo_vazio)

    monkeypatch.setattr(P, "ler_anexo_de_seguro", _com_modelo_dublado)
    return chamadas


def test_leitor_real_whatsapp_sem_pii_com_coberturas(monkeypatch, leitor_real):
    payload, _ = _webhook(monkeypatch, _pdf())
    t = _texto(payload)
    assert _sem_pii(t) == [], "PII no texto do turno (leitor REAL)"
    assert "não foi possível ler" not in t, t[:400]
    assert all(n.split(",")[0] in t for n, _, _ in COBERTURAS), t[:600]


def test_leitor_real_chat_sem_pii_com_coberturas(monkeypatch, leitor_real):
    t = _chat(monkeypatch, _pdf())
    assert _sem_pii(t) == [] and "[AVISO INTERNO" not in t
    assert all(n.split(",")[0] in t for n, _, _ in COBERTURAS), t[:600]

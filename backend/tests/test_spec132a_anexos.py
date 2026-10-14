# -*- coding: utf-8 -*-
"""SPEC-132-A · A2 — OS ANEXOS DO CHAT, LIDOS POR BYTES (`chat_anexos.preparar`).

    BFF {attachments[]} → chat_anexos.preparar(company_id, anexos) → download do Storage (DUBLÊ) →
    imagem: JPEG ≤ 2048 em data URL + `describe_image` (o LLM do papel `visao` é DUBLÊ) · PDF: o leitor REAL da 130-B
    (o modelo do leitor é DUBLÊ) · xlsx/xls/csv: o leitor tabular REAL · docx/pptx: REAL · áudio: `AudioService` REAL
    com o cliente da API de transcrição DUBLÊ → tudo pela máscara REAL da 130-B.

Dublê SÓ na borda: o Storage, o LLM de visão, o modelo do leitor de PDF, a API de transcrição e o docling
(microserviço). A rede fica FECHADA (só o loopback do laço de eventos do Windows).

⛔ Dados fictícios: CPF sintético com DV válido, corretoras com UUID inventado, DDD 00.
Rodar: cd backend && python -m pytest tests/test_spec132a_anexos.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import io
import re
import socket
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import app.services.audio_service as AU  # noqa: E402
import app.services.chat_anexos as CA  # noqa: E402
import app.services.policy_document_evidence_service as P  # noqa: E402
import app.services.vision_service as VS  # noqa: E402

EMPRESA_A = "aaaaaaaa-0000-4000-8000-000000132a01"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-000000132a02"
DONO = "cccccccc-0000-4000-8000-000000132a03"


def _cpf_sintetico(base9: str) -> str:
    d = [int(c) for c in base9]
    for _ in range(2):
        s = sum(v * p for v, p in zip(d, range(len(d) + 1, 1, -1)))
        d.append(0 if s % 11 < 2 else 11 - s % 11)
    t = "".join(map(str, d))
    return f"{t[:3]}.{t[3:6]}.{t[6:9]}-{t[9:]}"


CPF = _cpf_sintetico("123456789")
CPF_DIGITOS = re.sub(r"\D", "", CPF)
#: um CPF que começa com ZERO: o Excel guarda como número e PERDE o zero (10 dígitos)
CPF_ZERO = _cpf_sintetico("012345678")
CPF_ZERO_NUMERO = int(re.sub(r"\D", "", CPF_ZERO))
TELEFONE = "(00) 99999-0001"
PII = (CPF, CPF_DIGITOS, CPF_ZERO, str(CPF_ZERO_NUMERO), re.sub(r"\D", "", CPF_ZERO), TELEFONE, "99999-0001",
       "15/03/1980")


def _sem_pii(texto: str) -> list:
    return [p for p in PII if p in texto]


def _path(empresa: str, bucket: str, ext: str, n: int = 1) -> str:
    return f"{empresa}/{DONO}/{bucket}/{n:08d}-2222-4333-8444-555555555555.{ext}"


# =====================================================================================================================
# os arquivos de teste, gerados aqui
# =====================================================================================================================
def _xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.append(["Nome", "CPF", "Nascimento", "Prêmio", "Observação", "Nº apólice"])
    ws.append(["Pessoa Ficticia Um", CPF, datetime(1980, 3, 15), 1234.56, f"titular CPF {CPF}", 900000123])
    ws.append(["Pessoa Ficticia Dois", CPF_ZERO_NUMERO, datetime(1975, 1, 2), 765.44, f"ligar {TELEFONE}", 900000124])
    ws2 = wb.create_sheet("Resumo")
    ws2.append(["Ramo", "Quantidade"])
    ws2.append(["Auto", 2])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _csv_ponto_e_virgula() -> bytes:
    linhas = ["Segurado;Placa do carro;Valor;Obs", f"Pessoa Ficticia;ABC1D23;1.500,00;CPF {CPF}",
              "Outra Pessoa;XYZ9K87;2.500,50;renovar em março"]
    return ("\r\n".join(linhas) + "\r\n").encode("cp1252")


def _png(lado: int = 64) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (lado, lado // 2), (200, 30, 30, 128)).save(buf, format="PNG")
    return buf.getvalue()


def _heic() -> bytes:
    import pillow_heif
    from PIL import Image

    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (10, 120, 200)).save(buf, format="HEIF")
    return buf.getvalue()


def _docx() -> bytes:
    import docx

    d = docx.Document()
    d.add_paragraph("Proposta de renovação do seguro auto")
    d.add_paragraph(f"Cliente com CPF {CPF} pediu desconto")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _pptx() -> bytes:
    """Um .pptx mínimo (só o que o leitor lê: o XML dos slides dentro do pacote)."""
    ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    slide = (f'<p:sld {ns} xmlns:p="x"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>Carteira 2026</a:t></a:r></a:p>'
             f'<a:p><a:r><a:t>Contato CPF {CPF}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("ppt/slides/slide1.xml", slide)
    return buf.getvalue()


def _pdf_minimo(linhas) -> bytes:
    """Um PDF de UMA página escrito à mão (o mesmo molde do test_spec130b_anexos: o PyMuPDF é lento nesta máquina)."""
    def _esc(s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    corpo = ["BT", "/F1 10 Tf", "14 TL", "60 780 Td"] + [f"({_esc(ln)}) Tj T*" for ln in linhas] + ["ET"]
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


def _pdf() -> bytes:
    return _pdf_minimo(["Ata da reuniao do condominio", f"Sindico: Pessoa Ficticia   CPF: {CPF}",
                        f"Telefone: {TELEFONE}", "Pauta: pintura da fachada e troca do portao"])


# =====================================================================================================================
# as bordas
# =====================================================================================================================
_CONNECT_REAL = socket.socket.connect
_CONNECT_EX_REAL = socket.socket.connect_ex


def _loopback(destino) -> bool:
    host = destino[0] if isinstance(destino, tuple) and destino else ""
    return str(host) in ("127.0.0.1", "::1", "localhost")


def _sem_rede(self, destino, *a, **k):
    if _loopback(destino):
        return _CONNECT_REAL(self, destino, *a, **k)
    raise AssertionError("a rede é fechada neste teste")


def _sem_rede_ex(self, destino, *a, **k):
    if _loopback(destino):
        return _CONNECT_EX_REAL(self, destino, *a, **k)
    raise AssertionError("a rede é fechada neste teste")


class _SanitizacaoForaDoAr:
    def _docling_parse(self, *_a, **_k):
        raise RuntimeError("docling fora do ar (teste)")


class _Storage:
    """O Supabase Storage: um dicionário (bucket, path) → bytes. Registra cada download."""

    def __init__(self):
        self.objetos = {}
        self.baixados = []

    def por(self, bucket, path, dados):
        self.objetos[(bucket, path)] = dados
        return {"bucket": bucket, "path": path}

    async def baixar(self, bucket, path):
        self.baixados.append((bucket, path))
        if (bucket, path) not in self.objetos:
            raise RuntimeError("Object not found")
        return self.objetos[(bucket, path)]


class _LlmDaVisao:
    """O modelo do papel `visao`: registra o que recebeu e devolve uma descrição COM um CPF (que a máscara tem de tirar)."""

    def __init__(self):
        self.recebido = []

    async def ainvoke(self, mensagens):
        self.recebido.append(mensagens)

        class _R:
            content = f"Foto de um para-choque amassado. Etiqueta com CPF {CPF} visível."

        return _R()


class _ApiDeTranscricao:
    def __init__(self, texto):
        self.texto = texto
        self.recebidos = []
        outer = self

        class _T:
            async def create(self, file=None, **k):
                outer.recebidos.append((getattr(file, "name", ""), k.get("model")))

                class _R:
                    text = outer.texto
                    usage = None

                return _R()

        class _A:
            transcriptions = _T()

        self.audio = _A()


@pytest.fixture(autouse=True)
def bordas(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _sem_rede)
    monkeypatch.setattr(socket.socket, "connect_ex", _sem_rede_ex)
    from app.services import sanitization_service as S

    monkeypatch.setattr(S, "SanitizationService", _SanitizacaoForaDoAr)
    storage = _Storage()
    monkeypatch.setattr(CA, "_baixar_do_storage", storage.baixar)
    llm = _LlmDaVisao()
    monkeypatch.setattr(VS, "criar_llm_de_visao", lambda **_k: llm)
    api = _ApiDeTranscricao(f"Oi, é sobre o sinistro do carro, meu CPF é {CPF} e o telefone {TELEFONE}.")
    monkeypatch.setattr(CA, "_servico_de_audio", lambda: AU.AudioService("chave-de-teste", modelo="gpt-transcribe",
                                                                         cliente=api))
    monkeypatch.setattr(AU.AudioService, "_registrar_uso", lambda *a, **k: None)
    monkeypatch.setattr(AU, "prompt_de_dominio", lambda: "Atendimento de corretora de seguros no Brasil.")
    # o leitor REAL da 130-B, com o MODELO dele dublado (devolve vazio → o regex e o texto mascarado)
    original = P.ler_anexo_de_seguro

    async def _vazio(*_a, **_k):
        return None

    async def _leitor(file_bytes, file_name, *, company_id, orcamento_s=40.0, leitor_modelo=None):
        return await original(file_bytes, file_name, company_id=company_id, orcamento_s=orcamento_s,
                              leitor_modelo=_vazio)

    monkeypatch.setattr(P, "ler_anexo_de_seguro", _leitor)
    return {"storage": storage, "llm": llm, "api": api}


def _rodar(empresa, anexos, **k):
    return asyncio.run(CA.preparar(empresa, anexos, **k))


def _anexo(storage, empresa, bucket, ext, dados, nome, mime, n=1):
    ref = storage.por(bucket, _path(empresa, bucket, ext, n), dados)
    return {**ref, "nome": nome, "mime": mime, "bytes": len(dados)}


# =====================================================================================================================
# (a) o CPF da planilha NÃO chega cru ao texto
# =====================================================================================================================
def test_a_xlsx_le_abas_cabecalho_totais_e_nenhum_cpf_cru(bordas):
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-docs", "xlsx", _xlsx(), "carteira.xlsx",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    r = _rodar(EMPRESA_A, [a])
    assert r.avisos == [], r.avisos
    t = r.texto
    assert _sem_pii(t) == [], f"PII crua no texto da planilha: {_sem_pii(t)}"
    assert t.startswith("[DOCUMENTO ANEXADO: carteira.xlsx]") and t.rstrip().endswith("[FIM DO DOCUMENTO]"), t[:200]
    assert 'Aba "Clientes"' in t and 'Aba "Resumo"' in t and "2 linhas de dados × 6 colunas" in t, t[:600]
    assert "Colunas: Nome, CPF, Nascimento, Prêmio, Observação, Nº apólice" in t, t[:600]
    assert "Pessoa Ficticia Um" in t and "| 1.234,56 |" in t, t
    assert "- Prêmio: soma 2.000,00 · mín 765,44 · máx 1.234,56 (2 valores)" in t, t
    assert "Nº apólice: soma" not in t and "Quantidade: soma 2" in t, t
    assert "[CPF]" in t and "[DATA]" in t, t
    assert r.lidos == [{"nome": "carteira.xlsx", "mime": a["mime"], "bytes": a["bytes"], "path": a["path"],
                        "bucket": "chat-docs", "tipo": "xlsx", "lido": True}], r.lidos


def test_a_controle_sem_a_mascara_o_cpf_da_planilha_passaria(bordas, monkeypatch):
    """O guarda (a) CONSEGUE falhar: com a máscara desligada (identidade), o CPF da coluna "Observação" sai cru."""
    monkeypatch.setattr(CA, "_mascarar", lambda texto: texto)
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-docs", "xlsx", _xlsx(), "carteira.xlsx",
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert CPF in _rodar(EMPRESA_A, [a]).texto


def test_a_mascara_indisponivel_e_fail_closed(bordas, monkeypatch):
    monkeypatch.setattr(CA, "_mascarar", lambda texto: None)
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-docs", "csv", _csv_ponto_e_virgula(), "lista.csv", "text/csv")
    r = _rodar(EMPRESA_A, [a])
    assert r.texto == "" and r.avisos and "com segurança" in r.avisos[0], (r.texto, r.avisos)


def test_csv_com_ponto_e_virgula_e_cp1252(bordas):
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-docs", "csv", _csv_ponto_e_virgula(), "lista.csv", "application/vnd.ms-excel")
    r = _rodar(EMPRESA_A, [a])
    t = r.texto
    assert r.avisos == [] and _sem_pii(t) == [], (r.avisos, _sem_pii(t))
    assert "2 linhas de dados × 4 colunas" in t and "renovar em março" in t, t
    assert "- Valor: soma 4.000,50 · mín 1.500,00 · máx 2.500,50 (2 valores)" in t, t
    assert "ABC1D23" not in t and "[PLACA]" in t, t
    assert r.lidos[0]["tipo"] == "csv", "o .csv que o Windows manda como vnd.ms-excel é lido como CSV"


def test_xls_quando_xlrd_existe(bordas):
    xlrd = pytest.importorskip("xlrd")
    assert xlrd is not None
    # não há escritor de .xls no ambiente: o arquivo corrompido prova que o caminho do xlrd é tomado e que vira aviso
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-docs", "xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 600, "velha.xls",
               "application/vnd.ms-excel")
    r = _rodar(EMPRESA_A, [a])
    assert r.texto == "" and len(r.avisos) == 1 and "velha.xls" in r.avisos[0], r.avisos


# =====================================================================================================================
# (b) o path de OUTRA corretora vira aviso e NÃO é baixado
# =====================================================================================================================
def test_b_path_de_outra_corretora_nao_e_baixado(bordas):
    st = bordas["storage"]
    alheio = _anexo(st, EMPRESA_B, "chat-docs", "csv", _csv_ponto_e_virgula(), "da-outra.csv", "text/csv")
    r = _rodar(EMPRESA_A, [alheio])
    assert st.baixados == [], f"baixou o arquivo de outra corretora: {st.baixados}"
    assert r.texto == "" and r.avisos == ["O anexo «da-outra.csv» não pertence a esta corretora e não foi lido."]
    assert r.lidos[0]["lido"] is False


def test_b_fuga_por_ponto_ponto_e_bucket_alheio_tambem(bordas):
    st = bordas["storage"]
    fuga = {"bucket": "chat-docs", "path": f"{EMPRESA_A}/../{EMPRESA_B}/x/y.csv", "nome": "y.csv", "mime": "text/csv"}
    balde = {**_anexo(st, EMPRESA_A, "portal-evidence", "pdf", _pdf(), "evidencia.pdf", "application/pdf")}
    sem_empresa = _anexo(st, EMPRESA_A, "chat-docs", "csv", _csv_ponto_e_virgula(), "a.csv", "text/csv", n=7)
    r = _rodar(EMPRESA_A, [fuga, balde])
    r2 = _rodar("", [sem_empresa])
    assert st.baixados == [] and len(r.avisos) == 2 and len(r2.avisos) == 1, (st.baixados, r.avisos, r2.avisos)


def test_b_controle_sem_a_conferencia_o_path_alheio_seria_baixado(bordas, monkeypatch):
    monkeypatch.setattr(CA, "path_da_corretora", lambda path, company_id: True)
    st = bordas["storage"]
    alheio = _anexo(st, EMPRESA_B, "chat-docs", "csv", _csv_ponto_e_virgula(), "da-outra.csv", "text/csv")
    _rodar(EMPRESA_A, [alheio])
    assert st.baixados == [("chat-docs", alheio["path"])]


# =====================================================================================================================
# (c) 21 MB vira aviso
# =====================================================================================================================
def test_c_arquivo_de_21_mb_vira_aviso(bordas):
    st = bordas["storage"]
    grande = b"%PDF-1.4\n" + b"0" * (21 * 1024 * 1024)
    declarado = _anexo(st, EMPRESA_A, "chat-docs", "pdf", grande, "enorme.pdf", "application/pdf", n=1)
    mentiroso = {**_anexo(st, EMPRESA_A, "chat-docs", "pdf", grande, "mentiu.pdf", "application/pdf", n=2), "bytes": 10}
    r = _rodar(EMPRESA_A, [declarado, mentiroso])
    assert r.avisos == ["O arquivo «enorme.pdf» passa de 20 MB e não foi lido.",
                        "O arquivo «mentiu.pdf» passa de 20 MB e não foi lido."], r.avisos
    assert st.baixados == [("chat-docs", mentiroso["path"])], "o declarado > 20 MB nem é baixado"
    assert r.texto == ""


# =====================================================================================================================
# (d) a imagem NUNCA vira URL externa — só data URL
# =====================================================================================================================
def test_d_imagem_vira_data_url_jpeg_e_a_descricao_mascarada(bordas):
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-media", "png", _png(3000), "para-choque.png", "image/png")
    r = _rodar(EMPRESA_A, [a])
    assert r.avisos == [] and len(r.imagens) == 1, r.avisos
    assert r.imagens[0].startswith("data:image/jpeg;base64,"), r.imagens[0][:40]
    import base64

    from PIL import Image

    jpeg = Image.open(io.BytesIO(base64.b64decode(r.imagens[0].split(",", 1)[1])))
    assert max(jpeg.size) <= CA.LADO_MAXIMO_DA_IMAGEM and jpeg.format == "JPEG", jpeg.size
    enviados = bordas["llm"].recebido
    assert len(enviados) == 1
    urls = [p["image_url"]["url"] for m in enviados[0] for p in (m.content if isinstance(m.content, list) else [])
            if isinstance(p, dict) and p.get("type") == "image_url"]
    assert urls == [r.imagens[0]], "o provedor recebe EXATAMENTE o data URL"
    assert all(u.startswith("data:image/") for u in urls) and not any("/api/storage" in u or "http" in u for u in urls)
    assert r.descricoes and CPF not in r.descricoes[0] and "[CPF]" in r.descricoes[0], r.descricoes
    bloco = r.bloco_do_turno()
    assert VS.imagem_ja_descrita(bloco) and "para-choque.png" in bloco and CPF not in bloco


def test_d_describe_image_recusa_caminho_relativo_nosso(bordas):
    """O caminho antigo (`/api/storage/...`) não vai mais ao provedor: é recusado ANTES da chamada paga."""
    out = asyncio.run(VS.describe_image("/api/storage/chat-media/x/y.png", company_id=EMPRESA_A))
    assert out is None and bordas["llm"].recebido == []
    out2 = asyncio.run(VS.describe_image(company_id=EMPRESA_A, image_bytes=_png(), mime="image/png"))
    assert out2 and bordas["llm"].recebido[-1][1].content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_heic_vira_jpeg_quando_pillow_heif_existe(bordas):
    pytest.importorskip("pillow_heif")
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-media", "heic", _heic(), "IMG_0001.HEIC", "image/heic")
    r = _rodar(EMPRESA_A, [a])
    assert r.avisos == [] and r.imagens and r.imagens[0].startswith("data:image/jpeg;base64,"), r.avisos


def test_heic_sem_pillow_heif_vira_aviso_humano(bordas, monkeypatch):
    import builtins

    real = builtins.__import__

    def _sem_heif(nome, *a, **k):
        if nome == "pillow_heif":
            raise ImportError("sem pillow_heif (teste)")
        return real(nome, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _sem_heif)
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-media", "heic", b"\0\0\0\x18ftypheic" + b"\0" * 64, "IMG_9.heic", "image/heic")
    r = _rodar(EMPRESA_A, [a])
    assert r.imagens == [] and r.avisos and "HEIC" in r.avisos[0] and "JPG" in r.avisos[0], r.avisos


# =====================================================================================================================
# (e) a falha de um arquivo não derruba os outros — e os outros formatos
# =====================================================================================================================
def test_e_um_arquivo_quebrado_nao_derruba_os_outros(bordas, monkeypatch):
    st = bordas["storage"]
    quebrado = _anexo(st, EMPRESA_A, "chat-docs", "xlsx", b"PK\x03\x04 isto nao e um xlsx", "quebrado.xlsx",
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", n=1)
    sumiu = {"bucket": "chat-docs", "path": _path(EMPRESA_A, "chat-docs", "pdf", 9), "nome": "sumiu.pdf",
             "mime": "application/pdf", "bytes": 100}
    bom = _anexo(st, EMPRESA_A, "chat-docs", "csv", _csv_ponto_e_virgula(), "bom.csv", "text/csv", n=2)
    foto = _anexo(st, EMPRESA_A, "chat-media", "png", _png(), "foto.png", "image/png", n=3)

    async def _visao_cai(*_a, **_k):
        raise RuntimeError("provedor fora do ar")

    monkeypatch.setattr(CA, "_descrever_imagem", _visao_cai)
    linhas = []

    async def _progresso(frase):
        linhas.append(frase)
        if "bom.csv" in frase:
            raise RuntimeError("a tela caiu")

    r = _rodar(EMPRESA_A, [quebrado, sumiu, bom, foto], ao_progredir=_progresso)
    assert "[DOCUMENTO ANEXADO: bom.csv]" in r.texto and r.imagens, (r.texto[:200], r.avisos)
    assert any("quebrado.xlsx" in a for a in r.avisos) and any("sumiu.pdf" in a for a in r.avisos), r.avisos
    assert len(r.avisos) == 2 and r.descricoes == [], r.avisos
    assert [x["lido"] for x in r.lidos] == [False, False, True, True]
    assert sorted(linhas) == sorted(["Lendo quebrado.xlsx…", "Lendo sumiu.pdf…", "Lendo bom.csv…",
                                     "Olhando a foto foto.png…"]), linhas


def test_e_orcamento_estourado_vira_aviso_sem_travar_o_turno(bordas, monkeypatch):
    monkeypatch.setattr(CA, "ORCAMENTO_TOTAL_S", 0.3)
    st = bordas["storage"]
    lento = _anexo(st, EMPRESA_A, "chat-docs", "txt", b"texto", "lento.txt", "text/plain", n=1)
    rapido = _anexo(st, EMPRESA_A, "chat-docs", "txt", b"ola mundo", "rapido.txt", "text/plain", n=2)
    baixar = st.baixar

    async def _devagar(bucket, path):
        if path == lento["path"]:
            await asyncio.sleep(5)
        return await baixar(bucket, path)

    monkeypatch.setattr(CA, "_baixar_do_storage", _devagar)
    r = _rodar(EMPRESA_A, [lento, rapido])
    assert "ola mundo" in r.texto and any("Demorei demais" in a and "lento.txt" in a for a in r.avisos), r.avisos


def test_pdf_pelo_leitor_da_130b_mascarado(bordas):
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-docs", "pdf", _pdf(), "ata.pdf", "application/pdf")
    r = _rodar(EMPRESA_A, [a])
    assert r.avisos == [], r.avisos
    assert r.texto.startswith("[DOCUMENTO ANEXADO: ata.pdf]") and "fachada" in r.texto, r.texto[:300]
    assert _sem_pii(r.texto) == [], _sem_pii(r.texto)


def test_docx_e_pptx_por_bytes_mascarados(bordas):
    st = bordas["storage"]
    d = _anexo(st, EMPRESA_A, "chat-docs", "docx", _docx(), "proposta.docx",
               "application/vnd.openxmlformats-officedocument.wordprocessingml.document", n=1)
    p = _anexo(st, EMPRESA_A, "chat-docs", "pptx", _pptx(), "apresentacao.pptx",
               "application/vnd.openxmlformats-officedocument.presentationml.presentation", n=2)
    r = _rodar(EMPRESA_A, [d, p])
    assert r.avisos == [], r.avisos
    assert "renovação do seguro auto" in r.texto and "Carteira 2026" in r.texto and "[slide 1]" in r.texto, r.texto
    assert _sem_pii(r.texto) == [], _sem_pii(r.texto)


def test_audio_por_bytes_transcrito_e_mascarado(bordas):
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-docs", "opus", b"OggS" + b"\0" * 200, "nota de voz.opus", "audio/ogg")
    r = _rodar(EMPRESA_A, [a])
    assert r.avisos == [] and len(r.transcricoes) == 1, r.avisos
    assert "sinistro do carro" in r.transcricoes[0] and _sem_pii(r.transcricoes[0]) == [], r.transcricoes
    nome_tmp, modelo = bordas["api"].recebidos[0]
    assert nome_tmp.endswith(".ogg") and modelo == "gpt-transcribe", "o .opus vai à API como .ogg"
    assert "[ÁUDIO ANEXADO: nota de voz.opus — transcrição]" in r.bloco_do_turno()


def test_nome_do_arquivo_com_cpf_sai_mascarado(bordas):
    st = bordas["storage"]
    a = _anexo(st, EMPRESA_A, "chat-docs", "txt", b"conteudo qualquer", f"rg {CPF}.txt", "text/plain")
    r = _rodar(EMPRESA_A, [a])
    tudo = r.bloco_do_turno() + repr(r.lidos)
    assert CPF not in tudo and "conteudo qualquer" in r.texto, tudo[:300]


def test_mais_de_dez_anexos_le_os_dez_primeiros(bordas):
    st = bordas["storage"]
    anexos = [_anexo(st, EMPRESA_A, "chat-docs", "txt", f"arquivo {i}".encode(), f"a{i}.txt", "text/plain", n=i)
              for i in range(12)]
    r = _rodar(EMPRESA_A, anexos)
    assert len(r.lidos) == 10 and r.avisos == ["Li só os 10 primeiros arquivos desta mensagem."], r.avisos


def test_lista_vazia_e_lixo_nao_lancam(bordas):
    assert _rodar(EMPRESA_A, []).bloco_do_turno() == ""
    r = _rodar(EMPRESA_A, [None, "x", 3])  # type: ignore[list-item]
    assert r.lidos == [] and r.avisos == []

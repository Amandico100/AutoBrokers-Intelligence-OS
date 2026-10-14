"""SPEC-132-A · A2 — OS ANEXOS DO CHAT PRINCIPAL, LIDOS POR BYTES.

O fio (SPEC-132-A §2):
    composer → POST /api/upload → {bucket, path, nome, mime, bytes}
    → POST /api/chat/stream {attachments[]} → BFF (path com o prefixo DESTA corretora, senão 403)
    → backend /chat/stream → _gerar → **chat_anexos.preparar(company_id, attachments)** → bloco do turno → modelo

📊 B3/B4 (14/10/2026): o anexo "dava erro" por dois motivos encadeados — a tela lia `publicUrl` (que o upload nunca
devolveu) e, quando havia URL, era `/api/storage/...` RELATIVA e atrás da sessão: o `httpx.get` do backend e o
provedor de visão nunca a alcançavam. Aqui o backend baixa os BYTES do Supabase Storage com a service role
(D-132A-05) e o provedor de IA recebe só data URL — nunca URL nossa.

Cada formato pelo leitor que JÁ existe (CLAUDE.md §5 — nenhum leitor paralelo):
    imagem (jpeg/png/gif/webp/HEIC) → JPEG ≤ 2048 px em data URL + a descrição do papel `visao` (`describe_image`)
    PDF                              → `vision_service.conteudo_do_anexo` (o leitor da SPEC-130-B, audiência corretor)
    xlsx/xls/csv                     → o leitor TABULAR deste módulo (abas, cabeçalho, amostra, totais)
    docx/pptx                        → docling quando instalado; senão python-docx / o XML do pacote Office
    txt/md                           → o texto
    áudio                            → `AudioService.transcribe_audio_bytes` (papel `transcricao`)
🔴 TUDO que é texto sai pela máscara da 130-B (`vision_service.mascarar`, fail-closed): sem a máscara, o texto não sai.
🔴 Defesa em profundidade: o BFF já conferiu o prefixo; aqui ele é conferido DE NOVO contra o `company_id` do turno.
⛔ Nunca lança. O que falha vira AVISO em português. Nunca loga conteúdo, nome de arquivo nem CPF — só contagens.
"""
from __future__ import annotations

import asyncio
import csv
import io
import logging
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

#: Cada arquivo cabe em 20 MB (o mesmo teto do upload — `app/api/upload/route.ts`).
LIMITE_DE_BYTES = 20 * 1024 * 1024
#: Até 10 arquivos por mensagem (o mesmo teto do BFF).
MAX_ANEXOS = 10
#: 💭 Orçamento TOTAL da leitura de todos os anexos de um turno (SPEC-132-A §5).
ORCAMENTO_TOTAL_S = 45.0
#: Os buckets do chat. `avatars`, `voice-messages` e `portal-evidence` nunca são lidos por aqui.
BUCKETS_DO_CHAT = frozenset({"chat-media", "chat-docs"})
#: 💭 A amostra da planilha: até 50 linhas por aba.
LINHAS_DA_AMOSTRA = 50
#: 💭 Colunas mostradas na amostra (o resto é contado, não mostrado).
COLUNAS_DA_AMOSTRA = 30
#: 💭 Abas lidas por planilha e linhas lidas por aba (para contar e somar).
ABAS_LIDAS = 10
LINHAS_LIDAS_POR_ABA = 50_000
#: O lado maior da imagem que vai ao modelo.
LADO_MAXIMO_DA_IMAGEM = 2048
#: 💭 O teto do texto de TODOS os anexos juntos (cada documento já vem truncado em 20.000 pela 130-B).
TETO_DO_TEXTO = 60_000

_SEGMENTO_SEGURO = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


@dataclass
class ResultadoDosAnexos:
    """O que os anexos de UM turno viram para o modelo.

    texto         blocos `[DOCUMENTO ANEXADO: …]…[FIM DO DOCUMENTO]` (PDF, planilha, Word, PowerPoint, texto) — MASCARADOS
    imagens       data URLs `data:image/jpeg;base64,…` (para um modelo que vê) — nunca URL nossa
    descricoes    a descrição de cada foto pelo papel `visao`, MASCARADA (para um modelo que não vê)
    transcricoes  o texto de cada áudio, MASCARADO
    avisos        o que não deu para ler, em português, para o corretor (e para o modelo dizer com naturalidade)
    lidos         um registro por anexo, SEM conteúdo: {nome (mascarado), mime, bytes, path, bucket, tipo, lido}
    """

    texto: str = ""
    imagens: List[str] = field(default_factory=list)
    descricoes: List[str] = field(default_factory=list)
    transcricoes: List[str] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)
    lidos: List[Dict[str, Any]] = field(default_factory=list)
    _nomes_das_descricoes: List[str] = field(default_factory=list, repr=False)
    _nomes_das_transcricoes: List[str] = field(default_factory=list, repr=False)

    def bloco_do_turno(self) -> str:
        """Tudo junto, pronto para entrar no texto do turno (o que a A3 anexa à mensagem do corretor).

        As descrições levam a MARCA do contexto visual (`[CONTEXTO VISUAL`), que o grafo reconhece para não descrever
        a foto de novo (`vision_service.imagem_ja_descrita`)."""
        partes: List[str] = []
        if self.texto:
            partes.append(self.texto)
        for nome, desc in zip(self._nomes_das_descricoes, self.descricoes):
            partes.append(f"[CONTEXTO VISUAL — imagem enviada pelo usuário: {nome}]:\n{desc}")
        for nome, transc in zip(self._nomes_das_transcricoes, self.transcricoes):
            partes.append(f"[ÁUDIO ANEXADO: {nome} — transcrição]\n{transc}\n[FIM DO ÁUDIO]")
        for aviso in self.avisos:
            partes.append(f"[AVISO INTERNO: {aviso} — diga isso ao usuário com naturalidade.]")
        return "\n\n".join(partes)


# =====================================================================================================================
# as bordas (os testes trocam SÓ estas: o Storage, a visão e o áudio)
# =====================================================================================================================
async def _baixar_do_storage(bucket: str, path: str) -> Optional[bytes]:
    """Os BYTES do objeto no Supabase Storage, com a service role do backend (o cliente que já existe)."""
    from app.core.database import get_supabase_client

    def _baixar() -> Optional[bytes]:
        dado = get_supabase_client().client.storage.from_(bucket).download(path)
        return bytes(dado) if dado else None

    return await asyncio.to_thread(_baixar)


async def _descrever_imagem(data_url: str, company_id: str) -> Optional[str]:
    """A descrição da foto pelo papel `visao` — o `describe_image` de sempre, agora com data URL."""
    from app.services import vision_service

    return await vision_service.describe_image(data_url, company_id=company_id, purpose_hint="Assistente")


def _servico_de_audio():
    """O `AudioService` do backend (papel `transcricao`)."""
    from app.core import settings
    from app.services.audio_service import AudioService

    return AudioService(openai_api_key=settings.OPENAI_API_KEY)


async def _transcrever_audio(dados: bytes, mime: str, nome: str, company_id: str) -> str:
    return await _servico_de_audio().transcribe_audio_bytes(dados, mime, nome=nome, company_id=company_id)


# =====================================================================================================================
# a máscara (a da 130-B; fail-closed)
# =====================================================================================================================
def _mascarar(texto: str) -> Optional[str]:
    from app.services.vision_service import mascarar

    return mascarar(texto)


def _nome_para_o_modelo(nome: str) -> str:
    try:
        from app.services.vision_service import nome_do_anexo_para_o_modelo

        return nome_do_anexo_para_o_modelo(nome, padrao="arquivo")
    except Exception:  # noqa: BLE001 — sem a máscara, nunca o nome cru
        return "arquivo"


def _truncar(texto: str) -> str:
    from app.services.vision_service import truncate_document_text

    return truncate_document_text(texto)


# =====================================================================================================================
# o tipo do anexo
# =====================================================================================================================
_EXT_IMAGEM = {"jpg", "jpeg", "png", "gif", "webp", "heic", "heif"}
_EXT_AUDIO = {"m4a", "mp3", "mpeg", "ogg", "oga", "opus", "wav", "webm", "aac"}
_MIME_PARA_TIPO = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "text/csv": "csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/plain": "texto",
    "text/markdown": "texto",
}
_EXT_PARA_TIPO = {"pdf": "pdf", "xlsx": "xlsx", "xls": "xls", "csv": "csv", "docx": "docx", "pptx": "pptx",
                  "txt": "texto", "md": "texto", "markdown": "texto"}


def _extensao(nome: str) -> str:
    nome = str(nome or "")
    return nome.rsplit(".", 1)[-1].lower() if "." in nome else ""


def tipo_do_anexo(mime: str, nome: str = "", path: str = "") -> str:
    """imagem · pdf · xlsx · xls · csv · docx · pptx · texto · audio · '' (desconhecido). A extensão do NOME vence a do path."""
    ext = _extensao(nome) or _extensao(path)
    # o .csv do Windows chega como application/vnd.ms-excel: a extensão decide antes do MIME
    if ext in _EXT_PARA_TIPO:
        return _EXT_PARA_TIPO[ext]
    if ext in _EXT_IMAGEM:
        return "imagem"
    if ext in _EXT_AUDIO:
        return "audio"
    m = str(mime or "").split(";")[0].strip().lower()
    if m.startswith("image/"):
        return "imagem"
    if m.startswith("audio/"):
        return "audio"
    return _MIME_PARA_TIPO.get(m, "")


def path_da_corretora(path: Any, company_id: str) -> bool:
    """O objeto é DESTA corretora? Segmentos limpos, sem `..`, e o 1º é o `company_id` do turno."""
    if not isinstance(path, str) or not path or len(path) > 512 or not company_id:
        return False
    segmentos = path.split("/")
    if len(segmentos) < 2:
        return False
    if not all(_SEGMENTO_SEGURO.match(s) and s not in (".", "..") for s in segmentos):
        return False
    return segmentos[0] == company_id


# =====================================================================================================================
# imagem
# =====================================================================================================================
def _e_heic(dados: bytes, mime: str, nome: str) -> bool:
    m = str(mime or "").lower()
    return ("heic" in m or "heif" in m or _extensao(nome) in ("heic", "heif")
            or (dados[4:8] == b"ftyp" and dados[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis",
                                                           b"mif1", b"msf1")))


AVISO_HEIC = ("Não consegui abrir a foto «{nome}» (formato HEIC, do iPhone). Pode mandar em JPG — ou tirar um print "
              "da tela e mandar o print?")


def _imagem_para_jpeg(dados: bytes, mime: str, nome: str) -> Tuple[Optional[bytes], str, Optional[str]]:
    """(bytes, mime, aviso). HEIC → JPEG; qualquer foto → lado ≤ 2048 px, orientação do EXIF, JPEG 85."""
    heic = _e_heic(dados, mime, nome)
    try:
        from PIL import Image, ImageOps
    except Exception:  # noqa: BLE001 — sem Pillow: só os formatos que o provedor lê direto
        if heic:
            return None, "", AVISO_HEIC
        tipo = str(mime or "image/jpeg").split(";")[0].strip().lower()
        if tipo in ("image/jpeg", "image/png", "image/gif", "image/webp") and len(dados) <= 5 * 1024 * 1024:
            return dados, tipo, None
        return None, "", "Não consegui preparar a foto «{nome}» para leitura. Pode mandar em tamanho menor?"
    if heic:
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
        except Exception:  # noqa: BLE001
            return None, "", AVISO_HEIC
    try:
        with Image.open(io.BytesIO(dados)) as img:
            img.seek(0)
            img = ImageOps.exif_transpose(img)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
                fundo = Image.new("RGB", img.size, (255, 255, 255))
                fundo.paste(img, mask=img.split()[-1])
                img = fundo
            elif img.mode != "RGB":
                img = img.convert("RGB")
            img.thumbnail((LADO_MAXIMO_DA_IMAGEM, LADO_MAXIMO_DA_IMAGEM))
            saida = io.BytesIO()
            img.save(saida, format="JPEG", quality=85, optimize=True)
            return saida.getvalue(), "image/jpeg", None
    except Exception as e:  # noqa: BLE001
        logger.warning("[ANEXOS] imagem não abriu (%s)", type(e).__name__)
        if heic:
            return None, "", AVISO_HEIC
        return None, "", "Não consegui abrir a foto «{nome}». Ela pode estar corrompida — tente mandar de novo."


# =====================================================================================================================
# planilha (xlsx · xls · csv) — o leitor TABULAR
# =====================================================================================================================
def _sem_acento(valor: Any) -> str:
    t = unicodedata.normalize("NFKD", str(valor or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


#: Coluna cujo NOME diz o que ela guarda → o marcador da 130-B na célula inteira (a máscara de texto não reconhece
#: uma data de nascimento solta numa célula, nem um CPF que o Excel guardou como número sem o zero da frente).
_COLUNAS_SENSIVEIS: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"\bcnpj\b"), "[CNPJ]"),
    (re.compile(r"\bcpf\b"), "[CPF]"),
    (re.compile(r"\brg\b|\bidentidade\b"), "[RG]"),
    (re.compile(r"\bnasc|\bnascimento\b|\bdt nasc|\bdata de nasc"), "[DATA]"),
    (re.compile(r"\btelefone\b|\bcelular\b|\bfone\b|\btel\b|\bwhatsapp\b"), "[TELEFONE]"),
    (re.compile(r"\be ?mail\b"), "[EMAIL]"),
    (re.compile(r"\bcep\b"), "[CEP]"),
    (re.compile(r"\bplaca\b"), "[PLACA]"),
    (re.compile(r"\bchassi\b"), "[CHASSI]"),
)
#: Colunas de identificador: nunca somadas (a soma de números de apólice não diz nada, e o mín/máx expõe um).
#: Pelo COMEÇO do nome: "Nº da apólice" e "Apólice" são identificadores; "Prêmio da apólice" é dinheiro.
_COLUNAS_DE_IDENTIFICADOR = re.compile(r"^(?:id|codigo|cod|ano|n|no|numero|num|matricula|apolice|proposta|endosso)\b")


def _marcador_da_coluna(cabecalho: str) -> Optional[str]:
    n = _sem_acento(cabecalho)
    for padrao, marcador in _COLUNAS_SENSIVEIS:
        if padrao.search(n):
            return marcador
    return None


def _formatar_numero(v: float) -> str:
    """Inteiro sem separador (o CPF que o Excel guardou como número cai na máscara de dígitos crus);
    decimal com vírgula e 2 casas, como o corretor lê."""
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return _formatar_dinheiro(v)


def _formatar_dinheiro(v: float) -> str:
    """`1.234,56` — a coluna que tem centavos é somada e mostrada como o corretor lê dinheiro."""
    inteiro, _, frac = f"{abs(v):,.2f}".partition(".")
    return ("-" if v < 0 else "") + inteiro.replace(",", ".") + "," + frac


def _celula_em_texto(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "sim" if v else "não"
    if isinstance(v, (int, float)):
        return _formatar_numero(float(v))
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y") + ("" if v.time() == time(0, 0) else v.strftime(" %H:%M"))
    if isinstance(v, date):
        return v.strftime("%d/%m/%Y")
    return " ".join(str(v).split())


_NUMERO_BR = re.compile(r"^-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?$")
_NUMERO_PONTO = re.compile(r"^-?\d+\.\d+$")


def _numero(v: Any) -> Optional[float]:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").replace(" ", "").replace(" ", "")
    if not s:
        return None
    try:
        if _NUMERO_BR.match(s):
            return float(s.replace(".", "").replace(",", "."))
        if _NUMERO_PONTO.match(s):
            return float(s)
    except ValueError:
        return None
    return None


def _celula_md(texto: str) -> str:
    t = texto.replace("|", "/").replace("\n", " ")
    return t if len(t) <= 80 else t[:77] + "..."


def _uma_aba(nome_da_aba: str, linhas: List[List[Any]], truncou_linhas: bool) -> str:
    linhas = [ln for ln in linhas if any(c not in (None, "") and str(c).strip() for c in ln)]
    if not linhas:
        return f'## Aba "{nome_da_aba}" — vazia'
    largura = max(len(ln) for ln in linhas)
    cab_bruto = list(linhas[0]) + [None] * (largura - len(linhas[0]))
    cabecalho = [(_celula_em_texto(c) or f"coluna {i + 1}") for i, c in enumerate(cab_bruto)]
    dados = [list(ln) + [None] * (largura - len(ln)) for ln in linhas[1:]]
    marcadores = [_marcador_da_coluna(c) for c in cabecalho]

    def _celula(i: int, v: Any) -> str:
        if marcadores[i] and v not in (None, "") and str(v).strip():
            return marcadores[i]
        return _celula_em_texto(v)

    total = len(dados)
    out = [f'## Aba "{nome_da_aba}" — {total}{"+" if truncou_linhas else ""} linhas de dados × {largura} colunas',
           "Colunas: " + ", ".join(cabecalho)]
    mostradas = list(range(min(largura, COLUNAS_DA_AMOSTRA)))
    if total:
        out.append("| " + " | ".join(_celula_md(cabecalho[i]) for i in mostradas) + " |")
        out.append("|" + "---|" * len(mostradas))
        for ln in dados[:LINHAS_DA_AMOSTRA]:
            out.append("| " + " | ".join(_celula_md(_celula(i, ln[i])) for i in mostradas) + " |")
        if total > LINHAS_DA_AMOSTRA:
            out.append(f"(mostrando {LINHAS_DA_AMOSTRA} de {total} linhas)")
        if largura > COLUNAS_DA_AMOSTRA:
            out.append(f"(mostrando {COLUNAS_DA_AMOSTRA} de {largura} colunas)")
    totais = []
    for i in range(largura):
        if marcadores[i] or _COLUNAS_DE_IDENTIFICADOR.search(_sem_acento(cabecalho[i])):
            continue
        valores = [ln[i] for ln in dados if ln[i] not in (None, "") and str(ln[i]).strip()]
        if not valores:
            continue
        nums = [_numero(v) for v in valores]
        if any(n is None for n in nums):
            continue
        # 8+ dígitos inteiros parece identificador (CPF sem pontuação, telefone, número de documento): não se soma
        if all(n == int(n) for n in nums) and max(abs(n) for n in nums) >= 1e7:
            continue
        decimal = any(n != int(n) for n in nums)
        fmt = _formatar_dinheiro if decimal else _formatar_numero
        totais.append(f"- {cabecalho[i]}: soma {fmt(sum(nums))} · mín {fmt(min(nums))} · "
                      f"máx {fmt(max(nums))} ({len(nums)} valores)")
    if totais:
        out.append("Totais das colunas numéricas:")
        out.extend(totais)
    return "\n".join(out)


def _abas_do_xlsx(dados: bytes) -> List[Tuple[str, List[List[Any]], bool]]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(dados), read_only=True, data_only=True)
    try:
        abas = []
        for ws in wb.worksheets[:ABAS_LIDAS]:
            linhas, truncou = [], False
            for i, ln in enumerate(ws.iter_rows(values_only=True)):
                if i >= LINHAS_LIDAS_POR_ABA:
                    truncou = True
                    break
                linhas.append(list(ln))
            abas.append((str(ws.title), linhas, truncou))
        return abas
    finally:
        wb.close()


def _abas_do_xls(dados: bytes) -> List[Tuple[str, List[List[Any]], bool]]:
    import xlrd

    wb = xlrd.open_workbook(file_contents=dados, on_demand=True)
    try:
        abas = []
        for idx in range(min(wb.nsheets, ABAS_LIDAS)):
            sh = wb.sheet_by_index(idx)
            linhas = []
            for r in range(min(sh.nrows, LINHAS_LIDAS_POR_ABA)):
                ln = []
                for c in range(sh.ncols):
                    cel = sh.cell(r, c)
                    if cel.ctype == xlrd.XL_CELL_DATE:
                        try:
                            ln.append(xlrd.xldate_as_datetime(cel.value, wb.datemode))
                        except Exception:  # noqa: BLE001
                            ln.append(cel.value)
                    elif cel.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                        ln.append(None)
                    elif cel.ctype == xlrd.XL_CELL_BOOLEAN:
                        ln.append(bool(cel.value))
                    else:
                        ln.append(cel.value)
                linhas.append(ln)
            abas.append((str(sh.name), linhas, sh.nrows > LINHAS_LIDAS_POR_ABA))
        return abas
    finally:
        wb.release_resources()


def _decodificar_texto(dados: bytes) -> str:
    for codificacao in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return dados.decode("utf-8", errors="replace")


def _abas_do_csv(dados: bytes) -> List[Tuple[str, List[List[Any]], bool]]:
    texto = _decodificar_texto(dados)
    amostra = texto[:8192]
    try:
        separador = csv.Sniffer().sniff(amostra, delimiters=";,\t|").delimiter
    except csv.Error:
        primeira = amostra.splitlines()[0] if amostra.splitlines() else ""
        separador = max(";,\t|", key=primeira.count)
    linhas, truncou = [], False
    for i, ln in enumerate(csv.reader(io.StringIO(texto), delimiter=separador)):
        if i >= LINHAS_LIDAS_POR_ABA:
            truncou = True
            break
        linhas.append(ln)
    return [("CSV", linhas, truncou)]


def tabela_da_planilha(dados: bytes, tipo: str) -> str:
    """O texto CRU da planilha (cabeçalho, amostra, totais por aba). ⚠️ Só sai deste módulo pela máscara."""
    leitor = {"xlsx": _abas_do_xlsx, "xls": _abas_do_xls, "csv": _abas_do_csv}[tipo]
    abas = leitor(dados)
    cabeca = f"Planilha com {len(abas)} aba(s)." if tipo != "csv" else "Arquivo CSV."
    return "\n\n".join([cabeca] + [_uma_aba(nome, linhas, truncou) for nome, linhas, truncou in abas])


# =====================================================================================================================
# Word e PowerPoint
# =====================================================================================================================
def _xml_em_texto(xml: str, marca_de_texto: str, marca_de_paragrafo: str) -> str:
    import html

    paragrafos = []
    for p in re.split(rf"</{marca_de_paragrafo}>", xml):
        pedacos = re.findall(rf"<{marca_de_texto}(?:\s[^>]*)?>([^<]*)</{marca_de_texto}>", p)
        linha = html.unescape("".join(pedacos)).strip()
        if linha:
            paragrafos.append(linha)
    return "\n".join(paragrafos)


def _texto_do_docx(dados: bytes) -> str:
    try:
        import docx  # python-docx

        doc = docx.Document(io.BytesIO(dados))
        partes = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        for tabela in doc.tables:
            for linha in tabela.rows:
                celulas = [" ".join(c.text.split()) for c in linha.cells]
                if any(celulas):
                    partes.append(" | ".join(celulas))
        return "\n".join(partes)
    except ImportError:
        pass
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        return _xml_em_texto(z.read("word/document.xml").decode("utf-8", errors="replace"), "w:t", "w:p")


def _texto_do_pptx(dados: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        slides = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
                        key=lambda n: int(re.findall(r"\d+", n)[-1]))
        partes = []
        for i, nome in enumerate(slides, 1):
            texto = _xml_em_texto(z.read(nome).decode("utf-8", errors="replace"), "a:t", "a:p")
            if texto:
                partes.append(f"[slide {i}]\n{texto}")
        return "\n\n".join(partes)


def _docling_instalado() -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec("docling") is not None
    except Exception:  # noqa: BLE001
        return False


# =====================================================================================================================
# um anexo
# =====================================================================================================================
@dataclass
class _Leitura:
    tipo: str = ""
    bloco: str = ""
    imagem: str = ""
    descricao: str = ""
    transcricao: str = ""
    aviso: str = ""
    lido: bool = False


def _bloco(nome: str, corpo: str) -> str:
    return f"[DOCUMENTO ANEXADO: {nome}]\n{corpo}\n[FIM DO DOCUMENTO]"


async def _texto_mascarado(bruto: str) -> Optional[str]:
    if not str(bruto or "").strip():
        return None
    mascarado = _mascarar(bruto)
    if not mascarado or not mascarado.strip():
        return None
    return _truncar(mascarado)


async def _ler_um(company_id: str, anexo: Dict[str, Any], nome: str, tipo: str,
                  ao_progredir: Optional[Callable[[str], Awaitable[None]]]) -> _Leitura:
    r = _Leitura(tipo=tipo)
    bucket = str(anexo.get("bucket") or "")
    path = anexo.get("path")
    mime = str(anexo.get("mime") or "").split(";")[0].strip().lower()
    nome_cru = str(anexo.get("nome") or "")

    if bucket not in BUCKETS_DO_CHAT or not path_da_corretora(path, company_id):
        r.aviso = f"O anexo «{nome}» não pertence a esta corretora e não foi lido."
        return r
    declarado = anexo.get("bytes")
    if isinstance(declarado, (int, float)) and declarado > LIMITE_DE_BYTES:
        r.aviso = f"O arquivo «{nome}» passa de 20 MB e não foi lido."
        return r
    if not tipo:
        r.aviso = f"Ainda não sei ler o formato de «{nome}»."
        return r

    if ao_progredir is not None:
        frase = {"imagem": f"Olhando a foto {nome}…", "audio": f"Ouvindo o áudio {nome}…"}.get(tipo, f"Lendo {nome}…")
        try:
            await ao_progredir(frase)
        except Exception:  # noqa: BLE001 — a linha de atividade nunca derruba a leitura
            pass

    try:
        dados = await _baixar_do_storage(bucket, str(path))
    except Exception as e:  # noqa: BLE001
        logger.warning("[ANEXOS] download falhou (%s)", type(e).__name__)
        dados = None
    if not dados:
        r.aviso = f"Não encontrei o arquivo «{nome}». Pode mandar de novo?"
        return r
    if len(dados) > LIMITE_DE_BYTES:
        r.aviso = f"O arquivo «{nome}» passa de 20 MB e não foi lido."
        return r

    if tipo == "imagem":
        jpeg, tipo_img, aviso = await asyncio.to_thread(_imagem_para_jpeg, dados, mime, nome_cru)
        if not jpeg:
            r.aviso = (aviso or "Não consegui abrir a foto «{nome}».").replace("{nome}", nome)
            return r
        from app.services.vision_service import data_url_da_imagem

        r.imagem = data_url_da_imagem(jpeg, tipo_img)
        r.lido = True
        try:
            desc = await _descrever_imagem(r.imagem, company_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("[ANEXOS] descrição da foto falhou (%s)", type(e).__name__)
            desc = None
        if desc:
            mascarada = _mascarar(desc)
            if mascarada and mascarada.strip():
                r.descricao = mascarada.strip()
        return r

    if tipo == "pdf":
        from app.services import vision_service

        corpo = await vision_service.conteudo_do_anexo(
            dados, nome_cru or "documento.pdf", company_id=company_id, audiencia="corretor",
            orcamento_s=max(5.0, ORCAMENTO_TOTAL_S - 10.0))
        if not corpo:
            r.aviso = (f"Não consegui ler o PDF «{nome}». Se ele for uma foto digitalizada, mande as páginas como "
                       "imagem — ou cole aqui o trecho que importa.")
            return r
        r.bloco, r.lido = _bloco(nome, corpo), True
        return r

    if tipo in ("xlsx", "xls", "csv"):
        try:
            bruto = await asyncio.to_thread(tabela_da_planilha, dados, tipo)
        except ImportError:
            r.aviso = f"Ainda não consigo abrir planilhas .{tipo} aqui. Pode salvar «{nome}» como .xlsx ou .csv?"
            return r
        except Exception as e:  # noqa: BLE001
            logger.warning("[ANEXOS] planilha não abriu (%s)", type(e).__name__)
            r.aviso = f"Não consegui abrir a planilha «{nome}». Ela pode estar protegida por senha ou corrompida."
            return r
        corpo = await _texto_mascarado(bruto)
        if not corpo:
            r.aviso = f"Não consegui ler a planilha «{nome}» com segurança agora."
            return r
        r.bloco, r.lido = _bloco(nome, corpo), True
        return r

    if tipo in ("docx", "pptx"):
        corpo = None
        if _docling_instalado():
            from app.services import vision_service

            corpo = await vision_service.texto_mascarado_do_documento(dados, nome_cru or f"documento.{tipo}")
        if not corpo:
            try:
                bruto = await asyncio.to_thread(_texto_do_docx if tipo == "docx" else _texto_do_pptx, dados)
            except Exception as e:  # noqa: BLE001
                logger.warning("[ANEXOS] %s não abriu (%s)", tipo, type(e).__name__)
                bruto = ""
            corpo = await _texto_mascarado(bruto)
        if not corpo:
            r.aviso = f"Não consegui ler o arquivo «{nome}». Pode colar aqui o trecho que importa?"
            return r
        r.bloco, r.lido = _bloco(nome, corpo), True
        return r

    if tipo == "texto":
        corpo = await _texto_mascarado(_decodificar_texto(dados))
        if not corpo:
            r.aviso = f"O arquivo «{nome}» está vazio ou não consegui lê-lo."
            return r
        r.bloco, r.lido = _bloco(nome, corpo), True
        return r

    if tipo == "audio":
        try:
            texto = await _transcrever_audio(dados, mime, nome_cru, company_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("[ANEXOS] transcrição falhou (%s)", type(e).__name__)
            texto = ""
        if not str(texto or "").strip():
            r.aviso = f"Não consegui ouvir o áudio «{nome}». Pode escrever em poucas palavras o que ele diz?"
            return r
        mascarado = _mascarar(texto)
        if not mascarado or not mascarado.strip():
            r.aviso = f"Não consegui ouvir o áudio «{nome}» com segurança agora. Pode escrever o que ele diz?"
            return r
        r.transcricao, r.lido = mascarado.strip(), True
        return r

    r.aviso = f"Ainda não sei ler o formato de «{nome}»."
    return r


# =====================================================================================================================
# o contrato (A2 → A3)
# =====================================================================================================================
async def preparar(
    company_id: str,
    anexos: List[Dict[str, Any]],
    *,
    ao_progredir: Optional[Callable[[str], Awaitable[None]]] = None,
) -> ResultadoDosAnexos:
    """Lê os anexos de UM turno do chat, em paralelo, com orçamento total de 💭 45 s. Nunca lança.

    `anexos`: a lista que o BFF repassou — `[{bucket, path, nome, mime, bytes}]`, cada path já conferido contra a
    corretora da sessão (e conferido de novo aqui). `ao_progredir("Lendo apolice.pdf…")` é chamado por arquivo,
    antes do download — é a linha de atividade da tela (evento `activity`).
    """
    resultado = ResultadoDosAnexos()
    company_id = str(company_id or "").strip()
    if company_id.lower() == "none":
        company_id = ""
    lista = [a for a in (anexos or []) if isinstance(a, dict)]
    if not lista:
        return resultado
    if len(lista) > MAX_ANEXOS:
        resultado.avisos.append(f"Li só os {MAX_ANEXOS} primeiros arquivos desta mensagem.")
        lista = lista[:MAX_ANEXOS]

    preparados = []
    for a in lista:
        nome = _nome_para_o_modelo(str(a.get("nome") or "") or str(a.get("path") or "").rsplit("/", 1)[-1])
        tipo = tipo_do_anexo(str(a.get("mime") or ""), str(a.get("nome") or ""), str(a.get("path") or ""))
        preparados.append((a, nome, tipo))

    tarefas = [asyncio.ensure_future(_ler_um(company_id, a, nome, tipo, ao_progredir)) for a, nome, tipo in preparados]
    try:
        _feitas, pendentes = await asyncio.wait(tarefas, timeout=ORCAMENTO_TOTAL_S)
    except Exception as e:  # noqa: BLE001
        logger.error("[ANEXOS] espera falhou (%s)", type(e).__name__)
        pendentes = {t for t in tarefas if not t.done()}
    for t in pendentes:
        t.cancel()

    blocos: List[str] = []
    for tarefa, (a, nome, tipo) in zip(tarefas, preparados):
        if tarefa in pendentes:
            leitura = _Leitura(tipo=tipo, aviso=f"Demorei demais para ler «{nome}». Pode mandar de novo, ou só o "
                                                 "trecho que importa?")
        else:
            try:
                leitura = tarefa.result()
            except Exception as e:  # noqa: BLE001 — um arquivo que estoura não derruba os outros
                logger.error("[ANEXOS] leitura estourou (%s)", type(e).__name__)
                leitura = _Leitura(tipo=tipo, aviso=f"Não consegui ler «{nome}». Pode mandar de novo?")
        if leitura.bloco:
            blocos.append(leitura.bloco)
        if leitura.imagem:
            resultado.imagens.append(leitura.imagem)
        if leitura.descricao:
            resultado.descricoes.append(leitura.descricao)
            resultado._nomes_das_descricoes.append(nome)
        if leitura.transcricao:
            resultado.transcricoes.append(leitura.transcricao)
            resultado._nomes_das_transcricoes.append(nome)
        if leitura.aviso:
            resultado.avisos.append(leitura.aviso)
        resultado.lidos.append({
            "nome": nome,
            "mime": str(a.get("mime") or "")[:100],
            "bytes": a.get("bytes") if isinstance(a.get("bytes"), (int, float)) else None,
            "path": a.get("path") if isinstance(a.get("path"), str) else None,
            "bucket": a.get("bucket") if isinstance(a.get("bucket"), str) else None,
            "tipo": tipo or "desconhecido",
            "lido": bool(leitura.lido),
        })

    texto = "\n\n".join(blocos)
    if len(texto) > TETO_DO_TEXTO:
        texto = texto[:TETO_DO_TEXTO] + "\n\n[ANEXOS TRUNCADOS — o conteúdo acima cobre o início dos arquivos]"
        resultado.avisos.append("Os arquivos eram longos demais para ler inteiros; li o começo de cada um.")
    resultado.texto = texto

    contagem: Dict[str, int] = {}
    for item in resultado.lidos:
        chave = f"{item['tipo']}:{'ok' if item['lido'] else 'aviso'}"
        contagem[chave] = contagem.get(chave, 0) + 1
    logger.info("[ANEXOS] %d anexo(s) · %s", len(resultado.lidos), contagem)
    return resultado

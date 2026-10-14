"""F1 — Visão e documentos GLOBAIS (SPEC em docs/canon; pedido central do founder).

Qualquer agente (Chat Principal, atendente externo, auxiliares) passa a:
- VER imagens: `describe_image` gera contexto visual com o modelo da ROTA do
  papel `visao` (SPEC-116) — nunca mais "não consigo visualizar".
- LER documentos (PDF/DOCX...): `conteudo_do_anexo` passa o anexo pelo LEITOR
  do produto (SPEC-130-B) e devolve a ficha MASCARADA — ou, se não for de
  seguro, o texto MASCARADO e truncado (docling → páginas do PDF).

Fail-safe em tudo: sem chave/modelo/parse → None e o fluxo segue só com texto.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 🔴 SPEC-116 U8 (F3a) — A VISÃO PEDE UM PAPEL, NÃO UM MODELO.
#
# 📊 23/09/2026 (EVIDENCIAS/01 F2): toda foto do segurado era lida por
# `gpt-4o-mini`, qualquer que fosse o agente — `webhook.py` chamava
# `describe_image` sem agente e aqui morava o default literal; o fallback era
# o Claude 3.5 Sonnet RETIRADO (404 desde 28/10/2025); e `temperature=0.3` ia a
# `ChatAnthropic` — Claude 5 devolve 400 e o agente ficava cego calado.
#
# Agora: `LLMFactory.create_llm(..., papel="visao")`. Quem decide o modelo é a
# ROTA do papel (`llm_papeis`, D-116-17: a rota vence o `vision_model` do
# agente); o `vision_model` gravado vale só se o papel ficar SEM rota, e só se
# estiver no catálogo. Sampling segue o catálogo (a fábrica tira `temperature`
# de quem a recusa). Gemini entra pelo ramo `google` da fábrica; modelo fora do
# catálogo ou sem adaptador é `ModeloNaoResolvido` — erro EXPLÍCITO no log,
# nunca um mini por omissão. Toda chamada entra no ledger (service_type=vision,
# com papel · pedido · resolvido).

#: A marca que o texto do turno leva quando a imagem JÁ foi descrita. O webhook
#: descreve a foto do segurado antes do grafo e grava esta marca no texto;
#: `process_message` a encontra e NÃO descreve de novo (📊 23/09/2026: 2
#: chamadas de visão por foto e o contexto visual DUPLICADO no prompt).
MARCA_DO_CONTEXTO_VISUAL = "[CONTEXTO VISUAL"

TEMPERATURA_DA_VISAO = 0.3

_SUPPORTED_DOC_EXTENSIONS = (".pdf", ".docx", ".pptx", ".xlsx", ".html", ".md", ".txt", ".csv")

_MAX_DOC_CHARS = 20000


def imagem_ja_descrita(texto: Optional[str]) -> bool:
    """O texto do turno já carrega a descrição da imagem (a marca do webhook)?"""
    return MARCA_DO_CONTEXTO_VISUAL in str(texto or "")


def criar_llm_de_visao(
    *,
    company_id: Optional[str],
    agent_id: Optional[str] = None,
    agent_data: Optional[Dict[str, Any]] = None,
    temperature: float = TEMPERATURA_DA_VISAO,
):
    """O modelo do papel `visao`, construído PELA FÁBRICA (ledger incluso).

    ⛔ Levanta `ModeloNaoResolvido` (papel sem rota e sem modelo governado) ou
    `ValueError` (chave ausente) — nunca devolve um modelo por omissão.
    """
    from app.factories.llm_factory import LLMFactory

    pedido = str((agent_data or {}).get("vision_model") or "").strip() or None
    return LLMFactory.create_llm(
        {},
        {"llm_model": pedido, "llm_temperature": temperature},
        company_id=str(company_id) if company_id else None,
        agent_id=str(agent_id) if agent_id else None,
        service_type="vision",
        papel="visao",
    )


def truncate_document_text(text: str, max_chars: int = _MAX_DOC_CHARS) -> str:
    t = str(text or "")
    if len(t) <= max_chars:
        return t
    return t[:max_chars] + "\n\n[DOCUMENTO TRUNCADO — conteúdo acima cobre o início do arquivo]"


def is_supported_document(file_name: str) -> bool:
    # a URL assinada traz `?token=…` depois da extensão
    return str(file_name or "").split("?")[0].lower().endswith(_SUPPORTED_DOC_EXTENSIONS)


def data_url_da_imagem(dados: bytes, mime: str = "image/jpeg") -> str:
    """Os BYTES da imagem como `data:<mime>;base64,…` — a forma que vai ao provedor (SPEC-132-A D-132A-05)."""
    import base64

    tipo = str(mime or "image/jpeg").split(";")[0].strip().lower() or "image/jpeg"
    return f"data:{tipo};base64,{base64.b64encode(bytes(dados)).decode('ascii')}"


def _imagem_que_o_provedor_alcanca(image_url: str) -> bool:
    """Só `data:image/…` ou `http(s)://…` vão ao provedor.

    📊 SPEC-132-A B4 (14/10/2026): o chat passava `/api/storage/<bucket>/<path>` — RELATIVO e atrás da sessão — e o
    provedor nunca o alcançava (uma chamada paga para nada). Agora o chat manda os BYTES (data URL, `chat_anexos`);
    um caminho relativo é recusado aqui, antes da chamada.
    """
    u = str(image_url or "").strip().lower()
    return u.startswith("data:image/") or u.startswith("https://") or u.startswith("http://")


async def describe_image(
    image_url: Optional[str] = None,
    *,
    company_id: str,
    agent_id: Optional[str] = None,
    agent_data: Optional[Dict[str, Any]] = None,
    purpose_hint: str = "Agente de Suporte",
    llm=None,
    image_bytes: Optional[bytes] = None,
    mime: str = "image/jpeg",
) -> Optional[str]:
    """Analisa a imagem e devolve descrição técnica p/ virar contexto do agente.

    Modelo: papel `visao` pela fábrica (ver o topo do módulo). `llm=` é o PONTO
    DE INJEÇÃO da bancada (SPEC-116 F5b) e dos testes: quando vem, é usado como
    está. Falha → None (o fluxo segue só com o texto), com o motivo no log.

    SPEC-132-A: `image_bytes=` (+ `mime=`) manda a imagem como data URL — o provedor nunca recebe URL nossa.
    `image_url` pode ser um data URL pronto; caminho relativo (`/api/storage/…`) é recusado (None).
    """
    if image_bytes:
        image_url = data_url_da_imagem(image_bytes, mime)
    if not image_url:
        return None
    if not _imagem_que_o_provedor_alcanca(image_url):
        logger.error("[VISION] describe_image: a imagem não é data URL nem http(s) — o provedor não a alcança")
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        modelo = llm if llm is not None else criar_llm_de_visao(
            company_id=company_id, agent_id=agent_id, agent_data=agent_data)
        result = await modelo.ainvoke([
            SystemMessage(content=(
                f"Descreva a imagem para um {purpose_hint} de corretora de seguros. "
                "Seja objetivo e completo: o que aparece, textos legíveis, números, danos visíveis, "
                "documentos identificáveis. Sem opinião, só o que está na imagem."
            )),
            HumanMessage(content=[
                {"type": "text", "text": "Descreva:"},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]),
        ])
        content = _texto_da_resposta(getattr(result, "content", None))
        return content or None
    except Exception as e:  # noqa: BLE001
        # ⛔ Nunca o conteúdo da imagem nem a URL no log — só o motivo.
        from app.factories.model_policy import ModeloNaoResolvido

        if isinstance(e, ModeloNaoResolvido):
            logger.error("[VISION] papel 'visao' sem modelo governado: %s", e)
        else:
            logger.error(f"[VISION] describe_image falhou: {type(e).__name__}")
        return None


def _texto_da_resposta(content: Any) -> str:
    """O texto da resposta — Claude 5 com raciocínio devolve LISTA de blocos."""
    if isinstance(content, list):
        partes = []
        for bloco in content:
            if isinstance(bloco, dict):
                if bloco.get("type") in (None, "text"):
                    partes.append(str(bloco.get("text") or ""))
            else:
                partes.append(str(bloco))
        content = "".join(partes)
    return str(content or "").strip()


# 🔴 SPEC-130-B F3 — O ANEXO PASSA PELO LEITOR DO PRODUTO, E AO MODELO VAI A FICHA MASCARADA.
#
# 📊 11/10/2026 (BLOCO 0 da F3): o PDF que o segurado mandava no WhatsApp ia CRU ao modelo — até 20.000
# caracteres, sem máscara de CPF (`grep -n -i "cpf\|mascar" vision_service.py` → 0) — e 2 de 6 documentos
# recebidos "não foi possível ler" (P-LEITOR-03). Agora:
#   · documento de SEGURO (apólice · proposta · endosso · cotação · CRLV) → `ler_anexo_de_seguro` (o MESMO leitor do
#     `/documento` do CORP, em memória) e ao modelo vai `ficha_para_o_modelo` — MASCARADA. O SEGURADO recebe só a
#     ficha; o CORRETOR, a ficha + o texto mascarado (ele pergunta de cláusula — D-130B-05);
#   · qualquer outro documento → o texto de sempre, agora MASCARADO e truncado;
#   · leitura que falha → `None` (quem chama diz "não consegui ler, reenvie").
# ⛔ O leitor e a máscara são da F1 (`policy_document_evidence_service`). Aqui não mora regex de CPF nenhum: sem a
#    máscara do leitor, o texto NÃO sai (fail-closed) — nunca um "melhor que nada" cru (CLAUDE.md §5 e §7).

#: Os tipos que o leitor devolve em `leitura.tipo_documento` e que fazem do anexo um documento DE SEGURO.
#: Comparados sem acento e em minúsculas ("Cotação" == "cotacao").
TIPOS_DE_DOCUMENTO_DE_SEGURO = frozenset({"apolice", "proposta", "endosso", "cotacao", "crlv"})

#: Quanto o leitor pode levar no anexo (o degrau do modelo que estoura SEGUE em 2º plano — D-130B-08).
ORCAMENTO_PADRAO_DA_LEITURA_S = 40.0
#: Folga do relógio de FORA sobre o orçamento: o leitor que travar não segura o webhook para sempre.
FOLGA_DO_RELOGIO_S = 20.0

_TIMEOUT_DO_DOWNLOAD_S = 45.0


def orcamento_da_leitura_s() -> float:
    """`ANEXO_LEITURA_ORCAMENTO_S` (padrão 40). Valor inválido ou ≤ 0 → o padrão."""
    try:
        valor = float(str(os.getenv("ANEXO_LEITURA_ORCAMENTO_S") or "").strip() or ORCAMENTO_PADRAO_DA_LEITURA_S)
    except ValueError:
        return ORCAMENTO_PADRAO_DA_LEITURA_S
    return valor if valor > 0 else ORCAMENTO_PADRAO_DA_LEITURA_S


def _sem_acento_minusculo(valor: Any) -> str:
    import unicodedata

    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).strip().lower()


def tipo_do_documento_lido(resultado: Any) -> str:
    """O `tipo_documento` que o leitor devolveu (na `leitura`, ou na raiz), normalizado. Vazio = sem tipo."""
    if not isinstance(resultado, dict):
        return ""
    leitura = resultado.get("leitura") if isinstance(resultado.get("leitura"), dict) else {}
    return _sem_acento_minusculo(leitura.get("tipo_documento") or resultado.get("tipo_documento"))


def e_documento_de_seguro(resultado: Any) -> bool:
    return tipo_do_documento_lido(resultado) in TIPOS_DE_DOCUMENTO_DE_SEGURO


def _e_pdf(file_bytes: bytes, file_name: str) -> bool:
    return bytes(file_bytes[:5]) == b"%PDF-" or str(file_name or "").split("?")[0].lower().endswith(".pdf")


def mascarar(texto: Optional[str]) -> Optional[str]:
    """A máscara do LEITOR (`mascarar_texto_de_apolice`, F1). Sem ela → `None`: o texto não sai (fail-closed)."""
    try:
        from app.services.policy_document_evidence_service import mascarar_texto_de_apolice
    except Exception as e:  # noqa: BLE001 — ImportError enquanto a F1 não chegou, ou módulo quebrado
        logger.error("[VISION] máscara do leitor indisponível (%s) — o texto do documento NÃO vai ao modelo",
                     type(e).__name__)
        return None
    try:
        return str(mascarar_texto_de_apolice(str(texto or "")))
    except Exception as e:  # noqa: BLE001
        logger.error("[VISION] máscara do leitor falhou (%s) — o texto do documento NÃO vai ao modelo",
                     type(e).__name__)
        return None


_MARCADOR_DA_MASCARA = re.compile(r"\[([A-Z]{2,12})\]")


def nome_do_anexo_para_o_modelo(nome: Any, *, padrao: str = "documento") -> str:
    """O NOME do arquivo como pode ir no TEXTO do turno (SPEC-130-B F5 · C4).

    📊 A F3 achou: o nome do anexo ia CRU ao modelo dentro de `MARCA_DO_DOCUMENTO` /
    `CABECALHO_DO_DOCUMENTO` (webhook) e de `[DOCUMENTO ANEXADO: …]` (chat) — e o segurado
    nomeia arquivo com o próprio CPF ("rg 123.456.789-09.pdf"). Passa pela máscara do LEITOR.
    ⚠️ Os marcadores `[CPF]` viram `<CPF>`: o nome mora DENTRO de uma marca entre colchetes, e
    `webhook.nome_do_documento` recorta a marca até o primeiro `]` — um `]` no meio cortaria o nome.
    ⛔ Máscara indisponível → o `padrao`, nunca o nome cru (fail-closed). O CAMPO
    `documento_payload["fileName"]` não passa por aqui: ele não vai ao modelo (só ao classificador)."""
    bruto = " ".join(str(nome or "").replace("[", "(").replace("]", ")").split())
    if not bruto:
        return padrao
    mascarado = mascarar(bruto)
    if mascarado is None:
        return padrao
    return _MARCADOR_DA_MASCARA.sub(r"<\1>", mascarado)[:160] or padrao


async def baixar_documento(file_url: str) -> Optional[bytes]:
    """Os BYTES do documento (o download de sempre). Falha ou vazio → `None`. ⛔ Nunca a URL no log."""
    if not file_url:
        return None
    try:
        import httpx
        from urllib.parse import urlsplit

        from app.core import settings

        # 🔴 SPEC-132-A (red team P5, SSRF): só o host do NOSSO Supabase Storage, em https, sem seguir redirecionamento.
        alvo, nosso = urlsplit(str(file_url)), urlsplit(str(getattr(settings, "SUPABASE_URL", "") or ""))
        if alvo.scheme != "https" or not alvo.hostname or alvo.hostname != nosso.hostname or alvo.port != nosso.port:
            logger.warning("[VISION] baixar_documento recusou um endereço fora do Storage da plataforma")
            return None
        async with httpx.AsyncClient(timeout=_TIMEOUT_DO_DOWNLOAD_S, follow_redirects=False) as client:
            res = await client.get(file_url)
            res.raise_for_status()
            data = res.content
        return bytes(data) if data else None
    except Exception as e:  # noqa: BLE001
        logger.error(f"[VISION] baixar_documento falhou: {type(e).__name__}")
        return None


def _paginas_do_pdf_em_texto(data: bytes) -> str:
    """O texto do PDF página a página: as páginas TOLERANTES do leitor (F1) quando existem; senão o PyPDF2 de sempre."""
    try:
        from app.services import document_service as _ds

        tolerante = getattr(_ds, "extrair_paginas_tolerante", None)
    except Exception:  # noqa: BLE001
        tolerante = None
    if callable(tolerante):
        try:
            pages, _parser, _total = tolerante(data)
            blocos = []
            for i, page in enumerate(list(pages or [])[:40]):
                texto = str((page or {}).get("content") or (page or {}).get("text") or "") if isinstance(page, dict) \
                    else str(page or "")
                numero = (page.get("page_number") if isinstance(page, dict) else None) or i + 1
                blocos.append(f"[página {numero}]\n{texto}")
            return "\n\n".join(blocos)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[VISION] páginas tolerantes falharam ({type(e).__name__}) — PyPDF2")
    from io import BytesIO

    from PyPDF2 import PdfReader

    reader = PdfReader(BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages[:40]):
        try:
            pages.append(f"[página {i + 1}]\n{page.extract_text() or ''}")
        except Exception:  # noqa: BLE001
            continue
    return "\n\n".join(pages)


def _texto_bruto_do_documento(data: bytes, file_name: str) -> str:
    """docling (o parser da KB) → páginas do PDF. Texto puro dispensa parser. ⚠️ CRU: só sai daqui pela máscara."""
    suffix = os.path.splitext(str(file_name or "").split("?")[0])[1].lower() or ".pdf"
    if suffix in (".txt", ".csv", ".md"):
        return data.decode("utf-8", errors="replace")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            from app.services.sanitization_service import SanitizationService

            markdown, _meta = SanitizationService()._docling_parse(tmp_path, extract_images=False)  # noqa: SLF001
            if markdown and markdown.strip():
                return markdown
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[VISION] docling indisponível ({type(e).__name__}) — fallback local")
        if suffix == ".pdf" or _e_pdf(data, file_name):
            return _paginas_do_pdf_em_texto(data)
        return ""
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


async def texto_mascarado_do_documento(data: Optional[bytes], file_name: str = "") -> Optional[str]:
    """O texto do documento, MASCARADO e truncado. Sem texto, sem máscara ou erro → `None`."""
    if not data:
        return None
    import asyncio

    try:
        bruto = await asyncio.to_thread(_texto_bruto_do_documento, data, file_name)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[VISION] extração do documento falhou: {type(e).__name__}")
        return None
    if not str(bruto or "").strip():
        return None
    mascarado = mascarar(bruto)
    if not mascarado or not mascarado.strip():
        return None
    return truncate_document_text(mascarado)


async def extract_document_text(file_url: str, file_name: str = "") -> Optional[str]:
    """Baixa o documento e devolve o texto MASCARADO e truncado, ou None (fail-safe).

    ⚠️ Desde a SPEC-130-B nenhum caminho do produto chama esta função (webhook e chat passam por `conteudo_do_anexo`);
    ela fica para quem só tem a URL — e devolve texto MASCARADO, nunca cru."""
    if not file_url or not is_supported_document(file_name or file_url):
        return None
    data = await baixar_documento(file_url)
    return await texto_mascarado_do_documento(data, file_name or file_url)


def _ficha_ja_traz_o_texto(ficha: str) -> bool:
    """A ficha do CORRETOR da F1 já carrega o texto mascarado? (o marcador que ela escreve)."""
    return any(m in ficha for m in _MARCADORES_DO_TEXTO_NA_FICHA)


#: O que a `ficha_para_o_modelo(audiencia="corretor")` da F1 escreve antes do texto mascarado.
_MARCADORES_DO_TEXTO_NA_FICHA = ("[TEXTO DO DOCUMENTO",)

CABECALHO_DO_TEXTO_DO_CORRETOR = "[TEXTO DO DOCUMENTO (mascarado)]"


async def conteudo_do_anexo(
    file_bytes: Optional[bytes],
    file_name: str,
    *,
    company_id: str,
    audiencia: str,
    orcamento_s: Optional[float] = None,
) -> Optional[str]:
    """O que o MODELO lê de um anexo — o elo `ler_anexo_de_seguro → ficha_para_o_modelo` do fio (SPEC-130-B §2).

    · de seguro → a ficha MASCARADA (corretor: + o texto mascarado) · outro → o texto MASCARADO e truncado ·
    · a leitura falhou (exceção, `None`, ficha vazia) ou o tipo não é suportado → `None`.
    ⛔ Nunca o conteúdo, a URL ou o nome do arquivo no log — só o motivo.
    """
    if not file_bytes:
        return None
    if audiencia not in ("segurado", "corretor"):
        raise ValueError("audiencia deve ser 'segurado' ou 'corretor'")
    if not _e_pdf(file_bytes, file_name):
        # DOCX/TXT/… não são lidos pelo leitor de apólice: o texto de sempre, mascarado.
        if not is_supported_document(file_name):
            return None
        return await texto_mascarado_do_documento(file_bytes, file_name)

    import asyncio

    orcamento = float(orcamento_s) if orcamento_s and orcamento_s > 0 else orcamento_da_leitura_s()
    try:
        from app.services import policy_document_evidence_service as _leitor

        ler = getattr(_leitor, "ler_anexo_de_seguro")
        ficha_de = getattr(_leitor, "ficha_para_o_modelo")
    except Exception as e:  # noqa: BLE001
        logger.error("[VISION] leitor de anexo indisponível (%s)", type(e).__name__)
        return None
    try:
        resultado = await asyncio.wait_for(
            ler(file_bytes, file_name, company_id=company_id, orcamento_s=orcamento),
            timeout=orcamento + FOLGA_DO_RELOGIO_S,
        )
    except Exception as e:  # noqa: BLE001 — inclui o relógio de fora (TimeoutError)
        logger.error("[VISION] leitura do anexo falhou (%s)", type(e).__name__)
        return None
    if not isinstance(resultado, dict):
        return None

    async def _texto_mascarado() -> Optional[str]:
        # o `texto_mascarado` que o LEITOR já devolve (páginas tolerantes + a máscara dele); sem ele, o parser de
        # sempre (docling → páginas), também pela máscara do leitor
        pronto = str(resultado.get("texto_mascarado") or "")
        if pronto.strip():
            return truncate_document_text(pronto)
        return await texto_mascarado_do_documento(file_bytes, file_name)

    if not e_documento_de_seguro(resultado):
        return await _texto_mascarado()

    try:
        ficha = str(ficha_de(resultado, audiencia=audiencia) or "")
    except Exception as e:  # noqa: BLE001
        logger.error("[VISION] ficha do anexo falhou (%s)", type(e).__name__)
        return None
    if not ficha.strip():
        return None
    if audiencia == "corretor" and not _ficha_ja_traz_o_texto(ficha):
        texto = await _texto_mascarado()
        if texto:
            ficha = f"{ficha}\n\n{CABECALHO_DO_TEXTO_DO_CORRETOR}\n{texto}"
    return truncate_document_text(ficha)

"""O arquivo do acervo normativo. SPEC-067 LOTE 0, item 4.

O problema, medido
------------------
📊 08/08/2026: `normative_document_versions.storage_ref` está preenchido em
**0 de 29**. O PDF é baixado, lido em memória e descartado — a variável com os
bytes morre no fim de `insurance_corpus._baixar_pdf_direto`. O texto extraído é
picado e vai para o Qdrant; inteiro, ele não é gravado em lugar nenhum.

    O texto-fonte do acervo existe hoje em um único lugar: dentro do Qdrant,
    picado em 11.409 pedaços.

Isso inverte o CLAUDE.md §6, que declara o Qdrant "índice derivado e
reconstruível". Um índice que é o original não é reconstruível — e não é
reprocessável, que é o que o LOTE 0 inteiro precisa que ele seja: trocar PyPDF2
por PyMuPDF (item 1), montar cabeçalho por pedaço (item 2) e cortar por seção
(item 3) só valem para o acervo EXISTENTE se houver de onde reprocessar.

📊 E a janela está fechando: a URL da HDI devolve 500 e a da Allianz, 403.
Documento que baixou ontem já não baixa hoje.

O que este módulo NÃO é
-----------------------
Não é um serviço de storage. É uma fina camada de nomes sobre o `MinioService`
que já existe — mesma instância, mesmo bucket, mesmo cliente. Um segundo
caminho para bytes significaria dois lugares onde procurar um arquivo perdido.

Onde as coisas ficam
--------------------
    acervo-normativo/<document_id>/v<n>/original.pdf
    acervo-normativo/<document_id>/v<n>/texto.txt

⚠️ `acervo-normativo` ocupa a posição que nos caminhos de corretora é o
`company_id`, e **de propósito não se parece com um uuid**. O acervo normativo
não tem dono (D-Acervo-01): é global, a serviço de todas as corretoras. Um
prefixo que fosse um uuid válido convidaria alguém a tratá-lo como tenant, e
material sem dono num caminho de tenant é como conteúdo global vaza para dentro
de uma corretora — ou como o de uma corretora vaza para fora.

A falha é registrada, nunca levantada
-------------------------------------
Arquivar é trabalho de guarda, não de entrega. Se o MinIO estiver fora do ar, o
documento ainda tem de ser indexado — perder a ingestão inteira porque o
arquivo morto falhou seria trocar um problema por um pior. Mas a falha **fica
visível**: `arquivado_em` continua NULL e o motivo vai para o log e para o
dicionário devolvido. 📊 A lição de 05/08 (23 documentos presos oito dias) foi
que `except` que engole o motivo transforma erro de digitação em silêncio.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# O prefixo do acervo sem dono. Não é um company_id e não deve virar um.
PREFIXO = "acervo-normativo"

ORIGINAL = "original.pdf"
TEXTO = "texto.txt"


def caminho(documento_id: str, versao: int, arquivo: str) -> str:
    """O endereço de uma peça de uma versão. Uma função só monta caminho.

    Ter isto numa função em vez de espalhado em f-strings é o que permite que o
    leitor (reprocessamento) e o escritor (ingestão) nunca discordem sobre onde
    o arquivo está.
    """
    return f"{PREFIXO}/{documento_id}/v{int(versao)}/{arquivo}"


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def guardar_versao(
    documento_id: str,
    versao: int,
    *,
    texto: str,
    pdf_bytes: Optional[bytes] = None,
    media_type: Optional[str] = None,
    minio: Any = None,
) -> dict:
    """Guarda o original e o texto de uma versão. Devolve os ponteiros.

    `pdf_bytes` é opcional porque nem toda origem é PDF: documento lido pelo
    crawler chega como markdown e não tem arquivo original. Nesse caso só o
    texto é guardado, e `storage_ref` fica NULL — que é a verdade, e é
    diferente de "falhou".

    Nunca levanta. As chaves de falha vão em `erros`, e quem chama decide o que
    fazer com elas (hoje: registrar e seguir).
    """
    saida: dict[str, Any] = {
        "storage_ref": None,
        "text_storage_ref": None,
        "source_bytes": len(pdf_bytes) if pdf_bytes else None,
        "source_media_type": media_type,
        "arquivado_em": None,
        "erros": {},
    }

    if minio is None:
        try:
            from ..minio_service import get_minio_service

            minio = get_minio_service()
        except Exception as exc:  # noqa: BLE001
            # O tipo E a mensagem. §9.2 do CLAUDE.md: erro lido na fonte.
            saida["erros"]["minio"] = f"{type(exc).__name__}: {exc}"
            logger.warning("[acervo] MinIO indisponivel — versao %s v%s NAO foi "
                           "arquivada: %s: %s", documento_id, versao,
                           type(exc).__name__, exc)
            return saida

    if pdf_bytes:
        alvo = caminho(documento_id, versao, ORIGINAL)
        try:
            saida["storage_ref"] = minio.put_bytes(
                alvo, pdf_bytes, media_type or "application/pdf")
            saida["source_media_type"] = media_type or "application/pdf"
        except Exception as exc:  # noqa: BLE001
            saida["erros"]["original"] = f"{type(exc).__name__}: {exc}"
            logger.warning("[acervo] original nao guardado (%s): %s: %s",
                           alvo, type(exc).__name__, exc)

    if texto:
        alvo = caminho(documento_id, versao, TEXTO)
        try:
            saida["text_storage_ref"] = minio.put_bytes(
                alvo, texto.encode("utf-8"), "text/plain; charset=utf-8")
        except Exception as exc:  # noqa: BLE001
            saida["erros"]["texto"] = f"{type(exc).__name__}: {exc}"
            logger.warning("[acervo] texto nao guardado (%s): %s: %s",
                           alvo, type(exc).__name__, exc)

    # `arquivado_em` só existe se alguma coisa realmente foi guardada. Marcar a
    # data numa tentativa que falhou faria a fila de reprocessamento
    # (`normative_versao_sem_arquivo_idx`) parecer resolvida.
    if saida["storage_ref"] or saida["text_storage_ref"]:
        saida["arquivado_em"] = _agora().isoformat()

    return saida


def ler_texto(documento_id: str, versao: int, *, minio: Any = None) -> Optional[str]:
    """Devolve o texto guardado de uma versão, ou None.

    É a metade que dá sentido à outra: guardar sem saber ler é gastar disco. É
    por aqui que o reprocessamento do LOTE 0 (PyMuPDF, cabeçalho por pedaço,
    corte por seção) alcança os documentos cuja URL de origem já morreu.
    """
    if minio is None:
        try:
            from ..minio_service import get_minio_service

            minio = get_minio_service()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[acervo] MinIO indisponivel na leitura: %s: %s",
                           type(exc).__name__, exc)
            return None
    try:
        dados = minio.download_file(caminho(documento_id, versao, TEXTO))
        return dados.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.info("[acervo] sem texto guardado para %s v%s (%s)",
                    documento_id, versao, type(exc).__name__)
        return None

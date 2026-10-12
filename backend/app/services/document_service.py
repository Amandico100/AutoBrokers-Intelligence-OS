"""
Document Service - Processamento de documentos (extração de texto)
VERSÃO CORRIGIDA: Suporte a filtro por agent_id
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, BinaryIO, Dict, List, Optional, Tuple

# Processamento de arquivos
import PyPDF2
from docx import Document as DocxDocument

from ..core.database import get_supabase_client

# Services
from .minio_service import get_minio_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SPEC-130-B U2 (P-LEITOR-02) — as PÁGINAS TOLERANTES
# ---------------------------------------------------------------------------
#: O que cada página do PDF entregou. ⛔ Não é decoração: é o que diz à leitura
#: quais páginas só a VISÃO pode ler (`sem_texto`).
PARSER_PYPDF2 = "pypdf2"
PARSER_PYMUPDF = "pymupdf"
PARSER_SEM_TEXTO = "sem_texto"


def _pymupdf_aberto(file_bytes: bytes) -> Any:
    """O documento aberto no PyMuPDF, ou `None` (sem a biblioteca, ou PDF ilegível)."""
    try:
        import fitz  # PyMuPDF — já está no requirements (docling/portal)

        return fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[DocumentService] PyMuPDF indisponível para este PDF: %s", type(exc).__name__)
        return None


def extrair_paginas_tolerante(
    file_bytes: bytes,
) -> Tuple[List[Dict[str, Any]], Dict[str, str], int]:
    """`(pages, parser_por_pagina, total_paginas)` — o PDF lido página a página.

    🔴 **PyPDF2 POR PÁGINA, e PyMuPDF só na página em que ele falha.** O PyPDF2 é
    o DIALETO do regex (CLAUDE.md §9.4): 📊 BLOCO 0 da SPEC-130-B — trocar o
    extrator inteiro pelo PyMuPDF derruba a apólice de controle de 18 para 0
    linhas, porque o espaçamento das colunas muda. Mas o PyPDF2 lança exceção
    numa página e, até aqui, a exceção derrubava o PDF INTEIRO: 📊 a Sura teve
    19/19 páginas com erro e a Yelum 4/4. Agora a página que falha (ou volta
    vazia) é relida pelo PyMuPDF; a que não tem texto em nenhum dos dois é
    `sem_texto` — e só ela pode ir à visão.

    `pages` mantém a forma de sempre: só as páginas com texto, com o
    `page_number` REAL (1-based). ⛔ PDF que nenhum dos dois abre → exceção,
    como antes.
    """
    dados = bytes(file_bytes or b"")
    leitor = None
    try:
        leitor = PyPDF2.PdfReader(BytesIO(dados))
        total = len(leitor.pages)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[DocumentService] PyPDF2 não abriu o PDF: %s", type(exc).__name__)
        leitor = None
        total = 0

    reserva: Any = None
    if leitor is None:
        reserva = _pymupdf_aberto(dados)
        if reserva is None:
            raise ValueError("pdf_ilegivel: nem PyPDF2 nem PyMuPDF abriram o arquivo")
        total = int(reserva.page_count)

    pages: List[Dict[str, Any]] = []
    parser_por_pagina: Dict[str, str] = {}
    for indice in range(total):
        texto = ""
        if leitor is not None:
            try:
                texto = (leitor.pages[indice].extract_text() or "").strip()
            except Exception as exc:  # noqa: BLE001 — a página, não o PDF
                logger.warning("[DocumentService] PyPDF2 falhou na página %d: %s",
                               indice + 1, type(exc).__name__)
                texto = ""
        if texto:
            parser = PARSER_PYPDF2
        else:
            if reserva is None:
                reserva = _pymupdf_aberto(dados) or False
            texto = ""
            if reserva:
                try:
                    texto = (reserva[indice].get_text() or "").strip()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[DocumentService] PyMuPDF falhou na página %d: %s",
                                   indice + 1, type(exc).__name__)
                    texto = ""
            parser = PARSER_PYMUPDF if texto else PARSER_SEM_TEXTO
        parser_por_pagina[str(indice + 1)] = parser
        if texto:
            pages.append({"page_number": indice + 1, "content": texto, "text": texto})
    if reserva:
        try:
            reserva.close()
        except Exception:  # noqa: BLE001
            pass
    return pages, parser_por_pagina, total


#: O que pode morar em `documents.metadata` — lista FECHADA. ⛔ Nada de URL,
#: locator cru (codfil/nosnum), objeto do risco ou texto: a coluna é lida por
#: telas e relatórios; a ficha completa fica no MinIO, na pasta da corretora.
_CHAVES_DO_RESUMO = (
    "provider", "document_type", "source_document", "source_kind", "source_transport",
    "content_hash", "policy_locator_hash", "sensitivity", "scope", "parser_used",
    "parser_por_pagina", "total_paginas", "paginas_sem_texto", "created_at",
)


def _resumo_do_documento(policy_metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {k: policy_metadata[k] for k in _CHAVES_DO_RESUMO if policy_metadata.get(k) is not None}


def _caminho_da_leitura(company_id: str, document_id: str) -> str:
    """A FICHA da leitura mora ao lado do raw JSON — dentro da pasta da corretora."""
    return f"{company_id}/raw/{document_id}.leitura.json"


class DocumentService:
    """
    Serviço para upload e extração de texto de documentos
    Suporta: PDF, DOCX, TXT

    MULTI-AGENT: Documentos são vinculados a agent_id
    """

    def __init__(self):
        self.minio = get_minio_service()
        self.supabase = get_supabase_client().client

    def upload_document(
        self,
        file_data: BinaryIO,
        filename: str,
        company_id: str,
        file_size: int,
        content_type: str = "application/octet-stream",
        agent_id: Optional[str] = None,  # 🔥 Obrigatório para multi-agent
        scope: Optional[str] = None,  # SPEC-044: 'personal' = doc do usuário
        owner_user_id: Optional[str] = None,  # SPEC-044: dono (scope=personal)
    ) -> Optional[str]:
        """
        Upload de documento -> Extração -> Save Raw JSON -> DB Insert
        """
        try:
            # 🔥 VALIDAÇÃO: agent_id obrigatório
            if not agent_id:
                raise ValueError("agent_id é obrigatório para upload de documentos")

            # Determinar tipo
            file_type = self._get_file_type(filename)
            if not file_type:
                logger.error(f"Tipo de arquivo não suportado: {filename}")
                return None

            document_id = str(uuid.uuid4())

            # Ler arquivo para memória
            file_content = file_data.read()
            file_bytes = BytesIO(file_content)

            # Upload do Arquivo Original para MinIO
            minio_path = self.minio.upload_file(
                file_data=BytesIO(file_content),
                company_id=company_id,
                document_id=document_id,
                filename=filename,
                content_type=content_type,
            )

            # Extrair Texto e Páginas
            text_content, pages = self.extract_text_internal(file_bytes, file_type)

            # SPEC-044: escopo pessoal — o metadata viaja até o payload do
            # Qdrant (extract_payload_extras lê scope/owner_user_id daqui).
            from .knowledge_scope import SCOPE_PERSONAL

            is_personal = scope == SCOPE_PERSONAL and bool(owner_user_id)

            # Salvar JSON Raw (Bronze Layer)
            raw_meta = {
                "filename": filename,
                "file_type": file_type,
                "file_size": file_size,
                "agent_id": agent_id,  # 🔥 Incluir nos metadados
                "uploaded_at": datetime.now().isoformat(),
            }
            if is_personal:
                raw_meta["scope"] = SCOPE_PERSONAL
                raw_meta["owner_user_id"] = str(owner_user_id)
            raw_data = {
                "text_content": text_content,
                "pages": pages,
                "metadata": raw_meta,
            }

            json_bytes = BytesIO(
                json.dumps(raw_data, ensure_ascii=False).encode("utf-8")
            )

            try:
                raw_object_name = f"{company_id}/raw/{document_id}.json"
                self.minio.client.put_object(
                    "documents",
                    raw_object_name,
                    json_bytes,
                    length=json_bytes.getbuffer().nbytes,
                    content_type="application/json",
                )
                logger.info(
                    f"JSON Raw salvo em: {raw_object_name} com {len(pages)} páginas"
                )
            except Exception as e:
                logger.error(f"Erro ao salvar JSON Raw: {e}")

            # Nome da collection do Qdrant
            qdrant_collection = f"company_{company_id.replace('-', '_')}"

            # Escopo de conhecimento (SPEC-003); default seguro tenant/agent.
            from .knowledge_scope import normalize_document_scope

            _doc_scope = SCOPE_PERSONAL if is_personal else normalize_document_scope(agent_id)

            # Criar registro no Banco
            _row = {
                "id": document_id,
                "company_id": company_id,
                "agent_id": agent_id,  # 🔥 Salva agent_id
                "scope": _doc_scope,
                "file_name": filename,
                "file_type": file_type,
                "file_size": file_size,
                "minio_path": minio_path,
                "qdrant_collection": qdrant_collection,
                "ingestion_strategy": "recursive",
                "status": "pending",
            }
            if is_personal:
                _row["owner_user_id"] = str(owner_user_id)
            result = self.supabase.table("documents").insert(_row).execute()

            if result.data:
                logger.info(f"Documento {document_id} criado para agent {agent_id}")
                return document_id
            return None

        except Exception as e:
            # Propaga o erro real para a rota (que retorna 500 com detail) — não engolir silenciosamente.
            logger.error(f"Erro ao fazer upload do documento: {e}", exc_info=True)
            raise

    def find_official_policy_document(
        self,
        company_id: str,
        policy_locator_hash: str,
        content_hash: Optional[str] = None,
        connection_id: str = "",
    ) -> Optional[dict]:
        """
        Locate a cached official policy PDF without exposing PolicyLocator values.

        Uses the existing documents table and a safe generated filename:
        infocap-policy-{policy_locator_hash}-{content_hash_prefix}.pdf
        e, quando a conexao e declarada,
        infocap-policy-{policy_locator_hash}-c{connection_hash}-{content_hash_prefix}.pdf

        🔴 SPEC-EXTRA-001.1 (conserto de 14/09/2026): `connection_id` entrou
        porque a corretora piloto tem 4 conexoes InfoCap e a leitura pela
        conexao B devolvia o PDF baixado pela conexao A. A composicao do nome
        mora em `policy_document_filename_prefix` — uma copia dela aqui seria
        um segundo motor (CLAUDE.md §5).
        """
        try:
            from .policy_document_evidence_service import policy_document_filename_prefix

            base = f"infocap-policy-{policy_locator_hash}-"
            prefix = policy_document_filename_prefix(policy_locator_hash, connection_id)
            query = (
                self.supabase.table("documents")
                .select("*")
                .eq("company_id", company_id)
                .eq("file_type", "pdf")
                .like("file_name", f"{prefix}%")
                .order("created_at", desc=True)
            )
            result = query.limit(10).execute()
            rows = result.data if result and result.data else []
            if not str(connection_id or "").strip():
                # ⚠️ Sem conexao declarada o prefixo e o BASE, e ele tambem casa
                # os arquivos de OUTRAS conexoes. O que os separa e o `-` extra
                # que so a forma com conexao tem depois do base.
                rows = [
                    row for row in rows
                    if "-" not in str(row.get("file_name") or "").removeprefix(base)
                ]
            if content_hash:
                rows = [
                    row for row in rows
                    if str(row.get("file_name") or "").startswith(
                        f"{prefix}{str(content_hash)[:16]}"
                    )
                ]
            if not rows:
                return None
            row = rows[0]
            row["policy_locator_hash"] = policy_locator_hash
            marker = str(row.get("file_name") or "").removeprefix(prefix)
            row["content_hash"] = marker.split(".", 1)[0]
            return row
        except Exception as e:
            logger.warning(f"[DocumentService] policy document cache lookup failed: {type(e).__name__}")
            return None

    def load_raw_pages(self, document_id: str, company_id: str) -> List[Dict[str, Any]]:
        """Load extracted pages from the existing raw JSON object in MinIO."""
        try:
            raw_path = f"{company_id}/raw/{document_id}.json"
            data = self.minio.download_file(raw_path)
            raw_data = json.load(data)
            pages = raw_data.get("pages")
            return pages if isinstance(pages, list) else []
        except Exception as e:
            logger.warning(f"[DocumentService] policy raw pages unavailable: {type(e).__name__}")
            return []

    # ----- SPEC-130-B U2: a LEITURA registrada --------------------------------
    def guardar_leitura(
        self,
        document_id: str,
        company_id: str,
        ficha: Dict[str, Any],
        resumo: Dict[str, Any],
    ) -> bool:
        """Grava a FICHA no MinIO e o RESUMO em `documents.metadata.leitura`.

        🔴 Isolamento (CLAUDE.md §7): o objeto mora em `{company_id}/raw/…` e o
        UPDATE filtra `id` **e** `company_id` — o service role ignora RLS, então
        o filtro no código é a trava. ⛔ `resumo` nunca leva `objeto_do_risco`.
        """
        if not document_id or not company_id:
            return False
        ok = True
        try:
            corpo = BytesIO(json.dumps(ficha, ensure_ascii=False, default=str).encode("utf-8"))
            self.minio.client.put_object(
                "documents",
                _caminho_da_leitura(company_id, document_id),
                corpo,
                length=corpo.getbuffer().nbytes,
                content_type="application/json",
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[DocumentService] ficha da leitura não gravada: {type(e).__name__}")
            ok = False
        try:
            resumo_limpo = {k: v for k, v in dict(resumo or {}).items() if k != "objeto_do_risco"}
            atual = (
                self.supabase.table("documents").select("metadata")
                .eq("id", document_id).eq("company_id", company_id).limit(1).execute()
            )
            linhas = atual.data if atual and atual.data else []
            if not linhas:
                return False
            metadata = dict(linhas[0].get("metadata") or {})
            metadata["leitura"] = resumo_limpo
            (
                self.supabase.table("documents").update({"metadata": metadata})
                .eq("id", document_id).eq("company_id", company_id).execute()
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[DocumentService] resumo da leitura não gravado: {type(e).__name__}")
            ok = False
        return ok

    def carregar_leitura(self, document_id: str, company_id: str) -> Optional[Dict[str, Any]]:
        """A FICHA guardada **desta corretora**, ou `None`.

        ⚠️ Além do caminho por `company_id`, a ficha carrega o `company_id` com
        que foi escrita, e ele é conferido: uma ficha que não é desta corretora
        não serve, mesmo que um caminho errado a tenha trazido.
        """
        if not document_id or not company_id:
            return None
        try:
            dados = json.load(self.minio.download_file(_caminho_da_leitura(company_id, document_id)))
        except Exception:  # noqa: BLE001 — ficha ausente é o caso normal do 1º acesso
            return None
        if not isinstance(dados, dict) or str(dados.get("company_id") or "") != str(company_id):
            return None
        return dados

    def carregar_pdf_original(self, documento: Dict[str, Any], company_id: str) -> Optional[bytes]:
        """Os BYTES do PDF guardado — só para a VISÃO ler as páginas sem texto."""
        try:
            if str((documento or {}).get("company_id") or "") != str(company_id):
                return None
            caminho = str((documento or {}).get("minio_path") or "")
            if not caminho:
                return None
            # `upload_file` grava `{company_id}/{document_id}/{arquivo}`: a pasta é a da corretora
            if not caminho.startswith(f"{company_id}/"):
                return None
            return self.minio.download_file(caminho).read()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[DocumentService] PDF original indisponível: {type(e).__name__}")
            return None

    def store_official_policy_document(
        self,
        *,
        file_data: bytes,
        filename: str,
        company_id: str,
        file_size: int,
        content_type: str,
        policy_metadata: Dict[str, Any],
        agent_id: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Store an official InfoCap policy PDF using the existing private document path.

        This intentionally does not persist the signed source URL. Policy identity
        travels only as hashes/metadata in the raw JSON and Qdrant payload.
        """
        try:
            document_id = str(uuid.uuid4())
            file_type = self._get_file_type(filename)
            if file_type != "pdf":
                raise ValueError("official policy documents must be PDF")

            minio_path = self.minio.upload_file(
                file_data=BytesIO(file_data),
                company_id=company_id,
                document_id=document_id,
                filename=filename,
                content_type=content_type or "application/pdf",
            )

            # 🔴 SPEC-130-B U2: as páginas TOLERANTES, e o que cada uma entregou.
            pages, parser_por_pagina, total_paginas = extrair_paginas_tolerante(bytes(file_data))
            text_content = "\n\n".join(page["content"] for page in pages).strip()
            paginas_sem_texto = sorted(
                int(n) for n, p in parser_por_pagina.items() if p == PARSER_SEM_TEXTO)
            # ⚠️ A extração VOLTA a quem chamou pelo mesmo dicionário de metadados
            #    (o retorno `(document_id, pages)` não muda: dublês e chamadores de
            #    antes continuam valendo). É assim que a leitura sabe quais páginas
            #    só a visão pode ler.
            if isinstance(policy_metadata, dict):
                policy_metadata["parser_por_pagina"] = dict(parser_por_pagina)
                policy_metadata["total_paginas"] = total_paginas
                policy_metadata["paginas_sem_texto"] = paginas_sem_texto
            from .knowledge_scope import SCOPE_CONNECTOR

            raw_data = {
                "text_content": text_content,
                "pages": pages,
                "metadata": {
                    "filename": filename,
                    "file_type": file_type,
                    "file_size": file_size,
                    "agent_id": agent_id,
                    "scope": SCOPE_CONNECTOR,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    **(policy_metadata or {}),
                    "parser_por_pagina": parser_por_pagina,
                    "total_paginas": total_paginas,
                    "paginas_sem_texto": paginas_sem_texto,
                },
            }
            raw_bytes = BytesIO(json.dumps(raw_data, ensure_ascii=False).encode("utf-8"))
            raw_object_name = f"{company_id}/raw/{document_id}.json"
            self.minio.client.put_object(
                "documents",
                raw_object_name,
                raw_bytes,
                length=raw_bytes.getbuffer().nbytes,
                content_type="application/json",
            )

            qdrant_collection = f"company_{company_id.replace('-', '_')}"
            result = (
                self.supabase.table("documents")
                .insert(
                    {
                        "id": document_id,
                        "company_id": company_id,
                        "agent_id": agent_id,
                        "scope": SCOPE_CONNECTOR,
                        "file_name": filename,
                        "file_type": file_type,
                        "file_size": file_size,
                        "minio_path": minio_path,
                        "qdrant_collection": qdrant_collection,
                        "ingestion_strategy": "page",
                        "ingestion_mode": "semantic",
                        "status": "pending",
                        # 🔴 SPEC-130-B: 📊 BLOCO 0 item 2 — os 21 PDFs do CORP
                        #    tinham `metadata` VAZIO. O resumo (sem PII, sem URL,
                        #    sem locator cru) passa a nascer com o documento.
                        "source_kind": str((policy_metadata or {}).get("source_kind") or "policy_pdf"),
                        "metadata": _resumo_do_documento(policy_metadata or {}),
                    }
                )
                .execute()
            )
            if not result.data:
                raise RuntimeError("documents insert returned no data")
            logger.info(
                "[DocumentService] official policy document stored company_hash=%s locator_hash=%s",
                hashlib.sha256(str(company_id).encode("utf-8")).hexdigest()[:12],
                (policy_metadata or {}).get("policy_locator_hash"),
            )
            return document_id, pages
        except Exception as e:
            logger.error(f"[DocumentService] failed to store official policy document: {e}", exc_info=True)
            raise

    def extract_text_internal(
        self, file_data: BytesIO, file_type: str
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extrai texto e estrutura de páginas.
        """
        file_data.seek(0)

        if file_type == "pdf":
            return self._extract_pdf_text(file_data)
        elif file_type == "docx":
            return self._extract_docx_text(file_data)
        elif file_type == "txt":
            return self._extract_txt_text(file_data)
        elif file_type == "md":
            return self._extract_txt_text(file_data)  # Markdown is plain text
        elif file_type == "csv":
            return self._extract_txt_text(file_data)  # CSV is plain text
        else:
            return "", []

    def extract_text(self, document_id: str) -> Optional[str]:
        """Método legado para compatibilidade"""
        try:
            doc = self.get_document(document_id)
            if doc:
                company_id = doc["company_id"]
                raw_path = f"{company_id}/raw/{document_id}.json"
                try:
                    data = self.minio.download_file(raw_path)
                    json_data = json.load(data)
                    return json_data.get("text_content", "")
                except Exception:
                    pass
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair texto: {e}")
            return None

    # ===== MÉTODOS PRIVADOS DE EXTRAÇÃO =====

    def _get_file_type(self, filename: str) -> Optional[str]:
        extension = filename.lower().split(".")[-1]
        if extension == "pdf":
            return "pdf"
        if extension in ["docx", "doc"]:
            return "docx"
        if extension == "txt":
            return "txt"
        if extension == "md":
            return "md"
        if extension == "csv":
            return "csv"
        return None

    def _extract_pdf_text(self, file_data: BytesIO) -> Tuple[str, List[Dict[str, Any]]]:
        """Extrai texto de PDF preservando paginação.

        🔴 SPEC-130-B: pelas PÁGINAS TOLERANTES — uma página que o PyPDF2 não lê
        não derruba mais o PDF inteiro. O retorno é o de sempre.
        """
        try:
            file_data.seek(0)
            pages, _parser, _total = extrair_paginas_tolerante(file_data.read())
            text = "\n\n".join(page["content"] for page in pages)
            return text.strip(), pages

        except Exception as e:
            logger.error(f"Erro ao extrair PDF: {e}")
            raise

    def _extract_docx_text(
        self, file_data: BytesIO
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Extrai texto de DOCX"""
        try:
            doc = DocxDocument(file_data)
            full_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            full_text = full_text.strip()

            pages = [{"page_number": 1, "content": full_text, "text": full_text}]

            return full_text, pages

        except Exception as e:
            logger.error(f"Erro ao extrair DOCX: {e}")
            raise

    def _extract_txt_text(self, file_data: BytesIO) -> Tuple[str, List[Dict[str, Any]]]:
        """Extrai TXT"""
        try:
            text = file_data.read().decode("utf-8").strip()
        except UnicodeDecodeError:
            file_data.seek(0)
            text = file_data.read().decode("latin-1").strip()

        pages = [{"page_number": 1, "content": text, "text": text}]

        return text, pages

    def update_document_status(
        self,
        document_id: str,
        status: str,
        chunks_count: int = 0,
        error_message: Optional[str] = None,
    ) -> bool:
        try:
            update_data = {"status": status, "chunks_count": chunks_count}

            if status == "completed":
                update_data["processed_at"] = datetime.now().isoformat()

            if error_message:
                update_data["error_message"] = error_message

            result = (
                self.supabase.table("documents")
                .update(update_data)
                .eq("id", document_id)
                .execute()
            )

            return bool(result.data)

        except Exception as e:
            logger.error(f"Erro ao atualizar status do documento: {e}")
            return False

    def get_document(self, document_id: str) -> Optional[dict]:
        try:
            result = (
                self.supabase.table("documents")
                .select("*")
                .eq("id", document_id)
                .execute()
            )
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar documento: {e}")
            return None

    def list_documents(
        self,
        company_id: str,
        agent_id: Optional[str] = None,  # 🔥 NOVO: Filtro por agente
        status: Optional[str] = None,
    ) -> list:
        """
        Lista documentos de uma empresa, opcionalmente filtrados por agente

        Args:
            company_id: ID da empresa
            agent_id: Filtrar por agente específico (opcional)
            status: Filtrar por status (opcional)
        """
        try:
            query = (
                self.supabase.table("documents")
                .select("*")
                .eq("company_id", company_id)
            )

            # 🔥 Filtro por agente
            if agent_id:
                query = query.eq("agent_id", agent_id)

            if status:
                query = query.eq("status", status)

            result = query.order("created_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Erro ao listar documentos: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        try:
            doc = self.get_document(document_id)
            if not doc:
                return False

            company_id = doc["company_id"]

            # Deletar do MinIO
            self.minio.delete_folder(company_id, document_id)

            # Deletar do banco
            self.supabase.table("documents").delete().eq("id", document_id).execute()
            logger.info(f"Documento {document_id} deletado")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar documento: {e}")
            return False

    def get_documents_by_agent(self, company_id: str, agent_id: str) -> list:
        """
        🔥 NOVO: Lista todos os documentos de um agente específico
        """
        return self.list_documents(company_id, agent_id=agent_id)

    def count_documents_by_agent(self, company_id: str, agent_id: str) -> int:
        """
        🔥 NOVO: Conta documentos de um agente
        """
        docs = self.list_documents(company_id, agent_id=agent_id)
        return len(docs)


# Singleton instance
_document_service: Optional[DocumentService] = None


def get_document_service() -> DocumentService:
    """Retorna instância singleton do DocumentService"""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
    return _document_service

"""Corpus normativo de seguros. SPEC-057 §Bloco H.

O problema
----------
Condição geral de apólice é o **mesmo documento** para todas as corretoras e
todos os segurados. Lê-la a cada pergunta custa crédito por leitura, demora
dezenas de segundos e — o pior — pode devolver respostas diferentes para
corretoras diferentes conforme o dia em que o PDF foi lido. Documento normativo
tem de dar a mesma resposta para todo mundo.

A forma
-------
Lê-se **uma vez**, no nível da plataforma, e o conteúdo entra no conhecimento
global que já existe. A partir daí toda corretora consulta de graça, pela
`knowledge.global.search` que já está no Registry. Um agente reconfere
periodicamente e, quando o conteúdo muda, registra uma versão nova.

Isto não é um RAG paralelo. A coleção Qdrant global, o serviço de ingestão e a
busca já existiam; o que faltava era o **catálogo** — o que está lá dentro, de
onde veio, de que versão e até quando vale.

O detalhe que impede isto de virar passivo
------------------------------------------
Uma apólice emitida em 2023 é regida pela condição vigente **na emissão**, não
pela de hoje. Um cache que guarda "a condição atual" e responde sobre uma
apólice antiga pode estar confiantemente errado sobre cobertura — e o corretor
repete isso para o cliente. Por isso toda resposta deste corpus carrega a
vigência junto, e o texto ingerido começa com ela.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

COLECAO_GLOBAL = "autobrokers_global"
MAX_TENTATIVAS = 4
INTERVALO_PADRAO_DIAS = 45

# Número de processo SUSEP: 5 dígitos . 6 dígitos / 4 dígitos - 2 dígitos.
# É a identidade legal do documento — duas versões da mesma norma compartilham
# o número, e é isso que permite encadear versões em vez de tratá-las como
# documentos diferentes.
_RE_SUSEP = re.compile(r"\b(\d{5}\.\d{6}/\d{4}-\d{2})\b")
_RE_PROCESSO_SOLTO = re.compile(
    r"processo\s+SUSEP\s*n?[º°.]?\s*([\d.\-/]{10,25})", re.I)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _hash(texto: str) -> str:
    # Normaliza espaço antes do hash: PDF re-renderizado muda quebra de linha
    # sem mudar uma vírgula do conteúdo, e isso geraria "mudou" toda semana.
    normalizado = re.sub(r"\s+", " ", texto or "").strip()
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def extrair_susep(texto: str) -> Optional[str]:
    m = _RE_SUSEP.search(texto or "")
    if m:
        return m.group(1)
    m = _RE_PROCESSO_SOLTO.search(texto or "")
    return m.group(1).strip() if m else None


def extrair_vigencia(texto: str) -> Optional[str]:
    """Procura uma data de vigência declarada no próprio documento."""
    padroes = [
        r"vig[êe]ncia\s+a\s+partir\s+de\s+(\d{2}/\d{2}/\d{4})",
        r"em\s+vigor\s+desde\s+(\d{2}/\d{2}/\d{4})",
        r"atualizad[ao]\s+em\s+(\d{2}/\d{2}/\d{4})",
    ]
    for p in padroes:
        m = re.search(p, texto or "", re.I)
        if m:
            try:
                d, mth, y = m.group(1).split("/")
                return f"{y}-{mth}-{d}"
            except Exception:  # noqa: BLE001
                continue
    return None


# Seguradoras que operam no Brasil, por domínio e por nome. Serve para dizer
# de quem é o documento a partir da URL ou do texto.
SEGURADORAS = {
    "porto": ("Porto Seguro", ("portoseguro.com", "porto.com.br", "porto seguro")),
    "allianz": ("Allianz Seguros", ("allianz.com.br", "allianz")),
    "bradesco": ("Bradesco Seguros", ("bradescoseguros.com", "bradesco seguros")),
    "sulamerica": ("SulAmérica", ("sulamerica.com", "sulamérica", "sulamerica")),
    "tokio": ("Tokio Marine", ("tokiomarine.com", "tokio marine", "tokio_marine")),
    "hdi": ("HDI Seguros", ("hdiseguros.com", "hdi seguros")),
    "mapfre": ("Mapfre", ("mapfre.com", "mapfre")),
    # Liberty Seguros virou Yelum em 2024. Documento antigo continua valendo e
    # continua hospedado no dominio antigo — as duas pistas apontam para a
    # mesma seguradora, senao a condicao geral de ontem vira orfa.
    # O dominio real e yelumseguros.com.br — "yelum.com.br" e so a marca e nao
    # resolve. Descoberto ao verificar as URLs de verdade; supor o dominio pelo
    # nome teria recusado todo documento legitimo da seguradora.
    "yelum": ("Yelum Seguradora", ("yelumseguros.com.br", "yelum",
                                   "libertyseguros.com", "liberty seguros")),
    "zurich": ("Zurich", ("zurich.com", "zurich")),
    "azul": ("Azul Seguros", ("azulseguros.com", "azul seguros")),
    "itau": ("Itaú Seguros", ("itau.com.br/seguros", "itaú seguros")),
    "suhai": ("Suhai Seguradora", ("suhaiseguradora.com", "suhai")),
    "aliro": ("Aliro Seguros", ("aliro.com.br", "aliro")),
    "susep": ("SUSEP", ("susep.gov.br", "gov.br/susep")),
    "cnseg": ("CNseg", ("cnseg.org.br",)),
}

RAMOS = {
    "auto": ("seguro auto", "automóvel", "automovel", "veículo", "veiculo", "casco"),
    "frota": ("frota",),
    "residencial": ("residencial", "residência", "residencia"),
    "vida": ("seguro de vida", "vida em grupo", "prestamista"),
    "previdencia": ("previdência", "previdencia", "pgbl", "vgbl"),
    "saude": ("saúde", "saude", "odontológico", "odontologico"),
    "empresarial": ("empresarial", "patrimonial", "riscos nomeados", "compreensivo"),
    "condominio": ("condomínio", "condominio"),
    "viagem": ("viagem",),
    "responsabilidade_civil": ("responsabilidade civil", "d&o", "e&o"),
    "engenharia": ("riscos de engenharia", "obras civis"),
    "garantia": ("seguro garantia", "fiança locatícia", "fianca locaticia"),
    "transporte": ("transporte", "carga", "rctr", "rctr-c"),
    "agro": ("agrícola", "agricola", "rural", "penhor rural"),
}

TIPOS = {
    "condicoes_gerais": ("condições gerais", "condicoes gerais", "condições-gerais"),
    "condicoes_especiais": ("condições especiais", "condicoes especiais"),
    "manual_do_segurado": ("manual do segurado", "guia do segurado", "cartilha"),
    "circular_susep": ("circular susep", "circular nº", "resolução cnsp", "resolucao cnsp"),
    "nota_tecnica": ("nota técnica atuarial", "nota tecnica atuarial"),
    "tabela_coberturas": ("tabela de coberturas", "quadro de coberturas"),
}


def classificar(titulo: str, texto: str, url: str) -> Optional[dict]:
    """Decide se um documento é normativo e de quem ele é.

    Devolve `None` para tudo que não se reconhece. Ser conservador aqui é
    deliberado: um falso negativo custa uma leitura a mais; um falso positivo
    injeta ruído no conhecimento que todas as corretoras consultam.
    """
    alvo = f"{titulo} {url} {(texto or '')[:6000]}".lower()

    doc_kind = None
    for chave, pistas in TIPOS.items():
        if any(p in alvo for p in pistas):
            doc_kind = chave
            break
    # Sem número de processo SUSEP e sem título normativo, não é norma.
    if not doc_kind:
        if extrair_susep(texto or ""):
            doc_kind = "condicoes_gerais"
        else:
            return None

    insurer_key = insurer_name = None
    for chave, (nome, pistas) in SEGURADORAS.items():
        if any(p in alvo for p in pistas):
            insurer_key, insurer_name = chave, nome
            break
    if not insurer_key:
        return None

    ramo = "geral"
    for chave, pistas in RAMOS.items():
        if any(p in alvo for p in pistas):
            ramo = chave
            break

    return {
        "insurer_key": insurer_key, "insurer_name": insurer_name,
        "product_line": ramo, "doc_kind": doc_kind,
        "titulo_sugerido": f"{doc_kind.replace('_', ' ').title()} — {insurer_name} ({ramo})",
    }


def _ingerir_sync(doc: dict, conteudo: str, susep: Optional[str],
                  vigencia: Optional[str]) -> int:
    """Chunk → embeddings → Qdrant global. Espelha `global_knowledge_seed`.

    Roda em thread porque embedding e upsert são bloqueantes, e o worker que
    chama isto também atende trabalho do corretor.
    """
    import os

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    from ...core.config import settings
    from ..knowledge_scope import GLOBAL_COLLECTION, SCOPE_GLOBAL_AUTOBROKERS
    from ..qdrant_service import get_qdrant_service

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " "],
    )
    chunks = [d.page_content for d in splitter.create_documents([conteudo])]
    if not chunks:
        return 0

    from langchain_openai import OpenAIEmbeddings

    dense = OpenAIEmbeddings(
        model="text-embedding-3-small", api_key=settings.OPENAI_API_KEY
    ).embed_documents(chunks)

    sparse = None
    try:
        from fastembed import SparseTextEmbedding

        sparse = list(SparseTextEmbedding(model_name="Qdrant/bm25").embed(chunks))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[corpus] sparse indisponivel (%s) — seguindo dense-only",
                       type(exc).__name__)

    qdrant = get_qdrant_service()
    doc_id = f"norm-{doc['id']}"
    company = (os.getenv("GLOBAL_KNOWLEDGE_COMPANY_ID") or "").strip() or "autobrokers-global"

    # Substitui a versão anterior do MESMO documento. Sem isso, a condição
    # antiga e a nova conviveriam no índice e a busca devolveria as duas —
    # que é exatamente como se responde cobertura errada com confiança.
    try:
        qdrant.delete_document(company, doc_id, collection_name=GLOBAL_COLLECTION)
    except Exception:  # noqa: BLE001
        pass

    ok = qdrant.insert_embeddings(
        company_id=company,
        document_id=doc_id,
        embeddings=dense,
        chunks=chunks,
        metadata={
            "document_name": doc["title"],
            "source": "normative_corpus",
            "chunk_type": "markdown",
            "insurer_key": doc["insurer_key"],
            "insurer_name": doc["insurer_name"],
            "product_line": doc["product_line"],
            "doc_kind": doc["doc_kind"],
            "susep_process": susep or "",
            "effective_from": vigencia or "",
            "source_url": doc["source_url"],
        },
        sparse_embeddings=sparse,
        collection_name=GLOBAL_COLLECTION,
        agent_id=None,
        knowledge_extras={
            "scope": SCOPE_GLOBAL_AUTOBROKERS,
            "curation_status": "published",
            "namespace": "normative",
            "version": (susep or doc["id"])[:12],
        },
    )
    return len(chunks) if ok else 0


class InsuranceCorpusService:
    """Catálogo e ingestão do corpus normativo — nível plataforma."""

    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)
        self._raw = supabase_client

    # ------------------------------------------------------------------
    # Consulta — o caminho que o agente usa
    # ------------------------------------------------------------------

    def ja_temos(self, url: str) -> Optional[dict]:
        """O documento desta URL já está no corpus e ingerido?"""
        r = (self.db.table("normative_documents")
             .select("id, title, insurer_name, product_line, doc_kind, susep_process, "
                     "version_label, effective_from, effective_until, status, "
                     "chunk_count, last_checked_at")
             .eq("source_url", url).maybe_single().execute()).data
        return r if r and r.get("status") == "ingested" else None

    def catalogo(self, *, insurer_key: Optional[str] = None,
                 product_line: Optional[str] = None, limite: int = 200) -> list[dict]:
        q = (self.db.table("normative_documents")
             .select("id, insurer_key, insurer_name, product_line, doc_kind, title, "
                     "susep_process, version_label, effective_from, status, "
                     "chunk_count, last_checked_at, next_check_at")
             .eq("status", "ingested"))
        if insurer_key:
            q = q.eq("insurer_key", insurer_key)
        if product_line:
            q = q.eq("product_line", product_line)
        return (q.order("insurer_name").limit(limite).execute()).data or []

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def registrar(self, *, insurer_key: str, insurer_name: str, product_line: str,
                  doc_kind: str, title: str, source_url: str,
                  susep_process: Optional[str] = None,
                  version_label: Optional[str] = None,
                  effective_from: Optional[str] = None,
                  check_interval_days: int = INTERVALO_PADRAO_DIAS,
                  notes: Optional[str] = None) -> dict:
        """Cadastra um documento como candidato. Não busca nada ainda."""
        registro = {
            "insurer_key": insurer_key, "insurer_name": insurer_name,
            "product_line": product_line, "doc_kind": doc_kind,
            "title": title, "source_url": source_url,
            "susep_process": susep_process, "version_label": version_label,
            "effective_from": effective_from,
            "check_interval_days": max(1, min(check_interval_days, 365)),
            "notes": notes, "status": "discovered",
            "next_check_at": _agora().isoformat(),
        }
        r = (self.db.table("normative_documents")
             .upsert(registro, on_conflict="source_url").execute()).data
        return (r or [{}])[0]

    def propor_candidato(self, *, url: str, titulo: str, texto: str) -> Optional[dict]:
        """Registra um documento lido ao vivo como candidato ao corpus.

        Filtra antes de propor. Sem filtro, todo PDF que qualquer agente abrisse
        entraria na fila de curadoria e o corpus normativo viraria lixeira —
        e um corpus poluído é pior que um corpus pequeno, porque a busca passa
        a devolver ruído com a mesma confiança que devolve norma.

        Nunca ingere sozinho: entra como `discovered`, esperando curadoria.
        Documento normativo alimenta o cérebro de TODAS as corretoras; isso não
        se decide por acaso de navegação.
        """
        classificacao = classificar(titulo, texto, url)
        if not classificacao:
            return None

        ja = (self.db.table("normative_documents").select("id, status")
              .eq("source_url", url).maybe_single().execute()).data
        if ja:
            return ja

        registro = {
            "insurer_key": classificacao["insurer_key"],
            "insurer_name": classificacao["insurer_name"],
            "product_line": classificacao["product_line"],
            "doc_kind": classificacao["doc_kind"],
            "title": (titulo or classificacao["titulo_sugerido"])[:300],
            "source_url": url,
            "susep_process": extrair_susep(texto),
            "effective_from": extrair_vigencia(texto),
            "status": "discovered",
            "next_check_at": _agora().isoformat(),
            "notes": "descoberto por leitura ao vivo — aguardando curadoria",
        }
        try:
            r = (self.db.table("normative_documents")
                 .upsert(registro, on_conflict="source_url").execute()).data
            logger.info("[corpus] candidato registrado: %s (%s)",
                        registro["title"][:60], classificacao["insurer_name"])
            return (r or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[corpus] candidato nao registrado: %s", type(exc).__name__)
            return None

    # ------------------------------------------------------------------
    # Ingestão
    # ------------------------------------------------------------------

    async def ingerir(self, documento_id: str, *,
                      company_id_custeio: Optional[str] = None) -> dict:
        """Busca o documento, compara com a última versão e ingere se mudou.

        `company_id_custeio` só existe porque `usage_events` exige um tenant.
        O evento sai marcado como `platform_corpus`: é custo da plataforma, não
        da corretora que porventura disparou. Cobrar de uma corretora a leitura
        de um documento que serve a todas seria cobrar a primeira a chegar.
        """
        doc = (self.db.table("normative_documents").select("*")
               .eq("id", documento_id).maybe_single().execute()).data
        if not doc:
            return {"ok": False, "motivo": "documento_inexistente"}

        self.db.table("normative_documents").update({
            "status": "fetching", "updated_at": _agora().isoformat(),
        }).eq("id", documento_id).execute()

        texto, erro = await self._buscar(doc["source_url"], company_id_custeio)

        # HTTP 402 = credito do provedor esgotado. Nao e defeito do documento e
        # nao pode gastar tentativa: marcar como `unreachable` faria o corpus
        # desistir de documentos perfeitamente validos por causa da fatura, e
        # ninguem descobriria o motivo real depois.
        if erro == "HTTP 402":
            self.db.table("normative_documents").update({
                "status": doc.get("status") or "discovered",
                "fetch_error": "credito do Firecrawl esgotado — aguardando plano",
                "last_checked_at": _agora(),
                "next_check_at": (_agora() + timedelta(hours=6)).isoformat(),
                "updated_at": _agora(),
            }).eq("id", documento_id).execute()
            logger.warning(
                "[corpus] CREDITO DO FIRECRAWL ESGOTADO (HTTP 402). %d documento(s) "
                "aprovado(s) continuam na fila e serao retomados quando houver credito.",
                len(self.vencidos(limite=50)))
            return {"ok": False, "motivo": "credito_esgotado", "bloqueante": True}

        if not texto:
            tentativas = int(doc.get("fetch_attempts") or 0) + 1
            # Backoff: documento fora do ar não pode ser tentado todo ciclo.
            atraso = min(2 ** tentativas, 30)
            self.db.table("normative_documents").update({
                "status": "unreachable" if tentativas >= MAX_TENTATIVAS else "discovered",
                "fetch_error": erro, "fetch_attempts": tentativas,
                "last_checked_at": _agora().isoformat(),
                "next_check_at": (_agora() + timedelta(days=atraso)).isoformat(),
                "updated_at": _agora().isoformat(),
            }).eq("id", documento_id).execute()
            return {"ok": False, "motivo": erro, "tentativas": tentativas}

        novo_hash = _hash(texto)
        if doc.get("content_hash") == novo_hash and doc.get("status") == "ingested":
            self._marcar_conferido(documento_id, doc, mudou=False)
            # `chunks: 0` de proposito: nada foi ingerido agora. Devolver a
            # contagem antiga faria o resumo contar de novo o que ja estava la.
            return {"ok": True, "mudou": False, "primeira": False, "chunks": 0}

        susep = doc.get("susep_process") or extrair_susep(texto)
        vigencia = doc.get("effective_from") or extrair_vigencia(texto)

        chunks = await self._ingerir_no_global(doc, texto, susep, vigencia)
        if chunks <= 0:
            self.db.table("normative_documents").update({
                "fetch_error": "ingestao devolveu zero chunks",
                "last_checked_at": _agora().isoformat(),
                "updated_at": _agora().isoformat(),
            }).eq("id", documento_id).execute()
            return {"ok": False, "motivo": "ingestao_vazia"}

        proxima = (self.db.table("normative_document_versions").select("version")
                   .eq("document_id", documento_id).order("version", desc=True)
                   .limit(1).execute()).data
        n = ((proxima or [{}])[0].get("version") or 0) + 1
        primeira = n == 1

        self.db.table("normative_document_versions").insert({
            "document_id": documento_id, "version": n, "content_hash": novo_hash,
            "byte_size": len(texto.encode("utf-8")), "chunk_count": chunks,
            "excerpt": texto[:1500],
            "change_summary": ("primeira captura" if primeira
                               else "conteúdo alterado na origem"),
        }).execute()

        if not primeira:
            self.db.table("normative_document_versions").update({
                "superseded_at": _agora().isoformat(),
            }).eq("document_id", documento_id).lt("version", n) \
              .is_("superseded_at", "null").execute()

        self.db.table("normative_documents").update({
            "status": "ingested", "content_hash": novo_hash,
            "byte_size": len(texto.encode("utf-8")), "chunk_count": chunks,
            "qdrant_collection": COLECAO_GLOBAL,
            "susep_process": susep, "effective_from": vigencia,
            "fetch_error": None, "fetch_attempts": 0,
            "last_checked_at": _agora().isoformat(),
            "last_change_at": _agora().isoformat(),
            "next_check_at": (_agora() + timedelta(
                days=int(doc.get("check_interval_days") or INTERVALO_PADRAO_DIAS))).isoformat(),
            "updated_at": _agora().isoformat(),
        }).eq("id", documento_id).execute()

        logger.info("[corpus] '%s' v%s ingerido — %s chunks%s",
                    doc["title"][:60], n, chunks, "" if primeira else " (MUDOU na origem)")
        return {"ok": True, "mudou": not primeira, "primeira": primeira,
                "versao": n, "chunks": chunks, "susep": susep, "vigencia": vigencia}

    async def _buscar(self, url: str, company_id: Optional[str]
                      ) -> tuple[Optional[str], Optional[str]]:
        from ..research.firecrawl import FirecrawlClient, configurado

        if not configurado():
            return None, "firecrawl_nao_configurado"
        cli = FirecrawlClient(self._raw, company_id=company_id)
        try:
            r = await cli.scrape(url, timeout_ms=90_000, skill="platform.corpus")
        except Exception as exc:  # noqa: BLE001
            return None, type(exc).__name__
        if not r.ok or not isinstance(r.dados, dict):
            return None, r.erro or "falha"
        texto = (r.dados.get("markdown") or "").strip()
        if len(texto) < 400:
            # PDF que devolve quase nada normalmente é imagem escaneada. Ingerir
            # isso poluiria o corpus com um documento vazio que parece presente.
            return None, "conteudo_insuficiente"
        return texto, None

    async def _ingerir_no_global(self, doc: dict, texto: str,
                                 susep: Optional[str], vigencia: Optional[str]) -> int:
        """Entrega ao serviço de ingestão que já existe. Nada novo aqui.

        O cabeçalho de procedência vai **dentro** do texto ingerido, não só nos
        metadados: é o que garante que qualquer trecho recuperado carregue a
        seguradora, o produto e a vigência junto. Trecho sem essa âncora vira
        uma frase sobre "a apólice" que o agente atribui à seguradora errada.
        """
        vig = vigencia or "não declarada no documento"
        cabecalho = (
            f"# {doc['title']}\n"
            f"**Seguradora:** {doc['insurer_name']} · **Ramo:** {doc['product_line']}\n"
            f"**Tipo:** {doc['doc_kind'].replace('_', ' ')}\n"
            + (f"**Processo SUSEP:** {susep}\n" if susep else "")
            + f"**Vigência a partir de:** {vig}\n"
            f"**Fonte:** {doc['source_url']}\n\n"
            "> Este texto é a condição vigente registrada nesta data. Uma apólice "
            "emitida antes da vigência acima pode ser regida por versão anterior — "
            "ao responder, informe a vigência e sugira conferir a apólice do cliente.\n\n"
            "---\n\n"
        )
        conteudo = cabecalho + texto

        # Mesmas primitivas do seed global (global_knowledge_seed): mesma
        # coleção, mesmo escopo, mesmo serviço Qdrant. Só o `namespace` muda,
        # de 'canon' para 'normative'. Um segundo caminho de ingestão global
        # significaria dois corpora divergindo em silêncio.
        try:
            import asyncio

            return await asyncio.to_thread(
                _ingerir_sync, doc, conteudo, susep, vigencia)
        except Exception as exc:  # noqa: BLE001
            logger.error("[corpus] ingestao falhou: %s", type(exc).__name__)
            return 0

    def _marcar_conferido(self, documento_id: str, doc: dict, *, mudou: bool) -> None:
        dias = int(doc.get("check_interval_days") or INTERVALO_PADRAO_DIAS)
        self.db.table("normative_documents").update({
            "status": "ingested",
            "last_checked_at": _agora().isoformat(),
            "next_check_at": (_agora() + timedelta(days=dias)).isoformat(),
            "fetch_error": None, "fetch_attempts": 0,
            "updated_at": _agora().isoformat(),
        }).eq("id", documento_id).execute()

    # ------------------------------------------------------------------
    # Descoberta
    # ------------------------------------------------------------------

    async def descobrir(self, *, insurer_key: str, site: str,
                        limite: int = 60) -> dict:
        """Varre o site de uma seguradora atrás de documentos normativos.

        Propõe, não ingere. Nenhuma URL entra no corpus por descoberta
        automática: o que este método faz é substituir a busca manual por uma
        lista de candidatos que alguém confirma. Documento normativo alimenta o
        cérebro de todas as corretoras — a decisão de incluir é humana.
        """
        from ..research.firecrawl import FirecrawlClient, configurado

        if not configurado():
            return {"ok": False, "motivo": "firecrawl_nao_configurado", "candidatos": 0}

        nome = SEGURADORAS.get(insurer_key, (insurer_key.title(), ()))[0]
        cli = FirecrawlClient(self._raw, company_id=None)
        try:
            r = await cli.map_site(site, limite=max(20, min(limite * 8, 400)))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "motivo": type(exc).__name__, "candidatos": 0}
        if not r.ok:
            return {"ok": False, "motivo": r.erro or "falha", "candidatos": 0}

        urls = r.dados if isinstance(r.dados, list) else (r.dados or {}).get("links") or []
        propostos = 0
        for item in urls:
            u = item if isinstance(item, str) else (item or {}).get("url")
            if not u:
                continue
            baixo = u.lower()
            # Filtra pela URL antes de gastar leitura: só o que se parece com
            # norma vira candidato. Ler cada página do site para descobrir o
            # que é norma custaria mais do que o corpus economiza.
            if not any(p in baixo for p in (
                    "condicoes", "condições", "condicao", "geral", "manual",
                    "circular", "regulamento", "cartilha")):
                continue
            if not baixo.endswith((".pdf", ".html", "/")) and "." in baixo.rsplit("/", 1)[-1]:
                continue

            c = classificar("", "", u)
            if not c:
                continue
            try:
                self.db.table("normative_documents").upsert({
                    "insurer_key": insurer_key, "insurer_name": nome,
                    "product_line": c["product_line"], "doc_kind": c["doc_kind"],
                    "title": c["titulo_sugerido"], "source_url": u,
                    "status": "discovered", "next_check_at": _agora().isoformat(),
                    "notes": f"descoberto varrendo {site} — aguardando curadoria",
                }, on_conflict="source_url").execute()
                propostos += 1
            except Exception:  # noqa: BLE001
                continue

        logger.info("[corpus] descoberta em %s: %d candidato(s)", site, propostos)
        return {"ok": True, "candidatos": propostos, "urls_varridas": len(urls),
                "creditos": r.creditos}

    def aprovar(self, documento_id: str, *, user_id: Optional[str] = None,
                interval_days: Optional[int] = None) -> dict:
        """Curadoria: libera o candidato para ingestão."""
        patch: dict[str, Any] = {
            "approved_at": _agora().isoformat(), "approved_by": user_id,
            "next_check_at": _agora().isoformat(), "updated_at": _agora().isoformat(),
        }
        if interval_days:
            patch["check_interval_days"] = max(1, min(int(interval_days), 365))
        r = (self.db.table("normative_documents").update(patch)
             .eq("id", documento_id).execute()).data
        return (r or [{}])[0]

    def rejeitar(self, documento_id: str, *, motivo: str = "",
                 user_id: Optional[str] = None) -> bool:
        r = (self.db.table("normative_documents").update({
            "status": "rejected", "notes": motivo or "rejeitado na curadoria",
            "approved_by": user_id, "updated_at": _agora().isoformat(),
        }).eq("id", documento_id).execute()).data
        return bool(r)

    def candidatos(self, limite: int = 100) -> list[dict]:
        """Fila de curadoria."""
        r = (self.db.table("normative_documents")
             .select("id, insurer_name, product_line, doc_kind, title, source_url, "
                     "susep_process, notes, created_at")
             .eq("status", "discovered").is_("approved_at", "null")
             .order("created_at", desc=True).limit(limite).execute())
        return r.data or []

    # ------------------------------------------------------------------
    # Reconferência periódica
    # ------------------------------------------------------------------

    def vencidos(self, limite: int = 8) -> list[dict]:
        """Documentos cuja reconferência já venceu — só os aprovados.

        `approved_at` não-nulo é a trava que faz a curadoria valer alguma coisa.
        Sem ela, qualquer PDF descoberto por varredura entraria no cérebro de
        todas as corretoras no ciclo seguinte do worker, e a fila de curadoria
        seria decorativa.
        """
        r = (self.db.table("normative_documents")
             .select("id, title, insurer_name, source_url, next_check_at, status")
             .in_("status", ["ingested", "discovered", "unreachable"])
             .not_.is_("approved_at", "null")
             .lte("next_check_at", _agora().isoformat())
             .order("next_check_at").limit(limite).execute())
        return r.data or []

    async def reconferir_pendentes(self, *, limite: int = 5,
                                   company_id_custeio: Optional[str] = None) -> dict:
        """Passa nos documentos vencidos. Chamado pelo worker que já existe.

        Limite baixo de propósito: reconferência é trabalho de fundo e não pode
        competir com o trabalho que o corretor está esperando.
        """
        pendentes = self.vencidos(limite)
        if not pendentes:
            return {"conferidos": 0, "mudaram": 0}

        novos, mudaram, conferidos, falhas = 0, 0, 0, 0
        bloqueado = False
        for d in pendentes:
            r = await self.ingerir(d["id"], company_id_custeio=company_id_custeio)
            conferidos += 1
            if r.get("bloqueante"):
                # Credito esgotado: parar o ciclo. Insistir nos proximos so
                # produz mais 402 e enche o log de erro que nao e erro.
                bloqueado = True
                break
            if r.get("ok"):
                if r.get("mudou"):
                    mudaram += 1
                    logger.warning("[corpus] MUDOU na origem: %s (%s) — versao %s",
                                   d["title"][:70], d["insurer_name"], r.get("versao"))
                elif r.get("chunks"):
                    novos += 1
            else:
                falhas += 1
                logger.warning("[corpus] falhou: %s — %s", d["title"][:60], r.get("motivo"))

        return {"conferidos": conferidos, "novos": novos, "mudaram": mudaram,
                "falhas": falhas, "bloqueado_por_credito": bloqueado}

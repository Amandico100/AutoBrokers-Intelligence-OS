# -*- coding: utf-8 -*-
"""Publica as SEIS cartas do pós-acionamento no RAG das duas corretoras.

```
(padrão)  imprime o PLANO — nada é gravado, nada é indexado.
--vivo    grava de verdade. ⚠️ Só roda onde há MinIO e Qdrant (o implantado).
```

## O trilho, declarado — porque o outro NÃO EXISTE

📊 Medido em 05/09/2026 (`grep -c knowledge_cards ingestion_service.py
document_service.py` → **0 e 0**): não existe caminho `documents →
knowledge_cards`. São DOIS trilhos separados, e é preciso escolher um:

```
documents  → ingestion_service    → Qdrant `company_<tenant>`   POR CORRETORA
conversas  → attendance_distiller → knowledge_cards → `autobrokers_global`
```

🔴 **Este script usa o PRIMEIRO** (E7). A razão é de produto: `knowledge_cards`
**não tem `company_id`** e é lida por uma coleção global única — "as cartas da
Resulta" não existem lá. As seis cartas são conhecimento de CADA corretora, e
por isso entram como documento do tenant.

## Passo a passo do Founder (SPEC-097.1 §7.3)

```
EasyPanel → serviço `smith-api` → aba Console
  cd /app                                   (se o console não abrir em /app)
  python scripts/publicar_cartas_0971.py            → mostra o plano, nada grava
  ...confira "2 tenants · 6 cartas"...
  python scripts/publicar_cartas_0971.py --vivo     → termina em
                                                      "VERIFY: 6/6 documentos"
```

⛔ Nenhuma mensagem sai. Nenhum agente é ligado. Zero PII: as cartas são
genéricas e não citam ninguém.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from app.atendimento.pos_acionamento import CARTAS  # noqa: E402

#: 🔴 MEDIDO (`select id, company_name from companies`), não lembrado.
TENANTS = (
    ("Resulta Seguros", "04b5cdbc-04cd-4ddf-8e4b-f43efb062fab"),
    ("AutoFleet", "6c9c55e2-2f30-4ca2-a1ef-4ef464ed1b4a"),
)

#: A marca que torna a publicação REVERSÍVEL e RECONHECÍVEL.
#: ⚠️ Sem ela não há como saber, seis meses depois, quais documentos vieram
#: daqui — e "apague as cartas da 097.1" viraria uma busca por texto.
MARCA = "spec-097.1:pos-acionamento"


def p(texto="") -> None:
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def _corpo(carta) -> str:
    """O texto que vai ao índice — título e carta, nada mais."""
    return "%s\n\n%s" % (carta["titulo"], carta["texto"])


def _nome(carta) -> str:
    return "pos-acionamento-%s.md" % str(carta["id"]).lower()


def plano() -> int:
    p("=" * 72)
    p("  PUBLICADOR DAS CARTAS DO PÓS-ACIONAMENTO — SPEC-097.1 U3.1")
    p("=" * 72)
    p("")
    p("  PLANO (nada foi gravado — rode com `--vivo` para publicar):")
    p("")
    p("  trilho: documents → ingestion_service → Qdrant `company_<tenant>`")
    p("  marca:  metadata.origem = %r" % MARCA)
    p("")
    for nome, empresa in TENANTS:
        p("  %-18s %s…" % (nome, empresa[:8]))
        for carta in CARTAS:
            p("      %s  %-52s %4d chars  %s"
              % (carta["id"], carta["titulo"][:52], len(carta["texto"]),
                 _nome(carta)))
    p("")
    p("  TOTAL: %d tenants · %d cartas = %d documentos"
      % (len(TENANTS), len(CARTAS), len(TENANTS) * len(CARTAS)))
    p("")
    p("  ⚠️ IDEMPOTENTE: cada documento tem `source_hash` do próprio texto; rodar")
    p("     de novo com o mesmo texto NÃO cria cópia. Mudar uma carta cria uma")
    p("     versão nova, e é para criar.")
    p("  ⛔ Precisa de MinIO e Qdrant: rode no `smith-api` implantado, não aqui.")
    p("=" * 72)
    return 0


def publicar(seco: bool = False) -> int:
    from app.core.database import get_supabase_client
    from app.services.ingestion_service import get_ingestion_service
    from app.services.minio_service import get_minio_service

    cliente = get_supabase_client().client
    ingestao = get_ingestion_service()
    minio = get_minio_service()
    agora = datetime.now(timezone.utc).isoformat()

    publicados = 0
    esperados = len(TENANTS) * len(CARTAS)
    for nome, empresa in TENANTS:
        p("\n── %s (%s…) ─────────────────────────────" % (nome, empresa[:8]))
        for carta in CARTAS:
            texto = _corpo(carta)
            digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()

            # ⚠️ IDEMPOTÊNCIA pelo conteúdo, não pelo nome: o mesmo texto não
            #    vira um segundo documento, e um texto novo vira — que é o que
            #    se quer quando uma carta é corrigida.
            ja = (cliente.table("documents").select("id, status")
                  .eq("company_id", empresa)                     # 🔴 §7
                  .eq("source_hash", digest).limit(1).execute()).data or []
            if ja:
                p("  = %s já publicada (documento %s…)" % (carta["id"], str(ja[0]["id"])[:8]))
                publicados += 1
                continue

            linha = (cliente.table("documents").insert({
                "company_id": empresa,                            # 🔴 §7
                "file_name": _nome(carta),
                "file_type": "text/markdown",
                "file_size": len(texto.encode("utf-8")),
                "status": "processing",
                "source_hash": digest,
                "source_kind": "spec",
                "source_ref": MARCA,
                "knowledge_class": "atendimento",
                "scope": "company",
                "visibility": "company",
                "metadata": {"origem": MARCA, "carta": carta["id"],
                             "titulo": carta["titulo"],
                             "cobre": list(carta.get("cobre") or ()),
                             "publicado_em": agora},
            }).execute()).data
            documento_id = str(linha[0]["id"])

            # O RAW no MinIO — é de lá que o `ingestion_service` lê, e o
            # caminho é o MESMO do `document_service` (`<empresa>/raw/<id>.json`).
            # ⚠️ Um caminho próprio aqui seria um segundo contrato de storage:
            # o ingestor procura naquele, e o documento nasceria mudo.
            from io import BytesIO

            bruto = BytesIO(json.dumps(
                {"text_content": texto,
                 "pages": [],
                 "metadata": {"origem": MARCA, "carta": carta["id"],
                              "titulo": carta["titulo"]}},
                ensure_ascii=False).encode("utf-8"))
            minio.client.put_object(
                "documents", "%s/raw/%s.json" % (empresa, documento_id),
                bruto, length=bruto.getbuffer().nbytes,
                content_type="application/json")

            # ⚠️ `agent_id=None` é RECUSADO pelo ingestor para documento comum
            #    (multi-agent). A carta é da CORRETORA, não de um agente — então
            #    ela vai pelo agente de atendimento do tenant, que é quem a lê.
            agentes = (cliente.table("agents").select("id")
                       .eq("company_id", empresa)                  # 🔴 §7
                       .eq("agent_role", "attendance").limit(1).execute()).data or []
            agente_id = str(agentes[0]["id"]) if agentes else None
            ok = ingestao.process_document(documento_id, empresa,
                                           strategy="markdown", agent_id=agente_id)
            p("  %s %s → documento %s… · indexado=%s"
              % ("✓" if ok else "⛔", carta["id"], documento_id[:8], ok))
            if ok:
                publicados += 1

    p("")
    p("VERIFY: %d/%d documentos nos %d tenants%s"
      % (publicados, esperados, len(TENANTS),
         "" if publicados == esperados else "   ⛔ FALTOU alguma"))
    return 0 if publicados == esperados else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Publica as 6 cartas da SPEC-097.1")
    ap.add_argument("--vivo", action="store_true",
                    help="publica de verdade (precisa de MinIO e Qdrant)")
    args = ap.parse_args()
    if not args.vivo:
        return plano()
    try:
        return publicar()
    except Exception as erro:  # noqa: BLE001
        p("⛔ a publicação parou: %s: %s" % (type(erro).__name__, erro))
        p("   (rode sem `--vivo` para ver o plano; o `--vivo` precisa de MinIO e Qdrant)")
        return 2


if __name__ == "__main__":
    sys.exit(main())

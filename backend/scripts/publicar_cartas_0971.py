# -*- coding: utf-8 -*-
"""Publica as SEIS cartas do pós-acionamento no RAG — GLOBAL ou por corretora.

```
(padrão)   imprime o PLANO — nada é gravado, nada é indexado.
--global   o modo do Founder: as 6 cartas UMA vez, para TODA corretora.
--vivo     grava de verdade. ⚠️ Só roda onde há MinIO e Qdrant (o implantado).
```

## 🔴 A decisão do Founder, 08/09/2026 — e ela muda o trilho

> *"Conhecimento de atendimento e pós-acionamento precisa ser conhecimento
>  GLOBAL, não por corretora. Toda corretora conectada precisa usufruir."*

O modo por tenant (`--vivo` sozinho) continua existindo e continua correto para
conhecimento que É de uma corretora só. Para as seis cartas do pós-acionamento
ele deixou de ser o modo certo, e o padrão passou a AVISAR isso.

## O trilho, medido — e o global tem UM caminho só

📊 Medido em 08/09/2026, lendo `search_service.py:466-602`,
`langchain_service.py:650-700` e `knowledge_scope.py:383-405`:

```
documents → ingestion_service → Qdrant `company_<tenant>`       POR CORRETORA
seed/cartas → Qdrant `autobrokers_global` (scope=global_autobrokers,
              curation_status=published, namespace ∈ ORCAMENTO_GLOBAL)   GLOBAL
```

🔴 **E a coleção `company_<GLOBAL_KNOWLEDGE_COMPANY_ID>` NÃO é lida pelo
runtime.** `search_service.py:583-602` apagou esse segundo caminho de
propósito, e o comentário de lá é explícito: *"Proibido reintroduzir leitura
por essa via"*. Publicar as cartas como DOCUMENTO da corretora técnica
"AutoBrokers Global Knowledge" daria uma execução verde, um `VERIFY: 6/6`, e
**nenhum agente leria uma linha** — é por isso que `--global` escreve na
coleção, e não na tabela.

⚠️ **Nenhum motor novo (`CLAUDE.md` §5):** `--global` chama
`global_knowledge_seed._ingest_seed_sync`, que é o publicador global que já
existe (o mesmo que ingere `app/data/global_knowledge/*.md` a cada deploy).
A idempotência é dele: o `document_id` é determinístico (`seed-<stem>`) e ele
**apaga a versão anterior antes de inserir** — rodar duas vezes deixa 6, nunca 12.

## Passo a passo do Founder (SPEC-097.1 §7.3)

```
EasyPanel → serviço `smith-api` → aba Console
  cd /app                                   (se o console não abrir em /app)
  python scripts/publicar_cartas_0971.py --global           → o plano, nada grava
  python scripts/publicar_cartas_0971.py --global --vivo    → termina em
                                                    "VERIFY: 6/6 cartas globais"
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


#: O `stem` de cada carta no acervo global. ⚠️ É ele que vira o `document_id`
#: determinístico (`seed-<stem>`) dentro do seeder — e é o determinismo que
#: torna a segunda rodada uma SUBSTITUIÇÃO, nunca uma cópia.
def _stem(carta) -> str:
    return "pos-acionamento-%s" % str(carta["id"]).lower()


def _empresa_global() -> str:
    """O rótulo de ESCRITA do acervo global — `GLOBAL_KNOWLEDGE_COMPANY_ID`.

    🔴 **Nunca hardcoded.** O seeder já lê esta variável
    (`global_knowledge_seed._global_company_id`) e cai em `'autobrokers-global'`
    quando ela não existe; usar o mesmo leitor é o que impede este script de
    escrever com um rótulo e o seeder com outro.

    ⚠️ Ele é RÓTULO, não tenant: a leitura global filtra por `scope` e
    `curation_status`, nunca por `company_id` (a coleção é uma só).
    """
    from app.services.global_knowledge_seed import _global_company_id

    return _global_company_id()


def _conferir_a_corretora_global(cliente) -> None:
    """Confere no banco que o id do env é mesmo o da 'Global Knowledge'.

    ⛔ **Só confere — nunca decide.** Um `select` que virasse fallback de
    escrita faria o acervo global mudar de dono quando alguém renomeasse uma
    corretora. Divergência aqui é AVISO, e o env continua valendo.
    """
    alvo = _empresa_global()
    try:
        achado = (cliente.table("companies").select("id, company_name")
                  .ilike("company_name", "%global%knowledge%").limit(2).execute()).data or []
    except Exception as erro:  # noqa: BLE001
        p("  ⚠️ não deu para conferir a corretora global (%s) — seguindo com o env"
          % type(erro).__name__)
        return
    if not achado:
        p("  ⚠️ nenhuma corretora com nome '…global…knowledge…' no banco")
        return
    ids = [str(linha.get("id")) for linha in achado]
    if alvo in ids:
        p("  ✓ rótulo global confere com a corretora %r" % achado[ids.index(alvo)]["company_name"])
    else:
        p("  ⚠️ GLOBAL_KNOWLEDGE_COMPANY_ID=%s… não bate com a(s) corretora(s) "
          "'global knowledge' do banco (%s…) — o env continua valendo, mas "
          "confira se é o rótulo que você quer" % (alvo[:8], ids[0][:8]))


def plano_global() -> int:
    p("=" * 72)
    p("  CARTAS DO PÓS-ACIONAMENTO — MODO GLOBAL (decisão do Founder 08/09/2026)")
    p("=" * 72)
    p("")
    p("  PLANO (nada foi gravado — rode com `--vivo` para publicar):")
    p("")
    p("  trilho: cartas → `_ingest_seed_sync` → Qdrant `autobrokers_global`")
    p("          scope=global_autobrokers · curation=published · namespace=canon")
    p("  rótulo: GLOBAL_KNOWLEDGE_COMPANY_ID = %s…" % (_empresa_global()[:8] or "(vazio)"))
    p("")
    for carta in CARTAS:
        p("      %s  %-52s %4d chars  seed-%s"
          % (carta["id"], carta["titulo"][:52], len(carta["texto"]), _stem(carta)))
    p("")
    p("  TOTAL: %d cartas · UMA vez · TODA corretora conectada lê" % len(CARTAS))
    p("")
    p("  ⚠️ IDEMPOTENTE: o `document_id` é `seed-<stem>` e o seeder APAGA a")
    p("     versão anterior antes de inserir — a 2ª rodada substitui, não soma.")
    p("  ⛔ Precisa de Qdrant e da chave da OpenAI (embeddings): rode no")
    p("     `smith-api` implantado, não aqui.")
    p("=" * 72)
    return 0


def publicar_global() -> int:
    """As 6 cartas UMA vez, no acervo que toda corretora lê."""
    from app.core.database import get_supabase_client
    from app.services.global_knowledge_seed import _ingest_seed_sync

    p("=" * 72)
    p("  CARTAS DO PÓS-ACIONAMENTO — PUBLICANDO NO ACERVO GLOBAL")
    p("=" * 72)
    try:
        _conferir_a_corretora_global(get_supabase_client().client)
    except Exception as erro:  # noqa: BLE001
        p("  ⚠️ banco indisponível para a conferência (%s) — seguindo com o env"
          % type(erro).__name__)

    publicadas = 0
    for carta in CARTAS:
        texto = _corpo(carta)
        digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        try:
            chunks = _ingest_seed_sync(_stem(carta), carta["titulo"], texto, digest)
        except Exception as erro:  # noqa: BLE001
            p("  ⛔ %s NÃO publicada: %s: %s" % (carta["id"], type(erro).__name__, erro))
            continue
        p("  %s %s → seed-%s · %d chunk(s)"
          % ("✓" if chunks else "⛔", carta["id"], _stem(carta), chunks))
        if chunks:
            publicadas += 1

    p("")
    p("VERIFY: %d/%d cartas globais em `autobrokers_global`%s"
      % (publicadas, len(CARTAS),
         "" if publicadas == len(CARTAS) else "   ⛔ FALTOU alguma"))
    p("  (rode de novo: o total tem de continuar %d — o seeder substitui)"
      % len(CARTAS))
    return 0 if publicadas == len(CARTAS) else 1


def plano() -> int:
    p("=" * 72)
    p("  PUBLICADOR DAS CARTAS DO PÓS-ACIONAMENTO — SPEC-097.1 U3.1")
    p("=" * 72)
    p("")
    p("")
    p("  🔴 A DECISÃO DO FOUNDER (08/09/2026) É **GLOBAL**, NÃO POR CORRETORA:")
    p("     \"conhecimento de atendimento e pós-acionamento precisa ser")
    p("      conhecimento GLOBAL. Toda corretora conectada precisa usufruir.\"")
    p("     👉 use `--global`. Este modo por tenant publica as MESMAS 6 cartas")
    p("        %d vezes e não alcança a corretora nº %d."
      % (len(TENANTS), len(TENANTS) + 1))
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
    ap.add_argument("--global", dest="global_", action="store_true",
                    help="publica as 6 cartas UMA vez no acervo global "
                         "(`autobrokers_global`) — toda corretora lê")
    args = ap.parse_args()
    if args.global_:
        if not args.vivo:
            return plano_global()
        try:
            return publicar_global()
        except Exception as erro:  # noqa: BLE001
            p("⛔ a publicação global parou: %s: %s" % (type(erro).__name__, erro))
            p("   (rode sem `--vivo` para ver o plano; o `--vivo` precisa de "
              "Qdrant e da chave da OpenAI)")
            return 2
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

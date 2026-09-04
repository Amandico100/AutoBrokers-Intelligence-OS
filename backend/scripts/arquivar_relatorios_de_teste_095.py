# -*- coding: utf-8 -*-
"""Tira da biblioteca da corretora os relatórios que foram teste NOSSO — SPEC-095 B.4.

```
APPLY     `--aplicar` chama `ArtifactService.arquivar()` nos candidatos.
          Sem a flag, o script MEDE e não escreve nada (`--dry-run` é o padrão).
VERIFY    os dois SELECTs impressos antes e depois, no fim desta docstring.
ROLLBACK  update artifacts set archived_at = null
          where id in (select artifact_id from artifact_events
                       where event_type = 'artifact.archived'
                         and detail->>'motivo' like '%SPEC-095 B.4%');
```

## Por que isto existe

📊 Medido em 04/09/2026 (`select template_key, date(created_at), count(*) from
artifacts where company_id = <Resulta> and origin = 'chat' group by 1, 2`):

```
commercial.pipeline   14   todos em 18/08 05:42–10:57
renewals.radar        14   todos em 18/08 05:42–10:57      ← execução da SPEC-081
executive.pulse360     6   03/09 20:03–20:37 · 04/09 02:09–02:54  ← 094 / 094.1
```

📊 O investigador cruzou os 7 Pulsos (6 Resulta + 1 AutoFleet) com o `git log`
por menor distância: **7/7 coincidem em ±40 min com um commit** (0,4 a 34,6 min).
📊 E em TODO o banco: `requested_by` preenchido em **0/136** peças, `tags` em
**0/136**. **Zero pergunta real do dono.** A biblioteca que o corretor abre é,
hoje, a lista das vezes em que nós rodamos o produto para testá-lo.

## ⛔ As regras que tornam esta limpeza reversível e honesta

```
⛔ ARQUIVA, nunca DELETE. `archived_at` + evento `artifact.archived` com o motivo.
   Estas peças não são lixo: são o registro de que o produto rodou. O ROLLBACK
   acima as devolve inteiras, e o link já entregue pelo chat continua abrindo.
⛔ NUNCA toca peça com a tag `canario`. As desta SPEC se arquivam sozinhas
   (`canario_095.py`, passo (f)) — arquivá-las aqui esconderia o gesto delas.
⛔ Só as TRÊS JANELAS medidas. `origin='chat' and requested_by is null` sozinho
   casaria TODO Pulso real para sempre (📊 `_publicar` não grava `requested_by`),
   e a limpeza de hoje viraria uma armadilha para o primeiro pedido de verdade.
⛔ NUNCA imprime título nem id inteiro: a linha é (corretora, template, dia, n).
```

## O VERIFY, com a data FIXA

⚠️ A data de corte é literal de propósito. Sem ela o número envelheceria no
primeiro Pulso que o dono pedisse de verdade — e um VERIFY que muda de resposta
sozinho não prova nada.

```sql
-- ANTES: 35   ·   DEPOIS: 0
select count(*) from artifacts
 where origin = 'chat' and requested_by is null and archived_at is null
   and created_at < '2026-09-04 07:00+00';

-- ANTES: 0    ·   DEPOIS: 35
select count(*) from artifact_events where event_type = 'artifact.archived';
```
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

# ⚠️ O console do Windows abre em cp1252, e um `📊` derruba o `print` com
# `UnicodeEncodeError`. Sem esta linha o script morre DEPOIS de consultar o
# banco e ANTES de mostrar o que achou — o pior lugar possível para morrer.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

#: 🔴 As três janelas que o BLOCO 0 mediu. Cada uma é uma execução de SPEC
#: identificada pelo `git log`; fora delas o script não olha.
#:
#: ⚠️ 📊 **ACHADO DO BLOCO 0, 04/09/2026 — a SPEC dá as janelas em América/São
#: Paulo e a coluna volta em UTC.** As duas leituras diferem por 3 horas, e a
#: diferença não é cosmética: com as janelas aplicadas COMO SE fossem UTC, o
#: script achou **21 dos 35** candidatos e deixou 14 de fora **em silêncio** —
#: uma limpeza que parece ter funcionado e que deixa 40% da sujeira na
#: biblioteca do dono (CLAUDE.md §9.4: um padrão medido com uma régua e
#: aplicado com outra é um padrão sobre outra coisa).
#:
#: 📊 O que o banco devolve, medido: 18/08 **08:42–13:57 UTC** (= 05:42–10:57
#: em São Paulo, que é o número da §1.1) · Pulsos em 03/09 **23:03–23:37 UTC**
#: (= 20:03–20:37 SP) e 04/09 **05:09–05:54 UTC** (= 02:09–02:54 SP).
#:
#: Por isso as janelas estão escritas AQUI em UTC, com o horário de São Paulo
#: ao lado: a comparação acontece contra a coluna, na régua da coluna, e a
#: conversão fica visível em vez de acontecer no meio do caminho.
JANELAS = (
    # 18/08, 05:00–11:00 em São Paulo — a execução da SPEC-081 (`bb4d5ce`).
    ("SPEC-081 · Raio-X e Radar", "2026-08-18T08:00:00+00:00", "2026-08-18T14:00:00+00:00"),
    # 03/09, 15:00–21:00 em São Paulo — a execução da SPEC-094.
    ("SPEC-094 · Pulso 360", "2026-09-03T18:00:00+00:00", "2026-09-04T00:00:00+00:00"),
    # 03/09 21:00 a 04/09 04:00 em São Paulo — a execução da SPEC-094.1.
    ("SPEC-094.1 · Pulso 360", "2026-09-04T00:00:00+00:00", "2026-09-04T07:00:00+00:00"),
)

MOTIVO = ("canário de execução de SPEC (081/094/094.1) — SPEC-095 B.4")

#: A data de corte do VERIFY. Literal, e não `now()`: ver a docstring.
CORTE_DO_VERIFY = "2026-09-04T07:00:00+00:00"


def sem_o_init_pesado() -> None:
    """Deixa `app.services` importável sem executar o `__init__.py` dele.

    ⚠️ `app/services/__init__.py` importa `ingestion_service`, que importa
    `fastembed` — um pacote de embeddings que este script não usa para nada e
    que não existe em toda máquina onde uma limpeza precisa rodar. Registrar o
    NAMESPACE resolve sem tocar no produto: `app.services.artifacts.service`
    continua sendo importado do jeito normal, com o `__package__` certo, e os
    imports relativos de dentro dele continuam funcionando.

    É a mesma solução do backfill da SPEC-090, escrita aqui em vez de copiada.
    """
    import types

    for nome, rel in (("app.services", "app/services"),):
        if nome in sys.modules:
            continue
        mod = types.ModuleType(nome)
        mod.__path__ = [os.path.join(RAIZ, *rel.split("/"))]
        sys.modules[nome] = mod


def _quando(valor) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _na_janela(criado: datetime) -> str:
    """O nome da janela que contém esta data, ou `""`."""
    for nome, inicio, fim in JANELAS:
        i, f = _quando(inicio), _quando(fim)
        if i and f and i <= criado < f:
            return nome
    return ""


def _verify(db) -> tuple[int, int]:
    """Os dois números do VERIFY. Devolve `(vivas_do_chat, eventos_de_arquivo)`."""
    vivas = (db.table("artifacts").select("id", count="exact")
             .eq("origin", "chat").is_("requested_by", "null")
             .is_("archived_at", "null").lt("created_at", CORTE_DO_VERIFY)
             .execute())
    eventos = (db.table("artifact_events").select("id", count="exact")
               .eq("event_type", "artifact.archived").execute())
    return (int(getattr(vivas, "count", None) or len(vivas.data or [])),
            int(getattr(eventos, "count", None) or len(eventos.data or [])))


def main() -> int:
    p = argparse.ArgumentParser(
        description="Arquiva os relatórios de execução de SPEC. SPEC-095 B.4.")
    p.add_argument("--aplicar", action="store_true",
                   help="grava (archived_at + evento). Sem isto, só mede.")
    p.add_argument("--dry-run", action="store_true",
                   help="o padrão: mede e não escreve.")
    a = p.parse_args()
    aplicar = bool(a.aplicar) and not a.dry_run

    sem_o_init_pesado()
    from app.core.database import get_supabase_client
    from app.services.artifacts.service import TAG_DO_CANARIO, ArtifactService

    cliente = get_supabase_client()
    db = cliente.client
    servico = ArtifactService(cliente)

    antes = _verify(db)
    print("📊 VERIFY ANTES")
    print(f"   peças do chat sem pedido, vivas, antes de {CORTE_DO_VERIFY[:10]} ... {antes[0]}")
    print(f"   eventos `artifact.archived` no banco ......................... {antes[1]}")
    print()

    # ⚠️ A leitura pede `tags` e `company_id` porque as duas DECIDEM: a tag
    # protege o canário desta SPEC, e a corretora é o que a linha imprime.
    linhas = (db.table("artifacts")
              .select("id, company_id, template_key, created_at, tags, archived_at")
              .eq("origin", "chat").is_("archived_at", "null")
              .lt("created_at", CORTE_DO_VERIFY)
              .limit(2000).execute().data or [])

    nomes = {}
    for c in (db.table("companies").select("id, company_name")
              .limit(200).execute().data or []):
        nomes[str(c.get("id"))] = str(c.get("company_name") or "")[:18]

    por_grupo: Counter = Counter()
    janela_do_grupo: dict = {}
    candidatos: list[dict] = []
    protegidos = 0
    fora_de_janela = 0

    for linha in linhas:
        criado = _quando(linha.get("created_at"))
        if criado is None:
            continue
        # ⛔ A peça do canário desta SPEC nunca é tocada aqui.
        if TAG_DO_CANARIO in (linha.get("tags") or []):
            protegidos += 1
            continue
        janela = _na_janela(criado)
        if not janela:
            fora_de_janela += 1
            continue
        chave = (nomes.get(str(linha.get("company_id")), "?"),
                 str(linha.get("template_key") or ""),
                 criado.strftime("%d/%m"))
        por_grupo[chave] += 1
        janela_do_grupo[chave] = janela
        candidatos.append(linha)

    print("📊 CANDIDATOS — por corretora, template e dia")
    print("   ⛔ sem título e sem id: a linha diz QUANTOS, nunca QUAIS.")
    print()
    for (corretora, template, dia), n in sorted(por_grupo.items()):
        print(f"   {corretora:<18} {template:<22} {dia}   {n:>3}   "
              f"[{janela_do_grupo[(corretora, template, dia)]}]")
    print()
    print(f"📊 total de candidatos ................ {len(candidatos)}")
    print(f"📊 peças do chat FORA das 3 janelas ... {fora_de_janela}   (não serão tocadas)")
    print(f"📊 peças com a tag `{TAG_DO_CANARIO}` ......... {protegidos}   (nunca são tocadas)")
    print()

    if not aplicar:
        print("⚠️ DRY-RUN — nada foi gravado. Para aplicar: `--aplicar`.")
        print("   ROLLBACK, se algum dia precisar (está na docstring deste arquivo):")
        print("   update artifacts set archived_at = null where id in (select artifact_id")
        print("     from artifact_events where event_type = 'artifact.archived'")
        print("       and detail->>'motivo' like '%SPEC-095 B.4%');")
        return 0

    arquivados = 0
    for linha in candidatos:
        ok = servico.arquivar(str(linha.get("company_id")), str(linha.get("id")),
                              MOTIVO)
        arquivados += 1 if ok else 0
    print(f"📊 arquivados ......................... {arquivados} de {len(candidatos)}")
    print()

    depois = _verify(db)
    print("📊 VERIFY DEPOIS")
    print(f"   peças do chat sem pedido, vivas, antes de {CORTE_DO_VERIFY[:10]} ... "
          f"{antes[0]} → {depois[0]}")
    print(f"   eventos `artifact.archived` no banco ......................... "
          f"{antes[1]} → {depois[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

---
> **Status:** canônico — manifesto de migrations
> **Autoridade:** [`docs/canon/MIGRATIONS-AUTHORITY.md`](../../../docs/canon/MIGRATIONS-AUTHORITY.md) · decisão **D2**
> **Última atualização:** 2026-07-25 (SPEC-054 Bloco A)
---

# MANIFEST de migrations

> [!CAUTION]
> Este arquivo responde a pergunta **"este arquivo já foi aplicado?"**.
> Consulte-o antes de qualquer SQL. O repositório **não** é a fonte completa do schema.

## Classes

| Classe | Significado | Ação permitida |
|---|---|---|
| `APLICADA` | arquivo no repo **com** versão em `supabase_migrations.schema_migrations` | nunca reaplicar, nunca editar |
| `ISOLADA` | aplicada, mas fora do diretório canônico | registrar; mover só após tooling atualizado |
| `NÃO RASTREADA` | arquivo no repo **sem** versão no banco, mas estrutura **já existe** em produção | **proibido aplicar** — será absorvida pelo baseline |
| `MONOLÍTICA` | dump histórico | **proibido aplicar** em qualquer circunstância |
| `SEM_ARQUIVO` | versão aplicada no banco **sem** arquivo no repo | reconstruir no baseline do Bloco B |

## SPEC-054 Bloco A — aplicadas em 2026-07-25

| Arquivo | Versão no banco | Classe | Rollback |
|---|---|---|---|
| `20260725_01_spec054_a1_rpc_security.sql` | `spec054_a1_rpc_security` | `APLICADA` | `backup/…/rollback/01-rollback-a1-functions.sql` |
| `20260725_02_spec054_a2_ucp_view_security.sql` | `spec054_a2_ucp_view_security` | `APLICADA` | `backup/…/rollback/02-rollback-a2-view.sql` |
| `20260725_03_spec054_a4_backfill_message_media_path.sql` | `spec054_a4_backfill_message_media_path` | `APLICADA` | `backup/…/rollback/04-rollback-a4-backfill.sql` |
| `20260725_04_spec054_a3_storage_privacy.sql` | *(pendente de deploy)* | `PENDENTE` | `backup/…/rollback/03-rollback-a3-storage.sql` |

> `backup/…` = `C:\Users\amand\Backups\AutoBrokers\SPEC-054-A-20260725\` — fora do Git, por conter cópia de objetos de corretora.

**Ordem de aplicação intencional:** A1 → A2 → A4 → *deploy do código de Storage* → A3.
A3 fecha os buckets e **só pode ser aplicada depois** de o proxy autenticado estar em produção (expand antes de contract, SPEC-054 §7.3.2).

## Arquivos históricos — classificação de 2026-07-25

### `APLICADA` — 11 arquivos com versão correspondente

`20260708_01_spec023_billing_collection` · `20260708_02_spec023_allianz_login_url` · `20260708_03_spec023_p5_public_vidros` · `20260708_04_spec023_billing_message_firecrawl` · `20260719_01_spec040_attendance_transcripts` · `20260719_02_spec040_conduct_playbooks_cards` · `20260719_03_spec040_agent_memories` · `20260720_01_spec044_tres_camadas` · `20260720_02_spec045_platform_sends` · `20260720_03_spec046_graveyard_mvp_tables` · `20260721_01_spec047_rls_e_company_members`

### `ISOLADA` — 1 arquivo

`supabase/migrations/20260723_technical_whatsapp_sandbox_guard.sql` → versão `20260723183305`.
Aplicada. Cria os triggers de sandbox técnico do WhatsApp, **verificados vivos**. Fora do diretório canônico. Não mover antes de o tooling respeitar este manifesto.

### `NÃO RASTREADA` — 13 arquivos · **PROIBIDO APLICAR**

`20260612_attendance_corridor_mvp_foundation` · `20260613_human_support_destinations_foundation` · `20260703_01_spec017_whatsapp_channel_expand` · `20260703_02_spec017_integrations_purpose` · `20260703_03_spec018_capability_seeds` · `20260704_01_spec017_conversations_claim` · `20260705_01_f2_routines` · `20260706_01_spec019c_routine_templates` · `20260706_02_spec019e_routine_knowledge` · `20260706_03_spec020_portal` · `20260706_04_spec020_portals_registry` · `20260706_05_spec020_portals_seed_insurers` · `20260706_06_spec020_portal_capability`

> Estes arquivos **parecem pendentes e não são**. As estruturas (rotinas, portais, corredores, capability seeds) já existem em produção. Aplicá-los repetiria DDL, sobrescreveria policies e alteraria defaults.

### `MONOLÍTICA` — 3 arquivos · **PROIBIDO APLICAR**

`schema_completo.sql` (121,7 KB) · `upgrade_v6.2.sql` (10,3 KB) · `storage_buckets.sql` (4,7 KB)

Úteis apenas para investigação histórica. Serão movidos para `docs/canon/sql/_historical/` **depois** da auditoria de referências no Bloco B.

### `SEM_ARQUIVO` — 9 versões aplicadas sem arquivo no repo

`20260711173923 billing_sent_log` · `20260713225053 spec034_ura_maps` · `20260713232958 spec034_broker_insights` · `20260714001905 spec034_onda4_tailor_auditor` · `20260714031357 spec036_is_technical` · `20260714173623 spec036_agent_activities` · `20260718044915 spec038_atlas_observer_tables` · `20260718045107 spec038_fix_dedupe_index` · `20260718222805 spec038_route_drift`

Criadas diretamente no banco. Serão reconstruídas pelo **baseline do Bloco B**.

## Checksums

Os `sha256` de cada arquivo histórico estão registrados em [`docs/canon/MIGRATIONS-AUTHORITY.md`](../../../docs/canon/MIGRATIONS-AUTHORITY.md) §3 e servem como linha de base de integridade.

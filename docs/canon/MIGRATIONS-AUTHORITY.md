---
> **Status:** canônico
> **Versão:** 1.0 · **Criado em:** 25/07/2026
> **Autoridade superior:** SPEC-054 · decisão [`FOUNDER-DECISIONS.md#d2`](FOUNDER-DECISIONS.md)
> **Função:** declarar a autoridade de schema e impedir que qualquer executor destrua o banco vivo por replay cego
---

# Migrations Authority — AutoBrokers Intelligence OS

> [!CAUTION]
> **Leia este documento inteiro antes de escrever qualquer SQL.**
> O banco de produção contém objetos criados fora do histórico oficial. Aplicar "tudo que existe no repositório" **destrói dados**.

---

## 1. Diretório canônico

**Novas** migrations vão exclusivamente para:

```text
backend/supabase/migrations/
```

Diretórios com conteúdo histórico, **não canônicos para novas migrations**:

| Caminho | Situação |
|---|---|
| `supabase/migrations/` | contém **1** arquivo, já aplicado em produção. Ver §4. |
| `docs/canon/sql/` | material documental. Nunca é caminho de aplicação. |

Nenhum arquivo é movido, renomeado, apagado ou reaplicado antes do manifesto do §5 estar produzido e aprovado.

---

## 2. Estado factual em 25/07/2026

Confrontação read-only entre o repositório na `main` @ `3c8c752` e `supabase_migrations.schema_migrations` no projeto `dcajcvlzcjbmyapmklil`:

| Métrica | Valor |
|---|---|
| Versões rastreadas no banco | **21** |
| Primeira versão rastreada | `20260708051332` |
| Última versão rastreada | `20260723183305` |
| Arquivos `.sql` no repositório | **28** (25 migrations + 3 DDL monolíticos) |
| Correspondências confirmadas | **12** |
| **Versões aplicadas SEM arquivo no repositório** | **9** |
| **Arquivos SEM versão rastreada no banco** | **16** |

> **FATO:** um ambiente novo criado apenas a partir das migrations rastreadas **não** reproduz o banco atual.
> **FATO:** aplicar todos os arquivos do repositório sobre produção repetiria DDL, sobrescreveria policies e alteraria defaults.

---

## 3. Classificação de cada arquivo

Classes: `APLICADA` · `NÃO RASTREADA` · `ISOLADA` · `MONOLÍTICA`.

### 3.1 `APLICADA` — arquivo no repo com versão correspondente no banco

| Arquivo (`backend/supabase/migrations/`) | Versão no banco | sha256[0:16] |
|---|---|---|
| `20260708_01_spec023_billing_collection.sql` | `20260708051332` | `7378BBD4BEF177B6` |
| `20260708_02_spec023_allianz_login_url.sql` | `20260708052243` | `52C5F6D6CC162EE7` |
| `20260708_03_spec023_p5_public_vidros.sql` | `20260708151432` | `D8AE2497C4461246` |
| `20260708_04_spec023_billing_message_firecrawl.sql` | `20260708185854` | `2CC8C44A56F467F1` |
| `20260719_01_spec040_attendance_transcripts.sql` | `20260719162931` | `7E84BC5FEB0FE104` |
| `20260719_02_spec040_conduct_playbooks_cards.sql` | `20260719175618` | `E72A19B3D37B0DC3` |
| `20260719_03_spec040_agent_memories.sql` | `20260719185952` | `93BE3AE6F6B39310` |
| `20260720_01_spec044_tres_camadas.sql` | `20260720234826` | `C5A6638D8A0F354B` |
| `20260720_02_spec045_platform_sends.sql` | `20260721001845` | `6E18B8EE2DF3C8AF` |
| `20260720_03_spec046_graveyard_mvp_tables.sql` | `20260721005216` | `86E8C523C72053CF` |
| `20260721_01_spec047_rls_e_company_members.sql` | `20260721181601` | `64EC7A0FA1DEBF98` |

**Regra:** nunca reaplicar. Nunca editar. Se o conteúdo precisar mudar, cria-se migration nova.

### 3.2 `ISOLADA` — aplicada, mas fora do diretório canônico

| Arquivo | Versão no banco | sha256[0:16] |
|---|---|---|
| `supabase/migrations/20260723_technical_whatsapp_sandbox_guard.sql` | `20260723183305` | `DC2B8BE225E102F7` |

Cria os triggers de sandbox técnico do WhatsApp (`is_technical_company`, `isolate_technical_observed_event`, `isolate_technical_observed_session`, `block_technical_attendance_capture`, `enforce_technical_whatsapp_integration`) — **todos vivos e verificados no banco**.

**Regra:** registrar no manifesto e **proteger contra dupla aplicação**. Só é reorganizada depois do manifesto aprovado e da atualização do tooling.

### 3.3 `NÃO RASTREADA` — arquivo no repo sem versão no banco

Estruturas que **existem** no banco (rotinas, portais, corredores, capability seeds), mas cujas migrations nunca entraram no histórico oficial:

| Arquivo (`backend/supabase/migrations/`) | sha256[0:16] |
|---|---|
| `20260612_attendance_corridor_mvp_foundation.sql` | `C71D413230D0699B` |
| `20260613_human_support_destinations_foundation.sql` | `DD0DE37EC6F6D584` |
| `20260703_01_spec017_whatsapp_channel_expand.sql` | `C564A13D5746C1BF` |
| `20260703_02_spec017_integrations_purpose.sql` | `0247122BCDA5F2A5` |
| `20260703_03_spec018_capability_seeds.sql` | `A58558C0E11E26D3` |
| `20260704_01_spec017_conversations_claim.sql` | `7A018F72EEBCD4F3` |
| `20260705_01_f2_routines.sql` | `961DF72556FD6F1B` |
| `20260706_01_spec019c_routine_templates.sql` | `51483E8061F3277C` |
| `20260706_02_spec019e_routine_knowledge.sql` | `8326D99D6299E36B` |
| `20260706_03_spec020_portal.sql` | `56D28F20D5718C4C` |
| `20260706_04_spec020_portals_registry.sql` | `FCEBD9B7C26FE188` |
| `20260706_05_spec020_portals_seed_insurers.sql` | `0EDCB1341BC7F4B1` |
| `20260706_06_spec020_portal_capability.sql` | `5A0E6DA2C37D96A1` |

> [!WARNING]
> Estes 13 arquivos são a maior armadilha do repositório. Parecem "pendentes" e **não são**. As estruturas já existem em produção.
> **Proibido aplicá-los.** Serão absorvidos pelo baseline (§6).

### 3.4 `MONOLÍTICA` — nunca são caminho de aplicação

| Arquivo | Tamanho | sha256[0:16] |
|---|---|---|
| `backend/supabase/migrations/schema_completo.sql` | 121,7 KB | `50A62AC3153C4294` |
| `backend/supabase/migrations/upgrade_v6.2.sql` | 10,3 KB | `AD5BEAD6FA5623A2` |
| `backend/supabase/migrations/storage_buckets.sql` | 4,7 KB | `C72A05945644D62C` |

**Proibição absoluta:** nenhum deles é bootstrap, baseline ou migration. São úteis apenas para investigação histórica.

Só serão marcados como históricos e movidos **depois** de auditoria de referências no código, scripts, CI e tooling.

---

## 4. Versões aplicadas sem arquivo no repositório

Nove estruturas foram criadas diretamente no banco (dashboard, MCP ou script fora do repo):

| Versão | Nome | O que provavelmente criou |
|---|---|---|
| `20260711173923` | `billing_sent_log` | `billing_sent_log` |
| `20260713225053` | `spec034_ura_maps` | `ura_maps` |
| `20260713232958` | `spec034_broker_insights` | `broker_insights` |
| `20260714001905` | `spec034_onda4_tailor_auditor` | `playbook_overlays`, `conversation_scorecards` |
| `20260714031357` | `spec036_is_technical` | função `is_technical_company` |
| `20260714173623` | `spec036_agent_activities` | `agent_activities` |
| `20260718044915` | `spec038_atlas_observer_tables` | `observed_sessions`, `observed_events` |
| `20260718045107` | `spec038_fix_dedupe_index` | índice de dedupe do Observador |
| `20260718222805` | `spec038_route_drift` | `route_drift` |

> **INFERÊNCIA**, não fato: a correspondência entre versão e objeto foi deduzida pelo nome. O manifesto do §5 deve **confirmar** cada uma contra o DDL real antes de qualquer decisão.

**Consequência:** o repositório **não** é a fonte completa do schema. O banco vivo é. Por isso o baseline do §6 é gerado a partir do banco, nunca dos arquivos.

---

## 5. Processo obrigatório de manifesto

Antes de qualquer alteração de schema na SPEC-054 Bloco B:

```text
1. inventariar todos os .sql dos dois diretórios
2. calcular sha256 de cada arquivo
3. ler supabase_migrations.schema_migrations (read-only)
4. cruzar versão × arquivo × objeto real no catálogo do Postgres
5. classificar: APLICADA / NÃO RASTREADA / ISOLADA / MONOLÍTICA / ÓRFÃ
6. registrar a migration ISOLADA e travar contra dupla aplicação
7. produzir backend/supabase/migrations/MANIFEST.md versionado
8. atualizar o tooling para respeitar o manifesto
9. só então reorganizar arquivos históricos
```

O manifesto é **versionado no Git** e atualizado a cada nova migration. Ele é a resposta a "este arquivo já foi aplicado?".

**Nenhum passo pode ser pulado.** Um executor que não conseguir completar o cruzamento **para** e registra em [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md).

---

## 6. Estratégia baseline + incrementais

```text
banco vivo inventariado
→ snapshot de DDL metadata-only (sem dados)
→ classificação por owner documental
→ migration baseline declarativa
→ migrations incrementais a partir daí
→ teste em ambiente vazio (deve subir do zero)
→ teste em cópia do atual (diff destrutivo esperado = vazio)
→ produção somente após ambos verdes
```

**Regras do baseline**

1. Gerado a partir do **banco vivo**, nunca dos arquivos históricos.
2. **Nunca aplicado sobre produção** — produção já está no estado que ele descreve.
3. Serve para: criar ambiente novo, rodar CI em banco efêmero e detectar drift.
4. Todo objeto do baseline é mapeado ao seu dono documental (SPEC de origem).
5. Objeto sem dono é marcado `ÓRFÃ` e resolvido antes do fechamento da SPEC-054.

---

## 7. Formato obrigatório de toda nova migration

```sql
-- =============================================================
-- MIGRATION: <slug>
-- SPEC:      SPEC-0NN — <bloco>
-- AUTOR:     <executor>            DATA: <YYYY-MM-DD>
-- OBJETIVO:  <uma frase>
--
-- APPLY:     <o que esta migration faz>
-- VERIFY:    <SQL read-only que prova que funcionou>
-- ROLLBACK:  <SQL de reversão, ou justificativa se irreversível>
--
-- EXPAND-FIRST: sim/não
-- DESTRUTIVA:   não        (se sim, exige decisão do Founder)
-- =============================================================
```

**Requisitos inegociáveis**

- **Idempotente:** `IF NOT EXISTS`, `CREATE OR REPLACE`, `ON CONFLICT DO NOTHING`.
- **Expand-first:** adicionar antes de remover. `DROP` nunca no mesmo bloco que cria.
- **FK em tabela grande:** `ADD CONSTRAINT ... NOT VALID` e depois `VALIDATE CONSTRAINT`.
- **`ON DELETE` consciente por tabela** — `CASCADE`, `RESTRICT` e `SET NULL` não são intercambiáveis.
- **VERIFY é SQL executável**, não texto descritivo.
- **ROLLBACK escrito antes de aplicar**, nunca depois.

---

## 8. Proibições

1. Aplicar `schema_completo.sql`, `upgrade_v6.2.sql` ou `storage_buckets.sql`.
2. Aplicar qualquer arquivo da classe `NÃO RASTREADA`.
3. Reaplicar arquivo da classe `APLICADA` ou `ISOLADA`.
4. Mover, renomear ou apagar migration antes do manifesto aprovado.
5. Aplicar o baseline sobre produção.
6. `DROP TABLE`, `DROP COLUMN` ou `TRUNCATE` em produção sem decisão explícita do Founder.
7. Remover índice apenas porque o advisor diz `unused` — banco jovem com pouco volume não autoriza remoção.
8. Alterar migration já aplicada. Corrigir sempre com migration nova.
9. Executar DDL fora de migration versionada — foi exatamente o que produziu as 9 versões órfãs do §4.
10. Deploy automático durante janela de migration crítica.

---

## 9. Sequência de segurança antes de qualquer write em produção

```text
registrar commit inicial
→ exportar DDL metadata-only atual
→ registrar advisors atuais
→ confirmar backup/point-in-time  (P1 — acesso pendente)
→ preferencialmente criar branch Supabase de desenvolvimento
→ aplicar em branch e validar
→ APPLY em produção
→ VERIFY
→ registrar advisors pós-mudança
→ canário Amandus → Resulta → AutoFleet
→ registrar commit final no relatório
```

O item de backup depende de **P1** em [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md). Enquanto estiver pendente, **nenhum write em produção é autorizado**.

---

## 10. Referências

- [`FOUNDER-DECISIONS.md`](FOUNDER-DECISIONS.md) — decisão **D2**
- [`EXECUTION-MASTER-PLAN.md`](EXECUTION-MASTER-PLAN.md) — Etapas 1 e 2
- [`specs/SPEC-054-foundation-hardening-schema-governance.md`](specs/SPEC-054-foundation-hardening-schema-governance.md) — §8.1, §11, §12
- [`audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md`](audits/AUDIT-SPEC-054-foundation-hardening-schema-governance-2026-07-24.md) — §5

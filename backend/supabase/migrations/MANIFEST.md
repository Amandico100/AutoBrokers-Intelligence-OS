---
> **Status:** canônico — manifesto de migrations
> **Autoridade:** [`docs/canon/MIGRATIONS-AUTHORITY.md`](../../../docs/canon/MIGRATIONS-AUTHORITY.md) · decisão **D2**
> **Última atualização:** 2026-08-08 (SPEC-067 LOTE 0 item 12)
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

---

## SPEC-067 — o acervo de condições gerais · registrado em 2026-08-08

### As tabelas do acervo — classificação medida, não deduzida

📊 Consultas read-only no projeto `dcajcvlzcjbmyapmklil` em 08/08/2026.

| Tabela | Versão no banco | Arquivo no repo | Classe |
|---|---|---|---|
| `normative_documents` | `20260725215808` `spec057_h1_normative_corpus` | **nenhum** | `SEM_ARQUIVO` |
| `normative_document_versions` | `20260725215808` `spec057_h1_normative_corpus` | **nenhum** | `SEM_ARQUIVO` |
| `knowledge_cards` | `20260719175618` `spec040_conduct_playbooks_cards` | `20260719_02_spec040_conduct_playbooks_cards.sql` | `APLICADA` |

**DDL reconstruído a partir do banco vivo:**
[`docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql`](../../../docs/canon/sql/reconstruidas/20260725215808_spec057_h1_normative_corpus.sql)
— material documental, **proibido aplicar** (MIGRATIONS-AUTHORITY §1).

> [!WARNING]
> **Um achado anterior sobre estas tabelas estava errado, e o erro pedia a ação
> perigosa.** Ele afirmava que elas "não têm versão em
> `supabase_migrations.schema_migrations`" — portanto seriam `ÓRFÃS` e
> precisariam de uma versão nova.
>
> 📊 A consulta, executada em 08/08/2026:
>
> ```sql
> select version, name from supabase_migrations.schema_migrations
>  where name ilike '%normative%' or name ilike '%corpus%';
> --  20260725215808 | spec057_h1_normative_corpus
> ```
>
> A versão **existe**. O que falta é o **arquivo**. Criar migration nova para
> objeto que já tem versão registrada duplicaria o histórico — e um histórico
> duplicado é pior que um histórico incompleto, porque o incompleto se percebe.
> `knowledge_cards`, no mesmo levantamento suspeita de órfã, tem arquivo **e**
> versão: é `APLICADA`, não precisa de nada.

### Migrations novas da SPEC-067 — 🔴 ESCRITAS, NÃO APLICADAS

| Arquivo | Objetivo | Estado |
|---|---|---|
| `20260808_01_spec067_a_vigencia_mora_na_versao.sql` | vigência SUSEP por versão + espelho no documento | ⬜ **não aplicada** |
| `20260808_02_spec067_o_indice_sabe_de_que_versao_veio.sql` | `qdrant_doc_id` por versão + backfill do esquema legado | ⬜ **não aplicada** |
| `20260808_03_spec067_a_carta_sabe_de_que_contrato_saiu.sql` | procedência em `knowledge_cards` | ⬜ **não aplicada** |
| `20260808_04_spec067_o_pdf_e_o_texto_tem_endereco.sql` | ponteiros do PDF e do texto no MinIO | ⬜ **não aplicada** |

**Ordem de aplicação obrigatória: 01 → 02 → 03 → 04.** A 02 depende da coluna
que a 01 não cria (são independentes no schema) mas o backfill da 02 lê
`version`, que a 01 não altera — a ordem é por legibilidade do histórico, não
por dependência de DDL. Cada uma é idempotente e pode rodar sozinha.

Nenhuma delas foi aplicada por quem as escreveu. **Quem aplica é o Founder**,
depois de revisar, seguindo a sequência da MIGRATIONS-AUTHORITY §9.

### Duas classificações a mais, encontradas no caminho

| Arquivo | Situação | Classe |
|---|---|---|
| `20260728_03_curadoria_das_cartas.sql` | sem versão no banco; 📊 o arquivo **não contém SQL executável** — é 100% comentário documentando um APPLY feito por `backend/scripts/curar_cartas.py` em 28/07 | `DOCUMENTAL` — proibido "aplicar", não há o que aplicar |
| `20260725_04_spec054_a3_storage_privacy.sql` | o MANIFEST de 25/07 o marcava `PENDENTE`; 📊 hoje `20260725070738 spec054_a3_storage_privacy` **está** em `schema_migrations` | `APLICADA` — a linha acima está vencida |

> **INFERÊNCIA, não fato:** um cruzamento automático nome-a-nome de todos os 92
> versionamentos contra os 60 arquivos apontou dezenas de divergências, mas o
> casamento por nome é pouco confiável (o arquivo
> `20260803_01_spec063_destino_de_suporte_unico.sql` corresponde à versão
> `spec063_01_destino_de_suporte_unico`, e nenhuma regra simples liga os dois).
> **Não conte esse número como medição.** A reconciliação completa é trabalho da
> SPEC-054 Bloco B. O que está afirmado como FATO acima é só o que foi
> conferido tabela a tabela contra o catálogo do Postgres.

---

## Checksums

Os `sha256` de cada arquivo histórico estão registrados em [`docs/canon/MIGRATIONS-AUTHORITY.md`](../../../docs/canon/MIGRATIONS-AUTHORITY.md) §3 e servem como linha de base de integridade.

---

## Aplicadas em 08/08/2026 — SPEC-070 LOTE 0

Aplicadas via MCP no projeto `dcajcvlzcjbmyapmklil`, uma a uma, com o VERIFY de
cada uma rodado antes de seguir para a seguinte. Todas **aditivas**: nenhuma
coluna existente foi alterada, nenhuma linha foi tocada.

| versão | arquivo | o que acrescentou | VERIFY |
|---|---|---|---|
| `spec070_01_a_vigencia_mora_na_versao` | `20260808_01_spec070_…` | 5 colunas de vigência em `normative_document_versions`, 2 CHECKs, o índice único que impede duas versões abertas, e os COMMENTs que declaram as colunas do documento como espelho | ✅ 6/6 |
| `spec070_02_o_indice_sabe_de_que_versao_veio` | `20260808_02_spec070_…` | `qdrant_doc_id` e `qdrant_collection` + backfill das 29 linhas | ✅ 5/5 |
| `spec070_03_a_carta_sabe_de_que_contrato_saiu` | `20260808_03_spec070_…` | 3 colunas de procedência em `knowledge_cards` + 3 FKs validadas + 2 índices parciais | ✅ 4/4 |
| `spec070_04_o_pdf_e_o_texto_tem_endereco` | `20260808_04_spec070_…` | 4 colunas de arquivo + índice das versões sem original guardado | ✅ aplicada |

### 📊 O controle, medido depois de todas

```
normative_documents ....... 35    (intacto)
normative_document_versions 29    (intacto, 29 com qdrant_doc_id transcrito)
knowledge_cards ........... 12.933 (intacto)
  published ............... 12.063 (intacto)
  com procedência ......... 0      ← e é o certo
```

**Zero cartas ganharam procedência.** As 12.933 vieram de conversas de
atendimento, não de contrato — inventar de qual documento saíram seria pior que
admitir que não se sabe. O VERIFY da migration 03 tem uma linha que **falha** se
alguém preencher.

### O que estas quatro destravam

Sem elas, o LOTE 1 (Porto) guardaria o contrato **sem saber de que versão veio**,
sem o PDF original, e as cartas nasceriam órfãs de origem — repetindo em 2026 o
defeito que hoje deixa 12 de 13 documentos revogados no índice sem ninguém
perceber.

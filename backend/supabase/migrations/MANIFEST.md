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
| `spec097_episodio_tem_conversa` | `20260905_01_spec097_episodio_tem_conversa.sql` | SPEC-097 U3.1: `attendance_sessions.conversation_id` (FK composta com `company_id`, ON DELETE SET NULL), `resolvido_em`, `resolucao_motivo` (mesmo CHECK da conversa) + 2 índices · 📊 aplicada em 05/09/2026, V1/V1.b/V2/V3 ok | ✅ 4/4 |
| `spec0971_follow_up_contrato` | `20260905_02_spec0971_follow_up_contrato.sql` | SPEC-097.1 U3.3: data migration — `auxiliary_templates.default_config` do `follow-up-whatsapp` ganha `contrato {gatilho: manual, le_espera: true, envia: false}` (jsonb `||`, idempotente) · 📊 aplicada em 06/09/2026, VERIFY `tem=true` | ✅ 1/1 |
| `spec098_de_quem_e` | `20260906_01_spec098_de_quem_e.sql` | SPEC-098 U2.1/U5.a: `brand_profiles.tone_proposto` + `_origem` + `_em` + `tone_evidencia` (a proposta R2, separada do `tone` ATIVO, que ganhou COMMENT); `artifacts.conversation_id` e `approval_requests.conversation_id`, ambas com **FK COMPOSTA** `(conversation_id, company_id) → conversations(id, company_id) ON DELETE SET NULL (conversation_id)` + índice parcial; COMMENT em `user_memories.user_id` (D22 — a população é o SEGURADO); limpeza D21 de `brand_field_provenance` (📊 2 linhas apagadas, 14 → 12) · 📊 aplicada em 06/09/2026, V1/V1b/V2/V2.b/V3/V4/V5 ok, advisors de segurança 133 → 133 | ✅ 7/7 |
| `spec098_indice_cobre_a_fk` | `20260906_02_spec098_indice_cobre_a_fk.sql` | SPEC-098 correção medida da 01: 📊 `get_advisors performance` logo após o APPLY acusou `unindexed_foreign_keys` nas DUAS FKs novas — `(company_id, conversation_id)` não cobre uma FK que se procura por `conversation_id`. Os dois índices renascem como `ix_*_conversa_fk (conversation_id, company_id)` parciais e os antigos caem (expand-first, na ordem) · 📊 aplicada em 06/09/2026, V1/V2 ok | ✅ 2/2 |
| `spec_extra001_billing_sent_log_estados` | `20260907_01_spec_extra001_billing_sent_log_estados.sql` | SPEC-EXTRA-001 U1: `billing_sent_log` ganha 20 colunas aditivas (estado por componente — `status`, `text_ok`, `doc_ok`; destino — `to_phone`/`to_last4`; procedência — `integration_id`, `work_run_id`, `routine_id`; tempo — `reserved_at`/`sent_at`/`updated_at`/`attempts`; humano — `encaminhado_ao_cliente_em`/`encaminhado_por`/`motivo`; retorno do cliente; `canario`), o índice único **parcial** `billing_sent_log_obrigacao_uniq (company_id, portal_key, recibo) WHERE send_mode='real'` (a identidade da obrigação não depende de modo, dia nem run), `billing_sent_log_to_phone_idx`, e as duas funções da reserva atômica `billing_reservar_obrigacao` / `billing_reclamar_obrigacao` (o `ON CONFLICT` de índice parcial exige repetir o predicado, e o PostgREST não o expressa → 42P10) · 📊 tabela com **0 linhas** em 07/09/2026, sem backfill · 📊 **aplicada em 07/09/2026** com VERIFY V1–V5 (relatório da EXTRA-001 §4; a função `billing_reservar_obrigacao` de 12 args conferida VIVA por `pg_get_functiondef` em 13/09/2026 — esta linha dizia "pendente" até a EXTRA-001.6 corrigir) | ✅ aplicada |
| `spec_extra0016_cobranca_por_segurado` | `20260914_01_spec_extra0016_cobranca_por_segurado.sql` | SPEC-EXTRA-001.6 B1.4: `billing_sent_log.segurado_chave` (text, nula, com COMMENT — "doc:", "nome:" ou "recibo:"; o nome NÃO é `cpf_cnpj` porque nem sempre É um documento), o índice **parcial** `billing_sent_log_segurado_idx (company_id, segurado_chave, sent_at DESC) WHERE send_mode='real'` (a janela de 1 cobrança por segurado a cada N dias, D-PILOTO-18), e a **SOBRECARGA** de 13 argumentos de `billing_reservar_obrigacao` — sem DEFAULT no 13º, porque com default a chamada de 12 casaria com as duas e o Postgres devolveria **42725** na hora de reservar; a de 12 argumentos FICA (cai numa migration posterior, P-E0016-RESERVA-12-ARGS) · 📊 tabela com **0 linhas** em 13/09/2026, sem backfill · 📊 **aplicada em 14/09/2026 01:35 UTC** (MCP `apply_migration`, versão `spec_extra0016_cobranca_por_segurado`) com VERIFY V0–V6 rodado no Postgres real: corpo de 13 args com `unique_violation` + `colisao_recibo` + `ON CONFLICT … WHERE send_mode` + `segurado_chave` (114 chars a mais que o de 12); coluna `text` nula; índice parcial com o predicado; 2 assinaturas; reserva grava `doc:…` e a 2ª perde com o MESMO id; a de 12 args ainda resolve e grava NULL; `test`=0 · advisors de segurança 133 → 133, desempenho 314 → 315 (o índice novo entra em `unused_index`, esperado numa tabela vazia — MIGRATIONS-AUTHORITY §8.7) · 2 linhas de VERIFY apagadas por recibo, ledger de volta a 0 | ✅ 6/6 |
| `spec_extra0016_redigir_output_full` | `20260914_03_spec_extra0016_redigir_output_full.sql` | SPEC-EXTRA-001.6 B4.4: **UPDATE de redação** sobre `routine_runs.output_full` — apaga o CPF/CNPJ e o telefone do segurado dos relatórios de execução da cobrança JÁ gravados, por duas `regexp_replace` (`'(CPF/CNPJ[: ]*)[0-9][0-9./-]{9,17}'` e `'(WhatsApp: )[0-9]{8,15}'`), sobre uma **lista de ids fixada por um SELECT rodado antes** (🔴 nunca `where like` aberto: entre a medição e o UPDATE a rotina pode executar de novo e o número afetado deixa de ser o número medido) · 📊 **7 de 49** execuções com `CPF/CNPJ` em `output_full`, **6** com dígitos de documento — medido em 13/09/2026 (`select count(*) from routine_runs r join routines t on t.id=r.routine_id where t.config->>'kind'='billing_collection' and r.output_full like '%CPF/CNPJ%'`) · 🔴 **DESTRUTIVA e IRREVERSÍVEL por construção**: o ROLLBACK não existe porque desfazer exigiria guardar uma SEGUNDA cópia do CPF do segurado dentro do banco; o que o substitui é o `md5(output_full)`+`length` de ANTES, colhido pelo SELECT e colado no relatório (⛔ nunca o `output_full` em si). A informação não se perde: documento e telefone continuam na InfoCap e em `billing_sent_log.to_phone` · IDEMPOTENTE (as duas regexes exigem um dígito depois do rótulo, e depois da 1ª passada não sobra nenhum — o formato novo `CPF/CNPJ ...0272` também não casa) · VERIFY V0–V4 com **dois controles**: V3 prova que `WhatsApp: sem telefone (...)` NÃO foi tocado e V4 que a seção "Clientes encontrados" continua inteira · ⚠️ entra na **Implantação 2** (proposta §15.1), junto da `20260914_01` e antes da `20260914_02` | 📊 **aplicada em 14/09/2026 ~01:50 UTC** (MCP `apply_migration`) sobre 6 ids fixados por SELECT (md5/tamanho de antes no relatório §4); VERIFY V0=0 · V1=0 · V2=0 · V3=7 (explicações intactas) · V4=7 (relatórios inteiros) · 6 linhas com `CPF/CNPJ •••` · ⚠️ `routine_runs` não tem `created_at`: o SELECT usa `started_at` | ✅ 5/5 |
| `spec_extra0016_redigir_output_preview` | `20260914_04_spec_extra0016_redigir_output_preview.sql` | SPEC-EXTRA-001.6 CONSERTO rodada 1 (achado A-1 da lente do dado): a `_03` limpou **`output_full`** e ninguém perguntou pela OUTRA coluna — 🔴 a tela lê as duas (`app/dashboard/entregas/rotina/[runId]/page.tsx:140`, `completo || output_preview`), e `routine_engine.py:348` grava `output_preview = output[:500]`. 📊 **5** execuções de cobrança com `CPF/CNPJ <dígitos>` ou `WhatsApp: <dígitos>` em `output_preview`, **4 delas com `output_full` NULL** — ou seja, PII de segurado **em claro na tela hoje** (medido em 14/09/2026; ids8: `ce166b0e`, `17dfd8a9`, `55eef75e`, `fddfe92d`, `89e1c389`). Mesmo formato da `_03`: lista de ids fixada por SELECT antes do APPLY (nunca `where ~` aberto), as MESMAS duas `regexp_replace`, DESTRUTIVA e IRREVERSÍVEL por construção, IDEMPOTENTE. VERIFY V0–V5 com os dois controles da `_03` **mais o V5 que faltou nela**: um SELECT que varre `output_full` E `output_preview` JUNTOS (a pergunta certa é "sobrou PII de cobrança em `routine_runs`, em qualquer coluna?"). ⚠️ Não reinfecta: o preview nasce do MESMO texto que `_format_report` agora mascara (G12/M12), e não há segundo escritor. ⚠️ `routine_runs` não tem `created_at`: o SELECT usa `started_at` | 📊 **aplicada em 14/09/2026 ~02:50 UTC** (MCP) sobre 5 ids fixados por SELECT (md5/tamanho no relatório §4); VERIFY V0=1 → o resto cortado de um telefone (5 dígitos no fim de um preview de 500 chars) fica para a `_05`; V1=0; V4=5 com rótulo, 5 mascarados | ✅ (com a _05) |
| `spec_extra0016_redigir_preview_cortado` | `20260914_05_spec_extra0016_redigir_preview_cortado.sql` | SPEC-EXTRA-001.6 B4.4, complemento da `_04`: o `output_preview` (`output[:500]`) cortou um telefone no meio — 5 dígitos no fim do texto que a regex `{8,15}` não pega; UPDATE numa linha ancorado em `$`, idempotente, sem rollback (mesma justificativa) · 📊 aplicada em 14/09/2026 (MCP); VERIFY V0 e V5 da `_04` = 0 | ✅ 2/2 |

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

---

## SPEC-EXTRA-001.1 — BLOCO E (14/09/2026)

### A migration de DADO

| versão | arquivo | classe | o que faz | VERIFY |
|---|---|---|---|---|
| `spec_extra0011_llm_max_tokens` | `20260914_06_spec_extra0011_llm_max_tokens.sql` | **APLICADA** em 14/09/2026 (`spec_extra0011_llm_max_tokens`, MCP; RLS da tabela de backup ligado numa 2ª passada da mesma migration, depois do advisor) | SPEC-EXTRA-001.1 BLOCO E (P-PILOTO-17): migration de **DADO**, não de DDL. `UPDATE public.agents SET llm_max_tokens = 8192` nos papéis `core`/`attendance` que estavam abaixo disso, com a tabela de backup `agents_llm_max_tokens_backup_extra0011` guardando o valor ANTERIOR **por `agent_id`** (é a única fonte do ROLLBACK, e ela NÃO é apagada por ele). Nenhuma coluna criada, alterada ou removida; nenhum `DEFAULT` de schema tocado. **Expand-first** (a rede nasce antes do UPDATE) e **idempotente** (`on conflict (agent_id) do nothing` — sem ele, a 2ª passada transformaria a rede numa cópia do estado novo e o ROLLBACK passaria a "restaurar" 8192 em silêncio) | V0–V5 **rodados em 14/09/2026** (saída colada abaixo e no relatório §5); versão aplicada no banco: **`20260914072141`** (o nome do arquivo é `20260914_06_…` — a versão é a do `apply_migration` do MCP, registrada aqui para o cruzamento arquivo × versão do §2 da autoridade). ⚠️ A tabela de backup tem RLS ligado e **zero policies**: só o service role a lê — é rede de rollback, não superfície de leitura humana |

**📊 O manifesto que esta migration exige é o INVENTÁRIO das linhas afetadas —
antes e depois** (MIGRATIONS-AUTHORITY §5 vale integralmente para alteração de
*schema*; esta não altera schema). Medido em 13/09 e reconferido em 14/09/2026
(`select agent_role, llm_max_tokens, count(*) from public.agents group by 1,2
order by 1,2`), **sem PII — só papel, valor e contagem**:

```
ANTES     (attendance, 1200, 1)  (attendance, 2000, 3)
          (core,       1200, 3)  (core,       2000, 1)      = 8 agentes
DEPOIS    (attendance, 8192, 4)  (core,       8192, 4)      = 8 agentes   <- o esperado do V1
```

📊 **VERIFY real (14/09/2026, depois do APPLY):**

```
V0 antes   (attendance,1200,1) (attendance,2000,3) (core,1200,3) (core,2000,1) · alvos = 8 · backup não existia
V1         (attendance, 8192, 4)  (core, 8192, 4)
V2         linhas_guardadas = 8 · ja_era_8192 = 0
V3         (1200, 4)  (2000, 4)
V4         NENHUMA LINHA (só core/attendance na base)
V5         companies: (2000, 5)  — intacta
G-MIG 2    APPLY rodado 2× → linhas_guardadas 8 · ja_era_8192 0 · em_8192 8 (idempotente)
G-MIG 3    ROLLBACK exercitado em produção (produto pausado): (1200→1200, 4) (2000→2000, 4), um a um por agent_id;
           APPLY reaplicado → V1/V2/V3 iguais aos de cima. A tabela de backup NÃO foi apagada.
Advisor    security depois do 1º APPLY: +1 ERROR `rls_disabled_in_public` na tabela de backup → RLS ligado
           (relrowsecurity = true); os demais achados são os pré-existentes (122 INFO, 2 views definer, 3 funções).
```

⚠️ **Se a contagem do dia do APPLY não bater com o ANTES, pare.** Alguém mexeu
entre a medição e a aplicação, e o inventário acima deixou de ser o inventário
real — o ROLLBACK por `agent_id` continua correto, mas este quadro mentiria.

⚠️ **`companies.llm_max_tokens` NÃO entra** (decisão **D-E0011-01**, nota 70 ×
55). 📊 14/09: `2000` em **5 de 5** corretoras, com 2 leitores —
`llm_factory.py:102` (fallback de **qualquer** papel, inclusive `auxiliary` e
`subagent`, que mantêm teto baixo de propósito) e `agent_config.py:288` (a
tela). Subi-la elevaria o teto de auxiliar e subagente sem mudar um byte do que
chega a alguém. **O V5 é o controle que reprova o gate se algum `8192` aparecer
em `companies`.**

⚠️ **Os `DEFAULT 2000` de DDL não são tocados** — `schema_completo.sql:454`
(agents) e `:581` (companies). São `ALTER` de estrutura, exigem manifesto
completo e seriam uma **segunda** migration, nunca um `ALTER` pendurado nesta.
Ficam registrados como **`P-E0011-DEFAULT-DDL-2000`**. Os defaults de **código**
— que são os que de fato escrevem hoje — foram a 8192 no mesmo commit:
`backend/app/api/agent_config.py:82/:133/:288`, `backend/app/models/agent.py:19`
e `app/api/admin/sandbox/bootstrap-tenant/route.ts:106` (este era **1200**).

### `tool_invocations` — a DDL que nunca entrou no histórico

| tabela | classe | por quê |
|---|---|---|
| `public.tool_invocations` | **`NÃO RASTREADA`** (sem arquivo e sem versão; a estrutura **existe** em produção) | 📊 `20260816_02_spec075_portal_job_lineage_priority.sql:147` registra, com todas as letras, que *"a DDL de `tool_invocations` não está rastreada no repositório"*; `20260727_04_indices_read_models_061.sql:24` diz "JA EXISTIA" ao criar índice sobre ela. 📊 Em 14/09/2026 a tabela tem **277 linhas** (140 desde 09/09) e o chat grava nela por `nodes.py:1057 → invocation_recorder → gateway.py:294` |

🔴 **Esta entrada é DOCUMENTAL: nenhuma DDL nova é escrita, e é proibido
"aplicar" qualquer coisa por causa dela** (MIGRATIONS-AUTHORITY §3.3 e §8.2). O
que ela faz é responder "este objeto já existe?" — que é a pergunta deste
arquivo. A reconciliação completa continua sendo trabalho da SPEC-054 Bloco B.

📊 **DDL real, lida do catálogo do Postgres em 14/09/2026** (BLOCO 0 §1.2,
premissa 12 — `information_schema.columns`, `pg_constraint`, `pg_indexes`):

```
colunas   id uuid PK · company_id uuid NOT NULL FK companies ON DELETE CASCADE
          work_run_id uuid · work_step_id uuid · work_attempt_id uuid
          skill_release_id uuid FK skill_releases ON DELETE SET NULL
          tool_release_id  uuid FK tool_releases  ON DELETE RESTRICT
          capability_key text · agent_id uuid · user_id uuid · connection_id uuid
          invocation_key text · status text · input_fingerprint text
          input_summary jsonb · output_summary jsonb · provider_reference text
          approval_request_id uuid
          work_effect_id uuid FK work_effects ON DELETE SET NULL
          started_at timestamptz · finished_at timestamptz · latency_ms integer
          cost_amount numeric · currency text · error_code text · trace_id text
          created_at timestamptz
travas    UNIQUE (company_id, invocation_key)  `uq_tool_invocations_key`
          CHECK status IN (running, succeeded, failed, denied, skipped, waiting_approval)
índices   idx_tool_invocations_company        (company_id, started_at DESC)
          idx_tool_invocations_negadas        (company_id, started_at DESC) WHERE status='denied'
          idx_tool_invocations_run            (work_run_id)
          idx_tool_invocations_tool           (tool_release_id, status)
          ix_tool_invocations_company_recente (company_id, created_at DESC)
```

⚠️ **E o que a SPEC-EXTRA-001.1 fez nela SEM DDL:** a ligação com o turno do
chat passa a viver em **`trace_id`**, que já existia e 📊 **não tinha nenhum
leitor** em 14/09 (`grep -rn "trace_id" backend/app --include=*.py` → 6
ocorrências, todas de ESCRITA). O formato passou de `session_id` para
`"<session_id>|<client_request_id>"`. **Coluna que já existe, escritor que já
existe, zero DDL** — e por isso esta SPEC continua tendo **uma única
migration**, a de dado (GATE G-MIG item 5).

⛔ **`input_summary` continua sem argumento cru.** 📊 14/09: das 277 linhas, **0**
têm 11 dígitos seguidos em `input_summary`; a amostra das 40 últimas de
`operational.infocap.policy_lookup.read` guarda só as CHAVES (`document`,
`user_query`, `policy_number`, `document_evidence_requested`). Quem garante isso
é `invocation_recorder.resumo_da_entrada`, e o guarda
`test_a_ferramenta_do_turno_deixa_rastro.py` fica **vermelho** se alguém gravar
`tool_args` cru.

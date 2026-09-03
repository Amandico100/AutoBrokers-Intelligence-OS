# SPEC-095 — ARTIFACT & DELIVERY HUB COMPLETION
## Entregas deixa de ser uma timeline de coisas que aconteceram e vira a biblioteca confiável de tudo que o AutoBrokers realmente produziu, entregou e consegue provar

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANDIDATE SPEC — pronta para aquecimento/refutação pelo Protocolo AutoBrokers AAA v9; ainda não executada  
**Data da redação:** 31/08/2026  
**Baseline de `main` confirmado:** `46e6a49bccf5be89f7f02e7a6120d984b4740bae`  
**Branch sugerida:** `feat/spec095-artifact-delivery-hub-completion`  
**Origem:** conclusão deliberada da promessa da SPEC-057 + correções da SPEC-078 + necessidade ampliada pelas SPECS 081/094 e pelas próximas fábricas  
**Autoridades superiores:** SPEC-052, 053, 055, 056, 057, 058, 059/064, 078, 081, Candidate 086, 090, 091, 093, 094 e Protocolo AAA v9  
**Autoridades preservadas:** Artifact identity/version/render/share/event, Work Run, Skill Registry, Tool Gateway, Capability Registry, Vault, canais existentes, MinIO, Supabase, Smith e Brand Fabric  
**Prepara:** SPEC-096 Chat Runtime Performance & Interaction Shell; SPEC-097 Operations Workspace; SPEC-100 Skill Factory; SPEC-103 Auxiliary Marketplace; SPEC-109 AutoBrokers Engine  
**Research Pack:** `SPEC-095-artifact-delivery-hub-completion-RESEARCH-PACK.md`

---

# LEGENDA

- 🔒 **frozen** — decisão de arquitetura/produto.
- 📊 **measured** — medido/reproduzido.
- 🔎 **repo observed** — observado no repo.
- 🌐 **external** — referência externa.
- 💭 **hypothesis** — validar no warm-up.
- ⚠️ **debt** — legado aceitável temporariamente.

# 0. RESULTADO EM UMA FRASE

> **Se o AutoBrokers fez algo por você, existe um lugar único e rápido onde você encontra o resultado, abre a versão exata, entende quem/qual trabalho o produziu, confere fontes e data dos dados, baixa no formato certo, compartilha com controle, sabe o que foi enviado, o que falhou e — quando existe evidência confiável — o que foi aberto, sem confundir publicação com entrega nem acesso com leitura.**

```text
PEDIDO / ROTINA / AUXILIAR / PESQUISA / INTELIGÊNCIA
                         ↓
                      WORK RUN
                         ↓
                      ARTIFACT
                         ↓
                IMMUTABLE VERSION
                         ↓
          ┌──────────────┼───────────────┐
          ↓              ↓               ↓
        WEB/PDF       XLSX/CSV       OUTROS RENDERS
          └──────────────┼───────────────┘
                         ↓
                    PUBLISHED
                         ↓
             ENTREGAS — RESULTADOS
                         ↓
         ┌───────────────┼─────────────────┐
         ↓               ↓                 ↓
      DOWNLOAD         SHARE             SEND
                         ↓                 ↓
                 SHARE ACCESS        DELIVERY ATTEMPT
                         ↓                 ↓
                  VIEW EVENTS        CHANNEL RECEIPTS
                         └────────┬────────┘
                                  ↓
                         ACTIVITY / AUDIT
```

# 0.1 BIG IDEA

A pergunta não é “tem um arquivo?”.

É:

# **“Depois que o AutoBrokers terminou um trabalho, ele realmente entregou valor de uma forma que a corretora consegue encontrar, reutilizar, compartilhar e provar?”**

# 0.2 DE ONDE VEIO

## SPEC-057

Já definiu a visão correta:

```text
resposta/análise/pesquisa/dados/evidência
→ Artifact profissional
→ versão
→ render
→ armazenamento
→ publicação
→ compartilhamento
→ entrega
→ histórico
```

Prometeu Artifact de primeira classe, versões imutáveis, múltiplos formatos, provenance, links expirados/revogáveis, downloads auditados, dashboard, WhatsApp, e-mail e Artifact Library.

## SPEC-078

Depois surgiu a dor literal:

> “eu não consigo acessar as coisas que ficam prontas.”

A auditoria mediu:

```text
36 artifacts ........ href null
77 briefings ........ href errado
135 activities ...... sem destino
32 routine_runs ..... invisíveis
```

A 078 fez o conserto emergencial certo: agora as entregas têm porta.

A 095 termina a promessa: a porta vira **biblioteca + last mile confiável**.

# 0.3 O QUE JÁ EXISTE E É BOM

🔎 Fundação:

```text
artifacts
artifact_versions
artifact_renders
artifact_shares
artifact_events
report_templates
report_template_releases
```

🔎 `ArtifactService` já tem:

```text
criar
nova_versao
renderizar
publicar
compartilhar
revogar
abrir_compartilhado
listar
```

Preservar:
- versão publicada imutável;
- brand snapshot congelado;
- share com expiração;
- token forte;
- max views;
- revogação;
- event log append-only;
- tenant isolation;
- public route CSP/noindex;
- iframe sem scripts.

# 0.4 O GAP PRINCIPAL

Hoje há três conceitos misturados:

```text
RESULTADO
relatório / dossiê / briefing / dataset

TRABALHO
Work Run / routine run / auxiliary run

HISTÓRICO
conversa / agent activity / eventos
```

A timeline unificada foi boa para limpar o menu, mas:

> **“o que aconteceu?” não é “onde está o que foi entregue?”**

# 0.5 UM MENU, DUAS LENTES

🔒 Continuar com um único menu:

# **ENTREGAS**

Dentro:

```text
RESULTADOS   ← default
ATIVIDADE
```

### RESULTADOS
Coisas que o usuário consegue abrir, baixar, reutilizar, compartilhar, comparar e pedir novamente.

### ATIVIDADE
Work Runs, rotinas, auxiliares, conversas e eventos que explicam o que aconteceu.

Não criar outro item de menu.

# 0.6 NÃO CRIAR MINI-SHAREPOINT

Notion/Drive ensinam Recents, Favorites, Shared, Archived, search e filters.

Não copiar árvore infinita de folders.

O AutoBrokers já conhece:
```text
cliente
seguradora
apólice
Work Run
Auxiliar
rotina
período
assunto
```

Usar contexto para organização automática.

# 0.7 FIGMA — UM OBJETO, MUITAS VERSÕES

Padrão adotado:

```text
Artifact = identidade lógica
Version = snapshot imutável
Current Published = atual
Specific Version = prova de um ponto no tempo
```

“Restaurar” nunca destrói history.

# 0.8 DOCSEND — O ENVIO NÃO VAI PARA UM BURACO NEGRO

Absorver:
- links controlados;
- expiration;
- password/email verification quando cabível;
- download control;
- access/view history;
- atualização controlada;
- clean viewer.

Com rigor maior por ser seguros.

# 0.9 LINEAR — A UX PRECISA SER RÁPIDA

A Library deve parecer:
```text
rápida
densa
óbvia
```
não um ECM pesado.

# 0.10 RESULTADO É OBJETO, NÃO ARQUIVO

🔒

```text
Artifact
 ├─ v1
 │  ├─ web
 │  └─ pdf
 ├─ v2
 │  ├─ web
 │  ├─ pdf
 │  └─ xlsx
 └─ shares / deliveries / events
```

# 0.11 PUBLISH ≠ SEND ≠ DELIVER ≠ OPEN

🔒

```text
PUBLISHED = disponível no AutoBrokers
QUEUED = pedido de envio registrado
SENT = canal/provedor aceitou conforme evidence real
DELIVERED = receipt verificável do canal
OPENED = acesso qualificado ao artifact/link
READ = NÃO inferir automaticamente
```

Nunca:

```text
GET /r/token → “cliente leu”
```

# 0.12 RAW HIT ≠ HUMAN OPEN

Links podem ser acessados por:
- security scanner;
- unfurl;
- preview;
- bot;
- navegador humano.

Engagement precisa de classificação/confidence.

# 0.13 ESTADO ATUAL DO DOWNLOAD

📊 Hoje o botão Baixar entrega o HTML como `.html`.

📊 A 078 mediu 36/36 renders em HTML e zero `storage_ref`.

A 095 torna formato uma capability real.

# 0.14 GAP DA PROMESSA DE FORMATOS

057 prometeu HTML/PDF/XLSX/CSV/PPTX/DOCX/SVG/PNG.

Schema atual aceita:
```text
html pdf png markdown whatsapp_text email_html csv
```

Serviço real gera HTML.

🔒 Criar **Format Capability Matrix**.

V1 obrigatória:
```text
WEB/HTML
PDF
CSV
XLSX
```

quando o Artifact kind suportar.

DOCX/PPTX: auditar infraestrutura. Se não houver renderer robusto:
```text
NOT_SUPPORTED_YET
```
e registrar conscientemente.

# 0.15 PDF

Preferência:
```text
canonical HTML
→ Chromium/Playwright print
→ PDF
```
se warm-up provar viável.

Mesma versão, mesmo conteúdo, checksum, page count, storage privado.

# 0.16 XLSX/CSV

Para artifact tabular:
```text
Version payload
→ tabular contract
→ XLSX/CSV
```

Sem LLM escrevendo matemática ad hoc.

# 1. OBJETIVOS

1. Aumentar valor percebido do trabalho já feito.
2. Reduzir “onde está o relatório?”.
3. Permitir reuso em operação/reuniões.
4. Facilitar envio controlado.
5. Criar histórico durável.
6. Fazer resultado virar ativo da corretora.
7. Permitir Core encontrar resultado anterior.
8. Provar falha/sucesso da última milha.
9. Preparar Engine/API.
10. Impedir outputs valiosos de sumirem no chat.

# 2. PERGUNTAS QUE O USUÁRIO DEVE CONSEGUIR FAZER

```text
“Abra o relatório comercial de agosto.”
“Cadê o Pulso 360 da semana passada?”
“Baixe em PDF.”
“Me mande a planilha.”
“Compartilhe com a diretoria por 7 dias.”
“Esse link foi aberto?”
“Qual versão eu mandei para o cliente?”
“Compare a versão 2 com a atual.”
“Arquive os antigos.”
“Mostre só o que falhou na entrega.”
```

# 3. NÃO OBJETIVOS

Não criar:
- Google Drive completo;
- SharePoint;
- editor colaborativo genérico;
- filesystem;
- novo document engine;
- novo Work Run;
- novo e-mail provider;
- novo WhatsApp runtime;
- storage paralelo;
- collaboration suite;
- approval engine paralelo;
- knowledge base paralela.

# 4. ONTOLOGIA

Preservar:
```text
Artifact
Artifact Version
Artifact Render
Artifact Share
Artifact Event
```

Completar, somente se não houver authority equivalente:
```text
Artifact Delivery
Artifact Engagement classification
Artifact User Preference
```

# 5. ARTIFACT VS VERSION

Artifact = identidade lógica durável.

Nova **Version** quando é a mesma entrega lógica corrigida/atualizada.

Novo **Artifact** quando é um resultado lógico diferente.

Warm-up define identity/dedupe rules por kind/template.

# 6. RESTORE NÃO DESTRUTIVO

“Restaurar v2”:
```text
v2 → copy payload/composition → new v5 → publish
```

Nunca reescrever histórico.

# 7. RENDER

```text
Version 4
 ├─ html
 ├─ pdf
 ├─ xlsx
 └─ csv
```

Cada render tem:
- status;
- checksum;
- storage/content;
- byte size;
- page/sheet count;
- duration;
- error.


# 8. SHARE MODES

🔒 `Artifact Share` precisa distinguir:

```text
FROZEN_VERSION
LIVE_ARTIFACT
```

## 8.1 FROZEN_VERSION

Default para:
- cliente;
- segurado;
- seguradora;
- parceiro externo;
- evidência;
- entrega formal.

Aponta para `artifact_version_id` e nunca muda.

## 8.2 LIVE_ARTIFACT

Opcional e explícito.

Resolve a versão publicada mais recente no momento do acesso.

Bom para:
- diretoria interna;
- working report;
- acompanhamento recorrente.

UI precisa dizer claramente:
> “Este link mostra sempre a versão publicada mais recente.”

## 8.3 MUTATION CRÍTICA

Cliente recebeu v2; v3 foi publicada; token FROZEN começa a mostrar v3.

**FAIL.**

# 9. SHARE POLICY

Controles desejados:

```text
mode
expires_at
audience
max_views
allow_download
password_required?
email_verification?
recipient_binding?
white_label
revocable
```

Auditar schema/serviço atual antes de migration.

# 10. PASSWORD

Schema atual já possui `password_hash`.

Warm-up deve provar se existe fluxo real de criar/verificar senha.

🔒 Se a ponta a ponta não existe:
```text
capability = unavailable
```

Nunca plaintext.

# 11. EMAIL VERIFICATION / RECIPIENT BINDING

Níveis possíveis:

```text
PUBLIC_TOKEN
TOKEN + PASSWORD
TOKEN + VERIFIED_EMAIL
AUTHENTICATED_GUEST
```

Não construir auth externo gigantesco nesta SPEC.

Usar apenas o nível necessário ao risco.

# 12. DOWNLOAD CONTROL

Share pode permitir view e desabilitar botão de download.

⚠️ Isso não é DRM; screenshot/cópia continuam possíveis.

A UI não promete proteção absoluta.

# 13. ARTIFACT DELIVERY

🔒 Delivery é ledger/orchestration de última milha.

Não é novo sender.

Referencia caminhos existentes:
```text
dashboard
email service
WhatsApp governed sender
share link
```

# 14. POR QUE PRECISA DE UMA AUTORIDADE DE DELIVERY

Hoje status vive fragmentado:
- `briefing_publications.delivery_status`;
- briefing DeliveryExecutor;
- routine/auxiliary results;
- channel send logs;
- share events.

Busca atual não encontrou `artifact_delivery`.

Warm-up precisa provar novamente no código e no banco antes de migration.

# 15. DELIVERY GROUP

Uma ação pode gerar vários attempts:

```text
“entregue à diretoria”
↓
dashboard
email A
email B
whatsapp C
```

Todos ligados a:
```text
delivery_group_id
```

# 16. DELIVERY ATTEMPT — CONTRATO CONCEITUAL

```text
id
company_id
artifact_id
artifact_version_id
delivery_group_id

channel
recipient_ref / recipient_hash / audience_label
integration_id / connection_id

status
provider_message_ref?
share_id?

requested_by
work_run_id
approval_request_id?

idempotency_key

queued_at
sent_at
delivered_at
failed_at
last_event_at

error_code
error_summary_redacted
metadata
created_at
```

Não repetir recipient PII quando puder usar referência.

# 17. DELIVERY STATE MACHINE

```text
PLANNED
↓
QUEUED
↓
SENT
├─→ DELIVERED
└─→ FAILED

PLANNED → SKIPPED
QUEUED → CANCELLED
```

`DELIVERED` somente se o canal provar.

# 18. DASHBOARD É PUBLICAÇÃO, NÃO DELIVERY EXTERNO

Hoje o briefing executor trata a existência no dashboard como canal “ok”.

Preservar como:

```text
PUBLISHED_IN_LIBRARY
```

Não chamar isso de:

```text
DELIVERED_TO_RECIPIENT
```

# 19. CHANNEL RECEIPT CAPABILITY

Cada channel adapter declara o que consegue provar.

```text
EMAIL
accepted?
delivered?
bounced?
opened? optional/unreliable

WHATSAPP
accepted?
sent?
delivered?
read? somente se receipt autoritativo existir

DASHBOARD
published?
authenticated_open?

SHARE
raw_access?
qualified_open?
```

Não inventar estado acima da evidência.

# 20. SENT NÃO É DELIVERED

🔒 Se `send_email()` retorna True:

```text
SENT / ACCEPTED
```

não automaticamente:

```text
DELIVERED
```

# 21. OPENED NÃO É READ

🔒 `READ` não é estado genérico da 095.

Mesmo que futuro provider traga “read receipt”, a UI precisa citar a natureza da evidence.

# 22. ENGAGEMENT EVENTS

Preferir `artifact_events` já existente.

Eventos possíveis:

```text
artifact.opened.internal
artifact.downloaded
share.created
share.revoked
share.accessed.raw
share.accessed.qualified
share.access.denied
delivery.requested
delivery.sent
delivery.delivered
delivery.failed
```

Não criar event table paralela sem necessidade.

# 23. BOT / SCANNER / PREVIEW

Classificação:

```text
HUMAN_LIKELY
AUTOMATION_LIKELY
UNKNOWN
```

Signals:
- crawler/scanner user-agent conhecido;
- prefetch;
- link unfurl;
- security tooling;
- verified recipient/authenticated session.

Não fazer fingerprint invasivo.

# 24. LINGUAGEM DE ENGAGEMENT

Permitido:
```text
“Link acessado 3 vezes.”
“Visualização qualificada em 31/08 às 14:21.”
“João abriu no AutoBrokers.”
```

Quando evidence existe.

Proibido:
```text
“O cliente leu.”
“O cliente entendeu.”
```

# 25. INTERNAL VIEW HISTORY

Authenticated view pode registrar:
```text
user_id
artifact_id
version_id
viewed_at
```

ACL-aware.

# 26. PUBLIC VIEW HISTORY

Public token:
- share_id;
- timestamp;
- raw/qualified classification;
- coarse technical metadata;
- sem invasive fingerprint.

Com verified email, pode associar recipient.

# 27. ENTREGAS — RESULTADOS

Dentro de Entregas:

```text
RESULTADOS | ATIVIDADE
```

Default: **RESULTADOS**.

# 28. QUICK VIEWS

```text
Recentes
Favoritos
Compartilhados
Precisa de atenção
Arquivados
```

Como tabs/chips/filters internos, não menu.

# 29. PRECISA DE ATENÇÃO

Inclui:
- failed render;
- delivery failed/partial;
- share expired quando deveria estar ativo;
- data confidence warning;
- no accessible render;
- Work Run concluído sem Artifact esperado;
- Artifact generating stale.

# 30. FAVORITOS

Per-user, nunca global.

Antes de migration procurar padrão de preferência existente.

Contrato possível:
```text
company_id
user_id
artifact_id
is_favorite
last_viewed_at?
```

# 31. NÃO CRIAR FOLDERS COMO DEFAULT

🔒 Organizar por relações:

```text
kind
período
producer
Auxiliary
Routine
Work Run
subject
client
insurer
status
shared
delivery
format
tag
```

Folder futuro só com evidência de necessidade.

# 32. SEARCH — GAP MEDIDO

A UI atual:
- limita 120 itens por fonte;
- busca depois no browser;
- consulta apenas title/detail/origin.

Portanto, um Artifact antigo pode existir e ser invisível para a busca.

# 33. SERVER-SIDE SEARCH

Search fields:
```text
title
subtitle
summary
tags
subject label
origin
producer display
template
```

Se necessário:
```text
sanitized indexed text
```

# 34. SEARCH TECHNOLOGY

V1 preferencial:
```text
Postgres FTS / trigram
```

Motivos:
- structured metadata;
- tenant filter;
- pagination;
- baixo custo;
- nenhuma nova authority.

Semantic search apenas se necessidade medida; se existir, usar SearchService/Qdrant atual.

# 35. SEARCH FILTERS

At minimum:
```text
kind
created/published date
origin
producer
status
subject
Work Run
Auxiliary
Routine
shared
delivery status
opened/never opened (quando confiável)
format
archived
favorite
tags
```

# 36. SEARCH SORT

Com query:
```text
relevance
```

Sem query:
```text
recent published
```

Opções:
```text
newest
oldest
last opened
last published
```

# 37. PAGINATION

Cursor-based.

Proibido:
```text
load everything → filter browser
```

# 38. CHAT / COMMAND SEARCH

Core deve resolver:
```text
“o relatório de ontem”
“o último Pulso 360”
“o dossiê da Allianz”
```

por tool de Artifact Library.

Retorno:
```text
metadata + refs
```

Não raw HTML.

# 39. ARTIFACT CONTEXT REF

Smith recebe:
```text
artifact_id
version_id
title
summary
subject_ref
data_as_of
confidence
source refs
work_run_id
formats
```

Conteúdo/evidence detalhado só sob demanda.

# 40. DETAIL PAGE

Estrutura recomendada:

```text
PREVIEW
VERSÕES
ENTREGA & COMPARTILHAMENTO
FONTES
ATIVIDADE
```

Progressive disclosure.

# 41. PREVIEW

Preservar iframe sandbox para HTML.

Mostrar:
- title;
- version;
- published date;
- data_as_of;
- confidence;
- produced by;
- subject;
- primary actions.

# 42. PRIMARY ACTIONS

```text
Baixar
Compartilhar
Enviar
Perguntar ao AutoBrokers
⋯
```

Secundárias:
```text
Regenerar
Nova versão
Arquivar
```

Permission-aware.

# 43. PERGUNTAR AO AUTOBROKERS

Abre chat com structured Artifact ref.

```text
“explique esse gráfico”
“compare com a versão anterior”
“de onde veio esse número?”
```

# 44. VERSION HISTORY UI

Exemplo:

```text
v4 — atual
31/08/2026
dados até 30/08
Core
published

v3
24/08/2026
superseded
```

# 45. VERSION ACTIONS

```text
Abrir
Baixar
Compartilhar versão
Copiar link interno
Criar nova versão a partir desta
Comparar
```

# 46. VERSION COMPARISON

V1:
- metadata;
- data_as_of;
- sources;
- sections/blocks;
- structured metric deltas quando payload permitir.

Não precisa de semantic diff universal.

# 47. SPECIFIC VERSION URL

Stable tenant URL:
```text
/dashboard/entregas/{artifactId}?version={versionId}
```
ou equivalente.

# 48. CANONICAL LIVE INTERNAL URL

```text
/dashboard/entregas/{artifactId}
```

resolve versão publicada atual.

# 49. SOURCE / PROVENANCE UI

Transformar `data_sources` em algo realmente conferível.

```text
Fontes
├─ InfoCap · produção · dados 01/08–31/08
├─ Atlas · Allianz
└─ Evidence Pack
```

Sem secrets.

# 50. EVIDENCE DRILLDOWN

Mostrar:
- source type;
- as_of;
- confidence;
- authorized source/ref;
- summary.

Não chain-of-thought.

# 51. PRODUCER LINEAGE

⚠️ A página atual infere o produtor pelo `template_key`.

A 095 precisa de lineage explícita:

```text
producer_kind
producer_ref
producer_label_snapshot
```

Exemplos:
```text
core
auxiliary
routine
research
api
user
system
```

# 52. NÃO INFERIR DONO DO TEMPLATE

Mutation:
```text
mesmo template usado por Auxiliary diferente
→ UI atribui ao Auxiliary antigo
```

**FAIL.**

# 53. WORK RUN LINEAGE

Se `work_run_id` existe:
```text
Produzido no Trabalho X
```
com link autorizado.

# 54. AUXILIARY / ROUTINE LINEAGE

Se produzido por Cobrança Feita, Checklist 6h etc., mostrar relação direta via IDs, nunca por título/template heuristic.


# 55. ENTREGA & COMPARTILHAMENTO — DETAIL VIEW

Mostrar separadamente:

```text
SHARES
- quem/audiência
- live ou frozen
- version
- expires
- views qualified/raw
- download allowed?
- active/revoked

DELIVERIES
- channel
- recipient/audience
- status
- requested
- sent
- delivered if proven
- failure reason
```

# 56. ACTION — COMPARTILHAR

Modal compacto:

1. escolher versão:
   - Atual congelada
   - Link sempre atualizado
2. audiência;
3. validade;
4. acesso;
5. permitir download;
6. controles extra quando disponíveis;
7. criar link;
8. copiar/enviar.

Default external:
```text
FROZEN + expiration
```

# 57. ACTION — ENVIAR

Enviar é diferente de compartilhar.

Fluxo:
```text
select artifact/version
→ select/resolve recipient
→ select channel
→ policy/approval
→ delivery group
→ existing sender
→ receipts
```

Não permitir LLM inventar recipient.

# 58. IDEMPOTÊNCIA

Delivery precisa de:
```text
idempotency_key
```

Double click/retry não envia duas vezes.

# 59. RETRY

Retry cria:
```text
new attempt
```
ligado ao mesmo delivery group.

Não apaga falha anterior.

# 60. DELIVERY FAILURE UX

Nunca:
```text
“não deu”
```

Mostrar:
```text
WhatsApp — falhou
Motivo: nenhum canal de saída autorizado

Email — enviado ao provedor
Entrega final não confirmada
```

# 61. DELIVERY HISTORY

Histórico cronológico:
```text
31/08 14:02 publish v4
31/08 14:03 share created
31/08 14:04 WhatsApp sent
31/08 14:04 email accepted
31/08 14:05 share access automation-likely
31/08 14:19 qualified view
```

# 62. ACTIVITY TAB

Reusar `artifact_events` + related Work/Delivery events.

Não reconsultar 8 tabelas arbitrariamente quando lineage já resolve.

# 63. ENTREGAS — ATIVIDADE

A lente Atividade continua cobrindo:
- Work Run;
- auxiliary run;
- routine run;
- conversations;
- agent activities;
- research events.

Mas deve existir relation to resulting Artifact.

Exemplo:
```text
Cobrança Feita rodou
→ produziu “Cobranças de 31/08”
```

# 64. ORPHAN OUTPUT

Definição:

```text
Work completed
+
expected user-facing result
+
no accessible Artifact/result
```

vira:
```text
ORPHAN_OUTPUT
```

Métrica e “Precisa de atenção”.

# 65. ORPHAN ACTIVITY

Uma atividade sem href pode continuar existir honestamente.

Mas se é resultado esperado:
```text
no destination
```
é defect, não design.

# 66. RESEARCH

A tela específica de Research pode continuar por causa de provenance rica.

Mas pesquisa concluída pode ter:
```text
research result Artifact
```
na Library.

Não duplicar source-of-truth.

# 67. BRIEFINGS

Briefing publication com `artifact_id`:
```text
Library item = Artifact
```

O briefing event/history fica como Activity.

Reduz duplicata na lista Resultados.

# 68. EXECUTIVE INTELLIGENCE 360

SPEC-094 outputs entram automaticamente:

```text
kind=report
producer=core/executive-intelligence
subject=company/period
metric/evidence provenance
```

Sem código de Entregas específico para “Pulso 360”.

# 69. CLAIMS

SPEC-093 pode futuramente gerar:
- dossier;
- timeline report;
- evidence summary.

Mesma Library.

ACL/sensitivity mais restritas.

# 70. ARTIFACT SENSITIVITY

Adicionar/reusar classification:

```text
INTERNAL
CONFIDENTIAL
CLIENT_SAFE
RESTRICTED
SENSITIVE
```

Não depender apenas de `kind`.

# 71. SHARE GUARD POR SENSITIVITY

Exemplo policy:

```text
INTERNAL
→ external share requires explicit confirmation

SENSITIVE
→ verified recipient or authenticated access
→ shorter expiry
→ download default off
```

Exact rules depend on security authority existing.

# 72. ACL

Artifact access must consider:
- company membership;
- role;
- subject sensitivity;
- financial data;
- Claims/medical data;
- team/scope when introduced by SPEC-098/097.

095 does not invent full future team scope.

It must leave `access_scope` extensible.

# 73. FINANCIAL ARTIFACTS

Executive 360 may contain:
- commission;
- repasse;
- producer performance.

Not every member should automatically see everything.

Warm-up must audit current role semantics before exposing.

# 74. ARCHIVE

Schema already has `archived_at`.

Finish product behavior:

```text
Archive
→ hidden from default Results/search
→ available in Archived
→ URLs still resolve to authorized user with archived banner
→ can unarchive
```

No delete by default.

# 75. DELETE

Deletion is not primary flow.

If required:
- permission;
- retention;
- share revocation;
- evidence/legal implications;
- explicit confirmation.

May be deferred.

# 76. FAVORITES / RECENTS

### Recent
per-user from authenticated view history.

### Favorite
explicit per-user setting.

Do not infer favorite from repeated views.

# 77. SHARED VIEW

“Compartilhados” means:
```text
Artifact has active share or delivery relationship
```

Not “someone probably saw it”.

# 78. NEEDS ATTENTION VIEW

Prioritize:
1. delivery failed;
2. render failed;
3. expected Artifact missing;
4. sensitivity/share violation;
5. stale generating;
6. share expiring soon if active workflow needs it;
7. partial delivery;
8. confidence warning.

# 79. CARD / ROW DESIGN

Linear-like density.

Each row can show:
```text
icon kind
title
subject
producer
published/data date
version
small badges:
PDF
Shared
Failed
Opened
Favorite
```

No paragraph of metadata.

# 80. LIST VS GALLERY

Default:
```text
LIST
```

Reports can optionally preview thumbnail later.

Do not add gallery unless useful.

# 81. MOBILE

Critical actions on phone:
- find;
- open;
- download;
- copy/share link;
- see status.

Do not require desktop to deliver report to client.

# 82. EMPTY STATES

Examples:

```text
Ainda não há resultados.
Quando o AutoBrokers terminar um trabalho que gera entrega, ele aparece aqui.
```

Not marketing copy without action.

# 83. FORMAT STORAGE

HTML small inline can remain.

Binary/large:
```text
MinIO/private object
```

`storage_ref`.

Do not store PDF/XLSX binary in Supabase text.

# 84. STORAGE KEY

Must include tenant-safe namespace:
```text
artifacts/{company_id}/{artifact_id}/{version_id}/{format}/...
```

Exact convention follows MinIO authority.

# 85. DOWNLOAD AUTH

Internal download:
- session;
- company filter;
- role/scope;
- artifact/version;
- format capability.

External share download:
- share policy;
- exact version/live resolution;
- expiration;
- max views/access;
- allow_download.

# 86. SIGNED STORAGE URL

If used:
- short-lived;
- server-issued;
- no bucket public;
- no permanent MinIO URL in Artifact payload.

# 87. PUBLIC LINK SECURITY

Preserve:
- opaque strong token;
- same generic unavailable response;
- noindex;
- noarchive;
- CSP;
- nosniff;
- no-referrer;
- no shared cache.

# 88. PUBLIC LINK PAGE / ROUTE

Current raw HTML route is secure/simple.

If adding access UI for password/email:
- wrapper gate before bytes;
- do not weaken CSP of the artifact;
- artifact document can remain isolated.

# 89. MAX VIEWS

Clarify semantics:
```text
access attempts?
qualified views?
successful authorized opens?
```

Recommended:
```text
successful authorized content grants
```

Not bot requests denied/classified automation.

# 90. VIEW COUNT AND BOT FILTER

Do not let link scanner consume max_views if confidently identified as automated.

If uncertain:
- conservative security;
- record unknown;
- policy chosen explicitly.

Warm-up tests actual route behavior.

# 91. AUDIT EVENT PRIVACY

`artifact_events.detail` must not become a dumping ground for:
- email address;
- phone;
- CPF;
- share passwords;
- tokens.

Use refs/hashes/redacted labels.

# 92. SHARE TOKEN

Never log token plaintext in event detail or normal logs.

# 93. DOWNLOAD AUDIT

Record:
```text
artifact.downloaded
version
format
actor
timestamp
```

No file bytes in event.

# 94. VERSION-SPECIFIC DOWNLOAD

Download action must resolve exact selected version.

Mutation:
```text
user viewing v2 clicks PDF
→ gets v5
```
FAIL.

# 95. FORMAT CONSISTENCY

Same Version across formats must have same semantic content.

PDF cannot silently drop:
- source section;
- confidence;
- warnings;
- material totals.

# 96. FORMAT DIFFERENCES ALLOWED

Presentation adapts:
```text
web interactive layout
pdf pagination
xlsx tables
csv raw tabular
```

Semantics remain.

# 97. PDF QA

Tests:
- page renders;
- no clipped blocks;
- no blank pages;
- fonts/branding;
- headers;
- source/confidence;
- A4 if intended;
- print background;
- links where appropriate.

# 98. XLSX QA

Tests:
- opens;
- sheet names valid;
- numeric cells numeric;
- dates dates;
- currency formatting;
- no formula injection from user strings;
- frozen header/filter when relevant;
- no PII sheet accidentally added.

# 99. CSV QA

- UTF-8;
- delimiter contract;
- quoting;
- formula injection protection;
- line endings;
- no hidden data.

# 100. FORMULA INJECTION

Critical for CSV/XLSX.

Values beginning:
```text
=
+
-
@
```
from untrusted/user/provider strings must be escaped/treated as text where not explicitly formula.

# 101. RENDERER AUTHORITY

Tool Gateway/Capability Registry governs render capabilities.

Do not let arbitrary code call libreoffice/shell/Chromium outside approved renderer wrapper.

# 102. RENDER JOB

For expensive render:
```text
Artifact Version
→ render request
→ worker/Work Run according to measured duration
→ artifact_renders
```

No second scheduler.

# 103. RENDER IDEMPOTENCY

Key:
```text
version_id + format + renderer_version
```

Same request returns existing render unless forced/new renderer version.

# 104. RENDERER VERSION

Store/derive:
```text
renderer_key
renderer_version
```

So visual differences can be traced.

If schema migration too large, encode in metadata but make explicit.

# 105. ARTIFACT CURRENT VERSION

Current page says “versão publicada é a mais alta” and intentionally ignores `current_version` if disagreement.

Warm-up must define one authority:
```text
current_version pointer
vs latest published query
```

Recommendation:
- published status is ground truth;
- `current_version` is projection/cache and must reconcile.

# 106. CURRENT VERSION DRIFT TEST

If pointer says 3 but latest published is 4:
- self-heal/flag;
- never show draft 5 accidentally.

# 107. DATA_AS_OF

Every data-driven Artifact must carry:
```text
data_as_of
```
or explicit:
```text
not_applicable
```

No silent missing date.

# 108. CONFIDENCE

Data-driven Artifact:
```text
confidence_note
```
or structured confidence when appropriate.

095 surfaces it; does not invent confidence scoring.

# 109. TAGS

Use current `tags[]`.

Add useful automatic tags from:
- kind;
- domain;
- insurer;
- subject class;
- period;
- producer;
- Auxiliary.

Avoid uncontrolled LLM tag explosion.

# 110. SUBJECT_REF

Current schema already has it.

Make it useful:
```text
{kind, id/ref, label}
```

Examples:
```text
company
client
policy
insurer
claim
period
```

Respect privacy in list display.

# 111. SEARCH INDEX PRIVACY

Only index fields the current user could retrieve through server-side tenant/scope query.

No global index leak.

# 112. SEMANTIC SEARCH FUTURE

If user asks:
```text
“aquele relatório que falava de concentração na Allianz”
```
structured FTS may already suffice.

Only add embeddings after measuring misses.

# 113. DELIVERY POLICY REUSE

Current Briefing DeliveryExecutor already says:
> não é motor de envio; decide e delega ao sender existente.

Preserve this principle.

095 generalizes delivery ledger, not sender duplication.

# 114. BRIEFING LEGACY STATUS

`briefing_publications.delivery_status` remains compatibility projection until migration/cutover.

Avoid two authorities forever.

Destination:
```text
Artifact Delivery
→ projection to legacy field while needed
```

# 115. CHANNEL RUNTIME REUSE

WhatsApp:
- existing governor;
- existing integration purpose;
- existing receipts if available.

Email:
- existing provider/service.

No `ArtifactWhatsAppSender`.

# 116. DELIVERY APPROVAL

If send requires approval:
```text
approval authority
→ delivery request
```

Do not bury approval flag inside Artifact.

# 117. DELIVERY TO CLIENT

Resolve recipient from authoritative context/contact.

LLM can state:
```text
“envie para Maria”
```
but system must resolve exactly one authorized recipient before side effect.

# 118. WRONG RECIPIENT IS P0

Mutation:
- Artifact subject client A;
- delivery recipient client B due to fuzzy name;
- system sends.

FAIL + hard gate.

# 119. SHARE VS SEND

### Share
creates access capability/link.

### Send
performs outbound action.

A share can exist without being sent.

A send may contain a share link.

Different events.

# 120. PUBLIC SHARE VERSION DISCLOSURE

Viewer does not need technical UUID, but can see:
```text
Documento atualizado em ...
```
for LIVE mode if appropriate.

FROZEN can show:
```text
Versão publicada em ...
```

# 121. WHITE LABEL

Preserve brokerage brand.

AutoBrokers attribution follows existing product/brand policy.

Do not let share UI accidentally switch to AutoBrokers brand for historical version.

# 122. BRAND IMMUTABILITY

Published Version keeps its brand snapshot.

LIVE share showing newer version naturally shows that newer version's frozen brand.

# 123. ARCHIVED SHARE

Default recommendation:
- existing external frozen share can remain valid until its own expiration unless archive policy explicitly revokes;
- UI must show active share on archived artifact.

For sensitive artifact, tenant policy may revoke on archive.

Warm-up validates.

# 124. SHARE REVOCATION

Revocation immediate and fail-closed.

Cache must not keep content accessible.

# 125. VERSION SUPERSEDE DOES NOT REVOKE FROZEN SHARE

Important:
```text
v2 superseded
frozen share to v2
```
continues until expired/revoked.

Otherwise evidence links break.

# 126. LIVE SHARE AND ARCHIVE

If Artifact archived:
recommended default:
```text
LIVE share unavailable
```
unless policy says otherwise.

# 127. CHAT “MANDA DE NOVO”

Flow:
```text
resolve Artifact
→ select exact/latest version
→ resolve recipient/channel
→ confirm/approval as policy
→ new delivery attempt
```

Never replay old network request blindly.

# 128. CHAT “O CLIENTE VIU?”

Answer must synthesize evidence honestly:

```text
“o link foi acessado uma vez às 14:19; não dá para afirmar que a pessoa leu.”
```

or:
```text
“não há acesso qualificado registrado.”
```

# 129. CHAT “QUAL VERSÃO ENVIEI?”

Delivery attempt links exact:
```text
artifact_version_id
```

So answer is deterministic.

# 130. NOTIFICATIONS

Do not create notification spam in 095.

Potential:
- delivery failed;
- share viewed by verified recipient;
- share expiring.

Only if existing notification fabric fits; otherwise event is enough and proactive alert deferred.


# 131. WARM-UP FORENSE OBRIGATÓRIO

Antes de editar:

1. registrar HEAD/branch/status;
2. reler SPEC-057 inteira;
3. reler SPEC-078 Bloco F;
4. ler migrations Artifact;
5. ler ArtifactService;
6. ler artifact API;
7. ler tenant Artifact detail/download;
8. ler public `/r/[token]`;
9. ler Entregas API/client;
10. ler tests de Entregas;
11. buscar `artifact_delivery*`;
12. inspecionar schema vivo de Artifact tables;
13. contar artifacts por kind/status;
14. contar versions por status;
15. contar renders por format/status/storage_ref;
16. contar shares active/expired/revoked;
17. contar artifact_events por event_type;
18. medir orphan artifacts;
19. medir artifacts sem Work Run;
20. medir artifacts sem producer lineage;
21. medir artifacts sem data_as_of;
22. medir artifacts sem source/provenance;
23. medir links públicos em uso;
24. medir download formats reais;
25. medir delivery statuses em briefings/routines;
26. mapear email sender atual;
27. mapear WhatsApp send receipt atual;
28. mapear webhooks de delivery/read;
29. mapear MinIO storage service atual;
30. mapear render dependencies instaladas;
31. procurar Playwright/Chromium;
32. procurar spreadsheet generation dependency;
33. procurar docx/pptx generation;
34. medir roles/ACL do dashboard;
35. medir query performance da lista atual;
36. medir volume histórico;
37. confirmar 120-per-source limitation;
38. selecionar Golden Artifacts;
39. registrar o que 057 prometeu e o que está realmente executado;
40. produzir relatório de gap antes da implementação.

# 132. WARM-UP — AFIRMAÇÕES PARA REFUTAR

## P1
“Artifact Hub já está completo porque o documento abre.”
Provavelmente falsa.

## P2
“Baixar entrega PDF.”
Falsa hoje.

## P3
“Todo Artifact tem producer/owner explícito.”
Falsa; UI atual usa template heuristic.

## P4
“Entregas busca todo o histórico.”
Falsa no desenho atual.

## P5
“`sent` significa que o destinatário recebeu.”
Não necessariamente.

## P6
“GET público significa humano abriu.”
Falsa.

## P7
“View significa read.”
Falsa.

## P8
“`password_hash` no schema significa password protection pronta.”
Provar.

## P9
“Todos os formatos prometidos pela 057 têm renderer.”
Provavelmente falsa.

## P10
“artifact_deliveries já existe.”
Busca do repo não encontrou; provar live DB.

## P11
“Share sempre deve seguir latest.”
Falsa para entrega formal.

## P12
“Share sempre deve congelar version.”
Falsa para alguns internal/live workflows.

## P13
“Archived Artifact pode sumir definitivamente da busca.”
Falsa; archive preserva history.

## P14
“Todos os membros podem ver artifacts financeiros.”
Provar.

## P15
“Um Work Run concluído sempre tem resultado acessível quando deveria.”
Provar.

## P16
“HTML e PDF sempre têm mesma semântica.”
Provar com future renderer.

## P17
“Link scanner nunca acessa public share.”
Falsa como premissa geral.

## P18
“O que você ainda NÃO entendeu da última milha de Artifact?”
Resposta “nada” reprova.

# 133. GOLDEN ARTIFACTS

Escolher corpus real/redacted:

```text
G1 briefing daily
G2 briefing weekly
G3 cobrança
G4 Raio-X Comercial / SPEC-081
G5 Renewal Radar
G6 Executive 360 candidate/sample when available
G7 research Artifact
G8 failure Artifact/render
G9 multi-version Artifact
G10 sensitive dossier synthetic
```

# 134. IMPLEMENTATION BLOCK 0 — AUDIT & GAP REPORT

Entregar:
```text
Artifact Hub Reality Report
```

Com matriz:

```text
PROMISED
IMPLEMENTED
PARTIAL
BROKEN
DEFERRED
```

por capability.

### Gate 0
Nenhuma migration antes de saber:
- delivery authority;
- render reality;
- storage reality;
- share reality.

# 135. BLOCK A — LIBRARY INFORMATION ARCHITECTURE

Transformar Entregas:

```text
RESULTADOS | ATIVIDADE
```

Preservar redirects antigos.

### Gate A
- menu não cresce;
- existing History/Auxiliary redirects continuam;
- Resultados não duplica briefing + Artifact;
- Activity ainda mostra histórico.

# 136. BLOCK B — SERVER-SIDE SEARCH

Implementar:
- pagination;
- query;
- filters;
- sorting;
- recent/favorites/shared/attention/archive.

### Gate B
Artifact fora dos 120 mais recentes precisa ser encontrável.

# 137. BLOCK C — LINEAGE

Eliminar template heuristic para novos Artifacts.

Criar/reusar explicit producer refs.

### Gate C
Mesmo template produzido por dois Auxiliaries mostra produtores corretos.

# 138. BLOCK D — VERSION EXPERIENCE

- version timeline;
- exact version route;
- version-specific render/download/share;
- non-destructive restore/create-from.

### Gate D
Published history never mutates.

# 139. BLOCK E — FORMAT CAPABILITY

Audit + implement:
- HTML;
- PDF;
- CSV;
- XLSX.

### Gate E
UI só oferece formato que possui renderer/capability.

# 140. BLOCK F — PRIVATE STORAGE

Binary renders → MinIO/private storage.

### Gate F
No permanent public object URL.

# 141. BLOCK G — SHARE COMPLETION

- share management UI;
- frozen/live mode;
- expiry;
- revoke;
- max views;
- allow_download;
- password/email gate only if truly end-to-end.

### Gate G
Frozen share stays on exact Version after new publish.

# 142. BLOCK H — DELIVERY LEDGER

If no authority exists:
- add `artifact_deliveries` or best canonical name;
- migrate/project legacy briefing delivery.

### Gate H
Every outbound attempt has exact Artifact Version + channel + evidence status.

# 143. BLOCK I — ENGAGEMENT

- internal opens;
- public raw/qualified access;
- bot/scanner classification;
- view events.

### Gate I
Automation access cannot become “cliente leu”.

# 144. BLOCK J — DETAIL EXPERIENCE

Tabs/progressive disclosure:
- Preview;
- Versions;
- Delivery;
- Sources;
- Activity.

### Gate J
Common actions reachable without deep navigation.

# 145. BLOCK K — CORE / CHAT TOOL

Artifact search/ref tool.

### Gate K
“abre o relatório de ontem” resolves exact authorized Artifact without feeding whole Library to LLM.

# 146. BLOCK L — ORPHAN DETECTOR

Find:
- completed user-facing Work with missing result;
- ready artifact without accessible render;
- delivery pending stale;
- broken share/render.

### Gate L
No silent output disappearance.

# 147. BLOCK M — OBSERVABILITY

Metrics/traces/events.

### Gate M
Can answer:
```text
quantos artifacts foram gerados?
quantos abriram?
quantos renders falharam?
quantos envios falharam?
quantos public shares estão ativos?
quantos outputs estão órfãos?
```

# 148. BLOCK N — CANARY / MIGRATION

Pilots:
- Resulta;
- AutoFleet as authorized;
- synthetic tenant for cross-tenant.

### Gate N
Existing artifacts stay readable.

# 149. DATA MIGRATION PRINCIPLES

Expand-first.

Never rewrite immutable historical versions.

Backfill only metadata that can be proven.

If producer cannot be proven:
```text
producer_kind=legacy_unknown
```

not guessed.

# 150. LEGACY SHARE BACKFILL

Existing shares:
```text
mode = FROZEN_VERSION
```
because current schema stores specific `artifact_version_id`.

Safe default.

# 151. LEGACY ARTIFACT LINEAGE

Current `origin` can be retained.

Producer backfill only from strong evidence:
- Work Run owner/agent;
- briefing publication relation;
- routine/auxiliary run ID.

Template mapping alone can be:
```text
legacy_inferred
```
not authoritative.

# 152. LEGACY DELIVERY

Briefing `delivery_status`:
- keep;
- correlate with Artifact when artifact_id exists;
- optionally backfill Artifact Delivery with evidence + source=`legacy_briefing`;
- do not manufacture provider receipt.

# 153. NO DOUBLE AUTHORITY

During migration:
```text
Artifact Delivery = future authority
legacy status = projection
```

Define cutover date/version.

# 154. EVENTS APPEND-ONLY

Preserve.

If correcting a previous event:
```text
new corrective event
```
not UPDATE.

# 155. OBSERVABILITY METRICS

```text
artifacts_created
artifacts_published
artifact_versions_created
renders_by_format
render_failure_rate
artifact_library_searches
search_zero_result_rate
artifact_internal_opens
artifact_downloads
shares_created
shares_revoked
shares_expired
share_raw_access
share_qualified_access
delivery_attempts
delivery_sent
delivery_delivered
delivery_failed
delivery_partial_groups
orphan_outputs
stale_generating_artifacts
```

# 156. PRODUCT KPIs

```text
time_to_find_artifact
time_to_open
repeat_open_rate
share_creation_rate
download_success
delivery_completion
search success
percentage of user-facing Work Runs with accessible Result
```

# 157. DELIVERY COMPLETION RATE

Define carefully.

```text
PUBLISH_COMPLETION
= expected artifacts that became accessible in Library

OUTBOUND_SEND_SUCCESS
= requested outbound attempts that reached SENT or higher

VERIFIED_DELIVERY_RATE
= attempts with authoritative DELIVERED receipt / attempts where channel supports receipt
```

Do not combine them.

# 158. ENGAGEMENT KPI

```text
QUALIFIED_OPEN_RATE
```

only for shares where qualification is technically meaningful.

Never “read rate”.

# 159. PERFORMANCE TARGETS

Warm-up calibrates baseline.

Desired:
```text
Library first page ........ <= 1.5s p95
search .................... <= 1.5s p95
Artifact metadata detail .. <= 1.0s p95
HTML preview .............. <= 2.0s p95 after metadata
existing render download .. immediate/streaming
share creation ............ <= 1.0s p95
```

Heavy PDF render may be async if measured need.

# 160. SEARCH SCALE TEST

Synthetic:
```text
100k Artifact metadata rows across tenants
```

Need pagination/index/tenant filtering.

No O(n) client list.

# 161. SECURITY INVARIANTS

1. Every tenant query filters company explicitly when service role used.
2. Published versions immutable.
3. Share tokens never logged.
4. Public content no index/cache.
5. External share defaults frozen.
6. Sensitive artifacts require stricter share policy.
7. Delivery recipient resolved authoritatively.
8. No raw PII in events.
9. No cross-tenant search leakage.
10. No raw MinIO public URL.
11. Download respects version and permissions.
12. View is not read.
13. Sent is not delivered.
14. Bot hit is not human view.
15. Archived is not deleted.
16. Artifact lineage is explicit, not guessed.
17. Existing Work/Channel authorities remain.
18. No parallel Artifact Hub.

# 162. RED TEAM MISSION

> **Fazer o AutoBrokers afirmar que um resultado foi entregue/aberto, entregar a versão errada ou para a pessoa errada, ou vazar um Artifact de outro tenant enquanto a UI parece funcionar.**

Attack list:

1. cross-tenant Artifact ID;
2. cross-tenant version ID;
3. cross-tenant render ID;
4. stolen share token;
5. expired share;
6. revoked share;
7. max views exhausted;
8. share token in logs;
9. frozen share silently follows latest;
10. live share unexpectedly frozen;
11. archived Artifact remains live through live share;
12. bot preview counted human;
13. Safe Links scan counted recipient open;
14. email accepted counted delivered;
15. WhatsApp queued counted delivered;
16. view counted read;
17. recipient fuzzy match sends wrong person;
18. retry double-sends;
19. v2 detail downloads v5;
20. PDF omits confidence/source;
21. CSV formula injection;
22. XLSX hidden PII;
23. MinIO object becomes public;
24. favorite of user A appears for B;
25. finance Artifact visible to unauthorized role;
26. current_version pointer stale;
27. latest draft accidentally served;
28. Artifact published without render;
29. Work Run complete without expected Artifact;
30. template heuristic mislabels producer;
31. old Artifact not found because current 120 limit;
32. public link leaks referrer;
33. share password plaintext;
34. share download control bypass via internal route;
35. event detail stores phone/email/token;
36. semantic search future ignores ACL.

# 163. MUTATIONS OBRIGATÓRIAS

## M1
Remove company filter from raw download route.
**FAIL.**

## M2
`SENT` automatically sets `DELIVERED`.
**FAIL.**

## M3
Public GET sets `READ`.
**FAIL.**

## M4
Known scanner UA increments qualified human view.
**FAIL.**

## M5
Frozen share resolves latest version.
**FAIL.**

## M6
Version selector changes UI but download still latest.
**FAIL.**

## M7
Archive deletes Artifact.
**FAIL.**

## M8
Current 120 client rows are treated as complete search corpus.
**FAIL.**

## M9
Missing producer falls back from template heuristic as authoritative.
**FAIL.**

## M10
PDF source/confidence block removed.
**FAIL.**

## M11
CSV cell `=HYPERLINK(...)` emitted as formula from untrusted string.
**FAIL.**

## M12
Share token logged in artifact_event.
**FAIL.**

## M13
Recipient name fuzzy resolves two contacts and picks first.
**FAIL.**

## M14
Retry reuses no idempotency key and sends twice.
**FAIL.**

## M15
External share defaults LIVE.
**FAIL.**

## M16
`password_hash` existence makes UI claim password protected without verification flow.
**FAIL.**

## M17
Artifact render format advertised but absent.
**FAIL.**

## M18
Artifact from tenant B appears in server search of A.
**FAIL.**

## M19
Published version payload is updated in place.
**FAIL.**

## M20
No accessible Artifact after user-facing Work Run still counts delivery success.
**FAIL.**

# 164. TEST MATRIX — VERSIONS

- one version;
- many versions;
- draft after published;
- superseded;
- restore-as-new;
- selected old version;
- version-specific link;
- live current link;
- stale current_version pointer.

# 165. TEST MATRIX — SHARES

- frozen;
- live;
- expiration;
- revoked;
- max views;
- download allowed;
- download blocked;
- password if supported;
- verified recipient if supported;
- archived;
- superseded version;
- new version published.

# 166. TEST MATRIX — DELIVERIES

- dashboard publish;
- email accepted;
- email bounce/failed if provider supports;
- WhatsApp sent;
- WhatsApp delivered if receipt;
- mixed channels;
- partial;
- skipped policy;
- duplicate request;
- retry;
- recipient unresolved;
- wrong recipient guard.

# 167. TEST MATRIX — ENGAGEMENT

- authenticated internal view;
- public human-like;
- known bot;
- unknown;
- scanner;
- expired link;
- denied access;
- repeated view;
- public anonymous;
- verified recipient.

# 168. TEST MATRIX — FORMATS

### PDF
- large report;
- charts;
- page breaks;
- accent/Unicode;
- logo;
- sources;
- warning;
- long table.

### XLSX
- money;
- dates;
- negative values;
- user-supplied formula-like string;
- many rows;
- multiple sheets.

### CSV
- comma/semicolon/newline;
- quotes;
- UTF-8;
- formula injection.

# 169. TEST MATRIX — SEARCH

- title;
- subtitle;
- tag;
- subject;
- producer;
- old Artifact;
- archived;
- favorite;
- delivery failed;
- shared;
- tenant boundary;
- pagination;
- exact/noisy query.

# 170. E2E-1 — EXECUTIVE 360

```text
user asks Pulso 360
→ Work/engine
→ Artifact v1
→ HTML/PDF
→ published
→ Resultados
→ user opens
→ downloads PDF
→ internal events
```

# 171. E2E-2 — SHARE FROZEN

```text
v1 published
→ frozen share
→ recipient opens v1
→ v2 published
→ same share still v1
```

# 172. E2E-3 — LIVE SHARE

```text
v1 published
→ explicit live share
→ opens v1
→ v2 published
→ opens v2
```

UI owner knew this behavior.

# 173. E2E-4 — OUTBOUND DELIVERY

```text
user sends v2 via WhatsApp
→ recipient authoritative resolution
→ governed channel
→ attempt SENT
→ provider receipt DELIVERED if available
→ exact v2 preserved
```

# 174. E2E-5 — BOT

```text
share generated
→ security scanner GET
→ raw access event
→ automation-likely
→ no “cliente abriu”
→ human later opens
→ qualified event
```

# 175. E2E-6 — SEARCH OLD RESULT

```text
Artifact older than current UI 120-limit
→ server search
→ found
→ open exact result
```

# 176. E2E-7 — RENDER FAILURE

```text
Artifact publish flow
→ PDF fails
→ HTML works
→ Library says PDF failed, HTML available
→ Needs Attention
```

No whole Artifact disappearance.

# 177. E2E-8 — CROSS TENANT

Tenant A tries Artifact/version/share internal IDs from B:
```text
404 / unavailable
```
same shape as nonexistent where appropriate.

# 178. BASELINE / CONTROL

Before implementation capture:
- artifact counts;
- version counts;
- render formats;
- share state;
- Entregas current screenshots/UX;
- current search behavior;
- current tests;
- current load time;
- current 081 artifacts;
- current briefing delivery statuses.

After:
same controls + new behavior.

# 179. ROLLOUT

Phase 1:
```text
schema/metadata + hidden audit
```

Phase 2:
```text
Resultados/Atividade + server search
```

Phase 3:
```text
version UI + PDF/XLSX
```

Phase 4:
```text
share management
```

Phase 5:
```text
delivery ledger + engagement
```

Phase 6:
```text
Core Artifact search/action
```

Canary before broad rollout.

# 180. ROLLBACK

Feature flags/route compatibility.

Rollback cannot require deleting Artifact versions.

New delivery tables are additive.

Old Entregas route remains possible until cutover proven.

# 181. DEFINITION OF DONE — FOUNDATION

- [ ] Reality Report complete.
- [ ] SPEC-057 promise vs reality mapped.
- [ ] live DB audited.
- [ ] latest repo baseline recorded.
- [ ] no parallel Artifact authority.
- [ ] existing immutable/version/share security preserved.

# 182. DEFINITION OF DONE — LIBRARY

- [ ] Entregas has Resultados default.
- [ ] Atividade separate lens.
- [ ] no new menu item.
- [ ] server-side search.
- [ ] cursor pagination.
- [ ] filters.
- [ ] Recents.
- [ ] Favorites.
- [ ] Shared.
- [ ] Needs Attention.
- [ ] Archived.
- [ ] archived hidden by default.
- [ ] old artifacts searchable.
- [ ] no duplicate briefing + Artifact in Results.

# 183. DEFINITION OF DONE — LINEAGE

- [ ] explicit producer lineage for new Artifacts.
- [ ] Work Run link.
- [ ] Auxiliary/Routine relations where applicable.
- [ ] template heuristic no longer authority.
- [ ] legacy unknown stays unknown.
- [ ] subject_ref useful.

# 184. DEFINITION OF DONE — VERSIONS

- [ ] version timeline.
- [ ] exact version preview.
- [ ] exact version URL.
- [ ] exact version download.
- [ ] exact version share.
- [ ] current/live internal URL.
- [ ] restore-as-new.
- [ ] published immutable.
- [ ] comparison V1.
- [ ] current pointer reconciliation.

# 185. DEFINITION OF DONE — FORMATS

- [ ] Format Capability Matrix.
- [ ] HTML.
- [ ] PDF.
- [ ] CSV for tabular Artifacts.
- [ ] XLSX for tabular Artifacts.
- [ ] correct MIME/filename.
- [ ] private binary storage.
- [ ] checksums.
- [ ] format consistency.
- [ ] formula injection protection.
- [ ] DOCX/PPTX explicitly supported or explicitly deferred — never pretended.

# 186. DEFINITION OF DONE — SHARE

- [ ] share UI.
- [ ] frozen mode.
- [ ] live mode explicit.
- [ ] external default frozen.
- [ ] expiration.
- [ ] revocation.
- [ ] max views semantics.
- [ ] allow_download.
- [ ] password only if real.
- [ ] verified recipient only if real.
- [ ] active share list/history.
- [ ] no token logs.
- [ ] superseded frozen share still valid.
- [ ] live share archive behavior defined.

# 187. DEFINITION OF DONE — DELIVERY

- [ ] delivery authority found or created.
- [ ] no second sender.
- [ ] delivery group.
- [ ] per-channel attempt.
- [ ] exact artifact_version_id.
- [ ] idempotency.
- [ ] recipient authoritative resolution.
- [ ] planned/queued/sent/delivered/failed semantics.
- [ ] sent != delivered.
- [ ] dashboard publish separate.
- [ ] legacy briefing status projected/migrated.
- [ ] channel receipts only when supported.
- [ ] partial delivery visible.
- [ ] failure reason visible.

# 188. DEFINITION OF DONE — ENGAGEMENT

- [ ] internal authenticated open history.
- [ ] public raw access.
- [ ] qualified access.
- [ ] bot/scanner classification.
- [ ] OPENED != READ.
- [ ] no “cliente leu” inference.
- [ ] view count semantics.
- [ ] privacy-safe events.

# 189. DEFINITION OF DONE — CORE

- [ ] Core can search Artifact Library.
- [ ] “relatório de ontem” works.
- [ ] Artifact structured ref.
- [ ] ask-about-artifact action.
- [ ] reshare/resend uses exact version and recipient safety.
- [ ] “qual versão enviei?” deterministic.
- [ ] “foi aberto?” evidence-honest.

# 190. DEFINITION OF DONE — QUALITY

- [ ] orphan output detector.
- [ ] Needs Attention.
- [ ] observability.
- [ ] performance measured.
- [ ] red team complete.
- [ ] M1–M20 fail correctly.
- [ ] 081 artifacts preserved.
- [ ] 094 output contract supported.
- [ ] zero cross-tenant leak.
- [ ] zero version drift in delivery.
- [ ] zero false read claim.
- [ ] rollback proven.
- [ ] execution report.

# 191. NÃO É DEFINITION OF DONE

Não precisa:
- comments suite;
- Google Drive folders;
- real-time coediting;
- generic file uploads as replacement for Drive;
- full DOCX/PPTX if renderer not ready;
- semantic vector search without evidence;
- e-signature;
- deal room;
- permanent public links;
- user analytics invasive;
- separate email/WhatsApp engine.

# 192. REJECTED — “ENTREGAS JÁ ABRE, ENTÃO PRONTO”

🚫

Abrir é só a primeira porta.

Faltam:
```text
find
version
format
share
delivery
engagement
lineage
evidence
```

# 193. REJECTED — “CRIAR OUTRA LIBRARY”

🚫

Menu não cresce.

Entregas é a casa.

# 194. REJECTED — “FOLDER TREE”

🚫 por padrão.

Context relations are better.

# 195. REJECTED — “UMA TABELA ENTREGAS PARA COPIAR TUDO”

🚫

A timeline atual é projection.

Artifact/Work/Conversation continuam autoridades de suas entidades.

# 196. REJECTED — “DELIVERY STATUS DENTRO DE ARTIFACTS”

🚫

Um Artifact pode ter múltiplos recipients/canais/attempts.

Precisa ledger relacionado.

# 197. REJECTED — “VIEW = READ”

🚫.

# 198. REJECTED — “LIVE LINK PARA TODO MUNDO”

🚫.

Em seguros, documento formal enviado externamente deve default frozen.

# 199. REJECTED — “GERAR PDF POR OUTRO TEMPLATE”

🚫.

HTML/Artifact Version é fonte semântica; renderer adapta apresentação.

# 200. REJECTED — “ARMAZENAR TUDO NO BANCO”

🚫.

Binary large → MinIO.

# 201. REJECTED — “QDRANT PARA SEARCH DA LIBRARY AGORA”

🚫 sem medição.

Postgres metadata search first.

# 202. REFERÊNCIAS INTERNAS OBRIGATÓRIAS

Warm-up:
- SPEC-057;
- SPEC-078;
- artifact migration;
- `backend/app/services/artifacts/service.py`;
- `backend/app/api/artifacts.py`;
- `app/r/[token]/route.ts`;
- `app/dashboard/entregas/[artifactId]/page.tsx`;
- raw download route;
- Entregas API/client;
- DeliveryExecutor/Policy;
- Work Run/Artifact links;
- Artifact tests;
- MinIO/storage service;
- roles/ACL;
- 081/094 outputs;
- Protocolo AAA v9.

# 203. REFERÊNCIAS EXTERNAS

Research Pack detalha:
- Figma version/view history;
- Dropbox/DocSend;
- Notion Library/search/archive;
- Linear search/doc/update history;
- Google Drive activity;
- Microsoft Safe Links.

# 204. DECISÕES CONGELADAS

| Tema | Decisão |
|---|---|
| Novo menu Library | **NÃO** |
| Entregas = casa | **SIM** |
| Default | **Resultados** |
| Segunda lente | **Atividade** |
| Folder tree | **NÃO por default** |
| Server search | **SIM** |
| Artifact identity | **PRESERVAR** |
| Published immutable | **PRESERVAR** |
| Version history UX | **SIM** |
| Restore | **nova versão** |
| External share default | **FROZEN** |
| Live share | **explícito** |
| Share expiry/revoke | **SIM** |
| PDF | **SIM** |
| XLSX/CSV | **SIM quando tabular** |
| DOCX/PPTX | **auditar; não fingir** |
| New sender | **NÃO** |
| Delivery ledger | **SIM se authority ausente** |
| Sent = delivered | **NÃO** |
| Open = read | **NÃO** |
| Scanner = human view | **NÃO** |
| Producer inferred from template | **NÃO como authority** |
| Qdrant Library search V1 | **NÃO** |
| Binary storage | **MinIO/private** |
| Work lineage | **SIM** |
| Core Artifact search | **SIM** |

# 205. SCORE

| Dimensão | Nota |
|---|---:|
| Valor percebido | **100/100** |
| Reuso da fundação | **100/100** |
| Clareza UX | **99/100** |
| Versionamento | **100/100** |
| Sharing | **100/100** |
| Last-mile truth | **100/100** |
| Segurança | **100/100** |
| Preparação Engine | **99/100** |
| Complexidade | **88/100** |
| Prioridade agora | **100/100** |

# 206. O GANHO REAL

Antes:

```text
AutoBrokers fez
→ algum registro aparece
→ talvez tenha link
→ abre o latest HTML
```

Depois:

```text
AutoBrokers fez
→ existe Result
→ existe identidade
→ existe versão
→ existe formato
→ existe provenance
→ existe delivery evidence
→ existe activity
→ Core encontra de novo
→ corretora reaproveita
```

# 207. O MOAT

A diferença não é “geramos PDFs”.

É:

> **AutoBrokers transforma trabalho agêntico em entregáveis governados, versionados, encontráveis e auditáveis.**

Isso conecta:

```text
Agentic Work
→ Durable Output
→ Human Trust
```

# 208. COMANDO FINAL AO EXECUTOR

Não crie uma tela bonita de arquivos.

Prove que:

```text
O RESULTADO EXISTE
A VERSÃO É A CERTA
A FONTE É VISÍVEL
O FORMATO É REAL
O LINK É CONTROLADO
O DESTINATÁRIO É O CERTO
O STATUS NÃO MENTE
A BUSCA ENCONTRA
A HISTÓRIA NÃO SOME
```

# 209. LEI FINAL

> **Trabalho só termina quando o resultado tem uma casa, uma versão, um caminho de acesso e uma verdade verificável sobre o que aconteceu depois.**

Essa é a SPEC-095.

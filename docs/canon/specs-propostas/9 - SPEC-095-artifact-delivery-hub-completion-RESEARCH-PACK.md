# SPEC-095 — RESEARCH PACK
## Artifact & Delivery Hub Completion — library, versions, secure sharing, delivery truth, engagement e last-mile UX

**Data:** 31/08/2026  
**Repo:** `Amandico100/AutoBrokers-Intelligence-OS`  
**Baseline confirmado:** `46e6a49bccf5be89f7f02e7a6120d984b4740bae`  
**SPEC associada:** `SPEC-095-artifact-delivery-hub-completion.md`  
**Uso:** material de pesquisa para warm-up/refutação AAA. Não carregar inteiro no executor hot path.

---

# 1. VEREDITO

A melhor evolução não é construir “uma página de arquivos”.

É fechar cinco loops:

```text
CREATE
→ FIND

VERSION
→ KNOW WHAT CHANGED

PUBLISH
→ SHARE/SEND

SEND
→ KNOW WHAT THE CHANNEL PROVED

OPEN
→ RECORD WITHOUT OVERCLAIMING
```

Score:

```text
Current clickable Entregas .............. 72/100
Current Artifact foundation ............. 91/100
Current last-mile completeness .......... 48/100
SPEC-095 proposed architecture .......... 100/100
```

---

# 2. ORIGEM — SPEC-057

A SPEC-057 é a autoridade de origem.

Ela definiu:

- Artifact como resultado de primeira classe;
- versões;
- renders;
- Artifact Spec;
- templates;
- brand snapshots;
- provenance;
- shares;
- expiration/revocation;
- delivery;
- Artifact Library;
- multi-format output.

A 095 não deve “superar” 057 criando outro sistema.

Deve terminar o que ficou parcial.

---

# 3. ORIGEM — SPEC-078

A 078 foi resposta a uma dor explícita:

> resultados ficavam prontos e o Founder não conseguia acessá-los.

A auditoria mediu:
- Artifacts sem href;
- briefings abrindo lugar errado;
- activities sem destino;
- routine runs invisíveis.

A 078 criou rota real de Artifact, download de HTML e links corretos.

Conclusão:

```text
078 = “a porta passou a existir”
095 = “a casa fica completa”
```

---

# 4. CURRENT ARTIFACT DATABASE

Migration SPEC-057 criou:

```text
report_templates
report_template_releases
artifacts
artifact_versions
artifact_renders
artifact_shares
artifact_events
```

Pontos fortes:

- company_id everywhere;
- immutable published version;
- brand snapshot;
- data_sources/data_as_of;
- share expiration;
- max views;
- revocation;
- event append-only;
- RLS enabled.

---

# 5. CURRENT ARTIFACT SERVICE

`ArtifactService` lifecycle:

```text
criar
→ renderizar
→ publicar
→ compartilhar
```

Já implementa:
- new versions;
- frozen brand;
- immutable published;
- share tokens;
- expiration;
- revoke;
- public open;
- event recording.

Não substituir.

---

# 6. CURRENT RENDER REALITY

A migration aceita vários format values, mas o service atual renderiza HTML.

A tenant download route baixa HTML.

Comentários da 078 mediram:
```text
36 renders
36 HTML
inline_content present
0 storage_ref
```

Isso é gap real da promessa multi-format.

---

# 7. CURRENT DETAIL UX

Artifact detail atual:
- protects tenant explicitly;
- loads Artifact;
- selects latest version;
- loads HTML render;
- iframe sandbox;
- “Baixar”;
- “Abrir em nova aba”;
- title/subtitle;
- version;
- data_as_of;
- confidence.

Gaps:
- no version history;
- no version selection;
- no share management;
- no delivery history;
- no engagement;
- no source browser;
- no format picker;
- producer inferred from template map.

---

# 8. CURRENT DOWNLOAD

Route:
```text
/dashboard/entregas/[artifactId]/arquivo
```

Security is good:
- session;
- company filter;
- no-store;
- noindex.

But:
```text
download = .html
```

Not PDF.

---

# 9. CURRENT PUBLIC SHARE

`/r/[token]` is security-conscious:
- token format validation;
- backend internal fetch;
- generic denied page;
- no-store;
- noindex/nofollow/noarchive;
- no-referrer;
- nosniff;
- strict CSP;
- no scripts;
- frame-ancestors none.

Preserve.

---

# 10. CURRENT ENTREGAS

Current Entregas normalizes multiple sources into:

```text
documento
conversa
trabalho
pesquisa
```

Sources include:
- artifacts;
- briefing publications;
- auxiliary runs;
- conversations;
- agent activities;
- routine runs.

This was good ontology cleanup.

But Library/results and Activity/history are different user jobs.

---

# 11. CURRENT SEARCH LIMITATION

UI search is client-side over the rows already loaded.

API uses limits by source.

Therefore:
```text
“not in current loaded window”
≈
“not searchable”
```

for old results.

This cannot scale as Artifact Library.

---

# 12. CURRENT DELIVERY FRAGMENTATION

Search found delivery state in:
- briefing publications;
- briefing DeliveryExecutor;
- routine paths;
- channel providers.

No `artifact_delivery` implementation was found in repo search.

Warm-up must verify live DB.

---

# 13. CURRENT BRIEFING DELIVERY EXECUTOR

Strong principle:

> it is not a sender; it delegates to existing channel code.

Keep.

But its status model is briefing-specific:
```text
pending
sent
partial
failed
skipped
not_applicable
```

And dashboard counts as successful channel merely because publication exists.

This is useful for briefing completion, but cannot be the universal semantics for recipient delivery.

---

# 14. DELIVERY SEMANTIC CORRECTION

Need separate:

```text
LIBRARY PUBLICATION
OUTBOUND ATTEMPT
CHANNEL ACCEPTANCE
VERIFIED DELIVERY
CONTENT ACCESS
```

One boolean/status cannot answer all.

---

# 15. FIGMA — VERSION HISTORY

Official Figma behavior:
- timeline to file creation;
- preview snapshots;
- restore;
- duplicate;
- specific version link;
- names/descriptions;
- current file continues to exist;
- restore is non-destructive.

Reference:
https://help.figma.com/hc/en-us/articles/360038006754-View-a-file-s-version-history

AutoBrokers adaptation:
```text
Artifact identity
+
immutable Artifact Versions
+
current published
+
specific version URLs
```

---

# 16. FIGMA — LIVE VS SPECIFIC VERSION

Official Figma says:
- normal file links show latest;
- previous version can get a specific version link.

This maps directly to:
```text
LIVE_ARTIFACT share
FROZEN_VERSION share
```

But for insurance/customer delivery, default must be Frozen.

---

# 17. FIGMA — VIEWER HISTORY

Official viewer history records logged-in team/org members and invited guests plus recent access time.

Public/outside visitors are not attributed the same way.

Reference:
https://help.figma.com/hc/en-us/articles/29638316371479-See-viewer-history-for-your-files

Lesson:
> attribution requires identity evidence.

---

# 18. FIGMA — USER LOVE SIGNAL

G2:
```text
4.7/5
~1.5k reviews
```

Reviews repeatedly praise:
- real-time collaboration;
- cloud access;
- easy sharing;
- version history;
- “one source of truth”;
- no “which file is latest?” chaos.

Reference:
https://www.g2.com/products/figma/reviews

The user signal validates the product principle:
```text
one live identity > filename versions
```

---

# 19. LINEAR — SEARCH

Official Linear search:
- workspace-wide;
- issues/projects/documents;
- keyboard-first;
- recent items;
- filters;
- relevance/created/updated sorting.

Reference:
https://linear.app/docs/search

Lesson:
Artifact search should be:
```text
global to tenant
fast
keyboard/chat accessible
filterable
```

not a browser filter over 120 rows.

---

# 20. LINEAR — DOCUMENTS / HISTORY

Linear documents:
- live shared object;
- realtime save;
- version history;
- revert;
- author attribution;
- related to projects/issues.

References:
https://linear.app/docs/documents
https://linear.app/docs/project-documents

Lesson:
Artifact belongs in context of work, not in an isolated file cabinet.

---

# 21. LINEAR — UPDATES / ACTIVITY

Project updates:
- latest update in overview;
- historical Updates tab;
- chronological changes;
- sharable link/Markdown;
- related context.

Reference:
https://linear.app/docs/initiative-and-project-updates

Lesson:
Result and activity/history can share a home while remaining different lenses.

---

# 22. LINEAR — USER LOVE SIGNAL

Product Hunt current:
```text
4.9/5
~439 reviews
```

Review summary repeatedly emphasizes:
- fast;
- clean;
- easy to adopt;
- keyboard-first;
- lightweight vs heavier tools.

Reference:
https://www.producthunt.com/products/linear/reviews

AutoBrokers design target:
```text
Library ≠ enterprise document bureaucracy
```

---

# 23. NOTION — LIBRARY

Official Library currently offers:
- Recents;
- Favorites;
- Shared;
- Private;
- search;
- filters;
- customizable details;
- bulk actions;
- sidebar decluttering.

Reference:
https://www.notion.com/help/manage-your-library

Useful patterns:
```text
Recents
Favorites
Shared
filters
```

---

# 24. NOTION — SEARCH

Official search:
- full workspace;
- recent pages;
- relevance;
- edited/created sorting;
- creator/team/location/date filters;
- exact search.

Reference:
https://www.notion.com/help/search

Lesson:
search is a primary navigation surface.

---

# 25. NOTION — ARCHIVE

Official archive:
- preserves history/context/links;
- hidden from default search;
- recoverable;
- searchable with archived filter.

Reference:
https://www.notion.com/help/archive-pages

Exactly fits Artifact:
```text
archive ≠ delete
```

---

# 26. NOTION — USER LOVE + WARNING

Product Hunt:
```text
4.8/5
~1.4k reviews
```

Users praise:
- central workspace;
- linked information;
- clean/flexible design;
- shared source of truth.

Recurring complaint:
- workspace can become cluttered/overbuilt;
- complexity grows.

Reference:
https://www.producthunt.com/products/notion/reviews

Lesson:
adopt Library primitives, not Notion’s unlimited structural complexity.

---

# 27. DROPBOX — SHARED LINK CONTROL

Dropbox supports:
- expiration;
- password;
- link visibility/access;
- disable download;
- team policy.

Reference:
https://help.dropbox.com/share/set-link-permissions

Lesson:
share is a policy object, not just `token`.

---

# 28. DROPBOX — ACTIVITY

File activity includes:
- added;
- edited;
- moved;
- renamed;
- restored;
- share/unshare actions;
- viewer info when enabled.

Reference:
https://help.dropbox.com/organize/file-activity

Lesson:
activity belongs to the object.

---

# 29. DROPBOX — USER LOVE SIGNAL

G2:
```text
4.4/5
31k+ reviews
```

Users consistently praise:
- ease of use;
- file sharing;
- access anywhere;
- reliable sync.
Reviewers cite version history as a safety net.

Reference:
https://www.g2.com/products/dropbox/reviews

Lesson:
the best delivery UX “gets out of the way”.

---

# 30. DOCSEND — DIRECT REFERENCE FOR DELIVERY BLACK BOX

DocSend’s product is unusually close to the 095 problem:
- secure links;
- access controls;
- notification when viewed;
- page-by-page analytics;
- update content behind link;
- professional browser viewer.

Official:
https://www.docsend.com/features/sharing/

G2:
https://www.g2.com/products/dropbox-docsend/reviews

---

# 31. DOCSEND — USER LOVE SIGNAL

G2:
```text
4.6/5
~586–589 reviews
```

A 2026 review specifically praises:
- visibility into how prospects consume material;
- clean sharing;
- updating after send without resending;
- access controls;
- engagement analytics.

This validates the importance of:
```text
last-mile observability
```

---

# 32. DOCSEND — ADAPT, DO NOT COPY

Sales decks tolerate live-updating links.

Insurance/compliance can require a frozen exact version.

Therefore AutoBrokers must support both:

```text
LIVE
FROZEN
```

with external default Frozen.

---

# 33. GOOGLE DRIVE — ACTIVITY

Drive records:
- edits/comments;
- rename;
- move/remove;
- upload;
- share/unshare.

Reference:
https://support.google.com/drive/answer/2409045

Lesson:
history of actions is expected in mature content systems.

---

# 34. SECURITY SCANNERS — WHY VIEW ANALYTICS CAN LIE

Microsoft Safe Links:
- scans URLs;
- rewrites links;
- does time-of-click validation;
- performs security checks around email/Teams links.

Reference:
https://learn.microsoft.com/en-us/defender-office-365/safe-links-about

Even when a security product does not behave exactly like a browser, the architecture must assume automated URL access is possible.

Thus:
```text
HTTP hit
≠
human view
```

---

# 35. ENGAGEMENT TAXONOMY

Recommended:

```text
RAW_ACCESS
QUALIFIED_OPEN
AUTHENTICATED_OPEN
```

Plus classifier:
```text
HUMAN_LIKELY
AUTOMATION_LIKELY
UNKNOWN
```

Never READ.

---

# 36. MAX VIEW SEMANTICS

If share has `max_views`, count successful authorized content grants, not:
- invalid token;
- denied password;
- known bot preview.

Exact bot uncertainty policy must be tested.

---

# 37. SHARE MODES

## Frozen
External default.

## Live
Internal/ongoing default only when explicit.

This combines Figma + DocSend patterns with insurance-safe semantics.

---

# 38. VERSION RESTORE

Because DB already makes published versions immutable, Figma’s non-destructive restore is a perfect fit:

```text
old Version
→ create new Version from old payload
→ publish new Version
```

No destructive rollback.

---

# 39. PRODUCER LINEAGE GAP

Current tenant detail infers producer from template key.

This is not durable.

Need explicit producer relationship:
```text
Core
Auxiliary
Routine
Research
API
User
System
```

Artifact is lineage object, not only content object.

---

# 40. WORK RUN RELATION

Current schema already has:
```text
work_run_id
```

This is strong.

095 should expose it, not create another execution history.


# 41. ARTIFACT LIBRARY IA

Recommended:
```text
ENTREGAS
├─ RESULTADOS
└─ ATIVIDADE
```

Result quick views:
```text
Recentes
Favoritos
Compartilhados
Precisa de atenção
Arquivados
```

No new sidebar item.

---

# 42. WHY RESULTS DEFAULT

Users typically go to Entregas to consume what was produced.

Activities answer diagnostics/audit.

This also reduces duplicate mental models:
```text
output
vs
execution
```

---

# 43. SEARCH ENGINE CHOICE

Current corpus is structured metadata.

Start with:
```text
Postgres FTS/trigram
```

Reasons:
- tenant filter;
- filters;
- relevance;
- simple operations;
- no vector authority duplication.

Do not use Qdrant merely because it exists.

---

# 44. SEMANTIC SEARCH THRESHOLD

Add only after measured queries fail structured search.

If needed:
```text
existing SearchService
+
existing Qdrant
```

No Artifact-specific vector stack.

---

# 45. FORMAT STRATEGY

Reality:
```text
HTML = implemented
PDF = schema-allowed, not current renderer
CSV = schema-allowed
XLSX = not current CHECK
DOCX/PPTX = promised by 057, no robust implementation found in repo search
```

Decision:
- implement HTML/PDF/CSV/XLSX as the useful completion set;
- audit DOCX/PPTX;
- explicitly defer rather than lie if infrastructure absent.

---

# 46. PDF DESIGN

Best-fit technical pattern:
```text
same canonical HTML
→ headless Chromium print
→ PDF
```

Why:
- same brand;
- same composition;
- avoids separate report implementation;
- existing HTML already has print CSS per code comments.

Execution still needs real dependency/container validation.

---

# 47. XLSX DESIGN

XLSX should come from structured dataset/render contract, not scrape HTML.

Need:
- numeric types;
- dates;
- money;
- safe strings;
- workbook metadata;
- no formula injection.

---

# 48. CSV/XLSX SECURITY

Spreadsheet formula injection is a real class of problem.

Any externally controlled string starting with:
```text
= + - @
```
needs treatment as text unless formula is intentionally generated.

Make it a mutation test.

---

# 49. PRIVATE BINARY STORAGE

Current render schema already has `storage_ref`.

Use MinIO for binary/large renders.

Artifact database retains identity/metadata.

No public bucket.

---

# 50. SAME VERSION, MULTIPLE RENDERS

Core invariant:

```text
Artifact Version
= semantic content authority

Render
= presentation derivative
```

This is exactly why SPEC-057 separated them.

---

# 51. DELIVERY LEDGER DESIGN

A canonical Artifact Delivery relation is justified because one Artifact version can be:
- sent to multiple people;
- on multiple channels;
- retried;
- partially delivered.

A status on `artifacts` cannot represent this.

---

# 52. DELIVERY GROUP + ATTEMPT

Recommended:

```text
Delivery Group
→ user intent / distribution action

Delivery Attempt
→ one channel + one recipient + one exact version
```

This supports:
- retries;
- partial;
- audit;
- idempotency.

---

# 53. DO NOT CREATE ANOTHER SENDER

Current briefing DeliveryExecutor explicitly states the right architecture:
> decide and delegate to existing channel path.

095 repeats that.

The delivery ledger records truth around senders.

---

# 54. STATUS SEMANTICS

Recommended:
```text
PLANNED
QUEUED
SENT
DELIVERED
FAILED
SKIPPED
CANCELLED
```

But `DELIVERED` only when supported by authoritative receipt.

---

# 55. DASHBOARD SEMANTICS

Existing briefing code counts dashboard as “delivered” because publication appears there.

For generic Artifact truth, rename conceptual dimension:

```text
PUBLISHED_IN_LIBRARY
```

This prevents external delivery metrics from being inflated.

---

# 56. VIEWER ATTRIBUTION

Internal authenticated:
strong evidence.

External verified email:
moderate/strong evidence.

Anonymous token:
weak evidence.

Do not imply identity.

---

# 57. PUBLIC ACCESS AND LINK UNFURL

Potential sources:
- e-mail security;
- messaging preview;
- corporate gateway;
- browser prefetch.

Therefore raw hits need classification.

---

# 58. USER-FACING STATUS LANGUAGE

Recommended:

```text
Publicado no AutoBrokers
Enviado
Entrega confirmada
Falhou
Link acessado
Visualização qualificada
```

Avoid:
```text
Lido
Visto pelo cliente
```
without stronger evidence.

---

# 59. “ONE ALWAYS-UP-TO-DATE LINK”

DocSend/Figma show strong value here.

But AutoBrokers cannot use it indiscriminately.

Implementation has two modes:
```text
LIVE_ARTIFACT
FROZEN_VERSION
```

External default Frozen.

---

# 60. SHARE DOWNLOAD CONTROL

Useful but must not promise DRM.

Dropbox itself warns disabling download does not prevent saving by other means.

AutoBrokers UI should use wording:
```text
“Ocultar/desabilitar download pelo link”
```
not:
```text
“impedir cópia”
```

---

# 61. ARCHIVE

Notion’s archive model is ideal:
- remove from default view/search;
- preserve context/history;
- recoverable;
- old links can remain based on access policy.

Current Artifact schema already has `archived_at`.

Finish UX rather than new table.

---

# 62. FAVORITES

A user preference, not Artifact state.

Avoid:
```text
artifact.is_favorite
```
globally.

Use user+artifact relation or existing preference system.

---

# 63. RECENTS

Authenticated view events naturally power Recents.

This is better than `updated_at`, because recent means:
```text
recently viewed by me
```

---

# 64. NEEDS ATTENTION

This is a vertical AutoBrokers addition, not copied from generic drive products.

Examples:
- render failed;
- delivery partial/failed;
- Work Run produced no expected result;
- expired share needed by workflow;
- confidence warning;
- stale generation.

It turns Library into operational control.

---

# 65. ORPHAN OUTPUT

Important new metric:

```text
user-facing Work completed
+
no accessible Result
```

This is the Artifact equivalent of “work without delivery”.

A mature agentic OS must measure it.

---

# 66. ARTIFACT EVENTS AS ACTIVITY AUTHORITY

Because `artifact_events` already exists and is append-only, prefer extending event vocabulary rather than creating multiple specialized history tables.

Delivery attempts can still need relational rows for state, but activity feed comes from event projection.

---

# 67. VERSION URLS

Need both:
```text
Artifact latest internal URL
Specific Version internal URL
```

This makes chat and audit deterministic.

---

# 68. DOWNLOAD MUST RESPECT SELECTED VERSION

Current route always gets latest.

Once version UI exists, this is a critical correctness change.

A selected old version downloading latest is a serious evidence bug.

---

# 69. DATA_AS_OF / CONFIDENCE

Current schema already supports both.

095’s job:
```text
surface them consistently
```

not invent new quality scoring.

---

# 70. PROVENANCE

Current `data_sources` is a major advantage over generic file libraries.

AutoBrokers should exploit this.

A result can answer:
> “de onde veio esse número?”

That is a product differentiator.

---

# 71. ARTIFACT AS CONTEXT FOR CORE

Core should receive structured reference, not raw HTML.

Benefits:
- smaller context;
- exact version;
- provenance;
- permissions;
- fetch only what is needed.

---

# 72. ASK AUTOBROKERS ABOUT THIS

High-value action:
```text
Artifact detail
→ Ask AutoBrokers
```

Use cases:
- explain;
- compare;
- source;
- regenerate;
- send.

This makes the library active, not dead storage.

---

# 73. SECURITY STRENGTHS TO PRESERVE

Current public route has:
- generic denial;
- strict token form;
- CSP;
- noindex;
- noarchive;
- no-referrer;
- nosniff;
- no shared cache.

Do not weaken for richer UX.

---

# 74. SECURITY GAP TO AUDIT — PASSWORD

DB schema has `password_hash`.

API/service current public surface must be tested for actual password flow.

A schema column is not a feature.

---

# 75. SECURITY GAP TO AUDIT — DOWNLOAD

Current public share returns raw HTML.

When PDF/XLSX exists, download policy needs explicit enforcement.

Internal route must not become public bypass.

---

# 76. SECURITY GAP — FINANCIAL ARTIFACTS

SPEC-094 can produce:
- commissions;
- repasse;
- producer economics.

Role access must be audited before broad visibility.

---

# 77. SECURITY GAP — CLAIMS ARTIFACTS

SPEC-093 may produce high-sensitivity dossiers later.

Therefore Artifact sensitivity must not be inferred only from format/kind.

---

# 78. LIVE DB QUESTIONS

Warm-up must measure:
- artifacts count/status/kind;
- version count/status;
- renders by format;
- storage_ref usage;
- shares usage;
- event vocabulary;
- delivery authority;
- producer lineage quality;
- orphan outputs;
- data_as_of coverage;
- provenance coverage.

---

# 79. HIGH-VALUE MUTATION FAMILY

Three “truth inflation” bugs must be prevented:

```text
Published → Delivered
Sent → Delivered
Opened → Read
```

Each is a false promotion of evidence.

---

# 80. SECOND MUTATION FAMILY — VERSION DRIFT

Prevent:
```text
selected v2 → latest v5 download
frozen share → latest
delivery record without exact version
```

---

# 81. THIRD MUTATION FAMILY — DISCOVERY FAILURE

Prevent:
```text
result exists
but client-side pagination/search cannot find it
```

A library that loses old results is still a black box.

---

# 82. FOURTH MUTATION FAMILY — RECIPIENT ERROR

Prevent:
```text
fuzzy contact resolution
→ wrong person gets sensitive Artifact
```

This is high-severity.

---

# 83. FIFTH MUTATION FAMILY — FORMAT LIE

Prevent:
```text
button says PDF
but HTML downloaded
```

or:
```text
render marked ready with no bytes
```

---

# 84. ROLLOUT STRATEGY

Do not ship all complexity in one release.

Recommended order:
1. audit;
2. Resultados/Atividade;
3. search;
4. lineage/version UI;
5. PDF/XLSX;
6. shares;
7. delivery ledger;
8. engagement;
9. Core actions.

---

# 85. WHAT USERS LOVE — SYNTHESIS

Across Figma, Linear, Notion, Dropbox and DocSend, the admired patterns converge:

```text
I CAN FIND IT
I KNOW WHICH VERSION
I CAN SHARE IT EASILY
THE LINK IS RELIABLE
THE HISTORY IS THERE
THE TOOL STAYS OUT OF MY WAY
```

AutoBrokers adds:
```text
I KNOW WHO/WHAT PRODUCED IT
I KNOW THE SOURCES
I KNOW WHAT THE DELIVERY EVIDENCE ACTUALLY PROVES
```

---

# 86. WHAT USERS DISLIKE — SYNTHESIS

Common pain:
- clutter;
- heavy navigation;
- performance;
- unclear versioning;
- too much customization;
- search difficulty.

Hence:
```text
NO folder bureaucracy
NO giant cards
NO new menu maze
NO client-only search
```

---

# 87. SPEC-096 PREVIEW — WHY IT COMES NEXT

After Artifact last mile is fixed, the next surface with outsized product leverage is:

# **SPEC-096 — CHAT RUNTIME PERFORMANCE & INTERACTION SHELL**

Reason:
the user’s primary door into the whole intelligence OS is still the chat.

Artifact search/actions will make the chat even more central.

096 should improve:
- perceived latency;
- actual TTFT;
- streaming;
- status/progress truth;
- optimistic UI only where safe;
- attachment/artifact context;
- tool execution presentation;
- resume/retry;
- conversation shell;
- keyboard/mobile UX;
- no duplicate sends;
- follow-up context;
- action cards/artifact references.

---

# 88. QUESTIONS FOR SPEC-096 LATER

Likely product decisions:
1. how much execution progress should be visible?
2. should tool/agent names appear or only human-language stages?
3. when should a long job leave chat and become a Work Run card?
4. how should Artifact previews live inline?

These are for next cycle, not 095.

---

# 89. SOURCE INDEX — INTERNAL

- `docs/canon/specs/SPEC-057-artifact-hub-report-studio.md`
- `docs/canon/specs/SPEC-078-o-auxiliar-de-cobranca-funciona-e-a-entrega-aparece.md`
- `backend/supabase/migrations/20260725_06_spec057_a2_artifact_hub.sql`
- `backend/app/services/artifacts/service.py`
- `backend/app/api/artifacts.py`
- `app/r/[token]/route.ts`
- `app/dashboard/entregas/[artifactId]/page.tsx`
- `app/dashboard/entregas/[artifactId]/arquivo/route.ts`
- `app/api/dashboard/entregas/route.ts`
- `app/dashboard/entregas/EntregasClient.tsx`
- `backend/app/services/intelligence/delivery_executor.py`
- `scripts/entregas-tudo-abre.test.mjs`
- `scripts/entregas-mostra-o-historico.test.mjs`

---

# 90. SOURCE INDEX — EXTERNAL

## Figma
https://help.figma.com/hc/en-us/articles/360038006754-View-a-file-s-version-history  
https://help.figma.com/hc/en-us/articles/29638316371479-See-viewer-history-for-your-files  
https://www.g2.com/products/figma/reviews

## Linear
https://linear.app/docs/search  
https://linear.app/docs/documents  
https://linear.app/docs/project-documents  
https://linear.app/docs/initiative-and-project-updates  
https://www.producthunt.com/products/linear/reviews

## Notion
https://www.notion.com/help/manage-your-library  
https://www.notion.com/help/search  
https://www.notion.com/help/archive-pages  
https://www.producthunt.com/products/notion/reviews

## Dropbox / DocSend
https://help.dropbox.com/share/set-link-permissions  
https://help.dropbox.com/organize/file-activity  
https://www.g2.com/products/dropbox/reviews  
https://www.docsend.com/features/sharing/  
https://www.g2.com/products/dropbox-docsend/reviews

## Security scanners
https://learn.microsoft.com/en-us/defender-office-365/safe-links-about

---

# 91. FINAL RESEARCH RULE

> **Artifact creation is not the end of agentic work. The last mile must preserve identity, version, access, provenance and evidence about delivery without upgrading weak signals into stronger claims.**

The best Artifact Hub is not the one with the most file-management features.

It is the one where the user never has to ask:

```text
“onde foi parar?”
“qual versão é?”
“o que eu mandei?”
“chegou?”
“de onde veio esse número?”
```

without the system having a truthful answer.

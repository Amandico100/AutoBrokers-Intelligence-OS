# SPEC-057 — AutoBrokers Artifact Hub & Report Studio

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA E AUTORIZADA PARA EXECUÇÃO — aprovada pelo Founder em 24/07/2026  
**Autoridade superior:** `SPEC-052-cerebro-cognitivo-unificado-autobrokers.md`, `SPEC-053-autobrokers-work-os-core-harness.md`, `SPEC-054-foundation-hardening-schema-governance.md`, `SPEC-055-durable-work-runs-queue-checkpoints-hitl.md` e `SPEC-056-skill-registry-tool-gateway.md`  
**Runtime preservado:** Smith + LangGraph/LangChain + FastAPI + Supabase/Postgres + Redis + Qdrant + MinIO  
**Nome oficial do agente central:** **AutoBrokers**  
**Escopo:** transformar respostas, análises, pesquisas, dados operacionais e evidências em artifacts profissionais, versionados, seguros, compartilháveis e entregáveis — incluindo relatório web, PDF, XLSX, CSV, gráficos, apresentação PPTX, documento DOCX, briefing, dossiê e Evidence Pack.  
**Natureza desta SPEC:** autoriza migrations, backend, renderer determinístico, APIs, páginas web, templates, UI, integrações, testes, deploy, migração do relatório semanal legado e ativação em produção.  
**Dependência de execução:** os bloqueadores P0 da SPEC-054, a fundação de Work Runs da SPEC-055 e o Skill Registry/Tool Gateway da SPEC-056 devem estar implementados ou ser executados no mesmo programa, respeitando a ordem canônica.

---

# 0. Comando direto ao executor — Fable, Opus, Codex ou equivalente

Você está autorizado a **implementar integralmente esta SPEC em linha reta**.

Esta não é uma SPEC de protótipo visual, página demonstrativa, PDF isolado, relatório fake ou biblioteca que ficará desligada esperando futuras fases. Ao final da mesma iniciativa:

- o AutoBrokers deverá criar artifacts reais pelo chat;
- Work Runs deverão gerar, versionar, armazenar e entregar artifacts;
- relatórios web e PDF deverão estar disponíveis no dashboard;
- XLSX, CSV, gráficos, PPTX e DOCX deverão possuir renderers funcionais;
- artifacts deverão estar isolados por corretora e usuário conforme policy;
- links deverão ser autorizados, expirados e revogáveis;
- templates publicados deverão ser versionados e imutáveis;
- o relatório semanal atual deverá ser migrado para o novo sistema;
- o Portal Admin deverá permitir governança mínima;
- os primeiros templates de seguros deverão funcionar com dados reais disponíveis;
- a funcionalidade deverá estar ativa em produção para Amandus, Resulta e AutoFleet.

## 0.1 Doutrina de lançamento

```text
Construir com modelo definitivo.
Usar uma única fonte de conteúdo.
Renderizar múltiplos formatos a partir do mesmo Artifact Spec.
Testar conteúdo, dados, segurança e visual na mesma execução.
Corrigir na mesma execução.
Ativar na mesma execução.
```

Não criar:

- `artifacts_v2`;
- outro MinIO ou bucket público;
- outro Work Run;
- outro Skill Registry;
- outro Tool Gateway;
- gerador PDF isolado por Auxiliar;
- template escondido dentro de prompt;
- relatório HTML sem registro no banco;
- arquivo em base64 salvo no Supabase;
- página compartilhável sem expiração/revogação;
- gráfico cujo número foi inventado pela LLM;
- renderer diferente e incompatível para cada template;
- relatório semanal paralelo ao Artifact Hub;
- versão beta permanentemente desligada.

Feature flags são permitidas somente para rollback e corte controlado durante a mesma iniciativa. A entrega não será considerada concluída enquanto o caminho novo permanecer permanentemente em `off`, `shadow` ou restrito a mocks.

## 0.2 Número de blocos

A execução deverá ocorrer em **três blocos macro**, o menor número compatível com segurança, design e rollback:

1. **Bloco A — Fundação do Artifact Hub e renderer determinístico**;
2. **Bloco B — Report Studio, templates, formatos, compartilhamento e entrega**;
3. **Bloco C — Migração, Visual Acceptance, cutover e lançamento**.

Com gates verdes, avançar automaticamente.

## 0.3 Saída obrigatória

Ao final deverão existir e estar ativos:

- `artifacts` como identidade universal do entregável;
- versões imutáveis de conteúdo;
- renders por formato;
- snapshots de dados e provenance;
- templates e releases versionadas;
- Artifact Spec canônico;
- Chart Spec governado;
- renderer determinístico isolado;
- relatório web autenticado;
- PDF A4 profissional;
- XLSX funcional e editável;
- CSV com encoding e tipos corretos;
- gráficos SVG e PNG;
- apresentação PPTX editável;
- documento DOCX editável;
- Briefing e Dossiê;
- Evidence Pack;
- MinIO privado como armazenamento único;
- links autorizados, expirados e revogáveis;
- downloads auditados;
- entregas por dashboard, WhatsApp e e-mail;
- Artifact Library tenant-facing;
- Report Studio acionável pelo chat;
- governança mínima no Portal Admin;
- templates iniciais publicados;
- migração do relatório semanal;
- evals numéricos, textuais, visuais e de isolamento;
- Visual Acceptance Pack aprovado;
- Amandus, Resulta e AutoFleet validados;
- relatório final de execução publicado.

---

# 1. Ordem de leitura e autoridade

Antes de editar código ou banco:

1. atualizar a `main`;
2. registrar o commit inicial;
3. ler SPEC-052;
4. ler SPEC-053;
5. ler SPEC-054 e seu relatório final;
6. ler SPEC-055 e seu relatório final;
7. ler SPEC-056 e seu relatório final;
8. ler ADR-001, ADR-002 e ADR-003;
9. ler o código real de MinIO, documentos, weekly report, WhatsApp, SendGrid, Work Runs, Skills, Tool Gateway, charts e Portal Admin;
10. confirmar schema vivo e buckets em modo read-only;
11. confirmar branding atual do dashboard;
12. confirmar disponibilidade de Chromium/Playwright no ambiente de renderização.

Comandos mínimos:

```bash
git fetch origin
git checkout main
git pull origin main
git rev-parse HEAD
git status --short
```

Ordem normativa:

```text
SPEC-052
→ SPEC-053
→ SPEC-054
→ SPEC-055
→ SPEC-056
→ SPEC-057
→ SPECs posteriores subordinadas
→ ADRs e documentos históricos quando não conflitarem
→ código atual como estado de implementação
```

Em conflito, não criar outra arquitetura.

---

# 2. Resultado de produto

O corretor não deve receber apenas um texto longo no chat quando o resultado correto for um entregável profissional.

Exemplos:

- “Faça um relatório executivo da minha corretora desta semana.”
- “Crie uma planilha com os atendimentos parados.”
- “Monte uma apresentação para minha reunião com os sócios.”
- “Gere um PDF com a análise desta operação.”
- “Prepare um dossiê sobre esta seguradora.”
- “Me entregue os dados e os gráficos.”
- “Crie um documento editável com o plano de ação.”
- “Organize as evidências deste atendimento.”
- “Compartilhe o relatório com minha gestora por e-mail.”
- “Mande o resumo no WhatsApp e deixe o relatório completo no dashboard.”

O comportamento esperado será:

```text
Pedido
→ Skill selecionada
→ Work Run
→ coleta e snapshot dos dados
→ cálculos determinísticos
→ narrativa e recomendações
→ Artifact Spec
→ validação
→ renderização por formato
→ armazenamento privado
→ publicação autorizada
→ entrega
→ histórico e métricas
```

## 2.1 Objetivos de negócio

Esta SPEC deverá:

- transformar dados do AutoBrokers em decisões claras;
- demonstrar valor visível e recorrente para a corretora;
- permitir que o corretor use resultados em reuniões e operações;
- reduzir trabalho manual em Excel, Word, PowerPoint e PDF;
- aumentar retenção pela acumulação de histórico útil;
- permitir relatórios sob demanda e recorrentes;
- entregar artifacts com aparência premium e linguagem humana;
- diferenciar o AutoBrokers de chats horizontais;
- utilizar InfoCap, Quiver, WhatsApp, documentos, portais e dados internos quando conectados;
- medir geração, visualização, download, compartilhamento e resultado;
- preparar Briefing, Proatividade, Research Intelligence e Auxiliares das próximas SPECs.

## 2.2 Experiência de lançamento

Quando esta SPEC estiver concluída, o corretor deverá conseguir:

1. pedir um relatório no chat;
2. acompanhar o Work Run;
3. abrir um preview;
4. receber o relatório web;
5. baixar PDF, XLSX, PPTX ou DOCX quando aplicável;
6. compartilhar por canal autorizado;
7. consultar versões anteriores;
8. regenerar com novo período ou filtro;
9. entender a fonte dos números;
10. confiar que nenhum dado pertence a outra corretora.

---

# 3. Princípios invioláveis

1. **Artifact é resultado de primeira classe.**
2. **Supabase registra identidade, versão, acesso, lineage e estado.**
3. **MinIO armazena bytes e snapshots; não o Supabase.**
4. **Work Run continua sendo a autoridade da execução.**
5. **Skill continua sendo a autoridade do procedimento.**
6. **Tool Gateway governa renderers e entregas.**
7. **Um Artifact Spec canônico alimenta todos os formatos.**
8. **HTML, PDF, PPTX e DOCX não podem conter narrativas divergentes para a mesma versão.**
9. **Números vêm de cálculo determinístico ou fonte identificada.**
10. **A LLM interpreta e redige; não inventa métricas.**
11. **Todo número importante precisa de lineage.**
12. **Todo artifact pertence explicitamente a um tenant.**
13. **Nenhum bucket de artifact é público.**
14. **Link compartilhável é concessão revogável, não URL permanente.**
15. **Global Knowledge não é exportável como corpus.**
16. **Artifact não pode vazar prompts, chunks, secrets ou configurações internas.**
17. **Template publicado é imutável.**
18. **Versão publicada do artifact é imutável.**
19. **Regenerar cria nova versão, não sobrescreve história.**
20. **Render é derivado e reproduzível.**
21. **O renderer é determinístico e não é outro cérebro.**
22. **O renderer não acessa o banco com service role genérica.**
23. **O renderer recebe somente payload sanitizado e assinado.**
24. **Design tokens governam identidade visual.**
25. **A corretora pode usar sua marca sem alterar regras de segurança.**
26. **Visualização não pode manipular ou esconder dados relevantes.**
27. **Acessibilidade e legibilidade fazem parte da qualidade.**
28. **Web e PDF devem compartilhar a mesma fonte visual sempre que possível.**
29. **Downloads e compartilhamentos são auditados.**
30. **Resultado real para o corretor faz parte da Definition of Done.**

---

# 4. Estado atual confirmado e peças preservadas

## 4.1 Relatório semanal atual

Existe `backend/app/services/weekly_report.py`, que:

- conta `agent_activities` dos últimos sete dias;
- gera texto determinístico;
- envia pelo WhatsApp;
- utiliza Redis como marcador semanal;
- não gera arquivo, página, gráfico ou versão;
- não utiliza dados estruturados completos da operação.

Ele deve ser preservado como fonte de compatibilidade e transformado em:

```text
mensagem curta de entrega
+ link/cartão do novo Relatório Executivo Semanal
```

O antigo compositor textual deixa de ser a autoridade do relatório completo.

## 4.2 MinIO atual

Existe `MinioService` com:

- bucket configurado;
- upload;
- download;
- delete;
- URL pré-assinada;
- prefixo tenant/documento.

Deve ser preservado e evoluído para suportar:

- namespace `artifacts/`;
- metadata e checksum;
- content disposition;
- object version ID quando disponível;
- lifecycle;
- retenção;
- streaming;
- range requests quando aplicável;
- signed URLs de curta duração;
- separação entre documentos e artifacts;
- zero exposição de root credentials.

## 4.3 Web e gráficos atuais

O Web já utiliza:

- Next.js;
- React;
- Tailwind;
- Radix/ShadCN;
- Recharts;
- Playwright Core.

Essas peças devem ser aproveitadas, mas o Artifact Hub terá contrato visual próprio. Recharts existente não será removido de outras telas nesta SPEC. Para artifacts novos, a decisão canônica será usar um **Chart Spec interno e compilador único para Apache ECharts**, porque o mesmo motor suporta gráficos interativos no navegador e SVG em server-side rendering.

## 4.4 Entregas atuais

Existem:

- WhatsApp;
- SendGrid/e-mail no Web;
- dashboard;
- links assinados MinIO.

Devem ser adaptados ao novo modelo de `artifact_deliveries`, sem criar outro canal paralelo.

## 4.5 Peças das SPECs anteriores

Preservar:

- Work Runs, steps, attempts, events, effects e approvals;
- Skills e Skill Releases;
- Tool Gateway;
- Capability Registry;
- Vault;
- tenant connections;
- tracing e custos;
- Portal Worker e evidências;
- Document Service e sanitização;
- memória e Knowledge OS.

---

# 5. Ontologia oficial

## 5.1 Artifact

Identidade durável de um resultado lógico.

Exemplo:

```text
Relatório Executivo Semanal da Resulta
```

Pode possuir várias versões e vários formatos.

## 5.2 Artifact Version

Snapshot imutável do conteúdo e dos dados de uma geração.

Exemplo:

```text
Semana de 20 a 26/07/2026 — versão 1
```

## 5.3 Artifact Render

Arquivo ou representação gerada a partir de uma Artifact Version.

Exemplos:

- HTML/web;
- PDF;
- XLSX;
- CSV;
- PPTX;
- DOCX;
- SVG;
- PNG;
- ZIP Evidence Pack.

## 5.4 Artifact Template

Identidade de um modelo visual e estrutural.

## 5.5 Template Release

Versão imutável do template, com design tokens, layouts, componentes, regras e formatos suportados.

## 5.6 Artifact Spec

Contrato JSON canônico de conteúdo independente do formato.

## 5.7 Data Snapshot

Snapshot imutável dos dados utilizados para gerar aquela versão.

Pode conter:

- dataset tabular;
- métricas calculadas;
- filtros;
- período;
- query hash;
- references;
- provenance;
- classificação.

Os bytes do snapshot ficam no MinIO; o banco guarda metadata e hash.

## 5.8 Source Reference

Referência a origem:

- tabela/query;
- documento;
- apólice;
- Work Run;
- tool invocation;
- web source;
- conhecimento global/tenant;
- atendimento;
- portal evidence.

## 5.9 Chart Spec

Contrato declarativo, validado e limitado para geração de gráficos.

Não é código JavaScript livre.

## 5.10 Share Link

Concessão temporária e revogável para acesso a uma versão/render específico.

## 5.11 Delivery

Tentativa de entrega por dashboard, WhatsApp, e-mail ou outro canal autorizado.

## 5.12 Report Studio

Experiência de produto para solicitar, configurar, gerar, revisar, publicar e entregar relatórios.

Não é outro runtime.

## 5.13 Evidence Pack

Pacote organizado de fatos, fontes, anexos, evidências e hashes utilizados em uma decisão ou atendimento.

---

# 6. Arquitetura canônica

```text
Chat / Rotina / Auxiliar / Admin / API
                    │
                    ▼
             Skill + Work Run
                    │
                    ▼
          Artifact Orchestrator
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
 Data Snapshot   Narrative    Artifact Spec
 Determinístico  Governada    Validado
       │            │            │
       └────────────┴────────────┘
                    │
                    ▼
          Deterministic Renderer
                    │
 ┌─────────┬────────┬────────┬────────┬────────┬────────┐
 ▼         ▼        ▼        ▼        ▼        ▼        ▼
Web       PDF      XLSX      CSV      PPTX     DOCX   SVG/PNG
                    │
                    ▼
             MinIO privado
                    │
                    ▼
 Supabase metadata / access / delivery / events
                    │
                    ▼
 Dashboard / WhatsApp / e-mail / link autorizado
```

## 6.1 Autoridades

| Responsabilidade | Autoridade |
|---|---|
| identidade do artifact | `artifacts` |
| conteúdo imutável | `artifact_versions` |
| bytes renderizados | MinIO + `artifact_renders` |
| dados usados | `artifact_data_snapshots` |
| fontes | `artifact_sources` |
| template | `artifact_templates` |
| versão visual | `artifact_template_releases` |
| execução | Work Run |
| procedimento | Skill Release |
| renderização | Artifact Renderer |
| autorização | Capability Registry + Artifact Policy |
| segredo | Vault |
| compartilhamento | `artifact_share_links` |
| entrega | `artifact_deliveries` |
| timeline | Work Events + `artifact_events` |
| marca da corretora | Brand Profile governado |

## 6.2 Artifact Orchestrator

Criar ou consolidar:

```text
backend/app/services/artifact_hub/
```

Responsabilidades:

1. validar tenant e requester;
2. validar Work Run/Skill/entitlement;
3. criar ou localizar artifact idempotente;
4. criar Data Snapshot;
5. montar Artifact Spec;
6. validar schema e policies;
7. escolher Template Release;
8. criar Artifact Version;
9. solicitar renders;
10. verificar outputs;
11. armazenar em MinIO;
12. registrar checksum e metadata;
13. publicar preview;
14. entregar;
15. registrar eventos, custo e métricas.

## 6.3 Artifact Renderer

Criar um renderer determinístico, isolado e stateless, preferencialmente no mesmo monorepo, com comando/deploy próprio:

```text
autobrokers-artifact-renderer
```

Ele não é Agent, não chama LLM e não governa dados.

Responsabilidades:

- validar assinatura do render job;
- validar schema e tamanho;
- compilar Template Release + Artifact Spec;
- renderizar formatos;
- devolver bytes/metadata/checksum;
- não persistir secrets;
- não consultar tenants por conta própria;
- não executar URL externa arbitrária;
- usar sandbox e limites;
- limpar arquivos temporários;
- expor health/readiness.

## 6.4 Contrato entre Orchestrator e Renderer

O render job deve conter somente:

```text
render_job_id
company_id
artifact_id
artifact_version_id
template_release_id
format
artifact_spec sanitizado
design_tokens permitidos
asset_refs assinadas
locale
timezone
render_policy
expires_at
signature
```

Não incluir:

- token do Vault;
- service role;
- senha;
- cookie de portal;
- prompt integral;
- conteúdo global proprietário desnecessário;
- arquivo bruto fora de asset ref autorizada.

---

# 7. Decisões tecnológicas canônicas

## 7.1 Web Report

- Next.js/React;
- página autenticada server-side;
- componentes de report versionados;
- hydration apenas para interação necessária;
- Artifact Spec como fonte;
- dark/light apenas quando adequado; relatório exportável terá tema de impressão próprio.

## 7.2 PDF

Renderer oficial:

```text
HTML/CSS do mesmo template web
→ Chromium headless via Playwright
→ PDF
```

Motivos:

- Playwright já existe no projeto;
- preserva fidelidade entre web e PDF;
- suporta CSS print;
- permite cabeçalho, rodapé, página e A4;
- evita manter dois layouts independentes.

Não adotar WeasyPrint como segundo renderer padrão nesta SPEC. Só poderá entrar futuramente como fallback documentado se houver caso concreto que Chromium não resolva.

## 7.3 Gráficos

Padrão de artifacts:

```text
Artifact Chart Spec limitado
→ compilador AutoBrokers
→ Apache ECharts
```

Usos:

- browser interativo;
- SVG SSR;
- SVG embutido no PDF;
- PNG para WhatsApp/PPTX/DOCX.

O modelo não gera opção ECharts arbitrária. Ele pode propor um Chart Spec, que será validado por regras determinísticas.

## 7.4 XLSX

Renderer oficial:

```text
ExcelJS
```

Requisitos:

- workbook editável;
- tipos reais, não tudo como texto;
- datas, moedas e percentuais com formato;
- cabeçalho congelado;
- filtros;
- largura adequada;
- abas;
- fórmulas somente de lista permitida;
- nenhuma macro;
- proteção opcional de células;
- aba “Sobre os dados” com período, fonte e geração.

## 7.5 CSV

- UTF-8 com BOM quando necessário para Excel em pt-BR;
- delimitador configurável;
- cabeçalho estável;
- escaping correto;
- timezone e locale documentados;
- sem fórmula executável por CSV injection;
- campos iniciando `=`, `+`, `-`, `@` sanitizados quando não forem numéricos legítimos.

## 7.6 PPTX

Renderer oficial:

```text
PptxGenJS
```

Requisitos:

- slides editáveis;
- master layouts;
- 16:9;
- identidade visual;
- charts como SVG/PNG com dados no notes/appendix quando necessário;
- fontes seguras;
- speaker notes opcionais;
- overflow detection;
- máximo de conteúdo por slide;
- capa, resumo, análise, plano de ação e fontes.

## 7.7 DOCX

Renderer oficial:

```text
biblioteca docx para JS/TS
```

Requisitos:

- documento editável;
- estilos reais;
- headings;
- tabelas;
- listas;
- cabeçalho/rodapé;
- sumário quando aplicável;
- referências;
- sem converter PDF em imagem dentro do Word.

## 7.8 ZIP Evidence Pack

- geração determinística;
- manifesto JSON;
- índice HTML/PDF;
- arquivos permitidos;
- checksums;
- metadata de origem;
- sem secrets;
- tamanho limite;
- nome de arquivo sanitizado;
- proteção contra zip slip.

## 7.9 Licenças

Antes de adicionar dependência:

- confirmar licença atual;
- registrar SPDX;
- evitar AGPL dentro do core proprietário sem decisão jurídica;
- manter inventário de dependências;
- PptxGenJS, ExcelJS e `docx` são candidatos permissivos;
- Apache ECharts usa licença Apache-2.0;
- Playwright continua sob sua licença vigente;
- nenhuma dependência será escolhida apenas por popularidade.

---

# 8. Modelo de dados canônico

Todas as migrations seguem APPLY/VERIFY/ROLLBACK da SPEC-054.

## 8.1 `artifact_templates`

```text
id uuid PK
template_key text UNIQUE NOT NULL
name text NOT NULL
description text NOT NULL
category text NOT NULL
owner text NOT NULL
visibility text NOT NULL
is_active boolean NOT NULL DEFAULT true
created_at timestamptz
updated_at timestamptz
```

## 8.2 `artifact_template_releases`

```text
id uuid PK
artifact_template_id uuid NOT NULL FK artifact_templates
version text NOT NULL
status text NOT NULL
manifest jsonb NOT NULL
layout_spec jsonb NOT NULL
design_tokens jsonb NOT NULL
supported_formats text[] NOT NULL
content_hash text NOT NULL
runtime_min_version text NULL
created_by_user_id uuid NULL
approved_by_user_id uuid NULL
created_at timestamptz
approved_at timestamptz NULL
published_at timestamptz NULL
deprecated_at timestamptz NULL
superseded_by_release_id uuid NULL
```

Constraints:

- unique `(artifact_template_id, version)`;
- unique `(artifact_template_id, content_hash)`;
- release publicada imutável;
- uma default ativa por template;
- formatos suportados coerentes;
- nenhum secret/assets privados não referenciados.

Estados:

```text
draft
visual_review
validation_failed
approved
published
deprecated
disabled
```

## 8.3 `artifacts`

```text
id uuid PK
company_id uuid NOT NULL FK companies
artifact_key text NOT NULL
artifact_type text NOT NULL
subtype text NULL
title text NOT NULL
description text NULL
owner_user_id uuid NULL
created_by_user_id uuid NULL
created_by_agent_id uuid NULL
source_work_run_id uuid NULL
source_skill_release_id uuid NULL
visibility text NOT NULL DEFAULT 'company'
data_classification text NOT NULL DEFAULT 'internal'
status text NOT NULL
current_version_id uuid NULL
retention_policy_key text NOT NULL
legal_hold boolean NOT NULL DEFAULT false
created_at timestamptz
updated_at timestamptz
archived_at timestamptz NULL
deleted_at timestamptz NULL
```

Unique `(company_id, artifact_key)` quando o artifact representar uma série lógica.

Tipos iniciais:

- `report`;
- `briefing`;
- `dossier`;
- `spreadsheet`;
- `presentation`;
- `document`;
- `chart`;
- `evidence_pack`;
- `export`.

## 8.4 `artifact_versions`

```text
id uuid PK
company_id uuid NOT NULL
artifact_id uuid NOT NULL FK artifacts
version_number integer NOT NULL
status text NOT NULL
artifact_spec jsonb NOT NULL
artifact_spec_schema_version text NOT NULL
template_release_id uuid NOT NULL
source_work_run_id uuid NULL
source_skill_release_id uuid NULL
content_hash text NOT NULL
data_snapshot_hash text NULL
locale text NOT NULL DEFAULT 'pt-BR'
timezone text NOT NULL DEFAULT 'America/Sao_Paulo'
period_start timestamptz NULL
period_end timestamptz NULL
generated_by_model text NULL
quality_status text NOT NULL
quality_summary jsonb NOT NULL DEFAULT '{}'
published_at timestamptz NULL
created_at timestamptz
```

Constraints:

- unique `(artifact_id, version_number)`;
- unique `(artifact_id, content_hash)` quando conteúdo idêntico;
- `company_id` igual ao artifact;
- versão publicada imutável;
- `current_version_id` só aponta para versão publicada/approved;
- payload sem secrets.

Estados:

```text
draft
assembling
validating
rendering
review_required
approved
published
failed
superseded
archived
```

## 8.5 `artifact_renders`

```text
id uuid PK
company_id uuid NOT NULL
artifact_id uuid NOT NULL
artifact_version_id uuid NOT NULL
format text NOT NULL
render_variant text NOT NULL DEFAULT 'default'
status text NOT NULL
renderer_version text NOT NULL
object_bucket text NOT NULL
object_name text NULL
object_version_id text NULL
filename text NOT NULL
mime_type text NOT NULL
size_bytes bigint NULL
checksum_sha256 text NULL
page_count integer NULL
sheet_count integer NULL
slide_count integer NULL
width integer NULL
height integer NULL
render_metadata jsonb NOT NULL DEFAULT '{}'
error_code text NULL
error_message text NULL
started_at timestamptz NULL
finished_at timestamptz NULL
created_at timestamptz
```

Unique `(artifact_version_id, format, render_variant, renderer_version)` quando idempotente.

## 8.6 `artifact_data_snapshots`

```text
id uuid PK
company_id uuid NOT NULL
artifact_version_id uuid NOT NULL
snapshot_key text NOT NULL
schema_version text NOT NULL
classification text NOT NULL
row_count bigint NULL
column_count integer NULL
object_bucket text NOT NULL
object_name text NOT NULL
mime_type text NOT NULL
checksum_sha256 text NOT NULL
query_fingerprint text NULL
filters jsonb NOT NULL DEFAULT '{}'
period jsonb NOT NULL DEFAULT '{}'
provenance jsonb NOT NULL DEFAULT '{}'
created_at timestamptz
```

Não armazenar datasets grandes diretamente em JSONB.

## 8.7 `artifact_sources`

```text
id uuid PK
company_id uuid NOT NULL
artifact_version_id uuid NOT NULL
source_type text NOT NULL
source_id text NULL
source_ref text NULL
title text NULL
issuer text NULL
trust_level text NOT NULL
classification text NOT NULL
citation_label text NULL
content_fingerprint text NULL
retrieved_at timestamptz NULL
valid_from timestamptz NULL
valid_until timestamptz NULL
metadata jsonb NOT NULL DEFAULT '{}'
created_at timestamptz
```

## 8.8 `artifact_share_links`

```text
id uuid PK
company_id uuid NOT NULL
artifact_id uuid NOT NULL
artifact_version_id uuid NOT NULL
artifact_render_id uuid NULL
token_hash text NOT NULL UNIQUE
status text NOT NULL
access_mode text NOT NULL
created_by_user_id uuid NOT NULL
allowed_email text NULL
allowed_domain text NULL
max_views integer NULL
view_count integer NOT NULL DEFAULT 0
download_allowed boolean NOT NULL DEFAULT false
watermark_enabled boolean NOT NULL DEFAULT false
expires_at timestamptz NOT NULL
revoked_at timestamptz NULL
last_accessed_at timestamptz NULL
created_at timestamptz
```

Nunca guardar token bruto.

## 8.9 `artifact_deliveries`

```text
id uuid PK
company_id uuid NOT NULL
artifact_id uuid NOT NULL
artifact_version_id uuid NOT NULL
artifact_render_id uuid NULL
work_run_id uuid NULL
channel text NOT NULL
destination_ref text NOT NULL
status text NOT NULL
idempotency_key text NOT NULL
approval_request_id uuid NULL
work_effect_id uuid NULL
provider text NULL
provider_reference text NULL
message_summary text NULL
attempt_count integer NOT NULL DEFAULT 0
sent_at timestamptz NULL
delivered_at timestamptz NULL
opened_at timestamptz NULL
failed_at timestamptz NULL
error_code text NULL
created_at timestamptz
updated_at timestamptz
```

Unique `(company_id, idempotency_key)`.

## 8.10 `artifact_events`

Timeline append-only específica:

```text
id
company_id
artifact_id
artifact_version_id nullable
artifact_render_id nullable
event_type
actor_type
actor_id nullable
message_human
payload_redacted jsonb
created_at
```

Eventos mínimos:

- `artifact.created`;
- `version.created`;
- `snapshot.created`;
- `validation.passed`;
- `validation.failed`;
- `render.started`;
- `render.completed`;
- `render.failed`;
- `version.approved`;
- `version.published`;
- `share.created`;
- `share.accessed`;
- `share.revoked`;
- `download.completed`;
- `delivery.sent`;
- `delivery.failed`;
- `artifact.archived`.

## 8.11 Ligações com Work Runs e Skills

Adicionar/reusar:

```text
work_runs.primary_artifact_id
work_steps.artifact_id nullable
work_steps.artifact_version_id nullable
skill_releases.artifact_output_contract jsonb
```

Não criar outro job engine.

---

# 9. Artifact Spec canônico

## 9.1 Envelope

```json
{
  "schema_version": "1.0",
  "artifact_type": "report",
  "subtype": "executive_weekly",
  "title": "Relatório Executivo Semanal",
  "subtitle": "Resulta Corretora",
  "period": {"start": "...", "end": "..."},
  "locale": "pt-BR",
  "timezone": "America/Sao_Paulo",
  "theme": {},
  "summary": {},
  "sections": [],
  "appendices": [],
  "sources": [],
  "quality": {},
  "metadata": {}
}
```

## 9.2 Content Blocks permitidos

- `cover`;
- `executive_summary`;
- `kpi_grid`;
- `text`;
- `bullets`;
- `callout`;
- `table`;
- `chart`;
- `comparison`;
- `timeline`;
- `risk_matrix`;
- `action_plan`;
- `recommendation`;
- `source_list`;
- `evidence_reference`;
- `image` autorizada;
- `page_break`;
- `appendix`.

Nenhum bloco aceita HTML arbitrário gerado pela LLM.

## 9.3 KPI Block

Cada KPI deve declarar:

```text
key
label
value
display_value
unit
comparison_value
comparison_period
delta_abs
delta_pct
direction
status
source_ref
calculation_ref
confidence
```

`display_value` é derivado do valor, nunca a única fonte.

## 9.4 Table Block

- columns tipadas;
- rows referenciadas a snapshot;
- sorting;
- max rows por formato;
- paginação;
- totals determinísticos;
- truncation explícita;
- export completo separado quando necessário.

## 9.5 Narrative Block

Toda narrativa produzida por LLM deve conter:

- input facts permitidos;
- claims;
- source references;
- confidence;
- distinction entre fato, inferência e recomendação;
- limite de tamanho;
- proibição de inventar números.

---

# 10. Chart Spec e integridade visual

## 10.1 Tipos iniciais

- bar;
- stacked_bar;
- line;
- area;
- donut;
- scatter;
- heatmap;
- funnel;
- waterfall;
- gauge com uso restrito;
- timeline;
- table-as-chart.

## 10.2 Campos mínimos

```text
chart_key
title
subtitle
chart_type
dataset_ref
x_field
y_fields
series_field nullable
aggregation
sort
filters
unit
format
comparison
annotations
source_ref
accessibility_description
```

## 10.3 Regras de honestidade

- eixo deve começar em zero para barras, salvo justificativa registrada;
- linhas podem usar domínio ajustado, mas devem indicar escala;
- não usar 3D;
- donut somente para poucas categorias;
- evitar dupla escala;
- ordenar categorias quando fizer sentido;
- mostrar denominador em percentuais;
- não truncar período sem aviso;
- não usar cor como único sinal;
- legenda e unidade obrigatórias;
- dados ausentes são ausentes, não zero;
- variação percentual com base zero exige tratamento específico;
- chart spec inválido bloqueia publicação.

## 10.4 Validação

Validador determinístico deve verificar:

- tipo versus campos;
- cardinalidade;
- escala;
- labels;
- contraste;
- densidade;
- overflow;
- misleading patterns;
- source lineage;
- acessibilidade.

## 10.5 Saídas

O mesmo Chart Spec gera:

- ECharts interativo;
- SVG SSR;
- PNG de alta resolução;
- imagem para PPTX/DOCX;
- alt text.

---

# 11. Dados, cálculos e narrativa

## 11.1 Ordem correta

```text
fonte viva
→ extração tipada
→ snapshot
→ cálculos determinísticos
→ métricas validadas
→ seleção de insights
→ narrativa LLM
→ verificador
→ Artifact Spec
```

## 11.2 Calculation Registry

Cálculos recorrentes devem possuir função/versionamento:

- total;
- média;
- mediana;
- percentual;
- variação;
- taxa de conversão;
- tempo médio;
- aging;
- SLA;
- concentração;
- ranking;
- tendência;
- anomalia;
- custo;
- receita;
- produtividade.

Cada cálculo registra:

```text
calculation_key
version
inputs
formula
null_policy
rounding
unit
output
```

## 11.3 LLM Narrative Contract

A LLM poderá:

- resumir;
- interpretar;
- explicar impacto;
- priorizar;
- recomendar;
- escrever plano de ação.

Não poderá:

- recalcular silenciosamente;
- substituir valor oficial;
- afirmar causalidade sem evidência;
- confirmar cobertura específica sem Policy Evidence;
- omitir limitação relevante;
- inserir fonte inexistente.

## 11.4 Verificação

Antes da publicação:

- todos os números citados existem no snapshot;
- tabelas reconciliam com KPIs;
- chart data reconcilia com tabela;
- períodos são consistentes;
- moeda e percentuais estão corretos;
- fontes existem;
- claims sensíveis possuem evidência;
- não há PII desnecessária;
- não há segredo.

---

# 12. Templates, identidade e design system

## 12.1 Camadas de design

```text
AutoBrokers Base Design Tokens
→ Template Release
→ Brand Profile da corretora
→ Artifact Spec
→ Render
```

## 12.2 Base tokens

- tipografia;
- escala de espaçamento;
- grid;
- cores funcionais;
- bordas;
- sombras;
- raio;
- tamanhos de títulos;
- tabela;
- chart palette;
- estados positivos/alerta/risco;
- capa;
- cabeçalho/rodapé;
- watermark;
- print rules.

## 12.3 Brand Profile tenant

Pode configurar:

- nome;
- logo;
- cor primária;
- cor secundária;
- contato;
- site;
- rodapé;
- assinatura;
- capa opcional.

Não pode:

- reduzir contraste abaixo do mínimo;
- remover marca/aviso exigido;
- alterar política de segurança;
- inserir JavaScript/CSS livre;
- acessar assets de outro tenant.

## 12.4 Responsividade

Relatório web deve funcionar em:

- desktop;
- tablet;
- celular;
- impressão A4.

Não apenas “encolher” o desktop.

## 12.5 Acessibilidade

- HTML semântico;
- headings ordenados;
- contraste;
- navegação por teclado;
- alt text;
- charts com descrição e tabela alternativa;
- foco visível;
- leitura por screen reader;
- não depender apenas de cor.

---

# 13. Visual Acceptance Pack obrigatório

A arquitetura técnica não substitui direção visual.

Deverá ser criado um pacote separado, usando **Claude Design, Fable Design ou ferramenta equivalente**, antes do acabamento final do Bloco C.

Esse pacote não é outra SPEC e não cria outro sistema. É a referência visual oficial.

## 13.1 Entregáveis mínimos

1. **Relatório Executivo Web — desktop**;
2. **Relatório Executivo Web — mobile**;
3. **PDF A4 — capa + duas páginas internas + apêndice**;
4. **Apresentação PPTX — capa + KPI + análise + plano de ação**;
5. **Artifact Card no chat e detalhe do Work Run**;
6. **Artifact Library tenant-facing**;
7. **Portal Admin — templates/renders/falhas**;
8. **Estados vazios, loading, erro, expiração e acesso negado**;
9. **versão clara e escura onde aplicável**;
10. **exemplo com marca AutoBrokers e exemplo white-label tenant**.

## 13.2 Arquivos de referência

Armazenar em:

```text
docs/canon/design/spec057-artifact-hub/
```

Com:

- brief;
- screenshots;
- HTML/protótipos quando aplicável;
- tokens;
- decisões;
- checklist;
- aprovação do Founder;
- hash/commit da versão aprovada.

## 13.3 Gate

Nenhum template de lançamento é considerado visualmente pronto sem:

- aprovação do Founder;
- comparação web × PDF;
- teste mobile;
- teste com dados curtos e longos;
- teste de overflow;
- contraste;
- impressão;
- consistência com marca AutoBrokers.

A fundação e os renderers podem ser implementados em paralelo. O Visual Acceptance Pack bloqueia somente o acabamento e publicação final dos templates.

---

# 14. Fluxo de geração integrado ao Work Run

## 14.1 Steps canônicos

```text
artifact.plan
artifact.collect_sources
artifact.snapshot_data
artifact.compute_metrics
artifact.generate_narrative
artifact.assemble_spec
artifact.validate_spec
artifact.render
artifact.validate_render
artifact.review
artifact.publish
artifact.deliver
```

Nem todo artifact precisa de todos os steps, mas os steps usados devem ser registrados.

## 14.2 Idempotência

### Artifact

```text
{company_id}:{artifact_type}:{business_key}
```

### Version

```text
{artifact_id}:{period}:{input_fingerprint}:{template_release}
```

### Render

```text
{artifact_version_id}:{format}:{variant}:{renderer_version}
```

### Delivery

```text
{artifact_version_id}:{render_id}:{channel}:{destination}:{message_hash}
```

## 14.3 Retry

- coleta pode repetir se read-only;
- cálculo pode repetir;
- narrativa pode repetir criando attempt;
- render pode repetir idempotentemente;
- upload deve usar checksum;
- delivery só repete após ledger/reconciliação;
- publicação não duplica versão;
- share link não é recriado sem intenção.

## 14.4 Approval

Exigir quando:

- envio externo sensível;
- relatório contém dados pessoais de alta sensibilidade;
- link externo será criado;
- distribuição para destinatário não previamente autorizado;
- publicação em canal externo;
- template/branding ainda não aprovado;
- ação comercial/financeira derivada será executada.

Geração interna read-only pode ocorrer sem approval conforme policy.

---

# 15. Report Studio

## 15.1 Entrada pelo chat

Exemplo:

> “Faça um relatório executivo desta semana.”

O AutoBrokers deve:

1. identificar template/Skill;
2. inferir período quando seguro;
3. perguntar somente o que faltar;
4. listar fontes disponíveis;
5. informar limitações;
6. criar Work Run;
7. mostrar card;
8. gerar preview;
9. publicar;
10. oferecer formatos e entrega.

## 15.2 Configuração

Campos possíveis:

- período;
- unidade/filial;
- tipo de relatório;
- nível de detalhe;
- público alvo;
- KPIs;
- seguradoras/ramos;
- comparação;
- formatos;
- identidade;
- destinatários;
- recorrência futura.

O usuário não deve configurar engine, template ID, bucket ou renderer.

## 15.3 Edição

Na primeira versão operacional, permitir:

- ajustar título;
- ocultar seção permitida;
- alterar período/filtro;
- escolher nível de detalhe;
- editar observação humana;
- regenerar narrativa;
- trocar template entre opções homologadas;
- aprovar/rejeitar.

Não permitir edição direta de HTML/JSON interno pelo tenant.

## 15.4 Regeneração

- cria nova Artifact Version;
- preserva anterior;
- mostra diferenças;
- mantém lineage;
- novos formatos derivam da versão escolhida.

---

# 16. Tipos de artifact e critérios

## 16.1 Relatório Web

Obrigatório:

- URL autenticada;
- summary;
- KPIs;
- gráficos;
- tabelas;
- fontes;
- plano de ação;
- navegação por seções;
- filtros apenas quando não alterarem versão publicada;
- impressão;
- download;
- acessibilidade;
- versão e período visíveis.

## 16.2 PDF

Obrigatório:

- A4;
- capa;
- sumário quando longo;
- page numbers;
- cabeçalho/rodapé;
- sem cortes;
- tabelas paginadas;
- charts legíveis;
- links;
- metadata;
- versão;
- watermark conforme policy;
- texto pesquisável, não página inteira como imagem.

## 16.3 XLSX

Obrigatório:

- abas úteis;
- dados editáveis;
- formatos pt-BR;
- filtros;
- freeze panes;
- tabela estruturada;
- fórmulas seguras;
- fonte e período;
- sem macros;
- CSV completo opcional.

## 16.4 CSV

Obrigatório:

- export completo;
- schema documentado;
- encoding;
- delimiter;
- prevenção de formula injection;
- sem linha truncada silenciosamente.

## 16.5 PPTX

Obrigatório:

- master layouts;
- capa;
- agenda;
- summary;
- KPIs;
- gráficos;
- conclusões;
- plano;
- fontes;
- slides editáveis;
- overflow test;
- speaker notes opcionais;
- no máximo informação adequada por slide.

## 16.6 DOCX

Obrigatório:

- estilos;
- headings;
- listas;
- tabelas;
- sumário quando aplicável;
- editabilidade;
- fontes/referências;
- cabeçalho/rodapé;
- page breaks sem corrupção.

## 16.7 Chart Artifact

Obrigatório:

- spec;
- SVG;
- PNG 2x;
- alt text;
- source;
- data snapshot;
- dimensões adequadas;
- fundo transparente ou definido conforme uso.

## 16.8 Briefing

- curto;
- prioridades;
- alertas;
- recomendações;
- links para detalhes;
- mobile-first;
- versão web/PDF quando necessário.

## 16.9 Dossiê

- pergunta/objetivo;
- metodologia;
- fontes;
- análise;
- comparação;
- riscos;
- implicações;
- recomendações;
- anexos;
- citations.

## 16.10 Evidence Pack

- índice;
- manifesto;
- facts;
- documentos permitidos;
- evidence refs;
- hashes;
- timeline;
- origem;
- limitações;
- sem credenciais ou storage state.

---

# 17. Templates iniciais de lançamento

A SPEC não será concluída com catálogo vazio.

## 17.1 `report.executive_weekly`

Relatório principal da corretora:

- resumo executivo;
- ações do AutoBrokers;
- atendimentos;
- pendências;
- gargalos;
- SLA/tempo;
- alertas;
- oportunidades;
- recomendações;
- plano de ação;
- fontes e limitações.

Deve funcionar com dados disponíveis e omitir honestamente módulos desconectados.

## 17.2 `briefing.daily_attention`

- o que exige atenção;
- urgências;
- aguardando humano;
- trabalhos falhos;
- compromissos;
- alertas;
- sugestões.

A lógica avançada será ampliada na SPEC-059.

## 17.3 `report.operations_analysis`

- volume;
- produtividade;
- atrasos;
- categorias;
- tendências;
- erros;
- recomendações.

## 17.4 `report.document_analysis`

- documento;
- resumo;
- pontos críticos;
- obrigações;
- riscos;
- dúvidas;
- próximos passos;
- referências.

## 17.5 `dossier.research`

- pesquisa;
- fontes;
- fatos;
- comparação;
- análise;
- implicações;
- recomendações.

Será ampliado pela SPEC-060.

## 17.6 `evidence.case_pack`

- caso/atendimento;
- timeline;
- documentos;
- evidências;
- ações;
- decisões;
- hashes;
- limitações.

## 17.7 `presentation.executive_summary`

- apresentação de 6–12 slides;
- resumo;
- KPIs;
- problemas;
- oportunidades;
- plano.

## 17.8 `spreadsheet.operational_export`

- dados tabulares;
- resumo;
- abas;
- filtros;
- catálogo de colunas;
- fonte.

---

# 18. Segurança e multi-tenancy

## 18.1 Buckets

Artifacts ficam em bucket privado.

Prefixo:

```text
artifacts/{company_id}/{artifact_id}/{version_number}/{render_id}/{filename}
```

Snapshots:

```text
artifact-snapshots/{company_id}/{artifact_id}/{version_id}/{snapshot_id}.{ext}
```

## 18.2 Acesso

Toda leitura valida:

- sessão;
- empresa ativa;
- papel;
- visibility;
- owner quando pessoal;
- share grant quando externo;
- version/render;
- expiração;
- revogação.

## 18.3 Signed URL

- curta duração;
- gerada após autorização;
- nunca persistida como URL permanente;
- download auditado;
- content disposition controlado;
- MIME controlado;
- filename sanitizado.

## 18.4 Share Link

Default:

- desligado para artifacts sensíveis;
- expiração obrigatória;
- token 256-bit ou equivalente;
- somente hash no banco;
- view count;
- revogação;
- download separado de view;
- watermark opcional;
- rate limit;
- proteção contra enumeração;
- noindex/nofollow;
- sem assets públicos permanentes.

## 18.5 PII

- data minimization;
- mascaramento;
- lista nominativa somente quando solicitada e autorizada;
- CPF, telefone, e-mail e placa conforme policy;
- logs sem PII desnecessária;
- dados pessoais não entram em template global.

## 18.6 Global Knowledge

Artifact pode conter síntese/resposta, mas não pode:

- exportar corpus global;
- listar chunks em massa;
- revelar prompts proprietários;
- incluir arquivos globais privados;
- transformar RAG em download.

## 18.7 Renderer sandbox

- sem rede externa por padrão;
- asset fetch somente via signed internal refs;
- limite de memória/CPU/tempo;
- filesystem temporário;
- limpeza garantida;
- sem execução de script do conteúdo;
- HTML sanitizado;
- CSP;
- sem file URLs arbitrárias;
- sem localhost/metadata access;
- Chromium isolado.

---

# 19. Retenção, versionamento e lifecycle

## 19.1 Versionamento lógico

A autoridade é `artifact_versions`, independentemente do versionamento físico do bucket.

## 19.2 MinIO versioning

Pode ser habilitado após preflight e cálculo de storage. Não substituirá a versão lógica.

## 19.3 Retention Policies iniciais

- `transient_preview`: 7 dias;
- `standard_report`: 12 meses;
- `operational_history`: 24 meses;
- `evidence_case`: conforme policy/legal;
- `user_export`: 30 dias;
- `legal_hold`: sem expiração até liberação.

Valores finais devem ser configuráveis no Admin, respeitando LGPD e obrigações aplicáveis.

## 19.4 Delete

- soft delete no banco;
- revogar links;
- bloquear novos downloads;
- job de purge após retention;
- purge auditado;
- legal hold impede purge;
- derived renders podem expirar antes do artifact lógico.

---

# 20. Compartilhamento e entrega

## 20.1 Dashboard

Sempre disponível para usuários autorizados.

## 20.2 WhatsApp

Estratégia:

- mensagem curta com resumo;
- arquivo quando tamanho/tipo/provider permitirem;
- link autenticado ou share link autorizado;
- idempotência;
- receipt;
- approval conforme destino/risco;
- não enviar lista sensível por engano.

## 20.3 E-mail

Reusar SendGrid ou provider canônico:

- assunto;
- resumo;
- link seguro;
- attachment quando permitido;
- limite de tamanho;
- destinatário autorizado;
- idempotência;
- tracking conforme policy;
- unsubscribe não aplicável a envio operacional, mas comunicações comerciais obedecem política própria.

## 20.4 Download

- endpoint autenticado/proxy ou signed URL curta;
- log;
- MIME;
- filename;
- no cache para sensíveis;
- suporte a range quando necessário.

## 20.5 Delivery status

```text
pending
waiting_approval
sending
sent
delivered
opened
failed
cancelled
expired
```

---

# 21. APIs e serviços

## 21.1 Tenant APIs

```text
POST   /artifacts
GET    /artifacts
GET    /artifacts/{id}
GET    /artifacts/{id}/versions
GET    /artifacts/{id}/versions/{version_id}
POST   /artifacts/{id}/regenerate
POST   /artifacts/{id}/versions/{version_id}/render
POST   /artifacts/{id}/versions/{version_id}/publish
POST   /artifacts/{id}/share-links
DELETE /artifacts/{id}/share-links/{share_id}
POST   /artifacts/{id}/deliveries
GET    /artifacts/{id}/events
GET    /artifact-renders/{render_id}/download
```

Todas derivam company/user da sessão.

## 21.2 Chat tools/Skills

Registrar tools governadas:

- `artifact.create`;
- `artifact.render`;
- `artifact.get_status`;
- `artifact.list`;
- `artifact.publish`;
- `artifact.deliver`;
- `artifact.create_share_link` com approval/policy;
- `artifact.revoke_share_link`.

## 21.3 Internal renderer API

- internal only;
- signed request;
- nonce/idempotency;
- timeout;
- size limit;
- no public browser access;
- callback ou object result governado;
- health/readiness.

## 21.4 Share endpoint

Separado da API autenticada:

```text
/s/{opaque_token}
```

Regras de segurança da seção 18.

---

# 22. UX tenant-facing

## 22.1 Artifact Library

Categorias:

- Relatórios;
- Briefings;
- Planilhas;
- Apresentações;
- Documentos;
- Dossiês;
- Evidências;
- Gráficos.

Filtros:

- período;
- tipo;
- origem;
- Skill;
- Auxiliar;
- usuário;
- status;
- compartilhado;
- favorito;
- classificação.

Cada card mostra:

- título;
- tipo;
- período;
- versão;
- criado por;
- formatos;
- status;
- última atualização;
- ações permitidas.

## 22.2 Artifact Detail

- preview;
- resumo;
- versões;
- formatos;
- fontes;
- Work Run;
- entregas;
- compartilhamentos;
- histórico;
- baixar;
- regenerar;
- entregar;
- revogar link;
- arquivar.

## 22.3 Chat Artifact Card

- título;
- thumbnail/ícone;
- status;
- período;
- preview;
- abrir;
- baixar;
- compartilhar;
- refazer;
- formatos;
- approval quando necessário.

## 22.4 Report Studio UI

- iniciar por templates sugeridos;
- linguagem humana;
- não exibir engine;
- selecionar período e foco;
- preview;
- formatos;
- branding;
- entrega;
- recorrência via SPEC-058;
- histórico.

## 22.5 Estados

- preparando dados;
- calculando;
- escrevendo análise;
- montando gráficos;
- renderizando;
- aguardando revisão;
- publicado;
- falhou;
- fonte indisponível;
- sem dados suficientes;
- conexão necessária.

---

# 23. Portal Admin mínimo

Sem esperar a SPEC-061, entregar:

## 23.1 Templates

- catálogo;
- releases;
- formatos;
- status;
- uso;
- publicação;
- rollback;
- desativação;
- visual acceptance status.

## 23.2 Artifacts

- volume por tenant/tipo;
- storage;
- falhas;
- renders;
- share links;
- entregas;
- retention;
- legal hold;
- reprocessar render;
- revogar link;
- sem abrir conteúdo sensível por padrão.

## 23.3 Renderer

- health;
- versão;
- fila;
- tempo;
- memória;
- falhas;
- formato;
- template;
- retries;
- dead letters.

## 23.4 Qualidade

- templates sem visual approval;
- render regression;
- overflow;
- broken links;
- fonte ausente;
- chart invalid;
- mismatch numérico;
- acessibilidade.

## 23.5 Linguagem humana

Exemplo:

> “O PDF do Relatório Executivo da Resulta falhou porque uma tabela excedeu o limite de página. O relatório web está disponível. Reprocessar com layout compacto.”

Não mostrar apenas stack trace.

---

# 24. Evals e quality gates

## 24.1 Integridade numérica

- KPI versus snapshot;
- tabela versus total;
- chart versus dados;
- percentual;
- moeda;
- rounding;
- período;
- missing values;
- comparação.

Tolerance deve ser explícita.

## 24.2 Conteúdo

- factualidade;
- source coverage;
- distinção fato/inferência;
- recomendações úteis;
- linguagem clara;
- ausência de promessa indevida;
- cobertura específica somente com evidência;
- nenhuma PII desnecessária.

## 24.3 Visual

- screenshots golden;
- web desktop/mobile;
- PDF páginas;
- PPTX slides renderizados;
- DOCX preview;
- XLSX opening test;
- overflow;
- clipping;
- fontes;
- contraste;
- whitespace;
- densidade;
- gráfico legível.

## 24.4 Segurança

- tenant A/B;
- usuário sem acesso;
- token expirado;
- token revogado;
- token alterado;
- brute force/rate limit;
- path traversal;
- zip slip;
- HTML injection;
- SVG injection;
- CSV injection;
- asset SSRF;
- secret redaction;
- global knowledge extraction.

## 24.5 Formato

### PDF

- abre;
- texto pesquisável;
- páginas corretas;
- metadata;
- sem corte.

### XLSX

- abre no Excel/LibreOffice;
- tipos;
- fórmulas;
- abas;
- filtros.

### PPTX

- abre no PowerPoint/LibreOffice;
- slides;
- editabilidade;
- overflow.

### DOCX

- abre;
- estilos;
- editabilidade;
- imagens;
- tabelas.

## 24.6 Visual regression process

1. render fixture;
2. gerar screenshot/imagem de páginas;
3. comparar com golden;
4. threshold por região;
5. revisão humana em mudança intencional;
6. atualizar golden com aprovação e changelog.

## 24.7 Broker Outcome Regression Pack

### Relatório semanal

- dados reais da corretora;
- sem dados de outra;
- mensagem WhatsApp curta;
- link funciona;
- PDF e web consistentes;
- sem módulos desconectados fingindo dados.

### Documento

- análise;
- referências;
- PDF/DOCX;
- download privado.

### Pesquisa

- dossiê;
- fontes;
- datas;
- PDF/web;
- sem fonte inventada.

### Planilha

- XLSX/CSV;
- tipos;
- filtros;
- sem CSV injection.

### Apresentação

- PPTX editável;
- slides legíveis;
- dados consistentes.

### Evidence Pack

- hashes;
- evidence privada;
- ZIP seguro;
- sem segredo.

---

# 25. Observabilidade e custos

Registrar:

- artifact type;
- template/release;
- version;
- render format;
- renderer version;
- Work Run/Skill;
- tenant;
- duração de cada step;
- bytes;
- páginas/slides/abas;
- LLM tokens da narrativa;
- custo do renderer;
- storage;
- delivery;
- views/downloads;
- share links;
- falhas;
- retries;
- quality score.

Dashboards mínimos:

- artifacts por tenant/tipo;
- sucesso de render;
- p95 por formato;
- storage por tenant;
- custo por template;
- falhas por renderer;
- shares ativos;
- links expirados;
- downloads;
- entregas;
- templates mais usados;
- artifacts nunca abertos;
- regressões visuais.

Não registrar conteúdo integral por padrão.

---

# 26. SLOs iniciais

Excluindo coleta externa e LLM:

- criação de metadata: p95 ≤ 300 ms;
- preview web após spec pronto: p95 ≤ 3 s;
- PDF até 20 páginas: p95 ≤ 20 s;
- XLSX até 50 mil linhas: p95 ≤ 30 s;
- CSV até 100 mil linhas: p95 ≤ 20 s;
- PPTX até 20 slides: p95 ≤ 30 s;
- DOCX até 50 páginas: p95 ≤ 30 s;
- chart SVG: p95 ≤ 2 s;
- download auth: p95 ≤ 500 ms antes do redirect/stream;
- share link resolution: p95 ≤ 500 ms;
- zero perda de artifact após restart;
- checksum obrigatório;
- render retry sem versão duplicada.

Limites deverão ser configuráveis e ajustados com dados reais.

---

# 27. Migração do legado

## 27.1 Weekly Report

Fluxo novo:

```text
scheduler/Rotina semanal
→ Work Run
→ Skill report.executive_weekly
→ Artifact Version
→ web/PDF
→ mensagem WhatsApp resumida
→ delivery registrada
```

O Redis marker legado pode permanecer temporariamente apenas para evitar duplicidade durante o cutover. Depois, idempotência do Work Run/Rotina assume autoridade.

## 27.2 Relatórios e páginas existentes

Inventariar:

- telas com Recharts;
- relatórios Admin;
- exports CSV existentes;
- mensagens semanais;
- documentos enviados;
- screenshots/evidence;
- qualquer arquivo gerado manualmente.

Mapear:

```text
fonte legada
→ Artifact Type
→ Template
→ Work Run/Skill
→ retention
→ access policy
```

## 27.3 Cutover

Ao final:

- toda nova geração usa Artifact Hub;
- weekly report usa Artifact Hub;
- nenhum PDF novo é criado fora do Hub;
- nenhuma URL pública permanente;
- nenhuma entrega sem `artifact_deliveries`/effect;
- nenhuma template string solta como autoridade;
- reports antigos permanecem acessíveis conforme política;
- novos reports ativos em produção.

---

# 28. BLOCO A — Fundação do Artifact Hub e renderer

## Objetivo

Criar schema, contracts, Orchestrator, renderer, MinIO namespace, segurança e formatos básicos.

## Entregas

- migrations;
- repositories;
- Artifact Spec schemas Pydantic/Zod;
- Chart Spec;
- Artifact Orchestrator;
- renderer service;
- signed render jobs;
- MinIO artifact service;
- checksums;
- HTML/web renderer;
- PDF renderer Playwright;
- ECharts web/SSR;
- XLSX;
- CSV;
- PPTX;
- DOCX;
- SVG/PNG;
- ZIP Evidence Pack;
- RLS e indexes;
- Work Run integration;
- Tool Gateway tools;
- security tests;
- Admin read-only básico.

## Gate

- schema reproduzível;
- renderer isolado;
- sem secret;
- buckets privados;
- formats abrem;
- checksum correto;
- tenant tests;
- idempotência;
- restart recovery;
- rollback documentado.

---

# 29. BLOCO B — Report Studio, templates, compartilhamento e entrega

## Objetivo

Construir a experiência de produto e publicar templates reais.

## Entregas

- Artifact Library;
- Artifact Detail;
- chat cards;
- Report Studio;
- share links;
- download;
- WhatsApp delivery;
- e-mail delivery;
- tenant Brand Profile;
- templates 17.1–17.8;
- data/calculation registry inicial;
- narrative verification;
- visual/chart validation;
- version history;
- preview/review/publish;
- Admin mínimo;
- events/metrics.

## Gate

- templates geram formatos previstos;
- fontes e cálculos reconciliam;
- share/access seguro;
- delivery idempotente;
- UI humana;
- mobile;
- sem dados cruzados;
- relatório semanal funcionando pelo Hub.

---

# 30. BLOCO C — Visual Acceptance, cutover e lançamento

## Objetivo

Finalizar design, migrar legado, ativar produção e comprovar valor.

## Entregas

- Visual Acceptance Pack;
- ajustes aprovados;
- golden screenshots;
- cutover weekly report;
- templates publicados;
- renderer ativo;
- Artifact Hub ativo;
- Work Runs gerando artifacts;
- Authority Strict e policies;
- canário Amandus → Resulta → AutoFleet;
- deploy;
- runbook;
- relatório final.

## Gate

- Founder aprovou visuais;
- Broker Outcome Regression Pack verde;
- PDF/web coerentes;
- arquivos editáveis;
- links seguros;
- delivery real;
- Resulta/AutoFleet isoladas;
- nenhum caminho paralelo ativo;
- nenhuma flag deixando recurso desligado;
- versão de lançamento em produção.

---

# 31. Arquivos e áreas prováveis

O executor confirma no código real.

## Backend

```text
backend/app/services/artifact_hub/
backend/app/api/artifacts.py
backend/app/services/minio_service.py
backend/app/services/weekly_report.py
backend/app/services/whatsapp_service.py
backend/app/services/delivery/
backend/app/agents/tools/artifact_tools.py
backend/app/skills/... manifests da SPEC-056
Work Run/Tool Gateway services
```

## Renderer

Sugestão:

```text
artifact-renderer/
  src/contracts/
  src/templates/
  src/renderers/html/
  src/renderers/pdf/
  src/renderers/charts/
  src/renderers/xlsx/
  src/renderers/csv/
  src/renderers/pptx/
  src/renderers/docx/
  src/renderers/evidence-pack/
  src/security/
  src/validation/
  Dockerfile
```

Pode ficar dentro do Web/monorepo se houver isolamento operacional equivalente. Não colocar Chromium arbitrário dentro do processo principal sem limites.

## Web

```text
app/dashboard/artifacts/
app/dashboard/relatorios/
app/api/artifacts/
app/s/[token]/
components/artifacts/
components/reports/
components/charts/
lib/artifacts/
```

## Admin

```text
app/admin/artifacts/
app/admin/artifact-templates/
app/admin/artifact-renderer/
```

## Banco

```text
backend/supabase/migrations/
```

## Design

```text
docs/canon/design/spec057-artifact-hub/
```

---

# 32. Definition of Done

A SPEC-057 só está concluída quando:

## Fundação

- [ ] Artifact Hub é a única autoridade de artifacts novos.
- [ ] Work Run cria e acompanha artifact.
- [ ] Skill Release declara output contract.
- [ ] Tool Gateway governa render e delivery.
- [ ] MinIO privado armazena bytes.
- [ ] Snapshots e sources possuem lineage.
- [ ] Versões são imutáveis.
- [ ] Renderers são idempotentes.

## Formatos

- [ ] Web funciona.
- [ ] PDF funciona.
- [ ] XLSX funciona.
- [ ] CSV funciona.
- [ ] PPTX funciona.
- [ ] DOCX funciona.
- [ ] SVG/PNG funcionam.
- [ ] Evidence Pack funciona.

## Produto

- [ ] Artifact Library funciona.
- [ ] Report Studio funciona pelo chat.
- [ ] Preview e publicação funcionam.
- [ ] Histórico e versões funcionam.
- [ ] Downloads funcionam.
- [ ] Share links são seguros.
- [ ] WhatsApp entrega.
- [ ] E-mail entrega.
- [ ] Relatório semanal usa o Hub.

## Qualidade

- [ ] Métricas reconciliam.
- [ ] Charts são honestos.
- [ ] Narrativas têm fontes.
- [ ] Visual Acceptance Pack aprovado.
- [ ] Visual regression verde.
- [ ] Acessibilidade mínima verde.
- [ ] Nenhum overflow crítico.

## Segurança

- [ ] Zero bucket público.
- [ ] Zero secret em artifact/render/log.
- [ ] Tenant isolation verde.
- [ ] Token expirado/revogado bloqueia.
- [ ] CSV/SVG/HTML/ZIP injection testados.
- [ ] Global Knowledge não exportável.

## Lançamento

- [ ] Amandus verde.
- [ ] Resulta verde.
- [ ] AutoFleet verde.
- [ ] Deploy concluído.
- [ ] Recurso ativo.
- [ ] Runbook publicado.
- [ ] Relatório final publicado.

---

# 33. Rollback

Rollback deve preservar artifacts já gerados.

## Aplicação

- reativar release anterior de template;
- reativar renderer anterior;
- impedir novas gerações temporariamente se necessário;
- manter downloads existentes autorizados;
- reverter weekly report para mensagem curta somente como emergência;
- não apagar versions/renders;
- registrar incidente e motivo.

## Banco

- migrations expand-only durante lançamento;
- não dropar colunas/tabelas nesta SPEC;
- desativar path novo por flag emergencial;
- preservar rows;
- contract posterior somente após estabilidade.

## Renderer

- runs existentes pinados à versão;
- nova geração usa release estável;
- renders falhos podem ser reprocessados;
- nenhum overwrite de bytes confirmados.

---

# 34. Proibições absolutas

- não criar segundo cérebro;
- não criar segundo Work Run;
- não criar segundo Tool Gateway;
- não criar storage paralelo;
- não salvar arquivo grande no Postgres;
- não usar bucket público;
- não gerar número via LLM sem cálculo/fonte;
- não permitir HTML/CSS/JS livre do tenant;
- não expor service role ao renderer;
- não usar link permanente;
- não sobrescrever versão publicada;
- não enviar artifact sem autorização;
- não exportar conhecimento global;
- não concluir com templates fake;
- não concluir com somente PDF;
- não concluir com UI sem backend real;
- não declarar lançamento com recurso desligado.

---

# 35. Relatório final obrigatório do executor

Publicar documento com:

1. commit inicial e final;
2. arquivos alterados;
3. migrations aplicadas;
4. tabelas/índices/policies;
5. dependências e licenças;
6. arquitetura final;
7. renderer/deploy;
8. formatos implementados;
9. templates publicados;
10. Visual Acceptance Pack e aprovação;
11. testes executados;
12. resultados Amandus/Resulta/AutoFleet;
13. evidências web/PDF/XLSX/PPTX/DOCX;
14. segurança;
15. custos/SLOs;
16. rollback;
17. flags finais;
18. pendências reais, sem esconder;
19. confirmação de que o caminho novo está ativo.

---

# 36. Relação com próximas SPECs

## SPEC-058 — Auxiliary & Routine Factory

Usará Artifact Hub para que Auxiliares e Rotinas entreguem relatórios, briefings, planilhas, apresentações e evidências.

## SPEC-059 — Briefing, Proatividade & Garimpo v3

Usará templates de Briefing e relatórios de oportunidades.

## SPEC-060 — Research Intelligence

Usará Dossiê, Research Report, fontes e Evidence Pack.

## SPEC-061 — Portal Admin Control Plane

Expandirá governança, métricas e operações do Artifact Hub.

## SPEC-062 — Evals, Billing, Rollout & Production Readiness

Expandirá cobrança, limites e evals globais.

Nenhuma delas criará outro Artifact Hub.

---

# 37. Referências técnicas modeladas

A implementação deve revisar as versões oficiais atuais antes de fixar dependências.

Princípios incorporados:

- Playwright `page.pdf()` para PDF a partir de HTML/CSS;
- Apache ECharts com renderização browser e SSR SVG;
- MinIO/S3 object versioning e lifecycle como proteção física complementar;
- PptxGenJS para apresentações editáveis;
- ExcelJS para XLSX;
- biblioteca `docx` para Word editável;
- templates declarativos e versionados;
- visual regression e validação determinística;
- zero confiança implícita em conteúdo externo.

---

# 38. Checklist executivo de implementação

```text
[ ] atualizar main e ler SPECs 052–057
[ ] confirmar schema, MinIO, Work Runs e Tool Gateway
[ ] criar migrations e contracts
[ ] criar Artifact Orchestrator
[ ] criar renderer determinístico
[ ] implementar todos os formatos
[ ] criar snapshots/sources/checksums
[ ] criar web report/PDF
[ ] criar Artifact Library e Report Studio
[ ] criar links/download/delivery
[ ] publicar templates iniciais
[ ] migrar weekly report
[ ] criar Visual Acceptance Pack
[ ] executar evals e segurança
[ ] validar Amandus, Resulta e AutoFleet
[ ] fazer deploy e ativar
[ ] publicar relatório final
```

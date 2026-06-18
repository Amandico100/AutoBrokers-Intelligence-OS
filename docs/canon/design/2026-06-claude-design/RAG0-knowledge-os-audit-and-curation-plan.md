# RAG0 — AutoBrokers Knowledge OS Audit & Curation Plan

**Status:** auditoria RAG0 concluída como plano canônico inicial  
**Data:** 2026-06-18  
**Projeto:** AutoBrokers.ai / AutoBrokers Intelligence OS  
**Frente:** Knowledge OS / RAG / Memory / Curadoria  
**Destino:** `docs/canon/design/2026-06-claude-design/RAG0-knowledge-os-audit-and-curation-plan.md`

---

## 0. Decisão executiva

A frente RAG0 não deve começar por upload em massa. A decisão correta é preservar o Smith como runtime, auditar a infraestrutura existente e organizar uma camada de conhecimento escopada, auditável, versionada e segura.

Nesta execução foram auditados os artefatos disponíveis do repositório, SPECs canônicas, serviços backend, UI admin, snapshot Supabase, materiais do Smith, estrutura visual de RAG/memória e inventário estrutural dos pacotes de intake. Nenhum documento foi ingerido em RAG, nenhum banco vetorial paralelo foi criado e nenhuma estrutura existente foi removida.

Conclusão principal: **o Smith já possui base RAG suficiente para ser reaproveitada**, com MinIO, Supabase, Qdrant, busca híbrida, rerank, ingestion, benchmark e memória. O trabalho agora é corrigir lacunas de governança, escopo, autenticação, schema e integração runtime antes de alimentar conhecimento real.

---

## 1. Fontes auditadas

### 1.1 Repositório AutoBrokers Intelligence OS

Auditado localmente a partir do pacote do repositório e validado acesso GitHub ao repositório `Amandico100/AutoBrokers-Intelligence-OS`, branch `main`.

Arquivos canônicos auditados:

- `docs/canon/SPEC-003-knowledge-rag-memory.md`
- `docs/canon/SPEC-004-agent-intelligence-context-architecture.md`
- `docs/canon/SPEC-005-atendimento-runtime-architecture.md`
- `docs/canon/SPEC-007-atendimento-producao-autonomo.md`
- `docs/canon/SPEC-008-producao-global-autobrokers.md`
- `docs/canon/SPEC-010-rag-knowledge-memory-curation-autobrokers-smith.md`
- `docs/canon/SPEC-011-portal-browser-relay-action-engine-autobrokers-smith.md`
- `docs/canon/design/2026-06-claude-design/41C.0-knowledge-rag-memory-recon.md`
- `docs/canon/design/2026-06-claude-design/41C.1-*`
- `docs/canon/design/2026-06-claude-design/41C.2B-global-knowledge-runtime-foundation-report.md`
- `docs/canon/design/2026-06-claude-design/42R0-attendance-knowledge-rag-safe-context-report.md`
- `docs/sql/41C0-knowledge-rag-diagnostics.sql`
- `docs/sql/41C15-local-rag-acceptance-diagnostics.sql`
- `docs/sql/41C1-documents-rls-policies.sql`

### 1.2 Backend Smith / RAG / Memory

Serviços auditados:

- `backend/app/services/document_service.py`
- `backend/app/services/ingestion_service.py`
- `backend/app/services/search_service.py`
- `backend/app/services/qdrant_service.py`
- `backend/app/services/rerank_service.py`
- `backend/app/services/benchmark_service.py`
- `backend/app/services/sanitization_service.py`
- `backend/app/services/filesystem_search_service.py`
- `backend/app/services/memory_service.py`
- `backend/app/services/langchain_service.py`
- `backend/app/services/knowledge_scope.py`

Rotas auditadas:

- `backend/app/api/documents.py`
- `backend/app/api/sanitization.py`

### 1.3 Frontend/admin

Componentes auditados:

- `components/admin/DocumentManagementModal.tsx`
- `components/admin/BenchmarkModal.tsx`
- `components/admin/SanitizationModal.tsx`
- `components/admin/MemoryConfigTab.tsx`
- `app/admin/knowledge-base/sanitize/page.tsx`
- `app/api/admin/proxy/documents/[[...path]]/route.ts`
- `app/api/admin/memory/settings/route.ts`
- `app/api/admin/memory/user/[userId]/route.ts`
- `app/api/sanitization/*`
- `lib/admin-proxy.ts`
- `middleware.ts`

### 1.4 Supabase snapshot

Auditado snapshot metadata-only `SUPABASE_SCHEMA_SNAPSHOT_AUTOBROKERS_2026_05`, com foco em:

- schema `public`
- schema `rag`
- tabelas de documentos, chunks, sources, ingestion jobs, feedback, exemplars, conversation threads/messages
- tabelas de memória `user_memories`, `session_summaries`, `memory_settings`
- tabelas operacionais `cases`, `policies`, `case_evidence`, `protocol_*`, `broker_*`, `agents`, `companies`

### 1.5 Drive/Agent OS/Intake

Auditados como referência estrutural e conceitual:

- `README.md` do AutoBrokers Agent OS
- `AULAS SOBRE RAG DO SMITH.txt`
- `INFORMAÇÕES SMITH.txt`
- `INTAKE (2).zip` apenas por inventário estrutural
- `PORTAL ADMIN.zip` apenas por inventário visual
- screenshot da UI RAG/admin enviada na conversa

O pacote `INTAKE` contém grande volume de PDFs, imagens, áudios, exports e arquivos potencialmente sensíveis. Status: **quarentena de curadoria**. Não deve ser indexado bruto.

---

## 2. Auditoria da estrutura atual

### 2.1 O que já existe e deve ser reaproveitado

O Smith já possui uma cadeia RAG real:

1. upload de arquivo pelo admin;
2. armazenamento do original no MinIO;
3. extração de texto/raw JSON;
4. registro de metadados no Supabase;
5. ingestão assíncrona;
6. chunking por estratégia;
7. embeddings densos OpenAI;
8. sparse BM25 com fastembed;
9. indexação no Qdrant;
10. busca híbrida;
11. rerank via Cohere quando configurado;
12. fallback/HyDE no `search_service`;
13. benchmark de estratégia;
14. memória por agente/usuário via `memory_service`.

Não há justificativa para criar um RAG paralelo neste momento.

### 2.2 Como o RAG semântico atual funciona

```txt
Admin UI
  → app/api/admin/proxy/documents
  → backend /documents/upload
  → DocumentService
  → MinIO original + raw JSON
  → public.documents
  → IngestionService background
  → chunks + embeddings
  → Qdrant collection company_{company_id}
  → SearchService.smart_search
```

O Qdrant usa coleção por empresa:

```txt
company_{company_id_normalizado}
```

O payload dos pontos contém `document_id`, `agent_id`, `chunk_index`, `content`, `metadata` e extras de knowledge quando disponíveis.

### 2.3 Busca híbrida atual

O `search_service.py` implementa busca híbrida com:

- dense vector search;
- sparse BM25;
- merge/cascade;
- rerank;
- threshold;
- fallback lexical;
- HyDE opcional;
- `include_global` ainda desativado por padrão.

### 2.4 Escopo atual

O `knowledge_scope.py` já introduz conceitos importantes:

- `tenant`
- `agent`
- `global_autobrokers`
- `global_carrier`
- `workflow`
- `connector`
- coleção global planejada: `autobrokers_global`
- `curation_status = published`
- payload extras como `scope`, `knowledge_class`, `namespace`, `version`, `visibility`, `valid_until`, `source_hash`, `carrier_slug`, `product_slug`

Mas a UI ainda não força escopo/audiência/sensibilidade/publicação. Na prática, o admin ainda opera principalmente por `company_id + agent_id + strategy`.

### 2.5 File System Search atual

O modo `filesystem` existe, mas com uso restrito:

- aceita `.md`;
- exige agente;
- não indexa no Qdrant;
- armazena/associa documento como fonte de busca textual/outline;
- é útil para documentos canônicos longos de agente específico, não para corpus bruto.

### 2.6 Benchmark atual

O Benchmark atual testa estratégia de ingestão/chunking por documento, mas ainda não cobre integralmente:

- vazamento de PII;
- confirmação indevida de cobertura;
- fonte/provenance obrigatória;
- cross-tenant leakage;
- diferença entre conhecimento interno e externo;
- autorização por audiência.

Portanto, ele deve ser mantido e ampliado para um benchmark de segurança e qualidade de Knowledge OS.

### 2.7 Sanitização atual

Existe uma rota e UI de sanitização separada. Ela deve ser tratada como pré-etapa obrigatória para materiais sensíveis, especialmente:

- conversas reais;
- prints;
- documentos com CPF/CNPJ/telefone/endereço;
- PDFs de apólices;
- materiais de seguradora com dados de clientes;
- exports WhatsApp;
- áudios/transcrições.

---

## 3. Principais riscos encontrados

### P0 — Corrigir antes de produção ou ingestão real sensível

1. **Risco de autenticação no proxy admin de documentos.**
   - `middleware.ts` trata rotas `/api/*` como públicas/sem proteção.
   - `app/api/admin/proxy/documents/[[...path]]/route.ts` chama `authenticatedProxy`.
   - `lib/admin-proxy.ts` injeta `X-Admin-API-Key` no backend.
   - Não foi encontrada validação forte de sessão nessa rota antes do proxy.
   - Resultado: risco de endpoint admin expor operações de documentos se acessível externamente.

2. **Drift de schema em `public.documents`.**
   - O código atual insere/usa campos como `scope` e extras de knowledge.
   - A migration base `schema_completo.sql` auditada não inclui todos esses campos.
   - Scripts diagnósticos posteriores assumem campos como `scope`, `knowledge_class`, `curation_status`.
   - É necessário confirmar o schema real do Supabase atual ou criar migration de alinhamento.

3. **Attendance RAG ainda não está conectado ao RAG real do Smith.**
   - Há reports e funções future-ready.
   - A camada segura de snippets de Attendance parece curada/local, mas ainda não é retrieval canônico real com Qdrant + provenance.

4. **INTAKE contém material bruto sensível.**
   - O inventário indica grande volume de PDFs, imagens, áudios, contatos, conversas e documentos.
   - Status obrigatório: `quarantined`, não ingerir bruto.

5. **Schema `rag.*` existe no Supabase snapshot, mas não parece ser o runtime RAG atual do Smith.**
   - O runtime atual usa `public.documents` + MinIO + Qdrant.
   - O schema `rag` tem modelo rico para curadoria, redaction, sources e chunks, mas precisa de decisão arquitetural: camada de curadoria oficial ou legado/paralelo a assimilar.

### P1 — Corrigir no RAG1/RAG2

1. UI RAG não força `scope`, `audience`, `sensitivity`, `source_type`, `status`, `approval`.
2. `agent_id` é obrigatório para upload, o que dificulta knowledge tenant/global sem agente.
3. Global RAG (`autobrokers_global`) existe conceitualmente, mas precisa ser criado/operacionalizado.
4. Memory debug/user route precisa enforcement mais claro de `company_id`, `agent_id`, `role` e auditoria.
5. Benchmark precisa virar eval de segurança, não apenas escolha de chunking.
6. Provenance precisa aparecer no trace e no retorno runtime, especialmente Core/Jarvys.
7. Attendance não pode herdar documentos internos por erro de vínculo.

---

## 4. Mapa das tabelas Supabase usadas por RAG/memória

### 4.1 Runtime Smith atual — schema `public`

| Tabela | Uso atual/provável | Status RAG0 | Observação |
|---|---|---:|---|
| `public.documents` | Metadados dos arquivos enviados, status, estratégia, agente, MinIO, Qdrant | Ativa | Base do RAG Smith atual |
| `public.agents` | Configuração dos agentes, modelo, prompt, memory/retrieval settings | Ativa | Upload vincula documentos a agentes |
| `public.companies` | Isolamento multi-tenant | Ativa | Qdrant collection por empresa |
| `public.conversations` | Conversas do Smith/chat | Ativa | Não deve virar RAG bruto |
| `public.messages` | Mensagens das conversas | Ativa | Fonte para resumo/memória, não RAG bruto |
| `public.user_memories` | Fatos persistentes por usuário/agente | Ativa | Necessita isolamento rígido |
| `public.session_summaries` | Resumos de sessão por usuário/agente | Ativa | Entra no contexto via MemoryService |
| `public.memory_settings` | Configurações de memória por agente/canal | Ativa | UI já permite configurar WhatsApp/Web |
| `public.sanitization_jobs` | Jobs de sanitização | Ativa | Deve virar pré-etapa obrigatória para dados sensíveis |
| `public.cases` | Casos operacionais | Estruturada | Fonte determinística, não RAG aberto |
| `public.policies` | Apólices | Estruturada | Fonte de verdade parcial; não misturar com RAG geral |
| `public.case_evidence` | Evidências do caso | Estruturada | Usar para Evidence Pack/readiness |
| `public.protocol_*` | Protocolos/corredores | Estruturada | Pode gerar packs/procedural knowledge |
| `public.broker_*` | Perfis, playbooks, canais, integrações | Estruturada | Deve alimentar tenant knowledge com curadoria |

### 4.2 Schema `rag` do snapshot — possível camada de curadoria

| Tabela | Uso potencial | Status RAG0 | Decisão recomendada |
|---|---|---:|---|
| `rag.sources` | Fonte canônica com escopo, broker, insurer, validade, rank | Reaproveitável | Assimilar como registry de fontes ou mapear para public/Qdrant |
| `rag.documents` | Documento normalizado/redacted/aprovado para retrieval | Reaproveitável | Bom para camada Silver/Gold de curadoria |
| `rag.chunks` | Chunks textuais com metadados ricos e embedding | Atenção | Evitar segundo motor paralelo; usar como staging ou migrar |
| `rag.ingestion_jobs` | Jobs de ingestão | Atenção | RLS/segurança antes de expor |
| `rag.feedback` | Feedback de retrieval/resposta | Reaproveitável | Útil para evals e melhoria contínua |
| `rag.exemplars` | Exemplos/goldens | Reaproveitável | Excelente para evals e casos exemplo |
| `rag.conversation_threads` | Conversas redacted/aprovadas | Quarentena | Nunca usar conversa bruta |
| `rag.conversation_messages` | Mensagens redacted/aprovadas | Quarentena | Só após aprovação explícita |

### 4.3 Decisão sobre `rag.*`

Não tratar `rag.*` como novo runtime RAG agora. Três opções existem:

1. **Recomendado:** usar `rag.*` como camada de curadoria/staging e publicar somente para o pipeline Smith atual (`public.documents` → Qdrant).
2. **Alternativa:** migrar gradualmente o runtime para `rag.*`, com compatibilidade e testes.
3. **Não recomendado:** operar `rag.*` em paralelo sem governança, porque cria dois RAGs e aumenta risco de vazamento.

---

## 5. Mapa das rotas/API de upload, benchmark, sanitização e chunking

### 5.1 Backend documents API

| Rota | Função | Status | Observação |
|---|---|---:|---|
| `GET /documents/rag-health` | Diagnóstico MinIO/Qdrant/reranker/config | Ativa | Boa para healthcheck RAG |
| `POST /documents/rag-debug` | Busca debug master-only | Ativa | Retorna previews/metadados |
| `POST /documents/upload` | Upload semântico ou filesystem | Ativa | Exige `company_id` e `agent_id` |
| `GET /documents/` | Lista documentos por empresa/agente/status | Ativa | Base da UI |
| `GET /documents/chunks/{company_id}` | Lista chunks Qdrant do documento | Ativa | Útil para preview/provenance |
| `GET /documents/agent/{agent_id}/stats` | Stats por agente | Ativa | Útil para admin |
| `GET /documents/benchmark/eligible` | Docs elegíveis para benchmark | Ativa | Exclui CSV/filesystem |
| `POST /documents/benchmark/start` | Dispara benchmark | Ativa | Usa Redis/job |
| `GET /documents/benchmark/status/{job_id}` | Status benchmark | Ativa | UI acompanha job |
| `GET /documents/{document_id}` | Detalhe do documento | Ativa | Precisa policy de acesso |
| `DELETE /documents/{document_id}` | Remove doc + MinIO + Qdrant | Ativa | Operação sensível |
| `POST /documents/reprocess` | Reprocessa com estratégia | Ativa | Útil após benchmark |

### 5.2 Backend sanitization API

| Rota | Função | Status | Observação |
|---|---|---:|---|
| `POST /api/sanitization/upload` | Upload para sanitização | Ativa | Celery ou background task |
| `GET /api/sanitization/jobs` | Lista jobs | Ativa | Deve filtrar por company |
| `GET /api/sanitization/jobs/{job_id}` | Detalhe job | Ativa | Deve validar acesso |
| `GET /api/sanitization/download/{job_id}` | Baixa sanitizado | Ativa | Operação sensível |
| `DELETE /api/sanitization/jobs/{job_id}` | Remove job | Ativa | Operação sensível |

### 5.3 Frontend/admin proxy

| Rota | Função | Risco |
|---|---|---:|
| `app/api/admin/proxy/documents/[[...path]]/route.ts` | Proxy frontend → backend documents | P0 auth/session |
| `app/api/sanitization/*` | Proxy/rota sanitização | Revisar auth |
| `app/api/admin/memory/settings/route.ts` | Configura memória por agente | P1 role/company checks |
| `app/api/admin/memory/user/[userId]/route.ts` | Debug/delete memória usuário | P1 enforcement por tenant/agente |

---

## 6. Knowledge Scope Matrix

| Scope | Identificadores obrigatórios | Audiência padrão | Sensibilidade padrão | Pode ir para Attendance? | Exemplos | Status |
|---|---|---|---|---:|---|---|
| `global_autobrokers` | `scope`, `version`, `source_type`, `status` | `broker_internal`, `system`, `admin` | `internal` | Só subset aprovado | SPECs, seguros básicos, LGPD, vendas | Planejado |
| `global_carrier` / `insurer` | `insurer_key`, `line_kind`, `valid_until`, `provenance` | `broker_internal`, `insured_external` | `public/internal` | Sim, se público/safe | manuais Allianz/Porto/Tokio | Planejado |
| `tenant` | `company_id`, `status`, `audience` | `broker_internal` | `internal/confidential` | Só se marcado `insured_external` | regras Rafael/Resulta, horários, equipe | Parcial |
| `agent` | `company_id`, `agent_id`, `audience` | depende do agente | depende | depende | manual da Silvinha, Core, auxiliar sinistro | Atual dominante |
| `corridor` | `corridor_key`, `subcorridor_key`, `insurer_key` | `system`, `broker_internal`, `insured_external` | `internal` | Sim, se safe | Allianz residencial eletricista | Planejado |
| `workflow/playbook` | `workflow_key`, `macro_service`, `version` | `broker_internal/system` | `internal` | Só templates safe | follow-up, cobrança, renovação | Planejado |
| `case` | `case_id`, `company_id`, `customer_id` | `system/broker_internal` | `confidential` | Só próprio caso e sanitizado | Evidence Pack, readiness | Estruturado |
| `user` | `user_id`, `company_id`, `agent_id` | `system` | `confidential` | Apenas contexto do próprio usuário | preferências/resumos | Ativo como memória |
| `conversation_curated` | `conversation_id`, redaction status, approval | `broker_internal/system` | `confidential` | Só se transformado em FAQ/playbook | casos exemplo sanitizados | Quarentena |
| `vault/restricted` | `secret_ref`, `owner`, `policy` | `system/admin` | `restricted` | Nunca | credenciais, cookies, storageState | Fora do RAG |

---

## 7. Agent Knowledge Access Matrix

| Agente/camada | Pode acessar | Não pode acessar | Regra operacional |
|---|---|---|---|
| Core/Jarvys interno | global_autobrokers, tenant, insurer, product, corridor, playbooks, métricas, cases estruturados autorizados | credenciais, cookies, tokens, raw PII sem tool/role, segredo fora de vault | É o cérebro interno, mas com governança e provenance |
| AutoBrokers Sandbox | conhecimento amplo de teste, packs internos, docs de arquitetura | dados reais sensíveis sem necessidade | Tratar como Core sandbox até CEO confirmar papel oficial |
| Silvinha Attendance Sandbox | `insured_external`, FAQ segura, procedimentos, status do próprio caso, policy_snapshot/evidence do próprio atendimento | financeiro, comissão, estratégia, outros clientes, credenciais, gestão interna | Não vincular tudo à Silvinha |
| Attendance Agents externos | knowledge de atendimento seguro, seguradora/corredor, templates aprovados, dados mínimos do próprio caso | tenant_internal, admin, broker finance, outros cases | Não confirma cobertura via RAG |
| Auxiliar de Sinistro | procedimentos, documentos, prazos, seguradora, evidence pack, casos autorizados | credenciais e decisões finais sem humano/tool | Apoia, não decide cobertura final sozinho |
| Auxiliar de Renovação/Comercial | objeções, scripts, produtos, follow-up, tenant tone | sinistros sensíveis sem autorização | Pode gerar propostas de ação, não enviar sem policy |
| Auxiliar de Cobrança | cadências, scripts, status estruturado autorizado | dados bancários crus, cartões, tokens | Mensagens com cuidado e compliance |
| Admin Master/System | amplo, incluindo debug, benchmark, curation queue | exposição em contexto customer-facing | Toda ação sensível precisa audit trail |

---

## 8. Ingestion Pipeline canônico

```txt
0. Intake Registry / Quarantine
1. Upload ou seleção de fonte
2. Detecção de tipo e risco
3. Sanitização/redaction obrigatória quando sensível
4. Classificação de escopo/audiência/sensibilidade
5. Normalização para Markdown/JSON canônico
6. Extração de entidades e resumo canônico
7. Escolha de chunking
8. Enriquecimento de metadados/provenance/versionamento
9. Benchmark de retrieval/chunking
10. Evals de segurança
11. Aprovação humana/publicação
12. Indexação no Smith RAG existente
13. Runtime retrieval com filtros por tenant/agente/audiência
14. Observabilidade, feedback e revisão periódica
```

### Regras obrigatórias

- Upload bruto não é publicação.
- Sanitização não é só mascarar; também classifica destino permitido.
- Conversa real não entra como conversa real: vira padrão, FAQ, playbook ou caso exemplo sanitizado.
- Documento sem provenance fica `draft` ou `needs_review`.
- Documento externo deve ter validade/revisão (`valid_until` ou `last_reviewed_at`).
- Documento publicado para Attendance precisa `audience=insured_external` e `sensitivity=public/internal_safe`.

---

## 9. Sanitization Rules

### 9.1 Nunca entra no RAG

- credenciais;
- tokens;
- cookies;
- storageState;
- senhas;
- chaves de API;
- payloads privados de API;
- dados bancários;
- cartões;
- prints com sessão autenticada;
- documentos com segredo operacional sem redaction;
- conversas brutas não revisadas.

### 9.2 Remover, mascarar ou generalizar

- CPF;
- CNPJ quando não necessário;
- telefone;
- e-mail;
- endereço;
- placa/chassi quando não necessário;
- nomes de segurados;
- nomes de atendentes quando irrelevantes;
- números de apólice/sinistro/protocolo quando não forem parte de Evidence Pack específico;
- informações de saúde/financeiras/pessoais sensíveis.

### 9.3 Transformação correta de conversas reais

```txt
conversa bruta
  → quarentena
  → transcrição/OCR se necessário
  → redaction PII
  → extração de padrão
  → FAQ/playbook/caso exemplo
  → revisão humana
  → pack ativo
```

---

## 10. Chunking Rules

| Estratégia | Quando usar | Não usar para | Observação |
|---|---|---|---|
| IA Semântica / semantic | manuais, PDFs explicativos, condições gerais, procedimentos longos | CSV e documentos muito curtos | padrão inicial recomendado |
| Page by Page | PDF oficial, condições gerais, documento visual/escaneado, contrato | FAQ simples | preserva página/provenance |
| Agentic Chunking | playbooks de agente específico, documentos complexos já sanitizados | material bruto ou sensível sem revisão | caro; usar com curadoria |
| Recursive/Rápido | notas curtas, FAQs simples, textos pequenos | documentos com estrutura jurídica | bom para MVP/baixo custo |
| Tabela/CSV | planilhas, listas de portais, seguradoras, contatos, FAQ tabular | texto livre longo | chunk por linha/registro |
| File System Search | `.md` canônico de agente, documento que precisa navegação integral | corpus bruto de PDF/DOCX | não indexa Qdrant |

### Metadados mínimos por chunk

- `document_id`
- `chunk_index`
- `title`
- `summary`
- `source_title`
- `source_type`
- `scope`
- `company_id`
- `agent_id` quando aplicável
- `audience`
- `sensitivity`
- `insurer_key`
- `corridor_key`
- `subcorridor_key`
- `version`
- `curation_status`
- `provenance`
- `valid_until` / `last_reviewed_at`
- `usage_policy`

---

## 11. RAG Usage Policy

### 11.1 O que o RAG pode fazer

- explicar conceitos gerais;
- buscar procedimentos;
- recuperar trechos de manuais;
- sugerir próximos passos seguros;
- apoiar redação de respostas;
- enriquecer atendimento;
- apoiar Core/Jarvys em gestão e operação;
- apoiar auxiliares com playbooks específicos.

### 11.2 O que o RAG não pode fazer

- confirmar cobertura específica;
- garantir indenização;
- prometer prestador/protocolo/prazo não confirmado;
- substituir policy snapshot/InfoCap/Evidence Pack;
- autorizar dispatch;
- acionar seguradora;
- expor documentos internos para segurado;
- usar dados de outro tenant;
- usar conversa bruta como verdade.

### 11.3 Ordem de autoridade

```txt
Guardrails / Safety
  > Contratos e Action Gates
  > InfoCap / policy_snapshot / coverage_evidence / coverage_readiness
  > Dados estruturados do caso
  > Tenant policy autorizada
  > Knowledge pack curado
  > RAG global/seguradora
  > Inferência da LLM
```

---

## 12. Memory Type Matrix

| Tipo | Onde fica hoje | Escopo | Entra em RAG? | Uso |
|---|---|---|---:|---|
| Memória curta de sessão | LangGraph/checkpointer/conversation state | sessão/caso | Não | manter fluxo, perguntas pendentes |
| User profile memory | `public.user_memories` | company+agent+user | Não direto | preferências/fatos do usuário |
| Session summary | `public.session_summaries` | company+agent+user | Não direto | continuidade sem histórico infinito |
| Memória estruturada operacional | `cases`, `policies`, `case_evidence`, `protocol_*` | tenant/case | Não | decisões determinísticas |
| Semântica global | Qdrant/global planejado | global | Sim | seguros, gestão, compliance |
| Semântica tenant | Qdrant company collection | company | Sim | como a corretora trabalha |
| Episódica curada | futuro `rag.conversation_*` ou review queue | tenant/case | Só após curadoria | aprender com casos reais |
| Procedural/playbooks | docs/chunks/FS search | global/tenant/agent | Sim | como executar tarefas |
| Preferências do dono/corretor | futuro profile/memory curated | tenant/owner | Parcial | Jarvys pensar como a corretora |
| Performance/evals | feedback/exemplars/logs | system/admin | Não customer-facing | melhoria contínua |
| Agentic harvest | review queue futura | draft | Não automático | propostas de knowledge |

---

## 13. Knowledge packs iniciais

| Pack | Escopo | Audiência | Agentes | Fonte inicial | Status |
|---|---|---|---|---|---|
| AutoBrokers Canon Pack | global_autobrokers | broker_internal/system/admin | Core/Jarvys, builders | SPECs e reports canônicos | RAG2 |
| Insurance Fundamentals Pack | global_autobrokers | broker_internal/insured_external subset | Core, Attendance safe | curadoria nova | RAG2 |
| Attendance Safe Communication Pack | global_autobrokers + workflow | insured_external | Silvinha/Attendance | SPECs + templates | RAG2 |
| Compliance/LGPD Pack | global_autobrokers | broker_internal + safe external | Core, Attendance safe | curadoria nova | RAG2 |
| Allianz Residential Assistance Starter Pack | insurer/corridor | insured_external safe | Attendance, Sinistro | fontes oficiais/curadas | RAG2 |
| Portal Browser Knowledge Pack | workflow/connector | broker_internal/system | Core, Portal auxiliaries | portal-registry/SPEC-011 | RAG2 |
| Rafael Seguros Tenant Starter Pack | tenant | broker_internal + safe external subset | Core, Attendance safe | Resulta/Rafael curado | RAG2 |
| Sales & Renewals Pack | global/tenant | broker_internal | Core, Comercial/Renovação | playbooks curados | RAG2 |
| Claims/Sinistro Basics Pack | global/insurer | broker_internal/insured_external subset | Sinistro, Attendance | curadoria nova | RAG2 |
| Agent OS Assimilated Attendance Pack | workflow/playbook | system/insured_external subset | Attendance | Agent OS antigo assimilado | RAG2/RAG3 |
| Learning Review Queue Pack | draft/review | admin/system | curadoria | outputs de falhas/handoffs | RAG5 |

---

## 14. Plano de testes/evals

### 14.1 Testes técnicos

- upload semantic por agente;
- upload filesystem `.md` por agente;
- reprocessamento por estratégia;
- delete documento remove Qdrant/MinIO/metadata;
- benchmark roda e retorna ranking;
- preview de chunks retorna metadados/provenance;
- `rag-health` reflete MinIO/Qdrant/reranker;
- global collection não quebra quando ausente.

### 14.2 Testes de isolamento

- documento tenant A não aparece tenant B;
- documento agente A não aparece agente B;
- documento `broker_internal` não aparece no Attendance;
- documento `restricted` nunca entra em retrieval;
- memory user A não aparece user B;
- route admin exige sessão/role antes de proxy com Admin API Key.

### 14.3 Testes de segurança de conteúdo

- CPF fake é mascarado;
- telefone/e-mail/endereço são mascarados;
- token/cookie/storageState bloqueia publicação;
- conversa bruta fica em quarentena;
- resposta não confirma cobertura;
- resposta não promete protocolo/prestador/prazo sem evidência;
- fonte contraditória tenant vs global resolve por política de autoridade.

### 14.4 Evals por pack

Cada pack precisa de:

- 15 a 20 perguntas mínimas para benchmark inicial;
- perguntas positivas;
- perguntas negativas;
- perguntas ambíguas;
- perguntas com risco de cobertura;
- perguntas de escopo errado;
- goldens com resposta esperada;
- verificação de source/provenance;
- score mínimo de publicação.

---

## 15. Próximos batches de implementação

### RAG1 — Knowledge Scope Matrix & Admin UX

Objetivo: transformar o upload atual em curadoria governada.

Entregas:

1. Corrigir auth do proxy admin de documentos antes de qualquer exposição.
2. Confirmar/corrigir schema `public.documents` com campos de knowledge governance.
3. Adicionar UI obrigatória para `scope`, `audience`, `sensitivity`, `source_type`, `status`, `provenance`.
4. Adicionar preview de impacto: quais agentes podem acessar.
5. Criar status `draft`, `sanitized`, `approved`, `published`, `quarantined`, `deprecated`.
6. Adicionar bloqueio: Attendance só recebe `insured_external`.

### RAG2 — Curated Seed Packs

Objetivo: criar os primeiros packs pequenos, seguros e avaliáveis.

Entregas:

1. AutoBrokers Canon Pack interno.
2. Attendance Safe Communication Pack externo seguro.
3. Insurance Fundamentals Pack.
4. Compliance/LGPD Pack.
5. Rafael Seguros Tenant Starter Pack mínimo.
6. Allianz Residential Assistance Starter Pack.
7. Rodar benchmark/evals antes de publicar.

### RAG3 — Runtime Retrieval Integration

Objetivo: conectar runtime real ao RAG Smith com filtros e provenance.

Entregas:

1. Conectar `ATTENDANCE_KNOWLEDGE_URL` ao endpoint real do Smith.
2. Retornar snippets sanitizados com `source`, `scope`, `audience`, `confidence`.
3. Injetar snippets no Attendance sem permitir decisão de cobertura.
4. Core/Jarvys passa a usar tenant/global/internal com governança.
5. Adicionar traces de loadedDocuments/blockedDocuments.

### RAG4 — Evals, Benchmark & Source Provenance

Objetivo: tornar RAG mensurável e auditável.

Entregas:

1. Golden tests por pack.
2. Eval de PII.
3. Eval de cobertura indevida.
4. Eval de cross-tenant leakage.
5. Eval de source/provenance.
6. Dashboard ou relatório de benchmark por pack.

### RAG5 — Agentic Harvest / Learning Review Queue

Objetivo: permitir aprendizado sem autopublicação.

Entregas:

1. Capturar perguntas sem resposta.
2. Capturar handoffs recorrentes.
3. Gerar proposta de knowledge item.
4. Colocar em review queue.
5. Exigir humano antes de sanitizar/publicar.
6. Versionar e rodar eval antes de ativar.

---

## 16. Decisões pendentes para validação do Founder/CEO

1. O agente `AutoBrokers Sandbox` é o Core/Jarvys oficial ou apenas sandbox?
2. A `Silvinha Attendance Sandbox` será o primeiro Attendance externo oficial?
3. O conhecimento global deve usar a coleção Qdrant `autobrokers_global` ou uma company interna “AutoBrokers Global Knowledge”?
4. O schema `rag.*` deve virar camada oficial de curadoria/staging ou deve ser assimilado/deprecado?
5. O primeiro tenant real de curadoria será Rafael/Resulta somente ou inclui Autofleet?
6. Quais documentos da Rafael/Resulta podem ser usados como Tenant Starter Pack sem expor estratégia/comissão/gestão?
7. Quem aprova publicação de conhecimento global: Founder/CEO, Admin Master ou curador técnico?
8. Attendance deve citar fontes para segurado ou manter provenance apenas no trace/admin?
9. Company admin poderá publicar knowledge para Attendance sozinho ou precisa aprovação master?
10. Qual prioridade de produto: Core/Jarvys inteligente primeiro ou Attendance RAG real primeiro?
11. Como devem ser modeladas preferências do dono/corretor: memória do usuário, perfil da corretora ou tenant knowledge?
12. Existe taxonomia canônica final para `insurer_key`, `line_kind`, `corridor_key`, `subcorridor_key`?
13. O Supabase atual em produção já possui campos `scope`, `knowledge_class`, `curation_status` em `public.documents` ou eles estão apenas em scripts futuros?
14. Qual política de retenção para conversas/áudios/imagens do INTAKE?
15. Quais fontes oficiais de seguradora serão aceitas para o primeiro pack Allianz?

---

## 17. Checklist imediato antes de qualquer ingestão real

```txt
[ ] Corrigir/confirmar autenticação do proxy admin /api/admin/proxy/documents.
[ ] Confirmar schema real de public.documents no Supabase ativo.
[ ] Definir destino do schema rag.*.
[ ] Criar migration de governance fields se necessário.
[ ] Definir agente Core/Jarvys oficial e Attendance externo oficial.
[ ] Criar taxonomia mínima de scope/audience/sensitivity.
[ ] Criar primeiro pack pequeno em Markdown sanitizado.
[ ] Rodar benchmark/evals.
[ ] Publicar apenas depois de aprovação humana.
[ ] Não ingerir INTAKE bruto.
```

---

## 18. Conclusão RAG0

O AutoBrokers não precisa de um novo RAG. Ele precisa transformar o RAG do Smith em um **Knowledge OS governado**.

A infraestrutura atual é boa o suficiente para avançar, mas existem bloqueios importantes antes de produção: autenticação do proxy admin, drift de schema, falta de escopo/audiência explícitos na UI, falta de publicação/aprovação, e integração runtime do Attendance com RAG real.

A próxima execução recomendada é **RAG1 — Knowledge Scope Matrix & Admin UX**, começando por segurança e schema. Só depois disso faz sentido iniciar RAG2 com curated seed packs.

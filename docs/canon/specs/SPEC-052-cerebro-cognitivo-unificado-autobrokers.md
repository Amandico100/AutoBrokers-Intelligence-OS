# SPEC-052 — Cérebro Cognitivo Unificado do AutoBrokers

**Produto:** AutoBrokers Intelligence OS  
**Status:** CANÔNICA — aprovada pelo Founder em 23/07/2026  
**Autoridade:** esta SPEC é a fonte soberana para arquitetura de conhecimento, memória, contexto, aprendizagem, ferramentas e projeção do Segundo Cérebro do AutoBrokers.  
**Nome oficial do agente central:** **AutoBrokers**. “Jarvys/Jarvis” é apenas uma metáfora de capacidade e não deve aparecer como marca, agente ou componente visível.  
**Runtime técnico preservado:** Smith + LangGraph/LangChain + Supabase + Qdrant + MinIO + Redis.  
**Escopo desta SPEC:** arquitetura cognitiva unificada. A evolução avançada do harness, Skills, plugins, conectores, MCPs e toolsets do chat principal será detalhada em SPEC posterior, subordinada a esta arquitetura.

---

## 0. Aviso de autoridade e superação

Esta SPEC consolida e atualiza decisões distribuídas em documentos anteriores.

Em caso de conflito, **a SPEC-052 prevalece** sobre:

- `SPEC-003 — Knowledge/RAG/Memory Architecture`;
- `SPEC-004 — Agent Intelligence, Context Assembly & Role Architecture`;
- `SPEC-008 — Produção Global AutoBrokers`;
- `SPEC-010 — RAG, Knowledge, Memory & Curation`;
- `SPEC-034 — Harness Robusto Multiagente`;
- `SPEC-040 — Espelho, visão operacional e central de agentes`;
- `SPEC-044 — Três Camadas: Global, Corretora e Usuário`;
- relatórios 41C, 42A, RAG0 e demais documentos históricos relacionados.

Esses documentos **não devem ser apagados**. Permanecem como histórico, detalhamento técnico e evidência de evolução. Só podem ser usados quando não contradisserem esta SPEC.

Regra para qualquer agente de desenvolvimento:

```text
Antes de alterar RAG, memória, contexto, aprendizagem, ferramentas ou conhecimento,
leia primeiro a SPEC-052.
Em conflito, pare e solicite decisão do CEO/Founder.
```

---

## 1. Visão do produto

O AutoBrokers deve ser o sistema cognitivo central da corretora de seguros.

Ele deve combinar:

- inteligência nativa de uma LLM de ponta;
- conhecimento global proprietário do AutoBrokers;
- conhecimento privado da corretora;
- memória pessoal do usuário;
- conversas e experiências operacionais;
- dados vivos de InfoCap, Quiver, Segfy, Capta ou outros sistemas;
- Atlas de rotas e playbooks;
- documentos e evidências oficiais;
- pesquisa na internet;
- conectores, APIs, MCPs, Skills e ferramentas;
- execução governada de tarefas;
- observabilidade, segurança e aprovação humana.

Objetivo de negócio:

```text
Colocar dinheiro no bolso do corretor,
reduzir trabalho manual,
resolver problemas,
aumentar capacidade operacional,
melhorar vendas, retenção e atendimento,
e tornar o AutoBrokers indispensável pelo valor entregue diariamente.
```

O AutoBrokers não é apenas um chatbot, um RAG ou um conjunto de automações. É uma infraestrutura cognitiva verticalizada para corretoras de seguros.

---

## 2. Decisão arquitetural central

### 2.1 Um único cérebro lógico

O AutoBrokers terá **um único cérebro lógico**, governado pelo Smith Cognitive Runtime.

Um cérebro único não significa um único banco físico. Significa:

- uma autoridade única de contexto;
- uma política única de recuperação;
- uma autoridade única de publicação;
- uma fila única de aprendizagem;
- uma governança única de capabilities;
- um único contrato de provenance;
- um único sistema de avaliação e tracing.

### 2.2 Órgãos especializados

```text
AutoBrokers Cognitive Runtime
├── Supabase: catálogo, fatos, permissões, memória e auditoria
├── MinIO: documentos e artefatos originais
├── Qdrant: índices semânticos derivados
├── Redis: estado transitório, filas, locks e cache
├── Atlas: rotas e procedimentos executáveis
├── Sistemas conectados: dados operacionais vivos
├── Ferramentas/APIs/MCPs: leitura e ação
└── LLMs: raciocínio, síntese, planejamento e composição
```

Nenhum desses componentes constitui um cérebro paralelo.

### 2.3 Proibições estruturais

É proibido, sem aprovação expressa do CEO/Founder:

- criar um segundo motor de RAG;
- instalar outro provider de memória como autoridade paralela;
- criar outra coleção global de runtime;
- permitir que agentes publiquem diretamente no conhecimento global;
- gravar conversa bruta diretamente no RAG global;
- misturar dados de corretoras;
- usar documentos não curados como conhecimento global;
- transformar ferramentas ou MCPs em “memória”;
- carregar todo o acervo no prompt;
- substituir o Smith por outro runtime.

---

## 3. Estado auditado em 23/07/2026

### 3.1 Fundações presentes

O sistema já possui:

- upload de documentos;
- MinIO;
- Supabase;
- Docling/extração;
- chunking;
- embeddings densos;
- busca lexical/BM25;
- busca híbrida;
- Qdrant;
- reranking;
- HyDE;
- LangGraph/LangChain;
- tabelas de memória;
- Capability Registry;
- três camadas Global/Corretora/Usuário;
- Atlas de rotas;
- Observador, Espelho, Tecelão, Destilador, Garimpo e Conselho em diferentes graus de maturidade.

### 3.2 Problemas confirmados

1. A recuperação global possui dois caminhos concorrentes:
   - `autobrokers_global`;
   - `company_<GLOBAL_KNOWLEDGE_COMPANY_ID>`.
2. O segundo caminho não aplica a mesma curadoria do primeiro.
3. O conhecimento global pode ser ligado por environment sem respeitar integralmente a capability do agente.
4. Bindings de capabilities existem, mas seus `scope` estão majoritariamente vazios.
5. Provenance retornada ao runtime é insuficiente.
6. `valid_until`, namespace, versão e audiência não governam toda a recuperação.
7. Diagnósticos de RAG podem divergir do comportamento real.
8. A empresa técnica `AutoBrokers Global Knowledge` possui zero documentos cadastrados no Supabase no snapshot auditado.
9. O corpus global real é mínimo.
10. Conversas são registradas, mas o ciclo de consolidação produz pouco ou nenhum objeto de memória e conhecimento.
11. No snapshot auditado:
    - `conversation_logs`: 523;
    - `knowledge_cards`: 0;
    - `broker_insights`: 0;
    - `conduct_playbooks`: 0;
    - `playbook_overlays`: 0;
    - `session_summaries`: 0;
    - `user_memories`: 0;
    - `agent_memories`: 7.
12. Capabilities existem no catálogo, mas MCPs e ferramentas HTTP ainda não estavam materializados:
    - `mcp_servers`: 0;
    - `agent_mcp_connections`: 0;
    - `agent_mcp_tools`: 0;
    - `agent_http_tools`: 0.

### 3.3 Veredito

A base do Smith deve ser preservada. O problema não exige reconstrução integral. Exige consolidação de autoridade, fechamento de caminhos legados, ativação real do Context Assembly e governança do aprendizado.

---

## 4. Arquitetura canônica das camadas

### 4.1 Conhecimento Global AutoBrokers

Conteúdo compartilhado entre corretoras:

- fundamentos de seguros;
- legislação e normas;
- condições gerais e especiais;
- seguradoras, produtos e ramos;
- procedimentos oficiais;
- vendas, marketing e gestão;
- contabilidade e administração;
- playbooks globais;
- padrões anonimizados e agregados;
- rotas globais validadas;
- conhecimento autoral AutoBrokers.

**Única coleção semântica global de runtime:**

```text
autobrokers_global
```

A empresa técnica `AutoBrokers Global Knowledge` é a sala administrativa da biblioteca. Ela não é um segundo RAG.

### 4.2 Conhecimento da Corretora

Conteúdo privado do tenant:

- documentos internos;
- regras próprias;
- equipe;
- processos;
- carteira;
- integrações;
- relatórios;
- políticas locais;
- playbooks locais;
- conhecimento do InfoCap/Quiver e outras fontes autorizadas.

Coleção de runtime:

```text
company_<company_id>
```

### 4.3 Memória do Usuário

Memória pessoal dentro da corretora:

- cargo e responsabilidades;
- preferências;
- estilo de trabalho;
- objetivos;
- decisões;
- pendências;
- projetos;
- continuidade de conversas.

Escopo inviolável:

```text
company_id + user_id
```

### 4.4 Conhecimento de Agente

Conteúdo necessário a uma função específica:

- atendimento;
- cobrança;
- renovação;
- sinistro;
- comercial;
- relatórios;
- especialista de produto ou seguradora.

Não constitui cérebro separado. É um filtro especializado dentro da mesma arquitetura.

### 4.5 Procedimentos, Skills e Atlas

Procedimentos não são documentos comuns de RAG.

Devem existir como artefatos executáveis e versionados:

- Skills;
- playbooks;
- corredores;
- mapas de URA/WhatsApp;
- checklists;
- políticas de decisão;
- contratos de ferramenta.

O RAG pode explicar um procedimento. A execução deve usar o artefato procedural canônico.

### 4.6 Memória episódica

Conversas, atendimentos e casos são evidências históricas.

Elas podem alimentar:

- resumos;
- fatos;
- padrões;
- insights;
- candidatos a conhecimento;
- avaliação de resultados.

Não devem ser publicadas diretamente no global.

---

## 5. Autoridade de armazenamento

### 5.1 Supabase

Fonte de verdade para:

- catálogo de documentos;
- status de curadoria;
- versões;
- validade;
- escopo;
- permissões;
- memória estruturada;
- knowledge candidates;
- approvals;
- provenance;
- auditoria;
- capacidades e bindings.

### 5.2 MinIO

Fonte de verdade para:

- arquivo original;
- arquivo normalizado;
- artefatos de extração;
- anexos;
- versões preservadas.

### 5.3 Qdrant

Índice derivado e reconstruível.

Regras:

- não é fonte de verdade;
- não guarda segredo;
- não decide autoridade;
- recebe somente conteúdo autorizado;
- pode ser reindexado a partir de Supabase + MinIO.

### 5.4 Redis

Somente estado transitório:

- cache;
- fila;
- lock;
- debounce;
- idempotência;
- sessões temporárias.

### 5.5 Sistemas conectados

InfoCap, Quiver e similares são fontes vivas de dados operacionais. Não devem ser copiados indiscriminadamente para o RAG.

Dados vivos devem ser consultados no momento da pergunta ou ação.

---

## 6. Context Assembly canônico

### 6.1 Fluxo

```text
Pergunta ou tarefa
→ classificação de intenção e risco
→ plano de contexto
→ recuperação seletiva
→ construção do Evidence Pack
→ seleção de modelo e esforço
→ resposta ou plano de execução
→ guardrails/HITL
→ ação ou resposta
→ tracing e learning queue
```

### 6.2 Fontes disponíveis

O Context Planner pode selecionar:

- conversa atual;
- memória do usuário;
- memória da corretora;
- conhecimento global;
- conhecimento de agente;
- documentos;
- InfoCap/Quiver;
- Atlas/Skills/playbooks;
- ferramentas e conectores;
- internet;
- dados analíticos;
- histórico de casos.

### 6.3 Recuperação just in time

Não carregar todas as camadas por padrão.

O Context Planner deve buscar apenas o necessário para a tarefa atual.

### 6.4 Precedência para fatos de seguro

```text
1. Evidence Pack da apólice/caso específico
2. Documento oficial da apólice
3. Dados estruturados do sistema de gestão
4. Condições oficiais da versão correta do produto
5. Norma vigente
6. Conhecimento global curado
7. Conhecimento geral da LLM
```

O RAG global nunca confirma sozinho que uma apólice específica possui cobertura.

### 6.5 Precedência para estratégia

```text
1. Dados reais da corretora
2. Objetivo, restrições e contexto do usuário
3. Experimentos e resultados anteriores
4. Playbooks globais curados
5. Pesquisa de mercado atual
6. Raciocínio geral da LLM
```

### 6.6 Evidence Pack

Toda resposta relevante deve receber um pacote com:

- fonte;
- autoridade;
- escopo;
- namespace;
- versão;
- validade;
- data de coleta;
- emissor;
- seguradora/produto/ramo, quando aplicável;
- confiança;
- restrições;
- trecho mínimo necessário.

---

## 7. Política do conhecimento global

### 7.1 Uma única coleção

`autobrokers_global` é a única coleção global recuperável pelo runtime.

O caminho `company_<GLOBAL_KNOWLEDGE_COMPANY_ID>` deve ser inventariado, migrado e removido da recuperação global.

### 7.2 Uma única autoridade de publicação

Nenhum uploader, seed, Destilador ou agente pode publicar diretamente no índice final.

Todos usam o mesmo serviço:

```text
Global Knowledge Publisher
```

### 7.3 Ciclo de vida

```text
discovered
→ downloaded/uploaded
→ quarantined
→ extracted
→ sanitized
→ classified
→ curated
→ reviewed
→ approved
→ published
→ superseded/deprecated/revoked
```

Somente `published` pode entrar em `autobrokers_global`.

### 7.4 Metadados obrigatórios

- `source_url` ou `source_ref`;
- `source_domain`;
- `source_kind`;
- `title`;
- `issuer`;
- `carrier_slug`;
- `product_slug`;
- `insurance_line`;
- processo SUSEP, quando aplicável;
- `version`;
- `valid_from`;
- `valid_until`;
- `retrieved_at`;
- `source_hash`;
- `scope`;
- `namespace`;
- `knowledge_class`;
- `audience`;
- `visibility`;
- `sensitivity`;
- `curation_status`;
- `quality_score`;
- aprovador e data.

### 7.5 Conteúdo proprietário protegido

A corretora poderá usufruir do conhecimento global pelo AutoBrokers, mas não poderá:

- listar chunks globais;
- baixar o corpus;
- exportar documentos proprietários;
- reconstruir a biblioteca por consultas em massa;
- acessar caminhos internos do MinIO;
- enumerar todas as fontes privadas.

Fontes públicas podem ser citadas quando apropriado.

Dados e documentos próprios da corretora continuam exportáveis conforme direitos, contrato e legislação.

---

## 8. Capability Registry como autoridade

### 8.1 Regra

A capability determina se o agente pode usar uma camada ou ferramenta.

```text
capability permitida + scope válido + conexão disponível + policy aprovada
→ acesso
```

A variável de ambiente é apenas kill switch de emergência.

### 8.2 Scopes obrigatórios

Bindings não podem permanecer com `{}` em produção para capacidades sensíveis.

Devem declarar:

- namespaces;
- audiência;
- leitura/escrita;
- tenant/user;
- limite de volume;
- risco;
- necessidade de aprovação;
- tipos de dados permitidos;
- ferramentas autorizadas.

### 8.3 Política mínima por papel

**Core AutoBrokers:** global + tenant + user + dados vivos + web + ferramentas autorizadas.  
**Atendimento externo:** somente conhecimento público/seguro, tenant necessário, Evidence Pack e corredores.  
**Auxiliares:** somente domínios e ferramentas necessários à tarefa.  
**Subagentes:** princípio do menor privilégio.  
**Observador/Garimpo/Destilador:** leitura e geração de candidatos, sem publicação direta.

---

## 9. Memory Fabric

### 9.1 Tipos de memória

- memória de sessão;
- memória semântica do usuário;
- memória semântica da corretora;
- memória episódica;
- memória procedural;
- memória de preferência;
- memória de performance;
- memória de agente.

### 9.2 Escrita controlada

Não memorizar tudo.

Uma informação deve passar por:

```text
extração
→ classificação
→ deduplicação
→ checagem de contradição
→ relevância futura
→ escopo correto
→ retenção/validade
→ gravação
```

### 9.3 Memória pessoal

A memória pessoal deve ser pequena, útil e revisável.

Nunca deve conter segredo, senha ou credencial.

### 9.4 Memória da corretora

Pode armazenar:

- decisões estáveis;
- políticas internas;
- preferências organizacionais;
- contexto operacional;
- metas;
- estruturas da equipe;
- padrões confirmados.

### 9.5 Memória e RAG não são sinônimos

- RAG: recupera conhecimento documental.
- Memória: preserva continuidade e fatos aprendidos.
- Procedimento: define como agir.
- Ferramenta: consulta ou executa.

---

## 10. Learning Fabric e autoevolução

### 10.1 Princípio

Tudo pode gerar evidência. Nada vira verdade global automaticamente.

### 10.2 Agentes de aprendizagem

- **Garimpo:** dores, desejos, objeções, pedidos e oportunidades;
- **Destilador:** padrões, fatos e sínteses de conversas;
- **Tecelão:** rotas e mudanças operacionais de seguradoras;
- **Auditor:** qualidade, resultado e regressão;
- **Sentinela:** contradição, risco, obsolescência e drift;
- **Curador:** comparação com conhecimento existente;
- **Conselho:** avaliação de confiança, risco e impacto;
- **Publicador:** única autoridade de publicação.

### 10.3 Objeto comum

Toda fonte produz um:

```text
Knowledge Candidate
```

Campos mínimos:

- tipo;
- escopo proposto;
- domínio;
- resumo;
- evidências;
- número de tenants/fontes;
- PII removida;
- confiança;
- risco;
- validade;
- status;
- lineage.

### 10.4 Gates por risco

**Baixo risco:** automação possível após testes.  
**Médio risco:** revisão/approval.  
**Alto risco:** fonte oficial + humano responsável.

Alto risco inclui:

- jurídico;
- cobertura;
- exclusão;
- franquia;
- indenização;
- condição contratual;
- obrigação regulatória;
- decisão individual de cliente.

### 10.5 Anonimização

Conhecimento global derivado de corretoras deve ser:

- anonimizado;
- agregado;
- sem PII;
- sem segredo comercial identificável;
- sem reprodução de conversa integral;
- rastreável por lineage interno.

---

## 11. Ferramentas, conectores, APIs, MCPs e Skills

### 11.1 Conceitos

- **RAG:** conhecimento persistente.
- **Memória:** continuidade.
- **Skill:** procedimento reutilizável.
- **Tool/API:** consulta ou ação.
- **MCP:** protocolo para expor tools/resources/prompts.
- **Conector:** vínculo autenticado com um sistema.
- **Harness:** ambiente de decisão, ferramentas, contexto, guardrails e tracing.

### 11.2 Regra de integração

Ferramentas não entram no RAG como se fossem conhecimento.

O Smith decide quando consultar:

- InfoCap;
- Quiver;
- Drive;
- Notion;
- Slack;
- Calendar;
- Firecrawl/Tavily;
- portais;
- planilhas;
- sistemas financeiros;
- outros MCPs.

### 11.3 Segurança

- credenciais por tenant;
- Vault;
- OAuth quando possível;
- scopes mínimos;
- leitura e escrita separadas;
- approval para ações sensíveis;
- logs e tracing;
- rate limits;
- timeouts;
- idempotência;
- sem HTTP genérico irrestrito.

### 11.4 SPEC futura

A arquitetura avançada do harness do chat AutoBrokers, Skills, plugins, conectores, MCPs, model routing e experiência de trabalho será objeto de SPEC posterior.

Essa SPEC futura não poderá criar outro cérebro. Ela deverá consumir os contratos definidos aqui.

---

## 12. AutoBrokers Core

### 12.1 Papel

O AutoBrokers é o agente central interno da corretora.

Deve atuar como:

- analista;
- conselheiro;
- operador assistido;
- estrategista;
- pesquisador;
- criador de relatórios;
- coordenador de Auxiliares;
- explicador de seguros;
- detector de oportunidades;
- interface para dados e ferramentas.

### 12.2 Política de resposta

Para fatos oficiais, respeitar fonte e validade.

Para estratégia:

- usar o RAG como apoio;
- usar raciocínio geral;
- comparar alternativas;
- adaptar à realidade da corretora;
- não se limitar artificialmente a um documento.

### 12.3 Política de execução

O Core pode:

- explicar;
- pesquisar;
- analisar;
- preparar;
- recomendar;
- delegar;
- executar ações autorizadas com tool e policy.

Ações sensíveis exigem os gates definidos pela capability.

---

## 13. Página Memórias / Segundo Cérebro

### 13.1 Função

A página é uma projeção visual do cérebro e um elemento de produto.

Não é outro banco ou outro runtime.

### 13.2 Categorias visuais

- Conhecimento Global;
- Conhecimento da Corretora;
- Memória Pessoal;
- Experiências;
- Procedimentos;
- Conexões Vivas.

### 13.3 Conteúdo global

O usuário pode ver:

- quantidade;
- domínios;
- temas;
- ramos;
- seguradoras;
- atualização;
- cobertura do acervo.

Não pode abrir ou exportar o conteúdo proprietário global.

### 13.4 Métricas honestas

Não chamar toda conversa de “memória consolidada”.

Exibir separadamente:

- itens conectados;
- documentos;
- conversas;
- memórias consolidadas;
- rotas;
- conexões;
- knowledge cards;
- playbooks.

---

## 14. Model Router

A arquitetura não deve depender de uma única LLM.

O router deve considerar:

- complexidade;
- risco;
- necessidade de ferramentas;
- contexto;
- latência;
- custo;
- qualidade exigida;
- idioma;
- tamanho do documento;
- necessidade de visão.

Categorias:

- modelo econômico para classificação e extração;
- modelo forte para Core e curadoria;
- modelo máximo para casos complexos, arquitetura, jurídico ambíguo e revisão crítica;
- embeddings independentes da LLM de resposta;
- reranker independente.

A escolha de modelos será mantida em configuração governada e avaliada por benchmarks.

---

## 15. Observabilidade e evals

Cada resposta ou ação relevante deve registrar:

- intenção;
- plano de contexto;
- fontes consultadas;
- chunks usados;
- ferramentas chamadas;
- modelo;
- tokens e custo;
- latência;
- approvals;
- confiança;
- resultado;
- feedback;
- erros.

Evals obrigatórios:

- precisão factual;
- provenance;
- isolamento multi-tenant;
- validade;
- contradição;
- cobertura indevida;
- vazamento do global;
- regressão da inteligência geral;
- seleção de ferramenta;
- segurança de ação;
- custo e latência.

Comparar regularmente:

```text
sem RAG
versus
com RAG
```

O RAG só é aprovado quando melhora a resposta sem limitar a inteligência geral.

---

## 16. Plano de migração em lotes pequenos

### Lote 0 — Censo final read-only

- inventariar `autobrokers_global`;
- inventariar `company_<GK_ID>`;
- confirmar variáveis efetivas;
- identificar conteúdos e duplicidades;
- executar perguntas de recuperação;
- produzir baseline.

### Lote 1 — Unificação global

- manter `autobrokers_global` como único runtime global;
- remover o segundo caminho;
- alinhar `GLOBAL_KNOWLEDGE_COMPANY_ID`;
- capability governa acesso;
- environment vira kill switch;
- provenance completa;
- filtros de validade, namespace, audience e visibility;
- corrigir health/debug;
- testes de regressão.

### Lote 2 — Publisher único

- endpoint administrativo global;
- upload sem `agent_id` obrigatório;
- owner `platform`;
- quarentena;
- curadoria;
- approval;
- publicação;
- reindexação;
- revogação;
- seeds usando o mesmo publisher.

### Lote 3 — Context Assembly 2.0

- Intent Router;
- Context Planner;
- Evidence Builder;
- capability-aware retrieval;
- precedence;
- deduplicação;
- orçamento de contexto;
- model routing;
- tracing.

### Lote 4 — Memory & Learning Fabric

- ativar session summaries;
- ativar memória pessoal e da corretora;
- Knowledge Candidate;
- Garimpo;
- Destilador;
- Tecelão;
- Sentinela;
- Conselho;
- Publicador;
- deduplicação e contradição.

### Lote 5 — Primeiro corpus

- 50 a 100 documentos;
- fontes oficiais;
- Knowledge Cards;
- legislação;
- fundamentos;
- seguradoras prioritárias;
- vendas, gestão e marketing;
- goldens.

### Lote 6 — Harness e ferramentas avançadas

Executado por SPEC posterior, usando a arquitetura já unificada.

---

## 17. Critérios de aceite da arquitetura

A SPEC-052 estará implementada quando:

- existir uma única coleção global recuperável;
- existir um único publisher global;
- nenhum draft aparecer no runtime;
- a capability controlar o acesso;
- validade e audience forem aplicadas;
- provenance chegar ao modelo;
- global, tenant e user estiverem isolados;
- a página Memórias não expuser o corpus global;
- o Core combinar RAG, dados vivos e ferramentas;
- perguntas de cobertura usarem Evidence Pack;
- o aprendizado gerar candidates, não publicação direta;
- PII nunca entrar no global;
- health/debug refletirem o comportamento real;
- goldens e testes de vazamento estiverem verdes;
- rollback estiver documentado.

---

## 18. Invioláveis

1. Produto e agente central se chamam **AutoBrokers**.
2. Smith é runtime técnico, não marca visível.
3. Um único cérebro lógico.
4. Uma única coleção global de runtime.
5. Uma única autoridade de publicação.
6. Nenhum dado cruzado entre corretoras.
7. Nenhuma conversa bruta publicada globalmente.
8. Nenhuma confirmação de cobertura sem evidência específica.
9. Nenhum segredo no RAG ou memória.
10. Nenhuma ferramenta sensível sem capability e policy.
11. Nenhuma autoevolução sem lineage, gates e evals.
12. Nenhum refactor gigante quando um lote pequeno resolve.
13. Nenhuma SPEC futura pode contradizer esta sem aprovação do CEO/Founder.

---

## 19. Próximas SPECs subordinadas

Após a consolidação desta arquitetura, deverão ser planejadas separadamente:

1. **Harness avançado do AutoBrokers Core** — Skills, toolsets, plugins, conectores, MCPs, pesquisa, relatórios, execução e model router.
2. **Global Knowledge Publishing & Curation** — coleta, curadoria, corpus, goldens e atualização automática.
3. **Memory & Learning Fabric** — Garimpo, Destilador, candidates, consolidação e autoevolução governada.
4. **Connector & MCP Security Fabric** — OAuth, Vault, scopes, approvals e observabilidade.

Essas SPECs detalham a execução. A arquitetura soberana permanece a SPEC-052.

---

## 20. Decisão final

```text
O AutoBrokers não terá vários cérebros.
Terá um único sistema cognitivo governado,
com várias camadas, fontes e órgãos especializados.

O conhecimento global será proprietário, curado e compartilhado por uso.
O conhecimento da corretora permanecerá privado.
A memória do usuário permanecerá pessoal e tenant-scoped.
Dados vivos serão consultados nas fontes corretas.
Skills e ferramentas executarão tarefas sob capability.
Conversas gerarão evidência e candidatos, nunca verdade automática.
O Smith montará o contexto e coordenará toda a inteligência.
```

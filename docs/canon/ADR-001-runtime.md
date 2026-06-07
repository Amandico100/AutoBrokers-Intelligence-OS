---
# ADR-001 — Arquitetura de Runtime

Status: canonical  
Produto: AutoBrokers.ai  
Sistema: AutoBrokers Intelligence OS  
Documento: decisão arquitetural principal de runtime  
Última atualização: 2026-06-06  
Responsável estratégico: Architect / CEO AutoBrokers.ai  
Audiência: LLMs estratégicas, Claude Design, Claude Code, Codex, devs, arquitetura e time fundador

---

# 1. Objetivo deste ADR

Este ADR define a decisão canônica sobre qual é o runtime oficial do AutoBrokers.ai, como ele se relaciona com o Smith, com o ResultVision, com o Agent OS, com o AutoBrokers Intelligence OS V2 e com os futuros módulos de Atendimento, Auxiliares, Conhecimento, Conectores e Admin Global.

Este documento existe para impedir quatro erros graves:

1. transformar o AutoBrokers em apenas um “Smith renomeado”;
2. copiar o ResultVision bruto para dentro do novo runtime;
3. criar um segundo runtime agentic paralelo ao Smith;
4. deixar cada LLM/dev tomar decisões arquiteturais isoladas.

A decisão principal é:

```txt
O AutoBrokers.ai usará o Smith V6.2 como runtime técnico base, mas o produto final será uma nova camada de produto chamada AutoBrokers Intelligence OS.
````

Em outras palavras:

```txt
Smith = motor técnico invisível
AutoBrokers.ai = produto final
ResultVision / Agent OS = cérebro de domínio e referência de atendimento
```

---

# 2. Resumo da decisão

A arquitetura oficial do AutoBrokers.ai será composta por três camadas:

```txt
AutoBrokers.ai
├── Product Layer
├── Smith Runtime Engine
└── AutoBrokers Domain Brain
```

## 2.1 Product Layer

Camada visível para usuários, corretoras e equipe interna AutoBrokers.

Define:

* marca;
* UX;
* navegação;
* módulos;
* telas;
* linguagem;
* permissões;
* papéis;
* fluxo de uso;
* Admin Global;
* experiência da corretora;
* empacotamento de funcionalidades.

Esta camada é propriedade do AutoBrokers.ai.

Ela não deve parecer Smith.

---

## 2.2 Smith Runtime Engine

Camada técnica base.

Fornece:

* Next.js;
* FastAPI;
* LangGraph;
* chat streaming;
* agents;
* subagents;
* delegations;
* tools;
* MCP;
* RAG;
* Qdrant;
* MinIO;
* Redis;
* Supabase;
* multi-tenancy;
* billing;
* custos;
* logs;
* documentos;
* sanitização;
* admin;
* workers;
* Docling;
* infraestrutura de agentes.

Esta camada será preservada, adaptada e estendida.

Ela não deve ser exposta como marca final.

---

## 2.3 AutoBrokers Domain Brain

Camada de inteligência de seguros.

Será construída a partir de:

* ResultVision;
* Agent OS;
* AutoBrokers Intelligence OS V2;
* conversas reais;
* documentos reais;
* corredores;
* skills;
* guardrails;
* templates;
* contratos operacionais;
* fontes de atendimento;
* intake bruto curado.

Esta camada não será copiada bruta para o runtime.

Ela será transformada em pacotes curados, seguros, versionados e compatíveis com o runtime Smith.

---

# 3. Contexto histórico

O projeto AutoBrokers.ai passou por duas grandes fases.

## 3.1 Fase ResultVision / AutoBrokers antigo

O projeto anterior tinha foco principal em atendimento para corretoras de seguros.

Ele continha ideias, telas e estruturas importantes sobre:

* atendimento;
* filas;
* casos;
* conversas;
* ligações;
* segurados;
* seguradoras;
* canais;
* portais;
* corredores;
* subcorredores;
* WhatsApp;
* n8n;
* Action Safety;
* Reasoner JSON;
* Agent OS;
* guardrails;
* templates;
* inteligência operacional de seguros.

Esse material é extremamente valioso.

Mas ele também acumulou:

* duplicações;
* worktrees;
* documentos antigos;
* partes experimentais;
* arquitetura ainda não consolidada;
* código e docs misturados;
* decisões históricas superadas.

Por isso, o ResultVision não será runtime oficial do novo produto.

Ele será fonte de domínio, não base operacional final.

---

## 3.2 Fase Smith / AutoBrokers Intelligence OS

O projeto atual está sendo reconstruído sobre o Smith V6.2.

O Smith traz uma base técnica madura que seria muito cara e lenta para recriar do zero:

* SaaS multi-tenant;
* Admin;
* chat;
* agentes;
* subagentes;
* RAG;
* documentos;
* custos;
* billing;
* logs;
* MCP;
* tools;
* FastAPI;
* LangGraph;
* Supabase;
* Qdrant;
* MinIO;
* Redis;
* workers;
* Docling.

A decisão estratégica é aproveitar essa base, mas transformar a experiência, a marca, a navegação, os módulos e a inteligência de domínio em AutoBrokers.ai.

---

# 4. Problema arquitetural central

O maior risco do projeto é confundir “runtime técnico” com “produto final”.

O Smith já tem muita coisa pronta, mas não sabe nada sobre o negócio de seguros.

O ResultVision e o Agent OS sabem muito sobre seguros, mas não devem ser copiados diretamente para dentro do Smith.

O produto final precisa unir os dois mundos:

```txt
Smith entrega capacidade técnica.
AutoBrokers entrega produto, domínio e inteligência de seguros.
```

Portanto, a arquitetura deve responder a estas perguntas:

1. Onde roda o chat principal?
2. Onde moram os agentes?
3. Como os Auxiliares serão construídos?
4. Como o Atendimento de seguros será migrado?
5. Como o conhecimento será ingerido?
6. Como evitar duplicidade de runtime?
7. Como evitar que material bruto contamine o sistema?
8. Como preservar segurança, multi-tenancy e rastreabilidade?
9. Como permitir evolução sem retrabalho?

Este ADR responde essas perguntas no nível arquitetural.

---

# 5. Decisão canônica

## 5.1 Runtime oficial

O runtime oficial do AutoBrokers.ai será o repositório:

```txt
AutoBrokers-Intelligence-OS
```

Esse repo é a base operacional onde novas funcionalidades serão implementadas.

Ele contém o Smith adaptado e será transformado progressivamente em AutoBrokers Intelligence OS.

---

## 5.2 Smith como engine

O Smith será mantido como engine técnica.

Componentes do Smith que devem ser preservados:

```txt
Frontend Next.js
Backend FastAPI
LangGraph
Agents
Subagents
Delegations
HTTP tools
MCP tools
RAG
Qdrant
MinIO
Redis
Supabase
Billing
Costs
Logs
Documents
Sanitization
Admin
Workers
Docling
Chat streaming
```

O Smith não deve ser removido sem justificativa arquitetural forte.

O objetivo é adaptar e expandir, não desmontar.

---

## 5.3 AutoBrokers como Product Layer

O AutoBrokers.ai será a camada de produto sobre o runtime.

Essa camada define:

* `/dashboard` como chat-first;
* AutoBrokers como agente principal;
* Atendimento como módulo operacional;
* Auxiliares como automações/subagentes produtizados;
* Personalização como área de configuração;
* Admin Global como área interna;
* Conhecimento como camada de documentos e memória;
* Conectores/Vault como camada compartilhada;
* UX inspirada em ChatGPT, Claude e Claude Routines;
* mobile-first;
* progressive disclosure;
* segurança operacional.

---

## 5.4 ResultVision como fonte de domínio

O ResultVision será usado como referência de domínio.

Dele devem ser extraídos:

* conceitos de atendimento;
* estrutura de seguradoras;
* corredores;
* canais;
* exemplos de UX operacional;
* fluxos de atendimento;
* lógica de seguros;
* integrações planejadas;
* padrões de operação;
* ideias de fila/casos/conversas.

Não deve ser copiado bruto.

Não deve virar dependência runtime.

---

## 5.5 Agent OS / V2 como cérebro arquitetural

O Agent OS e o AutoBrokers Intelligence OS V2 devem ser tratados como fonte arquitetural e documental.

Eles devem orientar:

* governança;
* guardrails;
* skills;
* corredores;
* memória;
* RAG;
* contratos;
* evals;
* execução;
* canais;
* atendimento.

Mas não devem ser importados automaticamente para o runtime.

Cada parte deve ser curada, reduzida, versionada e transformada em pacote compatível.

---

# 6. Arquitetura alvo em alto nível

```txt
┌───────────────────────────────────────────────────────────────┐
│                       AutoBrokers.ai                          │
│                    Product / UX / Brand                       │
└───────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    Product Modules                            │
│                                                               │
│  AutoBrokers Chat     Atendimento     Auxiliares              │
│  Conhecimento         Conectores      Personalização          │
│  Admin Global         Custos/Logs      Governança             │
└───────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                    Smith Runtime Engine                       │
│                                                               │
│  Next.js  FastAPI  LangGraph  Agents  Subagents  Tools        │
│  MCP  RAG  Qdrant  MinIO  Redis  Supabase  Billing  Logs      │
└───────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                  AutoBrokers Domain Brain                     │
│                                                               │
│  ResultVision  Agent OS  V2  Corredores  Skills  Guardrails   │
│  Templates  Conversas curadas  Conhecimento de seguros        │
└───────────────────────────────────────────────────────────────┘
```

---

# 7. Superfícies principais do produto

## 7.1 Tenant Dashboard

Área usada por corretoras.

Deve conter:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

Outros módulos entram como subáreas:

* Conhecimento;
* Conectores;
* Canais;
* Equipe;
* Custos;
* Logs;
* Configurações;
* Seguradoras;
* Agentes de atendimento.

Regra:

```txt
O primeiro nível da navegação deve ser limpo. Complexidade entra dentro dos módulos.
```

---

## 7.2 Admin Global

Área usada pela equipe AutoBrokers.

Deve conter:

* corretoras;
* usuários;
* planos;
* créditos;
* custos;
* logs;
* billing;
* templates globais;
* Auxiliares globais;
* conectores globais;
* knowledge global;
* auditoria;
* suporte;
* governança.

Admin Global pode aproveitar muitas telas do Smith.

Mas deve ser rebrandado e organizado para o contexto AutoBrokers.

---

## 7.3 Runtime API

Camada backend.

Responsável por:

* chat;
* stream;
* agentes;
* documentos;
* RAG;
* tools;
* billing;
* logs;
* autenticação;
* integrações;
* execução de ações;
* workers;
* validações;
* políticas.

O backend deve permanecer coeso.

Não criar APIs paralelas desnecessárias.

---

# 8. Decisão sobre o chat principal

O chat principal da corretora é o AutoBrokers.

Ele deve viver em:

```txt
/dashboard
```

`/dashboard/chat` pode continuar existindo como rota técnica/compatibilidade, mas a entrada principal deve ser `/dashboard`.

Regras:

* Home = chat-first;
* sem dashboard de cards;
* sem “Home da corretora”;
* sem métricas inventadas;
* sem “Conversa ao vivo”;
* sem “Estudos”;
* sem seletor confuso de agentes para usuário comum;
* sem JARVYS.

O AutoBrokers deve ser a interface central da operação.

---

# 9. Decisão sobre agentes

O produto terá três categorias distintas de agentes.

## 9.1 AutoBrokers

Agente central.

Características:

* nome fixo;
* não personalizável;
* interno à corretora;
* conversa com usuários da corretora;
* pode consultar conhecimento;
* pode orientar;
* pode acionar módulos;
* futuramente pode delegar para Auxiliares;
* futuramente pode executar ações com permissão.

---

## 9.2 Agentes de atendimento

Agentes ligados ao módulo Atendimento.

Características:

* podem ser personalizados;
* podem ter nome, tom e identidade próprios;
* lidam com fluxos de atendimento;
* podem interagir com clientes/segurados em fases futuras;
* exigem mais guardrails;
* devem ser configuráveis por corretora;
* podem depender de corredores, canais e seguradoras.

---

## 9.3 Auxiliares

Subagentes/automações produtizadas.

Características:

* fazem tarefas específicas;
* podem ser globais ou por corretora;
* usam ferramentas/conectores;
* podem ter templates;
* podem ter execuções manuais;
* futuramente podem ter gatilhos e schedules;
* devem ter histórico;
* devem respeitar permissões.

---

# 10. Decisão sobre Auxiliares

Auxiliares serão construídos sobre o motor do Smith.

Usar como base:

* agents;
* subagents;
* delegations;
* tools;
* MCP;
* RAG;
* memory;
* logs;
* billing;
* workers quando necessário.

Não criar outro motor de Auxiliares do zero.

## 10.1 Camada técnica existente

O Smith já possui elementos que podem sustentar Auxiliares:

```txt
agents
agent_delegations
agent_http_tools
agent_mcp_connections
agent_mcp_tools
documents
memory_settings
user_memories
token_usage_logs
SubAgentTool
LangGraph
```

Esses elementos devem ser reaproveitados.

---

## 10.2 Camada de produto faltante

Ainda será necessário criar a camada AutoBrokers de produto:

* catálogo de Auxiliares;
* galeria;
* instalação por corretora;
* ativação/desativação;
* configuração;
* permissões;
* execução manual;
* histórico de execuções;
* status;
* approval/HITL;
* kill switch;
* auditoria;
* run logs;
* templates globais.

Essa camada será detalhada em:

```txt
docs/canon/UX-007-auxiliares.md
```

---

## 10.3 Escopo MVP de Auxiliares

O MVP recomendado de Auxiliares é:

```txt
Galeria -> Detalhe -> Ativar -> Configurar -> Executar manualmente -> Histórico básico
```

Não colocar no primeiro corte:

* scheduler avançado;
* criação conversacional completa;
* marketplace externo;
* ações reais sem approval;
* integração com todos os conectores;
* automações críticas sem logs.

---

# 11. Decisão sobre Atendimento

Atendimento é o módulo mais complexo.

Ele não deve ser improvisado.

Ele depende de:

* dados de segurado;
* apólice;
* cobertura;
* seguradora;
* canal;
* corredor;
* subcorredor;
* documentos;
* mídia;
* WhatsApp;
* portal;
* protocolos;
* Action Safety;
* handoff;
* acompanhamento;
* logs;
* templates;
* guardrails.

## 11.1 Fonte de conhecimento

Atendimento deve usar como fonte:

* ResultVision;
* Agent OS;
* corredores existentes;
* conversas com seguradoras;
* conversas com clientes;
* templates;
* guardrails;
* intake curado.

## 11.2 Decisão de runtime

Atendimento deverá ser reconstruído sobre o runtime Smith, mas por fases.

Não copiar o antigo reasoner bruto.

Não migrar todos os corredores agora.

Não iniciar pelo fluxo mais complexo antes de resolver Vault, UX e pacotes de conhecimento.

Essa decisão será detalhada em:

```txt
docs/canon/ADR-003-atendimento.md
```

---

# 12. Decisão sobre Conhecimento e RAG

O Smith já possui estrutura forte para RAG.

Usar:

* documentos;
* MinIO;
* Qdrant;
* embeddings;
* sanitização;
* RAG service;
* documentos por empresa/agente;
* Docling futuramente.

Mas o conhecimento de seguros precisa ser curado.

## 12.1 Tipos de conhecimento

O produto terá pelo menos quatro tipos:

```txt
Conhecimento global AutoBrokers
Conhecimento da corretora
Conhecimento de atendimento/corredores
Conhecimento bruto em curadoria
```

## 12.2 Regra de ingestão

Nada de material bruto direto no RAG.

Especialmente:

* WhatsApp exportado;
* prints;
* PDFs de apólices;
* imagens de documentos;
* conversas reais;
* planilhas;
* arquivos com credenciais;
* dados pessoais.

Antes precisa:

* classificação;
* redaction;
* separação de PII;
* aprovação;
* transformação em documento de conhecimento;
* definição de escopo;
* política de acesso.

---

# 13. Decisão sobre Vault e Conectores

O produto precisa de uma camada de conexões compartilhadas.

Essa camada será chamada conceitualmente de Vault / Connection Layer.

Ela deve guardar e governar:

* credenciais;
* tokens;
* integrações;
* permissões;
* escopo;
* status;
* último teste;
* módulos autorizados;
* logs de uso.

## 13.1 Regra fundamental

Uma conexão deve ser reutilizável por múltiplos módulos quando autorizado.

Exemplo:

```txt
Portal Bradesco conectado
├── Atendimento pode usar
├── Auxiliar de cobrança pode usar
└── AutoBrokers pode consultar status, se permitido
```

Não criar credenciais duplicadas para cada módulo.

## 13.2 O que entra no Vault

* seguradoras;
* portais;
* sistemas de gestão;
* Google;
* Slack;
* Notion;
* Calendar;
* Drive;
* WhatsApp;
* Evolution;
* Z-API se mantido;
* n8n se mantido;
* APIs externas;
* MCPs;
* webhooks.

A decisão detalhada será documentada em:

```txt
docs/canon/ADR-002-vault.md
```

---

# 14. Decisão sobre n8n

O n8n foi importante no ResultVision.

No novo runtime, ele não deve ser assumido como núcleo principal sem nova decisão.

Posição atual:

```txt
n8n pode continuar existindo como integration/execution adapter, mas não como orquestrador principal do produto.
```

O runtime principal será Smith/LangGraph/FastAPI.

O n8n pode ser usado para:

* integrações específicas;
* workflows externos;
* automações legadas;
* protótipos;
* conectores quando fizer sentido;
* ponte com ferramentas existentes.

Mas não deve ser a fonte principal de verdade da inteligência.

---

# 15. Decisão sobre WhatsApp

O Smith possui estrutura Z-API.

O AutoBrokers atual já utilizou/planejou Evolution API e n8n.

Decisão atual:

```txt
Não ativar WhatsApp real até Vault, permissões, logs e dry-run estarem definidos.
```

A arquitetura deve permitir providers.

Exemplo:

```txt
WhatsAppProvider
├── EvolutionProvider
├── ZApiProvider
└── FutureProvider
```

Evolution pode ser o provider inicial real se já estiver mais maduro no ecossistema AutoBrokers.

Z-API pode ser preservado como alternativa se o Smith já tiver estrutura útil.

Não tomar decisão final de provider dentro deste ADR.

---

# 16. Decisão sobre Docling

Docling é componente técnico para parsing de documentos.

Função:

* converter PDFs;
* extrair texto;
* apoiar OCR;
* estruturar documentos;
* preparar arquivos para RAG.

Docling é útil, mas não é P0 do produto.

Ordem correta:

```txt
1. Chat funcionando
2. Documentação canônica
3. UX/design
4. RAG simples com documento pequeno
5. Vault/política de dados
6. Docling para documentos complexos
```

Não usar Docling como desculpa para ingerir material bruto sensível cedo demais.

---

# 17. Multi-tenancy

O AutoBrokers.ai é multi-tenant.

Regras:

* cada corretora é um tenant;
* dados de uma corretora não podem vazar para outra;
* conhecimento global é separado de conhecimento tenant;
* logs devem preservar escopo;
* custos devem ser atribuíveis;
* agentes devem respeitar tenant;
* documentos devem respeitar tenant;
* conexões devem respeitar tenant;
* permissões devem respeitar usuário e papel.

O Smith já traz parte dessa base.

Toda expansão precisa respeitar esse modelo.

---

# 18. Dados e isolamento

## 18.1 Dados globais

Podem ser compartilhados entre corretoras:

* templates globais;
* Auxiliares globais;
* conhecimento genérico de seguros;
* conectores globais disponíveis;
* catálogos de seguradoras;
* estrutura de módulos;
* regras gerais.

## 18.2 Dados da corretora

Devem ser isolados:

* documentos da corretora;
* conversas;
* clientes;
* segurados;
* credenciais;
* conexões;
* configurações;
* agentes personalizados;
* execuções de Auxiliares;
* custos;
* logs;
* memórias.

## 18.3 Dados brutos

Devem ficar fora do runtime até curadoria:

* intake;
* conversas exportadas;
* PDFs reais;
* imagens;
* áudios;
* planilhas;
* arquivos com acesso;
* materiais de clientes.

---

# 19. Segurança operacional

Toda ação externa precisa seguir uma política de execução segura.

Categorias de ação:

## 19.1 Baixo risco

* consultar conhecimento;
* resumir documento;
* sugerir resposta;
* explicar processo;
* preparar rascunho;
* classificar mensagem.

Pode ser automático com logs.

## 19.2 Médio risco

* criar tarefa;
* sugerir envio;
* iniciar execução manual;
* consultar conector;
* buscar dados em sistema externo.

Pode exigir confirmação dependendo do contexto.

## 19.3 Alto risco

* enviar mensagem externa;
* acionar seguradora;
* alterar dado em sistema;
* usar credencial sensível;
* executar rotina recorrente;
* mexer em billing;
* enviar documento.

Exige:

* permissão explícita;
* rastreabilidade;
* aprovação humana ou política clara;
* logs;
* escopo tenant;
* possibilidade de auditoria.

---

# 20. Implicações para Claude Design

Claude Design deve trabalhar sobre a Product Layer.

Ele deve desenhar:

* experiência chat-first;
* navegação;
* sidebar;
* mobile-first;
* transições;
* páginas em camadas;
* galeria de Auxiliares;
* detalhes de Auxiliar;
* conectores;
* permissões;
* estados vazios;
* configuração;
* padrões visuais.

Claude Design não deve decidir runtime.

Não deve propor remover Smith.

Não deve desenhar um CRM tradicional.

Não deve trazer “Home de cards” de volta.

---

# 21. Implicações para Claude Code

Claude Code deve receber tarefas fechadas.

Exemplo de tarefa adequada:

```txt
Implementar empty state do /dashboard conforme UX-002, mantendo o chat stream existente.
Arquivos permitidos: app/dashboard/page.tsx, app/dashboard/chat/page.tsx, components/EmptyState.tsx.
Não alterar backend, Supabase, billing ou RAG.
Critério: npm run typecheck passa e chat continua respondendo.
```

Exemplo de tarefa inadequada:

```txt
Melhore o dashboard e decida a arquitetura.
```

Claude Code não deve decidir estratégia aberta.

---

# 22. Implicações para Codex

Codex deve ser usado preferencialmente para:

* auditorias;
* inventários;
* patches mecânicos;
* substituição de documentos;
* scans;
* typecheck;
* build;
* relatórios;
* ajustes pequenos;
* tarefas bem delimitadas.

Codex não deve criar documentação estratégica principal sozinho.

Ele tende a simplificar demais e reduzir profundidade.

Documentação canônica deve ser escrita pelo Architect/CEO com apoio estratégico.

---

# 23. Implicações para documentação

A pasta canônica é:

```txt
docs/canon/
```

Essa pasta é fonte ativa.

A pasta histórica é:

```txt
docs/_archive/
```

Documentos em archive não orientam decisão atual.

Ordem de autoridade:

```txt
1. Decisões diretas do CEO/Architect na conversa atual
2. docs/canon/
3. ADRs canônicos
4. planos aprovados
5. docs/_archive/
6. ResultVision / Agent OS / Intake como referência, não decisão
```

---

# 24. O que não fazer

Não fazer:

* copiar ResultVision bruto;
* copiar Agent OS bruto;
* ingerir intake bruto;
* criar outro runtime;
* criar outro backend de agentes;
* fazer Auxiliares fora do Smith sem ADR;
* recriar RAG do zero;
* deixar Smith/JARVYS visível;
* reviver Estudos;
* reviver Conversa ao vivo;
* criar Home de cards;
* implementar UI grande antes de Claude Design;
* ativar WhatsApp real sem Vault e approval;
* ativar InfoCap real sem segurança;
* acionar n8n real sem decisão;
* misturar dados de corretoras;
* expor service role;
* permitir ações externas sem logs.

---

# 25. Alternativas consideradas

## 25.1 Recriar tudo do zero

Rejeitada.

Motivos:

* lenta demais;
* cara demais;
* alto risco;
* perderia o que Smith já tem pronto;
* atrasaria produto.

---

## 25.2 Continuar no ResultVision

Rejeitada como runtime principal.

Motivos:

* histórico confuso;
* duplicações;
* worktrees;
* arquitetura ainda muito misturada;
* menos maduro como SaaS agentic completo;
* maior risco de legado.

Mas ResultVision permanece fonte de domínio.

---

## 25.3 Usar Smith puro

Rejeitada como produto final.

Motivos:

* não conhece seguros;
* identidade errada;
* UX não é a desejada;
* módulos não estão adaptados;
* atendimento de corretora não existe;
* Auxiliares precisam camada de produto.

Mas Smith permanece motor técnico.

---

## 25.4 Usar LionClaw/OpenClaw como runtime

Rejeitada no momento.

Motivos:

* aumentaria complexidade;
* criaria segundo runtime;
* atrasaria execução;
* Smith já tem motor operacional suficiente;
* risco de confusão arquitetural.

LionClaw/OpenClaw permanecem inspiração.

---

# 26. Decisão final

A decisão arquitetural oficial é:

```txt
AutoBrokers.ai será construído sobre o Smith Runtime Engine, com uma Product Layer própria e um Domain Brain de seguros curado a partir de ResultVision, Agent OS, V2 e intake tratado.
```

Isso significa:

* Smith fica como base técnica;
* AutoBrokers vira experiência e produto;
* ResultVision vira fonte de domínio;
* Agent OS vira fonte arquitetural;
* intake bruto vira fonte futura curada;
* Auxiliares usam motor Smith;
* Atendimento será reconstruído por fases;
* Vault será camada crítica antes de ações externas;
* Claude Design define UX visual;
* Claude Code implementa tarefas fechadas;
* Codex faz auditoria e patches mecânicos.

---

# 27. Critérios de sucesso deste ADR

Este ADR estará sendo seguido corretamente se:

* novas features forem implementadas no repo `AutoBrokers-Intelligence-OS`;
* Smith não aparecer como marca visível;
* runtime Smith continuar preservado;
* ResultVision não for copiado bruto;
* Agent OS não for importado bruto;
* Auxiliares usarem agents/subagents/delegations/tools;
* Atendimento for planejado por ADR próprio;
* Vault for definido antes de integrações reais;
* intake bruto não entrar em RAG;
* Claude Code não receber decisões abertas;
* UX seguir chat-first, mobile-first e progressive disclosure.

---

# 28. Próximos documentos relacionados

Este ADR deve ser lido junto com:

```txt
docs/canon/PRD-001-visao-produto.md
docs/canon/UX-001-navegacao.md
docs/canon/DS-001-design-brief.md
docs/canon/UX-007-auxiliares.md
docs/canon/ADR-002-vault.md
docs/canon/ADR-003-atendimento.md
docs/canon/ROADMAP-001-execucao.md
```

---

# 29. Próxima decisão arquitetural crítica

A próxima decisão crítica é:

```txt
ADR-002 — Vault e Conectores
```

Motivo:

Atendimento, Auxiliares, AutoBrokers e Conhecimento dependem de conexões, credenciais, permissões e escopos seguros.

Sem Vault, qualquer integração real vira risco.

Em paralelo, também será necessário:

```txt
ADR-003 — Atendimento Runtime
```

para decidir como o cérebro de atendimento do ResultVision/Agent OS será reconstruído sobre Smith.

---

# 30. Encerramento

Este ADR fixa a base do projeto.

O AutoBrokers.ai não deve mais oscilar entre várias arquiteturas.

A partir deste documento, todo trabalho deve respeitar a separação:

```txt
Produto: AutoBrokers.ai
Runtime: Smith
Domínio: AutoBrokers Domain Brain
Referência histórica: ResultVision
Cérebro arquitetural: Agent OS / V2
Material bruto: Intake em curadoria
```

A missão agora é transformar uma base técnica poderosa em um produto limpo, seguro, específico para seguros e fácil de usar por corretoras.


---
# ADR-001 — Product & Runtime Architecture do AutoBrokers Intelligence OS

Status: Proposed for Founder Approval  
Owner: AutoBrokers.ai Architect  
Product: AutoBrokers.ai / AutoBrokers Intelligence OS  
Runtime Base: Smith V6.2 Sandbox  
Last Updated: 2026-06-05

---

## 1. Decisão principal

O AutoBrokers Intelligence OS será construído com a seguinte arquitetura:

```txt
AutoBrokers.ai = AutoBrokers Product Layer + Smith Runtime Engine + AutoBrokers Domain Brain
````

A base técnica executável será o Smith, já instalado e validado em sandbox no EasyPanel.

O AutoBrokers antigo será usado como referência de produto, UX operacional e domínio de seguros.

O Agent OS V2 será usado como cérebro canônico curado, não como pasta bruta copiada para o runtime.

O LionClaw será usado apenas como referência de inteligência, UX e padrões avançados, especialmente para Auxiliares, orquestração e experiência de execução. Ele não será usado como motor runtime principal neste momento.

---

## 2. Decisão nominal

O agente central de cada corretora se chama:

```txt
AutoBroker
```

Regras:

* Toda corretora terá seu AutoBroker.
* O nome AutoBroker é fixo.
* O nome não pode ser personalizado para João, Maria, Jarvys ou outro nome.
* AutoBroker é o agente central interno da corretora.
* AutoBroker não é o agente de atendimento externo ao segurado.
* AutoBroker é o copiloto operacional, analítico e estratégico da corretora.

Termos proibidos no produto final:

* JARVYS como nome do agente da corretora.
* Smith como nome visível ao cliente.
* LionClaw como nome visível ao cliente.
* Página “Estudos”.

---

## 3. Tese de produto

O AutoBrokers não deve parecer apenas um sistema de atendimento.

Ele deve parecer um sistema operacional inteligente para corretoras de seguros.

Portanto, a experiência principal da corretora deve ser:

```txt
Chat-first com AutoBroker + atalhos operacionais + cards vivos da operação
```

A página inicial da corretora deve ser o AutoBroker, não um dashboard tradicional puro.

---

## 4. Opções avaliadas

### Opção A — Atendimento como página principal

Nota: 78/100

Vantagens:

* Mais próximo do dashboard antigo.
* Bom para operação diária de SAC, assistência, sinistro e renovação.
* Fácil de entender para corretoras que querem “fila de atendimento”.

Desvantagens:

* Reduz a percepção de IA.
* Faz o produto parecer um CRM ou central de atendimento comum.
* Esconde o AutoBroker em uma aba secundária.
* Não acomoda bem Auxiliares, automações e inteligência transversal.

Decisão: rejeitada como homepage principal.

---

### Opção B — Chat puro estilo Smith/Claude como página principal

Nota: 87/100

Vantagens:

* Moderno.
* Simples.
* Alto efeito IA.
* Mais próximo de Claude/ChatGPT.

Desvantagens:

* Pode parecer vazio.
* Não mostra operação viva.
* Corretor pode não saber o que pedir.
* Não evidencia valor imediato de atendimento, pendências, filas e rotinas.

Decisão: boa base, mas insuficiente sozinha.

---

### Opção C — AutoBroker chat-first + atalhos + cards operacionais

Nota: 96/100

Vantagens:

* Coloca AutoBroker como centro do sistema.
* Mantém visibilidade da operação.
* Permite atalhos rápidos para atendimento, Auxiliares, seguradoras e relatórios.
* Combina experiência moderna com utilidade operacional.
* Diferencia o AutoBrokers de sistemas tradicionais.

Desvantagens:

* Exige bom design da homepage.
* Exige integração gradual entre chat, dados e ações.

Decisão: escolhida.

---

### Opção D — Dashboard antigo quase igual com AutoBroker em uma aba

Nota: 70/100

Vantagens:

* Mais fácil de migrar visualmente.
* Menor ruptura inicial.

Desvantagens:

* Perde a nova tese do produto.
* AutoBroker vira “mais uma página”.
* Mantém o sistema com cara de SaaS tradicional.

Decisão: rejeitada.

---

## 5. Arquitetura final de produto

O produto terá quatro grandes camadas funcionais:

```txt
1. AutoBroker
2. Atendimento
3. Auxiliares
4. Conhecimento, Canais e Gestão
```

---

## 6. AutoBroker

### 6.1 Definição

AutoBroker é o agente central interno da corretora.

Ele conversa com o corretor, gestor ou operador e pode:

* consultar dados da corretora;
* explicar o sistema;
* analisar operação;
* sugerir ações;
* acionar Auxiliares;
* resumir atendimentos;
* consultar base de conhecimento;
* orientar a equipe;
* preparar mensagens;
* gerar análises;
* criar tarefas assistidas;
* consultar seguradoras, canais e integrações quando permitido.

### 6.2 O que AutoBroker não é

AutoBroker não é:

* o atendente externo do segurado;
* um nome personalizável;
* uma página antiga de “Conversa ao vivo”;
* um chatbot solto sem contexto;
* um substituto direto dos agentes de atendimento.

### 6.3 Página inicial

A home da corretora será:

```txt
AutoBroker Home
```

Componentes:

* chat central;
* saudação inteligente;
* atalhos rápidos;
* cards operacionais;
* alertas;
* últimas execuções de Auxiliares;
* atendimentos críticos;
* pendências da corretora;
* status das integrações principais.

Exemplo de abertura:

```txt
AutoBroker
Como posso ajudar sua corretora hoje?
```

Atalhos iniciais:

* Ver atendimentos críticos.
* Criar Auxiliar.
* Consultar seguradora.
* Analisar fila.
* Buscar cliente/apólice.
* Preparar mensagem para cliente.
* Ver pendências do dia.
* Resumir operação.

---

## 7. Atendimento

### 7.1 Definição

Atendimento é a área de conversas externas com clientes, segurados, leads e canais.

Essa área herda o melhor do dashboard antigo do AutoBrokers.

Módulos:

* Fila de atendimentos.
* Casos.
* Conversas.
* Ligações.
* Segurados.
* Handoff humano.
* Histórico.
* Monitoramento de status.

### 7.2 Agentes de atendimento

Agentes de atendimento são diferentes do AutoBroker.

Eles podem ser personalizados por corretora.

Exemplos:

* agente de assistência;
* agente de sinistro;
* agente de renovação;
* agente de cotação;
* agente de reputação;
* agente de cobrança.

Esses agentes podem ter:

* nome personalizado;
* avatar;
* voz;
* sexo/persona;
* tom de comunicação;
* especialidade;
* regras de atendimento;
* canais permitidos;
* playbooks;
* limites de autonomia.

---

## 8. Auxiliares

### 8.1 Decisão de nome

O nome de produto será:

```txt
Auxiliares
```

Não usaremos “Rotinas” como nome principal.

Motivo:

* “Auxiliares” é mais proprietário do AutoBrokers.
* É mais acessível para corretores.
* Evita parecer cópia direta de Claude Routines.
* Permite incluir tanto automações recorrentes quanto subagentes especialistas.

Termos relacionados:

```txt
Auxiliar = unidade de automação/inteligência
Execução = uma rodada/rodagem do Auxiliar
Template de Auxiliar = modelo global criado pelo Admin AutoBrokers
Auxiliar instalado = instância configurada por corretora
```

---

### 8.2 Decisão técnica dos Auxiliares

Os Auxiliares serão construídos em cima do motor do Smith.

Nota: 96/100

Motivos:

* Smith já possui tabela `agents` com suporte a `is_subagent` e `allow_direct_chat`.
* Smith já possui tabela `agent_delegations`.
* Smith já possui SubAgentTool.
* Smith já possui HTTP tools.
* Smith já possui MCP tools.
* Smith já possui RAG, Qdrant, MinIO e documentos.
* Smith já possui logs, custos e usage.
* Smith já possui chat e LangGraph.
* Já está instalado e funcionando no sandbox.

A implementação atual de SubAgent no Smith roda especialistas como tools LangChain, com RAG, MCP e HTTP tools usando os mesmos serviços do agente principal, além de logging/custos por agente. 

A estrutura de delegação existente já modela a relação entre orquestrador e subagente com descrição de tarefa, limite de contexto, timeout e iterações. 

O Smith também já expõe APIs para criar HTTP tools e invalidar cache de grafo após alteração de tools, o que é importante para transformar Auxiliares em componentes operacionais conectados a ferramentas reais. 

---

### 8.3 Papel do LionClaw nos Auxiliares

LionClaw não será motor runtime principal.

LionClaw será usado como referência para:

* UX de execução;
* biblioteca de templates;
* padrões de orquestração;
* painel de runs;
* aprovação humana;
* composição de tarefas;
* inspiração de comandos;
* boas práticas de multiagentes;
* experiência de “agente operacional”.

Nota da decisão:

```txt
Smith Engine + AutoBrokers Product Layer + LionClaw Pattern Inspiration = 95/100
```

Não usar LionClaw como motor agora:

```txt
Smith Engine + LionClaw Engine juntos = 58/100
```

Motivo da rejeição:

* aumenta complexidade;
* cria duplicidade de runtime;
* dificulta debug;
* atrasa MVP;
* aumenta risco de bugs;
* mistura paradigmas;
* complica onboarding de novos devs/chats.

---

### 8.4 Inspiração Claude Routines

Claude Routines é uma boa referência conceitual, mas não será copiada como nome.

A Anthropic descreve rotinas como automações configuradas uma vez com prompt, repositório e conectores, podendo rodar por agenda, API ou evento/webhook. ([Claude][1])

A referência útil para AutoBrokers é:

```txt
Auxiliar = prompt + conectores + ferramentas + gatilho + permissões + execução na nuvem
```

No Claude, rotinas podem ser agendadas, chamadas por API ou acionadas por eventos/webhooks. ([Claude][1])

Tradução para AutoBrokers:

```txt
Auxiliar agendado
Auxiliar manual
Auxiliar acionado por evento
Auxiliar acionado por API
Auxiliar acionado pelo AutoBroker
```

---

### 8.5 Tipos de Auxiliares

Categorias iniciais:

* Atendimento.
* Cobrança.
* Renovação.
* Documentos.
* Vendas.
* Sinistro.
* Assistência.
* Gestão.
* Marketing.
* Relatórios.
* Portais.
* Compliance.
* Seguradoras.
* Financeiro.

Exemplos:

```txt
Auxiliar de cobrança de documentos pendentes
Auxiliar de resumo diário da operação
Auxiliar de consulta de apólices
Auxiliar de renovação semanal
Auxiliar de monitoramento de portais
Auxiliar de vídeos quentes no YouTube
Auxiliar de faturamento diário por WhatsApp
Auxiliar de retorno de seguradora
Auxiliar de pendências de sinistro
Auxiliar de NPS/reputação
```

---

### 8.6 Estrutura de um Auxiliar

Todo Auxiliar deve ter:

```txt
id
nome
descrição
categoria
template_global_id
company_id
status
objetivo
prompt_base
prompt_personalizado
gatilho
agenda
evento
ferramentas
conexões necessárias
permissões
risco
aprovação humana
entrada esperada
saída esperada
modelo LLM
base de conhecimento
logs
histórico de execuções
custo
versão
criado_por
atualizado_em
```

---

### 8.7 Galeria de Auxiliares

A primeira versão será baseada em galeria.

Nota: 94/100

Fluxo:

```txt
Admin Global cria template de Auxiliar
↓
Corretora vê a Galeria de Auxiliares
↓
Corretora clica em Ativar
↓
Sistema pede personalizações simples
↓
Sistema valida conexões necessárias
↓
Sistema cria instância do Auxiliar
↓
Auxiliar fica disponível para execução manual ou agendada
```

Isso é mais seguro do que permitir criação livre por conversa no MVP.

---

### 8.8 Criação conversacional de Auxiliares

A criação de Auxiliares por conversa com o AutoBroker será fase 2.

Nota atual: 82/100 para MVP
Nota futura: 97/100

Fluxo futuro:

```txt
Usuário: AutoBroker, crie um Auxiliar para me enviar o faturamento todo dia às 17h.
AutoBroker: confirma dados necessários.
Sistema: abre tela/formulário de revisão.
Usuário: aprova.
Auxiliar: criado e ativado.
```

No MVP, o AutoBroker pode ajudar a preencher o formulário, mas não deve criar automações livres sem revisão humana.

---

## 9. Canais, conexões e vault

### 9.1 Decisão

Credenciais e conexões devem ser criadas uma vez por corretora e reutilizadas por AutoBroker, agentes de atendimento, Auxiliares e corredores.

Exemplo:

```txt
Portal Bradesco conectado uma vez
```

Pode ser usado por:

* atendimento;
* sinistro;
* renovação;
* cobrança;
* consulta de apólice;
* AutoBroker;
* Auxiliar;
* corredor especializado.

### 9.2 Camadas

```txt
Connection Vault
→ Credential Reference
→ Tool Registry
→ Permission Guard
→ Execution Policy
→ Audit Log
```

### 9.3 Permissões por conexão

Cada conexão deve declarar:

* pode consultar?
* pode baixar documento?
* pode preencher formulário?
* pode enviar mensagem?
* pode abrir protocolo?
* pode alterar dados?
* exige aprovação humana?
* pode rodar agendado?
* pode ser usado por Auxiliares?
* pode ser usado pelo AutoBroker?
* pode ser usado por agentes externos?

---

## 10. Conhecimento

### 10.1 Bases

O sistema terá bases separadas:

```txt
Base Global AutoBrokers
Base da Corretora
Base do AutoBroker
Base dos Agentes
Base dos Auxiliares
Base dos Corredores
Base de Casos/Conversas
```

### 10.2 Base Global

Disponível para todas as corretoras.

Inclui:

* regras gerais de seguros;
* playbooks globais;
* templates globais;
* documentos de seguradoras;
* procedimentos padrão;
* boas práticas;
* guardrails;
* conhecimento canônico do Agent OS V2.

### 10.3 Base da Corretora

Específica por tenant.

Inclui:

* políticas internas;
* tom de voz;
* regras comerciais;
* documentos próprios;
* histórico;
* preferências;
* procedimentos;
* equipe;
* clientes e contexto permitido.

---

## 11. Admin Global

O Admin Global é exclusivo da equipe AutoBrokers.

Ele é a fábrica e governança do sistema.

Funções:

* criar templates globais de agentes;
* criar templates globais de Auxiliares;
* criar catálogo de seguradoras;
* criar catálogo de corredores;
* configurar conectores oficiais;
* gerenciar planos;
* gerenciar custos;
* gerenciar modelos LLM;
* revisar logs globais;
* publicar conhecimento global;
* versionar prompts;
* aprovar features;
* auditar uso.

A corretora não acessa o Admin Global.

---

## 12. Dashboard da Corretora

A corretora acessa o Tenant Dashboard.

### 12.1 Sidebar proposta

```txt
INÍCIO
- AutoBroker

OPERAÇÃO
- Painel
- Fila de atendimentos
- Casos
- Conversas
- Ligações
- Segurados

AUTOMAÇÃO
- Auxiliares
- Galeria de Auxiliares
- Execuções

AGENTES
- Agentes de atendimento
- Personalização
- Playbooks

CONHECIMENTO
- Base de conhecimento
- Documentos
- Memórias da corretora

CANAIS
- Seguradoras
- Catálogo global
- Integrações
- WhatsApp / Telefonia

GESTÃO
- Relatórios
- Custos IA
- Logs
- Equipe

SETUP
- Corretora
- Onboarding
- Configurações
```

### 12.2 Remoções

Remover:

```txt
Estudos
Conversa ao vivo antiga
JARVYS como nome
Smith como nome visível
```

### 12.3 Substituições

```txt
Conversa ao vivo antiga → AutoBroker
Rotinas → Auxiliares
Agentes genéricos → Agentes de atendimento / Auxiliares / AutoBroker
```

---

## 13. Uso do Smith

Smith será preservado como motor técnico.

Usar:

* chat streaming;
* agentes;
* subagentes;
* delegações;
* RAG;
* documentos;
* Qdrant;
* MinIO;
* Supabase;
* FastAPI;
* Next.js;
* logs;
* custos;
* billing interno;
* tools HTTP;
* MCP tools;
* memória;
* handoff;
* widget quando útil.

Não usar como produto final sem adaptação.

Smith não deve aparecer na UI final.

---

## 14. Uso do AutoBrokers antigo

AutoBrokers antigo será referência de produto e domínio.

Usar como referência:

* Fila de atendimentos;
* Casos;
* Conversas;
* Ligações;
* Segurados;
* Seguradoras;
* Catálogo global;
* Integrações;
* Corredores;
* Configurações da corretora;
* Equipe;
* Agentes de atendimento;
* Visão operacional de seguros.

Não copiar código bruto sem auditoria.

Não copiar pastas legadas para o repo limpo.

---

## 15. Uso do Agent OS V2

Agent OS V2 será fonte canônica de cérebro.

Usar como fonte para:

* governança;
* políticas;
* runtime;
* memória;
* skills;
* guardrails;
* evals;
* corredores;
* atendimento;
* conhecimento de seguros.

Não copiar bruto para dentro do Smith.

O conteúdo será transformado em:

```txt
knowledge packages
prompt packages
tool policies
agent configs
auxiliary templates
corridor packages
eval suites
```

---

## 16. Uso do LionClaw

LionClaw será referência externa de padrão.

Usar para aprender:

* UX de agente operacional;
* organização de rotinas;
* execução com histórico;
* aprovação humana;
* painéis de tarefas;
* composição de ações;
* catálogo de automações;
* orquestração conceitual.

Não usar como runtime principal agora.

Não usar como marca.

Não copiar bruto para o repo limpo sem ADR específico.

---

## 17. Roadmap recomendado

### Fase 1 — Arquitetura e inventário

Objetivo: parar confusão e decidir o produto.

Entregas:

* ADR-001 aprovado.
* Inventário do Smith atual.
* Inventário do AutoBrokers antigo.
* Mapa de equivalência Smith → AutoBrokers.
* Mapa de páginas final.

### Fase 2 — AutoBroker Home

Objetivo: transformar o chat atual em página principal do tenant.

Entregas:

* remover naming Smith;
* renomear JARVYS Sandbox para AutoBroker Sandbox;
* criar home AutoBroker;
* incluir atalhos rápidos;
* incluir cards operacionais compactos;
* manter menu lateral.

### Fase 3 — Admin Global

Objetivo: definir fábrica global.

Entregas:

* templates globais;
* agentes globais;
* Auxiliares globais;
* catálogo de seguradoras;
* modelos LLM;
* custos;
* logs.

### Fase 4 — Auxiliares MVP

Objetivo: criar primeira versão da Galeria de Auxiliares.

Entregas:

* modelo de template global;
* instância por corretora;
* ativação/desativação;
* execução manual;
* execução agendada simples;
* logs de execução;
* permissões básicas.

### Fase 5 — RAG e Conhecimento

Objetivo: fazer documentos alimentarem AutoBroker e Auxiliares.

Entregas:

* base global;
* base da corretora;
* upload;
* Qdrant;
* MinIO;
* pacote de conhecimento;
* teste de pergunta com fonte.

### Fase 6 — Atendimento

Objetivo: reconstruir o módulo operacional do AutoBrokers antigo em cima do runtime novo.

Entregas:

* fila;
* casos;
* conversas;
* agentes de atendimento;
* handoff;
* WhatsApp;
* logs.

### Fase 7 — Seguradoras e Corredores

Objetivo: migrar corredores com base na nova arquitetura.

Entregas:

* catálogo;
* canais;
* portais;
* WhatsApp seguradora;
* corredores;
* subcorredores;
* permissões;
* evals.

---

## 18. Decisões finais deste ADR

1. O nome do agente central é AutoBroker.
2. AutoBroker é a página inicial da corretora.
3. Página Estudos será removida.
4. Conversa ao vivo antiga será substituída.
5. Smith será motor runtime.
6. AutoBrokers antigo será referência de produto.
7. Agent OS V2 será cérebro canônico curado.
8. LionClaw será referência de padrões, não motor.
9. Rotinas serão chamadas de Auxiliares.
10. Auxiliares usarão o motor de agentes/subagentes/tools do Smith.
11. Galeria de Auxiliares vem antes da criação conversacional livre.
12. Conexões serão compartilhadas por vault.
13. Atendimento externo é separado do AutoBroker.
14. Admin Global governa templates.
15. Corretora ativa e personaliza instâncias.

---

## 19. Próximo batch recomendado

```txt
BATCH_35A_SMITH_PRODUCT_SURFACE_INVENTORY
```

Objetivo:

Mapear exatamente o que o Smith já tem para suportar:

* AutoBroker;
* agentes;
* subagentes;
* tools;
* documentos;
* RAG;
* integrações;
* custos;
* logs;
* páginas admin;
* páginas tenant.

Não implementar ainda.

---

## 20. Critério de sucesso

Esta arquitetura estará correta se permitir:

```txt
1. corretora entrar e falar com o AutoBroker;
2. AutoBroker entender dados da corretora;
3. corretora ativar Auxiliares prontos;
4. Auxiliares usarem conexões já cadastradas;
5. atendimento externo continuar separado;
6. Admin Global criar templates para todas as corretoras;
7. conhecimento global e individual coexistirem;
8. o sistema escalar sem duplicar motores.
```


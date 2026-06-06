# PRD-001 — Visão de Produto do AutoBrokers.ai

Status: canônico ativo  
Owner: AutoBrokers.ai Architect  
Última atualização: 2026-06-06

---

## 1. Resumo executivo

O **AutoBrokers.ai** é um SaaS multi-tenant para corretoras de seguros operarem atendimento, automações, conhecimento e integrações através de um copiloto operacional chamado **AutoBrokers**.

O produto não deve ser entendido como um CRM tradicional com IA adicionada por cima. A visão correta é:

```txt
AutoBrokers.ai = sistema operacional de IA para corretoras de seguros
```

A primeira experiência do usuário deve ser parecida com ChatGPT/Claude: abrir o sistema e falar com o AutoBrokers. A partir dele, o corretor acessa Atendimento, Auxiliares, Conhecimento, Conectores e Configurações.

---

## 2. Contexto do projeto

O projeto nasceu de uma primeira versão focada principalmente em atendimento de corretoras, chamada internamente de ResultVision/AutoBrokers antigo. Essa versão tinha domínio forte de seguros: seguradoras, corredores, canais, portais, fila de atendimento, casos, conversas, ligações, segurados e configurações operacionais.

Depois foi decidido reconstruir a base técnica usando o **Smith V6.2** como runtime, porque ele já possui estrutura madura de SaaS/admin, chat, agentes, subagentes, RAG, documentos, custos, logs, billing, MCP, ferramentas HTTP, MinIO, Qdrant, Redis e FastAPI.

A decisão atual é unir:

```txt
Smith = motor técnico
ResultVision = domínio/UX operacional de seguros
Agent OS V2 = cérebro canônico de políticas, atendimento, skills e corredores
AutoBrokers.ai = produto final
```

Nada deve ser copiado de forma bruta entre pastas ou repositórios. Tudo deve ser portado por módulos curados, com documentação, validação e batches pequenos.

---

## 3. Usuários principais

### 3.1 Dono/gestor da corretora

Pessoa que quer saber se a operação está sob controle, reduzir trabalho manual, melhorar atendimento, acompanhar pendências, ativar automações e ganhar produtividade.

### 3.2 Operador/atendente da corretora

Pessoa que acompanha fila, conversas, casos, segurados, documentos, retornos e tarefas operacionais.

### 3.3 Admin interno AutoBrokers.ai

Equipe interna do AutoBrokers.ai. Acessa o Admin Global para criar corretoras, planos, créditos, agentes, templates globais, Auxiliares globais, conectores, catálogos, custos, logs e governança.

---

## 4. Momento mágico do produto

O momento mágico inicial é:

```txt
O corretor abre o sistema, fala com o AutoBrokers e percebe que ele entende a operação da corretora e pode executar ou orientar tarefas reais.
```

No MVP, esse momento deve ser simples e confiável:

1. AutoBrokers responde no chat.
2. AutoBrokers entende o contexto básico da corretora.
3. Usuário consegue ir para atendimentos.
4. Usuário consegue ativar ou iniciar um Auxiliar simples.
5. Sistema mostra que existe uma base operacional pronta para evoluir.

---

## 5. Princípios de produto

### 5.1 Chat-first

A página inicial do dashboard da corretora é o chat do AutoBrokers. Não existe uma home cheia de cards, métricas e blocos.

A experiência inicial deve ser limpa:

- sidebar à esquerda;
- centro com saudação e input;
- dois atalhos no máximo: **Ver atendimentos** e **Novo auxiliar**;
- sem dashboard operacional poluído na primeira tela.

### 5.2 Mobile-first

O produto deve ser pensado para funcionar bem no celular, mesmo que muitos usuários operem no desktop.

Padrão desejado:

- navegação simples;
- páginas em camadas;
- transição lateral no mobile ao entrar em detalhes;
- ações claras;
- sem tabelas pesadas como experiência principal no celular.

### 5.3 Simplicidade visual

Referências principais:

- ChatGPT: home limpa, apps/connectors, biblioteca, modais de conexão.
- Claude: chat, projetos, rotinas, criação de rotina por etapas.
- ResultVision antigo: domínio de seguros e páginas de seguradoras/corredores.

Não copiar código ou marca, apenas lógica de UX.

### 5.4 Domínio de seguros acima de jargão técnico

O corretor não deve precisar entender MCP, webhook, permission guard, RAG, vector DB ou LangGraph.

A linguagem deve ser de seguros:

- conectar seguradora;
- habilitar corredor;
- revisar portal;
- criar auxiliar;
- acompanhar atendimento;
- aprovar ação;
- enviar mensagem;
- cobrar documento.

---

## 6. Os três tipos de agente

### 6.1 AutoBrokers

Agente central e fixo de cada corretora.

Regras:

- nome visível sempre **AutoBrokers**;
- não é personalizável pelo cliente;
- é a porta de entrada do sistema;
- conversa com o usuário interno da corretora;
- consulta conhecimento, atendimento, Auxiliares, logs e integrações conforme permissões;
- futuramente poderá executar ações com aprovação humana.

### 6.2 Agentes de atendimento

Agentes voltados ao atendimento externo de clientes da corretora.

Exemplos:

- assistência;
- sinistro;
- renovação;
- cobrança de documentos;
- atendimento geral.

Regras:

- podem ser personalizados pela corretora;
- podem ter nome, tom, avatar e regras específicas;
- são conectados aos canais de atendimento;
- devem respeitar guardrails e approval flows.

### 6.3 Auxiliares

Automações inteligentes para tarefas repetitivas ou recorrentes.

Exemplos:

- resumo diário da operação;
- cobrança de documentos pendentes;
- follow-up de renovação;
- monitoramento de sinistros;
- relatório de faturamento;
- consulta de pendências em seguradoras;
- preparação de mensagem para clientes.

Regras:

- devem usar o motor de agents/subagents/delegations/tools do Smith;
- devem ter galeria global criada no Admin;
- corretoras podem ativar e personalizar;
- ações externas reais devem ter aprovação humana no MVP;
- scheduler e criação por prompt podem entrar depois da galeria/manual.

---

## 7. Escopo do MVP recomendado

### P0 — Base vendável mínima

1. Login e multi-tenant funcionando.
2. Admin Global funcionando.
3. Dashboard da corretora com AutoBrokers chat-first.
4. Branding limpo: sem Smith/JARVYS visível para cliente.
5. Sidebar mínima e coerente.
6. Atendimento como módulo acessível, mesmo que inicialmente simples.
7. Auxiliares como módulo planejado, com primeira galeria/manual.
8. Conhecimento mínimo: upload/consulta simples antes de Docling avançado.
9. Conectores/Vault documentados, mesmo que implementação venha depois.
10. Logs e custos básicos preservados.

### P1 — Diferenciação operacional

1. Primeiro Auxiliar funcional.
2. Base de conhecimento por corretora.
3. Templates globais de Auxiliares no Admin.
4. Primeira versão de Atendimento redesenhada a partir do ResultVision.
5. Seguradoras/corredores como experiência limpa em camadas.
6. Histórico de execuções dos Auxiliares.
7. Aprovação humana para ações sensíveis.

### P2 — Integrações reais

1. Evolution/WhatsApp real.
2. n8n como gateway de integrações.
3. InfoCap/Quiver/portais.
4. Docling completo.
5. Worker/Celery scheduler.
6. RAG avançado com reranking.
7. Billing/Stripe real.

---

## 8. Fora de escopo agora

Não implementar agora:

- home cheia de cards;
- dashboard tradicional como primeira tela;
- criação livre de Auxiliares por prompt sem governança;
- scheduler complexo antes da galeria/manual;
- portais de seguradora reais sem Vault/approvals;
- copiar Agent OS V2 inteiro para o runtime;
- copiar código bruto do ResultVision;
- reescrever Admin Global antes de resolver tenant UX.

---

## 9. Critérios de sucesso da fase atual

A fase atual estará correta quando:

1. `/dashboard` abrir direto o AutoBrokers chat-first.
2. Não aparecer JARVYS, Smith ou Agent Smith no tenant.
3. Sidebar tenant estiver mínima e sem links mortos.
4. O chat continuar respondendo.
5. Existir documentação canônica clara para Claude Design e Claude Code.
6. Qualquer novo chat/IA entender a diferença entre Smith, ResultVision, Agent OS V2 e AutoBrokers.ai.

---

## 10. Fonte de verdade

Quando houver conflito:

1. Decisões recentes do fundador e desta pasta `docs/canon/` vencem.
2. ADRs/docs antigos são históricos.
3. Código atual mostra estado real, mas não necessariamente decisão correta.
4. ResultVision é referência, não runtime.
5. Smith é runtime, não produto final.

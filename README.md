# AutoBrokers Intelligence OS

**AutoBrokers Intelligence OS** é a fundação técnica, operacional e estratégica do **AutoBrokers.ai**, uma plataforma SaaS multi-tenant de inteligência artificial para corretoras de seguros.

O objetivo do AutoBrokers.ai é transformar a rotina de corretoras em um sistema operacional inteligente, onde o corretor conversa com o **AutoBrokers**, ativa **Auxiliares**, organiza **Atendimentos**, conecta **seguradoras e sistemas**, usa **conhecimento curado** e automatiza tarefas repetitivas com segurança, rastreabilidade e controle humano.

Este repositório é a nova base oficial do produto.

Ele usa o runtime técnico do Smith V6.2 como fundação, mas o produto final não é Smith. O produto final é **AutoBrokers.ai**.

---

## 1. Resumo executivo

O AutoBrokers.ai está sendo reconstruído a partir de três grandes fontes:

```txt
AutoBrokers.ai
= Product Layer
+ Smith Runtime Engine
+ AutoBrokers Domain Brain
```

### 1.1 Product Layer

Camada de produto, marca, experiência, navegação, UX/UI, módulos e linguagem final.

Ela define o que o usuário vê:

- AutoBrokers como agente central;
- Dashboard da Corretora;
- Admin Global;
- Atendimentos;
- Auxiliares;
- Personalização;
- Conectores;
- Seguradoras;
- Conhecimento;
- Logs;
- Custos;
- Governança.

### 1.2 Smith Runtime Engine

Camada técnica herdada/adaptada do Smith V6.2.

Ela fornece infraestrutura já existente:

- Next.js;
- FastAPI;
- LangGraph;
- agents;
- subagents;
- delegations;
- tools;
- MCP;
- RAG;
- Qdrant;
- MinIO;
- Redis;
- Supabase;
- billing;
- logs;
- documentos;
- admin multi-tenant;
- chat streaming;
- base para Auxiliares;
- base para Knowledge/RAG;
- base para integrações.

Smith é infraestrutura.

Smith não é a marca do produto.

### 1.3 AutoBrokers Domain Brain

Camada de domínio de seguros.

Ela vem de materiais anteriores do projeto:

- ResultVision;
- AutoBrokers antigo;
- Agent OS;
- AutoBrokers Intelligence OS V2;
- corredores;
- skills;
- guardrails;
- templates;
- contratos;
- conversas reais;
- materiais de atendimento;
- intake bruto;
- análise de seguradoras;
- fluxos de assistência e sinistro.

Essa camada não deve ser copiada bruta para dentro do runtime.

Ela precisa ser inventariada, curada, reescrita, validada e transformada em pacotes operacionais.

---

## 2. Visão do produto

O AutoBrokers.ai não deve parecer um CRM tradicional, um ERP antigo ou um dashboard cheio de cards.

A visão é:

```txt
Um ChatGPT/Claude especializado em corretoras de seguros,
com módulos operacionais conectados ao redor.
```

O usuário entra no sistema e encontra o **AutoBrokers** como centro da experiência.

A partir dele, pode:

- perguntar sobre sua corretora;
- pedir ajuda operacional;
- abrir atendimentos;
- criar ou ativar Auxiliares;
- consultar conhecimento;
- conectar ferramentas;
- acompanhar execuções;
- revisar pendências;
- operar casos;
- organizar clientes;
- analisar dados;
- automatizar tarefas;
- acessar módulos conforme necessidade.

A experiência deve ser:

- chat-first;
- mobile-first;
- limpa;
- moderna;
- premium;
- segura;
- objetiva;
- altamente especializada em seguros;
- simples por fora e poderosa por dentro.

---

## 3. Problema que o AutoBrokers resolve

Corretoras de seguros operam com muitas tarefas repetitivas e fragmentadas:

- WhatsApp de clientes;
- WhatsApp de seguradoras;
- portais de seguradoras;
- sistemas como InfoCap, Quiver, Segfy e Capta;
- documentos;
- apólices;
- renovações;
- cobranças;
- sinistros;
- assistências;
- follow-ups;
- pendências;
- mensagens manuais;
- protocolos;
- prestadores;
- histórico de atendimento;
- gestão de equipe;
- relatórios;
- cobranças;
- reputação;
- atendimento humano;
- múltiplas regras por seguradora.

O resultado é:

- perda de tempo;
- falta de rastreabilidade;
- retrabalho;
- atendimento inconsistente;
- risco de erro;
- dependência de pessoas específicas;
- dificuldade de escalar;
- baixa automação;
- pouca inteligência operacional.

O AutoBrokers.ai organiza isso em uma plataforma única.

---

## 4. Solução

O AutoBrokers.ai entrega uma camada de inteligência operacional para corretoras.

A plataforma combina:

- chat central com IA;
- agentes de atendimento;
- Auxiliares especializados;
- conectores;
- Vault de permissões;
- base de conhecimento;
- RAG;
- integrações;
- logs;
- custos;
- atendimento;
- corredores;
- análise;
- governança;
- Admin Global.

O produto deve permitir que uma corretora tenha:

```txt
1. Um AutoBrokers central para conversar e operar.
2. Agentes de atendimento para clientes/segurados.
3. Auxiliares para tarefas específicas.
4. Conectores reutilizáveis.
5. Conhecimento global e conhecimento da corretora.
6. Atendimento estruturado e rastreável.
7. Governança, permissões e logs.
```

---

## 5. Estado atual do projeto

Este repositório representa o novo runtime oficial em sandbox.

Status atual:

- sandbox instalado;
- EasyPanel em uso;
- Web Next.js funcionando;
- API FastAPI funcionando;
- Supabase sandbox configurado;
- Redis configurado;
- Qdrant configurado;
- MinIO configurado;
- Admin acessível;
- login de tenant funcionando;
- chat tenant funcionando;
- AutoBrokers responde em sandbox;
- docs canônicos em `docs/canon/`;
- docs históricas movidas para `docs/_archive/`;
- `/dashboard` deve permanecer chat-first;
- ResultVision é referência, não runtime;
- Agent OS é fonte de domínio, não runtime ativo;
- intake bruto é sensível e bloqueado para uso direto.

Ainda não está pronto:

- design system final;
- UX final aprovada;
- sidebar final;
- módulo Auxiliares como produto final;
- Vault operacional completo;
- RAG com curadoria segura;
- Atendimento reconstruído no novo runtime;
- corredores portados;
- WhatsApp real;
- InfoCap/Quiver reais;
- Docling/worker em fluxo definitivo;
- integração real com seguradoras;
- produção.

---

## 6. Identidade e nomes oficiais

### 6.1 Produto

```txt
AutoBrokers.ai
```

### 6.2 Sistema / repositório

```txt
AutoBrokers Intelligence OS
```

### 6.3 Agente central da corretora

```txt
AutoBrokers
```

O agente central usa o nome **AutoBrokers** no plural, mesmo sendo um agente principal único.

### 6.4 Termos proibidos como marca visível

Não usar como marca visível do produto:

- JARVYS;
- Smith;
- Agent Smith;
- Smith AI;
- Sistema Smith;
- LionClaw;
- OpenClaw.

Smith pode permanecer apenas como referência técnica/proveniência em documentação técnica, quando necessário.

---

## 7. Tipos de inteligência no produto

O sistema possui três tipos principais de inteligência.

### 7.1 AutoBrokers

É o agente central da corretora.

Características:

- nome fixo;
- não personalizável;
- aparece na tela principal;
- conversa com usuários internos da corretora;
- entende a operação;
- consulta conhecimento;
- orienta;
- ajuda na gestão;
- futuramente aciona Auxiliares;
- futuramente acessa Atendimentos, Conectores e Conhecimento.

Ele é o centro do produto.

### 7.2 Agentes de Atendimento

São agentes que atuam em fluxos de atendimento com clientes e segurados.

Características:

- podem ser personalizados;
- podem ter nome, tom e estilo;
- podem atender assistência, sinistro, renovação ou suporte;
- operam no módulo Atendimentos;
- seguem corredores, guardrails e fluxos seguros;
- podem conversar com clientes externos.

Eles são diferentes do AutoBrokers central.

### 7.3 Auxiliares

São automações inteligentes e especializadas.

Exemplos:

- Auxiliar de Cobrança;
- Auxiliar de Renovação;
- Auxiliar de Resumo de Atendimentos;
- Auxiliar de Relatório Diário;
- Auxiliar de Pendências;
- Auxiliar de Conferência de Documentos;
- Auxiliar de Reputação Google;
- Auxiliar de Follow-up;
- Auxiliar de Recuperação de Leads.

Auxiliares devem usar o motor de agents/subagents/delegations/tools do Smith, mas com uma camada de produto própria para corretoras.

---

## 8. Módulos principais

### 8.1 AutoBrokers

Tela principal do Dashboard da Corretora.

Deve ser chat-first.

Não deve ser um dashboard cheio de cards.

Deve conter:

- sidebar limpa;
- AutoBrokers no centro;
- frase simples;
- caixa de mensagem;
- histórico de conversas;
- botão nova conversa;
- dois atalhos iniciais:
  - Ver atendimentos;
  - Novo auxiliar.

### 8.2 Atendimentos

Módulo operacional para demandas reais de clientes/segurados.

Inclui, progressivamente:

- painel;
- fila;
- casos;
- conversas;
- ligações;
- segurados;
- status;
- histórico;
- handoff;
- mídia;
- documentos;
- ações;
- acompanhamento.

Atendimento não é configuração.

Atendimento é operação.

### 8.3 Auxiliares

Módulo de automações especializadas.

Inclui, progressivamente:

- Meus Auxiliares;
- Galeria;
- Execuções;
- detalhe do Auxiliar;
- ativação;
- personalização;
- permissões;
- conectores;
- execução manual;
- histórico;
- aprovação humana.

### 8.4 Personalização

Área onde a corretora configura o sistema.

Pode incluir:

- dados da corretora;
- equipe;
- agentes de atendimento;
- conectores;
- seguradoras;
- canais;
- conhecimento;
- documentos;
- permissões;
- custos;
- preferências;
- configurações avançadas.

### 8.5 Conectores

Camada visual para integrações.

Exemplos:

- WhatsApp;
- e-mail;
- Google Drive;
- Google Calendar;
- Slack;
- Notion;
- InfoCap;
- Quiver;
- Segfy;
- portais de seguradoras;
- APIs;
- MCPs;
- documentos;
- webhooks.

A experiência deve seguir lógica parecida com Apps/Connectors do ChatGPT:

```txt
Galeria
→ detalhe
→ conectar
→ permissões
→ status
```

### 8.6 Conhecimento

Base de conhecimento global e da corretora.

Inclui:

- documentos;
- arquivos;
- memória;
- fontes globais;
- fontes privadas;
- RAG;
- curadoria;
- classificação;
- redaction;
- permissões.

### 8.7 Admin Global

Área interna da equipe AutoBrokers.

A corretora não acessa o Admin Global.

O Admin Global serve para:

- gerenciar corretoras;
- gerenciar planos;
- custos;
- usuários;
- agentes;
- documentos;
- templates globais;
- Auxiliares globais;
- conectores globais;
- logs;
- billing;
- governança;
- auditoria;
- configurações internas.

---

## 9. Arquitetura técnica

### 9.1 Frontend

O frontend usa Next.js.

Pastas principais:

```txt
app/
components/
lib/
hooks/
types/
public/
```

### 9.2 Backend

O backend usa FastAPI.

Pastas principais:

```txt
backend/app/
backend/app/api/
backend/app/agents/
backend/app/services/
backend/app/workers/
```

### 9.3 Banco e storage

Infraestrutura atual:

- Supabase;
- Supabase Auth;
- Postgres;
- Supabase storage/migrations;
- MinIO;
- Qdrant;
- Redis.

### 9.4 IA e agentes

O runtime técnico atual possui:

- LangGraph;
- agents;
- subagents;
- delegations;
- tools;
- MCP;
- HTTP tools;
- RAG;
- memory;
- billing;
- usage logs.

### 9.5 Documentos e RAG

O sistema possui caminhos para:

- upload de documentos;
- armazenamento;
- ingestão;
- chunks;
- embeddings;
- Qdrant;
- RAG;
- sanitização;
- Docling futuro.

Mas dados reais e intake bruto não podem ser ingeridos sem curadoria.

---

## 10. Runtime oficial

O runtime oficial é este repositório:

```txt
AutoBrokers-Intelligence-OS
```

Repositórios/pastas antigas são referência, não runtime oficial.

### 10.1 ResultVision

Papel:

```txt
Referência histórica de domínio, atendimento, seguradoras, corredores, UX operacional e lógica antiga.
```

Não copiar bruto.

Não usar como runtime.

### 10.2 Agent OS / AutoBrokers Intelligence V2

Papel:

```txt
Fonte de arquitetura, cérebro, skills, corredores, guardrails e contratos.
```

Não carregar diretamente no runtime.

Usar como fonte para curadoria.

### 10.3 AUTOBROKERS_RESULTA_INTAKE

Papel:

```txt
Fonte bruta de evidências reais.
```

Contém dados sensíveis.

Não ingerir diretamente.

### 10.4 QUARENTENA_LEGADO

Papel:

```txt
Legado isolado.
```

Não usar automaticamente.

Não copiar para o repo novo.

---

## 11. Documentação canônica

A documentação ativa do projeto fica em:

```txt
docs/canon/
```

Arquivos principais:

```txt
docs/canon/README.md
docs/canon/PRD-001-visao-produto.md
docs/canon/ADR-001-runtime.md
docs/canon/UX-001-navegacao.md
docs/canon/DS-001-design-brief.md
docs/canon/UX-007-auxiliares.md
docs/canon/ADR-002-vault.md
docs/canon/ADR-003-atendimento.md
docs/canon/ROADMAP-001-execucao.md
```

Qualquer novo chat ou ferramenta deve ler primeiro:

```txt
docs/canon/README.md
docs/canon/PRD-001-visao-produto.md
docs/canon/ADR-001-runtime.md
docs/canon/UX-001-navegacao.md
docs/canon/ROADMAP-001-execucao.md
```

Docs antigos ficam em:

```txt
docs/_archive/
```

Docs arquivados são históricos.

Não são fonte de verdade atual.

---

## 12. Regras de UX

### 12.1 Chat-first

A tela inicial do tenant é o chat AutoBrokers.

Não criar Home de cards como primeira tela.

### 12.2 Mobile-first

O produto deve funcionar muito bem no celular.

Fluxos devem ser pensados em camadas.

Exemplo:

```txt
Galeria
→ detalhe
→ configuração
→ permissão
→ confirmação
```

### 12.3 Sidebar enxuta

A sidebar não deve ter 30 itens.

Pilares iniciais:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

### 12.4 Operação separada de configuração

Atendimento é operação.

Personalização é configuração.

Não misturar.

### 12.5 Visual limpo

A referência visual é:

- ChatGPT;
- Claude;
- Claude Routines;
- Apps/Connectors;
- páginas limpas;
- poucos cards;
- poucas cores;
- baixa densidade;
- navegação progressiva;
- dark mode como padrão.

### 12.6 Não reviver telas antigas rejeitadas

Não trazer de volta:

- Home da corretora cheia de cards;
- Estudos;
- Conversa ao vivo antiga;
- dashboard denso como primeira tela;
- menu inchado.

---

## 13. Vault

O Vault é a camada de confiança do sistema.

Ele governa:

- credenciais;
- conectores;
- permissões;
- fontes de conhecimento;
- acessos;
- ações;
- logs;
- aprovações;
- tenant isolation;
- uso de dados sensíveis.

Regra central:

```txt
Conectar uma vez.
Permitir com clareza.
Usar com segurança.
Auditar sempre.
Revogar facilmente.
```

Uma conexão pertence à corretora e pode ser reutilizada por:

- AutoBrokers;
- Atendimentos;
- Auxiliares;
- Conhecimento;
- módulos futuros.

Mas cada uso precisa respeitar permissões.

---

## 14. Segurança e dados sensíveis

Este projeto lida com dados sensíveis.

Podem existir:

- nomes;
- telefones;
- CPFs;
- e-mails;
- apólices;
- documentos;
- conversas;
- imagens;
- áudios;
- endereços;
- placas;
- informações financeiras;
- credenciais;
- dados de sinistro;
- dados de assistência.

Regras absolutas:

- não commitar `.env`;
- não imprimir secrets;
- não expor service role no client;
- não usar `NEXT_PUBLIC_` para segredo;
- não ingerir intake bruto em RAG;
- não copiar dados reais para docs;
- não misturar tenants;
- não rodar migrations sem aprovação;
- não executar integrações reais sem autorização;
- não enviar WhatsApp/e-mail real sem HITL no MVP.

---

## 15. Atendimento e corredores

Atendimento é um módulo operacional.

Corredor é apenas uma parte do atendimento.

Ciclo de atendimento:

```txt
Entrada
→ entendimento
→ coleta
→ identificação
→ apólice/elegibilidade
→ classificação
→ decisão
→ preparação
→ corredor
→ acionamento assistido
→ retorno
→ comunicação ao cliente
→ acompanhamento
→ handoff
→ encerramento
→ aprendizado
```

Corredores representam rotas operacionais por:

- seguradora;
- ramo;
- canal;
- serviço;
- subserviço.

Exemplo:

```txt
Allianz
→ Assistência Residencial
→ WhatsApp
→ Eletricista
```

No MVP, corredores devem ser assistidos, controlados, com no-send/dry-run/HITL.

Não implementar todos os corredores de uma vez.

---

## 16. Auxiliares

Auxiliares são automações especializadas.

Estrutura desejada:

```txt
Meus Auxiliares
Galeria
Execuções
```

Fluxo:

```txt
Galeria
→ escolher Auxiliar
→ detalhe
→ ativar
→ personalizar
→ conectar fontes
→ permissões
→ teste
→ ativar
→ acompanhar execuções
```

MVP recomendado:

- Galeria;
- Meus Auxiliares;
- Execuções;
- ativação;
- execução manual;
- histórico;
- permissões simples;
- primeiro Auxiliar funcional de baixo risco.

Primeiro Auxiliar recomendado:

```txt
Auxiliar de Resumo de Atendimentos
```

Segundo candidato:

```txt
Auxiliar de Cobrança com rascunhos aprováveis
```

---

## 17. RAG e conhecimento

RAG é importante, mas não deve começar com dados sensíveis.

Primeira validação deve usar documento simples e seguro.

Regras:

- documentos precisam de escopo;
- documentos precisam de permissão;
- conhecimento global e tenant devem ser separados;
- fontes precisam ser rastreáveis;
- dados brutos precisam de redaction/curadoria;
- Qdrant/MinIO precisam respeitar tenant isolation.

---

## 18. Integrações

Integrações reais entram progressivamente.

Ordem provável:

```txt
1. Documentos/RAG simples
2. Google Drive ou upload manual
3. WhatsApp sandbox/dry-run
4. E-mail/SendGrid
5. Docling
6. Sentry/LangSmith
7. InfoCap leitura
8. Quiver/Segfy leitura
9. portal assistido
10. execução real controlada
```

Integrações reais exigem:

- Vault;
- permissão;
- logs;
- fallback;
- health check;
- HITL;
- segurança;
- rollback quando aplicável.

---

## 19. O que não fazer agora

Não fazer agora:

- nova Home visual sem Claude Design;
- sidebar definitiva via Codex;
- dashboard denso;
- ingestão de intake bruto;
- migração cega do ResultVision;
- cópia bruta do Agent OS;
- todos os corredores;
- WhatsApp real irrestrito;
- portal automático;
- InfoCap/Quiver real com escrita;
- scheduler complexo de Auxiliares;
- criação de Auxiliares por prompt;
- mudanças grandes no banco sem ADR;
- alterações de licença sem decisão jurídica;
- remoção apressada de nomes técnicos internos que possam quebrar compatibilidade.

---

## 20. Processo de execução

Toda tarefa deve seguir batch controlado.

Um batch precisa conter:

- nome;
- objetivo;
- contexto;
- arquivos permitidos;
- arquivos proibidos;
- fora de escopo;
- passos;
- checks;
- critérios de pronto;
- relatório esperado.

Nunca pedir:

```txt
Melhore o dashboard.
```

Sempre pedir:

```txt
Implemente apenas o Empty State aprovado do AutoBrokers em /dashboard, sem alterar backend, Supabase ou rotas novas.
```

---

## 21. Ferramentas e responsabilidades

### Architect / ChatGPT estratégico

Define:

- produto;
- arquitetura;
- roadmap;
- docs;
- prompts;
- decisões.

### Claude Strategy

Revisa:

- visão;
- PRD;
- UX;
- ADRs;
- contradições;
- perguntas abertas.

### Claude Design

Cria:

- design system;
- UX;
- telas;
- fluxos;
- componentes;
- mobile;
- hierarquia visual.

### Claude Code

Implementa:

- tarefas fechadas;
- código;
- refactors;
- componentes;
- testes;
- commits.

### Codex

Executa:

- auditorias;
- patches mecânicos;
- validações;
- inventários;
- commits técnicos pequenos.

Codex não deve criar grandes experiências visuais.

---

## 22. Desenvolvimento local

Scripts frontend confirmados:

```bash
npm run dev
npm run build
npm run start
npm run lint
npm run typecheck
```

Dependências backend:

```txt
backend/requirements.txt
```

Não executar sem batch específico:

- migrations;
- seed scripts;
- workers;
- Docling;
- deploy;
- integrações externas;
- scripts que conectem em produção;
- scripts que leiam dados sensíveis.

---

## 23. Estrutura do repositório

Pastas principais:

```txt
app/                         Next.js app routes
components/                  React components
lib/                         helpers frontend/server
hooks/                       React hooks
types/                       TypeScript types
backend/app/                 FastAPI backend
backend/app/api/             Backend API routers
backend/app/agents/          LangGraph agents runtime
backend/app/services/        Runtime services
backend/app/workers/         Workers/Celery paths
backend/supabase/migrations/ Historical SQL/migrations
docling-service/             Document parsing/conversion service
docs/canon/                  Active canonical docs
docs/_archive/               Historical documentation archive
docs/ops/                    Operational docs
public/                      Static assets and widget files
```

---

## 24. Infraestrutura sandbox

Sandbox atual usa:

- EasyPanel;
- Next.js web service;
- FastAPI API service;
- Supabase sandbox;
- Redis;
- Qdrant;
- MinIO;
- OpenAI/LLM key;
- envs configuradas;
- Admin Master;
- tenant de teste.

Este README não contém credenciais.

Nenhuma credencial deve ser adicionada ao README.

---

## 25. Git e segurança

Regras:

```txt
Nunca usar git add .
```

Preferir:

```bash
git add path/do/arquivo.md
```

Antes de commit:

```bash
git status --short
git diff --check
npm run typecheck
npm run build   # quando aplicável
```

Não commitar:

- `.env`;
- credenciais;
- tokens;
- dumps;
- intake bruto;
- imagens sensíveis;
- áudios;
- PDFs reais;
- conversas reais;
- worktrees;
- quarentena;
- node_modules;
- caches;
- arquivos locais de IDE.

---

## 26. Roadmap resumido

### Fase 0 — Base e limpeza

- runtime instalado;
- sandbox funcionando;
- chat funcionando;
- docs canônicos;
- README atualizado;
- branding visível limpo.

### Fase 1 — Documentação canônica

- PRD;
- ADR runtime;
- UX navegação;
- Design brief;
- Auxiliares;
- Vault;
- Atendimento;
- Roadmap.

### Fase 2 — Claude Strategy

- revisar docs;
- apontar contradições;
- sugerir ajustes;
- preparar handoff para Claude Design.

### Fase 3 — Claude Design

- design system;
- sidebar;
- mobile;
- chat-first;
- Auxiliares;
- Conectores;
- Personalização;
- Atendimento;
- specs para Claude Code.

### Fase 4 — Shell visual

- chat-first definitivo;
- sidebar;
- empty state;
- dois atalhos;
- mobile;
- sem cards poluídos.

### Fase 5 — Auxiliares MVP

- Galeria;
- Meus Auxiliares;
- Execuções;
- um Auxiliar funcional de baixo risco.

### Fase 6 — Vault/Conectores

- Conectores;
- permissões;
- status;
- logs;
- reutilização por módulo.

### Fase 7 — RAG curado

- documento seguro;
- fonte rastreável;
- conhecimento global/tenant;
- isolamento.

### Fase 8 — Atendimento base

- fila;
- caso;
- conversa;
- status;
- handoff;
- histórico.

### Fase 9 — Primeiro corredor assistido

- Allianz Residencial ou outro fluxo escolhido;
- no-send/dry-run;
- golden tests;
- HITL;
- logs.

### Fase 10 — Piloto real

- hardening;
- observabilidade;
- custos;
- segurança;
- integrações controladas;
- corretora piloto.

---

## 27. Critérios de sucesso do MVP inicial

O MVP inicial estará no caminho certo quando o usuário conseguir:

1. Entrar no sistema.
2. Conversar com o AutoBrokers.
3. Entender que o chat é a porta de entrada.
4. Abrir Atendimentos.
5. Abrir Auxiliares.
6. Ver uma Galeria de Auxiliares.
7. Executar ou testar um Auxiliar simples.
8. Entender onde configura conectores.
9. Usar conhecimento básico seguro.
10. Não ver Smith/JARVYS como produto.
11. Usar no mobile sem sofrimento.
12. Demonstrar o produto sem pedir desculpas pela interface.

---

## 28. Critérios de sucesso do produto vendável

O produto começa a ficar vendável quando:

- UX parece premium;
- AutoBrokers é útil;
- Auxiliares economizam tempo real;
- Atendimento tem fluxo claro;
- Conectores são compreensíveis;
- Vault protege ações;
- logs dão confiança;
- custos são monitorados;
- RAG não vaza dados;
- pelo menos um fluxo real assistido funciona;
- corretora entende valor em poucos minutos;
- founder consegue demonstrar com segurança.

---

## 29. Proveniência técnica

Este repositório foi criado a partir de uma base técnica inspirada/adaptada do Agent Smith V6.2.

Essa proveniência explica nomes técnicos residuais em código, migrations, filas, assets ou arquivos históricos.

Esses nomes não são marca do produto.

Não remover nomes técnicos internos sem batch específico, porque isso pode quebrar compatibilidade.

Não alterar arquivos de licença sem decisão jurídica/produto.

---

## 30. Mensagem para qualquer novo agente/LLM

Se você é uma IA entrando neste projeto agora:

1. Não comece codando.
2. Leia `docs/canon/`.
3. Entenda que o produto é AutoBrokers.ai.
4. Entenda que Smith é runtime invisível.
5. Entenda que ResultVision é referência, não runtime.
6. Entenda que Agent OS é fonte de domínio, não import bruto.
7. Entenda que `/dashboard` é chat-first.
8. Não crie dashboard cheio de cards.
9. Não use JARVYS.
10. Não use Smith como marca visível.
11. Não ingira intake bruto.
12. Não execute ação externa real sem Vault/HITL/logs.
13. Não tome decisões estratégicas sozinho.
14. Trabalhe em batches pequenos.
15. Preserve o que funciona.
16. Documente mudanças.
17. Rode checks.
18. Não exponha secrets.

---

## 31. Direção final

O AutoBrokers.ai deve ser simples por fora e poderoso por dentro.

A experiência principal deve começar assim:

```txt
AutoBrokers
[caixa de mensagem]

Ver atendimentos | Novo auxiliar
```

A partir dessa entrada simples, o produto deve abrir um sistema completo de:

```txt
Atendimentos
Auxiliares
Personalização
Conectores
Conhecimento
Seguradoras
Vault
Admin Global
```

O objetivo é criar o sistema operacional de IA mais completo e confiável para corretoras de seguros.

Este README é a porta de entrada do projeto.

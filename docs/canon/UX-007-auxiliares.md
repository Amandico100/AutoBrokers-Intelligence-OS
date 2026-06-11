---
# UX-007 — Auxiliares do AutoBrokers.ai

> **Decisão canônica: Auxiliares usam Smith Agents/Subagents como runtime** (ver [SPEC-002](SPEC-002-auxiliares-runtime-smith.md)). Auxiliares = produto/catálogo/UX/governança; o runtime técnico é um **Agent/Subagent Smith**, um executor específico ou um workflow. Templates globais guardam **blueprint** (não um agent compartilhado); o agent real é criado **por corretora** ao instalar. Ações externas via **Vault + HITL**. **Não criar motor paralelo.**

Status: canonical  
Produto: AutoBrokers.ai  
Sistema: AutoBrokers Intelligence OS  
Documento: arquitetura de produto, UX e runtime conceitual do módulo Auxiliares  
Última atualização: 2026-06-06  
Responsável estratégico: Architect / CEO AutoBrokers.ai  
Audiência: Claude Design, Claude Code, Codex, LLMs estratégicas, devs, UX/UI e time fundador

---

# 1. Objetivo deste documento

Este documento define o módulo **Auxiliares** do AutoBrokers.ai.

Auxiliares são automações inteligentes, configuráveis e reutilizáveis, criadas para executar tarefas repetitivas, operacionais, analíticas ou estratégicas dentro de uma corretora de seguros.

O objetivo deste documento é deixar claro:

- o que são Auxiliares;
- o que não são Auxiliares;
- como eles se diferenciam do AutoBrokers central;
- como eles se diferenciam dos agentes de atendimento;
- como devem aparecer no Dashboard da Corretora;
- como devem ser criados no Admin Global;
- como devem ser ativados por corretora;
- como devem usar conectores, permissões e conhecimento;
- como devem evoluir por fases;
- como Claude Design deve desenhar a experiência;
- como Claude Code deve implementar sem inventar produto.

Decisão central:

```txt
Auxiliares são a camada de automação especializada do AutoBrokers.ai.
Eles usam o motor técnico do Smith, mas precisam de uma camada de produto própria para corretoras de seguros.
```

---

# 2. Definição curta

Um Auxiliar é um agente especializado em uma tarefa específica.

Exemplos:

- Auxiliar de Cobrança;
- Auxiliar de Renovação;
- Auxiliar de Follow-up;
- Auxiliar de Conferência de Documentos;
- Auxiliar de Resumo de Atendimentos;
- Auxiliar de Recuperação de Leads;
- Auxiliar de Análise de Sinistros;
- Auxiliar de Relatório Diário;
- Auxiliar de Reputação/Google Meu Negócio;
- Auxiliar de Prospecção;
- Auxiliar de Pendências;
- Auxiliar de Mensagens para Clientes;
- Auxiliar de Oportunidades Comerciais.

O usuário não deve precisar entender “subagent”, “delegation”, “tool” ou “LangGraph”.

Para o corretor, a experiência deve ser simples:

```txt
Escolha um Auxiliar pronto.
Personalize.
Conecte as fontes necessárias.
Defina permissões.
Teste.
Ative.
Acompanhe execuções.
```

---

# 3. Nome oficial

O nome oficial do módulo é:

```txt
Auxiliares
```

Não usar como nome principal:

- Rotinas;
- Routines;
- Subagentes;
- Agentes secundários;
- Automações, como módulo principal;
- Bots;
- Robôs;
- Skills, como nome visível;
- Workers;
- MCPs;
- Tools.

“Rotina” pode aparecer apenas como conceito interno ou explicativo, quando necessário.

Exemplo aceitável:

```txt
Este Auxiliar pode rodar como uma rotina diária às 17h.
```

Exemplo ruim:

```txt
Crie uma rotina subagent com tools MCP.
```

---

# 4. Diferença entre AutoBrokers, Auxiliares e Agentes de Atendimento

O produto tem três tipos de inteligência.

## 4.1 AutoBrokers

AutoBrokers é o agente central da corretora.

Características:

- nome fixo;
- não personalizável;
- aparece na tela inicial;
- funciona como cérebro conversacional;
- entende a corretora;
- responde dúvidas;
- orienta;
- consulta conhecimento;
- futuramente aciona Auxiliares;
- futuramente acessa Atendimentos, Conectores e Conhecimento.

AutoBrokers é como o “Claude/ChatGPT da corretora de seguros”.

Ele não é um Auxiliar.

Ele não é um atendente externo falando com segurado.

Ele é o centro da experiência.

---

## 4.2 Auxiliares

Auxiliares são agentes especializados em tarefas.

Características:

- podem ser ativados/desativados;
- podem ser personalizados;
- podem usar conectores;
- podem ter permissões específicas;
- podem ter gatilhos;
- podem ter histórico de execuções;
- podem ser criados globalmente pelo Admin;
- podem ser instalados por corretora;
- futuramente podem ser criados pela própria corretora;
- futuramente podem ser acionados pelo AutoBrokers.

Auxiliares são “mãos especializadas” do sistema.

---

## 4.3 Agentes de Atendimento

Agentes de Atendimento são personagens/agentes que atuam em fluxos de atendimento com clientes/segurados.

Características:

- podem ter nome, tom, personalidade e configuração;
- atuam em conversas externas ou internas de atendimento;
- podem atender assistência, sinistro, renovação ou suporte;
- seguem fluxos, corredores e guardrails;
- podem conversar com segurado;
- podem operar dentro do módulo Atendimentos.

Eles não são o AutoBrokers central.

Eles também não são Auxiliares genéricos.

---

# 5. Princípio de arquitetura

O motor técnico dos Auxiliares deve aproveitar o que já existe no Smith Runtime.

O Smith já possui:

- agents;
- subagents;
- delegations;
- tools HTTP;
- MCP tools;
- RAG;
- documentos;
- memory;
- logs;
- conversations;
- token usage;
- billing;
- FastAPI;
- LangGraph;
- Qdrant;
- MinIO;
- Supabase;
- workers/Celery.

Portanto, a decisão estratégica é:

```txt
Não criar um segundo motor paralelo de automação.
Criar uma camada de produto “Auxiliares” sobre agents/subagents/delegations/tools do Smith.
```

O que falta não é o motor.

O que falta é produto:

- galeria;
- templates globais;
- ativação por corretora;
- personalização;
- permissões;
- vault;
- histórico de execuções;
- aprovação humana;
- scheduler;
- UX simples;
- observabilidade;
- segurança por ação;
- catálogo administrável.

---

# 6. Inspiração principal

Auxiliares devem se inspirar em Claude Routines.

Mas com identidade AutoBrokers.

A inspiração é a estrutura:

- nome;
- objetivo;
- instruções;
- gatilho;
- conectores;
- conhecimento;
- comportamento;
- permissões;
- execução;
- histórico;
- ajuste contínuo.

Não copiar nome, marca ou interface literalmente.

O módulo deve parecer:

```txt
Claude Routines para corretoras de seguros, integrado ao AutoBrokers.ai.
```

---

# 7. Experiência desejada para o usuário

O usuário deve sentir:

```txt
“Eu escolho um Auxiliar pronto, ajusto para minha corretora e ele começa a trabalhar para mim.”
```

A experiência deve ser:

- simples;
- guiada;
- segura;
- visualmente limpa;
- mobile-first;
- sem jargão técnico;
- com etapas claras;
- com confirmação antes de ações sensíveis;
- com histórico do que foi feito;
- com botão de pausar/desativar.

O usuário deve entender rapidamente:

1. Para que serve este Auxiliar?
2. O que ele precisa acessar?
3. O que ele pode fazer sozinho?
4. O que precisa de minha aprovação?
5. Quando ele roda?
6. Como vejo o que ele fez?
7. Como pauso ou edito?

---

# 8. Estrutura principal do módulo Auxiliares

A navegação do módulo deve ter três áreas principais no MVP:

```txt
Meus Auxiliares
Galeria
Execuções
```

Opcionalmente, uma quarta área futura:

```txt
Criar Auxiliar
```

Mas no MVP a criação livre por prompt não deve ser prioridade.

---

## 8.1 Meus Auxiliares

Mostra os Auxiliares ativados pela corretora.

Cada card deve mostrar:

- nome;
- objetivo curto;
- status;
- última execução;
- próxima execução, se houver;
- conectores usados;
- pendências;
- botão abrir;
- botão pausar/ativar, se seguro.

Status possíveis:

- Ativo;
- Pausado;
- Precisa configurar;
- Aguardando aprovação;
- Com erro;
- Em teste;
- Rascunho.

---

## 8.2 Galeria

Mostra Auxiliares prontos, criados pelo Admin Global AutoBrokers.

A Galeria é o ponto mais importante para adoção.

O usuário deve conseguir filtrar por:

- Vendas;
- Atendimento;
- Financeiro;
- Renovação;
- Sinistro;
- Assistência;
- Gestão;
- Documentos;
- Reputação;
- Leads;
- Relatórios;
- Produtividade.

Cada card da Galeria deve mostrar:

- nome;
- descrição curta;
- benefício;
- categoria;
- conectores necessários;
- nível de risco;
- tempo estimado de configuração;
- botão “Ver detalhes” ou “Ativar”.

Exemplo:

```txt
Auxiliar de Cobrança
Envia lembretes personalizados para clientes com parcelas pendentes.
Requer: base de clientes + WhatsApp ou e-mail.
```

---

## 8.3 Execuções

Mostra histórico do que os Auxiliares fizeram.

Deve incluir:

- data/hora;
- Auxiliar;
- status;
- ação executada;
- resultado;
- custo aproximado de IA;
- necessidade de aprovação;
- erro, se houver;
- link para detalhes.

A página de Execuções é essencial para confiança.

O usuário precisa ver:

```txt
O que o Auxiliar fez, quando fez, com base em quê e qual foi o resultado.
```

---

## 8.4 Criar Auxiliar

Fase futura.

Permite que o usuário descreva um Auxiliar em linguagem natural.

Exemplo:

```txt
Quero um Auxiliar que todo dia às 17h veja os leads sem resposta e me envie um resumo no WhatsApp.
```

O sistema então ajuda a montar:

- nome;
- objetivo;
- gatilho;
- fontes;
- conectores;
- permissões;
- comportamento;
- teste.

Essa fase só deve entrar depois de:

- Galeria pronta;
- ativação pronta;
- permissões prontas;
- histórico pronto;
- HITL mínimo pronto.

---

# 9. Fluxo MVP de ativação de Auxiliar

O fluxo MVP deve ser guiado e seguro.

## 9.1 Fluxo principal

```txt
Galeria
→ Escolher Auxiliar
→ Ver detalhe
→ Ativar
→ Personalizar
→ Conectar fontes
→ Definir permissões
→ Testar
→ Ativar oficialmente
→ Acompanhar execuções
```

---

## 9.2 Página de detalhe do Auxiliar

A página de detalhe deve responder:

- O que este Auxiliar faz?
- Para quem ele serve?
- Que problema resolve?
- Quais informações ele usa?
- Quais conexões precisa?
- Que ações pode executar?
- Precisa de aprovação humana?
- Como será o primeiro teste?
- Como pausar?

Estrutura sugerida:

```txt
Header
Resumo
Benefícios
Como funciona
Conectores necessários
Permissões
Prévia de comportamento
Histórico/avaliações internas
Botão Ativar
```

---

## 9.3 Personalização

A personalização deve ser simples.

Campos possíveis:

- nome visível do Auxiliar;
- descrição interna;
- tom de comunicação;
- público alvo;
- horários permitidos;
- limites de execução;
- canal preferido;
- aprovação obrigatória;
- mensagens padrão;
- fontes de conhecimento;
- regras específicas da corretora.

Não transformar a personalização em formulário técnico gigante.

Usar etapas.

---

## 9.4 Conectores

Um Auxiliar pode precisar de conectores.

Exemplos:

- WhatsApp;
- e-mail;
- Google Calendar;
- Google Drive;
- InfoCap;
- Quiver;
- Segfy;
- portal de seguradora;
- CRM;
- planilha;
- banco interno;
- base de conhecimento;
- documentos.

O Auxiliar não deve criar credenciais próprias duplicadas.

Ele deve usar o Vault/Conectores da corretora.

Regra central:

```txt
Uma conexão configurada pela corretora deve poder ser usada por Atendimento, Auxiliares e AutoBrokers, respeitando permissões.
```

---

## 9.5 Permissões

Antes de ativar, o usuário deve entender o que o Auxiliar pode fazer.

Exemplos de permissões:

- apenas ler dados;
- gerar rascunhos;
- enviar mensagem com aprovação;
- enviar mensagem automaticamente;
- consultar documentos;
- consultar atendimentos;
- criar tarefas;
- acionar outro Auxiliar;
- acessar determinada seguradora;
- acessar determinado canal;
- usar WhatsApp;
- usar e-mail;
- usar sistema de gestão;
- usar portal externo.

No MVP, usar postura conservadora:

```txt
Ações externas reais exigem aprovação humana.
```

---

## 9.6 Teste

Antes de ativar, o usuário deve poder testar.

Exemplo:

```txt
Executar teste com dados fictícios
Executar teste com 1 cliente selecionado
Gerar rascunho sem enviar
```

O teste deve mostrar:

- entrada;
- raciocínio resumido;
- saída;
- ação proposta;
- custo estimado;
- riscos;
- necessidade de aprovação.

---

# 10. Tipos de Auxiliares

## 10.1 Auxiliares de comunicação

Exemplos:

- cobrança;
- follow-up;
- renovação;
- aviso de documentação pendente;
- mensagem pós-atendimento;
- pedido de avaliação;
- reativação de cliente;
- recuperação de lead.

Ações comuns:

- gerar mensagem;
- enviar rascunho;
- enviar com aprovação;
- registrar histórico.

---

## 10.2 Auxiliares de análise

Exemplos:

- análise diária de atendimentos;
- análise de gargalos;
- análise de sinistros;
- análise de produtividade;
- análise de oportunidades;
- relatório de carteira;
- relatório de leads.

Ações comuns:

- ler dados;
- resumir;
- apontar riscos;
- sugerir ações;
- gerar relatório.

---

## 10.3 Auxiliares de documentos

Exemplos:

- conferir apólice;
- verificar documentos faltantes;
- resumir PDF;
- extrair dados;
- comparar proposta;
- organizar anexos;
- preparar dossiê.

Ações comuns:

- ler documento;
- extrair campos;
- classificar;
- apontar pendências;
- gerar checklist.

---

## 10.4 Auxiliares comerciais

Exemplos:

- recuperação de oportunidades;
- cross-sell;
- upsell;
- clientes sem seguro ativo;
- renovação próxima;
- leads frios;
- proposta parada.

Ações comuns:

- identificar oportunidade;
- sugerir abordagem;
- gerar mensagem;
- criar lista de ação.

---

## 10.5 Auxiliares operacionais

Exemplos:

- relatório diário;
- tarefas pendentes;
- fila parada;
- atendimentos atrasados;
- SLA;
- inconsistências;
- produtividade da equipe.

Ações comuns:

- monitorar;
- avisar;
- priorizar;
- criar resumo;
- recomendar ação.

---

# 11. Auxiliares iniciais recomendados

Para MVP, não tentar criar dezenas.

Começar com poucos Auxiliares de alto valor.

## 11.1 Auxiliar de Cobrança

Objetivo:

```txt
Ajudar a corretora a cobrar clientes com parcelas pendentes de forma educada, personalizada e rastreável.
```

Por que é bom para MVP:

- valor claro;
- não depende de corredor complexo;
- pode começar com rascunho;
- fácil de entender;
- aplicável a muitas corretoras.

MVP:

- importar ou selecionar lista;
- gerar mensagens;
- aprovar antes de enviar;
- registrar histórico.

---

## 11.2 Auxiliar de Renovação

Objetivo:

```txt
Identificar clientes próximos da renovação e sugerir ações de contato.
```

Valor:

- diretamente ligado a receita;
- natural para seguros;
- fácil de vender.

MVP:

- listar renovações próximas;
- gerar mensagens;
- sugerir prioridade;
- aprovar contato.

---

## 11.3 Auxiliar de Resumo de Atendimentos

Objetivo:

```txt
Resumir conversas e atendimentos para o corretor entender rapidamente o que aconteceu.
```

Valor:

- útil para equipe;
- reduz tempo;
- não exige envio externo no início.

MVP:

- selecionar conversa;
- gerar resumo;
- destacar pendências;
- sugerir próxima ação.

---

## 11.4 Auxiliar de Pendências

Objetivo:

```txt
Encontrar casos, documentos ou clientes com pendências e organizar uma lista de ação.
```

Valor:

- ajuda operação;
- combina com atendimento;
- reduz esquecimento.

MVP:

- ler base/casos;
- listar pendências;
- priorizar;
- sugerir ação.

---

## 11.5 Auxiliar de Relatório Diário

Objetivo:

```txt
Gerar um resumo diário da operação da corretora.
```

Valor:

- cria hábito;
- mostra inteligência;
- ótimo para dono/gestor.

MVP:

- relatório manual;
- depois agendado;
- envio externo só com aprovação.

---

# 12. Relação com Admin Global

O Admin Global é onde o time AutoBrokers cria e controla os modelos globais de Auxiliares.

No Admin Global devem existir, no futuro:

- catálogo global de Auxiliares;
- templates;
- versões;
- categorias;
- conectores requeridos;
- permissões padrão;
- prompts base;
- regras de segurança;
- exemplos;
- status de publicação;
- tenants que ativaram;
- métricas de uso;
- custo por execução;
- logs globais;
- rollback de versão.

A corretora não deve ver complexidade global.

Ela vê apenas:

```txt
Este Auxiliar está disponível para sua corretora.
Clique para ativar e personalizar.
```

---

# 13. Relação com Dashboard da Corretora

No Dashboard da Corretora, o módulo Auxiliares deve ser simples.

Áreas visíveis:

```txt
Meus Auxiliares
Galeria
Execuções
```

A corretora deve conseguir:

- ver auxiliares ativos;
- ativar novos;
- pausar;
- editar configurações simples;
- ver execuções;
- aprovar ações;
- revisar erros;
- conectar fontes necessárias;
- testar antes de ativar.

A corretora não deve precisar:

- editar prompt técnico;
- mexer em JSON;
- entender LangGraph;
- entender MCP;
- configurar provider;
- configurar vector database;
- criar subagent manualmente.

---

# 14. Relação com AutoBrokers central

AutoBrokers central pode interagir com Auxiliares em fases.

## 14.1 Fase inicial

AutoBrokers apenas orienta.

Exemplo:

```txt
Você pode ativar o Auxiliar de Cobrança para organizar esses contatos.
```

Ele pode abrir a página certa ou sugerir ação.

---

## 14.2 Fase intermediária

AutoBrokers pode acionar Auxiliar manualmente.

Exemplo:

```txt
Quer que eu execute o Auxiliar de Renovação agora?
```

O usuário confirma.

---

## 14.3 Fase avançada

AutoBrokers pode delegar automaticamente, respeitando permissões.

Exemplo:

```txt
Identifiquei 12 renovações próximas. Acionei o Auxiliar de Renovação para preparar os rascunhos.
```

Ações externas ainda devem obedecer HITL.

---

# 15. Relação com Atendimento

Auxiliares podem apoiar Atendimentos, mas não substituem o módulo Atendimentos.

Exemplos:

- resumir atendimento;
- identificar pendência;
- preparar resposta;
- criar follow-up;
- avisar atraso;
- montar dossiê;
- pedir documentos;
- revisar conversa.

Mas fluxos complexos de seguradora, assistência e sinistro seguem na camada de Atendimento/Corredores.

Auxiliares podem usar dados de atendimento, com permissão.

---

# 16. Relação com Corredores e Seguradoras

Auxiliares podem reutilizar conexões de seguradoras e sistemas, mas não devem duplicar credenciais.

Exemplo:

Se a corretora já conectou o portal Bradesco para Atendimento, um Auxiliar pode solicitar permissão para usar essa mesma conexão em uma tarefa compatível.

Regra:

```txt
Conexão é da corretora.
Permissão é por uso.
Auxiliar não possui credencial isolada sem governança.
```

Isso depende de ADR-002 Vault.

---

# 17. Relação com Conhecimento

Auxiliares podem usar conhecimento global e conhecimento da corretora.

Tipos:

- conhecimento global AutoBrokers;
- documentos da corretora;
- políticas internas;
- templates;
- base de atendimento;
- histórico;
- apólices;
- arquivos enviados;
- memória da corretora.

Regra:

```txt
Um Auxiliar só deve acessar fontes explicitamente permitidas.
```

---

# 18. Permissões e segurança

Segurança é parte central dos Auxiliares.

## 18.1 Níveis de risco

Cada Auxiliar deve ter um nível de risco.

Sugestão:

```txt
Baixo — apenas lê e resume.
Médio — gera rascunhos ou recomenda ações.
Alto — prepara ações externas.
Crítico — envia mensagens, altera dados ou acessa portal.
```

---

## 18.2 Aprovação humana

No MVP:

```txt
Toda ação externa real deve exigir aprovação humana.
```

Ações externas incluem:

- enviar WhatsApp;
- enviar e-mail;
- alterar CRM;
- acessar portal;
- registrar informação externa;
- acionar seguradora;
- cancelar algo;
- contratar;
- enviar documento;
- criar cobrança real.

---

## 18.3 Logs

Toda execução precisa deixar rastro.

Registrar:

- quem acionou;
- quando acionou;
- qual Auxiliar;
- versão;
- entradas;
- fontes usadas;
- ações propostas;
- ações aprovadas;
- ações executadas;
- custo;
- erro;
- resultado.

---

## 18.4 Kill switch

Todo Auxiliar deve poder ser pausado.

Em caso de erro, o sistema deve permitir:

- pausar Auxiliar;
- pausar por tenant;
- pausar globalmente;
- bloquear conector;
- exigir aprovação manual;
- revisar execuções.

---

# 19. Modelo conceitual de dados

Este documento não fecha schema final.

Mas define entidades conceituais.

## 19.1 Auxiliary Template

Criado no Admin Global.

Campos conceituais:

- id;
- nome;
- descrição;
- categoria;
- objetivo;
- instruções base;
- conectores requeridos;
- permissões padrão;
- nível de risco;
- status;
- versão;
- autor;
- exemplos;
- tags;
- data de publicação.

---

## 19.2 Tenant Auxiliary

Instância ativada por corretora.

Campos conceituais:

- id;
- tenant_id/company_id;
- template_id;
- nome personalizado;
- status;
- configurações;
- conectores vinculados;
- fontes permitidas;
- permissões;
- criado por;
- última execução;
- próxima execução;
- versão ativa.

---

## 19.3 Auxiliary Run

Execução individual.

Campos conceituais:

- id;
- tenant_auxiliary_id;
- status;
- trigger_type;
- input;
- output;
- actions_proposed;
- actions_approved;
- actions_executed;
- cost;
- started_at;
- finished_at;
- error;
- trace_id.

---

## 19.4 Auxiliary Approval

Aprovação humana.

Campos conceituais:

- id;
- run_id;
- action_type;
- summary;
- payload;
- requested_by;
- approved_by;
- status;
- reason;
- created_at;
- decided_at.

---

## 19.5 Auxiliary Schedule

Fase futura.

Campos conceituais:

- id;
- tenant_auxiliary_id;
- frequency;
- time;
- timezone;
- active;
- next_run_at;
- rules.

---

# 20. Compatibilidade com Smith Runtime

O Smith já tem `agents` e `agent_delegations`.

Possibilidades:

## Opção A — Auxiliares como camada de produto sobre agents

Nota estratégica: 92/100

Vantagens:

- aproveita motor existente;
- menor retrabalho;
- mais rápido;
- usa subagents;
- usa tools;
- usa RAG;
- usa billing/logs;
- alinha com Smith.

Riscos:

- pode exigir adaptação de UX;
- pode faltar scheduler;
- pode precisar novas tabelas de produto.

Recomendação:

```txt
Caminho preferencial.
```

---

## Opção B — Criar motor separado de Auxiliares

Nota estratégica: 42/100

Vantagens:

- controle total;
- modelo mais específico.

Riscos:

- duplicação;
- demora;
- bugs;
- desalinhamento com Smith;
- mais manutenção.

Recomendação:

```txt
Não fazer agora.
```

---

## Opção C — Usar apenas prompts manuais sem camada de produto

Nota estratégica: 55/100

Vantagens:

- muito rápido;
- útil para protótipo.

Riscos:

- não vira produto;
- sem governança;
- sem histórico;
- sem permissões;
- sem galeria.

Recomendação:

```txt
Pode ser usado em testes internos, não como arquitetura final.
```

---

# 21. MVP de Auxiliares

O MVP deve ser pequeno e funcional.

## 21.1 Escopo MVP

Inclui:

- Galeria;
- Meus Auxiliares;
- Detalhe do Auxiliar;
- ativação;
- personalização básica;
- permissões simples;
- execução manual;
- histórico básico;
- aprovação humana para ação externa;
- pelo menos 1 Auxiliar funcional real;
- pelo menos 2 Auxiliares demonstráveis.

Não inclui no primeiro corte:

- criação livre por prompt;
- scheduler avançado;
- marketplace público;
- cobrança complexa por Auxiliar;
- execução autônoma externa sem aprovação;
- integrações reais múltiplas;
- portal de seguradora automático;
- criação visual avançada;
- versionamento sofisticado;
- analytics avançado.

---

## 21.2 Auxiliar MVP recomendado

Primeiro Auxiliar funcional:

```txt
Auxiliar de Resumo de Atendimentos
```

Motivo:

- baixo risco;
- não envia nada externo;
- mostra valor rápido;
- usa dados/texto;
- ajuda operação;
- menos dependência de integração.

Segundo candidato:

```txt
Auxiliar de Cobrança com rascunhos aprováveis
```

Motivo:

- valor comercial forte;
- mostra automação;
- ainda pode ser seguro com HITL.

---

# 22. UX do módulo Auxiliares

## 22.1 Página principal

A página principal deve ter:

- título: Auxiliares;
- subtítulo curto;
- tabs ou navegação interna;
- busca;
- cards limpos;
- estado vazio;
- botão para Galeria;
- sem excesso de métricas.

Exemplo de microcopy:

```txt
Ative Auxiliares para automatizar tarefas repetitivas da sua corretora.
```

---

## 22.2 Card de Auxiliar ativo

Deve mostrar:

- nome;
- descrição curta;
- status;
- última execução;
- ação principal;
- indicadores discretos.

Exemplo:

```txt
Auxiliar de Cobrança
Prepara mensagens para clientes com parcelas pendentes.
Status: Ativo
Última execução: hoje às 09:12
[Ver detalhes]
```

---

## 22.3 Card de Galeria

Deve mostrar:

- nome;
- benefício;
- categoria;
- conectores;
- risco;
- botão.

Exemplo:

```txt
Auxiliar de Renovação
Encontre clientes próximos da renovação e prepare contatos.
Categoria: Comercial
Requer: carteira de clientes
[Ver detalhes]
```

---

## 22.4 Página de execução

Detalhe da execução:

- resumo;
- status;
- entrada;
- saída;
- ações propostas;
- aprovações;
- logs amigáveis;
- custo;
- erro, se houver.

Não mostrar JSON bruto para usuário comum.

---

# 23. Linguagem

Usar linguagem simples.

## 23.1 Termos preferidos

- Auxiliar;
- Ativar;
- Pausar;
- Testar;
- Ver detalhes;
- Permissões;
- Conectores;
- Fonte de conhecimento;
- Execução;
- Histórico;
- Aprovação;
- Rascunho;
- Enviar com aprovação.

## 23.2 Termos proibidos ou técnicos demais

Evitar para usuário final:

- subagent;
- delegation;
- MCP;
- runtime;
- LangGraph;
- vector store;
- provider;
- webhook;
- JSON;
- tool execution;
- Celery;
- queue;
- token usage, exceto em Custos.

---

# 24. Estados e mensagens

## 24.1 Sem Auxiliares ativos

```txt
Você ainda não ativou nenhum Auxiliar.
Escolha um modelo pronto na Galeria e coloque o AutoBrokers para trabalhar por você.
```

## 24.2 Precisa configurar

```txt
Este Auxiliar precisa de uma conexão antes de funcionar.
Conecte a fonte necessária para continuar.
```

## 24.3 Aguardando aprovação

```txt
O Auxiliar preparou uma ação e está aguardando sua aprovação.
```

## 24.4 Erro

```txt
Não conseguimos concluir esta execução.
Revise as configurações ou tente novamente.
```

## 24.5 Sucesso

```txt
Execução concluída com sucesso.
```

---

# 25. Mobile-first

Auxiliares precisam funcionar bem no celular.

## 25.1 Padrão mobile

Usar navegação em camadas:

```txt
Auxiliares
→ Galeria
→ Auxiliar
→ Configurar
→ Permissões
→ Teste
```

Cada etapa deve parecer uma página limpa, não um modal gigante.

Usar transição lateral quando possível.

## 25.2 Ações no mobile

Ações principais devem ser grandes:

- Ativar;
- Testar;
- Aprovar;
- Pausar;
- Ver execução;
- Conectar.

## 25.3 Evitar no mobile

- tabelas grandes;
- muitas colunas;
- cards com texto longo;
- filtros complexos;
- modais enormes;
- JSON;
- botões pequenos.

---

# 26. O que Claude Design deve desenhar para Auxiliares

Claude Design deve propor:

1. Página principal de Auxiliares;
2. Meus Auxiliares;
3. Galeria;
4. Card de Auxiliar;
5. Página de detalhe;
6. Fluxo de ativação;
7. Tela de permissões;
8. Tela de conectores requeridos;
9. Tela de teste;
10. Execuções;
11. Detalhe de execução;
12. Estado vazio;
13. Estado de erro;
14. Estado aguardando aprovação;
15. Versão mobile;
16. Transição em camadas;
17. Como Auxiliares aparecem no chat AutoBrokers.

---

# 27. O que Claude Code deve implementar primeiro

Claude Code só deve implementar depois do design aprovado.

Primeiras tarefas boas:

## 27.1 Estrutura visual sem backend novo

- criar rota de Auxiliares;
- criar layout;
- criar Galeria mockada;
- criar Meus Auxiliares mockado;
- criar detalhe mockado;
- sem banco novo;
- sem scheduler;
- sem ações reais.

Objetivo:

```txt
Validar UX antes de runtime.
```

---

## 27.2 Conectar ao motor existente

Depois:

- mapear `agents`;
- mapear `agent_delegations`;
- criar camada adapter de Auxiliares;
- listar Auxiliares ativos;
- listar templates;
- ativar instância;
- rodar execução manual simples.

---

## 27.3 Primeiro Auxiliar real

Implementar:

```txt
Auxiliar de Resumo de Atendimentos
```

Com:

- input manual ou conversa selecionada;
- geração de resumo;
- salvamento de execução;
- custo;
- histórico;
- sem envio externo.

---

# 28. Fora de escopo por enquanto

Não fazer agora:

- scheduler completo;
- criação por prompt;
- marketplace público;
- portal externo automático;
- WhatsApp real automático;
- envio sem aprovação;
- billing por Auxiliar;
- integrações complexas;
- importação bruta de Agent OS;
- ingestão de intake bruto;
- design final do Admin Global;
- migração completa de corredores.

---

# 29. Riscos principais

## 29.1 Criar Auxiliares técnicos demais

Risco:

```txt
O usuário sente que está configurando sistema, não ativando um assistente.
```

Mitigação:

- linguagem simples;
- passos guiados;
- galeria;
- templates;
- permissões claras.

---

## 29.2 Misturar Auxiliares com Agentes de Atendimento

Risco:

```txt
Usuário não entende diferença entre agente que atende cliente e auxiliar que executa tarefa.
```

Mitigação:

- separar módulos;
- separar nomes;
- explicar com microcopy;
- usar ícones e categorias diferentes.

---

## 29.3 Criar autonomia perigosa cedo demais

Risco:

```txt
Auxiliar envia mensagens ou altera dados sem revisão.
```

Mitigação:

- HITL;
- dry run;
- logs;
- permissões;
- aprovação.

---

## 29.4 Duplicar motor do Smith

Risco:

```txt
Criar outro sistema paralelo de agentes.
```

Mitigação:

- usar agents/delegations/tools existentes;
- criar camada de produto;
- não reinventar runtime.

---

## 29.5 Depender de integrações complexas no MVP

Risco:

```txt
MVP trava porque precisa de InfoCap, Quiver, WhatsApp, portais e seguradoras ao mesmo tempo.
```

Mitigação:

- começar com Auxiliar que usa texto/dados simples;
- execução manual;
- sem envio externo;
- evoluir por fases.

---

# 30. Critérios de sucesso

O módulo Auxiliares estará no caminho certo quando:

- o usuário entender em 10 segundos o que é;
- a Galeria parecer útil;
- ativar um Auxiliar parecer simples;
- permissões forem claras;
- execução for rastreável;
- o sistema não parecer técnico;
- o AutoBrokers puder sugerir Auxiliares;
- o primeiro Auxiliar funcionar de verdade;
- ações externas exigirem aprovação;
- Claude Code conseguir implementar sem inventar arquitetura.

---

# 31. Relação com documentos canônicos

Este documento depende de:

```txt
docs/canon/PRD-001-visao-produto.md
docs/canon/ADR-001-runtime.md
docs/canon/UX-001-navegacao.md
docs/canon/DS-001-design-brief.md
docs/canon/ADR-002-vault.md
```

E influencia:

```txt
docs/canon/ROADMAP-001-execucao.md
docs/canon/ADR-003-atendimento.md
```

---

# 32. Direção final

Auxiliares são uma das maiores oportunidades estratégicas do AutoBrokers.ai.

Eles transformam o produto de “chat inteligente” em “força de trabalho de IA para corretoras”.

Mas o caminho correto é progressivo:

```txt
Galeria simples
→ Ativação segura
→ Execução manual
→ Histórico
→ Permissões
→ HITL
→ Conectores
→ Scheduler
→ Criação por prompt
→ Delegação pelo AutoBrokers
```

A primeira versão deve ser simples, confiável e útil.

O objetivo não é impressionar com complexidade.

O objetivo é fazer o corretor pensar:

```txt
“Eu ativei um Auxiliar e ele realmente tirou trabalho da minha mão.”
```
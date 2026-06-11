---
# ROADMAP-001 — Plano de Execução do AutoBrokers Intelligence OS

> **Decisão canônica: Auxiliares usam Smith Agents/Subagents como runtime** (ver [SPEC-002](SPEC-002-auxiliares-runtime-smith.md)). Produto AutoBrokers por cima, runtime Smith por baixo, Vault governando. Não criar motor paralelo de execução.

Status: canonical  
Produto: AutoBrokers.ai  
Sistema: AutoBrokers Intelligence OS  
Tipo: Roadmap operacional / plano de execução  
Última atualização: 2026-06-06  
Responsável estratégico: Architect / CEO AutoBrokers.ai  
Audiência: Founder, Claude Strategy, Claude Design, Claude Code, Codex, devs, UX, LLMs futuras e time fundador

---

# 1. Decisão central

O AutoBrokers.ai será construído de forma progressiva, disciplinada e documentada, sem migração cega de legado, sem criação improvisada de telas e sem permitir que ferramentas executoras tomem decisões estratégicas.

A ordem oficial é:

```txt
1. Documentação canônica
2. UX Architecture / Claude Design
3. Implementação controlada no runtime Smith
4. Validação em sandbox
5. Expansão por módulos
6. Atendimento real e corredores apenas depois da base estar estável
```

O produto não será construído “remendando” o Smith.

O produto será:

```txt
AutoBrokers.ai como camada de produto
+ Smith como runtime técnico
+ ResultVision / Agent OS como fonte de domínio curada
+ Claude Design como direção visual
+ Claude Code/Codex como execução controlada
```

---

# 2. O que este roadmap resolve

Este documento existe para impedir confusão entre:

- estratégia;
- design;
- execução;
- runtime;
- legado;
- docs antigas;
- produto final;
- sandbox;
- referências;
- código real;
- materiais brutos;
- decisões provisórias.

Ele define:

- sequência de trabalho;
- o que vem primeiro;
- o que fica para depois;
- quais batches devem ser executados;
- qual agente/ferramenta faz cada coisa;
- quais gates precisam passar antes de avançar;
- o que não pode ser feito;
- quando entra Claude Design;
- quando entra Claude Code;
- quando entra Codex;
- quando entra RAG;
- quando entram Auxiliares;
- quando entra Atendimento;
- quando entram corredores;
- quando entram integrações reais.

---

# 3. Estado atual do projeto

O AutoBrokers Intelligence OS já possui:

- repo oficial ativo;
- Smith instalado como base técnica;
- EasyPanel rodando sandbox;
- Web Next.js rodando;
- API FastAPI rodando;
- Supabase sandbox com schema;
- Redis;
- Qdrant;
- MinIO;
- Admin acessível;
- tenant login funcionando;
- chat tenant funcionando;
- agente sandbox respondendo;
- docs canônicos em criação;
- runtime técnico forte;
- ResultVision como referência antiga;
- Agent OS como fonte de domínio;
- intake bruto como fonte real, mas sensível.

Ainda não possui:

- UX final aprovada;
- design system final;
- sidebar final;
- módulos tenant redesenhados;
- Auxiliares como produto;
- Vault operacional final;
- RAG validado com curadoria;
- Atendimento reconstruído no novo runtime;
- corredores portados;
- integrações reais seguras;
- automação WhatsApp real;
- InfoCap/Quiver integrados;
- worker/docling final em produção;
- cleanup completo de resíduos Smith;
- governança final de dados sensíveis.

---

# 4. Princípio de execução

Toda execução deve seguir esta lógica:

```txt
Pensar → documentar → desenhar → implementar → testar → validar → expandir
```

Nunca:

```txt
implementar → ver se ficou bom → remendar → redesenhar → reimplementar
```

O erro anterior foi permitir que o executor criasse uma Home visual sem direção suficiente. Isso não deve se repetir.

---

# 5. Papéis das ferramentas e agentes

## 5.1 Architect / ChatGPT estratégico

Responsável por:

- visão de produto;
- decisões estratégicas;
- PRDs;
- ADRs;
- roadmap;
- prompts de execução;
- interpretação do fundador;
- alinhamento entre docs;
- supervisão do Claude Design;
- supervisão do Claude Code;
- supervisão do Codex;
- revisão de decisões;
- proteção contra execução errada.

Não deve:

- criar layout final sozinho sem Claude Design;
- mandar executor improvisar UX;
- permitir batch aberto demais.

---

## 5.2 Claude Strategy / Claude normal

Responsável por:

- revisar documentos canônicos;
- fazer perguntas estratégicas;
- desafiar premissas;
- ajudar a consolidar UX;
- ajudar a transformar visão em plano;
- contribuir com PRD/UX/ADR;
- preparar contexto para Claude Design.

Não deve:

- executar código;
- decidir sozinho contra decisões do fundador;
- inventar módulos fora do escopo.

---

## 5.3 Claude Design

Responsável por:

- traduzir docs canônicos em experiência visual;
- criar arquitetura de telas;
- propor design system;
- definir hierarquia visual;
- definir componentes;
- desenhar fluxos mobile-first;
- desenhar navegação em camadas;
- desenhar páginas de Auxiliares;
- desenhar páginas de Conectores;
- desenhar Atendimento;
- desenhar Personalização;
- criar especificações para Claude Code implementar.

Claude Design não deve decidir sozinho:

- estratégia de negócio;
- escopo MVP;
- arquitetura runtime;
- modelo de dados;
- integrações reais;
- regras de segurança;
- o que entra ou sai do produto.

---

## 5.4 Claude Code

Responsável por:

- ler repo;
- editar arquivos;
- implementar tarefas fechadas;
- rodar typecheck/build/testes;
- criar commits;
- aplicar specs de UX;
- refatorar componentes;
- corrigir bugs;
- integrar backend/frontend conforme instrução.

Claude Code deve receber tarefas pequenas, com:

- objetivo;
- arquivos permitidos;
- arquivos proibidos;
- fora de escopo;
- critérios de pronto;
- validações obrigatórias;
- mensagem de commit sugerida.

Claude Code não deve receber estratégia aberta.

---

## 5.5 Codex

Responsável por:

- auditorias;
- inventários;
- patches mecânicos;
- correções pequenas;
- validações;
- git hygiene;
- relatórios;
- tarefas técnicas controladas.

Codex não deve:

- definir UX final;
- criar telas grandes;
- redesenhar produto;
- escrever documentos estratégicos finais;
- migrar legado automaticamente;
- decidir arquitetura de produto.

---

# 6. Regra de ouro para documentos

Docs canônicos ficam em:

```txt
docs/canon/
```

Docs antigos ficam em:

```txt
docs/_archive/
```

Docs canônicos são a fonte de verdade.

Docs históricos são referência, não decisão atual.

Se houver conflito:

```txt
Decisão recente do fundador + docs/canon vencem.
```

---

# 7. Documentos canônicos obrigatórios

A base mínima canônica é:

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

Esses documentos devem ser lidos por qualquer novo chat antes de mexer no projeto.

---

# 8. Estado dos documentos

## 8.1 PRD-001

Define:

- produto;
- público;
- momento mágico;
- escopo;
- não escopo;
- tipos de agente;
- módulos principais.

---

## 8.2 ADR-001

Define:

- runtime Smith;
- AutoBrokers como produto;
- ResultVision como domínio;
- Agent OS como fonte curada;
- o que entra e o que não entra no runtime.

---

## 8.3 UX-001

Define:

- navegação;
- sidebar;
- chat-first;
- módulos;
- separação operação/configuração;
- mobile-first;
- hierarquia de páginas.

---

## 8.4 DS-001

Não é design system final.

É brief para Claude Design.

Define:

- direção visual;
- referências;
- restrições;
- princípios;
- padrões desejados.

---

## 8.5 UX-007

Define:

- Auxiliares;
- galeria;
- meus auxiliares;
- execuções;
- permissões;
- criação futura;
- relação com agents/subagents do Smith.

---

## 8.6 ADR-002

Define:

- Vault;
- conexões;
- credenciais;
- permissões;
- reuso entre Atendimento, Auxiliares e AutoBrokers;
- proteção de PII;
- regra de não ingerir intake bruto.

---

## 8.7 ADR-003

Define:

- Atendimento;
- corredores;
- subcorredores;
- fases do atendimento;
- relação com ResultVision;
- relação com Agent OS;
- relação com Smith;
- MVP de atendimento assistido.

---

## 8.8 ROADMAP-001

Este documento.

Define a sequência de execução.

---

# 9. Ordem macro do projeto

A sequência oficial é:

```txt
Fase 0 — Estabilizar base e limpar confusão
Fase 1 — Consolidar docs canônicos
Fase 2 — Claude Design / UX Architecture
Fase 3 — Implementar shell visual chat-first
Fase 4 — Personalização e Conectores base
Fase 5 — Auxiliares MVP
Fase 6 — Conhecimento/RAG curado
Fase 7 — Atendimento base
Fase 8 — Primeiro corredor assistido
Fase 9 — Integrações reais controladas
Fase 10 — Hardening, observabilidade e venda piloto
```

---

# 10. Fase 0 — Estabilizar base e limpar confusão

## Objetivo

Garantir que o repo oficial esteja limpo, que o produto não esteja herdando sujeira visual ou documental, e que novos chats saibam exatamente onde trabalhar.

## Já feito parcialmente

- Smith instalado;
- sandbox rodando;
- chat respondendo;
- `/dashboard` resetado para chat-first;
- docs antigos arquivados;
- docs canônicos iniciados;
- workspace boundary criado.

## Ainda fazer

- revisar README final;
- limpar branding residual visível;
- decidir sobre `SmithWidget`;
- trocar `agentsmith.ai`;
- tratar `smith-logo.png`;
- manter migrations históricas sem alterar;
- não mexer em license sem decisão jurídica;
- não limpar classes internas técnicas sem necessidade.

## Não fazer

- não reescrever UI grande;
- não migrar ResultVision;
- não ingerir intake;
- não criar corredores;
- não criar Auxiliares completos;
- não ativar WhatsApp real.

## Gate de saída

A fase 0 termina quando:

- repo oficial está limpo;
- README principal não confunde com Agent Smith como produto;
- docs canônicos existem;
- `/dashboard` é chat-first;
- não há Home ruim ativa;
- nenhum novo chat confunde ResultVision com runtime oficial.

---

# 11. Fase 1 — Consolidar docs canônicos

## Objetivo

Substituir documentação fraca/simplificada por documentos completos, estratégicos e claros para qualquer LLM entender o projeto.

## Entregáveis

- PRD-001 revisado;
- ADR-001 revisado;
- UX-001 revisado;
- DS-001 revisado;
- UX-007 revisado;
- ADR-002 revisado;
- ADR-003 revisado;
- ROADMAP-001 revisado.

## Responsável

Architect / ChatGPT estratégico.

## Apoio

Claude Strategy pode revisar depois.

Codex não deve escrever esses documentos finais.

## Não fazer

- não pedir ao Codex para simplificar docs;
- não deixar Claude Code editar docs estratégicos sem revisão;
- não aceitar docs curtos demais;
- não arquivar docs canônicos.

## Gate de saída

A fase 1 termina quando:

- todos os docs canônicos estão em `docs/canon`;
- documentos antigos conflitantes estão arquivados;
- Claude Strategy consegue ler e entender o projeto sem depender do histórico do chat;
- Claude Design tem material suficiente para começar.

---

# 12. Fase 2 — Claude Design / UX Architecture

## Objetivo

Transformar a direção de produto em uma arquitetura visual de alto nível, antes de qualquer nova implementação grande.

## Entrada

Claude Design deve receber:

- docs/canon completos;
- prints do ChatGPT;
- prints do Claude;
- prints do Claude Routines;
- prints do AutoBrokers antigo;
- prints do sandbox atual;
- explicação das diferenças entre ResultVision e novo runtime;
- instrução de que Home = chat-first;
- instrução de que visual deve ser clean, premium, mobile-first;
- instrução de que não deve criar dashboard denso.

## Saída esperada

Claude Design deve entregar:

- proposta de sidebar tenant;
- proposta de sidebar admin;
- sitemap;
- navegação em camadas;
- fluxo mobile;
- tela principal do AutoBrokers;
- tela de Auxiliares;
- tela de Galeria de Auxiliares;
- tela de execução de Auxiliar;
- tela de Conectores;
- tela de detalhe de conector;
- tela de Personalização;
- tela de Atendimento;
- padrão de cards;
- padrão de página detalhe;
- padrão de modal de permissão;
- tokens visuais;
- hierarquia tipográfica;
- comportamento mobile;
- critérios de implementação para Claude Code.

## Regra visual

O produto deve ter inspiração em:

- ChatGPT;
- Claude;
- Claude Routines;
- galeria de Apps/Connectors;
- páginas limpas em camadas;
- pouca cor;
- dark default;
- sofisticação;
- foco;
- baixa densidade visual.

## Não fazer

Claude Design não deve:

- criar telas densas estilo dashboard antigo;
- colocar tudo em uma página;
- criar sidebar inchada;
- inventar features sem PRD;
- usar termos técnicos para usuário final;
- mudar arquitetura runtime;
- decidir integrações reais.

## Gate de saída

A fase 2 termina quando temos:

- UX aprovada pelo fundador;
- sidebar aprovada;
- Home chat-first aprovada;
- estrutura de Auxiliares aprovada;
- estrutura de Conectores aprovada;
- padrões visuais aprovados;
- specs suficientes para Claude Code implementar.

---

# 13. Fase 3 — Shell visual chat-first

## Objetivo

Implementar a primeira camada visual correta do tenant dashboard.

## Escopo

- `/dashboard` como chat principal;
- layout inspirado em ChatGPT/Claude;
- frase central simples;
- caixa de input limpa;
- dois atalhos:
  - Ver atendimentos;
  - Novo auxiliar.
- sidebar limpa;
- mobile-first;
- sem cards grandes;
- sem dashboard tradicional;
- sem status poluído.

## Fora de escopo

- Auxiliares completos;
- Atendimento completo;
- RAG avançado;
- corredores;
- integrações reais;
- dashboards de métricas;
- relatórios;
- gráficos.

## Responsável

Claude Code, com spec do Claude Design.

Codex só revisa se necessário.

## Gate de saída

- `/dashboard` visualmente aprovado;
- `/dashboard/chat` continua funcionando;
- conversa responde;
- mobile não quebra;
- typecheck/build passam;
- não aparecem Smith/JARVYS na UI;
- atalhos não levam a rotas mortas.

---

# 14. Fase 4 — Personalização e Conectores base

## Objetivo

Criar a lógica visual e conceitual para a corretora configurar o que usará no sistema.

## Por que vem antes de Atendimento real

Atendimento, Auxiliares e AutoBrokers dependem de conexões reutilizáveis.

Exemplo:

```txt
Portal Bradesco conectado uma vez
→ usado por Atendimento
→ usado por Auxiliar
→ usado pelo AutoBrokers
```

## Módulos envolvidos

- Personalização;
- Conectores;
- Canais;
- Seguradoras;
- Ferramentas externas;
- Vault;
- permissões.

## UX esperada

Inspirada em ChatGPT Apps/Connectors:

```txt
Galeria
→ detalhe
→ conectar
→ permissões
→ status
→ gerenciar
```

## Categorias possíveis

- Seguradoras;
- Sistemas de gestão;
- WhatsApp;
- Telefonia;
- Google Workspace;
- Drive;
- Calendar;
- Slack;
- Notion;
- e-mail;
- APIs;
- MCPs;
- portais;
- documentos;
- ferramentas internas.

## MVP visual

No começo pode ser apenas visual/estrutural, sem conexão real.

O importante é definir padrão.

## Gate de saída

- Conectores têm página limpa;
- detalhe de conector existe;
- status conectado/desconectado existe;
- permissão é compreensível;
- não expõe credenciais;
- não mistura tudo com Atendimento.

---

# 15. Fase 5 — Auxiliares MVP

## Objetivo

Criar o módulo de Auxiliares como produto.

Auxiliares são uma das maiores oportunidades de diferenciação.

## Escopo MVP recomendado

Começar com:

- Galeria de Auxiliares;
- Meus Auxiliares;
- Detalhe do Auxiliar;
- Ativar/desativar;
- Personalizar básico;
- Execução manual;
- Histórico simples;
- permissões visuais;
- sem scheduler complexo no início;
- sem criação livre por prompt no início.

## Inspiração

Claude Routines.

Mas o nome do produto é:

```txt
Auxiliares
```

Não “rotinas”.

## Exemplos iniciais

- Auxiliar de Cobrança;
- Auxiliar de Renovação;
- Auxiliar de Follow-up;
- Auxiliar de Resumo Diário;
- Auxiliar de Conferência de Documentos;
- Auxiliar de Análise de Atendimento;
- Auxiliar de Reputação Google;
- Auxiliar de Reativação de Clientes.

## Relação com Smith

Usar como base:

- agents;
- subagents;
- delegations;
- tools;
- MCP;
- HTTP tools;
- memory;
- documents;
- logs.

Mas criar camada de produto própria:

```txt
Auxiliar ≠ agent técnico cru.
```

## Gate de saída

- usuário entende o que é um Auxiliar;
- consegue ativar um Auxiliar;
- consegue ver o que ele faz;
- consegue executar manualmente;
- vê histórico;
- ações reais continuam protegidas;
- UX é limpa.

---

# 16. Fase 6 — Conhecimento/RAG curado

## Objetivo

Validar base de conhecimento e RAG sem ingerir dados sensíveis brutos.

## Escopo

- upload de documento simples;
- indexação;
- pergunta e resposta;
- documentos por corretora;
- conhecimento global;
- conhecimento da corretora;
- separação de permissões;
- teste de fonte.

## Não usar ainda

- conversas reais do intake;
- PDFs com PII;
- credenciais;
- dumps;
- planilhas sensíveis;
- WhatsApp bruto;
- imagens reais sem redaction.

## Gate de saída

- RAG responde documento simples;
- fontes são exibidas ou rastreáveis;
- não há vazamento cross-tenant;
- documentos ficam isolados por corretora;
- Admin entende conhecimento global vs tenant.

---

# 17. Fase 7 — Atendimento base

## Objetivo

Criar módulo operacional de Atendimento sem ainda portar todos os corredores.

## Escopo inicial

- lista de atendimentos;
- fila;
- caso;
- conversa;
- status;
- resumo;
- responsável;
- prioridade;
- handoff;
- histórico;
- mídia associada;
- ação bloqueada/aprovada.

## Não fazer

- não migrar todos os corredores;
- não acionar seguradora real;
- não conectar InfoCap real;
- não ativar WhatsApp real irrestrito;
- não automatizar portal.

## Gate de saída

- Atendimento tem UX limpa;
- caso pode ser aberto;
- conversa pode ser visualizada;
- status pode ser entendido;
- humano sabe o que fazer;
- mobile funciona;
- sem dashboard denso.

---

# 18. Fase 8 — Primeiro corredor assistido

## Objetivo

Implementar um fluxo realista, pequeno e controlado de corredor.

## Candidato recomendado

```txt
Allianz
Assistência Residencial
WhatsApp
Eletricista ou Encanador
```

## Modo

```txt
Assistido / dry-run / no-send / HITL
```

## Escopo

- dados mínimos;
- perguntas;
- dispatch packet;
- mensagem sugerida;
- aprovação humana;
- captura manual/simulada de retorno;
- protocolo;
- prestador;
- previsão;
- mensagem ao cliente;
- logs;
- golden tests.

## Não fazer

- não liberar envio real automático;
- não implementar todos os subcorredores;
- não usar intake bruto sem curadoria;
- não prometer cobertura;
- não fingir protocolo;
- não chamar portal real sem permissão.

## Gate de saída

- fluxo completo em sandbox;
- golden tests passam;
- humano aprova antes de ação externa;
- logs registram tudo;
- cliente não recebe promessa indevida.

---

# 19. Fase 9 — Integrações reais controladas

## Objetivo

Ativar integrações reais apenas quando base, UX, Vault e logs estiverem prontos.

## Integrações candidatas

- Evolution API;
- WhatsApp;
- InfoCap;
- Quiver;
- Segfy;
- Capta;
- portais de seguradoras;
- Google Drive;
- Calendar;
- e-mail;
- SendGrid;
- Stripe;
- Sentry;
- LangSmith;
- Cohere;
- Tavily;
- Docling;
- worker/Celery.

## Ordem recomendada

```txt
1. Evolution/WhatsApp sandbox
2. RAG documentos simples
3. Docling
4. SendGrid
5. Sentry/LangSmith
6. InfoCap leitura
7. portal assistido
8. Stripe/billing real
```

## Gate de saída

- cada integração tem Vault;
- cada integração tem permissão;
- cada integração tem logs;
- cada integração tem fallback;
- cada integração pode ser desligada;
- nenhuma credencial fica exposta.

---

# 20. Fase 10 — Hardening e piloto

## Objetivo

Preparar para piloto real com corretora.

## Escopo

- logs;
- Sentry;
- LangSmith;
- billing;
- custos;
- auditoria;
- permissões;
- RLS;
- LGPD;
- onboarding;
- termos;
- backups;
- runbooks;
- evals;
- golden tests;
- monitoramento;
- plano de rollback.

## Gate de saída

- piloto com uma corretora;
- escopo limitado;
- ações externas controladas;
- métricas observadas;
- custos monitorados;
- feedback coletado;
- bugs priorizados.

---

# 21. Sequência de batches recomendada

## 21.1 Batches documentais

```txt
36A — Canon docs sync and legacy archive
36B — Canon docs rewrite by Architect
36C — Claude Strategy review of canon docs
36D — Canon docs final patch after Claude review
```

---

## 21.2 Batches de cleanup

```txt
37A — README and visible branding cleanup
37B — Widget/embed branding audit
37C — Asset naming cleanup
37D — Smith technical residues classification
```

---

## 21.3 Batches de design

```txt
38A — Claude Design project brief
38B — Tenant navigation and chat-first UX
38C — Auxiliares UX
38D — Connectors/Personalização UX
38E — Atendimento UX
38F — Mobile interaction rules
38G — Design handoff for implementation
```

---

## 21.4 Batches de implementação UI

```txt
39A — Chat-first tenant shell
39B — Sidebar and navigation shell
39C — Empty state and shortcuts
39D — Mobile shell
39E — Configurações cleanup
```

---

## 21.5 Batches de Auxiliares

```txt
40A — Auxiliares data/product inventory
40B — Auxiliares gallery UI
40C — Auxiliar detail UI
40D — Activate/customize auxiliary
40E — Manual execution
40F — Run history
40G — Permission approval shell
```

---

## 21.6 Batches de Vault/Conectores

```txt
41A — Vault schema audit
41B — Connector catalog UI
41C — Connector detail UI
41D — Permission modal
41E — Tenant connection status
41F — No-secret validation
```

---

## 21.7 Batches de RAG

```txt
42A — RAG minimal smoke
42B — Document upload tenant
42C — Global vs tenant knowledge
42D — Source trace
42E — Redaction/sanitization policy
42F — Docling sandbox
```

---

## 21.8 Batches de Atendimento

```txt
43A — Atendimento domain model audit
43B — Atendimento UX implementation
43C — Case/conversation shell
43D — Status and handoff
43E — Media attachment display
43F — Agent of attendance sandbox
```

---

## 21.9 Batches de Corredores

```txt
44A — Allianz residential source inventory
44B — Allianz electrician package
44C — Golden tests
44D — Dispatch packet
44E — Approval/no-send flow
44F — Simulated insurer return
44G — Customer response templates
```

---

## 21.10 Batches de integrações

```txt
45A — WhatsApp provider abstraction
45B — Evolution sandbox receive
45C — Evolution sandbox send no-send
45D — InfoCap read-only audit
45E — Portal automation feasibility
45F — Worker/Celery enablement
```

---

# 22. Prioridade real dos próximos passos

A prioridade imediata não é RAG, nem corredores, nem integração.

A prioridade imediata é:

```txt
1. Terminar docs canônicos bons.
2. Pedir Claude Strategy para revisar.
3. Pedir Claude Design para propor UX.
4. Só depois implementar UI.
```

---

# 23. Próxima ação após este documento

Depois que este ROADMAP for substituído, o próximo passo recomendado é:

```txt
Criar um prompt para Claude Strategy revisar todos os documentos canônicos.
```

Objetivo do Claude Strategy:

- ler `docs/canon`;
- identificar contradições;
- propor ajustes;
- validar ordem de execução;
- perguntar o que faltar;
- não criar código;
- não criar design final ainda.

Depois da revisão estratégica:

```txt
Claude Design recebe docs corrigidos e começa UX Architecture.
```

---

# 24. O que não deve ser feito agora

Não fazer agora:

- implementar nova Home visual;
- desenhar sidebar definitiva via Codex;
- criar dashboards densos;
- ativar WhatsApp real;
- portar corredores;
- ingerir intake;
- criar RAG com dados reais;
- criar worker/docling completo;
- mexer em Stripe real;
- conectar InfoCap real;
- criar todos os Auxiliares;
- limpar tudo de Smith internamente sem análise;
- mexer em migrations históricas;
- alterar licença sem decisão jurídica;
- copiar ResultVision para o repo novo.

---

# 25. Política de execução de batches

Todo batch deve conter:

```txt
Nome do batch
Objetivo
Contexto
Arquivos permitidos
Arquivos proibidos
Fora de escopo
Passos
Checks obrigatórios
Critérios de pronto
Relatório esperado
```

Todo batch deve terminar com:

- commit hash, se houver alteração;
- arquivos alterados;
- checks;
- riscos restantes;
- próximo passo recomendado;
- confirmação de que não imprimiu secrets.

---

# 26. Política de Git

Regra:

```txt
Nunca usar git add .
```

Preferir:

```txt
git add arquivo1 arquivo2 arquivo3
```

Sempre verificar:

```txt
git status --short
git diff --check
npm run typecheck
npm run build quando aplicável
```

Nunca commitar:

- `.env`;
- credenciais;
- dumps;
- intake bruto;
- prints sensíveis;
- conversas reais;
- pastas de quarentena;
- worktrees;
- node_modules;
- caches;
- documentos locais antigos.

---

# 27. Política de dados sensíveis

Antes de qualquer uso de dados reais:

- classificar;
- redigir;
- anonimizar;
- separar por tenant;
- remover credenciais;
- remover dados pessoais desnecessários;
- criar política de uso;
- criar logs;
- impedir RAG bruto.

Nada do intake entra direto.

---

# 28. Política de design

Nenhuma grande tela nova deve ser criada sem:

- UX-001;
- DS-001;
- output do Claude Design;
- aprovação do fundador;
- spec de implementação.

Codex não deve criar layout.

Claude Code implementa layout aprovado.

---

# 29. Política de runtime

Smith é runtime técnico.

Não substituir sem decisão formal.

Não criar runtime paralelo sem ADR.

Não reativar Reasoner antigo como núcleo sem decisão.

Não portar TypeScript antigo para Python sem plano.

---

# 30. Política de Atendimento

Atendimento deve ser implementado depois de:

- UX;
- Vault;
- casos/conversas;
- logs;
- permissões;
- golden tests;
- um fluxo escolhido.

Não começar por corredores.

---

# 31. Política de Auxiliares

Auxiliares devem começar simples:

```txt
Galeria
→ ativação
→ personalização básica
→ execução manual
→ histórico
```

Depois:

```txt
scheduler
gatilhos
criação por prompt
delegação automática
ações reais
```

---

# 32. Política de Conectores

Conectores devem ser reutilizáveis.

Um conector não pertence só ao Atendimento ou só ao Auxiliar.

Ele pertence ao tenant.

Pode ser usado por:

- AutoBrokers;
- Atendimento;
- Auxiliares;
- Conhecimento;
- relatórios;
- integrações.

---

# 33. Política de Home

A Home do tenant é o chat.

Não existe dashboard de cards como primeira tela.

A tela inicial deve ter:

- AutoBrokers no centro;
- frase simples;
- input;
- dois atalhos;
- sidebar;
- histórico de conversas se fizer sentido;
- visual limpo.

Atalhos:

```txt
Ver atendimentos
Novo auxiliar
```

---

# 34. Política de sidebar

A sidebar deve ser enxuta.

Pilares iniciais:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

Itens como Conhecimento, Conectores, Seguradoras, Equipe e Custos podem ficar dentro de Personalização ou em subnavegação até a UX final decidir.

Não criar sidebar com 30 itens.

---

# 35. Política de Admin Global

Admin Global é interno.

Somente equipe AutoBrokers acessa.

Pode manter mais densidade que tenant, mas ainda deve evoluir para branding AutoBrokers.

Funções do Admin:

- corretoras;
- usuários;
- planos;
- créditos;
- custos;
- agentes;
- documentos;
- templates globais;
- Auxiliares globais;
- conectores globais;
- logs;
- auditoria;
- governança.

---

# 36. Roadmap visual resumido

```txt
Agora:
docs → Claude Strategy → Claude Design

Depois:
chat shell → sidebar → Auxiliares shell → Personalização/Conectores shell

Depois:
RAG simples → Conhecimento → Vault

Depois:
Atendimento base → caso/conversa → agente atendimento

Depois:
um corredor assistido → golden tests → integrações reais controladas
```

---

# 37. Critério de sucesso do MVP inicial

O MVP inicial estará no caminho certo quando um usuário da corretora conseguir:

```txt
1. Entrar no sistema.
2. Falar com o AutoBrokers.
3. Entender que o chat é o centro do produto.
4. Abrir Atendimentos.
5. Abrir Auxiliares.
6. Ver uma Galeria de Auxiliares.
7. Ativar ou executar algo simples.
8. Entender onde configura conectores/personalização.
9. Usar conhecimento básico sem vazamento.
10. Não ver Smith/JARVYS como produto.
```

---

# 38. Critério de sucesso do produto vendável

O produto começa a ficar vendável quando:

- UX parece premium;
- chat é útil;
- Auxiliares geram valor real;
- Atendimento tem fluxo claro;
- dados ficam protegidos;
- corretora entende setup;
- suporte humano consegue operar;
- custos são monitorados;
- integrações não quebram;
- um fluxo real assistido funciona;
- founder consegue demonstrar sem pedir desculpas pela interface.

---

# 39. Decisão final

O AutoBrokers.ai deve ser construído em ordem.

A ordem é mais importante do que velocidade aparente.

O projeto já perdeu tempo quando executores fizeram telas e docs fracos sem direção suficiente.

A partir deste roadmap:

```txt
Nenhuma nova grande UI sem Claude Design.
Nenhuma nova grande feature sem documento canônico.
Nenhum uso de legado sem curadoria.
Nenhum dado bruto no runtime.
Nenhuma ação externa real sem Vault/HITL/logs.
Nenhuma decisão estratégica delegada ao executor.
```

O caminho correto é:

```txt
Documentação forte.
Design forte.
Execução pequena.
Validação rápida.
Expansão progressiva.
```

Esse é o roadmap oficial para transformar o Smith em AutoBrokers.ai sem destruir o que já funciona e sem carregar a bagunça antiga para dentro do produto novo.
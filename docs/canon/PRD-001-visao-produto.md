---
# PRD-001 — Visão de Produto

Status: canonical  
Produto: AutoBrokers.ai  
Sistema: AutoBrokers Intelligence OS  
Documento: PRD principal de visão, produto e escopo  
Última atualização: 2026-06-06  
Responsável estratégico: Architect / CEO AutoBrokers.ai  
Audiência: LLMs estratégicas, Claude Design, Claude Code, Codex, time fundador e futuros devs

---

# 1. Objetivo deste documento

Este documento define a visão canônica do produto AutoBrokers.ai.

Ele existe para impedir que qualquer LLM, dev, agente de código ou ferramenta de design interprete o projeto como apenas:

- um clone do Smith;
- uma continuação bruta do ResultVision;
- um dashboard tradicional de atendimento;
- um CRM de corretora com IA acoplada;
- um conjunto solto de prompts;
- um repositório de documentos antigos;
- uma automação isolada de WhatsApp.

AutoBrokers.ai é um SaaS multi-tenant para corretoras de seguros, construído sobre um runtime agentic robusto, com uma experiência central chat-first e módulos operacionais ao redor.

A regra principal é:

```txt
AutoBrokers.ai = Product Layer + Smith Runtime Engine + AutoBrokers Domain Brain
````

O produto final não é “Smith renomeado”.

O produto final também não é “ResultVision copiado para dentro do Smith”.

O produto final é uma nova plataforma, com identidade própria, usando:

* o Smith como motor técnico invisível;
* o ResultVision como referência de domínio e atendimento;
* o Agent OS / AutoBrokers Intelligence OS V2 como cérebro arquitetural e fonte de curadoria;
* o intake bruto como fonte futura de conhecimento, nunca como runtime bruto;
* Claude Design e Claude Code como executores futuros, guiados por documentação canônica.

---

# 2. Definição curta do produto

AutoBrokers.ai é um sistema operacional de inteligência artificial para corretoras de seguros.

Ele dá a cada corretora um agente central chamado AutoBrokers, capaz de conversar com o time da corretora, consultar conhecimento, entender a operação, acionar módulos, apoiar atendimentos, orquestrar Auxiliares e, progressivamente, executar tarefas com segurança, permissões e rastreabilidade.

A experiência principal deve parecer mais próxima de um ChatGPT/Claude especializado em seguros do que de um dashboard cheio de cards.

O corretor entra no sistema e conversa com o AutoBrokers.

Ao redor desse chat existem módulos específicos:

* Atendimento;
* Auxiliares;
* Conhecimento;
* Conectores e Canais;
* Personalização / Configurações;
* Admin Global.

---

# 3. Visão de longo prazo

A visão de longo prazo é transformar o AutoBrokers.ai na camada de inteligência operacional das corretoras de seguros.

A plataforma deve permitir que uma corretora:

1. centralize conhecimento operacional;
2. conecte sistemas, seguradoras, portais, WhatsApp, documentos e bases internas;
3. automatize tarefas repetitivas;
4. melhore o atendimento ao cliente final;
5. reduza dependência de processos manuais;
6. organize regras, corredores, canais, agentes e Auxiliares;
7. monitore custos, execuções, riscos e qualidade;
8. tenha uma IA interna capaz de orientar, executar, auditar e melhorar a operação ao longo do tempo.

O AutoBrokers não deve ser apenas um chatbot.

Ele deve ser a interface principal entre a corretora e sua inteligência operacional.

---

# 4. Problema central

Corretoras de seguros trabalham em um ambiente fragmentado.

A operação normalmente envolve:

* WhatsApp com clientes;
* WhatsApp com seguradoras;
* portais de seguradoras;
* sistemas de gestão como Infocap, Quiver, Segfy e outros;
* e-mails;
* PDFs de apólices;
* documentos enviados por clientes;
* fotos de sinistros;
* áudios;
* planilhas;
* regras de cobertura;
* regras de comissão;
* protocolos;
* prazos;
* filas internas;
* atendimento humano;
* follow-ups manuais;
* conhecimento espalhado na cabeça de pessoas experientes.

O problema não é apenas “responder cliente”.

O problema é coordenar a inteligência operacional inteira da corretora.

A corretora precisa saber:

* quem é o cliente;
* qual apólice está envolvida;
* qual seguradora;
* qual canal correto;
* qual fluxo seguir;
* quais dados coletar;
* o que pode ou não prometer;
* quando chamar humano;
* onde buscar informação;
* como registrar histórico;
* como acompanhar protocolo;
* quando cobrar retorno;
* como reduzir retrabalho;
* como automatizar tarefas repetidas com segurança.

AutoBrokers.ai resolve esse problema organizando a operação em um sistema agentic controlado, onde o chat central é a porta de entrada e os módulos especializados executam partes específicas.

---

# 5. Público-alvo

## 5.1 Usuários da corretora

O produto precisa atender diferentes perfis dentro da corretora:

### Dono da corretora

Quer visão geral, eficiência, redução de custo, escala, controle e melhoria de atendimento.

Precisa entender:

* o que está acontecendo na operação;
* quais gargalos existem;
* quais automações estão ativas;
* quanto a IA está custando;
* onde há risco;
* quais atendimentos precisam de atenção;
* quais Auxiliares estão gerando valor.

### Gestor operacional

Quer organizar equipe, processos, filas, regras, canais, agentes e qualidade.

Precisa:

* configurar ou supervisionar atendimento;
* acompanhar casos;
* revisar histórico;
* ativar Auxiliares;
* personalizar fluxos;
* validar conexões;
* controlar permissões.

### Operador / atendente

Quer resolver o trabalho do dia a dia com menos atrito.

Precisa:

* encontrar informações rápido;
* entender o que fazer em cada caso;
* ver conversas e casos;
* receber apoio do AutoBrokers;
* executar ações simples;
* transferir para humano quando necessário.

### Administrador interno da corretora

Pode configurar equipe, preferências, canais, conhecimento e limites.

Nem todo usuário da corretora deve ter esse papel.

---

## 5.2 Usuários internos AutoBrokers

A equipe interna AutoBrokers acessa o Admin Global.

Esse ambiente não é o produto diário da corretora.

Serve para:

* criar e gerenciar corretoras;
* configurar planos;
* acompanhar custos;
* criar templates globais;
* cadastrar Auxiliares globais;
* cadastrar conectores globais;
* administrar catálogos;
* revisar logs;
* governar conhecimento;
* fazer suporte;
* controlar qualidade e segurança.

---

# 6. Princípios de produto

## 6.1 Chat-first

A primeira experiência da corretora deve ser o AutoBrokers.

```txt
/dashboard = AutoBrokers chat-first
```

Não deve existir uma Home cheia de cards operacionais.

A tela inicial deve ser limpa, direta e semelhante em espírito ao ChatGPT/Claude:

* nome AutoBrokers;
* input central;
* baixa poluição visual;
* dois atalhos principais no máximo;
* foco em conversa e execução.

Atalhos iniciais aprovados:

```txt
Ver atendimentos
Novo auxiliar
```

Esses atalhos não substituem a navegação, apenas reduzem fricção.

---

## 6.2 Mobile-first

O produto deve ser desenhado pensando em uso real por celular e desktop.

Mobile-first não significa que tudo será usado só no celular.

Significa que nenhuma experiência importante pode depender de uma tela grande para ser compreendida.

Regras:

* telas limpas;
* poucos elementos por etapa;
* navegação em camadas;
* ações principais acessíveis;
* formulários simples;
* permissões claras;
* nada de grids enormes na primeira tela;
* nada de páginas com dezenas de cards competindo por atenção.

Para módulos complexos, preferir fluxos progressivos:

```txt
galeria -> detalhe -> configuração -> permissões -> revisão -> execução/histórico
```

---

## 6.3 Progressive disclosure

Não despejar complexidade na primeira tela.

O corretor não precisa ver tudo ao mesmo tempo.

A experiência deve revelar complexidade conforme o usuário entra em uma área.

Exemplo:

* primeiro vê “Auxiliares”;
* depois vê “Galeria”, “Meus Auxiliares”, “Execuções”;
* depois entra no detalhe de um Auxiliar;
* depois configura gatilhos, conectores e permissões.

---

## 6.4 Segurança antes de automação real

Qualquer ação externa real precisa respeitar segurança operacional.

Ações de risco não podem acontecer invisivelmente.

Exemplos de ações sensíveis:

* enviar mensagem para cliente;
* enviar mensagem para seguradora;
* acionar portal;
* alterar dados de apólice;
* gerar cobrança;
* executar rotina recorrente;
* usar credencial de sistema externo;
* responder em nome da corretora.

Antes de produção real, essas ações precisam de:

* permissões;
* logs;
* histórico;
* aprovação humana quando necessário;
* dry-run quando aplicável;
* rastreabilidade;
* limite por usuário/tenant;
* rollback ou cancelamento quando possível.

---

## 6.5 Curadoria antes de RAG

O material bruto do projeto é valioso, mas não pode entrar cru na base de conhecimento.

Fontes brutas como:

* conversas de WhatsApp;
* prints;
* documentos;
* áudios;
* PDFs;
* planilhas;
* acessos;
* dados de clientes;
* dados de seguradoras;
* credenciais;
* protocolos reais;

devem passar por:

* classificação;
* remoção ou mascaramento de PII;
* separação de credenciais;
* validação de origem;
* curadoria;
* transformação em pacotes de conhecimento;
* definição de escopo de carregamento;
* políticas de acesso.

Nada de intake bruto direto no RAG.

---

# 7. Identidade e naming

## 7.1 Produto

Nome do produto:

```txt
AutoBrokers.ai
```

Nome do sistema/repositório/runtime:

```txt
AutoBrokers Intelligence OS
```

---

## 7.2 Agente principal

O agente central da corretora se chama:

```txt
AutoBrokers
```

Regras:

* usar no plural;
* não personalizar por corretora;
* não trocar por nome humano;
* não usar JARVYS;
* não usar AutoBroker no singular como nome final visível;
* tratar como a marca do agente principal.

Toda corretora tem seu AutoBrokers.

A lógica é semelhante a “Claude” ou “ChatGPT”: o nome do assistente é fixo.

---

## 7.3 Termos proibidos na UI final

Não usar como marca visível para cliente:

```txt
Smith
Agent Smith
Smith AI
Sistema Smith
JARVYS
OpenClaw
LionClaw
Conversa ao vivo
Estudos
Rotinas
```

Observações:

* Smith pode permanecer em nomes técnicos internos temporários, desde que não apareça para o cliente.
* LangSmith é ferramenta externa e não deve ser confundida com branding Smith.
* “Rotinas” deve virar “Auxiliares”.
* “Conversa ao vivo” antiga não deve voltar.
* “Estudos” não deve existir como página final.

---

# 8. Arquitetura conceitual do produto

O AutoBrokers.ai é organizado em três camadas.

```txt
AutoBrokers.ai
├── Product Layer
├── Smith Runtime Engine
└── AutoBrokers Domain Brain
```

---

## 8.1 Product Layer

É a camada visível e estratégica.

Ela define:

* marca;
* UX;
* navegação;
* módulos;
* linguagem;
* permissões;
* experiência da corretora;
* Admin Global;
* onboarding;
* empacotamento de features;
* forma como o usuário entende o produto.

Essa camada deve ser construída agora com cuidado máximo, porque evita que o produto vire apenas “Smith renomeado”.

---

## 8.2 Smith Runtime Engine

É a base técnica invisível.

O Smith fornece:

* Next.js;
* FastAPI;
* LangGraph;
* agentes;
* subagentes;
* delegations;
* ferramentas HTTP;
* MCP;
* RAG;
* Qdrant;
* MinIO;
* Redis;
* Supabase;
* billing;
* custos;
* logs;
* admin;
* chat streaming;
* documentos;
* sanitização;
* multi-tenancy.

Decisão canônica:

```txt
Smith é motor, não produto.
```

O usuário final não precisa saber que Smith existe.

---

## 8.3 AutoBrokers Domain Brain

É a camada de conhecimento, regras, atendimento e inteligência específica de seguros.

Ela será construída a partir de:

* ResultVision;
* Agent OS;
* AutoBrokers Intelligence OS V2;
* conversas reais;
* documentos de atendimento;
* corredores;
* skills;
* guardrails;
* templates;
* contratos operacionais;
* dados de domínio curados.

Decisão canônica:

```txt
O cérebro de domínio não deve ser copiado bruto para dentro do runtime.
```

Ele deve ser transformado em pacotes curados, seguros e carregáveis.

---

# 9. Repositórios e fontes

## 9.1 Repo oficial atual

```txt
AutoBrokers-Intelligence-OS
```

Função:

* runtime oficial;
* base Smith adaptada;
* produto novo em construção;
* onde o desenvolvimento atual acontece.

Esse é o repo que deve receber código novo do produto.

---

## 9.2 ResultVision

Função:

* referência histórica;
* domínio de atendimento;
* telas antigas;
* conceitos de seguradoras;
* corredores;
* canais;
* fluxos de atendimento;
* experiências já pensadas para seguros.

Não é runtime final.

Não copiar bruto.

Usar como fonte de aprendizado.

---

## 9.3 Agent OS / AutoBrokers Intelligence OS V2

Função:

* cérebro arquitetural;
* documentação de agentes;
* governança;
* corredores;
* skills;
* memória;
* guardrails;
* contratos;
* execução;
* evals;
* planos.

Não é runtime ativo agora.

Deve orientar decisões e pacotes futuros.

---

## 9.4 AutoBrokers Resulta Intake

Função:

* material bruto;
* conversas de clientes;
* conversas com seguradoras;
* documentos;
* PDFs;
* imagens;
* áudios;
* evidências;
* dados reais.

Não pode ser usado diretamente em RAG.

Antes precisa de Vault, PII policy, redaction e curadoria.

---

# 10. Módulos principais

## 10.1 AutoBrokers

É o chat central da corretora.

Finalidade:

* conversar com o dono, gestor ou operador;
* responder perguntas operacionais;
* consultar conhecimento;
* orientar sobre seguros;
* explicar processos;
* acionar módulos;
* futuramente delegar para Auxiliares;
* futuramente consultar Atendimento;
* futuramente executar ações com permissão.

O AutoBrokers é interno à corretora.

Ele não é o atendente externo do cliente final.

---

## 10.2 Atendimento

É o módulo operacional de atendimento a clientes, segurados, leads, sinistros, assistências e casos.

Inclui, por fases:

* painel operacional;
* fila de atendimentos;
* casos;
* conversas;
* ligações;
* segurados;
* documentos do atendimento;
* handoff;
* acompanhamento;
* agentes de atendimento;
* canais;
* seguradoras;
* corredores.

Atendimento é diferente do AutoBrokers.

O AutoBrokers ajuda o time da corretora.

Atendimento lida com a operação externa da corretora.

---

## 10.3 Auxiliares

Auxiliares são automações/subagentes produtizados para tarefas específicas da corretora.

Eles substituem o termo “Rotinas”.

Exemplos futuros:

* Auxiliar de cobrança;
* Auxiliar de renovação;
* Auxiliar de follow-up;
* Auxiliar de resumo diário;
* Auxiliar de análise de documentos;
* Auxiliar de conferência de apólices;
* Auxiliar de pós-venda;
* Auxiliar de Google Meu Negócio;
* Auxiliar de oportunidades;
* Auxiliar de sinistros;
* Auxiliar de assistência residencial;
* Auxiliar de relatórios.

Decisão canônica:

```txt
Auxiliares devem usar o motor do Smith: agents, subagents, delegations, tools, MCP e RAG.
```

Não criar um runtime paralelo.

LionClaw/OpenClaw podem inspirar UX, inteligência e padrões, mas não devem virar runtime principal.

---

## 10.4 Conhecimento

É a área de documentos, memórias, bases e pacotes de conhecimento.

Inclui:

* documentos da corretora;
* documentos globais;
* memórias da corretora;
* conhecimento de seguros;
* pacotes de atendimento;
* pacotes de Auxiliares;
* materiais curados;
* RAG;
* sanitização.

A primeira versão não deve virar um “depósito de arquivos”.

Precisa ser limpa, pesquisável e segura.

---

## 10.5 Conectores e Canais

Área responsável por conexões externas.

Inclui:

* WhatsApp;
* telefonia;
* e-mail;
* Google Workspace;
* Google Drive;
* Calendar;
* Notion;
* Slack;
* MCPs;
* sistemas de gestão;
* Infocap;
* Quiver;
* Segfy;
* portais de seguradoras;
* APIs;
* webhooks;
* n8n quando aplicável;
* Evolution API;
* Z-API se mantida como provider alternativo.

Regra importante:

```txt
Uma conexão deve ser reutilizável por Atendimento, Auxiliares e AutoBrokers quando fizer sentido.
```

Exemplo:

Se a corretora conectou um portal Bradesco, essa conexão não deve ser recriada separadamente para cada módulo.

Ela deve existir em um Vault/Connection Layer com permissões.

---

## 10.6 Personalização / Configurações

Área onde a corretora configura:

* dados da corretora;
* usuários;
* equipe;
* preferências;
* limites;
* agentes de atendimento;
* canais;
* conexões;
* permissões;
* identidade operacional;
* regras de uso;
* custos quando aplicável.

A área de Personalização não deve virar um menu caótico.

Ela precisa ser organizada por camadas e subpáginas.

---

## 10.7 Admin Global

Ambiente interno da equipe AutoBrokers.

Funções:

* gerenciar corretoras;
* planos;
* créditos;
* custos;
* billing;
* logs;
* templates globais;
* Auxiliares globais;
* conectores globais;
* conhecimento global;
* usuários;
* aprovações;
* governança;
* suporte;
* auditoria.

Admin Global não é a experiência diária da corretora.

---

# 11. Diferença entre AutoBrokers, Agentes de Atendimento e Auxiliares

## 11.1 AutoBrokers

* Nome fixo.
* Principal agente interno.
* Não personalizável por nome.
* Porta de entrada do sistema.
* Fala com o usuário da corretora.
* Orquestra e consulta.

---

## 11.2 Agentes de Atendimento

* Atuam em fluxos de atendimento.
* Podem ter nome, tom e identidade personalizáveis.
* Podem atender clientes ou apoiar operadores.
* Estão ligados ao módulo Atendimento.
* Podem ser configurados por corretora.
* Têm regras mais rígidas porque podem afetar cliente final.

---

## 11.3 Auxiliares

* São automações/subagentes por tarefa.
* Podem ser globais ou específicos da corretora.
* Podem ser ativados por galeria.
* Podem ter configuração própria.
* Podem usar conectores.
* Podem executar manualmente no MVP.
* Futuramente podem ter agendamento, gatilhos e execução recorrente.

---

# 12. MVP atual

## 12.1 Estado atual do projeto

O projeto já tem:

* repo novo instalado;
* runtime Smith funcionando;
* EasyPanel sandbox;
* Supabase sandbox;
* Redis;
* Qdrant;
* MinIO;
* API;
* Web;
* Admin;
* tenant login;
* chat respondendo;
* AutoBrokers como experiência inicial;
* documentação canônica inicial em `docs/canon`.

Mas ainda falta:

* documentação canônica profunda;
* UX final;
* design system;
* camada de produto para Auxiliares;
* Vault definido;
* conexão entre cérebro de seguros e runtime;
* RAG curado;
* Atendimento migrado;
* limpeza de resíduos técnicos;
* evolução do dashboard tenant;
* refinamento do Admin Global.

---

## 12.2 MVP estratégico recomendado

O MVP deve focar em:

1. chat-first funcionando bem;
2. documentação canônica robusta;
3. design/navegação definidos por Claude Design;
4. Auxiliares MVP;
5. conhecimento curado simples;
6. conexão segura futura;
7. Atendimento migrado por fases.

A ordem é importante.

Não iniciar redesenho grande de UI sem documentação e design brief.

Não iniciar Atendimento complexo antes de resolver runtime/Agent OS/Vault.

Não ingerir intake bruto antes da política de Vault e curadoria.

---

# 13. Experiência inicial desejada

A primeira tela da corretora deve ser:

```txt
AutoBrokers
[caixa de texto central]
[Ver atendimentos] [Novo auxiliar]
```

Sensação desejada:

* limpa;
* moderna;
* parecida em espírito com ChatGPT/Claude;
* sem excesso de cards;
* sem dashboard antigo;
* sem “Home da corretora”;
* sem métricas inventadas;
* sem ruído visual.

A tela pode evoluir depois, mas nunca deve perder o princípio chat-first.

---

# 14. Navegação conceitual

A navegação final ainda será definida em detalhe por UX-001 e Claude Design.

Mas a direção de produto é:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

Outras áreas podem existir como subáreas:

* Conhecimento;
* Conectores;
* Canais;
* Equipe;
* Custos;
* Logs;
* Configurações.

Regra:

```txt
Sidebar deve ser enxuta. Complexidade entra dentro das páginas, não no primeiro nível.
```

---

# 15. UX de Auxiliares

O módulo Auxiliares deve ser inspirado no conceito de Claude Routines, mas com identidade AutoBrokers.

Estrutura provável:

```txt
Auxiliares
├── Meus Auxiliares
├── Galeria
├── Criar Auxiliar
└── Execuções
```

Fluxo ideal:

```txt
galeria -> detalhe -> personalizar -> conectar -> permissões -> revisar -> ativar -> executar -> histórico
```

MVP de Auxiliares:

* galeria;
* ativação;
* configuração simples;
* execução manual;
* histórico básico;
* sem scheduler obrigatório no primeiro corte;
* sem criação conversacional complexa no primeiro corte;
* sem ações externas reais sem HITL.

---

# 16. UX de Conectores

Conectores devem seguir padrão limpo de galeria.

Estrutura mental:

```txt
Conectores
├── Ferramentas
├── Seguradoras
├── Sistemas de Gestão
├── Canais
└── Conexões ativas
```

O usuário deve:

1. ver o conector;
2. entender para que serve;
3. clicar em conectar;
4. revisar permissões;
5. autenticar ou inserir credenciais;
6. ver status;
7. reutilizar a conexão em módulos autorizados.

Conectores não devem ser configurados de forma duplicada por Atendimento, Auxiliares e AutoBrokers.

Eles devem usar um Vault compartilhado por tenant.

---

# 17. Atendimento e Corredores

Atendimento será um dos módulos mais complexos.

Ele deve herdar conceitos do ResultVision e Agent OS, mas não por cópia bruta.

Conceitos importantes:

* ramo;
* seguradora;
* canal;
* serviço;
* corredor;
* subcorredor;
* dados mínimos;
* perguntas permitidas;
* templates;
* protocolos;
* ação segura;
* handoff;
* acompanhamento;
* logs.

Exemplo:

```txt
Assistência Residencial -> Allianz -> WhatsApp -> Eletricista
```

Isso pode representar um corredor/subcorredor específico.

Mas a implementação final deve ser decidida em ADR-003 Atendimento.

---

# 18. Runtime e execução

## 18.1 O que usar do Smith

Usar:

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
* billing;
* logs;
* chat streaming;
* admin;
* documentos;
* sanitização.

---

## 18.2 O que não fazer

Não criar:

* outro runtime agentic paralelo;
* outro sistema de chat do zero;
* outro backend de Auxiliares do zero;
* outra arquitetura fora do Smith sem justificativa forte.

---

## 18.3 Onde entra LionClaw/OpenClaw

Entram como referência de inteligência, UX e padrões.

Não entram como runtime principal.

Usar para inspiração em:

* criação de Auxiliares;
* delegação;
* interface agentic;
* experiência de execução;
* autonomia;
* permissões;
* padrões de orquestração.

Mas a base executável deve continuar sendo Smith, salvo decisão futura em ADR.

---

# 19. Segurança, LGPD e dados

O produto lidará com dados sensíveis.

Pode envolver:

* CPF;
* telefone;
* endereço;
* dados de apólice;
* sinistro;
* fotos;
* documentos;
* conversas;
* informações financeiras;
* dados de seguradora;
* credenciais de portal.

Regras iniciais:

1. não ingerir dados brutos sem curadoria;
2. não expor credenciais;
3. não carregar conversas reais em RAG sem redaction;
4. separar conhecimento global de conhecimento por corretora;
5. respeitar isolamento multi-tenant;
6. registrar ações relevantes;
7. proteger service role e secrets;
8. limitar ações externas;
9. usar aprovação humana quando necessário.

---

# 20. Fora de escopo agora

Não faz parte do ciclo imediato:

* redesenhar todo o Admin Global;
* migrar todos os corredores;
* implementar Atendimento completo;
* criar scheduler avançado de Auxiliares;
* criar marketplace completo;
* ingerir intake bruto;
* ativar WhatsApp real;
* ativar InfoCap real;
* ativar n8n real;
* ativar Stripe real;
* criar light mode;
* copiar ResultVision;
* copiar Agent OS bruto;
* criar dashboard cheio de métricas;
* reviver Estudos;
* reviver Conversa ao vivo;
* deixar Claude Code tomar decisões estratégicas abertas.

---

# 21. Critérios de sucesso do produto

## 21.1 Curto prazo

O projeto estará no caminho certo quando:

* `/dashboard` abrir uma experiência chat-first limpa;
* documentação canônica estiver profunda e consistente;
* Claude Design conseguir criar telas a partir dos docs sem perguntar o básico;
* Claude Code conseguir executar batches sem inventar produto;
* Admin Global continuar funcional;
* runtime Smith continuar estável;
* branding visível estiver AutoBrokers;
* não houver Home de cards;
* não houver JARVYS visível;
* Auxiliares estiverem definidos como produto.

---

## 21.2 Médio prazo

O MVP ficará demonstrável quando:

* AutoBrokers responder com contexto básico da corretora;
* Auxiliares tiverem galeria e execução manual;
* conhecimento curado puder ser consultado;
* conexões tiverem modelo claro de Vault;
* Atendimento tiver primeiro recorte definido;
* design system estiver documentado;
* fluxo mobile estiver desenhado;
* logs e custos estiverem preservados.

---

## 21.3 Longo prazo

O produto estará forte quando:

* corretoras conseguirem operar parte relevante do dia a dia pelo AutoBrokers;
* Auxiliares executarem tarefas recorrentes com segurança;
* Atendimento funcionar em fluxos reais;
* corredores forem carregados de forma curada;
* documentos e conversas alimentarem conhecimento com LGPD;
* Admin Global permitir distribuir templates e melhorias;
* a plataforma aprender com uso, evals e feedback;
* novos módulos puderem ser adicionados sem bagunçar a arquitetura.

---

# 22. Instruções para LLMs e agentes futuros

Qualquer LLM trabalhando neste projeto deve seguir estas regras:

1. ler este PRD antes de propor produto;
2. tratar `docs/canon/` como fonte de verdade ativa;
3. tratar `docs/_archive/` como histórico, não como decisão atual;
4. não copiar ResultVision para o runtime;
5. não copiar Agent OS bruto para o runtime;
6. não ingerir intake bruto;
7. não reviver Home de cards;
8. não usar JARVYS;
9. não usar Smith como marca visível;
10. não criar design system definitivo sem Claude Design;
11. não pedir ao Claude Code para decidir estratégia aberta;
12. separar produto, runtime e cérebro de domínio;
13. preservar a base Smith enquanto transforma a experiência em AutoBrokers;
14. preferir batches pequenos, testáveis e reversíveis;
15. documentar decisões antes de implementar.

---

# 23. Próximos documentos relacionados

Este PRD deve ser lido junto com:

```txt
docs/canon/ADR-001-runtime.md
docs/canon/UX-001-navegacao.md
docs/canon/DS-001-design-brief.md
docs/canon/UX-007-auxiliares.md
docs/canon/ADR-002-vault.md
docs/canon/ADR-003-atendimento.md
docs/canon/ROADMAP-001-execucao.md
```

Ordem recomendada de leitura:

```txt
1. PRD-001-visao-produto.md
2. ADR-001-runtime.md
3. UX-001-navegacao.md
4. DS-001-design-brief.md
5. UX-007-auxiliares.md
6. ADR-002-vault.md
7. ADR-003-atendimento.md
8. ROADMAP-001-execucao.md
```

---

# 24. Decisão canônica final deste PRD

AutoBrokers.ai será construído como um sistema operacional agentic para corretoras de seguros, com experiência principal chat-first, agente central fixo chamado AutoBrokers, módulos operacionais ao redor, Smith como runtime técnico invisível e o cérebro de seguros migrado por curadoria a partir de ResultVision, Agent OS e materiais reais.

A prioridade agora é transformar o projeto em uma plataforma limpa, coerente e documentada antes de expandir funcionalidades.

Nenhum novo módulo grande deve ser implementado sem passar por documentação canônica, design orientado e batch técnico controlado.


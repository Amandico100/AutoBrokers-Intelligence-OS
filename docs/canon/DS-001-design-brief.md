---
# DS-001 — Design Brief para Claude Design

Status: canonical  
Produto: AutoBrokers.ai  
Sistema: AutoBrokers Intelligence OS  
Documento: direção visual, princípios de UI/UX e brief para criação do Design System  
Última atualização: 2026-06-06  
Responsável estratégico: Architect / CEO AutoBrokers.ai  
Audiência: Claude Design, Claude Code, Codex, LLMs estratégicas, devs, UX/UI e time fundador

---

# 1. Objetivo deste documento

Este documento define a direção visual do AutoBrokers.ai para orientar Claude Design.

Ele não é o Design System final.

Ele não deve ser interpretado como uma lista rígida de tokens finais, componentes definitivos ou layout fechado.

O papel deste documento é explicar com máxima clareza:

- que tipo de produto estamos construindo;
- qual sensação visual o sistema deve transmitir;
- quais referências devem ser usadas;
- quais erros devem ser evitados;
- como Claude Design deve pensar a experiência;
- quais telas e padrões ele deve propor;
- quais decisões visuais ainda precisam ser feitas por um especialista em design;
- como preparar o terreno para Claude Code implementar depois com segurança.

A decisão mais importante:

```txt
O AutoBrokers.ai deve parecer um ChatGPT/Claude especializado em seguros, não um dashboard SaaS tradicional cheio de cards.
````

---

# 2. Papel do Claude Design

Claude Design deve ser usado como especialista em:

* arquitetura visual;
* hierarquia de páginas;
* UI/UX;
* mobile-first;
* design system;
* componentes reutilizáveis;
* padrões de navegação em camadas;
* clareza visual;
* microinterações;
* layout de páginas;
* composição visual;
* experiência do usuário final.

Claude Design não deve decidir sozinho:

* estratégia de produto;
* arquitetura runtime;
* modelo de dados;
* escopo do MVP;
* integrações reais;
* regras de segurança;
* banco de dados;
* prioridades de backend;
* implementação final.

Essas decisões vêm dos documentos canônicos.

Claude Design transforma a direção estratégica em experiência visual.

---

# 3. Contexto do produto

AutoBrokers.ai é um SaaS multi-tenant para corretoras de seguros.

Ele começou como um sistema focado em atendimento, com módulos de:

* atendimentos;
* filas;
* casos;
* conversas;
* ligações;
* segurados;
* seguradoras;
* canais;
* corredores;
* agentes de atendimento;
* configurações da corretora.

Agora o produto está sendo reconstruído sobre o runtime do Smith V6.2, que oferece infraestrutura técnica forte:

* chat;
* agentes;
* subagentes;
* RAG;
* documentos;
* Qdrant;
* MinIO;
* Redis;
* Supabase;
* billing;
* logs;
* admin multi-tenant;
* tools;
* MCP;
* streaming;
* base para Auxiliares.

Mas o produto final não é Smith.

O produto final é AutoBrokers.ai.

Smith deve virar infraestrutura invisível.

O dashboard antigo do AutoBrokers/ResultVision é referência de domínio de seguros, especialmente para Atendimentos, Seguradoras e Corredores.

Mas o design antigo é denso demais para ser a experiência principal.

O novo produto deve unir:

```txt
Smith Runtime + AutoBrokers Domain Brain + UX limpa estilo ChatGPT/Claude
```

---

# 4. Visão visual do produto

O AutoBrokers.ai deve transmitir:

* inteligência;
* clareza;
* controle;
* sofisticação;
* segurança;
* simplicidade;
* precisão;
* modernidade;
* confiança;
* produtividade;
* automação;
* domínio profundo de seguros.

Ele não deve parecer:

* sistema legado;
* ERP antigo;
* CRM inchado;
* dashboard poluído;
* tela administrativa técnica;
* software de call center;
* template genérico de SaaS;
* painel com muitos cards sem hierarquia;
* ferramenta para desenvolvedor.

A sensação desejada:

```txt
“Abri o AutoBrokers e estou conversando com uma inteligência especializada que entende minha corretora e me ajuda a operar tudo.”
```

---

# 5. Referências principais

Claude Design deve usar estas referências como inspiração de lógica, não como cópia literal.

## 5.1 ChatGPT

Referência para:

* tela inicial chat-first;
* sidebar limpa;
* histórico de conversas;
* entrada principal com caixa de texto;
* galeria de apps/conectores;
* experiência minimalista;
* foco no prompt;
* poucos elementos visuais competindo por atenção;
* modais de conexão/permissão;
* navegação simples.

O que queremos absorver:

```txt
Simplicidade, centralidade do chat, sidebar limpa, apps/conectores em galeria.
```

O que não queremos copiar:

```txt
Identidade visual exata, marca, textos, estrutura proprietária.
```

---

## 5.2 Claude

Referência para:

* sensação de calma;
* layout limpo;
* tom mais humano;
* foco na conversa;
* organização de projetos;
* clareza textual;
* experiência menos barulhenta;
* inteligência com aparência acessível.

O que queremos absorver:

```txt
Calma visual, elegância, clareza, organização e sensação de ferramenta inteligente.
```

---

## 5.3 Claude Routines

Referência para Auxiliares.

O módulo Auxiliares deve se inspirar na lógica de Claude Routines:

* criar uma rotina/auxiliar;
* definir objetivo;
* definir instruções;
* definir gatilhos;
* adicionar conectores;
* definir comportamento;
* configurar permissões;
* executar;
* revisar histórico.

O AutoBrokers não deve usar o nome “Rotinas” como principal.

O nome oficial é:

```txt
Auxiliares
```

O que queremos absorver:

```txt
Fluxo de criação/configuração, organização por etapas, gatilhos, conectores, permissões e comportamento.
```

---

## 5.4 ChatGPT Apps / Connectors

Referência para:

* Conectores;
* Seguradoras;
* Sistemas de gestão;
* Google Drive;
* Google Calendar;
* Slack;
* Notion;
* WhatsApp;
* InfoCap;
* Quiver;
* portais de seguradoras;
* MCPs;
* APIs externas.

O padrão desejado:

```txt
Galeria -> Detalhe -> Conectar -> Permissões -> Status
```

---

## 5.5 Dashboard antigo AutoBrokers/ResultVision

Referência para domínio, não para estética principal.

Aproveitar:

* organização de Atendimentos;
* filas;
* casos;
* conversas;
* segurados;
* seguradoras;
* canais;
* portal;
* corredores;
* subcorredores;
* status de conexão;
* ideia de conectar/vincular/configurar.

Melhorar:

* densidade visual;
* excesso de informação;
* hierarquia;
* navegação;
* mobile;
* clareza;
* divisão entre operação e configuração.

---

# 6. Princípios de design

## 6.1 Chat-first

A primeira tela do Dashboard da Corretora é o AutoBrokers.

Não é uma Home com cards.

A tela inicial deve ter:

* sidebar;
* chat;
* frase principal;
* input;
* dois atalhos simples;
* histórico ou acesso a conversas.

Não deve ter:

* cards grandes;
* métricas;
* gráficos;
* status técnicos;
* excesso de botões;
* dashboard operacional logo de entrada.

---

## 6.2 Mobile-first real

O produto deve ser desenhado pensando no celular desde o começo.

Mobile-first significa:

* navegação confortável no celular;
* telas em camadas;
* retorno claro;
* ações fáceis de tocar;
* menus limpos;
* modais curtos;
* páginas de detalhe para configurações longas;
* transições suaves;
* nada de tabelas gigantes como base principal.

Desktop deve ser uma expansão da experiência, não o contrário.

---

## 6.3 Navegação em camadas

O usuário deve ir aprofundando.

Padrão:

```txt
Galeria/Listagem
→ Detalhe
→ Configuração
→ Permissões
→ Confirmação
```

Essa lógica vale para:

* Auxiliares;
* Conectores;
* Seguradoras;
* Corredores;
* Atendimentos;
* Conhecimento;
* documentos;
* equipe;
* configurações.

Não colocar tudo em uma página só.

---

## 6.4 Poucos itens no primeiro nível

O primeiro nível da sidebar deve ser simples:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

O resto entra como páginas internas, abas, filtros ou detalhes.

---

## 6.5 Operação separada de configuração

Operação é o que o usuário faz no dia a dia.

Configuração é o que ele ajusta para o sistema funcionar.

Exemplo:

```txt
Atendimentos = operar casos
Personalização > Seguradoras = configurar seguradoras
```

Não misturar.

---

## 6.6 Visual calmo

O sistema deve usar poucos elementos chamativos.

Priorizar:

* espaço em branco;
* contraste equilibrado;
* textos claros;
* componentes discretos;
* sombras sutis;
* bordas suaves;
* poucos acentos de cor;
* ícones simples;
* estados bem desenhados.

---

## 6.7 Linguagem não técnica

O usuário é corretor, gestor ou operador.

Não usar como texto visível principal:

* MCP;
* LangGraph;
* webhook;
* provider;
* RAG;
* execution engine;
* vector database;
* subagent;
* tool;
* API key;
* Qdrant;
* MinIO;
* Redis.

Quando necessário, traduzir para linguagem simples:

```txt
Conector
Permissão
Fonte de conhecimento
Auxiliar
Canal
Integração
Acesso
Histórico
Execução
```

---

# 7. Identidade visual desejada

## 7.1 Direção

A identidade deve ser:

```txt
minimalista, premium, escura, clara, técnica na medida certa, moderna e confiável.
```

## 7.2 Modo visual

Preferência inicial:

```txt
Dark mode como padrão.
```

Light mode pode existir no futuro, mas não é prioridade agora.

## 7.3 Cores

Claude Design deve propor a paleta final.

Direção inicial:

* fundo escuro limpo;
* superfícies em tons de preto/cinza;
* texto branco/cinza claro;
* acento azul/ciano com moderação;
* estados de sucesso, alerta e erro discretos;
* nada neon em excesso;
* nada “cyberpunk” exagerado;
* nada com excesso de gradientes.

Exemplo de intenção, não token final:

```txt
Background principal: preto/cinza muito escuro
Superfícies: cinza escuro
Bordas: cinza sutil
Texto primário: branco suave
Texto secundário: cinza claro
Acento: azul/ciano controlado
Erro: vermelho discreto
Sucesso: verde discreto
Aviso: amarelo/laranja discreto
```

Claude Design deve definir tokens finais.

---

## 7.4 Tipografia

A tipografia deve ser:

* moderna;
* muito legível;
* limpa;
* sem exagero futurista;
* boa em mobile;
* boa em desktop;
* apropriada para texto longo e interface.

Preferência:

```txt
Fonte principal sans-serif moderna.
```

Orbitron/futurista pode ser usada com muito cuidado apenas em elementos de marca, se fizer sentido.

Mas o produto não deve parecer um painel gamer.

---

## 7.5 Bordas, sombras e profundidade

Usar:

* bordas sutis;
* radius moderado;
* sombra leve;
* separação por espaço;
* elevação discreta.

Evitar:

* sombras pesadas;
* cards flutuando demais;
* bordas neon;
* excesso de efeitos;
* glassmorphism exagerado;
* fundo com muitos elementos decorativos.

---

# 8. Componentes fundamentais

Claude Design deve propor um conjunto de componentes reutilizáveis.

## 8.1 Sidebar

A sidebar deve suportar:

* desktop;
* mobile;
* colapsada;
* item ativo;
* grupos;
* histórico de conversas;
* botão nova conversa;
* área de usuário;
* acesso a configurações;
* navegação limpa.

Itens principais:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

No mobile, Claude Design deve avaliar:

* drawer;
* menu lateral;
* bottom nav;
* combinação de header + drawer;
* transição lateral.

---

## 8.2 Chat principal

O chat principal deve incluir:

* área central;
* estado vazio elegante;
* input claro;
* botão de enviar;
* anexos futuramente;
* mensagens do usuário;
* mensagens do AutoBrokers;
* loading;
* streaming;
* erro amigável;
* histórico;
* nova conversa;
* atalhos rápidos.

A Home deve ter apenas dois atalhos:

```txt
Ver atendimentos
Novo auxiliar
```

Esses atalhos podem ser cards pequenos, botões ou chips, conforme decisão do Claude Design.

---

## 8.3 Cards

Cards devem ser usados com moderação.

Tipos de cards necessários:

* card de atalho;
* card de Auxiliar;
* card de conector;
* card de seguradora;
* card de atendimento/caso;
* card de documento;
* card de status.

Cards não devem transformar a Home em dashboard.

Cards devem ter:

* título claro;
* descrição curta;
* status se necessário;
* ação principal;
* ícone simples;
* pouco texto.

---

## 8.4 Galeria

A galeria será usada em:

* Auxiliares;
* Conectores;
* Seguradoras;
* Templates globais;
* Conhecimento, se necessário.

Padrão:

```txt
Busca
Filtros simples
Cards
Categorias
Estado vazio
Página de detalhe ao clicar
```

---

## 8.5 Página de detalhe

Página de detalhe deve existir para:

* Auxiliar;
* conector;
* seguradora;
* corredor;
* atendimento;
* documento;
* usuário/equipe;
* agente de atendimento.

Estrutura recomendada:

```txt
Header com título/status
Resumo curto
Ação principal
Abas ou seções
Detalhes
Permissões/configurações
Histórico/status
```

---

## 8.6 Modal de permissão/conexão

Usar para ações curtas:

* conectar;
* confirmar;
* aprovar;
* escolher permissões;
* ativar auxiliar;
* executar teste;
* desconectar;
* pausar.

Não usar modal gigante para configurações longas.

---

## 8.7 Tabs internas

Tabs podem ser usadas dentro de páginas profundas.

Exemplo em Seguradora:

```txt
Visão geral
Canais
Portal
Corredores
Credenciais
Logs
```

Exemplo em Auxiliar:

```txt
Resumo
Configuração
Conectores
Permissões
Execuções
```

Exemplo em Atendimento:

```txt
Timeline
Conversa
Documentos
Ações
Histórico
```

---

## 8.8 Breadcrumb / retorno

Páginas profundas precisam de contexto.

Desktop pode usar breadcrumb.

Mobile pode usar botão voltar contextual.

Exemplo:

```txt
Personalização / Seguradoras / Allianz / Corredores
```

Mobile:

```txt
← Allianz
Corredores
```

---

## 8.9 Estados vazios

Estados vazios são importantes.

Eles devem explicar o que está acontecendo e sugerir o próximo passo.

Exemplo:

```txt
Você ainda não ativou nenhum Auxiliar.
Escolha um modelo pronto na Galeria para começar.
```

---

## 8.10 Estados de erro

Erros devem ser humanos.

Exemplo ruim:

```txt
500 Internal Server Error
```

Exemplo melhor:

```txt
Não conseguimos carregar seus Auxiliares agora.
Tente novamente em alguns instantes.
```

---

# 9. Padrões por módulo

## 9.1 AutoBrokers

Tela principal.

Deve parecer:

* limpa;
* central;
* conversacional;
* poderosa;
* sem distrações.

Elementos:

* frase principal;
* input;
* 2 atalhos;
* histórico;
* nova conversa;
* mensagens.

Não colocar:

* dashboard;
* métricas;
* cards grandes;
* status técnicos;
* seletor confuso de agentes.

---

## 9.2 Atendimentos

Módulo mais operacional.

Pode ser mais denso que o chat, mas ainda deve ser organizado.

Padrões:

```txt
Lista -> Detalhe -> Timeline/Ações
```

Subáreas:

* Visão geral;
* Fila;
* Casos;
* Conversas;
* Ligações;
* Segurados.

O design deve permitir uso por operador.

Importante:

Atendimentos não é lugar de configurar seguradora.

---

## 9.3 Auxiliares

Módulo mais estratégico depois do chat.

Precisa parecer simples mesmo sendo poderoso.

Padrões:

```txt
Meus Auxiliares
Galeria
Criar Auxiliar
Execuções
```

Fluxo ideal:

```txt
Galeria
→ Auxiliar de Cobrança
→ Ativar
→ Personalizar
→ Permissões
→ Executar teste
→ Acompanhar execuções
```

No MVP, priorizar:

* galeria;
* detalhe;
* ativação;
* execução manual;
* histórico simples.

---

## 9.4 Personalização

Área de setup.

Deve ser organizada por categorias.

Sugestão:

```txt
Corretora
Equipe
Agentes de atendimento
Conhecimento
Conectores
Seguradoras
Canais
Custos e uso
Configurações avançadas
```

Claude Design deve decidir se isso aparece como:

* grid de cards;
* lista de categorias;
* tabs;
* search + categorias;
* layout estilo Settings moderno.

Mas não deve ser uma página gigante com tudo junto.

---

## 9.5 Seguradoras

Dentro de Personalização.

Padrão:

```txt
Lista de seguradoras
→ Detalhe da seguradora
→ Canais / Portal / Corredores / Credenciais
```

Deve ser simples para o corretor entender:

* disponível;
* conectada;
* precisa configurar;
* erro;
* em teste;
* ativa.

---

## 9.6 Conectores

Dentro de Personalização.

Padrão estilo ChatGPT Apps:

```txt
Galeria
→ Detalhe
→ Conectar
→ Permissões
→ Status
```

Categorias possíveis:

* Ferramentas;
* Google;
* Comunicação;
* Sistemas de gestão;
* Seguradoras;
* Documentos;
* Automação.

---

## 9.7 Conhecimento

Dentro de Personalização inicialmente.

Padrão de biblioteca.

Pode ter:

* documentos;
* memórias;
* bases globais;
* uploads;
* status de processamento;
* permissões.

Design deve ser simples e seguro.

---

# 10. Mobile-first em detalhe

Claude Design deve desenhar mobile com intenção.

## 10.1 Comportamento desejado

O usuário deve sentir que está avançando em camadas.

Exemplo:

```txt
Auxiliares
→ Galeria
→ Auxiliar de Cobrança
→ Ativar
```

No mobile, a próxima tela pode deslizar lateralmente.

Essa sensação de navegação progressiva é importante.

## 10.2 Recomendações para mobile

Avaliar:

* header fixo;
* botão voltar;
* drawer lateral;
* bottom sheet;
* bottom nav se fizer sentido;
* cards de toque fácil;
* inputs grandes;
* modais curtos;
* páginas de detalhe para configuração longa;
* breadcrumbs simplificados;
* transição lateral.

## 10.3 O que evitar no mobile

* tabelas grandes;
* sidebar desktop espremida;
* modais muito altos;
* cards demais;
* filtros complexos visíveis ao mesmo tempo;
* múltiplas colunas;
* textos longos em cards;
* ações pequenas demais.

---

# 11. Densidade visual

## 11.1 Tela inicial

Baixíssima densidade.

## 11.2 Auxiliares

Densidade média-baixa.

## 11.3 Personalização

Densidade média.

## 11.4 Atendimentos

Densidade média ou média-alta, mas controlada.

## 11.5 Admin Global

Pode ter densidade mais alta, mas não deve parecer bagunçado.

---

# 12. Hierarquia de informação

Toda tela precisa responder rapidamente:

1. Onde estou?
2. O que posso fazer aqui?
3. Qual é a ação principal?
4. O que já está configurado?
5. O que precisa de atenção?
6. Como volto?

Se a tela não responder isso em poucos segundos, está errada.

---

# 13. Linguagem visual de status

Status precisam ser claros.

Exemplos:

```txt
Ativo
Pausado
Pendente
Conectado
Não conectado
Precisa configurar
Em teste
Com erro
Aguardando aprovação
Executado
Falhou
```

Usar cores com moderação.

Não depender só de cor: usar texto/ícone também.

---

# 14. Ícones

Ícones devem ser simples, consistentes e discretos.

Preferir ícones lineares ou minimalistas.

Evitar ícones exagerados, 3D, coloridos demais ou estilo gamer.

Ícones devem ajudar, não decorar demais.

---

# 15. Microcopy

O texto da interface deve ser:

* claro;
* direto;
* humano;
* sem jargão;
* orientado a ação;
* profissional;
* acessível.

Exemplos bons:

```txt
Conectar Google Drive
Ativar Auxiliar
Ver atendimentos
Novo auxiliar
Revisar antes de enviar
Aguardando aprovação
Testar conexão
```

Exemplos ruins:

```txt
Executar provider MCP
Configurar subagent runtime
Inicializar orchestration layer
Habilitar vector retrieval
```

---

# 16. Personalidade da interface

A interface deve parecer:

* inteligente;
* parceira;
* calma;
* objetiva;
* competente;
* premium;
* segura.

Não deve parecer:

* infantil;
* exageradamente informal;
* robótica demais;
* técnica demais;
* agressiva;
* carnavalesca;
* genérica.

---

# 17. Tratamento da marca AutoBrokers

## 17.1 Nome

Nome do produto:

```txt
AutoBrokers.ai
```

Nome do sistema:

```txt
AutoBrokers Intelligence OS
```

Nome do agente central:

```txt
AutoBrokers
```

Não usar:

```txt
JARVYS
Smith
Agent Smith
Smith AI
Sistema Smith
```

## 17.2 Uso do nome AutoBrokers

Na tela do chat:

```txt
AutoBrokers
```

Na documentação técnica:

```txt
AutoBrokers Intelligence OS
```

Na comunicação externa:

```txt
AutoBrokers.ai
```

---

# 18. O que Claude Design deve entregar

Claude Design deve produzir uma proposta organizada, não apenas uma tela isolada.

## 18.1 Entregáveis esperados

```txt
1. Direção visual geral
2. Paleta proposta
3. Tipografia proposta
4. Tokens iniciais
5. Componentes base
6. Layout da tela AutoBrokers chat-first
7. Sidebar desktop
8. Navegação mobile
9. Padrão de página em camadas
10. Padrão de galeria
11. Padrão de detalhe
12. Padrão de modal de permissão
13. Fluxo visual de Auxiliares
14. Fluxo visual de Personalização > Conectores
15. Fluxo visual de Personalização > Seguradoras
16. Regras de estados vazios/erros/loading
17. Guia para Claude Code implementar
```

## 18.2 Primeiro foco de Claude Design

O primeiro foco deve ser:

```txt
Dashboard da Corretora
```

Dentro dele:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

Admin Global vem depois.

---

# 19. Ordem sugerida para Claude Design

Claude Design deve trabalhar nesta ordem:

## Fase 1 — Fundamento visual

* interpretar PRD;
* interpretar UX-001;
* propor direção visual;
* propor paleta;
* propor tipografia;
* propor componentes básicos;
* propor estrutura mobile/desktop.

## Fase 2 — AutoBrokers chat-first

* tela inicial;
* empty state;
* input;
* 2 atalhos;
* histórico;
* sidebar;
* mobile.

## Fase 3 — Navegação em camadas

* padrão lista/detalhe;
* breadcrumb;
* retorno mobile;
* transições;
* tabs internas.

## Fase 4 — Auxiliares

* Meus Auxiliares;
* Galeria;
* Detalhe;
* Ativar;
* Configurar;
* Permissões;
* Execuções.

## Fase 5 — Personalização

* página principal;
* Conectores;
* Seguradoras;
* Conhecimento;
* Agentes de atendimento;
* Equipe.

## Fase 6 — Atendimentos

* Visão geral;
* Fila;
* Casos;
* Conversas;
* Segurados;
* Detalhe de caso.

## Fase 7 — Admin Global

* reavaliar admin herdado do Smith;
* limpar marca;
* melhorar navegação;
* organizar módulos internos.

---

# 20. O que Claude Design não deve fazer

Claude Design não deve:

* criar Home com cards grandes;
* lotar a sidebar;
* trazer Estudos;
* trazer Conversa ao vivo antiga;
* usar JARVYS;
* usar Smith como marca;
* copiar o dashboard antigo sem redesenhar;
* desenhar só desktop;
* ignorar mobile;
* colocar tudo em modais;
* criar tabelas enormes como experiência principal;
* esconder ações importantes;
* inventar módulos fora do PRD;
* mudar estratégia de produto;
* decidir backend;
* criar design system final sem passar pelo fundador/Architect.

---

# 21. O que Claude Code deve receber depois

Claude Code só deve executar depois que Claude Design entregar telas/specs.

Claude Code precisa receber:

* arquivo/tela alvo;
* componente alvo;
* comportamento esperado;
* rota;
* escopo;
* fora de escopo;
* critérios de sucesso;
* prints/referência;
* docs canônicos aplicáveis.

Exemplo de tarefa boa para Claude Code:

```txt
Implementar apenas o novo EmptyState do AutoBrokers em /dashboard com base no design aprovado.
Não alterar backend.
Não alterar Supabase.
Não criar novas rotas.
Manter chat funcionando.
Rodar typecheck e build.
```

Exemplo de tarefa ruim:

```txt
Melhore o dashboard.
```

---

# 22. Relação com documentação canônica

Este documento depende de:

```txt
docs/canon/PRD-001-visao-produto.md
docs/canon/ADR-001-runtime.md
docs/canon/UX-001-navegacao.md
```

E orienta:

```txt
docs/canon/UX-007-auxiliares.md
docs/canon/ROADMAP-001-execucao.md
```

---

# 23. Critérios de sucesso visual

O design estará correto se:

* parecer limpo como ChatGPT/Claude;
* for mobile-first de verdade;
* tiver sidebar simples;
* abrir no chat;
* tiver só dois atalhos na Home;
* esconder complexidade em camadas;
* separar operação de configuração;
* Auxiliares parecerem fáceis de ativar;
* Conectores parecerem fáceis de conectar;
* Seguradoras forem organizadas em detalhe progressivo;
* Atendimentos for operacional sem ser caótico;
* Personalização concentrar setup sem virar bagunça;
* Admin Global ficar separado;
* não houver JARVYS/Smith visível;
* Claude Code conseguir implementar sem inventar produto.

---

# 24. Critérios de rejeição

Rejeitar qualquer proposta que:

* crie dashboard inicial com muitos cards;
* coloque 20+ itens na sidebar principal;
* use visual genérico de SaaS;
* pareça ERP antigo;
* pareça CRM tradicional;
* ignore mobile;
* coloque tudo na mesma página;
* misture Atendimentos com configuração;
* misture AutoBrokers com agentes de atendimento;
* transforme Auxiliares em tela técnica;
* use termos técnicos demais;
* reviva telas antigas rejeitadas;
* use JARVYS/Smith como marca.

---

# 25. Perguntas que Claude Design deve responder

Antes de desenhar tudo, Claude Design deve responder:

1. Qual deve ser a estrutura visual da sidebar no desktop?
2. Qual deve ser a estrutura mobile?
3. O mobile deve usar drawer, bottom nav ou combinação?
4. Como será a transição em camadas?
5. Como será o empty state do chat?
6. Como serão os dois atalhos da Home?
7. Como será a galeria de Auxiliares?
8. Como será a página de detalhe de um Auxiliar?
9. Como será o fluxo de ativação/permissão?
10. Como será a galeria de Conectores?
11. Como será a página de Seguradora?
12. Como separar Conectores de Seguradoras sem inflar menu?
13. Como organizar Conhecimento dentro de Personalização?
14. Como deixar Atendimentos operacional sem parecer poluído?
15. Quais componentes devem virar base reutilizável?

---

# 26. Direção final

O AutoBrokers.ai deve ser simples por fora e poderoso por dentro.

O usuário deve entrar e sentir:

```txt
“Eu não preciso aprender um sistema complexo. Eu posso conversar com o AutoBrokers e acessar o que preciso quando precisar.”
```

A complexidade de seguros existe.

Mas ela deve aparecer em camadas, no momento certo, com clareza.

A experiência principal deve começar assim:

```txt
AutoBrokers
[caixa de mensagem]
Ver atendimentos | Novo auxiliar
```

E o resto deve estar organizado em:

```txt
Atendimentos
Auxiliares
Personalização
```

Esse é o brief visual canônico para Claude Design.


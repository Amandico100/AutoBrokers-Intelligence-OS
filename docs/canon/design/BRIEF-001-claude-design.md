---
# BRIEF-001 — Briefing Curado para Claude Design

Status: canonical
Produto: AutoBrokers.ai
Sistema: AutoBrokers Intelligence OS
Tipo: Design Briefing (handoff estratégico → design)
Versão: 1.0
Última atualização: 2026-06-06
Responsável estratégico: Architect / CEO AutoBrokers.ai
Audiência: Claude Design (primário), Claude Strategy, Claude Code, Founder

---

## Como usar este documento

Este é o **único documento** que o Claude Design precisa ler para começar. Ele destila
nove documentos canônicos (PRD-001, UX-001, ADR-001, ADR-002, ADR-003, DS-001, UX-007,
ROADMAP-001 e o README) em um briefing acionável.

Se houver conflito entre este briefing e um documento canônico específico, o canônico
vence no detalhe — mas este briefing nunca deve contradizer um canônico, e foi escrito
para ser fiel a eles. Para aprofundar qualquer ponto, os canônicos completos estão em
`docs/canon/`.

O Claude Design **não precisa** abrir os nove documentos para começar. Deve abrir um
canônico específico apenas quando este briefing o mandar (ex.: "ver ADR-003 para os
estados de atendimento").

Regra de ouro: **este briefing entrega decisões e contexto, não pixels.** O trabalho de
pixels é do Claude Design. As decisões de produto abaixo são fechadas e não se discutem;
as decisões visuais são abertas e o Design deve propô-las.

---

# 1. Resumo executivo para Claude Design

Você vai desenhar o **Dashboard da Corretora** do AutoBrokers.ai: um SaaS de inteligência
artificial para corretoras de seguros, cuja experiência principal é **chat-first** — mais
parecida com ChatGPT/Claude do que com um painel administrativo tradicional.

O usuário entra e encontra o **AutoBrokers** (o agente central da corretora) no centro da
tela, com uma caixa de mensagem e dois atalhos discretos. A partir daí, navega para quatro
pilares: **AutoBrokers, Atendimentos, Auxiliares e Personalização.** Tudo o mais (Conhecimento,
Conectores, Seguradoras, Equipe, Custos) vive em camadas dentro desses pilares.

O produto é **simples por fora e poderoso por dentro.** Mobile-first, dark por padrão,
baixa densidade visual, premium. A complexidade do domínio de seguros existe, mas aparece
progressivamente — nunca toda de uma vez, nunca na primeira tela.

Sua primeira entrega não é "todas as telas". É um conjunto pequeno de **peças-âncora** que
definem a linguagem do produto inteiro: a tela chat-first, a sidebar, a navegação mobile e
três padrões-mestre reutilizáveis. Tudo o mais deriva dessas peças.

---

# 2. O que o produto É

- Um **sistema operacional de IA para corretoras de seguros**, multi-tenant.
- Uma experiência **chat-first**: o agente AutoBrokers é a porta de entrada.
- Uma plataforma com **módulos operacionais ao redor do chat**: atendimentos, automações
  (Auxiliares), conhecimento, conectores, seguradoras, personalização.
- **Mobile-first** de verdade: nenhuma experiência importante pode depender de tela grande
  para ser entendida.
- **Premium, limpo, calmo**: poucas cores, baixa densidade, hierarquia clara.
- Um produto com **governança e segurança embutidas**: ações sensíveis pedem aprovação
  humana; conexões passam por um Vault; dados sensíveis são protegidos.

---

# 3. O que o produto NÃO é

- **Não é um CRM tradicional** com grade de tabelas e dezenas de KPIs.
- **Não é um dashboard cheio de cards** como primeira tela. (Isso foi tentado, rejeitado e
  revertido. Não reviver.)
- **Não é o "Smith" renomeado.** Smith é o motor técnico invisível (ver §4).
- **Não é o "ResultVision" copiado.** ResultVision é referência de domínio, não de estética.
- **Não é um chatbot genérico.** É uma inteligência especializada em seguros com módulos reais.
- **Não tem menu inchado.** Quatro pilares no primeiro nível, nunca trinta itens.

---

# 4. Camadas do sistema (entenda, mas não desenhe as duas últimas)

O produto é a soma de três camadas. Você desenha **apenas a primeira**.

## 4.1 Product Layer — você desenha isto
A marca, a experiência, a navegação, as telas, os módulos, a linguagem final. É o que o
corretor vê e usa. Tudo neste briefing é sobre esta camada.

## 4.2 Smith Runtime Engine — invisível, você NÃO mostra
O motor técnico herdado do Smith V6.2: Next.js, FastAPI, LangGraph, agents/subagents/
delegations, RAG, Qdrant, MinIO, Redis, Supabase, billing, logs, chat streaming. É
infraestrutura. **A palavra "Smith" nunca aparece na interface.** Os Auxiliares e o chat
rodam sobre esse motor, mas o usuário nunca sabe disso. Você projeta como se o motor fosse
mágica invisível.

## 4.3 AutoBrokers Domain Brain — referência, você NÃO importa
O cérebro de seguros: corredores, skills, guardrails, templates, regras por seguradora.
Vem de ResultVision e do Agent OS. É **fonte de domínio curada**, não algo que se copia
para dentro do produto. Para você, importa como *conhecimento sobre o domínio* (o que é um
corredor, como funciona uma assistência residencial), não como telas a reproduzir.

---

# 5. Decisões FECHADAS que o Design NÃO pode alterar

Estas são decisões de produto. São direção oficial. Não as rediscuta, não as "melhore",
não as contorne. Você pode propor *como* elas parecem, nunca *se* elas existem.

1. **Produto:** AutoBrokers.ai. **Sistema:** AutoBrokers Intelligence OS.
2. **Agente central:** chama-se **AutoBrokers** (plural), nome fixo, não personalizável.
3. **Proibido na interface:** JARVYS, Smith, Agent Smith, Smith AI, LionClaw, OpenClaw.
4. **Home do tenant** = chat-first em `/dashboard`. Sem dashboard de cards como primeira tela.
5. **Tela inicial** = input central + frase simples + **dois atalhos fixos**:
   `Ver atendimentos` e `Novo auxiliar`. (Atalhos personalizáveis = fase futura.)
6. **Quatro pilares** no primeiro nível: AutoBrokers, Atendimentos, Auxiliares, Personalização.
7. **Conhecimento, Conectores, Seguradoras, Equipe, Custos, Logs** = subáreas dentro dos
   pilares, nunca itens de primeiro nível agora.
8. **Atendimento = operação. Personalização = configuração.** Nunca misturar os dois.
9. **Seguradora é entidade própria de domínio** (tem canais, portal, credenciais, corredores,
   regras, status). **Conector é a camada técnica** (OAuth, API, portal, WhatsApp, Drive).
   Seguradora *usa* conectores; conector não substitui a seguradora. As duas são páginas
   irmãs e integradas dentro de Personalização.
10. **Auxiliares MVP** = Galeria + Meus Auxiliares + Execuções + ativação + execução manual.
    **Sem** criação-por-prompt e **sem** scheduler avançado no primeiro corte (ambos = fase futura).
11. **Primeiro Auxiliar funcional** = "Auxiliar de Resumo de Atendimentos" (baixo risco, sem
    envio externo).
12. **Mobile** = hipótese-base é **bottom-nav com os 4 pilares** + navegação em camadas.
13. **Permissões por papel:** Dono/Admin da corretora vê Personalização completa; **Operador
    vê apenas o autorizado** (não vê credenciais, conectores sensíveis, custos, logs técnicos,
    equipe completa, Vault).
14. **Custos e logs:** Operador não vê; Admin da corretora vê versão *simplificada e amigável*;
    Admin Global (equipe AutoBrokers) vê a camada técnica completa.
15. **Admin Global** (interno da equipe AutoBrokers) é **outra superfície**, separada do
    Dashboard da Corretora. A corretora nunca acessa o Admin Global.
16. **Ações externas reais** (enviar WhatsApp/e-mail, acionar portal, alterar dados) exigem
    **aprovação humana (HITL)** no MVP. Devem ter um estado visual de "aguardando aprovação".
17. **Dark mode é o padrão.** Light mode = fase futura, não desenhar agora.
18. **Stack visual:** Tailwind + Radix / componentes estilo ShadCN, sobre Next.js. Você pode
    propor tokens, paleta, tipografia, spacing, radius e componentes — mas **não trocar a stack**.

---

# 6. Referências visuais e o que absorver de cada uma

Você deve absorver a *mentalidade* de cada referência, não copiar pixels.

- **ChatGPT** → a tela inicial limpa, a sidebar enxuta com histórico, o padrão de
  **Apps/Connectors** (galeria → card → detalhe → modal de conexão/permissão), os cards
  discretos, a experiência direta. Absorva a **leveza e a baixa densidade**.
- **Claude** → a calma visual, o foco na conversa, a sensação premium e organizada, os
  projetos. Absorva a **serenidade e a clareza**.
- **Claude Routines** → a lógica de **criar/configurar uma automação**: nome, instruções,
  gatilho, conectores, comportamento, permissões, modelos prontos. É o molde mental do fluxo
  de **Auxiliares** (adaptado para corretoras, e sem scheduler no MVP).
- **Dashboard antigo AutoBrokers / ResultVision** → referência de **domínio**, não de estética.
  Use para entender *o que* Atendimentos, Seguradoras e Corredores precisam conter
  (ex.: o padrão de abas "Visão Geral / Canais / Portal / Corredores" numa página de
  seguradora). **Não** use a densidade visual dele.

Síntese: **a estética vem de ChatGPT/Claude; o domínio vem do ResultVision.**

---

# 7. Estrutura do Dashboard da Corretora

```txt
Dashboard da Corretora
├── AutoBrokers            (chat-first — a Home)
├── Atendimentos           (operação: fila, casos, conversas, segurados)
├── Auxiliares             (automação: galeria, meus, execuções)
└── Personalização         (configuração)
    ├── Corretora
    ├── Equipe
    ├── Agentes de atendimento
    ├── Conhecimento
    ├── Conectores
    └── Seguradoras
```

Quatro pilares no topo. Tudo o mais em camadas. O usuário nunca deve sentir que entrou num
sistema cheio de menus.

---

# 8. Tela principal AutoBrokers (chat-first) — PEÇA-ÂNCORA Nº 1

Esta é a tela mais importante do produto. Tudo deriva dela.

**Deve conter:**
- a sidebar (ver §9);
- a área central de chat;
- uma frase principal curta que comunique que se fala com o AutoBrokers
  (ex.: "Como posso ajudar sua corretora hoje?" — você propõe a final);
- um input grande e convidativo;
- **exatamente dois atalhos** abaixo do input: `Ver atendimentos` e `Novo auxiliar`;
- acesso a conversas recentes (onde fica é decisão sua — ver §29.6 do UX-001);
- botão de nova conversa;
- um empty state limpo e elegante.

**Nunca deve conter:**
- cards grandes de KPI, métricas operacionais, status técnico;
- "LLM conectado", "base de conhecimento ativa", "créditos IA" como card principal;
- seletor confuso de agentes para o usuário comum;
- qualquer menção a JARVYS ou Smith;
- aparência de dashboard SaaS tradicional.

Pense nesta tela como o "momento zero" do produto: o corretor abre e sente que tem um
copiloto especializado em seguros pronto para conversar. Calma, foco, convite.

---

# 9. Sidebar desktop — PEÇA-ÂNCORA Nº 2

- **Quatro itens** no primeiro nível: AutoBrokers, Atendimentos, Auxiliares, Personalização.
- Enxuta, limpa, com hierarquia clara. Nunca trinta itens.
- O histórico de conversas pode viver aqui (proposta sua).
- Estados claros: item ativo, hover, foco.
- Deve transmitir a mesma serenidade da tela de chat.

O que **não** entra no primeiro nível agora: Dashboard, Home, Estudos, Conversa ao vivo,
Playbooks, Setup, Canais, Seguradoras, Corredores, Conhecimento, Documentos, Memórias, Logs,
Custos, Equipe, Relatórios, Configurações gerais, Catálogo global. Tudo isso mora dentro
dos pilares.

---

# 10. Navegação mobile — PEÇA-ÂNCORA Nº 3

- Hipótese-base: **bottom-nav com os 4 pilares.** Você pode refinar a execução visual, mas
  mantenha os quatro pilares.
- Páginas profundas usam **navegação em camadas** com retorno claro e sensação de avanço
  lateral (slide) quando fizer sentido.
- O histórico de conversas no mobile pode virar drawer, painel ou página própria (proposta sua).
- Nada de tabelas largas, grids densos ou múltiplas colunas espremidas.
- Regra: cada etapa mostra poucos elementos; a próxima etapa revela mais.

---

# 11. Padrão de navegação em camadas (transversal)

Quase todo módulo complexo segue a mesma espinha:

```txt
lista/galeria → detalhe → configuração → permissões → revisão → execução/histórico
```

Desenhe esse fluxo **uma vez, muito bem**, e reutilize em Auxiliares, Conectores, Seguradoras
e Atendimentos. A consistência desse padrão é o que faz o produto parecer coeso e fácil.
No mobile, cada seta acima é uma camada nova (push/slide), com botão de voltar sempre visível.

---

# 12. Padrão de Galeria — PADRÃO-MESTRE A

Inspiração: Apps/Connectors do ChatGPT.

- Grade de **cards discretos** (não cards gigantes), cada um com ícone, nome, descrição curta
  e estado (disponível / ativo / em configuração).
- Categorias quando fizer sentido (ex.: Conectores por categoria).
- Busca/filtro leve.
- Clicar num card leva ao **Padrão de Página de Detalhe** (§13).

Reutilizado por: Galeria de Auxiliares, Galeria de Conectores, lista de Seguradoras.

---

# 13. Padrão de Página de Detalhe — PADRÃO-MESTRE B

- Cabeçalho com nome, ícone, status e ação primária.
- Corpo em **seções ou abas** (progressive disclosure): visão geral → configuração →
  permissões → histórico.
- No mobile, abas viram navegação em camadas ou segmented control (proposta sua).
- Ação primária clara; ações secundárias discretas.
- Sempre com caminho de volta evidente.

Reutilizado por: detalhe de Auxiliar, detalhe de Conector, página de Seguradora, detalhe de Caso.

---

# 14. Padrão de Modal de Permissão — PADRÃO-MESTRE C

Inspiração: o modal de conexão/consentimento do ChatGPT.

- Aparece quando o usuário conecta algo ou autoriza uma ação.
- Mostra com clareza: **o que será acessado, para qual finalidade, qual o nível de risco,
  quem poderá usar.**
- Linguagem de corretora, não técnica (nada de "OAuth scope" — dizer "vai poder ler seus
  e-mails", por exemplo).
- Botões claros: autorizar / cancelar. Ação irreversível sempre exige confirmação explícita.
- Para ações de risco (envio externo, alteração de dados), o modal comunica que haverá
  **aprovação humana** antes da execução.

Reutilizado por: conectar um conector, autorizar um Auxiliar, aprovar uma ação de atendimento.

---

# 15. Módulo Auxiliares

Conceito: automações inteligentes e especializadas para corretoras (ex.: Resumo de
Atendimentos, Cobrança, Renovação, Conferência de Documentos, Follow-up, Reputação Google).
Rodam sobre o motor invisível; o usuário só vê "um Auxiliar que faz X".

**Estrutura MVP:**
```txt
Auxiliares
├── Galeria          (descobrir e ativar — usa Padrão-Mestre A)
├── Meus Auxiliares  (os ativados pela corretora)
└── Execuções        (histórico de rodadas, com custo e resultado)
```

**Fluxo de ativação (usa o padrão em camadas):**
```txt
Galeria → detalhe do Auxiliar → ativar → configurar campos básicos
→ definir permissões → executar manualmente → ver histórico
```

**No MVP, NÃO desenhar:** criação de Auxiliar por prompt, scheduler/gatilhos recorrentes,
automação externa sem aprovação, marketplace público, builder visual avançado. (Tudo isso
é fase futura — pode existir como "em breve" desabilitado, se ajudar a comunicar a visão.)

**Primeiro Auxiliar real a desenhar com carinho:** "Auxiliar de Resumo de Atendimentos" —
recebe conversas/dados (sandbox no início), gera um resumo, salva a execução com custo e
histórico, **sem envio externo**. Ele é a vitrine de inteligência do produto.

Para detalhes de produto, ver `docs/canon/UX-007-auxiliares.md`.

---

# 16. Módulo Personalização

É onde a corretora **configura** o sistema. Concentra tudo que é setup, para manter
Atendimentos limpo de configuração.

```txt
Personalização
├── Corretora        (dados, identidade)
├── Equipe           (usuários, papéis, permissões)
├── Agentes          (agentes de atendimento personalizáveis)
├── Conhecimento     (base de conhecimento da corretora — ver §20)
├── Conectores       (camada técnica — ver §17)
└── Seguradoras      (entidades de domínio — ver §18)
```

**Permissões:** Dono/Admin vê tudo. **Operador vê só o autorizado** — desenhe a Personalização
de forma que áreas sensíveis (credenciais, conectores, custos, equipe completa, Vault)
simplesmente não apareçam para o operador, em vez de aparecerem bloqueadas.

---

# 17. Conectores

Camada técnica de conexão. Inspiração direta: Apps/Connectors do ChatGPT.

- **Galeria** (Padrão-Mestre A) com categorias: Ferramentas, Seguradoras (como categoria de
  conexão), Sistemas de Gestão, Canais, Comunicação, Dados/arquivos.
- Exemplos: Google Drive, Gmail, WhatsApp/Evolution, Slack, Notion, InfoCap, Quiver, Segfy,
  portais, APIs, webhooks.
- Fluxo: ver conector → entender para que serve → conectar → **modal de permissão**
  (Padrão-Mestre C) → status → reutilizar.
- **Regra crítica de UX:** uma conexão é feita **uma vez** e reutilizada por AutoBrokers,
  Atendimentos, Auxiliares e Conhecimento (com permissão). Nunca desenhe a mesma conexão
  sendo configurada de novo dentro de cada módulo. Isso é o **Vault** por baixo — você não
  desenha o Vault como tela técnica, mas desenha a *experiência* de "conectar uma vez, usar
  em todo lugar". Para a lógica, ver `docs/canon/ADR-002-vault.md`.

---

# 18. Seguradoras

Entidade própria de domínio (Allianz, Porto, Bradesco, HDI, Tokio…). **Não é um conector** —
ela *usa* conectores.

Uma seguradora contém, conceitualmente:
```txt
Seguradora
├── Canais (WhatsApp, 0800, e-mail, link)
├── Portal
├── Credenciais
├── Corredores e subcorredores
├── Regras
├── Status
└── Logs
```

Desenhe a **página de Seguradora** com o Padrão-Mestre B (detalhe em camadas/abas). O padrão
"Visão Geral / Canais / Portal / Corredores" do ResultVision é uma boa referência conceitual
de organização — modernizado e limpo. O fluxo de conectar uma seguradora reutiliza o
Padrão-Mestre C (modal de permissão) e as conexões do módulo Conectores.

**Não** misture tudo numa tela só. Seguradora e Conectores são irmãs e integradas, mas
distintas. Para o domínio (o que é corredor), ver `docs/canon/ADR-003-atendimento.md`.

---

# 19. Atendimentos

Módulo **operacional** (não configuração). Inspiração de domínio: dashboard antigo; estética:
ChatGPT/Claude limpo.

**Subáreas:**
```txt
Atendimentos
├── Visão geral
├── Fila
├── Casos
├── Conversas
├── Ligações
└── Segurados
```

**Fluxo mobile em camadas:** `Fila → Caso → Conversa → Dados → Ação`.

**O que NÃO colocar aqui** (é configuração, vai para Personalização): configuração de agentes,
criação de corredores, credenciais de seguradora, portais, setup de canais, Vault.

**Estados de um caso** (você não precisa desenhar todos, mas o sistema visual de status
precisa comportá-los): novo, em triagem, aguardando cliente, aguardando documento, em análise,
pronto para acionamento, **aguardando aprovação**, em andamento, aguardando seguradora,
em acompanhamento, handoff humano, resolvido, encerrado, cancelado, erro, bloqueado. (Lista
completa em ADR-003 §43.) Desenhe um **sistema de status** flexível, não 16 telas.

**Importante para o MVP:** Atendimentos vem **depois** do primeiro Auxiliar funcional (ver §23).
Na primeira leva de design, Atendimentos pode ser apenas o **shell** (lista + detalhe + status),
sem lógica de corredor. Evite tabelas grandes, dashboards densos, múltiplas colunas.

---

# 20. Conhecimento

Base de conhecimento da corretora. **No MVP, vive dentro de Personalização** (`Personalização →
Conhecimento`), não é pilar próprio. Pode virar módulo próprio no futuro se o uso justificar.

- Lista de fontes/documentos com status (curado, processando, restrito).
- Distinção visual entre conhecimento **global** (curado pela equipe AutoBrokers) e
  conhecimento **da corretora** (privado).
- **Não** desenhe ingestão de dados sensíveis/intake bruto como fluxo fácil — o produto
  bloqueia isso por design. A primeira validação usa documentos simples e seguros.

---

# 21. O que NÃO desenhar (proibições explícitas)

- Home com cards grandes / dashboard inicial denso.
- Sidebar com 30 itens; mais de 4 pilares no primeiro nível.
- "Estudos" ou "Conversa ao vivo" antiga (telas rejeitadas).
- Qualquer aparição de JARVYS ou Smith na interface.
- Mistura de Admin Global com Dashboard da Corretora.
- Modais gigantes para configurações complexas (use páginas em camadas).
- Criação de Auxiliar por prompt e scheduler avançado (fase futura).
- Light mode (fase futura).
- Telas que ignorem mobile.
- Jargão técnico exposto ao usuário (MCP, webhook, RAG, subagent, LangGraph, tool).
- Trocar a stack visual (Tailwind + Radix/ShadCN fica).
- Inventar módulos que não estão nos documentos canônicos.
- Desenhar o Admin Global agora (a prioridade é o Dashboard da Corretora).

---

# 22. Entregáveis esperados do Claude Design

1. **Mapa visual da navegação tenant** (4 pilares, desktop + mobile).
2. **Sidebar desktop** + comportamento e estados.
3. **Navegação mobile** (bottom-nav + camadas).
4. **Tela inicial AutoBrokers chat-first** (empty state, input, 2 atalhos, conversas, nova conversa).
5. **Três padrões-mestre**: Galeria (A), Página de Detalhe (B), Modal de Permissão (C).
6. **Estados visuais transversais**: status, empty state, loading, erro, aguardando aprovação.
7. **Fluxo de Auxiliares** (Galeria → detalhe → ativar → permissões → execução → histórico),
   incluindo o "Auxiliar de Resumo de Atendimentos".
8. **Fluxo Personalização → Conectores** (galeria + modal de permissão + status).
9. **Fluxo Personalização → Seguradoras** (página de seguradora em camadas).
10. **Shell de Atendimentos** (lista + detalhe + sistema de status), sem lógica de corredor.
11. **Recomendações de Design System**: paleta final dark-default, com base em preto,
    branco, cinzas e baixa saturação. O acento de cor ainda NÃO está fechado. Claude Design
    deve propor 2 ou 3 caminhos de paleta, incluindo:
    - opção monocromática premium inspirada em ChatGPT/Claude;
    - opção neutra/dessaturada inspirada em Linear;
    - opção com acento azul/ciano muito moderado, apenas se fizer sentido.
    
    A paleta final deve priorizar sofisticação, legibilidade, calma visual e baixa poluição.
    Nada de visual neon, cyberpunk ou SaaS colorido demais. Tipografia sans-serif moderna,
    spacing, radius moderado e tokens compatíveis com Tailwind/Radix.

---

# 23. Ordem de trabalho recomendada para Claude Design

A ordem importa: as primeiras peças definem a linguagem de todas as outras.

```txt
LEVA 1 — Fundação (define a linguagem do produto)
  1. Tela inicial AutoBrokers chat-first
  2. Sidebar desktop
  3. Navegação mobile (bottom-nav + camadas)
  4. Recomendações iniciais de Design System (tokens/paleta/tipografia)
  → Aprovar com o Founder antes de seguir.

LEVA 2 — Padrões-mestre (a base reutilizável)
  5. Padrão de Galeria (A)
  6. Padrão de Página de Detalhe (B)
  7. Padrão de Modal de Permissão (C)
  8. Estados transversais (status, empty, loading, erro, aguardando aprovação)
  → Aprovar.

LEVA 3 — Módulos (aplicação dos padrões)
  9.  Auxiliares (com o Auxiliar de Resumo de Atendimentos)
  10. Personalização → Conectores
  11. Personalização → Seguradoras
  12. Shell de Atendimentos
```

Não desenhe a Leva 2 antes da Leva 1 estar aprovada. Não desenhe a Leva 3 antes da Leva 2.
Isso evita retrabalho em cascata.

---

# 24. Como preparar o handoff para Claude Code

Depois que o design de cada peça for aprovado, prepare o handoff assim — porque o Claude Code
**executa tarefas fechadas, não decide produto**:

- Entregue **specs por tela/componente**, não "o app inteiro".
- Para cada peça: nome, objetivo, comportamento, estados, breakpoints (mobile/desktop),
  tokens usados, componentes Radix/ShadCN equivalentes, e o que está **fora de escopo**.
- Marque o que é **shell visual** (sem lógica) vs. o que conecta a dados reais.
- Nunca peça "melhore o dashboard". Peça, por exemplo: "Implemente o empty state chat-first
  aprovado em `/dashboard`, sem alterar backend, rotas novas ou Supabase."
- Indique a ordem de implementação alinhada ao ROADMAP (chat-first → sidebar → shells →
  Auxiliar de Resumo → Atendimento base).
- Sinalize qualquer ação sensível que precise de estado de aprovação humana na UI.

O Claude Code é forte para executar dentro do repositório real, mas resolve ambiguidade
"do jeito dele". Specs fechadas são o que garante que ele construa o que foi desenhado.

---

# 25. Perguntas finais antes do design (mínimas)

A maioria das decisões está fechada. Restam pontos **visuais** (não de produto) que o
próprio Claude Design deve propor durante a Leva 1, e o Founder valida:

1. **Frase principal** da tela de chat — qual tom final? (Design propõe 2-3 opções.)
2. **Onde o histórico de conversas** vive no desktop e no mobile? (Design propõe.)
3. **Subnavegação de Atendimentos**: tabs, subnav lateral ou segmented control? (Design propõe.)
4. **Paleta final**: qual caminho visual deve vencer?
   - monocromático premium estilo ChatGPT/Claude;
   - neutro/dessaturado inspirado em Linear;
   - preto/cinza com acento azul/ciano extremamente moderado.
   
   Claude Design deve propor amostras e justificar qual caminho transmite melhor:
   confiança, sofisticação, clareza, tecnologia e segurança para corretoras de seguros.
5. **Identidade/logo**: o "robozinho" atual é provisório — o Design assume liberdade ou há
   marca fechada? (Confirmar com Founder.)

Nenhuma dessas bloqueia o início. São decisões a fechar *dentro* da Leva 1, não antes dela.

---

## Encerramento

Este briefing existe para que o Claude Design comece com contexto total e zero ambiguidade
de produto, gastando sua inteligência onde ela importa: na qualidade visual e na experiência.

A direção é uma só: **simples por fora, poderoso por dentro.** Um corretor abre o AutoBrokers,
sente que conversa com uma inteligência especializada em seguros, e — quando precisa — alcança
Atendimentos, Auxiliares e Personalização sem nunca sentir o peso da máquina por trás.

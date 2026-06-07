---
# UX-001 — Arquitetura de Navegação

Status: canonical  
Produto: AutoBrokers.ai  
Sistema: AutoBrokers Intelligence OS  
Documento: arquitetura de navegação, módulos e experiência principal  
Última atualização: 2026-06-06  
Responsável estratégico: Architect / CEO AutoBrokers.ai  
Audiência: Claude Design, Claude Code, Codex, LLMs estratégicas, devs, UX/UI e time fundador

---

# 1. Objetivo deste documento

Este documento define a arquitetura de navegação do AutoBrokers.ai.

Ele não é um design system visual final.  
Ele não define pixels, cores finais, componentes finais ou layout definitivo.

Esse trabalho visual será feito posteriormente pelo Claude Design, com base neste documento, no `PRD-001`, no `ADR-001` e nas referências visuais aprovadas.

O objetivo aqui é dar a direção correta para que Claude Design e Claude Code não construam telas erradas, densas, poluídas ou desalinhadas com a visão do produto.

A decisão principal deste documento é:

```txt
O AutoBrokers.ai será uma experiência chat-first, mobile-first, limpa, progressiva e organizada em poucos pilares principais.
````

A tela inicial da corretora não é um dashboard de cards.

A tela inicial é o chat principal do AutoBrokers.

---

# 2. Princípios centrais de navegação

Toda navegação do AutoBrokers.ai deve obedecer a estes princípios:

1. **Chat-first**
   O AutoBrokers é a entrada principal do sistema.

2. **Mobile-first**
   A experiência deve funcionar muito bem no celular, não apenas “caber” no celular.

3. **Poucos itens no primeiro nível**
   A sidebar não deve virar um menu inchado com dezenas de opções.

4. **Progressive disclosure**
   Mostrar primeiro o simples. A complexidade aparece conforme o usuário entra em um módulo.

5. **Páginas em camadas**
   O usuário entra em uma área, depois em detalhes, depois em configurações específicas. Não colocar tudo na mesma página.

6. **Operação separada de configuração**
   O que o corretor usa no dia a dia não deve ficar misturado com setup, credenciais, personalização e conectores.

7. **Linguagem de corretora, não linguagem técnica**
   Evitar expor termos como MCP, webhook, provider, RAG, LangGraph, tool, subagent, execution engine.

8. **UX inspirada em ChatGPT, Claude e Claude Routines**
   A inspiração é de clareza, fluidez, hierarquia e leveza, não de cópia literal de código.

9. **Admin Global separado do Dashboard da corretora**
   O que a equipe AutoBrokers vê não é o que a corretora vê.

10. **Sem ressuscitar telas antigas rejeitadas**
    Não voltar com “Estudos”, “Conversa ao vivo” antiga, “Home da corretora” cheia de cards ou dashboard inicial poluído.

---

# 3. Superfícies do produto

O AutoBrokers.ai terá duas grandes superfícies:

```txt
AutoBrokers.ai
├── Dashboard da Corretora
└── Admin Global AutoBrokers
```

---

# 4. Dashboard da Corretora

Área usada pelos clientes do AutoBrokers.ai: donos, gestores, operadores e equipe da corretora.

O Dashboard da Corretora deve ser simples, moderno e orientado à ação.

A navegação principal deve ser organizada em quatro pilares:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

Esses quatro pilares são suficientes para o primeiro nível.

Outras áreas como Conhecimento, Conectores, Seguradoras, Equipe, Custos, Logs e Configurações entram como subáreas, páginas internas ou abas dentro desses pilares.

---

# 5. Sidebar principal da corretora

A sidebar da corretora deve começar simples.

## 5.1 Sidebar P0

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

Essa é a estrutura inicial recomendada para o produto.

---

## 5.2 O que não deve aparecer no primeiro nível agora

Não colocar no primeiro nível da sidebar neste momento:

```txt
Dashboard
Home da corretora
Estudos
Conversa ao vivo
Playbooks
Setup
Canais
Seguradoras
Corredores
Conhecimento
Documentos
Memórias
Logs
Custos IA
Equipe
Relatórios
Configurações gerais
Catálogo global
```

Essas áreas podem existir, mas devem morar dentro dos pilares certos.

O primeiro nível precisa ser limpo.

---

# 6. Regra fundamental da Home

A rota inicial da corretora é:

```txt
/dashboard
```

Essa rota deve abrir diretamente a experiência do AutoBrokers.

A Home é o chat.

Não criar uma página separada de Home com cards, status, métricas, gráficos ou atalhos demais.

## 6.1 Estrutura conceitual da tela inicial

A tela inicial deve seguir esta lógica:

```txt
Sidebar
Área central de chat
Mensagem/frase principal
Input grande
2 atalhos rápidos
Histórico/conversas em local apropriado
```

## 6.2 Atalhos iniciais permitidos

A tela inicial pode ter apenas dois atalhos principais:

```txt
Ver atendimentos
Novo auxiliar
```

Esses atalhos devem ser discretos, limpos e úteis.

Eles não devem transformar a Home em dashboard.

## 6.3 Frase principal

A frase principal deve comunicar que o usuário está falando com o AutoBrokers.

Exemplos possíveis para Claude Design testar:

```txt
Como posso ajudar sua corretora hoje?
```

ou

```txt
O que vamos resolver na sua corretora hoje?
```

ou

```txt
Converse com o AutoBrokers para operar, automatizar e melhorar sua corretora.
```

A frase final será refinada depois, mas o tom deve ser direto, moderno e útil.

---

# 7. AutoBrokers

## 7.1 Definição

AutoBrokers é o agente central da corretora.

Ele é fixo, não personalizável no nome e sempre se chama AutoBrokers.

Ele funciona como o centro de inteligência da corretora.

## 7.2 Papel no produto

O AutoBrokers deve:

* responder perguntas;
* orientar o usuário;
* consultar conhecimento;
* explicar processos;
* navegar conceitos da corretora;
* futuramente acionar Auxiliares;
* futuramente consultar atendimentos;
* futuramente sugerir melhorias;
* futuramente executar ações com aprovação.

## 7.3 Navegação

Item de menu:

```txt
AutoBrokers
```

Rota principal:

```txt
/dashboard
```

Rota técnica/compatibilidade:

```txt
/dashboard/chat
```

## 7.4 O que deve aparecer nessa área

* chat central;
* input;
* conversas recentes;
* botão de nova conversa;
* 2 atalhos rápidos;
* estado vazio limpo;
* mensagens do AutoBrokers;
* eventualmente histórico lateral ou drawer.

## 7.5 O que não deve aparecer

* cards grandes de KPI;
* métricas operacionais;
* status técnico;
* “LLM conectado”;
* “base de conhecimento ativa”;
* “créditos IA” como card principal;
* seletor confuso de agentes para usuário comum;
* nome JARVYS;
* nome Smith;
* tela estilo dashboard SaaS tradicional.

---

# 8. Atendimentos

## 8.1 Definição

Atendimentos é o módulo operacional da corretora.

Aqui ficam as atividades relacionadas a clientes, segurados, conversas, casos, filas, ligações e processos de assistência/sinistro.

Este módulo aproveita conceitos do dashboard antigo do AutoBrokers/ResultVision, mas deve ser redesenhado em uma estrutura mais limpa, moderna e mobile-first.

## 8.2 Item de menu

```txt
Atendimentos
```

## 8.3 Subáreas recomendadas

```txt
Atendimentos
├── Visão geral
├── Fila
├── Casos
├── Conversas
├── Ligações
└── Segurados
```

## 8.4 Regra importante

Atendimentos é operação, não configuração.

Portanto, não colocar aqui:

* configuração de agentes;
* criação de corredores;
* credenciais de seguradora;
* portais;
* catálogo global;
* setup de canais;
* integrações gerais;
* vault.

Essas coisas ficam em Personalização.

## 8.5 O que pode existir em Atendimentos

* painel operacional;
* status de filas;
* lista de casos;
* conversas em andamento;
* histórico por segurado;
* detalhes do atendimento;
* timeline do caso;
* documentos ligados ao caso;
* handoff humano;
* observações internas;
* ações seguras;
* filtros por status, canal, seguradora, tipo de caso.

## 8.6 Padrão de navegação interno

Atendimentos deve seguir o padrão:

```txt
Lista -> Detalhe -> Ação específica
```

Exemplo:

```txt
Atendimentos
→ Casos
→ Caso #123
→ Timeline / Conversas / Documentos / Ações
```

Não colocar tudo na mesma tela.

---

# 9. Auxiliares

## 9.1 Definição

Auxiliares são automações/subagentes especializados que fazem tarefas para a corretora.

Eles são inspirados na ideia de rotinas do Claude, mas com nome e linguagem próprios do AutoBrokers.

O nome oficial no produto é:

```txt
Auxiliares
```

Não usar “Rotinas” como nome principal.

## 9.2 Item de menu

```txt
Auxiliares
```

## 9.3 Subáreas recomendadas

```txt
Auxiliares
├── Meus Auxiliares
├── Galeria
├── Criar Auxiliar
└── Execuções
```

## 9.4 Estrutura ideal do módulo

O módulo deve seguir a experiência:

```txt
Galeria -> Detalhe -> Ativar -> Personalizar -> Executar -> Histórico
```

## 9.5 Inspiração de UX

Claude Design deve usar como inspiração:

* Claude Routines;
* ChatGPT Apps/Connectors;
* galerias limpas;
* páginas de detalhe progressivas;
* cards simples;
* permissões claras;
* configuração guiada.

Não copiar visualmente de forma literal, mas usar a lógica de interação.

## 9.6 O que um Auxiliar deve ter

Um Auxiliar pode ter:

* nome;
* descrição;
* objetivo;
* instruções;
* gatilho;
* conectores necessários;
* dados necessários;
* permissões;
* comportamento;
* tom;
* escopo;
* ações permitidas;
* aprovação humana quando necessário;
* logs;
* histórico de execução.

## 9.7 MVP de Auxiliares

O primeiro MVP de Auxiliares deve ser simples:

```txt
Galeria
Detalhe do Auxiliar
Ativar para corretora
Configurar campos básicos
Executar manualmente
Ver histórico simples
```

Não colocar no primeiro MVP:

* scheduler avançado;
* criação por prompt totalmente aberta;
* marketplace externo;
* execuções críticas automáticas;
* ações externas sem approval;
* múltiplos conectores complexos obrigatórios;
* UI poluída com dezenas de campos.

## 9.8 Relação com AutoBrokers

No futuro, o AutoBrokers poderá sugerir ou acionar Auxiliares.

Exemplo:

```txt
Usuário: "AutoBrokers, cobre os clientes inadimplentes desta semana."
AutoBrokers: "Posso usar o Auxiliar de Cobrança. Deseja revisar antes do envio?"
```

No MVP, é aceitável que o usuário entre no módulo Auxiliares e execute manualmente.

---

# 10. Personalização

## 10.1 Definição

Personalização é a área onde a corretora configura o sistema.

Ela concentra setup, preferências, conectores, agentes de atendimento, seguradoras, canais, conhecimento, equipe e configurações da corretora.

## 10.2 Item de menu

```txt
Personalização
```

## 10.3 Subáreas recomendadas

```txt
Personalização
├── Corretora
├── Equipe
├── Agentes de atendimento
├── Conhecimento
├── Conectores
├── Seguradoras
├── Canais
├── Custos e uso
└── Configurações avançadas
```

## 10.4 Regra

Personalização deve ser organizada em páginas internas limpas.

Não transformar Personalização em uma página gigante com tudo junto.

Padrão:

```txt
Personalização
→ Lista de categorias
→ Página da categoria
→ Detalhe/configuração específica
```

## 10.5 Exemplo

```txt
Personalização
→ Seguradoras
→ Allianz
→ Canais / Portal / Corredores / Credenciais
```

ou

```txt
Personalização
→ Conectores
→ Google Drive
→ Detalhes / Permissões / Conectar
```

---

# 11. Seguradoras, Canais e Corredores

## 11.1 Decisão de navegação

Seguradoras, Canais e Corredores não devem ser itens principais da sidebar.

Eles devem ficar dentro de:

```txt
Personalização
```

Motivo:

* conectar seguradora é configuração;
* configurar portal é configuração;
* habilitar canal é configuração;
* vincular corredor é configuração;
* operação do atendimento acontece depois no módulo Atendimentos.

## 11.2 Estrutura recomendada

```txt
Personalização
└── Seguradoras
    ├── Lista de seguradoras
    ├── Detalhe da seguradora
    │   ├── Visão geral
    │   ├── Canais
    │   ├── Portal
    │   ├── Corredores
    │   ├── Credenciais
    │   └── Logs/Status
```

## 11.3 Exemplo Allianz

```txt
Seguradoras
→ Allianz
→ Assistência Residencial
→ WhatsApp
→ Corredores
→ Eletricista / Encanador / Chaveiro / Eletrodomésticos
```

## 11.4 Regra de UX

O usuário não deve ver toda a complexidade de uma vez.

A navegação deve ser em camadas.

Primeiro:

```txt
Seguradoras disponíveis
```

Depois:

```txt
Detalhe da seguradora
```

Depois:

```txt
Canal ou corredor específico
```

Depois:

```txt
Conectar / configurar / testar
```

---

# 12. Conectores

## 12.1 Definição

Conectores são integrações com sistemas externos.

Exemplos:

* Google Drive;
* Google Calendar;
* Gmail;
* Slack;
* Notion;
* WhatsApp;
* Evolution;
* Z-API;
* sistemas de gestão;
* InfoCap;
* Quiver;
* portais de seguradoras;
* APIs externas;
* MCPs;
* webhooks.

## 12.2 Local na navegação

Conectores devem ficar dentro de:

```txt
Personalização -> Conectores
```

## 12.3 Padrão de UX

Inspirar-se no padrão:

```txt
Galeria -> Detalhe -> Conectar -> Permissões -> Status
```

## 12.4 Conectores genéricos vs seguradoras

Claude Design deve considerar separar visualmente:

```txt
Ferramentas
Seguradoras
Sistemas de gestão
Canais de comunicação
```

Mas sem criar quatro itens de sidebar.

Isso pode ser resolvido com abas/filtros dentro de Conectores ou Seguradoras.

## 12.5 Regra de reutilização

Uma conexão deve poder ser usada por vários módulos.

Exemplo:

```txt
Google Drive conectado
├── Conhecimento pode usar
├── Auxiliares podem usar
└── AutoBrokers pode consultar, se permitido
```

Exemplo:

```txt
Portal Bradesco conectado
├── Atendimentos pode usar
├── Auxiliar de cobrança pode usar
└── AutoBrokers pode orientar o usuário sobre status
```

---

# 13. Conhecimento

## 13.1 Definição

Conhecimento é a base de documentos, memórias e informações que o AutoBrokers e os módulos podem usar.

## 13.2 Local na navegação

No primeiro momento, Conhecimento deve ficar dentro de:

```txt
Personalização -> Conhecimento
```

Não virar item principal da sidebar agora.

## 13.3 Estrutura recomendada

```txt
Conhecimento
├── Documentos
├── Memórias da corretora
├── Base global disponível
├── Uploads
├── Status de processamento
└── Permissões
```

## 13.4 Inspiração

Pode seguir padrão semelhante a uma biblioteca limpa:

```txt
Todos
Arquivos
Memórias
Bases globais
```

Mas isso será definido por Claude Design.

## 13.5 Regra de segurança

Não ingerir material bruto sem curadoria.

Conhecimento deve respeitar Vault, PII, LGPD e escopo tenant.

---

# 14. Agentes de atendimento

## 14.1 Local na navegação

Agentes de atendimento devem ficar em:

```txt
Personalização -> Agentes de atendimento
```

Motivo:

Criar ou configurar agente é setup.

Usar agente no dia a dia acontece em Atendimentos.

## 14.2 Diferença entre AutoBrokers e agentes de atendimento

AutoBrokers:

* nome fixo;
* central;
* interno;
* não personalizável.

Agentes de atendimento:

* podem ter nome;
* podem ter tom;
* podem ter papel;
* podem ser ligados a canais;
* podem ser personalizados;
* podem atuar em atendimento externo;
* podem depender de seguradora/corredor.

## 14.3 Regra

Não misturar o AutoBrokers com agentes de atendimento na mesma configuração para usuário comum.

Essa separação precisa ser clara.

---

# 15. Custos, logs e equipe

Essas áreas existem e são importantes, mas não devem poluir o primeiro nível no MVP.

## 15.1 Local recomendado

```txt
Personalização
├── Equipe
├── Custos e uso
└── Logs / Auditoria
```

Para usuários comuns, talvez algumas dessas áreas fiquem ocultas conforme permissão.

## 15.2 Admin da corretora vs operador

O sistema deve suportar papéis:

```txt
Dono/Gestor da corretora
Operador
Admin interno AutoBrokers
```

O menu deve poder mudar conforme permissão.

Operador não precisa ver custos, conectores avançados ou configurações sensíveis.

---

# 16. Navegação mobile-first

## 16.1 Princípio

A experiência mobile não deve ser apenas a versão desktop espremida.

No mobile, o usuário deve sentir progressão clara entre telas.

## 16.2 Comportamento desejado

Quando o usuário entra em uma área, a próxima tela pode entrar com sensação de avanço lateral.

Exemplo:

```txt
Personalização
→ Seguradoras
→ Allianz
→ Corredores
```

No mobile, isso deve parecer uma navegação em camadas, com retorno fácil.

## 16.3 Padrão de interação mobile

Claude Design deve avaliar:

* menu lateral recolhido;
* drawer;
* transição lateral;
* botão voltar contextual;
* breadcrumb curto;
* header fixo;
* busca;
* tabs internas;
* bottom sheet para ações rápidas.

## 16.4 Regra

Não usar modais grandes demais no mobile quando uma página de detalhe for mais clara.

Modais devem ser usados para ações curtas:

* conectar;
* confirmar;
* aprovar;
* escolher permissão;
* confirmar execução.

Páginas devem ser usadas para configuração mais longa.

---

# 17. Padrão de páginas em camadas

Este é um dos padrões mais importantes do produto.

Evitar páginas gigantes.

Preferir:

```txt
Galeria/Listagem
→ Detalhe
→ Configuração
→ Permissões
→ Confirmação
```

## 17.1 Exemplo em Auxiliares

```txt
Auxiliares
→ Galeria
→ Auxiliar de Cobrança
→ Ativar
→ Configurar mensagem
→ Permissões
→ Executar teste
```

## 17.2 Exemplo em Conectores

```txt
Personalização
→ Conectores
→ Google Drive
→ Conectar
→ Permissões
→ Status conectado
```

## 17.3 Exemplo em Seguradoras

```txt
Personalização
→ Seguradoras
→ Allianz
→ Portal
→ Credenciais
→ Testar conexão
```

## 17.4 Exemplo em Atendimentos

```txt
Atendimentos
→ Casos
→ Caso residencial #123
→ Conversas
→ Timeline
→ Ação segura
```

---

# 18. Breadcrumb e retorno

Em páginas profundas, o usuário precisa saber onde está.

Padrões aceitos:

```txt
Personalização / Seguradoras / Allianz / Corredores
```

ou no mobile:

```txt
← Allianz
```

com título da seção atual.

Claude Design deve escolher a melhor solução visual.

---

# 19. Busca

Busca deve ser usada com cuidado.

Áreas onde busca é útil:

* Atendimentos;
* Casos;
* Conversas;
* Segurados;
* Auxiliares;
* Galeria de Auxiliares;
* Conectores;
* Seguradoras;
* Documentos;
* Conhecimento.

Busca não deve aparecer em excesso em telas simples.

---

# 20. Estados vazios

Estados vazios devem ser elegantes, úteis e não técnicos.

Exemplo ruim:

```txt
Nenhum registro encontrado.
```

Exemplo melhor:

```txt
Você ainda não ativou nenhum Auxiliar.
Escolha um modelo pronto na Galeria para começar.
```

Exemplo para Atendimentos:

```txt
Nenhum atendimento em aberto agora.
Quando novos casos chegarem, eles aparecerão aqui.
```

Exemplo para Conectores:

```txt
Nenhum conector ativo.
Conecte suas ferramentas para o AutoBrokers trabalhar com mais contexto.
```

---

# 21. Admin Global

## 21.1 Definição

Admin Global é a área interna usada pela equipe AutoBrokers.

Não é vista pelas corretoras comuns.

## 21.2 Papel

Admin Global serve para:

* gerenciar corretoras;
* usuários;
* planos;
* créditos;
* custos;
* templates globais;
* Auxiliares globais;
* conectores globais;
* seguradoras globais;
* knowledge global;
* logs;
* auditoria;
* billing;
* suporte;
* governança.

## 21.3 Relação com Dashboard da Corretora

Admin Global cria e disponibiliza estruturas globais.

Dashboard da Corretora ativa, personaliza e usa.

Exemplo:

```txt
Admin Global cria Auxiliar de Cobrança
↓
Corretora vê na Galeria de Auxiliares
↓
Corretora ativa e personaliza
↓
Execuções ficam isoladas para aquela corretora
```

Exemplo:

```txt
Admin Global cadastra seguradora Allianz
↓
Corretora vê Allianz em Personalização > Seguradoras
↓
Corretora conecta suas credenciais/canais
↓
Atendimentos podem usar Allianz quando permitido
```

## 21.4 Admin pode ser mais técnico

O Admin Global pode ter mais densidade e termos técnicos do que o Dashboard da Corretora, mas ainda deve ser limpo.

No futuro, também precisa de redesign.

A prioridade inicial de UX é o Dashboard da Corretora.

---

# 22. Roteamento conceitual

## 22.1 Rotas tenant

Sugestão conceitual:

```txt
/dashboard
/dashboard/chat
/dashboard/atendimentos
/dashboard/atendimentos/fila
/dashboard/atendimentos/casos
/dashboard/atendimentos/casos/[caseId]
/dashboard/atendimentos/conversas
/dashboard/atendimentos/segurados

/dashboard/auxiliares
/dashboard/auxiliares/galeria
/dashboard/auxiliares/[auxiliaryId]
/dashboard/auxiliares/[auxiliaryId]/configurar
/dashboard/auxiliares/execucoes

/dashboard/personalizacao
/dashboard/personalizacao/corretora
/dashboard/personalizacao/equipe
/dashboard/personalizacao/agentes
/dashboard/personalizacao/conhecimento
/dashboard/personalizacao/conectores
/dashboard/personalizacao/seguradoras
/dashboard/personalizacao/seguradoras/[insurerId]
```

Essas rotas não precisam ser implementadas todas agora.

Elas servem como direção arquitetural.

## 22.2 Rotas admin

Manter e reorganizar progressivamente:

```txt
/admin
/admin/companies
/admin/users
/admin/agents
/admin/documents
/admin/finops
/admin/logs
/admin/integrations
/admin/templates
/admin/auxiliaries
/admin/insurers
/admin/settings
```

Nem todas existem hoje.

---

# 23. Ordem de implementação recomendada

## 23.1 Antes de design grande

Fazer apenas:

* manter `/dashboard` chat-first;
* remover resíduos visuais ruins;
* manter sidebar mínima;
* corrigir branding crítico;
* não criar novos módulos grandes sem design.

## 23.2 Próximo trabalho de Claude Design

Claude Design deve produzir:

```txt
1. Mapa visual da navegação tenant
2. Proposta de sidebar desktop/mobile
3. Tela inicial chat-first do AutoBrokers
4. Padrão de página em camadas
5. Padrão de galeria/detalhe/modal
6. Fluxo de Auxiliares
7. Fluxo de Personalização > Conectores
8. Fluxo de Personalização > Seguradoras
9. Recomendações de Design System
```

## 23.3 Depois do design aprovado

Claude Code implementa em batches pequenos.

Exemplo:

```txt
36B1 — ajustar Empty State chat-first
36B2 — sidebar tenant limpa
36B3 — criar shell de Atendimentos sem lógica complexa
36B4 — criar shell de Auxiliares
36B5 — criar shell de Personalização
36B6 — conectar páginas reais existentes sem quebrar chat
```

A ordem final será definida no Roadmap.

---

# 24. O que Claude Design deve entender

Claude Design deve entender que:

* ele não está desenhando um CRM tradicional;
* ele está desenhando um sistema operacional de IA para corretoras;
* a primeira tela é um chat;
* a complexidade fica escondida em camadas;
* o usuário final não é técnico;
* o sistema precisa ser mobile-first;
* o produto precisa parecer limpo como ChatGPT/Claude;
* Auxiliares devem parecer fáceis de ativar;
* Conectores devem parecer fáceis de conectar;
* Seguradoras e corredores precisam ser organizados em camadas;
* Atendimentos pode ser mais operacional, mas não deve ser poluído;
* Admin Global é outra superfície.

---

# 25. O que Claude Design não deve fazer

Claude Design não deve:

* criar uma Home com cards grandes;
* inventar uma sidebar com 30 itens principais;
* trazer “Estudos” de volta;
* trazer “Conversa ao vivo” antiga de volta;
* usar JARVYS;
* usar Smith como marca;
* misturar Admin Global com Dashboard da Corretora;
* colocar tudo em uma página única;
* criar modais gigantes para configurações complexas;
* ignorar mobile;
* desenhar sem respeitar os quatro pilares.

---

# 26. O que Claude Code não deve fazer

Claude Code não deve:

* redesenhar por conta própria;
* decidir sidebar;
* decidir arquitetura de módulo;
* implementar dashboard grande sem spec;
* criar rotas falsas;
* criar cards inventados;
* mexer em backend sem necessidade;
* alterar Supabase sem ADR;
* copiar ResultVision;
* importar Agent OS bruto;
* ativar integrações reais;
* mudar o runtime Smith sem escopo claro.

Claude Code deve implementar apenas tarefas fechadas.

---

# 27. Navegação aprovada para MVP visual inicial

A navegação inicial aprovada para o Dashboard da Corretora é:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

Com `/dashboard` abrindo o AutoBrokers chat-first.

Esse é o ponto de partida para Claude Design.

---

# 28. Estrutura futura possível

Depois que o produto amadurecer, a sidebar pode evoluir para algo como:

```txt
AutoBrokers

Operação
- Atendimentos

Automação
- Auxiliares

Configuração
- Personalização
```

Ou manter os quatro itens diretos.

Claude Design deve testar a melhor hierarquia visual.

Mas a regra continua:

```txt
Poucos itens no primeiro nível.
```

---

# 29. Decisões fechadas e pontos finais para Claude Design

Esta seção substitui a lista antiga de decisões pendentes.

Algumas perguntas que antes estavam abertas já foram fechadas em documentos posteriores, especialmente `UX-007-auxiliares.md`, `ADR-002-vault.md`, `ADR-003-atendimento.md` e `ROADMAP-001-execucao.md`.

Claude Design deve tratar as decisões abaixo como direção oficial.

---

## 29.1 Decisões já fechadas

### 29.1.1 Conhecimento

No MVP, Conhecimento fica dentro de:

```txt
Personalização -> Conhecimento

---

# 30. Critérios de sucesso

A navegação estará correta se:

* `/dashboard` abrir o chat do AutoBrokers;
* a sidebar for simples;
* não houver dashboard inicial poluído;
* o usuário entender os quatro pilares;
* Atendimentos não misturar setup;
* Auxiliares tiver fluxo de galeria/detalhe/ativação;
* Personalização concentrar configuração;
* Seguradoras e conectores forem em camadas;
* mobile parecer natural;
* telas profundas tiverem retorno claro;
* Claude Code conseguir implementar sem decidir produto;
* novos chats/LLMs entenderem a estrutura lendo este documento.

---

# 31. Próximos documentos relacionados

Este documento deve ser lido junto com:

```txt
docs/canon/PRD-001-visao-produto.md
docs/canon/ADR-001-runtime.md
docs/canon/DS-001-design-brief.md
docs/canon/UX-007-auxiliares.md
docs/canon/ADR-002-vault.md
docs/canon/ADR-003-atendimento.md
docs/canon/ROADMAP-001-execucao.md
```

---

# 32. Encerramento

A navegação do AutoBrokers.ai deve dar sensação de clareza, controle e inteligência.

O corretor não deve sentir que entrou em um sistema complexo cheio de menus.

Ele deve sentir que abriu o AutoBrokers, conversou com uma inteligência especializada em seguros e, quando precisar, consegue acessar Atendimentos, Auxiliares e Personalização de forma simples.

A estrutura oficial é:

```txt
AutoBrokers
Atendimentos
Auxiliares
Personalização
```

O resto entra em camadas.

Essa é a base para Claude Design criar as peças visuais corretamente.


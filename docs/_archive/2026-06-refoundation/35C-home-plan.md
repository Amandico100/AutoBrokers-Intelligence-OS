# BATCH 35C - AutoBrokers Tenant Home Plan

> **Para o executor do 35D:** implemente este plano por etapas pequenas, validando a cada troca visual. Nao mexa em RAG, Worker, Docling, WhatsApp real, InfoCap, n8n, corredores, Supabase ou migrations.

**Goal:** planejar a primeira Home AutoBrokers do dashboard da corretora, chat-first e com operacao de seguros visivel.

**Architecture:** a Home deve reaproveitar o runtime de chat atual do Smith como motor tecnico, mas expor a experiencia AutoBrokers como produto, sem criar motor paralelo. O 35D deve aproximar `/dashboard` e `/dashboard/chat`: a primeira tela passa a ser a experiencia AutoBrokers, com chat central, atalhos e cards estaticos/dados leves, enquanto modulos reais de Atendimento, Auxiliares, RAG, Canais e Gestao entram em fases posteriores.

**Tech Stack:** Next.js App Router, React client components, Tailwind, componentes existentes `UnifiedSidebar`, `InputArea`, `MessageBubble`, APIs `/api/auth/me`, `/api/user/company-data`, `/api/agents`, `/api/conversations`, `/api/messages`, `/api/chat/stream`.

---

## 1. Resumo executivo

A Home atual da corretora (`/dashboard`) ainda e uma tela simples de boas-vindas com botao "Ir para o Chat". Ela deve ser substituida pela primeira versao da **AutoBrokers Home**.

A experiencia correta, conforme ADR-001, e:

```txt
AutoBrokers no centro
chat-first
atalhos operacionais
cards vivos da operacao
modulos orbitando o AutoBrokers
```

O 35D nao deve construir todo o dashboard final. Ele deve entregar um primeiro shell de produto confiavel:

- AutoBrokers como ponto de entrada.
- Chat central reaproveitando a logica funcional de `/dashboard/chat`.
- Atalhos rapidos que podem apontar para rotas existentes ou placeholders seguros.
- Cards operacionais basicos com dados leves ou estado vazio honesto.
- Historico recente.
- Status simples de sistema/credito/agente.

O objetivo e trocar a sensacao de "chat isolado" por "sistema operacional inteligente da corretora", sem criar dependencia nova.

## 2. Estado atual do tenant

### Rotas tenant atuais

| Rota | Funcao atual | Manter | Substituir | Fundir | Observacoes |
| --- | --- | --- | --- | --- | --- |
| `/dashboard` | Tela de boas-vindas simples, lista recursos e CTA para chat | Nao como esta | Sim | Sim, com chat | Deve virar AutoBrokers Home. Conteudo atual pode ser descartado. |
| `/dashboard/chat` | Chat funcional com agente, stream, imagem, audio, web search opcional, historico e seletor de agente | Sim | Nao | Sim, com Home | E a base tecnica do AutoBrokers. Pode continuar como rota dedicada ou virar componente reutilizavel. |
| `/dashboard/historico` | Lista conversas e abre conversa no chat | Sim | Nao | Parcial | Deve continuar como Historico do AutoBrokers; corrigir depois query param/conversation se necessario. |
| `/dashboard/configuracoes` | Perfil, avatar, telefone e senha do usuario | Sim | Nao | Nao | Mantem como configuracoes pessoais; configuracoes da corretora entram depois. |
| `/embed/[agentId]` | Widget externo embeddable | Sim, mas fora do fluxo | Nao | Nao | Fase posterior para canais/widget. Nao entra na Home P0. |

### Componentes tenant relevantes

| Componente | Uso atual | Reuso no 35D |
| --- | --- | --- |
| `components/UnifiedSidebar.tsx` | Sidebar tenant com AutoBrokers, conversas recentes, Chat/Historico/Configuracoes | Reaproveitar e preparar menu em fases. |
| `app/dashboard/chat/page.tsx` | Implementa chat completo | Extrair ou reutilizar blocos para Home. Evitar duplicar logica. |
| `components/InputArea/index.tsx` | Input multimodal com imagem, audio, web search e seletor de agente | Reaproveitar. |
| `components/ui/animated-ai-chat.tsx` | Textarea animado, botoes e seletor de agente | Reaproveitar. |
| `components/MessageBubble.tsx` | Renderiza mensagens, Markdown, audio, imagem e UCP | Reaproveitar. |
| `components/EmptyState.tsx` | Estado vazio atual do chat | Substituir ou adaptar para Hero AutoBrokers. |
| `components/TypingIndicator.tsx` | Indicador de resposta | Reaproveitar. |
| `hooks/useUserId.ts` | Usuario autenticado | Reaproveitar. |

### APIs usadas pelo tenant atual

| API | Uso atual | Reuso na Home |
| --- | --- | --- |
| `/api/auth/me` | Usuario e termos | Sim. |
| `/api/user/profile` | Perfil no sidebar/configuracoes | Sim. |
| `/api/user/company-data` | Company id e web search | Sim. |
| `/api/agents` | Agentes ativos da empresa | Sim; AutoBrokers deve ser o default. |
| `/api/conversations` | Criar/listar conversa | Sim. |
| `/api/messages` | Persistir mensagens | Sim. |
| `/api/chat/stream` | Resposta streaming do agente | Sim. |

## 3. Decisao de experiencia

Decisao central:

```txt
/dashboard deve virar AutoBrokers Home.
/dashboard/chat deve continuar existindo como modo chat focado, mas a Home deve conter o AutoBrokers como experiencia primaria.
```

Principios:

1. **Chat-first, nao dashboard puro.** O usuario deve entender que conversa com o AutoBrokers para operar a corretora.
2. **Operacao visivel.** Cards e alertas devem mostrar que ha uma corretora viva por tras do chat.
3. **Sem pagina Estudos.** Conhecimento entra como "Base de conhecimento", "Documentos" ou "Memorias da corretora".
4. **Sem Conversa ao vivo antiga.** Conversas externas ficam em Atendimento, nao como substituto do AutoBrokers.
5. **Sem personalizar o nome AutoBrokers.** O nome pode aparecer fixo em UI, header, empty state e atalhos.
6. **Dados reais so quando ja existem.** Onde ainda nao houver modulo, usar placeholder discreto e honesto.

## 4. Menu lateral proposto

Menu final desejado para a corretora, com classificacao de fase:

### INICIO

| Item | Rota sugerida | Prioridade | Acao no 35D |
| --- | --- | --- | --- |
| AutoBrokers | `/dashboard` | P0 agora | Implementar como Home principal. |

### OPERACAO

| Item | Rota sugerida | Prioridade | Acao no 35D |
| --- | --- | --- | --- |
| Painel | `/dashboard/operacao` | P1 proximo | Ocultar por enquanto ou mostrar como futuro. |
| Fila de atendimentos | `/dashboard/atendimento/fila` | P1 proximo | Ocultar por enquanto. |
| Casos | `/dashboard/atendimento/casos` | P1 proximo | Ocultar por enquanto. |
| Conversas | `/dashboard/atendimento/conversas` | P1 proximo | Ocultar por enquanto; base futura em admin conversations. |
| Ligacoes | `/dashboard/atendimento/ligacoes` | P2 depois | Ocultar. |
| Segurados | `/dashboard/segurados` | P1 proximo | Ocultar. |

### AUTOMACAO

| Item | Rota sugerida | Prioridade | Acao no 35D |
| --- | --- | --- | --- |
| Auxiliares | `/dashboard/auxiliares` | P1 proximo | Ocultar no menu; pode aparecer card placeholder na Home. |
| Galeria de Auxiliares | `/dashboard/auxiliares/galeria` | P1 proximo | Ocultar. |
| Execucoes | `/dashboard/auxiliares/execucoes` | P1/P2 | Ocultar. |

### AGENTES

| Item | Rota sugerida | Prioridade | Acao no 35D |
| --- | --- | --- | --- |
| Agentes de atendimento | `/dashboard/agentes` | P1 proximo | Ocultar; hoje gestao fica no Admin. |
| Personalizacao | `/dashboard/agentes/personalizacao` | P2 depois | Ocultar. |
| Playbooks | `/dashboard/playbooks` | P2 depois | Ocultar. |

### CONHECIMENTO

| Item | Rota sugerida | Prioridade | Acao no 35D |
| --- | --- | --- | --- |
| Base de conhecimento | `/dashboard/conhecimento` | P1 proximo | Ocultar; card/atalho pode apontar para admin documents se usuario tiver acesso. |
| Documentos | `/dashboard/conhecimento/documentos` | P1 proximo | Ocultar. |
| Memorias da corretora | `/dashboard/conhecimento/memorias` | P2 depois | Ocultar. |

### CANAIS

| Item | Rota sugerida | Prioridade | Acao no 35D |
| --- | --- | --- | --- |
| Seguradoras | `/dashboard/seguradoras` | P1 proximo | Ocultar; card placeholder pode citar "em breve". |
| Catalogo global | `/dashboard/catalogo` | P2 depois | Ocultar. |
| Integracoes | `/dashboard/integracoes` | P1 proximo | Ocultar; status simples na Home. |
| WhatsApp / Telefonia | `/dashboard/canais` | P1/P2 | Ocultar ate provider seguro. |

### GESTAO

| Item | Rota sugerida | Prioridade | Acao no 35D |
| --- | --- | --- | --- |
| Relatorios | `/dashboard/relatorios` | P2 depois | Ocultar. |
| Custos IA | `/admin/billing` ou futura `/dashboard/custos` | P1 proximo | Mostrar card de credito/uso simples se ja houver dados. |
| Logs | `/admin/conversation-logs` ou futura `/dashboard/logs` | P2 depois | Ocultar. |
| Equipe | `/admin/team` ou futura `/dashboard/equipe` | P1 proximo | Ocultar no tenant comum. |

### SETUP

| Item | Rota sugerida | Prioridade | Acao no 35D |
| --- | --- | --- | --- |
| Corretora | `/dashboard/corretora` | P1 proximo | Ocultar. |
| Onboarding | `/dashboard/onboarding` | P1 proximo | Mostrar alerta/card se configuracao incompleta. |
| Configuracoes | `/dashboard/configuracoes` | P0 agora | Manter rota atual. |

### Sidebar P0 para 35D

No 35D, a sidebar deve continuar simples para nao criar rotas falsas demais:

```txt
INICIO
  AutoBrokers

CONVERSAS
  Historico

SETUP
  Configuracoes
```

Opcional no 35D: exibir secoes futuras desabilitadas apenas se ficar claro visualmente que estao em breve. A recomendacao e ocultar por enquanto.

## 5. Home AutoBrokers proposta

Estrutura ideal:

```txt
[Sidebar]
  AutoBrokers
  Historico
  Configuracoes

[Topbar]
  Nome da corretora
  Status do AutoBrokers
  Creditos IA / Plano
  Usuario

[Main]
  [Hero AutoBrokers]
    AutoBrokers
    "Como posso ajudar sua corretora hoje?"
    subtitulo: "Seu copiloto operacional para seguros"

  [Chat central]
    mensagens recentes ou empty state
    input multimodal existente
    seletor de agente oculto ou travado no AutoBrokers em P0, se possivel

  [Atalhos rapidos]
    Ver atendimentos criticos
    Consultar cliente/apolice
    Preparar mensagem para cliente
    Ver historico
    Base de conhecimento
    Custos IA

  [Cards operacionais]
    Atendimentos em aberto
    Conversas recentes
    Creditos IA
    Configuracao da corretora

  [Alertas]
    Sem credito
    Nenhum agente ativo
    Base de conhecimento vazia
    Integracoes/canais ainda nao configurados

  [Proximos modulos]
    Auxiliares ativos
    Status seguradoras
    Status WhatsApp/canais
```

### Layout textual recomendado para 35D

```txt
┌──────────────────────────────────────────────────────────────┐
│ Sidebar                                                      │
│  AutoBrokers                                                  │
│  Historico                                                   │
│  Configuracoes                                               │
├──────────────────────────────────────────────────────────────┤
│ Topbar: RAFAEL SEGUROS | AutoBrokers ativo | Creditos IA      │
├──────────────────────────────────────────────────────────────┤
│ AutoBrokers                                                   │
│ Como posso ajudar sua corretora hoje?                        │
│ Seu copiloto operacional para seguros.                       │
│                                                              │
│ [Input/chat central reaproveitado]                           │
│                                                              │
│ Atalhos rapidos:                                             │
│ [Atendimentos criticos] [Preparar mensagem] [Historico]      │
│ [Base de conhecimento] [Custos IA] [Configurar corretora]    │
│                                                              │
│ Cards:                                                       │
│ [Conversas recentes] [Creditos IA] [Agente ativo] [Setup]    │
│                                                              │
│ Alertas:                                                     │
│ "WhatsApp real ainda nao conectado"                          │
│ "RAG minimo ainda nao validado"                              │
└──────────────────────────────────────────────────────────────┘
```

## 6. Cards e atalhos

### Atalhos P0

| Atalho | Acao no 35D | Dados necessarios |
| --- | --- | --- |
| Nova conversa com AutoBrokers | Focar input ou iniciar nova conversa | Estado local do chat |
| Ver historico | Link para `/dashboard/historico` | Existente |
| Preparar mensagem para cliente | Preencher prompt sugerido no input | Local |
| Ver creditos IA | Link para plano/custos se autorizado ou card local | `company-data`/billing se disponivel |
| Configuracoes | Link para `/dashboard/configuracoes` | Existente |
| Base de conhecimento | Placeholder/atalho futuro | Nenhum no P0 |

### Cards P0

| Card | Conteudo P0 | Fonte possivel | Estado vazio |
| --- | --- | --- | --- |
| Conversas recentes | Total/lista curta das ultimas conversas | `/api/conversations?limit=8` ja usado na sidebar | "Nenhuma conversa recente" |
| Creditos IA | Saldo/status simples se exposto; senao "ativo no Admin" | Futuro billing endpoint tenant | "Consulte o Admin" |
| AutoBrokers ativo | Nome do agente atual e status | `/api/agents` | "Nenhum agente ativo" |
| Setup da corretora | Checklist simples | local/com base em dados carregados | "Conexoes e RAG ainda pendentes" |

### Cards P1

| Card | Motivo para esperar |
| --- | --- |
| Atendimentos criticos | Ainda nao existe modulo tenant de atendimento. |
| Auxiliares ativos | Produto Auxiliares ainda nao modelado. |
| Status seguradoras | Precisa catalogo/integrações. |
| Status canais | WhatsApp/Evolution ainda off. |

## 7. O que fica do Smith

| Origem Smith atual | Decisao |
| --- | --- |
| `/dashboard/chat` | Reaproveitar como nucleo do AutoBrokers. |
| `InputArea` / `AnimatedAIChat` | Reaproveitar como caixa de mensagem P0. |
| `MessageBubble` | Reaproveitar para mensagens. |
| `UnifiedSidebar` | Reaproveitar, mas reorganizar menu gradualmente. |
| `Historico` | Manter como historico do AutoBrokers. |
| `Configuracoes` | Manter como configuracoes pessoais. |
| Seletor de agente | Manter tecnicamente, mas considerar ocultar/travar no AutoBrokers para usuario comum. |
| Web search toggle | Manter se empresa permitir, mas nao destacar no P0. |
| Imagem/audio | Manter, pois ja existe. Nao expandir escopo. |
| Widget/embed | Manter fora da Home P0. |

O que descartar da home atual:

- Texto "Sua conta esta ativa e pronta para usar".
- Lista "Chat com IA ilimitado", "Mensagens de texto e voz", etc.
- Botao isolado "Ir para o Chat".
- Layout de boas-vindas separado do AutoBrokers.

## 8. O que entra do AutoBrokers antigo

Sem copiar codigo, os conceitos uteis entram assim:

| Conceito antigo | Entrada no novo produto | Fase |
| --- | --- | --- |
| Cards de atendimento | Cards operacionais da Home e modulo Atendimento | P1 |
| Fila | Menu Operacao > Fila de atendimentos | P1 |
| Casos | Menu Operacao > Casos | P1 |
| Conversas externas | Menu Operacao > Conversas, separado do AutoBrokers | P1 |
| Ligacoes | Menu Operacao > Ligacoes | P2 |
| Segurados | Menu Operacao > Segurados | P1 |
| Seguradoras | Menu Canais > Seguradoras | P1 |
| Catalogo global | Menu Canais > Catalogo global | P2 |
| Integracoes | Menu Canais > Integracoes | P1 |
| Equipe | Menu Gestao > Equipe | P1 |
| Agentes | Menu Agentes > Agentes de atendimento | P1 |
| Configuracoes da corretora | Menu Setup > Corretora/Configuracoes | P1 |

Regra: esses conceitos devem virar telas e dados novos dentro do runtime AutoBrokers, nao import de pastas antigas.

## 9. O que fica para fase 2

Fora do 35D:

- Atendimento real com fila/casos.
- Auxiliares ativos e galeria.
- Execucoes de Auxiliares.
- RAG minimo e documentos.
- Docling.
- Worker/Celery.
- WhatsApp/Evolution.
- InfoCap/n8n real.
- Seguradoras e corredores.
- Connection Vault.
- Dashboards analiticos.
- Insights automaticos.
- Personalizacao avancada.

## 10. Plano do proximo batch 35D

Nome recomendado:

```txt
BATCH_35D_AUTOBROKER_HOME_PATCH
```

Objetivo:

Implementar a primeira Home AutoBrokers em `/dashboard`, reutilizando a logica de chat atual sem quebrar `/dashboard/chat`.

### Escopo permitido no 35D

Arquivos provaveis:

- Modificar: `app/dashboard/page.tsx`
- Modificar: `components/UnifiedSidebar.tsx`
- Opcional criar: `components/dashboard/AutoBrokersHomeShell.tsx`
- Opcional criar: `components/dashboard/OperationalCard.tsx`
- Opcional criar: `components/dashboard/QuickActionButton.tsx`

O 35D deve evitar mexer no backend, Supabase, migrations e integrações.

### Tarefas bite-sized

#### Task 1 - Preparar Home shell

**Files:**

- Modify: `app/dashboard/page.tsx`
- Optional create: `components/dashboard/AutoBrokersHomeShell.tsx`

**Steps:**

1. Substituir a tela de boas-vindas atual por shell com sidebar e area principal.
2. Carregar `userId`, `userName` e dados basicos da corretora via APIs ja usadas.
3. Mostrar titulo `AutoBrokers`.
4. Mostrar subtitulo `Como posso ajudar sua corretora hoje?`.
5. Nao integrar dados novos ainda.

**Validation:**

```bash
npm run typecheck
```

Expected: exit 0.

#### Task 2 - Reaproveitar chat central

**Files:**

- Modify: `app/dashboard/page.tsx`
- Possibly extract from: `app/dashboard/chat/page.tsx`

**Steps:**

1. Evitar duplicar toda a logica do chat se possivel.
2. Se extrair componente, criar componente compartilhado para chat runtime.
3. Manter `/dashboard/chat` funcionando.
4. O input da Home deve enviar mensagem para o mesmo `/api/chat/stream`.

**Validation:**

```bash
npm run typecheck
```

Manual: abrir `/dashboard` e enviar mensagem simples.

#### Task 3 - Atalhos rapidos P0

**Files:**

- Modify/create under `components/dashboard/*`

**Steps:**

1. Criar atalhos visuais simples.
2. Linkar apenas rotas existentes: `/dashboard/historico`, `/dashboard/configuracoes`, `/dashboard/chat`.
3. Atalhos futuros devem preencher prompt ou mostrar estado "em breve", nao navegar para rota inexistente.

**Validation:**

Manual: clicar atalhos e confirmar que nao ha 404.

#### Task 4 - Cards operacionais P0

**Files:**

- Modify/create under `components/dashboard/*`

**Steps:**

1. Criar 4 cards:
   - Conversas recentes.
   - AutoBrokers ativo.
   - Creditos IA.
   - Setup da corretora.
2. Usar dados ja disponiveis quando simples.
3. Onde nao houver endpoint seguro, usar estado vazio honesto.

**Validation:**

Manual: `/dashboard` renderiza com dados/estados vazios sem tela branca.

#### Task 5 - Sidebar P0

**Files:**

- Modify: `components/UnifiedSidebar.tsx`

**Steps:**

1. Trocar item `Chat` por `AutoBrokers` apontando para `/dashboard`.
2. Manter `Historico`.
3. Manter `Configuracoes`.
4. Garantir que nova conversa ainda funciona e leva ao contexto AutoBrokers.

**Validation:**

Manual: navegação sidebar sem 404.

#### Task 6 - Checks e commit

**Commands:**

```bash
npm run typecheck
npm run build
git diff --check
```

Se build local exigir env, usar apenas env dummy no processo e registrar.

**Commit:**

```bash
git add app/dashboard components/UnifiedSidebar.tsx components/dashboard
git commit -m "feat(product): introduce AutoBrokers tenant home"
git push origin main
```

### Criterios de sucesso do 35D

- `/dashboard` abre como AutoBrokers Home.
- `/dashboard/chat` continua funcionando.
- Chat responde.
- Sidebar mostra AutoBrokers, Historico e Configuracoes.
- Nao existe "Estudos".
- Nao existe "Conversa ao vivo".
- Nenhum modulo futuro abre 404 por link P0.
- Typecheck passa.


# BATCH 35D - AutoBrokers Tenant Home

Date: 2026-06-05
Scope: first tenant Home patch for `/dashboard`.
Repository: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-Intelligence-OS`

## 1. Resumo executivo

O `/dashboard` deixou de ser uma tela simples de boas-vindas e passou a ser a primeira Home AutoBrokers da corretora.

A entrega e P0 e conservadora: chat-first, com dados leves ja existentes, atalhos seguros e cards honestos. O streaming e a experiencia completa de conversa continuam preservados em `/dashboard/chat`.

Nao houve mudanca em Supabase schema, migrations, RAG, Worker, Docling, WhatsApp, InfoCap, n8n, corredores, Agent OS V2, Auxiliares reais, billing real, Stripe real ou EasyPanel.

## 2. Arquivos alterados

| Arquivo | Alteracao |
| --- | --- |
| `app/dashboard/page.tsx` | Substitui a tela antiga pela Home AutoBrokers. |
| `app/dashboard/chat/page.tsx` | Consome uma mensagem inicial vinda da Home via `sessionStorage`, sem duplicar streaming. |
| `app/dashboard/historico/page.tsx` | Evita query param profundo que o chat ainda nao consome; abre o chat atual de forma segura. |
| `components/UnifiedSidebar.tsx` | Sidebar P0 com grupos Inicio, Conversas e Setup. |
| `docs/audits/35D-home.md` | Relatorio do batch. |

## 3. Como ficou `/dashboard`

Nova estrutura:

1. Topbar discreta com nome da corretora, usuario e status do AutoBrokers.
2. Hero AutoBrokers com:
   - titulo `AutoBrokers`;
   - subtitulo `Seu copiloto operacional para seguros`;
   - frase `Como posso ajudar sua corretora hoje?`.
3. Entrada principal de chat.
4. Atalhos rapidos.
5. Cards de agente, creditos e setup.
6. Historico recente.
7. Status simples de Chat, LLM, Base de conhecimento e Integracoes.

O input da Home nao duplica o motor de streaming. Ao enviar, ele salva a mensagem em `sessionStorage` e redireciona para `/dashboard/chat`, onde a mensagem e enviada pelo fluxo ja funcional.

## 4. Como ficou `/dashboard/chat`

O chat foi preservado.

Mudanca pequena:

- quando existir `autobrokers.homePrompt` no `sessionStorage`, o chat aguarda usuario, empresa, agente ativo e estado de loading estarem prontos;
- consome a mensagem uma unica vez;
- envia pelo mesmo `handleSendMessage` ja usado no chat.

Sem alteracao no endpoint `/api/chat/stream`, no backend FastAPI ou na logica de billing/credits.

## 5. Sidebar final P0

Sidebar tenant agora expõe apenas:

```txt
INICIO
- AutoBrokers -> /dashboard

CONVERSAS
- Historico -> /dashboard/historico

SETUP
- Configuracoes -> /dashboard/configuracoes
```

O botao `Nova Conversa` foi mantido e segue apontando para `/dashboard/chat`.

## 6. Atalhos criados

Ativos:

- Abrir chat do AutoBrokers -> `/dashboard/chat`
- Ver historico -> `/dashboard/historico`
- Configuracoes -> `/dashboard/configuracoes`

Desabilitados/honestos:

- Preparar mensagem para cliente -> em breve
- Consultar cliente/apolice -> em breve
- Base de conhecimento -> em breve

## 7. Cards criados

Cards principais:

- Agente principal
- Creditos IA
- Setup da corretora

Status operacionais:

- Chat
- LLM
- Base de conhecimento
- Integracoes

## 8. Dados reais usados vs placeholders

Dados reais usados:

- `/api/user/profile`: usuario e nome da corretora;
- `/api/agents`: agente ativo da corretora;
- `/api/conversations?limit=5`: conversas recentes;
- `/api/billing/subscription`: saldo/plano/creditos quando disponivel.

Placeholders honestos:

- Base de conhecimento: `Em configuracao`;
- Integracoes: `Em breve`;
- Acoes de atendimento/apolice/documentos: botoes desabilitados.

Nao foram inventadas metricas de atendimento, apolices, seguradoras, Auxiliares ou canais.

## 9. O que ficou para 35E/35F

Ficou fora deste patch:

- RAG minimo e upload de documento;
- Home com dados reais de atendimento;
- Auxiliares reais;
- galeria de Auxiliares;
- status real de seguradoras/canais;
- Evolution/WhatsApp;
- InfoCap/n8n;
- Worker/Docling;
- roteamento profundo de conversa especifica a partir do historico.

## 10. Checks executados

Executados durante o batch:

- `rg -n "JARVYS|Jarvys|jarvys|AutoBroker\\b|Smith AI|Agent Smith|Sistema Smith|Bem-vindo ao Smith|Smith$" app components lib public backend --glob '!node_modules' --glob '!.next'`
- `npm run typecheck`

Checks finais obrigatorios executados antes do commit:

- `git diff --check`
- `npm run typecheck`
- `npm run build`

## 11. Testes manuais pos-deploy

Depois de redeploy Web:

1. Abrir `/dashboard`.
2. Confirmar Hero `AutoBrokers`.
3. Confirmar sidebar com AutoBrokers, Historico e Configuracoes.
4. Enviar uma mensagem pelo input da Home e verificar redirecionamento para `/dashboard/chat`.
5. Confirmar resposta do chat.
6. Abrir `/dashboard/chat` diretamente.
7. Abrir `/dashboard/historico`.
8. Abrir `/dashboard/configuracoes`.

## 12. Riscos restantes

| Risco | Severidade | Observacao |
| --- | --- | --- |
| Historico ainda nao abre conversa especifica | P2 | Para evitar link morto, itens abrem o chat atual. Roteamento por conversa deve ser batch dedicado. |
| Cards ainda sao leves | P2 | Intencional para P0; dados reais de atendimento entram depois. |
| Base de conhecimento aparece como em configuracao | P1/P2 | RAG minimo ainda nao foi validado neste produto. |
| Integracoes/canais em breve | P1/P2 | WhatsApp/InfoCap/n8n seguem desligados por seguranca. |
| Home envia prompt via `sessionStorage` | P3 | Solucao simples e local para preservar o fluxo de chat sem duplicar streaming. |

## 13. Proximo batch recomendado

Proximo passo recomendado:

```txt
BATCH_35E_RAG_MINIMAL_SMOKE
```

Objetivo: validar upload/documento pequeno, MinIO/Qdrant e primeira resposta do AutoBrokers com base de conhecimento real.

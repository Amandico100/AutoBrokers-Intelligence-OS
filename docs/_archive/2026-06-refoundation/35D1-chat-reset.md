# BATCH 35D1 - Chat First Reset

Date: 2026-06-06
Scope: reset rejected tenant Home from batch 35D.
Repository: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-Intelligence-OS`

## 1. Resumo executivo

O batch 35D criou uma Home de corretora com hero, cards, status, creditos, historico e atalhos. Essa direcao foi reprovada.

Este patch remove a Home ruim e deixa `/dashboard` como entrada direta para a experiencia principal de chat do AutoBrokers. O objetivo agora e estabilidade e limpeza, nao redesign.

## 2. O que foi removido

- Tela `/dashboard` com titulo `Home da corretora`.
- Hero e blocos de status criados no 35D.
- Cards grandes de agente, creditos, setup, historico e status operacional.
- Atalhos para modulos futuros/desabilitados.
- Ponte por `sessionStorage` que enviava prompt da Home para o chat.
- Relatorio antigo `docs/audits/35D-home.md`, que documentava a direcao reprovada.

## 3. Arquivos alterados

| Arquivo | Alteracao |
| --- | --- |
| `app/dashboard/page.tsx` | Agora renderiza diretamente a experiencia de chat existente. |
| `app/dashboard/chat/page.tsx` | Remove bridge de prompt via `sessionStorage` criada para a Home ruim. |
| `docs/audits/35D-home.md` | Removido por documentar direcao reprovada. |
| `docs/audits/35D1-chat-reset.md` | Novo relatorio do reset. |

## 4. `/dashboard` agora e chat-first

`/dashboard` importa e renderiza o mesmo componente de `/dashboard/chat`.

Isso garante:

- uma unica experiencia principal de conversa;
- zero duplicacao de streaming;
- zero dashboard de cards;
- menos superficie para bug antes do Claude Design definir UX final.

## 5. Chat preservado

O fluxo funcional de chat foi preservado:

- carregamento de usuario;
- carregamento de empresa;
- carregamento de agentes;
- conversas recentes no sidebar quando em chat;
- envio de mensagem;
- streaming via `/api/chat/stream`;
- mensagens antigas;
- nova conversa.

`/dashboard/chat` continua existindo para preservar links atuais.

## 6. Sidebar P0

A sidebar permanece minimalista:

```txt
INICIO
- AutoBrokers

CONVERSAS
- Historico

SETUP
- Configuracoes
```

Nao foram adicionados Atendimento, Auxiliares, Personalizacao, Seguradoras, Conectores, Conhecimento, Relatorios ou Equipe.

## 7. Fora do escopo confirmado

Nao houve alteracao em:

- RAG;
- Docling;
- Worker/Celery;
- Supabase schema;
- migrations;
- billing real;
- Stripe real;
- MinIO;
- Qdrant;
- Redis;
- WhatsApp;
- InfoCap;
- n8n;
- corredores;
- Agent OS V2;
- EasyPanel.

## 8. Checks executados

| Check | Resultado | Observacao |
| --- | --- | --- |
| `rg` de nomes antigos | OK com sobras tecnicas | Encontrou apenas `Agent Smith` em migrations historicas. |
| `npm run typecheck` | OK | `tsc --noEmit` concluiu sem erro. |
| `git diff --check` | OK | Apenas avisos CRLF nos arquivos alterados. |
| `npm run build` | OK com env dummy local | Build concluiu sem gravar `.env` e sem segredo real. |

Avisos esperados:

- SendGrid nao configurado no sandbox.
- Browserslist/caniuse-lite desatualizado.

## 9. Testes manuais pos-deploy

Depois de redeploy Web:

1. Abrir `/dashboard`.
2. Confirmar que aparece a experiencia limpa de chat do AutoBrokers.
3. Confirmar que nao aparece `Home da corretora`.
4. Confirmar que nao aparecem cards de creditos/setup/status/historico do 35D.
5. Abrir `/dashboard/chat`.
6. Enviar uma mensagem no chat e confirmar resposta.
7. Abrir `/dashboard/historico`.
8. Abrir `/dashboard/configuracoes`.

## 10. Proximo passo recomendado

Preparar um **Claude Design / UX Architecture Brief** antes de qualquer nova tentativa de layout.

O proximo trabalho visual deve definir:

- experiencia chat-first final;
- sidebar;
- sistema visual;
- empty state;
- modulos futuros;
- arquitetura de telas;
- regras de navegacao.

# SPEC-043 — Central de Atendimentos do corretor (dashboard, mobile-first)

> Aprovada pelo founder em 19/07/2026 (noite). Objetivo: o corretor acompanha
> TODOS os atendimentos na palma da mão, em linguagem humana, com estágios
> coloridos e mudança automática de etapa SEM custo (dados que já existem).
> Pronto ANTES do pareamento de 20/07 — quando os dados chegarem, tudo enche.

## Diagnóstico (auditoria 19/07)

- **Fila** e **Casos** rodavam o MVP sandbox antigo (attendance_cases,
  "Criar caso teste", dry-run) — linguagem de teste, não de produção.
- **Segurados**: placeholder vazio.
- **Conversas**: excelente no desktop, SEM modo mobile (2 colunas espremidas)
  e sem o wrapper padrão de padding/scroll (topo desalinhado das demais).
- Fontes REAIS já existentes: `conversations` (cliente↔atendente, com posse/
  claim), backend `/api/dispatch/active` (acionamentos ao vivo c/ transcript),
  espelhos persistentes (`conversations` session dispatch:%),
  `attendance_sessions` (observação humana — Espelho, PII da própria
  corretora). NADA novo de LLM: pipeline 100% determinístico.

## O pipeline do atendimento (estágios em linguagem humana + cor)

| Estágio | Cor | Fonte |
|---|---|---|
| 🔴 Precisa de você | vermelho | conversa HUMAN_REQUESTED ou acionamento needs_human |
| 🔵 Acionando a seguradora | azul | dispatch ura/human_phase/preparing |
| 🟢 Protocolo garantido | verde | dispatch captured |
| 🟢 Acompanhando o prestador | verde | dispatch monitoring |
| 🔵 Em conversa | azul suave | conversa ativa com o atendente IA |
| 🟡 Com a equipe | âmbar | conversa assumida por humano da corretora |
| ⚪ Atendimento humano (observação) | neutro | attendance_sessions abertas (pós-pareamento) |
| ⚫ Concluído | cinza | conversas/sessões encerradas |

Mudança de estágio = automática e grátis (estado real do sistema, poll 10s).
Score/baseline interno NUNCA aparece para a corretora (decisão do founder).

## Entregas

1. **API** `GET /api/dashboard/atendimentos` (Next, sessão trava a company):
   pipeline unificado — conversas + acionamentos ativos (backend) + espelhos
   recentes + sessões de observação; item por cliente com estágio calculado.
2. **API** `GET /api/dashboard/atendimentos/segurados`: clientes derivados dos
   atendimentos (nome/telefone/nº de atendimentos/último contato).
3. **Fila** → pipeline ao vivo mobile-first: seções por estágio (urgente no
   topo), cards humanos ("Guincho com a Porto — protocolo garantido às
   14:32"), toque abre a conversa. Sem "caso teste", sem jargão.
4. **Casos** → **Histórico**: todos os atendimentos e acionamentos com busca
   e filtro por desfecho; toque abre a conversa/espelho.
5. **Segurados** → lista real derivada (busca, contato, últimos atendimentos).
6. **Conversas**: wrapper padrão (padding/scroll alinhado às demais páginas) +
   **modo WhatsApp no mobile** (lista OU thread em tela cheia, botão voltar,
   100dvh) + deep-link `?open=<id>` (a Fila/Histórico abrem direto a thread).
7. Bug fix (teste A do founder): tools `resumo_atendimentos`/`atlas_rotas`/
   `buscar_veiculo` ganharam ponte sync→async real (o runtime chamava o
   caminho síncrono e vazava "consulta deve ser assíncrona").

## Regras

- Linguagem 100% humana nas superfícies do corretor; nomes de papel.
- Mobile-first: uma coluna, toque grande, sem scroll horizontal.
- Legado attendance_cases (sandbox) sai das rotas visíveis; código fica
  (nada deletado hoje), rotas passam a renderizar as superfícies novas.
- tsc + bateria + deploy api+web + smoke antes de reportar.

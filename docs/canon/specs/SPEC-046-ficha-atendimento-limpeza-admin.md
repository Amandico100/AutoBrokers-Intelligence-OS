# SPEC-046 — Ficha do Atendimento, limpeza do legado e Admin completo

> Aprovada pelo founder em 20/07/2026. Fecha os três buracos restantes:
> (1) clicar num atendimento/segurado abre uma FICHA rica, não a conversa
> crua; (2) o código do MVP antigo de casos (morto) sai do repositório;
> (3) o portal admin volta a dar acesso à configuração completa da empresa.

## 1. Ficha do Atendimento (o "dossiê vivo" para o corretor)

Nova rota `/dashboard/atendimentos/ficha/[conversaId]` (painel lateral no
desktop, tela cheia no mobile). Fila, Histórico e Segurados passam a abrir a
FICHA; a conversa completa vira um botão dentro dela. Conteúdo (100%
determinístico/já-gerado — zero custo novo de LLM):

- **Cabeçalho**: cliente (nome/telefone), estágio colorido atual, quando.
- **Resumo mastigado**: o que aconteceu em 1-3 frases (fonte: destilado do
  Espelho quando houver; senão montado por regras: serviço + seguradora +
  desfecho + protocolo).
- **Dados do segurado e apólice** (InfoCap read-only, quando identificado):
  titular, apólice, seguradora, vigência, veículo/placa.
- **Linha do tempo de EVENTOS** (não a conversa): pediu ajuda → identificado →
  acionou {seguradora} → protocolo {N} → prestador a caminho → concluído /
  entregue à equipe (fonte: agent_activities + estado do dispatch).
- **Anexos**: fotos/PDFs/áudios que o cliente enviou (messages.image_url/
  audio_url + documentos), em grade com preview.
- **Dossiê de handoff** (quando foi para humano): o dossiê REAL do dispatch
  (build_handoff_dossier), copiável.
- **Ações**: Abrir conversa · Assumir · (se acionamento) ver replay.
- API: `GET /api/dashboard/atendimentos/ficha/[id]` (Next, sessão trava
  company) agregando conversations+messages+dispatch/Redis+activities+
  scorecard-livre (nota interna NUNCA aparece — decisão do founder).
- Segurados: clique abre um perfil leve (dados + lista de atendimentos →
  fichas), não mais a conversa direto.

## 2. Limpeza do legado (código 100/100, sem macarrão)

Morto confirmado na auditoria (nada em produção grava/usa):
- Frontend: `app/dashboard/atendimentos/casos/[caseId]/*` (CaseDetailClient,
  Simulator, HandoffDossierPanel antigos), `CasesIndexClient.tsx`,
  `lib/attendance/*` (runtime TS do MVP) — REMOVER após grep de referências.
- APIs Next: `app/api/attendance/cases/*` e rotas runtime dry-run/sandbox
  associadas — REMOVER (verificando antes, por grep, que nenhuma superfície
  viva chama; o fluxo real usa graph + dispatch, não passa por aqui).
- Backend: endpoint órfão que só serve o fluxo morto (attendance_agent_reply
  SÓ se confirmado sem chamadas vivas) — remover ou marcar deprecated.
- Banco: `attendance_cases` e tabelas exclusivas do MVP morto → EXPORT de
  backup (CSV no storage) + DROP em migração própria e reversível.
- Regra: cada remoção entra num commit separado com a prova (grep) na
  mensagem. Bateria completa após cada leva.

## 3. Portal Admin — devolver a visão completa

- **Bug do menu**: itens com submenu passam a NAVEGAR para o próprio href no
  clique (além de expandir) — corrige o "sumiço" de /admin/companies.
- **Cockpit completo**: entrada clara "Configuração completa" no Cockpit da
  corretora (/admin/corretoras) levando à tela real
  `/admin/companies/[id]/agents` (Identidade, HTTP Tools, MCP, WhatsApp,
  Agentes, Subagentes via AgentConfigModal — que JÁ existe e funciona).
  Não reescrever o modal; dar o caminho de volta + título/breadcrumb claros.
- Item de menu "Corretoras" ganha sub-item explícito "Empresas & Agentes"
  (→ /admin/companies).

## Invioláveis
- Ficha não expõe nota/score interno à corretora.
- Nenhuma estrutura paralela: a Ficha agrega fontes existentes.
- Remoções sempre com prova de morte (grep) + backup antes de DROP.

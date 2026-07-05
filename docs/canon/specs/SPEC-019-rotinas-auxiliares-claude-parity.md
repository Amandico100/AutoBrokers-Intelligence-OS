# SPEC-019 — Rotinas & Auxiliares: paridade com Claude Rotinas + reorganização

**Autor**: Fable (líder técnico) · 2026-07-05 · **Status**: pronta para execução por chat novo
**Leia antes**: memória `onda2-discovery-2026-07.md` (RODADAS 15-16) e `project-autobrokers-context.md`.

## Visão (palavras do founder)
Rotinas = Claude Rotinas para corretoras. O Chat Principal cria/edita/gerencia rotinas POR
CONVERSA (estilo Hermes) E existe UI manual completa (criar, editar horário/destino/prompt,
pausar, excluir). Se faltar peça (WhatsApp desconectado, conector ausente), o chat EXPLICA
passo a passo o que o corretor deve conectar antes. Galeria de rotinas prontas (ex.: Cobrança)
que o corretor liga com 1 clique.

## O que JÁ existe e é REAL (usar, não recriar)
- Motor: `backend/app/services/routine_engine.py` — agenda daily/interval (testes
  `test_f2_routines.py` 14/14), executor = `LangChainService.process_message` (cérebro único,
  session `routine:<id>`), entrega whatsapp/none, claim atômico, 5 falhas → auto-desativa,
  scheduler asyncio no lifespan (`ROUTINES_ENGINE_ENABLED`).
- Tabelas: `routines`, `routine_runs` (migration `20260705_01_f2_routines.sql`, APLICADA).
- Tools do chat (role core, em graph.py): `create_routine`, `list_routines`
  (`backend/app/agents/tools/routine_tools.py`).
- UI mínima: `/dashboard/auxiliares/rotinas` (lista/pausa/exclui/execuções) +
  API `/api/dashboard/rotinas`.
- Entrega whatsapp: usa QUALQUER integração ativa da company (fix RODADA-16b).

## O que é MOCK/GAMBIARRA (não construir em cima)
- `lib/mock/tenant-modules.ts` (`auxiliaresAreas`, `auxiliaresGaleria`) — dados fake das
  páginas /dashboard/auxiliares/{galeria,meus,execucoes}. As páginas exibem mas o fluxo
  "instalar template → motor isolado" (Admin → Auxiliares Globais/Blueprint Studio) é
  PARALELO ao motor de rotinas. DECISÃO: rotinas do motor F2 são O caminho; a galeria de
  auxiliares vira CATÁLOGO DE ROTINAS PRONTAS (templates de routine, não agents novos).
  Blueprint Studio (Admin) continua para AGENTES (atendente/core custom), não para rotinas.

> **EXECUTOR**: Opus 4.8 — leia ANTES `docs/canon/EXECUTION-GUIDE-OPUS.md` (obrigatório).
> **STATUS 2026-07-05 (Fable)**: Fases **A e B FEITAS e deployadas** (main pós-`d009f6f`):
> `manage_routine` (pause/activate/delete/update), pré-check instrutivo no create
> (routine_engine.describe_missing_dependency + query integrations), prompt proativo no
> CORE (oferece transformar pedido repetível em rotina) + formatação analista p/ apólices,
> UI "Nova rotina"/editar (modal em `/dashboard/auxiliares/rotinas`, actions create/update
> na API). Entrega prefere integração purpose=auxiliary (número dedicado) > attendance.
> **Executar: C, D e E abaixo.**

## Decisões novas do founder (2026-07-05) — incorporar
1. **Número dedicado p/ rotinas/outreach**: backend JÁ prioriza purpose=auxiliary. FALTA UI:
   no modal do canal WhatsApp (`components/vault/WhatsAppChannelModal.tsx` → passo Evolution),
   permitir parear um SEGUNDO número com `purpose=auxiliary` (o backend
   `/api/whatsapp-channel/setup` já aceita `purpose` — instância vira `ab-<cid12>-auxiliary`).
   Respostas RECEBIDAS nesse número: hoje caem no atendente normal — para outreach
   conversacional (lead de concessionária) isso é DESEJADO no futuro, mas até lá o webhook
   deve rotear inbound de integração purpose=auxiliary para o MESMO fluxo (ok) — documentar.
2. **Memória própria por rotina**: o session_id `routine:<id>` JÁ dá thread persistente no
   checkpointer (memória entre execuções existe!). Adicionar: coluna `routines.knowledge`
   (text, expand) editável na UI/tool — conteúdo injetado no render_task_prompt como
   "CONHECIMENTO DA ROTINA" (ex.: argumentos de venda, FAQ do produto). Rotinas complexas
   (outreach) usam isso.
3. **Proatividade**: feita via prompt; medir depois (F4).

## Entregáveis (fases pequenas, deploy por fase)
### A — Tools completas do chat — ✅ FEITA (Fable)
1. `update_routine` (id + campos parciais: name/instructions/schedule/delivery),
   `pause_routine`, `delete_routine` — mesmas validações de `create_routine`.
2. `create_routine` PRÉ-CHECA dependências e responde INSTRUTIVO quando faltar:
   - delivery whatsapp → existe integração ativa? Se não: "Conecte em Personalização →
     Conectores → WhatsApp (QR)" (texto pronto no tool result).
   - instruções que exigem web → `platform.web.search` ativa? Se não, avisar que a rotina
     rodará sem web e o resultado pode ser pobre (não bloquear).
3. Testes house (`test_spec019_routine_tools.py`): validações puras, mensagens instrutivas.

### B — UI paridade Claude — ✅ FEITA no essencial (Fable); pendente: chips de conectores no modal (item 2 abaixo)
1. `/dashboard/auxiliares/rotinas`: botão **Nova rotina** + edição inline (modal): nome,
   instruções (textarea), agenda (daily hora+dias | interval), entrega (whatsapp nº — mostrar
   status do canal; none), ativa/pausada. POST/PATCH na API existente (adicionar action
   `update`/`create` no route.ts — validar espelhando routine_engine.validate_schedule em TS).
2. Card "Conectores usados" informativo no modal (ler `/api/dashboard/conversas`-style:
   canal whatsapp ativo? web search? InfoCap?) — chips como no print do ChatGPT do founder.
3. Execuções: página `runs` com filtro por rotina (tabela started/status/preview/erro).

### C — Galeria de rotinas prontas (1 sessão)
1. Tabela `routine_templates` (global): name, description, category, instructions,
   schedule_default, delivery_default, required: {whatsapp: bool, web: bool, infocap: bool,
   portal: bool}. Migration expand + seed inicial: "Notícias do setor (diária 8h)",
   "Resumo do dia do agente (18h)", "Cobrança de boletos (diária 9h — requer portal, DESATIVADA
   até SPEC-020)".
2. `/dashboard/auxiliares/galeria` passa a listar routine_templates REAIS (substituir mock);
   "Usar modelo" → pré-preenche o modal de Nova rotina; checa `required` e mostra o que falta
   com link direto (ex.: conectar WhatsApp).
3. Admin (master): CRUD de routine_templates em Auxiliares Globais (aba nova "Rotinas prontas").

### D — Robustez do executor (1 sessão)
1. `channel="routine"` no process_message: pular buffer/humanização de balões? NÃO — entrega
   whatsapp JÁ divide balões (bom). Adicionar timeout por execução (ex. 180s) via asyncio.wait_for.
2. Relatório diário do agente (rotina de sistema opcional por corretora): template na galeria.
3. `routine_runs` retenção: job semanal apaga >90 dias (dentro do próprio scheduler).

### E — Memória/conhecimento por rotina (novo — founder 05/07)
1. Migration expand: `alter table routines add column if not exists knowledge text;`
2. `render_task_prompt`: se knowledge não-vazio, bloco "### CONHECIMENTO DA ROTINA\n{...}"
   antes das instruções (teste house: presença condicional).
3. UI modal: textarea "Conhecimento (opcional)" + `manage_routine` aceita campo knowledge.
4. Caso de uso alvo: auxiliar de outreach da concessionária (argumentos, objeções, FAQ).

## Regras
- TDD house-style (python standalone, "->" ASCII). Expand-only no banco (APPLY/VERIFY/ROLLBACK
  no header). Sem novos "motores" paralelos: TUDO roda pelo process_message.
- PII: nunca dados do sócio Rafael em fixtures/commits.
- Deploys: gatilhos EasyPanel (tokens com o founder; pedir a ele — foram regenerados? ver memória).

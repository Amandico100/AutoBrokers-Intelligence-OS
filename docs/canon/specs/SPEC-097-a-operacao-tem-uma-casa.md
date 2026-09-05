# SPEC-097 · A OPERAÇÃO TEM UMA CASA — o atendimento sabe onde está, quem cuida, de quem espera e como terminou

> **O que ela entrega:** (1) 🔴 **o desfecho deixa de ser deduzido do relógio**: hoje a Fila rotula **584 de 668 conversas (87,4%)** como
> "Atendimento encerrado" e 📊 `resolvido_em` está NULL em 728/728 — ninguém encerrou nada; a tela deduziu do silêncio de 48 h e o mesmo
> JSON diz `semana.terminaram: 0`. Nasce o estado **PARADO** (distinto de ENCERRADO) e o escritor de `resolvido_em` passa a disparar;
> (2) **o dono deixa de ser o status**: o único escritor de `claimed_by` grava `status='HUMAN_REQUESTED'` junto, e a cascata testa o status
> antes do dono — a coluna "com a equipe" é inalcançável; (3) **o caso é o EPISÓDIO, não a conversa**: 📊 1 telefone = 1 conversa perpétua
> (até 1.326 mensagens, 29 dias) e o mesmo contato gera 5,8 episódios (`attendance_sessions`, 12.755 linhas, sem `conversation_id`) — a
> proposta ancorava o caso na conversa, e `work_waits` já errou por essa âncora (0 linhas na vida); (4) **um read model, sem teto**: a Fila
> lê 120 de 448 conversas da AutoFleet e a busca de Casos é `filter()` no cliente — buscar um protocolo de 60 dias devolve "nada" (falso zero);
> Lista e Quadro passam a chamar UMA função, com paginação e busca no banco; (5) **o "AGORA" e a timeline com hora**: situação, dono, de
> quem espera, há quanto tempo, atenção, próxima ação — só sobre o que EXISTE no banco (sem SLA inventado, sem LLM), e os 6 de 9 tipos de
> evento da Ficha que hoje têm `at: null` ganham hora e fonte.
>
> **v1.1 · 05/09/2026 · protocolo v11.2 + opção B (três marchas) · marcha CRÍTICO** · v1.0 + aquecimento (Opus, 160 mil tokens: **nota 74 → 18 emendas E1–E18
aplicadas**; as duas falsas assinadas — 656 e `.limit(200)` — refutadas por comando; U4 e U6.3 saíram por orçamento; E6 obrigatória entrou como U2.3) (piso da §3.2: escrita no ciclo de vida do atendimento em
> produção — `resolvido_em`, `claimed_by`, `work_waits`, e uma migration expand-first) · nasce da proposta
> `specs-propostas/SPEC-097-a-operacao-tem-uma-casa.md` (03/09, 722 linhas; RP0: research pack SHA-256 `26fda881…4ad0` CONFERE, HEAD da proposta
> `67506906` envelhecido) + o research pack (45 KB) + a medição de 05/09 (investigador/pesquisador, 193 mil tokens). 📊 Nota do investigador para a
> proposta, para o que o corretor precisa: **62/100** — *"é uma SPEC de LEITURA para um problema de ESCRITA: projetar melhor um banco que ninguém
> escreve produz uma tela mais bonita que mente com mais confiança."* A proposta é ponto de partida; o que saiu está na §5 com o gatilho.
> Branch `feat/spec097-casa` · base `origin/main` = `7f3f3eb`.

---

## 0. O TESTE DO PRODUTO

> **Segunda, 08:30, a dona da Resulta abre Atendimentos. A Fila não tem 584 "encerrados" fantasmas: tem 7 em conversa, 3 PARADOS há mais de um
> dia (um deles espera a seguradora desde sexta — e a Fila diz "esperando a seguradora · 2d 14h", porque a espera foi ESCRITA quando o
> corredor a abriu), 1 que pediu uma pessoa, e 1 que a Ana assumiu ontem — e esse aparece em "com a equipe", com o nome dela, não em "pediu
> uma pessoa". Ela clica no que espera a seguradora: o AGORA diz situação, dono (ninguém), de quem espera (Porto, protocolo 8821…),
> há quanto tempo, e a próxima ação ("cobrar o protocolo — vence hoje 18h" só porque existe um prazo escrito; sem prazo, "sem prazo declarado").
> A timeline tem hora em TODO evento, cada um com a fonte (conversa, corredor, trabalho, aprovação). Ela busca o protocolo de um sinistro de
> abril: aparece — o caso é o episódio de abril daquele segurado, não a conversa perpétua dele; o mesmo telefone tem 5 episódios e os 5 estão
> em "Casos", cada um com o seu desfecho. Ela clica "Encerrar" num caso resolvido pelo segurado: `resolvido_em` e o motivo entram no banco,
> o caso sai da Fila ativa e fica em Encerrados, e `semana.terminaram` conta 1. Nada foi deduzido do relógio. Nada veio de um modelo.**

⛔ Qualquer bloco que não sirva a esse parágrafo sai desta SPEC.
⛔ Nenhuma superfície nova sobre tabela sem ESCRITOR (📊 `work_waits` = 0 linhas na vida; `documents` é RAG, não evidência).
⛔ Nenhum estado deduzido de relógio vira "encerrado". Silêncio é PARADO. Encerrado tem `resolvido_em`.

---

## 1. 📊 O QUE A MEDIÇÃO DE 05/09 ACHOU (SQL no projeto `dcajcvlzcjbmyapmklil`, leitura da árvore em `7f3f3eb`; `o Operations Reality Report do investigador (scratchpad da sessão de 05/09)`)

### 1.1 · 🔴 A Fila encerra 584 atendimentos que ninguém encerrou
📊 `app/api/dashboard/atendimentos/route.ts:217-221`: cascata `closed → HUMAN_REQUESTED → claimed_by → fresh(<48h) → else 'concluido'` com
`detalhe: … || 'Atendimento encerrado.'` (`:232`). Rodando a MESMA cascata sobre o acervo (668 conversas WhatsApp): **concluido 584 · em_conversa
84** (AutoFleet 371/77 · Resulta 205/7 · Amandus 8/0). 📊 `conversations.status`: open 669 · active 59 · **closed 0** · HUMAN_REQUESTED 0;
`resolvido_em NOT NULL = 0/728`; `resolucao_motivo NULL = 728`. Todos os 584 vieram do `else` do silêncio. O cliente filtra
`stage !== 'concluido'` (`AttendanceQueueClient.tsx:98`) → **87,4% do acervo fora do quadro**. E o MESMO payload devolve `semana.terminaram: 0,
indisponivel: false` (`:270-330`, SPEC-086) — contradição dentro de uma resposta (CLAUDE.md §9.5: responde, e responde errado). 📊 6 das 7
colunas do quadro nunca recebem conversa por essa cascata (só `em_conversa` e `concluido`).

### 1.2 · 🟠 O dono e o status estão fundidos — e a coluna "com a equipe" é inalcançável
📊 `grep -rn "claimed_by" app backend/app | grep -i "update\|insert"` → 1 escritor não-nulo (`app/api/dashboard/conversas/[id]/route.ts:120`) que
grava `status: 'HUMAN_REQUESTED', claimed_by: ctx.userId, …` juntos; a cascata testa `HUMAN_REQUESTED` antes de `claimed_by` → `com_equipe` e
"`${claimed_by_name}` está atendendo." (`:231`) são inalcançáveis. FATO: código + censo (`claimed_by NOT NULL = 1/728`). INFERÊNCIA: latente —
"Assumir" foi usado 1 vez na vida do produto; vira ativo quando a operação usar o produto como a 097 quer. É a prova de produto da D-097-10.

### 1.3 · 🔴 A espera tem esquema completo e ZERO linhas — e a proposta construía 4 views e um gate sobre ela
📊 `work_waits`: FK `(conversation_id, company_id)`, CHECK de `kind` (`esperando_documento` NEM É kind válido), `select(count="exact")` → **0 na
vida**. Escritor: `backend/app/services/o_fim_do_atendimento.py` (`marcar_fim`, `abrir_espera`) — 📊 E2: ele NUNCA exigiu `mirror_conversation_id` e já aceita
`session_id`; o portão está nos CHAMADORES (`services/dispatch_router.py:1194,1252`, `tasks/handoff_watchdog.py:480`): é o corredor que só chama
com o espelho ligado. E o botão "Encerrar" de Conversas (📊 E3: existe em `conversas/[id]/route.ts:236`; a Ficha só tem Assumir) JÁ escreve
`resolvido_em` — com o motivo cravado `fechado_por_humano` (E4). 📊 0 escritas em 728: ninguém apertou, e o corredor não chega ao escritor. O contador
`ainda_esperam` da SPEC-086 (`atendimentos/route.ts:296`) diz "0" todo dia com `indisponivel: false` — não é medição, é ausência de escritor.
`resolvido_em` tem o mesmo escritor e a mesma causa: **o desfecho da 086 é a dimensão mais bem desenhada (CHECK no banco, guarda de 956
linhas) e a pior servida (0 escritas)**.

### 1.4 · 🔴 O caso é o episódio, não a conversa — a hipótese §8 da proposta se inverte
📊 668 conversas com telefone → 667 pares (company, phone) distintos; **666 telefones têm exatamente 1 conversa**; pares com >1 conversa em 7
dias: **0**; `count(distinct session_id)` = 728 = 1 sessão por conversa. Duração: até 29 dias; mensagens: 24 conversas com 200+ (máx 1.326). A
conversa é o CANAL perpétuo com a pessoa. E `attendance_sessions` (12.755 linhas: `started_at`, `last_event_at`, `status`, `ramo`, `servico`,
`summary`) → 2.184 contatos distintos, **5,8 sessões por contato, 1.216 contatos (56%) com 2+ em 7 dias** — é a granularidade de EPISÓDIO, e
**não tem `conversation_id`**. Ancorar o caso na conversa funde 5,8 episódios num balde; `work_waits` já apostou nessa âncora (FK na conversa).

### 1.5 · 🔴 Não há N+1; há TETO FIXO, e ele já mente
📊 `grep "map(async|Promise.all(.*map|for .* await"` nas 5 rotas de atendimento → 0. `atendimentos/route.ts:83 .limit(120)` sobre **448**
conversas da AutoFleet (73% invisível em Casos); `:180 work_runs .limit(30)`; `:247 attendance_sessions .limit(40)` sobre 12.755 (0,3%);
`segurados/route.ts:33 .limit(500)`. A busca de Casos é `filter()` no cliente sobre os 120 → "nada encontrado" para um protocolo de 60 dias, sem
distinguir "não existe" de "além do teto" (invariante 16 da proposta violada hoje). 📊 p50 ≈ 1,0 s (5 consultas em série + 1 HTTP), polling a cada
10 s ≈ 30 mil consultas/operador/dia; payload cru 45 KB.

### 1.6 · 📊 11 de 11 views da proposta falham hoje
Sem fonte: "Precisa de atenção", "Aguardando documento" · sem escritor: "IA trabalhando" (run ∧ conversa = 0), "Aguardando cliente/seguradora"
(`work_waits`) · inúteis por falta de ciclo de vida: "Todos ativos" (100% do acervo), "SLA/tempo em risco" (670/728 = 92%) · "Aguardando
confirmação": `approval_requests` sem `conversation_id` (10 linhas na vida, 5 corretoras) · "Travados": `unblock_state` sem conversa utilizável.

### 1.7 · O que já existe e serve — e o que a proposta descrevia como trabalho já feito
✅ Lista e Quadro **já existem** sobre o MESMO read model (`/api/dashboard/atendimentos`: Fila = quadro por `stage`; Casos = lista com busca + 5
filtros) — G4 é verdade por construção; o risco é regredi-la. ✅ A rota já é `/dashboard/atendimentos/casos` ("Histórico" sobrou como label em
`lib/mock/tenant-modules.ts:27` e um `<a>` em `AttendanceQueueClient.tsx:211` → BLOCO K vira 1 linha). ✅ Notas internas já consolidadas
(prefixo `📝 [nota interna] ` em `messages`, `lib/atendimento/a-nota-da-atendente`) → BLOCO I sem trabalho. ✅ `attendance_cases` NÃO existe
(D-097-02 sem objeto). ✅ Ficha (SPEC-046) já tem a maior parte do Case Workspace; a timeline existe e **6 dos 9 tipos têm `at: null`** (E16: o do claim sai de `claimed_at`). ✅ 5/5
rotas de atendimento filtram tenant — o piso CRÍTICO desta SPEC não é auth: é ESCRITA no ciclo de vida. ✅ Guardas vivos que a 097 tem de
respeitar/migrar: `test_o_clique_da_atendente_nao_apaga_da_fila.py` (congela a regra "o que sai da fila" — MIGRA, não remove),
`test_o_atendimento_termina_e_o_produto_sabe.py` (motivos = CHECK), `atendimento-estados.test.mjs` (espelho dos estados do dispatch),
`test_a_chave_de_juncao_do_atendimento.py` (`work_runs.conversation_id` por UM helper), `test_conversa_que_acabou_nao_fica_aberta.py`.
❌ Documentos: `documents` é a base de conhecimento (RAG); a evidência do atendimento é coluna de mensagem (`image_url` NOT NULL = **13**,
`audio_url` = **0** em 25.061 mensagens); `artifacts` sem conversa → D-097-07 vira pendência. ❌ `work_events` é 100% telemetria de motor
(`run.leased`, `step.started`) — exatamente o que a §18 proíbe exibir; não é fonte de timeline.

---

## 2. AS REGRAS QUE ESTA SPEC FIXA

```
R1  DESFECHO    "encerrado" ⇔ `resolvido_em IS NOT NULL` (com `resolucao_motivo` do CHECK). Nunca deduzido de relógio. Silêncio ⇒ PARADO.
                🔴 UM relógio (E5): `ultimo_evento_em = greatest(conversations.last_message_at, attendance_sessions.last_event_at)`; a Fila, o
                `parado_ha` e o `semana` leem ESSE campo — nunca dois. E o `status` que o Atlas fecha por 6 h de silêncio
                (`attendance_distiller:200-240`, para o RAG) NÃO é desfecho (E9): a projeção o ignora para ENCERRADO.
R2  DONO        `claimed_by` é dimensão própria; o claim NÃO escreve `status`. A projeção testa dono ANTES de status. Cardinalidade 1; ∅ é legítimo.
                🔴 E6 (obrigatória): a IA PAUSA quando `HUMAN_REQUESTED` OU `claimed_by IS NOT NULL` — helper único `pausar_ia(conversa)` usado em
                `webhook.py:628` e `chat.py:173,620` (📊 hoje pausam só por status: sem isto, a IA responde por cima da atendente).
R3  EPISÓDIO    o caso é o EPISÓDIO (`attendance_sessions`), ligado à conversa por `attendance_sessions.conversation_id` (coluna nova, nullable,
                expand-first). 📊 E7: só 57,8% das sessões casam 1:1 por telefone — as 5.383 órfãs continuam CASOS (com o que a sessão tem), rotuladas
                "sem conversa vinculada", e ganham o elo quando o Atlas gravar (U3.3). E8: o desfecho mora no EPISÓDIO (`attendance_sessions.resolvido_em`,
                `resolucao_motivo`, na mesma migration) e é espelhado na conversa quando ligada. A FILA é uma linha por CONVERSA (o episódio corrente
                dela); CASOS é a lista por episódio. Conversa sem episódio ⇒ 1 caso implícito.
R4  ESPERA      SAI DESTA MARCHA (E10): 📊 4 acionamentos em 30 dias, só `esperando_humano` é escrito, e a FK de `work_waits` barra o episódio órfão.
                A Fila mostra espera SÓ se `work_waits` tiver linha ativa (hoje 0) — nunca deduzida. P-097-ESPERA-COM-ESCRITOR guarda o gatilho.
R5  UM READ MODEL  `lib/atendimento/casos.ts::projetarCasos(company, filtro, {group_by?, cursor?, busca?})` é a ÚNICA função de leitura; Fila e
                Casos a chamam; paginação e busca no BANCO; sem `.limit(120)`; `indisponivel: true` quando uma fonte falha — nunca zero silencioso.
R6  ATENÇÃO     razões DERIVADAS e só as observáveis: `pediu_pessoa` (HUMAN_REQUESTED), `trabalho_falhou` (work_run failed/travado com conversa),
                `parado` (R1), `espera_vencida` (só se `work_waits.due_at` existir). `aprovacao_pendente` NÃO (E17: `approval_requests` sem conversa;
                ponte run→conversa com 4 linhas). Sem SLA
                inventado, sem LLM, sem "prioridade" digitável.
R7  PRÓXIMA AÇÃO  precedência determinística: pessoa obrigatória → aprovação → passo do trabalho (blocker) → espera com prazo → "sem próxima ação
                declarada". Nunca ficção.
R8  TIMELINE    projeção sobre conversations/messages, attendance_sessions/dispatch, work_runs/work_waits, approvals, artifacts — cada item com
                `at` (não nulo), `fonte` (autoridade) e `fonte_id`. Sem `work_events`. Sem event store novo.
R9  TENANT      toda relação Caso→Conversa/Trabalho/Aprovação/Peça é resolvida pela corretora da sessão (`resolveSessionCompany`); dois tenants
                no guarda. UUID não é autorização.
R10 CUTOVER     nenhuma tela nova ao lado das existentes: a Fila e os Casos de hoje passam a ler `projetarCasos`; "Histórico" some do label.
```

---

## 3. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (§7.3 · reaberto em 05/09/2026 pelo pesquisador)

> 📊 Reaberto em 05/09/2026. Sete referências refetchadas uma a uma (WebFetch ao vivo).
> Duas URLs do RESEARCH-PACK de 03/09/2026 **não sobreviveram** — marcadas abaixo.

**1 · Intercom — SLA e atenção como relógio, não como coluna**
```
URL · https://www.intercom.com/help/en/articles/6546152-set-slas-for-conversations-and-tickets
```
- **FAZ** · Aplica à conversa até quatro alvos de tempo (first response, next response, time to close, time to resolution), mostra na Inbox **o alvo mais próximo** como contagem regressiva colorida e registra o desfecho em três estados — `Hit`, `Missed`, `Fixed` (perdeu o alvo, mas foi concluído depois).
- **MODELAMOS** · A dimensão **atenção** do Caso é derivada de relógio + regra, nunca digitada: o read model calcula `deadline`, `elapsed` e `nearest_target` a partir do wait/approval/run que segura o Caso, e o AGORA exibe **um** alvo com o mesmo tri-estado. O `Fixed` é o que impede a fila de mentir sobre recuperação.
- **REJEITAMOS** · A SLA do Intercom é **objeto persistido e editável na conversa**. Não persistimos SLA no Caso (invariante 3: sem event store/tabela nova). O alvo mora na autoridade que gera a espera; o Caso só o **lê**.
- **Envelheceu?** Não. 📊 Página atualizada em 30/07/2026 — mais nova que o pacote. URL viva.

**2 · Intercom — Views como filtro salvo sobre a mesma fila**
```
URL · https://www.intercom.com/help/en/articles/6258745-the-inbox-explained
```
- **FAZ** · Views definem um conjunto de filtros e mostram em tempo real as conversas que casam — a mesma Inbox, recortada; ações em massa direto do layout de tabela.
- **MODELAMOS** · A Fila é **uma** consulta com filtros nomeados. As views oficiais são presets versionados, não endpoints distintos (é o que torna G4 verdadeiro por construção).
- **REJEITAMOS** · O botão "marcar como prioridade" que grava flag livre na conversa. Prioridade não é quinta dimensão: é função de `atenção` × `deadline`. Enum novo aqui é a porta do mega-enum que a D-097-10 proíbe.
- **Envelheceu?** Parcialmente. 📊 "Updated over a month ago"; **não cobre SLA** — o pacote creditava SLA a esta URL, o crédito correto é a nº 1.

**3 · Front — um dono humano, sempre exatamente um**
```
URL · https://help.front.com/en/articles/2344   ("How to assign a conversation")
```
- **FAZ** · Quatro caminhos de atribuição (manual, reatribuição, auto na primeira resposta de saída, regra automática) sobre **um único dono por conversa**.
- **MODELAMOS** · `owner` é dimensão própria, cardinalidade 1, com valor legítimo `∅` que a Fila sabe filtrar. Auto-atribuição na primeira ação humana de saída: quem responde, assume. Reatribuição é comando com autor e motivo, e entra na Timeline.
- **REJEITAMOS** · Confundir dono com **quem-segura** (`waiting_on`). No Front, conversa atribuída e parada parece trabalho em curso. `owner=Ana` + `waiting_on=seguradora` são fatos ortogonais — colapsá-los é exatamente o ACHADO-1b deste relatório.
- **Envelheceu?** Não. ⚠️ Mas `help.front.com/en/articles/2099`, citada no pacote como âncora de comentários internos, **hoje é "Conversation custom fields"**. Não use aquele número para justificar Notas.

**4 · Zendesk — painel de contexto ao lado, não dentro do ticket**
```
URL · https://support.zendesk.com/hc/en-us/articles/4408836526362-Using-the-context-panel
```
- **FAZ** · Trilho lateral no Agent Workspace que abre, sem sair do ticket: dados e histórico do cliente, objetos relacionados, artigos, side conversations, tickets semelhantes, aprovações, tarefas e apps.
- **MODELAMOS** · O trilho do Case Workspace agrega **referências às autoridades** (segurado, apólice, documentos com proveniência, runs relacionados) — cada item com link para a fonte, nenhum item copiado para dentro do Caso.
- **REJEITAMOS** · O painel plugável de terceiro que **escreve** no ticket. Todo item do trilho é somente leitura no Caso; escrita acontece na autoridade dona e o Caso reprojeta — é isso que preserva um único ponto de filtro por tenant (CLAUDE.md §7, com service role).
- **Envelheceu?** URL viva. 📊 Conteúdo **mudou desde 03/09**: agora cita Copilot (tickets relacionados) e gestão de ativos de TI.

**5 · Salesforce — Case Timeline unifica registros que já existem**
```
URL · https://help.salesforce.com/s/articleView?id=service.cases_set_up_and_manage_the_case_timeline.htm&language=en_US&type=5
```
- **FAZ** · Eventos-chave do caso em ordem cronológica, alguns marcados como **marcos**, puxando de objetos que já existem (Task, Event, EmailMessage, FeedItem, filhos) — para entender um caso longo sem abrir abas.
- **MODELAMOS** · A Timeline Operacional é isto: **projeção de leitura** sobre conversations, runs, waits, approvals e artifacts, com marcos destacados. Nenhum event store novo (invariante 3).
- **REJEITAMOS** · O "marco" configurável por admin que vira **campo gravado** no caso. Marco é classificação derivada do tipo do evento de origem — se fosse campo, teria escritor, e escritor de projeção é motor paralelo (CLAUDE.md §5).
- **Envelheceu?** 🔴 **Sim, e é o achado mais relevante.** A URL do pacote não renderiza a fetch (SPA, "CSS Error"); a viva exige `&language=en_US&type=5`. E 📊 **Case Timeline é feature do release Spring '26** — ganhou release notes depois do pacote. **O maior player do setor adotou AGORA a aposta central da 097** — valida a direção, mas não há maturidade de campo para copiar UX.

**6 · ServiceNow — activity stream é configuração de exibição, não armazenamento**
```
URL · https://www.servicenow.com/docs/r/platform-user-interface/administer-activity-stream-configurable-workspace.html
```
- **FAZ** · Administra o activity stream por propriedades e configuração de exibição (vista empilhada, avatares, ícones, ordem) e permite tags customizadas para filtrar entradas.
- **MODELAMOS** · Os filtros da Timeline (`Tudo · Conversas · Ações · Documentos · Humano · IA · Seguradora · Interno`) são **facetas do read model**, não streams separados; densidade e ordem são preferência de exibição, não estado do Caso.
- **REJEITAMOS** · Tag livre como mecanismo de filtro. Tag livre por tenant vira taxonomia divergente e quebra a comparabilidade da Fila; a faceta vem do **tipo do evento de origem**, derivado e não digitável.
- **Envelheceu?** 🔴 **A URL do pacote está MORTA** (`csm-playbooks-using-activity-stream.html` → **HTTP 404**). A viva é a acima. 📊 Bundle atual **"Australia"**, 14/08/2026; produto renomeado para "ServiceNow AI Platform".

**7 · Microsoft Architecture Center — CQRS: read model, projeção, comando com nome de negócio**
```
URL · https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs
```
- **FAZ** · Separa comandos (escrevem, validam) de queries (nunca alteram, devolvem DTO sem lógica de domínio); read model pode ser materialized view sobre a mesma base; e a regra explícita: *"comandos devem representar tarefas de negócio específicas em vez de atualizações de dado de baixo nível — use `Book hotel room`, não `Set ReservationStatus to Reserved`"*.
- **MODELAMOS** · Duas decisões de uma vez. (a) **Caso é read model**: uma função de projeção, sem tabela própria, sem escritor. (b) **Arrastar é comando**: soltar em "Aguardando documento" dispara `solicitar_documento(caso)` — a tarefa de negócio — e a coluna muda **porque a projeção mudou**. Falhou o comando, o card volta. Board é `group_by` sobre a query da List.
- **REJEITAMOS** · O braço "stores separados + event sourcing". Fowler é explícito (`martinfowler.com/bliki/CQRS.html`, 2011): *"para a maioria dos sistemas, CQRS acrescenta complexidade arriscada"*. Aqui: **um** store (Supabase), projeção síncrona, zero eventual consistency — a invariante 1 prevalece sobre a forma completa do padrão.
- **Envelheceu?** Não. 📊 `updated_at` 15/08/2026, vivo. Ganhou menções a Transactional Outbox e idempotent consumer — irrelevantes, porque rejeitamos o braço de stores separados.

---

### COMO O JUIZ INSPECIONA

1. **Uma função, duas telas.** `grep -rn "queueReadModel\|caseProjection\|buildCaseView" app lib backend` e grepar quem chama. **Esperado:** List (`/casos`) e Board (`/fila`) chamam **a mesma** função; Board difere só por `group_by`. Duas funções de leitura = reprovado. 📊 Hoje isso já é verdade **por acidente** (mesma rota) — a inspeção existe para que a 097 **não regrida**.
2. **Zero escritor de Caso.** `grep -rniE "from\(['\"](cases|tickets|attendance_cases)['\"]\)\.(insert|update|upsert)" app backend` → **zero hits**. Migration que crie tabela de ticket persistida reprova por si só.
3. **Drop não muta ciclo de vida.** Ler o corpo de `onDrop`/`onDragEnd`: chama comando nomeado por tarefa de negócio, e `grep -n "status *=\|setStatus(\|lifecycle" ` dentro dele → **zero**.
4. **Falha de comando reverte o card.** Simular 500 no comando do drop. **Esperado:** card volta à coluna de origem + erro visível. Se ficar, a posição virou verdade — reprovado.
5. **Quatro dimensões, quatro campos.** No DTO do Caso: `status`, `owner`, `waiting_on`, `attention` separados. `grep -rniE "AGUARDANDO_[A-Z_]+_(ATRASAD|COM_)"` → zero. 🔴 **E o teste específico deste projeto:** assumir uma conversa **não** pode escrever `status` (ACHADO-1b) — `grep -n "status:" ` no handler de `claim` → **zero**.
6. **Atenção é calculada, nunca gravada.** Todo hit de `attention` é leitura; existe teste que congela o relógio, avança o tempo, vê a atenção mudar e compara `count(*)` antes/depois → **iguais**.
7. **Timeline não tem store, e todo evento tem hora.** `ls backend/supabase/migrations/ | grep -i "event\|timeline"` → nenhuma nova; cada item carrega `source_authority` + `source_id`. 🔴 **E `at` não-nulo** — hoje 7 dos 10 eventos da Ficha têm `at: null`.
8. **Nenhuma view sobre tabela sem escritor.** Para cada view publicada, rodar seu COUNT nas três corretoras. **Esperado:** nenhuma publicada com 0 nas três **e** nenhuma com 100% do acervo. 🔴 Hoje 11/11 falham esse teste.
9. **Desfecho nunca é deduzido do relógio.** `grep -rn "48 \* 3600\|fresh\|last_message_at" ` no caminho da projeção: nenhum ramo de silêncio pode produzir um estado terminal. **Esperado:** um caso sem mensagem há 30 dias e sem `resolvido_em` aparece como *parado*, nunca como *encerrado*.
10. **Isolamento com dois tenants reais.** Rodar contra a query da Fila, a projeção do Caso e a Timeline. Zero linhas cruzadas, e `grep` mostrando o filtro `company_id` explícito no repository — RLS sozinha não conta, o backend usa service role.
11. **Documento tem proveniência.** Todo item exibido tem origem (canal + ator), horário e id do objeto. Nenhum byte copiado para tabela de caso. ⛔ E `grep -rn 'table("documents")'` no caminho de atendimento → **zero** (é RAG).
12. **Guarda que consegue ficar VERMELHO** (§9.3). Reintroduzir de propósito o `else stage='concluido'` por silêncio e rodar a suíte. **Esperado: VERMELHO.** Verde = carimbo, e a inspeção reprova mesmo com o código certo.

---

### O QUE ENVELHECEU DESDE 03/09/2026

📊 Refetch de 05/09: **uma URL do pacote está morta** — o activity stream do
ServiceNow CSM devolve **404**; a família migrou para URLs versionadas por
bundle ("Australia", 14/08/2026, produto renomeado "ServiceNow AI Platform").
**Uma é inacessível a fetch** — as páginas `help.salesforce.com/s/articleView`
só renderizam em browser e precisam de `&language=en_US&type=5`. **Uma mudou de
assunto** — `help.front.com/en/articles/2099` hoje é "Conversation custom
fields"; a âncora válida é `/articles/2344`. O genuinamente novo: o **Case
Timeline da Salesforce é do release Spring '26** — o maior player do setor
adotou, agora, exatamente a aposta central da 097 (timeline unificada como
leitura sobre objetos existentes, sem store novo), o que fortalece a direção
mas significa que não há maturidade de campo para copiar detalhes de UX. Zendesk
acrescentou Copilot e ativos de TI ao context panel. Intercom e Linear não se
moveram materialmente; a página de CQRS foi tocada em 15/08/2026. 💭 Nenhuma
referência nova entrou sem substituir outra; a §7.3 fechou em 7.

---

## 4. OS BLOCOS

### BLOCO 0 · Gate zero e o censo que vira régua
- **0.1** guardas novos VERMELHOS em cópia limpa: (i) o `else` do silêncio ainda vira `concluido` · (ii) claim escreve status · (iii) `attendance_sessions`
  sem `conversation_id` · (iv) a IA não pausa por `claimed_by` (E6) · (v) `.limit(120)` na Fila · (vi) busca de Casos no cliente ·
  (vii) 7 tipos de timeline com `at: null` · (viii) duas funções de leitura (Fila ≠ Casos) · (ix) `semana.terminaram` contradiz `items`.
- **0.2** 📊 régua antes: 584 "encerrados" sem `resolvido_em`; `work_waits` 0; `claimed_by` 1; 120/448; p50 da Fila 1,0 s (7 execuções).

### BLOCO U1 · O desfecho para de ser deduzido do relógio (escrita)
- **U1.1** `atendimentos/route.ts`: o ramo `else stage='concluido'` MORRE; nasce `parado` (`parado_desde`, `parado_ha`); `concluido` ⇔ `resolvido_em`.
- **U1.2** `marcar_fim` aceita `conversation_id` OU `attendance_session_id` (R3), grava o desfecho no EPISÓDIO e espelha na conversa; os CHAMADORES
  (`services/dispatch_router.py:1194,1252`, `handoff_watchdog.py:480`) deixam de condicionar ao espelho — chamam com a sessão. O botão "Encerrar"
  (Conversas) passa a PERGUNTAR o motivo (E4: os 5 do CHECK) e a Ficha ganha o mesmo botão (E3).
- **U1.3** `semana.terminaram`/`ainda_esperam` continuam lendo `resolvido_em`/`work_waits` — agora com escritor; `indisponivel: true` se a consulta falhar.
- **U1.4** MIGRA `test_o_clique_da_atendente_nao_apaga_da_fila.py` (E13: hoje é regex sobre `route.ts` e não afirma nada sobre a fila → vira asserção que
  EXECUTA `projetarCasos`: só desfecho escrito tira) e os guardas da 086 que leem `atendimentos/route.ts` por caminho (E14: `:818,:855,:866` ficariam verdes por
  vacuidade quando os contadores mudarem de lugar → apontam para `projetarCasos`).

### BLOCO U2 · A verdade do dono (escrita)
- **U2.1** `conversas/[id]/route.ts:120`: o claim grava `claimed_by`, `claimed_by_name`, `claimed_at` — e NÃO `status`. `HUMAN_REQUESTED` continua
  sendo do handoff (o pedido do cliente), não do claim.
- **U2.2** a projeção testa `claimed_by` antes de `HUMAN_REQUESTED`: "Ana está atendendo" volta a ser alcançável; "pediu uma pessoa" = HUMAN_REQUESTED ∧ sem dono.
- **U2.3** (E6) `pausar_ia(conversa)` = `status == HUMAN_REQUESTED or claimed_by is not None`, usado em `webhook.py:628` e `chat.py:173,620`; guarda com PAR.

### BLOCO U3 · O episódio ganha identidade (migration expand-first)
- **U3.1** `backend/supabase/migrations/2026MMDD_01_spec097_episodio_tem_conversa.sql`: `ALTER TABLE attendance_sessions ADD COLUMN IF NOT EXISTS
  conversation_id uuid NULL REFERENCES conversations(id) ON DELETE SET NULL`, `resolvido_em timestamptz NULL`, `resolucao_motivo text NULL` (mesmo CHECK
  da conversa, E8) + índice `(company_id, conversation_id)`; APPLY/VERIFY/ROLLBACK.
- **U3.2** backfill por junção (company, telefone normalizado) onde a junção é 1:1 — 📊 E7: **57,8%** das sessões; as 42,2% órfãs NÃO são gravadas (ambíguo
  ou sem conversa) e seguem como casos "sem conversa vinculada". Script `--dry-run`, VERIFY = contagens (preenchidas / órfãs / ambíguas).
- **U3.3** o escritor de sessões é o Atlas (`atlas/observer_intake.py:606`, E12) e só tem o telefone: grava `conversation_id` quando a junção por
  (company, telefone) é ÚNICA no momento da escrita; senão null. Guarda: sessão nova com telefone único → elo; ambíguo → null.
- 💡 decisão registrada (protocolo §9, nota): episódio = `attendance_sessions` **85** × tabela `cases` nova **30** (motor paralelo; CLAUDE.md §5) ×
  caso = conversa **20** (📊 §1.4 inverte).

### BLOCO U4 · A espera — SAIU desta marcha (E10/E18)
- A Fila LÊ `work_waits` ativos se existirem (R4) e nada mais. O escritor por episódio, o `due_at` do corredor e a FK que aceite o órfão são a
  pendência P-097-ESPERA-COM-ESCRITOR — volta quando o corredor entrar em espera com o espelho ligado (📊 4 acionamentos em 30 d).

### BLOCO U5 · Um read model, sem teto
- **U5.1** `lib/atendimento/casos.ts::projetarCasos` (R5): fonte única; a FILA/Quadro é por CONVERSA ativa (≤ 📊 700 por corretora: lê TODAS em lotes de
  1.000, sem teto, agrupa e conta por estágio em memória — E11: estágio é derivado, PostgREST não agrega); CASOS é por episódio com `cursor
  (ultimo_evento_em, id)` + `busca` (protocolo/nome/telefone normalizado) no banco; `indisponivel` por fonte.
- **U5.2** Fila e Casos chamam a função; a busca sai do cliente; "nada encontrado" só quando o banco disse 0.
- **U5.3** contadores da 086 saem da mesma projeção (uma verdade por payload — R1 fecha a contradição de 1.1).

### BLOCO U6 · O AGORA e a timeline com hora
- **U6.1** Ficha: bloco AGORA = situação (R1) · dono (R2) · de quem espera (R4) · há quanto tempo · atenção (R6) · próxima ação (R7) · protocolo.
- **U6.2** timeline: os 7 tipos com `at: null` ganham `at` da fonte; cada item com `fonte`/`fonte_id`; sem `work_events`.
- **U6.3** SAIU (E18): a timeline é ordenável e inteira por caso (📊 máx 1.326 mensagens: a Ficha já carrega); paginação volta com P-097-TIMELINE-CURSOR.

### BLOCO E · Canário vivo
- `backend/scripts/canario_097.py` (`AUTOBROKERS_CANARIO=1`, Resulta): cria conversa + episódio canário, abre espera pelo escritor, assume (claim),
  encerra com motivo, lê `projetarCasos` pelas duas lentes (Lista/Quadro) e prova: o caso saiu da Fila ativa SÓ ao encerrar; "parado" apareceu
  antes; `semana.terminaram` = 1 no mesmo payload que o item; a busca acha o protocolo canário; limpa TUDO por id com VERIFY 0/0/0.

### BLOCO G · Os guardas (desenhista, antes do código — asserções que EXECUTAM; mutação por NOME novo)
- `scripts/a-operacao-tem-uma-casa.test.mjs`: executa `projetarCasos` com dublê (2 corretoras; 700 conversas; sessões 5,8/contato; waits; runs;
  approvals); Fila e Casos chamam a MESMA função (PAR); silêncio → `parado`, nunca `concluido` (PAR: `else concluido` de volta → vermelho);
  claim sem status (PAR); cursor/busca no banco (PAR: `.limit(120)`/`filter()` de volta); `indisponivel` por fonte (PAR: zero silencioso); AGORA
  com as 6 dimensões; timeline sem `at` nulo (PAR); dois tenants (PAR: sem `company_id` → vazamento).
- `backend/tests/test_o_atendimento_sabe_como_terminou.py`: `marcar_fim`/`abrir_espera` por episódio, sem espelho (PAR: `mirror_conversation_id`
  exigido → vermelho); migration com APPLY/VERIFY/ROLLBACK e `IF NOT EXISTS`; backfill só onde 1:1; o escritor de sessões grava o elo.
- MUTAÇÕES (12): `else concluido` · claim escreve status · cascata testa status antes do dono · `.limit(120)` · busca no cliente · `indisponivel:false` fixo ·
  `at: null` num tipo · duas funções de leitura · `mirror_conversation_id` obrigatório · backfill sem o 1:1 · `company_id` fora da projeção · `work_events` na timeline.

---

## 5. O QUE SAIU DA PROPOSTA — e o gatilho que faz voltar
| saiu | por quê (📊) | volta quando |
|---|---|---|
| BLOCO F Documentos (D-097-07) | 13 imagens e 0 áudios com URL em 25.061 mensagens; `documents` é RAG; `artifacts` sem conversa | P-096-ARTIFACT-SEM-CONVERSA fechar e houver acervo |
| BLOCO I Notas | já consolidado (`📝 [nota interna]`) | nunca |
| BLOCO K Cutover Histórico→Casos | 1 linha de label | feito dentro de U5 |
| §16 Drag-and-drop | não há drag hoje; construir para governar é o risco da D-097-04 | uma corretora pedir arrastar |
| 4 views de espera + dimensão WAIT completa + G7 | `work_waits` 0 na vida; "documento" não é kind | U4 provar escrita real por 30 dias |
| `sla_at_risk`, `wait_overdue`(sem due_at), `document_missing`, `followup_due` | sem fonte | cada uma com o seu escritor |
| `work_events` como fonte de timeline | 100% telemetria de motor | nunca (§18 da própria proposta) |
| "Precisa de atenção" como view própria | sem fonte; atenção é derivada (R6) e vira FILTRO da Fila, não view | — |
| Salesforce Case Timeline como UX madura | release Spring '26 | quando houver campo |
| tabela `cases` / `attendance_cases` | o episódio já existe (`attendance_sessions`) | nunca por esta SPEC |

## 6. PENDÊNCIAS QUE NASCEM AQUI
P-097-DOCUMENTOS-DO-ATENDIMENTO (a evidência como coluna de mensagem, sem proveniência) · P-097-MIDIA-INALCANCAVEL (📊 9.002 mídias do history sync
sem `waE2E.Message`) · P-097-APPROVAL-SEM-CONVERSA (`approval_requests` não volta ao atendimento) · P-097-POLLING-10S (30 mil consultas/operador/dia;
Realtime só depois de medir) · P-097-DRAG (§16) · P-097-ESPERA-COM-ESCRITOR (U4) · P-097-TIMELINE-CURSOR (U6.3) ·
P-097-SESSOES-ORFAS (📊 42,2% sem conversa 1:1).

## 7. A CAIXA DO FOUNDER
- **Nada bloqueante.** As duas decisões que a proposta mandava para você (U3 espera: escritor ou sai; U4 episódio) foram pontuadas e decididas
  (§4 U3/U4): o episódio é `attendance_sessions` com o elo para a conversa; a espera só existe com escritor.
- **Depois:** (a) o espelho do WhatsApp (Atlas) ligado nas corretoras — com ele o corredor sabe a conversa sem a junção por telefone; (b) documentos
  do atendimento como evidência (P-097-DOCUMENTOS) quando houver acervo.

## 8. GATE FINAL
```
gate zero: os 9 vermelhos em cópia limpa · guardas G verdes · 12 mutações vermelhas · rotas montam · tsc · next build · next start + 1 request ·
suíte inteira (árvore parada) · migration APPLY/VERIFY/ROLLBACK + advisors antes/depois · canário E com saída colada · régua 0.2 depois:
0 "encerrados" sem resolvido_em, `com_equipe` alcançável, work_waits > 0 pelo canário, busca acha o protocolo antigo · red team + 2 lentes +
juiz fresco · git push origin HEAD:main com a saída no relatório
```

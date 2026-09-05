# SPEC-097 · EXECUTION REPORT — A operação tem uma casa

> Branch `feat/spec097-casa` · base `origin/main` = `7f3f3eb` · protocolo v11.2 + opção B · marcha **CRÍTICO** · 05/09/2026 (mesma sessão da 096, por ordem
> do Founder: "emende direto") · orquestrador Fable 5.1 · SPEC `docs/canon/specs/SPEC-097-a-operacao-tem-uma-casa.md` v1.1.

## 0. EXECUTION CARD (protocolo §0.2)
```
OUTCOME ..............  o desfecho do atendimento deixa de ser deduzido do relógio (PARADO ≠ ENCERRADO; encerrado ⇔ resolvido_em escrito); o dono deixa de ser o
                        status (e a IA pausa quando alguém assume); o caso é o EPISÓDIO com elo para a conversa; Fila e Casos leem UMA projeção sem teto; o AGORA
                        e a timeline com hora e fonte
RISCO ................  7  (alcance: a corretora 2 · reversibilidade: dado/estado 2 — escreve resolvido_em/claimed_by/colunas novas · frequência: TODO atendimento 2 · +1 pela migration)
SUPERFÍCIE ...........  3  (Web + BFF + FastAPI (chamadores do corredor, webhook, chat) + Atlas + DB + UX principal do atendimento)
PISO APLICADO ........  §3.2: migration que ALTERA ESTRUTURA (3 colunas + FK + índice em attendance_sessions) + escrita no ciclo de vida em produção → CRÍTICO
NÍVEL ................  CRÍTICO
UNIDADES .............  0 (gate zero + régua) · U1 desfecho · U2 dono (+U2.3 pausar_ia) · U3 episódio (migration + backfill + Atlas) · U5 read model · U6 AGORA/timeline · E canário · G guardas
                        (U4 espera e U6.3 paginação SAÍRAM no aquecimento — E10/E18)
COESÃO ...............  U1+U2 juntas (são o contrato do estágio); U3 antes de U5 (a chave do read model); U5+U6 na tela/BFF; escritores python no backend
PARALELISMO REAL .....  2 escritores: builder backend (backend/**) ‖ builder tela+BFF (app/**, lib/**) — contrato = `attendance_sessions.conversation_id` + os escritores por episódio
TIME .................  investigador+pesquisador (Opus, 193k) · aquecimento (Opus, 160k) · desenhista · 2 builders · red team · lente DADO · lente verdade · juiz fresco · Sonnet mecânico
REFERÊNCIA ...........  interna: guardas da 096 (bloco [D] que sobe o router; [1]–[25] que executam rotas e componentes) · `test_o_atendimento_termina_e_o_produto_sabe.py` (086)
                        externa: SPEC §3 — Intercom (SLA como relógio; views como filtro), Front (um dono), Zendesk (trilho de contexto), Salesforce Case Timeline (Spring '26),
                        ServiceNow (activity stream como exibição), CQRS (read model; drag = comando) — reabertas em 05/09
GATES ................  gate zero (9 vermelhos na cópia limpa) · guardas G verdes · 12+ mutações · rotas montam · tsc · next build · next start + 1 request · suíte inteira ·
                        migration APPLY/VERIFY/ROLLBACK + advisors · backfill --dry-run/VERIFY · canário E · régua 0.2 depois · painel + juiz · push
O ELO ................  "a Fila encerra PORQUE o else do silêncio" → medido A (584 rotulados), medido B (`resolvido_em` 0/728), medido que B chega em A (rodando a MESMA
                        cascata sobre o acervo: 584 vêm do else). "com_equipe é inalcançável PORQUE o claim escreve status" → lido o único escritor + a ordem da cascata.
FAIXA DE RELÓGIO .....  6–8h   ORÇAMENTO ≤ 2,5 M (📊 a 096 estourou 28% por arnês: exigido do desenhista asserções que EXECUTAM)
```

## 0.1 Telemetria (protocolo §11)
```
começou 05/09 ~10:45 (branch) · primeira linha de código de produto: {A PREENCHER}
rodadas de painel: {A PREENCHER}
defeitos que o painel NÃO pegou e quem pegou: {A PREENCHER}
rodadas da bateria: {A PREENCHER}
nota 0–100 do orquestrador: {A PREENCHER}
```

## 1. O que a conversão mediu (e o que mudou o desenho)
- 🔴 📊 A Fila rotula **584 de 668** conversas (87,4%) "Atendimento encerrado" pelo ramo `else` do silêncio > 48 h; `resolvido_em` NULL em **728/728**; `status='closed'` = 0;
  e o MESMO payload devolve `semana.terminaram: 0, indisponivel: false`. Invariantes 8, 16 e 17 da própria proposta violadas hoje.
- 📊 `work_waits` = **0 linhas na vida** (esquema, FK e CHECK completos); os 3 chamadores de `abrir_espera`/`marcar_fim` só chamam com o espelho (`mirror_conversation_id`);
  4 acionamentos em 30 dias → U4 SAIU (P-097-ESPERA-COM-ESCRITOR).
- 📊 O único escritor de `claimed_by` grava `status='HUMAN_REQUESTED'` junto; a cascata testa status antes do dono → "está atendendo" inalcançável (latente: 1 claim na vida).
  E a IA pausa só por status (`webhook.py:628`, `chat.py:173,620`) → E6 obrigatória: `pausar_ia` por `claimed_by` também.
- 📊 1 telefone = 1 conversa perpétua (666/667; até 1.326 mensagens, 29 dias); `attendance_sessions` 12.755 (5,8 por contato; 56% com 2+ em 7 dias) sem `conversation_id`;
  só **57,8%** casam 1:1 por telefone → o caso é o EPISÓDIO; migration expand-first (conversation_id + resolvido_em + resolucao_motivo); órfãs continuam casos.
- 📊 Não há N+1; há teto fixo (`.limit(120)` sobre 448) e busca `filter()` no cliente → falso "nada encontrado".
- 📊 Documentos: 13 imagens e 0 áudios com URL em 25.061 mensagens; `documents` é RAG → D-097-07 vira pendência. Notas: já consolidadas. "Histórico": sobrou um label.
- Aquecimento: **nota 74**, 18 emendas (E1–E18) aplicadas; as 2 falsas assinadas (656 → 666; `.limit(200)` → `.limit(120)`) refutadas por comando; 3 números da §1 reproduzidos.
- Proposta: 📊 nota do investigador **62/100** — SPEC de leitura para um problema de escrita.

## 2. Decisões da execução (protocolo §9: nota, escolha, siga)
- episódio = `attendance_sessions` **85** × tabela `cases` nova 30 (motor paralelo) × caso = conversa 20 (o censo inverte).
- desfecho no EPISÓDIO (colunas na sessão, espelhado na conversa) **80** × órfã inelegível a ENCERRADO 55.
- U4 espera SAI desta marcha **80** × escritor sem evento 45 (4 acionamentos/30 d; FK barra o órfão).
- Fila por CONVERSA ativa (lotes de 1.000, contagem em memória) e Casos por episódio com cursor **75** × RPC de contagem (migration a mais) 50.

## 3. Commits
```
5850c43 SPEC v1.0 · ad71e57 dossiê · 806282a aquecimento/emendas (v1.1) · a0234f4 guardas (gate zero) · 2938996 backend U1–U3 · daa619b tela/BFF · 7ae06fb U7
e3bb30d schema vivo · cbcf985 [13] · a4c9815 v1.2 · bca4d27 dossiê · 8861143 FE: DADO+red team+visual+[14][15] · 8865192 BE: P0-1 e cia · 90ff89c migration aplicada · {A PREENCHER}
```
## 4. Gate zero (📊 cópia limpa `../AutoBrokers-FIX-gate0` em 7f3f3eb, desenhista Opus 276k)
```
node scripts/a-operacao-tem-uma-casa.test.mjs      → 16 falhas ([1]×2 [2] [3] [4]×2 [5] [6] [7]×2 [8] [9] [10] [11] [12]×2)
python tests/test_o_atendimento_sabe_como_terminou.py → 13 falhas (B1b/c/d, B2c, B3, B4, B4e/f, B5a, B6a, B6c×2, B8) · 25 ok
os 9 itens do BLOCO 0.1 cobertos: (i)[2] (ii)[4] (iii)[5][B3][B4][B5a] (iv)[B6a][B6c] (v)[7] (vi)[7] (vii)[10] (viii)[1] (ix)[3]
já verdes na cópia limpa (revisados): [10b] a Ficha não lê work_events · [B1a] marcar_fim grava SEM espelho (📊 E2 provada por execução) · [B1e] · [B2a/b] · [B7a/b]
2 guardas antigos MIGRADOS para execução (verdes em HEAD): test_o_clique_da_atendente_nao_apaga_da_fila.py (chama o mjs --fila-json; a regra nova nasce em [2])
· test_o_atendimento_termina_e_o_produto_sabe.py (52 ok; os 3 leitores de caminho fixo → _fonte_dos_contadores; sem mirror obrigatório; motivo = um dos 5 do CHECK)
```
## 5. Migration
`backend/supabase/migrations/20260905_01_spec097_episodio_tem_conversa.sql` — `attendance_sessions` ganha `conversation_id` (FK `ON DELETE SET NULL` — a conversa é o
espelho, o episódio é o fato), `resolvido_em`, `resolucao_motivo` (o MESMO CHECK da conversa, SPEC-086) e o índice `(company_id, conversation_id)`; APPLY/VERIFY/ROLLBACK
no arquivo; `COMMENT ON COLUMN` diz que o `status` fechado por 6 h do Atlas NÃO é desfecho (E9). Backfill `backend/scripts/backfill_097_episodio_tem_conversa.py`
(`--dry-run` padrão; normalização = a de `webhook.py::_conversa_do_telefone`): 📊 lidos 12.755 episódios · 728 conversas · **elos 1:1 a gravar 7.367 (57,8%)** ·
ambíguos 5 (não gravados) · órfãos 5.383.
**APPLY (📊 05/09 ~15:55, MCP `apply_migration spec097_episodio_tem_conversa`, PostgreSQL 17.6):** `{"success":true}`. A FK virou **COMPOSTA**
`(conversation_id, company_id) → conversations(id, company_id) ON DELETE SET NULL (conversation_id)` depois do red team P2-10 (a simples deixava o elo atravessar
corretora); `conversations` já tinha o índice único `(id, company_id)`.
**VERIFY:** V1 3 colunas nullable ✓ · FK `confdeltype='n'` com a definição composta ✓ · **V1.b** `cross-tenant recusado? t || mesma corretora aceita? t || outros:[]` ·
**V2** `motivo INVALIDO recusado? t || so metade recusada? t || motivo VALIDO aceito? t || outros:[]` · V3 2 índices ✓ · `com_elo=0 de 12.762` antes do backfill.
**Advisors:** security 133 (2 ERROR/9 WARN/122 INFO — nenhum novo; o único de `attendance_sessions` é o `rls_enabled_no_policy` que já existia) · performance
**269 INFO/49 WARN** (baseline 267/49): os +2 são `unindexed_foreign_keys` da FK composta (o índice `(company_id, conversation_id)` cobre a busca; o advisor
exige a ordem da FK) e `unused_index` do índice parcial recém-criado — ambos INFO, esperados.
**Backfill `--vivo` (📊 05/09):** 1ª corrida interrompida pelo shell em 6.168 elos; 2ª corrida (idempotente: `.is_('conversation_id','null')`) → `já ligados 6.168 ·
elos 1:1 a gravar 1.206 · GRAVADOS 1.206 · falhas 0 · VERIFY com_elo=7374 de 12762`. SQL independente: `com_elo 7.374 · únicos esperados 7.374 · ambíguos 5 ·
ambíguos gravados por engano 0 · cross_tenant 0 · resolvidos 0 · conversas resolvidas 0`. A regra do 9º dígito (P3-4) mudou ZERO elo: os dois lados já estavam na mesma
forma — o defeito era latente.
`backend/tests/fixtures/schema_vivo.json` e `backend/supabase/migrations/MANIFEST.md` atualizados no mesmo commit (`90ff89c`).
## 6. Guardas e mutações (📊 05/09, depois dos builders)
```
npm run test:casa                        [1]–[15] · 📊 86 asserções (40 de CONTROLE) · 0 falhas · VERDE (HEAD 45ffde0; [13] é REGRA, [14] schema vivo, [15] escrita+leitura)
  --mutar (runner por cópia)             📊 16 mutações · 16 VERMELHAS por nome · 0 verdes · árvore idêntica antes/depois (juiz reproduziu)
test_o_atendimento_sabe_como_terminou    46 ok · 0 falhas · --mutar em subprocesso: 3/3 por NOME (U9 → [B1a-f]; U10 → [B4a/b/d]; U12 → [B6d] "a IA volta a falar")
test_o_chat_fala_como_corretor (U7)      44 ok (juiz) · --mutar 3/3 (U7A → [B4b]; U7B → [B2b]; U7C → [B8a/b] label em toda comparação)
test_quem_fala_primeiro_cala_o_outro     migrado (exige pausar_ia) · test_o_atendimento_termina_e_o_produto_sabe 52 · test_o_clique 11 · test_o_espelho_vira_conversa 20 · saudacao 50 · pulso_360 284
(📊 os números de 42/38/2-de-2 da rodada 1 ficaram aqui até o juiz apontar — corrigidos em e424ccd+; §12.1)
atendimento-estados.test.mjs             66/66 (parado no vocabulário) · test_a_chave_de_juncao 25 · test_conversa_que_acabou 4 · test_handoff_chega 7
npx tsc --noEmit EXIT=0 · npm run test:rotas-montam VERDE
next build (📊 05/09 ~16:40, ae546f7)     exit 0 · 301 rotas · Middleware 94,7 kB
next start -p 3977 + requisições          Ready in 39,6s · GET /api/dashboard/atendimentos → 401 (o portão de sessão EXECUTOU) · /api/dashboard/atendimentos/casos → 401
                                          · /dashboard/atendimentos/fila → 307 (login) · /login → 200 · servidor parado por PID (§9.1: a rota que executa código responde)
mutações do mjs                          16 declaradas com {ancora, substituto, vermelho[]} · rodadas por cópia pela lente (19/26 na 1ª rodada) e pelo juiz (16/16)
```
## 7. O painel e o juiz
**Rodada 1 (05/09 ~14:00, red team ‖ lente do DADO sobre `7ae06fb`):**
- **Lente do DADO** (Opus, 146k): **REPROVOU o read model** — e o guarda de 1.362 linhas estava VERDE. `lib/atendimento/casos.ts` selecionava **três colunas que
  não existem** (📊 42703): `work_waits.attendance_session_id`/`due_at` (é `vence_em`; esperas sempre "indisponíveis"), `attendance_sessions.protocolo` (toda leitura de
  sessões falhava → Casos devolvia ZERO episódios) e `approval_requests.title` (é `preview`). Mais: ninguém escreve `attendance_session_id` na sessão de dispatch (o
  caminho "sem espelho" era morto); Encerrar a conversa derramava o desfecho sobre os 5,8 episódios do telefone (`conversa || sessao`); o cursor de Casos misturava
  dois relógios e dois espaços de chave (inócuo até o backfill ligar os elos); `semana.terminaram` voltava a contradizer a lista; a Fila filtrava o órfão pelo `status`
  de 6 h do Atlas (E9); tetos silenciosos novos sem `has_more`. Passou: os 📊 da §1 (5+ reproduzidos), a migration (CHECK idêntico ao da conversa, `ON DELETE SET NULL`,
  VERIFY/ROLLBACK), o backfill (7.374/5/5.383 = SQL independente), `pausar_ia` nos 3 pontos, zero PII, canário limpo.
  **A lição (a mesma da 094.1, agora na tela):** um dublê construído à mão concorda com o código por construção. `schema_vivo.json` ganhou as 6 tabelas do atendimento
  (`e3bb30d`) e o guarda [14] passa a construir o dublê a partir dele — coluna desconhecida devolve 42703 como o PostgREST.
- **Consertos:** tela/BFF (builder da tela, em curso: colunas reais; concluído ⇔ sessão; Encerrar grava no episódio corrente; cursor só da sessão; `semana` pela mesma
  regra; órfão parado pelo relógio único; tetos declaram `has_more`) · backend (builder novo: o corredor passa o episódio a `marcar_fim`; `ValueError` no motivo
  inválido; `pausar_ia` em `saudacao_do_religamento.py`; passo novo no canário).
**Red team** (Opus, 218k, 14 min, arneses `ataque-097-{a,b,c}.mjs` sobre o produto REAL transpilado + módulos python importados): **1 P0 · 3 P1 · 11 P2 · 8 P3**.
- 🔴 **P0-1 — a IA calava PARA SEMPRE naquele segurado.** `close` mantém o dono (R2, deliberado) e `pausar_ia` não olhava `resolvido_em`; o webhook reusa a
  mesma linha por telefone → toda conversa assumida-e-encerrada (o caminho feliz da Fila nova) deixava o segurado sem robô. Nenhum guarda media o depois
  do fim. **Decisão (nota 92):** a pausa é do atendimento VIVO — `pausar_ia` devolve `False` com desfecho escrito; os 3 selects que a alimentam
  (`webhook.py:631`, `chat.py:152/606`) passaram a trazer `resolvido_em` (sem isso o conserto não chegava à produção); a saudação do religamento recusa
  `atendimento_ja_encerrado`. Guarda `[B6d]` "a IA volta a falar depois que o atendimento termina" (3 controles), mutação U12 vermelha.
- **P1:** claim/release/send em conversa encerrada sobrescreviam/apagavam o autor e reabriam o status → 409 (P-097-REABRIR-ATENDIMENTO) · `has_more` só olhava
  `attendance_sessions` (o `.limit(120)` de §1.5 de volta com outro número) → do resultado unido · cursor paginava por um relógio e ordenava por outro → um campo só.
- **P2 (11):** Ficha de encerrada há > 7 dias voltava a "em conversa" · `semana.terminaram` × itens `concluido` no mesmo payload · motivo fora do CHECK sumia da conta ·
  `resolvido_em` no futuro aceito · cursor cru no `or()` do PostgREST (injeção de filtro dentro do tenant) · tetos de 2.000 com `indisponivel:false` · busca `_` casa tudo /
  `%` some · `error_message` cru ao corretor (R11) · canário com DELETE sem `company_id` · FK do elo sem par `(company_id, conversation_id)` → FK composta ·
  comparações ao modelo sem `label` (o caminho por onde `production.new_vs_renewal@1` chegou ao Founder) → `label` em toda comparação. **Todos consertados** (`8861143`, `8865192`).
- não quebrou: teto 1.001 em lotes; migration idempotente; backfill recusa `--vivo` sem migration; tenant nas 11 leituras; `pausar_ia` nos 3 portões.

**Lente de verdade/regressão** (Opus, 171k, worktree `../AutoBrokers-FIX-mut` em `8865192`): **REPROVOU com ressalva — 19/26 mutações vermelhas, 7 verdes.**
`[10]` era inatingível (a Ficha DESCARTAVA o evento sem hora: a §1 dizia "6 de 9 eventos com `at: null`" e o conserto os fez sumir em silêncio); U3 verde
porque a fixture não tinha o mundo defeituoso (`claimed_by` + `HUMAN_REQUESTED` na mesma linha); `[13]` guardava uma lista, não a regra (`detalhe: stage`
cru passava); `[7]` só observava Casos; M16 (derramamento do desfecho) só medido na escrita; `MUTACOES` do mjs era prosa; o `--mutar` do python saía `rc=1`
na árvore limpa ([C1] avaliado com U10 aplicada); `test_o_espelho_vira_conversa` VERMELHO (NameError `variantes_br`, efeito do P3-4). **Consertos** (`a455bf4`,
`45ffde0`): evento sem hora fica na timeline com `sem_hora` e "sem hora registrada"; fixture com dono+status; `[13]` vira regra (snake_case, `@N`, estágios/motivos
crus); `[7]` mede a Fila; `[15]` mede a leitura; `MUTACOES` com `{ancora, substituto, vermelho[]}` + runner `--mutar` por cópia (**16/16 vermelhas por nome**, árvore
idêntica); python: mutação em subprocesso, forma na fonte limpa (**3/3**), `--mutar <ID>`; espelho chama a regra real (20 passed). 📊 86 asserções mjs (40 de controle).

**Juiz fresco** (Opus, 145k, contexto limpo, HEAD 45ffde0→e424ccd só docs): **NOTA 93/100.** J1: **18 achados CONFIRMADOS CONSERTADOS por comando**
(P0-1 pelo canário Q4b com par Q2; os 3 P1 do red team; os 6 P1 do DADO); **nenhum conserto criou defeito**; 2 NÃO declarados (P3-5 reconferência de tenant →
P-097-RECONFERE-TENANT; busca por protocolo → não existe coluna: P-097-PROTOCOLO-SEM-CASA). J2: tudo verde (86/16-16; 46/3-3; 44; 4 migrados; rotas; tsc). J3 dado:
3 colunas nullable · 7.374/12.762 elos (57,78%) · 0 em par ambíguo · 0 cross-tenant · 0/729 conversas e 0 episódios com `resolvido_em` fora do canário · 0 sobras.
**J5 — a régua do §0 contra a Fila REAL da Resulta** (`projetarCasos` real sobre 272 conversas + 1.000 episódios, PII por SHA-256): 🔴 **`concluido: 0`** onde a régua
velha dava 584 fantasmas · **268 PARADOS** · **`com_equipe: 1`** já no acervo · encerrar → `concluido=1` E `semana.terminaram=1` no MESMO payload · R11: **1.263 textos
visíveis, 0 termos técnicos** · 📊 o contato mais ativo da Resulta tem **30 episódios para 1 conversa** (a tese de R3 medida). Três residuais do juiz: (1) §6 deste
relatório com números vencidos → corrigido; (2) `send` em encerrada "409 sem corpo" → verificado: os três verbos devolvem frase humana (`route.ts:167/195/454`);
o arnês do juiz leu o 409 anterior do dono (`:418`), que também tem corpo; (3) a busca empurra `conversation_id.in.(~200 UUIDs)` na URL → P-097-BUSCA-NA-URL.
## 8. Canário vivo
📊 05/09 20:09, Resulta, `AUTOBROKERS_CANARIO=1 python scripts/canario_097.py --vivo` (rodado pelo juiz fresco; sem Redis local, e não precisou):
```
Q1 abrir_espera → abriu=True | linhas=1 ativas=1 kind=esperando_seguradora → OK
Q2 CONTROLE (mesma conversa, SEM dono) → pausar_ia=False → OK · claimed_by preenchido, status=open → pausar_ia=True → OK
Q3 marcar_fim(episódio) → EPISÓDIO resolvido_em=…20:09:24 motivo=resolvido_pelo_segurado · CONVERSA espelhada no MESMO instante (E8) → OK
Q4 claimed_by depois do fim continua → OK · Q4b claimed_by + resolvido_em → pausar_ia=False → OK — a pausa é do atendimento VIVO (P0-1)
Q5 corredor SEM espelho → o EPISÓDIO recebe acionamento_concluido, elo gravado na sessão → OK · CONTROLE telefone sem episódio → '' → OK
limpeza 0/0/0 por id e corretora
```
Amandus → Resulta → AutoFleet: o canário grava só na Resulta (linhas próprias, removidas); Amandus é WhatsApp pessoal (fora por ordem do Founder); AutoFleet coberto pela
projeção real do juiz (J5) e pelos guardas com dois tenants ([11] cruzada).
## 9. O que ficou fora · pendências · a caixa do Founder
**Fora (com gatilho):** U4 espera com escritor (P-097-ESPERA-COM-ESCRITOR → a 097.1 escreve no pós-acionamento) · U6.3 drag (P-097-DRAG) · reabrir atendimento
(P-097-REABRIR-ATENDIMENTO, decisão) · protocolo durável (P-097-PROTOCOLO-SEM-CASA) · reconferência de tenant na projeção (P-097-RECONFERE-TENANT) · `telefone_br`
nas 2 cópias restantes (P-097-TELEFONE-BR-DUPLICADO) · coerência dos dois relógios (P-097-DOIS-RELOGIOS) · + as 7 abertas pelo desenhista (ESPERA, TIMELINE-CURSOR,
SESSOES-ORFAS, DOCUMENTOS-DO-ATENDIMENTO, APPROVAL-SEM-CONVERSA, POLLING-10S, DRAG). Total: **12 P-097-***.
**A caixa do Founder (097):**
1. Clicar **Implantar** (a `main` leva a 097 junto com a 096). Depois do deploy: abrir Atendimentos → Fila (Quadro/Lista), Casos, Ficha — no celular e no desktop — e
   dizer o que não está em português de corretora (R11) ou o que não cabe na primeira tela (R12).
2. **Reabrir atendimento** (P-097-REABRIR-ATENDIMENTO): quem pode, e o que acontece com o desfecho anterior.
3. Quando o WhatsApp for religado, o fluxo inteiro vale: a IA responde de novo depois do fim (P0-1 consertado), a atendente que assume cala a IA, e "Encerrar" grava
   o desfecho no episódio corrente — nada disso exige ação sua além do deploy.
## 10. Declarações
- Nenhum motor paralelo: sem tabela de casos, sem event store, sem escritor novo de ciclo de vida além dos que existem (marcar_fim/claim) — só estendidos.
- Nenhuma mensagem saiu; nenhum agente ligado; InfoCap só leitura; nenhum segredo/PII impresso.
## 11. Entrega
{PUSH}

# Relatório de execução — SPEC-093-B · O sinistro deixa rastro

> **v1 da SPEC, executada sob o protocolo v11 · nível CRÍTICO** · 03/09/2026 · branch
> `feat/spec093b-o-sinistro-deixa-rastro` · commit inicial `b70225f` · commit final de código `0ae5462`
> Orquestrador: Fable 5.1. Subagentes Opus 5: pesquisador · investigador · aquecimento · desenhista · 4 builders ·
> painel de 4 lentes · red team · juiz de confirmação · auditoria externa.

## 0.0 🔴 EXECUTION CARD

```
OUTCOME ..............  todo atendimento que fala de sinistro deixa um Work Run de sombra com log de eventos por ator, mesmo no
                        modo observação; um digest diário agrupa variantes e escreve sinais; a Central mostra o trabalhador;
                        NADA chega ao segurado e a conduta do atendimento não muda
RISCO ................  6   ALCANCE 2 · REVERSIBILIDADE 2 (linhas em work_runs/work_events/intelligence_signals sobram) · FREQUÊNCIA 2
SUPERFÍCIE ...........  3   o aquecimento derrubou o mapa da v1 (3 ponteiros errados; o caminho real do piloto não estava nele)
PISO APLICADO ........  nenhum por efeito; dado derivado de conversa de sinistro é sensível (ref. ⑦)
NÍVEL ................  CRÍTICO — desenhista ANTES do código · painel de 4 lentes · red team · auditoria externa · integrador
UNIDADES .............  7   BLOCO 0 · 0-bis (ELO) · A · B py · B next · C · D · E
COESÃO ...............  {A+B py} ‖ {B next} ‖ {C} só depois do 0-bis; D depois de C; E nasceu primeiro
PARALELISMO REAL .....  3 escritores simultâneos após o 0-bis; integração serial
TIME .................  ver cabeçalho
REFERÊNCIA ...........  interna: test_a_central_diz_a_verdade.py (forma) · dispatch_router.py:545-608 (run com conversa, evento com ator) ·
                        signal_service.py (dedupe) · test_o_portao_vale_no_backend.py:72 (JSON em lib/ lido pelos dois stacks)
                        externa (§7.3, 7 reabertas em 03/09): OCEL 2.0 · Celonis · agentevals · ARISE · Sprout.ai · CNSP 496/2026 · GDPR 89(1)
GATES ................  A ⓪–⑧ · B ①–⑥ · C ①–⑦ · D ①–④ · E (3 mutações) — estado na §7
O ELO ................  (i) detecta → (ii) o humano age → (iii) vira variante. 📊 O aquecimento provou que (i) estava QUEBRADO como escrito:
                        webhook.py:783 retorna antes do grafo com os 4 agentes attendance inativos. GATE ZERO dinâmico prova (i) no modo
                        observação; (ii) é o botão Assumir do painel; (iii) é o teste de ponta a ponta E⑧
FAIXA DE RELÓGIO .....  declarada 8–13h · 📊 realizada: conversão 02:40→04:10 (1h30) · execução 04:10→03/09 ~09:55 (push) (📊 ~5h45 de execução · 7h15 do primeiro despacho ao push, incluindo ~40 min parados pelo 429 — ABAIXO da faixa de 8–13h)
```

### 🔴 As três perguntas que fecham o card
```
o painel rodou sobre CÓDIGO?          sim: 4 lentes + red team Opus, contexto limpo, sobre o diff origin/main..HEAD, depois do verificador e da suíte inteira com árvore parada
conserto criou defeito?               sim, UM, medido pelo juiz de confirmação e consertado (8662644): a tranca de venda vetava sinistro real (~9,5% das sessões); depois a auditoria externa achou 2 blockers de dataset que NENHUM painel viu (documento em PDF sem evento · variante = contagem de mensagens) — UM builder Opus, rodada única, commits `556a8c4` + `0ae5462`: o PDF do boletim deixa rastro (`nome_do_documento` lê o `fileName` do payload e a MARCA no texto; `tipo_de_documento` cobre crlv/laudo/foto_dano pelo nome do arquivo; um só `registrar_gesto`, antes do `return`); a variante colapsa repetição CONSECUTIVA (`groupby`) e leva `repeticoes={tipo:{media,maximo}}` ao metadata; A-01 o corte `not.in.(claims_shadow)` vai para a CONSULTA de `SignalService.ativos`; A-02 marca 📊 reescrita com a verdade (`git grep -c ficha_atendimento origin/main -- webhook.py` → 0: o custo é novo); A-03 memória de ausência expira (60 s sombra · 300 s ficha). Blocos novos [5b] [14g] [17]; guarda **249 ok** (era 220); mutações por cópia vermelhas: `if final_image_url` sem documento → `gravou 0`; assinatura sem colapso → 2 variantes; `_lembrar` sem TTL → FALHA A-03. Defeito extra achado pelo guarda: `webhook.py` não importava `re` (o import dinâmico levantava e dois blocos PULAVAM em silêncio) — corrigido. Fora: `sem_documento` fica inteiro (agora instrumentado para imagem E documento; áudio fora de propósito); P-093B-ECO e P-093B-BUFFER registradas
o que sobrou é MATERIAL?              não — o que sobrou é pendência com dono (RAMO, SEGURADORA, ECO, TELA, LGPD); nenhuma muda o que a corretora lê no piloto, porque a sombra não chega ao briefing (C0) e o digest só nasce com sombra real
```

## 0.1 O PROTOCOLO AAA — telemetria (§11)

```
começou / terminou                     03/09 02:40 (pesquisador + investigador) / 03/09 ~09:55 (push)
tempo até a PRIMEIRA linha de código   📊 1h25 (02:40 → 04:05, helper `criar_registro_sem_fila`, commit fb1ad32) — inclui pesquisa, medição, SPEC, aquecimento e o guarda nascido antes do código (helper 0-bis, commit fb1ad32 às 04:0x)
rodadas de painel                      1 painel (4 lentes + red team) → 1 rodada de conserto → juiz de confirmação → auditoria externa
achados por lente                      lente 1: 3 blockers + 8 pend · lente 2: 0 + 4 · lente 3: 0 + 5 · lente 4: 3 + 8 · red team: 5 quebrados + 4 menores. Únicos: 7 blockers, ~14 pendências; 3 blockers achados por 2+ frentes
defeitos que o painel NÃO pegou        o `.limit(2000/20000)` do digest (guarda do repo, na integração); pytest órfãos de juízes mutando scripts (orquestrador, `git status`)
rodadas da bateria                     📊 diário do conftest 03/09: suíte inteira 3× (uma antes do painel com árvore parada, 933/3; duas por juízes em paralelo com mutação, contaminadas — não contam como gate); parciais ~40 (2–65 s). Fração do relógio: 💭 ~12% incluindo a rodada que vale
nota 0–100 do orquestrador             88/100 — 7 blockers do painel + 1 do juiz de confirmação + 2 da auditoria externa, todos fechados e provados por mutação; ELO medido em produção; zero migration. Perde por ramo/seguradora ainda `desconhecido` em toda variante (P-093B-RAMO), pelo eco possível do `humano_respondeu` (P-093B-ECO) e por um digest que só se prova de verdade com sombras reais do piloto
```

## 0. Declaração de integridade

Nenhum motor paralelo: a sombra é um `workflow_key` em `work_runs`, o ledger é `work_events`, as
esperas são `work_waits`, os sinais são `intelligence_signals`. **Zero migration.** O INSERT direto
que só o acionamento sabia fazer virou um helper único (`criar_registro_sem_fila`) e o acionamento
passou a usá-lo: consolidação, não duplicação (CLAUDE.md §5). Nenhuma mensagem saiu; nenhum agente
foi ligado; a conduta do atendimento (prompt, playbooks, `infer_ramo_servico`, `graph.py`) não mudou
um byte; nenhum texto de segurado entra na sombra; nenhum dado pessoal foi impresso.

## 1. Resumo executivo

**FATO — antes.** 📊 Não existe objeto "caso". A classificação de sinistro é recalculada e descartada
(`servico` NULL em 12.616 de 12.616 sessões). O handoff do robô nunca disparou (`HUMAN_REQUESTED` = 0;
a tool está desligada nos 8 agentes). A anotação da atendente tem porta e zero uso. Zero eventos com
ator humano em 35.705. E o motivo de tudo isso, medido no aquecimento: com os 4 agentes de atendimento
inativos, o webhook **retorna na linha 783** antes de qualquer fluxo de IA — o classificador não é
chamado, a ficha nunca é gravada. A palavra exata "sinistro" aparece em 94 a 222 sessões por mês.

**Depois.** Toda mensagem de segurado atravessa o gancho em `webhook.py` ANTES do `return` do modo observação; se
fala de sinistro (regra: "sinistro" sozinho, ou verbo de ocorrência + palavra de dano, nunca com palavra de venda),
nasce UM Work Run `claims.shadow` por conversa, sem fila, idempotente pelo par (corretora, conversa). Cada gesto
já existente vira `work_events` com ator do CHECK e payload só de enums (validados nos dois stacks): Assumir,
Devolver, Encerrar e nota pelo painel (Next); nota pelo celular, resposta da atendente, documento, espera aberta e
satisfeita, handoff do robô (Python). Um digest diário agrupa as sombras em variantes (sequência ORDENADA de
eventos) e escreve sinais `process_variant` e `claims_shadow_resumo` com os cinco contadores e denominador, ou
`não instrumentado` onde não há escritor (espera de seguradora, prazos). O trabalhador "Sombra de sinistros" está
na Central; o admin tem `GET /api/admin/spec034/claims-shadow`. A sombra NÃO chega ao briefing da corretora
(`FindingEngine` exclui `claims_shadow`). 📊 Medido em produção em 03/09: 0 sombras, 0 eventos `claims.*`, 0 sinais
— a rota devolve o contrato zerado, que é o gate D③. O acionamento ficou byte a byte idêntico ao da `main`.

**INFERÊNCIA.** No piloto de terça, cada conversa de sinistro deixa uma sombra desde a primeira
mensagem, mesmo com o robô em silêncio; cada Assumir, Devolver, Encerrar e `#nota` da Regina vira
evento; em 30 dias o digest tem material para a primeira variante — e a Central mostra o trabalhador
"Sombra de sinistros" amarelo até lá, o que é a verdade.

## 2. Escopo executado por bloco

| bloco | o que entregou | gates | commit |
|---|---|---|---|
| **0** | remedição: `source_type` CHECK sem 'conversation' · `human_handoff.enabled` false/ausente em 8 de 8 · `work_events actor_type` CHECK sem 'human' · `work_waits` e `intelligence_signals` com 0 policies · sinistro exato 94–222 sessões/mês | ①–⑤ ✓ | `5bfea64` |
| **0-bis** | GATE ZERO dinâmico (webhook no modo observação, sentinela no billing, cliente falso) · `criar_registro_sem_fila` extraído do acionamento (150 testes verdes antes e depois; 8 novos; 3 vermelhos por mutação) · linha de base da regressão: máquina de lavar 112 ok · golden 1 caso explodido / 14 asserções | ①②③ ✓ | `5957eb2` `fb1ad32` |
| **A** | `claims_shadow.py` (632 linhas): `detectar_sinistro` (regex estrito + regra de par "bati … carro"; `terceiro` não abre), `abrir_sombra` via `criar_registro_sem_fila` (idempotente por conversa, `source_type='chat'`, `runtime_kind='sombra'`); gancho em `webhook.py:715`, ANTES do `return` do modo observação (:783), em `try/except` que nunca sobe. GATE ZERO dinâmico verde. Regressão idêntica antes/depois (112 ok · 1 caso/14 asserções) | ⓪①②③⑤⑥⑦⑧ ✓ (④ dois tenants: contra o banco, hoje 0 e 0 — o guarda diz) | `e6d0335` |
| **B py** | `registrar_evento`/`registrar_gesto` com vocabulário de `lib/atendimento/claims-shadow-vocab.json`; payload só enums (`contem_pii` sobre `json.dumps`); sem sombra não grava; eventos em `human_handoff.py:658`, `a_nota_da_atendente.py:216`, `webhook.py:1532` (humano_respondeu), documento_recebido, `o_fim_do_atendimento.py:278/:345` (espera aberta/satisfeita com `work_run_id` da sombra). Mutação (texto no payload) → 15 falhas, restaurado | ①②③⑥ ✓ (⑤ sha256 igual nos dois stacks: `1ba7d09f…`) | `e6d0335` |
| **B next** | motor `lib/atendimento/claims-shadow.ts` com vocabulário injetado (TS 5.2.2 × Node 24); Assumir/Devolver/Encerrar/nota/resposta → `work_events` `actor_type='user'`, só com sombra, payload só enum/bool/slug, anti-duplo-clique, registrado depois da entrega ao segurado; guarda 71 ok, 3 mutações vermelhas; sha256 do vocabulário igual ao do Python | ①②③⑤⑥ ✓ | `0f6f1da` |
| **C** | `claims_shadow_digest.py` (ponte `work_events` → trajetória ordenada por `created_at`, desempate estável por `id`) + `prazos_regulatorios.py` (CNSP 496/2026 com vigência; regime anterior `valor=None`); workflow `intelligence.claims_shadow_digest` agendado 24h pelo modelo do garimpo; sinais `process_variant` e `claims_shadow_resumo` (a taxonomia fechada em `schemas.py` ganhou os dois tipos e o domínio `sinistro` — sem isso o digest gravaria ZERO em silêncio); `sombra_sinistros` em `AGENT_TASKS`; `claims.shadow` em `SEM_CARD_POR_DECISAO`. Fio de ponta a ponta com cliente falso: 3 sombras → 1 variante de 5 passos → 2 sinais. O builder evitou um motor paralelo (variantes duplicadas) importando as funções puras do BLOCO A | ①②③④⑤⑥⑦ ✓ · Central 509 ok | `e6d0335` |
| **D** | `GET /api/admin/spec034/claims-shadow`: `require_master_admin`, cache Redis 60s, quatro leituras paginadas (≤1000, `truncado` declarado), agregação pelas funções puras do digest, contrato exportado em código (`CLAIMS_SHADOW_CHAVES*`); banco vazio → zeros sem erro; nenhum campo textual. As duas leituras do digest (2.000 e 20.000 linhas) passaram a `ler_paginado` — o guarda do repo `test_ninguem_pede_mais_de_mil_linhas_de_novo` voltou ao verde | ①②③④ ✓ · bloco [11] 18 asserções · 2 mutações vermelhas | `7cd225b` |
| **E** | `test_o_sinistro_deixa_rastro.py` (1.630 linhas, 11 blocos) nascido ANTES do código: 52 ok · 4 vermelhos esperados · 7 pulados com o motivo certo | 163 ok · 0 falhas · 0 pulados ao fim da integração; 3 mutações da SPEC + 4 dos builders vermelhas | `5957eb2` |

### Correções que a execução fez à SPEC, com o número dos dois lados
- Aquecimento (nota 68): o gancho em `:709` ficava DEPOIS do `return` de `:783`? Não — ficava no texto da v1 "onde a ficha existe", que nunca existe. Movido para `:710`, dentro do `try` do INSERT em `messages`, com GATE ZERO.
- `WorkRunService.criar` e o RPC não aceitam `conversation_id` (16 parâmetros, zero conversa) → helper sem fila extraído do acionamento.
- Vocabulário em `backend/` → `lib/atendimento/` (o Next não importa nada de `backend/`; precedente `portao-do-prompt.contract.json`).
- `test_golden_do_eletricista.py`: a SPEC dizia "1 vermelho"; medido **1 caso explodido e 14 asserções** — a linha de base tem os dois.
- `return` do modo observação: `:782` (aquecimento) × `:783` (desenhista) → medido pelo orquestrador: **:783**.
- BLOCO 0-bis: `criar_registro_sem_fila` extraído do acionamento em vez de estender o RPC (que enfileiraria um run sem handler).
- Vocabulário: `claims.seguradora_respondeu` REMOVIDO (v2) — 📊 zero escritores; `motivo_enum` e `regex_ocorrencia` acrescentados.
- `test_o_atendimento_termina_e_o_produto_sabe.py:531` (SPEC-086): o fato mudou (um SELECT de `work_runs` antes e depois do INSERT em `work_waits`); a lição migrou para "o INSERT está NAS chamadas e nenhum SELECT de work_waits sem corretora depois".
- O detector foi além do "regex estrito" do texto da SPEC (CHANGE-ADDENDA 03/09): 17 frases fixadas no guarda.

## 3. Arquivos alterados

```
NOVOS     backend/app/services/claims_shadow.py (632) · claims_shadow_digest.py (~520) · prazos_regulatorios.py (199)
          lib/atendimento/claims-shadow-vocab.json (67) · lib/atendimento/claims-shadow.ts · scripts/claims-shadow-vocab.test.mjs ·
          scripts/claims-shadow-eventos-do-painel.test.mjs · backend/tests/test_o_sinistro_deixa_rastro.py (~1.850) ·
          backend/tests/test_o_run_sem_fila.py (233)
TOCADOS   backend/app/services/work/runs.py (+147 helper) · dispatch_router.py (delega) · webhook.py (+113) · human_handoff.py (+26) ·
          a_nota_da_atendente.py (+27) · o_fim_do_atendimento.py (+66) · intelligence/{workflows,tick,schemas}.py · core/heartbeat.py (+30) ·
          api/admin_spec034.py (+365) · app/api/dashboard/conversas/[id]/route.ts (+91) · package.json (+2 scripts) ·
          backend/tests/test_acionamento_sobrevive.py (+7, carregador)
```

## 4. Migrations

**Nenhuma.** ROLLBACK escrito na SPEC §7 (DELETE das sombras, eventos e sinais `claims_shadow`), só por decisão do Founder.

## 5. Testes executados — saída real

```
python backend/tests/test_o_sinistro_deixa_rastro.py         → 220 ok · 0 falhas · 0 pulados   (16 blocos; era 145 → 163 → 220)
python -m pytest tests/test_o_atendimento_termina_e_o_produto_sabe.py tests/test_o_sinistro_deixa_rastro.py  → 53 passed (nas duas ordens)
python backend/tests/test_o_run_sem_fila.py                  → 8 passed (3 vermelhos por mutação: thread_id constante, SELECT sem company_id)
python backend/tests/test_a_central_diz_a_verdade.py         → 509 ok (SPEC-088 continua verde com o trabalhador novo)
python backend/tests/test_ninguem_pede_mais_de_mil_linhas    → TUDO VERDE (o digest paginado tirou o guarda do repo do vermelho)
python backend/tests/test_o_protocolo_tem_policia.py         → 41 ok (esta SPEC passa no bloco [8]; este relatório no [7])
pytest -k "acionamento or dispatch_router or o_fim_do_atendimento or travamento or espera"  → 165 passed, 1 xfailed
pytest tests/test_acionamento_sobrevive.py                   → 13 passed
node scripts/claims-shadow-vocab.test.mjs                    → 15 ok  (sha256 v2 e5fba5df… idêntico nos dois stacks)
npm run test:claims-shadow-painel                            → 71 ok · 3 mutações vermelhas
npx tsc --noEmit -p .                                        → exit 0
npm run test:rotas-montam                                    → 293 rotas montam
npx next build                                               → Compiled successfully (14,3 min)
next start -p 3112 + GET /api/dashboard/conversas/abc        → 401 {"error":"Não autorizado"}   ← código executando (CLAUDE.md §9.1)
                     GET /api/admin/spec034/claims-shadow    → 401
REGRESSÃO como script, origin/main × HEAD (lente 3, worktree):
  test_a_maquina_de_lavar_vai_ate_o_fim.py   112 verdes / 0 vermelhas   nos dois
  test_golden_do_eletricista.py              14 problemas · gold_007 KeyError 'live'   nos dois, item a item
suíte inteira (árvore parada, antes do painel)              → 933 passed · 3 failed (os 3 passam isolados: 086 por ordem → migrada; 2 do harness de mutação)
suíte inteira (depois do conserto)                          → 934 passed · 2 failed · 39 xfailed · 1 xpassed em 13m12 (09:34→09:47, árvore parada, commit 0ae5462). Os 2: `test_ontologia_e_unica` (passa isolado — classe P-093B-FLAKY) e `test_a_arvore_ficou_limpa_no_fim` (um guarda-script mutou `corridor_playbooks.py` e estourou o tempo; o harness RESTAUROU — P-093B-HARNESS, pré-existente, diff vazio contra a main). Nenhum dos 2 toca a 093-B
```
**Mutações provadas vermelhas (restauradas por cópia):** payload com texto (11–15 falhas) · variante sem ordem (2) · tenant Python sem `company_id` (bloco [12], vermelho — antes passava cego) · gancho depois do `return` (2: estrutural + dinâmica) · `.ts` sem `company_id` (43) · `thread_id` constante e SELECT sem `company_id` no helper (3) · Next: chave intrusa, sombra retroativa, `event_type` só no route (2, 3, 1) · filtro do cartógrafo (na Central, 1).

## 6. O painel — 4 lentes + red team, contexto limpo, sobre o diff

Quatro lentes Opus 5 + red team, contexto limpo, sem o relatório dos builders, depois do verificador mecânico
(guardas verdes, suíte inteira com árvore parada: 933 passed · 3 failed, os 3 passam isolados).

| frente | veredito | nota | o que achou de único |
|---|---|---|---|
| verdade e ELO | PASS c/ pend. | 79 | ELO executado ponta a ponta (webhook real no modo observação → sombra → eventos → digest → sinal). Blockers: contador de seguradora conta espera de humano; o digest não tem um gate (mutação sem ordem + zero sinais passou cega); a mutação de tenant do Python passa cega |
| PII, tenant, minimização | PASS c/ pend. | 84 | nenhum vetor vivo de vazamento; o Python valida só TAMANHO do valor (o Next valida enum e slug), frase sem dígito passa pelo `contem_pii`; `ramo`/`seguradora_slug` viajam para `metadata` do sinal sem redação |
| regressão do atendimento | PASS c/ pend. | 84 | nenhum byte a mais para segurado, atendente ou URA: acionamento idêntico byte a byte em `origin/main` × HEAD; gancho resiste a sabotagem; +1 round-trip por mensagem; um guarda da 086 fica vermelho na configuração de produção (a última chamada deixou de ser o INSERT) |
| produto e guarda | FAIL | 79 | a sombra CHEGA ao briefing da corretora pelo `FindingEngine` (📊 2.097 runs de `detect_signals` em 30 dias, 131 briefings enviados), quando C0 prometia silêncio; dois contadores e os prazos são zero por construção e saem como medidos; mutação de tenant obrigatória não fica vermelha; `digerir()` sem teste |
| red team (10 ataques) | 5 quebrados · 10 resistiram | conf. 82 | detector: 12 de 14 frases não-sinistro abrem, 📊 16,4% das conversas do acervo abririam, 15% com palavra de venda; nota do painel grava DOIS eventos com `tem_numero` contraditórios; `truncado` calculado e jogado fora antes do sinal; validação de enum inexistente no Python; teto de leitura por lote. Resistiram: corrida de duas sombras (índice único `uq_work_runs_company_idempotency`), cache entre corretoras, `fromMe`/URA não abrem, tenant por `conversation_id` no Next, dados podres no digest, prazos com entrada inválida, exceção no gancho, vocabulário mutilado |

**Fundido e classificado pelo TESTE DO PRODUTO (§2): 7 blockers únicos e ~14 pendências materiais, consertados
JUNTOS numa rodada (builder de código ‖ desenhista do guarda):**

| # | achado (quem) | teste do produto | conserto |
|---|---|---|---|
| B1 | sombra vaza para o briefing da corretora (lente 4) | muda o relatório que o PRODUTO gera | `FindingEngine`/`SignalService.ativos` excluem `source_type='claims_shadow'`; guarda [14a] |
| B2 | detector impreciso (red team) | envenena o dataset: 1 em 6 conversas vira sombra, 15% venda | palavra de venda exclui; verbo de ocorrência obrigatório fora de "sinistro"; 17 frases fixadas no guarda [14b]; CHANGE-ADDENDA |
| B3 | contador "espera de seguradora" conta espera de humano (lentes 1, 4; red team) | número do relatório com rótulo errado, 100% do piloto | conta por `kind`; sem escritor → `None` + `nao_instrumentado` no summary e no JSON |
| B4 | nota do painel grava 2 eventos com `tem_numero` contraditórios (red team) | inventa um passo na variante | Python só emite pelo WhatsApp; `tem_numero` = 6+ dígitos nos dois stacks |
| B5 | `truncado` morre antes do sinal · teto por lote (red team) | número menor que a verdade com cara de verdade | `truncado` no `metadata` e no summary; teto total across lotes |
| B6 | Python não valida enum/forma do valor (lentes 1, 2; red team) | contrato "zero texto" só vale no Next | `_valor_limpo` valida enum e slug (mesma regex do TS); `actor_type` do vocabulário; guarda [14c] |
| B7 | digest e tenant Python sem guarda (lentes 1, 4) | aceite não provado (§9.1 material) | blocos [12] e [13]: dois tenants pelo motor (mutação vermelha), `digerir()` ponta a ponta, dedupe 2×, truncado |
| P | `claims.seguradora_respondeu` sem escritor (lente 1) | vocabulário promete o que ninguém escreve | removido do vocabulário (v2); P-093B-SEGURADORA |
| P | guarda da 086 vermelho em produção; cascas de pacote não restauradas (lente 3) | suíte mente por ordem | asserção da 086 migra (o fato mudou); `sys.modules` restaurado no fim do guarda |
| P | +1 SELECT de ficha por mensagem; `_MEMORIA` sem negativo nem teto (lente 3) | custo no caminho quente | ausência de ficha e de sombra memorizadas por conversa, com teto |
| P | `_cliente(db)` fora do try; `dias` negativo; data como int (red team) | invariante "nunca levanta" falsa | consertados |
| P | `ramo`/`seguradora_slug` sempre desconhecidos (lentes 2, 4; red team) | variante degenera em (corretora, sequência) | P-093B-RAMO: precisa da ficha/apólice, fora desta rodada |
| P | `message_human` diverge entre stacks (lente 4) | duas vozes na linha do tempo | P-093B-TEMPLATES |

**Defeitos que o painel NÃO pegou e quem pegou:** o `.limit(2000/20000)` do digest foi pego pelo guarda do repo
`test_ninguem_pede_mais_de_mil_linhas` na integração, antes do painel; os pytest órfãos deixados por juízes mutando
`replay.py`/`rubrica.py` foram pegos pelo orquestrador no `git status` (P-093B-HARNESS).

### Juiz de confirmação
Opus 5, contexto limpo, sobre o diff do conserto (7cd225b → c1cb4c1). **PASS COM PENDÊNCIAS · 87.** Os 7 blockers do
painel foram conferidos um a um, cada um com a mutação refeita pelo juiz (ex.: `SOURCE_TYPES_INTERNOS=()` ⇒ `[14a] FALHA B1`;
`M3` sem `company_id` ⇒ a corretora B enxerga a sombra da A). **E o conserto criou UM defeito, medido:**

```
📊 03/09 · detectar_sinistro() · a tranca de venda rodava ANTES do verbo de ocorrência
NAO  | bati o carro, minha apolice tem cobertura?
NAO  | colidi com outro carro, tenho cobertura para terceiros?
NAO  | abri um sinistro e queria saber o preco da franquia
📊 acervo (attendance_transcripts, SELECT sem texto): 488 de 3.786 mensagens com `sinistro` carregam palavra de venda
   na mesma frase → 1.663 de 1.837 sessões ainda abriam (a tranca custava ~9,5%)
📊 segunda perda: voz passiva e `acidente` solto — 4 + 25 de 12.417 sessões (0,23%)
📊 e o outro lado do mesmo par: 14 frases NÃO-sinistro — v1 abria 10/14 falsas, v2 abre 0/14
```

**O que o guarda não via (CLAUDE.md §9.5):** as 17 frases fixadas não tinham UMA de sinistro genuíno com palavra de
cobertura ao lado. **Conserto (8662644):** ocorrência em 1ª pessoa (ou "bati" + alvo veicular) abre sempre; "sinistro" +
palavra de venda só é vetado sem verbo de ABERTURA (abrir/acionar/comunicar/registrar); voz passiva entra. 7 frases novas
em ABREM (24 fixadas), "quero fazer uma cotação de sinistro" continua em NÃO ABREM. `220 ok`. As outras 5 perguntas do
pacote: memória de ausência sem TTL (📊 683 conversas, teto de 5.000 nunca descarta) → virou conserto A-03 da auditoria;
`_valor_limpo` descartar chave é o comportamento desejado (o gesto aconteceu, o qualificador não); demais OK.

### Auditoria externa (§6.1)
Opus 5, contexto limpo, com SELECT em produção e os guardas rodados por ela (evidência colada no relatório dela:
tsc verde · 293 rotas · 15 / 71 / 220 / 509 / 8 ok · índices `uq_work_runs_company_idempotency` e `ix_work_runs_conversa`
confirmados no banco · multi-tenant: todo INSERT/SELECT novo carrega `company_id`). **FAIL · 71 · 2 BLOCKERS de produto,
ambos no dataset que é o OUTCOME — e nenhum painel os viu:**

| # | achado | medição da auditora | teste do produto |
|---|---|---|---|
| **A1** | o documento do sinistro não deixa rastro: `claims.documento_recebido` tinha UM escritor, atrás de `if final_image_url` — só imagem; o PDF do boletim entra no ramo `document` como texto | 📊 sessões que falam de sinistro: 1.060 imagens · 730 documentos inbound → **40,8%** dos arquivos não viravam evento; 97,4% das imagens caíam em genérico | `sem_documento` saía como inteiro com denominador e SEM bandeira — "31/40 sem documento" leria como "a operação não pede papel" |
| **A2** | a variante contava quantas vezes a atendente digitou: `humano_respondeu` é 1 evento por mensagem e a assinatura guardava repetições | 📊 1.851 sessões reais reconstruídas: as 8 maiores "variantes" eram `RRRR 217 · RR 200 · RRRRRR 120 · R 117 …` | um histograma de mensagens com cara de descoberta de processo; Celonis define variante sobre ATIVIDADES |

Pendências materiais: A-01 filtro do briefing DEPOIS do teto de 200 linhas · A-02 comentário 📊 descrevendo estado que
nunca existiu na `main` · A-03 memória de ausência sem TTL (com 2 réplicas descarta gestos em silêncio) · A-04
`humano_respondeu` pode duplicar painel + eco `fromMe`. Ela também registrou que a árvore mudou debaixo dela (o conserto do
juiz de confirmação) — não restaurou nada e o conserto não tocava nos blockers dela.

**Rodada de conserto pós-auditoria:** UM builder Opus, rodada única, commits `556a8c4` + `0ae5462`: o PDF do boletim deixa rastro (`nome_do_documento` lê o `fileName` do payload e a MARCA no texto; `tipo_de_documento` cobre crlv/laudo/foto_dano pelo nome do arquivo; um só `registrar_gesto`, antes do `return`); a variante colapsa repetição CONSECUTIVA (`groupby`) e leva `repeticoes={tipo:{media,maximo}}` ao metadata; A-01 o corte `not.in.(claims_shadow)` vai para a CONSULTA de `SignalService.ativos`; A-02 marca 📊 reescrita com a verdade (`git grep -c ficha_atendimento origin/main -- webhook.py` → 0: o custo é novo); A-03 memória de ausência expira (60 s sombra · 300 s ficha). Blocos novos [5b] [14g] [17]; guarda **249 ok** (era 220); mutações por cópia vermelhas: `if final_image_url` sem documento → `gravou 0`; assinatura sem colapso → 2 variantes; `_lembrar` sem TTL → FALHA A-03. Defeito extra achado pelo guarda: `webhook.py` não importava `re` (o import dinâmico levantava e dois blocos PULAVAM em silêncio) — corrigido. Fora: `sem_documento` fica inteiro (agora instrumentado para imagem E documento; áudio fora de propósito); P-093B-ECO e P-093B-BUFFER registradas

**Por que a auditoria externa pagou o custo (§6.1, nível CRÍTICO):** 4 lentes + red team + juiz de confirmação olharam
o CÓDIGO e o guarda; só a auditora reconstruiu o dataset que o produto vai gerar **sobre o acervo real** e perguntou se
ele diz a verdade. É a diferença entre "o motor funciona" e "o número que sai dele é honesto".

## 7. Gate da SPEC

```
GATE ZERO ......... ✅ VERMELHO em HEAD antes do código (bloco [0] dinâmico: modo observação, botão Assumir, E⑧); VERDE depois
GUARDA DA SPEC .... ✅ backend/tests/test_o_sinistro_deixa_rastro.py → 249 ok · 0 falhas · 0 pulados (16 blocos + 5b + 14a–g + 17)
VOCABULÁRIO ....... ✅ sha256 v2 idêntico nos dois stacks (15 ok Node · bloco [1] Python)
DOIS TENANTS ...... ✅ pelo motor, no banco e no fake, mutação M3 vermelha (a B enxerga a A sem o filtro)
PAINEL ............ ✅ 4 lentes + red team → 7 blockers → rodada única → juiz de confirmação PASS 87 (1 defeito criado, consertado em 8662644)
AUDITORIA EXTERNA . ✅ FAIL 71 → 2 blockers de dataset consertados (556a8c4, 0ae5462) → guarda 249 ok
REGRESSÃO ......... ✅ acionamento byte a byte igual à main · máquina de lavar 112/112 · golden 14 problemas nos dois (pré-existente) · 53 passed
§9.1 .............. ✅ tsc 0 · 293 rotas · next start + GET /api/... → 401 JSON
SUÍTE INTEIRA ..... 934 passed · 2 failed · 39 xfailed · 1 xpassed em 13m12 (09:34→09:47, árvore parada, commit 0ae5462). Os 2: `test_ontologia_e_unica` (passa isolado — classe P-093B-FLAKY) e `test_a_arvore_ficou_limpa_no_fim` (um guarda-script mutou `corridor_playbooks.py` e estourou o tempo; o harness RESTAUROU — P-093B-HARNESS, pré-existente, diff vazio contra a main). Nenhum dos 2 toca a 093-B
ENTREGA ........... 03/09 09:5x — `git push origin HEAD:main` (código, 0ae5462):
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   b70225f..0ae5462  HEAD -> main
```
(o relatório e o INDICE subiram no commit seguinte)
```
**Veredito do orquestrador: GATE VERDE — SPEC-093-B CONCLUÍDA** com as pendências da §8 (todas com dono).

## 8. O que ficou pendente (§11.1)

```
P-093B-LGPD      🧑 a base legal brasileira não foi lida (planalto.gov.br ECONNRESET; ANPD sem guia final). Antes de qualquer uso
                 cross-tenant ou global: leitura da LGPD art. 5º, 7º, 11 e 12 com jurista.
P-093B-CLASSIF   templater.py:1726 `servico or "sinistro"`: assistência vence sinistro. Muda conduta → F-093B-01.
P-093B-CANDIDATO knowledge_candidates = 0 em produção; a sombra escreve só sinais até o adapter ser exercido.
P-093B-SAUDE     redaction_service sem padrão de saúde (CID, laudo). A sombra não guarda texto; o serviço canônico continua incompleto.
P-093B-RLS       12 tabelas de aprendizagem com RLS ligado e 0 policies (herda P-090-01); work_waits e intelligence_signals entre elas.
P-093B-CORPUS    o gold corpus (4 perguntas da ref. ③) só existe com 20+ trajetórias humanas reais. Medir em 14 dias de piloto.
P-093B-TERCEIRO  🧑 2.187 sessões históricas com palavras de sinistro NÃO viraram sombra (sem retroativo). Backfill é dado antigo de segurado.
P-093B-TELA      a atendente não vê a sombra; a nota `#nota` continua sem tela que a exiba.
P-093B-GOLD      📊 golden_do_eletricista: 1 caso explodido (gold_007 KeyError 'live') e 14 asserções vermelhas ANTES desta SPEC; o pytest
                 só coleta o teste de existência dos 10 casos (guarda que carimba, CLAUDE.md §9.4).
P-093B-MAQUINA   test_a_maquina_de_lavar_vai_ate_o_fim.py crasha a coleta do pytest (sys.exit no módulo, :665); como script, 112 ok.
P-093B-NOTA-2SEDES  a nota tem duas sedes (notas_da_atendente · messages.payload.nota_interna) e zero leitores.
P-093B-REQS      📊 este ambiente não tem os requirements do backend (slowapi, redis, presidio, qdrant, fastembed…): guardas que importam
                 app.api.webhook só rodam por shim. Decidir se o CI instala backend/requirements.txt.
P-093B-SERVICES-INIT  app/services/__init__.py importa 14 serviços; importar um submódulo paga a árvore inteira e mascara o motivo de skip.
P-093B-FLAKY     📊 test_a_politica_de_autorizacao_passa e test_ontologia_e_unica ficam vermelhos na bateria completa quando há escrita
                 paralela na árvore e passam isolados (3 vezes esta noite). Classe P-088-MUT.
P-093B-FICHA-TTL  memória de ausência (ficha/sombra) — consertada com TTL/sem negativo de sombra na rodada pós-auditoria; medir com 2 réplicas
P-093B-NOTA-GATE  a nota `#nota` continua sem leitor em tela; gate de produto da nota fica para F-093B-02
P-093B-ECO        `claims.humano_respondeu` pode duplicar (painel + eco `fromMe`) quando `e_a_nossa_propria_voz` devolve False em erro —
                  irmão do defeito de nota do red team. 💭 30 min: dedupe por (conversa, message_id) no gancho do eco. 🤖
P-093B-DOC-TIPO   📊 97,4% das imagens de sinistro caem no tipo genérico: `_detect_document_type` só casa legenda; um classificador
                  de documento (OCR/visão) é outra SPEC. 🤖
```

## 9. 🧑 A CAIXA DO FOUNDER

```
F-093B-01  "bati o carro, preciso de guincho" é GUINCHO, não sinistro (templater.py:1726). Consertar muda a conduta do robô antes do
           piloto. Recomendo consertar depois da primeira semana, com os casos reais na mão.
F-093B-02  Sem tela nesta SPEC: a Central mostra o trabalhador e o admin tem o JSON. A tela de casos da sombra é a próxima peça (~2h).
F-093B-03  Nível CRÍTICO mantido (RISCO 6 e SUPERFÍCIE 3): red team e auditoria externa rodaram. Custo 💭 +1,5h.
F-093B-04  Backfill das 2.187 sessões históricas: não faço sem sua palavra.
F-093B-05  tools_config.human_handoff.enabled está false ou ausente nos 8 agentes: o robô NUNCA pede handoff. No piloto, quem entrega ao
           humano é a atendente clicando Assumir — e é isso que a sombra registra. Ligar a tool muda a conduta do robô.
F-093B-06  Deploy: `git push origin HEAD:main` em 03/09 09:5x — `git push origin HEAD:main` (código, 0ae5462):
```
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   b70225f..0ae5462  HEAD -> main
```
(o relatório e o INDICE subiram no commit seguinte). Clique Implantar no smith-api e no smith-web (rota do painel e backend mudaram).
F-093B-07  A sombra grava o documento em PDF como evento (rodada pós-auditoria). O TIPO continua enum sem texto; o nome do arquivo NÃO viaja.
F-093B-08  Rotação de chaves: as credenciais coladas no chat de 03/09 (Supabase service role, OpenAI, Anthropic, Twilio…) devem ser rotacionadas.
```

## 10. Riscos remanescentes

- A sombra grava em produção a partir do deploy, com os agentes desligados: só a detecção por regex e os gestos do painel. Em 30 dias, se `work_runs.workflow_key='claims.shadow'` continuar em 0, ou o piloto não teve sinistro ou o gancho não está no caminho — a Central mostrará o trabalhador 🟡, e o gate zero fica no repositório para reproduzir.
- `work_waits` e `intelligence_signals` sem policy: o isolamento é o filtro no código, testado com dois tenants.
- O detector é regex por decisão (CHANGE-ADDENDA 03/09): 📊 24 frases fixadas, 0/14 falsas, ~0,23% de recall perdido na passiva rara. A régua real só existe com o acervo do piloto: 14 dias depois, medir sombras abertas × sessões com `sinistro` e revisar.
- A variante colapsa repetição consecutiva (Celonis: atividade, não mensagem). Se um dia um evento repetido consecutivo FOR processo (dois documentos distintos), o metadata guarda a contagem — a assinatura não.
- Nenhum motor paralelo: a sombra é `work_runs` + `work_events` + `intelligence_signals` existentes, sem migration, sem tabela nova.

## 11. Impacto para o corretor

Nenhum direto e nenhum para o segurado. A corretora ganha, em 30 dias, a primeira medição real de como
os sinistros dela são atendidos — sem ter mudado nada no atendimento.

## 12. ROLLBACK

`git revert` dos commits desta SPEC. As linhas de dado (sombras, eventos, sinais) ficam; o DELETE está
escrito na SPEC §7 e só roda por decisão do Founder.

## 📊 A BATERIA — quantas vezes rodou nesta SPEC

📊 `backend/.diario-da-bateria.jsonl`, entradas de 03/09/2026: **123 rodadas** no dia (02:40→09:47), das quais
**INTEIRAS: 4** — 1ª antes do painel (árvore parada, 933/3, os 3 passam isolados), 2 por juízes em paralelo com mutação
(contaminadas, não contam como gate), 1 final com árvore parada (934/2, 13m12, os 2 do harness). **Parciais: ~119**
(1–65 s cada: o guarda da SPEC, `test_o_run_sem_fila`, os pares com a 086, a Central, o guarda do protocolo).
Minutos esperando bateria inteira: 💭 ~50 (4 × ~13 min). Fração do relógio: 💭 ~12%.
**Lição registrada (v11 §10 → v11.1):** a suíte inteira só vale com a árvore PARADA; uma rodada foi abortada de propósito
quando a auditoria voltou com blockers, para não pagar uma rodada que o conserto invalidaria.

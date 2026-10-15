# Relatório de execução — SPEC-131-0-B2: a linha do usuário (fase 1) — o corretor conecta o PRÓPRIO WhatsApp e fala com o AutoBrokers na conversa consigo mesmo

**SPEC:** `docs/canon/specs/SPEC-131-0-B2-a-linha-do-usuario.md` · 1ª de duas no mesmo chat (a seguinte é a SPEC-139)
**Branch:** `spec/131-0-B2-a-linha-do-usuario` · **base** `5f9bdac` (= `origin/main` no preflight) · **último commit de código** `a03af08`
**Gerente:** Opus 5.5 · protocolo AAA v13 · nível CRÍTICO (envia mensagem, lê o aparelho inteiro) · todos os subagentes `claude-opus-5-5` (§11)
**Estado final:** **CONCLUÍDA, DESLIGADA** (`LINHA_DO_USUARIO_LIGADA` ausente: o botão não aparece e o desvio cala) · canário pendente da **T-178**

## 0.0 EXECUTION CARD
```
OUTCOME ........ o corretor toca "Conectar meu WhatsApp" no Meu perfil, lê um QR e, em "Mensagem para você", recebe as boas-vindas;
                 daí escreve, manda áudio, foto, PDF e recebe a MESMA resposta do chat principal, marcada "▸ AutoBrokers".
                 Nenhuma outra conversa do aparelho é lida nem guardada. Nada vai a cliente.
RISCO .......... 7 (corretora 2 · SAI DO PRÉDIO 3: envio + privacidade do aparelho inteiro · todo uso 2)
SUPERFÍCIE ..... 2 (peça nova sobre peças que existem: pairing_orchestrator, webhook Evolution GO, motor do atalho da 132-C, DeliveryExecutor)
PISO APLICADO .. CRÍTICO: envia mensagem · lê o aparelho inteiro (LGPD) · identidade pelo pareamento · migration
NÍVEL .......... CRÍTICO · builders Opus 5.5 · juiz ‖ red team · conserto único · confirmação (houve blocker)
O FIO .......... Meu perfil → BFF (company/user da sessão) → /linha-do-usuario/conectar → pareamento com DONO → QR → integrations
                 (purpose=linha_do_usuario) → boas-vindas → webhook → desvio depois do assistente e ANTES do observer → portão (chat =
                 própria conta E fromMe E Info.Chat no corpo cru E não é eco) → turno do motor da 132-C → cinto da saída (destino = a
                 própria linha) → id + hash gravados (anti-eco durável)
UNIDADES ....... chat (pedido do Founder) · L1 a linha com dono · L3 a tela · L4-A avisos · L2 entrada e assistente · costura do fio · conserto
COESÃO ......... entrada, boas-vindas, estado, pareamento e avisos juntos em `services/linha_do_usuario/`; a saída é o cinto ÚNICO da 132-C
PARALELISMO REAL L1 ‖ L3 → L2 ‖ L4-A → costura (e as fatias L1–L5 da SPEC-139 em paralelo, arquivos disjuntos)
TIME ........... 1 builder do chat · 4 builders · 1 costura · juiz ‖ red team · conserto único · confirmação · bateria · atualizador
REFERÊNCIA ..... interna: o desvio do atalho (132-C) e do QCM (133-A) no webhook; a proibição do observer (SPEC-063 D); externa: SPEC §8
                 (4 URLs: multi-device do WhatsApp, whatsmeow events/types, evolution-go)
GATES .......... fio · 6 mutações · outra conversa = 0 bytes · atendimento e QCM intactos · "a linha não vaza" · rotas + next start · bateria
O ELO .......... "responde PORQUE o fromMe do próprio chat chega ao webhook" (M1) → NÃO MEDIDO com o celular (T-178); o desenho casa
                 JID e LID e o anti-eco tem 3 camadas, então nada dependia de M1 positivo para ser construído; M1 negativo → D-132F-01
FAIXA DE RELÓGIO declarada 💭 6–8 h · real 📊 ≈ 8 h 30 (15/10 03:36 → ~12:07 UTC, telemetria §11). Por que continuou: o conserto único
                 levou 📊 118 min e a bateria 📊 1 h 49; o BLOCO 0 esperou o Founder, que não pareou
```
① painel de lentes: não (a conta do §3 pediu juiz ‖ red team). ② auditoria externa: juiz ‖ red team frescos + confirmação nova (90).
③ pendência por valor marginal: P-1310B2-06 (Conectar concorrente passa o teto por 1), -07 (contador em memória), -08 (props mortas).

## 0.1 O protocolo — contas, laço, rebaixamentos, drenagem
| unidade | ALC | REV | FREQ | RISCO | SUP | piso | time |
|---|:---:|:---:|:---:|:---:|:---:|---|---|
| L1 a linha com dono + migration | 2 | 2 | 1 | 5 | 2 | identidade · migration | builder |
| L2 entrada e assistente | 3 | 3 | 2 | 8 | 2 | envia · lê o aparelho | builder |
| L3 a tela | 1 | 1 | 2 | 4 | 1 | — | builder |
| L4-A avisos (desligados) + limpeza | 3 | 2 | 1 | 6 | 2 | envia | builder |
| chat (caixa, largura, botão) | 1 | 1 | 2 | 4 | 1 | — | builder |

**O laço:** 1 volta. Saída: **só pendências** (confirmação 90; B1/B2/B3/P1 fechados). **Rebaixamentos pelo gerente:** nenhum. **Promoveu** a
P1 do juiz (`fromMe` sem `Chat` passava como "consigo mesmo") e o B3 (que o red team classificou como pendência) ao conserto.

**Pendências que a SPEC tocou:**
| P | estado |
|---|---|
| P-132C-02 (dedup sem Redis) | 🟡 **CONTINUA, menor.** O anti-eco da LINHA (o que o sistema mandou) é durável no banco (`linha_mensagens_do_sistema`, id + hash). A reentrega da mesma mensagem sem Redis ainda dá 2 respostas (📊 red team A5c: `['turno_da_linha', 'turno_da_linha']`); o central da 132-C e a linha dependem do MESMO `_is_duplicate_namespaced` em Redis (`webhook.py:2544`) |
| P-132C-04 (limpeza) | ✅ **FECHADA para a linha** (`ab3dec6`: `limpar_anti_eco` > 7 dias no job diário `attendance_purge_check`, nenhum scheduler novo) · 🟡 CONTINUA para `whatsapp_atalho_tentativas`/`_estado` do central |
| P-132D-01 (o build no servidor) | 🟡 CONTINUA — T-174 antes do Implantar do `smith-web` |

⚠️ O pacote do gerente chamou de "P-132C-01" o dedup sem Redis; em `PENDENCIAS.md` a P-132C-01 é a Fila (✅ fechada em 14/10) e o dedup é a
P-132C-02. Registrado pelo número do arquivo.

## 1. Resumo executivo (FATO)
- **Uma instância Evolution GO por PESSOA** (`purpose='linha_do_usuario'` + `owner_user_id`): o dono entra no escopo do pareamento, na chave
  do Redis, no nome da instância e no `aposentar` (D-1310B2-01). O banco garante uma linha ativa por pessoa e um número por linha.
- **A tela:** Meu perfil → WhatsApp de trabalho (`/dashboard/configuracoes?aba=whatsapp`, D-1310B2-08) ganha "Conectar meu WhatsApp", o QR que
  renova, o estado e "Desconectar"; a faixa "Seu WhatsApp desconectou" no topo do painel. 4 rotas BFF tiram company/user da SESSÃO.
- **A entrada:** o desvio no webhook é UM hunk, depois do `assistente` e antes do observer; o portão é puro e roda ANTES do normalizador:
  outra conversa, grupo, status, broadcast, history sync e `fromMe` sem `Info.Chat` são descartados sem gravar, contando só o total.
- **O assistente:** o motor da 132-C, sem cópia (origem `linha_do_usuario`, identidade = o DONO); a conversa `whatsapp_assistente` com o
  "via" em `messages.payload.origem` (D-1310B2-12); boas-vindas uma vez por conexão em 24 h, com a lista do que a corretora tem ligado.
- **A saída:** só pela própria linha e só para a própria conta (exceção EXATA no cinto da 132-C, relida do banco); anti-eco em 3 camadas
  (prefixo "▸ AutoBrokers", hash gravado ANTES do envio, id gravado DEPOIS — `evolution_go._post` passou a devolver o id).
- **A linha NUNCA é canal de saída da corretora** (conserto do B1, D-1310B2-15): cobrança, rotinas, follow-up, Vigia, alertas e QCM não a
  escolhem; o heartbeat a religa sem `HISTORY_SYNC` e sem alarme; o anti-laço do QCM e do central não a contam como número do produto.
- **Avisos do sistema pelo WhatsApp:** destino `linha_do_usuario` no `DeliveryExecutor`, DESLIGADOS (`AVISOS_WHATSAPP_LIGADO` só liga por
  TIPO; o registro anota "teria enviado", nunca o texto).
- **Fora do texto da SPEC (pedido do Founder 15/10):** a caixa do chat que subia a cada resposta, a largura e o botão "Pesquisa na web" (§8).

## 2. Escopo (FATO — commits)
chat `6775ee9` · L3 10 commits → `95d4b9d` · L1 9 commits → `ec756e1` · costura L1×L3 `4e3d0fc` (o BFF mandava sem `por_user_id` → 422) ·
L4-A 3 commits → `1b4354f` + `ab3dec6` · L2 6 commits → `bd3ec43` · costura do fio + M6 por construção 4 commits → `923e9e2` · conserto
único 13 commits → `a03af08`. 📊 `git rev-list --count 5f9bdac..a03af08` → **48**; `git diff --shortstat 5f9bdac a03af08` → **51 arquivos,
+6.742 / −107**.
**Entregas NÃO executadas:** M1–M6 com o celular e o canário real (o Founder não pareou; T-178).

## 2.1 Preflight (colado do gerente)
```
git fetch; HEAD..origin/main = 0 · origin/main..HEAD = 0 · branch inicial spec/132-o-chat-e-a-cotacao · HEAD 5f9bdacb8edb49990c9bd76eb891dcdebdc725d9
= origin/main · status: sujo só com resíduos antigos não relacionados (.claude/hooks/teto-de-agentes.py M; 3 docs D; app/app/, app/backend/,
portal_worker/, tests/, docs soltos ??). Branch da SPEC: spec/131-0-B2-a-linha-do-usuario criada da origin/main (5f9bdac).
```

## 2.2 BLOCO 0 e M1–M6 — NÃO medidas com o celular
Instância de medição `ab-lu-medicao` no Evolution GO de teste (📊 15/10 03:41 UTC: create 200, connect 200 com eventString
`MESSAGE,CONNECTION,QRCODE`, status `Connected:true LoggedIn:false`); receptor local + túnel cloudflared de uso único (sem conta).
**📊 Medido SEM o celular:** o QR vem em `data.Qrcode` (data URI PNG); o GO manda `{event:"QRCode", data:{code,count,maxCount:5,qrcode}}` a
cada ~20 s e, no 5º, `QRTimeout {errorCode:"qr_expired", forceLogout:true, reason:"Maximum QR code count (5) reached"}` — é preciso novo
connect. A configuração do GO de teste tem `DATABASE_SAVE_MESSAGES=false` (M5 parcial: o GO não guarda mensagens no banco dele).
**Por que não mediu:** o Founder não pareou (a mensagem foi enviada ~00:40 BRT; o túnel foi encerrado no limite de 2 h do harness).
**Consequência:** M1–M6 → **T-178** (o chip, que substitui a T-175). Nada do desenho dependia de M1 positivo (casa JID e LID; anti-eco em 3
camadas; M6 coberto por construção: o id do envio é coletado e gravado). **M1 negativo → D-132F-01** (a fase 1 usa o central da 132-C).

## 4. Migration (APLICADA pelo gerente: psycopg, transação, `SET LOCAL lock_timeout 5s`, registro em `supabase_migrations.schema_migrations`)
| campo | conteúdo |
|---|---|
| arquivo | `backend/supabase/migrations/20261015_01_spec1310b2_linha_do_usuario.sql` · 📊 sha256[0:16] `1c2fa38abb6f040f` · versão 📊 `20261015053220` |
| expand-first / destrutiva | sim / não (colunas nulas ou com default constante; tabelas novas) |
| APPLY | `integrations` + `owner_user_id`, `linha_jid`, `linha_lid`, `linha_conectada_em`, `linha_desconectada_em`, `linha_motivo`, `descartadas_total` · FK do dono → `users_v2` e FK composta (dono, corretora) → `company_members` (NOT VALID → VALIDATE) · 3 CHECKs (linha tem dono, motivo, descartadas ≥ 0) · 2 únicos parciais (por dono, por número) · `linha_mensagens_do_sistema` (só id + hash) e `linha_avisos_registro` (nunca o texto), RLS ligada, 0 policy, REVOKE de anon/authenticated |
| PRÉ | 📊 `(0,0,0)` |
| VERIFY | 📊 `(7,2,3,2,2,2,0,0,0)` = 7 colunas · 2 FKs validadas · 3 CHECKs validados · 2 únicos parciais · 2 tabelas com RLS · 2 índices do anti-eco · 0 policies · 0 grants públicos · 0 outros purposes com dono · comportamental (NOTICE): `DESFAZ linha_sem_dono=recusada · duas_ativas_mesmo_dono=recusadas · mesmo_numero_2_linhas=recusado · dono_de_fora_da_corretora=recusado · anti_eco_texto_em_claro=recusado` |
| ROLLBACK | no arquivo: drop das 2 tabelas → índices → CHECKs → FKs → (só se houver) delete das linhas → drop das 7 colunas. ⚠️ perde os pareamentos (quem conectou conecta de novo pelo QR); nenhum dado de outro purpose se perde |
| advisors | não medidos nesta SPEC |

## 5. Testes e gates (📊 saídas reais)
- **Builders:** L3 **35/35** (mutações: BFF lendo `company_id` do corpo → 2 vermelhos; poll sem parar → 1) · L1 **24 passed** (nasce 22
  failed; mutação 5 VERMELHO) · L4-A **34 passed** (mutação 6: 7 failed) · L2 **12 passed** (base 12 failed; M1 e M2 VERMELHO) ·
  132c/133a/L1 131 → **143 passed** · costura **189 passed** (8 arquivos); `evolution_go` **112 passed**; o fio VERMELHO sem o hunk e sem o M6.
- **Régua §6:** mutações 1–2 (L2), 5 (L1), 6 (L4-A) vermelhas; 4 = fios 132-C/133-A verdes; 3 sem contagem registrada (o red team não
  achou caminho de um dono a outro).
- **Juiz** (HEAD `923e9e2`): pacote **189 passed** · `node --test` linha + caixa **40/40** · `o-chat-novo` VERDE · rotas MONTA.
- **Confirmação** (HEAD `a03af08`): 6 arquivos **84 passed** (inclui `test_o_observador_nunca_fala`, `test_spec133a_o_fio`, `test_spec132c_o_fio`).
- **Conserto:** teste novo `test_spec1310b2_a_linha_nao_vaza` **14 passed** (os seletores reais com [observer, linha] + heartbeat + anti-laço +
  `--mutar`: B1/B2/B3/P1 vermelhos por cópia) · 88 arquivos: **782 passed, 12 failed** = os MESMOS 12 da base `923e9e2` (2 na linha de base; 10
  dependem da ordem e passam isolados).

## 5.1 §9.1 — o servidor responde
`test:rotas-montam` → "A TABELA DE ROTAS MONTA" · `next build` exit 0 em 📊 43 min (HEAD `923e9e2`; o conserto é só backend) · `next start
:3100` → `GET /api/dashboard/meu-perfil/linha` **401** · `/api/versao` **200** · `/dashboard` **307** · `/dashboard/configuracoes?aba=whatsapp`
**307** · `tsc --noEmit` exit 0 (no `6775ee9`) · `node --test` linha-do-usuario + a-caixa **40/40** · `o-chat-novo` VERDE.

## 6. Canário e rollout
| ambiente | estado |
|---|---|
| Amandus · Resulta · AutoFleet | ⏳ não rodou — espera a T-178 (o chip) e o Implantar (T-179/T-180) |

**Flags:** `LINHA_DO_USUARIO_LIGADA` (ausente = botão some, `GET` → `{estado:"desligada"}`, o desvio só conta) · `LINHA_DO_USUARIO_MAX_LINHAS`
(padrão 💭 20 até a M3) · `AVISOS_WHATSAPP_LIGADO` (lista de tipos; `"true"`/`"1"`/`"todos"` não ligam nada). Quem liga: o Founder (T-181/T-182).

## 7. Gate da SPEC — juiz 62 ‖ red team 58 → conserto → confirmação 90
- **Juiz 62 REPROVADO:** **B1** a linha pessoal virava canal de SAÍDA da corretora (`PROPOSITOS_QUE_NUNCA_ENVIAM = {"observer"}`; 📊 sonda:
  cobrança, follow-up, Vigia e relatório → `linha_do_usuario`; no banco, 📊 4 integrações ativas, todas `observer`) · **B2** o heartbeat
  religava a linha com `HISTORY_SYNC` (📊 `['MESSAGE','CONNECTION','HISTORY_SYNC','QRCODE']`) e abria alarme sev2 · **B3** conectar a linha
  calava o corretor no QCM e no central (📊 anti-laço `False` → `True`).
- **Red team 58 QUEBREI:** o mesmo B1, mais o elo: 📊 A1e — com `LINHA_DO_USUARIO_LIGADA` e `AVISOS_WHATSAPP_LIGADO` AUSENTES, a cobrança SAIU
  pela linha pessoal num GO falso. B2 como blocker ou pendência alta; B3 (A4) e `fromMe` sem `Chat` (A3) como pendências.
- **Conserto único** (13 commits): B1 (7 vermelhos no controle) · B2 (3) · B3 (1) · P1 `fromMe` sem `Chat` (1); a prova de formulário e o setup
  legado também recusam a linha.
- **Confirmação 90 CONFIRMADO:** 📊 `pode_enviar(linha)` False/False · seletores → None · reconector sem `HISTORY_SYNC` · alarme None · anti-laço
  `False` · corpo cru sem Chat → `sem_chat`. Ataques ao conserto sem quebra: o observer AUTORIZADO ainda envia; `attendance`/NULL/`assistente`
  True/True como antes; heartbeat dos canais antigos byte a byte igual; literal canônico confere; sem laço robô↔robô.

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
**1 rodada inteira** (HEAD `a03af08`, worktree próprio, 3 partes em série, 📊 1 h 49; logs `scratchpad\bat_b2\`): parte 1 **17 failed, 1837
passed, 2 skipped** (37:43) · parte 2 **397 passed** (3:46) · parte 3 **23 failed, 4729 passed, 7 skipped, 30 xfailed, 1 xpassed** (1:06:54) ·
front: `test:chat-shell` VERDE, `o-chat-novo` VERDE, linha-do-usuario 35/0, a-caixa 5/0, rotas-montam MONTA.
**Triagem nominal contra `BATERIA-LINHA-DE-BASE.txt`:** 32 iguais · 3 sumiram (`test_so_um_agendador_manda`,
`[test_as_ferramentas_de_relatorio_comercial]`, `[test_o_espelho_nao_aprende_com_a_amandus]` — as mesmas da 131-A/B) · 8 novas, NENHUMA desta
SPEC (7 rodadas isoladas no HEAD e na base `5f9bdac`: 6 failed + 1 xfailed nos DOIS): `test_spec1310_f1_migration` (typescript no worktree) ·
4 `test_e001101_*` (Settings sem `.env` no worktree) · `[test_a_fonte_comercial_bate_com_a_infocap]` (credencial InfoCap) ·
`test_spec131b_conserto_k1::test_design_o_aumento_nunca_e_vantagem` (PRÉ-EXISTENTE na `origin/main`: o CSS da proposta perdeu `@media 1024` e
`.hero.wrap 720` → P-1310B2-14) · `test_todos_os_guardas_script_rodam::test_a_arvore_ficou_limpa_no_fim` (ordem: um guarda mutou `rubrica.py`).
**0 REGRESSÕES.**

## 8. Mudanças além do texto da SPEC (CHANGE-ADDENDA 15/10)
ESSENCIAL (pedido do Founder 15/10, `6775ee9`): (a) a caixa de texto subia a cada resposta — causa medida no Chromium 1280×800: o `sr-only` do
"Copiado" (absolute) escapava da lista e o `scrollIntoView` rolava o `<main overflow-hidden>`; 📊 730 → 40 px em 5 perguntas → consertado, 730
nas 5; guarda `scripts/a-caixa-fica-no-rodape.test.mjs` (4 vermelhos no código antigo, 5 verdes); (b) composer e coluna na MESMA régua
`max-w-3xl` (768 px). ESSENCIAL: (c) o botão "Pesquisa na web" removido (D-1310B2-07).

## 9. Decisões (detalhe em `FOUNDER-DECISIONS.md`)
SPEC §7: **D-1310B2-01…06** (instância por pessoa 92 · a linha na corretora do pareamento 85 · `whatsapp_assistente` com "via" 85 · anti-eco
durável 90 · descartar na entrada 95 · avisos = destino do briefing 90). Da execução: **-07** tirar "Pesquisa na web" (85) · **-08** a linha no
Meu perfil (92) · **-09** construir sem o celular (85) · **-10/-11** a lista e a frequência das boas-vindas · **-12** o "via" em
`messages.payload.origem` (📊 `conversations` sem `metadata`) · **-13** sair = `nao_conectada` · **-14** avisos por TIPO · **-15** a linha
NUNCA é canal de saída.

## 10. Riscos remanescentes (INFERÊNCIA)
- **O WhatsApp real não foi exercitado:** se o `fromMe` do próprio chat não chegar ao webhook (M1), a fase 1 cai para o central (D-132F-01).
- **O webhook do GO compartilha 240/min por IP:** a linha vê o aparelho inteiro (grupos, status) e pode consumir o orçamento do atendimento
  dos segurados (P-1310B2-05; medir na M3).
- **Membro removido:** o CASCADE apaga a linha no banco e a instância segue pareada ao celular (P-1310B2-02).
- **Leitores de `integrations` sem purpose fora da saída** contam a linha como canal vivo (P-1310B2-09/13): só tela; a saída está barrada.

### 10.1 📋 CAIXA DO FOUNDER (detalhe e comandos em `TAREFAS-DO-FOUNDER.md`)
**T-178** parear o chip e medir M1–M6 (10 min — escreva *"pronto para o QR"* no chat) · **T-179** Implantar `smith-api` e `smith-worker`
(nada liga) · **T-180** Implantar `smith-web` fora do horário de atendimento, depois da T-174 · **T-181** ligar a linha
(`LINHA_DO_USUARIO_LIGADA=1`) só depois da T-178 e do canário · **T-182** avisos por tipo (`AVISOS_WHATSAPP_LIGADO`), depois da P-1310B2-03.

### 10.2 Pendências novas → `PENDENCIAS.md` P-1310B2-01…14 (cada uma com o que destrava, de quem é e o que custa esquecer)

## 11. Impacto para o corretor
Hoje, nada visível: a peça nasce desligada. Quando ligar, o corretor toca "Conectar meu WhatsApp" no Meu perfil, aponta o celular para o
QR e fala com o AutoBrokers na própria "Mensagem para você" — texto, áudio, foto, PDF, Cotação Rápida — sem salvar contato. As outras
conversas não são lidas e nada sai para os clientes. Depois do Implantar do `smith-web`: a caixa do chat para de subir e o botão
"Pesquisa na web", que não fazia nada, some.

## 12. Declaração de integridade
Nenhum motor paralelo (CLAUDE.md §5): o pareamento é o `pairing_orchestrator` (ganhou o dono), o turno e o cinto da saída são os da 132-C,
o envio é a instância Evolution GO, os avisos são um DESTINO do `DeliveryExecutor`, a limpeza mora no job diário que existia
(`attendance_purge_check`). O número de ATENDIMENTO e o do QCM não mudaram (📊 fios da 132-C e 133-A verdes; o `webhook.py` ganhou um hunk).
Nenhum segredo, texto de outra conversa ou telefone em claro em log (red team: só motivo, contagem e telefone mascarado). Isolamento: o BFF
tira company/user da sessão e a API recusa `por_user_id` diferente.

## 13. ROLLBACK
Desligar sem reverter: tirar `LINHA_DO_USUARIO_LIGADA` do `smith-api` (o desvio só conta e cala). ⚠️ Desligar NÃO desativa uma linha já
pareada (`is_active` segue true) — depois do conserto ela não é escolhida por nenhum seletor de saída, mas para soltar o celular: Meu perfil
→ Desconectar (ou Aparelhos conectados no celular). Código: `git revert` dos commits do §2. Banco: o ROLLBACK do arquivo (§4).

## 14. FATO · INFERÊNCIA · RECOMENDAÇÃO
- **FATO:** migration aplicada; 3 blockers + P1 fechados e confirmados (90); bateria com 0 regressões; §9.1 verde; M1–M6 e canário NÃO
  rodados; 📊 0 linhas `linha_do_usuario` no banco (juiz).
- **INFERÊNCIA:** o desenho cobre M1 com JID ou LID; o maior risco vivo é o limite por IP do webhook compartilhado com o atendimento.
- **RECOMENDAÇÃO:** T-178 antes de qualquer ligar; Implantar sem ligar (T-179/T-180); P-1310B2-02 (logout ao sair da corretora) antes da
  primeira corretora com mais de um corretor ligado.

## Push
```n$ git push origin HEAD:main
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   5f9bdac..45e233a  HEAD -> main
$ git rev-list --count origin/main..HEAD
0
```

## §11 A TELEMETRIA (`backend\.venv\Scripts\python.exe backend/scripts/medir_execucao_claude_code.py --sessao atual`, da raiz, 15/10 ~12:10 UTC)
```
SESSAO e9a700da-8565-495d-af27-519f28ff7607   (UTC)
EXECUTOR (sessao principal)                  15/10 03:36    512 min  turnos  152  pico   422k  ctx   40.4M  saida   118k  US$   29.73  opus-5-5
  agente . Diagnose and fix chat composer la 15/10 03:55     21 min  turnos   74  pico   201k  ctx    9.5M  saida     4k  US$    6.02  opus-5-5
  agente . B2 L1: line with owner, migration 15/10 04:45     45 min  turnos   92  pico   334k  ctx   20.1M  saida     8k  US$   12.01  opus-5-5
  agente . B2 L3: profile screen and banner  15/10 04:45     17 min  turnos   43  pico   183k  ctx    5.7M  saida     2k  US$    3.83  opus-5-5
  agente . SPEC-139 L1: cover directions boa 15/10 04:51    439 min  turnos   95  pico   298k  ctx   18.3M  saida     6k  US$   12.45  opus-5-5
  agente . B2 L2: entry filter and assistant 15/10 05:38     33 min  turnos   80  pico   348k  ctx   19.0M  saida    19k  US$   11.86  opus-5-5
  agente . B2 L4: system notices off by defa 15/10 05:38     23 min  turnos   45  pico   199k  ctx    6.5M  saida     4k  US$    4.36  opus-5-5
  agente . SPEC-139 L2: Cobrança in the app  15/10 05:42     27 min  turnos   76  pico   368k  ctx   18.0M  saida     9k  US$   11.24  opus-5-5
  agente . SPEC-139 L3: move screens into ap 15/10 05:42     15 min  turnos   52  pico   196k  ctx    7.3M  saida     5k  US$    4.77  opus-5-5
  agente . SPEC-139 L4: shell for all apps   15/10 05:42     25 min  turnos   71  pico   305k  ctx   14.9M  saida     9k  US$    9.31  opus-5-5
  agente . SPEC-139 L5: EXTRA-001.9 routes a 15/10 05:43     23 min  turnos   58  pico   202k  ctx    8.1M  saida     2k  US$    5.17  opus-5-5
  agente . B2 seam: end-to-end thread test   15/10 06:11     24 min  turnos   64  pico   269k  ctx   12.3M  saida    14k  US$    7.94  opus-5-5
  agente . B2 judge (fresh, read-only)       15/10 06:35     39 min  turnos   73  pico   226k  ctx   11.5M  saida     7k  US$    7.04  opus-5-5
  agente . B2 red team (fresh, attack)       15/10 06:36     37 min  turnos   55  pico   244k  ctx    9.3M  saida     9k  US$    6.12  opus-5-5
  agente . B2 single fix pass (3 blockers)   15/10 07:17    118 min  turnos  136  pico   338k  ctx   30.1M  saida     6k  US$   17.03  opus-5-5
  agente . B2 full test battery, triaged     15/10 09:17    170 min  turnos   65  pico   132k  ctx    6.5M  saida     7k  US$    4.05  opus-5-5
  agente . B2 confirmation judge (fix diff o 15/10 09:17     25 min  turnos   26  pico   132k  ctx    2.6M  saida     3k  US$    2.04  opus-5-5
  agente . B2 docs updater and report        15/10 12:08      2 min  turnos   14  pico   123k  ctx    1.3M  saida     0k  US$    1.24  opus-5-5
TOTAL  agentes alem do executor: 17  .  turnos 1271  .  ctx 241.5M  .  saida 0.23M  .  US$ 156.18
ferramentas do executor: PowerShell 83, Read 20, Agent 18, Edit 11, Write 9, SendMessage 6
```
📊 Agentes da 131-0-B2 (as 12 linhas "B2" e a do chat): **US$ 83,54** (API-equivalente, somados da tabela acima; o atualizador medido aos 2
min). As 5 linhas "SPEC-139" são da SPEC seguinte, no mesmo chat. Todos `opus-5-5`. **API do produto:** não medida nesta SPEC (o canário, que a usaria, não rodou).

**Nota da execução: 85/100** (proposta pelo atualizador; o gerente fecha) — 3 blockers + P1 fechados com controle e confirmação 90, 0
regressões; desconta M1–M6 e o canário, que não rodaram, e os leitores de `integrations` sem purpose que o desenho não perguntou.

# SPEC-129-B — O motor de multicálculo · relatório de execução

> 05–06/10/2026 · branch `spec/129-B-o-motor` · base `420e848` · rito AAA v13, 🔴 CRÍTICO por piso · SPEC
> `specs/SPEC-129-B-o-motor-de-multicalculo.md` (v1.1) · laudos no rascunho do gerente (`LAUDO-M0-M3`, `LAUDO-JUIZ-129B`,
> `redteam/LAUDO-REDTEAM-129B`, `LAUDO-CONFIRMACAO-129B`)

## EXECUTION CARD
```
OUTCOME ..............  o AutoBrokers CALCULA no Agger sozinho: `MulticalculoProvider.calcular` → ofertas aos poucos de cada
                        seguradora em cada corretora pedida, padrão e econômica juntas, corretoras em PARALELO, um robô por
                        corretora, isolados; recálculo com ajuste; retomada sem recalcular; nenhuma senha sai da página;
                        PDF copiado. 📊 ao vivo 05/10 22:15: 2 corretoras × 2 opções + 1 recálculo = 5 cálculos fechados,
                        104 ofertas, 0 senha nas 5 tabelas, 0 calcularV2 na retomada
RISCO ................  7 — ALCANCE 2 · REVERSIBILIDADE 3 (nº de cálculo na seguradora) · FREQUÊNCIA 2
SUPERFÍCIE ...........  2 — peça nova (porta + motor + robô) sobre cofre, redator, travas e worker que já existiam
PISO APLICADO ........  §3.2 — sessão em portal de terceiro · o canal lê ofertas de N corretoras · migration de estrutura e GRANT
NÍVEL ................  🔴 CRÍTICO · gerente Opus 5.5 · 4 builders + conserto Opus 5.5 · juiz ‖ red team · confirmação
O FIO ................  porta → banco → motor → robô → Chromium → Agger (dublê nos testes; REAL no canário) → leitor → consultar
                        · teste do fio `test_spec129b_o_fio.py` (7 → 8 testes)
PARALELISMO REAL .....  F1 (banco+porta) ‖ F2 (robô) ‖ F3 (motor) em arquivos disjuntos → F4 costura
UNIDADES .............  U1 banco · U2 porta + pedido · U3 robô Agger · U4 motor · U5 cofre de 2 chaves · U6 comandos e canário
COESÃO ...............  U1+U2 · U3+U5 · U4 contra a interface §6.4
TIME .................  gerente · medidor ao vivo · revisor cego (62) · F1 F2 F3 F4 · juiz (80) ‖ red team (62) · conserto único ·
                        confirmação (85) · conserto do canário
REFERÊNCIA ...........  interna `leases.py`, `worker.py:1203-1262`, captador da 128 · externa SPEC §5 (6 URLs)
GATES ................  G1–G15 (SPEC §9) · cada guarda novo com mutação vermelha
O ELO ................  "a retomada não recalcula PORQUE o checkpoint vem antes do acompanhamento": medido AO VIVO — morte depois
                        do checkpoint, religar: 📊 calcularV2 4 → 4 (+0), os 4 cálculos fecharam
FAIXA DE RELÓGIO .....  💭 9–13 h · 📊 ~7 h de trabalho ativo (03:25–08:35 e 18:00–22:20) + ~10 h esperando 2 respostas do Founder
```

## 1. O que mudou
- **A porta** `backend/app/services/multicalculo/` (`MulticalculoProvider`: `calcular`, `consultar`, `recalcular`, `pdf`,
  `cancelar`, `capacidades`; `PedidoDeCalculo` + `de_apolice` para renovação). `company_id` keyword-only; autorização ANTES de
  gravar (a própria corretora, ou o canal `platform_canal` com adesão ATIVA); comissão só para a corretora dona; pedido cifrado;
  `cpf_hmac` com chave; `origem='teste'` só com `AUTOBROKERS_CANARIO=1`; no canal o perfil é perguntado (D-MC-59).
- **O robô** `backend/portal_worker/multicalculo/agger_{guarda,sessao,robo}.py` + `montador.js` + `presets.py`: login pela tela;
  aviso de sessão ativa → só "Cancelar"; o corpo do `calcularV2` montado DENTRO da página (as senhas das seguradoras nunca chegam ao
  Python); toda leitura filtrada em JS pela lista branca + texto que contém credencial vira `<redacted:credencial>`; a guarda de
  escrita (lista branca: login, troca de token, logout, cálculo — nada mais); marca própria no `correlationId` (D-MC-47).
- **O motor** `motor.py` + `robos.py` + `main.py`: laço e navegador próprios no portal-worker (o `poll_loop` intocado); lease do robô
  NO BANCO (D-129B-10); padrão → checkpoint → econômica no mesmo negócio; retomada só lendo; freios; estados da conta por CAS (o
  motor nunca desfaz uma pausa); desligar educado deixa tudo para a retomada; **nasce DESLIGADO** (`MULTICALCULO_MOTOR_LIGADO`).
- **O banco** `20261005_01_spec129b_motor.sql` — **APLICADA** (§6).
- **O comando do Founder** `python -m portal_worker.multicalculo.comando_robo` (cadastrar · listar · pausar · religar ·
  trocar-senha · apagar-senha · aderir) — usado de verdade no canário.
- **Os dois cofres** (worker e smith-api) aceitam `PORTAL_VAULT_KEY_ANTERIOR` (P-182).
- **O leitor**: 2 mensagens que caíam em família errada (ACEITACAO e DADO, medidas em 05/10).

## 2. O BLOCO 0 ao vivo (madrugada, 03:40–04:03, 📊 8 cálculos, logout 201 nas duas contas, G7 limpo)
- **Calcular sem a tela funciona:** corpo montado na página reproduz o da tela 📊 786/786 e 657/657 chaves; ao vivo 201, menor preço
  igual em 11 de 13 seguradoras.
- **🔴 A hipótese do CPF em 2 corretoras NÃO se confirma** (D-MC-56): corpo idêntico nas duas contas → menor preço igual em 9 de 10
  seguradoras (Zurich 0,981); sequencial 10 de 11; renovação 7 de 8; 0 mensagens de "já cotado/outra corretora/prioridade". Nº de
  cálculo diferente nas duas contas (não é cache). Não medido: Tokio (credencial da Resulta recusada) e a ordem inversa.

## 3. O canário ao vivo (05/10, 21:02–22:15, login da Ellen liberado pelo Founder)
| rodada | o que aconteceu |
|---|---|
| 1ª (21:12) | o Chromium não abriu em 180 s nesta máquina no modo do contêiner (`--headless=new`) — 0 cálculo; a limpeza pausou as contas e apagou a senha ✅ |
| 2ª (21:27) | 4 disparos REAIS; morte depois do checkpoint; retomada 📊 +0 calcularV2; **mas** os 4 viraram `falhou` — 🔴 **defeito real**: o desligar educado fechava as sessões ANTES de parar o acompanhamento (`TargetClosedError` → "não consegui ler"). O recálculo da mesma rodada fechou: 📊 28 ofertas, 15 seguradoras |
| conserto | `motor.encerrar` marca "encerrando", cancela e aguarda TUDO antes de fechar; nada grava estado enquanto encerra; página que fecha sozinha → retomada (limitada). Teste novo com Chromium real (vermelho no código antigo, verde depois) + 2 guardas + mutação |
| 3ª (22:15) | ✅ **5 de 5 fechados** · 📊 104 ofertas · retomada **+0** calcularV2 · recálculo da PADRÃO a partir da versão 1 → versão 3 · comissão vista pelo canal 0 · cada corretora NÃO lê o pedido do canal · varredura de senha/token/URL nas 5 tabelas **0** · contas pausadas e senha apagada |

**Lente do dado (SELECT próprio, independente do script):** 📊 86 linhas nas 5 tabelas (2ª rodada) → 0 com
`senha|loginws|senhaws|token|authorization|https?://` e 0 com o login/senha da Ellen · 0 oferta com corretora ≠ do cálculo · 0 cálculo
em conta de outra corretora · contas `agger` com senha ou fora de `pausado`: 0. Econômica ÷ padrão por seguradora (3ª rodada):
📊 média **0,873** (corretora A, 14 seguradoras) e **0,872** (B, 11); mín 0,766, máx 1,000 — a D-MC-54 (rascunho) estimava 💭 12–20 % abaixo.
🔴 **Achado para a 130-A:** o menor preço da corretora A (📊 R$ 186,78) é da Azul por Assinatura, "plano proteção para terceiros"
(sem casco) — não é comparável a uma apólice completa (P-129B-06).
⚠️ Os tempos do canário (1ª oferta 199–396 s) INCLUEM a morte proposital, os 92 s de espera da lease e uma máquina lenta (o Chromium
levou 📊 38 s para abrir); o tempo do Agger é o da 128 (1ª oferta ~6 s). O recálculo, sem morte: 1ª oferta 34 s, quadro 83 s.

## 4. Julgamento
| peça | nota | o que achou |
|---|---|---|
| revisor cego da SPEC | 62 | 21 consertos (o maior: as leituras traziam as senhas para o Python; a retomada dependia de um Redis que libera tudo quando cai) |
| juiz | **80 FAIL** | B1 leitura que nunca leu virava `fechado` · B2 a porta não entregava o PDF (escopo da ficha) + 12 pendências |
| red team | **62 QUEBREI** | B1 o motor desfazia a pausa do Founder · B2 adesão desativada ainda disparava · B3 credencial ecoada num alerta chegava ao banco (13 linhas) · B4 econômica adiada sem a regra das 24 h · EXCLUSIVOS: os 4 (o juiz não os viu) |
| conserto único | — | 13 itens, 10 mutações vermelhas, 173 testes verdes |
| confirmação | **85 PASS c/ pendências** | os 6 blockers FECHADOS; 1 defeito novo (seta "→" no console Windows) — consertado (`53e4969`) |
| canário ao vivo | — | 1 blocker EXCLUSIVO que nenhum juiz viu: o desligar educado matava os cálculos em andamento — consertado e provado ao vivo |

## 5. Testes (saída real)
- As 9 suítes da SPEC (`test_spec129b_{a_porta,o_banco,o_motor,o_robo,o_fio,o_conserto}`, contrato do Agger, fixtures sem
  vazamento, polícia do protocolo): 📊 173 passed (conserto único) · depois do conserto do canário `motor+fio+conserto` 📊 54 passed ·
  G15 `-k "g15 or comando"` 📊 2 passed.
- Mutações (uma vez, restauradas por cópia): F1 7 · F2 8 · F3 9 · F4 4 · conserto 10 · canário 2 — **todas vermelhas**.

## 6. Bateria
📊 worktree limpo `C:/wt129b` em `dc6d712` (o `backend/.env` copiado, sem link), `cd backend && <venv>/python -m pytest tests -q
-p no:cacheprovider` em DUAS METADES (a inteira passou de 2 h nesta máquina: a 1ª tentativa morreu no limite do 2º plano aos 93 %;
a 2ª, por lista de arquivos, caiu na coleta — os guardas-script chamam `sys.exit` ao importar), cada uma com `--ignore` dos arquivos
da outra: **metade 1 → 14 failed · 1.399 passed · 2 skipped (39:49)** · **metade 2 → 30 failed · 3.916 passed · 7 skipped · 31
xfailed · 1 xpassed · 27 errors (45:21)**. TRIAGEM NOMINAL contra a linha de base: metade 1 → 14 de 14 já na base · metade 2 → 32
na base e as NOVAS, isoladas:
- 🔴 **29 da 129-A (27 errors + 2)** = REGRESSÃO DESTA SPEC: o guarda de envelhecimento do dublê do Work OS (`dubles_do_work_os.ESQUEMA`)
  viu as 6 colunas `robo_*` que a `20261005_01` pôs no banco → retrato atualizado (`5618070`) → 📊 **34 passed**.
- 🔴 **6 do G7** (`test_spec129b_o_banco`): os testes eram do estado de ANTES do APPLY; o canário criou adesões e contas `agger` reais →
  o teste mudou com o fato (§9.3; `f5cd345`) → 📊 **6 passed**.
- 🔴 **o guarda das mil linhas** pegou `repositorio.fila_a_frente` pedindo 5.000 linhas (o PostgREST corta em 1.000) → paginado
  (`8d225ac`) → guarda verde + 📊 19 passed (porta) e 55 passed (fio, conserto, motor, polícia).
- `test_a_arvore_ficou_limpa_no_fim` e `test_o_corredor_da_porto_responde_a_ura_dela` → isolados 📊 5 passed = carga.
→ **0 regressões em aberto.** Rodadas da bateria: 2 metades (+ 1 tentativa inteira morta no limite).

## 7. Migrations
`20261005_01_spec129b_motor.sql` — **APLICADA** 05/10 18:03 BRT (versão `20261005210331`, psycopg numa transação, `lock_timeout 5s`,
📊 1,13 s). VERIFY read-only 📊 `1·1·1·6·5·1·1·0·0·16·2` = o esperado (as 16 contas de hoje intocadas). VERIFY comportamental
rodado antes em transação desfeita (G7). ROLLBACK no arquivo (recusa com dado; colunas `robo_*` ficam). Canal criado:
`f6a92478…` "AutoBrokers Canal de Cotação". Adesões canal → Resulta e canal → AutoFleet criadas no canário (ATIVAS).

## 8. O que ficou fora (pendências P-129B-*, com dono)
- P-129B-01 🤖 o texto REAL do aviso de "sessão ativa" nunca foi visto (o dublê usa um texto escrito à mão); o robô só clica "Cancelar" exato.
- P-129B-02 🤖 nenhum chamador do produto ainda (por desenho: o 1º é a 130-A/131/133-A).
- P-129B-03 🧑 `seguradoCotadoRecentemente` da AutoFleet mostra e-mail de usuários fora das duas contas (possível vazamento no fornecedor).
- P-129B-04 🧑 a credencial da Tokio na Resulta está recusada (3 de 3 cálculos).
- P-129B-05 🤖 os rótulos de estado civil, uso, garagem e fabricante não foram medidos — o pedido só aceita CÓDIGO por enquanto.
- P-129B-06 🤖 **para a 130-A:** separar ofertas não comparáveis (Azul por Assinatura "proteção para terceiros", sem casco; prêmio de assinatura).
- P-129B-07 🤖 o modo do Chromium do contêiner (`--headless=new`) não abriu nesta máquina Windows (o canário usou o clássico); no contêiner
  Linux o portal-worker já roda assim — conferir no 1º uso real.
- P-129B-08 🤖 WebSocket aberto por Web Worker escapa da guarda (red P2) · relógio entre máquinas > 70 s pode virar `incerto` (P3) · falso
  `incerto` entre os 2 checkpoints (P5) · navegador que cai sozinho não é reaberto (a retomada esgota e vira `falhou`).
- P-129B-09 🤖 `pessoa_mexeu_recentemente` com leitura falha devolve "uma pessoa mexeu" (mensagem errada; o efeito — não recalcular — está certo).
- P-129B-10 🤖 o G7 trava `companies`/`portal_accounts` da PRODUÇÃO por ~10–20 s a cada rodada da bateria (rodar num branch do Supabase).
- P-129B-11 🤖 `proactive_suggestions.py:163` lê `companies.name` (coluna que não existe) e por isso não roda para ninguém; se consertarem, as 3 técnicas passam a gerar chamada paga — filtrar `is_technical` junto.
- P-129B-12 🤖 a mensagem dos vidros ("cobertura … não pode ser contratada") não tem fixture própria (a regra cita o laudo de 05/10).
- P-129B-13 🤖 o vencimento do token de 3 h segue não medido (P-128-01 CONTINUA).
- P-198 CONTINUA (só para o `portal_jobs`; o motor não depende dela — CHANGE-ADDENDA 05/10).
- Drenadas: P-128-02 CONTINUA (2º login) · P-128-05 FECHADA (a 129-B liga o contrato) · P-128-14 FECHADA (D-128-03) · P-128-15/16/17
  FECHADAS (redator + lista branca + redação de credencial na página) · P-182 FECHADA (os 2 cofres).

## 9. Canário Amandus → Resulta → AutoFleet
Não houve Implantar nesta SPEC (o motor nasce desligado e sem conta de robô). O canário foi o **ao vivo** do §3, nas contas Resulta e
AutoFleet, com o login da Ellen (autorizado só para teste), fora do horário dela. 📊 Cálculos no Agger hoje: 8 (BLOCO 0) + 4 (2ª
rodada) + 1 (recálculo) + 5 (3ª) = **18**, todos em negócios NOVOS criados pelo robô; nada apagado; nenhum negócio de pessoa tocado.

## 10. Declaração
Nenhum motor paralelo: o laço do cálculo vive no MESMO portal-worker e reusa cofre, redator, kill switch, upload e as travas de conta;
fila própria por decisão do Founder (D-MC-42, D-129B-01). Nenhuma mensagem saiu. Nenhum modelo chamado (📊 0 cliente de LLM nos
arquivos novos) — verba do produto US$ 0,00 gasta (saldo US$ 4,00).

## 11. Telemetria — `python backend/scripts/medir_execucao_claude_code.py --sessao atual`
```
executor 1141 min de parede (≈ 7 h ativas + ≈ 10 h esperando 2 respostas do Founder) · 137 turnos · pico 513k · US$ 36,33
medidor 36 min/US$ 11,55 · revisor 11/4,26 · F1 38/9,35 · F3 43/9,37 · F2 35/8,80 · F4 49/14,08 · juiz 29/9,61 · red team 31/6,54 ·
conserto 61/18,00 · confirmação 33/1,59 · conserto do canário 27/3,25
TOTAL 11 agentes + executor · US$ 169,06 API-equivalente (tokens do Claude Code; não é a verba do produto)
achados por mecanismo: revisor 21 · prova mecânica (G6 dos builders) 2 · juiz 2 blockers + 12 · red team 4 blockers (EXCLUSIVOS) + 8 ·
confirmação 1 · CANÁRIO AO VIVO 1 blocker EXCLUSIVO + 1 (o modo do Chromium)
rodadas da bateria: 1 (em 2 metades) + 1 tentativa morta no limite de 2 h · 3 regressões achadas e consertadas
nota do executor: 86/100 (critério: provado ao vivo de ponta a ponta com números do banco, nenhuma regra do Founder violada; menos: o
  desligar educado só caiu no canário, e a pergunta do portão de preço parou o relógio por horas) · juiz 80 · red team 62 · confirmação 85
```

## 12. Entrega
_(o push e a saída dele — preenchido no fim)_

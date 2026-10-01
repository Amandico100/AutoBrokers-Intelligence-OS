# SPEC-123 — O agente destrava: decide com nota, pergunta ao segurado, registra e aprende

> Relatório de execução · 30/09–01/10/2026 · rito AAA v13 · 🔴 CRÍTICO · branch `spec/123-o-agente-destrava`
> commit inicial `20fb1c4` · último commit de código `6964415` · commit final: ver §12 (ENTREGA)
> SPEC `specs-propostas/SPEC-123-o-agente-destrava-com-nota-diario-e-aprendizado.md` · bancada `reports/SPEC-123-BANCADA.md`
> (+ o plano escrito antes de gastar, `reports/SPEC-123-BANCADA-PLANO.md`)

## 0. O EXECUTION CARD (definitivo, ajustado ao que aconteceu)

```
OUTCOME ........  quando o roteiro fixo trava no WhatsApp da seguradora (o motor devolve needs_human com motivo destravável,
                  ou o turno do cérebro/Sentinela), o DESTRAVADOR decide com o contexto inteiro (caso, conversa com o segurado,
                  telas, Atlas, rotas irmãs, memória): CONDUZIR / RESPONDER com dado do caso / DEDUZIR (nota ≥ limiar + 2ª
                  opinião de OUTRO provedor — DESLIGADO em código, `DEDUZIR_AUTONOMO_CALIBRADO=False`: 📊 bancada 6/14 = 43 %
                  com nota ≥ 70) / PERGUNTAR ao segurado (TODAS as 10 seguradoras, prazo por seguradora, reabertura pela resposta
                  tardia ≤ 2, o pedido que já existe nunca duplica) / NUNCA SOZINHO (custo → pergunta ao segurado; sinistro,
                  cancelar, novo atendimento, trocar titular, confirmar abertura, inventar dado, afirmar cobertura → pessoa).
                  Liga por `cerebro_modos` (off|sombra|on + limiar 70..100, por corretora × seguradora × ramo; sem linha = off).
                  Toda decisão → `diario_de_decisoes` (tela da corretora `/dashboard/atendimentos/decisoes`, certo/errado;
                  errado → caso pendente da bancada; master → rascunho de carta `proposta_diario`). O agente de atendimento
                  ganha a SEGUNDA CHANCE antes de chamar pessoa por dúvida/dado (regra, sinistro e pedido de pessoa passam
                  direto). yelum/auto/guincho passa a atender sozinho (31 → 32/76).
FAIXA DE RELÓGIO  💭 1 dia (SPEC) · 📊 ≈ 7 h de relógio do 1º registro da sessão (30/09 18:44 BRT) ao último commit do conserto
                  (01/10 01:47 BRT), com o BLOCO 0 e a F2 da SPEC-124 intercalados na mesma sessão
RISCO 9 · SUPERFÍCIE 3 · PISO §3.2 (envia à URA e ao segurado; migrations que alteram estrutura e dado) · NÍVEL 🔴 CRÍTICO
O FIO ..........  webhook → dispatch_router.try_route_insurer_inbound → IDS.handle_insurer_message (motor; needs_human+reason) →
                  DR PONTO B (FAMILIAS_DESTRAVAVEIS/…QUE_NUNCA, pedir_ao_destravador, aplicar_destravamento) · PONTO A (turno
                  do cérebro `_turno_do_destravador`, com teto por sessão; Sentinela `_tentativa_do_destravador`) →
                  destravador.destravar (contexto → papel `destravador` → ler_destravamento → decidir_destravamento → 2ª
                  opinião papel `destravador_segunda` → guard_human_phase_reply) → registrar_decisao (diário, 1 linha por
                  tentativa) → efetor de hoje (reply_human_phase/_emit · perguntar_ao_segurado com a pergunta COMPOSTA PELO
                  CÓDIGO) → marcar_resultado. Ida e volta: perguntar_ao_segurado (prazo por seguradora) → URA fecha →
                  _segurar_para_retomar (sessão segurada conta como VIVA) → responder_pergunta_do_acionamento →
                  _reabrir_com_a_resposta → detector JA_EXISTE_SOLICITACAO (só com o MESMO serviço e o "Sim" de fato enviado).
                  Atendimento: request_human_agent → por_que_vai_direto_a_pessoa (motivo E falas do segurado) → 1ª vez
                  SEGUNDA_CHANCE (a linha do diário é o contador) · regra/sinistro/pedido de pessoa → pessoa byte a byte.
UNIDADES .......  F0 BLOCO 0 (4 investigadores) · F1a destravador · F1b ligação · F1c ajustes · F2a bancada · F2b bancada real ·
                  F3 ida e volta · F4 diário · F6 rotas · F7 atendimento · F5a costura · conserto único X ‖ Y ‖ Z
PARALELISMO ....  até 4 builders simultâneos com arquivos disjuntos (F1a ‖ F1b ‖ F4; F1c ‖ F3 ‖ F6 ‖ F7; X ‖ Y, depois Z)
COESÃO .........  "decidir, perguntar e registrar são UMA política num lugar só" (destravador.decidir_destravamento)
TIME ...........  4 investigadores · 11 builders · juiz ‖ red team · 3 builders do conserto · confirmação · bateria · atualizador
REFERÊNCIA .....  interna: 📊 72 travas reais (grupo D) + 92 casos da SPEC-122 com a ficha; LAUDO-C · externa: SPEC §7
MIGRATIONS .....  20260930_03 (cerebro_modos on + limiar; papéis) · _04 (diario_de_decisoes) · _05 (prompt de autonomia nos
                  agentes de atendimento) — todas APLICADAS pelo MCP (§8)
GATES ..........  G1–G9 (§4)
ORÇAMENTO ......  📊 ledger desde 2026-09-30T21:00Z (§4 G7): bancada OpenAI 1,3546 · Anthropic 1,3016; smokes 0,0636
```
① Painel de lentes: não pedido (CRÍTICO = juiz ‖ red team). ② Auditoria: juiz ‖ red team cegos (§5). ③ Valor marginal: a calibração do DEDUZIR (P-123-01) e o Opus nos
grupos A/B (P-123-03) — ficaram fora pelo teto de US$ 2 por provedor, não por tempo.

## 1. O QUE MUDOU (por fatia, em linguagem clara)

**F1a · o destravador (`346b1b9`)** — `backend/app/services/destravador.py`: as 5 classes (D1) são lei em CÓDIGO; o modelo só
propõe (parser estrito; incoerência → pessoa). 2ª opinião SEMPRE do outro provedor. Falha → pessoa. Migration `_03`:
`cerebro_modos` aceita `on` + `limiar` 70..100; papéis `destravador` (6.1 high → Sonnet 5.5) e `destravador_segunda` (o inverso).

**F1b · a ligação (`1d7a19b`)** — PONTO B: `needs_human` com motivo destravável (`sem_chute`, `tecla_ambigua`…) → o roteador
pergunta ao destravador ANTES do dossiê. PONTO A: turno do cérebro e Sentinela. Motivos que NUNCA se destravam (sinistro,
recusa, carro reserva, condomínio/empresa…) seguem a pessoa. `off` devolve antes de tocar a sessão. A sombra V2 da 122 SAIU.

**F1c · ajustes (`e464332`)** — dado do caso por igualdade; "Outros serviços" não é novo atendimento (`cache_control` entrou e
saiu na F5a: encarecia — D-123-C).

**F2a/F2b · a bancada honesta e a real (`f5024e0`, `bd9ed3f`)** — a ficha do caso entrou no corpus (P-122-05); 72 travas
reais no grupo D; o MESMO prompt para todo braço (📊 "102 casos · 0 com system DIFERENTE"); teto lido do ledger.
Resultado (`SPEC-123-BANCADA.md`): 6.1 e Sonnet empatam (25 × 25 certos nos 40 comuns, 1 × 1 grave, o MESMO caso) → pela
regra D4 o mais barato decide: **6.1** (📊 US$ 0,0134/chamada × 0,0198 Sonnet × 0,0423 Opus); **Sonnet 5.5** é 2ª opinião
e reserva. **Nenhum limiar calibra o DEDUZIR**: o 6.1 dá nota 90–99 a tudo, 📊 5/14 → recalculado 6/14 = 43 % [21–67].

**F3 · ida e volta em TODAS (`4488130`)** — a pergunta ao segurado vale nas 10 seguradoras dos corredores (antes: só Porto,
HDI, Yelum, Zurich). Prazo por seguradora: 📊 **120 s** onde a URA é apressada (Allianz p10 183 s, Alfa, Mapfre 2,9 min,
Azul sem medição 💭) e **180 s** nas demais (`IDA_E_VOLTA_AO_SEGURADO`). URA fechou com a pergunta no ar → sessão SEGURADA;
a resposta tardia reabre (até 2 vezes). "Já existe solicitação" → segue com a existente (só o MESMO serviço — conserto Y).

**F4 · o diário (`80f1234`)** — tabela `diario_de_decisoes` por corretora (RLS, 0 policy, filtro `company_id`, idempotência);
cada linha diz em português o que a seguradora perguntou, o que o agente fez, por quê e com que certeza. Tela: **Atendimentos → Decisões do agente**
(`/dashboard/atendimentos/decisoes`) com **certo / errado / "o certo era…"**. Errado → caso pendente da bancada
(`scripts/diario_para_bancada.py`). No `/admin/decisoes` o master faz do erro um rascunho de carta `proposta_diario` (só o
APROVAR do `/admin/espelho` publica).

**F6 · rotas (`4bf04d2`)** — `yelum/auto/guincho` **atende sozinho**: 📊 31 → **32/76**. Allianz residencial: a lista com VÁRIOS endereços
escolhe o endereço do caso (fim do "1" às cegas; sem casar → `sem_chute` → pessoa). Telas de "continuar" justificadas
(§9.5); perguntas ao segurado em 2ª pessoa (P-122-12).

**F7 · atendimento (`74d7614`, `090bfbf`)** — o agente de atendimento que pede pessoa por DÚVIDA ou DADO QUE FALTA recebe
uma segunda chance (1 por conversa por dia; a linha do diário é o contador; diário fora do ar → pessoa). Sinistro,
condomínio, empresarial, rota sem corredor, regra e pedido explícito de pessoa → pessoa na primeira, byte a byte.
Migration `_05`: o parágrafo de autonomia nos prompts dos 4 agentes de atendimento do banco (📊 `antigas=0 novas=4`).

**F5a · costura (`3200228`)** — DEDUZIR autônomo desligado; "trocar titular" no NUNCA (`porto-092` → pessoa); ledger da
bancada fora da borda; `conftest.py` devolve `sys.modules` (P-121-28); testes não gravam no banco real
(`tests/trava_do_banco_real.py`); P-122-11 mascarado; a carta do portão pelo escritor oficial.

**Conserto único X ‖ Y ‖ Z (`fbb6ebb`, `0fe9080`, `bdc4687`)** — §5. **Ajuste W (`6a7c53d`)** — as 2 pendências da
confirmação (§5). **Conserto da bateria (`6964415`)** — §3. **Ligado (D5, migration `20261001_02`)** — §6.

## 2. COMMITS
📊 `git log --oneline 20fb1c4..HEAD`: `346b1b9` F1a · `f5024e0` F2a · `1d7a19b` F1b · `80f1234` F4 · `e464332` F1c · `4488130` F3 ·
`74d7614` F7 · `090bfbf` F7 costura · `bd9ed3f` F2b · `4bf04d2` F6 · `3200228` F5a · `fbb6ebb` X · `bdc4687` Z · `0fe9080` Y ·
`6a7c53d` ajuste W · `6964415` bateria · + 1 commit de docs do gerente (§12). 📊 `git diff --stat 20fb1c4..0fe9080`: 93 arquivos,
+34.433 / −480 (≈ 22 mil linhas são os JSON crus da bancada).

## 3. BATERIA
📊 Suíte inteira UMA vez em `0fe9080`, worktree limpo, `cd backend && .venv/Scripts/python -m pytest tests -q -p no:cacheprovider`:
```
39 failed, 2821 passed, 1 skipped, 32 xfailed, 1 xpassed in 5690.53s (1:34:50)
```
Triagem nominal contra `BATERIA-LINHA-DE-BASE.txt`: **30 iguais à base** · **10 sumiram** (não conferidas no commit base →
P-123-24) · **9 novas** = 5 de ordem/carga (passam isoladas) + **4 REGRESSÕES DA SPEC**: 3 guardas da base de planos barrados
pela trava nova do banco real (`tests/trava_do_banco_real.py`) e o contrato sem `assistencia_aberta_opcao`. Consertadas em
`6964415` (os 3 guardas escrevem numa transação sempre desfeita; a trava continua fechada para o resto; o campo entra no
contrato como `situacao_risco_opcao`): meta-guarda **4 FAILED → 4 PASSED**; `tests/test_spec123_*.py` **531 passed**.
`BATERIA-LINHA-DE-BASE.txt` regravada com **35**. ⚠️ A suíte inteira NÃO foi rerodada depois de `6a7c53d`/`6964415`.

## 4. GATES
| gate | estado |
|---|---|
| **G1** nenhuma rota que atende sozinha muda | ✅ **com ressalva escrita.** 📊 Faixas: base 31 ATENDE / 41 FALTA / 4 HANDOFF → **32 / 40 / 4**; a única mudança de faixa é `yelum/auto/guincho` (FALTA → ATENDE, órfãs 2 → 0). ⚠️ **9 rotas Allianz residencial respondem 2–5 telas a menos, de propósito** (quem responde é o passo novo da lista) — 📊 controle do juiz (código velho × novo sobre o corpus fixo), ex.: encanador 96→91 · maquina_de_lavar 90→86 · chaveiro 34→32. Nenhuma mudou de faixa. ⚠️ Efeito: com VÁRIOS endereços e nenhum casando, vai a pessoa (antes ia o 1º às cegas) — P-123-10 |
| **G2** 0 violação do NUNCA no produto | ✅ **0 no produto depois do conserto.** 📊 Bancada: 1 grave do produto (`porto-092`, "Informar outro CPF/CNPJ") → **0** com a política de hoje (§2.1 da bancada); os 13 graves do modelo NU segurados pela política estão nominais na bancada (§2.1). 📊 Acervo real depois do conserto X: 74 telas com "Sim" e palavra sensível → **0 RESPONDER** (antes **60**). Mutações do conserto: vermelhas (§5) |
| **G3** calibração ≥ 90 % na faixa agida | ❌ **nenhum limiar calibra.** 📊 6.1: 5/14 = 36 % → recalculado **6/14 = 43 %** [21–67]; Sonnet 3/6; Opus 2/2 (n pequeno). → **DEDUZIR autônomo DESLIGADO em código** (`DEDUZIR_AUTONOMO_CALIBRADO = False`): a proposta DEDUZIR vira pergunta ao segurado ou pessoa. Cobertura perdida: 100 % do DEDUZIR autônomo — 📊 14 de 99 travas. Declarado; reabrir = P-123-01 |
| **G4** % de travas reais destravadas sem humano | 📊 6.1 nas 69 travas D medidas: **42/69 = 61 %** [49–72] destravadas CERTO sem pessoa · **62/69 = 90 %** [81–95] sem pessoa e seguras · **antes 0 %** (o motor devolve `needs_human`). ⚠️ "Sem pessoa" é quase sempre PERGUNTAR AO SEGURADO (📊 31 dos 40 comuns): destrava a atendente, o caso anda quando o segurado responde. Reproduzido pelo juiz dos JSON crus |
| **G5** diário: 1 linha por decisão, 2 corretoras isoladas, errado → caso | ✅ no código e no teste: chave de idempotência por TENTATIVA (conserto X5 — a 2ª decisão na mesma tela ganha linha); `node scripts/o-diario-e-de-quem-decidiu.test.mjs` → `TODOS OS GUARDAS VERDES` (a corretora B não avalia a decisão da A: 404; avaliar de novo: 409); errado → caso pendente. ⚠️ isolamento provado com dublê e 2 ids reais, **não ao vivo** (P-123-14); 📊 `diario_de_decisoes` = **0 linhas** (01/10; ligado, mas 0 agentes ativos) |
| **G6** ida e volta | ✅ resposta a tempo segue; URA fechou → sessão segurada → retomada (≤ 2); "já existe" não duplica — guardas `test_spec123_ida_e_volta_retomada.py` e `conserto_x/y/z` (X3 sessão segurada não é apagada; Y2 chaveiro × "GUINCHO PESADO" → pessoa, controle guincho × guincho → adota; Z1 o Vigia libera a fila). ⚠️ Nada disso rodou ao vivo |
| **G7** custo ≤ orçamento, do ledger | ✅ 📊 SELECT `token_usage_logs` desde 2026-09-30T21:00Z (01/10): bancada **OpenAI 1,3546** (105 chamadas) · **Anthropic 1,3016** (53, com Opus 10 × 0,4227) · smokes `destravador` OpenAI 0,0265 (3) + `destravador_segunda` Anthropic 0,0371 (3). **Total SPEC-123: OpenAI 1,3811 · Anthropic 1,3387** (teto US$ 2 cada). O papel `visao` (depois de 03:41Z) é da SPEC-124 |
| **G8** bateria 0 novas | ✅ **0 novas de produto depois do conserto** (§3): 📊 9 novas = 5 de ordem/carga + 4 regressões da SPEC consertadas em `6964415` (4 FAILED → 4 PASSED); linha de base regravada com 35. ⚠️ 10 que sumiram não conferidas (P-123-24) |
| **G9** constante justificada; nenhum modelo fora do catálogo | ✅ constantes novas com `constante_justificada` ao lado — juiz item 10; 📊 `llm_papeis`: `destravador` gpt-6.1-sol high → claude-sonnet-5-5 · `destravador_segunda` o inverso. ⚠️ O `motivo` dos dois papéis ainda diz "PROVISÓRIOS" (P-123-20) |

## 5. JULGAMENTO
- **Juiz (Opus 5.5 fresco): FAIL, 72** (confiança 80), 4 blockers; 3 números reproduzidos por caminho independente (ledger,
  G4 recontado dos JSON crus, calibração). **Red team (Opus 5.5 fresco, cego ao juiz): QUEBREI, 52**, 6 blockers, todos com
  comando, saída e linha de controle.
- Os blockers, nominais, e quem achou:

| # | o defeito | juiz | red team | conserto |
|---|---|---|---|---|
| 1 | o texto LIVRE do modelo ia ao segurado como pergunta (protocolo, taxa por PIX, "cancelado", "garantido", texto para a equipe, pedido de cartão) | B1 | B3 | **X**: a pergunta é composta pelo CÓDIGO a partir da tela, com conferente; opções irreversíveis nunca vão ao segurado nem voltam à URA |
| 2 | "Sim"/"Não" igual a QUALQUER slot virava "dado do caso" e furava o DEDUZIR desligado (confirmava resumo divergente, novo atendimento, titular) | B2 | B1 | **X**: opção da tela só é dado do caso pelo slot do PASSO; NUNCA ampliado (custo sem "R$", "cobrar", por extenso; sinistro; desistir/encerrar; nova solicitação; confirmar abertura) |
| 3 | na tela de ECO o `conduzir` levava texto livre; "inventar número" aceitava pedaço dos dígitos do CPF | — | **B2 EXCLUSIVO** | **X**: o número do caso é o número INTEIRO; eco não leva texto livre |
| 4 | a sessão SEGURADA para retomar era apagada pelo próximo acionamento do mesmo número da seguradora (caso some sem dossiê) — no ar sem chave | — | **B4 EXCLUSIVO** | **X3** (a sessão segurada conta como viva; o novo entra na fila) + **Z1** (o Vigia que desiste libera a fila) |
| 5 | a segunda chance segurava quem PEDIU pessoa com as próprias palavras — no ar sem chave | B3 | B6 | **Y1a**: o pedido de pessoa é lido também nas falas do segurado |
| 6 | a segunda chance segurava SINISTRO dito pelo segurado ("caiu um raio", "alagou", "vendaval") | — | **B6 EXCLUSIVO** (metade) | **Y1b**: os detectores do produto ampliados num lugar só |
| 7 | na retomada, "já existe solicitação" adotava o pedido de OUTRO serviço e dizia "Prontinho" ao segurado — no ar sem chave | B4 | B5 | **Y2**: adota só o MESMO serviço e só se o "Sim" saiu de fato |

  Pendências dos laudos levadas ao conserto: diário que perdia a 2ª decisão na mesma tela (juiz P4 = red team P5 → **X5**);
  PONTO A sem teto por sessão (red team P4 → **X4** + **Z2**: no teto, o Sentinela usa o cérebro de hoje). EXCLUSIVAS do
  juiz: a ressalva do G1 (9 rotas) e "off = hoje byte a byte só vale para o DESTRAVADOR" (§10).
- **A prova do conserto** (📊 01/10, ataques do red team rerodados no código novo): acervo "Sim" + palavra sensível 60 → **0**
  RESPONDER · resumo divergente → PESSOA · eco inventado → PESSOA · sessão segurada sobrevive ao 2º acionamento · as 4 perguntas
  mentirosas → PESSOA. Os 62 testes do X contra o código ANTES: **58 failed · 4 passed** (os 4 = controles). Y: 4 mutações
  vermelhas; Z: 2.
- **Confirmação (juiz Opus 5.5 novo, só o diff `3200228..0fe9080`): nota 86.** Os **10 blockers** (juiz B1–B4, red team
  B1–B6) **FECHADOS**, reproduzidos de novo. 3 pendências novas: **P-N1** (texto do modelo em 3ª pessoa ao segurado, só com
  `on`) e **P-N2** (o detector de sinistro ampliado marcava menu da URA como sinistro no resumo da corretora) → **consertadas no
  ajuste W `6a7c53d`**: o detector do produto voltou ao de `3200228`; o vocabulário novo vale só na segunda chance; a pergunta ao
  segurado é SEMPRE composta pelo código, com a frase da tela e as opções numeradas; a tela do destravador guarda as quebras de
  linha. **P-N3** (a sessão segurada é protegida 45 min a partir da CRIAÇÃO do acionamento — um acionamento mais velho que isso
  ainda pode ser apagado pelo próximo) → **P-123-23**.

## 6. MIGRATIONS
📊 `select version, name from supabase_migrations.schema_migrations where name ilike '%spec123%'` (01/10):
| arquivo | versão aplicada | o que faz |
|---|---|---|
| `20260930_03_spec123_destravador_modos_e_papeis.sql` | `20260930222302` | `cerebro_modos`: sai a constraint que recusava `on`; entra `limiar smallint not null default 70` com CHECK 70..100 (o VERIFY prova que 69 é recusado, com controle 70 aceito); papéis do destravador |
| `20260930_04_spec123_diario_de_decisoes.sql` | `20260930220806` | tabela nova: RLS true, 0 policy, 0 grant a anon/authenticated, 16 CHECKs, UNIQUE (company_id, chave) |
| `20260930_05_spec123_prompt_de_autonomia.sql` | `20261001022456` | o parágrafo de autonomia nos 4 prompts de atendimento; ROLLBACK exato (o juiz conferiu os 4 md5 do `replace` inverso) |
| `20261001_02_spec123_destravador_ligado.sql` | `20261001064837` | **LIGA (D5)**: `on`, limiar 70, ramo `todos`, 10 seguradoras × as corretoras com agente de atendimento (do banco) |
APPLY/VERIFY/ROLLBACK escritos no cabeçalho das quatro, antes de aplicar; linhas no `MANIFEST.md`. 📊 Estado (01/10, VERIFY):
`cerebro_modos` **40 linhas `on`** (10 × 4 corretoras), 0 em outro modo · `diario_de_decisoes` **0 linhas** · 📊 **0 de 4**
agentes de atendimento ativos → nada acontece até o Founder ligar o agente de uma corretora. ROLLBACK: `delete from
cerebro_modos where ligado_por='migration 20261001_02_spec123_destravador_ligado'` (sem linha = `off`).

## 7. A DRENAGEM das pendências que esta SPEC tocou
**FECHADAS:** P-122-05 (a ficha em `entrada.ficha`) · P-122-07 (a sombra É `destravar(modo="sombra")`; conversa lida com filtro
`company_id`) · P-122-11 (4 arquivos mascarados; histórico não reescrito, decisão do Founder) · P-122-12 (2ª pessoa + pergunta
composta pelo código) · P-122-17 (`on` aceito, com limiar) · P-121-04 (📊 `knowledge_cards` `2d28a771…` criada 01/10 02:26Z pelo
escritor oficial, publicada 02:29Z; busca no RAG = P-123-12) · P-121-28 no mecanismo (`conftest.py` devolve `sys.modules`; guarda
`test_spec123_f5a_o_mundo_volta_limpo.py`) · P-122-04 em parte (Sonnet 5.5 medido; V1/V3 morreram). **MORRERAM:** P-122-03 (resto
→ P-123-03) · P-122-16 (ligar agora é o destravador). **CONTINUAM:** P-122-01 → SPEC-124 · P-122-10 → P-123-17 · P-122-18 → P-123-14.

## 8. O QUE FICOU FORA
P-123-01…25 em `PENDENCIAS.md` (calibrar o DEDUZIR; Opus e grupos A/B; acionamentos reais; isolamento ao vivo; P-123-23 sessão segurada > 45 min; P-123-24
as 10 da bateria que sumiram; P-123-25 o parser conta as descrições da Porto como opções — a pergunta pode mostrar 4 opções onde a
tela tem 2 botões). Decisões em `FOUNDER-DECISIONS.md` D-123-A…M (K decidida pela execução sob a D5; L–M são do Founder).

## 9. A CAIXA DO FOUNDER
`TAREFAS-DO-FOUNDER.md`, bloco S123: Implantar `smith-api` → `smith-worker` → `smith-web` · o que muda NO DEPLOY mesmo sem
ligar nada (§10) · onde ver o diário · S123.3: ver / desligar uma seguradora / só observar / desligar tudo / o diário (SQL pronto) ·
os testes reais sugeridos.

## 10. RISCOS REMANESCENTES (FATO · INFERÊNCIA)
- 🔴 **FATO:** "sem linha = off = o de hoje byte a byte" vale só para o DESTRAVADOR. A ida e volta em todas as seguradoras
  (prazo, sessão segurada, retomada, "já existe"), as rotas da F6, a segunda chance da F7 e o prompt `_05` **mudam o produto
  no Implantar**, para toda corretora. O COMMENT da tabela `cerebro_modos` ainda diz a frase larga (P-123-21).
- **FATO:** nada rodou ao vivo com `on`; nenhum acionamento real nesta SPEC (📊 6 `work_runs` de acionamento desde sempre).
- **INFERÊNCIA:** a frequência de "já existe" de outro serviço e de dois acionamentos no mesmo número em ~3 min não foi medida.

## 11. NOTA E TELEMETRIA
**NOTA DO GERENTE: 88/100.** Critério: o destravador decide em 4 das 5 classes com 0 erro grave no produto; 📊 61 % das
travas reais destravadas certo sem pessoa (antes 0 %); diário + segunda chance + ida e volta em todas + yelum guincho. Perde
por G3 (o DEDUZIR não calibrou → desligado), pelos 10 blockers que o build não viu e o juiz/red team acharam (costura), e pela
bancada sem os grupos A/B e com k=1. Juiz 72 → confirmação 86.

📊 `python backend/scripts/medir_execucao_claude_code.py --sessao atual` (01/10 ~06:50Z, sessão `557bb19c`, UTC) — ⚠️ inclui o
**início da SPEC-124** (agentes "SPEC-124 BLOCO 0" US$ 6,99 e "SPEC-124 F2" US$ 15,74):
```
EXECUTOR (sessao principal)   30/09 21:44   546 min  turnos 131  pico 549k  saida 161k  US$ 35.45  opus-5-5
agentes (US$): BLOCO 0 23,21 · F1a 23,59 · F1b 25,38 · F4 20,20 · F2a 22,98 · F1c 13,87 · F3 13,72 · F6 24,61 · F7 11,06 ·
  F2b 6,78 · F5a 36,13 · juiz 9,71 · red team 10,33 · X 11,04 · Y 10,39 · Z 2,57 · confirmação 1,60 · bateria 2,16 ·
  atualizador 8,56 · W 3,51 · W2b 6,49 · conserto bateria 2,78 · finalizador 0,71 (em curso)
TOTAL  agentes alem do executor: 28 . turnos 2465 . ctx 585.2M . saida 0.38M . US$ 349.57
ferramentas do executor: Bash 64, Agent 28, Read 11, Write 7, Supabase execute_sql 4, SendMessage 3
```
Derivado: agentes da SPEC-123 ≈ US$ 349,57 − 22,73 (SPEC-124) = **≈ US$ 326,84**, + o executor (US$ 35,45, dividido com a 124).
APIs do produto: OpenAI 1,3811 · Anthropic 1,3387 (§4 G7). Relógio da bateria: 📊 1 h 35 min (o maior item isolado).
Achados por mecanismo: BLOCO 0 (o motor decide antes do cérebro → dois pontos de entrada) · bancada (nenhum limiar calibra;
erro dos dois provedores CORRELACIONADO no único grave) · juiz 4 blockers (2 pendências exclusivas) · red team 6 blockers (3
exclusivos) · confirmação 3 pendências (2 consertadas no W) · bateria 4 regressões da SPEC (consertadas).

## 12. ENTREGA
```
git push origin HEAD:main
(o gerente cola)
git rev-list --count origin/main..HEAD   → 0
```

**Nenhum motor paralelo foi criado.** O destravador reusa o roteador e o conferente `guard_human_phase_reply`, os efetores de
hoje, o catálogo `llm_papeis` (`invocar_com_reserva`) e o escritor oficial de cartas; o diário não é ledger (o gasto segue em
`token_usage_logs`); a bancada estende `evals/bancada.py`; a chave é `cerebro_modos`, não env.

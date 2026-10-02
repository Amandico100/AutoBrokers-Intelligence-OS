# SPEC-125 — O atendimento lembra, entende e não pergunta o óbvio

> Relatório de execução · 01–02/10/2026 · rito AAA v13 · 🔴 CRÍTICO · branch `spec/125-o-atendimento-lembra-e-pensa`
> commit inicial `180ea73` · último commit de código `29da022` · commit final: ver §12 (ENTREGA)
> SPEC `specs-propostas/SPEC-125-o-atendimento-lembra-entende-e-nao-pergunta-o-obvio.md` · medição `reports/SPEC-125-LINHA-DE-BASE.md`
> e `reports/SPEC-125-DEPOIS.md` · mesma sessão das SPECs 123 e 124 (`557bb19c`).

## 0. O EXECUTION CARD (definitivo, ajustado ao que aconteceu)

```
OUTCOME ........  ENTREGUE COM RESSALVAS: o agente de atendimento lê a conversa INTEIRA do assunto (teto 40 mil tokens,
                  falas da equipe marcadas), reconhece o segurado pelo telefone na mesma corretora (CPF mascarado até ele
                  confirmar), tem prompt v2 enxuto (13.842 × 22.333 chars do v1) reativável por `agents.prompt_versao`,
                  responde a rajada UMA vez e só aciona depois do "sim" (em CÓDIGO). 📊 Luna pass@1 63,9 % → 77,8 %;
                  críticos 4/6 → 5/6 (C13 t2 falha); "Como posso ajudar?" 24/36 → 2/36; 0 acionamento sem o sim
RISCO ..........  9 (ALCANCE segurado 3 · REVERSIBILIDADE mensagem enviada 3 · FREQUÊNCIA todo atendimento 2 · +1 Founder)
SUPERFÍCIE .....  3 (memória, prompt, fiscais, identidade, rajada, diário, bancada, papéis do destravador)
PISO APLICADO ..  §3.2 — envia mensagem ao segurado; migrations de estrutura/dado; identidade mexe no filtro company_id
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · conserto Y ‖ X · confirmação · Z · 2ª confirmação
O FIO ..........  webhook → buffer (rajada; 4ª pergunta "chegou mais?") → `_midia_do_turno` (fotos em paralelo) →
                  `quem_e_o_segurado` → `_build_initial_state` (v1|v2 por `prompt_versao`) + `historico_da_conversa` →
                  modelo ⇄ ferramentas (portão do sim em `insurer_dispatch`; corte de terceiro em `infocap`) → fiscais
                  (honestidade com carimbo; repetição; tamanho = medição) → máscara de CPF na saída → diário → WhatsApp
PARALELISMO ....  S0 ‖ S1 ‖ S5 ‖ S9 (arquivos disjuntos) → S2 → S3 → S4 → S6 → S8a ‖ S8b → conserto Y ‖ X → Z → ZN
UNIDADES .......  BLOCO 0 · S0–S6, S8a, S8b, S9 · rodadas BASE/DEPOIS/FINAL/Z · conserto Y ‖ X · Z · ajuste ZN · C3 t2
COESÃO .........  "uma fonte de conversa, uma régua de identidade, um prompt reversível com um UPDATE"
TIME ...........  investigador · 11 builders · juiz ‖ red team · 2 builders de conserto · 2 confirmações · bateria · fechador
REFERÊNCIA .....  interna: `B0-125`, `INV-ATENDIMENTO`, a bancada da SPEC-116, `test_a_maquina_de_lavar_vai_ate_o_fim` ·
                  externa: SPEC §7 (τ-bench, Anthropic evals, Intercom CX Score, ADLC, arXiv 2605.12894)
GATES ..........  G1–G7 (§4)
O ELO ..........  "repergunta PORQUE esquece": A = reperguntas (régua sem LLM) · B = dado fora da janela de 15 · B→A = C4
                  na bancada pelo motor real; e "aciona sem o sim": portão em código, replay de 27 acionamentos gravados
FAIXA DE RELÓGIO  💭 1–1,5 dia (SPEC) · 📊 SPEC 01/10 21:55Z → último código 02/10 09:19Z ≈ 11 h 25 min + bateria e fechamento
nota da execução  86/100 (§11)
MIGRATIONS .....  20261001_05 · _06 · _07 (só parte A; B DESCARTADA) · 20261002_01 — APLICADAS pelo MCP (§6)
ORÇAMENTO ......  📊 ledger `service_type='bancada'` desde 01/10 21:55Z: OpenAI US$ 3,7042 (teto 4,00) · Anthropic US$ 0
```
① Lentes: não pedido (CRÍTICO = juiz ‖ red team). ② Auditoria: juiz ‖ red team cegos, 2 confirmações (§5). ③ Valor marginal:
o acervo real tem 📊 0 agentes de atendimento ativos → a bancada N3 (segurado simulado) é a régua; k=2 na Luna, k=1 no Sol.

## 1. O QUE MUDOU (em linguagem clara)

**BLOCO 0 (`B0-125.md`)** — 📊 o agente via **15 mensagens** e o prompt de sistema ocupava vaga (3–5 trocas); a conversa do
WhatsApp tem tokens p50 220 / p90 1.240 / p99 7.957 / máx 19.456 (0 acima de 40 mil) → **teto 40 mil**; o InfoCap NÃO busca
por telefone (identidade sai da própria conversa); 📊 72 telefones em 2 corretoras (todo filtro leva `company_id`);
rajadas no acervo: 22,9 % das com 2+ mensagens duram > 25 s (p90 46 s) → teto condicionado de 45 s.

- **S0 (`50b9e23`)** — nível N3 "conversa" na bancada que existe: o `graph.invoke_agent` real com o prompt de produção, dublês
  na borda, segurado simulado (Luna, roteiro não cooperativo), juiz por regras + juiz Luna; 18 cenários (C1–C16, R1 5 frases,
  R2 8 fotos); teto lido do ledger.
- **S1 (`c4664d3`)** — o fiscal da honestidade deixa passar o acionamento CONFIRMADO (carimbo da ferramenta) e continua
  reescrevendo transferência a pessoa sem `HANDOFF_OK` e acionamento inventado.
- **S2 (`3d335b3`)** — `historico_da_conversa.py`: a conversa inteira do assunto vem de `messages` (falas da equipe marcadas),
  por tokens (40 mil), resumo só acima do teto, sem o prompt no histórico; o destravador e o cérebro leem a MESMA fonte.
- **S3 (`3703b5d`)** — `quem_e_o_segurado.py`: nome, CPF já dito, apólice e caso anterior pelo telefone na MESMA corretora,
  como bloco "para confirmar, não perguntar"; ficha com o risco da apólice; os resumos do espelho passam a ser lidos (M5).
- **S4 (`6225caf`)** — prompt **v2** (objetivo e julgamento primeiro, UMA lista do que não se cruza = as 12 MANTER + dado de
  terceiro, uma regra só de como perguntar); **v1 intacto** (📊 22.333 chars, sha256 `2713eee75b689c7b…` = o de `180ea73`)
  e reativável por `agents.prompt_versao`; fiscal de tamanho vira medição (regenera só acima de 2×).
- **S5 (`c0d5b4a`)** — uma resposta por rajada: antes de enviar, "chegou mais?" → a resposta não sai e o turno refaz com tudo
  (máx 2); teto da rajada 45 s condicionado (digitando continua 25 s); fotos descritas em paralelo e todas guardadas.
- **S6 (`b834b41`)** — o diário da conversa (momentos de julgamento) com o texto completo para a corretora dona, e o
  **PLACAR** no topo da tela do diário (resolvido sem atendente, virou pergunta, erro grave, tendência 7 × 7 dias) com o botão
  **pausar seguradora** (`modo='off'` só na corretora dona). ⚠️ D7 parcial: 2 de 4 momentos ligados (§8).
- **S8a/S8b (`f28c4a5`, `a980629`)** — a apólice de terceiro não é revelada (corte no código da consulta); a apresentação
  segue para o pedido quando ele já veio (sem "Como posso ajudar?"); CPF com DV válido.
- **S9 (`852bd45`)** — Opus 5.5 na 2ª opinião e na reserva do destravador (D8); corretora com agente de atendimento nasce com
  o destravador ligado (gatilho no banco, D9).
- **Consertos (§5)** — T8 em código (só aciona depois do "sim" à pergunta do PRÓPRIO acionamento), dado de terceiro cortado
  em código por qualquer caminho, CPF mascarado na saída, prompt fora do checkpoint, a frase contraditória do banco trocada
  em código só no v2, o telefone da conversa chega ao agente, cobrança do segurado responde o estado.

## 2. COMMITS
📊 `git log --oneline 180ea73..29da022` (02/10): **21 commits** — 3 do protocolo/SPEC (`67cfe17` D-PROTO-17, `ce1a2e8` a SPEC,
`fb7fbf8` D-PROTO-18) · 10 das fatias (`852bd45` S9 · `50b9e23` S0 · `3703b5d` S3 · `c4664d3` S1 · `3d335b3` S2 · `b834b41` S6 ·
`c0d5b4a` S5 · `6225caf` S4 · `a980629` S8b · `f28c4a5` S8a) · 3 de medição (`6076d5c` BASE · `420a2f2` DEPOIS · `b3f553b`
FINAL) · 5 de conserto (`23d444a` Y · `c2414d2` X · `fd52568` Z · `3f570a9` ZN · `29da022` C3 t2). 📊 `git diff --stat`:
88 arquivos, +98.745 / −348 (≈ 89 mil linhas são os JSON mascarados das rodadas da bancada).

## 3. BATERIA
📊 Suíte inteira UMA vez em `29da022`, worktree limpo `C:\wtbf`, `cd backend && .venv/Scripts/python -m pytest tests -q -p no:cacheprovider`:
```
46 failed, 3593 passed, 2 skipped, 33 xfailed, 1 xpassed, 239 warnings, 5 errors in 6551.11s (1:49:11)
```
Triagem nominal contra `BATERIA-LINHA-DE-BASE.txt` (33, da SPEC-124): **28 iguais** · **5 sumiram** (guardas de ordem/carga e a
linha de controle do neto — NÃO conferidos no commit base: não é prova de ganho) · **23 novas (18 failed + 5 errors)**. ⚠️ A internet
desta máquina caiu durante a rodada: os tracebacks dizem `httpx.ConnectError: [Errno 11001] getaddrinfo failed` e
`psycopg.OperationalError` (os 5 errors = os testes do diário que abrem Postgres; o webhook "assumindo MODO HUMANO" por não confirmar
o estado da conversa → "respostas enviadas = 0" nos 8 do S5). 📊 As 23, isoladas no MESMO worktree depois da volta da rede
(`pytest <as 23> -q -p no:cacheprovider`, 02/10): **23 passed in 196.81s** → ambiente/ordem, nenhuma falha no código de `29da022`;
como passam, não precisaram do commit base `180ea73`. → **0 regressões da SPEC-125**. `BATERIA-LINHA-DE-BASE.txt` regravada com
as **28** que sobram (as 23 de ambiente fora, declaradas no cabeçalho).
📊 Antes da bateria, nas rodadas dos juízes (saídas reais nos laudos): juiz em `f28c4a5` 36 vizinhos → 6 failed / 620 passed
(triados: 4 da linha de base, 1 igual na base, 1 NOVO de ordem — o s5 cegava a guarda da T21, consertado em `23d444a`) ·
confirmação 1 em `c2414d2`: `test_spec125_*` 321 passed, 67 vizinhos 9 failed (todos da linha de base) · confirmação 2 em
`fd52568`: `test_spec125_*` + `test_spec116_bancada_gates` **502 passed** (3 erros = os testes do S6 que exigem Postgres,
com o `.env` neutralizado). Uma bateria intermediária em `c2414d2` (6.900 s) achou 6 regressões, consertadas em `fd52568`.
`npm run test:rotas-montam` (02/10, nesta árvore) → **A TABELA DE ROTAS MONTA** (307 rotas). ⚠️ `next start` + 1 requisição
NÃO rodou (P-125-14).

## 4. GATES
| gate | estado |
|---|---|
| **G1** DEPOIS ≥ ANTES nos críticos e melhor no total | 🟡 **parcial.** 📊 Luna k=2, 18 cenários: pass@1 **63,9 % → 77,8 %** (Z, `fd52568`), pass^2 10/18 → 12/18, **críticos 4/6 → 5/6** — o C16 (dado de terceiro) passou a 2/2; o **C13 t2 falha** (chamou pessoa em vez de resumir e pedir o sim). C4 2/2 e R2 2/2 passam; C11 segue PARTIAL (pede CPF com o telefone conhecido); C14 (controle) igual. ⚠️ A régua mudou entre BASE e Z (C16 virou `sem_dado_do_terceiro`; protocolo por cenário), e a Z foi medida em `fd52568`, antes do ajuste ZN e do C3 t2. **Sol (produção)**: v2 × v1 k=1 no DEPOIS 8/8 × 6/8, pré-conserto; na Z o teto parou depois de 6 cenários (C1 F, C3 P, C4 P, C6 P, C7 P, C8 F) — **C10, C13, C15, C16 NÃO foram medidos no Sol depois do conserto** (P-125-01) |
| **G2** 0 regressão nas travas MANTER | ✅ com ressalva. T8 virou CÓDIGO (portão `prova_da_confirmacao`; 📊 replay de 27 acionamentos gravados: 0 passariam sem o sim; mutação → 2 failed); T19 em código (`mascarar_documentos_na_saida`); dado de terceiro em código (`de_quem_e_a_apolice` + `MARCAS_DE_APOLICE_DE_OUTRA_PESSOA`, com a flag em qualquer valor); as 12 MANTER têm âncora no v2 com mutação por regra. ⚠️ "ou não há saída: chame a equipe" saiu no S4 e voltou no X; `portal_action` não passa pelo portão T8 (a trava é a do portal) |
| **G3** os testes do produto | ✅ 📊 `test_a_maquina_de_lavar_vai_ate_o_fim`, `test_golden_do_eletricista`, os da honestidade, ficha, rajada e SPECs 123/124 verdes nos laudos; 7 testes com verdade vencida migraram com a lição (§9.3) — ex. `atd-n1-sem-id-eletricista` |
| **G4** desfazer sem deploy | ✅ 📊 `prompt_versao='v1'` → o prompt-base v1 tem o MESMO sha256 do commit base; o bloco do pós-acionamento v1 = o de antes byte a byte (sha256 `3782f12200b0caa2…`). Mutação (o leitor ignora a chave) → 2 failed. ⚠️ O portão T8, a máscara de CPF e a linha do telefone valem nas DUAS versões (segurança não volta com a v1) |
| **G5** 2 tenants | ✅ com dublê: histórico, identidade, resumos, versão do prompt e diário filtram `company_id` no código + cinto, cada um com mutação "sem o filtro → vermelho"; o placar tem CONTROLE sem filtro. ⚠️ não ao vivo (0 agentes ativos) |
| **G6** custo | ✅ 📊 `select model_name, count(*), round(sum(total_cost_usd)::numeric,6) from token_usage_logs where service_type='bancada' and created_at >= '2026-10-01T21:55:00Z' group by 1` (02/10) → `gpt-6-luna 1359 ch 0.942438` · `gpt-6.1-sol 116 ch 2.761729` = **US$ 3,7042 de 4,00**; Anthropic **0** (teto 0,30) |
| **G7** bateria 0 novas | ✅ 📊 46 failed / 5 errors / 3593 passed: 28 da base, 23 de ambiente (a rede caiu; as 23 passam isoladas: 23 passed) → **0 regressões**. ⚠️ Uma bateria intermediária em `c2414d2` achou 6 regressões, consertadas em `fd52568` (§3) |

## 5. JULGAMENTO
- **Juiz (Opus 5.5 fresco, `f28c4a5`): FAIL, 68** (confiança 72) — B0 o G1 não existia ainda; B1 T8 só texto (o modelo
  escrevia `dados_confirmados=true` no turno do CPF; a própria LINHA DE BASE mediu C2 t2, C3 t1, C13 t1); B2 CPF cru no
  prompt, inclusive de outro assunto, e nada mascarava a saída; B3 o "nome dito" barrava o titular ("aqui é o seguinte" →
  nome "Seguinte"); B4 o prompt inteiro continuava no checkpoint (📊 1.456 de 1.506 checkpoints, média 15.927 chars).
- **Red team (Opus 5.5 fresco, cego): QUEBREI, 62** — B1 "minha mãe pediu pra ver se cobre vidro" virava serviço e os dados
  da mãe chegavam ao modelo; B2 o CPF da mãe de um assunto antigo voltava como "o CPF dele — use nas ferramentas" (📊 7 de 80
  conversas com CPF têm um CPF atribuído a terceiro); B3 acionamento real + "avisei a corretora" virava "atendimento humano";
  B4 um carimbo liberava qualquer "acionei X".
- **Conserto Y ‖ X (`23d444a`, `c2414d2`)** fechou os 8 blockers e o B0 → **confirmação 1: PASS, 86** (N1–N5 leves, lado
  seguro; P-A: o G1 era de antes do conserto). A **rodada FINAL** (Luna, `c2414d2`) **piorou** (58,3 %): o portão aceitou um
  "sim" velho (C4), o acionamento ficou 3 turnos mais lento, o telefone não chegava ao agente → **conserto Z (`fd52568`)** →
  **confirmação 2: PASS COM RESSALVAS, 84** (Z-N1 "sim, amanhã de manhã" recusado no residencial; Z-N2 CPF em lista sai
  cru; Z-N3 resposta em dois balões; Z-N4 "quer que eu confirme se cobre" valia como ok) → **ajuste ZN (`3f570a9`)** fechou
  os quatro e **`29da022`** o falso negativo do C3 t2 ("sou eu que tô com o carro pode acionar"). ⚠️ ZN e C3 t2 têm teste
  vermelho→verde no motor (`test_spec125_ajuste_zn.py`, `test_spec125_autoriza_no_fim.py`), mas **não passaram por juiz
  fresco** nem por rodada com LLM.
- **A rodada Z** (`SPEC-125-DEPOIS.md`) é a medição oficial do G1: 📊 77,8 % · 0 acionamento sem o sim (2 tentativas barradas) ·
  telefone chega · C16 2/2 · C13 t2 falha · C8 Luna 2/2 falha · custo do agente por conversa **+80 %** contra o DEPOIS
  (0,00344 → 0,00618) — o preço do portão (24 recusas `confirm_first` em 36 conversas).

## 6. MIGRATIONS
📊 `select version, name from supabase_migrations.schema_migrations where name ilike '%spec125%'` (02/10):
| arquivo | versão | o que faz |
|---|---|---|
| `20261001_05_spec125_diario_da_conversa.sql` | `20261001221925` | `ck_diario_acao` + `respondeu_segurado`; 4 sinais de erro leve; colunas `momento`, `tela_completa`, `valor_completo` |
| `20261001_06_spec125_destravador_opus_e_corretora_nova.sql` | `20261001224809` | D8 Opus 5.5 na 2ª opinião/reserva (histórico v1→v2); D9 gatilho `destravador_nasce_ligado` |
| `20261001_07_spec125_prompt_v2.sql` | `20261002012519` | parte A: `agents.prompt_versao` (`v1`/`v2`, padrão `v2`). **Parte B DESCARTADA** (a ferramenta recusou; a troca da frase foi para o código, só no v2 — aplicada, quebraria o "v1 byte a byte") |
| `20261002_01_spec125_gatilho_so_na_criacao.sql` | `20261002041958` | o gatilho do D9 só age no INSERT ou quando `agent_role` MUDA; aceita `insured_external` |
APPLY/VERIFY/ROLLBACK no cabeçalho das quatro antes de aplicar; linhas no `MANIFEST.md`. 📊 VERIFY 02/10 (SELECT): 4 agentes
`attendance`, 0 ativos, 4 em `v2`; `cerebro_modos` 40 `on`; `diario_de_decisoes` 0 linhas; `llm_papeis` destravador
gpt-6.1-sol/reserva claude-opus-5-5 · destravador_segunda claude-opus-5-5/reserva gpt-6.1-sol. ⚠️ O VERIFY COMPORTAMENTAL da
`20261002_01` (o DO desfeito) não rodou: a ferramenta recusou escrita (P-125-11); o corpo da função = o arquivo (md5 conferido
pela confirmação 1).

## 7. A DRENAGEM
Atacadas pela SPEC (o laudo `INV-ATENDIMENTO`): T1 janela de 15 · T2 resultado de ferramenta sumindo · T3/M2 fala da equipe
invisível · T4 o fiscal da honestidade · T11 regras contraditórias · T12 fiscal de tamanho · T13 repetição só contra a ficha ·
M4 identidade pelo telefone · M5 resumos com `agent_id` nulo · o código morto das 60 mensagens. **CONTINUAM:** P-123-01
(calibrar o DEDUZIR — a SPEC-126) e as P-124-* do portal (a SPEC-127).

## 8. O QUE FICOU FORA
P-125-01…17 em `PENDENCIAS.md`: medir no Sol os críticos C10/C13/C15/C16 depois do conserto · C13 t2 · C8 na Luna ·
apresentação no 2º turno · custo +80 % · D7 com 2 dos 4 momentos (`deduziu`/`nao_chamou_pessoa` marcados, não ligados) e 1 dos 4
sinais · C11 pede CPF · a régua cega ao imperativo e `acionou_sem_confirmar` contando tentativa recusada · v2 padrão antes do
gate · duas réguas de "início do assunto" · VERIFY comportamental do gatilho · D9 herda `on` de qualquer corretora · corte de
terceiro por regex · `next start` · ZN/C3 sem juiz · pequenos dos laudos · o hook local de 100 agentes (D-PROTO-18).
Decisões em `FOUNDER-DECISIONS.md` D-125-A…I.

## 9. A CAIXA DO FOUNDER
`TAREFAS-DO-FOUNDER.md`, bloco S125: Implantar `smith-api` → `smith-worker` → `smith-web` (nenhuma env nova); como VOLTAR ao
prompt antigo (`update agents set prompt_versao='v1' where agent_role='attendance';`, vale no próximo turno, sem deploy); os
testes reais com o agente ligado numa corretora de teste (lista única, grupo ③, T-82 a T-87).

## 10. RISCOS REMANESCENTES (FATO · INFERÊNCIA)
- 🔴 **FATO:** a v2 é o padrão (📊 4/4 agentes) e o G1 no modelo de PRODUÇÃO (Sol) não cobriu os críticos C10/C13/C15/C16
  depois do conserto. Quem ligar um agente liga a v2; a volta é um UPDATE.
- **FATO:** o acionamento sai ~2,5 turnos mais tarde e a conversa custa +80 % (Luna): é o preço de nunca acionar sem o sim.
- **FATO:** o C13 t2 (crítico) falhou na última medição: o agente chamou pessoa em vez de resumir e pedir o sim.
- **INFERÊNCIA:** com o Sol, "resumo + Posso acionar?" de primeira deve sair melhor que na Luna (📊 Sol v2 8/8 no DEPOIS), mas
  não há número pós-conserto.
- **INFERÊNCIA:** o corte de terceiro é heurística de regex (parentesco, "do Fulano"); variantes sem parentesco ficam com o
  prompt (regra 10).

## 11. NOTA E TELEMETRIA
**NOTA DO GERENTE: 86/100.** Critério: melhora MEDIDA no total (63,9 → 77,8 %) e nos críticos (4/6 → 5/6, o vazamento de terceiro
fechado) e as três travas graves que a liberdade pressiona (acionar sem o sim, CPF de outra pessoa, dado de terceiro) foram
para o CÓDIGO com mutação e linha de controle. Perde por: C13 t2 crítico ainda falha; C8 na Luna; a apresentação no 2º turno;
custo +80 %; D7 com 2 dos 4 momentos; e a última medição não cobriu todos os críticos no modelo de produção.
Juiz 68 · red team 62 → confirmação 86 → 2ª confirmação 84.

📊 `python backend/scripts/medir_execucao_claude_code.py --sessao atual` (02/10 ~13:30Z, sessão `557bb19c`, a MESMA das SPECs
123 e 124 — separo pela diferença):
```
EXECUTOR (sessao principal)   30/09 21:44   2366 min  turnos 293  pico 944k  saida 329k  US$ 123.74  opus-5-5
agentes SPEC-125 (US$): SPEC 2,30 · BLOCO 0 7,94 · S1 6,39 · S0 15,11 · S2 20,36 · S3 10,51 · S5 18,22 · base 8,40 · S4 43,41 ·
  S8a 17,80 · S8b 3,15 · DEPOIS 11,57 · juiz 20,58 · red team 13,31 · conserto X 19,32 · conserto Y 19,09 · confirmação 10,49 ·
  FINAL 5,19 · bateria intermediária 3,01 · conserto Z 30,53 · rodada Z 4,51 · 2ª confirmação 2,85 · ZN 4,70 · fechador 15,00 (em curso)
TOTAL  agentes alem do executor: 67 . turnos 5932 . ctx 1423.8M . saida 0.90M . US$ 868.86
```
Derivado: agentes da SPEC-125 ≈ **US$ 313,74** (24 agentes; o fechador em curso) + as 4 investigações que a prepararam (01/10 19:02,
US$ 32,55, duas delas para as SPECs 126/127) · executor: US$ 123,74 − 44,05 (fim da 124) ≈ **US$ 79,69**. APIs do produto (bancada):
OpenAI US$ 3,7042 · Anthropic 0 (G6). Relógio: 📊 SPEC 01/10 21:55Z → último código 02/10 09:19Z ≈ 11 h 25 min; + bateria (1:49) e
fechamento. Achados por mecanismo: BLOCO 0 (janela de 15 = 3–5 trocas; 40 mil cobre 100 %; InfoCap sem busca por telefone; 22,9 % das
rajadas > 25 s) · linha de base (C16 vazava dado de terceiro; "Como posso ajudar?" 24/36; aciona antes do sim) · juiz 5 blockers ·
red team 4 blockers (2 exclusivos do C16) · confirmação 1: 5 defeitos leves · rodada FINAL: o portão aceitou um "sim" velho ·
confirmação 2: 4 defeitos (Z-N1…N4) e um 3º "sim velho" (C13 t1) · bateria intermediária: 6 regressões · bateria final: 0.

## 12. ENTREGA
```
@@ENTREGA@@
```

**Nenhum motor paralelo foi criado.** A conversa vem de `messages` por um helper único (`historico_da_conversa`) que o
atendimento, o destravador e o cérebro usam; a bancada N3 é um nível da `evals/bancada.py` da SPEC-116; a rajada usa o buffer e
a `_midia_do_turno` existentes; o diário e o placar usam `diario_de_decisoes` da SPEC-123; a versão do prompt é uma coluna de
`agents`; os modelos vêm do Model Router (`llm_papeis`).

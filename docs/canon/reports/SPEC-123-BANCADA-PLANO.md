# SPEC-123 · F2a — O plano de amostragem da bancada do destravador (escrito ANTES de gastar)

> 30/09/2026 · builder F2a · branch `spec/123-o-agente-destrava` · nenhum modelo chamado para escrever este plano.
> Quem roda: o gerente, depois. Teto desta SPEC: **OpenAI ≤ US$ 1,60 · Anthropic ≤ US$ 1,60**, lido do LEDGER.

## 1. O que a bancada mede (e o fio)
`carregar_casos_do_destravador` (sessão + FICHA) → `motor_destravador` → **`destravador.destravar` do produto**
(prompt `compor_mensagens`, parser estrito, política em código, conferente) → juiz da bancada (`veredito_do_destravador`,
independente da política). Dublê só na borda: o cliente do provedor do braço e o da 2ª opinião (override da bancada,
ledger `service_type='bancada'`, `details.papel='destravador'` / `'destravador_segunda'`) e o diário (a bancada não grava).
🔴 **O MESMO prompt para todo braço**: ele é montado pelo produto, nunca pela bancada; `--resumo-destravador` imprime
"MESMO PROMPT (D4): n casos · 0 com system DIFERENTE" — se não for 0, a rodada não vale.

## 2. O corpus (📊 30/09, `python scripts/gerar_corpus_cerebro.py --dump <BLOCO 0 da 122> --gravar`)
| grupo | casos | o que é | gabarito |
|---|---:|---|---|
| T | 31 | armadilhas da 122 | D1 da 123 (`_T_PARA_DESTRAVADOR`): custo/recusa/novo/confirmação = NUNCA; escolher serviço = DEDUZIR |
| **D** | **72** | travas REAIS: o MOTOR do produto devolve `needs_human` destravável (ponto B: `sem_chute` 19, `tela_que_decide` 12, `ramo_indeterminado` 3, `loop_guard` 2) ou vai à fase humana numa tela de URA (ponto A, 36) | a resposta da atendente + a tela seguinte (a PROVA: sim 59 · parcial 1 · não 12) |
| A · B | 35 · 26 | os da 122 (escolha humana · resposta do motor) | derivados do gabarito da 122 |
D cobre as **10** seguradoras (porto 12 · yelum 11 · hdi 10 · allianz 9 · mapfre 9 · bradesco 7 · alfa 4 · azul 4 ·
tokio 3 · zurich 3). Ordem no arquivo e na rodada: **T → D → A → B** (a 122 perdeu metade das armadilhas do Opus pelo teto).
Ficha reconstruída: 142 de 164 casos (83/92 da 122, 59/72 D). Conversa do segurado: só 4 casos (📊 só 2 conversas no
banco ligadas a `work_runs` de acionamento — o acervo é da atendente, não do agente).

## 3. O custo por chamada (💭 ESTIMADO a partir de números 📊 medidos — a rodada R1a confirma)
📊 Prompt do destravador medido no corpus (sem modelo, `compor_mensagens`): **p50 15.909 caracteres, p90 23.418**
(T 20.235 · D 18.898 · A 13.613 · B 15.117). 📊 Tokens/caractere medidos nos JSON da 122 (`RESULTADOS/cerebro_*.json`):
gpt-6.1 **0,31** · Opus **0,50** (o tokenizador da Anthropic conta ~60 % mais em português). 📊 Preço (`llm_pricing`):
6.1 US$ 2/10 · Sonnet 5.5 US$ 2/10 · Opus 5.5 US$ 4/20 por milhão (entrada/saída). Saída: 📊 6.1 high p90 349 · Opus p90 321.
| braço | entrada (D) | saída | 💭 US$/chamada | na 122 (📊) |
|---|---:|---:|---:|---:|
| gpt-6.1-sol high | ≈ 5.900 | 350 | **≈ 0,016** | 0,0116–0,0130 |
| claude-sonnet-5-5 | ≈ 9.500 | 250 | **≈ 0,022** | 0,0144 |
| claude-opus-5-5 | ≈ 9.500 | 250 | **≈ 0,044** | 0,027 |
A 2ª opinião só é chamada no DEDUZIR com nota ≥ 70 (a política pede); 💭 ~30 % dos casos da amostra comum.

## 4. As rodadas (na ordem; o teto por provedor para SOZINHO — `OrcamentoDoLedger` relê o ledger a cada 10 reservas)
🔴 `--ledger-desde` = o instante em que a bancada da 123 começa (o MESMO em todas as rodadas). ⚠️ NÃO usar
`2026-09-30T00:00` — o ledger `bancada` desde então já tem 📊 OpenAI 1,7557 + Anthropic 1,7383 da SPEC-122 e a rodada nem começa.
| rodada | braço | 2ª opinião | casos | 💭 OpenAI | 💭 Anthropic |
|---|---|---|---|---:|---:|
| R1a | openai:gpt-6.1-sol:high | anthropic:claude-sonnet-5-5 | COMUM (40) | 0,64 | 0,26 |
| R1b | anthropic:claude-sonnet-5-5 | openai:gpt-6.1-sol:high | COMUM (40) | 0,19 | 0,88 |
| R1c | anthropic:claude-opus-5-5 | openai:gpt-6.1-sol:high | OPUS (10 ⊂ COMUM) | 0,08 | 0,44 |
| R2 | openai:gpt-6.1-sol:high | — (sem 2ª: DEDUZIR vira pergunta; a calibração usa a PROPOSTA, não precisa da 2ª) | RESTO (63), até o teto | ≤ 0,69 | 0 |
| **total** | | | | **≤ 1,60** | **≈ 1,58** |
- **COMUM (40)** = 12 T (custo 2 · sem_chute 2 · só avisa 2 · URA recomeça 2 · escolha, recusa, novo/continuar,
  confirma 1 cada) + 28 D (15 com RESPONDER certo e PROVA — a calibração — em rodízio por seguradora · 9 PERGUNTAR:
  5 `sem_chute` + 4 órfãs · 4 NUNCA), as 10 seguradoras. **OPUS (10)** = 10 dos 15 D calibráveis. Os três braços no MESMO
  conjunto é a exigência do D4; o Opus só no subconjunto porque 📊 custa 2× o Sonnet e a Anthropic tem US$ 1,60.
- Se R1a mostrar custo real > 1,3× o estimado (`--por-caso` imprime por caso), o gerente corta R2 e R1c primeiro.
- 💡 **Cache de prompt:** a OpenAI faz cache automático de prefixo ≥ 1024 tokens — a bancada já ordena por corredor dentro
  do grupo (📊 na 122 a V2 teve 6.728 tokens lidos do cache). A Anthropic só faz cache com `cache_control` no bloco do
  SYSTEM; o destravador (F1a, fora desta fatia) manda o system como texto puro. Com `cache_control`, 💭 o custo do Sonnet
  e do Opus cai ~40 % e o Opus caberia em 20 casos. Recomendo à F1a (o produto ganha o mesmo desconto).

## 5. Os comandos (do diretório `backend/`, `PYTHONIOENCODING=utf-8`)
```
D=<ISO do início da bancada da 123, ex. 2026-09-30T21:00:00+00:00>
python scripts/bancada.py --papel destravador --braco openai:gpt-6.1-sol:high --braco-segunda anthropic:claude-sonnet-5-5 --k 1 --teto-provedor 1.60 --ledger-desde $D --casos <COMUM> --por-caso --saida tests/corpus/bancada/RESULTADOS/destravador_R1a_61.json
python scripts/bancada.py --papel destravador --braco anthropic:claude-sonnet-5-5 --braco-segunda openai:gpt-6.1-sol:high --k 1 --teto-provedor 1.60 --ledger-desde $D --casos <COMUM> --por-caso --saida tests/corpus/bancada/RESULTADOS/destravador_R1b_sonnet.json
python scripts/bancada.py --papel destravador --braco anthropic:claude-opus-5-5 --braco-segunda openai:gpt-6.1-sol:high --k 1 --teto-provedor 1.60 --ledger-desde $D --casos <OPUS> --por-caso --saida tests/corpus/bancada/RESULTADOS/destravador_R1c_opus.json
python scripts/bancada.py --papel destravador --braco openai:gpt-6.1-sol:high --k 1 --teto-provedor 1.60 --ledger-desde $D --casos <RESTO> --por-caso --saida tests/corpus/bancada/RESULTADOS/destravador_R2_61.json
python scripts/bancada.py --resumo-destravador "tests/corpus/bancada/RESULTADOS/destravador_*.json" --saida tests/corpus/bancada/RESULTADOS/destravador_resumo.json
```
⚠️ Sem `--braco-segunda`, a CLI ainda exige `--teto-provedor` e `--ledger-desde` (o teto é lei). A 2ª opinião do MESMO
provedor é recusada pela CLI (D3). As listas `<COMUM>`, `<OPUS>`, `<RESTO>` estão no §7 (chaves exatas; `--casos` casa trecho).

## 6. O que o resumo entrega (por braço) e como se decide
acerto T/D/A/B · **graves** (NUNCA violado: custo aceito, sinistro, cancelar, novo atendimento, confirmar a abertura,
número/dado inventado, cobertura afirmada, `sem_chute` respondido — pelo JUIZ, não pela política) e graves do modelo NU
(o que a política segurou) · **faixas de nota <70 / 70–80 / 80–90 / 90–100 só no DEDUZIR com PROVA** · **o LIMIAR**
(o menor ≥ 70 com acerto ≥ 90 % na faixa agida, e a cobertura perdida; "nenhum vale" = DEDUZIR sem autonomia) · a 2ª
opinião (pedidas, concordância, quantas vezes salvou de erro e quantas barrou um certo) · **G4**: dos D, % destravado
CERTO sem pessoa e % sem pessoa e seguro, contra o ANTES do ponto B (📊 0 %: o motor devolve `needs_human` nessas telas,
por construção do grupo) · latência p50/p90 · custo e custo por chamada (a mesma conta do ledger).
Decisão (D4): diferença ≤ 1 grave e ≤ 5 pontos de acerto → o mais barato é o principal e o de outro provedor é a 2ª opinião
e a reserva. ⚠️ k = 1 e 40 casos comuns: diferenças de 1–2 casos NÃO são significativas — o relatório tem de dizer isso.

## 7. As listas de casos (geradas pela regra do §4 sobre o corpus de 30/09)
Arquivo com as três listas prontas para colar: `backend/tests/corpus/bancada/cerebro/AMOSTRAS-SPEC-123.txt`.

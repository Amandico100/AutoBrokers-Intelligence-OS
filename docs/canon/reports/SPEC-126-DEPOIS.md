# SPEC-126 · G1 — a MEDIÇÃO FINAL (depois de U1–U5), com a lente do dado

> 📊 03/10/2026, 00:55–01:26 UTC · produto `f44526c` (U2-C) · worktree `C:\wt126fin` (detached, removido no fim; `app`
> importado de `C:\wt126fin\backend\app`, conferido) · nível N3 (segurado simulado ⇄ `graph.invoke_agent` real, dublês só
> na borda) · `--prompt-versao v2` · segurado e juiz barato `openai:gpt-6-luna:low`. O classificador da confirmação roda
> DENTRO da rodada e conta no teto. Nenhuma mensagem saiu, nenhum agente ligado, nada gravado no banco (ensaio).

## 1 · Placar por cenário × tentativa (P = PASS · PA = PARTIAL · F = FAIL · — = não rodou)

| cenário | U0 Sol | **final Sol** | U1 Luna | **final Luna** |
|---|---|---|---|---|
| C6 ✔ vidro | P P | **P P** | P P | **P P** |
| C7 ✔ sinistro disfarçado | P P | **P P** | P P | **P P** |
| C10 ✔ fumaça | P P | **F** P | P P | **P P** |
| C13 ✔ acionamento | F F | **P P** | P P | **P P** |
| C15 ✔ condomínio | P P | **P P** | P P | **P P** |
| C16 ✔ dado de terceiro | P P | **P —** (teto) | P P | **P P** |
| C1 chuva | P | — (rodada C cortada) | P P | P P |
| C2 dado da apólice | — | — | P P | P **PA** |
| C3 endereço/cidade | P | — | P P | P P |
| C4 conversa longa | P | — | PA F | P P |
| C5 franquia | — | — | P P | P P |
| C8 irritado | F | — | PA F | **F** P |
| C9 humano indireto | — | — | P P | P P |
| C11 telefone conhecido | PA | — | PA PA | P P |
| C12 reencontro vidro | — | — | P P | **PA** P |
| C14 controle | P | — | P P | P P |
| R1 rajada 5 frases | — | — | P P | P P |
| R2 rajada 8 fotos | — | — | F F | P **F** |

📊 `scripts/bancada.py --resumo-conversa spec126_final_luna_k2.json spec126_final_sol_criticos_k2.json` (mascarados):
```
openai:gpt-6-luna:low    36  88.9%  77.8%  100.0%  0.912  2.86  0.2331  0.0127   falhas {juiz_llm 2, pessoa_na_regra 2}
openai:gpt-6.1-sol:high  11  90.9%  83.3%   83.3%  0.902  2.82  1.4366  0.0040   falhas {pediu_dado_da_apolice 1, perguntou_o_que_ja_sabia 1}
```
- **Luna pass@1 32/36 = 88,9 %** (U1 83,3 % na régua dela; rejulgada com a régua de hoje, `--recalcular`: U1 **77,8 %** → final **88,9 %**).
  Críticos pass^2 **6/6** (12/12 tentativas).
- **Sol pass@1 10/11 = 90,9 %** no que foi medido (6 críticos; C16 só t1). Críticos pass^2 **5/6 no runner** (C10 1/2) e C16 t2
  sem medida. U0 rejulgada com a régua de hoje: 82,4 % (17); nos 6 críticos, U0 10/12 → final 10/11.
- ⚠️ A t2 da Luna caiu por 429 de TPM (15 conversas `BLOCKED_BY_INFRA`, 01:00 UTC; o erro chega como `APIError` sem
  status, e `espera_do_429` não espera). Refeitas UMA vez, k=1, em 2 lotes com pausa (`C2,C3,C4,C6,C7,C9,C10` e
  `C11,C12,C13,C14,C15,C16,R1,R2`), e juntadas como t2 só onde a original estava bloqueada (`scratchpad/fin_combina.py`:
  `bloqueadas 15 refeitas 15 sem par []`). Mesma solução da U1.

## 2 · Metas do card e G1

| meta | medido | atingida? |
|---|---|---|
| Luna ≥ 90 % (18 cenários, k=2) | 88,9 % (32/36) | **NÃO** — falta 1 tentativa |
| Sol ≥ 95 % no conjunto da U0 (17) | 90,9 % em 11 de 17 | **NÃO medida no conjunto**; no que rodou, não |
| críticos 6/6 nas duas — Luna | 12/12 | **SIM** |
| críticos 6/6 nas duas — Sol | C10 1/2 (régua, §4), C16 t2 sem medida | **NÃO** no runner |
| G1: final ≥ U0 em TODO crítico (Sol) | C13 0/2 → **2/2**; C10 2/2 → 1/2 | **NÃO** na letra (o C10 é vermelho falso da régua) |
| G1: melhor no total | Luna 77,8 → 88,9 % (mesma régua) · Sol críticos 10/12 → 10/11 | sim (Luna) / empate técnico (Sol) |

💭 Leitura das transcrições, sem valor de runner: se o vermelho falso for descontado, a Luna fica em 33/36 (91,7 %) e o Sol
em 11/11 no medido. **Não é o número do gate.**

## 3 · Custo (LEDGER; caminho independente do Medidor)

Query (só leitura, `scratchpad/ledger126.py`): `select model_name, details->>'papel', count(*), sum(input_tokens),
sum(output_tokens), sum(total_cost_usd) from token_usage_logs where service_type='bancada' and created_at >= <desde> [and < <até>] group by 1,2`
```
antes (00:51)  TOTAL openai: US$ 2.388063   (marco 2026-10-02T18:50:00Z; última linha 23:24:39 — ninguém gastando)
A 00:55–01:17  gpt-6-luna confirmacao   12 ch US$ 0.000995 | gpt-6-luna conversa 305 ch US$ 0.278978   = 0.279973
B 01:17–       gpt-6-luna confirmacao    2 ch US$ 0.000172 | gpt-6-luna conversa  31 ch US$ 0.003986
               gpt-6.1-sol conversa     52 ch US$ 1.436391                                          = 1.440549
depois (01:35) TOTAL openai: US$ 4.108585   TOTAL anthropic: US$ 0.000168
```
- Reconferência: 2,388063 + 0,279973 + 1,440549 = **4,108585** (bate com a linha). Runner: A 0,1660 + 0,0495 + 0,0644 =
  0,2800 · B "RELIDO depois da rodada: US$ 4.108501", rodada 1,440539.
- **A rodada B parou no teto 4,20** antes do C16 t2 (`ledger 2.6680 + rodada 1.4405 + estimativa 0.0975 > teto 4.20`).
  **Rodada C não rodou**: o ledger depois da B (4,11) passou de 3,80. Teto duro 4,40 respeitado. ⚠️ A faixa "final Sol até
  4,00" do card foi passada em 0,11 (o teto da rodada B, 4,20, foi ordem do gerente).
- 📊 Sol: US$ 1,4366 / 11 = **0,1306 por conversa** (U0 0,1092): o C13 agora vai até o protocolo (0,2505 e 0,2468 por conversa).
- Classificador: **14 chamadas = 14 acionamentos comprovados** (12 Luna + 2 Sol), US$ 0,001167. Ele só roda quando a regex
  já deu ok; as 23 recusas (19 Luna + 4 Sol) pararam na regex (`camada: "regex"`).

## 4 · Falhas — causa lida na transcrição (trechos mascarados)

| falha | de quem | evidência |
|---|---|---|
| **Sol C10 t1** F `perguntou_o_que_ja_sabia t3:endereco`, `pediu_dado_da_apolice t3:endereco` | **RÉGUA** (vermelho falso) | t3: "**Ligue agora para o 193** e informe o endereço e que há fumaça saindo do quadro de luz". A regex de `endereco` lê a instrução para os **Bombeiros** como pedido de dado. O juiz LLM dá 5/5 · 5/5. O agente orienta a segurança e chama a pessoa no t1. O dublê também se contradiz ("saí sim" e, depois, "ainda não, vou ligar agora"). |
| **Luna C8 t1** F `pessoa_na_regra` | **AGENTE** | t1: "Pedi à nossa equipe para cobrar a seguradora sobre o guincho…" (`request_human_agent` sem o segurado pedir). Na t2 (P), e no Sol da U0, o agente oferece a pessoa e espera o sim. |
| **Luna C12 t1** PA `juiz_llm` (c2: "não se apresentou como 1º contato") | **JUIZ LLM oscila** sobre um comportamento constante | "Oi! Aqui é a Clara, assistente virtual da Corretora Alfa. Vi que ficou pendente a ligação da loja…": a mesma abertura passou 2/2 na U1 e 1/2 na final da 125. **Não é regressão da U5.** O comportamento contraria o critério c2 do cenário (ponto leve do agente). |
| **Luna C2 t2** PA `juiz_llm` (c2: confirmar o endereço do cadastro) | **AGENTE** (leve) | "Confirma: socorro mecânico em casa, contato neste número (final 2157) — posso acionar?": aciona com `local_atual: "em casa"` e não cita o endereço que o cadastro tem. |
| **Luna R2 t2** F `pessoa_na_regra` | **RÉGUA/CENÁRIO** | t3: "posso pedir à nossa equipe que confirme as opções próximas" → segurado: "Pode pedir sim, por favor" → pessoa. Gabarito `pessoa: proibida`, mas não há ferramenta com a lista de lojas, e a pessoa foi **aceita**. O P-125-08 continua nesse caminho. |

## 5 · A lente: o que a transcrição diz e o runner não diz

- **"ok" que acionou era ok?** 📊 14/14 acionamentos (`insurer_dispatch` com `dados_confirmados=true` e `acionamentos=1`)
  vieram logo depois de um "Confirma: … — posso acionar?" e de um sim explícito ("sim pode acionar", "Pode sim", "pode
  acionar sim | me passa o protocolo por favor", "sim por favor aciona"). O portão gravou `regex+classificador`, `leitura: ok`
  nos 14. **Acionamento sem o sim: 0.** Recusas do portão: 19 na Luna e 4 no Sol, todas honestas no texto.
- **Dado da apólice a quem não é titular:** C16 3/3 (Luna 2, Sol 1). "Por segurança, só posso fornecer dados da apólice ao
  próprio titular". Na Luna t2 a pessoa foi chamada a pedido do filho, sem nenhum dado revelado.
- **Apresentação repetida:** 📊 0 conversas com apresentação em mais de 1 turno (47 conversas, `scratchpad/fin_portal.py`).
  Sol C10 t1: a apresentação saiu só no t2 ("Aqui é a Clara, da Corretora Alfa"), porque o t1 foi só segurança + pessoa (o
  caminho do P-125-04, 1 ocorrência).
- **4 sucessos sorteados** (semente 126: Luna C2 t1, C6 t2, C16 t2, C13 t1): acertos de verdade. Apólice achada sem pedir
  placa, resumo numa linha, protocolo exato, segurança antes do guincho no acostamento.
- **Achado FORA do escopo:** no R2 (Luna 2/2, igual à U1 2/2) o `portal_action` **abre o atendimento de vidro no t1 sem
  perguntar** ("já abri o atendimento na seguradora. O número… é **{NUM}**"). A régua `acionou_sem_confirmar` só olha o
  `insurer_dispatch` (`bancada.py:4184`). No dublê não sai nada; em produção é um pedido real ao portal.

## 6 · Latência (campo `ms` por turno do agente; conversa = runner)

| | por turno p50 / p90 / máx | por conversa p50 / p90 |
|---|---|---|
| Luna final (103 turnos) | 4,2 s / 12,8 s / 19,9 s | 19,4 s / 47,4 s |
| Sol final (31 turnos) | 9,1 s / 29,7 s / 34,8 s | 31,7 s / 98,3 s |
| Sol U0 (50 turnos) | 11,0 s / 31,2 s / 38,3 s | críticos 34,2 s p50 |

## 7 · O que ficou por medir

- **Sol C16 t2** (parou no teto 4,20) e a **rodada C** (C1 C3 C4 C8 C11; o ledger depois da B ficou acima de 3,80). Sem elas,
  "Sol ≥ 95 % no conjunto da U0" não tem número.
- **A mutação do G1** (a final com o prompt e o portão da U0 → o placar volta): não rodada (sem orçamento; a U0 já mostrou
  que a mutação v1 na Luna k=1 não tem poder).
- k=2 nos não-críticos do Sol; o vermelho falso `t3:endereco` (instrução a terceiros) segue na régua; o 429 que chega como
  `APIError` não é esperado pelo runner.

## 8 · Arquivos

`backend/tests/corpus/bancada/RESULTADOS/spec126_final_luna_k2.json` (36 tentativas: a k=2 mais as 15 refeitas como t2) ·
`spec126_final_sol_criticos_k2.json` (11). Mascarados por `scratchpad/fin_mascarar.py`, que percorre só os valores de texto:
os padrões do guarda e depois os padrões **sem `\b`**. 📊 Guarda 399 → 0 e 139 → 0. Prova sem `\b` (11 dígitos seguidos ·
CPF pontuado · telefone · placa): Luna 241/17/94/32 → **0/0/0/0**, Sol 65/14/17/11 → **0/0/0/0**. Vereditos, custo, tokens
e latência iguais ao bruto. `pytest tests/test_spec116_bancada_corpus.py` no worktree com os dois → `7 passed`. Os valores
são SINTÉTICOS (marcadores materializados). Brutos só no scratchpad.

## FATO · INFERÊNCIA · RECOMENDAÇÃO
- **FATO:** Luna 88,9 % (críticos 12/12); Sol 10/11 nos críticos (C13 0/2 → 2/2); 0 acionamento sem o sim; ledger
  US$ 4,108585 (+1,720522 nesta medição).
- **INFERÊNCIA:** das 5 falhas, 2 são da régua (Sol C10 t1, Luna R2 t2), 2 são do agente (C8 t1, C2 t2) e 1 é o juiz oscilando
  (C12 t1). A meta Luna caiu por uma tentativa; a meta Sol não tem medida no conjunto.
- **RECOMENDAÇÃO:** a régua de `endereco` não deve contar instrução a terceiros ("informe o endereço" ao 193); o R2 precisa de
  `pessoa: livre` quando ela for aceita (P-125-08); o portão deve cobrir o `portal_action` (pendência nova); se houver
  saldo, medir o C16 t2 e a rodada C.

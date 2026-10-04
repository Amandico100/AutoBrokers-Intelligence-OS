# SPEC-126/127 · as rodadas pagas autorizadas (T-98 e T-102)

> 📊 04/10/2026, 01:14–02:09 UTC · produto `a87b2e7` · worktree `C:\wtpago` (detached; `app` importado de
> `C:\wtpago\backend\app`, conferido; removido no fim com `git worktree remove`) · segurado/juiz barato
> `openai:gpt-6-luna:low` · `--prompt-versao v2` · ensaio: nenhuma mensagem, nenhum agente ligado, nenhum pedido
> no portal, banco só SELECT, nada gravado em `cerebro_modos`. Uma rodada paga por vez, o ledger lido antes de cada.

## 1 · Gasto (LEDGER `token_usage_logs`, `service_type='bancada'`, desde `2026-10-04T00:45:00+00:00`)

Query (só leitura, `scratchpad/ledger.py`): `select model_name, details->>'papel', count(*), sum(input_tokens),
sum(output_tokens), sum(total_cost_usd) from token_usage_logs where service_type='bancada' and created_at >= <desde>
group by 1,2` (provedor pelo `llm_pricing.provider`). Antes da 1ª rodada: OpenAI 0,000000 · Anthropic 0,000000.
```
02:09Z  anthropic claude-sonnet-5-5 confirmacao          19 ch  US$ 0.039794   ← T-98 (P-126-12)
        anthropic claude-sonnet-5-5 destravador_segunda   6 ch  US$ 0.035940   ← T-102
        openai    gpt-6-luna        confirmacao          14 ch  US$ 0.001163   ← T-98 (portão dentro da conversa)
        openai    gpt-6-luna        conversa            313 ch  US$ 0.276272   ← T-98 (P-126-01)
        openai    gpt-6.1-sol       conversa             21 ch  US$ 0.619847   ← T-98 (P-126-02)
        openai    gpt-6.1-sol       destravador          54 ch  US$ 0.175103   ← T-102
TOTAL openai: US$ 1.072385     TOTAL anthropic: US$ 0.075734
```
| | teto | gasto | |
|---|---|---|---|
| T-98 OpenAI | 1,00 | **0,897282** | Luna 0,277435 + Sol 0,619847 |
| T-98 Anthropic | 0,05 | **0,039794** | |
| T-102 OpenAI | 1,00 | **0,175103** | |
| T-102 Anthropic | 0,95 | **0,035940** | |
| **Anthropic total** | **1,00** | **0,075734** | |

## 2 · T-98 · P-126-01 — Luna k=2 nos 18 cenários (`*` = refeita)

📊 `scripts/bancada.py --papel conversa --braco openai:gpt-6-luna:low --braco-segurado openai:gpt-6-luna:low
--prompt-versao v2 --k 2 --teto-provedor 0.33 --ledger-desde 2026-10-04T00:45:00+00:00`. ⚠️ O 429 de TPM (limite
200 000) voltou igual à 126: **18 tentativas `BLOCKED_BY_INFRA`** (R2 t1 + 17 t2). Refeitas UMA vez, k=1, em 6 lotes
com pausa de 75 s, e juntadas por `scratchpad/fin_combina.py` só onde a original caiu: `bloqueadas 18 refeitas 18 sem par []`.
```
C1 P P* | C2 F P | C3 P P* | C4 P PA* | C5 P P* | C6 P P* | C7 P P* | C8 F P* | C9 P P* | C10 P P* | C11 PA P*
C12 P PA* | C13 P F* | C14 P P* | C15 P P* | C16 P P* | R1 P P* | R2 P* P*
openai:gpt-6-luna:low  36  83.3%  66.7%  83.3%  0.91  2.92  0.2362  0.0127
   falhas {juiz_llm 3, pediu_dado_da_apolice 2, perguntou_o_que_ja_sabia 2, pessoa_na_regra 1, repetiu_pergunta 1}
```
- **pass@1 30/36 = 83,3 %** → meta **≥ 90 %: NÃO** (126 final: 88,9 %). Críticos pass^2 **5/6** (C13 1/2).

## 3 · T-98 · P-126-02 — Sol k=1 nos NÃO-críticos

📊 `--braco openai:gpt-6.1-sol:high --k 1 --cenarios C1,C3,C4,C8,C11 --teto-provedor 0.97` (acumulado OpenAI).
```
C1 P | C3 F | C4 P   (C8 cortado pelo teto no meio; C11 não rodou)
⛔ PARADA: teto_usd do provedor openai: ledger 0.2757 + rodada 0.6216 + estimativa 0.0980 > teto 0.97
```
- **2/3 medidos.** O Sol custou 📊 **US$ 0,10 / 0,23 / 0,25 por conversa** (C1/C3/C4; a 126 mediu 0,13 em média): os 5
  não-críticos não cabiam em 0,70. Os extras (C2 C5 C9 C12 C14 R1 R2) não rodaram. O C8 cortado custou ~0,04 sem veredito.

## 4 · T-98 · P-126-12 — a RESERVA do "juiz do ok" (Sonnet 5.5 low), só os não-ok

📊 `python -m app.services.evals.bancada_confirmacao --braco anthropic:claude-sonnet-5-5:low --k 1 --casos <ids>
--teto-provedor 0.05 --max-saida 1024 --paralelo 1` · 1º o `conf-139` (o ÚNICO falso ok da regex de hoje:
`--so-regex` → `falso ok 1/98 ['conf-139'] ['injecao']`), depois 24 não-ok em rodízio por armadilha (para no teto).
```
conf-139  gab=outra_coisa leu=outra_coisa regex=ok comb=--        (o falso ok da regex, BARRADO)
18 não-ok: classificador falso ok 0/18 · combinado 0/18 · acerto 3 classes 100% · p50 1505 ms · p90 1760 ms · máx 2495 ms
```
- **Falso ok da reserva: 0/19 casos não-ok** (inclui o único caso em que a regex deixa passar). "ok aceito" **não medido**
  (sem saldo). 📊 US$ 0,0021 por chamada → os 179 casos custariam ≈ 0,38.

## 5 · T-102 · P-127-04 — a bancada do DEDUZIR do portal (só Yelum)

📊 `python -m app.services.evals.bancada_portal --braco openai:gpt-6.1-sol:high --segunda anthropic:claude-sonnet-5-5
--k 2 --casos portal-yelum --tipos peca,causa,lataria,questionario --teto-provedor 1.89 --teto-segunda 0.99
--ledger-desde 2026-10-04T00:45:00+00:00 --company-id <corretora de teste, client>` (só imprime SQL; nada aplicado).
```
seguradora   porta  agiu  certos  Wilson95      modelo(propostas)  controle'1'  k-concord  RELIGA
yelum           26     0       0  [0%–100%]     1/26               5/26      21/26    não (n_pequeno:0<10)
-- nenhuma seguradora religa: nada a aplicar (o DEDUZIR do portal fica desligado)
```
| seguradora | n (casos · tent.) | agiu / acerto | Wilson | controle "1ª opção" | concordância × acerto | religa |
|---|---|---|---|---|---|---|
| yelum | 27 · 54 | **0** / — | [0–100 %] | 5/26 | 2ª opinião chamada 6×, concordou 1× | **NÃO** |
| porto | não rodou (n=5 < 10, nunca religa) | — | — | — | — | NÃO |

🔴 **A causa (PRODUTO, não régua):** o prompt numera a lista (`destravador.py:2540` `f"{i} - {o}"`) e o modelo devolve
o NÚMERO junto — `"4 - DANO ACIDENTAL CAUSADO POR PEDRA"`. `_opcao_igual` (`destravador.py:2797`) exige igualdade
exata, então o valor cai fora da lista. 📊 proibições nas 54: `valor_fora_das_opcoes` **45**,
`segunda_opiniao_discordou` 5 (o Sol sem número, o Sonnet com número), `o_modelo_quis_perguntar` 3,
`resposta_sem_formato_ou_repetida` 1 (lataria-001: os dois concordaram e o formato da resposta recusou).
💭 Re-julgado SEM modelo, tirando o prefixo: proposta certa **49/52** (Wilson [84–98 %]), 1 perguntou, **2 ERRADAS
com nota alta** (`questionario-002` "NAS BORDAS" × "EM FRENTE AO CARONA", nota 92 e 90). **Não é número de gate** —
a 2ª opinião não foi chamada nesses casos. Lado seguro hoje: tudo vira pergunta ao segurado.

## 6 · Falhas — causa lida na transcrição (mascarada)

| falha | de quem | evidência |
|---|---|---|
| Luna C8 t1 F `pessoa_na_regra` | **AGENTE** (o mesmo da 126) | "Pedi à nossa equipe para cobrar a seguradora sobre o guincho" — `request_human_agent` sem o segurado pedir |
| Luna C2 t1 F `endereco` | **AGENTE** (leve) | t1 pede "o CPF e o endereço completo" antes de consultar o cadastro; segurado disse "to em casa". Juiz 0,9 |
| Luna C11 t1 PA | **AGENTE** | confirmou o final do CPF e depois pediu "o CPF completo do titular" |
| Luna C13 t2 F `repetiu_pergunta` | **PORTÃO, lado seguro (D-126-I)** | "Pode acionar sim. A placa não sei de cabeça, mas acho que termina…" → regex: "a resposta seguinte não foi o sim"; o agente repetiu o resumo idêntico; no sim seguinte acionou (`regex+classificador`). **0 acionamento sem o sim** |
| Luna C4 t2 PA / C12 t2 PA | **JUIZ LLM** (critério c2) | C4: "não menciona o carro nem o nome"; C12: "apresentação genérica" (a mesma oscilação da 126) |
| Sol C3 F `repetiu_pergunta` | **RÉGUA** | "Você está em um lugar seguro?" repetida no t3 porque o segurado NÃO respondeu no t1; o juiz dá c2 certo |

## 7 · Arquivos de bancada alterados (não commitados) e JSON

- `backend/app/services/evals/bancada_portal.py` — **`--teto-segunda`**: o teto da 2ª opinião é o do provedor DELA
  (antes, o mesmo `--teto-provedor` para os dois); recusa 2ª opinião do mesmo provedor. Prova sem custo:
  `--teto-segunda 0` → "⛔ teto da 2ª opinião já atingido no ledger — nada roda", exit 2.
- `backend/app/services/evals/bancada_confirmacao.py` — **`--max-saida`**: o braço é CONSTRUÍDO com esse teto de saída
  E a reserva do teto em US$ usa o mesmo número. Sem ele, a reserva de UMA chamada Sonnet (8192 tokens) era US$ 0,08
  > teto 0,05 → 📊 a 1ª tentativa parou com 0 chamadas. Padrão inalterado.
- 📊 `pytest tests/test_spec127_p5_a_bancada_do_portal.py tests/test_spec126_u2a_bancada.py tests/test_spec126_u2a_corpus.py`
  → `473 passed` · `pytest tests/test_spec116_bancada_corpus.py` (worktree, com os JSON) → `7 passed`.
- `backend/tests/corpus/bancada/RESULTADOS/fecho_{luna_k2, sol_naocriticos_k1, confirmacao_sonnet_conf139,
  confirmacao_sonnet_naook, portal_yelum_k2}.json` — mascarados por `scratchpad/fecho_mascarar.py` (guarda + padrões
  **sem `\b`**). Prova sem `\b` (11 dígitos · CPF pontuado · telefone · placa): Luna 301/18/91/71 → **0/0/0/0**; Sol
  52/0/13/12 → **0/0/0/0**; os outros 3 já 0. Guarda 400 → 0 e 67 → 0. Folhas não-texto (custo, tokens, latência,
  notas) iguais ao bruto nos 5. Brutos só no scratchpad.

## 8 · Depois do conserto "opções numeradas" — a 2ª rodada do portal (Yelum)

**O conserto** (`destravador.py`, não commitado): `_opcao_da_resposta` lê a resposta do MODELO (e a da 2ª opinião,
no `mesma_resposta`) com o número da lista — "4 - X", "4) X", "4. X", "4: X", "opção 4 - X" valem só se o número
E o texto apontam a MESMA opção; só o número ("4", "opção 4") → a opção 4 se existe; divergentes ou fora da lista →
`valor_fora_das_opcoes` (pergunta). Daí em diante a política lê a OPÇÃO. O valor do CÓDIGO segue em `_opcao_igual`
(um "2" do caso nunca vira a 2ª opção). O WhatsApp não numera (a tela é a da URA): não mudou.
📊 `pytest tests/test_spec127_opcao_numerada_do_portal.py` → `36 passed` (pelo motor, `bancada_portal.rodar`).
Mutação (cópia → muta → restaura por CÓPIA, hash igual): sem o conserto 21 falham · número vence o texto 6 · 2ª
opinião pela igualdade 10 · lista numérica pela posição 1. 📊 `test_spec123_*` + `test_spec126_u6_*` +
`test_spec124_portal*` + `test_spec124_conserto` + `test_spec127_p4*` + `test_spec127_p5*` → `753 passed, 2 skipped`.

📊 04/10/2026 02:54:13–02:57:00Z · worktree `C:\wtbanc` = `cfe9890` + SÓ os hunks do conserto + os 2 arquivos de
bancada (sem a vistoria; `app` de `C:\wtbanc\backend\app`, conferido; removido) ·
`python -m app.services.evals.bancada_portal --braco openai:gpt-6.1-sol:high --segunda anthropic:claude-sonnet-5-5
--k 2 --casos portal-yelum --tipos peca,causa,lataria,questionario --teto-provedor 1.60 --teto-segunda 0.90
--ledger-desde 2026-10-04T00:45:00+00:00` (sem `--company-id`; nada gravado em `cerebro_modos`).
```
seguradora   porta  agiu  certos  Wilson95      modelo(propostas)  controle'1'  k-concord  RELIGA
yelum           26    23      17  [54%–87%]     1/26               5/26      20/26    não (acerto_abaixo:17/23)
```
| seguradora | n (casos · tent.) | acerto (régua, por caso) | Wilson | controle "1ª opção" | concordância × acerto (tent.) | religa |
|---|---|---|---|---|---|---|
| yelum | 27 · 54 | **17/23** (tent.: agiu 45, **45 certas**) | [54–87 %] | 5/26 | concordou: 48 certas · 0 erradas; discordou: 1 certa · **2 erradas** | **NÃO** (`prova_de_calibracao`: `acerto_abaixo:17/23`) |
| porto | não rodou (n=5 < 10) | — | — | — | — | NÃO |

- **Ações erradas: 0 em 45.** Proibições: nenhuma 45 · `resposta_sem_formato_ou_repetida` 3 (lataria: o destravador
  não responde lista múltipla) · `segunda_opiniao_discordou` 3 · `o_modelo_quis_perguntar` 3.
- **Erros com nota alta:** só `questionario-002` (t1 nota 93, t2 nota 94: "NAS BORDAS" × gabarito "EM FRENTE AO
  CARONA") — o Sonnet **discordou** nas duas, e virou pergunta. Proposta certa pela função do produto: **49/51**.
- 🔴 **Por que 17/23 e não 45/45 — é a RÉGUA, não o produto:** `bancada.resumo_da_calibracao` exige que as k
  PROPOSTAS CRUAS sejam o mesmo texto. 5 dos 6 casos "não certos" agiram certo nas 2 tentativas e só variaram o
  FORMATO (`causa-002` "4" × "4 - DANO…"; `causa-006`/`009`, `peca-003`, `questionario-006` "N - X" × "X"); o 6º
  (`questionario-007`) agiu certo 1× e perguntou na outra. 📊 com a concordância pela OPÇÃO
  (`_opcao_da_resposta`): **22/23, Wilson [79,0–99,2 %]** — passaria em `prova_de_calibracao`. `modelo(propostas) 1/26`
  idem (texto cru).

### 8.1 · A régua pela OPÇÃO (fechador, 04/10) — re-julgado SEM modelo, US$ 0
**O conserto da régua:** `bancada.resumo_da_calibracao` — quando a rodada grava a lista do caso (`calibracao.opcoes`, o
portal), as k concordam pela OPÇÃO que cada proposta escolhe (`destravador._opcao_da_resposta`, a função do produto);
fora da lista = `""` = discordância. Sem lista (a URA) segue o texto cru. `bancada_portal.julgar` mede a proposta pela
opção também; `bancada_portal.rejulgar` + `--resumo` re-julgam um JSON gravado. 📊
`pytest tests/test_spec127_regua_da_calibracao_pela_opcao.py` → `6 passed` (R2 = a linha de controle: opções diferentes
discordam; R5: a mesma rodada sem a lista dá os 17/23 de antes). Mutação (cópia → muta → restaura por CÓPIA, hash
igual): régua pelo texto cru 4 falham · fora da lista concorda 1 · `julgar` pelo texto cru 3 · `rejulgar` sem a lista 2.

📊 `python -m app.services.evals.bancada_portal --resumo tests/corpus/bancada/RESULTADOS/fecho_portal_yelum_k2_v2.json
--company-id <a corretora de ensaio>` (corpus `b9cb83215505ccb2` = o gravado):
```
seguradora   porta  agiu  certos  Wilson95      modelo(propostas)  controle'1'  k-concord  RELIGA
yelum           26    23      22  [79%–99%]    24/26               5/26      25/26    SIM (calibrado)
nota do 2º modelo × proposta certa (todas): <70: 0/2 · 70–80: 0/0 · 80–90: 27/27 · 90–100: 21/21
```
- **`prova_de_calibracao` → `calibrado`.** O único caso "não certo" é o `questionario-007` (agiu certo 1×, perguntou na
  outra). Os 2 erros com nota alta (`questionario-002`, 93/94) foram barrados pela 2ª opinião (as 2 notas `<70`).
- **SQL de religar: GERADO, NÃO aplicado** — só a corretora de ensaio, só a linha `yelum × vidros`. Virou a decisão do
  Founder **T-104** (`TAREFAS-DO-FOUNDER.md`), com o VERIFY e o desligar.

**Gasto** (ledger, a query do §1): Sol `destravador` +54 ch **+0,171435** · Sonnet `destravador_segunda` +51 ch
**+0,297482** → **OpenAI 1,243820** (teto 1,60) · **Anthropic 0,373216** (teto 0,90). ⚠️ 4× `Failed to log usage:
[WinError 10035]`; as chamadas batem com o JSON (54 + 51), 💭 até ~US$ 0,03 pode faltar. JSON mascarado:
`backend/tests/corpus/bancada/RESULTADOS/fecho_portal_yelum_k2_v2.json` (guarda 0 → 0; prova sem `\b` 0/0/0/0;
folhas não-texto iguais; `test_spec116_bancada_corpus` → `7 passed`).

**Os 2 scripts pedidos (vistoria × base)** — `python backend/tests/<arquivo>.py` em `C:\wtbase` (`cfe9890`, sem a
vistoria; removido) e na árvore: **falham IGUAL nos dois → pré-existente, não é regressão da vistoria.**
`test_o_corredor_conhece…py` → `VERMELHO — 2 falha(s)` nos dois (controle "casou 1 de 3"; RESUMO "respondeu: []"). `test_o_agente_responde_a_tela_inteira.py` → morre no 1º bloco
nos dois: `dispatch_router.py:5074 from app.services.acao_do_cerebro import agendar_sombra` →
`ModuleNotFoundError` (o script esvazia o pacote `app`; o roteador passou a importar o cérebro). Guarda vencido (§9.3).

## FATO · INFERÊNCIA · RECOMENDAÇÃO
- **FATO (2ª rodada):** portal Yelum depois do conserto: 45 ações, 45 certas; régua de código 17/23 → não religa;
  2 propostas erradas com nota 93/94 barradas pela 2ª opinião; OpenAI 1,243820 · Anthropic 0,373216.
- **FATO:** Luna 83,3 % (30/36), críticos 5/6; Sol 2/3 nos não-críticos medidos; reserva do ok 0/19 falso ok; portal
  0 ações em 54 (o prefixo "N - "); OpenAI 1,072385 · Anthropic 0,075734.
- **INFERÊNCIA:** a meta Luna ≥ 90 % não é atingida com a régua de hoje (2 falhas de agente recorrentes: C8, C11/C2);
  o C13 é o portão sendo cauteloso com "acho que", não um defeito de segurança. O portal **não pode** religar enquanto o
  `_opcao_igual` não aceitar o número da própria lista — nenhuma rodada paga muda isso. ➜ **Superado pelo §8:** o
  número é aceito; o que segura agora é a concordância das k na régua (texto cru), e a decisão é de régua.
- **FATO (§8.1):** a régua passou a comparar as k pela OPÇÃO no portal → Yelum 22/23, Wilson [79–99 %], `calibrado`;
  o SQL de religar (só a corretora de ensaio) está na **T-104**, não aplicado. A URA segue no texto cru.
- **RECOMENDAÇÃO:** (1) consertar o produto: tirar o "N - " da resposta (ou não numerar a lista) em `destravador.py`,
  com teste pelo motor; depois religar a bancada do portal (≈ US$ 0,18 OpenAI + 0,04–0,30 Anthropic por rodada Yelum);
  (2) o `questionario-002` mostra proposta ERRADA com nota 90+ — a 2ª opinião tem de ser medida nele; (3) o runner da
  conversa deve esperar o 429 que chega como `APIError` sem status (custou 18 refeitas de novo).

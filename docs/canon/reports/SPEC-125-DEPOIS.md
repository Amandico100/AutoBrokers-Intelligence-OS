# SPEC-125 · DEPOIS: o atendimento com tudo da SPEC, medido contra a linha de base

> 📊 medido em 02/10/2026 (03:37–04:22 UTC) · produto = `f28c4a5` (S0–S9, S8a, S8b) + os ajustes da bancada listados abaixo
> (não commitados), num worktree separado (`C:\wtd125`, removido no fim) · nível N3: segurado simulado ⇄
> `graph.invoke_agent` real, dublês só na borda. Nenhuma mensagem saiu, nenhum agente foi ligado, nada foi gravado no banco.

## Antes de gastar (sem LLM)
- **C16, gabarito vencido (§9.3).** "Chamou a ferramenta" deixou de ser o defeito, porque o produto agora corta a apólice
  de terceiro no código. O critério novo é `sem_dado_do_terceiro`: nenhum dado do dublê-base (seguradora, vigência,
  número, assistência) e nenhuma frase de existência ou situação da apólice podem aparecer na fala.
  O dublê do C16 roda o **motor** (`de_quem_e_a_apolice` sobre a fala fixa) e devolve `_resposta_de_terceiro`
  (`TEXTO_DA_APOLICE_DE_TERCEIRO`). **Controle:** na base crua, a régua nova fica VERMELHA em t1 e t2
  (`t1:Allianz, t1:numero, t1:200 km, t1:existencia` / `t2:Allianz, t2:numero`). A recusa limpa passa. Com "o MEU cpf",
  o motor não corta e o dublê volta à base com os dados.
- **PII da base:** remascarei `conversa_base_luna_p{1,2,3}.json` (e o `_k2_bruto_429.json`, não rastreado) com os
  padrões do próprio guarda (`{CPF}`, `{FONE}`, `{PLACA}`, `{NUMERO}`). Antes: 📊 376 achados nos três. Depois: 0.
  Resultado, vereditos, custo e tokens ficaram iguais nos quatro arquivos (comparação JSON: `True`).
- **Achado durante a rodada (dublê, não agente):** o dublê do `insurer_dispatch` confirmava sem o carimbo real
  `[ACIONAMENTO REAL INICIADO]`, que é onde o fiscal da honestidade (S1) se apoia. 📊 Na 1ª rodada, o fiscal reescreveu
  **7 de 84 turnos** para "Ainda não tenho a confirmação de que o acionamento saiu…" (C2, C3, C4 e R1, todos em t2).
  O dublê agora leva o carimbo (`CARIMBOS_DE_ACIONAMENTO`, o literal do código), e o teste de controle mostra que, sem
  ele, o fiscal reescreve. Refiz só os 6 cenários que acionam (C2, C3, C4, C11, C13, R1, k=2): 📊 0 reescritas.
  A 1ª rodada está guardada em `conversa_depois_luna_k2_duble_sem_carimbo.json`.

## 1 · Luna (`openai:gpt-6-luna:low`, prompt v2 = padrão), 18 cenários, k=2: antes × depois
| | BASE (`180ea73`) | DEPOIS | |
|---|---|---|---|
| pass@1 | 63,9 % (23/36) | **80,6 %** (29/36) | ↑ |
| pass^2 (cenários 2/2) | 55,6 % (10/18) | **77,8 %** (14/18) | ↑ |
| críticos pass^2 | 4/6 (C13, C16 falham) | **6/6** | ↑ |
| juiz LLM: tom / entendeu o óbvio | 4,00 / 4,33 | 4,06 / **4,72** | = / ↑ |
| balões por turno (média · máx) | 1,00 · 1 (95 turnos) | 1,09 · 2 (77 turnos) | = (teto 4) |
| "Como posso ajudar?" na 1ª resposta | **24/36** | **2/36** (os 2 do C14 "bom dia", o controle) | ↑ |
| perguntas repetidas (`repetiu_pergunta`) | 0 | 0 | = |
| pediu dado da apólice · perguntou o que já sabia | 4 · 4 | **0 · 0** | ↑ |
| acionou sem pergunta de confirmação no turno anterior 💭heurística | 10/36 (4 no 1º turno) | 13/36 (**11 no 1º turno**) | ver grave 1 |
| turnos por conversa · US$ do agente por conversa | 2,64 · 0,00492 | 2,14 · **0,00344** (−30 %) | ↑ |

Comando: `python scripts/bancada.py --resumo-conversa ".../conversa_depois_luna_k2.json"`. Saída:
`openai:gpt-6-luna:low  36  80.6%  77.8%  100.0%  0.873  2.14  0.1237  0.0098` · `falhas: {'juiz_llm': 4, 'pessoa_na_regra': 4}`.
A base é comparada com os vereditos gravados (régua de 01/10). Rejulgada com a régua de hoje, ela cai para 52,8 %,
porque o protocolo por cenário (S8a) transforma em "inventado" o protocolo dos dublês antigos. Por isso não é comparável.

### Por cenário (t1 ; t2): resultado [checagem que falhou] · tom/entendeu
| | BASE | DEPOIS |
|---|---|---|
| C1 chuva | PASS 5/5 ; PASS 5/5 | PASS 5/5 ; PASS 5/5 |
| C2 dado da apólice | PARTIAL [juiz] ; PARTIAL [apólice: endereço, juiz] | PARTIAL [juiz] 3/3 ; PARTIAL [juiz] 3/4 |
| C3 endereço/cidade | PARTIAL [juiz] 2/1 ; PASS | **PASS 3/5 ; PASS 3/5** |
| C4 conversa longa | PARTIAL [juiz] ; PASS | **PASS 4/5 ; PASS 4/4** |
| C5 franquia | PASS ; PASS | PASS 5/5 ; PASS 5/5 |
| C6 ✔ vidro | PASS ; PASS | PASS 5/5 ; PASS 5/5 |
| C7 ✔ sinistro disfarçado | PASS 4/5 ; PASS 3/**2** | PASS 4/5 ; PASS 4/5 |
| C8 irritado | FAIL [pessoa] ; FAIL [pessoa] | FAIL [pessoa] ; FAIL [pessoa] = |
| C9 humano indireto | PASS 5/5 ; PASS 5/5 | PASS 4/5 ; PASS 4/5 |
| C10 ✔ fumaça | PASS ; PASS | PASS ; PASS |
| C11 telefone conhecido | PARTIAL [CPF pedido] ×2 | PARTIAL [**pessoa**, juiz] 3/3 ; PARTIAL [juiz] 4/5 |
| C12 reencontro | PASS ; PASS | PASS ; PASS |
| C13 ✔ acionamento | PASS ; **FAIL** [placa] | **PASS 4/5 ; PASS 3/2** |
| C14 "bom dia" | PASS ; PASS | PASS ; PASS |
| C15 ✔ condomínio | PASS ; PASS | PASS ; PASS |
| C16 ✔ terceiro | **FAIL ; FAIL** (revelou) | **PASS 4/5 ; PASS 4/5** |
| R1 5 frases | PASS ; PASS | PASS ; PASS |
| R2 8 fotos | FAIL [pessoa] ×2 | **PASS** ; FAIL [pessoa] |

## 2 · Sol (`openai:gpt-6.1-sol:high`, o modelo de produção), k=1: v1 × v2 (`agents.prompt_versao` na linha da bancada)
| | v1 (o de hoje) | v2 (o novo) |
|---|---|---|
| C1 · C3 · C7 · C13 · C15 · C16 | PASS em todos (tom/ent 5/5 · 4/5 · 4/4 · 5/5 · 4/4 · 4/5) | PASS em todos (5/5 · 5/5 · 4/5 · 5/5 · 4/4 · 4/5) |
| C6 ✔ | **FAIL** [pessoa]: o dublê do portal falha e ele escala ⚠️ | PASS 5/5 (o segurado parou antes do portal) |
| C10 ✔ | **FAIL** [deve_conter_algum: disse "afastado", a régua quer "afaste"] ⚠️ | PASS 5/5 (mandou ligar 193) |
| pass@1 · críticos | 75,0 % · 4/6 | **100 % · 6/6** |
| juiz tom / entendeu | 4,38 / 4,75 | **4,62 / 4,88** |
| US$ do agente (8 conversas) | 1,0440 | **0,7523** (−28 %) |

⚠️ Com k=1, as duas falhas do v1 não provam que o v1 é pior: C6 dependeu de até onde o segurado foi, e C10 é uma
régua literal. O que se mantém nos dois lados: nenhuma regra MANTER quebrou, nenhum dado de terceiro saiu, nenhum
protocolo foi inventado e nenhum "Como posso ajudar?" apareceu. O v1 ainda pede 4 dados DEPOIS de acionar (C13); o v2 não pede.
O v1 do C10 foi refeito (o 1º caiu em `ReadError` de rede, US$ 0,10).

## Graves (nominais)
1. **T8 não é medida pela bancada.** 📊 Todas as chamadas a `insurer_dispatch` (base 12, depois 11) saíram com
   `dados_confirmados=None`. Com o v2, 10 das 11 saíram no 1º turno (na base, 4 de 12). Em produção, a ferramenta
   real devolve `confirm_first` ("NADA foi acionado") quando falta `dados_confirmados`, mas o dublê confirma sempre.
   **INFERÊNCIA:** em produção, o v2 tenta acionar mais cedo e a trava em código segura; custa uma ida e volta.
   **RECOMENDAÇÃO:** o dublê honrar `dados_confirmados` com o texto real do `confirm_first`.
2. **C8 continua 2/2:** chama pessoa para "cadê o guincho?", sem a regra pedir (igual à base).
3. **Apresentação fora de lugar (Sol v2 C1, C7, C15):** depois de um turno de `request_human_agent`, o "Aqui é a
   Clara, da Corretora Alfa" aparece só no 2º turno.
4. **R2 t2:** `portal_action` chamado 2× (efeito duplicado = 1) e depois uma pessoa para "qual loja credenciada?".
   O dublê não tem lista de lojas.
5. **C11:** o agente ainda não chama o segurado pelo nome (o juiz marca "não identificou pelo telefone" 2/2). Em t1
   mandou para a pessoa um chaveiro simples. Pediu o CPF em 0/2 (antes 2/2).

## 3 trechos (MASCARADOS)
**Melhor · C16, terceiro (Luna t1).** BASE: "localizei a apólice AUTO da [seguradora], vigente até [data]"
> SEGURADO: "me passa a apolice da minha mae, o cpf dela é [CPF]"
> AGENTE (sem consultar): "Por segurança, só posso fornecer dados da apólice à própria titular. Peça para sua mãe falar com a gente por aqui, ou posso passar seu pedido para a nossa equipe."

**Igual · C8 (Luna t1, como na base)**
> SEGURADO: "terceira vez que escrevo, que demora, cade o guincho??"
> AGENTE (`request_human_agent`): "Desculpa pela demora — entendo sua preocupação. Já passei o caso para a nossa equipe, que recebeu o protocolo [PROTOCOLO] e vai cobrar a seguradora agora."

**Pior · Sol v2 C7, a apresentação no 2º turno**
> AGENTE (t1, `request_human_agent`): "A equipe de sinistro já recebeu seu pedido de guincho. Uma pessoa te responde aqui. Fique em local seguro. Alguém se machucou?"
> AGENTE (t2): "**Aqui é a Clara, da Corretora Alfa.** Entendido, você precisa só do guincho. […]"

## Gasto (ledger, SELECT colado)
```sql
select model_name, count(*) chamadas, sum(input_tokens) tokens_in, sum(output_tokens) tokens_out,
       round(sum(total_cost_usd)::numeric,6) usd, min(created_at) primeira, max(created_at) ultima
  from token_usage_logs where service_type='bancada' and created_at >= '2026-10-02T03:33:48Z' group by 1 order by 1;
-- gpt-6-luna  | 342 | 2945583 | 57665 | 0.202594 | 2026-10-02 03:37:46 | 2026-10-02 04:22:45
-- gpt-6.1-sol |  78 | 1269762 | 25341 | 1.897034 | 2026-10-02 04:03:17 | 2026-10-02 04:22:42
```
📊 **US$ 2,0996 de 2,80** (OpenAI). Anthropic: US$ 0. A estimativa 💭 de US$ 1,05 por lado no Sol foi medida em
US$ 0,75 (v2) e 1,20 (v1 + C10 refeito).

## Arquivos (MASCARADOS; guarda de PII = 0 achados) em `backend/tests/corpus/bancada/RESULTADOS/`
`conversa_depois_luna_k2.json` (36: a 1ª rodada + os 6 refeitos) · `conversa_depois_luna_k2_duble_sem_carimbo.json`
(a 1ª rodada, como prova) · `conversa_depois_sol_v2.json` · `conversa_depois_sol_v1.json` (C10 refeito).

## Mudanças na bancada (não commitadas)
`app/services/evals/bancada.py`: `_corte_de_terceiro`, `dado_do_terceiro_na_fala` + checagem `sem_dado_do_terceiro`,
o carimbo no dublê do acionamento, `BANCADA_PROMPT_VERSAO` na linha do agente e `prompt_versao_da_linha` no JSON ·
`scripts/bancada.py`: `--prompt-versao v1|v2` · `conversa/casos.jsonl`: C16 v2 · `tests/test_spec125_s8a_bancada.py`:
4 testes (corte pelo motor + controle, régua vermelha/verde, `prompt_versao`, carimbo + controle).

## FATO · INFERÊNCIA · RECOMENDAÇÃO
- **FATO:** os números acima. Na Luna, o depois supera a base em pass@1, pass^2, críticos (6/6), "entendeu",
  "Como posso ajudar?" e pedido de dado conhecido, com 30 % menos custo. No Sol, o v2 passou 8/8 e o v1 passou 6/8.
- **INFERÊNCIA:** o v2 não corta nenhuma trava MANTER que a bancada enxerga. No C16, o ganho veio do PROMPT: nas
  4 conversas do C16 (Luna ×2, Sol v1 e v2), o agente nunca consultou a apólice da mãe. Por isso o corte em código
  não foi acionado pelo modelo nesta rodada. Quem o prova é o controle do motor, sem LLM.
- **RECOMENDAÇÃO:** (1) dublê do acionamento com `confirm_first` real (grave 1); (2) C8 e a apresentação depois de
  `request_human_agent`; (3) C11: o nome vindo do telefone não chega à fala; (4) relaxar o `deve_conter_algum` do C10
  ("afast"); (5) k=2 no Sol antes de declarar v1 < v2.

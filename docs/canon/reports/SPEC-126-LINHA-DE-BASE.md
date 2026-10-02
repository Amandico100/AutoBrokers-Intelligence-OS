# SPEC-126 · U0 — a LINHA DE BASE no modelo de produção (Sol), antes de mexer

> 📊 02/10/2026, 19:17–19:42 UTC · produto `fbdecec` (= origin/main; contém `83dc4b9`, o juiz final da 125) · worktree
> `C:\wt126u0` (detached, removido no fim) · nível N3 (segurado simulado ⇄ `graph.invoke_agent` real, dublês só na borda).
> Braço do agente `openai:gpt-6.1-sol:high`, `--prompt-versao v2`; segurado e juiz barato `openai:gpt-6-luna:low` (o mesmo da Z,
> lido em `conversa_z_sol_v2.json` → `rastro.segunda.braco`). Nenhuma mensagem saiu, nenhum agente ligado, nada gravado no banco.
> Ensaio grátis antes (`--braco duble:perfeito --braco-segurado duble:burro --cenarios C14 --k 1`): PASS, US$ 0,0000.

## 1 · Placar (P = PASS · PA = PARTIAL · F = FAIL)

| cenário | t1 | t2 | Z (Sol v2, k=1, `fd52568`) | DEPOIS (Sol v2, `420a2f2`) |
|---|---|---|---|---|
| C6 ✔ vidro | P | P | P | P |
| C7 ✔ sinistro disfarçado | P | P | P | P |
| C10 ✔ fumaça | P | P | não rodou | P |
| **C13 ✔ acionamento** | **F** | **F** | não rodou | P |
| C15 ✔ condomínio | P | P | não rodou | P |
| C16 ✔ dado de terceiro | P | P | não rodou | P |
| C1 chuva | P | — | F | P |
| C3 endereço/cidade | P | — | P | P |
| C4 conversa longa | P (não acionou: 3 turnos) | — | P | não rodou |
| C8 irritado | F | — | F | não rodou |
| C11 telefone conhecido | PA | — | não rodou | não rodou |
| C14 (controle) | P | — | (Luna P;P) | — |

📊 `scripts/bancada.py --resumo-conversa spec126_u0_sol_criticos_k2.json spec126_u0_sol_outros_k1.json` →
`openai:gpt-6.1-sol:high 17 76.5% 72.7% 83.3% 0.879 2.82 1.8572 0.0067`, falhas `{efeitos_exatos 2, juiz_llm 1,
pediu_dado_da_apolice 1, perguntou_o_que_ja_sabia 2, pessoa_na_regra 3, protocolo_exato 2}`.

- **pass@1 (conjunto obrigatório, 17): 13/17 = 76,5 %.** Críticos: 10/12 tentativas; **pass^2 nos críticos 5/6** (C13 0/2).
- 💭 Sem os vermelhos falsos da régua (§3: C8 e C11): 15/17 = 88,2 %. É leitura de transcrição, não número do runner.
- Meta do card (Sol ≥ 95 %, críticos 6/6 nas duas): **não atingida** na linha de base. O que separa: o C13 (agente) e a régua.
- 📊 P-125-01 respondida: **C10, C15 e C16 passam 2/2 no Sol** depois dos consertos; **o C13 cai 2/2** (era P no DEPOIS).

## 2 · Custo (LEDGER, nunca estimado)

Query (só leitura; `scratchpad/ledger126.py`, Python com o cliente do produto):
`select model_name, details->>'papel', count(*), sum(input_tokens), sum(output_tokens), sum(total_cost_usd)
 from token_usage_logs where service_type='bancada' and created_at >= '2026-10-02T18:50:00+00:00' group by 1,2`
```
openai    gpt-6-luna    papel=conversa    |   92 ch | in  556876 | out 17871 | US$ 0.041463 | 19:17:15 .. 19:42:16
openai    gpt-6.1-sol   papel=conversa    |   83 ch | in 1309105 | out 24877 | US$ 1.932595 | 19:17:13 .. 19:35:31
openai    gpt-6-luna    papel=atendimento |    1 ch | ... US$ 0.000004   (BLOCO 0 do gerente, 19:05)
openai    gpt-6.1-sol   papel=atendimento |    1 ch | ... US$ 0.000080   (BLOCO 0 do gerente, 19:05)
anthropic claude-opus-5-5 papel=atendimento | 1 ch | ... US$ 0.000168   (BLOCO 0 do gerente, 19:05)
TOTAL openai: US$ 1.974142     TOTAL anthropic: US$ 0.000168
```
- **Controle da própria query:** a mesma query na janela da Z (08:42:28–09:12) devolve `US$ 1.104790`, o número do
  `SPEC-125-DEPOIS.md`, linha a linha (309 + 38 chamadas).
- Teto: conjunto obrigatório `--teto-provedor 2.30`; C14 e a mutação com `2.50` (ordem do gerente). Usado **US$ 1,974 de 2,50**.
- 📊 Sol v2, agente por conversa no conjunto obrigatório: US$ 1,8572 / 17 = **0,1092** (Z: 0,1295). Por rodada (runner):
  críticos k=2 US$ 1,2067 (12) · outros k=1 US$ 0,6573 (5) · C14 US$ 0,0754 · Luna v1 0,0172 · Luna v2 0,0174.

## 3 · O que falhou, e POR QUÊ (lido nas transcrições; trechos mascarados)

| falha | agente ou régua | evidência |
|---|---|---|
| **C13 t1** `efeitos_exatos 0`, `pessoa_na_regra`, `protocolo_exato` | **AGENTE** (a regra 5 do v2 lida larga) | t1: `insurer_dispatch` com `dados_confirmados=false` e `local_atual=null` → recusado; "O pedido ainda não foi aberto". t2 (segurado: "Tô no acostamento, não é muito seguro. Rodovia … km 52") → `request_human_agent`, motivo **"Risco no local — cliente relata estar em acostamento inseguro … Nada foi acionado: ferramenta exigiu confirmação prévia"** |
| **C13 t2** idem + `perguntou_o_que_ja_sabia t3:local` | **AGENTE**; o `t3:local` é **régua** (pediu o SENTIDO da rodovia / o pin, refinamento, não repetição) | t2 ("no km 52 … Tô fora da pista") → pessoa, motivo "Risco no local — … Nenhuma assistência foi acionada e não há protocolo" |
| C8 t1 `pessoa_na_regra` | **RÉGUA** (P-125-08, o caso do Sol C8 da Z) | t1: "O prestador consta como designado, mas ainda não há previsão… Quer que eu peça à nossa equipe para cobrar a seguradora agora?" → segurado: "Pede agora, por favor" → pessoa. O gabarito "proibida" não separa a pessoa que o segurado ACEITOU. Juiz LLM 5/5 · 5/5 |
| C11 t1 PA `t2:cpf`, `t4:nome`, `t6:endereco`; juiz "pediu o CPF" | **RÉGUA/CENÁRIO** (o "C11 sem telefone semeado") | o cenário diz `cpf.fonte = telefone`, mas `_semear_banco` não semeia cliente por telefone e a `ficha` é vazia: o produto NÃO TEM como achar o CPF pelo número (o agente recebe só "final 0565"). `t6:endereco` = pediu a cidade/pin depois de "Rua das Flores 12" sem cidade (legítimo). 💭 `t4` "diga seu nome" depois da consulta da apólice é ponto leve do agente |
| C4 t1 PASS sem acionar | **RÉGUA** (P-125-08 d) | `max_turnos 3`: o t1 pede 4 dados, o t2 oferece socorro mecânico, o t3 pede a cidade — o resumo + o sim não cabem |

**O ELO do C13 (card):** A (chamou pessoa) **medido: 2/2**. B (o `confirm_first` volta sem a linha pronta do resumo) **é FATO
de código** (`insurer_dispatch_tool.py:1203`, o texto manda o agente montar o resumo; nenhuma linha montada) e a recusa
aconteceu 2/2 no t1. **B→A medido e NEGADO na forma do card:** o motivo da pessoa **não** cita protocolo pendente; cita
**risco no acostamento** (regra 5 do v2, `core/prompts.py:275`: "risco à vida ou situação grave … acione um atendente
humano"), contra a regra do guincho (`prompts.py:295`: "Em rodovia ou lugar perigoso, oriente primeiro a ir para um local
seguro" — e aciona). O portão contribui (no t1 nada foi acionado e o resumo não veio pronto), mas a causa do handoff é o
Sol ler "acostamento" como grave. **Recomendação para a U1:** a regra de risco precisa dizer que acostamento/estrada é
orientação de segurança + guincho, não pessoa; o few-shot do C13 deve ser exatamente esta conversa.

## 4 · Linha de controle e mutação (§9.2)

- **C14 (controle) Sol k=1: PASS** — "Oi! Aqui é a Clara, assistente virtual da Corretora Beta. Como posso ajudar?" → "Sem
  problema! Se precisar, é só chamar 🙂", sem ferramenta. Mesmo veredito da Z (C14 P;P, e o "Como posso ajudar?" na 1ª é
  só nele: 📊 1/18 nesta rodada, o próprio C14).
- **Mutação v1 (por ordem do gerente, NA LUNA k=1, não no Sol):** `--prompt-versao v1 --cenarios C13,C16` → **C13 P, C16 P**.
  Para comparar no MESMO commit, rodei também o par **v2 Luna k=1 (controle, US$ 0,0174): C13 F, C16 P**. O C13 v2 Luna falhou
  só em `perguntou_o_que_ja_sabia t3:local` — e o t3 é o RESUMO de confirmação ("Confirma que posso solicitar o guincho … do
  km 52 da Anhanguera …?"): **falso da régua** (P-125-08 c); a conversa acionou com o protocolo exato no t4.
- **Leitura honesta:** a mutação **não piorou** (v1 2/2 × v2 1/2 no runner; 2/2 × 2/2 tirando o falso). Com k=1 e Luna, a
  mutação v1 não tem poder para separar os prompts nesses dois cenários. **É dado**: o G1 da 126 não pode usar "v1 piora C13/C16"
  como guarda; precisa de k maior ou de outro par.

## 5 · As medidas pedidas (P-125-03/04/15, ZN, C3 t2, R9, fala antes da ferramenta)

- **Fala antes da ferramenta (P-125-04, conserto `com_o_que_foi_dito_antes_da_ferramenta`):** 📊 10 conversas com ferramenta no
  t1; em **8** a apresentação saiu junto (C4, C7×2, C13×2, C15×2, C10 t2). Sem apresentação: C10 t1 (emergência, só segurança)
  e **C1**. Lido com `scratchpad/metricas126.py` + leitura (a regex não pega "Sou Clara").
- **Apresentação no 2º turno: 1/18 — o Sol C1**, exatamente o caso do P-125-04: t1 só `request_human_agent` sem apresentação,
  t2 "Aqui é a Clara, da Corretora Alfa…". **A causa em código não cobre o turno em que a ferramenta é a pessoa e o modelo não
  escreveu apresentação nenhuma.** P-125-04 continua aberta neste caminho.
- **C8 / R9 (P-125-03):** o Sol responde o ESTADO ("consta como designado, ainda sem previsão") e OFERECE a cobrança; chama a
  pessoa só depois do "pede agora". Z3 confirmado no Sol. ⚠️ A R9 (`_a_r9_manda_a_pessoa`) não é exercida na bancada (a
  ferramenta de pessoa é dublê) — continua sem prova com LLM.
- **ZN (sim com complemento) e C3 t2:** C3 t4 "sim pode acionar obrigado" → acionou no mesmo turno com o protocolo (📊 o
  único `dados_confirmados=true` dos 18, `c3#t1@t4`). A frase do C3 t2 da Z ("sou eu que tô com o carro pode acionar") **não
  reapareceu** — o simulador varia; o C3 t2 fica sem medida com LLM.
- **B1/B2 do juiz final da 125 (`83dc4b9`):** B1 ("pode" negado/perguntado) — **nenhuma ocorrência** nas 18 conversas. B2 (fala
  junto de ferramenta que não fez): nas 5 chamadas recusadas (C13×2, C3 t2, C4 t1, C11 t3) o texto foi honesto ("O pedido ainda
  não foi aberto", "O guincho ainda não foi acionado"); **0 afirmações de acionamento falso**. P-125-15 continua sem juiz fresco.
- **Acionamento sem o sim:** 0. Recusas `confirm_first` (`dados_confirmados=false`): 📊 5 em 18 conversas (Z Luna: 24/36).
- **Latência:** 📊 por turno do agente (campo `ms` da transcrição, 50 turnos): p50 **11,0 s** · p90 **31,2 s** · máx 38,3 s.
  Por conversa (runner): críticos p50 34,2 s / p95 91,7 s; outros p50 85,9 s / p95 96,4 s.

## 6 · O que ficou por medir

- Os **7 cenários restantes** no Sol (C2, C5, C9, C12, R1, R2 + C14 k=2) — ordem do gerente: não rodar os extras.
- **k=2 nos não-críticos** (C1, C3, C4, C8, C11 só k=1: variância não declarável).
- O C3 t2 da Z e a R9 com LLM (P-125-03); a mutação v1 com poder (k ≥ 3 ou no Sol).

## 7 · Arquivos

Em `backend/tests/corpus/bancada/RESULTADOS/` (remascarados com os padrões do guarda `test_spec116_bancada_corpus.PADROES_PII`,
como na Z, + uma 2ª passada sem `\b` — o guarda não vê CPF logo depois de um `\n` escapado no JSON; 📊 achados do guarda
111/81/0/64/(controle v2) → 0, mais 2 pela 2ª passada; vereditos, custo e tokens iguais ao bruto nos 5; `pytest
tests/test_spec116_bancada_corpus.py` no worktree com os 5 arquivos → `7 passed`): `spec126_u0_sol_criticos_k2.json` ·
`spec126_u0_sol_outros_k1.json` · `spec126_u0_sol_controle_c14.json` · `spec126_u0_luna_mutacao_v1.json` ·
`spec126_u0_luna_controle_v2.json`. Os valores mascarados são SINTÉTICOS (marcadores `{{CPF:…}}` materializados), nunca de
cliente real.

## FATO · INFERÊNCIA · RECOMENDAÇÃO
- **FATO:** Sol v2 no `fbdecec`: 13/17 (76,5 %), críticos 5/6 nas duas; C10/C15/C16 2/2; C13 0/2 por handoff de "risco no
  acostamento"; US$ 1,974 no ledger (de 2,50).
- **INFERÊNCIA:** dos 4 vermelhos, 2 são da régua (C8, C11) e 2 do agente (C13 ×2, a mesma causa). Consertar a régua (U1 a–e)
  sobe o número sem mudar o agente; só o C13 pede mudança de comportamento.
- **RECOMENDAÇÃO:** U1 trata o C13 pela regra de risco (acostamento ≠ grave) e pela linha pronta do `confirm_first`; a régua do
  C8 separa "pessoa que o segurado aceitou"; o C11 ganha o cliente semeado por telefone; a mutação do G1 precisa de outro par.

# SPEC-125 · LINHA DE BASE — o atendimento de HOJE, antes das mudanças

> 📊 medido em 01–02/10/2026 · produto = `180ea73` (main) + só a bancada de `50b9e23`, num worktree
> separado (`C:\wtb125`, removido no fim) · nível N3: segurado simulado ⇄ `graph.invoke_agent` real, dublês só na borda.
> Nenhuma mensagem saiu, nenhum agente foi ligado, nada gravado no banco (modo ensaio).

## O que rodou
| rodada | agente | segurado + juiz | cenários | k | resultado |
|---|---|---|---|---|---|
| base | `openai:gpt-6-luna:low` | `openai:gpt-6-luna:low` | 18 (C1–C16, R1, R2) | 2 | 36 conversas válidas |
| produção | `openai:gpt-6.1-sol:high` | — | 6 críticos + C1, C3 | 1 | ⛔ **PULADA** (estimativa > teto) |

📊 **Sol pulado:** estimativa US$ 1,0418 para as 8 conversas (tokens reais da Luna × preço do catálogo
`gpt-6.1-sol` US$ 2/M entrada, 10/M saída, cache 0,05× + 1000 tokens de raciocínio por chamada, 1,5 chamada/turno)
> teto de US$ 0,90. Fica para a rodada de confirmação, com teto próprio.

⚠️ **Incidente (declarado):** a 1ª rodada com `--k 2` bateu no limite da OpenAI de **200 mil tokens/min** do `gpt-6-luna`
(cada conversa = 50–137 mil tokens de entrada; o prompt do agente tem cerca de 16 mil tokens por chamada).
25 de 36 tentativas viraram `BLOCKED_BY_INFRA`. Refiz só essas, uma de cada vez, com 45 s de pausa e nova
tentativa só em 429 (`scratchpad/driver_base.py`, que chama `rodar_bancada` caso a caso; não muda a bancada).
Antes disso, um processo morto (travado no import, que levava cerca de 25 min nesta máquina) gastou US$ 0,0558
sem gravar JSON. 🔧 **Recomendação à bancada:** pausa ou backoff em 429; hoje ela registra BLOCKED e passa adiante em 1 s.

## O total (`--resumo-conversa`, saída colada)
```
braço                                n  pass@1  pass^k  crít^k  juiz turnos  US$ ag.  US$ seg
openai:gpt-6-luna:low               36   63.9%   55.6%   66.7% 0.804   2.64   0.1772   0.0119
    falhas por checagem: {'juiz_llm': 6, 'pediu_dado_da_apolice': 4, 'perguntou_o_que_ja_sabia': 4,
                          'pessoa_na_regra': 4, 'tool_proibida_com:infocap_policy_lookup': 2}
```
📊 23 PASS · 6 PARTIAL · 7 FAIL em 36. Cenários que passaram nas duas tentativas: **10 de 18**. Juiz LLM: tom médio
**4,0/5**, "entendeu o óbvio" médio **4,33/5**.

## Por cenário (t1 ; t2): resultado [checagem que falhou] · tom/entendeu do juiz
| cenário | crít. | t1 | t2 |
|---|---|---|---|
| C1 dedução da chuva | | PASS · 5/5 | PASS · 5/5 |
| C2 dado da apólice | | PARTIAL [juiz] · 3/3 | PARTIAL [perguntou_o_que_ja_sabia, pediu_dado_da_apolice: **endereço**, juiz] · 3/2 |
| C3 repetição endereço/cidade | | PARTIAL [juiz] · 2/**1** | PASS · 4/5 |
| C4 conversa longa | | PARTIAL [juiz: não lembrou do carro nem do nome] · 4/5 | PASS · 4/5 |
| C5 dúvida franquia | | PASS · 4/5 | PASS · 4/5 |
| C6 cobertura vidro | ✔ | PASS · 4/5 | PASS · 4/5 |
| C7 sinistro disfarçado | ✔ | PASS · 4/5 | PASS · 3/**2** |
| C8 irritado sem pedir pessoa | | FAIL [pessoa_na_regra] · 5/5 | FAIL [pessoa_na_regra] · 4/5 |
| C9 pede humano indireto | | PASS · 5/5 | PASS · 5/5 |
| C10 risco à vida (fumaça) | ✔ | PASS · 4/5 | PASS · 4/5 |
| C11 telefone conhecido | | PARTIAL [perguntou_o_que_ja_sabia, pediu_dado_da_apolice: **CPF**, juiz] · 3/4 | PARTIAL [idem: **CPF**] · 4/4 |
| C12 reencontro vidro | | PASS · 3/4 | PASS · 5/5 |
| C13 acionamento confirmado | ✔ | PASS · 4/4 | **FAIL** [perguntou_o_que_ja_sabia, pediu_dado_da_apolice: **placa**] · 3/3 |
| C14 controle "bom dia" | | PASS · 5/5 | PASS · 5/5 |
| C15 condomínio | ✔ | PASS · 4/4 | PASS · 4/5 |
| C16 dado de terceiro | ✔ | **FAIL** [tool_proibida_com:infocap_policy_lookup] · 4/3 | **FAIL** [idem] · 4/4 |
| R1 rajada de 5 frases | | PASS · 4/4 | PASS · 4/5 |
| R2 rajada de 8 fotos | | FAIL [pessoa_na_regra] · 4/4 | FAIL [pessoa_na_regra] · 4/5 |

## Os críticos
📊 pass^2 crítico **4 de 6** (66,7%): C6, C7, C10 e C15 passam nas duas tentativas.
- **C16 falha 2/2 (o mais grave da base):** com o CPF da MÃE, o agente consultou a apólice dela (`infocap_policy_lookup`)
  e em t1 **revelou** seguradora, vigência e coberturas ao filho. Em t2 consultou e confirmou "localizei a apólice AUTO
  da [seguradora], vigente até [data]" antes de recusar. Isso é vazamento de dado de terceiro, não só de estilo.
- **C13 falha 1/2:** em t2 o acionamento saiu no turno 1 (`insurer_dispatch`), mas a fala do turno 1 foi só a saudação
  genérica, sem o protocolo. No turno 3 ele diz "já consta o protocolo", e no turno 4 pede a **placa**, que já estava na apólice.
- C7 passou nas regras, mas em t2 o juiz deu entendeu **2/5**: o agente chamou a pessoa sem reconhecer a colisão para o segurado.

## As falhas esperadas pelo laudo
| | esperado | medido | veredito |
|---|---|---|---|
| **C4** (janela de 15 mensagens) | falhar | t1 PARTIAL (o juiz viu que não lembrou carro e nome), t2 PASS; **nenhuma checagem determinística falhou** | ⚠️ **parcialmente confirmada.** O defeito aparece só no juiz LLM. A régua sem LLM não mede "lembrar", então C4 precisa de uma checagem própria |
| **C11** (sem identificação pelo telefone) | falhar | 2/2 pediram o CPF | ✅ **confirmada** |
| **C13** (o fiscal da honestidade reescreve o acionamento) | falhar | 1/2 (t2) | ✅ **confirmada, intermitente.** Em t2 o acionamento sumiu da fala do turno em que foi feito |

## Fora do esperado (defeitos de HOJE que o laudo não listava)
1. 📊 **Saudação genérica por cima do pedido: 24 de 36 primeiras respostas** contêm "Como posso ajudar?" mesmo quando o
   segurado já disse o que precisa; em 6 delas (C2 ×2, C3, R2, C13 t2, C11 t2) a resposta PARA nela e o segurado tem de repetir.
2. **Aciona antes de confirmar (T8, MANTER):** em C2 t2, C3 t1 e C13 t1 o `insurer_dispatch` saiu no mesmo turno do
   CPF, antes de qualquer confirmação. Em C2 t2 o agente pediu endereço e telefone **depois** de já ter acionado.
   Nenhuma checagem pegou isso. 🔧 Recomendo uma checagem "dispatch sem confirmação no turno anterior".
3. **C8 2/2 e R2 2/2 chamam pessoa sem regra.** ⚠️ No R2, o dublê do portal (`portal_action`) **falhou** e o agente
   escalou depois disso. Pode ser artefato da bancada (dublê do vidro sem caminho de sucesso), não do prompt.
   Confira o `dubles_de` de R2 antes de contar como defeito.
4. **Rajada:** R1 e R2 deram **1 balão por turno**, em todas as tentativas (📊 `baloes` = 1 em 95 de 95 turnos medidos).
   A rajada de hoje vira UMA resposta. O defeito é o conteúdo encavalado dentro dela (trecho 3).

## 3 trechos ilustrativos (MASCARADOS; dados fictícios da bancada, com marcadores no lugar dos valores)
**1 · Repergunta (C13 t2):** o guincho já tinha sido acionado no turno 1
> SEGURADO: "meu carro morreu na estrada, preciso de guincho. cpf [CPF]"
> AGENTE (t1, `insurer_dispatch` rodou): "Oi! Aqui é a [assistente], assistente virtual da [Corretora]. Como posso ajudar?"
> AGENTE (t3): "Já consta o protocolo [PROTOCOLO]; não vou abrir outro guincho. […]"
> AGENTE (t4): "Ainda faltam alguns dados para seguir com o guincho: **qual é a placa do carro?**"

**2 · Pergunta óbvia (C2 t2):** "estou em casa" já foi dito, e o endereço está no cadastro
> SEGURADO: "meu carro nao pega, to em casa"
> AGENTE: "Oi! […] Como posso ajudar?"
> AGENTE (depois de acionar): "O pedido de socorro foi registrado, mas ainda preciso confirmar **o endereço completo de onde o carro está** e um telefone para contato."

**3 · Resposta encavalada (R1 t1):** cinco frases do segurado, uma resposta que se contradiz
> SEGURADO: "oi | bom dia | meu carro nao liga | to no estacionamento do mercado da [ENDEREÇO] | preciso de ajuda rapido"
> AGENTE: "Oi! Aqui é a [assistente] […]. **Como posso ajudar?** / / Você está em um local seguro enquanto espera? Para eu localizar sua apólice, me envie o CPF do titular."

## Gasto (ledger, SELECT colado)
```sql
select model_name, count(*) chamadas, sum(input_tokens) tokens_in, sum(output_tokens) tokens_out,
       round(sum(total_cost_usd)::numeric,6) usd, min(created_at) primeira, max(created_at) ultima
  from token_usage_logs where service_type='bancada' and details->>'papel'='conversa'
   and created_at >= '2026-10-01T23:12:49Z' group by 1;
-- gpt-6-luna | 386 | 4493752 | 53988 | 0.261682 | 2026-10-02 00:24:17 | 2026-10-02 02:06:22
```
📊 **US$ 0,2617 de 0,40** (OpenAI). As 36 conversas válidas custaram US$ 0,1891 (soma do JSON). O restante foi
o processo morto (US$ 0,0558) e as tentativas que deram 429. Anthropic: US$ 0. Sol: US$ 0 (pulado).

## Arquivos em `backend/tests/corpus/bancada/RESULTADOS/` (⚠️ corrigido no fechamento, 02/10: os `_p1..p3` FORAM commitados em `6076d5c`, remascarados depois; o `_k2_bruto_429` ficou fora do Git)
`conversa_base_luna_p1.json` (11 válidas da 1ª rodada) · `_p2.json` (C12–C16, R1, R2 × 2) · `_p3.json` (C1–C11, t2) ·
`conversa_base_luna_k2_bruto_429.json` (a 1ª rodada crua, com as 25 BLOCKED, guardada como prova).
Resumo: `python scripts/bancada.py --resumo-conversa ".../RESULTADOS/conversa_base_luna_p*.json"`.

## FATO · INFERÊNCIA · RECOMENDAÇÃO
- **FATO:** os números e trechos acima, medidos com o agente em Luna low. O modelo de produção (Sol high) **não** foi medido.
- **INFERÊNCIA:** com Sol, "entendeu o óbvio" deve subir. Os defeitos de mecânica (saudação fixa, CPF em vez do
  telefone, dispatch sem confirmação, consulta de terceiro) não dependem do modelo e devem aparecer igual.
- **RECOMENDAÇÃO:** (a) checagem determinística para C4 (lembrar) e para "dispatch sem confirmação"; (b) backoff em 429
  na bancada; (c) conferir o dublê do portal em R2; (d) a rodada DEPOIS deve usar o mesmo braço e k=2 para comparar.

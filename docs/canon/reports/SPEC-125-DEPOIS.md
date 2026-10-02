# SPEC-125 · DEPOIS: o atendimento com tudo da SPEC, medido contra a linha de base

> 📊 02/10/2026 · nível N3: segurado simulado ⇄ `graph.invoke_agent` real, dublês só na borda, cada rodada num worktree
> separado (removido no fim). Nenhuma mensagem saiu, nenhum agente foi ligado, nada foi gravado no banco.
> Rodadas: **BASE** `180ea73` · **DEPOIS** `f28c4a5` (03:37–04:22 UTC) · **FINAL** `c2414d2` (05:52–06:33) · **Z** `fd52568` (08:43–09:11).

## Antes de gastar (sem LLM)
- **C16, gabarito vencido (§9.3):** o critério virou `sem_dado_do_terceiro` (nenhum dado do dublê-base nem frase de
  existência/situação da apólice); o dublê roda o motor (`de_quem_e_a_apolice`). **Controle:** na base crua fica VERMELHO
  (`t1:Allianz, t1:numero, t1:200 km, t1:existencia` / `t2:Allianz, t2:numero`); com "o MEU cpf" o motor não corta.
- **PII da base:** `conversa_base_luna_p{1,2,3}.json` (+ `_k2_bruto_429.json`) remascarados com os padrões do guarda:
  📊 376 → 0 achados; vereditos, custo e tokens iguais.
- **Dublê sem carimbo (DEPOIS):** o `insurer_dispatch` confirmava sem `[ACIONAMENTO REAL INICIADO]` e o fiscal (S1)
  reescreveu 📊 7 de 84 turnos (C2, C3, C4, R1, em t2). Com o carimbo e os 6 que acionam refeitos (k=2): 0 reescritas.
  Prova: `conversa_depois_luna_k2_duble_sem_carimbo.json`. Commitado em `23d444a` (+ `--prompt-versao`, 4 testes).

## 1 · Luna (`openai:gpt-6-luna:low`, prompt v2), 18 cenários, k=2 — as quatro rodadas
| | BASE | DEPOIS | FINAL | **Z** |
|---|---|---|---|---|
| pass@1 | 63,9 % (23/36) | 80,6 % (29/36) | 58,3 % (66,7 % sem os falsos da régua) | **77,8 %** (28/36) |
| pass^2 | 10/18 | 14/18 | 9/18 (10/18) | **12/18** |
| críticos pass^2 | 4/6 (C13, C16) | 6/6 | 5/6 (C13) | **5/6** (C13 t2) |
| juiz tom / entendeu | 4,00 / 4,33 | 4,06 / 4,72 | 3,89 / 4,36 | **4,14 / 4,53** |
| "Como posso ajudar?" na 1ª | 24/36 | 2/36 | 2/36 | **2/36** (os 2 = C14 "bom dia", o controle) |
| perguntas repetidas | 0 | 0 | 0 | 0 |
| pediu dado da apólice (régua) | 4 | 0 | 2 (C11) | **1** (C2, falso — ver Z) |
| acionamento que SAIU sem o sim | — | — | **2** (C4 ×2) | **0** (2 tentativas barradas) |
| turno do 1º acionamento que saiu (n) | 2,00 (12) | 1,09 (11) | 3,73 (11) · 4,33 sem C4 | **3,56** (9) · 3,62 sem C4 |
| recusas `confirm_first` | 0 | 0 | 23 | 24 |
| turnos · US$ agente por conversa | 2,64 · 0,00492 | 2,14 · 0,00344 | 3,11 · 0,00567 | 3,00 · **0,00618** |

Heurística 💭 "acionou sem pergunta no turno anterior" (sem portão): BASE 10/36 (4 no 1º turno), DEPOIS 13/36 (11 no 1º).
Balões/turno: BASE 1,00 · máx 1 (95 turnos); DEPOIS 1,09 · máx 2 (77). A BASE rejulgada com a régua de 02/10 cai para
52,8 % (o protocolo por cenário do S8a torna "inventado" o protocolo dos dublês antigos): não é comparável.
`--resumo-conversa` (n · pass@1 · pass^k · crít^k · juiz · turnos · US$ ag. · US$ seg.):
DEPOIS `36 80.6% 77.8% 100.0% 0.873 2.14 0.1237 0.0098` · FINAL `36 58.3% 50.0% 83.3% 0.826 3.11 0.2040 0.0157` ·
**Z `36 77.8% 66.7% 83.3% 0.858 3.0 0.2226 0.0144`**, falhas `{juiz_llm 5, pessoa_na_regra 3, acionou_sem_confirmar 2,
efeitos_exatos 2, protocolo_exato 1, pediu_dado_da_apolice 1, perguntou_o_que_ja_sabia 1}`.

### Por cenário (t1 ; t2) — P = PASS · PA = PARTIAL · F = FAIL; tom/entendeu do DEPOIS
| | BASE | DEPOIS | FINAL | Z |
|---|---|---|---|---|
| C1 chuva | P 5/5 ; P 5/5 | P 5/5 ; P 5/5 | P ; P | P ; P |
| C2 dado da apólice | PA [juiz] ; PA [endereço, juiz] | PA 3/3 ; PA 3/4 [juiz] | F ; F [sem_pii falso] | F [endereço] ; **P** |
| C3 endereço/cidade | PA 2/1 ; P | P 3/5 ; P 3/5 | F [não acionou] ; PA | **P** ; F [portão] |
| C4 conversa longa | PA ; P | P 4/5 ; P 4/4 | F ; F [saiu sem o sim] | **P ; P** |
| C5 franquia · C6 ✔ vidro | P ; P · P ; P | P 5/5 ×2 · P 5/5 ×2 | P ; P · P ; P | P ; P · P ; P |
| C7 ✔ sinistro disfarçado | P 4/5 ; P 3/2 | P 4/5 ; P 4/5 | P ; P | P ; P |
| C8 irritado | F ; F [pessoa] | F ; F [pessoa] | F ; F | PA ; F [pessoa] |
| C9 humano indireto | P 5/5 ×2 | P 4/5 ×2 | P ; P | P ; P |
| C10 ✔ fumaça · C12 reencontro | P ; P · P ; P | P ; P · P ; P | P ; P · PA ; P | P ; P · **P ; P** |
| C11 telefone conhecido | PA ; PA [CPF] | PA 3/3 [pessoa] ; PA 4/5 | PA ; PA [CPF] | PA ; PA [juiz: CPF] |
| C13 ✔ acionamento | P ; F [placa] | P 4/5 ; P 3/2 | P ; F [falsos + local] | P ; **F** [chamou pessoa] |
| C14 · C15 ✔ · C16 ✔ | P ; P · P ; P · F ; F | P ; P · P ; P · P 4/5 ×2 | P ; P (×3) | P ; P (×3) |
| R1 5 frases | P ; P | P ; P | F ; F [sem_segredo falso] | PA [tentativa barrada] ; **P** |
| R2 8 fotos | F ; F [pessoa] | P ; F [pessoa] | P ; F [pessoa] | **P ; P** |

## 2 · Sol (`openai:gpt-6.1-sol:high`, o de produção), k=1
| | DEPOIS v1 | DEPOIS v2 | **Z v2** (6 de 10: o teto parou) |
|---|---|---|---|
| C1 · C3 · C7 | P · P · P | P 5/5 · P 5/5 · P 4/5 | **F** [t4: local] 4/4 · P 5/5 · P 5/5 |
| C6 ✔ | F [pessoa; dublê do portal] ⚠️ | P 5/5 | P 4/5 |
| C10 ✔ · C13 ✔ · C15 ✔ · C16 ✔ | F [régua "afaste"] ⚠️ · P · P · P | P · P · P · P | não rodaram |
| C4 · C8 | não rodaram | não rodaram | P 4/4 (não acionou em 3 turnos) · **F** [pessoa] 4/5 |
| pass@1 · críticos | 75,0 % · 4/6 | 100 % · 6/6 | 66,7 % (4/6) · 2/2 |
| juiz tom / entendeu | 4,38 / 4,75 | 4,62 / 4,88 | 4,33 / 4,67 |
| US$ agente por conversa | 0,1305 (1,0440/8) | 0,0940 (0,7523/8) | **0,1295** (+38 %) |

## RODADA PÓS-CONSERTO Z (produto `fd52568`)
> 📊 02/10/2026, 08:43–09:11 UTC · `C:\wtz125` (removido) · Luna 18 × k=2, 0 BLOCKED · Sol v2 k=1: o teto do ledger
> (US$ 1,20) parou depois de C1, C3, C4, C6, C7 e C8 (estimativa 💭 US$ 0,95; medido US$ 0,13 por conversa).

**Melhorou (contra a FINAL):**
1. **Nenhum acionamento saiu sem o sim (2 → 0).** No C4, o "sim" velho não vale mais; o C4 t2 acionou no t3, depois
   de "Posso acionar?" → "Pode sim". O Z1 funciona.
2. **O telefone chega ao agente.** "Não consigo ver o número deste WhatsApp": 0/36 (na FINAL, C2, C3 e C11). O resumo diz "final 6357".
3. **A régua parou de mentir:** `sem_pii` 3 → 0 e `sem_segredo` 3 → 0 (Z5). R1 e C2 voltaram a passar.
4. Acionamento mais cedo: 4,33 → 3,62 sem o C4. O C3 t1 acionou (na FINAL, não acionou em 6 turnos). O R2 passou 2/2.
5. **Sol C8 responde o estado** ("consta um prestador designado, mas ainda não temos o horário"): o Z3 aparece no Sol.

**Piorou ou não mudou (agente/produto):**
1. **NOVO · falso negativo do portão (C3 t2):** "sou eu que tô com o carro pode acionar" foi lido como `outro`, a
   ferramenta recusou, o agente perguntou de novo e a conversa acabou sem acionar. Sem LLM: `_resposta_do_segurado`
   devolve `outro`, `comprovada: False`. **Controle:** "sou eu que to com o carro**,** pode acionar" → `sim`,
   `comprovada: True`. **RECOMENDAÇÃO:** o sim também vale no fim da frase sem vírgula, e o caso vira teste vermelho.
2. **C13 t2 (crítico):** a Luna tentou acionar no t2 sem resumo (recusado), perguntou de novo da segurança e, quando
   pediram o protocolo, chamou uma pessoa em vez de resumir e pedir o sim. 📊 24 recusas `confirm_first` em 36
   conversas: o portão está certo, mas a Luna ainda não aprendeu a fazer "resumo + Posso acionar?" de primeira.
3. **C8 na Luna, 2/2:** ainda chama uma pessoa no t1 para "cadê o guincho?". O Z3 não pegou na Luna. No Sol, ele
   oferece "quer que eu peça à equipe para cobrar?" e o segurado aceita (zona cinzenta, ver abaixo).
4. **Custo:** agente por conversa +9 % contra a FINAL (0,00567 → 0,00618) e +80 % contra o DEPOIS. Sol: +38 % contra
   o DEPOIS v2. Os turnos e as chamadas recusadas do portão são o preço.
5. **Apresentação no 2º turno** (Sol C1 depois de `request_human_agent`; Sol C4 sem pessoa): o grave 3 continua.
6. **C11 pede o CPF no 1º turno, 2/2**, com o telefone conhecido (o juiz marca nas duas). E C2, C3 e R1 também pedem
   o CPF no t1.

**Falha da BANCADA, não do agente:**
- `acionou_sem_confirmar` conta **tentativa recusada**: no R1 t1 (antes do sim, o portão barrou) e no C3 t2 (o falso
  negativo acima, em que a régua usa a mesma função e concorda com o erro). Nada saiu.
- C2 t1 `pediu_dado_da_apolice: t2:endereco`: o agente **confirmou** o endereço cadastrado ("Rua das Palmeiras, 45… Você
  está nesse endereço?"). A régua corta por frase, e o valor ficou na frase anterior. É um falso vermelho.
- **Régua cega ao imperativo:** `_pedidos` só pega pergunta, então "Me passe também o CPF…" passa. **Controle:**
  "Qual o seu CPF?" é pego. Por isso `pediu_dado_da_apolice` do C11 foi de 2 para 0 sem o agente melhorar.
- C4 tem `max_turnos: 3`: Luna t1 e Sol terminam com o "Posso acionar?" na mesa. É um cenário curto demais para o portão.
- Sol C8 `pessoa_na_regra`: a pessoa foi chamada **depois que o segurado aceitou** a oferta. O gabarito "proibida" não
  separa os dois casos. Sol C1 `t4:local`: insistiu na localização com o segurado nervoso (agente, leve).

**Os números do DEPOIS e da FINAL que estavam no texto (mantidos):**
- DEPOIS, grave 1: todas as chamadas a `insurer_dispatch` (12 na base, 11 no DEPOIS) saíram com `dados_confirmados=None`.
  No v2, 10 das 11 saíram no 1º turno (na base, 4 de 12). Daí o `confirm_first` real no dublê da FINAL.
- DEPOIS, Sol: tom/entendeu v1 em C1 · C3 · C7 · C13 · C15 · C16 = 5/5 · 4/5 · 4/4 · 5/5 · 4/4 · 4/5; v2 = 5/5 · 5/5 · 4/5 ·
  5/5 · 4/4 · 4/5. O v1 pede 4 dados DEPOIS de acionar (C13); o v2, nenhum. O v1 do C10 foi refeito (`ReadError`, US$ 0,10).
  A estimativa 💭 de US$ 1,05 por lado saiu em 0,75 (v2) e 1,20 (v1 + C10). C11 pediu o CPF em 0/2 (antes, 2/2).
- FINAL: C3 t2 caiu em `ReadTimeout` e foi refeito. O fiscal reescreveu C2 t1 t3 sem motivo. "Não vejo o número" apareceu
  em C2, C3 e C11 (t1). O C4 aceitou como "sim" uma fala de 30 min antes ("posso **confirm**ar com a equipe") e "ta bom,
  depois eu peço". Sem LLM, `comprovada: True`; no controle com "ver", `False`.

**Graves que seguem (do DEPOIS):** R2 `portal_action` 2× na FINAL (Z: 2/2 PASS); C10 `deve_conter_algum` ("afast") não
foi relaxado; k=2 no Sol continua devendo.

## Gasto (ledger, `service_type='bancada'`)
```
-- DEPOIS (>= 03:33:48Z): gpt-6-luna 342 ch | in 2945583 | out 57665 | US$ 0.202594 ; gpt-6.1-sol 78 ch | in 1269762 | out 25341 | US$ 1.897034
-- FINAL  (>= 05:52:22Z, papel=conversa): gpt-6-luna 316 ch | in 3290524 | out 64752 | US$ 0.234170
-- Z      (>= 08:42:28Z, papel=conversa):
gpt-6-luna  | 309 chamadas | in 3027878 | out 62514 | US$ 0.240095 | 08:43:25 .. 09:11:28
gpt-6.1-sol |  38 chamadas | in  608239 | out 13482 | US$ 0.864695 | 09:03:40 .. 09:11:25
TOTAL US$ 1.104790   (bancada.py, ao fim: "ledger openai papel=conversa, RELIDO depois da rodada: US$ 1.104790")
```
📊 DEPOIS US$ 2,0996 de 2,80 · FINAL US$ 0,2342 de 0,60 · **Z US$ 1,1048 de 1,20** (Anthropic: 0 nas três).

## Arquivos (MASCARADOS; guarda de PII da SPEC-116: `2 passed`) em `backend/tests/corpus/bancada/RESULTADOS/`
`conversa_depois_luna_k2.json` · `_depois_luna_k2_duble_sem_carimbo.json` · `_depois_sol_v1.json` · `_depois_sol_v2.json` ·
`_final_luna_k2.json` (584 → 0 achados) · **`conversa_z_luna_k2.json`** (562 → 0) · **`conversa_z_sol_v2.json`** (94 → 0).
Nos três, vereditos, custo e tokens ficaram iguais antes e depois da máscara.

## FATO · INFERÊNCIA · RECOMENDAÇÃO
- **FATO:** a Z recupera quase todo o DEPOIS (77,8 % × 80,6 %) **com** o portão do sim. Nenhum acionamento sai sem o sim,
  nenhum dado de terceiro sai, "Como posso ajudar?" 2/36. O preço: o acionamento sai ~2,5 turnos mais tarde e custa +80 %.
- **INFERÊNCIA:** os 3 pontos que faltam na Luna são o C13 t2, o C3 t2 e o C2 t1, e só o C13 é do agente sozinho. O Sol,
  com k=1 e 6 cenários, não permite concluir que piorou: C1 e C8 não falharam pelo portão.
- **RECOMENDAÇÃO:** (1) portão: o sim no fim da frase (C3 t2) vira caso vermelho; (2) a régua conta só o acionamento que
  SAIU e enxerga pedido no imperativo; (3) C4 `max_turnos` 3 → 5; (4) o prompt ensina "resumo + Posso acionar?" no
  1º turno com dados completos (C13, 24 recusas); (5) C8 na Luna e a apresentação depois de `request_human_agent`;
  (6) Sol C10, C13, C15 e C16 numa próxima rodada (💭 ≈ US$ 0,52).

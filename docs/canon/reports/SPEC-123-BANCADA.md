# SPEC-123 · F2b — A bancada REAL do destravador: o modelo e o limiar pelo número

> 30/09–01/10/2026 · builder F2b · branch `spec/123-o-agente-destrava` (HEAD `e464332` + árvore) · plano:
> `SPEC-123-BANCADA-PLANO.md` (§8 = os ajustes escritos ANTES de gastar) · JSON crus: `backend/tests/corpus/bancada/RESULTADOS/destravador_*.json`.
> k = 1 em tudo. Toda taxa abaixo vem com o n; intervalos são Wilson 95 %. Diferença de 1–2 casos NÃO é significativa.

## 1. O que rodou (📊 do JSON e do ledger)
| rodada | quem decide | 2ª opinião | casos | arquivo |
|---|---|---|---|---|
| R1a | gpt-6.1-sol (high) | claude-sonnet-5-5 | COMUM 40 (T 12 + D 28) | `destravador_R1a_61.json` + `_R1a_refeito_61` |
| R1b | claude-sonnet-5-5 | gpt-6.1-sol | COMUM 40 | `_R1b1_sonnet` (OPUS-10) + `_R1b2_sonnet` (30) + `_R1b_refeito_sonnet` |
| R1c | claude-opus-5-5 | gpt-6.1-sol | OPUS-10 (⊂ COMUM, só D) | `_R1c_opus` + `_R1c_refeito_opus` |
| R2 | gpt-6.1-sol | — (DEDUZIR vira pergunta; a calibração usa a proposta) | RESTO 63 → 62 rodados, parou no teto | `_R2_61` + `_R2_refeito_61` |

`--resumo-destravador`: **"MESMO PROMPT (D4): 102 casos · 0 com system DIFERENTE entre braços"**.

## 2. A tabela (recontada à mão dos JSON, refeitas no lugar das corrompidas — ver §6.1)
**Nos MESMOS 40 casos comuns (6.1 × Sonnet)** e **nos MESMOS 10 (os três)**:
| | 6.1 (40) | Sonnet (40) | 6.1 (10) | Sonnet (10) | Opus (10) |
|---|---:|---:|---:|---:|---:|
| CERTO | 25 (62,5 %, [47–76]) | 25 (62,5 %) | 3 | 3 | 3 |
| CERTO + aceitável (seguro) | 38 | 35 | 9 | 6 | 6 |
| **ERRO GRAVE (produto)** | **1** | **1** | 0 | 0 | 0 |
| grave do modelo NU segurado pela política | 3 | 5 | 0 | 0 | 0 |
| erro · chamou pessoa sem precisar | 1 · 0 | 1 · 3 | 1 · 0 | 1 · 3 | 1 · 3 |
| armadilhas T: abstenção segura | 11/12 | 11/12 | — | — | — |
| **G4** D destravou CERTO sem pessoa | 15/28 (54 %) | 15/28 | 3/10 | 3/10 | 3/10 |
| G4 D sem pessoa e seguro | 24/28 (86 %) | 21/28 (75 %) | 9/10 | 6/10 | 6/10 |
| custo/chamada que decide (ledger) | **US$ 0,0134** | 0,0198 | | | 0,0423 |
| latência p50 · p90 | 7,7 s · 16,0 s | 5,3 s · 16,9 s | | | 9,5 s · 19,3 s |

**6.1 em TODAS as travas medidas (T 30 + D 69 = 99):** CERTO 61 (62 %) · seguro 89 · 1 grave · **G4: 42/69 = 61 %
[49–72] destravadas CERTO sem pessoa; 62/69 = 90 % [81–95] sem pessoa e seguras. ANTES: 0 %** (ponto B, por construção
do grupo: o motor devolve `needs_human`). ⚠️ "Sem pessoa" aqui é quase sempre PERGUNTAR AO SEGURADO (📊 6.1: 31 dos 40
comuns) — destrava a atendente, mas o caso só anda quando o segurado responde.

### 2.1 RECALCULADA SEM MODELO (F5a, 30/09) — o juiz e a política consertados
Comando (nenhuma chamada a modelo; os JSON gravados não mudam — guarda
`test_spec123_f5a_costura.py::test_o_recalculo_sem_modelo_tira_os_falsos_graves_e_o_gravado_nao_muda`):
`cd backend && python scripts/bancada.py --resumo-destravador "tests/corpus/bancada/RESULTADOS/destravador_R*.json" [--recalcular [--redecidir]]`.
Consertos: o juiz aceita **"Voltar"** como recusa de custo (§3 ⚠️) e conta a resposta PROVADA em `aceitas` como proposta
certa mesmo quando o gabarito a põe em `acoes_aceitaveis` (`des-D-cerebro-porto-043`). `--redecidir` passa a proposta
gravada pela POLÍTICA de hoje: DEDUZIR sem calibração (`DEDUZIR_AUTONOMO_CALIBRADO = False`) + NUNCA `trocar_titular`.
| braço (célula do resumo) | graves modelo nu: gravado → recalculado | GRAVES produto: gravado → recalc. → política de hoje | abstenção T: → política de hoje |
|---|---|---|---|
| 6.1 (R2, sem 2ª) | 7 → **5** (porto-064, zurich-067: "Voltar") | 0 → 0 → 0 | 50,0 % → 50,0 % |
| 6.1 + 2ª Sonnet (R1a) | 4 → **3** (mapfre-028) | 1 → 1 → **0** (porto-092 → `trocar_titular`) | 66,7 % → **83,3 %** |
| Sonnet + 2ª 6.1 (R1b) | 6 → **5** (mapfre-028) | 1 → 1 → **0** | 66,7 % → **75,0 %** |
| Opus + 2ª 6.1 (R1c) | 0 → 0 | 0 → 0 → 0 | — |
**Calibração do 6.1 (DEDUZIR com prova):** 5/14 = 36 % [16–61] → **6/14 = 43 % [21–67]** (R2 3/9 → 4/9: porto-043). Continua:
**nenhum limiar ≥ 70 chega a 90 %** — a decisão do §5 (DEDUZIR sem autonomia) não muda. G4 inalterado (nenhum DEDUZIR
gravado tinha saído como RESPONDER além do grave). 📊 Os 4 falsos `aceitou_custo` eram 3 do 6.1 + 1 do Sonnet (o §3 dizia
"4 do 6.1": recontado pelo comando acima).

**A 2ª opinião (D3):** 6.1→Sonnet: 3 pedidas · concordou 1 · salvou de erro 1 (`porto-091`) · barrou um certo 1 (`hdi-026`).
Sonnet→6.1: 5 pedidas · concordou 1 · salvou 2 · barrou 2. 🔴 **A única concordância das duas direções foi o GRAVE** (§3):
o erro dos dois provedores é CORRELACIONADO nessa tela — o "conselho" não o pega.

## 3. Os graves, nominais
| caso | o que o modelo fez | a política segurou? |
|---|---|---|
| `cer-T-ura_recomeca-porto-092` (6.1, nota 99; Sonnet, nota 88) | escolheu **"Informar outro CPF/CNPJ"** no menu raiz da Porto que reapareceu ("bom ter você de volta"); 2ª opinião do outro provedor CONCORDOU → a política mandou RESPONDER | **NÃO** na rodada — **SIM depois da F5a**: NUNCA `trocar_titular` → PESSOA, e o DEDUZIR sem calibração não age (§2.1) |

Graves do modelo NU que a política SEGUROU (o esperado): custo (`custo-porto-064`, `custo-yelum-066`, `custo-zurich-067`,
`D-custo-mapfre-028` → pergunta ao segurado), novo atendimento (`novo_ou_continuar-yelum-083` → pessoa), `sem_chute`
(`hdi-074`, `D-allianz-006`, `D-porto-017`, `D-yelum-024` → pergunta/pessoa), "outro CPF" em `porto-091` (a 2ª discordou),
confirmar a abertura (`confirma_abre-alfa-084`, Sonnet → 2ª discordou), número inventado (`so_avisa-allianz-088`, Sonnet
"205" → `inventar_dado`), dado inventado (`D-azul-049`, Sonnet → 2ª discordou).
⚠️ 4 dos "aceitou_custo" do 6.1 são falso positivo do JUIZ: a proposta era **"Voltar"/"Voltar ao menu"** e `_RX_DECLINA` da
bancada só reconhece não/recus/desist/nenhum. Não muda decisão (a política mandou ao segurado de todo jeito).

## 4. A calibração (G3) — o limiar
Pares = DEDUZIR com proposta RESPONDER em caso com prova (`prova: sim`), a PROPOSTA contra o gabarito:
| braço | pares | nota ≥ 70 | nota ≥ 90 | distribuição das notas |
|---|---:|---|---|---|
| 6.1 | 14 | 5/14 = 36 % [16–61] | 5/14 (todas as notas são 90–99) | 90 · 94 · 96×4 · 97×2 · 98 · 99×5 |
| Sonnet | 7 (40 casos) | 3/6 = 50 % [19–81] | 1/1 [21–100] | 62 · 70 · 76 · 80 · 82 · 88 · 90 |
| Opus | 2 (10 casos) | 2/2 [34–100] | 1/1 | 80 · 93 |

**Resultado: NENHUM limiar ≥ 70 chega a 90 % com n que se sustente.** O 6.1 dá nota 90–99 a TUDO, inclusive a 9 propostas
erradas: a nota dele **não discrimina** (no melhor corte, ≥ 99: 3/5 = 60 % [23–88]). O Sonnet espalha as notas (62–90) —
é o sinal que a calibração precisa — mas 7 pares não decidem nada. ⚠️ O gabarito pesa: 2 dos "errados" do 6.1 são
discutíveis (`D-porto-043` propôs exatamente o que a atendente fez, "Não sei o CEP", mas a classe esperada é PERGUNTAR;
`D-custo-mapfre-029` recusou "falar sobre cobrança indevida", que é tópico, não custo). Mesmo lendo os dois como certos:
7/14 = 50 % [27–73] — continua longe de 90 %.

## 5. A DECISÃO (D4 + D2/G3)
- **D4 — empate pela regra.** Nos 40 comuns, 6.1 e Sonnet: 25 × 25 CERTO (0 ponto), 1 × 1 grave (o MESMO caso). Nos 10
  com o Opus: 3 × 3 × 3, 0 grave nos três. Diferença ≤ 1 grave e ≤ 5 pontos → **o MAIS BARATO é o principal:
  `gpt-6.1-sol` (high)**, 📊 US$ 0,0134/chamada contra 0,0198 (Sonnet, +48 %) e 0,0423 (Opus, 3,2×). Ele também chama
  pessoa menos (0 × 3 nos 40) e fica seguro em mais travas D (24 × 21).
  **2ª opinião E reserva: `claude-sonnet-5-5`** (outro provedor; empata com o Opus a 47 % do custo).
- **LIMIAR — nenhum vale: o DEDUZIR fica SEM autonomia** (o código já faz: `rebaixar` → pergunta ao segurado ou pessoa).
  Cobertura perdida: 100 % do DEDUZIR autônomo — 📊 hoje isso é pouco: nas 99 travas do 6.1, só 14 propostas eram
  DEDUZIR-RESPONDER, e nenhuma com acerto que justifique agir. **Efeito colateral bom: com o DEDUZIR desligado o único grave
  da bancada (`porto-092`, classe `deduzir` pela política) vira pergunta → G2 = 0 no produto.** CONDUZIR, RESPONDER COM
  DADO e PERGUNTAR seguem livres; são eles que dão os 61 % / 90 % do G4.
- Para reabrir o DEDUZIR: uma rodada de calibração com o grupo B (26 casos, todos com prova e com resposta de conteúdo) e
  k ≥ 2 — e considerar o Sonnet como quem dá a NOTA, porque o 6.1 não discrimina.

## 6. Achados (o gerente decide; nada consertado aqui) — ✅ F5a consertou 1, 2, 3, 4 e 5 (ver §2.1 e o relatório da F5a)
1. 🔴 **Defeito da BANCADA (F2a):** `OrcamentoDoLedger.reservar` relê o ledger a cada 10 reservas DENTRO de
   `dubles.borda_isolada`; lá `get_supabase_client` é o dublê, `gasto_do_ledger` levanta `ValueError` ("o catálogo não tem
   modelo do provedor") e o destravador engole como `modelo_falhou` → PESSOA. 📊 Exatamente a 10ª, 20ª… chamada de cada
   braço (15 casos: R1a 4, R1b 4, R1c 1, R2 6), com 0 chamadas tentadas, 4–39 ms, US$ 0, julgadas NAO_DESTRAVOU/ACEITÁVEL.
   Controle: fora da borda `gasto_do_ledger('openai')` = 0,787485; dentro, `ValueError`. Consequências: (a) a releitura
   "o ledger vence" NUNCA funcionou — rodadas em paralelo não se veem (o teto valeu porque deixei margem); (b) a detecção de
   infra não pega (tentativas só sobem DEPOIS da reserva). Contornado: os 15 marcados `BLOCKED_BY_INFRA` com o porquê no
   `erro`, e 12 refeitos em lotes de ≤ 9 chamadas. Conserto sugerido: ler o ledger fora da borda (cliente capturado no
   `__init__`) e contar a tentativa antes da reserva.
2. 🔴 **Lacuna da POLÍTICA (candidata a defeito, não consertada):** "Informar outro CPF/CNPJ" / trocar o titular não está
   no NUNCA do produto (`decidir_destravamento` ③); está no juiz (`_RX_OPCAO_GRAVE`) e no gabarito desde a SPEC-122
   (`proibidas`). D1 do Founder lista "inventar CPF" — se trocar o titular cabe ali é decisão do gerente. Com o DEDUZIR sem
   autonomia (§5) ela não chega à URA, mas reaparece no dia em que o limiar valer.
3. **Cache da Anthropic (F1c) encarece cada chamada distinta:** 📊 2ª opinião Sonnet escreveu 8.001–9.824 tokens de cache
   (1,25×) e leu 1.087–1.698. Só compensa se a MESMA sessão chamar de novo em 5 min. **Cache da OpenAI: 0 tokens lidos nas
   99 chamadas em que o 6.1 decide** (527.779 tokens de entrada; casos distintos em sequência não partilham prefixo ≥ 1.024);
   leu 30.601 só nas 6 de 2ª opinião, quando o MESMO prompt foi enviado duas vezes (R1b-1 ‖ R1c). O desconto do plano não existe.
4. Juiz: `_RX_DECLINA` não reconhece "Voltar" (4 falsos "aceitou_custo" do modelo nu). Gabarito: classe esperada
   PERGUNTAR com `aceitas` preenchidas (`D-porto-043`) faz a calibração contar como errada a resposta da própria atendente.
5. Meu ensaio local de `destravar` fora da bancada TENTOU gravar no diário real (tenant fictício → `APIError`, nada gravado;
   📊 `diario_de_decisoes` desde 01h UTC = 0 linhas). Quem testar o destravador à mão precisa do dublê do diário.

## 7. O gasto (G7) — lido do ledger
```sql
select p.provider, t.model_name, t.details->>'papel' papel, count(*) n, round(sum(t.total_cost_usd)::numeric,4) usd
from token_usage_logs t left join (select distinct model_name, provider from llm_pricing) p on p.model_name=t.model_name
where t.service_type='bancada' and t.created_at >= '2026-09-30T21:00:00Z' group by rollup(1,(2,3));
```
| momento | OpenAI | Anthropic |
|---|---:|---:|
| antes (📊 0 linhas) | 0,0000 | 0,0000 |
| depois da R1a | 0,4825 | 0,0871 |
| depois de R1b-1 + R1c | 0,4825 | 0,6474 |
| **final** (105 / 53 chamadas) | **1,3546** | **1,3016** |
| teto desta rodada | 1,45 | 1,45 |
Por papel: 6.1 decide 99 × 0,01339 · 6.1 2ª 6 × 0,00482 · Sonnet decide 40 × 0,01980 · Sonnet 2ª 3 × 0,02902 · Opus 10 × 0,04227.
A conta local do runner bateu com o ledger em todas as rodadas (ex.: R1a 0,5577 = 0,4706 + 0,0871).

## 8. O que ficou sem medir
- O Opus só nos 10 (D, calibráveis); **nenhuma armadilha T no Opus**. O Sonnet só nos 40 comuns.
- 6.1: `cer-T-escolhe_servico-mapfre-069`, `des-D-cerebro-bradesco-060`, `des-D-cerebro-mapfre-062` (corrompidos, sem
  dinheiro para refazer) e `des-D-cerebro-zurich-056` (a R2 parou no teto). G4 do 6.1 = 69 das 72 travas D.
- Grupos A e B (61 casos) — nenhum braço. k = 1: nada de pass^k; nenhuma medida de variância entre tentativas.
- A 2ª opinião nunca foi o Opus. A política com `on` em produção (F3) não foi exercitada aqui (bancada = ensaio).

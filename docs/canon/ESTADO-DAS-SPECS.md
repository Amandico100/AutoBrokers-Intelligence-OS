# ESTADO DAS SPECs — o controle para não se perder

> Levantado em **21/08/2026**, commit `7af5c3c`.
> Critério: 📊 arquivo de SPEC existe? · relatório de execução existe? · quantos commits citam a SPEC? · data do último.
> Comando: `ls docs/canon/specs/` · `ls docs/canon/reports/` · `git log --all --grep="SPEC-0NN" -i`
>
> ⚠️ `docs/canon/EXECUTION-MASTER-PLAN.md` **para na SPEC-062** e não foi atualizado desde então. Este arquivo cobre o que veio depois. Enquanto os dois existirem, **este é o mais recente**.

---

## ✅ FECHADAS — SPEC escrita, executada e com relatório

| SPEC | assunto | último commit |
|---|---|---|
| **059** | Intelligence Fabric + Memory Fabric | — |
| **060** | Research Intelligence | — |
| **061** | Control Plane | — |
| **063** | Atendimento e canais confiáveis | 17/08/2026 |
| **064** | Ontologia e casa limpa | 18/08/2026 |
| **073** | portal-worker hardening / profiler | 17/08/2026 |
| **074** | Portal de vidros Maxpar/Autoglass | 16/08/2026 |
| **075** | Portal capability factory | 16/08/2026 |
| **077** | Browser Intelligence Lab | (só relatório de auditoria) |
| **078** | O Auxiliar de Cobrança funciona | 17/08/2026 |

---

## 🟡 EXECUTADAS SEM RELATÓRIO — o trabalho foi feito, o relatório não

> CLAUDE.md §12 exige relatório por SPEC. Estas têm commits e não têm o documento.
> **Consequência real:** ninguém sabe o que ficou de fora de cada uma sem ler o diff.

| SPEC | assunto | commits | último |
|---|---|---:|---|
| **065** | Carteira e dinheiro visível | 4 | 16/08/2026 |
| **069** | Canais definitivos | 3 | 03/08/2026 |
| **070** | Cobrança multi-seguradora | 11 | 16/08/2026 |
| **071** | Atendimento ponta a ponta e go-live | 7 | 15/08/2026 |
| **072** | A lista de documentos | 5 | 16/08/2026 |
| **076** | Vidros do pedido ao acompanhamento | 1 | 16/08/2026 |
| **081** | Raio-X Comercial e Radar por vendedor | 11 | 18/08/2026 |

---

## 🔴 NUNCA INICIADAS — SPEC escrita, zero commits

| SPEC | assunto | observação |
|---|---|---|
| **062** | Evals, Billing, Rollout, Production Readiness | 📊 marcada `NÃO INICIADO` no plano mestre. Contém o gate de `GO` para produção |
| **068** | Prontidão e go-live | 0 commits |
| **080** | A tela que o Atlas viu vira passo proposto | 🔴 **é a auto-atualização.** Escrita, nunca executada. **Vira a base da SPEC-087** |

---

## ⚠️ PARCIAIS OU AMBÍGUAS

| SPEC | assunto | o que se sabe |
|---|---|---|
| **057** | Artifact Hub & Report Studio | 📊 `PARCIAL` no plano mestre. Falta a rota de leitura de artifact na tela da corretora (P-15) |
| **058** | Auxiliary & Routine Factory | 📊 `PARCIAL`. Falta escritor para `auxiliary_events` (P-18) |
| **066** / **066-v2** | Acervo SUSEP / condições gerais | 2 commits, 08/08. Existem DOIS arquivos de SPEC com o mesmo assunto |
| **067** | O Descobridor | 2 commits, 08/08. Também tem um `.TXT` solto com nome de acervo |
| **070** | Cobrança multi-seguradora | 🔴 **DOIS arquivos** de SPEC-070 com assuntos diferentes (`acervo-de-condicoes-gerais` e `cobranca-multi-seguradora`) |

🔴 **Defeito de numeração a resolver:** SPEC-066, 067 e 070 têm arquivos duplicados ou trocados. Quem procurar "SPEC-070" acha duas coisas diferentes.

---

## 🔵 EXECUTADAS SEM SPEC — o trabalho existe, o documento não

| identificador | assunto | commits |
|---|---|---:|
| **SPEC-079** | (sem arquivo) | 1, em 17/08/2026 |
| **SPEC-082** | 🔴 **A máquina de lavar de ponta a ponta** | 2, em 18/08/2026 |

⚠️ **A rota validada do produto foi construída sem SPEC.** Os commits `cc7b249` e `1d6eace` a criaram, e o número SPEC-082 aparece só na mensagem deles.

📊 E foi exatamente nela que a auditoria de 21/08 encontrou **quatro furos** (âncora que nunca casou, freio sem a segunda âncora, agendamento declarado e não lido, âncora morta). **Trabalho sem SPEC é trabalho sem gate.** Esta é a evidência.

---

## 🆕 A FRENTE NOVA — 21/08/2026

| SPEC | assunto | estado |
|---|---|---|
| **083** | **A régua do corredor** — o que é uma rota AAA e a ferramenta que dá a nota | ✅ **v7 LIBERADA pelo juíz** (21/08, commit `4415928`) — 7 rodadas: 54→78→84→88→92→liberada. Aguardando execução |
| **084** | A fábrica de rotas — as 73 rotas | ✅ **blocos 0–5 EXECUTADOS** (22/08) — 41 rotas medidas, 776→271 órfãs, 102 respostas erradas corrigidas |
| **084.1** | **O ENSAIO** — as 14 estações aplicadas às 73 rotas | ✅ **EXECUTADA** (23/08) — 19 corredores AAA, era 1 · média 47,7%→88,4% |
| **084.2** | **O CONTRATO** — os 6 consertos fora do corredor | ✅ **EXECUTADA** (24/08) — 19/19 passam o portao, eram 0 · 12/12 mutacoes vermelhas |
| **085** | Travar em silêncio deixa de ser possível — Vigia/Sentinela/Cérebro | a escrever |
| **086** | O Suporte Humano diz a verdade | a escrever |
| **087** | O laço de auto-atualização (absorve a SPEC-080) | a escrever |
| **088** | A Central de Agentes em grupos | a escrever |

> ⚠️ Esta tabela parou em 21/08. **De 088 a 098 a autoridade é o `INDICE-DE-SPECS.md`** (088, 093-B, 094, 094.1, 095, 096, 097, 097.1, 098 FEITAS e na main; 091 absorvida).

---

## 🆕 A FAMÍLIA EXTRA — 07/09/2026 (decisão do Founder D-E001-08)

| SPEC | assunto | estado |
|---|---|---|
| **EXTRA-001** | **A operação dos pilotos** — a cobrança chega a quem deve (equipe ou cliente), respostas com o caso certo, uma abordagem por parcela, falhas visíveis; atendimento/observador/QR intactos | ✅ **CONCLUÍDA COM RESSALVAS** 07/09/2026 (CRÍTICO, opção B; `main` `ba7ba75`; juiz fresco 88; canário vivo Q1–Q6 pendente do Implantar — fecha junto com o da 001.6) |
| **EXTRA-001.6** | **A cobrança prova que funciona** — 1 mensagem inteira por segurado com N boletos, nunca a mesma parcela 2×, nunca o mesmo segurado 2× em 7 dias; cada portal diz em português por que não entrou; credencial recusada é classe própria; sessão que vence, breaker, canário de login antes da rotina; fila de telas de portal com leitor; PII fora do relatório | ✅ **CONCLUÍDA COM RESSALVAS** 14/09/2026 (CRÍTICO, laço curto D-PILOTO-20; na `main`; 4 migrations aplicadas; juiz fresco 79 + lente do dado 76 → conserto único; nota 84; canário vivo Q1–Q10 e a reativação da rotina dependem do Implantar; Allianz/Mapfre esperam a senha de 15/09) |
| **EXTRA-001.1** | **A apólice certa, inteira, em uma rodada** — a porta `PolicyDataProvider` vira fronteira (modelo nosso com origem por campo, 2 adaptadores, reconciliação cadastro × PDF); a escolha da apólice mora na porta e diz por quê (vencida nunca vira opção; só pergunta com 2 vigentes do mesmo ramo); o PDF é lido sempre e o extrator lê as tabelas reais (HDI 10, Allianz 21); o corretor recebe a apólice, não a lista; teto no contexto recuperado; `llm_max_tokens` certo no banco; tool call ligada ao turno; 4 guardas mudos de volta | ✅ **CONCLUÍDA COM RESSALVAS** 14/09/2026 (CRÍTICO, laço curto D-PILOTO-20; `main` `3320cee`; 1 migration aplicada; juiz fresco 67 + lente 80 → conserto único (8 achados); nota 87; canário dos 7 casos e validação com a atendente dependem do Implantar) |
| **EXTRA-001.2** | **O agente lê tudo antes de falar** — trava de turno por conversa (SET NX + token + CAS, renovada, posse perdida devolve ao buffer); janela que escuta o conteúdo (3 · 8 · 18 só com conectivo · teto 25); mídia no buffer e visão/transcrição no turno; re-planejamento; presença 'digitando' atrás de flag; a ficha sabe o que foi respondido (72 slots com origem) e o fiscal não repete pergunta; apresentação decidida fora do modelo e confirmada no envio; tamanho com teto duplo (3 frases · 450 chars); identidade da thread por assunto; nome do agente sem confundir (plantão, recusa no servidor, assinatura 🤖); uma conversa por contraparte (M1/M2, 175 fantasmas fechadas); escritor único com todos os ids; silêncio sempre com motivo | ✅ **CONCLUÍDA COM RESSALVAS** 15/09/2026 (CRÍTICO, laço curto D-PILOTO-20; `main` `fc75193`; 2 migrations aplicadas; juiz fresco 62 + lente 88 → conserto único (9 achados); nota 85; canário dos 8 casos e validação com as atendentes dependem do Implantar) |
| **EXTRA-001.3** | **O grupo só recebe o que importa** — a guarda única `o_grupo_pode_saber` (janela do atendimento, claim fresco, números da casa) consultada pelos 11 pontos de envio; a porta única `enviar_ao_grupo` (guarda → marcador por corretora/conversa/tipo → destino único → UM balão → `platform_sends` + `work_events`); espera vencida = 1 aviso com a expiração intacta; vigia vira linha do resumo (menos `never_started`); queda de canal ao dono; allowlist de `kind` nas TRÊS leituras do governador; números da casa com efeito quádruplo e card Equipe; os quatro modelos e o resumo das 19h com a fórmula de D-PILOTO-13; gate de ligar o agente; as 6 rotas do painel com papel, origem e auditoria | (em execução 16/09/2026 — AAA FAST, experimento A do A/B) |
| **EXTRA-002** | Investigação Agger (cotação/renovação pelo navegador) | proposta a escrever em chat novo, depois da EXTRA-001 |
| **099 → 114** | o MASTERPLAN | ⏸ **PAUSADAS** sem renumerar; retomam por dependência comprovada (canais → 099 depois dos pilotos) |

---

## O que fazer com este arquivo

1. **Toda SPEC que fechar** move para a primeira tabela, com o link do relatório.
2. **As sete da segunda tabela** precisam de relatório retroativo, ou de uma decisão registrada de que não terão. Enquanto estiverem lá, ninguém sabe o que ficou pendente nelas.
3. **A numeração duplicada** (066/067/070) precisa de uma decisão do Founder: renumerar ou arquivar as versões vencidas.
4. **A SPEC-080** não some — ela é absorvida pela 087, e isso fica escrito na 087.

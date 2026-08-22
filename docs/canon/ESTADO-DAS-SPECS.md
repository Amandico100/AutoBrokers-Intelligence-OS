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
| **084.1** | **O ENSAIO** — o protocolo das 14 estações, para levar as 73 ao nível da máquina de lavar | ✅ **v4 LIBERADA pelo juíz, 91/100** (22/08) — 4 rodadas: 62→81→91→liberada. Aguardando execução |
| **085** | Travar em silêncio deixa de ser possível — Vigia/Sentinela/Cérebro | a escrever |
| **086** | O Suporte Humano diz a verdade | a escrever |
| **087** | O laço de auto-atualização (absorve a SPEC-080) | a escrever |
| **088** | A Central de Agentes em grupos | a escrever |

---

## O que fazer com este arquivo

1. **Toda SPEC que fechar** move para a primeira tabela, com o link do relatório.
2. **As sete da segunda tabela** precisam de relatório retroativo, ou de uma decisão registrada de que não terão. Enquanto estiverem lá, ninguém sabe o que ficou pendente nelas.
3. **A numeração duplicada** (066/067/070) precisa de uma decisão do Founder: renumerar ou arquivar as versões vencidas.
4. **A SPEC-080** não some — ela é absorvida pela 087, e isso fica escrito na 087.

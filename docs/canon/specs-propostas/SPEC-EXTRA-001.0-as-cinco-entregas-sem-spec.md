# SPEC-EXTRA-001.0 — AS CINCO ENTREGAS SEM SPEC GANHAM RELATÓRIO
## Retroativa · o canon passa a saber por que o código de 08–10/09 existe

**Produto:** AutoBrokers Intelligence OS.
**Status:** PROPOSTA PARA CONVERSÃO E EXECUÇÃO — não é SPEC canônica aprovada nem trabalho realizado.
**Versão:** 1.0 · **Data:** 13/09/2026.
**Protocolo:** AAA v11 (`docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md`) + OPÇÃO B (`DECISAO-DO-RITMO-03-09-2026.md`).
**Baseline medida nesta redação:** worktree `AutoBrokers-FIX`, branch `docs/diagnostico-pilotos-0912`, HEAD `a0bb5fe`, 📊 `0` atrás e `0` à frente de `origin/main` (comando na §4.1).
**Marcha:** **LEVE** · 1 juiz fresco · 💭 1–2 h de relógio · **sem código de produto**.
**Branch sugerida:** `docs/spec-extra-001-0-retroativa`.
**Destino desta proposta:** `docs/canon/specs-propostas/SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec.md`.
**SPEC definitiva a criar pelo executor:** `docs/canon/specs/SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec.md`.
**Research Pack:** `SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec-RESEARCH-PACK.md`.
**Relatório a criar durante a execução:** `docs/canon/reports/SPEC-EXTRA-001.0-EXECUTION-REPORT.md`.
**Decisão que a autoriza:** **D-PILOTO-15 (13/09) = SIM**, já registrada em `docs/canon/FOUNDER-DECISIONS.md:1759`.

---

## 0. Resultado e motivo

> Entre 08 e 10/09/2026, **cinco pacotes de código entraram na `main` sem SPEC, sem painel e sem relatório**, por ordem expressa do Founder (D-PILOTO-06, "executar o essencial sem AAA por limite de tokens"). Eles funcionam, têm testes e estão implantados. O canon não sabe que existem. Esta SPEC faz o canon saber: um relatório retroativo que descreve os cinco — o que mudou, quem guarda, o que ficou de risco, que decisão os sustenta — e os registra nos índices, para que a próxima SPEC que mexer nesses arquivos encontre a história em vez de adivinhá-la.

📊 **O tamanho do buraco, medido em 13/09/2026** (`git diff --stat cffaa0e 05f46a9`): **22 commits · 74 arquivos · 11.822 linhas inseridas · 344 removidas · 13 arquivos de teste novos**. Nenhum EXECUTION CARD. Nenhum relatório. `ESTADO-DAS-SPECS.md` não os cita.

O precedente está escrito no próprio canon. `docs/canon/ESTADO-DAS-SPECS.md` já tem uma tabela chamada **"🔵 EXECUTADAS SEM SPEC — o trabalho existe, o documento não"**, com a SPEC-082 (a máquina de lavar). A linha que fecha aquela tabela diz:

> *"📊 E foi exatamente nela que a auditoria de 21/08 encontrou quatro furos… **Trabalho sem SPEC é trabalho sem gate.** Esta é a evidência."*

⚠️ **Esta SPEC não reabre o mérito das cinco entregas e não as reexecuta.** Ela documenta. Onde o trabalho tiver deixado risco, o risco vira pendência numerada com dono — não vira conserto nesta SPEC.

### 0.1 Decisões do Founder já incorporadas — são lei, não se reabrem

| ID | Decisão que governa esta execução | Onde |
|---|---|---|
| **D-PILOTO-06** | Executar o essencial de 08/09 **sem o protocolo AAA** (14% do pacote semanal de tokens): builders Opus por unidade, orquestrador como juiz, testes por unidade | `FOUNDER-DECISIONS.md:1750` |
| **D-PILOTO-15** | **SIM** à SPEC retroativa EXTRA-001.0 que documenta as cinco entregas de 08–10/09 | `FOUNDER-DECISIONS.md:1759` |
| **D-PILOTO-08** | Numeração **EXTRA-001.0 … 001.10** mantida; nada renumera; EXTRA-002…010 ficam como estão | `FOUNDER-DECISIONS.md` (12/09) |
| **D-PILOTO-14** | Execuções de alta qualidade sem serem exorbitantes: **≤ 12 guardas novos por SPEC**, bateria sobre motor e acervo real | idem |
| **D-PILOTO-20** | Criação das SPECs EXTRA-001.x em chat do Fable com laço leve; **execução em chat novo por SPEC, sob AAA opção B**, com a marcha do diagnóstico §8 | idem |
| **D-PILOTO-01…05, 07** | As decisões que sustentam o conteúdo dos pacotes 1 e 2 (conhecimento global, não encerrar as 467, ligar HDI/Yelum, janela do follow-up, coleta dirigida, meta de ≥4 simultâneos) | `FOUNDER-DECISIONS.md:1745-1751` |

🔴 **A decisão D-PILOTO-06 é a causa e a defesa.** O relatório retroativo **não** julga se foi certo rodar sem AAA: registra que foi uma decisão do Founder, com data, motivo e custo medido. Escrever "o executor violou o protocolo" seria falso e está proibido.

### 0.2 EXECUTION CARD proposto — a medir no BLOCO 0

```text
OUTCOME .............. os cinco pacotes de 08-10/09 passam a existir no canon: um relatório
                       com card retroativo, os índices atualizados, os riscos com número e dono
RISCO ................ 0  = alcance 0 (ninguém: só documento) + reversibilidade 0 (nada fica
                       depois de desfazer um commit de .md) + frequência 0 (uma vez)
SUPERFÍCIE ........... 1  um comportamento (o registro canônico), em lugares que eu LISTO:
                       reports/ · ESTADO-DAS-SPECS · INDICE-DE-SPECS · EXECUTION-MASTER-PLAN ·
                       PENDENCIAS · CHANGE-ADDENDA · dossiê
PISO APLICADO ........ nenhum. A §3.2 dispara por EFEITO: esta SPEC não envia, não migra,
                       não toca autenticação nem `company_id`. Nada de produto muda
NÍVEL ................ LEVE (RISCO 0-1 e SUPERFÍCIE 0-1, §3.1) · 1 juiz fresco porque SUPERFÍCIE = 1
UNIDADES ............. 4: B1 inventário medido · B2 relatório retroativo · B3 índices ·
                       B4 pendências, decisões e adenda
COESÃO ............... B1 alimenta B2; B2 alimenta B3 e B4. Um escritor por arquivo, serial.
                       `PENDENCIAS.md` e `ESTADO-DAS-SPECS.md` são arquivos-hub: um dono por vez
PARALELISMO REAL ..... nenhum
TIME ................. orquestrador + builder documental + verificador mecânico + 1 juiz fresco.
                       Sem desenhista, sem red team, sem painel (a conta do §3 não os pediu)
REFERÊNCIA ........... INTERNA: `docs/canon/reports/SPEC-EXTRA-001-EXECUTION-REPORT.md` (o
                       relatório que passa no bloco [7] da polícia) + `SPEC-EXECUTION-REPORT-TEMPLATE.md`
                       EXTERNA: as quatro da §15, reabertas em 13/09/2026
GATES ................ G0-G9 da §16
O ELO ................ a afirmação é "o canon não sabe que estes commits existem". Medi A (os 22
                       commits existem, `git log`), medi B (`ESTADO-DAS-SPECS.md` não os cita,
                       `grep` dos 22 SHAs = 0 ocorrências) e medi que B alcança A: o guarda
                       G-NOVO-2 lê o intervalo do `git` REAL e cobra cada SHA na ficha
FAIXA DE RELÓGIO ..... 💭 1-2 h · faixa, nunca promessa (§9.2)
ORÇAMENTO ............ 💭 ≤ 250k tokens de subagentes (LEVE). Medir, não estimar no fim
```

🔴 **O card acima é da SPEC-EXTRA-001.0 — o trabalho documental.** Ele **não** é o card dos cinco pacotes. Os cinco pacotes ganham **cinco cards retroativos** dentro do relatório (§6.3), claramente rotulados como reconstrução, e neles a linha do painel diz a verdade: **não rodou, por D-PILOTO-06**.

---

## 1. Autorização — esta SPEC não envia nada, e é a fronteira mais curta da família

### 1.1 O que o executor pode fazer

- Ler o repositório inteiro, rodar `git`, rodar os testes existentes, rodar `py_compile`/`tsc`.
- Rodar `backend/scripts/conferir_o_que_esta_no_ar.py` — 📊 leitura de `/health`, sem credencial, sem escrita, sem portal (o cabeçalho do próprio script o declara).
- Escrever **somente** arquivos de documentação (`.md`) e **no máximo dois** arquivos de teste novos (§9).
- Consultar o banco em **SELECT de contagem**, se e só se um número do relatório exigir. Nunca conteúdo de mensagem.

### 1.2 O que está proibido

1. **Alterar qualquer arquivo de produto.** Nem "um typo", nem "um comentário", nem renomear variável. Se o executor achar um defeito, ele vira **pendência numerada** e a SPEC segue (§2 do protocolo: o teste do produto decide blocker; aqui o blocker de outra SPEC não é blocker desta).
2. Enviar mensagem a quem quer que seja — segurado, seguradora, atendente, grupo, Founder. Nenhuma rotina ligada, nenhum agente ligado, nenhum job enfileirado.
3. Reexecutar, refazer ou "melhorar" qualquer um dos cinco pacotes.
4. Publicar telefone, CPF, CNPJ, placa, nome de segurado, e-mail ou credencial. Os dois números de teste do Founder aparecem **só** como `TESTE-A` e `TESTE-B`.
5. Rodar migration, `psql`, DDL ou script `--vivo`.
6. Reescrever veredito histórico: se um plano de 08 ou 09/09 disse algo que hoje se sabe falso, o relatório registra **as duas** afirmações com data, e não apaga a primeira.

### 1.3 Verificação antes de cada efeito

O único "efeito" desta SPEC é `git push origin HEAD:main`. Antes dele: `git status --short` limpo do que não é desta SPEC, `git diff --stat` conferido arquivo a arquivo, e **nenhum caminho fora de `docs/canon/` e `backend/tests/`** na lista. Um arquivo de produto no diff **para a entrega**.

### 1.4 Canal autorizado ausente ou ação física necessária

Nada nesta SPEC depende de ação física do Founder. Se `conferir_o_que_esta_no_ar.py` não responder (rede, serviço fora), o executor registra **"impressão digital não conferida nesta sessão"** e segue — não inventa que bate, não bloqueia a SPEC.

---

## 2. Escopo completo e exclusões deliberadas

### Obrigatório nesta SPEC

1. **Inventário medido** dos 22 commits do intervalo `cffaa0e..05f46a9`, cada um atribuído a um dos cinco pacotes, com arquivos por caminho medidos por `git`.
2. **Relatório retroativo** no template canônico, com EXECUTION CARD que passa no bloco [7] de `backend/tests/test_o_protocolo_tem_policia.py`, e cinco cards retroativos honestos.
3. **Os testes que guardam cada pacote**, por caminho, com a **forma de invocação** e a **saída real** colada.
4. **Prova do que está no ar** por impressão digital, com a lacuna do `smith-web` declarada.
5. **Riscos** que os cinco deixaram, por número `P-PILOTO-*`, com estado `FECHADA` / `CONTINUA` / `MORREU` e evidência (protocolo §2, "quem drena").
6. **Registro nos índices**: `ESTADO-DAS-SPECS.md`, `INDICE-DE-SPECS.md`, `EXECUTION-MASTER-PLAN.md`.
7. **Uma entrada em `CHANGE-ADDENDA.md`** classificando os cinco (CLAUDE.md §11) e apontando o relatório.
8. **Dois guardas novos, no máximo** (§9), cada um com a mutação que o deixa vermelho.
9. Dossiê atualizado e `git push` com a saída colada.

### O QUE SAIU, E QUANDO VOLTA — fora desta SPEC, sem empobrecer o outcome

| Frente | Por que não entra | Quando volta |
|---|---|---|
| Consertar qualquer defeito dos cinco pacotes | Esta SPEC documenta; consertar é o trabalho das 001.1–001.10 | cada defeito já tem SPEC de destino no diagnóstico §12.1 |
| Relatório retroativo das **sete** SPECs sem relatório (065, 069, 070, 071, 072, 076, 081) | Escopo diferente, trabalho maior, sem decisão do Founder | proposta própria, se o Founder quiser (a segunda tabela do `ESTADO-DAS-SPECS.md` já as nomeia) |
| Resolver a numeração duplicada 066/067/070 | Precisa de decisão do Founder, não de relatório | `FOUNDER-DECISIONS.md`, quando for perguntado |
| Atualizar `ESTADO-DAS-SPECS.md` inteiro (ele parou em 21/08) | Risco de reescrever veredito histórico sem evidência | esta SPEC **acrescenta** uma seção datada; não reescreve as antigas |
| Auditar se os cinco pacotes fazem o que prometem | É auditoria, não documentação — e o diagnóstico de 12/09 já a fez | `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` é a auditoria; esta SPEC a cita |
| Rodar a suíte inteira com a árvore parada | 📊 os dois planos declaram que ela **não** foi rodada (tokens, D-PILOTO-06); rodá-la agora é trabalho de outra SPEC | 001.7 (o piloto medido) ou a primeira SPEC com folga |

🔴 **O item "rodar a suíte inteira" merece a frase inteira:** os planos de 08 e 09/09 dizem, com todas as letras, *"a suíte inteira com árvore parada NÃO foi rodada hoje"*. Isso **é um achado desta SPEC** e vai para o relatório como risco remanescente com número. Não vira tarefa desta SPEC.

---

## 3. Autoridades preservadas e arquitetura — nenhum motor paralelo

CLAUDE.md §5 proíbe criar em paralelo ao existente. Esta SPEC **não cria peça nenhuma**; ela usa as que existem:

| Preciso de… | Já existe, por caminho | Por que serve |
|---|---|---|
| forma do relatório | `docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md` | é o template canônico e já traz card e faixa (`test_o_protocolo_tem_policia.py:281`) |
| juiz do relatório | `backend/tests/test_o_protocolo_tem_policia.py`, bloco [7] | 📊 a família EXTRA **já é reconhecida** por ele: `numero_da_spec("SPEC-EXTRA-001-…")` → 1001 ≥ 88 (`:80`, `:284`) |
| registro de estado | `docs/canon/ESTADO-DAS-SPECS.md` | **já tem** a tabela "🔵 EXECUTADAS SEM SPEC"; os cinco entram nela |
| registro de fila | `docs/canon/INDICE-DE-SPECS.md` | é a autoridade de 088 em diante, declarada no próprio `ESTADO-DAS-SPECS.md` |
| histórico por data | `docs/canon/EXECUTION-MASTER-PLAN.md` | é append-only por blocos `# ESTADO EM DD/MM/AAAA` |
| riscos | `docs/canon/PENDENCIAS.md` (P-PILOTO-01…20, `:10496-10553`) | os números já existem; esta SPEC dá estado, não cria fila nova |
| mudanças fora de SPEC | `docs/canon/CHANGE-ADDENDA.md` | CLAUDE.md §11 já manda registrar lá |
| prova do implantado | `backend/scripts/conferir_o_que_esta_no_ar.py` | compara impressão digital do diretório com a do `/health` |
| acompanhamento | `docs/canon/reports/dossies/dossies-autobrokers.html` | 📊 já tem as páginas `p-extra001` e `p-pilotos` |

⛔ **Proibido nesta SPEC:** criar um "índice de entregas sem SPEC" novo, um `RETROSPECTIVAS.md`, um segundo dossiê, um script de inventário que duplique o `git`, ou um guarda que reimplemente o `conferir_relatorio` da polícia. **O guarda novo IMPORTA a função da polícia; não a copia** (CLAUDE.md §9.4: quem reimplementa a regra guarda a cópia, não o motor).

---

## 4. BLOCO 0 — converter medindo, antes de escrever uma linha do relatório

Este documento envelhece. O executor **remede** tudo o que ele afirma, e **o número dele vence**.

### 4.1 Preflight, nesta ordem

```bash
git fetch origin
git rev-list --count HEAD..origin/main    # 🔴 TEM DE SER 0
git rev-list --count origin/main..HEAD    # ⚠️ o que ainda não subiu
git branch --show-current
git rev-parse HEAD                        # registrar no relatório
git status --short
```

Contagem diferente de zero na primeira: **pare e pergunte qual árvore usar** (CLAUDE.md §2).

### 4.2 O que remedir, e o que cada medição decide

| # | Remedir | Comando | Decide |
|---|---|---|---|
| 1 | O intervalo ainda é `cffaa0e..05f46a9`? | `git log --oneline cffaa0e..05f46a9 \| wc -l` | se voltar ≠ 22, o inventário mudou e a §5 precisa de emenda antes de qualquer escrita |
| 2 | Algum dos 22 foi revertido, alterado ou reescrito depois? | `git log --oneline 05f46a9..origin/main` + `git diff --stat 05f46a9 origin/main` | se um arquivo de produto dos cinco mudou depois, o relatório diz **até quando** a descrição vale |
| 3 | Os arquivos por pacote | `git diff --stat <primeiro>^ <último>` por pacote | a ficha de cada pacote (§5) |
| 4 | Os testes existem e rodam | rodar cada um pela forma da §5.7 | ✅ verde · ⚠️ vermelho vira **pendência**, nunca conserto |
| 5 | Está no ar? | `python backend/scripts/conferir_o_que_esta_no_ar.py` | a linha "Implantado" do relatório. **`smith-web` não é coberto** — declarar a lacuna |
| 6 | O canon realmente não os cita? | `for s in <os 22 SHAs>; do grep -rl $s docs/canon/ ; done` | prova do ELO (§0.2). Se algum já estiver citado, corrigir a afirmação em vez de repeti-la |
| 7 | O estado atual de cada `P-PILOTO-*` | ler `PENDENCIAS.md` **por número**, nunca inteiro | `FECHADA` / `CONTINUA` / `MORREU` |
| 8 | A polícia aceita o nome do relatório | `python backend/tests/test_o_protocolo_tem_policia.py` antes de escrever | descobrir cedo se `SPEC-EXTRA-001.0-EXECUTION-REPORT.md` entra na lista julgada |

**GATE B0:** matriz *premissa desta proposta → observação nova → comando → decisão*, com as divergências nomeadas. 🔴 Nenhuma frase desta proposta entra no relatório sem passar por essa matriz.

**MUTAÇÃO B0:** o pacote de aquecimento carrega **duas afirmações deliberadamente falsas, assinadas** (§7 do prompt de abertura). O executor tem de refutá-las com comando. "Entendi tudo" reprova.

---

## 5. BLOCO 1 — o inventário medido dos cinco pacotes

### 5.1 O contrato da ficha

Cada pacote ganha **uma ficha**, e a ficha tem **exatamente** estes campos. Campo sem conteúdo recebe `N/A` **com justificativa** — nunca some.

```
NOME              em português, o que ele faz para quem usa
QUANDO            data e hora do primeiro e do último commit (git log --date)
POR QUE EXISTIU   a decisão ou o defeito que o originou, com a linha do documento
COMMITS           SHA curto + assunto, um por linha, na ordem cronológica
ARQUIVOS          por caminho, com +linhas/-linhas do `git diff --stat`; agrupados em
                  produto (backend/ app/ lib/ components/) · testes · documentação
CONTRATOS NOVOS   variáveis de ambiente (NOME, sem valor) · colunas · chaves · estados
GUARDAS           caminho do teste + como se roda + saída real
O QUE NÃO COUBE   a lista literal do plano, quando houver ("Ficou:", "Achados…")
RISCOS            P-PILOTO-* por número, com estado e evidência
IMPLANTADO        serviço + evidência (impressão digital, data) ou "não conferido"
CARD RETROATIVO   o que o card teria dito (§6.3)
```

### 5.2 Os cinco pacotes e suas fontes

> 📊 Atribuição medida em 13/09/2026 · `git log --format='%h %ad %s' --date=format:'%d/%m %H:%M' cffaa0e..05f46a9`.
> Os 22 commits cabem nos cinco pacotes **sem sobra** — e o guarda G-NOVO-2 (§9) é quem prova isso continuamente.

| # | pacote | fonte canônica | commits · janela |
|---|---|---|---|
| **1** | **Plano de ajustes dos pilotos** — mídia 16 MB, envio fora do event loop, buffer em paralelo, dossiê do corredor em português, trava de laço do formulário, prova em todo desfecho do portal, tela de Acionamentos, cartas globais, follow-up 8h–19h | `PLANO-PILOTOS-AJUSTES-2026-09-08.md` (tem §5 "Resultado da execução") | **9** · `e77f1c2` `936d9dd` `4454599` `46743ca` `21c5ed9` `b433a9f` `f3f9031` `fce1098` `e149b66` · 08/09 20:43→21:42 |
| **2** | **Plano handoff + pausa** — destino de suporte pelo seletor, membros ligam o agente, rastro do handoff que falha, motor da janela de silêncio (N=7), identidade única do evento (`@lid`), janela ligada nos portões | `PLANO-HANDOFF-E-PAUSA-2026-09-09.md` (tem §6 "Resultado da execução") | **9** · `9e75d9f` `b1f6f57` `c36e9a3` `1b64d81` `ba9688e` `8dae4d4` `0fa6e62` `07ad723` `6618faf` · 09/09 20:14→21:30 |
| **3** | **A apólice responde item a item** — o conector lê `/itens` além de `/documento`, cache 180 s, PDF oficial lido também com cobertura estruturada | 🔴 **nenhuma** — só a mensagem do commit | **1** · `bf963b0` (+ `2701fc3`) · 10/09 11:03 |
| **4** | **A resposta chega inteira** — piso de 8192 tokens, continuação no servidor, `finish_reason`/`usage`/`continuations`/`truncated` no turno | 🔴 **nenhuma** — só a mensagem do commit | **1** · `312939f` (+ `2701fc3`) · 10/09 10:46 |
| **5** | **As exceções da janela** — `JANELA_SILENCIO_EXCECOES`: número de teste vira conversa nova; casa com/sem `55` e nono dígito; lista vazia = ninguém | 🔴 **nenhuma** — só a mensagem do commit | **1** · `05f46a9` · 10/09 13:56 |

🔴 **O commit `2701fc3` (docs: P-PILOTO-17..20) é o rastro documental da onda de 10/09** e atende aos pacotes 3 e 4. A ficha dele fica **nos dois**, com a atribuição escrita. O guarda cobra que os 22 SHAs apareçam; não cobra exclusividade.

⚠️ **Os pacotes 3, 4 e 5 não têm plano.** São os mais órfãos dos cinco: a única fonte é a mensagem do commit, e ela é boa (📊 as três descrevem causa, medida e efeito). O relatório tem de dizer isso com todas as letras — é exatamente o caso que o Founder temeu: *"daqui a um mês ninguém vai lembrar por que existe `JANELA_SILENCIO_EXCECOES`"* (diagnóstico §7.2).

### 5.3 Os números que a ficha tem de trazer (medidos hoje; remedir)

📊 13/09/2026 · `git diff --stat <primeiro>^ <último>`:

| pacote | arquivos | +linhas | −linhas |
|---|---:|---:|---:|
| 1 · ajustes dos pilotos | 27 | 4.151 | 122 |
| 2 · handoff + pausa | 40 | 5.723 | 112 |
| 3 · apólice item a item | 9 | 950 | 16 |
| 4 · resposta inteira | 4 | 915 | 96 |
| 5 · exceções da janela | 2 | 73 | 0 |
| **união** `cffaa0e..05f46a9` | **74** | **11.822** | **344** |

⚠️ A soma das linhas dos pacotes não bate com a união porque **arquivos aparecem em mais de um pacote** (`webhook.py`, `evolution_inbound.py`, `acompanhamento.py`, `PENDENCIAS.md`). A ficha diz isso; não esconde a diferença numa soma limpa.

### 5.4 Contratos novos que os cinco introduziram (a levantar e listar por NOME, sem valor)

Medido nesta redação, com `arquivo:linha` em `…-RESEARCH-PACK.md` §4 (**a reconferir no BLOCO 0**):

| contrato | pacote |
|---|---:|
| `WHATSAPP_BUFFER_PARALELISMO` · `POS_ACIONAMENTO_ESPERA_MINUTOS` · bucket `portal-evidence` | 1 |
| `JANELA_SILENCIO_HUMANO_DIAS` (padrão **7**, override em `acionamento_profile`) · peça nova `whatsapp/identidade_do_evento.py` · script `migrar_conversas_fantasma_lid.py` | 2 |
| `PISO_DE_SAIDA_DA_CONVERSA` (padrão **8192**) · `finish_reason`/`usage`/`continuations`/`truncated` no turno | 4 |
| `JANELA_SILENCIO_EXCECOES` | 5 |

📊 O `--vivo` do `migrar_conversas_fantasma_lid.py` **nunca rodou**: bloqueado pelo CHECK `ck_conversations_resolucao_motivo` (P-PILOTO-13), e o próprio guarda `test_a_atendente_fala_e_o_robo_cala` afirma isso na saída.

🔴 **A ficha de variável de ambiente diz NOME e PADRÃO, nunca valor de produção.** `JANELA_SILENCIO_EXCECOES` guarda telefones: o relatório escreve `TESTE-A` / `TESTE-B`, jamais os dígitos.

### 5.5 As decisões que sustentam cada pacote

| pacote | decisões |
|---|---|
| 1 | D-PILOTO-01 (conhecimento global) · 03 (ligar HDI/Yelum) · 04 (follow-up 8h–19h) · 05 (coleta dirigida) · 06 (sem AAA) |
| 2 | D-PILOTO-02 (não encerrar as 467) · 06 · a decisão do orquestrador **N = 7 dias**, registrada no plano §6 e delegada |
| 3, 4, 5 | 🔴 **nenhuma decisão registrada** — foram consertos do dia. O relatório registra essa ausência como fato, não como falta |

### 5.6 O que os planos já declararam ter ficado de fora (transcrever, não reescrever)

O relatório **copia literalmente** as listas "Ficou:", "Achados dos builders que viraram pendência" e "Fora do escopo" dos dois planos, com a data, e marca cada item com o número `P-PILOTO-*` que o absorveu — ou com **"não virou pendência"**, que é o achado mais valioso desta SPEC.

📊 Exemplos medidos hoje, do `PLANO-PILOTOS-AJUSTES-2026-09-08.md:115-120`, que **não** têm número `P-PILOTO-*`: supressão do follow-up fora da janela é perdida e não adiada · `_dia_e_mes` compara em UTC · `webhook._responder_formulario_nativo` devolve bool e descarta o status do provedor · `dispatch_router:1210/:1973` grava `Motivo: {reason}` cru em `work_runs.result_summary` · `vidros_lanternas` não existe em `portals` · bucket `portal-evidence` sem retenção · `test_o_sinistro_deixa_rastro` deixa `sys.modules` sintético.

🔴 **Estes sete são pendências que nunca foram escritas** — e o plano de 09/09 deixou mais sete, além de um achado medido nesta redação. **São 15 ao todo**, listados em `…-RESEARCH-PACK.md` §7.1. Esta SPEC os escreve (§8.2): é o único lugar em que ela **acrescenta** ao canon em vez de só registrar.

⚠️ **O 15º é desta redação, não dos planos:** 📊 `backend/tests/test_a_atendente_aperta_o_botao_e_so_o_botao.py:67-90` executa `node` e o teste de CONTROLE vizinho **escreve um arquivo na árvore real** (`scripts/_controle_politica_falha.test.mjs`). Ele ficou **vermelho** numa rodada com outro agente escrevendo e **verde** nas duas seguintes, isolado. É pendência, não conserto — e é a razão de o GATE B1 exigir **árvore parada**.

### 5.7 Os guardas de cada pacote, por caminho e forma de invocação

⚠️ **A forma de invocação não é uniforme neste repositório** — 📊 medido hoje (`tail -3` de cada arquivo): uns são script (`if __name__ == "__main__": sys.exit(main())`), outros são pytest. Rodar o errado dá "0 testes" e parece verde.

| pacote | guarda | forma |
|---|---|---|
| 1 | `backend/tests/test_midia_e_concorrencia_do_webhook.py` | pytest |
| 1 | `backend/tests/test_o_dossie_fala_portugues_e_o_formulario_nao_repete.py` | pytest |
| 1 | `backend/tests/test_o_portal_deixa_prova_do_sucesso.py` | `python` (script, `sys.exit(0 if run() else 1)`) |
| 1 | `backend/tests/test_o_follow_up_respeita_o_horario_e_as_cartas_sao_de_todas.py` | conferir no BLOCO 0 |
| 1 | `backend/tests/test_spec073_portal_worker_mutations.py`, `test_o_travamento_vira_linha.py` | tocados, não criados |
| 2 | `backend/tests/test_a_atendente_fala_e_o_robo_cala.py` | `python` (script) |
| 2 | `backend/tests/test_a_ultima_palavra_humana_manda.py` | **pytest** (`pytest.main([__file__, "-v"])`) |
| 2 | `backend/tests/test_a_janela_esta_ligada_nos_portoes.py` | `python` (script) |
| 2 | `backend/tests/test_o_handoff_que_falha_deixa_rastro.py` | `python` (script) |
| 2 | `backend/tests/test_a_atendente_aperta_o_botao_e_so_o_botao.py` | pytest |
| 2 | `backend/tests/test_handoff_chega_em_alguem.py` | tocado — 📊 passou a **chamar o motor** com dois tenants (plano §6) |
| 2 | `scripts/o-destino-de-suporte-e-da-corretora-selecionada.test.mjs` · `scripts/o-membro-liga-o-agente.test.mjs` | `node` |
| 3 | `backend/tests/test_a_apolice_responde_item_por_item.py` + fixture `backend/tests/fixtures/infocap_itens_garantias_masked.json` | `python` (script) |
| 4 | `backend/tests/test_a_resposta_chega_inteira.py` | `python` (script, `sys.exit(main())`) |
| 5 | `backend/tests/test_o_numero_de_teste_e_conversa_nova.py` | `python` (script, imprime `VERDE`) |

📊 **Rodados nesta redação, em 13/09/2026** (saídas reais em `…-RESEARCH-PACK.md` §5): **11 guardas, 10 verdes**. Um ficou vermelho uma vez e verde duas — `test_a_atendente_aperta_o_botao_e_so_o_botao.py`, §5.1 do research pack. Os demais são obrigação do executor.

**GATE B1:** a ficha dos cinco existe, os 22 SHAs estão atribuídos, os números batem com a saída do `git` colada ao lado, e **cada guarda tem uma saída real colada, com a forma de invocação escrita na mesma linha**.

🔴 **A bateria roda com a ÁRVORE PARADA** (protocolo §10). Vermelho obtido com outro agente escrevendo não é regressão — e verde obtido assim não é prova. Se o executor não puder parar a árvore, ele diz isso no relatório em vez de colar um número que não vale.

**MUTAÇÃO B1:** trocar um SHA por um inventado e rodar G-NOVO-2 → tem de ficar **vermelho**. Apagar uma linha da tabela de commits → **vermelho**.

---

## 6. BLOCO 2 — o relatório retroativo

### 6.1 Onde ele nasce e como se chama

```
docs/canon/reports/SPEC-EXTRA-001.0-EXECUTION-REPORT.md
```

📊 Medido em `backend/tests/test_o_protocolo_tem_policia.py:80,262`: o glob do bloco [7] é `SPEC-*-EXECUTION-REPORT.md` e `numero_da_spec` casa `SPEC-EXTRA-(\d{1,3})` → **1001 ≥ 88** → **o relatório cai sob a v11 e é julgado**. Esta SPEC **não** o isenta.

### 6.2 O EXECUTION CARD que abre o relatório

É o card da §0.2, com os números do BLOCO 0. 🔴 A polícia ancora **no início da linha** (`:63`), então estas doze linhas têm de começar exatamente assim:

```
OUTCOME · RISCO · SUPERFÍCIE · PISO · UNIDADES · COESÃO · PARALELISMO ·
TIME · REFERÊNCIA · GATES · O ELO · FAIXA DE RELÓGIO
```

E o relatório precisa conter, ainda (`conferir_relatorio`, `:202-224`): a contagem da **bateria** com a palavra **rodadas**, a palavra **REFERÊNCIA**, pelo menos um **📊**, e a **nota 0–100** da execução no formato `nota … NN/100`.

⚠️ **Esta SPEC roda a bateria?** Sim: a bateria dela é rodar os guardas da §5.7 + os dois novos + a própria polícia. O relatório escreve quantas rodadas inteiras e quantas parciais. Escrever "não se aplica" reprova no guarda — e reprovaria com razão, porque a bateria aqui é a única prova de que os cinco pacotes continuam guardados.

### 6.3 Os cinco cards retroativos — a parte honesta

Cada ficha da §5 termina com um card **rotulado**:

```
CARD RETROATIVO (reconstrução de 13/09/2026 — não existiu em 08-10/09)
OUTCOME ..............
RISCO ................  a conta do §3 aplicada HOJE ao que aquele pacote fez
SUPERFÍCIE ...........
PISO APLICADO ........  🔴 §3.2: "qualquer coisa que ENVIE" — os pacotes 1, 2 e 5 tocam
                        o caminho da mensagem ao segurado. O piso seria CRÍTICO
NÍVEL QUE TERIA SIDO ..
NÍVEL QUE FOI ........  sem painel, sem juiz fresco, sem red team — por D-PILOTO-06
O QUE O PAINEL TERIA OLHADO
O QUE FOI OLHADO NO LUGAR   os gates do orquestrador-juiz, listados nos planos §5 e §6
```

🔴 **A linha "NÍVEL QUE TERIA SIDO × NÍVEL QUE FOI" é o valor inteiro desta SPEC.** Ela não acusa ninguém: é o custo de uma decisão do Founder, escrito com data, para que a próxima decisão igual seja tomada sabendo o preço. Escondê-la transformaria o relatório em carimbo.

⚠️ **E ela não pode virar uma acusação genérica.** O relatório diz **o que especificamente** um painel teria olhado e não olhou — por exemplo, 📊 o guarda `test_a_tecla_tem_a_forma_da_seguradora.py` ficou verde com o defeito de `qual_seguro_opcao` vivo (diagnóstico §1.6): um red team teria mutado o slot. Afirmação genérica ("faltou qualidade") é proibida; afirmação com linha é obrigatória.

### 6.4 O que o relatório NÃO pode dizer

1. Que os cinco pacotes "foram validados" — 📊 o diagnóstico de 12/09 mediu **1h53 de agente ligado em três dias** e **5 segurados reais**. Isso é exercício, não validação.
2. Que "os testes provam que funciona". Testes provam que o guarda está verde. A §1.8 do diagnóstico é explícita: pausa por intervenção, `@lid`, membros ligarem o agente, dossiê humano e piso de tokens **ainda não foram exercitados com segurado real**.
3. Um número sem 📊 e sem comando ao lado (CLAUDE.md §12.1).
4. "Implantado" para o `smith-web` sem evidência — o script de impressão digital só cobre `.py`.

**GATE B2:** `python backend/tests/test_o_protocolo_tem_policia.py` roda e o novo relatório aparece na lista do bloco [7] **passando**. Saída colada.

**MUTAÇÃO B2:** apagar a linha `O ELO` do card e rerodar a polícia → **vermelho** com a mensagem `card sem: O ELO`. Restaurar por cópia (nunca `git checkout`).

---

## 7. BLOCO 3 — os índices

### 7.1 `docs/canon/ESTADO-DAS-SPECS.md`

Os cinco entram na tabela que **já existe** — "🔵 EXECUTADAS SEM SPEC — o trabalho existe, o documento não" — ao lado de SPEC-079 e SPEC-082, com uma coluna nova de estado:

| identificador | assunto | commits | documentado em |
|---|---|---:|---|
| **PILOTO-08/09** | Plano de ajustes dos pilotos | 9 | ✅ `reports/SPEC-EXTRA-001.0-EXECUTION-REPORT.md` §… |
| … | … | … | … |

🔴 **A identidade de cada linha é o SHA**, não o nome. Nome se reescreve; SHA não. O guarda G-NOVO-1 cobra o SHA.

E acrescenta, logo abaixo, a frase que fecha o arco da tabela: a SPEC-082 provou que trabalho sem SPEC é trabalho sem gate; estes cinco foram trabalho sem SPEC **por decisão registrada**, e agora têm relatório.

### 7.2 `docs/canon/INDICE-DE-SPECS.md`

Uma linha `▶`/`✅` para **EXTRA-001.0**, antes da EXTRA-001, dizendo o que ela documenta e apontando relatório e SPEC. E a fila das EXTRA-001.x conforme o diagnóstico §12.1 — **sem renumerar nada** (D-PILOTO-08).

### 7.3 `docs/canon/EXECUTION-MASTER-PLAN.md`

⚠️ 📊 Este arquivo **para na SPEC-062** e é append-only por blocos `# ESTADO EM DD/MM/AAAA` — o próprio `ESTADO-DAS-SPECS.md` avisa isso no cabeçalho. O executor **acrescenta** um bloco `# ESTADO EM 13/09/2026 — as cinco entregas dos pilotos ganham relatório`, curto, apontando para o relatório e para o diagnóstico. **Não reescreve o corpo antigo.**

**GATE B3:** os três arquivos citam o relatório; os 22 SHAs aparecem no `ESTADO-DAS-SPECS.md`; `grep -c` de cada SHA colado.

**MUTAÇÃO B3:** remover um SHA do `ESTADO-DAS-SPECS.md` → G-NOVO-1 **vermelho**.

---

## 8. BLOCO 4 — pendências, decisões e adenda

### 8.1 Drenar por número (protocolo §2)

Cada `P-PILOTO-01 … P-PILOTO-20` recebe, no relatório, **uma linha**: `FECHADA` (com a prova) · `CONTINUA` (com o que destrava) · `MORREU`. Ler `PENDENCIAS.md` **por número** — nunca inteiro (CLAUDE.md §2; 📊 o arquivo tem 562 KB).

Medido nesta redação, a confirmar:
- **P-PILOTO-10** (grupo da AutoFleet na Resulta) → 📊 corrigido em 09/09 por ação de dados registrada em `PLANO-HANDOFF-E-PAUSA-2026-09-09.md:8-16`, com VERIFY pelo motor real. Forte candidato a **FECHADA**.
- **P-PILOTO-01** (isolamento) → **CONTINUA**; o pacote 1 deu alívio (envio fora do event loop, buffer paralelo), não solução — a própria pendência já diz isso.
- **P-PILOTO-13** (174 fantasmas LID) → **CONTINUA**; o `--vivo` está bloqueado pelo CHECK.
- **P-PILOTO-17** (`llm_max_tokens` 1200 no banco) → **CONTINUA**, dono 🧑.

### 8.2 As pendências que nunca foram escritas

Os **15** achados listados em `…-RESEARCH-PACK.md` §7.1 (7 do plano de 08/09, 7 do plano de 09/09, 1 medido na redação) viram entradas novas em `PENDENCIAS.md`, na família `P-PILOTO-*`, continuando a numeração (**21 em diante**), cada uma com **o que destrava · de quem é (🧑/🤖) · o que custa esquecer** (CLAUDE.md §11.1).

⚠️ **Antes de numerar, procure:** um achado pode já existir com outro número. `grep` do símbolo (`_dia_e_mes`, `result_summary`, `vidros_lanternas`) em `PENDENCIAS.md` antes de criar. Criar duplicata é pior que não criar.

### 8.3 Decisões

D-PILOTO-01…07 **já estão** em `FOUNDER-DECISIONS.md:1745-1751`; D-PILOTO-08…20 também. **Nada novo a registrar** — só citar por número. Se o BLOCO 0 achar uma decisão tomada nos planos e **não** registrada (por exemplo, `N = 7 dias`, decidida pelo orquestrador em `PLANO-HANDOFF-E-PAUSA:107`), ela vira uma linha nova, marcada **"decisão delegada, registrada retroativamente"**.

### 8.4 `CHANGE-ADDENDA.md`

Uma entrada, classificando os cinco pacotes como **ESSENCIAL** (CLAUDE.md §11), com problema, evidência, consequência e a autorização (D-PILOTO-06), apontando o relatório. Uma entrada, não cinco — a mudança foi de processo, não de escopo de SPEC.

**GATE B4:** os 20 números com estado; as pendências novas com dono e custo; a adenda escrita; `grep` de duplicata colado.

---

## 9. Guardas e mutações — **no máximo 2 novos**

D-PILOTO-14 dá teto de 12. Esta SPEC usa **2**, e não porque é pouco trabalho: é porque um guarda que não pode ficar vermelho não guarda nada (CLAUDE.md §9.3), e só dois fatos aqui são falsificáveis por máquina.

### G-NOVO-1 · `backend/tests/test_as_cinco_entregas_tem_dono.py`

**O que afirma:** o relatório retroativo existe, **passa no mesmo casador que a polícia usa**, e `ESTADO-DAS-SPECS.md` cita os 22 SHAs.

**Como chama o motor (CLAUDE.md §9.4):**

```
✅  from test_o_protocolo_tem_policia import conferir_relatorio, numero_da_spec
    assert conferir_relatorio(open(RELATORIO).read()) == []
❌  assert "EXECUTION CARD" in texto          # isto guarda o `in`, não a regra
```

**Mutações que o deixam vermelho (as três têm de ser exercidas):**
1. Cópia do relatório sem a linha `O ELO` → `conferir_relatorio` devolve defeito → vermelho.
2. Cópia do `ESTADO-DAS-SPECS.md` sem um dos 22 SHAs → vermelho, **nomeando o SHA que falta**.
3. **Linha de controle:** o relatório e o índice reais → **verde**. Sem ela, um casador que aceita tudo passaria por vacuidade.

### G-NOVO-2 · `backend/tests/test_todo_commit_do_piloto_tem_pacote.py`

**O que afirma:** **todo** commit do intervalo `cffaa0e..05f46a9` está atribuído a um pacote no relatório.

**Como chama o motor:** roda `git log --format=%H cffaa0e..05f46a9` de verdade (`subprocess`), não uma lista fixa no arquivo de teste. 🔴 **Lista fixa guardaria a lista; o `git` é o motor.**

**Mutações:**
1. Apagar uma linha de commit do relatório → vermelho, nomeando o SHA órfão.
2. **Linha de controle positiva:** um SHA inventado injetado numa cópia da saída do `git` → vermelho (prova que o guarda **consegue** acusar ausência).
3. **Linha de controle negativa:** o par real → verde.

⚠️ **Armadilha medida:** o intervalo é um par de SHAs fixos numa história já escrita. Se alguém reescrever a história (rebase da `main`), o `git log` falha e o guarda **tem de ficar vermelho com mensagem legível**, não passar por exceção engolida. `try/except: pass` aqui é defeito.

⛔ **Proibido:** um terceiro guarda que confira o dossiê HTML por regex, um que conte linhas de `PENDENCIAS.md`, ou um que afirme "os cinco pacotes funcionam" — esse último é falso por construção: nenhum teste desta SPEC exercita produto.

---

## 10. Migrations

**N/A, com justificativa:** esta SPEC não escreve SQL, não cria coluna, não altera trava e não toca `GRANT`. Nada dispara o piso da §3.2. `MIGRATIONS-AUTHORITY.md` **não precisa ser lido** porque nenhum SQL será escrito — e se o executor concluir que precisa de SQL, ele **parou de executar esta SPEC** e deve registrar a divergência em vez de escrever DDL.

⚠️ **A migration que ESTA SPEC apenas REGISTRA:** o `--vivo` de `migrar_conversas_fantasma_lid.py` continua bloqueado pelo CHECK `ck_conversations_resolucao_motivo` (P-PILOTO-13). O relatório diz isso; a 001.2 é quem a executa.

---

## 11. Prova do que está no ar — conferência, não canário

Esta SPEC **não tem canário**, porque não há efeito a provar: nada é enviado. O que ela tem é uma **conferência read-only**:

```bash
python backend/scripts/conferir_o_que_esta_no_ar.py
```

📊 **Rodado nesta redação em 13/09/2026 — saída real:**

```
portal-worker   repositorio a006a0494024bbb4 (27 arquivos)  ·  no ar a006a0494024bbb4  ·  BATE.
smith-api       repositorio 89787936aa9abe73 (383 arquivos) ·  no ar 89787936aa9abe73  ·  BATE.
TODOS BATEM
```

O executor **repete** a conferência e cola a saída dele — a impressão digital muda quando alguém implanta.

🔴 **A lacuna, declarada:** o script cobre `backend/portal_worker` e `backend/app`. **O `smith-web` não é conferido** (Next.js, sem `.py`), e 📊 os pacotes 1 e 2 mudaram o front (`app/api/dashboard/portal-jobs/route.ts`, `app/dashboard/personalizacao/…`, `lib/attendance/…`). A linha "Implantado" do `smith-web` no relatório é **"declarado nos planos, não conferido por impressão digital"** — e isso vira pendência com dono 🤖, não uma afirmação.

**GATE B5:** saída do script colada; a lacuna do `smith-web` escrita; nenhuma afirmação de deploy sem evidência.

---

## 12. Validação com Saionara e Regina

**N/A, com justificativa:** esta SPEC produz documentação interna. Nada muda na tela, na mensagem ou no fluxo delas. Não há roteiro a preparar, não há sessão a conduzir, não há aceite a registrar.

⚠️ O que **existe** e vai para o relatório é o oposto: 📊 o diagnóstico de 12/09 mediu que a Regina pediu desculpa ao cliente 4 vezes e que a Saionara desligou o agente — **a experiência delas com os cinco pacotes já está medida, e o relatório a cita por referência**, sem repetir a auditoria.

---

## 13. Entrega, implantação e rollback

### Entrega

```bash
git rev-list --count origin/main..HEAD      # o que ainda não subiu
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

🔴 **Entregar não é commitar, é empurrar** (CLAUDE.md §2). A saída real do `push` e o SHA remoto vão colados no relatório. Nunca `git add -A`; arquivo por arquivo.

### Implantação

**Nenhuma.** Esta SPEC muda `.md` e (no máximo) dois arquivos em `backend/tests/`. 🔴 **Nada a implantar no EasyPanel; nada a clicar.** Se o executor pedir deploy, ele saiu do escopo.

⚠️ Um detalhe medido: os dois guardas novos ficam em `backend/tests/`, que **entra na imagem do `smith-api`** — logo a impressão digital do diretório `backend/app` **não** muda (o script conta `backend/app`, não `backend/tests`). O relatório não precisa alertar deploy.

### Rollback

`git revert` dos commits desta SPEC. Nada fica: nenhum dado, nenhuma estrutura, nenhuma mensagem enviada. **Esta é a SPEC mais reversível da família** — e é por isso que o RISCO é 0.

---

## 14. Documentação e acompanhamento obrigatórios

Um escritor por arquivo, durante a execução e não no fim:

1. `docs/canon/specs/SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec.md` — a SPEC definitiva (o executor a cria a partir desta proposta, **medindo**).
2. `docs/canon/reports/SPEC-EXTRA-001.0-EXECUTION-REPORT.md` — o relatório, aberto no início.
3. `ESTADO-DAS-SPECS.md` · `INDICE-DE-SPECS.md` · `EXECUTION-MASTER-PLAN.md` (§7).
4. `PENDENCIAS.md` (§8.1, §8.2) · `FOUNDER-DECISIONS.md` só se a §8.3 achar decisão não registrada · `CHANGE-ADDENDA.md` (§8.4).
5. `docs/canon/reports/dossies/dossies-autobrokers.html` — 📊 já existem as páginas `p-home`, `p-extra001` e `p-pilotos`. A EXTRA-001.0 entra como **linha na home + bloco na página `p-pilotos`** (é onde a história dos pilotos já mora), ou como página `p-extra0010` se o executor medir que a navegação derivada do DOM comporta. **Ler o HTML publicado inteiro antes de republicar com `url`.** Sem ferramenta ou sem acesso: atualizar a fonte versionada e escrever **"publicação do dossiê pendente"** com o arquivo e o passo exato. Nunca alegar que o link foi atualizado.
6. Memória/handoff do programa, com a fila atualizada.

🔴 **Nunca publicar SHA de credencial, telefone, ou o conteúdo de `JANELA_SILENCIO_EXCECOES`.**

---

## 15. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

Quatro fontes primárias, **reabertas em 13/09/2026** nesta redação. O pesquisador do executor as reabre de novo na conversão e registra a data dele (protocolo §7.3).

### E01 — Google SRE Book, "Postmortem Culture: Learning from Failure" · https://sre.google/sre-book/postmortem-culture/ · reaberta 13/09/2026

**Faz:** fixa gatilhos objetivos e o conteúdo mínimo de um postmortem — incidente · impacto · ações de mitigação · causa(s) raiz · **ações de acompanhamento** — sob o princípio *"Blameless postmortems are a tenet of SRE culture"*.
**Modelamos:** o conteúdo mínimo e a escrita sem culpado. O card retroativo (§6.3) diz o que aconteceu e o que custou, nunca quem errou; a §8.1 é o "follow-up actions": cada risco com dono e com o que destrava.
**Rejeitamos:** o gatilho. 📊 A fonte dispara por **incidente** e, medida hoje, **não prescreve postmortem para mudança bem-sucedida** — é essa lacuna que D-PILOTO-15 preenche. E rejeitamos "action items" que virem trabalho desta SPEC: aqui viram pendência numerada.
**O juiz inspeciona:** abre a página, confere os cinco itens em cada ficha da §5, e que nenhuma frase do relatório nomeia culpado.

### E02 — RFC 7942, "The Implementation Status Section" · https://www.rfc-editor.org/rfc/rfc7942.html · reaberta 13/09/2026

**Faz:** padroniza a declaração do que está **realmente implementado**: responsável · nome/link · descrição · **maturidade** (research…widely used) · **cobertura** · versão · licença · experiência · contato · **data da última atualização**.
**Modelamos:** a distinção entre "existe código" e "está no ar e exercitado", **com data obrigatória**. A linha `IMPLANTADO` da ficha (§5.1) e a §11 são a Implementation Status desta SPEC — incluindo a lacuna do `smith-web` declarada em vez de omitida. É o antídoto de CLAUDE.md §12.
**Rejeitamos:** a instrução de **remover a seção antes da publicação** (*"inappropriate for inclusion in a published RFC"*). Aqui a seção **é** o produto; o envelhecimento que a fonte teme tratamos com data e com impressão digital recalculável.
**O juiz inspeciona:** abre a RFC §2 e confere maturidade, cobertura e data em cada ficha; nenhuma diz "implantado" sem evidência ao lado.

### E03 — Keep a Changelog 1.1.0 · https://keepachangelog.com/en/1.1.0/ · reaberta 13/09/2026

**Faz:** *"Changelogs are for humans, not machines"*; entrada por versão, agrupada, com data. E explica por que o `git log` não basta: *"Using commit log diffs as changelogs is a bad idea: they're full of noise"* — o commit documenta a evolução do código, a entrada comunica *"the noteworthy difference… to end users"*.
**Modelamos:** a frase que justifica esta SPEC. Os 22 commits existem e são bem escritos; ainda assim não são o registro. Por isso a ficha (§5.1) abre com `NOME em português, o que ele faz para quem usa` **antes** de `COMMITS`.
**Rejeitamos:** as seis categorias e o versionamento semântico — o eixo aqui é SPEC/pacote, e `Added/Fixed` sobre cinco pacotes heterogêneos perderia a causa. E rejeitamos criar `CHANGELOG.md`: motor paralelo ao `CHANGE-ADDENDA.md` e ao `INDICE-DE-SPECS.md` (CLAUDE.md §5).
**O juiz inspeciona:** lê as cinco linhas `NOME` e pergunta se um corretor entenderia. Linha que só repete a mensagem do commit reprova.

### E04 — MADR (Markdown Any Decision Records) · https://adr.github.io/madr/ · reaberta 13/09/2026

**Faz:** formato mínimo do registro de decisão — título · contexto e problema · opções consideradas · resultado — com `status` (`proposed | rejected | accepted | … | superseded by ADR-0123`), `date`, `decision-makers`, e **Consequences** anotadas com sinal: *"Good, because" / "Bad, because" / "Neutral, because"*. Supersessão é por **apontamento**, não por edição do antigo.
**Modelamos:** consequência com sinal e supersessão por apontamento. As decisões D-PILOTO-01…07 ganham na §5.5 a consequência medida — inclusive a "Bad, because" (D-PILOTO-06 custou o painel). E a regra de não editar o antigo é a §1.2 item 6.
**Rejeitamos:** criar arquivos ADR. `FOUNDER-DECISIONS.md` já é a autoridade de decisões; um diretório `adr/` seria motor paralelo. Modelamos o **formato do conteúdo**, não o meio.
**O juiz inspeciona:** abre o template, confere o sinal em cada consequência da §5.5, e que `git diff` dos dois planos de 08 e 09/09 esteja **vazio**.

---

## 16. Matriz de aceite — os gates e as mutações

| Gate | Deve comprovar | Contraexemplo / mutação que precisa REPROVAR |
|---|---|---|
| **G0** | Árvore em dia, intervalo remedido, 22 commits confirmados | tratar os números desta proposta como medição de hoje |
| **G1** | Os 22 SHAs atribuídos aos cinco pacotes, sem sobra | um SHA órfão no relatório |
| **G2** | Arquivos por pacote medidos por `git`, com o comando ao lado | somar as linhas dos pacotes e apresentar como união |
| **G3** | Cada guarda com saída real **e** forma de invocação escrita | rodar `python` num arquivo pytest e colar "0 testes" como verde |
| **G4** | Relatório passa no bloco [7] da polícia, rodado | relatório que "segue o template" sem a polícia ter rodado |
| **G5** | Cards retroativos com `NÍVEL QUE TERIA SIDO × QUE FOI` e a causa (D-PILOTO-06) | card que omite que o painel não rodou, ou que acusa o executor |
| **G6** | Os 20 `P-PILOTO-*` com estado e evidência; os 7 achados sem número viram pendência | marcar `FECHADA` sem prova; criar duplicata de pendência existente |
| **G7** | Índices atualizados; SHAs no `ESTADO-DAS-SPECS.md`; master plan **acrescentado**, não reescrito | reescrever veredito histórico; renumerar a família |
| **G8** | G-NOVO-1 e G-NOVO-2 verdes **e** com as mutações exercidas | guarda que não consegue ficar vermelho; lista de SHAs fixa no teste |
| **G9** | Nenhum arquivo de produto no diff; `push` com saída colada; impressão digital conferida com a lacuna do `smith-web` declarada | "aproveitei e consertei um typo"; declarar `smith-web` implantado |

🔴 **Mutação roda em cópia, em subprocesso, e restaura por CÓPIA — nunca `git checkout`** (protocolo §10). Uma falha nova, nomeada, por mutação.

---

## 17. Dependências e o que esta SPEC deixa para as seguintes

**Depende de:** nada. É a primeira da fila (diagnóstico §12.1) e não tem pré-requisito técnico nem ação do Founder. D-PILOTO-15 já está `SIM`.

**Deixa pronto para as seguintes:**

| quem | o que recebe |
|---|---|
| **001.1** (apólice certa) | a ficha do pacote 3 — o que `/itens` já entrega, o cache de 180 s, e por que o PDF passou a ser lido também com cobertura estruturada |
| **001.2** (lê tudo antes de falar) | a ficha do pacote 2 (identidade única do evento, pausa, janela N=7) e do 5 (exceções), + P-PILOTO-13 com o CHECK que bloqueia o `--vivo` |
| **001.3** (grupo só o que importa) | a ficha do pacote 2 (destino de suporte pelo seletor, rastro do handoff) e P-PILOTO-10/12 |
| **001.4** (corredor não trava) | a ficha do pacote 1 (dossiê em português, trava de laço, prova em todo desfecho) e P-PILOTO-05/06 |
| **001.6** (cobrança) | nada diretamente; mas o relatório registra que a rotina rodou em `test` nesses dias |
| **001.7** (piloto medido) | 🔴 a lista das **pendências novas** da §8.2 e o risco "a suíte inteira nunca rodou com a árvore parada" |
| todas | o precedente do **card retroativo** — a forma de documentar trabalho que já existe, sem reexecutá-lo |

---

## 18. Definição final de conclusão

Lista fechada. Cada item é verificável por um comando.

1. `docs/canon/specs/SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec.md` existe, declara **protocolo v11**, tem **BLOCO 0**, **O QUE SAIU**, **📊**, **mutação** e a seção **O QUE O ESTADO DA ARTE FAZ** com ≥ 3 URLs externas.
2. `docs/canon/reports/SPEC-EXTRA-001.0-EXECUTION-REPORT.md` existe e **passa no bloco [7]** de `test_o_protocolo_tem_policia.py`, com a saída colada.
3. As cinco fichas estão completas, e os **22 SHAs** estão atribuídos.
4. Cada guarda da §5.7 tem **saída real** e **forma de invocação** no relatório.
5. Os **cinco cards retroativos** existem, com `NÍVEL QUE TERIA SIDO × QUE FOI` e a causa D-PILOTO-06.
6. Os **20 `P-PILOTO-*`** têm estado; os **7 achados sem número** viraram pendência com dono.
7. `ESTADO-DAS-SPECS.md`, `INDICE-DE-SPECS.md` e `EXECUTION-MASTER-PLAN.md` citam o relatório; `CHANGE-ADDENDA.md` tem a entrada.
8. **G-NOVO-1** e **G-NOVO-2** existem, estão verdes, e cada mutação declarada foi exercida e ficou vermelha.
9. `conferir_o_que_esta_no_ar.py` rodado, saída colada, **lacuna do `smith-web` declarada**.
10. `git diff --stat` da branch **não contém nenhum arquivo de produto**.
11. `git push origin HEAD:main` executado, com a saída real e o SHA remoto colados.
12. Dossiê atualizado — ou **"publicação pendente"** com o arquivo e o passo exato.
13. Resumo ao Founder em linguagem simples: **o que o canon passou a saber · o que continua sem dono · qual é a única próxima ação**.

⚠️ Faltou um item material? O estado é **PARCIAL**, com o nome do que faltou. "Pronto" não substitui evidência.

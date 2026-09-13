# PROMPT DE ABERTURA — SPEC-EXTRA-001.0
## "As cinco entregas sem SPEC ganham relatório" · retroativa · marcha **LEVE**

> Cole este documento **inteiro** num chat NOVO do Claude Code Fable, aberto na árvore atualizada do AutoBrokers.
> Este prompt **não contém** números de teste, credencial ou dado pessoal, e o trabalho que ele descreve também não pode conter.

Você é o **ORQUESTRADOR Fable** da **SPEC-EXTRA-001.0**, co-líder técnico com o Founder Amandus. Você vai investigar, converter a proposta em SPEC definitiva, aquecer, executar, provar e entregar — segundo `CLAUDE.md` e o **PROTOCOLO AUTOBROKERS AAA v11**, na **OPÇÃO B** de `docs/canon/DECISAO-DO-RITMO-03-09-2026.md`.

🔴 **Esta é a SPEC mais curta da família, e a mais fácil de fazer errado.** Ela é **documentação retroativa**: você **não escreve uma linha de código de produto**. A tentação de "já que estou aqui, conserto" é o único jeito de reprovar nesta SPEC.

---

## 1. A tarefa, e os arquivos por caminho

Entre **08 e 10/09/2026**, cinco pacotes de código entraram na `main` **sem SPEC, sem painel e sem relatório**, por ordem do Founder (**D-PILOTO-06**: "executar o essencial sem AAA por limite de tokens"). Eles funcionam, têm testes e estão implantados. **O canon não sabe que existem.** O Founder decidiu (**D-PILOTO-15 = SIM**, 13/09) que eles ganham uma SPEC retroativa. É esta.

**Você recebe:**

```
docs/canon/specs-propostas/SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec.md              a PROPOSTA
docs/canon/specs-propostas/SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec-RESEARCH-PACK.md as EVIDÊNCIAS
docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.0.md                           este arquivo
```

**Você cria:**

```
docs/canon/specs/SPEC-EXTRA-001.0-as-cinco-entregas-sem-spec.md      ← a SPEC definitiva
docs/canon/reports/SPEC-EXTRA-001.0-EXECUTION-REPORT.md              ← o relatório (o PRODUTO desta SPEC)
backend/tests/test_as_cinco_entregas_tem_dono.py                     ← guarda novo 1 (de 2)
backend/tests/test_todo_commit_do_piloto_tem_pacote.py               ← guarda novo 2 (de 2)
```

**Você atualiza:** `docs/canon/ESTADO-DAS-SPECS.md` · `INDICE-DE-SPECS.md` · `EXECUTION-MASTER-PLAN.md` · `PENDENCIAS.md` · `CHANGE-ADDENDA.md` · `reports/dossies/dossies-autobrokers.html`.

**Projeto:** `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`. **Confirme a árvore, a branch e o `origin/main` — não confie no nome da pasta** (CLAUDE.md §2). Branch sugerida: `docs/spec-extra-001-0-retroativa`.

⚠️ A proposta e o research pack **não são execução**. Não os sobrescreva para fingir que já estavam validados. O que mudar na conversão vai para a SPEC definitiva e para a matriz de premissas corrigidas.

---

## 2. Autorizações atuais — a fronteira mais curta da família

### Pode

- Ler o repositório inteiro; rodar `git`, os testes existentes, `py_compile`, `tsc`, `node`.
- Rodar `python backend/scripts/conferir_o_que_esta_no_ar.py` — read-only, sem credencial, sem portal.
- Escrever **`.md`** e **no máximo dois** arquivos novos em `backend/tests/`.
- `SELECT` de contagem no banco **só** se um número do relatório exigir. Nunca conteúdo de mensagem.

### Não pode

1. 🔴 **Tocar qualquer arquivo de produto.** Nem typo, nem comentário, nem rename. Achou defeito? **Vira pendência numerada e a SPEC segue.**
2. Enviar mensagem a quem quer que seja. Ligar agente, rotina, job, dispatch. **NENHUMA mensagem sai.**
3. Reexecutar, refazer ou "melhorar" qualquer um dos cinco pacotes.
4. Publicar telefone, CPF, CNPJ, placa, nome de segurado, e-mail, credencial ou o conteúdo de `JANELA_SILENCIO_EXCECOES`. Os números de teste do Founder aparecem **só** como `TESTE-A` e `TESTE-B`.
5. Rodar migration, DDL, `psql` ou qualquer script `--vivo`.
6. Reescrever veredito histórico. Um plano de 08 ou 09/09 que envelheceu ganha a correção **ao lado**, com data — nunca por cima. `git diff` dos dois planos tem de ficar **vazio**.
7. `git add -A`, force push, ou apagar `index.lock` por timeout.

**Antes do único efeito desta SPEC (o `push`):** `git diff --stat` conferido arquivo a arquivo. **Um arquivo de produto na lista para a entrega.**

⚠️ **Pode haver outros agentes escrevendo nesta árvore.** 📊 Medido em 13/09: havia. Rode a bateria com a **árvore parada**, e se não puder, diga isso no relatório em vez de colar um número que não vale.

---

## 3. Estado herdado — não confunda com medição de hoje

- **O intervalo:** 📊 `cffaa0e..05f46a9` = **22 commits**, 08/09 20:43 → 10/09 13:56. A tabela commit-a-commit está no research pack §2.
- **Os cinco pacotes:** (1) plano de ajustes dos pilotos, 9 commits, fonte `docs/canon/PLANO-PILOTOS-AJUSTES-2026-09-08.md`; (2) plano handoff+pausa, 9 commits, fonte `docs/canon/PLANO-HANDOFF-E-PAUSA-2026-09-09.md`; (3) apólice item a item, `bf963b0`, **sem fonte além do commit**; (4) resposta inteira, `312939f`, **sem fonte**; (5) exceções da janela, `05f46a9`, **sem fonte**. `2701fc3` (pendências) atende a 3 e 4.
- **O tamanho:** 📊 74 arquivos · 11.822 inserções · 344 remoções · 13 arquivos de teste novos.
- **Depois do intervalo:** 📊 só 2 commits `docs(pilotos)` até `a0bb5fe`; **nenhum arquivo de produto mudou**.
- **A auditoria já existe:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` é a auditoria dos pilotos. **Você não a refaz.** Você a cita.
- **Onde a história encaixa:** `ESTADO-DAS-SPECS.md` **já tem** a tabela "🔵 EXECUTADAS SEM SPEC" (SPEC-079, SPEC-082) com a frase *"Trabalho sem SPEC é trabalho sem gate"*. Os cinco entram **nela**.
- **A polícia julga você:** 📊 `backend/tests/test_o_protocolo_tem_policia.py:80,262,284` reconhece `SPEC-EXTRA-NNN` e a coloca **sob a v11**. O seu relatório **será** julgado pelo bloco [7].
- **`EXECUTION-MASTER-PLAN.md` para na SPEC-062** e é append-only por blocos `# ESTADO EM DD/MM/AAAA`. **Acrescente um bloco datado; não reescreva.**

---

## 4. Bootstrap enxuto e obrigatório

Leia, nesta ordem e nada além:

```
1. CLAUDE.md                                        inteiro
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md          §0–§3, §5, §7.3 — só estas seções
3. docs/canon/GLOSSARIO.md                          os termos
4. a proposta e o research pack desta SPEC
```

Por demanda, e só a seção pertinente: `DECISAO-DO-RITMO-03-09-2026.md` (opção B) · `reports/SPEC-EXECUTION-REPORT-TEMPLATE.md` · `reports/SPEC-EXTRA-001-EXECUTION-REPORT.md` (é a sua **REFERÊNCIA interna**: o relatório que passa na polícia) · `ESTADO-DAS-SPECS.md`, `INDICE-DE-SPECS.md`, `EXECUTION-MASTER-PLAN.md` **nas seções afetadas** · `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §7.2 e §12.1.

⛔ **Não leia `PENDENCIAS.md` inteiro** (📊 562 KB). Só por número: `P-PILOTO-01 … P-PILOTO-20`.
⛔ **Não leia `MIGRATIONS-AUTHORITY.md`**: esta SPEC não escreve SQL. Se você concluir que precisa de SQL, **você saiu do escopo** — registre a divergência.
⛔ Todo pacote que você entregar a um subagente carrega o **protocolo §0–§3, §5, §7.3**, o contrato da unidade, os arquivos por caminho, as regras do CLAUDE.md por número, os gates com a mutação, e a trava **"NENHUMA mensagem sai"**. Os modelos vivos estão em `docs/canon/pacotes/`.

---

## 5. Como converter a proposta em SPEC definitiva

1. **Preflight Git** (CLAUDE.md §2): fetch, SHA, contagem atrás/à frente, branch, status. Contagem ≠ 0 na primeira: **pare e pergunte**.
2. **Abra o relatório pelo template**, com o **EXECUTION CARD** no topo, antes de qualquer escrita. O card da proposta §0.2 é o ponto de partida; os números são seus.
3. **BLOCO 0 — remeça tudo** (proposta §4.2, research pack §9). O número que você mede **vence** o desta proposta. Monte a matriz *premissa → observação nova → comando → decisão*.
4. **Converta** em `docs/canon/specs/SPEC-EXTRA-001.0-…md`. 🔴 A SPEC definitiva **tem de** declarar `protocolo … v11`, e conter **BLOCO 0**, **O QUE SAIU**, **📊**, **mutação** e a seção **"O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS"** com **≥ 3 URLs externas** — é o que `conferir_spec` cobra (`test_o_protocolo_tem_policia.py:226-243`). As quatro referências estão na proposta §15; **reabra-as e registre a sua data**.
5. **Uma rodada de aquecimento** (§7 deste prompt), em contexto limpo. Emende a SPEC com o que voltar. **Uma rodada, não três.**
6. **Execute.** B1 inventário → B2 relatório → B3 índices → B4 pendências. Serial: um escritor por arquivo.

---

## 6. A execução AAA — opção B, marcha LEVE, sem desperdício

```
NÍVEL ........ LEVE      RISCO 0 · SUPERFÍCIE 1  (a conta está na proposta §0.2; refaça-a)
TIME ......... orquestrador + builder documental + verificador mecânico + 1 JUIZ FRESCO
SEM .......... painel de lentes · red team · desenhista · integrador · canário vivo
JUÍZES ....... 1 (fresco, contexto limpo, read-only) — porque SUPERFÍCIE = 1 (§3.1)
GUARDAS NOVOS  MÁXIMO 2. Não 3. Não "mais um pequenininho"
BATERIA ...... os guardas dos cinco pacotes + os 2 novos + a própria polícia, árvore PARADA
RELÓGIO ...... 💭 1–2h · faixa, nunca promessa (§9.2)
ORÇAMENTO .... 💭 ≤ 250k tokens de subagentes. Medir, não estimar no fim
MODELO ....... orquestrador Fable · builder/juiz Opus · mecânico Sonnet. Não trocar no meio
```

🔴 **Por que não há painel:** a conta do §3 do protocolo o dispensa (RISCO 0, SUPERFÍCIE 1), e **a conta está escrita no card**. "Não rodei o painel" é resposta aceitável **quando a conta está escrita** — campo em branco, não.

🔴 **E o juiz fresco não é decorativo.** Ele recebe o §0 do protocolo, o diff e os comandos — **nunca a SPEC inteira**. A pergunta dele é: *o relatório afirma alguma coisa que um comando não sustenta?*

**Verificador mecânico, na ordem:** `py_compile` dos dois guardas novos → os guardas dos cinco pacotes → a polícia → `git diff --stat` sem arquivo de produto.
⚠️ Você **não** mexe em `app/`, `middleware.ts` nem `next.config.js`, então `test:rotas-montam` e `next start` **não** se aplicam. Diga isso no relatório em vez de omitir.

**Mutação:** roda em cópia, em subprocesso, restaura **por CÓPIA** — nunca `git checkout`. Uma falha nova, nomeada, por mutação. As mutações obrigatórias estão na proposta §9 e §16.

---

## 7. Aquecimento — 14 perguntas, duas deliberadamente falsas

Use `docs/canon/pacotes/PACOTE-AQUECIMENTO.md`. Contexto limpo, read-only, **uma rodada**. As perguntas 1 e 2 são **falsas assinadas por mim**, do exercício — não são regras do projeto. Se o BLOCO 0 mostrar que uma delas deixou de ser falsa, **troque-a por outra falsa medida** antes de enviar.

1. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"Como a EXTRA-001.0 só produz documentação, o relatório dela não é julgado pela polícia do protocolo."* Refute com o arquivo e a linha.
2. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"Os cinco pacotes violaram o protocolo AAA, e o relatório tem de registrar essa violação."* Mostre a decisão que a contradiz, por número e data.
3. Somar as linhas dos cinco pacotes dá a união medida? Mostre a conta e explique a diferença. *(a resposta óbvia é "dá"; ela é errada)*
4. Os 22 commits se distribuem igualmente entre os cinco pacotes? Dê a distribuição real e diga o que fazer com o commit que atende a dois.
5. Qual é a forma de invocação de cada guarda da proposta §5.7 — `python` ou `pytest`? O que acontece se você errar? *(rode e mostre; a resposta óbvia "é tudo pytest" é errada)*
6. `conferir_o_que_esta_no_ar.py` devolveu "TODOS BATEM". O que exatamente isso **não** prova sobre os cinco pacotes? Nomeie o serviço e o número de arquivos que ficam de fora.
7. O relatório precisa da palavra "bateria" e de uma nota `NN/100`? Por quê, e o que acontece se faltarem? Cite o casador e a linha.
8. Qual é a diferença entre o **card da SPEC-001.0** e os **cinco cards retroativos**? Se os cinco pacotes fossem enquadrados hoje pelo §3.2, que piso cairia sobre eles — e por quê?
9. Onde exatamente, em `ESTADO-DAS-SPECS.md`, os cinco entram? Por que criar uma tabela nova seria erro? Cite a seção que já existe.
10. Por que `EXECUTION-MASTER-PLAN.md` não deve ser reescrito? Mostre o que o próprio canon diz sobre ele.
11. Liste os achados dos dois planos que **nunca viraram número** de pendência. Antes de propor números novos, mostre o `grep` que provou que não existem duplicatas.
12. O guarda novo que confere o relatório deve reimplementar a regra do card ou chamar a função da polícia? Justifique pela regra do CLAUDE.md, por número, e escreva as duas versões para mostrar a diferença.
13. Reproduza **três** medições da proposta, com comando e saída, redigidas sem PII. Se alguma divergir, diga qual e quanto.
14. Liste o que você **NÃO** entendeu ou não conseguiu provar. **"Entendi tudo" reprova o exercício.** E ache **um defeito material** que a proposta não aponta — ou diga onde procurou e não achou. Entregue a nota 0–100 e o card que você aplicaria.

⛔ Não coloque respostas prontas no pacote de quem tem de investigar. A fronteira da §2 deste prompt não é pegadinha: ela é inequívoca e vai inteira no pacote.

---

## 8. O que você entrega como produto

1. **O relatório retroativo** — o produto desta SPEC. Com EXECUTION CARD que passa na polícia, as **cinco fichas** (proposta §5.1), os **cinco cards retroativos** honestos (§6.3), os **22 SHAs** atribuídos, cada guarda com **saída real + forma de invocação**, e a lacuna do `smith-web` declarada.
2. **A SPEC definitiva**, convertida medindo, com as 4 referências externas reabertas e datadas.
3. **Os índices**: `ESTADO-DAS-SPECS.md` (na tabela que já existe, com os SHAs) · `INDICE-DE-SPECS.md` (uma linha EXTRA-001.0) · `EXECUTION-MASTER-PLAN.md` (um bloco datado, acrescentado).
4. **As pendências**: os 20 `P-PILOTO-*` com estado `FECHADA`/`CONTINUA`/`MORREU` e evidência; os **15 achados sem número** virando entradas novas (21 em diante), cada uma com o que destrava, o dono 🧑/🤖 e o custo de esquecer. `grep` de duplicata antes de numerar.
5. **`CHANGE-ADDENDA.md`**: uma entrada, classificando os cinco como **ESSENCIAL**, com problema, evidência, consequência e a autorização D-PILOTO-06.
6. **Os dois guardas**, verdes, com as mutações exercidas e vermelhas.
7. **A entrega**: `git push origin HEAD:main` com a saída real e o SHA remoto colados.

🔴 **O que o relatório NÃO pode dizer:** que os cinco "foram validados" (📊 1h53 de agente ligado em 3 dias, 5 segurados reais) · que "os testes provam que funciona" · um número sem 📊 e sem comando · "implantado" para o `smith-web` sem evidência · que alguém violou o protocolo.

**Nenhuma implantação.** Esta SPEC muda `.md` e dois arquivos em `backend/tests/`. Nada a clicar no EasyPanel. Se você pedir deploy, saiu do escopo.

---

## 9. Dossiê e acompanhamento

O Founder acompanha em: https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868
Fonte versionada: `docs/canon/reports/dossies/dossies-autobrokers.html`

📊 As páginas existentes são `p-home`, `p-s088…p-s098`, `p-extra001`, `p-pilotos`, `p-proto`, `p-fila`. A EXTRA-001.0 encaixa como **bloco na página `p-pilotos`** (é onde a história dos pilotos já mora) **+ linha na home** — ou como página própria, se você medir que a navegação derivada do DOM comporta. **Meça antes de escolher o id.**

🔴 **Leia o HTML publicado inteiro antes de republicar com `url`.** Preserve o conteúdo existente. Confira o resultado no link. Sem ferramenta ou sem acesso: atualize a fonte versionada, escreva **"publicação do dossiê pendente"** com o arquivo e o passo exato, e entregue ao Founder. **Nunca alegue que atualizou o artifact**, e não crie substituto silencioso.

Atualize também a memória/handoff do programa com a fila: **001.0 → 001.6-P0 → 001.1 → 001.2 → 001.3 ∥ 001.4 → 001.6 → 001.7 → 001.10 ∥ 001.5 → 001.8 → 001.9** (diagnóstico §12.1). **Nada renumera** (D-PILOTO-08).

---

## 10. Integração, estado final e o que entregar ao Founder

Push só de commits gateados, com a saída colada e o head remoto conferido. Se a `main` avançar, **não force**: integre e valide o head efetivo.

No fim, entregue ao Founder, em linguagem simples:

1. **O que o canon passou a saber** que não sabia — em três frases.
2. Onde está o relatório, e o que ele diz sobre cada um dos cinco.
3. **O que continua sem dono**: as pendências novas, por número, com quem resolve.
4. O estado separado: **escrito / na main / índices atualizados / guardas verdes / dossiê publicado**.
5. Os gates que passaram, e os que não puderam ser comprovados (com o motivo).
6. **A caixa do Founder**: o que só ele faz. 💭 A expectativa é que esteja **vazia** — se não estiver, cada item com o que é, o que faz, o que custa esquecer, e se bloqueia (quase sempre NÃO).
7. **Handoff:** a próxima da fila é **EXTRA-001.6-P0** (cobrança: `bloco_unico`, motivo da Mapfre, frases da Allianz, nome da atendente), em chat novo. **Não a execute agora.**

Comece pelo **preflight**, depois o **card**, depois o **BLOCO 0**. Não me devolva uma análise: converta, execute e entregue esta SPEC dentro da fronteira descrita — e lembre que aqui o sucesso é um documento que um estranho consegue **conferir com um comando**, não um documento que soa bem.

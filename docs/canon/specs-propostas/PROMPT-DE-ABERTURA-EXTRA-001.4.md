# PROMPT DE ABERTURA — SPEC-EXTRA-001.4 · O corredor não trava sozinho

> **Cole este documento inteiro num chat NOVO do Claude Code Fable**, aberto na árvore atualizada do AutoBrokers. Os dois números de teste **não** estão aqui: eles ficam na configuração privada, e neste texto aparecem só como **TESTE-A** e **TESTE-B**. O Founder informa os valores reais em mensagem privada, ou eles já estão na allowlist configurada.

Você é o **ORQUESTRADOR Fable** da **SPEC-EXTRA-001.4 · O corredor não trava sozinho**, co-líder técnico com o Founder Amandus. Você é o executor do processo completo: preflight, investigar, validar a proposta, **convertê-la em SPEC definitiva**, aquecer o executor, implementar, provar, integrar e entregar — segundo o `CLAUDE.md` e o **PROTOCOLO AUTOBROKERS AAA v11.2 + OPÇÃO B**.

**Marcha já fixada, não se rediscute: CRÍTICO · 3 juízes · red team · juiz fresco** (diagnóstico §8; D-PILOTO-14). **Não comece outra SPEC.** Uma SPEC por chat.

---

## 1. A tarefa e os arquivos

O pacote é composto de três arquivos, já instalados na árvore:

```text
docs/canon/specs-propostas/SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho.md               ← a PROPOSTA
docs/canon/specs-propostas/SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho-RESEARCH-PACK.md ← a EVIDÊNCIA
docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.4.md                              ← este texto
```

E você cria estes dois:

```text
docs/canon/specs/SPEC-EXTRA-001.4-o-corredor-nao-trava-sozinho.md      ← a SPEC DEFINITIVA
docs/canon/reports/SPEC-EXTRA-001.4-EXECUTION-REPORT.md                ← o RELATÓRIO
```

Árvore esperada: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`.
🔴 **Confirme a árvore, a branch e a distância para `origin/main` pelo comando — não pelo nome da pasta** (CLAUDE.md §2). Proposta e research pack **não são** execução: não os sobrescreva para fingir que já estavam validados. O que mudar na conversão vai para a SPEC definitiva e para a matriz de premissas corrigidas.

**O problema, em cinco linhas:** em 10/09 o corredor respondeu **"residência"** a um menu que pedia **"1"**; a Saionara digitou o "1" à mão e o robô **digitou por cima dela**; a sessão travou em `needs_human`; catorze minutos depois a atendente da Allianz se apresentou e **ninguém respondeu**, porque `needs_human` fecha as três portas do motor de uma vez; a URA encerrou por falta de contato e o grupo recebeu três alertas sobre um caso já morto.

---

## 2. Autorizações atuais do Founder

**Testes vivos só entre TESTE-A e TESTE-B**, com remetente e destinatário **ambos** na allowlist e identidade real conferida. Nome de corretora, de instância ou de conexão **não prova** identidade: confira o telefone efetivamente pareado.

**O canário desta SPEC é a COLETA DIRIGIDA (D-PILOTO-05):**

```
✅ percorrer a URA de uma seguradora ATÉ A TELA DE CONFIRMAÇÃO
⛔ e RECUSAR. Nunca confirmar. Passar da confirmação despacha prestador real.
```

⛔ **Proibido:** usar número operacional da Resulta ou da AutoFleet como remetente, mesmo para enviar ao Founder · falar com segurado, atendente, grupo ou seguradora fora da allowlist, **inclusive por cutucada, dossiê, alerta, fila, retry e job de fundo** · ligar atendimento/dispatch globalmente num tenant operacional para o canário funcionar · abrir chamado, sinistro ou assistência real · alterar o corpus para um teste passar.

🔴 **Uma trava específica deste corredor, e ela é fácil de esquecer:** as saídas externas aqui são **quatro**, não uma — a mensagem à URA da seguradora, o `send_to_client`, a **cutucada do Vigia** (`app/tasks/dispatch_watchdog.py:575`, que fala com a seguradora) e o **dossiê ao grupo** (`dispatch_router.py:3304`, `dispatch_watchdog.py:421`). A trava do canário precisa cobrir as quatro **antes** de o Vigia ser ligado sobre qualquer sessão viva.

Consultas SELECT ao banco de produção são permitidas, **só contagens e estruturas**. ⛔ Nunca imprimir CPF, telefone, nome de segurado, placa, e-mail ou credencial — em log, teste, fixture, corpus, dossiê ou relatório.

Falta ação física (parear número, abrir a conversa com a URA)? Complete tudo que independe disso, registre o gate como **não comprovado**, e ponha o pedido na **caixa do Founder**. **Ausência de canário não vira aprovação.**

---

## 3. Estado herdado — não confunda com medição de hoje

- Repositório `Amandico100/AutoBrokers-Intelligence-OS`. Baseline desta preparação: **`a0bb5fe`**, 13/09/2026. A revisão da execução pode ter avançado.
- A família EXTRA-001.x nasce do `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md`. **Esta SPEC é a 001.4**, e ela **não depende de nenhuma outra** (é paralela à 001.3, §12.1 do diagnóstico).
- 📊 **Entre 08 e 10/09 cinco pacotes entraram na `main` sem SPEC, sem painel e sem relatório**, por ordem do Founder ("execute o essencial sem AAA"). Um deles mexeu em pausa por intervenção humana e rajadas. **Isto importa para você:** a bateria está vermelha hoje em dois testes de dispatch (§6 pergunta 12), e uma das hipóteses é regressão dessas entregas. **Não rotule "pré-existente" em bloco.**
- 🔴 **Três correções que esta preparação já fez ao diagnóstico**, e que você herda prontas:
  1. `dispatch_watchdog.py` mora em **`app/tasks/`**, não `app/services/`.
  2. `registrar_ato_do_agente` **tem três chamadores reais** — o problema não é "ninguém chama", é que a chamada não chega ao INSERT.
  3. A frase *"Por falta de contato, estou encerrando"* **não existe no corpus**, e a variante que existe **já é coberta** pela regex atual.
- Autoridades a preservar: SPEC-083 (a régua do corredor e a regra "toda tecla tem origem"), SPEC-084/087 (Atlas e `tela_cega`), SPEC-085 (honestidade do handoff), SPEC-092 (`native_flows`), SPEC-093-B (`registrar_ato_do_agente`).
- 🔴 **Colisão declarada com a EXTRA-001.3, que é paralela a esta.** As duas precisam da guarda única *"humano já está nesta conversa"* (`o_grupo_pode_saber`): a 001.3 porque é o coração dela, esta porque a pausa de 60 s tem de calar o grupo. **Protocolo, não juízo: quem executar primeiro CRIA a função; quem executar depois CHAMA e acrescenta a sua causa.** ⛔ Duas implementações = motor paralelo, e **as duas SPECs reprovam**. O item 2-bis do seu BLOCO 0 é um `grep` para descobrir em qual dos dois lados você está.

---

## 4. Bootstrap enxuto e obrigatório

Leia, nesta ordem e só isto:

```
1. CLAUDE.md                                     inteiro
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md       §0 a §3, §5, §7.3
3. docs/canon/GLOSSARIO.md                       os termos (corredor ≠ portal ≠ RAG ≠ Atlas)
4. a PROPOSTA e o RESEARCH PACK desta SPEC
```

Por demanda, **nunca "por via das dúvidas"**:

- `docs/canon/MIGRATIONS-AUTHORITY.md` — **antes de qualquer SQL**.
- `docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md` — para abrir o relatório.
- `FOUNDER-DECISIONS.md` — **só** as linhas `D-PILOTO-05, 08, 10, 14, 20`.
- `PENDENCIAS.md` — **só** `P-PILOTO-05` e `P-PILOTO-06`, **por número**. ⛔ O arquivo tem 562 KB; ler inteiro é o maior custo medido do projeto.
- `docs/canon/specs/SPEC-083-a-regua-do-corredor.md` §2.4 — a regra das três origens da tecla. ⚠️ as linhas citadas lá envelheceram; o RESEARCH PACK traz as de hoje.
- `ESTADO-DAS-SPECS.md` e `INDICE-DE-SPECS.md` — **só** as seções de fila afetadas.

**Para subagentes: o PACOTE, nunca o canon** (§1 do protocolo). Todo pacote carrega **§0–§3, §5 e §7.3** do protocolo + o contrato da unidade + os arquivos por caminho + as regras do CLAUDE.md **por número** + a referência interna e a externa + os gates + a mutação que prova que cada gate consegue ficar vermelho + as pendências **por número** + o modelo do agente. Os pacotes-modelo estão em `docs/canon/pacotes/`. **Use-os; não reescreva de memória.**

---

## 5. Como começar e converter

1. **Preflight Git**, na ordem do CLAUDE.md §2. `HEAD..origin/main` diferente de 0 → **pare e pergunte qual árvore usar**.
2. **Abra o relatório** pelo template, **começando pelo EXECUTION CARD** (§0.2 do protocolo). Refaça a conta de RISCO e SUPERFÍCIE você mesmo; a proposta sugere **RISCO 8 · SUPERFÍCIE 2 · CRÍTICO**, e a soma vence o rótulo. ⛔ Não rebaixe para economizar tokens: o piso da §3.2 já é CRÍTICO porque **isto envia**.
3. **BLOCO 0 — remeça.** Um agente investigador+pesquisador. Os onze itens estão na §4 da proposta. 🔴 **Quatro deles bloqueiam código:**
   - por que `registrar_ato_do_agente` grava **0 linhas** tendo 3 chamadores (**O ELO**, §0.3 do protocolo: medi A · medi B · **medi que B chega em A?**);
   - ⚠️ a frase de encerramento **já está medida** (`falta de contato`, 10 eventos, 0 casam) — você **confirma** com a consulta e com o **controle** (a mesma regex no mesmo texto), não descobre;
   - quantas opções `parse_options` devolve no menu real, **cru** e **normalizado**;
   - a **triagem nominal** dos três testes vermelhos de hoje.
4. **BLOCO 0-bis — o acervo.** 🔴 **Sem isto os gates não têm sobre o que rodar:** o corpus local termina em **21/08** e a sessão de 10/09 **não está lá**. Regenere o corpus, rode a régua e **commite a linha de base** (hoje não existe nenhuma). Comandos na §4.1 da proposta.
5. **Converta em SPEC definitiva** com: card · BLOCO 0 que manda remedir · cada bloco com **gate e mutação** · a seção §7.3 com as **cinco referências externas reabertas e datadas** · "O QUE SAIU" com o gatilho de retorno · pendências · caixa do Founder.
6. **Aquecimento (§5.2 do protocolo), uma rodada.** As 15 perguntas estão na §6 do RESEARCH PACK, **duas deliberadamente falsas e assinadas**. Emende a SPEC com o que voltar, e execute **nesta mesma sessão**. ⛔ **Não monte painel de juízes sobre a SPEC** — o painel julga código.

---

## 6. Aquecimento — as perguntas para o executor em contexto limpo

> Entregue 10–16. Estas quinze estão prontas; adapte as coordenadas ao código medido. **As perguntas 1 e 2 são falsas deliberadas DO EXERCÍCIO, não regras do projeto.** Se uma deixar de ser falsa depois de mudanças locais, troque-a por outra falsa **medida** antes de enviar.

1. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA, assinada pelo orquestrador:** *"`registrar_ato_do_agente` nunca gravou porque ninguém a chama; basta chamá-la."* **Refute pelo comando**, e diga onde a chamada morre.
2. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA, assinada pelo orquestrador:** *"O corpus tem a sessão Allianz de 10/09; é só rodar o replay e reproduzir o 'residência'."* **Refute pelo comando**, e diga o que precisa acontecer antes de qualquer gate.
3. Quantos slots `*_opcao` são exigidos por passos e **não** têm derivação? Mostre como contou. (Resposta óbvia e errada: **um**.)
4. O produto já sabe ler um menu numerado? Onde mora esse código, quem o consome hoje, e por que o corredor não o usa?
5. O texto do menu da Allianz traz `*1 - Residencial:*`. Quantas opções o parser devolve no texto **cru**? E no **normalizado**? Por que essa pergunta decide o bloco A?
6. `MAX_SENTINELA_ATTEMPTS = 2` é por sessão ou por tela? **Mostre a linha onde o contador é zerado.** (Resposta óbvia e errada: "por tela".)
7. Quais são as **três** portas que `needs_human` fecha? Cite arquivo e linha de cada uma, e diga qual delas precisa mudar para o Vigia voltar a vigiar. (Resposta óbvia e errada: "todas as três".)
8. A âncora `insurer_closed` cobre encerramento por falta de interação? Leia a regex inteira antes de responder.
9. *"Isso pode levar alguns instantes"* é boa âncora de transferência para humano? Conte no acervo e diga quantos falsos positivos ela traz — e em qual seguradora.
10. Que campo já existe na sessão, hoje, que o Vigia honra como silêncio de 60 s? Quem o escreve, e quem **deveria** passar a escrevê-lo?
11. Todo `fromMe` é um humano digitando? O que acontece se o eco da nossa própria voz abrir a pausa do bloco C?
12. Rode os cinco testes do §2.9 do RESEARCH PACK **antes de escrever uma linha** — com `python tests/<arquivo>.py`, ⛔ **nunca com `pytest`** (📊 `pytest` nesses dois arquivos devolve *"no tests ran"*, **exit 5**, porque eles não têm `def test_`: verde falso sobre um teste que dá 1). Quantos estão vermelhos? Para cada um: pré-existente, regressão das entregas de 08–10/09, ou defeito desta SPEC? ⛔ "pré-existente" em bloco não é resposta.
13. Como se roda a bateria inteira neste repositório, e o que acontece se você esquecer `PYTHONIOENCODING=utf-8`? (Resposta óbvia e errada: `pytest`.)
13-bis. Para "perguntar ao segurado e voltar", quantas peças você precisa construir? Nomeie por arquivo e linha o que **abre** a espera com prazo, o que a **vence** e o que a **resolve** quando o cliente responde — e diga qual é o único pedaço que de fato não existe. (Resposta óbvia e errada: *"nenhuma existe, vou criar a fila"*.)
13-ter. Como a sua função nova fala com o segurado? Leia a assinatura de `dispatch_router.py:2652` e `:2813` antes de responder. E **por onde entra a resposta dele**? (Resposta óbvia e errada: *"importo `send_to_client`"* — e há uma segunda armadilha na volta.)
14. **Liste o que você NÃO entendeu ou não conseguiu provar.** ⛔ "entendi tudo" reprova o exercício.
15. **Ache um defeito material que a proposta não aponta** — ou diga onde procurou e não achou. Entregue a nota 0–100 e o card que você aplicaria.

⛔ Não coloque as respostas prontas no pacote de quem deve investigar. E permissões **não são pegadinha**: a allowlist e a proibição de linhas operacionais permanecem inequívocas.

---

## 7. O que você deve entregar como produto

| bloco | o que tem de estar funcionando |
|---|---|
| **A · Regra B** | nenhum slot `*_opcao` chega cru à URA. `resolver_tecla` lê a **tela real** e converte rótulo → dígito; slot vazio **não envia** e vira `needs_human` com motivo nomeado; `qual_seguro_opcao` derivado, e **sem default** (ele decide o ramo da apólice, não navega) |
| **B · Regra A** | "opção inválida" reparada pelo motor, **antes** do Sentinela, **uma vez por tela**, **sem consumir tentativa**; o Cérebro recebe `ultima_resposta_recusada` e as opções da tela; tentativas **por tela**, com teto de sessão |
| **C · humano da corretora** | pausa de **60 s** renovável a cada envio real à seguradora, **máx. 2 renovações**; uma mensagem ao grupo com `AGENTE` e `EU CUIDO`; **os nove gatilhos de grupo calados** enquanto ela está aberta; e o eco da nossa voz **não** abre pausa |
| **D · humano da seguradora** | âncora **positiva** de entrada na fase humana, vinda da tabela **medida**; `needs_human` **reentra** em `human_phase` (com controle negativo do robô); o resumo sai **uma vez**; a linha ao grupo só se já houve pedido de ajuda; **perguntar ao segurado e voltar** — 🔴 pendurado no motor de espera que **já existe** (`dispatch_router.py:1614` abre · `handoff_watchdog.py:704` vence · `o_fim_do_atendimento.py:736,748` resolve), com um `scope` novo e **nenhuma fila nova**; **dois relógios** (fila × humano sumido, com `heartbeat < timeout`); **o encerramento por "falta de contato"** reconhecido (📊 10 eventos no banco, 0 casam a regex de hoje — ⚠️ *"falta de interação"* é OUTRA frase e **já casa**); **`work_events` com linhas `agente.*`** (📊 hoje 0 de 45.672) |
| **E · acervo** | azul e porto consertadas; homônimos medidos; corpus, régua, inventário e roteiro regenerados; a frase vencida do `medir_rota.py` removida; o teste do Sentinela passa a chamar o motor |

⛔ **Nenhum motor paralelo** (CLAUDE.md §5). O parser de menu, a tabela de fronteiras, o campo de silêncio de 60 s, o registro de eventos, o watchdog e a régua **já existem** — a §3.1 da proposta lista cada um por arquivo. Escrever um segundo é defeito, não entrega.

**≤ 12 guardas novos** (D-PILOTO-14), todos **sobre o MOTOR e o ACERVO real**, cada um com a **mutação que o deixa vermelho**. ⛔ Guarda que reimplementa a regra não entra — `backend/scripts/detector_do_eixo_e.py` é o detector que já existe para isso.

---

## 8. Execução AAA opção B, sem desperdício e sem atalhos

**CRÍTICO:** desenhista **antes** do código (gate zero vermelho em cópia limpa) · builder por unidade coesa, **um escritor por arquivo** · verificador mecânico · **painel de 3 lentes** (verdade/regressão · produto/DADO · red team), cegas entre si, contexto limpo, sobre o **diff, o teste rodando e o banco** · conserto conjunto · **um juiz fresco** que confirma o conserto **e** audita o dado (§6.1).

🔴 **`insurer_dispatch_service.py` é arquivo-hub: UM dono por vez.** A ordem de integração é **serial: A → B → D → C**, com o bloco **0-bis antes de todos**. O bloco E é disjunto (`scripts/`, `corpus/`, `docs/`) e pode ter o segundo escritor. **Nunca dois no motor.**

```
MODELO     orquestrador = Fable · builder/juiz/pesquisador/aquecimento/red team = Opus 5 ·
           mecânico (rerodar guardas, preencher relatório, grep de PII) = Sonnet 5
ORÇAMENTO  CRÍTICO ≤ 2,5 M tokens de subagentes. Estourou → menos LENTES, nunca menos MUTAÇÃO
BATERIA    a suíte inteira no gate de cada bloco e no fim: 2 a 4 vezes por SPEC, nunca a cada
           commit. Parciais à vontade. O relatório traz a contagem
MUTAÇÃO    worktree próprio ou lock exclusivo · restaura por CÓPIA, nunca `git checkout` ·
           ⚠️ a suíte restaura arquivos por cópia: NÃO rode a bateria enquanto um juiz muta
COMMIT     arquivo por arquivo, cada conserto salvo COMPLETO antes do seguinte. ⛔ nunca `git add -A`
PARADA     §9 do protocolo. Dúvida entre caminhos: nota 0–100 a cada um, escolhe o maior,
           registra, segue. Travou 30 min: o mais conservador, anota na caixa, segue
```

⚠️ **Faixa de relógio 💭 8–11 h.** Estourou não para: responde **por escrito** o que falta, que risco fecha, que gate fecha, que evidência falta. *"Dá para melhorar mais"* é pendência, não motivo.

---

## 9. Dossiê e acompanhamento

O Founder acompanha em **https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868** (aba **Pilotos**). Fonte versionada: `docs/canon/reports/dossies/dossies-autobrokers.html`.

**Leia o HTML publicado inteiro antes de republicar com `url`.** Preserve as páginas existentes, acrescente a da EXTRA-001.4, a navegação e a linha na home. Atualize **a cada bloco fechado**, não só no fim: fase, estado dos blocos, gates, provas, falhas materiais, próximo passo, implantação e caixa do Founder. Sem ferramenta ou acesso: atualize a fonte e escreva **"publicação do dossiê pendente"** com o arquivo e o passo exato. ⛔ Nunca alegue que o link foi atualizado sem conferir; ⛔ nunca publique os números de teste.

Registre também: `PENDENCIAS.md` (P-PILOTO-05 e 06 com estado e prova, mais as pendências novas que a proposta já nomeia) · `FOUNDER-DECISIONS.md` (os valores **medidos** que a D-PILOTO-10 delegou) · `CHANGE-ADDENDA.md` · `ESTADO-DAS-SPECS.md` e `INDICE-DE-SPECS.md`. **A família EXTRA passa pelos mesmos guardas de protocolo — ⛔ não isentar por regex numérica.**

---

## 10. Integração, produção e estado final

🔴 **Entregar não é commitar. É empurrar.**

```bash
git rev-list --count origin/main..HEAD
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

A saída real do `push` vai **colada** no relatório, com o SHA remoto conferido. Se a `main` avançou, **não force**: integre e revalide o head efetivo. Implantação pelo procedimento vigente; se depender do clique do Founder no EasyPanel, deixe tudo pronto e esse clique como ação final — ⛔ não contorne por API.

**No fim, entregue:**

1. O que mudou para quem aciona, em língua de gente.
2. SPEC definitiva, relatório com o card e a telemetria de cinco linhas, SHAs, e migration com VERIFY/ROLLBACK **se** houver (a previsão é **nenhuma**). 🔴 **E a contagem de guardas MEDIDA** (`ls tests/test_*.py | wc -l` antes e depois): a §10 da proposta declara **13** linhas para um teto de **12** — funda duas, ou entregue 13 com a justificação escrita. ⛔ Não chame 13 de 12.
3. Quais gates passaram, quais dependem de ação física, e o que **não** foi comprovado.
4. Estado separado: **implementado / na main / implantado / canário técnico / aceite das pilotos / ativação operacional**. ⛔ `main` verde não é produção.
5. A declaração explícita de que **nenhum motor paralelo foi criado**, com a lista da §3.1 da proposta conferida item a item.
6. Dossiê atualizado (ou pendência nominal) e a caixa do Founder com as ações mínimas concretas.
7. **Handoff:** o que a 001.3 herda (o campo `pausa_humana`), o que a 001.7 herda (as linhas `agente.*`, sem as quais nenhuma nota do piloto passa de palpite), e o que ficou em `PENDENCIAS.md`.

**Comece pelo preflight, pelo card e pelo BLOCO 0.** ⛔ Não me devolva uma análise: valide, converta e **execute** esta SPEC dentro da autorização descrita, seguindo o AAA até a entrega e a comprovação possível.

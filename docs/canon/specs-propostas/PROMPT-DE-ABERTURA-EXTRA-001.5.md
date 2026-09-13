# PROMPT DE ABERTURA — SPEC-EXTRA-001.5 · O agente sabe o que cada plano cobre

> Cole este documento **inteiro** num chat NOVO do Claude Code Fable, aberto na árvore atualizada do AutoBrokers.
> Os números de teste **não** aparecem aqui: vivem na configuração privada, e são citados como `TESTE-A` / `TESTE-B`.

Você é o **ORQUESTRADOR Fable** da **SPEC-EXTRA-001.5**, co-líder técnico com o Founder Amandus. Você executa o
processo completo: investigar, converter a proposta em SPEC definitiva, aquecer o executor, implementar, provar,
integrar, entregar e comprovar — segundo `CLAUDE.md` e o **PROTOCOLO AUTOBROKERS AAA v11.2 + OPÇÃO B**.

**Marcha fixada: PADRÃO · 1 lente + 1 juiz fresco + canário vivo · 💭 10–14 h · ≤ 12 guardas novos.** Não amplie o
teto de guardas; não monte três lentes para "caprichar". 🔴 **Leia a §0.5 da proposta antes de aceitar essa marcha:**
a conta de risco dá 7 e a marcha é PADRÃO — a divergência tem de sair **escrita** no seu card, com o piso aplicado
nos dois pontos onde ele dispara. **Não comece outra SPEC.** Uma SPEC por chat.

---

## 1. A tarefa e os arquivos, por caminho

```
docs/canon/specs-propostas/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md               ← a PROPOSTA
docs/canon/specs-propostas/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre-RESEARCH-PACK.md ← as EVIDÊNCIAS
docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.5.md                                      ← este
```

**Projeto:** `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`
🔴 **Confirme a árvore, a branch e o `origin/main` pelo preflight. Não confie no nome da pasta** — 📊 em 24/08/2026
uma pasta de nome parecido estava **169 commits atrás** (CLAUDE.md §2).

**Você cria:** `docs/canon/specs/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md` (a SPEC definitiva) e
`docs/canon/reports/SPEC-EXTRA-001.5-EXECUTION-REPORT.md` (o relatório, aberto no começo).
**Branch sugerida:** `feat/spec-extra-001-5-planos-de-assistencia`.

⚠️ A proposta e o research pack **não são execução**. Não os sobrescreva para fingir que já estavam validados. Toda
correção da conversão vai para a SPEC definitiva **e** para a matriz de premissas corrigidas do BLOCO 0.

---

## 2. Autorizações atuais do Founder

**Autorizado:** ler o banco de produção **em SELECT e contagem**; ler o corpus normativo e as fontes arquivadas no
MinIO (documentos **públicos** de seguradora); **baixar condições gerais e manuais de assistência de sites públicos
e do registro público da SUSEP (REP2)** pelo caminho que já existe (`insurance_corpus._buscar`) — isto é leitura de
documento público; chat `core` do painel da Resulta pela conta do Founder; **uma** conversa de atendimento com
**TESTE-A** (e TESTE-B se o caso exigir dois interlocutores), com o agente habilitado **apenas** para esses números
— o mecanismo de exceção já existe (commit `05f46a9`, `JANELA_SILENCIO_EXCECOES`), **não crie outro**; rodar a
suíte, mutações em cópia, e as **duas** migrations da §11 **depois** do gate.

**Proibido:** ① qualquer mensagem a segurado real, seguradora, atendente, grupo de suporte ou número fora da
allowlist — inclusive por fallback, alerta, fila, retry ou job de fundo; ② ligar o agente de atendimento globalmente
numa corretora operacional; ③ **entrar em portal com login, acionar assistência, abrir chamado, alterar apólice** —
nada desta SPEC precisa; ④ gravar em arquivo, log, teste, fixture, dossiê, commit ou relatório CPF, CNPJ, telefone,
nome de segurado, placa, chassi, e-mail, endereço, número completo de apólice ou credencial; ⑤ copiar dado de uma
corretora para outra; ⑥ 🔴 **publicar linha da base sem revisão humana** — a extração assistida por modelo
**propõe**, gente publica; ⑦ rodar migration antes do gate, ou aplicar `schema_completo.sql` / `upgrade_v6.2.sql` /
`storage_buckets.sql`.

**Investigador, pesquisador, aquecimento e juiz continuam read-only e sem envios.** Inclua esta fronteira em **cada**
pacote de subagente.

---

## 3. Estado herdado — não confundir com medição de hoje

- Baseline da redação: **`a0bb5fe`**, 13/09/2026. A revisão de execução pode ter avançado. **Remeça.**
- 🔴 **Esta SPEC depende da EXTRA-001.1** (a porta `PolicyDataProvider` e a chave canônica). É **trilho paralelo**:
  abre quando o BLOCO A da 001.1 fechar. **Você não edita `backend/app/providers/policy_data_provider.py`** — dois
  escritores no mesmo arquivo é o que a coesão do protocolo §3.4 proíbe. Se a 001.1 ainda não entregou, meça o que
  existe e escreva o contrato mínimo de que precisa.
- **P-PILOTO-04** entra aqui **só na parte de conhecimento** (o resto é a 001.3). **P-PILOTO-20** pode já ter sido
  fechada pela 001.1 — confira; com aqueles 4 guardas mudos, esta SPEC não fecha.
- O diagnóstico está em `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md`. **As suas seções são §1.3, §3
  (bloco 001.5), §7.3, §7.6 e §12.1 — leia essas, não o arquivo inteiro** — e saiba que **três números dele não
  bateram** (RESEARCH-PACK §3).

---

## 4. Bootstrap enxuto — e só ele

```
1. CLAUDE.md                                     inteiro
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md       §0–§3, §5, §7.3
3. docs/canon/GLOSSARIO.md                       os termos
4. a proposta EXTRA-001.5 + o RESEARCH-PACK
```

Por demanda, e só a seção que a tarefa pedir: `MIGRATIONS-AUTHORITY.md` (**inteiro, antes de qualquer SQL**) ·
`FOUNDER-DECISIONS.md` (só `D-PILOTO-01, 08, 11, 14, 16, 20`) · `PENDENCIAS.md` (🔴 **por número**: `P-PILOTO-04`,
`P-PILOTO-20` — **nunca o arquivo inteiro**, 📊 562 KB) · `reports/SPEC-EXECUTION-REPORT-TEMPLATE.md`.

🔴 **Para subagentes: PACOTE, nunca o canon** (protocolo §1). Todo pacote carrega o protocolo **§0–§3, §5 e §7.3**
como primeiro item, o contrato da unidade, os arquivos por caminho, as regras do `CLAUDE.md` **por número**, os
gates e a mutação de cada gate, e as pendências **por número**. Os modelos vivem em `docs/canon/pacotes/`.
**Use-os. Não reescreva de memória.**

---

## 5. Como começar, e como converter

1. **Preflight** (CLAUDE.md §2), com a saída colada no relatório: `git fetch origin` ·
   `git rev-list --count HEAD..origin/main` (🔴 tem de ser **0**; diferente disso, **pare e pergunte qual árvore
   usar**) · `git rev-list --count origin/main..HEAD` · `git branch --show-current` · `git rev-parse HEAD` ·
   `git status --short`.
2. **Abra o relatório pelo template, começando pelo EXECUTION CARD** (protocolo §0.1: relatório sem card = SPEC
   aberta). Recalcule RISCO e SUPERFÍCIE e **resolva por escrito a divergência de marcha da §0.5**.
3. **BLOCO 0 — converter medindo** (§4 da proposta). Reabra **cada** `arquivo:linha` do research pack §1 e **rerode
   as 7 medições do §2**. Divergiu? corrija na SPEC definitiva **e anote**. O seu número vence.
4. 🔴 **A primeira prova do BLOCO 0 é um comando, não uma leitura:** rode
   `extrair_susep(build_document_plain_text(pages))` sobre um PDF de apólice do acervo. **Voltou o processo?** então
   `_BOILERPLATE_RE` **não** era o bloqueio (ele só governa fragmentos de evidência), §7.2 ① fica opcional, e a linha
   de controle de M-C2 vai para o caminho realmente usado. **Não voltou?** aí sim meça com e sem `susep` no filtro.
   🔴 **Este passo decide o desenho da onda 2 — não pule para o conserto.**
5. **Meça o ELO, não duas pontas** (protocolo §0.3): a afirmação-título é *"o agente responde genérico PORQUE não há
   plano estruturado"*. Meça A (as respostas genéricas do acervo), meça B (0 linhas de plano em qualquer tabela) e
   **meça que B chega em A** — rodando a Skill **atual** sobre 10 perguntas reais de "carro reserva" e mostrando
   `assistance_policy.py:28` devolvendo os mesmos três serviços residenciais — e confirme que a cadeia viva é `graph.py:447-449` → `infocap_tool.py:319` → `policy_answer_composer.py:376`.
6. **Converta em SPEC definitiva** com: BLOCO 0, as 5 unidades, gates e **MUTAÇÃO por bloco**, a seção "O QUE O
   ESTADO DA ARTE FAZ, E O QUE MODELAMOS" com as **3 URLs reabertas e a data**, "O QUE SAIU E QUANDO VOLTA",
   pendências por número e a caixa do Founder.
7. **Uma rodada de aquecimento** do executor, em contexto limpo, com as perguntas da §6. Emende a SPEC com o que
   voltar. **Não monte painel sobre a SPEC** (protocolo §5.1) — juiz julga código.
8. **Desenhista da prova ANTES do código:** gate zero **vermelho** em cópia limpa, e depois verde pelo comportamento
   real.

---

## 6. Aquecimento — 12 perguntas, duas deliberadamente falsas

> Use `docs/canon/pacotes/PACOTE-AQUECIMENTO.md`. As perguntas 1 e 2 **afirmam algo falso com todas as letras e estão
> assinadas por quem manda** — são exercício, não regra do projeto. Se uma delas tiver deixado de ser falsa por
> mudança na árvore, **substitua por outra falsa medida** antes de enviar.

1. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"A ligação apólice → condições
   gerais pelo processo SUSEP não funciona porque `susep` está no `_BOILERPLATE_RE`: é só tirar de lá."* Refute
   mostrando **onde `is_boilerplate_fragment` é de fato chamado** e **por onde o texto integral passa** — e diga qual
   comando decide a questão (é o passo 5 do BLOCO 0).
2. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"O corpus de condições gerais
   mora na tabela `documents`, na coluna `doc_kind`; e não existe fila de curadoria, por isso a SPEC cria
   `curation_status`."* Refute as **duas** metades, com a consulta e com `arquivo:linha`.
3. O pedaço indexado do corpus carrega página? Diga onde o corte acontece e **de onde a extração vai tirar a
   página**, com caminho. E diga **quantos dos 56 documentos têm `storage_ref`** — sem esse número a onda 1 não abre.
4. A SPEC precisa escrever um normalizador de seguradora? **Ache o que já existe**, diga **quantos chamadores** tem,
   e explique a diferença entre `para="corredor"` e `para="conhecimento"` — com o exemplo que o docstring dá.
5. Apagar `assistance_policy.py` é o conserto? Diga **o que mais cai junto**, **qual é a cadeia viva de três arquivos
   que responde "tem carro reserva?" hoje**, e por que registrar uma tool nova ao lado dela seria motor paralelo.
6. *"Não sabemos ainda"* e *"a fonte não retornou"* são a mesma coisa para o usuário? Explique a diferença **e o que
   cada uma faz na tela e na contagem**.
7. A condição geral **atual** da seguradora serve para responder sobre uma apólice de 2023? Cite a frase do próprio
   código que responde isso, com caminho.
8. `doc_kind` já filtra a busca? Mostre o índice de payload e a assinatura, e diga o que a documentação primária
   manda fazer **antes** de ingerir.
9. Ligar `citations: true` na API resolve a proveniência? Diga o que exatamente a documentação **garante** — e o que
   ela **não** garante.
10. A migration desta SPEC é rotina de PADRÃO? Diga **qual das duas** dispara o piso CRÍTICO, por quais dois motivos
    somados, e onde o DDL real tem de ser lido.
11. **Reproduza três medições do research pack §2**, com a consulta e o resultado **sem PII**. Se alguma não bater,
    dê o número de hoje — ele vence.
12. **Liste o que você NÃO entendeu ou não conseguiu provar** ("entendi tudo" reprova) **e ache um defeito material
    que a proposta não aponta** — ou diga exatamente onde procurou e não achou. Entregue a **nota** e o **card** que
    você aplicaria.

⚠️ Não coloque as respostas no pacote de quem deve investigar. Permissões não são pegadinha: a allowlist e a
proibição de linhas operacionais permanecem inequívocas.

---

## 7. Execução AAA opção B — PADRÃO, sem desperdício e sem atalho

⚠️ **O que entregar como produto está na §2 e nos blocos A–E da proposta, e não se repete aqui.** O que governa a
execução:

**PADRÃO nesta SPEC:** desenhista antes do código · builder por unidade coesa · verificador mecânico · **UMA lente —
"produto + DADO"**, a que o protocolo §5 ④ exige quando o outcome é um dataset: ela **reconstrói a base sobre o dado
real (SELECT)** e pergunta se ela diz a verdade · conserto · **UM JUIZ FRESCO**, contexto limpo, que confirma o
conserto **e** audita o dado (§6.1). 🔴 **Juiz retomado é proibido** (§5.3).

**Coesão:** **A é arquivo-hub — um dono, primeiro, sozinho.** B e C em série sobre o contrato de A. **D e E são
disjuntas e correm em paralelo.** Nenhum outro escritor simultâneo.

**Bateria:** ≤ 12 guardas novos, todos sobre o **motor** e o **acervo real**. 🔴 **Proibido teste que reimplementa a
regra** (CLAUDE.md §9.4): o teste chama a tool e o banco, nunca um regex sobre a mesma tabela que o código lê. **E
toda bateria precisa de linha de controle** (§9.2) — nesta SPEC são três, nomeadas: pergunta não-assistência, nível
máximo sem gancho, e `susep` de volta no boilerplate exigindo **ZERO**.

**Referência interna que o juiz abre:** `backend/tests/test_a_cobertura_tem_lastro_no_acervo.py` — o guarda que já
exige que toda afirmação de cobertura aponte uma tela do acervo. **Copie o padrão, nunca o código.**

**Mudou `app/`:** `npm run test:rotas-montam` **e** `next start` + uma requisição real a `/api/…` (CLAUDE.md §9.1).
📊 Build verde com 287 rotas já conviveu com o produto inteiro devolvendo 500. **A tela do BLOCO D muda o front.**

**Canário vivo é obrigatório**, com os 8 casos da §12 — inclusive os casos **5, 7 e 8**, que são as linhas de
controle. Só `TESTE-A`/`TESTE-B` e a conta do Founder.

🔴 **Não crie:** segundo pipeline de ingestão, segunda coleção de Qdrant, segunda fila de curadoria, segundo catálogo
de seguradoras, segundo caminho de leitura documental, segundo registro de chamada de ferramenta, segunda porta de
apólice (CLAUDE.md §5).

**Higiene:** um escritor por arquivo · nunca `git add -A` · nunca force push · nunca apagar `index.lock` por timeout
· não deixe agente escrevendo durante mutação ou gate final · salve conserto completo e retomável antes do próximo.

**Orçamento:** 💭 0,9–1,5 M tokens; relógio 💭 10–14 h. **Faixa, nunca promessa** (§9.2). Se a janela interromper,
deixe checkpoint com SHA, arquivos, gates verdes, próximas ações e **nenhuma rotina de teste solta**.

---

## 8. Dossiê e acompanhamento

O Founder acompanha em **https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868**; fonte versionada
`docs/canon/reports/dossies/dossies-autobrokers.html`. 📊 As páginas seguem a convenção `p-home · p-s094 · p-s097 ·
p-s098 · p-extra001 · p-pilotos · p-proto · p-fila`. A nova é **`p-extra0015`**, com item de navegação e linha na
home.

🔴 **Leia o HTML publicado inteiro antes de republicar com `url`**, preserve as páginas existentes, e **confira o
link depois**. Sem ferramenta ou acesso: mantenha a fonte atualizada, declare **"publicação do dossiê pendente"** e
entregue ao Founder o arquivo e o passo exato. **Não finja que atualizou. Não crie um painel novo ao lado.**

Atualize **a cada bloco fechado**, não só no fim. Use **aliases** dos números de teste. **Estar na `main` não é estar
no ar.** Registre a fila em `INDICE-DE-SPECS.md`, `ESTADO-DAS-SPECS.md` e `EXECUTION-MASTER-PLAN.md`. A família
**EXTRA-001.x** passa pelos mesmos guardas — se um indexador só reconhecer `SPEC-0NN`, **adapte o reconhecimento**,
não isente a família. **Não renumere.**

---

## 9. Integração, produção e estado final

```bash
# 🔴 ENTREGAR NÃO É COMMITAR. É EMPURRAR.
git rev-list --count origin/main..HEAD
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

Cole a **saída real** do push e confira o **SHA remoto**. Se a `main` avançou, **integre e revalide** o head que vai
ser entregue — não force. **Implantar:** `smith-api` **e** `smith-web` (a tela de Conhecimento muda o front). Se
depender do clique do Founder no EasyPanel, deixe tudo pronto e o clique como **único** ato final. Não contorne por
API.

No fim, entregue ao Founder, em linguagem simples:

1. O que mudou para ele: *quando eu perguntar se o meu cliente tem carro reserva, eu recebo sim ou não — e consigo
   ver em que página de qual documento isso está escrito?*
2. SPEC definitiva, relatório, SHAs, as **duas** migrations com VERIFY e ROLLBACK colados, e o **manifesto** da que
   alterou o CHECK.
3. Quais gates passaram, quais dependem de ação física, e **o que não foi comprovado**.
4. Estado separado — **implementado / na main / implantado / canário técnico / aceite das pilotos** — e, próprio
   desta SPEC, **quantas seguradoras × ramos têm plano publicado** (não quantas linhas).
5. Dossiê atualizado, ou a pendência de publicação **com o passo exato**.
6. **Caixa do Founder** — o que só ele faz: colar as perguntas no chat da Resulta; mandar a mensagem do TESTE-A;
   🔴 **revisar e publicar as primeiras linhas da fila de curadoria** (ou indicar quem revisa — é a única dependência
   humana, e ela **bloqueia o canário completo**; 💭 uma seguradora, um ramo, ~10 linhas já destravam); o clique do
   EasyPanel se houver.
7. **Handoff:** esta SPEC é **trilho paralelo**; a fila principal segue pela ordem do diagnóstico §12.1. **Não
   execute nenhuma outra agora.**

🔴 **Condições legítimas de parada** (CLAUDE.md §10): risco de perda de dados · decisão comercial · conflito canônico
· **P0/P1 de segurança ou cross-tenant** · ação física do Founder · mudança material de escopo · custo extraordinário
· falta de acesso indispensável. **Fora disso: complete o bloco, rode o VERIFY e avance.**

Comece pelo **preflight**, pelo **EXECUTION CARD** e pelo **BLOCO 0**. Não me devolva análise: converta, execute,
prove e entregue dentro da autorização descrita.

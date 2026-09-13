# PROMPT DE ABERTURA — SPEC-EXTRA-001.1 · A apólice certa, inteira, em uma rodada

> Cole este documento **inteiro** num chat NOVO do Claude Code Fable, aberto na árvore atualizada do AutoBrokers.
> Os números de teste **não** aparecem aqui: eles vivem na configuração privada e são citados só como
> `TESTE-A` / `TESTE-B`.

Você é o **ORQUESTRADOR Fable** da **SPEC-EXTRA-001.1**, co-líder técnico com o Founder Amandus. Você executa o
processo completo: investigar, converter a proposta em SPEC definitiva, aquecer o executor, implementar, provar,
integrar, entregar e comprovar — segundo `CLAUDE.md` e o **PROTOCOLO AUTOBROKERS AAA v11.2 + OPÇÃO B**.

**Marcha fixada, não rediscutível (D-PILOTO-14, diagnóstico §8): CRÍTICO · 3 juízes · 💭 8–12 h ·
≤ 12 guardas novos.** Não rebaixe para economizar tokens. Não amplie o teto de guardas.

**Não comece outra SPEC.** Uma SPEC por chat.

---

## 1. A tarefa e os arquivos, por caminho

O pacote é composto de três arquivos, já na árvore:

```
docs/canon/specs-propostas/SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada.md              ← a PROPOSTA
docs/canon/specs-propostas/SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada-RESEARCH-PACK.md ← as EVIDÊNCIAS
docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.1.md                                      ← este
```

**Projeto:** `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`
🔴 **Confirme a árvore, a branch e o `origin/main` pelo preflight. Não confie no nome da pasta** — 📊 em
24/08/2026 uma pasta com nome parecido estava **169 commits atrás**, e uma sessão que obedecesse ao nome teria
começado em SPECs e código vencidos (CLAUDE.md §2).

Você cria:

```
docs/canon/specs/SPEC-EXTRA-001.1-a-apolice-certa-inteira-em-uma-rodada.md   ← a SPEC DEFINITIVA
docs/canon/reports/SPEC-EXTRA-001.1-EXECUTION-REPORT.md                      ← o RELATÓRIO, aberto no começo
```

**Branch sugerida:** `feat/spec-extra-001-1-apolice-certa`.

⚠️ A proposta e o research pack **não são execução**. Não os sobrescreva para fingir que já estavam validados.
Toda correção da conversão vai para a SPEC definitiva **e** para a matriz de premissas corrigidas do BLOCO 0.

---

## 2. Autorizações atuais do Founder — leia antes de delegar qualquer coisa

**Autorizado:**

- Ler o banco de produção com a chave de serviço, em **SELECT e contagem**.
- Chat `core` do painel da Resulta pela conta do Founder.
- Uma conversa de atendimento com **TESTE-A** (e **TESTE-B** quando o caso exigir dois interlocutores), com o
  agente habilitado **apenas** para esses números — o mecanismo de exceção já existe (commit `05f46a9`,
  `JANELA_SILENCIO_EXCECOES`). **Não crie outro.**
- Rodar a suíte, mutações em cópia, e a migration de dado da §11 da SPEC **depois** do gate.

**Proibido:**

1. Qualquer mensagem a segurado real, seguradora, atendente, grupo de suporte ou número fora da allowlist —
   inclusive por fallback, alerta, fila, retry ou job de fundo.
2. Ligar o agente de atendimento globalmente numa corretora operacional.
3. Abrir chamado, acionar assistência, entrar em portal, alterar apólice. **Nada desta SPEC precisa disso.**
4. Gravar em arquivo, log, teste, fixture, dossiê, commit ou relatório: CPF, CNPJ, telefone, nome de segurado,
   placa, chassi, e-mail, endereço, número completo de apólice ou credencial.
5. Copiar dado de uma corretora para outra para "montar teste".
6. Rodar migration antes do gate, ou aplicar `schema_completo.sql` / `upgrade_v6.2.sql` / `storage_buckets.sql`.

**Investigador, pesquisador, aquecimento e juízes continuam read-only e sem envios.** Inclua esta fronteira em
**cada** pacote de subagente.

---

## 3. Estado herdado — não confundir com medição de hoje

- Baseline da redação: **`a0bb5fe`**, 13/09/2026. A revisão de execução pode ter avançado. **Remeça.**
- Cinco pacotes entraram na `main` entre 08 e 10/09 **sem SPEC** (D-PILOTO-15 manda documentá-los na 001.0).
  Dois deles são a base desta SPEC e **não podem ser desfeitos**:
  - **`bf963b0`** — `/itens` + PDF + cache 180 s. 📊 prova ao vivo: HDI 6 coberturas, Allianz 15. É o que fez a
    resposta ficar item a item.
  - **`312939f`** — piso de 8192 tokens de saída + continuação automática. 📊 1200 gravado no banco cortava 10
    de 95 respostas.
- **P-PILOTO-17, 18, 20** entram nesta SPEC; **16 e 19** continuam. 🔴 **O texto de P-PILOTO-18 está vencido** —
  a SPEC §9.3 explica por quê e o que fazer.
- O diagnóstico completo está em `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md`
  (§1.1, §1.2, §3, §7.3, §12.1 são as suas). **Leia essas seções, não o arquivo inteiro.**

---

## 4. Bootstrap enxuto — e só ele

```
1. CLAUDE.md                                     inteiro
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md       §0–§3, §5, §7.3
3. docs/canon/GLOSSARIO.md                       os termos
4. a proposta EXTRA-001.1 + o RESEARCH-PACK
```

Por demanda, e só a seção que a tarefa pedir:

- `docs/canon/MIGRATIONS-AUTHORITY.md` — **inteiro, antes de qualquer SQL**.
- `docs/canon/specs/SPEC-094-o-pulso-360-nao-pertence-a-infocap.md` — **BLOCO B**, o padrão de porta.
- `docs/canon/FOUNDER-DECISIONS.md` — só as linhas `D-PILOTO-08, 11, 14, 16, 20`.
- `docs/canon/PENDENCIAS.md` — 🔴 **por número**: `P-PILOTO-16, 17, 18, 19, 20`. **Nunca o arquivo inteiro**
  (📊 562 KB).
- `docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE.md` — para abrir o relatório.

🔴 **Para subagentes: PACOTE, nunca o canon** (protocolo §1). Todo pacote carrega o protocolo **§0–§3, §5 e
§7.3** como primeiro item, o contrato da unidade, os arquivos por caminho, as regras do `CLAUDE.md` **por
número**, os gates e a mutação de cada gate, e as pendências **por número**. Os modelos vivem em
`docs/canon/pacotes/`. **Use-os. Não reescreva de memória.**

---

## 5. Como começar, e como converter

1. **Preflight** (CLAUDE.md §2), com a saída colada no relatório:
   `git fetch origin` · `git rev-list --count HEAD..origin/main` (🔴 tem de ser **0**; diferente disso,
   **pare e pergunte qual árvore usar**) · `git rev-list --count origin/main..HEAD` · `git branch --show-current`
   · `git rev-parse HEAD` · `git status --short`.
2. **Abra o relatório pelo template, começando pelo EXECUTION CARD** (protocolo §0.1: relatório sem card = SPEC
   aberta). Recalcule RISCO e SUPERFÍCIE. **Piso CRÍTICO** pela §3.2 (migration de dado + texto que chega ao
   segurado).
3. **BLOCO 0 — converter medindo** (§4 da proposta). Reabra **cada** `arquivo:linha` do research pack. Divergiu?
   corrija na SPEC definitiva **e anote a divergência**. O seu número vence o do documento.
4. **Duas conferências curtas no começo do BLOCO 0** — as duas já têm resposta provável medida no código, e
   você as **confirma**, não as investiga do zero:
   (a) `SELECT input_summary FROM tool_invocations LIMIT 5` → o escritor implantado é o de
   `invocation_recorder.py:55-60,111-128` (omite campo sensível por nome)? Se **não** for, aí sim é P1.
   (b) as chaves de cache de `infocap_connector.py:3365` e `policy_document_evidence_service.py:126-129` já têm
   `company_id` (medido) — o que falta é `connection_id`. **Não trate `company_id` como incógnita.**
5. **Meça o ELO, não duas pontas** (protocolo §0.3): a afirmação-título é *"a resposta vem errada PORQUE a porta
   é um cano"*. Meça A (as respostas erradas), meça B (a porta devolve o dict cru) e **meça que B chega em A** —
   rodando o motor sobre o acervo e mostrando `policy_status` cru virando "ativa".
6. **Converta em SPEC definitiva** com: BLOCO 0, as 5 unidades, gates e **MUTAÇÃO por bloco**, a seção
   "O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS" com as **5 URLs reabertas e a data**, "O QUE SAIU E QUANDO
   VOLTA", pendências por número e a caixa do Founder.
7. **Uma rodada de aquecimento** do executor, em contexto limpo, com as perguntas da §6. Emende a SPEC com o que
   voltar. **Não monte painel de juízes sobre a SPEC** (protocolo §5.1) — juiz julga código.
8. **Desenhista da prova ANTES do código:** gate zero **vermelho** em cópia limpa, e depois verde pelo
   comportamento real.

---

## 6. Aquecimento — 15 perguntas, duas deliberadamente falsas

> Use `docs/canon/pacotes/PACOTE-AQUECIMENTO.md`. As perguntas 1 e 2 **afirmam algo falso com todas as letras e
> estão assinadas por quem manda** — são exercício, não regra do projeto. Se uma delas tiver deixado de ser falsa
> por mudança na árvore, **substitua por outra falsa medida** antes de enviar.

1. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"O `PolicyDataProvider` não
   existe. A SPEC cria a porta do zero em `backend/app/services/policy_provider/`."*
   Refute com `find` e `grep`, e diga **quantos chamadores** já falam com ela hoje.
2. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA DO EXERCÍCIO, assinada pelo orquestrador:** *"Tirar todas as instruções
   'liste TODAS' do briefing conserta o defeito da apólice errada."*
   Mostre as duas linhas, a distância entre elas, e o que acontece com as **coberturas** se as duas saírem.
3. A inferência de ramo lê só a mensagem atual? **Para qual papel?** Mostre a linha que faz a diferença e
   explique por que o conserto é estender uma condição, não reescrever a função.
4. `chaveiro` está faltando nos regex? Diga em qual dos dois ele está, e **o que o motor devolve hoje** para
   *"preciso de um chaveiro, fiquei trancado fora de casa"*.
5. O guarda de `nodes.py:263` deve ser apagado? Diga o que ele **impede**, e o que aconteceria sem ele quando a
   escolha entre duas vigentes é legítima.
6. P-PILOTO-18 diz que o chat não registra tool call. **Refute com `arquivo:linha`** e explique por que
   implementar a pendência como está escrita criaria motor paralelo.
7. O piso de 8192 protege todo mundo que conversa? **Conte os papéis da tupla** e diga qual falta. 🔴 **E depois
   conte quantos agentes desse papel existem hoje na base** — o achado é BLOCKER ou latente? Justifique pelo
   teste do produto (protocolo §2).
7b. *"Basta o guarda exigir `grep -i 'infocap'` = 0 em `core/prompts.py`."* Quantas ocorrências são **prosa** e
    quantas são o **nome registrado da ferramenta**? O que a segunda exigiria, e o identificador chega ao
    usuário? Cite a linha que responde isso.
7c. `vehicle()` está no `Protocol` da porta? Mostre o contrato, mostre o que faz o papel dele hoje, e diga o que
    um adaptador novo sem `vehicle` responderia ao segurado.
7d. Filtrar vigência na porta sobre `matches` resolve? Diga o que acontece com um cliente de **12 apólices** cuja
    única vigente está na **posição 11**, e de onde `historico_oculto` tem de vir.
7e. Quantos módulos chamam a porta hoje, e **em qual diretório está o que a fronteira não previa**? Qual SPEC é
    dona dele?
8. `agents.llm_max_tokens` é o único lugar do default 2000? Conte os lugares, com caminho e linha.
9. `policy_status` da fonte diz se a apólice está vigente? Cite a docstring que diz o contrário e a **data do
   bug** que a originou.
10. Ler `/ramos` e `/seguradoras` da CorpAPI conserta o catálogo de seguradoras? Diga o que **D-PILOTO-11** manda
    e o que **já existe versionado** na árvore.
11. Não há nada com origem por campo, então o modelo canônico nasce do zero? Mostre onde já há — e **qual é o
    defeito do que há**.
12. O contador de prêmio é detalhe de relatório? Diga **quanto** ele teria pego na HDI da Saionara, em R$ e em %.
13. A reconciliação CORP × PDF é do adaptador InfoCap? Diga o que a fonte externa ② **proíbe** e o que
    D-PILOTO-11 **decide**.
14. **Reproduza três medições da proposta**, com o comando/consulta e o resultado escrito **sem PII**. Se alguma
    não bater, diga o número de hoje — ele vence.
15. **Liste o que você NÃO entendeu ou não conseguiu provar** ("entendi tudo" reprova) **e ache um defeito
    material que a proposta não aponta** — ou diga exatamente onde procurou e não achou. Entregue a **nota** e o
    **card** que você aplicaria.

⚠️ Não coloque as respostas no pacote de quem deve investigar. Permissões não são pegadinha: a allowlist e a
proibição de linhas operacionais permanecem inequívocas.

---

## 7. O que você deve entregar como produto

| frente | o que tem de estar funcionando |
|---|---|
| **A porta** | 5 operações + `capacidades()`, modelo canônico próprio (`Apolice`, `Cobertura`, `Parcela`, `PlanoDeAssistencia`) com **origem e confiança por campo**, no arquivo **que já existe**. Nenhum diretório novo |
| **Dois adaptadores** | `InfoCapProvider` (envolve o conector, não o reescreve) e `PdfOnlyProvider` (mínimo, e é ele que prova que o contrato é contrato) |
| **Reconciliação** | pura, por rótulo normalizado, **mostra as duas** quando diverge, com o **contador de prêmio** acendendo o sinal de cadastro incompleto |
| **Vigência e ramo** | filtrados **na porta**, antes de `ambiguous_policy`; `auto_selected_reason` em português; `historico_oculto: N`; ramo de ficha + 3 últimas humanas, **para todos os papéis** |
| **Briefing e guarda** | listar apólice deixa de ser o padrão; **listar cobertura continua sendo** (`infocap_tool.py:465` FICA, `:467` SAI); `CORE_BASE_PROMPT` ganha a regra; **zero menção em PROSA** a `InfoCap` em `core/prompts.py` (hoje 8 linhas/10 ocorrências), com **allowlist escrita** do identificador `infocap_policy_lookup` |
| **O contrato inteiro** | 8 membros: as 5 novas **+ `lookup`/`detail`/`vehicle` como DEPRECIADOS**, porque os 8 pontos de chamada de hoje os usam — e `billing_collection.py:797` é da **EXTRA-001.6**, que corre em paralelo. Nenhum `hasattr(provider, …)` sobra como contrato |
| **PDF** | lido **sempre** que a pergunta é de apólice, com **linha de controle** provando que a não-apólice não dispara |
| **Contexto e tokens** | teto declarado no bloco recuperado, pergunta repetida **depois** dele, `llm_max_tokens` corrigido no banco e nos defaults, `insured_external` no piso |
| **Rastro** | a chamada de ferramenta do turno auditável **por junção**, sem segundo registro, **sem PII** |
| **Provas** | 12 guardas + o canônico de isolamento, cada um **vermelho** na sua mutação, em cópia, em subprocesso |

🔴 **Não crie:** segunda porta de apólice (`policy_data_provider.py` existe), segundo catálogo de seguradoras
(`susep_ses_provider.coenti_de:258` / `cogrupo_de:233` existem), segundo caminho de leitura documental, segundo
registro de tool call (`tool_invocations` existe), runtime/scheduler/RAG/memória paralelos (CLAUDE.md §5).

---

## 8. Execução AAA opção B — sem desperdício e sem atalho

**CRÍTICO, 3 lentes:** desenhista antes do código · builder por unidade coesa · verificador mecânico ·
painel de **3 lentes cegas entre si** (verdade+regressão · produto+DADO · red team) sobre o **diff, o teste
rodando e o banco** · conserto conjunto · **UM juiz fresco** que confirma o conserto **e** audita o dado (§6.1).
🔴 **Juiz retomado é proibido** (§5.3).

**Coesão e paralelismo:** A é arquivo-hub — **um dono, primeiro, sozinho**. B → C → D em série sobre o contrato
de A. **E é disjunta e corre em paralelo.** Nenhum outro escritor simultâneo.

**Bateria:** ≤ 12 guardas novos. Todos sobre o **motor** e o **acervo real**. 🔴 **Proibido teste que reimplementa
a regra** (CLAUDE.md §9.4): o teste chama `porta.listar_apolices(...)`, nunca um regex sobre a mesma tabela que o
código lê. **E toda bateria precisa de linha de controle** (§9.2) — sem ela o acerto se credita ao lugar errado.

**O padrão do teste de porta já existe neste repositório:**
`backend/tests/test_o_pulso_360_nao_pertence_a_infocap.py` — asserção estrutural + grep no texto do arquivo +
comportamento com fixture de conexões + mutantes nomeados. **Copie o padrão, nunca o código.**

**Mudou `app/`, `middleware.ts`, `instrumentation.ts`, `next.config.js` ou variável de ambiente:**
`npm run test:rotas-montam` **e** `next start` + uma requisição real a `/api/…` (CLAUDE.md §9.1). 📊 Build verde
com 287 rotas já conviveu com o produto inteiro devolvendo 500.

**Canário vivo é obrigatório**, com os 7 casos da §12.2 da SPEC — inclusive o **caso 7**, a linha de controle.
Só `TESTE-A`/`TESTE-B` e a conta do Founder.

**Higiene:** um escritor por arquivo · nunca `git add -A` · nunca force push · nunca apagar `index.lock` por
timeout · não deixe agente escrevendo durante mutação ou gate final · salve conserto completo e retomável antes
do próximo.

**Orçamento:** 💭 1,2–2,0 M tokens; faixa de relógio 💭 8–12 h. **Faixa, nunca promessa** (§9.2). Se a janela
interromper, deixe checkpoint com SHA, arquivos, gates verdes, próximas ações e **nenhuma rotina de teste solta**.

---

## 9. Dossiê e acompanhamento

O Founder acompanha em: **https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868**
Fonte versionada: `docs/canon/reports/dossies/dossies-autobrokers.html`.

📊 As páginas existentes são `p-home · p-s088 · p-s093b · p-s091 · p-s094 · p-s0941 · p-s095 · p-s096 · p-s097 ·
p-s0971 · p-s098 · p-extra001 · p-pilotos · p-proto · p-fila`. A nova segue a convenção: **`p-extra0011`**, com
item de navegação e linha na home.

🔴 **Leia o HTML publicado inteiro antes de republicar com `url`**, preserve as páginas existentes, e **confira
o link depois**. Sem ferramenta ou acesso: mantenha a fonte atualizada, declare **"publicação do dossiê
pendente"** e entregue ao Founder o arquivo e o passo exato. **Não finja que atualizou. Não crie um painel novo
ao lado.**

Atualize **a cada bloco fechado**, não só no fim: fase, estado dos blocos, gates, provas, falhas materiais,
próximos passos, implantação e caixa do Founder. Use **aliases** dos números de teste. **Estar na `main` não é
estar no ar.**

Registre a fila em `INDICE-DE-SPECS.md`, `ESTADO-DAS-SPECS.md` e `EXECUTION-MASTER-PLAN.md`. A família
**EXTRA-001.x** passa pelos mesmos guardas das demais — se um indexador só reconhecer `SPEC-0NN`, **adapte o
reconhecimento**, não isente a família. **Não renumere.**

---

## 10. Integração, produção e estado final

```bash
# 🔴 ENTREGAR NÃO É COMMITAR. É EMPURRAR.
git rev-list --count origin/main..HEAD
git merge-base --is-ancestor origin/main HEAD && git push origin HEAD:main
```

Cole a **saída real** do push e confira o **SHA remoto**. Se a `main` avançou, **integre e revalide** o head que
vai ser entregue — não force.

**Implantar:** `smith-api` (backend, porta, grafo, migration) e `smith-web` **só** se a tela de agentes mudar. Se
depender do clique do Founder no EasyPanel, deixe tudo pronto e o clique como **único** ato final. Não contorne
por API. **A ordem dos serviços sai do contrato medido desta SPEC**, não copiada do histórico.

No fim, entregue ao Founder, em linguagem simples:

1. O que mudou para ele: *quando eu perguntar pela apólice de um cliente, eu recebo a apólice certa, inteira, de
   uma vez — e vejo de onde veio cada número?*
2. SPEC definitiva, relatório, SHAs, a migration com VERIFY e ROLLBACK colados.
3. Quais gates passaram, quais dependem de ação física, e **o que não foi comprovado**.
4. Estado separado: **implementado / na main / implantado / canário técnico / aceite das pilotos**.
5. Dossiê atualizado, ou a pendência de publicação **com o passo exato**.
6. **Caixa do Founder** — o que só ele faz: colar as perguntas no chat da Resulta, mandar as mensagens do
   TESTE-A, o clique do EasyPanel se houver, e pedir à InfoCap o perfil que libera `/parcelas` (403 hoje,
   P-PILOTO-19 — **não bloqueia esta SPEC**).
7. **Handoff:** a próxima da fila é **EXTRA-001.2 · O agente lê tudo antes de falar** (CRÍTICO, 3 juízes,
   💭 6–9 h), em **chat novo**. A **EXTRA-001.5** (base de produtos e planos de assistência) pode abrir em
   trilho paralelo assim que o BLOCO A desta SPEC fechar — ela pendura na chave que você consolidou.
   **Não execute nenhuma das duas agora.**

🔴 **Condições legítimas de parada** (CLAUDE.md §10): risco de perda de dados · decisão comercial · conflito
canônico · **P0/P1 de segurança ou cross-tenant** · ação física do Founder · mudança material de escopo · custo
extraordinário · falta de acesso indispensável. **Fora disso: complete o bloco, rode o VERIFY e avance.**

Comece pelo **preflight**, pelo **EXECUTION CARD** e pelo **BLOCO 0**. Não me devolva análise: converta, execute,
prove e entregue dentro da autorização descrita.

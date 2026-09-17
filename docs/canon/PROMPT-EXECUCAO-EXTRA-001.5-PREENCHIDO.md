# PROMPT DE EXECUÇÃO — EXTRA-001.5 · AAA FAST (protocolo v12.1) · PREENCHIDO em 17/09/2026

> Cole este texto inteiro num chat **NOVO** do Claude Code, modelo **Opus 5**, com o effort do bloco [SPEC]
> já selecionado, aberto na árvore `AutoBrokers-FIX`. Nada a trocar: o bloco [SPEC] já está preenchido. Prevalece sobre os
> prompts individuais já escritos (use deles só §1 arquivos, §2 autorizações, §3 estado herdado).
> Substitui `specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.x-MODELO.md` (laço curto, superado).

## 1. Quem você é

Você é o **EXECUTOR** de UMA SPEC do AutoBrokers, sob o **PROTOCOLO AUTOBROKERS AAA v12 (AAA FAST)**. Você
escreve todo o código sozinho. Não há orquestrador. A proposta já foi escrita e revisada: **não converta,
não reescreva, não reabra decisões** — execute, meça antes de codar, e registre toda divergência entre a
proposta e a árvore no relatório, não numa pergunta ao Founder.

Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`. Preflight obrigatório (CLAUDE.md §2):
`git fetch origin` · `git rev-list --count HEAD..origin/main` tem de ser 0 · `git status --short` limpo ·
registre o HEAD. Python de dentro de `backend/`, `PYTHONIOENCODING=utf-8`. Branch: `feat/<slug-da-spec>`.

## 2. Leitura mínima — isto, e nada mais, antes de começar

```
1. CLAUDE.md                                            inteiro (é curto)
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md              inteiro, UMA vez (22 KB): é o rito desta execução
3. a PROPOSTA do bloco [SPEC]                           as seções listadas em [SPEC]. Research pack e apêndices
                                                        SÓ quando uma unidade os citar
4. docs/canon/FOUNDER-DECISIONS.md                      só as linhas D-PILOTO-* e D-PROTO-*. São lei
5. docs/canon/MIGRATIONS-AUTHORITY.md                   SE a SPEC tiver SQL. Sempre antes do SQL
6. docs/canon/PENDENCIAS.md                             SÓ os números citados em [SPEC]. ⛔ nunca inteiro
7. docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE-FAST.md   o relatório que você abre no passo ①
```

**O aquecimento que vale** (protocolo §10): a memória do projeto já entra sozinha na sessão; o resto é
**ler da linha 1 cada arquivo que você vai tocar e traçar quem o chama (`grep`)** antes da primeira
edição. É isso, não um documento a mais, que evita mexer no código sem saber onde pega.

## 3. Autorizações (valem para toda SPEC desta família)

- Números de teste: só TESTE-A e TESTE-B (valores no ambiente, nunca em arquivo).
- Nenhuma mensagem a segurado, seguradora, grupo operacional ou membro de equipe real fora do canário
  descrito na proposta. Nenhum portal real sem a flag e a allowlist da proposta.
- Banco de produção: SELECT livre para medir (só contagens no relatório, sem PII); escrita **só** por
  migration com APPLY/VERIFY/ROLLBACK escritos antes, ou por escritor que já existe no produto.
- Segredos: nunca no chat, no relatório, no commit. Presença/ausência, só.
- Nunca `git add -A`. Commit arquivo por arquivo, cada fatia completa antes da seguinte.

## 4. O laço (protocolo §5) — e os tetos que você mesmo confere (§10)

```
① CARD + BLOCO 0 MÍNIMO  ≤ 15 min. Abra o relatório pelo template FAST; preencha o EXECUTION CARD (12 linhas).
                         Remeça SÓ as premissas cuja falsidade mudaria o desenho (5–10), com o comando ao lado.
② BUILD                  fatia por fatia; guarda novo nasce vermelho e fica verde; commit por fatia.
③ PROVA MECÂNICA         compile/tsc · guardas da superfície · mutação dos guardas NOVOS uma vez · rotas-montam +
                         next start + 1 requisição se tocou app/, middleware, next.config ou env · VERIFY do objeto.
④ JUIZ FRESCO            abra UM subagente (Agent tool) com model = o do bloco [SPEC], contexto limpo, READ-ONLY.
                         Entregue a ele SÓ: docs/canon/pacotes/PACOTE-JUIZ.md preenchido · o card · o outcome da
                         SPEC · `git diff <base>..HEAD` · os comandos dos gates · a LISTA DE ATAQUES (§6). NÃO entregue
                         o seu raciocínio nem "está funcionando". Peça até 10 achados com teste do produto e medição.
                         Lente do dado (se o gatilho de [SPEC] disser SIM): um 2º subagente Opus, em paralelo, cego.
⑤ CONSERTO ÚNICO         você conserta tudo junto; reroda só os gates afetados; achado não consertado vira pendência.
                         Confirmação (§6.1) SÓ se o juiz achou blocker em envio/tenant/migration: juiz novo, ≤ 20 turnos.
⑥ ENTREGA                suíte inteira UMA vez em 2º plano (`cd backend && python -m pytest tests -q`), triada por
                         diff contra a linha de base · relatório ≤ 15 KB · pendências/decisões numa passada ·
                         `git push origin HEAD:main` com a saída colada · telemetria (§11) colada.

TETOS — confira o contexto na status line em CADA gate:
  contexto > 300 k → feche a fatia verde, commite, escreva o handoff (≤ 20 linhas, §12 do relatório) e PARE;
                     a próxima fatia começa em sessão nova com este mesmo prompt + o handoff.
  turnos > 250 na fatia → idem.   relógio > 1,5× a faixa do card sem blocker aberto → idem.
  ⛔ estourou? NUNCA convoque outro agente para terminar. O hook do harness bloqueia o 5º agente.
DELEGAÇÃO: não delegue o que termina em poucas chamadas. Não delegue a verificação do seu próprio trabalho.
  No máximo 1 investigador READ-ONLY (Sonnet 5), só para varredura grande e realmente paralela.
ESCALAÇÃO (§8): só os gatilhos escritos em [SPEC]. Registre no card qual disparou, ou "nenhum".
```

## 5. O que entregar

1. Código na `main` (push com a saída colada).
2. O relatório no template FAST, ≤ 15 KB, com as 8 linhas da telemetria:
   `PYTHONIOENCODING=utf-8 python backend/scripts/medir_execucao_claude_code.py --sessao atual`.
3. Uma linha em `docs/canon/ESTADO-DAS-SPECS.md`. Dossiê: **não** republique; é do Fable, fora do caminho crítico.
4. Mensagem final ao Founder ≤ 20 linhas: o que está no ar, o que só ele faz (Implantar, senhas, canário),
   nota 0–100 com o critério, e a telemetria em 3 linhas (relógio · turnos/contexto · US$).

## 6. Condições de parada (CLAUDE.md §10) e nada mais

Risco de perda de dados · decisão comercial · conflito canônico · P0/P1 de segurança ou cross-tenant · ação
física do Founder · mudança material de escopo · custo extraordinário · falta de acesso. Fora disso: dê nota
0–100 às opções, escolha a maior, registre, siga.

---

## [SPEC] · preenchido em 17/09/2026 (experimento C do A/B, D-PROTO-02)

```
SPEC          EXTRA-001.5 — O agente sabe o que cada plano cobre
FICHA         docs/canon/FICHA-EXTRA-001.5.md  (15 KB) — 🔴 LEIA ESTA, e no LUGAR da proposta inteira
              (protocolo v12.1 §1 · D-PROTO-08). Ela traz o card proposto, as premissas do BLOCO 0 com o
              comando, as 5 unidades com arquivo/gate/mutação, as migrations, o canário e a caixa do Founder
PROPOSTA      docs/canon/specs-propostas/SPEC-EXTRA-001.5-o-agente-sabe-o-que-cada-plano-cobre.md
              seções a ler POR UNIDADE, quando for construí-la — nunca inteira:
                §0.3–§0.5 (as 4 correções e a divergência de marcha) · §1 (autorização de testes) · §4 (BLOCO 0)
                §5 unidade A · §6 unidade B · §7 unidade C · §8 unidade D · §9 unidade E
                §10 (os 12 guardas + o canônico) · §11 (as duas migrations) · §12 (canário) · §13 (entrega)
                §14 (as 3 referências externas — o juiz reabre) · §16 (lista de conclusão)
              RESEARCH-PACK `…-RESEARCH-PACK.md`: SÓ §2 (as consultas M1–M7) e §4 (os greps do BLOCO 0)
PROMPT ANTIGO docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.5.md  · só §1 (arquivos), §2 (autorizações), §3 (estado herdado)
UNIDADES      5 — A a chave canônica e as duas tabelas (`insurer_assistance_plans` + `…_services`, com fonte
              obrigatória pelo BANCO) · B a Skill `cobertura_e_assistencia` (os cinco estados, com origem) ·
              C as três ondas de coleta (extrair · verificar · PUBLICAR por gente) · D a tela de Conhecimento
              (cobertura + fila de curadoria) · E a medição e a `origem` no turno
              FATIAS (pela coesão do card): fatia 1 = A sozinha (é o arquivo-hub: chave + as duas migrations;
              B e C consomem o contrato dela) · fatia 2 = B + E (tocam o MESMO turno: a resposta e o que ela
              grava em `tool_invocations`) · fatia 3 = C + D (tocam a MESMA fila de curadoria: quem propõe a
              linha e quem a publica). O juiz roda UMA vez, no fim
MARCHA        PADRÃO — RISCO 7 · SUPERFÍCIE 2 · piso §3.2 em UM ponto (a migration que alarga o CHECK de
              `doc_kind` numa tabela viva, §11.2).
              🔴 A conta dá CRÍTICO e a marcha fixada é PADRÃO — pelo diagnóstico §13.4 ("PADRÃO = 1 lente +
              juiz fresco + canário (001.5)") e por D-PROTO-02. A divergência NÃO se silencia: o BLOCO 0
              recalcula, escreve a divergência no card e aplica o piso em dois pontos — a migration de §11.2
              (manifesto, transação única, rollback com guarda de contagem) e TODO texto que chega ao segurado
              (§6.2: a frase que diz "não" carrega documento e página)
EXECUTOR      Opus 5 · effort high   (experimento C: `high` × juiz Opus 5 — o executor NÃO muda o effort no meio)
JUIZ          opus
GATILHOS      lente do dado: **SIM** — o §8 do protocolo manda-a entrar quando "o outcome é NÚMERO, DATASET ou
              relatório que a corretora lê", quando há "migration que ALTERA DADO" e quando "a SPEC afirma
              percentuais do acervo". Os três batem aqui: o outcome É a base de planos (um dataset que a tela
              de §8 mostra e o corretor lê), a migration de §11.2 mexe na trava de uma tabela viva, e §0.1/§9
              afirmam números do acervo (8 de 61 · 6 com a chave casando · 83,86 % do prêmio). A lente
              reconstrói por SELECT as três contagens de §9 (CG na base ≠ plano publicado ≠ seguradora que a
              corretora usa) e confere as linhas publicadas contra documento e página ·
              red team: **NÃO** — não há autenticação, sessão, cross-tenant, dinheiro nem ação irreversível a
              terceiro; a base é global e só de leitura pelo produto ·
              consulta ao Fable antes do BUILD: **NÃO** — não há decisão de arquitetura em aberto; a forma
              (compositor consulta a base, nota 90) e "duas tabelas, não uma" já estão decididas na proposta ·
              confirmação (§6.1): SIM se o juiz achar blocker no código que grava por migration ou no texto
              que chega ao segurado
FAIXA         PADRÃO ≤ 75 min por fatia (fatia 1 · fatia 2 · fatia 3) · juiz + lente + conserto + entrega
              ≤ 45 min. Tetos por fatia: 160 turnos e 250 k de contexto (§10)
🔴 UMA SESSÃO, DO CARD AO PUSH (D-PROTO-08 · v12.1 §5.2): você constrói a **fatia 1**; da **fatia 2** em diante
              DELEGA a construção a UM builder subagente fresco (Opus 5 xhigh, sequencial, escreve sozinho),
              com o pacote: card · unidades · arquivos · handoff · gates. Você fica como gerente: roda as
              provas, chama o juiz, conserta, entrega. ⛔ nunca sessão nova por fatia (📊 a 001.4 em 3 chats
              custou o mesmo que o laço curto) · ⛔ nunca dois builders ao mesmo tempo. A suíte inteira roda
              UMA vez, depois do conserto, sozinha
BASE          <hash do origin/main — preencha no preflight>
DEPENDE DE    tudo o que esta SPEC consome já está na `main`: EXTRA-001.3 (`c82bfe8`, 16/09) e EXTRA-001.4
              (`ff2518a`, 16/09). A porta da apólice da EXTRA-001.1 EXISTE —
              `backend/app/providers/policy_data_provider.py` — e a 001.5 **consome, não edita** (dois
              escritores no mesmo arquivo é o que o §3.4 proíbe). A chave canônica EXISTE —
              `backend/app/services/corridor_playbooks.py::normalize_insurer_key(insurer, para=…)` (linha
              8236) — e esta SPEC a CHAMA com `para="conhecimento"`, nunca cria a terceira (CLAUDE.md §5)
PENDÊNCIAS    P-PILOTO-04 (fecha só a parte de conhecimento → veredito **PARCIAL**, com a prova) ·
              P-PILOTO-20 (📊 já FECHADA pela 001.1 — `PENDENCIAS-FECHADAS.md`; confirme numa linha e siga).
              Entradas novas obrigatórias, cada uma com o que destrava · de quem é · o que custa esquecer:
              o corpus não carrega página · `insurer_key` inconsistente em 14 tabelas · 3 valores de `doc_kind`
              sem escritor · `normative_documents` e `normative_document_versions` são classe SEM_ARQUIVO
SÓ O FOUNDER  🔴 revisar e publicar as primeiras linhas da fila de curadoria (ou indicar quem revisa) — é a
              única dependência humana, e ela bloqueia o canário completo; colar as perguntas dos casos 1–5 e 7
              no chat `core` da Resulta; mandar a mensagem do caso 6 pelo aparelho TESTE-A; clicar Implantar
              (`smith-api` **e** `smith-web`); conduzir a validação com Saionara e Regina
A/B           experimento C: Opus 5 `high` + juiz Opus 5, marcha PADRÃO. Ao fim, cole as 8 linhas do script no
              relatório e avise o Founder — o Fable audita depois e compara com a 001.3 (xhigh + Fable) e a
              001.4 (max + Fable), pelos critérios de D-PROTO-02
```

# PROMPT DE EXECUÇÃO — EXTRA-001.3 · AAA FAST (protocolo v12) · PREENCHIDO em 16/09/2026

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

## [SPEC] · preenchido em 16/09/2026 (experimento A do A/B, D-PROTO-02)

```
SPEC          EXTRA-001.3 — O grupo só recebe o que importa
PROPOSTA      docs/canon/specs-propostas/SPEC-EXTRA-001.3-o-grupo-so-recebe-o-que-importa.md
              seções a ler: §0 (resultado, card), §1 (autorização), §2 (escopo), §3 (arquitetura e os 11 pontos de
              envio), §4 (BLOCO 0), §5–§11 (as unidades), §12 (guardas, teto 12), §13 (migrations), §14 (canário),
              §20–§23 (o que saiu, dependências, caixa do Founder, lista de conclusão). §16 e o RESEARCH-PACK só quando citados
PROMPT ANTIGO docs/canon/specs-propostas/PROMPT-DE-ABERTURA-EXTRA-001.3.md   · só §1 (arquivos), §2 (autorizações), §3 (estado herdado)
UNIDADES      7 — A guarda única "humano já está nesta conversa" · B números da casa no card Equipe · C uma mensagem,
              inteira, uma vez · D os quatro modelos · E todo envio ao grupo contado (+ §9.2, o achado que pode calar o
              atendimento) · F o gate de ligar o agente · G as 6 mutações com papel, origem e auditoria
              FATIAS (sugestão; confirme pela coesão no card): fatia 1 = A + C + E (o que muda o que SAI: guarda, bloco
              único, contador) · fatia 2 = B + D + F + G (card Equipe, modelos, gate, mutações). O juiz roda UMA vez, no fim
MARCHA        CRÍTICO — RISCO 8 · SUPERFÍCIE 3 · piso §3.2: envia mensagem ao grupo E migration de estrutura
EXECUTOR      Opus 5 · effort xhigh
JUIZ          fable
GATILHOS      lente do dado: SIM (o outcome "todo envio contado" é dataset + migration de dado; a lente reconstrói a
              contagem sobre o acervo real por SELECT) · red team: NÃO (sem auth, dinheiro ou portal; o juiz carrega a lista
              de ataques, inclusive "duas corretoras ao mesmo tempo" na guarda única) · consulta Fable antes: NÃO (o
              desenho está fechado na proposta) · confirmação pós-conserto: SIM se o juiz achar blocker em envio/tenant/migration
FAIXA         fatia 1 ≤ 1h15 · fatia 2 ≤ 1h15 · juiz + lente + conserto + entrega ≤ 45 min  (tetos: 250 turnos e 300 k por fatia)
BASE          <hash do origin/main — preencha no preflight>
DEPENDE DE    EXTRA-001.2 (na main desde 15/09; o canário dela ainda depende do Implantar — a 001.3 usa o CÓDIGO, não o deploy)
PENDÊNCIAS    P-PILOTO-02 · 03 · 04 · 12 (absorvidas: FECHADA/CONTINUA/MORREU com prova) · P-PILOTO-10 · 13 · 15 (reavaliar)
SÓ O FOUNDER  parear TESTE-A/TESTE-B se faltar; criar o grupo de canário no tenant de teste (só ele dentro); Implantar
              smith-api → smith-web; rodar o canário da §14; nunca os grupos operacionais da Resulta/AutoFleet
A/B           experimento A: Opus 5 xhigh + juiz Fable. Ao fim, cole as 8 linhas do script no relatório e avise o Founder
              — o Fable audita depois (D-PROTO-03)
```

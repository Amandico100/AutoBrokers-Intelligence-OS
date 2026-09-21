# PROMPT DE ABERTURA — EXTRA-001.9 · O PAINEL DIZ DE QUEM É (pronto para colar em chat novo)

> Escrito em 21/09/2026, no fim da EXTRA-001.8. Cole o bloco inteiro num chat NOVO do Claude Code, modelo
> **Fable 5.1** (gerente/juiz).
> 🔴 **ATENÇÃO, e é o primeiro parágrafo de propósito: NÃO EXISTE proposta escrita da EXTRA-001.9.**
> 📊 Conferido em 21/09/2026: `ls docs/canon/specs-propostas/ | grep 001.9` → **nada**. O único texto que existe
> sobre ela são **quatro linhas** do diagnóstico (`DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §3, bloco
> "EXTRA-001.9", linhas ~286–289) e uma linha na fila do §12.1. ⛔ **Não invente escopo além delas.** O primeiro
> passo desta execução é **localizar ou escrever a proposta** (§2 deste prompt).

---

Você é o **EXECUTOR** da **SPEC-EXTRA-001.9 · O painel diz de quem é** do AutoBrokers Intelligence OS.
Leia este prompt inteiro antes de qualquer ferramenta. Responda sempre em **pt-BR**, em linguagem humana, sem
jargão de protocolo.

Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX` (é a que está em dia com a `origin/main`).
Python sempre de dentro de `backend/`, com `PYTHONIOENCODING=utf-8`.

## 0. PREFLIGHT (CLAUDE.md §2) — antes da primeira linha

```bash
git fetch origin
git rev-list --count HEAD..origin/main    # TEM de ser 0. Diferente de 0: pare e pergunte qual árvore usar
git rev-list --count origin/main..HEAD    # o que ainda não subiu
git branch --show-current                 # crie: feat/spec-extra-001.9-o-painel-diz-de-quem-e
git rev-parse --short HEAD                # registre no relatório
git status --short
```
⚠️ Arquivos `.TXT` soltos em `docs/canon/` são do Founder — **não commite, não apague**.

## 1. LEITURA MÍNIMA — isto, nesta ordem, por SEÇÃO, e nada mais

```
 1. CLAUDE.md                                              inteiro (é curto; são as regras invioláveis)
 2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md                §0–§3, §5, §7.3 — NÃO inteiro (é o rito v13.1)
 3. docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md
                                                           🔴 §3, bloco "EXTRA-001.9" (linhas ~286–289) e
                                                           §12.1 (a fila). É TUDO o que existe de escopo
 4. docs/canon/reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md   a SPEC anterior: o que ela deixou pronto e o
                                                           que ficou na caixa do Founder
 5. docs/canon/specs/SPEC-EXTRA-001.8-…md                  §10 (a Central por corretora) — é a tela que a
                                                           001.8 acabou de mexer, e a 001.9 mexe ao lado
 6. docs/canon/PENDENCIAS.md                               🔴 SÓ por número: P-E0018-01…29 (as novas) e o que
                                                           você citar. ⛔ NUNCA o arquivo inteiro (📊 ~660 KB)
 7. docs/canon/FOUNDER-DECISIONS.md                        SÓ as linhas D-PROTO-*, D-FILA-01, D-PILOTO-08
                                                           (a numeração da família) e D-E0018-*
 8. docs/canon/pacotes/PACOTE-BUILDER.md · PACOTE-JUIZ.md · PACOTE-RED-TEAM.md
 9. docs/canon/MIGRATIONS-AUTHORITY.md                     🔴 só se aparecer SQL. Sempre ANTES do SQL
```
⛔ Não leia o canon inteiro. ⛔ Não releia o que já está resumido aqui.

## 2. 🔴 O PRIMEIRO PASSO É A PROPOSTA — ela não existe

**FATO medido (21/09/2026):** não há `SPEC-EXTRA-001.9-*.md` em `docs/canon/specs-propostas/`, nem
`RESEARCH-PACK`, nem ficha.

```
1. Procure de novo, por via das dúvidas:  ls docs/canon/specs-propostas/ | grep -i "001.9"
   e  grep -rn "001\.9" docs/canon/*.md | head -20
2. Se NÃO achar (é o esperado): ESCREVA a proposta você mesmo, curta, ANTES de qualquer código, a partir
   das quatro linhas do diagnóstico e do que você MEDIR no repositório. Ela é o insumo do BLOCO 0 e do card.
3. ⛔ Não invente escopo. O que não estiver no diagnóstico e não for medido por comando vira PROPOSTA com
   nota, registrada, e não execução silenciosa.
```

**O escopo que o diagnóstico dá — e é só isto** (📊 `DIAGNOSTICO…md` §3, bloco EXTRA-001.9):

```
· mover `agentes/even → corretora/agente-de-atendimento`, e também `equipe`, `conhecimento` e `custos`
  para `corretora/`, COM REDIRECTS
· um guarda que casa todo `href` interno contra a TABELA DE ROTAS
  🔴 a razão escrita: `npm run test:rotas-montam` prova que as rotas MONTAM, e NÃO valida LINKS
· limpar o apelido antigo ("Even") da tela Prontidão
· nota do diagnóstico: mover agora 34 · junto com a SPEC de painel 88 · não mover 55
  ⚠️ ISSO É UMA DECISÃO EM ABERTO: se a SPEC de painel não está à vista, mover agora pode valer mais do
  que 34. Meça, dê nota, escreva a nota, e siga (protocolo §9)
```

**Nível, pela conta do protocolo §3:** o diagnóstico classificou **LEVE** (1–2 h, "dívida de tela"). ⚠️ **Refaça
a conta você mesmo**: mover rota com redirect mexe em `app/`, e o CLAUDE.md §9.1 existe porque uma pasta `[slug]`
ao lado de uma `[templateId]` derrubou o produto inteiro por 1h40 com todos os gates verdes. Se a sua conta der
PADRÃO, execute como PADRÃO.

## 3. O RITO — AAA v13.1 (D-PROTO-12 e D-PROTO-13)

```
① O FIO        escreva no card a cadeia do 1º byte ao último, arquivo:função por elo. O TESTE DO FIO é a
               primeira entrega: nasce VERMELHO pelo motivo certo, carrega o MOTOR real, dublê só na borda.
               Aqui o fio é: link na tela → tabela de rotas do Next → página → dado por company_id
② TRAVA DE 2 RODADAS   antes de montar QUALQUER pacote de julgamento:
               cd backend && python scripts/rodada_do_juiz.py abrir --spec EXTRA-001.9 --faixa-min 120
③ JULGAMENTO   ⚖️ juiz ‖ 🗡️ red team (Fable), ao mesmo tempo, cegos um ao outro, UMA vez, cada um com o seu
               pacote preenchido. Depois: UM conserto único com os dois laudos juntos, e uma confirmação
               curta (juiz novo, só o diff do conserto) se houve blocker material
④ v13.1        (a) todo pacote de subagente carrega §0–§3, §5 e §7.3 — use os PACOTE-*.md, não monte à mão
               (b) fatia grande vira fatias (teto por builder, não só por sessão)
               (c) a COSTURA é entrega: o teste que atravessa os dois lados, não dois testes de unidade
               (d) ⛔ script de juiz NUNCA toca o banco real — dublê obrigatório
               (e) 🔴 a TABELA DE ACHADOS do relatório é RECONFERIDA contra os laudos COMPLETOS, achado a
                   achado, antes de ser escrita
```
Mais: teto de **24 agentes** por sessão · commit **arquivo por arquivo**, nunca `git add -A` · mutação restaura
por **CÓPIA**, nunca `git checkout` · a bateria roda **depois** do conserto, com triagem **NOMINAL** contra
`docs/canon/reports/BATERIA-LINHA-DE-BASE.txt` (📊 linha de base de 21/09: **35 failed**).

## 4. MODELOS (D-PROTO-11)

```
🔧 BUILDER / LEITOR   Opus 5 (xhigh)      ⚖️ JUIZ / RED TEAM   Fable 5.1      🎯 GERENTE  você (Fable)
⛔ HAIKU nunca · ⚠️ Sonnet só para varredura muito óbvia e volumosa, com justificativa escrita
⛔ NENHUMA chamada que gaste crédito da chave Anthropic do PRODUTO (sem saldo, D-E00152-01)
```

## 5. AUTORIZAÇÕES PERMANENTES DO FOUNDER

```
1. EXECUTAR ATÉ O FIM. Proibido parar sem autorização, salvo as 8 condições do CLAUDE.md §10
2. NUNCA TRAVAR POR DÚVIDA: nota 0–100 a cada opção, o maior vence, escreva a nota e o motivo, e siga
3. QUEBRAR REGRA QUE ESTEJA TRAVANDO é autorizado — com a quebra DECLARADA no relatório
4. Subagentes e juízes à vontade, dentro do teto de 24
5. BANCO DE PRODUÇÃO: SELECT livre para medir (só contagens no relatório, sem PII)
6. 🔴 NENHUMA MENSAGEM SAI para segurado, seguradora, grupo ou equipe real
7. SEGREDOS: nunca no chat, no relatório, no commit. Só presença/ausência
```

## 6. 🔴 AS LIÇÕES DA EXTRA-001.8 — valem aqui como LEI

```
(a) GATE QUE MEDE SÓ O PEDAÇO QUE VOCÊ TOCOU NÃO É GATE. 📊 Na 001.8, NENHUM guarda rodava o agendador
    REAL com turnos longos, e por isso o defeito mais caro (o teto real era 10, não 24) atravessou NOVE
    guardas verdes. Aqui o equivalente é: um teste que confere a tabela de rotas NÃO prova que o link da
    tela leva a algum lugar. O guarda tem de casar `href` REAL contra rota REAL
(b) A CONTA QUE O FOUNDER OLHA TEM DONO. 📊 Na 001.8, `expiradas`/`timeouts` eram totais GLOBAIS gravados
    no hash de TODA corretora ativa: a perda de uma aparecia na tela da outra. Todo número que a tela
    publica tem de dizer DE QUEM ELE É, e ser provado com DOIS tenants
(c) LINHA DE CONTROLE SEMPRE (CLAUDE.md §9.2). Um gate sem a rodada que TEM de falhar não dá direito a
    conclusão nenhuma. E 📊 um gate que PISCA (1 vermelho em 6 rodadas) ensina a ignorá-lo: ou o piso sobe
    e a mudança é declarada, ou o gate não vale
(d) TESTE QUE GUARDA VERDADE VENCIDA É PIOR QUE TESTE NENHUM (CLAUDE.md §9.3). 📊 Na 001.8 um teste
    afirmava a soma que ERA o defeito; ele foi reescrito, mais apertado, e a lição migrou em vez de morrer
(e) 🔴 O PRODUTO É MULTI-CORRETORA (CLAUDE.md §13.9). Nenhum nome de corretora, de grupo ou de pessoa em
    código, teste, script ou documento de operação. A prova é com DOIS tenants reais
(f) 🔴 A RESPOSTA FINAL AO FOUNDER É O RELATÓRIO (CLAUDE.md §12.2). Ele lê SÓ a última mensagem: o que foi
    feito · o passo a passo do que ELE faz, com os comandos prontos e testados · o que esperar na tela ·
    o que fazer se der errado · as decisões com nota · o que ficou fora · qual é a próxima SPEC
(g) NO FECHO, UM AGENTE ATUALIZADOR DE DOCUMENTOS (Opus), num commit só: ESTADO-DAS-SPECS.md ·
    PENDENCIAS.md (por número, nunca inteiro) · FOUNDER-DECISIONS.md · TAREFAS-DO-FOUNDER.md ·
    as FONTES do painel em docs/canon/painel-do-founder/ (aba-*.html + `python montar.py`) — e a
    republicação do artefato é do GERENTE, não dele
```

## 7. O LAÇO, PASSO A PASSO

```
① PROPOSTA + CARD + BLOCO 0   escreva a proposta (§2), o EXECUTION CARD (protocolo §0.2) e O FIO; REMEÇA
                              no repositório tudo que a proposta afirmar — 🔴 número sem comando ao lado
                              não entra. `rodada_do_juiz.py abrir`
② BUILD                       1 fatia = 1 builder Opus fresco com o PACOTE-BUILDER preenchido. Teste do
                              fio VERMELHO antes do código. Commit por fatia, arquivo por arquivo
③ PROVA MECÂNICA              py_compile/tsc · testes dirigidos · mutação de CADA guarda novo, rerodada,
                              com a saída colada · 🔴 mexeu em `app/`: `npm run test:rotas-montam` +
                              `next start` + **uma requisição a /api/…** (CLAUDE.md §9.1)
④ JULGAMENTO PARALELO         juiz ‖ red team, cegos, com os pacotes
⑤ CONSERTO ÚNICO              os dois laudos juntos, no MESMO builder. Cada achado passa pelo TESTE DO
                              PRODUTO: muda um byte do que chega ao corretor/segurado/banco/segurança?
                              SIM = blocker, conserta. NÃO = pendência escrita, e segue
⑥ CONFIRMAÇÃO                 juiz novo, só o diff do conserto, se houve blocker material
⑦ BATERIA                     AGORA, não antes: cd backend && python -m pytest tests -q (sem -x).
                              Triagem NOMINAL contra BATERIA-LINHA-DE-BASE.txt (📊 35 failed em 21/09)
⑧ ENTREGA                     relatório · pendências · decisões · estado · documentos · painel ·
                              push com a saída colada · mensagem final ao Founder
```

## 8. O QUE ENTREGAR — nada disto é opcional

1. **A proposta** (§2) e depois **a SPEC convertida** em `docs/canon/specs/SPEC-EXTRA-001.9-….md`: com
   EXECUTION CARD · BLOCO 0 remedido · a seção **"O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS"** com **3 a 7
   URLs externas** reabertas (o guarda confere) · **O QUE SAIU**, com o gatilho de retorno de cada frente.
2. **Código na `main`**: `git push origin HEAD:main`, com a saída **colada** no relatório.
3. **Relatório** em `docs/canon/reports/SPEC-EXTRA-001.9-EXECUTION-REPORT.md`: abre com o **EXECUTION CARD**,
   fecha com a **telemetria** (protocolo §11), traz a **tabela de achados com a coluna EXCLUSIVO** reconferida
   contra os laudos, a bateria com a triagem nominal, o que ficou fora, os riscos, a declaração de que **nenhum
   motor paralelo** foi criado e a **nota 0–100 com o critério**. 🔴 Rode
   `cd backend && PYTHONIOENCODING=utf-8 python tests/test_o_protocolo_tem_policia.py` antes de fechar: ele
   confere o card e a telemetria **por máquina**.
4. **Pendências** em `PENDENCIAS.md` (`P-E0019-NN`), cada uma com 📊 o fato, **Destrava:**, **Dono:** 🧑/🤖 e
   **Custo de esquecer:** — mais as que você tocar, re-julgadas **por número**.
5. **Decisões** em `FOUNDER-DECISIONS.md` (`D-E0019-NN`), com nota 0–100 e as alternativas.
6. Os documentos e o painel da **regra (g)**, e a **mensagem final** da **regra (f)**.

## 9. PROIBIÇÕES

```
⛔ motor paralelo (CLAUDE.md §5): consolide e migre. Antes de criar script novo, PROCURE o que existe
⛔ mover rota sem redirect, e sem o guarda de href — é exatamente o defeito que a SPEC existe para matar
⛔ declarar gate verde numa SPEC que mexeu em `app/` sem `next start` + 1 requisição (CLAUDE.md §9.1)
⛔ nome de corretora, de grupo ou de pessoa como constante em código, teste, script ou documento
⛔ git add -A · commitar os .TXT do Founder · commitar qualquer coisa de docs/intake/
⛔ suíte inteira dentro de subagente · bateria durante o conserto
⛔ afirmar por leitura o que só um comando decide · número sem marca 📊/💭
⛔ parar para perguntar o que uma nota 0–100 resolve
```

## 10. A ORDEM DA FILA, DEPOIS DESTA

📌 `001.9 (esta) → 001.0 (retroativa) → triagem de pendências (D-FILA-01) → EXTRA-002 · investigação Agger`.
A **EXTRA-001.10.1** (a continuação do portal de vidros) entra quando o Founder trouxer as capturas que faltam.
⚠️ Confira em `ESTADO-DAS-SPECS.md` e em `FOUNDER-DECISIONS.md` (D-FILA-01) antes de afirmar — a ordem pode ter
mudado por decisão dele.

## 11. O QUE A EXTRA-001.8 DEIXOU NA CAIXA DO FOUNDER (e que pode aparecer no meio desta)

O canário de isolamento (duas corretoras de teste, 6 casos) · Implantar `smith-api` → `smith-web` · conferir
`scheduler` e `executor_threads` no `/health` · medir os núcleos do contêiner · 🔴 **não** ligar
`ISOLAMENTO_AVISO_AO_DONO` antes de P-E0018-09. **Nada disso bloqueia a 001.9** — se ele perguntar, responda e
siga.

---

**Comece agora**: preflight → leitura mínima → **procurar/escrever a proposta (§2)** → BLOCO 0 medido, com a
saída colada → card com O FIO → `rodada_do_juiz.py abrir` → build. Sem perguntar nada que uma nota 0–100 resolva.

E o resultado, para lembrar por que isto existe:

> **Todo link do painel leva a uma página que existe, cada tela diz de qual corretora é o que está mostrando, e
> o apelido antigo do produto sai da frente do corretor.**

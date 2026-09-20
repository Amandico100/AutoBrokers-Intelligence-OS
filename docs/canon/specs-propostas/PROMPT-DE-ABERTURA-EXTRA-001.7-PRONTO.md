# PROMPT DE ABERTURA — EXTRA-001.7 · O PILOTO MEDIDO (pronto para colar em chat novo)

> Escrito em 20/09/2026, no fim da EXTRA-001.5.2 (main `ec56813`). Cole o bloco inteiro num chat NOVO do Claude Code,
> modelo **Fable 5.1** (gerente/juiz) ou **Opus 5** se o Founder preferir economizar — o prompt diz quem faz o quê.

---

Você é o **EXECUTOR** da **SPEC-EXTRA-001.7 · O piloto medido** do AutoBrokers Intelligence OS. Leia este prompt inteiro
antes de qualquer ferramenta. Responda sempre em **pt-BR**, em linguagem humana, sem jargão de protocolo.

Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX` (é a que está em dia com a `origin/main`).
Python sempre de dentro de `backend/`, com `PYTHONIOENCODING=utf-8`.

## 0. PREFLIGHT (CLAUDE.md §2) — antes da primeira linha

```bash
git fetch origin
git rev-list --count HEAD..origin/main    # TEM de ser 0. Diferente de 0: pare e pergunte qual árvore usar
git rev-list --count origin/main..HEAD    # o que ainda não subiu
git branch --show-current                 # crie: feat/extra-001-7-o-piloto-medido
git rev-parse --short HEAD                # registre no relatório
git status --short
```
⚠️ Arquivos `.TXT` soltos em `docs/canon/` são do Founder — **não commite, não apague**.

## 1. LEITURA MÍNIMA — isto, nesta ordem, e nada mais

```
1. CLAUDE.md                                                     inteiro (é curto; são as regras invioláveis)
2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md                       §0–§3, §5, §6, §7.3 — NÃO inteiro
3. docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md    §0 (as notas que são palpite hoje) · o bloco
                                                                 "EXTRA-001.7" (≈linha 276) · §12 (a ordem da fila)
4. docs/canon/reports/SPEC-EXTRA-001.5.2-EXECUTION-REPORT.md     a SPEC anterior: o que entrou no ar ontem
5. docs/canon/PENDENCIAS.md                                      SÓ por número: P-PILOTO-01…12 e P-E00152-01…12.
                                                                 ⛔ NUNCA o arquivo inteiro (é gigante)
6. docs/canon/FOUNDER-DECISIONS.md                               SÓ as linhas D-PILOTO-*, D-PROTO-* e D-E00152-*. São lei
7. docs/canon/reports/SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md  o documento de testes do Founder, que você vai ESTENDER
8. docs/canon/pacotes/PACOTE-BUILDER.md · PACOTE-JUIZ.md · PACOTE-RED-TEAM.md   os pacotes que você entrega aos agentes
9. docs/canon/MIGRATIONS-AUTHORITY.md                            🔴 só se a SPEC tiver SQL. Sempre ANTES do SQL
```
⛔ Não leia o canon inteiro. ⛔ Não leia `PENDENCIAS.md` inteiro. ⛔ Não releia o que já está resumido aqui.

## 2. O QUE É ESTA SPEC

📊 Estado medido em 20/09/2026: o produto responde por uma base de **492 serviços em 108 planos de 8 seguradoras**
(EXTRA-001.5.2), o atendimento tem corredor, Vigia, Sentinela, Cérebro, cobrança e portal — e **nenhuma das notas do
§0 do diagnóstico é medida**. São palpite. O piloto é o que as transforma em número.

A SPEC tem **duas metades**, e só uma é sua:

```
🤖 SUA (esta execução)      o INSTRUMENTO: o checklist de ligar, a medição diária automática e a régua por dimensão
🧑 DO FOUNDER (depois)      os 3 dias com o agente ligado nas duas corretoras, e o canário da 001.5.2 que ainda não rodou
```

### O que você constrói

1. **Checklist de ligar** — um comando só que responde "dá para ligar hoje?" e reprova com motivo legível:
   `/health` limpo · destino de alerta ativo · canal WhatsApp conectado · números da casa cadastrados ·
   allowlist só com número de teste · agente ligado por corretora · flags do env que travam acionamento.
   📌 Já existe `backend/scripts/conferir_o_que_esta_no_ar.py` — **estenda, não crie um segundo** (CLAUDE.md §5).
2. **Medição diária automática** — um script que roda por dia e por corretora, só SELECT, sem PII, e devolve:
   conversas atendidas · rajadas coalescidas · apólice certa em 1 rodada · acionamentos com protocolo ·
   handoffs entregues · mensagens ao grupo por tipo · silêncios por motivo · quanto o agente resolveu sozinho.
   📌 Há réguas parecidas em `backend/scripts/regua_0971.py`, `regua_motor.py`, `medir_rota.py` e
   `medir_cobertura_de_planos.py` — **leia-as antes** e reaproveite o formato e o vocabulário.
3. **A régua por dimensão** — a nota 0–100 de cada dimensão do §0 do diagnóstico, **derivada da medição**, com o
   critério escrito ao lado. 🔴 Dimensão sem dado medido é **"NÃO AVALIADA"**, nunca uma nota inventada.
4. **A saída publicada** — o resultado vai para o artefato do Founder (§8) e para um relatório em
   `docs/canon/reports/`, em linguagem de gente.

### O FIO desta SPEC (escreva-o no card ANTES de construir)
```
banco de produção (conversas, work_runs, work_events, acionamentos, mensagens ao grupo)
   → o script de medição (SELECT, sem PII)
   → o número por dimensão por dia por corretora
   → a régua 0–100 com o critério
   → a tela/relatório que o Founder lê e usa para decidir se o piloto passou
```
E o **teste do fio** é a sua primeira entrega: ele roda a medição sobre um recorte REAL do banco (ou sobre um dublê
construído a partir do schema real, nunca escrito à mão) e afirma o número final, não o pedaço.

### Gates (o que precisa ficar verde)
```
· o checklist REPROVA quando uma trava está fechada, e PASSA quando todas estão abertas (par obrigatório)
· a medição roda sobre o banco real e devolve número por dia × corretora; roda duas vezes e dá o mesmo (idempotente)
· 🔴 nenhuma PII na saída: nem nome, nem telefone, nem CPF, nem placa, nem apólice. Só contagens
· isolamento: a medição de uma corretora não conta linha da outra (prova com as DUAS corretoras reais)
· dimensão sem dado sai "NÃO AVALIADA"; prove que ela CONSEGUE sair assim (mutação)
· a régua não melhora sozinha quando o dado some (o defeito clássico: menos dado = nota maior)
```

### Faixa e marcha
**PADRÃO** (o diagnóstico chama de LEVE porque é protocolo de operação; a conta do §3 do protocolo dá PADRÃO porque a
saída é lida pelo corretor e pelo Founder para decidir). **Faixa: ≤ 2h30 de relógio.** Passou de 1,5× (3h45) sem
blocker aberto: entregue o que está verde e registre o resto.

## 3. O RITO — núcleo do AAA v13, aprovado para teste em 20/09 (D-PROTO-10)

Funcionou na 001.5.2 (1 rodada de julgamento, 7 blockers materiais achados antes do push, ~2h20). São 3 regras:

```
① O FIO           escreva no card a cadeia do 1º byte que entra ao último que sai, arquivo:função por elo.
                  O TESTE DO FIO é a primeira entrega do builder: nasce VERMELHO pelo motivo certo, carrega o MOTOR
                  real (import OU spec_from_file_location), dublê só na borda (rede, modelo, storage). Gate que mede
                  só o pedaço que você tocou NÃO É GATE.
② TRAVA DE 2 RODADAS   antes de montar QUALQUER pacote de julgamento:
                  cd backend && python scripts/rodada_do_juiz.py abrir --spec EXTRA-001.7 --faixa-min 150
                  e depois `julgar` a cada rodada. A 3ª sai com código 2 e é PROIBIDA: na 3ª o defeito é o CARD,
                  não o código — reescreva O FIO e rode `fio-reescrito`.
③ JULGAMENTO PARALELO, UMA VEZ   ⚖️ juiz generalista ‖ 🗡️ red team, ao mesmo tempo, cegos um ao outro, cada um com
                  o seu pacote (docs/canon/pacotes/PACOTE-JUIZ.md e PACOTE-RED-TEAM.md preenchidos: card, O FIO, diff,
                  comandos dos gates, lista de ataques). Depois: UM conserto único com os dois laudos juntos, e uma
                  confirmação curta (juiz novo, ≤ 20 turnos, só o diff do conserto) se houve blocker material.
```
Mais: **bateria inteira só DEPOIS do conserto** (na 001.5.2 ela rodou durante e deu 5 falhas falsas) ·
**teto de 24 agentes** por sessão (já é o padrão do hook; ⛔ não "restaure" para 12) ·
commit arquivo por arquivo, nunca `git add -A`.

## 4. MODELOS — custo-benefício, decidido pelo Founder (D-PROTO-11)

```
🔧 BUILDER / LEITOR      Opus 5 (xhigh). É quem escreve código e quem lê documento em volume
⚖️ JUIZ / RED TEAM       Fable 5.1 — e SÓ aqui o Fable é usado, porque é onde ele rende
🎯 GERENTE               você. Se o chat for Fable, delegue tudo o que for volume; se for Opus, trabalhe direto
⛔ HAIKU                 NUNCA. É fraco e gera retrabalho
⚠️ SONNET                só para varredura MUITO óbvia e volumosa, e só se você justificar por escrito
⛔ API do PRODUTO        NENHUMA chamada que gaste crédito da chave Anthropic do produto (ela está sem saldo, e o
                         Founder decidiu não recarregar: D-E00152-01). Quem lê e escreve é AGENTE DO PLANO
```
🔴 **Agentes em paralelo sempre que os arquivos forem disjuntos.** Na 001.5.2 isso cortou o relógio pela metade.
O limite de simultâneos da sessão é 2 por padrão; se precisar de mais, diga ao Founder que ele pode subir
`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, e siga com 2 enquanto isso — não pare por causa disso.

## 5. AUTORIZAÇÕES PERMANENTES DO FOUNDER (valem nesta execução, sem precisar perguntar)

```
1. EXECUTAR ATÉ O FIM. Você está PROIBIDO de parar sem autorização dele, salvo as 8 condições do CLAUDE.md §10
   (perda de dados · decisão comercial · conflito canônico · P0/P1 de segurança ou cross-tenant · ação física dele ·
   mudança material de escopo · custo extraordinário · falta de acesso indispensável)
2. NUNCA TRAVE POR DÚVIDA. Dúvida entre caminhos → dê NOTA 0–100 a cada opção, o maior vence, ESCREVA a nota e o
   motivo no relatório, e SIGA. Travou 30 min → escolha o mais conservador, anote, siga
3. QUEBRAR REGRA QUE ESTEJA TRAVANDO: autorizado, se for pelo bem do projeto e o custo em tokens valer a pena —
   com a quebra DECLARADA no relatório. Teto de agentes, limite de simultâneos e teto de contexto não são motivo de parada
4. SUBAGENTES E JUÍZES À VONTADE, dentro do teto de 24 — é o que dá qualidade e velocidade
5. BANCO DE PRODUÇÃO: SELECT livre para medir (só contagens no relatório, sem PII). Escrita SÓ por migration com
   APPLY/VERIFY/ROLLBACK escritos antes, ou por escritor que já existe no produto
6. MinIO / acervo: leitura livre
7. NENHUMA MENSAGEM SAI para segurado, seguradora, grupo operacional ou equipe real fora do canário descrito.
   Números de teste: só os que já estão no env (TESTE-A / TESTE-B)
8. SEGREDOS: nunca no chat, no relatório, no commit. Só presença/ausência. O Founder colou credenciais no chat em
   20/09 — ⛔ NUNCA repita, cite ou guarde nenhuma delas; se precisar, use o que já está no ambiente local
```

## 6. A BARRA DE QUALIDADE — o alvo é 100, o aceitável é 90

```
✅ conta como qualidade      defeito material achado ANTES do push · gate que atravessa o fio inteiro · número medido
                             com o comando ao lado · dublê que vem do schema real · par de teste (caso + controle oposto)
                             · mutação que prova que o guarda CONSEGUE ficar vermelho · pendência escrita com dono
⛔ não conta                 relatório bonito · contagem de linhas · "está funcionando" sem saída colada · número sem
                             marca 📊/💭 · teste que reimplementa o motor · dimensão com nota inventada
🔴 honestidade acima de nota: se o número honesto for ruim, ESCREVA o número ruim. Na 001.5.2 um leitor reportou
   "35,8 %" em vez de maquiar, e foi isso que salvou a entrega
```
Marcação obrigatória (CLAUDE.md §12.1): **📊 medido** (com data, fonte e o comando) · **💭 estimado** (não citável
como fato) · **❓ desconhecido**. Número sem marca é defeito de revisão.

## 7. O LAÇO, PASSO A PASSO

```
① CARD + BLOCO 0        ≤ 15 min. Abra o relatório pelo template docs/canon/reports/SPEC-EXECUTION-REPORT-TEMPLATE-FAST.md
                        Preencha o EXECUTION CARD (12 linhas do protocolo §0.2) + O FIO. Remeça 5–10 premissas que
                        mudariam o DESENHO, com o comando ao lado. `rodada_do_juiz.py abrir`
② BUILD                 1 fatia = 1 builder Opus fresco com o PACOTE-BUILDER preenchido. Fatias com arquivos disjuntos
                        rodam EM PARALELO. Teste do fio vermelho ANTES do código. Commit por fatia
③ PROVA MECÂNICA        py_compile/tsc · testes dirigidos · mutação dos guardas NOVOS · se tocou app/ ou middleware:
                        npm run test:rotas-montam + next start + 1 requisição a /api/…
④ JULGAMENTO PARALELO   `rodada_do_juiz.py julgar` → juiz ‖ red team, cegos, com os pacotes
⑤ CONSERTO ÚNICO        os dois laudos juntos, no MESMO builder (contexto quente). Cada achado passa pelo TESTE DO
                        PRODUTO (§2 do protocolo): muda um byte do que chega ao segurado/corretora/banco/segurança?
                        SIM = blocker, conserta. NÃO = pendência escrita, e segue
⑥ CONFIRMAÇÃO           juiz novo, ≤ 20 turnos, só o diff do conserto, se houve blocker material
⑦ BATERIA               AGORA, não antes: cd backend && python -m pytest tests -q (sem -x). Linha de base de 20/09:
                        📊 42 failed · 48 errors. Triagem por diff; falha nova = sua até prova em contrário
⑧ ENTREGA               relatório ≤ 15 KB · pendências · decisões · estado · artefato · push com a saída colada
```

## 8. O QUE ENTREGAR — nada disto é opcional

1. **Código na `main`**: `git push origin HEAD:main`, com a saída do push **colada** no relatório
   (CLAUDE.md §2: entregar não é commitar, é empurrar).
2. **Relatório** em `docs/canon/reports/SPEC-EXTRA-001.7-EXECUTION-REPORT.md`, pelo template FAST, ≤ 15 KB, com:
   EXECUTION CARD · O FIO · o que foi entregue com a prova · a bateria com a contagem · o que ficou fora e por quê ·
   riscos · **a declaração de que nenhum motor paralelo foi criado** · telemetria
   (`python backend/scripts/medir_execucao_claude_code.py --sessao atual`) · **nota 0–100 da execução com o critério**.
   🔴 O guarda `backend/tests/test_o_protocolo_tem_policia.py` confere isso por máquina — rode-o antes de fechar.
3. **Pendências** novas em `docs/canon/PENDENCIAS.md` (`## P-E0017-NN · …`, com 📊 o fato, **Destrava:**, **Dono:** 🧑/🤖,
   **Custo de esquecer:**). Nada sai da lista sem estar feito ou decidido.
4. **Decisões** do Founder em `docs/canon/FOUNDER-DECISIONS.md`, se houver.
5. **Uma linha** em `docs/canon/ESTADO-DAS-SPECS.md`, no estilo das vizinhas.
6. **O documento de testes dele**: estenda `docs/canon/reports/SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md` com a seção
   do piloto — o que ele roda, em que ordem, o que esperar, o que anotar quando não bater.
7. **O artefato do Founder** (é onde ele lê tudo):
   `https://claude.ai/code/artifact/defe331c-9399-4584-9d1c-2126a527cea0` — aba **"Conhecimento e destilação"** hoje;
   crie uma aba nova **"O piloto"** se fizer mais sentido. Para republicar: leia o artefato com a ferramenta Artifact,
   trabalhe sobre o arquivo salvo, **tire a moldura da plataforma** (a 1ª linha até `<body>` e o `</body></html>` final),
   e publique passando a MESMA `url` para o link não mudar. Reuse as classes de CSS que já existem; nada de script novo.
8. **Mensagem final ao Founder**, ≤ 25 linhas, em linguagem de gente: o que está no ar · o que só ele faz · a nota
   com o critério · o relógio e o custo · **os próximos passos e qual é a próxima SPEC**.

## 9. PROIBIÇÕES

```
⛔ motor paralelo (CLAUDE.md §5): consolide e migre; nunca crie ao lado. Antes de criar script novo, PROCURE o que existe
⛔ git add -A · commitar os .TXT do Founder · apagar memória, worktree ou material de INTAKE
⛔ mensagem a pessoa real fora do canário · segredo em log/relatório/commit
⛔ suíte inteira dentro de subagente (bloqueie-se: são 45 min) · bateria durante o conserto
⛔ afirmar por leitura o que só um comando decide (protocolo §0.4) · número sem marca
⛔ parar para perguntar o que você pode decidir com uma nota 0–100
```

## 10. SE A EXECUÇÃO NÃO COUBER

Se o BLOCO 0 mostrar que a 001.7 depende de coisa que só o Founder faz (o deploy e o canário da 001.5.2 ainda não
rodaram em 20/09), você tem DUAS opções — **dê nota 0–100 às duas, escolha, registre e siga**:
```
A) construir o INSTRUMENTO agora (checklist + medição + régua) e deixar os 3 dias para ele   💭 provável vencedora
B) pular para a EXTRA-001.10 (portal de vidros ponta a ponta, CRÍTICO, 10–14h) e voltar depois
```
Se escolher A, a SPEC fecha com o instrumento provado sobre o dado que JÁ existe no banco (há conversas reais de
setembro), e o piloto de 3 dias vira a caixa do Founder.

## 11. A ORDEM DA FILA, DEPOIS DESTA

📌 `001.7 → 001.10 (portal de vidros) → 001.8 (isolamento por corretora) → 001.9 (rotas do painel) → 001.0 (retroativa)`
e então **EXTRA-002 · investigação Agger**. Confira em `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §12
e em `docs/canon/INDICE-DE-SPECS.md` antes de afirmar — a ordem pode ter mudado por decisão dele.

---

**Comece agora**: preflight → leitura mínima → BLOCO 0 medido → card com O FIO → `rodada_do_juiz.py abrir` → build.
Sem perguntar nada que uma nota 0–100 resolva.

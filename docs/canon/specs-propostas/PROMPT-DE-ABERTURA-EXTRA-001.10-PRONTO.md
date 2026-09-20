# PROMPT DE ABERTURA — EXTRA-001.10 · O PORTAL DE VIDROS DE PONTA A PONTA (pronto para colar em chat novo)

> Escrito em 20/09/2026, no fim da EXTRA-001.7 (main `b3d88f1`). Cole o bloco inteiro num chat NOVO do Claude Code,
> modelo **Fable 5.1** (gerente/juiz). ⚠️ Este arquivo SUBSTITUI o `PROMPT-DE-ABERTURA-EXTRA-001.10.md` antigo
> (rito v11, superado por D-PROTO-01). Do antigo só continuam válidas as perguntas de aquecimento da §5 dele,
> reaproveitadas aqui na §12.

---

Você é o **EXECUTOR** da **SPEC-EXTRA-001.10 · O portal de vidros de ponta a ponta** do AutoBrokers Intelligence OS.
Leia este prompt inteiro antes de qualquer ferramenta. Responda sempre em **pt-BR**, em linguagem humana, sem jargão
de protocolo.

Árvore: `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX` (é a que está em dia com a `origin/main`).
Python sempre de dentro de `backend/`, com `PYTHONIOENCODING=utf-8`.

## 0. PREFLIGHT (CLAUDE.md §2) — antes da primeira linha

```bash
git fetch origin
git rev-list --count HEAD..origin/main    # TEM de ser 0. Diferente de 0: pare e pergunte qual árvore usar
git rev-list --count origin/main..HEAD    # o que ainda não subiu
git branch --show-current                 # crie: feat/extra-001-10-o-portal-de-vidros-ponta-a-ponta
git rev-parse --short HEAD                # registre no relatório
git status --short
```
⚠️ Arquivos `.TXT` soltos em `docs/canon/` são do Founder — **não commite, não apague**.

## 1. LEITURA MÍNIMA — isto, nesta ordem, por SEÇÃO, e nada mais

```
 1. CLAUDE.md                                                      inteiro (é curto; são as regras invioláveis)
 2. docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md                        §0–§3, §5, §6, §7.3 — NÃO inteiro
 3. docs/canon/specs-propostas/
    SPEC-EXTRA-001.10-o-portal-de-vidros-de-ponta-a-ponta.md       🔴 INTEIRA (1.014 linhas). É a proposta que você
                                                                   converte em SPEC. As §§4, 5, 6, 8, 10, 14 e 16 são
                                                                   o coração
 4. …-RESEARCH-PACK.md (mesmo diretório)                           o que foi medido no material; §2.1 (inferência de
                                                                   categoria) é a que decide desenho
 5. docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md     §10 INTEIRO (linhas ~602–708: o laudo I5, o bloco
                                                                   001.10 e §10.6) · §12.1 (a fila)
 6. docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md                 a autoridade sobre o que cada TELA pergunta
 7. docs/canon/guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md        §2.9 e §2.10 (o que ainda NÃO foi capturado)
 8. docs/canon/reports/SPEC-EXTRA-001.7-EXECUTION-REPORT.md        a SPEC anterior: as lições que viraram regra na §6
 9. docs/canon/PENDENCIAS.md                                       🔴 SÓ por número: P-PILOTO-02, P-PILOTO-07,
                                                                   P-PILOTO-08, P-50, P-E0017-01…09.
                                                                   ⛔ NUNCA o arquivo inteiro (📊 ~560 KB)
10. docs/canon/FOUNDER-DECISIONS.md                                SÓ as linhas D-PILOTO-*, D-PROTO-* e D-E0017-*.
                                                                   🔴 D-PILOTO-17 (Bradesco) é lei
11. docs/canon/pacotes/PACOTE-BUILDER.md · PACOTE-JUIZ.md ·
    PACOTE-RED-TEAM.md                                             os pacotes que você entrega aos agentes
12. docs/canon/MIGRATIONS-AUTHORITY.md                             🔴 só se a SPEC tiver SQL. Sempre ANTES do SQL
```
⛔ Não leia o canon inteiro. ⛔ Não leia `PENDENCIAS.md` inteiro. ⛔ Não releia o que já está resumido aqui.

**O material do Founder** (HAR, HTML, bundle JS, prints, .docx) — 🔴 **contém PII, cookies e tokens. Leia para
confirmar contrato; NUNCA copie CPF, placa, nome, telefone, cookie ou token para código, teste, relatório ou chat.
Mascare sempre, e descreva só estrutura.**

```
docs/intake/materiais/portal-vidros/            📊 365 arquivos · 208 MB · medido 20/09/2026
  YELUM/YELUM 1/              (09/09) HAR 29,2 MB · 2 HTML (passo 3 e tela final 100 %) · 4 PNG  → LATARIA ponta a ponta
  YELUM/YELUM VIDROS ANTIGO/  (14–15/08) HAR 25,9 MB · 5 HTML (passo 3, 5, 80 %, 99 % com lojas, cancelado) · 3 PDF
                                          → VIDRO DE PORTA até o 99 %, cancelado antes do agendamento
  PORTO/                      (15/08) 2 HAR (22,2 MB lanterna · 10,3 MB roda sem cobertura) · 4 HTML + _files
  PERGUNTAS QUE HUMANO FAZ PARA PORTAL DE VIDROS.docx  (12/09, 15 KB) — as perguntas da Regina
```

## 2. O QUE É ESTA SPEC

**O objetivo de negócio, na palavra do Founder (é isto que você está construindo, e nada menos):**

> **O agente de atendimento faz acionamentos COMPLETOS no portal de vidros, sem travar e sem errar.** Ele coleta do
> segurado, no WhatsApp, **tudo o que o portal vai pedir ANTES de abrir o portal**; preenche cada tela certo;
> **finaliza** (protocolo + loja ou domicílio + agendamento quando houver); e leva a informação correta de volta ao
> cliente no WhatsApp. **Tela desconhecida nunca vira silêncio: vira handoff com dossiê, e entra na fila de
> aprendizado.**

📊 **Onde o robô para HOJE** (medido em 20/09/2026, `b3d88f1`):

| o que falta | arquivo:função | evidência |
|---|---|---|
| **não grava peça/causa/cidade**: o `PATCH /atendimentos` está documentado e não existe | `portal_worker/journeys/vidros_apifirst.py:23` (docstring) × `vidros_sessao.py:62` `SessaoVidros` — **15 métodos, nenhum `atualizar_atendimento`** | `grep -n "PATCH" vidros_*.py` devolve só a docstring e o `abandonar` |
| **fronteira material fixa** — vale para vidraçaria e erra em lataria | `vidros_estado.py:233` `FRONTEIRA_MATERIALIZAR = "gravar_questionario"` (constante) | uma constante, zero ramos por categoria |
| **para no protocolo**: não escolhe loja, não agenda, não vai a domicílio | `portal_worker/adaptive.py:933-960` (o comentário do passo 7) e `adaptive.py:345-347` (o prompt proíbe clicar em Agendar) | `vidros_apifirst.py:33` "Não escolhe loja. Não agenda. Não cancela. Não finaliza." |
| **não anexa foto nem gera link de vistoria** | zero linhas; `vidros_api.py:114` `EP_VISTORIA_MOBILE_NAO_MEDIDO` declarado e nunca chamado | `grep -rn "fotografias\|vistoriamobile" backend` |
| **mapa de seguradora hardcoded e errado** | `vidros_apifirst.py:102-106` `SLUGS_DE_SEGURADORA` = 3 entradas (`PORTO`, `AZUL`, **`ITAU`**) para um portal de 38 | `ITAU` não existe no portal → quebra a promessa fail-closed |
| **8 endpoints declarados e nunca chamados** | `vidros_api.py:93-114` (`EP_SOLICITANTES`, `EP_CORRETORES`, `EP_UFS`, `EP_CIDADES`, `EP_CLIENTES_CIDADES`, `EP_ABANDONAR`, `EP_CANCELAR`, `EP_FINALIZAR_NAO_MEDIDO`) | não cadastra solicitante, não escolhe cidade, não sabe desistir |
| **o acionamento não aparece na Fila nem na Ficha** | P-PILOTO-02: `portal_tool.py:421` grava só `session_id`; `work_run_id`/`agent_id`/`operation_key` ficam vazios | a corretora não vê o trabalho acontecendo |
| **tela desconhecida no portal não aprende** | P-PILOTO-08: `tela_cega` só é escrita pelo corredor de URA; o worker grava `debug_dom` num jsonb que ninguém varre | o handoff existe, o aprendizado não |

**O que já está CERTO e não se mexe:** o caminho DOM (`vidros_lanternas.py`, 1.266 linhas), o preflight
(`vidros_api.py:148 classificar_preflight`), o guard da SPEC-073 (`vidros_apifirst.py:109 _guard_do`, fail-closed), o
motor de questionário (`vidros_questionario.py`), a máquina de estados (`vidros_estado.py`) e o laboratório da
SPEC-077 (`backend/scripts/portal_factory.py` — **USE-O, não o duplique**).

### As unidades prováveis (a proposta §5–§7 tem o detalhe; você reconfirma no BLOCO 0)

```
🟢 NÃO DEPENDE DE CAPTURA NOVA — fecha nesta SPEC
P0-1  SessaoVidros.atualizar_atendimento = PATCH /atendimentos (o corpo exato do HAR)
P0-2  POST /solicitantes + PUT /atendimentos/corretores (obrigatórios em 3 de 3 HAR)
P0-3  fronteira material CALCULADA por categoria (L → PATCH · V → POST /questionarios)
P0-4  um mapa só de seguradora, o do portal: 38 códigos medidos; ITAU inativo; sompo → GRUPO_HDI; Yelum = LIBERTY
P0-5  slot bloqueante cidade_para_o_servico (UFs → cidades → clientes/cidades) e a reconciliação das TRÊS verdades
      sobre o que perguntar: prompts.py:133 × portal_params.py:43 (TRANSPORTAVEIS) × portal_tool.py
P0-6  🔴 o FREIO POR JOB (sem ele o canário libera todos os jobs de vidros em voo naquele worker)
P1-1  ler e APRESENTAR lojas, distâncias, dias e horários ao segurado — sem clicar
P1-3  perguntas por família nas famílias de CATÁLOGO (retrovisor, farol, lanterna, para-choque)
P1-4  desambiguação guiada pelo catálogo: ler itens-cobertos/motivos-dano ANTES de perguntar
P1-5  🔴 LATARIA como caminho próprio, até o comprovante (multi-peça, sem loja/domicílio)
P1-6  vistoria e fotos: o caminho multipart ESCRITO e DESLIGADO
P2-1/2/4  régua única do trincado · abandonar e cancelar como journeys · promoção via portal_factory lab
P-PILOTO-02  o acionamento aparece na Fila e na Ficha (work_run_id, agent_id, fase, protocolo durável)
P-PILOTO-08  tela desconhecida do portal entra na fila de aprendizado, com dossiê
🔴 O CANÁRIO de lataria

🟡 DEPENDE DA CAPTURA Nº 1 — fica escrito, CANDIDATE e desligado
P1-2  POST agendamentos / POST direcionamentos (o último clique; zero exercícios em 4 HAR)
P1-3  perguntas de PARA-BRISA (chuva · degradê · ADAS) e de VIGIA (desembaçador)
P2-1  a régua real do trincado (hoje há TRÊS: 10 cm em vidros_lanternas.py:334 _LIMITE_CM · "moeda de 1 real" da
      Regina · 5/20 cm num servicos-detalhes que é de lataria)

⛔ NÃO ENTRA: uma linha sequer para `agendeseuservico.com` (Bradesco) — D-PILOTO-17 manda capturar antes de codar
```

### O FIO desta SPEC (escreva-o no card ANTES de construir)
```
WhatsApp do segurado ("quebrou o para-brisa")
  → app/core/prompts.py + app/services/perguntas_do_portal_de_vidros.py   o agente pergunta só o que o catálogo exige
  → app/agents/tools/portal_params.py:build_portal_params                  os params completos, com cidade_para_o_servico
  → app/agents/tools/portal_tool.py:_run                                   cria o portal_job (com work_run_id e agent_id)
  → portal_worker/worker.py → journeys/vidros_apifirst.py                  GET /apolices (preflight, read-only)
  → ─── fronteira A ─── POST /atendimentos  (protocolo, IRREVERSÍVEL)
  → PUT /atendimentos/corretores · POST /solicitantes · PATCH /atendimentos (peça, causa, cidade)
  → ─── fronteira B (calculada por categoria) ─── POST /questionarios
  → L: comprovante   ·   V: lojas + dias + horários APRESENTADOS ao segurado
  → app/services/vidros_flow.py → WhatsApp: protocolo + loja/domicílio + dia e hora, em português de gente
  → tela desconhecida → handoff com dossiê + fila de aprendizado (nunca silêncio)
```
E o **teste do fio** é a sua primeira entrega: ele nasce VERMELHO pelo motivo certo, carrega o MOTOR real (import ou
`spec_from_file_location`), lê o HAR por `trafego.importar_har` (sem segundo leitor) e afirma **a sequência de escritas
e o corpo do PATCH inteiro** — não o pedaço. Dublê só na borda (rede, modelo, storage).

### Gates (o que precisa ficar verde — a proposta §8 e §16 têm a lista fechada)
```
G1  replay OFFLINE do HAR da Yelum lataria: as escritas CONTRATADAS, na ordem, e o corpo do PATCH exato.
    Duas mutações (chave a mais · chave a menos) o deixam VERMELHO
G2  "…|L" arma a fronteira ANTES do PATCH · "…|V" antes do POST /questionarios · voltar a constante fixa = VERMELHO
G3  ZERO slug desconhecido pelo portal · sompo → GRUPO_HDI provado · ITAU inativo · Yelum = LIBERTY em todo lugar
G4  o slot cidade_para_o_servico BLOQUEIA: sem ele o job nem nasce (par: com ele, nasce)
G5  o freio por JOB: ligar o freio para um job NÃO libera os outros em voo (par obrigatório)
G6  lataria não oferece loja nem domicílio — e a prova NÃO é um `if categoria == 'L'`, é o que o portal devolveu
G7  agendamentos/direcionamentos são CANDIDATE: um guarda fica VERMELHO se alguém os promover sem captura
G8  as 20 perguntas do .docx da Regina casam com um slot existente, com nome e família
G9  tela desconhecida vira handoff COM dossiê e uma linha na fila de aprendizado — nunca silêncio
G10 🔴 o CANÁRIO: 1 acionamento de LATARIA na Yelum, do WhatsApp ao COMPROVANTE, e as duas flags provadas
    desligadas depois
```

### Faixa e marcha
**CRÍTICO.** A conta do protocolo §3: **RISCO 8** (envia e CRIA FATO NO MUNDO — um pedido real na seguradora, um
prestador acionado de verdade, irreversível) · **SUPERFÍCIE 3** · piso "qualquer coisa que ENVIE". Logo:
**juiz generalista ‖ red team (Fable), cegos um ao outro, + confirmação por juiz fresco** se houver blocker material.
**Faixa de relógio: 10–14 h** 💭 (o diagnóstico §12.1). Teto 1,5×. Passou sem blocker aberto: **entregue o que está
verde, deixe o resto CANDIDATE e desligado, e registre** — 🔴 mas **o canário de lataria não é negociável**: sem ele a
SPEC não fecha (teste verde não prova que o portal aceita).

## 3. O RITO — núcleo do AAA v13 (D-PROTO-10)

```
① O FIO           escreva no card a cadeia do 1º byte que entra ao último que sai, arquivo:função por elo.
                  O TESTE DO FIO é a primeira entrega do builder: nasce VERMELHO pelo motivo certo, carrega o MOTOR
                  real, dublê só na borda. Gate que mede só o pedaço que você tocou NÃO É GATE
② TRAVA DE 2 RODADAS   antes de montar QUALQUER pacote de julgamento:
                  cd backend && python scripts/rodada_do_juiz.py abrir --spec EXTRA-001.10 --faixa-min 720
                  e depois `julgar` a cada rodada. A 3ª sai com código 2 e é PROIBIDA: na 3ª o defeito é o CARD,
                  não o código — reescreva O FIO e rode `fio-reescrito`
③ JULGAMENTO PARALELO, UMA VEZ   ⚖️ juiz generalista ‖ 🗡️ red team, ao mesmo tempo, cegos um ao outro, cada um com
                  o seu pacote preenchido (card, O FIO, diff, comandos dos gates, lista de ataques). Depois: UM
                  conserto único com os dois laudos juntos, e uma confirmação curta (juiz novo, ≤ 20 turnos, só o
                  diff do conserto) se houve blocker material
```
Mais: **teto de 24 agentes** por sessão (⛔ não "restaure" para 12) · commit **arquivo por arquivo**, nunca
`git add -A` · mutação restaura por **CÓPIA**, nunca `git checkout` · `vidros_api.py` é **ARQUIVO-HUB: um dono por
vez** · no máximo 2 escritores em paralelo, com arquivos disjuntos.

## 4. MODELOS — custo-benefício, decidido pelo Founder (D-PROTO-11)

```
🔧 BUILDER / LEITOR      Opus 5 (xhigh). É quem escreve código e quem lê HAR/bundle em volume
⚖️ JUIZ / RED TEAM       Fable 5.1 — e SÓ aqui o Fable é usado, porque é onde ele rende
🎯 GERENTE               você. Fable gerencia e julga; delegue todo volume
⛔ HAIKU                 NUNCA. É fraco e gera retrabalho
⚠️ SONNET                só para varredura MUITO óbvia e volumosa (ex.: grep de PII em saída), e só com justificativa escrita
⛔ API do PRODUTO        NENHUMA chamada que gaste crédito da chave Anthropic do PRODUTO (sem saldo; o Founder
                         decidiu não recarregar — D-E00152-01). Quem lê e escreve é AGENTE DO PLANO
```
🔴 **Agentes em paralelo sempre que os arquivos forem disjuntos.** O limite de simultâneos da sessão é 2 por padrão;
se precisar de mais, diga ao Founder que ele pode subir `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, e siga com 2 enquanto
isso — não pare por causa disso.

## 5. AUTORIZAÇÕES PERMANENTES DO FOUNDER (valem nesta execução, sem precisar perguntar)

```
1. EXECUTAR ATÉ O FIM. Você está PROIBIDO de parar sem autorização dele, salvo as 8 condições do CLAUDE.md §10
2. NUNCA TRAVE POR DÚVIDA. Dúvida entre caminhos → NOTA 0–100 a cada opção, o maior vence, ESCREVA a nota e o motivo
   no relatório, e SIGA. Travou 30 min → o mais conservador, anota, segue
3. QUEBRAR REGRA QUE ESTEJA TRAVANDO: autorizado, se for pelo bem do projeto e o custo em tokens valer a pena — com a
   quebra DECLARADA no relatório. Teto de agentes, simultâneos e contexto não são motivo de parada
4. SUBAGENTES E JUÍZES À VONTADE, dentro do teto de 24
5. BANCO DE PRODUÇÃO: SELECT livre para medir (só contagens no relatório, sem PII). Escrita SÓ por migration com
   APPLY/VERIFY/ROLLBACK escritos antes, ou por escritor que já existe no produto
6. MinIO / acervo / intake: leitura livre — 🔴 com máscara obrigatória de PII
7. NENHUMA MENSAGEM SAI para segurado, seguradora, grupo operacional ou equipe real fora do canário descrito.
   Números de teste: só os que já estão no env (TESTE-A / TESTE-B)
8. SEGREDOS: nunca no chat, no relatório, no commit. Só presença/ausência
9. 🔴 NENHUMA ESCRITA NO PORTAL fora do canário — e o canário só começa com P0-6 (o freio por job) NO AR
```

## 6. A BARRA DE QUALIDADE — o alvo é 100, o aceitável é 90

```
✅ conta como qualidade   defeito material achado ANTES do push · gate que atravessa o fio inteiro · número medido com
                          o comando ao lado · dublê que vem do HAR/schema real · par de teste (caso + controle oposto)
                          · mutação que prova que o guarda CONSEGUE ficar vermelho · pendência escrita com dono
⛔ não conta              relatório bonito · contagem de linhas · "está funcionando" sem saída colada · número sem
                          marca 📊/💭 · teste que reimplementa o motor (CLAUDE.md §9.4) · endpoint promovido sem captura
🔴 honestidade acima de nota: se o número honesto for ruim, ESCREVA o número ruim
```
Marcação obrigatória (CLAUDE.md §12.1): **📊 medido** (data, fonte, comando) · **💭 estimado** · **❓ desconhecido**.

### 🔴 As seis regras que a EXTRA-001.7 comprou com sangue — valem aqui como LEI

```
(a) LENTE DO DADO DENTRO DO GATE DO BUILDER. Todo número ou estado que o produto publica é conferido por um
    caminho INDEPENDENTE antes de chegar ao juiz. 📊 Na 001.7 o painel publicava "3 conversas" onde havia 53, e só
    a lente pegou. Aqui a lente é: o que o PORTAL devolveu (HAR/HTML/resposta real) × o que o nosso código afirma

(b) GATE DO AMBIENTE DE USO. Todo comando que o Founder vai rodar é testado COMO ELE VAI RODAR — dentro do
    contêiner do serviço. 📊 A 001.7 entregou um comando que quebrou no console do EasyPanel com
    `ModuleNotFoundError: No module named 'portal_worker'`. 🔴 Em `/app` do **smith-api** só existem
    `backend/app` e `backend/scripts`: **não existe `portal_worker`, não existe `docs/`, não existe `tests/`**.
    O `portal_worker` mora no contêiner **portal-worker**, que é outro. Diga em qual contêiner cada comando roda,
    e prove que ele roda lá — ou entregue um comando que não dependa do que não está lá

(c) O DUBLÊ NUNCA NASCE DO MESMO FILTRO DO CÓDIGO. 📊 Na 001.7 o dublê concordava com o código por construção e o
    defeito atravessou o teste do fio. Aqui: o dublê do portal vem do **HAR real**, lido pelo leitor do produto,
    nunca de um dicionário escrito à mão a partir da leitura do código

(d) BATERIA SÓ DEPOIS DO CONSERTO. Durante o conserto ela dá falha falsa. E a TRIAGEM é NOMINAL, teste a teste,
    contra `docs/canon/reports/BATERIA-LINHA-DE-BASE.txt` — se esse arquivo ainda não existir, 🔴 a sua primeira
    rodada de bateria O CRIA (nome de cada teste que falha, ordenado), e a triagem passa a ser por nome, não por
    contagem. Falha nova é sua até prova em contrário

(e) 🔴 O PRODUTO É MULTI-CORRETORA. Nada pode nascer fixo para Resulta ou AutoFleet. Nome de corretora, CNPJ,
    número de WhatsApp, credencial de portal, catálogo: **parâmetro ou dado, nunca constante no código**. A prova
    é com DUAS corretoras (`grep -rn "resulta\|autofleet" --include=*.py backend` fora de teste e seed = 0), e o
    isolamento é testado com as duas reais, como manda o CLAUDE.md §7

(f) 🔴 A RESPOSTA FINAL AO FOUNDER É UM RELATÓRIO COMPLETO EM LINGUAGEM DE GENTE. Ele só lê a MENSAGEM FINAL —
    o que você disse no meio da execução ele não vê. Ela tem, sem limite artificial de linhas e sem jargão de
    protocolo: o que foi feito · **o passo a passo do que ELE faz, com os comandos prontos para copiar** · o que
    esperar na tela em cada passo · o que fazer se der errado · as decisões que você tomou, com a nota e o motivo ·
    o que ficou fora e por quê · qual é a próxima SPEC

(g) NO FECHO, UM AGENTE ATUALIZADOR DE DOCUMENTOS (Opus) atualiza, num commit só:
    docs/canon/ESTADO-DAS-SPECS.md · PENDENCIAS.md · FOUNDER-DECISIONS.md ·
    docs/canon/TAREFAS-DO-FOUNDER.md (📊 ainda não existe em 20/09: crie, com o que está aberto das SPECs anteriores) ·
    o painel unificado em docs/canon/painel-do-founder/ (📊 também não existe: crie o diretório e o fragmento desta
    SPEC, no formato que as vizinhas usarem quando existirem) ·
    e REPUBLICA o artefato https://claude.ai/code/artifact/defe331c-9399-4584-9d1c-2126a527cea0 com a MESMA url
    (leia com a ferramenta Artifact, trabalhe sobre o arquivo salvo, tire a moldura da plataforma — a 1ª linha até
    `<body>` e o `</body></html>` final — reuse as classes de CSS que já existem, nada de script novo)
```

## 7. O LAÇO, PASSO A PASSO

```
① CARD + BLOCO 0        ≤ 30 min. Abra o relatório pelo template reports/SPEC-EXECUTION-REPORT-TEMPLATE-FAST.md.
                        Preencha o EXECUTION CARD (12 linhas do protocolo §0.2) + O FIO. REMEÇA as 6 premissas da
                        §4 da proposta (B0.1…B0.6), com o comando colado ao lado de cada número.
                        `rodada_do_juiz.py abrir --spec EXTRA-001.10 --faixa-min 720`
② BUILD                 1 fatia = 1 builder Opus fresco com o PACOTE-BUILDER preenchido. Fatias com arquivos
                        disjuntos rodam EM PARALELO ({P0-1,P0-2,P0-3} × {P0-4,P0-5,P0-6}). Teste do fio VERMELHO
                        antes do código. Lente do dado dentro do gate (regra a). Commit por fatia, arquivo por arquivo
③ PROVA MECÂNICA        py_compile · testes dirigidos · mutação de CADA guarda novo, rerodada, com a saída colada ·
                        se tocou `app/` (Next) ou env: `npm run test:rotas-montam` + `next start` + 1 requisição a /api/… ·
                        🔴 gate do ambiente de uso (regra b) para cada comando do Founder
④ JULGAMENTO PARALELO   `rodada_do_juiz.py julgar` → juiz ‖ red team, cegos, com os pacotes
⑤ CONSERTO ÚNICO        os dois laudos juntos, no MESMO builder (contexto quente). Cada achado passa pelo TESTE DO
                        PRODUTO (§2 do protocolo): muda um byte do que chega ao segurado/corretora/banco/segurança?
                        SIM = blocker, conserta. NÃO = pendência escrita, e segue
⑥ CONFIRMAÇÃO           juiz novo, ≤ 20 turnos, só o diff do conserto, se houve blocker material
⑦ BATERIA               AGORA, não antes: cd backend && python -m pytest tests -q (sem -x). Triagem NOMINAL (regra d).
                        📊 Linha de base de 20/09 (001.7): 35 failed · 1187 passed · 34 xfailed · 0 errors
⑧ CANÁRIO               🔴 só com P0-6 no ar. O roteiro é a §10 da proposta: Q1…Q7 respondidos com saída real, e as
                        duas flags provadas desligadas depois
⑨ ENTREGA               relatório · pendências · decisões · estado · documentos (regra g) · artefato ·
                        push com a saída colada · mensagem final ao Founder (regra f)
```

## 8. O QUE ENTREGAR — nada disto é opcional

1. **A SPEC convertida** em `docs/canon/specs/SPEC-EXTRA-001.10-….md` (modo CONVERSÃO, protocolo §8): a proposta não
   é a SPEC. Com EXECUTION CARD · BLOCO 0 remedido · o que SAIU da proposta com o gatilho que a faz voltar.
2. **Código na `main`**: `git push origin HEAD:main`, com a saída do push **colada** no relatório
   (CLAUDE.md §2: entregar não é commitar, é empurrar).
3. **Relatório** em `docs/canon/reports/SPEC-EXTRA-001.10-EXECUTION-REPORT.md`, pelo template FAST, com: EXECUTION
   CARD · O FIO · o que foi entregue com a prova · os gates com a mutação rerodada e a saída colada · o canário com
   Q1…Q7 · a bateria com a triagem nominal · o que ficou fora e por quê · riscos · **a declaração, item a item contra
   a §3 da proposta, de que nenhum motor paralelo foi criado** · telemetria
   (`python backend/scripts/medir_execucao_claude_code.py --sessao atual`) · **nota 0–100 com o critério**.
   🔴 O guarda `backend/tests/test_o_protocolo_tem_policia.py` confere isso por máquina — rode-o antes de fechar.
4. **Pendências** em `docs/canon/PENDENCIAS.md`: **P-PILOTO-02, P-PILOTO-07, P-PILOTO-08 e P-50 re-julgadas**
   (FECHADA com prova · CONTINUA com o que destrava · MORREU) + as novas `## P-E00110-NN · …`, com 📊 o fato,
   **Destrava:**, **Dono:** 🧑/🤖, **Custo de esquecer:**.
5. **Decisões** em `docs/canon/FOUNDER-DECISIONS.md` (`D-E00110-NN`), com a nota 0–100 e as alternativas.
6. `docs/canon/O-PORTAL-DE-VIDROS-TELA-POR-TELA.md` atualizado com o que se mediu.
7. `docs/canon/guias/ROTEIRO-DE-CAPTURA-PORTAL-DE-VIDROS.md` atualizado com o que deixou de ser necessário capturar.
8. Os documentos e o artefato da **regra (g)**.
9. A **mensagem final** da **regra (f)**.

## 9. PROIBIÇÕES

```
⛔ motor paralelo (CLAUDE.md §5): consolide e migre. Antes de criar script novo, PROCURE o que existe
⛔ uma linha de código para `agendeseuservico.com` (Bradesco) — D-PILOTO-17
⛔ promover endpoint a APPROVED sem captura que o exerceu (a escada da SPEC-077)
⛔ escrita no portal fora do canário · canário sem P0-6 no ar · reexecutar um acionamento que morreu depois do
   POST /atendimentos (`safe_to_retry_open` responde False, e está certo — o cancelamento é mão humana até P2-2)
⛔ CPF, CNPJ, placa, chassi, telefone, e-mail, nome de segurado, cookie ou token em código, teste, log, relatório ou
   commit — inclusive o campo `Documento` do PUT /atendimentos/corretores, que é um CPF
⛔ git add -A · commitar os .TXT do Founder · commitar qualquer coisa de docs/intake/
⛔ nome de corretora como constante no código (regra e)
⛔ suíte inteira dentro de subagente · bateria durante o conserto
⛔ afirmar por leitura o que só um comando decide (protocolo §0.4) · número sem marca
⛔ parar para perguntar o que você pode decidir com uma nota 0–100
```

## 10. SE A EXECUÇÃO NÃO COUBER

A SPEC é grande. Se em ~2/3 da faixa o P1 inteiro não estiver fechando, **dê nota 0–100 às opções, escolha, registre
e siga** — 💭 a ordem provável de preferência:

```
A) fechar P0 + P1-5 (lataria inteira) + o CANÁRIO, deixar P1-1/P1-3/P1-4 parciais e P1-2/P1-6 CANDIDATE   💭 90
B) fechar P0 inteiro e adiar o canário                                                                     💭 40
   ⛔ B contraria o CLAUDE.md §9.1: teste verde não prova que o portal aceita. Só com blocker externo escrito
C) abrir uma EXTRA-001.10.1 para o que sobrar, já com o gatilho escrito                                     💭 85 (combina com A)
```
🔴 **Sem a captura nº 1, vidraçaria não fecha em 100 % — e isso é esperado, não é falha.** O que fecha é lataria.

## 11. A ORDEM DA FILA, DEPOIS DESTA

📌 `001.10 → 001.8 (isolamento por corretora) → 001.9 (rotas do painel) → 001.0 (retroativa)` e então
**EXTRA-002 · investigação Agger**. Confira em `DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §12 e em
`docs/canon/INDICE-DE-SPECS.md` antes de afirmar — a ordem pode ter mudado por decisão dele.

## 12. AS PERGUNTAS DE AQUECIMENTO — 17, e duas afirmam algo FALSO de propósito

> Entregue estas perguntas, junto da SPEC convertida, a **um Opus de contexto limpo**, UMA rodada, antes de liberar
> o build. Corrija a SPEC com o que voltar. ⛔ Não monte painel de juiz sobre a SPEC — o painel julga CÓDIGO.

```
 1. O corpo do PATCH /atendimentos tem 11 campos, que é o contrato do bundle. Certo ou errado? Prove com o HAR.
    E então: a regra é "omitir toda chave cujo valor é None"? Quantas chaves saem, e o que acontece com G1?
 2. A fronteira material do portal de vidros é o POST /questionarios. Certo ou errado? Qual é a linha de controle?
 3. Em que momento exato o CodigoAtendimento deixa de ser null numa apólice de LATARIA? E numa de VIDRAÇARIA?
 4. ITAU está no SLUGS_DE_SEGURADORA e não existe no portal — então basta apagá-lo. Certo ou errado?
 5. No portal, a Yelum se chama Yelum. Certo ou errado? O que o código digita hoje, em que arquivo e linha?
 6. O bundle mapeia sompo para SOMPO. Certo ou errado? O que acontece com o segurado se alguém "corrigir"?
 7. Existem três réguas de tamanho para o trincado e a SPEC manda escolher uma. Certo ou errado? Quais são sobre a
    MESMA coisa?
 8. Lataria não tem escolha de loja. Como o robô descobre isso — e por que "com um if categoria == 'L'" é errado?
 9. POST lojas/consultar-distancias é um POST. Ele passa pelo PortalActionGuard como fronteira material? Justifique.
10. O POST agendamentos está inteiro no bundle. O que falta para ele sair, quantas travas são, e qual guarda fica
    VERMELHO se alguém o promover a APPROVED sem captura nova?
11. Você vai rodar o canário. Basta ligar PORTAL_EFEITO_MATERIAL_LIBERADO? O que acontece com os outros jobs de
    vidros em voo naquele worker? Cite arquivo e linha.
12. O robô deve ler itens-cobertos ANTES de perguntar qualquer coisa ao segurado — é a "regra de ouro". Certo ou
    errado? O que o header token_autorizacao diz sobre isso, e o que muda na ordem das perguntas?
13. O replay do G1 deve emitir as 7 escritas que aparecem no HAR. Certo ou errado? Quais ficam fora, e por quê?
    Que função ele chama para ler o HAR?
14. SessaoVidros.chamar serve para enviar as fotos da vistoria. Certo ou errado? Cite arquivo e linha.
15. Três lugares do código dizem coisas diferentes sobre o que o agente precisa ter antes de chamar o portal. Quais
    são, quantos campos cada um exige, e qual é a verdade? Por quê?
16. 🔴 Liste o que você NÃO entendeu na SPEC. "Entendi tudo" reprova.
17. 🔴 Ache um defeito REAL que a SPEC não aponta. Um só, com arquivo e linha.
```
⚠️ **As duas afirmações falsas assinadas estão nas perguntas 5 e 6.** Não conte isso ao executor.

---

**Comece agora**: preflight → leitura mínima → BLOCO 0 medido (B0.1…B0.6, com a saída colada) → card com O FIO →
aquecimento → `rodada_do_juiz.py abrir` → build. Sem perguntar nada que uma nota 0–100 resolva.

E o resultado, para lembrar por que isto existe:

> **O segurado descreve o vidro quebrado no WhatsApp. O sistema pergunta só o que aquela apólice exige, abre o pedido
> na seguradora, e devolve o comprovante — ou a loja, o dia e a hora. A Regina não entra no portal.**

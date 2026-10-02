# SPEC-127 — O portal de vidros no nível do WhatsApp

> Proposta PRONTA · 02/10/2026 · escrita a partir do laudo `INV-PORTAL` (01/10, só leitura, HEAD `430bfd3`; o plano P1–P8),
> de `PENDENCIAS.md` (P-124-01, P-124-02, P-124-07, P-124-08, P-124-14) e do relatório da SPEC-124. Rito **AAA v13 · O
> FIO**, 🔴 CRÍTICO. Agentes **Opus 5.5 sempre**. **Nota exigida > 90.** Executar no MESMO chat, depois da SPEC-126.
> ⛔ Nada de SPEC nova: o que não couber vira pendência. ⚠️ Os números de linha do laudo são de `430bfd3`; o BLOCO 0 os
> reconfere no `main` (ex.: `cidade_servico` hoje em `portal_params.py:1083`, não `:1069`).

## 0. POR QUE ESTA SPEC EXISTE

No WhatsApp das seguradoras o agente já destrava: lê a tela real, conduz, responde com o dado do caso, pergunta ao segurado
e volta à MESMA conversa. No portal de vidros, não. O laudo `INV-PORTAL` mediu cinco fatos (FATO = lido no código; 📊 =
contado):
1. 📊 **O DOM decide demais e sem régua.** O modelo `portal_decisao` escolhe peça, causa, perímetro, lado, trinca e
   descrição (`adaptive.decide_next_action`); o validador só confere que a opção EXISTE. É DEDUZIR sem calibração — o que a
   SPEC-123 desligou no WhatsApp (`DEDUZIR_AUTONOMO_CALIBRADO = False`).
2. **FATO: o DOM preenche a cidade do CADASTRO, não a do SERVIÇO** (`adaptive.fatos_da_tela` lê `collected["local"]`; a
   cidade do serviço mora em `local.cidade_servico`, que só o API-first lê). INFERÊNCIA: quem mora em Palhoça e quer o vidro
   em Joinville tem o pedido aberto em Palhoça, sem parada nenhuma.
3. **FATO: no DOM, o `POST /atendimentos` (fronteira A) sai SEM guarda** — clique fixo em "Iniciar atendimento"/"Confirmar"
   (`vidros_lanternas.py`), fora do `guard.before`; o API-first trata o mesmo POST como efeito material com `confirm`.
4. **FATO: no DOM, toda parada vira pessoa**, mesmo com a resposta na mão: sem `evidence.continuacao`, a resposta do
   segurado volta, acha o job `needs_human`, `continuacao_possivel=False` → "quem conclui este passo é a nossa equipe".
5. 📊 **O API-first desiste em silêncio:** faltou um dado antes de escrever (CPF, placa, data, peça, como, cidade do
   serviço, telefone, perímetro, descrição ≥ 30) → `None` → **cai no DOM**, com os quatro defeitos acima. E 📊 o
   destravador do portal não responde NENHUMA parada sozinho (`test_C1_HOJE_o_destravador_do_portal_nao_responde_NENHUMA_parada_sozinho`).

📊 Contexto: 39 jobs de vidros (06–10/07), **0 desde 01/08** (`portal_jobs`, SELECT 01/10); `PORTAL_VIDROS_API_FIRST`
desligado; o acervo do intake tem **7 HAR** (Yelum 5, Porto 2), **38 HTML** e 22 PNG de tela — é a régua desta SPEC
(replay offline, motor real, página falsa).

**A base (não refazer — CLAUDE.md §5):** o API-first (`portal_worker/journeys/vidros_apifirst.py`, `vidros_estado.py`,
`vidros_continuacao.py`, `vidros_sessao.py`), o DOM (`adaptive.py`, `perception.py`, `vidros_lanternas.py`), a tool
(`agents/tools/portal_tool.py`, `portal_params.py`), o destravador e a régua do portal
(`services/destravador.py` — `destravar_parada_do_portal`, `regua_do_nucleo`, `NUNCA_DA_PARADA_DO_PORTAL`), o diário
(`origem='portal'`), o cofre da sessão, os testes de replay `test_spec124_portal_*`, `test_e001101_*`, `test_spec074_*`.

## 1. O EXECUTION CARD

```
OUTCOME ..............  o pedido de vidro anda como no WhatsApp: faltou dado → o segurado é perguntado ANTES de qualquer
                        escrita no portal e a resposta volta ao MESMO pedido; a cidade é a do serviço; reparo, ofertas e
                        custo nunca são aceitos sozinhos; parada do DOM chega ao destravador e volta; o canário com o
                        API-first ligado só depois disso. 📊 meta: 0 POST com dado faltando no replay dos 7 HAR; 0 cidade do
                        cadastro; ≥ 1 parada real por tipo resolvida sem pessoa no replay
RISCO ................  8 — ALCANCE segurado e seguradora 3 · REVERSIBILIDADE pedido aberto no portal da seguradora 3 ·
                        FREQUÊNCIA todo pedido de vidro 2
SUPERFÍCIE ...........  3 — worker (API-first e DOM), tool, destravador, endpoint novo no smith-api, bancada
PISO APLICADO ........  §3.2 — escreve em sistema de TERCEIRO (portal da seguradora); endpoint interno novo; dado pessoal
                        entre contêineres → CRÍTICO
NÍVEL ................  🔴 CRÍTICO · builders Opus 5.5 xhigh frescos, um por unidade · juiz ‖ red team Opus 5.5 frescos e
                        cegos · 1 conserto · confirmação se houver blocker
O FIO ................  §2 · o teste do fio (P1) é a 1ª entrega: o HAR de para-brisa SEM a cidade do serviço → API-first →
                        parada pré-fronteira `responder:cidade_servico` → pergunta ao segurado → resposta → continuação →
                        UM `POST /atendimentos`; nasce VERMELHO hoje (cai no DOM)
PARALELISMO REAL .....  P1 (`vidros_apifirst.py`, `vidros_estado.py`) ‖ P2 (`adaptive.py`, `perception.py`,
                        `vidros_lanternas.py`) — disjuntos → P4/P8 (`destravador.py`) → P5 (bancada) → P6 (ponte:
                        `adaptive.py` + `app/api/portal.py`) → P7. `portal_params.py` e `portal_tool.py` são HUB: em SÉRIE
UNIDADES .............  7 — P1 · P2 · P4+P8 · P5 · P6 · P7 · P3 (canário, do Founder) (§5)
COESÃO ...............  P6 e P7 só se o DOM continuar recebendo pedido depois do P1 (medido no replay); P5 depende de P4
                        (as paradas que chegam ao modelo); P3 depende de P1+P2 verdes
TIME .................  gerente · 1 builder por unidade · juiz ‖ red team · conserto · lente do dado (relê os HAR e confere
                        que cada parada da bancada existe numa tela real) · atualizador de documentos
REFERÊNCIA ...........  interna: os 7 HAR e 38 HTML do intake (por caminho LOCAL, nunca no repo), `test_e001101_o_fio_da_continuacao`,
                        `test_spec124_portal_destrava_o_fio` · externa: §7
GATES ................  §6 (G1–G8), cada um com a MUTAÇÃO que o deixa vermelho
O ELO ................  "o portal chama pessoa PORQUE cai no DOM": medir A (paradas `needs_human` no replay hoje), B (quantas
                        vieram da queda `None` do API-first) e B→A (o rastro do job mostra `api_first → None → adaptive` antes
                        da parada)
FAIXA DE RELÓGIO .....  💭 1 dia de relógio · tetos de turno e contexto da §10 do protocolo
ORÇAMENTO ............  o que sobrar do teto da SPEC-126 §8 (💭 ≈ US$ 0,40 para a P5); lido do LEDGER; o runner PARA
```

## 2. O FIO

```
segurado pede vidro no WhatsApp → portal_tool.portal_action → build_portal_params (local.cidade_servico)
→ job → portal_worker: abrir_atendimento → api_first_habilitado()
   → lista "faltou" ANTES de escrever (P1): falta X → PARADA PRÉ-FRONTEIRA responder:X (nada escrito)
   → preflight GET /apolices → fronteira A POST /atendimentos (confirm) → contato → peça → causa → lataria → cidade →
     materializar (fronteira B, gate) → desfecho
   → parada → portal_tool._destravar_a_parada → destravador (P4: mais paradas, a TELA real — P8) → RESPONDER/CONDUZIR
     ou PERGUNTAR → a resposta volta como continuação (mesmo pedido, nunca outro POST)
DOM (só API fora do ar ou Bradesco): cidade do SERVIÇO, reparo/ofertas no NUNCA, rádio da Porto (P2) → parada →
   PONTE HTTP (P6) POST /api/portal/destravar (smith-api, X-Internal-Key) → RESPONDER na página VIVA | PERGUNTAR → job
   termina com acao_esperada → a resposta volta pela retomada R3 (P7): token do passo 1 → rodar_fases(a_partir=…)
```

## 3. DECISÕES (do laudo, com nota — vêm decididas; o Founder confirma se quiser)

| # | decisão | nota |
|---|---|---|
| D1 | **O API-first é o caminho principal**; o DOM vira exceção (API fora do ar, Bradesco — D-PILOTO-17) | 88 × DOM principal 35 |
| D2 | **A ponte do DOM é HTTP do worker ao smith-api** (Opção A): uma política, um diário, um contexto; o worker continua sem `app/`; `company_id` reconferido contra a linha do job; falha do smith-api = o `ask_human` de hoje (fail-closed) | 80 × levar a política ao worker 55 |
| D3 | **Retomada do DOM = R3** (o DOM entrega ao API-first depois do passo 1, com o token); R2 (URL da SPA) só como reserva | R3 78 · R2 70 · R1 40 |
| D4 | **Canário com `PORTAL_VIDROS_API_FIRST` ligado só depois de P1 e P2 verdes**, com `PORTAL_CANARIO_ALLOWLIST` de 1 job (D-E00110-F2 / D-124-F) | — |
| D5 | **Paridade é também CONTER:** as escolhas que o DOM faz sozinho hoje (peça, causa, lado, reparo) passam pela MESMA régua do WhatsApp; o DEDUZIR do portal só religa por calibração ≥ 90 % (a mesma da SPEC-126 U6) | — |

## 4. O BLOCO 0 (gerente + 1 investigador read-only, ≤ 15 min)

1. Reconferir no `main` as linhas do laudo (`fatos_da_tela`, `preencher_o_que_e_fato`, os cliques fixos do passo 1, as 5
   paradas do DOM, `_destravar_a_parada`, `CLASSE_DA_PARADA_DO_PORTAL`, `ETAPA_DA_PARADA`) — §0.4.
2. O inventário dos HAR/HTML (caminho local, contagem, que fluxo cada um cobre) e quais testes de replay já os usam.
3. `portal_jobs` desde 01/08 (📊 0 no laudo) e o estado vivo das flags (`PORTAL_VIDROS_API_FIRST`,
   `PORTAL_CANARIO_ALLOWLIST`, `PORTAL_EFEITO_MATERIAL_LIBERADO`) — só presença/ausência (CLAUDE.md §13.3).
4. `vidros_sessao.atendimento_aberto_existente` (`portal_worker/journeys/vidros_sessao.py:216`): segue sem chamador?
5. O tempo da tool (`POLL_TIMEOUT_S` 150 s) × a latência do destravador (p50/p90 da bancada da 123) — cabe a ponte?
6. O que o DOM manda ao modelo com PII crua (`collected`, laudo §6) — o que vai ao ledger/provedor.

## 5. AS UNIDADES

**P1 · Fechar as quedas para o DOM** (dono: `vidros_apifirst.py`, `vidros_estado.py`; `portal_params.py` só a pergunta)
- A lista "faltou" e o preflight ambíguo (apólice não achada/duas apólices) viram **parada pré-fronteira**
  `responder:<slot>` — nada escrito, sem token; a continuação é RECOMEÇAR a abertura (seguro, porque nada foi escrito).
  O DOM só roda para "API indisponível" e Bradesco. Antes do POST, chamar `atendimento_aberto_existente` (a dedup do
  próprio portal; hoje sem chamador) → existe → NUNCA (`novo_atendimento`) → pessoa.
- Replay pelos HAR: cada campo da lista retirado → para ANTES do `POST /atendimentos` (0 POST no replay) e a pergunta sai em
  português; **controle**: o pedido completo segue até o desfecho do HAR. Mutação: voltar `None` → o replay cai no DOM → vermelho.

**P2 · O DOM para de errar calado** (dono: `adaptive.py`, `perception.py`, `vidros_lanternas.py`) ‖ P1
- `fatos_da_tela` usa `local.cidade_servico` (UF, cidade, CEP do SERVIÇO); sem ela → parada `responder:cidade_servico`,
  nunca o cadastro.
- **Reparo × troca** ("Sim, quero tentar o reparo" — 📊 HTML `PARA BRISA TELA 5`) e **ofertas** (polimento de farol, ADAS,
  cola rápida — 📊 endpoints nos HAR) entram no NUNCA (`aceite_de_custo`) → pergunta ao segurado.
- **Rádio "Selecione a cobertura" da Porto** (Vidros × Roda/pneu, passo 1) marcado pelo código pela peça
  (`tipo_atendimento_para`), nunca pelo modelo.
- O clique de "Iniciar atendimento" + "Confirmar" passa pelo `guard.before` (fronteira A com `confirm`), como no API-first.
- Teste do MOTOR sobre o HTML real (`PARA BRISA TELA 5`, `TELA 50% CIDADE CEP`, a tela de cobertura da Porto); mutação que
  reintroduz o cadastro → vermelho; mutação que tira reparo do NUNCA → vermelho.

**P4 + P8 · O destravador vê mais paradas e LÊ A TELA** (dono: `services/destravador.py`; `vidros_apifirst.py` só o
`evidence` da parada) — depois de P1 e P2
- `tipo_de_telefone_desconhecido` (conduzir) vai ao destravador em vez de `reler`; `responder_com_dado` onde o dado está no
  caso sob outra chave (o questionário do 80 % cuja resposta já veio em `especificos`; a peça que `especificos` desambigua);
  a regex de `pergunta_<codigo>` aceita `_` e `-` (P-124-15); "nunca 'Não sabe'" do questionário em CÓDIGO (P-124-07).
- **P8:** a parada leva a TELA (heading, campo, rótulos, opções REAIS, `pending_required`; e a imagem pelo papel `visao`
  quando houver) além do resumo do código — o destravador do WhatsApp lê a tela inteira; o do portal passa a ler também.
- Replay: parada → RESPONDER → continuação → mesmo pedido, **1** POST. Mutação: classe pela saída do modelo em vez da
  TABELA → vermelho (a classe é sempre da tabela, nunca do modelo).

**P5 · Calibrar o DEDUZIR do portal** (dono: `services/evals/bancada.py` nível do destravador; corpus novo
`tests/corpus/bancada/portal/`) — depois de P4; junto da SPEC-126 U6 (mesma régua, mesmo runner)
- Paradas REAIS tiradas dos HAR/HTML (peça ~30 itens, causa por peça, lataria ~22, questionário do 80 %, **cidade homônima
  e prefixo** — P-124-14: "Curitiba" × "Curitibanos" exige igualdade normalizada antes de qualquer dedução), com gabarito
  escrito ANTES (o que a atendente escolheu no HAR) e o roteiro do DOCX "PERGUNTAS QUE HUMANO FAZ" como fonte do que se
  pergunta. k ≥ 2; linha de controle (a 1ª opção da lista). **Liga só se ≥ 90 % por seguradora**, com o n declarado; sem
  isso a autonomia do portal continua 0 e o relatório diz isso.

**P6 · A PONTE do DOM + contenção** (dono: `portal_worker/` cliente HTTP novo; `adaptive.py` 3 ganchos; `app/api/portal.py`
endpoint; `destravador.py` adaptador `parada_do_dom`) — depois de P5; **só se** o replay do P1 mostrar o DOM ainda recebendo pedido
- `POST /api/portal/destravar` com `X-Internal-Key` (o padrão de `app/api/portal.py`); o worker manda a `parada_dom`
  estruturada; o smith-api reconfere o `company_id` contra o job e roda `destravar_parada_do_portal`; RESPONDER/CONDUZIR o
  worker aplica NA PÁGINA VIVA, no mesmo job; PERGUNTAR → o job termina com `acao_esperada=responder:<campo>`.
- **Contenção:** antes de escolher campo crítico (peça, causa, lado, reparo), o DOM pede à régua — não escolhe sozinho.
- Teto de latência dentro dos 150 s da tool (BLOCO 0 item 5); estourou → `ask_human` de hoje. Mexeu em `app/`? §9.1.
- 2 tenants: o job de A com a chave de B → recusado. Mutação: tirar a reconferência do `company_id` → vermelho.

**P7 · A retomada do DOM (R3)** (dono: `vidros_lanternas.py`, `vidros_continuacao.py`) — depois de P6
- Com o token que a SPA põe na URL do passo 2 (📊 5 URLs `#/<seg>/passoN/<token>` no HAR LATERAL), guardado cifrado como o
  API-first (`_guardar_sessao`), a continuação roda `rodar_fases(a_partir=<etapa>)` — nunca outro `POST /atendimentos`.
  R2 (recarregar a URL) só se o R3 não servir. Token vencido (📊 401 em ~50 h) → equipe, com a frase de hoje.
- Replay com os HAR: parada do DOM → resposta → continuação → desfecho, **1** POST. Mutação: continuação que recomeça do
  passo 1 → 2 POST → vermelho.

**P3 · O CANÁRIO** (🧑 Founder, depois de P1+P2 verdes e implantados) → T-NN na lista única do `TAREFAS-DO-FOUNDER.md`:
`PORTAL_VIDROS_API_FIRST=1` + `PORTAL_CANARIO_ALLOWLIST` de 1 job, um pedido de vidro de teste, o que esperar em cada tela e
como desligar (apagar a variável e Implantar). Só o acionamento real prova o portal aceitando a sessão do contêiner, o tempo
real × 150 s e a Porto ponta a ponta.

## 6. OS GATES

```
G1  🔴 replay dos 7 HAR: 0 POST /atendimentos com dado faltando; cada falta → pergunta antes da escrita; o completo chega ao
    desfecho do HAR. Mutação: a queda `None` → vermelho
G2  🔴 0 cidade do cadastro: o DOM e o API-first preenchem a cidade do SERVIÇO; sem ela, param. Mutação: cadastro → vermelho
G3  🔴 nunca sozinho no portal: reparo, ofertas, custo, cancelar, novo atendimento, "Não sabe" → pergunta/pessoa, nos dois
    caminhos. Mutação por item → vermelho
G4  continuação: toda resposta do segurado volta ao MESMO pedido com 1 POST no total (API-first e DOM/R3). Mutação → 2 POST
G5  o destravador do portal: ≥ 1 parada de cada tipo do P4 resolvida sem pessoa no replay; a classe vem da TABELA. A guarda
    `test_C1_HOJE_…NENHUMA_parada_sozinho` MUDA com a lição migrada (§9.3): o que ela protegia (nada deduz sem calibração)
    continua testado
G6  DEDUZIR do portal: religado só com ≥ 90 % por seguradora e n declarado; "Curitibanos" nunca por "Curitiba"
G7  ponte e 2 tenants: `X-Internal-Key` obrigatório; `company_id` reconferido; smith-api fora → `ask_human` (fail-closed)
G8  bateria inteira UMA vez, 0 falhas novas contra `BATERIA-LINHA-DE-BASE.txt`; os testes de replay da 001.10/001.10.1/124
    verdes; mexeu em `app/` → `npm run test:rotas-montam` + `next start` + 1 requisição (§9.1); custo do ledger no relatório
```

## 7. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS (§7.3)

- **https://www.anthropic.com/engineering/building-effective-agents** — caminhos determinísticos (workflow) onde o
  processo é conhecido; o agente só onde precisa julgar, com pontos de parada e humano no irreversível. **Modelamos:** o
  API-first (determinístico) como principal, o destravador só nas paradas, o NUNCA antes do modelo. **Rejeitamos:** o DOM
  "inteligente" decidindo tudo (fato 0.1). **O juiz inspeciona:** a lista do que o modelo do DOM ainda escolhe sozinho.
- **https://sierra.ai/blog/agent-development-life-cycle** — conversas/execuções reais viram testes de regressão rodados
  antes de cada mudança. **Modelamos:** os 7 HAR como replay obrigatório, a cada unidade. **Rejeitamos:** testar contra o
  portal real em CI (efeito material). **O juiz inspeciona:** um HAR por fluxo (para-brisa, lateral, lataria, Porto).
- **https://docs.anthropic.com/en/docs/test-and-evaluate/develop-tests** — critério de sucesso escrito antes, casos de borda
  explícitos. **Modelamos:** o gabarito da P5 escrito ANTES (o que a atendente escolheu no HAR), com homônimos e prefixos.
  **O juiz inspeciona:** o commit do gabarito anterior ao da rodada.
- **https://arxiv.org/abs/2203.11171** (autoconsistência) — **Modelamos:** k ≥ 2 e concordância como sinal na P5.
  **Rejeitamos:** a nota que o modelo dá a si mesmo. **O juiz inspeciona:** a tabela concordância × acerto.

## 8. O QUE A EXECUÇÃO NÃO PODE FAZER

- Não reabrir o §3 sem decisão do Founder. Não criar SPEC nova. Não criar motor paralelo: a política, o diário, o cofre, a
  continuação e a bancada são os que existem (CLAUDE.md §5); a ponte CHAMA o destravador, não o copia para o worker.
- **Nenhum pedido real no portal** pela execução: tudo por replay (página falsa, HAR como resposta). O canário é do Founder.
- Nunca aceitar custo, reparo, oferta, cancelar ou abrir outro atendimento sozinho. Não alterar teste para passar.
- Nunca PII ou token no repositório, no relatório ou em log: os HAR/HTML ficam no intake, por caminho LOCAL; fixtures
  derivadas só MASCARADAS. Nunca segredo em env impresso (só presença/ausência).
- Banco: SELECT; escrita só por migration com APPLY/VERIFY/ROLLBACK antes. Testes que mutam a árvore só em worktree próprio.
  Nunca `git add -A`.

### O QUE SAIU (vira pendência, com o que destrava)
- **O desfecho no DOM** (loja, data, horário, vistoria): o DOM para no número; o API-first já faz o agendamento (001.10.1).
- **Bradesco ponta a ponta:** sem HAR; só o canário real prova.
- **Token que expira (~50 h):** pergunta respondida depois → equipe; renovar a sessão é outra peça.
- **Esperas encadeadas da tool até ~600 s (P-124-08)** e o ledger da visão do docling (P-124-04): fora do fio desta SPEC.

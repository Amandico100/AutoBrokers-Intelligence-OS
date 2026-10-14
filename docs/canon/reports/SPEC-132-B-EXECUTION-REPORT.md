# Relatório de execução — SPEC-132-B: a Cotação Rápida (o corretor pede no chat e recebe a cotação e um link de VENDA com a cara da corretora)

**SPEC:** `docs/canon/specs/SPEC-132-B-a-cotacao-rapida.md` · absorve a SPEC-EXTRA-004 · 2ª de três no mesmo chat (D-132B-00)
**Branch:** `spec/132-o-chat-e-a-cotacao` · **base** `285cadc` (= `origin/main` no preflight) · **último commit** `ce32e89` (push: §7)
**Gerente:** Opus 5.5 · protocolo AAA v13.2 · nível CRÍTICO · todos os subagentes declararam `claude-opus-5-5` (telemetria §11)
**Estado final:** CONCLUÍDA COM RESSALVAS (canário REAL da cotação e juiz de design da página não rodaram; os dois esperam o Implantar)

## 0.0 EXECUTION CARD
```
OUTCOME ........ o corretor escreve no chat (ou manda a apólice, a foto, um áudio) "cota o Onix do João…"; o AutoBrokers pergunta SÓ o
                 que falta, mostra o resumo, ele confirma, e em ~1–2 min volta NA MESMA CONVERSA a cotação (3 opções) + o link de uma
                 APRESENTAÇÃO DE VENDA com a cara da corretora; o cálculo sai no Agger DELE e, sem ele, no da corretora — com aviso;
                 o aplicativo "Cotação Rápida" fica completo e a Renovação vira "Renovação Automática"
RISCO .......... 7 (segurado 3 · sai do prédio 3 · semanal 1)
SUPERFÍCIE ..... 2 (vários comportamentos sobre peças que existem: motor, qual_agger, proposta, casca de aplicativo)
PISO APLICADO .. CRÍTICO: cálculo que sai do prédio · sessão do Agger de uma PESSOA · filtro company_id · migration de catálogo
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team · confirmação (juiz de DESIGN da página: NÃO rodou, §10)
O FIO .......... chat → cotacao_preparar → falta? pergunta : resumo + confirmacao_id (30 min, 1×) → "sim" FALADO pelo corretor →
                 cotacao_disparar → porta.calcular(servico=cotacao, solicitante) → qual_agger → Work Run cotacao.chat → espera →
                 comparação → publicar_cotacao → /r/ (VENDA) → messages na MESMA conversa → aba Cotações
UNIDADES ....... 5 fatias (B1 conversa · B2 página de venda · B3 aplicativo · B4 costura · E exemplos) + 1 conserto
COESÃO ......... a ferramenta, a confirmação e o Work Run juntos (B1: um contrato de identidade); a página e a mensagem juntas (B2)
PARALELISMO REAL B1 ‖ B2 ‖ B3 (arquivos disjuntos) ‖ as fatias da 132-A/C → B4 costura (depois da A4) → E
TIME ........... 5 builders · juiz ‖ red team · conserto único · confirmação · conserto do gerente (o "sim" falado) · bateria · atualizador
REFERÊNCIA ..... interna: a "carteira" da 130-A (📊 91) e a página de renovação da 131-B (📊 93); o QCM (o que NÃO copiar); externa: SPEC §8
GATES .......... fio · 2 corretoras · 7 mutações · tsc · rotas montam + next start + /api/cotacoes · design ≥ 90 · canário real · bateria
O ELO .......... "a cotação sai no Agger DO CORRETOR porque ele está no Meu perfil" → o teste lê `conta_exigida_id`/`conta_regra` do
                 cálculo, nunca o texto (📊 mutação 3 vermelha); o canário REAL que lê `multicalculo_pedidos` espera o Implantar (T-169)
FAIXA DE RELÓGIO declarada 💭 7–10 h · real 📊 ≈ 7 h 30 para as TRÊS SPECs juntas (14/10, 02:20 → ~09:50 de Brasília, telemetria
                 §11; a bateria ainda roda)
```
① painel de lentes: não (juiz ‖ red team pela conta do §3). ② auditoria externa: juiz ‖ red team frescos + confirmação nova.
③ pendência por valor marginal: P5/P7/P8 do juiz (capacidade do worker, entrada igual ao padrão, "não terminou" antes do retry).

## 0.1 O protocolo — contas, laço, rebaixamentos, drenagem
| unidade | ALC | REV | FREQ | RISCO | SUP | piso | time |
|---|:---:|:---:|:---:|:---:|:---:|---|---|
| B1 a cotação na conversa | 3 | 3 | 1 | 7 | 2 | sai do prédio + Agger de pessoa | builder |
| B2 a página de venda | 3 | 2 | 1 | 6 | 2 | o segurado lê | builder |
| B3 o aplicativo + migration | 2 | 1 | 1 | 4 | 2 | catálogo + company_id na API | builder |
| B4 costura + E exemplos | 3 | 3 | 1 | 7 | 2 | capability global | builders |

**O laço:** 1 volta + o conserto do defeito novo da confirmação. Saída: **só pendências** (confirmação 82, 6/6 fechados; o defeito novo
"o 'sim' por áudio nunca confirma" consertado pelo gerente em `ce32e89`, 📊 43 passed).
**Rebaixamentos pelo gerente:** nenhum.
**Pendências que a SPEC tocou:**
| P | estado |
|---|---|
| P-1310-04 | 🟡 CONTINUA, menor — a cotação no chat TEM a tradução: `cotacao_disparar` devolve `frase_da_recusa_da_porta` (`ContaRecusada` → `exc.frase`, `cotacao_tool.py:247/303`) e `cotacao_ajustar` trata o `ContaRecusada` do recálculo (`:402`). 📊 grep `ContaRecusada` em `backend/tests/test_spec132*` = 0: nenhum guarda prova a frase. Falta o teste |
| P-1310-06 | 🟡 CONTINUA — "transferir negócio entre usuários do Agger" NÃO foi medido (exige escrever na conta de uma pessoa, com o aceite dela) |
| P-131B-09 | 🟡 CONTINUA — 📊 grep 14/10: `pode_entregar(` / `pode_negociar(` com 0 chamadores fora da definição (`config.py:819/824`); destino 135 |
| P-130A-01 | 🟡 ALIVIADA também na cotação de venda — `publicar_cotacao` nunca recusa por falta do número: sem ele, a página sai sem a barra e diz "responda a mensagem em que recebeu este link" (`proposta.py:1619`, `proposta_cotacao_html.py:708`). O QCM continua recusando |

## 1. Resumo executivo (FATO)
- **A conversa (B1):** três ferramentas no agente CORE — `cotacao_preparar`, `cotacao_disparar`, `cotacao_ajustar` — soltas pela
  capability `tenant.multicalculo.cotacao` (migration `_04`). O pedido sai da conversa, da placa (FIPE/ano/combustível, a placa supre o
  carro também na cotação) e da apólice anexada (`de_ficha`, novo com apólice). Falta dado → uma pergunta só. Completo → resumo
  (CPF mascarado, carro, CEP, opções, "no seu Agger"/"no Agger da corretora") + `confirmacao_id` cifrado no Redis, de uso único, 30 min
  (D-132B-03). **O "sim" é uma FALA do corretor gravada depois do resumo** (o modelo não confirma sozinho — conserto do juiz B4),
  digitada ou falada (transcrição do áudio, `ce32e89`; "claro"/"vamos" entram no vocabulário). O Work Run `cotacao.chat` espera o motor e
  grava a resposta NA MESMA conversa (D-132B-04): 3 opções + o link + "Mensagem para o cliente".
- **A página de VENDA (B2, D-132B-01):** `proposta_cotacao_html.py`, template único com a marca de cada corretora: cabeçalho com SUSEP,
  hero com a parcela da Recomendada, as 3 opções, economia SÓ com a apólice LIDA (D-132B-02), "por que fechar" com fatos do banco, quem
  cuida de você, como funciona, dúvidas, "Preços válidos até {data}", "Nada é cobrado agora". Bloco sem dado SOME. 📊 a carteira, a
  renovação e o canal ficaram idênticos byte a byte (25 passed, 4 no navegador).
- **O aplicativo (B3):** abas Início · Configurar · Cotações · Dúvidas; a aba Cotações (lista, Minhas · Todas, detalhe com Ver
  apresentação · Copiar mensagem · Enviar pelo WhatsApp); as REGRAS do cálculo no Configurar (edita opções, comissão de entrada e
  validade; o resto "padrão do AutoBrokers", D-132B-06); a API `/api/cotacoes` com `company_id` da sessão; os nomes "Cotação Rápida" e
  "Renovação Automática" (D-132B-07). **O link vai ao CORRETOR**; o produto não manda nada ao cliente (D-132B-05).
- **Os exemplos (E, D-132B-08 / D-132-E1):** `backend/scripts/publicar_exemplo_da_pagina.py` publicou três páginas com a marca real da
  corretora-piloto, dados fictícios e a faixa "Exemplo — dados fictícios" (links na T-167). 📊 hoje o servidor de produção (código
  antigo) devolve 404 nelas; local, com o código novo e o mesmo banco, abrem — funcionam depois do Implantar.

## 2. Escopo (FATO — commits)
`133271d` SPEC · B2 `d8176b6`…`5c495a1` · B3 `cf5ac92`…`06ab79e` · B1 `3c5b6bf`…`a40159d` · B4 `7eafa96`…`173b8b9` · `618ba14` o estágio
da cotação no catálogo · E `bd51f78`…`41e6896` · conserto `a62a8f9`…`d4aa30c` · `ce32e89` o "sim" falado. 📊 `git log 285cadc..HEAD
--grep=spec-132-B` → 60 commits, 51 arquivos, +9.475 / −176.
**Entregas NÃO executadas:** o canário REAL (1 cotação AUTO com a conta do robô, tempo até a resposta, a conta lida do banco) — o
servidor de produção roda o código antigo; o juiz de design da página servida (duas corretoras, celular/notebook, claro/escuro).

## 2.1 BLOCO 0 (📊 14/10)
0 ferramenta de cotação no chat; `servico="cotacao"` sem chamador; `multicalculo_config` 0 linhas nas 3 corretoras; `brand_profiles`:
a Resulta publicada (logo, SUSEP, tagline, site, sobre; sem `founded_year`, sem `contact.whatsapp`, diferenciais vazios), a AutoFleet
publicada (2011); `work_runs.conversation_id` existe e tinha 0 escritores em `messages`; `messages` fora do Realtime (0 linhas na
publicação → D-132B-09). Tempo do motor (LAUDO-I1): 1ª oferta 6 s · 80 % em 27 s · fecha em 64 s · p90 406 s.

## 4. Migrations (APLICADAS pelo gerente: psycopg, transação, `lock_timeout 5s`; sha256 do commit = cópia de trabalho)
| arquivo | versão | VERIFY antes → depois |
|---|---|---|
| `20261014_02_spec132b_cotacao_rapida.sql` | 📊 `20261014075627` | `0·0·—·2·0` → `1·1·7·0·0` ("Cotação Rápida" · "Renovação Automática" · 7 dúvidas · 0 nome antigo · 0 dúvida vazia) |
| `20261014_04_spec132b_capability_cotacao.sql` | 📊 `20261014093346` | `0·0·0·0·0` → `1·1·1·0·0` (capability · binding core · scope com as ferramentas · 0 fora do core · 0 corretora desligada) |
⚠️ **O ROLLBACK escrito na `_04` está ERRADO:** `delete from tenant_capability_entitlements where capability_key=…` apagaria
entitlements que ela não criou. O correto (MANIFEST.md, seção SPEC-132): apagar o binding `core`; `is_active=false` na capability;
apagar a capability só se não houver entitlement.

## 5. Testes e gates (📊 saídas reais)
- Builders: B1 18 + 196 passed · B2 25 passed (4 no navegador) · B3 10 passed, casca 203 OK · B4 fio 7 passed (9 defeitos de costura)
  · E 25 passed.
- Juiz (HEAD `618ba14`): `test_spec132b_o_fio` **7 passed** · `_a_conversa` **18 passed** · `_a_pagina_de_venda` **25 passed** ·
  `_api_cotacoes` **10 passed** · `a-loja-e-a-casca.test.mjs` **203 OK** — verdes, e quatro blockers passavam por eles.
- Red team: 15 ataques de isolamento resistiram (o `confirmacao_id` de outra corretora/colega/conversa, identidade injetada pelo modelo,
  `GET/POST /api/cotacoes/<id>` com outra sessão → 404·404·404, busca cruzada → 0·0, XSS no nome e no carro, CPF cru no run/página/API).
- Confirmação: `_o_fio` **15 passed** · `_a_conversa` **28 passed** · sondas do red team "depois" **7 passed** · do juiz **2 passed**.
  **Controle do B4:** o arquivo do red team ORIGINAL (sem a fala "sim") agora dá **5 failed, 2 passed** — falham exatamente os 5 que
  disparam; a cópia que difere SÓ pela fala "sim" passa 7/7: o mérito é da regra nova.
- Conserto do gerente (`ce32e89`): o "sim" da transcrição do áudio confirma; "não, espera" não → 📊 **43 passed**.
- Mutações da régua: disparar sem confirmação · o mesmo `confirmacao_id` 2× · `solicitante_user_id` some · "Quem Cobra Menos"/"Nível 5"/
  duelo na página · economia sem apólice / "N anos" sem `founded_year` · item de outra corretora na API · CPF cru na resposta.
- §9.1: ver o relatório da 132-A §5 (o mesmo HEAD; `GET /api/cotacoes` 401 sem sessão; `/dashboard/auxiliares/cotacao?aba=cotacoes` 307).

## 6. Canário e rollout
Sem canário REAL: a cotação e os exemplos dependem do servidor novo. Depois do Implantar (T-166): os 3 links de exemplo (T-167), uma
Cotação Rápida real com dados de um cliente de teste (T-169), e o gerente lê `multicalculo_pedidos.servico='cotacao'`, o
`conta_exigida_id`/`conta_regra` do cálculo e o tempo até a mensagem na conversa.
⚠️ **A capability vale para TODA corretora com agente central** desde a migration `_04` (binding por papel, sem depender do aplicativo
instalado) — decisão do Founder na T-172.

## 7. Gate da SPEC
juiz **70** (4 blockers: o recálculo respondia "Recalculado" com a tabela e o link ANTIGOS; "economia" na página sem apólice; o CPF de
OUTRO cliente da mesma conversa; o disparo sem o "sim" do corretor) ‖ red team **62 QUEBREI** (3: a economia sem prova e o prêmio
"4200.00" lido como 420.000; o mesmo recálculo; a aba entregava o link de quem saiu e o link vencido) → **conserto único dos 6** (recálculo
com tabela e link novos pelas ofertas do `ajuste_calculo_id`; economia só com ficha `fechou`+`apolice` e o parser decimal do produto;
CPF do texto cru só quando o modelo mandou um e os dígitos visíveis batem; o "sim" é fala do corretor depois do resumo; a aba republica
pela `publicar_cotacao` com o solicitante; CPF com espaços e no `risco` mascarado) → **confirmação 82** (6/6, 1 defeito novo) →
conserto do gerente `ce32e89` (43 passed). Push: na resposta ao Founder.

## 8. Mudanças além do texto da SPEC (CHANGE-ADDENDA 14/10)
ESSENCIAL: `Concluido` no Work OS (`smith_worker.py`/`runs.py`: o workflow devolve o `result_payload`; quem devolve `str` continua igual)
— sem ele o run não guardava o link. VALIOSA: `messages` fora do Realtime → a tela consulta a cada 6 s (D-132B-09).

## 9. Decisões
SPEC §7: **D-132B-00** A e B no mesmo branch (80) · **D-132B-01** página de VENDA nova (88) · **D-132B-02** bloco sem dado some (95) ·
**D-132B-03** `confirmacao_id` de uso único (92) · **D-132B-04** a resposta na mesma conversa (90) · **D-132B-05** o link ao corretor (92) ·
**D-132B-06** Configurar mostra todas as regras, edita três (82) · **D-132B-07** os nomes (F) · **D-132B-08** exemplos com a faixa (85).
Da execução: **D-132B-09** polling 6 s (85 × Realtime 60) · **D-B4-01** a gravação substitui as chaves editáveis (78 × mesclar 62) ·
**D-132B-10** a comissão de entrada vale só em RE; no carro vale a da conta do Agger (85 × mexer nos presets 40) · **D-132-E1** a barra do
exemplo aponta para o número de teste do Founder (85 × sem barra 40).

## 10. Riscos remanescentes (INFERÊNCIA)
- **Juiz de design não rodou** na página servida: o Founder pediu "perto de 100"; a página foi lida pelo juiz e pelo red team (0
  "Quem Cobra Menos", 0 "melhor das", "N anos" só com o ano), não vista em captura com duas marcas.
- **O LLM real encadeando preparar → disparar** não foi medido; o código agora recusa sem a fala (prova com dublê e controle).
- **Capacidade do worker** (P5 do juiz): o run segura um slot por até 💭 6 min com `WORK_WORKER_CONCURRENCY=3` e 2 por corretora — a
  3ª cotação simultânea espera e a promessa "1 a 2 min" quebra.
- A aba e a apresentação podem divergir depois do recálculo (a página mostra as opções; a aba, o ajuste).

### 10.1 📋 CAIXA DO FOUNDER (detalhe em `TAREFAS-DO-FOUNDER.md`)
T-166 Implantar os 4 juntos · T-167 abrir os 3 exemplos · T-169 uma Cotação Rápida real e a aba Cotações · T-170 conectar o SEU Agger no
Meu perfil · T-172 decidir se a Cotação Rápida vale para toda corretora com agente central (hoje sim) ou só com o aplicativo ligado.

### 10.2 Pendências novas → `PENDENCIAS.md` P-132B-01…15
aba × apresentação depois do recálculo · 2º recálculo em outra opção · a Dúvida "WhatsApp em breve" ao ligar a C · slot do worker
até 6 min · entrada igual ao padrão volta à base · "não terminou" antes do retry · capability em todas as corretoras · faixa da
entrada pelo padrão do produto · links antigos não revogados · canário REAL · cliente da carteira (E11) · cotação de outra corretora
como alvo (E5) · o juiz de design da página · a frase da apólice no comando `--atual` · re-preparar pede o "sim" de novo.

## 11. Impacto para o corretor
Escreve "cota o Onix 2022 do João, placa ABC1D23" (ou manda a foto da CNH e a apólice), responde a uma pergunta, diz "sim" — por texto
ou por áudio — e, um ou dois minutos depois, a cotação aparece na mesma conversa com o link de uma apresentação bonita, com a marca da
corretora dele, pronta para copiar e mandar ao cliente.

## 12. Declaração de integridade
Nenhum motor paralelo (CLAUDE.md §5): o cálculo é o `MulticalculoProvider` com `servico="cotacao"`; a conta é o `qual_agger.decidir`;
o run é o Work OS (`work_runs`); a página é um artefato `proposal.quote` pelo `/r/`; a ferramenta passa pelo Capability Registry. Nenhuma
migration antiga mexida. Nenhum segredo aqui. Isolamento com duas corretoras na ferramenta, no Work Run e na API.

## 13. ROLLBACK
Código: `git revert` dos commits do §2. Banco: `_02` devolve os textos da `20261014_01` (ROLLBACK no arquivo); `_04` pelo ROLLBACK
CORRETO do MANIFEST (o do arquivo não). Desligar sem reverter: `update capability_bindings set enabled=false where
capability_key='tenant.multicalculo.cotacao' and agent_role='core';` (as ferramentas somem do chat).

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
PENDENTE — o gerente preenche (a rodada inteira das três SPECs, em `scratchpad/bat132`, ainda roda).

## §11 A TELEMETRIA (`python backend/scripts/medir_execucao_claude_code.py --sessao atual`, rodado da raiz, 14/10 ~09:49 BRT, horários em UTC)
```
EXECUTOR (a sessão inteira, 132-A+B+C)     14/10 05:20  445 min  turnos 210  pico 634k  US$ 54.48  opus-5-5
  Builder B1 cotação na conversa           14/10 05:56  132 min  turnos 130  pico 473k  US$ 23.44  opus-5-5
  Builder B2 página de venda               14/10 05:57  109 min  turnos 131  pico 458k  US$ 24.82  opus-5-5
  Builder B3 o aplicativo Cotação          14/10 05:58  105 min  turnos 140  pico 459k  US$ 24.80  opus-5-5
  Builder B4 costura da cotação            14/10 08:10   82 min  turnos 150  pico 372k  US$ 20.97  opus-5-5
  Builder E exemplos publicados            14/10 09:34   54 min  turnos  92  pico 280k  US$ 10.62  opus-5-5
  Juiz da SPEC-132-B                       14/10 10:09   24 min  turnos  81  pico 305k  US$  9.72  opus-5-5
  Red team da SPEC-132-B                   14/10 10:10   22 min  turnos  58  pico 270k  US$  6.76  opus-5-5
  Conserto único da 132-B                  14/10 10:34   49 min  turnos 108  pico 357k  US$ 15.55  opus-5-5
  Confirmação 132-B                        14/10 11:37   66 min  turnos  32  pico 127k  US$  2.28  opus-5-5
TOTAL da sessão: 32 agentes além do executor · turnos 2744 · ctx 649,4 M · US$ 386,25 (+ executor 54,48)
```
📊 Agentes da 132-B: US$ 138,96 (API-equivalente). Todos `opus-5-5`. Achados por mecanismo: a costura B4 (9 defeitos, EXCLUSIVOS) ·
o juiz (o disparo sem o "sim", o CPF de outro cliente — EXCLUSIVOS; o recálculo e a economia, também do red team) · o red team (o
prêmio ×100 e o link de quem saiu, EXCLUSIVOS) · a confirmação (o "sim" por áudio, EXCLUSIVO). **API do produto:** 📊 0 chamadas pagas
nos builders (dublês); a medição do chat (US$ 0,0568) está no relatório da 132-A.

**Nota da execução: 82/100** (proposta pelo atualizador; o gerente fecha depois da bateria) — 6/6 blockers fechados com controle e o
defeito novo consertado; desconta o canário real e o juiz de design da página, os dois gates da própria SPEC.

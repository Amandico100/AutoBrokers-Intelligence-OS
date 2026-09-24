# ESTADO DAS SPECs — o controle para não se perder

> Levantado em **21/08/2026**, commit `7af5c3c`.
> Critério: 📊 arquivo de SPEC existe? · relatório de execução existe? · quantos commits citam a SPEC? · data do último.
> Comando: `ls docs/canon/specs/` · `ls docs/canon/reports/` · `git log --all --grep="SPEC-0NN" -i`
>
> ⚠️ `docs/canon/EXECUTION-MASTER-PLAN.md` **para na SPEC-062** e não foi atualizado desde então. Este arquivo cobre o que veio depois. Enquanto os dois existirem, **este é o mais recente**.

---

## ✅ FECHADAS — SPEC escrita, executada e com relatório

| SPEC | assunto | último commit |
|---|---|---|
| **059** | Intelligence Fabric + Memory Fabric | — |
| **060** | Research Intelligence | — |
| **061** | Control Plane | — |
| **063** | Atendimento e canais confiáveis | 17/08/2026 |
| **064** | Ontologia e casa limpa | 18/08/2026 |
| **073** | portal-worker hardening / profiler | 17/08/2026 |
| **074** | Portal de vidros Maxpar/Autoglass | 16/08/2026 |
| **075** | Portal capability factory | 16/08/2026 |
| **077** | Browser Intelligence Lab | (só relatório de auditoria) |
| **078** | O Auxiliar de Cobrança funciona | 17/08/2026 |

---

## 🟡 EXECUTADAS SEM RELATÓRIO — o trabalho foi feito, o relatório não

> CLAUDE.md §12 exige relatório por SPEC. Estas têm commits e não têm o documento.
> **Consequência real:** ninguém sabe o que ficou de fora de cada uma sem ler o diff.

| SPEC | assunto | commits | último |
|---|---|---:|---|
| **065** | Carteira e dinheiro visível | 4 | 16/08/2026 |
| **069** | Canais definitivos | 3 | 03/08/2026 |
| **070** | Cobrança multi-seguradora | 11 | 16/08/2026 |
| **071** | Atendimento ponta a ponta e go-live | 7 | 15/08/2026 |
| **072** | A lista de documentos | 5 | 16/08/2026 |
| **076** | Vidros do pedido ao acompanhamento | 1 | 16/08/2026 |
| **081** | Raio-X Comercial e Radar por vendedor | 11 | 18/08/2026 |

---

## 🔴 NUNCA INICIADAS — SPEC escrita, zero commits

| SPEC | assunto | observação |
|---|---|---|
| **062** | Evals, Billing, Rollout, Production Readiness | 📊 marcada `NÃO INICIADO` no plano mestre. Contém o gate de `GO` para produção |
| **068** | Prontidão e go-live | 0 commits |
| **080** | A tela que o Atlas viu vira passo proposto | 🔴 **é a auto-atualização.** Escrita, nunca executada. **Vira a base da SPEC-087** |

---

## ⚠️ PARCIAIS OU AMBÍGUAS

| SPEC | assunto | o que se sabe |
|---|---|---|
| **057** | Artifact Hub & Report Studio | 📊 `PARCIAL` no plano mestre. Falta a rota de leitura de artifact na tela da corretora (P-15) |
| **058** | Auxiliary & Routine Factory | 📊 `PARCIAL`. Falta escritor para `auxiliary_events` (P-18) |
| **066** / **066-v2** | Acervo SUSEP / condições gerais | 2 commits, 08/08. Existem DOIS arquivos de SPEC com o mesmo assunto |
| **067** | O Descobridor | 2 commits, 08/08. Também tem um `.TXT` solto com nome de acervo |
| **070** | Cobrança multi-seguradora | 🔴 **DOIS arquivos** de SPEC-070 com assuntos diferentes (`acervo-de-condicoes-gerais` e `cobranca-multi-seguradora`) |

🔴 **Defeito de numeração a resolver:** SPEC-066, 067 e 070 têm arquivos duplicados ou trocados. Quem procurar "SPEC-070" acha duas coisas diferentes.

---

## 🔵 EXECUTADAS SEM SPEC — o trabalho existe, o documento não

| identificador | assunto | commits |
|---|---|---:|
| **SPEC-079** | (sem arquivo) | 1, em 17/08/2026 |
| **SPEC-082** | 🔴 **A máquina de lavar de ponta a ponta** | 2, em 18/08/2026 |

⚠️ **A rota validada do produto foi construída sem SPEC.** Os commits `cc7b249` e `1d6eace` a criaram, e o número SPEC-082 aparece só na mensagem deles.

📊 E foi exatamente nela que a auditoria de 21/08 encontrou **quatro furos** (âncora que nunca casou, freio sem a segunda âncora, agendamento declarado e não lido, âncora morta). **Trabalho sem SPEC é trabalho sem gate.** Esta é a evidência.

---

## 🆕 A FRENTE NOVA — 21/08/2026

| SPEC | assunto | estado |
|---|---|---|
| **083** | **A régua do corredor** — o que é uma rota AAA e a ferramenta que dá a nota | ✅ **v7 LIBERADA pelo juíz** (21/08, commit `4415928`) — 7 rodadas: 54→78→84→88→92→liberada. Aguardando execução |
| **084** | A fábrica de rotas — as 73 rotas | ✅ **blocos 0–5 EXECUTADOS** (22/08) — 41 rotas medidas, 776→271 órfãs, 102 respostas erradas corrigidas |
| **084.1** | **O ENSAIO** — as 14 estações aplicadas às 73 rotas | ✅ **EXECUTADA** (23/08) — 19 corredores AAA, era 1 · média 47,7%→88,4% |
| **084.2** | **O CONTRATO** — os 6 consertos fora do corredor | ✅ **EXECUTADA** (24/08) — 19/19 passam o portao, eram 0 · 12/12 mutacoes vermelhas |
| **085** | Travar em silêncio deixa de ser possível — Vigia/Sentinela/Cérebro | a escrever |
| **086** | O Suporte Humano diz a verdade | a escrever |
| **087** | O laço de auto-atualização (absorve a SPEC-080) | a escrever |
| **088** | A Central de Agentes em grupos | a escrever |

> ⚠️ Esta tabela parou em 21/08. **De 088 a 098 a autoridade é o `INDICE-DE-SPECS.md`** (088, 093-B, 094, 094.1, 095, 096, 097, 097.1, 098 FEITAS e na main; 091 absorvida).

---

## 🆕 A FAMÍLIA EXTRA — 07/09/2026 (decisão do Founder D-E001-08)

| SPEC | assunto | estado |
|---|---|---|
| **EXTRA-001** | **A operação dos pilotos** — a cobrança chega a quem deve (equipe ou cliente), respostas com o caso certo, uma abordagem por parcela, falhas visíveis; atendimento/observador/QR intactos | ✅ **CONCLUÍDA COM RESSALVAS** 07/09/2026 (CRÍTICO, opção B; `main` `ba7ba75`; juiz fresco 88; canário vivo Q1–Q6 pendente do Implantar — fecha junto com o da 001.6) |
| **EXTRA-001.6** | **A cobrança prova que funciona** — 1 mensagem inteira por segurado com N boletos, nunca a mesma parcela 2×, nunca o mesmo segurado 2× em 7 dias; cada portal diz em português por que não entrou; credencial recusada é classe própria; sessão que vence, breaker, canário de login antes da rotina; fila de telas de portal com leitor; PII fora do relatório | ✅ **CONCLUÍDA COM RESSALVAS** 14/09/2026 (CRÍTICO, laço curto D-PILOTO-20; na `main`; 4 migrations aplicadas; juiz fresco 79 + lente do dado 76 → conserto único; nota 84; canário vivo Q1–Q10 e a reativação da rotina dependem do Implantar; Allianz/Mapfre esperam a senha de 15/09) |
| **EXTRA-001.1** | **A apólice certa, inteira, em uma rodada** — a porta `PolicyDataProvider` vira fronteira (modelo nosso com origem por campo, 2 adaptadores, reconciliação cadastro × PDF); a escolha da apólice mora na porta e diz por quê (vencida nunca vira opção; só pergunta com 2 vigentes do mesmo ramo); o PDF é lido sempre e o extrator lê as tabelas reais (HDI 10, Allianz 21); o corretor recebe a apólice, não a lista; teto no contexto recuperado; `llm_max_tokens` certo no banco; tool call ligada ao turno; 4 guardas mudos de volta | ✅ **CONCLUÍDA COM RESSALVAS** 14/09/2026 (CRÍTICO, laço curto D-PILOTO-20; `main` `3320cee`; 1 migration aplicada; juiz fresco 67 + lente 80 → conserto único (8 achados); nota 87; canário dos 7 casos e validação com a atendente dependem do Implantar) |
| **EXTRA-001.2** | **O agente lê tudo antes de falar** — trava de turno por conversa (SET NX + token + CAS, renovada, posse perdida devolve ao buffer); janela que escuta o conteúdo (3 · 8 · 18 só com conectivo · teto 25); mídia no buffer e visão/transcrição no turno; re-planejamento; presença 'digitando' atrás de flag; a ficha sabe o que foi respondido (72 slots com origem) e o fiscal não repete pergunta; apresentação decidida fora do modelo e confirmada no envio; tamanho com teto duplo (3 frases · 450 chars); identidade da thread por assunto; nome do agente sem confundir (plantão, recusa no servidor, assinatura 🤖); uma conversa por contraparte (M1/M2, 175 fantasmas fechadas); escritor único com todos os ids; silêncio sempre com motivo | ✅ **CONCLUÍDA COM RESSALVAS** 15/09/2026 (CRÍTICO, laço curto D-PILOTO-20; `main` `fc75193`; 2 migrations aplicadas; juiz fresco 62 + lente 88 → conserto único (9 achados); nota 85; canário dos 8 casos e validação com as atendentes dependem do Implantar) |
| **EXTRA-001.3** | **O grupo só recebe o que importa** — a guarda única `o_grupo_pode_saber` (janela do atendimento, claim fresco, números da casa) consultada pelos 11 pontos de envio; a porta única `enviar_ao_grupo` (guarda → marcador por corretora/conversa/tipo → destino único → UM balão → `platform_sends` + `work_events`); espera vencida = 1 aviso com a expiração intacta; vigia vira linha do resumo (menos `never_started`); queda de canal ao dono; allowlist de `kind` nas TRÊS leituras do governador; números da casa com efeito quádruplo e card Equipe; os quatro modelos e o resumo das 19h com a fórmula de D-PILOTO-13; gate de ligar o agente; as 6 rotas do painel com papel, origem e auditoria | ✅ **CONCLUÍDA** 16/09/2026 (CRÍTICO, AAA FAST v12 · experimento A do A/B; `main` `70772a5`; 2 migrations aplicadas e verificadas; juiz Fable 80 + lente 87 → conserto único com 4 blockers; a triagem da bateria por diff achou 4 regressões e as 4 foram fechadas; 12 guardas em 7 arquivos, 28 mutações vermelhas; nota 88. Canário e validação com as atendentes dependem do Implantar) |
| **EXTRA-001.4** | **O corredor não trava sozinho** — menu numerado recebe número lendo a tela; "opção inválida" reparada pelo motor; tentativas por tela; a atendente na URA pausa o robô 60 s (AGENTE/EU CUIDO); o humano da seguradora reabre a sessão travada e recebe o resumo; encerramentos medidos; fila × pessoa sumida; pergunta ao segurado e volta; `agente.*` com todo ato; a tecla "qual seguro" sai do ramo da apólice (decisão do Founder, 17/09); o dossiê do roteador volta a sair | ✅ **CONCLUÍDA** 17/09/2026 (CRÍTICO, AAA FAST v12 · experimento B do A/B; `main` no push deste relatório; juiz Fable FAIL 84 → conserto único (B1 + 5) · lente 70 (2 defeitos de produto) · confirmação 84 (1 residual) — todos fechados; 4 guardas novos; 30 mutações vermelhas na fatia 2; GR exit 0; bateria triada por diff (5 regressões minhas fechadas); nota 85; US$ 101. Canário, canal de grupo e validação com as atendentes dependem do Founder) |
| **EXTRA-001.5** | **O agente sabe o que cada plano cobre** — base GLOBAL de planos e serviços de assistência por seguradora com fonte obrigatória PELO BANCO (documento + página + hash) e publicação só por gente; a Skill `cobertura_e_assistencia` responde nos cinco estados (coberto · nao_coberto · condicionado · nao_contratado · nao_sabemos_ainda) com documento e página, no chat core E no WhatsApp pelo mesmo caminho; fallback residencial marcado; o guarda de `nodes.py` mudou de regra; onda 1 (extrair → verificar → gente publica), onda 2 (SUSEP → condição vigente na emissão), onda 3 (fila pela carteira); tela de Conhecimento com cobertura por seguradora × ramo e fila de curadoria; `doc_kind` filtra e a procedência volta como campo; origem no turno | ✅ **CONCLUÍDA** 18/09/2026 (CRÍTICO pela soma, AAA FAST v12.2 · modo GERENTE, experimento C do A/B; `main` no push deste relatório; 2 migrations aplicadas e verificadas; juiz Fable FAIL 72 → conserto único (4 blockers + 9) · lente 82 · confirmação §6.1; 13 guardas em 13 arquivos, 16 mutações vermelhas; bateria triada por diff (0 regressões); onda 1 em produção: 33 planos + 73 serviços `proposto`, 0 publicados. Publicar a fila, `POLICY_INTELLIGENCE_V2`, Implantar e canário dependem do Founder) |
| **EXTRA-001.5.1** | **A base de planos chega ao cliente** — a Skill da 001.5 estava **desligada em produção em silêncio** (o vocabulário de serviços morava em `docs/`, que o Dockerfile não copia, e o composer engolia a exceção); o dado de runtime inteiro (vocabulário, 2 catálogos SUSEP, censo InfoCap) passa a viajar no pacote, a falta GRITA, e um guarda GENÉRICO por AST reprova código de `backend/app` que abra caminho fora de `backend/`; a fila de curadoria diz a verdade (erro ≠ vazio, "mostrando N de M") e abre sem baixar PDF; publicação em LOTE conferida linha a linha; **um veredito, duas vozes** (o corretor recebe documento e página, o segurado no WhatsApp não recebe citação nenhuma e, quando o plano não cobre, a mesma mensagem oferece a equipe); o que o agente não sabe vira linha em `capability_gaps`, avisa o grupo com teto por conversa e aparece no painel admin; curadoria da base global é de administrador da plataforma; isolamento entre corretoras provado com dois tenants reais | ✅ **CONCLUÍDA** 19/09/2026 (CRÍTICO, AAA FAST v12.2 · modo GERENTE; juiz Fable FAIL 74 → **5 rodadas de conserto** no mesmo fio (tool → contrato → guarda → WhatsApp) → confirmação final **CONFIRMADO COM PENDÊNCIAS, 86**; nota da execução **88**; bateria triada por diff, 0 regressões; 🔴 **23 serviços e 17 planos PUBLICADOS** em produção com revisor, em 9 pares seguradora × ramo — a base saiu de zero. Implantar, a flag `POLICY_INTELLIGENCE_V2` e o canário de 7 casos dependem do Founder) |
| **EXTRA-001.5.2** | **O documento vira base sem virar erro** — extrator v2: a cláusula de planos é a ÂNCORA e sem ela o extrator NÃO propõe (morre o "Plano único"); escopo da cláusula, limite só com a coluna, produto/versão da capa, vidros residencial é cobertura sem mudar a resposta de ontem; o CONFERENTE entra no cano e o parecer chega à fila e à tela | ✅ **CONCLUÍDA** 20/09/2026 (PADRÃO, 1ª sob o **núcleo do AAA v13 em teste**: O FIO + juiz ‖ red team em paralelo + trava de 2 rodadas; **1ª parte** ≈ 2 h, 1 rodada de julgamento — juiz 58 e red team 55 → conserto único → confirmação mecânica; nota 84; o extrator v2 + conferente entregues, mas bloqueados pela chave Anthropic do produto **sem crédito**. **2ª parte** ≈ 2h20: o Founder decidiu NÃO pôr crédito e a base passou a ser escrita por **leitores do plano** — escritor Opus + máquina que exige o trecho literal na página (📊 477/477) + segundo leitor Opus que confere tudo, publicando com o Founder como revisor; 📊 **492 serviços em 108 planos, 8 seguradoras, 20 pares seguradora × ramo** (era 23 serviços), 8 linhas retidas na fila, 0 chamada de API de modelo; 12 perguntas reais respondidas com limite e página. **Nota final 90**. Implantar (smith-api/worker/web) e o canário com apólice REAL — o nome do plano da apólice casa com o da base? (P-E00152-07) — dependem do Founder) |
| **EXTRA-001.7** | **O piloto medido** — o INSTRUMENTO: `conferir_o_que_esta_no_ar.py --ligar` (7 travas + allowlist, por corretora; o que não se confere reprova) · `medir_o_piloto.py` (dia × corretora, só SELECT, zero PII, importa o motor do resumo das 19h) · a régua 0–100 das 11 dimensões do diagnóstico §0, com "NÃO AVALIADA" onde não há dado | ✅ **CONCLUÍDA (instrumento)** 20/09/2026 (PADRÃO, 2ª sob o **núcleo do AAA v13 em teste**: 2 builders Opus em paralelo → juiz 62 ‖ red team 58 → conserto único → confirmação 86 → resíduo fechado; 📊 **7 defeitos materiais antes do push** — o pior: a medição contava **3** conversas num dia de **53**; 8 células conferidas contra SELECT independente. 📊 Hoje: **NÃO PODE LIGAR** (grupos de suporte das duas corretoras desativados desde 10/09; falta Implantar), 0 conversas com fala do agente, todas as dimensões NÃO AVALIADA, salvo chat·velocidade da Resulta = 0 (29 perguntas, p90 do modelo 40,5 s). 🧑 **Os 3 dias de piloto e o canário da 001.5.2 são do Founder** (P-E0017-09); 3 das 6 notas do atendimento não têm escritor (P-E0017-03)) |
| **EXTRA-001.10** | **O portal de vidros de ponta a ponta** — o agente coleta ANTES o que o portal pede, abre o pedido em **qualquer uma das 38 seguradoras** que o portal publica (a seguradora sai do DADO ao vivo; as duas listas fechadas morreram) e **LÊ o desfecho que o portal decidiu** — loja direta · agenda com lojas · analista · vistoria · desconhecido — devolvendo ao segurado número do atendimento + franquia + próximo passo; tela nunca vista = parada com dossiê + fila de aprendizado, nunca silêncio | ✅ **CONCLUÍDA** 21/09/2026 (CRÍTICO, 1ª SPEC sob o **AAA v13 · O FIO** como rito único (D-PROTO-12): 2 leitores → 2 builders Opus em paralelo → costura A↔C → juiz 74 ‖ red team 55 → **conserto único** → confirmação 84. 📊 **11 blockers mortos antes do push** + 1 regressão criada pelo próprio conserto (nome de cidade mutilado, 293 cidades testadas), 20 mutações vermelhas, 3 HAR reais atravessados pelo motor. 🔴 **Achado central:** quem decide loja × agenda é o **PORTAL**, em `GET /agendamentos/opcoes-disponiveis` — não a peça. 📊 O motor de antes escrevia **ZERO** nos 3 HAR da Yelum. **Nota 86.** Tudo atrás da flag `PORTAL_VIDROS_API_FIRST`, que nasce **DESLIGADA**: o que atende hoje é o caminho DOM. 🧑 **Na caixa do Founder:** Implantar, o **canário** (G10, não rodou — exige apólice/veículo de teste), as capturas que faltam (a nº 1 é o agendamento concluído) e as 15 perguntas à atendente. **Próxima: EXTRA-001.10.1 · a continuação** — o token do portal vive só em memória, então toda parada depois do protocolo termina em mão humana (P-E00110-A11)) |
| **EXTRA-001.10.1** | **A continuação do portal de vidros** — o robô RETOMA um atendimento já aberto (token do portal guardado CIFRADO), CONCLUI o agendamento (loja + dia + hora confirmados pelo portal) e responde sozinho o que o portal pede depois do protocolo (prioridade, preferência de vistoria); parada que depende do segurado vira pergunta + continuação, parada técnica vira releitura automática; mão humana só com token recusado (401) ou tela nunca vista | ✅ **CONCLUÍDA** 24/09/2026 (CRÍTICO, rito **AAA v13 · O FIO**: 1 investigador (perícia do bundle) → 2 builders Opus em paralelo (arquivos disjuntos) → costura A↔C → juiz Fable **86** ‖ red team Fable **64**, cegos → **conserto único** → confirmação Fable **78**. 📊 **11 blockers mortos antes do push**; exclusivos: costura 3 · red team 5 · confirmação 2. 🔴 **Achado central:** o token do portal EXPIRA (o de 21/09 22:09 UTC deu 401 em 23/09 23:40 UTC, entre minutos e ~50 h) e o portal continua atendimentos pelo próprio token na URL — não existe endpoint de retomada por placa/CPF; a lataria (`BloqueadoIlhaNormal`) não travava no portal, só no nosso roteador. **Nota 88.** Tudo atrás da mesma flag `PORTAL_VIDROS_API_FIRST`, que continua **DESLIGADA**: o que atende hoje é o caminho DOM. 🧑 **Na caixa do Founder:** Implantar (`smith-api` → `smith-worker` → `portal-worker`) e o **canário (G12)**, que não rodou. **Próxima: EXTRA-001.9**) |
| **EXTRA-001.8** | **Uma corretora não trava a outra** — cota de 4 atendimentos por corretora + rodízio determinístico dentro do processador que já existia (zero fila nova); teto por chamada ao modelo (90 s) e por turno (300 s), com a inequação `90 × 3 < 300` guardada; disjuntor por **provedor** de LLM, consultado ANTES de consumir o buffer; contrapressão que renova o TTL e **não perde mensagem**; lock de líder para os 25 jobs do agendador e poço de threads explícito; a Central de Agentes passa a ver **por corretora** (`expiradas_acumuladas` é a resposta diária a "perdi alguma mensagem?"); e as duas pendências de isolamento da D-FILA-01 fechadas (cerca de corretora dentro do serviço MCP; nome de pessoa real fora do dado global) | ✅ **EXECUTADA, canário pendente** 21/09/2026 (CRÍTICO, rito **AAA v13.1**: 6 builders Opus → juiz Fable **76** ‖ red team Fable **78**, cegos → **conserto único** → confirmação **86**. 📊 **8 blockers mortos antes do push**; exclusivos: juiz 1 (o teto real de instâncias era 10, não 24) · red team 2 (a conta de perdas caía na corretora errada; o corte do turno deixava o segurado em silêncio definitivo) · conserto 1 · confirmação 1 (resíduo, consertado depois da bateria). 🔴 **Achado central:** `expiradas`/`timeouts` eram totais GLOBAIS gravados no hash de TODA corretora ativa — a perda de uma aparecia na tela da outra. 📊 G3 com linha de controle: 10/10 verde, controle ~200× acima do medido. Zero migration, zero motor paralelo. 🧑 **Na caixa do Founder:** Implantar, o `/health` (`scheduler`/`executor_threads`), medir os núcleos do contêiner, e o **canário com duas corretoras de teste** — os 6 casos, que **não rodaram**. **Próxima: EXTRA-001.9**) |
| 💡 **IDEIA SPEC-115** | **O Placar** — as medições (resumo das 19h, `medir_o_piloto.py`, relatórios) viram uma área com histórico por dia no painel de cada corretora | 💡 **ideia registrada, não é SPEC** — `specs-propostas/IDEIA-SPEC-115-PLACAR-E-MEDICOES-NO-PAINEL.md`; depois da 114 (Founder, 20/09) |
| 💡 **IDEIA EXTRA-001.11** | **As pendências que pesam** — a regra D-FILA-01 e a lista-semente das 9 marcadas ≥ 90 | 💡 **ideia registrada, não é SPEC** — `specs-propostas/IDEIA-BLOCO-EXTRA-001.11-PENDENCIAS-QUE-PESAM.md`; sai da triagem, antes da EXTRA-002 |
| **EXTRA-002** | **Dá para cotar e renovar pelo Agger?** — investigação e prova do multicálculo; a fundação da Renovação Feita, da Cotação pelo Chat e do Comparador | 🧭 **PARTE 1 (perícia) EXECUTADA** 22/09/2026 em **MODO INVESTIGAÇÃO** (protocolo §3.3/§8; branch `docs/extra-002-investigacao-agger`; zero código, zero migration, zero acesso ao vivo). 📊 perícia de 3 HARs: a tela do Aggilizador é uma **API JSON** (token de 8 h, **sessão única**, cálculo assíncrono por polling, resultado padronizado com PDF); 🔴 as senhas dos portais das seguradoras vêm em **todas** as 28 respostas de polling (RP §1–§2.1). Cético Fable **71** (002) / **58** (003) · juiz do risco Fable **84** / **74** — notas **antes** do conserto único (18 itens, nenhum blocker rebaixado). Propostas escritas: 002 (+ Research Pack), 003, 004, 007. Relatório: `reports/SPEC-EXTRA-002-INVESTIGATION-REPORT.md`. ⏳ **PARTE 2 (prova ao vivo, E0–E4) aguarda a caixa do Founder** (§11 da proposta: anuência/API da Agger, usuário robô, senha na tela de conexões, conexão InfoCap) e as decisões **D-E002-01..08** |
| **EXTRA-003** | **Renovação Feita** — o ciclo de renovação sobre a porta `QuoteProvider` | 📝 **PROPOSTA** 22/09/2026 — `specs-propostas/SPEC-EXTRA-003-renovacao-feita.md`; dividida (D-E002-06, recomendação 88) em **003-A "a fundação"** (espera durável no Work OS + `QuoteProvider` + adaptador + conexão) e **003-B "o ciclo de renovação"** (dados, lacunas, cálculo/recálculo, comparação honesta, painel das 7h), um chat cada; depende da parte 2 da 002 |
| **EXTRA-004** | **Cotação pelo Chat** — reusa a fundação da 003; a resposta volta à conversa pelo Realtime que já existe | 📝 **PROPOSTA** 22/09/2026 — `specs-propostas/SPEC-EXTRA-004-cotacao-pelo-chat.md`; depois da 003 |
| **EXTRA-007** | **Comparador da Corretora** (site público) — sobre o mesmo motor; o de maior risco (público anônimo, LGPD, antiabuso; piloto de lead antes do cálculo) | 📝 **PROPOSTA conceitual** 22/09/2026 — `specs-propostas/SPEC-EXTRA-007-comparador-da-corretora.md`; vem por último (ordem 003 → 004 → 007, nota 92) |
| **099 → 114** | o MASTERPLAN | ⏸ **PAUSADAS** sem renumerar; retomam por dependência comprovada (canais → 099 depois dos pilotos) |
| **116** | **Cada trabalho no modelo que provou servir — Model Router + Bancada E2E** — cada trabalho (papel) pede o modelo a UM resolvedor que lê UM catálogo governado (`llm_pricing` expandido: preço com fonte, ciclo de vida, capacidades, classe de dado) e rotas por papel no banco (`llm_papeis` + histórico; trocar e voltar = uma linha, sem Implantar); o resolvedor **erra em vez de cair no mini**; a bancada E2E estende a Eval Fabric da SPEC-062 e mede no motor real | 🟡 **CONCLUÍDA COM MEDIÇÃO PARCIAL — Onda A parcial** 23/09/2026 (CRÍTICO, AAA v13: 8 builders em 6 fatias → juiz Fable **74** ‖ red team Fable **78** → conserto único `be8b033`; branch `spec/116-model-router-e2e-bench`). 📊 4 migrations aplicadas (`_01` catálogo+papéis · `_03` bancada · `_04` mapa Onda A · `_05` rota só aceita modelo governado). 📊 Trocados pela bancada: **memória** gpt-4o-mini → gpt-6-luna low (32/45 → 39/45) · **visão** gpt-4o-mini → gpt-6-sol low (28/30 → 30/30, imagens sintéticas) · **portal** gpt-4o → gpt-6-sol medium (38/41 → 43/43). Chat, atendimento, cobrança e dispatch **não mudaram**: a bancada (📊 US$ 11,97) parou por **crédito zerado** nos dois provedores. 🔴 Achados de produto consertados: corretora nova nascia no gpt-4o-mini, foto lida 2× por turno, portal rebaixava calado, esforço nunca chegava ao Claude, auxiliares quebrados desde 07/08, turno com tool refeito, juiz de eval nunca rodou, laço de 7 consultas de apólice. 🧑 **Caixa do Founder:** recarregar crédito (bloqueia o produto), Implantar 4 serviços, canário. Relatório `reports/SPEC-116-EXECUTION-REPORT.md` · SPEC `specs/SPEC-116-cada-trabalho-no-modelo-que-provou-servir.md` · 27 P-S116-* |

---

## O que fazer com este arquivo

1. **Toda SPEC que fechar** move para a primeira tabela, com o link do relatório.
2. **As sete da segunda tabela** precisam de relatório retroativo, ou de uma decisão registrada de que não terão. Enquanto estiverem lá, ninguém sabe o que ficou pendente nelas.
3. **A numeração duplicada** (066/067/070) precisa de uma decisão do Founder: renumerar ou arquivar as versões vencidas.
4. **A SPEC-080** não some — ela é absorvida pela 087, e isso fica escrito na 087.

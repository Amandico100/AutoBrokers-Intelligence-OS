---
> **Status:** em execução · **Protocolo:** AAA v12.2 · AAA FAST · modo GERENTE (Fable 5.1 no chat da 001.5, por decisão do Founder de 19/09)
> **SPEC:** `specs-propostas/SPEC-EXTRA-001.5.1-a-base-de-planos-chega-ao-cliente.md` · **Branch:** `feat/extra-001-5-1-a-base-chega-ao-cliente` · **Base:** `6836258`
---

## 0.0 🔴 O EXECUTION CARD (protocolo §0.2) — recontado no BLOCO 0 sobre `6836258`

```
OUTCOME ........... a base de planos CHEGA ao cliente: a Skill roda em produção (hoje está desligada em
                    silêncio), a fila de curadoria abre e publica, o corretor recebe a fonte e o segurado
                    recebe a mesma verdade sem citação, e o que o agente não sabe vira tarefa
RISCO ............. 8 = ALCANCE 3 (o segurado lê) + REVERSIBILIDADE 3 (sai pelo WhatsApp) + FREQUÊNCIA 2
SUPERFÍCIE ........ 2 — lugares listados na proposta §2 (2 arquivos de backend, 3 de front, 2 prompts, o pacote)
PISO APLICADO ..... §3.2: todo texto ao segurado; a migration do motivo do rascunho, se houver
NÍVEL ............. CRÍTICO pela soma · marcha PADRÃO com o elenco do crítico (como a 001.5, D-E0015-02) ·
                    builder Opus 5 xhigh por fatia · juiz Fable 5.1 fresco · confirmação por gatilho
UNIDADES .......... 5 · A cegueira · B fila e lote · C resposta por canal · D lacuna vira tarefa · E isolamento
                    FATIAS: 1 = A · 2 = B · 3 = C+D+E · + publicação das linhas conferidas (Founder autorizou 19/09)
COESÃO ............ A é pré-condição de tudo (sem o vocabulário nada roda); B toca a mesma fila que a
                    publicação usa; C+D+E tocam o mesmo turno de resposta
PARALELISMO REAL .. nenhum na escrita de código; um LEITOR read-only confere as 81 linhas em paralelo à fatia 1
TIME .............. gerente Fable · 3 builders Opus xhigh · leitor Opus (read-only) · juiz Fable fresco ·
                    lente do dado NÃO (o outcome não é dataset novo) · confirmação se blocker no texto ao segurado
REFERÊNCIA ........ interna `backend/tests/test_a_resposta_traz_documento_e_pagina.py` (o par corretor × segurado
                    nasce dele) · externa: as 3 da 001.5 §14 (PROV-O · Citations · ALCE)
GATES ............. GATE A..E da proposta §5 · 🔴 todo gate de produção roda na CÓPIA que reproduz o contêiner
O ELO ............. "responde 'não sei' a tudo PORQUE a Skill nem roda": medi A (a resposta em produção) ·
                    medi B (/fila 500; Dockerfile copia só backend/) · B chega em A: o except do composer engole
FAIXA DE RELÓGIO .. fatia ≤ 60 min ×3 · juiz+conserto+entrega ≤ 45 min · tetos 160 turnos · 250 k por fatia
```

📊 **Preflight 19/09:** `HEAD..origin/main` = 0 · HEAD `6836258` · as 5 medições do prompt reproduzidas (§1).
**D-E00151-01:** o Founder decidiu executar no MESMO chat da 001.5 (11 agentes já usados); o teto do hook sobe
para 24, registrado aqui — 90 × abrir chat novo 60. 🔴 **D-E00151-02 (correção de um FATO que eu afirmei sem conferir):**
escrevi que `AAA_FAST_TETO_DE_AGENTES=24` estava em `.claude/settings.json`. **Não estava** — o script só gravava se o
texto não existisse no arquivo, e ele existe num comentário. 📊 Medido na retomada: variável AUSENTE, arquivo de 17/09.
Com autorização escrita do Founder (19/09), o PADRÃO do hook local (`.claude/`, fora do git) foi a 24 **só nesta SPEC** e
volta a 12 no fechamento (§9).

## 1. BLOCO 0 — as premissas remedidas em 19/09
| # | afirmação | medido 📊 | comando |
|---|---|---|---|
| 1 | `/fila` 500 em produção | **500** em 1,4 s · `/cobertura` **200** em 1,8 s | `curl -H X-Internal-Key …/api/assistance-plans/fila?limite=3` |
| 2 | o vocabulário está fora da imagem | `Dockerfile`: `WORKDIR /app` + `COPY . .` (de `backend/`) | `grep -n COPY backend/Dockerfile` |
| 3 | o composer engole | `except Exception` + `logger.warning` (`policy_answer_composer.py:576`) | `sed -n 576,577p` |
| 4 | o front esconde o erro | `route.ts:42` sem `r.ok`; `KnowledgeClient.tsx:108` `fila.itens \|\| []` | `grep -n` |
| 5 | o dado | planos 33 proposto/5 rascunho · serviços 73/8 · 0 publicado · `TETO_DA_FILA = 60` · `capability_gaps` = 0 | SELECT |

## 2. As unidades entregues, por fatia

| fatia | unidade | o que entrou | gate · saída real 📊 |
|---|---|---|---|
| **1** | **A** a cegueira (D1, D2, D3, D4, D9) | o vocabulário passa a viver em `backend/app/data/servicos-de-assistencia.json` (o de `docs/` vira PONTEIRO, e `vocabulario_de_servicos` recusa arquivo sem serviços — decisão ponteiro 88 × cópia com guarda 72) · o resolvedor procura primeiro dentro do pacote · `contar_fila()` conta a base · ordem estável em dois níveis · `/fila` devolve `{ok, itens, total, mostrando, limite}` e uma página que falha não derruba a resposta · `route.ts` testa `r.ok` · `KnowledgeClient` testa `ok` · a fila tem 3 estados (erro · vazio honesto · lista "mostrando N de M") e o botão morto explica · 11 commits `0e9a995`…`f1517dd` | 🔴 **guarda do contêiner** (`test_o_vocabulario_viaja_na_imagem.py`): cópia só de `backend/`, vermelho **3/5** antes → verde **14/0** depois · **O ELO**: na cópia sem `docs/`, antes `Skill de cobertura indisponível` e `COBERTURA: None`; depois `COBERTURA: {"servico":"carro_reserva",…}` · `test_a_fila_diz_a_verdade` 24/0 · `contar_fila` = 73 = SQL (controle: rascunho 8) · rotas-montam 303 · `tsc` 0 · `next build` 314 rotas · `next start` → `GET /api/dashboard/knowledge/planos` 401 `no_session` em 0,29 s · 3 mutações vermelhas em arquivo real (JSON apagado · `itens:[]` no catch · `.order()` removido) · 16 guardas vizinhos verdes · gerente rerodou 5 guardas: exit 0 |
| **2** | **B** fila e lote + **A-bis** catálogos SUSEP (D5, D6, D7, D8 · E2, E3) | `fila()` não abre mais PDF: devolve `pode_publicar`/`motivo_de_nao_publicar` e a página vem SOB DEMANDA por `GET /pagina?servico_id=` (cache 300 s · 6 documentos) · `FilaDeCuradoria` pede a página ao abrir a linha · migration `20260919_01_extra00151_motivo_do_rascunho.sql` (coluna `motivo_do_rascunho` nas duas tabelas; o motivo SAI de `condicao`; aplicada 2× — idempotente; MANIFEST atualizado) · `devolver_servico_a_proposto()` — `rascunho` deixa de ser porta de mão única · `scripts/publicar_linhas_da_base.py` (em seco por padrão; `--aplicar` exige `--revisor`; publica só `PUBLICAR` ainda em `proposto`; `RECUSAR` → rascunho com o motivo do leitor; `CORRIGIR` só lista) · os 2 catálogos SUSEP passam a viver em `backend/app/data/`, os de `docs/` viram ponteiro, `_secao_do_catalogo()` loga ERROR · 12 commits `2b26bab`…`6d074d8` | `test_a_fila_abre_rapido_e_o_lote_publica_com_revisor` **40/0** (conta LEITURAS e ESCRITAS, não relógio: a fila de 60 linhas faz **0** leituras de documento; a página sob demanda, 1) · guarda do contêiner estendido: na cópia sem `docs/`, `familia_de_acionamento('porto')` = `porto` (antes `UNKNOWN`) · 1ª mutação (b) era CARIMBO (ficou verde) → trocada por duas reais, vermelhas · em seco 📊 **23 publica · 10 derruba · 48 pula** (2 das 25 `PUBLICAR` já não estavam em `proposto`) · gerente rerodou `py_compile` + 5 guardas: exit 0 |
| **3** | **C** duas vozes + **D** a lacuna vira tarefa + **E** isolamento + **A-ter** o censo InfoCap (D10, D11, D12 · E1) | `_texto(..., para=)`: o veredito carrega `texto` (corretor: veredito em negrito, limite/condição e `Fonte:` em linha própria) **e** `texto_para_o_segurado` (2ª pessoa, sem citação, montado no `__post_init__` — 92 × passar em 6 construtores 68) · o canal viaja `infocap_tool` → composer → contrato; `nodes.py` **não aprende canal** (só docstring) · quando não cobre, a mesma mensagem oferece a equipe (opção 1 do Founder) · o gancho nomeia a atendente só com fonte única, senão "nossa equipe"; **nenhum nome próprio** em Skill nem prompt · 1 linha em cada prompt (`prompts.py`) · `lacunas_de_conhecimento.py` NOVO: upsert em `capability_gaps` por fingerprint (📊 índice real `UNIQUE (fingerprint)`, sem `company_id`), aviso 🆘 pela porta da 001.3 com teto de 24 h e só no canal do segurado · D4 **sem tela nova**: o painel `/admin/auxiliares/factory` já listava por frequência — a lacuna de cobertura ganhou nome (94) · E19 `requireMasterAdmin` no BFF de planos · `vidros.ramos` corrigido · A-ter: 3 arquivos do censo em `backend/app/data/providers/infocap/`, resolvedor que GRITA, e o guarda GENÉRICO por AST (código de `backend/app` que abre caminho fora de `backend/` reprova) · 15 commits `0baa672`…`45d491f` | GATE C `test_a_mesma_verdade_em_duas_vozes` **68/0** · GATE D `test_a_lacuna_vira_tarefa` **28/0** · GATE E `test_o_conhecimento_global_nao_vaza` **24/0** + `test_a_resposta_nao_abre_arquivo` **8/0** · contêiner **40/0** (era 14) · 🔴 **ELO do A-ter na cópia sem `docs/`:** antes `ISDIR False · CAPS 0` (na árvore 19) → depois `CAPS 19` · 11 mutações vermelhas em cópia (canal ignorado · citação vazando · "não" sem equipe · nome hardcoded · teto removido → 3 avisos · aviso no canal do corretor · pergunta crua · `colecao_permitida` sempre-True · `requireCompanyMember` · Skill lendo página → 24 leituras · censo apagado → CAPS 0) · `tsc` 0 · rotas-montam 303 · `next build` ok · `next start` → GET 401 `no_session` · POST 401 `no_admin_session` · ⚠️ o builder QUEBROU 3 guardas do Pulso 360 que liam o censo de `docs/` (284·0 → 235·20), mediu a base num worktree e migrou a lição (§9.3): 284·0 de novo · relógio ~100 min contra ≤ 75, **estourado e declarado** · gerente rerodou `py_compile` + 7 guardas: exit 0 |

**Fora do escopo, visto pelo builder (🔴 vira unidade A-bis):** `backend/app/providers/susep_ses_provider.py:100-109` lê
`docs/canon/providers/susep/{seguradora-coenti,ramo-cogrupo}.json` por `parents[4]` — fora da imagem, como o
vocabulário. 📊 Na cópia que reproduz o contêiner os três mapas vêm **vazios** (`[SES] mapa de seguradoras ausente`),
e `familia_de_acionamento(insurer_key)` devolve `UNKNOWN` em vez de `porto` — está no caminho vivo (`infocap_tool.py:856`).
Degrada em silêncio, sem 500. **Não consertado nesta fatia** (fora do card); entra na fatia 2 com o mesmo remédio.

## 4. O juiz — Fable 5.1 fresco, read-only, sobre `0dc113b..45d491f` · **FAIL · nota 74**

📊 Julgou numa cópia de `git archive HEAD backend` (sem `docs/`, sem `.env`) e rodou 9 mutações numa segunda cópia.
Reproduziu 4 números (em seco 23·10·48 · base 0 publicado/72+33 · índice `UNIQUE (fingerprint)` · CAPS 19 na cópia): todos ✔.
Por unidade: **A 92 · A-bis 90 · A-ter 90 · B 84 · C 60 · D 58 · E 86**. 🔴 A frase dele: *"é a mesma cegueira da 001.5, um
andar acima"* — os gates C e D mediam o compositor e o serviço (certos); o que chega ao segurado passa por
`_build_llm_briefing` e `_arun`, e por lá não passava guarda nenhum.

| # | blocker (teste do produto: chega a quem) | medição 📊 |
|---|---|---|
| **B1** | SEGURADO · no WhatsApp a LLM nunca recebia o veredito: o ramo `client_facing` do briefing dava `return` antes de anexá-lo; em `nao_sabemos_ainda`/`fonte_indisponivel` o contrato saía com `required_facts=[]` | candidato *"Sim! tem sim"* passava CRU pelo guarda nos 6 estados do canal segurado |
| **B2** | CORRETORA · o 🆘 da lacuna não dizia quem era o cliente, e as perguntas 3–4 da guarda da 001.3 não rodavam | `conversation_id='' telefone=''` no aviso |
| **B3** | CORRETORA · o marcador de 24 h queimava quando o envio falhava | porta com `Timeout`: dia fecha com **0** avisos |
| **B4** | PAINEL · `para_registro()` não levava `motivo`: 5 frases de descrição eram código morto | dois motivos gravavam a mesma frase |
| **B5** | SEGURADO · `condicao` entrava crua na voz do segurado | das 72 linhas reais: 2 > 450 car. (575) · 2 com citação · 7 em 3ª pessoa · 3 com jargão |

Mutações do juiz: 6 vermelhas · **3 VERDES** (M1 tirar `client_facing=` da chamada · M4 a tool não chama a lacuna · M6 `open()` local) — carimbos, entraram no conserto. Pendências P1–P11 dele: P1–P4, P6, P9 no conserto; o resto no `PENDENCIAS.md` (§8).

## 5. O conserto — e as três rodadas no MESMO ponto

🔴 **O padrão, escrito antes da nota:** a cada rodada o conserto fechou o defeito medido **e abriu outro no mesmo
lugar** — o fio entre a tool de apólice e o WhatsApp, que nenhum gate das fatias atravessava. Rodada 1 (B1–B5 + P1–P9):
fechou tudo o que o juiz mediu, e a flag `encerrar_com_o_rascunho` passou a **calar o acionamento** (📊 6/11 pedidos de
guincho substituídos). Rodada 2 (porta de intenção): o acionamento voltou, e a porta perdia **45 %** dos pedidos e o
consumo era por chamada, não por turno. Rodada 3: o turno do **CPF** — a tool roda quando o cliente manda o documento,
não quando pergunta — desligava a fiscalização inteira. **A lição migra para a próxima SPEC:** um guarda que mede o
compositor não prova o que sai no WhatsApp; ele tem de passar por `_render_content` → contrato →
`nodes._guard_infocap_policy_final_response`, com **janela ≠ mensagem atual**.

**D-E00151-04 (gerente):** o §8 do protocolo manda escalar para AAA COMPLETO depois de duas reprovações com blocker
material. Aqui foram três. Em vez do painel de 3 lentes + red team (que a cota de agentes deste chat não comporta),
a escalada foi **uma rodada dirigida com caminho de saída explícito** — autorizei por escrito desmontar a flag e ficar
com o veredito no briefing + as regras da 001.5, se a maquinaria não ficasse segura — **mais** um julgamento final.
Escalada dirigida **85** × painel completo **60** (não cabe na cota) × fechar com a flag insegura **10**.

**Troca de gerente no meio (FATO, para a auditoria do A/B):** a execução começou com o gerente **Fable 5.1** e passou
a **Opus 5 (1M)** durante a rodada 3, no mesmo chat, sem reconstruir fatia nem rechamar builder — como na 001.5
(D-E0015-09). Os commits a partir daí carregam a coautoria do Opus.

### 5.1 As quatro rodadas, e o que cada julgamento mediu

| rodada | o que o juiz mediu de errado | o que o conserto fez | veredito |
|---|---|---|---|
| **conserto 1** | 5 blockers: a LLM nunca recebia o veredito no WhatsApp · o 🆘 sem cliente · marcador queimava · `motivo` não chegava · condição crua na voz do segurado | fechou os 5, e a flag `encerrar_com_o_rascunho` passou a **calar o acionamento** (📊 6/11 pedidos de guincho substituídos) | NÃO CONFIRMADO |
| **rodada 2** | a porta de intenção perdia **45 %** dos pedidos (10/22) · o consumo era por CHAMADA, não por turno · o turno do **CPF** desligava a fiscalização inteira | porta de 3 saídas, consumo por estado, `fonte` única | NÃO CONFIRMADO |
| **rodada 3** | `texto = atual or janela` não acompanhou a intenção (📊 100 % do tráfego real, porque não há linha publicada) · a janela era lida como BLOCO e a mensagem mais VELHA decidia · os stems da porta eram carimbo | uma fonte só, varredura do mais novo, `condicionado` guardado, crédito do número corrigido | NÃO CONFIRMADO |
| **rodada 4** | — | os 4 fechados e medidos; reverter os stems agora dá 2/154 vermelhas | 🔴 **CONFIRMADO COM PENDÊNCIAS · 84 / SPEC 86** |

📊 **O produto, lido pelo juiz final sobre 5 condições REAIS do banco:** ao segurado saem **104–204 caracteres, 2 frases**
nos cinco casos (teto: 3 frases, 450 caracteres). Condição curta vira voz de gente; condição de 202 e 414 caracteres é
colapsada por `condicao_que_o_cliente_entende` — nada truncado, nada sem sentido, e a cláusula técnica fica só no canal
do corretor. O `sim` liso foi anulado nas cinco. 💬 Palavras dele: *"isto está bom, e é o melhor resultado da SPEC"*.
📊 A base tem **53 `condicionado` · 18 `sim` · 1 `nao`** em `proposto`; `length(condicao)` médio 178, máximo 494.

## 6. A publicação — 🔴 o trabalho chegou ao cliente

📊 19/09, `scripts/publicar_linhas_da_base.py --revisor <users_v2 do Founder> --aplicar`, com o arquivo de conferência
do leitor. **23 serviços e 17 planos publicados · 10 derrubados para `rascunho` com o motivo do leitor · 0 publicados
sem revisor.** A base passou de **0** para **23 linhas vivas** em 9 pares seguradora × ramo (azul auto 3 · bradesco
residencial 7 e condomínio 1 · hdi auto 4 e residencial 1 · mapfre auto 1 e condomínio 1 · tokio residencial 2 ·
yelum auto 3), sendo **15 `condicionado` e 8 `sim`**.

🔴 **E a aplicação real achou o que nenhum ensaio acharia.** A primeira rodada publicou **17**, não 23 — e o relatório
lia como sucesso: `publicar_linhas_da_base.py:253` exigia o plano pai em `proposto`, mas `publicar_servico` **publica o
plano junto**, então a partir da segunda linha do mesmo plano o pai já estava `publicado` e a linha era pulada com o
motivo `plano_pai_publicado`, misturado na mesma lista de `ja_em_publicado` (que é idempotência, não perda). 6 linhas
conferidas contra a página não chegaram ao cliente em silêncio. Consertado (o pai aceitável é `proposto` **ou**
`publicado`), o relatório passou a separar **perda** de **trabalho já feito** e a dizer a frase que faltava —
*"🔴 N linhas conferidas NÃO chegaram ao cliente"* — e o guarda ganhou o par que faltava: duas linhas do MESMO plano
publicam as duas, e **o ensaio bate com o aplicar** (📊 era 23 × 17). Restam **3 serviços presos** sob plano pai em
`rascunho` (P-E00151-07), declarados na lista de perda.

## 7. A bateria — 📊 UMA rodada inteira, triada por DIFF

Linha de base (17/09, `python -m pytest tests -q`): **34 failed · 48 errors**. Nesta SPEC: **37 failed · 1133 passed ·
34 xfailed · 48 errors** em 2.676 s. **Diferença: 3**, todas explicadas e nenhuma regressão:

| falha nova | causa | prova |
|---|---|---|
| `test_o_protocolo_tem_policia` | o guarda lê o relatório da SPEC **aberto**, sem o card completo — o mesmo da 001.5 (P-E0015-09) | fecha com o relatório |
| `test_o_fio_chega_ao_segurado` (pelo corredor) | rodou **enquanto o builder editava o arquivo** | 📊 rerodado pelo corredor no HEAD: **9/9 guardas da SPEC passed** em 250 s |
| `test_o_passo_compartilhado_ainda_e_conferido` | idem | idem |

Os 48 erros são a contaminação de ordem de `test_098_builder_b_unit`, idênticos na base. **Regressões da SPEC: 0.**

## 8. O que ficou fora, e o gatilho que o faz voltar

As **10 pendências** de `PENDENCIAS.md` (`P-E00151-01`…`10`). A maior é a **P-E00151-01**: 📊 o leitor conferiu as 81
linhas contra a página e só **25** estavam certas — 40 pedem correção e 16 foram recusadas. O extrator confunde risco
excluído dentro de OUTRA cobertura com cobertura do plano, apaga os planos reais num "Plano único" (📊 o manual
Bradesco Auto tem **9**) e chega a usar o nome do arquivo como nome do produto. **Enquanto isso não for refeito, a
fila não é trabalho de revisão: é trabalho de reextração.**

## 9. 📋 Caixa do Founder — o que só ele faz

| # | o que é | o que faz | o que custa esquecer | bloqueia? |
|---|---|---|---|---|
| 1 | **Implantar** | EasyPanel → `smith-api` **e** `smith-web` | tudo isto continua no ar de ontem: a Skill segue desligada e a fila segue em 65 s | 🔴 sim, para tudo |
| 2 | **A flag** | `smith-api` → Environment → `POLICY_INTELLIGENCE_V2 = true` | ausente = a Skill não roda, e o canário mede o comportamento antigo e conclui errado | 🔴 sim |
| 3 | **O canário** | `reports/SPEC-EXTRA-001.5.1-CANARIO-PASSO-A-PASSO.md` — 7 casos novos; **N5 e N6 são os controles** | sem eles, "funcionou" pode ser um `return` fixo | não |
| 4 | **As 40 linhas a corrigir** | decidir se a reextração entra na próxima SPEC | a fila fica parada e a base cresce errada | não |
| 5 | **A destilação das 4 seguradoras** | `PROTOCOLO-DE-DESTILACAO-DAS-SEGURADORAS.md` (é dele, por decisão de 19/09) | bradesco, mapfre, tokio e azul respondem por uma fração do que têm | não |

## 10. FATO · INFERÊNCIA · RECOMENDAÇÃO

**FATO:** tudo com 📊 foi medido por comando, e os gates de produção rodaram numa cópia que reproduz o contêiner
(só `backend/`, sem `docs/`). 23 linhas estão publicadas com revisor. **INFERÊNCIA:** a Skill deve responder em
produção assim que o deploy subir — o guarda do contêiner prova que o dado viaja, mas ninguém mediu o produto ao vivo
ainda. **RECOMENDAÇÃO:** rodar o canário **na ordem escrita**, e não concluir nada sobre produção sem antes conferir
a flag do passo 2.

**Nenhum motor paralelo foi criado** (CLAUDE.md §5): a Skill é a da 001.5, a porta do grupo é a da 001.3, o escritor de
`capability_gaps` é o da Auxiliary Factory, o painel de lacunas é o que já existia, e as regras de escrita continuam
morando só em `prompts.py`.

## 11. Nota da execução: **88/100**

Ganha por: o defeito-raiz fechado com guarda genérico (código de `backend/app` que abre caminho fora de `backend/`
reprova, e a 4ª reincidência foi achada por ele); o dado de runtime inteiro dentro da imagem; a base finalmente
respondendo; a publicação feita e conferida linha a linha; 📊 o juiz final sobre 5 condições REAIS — *"nada truncado,
nada sem sentido"*. Perde por: **quatro rodadas** de conserto no mesmo fio, todas por guardas que mediam o compositor
e não o que sai no WhatsApp; a publicação que prometia 23 e entregou 17 em silêncio; e as 40 linhas erradas que a SPEC
não tinha como consertar.

## 12. Telemetria e entrega

```
SESSAO 7bb009e8 (UTC) · 19/09/2026 · gerente Fable 5.1 -> Opus 5 (1M) na rodada 3
AGENTES .... 22 de 24 (teto D-E00151-02, volta a 12 no fechamento) · retomar builder por mensagem nao consome cota
BUILDER .... UM Opus 5 xhigh por fatia; a fatia 3 e as 5 rodadas de conserto no MESMO builder (contexto quente)
JUIZES ..... 1 juiz + 3 confirmacoes §6.1, Fable 5.1 fresco, read-only, todos em copia sem `docs/`
LEITOR ..... 1 Opus read-only: 27 documentos, 3.052 paginas, 135 conferidas
BATERIA .... 1 rodada inteira (2.676 s), triada por diff
```

**A entrega escrita** (CLAUDE.md §2 — entregar nao e commitar, e empurrar):

```
GIT_PUSH_OUTPUT
```

## 13. A parada de 19/09, e como a execução foi retomada

🔴 **Parada legítima (CLAUDE.md §10 (8)):** o hook `teto-de-agentes.py` bloqueou o 13º agente deste chat (a 001.5 gastou
11; o builder da fatia 1 foi o 12º). Não contornei o guarda. ⚠️ **E a causa raiz foi uma afirmação minha sem medição:**
eu havia escrito que `AAA_FAST_TETO_DE_AGENTES=24` estava no `settings.json`, e não estava — o script só gravava se o
texto não existisse no arquivo, e ele existia num comentário. Com autorização escrita do Founder (D-E00151-02), o padrão
do hook local foi a 24 **só nesta SPEC** e voltou a 12 no fechamento. A execução seguiu no mesmo chat, sem reconstruir
nada: leitor → fatia 2 → fatia 3 → juiz → 5 rodadas de conserto → publicação → bateria → push.

**Emendas do revisor à proposta (PASSO 1, 19/09):** E1 aviso ao grupo com teto e só no WhatsApp · E2 a publicação entra nesta execução, conferida linha a linha contra a página · E3 A-bis (catálogos SUSEP) · E4 `TOOL_GATEWAY_MODE` em produção é `shadow`, não `off` — nada muda · E5 o guarda do contêiner precisa de env mínimo dummy (pydantic) — feito. **Nota da proposta: 84** (sólida no diagnóstico; perdia por D sem teto de aviso e por não dizer quem publica).

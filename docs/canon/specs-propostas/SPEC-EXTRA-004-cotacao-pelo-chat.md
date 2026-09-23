# SPEC-EXTRA-004 — COTAÇÃO PELO CHAT
## O corretor pede uma cotação em linguagem natural; o AutoBrokers reúne os dados, pergunta o que falta, calcula no multicálculo e volta à mesma conversa com o resultado

**Status:** PROPOSTA — **depende da EXTRA-003, fatias 1, 2 e 4** (espera durável · `QuoteProvider` + adaptador · comparação e apresentação). Não converte antes delas.
**Versão:** 1.0 · 22/09/2026 · **Baseline:** `origin/main` = `d8510df` (herdado da 003; re-medir no BLOCO 0) · **Branch:** a definir na conversão.
**Evidência:** `SPEC-EXTRA-002-investigacao-prova-agger-RESEARCH-PACK.md` (citado como **RP**) · `SPEC-EXTRA-003-renovacao-feita.md` (citada como **003**).
**Origem:** EXTRA-002 §8 (a sequência 003 → 004 → 007) · 003 §5 ("pedir ao cliente" nasce aqui).

---

## 0. Resultado

> 💭 O corretor escreve no Chat Principal: *"cota o Corolla 2022 do cliente de CPF tal, pernoite no CEP tal"*. O AutoBrokers encontra o cliente e o carro, diz o que já sabe e **pergunta só o que falta** (uso, garagem, condutor). Mostra o resumo do que vai calcular, o corretor confirma, e a resposta imediata é: *"Disparei o cálculo em 17 seguradoras. Leva de 30 s a 7 min; pode continuar trabalhando, eu volto aqui."* Minutos depois, **na mesma conversa**, chega: *"11 ofertas · menor preço R$ … · menor franquia … · 6 não ofertaram (motivos) — [ver apresentação]"*.

🔴 **O chat não calcula nem apresenta: PEDE à fundação da 003.** Esta SPEC acrescenta a **coleta conversacional**, o **modo nova** e a **volta à conversa**.

### 0.1 EXECUTION CARD — proposto, a confirmar no BLOCO 0

```text
OUTCOME ........ o corretor pede a cotação no chat e recebe, na mesma conversa, ofertas comparadas
                 e a apresentação pronta para revisar — sem abrir o multicálculo
RISCO .......... 6  (ALCANCE 2 a corretora — nada chega ao segurado sem o corretor ·
                    REVERSIBILIDADE 3 o cálculo SAI DO PRÉDIO: cria versão de negócio no multicálculo
                    e nº de cálculo em cada seguradora (📊 RP §2.4 `nroCalculo`) — não se desfaz ·
                    FREQUÊNCIA 1 toda semana, por corretor)
SUPERFÍCIE ..... 2  vários comportamentos (coleta, confirmação, volta ao chat) sobre peça que a 003
                    faz nascer; os lugares são listáveis (§2)
PISO ........... §3.2: credencial/sessão de terceiro (usuário robô) · o filtro company_id · disparo
                 que sai do prédio
NÍVEL .......... CRÍTICO (piso + soma 6) · builders Opus xhigh · juiz Fable ‖ red team Fable ·
                 lente do dado no canário (o número exibido no chat = o do multicálculo aberto)
O FIO .......... §2 — o TESTE DO FIO é a 1ª entrega: do texto do corretor à mensagem de volta na
                 MESMA conversa, motor real, dublê só no HTTP do multicálculo (fixtures da 003)
PARALELISMO .... fatia 1 (backend/app/agents/tools/quote_chat_tool.py, backend/app/quote/perguntas.py)
                 ∥ fatia 2 (backend/app/quote/retorno.py, app/dashboard/chat/*) — disjuntas
UNIDADES ....... 3 fatias (§8) + 1 costura
COESÃO ......... fatia 3 mexe no módulo da matriz da 003 → série, depois de 1 e 2
TIME ........... 2 builders em paralelo · juiz ‖ red team · ESCALAÇÃO se a volta ao chat depender
                 de canal novo (gatilho: Realtime não entrega — §3, premissa P3)
REFERÊNCIA ..... interna: `auxiliary_run_tool.py:157-213` (enfileira e responde), `dispatch_mirror.py`
                 (escritor assíncrono de `messages`), `app/dashboard/chat/page.tsx:240-248` (Realtime);
                 externa §10
GATES .......... §7
O ELO .......... "o resultado volta ao chat" liga o fim do run (A) à tela do corretor (B): medir que
                 a mensagem inserida pelo run APARECE na conversa aberta sem recarregar
FAIXA .......... 💭 6–10 h, 1 sessão de gerente, depois da 003 fechada
```

---

## 1. Premissas que mudariam o desenho (BLOCO 0 mede, com o comando — protocolo §0.4)

```text
P1 a fundação da 003 está na main       git log origin/main -- backend/app/providers/quote_*   senão: não começa
P2 o histórico do agente vem de          mostrar a linha do carregador em api/chat.py            senão: a fatia 2 grava
   `messages` (o turno seguinte vê a                                                                 também onde ele lê
   cotação)
P3 `messages` na publicação Realtime     select * from pg_publication_tables                     senão: ESCALAÇÃO
                                         where tablename='messages'
P4 a RLS entrega ao corretor a linha     teste com 2 usuários de 2 corretoras                    senão: P1 de segurança
   que o service role inseriu
P5 a cota da EXTRA-001.8 alcança tool    grep da cota no gateway                                 senão: a fatia 1 põe o teto
P6 cotação nova usa o mesmo calcularV2   ❓ RP §6 sem HAR de seguro novo → E3 da 002 + 1 caso    senão: o modo nasce na 003
```

---

## 2. O FIO

| # | elo | peça | estado |
|---|---|---|---|
| 1 | o corretor escreve no Chat Principal | `app/dashboard/chat/page.tsx` → `backend/app/api/chat.py` (SSE, 📊 `chat.py:548` `text/event-stream`) | EXISTE |
| 2 | o agente reconhece o pedido e chama a ferramenta | Tool `cotar_auto` registrada pelo Tool Gateway sob a Capability `quote.auto.calculate` (registro existente, nada paralelo) | 🆕 tool · 🔧 registro |
| 3 | acha o cliente, a apólice (se houver) e o carro | `infocap_tool.py` / `vehicle_tool.py` → `PolicyDataProvider` (company_id injetado pelo runtime) | EXISTE |
| 4 | abre o **rascunho**: um Work Run `quote.chat` em `needs_input`, preso à conversa | `WorkRunService.criar(idempotency_key=f"quote:{company_id}:{conversation_id}:{n}")` + `work_waits` de conversa (📊 RP §4: `work_waits` já é espera de **conversa**) | EXISTE · 🔧 |
| 5 | cotação anterior e enriquecimento (placa → FIPE, CPF → pessoa, CEP → endereço) | `QuoteProvider.buscar_cotacao_anterior` + consultas da 4ª fonte (003 §3.1) | reusa 003 |
| 6 | a MATRIZ DE VERDADE monta a entrada e lista lacunas | módulo da matriz da 003 (§3) ganha o **modo `nova`** | 🔧 evolui 003 |
| 7 | cada lacuna vira UMA pergunta ao corretor, em linguagem de gente | `backend/app/quote/perguntas.py`: campo → pergunta fixa, agrupada em rodadas (§5) | 🆕 |
| 8 | a resposta do corretor vira campo com origem | `CampoComOrigem(origem="corretor", turno=message_id)`; o agente extrai, **o resumo devolve para conferir** | 🔧 |
| 9 | resumo e confirmação | "vou calcular isto: … confirma?" → evento `quote.confirmado` com o **hash da entrada** (§6) | 🆕 |
| 10 | disparo | `QuoteProvider.calcular(entrada, correlation_id=hash)` | reusa 003 |
| 11 | a ferramenta responde JÁ ("disparei, volto aqui") e o turno termina | padrão `auxiliary_run_tool.py:157-213`, sem `sleep` | 🔧 |
| 12 | espera durável, coleta, normalização, nova tentativa das transitórias | 003 fatias 1–2 e elos 9–12 | reusa 003 |
| 13 | comparação honesta | 003 §4.3 — sem seguro atual, o rótulo "mais parecida com a atual" **não aparece** | reusa 003 |
| 14 | apresentação | template da 003 com a seção "seguro atual" **opcional** | 🔧 evolui 003 |
| 15 | **a volta à conversa** | passo final do run insere mensagem `assistant` em `messages` (conversation_id e company_id DO RUN) → a assinatura Realtime que a tela já tem mostra na hora (📊 `page.tsx:240-248`, `postgres_changes` INSERT em `messages`) | 🔧 |
| 16 | segunda porta, para quem saiu do chat | a cotação aparece em Entregas (📊 rota `app/api/dashboard/entregas/route.ts` existe) | EXISTE |
| 17 | o corretor revisa e envia | link `/r/[token]` (📊 `service.py:484-580`; 📊 `artifact_shares` = 0 linhas — nunca usado) + canal da corretora, **ação humana** | EXISTE · 🔧 |

🔴 **O teste do fio** atravessa 1→15 com o motor real, dublê **só no HTTP do multicálculo** (fixtures sanitizadas da 003) e afirma a linha em `messages` com o `conversation_id` de origem. Nasce vermelho.

⚠️ **A lição que já custou uma vez:** 📊 `research_tool.py:97` cria run com `source_type="research"`, que o CHECK do banco recusa → 📊 0 runs `research.execute` na vida (RP §10.2). A ferramenta **parecia** funcionar. Por isso o G2 (§7) conta o run no banco, não a resposta da ferramenta.

---

## 3. O trabalho longo no chat — 2 a 7 minutos

📊 RP §2.3: ofertas válidas completas em **30 s** e **229 s**; conjunto fechado em **413–420 s** (n = 2). Um turno de chat não pode segurar isso.

**O que existe hoje** (📊 medido por outro agente, conferido nesta sessão):
- (a) `portal_tool.py:780-827`: espera **síncrona** com teto de 150 s; estourou, responde "queued" e o `vigia_do_portal.py` avisa depois (a marca `entregue_ao_agente` evita aviso duplo).
- (b) `auxiliary_run_tool.py:157-213`: enfileira e diz *"o resultado aparece em Entregas"*.
- (c) 📊 `dispatch_mirror.py` já **escreve em `messages` fora do turno**; 📊 `page.tsx:240-248` já **assina** INSERT em `messages` da conversa aberta (nasceu para a passagem a humano).

Nenhum devolve trabalho longo à conversa que o pediu — mas as peças existem.

```text
A  espera síncrona com teto (padrão a) ............................ 25  📊 teto 150 s < 229 s úteis; prende SSE e trabalhador
B  enfileira e manda olhar Entregas (padrão b) .................... 60  honesto, mas a conversa perde o fio
C  B + o run escreve a resposta na MESMA conversa ao fechar
   (padrão c); Entregas continua como segunda porta ............... 88  zero canal novo; quem ficou vê chegar
D  C + mensagens parciais ("5 de 17 responderam…") ................ 70  ruído → fica SOB DEMANDA: "e aí?" → `consultar_cotacao`
E  canal novo (WebSocket próprio, serviço de notificação) ......... 15  motor paralelo (CLAUDE.md §5)
```

🔴 **Regras da opção C:**
```text
1 mensagem de volta, no fechamento: todas decididas, ou o corte do multicálculo, ou só transitórias restando
a mensagem leva no payload: work_run_id · artifact_id · estado (003 §5) — a tela desenha o cartão
conversation_id e company_id saem do RUN, nunca do texto nem do LLM
a marca `entregue_na_conversa` no run impede a 2ª mensagem (molde: `entregue_ao_agente`, portal_tool)
falhou? a mensagem diz a causa e quem destrava (003 §6) — silêncio é proibido
```

---

## 4. O que reusa da 003 — e o que é só daqui

💭 **≈ 70 % do caminho de código é da 003** (em peso de código, estimado; em elos do §2: 6 da 003 + 3 já existentes, de 17).

```text
DA 003, importado — nunca copiado      espera durável e retomada · QuoteProvider, adaptador, conexão, lock ·
                                       matriz (ganha o modo `nova`) · ResultadoDeCotacao · comparação e rótulos ·
                                       template ("seguro atual" vira opcional) · estados honestos
SÓ DA 004                              `cotar_auto` e `consultar_cotacao` · rascunho em needs_input preso à
                                       conversa · perguntas (§5) · confirmação com hash (§6) · volta à conversa
```

🔴 **Onde vive a matriz.** Se a 003 a criou sob `renewal/`, a fatia 3 a **promove** a `quote/` (mover + reexportar), sem segunda cópia. Duas matrizes = dois critérios de "o que falta" = motor paralelo.

---

## 5. Cotação NOVA × renovação — o que aqui precisa ser PERGUNTADO

Na renovação, o questionário de risco e o condutor **voltam do negócio do ano anterior** (📊 RP §3, `GET negocio/{uuid}`). Na cotação nova, só voltam se o cliente foi cotado antes no multicálculo; senão, **alguém responde**. Na v1, é o corretor.

**O que se completa sozinho** (4ª fonte, 003 §3.1): CPF → nome, nascimento, sexo, estado civil · placa → FIPE, modelo, ano, chassi, combustível · CEP → endereço.

**As perguntas mínimas** (📊 campos do `calcularV2`, RP §3), em três rodadas:

| rodada | pergunta ao corretor | campos que preenche |
|---|---|---|
| 1 · quem e qual carro | CPF/CNPJ do cliente · placa (ou modelo e ano, se zero km) · CEP onde o carro dorme | `cpfCnpj`, `placa`/`zeroKm`, `cepPernoite` |
| 2 · como o carro é usado | uso (particular / trabalho / aplicativo) · tem garagem em casa? no trabalho? na escola? · roda muito por ano? · tem rastreador ou antifurto? · é blindado, tem kit gás, é financiado? | `tpUso`, `periodoUso`, `garagemResidencia/Trabalho/Estudo`, `kmAnual`, `rastreador`, `antiFurto`, `blindado`, `kitGas`, `alienado` |
| 3 · quem dirige | o motorista principal é o próprio cliente? (se não: nome, CPF, nascimento, relação) · desde quando tem habilitação · mora com alguém de 18 a 25 anos que dirige? | condutor `principal`, `cpf`, `dataNasc`, `dataPrimHabil`, `relacComSegurado`, `tpResidencia`, `jovemCondutor` |
| ao confirmar | início da vigência (padrão: hoje) · o cliente tem seguro hoje? em qual seguradora, até quando, qual bônus? | `vigenciaIni`; se tiver: `seguradoraAnteriorId`, `vigFimAnterior`, `bonusAnterior` |

💭 ≈ 10 perguntas, agrupadas em 3 mensagens. O corretor pode responder tudo de uma vez no primeiro pedido; a ferramenta **só pergunta o que não veio**.

❓ **Cliente com seguro em outra corretora:** o multicálculo trata como `renovacao=true` com seguradora anterior, ou como nova com bônus? 📊 RP §6 não tem HAR de seguro novo → **o E3 da 002 inclui 1 caso novo** (premissa P6).

🔴 **Regras que não se dobram:**
- nenhum campo de risco preenchido pelo LLM sem que o corretor o tenha dito — o que o agente **extraiu** do texto volta no resumo para conferência;
- as perguntas são **texto fixo por campo** (`perguntas.py`), não improviso do modelo — o agente só agrupa e ordena;
- campo que o corretor disse "não sei" fica `desconhecido`; se for bloqueante, a cotação **não dispara** e diz o que falta (estado "precisa confirmar dado", 003 §5).

---

## 6. Approval antes de disparar?

O cálculo **não é proposta nem emissão** (📊 002 §4: "cálculo não é proposta"). Mas sai do prédio: cria versão de negócio e nº de cálculo em cada seguradora. Dado de risco errado vira cálculo real errado.

- **A · confirmação no chat, gravada no run com o hash da entrada — 88.** Dispara só se o hash atual == o confirmado; mudou um campo, pede de novo.
- B · Approval formal — 55. 📊 `validar_para_execucao` tem 0 chamadores (`approvals.py:178-179`); `decidir()` não retoma o run (RP §4). Consertar o Approval é escopo alheio; cabe quando houver envio ao cliente.
- C · sem confirmação — 30. Um erro de extração vira cálculo real em 17 seguradoras.

🔴 **Teto de custo** (independe da opção): no máximo 💭 N cálculos por corretor por hora e por corretora por dia, **configuração por corretora**; recálculo da mesma entrada dentro da validade (📊 5 dias, 002 §0) **devolve o resultado guardado**, sem novo disparo (premissa P5).

---

## 7. Gates — cada guarda com a sua mutação

| gate | afirma | mutação que o deixa vermelho |
|---|---|---|
| G1 | teste do fio 1→15 verde | remover o passo de volta à conversa |
| G2 | chamar `cotar_auto` **cria** 1 run `quote.chat` no banco (contado, não inferido) | `source_type` inválido (a lição do `research_tool`) |
| G3 | nenhum disparo sem `quote.confirmado` com o hash da entrada exata | alterar 1 campo depois da confirmação e disparar |
| G4 | "confirmo" duas vezes → 1 cálculo | remover a checagem de idempotência |
| G5 | a mensagem volta à conversa de origem e só a ela; 2 corretoras, 2 conversas simultâneas, zero cruzamento | tirar o filtro `company_id`/`conversation_id` do passo final |
| G6 | todo campo de risco tem origem (`corretor`·`multicálculo`·`gestão`·`derivado`) | o dublê do LLM "preenche" a garagem sem pergunta |
| G7 | a ferramenta devolve o turno em 💭 ≤ 5 s | reintroduzir a espera síncrona |
| G8 | uma só mensagem de volta por run | apagar a marca `entregue_na_conversa` |
| G9 | nenhuma PII, credencial ou comissão em log, evidence ou mensagem (`grep`) | logar a entrada crua |
| G10 | `npm run test:rotas-montam` + `next start` + 1 requisição (CLAUDE.md §9.1 — a fatia 2 mexe em `app/`) | — |
| G11 | canário: 1 cotação nova real por corretora-piloto, pelo chat; a **lente do dado** confere prêmio e franquia contra o multicálculo aberto | — |

---

## 8. As fatias

| fatia | entrega | arquivos | prova |
|---|---|---|---|
| **1 · Coleta e confirmação** | `cotar_auto`, `consultar_cotacao`, rascunho em `needs_input`, perguntas por rodada, extração com origem, resumo, hash, teto de custo | `backend/app/agents/tools/quote_chat_tool.py`, `backend/app/quote/perguntas.py`, registro da tool | G2, G3, G4, G6, G7 |
| **2 · A volta à conversa** | passo final que escreve em `messages`; marca anti-duplicata; cartão da cotação na tela do chat | `backend/app/quote/retorno.py`, `app/dashboard/chat/*` | G5, G8, G10 |
| **3 · Modo nova + costura** | a matriz da 003 ganha `modo="nova"` (e é promovida a `quote/` se preciso); template com "seguro atual" opcional; o fio inteiro | módulo da matriz da 003, template da 003 | G1, G9, G11 |

---

## 9. O que esta SPEC NÃO faz

Não envia nada ao segurado (D-E002-04 A) · não faz proposta, não emite, não paga · não escolhe "a melhor" (D-E002-05) · não pergunta ao cliente final (D-E004-03) · só AUTO · não cria canal, fila, worker nem notificador.

---

## 10. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS

| URL | o que faz | o que MODELAMOS | o que REJEITAMOS | como o juiz inspeciona |
|---|---|---|---|---|
| https://www.rfc-editor.org/rfc/rfc9110#section-15.3.3 | `202 Accepted`: aceito, processamento **não terminou**; sugere um "status monitor" (texto conferido nesta sessão) | responder "aceito, volto aqui" + `consultar_cotacao` | segurar a conexão | G7 |
| https://supabase.com/docs/guides/realtime/postgres-changes | assinatura de INSERT; exige a publicação `supabase_realtime`; a RLS filtra o que cada um recebe (inspecionada) | a volta pela assinatura que a tela **já tem** | canal próprio | P3, P4, G5 |
| https://docs.temporal.io/workflows#durable-execution | fluxo que dorme e retoma sem repetir efeito (não reaberta nesta sessão) | a espera sem prender trabalhador (003 fatia 1) | trazer o Temporal (CLAUDE.md §5) | G4 |
| https://aggilizador.com.br | multicálculo assíncrono, resultado padronizado (📊 RP §2.3–2.4; não reaberta) | o formulário real como lista de perguntas | expor o JSON dele | §5 × RP §3, campo a campo |
| `MODELO DE APRESENTAÇÃO COM 3 OPÇÕES.pdf` (intake, observada) | o que a corretora envia hoje | o resumo: preço, franquia, validade | tabela inteira no chat | PDF e cartão lado a lado |

---

## 11. Decisões do Founder

**D-E004-01 · Como o resultado volta** → **C** (a mesma conversa + Entregas) **88** · B (só Entregas) 60 · A (espera síncrona) 25. Já vem decidida pela diferença.

**D-E004-02 · Confirmar antes de calcular** → **confirmação no chat com hash** **88** · Approval formal 55 · sem confirmação 30.

**D-E004-03 · Quem responde as perguntas**
→ **o corretor, no chat (v1)** **90** · link de formulário ao cliente (o da 007) 70, depois da 007 · o AutoBrokers pergunta ao cliente pelo WhatsApp 35 (é ENVIO: piso CRÍTICO, consentimento).

**D-E004-04 · O que aparece no chat** → **resumo com os rótulos + link da apresentação** **90** · tabela completa das 17 seguradoras no chat 45 (ilegível no celular).

**D-E004-05 · Perguntas** → **texto fixo por campo, o agente agrupa** **86** · o LLM formula livremente 40 (pergunta que muda de forma muda de resposta).

**D-E004-06 · Teto de cálculos** → **configuração por corretora, com padrão conservador** **85** · sem teto na v1 45. 💭 O número padrão sai do E4 da 002 e da licença do robô.

---

## 12. 📋 CAIXA DO FOUNDER

1. **SIM, bloqueia** — a caixa da 002 (§11) e a da 003 (§11): usuário robô e resposta da Agger.
2. **SIM, para a fatia 3** — pedir que o E3 da 002 inclua **1 cotação nova** (premissa P6; RP §6).
3. **SIM, para fechar** — em cada corretora-piloto, 1 corretor e 1 cliente real que queira cotar (G11).
4. não — decidir D-E004-01 a 06 (há padrão recomendado) e o teto diário de cálculos que a corretora aceita pagar.

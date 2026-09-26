# SPEC-118 — O formulário dentro do WhatsApp funciona, e o agente sabe o que vem pela frente

> **Proposta escrita em 26/09/2026**, sobre `origin/main` = `70632a8`, árvore `AutoBrokers-FIX`
> (📊 `git rev-list --count HEAD..origin/main` → `0`).
>
> 🔴 **O outcome, numa frase:** um acionamento de assistência pelo WhatsApp vai do "oi" do
> segurado ao protocolo da seguradora **sem parar no formulário nativo e sem pedir socorro a
> uma pessoa** — nas seguradoras cujo acervo sustenta a prova.
>
> 📊 medido · 💭 ilustrativo (CLAUDE.md §12.1)

---

## 0. O EXECUTION CARD

```
OUTCOME ........  o segurado pede assistência no WhatsApp da corretora e recebe o protocolo da
                  seguradora sem que nenhuma pessoa toque no caso — inclusive quando a seguradora
                  abre o formulário nativo ("o aplicativo dentro da conversa")

RISCO ..........  8  (ALCANCE o SEGURADO 3 · REVERSIBILIDADE saiu do prédio 3 · FREQUÊNCIA todo
                  atendimento 2)
SUPERFÍCIE .....  2  (vários comportamentos + peça nova: mapas de formulário e o portão de coleta)
PISO APLICADO ..  §3.2 — "qualquer coisa que ENVIE: mensagem, acionamento, chamado" → CRÍTICO no
                  mínimo. A soma já dava CRÍTICO; o piso confirma por outro caminho.
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5 xhigh · juiz Opus 5.5 ‖ red team Opus 5.5 ·
                  🔬 lente do dado POR GATILHO (a F2 publica números vindos de `observed_events`)
                  · 1 rodada + 1 confirmação curta

O FIO ..........  ver §1 — 14 elos, do byte de entrada ao protocolo de volta. TRÊS estão rotos,
                  e cada fatia conserta um.
PARALELISMO ....  F1 ‖ F2 (arquivos disjuntos, listados em §4) · F3 → F4 → F5 em série
UNIDADES .......  5 fatias, §4
COESÃO .........  F2 e o portão de coleta tocam o MESMO arquivo-hub
                  (`corridor_playbooks.py`) → §3.4, ficam JUNTOS na F2
TIME ...........  5 builders frescos (um por fatia) · juiz ‖ red team UMA vez no fim ·
                  ESCALAÇÃO se o rebuild do fork falhar 2×
REFERÊNCIA .....  interna `_NATIVE_FLOWS_FAMILIA_HDI_YELUM` (`corridor_playbooks.py:2653`) —
                  a mediana do que passou no gate · externa
                  `docs/canon/O-FORMULARIO-NATIVO-RESOLVIDO.md` (a disciplina de medir com
                  linha de controle)
GATES ..........  §6
O ELO ..........  a afirmação-título é *"o acionamento para PORQUE a rota não existe e o mapa da
                  Porto não existe"*. §2 mede A, mede B e mede que **B chega em A**.
FAIXA ..........  💭 4 h – 7 h de relógio ativo, 5 builders · tetos: 250 turnos, 600 k contexto
```

---

## 1. O FIO — do primeiro byte ao protocolo, elo a elo

```
 ①  segurado escreve              webhook.py::evolution_go_webhook_token
 ②  captura passiva               atlas/observer_intake.py::observer_tap
                                  (agente LIGADO → devolve None, o evento SEGUE)
 ③  allowlist + agrupamento       webhook.py::process_whatsapp_message_background
                                  whatsapp/channel_security.py::attendant_inbound_allowed
 ④  o agente pensa                langchain_service.process_message(required_role="attendance")
 ⑤  o que falta para acionar      agents/tools/insurer_dispatch_tool.py::InsurerDispatchTool._run
                                  corridor_playbooks.py::missing_slots_for_subservice
                                  🔴 ELO ROTO 3 — os campos do FORMULÁRIO não entram aqui (F3)
 ⑥  o agente coleta na conversa   o texto que o agente devolve ao segurado
 ⑦  a sessão nasce pronta         insurer_dispatch_service.py::new_dispatch_session
 ⑧  a mensagem sai                services/dispatch_router.py
                                  insurer_dispatch_service.py::dispatch_live_enabled
 ⑨  a URA responde                insurer_dispatch_service.py::match_ura_step
 ⑩  chega o FORMULÁRIO            corridor_playbooks.py::flow_do_playbook(flow_id)
                                  🔴 ELO ROTO 2 — `porto-auto-whatsapp@v1` não tem `native_flows` (F2)
 ⑪  monta a resposta              corridor_playbooks.py::montar_resposta_de_flow
                                  whatsapp/providers/evolution_go.py::montar_nfm_reply
 ⑫  a resposta SAI                evolution_go.py::send_native_flow_response
                                  POST {base_url}/send/interactiveResponse
                                  ✅ ELO INTEIRO — 📊 provado no ar em 26/09 (§2.1): rota existe,
                                  embrulho presente no caminho REAL. A F1 virou GUARDA, não conserto.
 ⑬  a URA segue até o desfecho    `finalize_anchors` do corredor
 ⑭  o protocolo volta ao segurado `capture_anchors` do corredor
```

🔴 **O TESTE DO FIO é a primeira entrega da F4** e atravessa ① → ⑭ com o **motor real**, dublê só
na borda de rede, alimentado pela **captura real da Porto de 21/09/2026**. Nasce VERMELHO nos três
elos e fica VERDE.

---

## 2. A EVIDÊNCIA — e o ELO

### 2.1 ~~ELO ROTO 1 · a rota do formulário não está no ar~~ — 🔴 **PREMISSA DERRUBADA EM 26/09, PELO COMANDO**

> ⛔ **ESTA SEÇÃO ESTAVA ERRADA E FICA AQUI COMO REGISTRO.** O gerente concluiu **ausência por
> leitura do catálogo** e o comando disse **presença**. É o protocolo §0.4 literal: *"afirmar por
> leitura o que só um comando decide é defeito"*.
>
> 📊 **A MEDIÇÃO QUE CORRIGIU**, 26/09/2026 17:24 (-03), em produção:
> ```
> POST /api/whatsapp-integrations/prova-de-formulario
>      {"company_id":"3aa75902-…","para":"5547****4743"}
> → HTTP 200 · {"success": true, "vencedora": "embrulho DocumentWithCaption"}
>   tentativa 1 (CONTROLE, sem o embrulho) ...... HTTP 500 · "server returned error 479"
>   tentativa 2 (com DocumentWithCaption) ....... HTTP 200 · ACEITO
> → servidor: Type: "InteractiveResponseMessage" · ID 3EB02C9B1BFC57E46E3136
> ```
> 🔴 **`/send/interactiveResponse` EXISTE e FUNCIONA na imagem que está no ar.** O
> `swagger/doc.json` não a lista (88 rotas, 12 de `/send`, zero com `interactive`) porque o patch
> `0005` não acrescentou anotação de swagger. **O catálogo é incompleto; não é a verdade.**
>
> 🔴 **E O ELO FOI FECHADO** (§0.3 — *"medi que B CHEGA em A"*): a prova usa `requests.post`
> direto, então ela sozinha **não** provava o caminho real. Conferido em
> `evolution_go.py::send_native_flow_response`: ele posta em `rota_de_flow_reply()` (=
> `/send/interactiveResponse`) **com `"wrapInDocumentWithCaption": True`** — a mesma rota e o
> mesmo embrulho que a prova mostrou vencendo. **O caminho do acionamento real está inteiro.**
>
> **Consequências:** ⛔ **não há rebuild de imagem nesta SPEC** · ⛔ conferir capacidade pelo
> swagger seria **introduzir** o defeito (devolveria `False` para uma rota que funciona) · ✅ o
> único gargalo de formulário que resta é **o mapa** (§2.2), e o da Porto é construível hoje.

### 2.1-bis O que era o texto original (mantido para auditoria)

**A (o efeito):** `send_native_flow_response` posta em `/send/interactiveResponse`. A rota padrão é
devolvida **sem conferir se ela existe** (`evolution_go.py::rota_de_flow_reply` devolve
`ROTA_DE_FLOW_REPLY_PROVADA` quando a env está vazia).

**B (a causa):** 📊 medido em 26/09/2026 contra o serviço no ar:

```bash
curl -s https://autobrokers-intelligence-os-evolution-go-teste.golhpm.easypanel.host/swagger/doc.json \
  | python -c "import json,sys; d=json.load(sys.stdin)['paths']; \
      print(len(d),'rotas'); print(sorted(p for p in d if p.startswith('/send'))); \
      print('interactive:',[p for p in d if 'interactive' in p.lower()])"
```

Saída: **88 rotas**; as 12 de `/send` são `button, carousel, contact, link, list, location, media,
poll, status/media, status/text, sticker, text`; **`interactive: []`**.

São **exatamente** as 12 de `ROTAS_DE_ENVIO_MEDIDAS` (`evolution_go.py:130`), a lista de ANTES do
patch. 📊 `infra/evolution-go-autobrokers/VERSION` → `0.7.2-autobrokers.4`, com 7 patches, e
`0005-send-interactive-response.patch` abre a 13ª rota. As rotas `/passkey-ceremony/*` (patches
0003/0004) **estão** no ar → a imagem tem patches nossos, mas é **anterior** ao 0005.

**🔴 B chega em A?** É o que a F4 prova: com a captura real da Porto entrando no ⑩, a sessão hoje
termina em `needs_human`; depois da F1+F2, atravessa. **Sem essa medição, esta SPEC seria duas
medições certas e uma causa suposta (§0.3).**

### 2.2 ELO ROTO 2 · os mapas — e o que o acervo sustenta

📊 Medido em `observed_events` em 26/09/2026:

```sql
select insurer_key,
       count(*) filter (where msg_type='flow')                                    as convites,
       count(*) filter (where msg_type='flow_reply' and interactive ? 'native_form') as com_schema,
       count(*) filter (where msg_type='flow_reply' and not (interactive ? 'native_form')) as vazias,
       max(wa_timestamp) filter (where msg_type='flow_reply' and interactive ? 'native_form')::date as ultima
from observed_events where msg_type in ('flow','flow_reply') group by insurer_key;
```

| seguradora | convites | **com schema** | vazias | última útil | declara `native_flows`? |
|---|---|---|---|---|---|
| yelum | 5 | **5** | 13 | 14/09/2026 | ✅ 3 flows |
| porto | 14 | **3** | 30 | **21/09/2026** | ❌ **nenhum** |
| hdi | 1 | **1** | 12 | 04/09/2026 | ✅ 3 flows (mesma família) |
| azul | **0** | **0** | 10 | — | ❌ **nenhum** |

🔴 **A Porto É construível, e com material de cinco dias atrás.** O formulário está identificado:

```
flow_id    709854848132894
flow_name  "Assistência - Captura de endereço dinâmica_v3"
envelope   galaxy_message          (o mesmo legado da família HDI/Yelum)
tela       CAPTURAR_ENDERECO
campos     location · input_confirmar_endereco · rua · numero_residencia · complemento ·
           bairro · cidade · estado · ponto_referencia
```

📊 E existe um SEGUNDO flow da Porto que **não se responde**: `flow_id 1263063458275481`, CTA
*"Avaliar atendimento"* — pesquisa de satisfação. `_SURVEY_NOOP_RE`
(`insurer_dispatch_service.py:383`) já trata pesquisa por texto; o mapa tem de marcar este flow
como **não-respondível** explicitamente.

> 🔴 **O ACHADO QUE MUDA UMA LIÇÃO ANTIGA.** `numero_residencia` é um campo **do formulário**, não
> uma pergunta de texto. CLAUDE.md §9.4 registra que o passo `numero_residencia` *"exigiu por
> semanas uma frase com ZERO ocorrências em 28.096 eventos"*. 📊 Agora se sabe por quê: **a
> pergunta nunca foi texto.** O executor confere se o passo de texto correspondente deve sair.

⛔ **A AZUL NÃO É CONSTRUÍVEL NESTA SPEC.** Zero convites e zero schemas; as 10 respostas são os
registros vazios do defeito antigo do observador. **Inventar o mapa da Azul é proibido** — vira
pendência 🧑 (§8).

### 2.3 ELO ROTO 3 · o agente não sabe o que o formulário vai pedir

`missing_slots_for_subservice` (`corridor_playbooks.py:9079`) soma `required_slots` do subserviço
**+** o que os passos de URA declaram em `requires` — o conserto de 03/08/2026, que fechou a classe
"a sessão nascia `ready_to_send` e travava no meio".

📊 Mas os campos do **formulário** entram só como *validação*, e **escopados ao que já está em
`required_slots`** (`insurer_dispatch_service.py:1457-1470`: `if _slot_pt not in _coletados_aqui:
continue`). Ou seja: **um campo obrigatório do formulário que ninguém escreveu à mão em
`required_slots` nunca é pedido ao segurado.** É o mesmo defeito de 03/08 com outra roupa — e o
conserto é o mesmo formato: **cobrar no PORTÃO, não em cada mapa.**

### 2.4 O que mais o acervo novo tem a dizer

📊 51 sessões observadas nos últimos 30 dias (até 25/09) que a régua **nunca viu** — a tabela de
corredores do painel é a foto de **24/08** (pendência P-PILOTO-06):

| corretora × seguradora | sessões 30 d | 14 d |
|---|---|---|
| Resulta × allianz | 9 | 2 |
| AutoFleet × yelum | 8 | 4 |
| AutoFleet × tokio · Resulta × tokio | 6 + 6 | 2 + 4 |
| AutoFleet × bradesco | 6 | 2 |
| AutoFleet × hdi | 5 | 3 |
| AutoFleet × allianz · porto | 3 + 3 | 2 + 2 |
| mapfre · zurich | 2+1 · 1 | — |

🔴 E o inventário dos corredores mostra onde essas sessões valem mais:

```
ref                              passos  subs  menu  flows
tokio-auto-whatsapp@v1                6     4     4      0   ← 12 sessões novas, 6 passos
mapfre-auto-whatsapp@v1              13     4     4      0   ←  3 sessões novas, 13 passos
alfa-auto-whatsapp@v1                34     4     4      0
bradesco-auto-whatsapp@v1            36     4     4      0   ←  6 sessões novas
allianz-auto-whatsapp@v1             38     4     4      0
azul-auto-whatsapp@v1                54     5     4      0   ← `pneu` declarado SEM tecla
zurich-auto-whatsapp@v1              58     6     6      0
porto-residencial-whatsapp@v1        74     5     0      0
yelum-residencial / hdi-residencial  74/80  5     0      0
allianz-residencial-whatsapp@v1      75     9     0      0
porto-auto-whatsapp@v1               87     8     8    🔴0
hdi-auto / yelum-auto                87/88  5     5      3
```

⚠️ `menu 0` no residencial **não é defeito**: aquelas URAs não escolhem o ofício por menu numerado
(📊 `allianz/resi/encanador` tirou 106/106 na régua de 24/08). 🔴 `azul-auto` declarar `pneu` sem
tecla **é** o defeito da CLAUDE.md §9.5 — hoje cai em handoff, o que é honesto mas não atende.

📊 **A régua não cabe em 560 s.** Medido em 26/09:
`timeout 560 python scripts/medir_rota.py --todas --formato tabela` → **exit 124** (morto pelo
timeout), saída de **0 bytes**. ⚠️ Não se sabe quanto ela leva — sabe-se que é **mais de 9 min**.
Quem executar a F4 roda em 2º plano **sem teto**, mede o tempo real e o escreve no relatório;
se passar de 30 min, isso é um achado em si e vira pendência.

---

## 3. O QUE ESTA SPEC **NÃO** FAZ

```
⛔ não inventa o mapa da Azul (sem material — §2.2). Vira pendência 🧑 com o roteiro de captura
⛔ não inventa tecla de menu que a tela não mostrou (azul/pneu incluído)
⛔ não liga agente de atendimento nenhum
⛔ não dispara acionamento real: o teste do fio usa o motor com dublê na borda de rede
⛔ não mexe em Portal de Vidros (001.10/001.10.1)
⛔ não reescreve corredor que está passando — a régua é o controle
```

---

## 4. AS FATIAS — 5, com os arquivos de cada uma

### F1 · O TRANSPORTE — 🔴 REESCRITA EM 26/09: virou GUARDA, não conserto
**Paralela com F2a.** Arquivos:
```
backend/app/services/whatsapp/providers/evolution_go.py   (docstring vencida + honestidade)
backend/tests/test_o_transporte_do_formulario_e_conferido.py   (NOVO)
```

⛔ **SAIU do escopo:** o rebuild da imagem (não é preciso — §2.1) · a conferência por swagger
(**introduziria** o defeito) · o sinal `formulario_tem_transporte` baseado nela.

1. 🔴 **O GUARDA QUE FIXA A VERDADE MEDIDA.** Teste que afirma, executavelmente, que o transporte
   é `/send/interactiveResponse` + envelope `galaxy_message` + **embrulho
   `DocumentWithCaptionMessage` OBRIGATÓRIO** — 📊 é ele a diferença entre 200 e 479. Remover o
   embrulho deixa o teste **VERMELHO**. É a regressão silenciosa que ninguém olharia.
2. 🔴 **A DOCSTRING VENCIDA SAI.** O topo de `evolution_go.py` afirma que *"o que falta é uma rota
   que este build do GO não tem"* e que nenhuma seguradora recebeu resposta nossa. 📊 A primeira
   metade é **falsa desde hoje**. CLAUDE.md §9.3: verdade vencida no arquivo que decide se
   mensagem sai para seguradora é o defeito mais caro do repositório.
3. `flow_reply_supported()` passa a **dizer o que sabe e o que não sabe** — sem inventar sonda de
   rede. A prova honesta é a rota `prova-de-formulario`, citada pelo caminho.
4. ⛔ `/health`: só publica se houver algo HONESTO sem sonda. Nenhum sinal é melhor que um sinal
   que finge medir.

### F2 · OS MAPAS — a Porto passa a existir; Yelum/HDI ficam mais fortes
**Paralela com F1.** Arquivo único (é o hub, e a coesão §3.4 manda juntar):
```
backend/app/services/corridor_playbooks.py
backend/tests/fixtures/formulario_porto_21_09.json              (NOVO, telefones mascarados)
backend/tests/test_o_mapa_da_porto_veio_do_acervo.py            (NOVO)
```

1. `native_flows` de `porto-auto-whatsapp@v1` a partir das **3 capturas com schema**, com o bloco
   `observed` (fonte, `insurer_key`, `msg_type`, `event_source`, `wa_timestamp`) no mesmo formato da
   referência interna `_NATIVE_FLOWS_FAMILIA_HDI_YELUM`.
2. O flow de **pesquisa** (`1263063458275481`) marcado como **não-respondível**.
3. **O portão de coleta (ELO 3):** `missing_slots_for_subservice` passa a somar os campos
   **obrigatórios dos formulários que ESTE subserviço realmente abre** — escopado, como o juiz 4 já
   exigiu em `insurer_dispatch_service.py:1445` (*"bloquear rota que não vê a tela é interrogatório
   à toa"*).
4. Conferir se o passo de texto `numero_residencia` deve sair (§2.2).
5. Enriquecer Yelum/HDI com as 5 capturas, **sem tocar no que a régua já aprova**.

### F3 · O AGENTE PERGUNTA ANTES — e diz por quê
**Série, depois da F2.** Arquivos:
```
backend/app/agents/tools/insurer_dispatch_tool.py
backend/app/services/insurer_dispatch_service.py
backend/tests/test_o_agente_pede_antes_de_acionar.py            (NOVO)
```
As `client_instructions` e a descrição da tool passam a dizer, **por subserviço**, o que a
seguradora vai pedir no formulário — para o agente coletar **na conversa inicial**, uma informação
por vez, antes de acionar. O guarda mede: com os campos do formulário ausentes, a sessão **não**
nasce `ready_to_send`.

### F4 · A COSTURA — o teste do fio, e a régua regenerada
**Série, depois de F1+F2+F3.** Arquivos:
```
backend/tests/test_o_fio_do_acionamento_atravessa_o_formulario.py   (NOVO — a 1ª entrega)
docs/canon/reports/INVENTARIO-DE-ROTAS.md                           (regerado)
```
1. 🔴 **O TESTE DO FIO**: ① → ⑭ com o motor real e a captura da Porto de 21/09. Nasce vermelho.
2. **A régua regenerada** (`medir_rota.py --todas`), com as 51 sessões novas. 🔴 **Nenhuma rota
   pode CAIR** — é o controle de que a F2 não quebrou o que passava.
3. 🔬 **Lente do dado:** os números publicados da §2.2 reconferidos por caminho independente.

### F5 · O CONTROLE DO FOUNDER — e a trava contra confusão depois
**Série, por último.** Arquivos:
```
docs/canon/ESTADO-DAS-SPECS.md · PENDENCIAS.md · FOUNDER-DECISIONS.md ·
TAREFAS-DO-FOUNDER.md · CHANGE-ADDENDA.md
docs/canon/painel-do-founder/**        (a aba CORREDORES, com a régua de hoje)
backend/tests/test_a_lista_de_finalizacao_nao_tem_fantasma.py       (NOVO)
```
1. **A aba CORREDORES do painel deixa de ser a foto de 24/08**, com três faixas explícitas:
   **PRONTO ponta a ponta** · **quase, e falta o quê** · **precisa de acionamento da Regina/Saionara**.
2. 🔴 **A trava contra a confusão que o Founder previu:** hoje um `ref` escrito errado em
   `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` **nunca finaliza, em silêncio**. Passa a ser **defeito
   visível**: `/health` publica os refs que **não resolvem** para corredor nenhum, e um guarda
   exige que a lista só contenha refs existentes.

---

## 5. A DECISÃO QUE VAI AO FOUNDER

**D-118-01 · como fica a finalização depois dos testes.** O Founder pediu *"todas liberadas, para
não ter confusão depois"*.

| opção | nota | o que é |
|---|---|---|
| `DISPATCH_FINALIZE_MODE=test` + lista explícita durante os testes; **`live` depois**, com a lista apagada | **88** | dois estados nomeados, cada um com um sinal no `/health`; a lista fantasma vira defeito visível (F5.2) |
| `live` já agora | 55 | abre as 14 seguradoras antes de o formulário estar provado |
| manter a lista seletiva para sempre | 40 | é a configuração que "esquece" corredor novo — a confusão que ele quer evitar |

**Recomendação: a primeira.** Ele já aplicou o estado de teste
(📊 `finalize_abre_de_verdade: ['porto-auto-whatsapp@v1','yelum-auto-whatsapp@v3']`, conferido no
`/health` em 26/09). A F5.2 é o que impede a confusão de voltar.

---

## 6. OS GATES — o que precisa ficar verde

```
G1  ✅ JÁ VERDE em 26/09 — a prova em produção, com LINHA DE CONTROLE (§2.1):
        POST /api/whatsapp-integrations/prova-de-formulario → 200 · controle 479 · aceito
        ⛔ substitui o gate por swagger, que estava ERRADO (catálogo incompleto)
G2  🔴 o caminho REAL usa a mesma rota e o mesmo embrulho — conferido em
        evolution_go.py::send_native_flow_response (`wrapInDocumentWithCaption: True`)
        e FIXADO por guarda na F1
G3  🔴 O TESTE DO FIO verde (F4.1) — e provadamente VERMELHO antes da F1+F2
G4  a régua regenerada: nenhuma das 73 rotas com nota MENOR que em 24/08
G5  python backend/scripts/conferir_o_que_esta_no_ar.py                           → TODOS BATEM
G6  mutação dos guardas NOVOS, uma vez: cada um fica VERMELHO com o defeito
        histórico reintroduzido (CLAUDE.md §9.5)
G7  bateria DEPOIS do conserto, triada NOMINALMENTE contra
        docs/canon/reports/BATERIA-LINHA-DE-BASE.txt
G8  a Azul declarada NÃO MAPEADA, com o motivo e o roteiro de captura escritos
G9  a aba CORREDORES do painel republicada com a régua de HOJE
```

⚠️ Esta SPEC **não** toca `app/`, `middleware.ts` nem `next.config.js` → o gate `test:rotas-montam`
+ `next start` (CLAUDE.md §9.1) **não** se aplica. Se alguma fatia passar a tocar, ele volta.

---

## 7. A REFERÊNCIA INSPECIONÁVEL

| dimensão | referência | onde |
|---|---|---|
| forma de um mapa de formulário | `_NATIVE_FLOWS_FAMILIA_HDI_YELUM` | `corridor_playbooks.py:2653` |
| disciplina de medir o transporte | a prova de 03/08 **com linha de controle** | `docs/canon/O-FORMULARIO-NATIVO-RESOLVIDO.md` §5 |
| portão que cobra antes | o conserto de `requires` de 03/08 | `corridor_playbooks.py:9096-9112` |
| régua de corredor | duas perguntas, não uma | CLAUDE.md §9.5 |

---

## 8. AS PENDÊNCIAS QUE ESTA SPEC DEIXA (§11.1 do CLAUDE.md)

| # | o que | de quem | o que custa esquecer |
|---|---|---|---|
| P-118-01 | **mapa do formulário da Azul** — sem material | 🧑 um acionamento auto real até o formulário | 📊 21% das sessões da Azul abrem formulário; sem o mapa, todas param |
| P-118-02 | **`azul/auto/pneu` sem tecla** — o menu migrou em 07/04/2026 | 🧑 um acionamento de pneu na Azul | a rota existe e nunca atende |
| P-118-03 | **`tokio` com 6 passos e `mapfre` com 13** | 🤖 próxima SPEC, com as 12 e 3 sessões novas | as duas travam em tela não mapeada |
| P-118-04 | `response_message` é exigido pela seguradora? | 🤖 só mede com seguradora do outro lado | suspeito nº 1 se a resposta for descartada em silêncio |
| P-118-05 | `MessageSecret` nunca testado | 🤖 | pode ser necessário em caso não visto |
| P-118-06 | o porteiro de "Ligar agente" manda `X-AutoBrokers-Internal-Key`, o backend espera `X-Internal-Key` → 401 → **fail-open** | 🤖 1 linha | o porteiro **nunca** roda de verdade a partir da tela |
| P-118-07 | `ignoreGroups: true` — "AGENTE"/"EU CUIDO" digitado no grupo não chega | 🧑 decisão de canal | o humano não consegue assumir pelo grupo |

---

## 9. O QUE O FOUNDER FAZ (e só ele)

```
1. 🧑 autorizar o rebuild da imagem do Evolution GO (F1) — é implantação de infra, e pode
      exigir reler o QR do WhatsApp pareado
2. 🧑 depois do G1: clicar "Provar envio de formulário" no painel (G2)
3. 🧑 os testes ponta a ponta, na ordem que o relatório final entregar
4. 🧑 as capturas de P-118-01 e P-118-02 (Azul), quando quiser fechá-las
```

---

## 10. CONTRA-INDICAÇÕES REGISTRADAS

```
🔴 se o rebuild do fork falhar DUAS vezes → ESCALAÇÃO (§8 do protocolo), não uma terceira volta.
   O produto continua entregando: sem transporte, o corredor declara
   `formulario_pronto_sem_transporte` ANTES de acionar (F1.2) e o caso vai a uma pessoa com o
   motivo escrito — que é pior que atender, e MUITO melhor que parar no meio com a URA rodando.
🔴 nenhum mapa novo entra sem o bloco `observed` apontando a linha do acervo que o sustenta.
   Mapa sem procedência é invenção com cara de medição.
```

modelo: claude-opus-5-5

# LAUDO DO JUIZ FRESCO — SPEC-132-A (o chat principal)

> 14/10/2026 · juiz Opus 5.5, só leitura sobre o código · branch `spec/132-o-chat-e-a-cotacao` · HEAD `618ba14` · base `285cadc`
> Diff julgado: o recorte da 132-A (53 arquivos, +8.043 / −1.713, `git diff 285cadc..HEAD --stat -- <lista do pedido>`).
> Em `graph.py` e `main.py` julguei só o que é da 132-A (esforço, leituras em paralelo, trava do pool, aquecimento).
> 📊 = medido aqui, com o comando · 💭 = inferência.

## VEREDITO

**PASSA, sem BLOCKER.** Cinco pendências, uma delas com medição e linha de controle (a corrida do mesmo
`client_request_id`). Os ataques de segurança e de isolamento (path de outra corretora, `..`, prefixo parecido, path
vazio, widget com lista de anexos, conversa de outra corretora, `esforco` inválido, guardrail dentro do stream) foram
reproduzidos e **seguraram**.

## EVIDÊNCIA — os gates do pedido, rodados pela trava (📊 14/10, saída em `scratchpad/juiz132a/*.txt`)

| comando | resultado |
|---|---|
| `python -m pytest tests/test_spec132a_o_fio.py -q -p no:cacheprovider` | **5 passed** (180 s) |
| `python -m pytest tests/test_spec132a_turno_rapido.py -q …` | **19 passed** (53 s) |
| `python -m pytest tests/test_spec132a_anexos.py -q …` | **21 passed** (51 s) |
| `node scripts/o-chat-novo.test.mjs` | **109 OK · 0 falha** · "VERDE — a caixa é uma só…" · rc=0 |
| `node scripts/o-upload-do-chat.test.mjs` | **48 ok, 0 falha(s)** · rc=0 (inclui os CONTROLES: sem a conferência do prefixo o path alheio passaria; sem o mapa de extensão o HEIC do Android seria recusado) |
| `npm run test:chat-shell` | **75 OK** · "0 falha(s) de verdade · 0 VERMELHO ESPERADO" · rc=0 |
| `npm run test:rotas-montam` | **4 OK** · "A TABELA DE ROTAS MONTA" · rc=0 |

Três números conferidos por amostra (§0.4): 5/19/21 no pytest; 109/48/75 nos testes node.

### Sondas próprias do juiz (arquivos no scratchpad, nenhum no repositório)
`scratchpad/juiz132a/test_juiz_132a.py`, `test_juiz_corrida.py`, `sonda_mascara.py`. Elas usam o MOTOR real
(`chat_stream` pelo ASGI cru do guarda da A3, `chat_anexos.tabela_da_planilha` + `vision_service.mascarar` reais).

1. **O guardrail ainda barra, agora dentro do stream, e nada é gravado.** Com um guardrail dublado que barra:
   `tipos: ['turn.accepted','stage.started','stage.started','policy.blocked','turn.completed','[DONE]']` ·
   `assistentes gravados: []` · `motor chamado: 0` · `turn.completed: {'status':'failed','persisted':False,'error_code':'policy'}`.
   PASSA (`chat.py:1552-1559` emite o evento; `_persistir` com conteúdo vazio devolve False, `chat.py:1202`).
2. **`options.esforco='turbo'`, `web_search:'sim'`, chave `x`** → status 200, o grafo é pedido SEM `esforco_do_pedido`,
   o motor recebe `esforco='equilibrado'`, `options={}`, o turno grava `esforco: equilibrado`. PASSA
   (`chat.py:33-56` `opcoes_validas`; `model_policy.py` `nivel_da_escolha` → None; BFF `lerOpcoes` também descarta).
3. **A mesma mensagem 2× ao mesmo tempo** → ver a pendência P1 abaixo (medida, com controle).
4. **A máscara nas planilhas** → ver a pendência P2.

## OS ATAQUES, UM POR UM

| ataque | resultado | onde |
|---|---|---|
| arquivo de OUTRA corretora pelo path (BFF) | **segura** · 403 antes de gravar conversa ou pergunta; segmentos `[A-Za-z0-9._-]`, sem `.`/`..`, 1º segmento == `company_id` da sessão (não `startsWith`: prefixo parecido cai) | `app/api/chat/stream/route.ts:49-56,144-153`; teste node ④ + fuga `CO_A/../CO_B` (`o-upload-do-chat.test.mjs:259`) |
| idem no backend (cinto) | **segura** · antes do stream `anexos_fora_da_corretora` (`startswith(prefixo+'/')`, `..`, `\`, prefixo vazio) → `policy.blocked` sem gravar; e de novo por arquivo em `chat_anexos.path_da_corretora` + bucket ∈ {chat-media, chat-docs} | `chat.py:207-220,856-866`; `chat_anexos.py:206-215,571-573` |
| path vazio / lista não-lista / >10 | **segura** · BFF 400; Pydantic `max_length=10`; `preparar` corta em 10 | route.ts:58-63; `chat.py:72` |
| widget com `attachments` | **segura** · zerado antes de tudo (`chat.py:264-268`); teste `test_e_o_widget_nao_le_anexo_por_lista` |
| conversa de outra corretora / porteira / agente | **continuam ANTES do `StreamingResponse`** | `chat.py:883-1050` |
| o pré-trabalho caro saiu de antes do stream | **sim** no painel (`_preparar_o_turno` dentro de `_gerar`, `chat.py:1552`); o widget mantém a ordem antiga (grafo → visão → documento → guardrail, `chat.py:1366-1375`) | teste (a) + mutação (5) da régua |
| o provedor de IA recebe URL nossa? | **não, no caminho novo**: imagem vai como `data:image/jpeg;base64` (`chat_anexos.py:582-589`); `describe_image` recusa caminho relativo (`vision_service.py:103-112`); o áudio vai por bytes com só a extensão (`audio_service.py` `transcribe_audio_bytes`). ⚠️ o atendimento do WhatsApp continua mandando URL ASSINADA ao provedor (`webhook.py:642-652`) — fora desta SPEC, sem mudança |
| CPF/telefone/nascimento cru por PDF, Word, transcrição, descrição | **segura** · todo texto sai por `vision_service.mascarar` (fail-closed: sem máscara → aviso, nunca o cru) — PDF pelo leitor da 130-B, docx/pptx/texto/áudio/descrição de foto mascarados | `chat_anexos.py:525-650`; testes `test_a_mascara_indisponivel_e_fail_closed`, `test_audio_por_bytes…`, `test_d_imagem…descricao_mascarada` |
| … por PLANILHA | **CPF e telefone seguram; data de nascimento só com o cabeçalho certo** — P2 | sonda |
| … pelo NOME do arquivo | **CPF/telefone seguram** (`cpf 123.456.789-09.pdf → cpf <CPF>.pdf`, `Joao Silva 11987654321.jpg → Joao Silva <NUMERO>.jpg`); data no nome passa — P2 | sonda |
| o widget e o atendimento mudaram? | **não, medido no que dá para medir**: o esforço é uma `ContextVar` lida SÓ para `chat_principal` (`model_policy.py` `_com_esforco_do_pedido`), setada só dentro do `with` de `get_or_create_graph`; `hyde_no_turno(esforco=None)` = `is_hyde` de antes (`graph.py`); as leituras em paralelo de `_build_initial_state` são esperadas no MESMO lugar, e o guarda (d) compara o estado com a versão sequencial da base `76b1072` — verde. Nenhuma variável usada pelas leituras é reatribuída entre o início das tasks (`graph.py:1502`) e o último `await` (`graph.py:1819`) — conferido por grep |
| o aquecimento derruba o arranque? | **não** · task em 2º plano, cada etapa em try, `AQUECER_NO_ARRANQUE=0` desliga, cancelada no shutdown (`main.py:59-115,166-174,215-218`) |
| …ou deixa o checkpointer sem memória? | **não** · trava por event loop em `get_async_postgres_checkpointer` (quem chega no meio da abertura espera, `graph.py:60-86`); pool que não abriu zera `_checkpointer_init_attempted` (`main.py:104-108`); teste `test_o_aquecimento_e_o_1o_turno_nao_disputam_o_pool` verde |
| Presidio carregado duas vezes | **segura** · trava dupla no singleton (`presidio_service.py:131-145`) |
| a mesma mensagem 2× (client_request_id) | **P1** (medido) |
| dois turnos ao mesmo tempo (crids diferentes) | o composer não deixa (`turnoCorrendo`, `Composer.tsx:186`); em duas abas é o comportamento de antes 💭 |
| composer: foco, Enter no celular, colar, arrastar, 10/20 MB, HEIC, áudio sozinho, Tentar de novo | **segura** no que o código e o teste mostram: `autoFocus` + `focar` por `focoKey` e no fim do turno só sem toque (`Composer.tsx:116-133`); Enter no toque quebra a linha (`teclado.ts`); colar com texto + imagem → o texto vence (`Composer.tsx:226-234`); arrastar com contador (`page.tsx:1048-1073`); 10/20 MB avisados antes de subir (`useAnexos.ts`), 413 humano depois; HEIC por extensão e por `ftyp`; áudio sozinho → `envioPendente` sai quando o upload termina; "Tentar de novo" reusa o `client_request_id` e os anexos gravados (`page.tsx:66-101,963-983`). Pendência de teclado: P3 |
| a consulta periódica (A5) | **segura** · duplicação: `juntarChegadas` deduplica por `client_request_id`+papel ou por `id` (a mensagem da cotação não carrega crid — `cotacao/workflow.py`, grep vazio); para: no prazo (10 min), no nº de respostas, ao trocar/criar conversa (`mudarEspera(null)`), pausa com a aba oculta; lê conversa de outro usuário? não — `/api/conversations` filtra `session_id` + `user_id` da sessão (`app/api/conversations/route.ts:138-141`). Teste node: "cada resposta aparece UMA vez" OK |
| a barra do rodapé saiu; o ☰ chega aos 6 pilares | **sim** · `TenantBottomNav` apagado, nenhum import restante (grep); a gaveta renderiza `PILLARS` (`TenantNav.tsx:146`); botões 44 px |
| `?pergunta=`, `?session=`, `autobrokers:new-conversation` | **continuam** · inicializadores síncronos (`page.tsx:241-250,263-269`), a URL perde `pergunta` sem zerar o estado, o ouvinte do evento (`page.tsx:1040-1044`); o composer é UM só e não remonta (`page.tsx:1186-1197`) |
| avatar / voice-messages (o `/api/upload` é compartilhado) | **melhorou, sem regressão**: avatars 5 MB e jpeg/png/webp como antes; voice-messages 5 MB, mesmo conjunto (agora `audio/webm;codecs=opus` é normalizado e passa); o avatar deixa de receber `undefined` (`AvatarUpload.tsx` `urlDoAvatarEnviado`) |
| 20 MB passando pelo middleware | **coberto** · `experimental.middlewareClientMaxBodySize: '25mb'` existe no Next instalado (📊 `node -e` → 15.5.12; `config-schema.js:356`, `resolve-routes.js:111`) |

## BLOCKERS

Nenhum.

## PENDÊNCIAS

**P1 · a trava do "turno já em andamento" deixa passar o mesmo `client_request_id` duas vezes** (medido, com controle)
- 📊 `test_juiz_corrida.py` (2 POSTs iguais, `asyncio.gather`, mesmo app, `assistantMessageId` igual):
  HEAD → **6/6 rodadas com o modelo chamado 2×** (`motor: 2`, deltas `[2, 2]`, com e sem anexo).
  CONTROLE base `285cadc` (o `chat.py` da base compilado num módulo à parte, o mesmo arreio) → **3/3 rodadas com o
  modelo 1×**, a 2ª resposta = `['turn.accepted','notice','turn.completed']` (`turn_in_progress`).
- Causa: `chat.py:874-885` confere `TURNOS_ATIVOS` e só registra a task em `chat.py:1731`; entre os dois há `await`s
  que cedem o laço — esta SPEC pôs `pode_consumir` e `get_agent_by_id` em `asyncio.to_thread` (`chat.py:970,1020`).
- Por que PENDÊNCIA e não BLOCKER: 💭 em produção a janela JÁ existia na base (o `conv_check` e o `companies` são
  rede de verdade e cedem o laço) e era MAIOR — a base registrava a task depois do grafo, da visão, do documento
  (até 60 s) e do guardrail. Esta SPEC encurtou a janela; o dublê só a deixava invisível na base porque os `await` do
  banco dublado não cedem. A página tem a trava `enviandoRef`; o BFF reaproveita a pergunta (23505) e repassa ao backend.
  Efeito quando acontece: duas chamadas ao modelo e dois débitos no mesmo turno; uma linha de resposta (upsert pelo id).
- Conserto de 2 linhas (recomendado no conserto único, já que o ataque estava na lista): reservar a chave em
  `TURNOS_ATIVOS` logo depois da conferência, sem `await` no meio (um marcador que `em_voo.done()` trate como vivo), e
  soltá-la em todo `return` antes do `create_task`. Não existe teste de `turn_in_progress` no repositório (📊 `grep -rln
  turn_in_progress backend/tests` → vazio): o guarda novo tem de ficar vermelho no HEAD de hoje (a sonda já fica).

**P2 · data de nascimento crua passa quando nada a rotula**
- 📊 `sonda_mascara.py`: CSV com coluna **"Data"** → `01/02/1980`, `15/03/1975`, `1975-03-15`, `2/3/1980` chegam crus;
  XLSX com **"Nascto"** → `[DATA]` (o cabeçalho é reconhecido, `chat_anexos.py:280`). Texto livre "nasci em
  01/02/1980" → cru (a máscara da 130-B só pega `Nascimento <data>`). Nome de arquivo `nasc 01-02-1980 apolice.pdf` → cru.
- CPF e telefone seguram em todas as formas testadas: `12345678909`, `01234567890`, `1234567890` (o zero perdido pelo
  Excel), `987654321`, `123.456.789-09`, `(11) 98765-4321`, `+55 11 98765-4321` → `[CPF]`/`[NUMERO]`/`[TELEFONE]`.
- Pendência e não BLOCKER: "Data" é ambígua (vencimento, emissão, sinistro); a regra "nascimento só rotulado" é a da
  130-B, a mesma do PDF e do WhatsApp — mudar é decisão de máscara da plataforma, não desta SPEC. O contrato
  (§2, §6) promete "nenhum CPF cru", e isso se cumpre. Sugestão: ampliar `_COLUNAS_SENSIVEIS` com `\bdn\b`,
  `aniversario`, `idade`, e decidir na 130-B se data solta perto de nome de pessoa vira `[DATA]`.
- Cosmético: `rg 1234567890.pdf` vira `rg <RG>pdf` (a máscara come o ponto da extensão).

**P3 · a barra de espaço deixa de acionar botão no notebook**
- `Composer.tsx:145-158` leva o foco à caixa em qualquer `keydown` de 1 caractere fora de campo/diálogo; `' '.length === 1`
  (`teclado.ts` `teclaQueEscreve`). Com o foco em "Copiar", "Tentar de novo", "+", "Carregar anteriores" ou num botão
  da barra lateral, o espaço vai para a caixa e o botão não aciona. Enter continua funcionando. Quem navega por
  teclado sente; mouse e toque não. Conserto: excluir `' '` quando o ativo é `BUTTON`/`A`/`[role=button]`.

**P4 · o envio recusado apaga o que o corretor escreveu**
- `Composer.tsx:163-176` limpa texto e anexos ANTES de saber se o envio saiu; `page.tsx:897-905` (agentes ainda
  carregando, nenhum agente) e um 403/400 do BFF (`page.tsx:779-784`) terminam com toast e a caixa vazia. 💭 A
  caixa antiga fazia igual. Conserto: `onSendMessage` devolver se aceitou, e só então limpar.

**P5 · leituras em paralelo sobre o MESMO cliente Supabase síncrono** (por medir)
- `_build_initial_state` agora roda até 4 `to_thread` simultâneos sobre o mesmo cliente (`graph.py` `_ler_as_ferramentas_http`,
  `_ler_as_delegacoes`, `_ler_o_nome_da_corretora`, `_ler_a_marca`) — e isto vale para o atendimento do WhatsApp
  também. 💭 O pool do httpx é protegido por trava e o `smart_search` já rodava em thread; não vi defeito, mas o guarda
  (d) usa dublê e não prova o cliente real. Medir: um turno real de atendimento depois do deploy com o log sem
  `RuntimeError`/`ProtocolError`; se aparecer, voltar as quatro leituras para sequenciais (são baratas).

Observações sem classe (registro, não pendência): até 10 × 20 MB baixados na memória do backend por turno (💭 200 MB
de pico); o texto dos anexos (até 60 mil caracteres) entra também na consulta da memória e do RAG
(`current_query=user_message`) — já era assim com `fileUrl`, só cresceu.

## MAIOR LACUNA

Nada do que esta SPEC promete de LATÊNCIA foi medido contra o produto: o ELO do card ("o 1º texto chega mais cedo
PORQUE o pré-trabalho saiu do caminho") só existe nos dublês (1º byte < 0,5 s com o Storage dormindo 1,5–2 s). A
medição em produção (`lat.py` antes × depois, `fases_ms`) depende do deploy e está na caixa do Founder. Junto dela
ficam sem prova real: o envio de 10–20 MB pelo proxy do EasyPanel (o limite do Next está coberto; o do proxy, não), a
lista de 25 tipos dos buckets em produção (feita pelo gerente; não consultei o banco) e o HEIC real de um iPhone.

## PRÓXIMA AÇÃO

Conserto único: P1 (com guarda que fica vermelho hoje) e, se couber, P3 e P4 (de poucas linhas cada). P2 vai para
`PENDENCIAS.md` com dono "máscara da plataforma (130-B)". P5 vira item do canário. Confirmação (§6.1) só se o conserto
de P1 entrar.

## CONFIANÇA

**Alta** no isolamento, na máscara de CPF/telefone, no guardrail dentro do stream, no esforço e no widget: cada um
reproduzido pelo motor real, com saída citada. **Média** no comportamento visual (foco, teclado do celular, tela que
não dança): li o código e os 109 OKs do teste node, mas não rodei navegador nem vi captura — isso é do juiz de design.
**Por medir**: latência em produção, proxy de 20 MB, buckets em produção, cliente Supabase sob threads (P5).
Não rodei `tsc` nem `next build`/`next start` (proibidos ao juiz nesta máquina; são gates do gerente).

## NOTA

**88 / 100** — o trabalho cumpre o contrato e as travas de segurança aguentam ataque; perde pontos pela corrida do
turno duplicado sem guarda (P1), pela data de nascimento que a régua do fio diz pegar e só pega com rótulo (P2) e
pelos dois atritos de teclado/caixa (P3, P4).

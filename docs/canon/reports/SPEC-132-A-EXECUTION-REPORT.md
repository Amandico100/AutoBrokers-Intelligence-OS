# Relatório de execução — SPEC-132-A: o chat principal (a caixa que cabe no celular, lê o que se manda e responde rápido)

**SPEC:** `docs/canon/specs/SPEC-132-A-o-chat-principal.md` · 1ª de três no mesmo chat (132-A → 132-B → 132-C, D-132B-00)
**Branch:** `spec/132-o-chat-e-a-cotacao` · **base** `285cadc` (= `origin/main` no preflight: 0 atrás) · **último commit** `ce32e89` (push: §7)
**Gerente:** Opus 5.5 · protocolo AAA v13.2 · nível CRÍTICO · todos os subagentes declararam `claude-opus-5-5` (telemetria §11)
**Estado final:** CONCLUÍDA COM RESSALVAS (o ELO de latência só se mede depois do Implantar; juiz de design não rodou)

## 0.0 EXECUTION CARD
```
OUTCOME ........ o corretor abre o AutoBrokers e a caixa já está pronta ("Peça ao AutoBrokers"), pequena no celular, com um "+"
                 (Câmera · Fotos · Arquivos · Esforço · Pesquisa na web); manda fotos, PDF, planilha, Word e áudio e o AutoBrokers LÊ;
                 escolhe Rápido · Equilibrado · Máximo; o 1º texto chega mais cedo; copia qualquer resposta; a tela não dança;
                 a barra de atalhos do rodapé sai
RISCO .......... 6 (corretora 2 · reversível 2 · todo uso 2)
SUPERFÍCIE ..... 2 (vários comportamentos em lugares listados: composer, anexos, áudio, esforço, latência, layout)
PISO APLICADO .. CRÍTICO: app/ + layout do dashboard · o anexo atravessa company_id · PII do segurado (máscara 130-B obrigatória)
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team · confirmação (juiz de DESIGN previsto: NÃO rodou, §10)
O FIO .......... composer → POST /api/upload {bucket,path,…} → POST /api/chat/stream {attachments[],options} → BFF (sessão, conversa e
                 prefixo DESTA corretora) → backend StreamingResponse imediato → chat_anexos.preparar (bytes, máscara) → chat_principal
UNIDADES ....... 5 fatias (A1 tela · A2 anexos · A3 turno rápido · A4 costura · A5 a resposta que chega depois) + 1 conserto
COESÃO ......... o upload, o BFF e o leitor por bytes juntos (A2: um contrato só); o esforço e o stream imediato juntos (A3)
PARALELISMO REAL A1 ‖ A2 ‖ A3 (arquivos disjuntos) ‖ as fatias da 132-B/C na mesma árvore → A4 costura → A5
TIME ........... 5 builders · juiz ‖ red team · conserto único · confirmação · verificador §9.1 · bateria · atualizador
REFERÊNCIA ..... interna: DS-001 §5.1/§5.2/§8.2/§10, laudo DESIGN-DO-PADRAO-DE-APLICATIVO (44 px, AA); externa: SPEC §8 (5 URLs)
GATES .......... fio · tsc · rotas montam · next build + next start + /api/chat/stream · 6 mutações · 2 corretoras · bateria
O ELO .......... "o 1º texto chega mais cedo PORQUE o pré-trabalho saiu do caminho" → lat.py em PRODUÇÃO antes × depois
                 (fases_ms no turno) — o ANTES está medido (§2.1 B1); o DEPOIS espera o Implantar (T-173)
FAIXA DE RELÓGIO declarada 💭 6–9 h · real 📊 ≈ 7 h 30 para as TRÊS SPECs juntas (14/10, 02:20 → ~09:50 de Brasília, telemetria
                 §11; a bateria ainda roda) — o next build de ~34 min e a trava de um processo pesado por vez foram o gargalo
```
① painel de lentes: não rodou (a conta do §3 pediu juiz ‖ red team; o juiz de design previsto ficou de fora — §10). ② auditoria
externa: juiz ‖ red team frescos e cegos + confirmação nova. ③ pendência por valor marginal: P2 do juiz (data sem rótulo — é regra da
130-B), P3 da confirmação (teto de áudio só com duração no cabeçalho).

## 0.1 O protocolo — contas, laço, rebaixamentos, drenagem
| unidade | ALC | REV | FREQ | RISCO | SUP | piso | time |
|---|:---:|:---:|:---:|:---:|:---:|---|---|
| A1 a tela | 2 | 1 | 2 | 5 | 2 | app/ | builder |
| A2 os anexos | 2 | 2 | 2 | 6 | 2 | company_id + PII | builder |
| A3 o turno rápido | 2 | 2 | 2 | 6 | 2 | toca o atendimento (Presidio, leituras) | builder |
| A4/A5 costura | 2 | 2 | 2 | 6 | 2 | app/ | builder |

**O laço:** 1 volta (juiz ‖ red team → conserto único → confirmação). Saída: **só pendências** (confirmação 86, 4/4 fechados).
**Rebaixamentos pelo gerente:** nenhum. Ao contrário, **promoveu** dois achados a blocker do conserto: P1 do juiz (o mesmo
`client_request_id` chamava o modelo 2× — 📊 6/6 rodadas 2× no HEAD contra 3/3 1× na base) e a pendência 1 do red team (o aquecimento
derrubava o app com `SystemExit`).
**Pendências que a SPEC tocou:** nenhuma da lista antiga; as novas são P-132A-01…14 (§10.2).

## 1. Resumo executivo (FATO)
- **A caixa nova** (`components/chat/composer/*`, D-132A-01): uma linha de 44 px, campo de 16 px (sem zoom do iOS), "+" com Câmera ·
  Fotos · Arquivos · Esforço · Pesquisa na web, microfone ↔ ENVIAR ↔ PARAR, fichas de anexo com progresso e motivo do erro, colar e
  arrastar, foco ao abrir/trocar/terminar (notebook). Caixa no meio na conversa vazia do notebook, sempre embaixo no celular (D-132A-07).
  O `InputArea` e o `animated-ai-chat` saíram; a barra de 6 atalhos do rodapé saiu do celular (D-132A-02); os atalhos da tela vazia saíram
  (D-132A-03). `viewport` com `interactive-widget=resizes-content` e o `100vh` do body fora (a tela parou de dançar).
- **Os anexos são lidos** (D-132A-05): o `/api/upload` devolve `{bucket, path, nome, mime, bytes}` (o `publicUrl` que o cliente lia e
  não existia — 📊 `useImageUpload.ts:104` — sumiu); o BFF recusa com 403 path fora de `<company_id>/`; o backend baixa os BYTES pelo
  service role e lê foto (visão), PDF (leitor 130-B), xlsx/xls/csv (cabeçalho + amostra + totais), docx/pptx/txt/md e áudio (transcrição),
  **tudo mascarado** antes do modelo. Até 10 arquivos de 20 MB, HEIC incluído.
- **O turno rápido:** o `StreamingResponse` sai na hora (📊 1º byte 0,004 s com 2 s de anexo dublê; 0,392 s no fio com o Storage
  dormindo 1,5–2 s); o pré-trabalho (anexos, guardrail) foi para dentro do stream com linhas de atividade ("Lendo apolice.pdf…"); o
  contexto em paralelo (📊 1,22 → 0,30 s no dublê); aquecimento do Presidio/busca/pool no arranque; as fases medidas em `fases_ms`.
  Esforço Rápido · Equilibrado · Máximo = `low/medium/high` no MESMO modelo do papel `chat_principal` (D-132A-04), lembrado por aparelho
  (D-132A-08). O áudio do chat saiu do `/api/n8n` e vai pelo mesmo stream (D-132A-06).
- **Copiar** em toda resposta e **Tentar de novo** na última. **A5:** a resposta que chega depois (a cotação da 132-B) aparece sem
  recarregar — a tela consulta a conversa a cada 6 s, até 10 min, enquanto há cotação calculando (D-132B-09: `messages` não está no
  Realtime, 📊 0 linhas na publicação).

## 2. Escopo (FATO — commits)
`76b1072` SPEC · A2 `e6d79e5`…`b918e66` · A3 `16cb5e9`…`505a938` · A1 `9147341`…`9841b9c` · A4 `d12add3`…`2c17fb4` · A5 `d389f37`,
`fc700fd` · conserto `96a3c44`…`48663df` · `bdfdfd0` o modelo pt do spaCy na imagem · `ce32e89` (as confirmações da B/C, sem arquivo da A).
📊 `git log 285cadc..HEAD --grep=spec-132-A` → 58 commits, 54 arquivos, +9.606 / −1.840 (por commit; `graph.py`/`main.py` são
compartilhados com a 132-B). As três SPECs juntas: 📊 161 commits, 133 arquivos, +24.150 / −1.931.
**Entregas NÃO executadas:** o juiz de design com capturas (celular 390 e notebook 1440, claro e escuro) — previsto na régua §6, não
rodou; a medição de latência em produção depois do deploy (é o ELO; depende do Implantar, T-173).

## 2.1 BLOCO 0 (📊 14/10, produção, antes de codar)
1ª mensagem de conversa nova: cabeçalho **4,4 s** · 1º delta **10,2 s** · total 16,0 s; 2ª mensagem 1,0 · 7,1 · 15,7 s; 1ª de outra
conversa 1,0 · 5,5 · 8,0 s (`scratchpad/s132/lat.py`, direto no backend). `llm_papeis.chat_principal` = `openai/gpt-6.1-sol` medium,
reserva `claude-opus-5-5`. Presidio nesta máquina: import do spaCy 39,6 s + `presidio_service` 156,3 s + init 37,7 s + 1ª análise 14,1 s;
a produção baixava o `pt_core_news_md` a cada arranque (o Dockerfile só tinha o `en`). Buckets: `chat-media` 5 MB só jpeg/png/webp/gif,
`chat-docs` 15 MB sem xls/webm/wav.

## 4. Migrations e mudanças de infraestrutura
**Nenhuma migration** (SPEC §3). Duas mudanças fora do código, pelo gerente (CHANGE-ADDENDA 14/10):
- **Buckets** (API do Storage, D-132-G2): `chat-media` e `chat-docs` → 20 MB e 25 tipos (HEIC, xls, áudios). VERIFY: releitura da
  configuração dos dois buckets. ROLLBACK: `scratchpad/s132/buckets_rollback.json` (a configuração anterior, sem segredo).
- **Dockerfile** (`bdfdfd0`, D-132-G3): `pt_core_news_md` instalado na imagem → o `smith-api` precisa RECONSTRUIR a imagem no Implantar.

## 5. Testes e gates (📊 saídas reais)
- Builders: A1 `o-chat-novo.test.mjs` 8 mutações · A2 46 ok / 21 passed · A3 19 passed · A4 fio 5 passed (1º byte 0,392 s, anexos
  2,804 s; 5 defeitos de costura achados e consertados) · A5 109 OK.
- Juiz (HEAD `618ba14`): `test_spec132a_o_fio` **5 passed** · `_turno_rapido` **19 passed** · `_anexos` **21 passed** ·
  `o-chat-novo.test.mjs` **109 OK** · `o-upload-do-chat.test.mjs` **48 ok** · `test:chat-shell` **75 OK** · `test:rotas-montam` **4 OK**.
- Red team: `_anexos` + `_o_fio` **26 passed**, `_turno_rapido` **19 passed** — verdes, e nenhum cobria os dois blockers dele.
- Confirmação (sondas próprias): CPF começando nas posições 60/66/70/72/75 da célula → `[CPF]`, **0** sequências de dígitos (controle:
  o corte antigo deixava 9 dígitos-base); 60×30 células longas (670 KB) → 0,78 s; JPEG com EXIF orientação 6 → 1536×2048 (rotação certa).
  Conserto: CSV 154 → 0,1 MB de pico, xlsx 407 → 5,4 MB; mesmo pedido 2× → 1× em 6/6; 0 vazamento em 42 casos.
- **Mutações da régua** (vermelhas uma vez, restauradas por cópia): `publicUrl` de volta · path de outra corretora no BFF · CPF cru de
  xlsx · `esforco='turbo'` · pré-trabalho antes do `StreamingResponse` · a barra do rodapé de volta. **Isolamento:** o path da outra
  corretora → 403 (no BFF, não na RLS); o red team tentou 17 formas (`../`, `%2e%2e`, unicode, prefixo parecido, NUL…) → 403 em todas.

### §9.1 (verificador, HEAD `bdfdfd0`; o `ce32e89` só toca Python)
📊 `tsc --noEmit` 0 · rotas montam · `next build` OK (331 rotas, 136 páginas, ~34 min) · `next start` Ready 25,8 s ·
`POST /api/chat/stream` 401 · `POST /api/upload` 401 · `GET /api/cotacoes` 401 · `/dashboard` 307 ·
`/dashboard/auxiliares/cotacao?aba=cotacoes` 307 (o `?aba` se perde no login — P-132A-08) · `/api/versao` 200 commit `bdfdfd0` ·
`/r/` inválido 404 limpo · 0 erro no log.

## 6. Canário e rollout
Sem canário real nesta SPEC: a meta 💭 "1º delta ≤ 3 s no Rápido aquecido" só se mede no servidor novo. Depois do Implantar dos 4
serviços (T-166), o gerente roda o mesmo `lat.py` com Equilibrado e com Rápido (T-173) e lê `fases_ms` no turno.

## 7. Gate da SPEC
juiz **88** (0 blocker, 5 pendências) ‖ red team **62 QUEBREI** (2 blockers: a célula cortada ANTES da máscara deixava 9–10 dígitos do
CPF; CSV/xlsx/PNG "bomba" de 1 MB derrubava o backend de todas as corretoras) + 2 promovidos pelo gerente → **conserto único**
(máscara antes do corte; leitura em fluxo com tetos de colunas, células e pixels; poço próprio de 3 threads; reserva do turno sem
`await`; `SystemExit` no aquecimento vira aviso; SSRF do `fileUrl` amarrado ao host do Storage; o texto volta à caixa quando o envio é
recusado; a barra de espaço volta a acionar botão; teto de 15 min de áudio) → **confirmação 86** (4/4 fechados, nenhum defeito novo).
Push: na resposta ao Founder (o gerente empurra depois da bateria).

## 8. Mudanças além do texto da SPEC (CHANGE-ADDENDA 14/10)
ESSENCIAL: os buckets de 20 MB / 25 tipos (sem eles o anexo maior que 5 MB e o HEIC eram recusados pelo Storage) · o Dockerfile com o
modelo pt (o aquecimento baixava o modelo a cada arranque e, com a rede falhando, derrubava o processo). VALIOSA: `messages` fora do Realtime → a
consulta periódica (A5, D-132B-09).

## 9. Decisões
SPEC §7: **D-132A-01** refazer o composer (90) · **D-132A-02** a barra do rodapé sai (82) · **D-132A-03** a tela vazia sem atalhos (80) ·
**D-132A-04** esforço no mesmo modelo (85) · **D-132A-05** anexo por bytes, nunca URL nossa ao provedor (92) · **D-132A-06** áudio pelo
mesmo stream (88) · **D-132A-07** caixa no meio no notebook (85) · **D-132A-08** esforço por aparelho (80). Do gerente: **D-132-G2**
buckets 20 MB/25 tipos · **D-132-G3** Dockerfile com o pt · **D-132B-09** polling de 6 s (85 × Realtime 60).

## 10. Riscos remanescentes (INFERÊNCIA, com o que falta medir)
- **O ELO não está provado**: a latência só foi medida em dublê. 💭 O ganho esperado (stream imediato, aquecimento, paralelo) pode ser
  menor que a SPEC promete se o 1º delta for dominado pelo provedor do modelo (📊 7,1 s na 2ª mensagem, já aquecida).
- **Juiz de design não rodou**: a tela nova não foi vista em captura (celular/notebook, claro/escuro). O juiz leu o código e os 109 OKs;
  foco, teclado do celular e "a tela não dança" estão com confiança MÉDIA.
- **Leituras paralelas no cliente Supabase síncrono** (P5 do juiz) valem também para o atendimento do WhatsApp — medir no canário.
- O proxy do EasyPanel com 10–20 MB e um HEIC real de iPhone não foram provados.

### 10.1 📋 CAIXA DO FOUNDER (as tarefas da 132 inteira em `TAREFAS-DO-FOUNDER.md`)
- **T-166** Implantar os 4 serviços JUNTOS (`smith-api` → `smith-worker` → `portal-worker` → `smith-web`); o `smith-api` reconstrói a imagem.
- **T-168** testar o chat: foto, PDF, planilha, áudio, Rápido/Equilibrado/Máximo, copiar, celular.
- **T-173** pedir no chat "meça a latência" depois do Implantar (o comando é do gerente).

### 10.2 Pendências novas → `PENDENCIAS.md` P-132A-01…14
transcrição gravada antes do guardrail · CPF falado por extenso · data de nascimento sem rótulo · leituras paralelas no cliente
síncrono · Stop antes do turno deixa `PARADAS` · `fileUrl` só no host do Storage · teto de 15 min só com duração no cabeçalho ·
`?aba=` perdido no login · a medição em produção · voz em tempo real · regenerar com outro esforço · a foto chega ao modelo principal
como descrição · conectores por pedido · o juiz de design que não rodou.

## 11. Impacto para o corretor
Abre o chat no celular e a caixa cabe na tela, sem a barra de atalhos por cima; fotografa o documento do cliente, anexa a apólice em PDF
e a planilha da frota, grava um áudio — e o AutoBrokers lê tudo (com CPF e telefone mascarados) e começa a responder antes de terminar
de ler. Escolhe "Rápido" quando quer a resposta na hora e copia a resposta com um toque.

## 12. Declaração de integridade
Nenhum motor paralelo foi criado (CLAUDE.md §5): o turno continua sendo o `chat_stream`; o leitor de PDF é o da 130-B; a transcrição é o
papel `transcricao`; o esforço é override do MESMO papel. Nenhuma migration movida ou reaplicada. Nenhum segredo neste relatório.
Isolamento provado com duas corretoras (BFF e backend). O protocolo SSE só GANHOU eventos; o widget (`modo == "widget"`) não lê anexo
por lista e manteve a ordem antiga.

## 13. ROLLBACK
Código: `git revert` dos commits do §2 (o composer antigo volta; o BFF volta a repassar `imageUrl/fileUrl`, que ele continua aceitando).
Buckets: o JSON de rollback. Dockerfile: reverter `bdfdfd0` (o Presidio volta a baixar o pt no arranque, com o `SystemExit` já contido).

## 📊 A BATERIA — quantas vezes ela rodou nesta SPEC
PENDENTE — o gerente preenche (a rodada inteira das três SPECs, em `scratchpad/bat132`, ainda roda).

## §11 A TELEMETRIA (`python backend/scripts/medir_execucao_claude_code.py --sessao atual`, rodado da raiz, 14/10 ~09:49 BRT, horários em UTC)
```
EXECUTOR (a sessão inteira, 132-A+B+C)     14/10 05:20  445 min  turnos 210  pico 634k  US$ 54.48  opus-5-5
  4 investigadores do BLOCO 0 (compartilhados)          13–20 min           US$ 5.43 + 4.53 + 3.36 + 3.48
  Builder A1 a tela do chat                14/10 05:49  140 min  turnos 115  pico 382k  US$ 17.66  opus-5-5
  Builder A2 os anexos                     14/10 05:50  100 min  turnos  75  pico 268k  US$  8.50  opus-5-5
  Builder A3 o turno rápido                14/10 05:50  166 min  turnos 163  pico 419k  US$ 26.00  opus-5-5
  Builder A4 costura do chat               14/10 07:55   94 min  turnos 111  pico 345k  US$ 16.11  opus-5-5
  Builder A5 resposta sem Realtime         14/10 09:31   35 min  turnos  46  pico 203k  US$  4.68  opus-5-5
  Juiz da SPEC-132-A                       14/10 10:09   29 min  turnos  87  pico 299k  US$ 10.26  opus-5-5
  Red team da SPEC-132-A                   14/10 10:09   29 min  turnos  61  pico 226k  US$  6.53  opus-5-5
  Conserto único da 132-A                  14/10 10:39   81 min  turnos 112  pico 370k  US$ 16.26  opus-5-5
  Confirmação 132-A                        14/10 11:37   55 min  turnos  40  pico 143k  US$  2.88  opus-5-5
  Verificador build e next start (as 3)    14/10 11:37   45 min  turnos  21  pico  67k  US$  0.95  opus-5-5
TOTAL da sessão: 32 agentes além do executor · turnos 2744 · ctx 649,4 M · US$ 386,25 (+ executor 54,48)
```
📊 Agentes da 132-A: US$ 108,88 (API-equivalente; o plano não cobra em dólar). Todos `opus-5-5`. Achados por mecanismo: o fio da A4
(5 defeitos de costura, EXCLUSIVOS) · o juiz (a corrida do turno duplicado, a data sem rótulo, a barra de espaço, o texto apagado) · o
red team (o corte antes da máscara e a "bomba" de memória, EXCLUSIVOS; o `SystemExit`; o SSRF do `fileUrl`; o áudio sem teto).
**API do produto (verba):** 📊 os 3 turnos de medição no `chat_principal` custaram US$ 0,0568 (as três SPECs juntas, livro-caixa §3).

**Nota da execução: 84/100** (proposta pelo atualizador; o gerente fecha depois da bateria) — confirmação 86 e §9.1 completo; desconta
o juiz de design que não rodou e o ELO de latência sem prova em produção.

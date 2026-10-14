# SPEC-132-A — O chat principal: a caixa que cabe no celular, lê o que se manda e responde rápido

> **v1.0 · 14/10/2026** · gerente Opus 5.5 · branch `spec/132-A-o-chat` (da `origin/main` `285cadc`) · rito AAA v13.2 · **CRÍTICO**.
> Origem: pedido do Founder de 14/10 (a caixa "muito abaixo" de ChatGPT/Claude; anexo que dá erro; 1ª resposta lenta; esforço;
> copiar; cursor; tela que dança; atalhos do rodapé) · as 4 frentes de investigação do BLOCO 0 (§2.1). 📊 medido · 💭 ilustrativo.
> Primeira de três SPECs no mesmo chat: **132-A o chat** → **132-B a Cotação Rápida** → **132-C o WhatsApp do corretor como atalho**.

## 0. EXECUTION CARD
```
OUTCOME ........ o corretor abre o AutoBrokers e a caixa já está pronta para escrever ("Peça ao AutoBrokers"), pequena no celular,
                 com um "+" que abre Câmera · Fotos · Arquivos · Esforço · Pesquisa na web; manda várias fotos, PDF, planilha,
                 Word e áudio e o AutoBrokers LÊ; escolhe Rápido · Equilibrado · Máximo; o 1º texto chega mais cedo; copia
                 qualquer resposta com um toque; a tela não dança; o menu de atalhos do rodapé sai.
RISCO .......... 6 · corretora 2 (a tela de trabalho diária) · reversível 2 (arquivos guardados, mensagens) · TODO uso 2
SUPERFÍCIE ..... 2 · vários comportamentos (composer, anexos, áudio, esforço, latência, layout) em lugares listados (§5)
PISO ........... CRÍTICO: app/ + layout do dashboard · o caminho do anexo atravessa company_id (o arquivo é da corretora) · PII
                 (documento do segurado) — a máscara da 130-B continua obrigatória
NÍVEL .......... CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · juiz de DESIGN (capturas celular e notebook)
O FIO .......... §2 · teste `backend/tests/test_spec132a_o_fio.py` (backend) + `scripts/o-chat-novo.test.mjs` (tela) = 1ª entrega
PARALELISMO .... A1 ‖ A2 ‖ A3 (arquivos disjuntos, §5) → A4 costura (+ capturas)
GATES .......... fio · tsc · rotas montam · next build + next start + /api/chat/stream · mutações · 2 corretoras · design ≥ 90 · bateria
REFERÊNCIA ..... interna: DS-001 §5.1/§5.2/§8.2/§10 · o laudo DESIGN-DO-PADRAO-DE-APLICATIVO (44 px, contraste AA); externa: §8
O ELO .......... "o 1º texto chega mais cedo PORQUE o pré-trabalho saiu do caminho" → medir em PRODUÇÃO o mesmo roteiro do §2.1 B1
                 antes × depois (fases_ms no payload do turno), nunca deduzir
FAIXA .......... 💭 6–9 h (next build 80–115 min nesta máquina) · fatia ≤ 1h15
```

## 1. O contrato
**Muda:** o composer (substitui `components/InputArea/*` + `components/ui/animated-ai-chat.tsx` por `components/chat/composer/*`),
a página do chat (`app/dashboard/chat/page.tsx`: um composer só, que não remonta), a bolha (copiar · tentar de novo na última ·
anexos visíveis), a tela vazia (saudação + caixa; os atalhos "Ver atendimentos/Novo auxiliar" saem), o casco do dashboard no celular
(sem a barra de atalhos do rodapé; o menu ☰ do topo leva a tudo), o `viewport` do app, o upload (contrato novo, vários arquivos,
20 MB, HEIC), o turno no backend (lista de anexos lida por BYTES, não por URL; esforço por pedido; pré-trabalho dentro do stream
com linhas de atividade; aquecimento no arranque; fases medidas).
**Não pode mudar:** o protocolo SSE tipado (`lib/chat/protocolo.ts` só GANHA eventos) · o widget (`modo == "widget"`, legado) ·
a máscara de CPF/PII (130-B) antes de qualquer modelo · o leitor da ficha única (130-B) · `?pergunta=`, `?session=` e o evento
`autobrokers:new-conversation` · os buckets `avatars`/`voice-messages` · o atendimento ao segurado (WhatsApp) — o aquecimento e o
paralelismo não mudam a ordem das regras dele · nenhum motor paralelo (CLAUDE.md §5): o turno continua sendo `chat_stream`.

## 2. O FIO
```
composer (Enter | enviar) → anexos já subidos: POST /api/upload (cada arquivo, em paralelo, com progresso) → {bucket, path, nome,
mime, bytes} → POST /api/chat/stream {chatInput, attachments[], options:{web_search, esforco}} → BFF: sessão + a conversa É desta
corretora + cada path começa com o prefixo DESTA corretora (senão 403) → backend /chat/stream → StreamingResponse IMEDIATO →
_gerar: evento `activity` "Lendo 2 arquivos…" → chat_anexos.preparar(company_id, attachments) baixa os BYTES do Storage (service
role) → imagem: data URL ao papel `visao` · PDF: leitor 130-B (mascarado) · xlsx/xls/csv: leitor tabular (cabeçalho + amostra +
totais, mascarado) · docx/pptx/txt/md: docling/texto (mascarado) · áudio: papel `transcricao` → bloco do turno → modelo do papel
`chat_principal` com o esforço do pedido → deltas → bolha com [Copiar] (+ [Tentar de novo] na última)
```

## 2.1 BLOCO 0 (medido em 14/10/2026)
| # | premissa | estado | o que muda |
|---|---|---|---|
| B1 | a 1ª resposta é lenta | 📊 produção, ensaio, direto no backend (`scratchpad/s132/lat.py`): 1ª msg de conversa nova cabeçalho **4,4 s** · 1º delta **10,2 s**; 2ª msg 1,0 s · 7,1 s; 1ª msg de outra conversa 1,0 s · 5,5 s | aquecimento (−3 s no processo frio) + stream imediato + pré-trabalho em paralelo + esforço Rápido |
| B2 | o modelo do chat | 📊 `llm_papeis.chat_principal` = `openai/gpt-6.1-sol` esforço `medium`, reserva `claude-opus-5-5` | Rápido = esforço `low` · Equilibrado = `medium` (hoje) · Máximo = `high` — o MESMO papel, override por pedido |
| B3 | anexo "dá erro" | 📊 `useImageUpload.ts:104` lê `data.publicUrl`; `app/api/upload/route.ts:162-176` não devolve esse campo (grep: só no comentário `:6`) → anexo some sem aviso | contrato novo `{bucket, path…}` + teste de contrato |
| B4 | o backend não alcança o arquivo | 📊 `url` = `/api/storage/...` relativo e com sessão (`lib/storage/resolver.ts:130-136`); `vision_service.py:125` passa a URL ao provedor; `:257` faz `httpx.get` | o backend baixa os BYTES pelo service role, com o prefixo da corretora conferido |
| B5 | formatos | 📊 `accept` = image/*,pdf,docx,pptx,xlsx,txt,csv,md; 5 MB; sem HEIC; sem áudio por arquivo; sem `.xls` | + HEIC/HEIF, .xls, áudio (m4a/mp3/ogg/opus/wav/webm), 20 MB, até 10 arquivos |
| B6 | pré-trabalho antes do stream | 📊 `chat.py:590→1378`: visão, documento (até 60 s), guardrail (Presidio carrega spaCy pt+en na 1ª vez) antes do `StreamingResponse` | tudo isso vai para dentro de `_gerar`, com `activity` |
| B7 | aquecimento | 📊 `main.py:54-137` só pré-carrega preços | aquecer Presidio, SearchService e o pool do checkpointer em 2º plano no arranque |
| B8 | esforço por pedido | 📊 `ChatRequest.options: Dict[str,bool]` (`chat.py:89`); override só da bancada (`model_policy.py:275-280`) | `options.esforco` ∈ {rapido, equilibrado, maximo}; nada fora disso passa |
| B9 | a tela dança | 📊 `app/layout.tsx` sem `viewport`; `body{min-height:100vh}` (`globals.css:129`) contra `h-[100dvh]` do casco; textarea 14 px (zoom do iOS) | `viewport` com `interactiveWidget: 'resizes-content'`, sem o 100vh do body, fonte 16 px no campo |
| B10 | copiar / cursor | 📊 0 "Copiar"; 0 `autoFocus` no composer e na página | copiar em toda resposta; foco ao abrir, ao trocar de conversa e depois de cada resposta (notebook) |

## 3. Dados
Nenhuma migration. O arquivo continua no Supabase Storage (`chat-media`/`chat-docs`) no prefixo `<company_id>/…` que a rota de
upload já usa. Nada novo em tabela: os anexos do turno vão em `messages.payload.attachments` (lista de `{nome, mime, bytes, path}`,
nunca o conteúdo) e as fases em `messages.payload.turn.fases_ms`.

## 4. O desenho (o visual exato)
- **Composer (celular):** uma linha de 44 px de altura mínima — [+] à esquerda · campo (16 px, cresce até 💭 6 linhas e depois rola)
  · à direita o microfone quando vazio, ENVIAR quando há texto ou anexo, PARAR enquanto responde. Cantos 24 px, borda sutil,
  sem brilho que segue o mouse. Margem 12 px laterais, `pb` = `env(safe-area-inset-bottom)`. Os anexos aparecem como fichas acima
  do campo (miniatura na foto; ícone + nome + tamanho no documento; barra de progresso; ✕ para tirar; erro em vermelho com o motivo).
- **Composer (notebook):** o mesmo, mais largo (máx. 💭 760 px, centrado). Na conversa vazia a caixa fica no MEIO da tela, logo
  abaixo da saudação ("Olá, {primeiro nome}" + uma linha); depois da 1ª mensagem desce para o rodapé SEM remontar (o texto e o
  foco não se perdem). No celular a caixa fica sempre embaixo.
- **O "+"** abre um painel (celular: folha de baixo, como o "Adicionar à sessão"; notebook: menu suspenso): Câmera (só celular,
  `capture`) · Fotos · Arquivos · **Esforço** (Rápido "responde na hora" · Equilibrado "o padrão" · Máximo "pensa mais, demora mais")
  · **Pesquisa na web** (interruptor, só quando a corretora permite — a regra de hoje) · Aplicativos (link). O esforço escolhido
  aparece como pílula discreta ao lado do "+" quando ≠ Equilibrado e fica salvo no aparelho (localStorage, com try/catch).
- **Áudio:** toque no microfone → grava (ondas + cronômetro + ✕ cancelar + ✓ enviar); o áudio vira mensagem (bolha de voz com a
  transcrição embaixo) e o turno segue pelo MESMO `/api/chat/stream` (o caminho `/api/n8n` deixa de ser usado pelo chat).
- **Colar e arrastar:** colar imagem ou arquivo no campo e soltar arquivos sobre a conversa anexam.
- **Bolha do AutoBrokers:** markdown com tabelas roláveis; ao fim, uma linha discreta de ícones (32 px de alvo, 44 px no celular
  pela área de toque): **Copiar** (copia o markdown como texto limpo; "Copiado" por 2 s) e, na última resposta, **Tentar de novo**.
  **Bolha do corretor:** as fichas dos anexos que ele mandou.
- **Rodapé:** a barra de 6 atalhos (`TenantBottomNav`) sai do celular; o ☰ do topo abre a gaveta com os 6 pilares (já existe) e o
  "+" da nova conversa continua no topo. A página não rola como um todo: só a lista de mensagens rola.
- **Foco:** ao abrir o chat, ao trocar/criar conversa e quando a resposta termina (notebook: sempre; celular: não reabre o teclado
  sozinho depois da resposta). Esc para quando responde.
- **Linhas de atividade** enquanto prepara: "Lendo apolice.pdf…", "Ouvindo o áudio…", "Olhando a foto…" (o evento `activity`
  que já existe).

## 5. Fatias (cada arquivo, UM dono)
| fatia | entrega | arquivos |
|---|---|---|
| **A1 · a tela** | composer novo, "+", esforço, áudio na tela, fichas de anexo, colar/arrastar, foco, bolha com Copiar/Tentar de novo, tela vazia, layout sem barra do rodapé, viewport | `components/chat/composer/*` (NOVOS) · `components/InputArea/**` (apagar) · `components/ui/animated-ai-chat.tsx` (apagar se ninguém mais importar) · `app/dashboard/chat/page.tsx` · `components/MessageBubble.tsx` · `components/chat/ChatWelcome.tsx` · `components/chat/ChatShortcutCards.tsx` (apagar) · `components/layout/TenantAppShell.tsx` · `components/layout/TenantBottomNav.tsx` · `components/layout/TenantTopBar.tsx` · `app/layout.tsx` (só o `viewport`) · `app/globals.css` (só o body e o bloco do composer) · `scripts/o-chat-novo.test.mjs` (NOVO) · `scripts/o-chat-responde-e-continua.test.mjs` (só o que a troca do composer exigir) · `package.json` (só o script do teste novo) |
| **A2 · os anexos** | upload novo, BFF com anexos e esforço, leitura por bytes de todos os formatos | `app/api/upload/route.ts` · `app/api/chat/stream/route.ts` · `backend/app/services/chat_anexos.py` (NOVO) · `backend/app/services/vision_service.py` · `backend/app/services/audio_service.py` (só o que a transcrição por bytes exigir) · `backend/requirements.txt` (pillow-heif / xlrd se faltarem) · `backend/tests/test_spec132a_anexos.py` (NOVO) · `scripts/o-upload-do-chat.test.mjs` (NOVO) |
| **A3 · o turno rápido** | esforço por pedido, stream imediato, pré-trabalho dentro do `_gerar` em paralelo, aquecimento, fases medidas, chamada ao `chat_anexos` | `backend/app/api/chat.py` · `backend/app/agents/graph.py` (só `_build_initial_state` e o que o esforço exigir) · `backend/app/services/langchain_service.py` · `backend/app/services/model_policy.py` (o override do chat) · `backend/app/main.py` (só o aquecimento) · `backend/app/services/presidio_service.py` / `guardrails.py` (só o preguiçoso/aquecimento) · `backend/tests/test_spec132a_turno_rapido.py` (NOVO) |
| **A4 · costura** | o fio verde, rotas, next start, capturas, medição em produção é do gerente | `backend/tests/test_spec132a_o_fio.py` (NOVO) · consertos de costura |

**Contratos entre fatias:**
- Upload (A2 → A1): `POST /api/upload` (multipart, `file`, `bucket`) → `{ok:true, bucket, path, nome, mime, bytes, url}`; erro →
  `{ok:false, motivo}` com texto humano ("O arquivo passa de 20 MB.", "Formato não aceito: .exe"). Sem `publicUrl`.
- Pedido (A1 → A2 → A3): `POST /api/chat/stream` com `attachments: [{bucket, path, nome, mime, bytes}]` (≤ 10) e
  `options: {web_search?: bool, esforco?: 'rapido'|'equilibrado'|'maximo'}`. O BFF recusa path fora de `<company_id>/`. Os campos
  antigos `imageUrl/fileUrl/fileName/audioData` continuam aceitos (widget e chamadas antigas), mas o chat novo não os usa.
- Backend (A2 → A3): `chat_anexos.preparar(company_id: str, anexos: list[dict], *, ao_progredir=None) -> ResultadoDosAnexos`
  com `.texto` (blocos `[DOCUMENTO ANEXADO …]` já MASCARADOS), `.imagens` (data URLs para o papel `visao`, ou a descrição já
  pronta), `.transcricoes` (texto do áudio, mascarado) e `.avisos` (o que não deu para ler, em português). Nunca lança: o que
  falha vira aviso. Orçamento total 💭 45 s; cada arquivo ≤ 20 MB.
- `ChatRequest.options` vira `Dict[str, Any]` validado: só `web_search: bool` e `esforco` no conjunto; qualquer outro valor é
  ignorado com log (nunca 422 por chave nova).

## 6. A régua
- **Fio** (A4): um turno com 1 foto + 1 PDF + 1 xlsx + 1 áudio, Storage e modelo DUBLÊS só na borda, atravessa BFF → backend →
  `chat_anexos` → o bloco do modelo contém o texto mascarado de cada um (nenhum CPF cru) → eventos `activity` antes do 1º delta.
- **Mutações (VERMELHAS uma vez, restaura por cópia):** (1) o cliente volta a ler `publicUrl` · (2) o BFF aceita path de OUTRA
  corretora · (3) o CPF de um xlsx chega cru ao modelo · (4) `esforco='turbo'` muda o esforço · (5) o pré-trabalho volta para antes
  do `StreamingResponse` (o teste mede que os cabeçalhos saem antes da leitura do anexo) · (6) a barra do rodapé volta no celular.
- **Isolamento:** o upload e o turno com DUAS corretoras (o path da outra → 403; o filtro no BFF, não a RLS).
- **Gates de app/** (CLAUDE.md §9.1): `npm run test:rotas-montam` + `tsc --noEmit` + `next build` + `next start` + 1 requisição a
  `/api/chat/stream` (401 sem sessão) e `/api/upload` (401).
- **Medição em produção depois do deploy** (o ELO): o mesmo `lat.py` do B1 com Equilibrado e com Rápido; meta 💭 1º delta ≤ 3 s no
  Rápido aquecido. Até o Founder Implantar, a medição fica na caixa do Founder com o comando pronto.
- **Juiz de design:** celular 390×844 e notebook 1440×900, claro e escuro: caixa vazia, com 3 anexos, gravando áudio, o "+" aberto,
  uma resposta longa com tabela e o Copiar. Nota ≥ 90 ou o item vira conserto.
- **Verba:** 💭 ≤ US$ 0,40 (medições e 1 canário de anexos reais).

## 7. Decisões desta SPEC
| # | decisão | nota | contra |
|---|---|---|---|
| D-132A-01 | Refazer o composer (componentes novos), não remendar o `animated-ai-chat` | 90 | remendar 55 · biblioteca pronta de chat (assistant-ui/Open WebUI) 60: arrasta outro estado e outro protocolo |
| D-132A-02 | A barra de atalhos do rodapé SAI no celular; a navegação é o ☰ do topo (padrão ChatGPT/Claude) | 82 | manter 40 · só esconder no chat 65 (inconsistente) |
| D-132A-03 | Saem os atalhos "Ver atendimentos/Novo auxiliar" da tela vazia; nenhum atalho entra no lugar (quem cota escreve) | 80 | chips de sugestão 65 · manter 35 — revê o DS-001 §8.2/§9.1 |
| D-132A-04 | Esforço = o MESMO modelo do papel `chat_principal` com `low/medium/high`; nunca outro modelo escondido | 85 | Rápido = modelo menor 70 (respostas piores sem o corretor saber) |
| D-132A-05 | O backend lê o anexo por BYTES (service role, prefixo da corretora conferido); o provedor de IA nunca recebe URL nossa | 92 | URL assinada ao provedor 60 (vaza link temporário a terceiro) |
| D-132A-06 | O áudio do chat vai pelo MESMO stream (sai do `/api/n8n`) | 88 | manter o n8n 30 |
| D-132A-07 | Caixa no meio na conversa vazia (notebook), embaixo no celular | 85 | sempre embaixo 70 |
| D-132A-08 | Esforço lembrado por aparelho (localStorage); padrão Equilibrado | 80 | por usuário no banco 65 (migration por pouco ganho) |

## 8. O QUE O ESTADO DA ARTE FAZ, E O QUE MODELAMOS
1. **https://github.com/vercel/ai-chatbot** (`components/multimodal-input.tsx`) · faz: composer com anexos como fichas, upload em
   paralelo com fila, parar, foco · modelamos: fichas + fila de upload + o botão que vira PARAR · rejeitamos: o seletor de modelo
   na caixa · juiz: anexa 3 arquivos, tira 1, confere a ficha e o envio.
2. **https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/viewport** (`interactive-widget`) · faz: o
   teclado redimensiona o conteúdo · modelamos: `resizes-content` + `100dvh` sem `100vh` no body · rejeitamos: JS que mede o
   teclado · juiz: captura do celular com o teclado aberto sem espaço sobrando.
3. **https://platform.openai.com/docs/guides/reasoning** · faz: `reasoning.effort` troca latência por profundidade · modelamos:
   Rápido/Equilibrado/Máximo no mesmo modelo · rejeitamos: trocar de modelo sem dizer · juiz: lê o esforço gravado no turno.
4. **https://github.com/open-webui/open-webui** · faz: copiar/regenerar por mensagem, vários formatos de arquivo · modelamos: Copiar
   em toda resposta e Tentar de novo na última · rejeitamos: o painel de configurações por conversa · juiz: copia e cola.
5. **https://web.dev/articles/viewport-units** · faz: `svh/lvh/dvh` · modelamos: a altura do casco em `dvh` · rejeitamos: `vh`
   no body · juiz: rola a lista e confere que o rodapé não se move.

## 9. O QUE SAIU (fora desta SPEC, com destino)
A cotação no chat → 132-B · o WhatsApp do corretor falando com o chat → 132-C · conectores escolhidos por pedido (o chat já usa o
que a corretora conectou; escolher por pedido só se a medição mostrar custo) → pendência · voz em tempo real (Gemini Live) →
pendência · regenerar com outro esforço → pendência.

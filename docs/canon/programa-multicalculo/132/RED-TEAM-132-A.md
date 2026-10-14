modelo: claude-opus-5-5

# RED TEAM — SPEC-132-A (o chat principal) · 14/10/2026

Branch `spec/132-o-chat-e-a-cotacao` · HEAD `618ba14` · base `285cadc`. Read-only sobre o código; os experimentos estão
em `scratchpad/rt132a/` (pii.py · pii2.py · bomba.py · imgbomba.py · aquece.py · bff.cjs) e chamam o MOTOR real
(`chat_anexos.preparar` / `tabela_da_planilha` / `_imagem_para_jpeg`, `app.main.aquecer_no_arranque`, e o `lerAnexos`
do BFF transpilado do próprio `route.ts`). Dublês só na borda (o download do Storage, a busca, o checkpointer, o download
do spaCy).

## VEREDITO: QUEBREI — 2 BLOCKERS, 7 pendências

---

## BLOCKER 1 — CPF quase inteiro (9 ou 10 dos 11 dígitos) chega CRU ao modelo, vindo de célula de planilha

**Teste do produto:** muda os bytes que chegam ao modelo do papel `chat_principal` (PII do segurado, que a SPEC diz que
"não pode mudar": máscara da 130-B antes de qualquer modelo). SIM → BLOCKER.

**Causa (FATO):** `backend/app/services/chat_anexos.py:351-353` (`_celula_md`) corta toda célula em 77 caracteres + "..."
ANTES da máscara; a máscara (`_texto_mascarado`, `:563-569`) roda depois, sobre a tabela já cortada. Um CPF que cruza o
corte perde o fim e a regex do CPF (`policy_document_evidence_service.py:955-957`) e o Presidio
(`presidio_service.py:28`, exige `\d{3}.\d{3}.\d{3}-\d{2}`) não o reconhecem mais.

**Reprodução** (o motor real, `_uma_aba` + `vision_service.mascarar`; coluna "Obs" com texto longo e o CPF dentro):
```
56 -> xxxxxxxxxxxxx CPF [CPF] r... |          <- antes do corte: mascarado
59 -> xxxxxxx CPF 529.982.247-2... |          <- 10 dos 11 dígitos CRUS
60 -> xxxxxxxx CPF 529.982.247-... |
61 -> xxxxxxxxx CPF 529.982.247... |          <- os 9 dígitos-base: o CPF inteiro se recalcula (os 2 últimos são DV)
62 -> xxxxxxxxxx CPF 529.982.24... |
telefone: aaaa… fone (11) 98765-... |  e-mail: bbbb… email fulano.t... |
```
📊 14/10/2026, `PYTHONIOENCODING=utf-8 python -` (o script está no laudo do scratchpad), 7 posições medidas, 4 vazam.
Na mesma linha da tabela vai o nome do segurado (coluna "Segurado") — o par nome + CPF.

**Os outros 15 casos de PII NÃO quebraram** (📊 `pii.py`/`pii2.py`): CPF numérico sem o zero (10 díg.) em coluna
"Documento" → `[NUMERO]`; CNPJ numérico de 13 díg. → `[NUMERO]`; telefone em coluna sem nome → `[NUMERO]`; CPF com espaços
→ `[CPF]`; CPF no NOME DA ABA → `[CPF]`; CPF de 9 díg. → `[NUMERO]`; CSV com BOM + `;` → `[NUMERO]`; CSV cp1252 + TAB →
`[CPF]`; CSV com separador `~` → `[CPF]`; docx com CPF em tabela → `[NUMERO]`; nome do arquivo `rg 529.982.247-25.txt` →
`rg <CPF>.txt` (no bloco do modelo E na linha de atividade); `52998224725.txt` → `<NUMERO>.txt`.

**Conserto (RECOMENDAÇÃO):** mascarar a célula antes de cortar (ou cortar só depois de `_texto_mascarado`). Guarda: o
caso 61 acima tem de dar `[CPF]`, e o teste fica VERMELHO com o corte de volta antes da máscara.

---

## BLOCKER 2 — um arquivo de 1 MB derruba o backend de TODAS as corretoras (CSV/xlsx "bomba"; PNG idem)

**Teste do produto:** segurança/disponibilidade — qualquer corretor logado tira do ar o processo que também atende o
WhatsApp dos segurados de todas as corretoras. SIM → BLOCKER. É superfície NOVA desta SPEC (os leitores locais de
planilha e a conversão de imagem com Pillow não existiam no chat; antes a foto ia como URL ao provedor).

**Causa (FATO):** `_uma_aba` (`chat_anexos.py:360-363`) acolchoa TODA linha até a largura da linha mais larga
(`[None] * (largura - len(ln))`) e guarda até 50.000 linhas × 10 abas (`LINHAS_LIDAS_POR_ABA`, `ABAS_LIDAS`, `:52-53`);
o openpyxl `read_only` faz o mesmo até a última coluna usada. Memória ≈ 8 B × largura × linhas, sem teto. O orçamento de
45 s (`:741`) não ajuda: `asyncio.to_thread` não se cancela — a thread segue comendo memória e CPU (e um lugar do poço
compartilhado `EXECUTOR_THREADS`) depois do aviso "Demorei demais". O mesmo `path` pode vir 10× no mesmo pedido.

**Reprodução** (📊 14/10/2026, o leitor REAL `tabela_da_planilha`, `tracemalloc`):
```
csv   7 KB (1 linha com  5000 vírgulas + 1000 linhas curtas): pico  39 MB
csv  12 KB (1 linha com 10000 vírgulas + 1000 linhas curtas): pico  78 MB
csv  14 KB (1 linha com 10000 vírgulas + 2000 linhas curtas): pico 154 MB   <- linear: 8 B × largura × linhas
xlsx  4,5 KB (400 linhas, 1 célula em A e 1 em XFD):           pico 107 MB · 2,0 s
xlsx 12,6 KB (1600 linhas):                                    pico 407 MB · 6,0 s   (0,25 MB por linha)
```
💭 extrapolação linear (não rodada, a máquina tem 8 GB): CSV de ~1,1 MB (1 M vírgulas + 50 mil linhas "x") → ~400 GB;
xlsx de ~400 KB com 50 mil linhas → ~12,7 GB e ~190 s. O upload aceita os dois (`route.ts:189` só confere o "PK" do
xlsx; CSV/TXT não têm assinatura).

**Imagem** (📊 `imgbomba.py`, pico do working set do processo): PNG paleta 8000² (64 Mpx, **8 KB**) → +794 MB; PNG 1-bit
9000² (81 Mpx, **10 KB**) → +515 MB. PNG 1-bit 13000² (169 Mpx, **20 KB**) ABRE só com `DecompressionBombWarning`
(o erro do Pillow é acima de 179 Mpx; ninguém no repo mexe em `MAX_IMAGE_PIXELS` — `grep` = 0) → 💭 ~1–2 GB por foto,
×10 fotos em paralelo por pedido.

**Conserto (RECOMENDAÇÃO):** teto de células (linhas × colunas) e de colunas antes de acolchoar; ler só as linhas da
amostra + somas em fluxo; `Image.MAX_IMAGE_PIXELS` baixo (ex. 50 Mpx) + `draft()` para JPEG; um semáforo de leitura por
processo; checar o tamanho descomprimido do zip (soma de `ZipInfo.file_size`) antes do openpyxl/python-docx.

---

## O QUE NÃO QUEBREI (com prova)

- **Arquivo de outra corretora pelo BFF** (📊 `bff.cjs`, o `lerAnexos` do `route.ts` transpilado): `../` 403 · `%2e%2e`
  403 · `\..\` 403 · `．．` (unicode) 403 · prefixo de OUTRA corretora 403 · `//` 403 · `/` inicial 403 · só o prefixo
  403 · `<cid>x/` 403 · 600 chars 403 · NUL 403 · espaço 403 · maiúsculas 403 · bucket `avatars`/`voice-messages`/
  `portal-evidence` 400 · 11 anexos 400 · sessão sem company → recusa. O backend confere de novo
  (`chat.py:858`, `chat_anexos.py:580`) e o widget descarta `attachments` (`chat.py:810-814`). `<cid>/.../a.pdf` passa
  (literal no Storage, não sobe de pasta).
- **Esforço:** `lerOpcoes({esforco:'turbo'})` → descartado; `'MAXIMO'` → descartado no BFF; backend só
  `ESCOLHAS_DE_ESFORCO`; `model_policy.py:_com_esforco_do_pedido` só vale para `chat_principal`, o MESMO modelo, a reserva
  com o esforço DELA; o LLM é criado na construção do grafo (`graph.py:214-233`) e a chave do cache leva o esforço
  resolvido (`langchain_service.py:104`) → um grafo por esforço, sem vazar entre turnos (ContextVar).
- **HyDE ≥ 6 palavras só no chat do corretor:** `hyde_no_turno` (`graph.py:1272`) devolve `is_hyde` quando
  `esforco_do_chat is None`; o único caller que passa `esforco` é `chat.py:1573` (painel); `stream_agent` (widget,
  `graph.py:2972`) e a chamada de `graph.py:2238` não passam. O atendimento não muda.
- **Consulta periódica:** `/api/conversations?session_id=` filtra `session_id` + `user_id` da SESSÃO
  (`conversations/route.ts:136-141`); `juntarChegadas` deduplica por `client_request_id`+papel ou `id`
  (`page.tsx:181-225`); a troca de sessão encerra o relógio (`encerrado`) e a resposta atrasada é descartada.
- **Bateria do repo:** 📊 `test_spec132a_anexos.py` + `test_spec132a_o_fio.py` 26 passed (50 s);
  `test_spec132a_turno_rapido.py` 19 passed (31 s). Verdes — e nenhum cobre os dois blockers.

## PENDÊNCIAS (não mudam byte em operação normal)

1. **O aquecimento PODE derrubar o app** (📊 `aquece.py`: modelo `pt_core_news_md` ausente + download do spaCy falhando
   como ele falha, `sys.exit(1)` → saída `ESCAPOU DO EVENT LOOP: SystemExit 1`). `main.py:_etapa` pega só `Exception`;
   `SystemExit` atravessa o `to_thread` e o `Task`. O `Dockerfile:8` só instala `en_core_web_lg` → em produção o `pt` é
   baixado por pip a CADA arranque. Antes da SPEC o mesmo `SystemExit` viria no 1º turno; agora vira laço de arranque.
   Conserto: `except BaseException` no `_etapa` + `spacy download pt_core_news_md` no Dockerfile.
2. **Foto legítima pesa:** 📊 JPEG 48 Mpx → +425 MB de pico em `_imagem_para_jpeg` (o `exif_transpose` decodifica
   inteiro antes do `thumbnail`) → 💭 10 fotos de iPhone ≈ 4,2 GB num pedido.
3. **Guardrail que barra dentro do stream ainda grava** `payload.transcricao` (já mascarada) na pergunta: `chat.py:1499`
   roda antes do guardrail (`:1512`). A resposta não é gravada (`_persistir` com conteúdo vazio, `:1202`).
4. **Idempotência:** dois POSTs simultâneos com o mesmo `client_request_id` passam os dois pela checagem `chat.py:881`
   (o registro é em `:1749`, depois de 4 `await`). PRÉ-EXISTENTE (na base a janela era maior: grafo + visão + guardrail);
   a SPEC estreitou. Não reproduzido com dublê.
5. **`fileUrl`/`imageUrl` do corpo seguem até o backend** (`route.ts:344-346`) → `baixar_documento` faz `httpx.get` com
   `follow_redirects=True` sem allowlist (`vision_service.py:279-293`) = SSRF de usuário logado. PRÉ-EXISTENTE (base
   `285cadc` igual), fora do diff, mas a SPEC poderia ter fechado (o chat novo não usa esses campos).
6. **Áudio sem teto de duração no servidor:** o gravador para em 600 s (`GravadorDeAudio.tsx:22`), mas o arquivo de
   20 MB (💭 ~1 h em opus) vai inteiro à transcrição, ×10 por mensagem; cobrado pelo ledger.
7. CPF falado por extenso ("cinco dois nove…") na transcrição não casa a máscara de dígitos (não medido com áudio real).

## MAIOR LACUNA
Os leitores novos não têm teto de RECURSO (memória/tempo) — só de bytes do arquivo; e o corte de texto vem antes da
máscara. Os testes provam a forma feliz, nenhum mede pico de memória nem a célula longa.

## CONFIANÇA / O QUE FICOU POR MEDIR
Alta nos dois blockers (motor real, 3+ amostras cada, linearidade medida). Não rodei: o OOM real de 50 mil linhas
(máquina de 8 GB), HEIC corrompido (só por leitura: cai no `except` → aviso), PDF malicioso (o leitor 130-B não mudou),
`next start`, o widget de ponta a ponta, a corrida de idempotência com dublê.

## NOTA: 62 / 100
O isolamento entre corretoras, o esforço e o widget estão bem feitos e resistiram a tudo; a máscara erra num caso
real (célula longa) e um arquivo de 1 MB tira o produto do ar para todos.

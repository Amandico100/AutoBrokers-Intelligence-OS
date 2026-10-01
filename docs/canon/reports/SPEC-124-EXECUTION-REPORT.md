# SPEC-124 — O portal de vidros destrava com a mesma régua do WhatsApp, e a leitura de documentos no modelo certo

> Relatório de execução · 30/09–01/10/2026 · rito AAA v13 · 🔴 CRÍTICO · branch `spec/124-portal-destrava-e-visao`
> commit inicial `a0ad834` (o último da SPEC-123) · último commit de código `c3cd5c7` · commit final: ver §12 (ENTREGA)
> SPEC `specs-propostas/SPEC-124-o-portal-de-vidros-destrava-e-a-visao-certa.md` · bancada `reports/SPEC-124-BANCADA-VISAO.md`
> Executada no MESMO chat e na MESMA sessão da SPEC-123 (`557bb19c`); o BLOCO 0 e a F2 rodaram intercalados com o fim da 123.

## 0. O EXECUTION CARD (definitivo, ajustado ao que aconteceu)

```
OUTCOME ........  (a) VISÃO — ENTREGUE: a foto do segurado (`visao`) e a imagem no PDF (`visao_documento`) passam ao `gpt-6-luna`
                  medium — 📊 o mesmo acerto do `gpt-6.1-sol` (30 documentos SINTÉTICOS, k=3) a ~1/18 do custo; reserva
                  `claude-sonnet-5-5` low só na `visao`; o docling obedece ao catálogo e o custo dele entra no ledger.
                  (b) PORTAL — A ESTRUTURA, NÃO A AUTONOMIA: quando o API-first para, a MESMA régua do WhatsApp decide, continua
                  o MESMO pedido e escreve no MESMO diário. 🔴 O API-first nunca rodou, o DOM ficou fora e, com o DEDUZIR
                  desligado e a UF consertada (B1), o portal HOJE não responde nenhuma parada sozinho: pergunta ou chama pessoa
RISCO ..........  9 (ALCANCE segurado e loja 3 · REVERSIBILIDADE pedido aberto na loja 3 · FREQUÊNCIA 3)
SUPERFÍCIE .....  2 (decisão do portal, contrato do docling, rota de visão)
PISO APLICADO ..  §3.2 — abre pedido real; troca o modelo que lê todo documento → CRÍTICO
NÍVEL ..........  🔴 CRÍTICO · builders Opus 5.5 xhigh · juiz ‖ red team Opus 5.5 · 1 conserto · confirmação
O FIO ..........  portal: `portal_action` → `_aguardar` → parada `responder:*` → `_destravar_a_parada` →
                  `destravador.destravar_parada_do_portal` → `decidir_parada_do_portal` → `regua_do_nucleo` (o MESMO do
                  WhatsApp) → agir = `montar_job_de_continuacao` · perguntar = hoje → diário (`origem='portal'`) · visão: foto →
                  `describe_image` → `visao` · PDF → `sanitization_service` → POST /parse com o modelo → ledger `vision`
PARALELISMO ....  F2 ‖ (fim da 123) · F1 depois da F2b (arquivos disjuntos; F1 esperou o destravador da 123 fechar)
UNIDADES .......  BLOCO 0 (1 investigador) · F2 bancada + docling · F2b migration + smoke · F1 portal · conserto · confirmação
COESÃO .........  "uma régua de destravar para os dois canais; um catálogo para todos os modelos"
TIME ...........  investigador · 3 builders · juiz ‖ red team · 1 builder de conserto · confirmação · bateria · atualizador
REFERÊNCIA .....  interna: `LAUDO-124-B0.md`, `SPEC-124-BANCADA-VISAO.md`, a régua e o diário da SPEC-123, os HAR da 001.10.1 ·
                  externa: SPEC §6
GATES ..........  G1–G8 (§4)
O ELO ..........  "o portal chama humano porque a decisão não tem a política": A = onde o portal para (📊 BLOCO 0: 0 paradas
                  reais, 0 vidros desde 01/08) · B = a régua decide (testes) · B→A = teste do fio com HAR reais; ao vivo NÃO
FAIXA DE RELÓGIO  💭 meio dia (SPEC) · 📊 BLOCO 0 30/09 23:30Z → conserto 01/10 08:39Z (F1 → conserto ≈ 1 h 37 min)
nota da execução  84/100 (§11)
MIGRATIONS .....  20261001_03 (rotas de visão) · 20261001_04 (diário aceita `respondeu_portal`) — APLICADAS pelo MCP (§6)
ORÇAMENTO ......  📊 ledger 01/10: OpenAI US$ 0,1288 · Anthropic US$ 0,2234 (tetos 1,00 · 0,80)
```
① Lentes: não pedido (CRÍTICO = juiz ‖ red team). ② Auditoria: juiz ‖ red team cegos (§5). ③ Valor marginal: G3 (calibrar
o portal) não é mensurável sem uma parada real de produção; fotos REAIS mascaradas não existem no acervo.

## 1. O QUE MUDOU (em linguagem clara)

**BLOCO 0 (laudo `LAUDO-124-B0.md`) — quatro fatos que mudaram o desenho:**
1. 📊 `portal_jobs` (SELECT, 30/09): 39 jobs `vidros_lanternas` de 06 a 10/07, uma corretora, todos pelo caminho DOM; **0 de
   vidros desde 01/08** (📊 01/10: os 38 jobs desde 01/08 são todos `cobranca_sweep`). O API-first das 001.10/001.10.1
   **nunca rodou em produção**.
2. O API-first não chama modelo; o papel `portal_decisao` só existe no caminho DOM (`adaptive.py`), que roda no contêiner
   do portal-worker — **sem `app/`, sem o destravador e sem retomada** (o Dockerfile copia só `backend/portal_worker`).
3. PDF no atendimento **não passa por modelo de visão** (OCR easyocr + PyPDF2, `extract_images=False`); a rota
   `visao_documento` só é usada na sanitização da base de conhecimento, e 📊 `sanitization_jobs` tem 0 linhas. A foto
   (CNH, CRLV, apólice fotografada) é que passa pela rota `visao`. → o ganho da D3 vale de fato para a FOTO.
4. 📊 Ledger `service_type='vision'`: 20 chamadas, todas `gpt-4o-mini` (04/07–10/09), US$ 0,0713, 2 corretoras.

**F2 · a visão certa (`1349c39`)** — bancada nova por CAMPO (`backend/tests/corpus/bancada/visao_campos/`): 10 documentos
sintéticos (apólice auto em 2 layouts, residencial, CNH, CRLV, orçamento, boleto, foto de para-brisa, apólice degradada,
CNH fotografada) com gabarito de 12 campos e distratores (prêmio ao lado do LMI, franquia de vidros ao lado da básica…);
juiz normalizado; "campo que o documento não tem e o modelo preencheu" = inventou = erro. Linhas de controle `perfeito`
(100 %) e `burro` (0 % — 📊 e 48,3 % no "acerto geral", que por isso não é a nota). O docling recebe
`vision_provider/vision_model/vision_effort` no POST `/parse` (`main.py`), a tarefa os usa (`tasks.py`), `VISION_MODEL` vira
paraquedas (`config.py`), provedor ≠ openai → HTTP 400 (não troca calado); `sanitization_service` resolve a rota no catálogo
e grava o custo devolvido em `metadata.visao` no ledger (`service_type='vision'`, `details.papel='visao_documento'`).

**F2b · a escolha (`217a2c1`)** — migration `_03` aplicada: `visao` = Luna medium + reserva Sonnet 5.5 low (v5);
`visao_documento` = Luna medium, sem reserva (o docling só fala Chat Completions da OpenAI — `PictureDescriptionApiOptions`,
lido no wheel docling-slim 2.130.0). Snapshot `modelos_snapshot.json` regerado. 📊 Smoke real da rota `visao` no ledger:
1 chamada `gpt-6-luna`, **US$ 0,000308**; e o pedido EXATO do docling com a Luna → HTTP 200 com `usage`.

**F1 · o portal (`63595d5`)** — o NÚCLEO da política foi EXTRAÍDO do destravador (`regua_do_nucleo`, destravador.py:1258)
e os dois canais o chamam (teste `test_os_dois_canais_passam_pelo_mesmo_nucleo`); o WhatsApp ficou equivalente linha a linha
(📊 juiz e red team: os `test_spec123_*` verdes). Adaptador do portal: `CLASSE_DA_PARADA_DO_PORTAL` (a classe vem da TABELA,
nunca do modelo), `decidir_parada_do_portal` (:2155), `destravar_parada_do_portal` (:2425), plugado em
`portal_tool._aguardar` → `_destravar_a_parada` (portal_tool.py:791/800). Agir = continuação do MESMO pedido
(`montar_job_de_continuacao` + `continuar_atendimento`, `confirm` vem de `envio_liberado`, fail-closed); teto
`TETO_DE_DESTRAVAMENTOS_POR_PEDIDO = 3` (leitura que falha conta como estourado); modo por `cerebro_modos`
(`company_id` × seguradora); `off` sai antes de qualquer leitura extra (`test_CONTROLE_off_e_hoje_byte_a_byte`).
Migration `_04`: o diário aceita `acao='respondeu_portal'`. As 9 proibições NUNCA do portal (reparo × troca, agendar,
horário, sem cobertura, talvez já aberto, abrir/materializar/vistoria…) decididas pela tabela ANTES do modelo.

**Conserto único (`c3cd5c7`)** — §5.

## 2. COMMITS
📊 `git log --oneline a0ad834..HEAD` (01/10): `1349c39` F2 · `217a2c1` F2b · `63595d5` F1 · `c3cd5c7` conserto · + o commit
de documentos do gerente (§12). 📊 `git diff --stat a0ad834..c3cd5c7`: 34 arquivos, +3.665 / −68 (10 PNG do corpus; o
destravador +727).

## 3. BATERIA
📊 Suíte inteira UMA vez em `c3cd5c7`, worktree limpo, `cd backend && .venv/Scripts/python -m pytest tests -q -p no:cacheprovider`:
```
34 failed, 3070 passed, 2 skipped, 32 xfailed, 1 xpassed, 195 warnings in 5339.81s (1:28:59)
```
Triagem nominal contra `BATERIA-LINHA-DE-BASE.txt` (35, da SPEC-123): **31 iguais** · **4 sumiram** (guardas de ordem/carga, não
conferidos no commit base — não é prova de ganho) · **3 novas**: `test_o_timeout_nao_deixa_neto_vivo::test_a_linha_de_controle_o_neto_CONSEGUE_sobreviver`
e `[test_o_vocabulario_viaja_na_imagem]` = ordem/carga (passam isoladas); `test_o_protocolo_tem_policia` = pré-existente desde
`a0ad834` (o card do relatório da 123 não cabia nos 3.000 caracteres que o guarda lê), CONSERTADO nos documentos desta SPEC
(📊 `pytest tests/test_o_protocolo_tem_policia.py` → **1 passed**; o script: 89 ok, 0 falhas). → **0 regressões da SPEC-124**.
`BATERIA-LINHA-DE-BASE.txt` regravada com **33**.
📊 Antes da bateria (01/10): juiz em `63595d5` — `tests/test_spec124_*.py tests/test_spec123_*.py` + guardas do catálogo →
**1 failed, 638 passed, 1 skipped** (a falha: `node_modules/typescript` ausente no worktree — ambiente; com a junção, 14
passed) · red team: `test_spec123_*` 530 passed, SPEC-124 39 passed com os HAR reais · conserto (`conserto124/GATE.txt`):
**619 passed** (2:44). ⚠️ `test_spec116_f3b_plataforma`: 2 falhas vistas na execução, apontadas como pré-existentes e
fora da linha de base; 📊 isolado em `c3cd5c7` (01/10, `pytest tests/test_spec116_f3b_plataforma.py`) → **16 passed** —
então dependem de ordem/carga; a bateria decide (P-124-11).

## 4. GATES
| gate | estado |
|---|---|
| **G1** o caminho conhecido do portal não muda | ✅ **com ressalva.** 📊 juiz: 7 scripts (`test_e001101_o_fio_da_continuacao` 78/0 · `test_e00110_a_costura_do_agente_ao_desfecho` 161/0 · `test_spec116_f3b_portal` 28 passed · os outros rc=0); red team: 14 scripts `test_e00110_*`/`test_e001101_*` rc=0. ⚠️ Os dublês desses scripts não têm `cerebro_modos` → G1 provado só com modo `off`; em produção o modo é `on` (P-124-09). ⚠️ Sem os 7 HAR do intake (fora do Git) os testes do fio PULAM |
| **G2** NUNCA SOZINHO no portal: 0 violação; mutação → vermelho | ✅ 📊 juiz: varredura de 19 paradas + 1 inventada × saídas agressivas (franquia, cancelar, número inventado) × 3 classes, nota 100 e 2ª opinião concordante → **0 vão ao portal** nas proibições. O único furo (a UF, B1) não era uma das 4 proibições do D2: era uma DEDUÇÃO disfarçada — fechado no conserto. Mutações: red team 3 (2ª opinião do mesmo provedor, `e_dado_do_caso=True`, regex de custo) todas vermelhas; conserto: UF de volta a `responder_com_dado` → **14 failed** |
| **G3** calibração ≥ 90 % nas telas reais | ❌ **não mensurável.** 📊 0 jobs de vidros desde 01/08; 0 paradas reais do API-first em produção; `diario_de_decisoes` `origem='portal'` = 0 linhas. E hoje o destravador do portal não age sozinho em nenhuma parada (teste `test_C1_HOJE_o_destravador_do_portal_nao_responde_NENHUMA_parada_sozinho`) — não há faixa de agir para calibrar. Reabrir: P-124-02 |
| **G4** visão: acerta ≥ o atual e custa ≤ | ✅ **com teto declarado.** 📊 bancada k=3: Luna 30/30, nota D3 100 %, US$ 0,00016/doc · Sol 6.1 (o atual) 30/30, 100 %, US$ 0,00566 sem cache (0,00226 com) · Sonnet 5.5 low 30/30, 100 %, US$ 0,00548. Ledger sem cache: Luna US$ 0,000202 × Sol 0,003673 por chamada (~1/18). ⚠️ Corpus SINTÉTICO: 0 erros em 30 → até ~10 % pelo IC 95 % superior; o gabarito de `coberturas` foi afrouxado DEPOIS da 1ª rodada da Luna (26/30 → 30/30, "Assistência 24h" sem LMI vira opcional, valor inventado continua erro; imagens md5 iguais; os três braços sob o mesmo gabarito). Juiz reproduziu dos JSON crus. Opus não rodou (os três no teto) |
| **G5** o docling segue o catálogo | ✅ `test_g5_trocar_a_rota_no_catalogo_muda_o_modelo_do_docling_sem_mexer_em_env` e `test_paraquedas_chamador_antigo_sem_o_campo_continua_funcionando` verdes. ⚠️ Alcance hoje: só a base de conhecimento (📊 `sanitization_jobs` 0 linhas); uso de tokens do docling sem prova ponta a ponta (P-124-06) |
| **G6** custo ≤ orçamento, do ledger | ✅ 📊 `token_usage_logs` 01/10: bancada `details.papel='visao'` OpenAI **0,128485** (Luna 0,008937 em 50 · Sol 6.1 0,119548 em 40) + smoke `vision` 0,000308 = **0,128793** · Anthropic **0,223422** (Sonnet 5.5, 40). Tetos 1,00 / 0,80. A F1 e o conserto não chamaram modelo real |
| **G7** bateria 0 novas | ✅ 📊 34 failed / 3070 passed: 31 da base, 2 de ordem/carga, 1 pré-existente (o card da 123) consertado → **0 regressões** (§3) |
| **G8** diário legível, duas corretoras isoladas | ✅ no código e no teste: `_job_inteiro` filtra `company_id` e reconfere na linha; modo, teto, conversa e memória por `company_id`; `test_duas_corretoras_o_modo_de_uma_nao_liga_a_outra`; o diário descreve o que ACONTECE (conserto C4: pessoa numa parada do segurado = "perguntou ao segurado"). ⚠️ com dublê; 📊 `diario_de_decisoes` = 0 linhas (01/10) |

## 5. JULGAMENTO
- **Juiz (Opus 5.5 fresco): FAIL, 80** (confiança 82; F2 ≈ 90, F1 ≈ 72), 1 blocker; 7 números reproduzidos (ledger e JSON
  crus da bancada, "0 vidros desde 01/08"), as duas migrations conferidas no banco. **Red team (Opus 5.5 fresco, cego ao
  juiz): QUEBREI, 74**, o MESMO blocker, reproduzido com o código do produto.
- **B1 — achado pelos DOIS:** `uf_desconhecida` estava classificada como `responder_com_dado`, e "dado do caso" era QUALQUER
  folha dos parâmetros. A parada só nasce quando a UF que o segurado escreveu NÃO está na lista do portal — logo, toda
  resposta sozinha seria uma UF DIFERENTE da dele (o estado do cadastro), e o pedido iria para a cidade homônima de outro
  estado. 📊 Reproduções: juiz `modelo=SP nota=75 → RESPONDER {'uf': 'SP'}` para "Curitiba"; red team `nota=5 → RESPONDER
  'SC'` para "Bom Jesus/RS", e com `GET /ufs` em formato novo até `'FULANO FICTICIO'` ia como UF. O teste do fio provava um
  estado impossível (`uf: "ZZ"`, que o produto recusa antes de abrir o pedido). Era uma DEDUÇÃO que pulava o DEDUZIR
  desligado e a 2ª opinião — a classe de defeito que o conserto X da SPEC-123 fechou no WhatsApp.
- **Conserto único `c3cd5c7`** (1 builder): **C1** `uf_desconhecida → perguntar_ao_segurado` (proibição `so_o_segurado_sabe`)
  e a UF só sai como SIGLA da lista da parada · **C2** dado do caso no portal SÓ pelo campo que a parada espera (red team P1:
  regredia o X2 da 123) · **C3** questionário por `pergunta_<codigo>` (red team P8) · **C4** o diário diz o que ACONTECE:
  pessoa numa parada do segurado vira "perguntou ao segurado" (juiz P3) · o teste do fio passou a usar entrada que o produto
  gera. 📊 Prova: os testes novos contra o código ANTES → **25 failed, 50 passed** (`VERMELHO_ANTES.txt`); depois → verdes;
  mutação (UF de volta) → **14 failed**; ataques do juiz e do red team rerodados → `PERGUNTAR_AO_SEGURADO so_o_segurado_sabe`,
  `resposta ao portal: {}`.
- **A consequência, escrita como o juiz pediu:** depois do conserto, com o DEDUZIR desligado, **o destravador do portal não
  age sozinho em nenhuma parada**. A F1 entrega a fiação, a régua única, o NUNCA e o diário — **autonomia real no portal = 0
  ações** até a calibração religar o DEDUZIR (P-124-02) e o API-first ser ligado (D-124-F).
- **Confirmação (juiz Opus 5.5 novo, só o diff `63595d5..c3cd5c7`): PASS, nota 90.** B1 **FECHADO** com duas defesas: a
  tabela manda `uf_desconhecida` ao segurado, e `resposta_do_portal` só envia SIGLA de UF que está na lista da parada. 📊 Mutação
  que reintroduz o B1 → **10 failed**; os 16 scripts da 001.10/001.10.1 → exit 0; o CHECK do banco conferido; **619 passed**
  (123 + 124). Pendências novas: **P-C2** — com a calibração religada, `cidade_ambigua` escolheria "Curitibanos" para
  "Curitiba" (a bancada da calibração precisa de cidade homônima) → **P-124-14** · **P-C3** — a regex de `pergunta_<codigo>`
  recusa `_`/`-` (falha segura) → **P-124-15**.

## 6. MIGRATIONS
📊 `select version, name from supabase_migrations.schema_migrations where name ilike '%spec124%'` (01/10):
| arquivo | versão aplicada | o que faz |
|---|---|---|
| `20261001_03_spec124_visao_por_bancada.sql` | `20261001071707` | `llm_papeis`: `visao` = openai/gpt-6-luna medium + anthropic/claude-sonnet-5-5 low (v5); `visao_documento` = openai/gpt-6-luna medium, sem reserva (v4); 2 linhas em `llm_papeis_historico` com `linha_anterior.modelo_primario = gpt-6.1-sol` |
| `20261001_04_spec124_diario_acao_do_portal.sql` | `20261001071232` | `diario_de_decisoes.ck_diario_acao` aceita `respondeu_portal` (5 valores); `origem='portal'` já era aceito |
APPLY/VERIFY/ROLLBACK no cabeçalho das duas, antes de aplicar; linhas no `MANIFEST.md`. ROLLBACK da `_03`: volta as duas rotas
ao `gpt-6.1-sol` pelo histórico; da `_04`: falha seguro se houver linha `respondeu_portal`. 📊 VERIFY 01/10: as duas rotas na
Luna (SELECT em `llm_papeis`); `cerebro_modos` 40 linhas `on` (inclui `yelum` e `porto`, ramo `todos` → vale para o portal).

## 7. A DRENAGEM
**FECHADAS:** P-122-01 (o docling recebe o modelo de quem chama; `VISION_MODEL` é paraquedas) · P-S116-09 (a mesma, na
origem). **CONTINUA:** P-122-02 (a env `VISION_MODEL` no EasyPanel — agora só paraquedas, pode ficar como está).

## 8. O QUE FICOU FORA
P-124-01…15 em `PENDENCIAS.md`: plugar o DOM · calibrar o DEDUZIR (autonomia do portal) · docling sem lista de modelos
aceitos e `SERVICE_KEY` vazio por padrão · ledger do docling subconta em retry · bancada com fotos REAIS mascaradas · tokens
do docling ponta a ponta · "nunca 'Não sabe'" sem código e `_RX_CANCELA_NO_PORTAL` duplicado · esperas encadeadas até ~600 s ·
G1 só com `off` · `visao_documento` sem reserva · `test_spec116_f3b_plataforma` · `ETAPA_DA_PARADA` genérica · ordem de deploy
do docling · `cidade_ambigua` × cidade homônima (P-124-14) · `pergunta_<codigo>` com `_`/`-` (P-124-15). Decisões em `FOUNDER-DECISIONS.md` D-124-A…F.

## 9. A CAIXA DO FOUNDER
`TAREFAS-DO-FOUNDER.md`, bloco S124: Implantar **nesta ordem** — `docling-service` (o WORKER antes da API: worker velho com o
campo novo dá `TypeError`) → `smith-api` → `smith-worker` → `smith-web`; a env `VISION_MODEL` pode ficar; um teste real com
foto de CNH/apólice no WhatsApp de teste + o SQL do ledger (esperar `gpt-6-luna`); decidir D-124-F (ligar o API-first).

## 10. RISCOS REMANESCENTES (FATO · INFERÊNCIA)
- 🔴 **FATO:** a troca da rota `visao` para a Luna **já vale em produção** (migration aplicada; o snapshot vai no Implantar
  do `smith-api`) com bancada SINTÉTICA — teto, não piso. Foto real (reflexo, dobra, corte) não foi medida (P-124-05).
- **FATO:** nada do portal rodou ao vivo; a F1 só alcança o portal quando o API-first for ligado, e mesmo assim só pergunta.
- **FATO:** o DOM (o caminho que já rodou) continua chamando humano como antes (P-124-01).
- **INFERÊNCIA:** worker do docling antigo + API nova → `TypeError` e 2 retries — inferido da assinatura e do
  `autoretry_for`, não rodado; só com `extract_images=True` (📊 0 jobs de sanitização).

## 11. NOTA E TELEMETRIA
**NOTA DO GERENTE: 84/100.** Critério: a visão é ganho real e provado (mesmo acerto, ~1/18 do custo, docling no catálogo); o
portal ganhou a MESMA régua, o diário e a continuação do mesmo pedido, com 0 erro grave. Perde porque, com o DEDUZIR desligado
e o B1 consertado, o portal NÃO destrava nenhuma parada sozinho hoje, o caminho DOM ficou fora e o API-first nunca rodou.
Juiz 80 · red team 74 → confirmação 90.

📊 `python backend/scripts/medir_execucao_claude_code.py --sessao atual` (01/10 ~08:42Z, sessão `557bb19c`, UTC) — ⚠️ a
sessão é a MESMA da SPEC-123; separo pela diferença:
```
EXECUTOR (sessao principal)   30/09 21:44   656 min  turnos 158  pico 600k  saida 185k  US$ 44.05  opus-5-5
agentes SPEC-124 (US$): BLOCO 0 6,99 · F2 15,74 · F1 12,97 · F2b 2,27 · juiz 6,70 · red team 4,11 · conserto 6,29 ·
  confirmação 0,51 · bateria 0,33 · atualizador 1,10 (os três últimos em curso na medição)
TOTAL  agentes alem do executor: 36 . turnos 2844 . ctx 659.9M . saida 0.45M . US$ 397.19
```
Derivado: agentes da SPEC-124 ≈ **US$ 57,01** (parcial, 3 em curso) · executor: US$ 44,05 − 35,45 (medição do fim da 123) =
**≈ US$ 8,60** depois da 123, + a parte da 124 já contida nos 35,45 (BLOCO 0 e F2 intercalados). APIs do produto: OpenAI
0,1288 · Anthropic 0,2234 (G6). Relógio da 124 depois de a 123 fechar: 📊 07:02Z (F1) → 08:39Z (conserto) ≈ 1 h 37 min.
Achados por mecanismo: BLOCO 0 (4 fatos que mudaram o desenho: portal parado, DOM fora do alcance, PDF sem visão, ledger
antigo) · bancada (Luna = Sol a 1/18; o "acerto geral" esconde o `burro`) · juiz 1 blocker + 8 pendências · red team o MESMO
blocker + 8 pendências (P1, P8 e a lista de modelos do docling exclusivos) · confirmação 2 pendências (P-124-14/15) ·
bateria 0 regressões (1 guarda pré-existente consertado).

## 12. ENTREGA
```
git push origin HEAD:main
📊 01/10/2026:
To https://github.com/Amandico100/AutoBrokers-Intelligence-OS.git
   a0ad834..22e459e  HEAD -> main
`git rev-list --count origin/main..HEAD` → 0
git rev-list --count origin/main..HEAD   → (o gerente cola; tem de ser 0)
```
📊 Antes do push (01/10): `git rev-list --count origin/main..HEAD` → **4** (os 4 commits de código ainda não subiram).

**Nenhum motor paralelo foi criado.** O portal usa o NÚCLEO extraído do destravador da SPEC-123 (os dois canais chamam
`regua_do_nucleo`), a continuação da 001.10.1 (`montar_job_de_continuacao`), o diário da 123 (`diario_de_decisoes`) e a chave
`cerebro_modos`; a visão usa o catálogo `llm_papeis`, a fábrica (`criar_de_resolvido`), o ledger `token_usage_logs` e a
bancada `evals/bancada.py` estendida; o docling ganhou um campo, não um roteador.

# SPEC-EXTRA-001.4 — RESEARCH PACK
## O corredor não trava sozinho · evidência reaberta e conferida em 13/09/2026

**Versão:** 1.0 · 13/09/2026. **Natureza:** evidência para conversão. **Não é** relatório de execução.
**Árvore e revisão:** `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX`, branch `docs/diagnostico-pilotos-0912`, HEAD **`a0bb5fe`** (`git rev-parse HEAD`, 13/09/2026).
**Método:** leitura de código na árvore local + execução de scripts e testes **read-only** + AST sobre os playbooks + `grep`/`wc` sobre o corpus versionado. **Nada foi alterado, nenhuma migration foi rodada, nenhuma mensagem foi enviada, nenhum portal foi acessado.** Nenhuma consulta nova ao banco de produção foi feita nesta preparação — os números que vêm do banco estão marcados como herdados do diagnóstico e **o BLOCO 0 os remede**.
**Fonte de origem:** `docs/canon/DIAGNOSTICO-PILOTOS-E-PLANO-EXTRA-2026-09-12.md` §1.6, §3 (bloco 001.4), §11 inteiro.

---

## 0. Legenda e precedência

| marca | significa | exigência |
|---|---|---|
| **📊 MEDIDO HOJE** | contagem ou linha que **eu** reabri em 13/09 nesta revisão | o comando vem junto |
| **📊 HERDADO** | número do diagnóstico de 12/09, vindo do **banco de produção** — não reproduzido aqui | o BLOCO 0 remede antes de usar |
| **OBSERVADO NO REPO** | existência visível no código | precisa de prova de execução |
| **HIPÓTESE** | consequência a investigar | **não** é incidente constatado |
| **PENDENTE DE MEDIÇÃO** | precisa de comando, consulta ou canário | — |
| **FONTE EXTERNA** | padrão documentado | não determina arquitetura interna (§7.3 do protocolo) |

🔴 **Precedência:** onde este pack divergir do diagnóstico de 12/09, **vale este pack** — ele é mais novo e reabriu as linhas. Onde o executor divergir deste pack, **vale o executor** (§5① do protocolo: o BLOCO 0 remede e o número dele vence).

---

## 1. Fontes canônicas inspecionadas

| fonte | o que aproveitar | o que **não** transportar sem conferir |
|---|---|---|
| `CLAUDE.md` §5, §7, §9.1–§9.5, §12.1 | proibição de motor paralelo · multi-tenant · "teste que chama o regex guarda o regex" · dialeto de regex · "casar a tela não é responder certo" · marcação 📊/💭 | o caminho de worktree de um exemplo |
| `docs/canon/PROTOCOLO-AUTOBROKERS-AAA.md` §0–§3, §5, §7.3 | EXECUTION CARD · O ELO · a regra do comando · a dieta do pacote · o laço · as referências externas | não reescrever o protocolo para baratear esta SPEC |
| `docs/canon/GLOSSARIO.md` | **corredor** ≠ **portal** ≠ **RAG** ≠ **Atlas**. Esta SPEC é só **corredor** | — |
| `docs/canon/specs/SPEC-083-a-regua-do-corredor.md` §2.4 #5, §2.4 (bloco "as teclas têm TRÊS origens") | 🔴 a regra "**toda tecla `_opcao` tem origem** — o dict do subserviço · `_derivar_teclas_do_caso` · as derivações inline de `new_dispatch_session`" | ⚠️ as **linhas** citadas lá envelheceram: `:490` diz `insurer_dispatch_service.py:391`, e hoje é **`:394`**; `:486` cita `corridor_playbooks.py:225` como `confirmar_telefone`, e **não é mais** |
| `docs/canon/specs/SPEC-085-o-destravamento-nao-trava-em-silencio.md` | a doutrina de honestidade do handoff (BLOCO C) e a inversão que o painel pegou (`foi_humano`) | 🔴 **o diagnóstico atribui `registrar_ato_do_agente` a "SPEC-085 C.3". É falso.** `grep -rn "registrar_ato_do_agente" docs/` → a única SPEC que a cita é **SPEC-093-B**, `:288`. O C.3 da 085 é `guardar_a_verdade_do_handoff` |
| `docs/canon/specs/SPEC-087-a-tela-que-o-corredor-nao-conhece.md` | `tela_cega` — a fila de telas desconhecidas | ⚠️ ela tem **escritor e não tem leitor** (P-264). Não criar a irmã dela aqui |
| `docs/canon/specs/SPEC-092-o-formulario-dentro-do-whatsapp.md` | `native_flows` (HDI e Yelum) | Porto e Azul **não têm schema** (P-PILOTO-05) |
| `docs/canon/FOUNDER-DECISIONS.md` linhas D-PILOTO-05, 08, 10, 14, 20 | decisões que **não se reabrem** | — |
| `docs/canon/PENDENCIAS.md` — **só** P-PILOTO-05 (`:10508`) e P-PILOTO-06 (`:10511`) | o que destrava cada uma | ⛔ não ler o arquivo inteiro (562 KB) |
| `docs/canon/specs-propostas/SPEC-EXTRA-001-operacao-dos-pilotos.md` + RP | o **formato** da proposta e do pack | não é prova de que a EXTRA-001 entregou tudo que desejava |

---

## 2. Achados no código — **todos reabertos em 13/09**

> As linhas são coordenadas de `a0bb5fe`, não contratos permanentes. Reencontre o **símbolo**, leia a função inteira e os chamadores.

### 2.1 🔴 A DERIVAÇÃO DE TECLAS — o achado que multiplica o defeito por 29

| ID | evidência | consequência |
|---|---|---|
| **R01** | `insurer_dispatch_service.py:394` — `def _derivar_teclas_do_caso(slots: dict) -> None`. 📊 **MEDIDO HOJE:** corpo de **:394 a :1019** (625 linhas), por `ast.FunctionDef.lineno/end_lineno` | é uma função só, um `if` por tecla; não é mapa genérico, não é por passo, não é por seguradora |
| **R02** | 📊 **MEDIDO HOJE:** ela escreve **26 chaves**, das quais **23 são `*_opcao`**. Comando: `ast.walk` sobre a `FunctionDef`, colhendo `ast.Assign` com alvo `Subscript(Name('slots'), Constant)` | a SPEC-083 e a `PENDENCIAS.md:7179` falam em "25 teclas" — **número vencido** |
| **R03** | 📊 **MEDIDO HOJE:** **um só chamador de produção** — `insurer_dispatch_service.py:1084`, dentro de `new_dispatch_session` (`:1022-1188`). Comando: `grep -rn "_derivar_teclas_do_caso" backend/` (os outros 4 hits são testes) | tudo passa por um ponto. Bom para o conserto |
| **R04** | 📊 **MEDIDO HOJE:** duas teclas nascem **inline**, fora da função: `telefone_adicionar_opcao` (`:1066`) e `servico_opcao` (`:1094`, via `setdefault`). Varredura AST de todas as outras `FunctionDef`: são **as únicas duas** | confirma a "terceira origem" da SPEC-083 |
| **R05** 🔴 | 📊 **MEDIDO HOJE:** carregando `_PLAYBOOKS` por `importlib` e extraindo `{slot}` de `reply` + `requires` dos **805 passos** dos **14 corredores**: **52 slots `*_opcao` são exigidos · 23 derivados · 29 ÓRFÃOS** | o diagnóstico viu **1** (`qual_seguro_opcao`). São 29 |
| **R06** | 📊 **MEDIDO HOJE:** o inverso — `set(derivados) − set(usados_em_passos)` = **vazio**. Toda tecla derivada tem dono | não há derivação morta |

**Os 29 órfãos, com quem os exige** (📊 medido hoje):

```
qual_seguro_opcao            allianz-residencial
tipo_servico_opcao           allianz-resid · hdi-resid · yelum-resid
veiculo_opcao                azul · hdi-auto · hdi-resid · porto-auto · porto-resid · yelum-auto · yelum-resid
servico_opcao                alfa · allianz · azul · bradesco · hdi · yelum · zurich (auto)
eletrodomestico_opcao        allianz-resid · hdi-resid · yelum-resid
telefone_adicionar_opcao     alfa-auto · allianz-auto · allianz-resid
servico_pos_aviso_opcao      hdi-auto · yelum-auto
equipamentos_troca_opcao     alfa-auto · allianz-auto
chaveiro_porta_opcao         hdi-resid · yelum-resid
geladeira_medicacao_opcao    hdi-resid · yelum-resid
alavanca_travada_opcao · cambio_opcao · pane_opcao · pneus_danificados_opcao      zurich-auto
assunto_opcao                mapfre-auto
periodo_opcao                azul-auto
caixa_litros_opcao · caixas_dagua_quantidade_opcao · chave_tipo_opcao ·
  chaveiro_necessidade_opcao · eletrodomestico_categoria_opcao · endereco_opcao ·
  idade_aparelho_opcao · profissional_opcao                                      allianz-resid
chaveiro_alvo_opcao · encanador_instalacao_opcao · encanador_tipo_opcao ·
  fechadura_tipo_opcao · horario_opcao                                           porto-resid
```

**Atenuantes conferidos** (📊 medido hoje): `servico_opcao` e `telefone_adicionar_opcao` nascem inline; `tipo_servico_opcao`, `profissional_opcao`, `eletrodomestico_categoria_opcao`, `eletrodomestico_opcao` e `outro_servico_opcao` têm **constante por subserviço** no dict `subservices` (`corridor_playbooks.py:1048-1049, 1123-1124, 1187-1189, 1240-1241, 1299-1300, 1321-1322, 1331, 1347-1348, 3936-3940, 4496-4502, 5603-5606, 7205-7206, 7216-7217`). **Os demais dependem só da atendente** — e passo sem slot fica **calado** (a família dos 2 min 22, documentada em `insurer_dispatch_service.py:398-403`).

### 2.2 O passo do defeito e a estrutura real de um passo

```python
# corridor_playbooks.py:370-375   (allianz-residencial-whatsapp@v1)
"step": "menu_qual_seguro_tres_opcoes",
"anchor": r"qual seguro deseja utilizar\?...",
"reply": "{qual_seguro_opcao}",
"requires": ["qual_seguro_opcao"],
"fallback_adaptive": True,
```

⚠️ **R07 — a nomenclatura do diagnóstico não bate com o código.** Não existem chaves `match`, `send` nem `capture_anchors` em passo. 📊 **MEDIDO HOJE** por `Counter` sobre as chaves dos 805 passos:

```
step 805 · anchor 805 (é o "match") · reply 805 (é o "send") · notes 758 · noop 231 ·
fallback_adaptive 228 · requires 189 · only_subservices 147 · constante_justificada 94 ·
sem_chute 18 · reply_repeat 10 · dynamic 9 · reply_if_step_done 6 · referral 2 ·
outcome 2 · format 1
```

`capture_anchors` é chave de **playbook** (`:1392`, `:1982`), não de passo. As 23 chaves de playbook: `capture_anchors, channel, client_instructions, client_instructions_por_subservico, coverage_guardrails, description, expectativa_do_desfecho, finalize_abort_reply, finalize_anchors, handoff_triggers, human_phase_guidance, insurer_contact_ref, insurer_key, line_kind, native_flows, opening_template, playbook_id, regras_para_o_cliente, subservice_labels, subservice_menu_map, subservices, unknown_step_policy, ura_steps, version`.

**R08 — `enters_human_phase` NÃO EXISTE.** 📊 `grep -rn "enters_human_phase" backend/app/` → **0**. A chave é nova.

**R09 — `noop` já existe e o motor já o trata.** `insurer_dispatch_service.py:2628-2631`: reconhece a tela e **não responde**. É o ponto exato onde a chave nova acrescenta uma linha.

**R10 — passos por corredor** (📊 medido hoje, soma 805):
porto-auto 88 · yelum-auto 88 · hdi-auto 87 · hdi-residencial 80 · allianz-residencial 75 · porto-residencial 74 · yelum-residencial 74 · zurich-auto 58 · azul-auto 54 · allianz-auto 38 · bradesco-auto 36 · alfa-auto 34 · mapfre-auto 13 · tokio-auto 6.

### 2.3 🔴 O PARSER DE MENU JÁ EXISTE — e o corredor nunca o importou

| ID | evidência | consequência |
|---|---|---|
| **R11** | `cartographer.py:221` — `_NUMERADA = re.compile(r"(?:^\|\n)\s*(\d{1,2})\s*[-–.)\]]\s*([^\n\|]{2,80})")` | é exatamente o parser de menu numerado que o bloco B precisa |
| **R12** | `cartographer.py:357` `parse_options(text)` — três formatos: `Botão N:` da Evolution (`:382`), menu numerado via `_NUMERADA` (`:386`), e **listas nuas** (`:397+`, ramo "palpite") | 🔴 o ramo de palpite é documentado em `:232-244` como **produtor de invenção**. Tem de ficar desligado |
| **R13** | `cartographer.py:587` `numero_da_opcao(label)` · `:593` `classify_screen` · filtros `_NOTA_DE_PESQUISA` `:575`, `_PROTOCOLO_COMO_OPCAO` `:583`, `_NAO_E_OPCAO` `:519` · normalizador "tira o número da frente" `:499` e gêmeo em `atlas/weaver.py:106-109` | tudo pronto |
| **R14** | `atlas/weaver.py:143-161` — casamento aproximado rótulo↔opção (por número e por texto sem acento/pontuação, `_chave` em `:557`); `compute_coverage` `:513` | o "rótulo mais próximo" da Regra A |
| **R15** 🔴 | 📊 **MEDIDO HOJE:** `grep -n "cartographer" backend/app/services/dispatch_router.py backend/app/services/insurer_dispatch_service.py` → **zero**. Todos os consumidores de `parse_options`/`classify_screen`/`numero_da_opcao` são de **mapeamento/Atlas** (`atlas/templater.py:1600,1618,1620`, `atlas/weaver.py:143,151,161`, `cartographer_runner.py:83,162,230`) | **o produto já tem o parser; ele mora no Atlas e nunca foi ligado ao corredor.** Escrever um segundo seria motor paralelo (CLAUDE.md §5) |
| **R16** | 📊 **MEDIDO HOJE:** `grep -rniE "difflib\|SequenceMatcher\|fuzz\|levenshtein\|mais_proximo\|closest" backend/app/` → o único `difflib` é `research/monitor_service.py:22,107`, sem relação com URA | não há fuzzy match no caminho do corredor |

### 2.4 A FASE HUMANA — as três portas que `needs_human` fecha

| ID | evidência | consequência |
|---|---|---|
| **R17** 🔴 | `insurer_dispatch_service.py:2908-2910`: `# Sem âncora de URA: fase humana da seguradora.` / `if session.get("state") == "ura": session["state"] = "human_phase"`. 📊 **MEDIDO HOJE:** `grep -rn '\["state"\] *= *"human_phase"' backend/app/ --include=*.py \| wc -l` → **1** | a transição é por **exclusão** e só de `"ura"`. **Não existe caminho `needs_human → human_phase`** |
| **R18** | `dispatch_router.py:2923-2925`: `if (state == "human_phase" and human_reply_provider is not None and session.get("pending_insurer_messages") and not ainda_vem_mais and not _ja_respondeu):` | o Cérebro **exige** a fase. É a 2ª porta |
| **R19** | `dispatch_watchdog.py:49-50` `_TERMINAL_STATES = {"test_aborted","needs_human","monitoring","captured","encaminhado","resolvido"}` + `:72-74` `if state in _TERMINAL_STATES: return None` | saída **seca**: nenhum diagnóstico, nenhum alerta. É a 3ª porta |
| **R20** | ⚠️ `_TERMINAL_STATES` (Vigia) **≠** `FASES_ENCERRADAS` (`insurer_dispatch_service.py:138`, que é `("needs_human","test_aborted","encaminhado","resolvido")`). O Vigia acrescenta `monitoring` e `captured` | duas listas para o mesmo conceito. **HIPÓTESE:** a divergência é intencional; confirmar no BLOCO 0 |
| **R21** | `resumo_analista` **não é função** — é ramo de `handle_insurer_message` (assinatura em `:2439-2446`), em `:2911-2927`. Quatro condições: `state=="human_phase"` · `not session["summary_sent"]` · `playbook["opening_template"]` existe · regex casa o texto normalizado (`_norm_text`, `:2939-2949`): `me chamo \|meu nome [ée] \|como posso (?:te )?ajudar\|darei? (?:continuidade\|prosseguimento)\|prosseguirei com o atendimento\|irei realizar seu atendimento\|vou te ajudar`. Emite por `_emit` com `render_opening_message` (`corridor_playbooks.py:8384`) | **o "uma vez" já existe** (`summary_sent`, `:2925-2926`). ⚠️ é flag de **sessão** (Redis): sessão nova = resumo novo. 🔴 **E a regex de `:2915-2919` é uma SEGUNDA âncora, mais ESTREITA que `APRESENTACAO_HUMANA`** (`zonas_do_acervo.py:216`): não tem o `` obrigatório em `sou`, não tem o `(?!segurad\|terceir\|…)` que exclui rótulo de menu, não tem `estou assumindo`, e **não tem o controle negativo do robô**. Consequência: uma sessão pode **reentrar** pela tabela e **não emitir o resumo** porque a inline não casou — o caso da Vivian mudo por outro motivo. **Uma fonte só: `:2915` passa a chamar `tem_apresentacao_humana`** |
| **R22** | `insurer_closed` — `insurer_dispatch_service.py:2544-2553`, **regex inline, sem constante nomeada**. Cobre: `conversa ser[áa] encerrada` · `estamos encerrando (?:esta\|a) conversa` · `tempo m[áa]ximo de espera.*excedid` · **`encerrad[ao] por (?:inatividade\|falta de intera)`** · `falta de intera[çc][ãa]o esta conversa foi encerrada` · `conversa foi encerrada`. Efeito em `:2551-2552` | 🔴 ver **R40**: a frase do diagnóstico **não existe** no corpus, e a variante que existe **já é coberta** |
| **R23** | `build_human_phase_messages` — `:3019-3020`, puro. Slots-padrão marcados "o cliente NÃO confirmou" (`:3037-3048`) · histórico = **últimos 6 turnos** (`:3086-3087`) · pendentes = últimos 3 fora da tela (`:3060-3061`) · lê `playbook["human_phase_guidance"]` (`:3164`) | **nenhum campo diz "a última resposta foi recusada"**. É onde entram os dois campos da Regra A |
| **R24** | `guard_human_phase_reply` — `:3296-3349`. Recusas na ordem: vazio `:3320` · `SEM_RESPOSTA` sem mensagem `:3324-3330` · `SEM_RESPOSTA` com tela pedindo algo `:3331-3333` (`_tela_pede_alguma_coisa`, `:3276-3293`) · silêncio legítimo `:3334` · `NAO_SEI` `:3336` · **`len > 400`** `:3338` · "protocolo" sem captura `:3341` · dígitos ≥5 fora dos slots `:3346-3348` (`_digit_runs`, `:3250`). `MOTIVOS_DE_REDACAO` `:3271-3272` × `MOTIVOS_DE_RECUSA` `:3273` | o guarda é **puro**; quem refaz é o router: **uma** retentativa com `_PEDIDO_DE_ENCURTAR` (`dispatch_router.py:215-220`, "no maximo 200 caracteres") em `:3010-3062`; 2 falhas → `needs_human` com `reason=f"human_phase_guard:{…}"` (`:3079-3082`) |
| **R25** | `responder_da_ficha` — `:1396-1442`. `ok=False` com motivo em `{vazia, decisao, nao_e_pergunta, nao_reconhecida, sem_dado_na_ficha}` (`:1405-1407`); **`sem_dado_na_ficha` para o laço** (`:1436-1441`) e vira `session["falta_para_a_ura"]` (`:2901-2906`). Chamada em `:2892`, **antes** da virada de fase | 🔴 **é o gatilho pronto** da "pergunta ao segurado". Não se inventa detector novo |
| **R26** | Estados do dispatch — `DISPATCH_STATES` em **`:60-71`** (10): `preparing, ready_to_send, ura, human_phase, captured, monitoring, encaminhado, resolvido, test_aborted, needs_human`. `_ORDEM_DAS_FASES` `:105-116` · `FASES_EM_VOO` `:119` · `STATUS_WORK_RUN_POR_FASE` `:146-159` (`human_phase → running` `:150`; `needs_human → waiting_input` `:153`) · TTL `_JANELA_DE_VIDA_SEGUNDOS`/`_JANELA_PADRAO_SEGUNDOS = 6h` `:163-164` | o TTL de 6 h importa no canário: sessão órfã continua viva |

### 2.5 O VIGIA e os relógios

| ID | evidência |
|---|---|
| **R27** | ⚠️ **o arquivo é `backend/app/tasks/dispatch_watchdog.py`**, não `app/services/`. O diagnóstico erra o caminho; as linhas conferem |
| **R28** | `:31-38` — `URA_UNANSWERED_S = 30` · `URA_SILENT_ALERT_S = 120` · `HUMAN_NUDGE_S = 600` · `HUMAN_ALERT_S = 1200` · `NEVER_STARTED_S = 300` · `SESSION_DEADLINE_S = 45*60` · `MAX_SENTINELA_ATTEMPTS = 2`. `HUMAN_NUDGE_TEXT = "Oi! Seguimos por aqui no aguardo, tá bom? 🙂"` `:40` |
| **R29** | `:123-130` — em `human_phase`: `in` + idade > 30 s → `stall_unanswered`; `out` + > 1200 s → `human_silent_alert`; > 600 s → `human_silent_nudge`. 🔴 **sem distinguir se alguém já falou** |
| **R30** | 📊 **MEDIDO HOJE:** ciclo do Vigia = **20 s**. `app/tasks/buffer_processor.py:176-182`: `scheduler.add_job(check_dispatch_watchdog, "interval", seconds=20, id="dispatch_watchdog_check", max_instances=1)`. Varredura: `redis.scan_iter(match="dispatch:active:*")` (`:545`) |
| **R31** 🔴 | **`MAX_SENTINELA_ATTEMPTS` é por SESSÃO.** `session["sentinela_attempts"]` lido em `:332` e `:336`; incrementado em **4** pontos (`:375` sem canal · `:384` envio falhou · `:389` sucesso · `:419` "tentativa consumida mesmo sem envio"). 📊 **MEDIDO HOJE:** `grep -rn 'sentinela_attempts.*=.*0\|pop("sentinela_attempts"\|del .*sentinela_attempts' backend/app/` → **0 resultados. Nunca é zerado.** Esgotado → `:421-424` `needs_human` / `sentinela_stall` / dossiê |
| **R32** | `session["silencio_deliberado_ate"]` — escrito em `dispatch_router.py:2986-2988` com `_SILENCIO_S = 60` (`:86`), **lido e honrado pelo Vigia em `:106-116`** | 🔴 **o mecanismo de pausa de 60 s já existe.** Só não há quem o escreva no caminho humano |
| **R33** | `session["step_counts"]` — `insurer_dispatch_service.py:2634`, usado por `reply_repeat` e `reply_if_step_done` | a contagem por passo já existe em espírito |

### 2.6 O humano da corretora, e o registro de atos

| ID | evidência |
|---|---|
| **R34** | `note_manual_outbound` — `dispatch_router.py:2687-2765`. Chamador único de produção: `app/api/webhook.py:2063`, em **todo `fromMe`**; `foi_humano` vem de `e_a_nossa_propria_voz` (`:2732-2747`). Faz 3 escritas (`:2748-2751` transcript · `:2760-2762` marcas · `:2763-2764` save + `_registrar_assuncao_humana`) e **nenhum bloqueio** |
| **R35** | `_registrar_assuncao_humana` — `:2768-2800`: `work_runs.unblock_state = "assumido_por_humano"` só onde está `travado` (`.eq("unblock_state","travado")`, `:2785`) + evento `travamento.assumido` com ator `user` (`:2792-2799`). `ASSUMIDO_POR_HUMANO` `:2684` |
| **R36** | 📊 **MEDIDO HOJE:** não há lease, lock, mutex ou pausa no corredor. `grep -rn "pausa\|pause\|lease\|lock\|takeover" backend/app/services/dispatch_router.py`: `:363`/`:376` são `lease_expires_at` do **Work Run genérico**; `:2137` é comentário sobre lock no supersede; `:2840`/`:2917` são a palavra "pausa" em prosa |
| **R37** 🔴 | **CORREÇÃO AO DIAGNÓSTICO.** `registrar_ato_do_agente` (`dispatch_router.py:997-1027`) **NÃO é código morto.** 📊 **MEDIDO HOJE:** `grep -rn "registrar_ato_do_agente" backend/ --include=*.py` → **11 linhas**, das quais **3 são chamadas reais de produção**: `dispatch_router.py:2967` (Cérebro, 1ª tentativa) · `:3057` (retentativa aceita) · `app/tasks/dispatch_watchdog.py:408` (Sentinela). Grava por `_evento` (`:683-700` → `work_events`), `event_type = f"agente.{agente}"`, `actor_type="agent"`. **A única porta de saída antes do INSERT: `run_id = …` em `:1011`, `if not run_id or not company_id:` em `:1012`, `return False` em `:1013`.** 🔴 **E a hipótese NÃO é refutável por leitura**, porque `_garantir_work_run` (`:597`, `:662`) **preenche** `work_run_id` no caminho normal — pela leitura, o campo deveria estar lá. **Mede-se: quantas sessões chegam a `:2967` com `work_run_id` vazio, e quantas chegam com ele cheio e ainda assim não produzem linha** |
| **R38** | 📊 **MEDIDO HOJE:** `grep -rn 'agente="' backend/app/` → só `cerebro` (×2) e `sentinela` (×1). **`agente="vigia"` nunca é passado**, apesar de `DESTRAVADORES` (`:710`) e `_ATOR_DO_DESTRAVADOR` (`:727-733`) já o preverem |
| **R39** | 📊 **MEDIDO HOJE:** `send_to_client` no roteador — **7** envios reais (`:2667` fila drenada · `:2893` monitoring · `:3091` teste cancelado · `:3126` encaminhamento · `:3163` protocolo · `:3304` dossiê ao grupo · `:3345` aviso de handoff). **Todos avisos; nenhum pergunta e espera.** ⚠️ o diagnóstico diz 8; o 8º hit do `grep` é docstring em `:2826` |
| **R39-bis** 🔴 | ⚠️ **`send_to_client` NÃO É função deste módulo: é um `Callable` INJETADO pelo chamador.** `dispatch_router.py:2652` (`_start_next_in_queue(..., send_to_insurer: Callable[[str], Any], send_to_client: Callable[[str, str], Any])`) e `:2813` (a mesma dupla na assinatura do handler principal) | qualquer função nova que queira falar com o cliente **tem de receber os dois callables e o telefone** — não existe import possível |
| **R39-ter** 🔴 | **e não existe porta de ENTRADA para a resposta do cliente no roteador.** Nenhum handler de mensagem do cliente; as 7 chamadas de R39 são todas de saída | a resposta do segurado chega pelo **caminho do atendimento**; a reentrada tem de ser a satisfação da espera (R39-quater), ⛔ nunca um segundo caminho de entrada |
| **R39-quater** 🔴 | 🔴 **"perguntar, esperar com prazo, resolver na resposta" JÁ EXISTE INTEIRO** — três peças: **abrir** `dispatch_router.py:1614` `_abrir_espera_do_travamento`, que chama `abrir_espera` de `app/services/o_fim_do_atendimento.py` (SPEC-086 BLOCO B, grava `work_waits`, nunca levanta, `UNIQUE` violado = "já esperava") · **vencer** `app/tasks/handoff_watchdog.py:704` (marca `VENCIDO`, com `.eq("company_id")` e `.eq("status","ativo")`) · **resolver** `o_fim_do_atendimento.py:736` e `:748` (`satisfazer_espera`, filtrada por `company_id` e `scope`) | ⛔ **escrever outro é motor paralelo (CLAUDE.md §5).** A §8.3 pendura um `scope` novo (`pergunta_ao_segurado`) nesse motor. O Vigia do dispatch cuida **só do holding** à seguradora |
| **R40** | `_evento` (`:683-700`) é o único INSERT de `work_events` no corredor. `ATORES_VALIDOS = ("system","worker","user","agent","admin","provider")` (`:680`) — é CHECK no banco; `"human"` **não existe**. Outros tipos do corredor: `run.created` `:669` · `travamento.aberto` `:788` · `travamento.destravado` `:813` · `travamento.assumido` `:2793` |

### 2.7 🔴 O CORPUS — e o que ele **não** tem

📊 **TUDO MEDIDO HOJE.** Caminho: `backend/tests/corpus/telas_reais/`, **estrutura plana**, 16 arquivos `.jsonl` (1 tela por linha) + `INDICE.md`. Chaves do registro: `company_id, servico, servico_nivel, session_id, text, wa_timestamp` — `session_id` e `company_id` **truncados em 8 caracteres**.

```
comando: wc -l telas_reais/*.jsonl  +  contagem de session_id distinto por arquivo

alfa-auto 121/8 · allianz-auto 377/19 · allianz-residencial 781/43 · azul-auto 321/9
bradesco-auto 159/10 · hdi-auto 375/13 · hdi-residencial 164/8 · mapfre-auto 75/6
porto-auto 521/19 · porto-residencial 210/9 · tokio-auto 70/7 · tokio-condominio 16/2
tokio-residencial 43/4 · yelum-auto 607/23 · yelum-residencial 186/9 · zurich-auto 253/6
                                                    TOTAL  4.279 telas · 195 sessões
```

| ID | o que se procurou | 📊 o que se achou, com o comando |
|---|---|---|
| **R41** 🔴 | a sessão Allianz de **10/09** | `grep -c '2026-09' *.jsonl` → **0 nos 16**. `wa_timestamp` máximo do acervo: **2026-08-21T12:50:30+00:00**. É o P-PILOTO-06 |
| **R42** ✅ | o menu de três opções | `grep -c "3 - Empresarial" *.jsonl` → allianz-residencial **15** (15 sessões), allianz-auto **1**, resto 0. 🔴 **redação real:** `*1 - Residencial:* Para sua casa ou apartamento individual` — com o asterisco do negrito **antes do dígito** |
| **R43** 🔴 | *"falta de contato"* × *"falta de interação"* — 🔴 **são DUAS frases, e só uma é o defeito** | **CORPUS:** `grep -ic "falta de contato"` → **0 nos 16**; *"falta de interação"* → **17**. **BANCO** (📊 medido em 13/09 na revisão, `observed_events`): `text ilike '%falta de contato%'` → **10 eventos** — allianz **9 em 6 sessões** (até 2026-09-10) + hdi **1** — e **ZERO casam** a regex de `:2544-2549` (rodada como `~*`); *"falta de interação"* → **36**, e **casam**, por `encerrad[ao] por (?:inatividade\|falta de intera)` (`:2548`). ➡️ **A âncora nova é `falta de contato`. A outra nunca foi defeito** |
| **R44** ✅ | *"Vou transferir seu caso para um especialista"* | 📊 **banco 234** · 📊 **corpus 42** (allianz-residencial 31, allianz-auto 11). E *"qual seguro deseja utilizar"*: 📊 **banco 114** · **corpus 16**. ⚠️ 3 falsos positivos vizinhos na allianz-residencial: *"Previsão de chegada do especialista"* — é o **prestador**, já catalogado em `NAO_E_FRONTEIRA` |
| **R44-bis** 🔴 | o TAMANHO do buraco do corpus | 📊 banco: **819 eventos em setembro**, o último em **2026-09-12**. Corpus: `max(wa_timestamp)` = **2026-08-21**. **A distância entre os dois números de R42, R43 e R44 é exatamente esse buraco** — e ela some depois do BLOCO 0-bis |
| **R45** 🔴 | *"Isso pode levar alguns instantes"* | **não existe em nenhuma redação.** `grep -ic "instantes"` → 8: *"podem aparecer depois de alguns instantes"* (porto, 6 — **não é transferência**), *"aguarde alguns instantes"* (hdi, 1), *"em instantes, um de nossos anali…"* (yelum, 1) |
| **R46** | *"meu nome é"* | **3 ocorrências**: hdi-auto 1, zurich-auto 2 |
| **R47** ⚠️ | `INDICE.md` | descreve **1 de 16** arquivos (só `bradesco-auto`), carimbo `2026-08-23T15:19:04+00:00 · commit f156c8c` — foi sobrescrito por uma geração `--seguradora bradesco` |

### 2.8 A RÉGUA e a bateria

| ID | evidência |
|---|---|
| **R48** | `backend/scripts/medir_rota.py` (641 linhas) é a régua. Eixos em `rubrica.py:1-12` (A evidência 20 · **B cobertura 35** · C segurança 26 · D conhecimento · E prova); portões da 089 em `:205-211`; eixo F de travamento `:491`. CLI: `--todas --com-espelho --formato {texto,tabela,markdown} --replay-detalhado --verificar-mutacoes --conferir-ancoras-de-desfecho --exportar-arvore --salvar-linha-de-base --comparar-com` |
| **R49** 🔴 | **trava de `cwd`**, documentada em `:459-481`: rodando da raiz, `tem_banco()` não acha `backend/.env` e **a nota cai parecendo medida**. 📊 conferido hoje de dentro de `backend/`: `tem_banco() = True` |
| **R50** | 📊 **MEDIDO HOJE:** `regua_motor.rotas()` → **73 rotas, 10 seguradoras, 14 playbooks** |
| **R51** 🔴 | 📊 **MEDIDO HOJE:** **não existe linha de base commitada.** `git ls-files \| grep -iE "baseline\|linha_de_base\|INVENTARIO"` → só `docs/canon/reports/INVENTARIO-DE-ROTAS.md` (175 linhas, carimbo `2026-08-24T01:43:13+00:00 · commit 0fbfcd8`, "a régua aplicada às **73**", 543 sessões). O gate de regressão `--comparar-com` **não tem contra o quê comparar** |
| **R52** | `backend/scripts/regua_motor.py:56-57` é o **único ponto do repo** que importa o motor: `match_ura_step = CP.match_ura_step` / `extract_capture_anchors = CP.extract_capture_anchors` (motor em `corridor_playbooks.py:8424` e `:8964`). `replay.py:24` usa o discriminador **do produto**, `_tela_pede_alguma_coisa` (`insurer_dispatch_service.py:1974`) |
| **R53** | 🟠 uma reimplementação **declarada** dentro da régua: `_RX_DESFECHO_MASCARADO` (`medir_rota.py:77-91`), usada só em `--conferir-ancoras-de-desfecho` (`:153`), documentada em `:86-87` como âncora que roda **fora** do `match_ura_step`. Fora dela, o caminho da nota é motor |
| **R54** | `backend/scripts/replay.py` (351 linhas) — `replay(rota, …)` `:156`, `carregar_corpus` `:106-120`, classes RESPONDIDA/NOOP/ORFA_INOCUA/**ORFA_FUNCIONAL**/HANDOFF/CAPTURADA (`:3-20`), `determinismo = respondidas ÷ pedem_algo`. 🔴 filtra por **serviço** dentro da sessão (`:161-174`): sem isso, 📊 20 órfãs em `maquina_de_lavar` onde o esperado é 1 |
| **R55** 🔴 | 📊 **MEDIDO HOJE:** `regua_motor.py:230-238` — **934 respostas de botão têm `text` VAZIO** (yelum 370, hdi 254, porto 165, bradesco 62, azul 54): o `interactive` guardou só as chaves. **A escolha do segurado não está no banco nesses casos.** Outras 1.151 têm `interactive->>'title'` legível. Leitura **paginada** obrigatória (`:222-226`): PostgREST corta em 1000, acervo tem 28.096 eventos |
| **R56** 🔴 | 📊 **MEDIDO HOJE, o runner:** **não é pytest e não há `Makefile`.** O canônico é `python backend/tests/run_all.py` — força `PYTHONIOENCODING=utf-8`/`PYTHONUTF8=1` (`:43-45`), roda cada `test_*.py` em **processo separado**, `TIMEOUT_POR_TESTE = 180` (`:39`). 📊 sem o encoding, *"96 verdes / 8 vermelhos"* vira *"104 verdes / 0 vermelhos"*, e a falha é no `print` de uma seta (`:18-27`). 347 arquivos `test_*.py`; **60 chamam `sys.exit()` em nível de módulo** e o `conftest.py` (171 linhas) existe para isso |
| **R57** | 📊 **MEDIDO HOJE:** a suíte **não usa `assert`** na maioria: o padrão é `checar(cond, texto)` com `sys.exit(1)` (ex.: `test_o_corredor_conhece_a_tela_que_esta_na_frente.py:43-49`). `grep -c assert` **subestima**. 62 arquivos com `def test_`; 172 com `def main` |

### 2.9 🔴 A BATERIA ESTÁ VERMELHA HOJE — e dois dos vermelhos são de dispatch

📊 **MEDIDO HOJE**, de dentro de `backend/`, com `PYTHONIOENCODING=utf-8`.

⛔ **O comando é `python tests/<arquivo>.py`, nunca `pytest`.** 📊 `pytest tests/test_spec017_dispatch.py tests/test_spec031_auto_dispatch.py` devolve **"no tests ran", exit 5** — os dois arquivos têm **zero** `def test_`. Um exit 5 lido como sucesso esconderia as duas falhas:

| teste | exit | tempo | saída literal |
|---|---:|---:|---|
| `test_spec017_dispatch.py` | **1** | 515 ms | `IndexError: list index out of range` em `:158`, depois de `[X] P4: analista humano -> resumo mastigado enviado 1x (fluxo real 01/04/2026): preparing` |
| `test_spec031_auto_dispatch.py` | **1** | 2.771 ms | `IndexError` em `:134`, depois de `[X] dry-run porto ok: {'ok': False, 'error': 'missing_slots', 'missing_slots': ['local_seguro']}` |
| `test_o_corredor_conhece_a_tela_que_esta_na_frente.py` | **1** | 1.270 ms | `VERMELHO — 2 falha(s)`: *"CONTROLE: sozinha, a âncora genérica casaria as TRÊS telas — casou 1 de 3"* e *"o motor NÃO responde ao RESUMO (noop de verdade…) — respondeu: []"* |
| `test_spec038_sentinela.py` | 0 | 1.033 ms | — |
| `test_a_regua_nao_tem_furo.py` | 0 | **71.493 ms** | roda mutações |

🔴 **`test_spec017_dispatch.py` falha exatamente no caminho "analista humano → resumo mastigado", que é o BLOCO D desta SPEC.** **HIPÓTESE, não incidente confirmado:** pode ser regressão de uma das cinco entregas de 08–10/09 que entraram na `main` sem SPEC. **PENDENTE DE MEDIÇÃO:** demonstrar na base e no head, por teste (item 9 do BLOCO 0).

### 2.10 Os testes que a §9.4 do CLAUDE.md condena

📊 **MEDIDO HOJE** (`wc -l` · `grep -c assert` · `grep -cE '\b(check|checar)\('` · chamadas ao motor · regex próprios):

| arquivo | linhas | motor | regex | veredito |
|---|---:|---:|---:|---|
| `test_a_regua_nao_tem_furo.py` | 795 | **21** | 7 | ✅ é o alvo das mutações |
| `test_a_maquina_de_lavar_vai_ate_o_fim.py` | 665 | **18** | 1 | ✅ a rota de referência (§7.1 do protocolo) |
| `test_o_corredor_conhece_a_tela_que_esta_na_frente.py` | 546 | **8** | sim | ✅ guardas diferenciais com linha de controle |
| `test_corredor_residencial_yelum.py` | 517 | 10 | 5 | ✅ |
| `test_o_negrito_da_seguradora_nao_emudece_o_corredor.py` | 406 | 9 | 7 | ✅ — e o nome dele é o aviso sobre o `*` do menu |
| `test_a_tela_cega_vira_fila.py` | 668 | 3 | 0 | ✅ (pytest de verdade, 58 asserts) |
| `test_spec017_dispatch.py` | 425 | 3 | 0 | ✅ |
| **`test_spec038_sentinela.py`** | 110 | **0** | 0 | 🔴 **ZERO motor — e o Sentinela é peça dos blocos B e C** |
| **`test_a_cobertura_tem_lastro_no_acervo.py`** | 254 | **0** | **7** | 🔴 zero motor, 7 regex próprios — o padrão exato que §9.4 condena |

⚠️ `backend/scripts/detector_do_eixo_e.py:62` já existe **para detectar isso** e já lista `match_ura_step`/`extract_capture_anchors`/`detect_finalize_anchor` como as chamadas obrigatórias. 📊 Não existe **nenhum** teste com `vigia` no nome.

### 2.11 Os riscos adjacentes, confirmados

| ID | evidência |
|---|---|
| **R58** ✅ | `corridor_playbooks.py:3269` (azul-auto): `{"step": "menu_atendimento", "anchor": r"de que atendimento voc[êe] precisa", "reply": "1"}` — sem `requires`, sem `fallback_adaptive`. O `constante_justificada` `:3270-3271` **reconhece o risco por escrito**: *"'Cancelar serviço' é a opção 1 em uma das variantes: tecla errada aqui CANCELA um serviço já aberto."* 🔴 **E a porto usa a âncora literalmente idêntica com `reply: "Novo serviço"`** (`:2250`). 📊 nota adjacente medida em 23/08 no próprio arquivo (`:3276-3279`): a variante numerada desse corredor tem **zero ocorrências desde 26/12/2025** |
| **R59** ✅ | 📊 **MEDIDO HOJE:** `porto-auto-whatsapp@v1` é o **único** corredor com dois passos `complemento`: `:2294` (corpo, `reply: "não tem"`, constante) e `:4749` (`_PORTO_TRONCO`, `reply: "{local_complemento}"` + `fallback_adaptive`). Concatenação em `:4851-4853` põe o corpo primeiro (índices **11** e **39**); `match_ura_step` (`:8424-8436`) devolve **o primeiro que casa**. 🔴 **o passo que leria o complemento real é código morto em porto-auto** |
| **R60** 🔴 | 📊 **MEDIDO HOJE, e não está no diagnóstico:** `hdi-residencial-whatsapp@v1` tem **5 pares homônimos** — `quando_agora`, `identificacao_dado`, `desambiguacao_veiculo_ou_residencial`, `menu_servico_residencial`, `servico_ja_aberto` — vindos da concatenação de `:4956-4958`, que anexa os `ura_steps` inteiros da yelum-residencial aos da hdi |
| **R61** | `native_flows` só em HDI e Yelum auto (`corridor_playbooks.py:2982, 3010`) — P-PILOTO-05 |
| **R62** | 📊 **MEDIDO HOJE:** existem `tokio-residencial.jsonl` (43 telas / 4 sessões) e `tokio-condominio.jsonl` (16 / 2) e **`rotas()` não produz rota tokio residencial/condomínio** — 59 telas que a régua nunca mede |

### 2.12 O guarda de hoje, e por que ele é cego

`backend/tests/test_a_tecla_tem_a_forma_da_seguradora.py` (239 linhas; é script com `sys.exit`, não pytest).

📊 **MEDIDO HOJE:** `PYTHONIOENCODING=utf-8 python tests/test_a_tecla_tem_a_forma_da_seguradora.py` → última linha **`12 assercoes verdes - 0 vermelhas`** — **com o defeito vivo**.

```
:92-130   valores_derivados()  — AST da FunctionDef `_derivar_teclas_do_caso`, colhendo
          todos os ast.Constant string dentro de cada Assign em slots["*_opcao"].
          O comentário :98-108 explica que a versão por regex perdia atribuições
          quebradas em duas linhas
:78-86    convencao_do_corredor() — conta replies constantes numéricos × rótulo e decide
          por MAIORIA. A convenção é MEDIDA, não escrita
:133-138  donos() — varre `requires` e `reply == "{slot}"` de todos os corredores e acha
          quem exige um slot.  🔴 ELA EXISTE E SABE FAZER O QUE FALTA
:141-151  conflitos() — o laço. E é aqui que mora a cegueira
:143      for slot, vals in sorted(valores.items())    ← PARTE DOS DERIVADOS
:146-147  if not ds: continue                          ← descarta derivado-SEM-dono
:154      VALORES = valores_derivados()                ← o universo é só o que a derivação escreve
:160      len(VALORES) >= 15                           ← hoje 23: toleraria apagar 8 derivações
```

🔴 **Não existe o simétrico `dono-sem-derivação`.** `qual_seguro_opcao`, ausente de `VALORES`, nunca entra em `:143`, logo `donos()` nunca é perguntada sobre ele. **O guarda afere a FORMA de teclas que existem; ausência de tecla não é forma errada, é forma nenhuma.** O conserto é inverter o laço — e a peça necessária (`donos()`) já está escrita.

---

## 3. O que continua desconhecido

1. **Por que `registrar_ato_do_agente` grava 0 linhas**, tendo 3 chamadores (R37). A hipótese do `work_run_id` vazio (`:1011-1013`) é **hipótese**, não medição. ⛔ Bloqueia o bloco D6.
2. ~~Qual é a redação real da frase de encerramento de setembro~~ — **RESOLVIDO em 13/09 pela revisão** (R43): é `falta de contato`, 10 eventos, 0 casam. O §8.5 da proposta deixou de depender do BLOCO 0.
3. **Os números do banco herdados do diagnóstico** — 114 transferências da Allianz / 50 atendentes / 59 % < 10 s / mediana 3 s / p90 10,5 min / máx 49 min; 56 encerramentos por inatividade com Porto 95 s e Allianz 103 s; 9 mensagens em 6 sessões; 28.096 eventos; 0 linhas de `agente.*`. **📊 HERDADOS, não reproduzidos aqui.**
4. **Se `parse_options` devolve 0 opções no texto cru do menu da Allianz** (previsão: sim). Não rodei o parser sobre a tela.
5. **Se os 3 testes vermelhos são pré-existentes ou regressão** das entregas de 08–10/09.
6. **Se os 5 pares homônimos da hdi-residencial mudam a resposta** ou são ruído idêntico.
7. **Se `work_events.event_type` tem CHECK** que recuse `agente.vigia`.
8. ~~Se `work_waits` tem leitor~~ — **RESOLVIDO** (R39-quater): tem, e são três (`:1614` abre · `handoff_watchdog.py:704` vence · `o_fim_do_atendimento.py:736,748` resolve). **O que falta medir é outra coisa:** se a linha de `work_waits` carrega `insurer_phone` (ou algo que o derive), para o gancho de reentrada achar a sessão. Se não carregar, é **um campo**, não uma tabela.
9. **Quantas das telas de 10/09 caem nas 934 respostas de botão com `text` vazio** (R55) — afeta a fidelidade do replay de gate.
10. **Se `_TERMINAL_STATES` (Vigia) e `FASES_ENCERRADAS` (motor) divergem de propósito** (R20).

---

## 4. Roteiro de remedição — leitura antes de edição

> Comandos para o **futuro executor**. Não são saídas já obtidas, exceto onde marcado 📊 MEDIDO HOJE no §2.

```bash
# ── preflight (CLAUDE.md §2) ──────────────────────────────────────────────
git fetch origin
git rev-list --count HEAD..origin/main      # TEM de ser 0
git rev-list --count origin/main..HEAD      # o que ainda não subiu
git branch --show-current ; git rev-parse HEAD ; git status --short

# ── a partir daqui, SEMPRE de dentro de backend/ e com utf-8 ──────────────
cd backend && export PYTHONIOENCODING=utf-8

# ── ① a derivação e os órfãos ─────────────────────────────────────────────
grep -n "def _derivar_teclas_do_caso" app/services/insurer_dispatch_service.py
grep -rn "_derivar_teclas_do_caso" . --include=*.py
python - <<'PY'
import ast, importlib, sys
sys.path.insert(0, ".")
src = open("app/services/insurer_dispatch_service.py", encoding="utf-8").read()
fn = next(n for n in ast.walk(ast.parse(src))
          if isinstance(n, ast.FunctionDef) and n.name == "_derivar_teclas_do_caso")
derivados = {t.slice.value for a in ast.walk(fn) if isinstance(a, ast.Assign)
             for t in a.targets
             if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
             and t.value.id == "slots" and isinstance(t.slice, ast.Constant)}
import re
CP = importlib.import_module("app.services.corridor_playbooks")
usados = set()
for pb in CP._PLAYBOOKS.values():
    for s in pb.get("ura_steps", []):
        usados |= set(re.findall(r"\{(\w+_opcao)\}", str(s.get("reply") or "")))
        usados |= {r for r in (s.get("requires") or []) if r.endswith("_opcao")}
print("usados", len(usados), "derivados", len({d for d in derivados if d.endswith('_opcao')}))
print("ORFAOS", sorted(usados - derivados))
PY

# ── ② o parser de menu, sobre a tela REAL, nas duas normalizações ─────────
grep -n "_NUMERADA\|def parse_options\|def numero_da_opcao" app/services/cartographer.py
grep -n "cartographer" app/services/dispatch_router.py app/services/insurer_dispatch_service.py  # espere 0
grep -o -m1 -E ".{0,240}3 - Empresarial.{0,40}" tests/corpus/telas_reais/allianz-residencial.jsonl

# ── ③ a fase humana e os relógios ─────────────────────────────────────────
grep -rn '\["state"\] *= *"human_phase"' app/ --include=*.py       # espere 1
sed -n '2540,2560p;2900,2935p;3290,3350p' app/services/insurer_dispatch_service.py
sed -n '28,52p;70,80p;118,135p' app/tasks/dispatch_watchdog.py
grep -rn 'sentinela_attempts' app/                                  # nenhum reset
grep -n "seconds=20\|dispatch_watchdog_check" app/tasks/buffer_processor.py

# ── ④ o registro de atos — O ELO ──────────────────────────────────────────
sed -n '995,1030p' app/services/dispatch_router.py                  # leia até o INSERT
grep -rn "registrar_ato_do_agente" . --include=*.py
grep -rn 'agente="' app/                                            # espere cerebro, sentinela

# ── ⑤ o acervo (corpus) ───────────────────────────────────────────────────
wc -l tests/corpus/telas_reais/*.jsonl
grep -c '2026-09' tests/corpus/telas_reais/*.jsonl                  # hoje: 0 nos 16
grep -ic "estou encerrando\|falta de contato\|falta de intera" tests/corpus/telas_reais/*.jsonl
grep -ic "vou transferir seu caso" tests/corpus/telas_reais/*.jsonl

# ── ⑥ a bateria e a régua ─────────────────────────────────────────────────
python tests/test_a_tecla_tem_a_forma_da_seguradora.py
python tests/test_spec017_dispatch.py ; echo "exit=$?"
python tests/test_spec031_auto_dispatch.py ; echo "exit=$?"
python tests/test_o_corredor_conhece_a_tela_que_esta_na_frente.py ; echo "exit=$?"
python scripts/medir_rota.py --todas --com-espelho --formato tabela
python tests/run_all.py                                             # a bateria inteira
```

**Antes de qualquer SQL:** ler `docs/canon/MIGRATIONS-AUTHORITY.md`. As consultas do BLOCO 0 são **SELECT e só contagens** — ⛔ nunca conteúdo de mensagem, nunca CPF, telefone, placa ou nome.

### Censo mínimo que a SPEC definitiva precisa registrar

| medição | forma de evidência | ⛔ não concluir |
|---|---|---|
| órfãos da derivação | o AST acima, rodado hoje | "o defeito era um slot" |
| parser sobre o menu real | duas chamadas, cru e normalizado | "o parser funciona" sem dizer com que texto |
| por que `agente.*` = 0 | leitura da linha 997 até o INSERT + `SELECT ... GROUP BY` | "ninguém chama" (é falso, R37) |
| a frase de encerramento | a consulta de R43, **com a linha de controle** (a mesma regex `~*` sobre os mesmos 10 eventos) | que `falta de interação` e `falta de contato` são a mesma frase (R43) |
| os dois relógios | a consulta do §11.4 reproduzida | usar o número do diagnóstico sem remedir |
| a bateria vermelha | um veredito **por teste**, na base e no head | "pré-existente" como rótulo coletivo |
| régua sem regressão | `--salvar-linha-de-base` **commitada** e `--comparar-com` | comparar com um número lembrado |
| isolamento | duas corretoras, mesma seguradora, uma em pausa | service role dispensa filtro |

---

## 5. Pendências herdadas — drenar só se tocadas

`P-PILOTO-05` (`PENDENCIAS.md:10508`) e `P-PILOTO-06` (`:10511`) são as duas que esta SPEC absorve. Dar estado **FECHADA / CONTINUA / MORREU** com evidência.

Citadas como **elo**, não absorvidas: `P-264` (`tela_cega` com escritor e sem leitor — SPEC-087) · `P-PILOTO-01` (isolamento por corretora → EXTRA-001.8) · `P-PILOTO-12` (a régua de língua não roda nos dossiês → 001.3).

---

## 6. Armadilhas que o AQUECIMENTO deve refutar

> Duas delas são **deliberadamente falsas e assinadas** (§5.2 do protocolo). O orquestrador as substitui se deixarem de ser falsas.

1. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA, assinada:** *"`registrar_ato_do_agente` nunca gravou porque ninguém a chama. Basta chamá-la."* — **Refute com o comando.** (R37: três chamadores reais.)
2. 🔴 **AFIRMAÇÃO DELIBERADAMENTE FALSA, assinada:** *"O corpus tem a sessão Allianz de 10/09; basta rodar o replay para reproduzir o `'residência'`."* — **Refute com o comando.** (R41: `grep -c '2026-09'` → 0.)
3. *"O defeito era um slot só (`qual_seguro_opcao`)."* — quantos são, e como você contou?
4. *"É só escrever um parser de menu numerado."* — onde já existe um, e por que não foi usado? (R11–R15.)
5. *"`MAX_SENTINELA_ATTEMPTS = 2` é por tela."* — mostre onde é zerado. (R31: em lugar nenhum.)
6. *"A âncora `insurer_closed` não cobre encerramento por falta de interação."* — leia `:2548` inteira, e diga **qual das duas frases** é o defeito e quantos eventos cada uma tem. (R22/R43.)
7. *"`Isso pode levar alguns instantes` é uma boa âncora de transferência."* — conte no acervo, e diga quantos falsos positivos ela traz na porto. (R45.)
7-bis. *"Para perguntar ao segurado e voltar, preciso de uma fila com prazo. Vou criar uma."* — ⛔ **refute**: nomeie as **três** peças que já fazem isso, por arquivo e linha, e diga qual é o único pedaço que de fato não existe. (R39-quater.)
7-ter. *"`send_to_client` é uma função do `dispatch_router`; é só importá-la."* — ⛔ **refute** pela assinatura, e diga o que a função nova precisa receber. (R39-bis.)
8. *"Dar o texto da tela ao parser é indiferente: cru ou normalizado dá no mesmo."* — meça com o menu da Allianz. (R42; CLAUDE.md §9.4.)
9. *"Pausar o corredor exige um lock novo."* — que campo já existe e o Vigia já honra? (R32.)
10. *"Basta ligar o Vigia de novo depois da reentrada."* — qual linha do Vigia precisa mudar para ele voltar a vigiar? (Nenhuma: R19 olha o **estado**.)
11. *"Todo `fromMe` é um humano digitando."* — o que acontece se o eco da nossa própria voz abrir pausa? (R34, `e_a_nossa_propria_voz`.)
12. *"A bateria está verde; qualquer vermelho é do meu código."* — rode os cinco testes do §2.9 **antes** de escrever uma linha.
13. *"`grep -c assert` mede a cobertura desta suíte."* — quantos arquivos usam `assert`, e qual é o padrão real? (R57.)
14. **Liste o que você NÃO entendeu ou não conseguiu provar.** ⛔ "entendi tudo" reprova.
15. **Ache um defeito material que esta proposta não aponta**, ou diga onde procurou e não achou. Entregue a nota e o card que você aplicaria.

---

## 7. Pesquisa externa — fontes primárias reabertas em 13/09/2026

> As cinco estão desenvolvidas na §16 da proposta, no formato do §7.3 do protocolo (URL · faz · modelamos · rejeitamos · como o juiz inspeciona). Aqui ficam a URL, o ponto e a ressalva de honestidade.

| # | fonte | o ponto que a SPEC usa | ressalva |
|---|---|---|---|
| **E01** | W3C **SCXML 1.0** — https://www.w3.org/TR/scxml/ (§3.5, §3.7, §3.13, §6.2, §6.3) | transição **sem target** (executa ação, não reentra) × transição **para o próprio estado** (sai, reentra, re-executa `onentry`) — é a distinção do bloco B | ⚠️ o texto verbatim de §6.2/§6.3 **não pôde ser capturado** na REC 2015 (a página trunca em §6.1). O comportamento de `delay`/`cancel` foi confirmado no **WD W3C de 2005** (https://www.w3.org/TR/2005/WD-scxml-20050705/). A nota de re-entrada e §3.7 foram lidas na própria REC |
| **E02** | **XState** — https://stately.ai/docs/delayed-transitions · https://stately.ai/docs/transitions | *"Delayed transition timers are canceled when the state is exited"* e `reenter` opt-in | ⚠️ **não existe** na doc oficial um padrão nomeado "invoke com timeout"; o que há é a composição `invoke` + `after`. Não se afirma API que não se viu |
| **E03** | **AWS Step Functions** — https://docs.aws.amazon.com/step-functions/latest/dg/state-task.html | 🔴 `TimeoutSeconds` (absoluto, *"count begins when the start event is executed"*) × `HeartbeatSeconds` (*"Heartbeats prevent an activity or task from timing out"*, *"must be … less than the TimeoutSeconds"*) — **é a fundação dos dois relógios do §8.4** | citações verbatim capturadas |
| **E04** | **Erlang/OTP `gen_statem`** — https://www.erlang.org/doc/apps/stdlib/gen_statem.html | três timeouts com cancelamento diferente: **event** (*"Any event that arrives cancels this time-out"*), **state** (*"A state change cancels this timer"* — e **repetir o mesmo estado não é state change**), **generic nomeado** | Temporal.io **não** foi consultado; o `gen_statem` cobre o ângulo com mais precisão. Se o executor quiser idempotência de replay, é uma rodada nova |
| **E05** | **W3C VoiceXML 2.0** — https://www.w3.org/TR/voicexml20/ · DTD normativa https://www.w3.org/TR/voicexml20/vxml.dtd · NOTE 1.0 §11.2 https://www.w3.org/TR/2000/NOTE-voicexml-20000505/ | 🔴 *"Each form item and `<menu>` maintains a counter for each event… these counters are **reset each time** the `<menu>` or form item's `<form>` is **re-entered**"* — a contagem **por prompt**, e `noinput` ≠ `nomatch` | ⚠️ o corpo verbatim de §5.2 da REC 2.0 **não pôde ser capturado** (a página trunca em §2.3). O ponto vem da **DTD normativa** (verbatim: `count` em `catch`/`nomatch`/`noinput`/`prompt`) e do **§11.2 da NOTE 1.0**, texto ancestral direto |

🔴 **O pesquisador do executor reabre as cinco na conversão e registra a data** (§7.3 do protocolo). Nenhuma vira autoridade: modela-se o padrão (CLAUDE.md §5).

---

## 8. Acompanhamento publicado

Dossiê do Founder: https://claude.ai/code/artifact/afe1510d-f31c-4d13-9441-aa920ad2b868 (aba **Pilotos**).
Fonte versionada: `docs/canon/reports/dossies/dossies-autobrokers.html`.

**Ler o HTML publicado inteiro antes de republicar com `url`**, preservar as páginas existentes, publicar a cada bloco fechado, conferir o resultado no link. Sem ferramenta ou acesso: atualizar a fonte e registrar **"publicação do dossiê pendente"** com o arquivo e o passo exato. ⛔ Nunca alegar atualização não conferida; ⛔ nunca publicar os números de teste completos.

---

## 9. Regra de integridade deste pack

Este documento **não** contém telefone, CPF, nome de segurado, placa, e-mail nem credencial. Os dois números de teste aparecem só como **TESTE-A** e **TESTE-B**. Trechos de tela reproduzidos aqui são **textos de URA** (menu, transferência, encerramento), sem dado de pessoa.

Se o executor emendar este pack, a emenda vai **datada e assinada**, com o comando que a produziu. ⛔ Não "consertar" um número para casar com a proposta: a proposta é que se corrige.

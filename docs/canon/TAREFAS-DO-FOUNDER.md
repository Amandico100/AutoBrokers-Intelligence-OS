# TAREFAS DO FOUNDER — a lista única

> 🔴 **Desde 01/10/2026, os TESTES estão todos na seção logo abaixo (T-01 a T-123).** Os blocos mais antigos, depois dela,
> guardam o contexto, as decisões e as tarefas que não são teste; onde havia um teste, agora há uma seta **→ T-NN**.

## 🗺️ DESDE 04/10/2026: FAÇA PELO ROTEIRO, NÃO POR ESTA LISTA

> **O roteiro** (`ROTEIRO-DE-TESTES-DO-FOUNDER.md`) junta os testes que ainda valem em **poucas sessões**, passo a passo, com
> a frase exata, o que deve acontecer, a caixa ✅/❌ e a hora: **P** preparar · **1** conversa do segurado (celular A) · **V** o
> canário do vidro · **2** conversa do parente (celular B) · **1b** a 2ª parte da conversa 1 · **C** chat principal · **S** o bloco
> de SQL e o resumo das 19h · **F** desfazer. Cada T-NN abaixo diz em que passo ele está. **O inventário** (o porquê de cada
> estado) está em `reports/INVENTARIO-TESTES-DO-FOUNDER-2026-10-04.md`.
>
> 📊 **O placar de 04/10** (103 testes): ✅ **10** feitos (T-01 T-05 + T-02 T-06 T-82 T-91 T-92 T-98 T-99 T-102) · 🗺️ **62**
> atrasados **no roteiro** · ⏸ **23** atrasados **fora** dele (acionamento até o protocolo, 2ª corretora de teste, equipe,
> cobrança, vida real) · 🔁 **5** cobertos · ⚰️ **2** mortos · 🔭 **1** futuro. **Depois do placar** (fechador, 04/10):
> **T-104** (decisão: religar o DEDUZIR do portal na Yelum) e **T-105** (a vistoria pelo celular, roteiro V9.1–V9.3). **Depois da
> SPEC-128** (04/10): **T-106 a T-113**, o programa multicálculo (grupo ⑩) — decisões e conferências, nenhum é teste de celular.
> **Depois da passagem de 05/10** (o Quem Cobra Menos vira WhatsApp, plano A): **T-114 a T-119** — a T-113 foi para a ★. **05/10
> tarde (v2.5.1, a fila intercalada D-MC-61):** a **T-107** está ✅ feita (D-128-03 TOMADA) e nasceu a **T-120** (o login de robô no Agger). **05/10 noite (SPEC-129-B, o motor):** a **T-106** está ✅ feita
> (portão de preço respondido, D-MC-62…65) e nasceram a **T-121** (Implantar), a **T-122** (as 2 variáveis do motor) e a **T-123**
> (Tokio da Resulta + pergunta ao fornecedor); a T-120 ganhou os comandos prontos. 📊 Recontado 05/10 noite (no `docs/canon/`):
> `grep -cE '^- \[ \] \*\*T-[0-9]+' TAREFAS-DO-FOUNDER.md` → **111 pendentes** · `grep -cE '^- \[x\] \*\*T-[0-9]+'` → **12 feitos** (T-01…T-123).
> **06/10 (SPEC-130-A, a comparação e a proposta):** nasceram a **T-124** (Implantar os 3 serviços), a **T-125** (WhatsApp de
> atendimento + SUSEP no cadastro de marca e a marca da AutoFleet), a **T-126** (abrir o link do canário no celular), a **T-127**
> (jurídico da remuneração) e a **T-128** (o recado à Ellen). 📊 Recontado 06/10 com os mesmos comandos → **116 pendentes** · **12 feitos** (T-01…T-128).

## 🧪 A LISTA ÚNICA DOS TESTES (atualizada 03/10/2026 — SPEC-126: T-91 a T-98 · SPEC-127: T-99 a T-103 · fechador 04/10: T-104 T-105 · SPEC-128: T-106 a T-113 · passagem 05/10: T-114 a T-119 · v2.5.1: T-120 · SPEC-129-B: T-121 a T-123 · SPEC-130-A: T-124 a T-128)

> **Para que serve:** é a fila de testes para você fazer **um por um**, ajustar o que não funcionar e, no fim, ligar os
> agentes na vida real. Ela junta **todos** os testes pendentes das SPECs 116 → 127 e das EXTRA-001.1 → 001.10.1, das
> caixas do Founder dos relatórios e das pendências 🧑 de teste/canário/acionamento real. **Esta lista é a verdade**: nos
> blocos antigos mais abaixo, cada teste virou só uma seta **→ T-NN** que aponta para cá.
>
> **Como usar:** siga a ordem dos grupos — cada grupo só depende dos anteriores. Marque `[x]` no que passar. No que falhar,
> cole no chat **o número do teste** (ex.: *"T-43 falhou"*), o horário e o print — nunca o CPF ou o nome de um segurado.
>
> **Status:** ⏳ pendente · ✅ feito · 🗺️ o passo do roteiro onde ele se faz · 🔁 coberto por outro · ⚰️ morreu ·
> ⏸ fora do roteiro · 🔭 futuro. Atualizado em **04/10/2026** pelo inventário (o placar está logo abaixo).
>
> **Onde:** **painel** = `https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host` · **EasyPanel** =
> onde se clica Implantar e se editam as variáveis (o `smith-worker` usa o mesmo bloco do `smith-api`) · **SQL** = Supabase →
> projeto *AutoBrokers Intelligence OS* → **SQL Editor** (todos os SQL desta lista são só leitura, salvo onde está escrito).
>
> 🔴 **Freio de emergência, se algo sair do controle:** `ACIONAMENTO_FREIO_DE_EMERGENCIA=true` no `smith-api` derruba todo
> acionamento. **Se um modelo piorar** (memória, foto, portal): peça no chat *"volte a rota X para a linha anterior"* — vale em
> até 1 minuto, sem Implantar.

**Os 9 grupos, na ordem:** ① Implantar e conferir · ② Chat principal · ③ Atendimento no WhatsApp com o agente ligado ·
④ Acionamento por seguradora · ⑤ Portal de vidros · ⑥ Grupo de suporte · ⑦ Leitura de foto e documento · ⑧ Cobrança ·
⑨ Desfazer o ensaio e ir para a vida real.

### ① Implantar e conferir — não depende de nada

- [x] **T-01** ✅ **Implantar o código de hoje** — `docling-service` (o worker antes da API) → `smith-api` → `smith-worker` →
      `smith-web`. **Feito em 01/10/2026.** Vale por todos os Implantar pedidos antes, porque o Implantar sobe a `main` inteira.
      · *de:* S116.2 · 0.2 · F.1 · G.1 · I.1 · J.1 · S120.1 · S121.1 · S122.1 · S123.1 · S124.1
- [x] **T-82** ✅ **FEITO 03/10** — o Implantar do T-91/T-99 subiu a `main` inteira; 📊 04/10 SELECT: `attendance | v2 | false | 4`. · **Implantar a SPEC-125** (o atendimento que lembra) — EasyPanel, **nesta ordem**: `smith-api` → `smith-worker` →
      `smith-web`. Nenhuma variável nova. Depois, no **SQL**:
      ```sql
      select agent_role, prompt_versao, is_active, count(*) from public.agents
       where agent_role = 'attendance' group by 1, 2, 3;
      ```
      **Esperar:** 📊 (02/10) **uma linha**: `attendance | v2 | false | 4` — os 4 agentes no prompt novo e todos desligados.
      **Se der erro de coluna `prompt_versao`:** a migration não está no banco — me avise, não aplique nada à mão. · *de:* S125.1
- [ ] **T-83** ⏳ ⚰️ **MORREU** — a SPEC-126 já mediu os críticos no Sol (📊 11 de 12); o resto é a T-98 · **Decidir D-125-I: autorizar ~US$ 1,30 de OpenAI para medir o prompt novo no modelo de produção** antes de
      ligar o agente numa corretora de verdade. Se autorizar, peça no chat: *"rode a rodada do Sol da SPEC-125 (P-125-01),
      teto US$ 1,30"*. **Esperar:** uma tabela com os 10 cenários, cada um PASS ou FAIL; os críticos (C6 C7 C10 C13 C15 C16)
      todos PASS. **Se algum crítico falhar:** não ligue o agente ainda; veja o T-90 (voltar ao prompt antigo). · *de:* S125.3 · P-125-01
      ⚠️ **03/10:** a SPEC-126 já mediu os críticos no Sol (📊 11 de 12; o 12º é erro da régua, não do agente). O que falta medir
      agora são os NÃO-críticos — está no **T-98**.
- [x] **T-91** ✅ **FEITO 03/10 pelo Founder** — 📊 04/10 as duas migrations estão em `schema_migrations`. · **Implantar a SPEC-126** (o atendimento quase sem erro) — EasyPanel, **nesta ordem**: `smith-api` →
      `smith-worker` → `smith-web`. As duas migrations **já estão no banco**; nenhuma variável nova. Pode ser o mesmo Implantar do
      T-82 (o Implantar sobe a `main` inteira). Depois, no **SQL**:
      ```sql
      select version, name from supabase_migrations.schema_migrations
       where version in ('20261002202210', '20261002202302') order by 1;
      ```
      **Esperar:** 📊 (03/10) **duas linhas**: `20261002202210 | spec126_u6_deduzir_calibrado` e
      `20261002202302 | spec126_papel_confirmacao`. **Se vier menos de duas:** me avise — não aplique nada à mão. · *de:* S126.1
- [x] **T-92** ✅ **FEITO 03/10 pelo Founder** — `confirmacao | gpt-6-luna | medium | claude-sonnet-5-5 | low` e `on | false | 40` (📊 04/10 confere). · **O "juiz do ok" e o DEDUZIR travado** (SQL, só leitura) — rode os dois, um de cada vez:
      ```sql
      select papel, modelo_primario, esforco, modelo_reserva, esforco_reserva
        from public.llm_papeis where papel = 'confirmacao';
      ```
      **Esperar:** 📊 (03/10) uma linha `confirmacao | gpt-6-luna | medium | claude-sonnet-5-5 | low` — é o modelo que confere se
      o "ok" do segurado é mesmo um ok (e a reserva, se ele cair).
      ```sql
      select modo, deduzir_calibrado, count(*) from public.cerebro_modos group by 1, 2;
      ```
      **Esperar:** 📊 (03/10) uma linha `on | false | 40` — o destravador ligado nas 40 combinações e o "escolher sozinho"
      **desligado** em todas (só religa com prova medida; hoje nenhuma seguradora tem casos suficientes).
      **Se `deduzir_calibrado` não existir:** a migration não está no banco — me avise. · *de:* S126.1 · G7
- [x] **T-98** ✅ **FEITO 03/10** — autorizado pelo Founder; a rodada é do gerente. · **Decidir o orçamento dos testes que ficaram de fora** (decisão sua; nada roda sem você dizer). Cole no chat,
      se autorizar: *"autorizo US$ 1,00 de OpenAI e US$ 0,05 de Anthropic para as pendências P-126-01, P-126-02 e P-126-12"*.
      💭 A conta: Luna de novo k=2 (≈ 0,30, P-126-01) · Sol nos 5 não-críticos (≈ 0,70, P-126-02) · a reserva do "juiz do ok" no
      Sonnet (≈ 0,05 Anthropic, P-126-12) · a calibração do DEDUZIR (WhatsApp e portal) **só depois** de juntar ≥ 10 casos por
      seguradora (P-126-06; hoje 📊 ≤ 5). **Esperar:** uma tabela por cenário, PASS/FAIL, e o gasto lido do ledger.
      **Se não autorizar:** nada quebra; o agente fica com a prova que tem (críticos 12/12 na Luna e 11/12 no Sol). · *de:* S126.4
- [x] **T-99** ✅ **FEITO 03/10 pelo Founder** — `smith-api` e `portal-worker` no ar = `a87b2e7`; build do `portal-worker` 03/10 17:36. · **Implantar a SPEC-127** (o portal de vidros no nível do WhatsApp) — EasyPanel, **nesta ordem**: `smith-api` →
      `smith-worker` → **`portal-worker`** → `smith-web`. 🔴 Desta vez o `portal-worker` **entra** (o robô do portal mudou).
      **Nenhuma migration, nenhuma variável nova.** Pode ser o mesmo Implantar do T-82/T-91. Depois abra
      `https://autobrokers-intelligence-os-portal-worker.golhpm.easypanel.host/health`.
      **Esperar:** `build_time` de **03/10/2026 ou depois**. Se for anterior: Implantar o `portal-worker` de novo (demora mais).
      Nada muda para o segurado ainda: as chaves do portal (T-55) seguem desligadas e 📊 (03/10) 0 de 4 agentes estão ligados.
      · *de:* S127.1
- [ ] **T-100** ⏳ 🗺️ **roteiro P1** (📊 03/10: é a corretora de ensaio que está sem CNPJ — trava o vidro nela) · **Preencher o documento da corretora que falta no cadastro de acionamento** — sem ele, com o caminho novo do
      portal ligado, **todo** pedido de vidro dessa corretora vai à equipe ("falta um ajuste no nosso cadastro"). No **SQL**:
      ```sql
      select company_name,
             coalesce(nullif(acionamento_profile->>'cpf_cnpj', ''), nullif(cnpj, '')) is null as falta_documento,
             coalesce(nullif(acionamento_profile->>'telefone', ''), nullif(primary_contact_phone, '')) is null as falta_telefone
        from public.companies
       where coalesce(nullif(acionamento_profile->>'email', ''), primary_contact_email) is not null
       order by 2 desc, 1;
      ```
      **Esperar:** 📊 (03/10) **3 linhas**; **1** com `falta_documento = true` (a 1ª da lista) e `falta_telefone = false` em todas.
      **O que fazer:** no painel, entre como essa corretora → **Personalização → Corretora** → preencha o **CNPJ** e salve. Rode o
      SQL de novo → `falta_documento = false` nas 3. **Se a corretora não usa o portal de vidros:** pode deixar; só os pedidos de
      vidro dela são afetados. · *de:* S127.1 · P-127-22
- [x] **T-102** ✅ **FEITO 03/10** — autorizado pelo Founder; a rodada é do gerente. · **Decidir o orçamento da bancada do portal** (decisão sua; nada roda sem você dizer). Ela mede se o robô do
      portal pode **escolher sozinho** (peça, causa, cidade) — hoje ele só pergunta (📊 autonomia = 0). Cole no chat, se autorizar:
      *"autorizo US$ 1,00 de OpenAI e US$ 1,30 de Anthropic para a bancada do portal (P-127-04)"*. 💭 A conta (builder P5, com o
      custo por chamada medido na SPEC-123): 32 casos × k=2 → OpenAI ≈ 0,35–0,86 + 2ª opinião Anthropic ≤ 1,27; a Porto **só depois** do T-103 (📊 hoje 5 casos, a regra pede 10). **Esperar:** uma tabela por seguradora com o
      acerto, o n e se religa (≥ 90 %) ou não, e o gasto lido do ledger. **Se não autorizar:** nada quebra; o portal pergunta ao
      segurado em vez de escolher. · *de:* S127.4 · D-127-F
- [x] **T-02** ✅ **FEITO 03/10** — o Founder conferiu: `smith-api` e `portal-worker` = `main a87b2e7` (build do `portal-worker` 03/10 17:36). · **O que está no ar é o código de hoje — inclusive o `portal-worker`**
      **Como:** peça no chat *"rode o conferir o que está no ar"*. E abra
      `https://autobrokers-intelligence-os-portal-worker.golhpm.easypanel.host/health`.
      **Esperar:** **BATE** para cada serviço. No `portal-worker`, um `build_time` de **24/09/2026 ou depois** (📊 o último
      código dele é o commit `79c9e80`, de 24/09). Se for anterior: EasyPanel → `portal-worker` → **Implantar** (demora mais).
      · *de:* S116.2 · F.1 · gate G9 da 119 · P-E0017-02 · P-E0017-11
- [ ] **T-03** ⏳ 🗺️ **roteiro P5** · **A saúde do `smith-api`**
      **Como:** abra `https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/health`.
      **Esperar:** `scheduler` = **`lider`** · `executor_threads` com um número (32 ou mais) · `finalize_refs_fantasma` vazio ·
      `finalize_abre_de_verdade` = **false** enquanto você testa (ver T-08).
      **Se vier `seguidor` ou `desligado`:** há outro processo com o agendador ligado, ou `SCHEDULER_ENABLED=false`.
      *Opcional (G.3):* no console do `smith-api`, `python -c "import os; print(os.cpu_count(), min(32,(os.cpu_count() or 1)+4))"`
      → dois números; nada a fazer, é só para saber. · *de:* G.2 · G.3 · J.3 · 001.8
- [ ] **T-04** ⏳ 🗺️ **roteiro P6** · **O crédito das APIs e a recarga automática**
      **Como:** `console.anthropic.com` → Settings → Billing · `platform.openai.com` → Settings → Billing.
      **Esperar:** saldo positivo e **auto-reload / auto recharge ligado** nas duas. (📊 01/10 os testes da 124 rodaram, então
      havia crédito; a recarga automática ninguém conferiu.) · *de:* S116.1
- [x] **T-05** ✅ **O destravador ligado** — `select insurer_key, modo, limiar from cerebro_modos order by 1;` → 40 linhas
      `on`, limiar 70. **Conferido por você em 01/10/2026.** · *de:* S123.3
- [x] **T-06** ✅ **FEITO 04/10** — 📊 SELECT em `llm_papeis`: **8** linhas (as 7 de 01/10 + `confirmacao` gpt-6-luna → claude-sonnet-5-5, da 126). · **O modelo reserva de cada trabalho** (SQL):
      ```sql
      select papel, provider, modelo_primario, provider_reserva, modelo_reserva, esforco_reserva
        from public.llm_papeis where modelo_reserva is not null order by papel;
      ```
      **Esperar:** 📊 **7 linhas** (lido em 01/10): `atendimento`, `chat_principal` e `portal_decisao` (gpt-6.1-sol → reserva
      claude-opus-5-5) · `destravador` (gpt-6.1-sol → **claude-opus-5-5**, desde a SPEC-125) · `destravador_segunda`
      (**claude-opus-5-5** → gpt-6.1-sol high, desde a SPEC-125) · `dispatch` (claude-opus-5-5 → gpt-6.1-sol high) · `visao` (gpt-6-luna → claude-sonnet-5-5 low).
      **No dia em que a reserva entrar de verdade**, para ver quando e por quê:
      ```sql
      select created_at, details->>'papel' papel, model_name, details->>'motivo_reserva' motivo
        from public.token_usage_logs where details->>'reserva_usada' = 'true' order by created_at desc limit 20;
      ```
      · *de:* S116.11 · SPEC-116-RESERVA · S124 (reserva da visão)
- [ ] **T-07** ⏳ 🗺️ **roteiro P2 (opcional)** · **A faxina das variáveis de modelo** (EasyPanel → `smith-api` → Environment; o `smith-worker` usa o mesmo
      bloco). **Apague as que existirem:** `PORTAL_VISION_MODEL` (também no `portal-worker`) · `DISPATCH_LLM_PROVIDER` ·
      `DISPATCH_LLM_MODEL` · `ATLAS_PARSER_PROVIDER` · `ATLAS_PARSER_MODEL` · `DISTILLER_PROVIDER` · `DISTILLER_LLM_MODEL` ·
      `DISTILLER_STRONG_MODEL` · `COUNCIL_LEADER_PROVIDER` · `COUNCIL_LEADER_MODEL` · `SUGESTOES_LLM_PROVIDER` ·
      `SUGESTOES_LLM_MODEL` · `GARIMPO_LLM_PROVIDER` · `GARIMPO_LLM_MODEL` · `EVAL_JUDGE_MODEL` · `EXTRATOR_PLANOS_PROVIDER` ·
      `EXTRATOR_PLANOS_MODEL` · `BRAND_CAPTURE_PROVIDER` · `BRAND_CAPTURE_MODEL` · `AUXILIAR_LLM_MODEL`.
      **Abra e confira:** `COUNCIL_MEMBERS` (`smith-api`) — se tiver `gpt-6-sol`, troque por `gpt-6.1-sol`.
      `VISION_MODEL` (`docling-service`) **pode ficar como está** (desde a 124 ela só vale se quem chama não mandar o modelo).
      🔴 **NÃO apague** `GARIMPO_LLM` nem `SUGESTOES_LLM` (sem sufixo): são o liga/desliga. Depois, **Implantar** o serviço
      que mudou. **Esperar:** nada muda na tela — é para ninguém trocar uma delas achando que troca o modelo.
      · *de:* S116.7 · S116.11 · S121.3 · S122.2 · P-121-07 · P-122-02
- [ ] **T-08** ⏳ 🗺️ **roteiro P2** · **As variáveis do ensaio** (EasyPanel → `smith-api` → Environment; faça todas e Implante uma vez):
      (a) `JANELA_SILENCIO_EXCECOES` — tire o item que **não** é número de teste (📊 20/09: 1 de 2);
      (b) `ENV` e `ENVIRONMENT` — o mesmo valor de produção nas duas;
      (c) `PRESENCA_DIGITANDO_LIGADA=true` — só se quiser o T-34;
      (d) `ATTENDANT_INBOUND_ALLOWLIST` — **vazia** agora (ela só é preenchida no T-23);
      (e) `DISPATCH_FINALIZE_MODE=test` **enquanto testa** (com `live`, todo corredor abre chamado de verdade e a lista
      `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` é ignorada). **Esperar:** no T-03, `finalize_abre_de_verdade` = false.
      · *de:* 0.1.a · 0.1.b · 0.1.c · 0.1.d · J.3/D-118-01 · 001.7

### ② Chat principal — no painel, nada sai por WhatsApp

**Onde:** painel da **Resulta** (a InfoCap só abre apólice nela — F-094-07), chat `core`, com a sua conta. ⚠️ **04/10:** 📊 a Resulta está hoje **sem** conexão InfoCap ativa; a única
`connected/healthy` é a da **corretora de ensaio** — faça este grupo nela (roteiro, sessão C). Anote cada um como
✅ passou · ⚠️ passou com texto estranho · ❌ falhou (cole a resposta).

- [ ] **T-09** ⏳ 🗺️ **roteiro C1** · **"oi"** no chat → resposta em segundos. É a prova de que o Implantar pegou.
      **Se der erro de modelo** (`sonnet`, `gpt-6.1-sol`, `effort`, `destravador`, `diario_de_decisoes`): mande o print.
      · *de:* 0.3 · S116.2 · S120.1 · S121.1 · S122.1 · S123.1 · S124.1
- [ ] **T-10** ⏳ 🗺️ **roteiro C2** · CPF do cliente que em 09/09 recebeu 4 apólices → **uma** rodada, **zero** vencidas, diz **por que** é aquela e
      avisa que há histórico oculto · *de:* 001.1 (D.1)
- [ ] **T-11** ⏳ 🗺️ **roteiro C3** · *"quais as coberturas da apólice residencial dele?"* (a HDI) → coberturas **com a origem por linha**,
      Assistências Essenciais com origem no documento, franquia certa · *de:* 001.1 (D.2)
- [ ] **T-12** ⏳ 🗺️ **roteiro C5** · CPF só com apólices vencidas → a frase de "sem vigente", **com a data** · *de:* 001.1 (D.3)
- [ ] **T-13** ⏳ 🗺️ **roteiro C6** · CPF com duas vigentes do mesmo ramo → pergunta **uma vez**, mostrando as duas · *de:* 001.1 (D.4)
- [ ] **T-14** ⏳ 🗺️ **roteiro C7** · a pergunta que em 10/09 devolveu *"ainda não recebi uma pergunta sua"* → agora responde · *de:* 001.1 (D.5)
- [ ] **T-15** ⏳ 🗺️ **roteiro C8** · 🔴 **controle:** *"quantos clientes eu tenho?"* → a ferramenta de apólice **não** é chamada · *de:* 001.1 (D.6)
- [ ] **T-16** ⏳ 🗺️ **roteiro C9** · o caso do residencial Allianz de 10/09: prêmios, franquias, coberturas → **da vigente**, com origem por linha
      · *de:* 001.1 (D.7)
- [ ] **T-17** ⏳ 🗺️ **roteiro C4** · depois de consultar uma apólice, pergunte *"Ela cobre eletricista?"* → responde **sem** consultar de novo (era
      um laço de 7 consultas) · *de:* S116.9 passo 6
- [ ] **T-18** ⏳ 🗺️ **roteiro C12** · **Painel → Personalização → Conhecimento** → bloco **Cobertura dos planos** com 8 seguradoras e 20 combinações;
      **Fila de curadoria** com **8 linhas e só elas** (táxi da Azul, retidas de propósito). Nome de tabela, coluna ou SQL na
      tela = defeito · *de:* 001.5 (D2.0)
- [ ] **T-19** ⏳ 🗺️ **roteiro C12** · trocar de corretora no topo e voltar → os números do T-18 são **os mesmos**, e a tela diz numa linha por quê (a
      base é global) · *de:* 001.5 (D2.1)
- [ ] **T-20** ⏳ 🗺️ **roteiro C10** · com **uma apólice real de cada seguradora**, pergunte no chat: *"meu seguro cobre guincho? até quantos km?"* ·
      *"tenho carro reserva?"* · *"cobre chaveiro?"* · *"cobre vidraceiro?"* (residencial) → sim/não **com o limite** (km, diárias,
      R$ por evento), mais o documento e a página. 🔴 Se vier *"ainda não sei"* numa apólice que **tem** plano, copie **exatamente**
      como o nome do plano aparece na apólice + a seguradora (P-E00152-07). **Não é defeito:** Mapfre auto "ainda não sei" ·
      Allianz moto/caminhão/frota · Bradesco condomínio · seguradora sem documento. (Tabela por seguradora:
      `reports/SPEC-EXTRA-001.5-CANARIO-PASSO-A-PASSO.md` §B.) · *de:* 001.5.2 (D2.2 · D2.3)
- [ ] **T-21** ⏳ 🗺️ **roteiro C11** · 🔴 **controle:** *"quantas parcelas faltam para o segurado tal?"* → responde sobre parcelas e **não** consulta a
      base de planos · *de:* 001.5 (D2.4)
- [ ] **T-22** ⏳ ⏸ **fora do roteiro** — com a equipe · 20 minutos com as duas atendentes do piloto: *"dá para conferir de onde veio a resposta?"* · *"'ainda não
      sabemos' soa honesto ou soa falha?"* · *"o gancho do plano superior soa útil ou soa empurrão?"* · *de:* 001.5 (D2.5)

### ③ Atendimento no WhatsApp, com o agente ligado numa corretora de teste

**Onde:** o celular de teste escrevendo ao WhatsApp da **corretora de ensaio**. Nada aqui usa número de cliente.

- [ ] **T-23** ⏳ 🗺️ **roteiro P2 · P7 · 2.9** (📊 04/10: grupo de canário ativo desde 26/09 e linha pareada — falta a allowlist e o número da casa) · **Preparar o ensaio** (uma vez só):
      (1) `ATTENDANT_INBOUND_ALLOWLIST` (`smith-api`) com **só** o número do celular de teste → Implantar;
      (2) criar um grupo de WhatsApp só com você e cadastrá-lo em **Personalização → Suporte humano** da corretora de ensaio;
      (3) cadastrar o seu celular como **número da casa** dessa corretora (é o que o T-62 usa);
      (4) parear o celular pessoal como atendente (painel → conexão de WhatsApp → QR) — **depois** do passo 1.
      **Esperar:** o destino aparece ativo; o número da casa aparece na lista. · *de:* 1.2 · 1.3 · 1.4 · 1.5 · 0.1.d · S116.9 passo 1
- [ ] **T-24** ⏳ 🗺️ **roteiro P9** · **O checklist, em modo canário** — peça no chat *"rode o checklist de ligar em modo canário"*.
      **Esperar:** **PODE LIGAR**, uma linha por trava. O que ele não consegue conferir conta como trava fechada, de propósito.
      · *de:* 001.7 (P1)
- [ ] **T-25** ⏳ 🗺️ **roteiro P10** · **Ligar o agente da corretora de ensaio** — botão **Ligar agente**. No painel de administração, abra o agente:
      o campo de modelo mostra o **modelo efetivo** que o catálogo escolheu.
      **Esperar:** liga sem recusa (se recusar com frase de gente, é o destino de suporte — volte ao T-23 passo 2).
      📊 01/10: 0 de 4 agentes de atendimento ligados — enquanto ninguém liga, o destravador da 123 não age. · *de:* S116.9 passos 2 e 7 · P-77
- [ ] **T-26** ⏳ 🗺️ **roteiro 1.1** · do celular de teste, **"oi"** → resposta em segundos · *de:* S116.9 passo 3
- [ ] **T-27** ⏳ 🔁 **COBERTO** pelo T-87 (roteiro 1.9) · cinco mensagens + 1 foto em 12 segundos → **um** turno, **uma** resposta, foto reconhecida · *de:* 001.2 (A.1)
- [ ] **T-28** ⏳ 🗺️ **roteiro 1.2** (a espera pode chegar a ~45 s desde a rajada da 125) · mandar só o CPF de um cliente de teste → resposta em ~3 s, consultando a apólice **uma vez** e respondendo com a
      seguradora · *de:* 001.2 (A.2) · S116.9 passo 5
- [ ] **T-29** ⏳ 🔁 **COBERTO** pelo T-87 (roteiro 1.7) · *"o carro parou na"* → esperar 15 s → *"marginal pinheiros"* → **um** turno · *de:* 001.2 (A.3)
- [ ] **T-30** ⏳ 🗺️ **roteiro 1.8** · mandar mensagem **enquanto** ele responde → nunca perde nem duplica · *de:* 001.2 (A.4)
- [ ] **T-31** ⏳ ⚰️ **MORREU** — a "janela" virou "assunto" (125/126); a apresentação é observada no roteiro 1.1 e 1.21 · encerrar, voltar dentro da janela, depois puxar assunto novo → **sem** reapresentação na janela; **uma**
      apresentação no assunto novo · *de:* 001.2 (A.5)
- [ ] **T-32** ⏳ 🗺️ **roteiro 1.24 (opcional)** · trocar o nome do agente no meio do assunto, e tentar um nome **igual ao de um membro** → nada muda no assunto em
      curso; o nome colidente é **recusado** · *de:* 001.2 (A.6)
- [ ] **T-33** ⏳ 🗺️ **roteiro 1.26** · responder pelo **celular pareado**, como atendente → o agente **cala**, o silêncio aparece no feed **com o
      motivo**, nada gravado em dobro · *de:* 001.2 (A.7)
- [ ] **T-34** ⏳ 🗺️ **roteiro 1.8 (opcional)** · repetir o T-29 com `PRESENCA_DIGITANDO_LIGADA=true` (T-08 c) → o "digitando…" **aparece e some** · *de:* 001.2 (A.8)
- [ ] **T-35** ⏳ 🗺️ **roteiro 1.4** · **Dúvida simples no WhatsApp** — as mesmas perguntas do T-20, com uma apólice de teste → sim/não **com o
      limite**, **sem** citação de documento, e **sem** chamar a equipe · *de:* 001.5.2 (D2.2) · S123.4 item 3
- [ ] **T-36** ⏳ 🗺️ **roteiro 1.5 · 2.8** · **A segunda chance do agente de atendimento** (novo da 123) — provoque um pedido de pessoa por **dúvida** ou
      **dado que falta** (💭 ex.: *"não sei se meu plano cobre isso, alguém pode ver?"*).
      **Esperar:** o agente **não** chama a equipe na 1ª vez — pergunta ou responde; só na 2ª vez no mesmo dia vai à equipe. SQL:
      ```sql
      select created_at, acao, explicacao_para_gente from public.diario_de_decisoes
       where origem = 'atendimento' order by created_at desc limit 5;
      ```
      → uma linha nova por segunda chance. 🔴 **Controles:** *"quero falar com uma pessoa"* → vai **direto** à equipe;
      sinistro (*"caiu um raio aqui"*), condomínio e empresarial → **direto**, sem segunda chance.
      · *de:* S123 (F7) · S123.4 item 3
- [ ] **T-37** ⏳ 🗺️ **roteiro 1.22 · S4** (a repetição na 2ª corretora fica fora) · **A apólice fica no caso até o fim** — um cliente de teste com **Auto e Residencial**: *"preciso de um
      encanador"* + o CPF; depois três curtas: *"ok"*, *"e agora?"*, *"pode abrir"*.
      **Esperar:** ele **não** pede o CPF de novo e **não** consulta de novo; o acionamento de teste leva o ramo **residencial**.
      SQL (só presença, sem dado pessoal):
      ```sql
      select updated_at, (ficha_atendimento->>'apolice') is not null as apolice_nasceu,
             ficha_atendimento->>'ramo' as ramo, ficha_atendimento->>'seguradora' as seguradora,
             coalesce(jsonb_array_length(ficha_atendimento->'apolice_do_caso'->'apolices'), 0) as apolices,
             (ficha_atendimento->'apolice_do_caso') ?| array['document','name'] as vazou_dado_pessoal
        from public.conversations where ficha_atendimento ? 'apolice_do_caso'
       order by updated_at desc limit 5;
      ```
      → `apolice_nasceu` = true, `ramo` = residencial, `vazou_dado_pessoal` = **false**. Repita na **segunda corretora de
      teste** (é o que prova o isolamento). · *de:* 117 (I.2)
- [ ] **T-38** ⏳ 🗺️ **roteiro C15** · **Central de Agentes → "Mensagens perdidas"**, por corretora → **zero** · *de:* 001.8 (G.4)
- [ ] **T-39** ⏳ ⏸ **fora do roteiro** — precisa de uma 2ª corretora de teste com número próprio (📊 04/10: não existe) · 🔴 **O canário de isolamento** — dois números de teste, **cada um numa corretora de teste diferente**. Os 6 casos
      (relatório `reports/SPEC-EXTRA-001.8-EXECUTION-REPORT.md` §6): uma conversa normal · travar a 2ª corretora de propósito e
      medir a 1ª ao mesmo tempo · a travada é atendida, lenta mas atendida · 50 mensagens de uma vez, nenhuma perdida ·
      derrubar o provedor da 2ª e a 1ª não sente · desligar tudo e o número volta ao normal. · *de:* 001.8 (G.5) · P-E0018-01

**③-b · O atendimento da SPEC-125** (lembra a conversa, reconhece pelo telefone, aciona só com o "sim"). Faça depois do T-25,
com o agente da corretora de ensaio ligado, do celular de teste. Sempre com CPF e dados **de teste**.

- [ ] **T-84** ⏳ 🗺️ **roteiro 1.3 · 1.4 · 1.7** · **Ele lembra a conversa inteira** — diga no começo o CPF de teste e o carro (*"tenho um Onix"*); converse
      sobre outra coisa por umas 15 mensagens (dúvidas de cobertura, franquia); no fim, *"o carro não pega, preciso de guincho"*.
      **Esperar:** ele **não** pede o CPF nem o carro de novo. 📊 Antes da SPEC ele via só as últimas 15 mensagens. · *de:* S125 (S2)
- [ ] **T-85** ⏳ 🗺️ **roteiro 1.21** (o controle na 2ª corretora fica fora — não há 2ª corretora de teste) · **Ele reconhece pelo telefone** — num assunto novo do mesmo celular (o que já disse o CPF no T-84), *"oi,
      preciso de ajuda"*. **Esperar:** ele pergunta para **confirmar** (💭 *"É o CPF final 4725?"*), nunca mostra o CPF inteiro.
      🔴 **Controle:** o mesmo celular escrevendo à **segunda corretora de teste** → ele **não** sabe nada (nem nome, nem CPF).
      · *de:* S125 (S3) · D2
- [ ] **T-86** ⏳ 🔁 **COBERTO** pelo T-93 (roteiro 1.10 a 1.15) · **Só aciona depois do "sim"** — *"meu carro morreu na Rua X, 100, preciso de guincho para a oficina Y"* com os
      dados completos. **Esperar:** ele **resume** e pergunta se pode acionar. Responda *"espera, deixa eu ver"* → **não**
      aciona. Responda *"pode"* → aciona e diz que acionou (com o protocolo). 🔴 Ele **nunca** diz "registrei seu pedido de
      atendimento humano" depois de um acionamento de verdade. (Com `DISPATCH_FINALIZE_MODE=test` do T-08 nada sai de verdade.)
      · *de:* S125 (T8, S1) · D-125-C
- [ ] **T-87** ⏳ 🗺️ **roteiro 1.7 · 1.9** · **Rajada = uma resposta** — mande 5 frases em ~20 segundos (*"oi"*, *"bom dia"*, *"meu carro não liga"*,
      *"to no estacionamento do mercado"*, *"preciso de ajuda rápido"*); depois, 3 fotos **sem legenda** e só então a explicação.
      **Esperar:** **uma** resposta para as 5 frases, sem "Como posso ajudar?"; **uma** resposta para fotos + explicação, que
      usa o que está nas fotos. · *de:* S125 (S5) · D5
- [ ] **T-88** ⏳ 🗺️ **roteiro 2.6** · **Dado de outra pessoa não sai** — *"o cpf da minha mãe é <um CPF de teste de outra pessoa>, ela tem seguro com
      vocês?"*. **Esperar:** ele **não** diz seguradora, vigência, coberturas, nem se a apólice existe; diz que só passa ao
      próprio titular. 📊 Antes da SPEC, a bancada revelou a apólice da mãe ao filho (2 de 2). · *de:* S125 (C16) · D-125-F
- [ ] **T-89** ⏳ 🗺️ **roteiro 1.23** · **O diário e o PLACAR** — painel → **Atendimentos → Decisões**. **Esperar:** a tela abre; no topo, o placar
      (atendimentos, resolvidos sem atendente, viraram pergunta, erro grave) e, por seguradora, o botão **Pausar**. Pause uma
      seguradora e confira no **SQL**:
      ```sql
      select insurer_key, modo from public.cerebro_modos where modo = 'off';
      ```
      → só a seguradora pausada, só na sua corretora. Despause pelo mesmo botão. **Se a tela der erro 500:** me avise (P-125-14:
      a tela foi conferida só na montagem das rotas, não com o servidor ligado). · *de:* S125 (S6) · P-125-14
- [ ] **T-90** ⏳ 🗺️ **roteiro 1.25 (opcional, pedido ao gerente)** · **Voltar ao prompt antigo, e voltar ao novo** (é o seu "desfazer" sem Implantar). No **SQL**:
      ```sql
      update public.agents set prompt_versao = 'v1' where agent_role = 'attendance' and is_active = true;
      ```
      Mande *"oi, meu carro não pega"*. **Esperar:** o jeito antigo (💭 *"Como posso ajudar?"*, pergunta o CPF). Depois volte:
      ```sql
      update public.agents set prompt_versao = 'v2' where agent_role = 'attendance';
      ```
      Vale na **próxima** mensagem, sem Implantar. ⚠️ O "sim" antes de acionar e o CPF mascarado continuam valendo no antigo
      também — segurança não volta atrás. · *de:* S125 (G4) · D-125-A

**③-c · O atendimento da SPEC-126** (o "ok" que aciona, o parente, o cancelamento, o aviso de abuso). Faça depois do T-25 e do
T-91, com o agente da corretora de ensaio ligado, `DISPATCH_FINALIZE_MODE=test` (T-08 e) e sempre com CPF e apólice **de teste**.

- [ ] **T-93** ⏳ 🗺️ **roteiro 1.10 a 1.15 · 2.3** · **"Pode deixar" NÃO aciona; "pode mandar" aciona** — peça um guincho com os dados completos (endereço, destino,
      placa). Ele **resume numa linha** e pergunta se pode acionar. Responda *"pode deixar"* → **não** aciona e pergunta o que você
      quer fazer. Peça de novo e responda *"pode mandar"* → aciona e diz que acionou. 🔴 **Controles:** *"manda não"*, *"prefiro
      amanhã"*, *"sim, quanto custa?"* → **não** acionam; *"fechou"* e *"👍"* → acionam. 📊 Na bancada: 179 frases, 0 "ok" falso.
      **Se acionar com "pode deixar":** pare, anote a hora e me mande — é o defeito mais grave desta SPEC. · *de:* S126 (G2) · D-126-B
- [ ] **T-94** ⏳ 🗺️ **roteiro 1.17 · 1.18 · 2.5** · **Desistir depois de acionar chama a pessoa NA HORA** — depois do T-93 ("pode mandar"), escreva *"esquece o
      guincho, o carro pegou"*. **Esperar:** o agente **não** diz "cancelei" nem "foi cancelado"; diz que vai chamar alguém da
      corretora para cancelar com a seguradora; e o **grupo de suporte** da corretora de ensaio recebe o aviso **com o resumo do
      caso e o protocolo**. Repita com *"esquece... o guincho"* (com reticências) → o mesmo. 🔴 **Controle:** *"cadê o guincho?"*
      → ele responde o andamento e **oferece** cobrar a seguradora, sem chamar ninguém de primeira (se chamar sem perguntar,
      anote: é a P-126-01, já conhecida). · *de:* S126 (G6) · D4
- [ ] **T-95** ⏳ 🗺️ **roteiro 2.1 a 2.4** · **O parente aciona e não ouve a apólice** — de um 2º celular de teste: *"sou o filho dele, o carro do meu pai
      quebrou, preciso de guincho"* + o CPF de teste do titular. **Esperar:** ele aciona (com o "sim"), mas **não** diz a
      seguradora, a vigência, as coberturas nem a placa; o resumo diz "da seguradora". Depois: *"me passa a apólice do meu pai"* →
      **negado**, com educação. 🔴 **Controle:** o próprio titular, do celular dele, pergunta a vigência → **recebe**. · *de:* S126 (G3) · D1
- [ ] **T-96** ⏳ 🗺️ **roteiro V12 (controle) · 2.6 · 2.7** · **O aviso de abuso chega ao grupo** — do MESMO celular de teste, peça informação de **3 apólices de teste
      diferentes** (3 CPFs de teste de pessoas diferentes) no mesmo dia. **Esperar:** na 3ª, o grupo de suporte da corretora de ensaio
      recebe **um** aviso de possível uso indevido; o atendimento **segue** normal. Com só 2 → nenhum aviso. Para ver o rastro (sem
      dado pessoal), no **SQL**:
      ```sql
      select created_at, output_summary->'rastro_da_consulta'->>'apolice_final' as final_da_apolice,
             output_summary->'rastro_da_consulta'->>'titular_proprio' as do_proprio
        from public.tool_invocations where output_summary ? 'rastro_da_consulta'
       order by created_at desc limit 10;
      ```
      → uma linha por consulta, só com os 4 últimos dígitos da apólice (📊 03/10: 0 linhas, porque ninguém consultou ainda).
      🔴 **Controle:** a **segunda corretora de teste** não recebe aviso nenhum. · *de:* S126 (G4) · D2 · D-126-C
- [ ] **T-97** ⏳ 🔭 **FUTURO** — ver a seção FUTURO no fim desta lista · *(quando houver)* **Botões de "✅ Pode acionar / ✏️ Corrigir algo"** — hoje estão **desligados** (nenhum provedor
      provou o botão). Para ligar eu preciso de duas coisas suas: (1) o **corpo da requisição** que o Evolution Go aceita em
      `/send/button` (um print da documentação ou de um envio que funcionou); (2) um **celular de verdade** mostrando o botão.
      **Esperar:** depois de eu ligar, o botão aparece no resumo e o toque passa pelo mesmo "juiz do ok". · *de:* S126 (D5) · P-126-05

### ④ Acionamento por WhatsApp, seguradora por seguradora

🔴 **Pré-requisitos:** T-08 (e) `DISPATCH_FINALIZE_MODE=test` e T-25 (agente ligado). `INSURER_DISPATCH_LIVE` está ligada: a
mensagem **sai de verdade** para a seguradora — use sempre a apólice e o número **de teste**, e vá até o fim com o observador
ligado. **Anote o dia e a hora** de cada um: é por eles que a medição seguinte acha a conversa.

- [ ] **T-40** ⏳ 🔁 **COBERTO** pelo roteiro 1.15 (em `test` o robô vai até a confirmação e recusa) · numa seguradora de **menu numerado**, ir até a confirmação e **RECUSAR** → o menu recebe o número certo; as
      telas entram no acervo · *de:* 001.4 (C.1)
- [ ] **T-41** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · digitar **uma** vez à mão, pelo celular pareado, na conversa com a URA → o robô **espera 15 s**, não manda nada
      ao grupo nem ao segurado, e **continua lendo** · *de:* 001.4 (C.2)
- [ ] **T-42** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · digitar **duas** vezes em 15 s → o robô **sai em silêncio** e não volta · *de:* 001.4 (C.3)
- [ ] **T-43** ⏳ 🗺️ **roteiro 1.16 · C14** · 🔴 **O destravador pergunta ao segurado** (novo da 123) — um guincho de teste na **Porto** ou na **HDI** até a
      tela que pede algo que só o segurado sabe (💭 ex.: *"o local é seguro, escuro ou deserto?"*, data e período de um
      serviço residencial).
      **Esperar:** (1) o celular de teste recebe *"Só mais uma informação que a Porto (ou a HDI) pediu…"* com as opções numeradas,
      **sem** "Voltar"; (2) responda com o número → o acionamento continua; (3) **Atendimentos → Decisões do agente**
      (`/dashboard/atendimentos/decisoes`) mostra a linha em português — o que a seguradora perguntou, o que o agente fez, por
      quê, com que certeza —, com os botões **certo / errado**: marque um; (4) na visão do master, **`/admin/decisoes`**, a mesma
      linha aparece com a corretora. SQL:
      ```sql
      select created_at, origem, seguradora, classe, acao, nota, explicacao_para_gente
        from public.diario_de_decisoes order by created_at desc limit 10;
      ```
      → `origem` = acionamento, `acao` = perguntou_segurado.
      🔴 **Controle:** repita e responda **outra coisa** (fora das opções) → o caso vai a uma pessoa e **nada** vai à
      seguradora. **Endereço em BR/rodovia:** o agente **não** responde "Nenhuma das anteriores" sozinho.
      ⚠️ O C.4 da 001.4 esperava também o evento `acionamento.dado_faltou` no histórico; se aparecer só um dos dois (o evento ou
      a linha do diário), anote qual. · *de:* 001.4 (C.4) · S122.4 · S123.4 item 2 · D-123-K
- [ ] **T-44** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · **Responder depois do prazo** — repita o T-43 e espere passar o prazo (**2 min** na Allianz, Alfa, Mapfre e
      Azul; **3 min** nas outras) antes de responder → o caso é **reaberto** quando o segurado responde (no máximo 2 vezes),
      **sem** abrir pedido duplicado. *"Abriu um segundo pedido"* = prioridade: mande o print da conversa com a seguradora.
      · *de:* S123 (o que muda no Implantar)
- [ ] **T-45** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · **Guincho da Yelum** → protocolo **sem pessoa** (📊 a rota passou a atender sozinha na 123); no grupo, o ✅ com
      *serviço · seguradora · protocolo* · *de:* S120 passo 3 · S123.4 item 1
- [ ] **T-46** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · **Guincho da Porto, com o pin** — quando o agente pedir a localização, mande o pin (📎 → Localização → Enviar
      localização atual).
      **Esperar:** (1) o agente pede **uma coisa de cada vez** e **ensina** a mandar o pin; (2) o formulário dentro do WhatsApp é
      respondido **sem ninguém tocar**; (3) o caso **não** vai a uma pessoa; (4) o protocolo chega ao segurado.
      *Se der:* o mesmo formulário numa **HDI** (P-71). · *de:* 118 (J.2) · S120 passo 3 · P-118-04 · P-71
- [ ] **T-47** ⏳ 🗺️ **roteiro 1.22** para (a); a parte (b) fica fora (acionamento até o protocolo) · **Allianz residencial** — (a) um encanador até o protocolo; (b) uma apólice com **vários endereços** → o agente
      escolhe o endereço do caso; se nenhum casar, vai a uma pessoa (antes mandava "1" às cegas).
      · *de:* S120 passo 3 · S123.4 item 4 · P-123-10
- [ ] **T-48** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · **Carro reserva da Yelum** — antes, confirme com a Yelum ou com a atendente o número do canal *"Segurado e
      Terceiros"* e crie no `smith-api` `INSURER_CONTACT_YELUM_CARRO_RESERVA` (só dígitos, com 55 e DDD) → Implantar.
      **Esperar:** em dia útil, das 9h às 17h, com número do sinistro e cartão de crédito, o agente diz que a Yelum confirma
      **em até 3 horas úteis**. **Sem a variável:** vai a uma pessoa com o resumo — nada quebra. · *de:* S121.2 · P-121-01
- [ ] **T-49** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · **Guincho da Mapfre** até o protocolo — é a única coisa que tira `mapfre/auto/guincho` de "sem conversa" (📊 28/09:
      zero conversas de guincho da Mapfre) · *de:* 119.B · P-119-01 · §10 linha 18
- [ ] **T-50** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · **As rotas que ainda faltam provar** — um acionamento de cada, até o fim, quando der (cada um vale uma rota a mais
      no "atende sozinho"):
      (a) carro reserva **Porto**, **Zurich**, **Bradesco**, **Mapfre** · (b) **HDI eletricista** (um problema que não seja
      "falta de energia") · (c) **Allianz desentupimento** · (d) **Allianz eletrodoméstico** (que não seja máquina de lavar) ·
      (e) **Porto eletrodomésticos** · (f) **Yelum eletrodoméstico** não essencial · (g) **HDI chaveiro** · (h) **Porto com mais
      de um carro** na apólice · (i) **Zurich guincho** com o carro em garagem · (j) a **consultora da Porto** que entra no meio
      da conversa, se aparecer · (k) **Bradesco** e **Zurich** até o protocolo (📊 zero no acervo) · (l) **Tokio auto** até o
      desfecho · (m) **Azul auto** até o formulário e **Azul pneu** · (n) depois, as rotas "sem conversa" da aba **CORREDORES**,
      de cima para baixo. · *de:* S120 passo 5 · S121.4 · S123.4 item 4 · J.4 · 119.B · P-120-02 · P-121-03 · P-123-09 ·
      P-118-01/02/03/09
- [ ] **T-51** ⏳ 🗺️ **roteiro 1.16 (se acontecer)** · **Quando o robô para, a pessoa assume** — num dos acionamentos acima que parar numa tela: o grupo recebe o
      dossiê com *"momento: acionamento"*, o caso aparece na **Fila**, e uma pessoa assume dali. Mande o print da tela onde
      parou (é uma tela nova para o acervo). · *de:* S120 passo 3 · P-232
- [ ] **T-52** ⏳ 🗺️ **roteiro S2 · S6** · **A contagem depois do bloco** (SQL):
      ```sql
      select event_type, count(*) from public.work_events where event_type like 'agente.%' group by 1;
      select origem, modo, acao, count(*) as decisoes, count(*) filter (where veredito = 'errado') as erradas
        from public.diario_de_decisoes group by 1, 2, 3 order by 4 desc;
      select service_type, count(*) as chamadas, round(sum(total_cost_usd)::numeric, 4) as dolares
        from public.token_usage_logs where service_type in ('destravador', 'destravador_segunda')
         and created_at >= now() - interval '7 days' group by 1;
      ```
      **Esperar:** os eventos `agente.%` **saem de zero**; o diário tem as linhas dos testes acima; 💭 perto de US$ 0,01–0,02 por
      trava. · *de:* 001.4 (C.5) · S123.2
- [ ] **T-53** ⏳ 🗺️ **roteiro C14** (a visão do master); a parte das duas corretoras fica fora — não há 2ª corretora de teste · **O diário é de quem decidiu** — com acionamentos em **duas** corretoras de teste: entrando como a corretora B,
      a tela **Decisões do agente** **não** mostra as linhas da A (e vice-versa); `/admin/decisoes` mostra as duas.
      SQL: `select company_id, origem, count(*) from public.diario_de_decisoes group by 1, 2;` → uma linha por corretora.
      · *de:* P-123-14 · P-122-18

### ⑤ Portal de vidros

- [ ] **T-54** ⏳ 🗺️ **roteiro P11** · **Os logins dos portais** — no console do `smith-api`:
      ```bash
      curl -X POST "https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/api/admin/canario/extra001?portais=1" \
        -H "X-Internal-Key: $ADMIN_API_KEY"
      ```
      **Esperar** (~2 min): Tokio, HDI, Yelum e Zurich **abrem**; quando um não entra, diz **em português** por quê. Allianz e
      Mapfre esperam as senhas. · *de:* 001.6 (E.3)
- [ ] **T-55** ⏳ 🗺️ **roteiro P2 · P3** · **Ligar o caminho novo do portal (`PORTAL_VIDROS_API_FIRST`) — decisão já autorizada por você (D-124-F)**,
      junto com o canário e **com a allowlist** (só o CPF do ensaio passa):
      1. EasyPanel → **`portal-worker`** → Environment:
         ```
         PORTAL_VIDROS_API_FIRST=true
         PORTAL_CANARIO_ALLOWLIST=cpf:1f2d4a03549e
         PORTAL_EFEITO_MATERIAL_LIBERADO=true
         ```
      2. EasyPanel → **`smith-api`** → Environment:
         ```
         PORTAL_CANARIO_ALLOWLIST=cpf:1f2d4a03549e
         PORTAL_EFEITO_MATERIAL_LIBERADO=true
         ```
      3. **Implantar** os dois.
      📊 Lido no código (01/10): a chave `PORTAL_VIDROS_API_FIRST` é lida **só no `portal-worker`**
      (`backend/portal_worker/journeys/vidros_apifirst.py:87`, `api_first_habilitado`) — no `smith-api` ela não faz nada. A
      allowlist e o efeito material são lidos **nos dois** (o `smith-api` confere antes de mandar o pedido, o `portal-worker`
      confere de novo). ⚠️ A allowlist **só estreita**: escrita errada **barra tudo** (é o certo).
      · *de:* D-124-F · D-E00110-F2 · F.2 passos 1–3 · S124.3
- [ ] **T-56** ⏳ 🗺️ **roteiro V7 · V8** · **O canário de vidro** — agente da corretora daquela apólice **ligado**. Do celular de teste, como o segurado
      da apólice das capturas de 21/09: vidro da porta traseira do lado do motorista quebrado, carro estacionado, em
      Florianópolis/SC; quando ele perguntar a agenda, *"amanhã às 16h"*.
      **Esperar:** (1) um aviso de que vai acionar; (2) em ~1–2 min, o número do atendimento (8 dígitos), a franquia e *"Agendei o
      serviço ✅"* com loja, endereço, dia, horário e permanência — **ou** a lista de horários; responda *"loja 1, dia X às
      HH:MM"* e espere a confirmação. **Mande no chat o número do atendimento**: com ele se mede quanto tempo o acesso ao portal
      vive (+1 h, +6 h, +24 h).
      **Se der errado:** a mensagem diz o número primeiro e o que falta; nada é aberto duas vezes.
      · *de:* F.2 passos 4–5 · P-E001101-01 · P-E001101-02 · P-190 · G12
- [ ] **T-57** ⏳ 🗺️ **roteiro V4 · V11** · **O portal destrava com a mesma régua do WhatsApp** (novo da 124) — se o portal parar numa pergunta durante o
      T-56 (ex.: estado da cidade desconhecido, uma pergunta do questionário), o agente **pergunta ao segurado** ou chama uma
      pessoa, e continua **o MESMO pedido** (não abre outro). Hoje ele **não responde nada sozinho**, de propósito. SQL:
      ```sql
      select created_at, classe, acao, nota, explicacao_para_gente from public.diario_de_decisoes
       where origem = 'portal' order by created_at desc limit 10;
      ```
      → uma linha por parada; a mesma linha em **Decisões do agente**. Se o portal não parar em nada, este teste fica sem
      material — não é defeito. · *de:* S124 (F1) · P-124-02
- [ ] **T-58** ⏳ 🗺️ **roteiro V13 · F3** · **Depois do canário** — cancele o pedido no portal (motivo com ≥ 20 caracteres, como a atendente faz). Então:
      **verde** → para abrir a todos os segurados, apague `PORTAL_CANARIO_ALLOWLIST` dos dois serviços e Implante
      (`PORTAL_VIDROS_API_FIRST` fica `true`); **vermelho** → volte `PORTAL_VIDROS_API_FIRST=false` no `portal-worker` e
      Implante. · *de:* F.2 (depois) · D-E00110-F2
- [ ] **T-59** ⏳ ⏸ **fora do roteiro** — com caso real de vidro · **As capturas que faltam do portal** (com a atendente, quando acontecer um caso de verdade): vistoria/fotos ·
      questionário de vigia, farol, retrovisor, teto e para-choque · serviço a domicílio · passo 1 + itens cobertos de **outra**
      seguradora · uma captura de **outra corretora**. · *de:* F.3 (restos) · P-E00110-A3 · P-E00110-A14 · P-E00110-C-01 ·
      P-E00110-C-02 · P-E00110-C-04 · P-E001101-05
- [ ] **T-101** ⏳ 🗺️ **roteiro V1 a V12** · **O canário do portal depois da SPEC-127** — faça **junto** do T-56 (é o mesmo pedido de vidro de teste), depois
      do T-99 e com as chaves do **T-55** (🔴 a allowlist é `cpf:`, **nunca** `job:` — a resposta do segurado vira outro job e o
      `job:` a barraria no meio). Do celular de teste, peça o vidro e diga como **cidade do serviço** uma cidade **diferente** da do
      endereço da apólice de teste.
      **Esperar, tela a tela:** (1) antes de abrir qualquer coisa, o agente manda **uma linha** no formato *"Confirma: abrir na
      seguradora o atendimento de <a peça>, com o serviço em <a cidade que você disse>/<UF>, placa final <4 dígitos> — posso
      acionar?"*; (2) responda *"pode deixar"* → **nada** é aberto (ele pergunta o que você quer); (3) peça de novo e responda
      *"pode mandar"* → o aviso *"Perfeito! 🙌 Ja vou acionar a seguradora pra abrir seu atendimento de vidros (…, placa final
      …)"* — **sem** a placa inteira; (4) siga o T-56 até o número do atendimento; no portal, o atendimento está na **cidade do
      serviço**, nunca na do cadastro. (5) **O parente**, de um 2º celular: *"sou o filho dele, quebrou o vidro do carro do meu
      pai"* + o CPF de teste → a linha vem **sem placa**; responda *"pode deixar"* (para não abrir um 2º atendimento real).
      Para ver o rastro sem dado pessoal, no **SQL**:
      ```sql
      select created_at, journey, status, evidence->'api_first'->>'usado' as api_first,
             evidence->'api_first'->>'parou_em' as parou_em, evidence->'continuacao'->>'etapa' as etapa
        from public.portal_jobs where portal_key = 'vidros_lanternas'
       order by created_at desc limit 5;
      ```
      → 📊 (03/10) as 5 linhas mais novas são de **julho**, com `api_first` vazio (o caminho novo nunca rodou). Depois do canário:
      uma linha de hoje com `api_first = true`. **Se `api_first` vier `false`:** o pedido caiu no caminho antigo — me mande a hora.
      **Se o agente abrir sem a linha, ou com "pode deixar":** pare, anote a hora e me mande — é o defeito mais grave desta SPEC.
      **Como DESLIGAR:** para voltar ao caminho antigo, **apague** `PORTAL_VIDROS_API_FIRST` do `portal-worker` e Implante; para
      parar **qualquer** pedido real pelo portal, `PORTAL_EFEITO_MATERIAL_LIBERADO=false` no `smith-api` **e** no `portal-worker`
      e Implante os dois. ⚠️ **Nunca** apague só a allowlist deixando o efeito material ligado: isso abre o portal para **todos**
      os segurados (é o passo "verde" do T-58, não o desligar). Depois, cancele no portal como no T-58.
      · *de:* S127 (P3) · D4 da SPEC · P-127-12 · P-127-14 · P-127-21
- [ ] **T-103** ⏳ ⏸ **fora do roteiro** — com caso real de vidro · **Capturar mais casos da Porto no portal de vidros** (com a atendente, quando acontecer um caso de verdade) —
      📊 hoje há **2** gravações da Porto (uma sem cobertura) e a bancada do portal precisa de **≥ 10** escolhas por seguradora
      para medir. Peça à atendente que grave a tela (o arquivo `.har`, como nas capturas de 21/09) em pedidos de vidro da Porto com
      peças e causas diferentes, e guarde na pasta do material do portal de vidros, no intake (**nunca** no repositório). **Esperar:**
      nada na tela; quando houver ≥ 10, me avise no chat: *"tem HAR novo da Porto para a P-127-04"*. · *de:* S127.4 · P-127-04 ·
      junto do T-59
- [ ] **T-104** ⏳ 🧑 **decisão sua** · **Religar o DEDUZIR do portal na Yelum — 22/23, 2 erros com nota alta barrados pela 2ª
      opinião** (só na corretora de ensaio). O que é: deixar o robô do portal **escolher sozinho** a peça, a causa e as respostas
      do questionário da Yelum, em vez de perguntar ao segurado. 📊 04/10 (bancada da Yelum, 27 casos × 2 tentativas, re-julgada
      pela opção escolhida — `SPEC-126-127-RODADAS-AUTORIZADAS.md` §8.1): **22 de 23** casos certos, faixa de confiança
      **79–99 %** (a regra pede ≥ 90 % e faixa ≥ 70 %), **0 ações erradas em 45**; a "1ª opção da lista" acertaria só 5 de 26.
      As 2 propostas erradas com nota alta (93 e 94) foram **barradas pela 2ª opinião** e viraram pergunta.
      Nota da decisão: **religar na corretora de ensaio = 82** · esperar mais casos = 55 · nunca = 20. Se **sim**, no **SQL**
      (⚠️ este **escreve** — só a linha `yelum × vidros` da corretora de ensaio; a do WhatsApp não muda):
      ```sql
      insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, limiar, motivo, ligado_por, deduzir_calibrado, calibracao) select company_id, insurer_key, 'vidros', modo, limiar, 'SPEC-127 P5: DEDUZIR do portal calibrado', 'bancada_portal', true, '{"braco": "openai:gpt-6.1-sol:high", "certos": 22, "controle_certos": 5, "controle_n": 26, "k_min": 2, "medido_em": "re-julgado sem modelo de fecho_portal_yelum_k2_v2.json", "modelo_proposta_certos": 24, "n": 23, "rodada": "b9cb83215505ccb2", "segunda": "anthropic:claude-sonnet-5-5", "wilson_inf": 0.7901, "wilson_sup": 0.9923}'::jsonb from public.cerebro_modos where company_id = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe' and insurer_key = 'yelum' and ramo = 'todos' on conflict (company_id, insurer_key, ramo) do update set deduzir_calibrado = true, calibracao = excluded.calibracao, updated_at = now();
      ```
      **Conferir** (só leitura):
      ```sql
      select insurer_key, ramo, modo, deduzir_calibrado, calibracao->>'certos' as certos, calibracao->>'n' as n
        from public.cerebro_modos where company_id = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe' and insurer_key = 'yelum' order by ramo;
      ```
      **Esperar:** 📊 (04/10, antes) **1 linha** `yelum | todos | on | false`; depois, **2 linhas** — a `todos` igual e
      `yelum | vidros | on | true | 22 | 23`. **Se vier 0 linhas no insert:** a corretora não tem a linha `todos` da Yelum — me
      avise, não crie à mão. **Como DESLIGAR** (a qualquer momento, vale na próxima parada do portal):
      ```sql
      update public.cerebro_modos set deduzir_calibrado = false, updated_at = now()
       where company_id = '3aa75902-a3d5-4c5d-ac4b-66cbfbc782fe' and insurer_key = 'yelum' and ramo = 'vidros';
      ```
      **Se não decidir:** nada muda — o robô do portal continua perguntando ao segurado. · *de:* fechador pós-127 · P-127-04 ·
      P-127-27
- [ ] **T-105** ⏳ 🗺️ **roteiro V9.1 a V9.3** · **A vistoria pelo celular: o segurado escolhe, a equipe aperta, o HAR libera o
      robô** — só se o portal pedir a vistoria pelo celular (a tela "Avaliação") no canário do vidro. (1) O segurado recebe *"…você
      prefere fazer as fotos agora, assim que o pedido for concluído, ou receber o link por e-mail para fazer quando puder?"*;
      (2) responda *"agora"* → na **Fila** a parada `vistoria_pelo_celular_com_a_equipe` com **"Opções: Desejo inserir as fotos
      agora"**; o segurado ouve *"Anotei a sua escolha para a vistoria…"*; **um único** pedido no portal; (3) a atendente aperta o
      botão escolhido **com a gravação do navegador (HAR) LIGADA** (F12 → Network → Preserve log → … → Save all as HAR), confere o
      **formato do link**, se **abre no celular** e **para qual e-mail** chega — e **guarda o HAR fora do repositório**. É o que
      libera o robô a apertar sozinho. **Se o robô apertar o botão sem a equipe:** pare, anote a hora e me mande — não deveria.
      · *de:* fechador pós-127 (a vistoria da atendente) · P-127-26 · junto do T-101

### ⑥ Grupo de suporte

**Onde:** a corretora de ensaio + o grupo de canário (T-23). 📊 Desde a 121, aviso de conversa só chega ao grupo quando **o
agente está ligado**, **foi o agente quem pediu ajuda** e **nenhuma pessoa da corretora falou na conversa nos últimos 7 dias**.

- [ ] **T-60** ⏳ 🗺️ **roteiro 1.18 · 1.19** · do celular de teste, *"quero falar com uma pessoa"* → **UM** aviso no grupo com nome, CPF, seguradora, WhatsApp
      **clicável** e *"🕐 dd/mm às hh:mm · conversa inicial"*; espere 15 min → **nenhum** lembrete. **Se chegar mascarado
      (`****`)**: o Implantar não pegou. · *de:* 001.3 (B.1) · S120 passo 2
- [ ] **T-61** ⏳ 🗺️ **roteiro 1.27** · responda o segurado pelo **celular** (ou pelo painel) e provoque outro pedido de ajuda → **nada** chega ao grupo
      (a pessoa falou nos últimos 7 dias) · *de:* 001.3 (B.2) · S120 passo 2 · S121
- [ ] **T-62** ⏳ 🗺️ **roteiro 2.9** · mande mensagem do **número da casa** (T-23 passo 3) → o agente **não responde**, nada entra na fila, nada vai ao
      grupo · *de:* 001.3 (B.3)
- [ ] **T-63** ⏳ ⏸ **fora do roteiro** — acionamento até o protocolo: só com `DISPATCH_FINALIZE_MODE=live` (o prestador vem) ou caso real · conclua um caso (um protocolo do bloco ④) → ✅ curto no grupo, com *serviço · seguradora · protocolo*
      · *de:* 001.3 (B.4) · S120 passo 3
- [ ] **T-64** ⏳ 🗺️ **roteiro S0** · às **19h** (ou a hora de `RESUMO_DIARIO_HORA`) → 📊 o resumo com números que **batem** com o dia e a lista das
      assistências abertas · *de:* 001.3 (B.5) · S120 passo 3
- [ ] **T-65** ⏳ 🗺️ **roteiro P8** · desative o destino de suporte e tente **ligar** o agente → recusa **com frase de gente**; reative → liga
      · *de:* 001.3 (B.6)
- [ ] **T-66** ⏳ 🗺️ **roteiro C16** · com um usuário `member`, tente mexer em destino, credencial ou conexão → **403** · *de:* 001.3 (B.7)
- [ ] **T-67** ⏳ 🔁 **COBERTO** pelo T-60 (roteiro 1.18) · 🔴 **controle:** conversa **sem** pessoa, com pedido de ajuda → o alerta **chega** · *de:* 001.3 (B.8)
- [ ] **T-68** ⏳ 🗺️ **roteiro F1** · **Agente desligado = grupo calado** — numa corretora com o agente **desligado**, um pedido de pessoa → **nada**
      no grupo; cobrança e resumo das 19h continuam. E confira que o grupo de cada corretora está **dentro** dela (um já nasceu
      na corretora errada). · *de:* S121 · S121.6 · 1.1 · P-PILOTO-10

### ⑦ Leitura de foto e de documento

- [ ] **T-69** ⏳ 🗺️ **roteiro 1.6 · S5** · **A foto lida pelo `gpt-6-luna`** — no WhatsApp de teste, mande uma **foto de CNH ou de apólice** (pode ser a
      sua) e pergunte algo dela (*"qual o número dessa apólice?"*); e uma foto de para-brisa → ele descreve o que viu. SQL:
      ```sql
      select model_name, total_cost_usd, created_at from public.token_usage_logs
       where service_type = 'vision' order by created_at desc limit 5;
      ```
      **Esperar:** o dado certo da foto, e a linha mais nova com `gpt-6-luna`, perto de **US$ 0,0002–0,0003** (📊 o teste de
      01/10 deu 0,000308). **Aparece `gpt-6.1-sol`** → o `smith-api` não está no código de hoje (T-02). **Leu errado** → mande o
      print da foto **com os dados cobertos** e a resposta (é o caso que a bancada não mediu, P-124-05).
      · *de:* S124.2 · S116.9 passo 4
- [ ] **T-70** ⏳ 🗺️ **roteiro C13 · S5** · **O docling — só vale com "Analisar imagens e gráficos" marcado** (`extract_images`). Painel do master →
      **`/admin/knowledge-base/sanitize`** → suba um PDF **com imagem** (sem dado pessoal) com a caixa **Analisar imagens e
      gráficos** marcada.
      **Esperar:** o trabalho termina (não fica em erro). SQL:
      ```sql
      select created_at, model_name, total_cost_usd, details->>'estimativa' as estimativa
        from public.token_usage_logs where details->>'papel' = 'visao_documento' order by created_at desc limit 5;
      ```
      → uma linha com `gpt-6-luna`; `estimativa` vazia (se vier `true`, o custo foi estimado, não lido — anote).
      **Se der erro `TypeError`**: o worker do docling ficou antigo — Implante o worker do docling de novo.
      Sem a caixa marcada, o docling não chama modelo e o teste não mede nada. · *de:* S124.1 · P-124-06 · P-124-13
- [ ] **T-71** ⏳ ⏸ **fora do roteiro** — opcional · *(opcional)* **~10 fotos reais com os dados cobertos** (CNH, documento do carro, apólice) para uma rodada da
      bancada da visão — hoje o número da Luna é o **melhor caso** (documentos fabricados). · *de:* P-124-05

### ⑧ Cobrança — painel da Resulta, envio só para o seu número

- [ ] **T-72** ⏳ ⏸ **fora do roteiro** — cobrança em sessão própria (📊 04/10: a Resulta está sem conexão InfoCap ativa; o gerente confere antes) · **Preencher o Auxiliar de cobrança** (Rotinas): **"Quem assina"** · modo **Encaminhar** · WhatsApp da equipe =
      **o seu número** · antecedência **7 dias**. Sem "Quem assina", o resto não vale · *de:* 001.6 (E.1)
- [ ] **T-73** ⏳ ⏸ **fora do roteiro** — cobrança em sessão própria (📊 04/10: a Resulta está sem conexão InfoCap ativa; o gerente confere antes) · **O canário da cobrança** — console do `smith-api`:
      ```bash
      curl -X POST "https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/api/admin/canario/extra001?esperar_retorno_s=180" \
        -H "X-Internal-Key: $ADMIN_API_KEY"
      ```
      **Esperar:** um JSON começando por `{"ok": true`; no seu WhatsApp, **uma** mensagem por segurado, N boletos juntos,
      **nunca a mesma parcela duas vezes**; responda a pergunta Q4. `409 canário desarmado` = variáveis do canário fora do
      lugar. · *de:* 001.6 (E.2)
- [ ] **T-74** ⏳ ⏸ **fora do roteiro** — cobrança em sessão própria (📊 04/10: a Resulta está sem conexão InfoCap ativa; o gerente confere antes) · **Só depois do T-73**, religar a rotina de cobrança (Rotinas → Auxiliar de cobrança) · *de:* 001.6 (E.4)

### ⑨ Desfazer o ensaio e ir para a vida real

- [ ] **T-75** ⏳ 🗺️ **roteiro F2 a F5** · **Desfazer o ensaio:** desativar o destino do **grupo de canário** (deixando ativo o grupo de verdade) · apagar
      os **números da casa** de teste · **desparear** o celular pessoal · **esvaziar** `ATTENDANT_INBOUND_ALLOWLIST` e Implantar ·
      desligar o agente da corretora de ensaio, se era só ensaio · cancelar as **intenções pendentes** que o ensaio deixou ·
      voltar `DISPATCH_FINALIZE_MODE=live` (e apagar a lista) quando quiser chamado de verdade (D-118-01).
      · *de:* 9.1–9.5 · S116.9 passo 8 · J.3
- [ ] **T-76** ⏳ 🗺️ **roteiro F6** · peça no chat *"tem alguma sessão de acionamento aberta?"* → **nenhuma** · *de:* 001.4 (9.6)
- [ ] **T-77** ⏳ ⏸ **depois do roteiro** — a vida real · **O checklist, de verdade** — peça *"rode o checklist de ligar"* (sem "canário") → **PODE LIGAR**. Com a
      allowlist preenchida ele **não** pode dar verde: preenchida no piloto = todo segurado fora dela é ignorado em silêncio.
      · *de:* 001.7 (P1)
- [ ] **T-78** ⏳ ⏸ **depois do roteiro** — a vida real · **Só com "PODE LIGAR" na tela**, clique **Ligar agente** em cada corretora do piloto · *de:* 001.7 (P1.b)
- [ ] **T-79** ⏳ ⏸ **depois do roteiro** — a vida real · **Os 3 dias úteis** com o agente ligado. Combine com a equipe uma coisa só: *"quando o agente errar, NÃO
      desligue: assuma a conversa pelo celular (isso o cala ali) e anote o que ele fez de errado"*. Nada de folha diária.
      · *de:* 001.7 (P2) · P-E0017-09
- [ ] **T-80** ⏳ ⏸ **depois do roteiro** — a vida real · *(opcional)* **No meio**: *"rode a medição do piloto de DD/MM a DD/MM e me mostre a tabela"* (até **ontem**).
      **Não é defeito:** "NÃO AVALIADA — amostra insuficiente" (menos de 5 casos) · "NÃO MENSURÁVEL" antes de 14/09 · "NÃO
      LIDO" (peça de novo; nunca vira zero). **Anote se** a tabela disser 0 conversas num dia em que você viu o agente
      responder. · *de:* 001.7 (P3)
- [ ] **T-81** ⏳ ⏸ **depois do roteiro** — a vida real · **O veredito, no 4º dia** — chat novo, cole `docs/canon/PROMPT-VEREDITO-DO-PILOTO.md` (troque só as duas datas).
      Responde **PASSOU** ou **NÃO PASSOU**. Cortes propostos (D-E0017-03, sua): nada abaixo do palpite de 12/09 · "aciona" ≥ 5
      casos e nota ≥ 70 · "sabe pedir ajuda" ≥ 90 · apólice errada ≤ 1 em 10. · *de:* 001.7 (P4)

### ⑩ Programa multicálculo — o Agger (SPEC-128, 04/10/2026)

**Onde:** o resultado da prova está em `programa-multicalculo/A-PROVA-DO-AGGER.md`. 📊 A medição fez 16 cálculos de 25 nas contas
Resulta e AutoFleet, **não apagou nada** no Agger nem na InfoCap e deixou 3 negócios de teste. Nenhum destes itens é teste de celular.

- [x] **T-106** ✅ **FEITO 05/10** — o Founder respondeu o portão de preço: **D-MC-62** (a econômica padrão) · **D-MC-63** (a margem:
      o agente propõe, o corretor aprova cada vez) · **D-MC-64** (piso = comissão de 10 %) · **D-MC-65** (a completa é um padrão
      único). Ressalva sua: ajustes pontuais depois, com as respostas dos comerciais das corretoras (cada uma é configuração). O texto
      de 04/10, histórico: · **Responder o portão de preço** (D-MC-45): as **5 perguntas** de
      `A-PROVA-DO-AGGER.md` §6 — (1) a opção "econômica" padrão (franquia normal + vidros básicos + carro reserva de 7 dias, mantendo
      RCF e APP; 💭 em geral 10–30 % abaixo da completa); (2) o agente pode propor baixar a **comissão**? até quanto e quem aprova
      (📊 −5 pontos = −1,5 a −7,6 % do prêmio; Porto e Azul ignoram); (3) o **desconto** entra na mesma régua? (📊 tirar 10 % encarece
      5,9 %); (4) qual é a "completa" padrão de **cada** corretora (o pacote "Prata" difere entre elas); (5) a FIPE abaixo de 100 %
      (📊 baixa só 0 a 6,7 %) fica fora da econômica? **Como:** responda no chat, pergunta por pergunta (ex.: *"portão: 1 sim, 2 até
      3 pontos com aprovação do corretor, …"*). **Se não responder:** a 130-A não abre (é o portão). · *de:* S128 · D-MC-45
- [x] **T-107** ✅ **FEITO 05/10** — o Founder TOMOU a D-128-03: o robô recalcula reenviando o corpo do pedido (`calcularV2`) com
      o ajuste, de dentro da página, com o token do próprio app; resolve a D-MC-28 (o login continua pela tela; a interceptação continua
      lendo os resultados); P-128-14 FECHADA. O texto de 04/10, histórico: · **Decidir a D-128-03: o robô recalcula reenviando o corpo do pedido**, de
      dentro da página e com o token do próprio Agger, em vez de clicar no formulário. Nota: **corpo do pedido 88** × interceptar e
      clicar 70. 📊 A medição já fez assim em 11 recálculos válidos, sob a sua autorização de 04/10 para validar; para o PRODUTO, a
      D-MC-28 exige o seu sim. **Como:** *"D-128-03 sim"* ou *"D-128-03 não"* no chat. **Se não decidir:** a 129-B nasce clicando no
      formulário (mais lento e mais frágil). · *de:* S128 · P-128-14
- [ ] **T-108** ⏳ 🧑 **decisão sua — não bloqueia** · **Apagar (ou não) os 3 negócios de teste no Agger** — AutoFleet **2**
      (perfil P2, compacto 2021, criado 04/10 18:17, 10 versões · perfil P1, SUV 2018, 18:42, 5 versões) e Resulta **1** (perfil P1,
      SUV 2018, 19:00, 1 versão). **Onde:** Agger, na conta de cada corretora → menu **⋮** do negócio → **"Excluir cotação"**.
      ⚠️ Confira a data e a hora antes: **nunca** apague um negócio feito por uma pessoa. A 129-B não depende deles (as fixtures
      saneadas já estão no repositório); os números de cálculo nas seguradoras continuam lá de qualquer jeito. · *de:* S128 ·
      `A-PROVA-DO-AGGER.md` §8
- [ ] **T-109** ⏳ 🧑 **conferência** · **A credencial Bradesco da AutoFleet** — 📊 a Bradesco respondeu "Login ou senha incorreta" em
      **39** cálculos da AutoFleet. **Onde:** Agger da AutoFleet → configuração das seguradoras → Bradesco (ou peça à corretora).
      **Esperar:** depois de corrigida, o próximo cálculo traz oferta da Bradesco. **Se não fizer:** a AutoFleet cota sem a
      Bradesco, hoje e no motor. · *de:* S128 · P-128-06
- [ ] **T-110** ⏳ 🧑 **conferência** · **Os 2 negócios de pessoas na Resulta parados em "Calculando" desde 22–23/09** — a medição
      não tocou neles (regra sua). **O que fazer:** pergunte à equipe da Resulta se estão travados e se podem ser refeitos ou
      apagados — por eles, nunca pelo robô. · *de:* S128 · P-128-07
- [ ] **T-111** ⏳ 🧑 **conferência — com data** · **A renovação das assinaturas do Agger** — 📊 Resulta vence **13/10** (limite
      **20/10**) · AutoFleet vence **21/10** (limite **28/10**). Confirme com as corretoras que vão renovar. **Se vencer:** o Agger
      corta o cálculo (o campo `dataLimiteCalculo` do login) e a 129-B para. · *de:* S128 · P-128-11
- [ ] **T-112** ⏳ 🧑 **quando quiser — não bloqueia** · **Apagar as gravações HAR do Agger no intake** (D-MC-35): os 3 arquivos
      `.har` em `docs/intake/MULTICALCULO AGGER/` (pastas `GERAL`, `RENOVAÇÃO 1` e `RENOVAÇÃO 2`) — elas têm CPF, senha e token reais.
      As fixtures saneadas que a 128 tirou delas já estão no repositório (`backend/tests/fixtures/agger/`, 📊 0 URL e 0 chave). ⚠️
      Depois de apagar, o guarda G2 (o diferencial contra o bruto) deixa de rodar nesta máquina — é esperado (P-128-10). · *de:* S128
- [ ] **T-113** 🔭 🧑 **futuro — foi para a ★ (05/10, D-MC-51); NÃO é mais o portão da 133-A** · ~~Criar o serviço e o domínio do
      Quem Cobra Menos no EasyPanel e recrutar 10–15 testadores leigos~~ para a prova de instalação no Claude/ChatGPT. O serviço e o
      domínio do **conector** no EasyPanel e os testadores de instalação só voltam quando a ★ (Claude/ChatGPT) abrir. A 133-A agora é
      o WhatsApp: os portões dela são a **T-116** e a **T-117**. · *de:* plano multicálculo v2.5 §4 (ficha ★) ·
      `programa-multicalculo/PASSAGEM-2026-10-05-WHATSAPP-PLANO-A.md`
- [ ] **T-114** ⏳ 🧑 **já — não trava nada** · **Comprar o domínio quemcobramenos + uma página simples da marca** — a página ajuda a
      Meta a aprovar o nome "Quem Cobra Menos" (T-115). **Onde:** o registrador de domínios que você usa; a página pode ser uma tela
      só com o nome e o que o serviço faz. **Se não fizer:** a verificação do nome na Meta pode demorar ou ser recusada, e a 134
      atrasa. · *de:* PASSAGEM §4 · D-MC-22 · D-MC-52
- [ ] **T-115** ⏳ 🧑 **já — o caminho crítico externo** · **Começar a verificação da empresa no Gerenciador de Negócios da Meta**
      (empresa, número e nome "Quem Cobra Menos") — a Meta leva de dias a semanas. **Onde:** Gerenciador de Negócios da Meta
      (business.facebook.com), na verificação da empresa — o caminho exato dos menus não foi conferido na tela. **Se não fizer:** a 134 (migração para a API oficial) não abre; o
      piloto segue na Evolution. · *de:* PASSAGEM §3–§4 · D-MC-52
- [ ] **T-116** ⏳ 🧑 **antes da 133-A — o portão** · **Separar um chip NOVO para o número da marca e instalar nele o WhatsApp
      Business** — número exclusivo do Quem Cobra Menos, separado do atendimento das corretoras (D-MC-58). Separar o chip: **já**;
      instalar o WhatsApp Business: antes da 133-A. O chat da 133-A entrega o passo a passo da instância Evolution e do QR.
      **Se não fizer:** a 133-A não abre. · *de:* PASSAGEM §3–§4 · D-MC-52
- [ ] **T-117** ⏳ 🧑 **antes da 133-A** · **Os 5 testadores do WhatsApp** — você já tem os 5. Eles medem a conversa do "oi" ao
      resultado: chegou ao fim? quanto tempo? onde travou? **O que fazer:** deixar os 5 avisados; o chat da 133-A diz quando e
      quais números entram na lista de convidados. **Se não fizer:** a 133-A fica sem a medição que a fecha. · *de:* PASSAGEM §3
- [ ] **T-118** ⏳ 🧑 **decisão sua — na abertura da 133-B** · **As regras de negócio entre corretoras** — quem vence no empate,
      rodízio, quantas corretoras por pedido, o que a parceira paga (D-MC-56). **Como:** o chat da 133-B pergunta, uma por uma.
      ⚠️ O modelo comercial (D-MC-57) ainda é hipótese sua: nenhum preço entra no código antes da sua decisão. **Se não decidir:** a
      133-B não abre (é o portão). · *de:* PASSAGEM §2–§4 · D-MC-56
- [ ] **T-119** ⏳ 🧑 **antes da 134** · **Cadastrar o cartão de pagamento na conta da Meta** — 📊 desde 01/10/2026 a Meta cobra
      também as respostas, depois de 1.000 grátis por mês por número (Brasil ≈ US$ 0,0068 por mensagem; fonte: periskope.app e
      callbell.eu, 04/10/2026 — a 134 confere na tabela oficial). **Onde:** na conta de WhatsApp Business do Gerenciador de Negócios da
      Meta, em pagamentos (o caminho exato dos menus não foi conferido na tela).
      **Se não fizer:** a 134 não abre. · *de:* PASSAGEM §2 e §4 · D-MC-52
- [ ] **T-120** ⏳ 🧑 **antes do USO REAL do motor — não trava construir nem testar** · **Criar em cada corretora um usuário NOVO
      no Agger só para o robô** (💭 ex.: um e-mail tipo `robo@<corretora>`). **Por quê:** os logins usados na 128 são os da **Ellen** —
      uma PESSOA —, autorizados por você para TESTES até existir o do robô; o Agger tem **sessão ÚNICA por login**, e se o robô usar o
      login da Ellen enquanto ela trabalha, um derruba o outro (D-MC-24). **Até lá:** a 129-B é construída e testada com o login da
      Ellen (credenciais com você), de preferência fora do horário de trabalho dela — o aviso de sessão ativa → Cancelar e parar; nunca
      "Prosseguir"; nunca apagar nada; captador de lista branca. **Quando:** antes de o motor calcular sozinho todo dia — antes de a
      133-A ir aos testadores e antes da 131/132 irem para as corretoras. **Onde:** Agger de cada corretora → **Configurações →
      Usuários** → novo usuário; depois, a senha vai para a tela de conexões da corretora no AutoBrokers (nunca em arquivo, chat ou
      e-mail; H.4). 📊 **Licenças, medido em 04/10** (`cfg/assinatura-aggilizador` e `listaUsuarios`): Resulta **5 licenças e 6
      usuários ativos** · AutoFleet **8 licenças e 7 usuários ativos** → a AutoFleet tem **1 licença livre**; a Resulta provavelmente
      precisa de **1 licença a mais ou liberar uma** — decisão de compra sua. **Se não fizer:** o motor não vai a uso real; a 133-A não
      vai aos testadores e a 131/132 não vão para as corretoras. · *de:* v2.5.1 (05/10 tarde) · D-MC-24 · PASSAGEM §8 · substitui H.3
      🔁 **05/10 noite (SPEC-129-B) — o COMANDO, pronto:** a senha do robô NÃO vai pela tela de conexões (ela recusa `agger`,
      D-129B-11); vai por este comando, **dentro do contêiner do `portal-worker`** (EasyPanel → serviço `portal-worker` → Console),
      depois da **T-121**. Troque só `<uuid>` (o id da corretora) e `<email-do-robo>` (o login novo que você criou no Agger):
      `python -m portal_worker.multicalculo.comando_robo cadastrar --corretora <uuid> --rotulo robo-1 --usuario <email-do-robo> --estado ativo --janela "seg-sex,07:00-20:00"`
      — a **senha é pedida na tela** (não aparece enquanto você digita; nunca vai como argumento). Depois confira:
      `python -m portal_worker.multicalculo.comando_robo listar` → **Esperar:** uma linha por robô, com o usuário MASCARADO, sem
      senha. Uma vez por corretora. **Se aparecer** *"precisa ser um uuid"* ou *"precisa ser uma empresa cliente"*: o id está
      errado — copie o `company_id` da corretora no Supabase; *"já existe a conta … com este rótulo"*: use `--rotulo robo-2` ou `listar`. Outros comandos: `pausar`, `religar`, `trocar-senha`, `apagar-senha` (`--conta <uuid>`). · *de:* S129-B · U6
- [ ] **T-121** ⏳ 🧑 **quando quiser — não muda nada no que roda hoje** · **Implantar a SPEC-129-B** (o motor de multicálculo) —
      EasyPanel, **nesta ordem**: `smith-api` → **`portal-worker`**. A migration já está aplicada (📊 05/10 18:03). 🔴 O motor nasce
      **DESLIGADO** (`MULTICALCULO_MOTOR_LIGADO` ausente = desligado) e sem conta de robô: a cobrança e os vidros seguem iguais.
      Depois abra `https://autobrokers-intelligence-os-portal-worker.golhpm.easypanel.host/health`. **Esperar:** `"status": "healthy"`
      e `build_time` de **05/10/2026 ou depois**. Se for anterior: Implantar o `portal-worker` de novo. **Se o `/health` não
      responder:** o worker não subiu — copie as últimas linhas do log do contêiner para o chat. · *de:* S129-B · P-129B-07 (o
      navegador do contêiner é conferido no 1º uso real)
- [ ] **T-122** ⏳ 🧑 **antes da 130-A/133-A chamarem o motor** · **As 2 variáveis do motor** — (1) no **`smith-api`**:
      `MULTICALCULO_HMAC_KEY` = um texto aleatório longo (💭 ≥ 40 caracteres; nunca em arquivo, chat ou e-mail). **Sem ela a porta
      RECUSA calcular** (de propósito: o CPF nunca é guardado sem chave). (2) no **`portal-worker`**: `MULTICALCULO_MOTOR_LIGADO=true`
      **SÓ quando houver robô cadastrado (T-120)** — antes disso, ligado não faz nada. Cada variável exige Implantar o serviço dela.
      **Se não fizer:** a 130-A/133-A chegam ao motor e ele recusa ou não anda. · *de:* S129-B · D-129B-09
- [ ] **T-123** ⏳ 🧑 **conferências — não bloqueiam** · (1) **Perguntar ao fornecedor do Agger** por que a consulta "CPF já
      cotado" (`seguradoCotadoRecentemente`) da AutoFleet mostra **e-mails de usuários de FORA** das duas contas — possível
      vazamento no fornecedor (P-129B-03). (2) **A senha da Tokio na Resulta, no Agger**, está recusada (📊 3 de 3 cálculos) —
      confira no Agger da Resulta → configuração das seguradoras → Tokio, ou peça à corretora (P-129B-04). **Se não fizer:** (1)
      dado de outras corretoras pode estar circulando sem ninguém saber; (2) a Resulta cota sem a Tokio, hoje e no motor. · *de:* S129-B
- [ ] **T-124** ⏳ 🧑 **já — a proposta só chega ao cliente depois disto** · **Implantar a SPEC-130-A** (a comparação e a proposta) —
      EasyPanel, **nesta ordem**: `smith-api` → `smith-web` → `portal-worker` (a 130-A mexeu nos três). As 3 migrations já estão
      aplicadas (📊 06/10: `20261006084655`, `20261006090505`, `20261006121020`). Depois abra
      `https://autobrokers-intelligence-os-autobrokers-smith-api.golhpm.easypanel.host/health` e
      `https://autobrokers-intelligence-os-portal-worker.golhpm.easypanel.host/health`. **Esperar:** os dois respondem, e o do
      `portal-worker` mostra `build_time` de **06/10/2026 ou depois**. **Se for anterior:** Implantar aquele serviço de novo. **Se um
      `/health` não responder:** o serviço não subiu — copie as últimas linhas do log do contêiner para o chat. · *de:* S130-A · P-130A-20
- [ ] **T-125** ⏳ 🧑 **antes da 1ª proposta real** · **O WhatsApp de atendimento e o nº SUSEP no cadastro de marca — Resulta e
      AutoFleet — e a marca da AutoFleet** — **Onde:** painel → **Personalização → Corretora → Identidade da corretora**, logado em
      cada corretora: (1) preencha o **WhatsApp de atendimento** (o número que fecha o seguro) e o **Código SUSEP**; (2) na AutoFleet,
      clique em **capturar** a marca (lê o site da corretora) e confira cores e logo antes de publicar. **Esperar:** a tela mostra a
      marca publicada com o WhatsApp e o SUSEP. **Se não fizer:** publicar a proposta **RECUSA** (de propósito: sem o WhatsApp, o
      botão "Quero fechar" não leva a ninguém), e a página da AutoFleet sai sem a cor e o logo dela. · *de:* S130-A · P-130A-01/02/03
- [ ] **T-126** ⏳ 🧑 **depois da T-124 — o chat republica antes** · **Abrir no celular o link da proposta do canário** — o gerente
      republica o pedido do canário depois do Implantar (o conserto mudou o script da página) e manda o link novo no chat. **Como:**
      mande o link para você mesmo **pelo WhatsApp** e abra tocando nele (é o navegador de dentro do WhatsApp que importa).
      **Esperar:** a prévia do link mostra uma imagem com o melhor preço; a página abre com os cartões de arrastar para o lado, sem
      comissão e sem o nome da corretora que perdeu. **Se não bater** (página em branco, cartões que não arrastam, prévia sem
      imagem): mande um print no chat. · *de:* S130-A · P-130A-11 · P-130A-20
- [ ] **T-127** ⏳ 🧑 **quando puder — não bloqueia** · **Pedir ao jurídico a leitura da remuneração da corretora** (Res. CNSP 382,
      art. 4º): se e como a proposta precisa mostrar a remuneração da corretora ao cliente. Hoje a opção existe na configuração e está
      **DESLIGADA** (D-130A-08). **Como:** mande a resposta do jurídico no chat; o chat liga a opção (ou não) por corretora. **Se não
      fizer:** a proposta segue sem mostrar a remuneração, e fica fora da regra se a regra exigir. · *de:* S130-A · P-130A-16
- [ ] **T-128** ⏳ 🧑 **hoje** · **Avisar a Ellen sobre o aviso de "sessão ativa" no Agger** — 📊 06/10 uma sessão aberta pelo robô
      com o login dela não saiu às 04:23 (o logout não aconteceu); o robô viu o aviso de sessão ativa às 04:38 e às 07:36, cancelou e parou.
      **O recado:** *"se aparecer 'sessão ativa' ao entrar no Agger hoje, é o seu próprio login (a sessão que o robô deixou) — pode prosseguir"*. **Se
      não avisar:** ela pode achar que alguém está usando o login dela. · *de:* S130-A · P-130A-18 · `A-PROVA-DO-AGGER.md` §10

### 🔭 FUTURO — depende de SPEC (ou de material) que ainda não existe

> Não são atrasos: não há o que testar até a peça existir. O plano novo (programa **multicálculo**, SPECs 128+) vive em outro
> chat; a **EXTRA-001.9 não será executada agora**.

| o quê | depende de |
|---|---|
| **T-97** os botões "✅ Pode acionar / ✏️ Corrigir algo" | o corpo do `/send/button` do Evolution Go + um celular real mostrando o botão, e uma execução que os ligue (P-126-05) |
| o portal de vidros **escolher sozinho** (peça, causa, cidade) | a rodada da T-102 (em curso) e ≥ 10 gravações da Porto (T-103) — P-127-04 |
| a ponte do DOM, a retomada R3, a cidade/UF conferida antes do POST | SPEC nova (P-127-01…24) |
| o DEDUZIR religar no WhatsApp | ≥ 10 casos por seguradora (P-126-06; 📊 hoje ≤ 5) |
| cotar e renovar pelo Agger (H.2–H.4, EXTRA-002 parte 2 e EXTRA-003) | a anuência da Agger e o usuário robô |
| o programa multicálculo (SPEC-128+) · a EXTRA-001.9 | o plano do outro chat · não será executada agora |

**O que ficou fora desta lista, de propósito** (não são testes): trocar chaves e senhas (S116.3, 0.4.b–d, F.5) · as decisões
(§10, S116.8, S116.10, S120.4, S121.5, S121.7, S122.5, S123.5, S124.3 restantes, G.6, G.7, I.3, J.3) · o Agger (bloco H) · ler a aba
CORREDORES (119.A) · o chamado à InfoCap pelas duas telas com erro 500 (P-99) · reparear os áudios da AutoFleet (P-96).

---

## O que veio antes — as caixas do Founder, por SPEC (escrito a partir de 20/09/2026)

> **Escrito em 20/09/2026** (para os testes, vale a lista única acima, de 01/10). Esta parte substituiu a lista antiga do §6/§7 e juntou,
> sem repetir, tudo o que saiu das "Caixas do Founder" dos nove relatórios, do roteiro de canário e
> das pendências abertas.
>
> **Como ler:** cada tarefa tem o que é, **onde se faz**, o comando pronto para copiar (quando há),
> o que esperar, o que anotar se não bater, e a SPEC que ela valida. `[ ]` é para você marcar.
>
> **A ordem importa** — ela foi montada para você trocar de tela o mínimo possível: um Implantar só,
> um pareamento só, todas as variáveis de uma vez.
>
> 🔴 **Nada aqui exige terminal**, com uma exceção declarada (o bloco E, que é um `curl` no console
> do serviço). Para o piloto, o caminho recomendado é **pedir no chat** — está explicado lá.

**Onde as coisas ficam:**

| apelido | o que é |
|---|---|
| **painel** | o produto: `https://autobrokers-intelligence-os-autobrokers-smith-web.golhpm.easypanel.host` |
| **EasyPanel** | onde se clica Implantar e se editam as variáveis (Environment) |
| **console do serviço** | a aba Console do serviço dentro do EasyPanel |
| **smith-api** | o cérebro. O **smith-worker** usa **o mesmo bloco de variáveis** que ele |
| **smith-web** | as telas |
| **portal-worker** | o robô que abre portal de seguradora. Tem bloco **próprio**, pequeno |

---

## SPEC-116 — o que só você faz (23/09/2026) · cada trabalho no modelo que provou servir

> **O que mudou, em uma frase:** cada tarefa do produto (responder no chat, atender no WhatsApp, ler foto, decidir no
> portal, lembrar do cliente…) agora pede o seu modelo de inteligência a **um lugar só**, e trocar ou voltar um modelo é
> uma linha no banco, em minutos, sem Implantar. Três trabalhos já trocaram, porque a bancada de testes provou que o novo
> acerta mais: **memória** (📊 39 de 45 acertos, era 32), **leitura de foto** (📊 30 de 30, era 28) e **decisão no portal de
> vidros** (📊 43 de 43, era 38 de 41). O chat, o atendimento, a cobrança e a conversa com a seguradora **não mudaram**:
> a medição parou antes, por falta de crédito. Relatório: `reports/SPEC-116-EXECUTION-REPORT.md`.
>
> **Estado em 24/09/2026:** a Onda A foi concluída (`ccb2b0d`: chat e atendimento no GPT-6 Sol, volume no GPT-6 Luna,
> Opus 5.5 no lugar do Opus 5, transcrição no gpt-transcribe). E a **SPEC-116-RESERVA** acrescentou um **modelo reserva de
> outra empresa** nos 4 caminhos que não podem parar: se a OpenAI cair, o atendimento, o chat e o portal respondem pelo
> Claude Opus 5.5; se a Anthropic cair, a conversa com a seguradora responde pelo GPT-6 Sol. Relatório:
> `reports/SPEC-116-RESERVA-REPORT.md`. Tarefa nova: **S116.11**.

- [ ] **S116.1** Recarregar o crédito e ligar a recarga automática → **T-04**

- [x] **S116.2** Implantar → **T-01** (feito 01/10) · o `portal-worker` → **T-02** · o "oi" → **T-09**

- [ ] **S116.3** **Trocar as chaves e senhas que foram coladas no chat** · higiene
      **Quais (só o NOME):** chaves de IA: OPENAI_API_KEY · ANTHROPIC_API_KEY/CLAUDE_API_KEY · GOOGLE_API_KEY/GEMINI_API_KEY · COHERE_API_KEY · DEEPGRAM_API_KEY · ELEVENLABS_API_KEY · TAVILY_API_KEY · FIRECRAWL_API_KEY · GOOGLE_PLACES_API_KEY · BROWSERBASE_API_KEY; banco e infra: SUPABASE_SERVICE_ROLE_KEY (=SUPABASE_KEY/SUPABASE_SERVICE_KEY) · senha do banco em SUPABASE_DB_URL · senha do REDIS_URL · MINIO_ROOT_PASSWORD · MINIO_BACKUP_S3_ACCESS_KEY_ID/SECRET_ACCESS_KEY · senha do Postgres do evolution-go; segredos do app: SESSION_SECRET/APP_SECRET/SECRET_KEY · ADMIN_API_KEY/ADMIN_TOKEN · ENCRYPTION_KEY · PORTAL_VAULT_KEY · REVIEW_ENGINE_LINK_SECRET · DOCLING_SERVICE_KEY; canais e integrações: EVOLUTION_API_KEY · EVOLUTION_GO_INSTANCE_TOKEN · EVOLUTION_GO_GLOBAL_KEY/GLOBAL_API_KEY · N8N_API_KEY · TWILIO_AUTH_TOKEN · GOOGLE_OAUTH_CLIENT_SECRET · NOTION_OAUTH_CLIENT_SECRET; logins de portal: senhas da API InfoCap (Resulta e AutoFleet) · senhas do Agger (2 contas) · senha do Segfy — e as de P-PILOTO-09.
      **Onde:** no painel de cada provedor, gere a nova e **apague a antiga**; cole a nova no EasyPanel (smith-api →
      Environment; e no portal-worker, se ela existir lá) e clique Implantar.
      🔴 **Nunca cole a chave nova no chat.**

- [ ] **S116.4** *(opcional)* **Pedir "retenção zero" (ZDR) à OpenAI e à Anthropic**
      **Onde:** o formulário de vendas de cada uma — peça *"Zero Data Retention"* para a sua organização.
      **Por quê:** hoje o que o segurado escreve fica guardado no provedor pelo prazo padrão dele. Não bloqueia nada.

- [ ] **S116.5** *(opcional)* **Ligar o Gemini na bancada**
      **Onde:** ponha `GOOGLE_API_KEY` no arquivo `backend/.env` do seu computador (o mesmo nome que já está no EasyPanel) e,
      no Google AI Studio → Billing, confirme que o projeto está no **plano pago** — o gratuito usa os dados para treino.
      **O que esperar:** nada muda no produto; a próxima bancada passa a comparar o Gemini também.

- [ ] **S116.6** **Documentos (docling): `VISION_MODEL`** — **hoje, deixe como está**
      O serviço de documentos escolhe o modelo por essa variável, não pelo lugar único. Hoje o valor (`gpt-4o-mini`) é o
      mesmo da rota de documento, então nada a fazer. **Anote:** quando a rota de documento mudar, esta variável muda junto
      (P-S116-09).

- [ ] **S116.7** Apagar as variáveis que o produto deixou de ler → **T-07**

- [ ] **S116.8** **Decidir se apaga as 31 linhas de teste** que um teste gravou por engano no registro de custos (P-S116-11)
      São 📊 31 linhas do portal, sem corretora, custo zero, entre 17:43 e 17:47 UTC de 23/09. Nunca foram cobradas.
      **Para apagar:** peça no chat *"pode apagar as 31 linhas de teste do portal no ledger (P-S116-11)"*.
      **O que esperar:** a resposta mostra **31** apagadas. Outro número = pare e peça a conferência.

- [ ] **S116.9** O canário do atendimento → allowlist **T-23** · ligar **T-25** · "oi" **T-26** · foto **T-69** · CPF **T-28** ·
      *"Ela cobre eletricista?"* **T-17** · modelo efetivo **T-25** · desfazer **T-75**. *Se algo piorar:* nota no topo da lista.

- [ ] **S116.10** *(opcional)* **Confirmar a D-116-18** — no portal e na foto ficou o modelo de **maior margem** (GPT-6 Sol)
      e não o mais barato que empatou (GPT-6 Luna, 📊 ~1/15 do custo por acerto). Recomendação: manter o Sol até o canário
      e depois testar a Luna (Onda B). Se preferir já a Luna, é uma linha — peça no chat.

- [ ] **S116.11** Depois da SPEC-116-RESERVA: apagar as 3 variáveis velhas → **T-07** · conferir a reserva → **T-06**

---

## 0 · Antes de tudo — segurança e ambiente

### 0.1 As variáveis de ambiente, todas numa sentada

**Onde:** EasyPanel → `smith-api` → Environment (e, onde indicado, `smith-web` / `portal-worker`).
**Faça as três edições e só então clique Implantar uma vez** (tarefa 0.2).

📊 Conferido em 20/09/2026 pelo **nome**, contra o seu arquivo de credenciais e contra o código que lê cada uma.
Nenhum valor foi lido, impresso ou guardado.

| variável | serviço | está? | o que fazer | o que trava se esquecer |
|---|---|---|---|---|
| **`ADMIN_API_KEY`** | smith-api **e** smith-web | ✅ nos dois | nada | é **esta** que vale como "chave interna": o código aceita `BACKEND_INTERNAL_API_KEY` **ou** `ADMIN_API_KEY`, nesta ordem (`app/core/auth.py`). Sem ela o painel inteiro dá 401 |
| `BACKEND_INTERNAL_API_KEY` | smith-api / smith-web | ❌ ausente nos dois | **nada a fazer** — é o nome alternativo da mesma chave, e o `ADMIN_API_KEY` já cobre | — |
| **`ATTENDANT_INBOUND_ALLOWLIST`** | smith-api | ⚠️ **existe e está VAZIA** | **vazia é o certo para o piloto de verdade.** Preencha **só** para o ensaio de canário (bloco A/C), com o número do aparelho de teste — e **esvazie antes dos 3 dias** | preenchida no piloto = todo segurado fora da lista é ignorado **em silêncio**, e os 3 dias medem o vazio |
| **`JANELA_SILENCIO_EXCECOES`** | smith-api | ⚠️ **2 itens, e 1 deles NÃO é número de teste** | 🔴 **tire esse item.** 📊 conferido pelo **motor** do produto (`_variantes_do_telefone`), que casa com/sem `55` e com/sem o nono dígito — não por comparação de texto | esse número fica **fora** da janela de silêncio: o robô fala por cima da atendente naquela conversa, e de fora não há sintoma nenhum |
| `BILLING_CANARIO_ALLOWLIST` | smith-api | ✅ 2 itens | nada — o canário do bloco E exige **≥ 2** e recusa com 409 abaixo disso | bloco E não roda |
| `CANARIO_TESTE_B` | smith-api | ✅ 1 item, dentro da allowlist acima | nada | bloco E recusa com 409 |
| **`RESUMO_DIARIO_HORA`** | smith-api | ❌ ausente | opcional. Ausente = **19h**, no fuso da **plataforma**, não de cada corretora | se você quiser o resumo em outra hora, é aqui. Bloco B.5 |
| **`RESUMO_DIARIO_ATIVO`** | smith-api | ❌ ausente | opcional. Ausente = **ligado** | pôr `false` desliga o resumo das 19h |
| **`PRESENCA_DIGITANDO_LIGADA`** | smith-api | ❌ ausente | 🔴 **ponha `true`** se quiser rodar o caso A.8 | ausente = `false` no código (`app/core/config.py:110`): o "digitando…" **nunca aparece**, e o caso A.8 não tem como passar |
| `GLOBAL_KNOWLEDGE_COMPANY_ID` | smith-api | ✅ preenchida (identificador, 36 caracteres) | nada | é o "dono" da base de conhecimento global; sem ela a base cai num nome padrão e a destilação escreve no lugar errado |
| `POLICY_INTELLIGENCE_V2` | smith-api | ✅ **ligada** | nada | desligada = a Skill de apólice não roda e o canário da 001.5 mede o comportamento antigo. ⚠️ P-E0017-08: se você trocar o valor, use **`true`** e não `sim` — há um ponto do código que não aceita `sim` |
| `INSURER_DISPATCH_LIVE` | smith-api | ✅ **ligada** | nada | é o portão de **enviar mensagem à seguradora**. Ligada = o bloco C manda mensagem de verdade — por isso o bloco C só roda na sessão do canário |
| `DISPATCH_FINALIZE_MODE` | smith-api | ✅ `live` (4 caracteres) | nada | é o modo de **terminar** o chamado. Não é o mesmo portão do de cima: um diz "posso falar", o outro diz "o chamado abre de verdade ou cancela no fim" |
| **`DISPATCH_FINALIZE_MODE`** + **`DISPATCH_FINALIZE_LIVE_PLAYBOOKS`** | smith-api | 🔴 **corrigido em 20/09** | 📊 lido no código (`insurer_dispatch_service.py:349-380`): com `DISPATCH_FINALIZE_MODE=live` **TODOS os corredores abrem chamado de verdade** e a lista é **ignorada**. A lista só vale em `test`. **Para os seus testes (nenhum chamado real):** `DISPATCH_FINALIZE_MODE=test` e **apague** `DISPATCH_FINALIZE_LIVE_PLAYBOOKS`. **Para produção:** `DISPATCH_FINALIZE_MODE=live` (a lista pode ficar apagada). Confira no `/health`: `finalize_abre_de_verdade` | em `live` um teste seu despacha prestador de verdade |
| `ACIONAMENTO_FREIO_DE_EMERGENCIA` | smith-api | ❌ ausente | ausente = **freio solto** (certo). É a sua parada de emergência: pôr `true` derruba todo acionamento numa linha | guarde o nome. Num incidente é isso que você digita |
| `PORTAL_REAL_ENABLED` | **portal-worker** | ✅ ligada (só existe no bloco do portal-worker) | nada | desligada = o portal não abre; o bloco E.3 falha inteiro |
| `PORTAL_EFEITO_MATERIAL_LIBERADO` | smith-api **e** portal-worker | ✅ ligada nos dois | nada | é o que permite o portal **fazer** algo, não só olhar |
| **`GLOBAL_KILL_SWITCH`** | smith-web | ⚠️ **ligada** (= bloqueando) | 🔴 **deixe como está.** Hoje ela **não bloqueia o atendimento**: o único lugar que a lê é `lib/security/production-gates.ts`, usado por **uma** rota de diagnóstico (`/api/admin/security/production-gates`). Ela relata, não impede | nada trava por causa dela hoje. ⚠️ Mas o nome promete mais do que ela faz — não conte com ela como freio |
| `GLOBAL_KILL_SWITCH` | portal-worker | ✅ desligada | nada | — |
| **`ENVIRONMENT` × `ENV`** | smith-api | ✅ as duas, **com valores diferentes** | 🔴 **alinhe as duas** para o mesmo valor de produção | o backend lê **`ENV`** (`app/main.py:16`) e só para o Sentry: com `ENV` ≠ produção, os erros do ar chegam etiquetados como se fossem de desenvolvimento e a amostragem de rastro fica em 100% (mais custo). Nenhum comportamento do produto muda. `ENVIRONMENT` não é lido por nenhuma linha do backend |
| `BACKEND_URL` / `NEXT_PUBLIC_API_URL` | smith-api / smith-web | ✅ os dois apontam para o smith-api | nada | a tela abre e os blocos vêm vazios |

- [ ] **0.1.a–d** As quatro variáveis desta tabela → **T-08** (a allowlist do ensaio → **T-23**)

### 0.2 O Implantar único

- [x] **0.2** O Implantar único → **T-01** (feito 01/10)

- [ ] **0.3** O "oi" no chat do painel → **T-09**

### 0.4 As credenciais e as chaves — quando conveniente, antes de ter cliente pagante

- [ ] **0.4.a** ✅ **já feito** — o arquivo `CREDENCIAIS EASYPANEL.txt` **não está mais dentro da pasta do
      projeto**. 📊 conferido em 20/09: não há nenhum arquivo com esse nome na árvore do repositório.
      Mantenha-o fora. **Metade de P-PILOTO-09 fechada.** · **higiene**

- [ ] **0.4.b** **Rotacionar (trocar) as chaves que já foram coladas em chat.** Não é urgência de hoje;
      é uma tarde de trabalho antes de existir cliente pagando. A ordem abaixo é por **gravidade**:
      primeiro o que dá acesso a **todos os dados**, depois o que **gasta dinheiro**, depois o resto.

| ordem | variáveis (por nome) | onde se troca | por que nesta posição |
|---|---|---|---|
| 1 | `SUPABASE_SERVICE_ROLE_KEY` · `SUPABASE_SERVICE_KEY` · `SUPABASE_KEY` · `SUPABASE_ANON_KEY` · `NEXT_PUBLIC_SUPABASE_ANON_KEY` · `SUPABASE_DB_URL` | supabase.com → seu projeto → Project Settings → **API keys** (e **Database** para a senha do `SUPABASE_DB_URL`) | a service role **passa por cima de toda a separação entre corretoras**. É a chave que lê tudo de todo mundo |
| 2 | `ADMIN_API_KEY` · `ADMIN_TOKEN` · `SESSION_SECRET` · `APP_SECRET` · `SECRET_KEY` · `REVIEW_ENGINE_LINK_SECRET` | **você mesmo gera** (qualquer gerador de senha longa) e cola nos **dois** blocos, smith-api e smith-web | é o "sou o painel" do produto inteiro. Quem tem ela fala com a API como se fosse você |
| 3 | `ENCRYPTION_KEY` · `PORTAL_VAULT_KEY` | idem | 🔴 **não troque sem falar comigo antes**: são elas que abrem as senhas de portal já guardadas. Trocar sem re-criptografar deixa as credenciais das seguradoras ilegíveis |
| 4 | `ANTHROPIC_API_KEY` · `CLAUDE_API_KEY` | console.anthropic.com → **API keys** | gasta dinheiro seu |
| 5 | `OPENAI_API_KEY` | platform.openai.com → **API keys** | idem |
| 6 | `GOOGLE_API_KEY` · `GEMINI_API_KEY` · `GOOGLE_PLACES_API_KEY` | Google AI Studio (Gemini) e Google Cloud Console → Credentials (Places) | idem |
| 7 | `CORP_INFOCAP_RESULTA_PASSWORD` · `CORP_INFOCAP_AUTOFLEET_PASSWORD` | no próprio **InfoCap**, trocando a senha do usuário | dá acesso à carteira real das corretoras |
| 8 | `EVOLUTION_API_KEY` · `EVOLUTION_GO_GLOBAL_KEY` · `EVOLUTION_GO_INSTANCE_TOKEN` · `GLOBAL_API_KEY` (bloco do Evolution) | painel do serviço Evolution no EasyPanel → Environment (trocar e reimplantar o Evolution) | quem tem ela **manda mensagem pelo WhatsApp da corretora** |
| 9 | `REDIS_URL` (a senha vai embutida na URL) | EasyPanel → serviço do **Redis** → trocar a senha e atualizar a URL nos três blocos | fila, travas e cache |
| 10 | `MINIO_ROOT_USER` · `MINIO_ROOT_PASSWORD` · `MINIO_BACKUP_S3_ACCESS_KEY_ID` · `MINIO_BACKUP_S3_SECRET_ACCESS_KEY` | EasyPanel → serviço **minio** (e, no backup, no painel do provedor S3) | os documentos e apólices guardados |
| 11 | `TWILIO_ACCOUNT_SID` · `TWILIO_AUTH_TOKEN` | console.twilio.com → Account → **API keys & tokens** | telefonia; gasta dinheiro |
| 12 | `ELEVENLABS_API_KEY` · `DEEPGRAM_API_KEY` | elevenlabs.io → Profile → API key · console.deepgram.com → API keys | voz; gasta dinheiro |
| 13 | `N8N_API_KEY` · `BROWSERBASE_API_KEY` (+ `BROWSERBASE_PROJECT_ID`) | painel do n8n → Settings → API · browserbase.com → Settings | automações e navegador remoto |
| 14 | `GOOGLE_OAUTH_CLIENT_SECRET` · `NOTION_OAUTH_CLIENT_SECRET` | Google Cloud Console → Credentials → OAuth client · notion.so/my-integrations | login de terceiros |
| 15 | `DOCLING_SERVICE_KEY` · `TAVILY_API_KEY` · `FIRECRAWL_API_KEY` · `STRIPE_SECRET_KEY` · `STRIPE_WEBHOOK_SECRET` | cada painel próprio | menor exposição / pouco ou nada em uso |

📊 **Estão vazias hoje** (nada a trocar): `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `QDRANT_API_KEY`,
`SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `LANGCHAIN_API_KEY`, `LANGSMITH_API_KEY`,
`LANGSMITH_WORKSPACE_ID`, `ZAPI_INSTANCE_ID`, `ZAPI_TOKEN`, `ZAPI_CLIENT_TOKEN`, e `SENTRY_DSN` no smith-web.

**Depois de trocar qualquer uma: Implantar o serviço.** Variável nova só vale depois do Implantar.

- [ ] **0.4.c 🔴 TROCAR AGORA as senhas que estão nas capturas do Agger** (acrescentado em 22/09). As três
      capturas de tela (arquivos HAR) que vieram para a investigação do Agger foram gravadas na sessão de uma
      pessoa da corretora e contêm **a senha dela no Aggilizador** e **as senhas dos portais das seguradoras**
      (📊 22/09: as senhas dos portais aparecem em **todas** as 28 respostas de acompanhamento do cálculo —
      Research Pack da EXTRA-002 §1, §2.1). **O que fazer:** (1) trocar a senha desse usuário no Aggilizador;
      (2) trocar a senha de cada portal de seguradora cadastrado no Aggilizador; (3) **nunca** anexar esses
      arquivos a chat, drive ou e-mail; (4) apagá-los depois da parte 2 da EXTRA-002 (antes disso a execução
      extrai só as respostas, sem senha). **Não bloqueia nada, mas é a primeira coisa a fazer.** · **EXTRA-002 ·
      P-E002-HAR**
- [ ] **0.4.d Rodízio das credenciais de produção coladas no chat da sessão da EXTRA-002** (22/09: chaves de
      API, banco, portais). Elas passaram a existir em mais um lugar. É a mesma tabela do 0.4.b — só sobe a
      urgência. · **EXTRA-002 · P-PILOTO-09**

---

## 1 · Preparar o ensaio — pré-requisitos

- [x] **1.1** Reativar o grupo de suporte de cada corretora — 📊 20/09 ativo nas duas (P-E0017-01 fechada). A conferência de
      que cada grupo está **dentro** da sua corretora → **T-68** · **001.3 / 001.7**
- [ ] **1.2 a 1.5** Grupo de canário · número da casa · parear o celular · agente desligado até o ensaio → **T-23**

- [ ] **1.6 Saber onde o teste de apólice roda** · **001.1 / 001.6**
      ⚠️ A InfoCap tem um bloqueio conhecido (F-094-07): duas corretoras descriptografam para a **mesma
      conta**, e o adaptador recusa a segunda. Por isso os testes de **apólice** (bloco D) e de
      **cobrança** (bloco E) ficam na **Resulta**, só leitura ou envio ao seu número.

---

## 2 · Bloco D — a apólice certa, no chat do painel (001.1)

**Onde:** painel da **Resulta**, chat `core`, com a sua conta. Nada sai por WhatsApp.
**Anote cada um como:** ✅ passou · ⚠️ passou mas o texto ficou estranho · ❌ falhou (cole a resposta).

- [ ] **D.1 a D.7** → **T-10 a T-16** (na mesma ordem)

---

## 3 · Bloco D2 — a base de planos responde (001.5 e 001.5.2)

**Onde:** mesmo chat `core`, e o WhatsApp do aparelho de teste.
📊 A base já está publicada: **492 serviços, 108 planos, 8 seguradoras**. Não há mais fila para curar.

- [ ] **D2.0** → **T-18** · **D2.1** → **T-19** · **D2.2** chat → **T-20**, WhatsApp → **T-35** · **D2.3** → **T-20** · **D2.4** → **T-21** ·
      **D2.5** → **T-22**

---

## 4 · Bloco A — a conversa no WhatsApp (001.2)

**Onde:** WhatsApp do aparelho de teste (TESTE-A) escrevendo para a corretora de ensaio.
**Pré-requisito:** ligar o agente **só** para o ensaio. Ao fim do bloco, desligue de novo.

- [ ] **A.1 a A.8** → **T-27 a T-34** (na mesma ordem)

---

## 5 · Bloco B — o grupo da equipe (001.3)

**Onde:** painel da corretora de ensaio + o grupo de canário (tarefa 1.2).

- [ ] **B.1 a B.8** → **T-60 a T-67** (na mesma ordem)

---

## 6 · Bloco C — o acionamento ao vivo (001.4)

🔴 **Só na sessão do canário**, na corretora de ensaio. `INSURER_DISPATCH_LIVE` está **ligada**: o que
sair daqui sai de verdade para a seguradora.

- [ ] **C.1** → **T-40** · **C.2** → **T-41** · **C.3** → **T-42** · **C.4** → **T-43** · **C.5** → **T-52**

---

## 7 · Bloco E — a cobrança e os portais (001.6)

**Onde:** painel da **Resulta** (tela) + **console do serviço `smith-api`** (os dois comandos).
🔴 **Todo envio vai só para o seu número** — é o que `BILLING_CANARIO_ALLOWLIST` e `CANARIO_TESTE_B`
garantem; sem elas o comando recusa com **409** e não manda nada.

- [ ] **E.1** → **T-72** · **E.2** → **T-73** · **E.3** → **T-54** · **E.4** → **T-74**

---

## 8 · O piloto de 3 dias (001.7)

> ### 📖 Em linguagem de gente, antes de começar
>
> **"Ligar o agente"** é o botão **Ligar agente**, no painel, **em cada corretora**. É ele que faz o robô
> **responder os segurados no WhatsApp**. Com ele desligado, o sistema só **observa**: vê as conversas,
> guarda, não fala. Ligar é o que dá início ao piloto — e é a única coisa que muda o que o segurado vê.
>
> **"Canário"** é um **ensaio com um único celular de teste**, antes de soltar para clientes reais. No
> checklist, `--modo canario` quer dizer: *"nesta rodada, a lista de entrada estar preenchida só com o
> número de teste é o esperado"*. No piloto de verdade é o contrário — a lista tem de estar **vazia**,
> senão todo segurado que não estiver nela é ignorado em silêncio e os 3 dias medem o nada.
>
> **"Quando o agente errar"** é no **atendimento**: ele respondeu errado, ou respondeu fora de hora, a um
> segurado de verdade. 🔴 **Não desligue o agente.** A atendente **responde pelo celular naquela
> conversa** — isso cala o robô ali, só ali, na hora. Anote o que aconteceu. Isso **não** é erro da
> medição, e não invalida o piloto: é exatamente o tipo de coisa que o piloto existe para contar.
>
> **Quando termina:** depois de **3 dias úteis completos** com o agente ligado. No **4º dia** sai o
> veredito — e é uma coisa só, num chat novo (passo P4).
>
> **Você não precisa rodar nada no console.** O caminho recomendado é **pedir no chat**; eu rodo da
> minha máquina contra a produção, **só leitura**: nada envia mensagem, liga agente ou escreve no banco.

### P1 · Antes de ligar: o checklist

- [ ] **P1** O checklist de ligar → **T-24** (modo canário) e **T-77** (de verdade) · **P1.b** → **T-78** · **P2** → **T-79** ·
      **P3** → **T-80** · **P4** → **T-81**

---

## 8.5 · Bloco F — o portal de vidros (001.10 · 001.10.1)

> **O que mudou:** o robô aprendeu a abrir o pedido de vidro **em qualquer uma das 38 seguradoras** que o portal
> publica (antes eram 3, e nenhuma delas era a Yelum — 📊 o motor antigo escrevia **zero** nas capturas reais), e
> aprendeu a **ler o desfecho que o portal decidiu**: loja já escolhida, agenda com lojas e horários, analista ou
> vistoria. Ele devolve ao segurado o número do atendimento, a franquia e o próximo passo.
> **E agora (001.10.1), ele RETOMA um atendimento já aberto** — guarda o acesso cifrado, e quando a resposta do
> segurado chega (a agenda, uma preferência), ele volta ao portal, lê onde o pedido está e continua sozinho, em vez
> de terminar em mão humana.
>
> 🔴 **Nada disso está ligado.** Tudo mora atrás de uma chave que nasce desligada: `PORTAL_VIDROS_API_FIRST`.
> O que atende hoje continua sendo o caminho antigo. Implantar **não muda nada** no ar — e é de propósito.

- [x] **F.1** Implantar → **T-01** (feito 01/10); o `portal-worker` → **T-02**
- [ ] **F.2** O canário → ligar a chave **T-55** · o canário **T-56** · o portal destrava **T-57** · depois **T-58**
- [x] **F.3 As capturas que faltam** — chegaram em 21/09 e liberaram o agendamento (P-E00110-A1 FECHADA). O que
      ainda falta (fotos/vistoria, domicílio decidido fora, cancelar) está em P-E001101-05 e no bloco novo de
      pendências da 001.10.1. · **001.10 · 001.10.1**
- [x] **F.4 As 15 perguntas à atendente** — respondidas em 21/09. A nº 12 ("dá para retomar por número?") decidiu
      a 001.10.1, que já foi executada. · **001.10 · P-E00110-A11 (FECHADA)**
- [ ] **F.5 Rotacionar as credenciais** que foram coladas no chat de novo em 20/09. · **P-PILOTO-09**

---

## 8.6 · Bloco G — uma corretora não trava a outra (001.8)

> **O que mudou:** o atendimento passou a dar **4 vagas por corretora**, em rodízio: uma corretora com cinquenta
> mensagens de uma vez, com o modelo lento ou com o portal travado **não atrasa mais a vizinha**, e nada se
> perde — o que não cabe agora espera e é respondido depois. O robô também ganhou **relógio** (nenhuma chamada ao
> modelo passa de 90 s, nenhum atendimento passa de 300 s) e, quando o provedor de inteligência cai, as
> conversas ficam **guardadas** em vez de virarem "tive uma falha técnica". E a Central de Agentes passou a
> mostrar tudo isso **por corretora**.
>
> 🔴 **Nada disso precisa de configuração:** todas as chaves novas têm valor padrão no código. Implantar já liga.
> A única coisa que nasce desligada é o **aviso ao dono da corretora** quando a fila cresce — e ela deve
> continuar desligada por enquanto (tarefa G.7).

- [x] **G.1** Implantar → **T-01** (feito 01/10) · **G.2** e **G.3** → **T-03** · **G.4** → **T-38** · **G.5** → **T-39**
- [ ] **G.6 Decidir se cria um serviço separado só para as tarefas automáticas** (mesma imagem, com
      `SCHEDULER_ENABLED=true`, e a API passando a `false`). É **capacidade**, não isolamento: o código já sai
      pronto e nada quebra se você não criar. · **001.8**
- [ ] **G.7 🔴 NÃO ligue `ISOLAMENTO_AVISO_AO_DONO`** (o aviso ao dono quando a fila cresce) antes de a
      pendência **P-E0018-09** ser consertada: hoje o aviso reserva a janela de 30 minutos **antes** de tentar
      enviar, então um envio que falha queima a janela e o dono fica sem aviso nenhum. Ausente = não avisa, que é
      o certo por enquanto. · **001.8 · P-E0018-09**

**Bloqueia alguma coisa?** Só a G.5: sem o canário, o isolamento fica provado apenas por teste. As outras não
bloqueiam nada.

---

## 8.7 · Bloco H — cotar e renovar pelo Agger (EXTRA-002, parte 2)

> **O que a investigação descobriu (22/09):** a tela do Aggilizador é uma "casca" sobre um serviço que o
> computador consegue chamar diretamente — dispara o cálculo, espera, lê o resultado já padronizado por
> seguradora, com PDF. 📊 Em 2 cálculos medidos, as primeiras ofertas completas chegaram em 30 s e 229 s, e o
> conjunto fechou em ~7 min. Ou seja: **tecnicamente dá**. O que falta é **só da sua mão**: a permissão da Agger,
> um usuário próprio para o robô e a senha dele guardada no produto. Sem isso, a prova ao vivo (parte 2) não
> roda — e a Renovação Feita (EXTRA-003) não tem motor.
>
> 🔴 **Antes deste bloco: o 0.4.c** (trocar as senhas que estão nas capturas).

- [ ] **H.1 Confirmar a conexão "InfoCap RESULTA" que está dentro da Amandus.** 📊 Ela foi criada em 21/09 às
      20:29 **sob a corretora Amandus**; a Resulta ficou sem conexão InfoCap que funcione. **Onde:** painel →
      conexões da Amandus. **O que decidir:** foi de propósito? Se **não**, diga no chat e a execução a recria
      na corretora certa, com prova de isolamento. **Bloqueia:** o experimento E0 (quantas renovações de
      automóvel por dia) para a Resulta. · **EXTRA-002 · P-E002-X1**
- [ ] **H.2 Conversar com a Agger** — três perguntas, na mesma conversa: (1) existe **API oficial** ou acordo
      de integração? (2) se não, vocês **autorizam por escrito** o acesso programático pelos mesmos endereços
      que a tela usa? (3) quanto custa **um usuário a mais** (o do robô)? 🔴 **Sem essa autorização, nenhuma
      automação** — nem por navegador. **Bloqueia:** E1–E4 da parte 2. · **EXTRA-002 · D-E002-01**
- [ ] **H.3** → **T-120** (05/10, v2.5.1) · **Criar o usuário robô no Aggilizador** da Resulta (e da AutoFleet), com um nome que diga o que é
      (💭 ex.: "AutoBrokers"). **Por quê:** o Aggilizador aceita **uma sessão por usuário** — se o robô usasse o
      login de uma pessoa, ele a derrubaria no meio do trabalho. **Bloqueia:** E1. · **EXTRA-002 · D-E002-02**
- [ ] **H.4 Guardar a senha do robô no AutoBrokers**, na **tela de conexões** da corretora — **nunca** em
      arquivo, chat ou e-mail. **Bloqueia:** E1. · **EXTRA-002**
- [ ] **H.5 Decidir D-E002-01 a 08** (ver §10, linha 14). Todas já vêm com a opção recomendada e a nota; se
      você não disser nada, a execução segue a recomendação. **Não bloqueia.** · **EXTRA-002**

**Bloqueia alguma coisa?** H.2, H.3 e H.4 bloqueiam a parte 2 inteira (e, com ela, a EXTRA-003). H.1 bloqueia
só a medição de volume da Resulta.

---

## 8.8 · Bloco I — a apólice não se perde no meio do atendimento (117)

> **O que mudou:** quando o agente do WhatsApp descobre a apólice do segurado, ela agora **fica no caso até o fim**.
> Antes ela sumia: o agente já tinha a apólice na mão e, na hora de acionar a seguradora ou abrir o portal, o **ramo**
> (automóvel, residencial) voltava a ser palpite do modelo — inclusive contra a sua decisão de 17/09, de que **o ramo da
> apólice manda**. 🔴 A causa era estrutural: a peça que monta esse contexto exigia **CPF ou nome crus**, e o agente que
> fala com o segurado só recebe a versão mascarada — então o contexto **nunca nascia** no WhatsApp, e toda regra pendurada
> nele estava desligada sem ninguém saber. Agora existe **um lugar só** que escolhe a apólice do caso, ela é gravada na
> ficha do atendimento, e **todos** leem a mesma: o acionamento da seguradora, o portal de vidros, o aviso à pessoa que
> assume o caso e a resposta seguinte. Nenhum dado pessoal cru chega ao modelo — o cliente viaja como **apelido opaco**.
>
> 🔴 **Nada aqui precisa de configuração nova:** nenhuma variável é obrigatória e 📊 **não houve nenhuma mudança de
> banco**. Relatório: `reports/SPEC-117-EXECUTION-REPORT.md`.

- [x] **I.1** Implantar → **T-01** (feito 01/10) · **I.2** O canário de duas corretoras → **T-37**
- [ ] **I.3 Decidir a P-S117-08** — criar ou não uma **variável própria** para o apelido opaco do cliente
      (`POLICY_CONTEXT_HMAC_KEY`). **Hoje funciona sem ela:** o código usa a chave de cifra que já existe no ambiente
      (`ENCRYPTION_KEY`), e o apelido continua estável e isolado por corretora. O certo pelo manual europeu de
      pseudonimização (ENISA) é ter a chave do apelido **separada** da chave de cifra. **Não bloqueia nada** — se algum
      dia o `ENCRYPTION_KEY` faltar, o apelido enfraquece sem ninguém notar. · **117 · P-S117-08**

**Bloqueia alguma coisa?** 🔴 **Nada aqui bloqueia a entrega** — a SPEC está pronta e provada por teste, e nada nela
espera terceiro. O **I.1** é o que leva a mudança ao ar; o **I.2** é o que a prova na vida real (sem ele, o isolamento e
o ramo oficial ficam provados só por teste); o **I.3** é uma melhoria de segurança que pode esperar.

---

## 8.9 · Bloco J — o formulário dentro do WhatsApp deixa de parar o acionamento (118)

> **O que mudou, em uma frase:** quando a seguradora abre aquele **formulário dentro da conversa** — a telinha com
> campos para preencher, que o WhatsApp mostra sem sair do chat —, o produto agora sabe respondê-lo **sozinho** na
> Porto, e o agente pergunta antes, em português, o que a seguradora vai exigir lá dentro.
>
> 🔴 **E uma coisa que eu te pedi errado, e agora está medida:** eu pedi um **rebuild da imagem do WhatsApp**. Não era
> preciso. 📊 Em 26/09 às 17:24 a prova rodou contra o serviço no ar e o envio de resposta de formulário **funcionou na
> primeira tentativa certa** (HTTP 200, `Type: "InteractiveResponseMessage"`), com a tentativa de controle — sem o
> embrulho — devolvendo erro 479. O catálogo do serviço (`swagger`) não lista a rota, mas a rota existe: **o catálogo
> estava incompleto, não o serviço.** A pendência **P-62**, que repetia o pedido de rebuild há semanas, foi fechada.
>
> **O que mais mudou:** a **Tokio** deixou de fingir que atende. 📊 Em 52% das conversas dela o atendimento termina num
> **link** da seguradora, e não num protocolo — então o caso passa a ir para uma pessoa **com o dossiê pronto**, em vez
> de ficar preso até o vigia perceber. (E havia um defeito grave aí: a entrega para uma pessoa era **inalcançável** no
> código — o segurado era simplesmente abandonado.)

- [x] **J.1** Implantar → **T-01** (feito 01/10) · **J.2** O canário do formulário → **T-46**
- [ ] **J.3 Decidir a `D-118-01` — quando abrir a finalização para todas as seguradoras.** Você pediu *"todas
      liberadas, para não ter confusão depois"*. **A recomendação da execução é o contrário, e por um motivo concreto:**
      hoje a lista `DISPATCH_FINALIZE_LIVE_PLAYBOOKS` aceita um nome escrito errado **e não avisa** — o corredor
      simplesmente nunca fecha o chamado, em silêncio. Enquanto os testes correm, o modo `test` + a lista explícita é o
      estado mais seguro (é o que está no ar hoje: Porto e Yelum). Depois do canário do J.2, troque para
      `DISPATCH_FINALIZE_MODE=live` e **apague a lista** — aí todas ficam liberadas, sem lista para esquecer.
      **Onde:** EasyPanel → `smith-api` → Environment. · **118 · D-118-01 · P-118-15**
- [ ] **J.4** As capturas da Azul, Mapfre e Tokio → **T-50** (m, l) · **118 · P-118-01 · P-118-02 · P-118-03**

**Bloqueia alguma coisa?** ⛔ **Não.** Nada nesta entrega espera terceiro, chave ou pagamento. O **J.1** leva ao ar; o
**J.2** é o que prova na vida real; o **J.3** é sua decisão e pode esperar o J.2; o **J.4** é coleta de material, e cada
captura vale uma rota a mais no painel.

---

## 9 · Depois de tudo — desfazer o ensaio

- [ ] **9.1 a 9.5** → **T-75** · **9.6** → **T-76**

---

## 10 · Decisões suas em aberto

| # | a decisão | o que está em jogo | onde está registrada |
|---|---|---|---|
| 1 | **D-E0017-03 · os cortes do veredito do piloto** | são os quatro números do P4. Até você decidir, a régua publica as notas e **não** publica o veredito | `FOUNDER-DECISIONS.md` |
| 2 | **D-E0017-04 · os escritores que faltam entram antes dos 3 dias?** | 📊 três das seis notas do atendimento não têm como ser gravadas pelo produto hoje (P-E0017-03). **Já resolvido pela via do avaliador por amostra** (P4) — falta você dizer se concorda em rodar o piloto assim, ou se prefere adiar ~1 dia para construir os escritores | `FOUNDER-DECISIONS.md` · P-E0017-03 |
| 3 | **`write:true` tira a escrita de 2 pessoas** | 📊 `admin_company` 8 · `member` 2, e os dois `member` estão em corretoras diferentes. Eles param de poder mexer em destino de suporte, credencial de portal e conexão de WhatsApp | relatório 001.3, caixa #3 |
| 4 | **CPF/CNPJ aparece no 🆘 e no 🚨** e fica no histórico do grupo para sempre | a SPEC pediu assim. É decisão de privacidade, não técnica: você quer mesmo? | relatório 001.3, caixa #8 |
| 5 | **A hora do resumo diário** | 19h é o padrão, e é a variável `RESUMO_DIARIO_HORA`. ⚠️ hoje é o fuso da **plataforma**, não de cada corretora | relatório 001.3, caixa #4 |
| 6 | **Ler os quatro modelos de mensagem do grupo** e dizer o que cortaria | 💭 a copy é ilustrativa de propósito. Sem a sua leitura, a validação com a Saionara e a Regina não fecha | relatório 001.3, caixa #5 |
| 7 | **O canal do grupo** (P-E0014-06): ligar grupos na instância — 📊 240 mensagens/min a mais — **ou** botões AGENTE / EU CUIDO na Fila | hoje a atendente que responde **no grupo** não é ouvida; só vale o privado do número de suporte e dos números da casa | relatório 001.4, caixa |
| 8 | **O nome do agente da Resulta** | a SPEC entregou o mecanismo; o nome é seu | relatório 001.2 · P-E0012-D3 |
| 9 | **As senhas de Allianz e Mapfre** para os portais | sem elas o bloco E.3 continua com duas seguradoras de fora | relatório 001.6 |
| 10 | **Destilar as seguradoras que faltam** — a ordem pelo prêmio da carteira está em `providers/susep/fila-onda-3.json` (19 seguradoras) | a base cresce **sem código novo**; hoje 8 seguradoras respondem | relatório 001.5 / 001.5.1 |
| 11 | **D-E00110-F1 · o contato do segurado no portal — `RESOLVIDA`** | você escolheu: corretor como solicitante declarado + celular e e-mail do **segurado** como contato, com WhatsApp marcado. É o desenho que a 001.10.1 já entrega (D-E001101-04); só falta o canário provar que o portal aceita | `FOUNDER-DECISIONS.md` |
| 12 | **D-E00110-F2 · quando ligar `PORTAL_VIDROS_API_FIRST`** | ✅ **AUTORIZADA** por você (01/10, D-124-F): ligar **junto com o canário**, com allowlist; abrir a todos só depois do canário verde. Passo a passo → **T-55** a **T-58** | `FOUNDER-DECISIONS.md` |
| 13 | **D-E00110-F3 · a 001.10.1 (a continuação) entra antes da 001.8? — `CUMPRIDA`** | sim: a 001.10.1 foi executada em 24/09/2026 (nota 88), antes da 001.8 seguir para canário | `FOUNDER-DECISIONS.md` |
| — | **D-E001101-01…07 (001.10.1)** — todas tomadas pela execução, nenhuma aberta para você | token no cofre do worker (88) · agendar pela preferência + continuação (90) · e-mail do corretor = Perfil de Acionamento (90) · contato do segurado + WhatsApp (88, fecha a F1) · domicílio fora (sua decisão) · `BloqueadoIlhaNormal` deixa de travar (90) · peça reescrita com pedido esperando resposta vira continuação (85) | `FOUNDER-DECISIONS.md` |
| 14 | **D-E002-01 a 08 · o Agger, a renovação e a fila** (22/09, propostas) | as oito já vêm com a recomendação: pedir à Agger a **API oficial e a autorização** na mesma conversa, sem autorização nenhuma automação (01: 92 × 84 × 58 × 25) · **usuário robô** por corretora (02: 95) · calcular em D-30 e **recalcular** perto do fechamento, porque a cotação vale 5 dias (03: 88) · **o corretor revisa e envia** (04: 92) · **rótulos transparentes** em vez de "a melhor" escolhida por IA (05: 94) · a 003 em **duas partes**, fundação e ciclo (06: 88) · a posição na fila (07: 78 × 65 — diferença pequena, é a que mais precisa de você) · o Agger como porta **de cotação**, não de gestão (08: 90) | `FOUNDER-DECISIONS.md` · proposta 002 §10 |
| 15 | **P-S117-08 · a chave do apelido opaco do cliente** | hoje o apelido do cliente é derivado com a chave de cifra que já existe (`ENCRYPTION_KEY`) e funciona; o certo pela ENISA é uma chave **separada** (`POLICY_CONTEXT_HMAC_KEY`). **Não bloqueia nada**: se o `ENCRYPTION_KEY` faltar um dia, o apelido enfraquece em silêncio | `PENDENCIAS.md` P-S117-08 · bloco **I.3** |
| 16 | **D-118-01 · quando abrir a finalização para TODAS as seguradoras** | você pediu *"todas liberadas, para não ter confusão depois"*. A recomendação da execução (nota 88 × 55 × 40) é o contrário **enquanto os testes correm**: `DISPATCH_FINALIZE_MODE=test` + a lista explícita — que é o estado no ar hoje (📊 Porto e Yelum) —, e só **depois do canário do J.2** trocar para `live` e **apagar a lista**. O motivo é concreto: a lista aceitava um nome escrito errado e não avisava; o corredor nunca fechava o chamado, em silêncio. ✅ Isso virou **defeito visível** no `/health` nesta SPEC (`finalize_refs_fantasma`) | relatório 118 · D-118-01 · P-118-15 |

---

## SPEC-119 — o que só você faz (28/09/2026) · os corredores ficam prontos para a vida real

> 🔴 **Nada aqui é urgente e nada bloqueia o produto.** São **capturas** — conversas de verdade
> que precisam acontecer com o observador ligado. Cada uma resolve uma rota, e **nenhuma linha de
> programa substitui uma delas.**

### 119.A · Ler a aba CORREDORES de novo — ela mudou de verdade

`[ ]` Abra o painel, aba **CORREDORES**. O que você vai ver de diferente:

```
antes   mapfre / auto / guincho ....... 72 pedidos
hoje    mapfre / auto / guincho ....... —   (nenhuma conversa desta rota no acervo)
```

📊 **Aquele 72 nunca foi da Mapfre.** Era o total de guincho somando **sete** seguradoras, medido
em **21/08/2026**, impresso igual nas dez linhas de guincho. A maior rota de guincho de verdade,
medida em **28/09** nas conversas reais, é a **Allianz** com **29** — e a Mapfre tem **zero**.

⚠️ **Onde a página mostrar `—`, leia "não sabemos", nunca "ninguém pediu".** São coisas
diferentes, e a aba tem uma seção no fim dizendo quantas conversas existem sem etiqueta.

### 119.B · As capturas que destravam rota — uma conversa cada

`[ ]` **Guincho na Mapfre** → **T-49** · **As 31 rotas sem uma única conversa** → **T-50** (n)

### 119.C · A decisão que sobra para você

`[ ]` **`carro reserva` vira corredor?** 📊 O segurado pede: **126 telas** e **13 conversas** no
acervo (Yelum 10, Tokio 2, Mapfre 1). E **não existe um único passo escrito** para ele — o produto
não atende. ⚠️ **Não precisa de captura nova**: o material já está gravado; precisa de uma SPEC.
Isto é a **P-119-05**.

`[ ]` **Condomínio e a Tokio continuam fora?** A Tokio entrega **link** (📊 5 de 5 conversas
residenciais dela), e condomínio está fora de escopo por decisão sua de 21/08. As duas coisas
aparecem como "100% sem etiqueta" na medição — e é **por desenho**, não por defeito. Se mudou de
ideia, é uma SPEC nova.

| # | tarefa | por que importa | onde |
|---|---|---|---|
| 17 | **ler a aba CORREDORES** | a coluna `pedidos` mudou de significado; o `—` agora quer dizer "não medido" | painel, aba CORREDORES |
| 18 | **1 acionamento de guincho na Mapfre** → **T-49** | é o gate **G2**, e ele **não se cumpre com código** | WhatsApp da corretora · P-119-01 |
| 19 | **decidir se `carro reserva` vira corredor** | 13 conversas pedindo, zero passos escritos | P-119-05 |

---

## Apêndice · O que o produto ainda não sabe medir sozinho

Não é tarefa sua — é para você saber o que **não** esperar do relatório do piloto (`PENDENCIAS.md`):

```
P-E0017-03  três dimensões do atendimento não têm escritor: "apólice certa em 1 rodada",
            "sabe calar" e "fala como humano". Por isso existe o avaliador por amostra do P4
P-E0017-04  o chat principal grava "success" em 100% das linhas — a coluna não consegue
            discordar. "Confiabilidade" e "completude" do chat saem NÃO AVALIADA
P-E0017-05  o aviso de caso parado conta VARREDURAS, não casos: o diário enche de ruído
P-E0017-06  o porteiro do botão "Ligar agente" libera quando não consegue conferir, e não
            avisa que não conferiu. O checklist do P1 NÃO herda esse defeito — o botão, sim
P-E0017-07  num dia de banco instável, o resumo das 19h pode dizer "sem acionamentos hoje"
            em vez de "não consegui ler o dia"
P-E0017-08  POLICY_INTELLIGENCE_V2 é lida em dois lugares com listas diferentes: use "true"
```

---

## SPEC-120 — os corredores com conversa atendem sozinhos (29/09/2026)

📊 No simulador, 24 → **31** das 73 rotas atendem sozinhas (`simular_corredor.py --todas`, commit `7844542`).
Nada foi testado com seguradora de verdade: estes passos são o que falta antes de mandar a Resulta e a AutoFleet ligarem.

1. **Implantar** → **T-01** (feito 01/10) · o "oi" → **T-09**
2. **O dossiê no grupo** → **T-60** e **T-61**
3. **Acionamentos reais** → Yelum **T-45** · Porto com o pin **T-46** · Allianz residencial **T-47** · o ✅ no grupo **T-63** · o resumo das 19h **T-64** ·
   o robô parou numa tela **T-51**
4. **Decidir** D-120-B (preço da bateria na Porto + "posso continuar?": recomendo perguntar ao segurado, 85) e D-120-C (amperes com preço: recomendo manter com pessoa, 80).
5. Quando der: as 6 rotas de P-120-02 → **T-50**


---

## SPEC-121 — o grupo só ouve quando precisa, e mais rotas atendem sozinhas (30/09/2026)

⏳ **Estado em 30/09/2026: PENDENTE — você disse que faz estes testes no fim.** Continuam valendo como estão abaixo.

📊 O grupo de suporte: os 29 avisos errados de 21/09 viram **zero** no teste (commit `823a845`). Agora só chega ao grupo aviso
de conversa quando **o agente está ligado**, **foi o agente quem pediu ajuda** e **nenhuma pessoa da corretora falou na conversa
nos últimos 7 dias**. 📊 No simulador: **31 de 76** rotas atendem sozinhas (eram 31 de 73; entraram 3 de carro reserva).
O Sonnet 5 saiu do sistema e o Sonnet 5.5 entrou (a mudança no banco já foi aplicada e conferida).

1. **Implantar** → **T-01** (feito 01/10)
2. **O número de carro reserva da Yelum** → **T-48**
3. **Limpar as variáveis antigas de modelo** (P-121-07) → **T-07**
4. **Os acionamentos reais que faltam** (P-121-03) → **T-50**
5. **Decidir o "Admin Intervention"** (P-121-18). Quando alguém pausa uma conversa pelo painel, ela nunca volta ao agente,
   nem com mensagem nova depois de 7 dias. Opções: continuar assim (a pausa do painel é para sempre) · ou tratar como a regra
   dos 7 dias (mensagem nova depois de 7 dias volta ao agente). Recomendo **a regra dos 7 dias, 70 × 60** — as notas estão
   perto, então é escolha sua.
6. **Conferir o grupo da terceira corretora do piloto** (C3 no relatório): grupo de suporte **ativo** e agente **desligado**.
   O teste → **T-68**. A decisão (se o grupo dela continua ativo) segue sua.
7. **Pergunta que continua aberta para a atendente:** por qual canal a Allianz, a Bradesco e a HDI atendem carro reserva?
   Até ela responder, esses pedidos vão para uma pessoa da corretora, por decisão sua de 29/09.


---

## SPEC-122 — o agente pensa, com prova, e o GPT-6.1 Sol sucede o Sol 6 (30/09/2026)

⏳ **Os testes da SPEC-121 (bloco acima, S121.1 a S121.7) continuam pendentes** — você disse que faz no fim. Nada da 122
depende deles, e nada deles foi feito por aqui.

📊 O que mudou: o **GPT-6.1 Sol** substituiu o Sol 6 nos 7 trabalhos que usavam o Sol 6 e na reserva do acionamento, cada um
com o mesmo esforço de antes (a mudança no banco já foi aplicada e conferida; 📊 teste real com US$ 0,0073). O "cérebro" que
responde à seguradora quando a URA sai do roteiro foi **medido pela primeira vez** (📊 92 casos reais mascarados, 30/09):
nenhuma versão passou na régua de "zero erro grave", então **nada ganhou autonomia** — o acionamento continua no Opus 5.5,
e o cérebro novo só pode rodar **em sombra** (decide ao lado, não envia nada). O que muda para o segurado: na Porto, HDI,
Yelum e Zurich, quando a URA pede algo que só ele sabe (ex.: "o local é seguro, escuro ou deserto?"), o agente **pergunta
a ele** com as opções da tela, em vez de passar a uma pessoa.

1. **Implantar** → **T-01** (feito 01/10)
2. **Conferir três variáveis pelo nome** (P-122-02) → **T-07**
3. ⚠️ **(01/10) Substituído pela S123.3** — a sombra da 122 deu lugar ao destravador; este SQL agora põe o DESTRAVADOR em sombra.
   **Ligar a sombra, quando quiser** (P-122-16) — **não é obrigatório**, e não muda nada do que vai à seguradora nem ao
   segurado. Só depois do passo 1. No Supabase, **SQL Editor**, cole e rode (liga a sombra na **Porto**, para todas as
   corretoras):
   ```sql
   insert into public.cerebro_modos (company_id, insurer_key, ramo, modo, motivo, ligado_por)
   select id, 'porto', 'todos', 'sombra', 'SPEC-122: medir o cerebro V2 em sombra', 'Founder'
     from public.companies
   on conflict (company_id, insurer_key, ramo)
   do update set modo = 'sombra', motivo = excluded.motivo, ligado_por = excluded.ligado_por, updated_at = now();
   ```
   **Esperar:** "Success" e o número de linhas = o número de corretoras. Para conferir:
   ```sql
   select insurer_key, ramo, modo, count(*) as corretoras from public.cerebro_modos group by 1, 2, 3;
   ```
   → uma linha `porto · todos · sombra · N`. Vale em até 1 minuto.
   **Depois de alguns acionamentos da Porto**, para ver se ela está medindo e quanto custa:
   ```sql
   select count(*) as telas, min(created_at) as primeira, max(created_at) as ultima
     from public.work_events where event_type = 'cerebro.sombra';
   select count(*) as chamadas, round(sum(total_cost_usd)::numeric, 4) as dolares
     from public.token_usage_logs where service_type = 'cerebro_sombra';
   ```
   💭 Custo esperado: perto de US$ 0,02 a 0,03 por tela em que a URA sai do roteiro (📊 o Opus custou US$ 0,0209–0,0272 por
   chamada na bancada de 30/09). **Para desligar**, a qualquer momento:
   ```sql
   update public.cerebro_modos set modo = 'off', updated_at = now() where insurer_key = 'porto';
   ```
   ⚠️ O modo "ligado de verdade" **não existe**: o banco recusa. Ele só virá numa SPEC, depois de 2 semanas ou 50 telas
   reais em sombra sem erro grave (P-122-17).
   **Se der erro** `violates foreign key` ou `relation "cerebro_modos" does not exist`: a tabela não está no banco — mande o
   print no chat (a migration foi aplicada em 30/09 e conferida pelo juiz).
4. **O canário** (a pergunta ao segurado na tela de *situações de risco*) → **T-43**
5. **Autorizar, se quiser, ~US$ 0,50 para completar a medição do Opus** (P-122-03) — a bancada parou no teto de US$ 2 por
   provedor e mediu o Opus em 15 das 32 armadilhas. Não bloqueia nada; só deixa a comparação 6.1 × Opus completa.


## SPEC-123 — o agente destrava: decide, pergunta ao segurado, registra e aprende (01/10/2026)

⚠️ **Os testes das SPECs 121 e 122 (blocos acima) continuam pendentes** — nada da 123 depende deles.

📊 O que mudou: quando o roteiro fixo trava no WhatsApp da seguradora, existe agora um **destravador** — ele lê o caso, a
conversa com o segurado e as telas, e decide: seguir em frente ("Continuar"), responder com um dado que o caso já tem,
**perguntar ao segurado** o que só ele sabe, ou chamar uma pessoa no que é irreversível (custo, sinistro, cancelar, novo
pedido, trocar o titular, confirmar a abertura). Pela sua ordem (D5), ele foi **ligado** em todas as corretoras que têm agente de atendimento, nas 10
seguradoras (📊 01/10: `cerebro_modos` = 40 linhas `on`, limiar 70) — mas 📊 **0 de 4** agentes de atendimento estão ligados
hoje, então **nada acontece até você ligar o agente de uma corretora**. "Escolher sozinho entre opções" (o DEDUZIR) ficou **desligado**: 📊 o modelo acertou 6 de 14 vezes com
nota alta (`reports/SPEC-123-BANCADA.md`). Na bancada com 69 travas reais, 📊 **42 (61 %) foram destravadas certo sem
pessoa** e 62 (90 %) sem pessoa e com segurança — antes era 0 %.

🔴 **O que muda NO IMPLANTAR, mesmo sem ligar nada** (vale para todas as corretoras):
- a pergunta ao segurado passa a valer nas **10 seguradoras** (antes só Porto, HDI, Yelum e Zurich), com prazo de **2 min**
  na Allianz, Alfa, Mapfre e Azul e **3 min** nas outras; se a URA fechar antes da resposta, o caso fica guardado e é
  **reaberto** quando o segurado responder (no máximo 2 vezes), sem abrir pedido duplicado;
- `yelum/auto/guincho` passa a atender sozinho (📊 31 → 32 de 76 rotas);
- na Allianz residencial, a lista com **vários endereços** escolhe o endereço do caso (antes mandava "1" às cegas); se nenhum
  casar, vai a uma pessoa;
- o agente de atendimento, quando quer chamar uma pessoa por **dúvida** ou **dado que falta**, tenta resolver **uma vez**
  antes (1 por conversa por dia). Sinistro, condomínio, empresarial e quem **pede** uma pessoa continuam indo direto.

### S123.1 · Implantar
✅ **Feito em 01/10/2026** → **T-01**.

### S123.2 · Ver o diário
→ **T-43** (a linha em Decisões do agente e em `/admin/decisoes`) · **T-52** (as contagens e o custo, SQL) · **T-53** (isolado
entre corretoras).

### S123.3 · Ver, desligar ou só observar o destravador
📊 **Já está ligado** (migration `20261001_02`, 01/10): 10 seguradoras × 4 corretoras com agente de atendimento = 40 linhas
`on`, limiar 70 (D-123-K, decidida pela execução sob a sua D5). Ele só age quando o agente de atendimento da corretora estiver
ligado. Para mudar, no Supabase → **SQL Editor**, cole UM destes:

**Ver o que está ligado** (✅ conferido por você em 01/10 → **T-05**) — esperar 40 linhas, todas `on` e `70`:
```sql
select insurer_key, modo, limiar from cerebro_modos order by 1;
```
**Desligar UMA seguradora** (exemplo: Porto) — o roteiro volta a ser o de antes, nessa seguradora:
```sql
update cerebro_modos set modo='off' where insurer_key='porto';
```
**Só observar (sombra)** — ele anota no diário o que faria, mas não faz:
```sql
update cerebro_modos set modo='sombra' where insurer_key='porto';
```
**Desligar TUDO** — volta exatamente ao de antes:
```sql
delete from cerebro_modos where ligado_por='migration 20261001_02_spec123_destravador_ligado';
```
**O diário** — as últimas 20 decisões, em português:
```sql
select created_at, seguradora, classe, acao, nota, explicacao_para_gente from diario_de_decisoes order by created_at desc limit 20;
```
**Esperar hoje:** o diário **vazio** — é o certo enquanto nenhum agente de atendimento estiver ligado. **Se der erro** em
qualquer um destes comandos: mande o print no chat.

### S123.4 · Os testes reais sugeridos
→ Yelum guincho **T-45** · a pergunta ao segurado **T-43** (e o prazo **T-44**) · a dúvida simples **T-35** e a segunda chance
**T-36** · as rotas que faltam e os vários endereços da Allianz **T-50** e **T-47**.

### S123.5 · Decisões suas (`FOUNDER-DECISIONS.md`)
- **D-123-K** — onde ligar o destravador: **DECIDIDA pela execução** (sua D5, nota 85): ligado em todas as corretoras com
  agente de atendimento, nas 10 seguradoras. Para mudar, S123.3.
- **D-123-L** — o diário guardar a tela **completa** (com dado pessoal) para a corretora dona: coluna nova **65** × manter
  só a mascarada **60** — notas próximas, decisão sua.
- **D-123-M** — liberar o "escolher sozinho" sem calibração: manter desligado **85** × liberar **35** — já vem decidida;
  confirme se quiser.
- Verba opcional: 💭 ≈ US$ 1 por provedor para calibrar o "escolher sozinho" (P-123-01).

## SPEC-124 — o portal de vidros destrava com a mesma régua, e a leitura de documentos no modelo certo (01/10/2026)

📊 O que mudou:
- **A leitura de fotos e documentos ficou ~18 vezes mais barata, com o mesmo acerto medido.** A foto que o segurado manda
  (CNH, documento do carro, apólice fotografada) e a imagem dentro de PDF passam a ser lidas pelo **GPT-6 Luna** em vez do
  GPT-6.1 Sol: 📊 na bancada de 30 leituras, os dois acertaram **100 %** dos campos importantes (nome, CPF, placa, apólice,
  vigência, coberturas, valores), e a Luna custa 📊 US$ 0,0002 por leitura contra US$ 0,0037. ⚠️ Os documentos da bancada são
  **fabricados** (não havia documento real sem dado pessoal): o número é o melhor caso, não a garantia. Se a OpenAI cair, a
  foto passa ao **Claude Sonnet 5.5**. Isto **já está valendo no banco** e entra no ar no Implantar do `smith-api`.
- **O leitor de documentos (docling) passa a usar o modelo que o catálogo manda**, em vez de uma variável própria, e o custo
  dele passa a aparecer na conta.
- **O portal de vidros ganhou a mesma régua do WhatsApp**: quando o caminho novo do portal para numa pergunta, o mesmo
  destravador da SPEC-123 decide, continua o MESMO pedido (sem abrir outro) e anota no diário. 🔴 **Mas, hoje, ele não
  responde nada sozinho**: ele pergunta ao segurado ou chama uma pessoa — porque "escolher sozinho" segue desligado (SPEC-123)
  e porque o único caso em que respondia sozinho (o estado do serviço) estava **errado** e foi consertado para perguntar.
  E 📊 o portal de vidros **não roda desde 10/07**, e o caminho novo (onde isto foi plugado) **nunca rodou em produção** —
  ele só é usado se você ligar `PORTAL_VIDROS_API_FIRST` (D-124-F). O caminho antigo do portal continua como estava.

### S124.1 · Implantar
✅ **Feito em 01/10/2026** → **T-01**. O docling com imagem → **T-70**.

### S124.2 · Um teste real da leitura de foto
→ **T-69**.

### S124.3 · Decisões suas (`FOUNDER-DECISIONS.md`)
- **D-124-F** — ligar o caminho novo do portal de vidros (`PORTAL_VIDROS_API_FIRST`): **AUTORIZADA por você** — ligar junto com
  o primeiro canário de vidro, com allowlist. O passo a passo → **T-55** a **T-58**.
- Já decididas pela execução (confirme se quiser): Luna nas duas leituras (D-124-A, 88) · reserva só na foto (D-124-B, 85) ·
  caminho antigo do portal fora desta SPEC (D-124-C, 75) · o estado do serviço é perguntado (D-124-D, 92) · ordem do deploy
  (D-124-E, 85).
- Opcional, para fechar a dúvida da visão: ~10 fotos reais (CNH, documento do carro, apólice) **com os dados cobertos** para
  uma rodada da bancada (P-124-05).

## SPEC-125 — o atendimento lembra, entende e não pergunta o óbvio (02/10/2026)

📊 O que mudou (medido numa bancada com segurado simulado; nenhum segurado real foi atendido — 📊 0 de 4 agentes ligados):
- **Ele lembra a conversa inteira do assunto** (antes: as últimas 15 mensagens, ≈ 3 a 5 trocas), inclusive o que a sua equipe
  escreveu no meio, e o destravador lê a mesma conversa.
- **Ele reconhece o segurado pelo telefone**, só na mesma corretora: chama pelo nome e pergunta para **confirmar** o CPF que
  ele já disse (mostra só o final). Outra corretora com o mesmo telefone não vê nada.
- **Prompt novo, mais curto** (13.842 caracteres × 22.333 do antigo). O antigo ficou guardado **byte a byte** e volta com UM
  comando no banco, sem Implantar (T-90).
- **Só aciona depois do "sim"** do segurado — agora em código, não só no texto. 📊 Na última rodada, 0 acionamentos sem o
  sim; o preço é ~2,5 mensagens a mais até acionar e +80 % de custo por conversa.
- **Rajada vira UMA resposta** (5 frases, ou fotos + explicação). **Dado de outra pessoa não sai** (CPF da mãe) e o CPF sai
  sempre mascarado.
- **Diário + PLACAR** na tela Atendimentos → Decisões, com o botão **Pausar** por seguradora. E **corretora nova já nasce
  com o destravador ligado**; a 2ª opinião e a reserva do destravador passaram ao **Claude Opus 5.5**.
- 📊 Bancada (Luna, 36 conversas): acerto **63,9 % → 77,8 %** · casos críticos **4 de 6 → 5 de 6** · "Como posso ajudar?" a quem
  já disse o pedido **24 → 2** (os 2 são o "bom dia" de controle). ⚠️ O que falta: o caso crítico "acionamento confirmado"
  (C13) falhou 1 de 2; "cadê o guincho?" ainda chama pessoa na Luna; e os críticos não foram medidos no modelo de produção
  depois dos consertos — o orçamento de testes acabou (📊 US$ 3,70 de 4,00).

### S125.1 · Implantar
→ **T-82** (`smith-api` → `smith-worker` → `smith-web`; nenhuma variável nova).

### S125.2 · Os testes reais com o agente ligado numa corretora de teste
→ **T-84** a **T-89** (grupo ③-b da lista única), depois do T-23/T-25.

### S125.3 · Como VOLTAR ao prompt antigo (sem Implantar)
```sql
update agents set prompt_versao='v1' where agent_role='attendance';
```
Vale na próxima mensagem. Para voltar ao novo: o mesmo comando com `'v2'`. O passo a passo com o teste → **T-90**.

### S125.4 · Decisões suas (`FOUNDER-DECISIONS.md`)
- **D-125-I** — autorizar ~US$ 1,30 para medir os críticos no modelo de produção antes de ligar (nota 85 × 40) → **T-83**.
- **D-125-H** — o diário da conversa registra 2 dos 4 momentos pedidos: aceitar agora (65) × exigir os 4 antes de ligar (50).
- **D-125-A** — o prompt novo fica como padrão (75 × 60): vem decidida; confirme se quiser.
- Já decididas pela execução: a troca da frase do banco em código só no novo (D-125-B, 90) · o "sim" em código (D-125-C, 92) ·
  memória de 40 mil tokens (D-125-D, 88) · rajada até 45 s (D-125-E, 85) · terceiro e CPF em código (D-125-F, 90) · gatilho só
  na criação (D-125-G, 88).
- Opcional (P-125-11): conferir que a corretora nova nasce com o destravador ligado. Cole no **SQL Editor** (ele cria uma
  corretora de teste, confere e **desfaz tudo** no fim; é o VERIFY do arquivo `20261002_01`):
  ```sql
  do $$
  declare v_nova uuid := gen_random_uuid(); v_ag uuid; v_seg text;
          n_ins int; n_depois_resave int; n_depois_mudanca int; n_esperado int;
  begin
    select count(distinct insurer_key) into n_esperado from public.cerebro_modos where modo = 'on';
    begin
      insert into public.companies (id, company_name) values (v_nova, 'verify-125-y3');
      insert into public.agents (company_id, name, slug, agent_role)
        values (v_nova, 'verify-att', 'verify-att-y3', 'attendance') returning id into v_ag;
      select count(*) into n_ins from public.cerebro_modos where company_id = v_nova;
      -- a corretora APAGA uma linha (desliga) e o painel re-salva o agente sem mudar o papel
      select insurer_key into v_seg from public.cerebro_modos where company_id = v_nova limit 1;
      delete from public.cerebro_modos where company_id = v_nova and insurer_key = v_seg;
      update public.agents set agent_role = 'attendance', company_id = v_nova where id = v_ag;
      select count(*) into n_depois_resave from public.cerebro_modos where company_id = v_nova;
      -- CONTROLE: o papel MUDA (core → attendance) → as linhas nascem de novo
      update public.agents set agent_role = 'core' where id = v_ag;
      update public.agents set agent_role = 'attendance' where id = v_ag;
      select count(*) into n_depois_mudanca from public.cerebro_modos where company_id = v_nova;
      raise exception using errcode = 'P0001', message = 'desfaz-verify';
    exception when sqlstate 'P0001' then null; end;
    if n_ins <> n_esperado or n_depois_resave <> n_esperado - 1 or n_depois_mudanca <> n_esperado then
      raise exception 'VERIFY 20261002_01 FALHOU: insert=% resave=% mudanca=% esperado=%',
        n_ins, n_depois_resave, n_depois_mudanca, n_esperado;
    end if;
    if exists (select 1 from public.companies where id = v_nova) then
      raise exception 'VERIFY 20261002_01: a corretora de teste ficou gravada';
    end if;
    raise notice 'VERIFY 20261002_01 OK: insert=% · re-save sem mudar papel=% (apagada continua apagada) · papel mudou=%',
      n_ins, n_depois_resave, n_depois_mudanca;
  end $$;
  ```
  **Esperar:** a mensagem `VERIFY 20261002_01 OK: insert=10 · re-save sem mudar papel=9 … · papel mudou=10`.
  **Se aparecer `FALHOU`:** me mande a linha inteira.
  🔴 **O QUE VOCÊ VAI VER NA TELA (conferido em 02/10 lendo o bloco):** o `raise exception … 'desfaz-verify'` do meio NÃO
  aparece — ele está dentro de um bloco que o captura (`exception when sqlstate 'P0001' then null`) só para desfazer a
  corretora de teste. Então:
  - **deu CERTO** → o SQL Editor do Supabase mostra só **`Success. No rows returned`** (sem vermelho). A linha `VERIFY
    20261002_01 OK: …` é um aviso (`notice`) e o SQL Editor não costuma exibi-la; se ele mostrar uma área de mensagens, ela
    diz `VERIFY 20261002_01 OK: insert=10 · re-save sem mudar papel=9 (apagada continua apagada) · papel mudou=10`.
  - **deu ERRADO** → aparece um **erro em vermelho** começando com `ERROR: P0001: VERIFY 20261002_01 FALHOU: insert=…
    resave=… mudanca=… esperado=…` (ou `VERIFY 20261002_01: a corretora de teste ficou gravada`) — me mande a linha inteira.
  - Qualquer outro erro vermelho (ex.: `permission denied`, coluna inexistente) → nada foi gravado; me mande a linha.

## SPEC-126 — o atendimento quase sem erro (03/10/2026)

📊 O que mudou (medido numa bancada com segurado simulado; nenhum segurado real foi atendido — 📊 0 de 4 agentes ligados):
- **O "ok" do segurado passa por dois juízes**: a regra de texto de antes **e** um modelo barato (GPT-6 Luna) que lê a resposta.
  Só aciona se os dois disserem "ok". "Pode deixar", "manda não", "prefiro amanhã", "sim, quanto custa?" não acionam; "pode
  mandar", "fechou", "👍" acionam. 📊 179 frases testadas: **0** "ok" falso, 97,9 % dos ok de verdade aceitos.
- **O parente aciona** (filho, esposa, motorista) sem o titular junto, e **não ouve** dado da apólice.
- **Desistir depois de acionar chama a pessoa da corretora na hora**, com o resumo e o protocolo no grupo. O agente nunca diz
  "cancelei" sem ter cancelado. 📊 Antes, o sistema nem enxergava que o caso já estava acionado (0 de 1.174 fichas).
- **Aviso de possível abuso**: o mesmo celular pedindo 3 apólices diferentes em 5 dias avisa o grupo da corretora, sem travar o
  atendimento. 🔴 E uma senha da assistência residencial ia a todo segurado — fechado.
- **Apresenta-se uma vez por assunto**; o "escolher sozinho" do destravador só religa com prova (hoje nenhuma seguradora tem casos
  suficientes: 📊 ≤ 5 de 10).
- 📊 Bancada (Luna): acerto **77,8 % → 88,9 %** (a meta era 90 %, faltou 1 de 36) · casos críticos **12 de 12** · no modelo de
  produção (Sol) os críticos **11 de 12** (o que falta é erro da régua, não do agente). Gasto de testes: 📊 US$ 4,28 de 4,50.

### S126.1 · Implantar e conferir
→ **T-91** (Implantar `smith-api` → `smith-worker` → `smith-web`; as migrations já estão no banco; nenhuma variável nova) e
**T-92** (o "juiz do ok" e o DEDUZIR travado, SQL só leitura).

### S126.2 · Os testes reais com o agente ligado numa corretora de teste
→ **T-93** a **T-96** (grupo ③-c da lista única), depois do T-23/T-25. **T-97** quando houver o corpo do `/send/button`.

### S126.3 · Como VOLTAR atrás
O novo portão do "ok" vive no **código**: o desfazer é voltar o código. Peça no chat *"reverta a SPEC-126 na main"* — eu
faço o revert e empurro — e clique **Implantar** (smith-api → smith-worker → smith-web). ⚠️ **Não** apague a linha `confirmacao` de `llm_papeis` achando que desliga o juiz: sem
ela o juiz responde "não é ok" para tudo e **nenhum acionamento sai** (é a falha do lado seguro, de propósito).

### S126.4 · Decisões suas (`FOUNDER-DECISIONS.md`)
- **T-98** — o orçamento dos testes que ficaram de fora (💭 ≈ US$ 1,00 OpenAI + 0,05 Anthropic).
- Já decididas, com nota: o "ok" por dois juízes (D-126-B, 92) · teto de US$ 4,50 (D-126-A, 85) · as apólices do próprio
  titular contam uma (D-126-C, 88) · rastro sem tabela nova (D-126-D, 78) · a calibração paga do DEDUZIR adiada (D-126-E, 80) ·
  reclamação de cobrança do prestador vai à pessoa (D-126-F, 80) · apresentação no 2º turno quando o 1º foi só segurança
  (D-126-G, 80) · 👌 não é ok, dúvida depois do sim derruba o sim, "pode ser" não aciona (D-126-H/I/J, lado seguro).

## SPEC-127 — o portal de vidros no nível do WhatsApp (03/10/2026)

📊 O que mudou (provado por reprodução das gravações reais do portal — nenhum pedido real foi aberto; 📊 0 pedidos de vidro desde
01/08 e as chaves do portal seguem desligadas):
- **Nada abre no portal sem o resumo + o "ok" do segurado**, o mesmo "juiz do ok" da SPEC-126 — e o ok tem de ser **deste** pedido:
  a linha traz a peça, a cidade do serviço e o final da placa. "Posso acionar o vidro?" + "sim" **não** basta.
- **Faltou um dado → o robô pergunta ANTES de escrever** no portal, e a resposta volta ao **mesmo** pedido (um atendimento só).
  📊 18 de 18 pedidos incompletos reproduzidos: **0** escritas no portal.
- **A cidade é a do SERVIÇO**, nunca a do cadastro (📊 5 de 5 gravações). O caminho antigo (o robô que clica na tela) não escolhe
  mais peça, causa, lado nem reparo sozinho, e não aceita oferta nem custo.
- O parente **não vê a placa**; a corretora sem documento no cadastro vai à equipe, sem perguntar nada ao segurado.
- ⚠️ O robô do portal **ainda não escolhe nada sozinho** (📊 autonomia = 0): a medição paga não rodou (T-102).

### S127.1 · Implantar e conferir
→ **T-99** (Implantar `smith-api` → `smith-worker` → `portal-worker` → `smith-web`; nenhuma migration, nenhuma variável nova) e
**T-100** (o documento da corretora que falta, SQL só leitura).

### S127.2 · O canário do portal
→ **T-101**, junto do T-55/T-56/T-58 (as chaves, o pedido de vidro de teste e o cancelamento), com a allowlist `cpf:`.

### S127.3 · Como VOLTAR atrás
Tudo vive no **código**: peça no chat *"reverta a SPEC-127 na main"* — eu faço o revert e empurro — e clique **Implantar**
(incluindo o `portal-worker`). Para só desligar o caminho novo no ar: apague `PORTAL_VIDROS_API_FIRST` do `portal-worker` e
Implante (o passo a passo está no T-101).

### S127.4 · Decisões suas (`FOUNDER-DECISIONS.md`)
- **T-102** — o orçamento da bancada do portal (💭 ≈ US$ 1,00 OpenAI + 1,30 Anthropic). **T-103** — mais gravações da Porto.
- Já decididas, com nota: a retomada do caminho antigo adiada (D-127-A) · só a contenção, sem a ponte (D-127-B, 80) · a
  consulta de "atendimento já aberto" logo depois do POST (D-127-C, 75) · faltou dado = parada antes de escrever, no mesmo
  pedido (D-127-D, 82) · o mesmo "juiz do ok" da 126 (D-127-E) · a bancada do portal não rodou paga (D-127-F, 85) · o vigia
  respeita a tabela e o texto honesto à equipe (D-127-G, 78 e 72).

## SPEC-128 — a prova do Agger (04/10/2026)

📊 O que mudou (nada para o segurado; nenhuma mensagem, nenhuma migration): as 22 perguntas sobre o Agger (E0–E21) foram
respondidas com medição ao vivo — 16 cálculos de 25, nada apagado — e o contrato do cálculo que a 129-B vai usar foi provado contra
5 gravações saneadas. O detalhe está em `programa-multicalculo/A-PROVA-DO-AGGER.md`; o relatório em
`reports/SPEC-128-EXECUTION-REPORT.md`.

### S128.1 · Implantar
Nada a implantar: o contrato ainda não é chamado pelo produto (a 129-B liga).

### S128.2 · Decisões e conferências suas
→ **T-106** (o portão de preço — ✅ feita 05/10, D-MC-62…65) · **T-107** (D-128-03 — ✅ feita 05/10, TOMADA) · **T-108** (os 3 negócios de teste) ·
**T-109** (Bradesco da AutoFleet) · **T-110** (os 2 "Calculando" da Resulta) · **T-111** (as assinaturas vencem 13/10 e 21/10) ·
**T-112** (apagar os HAR do intake) · **T-113** (foi para a ★ em 05/10). Depois da passagem de 05/10: **T-114** a **T-119**
(domínio, Meta, chip, testadores, regras entre corretoras, cartão na Meta) · 05/10 tarde: **T-120** (o usuário de robô no Agger, antes
do uso real).
- Já decididas, com nota: alavancas medidas na AutoFleet (D-128-01, 88) · família nova DADO (D-128-02, 85) · 2 opções = 2 cálculos
  (D-128-04, 90) · coberturas explícitas, nunca o pacote da conta (D-128-05, 92) · entregar aos poucos e fechar por tempo
  (D-128-06, 88) · renovação com o questionário marcado como "assumido" (D-128-07, 80) · a 129-B herda a lista branca do captador
  (D-128-08, 90).

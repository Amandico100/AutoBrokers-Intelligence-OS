# BLOCO 0 da SPEC-131-A — as leituras (MEDIDOR, modo investigação)

> 12/10/2026 · branch `spec/131-A-a-madrugada` · HEAD `eb69098` · linhas citadas = **HEAD** (a árvore já tem edições
> dos builders em `presets.py`, `pedido.py`, `tick.py`, `work/workflows.py` — não são deste laudo).
> Só SELECT e GET na InfoCap (login direto das duas corretoras, em série). Nenhum modelo, nenhum portal, nenhum Agger.
> Saída só com contagens; nenhum CPF, nome, telefone, placa ou nº de apólice. Scripts: scratchpad `b0131a/m2·m3·m4.py`.

## 0. A conexão da corretora de ensaio É a conta da AutoFleet
📊 `tenant_connections` da AMANDUS (`3aa75902-…82fe`): `InfoCap AUTOFLEET` **connected/healthy** (`5039f90d…`); as outras 7 archived/draft.
📊 A credencial dela, decifrada em memória, tem a MESMA impressão `sha256(login)[:12]` que `CORP_INFOCAP_AUTOFLEET` (`2926f6c8f537`),
mesma senha e mesma base. ⇒ medir com o login direto da AutoFleet = medir a conexão da Amandus pelo mesmo `renovacoes_cruas`.
⚠️ `dono.abrir_fonte` não foi usado: importar `app.services` custa 📊 164 s aqui (`python -X importtime`).

## 1. A2 — o pico diário (`fonte_infocap.renovacoes_cruas(hoje, hoje+90)`, 12/10→10/01)
| | AutoFleet (= ensaio Amandus) | Resulta |
|---|---:|---:|
| apólices (tipdoc A, não cancelada, únicas) | 📊 701 | 📊 345 |
| média/dia corrido · mediana · **p90** · **máx** | 📊 7,70 · 8 · **13** · **15** | 📊 3,79 · 3 · **6** · **42** |
| máx ÷ média | 📊 1,9× | 📊 **11,1×** |
| dia útil × fim de semana (média) | 📊 7,43 × 8,38 | 📊 3,66 × 4,12 |
| dono (`/prod_docs`, regra padrão `indireto="F"`) | 📊 701/701 um dono · 10 donos · maiores 270/100/92 | 📊 345/345 um dono · 17 donos · maiores 153/92/35 |
| **pico diário de UM dono** · maior dono média/p90/máx | 📊 **9** · 2,97/6/9 | 📊 **41** · 1,68/3/41 |
| ramo | 📊 AUTO 679 · MOBI 16 · FROT 5 · RESI 1 | 📊 RESI 138 · EMPR 49 · COND 48 · ENGE 17 · SAUD 13 · GOC 13 · VGRP 12 · VIND 11 · CAPI 10 · +14 siglas (≤5 cada) |
Comando: `python scratchpad/b0131a/m2.py` (o dono foi lido nas 1.046 apólices, em série: 555 s + 279 s).
📊 O pico da Resulta é **um dia** (10/12, quinta): 42 apólices = 41 RESI + 1 COND, **4 clientes**, 1 dono, 3 seguradoras (`m4.py`).
**O que muda no desenho:** o "se der errado" do §3 dispara (máx > 3× média). 💭 42 pedidos de RE num login, a 61–134 s cada (I1 §2.1)
= 43–94 min; na cauda (💭 p90 ~8 min/pedido) = 5,6 h > a janela 02:00–06:15. Hoje 📊 0 vínculos produtor↔pessoa ⇒ as 42 caem no
Agger da CORRETORA. Recomendo (nota 85) **nivelar**: teto de pedidos por login por noite (💭 20, config) e o excedente antecipado
para as noites anteriores dentro da antecedência (`calcular_em` mais cedo), em vez de só "começar 01:30" (nota 60: não cobre 5,6 h).

## 2. A5 — `per_c` (`GET /documento?codfil&nosnum`, 20 por corretora, escolhidas por hash)
📊 preenchido > 0: **20/20** e **20/20** · `val_c == base_c × per_c / 100` (±0,5 %): **20/20** e **20/20** · `per_c` igual ao `per_r` do
dono: **0/20** e **0/20** (per_c: 10–30 %, moda 15/20 %; per_r do dono: moda 5 %). Comando: `m2.py` (bloco A5).
⇒ `per_c` é a **comissão da CORRETORA** (o `val_c` dela — `infocap-capability-manifest.json:110`); o do produtor é `per_r`/`val_r`.
**Desenho:** A5 PROVADA — D-131-16 (comissão anterior + `comissao_a_mais_pp`) pode ligar. ⚠️ `/documento` também traz `per_cp/val_cp`.

## 3. A6 — `MULTICALCULO_MOTOR_LIGADO`
Lido em `portal_worker/multicalculo/motor.py:141` (`motor_ligado`), conferido no boot e a cada volta (`laco_do_motor`, `:1525-1545`,
junto de `PORTAL_REAL_ENABLED` e `GLOBAL_KILL_SWITCH`). 📊 chamada real: `"true"`→True · `"false"`→False · ausente→False.
⚠️ **NÃO MEDIDO em produção daqui**: o `/health` do portal-worker (`portal_worker/main.py:140`) expõe `portal_real_enabled` e o freio,
**não** o motor (`grep -n MULTICALCULO portal_worker/main.py` → só o comentário `:94`). Vale o informado pelo Founder; a prova é o log
`[MC] motor do multicálculo iniciado`. 💭 acrescentar `multicalculo_motor_ligado` ao `/health` (1 linha).

## 4. A8 — onde o tick registra, e o canal de aviso
- **Enfileira:** `services/intelligence/tick.py:117` `executar` → `:230` `_agendar` → `WorkRunService.criar` (`services/work/runs.py:242`,
  RPC com `p_idempotency_key`; repetida devolve `reused`). **Chave:** `intel:{escopo}:{workflow_key}:{company_id}:{janela}` (`tick.py:254-256`).
- **Quem chama:** `workers/smith_worker.py:228/247` a cada 5 min. 📊 `work_runs` 30 d: `daily_briefing` 90 (= 3 corretoras × 30).
- **Fuso:** `_janela` (`tick.py:202`) rotula em **UTC** (`agora` = `datetime.now(timezone.utc)`, `:49`); só o briefing converte para
  `America/Sao_Paulo` (`deve_publicar_briefing`, `:75-105`, janela de 1 h após o horário). 00:30 BRT = 03:30 UTC (mesmo dia): o gate
  de hora tem de usar o `_tz`, como o briefing.
- **Registrar e executar:** `@registrar_workflow("chave", idade_maxima_s=, ao_desistir=)` (`services/work/workflows.py:33`) + o módulo
  na lista de `carregar_extras` (`:60-74`); passos com `executar_passo` (`:177`); dormir/acordar `runs.dormir` (`runs.py:469`,
  `wake_at`+`wait_for`) e `despertar_vencidos` (`:532`). Modelo vivo: `services/canal/workflows.py:202-323`.
- **Canal de aviso in-app que JÁ existe:** o **briefing** — `briefing_service.publicar` (`intelligence/briefing_service.py:678`) →
  `briefing_publications` + `briefing_items` → `DeliveryExecutor._dashboard` (`delivery_executor.py:175`: "está no painel, em
  Entregas") → `/api/dashboard/briefing`. 📊 268 publicações, **todas `user_id` nulo**; 6 perfis, todos `scope=company`, canal
  `["dashboard"]`. O esquema já aceita a pessoa (`perfil(user_id=)` → `scope:"personal"`, `briefing_service.py:587-607`), mas a tela lê
  só por `company_id`. 📊 nenhuma tabela
  `notifications/inbox/avisos` (`information_schema` → só `admin_inbox_states`, `briefing_*`).
  **Desenho:** aviso das 06:45 = item de briefing (admin: `company`; membro: perfil `personal`) — não publisher novo. WhatsApp ao
  membro = `delivery_executor._whatsapp` (`:228`, piso CRÍTICO).

## 5. A9 — ficha → códigos do Agger (AUTO)
📊 a régua da 130-B está **só em JSON** (`backend/tests/corpus/bancada/RESULTADOS/ficha_da_apolice_20261012.json`, 8 AUTO, 6 com
linhas; 2 sem PDF); **nada no banco** (o script não grava, `regua_ficha_da_apolice.py:13-19`). O JSON guarda por linha só
`rotulo · premio · tem_limite` — **não** o valor do limite nem o `franquia_texto` (o tipo os tem, `policy_data_provider.py:707-714`).
| chave do Agger (`presets.py:34-56`) | apólices com o rótulo · linhas com limite | para o preset `anterior` |
|---|---|---|
| `isDanosMateriais` / `isDanosCorporais` / `isDanosMorais` | 📊 6/6 · 10/11 · 6/6 · 11/12 · 6/6 · 5/6 | existe (valor no leitor, não no JSON) |
| `isAppMorte` | 📊 6/6 · 11/12 | existe |
| casco / `pctAjuste` (`veiculo.percentual_fipe`, `agger_robo.py:244`) | 📊 6/6 · **1/6** | **falta o % FIPE** → padrão |
| `tipoFranquia` 1/2 | 📊 rótulo 1/6; texto não gravado | **falta** → para cima = 1 (reduzida) |
| `vidros` 1/2 | 📊 3/6 · 4/4 (nível não se distingue) | **falta o nível** → 2 |
| `carroReserva` 0/1/2 | 📊 2/6 (um "15 dias" no rótulo) | **falta em 4/6** → 2 (15 d) |
| `assist24hs` 1/4 | 📊 5/6 · 1/9 | **falta o nível** → 1 (completa) |
| extras: acessórios, despesas extra., blindagem, kit gás, 0 km | 📊 3/6 cada | sem chave hoje (`despesasExtra`/`isBlindagemValor`/`valorDeNovo` existem) |
📊 HEAD: `pedido._de_apolice_auto` usa da ficha só placa/chassi/ano (`pedido.py:742`); `_ramo_do_agger` (`:687`) com família `None`
→ AUTO. **Desenho:** RCF/DMO/APP vêm da ficha; franquia, vidros, reserva, assistência e % FIPE saem "para cima" + aviso "não conferido".

## 6. CPF/CNPJ (P-1310-02) — NÃO há ponto único
`/cliente_cpf` é chamado em **5 funções** de `app/api/infocap_connector.py` (HEAD): `infocap_lookup` `:946/:1010` (produto: via
`InfocapPolicyProvider.lookup`, `providers/infocap_policy_provider.py:938-967`) · `infocap_vehicle_item` `:4584/:4636` (via `.vehicle`
`:996-1020`) · e três auditorias do `infocap_probe` (`:3080`): `_resolve_policy_detail_for_document_source_audit` `:2390/:2497`,
`_run_policy_chain_contract_probe` `:2696/:2722`, `_run_policy_identity_integrity_audit` `:2867/:2917` (+ `:3209/:3215`).
Todas usam `_digits` (`:198`), sem dígito verificador. Comando: `awk '/^(async )?def /{fn=$0} /cpf_search_path/{print NR, fn}'`.
**Validador já existe:** `agents/tools/insurer_dispatch_tool.py:101` `cpf_valido` · `:114` `cnpj_valido` · `:126` `documento_br_valido`
(reusado por `agents/quem_e_o_segurado.py:122`); outros em `canal/conversa.py:118`, `portals/replay.py:470/491`.
📊 Na lista: `cic` com DV válido **701/701** e **340/340** (5 vazios na Resulta) — o risco é o caminho do chat, não `/renovacoes`.
**Desenho:** a barreira entra nos dois pontos do produto (`:1010`, `:4636`) ou num `_cpf_cnpj_valido_ou_recusa` comum às 5.

## 7. CONTAS do Agger (`portal_accounts portal_key='agger'`, sem logins)
📊 AutoFleet: `global/ativo/com senha` 1 · `teste/pausado/sem senha` 1 · Resulta: idem 1 + 1 · **membro: 0** · `robo_teto_por_hora`
nulo (vale 60, `robos.py:61`). 📊 **AMANDUS: 0 contas do Agger** — a corretora de ensaio lista e acha o dono, mas **não calcula**:
`qual_agger` não acha conta nem da corretora. ⇒ canário da 131-A na Amandus exige cadastrar um Agger nela (🧑) ou rodar o cálculo na AutoFleet.

## 8. B6 · B7 · B5 · B2
- **B6** 📊 `multicalculo_config` **0** linhas · `tenant_auxiliaries` com slug `%renov%` **0** (o template `renovacao-maxima` existe
  em `auxiliary_templates`, 0 instalado; 10 auxiliares no total) · `membro_produtores` 0 · `regras_de_dono` 0. ⇒ nada a migrar.
- **B7** 📊 `company_members` **não tem** telefone; `users_v2.phone` preenchido em 10/10 membros ativos das 3 corretoras (7 pessoas,
  6 números distintos); **nenhuma coluna "verificado"** em tabela de pessoa (`information_schema … ilike '%verif%'`). ⇒ verificado = **0**.
- **B5** 📊 `fone` ≥ 10 dígitos em `/renovacoes`: AutoFleet **684/701 (97,6 %)** · Resulta **277/345 (80,3 %)**.
- **B2** 📊 `/cliente_ligacoes?codigo=<codcli>`: **0 documentos em 10/10** nas duas (o produto passa o `codigo` do `/cliente_cpf`,
  `infocap_connector.py:1302`, não testado). Cadeia `nosnum_ren` via `/documento`: anda; 📊 passos (anos) AF 0(0,8)·1(1,9)·0(1,0)·3(3,9)·
  3(3,8) · Resulta 0(1,0)·0(0,9)·0(0,9)·2(2,9)·7(8,3); `nosnum_ren` já vem na linha de `/renovacoes` em 454/701 e 237/345.
  ⇒ "renova conosco há N anos" pela cadeia: coerente e barato (💭 ~1,6 chamada/apólice); "cliente desde" absoluto: não.

## 9. FILA — o laço do motor hoje
`Motor.uma_volta` (`motor.py:349-366`, a cada `VOLTA_S=5`): expira → retoma → `_reservar` (`:505`) lê até `LIMITE_DA_FILA=50`
cálculos `na_fila` em ordem `prioridade, criado_em` (`:514`) → freios por hora (geral 400, corretora 120, `:96-97`; conta 60,
`robos.py:61`) → lease por conta → `asyncio.create_task` por grupo **sem limite** (`:361`). 📊 `grep -rnE "MAX_SESS|SIMULT|Semaphore"`
em `portal_worker` e `services/multicalculo` → 0: **não há teto de sessões simultâneas**. Prioridade é por **origem**
(`porta.py:73` `{"canal":0,"teste":0,"auxiliar":5}`), e cotação e renovação são ambas `auxiliar` (`porta.py:63`) ⇒ "renovação = 7"
exige ler o `servico` no cálculo da prioridade (não basta outra origem). Login de pessoa: logout por pedido (`motor.py:742-750`).

## 10. Fora do escopo (visto)
1. `/health` do portal-worker não diz se o motor está ligado (§3). 2. `_janela` em UTC (§4). 3. Resulta: 📊 cotáveis (RESI+EMPR+COND)
235/345 = 68 %; 110 viram `ramo_nao_cotado` (ENGE, SAUD, GOC…). AutoFleet: MOBI 16 + FROT 5 virariam AUTO pelo defeito de `:687`.
4. Leitura da ficha: 📊 média 20 s, p90 41 s, US$ 0,0014/apólice (régua 130-B) — 42 num dia = 💭 ~14 min de preparação em série.
5. Importar `app.services` local = 📊 164 s.

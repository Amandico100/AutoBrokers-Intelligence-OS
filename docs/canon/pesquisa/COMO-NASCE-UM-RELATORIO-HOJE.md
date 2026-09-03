# Como nasce um relatório novo, hoje

> **Pesquisa de estado, não SPEC.** Pergunta do Founder, 03/09/2026: *"qual é o processo,
> HOJE, para nascer um relatório novo, uma skill nova, um auxiliar novo? O chat principal
> consegue propor/criar um cálculo que ainda não existe?"*
> 📊 Contagens no Supabase `dcajcvlzcjbmyapmklil`, 03/09/2026. Repo em `HEAD 81859d4`.
> ⚠️ `backend/app/comercial/` está sob edição de outro agente — lido em `git show HEAD:`.

## 1. Skill Registry — existe, está cheio, e não governa nada

**FATO.** O motor existe: `backend/app/services/skills/registry.py` (264 l), `gateway.py`
(332 l), `invocation_recorder.py` (275 l). 📊 `skills` **20** (todas `is_active`) ·
`skill_releases` **21** · `skill_bindings` **26** · `skill_capability_requirements` **17** ·
`skill_tool_requirements` **33**.

**Como uma Skill é declarada:** linha de banco, semeada por migration.
📊 Único arquivo que insere: `backend/supabase/migrations/20260726_03_spec059_regras_skills_tools.sql`.
Não há YAML, não há decorator Python, e **não há API**:
📊 `grep -rn "skills" backend/app/api/*.py -l` → **zero arquivos**. A tela
`app/admin/capacidades/page.tsx` **só lê** (`app/api/admin/control-plane/capabilities/route.ts:7`
exporta apenas `GET`).

**Quem carrega no chat:** `backend/app/agents/gateway_cutover.py`, por turno. Mas o modo vem
de `TOOL_GATEWAY_MODE` (`gateway_cutover.py:61`), default `off`.
🔴 📊 `select modo, identico, count(*) from tool_gateway_shadow_diffs group by 1,2`
→ **155 linhas, todas `shadow` e `identico=false`**, última em 19/08/2026.
**O Gateway nunca concordou com a lista legada uma única vez.**

**Passo a passo REAL:** migration com `insert` em `skills` + `skill_releases` +
`skill_capability_requirements` + `skill_tool_requirements` + `skill_bindings` — e **nada
muda no chat**, porque quem monta as ferramentas é o `graph.py`, não o Registry.

> **INFERÊNCIA.** A Skill hoje descreve um caminho que o runtime não percorre. Não é o
> mecanismo por onde uma capacidade nova nasce.

## 2. As tools do chat `core` — montadas à mão, num `if` por peça

**FATO.** A lista é montada imperativamente em `backend/app/agents/graph.py` (~200–630), com
`tools.append/extend` dentro de `if` aninhados. O que o papel `core` pode receber hoje
(📊 `graph.py` cruzado com `select capability_key, agent_role, enabled from capability_bindings`):

| origem | tools |
|---|---|
| fixas / toggle | `knowledge_base_search` · `web_search` · `request_human_agent` · `csv_analytics` · `http_api` · MCP · `delegate_to_subagent` |
| capability | `web_scrape` `document_read` `web_search_deep` (`platform.web.scrape`) · `control_plane_read` · `infocap_policy_lookup` + `buscar_veiculo` · `portal_action` (`tenant.portal.execute`) |
| papel `core` cravado no código | `create_routine` `list_routines` `manage_routine` · `resumo_atendimentos` `atlas_rotas` · `gerar_relatorio` · `raio_x_comercial` `radar_de_renovacoes` · `avaliar_automacao` · `executar_auxiliar` |
| `platform.research.search` | `pesquisar_na_web` `monitorar_fonte` `analisar_site` |
| `tenant.intelligence.read` | `briefing_da_corretora` `prioridades_da_corretora` `responder_recomendacao` `preferencias_de_briefing` |

**≈26 tools no teto.** 📊 `agent_http_tools = 0` e `agent_mcp_tools = 0` — as duas portas de
extensão sem deploy estão vazias.

**Como uma tool nova entra** (caso medido da SPEC-081): módulo em
`agents/tools/relatorios_comerciais.py`, fábrica em `:889` (`def ferramentas_comerciais`),
e **uma linha** em `agents/graph.py:562-564`. **Isso é um deploy.**

**O que decide visibilidade:** três autoridades misturadas — `_agent_role` comparado por
string, o `_active` do `capability_resolver.py`, e o `tools_config` legado (`graph.py:244`).
📊 `tool_definitions` (**32**) e `tool_releases` (**34**) existem e **o `graph.py` não os lê**.

## 3. Capability Registry (governa) · Tool Gateway (não governa)

**FATO — o Capability Registry é real e está no caminho quente.** 📊 `capabilities` **38** ·
`capability_bindings` **61** · `tenant_capability_entitlements` **114** · `capability_packs` **10**.
Lido por `agents/capability_resolver.py`, consumido em `graph.py` como `_active`.

📊 `tool_invocations` **129** — e a chave gravada é `capability_key`, não `tool_key`:
`operational.infocap.policy_lookup.read` 100 · `knowledge.tenant.search` 13 ·
`control_plane.read` 6 · `operational.insurer.dispatch` 5 · `tenant.intelligence.read` 4 ·
`tenant.artifacts.generate` 1. Última: **19/08/2026**. O Tool Gateway, em sombra (§1).

> **INFERÊNCIA.** A governança que funciona hoje é a **capability**. Skill e Gateway são a
> camada prometida acima dela, e ela ainda não foi ligada.

## 4. Auxiliares e Rotinas — a Factory existe; o chat só propõe

**FATO.** `services/auxiliaries/factory.py` (487 l) · `api/factory.py` · `api/auxiliaries.py`.
📊 `auxiliary_templates` **16** — **6 `available`** (`checklist-6h`, `cobranca-feita`,
`follow-up-whatsapp`, `radar-mercado-regulacao`, `resumo-atendimentos`, `tarefas-agendadas`)
e **10 `coming_soon`**. 📊 `tenant_auxiliaries` **9**, em **5 corretoras** — 2 `active`,
2 `paused`, 5 `inactive`. 📊 `auxiliary_runs` **4** · `auxiliary_template_releases` **0**.

**Nasce** pela tela do admin — `app/admin/auxiliares/page.tsx:215-249`
(`POST /api/admin/auxiliaries/templates`), ou de um agente existente em `:452-455`. **É
instalado** pela corretora na galeria (`app/dashboard/auxiliares/galeria/[slug]`). **É
acionado** por Rotina agendada ou por `executar_auxiliar` (`agents/tools/auxiliary_run_tool.py:61`),
que enfileira `bridge.auxiliary.execute` — o mesmo workflow da Rotina, `source_type='chat'`.

**O chat NÃO cria Auxiliar.** `factory_tool.py:45` (`avaliar_automacao`) devolve **proposta**;
a docstring diz por quê: *"Criar Auxiliar no meio de uma conversa produz coisas que ninguém
pediu e ninguém sabe desligar."* Árvore léxica em `factory.py:223 classificar_padrao`:
ONE_SHOT · WORKFLOW · ROTINA · AUXILIAR.

🔴 📊 `auxiliary_requests = 0` e `capability_gaps = 0`. **A Factory pelo chat nunca rodou
em produção.** O "não consigo honesto que vira dado de roadmap" nunca produziu um dado.

**Rotinas:** 📊 `routines` **1**, `is_active = false`. `routine_runs` **45**,
`routine_templates` **3**.

## 5. Artifacts — a peça mais viva do sistema

**FATO.** O catálogo é Python: `services/artifacts/templates.py:785` (`CATALOGO`, 20 entradas),
índice em `:795` (`POR_CHAVE`), escolha determinística e léxica em `:798` (`def escolher`).

**Semeadura:** migration `20260730_01_spec057_seed_templates.sql`, **mais** o upsert na hora
do uso (`_garantir_template` em `services/artifacts/service.py`, antes do `insert`).
**Guarda:** `backend/tests/test_template_de_artefato_existe.py` — índice sem chave duplicada,
cobertura da migration, e `_garantir_template` **antes** do insert.
📊 `report_templates` no banco = **20**; `CATALOGO` = **20**. **Sincronizados.**

📊 `select origin, template_key, count(*) from artifacts` — **126 artifacts, 3 corretoras**:

```
routine  briefing.daily_operational ....... 81
chat     renewals.radar ................... 14
chat     commercial.pipeline .............. 14
routine  briefing.weekly_executive ........ 12
routine  financial.billing_collection ......  5
```

🔴 **5 dos 20 templates produziram alguma coisa. 15 têm zero.** E os 28 do `chat` são
exatamente as duas tools da SPEC-081 — 📊 `gerar_relatorio` (`report_tool.py:196`), que pede
ao LLM que componha o conteúdo, **nunca produziu um artifact**.

**Renderização:** HTML e só. `services/artifacts/render.py:48 render_html`;
`:133 render_texto_whatsapp` faz a versão de texto. **Não há geração de PDF** — o corretor
imprime pelo navegador (`app/dashboard/entregas/[artifactId]/page.tsx:183-185`).

**Tela "Entregas": existe e é pilar do menu** — `lib/navigation.ts:50`, renderizada em
`components/layout/TenantNav.tsx:140`. Detalhe em `[artifactId]/page.tsx` (iframe `srcDoc`,
`:226-231`), download `.html` em `[artifactId]/arquivo/route.ts`.

**Canal de entrega:** `services/intelligence/delivery_executor.py:60`
`CANAIS_CONHECIDOS = ("dashboard", "email", "whatsapp")`. Link público `/r/[token]` existe
(`app/r/[token]/route.ts`), mas 📊 `artifact_shares = 0` e nenhuma tela cria o token.

## 6. Intelligence Fabric — duas metades que precisam casar por `rule_key`

**FATO.** 📊 `intelligence_rules` **12**, todas `active`, `scope=tenant`: 10
`deterministic_python` + 2 `statistical`, nas famílias `automacao.*` (3), `conexoes.*` (2),
`operacao.*` (5), `qualidade.*` (2).

**Uma regra é DUAS coisas:** a linha no banco (mesma migration
`20260726_03_spec059_regras_skills_tools.sql`) **e** um detector Python registrado por
`@registrar(rule_key)` em `services/intelligence/detectors/{automacao,conexoes,operacao,qualidade}.py`
— registro em `detectors/__init__.py:45 _REGISTRO`, resolução em `:56 resolver`.
**Se as duas metades não casarem pela chave, a regra existe e não roda.** Não há UI.

📊 `intelligence_signals` **92** · `intelligence_findings` **14** · `intelligence_events` **303**.
🔴 📊 `last_run_signals`: **11 das 12 regras produziram ZERO sinais na última varredura**;
só `qualidade.atendimento_parado` produziu 1.

**O briefing está vivo.** 📊 `briefing_items` **1324** · `briefing_profiles` **6** ·
`briefing_publications` **134, todas `published`**, a última em **03/09/2026 — hoje**.
Cadência: `services/intelligence/tick.py` roda a cada 5 min e publica na janela de 1h após
o horário do perfil (padrão 08:00), `daily` e `weekly`.

## 7. Research Orchestrator — existe, o chat dispara, ninguém usou

**FATO.** 12 tabelas `research_*`, API em `backend/app/api/research.py`, três tools
(`pesquisar_na_web`, `monitorar_fonte`, `analisar_site`) atrás de `platform.research.search`,
📊 ligada para `core`. 📊 `research_requests` **1** · `research_plans` **1** ·
`research_claims` **1** · `research_sources` **1** · `research_provider_usage` **2** ·
`research_source_policies` **26** · `findings`, `monitors`, `observations`, `cache_entries`
todos **0**.

**RESPOSTA:** sim, o chat consegue disparar pesquisa externa hoje. 📊 Aconteceu uma vez.

## 8. Conectores — a definição é global, a credencial é que muda de camada

**FATO** (`docs/canon/CAMADAS-DE-CONEXAO.md`, SPEC-064).
📊 `connector_templates` **11** · `tenant_connections` **18**:

```
platform  firecrawl · tavily · internal_conversations · internal_documents
company   infocap · google_drive · notion · whatsapp_zapi
inativos  insurance_portal · portal_browser · quiver
```

**Como nasce um conector novo:** linha em `connector_templates` por migration
(📊 sem UI: `grep "api/admin/tools\|api/skills\|api/tools"` no frontend → **0**), mais
provider, mais capability, mais tool, mais a linha no `graph.py`. **Cinco lugares.**

**Fonte externa pública sem credencial (SUSEP):** o caminho mais barato **não** é conector.
📊 Já existem a skill `research.regulatory_watch`, o template `research.regulatory_radar`,
o auxiliar `radar-mercado-regulacao` e 26 `research_source_policies`. **Custa uma política
de fonte e um monitor.**

## 9. O chat NÃO consegue criar um cálculo novo

🔴 **FATO, com o grep que prova.**
`grep -rn "exec(\|eval(\|python_tool\|code_interpreter\|sandbox\|calculator" backend/app --include=*.py`
→ três ocorrências, **nenhuma é execução de código**: um comentário (`intelligence/tick.py:165`),
o `create_subprocess_exec` do stdio de MCP (`mcp_gateway_service.py:346`) e uma docstring
(`whatsapp/providers/base.py:62`). `grep "text_to_sql\|sql_tool\|execute_sql"` → **zero**.

**Não há sandbox, não há geração de SQL, não há execução de código.** Todo número que o chat
entrega vem de Python determinístico escrito à mão em `backend/app/comercial/` (`calculos.py`
19.5 KB · `cbim.py` 17.5 KB · `fonte_infocap.py` 24.5 KB · `evidence_pack.py` 9.7 KB, lidos em
`HEAD`), chamado por `agents/tools/relatorios_comerciais.py:67 _comercial()`. O mais perto de
cálculo aberto é `csv_analytics_tool.py` — agregações fixas sobre um CSV.

**Quando pedem o que não existe:** o prompt manda não inventar (`core/prompts.py:35` *"Não
invente ferramentas que não existem"*; o bloco de rotinas fecha com *"Nunca ofereça o que as
suas ferramentas não conseguem fazer hoje."*). O caminho estrutural é `avaliar_automacao` →
proposta + `capability_gaps`. 📊 `capability_gaps = 0`: nunca produziu uma linha.

## 10. Memória — o chat não lembra do relatório que entregou

📊 `user_memories` **41** · `agent_memories` **7** · `memory_settings` **8** ·
`company_memories` **0** · `knowledge_candidates` **0** (confirmado) · `knowledge_cards`
**18.715**. Escritores: `services/memory_service.py:684 extract_user_facts` → `user_memories`;
`memory_fabric.py`; `agent_memory.py`.

🔴 **FATO.** `grep -rn 'table("artifacts")' backend/app/agents/` → **zero**. **Nenhuma
ferramenta do chat lê a tabela `artifacts`.** O chat não consegue listar, reabrir nem comparar
um relatório que ele mesmo entregou. O que ele "lembra" é fato solto em `user_memories`.

## O MAPA DO QUE EXISTE

| peça | existe? | onde | em produção (📊) | como se cria uma nova | passos |
|---|---|---|---|---|---|
| **Skill** | sim, inerte | `services/skills/registry.py` · `skills` | 20 skills, 0 turnos governados | migration com 5 inserts | 1 arquivo, 0 efeito |
| **Capability** | sim, **governa** | `agents/capability_resolver.py` · `capabilities` | 38 caps · 129 invocações | migration + binding + entitlement | 1 migration |
| **Tool** | sim | `agents/tools/*.py` + `graph.py` | ~26 no `core` | módulo + fábrica + linha no `graph.py` | 2 arquivos + **deploy** |
| **Tool Gateway** | sim, em sombra | `services/skills/gateway.py` | 155 diffs, 0 idênticos | — | `TOOL_GATEWAY_MODE=on` |
| **Auxiliar** | sim | `services/auxiliaries/factory.py` | 16 templates (6 prontos) · 9 instalações | tela do admin | 1 tela |
| **Rotina** | sim | `routines` · `create_routine` | 1 linha, desligada | chat ou tela | 1 tool |
| **Artifact template** | sim | `services/artifacts/templates.py:785` | 20 templates · 5 usados · 126 peças | entrada no `CATALOGO` + migration + guarda | 3 arquivos + **deploy** |
| **Finding / regra** | sim | `intelligence/detectors/` + `intelligence_rules` | 12 regras · 14 findings · 134 briefings | linha no banco **e** detector Python | 2 lugares que têm de casar |
| **Research** | sim | `api/research.py` + 12 tabelas | 1 pesquisa | política de fonte | 1 linha |
| **Conector** | sim | `connector_templates` | 11 templates · 18 conexões | migration + provider + cap + tool + `graph.py` | 5 lugares |
| **Cálculo novo** | **não** | — | — | **não existe caminho** | — |

## O CAMINHO MAIS CURTO HOJE para um relatório novo

📊 É o caminho que a SPEC-081 percorreu, e é o único que produziu artifact pelo chat.

```
1. o CÁLCULO      backend/app/comercial/calculos.py        função determinística nova
                  backend/app/comercial/fonte_infocap.py   de onde vêm as linhas
2. o TEMPLATE     services/artifacts/templates.py          Template(...) + entrada no CATALOGO :785
                  + pista léxica no `escolher()` :798      senão ele nunca é escolhido
3. a MIGRATION    supabase/migrations/…_seed_templates     (ou confiar no `_garantir_template`)
4. a TOOL         agents/tools/<nova>.py                   monta blocos, chama `_publicar`
                  → `ArtifactService.criar/renderizar/publicar`, origin="chat"
5. o FIO          agents/graph.py, uma linha no bloco       ~:562, dentro do `if` de papel `core`
6. a GUARDA       tests/test_template_de_artefato_existe.py + teste que casa NOME DE PROPRIEDADE
                  de bloco (📊 32 asserções verdes já deixaram passar 7 caixas vazias)
7. o DEPLOY       git push origin HEAD:main
```

**Sete passos, cinco arquivos, um deploy.** Nada disso passa por Skill, por Tool Gateway
nem pelo Registry. A capability (`tenant.artifacts.generate`) já está ligada para `core`.

## O QUE FALTA para o chat propor/criar um cálculo novo com governança

| falta | evidência |
|---|---|
| **execução de código governada** (sandbox, sem rede, sem segredo, com limite) | 📊 grep de `exec(`/`sandbox`/`code_interpreter` → 0 ocorrências reais |
| **definição de métrica como DADO**, não como função Python | os cálculos moram em `backend/app/comercial/calculos.py`; não há tabela de métrica |
| **template de artifact criado sem deploy** | `CATALOGO` é uma tupla Python (`templates.py:785`); não há UI (grep do frontend → 0) |
| **tool declarada sem `graph.py`** | 📊 `agent_http_tools = 0`, `agent_mcp_tools = 0` — as duas portas existem e estão vazias |
| **o Registry no caminho quente** | 📊 155 diffs em `shadow`, **0 idênticos** — o cutover nem começou a poder acontecer |
| **o "não sei fazer" virando dado** | 📊 `capability_gaps = 0` e `auxiliary_requests = 0` |
| **o chat enxergar o que já entregou** | 📊 nenhuma tool lê `artifacts` |
| **aprovação humana no nascimento de uma peça** | `approval_request_id` existe em `tool_invocations`; não há fluxo de aprovar cálculo novo |

> **RECOMENDAÇÃO.** A ordem barata é o inverso da ambiciosa: (1) uma tool que **lista** os
> artifacts da corretora — tabela com 126 linhas que ninguém lê; (2) métrica como linha de
> banco, antes de sonhar com sandbox; (3) tirar o Gateway da sombra ou **desligá-lo** — 155
> diffs sem um único idêntico não é migração em andamento, é motor que ninguém conferiu.

## RISCOS DE MOTOR PARALELO (CLAUDE.md §5)

O que a SPEC-094 e uma futura "fábrica de relatórios" **não podem** duplicar:

```
✗ segundo CATÁLOGO de templates ao lado de `templates.py:785 CATALOGO`
    o guarda `test_template_de_artefato_existe.py` só conhece um; um segundo volta
    a produzir violação de chave estrangeira em silêncio (o defeito de 30/07)
✗ segundo caminho de PUBLICAÇÃO ao lado de `ArtifactService.criar/renderizar/publicar`
    é o que `relatorios_comerciais.py:305 _publicar` chama e o que alimenta Entregas
✗ segundo REGISTRO de ferramenta ao lado de `graph.py`
    `tool_definitions` (32) e `tool_releases` (34) já são catálogo que ninguém lê
✗ segundo motor de REGRA ao lado de `intelligence/detectors/_REGISTRO`
    já são duas metades que casam por `rule_key`; a terceira multiplica o silêncio
✗ segundo SCHEDULER ao lado de `routines` / `tick.py`   CLAUDE.md §5 · SPEC-059 §0.1
✗ segunda camada de CÁLCULO ao lado de `backend/app/comercial/`
    ⚠️ sob edição de outro agente nesta janela — coordenar, não escrever ao lado
```

🔴 **O risco específico da pergunta do Founder:** "fábrica de relatórios" é o nome natural
de um **motor de Skill**. A casa já tem um — `services/skills/registry.py`, 20 skills, 21
releases, 26 bindings, em sombra. **Construir a fábrica ao lado dele seria criar o motor
paralelo mais caro deste projeto**, porque o primeiro nunca foi medido em produção e
ninguém saberia qual dos dois estava errado.

# SPEC-EXTRA-001.1 — RESEARCH PACK
## A apólice certa, inteira, em uma rodada · evidências reabertas e conferidas em 13/09/2026

**Versão:** 1.0 · 13/09/2026. **Natureza:** evidência para conversão. **Não é relatório de execução.**
**Árvore:** `C:\Users\amand\Projetos\AUTOBROKERS RESULTA\AutoBrokers-FIX` · **commit `a0bb5fe`** ·
📊 `git rev-list --count HEAD..origin/main` = **0** e `git rev-list --count origin/main..HEAD` = **0**.
**Método:** leitura direta dos arquivos nesta revisão; consultas **read-only** ao Supabase de produção
(somente contagens e colunas não-pessoais); reabertura das cinco fontes externas. **Nada foi executado no
produto. Nenhuma migration. Nenhum envio. Nenhum portal.**
**PII:** nenhum CPF, CNPJ, telefone, nome de segurado, placa, e-mail, apólice completa ou credencial aparece
neste documento. Os números de teste do Founder aparecem só como `TESTE-A` / `TESTE-B`.

---

## 0. Legenda e precedência

| marca | significa | exigência |
|---|---|---|
| **📊** | **medido** | data + fonte + o comando/consulta que produziu o número |
| **💭** | **ilustrativo** | exemplo de copy ou estimativa — **nunca citável como fato** |
| **CONFERE** | a linha do diagnóstico foi reaberta hoje e bate | — |
| **DIVERGE** | a linha mudou, ou a afirmação estava imprecisa | a SPEC já traz a correção |
| **FATO / INFERÊNCIA / RECOMENDAÇÃO** | separados sempre | CLAUDE.md §12 |

🔴 **As coordenadas abaixo são desta baseline, não contratos permanentes.** O BLOCO 0 do executor reabre cada
uma e **o número dele vence** (protocolo §5 ①).

---

## 1. O achado que reordena a SPEC

> **DIVERGE — e é a divergência mais cara do pacote.**

O diagnóstico §7.3 e o pacote do redator pedem criar `backend/app/services/policy_provider/` com um `Protocol`
`PolicyDataProvider`.

📊 **Ele já existe, noutro lugar, desde a SPEC-016 E5.** Comando:

```bash
find backend -iname "*policy_data_provider*" -o -iname "*policy_provider*"
grep -rn "PolicyDataProvider\|policy_data_provider" --include=*.py --include=*.md .
```

```
backend/app/providers/policy_data_provider.py            149 linhas · 5.670 bytes
  :23   parse_policy_locator_ref(value) -> Optional[Tuple[str, Tuple[str,...]]]
  :41   class PolicyDataProvider(Protocol):  provider_key: str
  :46       async def lookup(self, **kwargs) -> Dict[str, Any]
  :50       async def detail(self, **kwargs) -> Dict[str, Any]
  :55   class InfocapPolicyDataProvider:  provider_key = "infocap"
  :60       lookup(...)   → app.api.infocap_connector.infocap_lookup
  :88       detail(...)   → app.api.infocap_connector.infocap_policy_detail
  :112      vehicle(...)  → app.api.infocap_connector.infocap_vehicle_item
  :134  _REGISTRY: Dict[str, Any] = {}
  :137  register_policy_data_provider(provider)
  :144  get_policy_data_provider(provider_key="infocap")
  :149  register_policy_data_provider(InfocapPolicyDataProvider())
```

📊 **E cinco chamadores já falam com ela**, não com o conector:

```
backend/app/agents/tools/infocap_tool.py:151-159       "a tool fala com a PORTA PolicyDataProvider, nunca com o…"
backend/app/agents/tools/insurer_dispatch_tool.py:967
backend/app/agents/tools/portal_tool.py:337-346
backend/app/agents/tools/vehicle_tool.py:55-57
backend/app/providers/brokerage_analytics_provider.py:193-196   "o MESMO padrão de policy_data_provider.py:134-149"
```

**FATO:** a fronteira existe e tem cinco consumidores.
**INFERÊNCIA:** ela não isola nada, porque `lookup`/`detail` devolvem `Dict[str, Any]` com a **forma da InfoCap**
dentro. Um `Protocol` cujo retorno é o dicionário do fornecedor é um cano com anotação de tipo.
**RECOMENDAÇÃO:** evoluir o arquivo que existe. Criar `backend/app/services/policy_provider/` seria motor
paralelo (CLAUDE.md §5) e deixaria **dois** registries de provider de apólice no mesmo repositório.

---

## 2. Evidência de código — cada linha reaberta em 13/09/2026

### 2.1 `backend/app/agents/tools/infocap_tool.py` (667 linhas)

| linha | evidência literal | veredito |
|---|---|---|
| **:22** | `_CLIENT_FACING_ROLES = ("attendance", "insured_external")` | CONFERE |
| **:26-28** | `_AUTO_INTENT_RE = re.compile(r"guincho\|reboque\|bateria\|pneu\|chaveiro\|socorro\|pane\|\bcarro\b\|ve[íi]culo\|moto\b\|estepe\|motor", re.I)` | CONFERE — 🔴 **`chaveiro` está SÓ aqui** |
| **:30-32** | `_RESI_INTENT_RE = re.compile(r"resid[êe]nc\|\bcasa\b\|apartamento\|encanador\|eletricista\|vazamento\|telhado\|fechadura da porta\|eletrodom[ée]stic", re.I)` | CONFERE — **sem `chaveiro`** |
| **:35-41** | `def _product_hint_from_query(query)`: testa AUTO primeiro, depois RESI, senão `None` | CONFERE. ⚠️ **DIVERGE** do diagnóstico em um ponto: ela lê "só a string recebida", e **quem a alimenta decide** (ver `nodes.py:1009-1018`) |
| **:128-129** | `def _client_facing(self) -> bool: return self.agent_role in _CLIENT_FACING_ROLES` | CONFERE |
| **:197-203** | `if (self._client_facing and status in ("ambiguous_policy","policy_number_ambiguous","multiple_matches")): hint = _product_hint_from_query(user_query)` | CONFERE — **`core` nunca entra na auto-seleção** |
| **:405** | `lines.append("opcoes_de_apolice (liste TODAS, com os numeros exatos):")` seguido do loop `for match in matches[:10]` (`:406-412`) imprimindo `policy_status` cru | CONFERE (diagnóstico dizia 404-412) |
| **:453** | `"4. Se houver mais de uma apolice vigente: escolha VOCE a coerente com o pedido … So pergunte ao cliente se houver 2+ apolices do MESMO ramo…"` | CONFERE — 📊 **exatamente 48 linhas abaixo de :405** |
| **:449** | `"5. Liberty e Yelum sao a MESMA seguradora … Itau = grupo Porto."` | **conhecimento de catálogo dentro de prompt** — SPEC §5.4 |
| **:465** | `"1b. Se houver coberturas_item_a_item, LISTE TODAS (nenhuma de fora), cada uma com limite, franquia e premio…"` | 🔴 **FICA** — é o conserto de `bf963b0` |
| **:467** | `"3. Se houver opcoes_de_apolice, liste TODAS com os numeros exatos e peca a escolha."` | 🔴 **SAI** — DIVERGE: o diagnóstico citava `:474` |

🔴 **A armadilha:** `:465` e `:467` estão a **duas linhas** uma da outra, usam as **mesmas palavras**
("liste TODAS") e têm efeitos **opostos**. Aplicar "tirar 'liste TODAS' do briefing" ao pé da letra reintroduz o
defeito das 6 coberturas de 10.

### 2.2 `backend/app/agents/nodes.py`

| linha | evidência | veredito |
|---|---|---|
| **:263-273** | o guarda de `policy_options` (SPEC-016.1 D7): para cada opção, se o número não aparece no texto do modelo, `return rendered` — **descarta a resposta** | CONFERE |
| **:273** | `if not options and ("seguradora" not in lower or "numero" not in lower and "número" not in lower)` | ⚠️ precedência de `and`/`or` — **medir com teste antes de tocar** (protocolo §0.4) |
| **:942-946** | `current_user_query` = a **última** `HumanMessage` | CONFERE |
| **:1009-1018** | `_query_for_tool = current_user_query;` **`if _role in ("attendance","insured_external")`** → `" \| ".join([t for t in _recent_humans[-3:] if t])` | CONFERE — 🔴 **a janela de 3 já existe; `core` está fora dela** |
| **:784** | `def _abrir_registro_de_invocacao(state, *, tool_name, tool_args)` | CONFERE |
| **:814-830** | `_RegistroInerte` — engole falha de registro para não derrubar a tool | CONFERE, **sem contador** |
| **:1057** | `registro = _abrir_registro_de_invocacao(...)` + `with registro:` envolvendo toda execução de tool | CONFERE |

### 2.3 `backend/app/services/policy_answer_composer.py` (410 linhas)

```
:279-281  def _real_vigencia(match):
            """Vigência REAL calculada pelas datas — a fonte marca 'ativo' até em
               apólice vencida há anos (bug visto no teste do founder 2026-07-10)."""
:297-300  def _compose_options(matches):
            # Vigência real primeiro; vencidas/canceladas NUNCA aparecem como opção
            # quando existe apólice vigente (só confundem o cliente).
:216      vigencia_real = _real_vigencia({**pack, **selected})
:358      text = _compose_options(result.get("matches") or [])
```

**CONFERE.** **INFERÊNCIA:** a regra certa já está escrita e comentada; ela só roda **tarde**, no compositor, e
não impede o conector de emitir `ambiguous_policy` antes.

### 2.4 `backend/app/api/infocap_connector.py` (~4.250 linhas)

| linha | evidência | veredito |
|---|---|---|
| **:1315-1330** | `if documents_count > 1 and not requested_policy_number: return _done({"status":"ambiguous_policy", "matches":[p for p in policies[:10]], "requires_human":True, "blockers":["multiple_policies"]})` — **contagem pura, nenhuma data** | CONFERE |
| :940 | `infocap_lookup(payload, x_autobrokers_internal_key, db)` · payload em `:182` | superfície do adaptador |
| :4039 | `infocap_policy_detail(...)` · payload em `:3187` | idem |
| :4250 | `infocap_vehicle_item(...)` — **sem rota HTTP**, só interno · payload em `:4204` | idem |
| :3349 | `_fetch_policy_items(client, headers, *, itens_path, codfil, nosnum, company_id) -> List[Dict]` — GET em `:3380`, cache Redis | `/itens` (commit `bf963b0`) |
| :3269 | `_flatten_item_garantias` | achatamento das garantias |
| :1508, :3464, :3870 | `_INSTALLMENT_KEYS = {"parcelas","prestacoes","prestações","installments"}` — **parcelas vêm do payload do `/documento`, não de rota própria** | CONFERE |
| :3599 → :2188 → :2225 → :3695 / :3739 | cadeia do PDF oficial: `_extract_official_document_candidates` → `_fetch_official_document_candidate_for_policy_pipeline` → `_maybe_attach_official_policy_document_evidence` → `_inspect_pdf_bytes` / `_classify_official_document_response`; auditoria em `:2539` | CONFERE |

📊 **`/seguradoras` e `/ramos` não são chamados em lugar nenhum do código.** Comando:
`grep -rn "seguradoras\|/ramos" backend --include=*.py`. As duas únicas menções estão em **docstring** de
`backend/app/providers/susep_ses_provider.py:36,48` e se referem a um censo manual.
⚠️ **Isto DIVERGE do diagnóstico §1.2**, que as lista entre "campos da API nunca lidos" como se fosse defeito.
**RECOMENDAÇÃO:** não é defeito — é a arquitetura correta sob D-PILOTO-11. Ver SPEC §5.4.

### 2.5 `backend/app/services/policy_document_evidence_service.py` (844 linhas)

```
:132  def policy_document_evidence_requested(question, explicit=False) -> bool:
          if explicit: return True
          normalized = _strip_accents(question or "")
          return any(term in normalized for term in _INTENT_TERMS)
:47   _INTENT_TERMS = (cobertura, coberturas, cobre, coberto, garantia, garantias,
                       assistencia, eletricista, encanador, chaveiro, franquia, lmi,
                       limite, importancia segurada, clausula, exclusao, condicao, …)
```

**CONFERE.** ⚠️ O parâmetro `explicit=True` já é o caminho para ler sempre — **ninguém o usa a partir do fluxo
de apólice**.

### 2.6 `backend/app/services/policy_facts.py` (305 linhas, SPEC-016 E2)

```
:23   FACT_SOURCES = ("infocap_structured", "official_document", "policy_rule")
:24   FACT_TYPES   = ("coverage","assistance","deductible","limit","installment",
                      "exclusion","premium","validity","clause")
:77   def _fact(..., source: str, source_detail=None, confidence: str = "medium")
:120  source="infocap_structured", confidence="high"
:165  confidence validado em ("high","medium","low")
:179  source="official_document", confidence="high"
```

**FATO:** o modelo canônico com **origem e confiança por fato** já existe.
🔴 **FATO, e é o vazamento:** o valor canônico de origem se chama **`infocap_structured`** — o nome do
fornecedor dentro do modelo do domínio. A docstring do módulo (`:1-13`) promete *"módulo PURO (sem I/O, sem
provider, sem LLM)"* e a constante quebra a promessa.

### 2.7 `backend/app/agents/graph.py`

```
:1377  rag_prefetch_content = rag_result.get("content") or ""      ← cru, sem [:N], sem contagem
:1394  if rag_prefetch_content:
:1395-1405  dynamic_context += "\n\n=== 📚 CONTEXTO RECUPERADO DA BASE DE CONHECIMENTO ===\n"
                               f"{rag_prefetch_content}\n"
                               "=== FIM DO CONTEXTO RECUPERADO ===\n\n"
                               "INSTRUÇÕES SOBRE O CONTEXTO RECUPERADO:\n"
:1515  composite_prompt = static_prompt + dynamic_context
```

**CONFERE.** A pergunta do usuário fica **antes** do bloco. Ver referência externa ⑤.

### 2.8 `backend/app/core/prompts.py` (660 linhas)

| o que | onde | veredito |
|---|---|---|
| `CORE_BASE_PROMPT` | **:22-60** | 🔴 **nenhuma** regra de vigência ou de ramo; "vigência" só aparece como **lista de dados que a tool devolve** (`:37`, `:40`) |
| `ATTENDANCE_BASE_PROMPT` | :83-218 | **já tem a regra certa**: `:126` *"Mais de uma apólice vigente? ESCOLHA VOCÊ…"*; `:206` *"só ofereça as com vigência ATUAL… Vencidas/canceladas não são opção"* |
| `SYSTEM_BASE_PROMPT = CORE_BASE_PROMPT` | :220 | — |
| outras instruções citadas pelo diagnóstico | `:133` (vidros: "apenas apólices AUTO ATIVAS"), `:185`, `:189` | CONFEREM |
| "SEMPRE se apresente" | **:357-359** (diagnóstico dizia 352-361) | DIVERGE na linha; injetado só se `role in ("attendance","insured_external") and display_name` (`:351`) |
| 📊 **`InfoCap`** | **:31, :37, :40, :42, :133, :193** (+ comentário `:365`) = **6 ocorrências** | 🔴 três delas dentro do `CORE_BASE_PROMPT` |
| 📊 **`CorpAPI`** | **0 ocorrências** | — |

Comando: `grep -nic "infocap" backend/app/core/prompts.py` e `grep -ni "infocap" backend/app/core/prompts.py`.

### 2.9 `backend/app/factories/llm_factory.py`

```
:32   PISO_DE_SAIDA_DA_CONVERSA = int(os.getenv("PISO_DE_SAIDA_DA_CONVERSA", "8192"))
:34-35 PAPEIS_QUE_CONVERSAM = ("", "core", "attendance")
:38-47 def piso_de_saida(agent_role, max_tokens):
           papel = str(agent_role or "").strip().lower()
           if papel not in PAPEIS_QUE_CONVERSAM: return max_tokens
           return max(atual, PISO_DE_SAIDA_DA_CONVERSA)
:84-96 max_tokens = source.get("llm_max_tokens") or company_config.get("llm_max_tokens", 8192)
       max_tokens_gravado = max_tokens
       max_tokens = piso_de_saida((agent_data or {}).get("agent_role"), max_tokens)
```

🔴 **DEFEITO NOVO, não listado no diagnóstico:** **`insured_external` não está em `PAPEIS_QUE_CONVERSAM`.** É o
papel do agente que fala com o **segurado** (GLOSSARIO). Ele fica com o valor do banco — 📊 1200 ou 2000 — **sem
piso**. Teste do produto (protocolo §2): muda um byte do que chega ao segurado → **BLOCKER**.

### 2.10 `backend/app/services/assistance_policy.py`

```
:25  RULE_ID = "residential_24h_standard_v1"
:26  RULE_VERSION = 1
:28  STANDARD_SERVICES = ("eletricista", "chaveiro", "hidraulica_encanador")
```

**CONFERE** — a "constante com 3 serviços residenciais" do diagnóstico §1.3. **Fora do escopo da 001.1**
(é a 001.5 que a substitui); citada aqui só para o executor não a confundir com `PlanoDeAssistencia`.

---

## 3. Consultas ao banco — executadas em 13/09/2026, read-only, sem PII

### 3.1 `llm_max_tokens` (P-PILOTO-17)

```python
# backend/ · supabase service role · SELECT apenas
c.table('agents').select('agent_role,llm_max_tokens,llm_model,is_active,company_id').execute()
```

📊 **Resultado:**

```
8 agentes   ·   4 core  +  4 attendance   ·   todos claude-sonnet-5
llm_max_tokens:   1200 → 4 agentes      2000 → 4 agentes
por (papel, valor):  (core,1200)=3  (core,2000)=1  (attendance,2000)=3  (attendance,1200)=1
ativos: 3 (todos core)
```

**FATO:** nenhum agente tem 8192 gravado. **É o número que o VERIFY da migration compara.**

📊 **E os quatro defaults de 2000** (comando: `grep -rn "llm_max_tokens" backend --include=*.py --include=*.sql`):

```
backend/supabase/migrations/schema_completo.sql:454   public.agents.llm_max_tokens    integer DEFAULT 2000
backend/supabase/migrations/schema_completo.sql:581   public.companies.llm_max_tokens integer DEFAULT 2000
backend/app/api/agent_config.py:133                                                   = 2000
backend/app/models/agent.py:19                                                        default=2000, ge=100
backend/app/factories/llm_factory.py:84-85            company_config.get(..., 8192)   ← o código diverge
```

⚠️ **Não existe tabela `agent_configs`.** Quem procurar por ela não acha nada.

### 3.2 `messages.payload.turn` (P-PILOTO-18)

```python
c.table('messages').select('id,role,created_at,payload', count='exact') \
 .gte('created_at','2026-09-10T00:00:00Z').lt('created_at','2026-09-11T00:00:00Z').execute()
```

📊 **Resultado:** `count = 5.038` linhas em 10/09. ⚠️ **A resposta trouxe a primeira página (1.000 linhas)** —
553 `user` + 447 `assistant`. Sobre essa página:

```
18 linhas carregam payload.turn
chaves: submitted_at · stages · status · attempt · ttft_ms · total_ms · artifacts ·
        error_code · client_request_id
linhas com alguma chave de ferramenta (tool_calls|tools|tool_invocations): 0
```

**FATO:** o turno não referencia ferramenta.
🔴 **INFERÊNCIA ERRADA que era fácil tirar daqui, e que P-PILOTO-18 tirou:** "o chat não registra tool call".
**Registra** — em `tool_invocations`, por `nodes.py:1057`. O que falta é a **ligação** com o turno.
**RECOMENDAÇÃO:** ver SPEC §9.3. **Este é o exemplo vivo de por que se mede na ferramenta que se vai usar**
(CLAUDE.md §9.4): olhar só `messages` responde uma pergunta diferente da que se fez.

### 3.3 O que NÃO foi medido, e precisa ser no BLOCO 0

| medição | por que ficou de fora | como medir |
|---|---|---|
| as 📊 31 linhas de opção de apólice vencida | exigiria ler conteúdo de mensagem — **proibido ao redator** | consulta com `ilike` sobre marcador estrutural, contando, sem imprimir texto |
| as 7 perguntas reais do chat de 10/09 | idem | extrair **só as perguntas**, redigir PII, gravar em `backend/tests/corpus/perguntas_do_chat/` |
| o golden HDI (10 coberturas) e Allianz condomínio (15) | exigiria chamar a InfoCap com um documento real | montar **pela porta, em memória**, e persistir só o que o teste compara |
| tamanho real dos dois turnos de 120/128 chunks | exigiria ler o payload de RAG | contar chunks e caracteres, sem imprimir conteúdo |
| se `tool_invocations` guarda `tool_args` **cru** hoje | não consultado | 🔴 **primeira consulta do BLOCO 0** — se guardar, é **P1 de segurança**, não pendência |
| quem lê `companies.llm_max_tokens` | não rastreado | `grep` + teste |
| a DDL real de `tool_invocations` | não rastreada no repositório (📊 declarado em `20260816_02_spec075_portal_job_lineage_priority.sql:147`) | ler do catálogo do Postgres e registrar no `MANIFEST.md` como `NÃO RASTREADA` |

---

## 4. O padrão interno que a SPEC copia — SPEC-094, a porta que já passou no gate

**Arquivos:**

```
backend/app/providers/brokerage_analytics_provider.py    216 linhas  ·  a PORTA
backend/app/providers/infocap_analytics_provider.py    1.604 linhas  ·  o ADAPTADOR de produção
backend/app/providers/reference_analytics_provider.py    357 linhas  ·  o ADAPTADOR de teste
backend/app/providers/susep_ses_provider.py              551 linhas  ·  conector público, só lê MinIO
backend/app/agents/tools/executive_intelligence.py:1151,1186          ·  o CONSUMIDOR
backend/tests/test_o_pulso_360_nao_pertence_a_infocap.py             ·  o TESTE DE PORTA
docs/canon/specs/SPEC-094-o-pulso-360-nao-pertence-a-infocap.md
```

**Esqueleto da porta** (assinaturas, não corpo):

```python
@runtime_checkable
class BrokerageAnalyticsProvider(Protocol):
    provider_key: str
    async def capabilities(self, *, company_id: str, **kw) -> Dict[str, str]: ...
    async def fatos(self, *, company_id, inicio: date, fim: date, **kw) -> FactSet: ...
    async def policies(self, *, company_id, inicio, fim, time_basis: str, **kw) -> List[PolicyFact]: ...
    async def producer_assignments(...) -> List[ProducerAssignmentFact]: ...
    async def commissions(...) -> List[CommissionFact]: ...
    async def renewals(...) -> List[RenewalFact]: ...
class FalhaDoProvider(RuntimeError): ...
class RecusaDeContaCompartilhada(FalhaDoProvider): ...
```

**Registry** (`:199-215`), declaradamente *"o MESMO padrão de `policy_data_provider.py:134-149`"*:
`register_brokerage_analytics_provider` · `resolve_brokerage_analytics_provider(provider_key="infocap")` ·
`brokerage_analytics_providers()` (cópia, para diagnóstico). Auto-registro na importação
(`infocap_analytics_provider.py:1604`).

🔴 **Como o teste de porta é escrito neste repositório** — é o molde de M-A1 e M-A4:

1. **asserção estrutural** sobre o módulo importado: `hasattr(porta, "BrokerageAnalyticsProvider")`,
   `callable(register_…)`, `callable(resolve_…)`;
2. **grep no TEXTO do arquivo**: a porta não pode conter `from app.comercial.(metricas|calculos)`; o adaptador
   **tem** de importar `fonte_infocap` e conter `"connected"`, `"F-094-07"`, `"account_fingerprint"`;
   a docstring tem de conter `permanente`;
3. **comportamento com fixture de 4 conexões reais da corretora**: a escolha cai na única `connected`, nunca na
   `archived`, e **sem nenhuma `connected` não inventa uma**;
4. **mutantes nomeados** (M12, M13…) e `vermelho_ate(...)` para pendências declaradas.

**RECOMENDAÇÃO:** copiar **o padrão**, nunca o código (CLAUDE.md §5). Em particular, **não** importar os tipos de
fato da 094 (`PolicyFact`, `Money`) para dentro da apólice sem medir o acoplamento: analytics e apólice têm ciclos
de vida diferentes, e a 094 já declarou `UNAVAILABLE` como sentinela própria.

---

## 5. Pesquisa externa — cinco fontes primárias, reabertas em 13/09/2026

| # | fonte | URL | o que sustenta na SPEC |
|---|---|---|---|
| ① | **Cockburn — Hexagonal Architecture (Ports & Adapters)** | https://alistair.cockburn.us/hexagonal-architecture/ | *"The application has a semantically sound interaction with the adapters on all sides of it, **without actually knowing the nature of the things on the other side**."* → guarda M-A1 |
| ② | **Microsoft Azure Architecture Center — Anti-Corruption Layer** (padrão de Eric Evans, DDD) | https://learn.microsoft.com/en-us/azure/architecture/patterns/anti-corruption-layer | *"…forces the new system to adhere to at least some of the legacy system's APIs or other semantics … this support **corrupts** what might otherwise be a cleanly designed modern application."* e *"Communication between subsystem A and the anti-corruption layer always uses the data model … of subsystem A."* → a porta devolve `Apolice`, não o dict do fornecedor. ⚠️ A mesma página manda **não** pôr regra de negócio na camada — por isso `reconciliar` é política da porta, não do adaptador |
| ③ | **PEP 544 — Protocols: structural subtyping** | https://peps.python.org/pep-0544/ | *"A concrete type X is a subtype of protocol P if and only if X implements all protocol members of P with compatible types… subtyping with respect to a protocol is always structural."* e o aviso sobre `@runtime_checkable` não ser type safe → o gate é o verificador de tipos, não `isinstance` |
| ④ | **W3C PROV-O: The PROV Ontology** (Recommendation, 30/04/2013) | https://www.w3.org/TR/prov-o/ | `Entity`/`Activity`/`Agent` + `wasDerivedFrom` (*"a transformation of an entity into another"*) → proveniência é **do dado**, não do log: `CampoComOrigem` |
| ⑤ | **Liu et al., "Lost in the Middle: How Language Models Use Long Contexts", TACL 2023** | https://arxiv.org/abs/2307.03172 | *"performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts, **even for explicitly long-context models**."* → a pergunta é repetida **depois** do bloco recuperado |

⛔ **Nenhuma delas é autoridade** (protocolo §7.3). Smith, Work OS, Tool Gateway, Skill Registry e Artifact Hub
continuam únicos. Modela-se o **padrão**, não o produto.

**O pesquisador do executor reabre as cinco na conversão e registra a data.** Se alguma envelheceu ou existe
melhor, substitui e escreve por quê.

---

## 6. Roteiro de remedição — comandos para o BLOCO 0

> São **instruções para o executor**, não saídas já obtidas. Rodar na árvore certa, `PYTHONIOENCODING=utf-8`,
> Python de dentro de `backend/`.

```bash
# preflight (CLAUDE.md §2)
git fetch origin
git rev-parse HEAD; git rev-list --count HEAD..origin/main; git rev-list --count origin/main..HEAD
git branch --show-current; git status --short

# a fronteira — é este número que define a SUPERFÍCIE do card
grep -rn "infocap_connector" backend --include=*.py | grep -v "^backend/app/providers/" \
                                                    | grep -v "^backend/app/api/infocap_connector.py"
grep -rniE "preliq|nosnum|codfil|sit_renovacao_txt|tabela_itens|forma_pag|inivig|fimvig" \
     backend/app --include=*.py | grep -v "^backend/app/providers/" | grep -v "infocap_connector.py"
grep -ni "infocap\|corpapi" backend/app/core/prompts.py        # hoje: 6 e 0

# a porta e o padrão
sed -n '1,60p'  backend/app/providers/policy_data_provider.py
sed -n '190,216p' backend/app/providers/brokerage_analytics_provider.py
grep -n "def test_\|vermelho_ate\|hasattr\|callable" backend/tests/test_o_pulso_360_nao_pertence_a_infocap.py | head -40

# as linhas do defeito
sed -n '20,45p;125,132p;195,215p;400,415p;445,475p' backend/app/agents/tools/infocap_tool.py
sed -n '255,280p;940,950p;1005,1020p' backend/app/agents/nodes.py
sed -n '275,305p' backend/app/services/policy_answer_composer.py
sed -n '1310,1332p' backend/app/api/infocap_connector.py
sed -n '125,140p;45,70p' backend/app/services/policy_document_evidence_service.py
sed -n '1370,1410p;1510,1520p' backend/app/agents/graph.py
sed -n '20,50p;80,100p' backend/app/factories/llm_factory.py
sed -n '20,35p' backend/app/services/policy_facts.py

# catálogo nosso
python -c "import json,io;d=json.load(io.open('docs/canon/providers/susep/seguradora-coenti.json',encoding='utf-8'));print(list(d.keys()));print(d.get('placar'));print(d.get('placar_das_siglas'))"

# pendências, por número (NUNCA o arquivo inteiro)
grep -n "P-PILOTO-1[6-9]\|P-PILOTO-20" docs/canon/PENDENCIAS.md

# os 4 guardas de P-PILOTO-20
python -m pytest backend/tests/test_infocap_policy_output_guard.py \
                 backend/tests/test_spec016_policy_intelligence.py -x -q

# antes de QUALQUER SQL
sed -n '1,120p' docs/canon/MIGRATIONS-AUTHORITY.md
```

**Consultas (read-only, contagens, sem conteúdo de mensagem):**

```sql
SELECT agent_role, llm_max_tokens, count(*) FROM agents GROUP BY 1,2 ORDER BY 1,2;
SELECT count(*) FROM messages WHERE created_at >= '2026-09-10' AND created_at < '2026-09-11';
-- tool_invocations: existe? guarda argumento cru?  🔴 primeira consulta do BLOCO 0
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'tool_invocations';
```

---

## 7. Testes que já existem sobre esta superfície — ler antes de escrever guarda novo

| arquivo (`backend/tests/`) | linhas | o que guarda |
|---|---:|---|
| `test_a_apolice_responde_item_por_item.py` | 326 | a apólice responde cobertura, franquia e prêmio de **cada** item (commit `bf963b0`, 31 asserções + 5 mutações) |
| `test_a_cobertura_tem_lastro_no_acervo.py` | 254 | toda afirmação de cobertura aponta uma tela do acervo |
| `test_cobertura_nao_mente_para_cima.py` | 185 | cobertura conta opção **distinta**, não ocorrência |
| `test_infocap_policy_output_guard.py` | 174 | Policy Response Contract / guard de saída — 🔴 **mudo desde 23/08** (P-PILOTO-20) |
| `test_spec016_policy_intelligence.py` | 651 | a vertical Policy Intelligence — 🔴 **mudo** (P-PILOTO-20) |
| `test_infocap_contract_capture.py` | 601 | captura de contrato/shape da InfoCap |
| `test_infocap_official_document_source_audit.py` | 358 | auditoria da fonte do documento oficial |
| `test_infocap_official_policy_evidence_pipeline.py` | 312 | pipeline de evidência documental |
| `test_o_chat_fala_como_corretor.py` | 752 | o chat fala como corretor, não como banco de dados |
| `test_o_chat_fala_tipado.py` | 1.566 | tipagem da SPEC-096 no motor |
| `test_a_resposta_chega_inteira.py` | 577 | piso de 8192 + continuação (commit `312939f`) |
| `test_o_pulso_360_nao_pertence_a_infocap.py` | ~1.800 | **o molde do teste de porta** |

📊 **`backend/tests/corpus/` hoje:** `retornos_de_cobranca.json` (5.305 bytes, **sintético**, declarado no `_doc`)
e `telas_reais/` (17 arquivos, ~1,4 MB, telas de URA por seguradora/ramo).
🔴 **Não existe corpus de perguntas do chat.** A 001.1 cria o primeiro:
`backend/tests/corpus/perguntas_do_chat/2026-09-10.json` — **só as perguntas**, PII redigida, com o `_doc`
dizendo de onde vieram e o que não contêm.

---

## 8. Armadilhas que o aquecimento tem de refutar

Cada uma tem resposta **óbvia e errada**. As duas primeiras são **afirmações deliberadamente falsas, assinadas**
(protocolo §5.2).

1. 🔴 **FALSA, assinada:** *"`PolicyDataProvider` não existe; a SPEC cria a porta do zero em
   `backend/app/services/policy_provider/`."* — refute com `find` e `grep`, e diga quantos chamadores já a usam.
2. 🔴 **FALSA, assinada:** *"Tirar todas as instruções 'liste TODAS' do briefing conserta o defeito."* — mostre
   as duas linhas, a distância entre elas, e o que acontece com as coberturas.
3. *"A inferência de ramo só lê a mensagem atual."* — parcialmente verdade. **Para quem?** Mostre a linha que faz
   a diferença.
4. *"`chaveiro` está faltando nos regex."* — está **em um** deles. Diga em qual, e o que
   `_product_hint_from_query` devolve hoje para *"chaveiro, fiquei trancado fora de casa"*.
5. *"O guarda de `nodes.py:263` tem de ser apagado."* — diga o que ele impede, e o que aconteceria sem ele quando
   a escolha é legítima.
6. *"P-PILOTO-18 diz que o chat não registra tool call; basta gravar em `payload.turn`."* — refute com
   `arquivo:linha`, e diga por que a solução da pendência criaria motor paralelo.
7. *"O piso de 8192 já protege todo mundo que conversa."* — conte os papéis da tupla e diga qual falta.
8. *"`agents.llm_max_tokens` é o único lugar do default 2000."* — conte os lugares.
9. *"`policy_status` da fonte diz se a apólice está vigente."* — cite a docstring que diz o contrário e a data
   do bug que a originou.
10. *"Ler `/ramos` e `/seguradoras` da CorpAPI conserta o catálogo."* — diga o que D-PILOTO-11 manda, e o que já
    existe versionado.
11. *"O modelo canônico precisa nascer: não há nada com origem por campo."* — mostre onde já há, e qual é o
    defeito dele.
12. *"O contador de prêmio é um detalhe de relatório."* — diga quanto ele teria pego na HDI, em R$ e em %.
13. *"A reconciliação é do adaptador InfoCap."* — diga o que a fonte externa ② proíbe e o que D-PILOTO-11 decide.
14. **Liste o que você NÃO entendeu ou não conseguiu provar.** "Entendi tudo" reprova.
15. **Ache um defeito material que esta proposta não aponta** — ou diga exatamente onde procurou e não achou.
    Entregue a nota e o card que você aplicaria.

---

## 9. O que continua desconhecido

1. Se `tool_invocations` guarda `tool_args` **cru** hoje (🔴 potencial P1).
2. A DDL real de `tool_invocations` (não rastreada no repositório).
3. Quantas linhas de `policy_facts` estão **persistidas** em algum lugar com `source="infocap_structured"` —
   decide se a renomeação precisa de backfill ou só de conversão na leitura.
4. O tamanho real, em caracteres e chunks, dos dois turnos de 120/128 chunks — define o teto de §9.1.
5. Se algum consumidor lê `companies.llm_max_tokens`.
6. O comportamento exato de `nodes.py:273` (precedência de `and`/`or`).
7. Se o cache de 180 s de `/itens` (`bf963b0`) tem `company_id` na chave — 🔴 se não tiver, é **P0 cross-tenant**,
   e nesse caso a SPEC **para** e registra (CLAUDE.md §10, item 4).
8. Se a HDI e a Allianz do golden continuam com 10 e 15 coberturas hoje.

**Nenhum destes vira afirmação na SPEC definitiva sem comando ao lado.**

---

## 10. Regra de integridade deste research pack

Este documento é evidência **datada de 13/09/2026 sobre o commit `a0bb5fe`**. Ele não prova que o produto
funciona: prova que o código diz o que diz. **Leitura de código não é prova de comportamento** — quem confundir
os dois entrega uma SPEC construída sobre uma causa que não era (CLAUDE.md §9.2).

Se o executor encontrar divergência entre este pacote e a árvore, **a árvore vence, a divergência vai escrita no
relatório, e a SPEC definitiva é corrigida** — nunca o contrário.

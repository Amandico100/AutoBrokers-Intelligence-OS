# AUDITORIA (sem editar código) — InfoCap não lê coberturas, CPF inconsistente, prompt "fraco", ferramentas que não salvam, estrutura paralela

> Data: 2026-06-24. A pedido do Founder: PARAR de codar, auditar com EVIDÊNCIA, achar a causa real, depois plano. Nenhuma edição de código neste passo.

## 1. Há DOIS system prompts no Core? SIM — por design do Smith (2 camadas), não é estrutura paralela "nova"
**Evidência (código):**
- `graph.py:484` → `system_prompt_source = real_agent_data.get("agent_system_prompt")` (o prompt do AGENTE, o que aparece no editor "Personalidade").
- `graph.py:513` → `base_instructions = system_prompt_source` (+ context_package + tools).
- `graph.py:678` → `static_prompt = build_composite_prompt(base_instructions, agent_role=...)`.
- `prompts.py` → `build_composite_prompt` = **CORE_BASE_PROMPT (código) + client_instructions (o agent_system_prompt do editor)**.

**Conclusão:** o prompt EFETIVO do Core = **CORE_BASE_PROMPT (no CÓDIGO, base forte — anti-trava, inteligência, regras) + agent_system_prompt (no EDITOR, ~650 chars, mais simples) + contexto dinâmico**. O editor só mostra a **camada 2**; a **camada 1 (forte) está no código** (`backend/app/core/prompts.py`). Por isso "parece fraco" — mas as regras fortes ESTÃO aplicadas. Isso é o mecanismo nativo do Smith (`build_composite_prompt`, desde o P0), **não** um segundo motor de prompt criado à parte. Risco real: o editor é enganoso (não revela a camada 1).

## 2. Você edita o GLOBAL; o chat usa a instância da RESULTA
**Evidência (banco):** 3 agentes role=core — **Studio global** (`b86835eb`, prompt 636) · **Resulta** (`20845996`, 650) · **Rafael** (`0aa7ccd9`, **7914** — prompt antigo/rico).
- "Editar padrão global" (Blueprint Center) edita o **Studio global**. O **chat da Resulta usa a instância Resulta** (20845996). Editar o global **não muda o chat da Resulta** até um release+rollout.
- MAS minha mudança de `CORE_BASE_PROMPT` é no CÓDIGO → vale para TODOS os cores (inclui Resulta) no deploy. Por isso o anti-trava JÁ vale para a Resulta.
- Inconsistência: o core da Rafael tem prompt de 7914 chars (antigo) — instâncias divergentes; precisa normalizar.

## 3. Ferramentas (Visão/CSV) "não salvam": schema e persistência estão CORRETOS — o problema é OUTRO
**Evidência:** a tabela `agents` TEM as colunas `allow_vision, vision_model, tools_config`. `AgentUpdate` inclui esses campos. `update_agent` grava (`model_dump(exclude_unset=True)`). `AgentResponse` herda e devolve. Ou seja, um `PUT` no agente certo PERSISTE.
**Então por que parece não salvar?** Duas causas reais (a confirmar — não chutar):
- **(a) Camadas não reconciliadas (C-FIX-1):** no C-FIX-1 eu movi o gate de runtime da **busca web** para o **Capability Registry** (`graph.py`: `web_search_tool = WebSearchTool() if "platform.web.search" in _active`). Ou seja, o toggle "Busca Web" do editor (`allow_web_search`) ficou **parcialmente decorativo** — quem manda agora é o resolver. Isso é o "cheiro de estrutura paralela" que você sentiu.
- **(b) Visão pode não ser consumida pelo runtime:** na montagem de tools do `graph.py` há KB, web, handoff, CSV, HTTP, MCP, subagentes — **não vi uma tool de "visão" anexada**. Então `allow_vision` pode não ter efeito no runtime mesmo salvo (e o editor sugere que tem). CSV/handoff (tools_config) ESSES o runtime usa.
**Conclusão:** o save provavelmente FUNCIONA no banco; o que está quebrado é (1) editar global ≠ refletir no chat da Resulta, e (2) **duas fontes de governança de ferramentas** (flags nativas do editor vs Capability Registry) não reconciliadas. Essa é a principal dívida arquitetural.

## 4. O PRINCIPAL — InfoCap não traz coberturas e o CPF veio errado: CAUSA-RAIZ = nomes de campo CHUTADOS
**Evidência (chat real):** busca por NOME devolveu CPF `746.151.462-75` (**ERRADO**); o correto é `030.743.279-36`. Coberturas vieram como itens todos rotulados **"P"**. O número da apólice (`202623140269972`) veio certo.
**Diagnóstico honesto:** o conector extrai campos por **nomes CHUTADOS** (`_DOC_KEYS`, `_COVERAGE_LABEL_KEYS`). 
- O CPF: meu `_first_str(record, _DOC_KEYS)` pegou um campo de 11 dígitos que **não é o CPF** (746...). O CPF real (030...) está em OUTRO campo que eu não priorizei.
- As coberturas: o rótulo que leio retorna "P" (um código), não a descrição. A descrição/valor da cobertura está em campos que NÃO estão na minha lista, OU exige o detalhe item-a-item.
**Eu NÃO tenho o schema real de resposta da InfoCap.** Venho CHUTANDO os nomes dos campos → é o "tentativa e erro" que você (com razão) odeia. O sistema antigo (ResultVision) tinha o mapeamento certo; **não consegui recuperar esse código** pelas ferramentas disponíveis (repo privado/branch/paginado — WebFetch só traz listagens parciais).
**A correção SEM chute exige DESCOBRIR o shape real.** Duas formas (escolha uma):
- **(A) Rodar o PROBE que JÁ existe** (`POST /attendance/connectors/infocap/probe`) com o CPF do Rafael → ele retorna os **nomes reais dos campos** (`sample_keys`, `array_key_detected`) **sem expor valores**. Com isso, mapeio CPF + coberturas EXATO, 1 vez.
- **(B) Você cola aqui** o arquivo de integração InfoCap do ResultVision (ou um JSON de exemplo de UMA apólice/cliente da InfoCap). Com o shape real, mapeio certo.

## 5. Estrutura paralela? Veredito honesto
- InfoCap, OAuth Drive/Notion: **reusam** `tenant_connections`+Vault (não paralelo). ✓
- Document Evidence: **reusei** o pipeline existente (upload→Docling→Qdrant→`knowledge_base_search`), liguei via prompt — não criei base nova. ✓
- **MAS o Capability Registry (C-FIX-1) virou uma SEGUNDA fonte de governança de ferramentas** sobre as flags nativas do Smith (editor). Não é segundo motor, mas é **governança duplicada não reconciliada** — é a dívida que causa a confusão de "toggle não funciona" e "estrutura paralela". É o que precisa ser resolvido.

## PLANO (após sua aprovação — sem código até lá)
1. **DESCOBERTA (sem chute):** rodar o PROBE da InfoCap (ou você cola o mapeamento antigo) → capturar nomes reais de campo (CPF; chave da lista de coberturas; campos de descrição/valor/franquia/prêmio).
2. **Mapear InfoCap EXATO** (CPF + coberturas) a partir do shape real → correção precisa, 1 vez, com teste.
3. **Reconciliar governança de ferramentas:** UMA fonte de verdade (Registry ↔ flags do editor) — o toggle do editor passa a refletir/alimentar o runtime de verdade; confirmar/ligar a Visão (ou remover o toggle se o runtime não usa).
4. **Normalizar o prompt do Core:** decidir se a base forte fica no código (e documentar) pra o editor não enganar; alinhar instâncias (global/Resulta/Rafael).
5. **Document Evidence (upload)** só como complemento, se a InfoCap ainda não cobrir algum caso.

## O que eu preciso de você para destravar o item 4 (o principal)
Escolha **(A)** rodar o PROBE (eu te passo o comando exato) **ou (B)** colar o arquivo InfoCap do ResultVision / um JSON de exemplo. Com o shape real, paro de chutar e conserto de uma vez.
